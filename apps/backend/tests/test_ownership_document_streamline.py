"""Owner-authorized review continuation and active-slot replacement regressions."""

from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from test_batch_review_decisions import create_review
from test_phase11_reconciliation import FieldOverrideIdp
from test_zero_touch_orchestration import PDF, build_system

from app.connectors.mock_idp import MockIdpProvider, MockIdpScenario
from app.domain.documents import DocumentFieldKey
from app.domain.zero_touch import AutomationStage, validate_automation_transition
from app.services.document_errors import DocumentProcessingInfrastructureError
from app.services.ownership_errors import OwnershipInfrastructureError
from app.services.zero_touch_errors import ZeroTouchInfrastructureError


def pending_review():
    client, zero, documents, target, _ = build_system(require_confirmation=True)
    created = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"}).json()
    cid = UUID(created["case"]["case_id"])
    doc = zero.intake_document(
        case_id=cid,
        display_name="synthetic-review.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=FieldOverrideIdp({DocumentFieldKey.LEGAL_NAME: "OTHER NAME"}),
    )
    current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
    batch = {
        "expected_automation_version": current["version"],
        "expected_case_event_count": len(current["case"]["events"]),
        "documents": [
            {
                "document_id": str(doc.document_id),
                "expected_event_count": len(doc.events),
                "source_fingerprint": client.get(f"/api/onboarding/cases/{cid}/documents").json()[
                    0
                ]["review_source_fingerprint"],
                "decisions": [
                    {"field_key": f.field_key.value, "decision": "ACCEPTED"}
                    for f in doc.fields
                    if f.review_status == "PENDING"
                ],
            }
        ],
    }
    return client, zero, documents, target, cid, doc, batch


def test_final_intake_retry_projects_continuation_failure_and_retains_accepted_evidence():
    client, zero, documents, target, cid, doc, _ = pending_review()
    client._transport.raise_server_exceptions = False
    with pytest.raises(DocumentProcessingInfrastructureError):
        zero.intake_document(
            case_id=cid, display_name="failed-sibling.pdf",
            content_type="application/pdf", content=PDF,
            idp_provider=MockIdpProvider(MockIdpScenario.PROCESSOR_FAILURE),
        )
    failed = next(
        item for item in documents.list_documents(case_id=cid)
        if item.is_current_evidence and item.state == "FAILED"
    )
    zero.replace_document(
        case_id=cid, document_id=doc.document_id,
        expected_document_event_count=len(doc.events), display_name="replacement.pdf",
        content_type="application/pdf", content=PDF,
    )
    failure = OwnershipInfrastructureError(
        case_id=cid, analysis_id=uuid4(), correlation_id=uuid4(),
        code="OWNERSHIP_PERSISTENCE_UNAVAILABLE", message="Ownership evidence is unavailable.",
    )
    with patch.object(zero._ownership, "load", side_effect=failure):
        response = client.post(
            f"/api/clm/zero-touch/cases/{cid}/intake/documents/{failed.document_id}/retry",
            content=PDF,
            headers={"Content-Type": "application/pdf", "X-Document-Name": "retry.pdf"},
        )
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["code"] == "OWNERSHIP_PERSISTENCE_UNAVAILABLE"
    assert detail["case_id"] == str(cid)
    assert detail["message"] == "Ownership evidence is unavailable."
    assert set(detail) == {"code", "message", "case_id", "automation_id"}
    current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
    assert current["status"] == "TECHNICAL_FAILURE"
    assert current["current_stage"] == "OWNERSHIP"
    assert current["technical_failure"]["code"] == detail["code"]
    assert current["automation_id"] == detail["automation_id"]
    history = documents.list_documents(case_id=cid)
    accepted = next(item for item in history if item.supersedes_document_id == failed.document_id)
    assert accepted.is_current_evidence and accepted.state == "REVIEWED"
    retained = documents.get_document(case_id=cid, document_id=failed.document_id)
    assert retained.superseded_by_document_id == accepted.document_id
    assert retained.events[:len(failed.events)] == failed.events
    assert target.calls == ["search"]
    rejected = client.post(
        f"/api/clm/zero-touch/cases/{cid}/intake/documents/{failed.document_id}/retry",
        content=PDF,
        headers={"Content-Type": "application/pdf", "X-Document-Name": "retry.pdf"},
    )
    assert rejected.status_code == 409
    assert documents.list_documents(case_id=cid) == history
    assert target.calls == ["search"]


@pytest.mark.parametrize("decision", ["ACCEPTED", "REJECTED", "CORRECTED"])
def test_pending_confirmation_continues_once_to_truthful_blocker(decision):
    client, zero, documents, target, cid, doc, batch = pending_review()
    batch["documents"][0]["decisions"][0]["decision"] = decision
    if decision == "CORRECTED":
        batch["documents"][0]["decisions"][0]["corrected_value"] = "MERLION CIRCULAR LABS PTE. LTD."
    response = client.post(f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch)
    assert response.status_code == 200
    assert response.json()["status"] == "WAITING_FOR_REVIEW"
    assert response.json()["current_stage"] == (
        "READINESS" if decision == "CORRECTED" else "DOCUMENT"
    )
    assert target.calls == ["search"]
    assert (
        client.post(f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch).status_code
        == 409
    )
    retained = documents.get_document(case_id=cid, document_id=doc.document_id)
    assert sum(e.event_type.value == f"DOCUMENT_FIELD_{decision}" for e in retained.events) == 1
    assert zero.get(case_id=cid).started_at is not None


def test_incomplete_document_group_is_rejected_before_any_write_or_continuation():
    client, zero, documents, target, cid, batch = create_review(two_documents=True)
    batch["documents"][1]["decisions"].pop()
    before = documents.list_documents(case_id=UUID(cid))
    with patch.object(zero, "_advance_locked", wraps=zero._advance_locked) as advance:
        response = client.post(f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch)
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "ZERO_TOUCH_REVIEW_INCOMPLETE"
        advance.assert_not_called()
    assert documents.list_documents(case_id=UUID(cid)) == before
    assert target.calls == ["search"]


def test_pending_replacement_supersedes_slot_and_automatically_reprocesses():
    _, zero, documents, target, cid, doc, _ = pending_review()
    result = zero.replace_document(
        case_id=cid,
        document_id=doc.document_id,
        expected_document_event_count=len(doc.events),
        display_name="replacement.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    assert result.status == "WAITING_FOR_REVIEW" and result.current_stage == "READINESS"
    history = documents.list_documents(case_id=cid)
    assert len(history) == 2
    active = [d for d in history if d.is_current_evidence]
    assert len(active) == 1 and active[0].state == "REVIEWED"
    assert active[0].supersedes_document_id == doc.document_id
    assert (
        documents.get_document(case_id=cid, document_id=doc.document_id).superseded_by_document_id
        == active[0].document_id
    )
    assert target.calls == ["search"]


@pytest.mark.parametrize(
    "scenario", [MockIdpScenario.FIELD_MISMATCH, MockIdpScenario.LOW_CONFIDENCE]
)
def test_new_conflicting_or_low_confidence_replacement_is_extracted_once_and_stays_blocked(
    scenario,
):
    _, zero, documents, target, cid, doc, _ = pending_review()
    provider = MockIdpProvider(scenario)
    with patch.object(provider, "process", wraps=provider.process) as extract:
        result = zero.replace_document(
            case_id=cid,
            document_id=doc.document_id,
            expected_document_event_count=len(doc.events),
            display_name="replacement.pdf",
            content_type="application/pdf",
            content=PDF,
            idp_provider=provider,
        )
        assert extract.call_count == 1
    assert result.status == "WAITING_FOR_REVIEW" and result.current_stage == "DOCUMENT"
    assert result.active_exceptions
    assert target.calls == ["search"]
    assert len([d for d in documents.list_documents(case_id=cid) if d.is_current_evidence]) == 1


def test_failed_replacement_retains_failed_active_slot_and_truthful_reupload_checkpoint():
    _, zero, documents, target, cid, doc, _ = pending_review()
    with pytest.raises(ZeroTouchInfrastructureError) as failure:
        zero.replace_document(
            case_id=cid,
            document_id=doc.document_id,
            expected_document_event_count=len(doc.events),
            display_name="failed-replacement.pdf",
            content_type="application/pdf",
            content=PDF,
            idp_provider=MockIdpProvider(MockIdpScenario.PROCESSOR_FAILURE),
        )
    assert failure.value.code == "IDP_PROCESSING_FAILED"
    assert zero.get(case_id=cid).status == "PENDING_INPUTS"
    current = [d for d in documents.list_documents(case_id=cid) if d.is_current_evidence]
    assert len(current) == 1 and current[0].state == "FAILED"
    assert current[0].supersedes_document_id == doc.document_id
    assert target.calls == ["search"]


@pytest.mark.parametrize("action", ["confirmation", "replacement", "replacement_refresh_retry"])
def test_document_action_preserves_failed_sibling_retry_then_continues(action):
    client, zero, documents, target, cid, doc, batch = pending_review()
    with pytest.raises(DocumentProcessingInfrastructureError):
        zero.intake_document(
            case_id=cid,
            display_name="failed-sibling.pdf",
            content_type="application/pdf",
            content=PDF,
            idp_provider=MockIdpProvider(MockIdpScenario.PROCESSOR_FAILURE),
        )
    failed = next(
        item for item in documents.list_documents(case_id=cid)
        if item.is_current_evidence and item.state == "FAILED"
    )
    with patch.object(zero, "_advance_locked", wraps=zero._advance_locked) as advance:
        if action.startswith("replacement"):
            arguments = dict(
                case_id=cid, document_id=doc.document_id,
                expected_document_event_count=len(doc.events), display_name="replacement.pdf",
                content_type="application/pdf", content=PDF,
            )
            if action == "replacement_refresh_retry":
                current = zero.get(case_id=cid)
                with patch.object(
                    zero, "_refresh_replacement_evidence_locked",
                    side_effect=ZeroTouchInfrastructureError(
                        case_id=cid, automation_id=current.automation_id,
                        code="CLM_PERSISTENCE_UNAVAILABLE", message="Checkpoint unavailable.",
                    ),
                ), pytest.raises(ZeroTouchInfrastructureError):
                    zero.replace_document(**arguments)
                previous = zero.get(case_id=cid)
                assert zero.document_refresh_pending(previous)
                result = zero.start(
                    case_id=cid,
                    expected_automation_id=previous.automation_id,
                    expected_automation_version=previous.version,
                    expected_clm_version=zero._clm.get(case_id=cid).version,
                    expected_case_event_count=len(zero._cases.get_case(cid).events),
                )
                validate_automation_transition(previous, result)
                with pytest.raises(ValueError):
                    validate_automation_transition(
                        previous.model_copy(update={"current_stage": AutomationStage.READINESS}),
                        result,
                    )
                with pytest.raises(ValueError):
                    validate_automation_transition(
                        previous, result.model_copy(update={"events": result.events[:-1]}),
                    )
                with pytest.raises(ValueError):
                    validate_automation_transition(
                        previous, result.model_copy(update={"completed_stages": ()}),
                    )
            else:
                result = zero.replace_document(**arguments)
        else:
            current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
            batch["expected_automation_version"] = current["version"]
            batch["expected_case_event_count"] = len(current["case"]["events"])
            decision = batch["documents"][0]["decisions"][0]
            decision["decision"] = "CORRECTED"
            decision["corrected_value"] = "MERLION CIRCULAR LABS PTE. LTD."
            response = client.post(f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch)
            assert response.status_code == 200
            result = zero.get(case_id=cid)
        assert result.status == "PENDING_INPUTS" and result.current_stage == "DOCUMENT"
        advance.assert_not_called()
    assert documents.get_document(case_id=cid, document_id=failed.document_id) == failed
    retry = zero.retry_intake_document(
        case_id=cid,
        failed_document_id=failed.document_id,
        display_name="sibling-retry.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    assert retry.supersedes_document_id == failed.document_id
    current = zero.get(case_id=cid)
    assert current.status == "WAITING_FOR_REVIEW" and current.current_stage == "READINESS"
    assert target.calls == ["search"]
