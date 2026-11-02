"""Current-main regression for retained manual ownership checkpoint alignment."""

from decimal import Decimal
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from test_zero_touch_orchestration import PDF, build_system, policy_rebind_snapshots

from app.domain.access import TeamId


def prepare_case():
    _, policy = policy_rebind_snapshots()
    client, zero, documents, target, _ = build_system(
        require_confirmation=True,
        policy_snapshot_provider=lambda: policy,
    )
    created = zero.create_case(
        "202400001A",
        "SG",
        legal_name="MERLION CIRCULAR LABS PTE. LTD.",
        team_id=TeamId.TEAM_A,
        created_by_actor_id="maya-lim",
    )
    waiting = zero.attach_document(
        case_id=created.case_id,
        display_name="synthetic-ownership.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    case = zero._cases.get_case(created.case_id)
    waiting = zero.bind_target_classification(
        case_id=created.case_id,
        kyc_customer_type="Company - Private",
        client_segment="Corporate",
        expected_automation_version=waiting.version,
        expected_case_event_count=len(case.events),
        actor_id="maya-lim",
    )
    assert waiting.current_stage == "READINESS"
    assert target.calls == ["search"]
    return client, zero, documents, target, created.case_id


def declaration_payload(summary, ownership, document, *, complete=True, percent="62.5"):
    parties = [
        {
            "party_id": "ROOT_ENTITY",
            "display_name": "Synthetic client",
            "party_type": "LEGAL_ENTITY",
            "registration_number": "202400001A",
            "country": "SG",
        },
        {
            "party_id": "HOLDING_ENTITY",
            "display_name": "Synthetic holding company",
            "party_type": "LEGAL_ENTITY",
            "country": "SG",
        },
        {
            "party_id": "PERSON_B",
            "display_name": "Synthetic direct owner",
            "party_type": "NATURAL_PERSON",
            "country": "SG",
        },
    ]
    relationships = [
        {
            "relationship_id": "DIRECT_A",
            "parent_party_id": "ROOT_ENTITY",
            "child_party_id": "HOLDING_ENTITY",
            "ownership_percent": percent,
        },
        {
            "relationship_id": "DIRECT_B",
            "parent_party_id": "ROOT_ENTITY",
            "child_party_id": "PERSON_B",
            "ownership_percent": "37.5" if percent == "62.5" else "40",
        },
    ]
    if complete:
        # This edge is explicitly declared synthetic evidence, never inferred.
        parties.append(
            {
                "party_id": "PERSON_C",
                "display_name": "Synthetic indirect owner",
                "party_type": "NATURAL_PERSON",
                "country": "SG",
            }
        )
        relationships.append(
            {
                "relationship_id": "HOLDING_EDGE",
                "parent_party_id": "HOLDING_ENTITY",
                "child_party_id": "PERSON_C",
                "ownership_percent": "100",
            }
        )
    return {
        "root_registration_number": "202400001A",
        "evidence_document_id": document["document_id"],
        "evidence_document_version": len(document["events"]),
        "as_of_date": "2026-10-04",
        "rationale": None,
        "root_party_id": "ROOT_ENTITY",
        "parties": parties,
        "relationships": relationships,
        "observed_document_versions": ownership["document_bindings"],
        "selected_observation_ids": [],
        "source_selection": "USER_SUPPLIED_DECLARATION",
        "expected_automation_version": summary["version"],
        "expected_ownership_version": ownership["version"],
        "expected_case_event_count": len(summary["case"]["events"]),
    }


def current_payload(client, case_id, **options):
    summary = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
    ownership = client.get(f"/api/onboarding/cases/{case_id}/ownership").json()
    documents = client.get(f"/api/onboarding/cases/{case_id}/documents").json()
    document = next(
        item
        for item in documents
        if not item["superseded_by_document_id"] and item["state"] == "REVIEWED"
    )
    return declaration_payload(summary, ownership, document, **options)


def test_retained_review_required_graph_reconciles_current_checkpoint_before_409():
    client, zero, documents, target, case_id = prepare_case()
    endpoint = f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence"
    first = client.post(endpoint, json=current_payload(client, case_id))
    assert first.status_code == 200, first.text
    before = first.json()
    old_confirmation = next(
        e
        for e in before["active_exceptions"]
        if e["exception_type"] == "TARGET_CONFIRMATION_REQUIRED"
    )
    incomplete = current_payload(client, case_id, complete=False, percent="60")
    response = client.post(endpoint, json=incomplete)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ZERO_TOUCH_MANUAL_OWNERSHIP_REVIEW_REQUIRED"
    retained = zero._ownership.get(case_id=case_id)
    assert retained.state == "REVIEW_REQUIRED"
    # No corporate discovery is composed here, so the UEN-less holder is only an incomplete
    # legal entity. With discovery (test_final_review_editing_real_mongo) it is also an
    # unresolved corporate branch (UNVERIFIED_UEN).
    assert retained.discovery is None
    assert {issue.code.value for issue in retained.issues} == {"INCOMPLETE_LEGAL_ENTITY"}
    assert retained.manual_review_receipt is not None
    assert retained.manual_review_receipt.actor_id == "maya-lim"
    assert retained.manual_review_receipt.rationale is None
    assert len(retained.parties) == 3 and len(retained.relationships) == 2
    assert str(retained.relationships[0].ownership_percent) == "60"
    assert retained.prior_analyses[-1].analysis_id == UUID(
        before["ownership_recovery"]["analysis_id"]
    )
    current = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
    assert "OWNERSHIP_REVIEW_REQUIRED" in current["clm"]["readiness"]["blockers"]
    assert current["case"]["target_dispatch_confirmation"] is None
    assert current["clm"]["submission"] is None
    assert all(
        item["status"] == "NOT_ATTEMPTED"
        for item in current["target_operations"]
        if item["operation"] != "SEARCH"
    )
    assert target.calls == ["search"]
    # This is the current-main RED: persisted graph and CLM agree, automation does not.
    assert current["current_stage"] == "OWNERSHIP"
    assert current["version"] > before["version"]
    assert "OWNERSHIP" not in current["completed_stages"]
    assert "READINESS" not in current["completed_stages"]
    assert [e["blocker_code"] for e in current["active_exceptions"]] == ["OWNERSHIP_INCOMPLETE"]
    assert old_confirmation["exception_id"] in {
        e["exception_id"] for e in current["historical_exceptions"]
    }
    cancelled = next(
        e
        for e in current["historical_exceptions"]
        if e["exception_id"] == old_confirmation["exception_id"]
    )
    assert cancelled["status"] == "CANCELLED"
    assert cancelled["evidence_version"] == old_confirmation["evidence_version"]
    assert current["metrics"]["exceptions_resolved"] == before["metrics"]["exceptions_resolved"]
    assert current["active_exceptions"][0]["status"] == "OPEN"
    assert len(current["interventions"]) == 1
    intervention = current["interventions"][0]
    assert intervention["owning_stage"] == "OWNERSHIP"
    assert intervention["evidence_actions"][0] == {
        "target": "OWNERSHIP_DETAILS",
        "label": "Add structured ownership details",
    }
    assert current["ownership_recovery"]["manual_evidence_action"] == "MANUAL_OWNERSHIP_EVIDENCE"


def test_corrected_complete_graph_requires_fresh_review_and_preserves_classification():
    client, zero, documents, target, case_id = prepare_case()
    endpoint = f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence"
    first = client.post(endpoint, json=current_payload(client, case_id))
    assert first.status_code == 200
    before = first.json()
    incomplete = current_payload(client, case_id, complete=False, percent="60")
    assert client.post(endpoint, json=incomplete).status_code == 409
    blocked = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
    rejected_confirmation = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
        json={
            "expected_automation_version": before["version"],
            "expected_clm_version": before["clm"]["version"],
            "expected_case_event_count": len(before["case"]["events"]),
        },
    )
    assert rejected_confirmation.status_code == 409
    assert target.calls == ["search"]
    corrected = client.post(endpoint, json=current_payload(client, case_id, percent="60"))
    assert corrected.status_code == 200, corrected.text
    recovered = corrected.json()
    assert recovered["current_stage"] == "READINESS"
    assert recovered["clm"]["readiness"]["blockers"] == []
    assert [e["blocker_code"] for e in recovered["active_exceptions"]] == [
        "TARGET_CONFIRMATION_REQUIRED"
    ]
    assert recovered["active_exceptions"][0]["evidence_version"] == (
        f"target-confirmation:{recovered['clm']['version']}:{len(recovered['case']['events'])}"
    )
    assert (
        recovered["active_exceptions"][0]["exception_id"]
        != before["active_exceptions"][0]["exception_id"]
    )
    for name in ["kyc_customer_type", "client_segment"]:
        assert recovered["target_classification"][name] == before["target_classification"][name]
    assert recovered["case"]["initial_identity"] == before["case"]["initial_identity"]
    assert recovered["case"]["target_dispatch_confirmation"] is None
    ownership = zero._ownership.get(case_id=case_id)
    assert ownership.state == "ANALYZED"
    assert ownership.root_party_id == "ROOT_ENTITY"
    assert len(ownership.relationships) == 3
    assert {c.aggregated_ownership_percent for c in ownership.candidates} == {
        Decimal(60),
        Decimal(40),
    }
    assert any(p.state == "REVIEW_REQUIRED" for p in ownership.prior_analyses)
    assert any(
        e["exception_id"] == blocked["active_exceptions"][0]["exception_id"]
        for e in recovered["historical_exceptions"]
    )
    assert client.post(endpoint, json=incomplete).status_code == 409
    assert target.calls == ["search"]


@pytest.mark.parametrize(
    "version",
    [
        "expected_automation_version",
        "expected_ownership_version",
        "expected_case_event_count",
    ],
)
def test_stale_manual_replacement_does_not_change_any_retained_checkpoint(version):
    client, zero, documents, target, case_id = prepare_case()
    payload = current_payload(client, case_id, complete=False, percent="60")
    before = zero.get(case_id=case_id)
    ownership = zero._ownership.get(case_id=case_id)
    case = zero._cases.get_case(case_id)
    payload[version] -= 1
    rejected = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence", json=payload
    )
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "ZERO_TOUCH_MANUAL_OWNERSHIP_STALE"
    assert zero.get(case_id=case_id) == before
    assert zero._ownership.get(case_id=case_id) == ownership
    assert zero._cases.get_case(case_id) == case
    assert target.calls == ["search"]


@pytest.mark.parametrize("missing", [False, True])
def test_missing_or_stale_support_document_rejects_before_graph_or_checkpoint_write(missing):
    client, zero, documents, target, case_id = prepare_case()
    payload = current_payload(client, case_id, complete=False, percent="60")
    before = zero.get(case_id=case_id)
    ownership = zero._ownership.get(case_id=case_id)
    if missing:
        payload["evidence_document_id"] = str(uuid4())
    else:
        payload["evidence_document_version"] += 1
    rejected = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence", json=payload
    )
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == (
        "MANUAL_OWNERSHIP_DOCUMENT_NOT_FOUND" if missing else "MANUAL_OWNERSHIP_DOCUMENT_STALE"
    )
    assert zero.get(case_id=case_id) == before
    assert zero._ownership.get(case_id=case_id) == ownership
    assert target.calls == ["search"]


def test_valid_ownership_preserves_independent_document_conflict():
    from app.connectors.mock_idp import MockIdpProvider, MockIdpScenario

    client, zero, documents, target, case_id = prepare_case()
    support = documents.create_document(
        case_id=case_id,
        display_name="independent-support.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    documents.auto_confirm_document(case_id=case_id, document_id=support.document_id)
    original = documents.list_documents(case_id=case_id)[0]
    before = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
    zero.replace_document(
        case_id=case_id,
        document_id=original.document_id,
        expected_document_event_count=len(original.events),
        expected_automation_version=before["version"],
        expected_clm_version=before["clm"]["version"],
        expected_case_event_count=len(before["case"]["events"]),
        display_name="conflicting-current.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
    )
    blocked = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
    conflict_ids = {
        e["exception_id"] for e in blocked["active_exceptions"] if e["stage"] == "DOCUMENT"
    }
    assert conflict_ids
    edited = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
        json=current_payload(client, case_id, percent="60"),
    )
    assert edited.status_code == 200, edited.text
    after = edited.json()
    assert after["current_stage"] == "DOCUMENT"
    assert conflict_ids <= {e["exception_id"] for e in after["active_exceptions"]}
    assert "DOCUMENT_REVIEW_INCOMPLETE" in after["clm"]["readiness"]["blockers"]
    assert not any(
        e["blocker_code"] == "TARGET_CONFIRMATION_REQUIRED" for e in after["active_exceptions"]
    )
    assert target.calls == ["search"]


def test_reauthorization_denial_precedes_any_manual_replacement():
    from app.main import ManualOwnershipEvidenceRequest

    client, zero, documents, target, case_id = prepare_case()
    payload = current_payload(client, case_id, complete=False, percent="60")
    declaration = ManualOwnershipEvidenceRequest.model_validate(payload).declaration_for(case_id)
    before = zero._ownership.get(case_id=case_id)

    def deny():
        raise PermissionError("Current evidence authority revoked")

    with patch.object(zero._ownership, "replace_review_required_source") as replace:
        with pytest.raises(PermissionError):
            zero.submit_manual_ownership_evidence(
                case_id=case_id,
                actor_id="maya-lim",
                declaration=declaration,
                expected_automation_version=payload["expected_automation_version"],
                expected_ownership_version=payload["expected_ownership_version"],
                expected_case_event_count=payload["expected_case_event_count"],
                reauthorize=deny,
            )
        replace.assert_not_called()
    assert zero._ownership.get(case_id=case_id) == before
    assert target.calls == ["search"]


@pytest.mark.parametrize("conflict", [False, True])
def test_rejected_automation_checkpoint_is_safe_and_requires_explicit_fresh_recovery(conflict):
    from app.services.zero_touch_repository import ZeroTouchRepositoryConflictError

    client, zero, documents, target, case_id = prepare_case()
    payload = current_payload(client, case_id, complete=False, percent="60")
    before = zero.get(case_id=case_id)
    error = ZeroTouchRepositoryConflictError() if conflict else ValueError("PRIVATE_REJECTION")
    with patch.object(zero._repository, "save", side_effect=error):
        rejected = client.post(
            f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
            json=payload,
        )
    assert rejected.status_code == (409 if conflict else 503)
    assert rejected.json()["detail"]["code"] == (
        "ZERO_TOUCH_AUTOMATION_CONFLICT" if conflict else "ZERO_TOUCH_TRANSITION_REJECTED"
    )
    assert "PRIVATE_REJECTION" not in rejected.text
    assert zero.get(case_id=case_id) == before
    retained = zero._ownership.get(case_id=case_id)
    assert retained.state == "REVIEW_REQUIRED"
    assert retained.manual_review_receipt is not None
    assert (
        "OWNERSHIP_REVIEW_REQUIRED"
        in client.get(f"/api/clm/zero-touch/cases/{case_id}").json()["clm"]["readiness"]["blockers"]
    )
    assert target.calls == ["search"]
    # Deliberate fresh-version correction; neither route nor view retries a write.
    recovered = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
        json=current_payload(client, case_id, percent="60"),
    )
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["clm"]["readiness"]["blockers"] == []
    assert target.calls == ["search"]


@pytest.mark.parametrize("conflict", [False, True])
def test_clm_refresh_failure_retains_evidence_and_returns_typed_safe_error(conflict):
    from app.services.clm_errors import ClmInfrastructureError
    from app.services.clm_repository import ClmRepositoryConflictError

    client, zero, documents, target, case_id = prepare_case()
    payload = current_payload(client, case_id, complete=False, percent="60")
    before = zero.get(case_id=case_id)
    clm = zero._clm.get(case_id=case_id)
    if conflict:
        failure = ClmRepositoryConflictError()
        failed_port = patch.object(zero._clm._repository, "save", side_effect=failure)
        code = "CLM_ORCHESTRATION_CONFLICT"
    else:
        # Inject the real trusted infrastructure type at its service port. This
        # existing code is test data; no target execution or finalization occurred.
        code = "CLM_FINALIZATION_RETRY_REQUIRED"
        failure = ClmInfrastructureError(
            case_id=case_id,
            orchestration_id=clm.orchestration_id,
            correlation_id=clm.correlation_id,
            code=code,
            message="The synthetic CLM checkpoint is unavailable.",
        )
        failed_port = patch.object(
            zero._clm, "refresh_pre_submission_evidence", side_effect=failure
        )
    with (
        failed_port as refresh,
        patch.object(zero._repository, "save", wraps=zero._repository.save) as automation_save,
    ):
        rejected = client.post(
            f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
            json=payload,
        )
    assert rejected.status_code == (409 if conflict else 503)
    assert rejected.json()["detail"]["code"] == code
    assert refresh.call_count == 1
    automation_save.assert_not_called()
    assert zero.get(case_id=case_id) == before
    retained = zero._ownership.get(case_id=case_id)
    assert retained.state == "REVIEW_REQUIRED"
    assert retained.manual_review_receipt is not None
    assert retained.manual_review_receipt.rationale is None
    current = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
    assert "OWNERSHIP_REVIEW_REQUIRED" in current["clm"]["readiness"]["blockers"]
    assert current["case"]["target_dispatch_confirmation"] is None
    assert current["clm"]["submission"] is None
    assert target.calls == ["search"]
    recovered = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
        json=current_payload(client, case_id, percent="60"),
    )
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["clm"]["readiness"]["blockers"] == []
    assert recovered.json()["active_exceptions"][0]["blocker_code"] == (
        "TARGET_CONFIRMATION_REQUIRED"
    )
    assert target.calls == ["search"]


@pytest.mark.parametrize("complete", [False, True])
def test_confirmation_history_cancellation_is_limited_to_retained_incomplete_409(complete):
    client, zero, documents, target, case_id = prepare_case()
    endpoint = f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence"
    before = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
    old = next(
        e
        for e in before["active_exceptions"]
        if e["blocker_code"] == "TARGET_CONFIRMATION_REQUIRED"
    )
    response = client.post(
        endpoint, json=current_payload(client, case_id, complete=complete, percent="60")
    )
    assert response.status_code == (200 if complete else 409)
    after = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
    historical = next(
        e for e in after["historical_exceptions"] if e["exception_id"] == old["exception_id"]
    )
    # Successful complete200 retains its published semantics; only retained409 cancels.
    assert historical["status"] == ("RESOLVED" if complete else "CANCELLED")
    assert historical["evidence_version"] == old["evidence_version"]
    assert historical["created_at"] == old["created_at"]
    assert after["metrics"]["exceptions_resolved"] == before["metrics"]["exceptions_resolved"]
    assert after["case"]["target_dispatch_confirmation"] is None
    assert after["clm"]["submission"] is None
    assert not any(e.code == "TARGET_DISPATCH_CONFIRMED" for e in zero.get(case_id=case_id).events)
    assert all(
        op["status"] == "NOT_ATTEMPTED"
        for op in after["target_operations"]
        if op["operation"] != "SEARCH"
    )
    assert target.calls == ["search"]
    if complete:
        assert after["current_stage"] == "READINESS"
        assert after["active_exceptions"][0]["blocker_code"] == "TARGET_CONFIRMATION_REQUIRED"
        return
    current_owner = after["active_exceptions"][0]
    assert current_owner["blocker_code"] == "OWNERSHIP_INCOMPLETE"
    assert current_owner["status"] == "OPEN"
    assert after["current_stage"] == "OWNERSHIP"
    assert "OWNERSHIP_REVIEW_REQUIRED" in after["clm"]["readiness"]["blockers"]
    stale_confirmation = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
        json={
            "expected_automation_version": before["version"],
            "expected_clm_version": before["clm"]["version"],
            "expected_case_event_count": len(before["case"]["events"]),
        },
    )
    assert stale_confirmation.status_code == 409
    corrected = client.post(endpoint, json=current_payload(client, case_id, percent="60"))
    assert corrected.status_code == 200
    recovered = corrected.json()
    resolved_owner = next(
        e
        for e in recovered["historical_exceptions"]
        if e["exception_id"] == current_owner["exception_id"]
    )
    assert resolved_owner["status"] == "RESOLVED"
    assert (
        recovered["metrics"]["exceptions_resolved"] == after["metrics"]["exceptions_resolved"] + 1
    )
    assert (
        next(
            e
            for e in recovered["historical_exceptions"]
            if e["exception_id"] == old["exception_id"]
        )["status"]
        == "CANCELLED"
    )
    assert recovered["current_stage"] == "READINESS"
    assert recovered["clm"]["readiness"]["blockers"] == []
    fresh = recovered["active_exceptions"][0]
    assert fresh["blocker_code"] == "TARGET_CONFIRMATION_REQUIRED" and fresh["status"] == "OPEN"
    assert fresh["exception_id"] != old["exception_id"]
    assert recovered["case"]["target_dispatch_confirmation"] is None
    assert recovered["clm"]["submission"] is None
    assert target.calls == ["search"]
