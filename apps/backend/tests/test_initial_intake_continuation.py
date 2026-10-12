"""Explicit count-bound initial intake cannot be replaced by a document action."""

from unittest.mock import patch
from uuid import UUID

import pytest
from test_phase11_reconciliation import FieldOverrideIdp
from test_zero_touch_orchestration import PDF, build_system

from app.connectors.mock_idp import MockIdpProvider, MockIdpScenario
from app.domain.documents import DocumentFieldKey


def initial_intake(*, failed=False):
    client, zero, documents, target, _ = build_system(require_confirmation=True)
    created = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
    assert created.status_code == 201
    cid = created.json()["case"]["case_id"]
    provider = (
        MockIdpProvider(MockIdpScenario.PROCESSOR_FAILURE) if failed
        else FieldOverrideIdp({DocumentFieldKey.LEGAL_NAME: "OTHER SYNTHETIC NAME"})
    )
    with patch.object(documents, "_idp", provider):
        uploaded = client.post(
            f"/api/clm/zero-touch/cases/{cid}/intake/documents",
            headers={"Content-Type": "application/pdf", "X-Document-Name": "first.pdf"},
            content=PDF,
        )
    assert uploaded.status_code == (503 if failed else 201)
    current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
    records = client.get(f"/api/onboarding/cases/{cid}/documents").json()
    assert current["status"] == "PENDING_INPUTS"
    assert zero.get(case_id=UUID(cid)).started_at is None
    assert len(records) == 1
    return client, zero, documents, target, cid, records[0]


def current_batch(client, cid, document):
    current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
    return {
        "expected_automation_version": current["version"],
        "expected_case_event_count": len(current["case"]["events"]),
        "documents": [{
            "document_id": document["document_id"],
            "expected_event_count": len(document["events"]),
            "source_fingerprint": document["review_source_fingerprint"],
            "decisions": [{
                "field_key": field["field_key"], "decision": "CORRECTED",
                "corrected_value": "MERLION CIRCULAR LABS PTE. LTD.",
            } for field in document["fields"] if field["review_status"] == "PENDING"],
        }],
    }


@pytest.mark.parametrize("action", ["confirmation", "replacement", "retry"])
def test_partial_initial_intake_document_action_never_starts_without_completion(action):
    client, zero, documents, target, cid, document = initial_intake(failed=action == "retry")
    before = zero.get(case_id=UUID(cid))
    with patch.object(zero, "_advance_locked", wraps=zero._advance_locked) as advance:
        if action == "confirmation":
            response = client.post(
                f"/api/clm/zero-touch/cases/{cid}/review-decisions",
                json=current_batch(client, cid, document),
            )
        else:
            route = (
                f"intake/documents/{document['document_id']}/retry" if action == "retry"
                else f"documents/{document['document_id']}/replacement"
            )
            response = client.post(
                f"/api/clm/zero-touch/cases/{cid}/{route}", content=PDF,
                headers={"Content-Type": "application/pdf", "X-Document-Name": "accepted.pdf",
                         "X-Document-Event-Count": str(len(document["events"]))},
            )
        assert response.status_code == (201 if action == "retry" else 200)
        current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        assert current["status"] == "PENDING_INPUTS"
        assert current["current_stage"] == "DOCUMENT"
        assert zero.get(case_id=UUID(cid)).started_at is None
        assert current["version"] == before.version
        assert not any(event.event_type == "ONBOARDING_STARTED"
                       for event in zero.get(case_id=UUID(cid)).events)
        advance.assert_not_called()
    active = [record for record in documents.list_documents(case_id=UUID(cid))
              if record.is_current_evidence]
    assert len(active) == 1 and active[0].state == "REVIEWED"
    assert zero._ownership.get(case_id=UUID(cid)) is None
    assert current["case"]["target_dispatch_confirmation"] is None
    assert current["case"]["goldtier_result"] is None and target.calls == ["search"]
    rejected = client.post(
        f"/api/clm/zero-touch/cases/{cid}/intake/complete",
        json={"expected_document_count": 2},
    )
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "ZERO_TOUCH_INTAKE_INCOMPLETE"
    assert zero.get(case_id=UUID(cid)).version == before.version
    second = client.post(
        f"/api/clm/zero-touch/cases/{cid}/intake/documents", content=PDF,
        headers={"Content-Type": "application/pdf", "X-Document-Name": "second.pdf"},
    )
    assert second.status_code == 201
    with patch.object(zero, "_advance_locked", wraps=zero._advance_locked) as advance:
        completed = client.post(
            f"/api/clm/zero-touch/cases/{cid}/intake/complete",
            json={"expected_document_count": 2},
        )
        assert completed.status_code == 200
        assert completed.json()["status"] == "WAITING_FOR_REVIEW"
        assert completed.json()["current_stage"] == "READINESS"
        assert advance.call_count == 1
        checkpoint = zero.get(case_id=UUID(cid))
        history = documents.list_documents(case_id=UUID(cid))
        repeated = client.post(
            f"/api/clm/zero-touch/cases/{cid}/intake/complete",
            json={"expected_document_count": 2},
        )
        assert repeated.status_code == 200
        assert repeated.json()["version"] == completed.json()["version"]
        assert repeated.json()["status"] == completed.json()["status"]
        assert zero.get(case_id=UUID(cid)) == checkpoint
        assert documents.list_documents(case_id=UUID(cid)) == history
        assert advance.call_count == 1
    assert sum(event.event_type == "ONBOARDING_STARTED"
               for event in zero.get(case_id=UUID(cid)).events) == 1
    assert completed.json()["case"]["target_dispatch_confirmation"] is None
    assert completed.json()["case"]["goldtier_result"] is None and target.calls == ["search"]


def test_initial_resume_cannot_substitute_for_count_bound_completion():
    client, zero, _, target, cid, _ = initial_intake()
    before = zero.get(case_id=UUID(cid))
    response = client.post(f"/api/clm/zero-touch/cases/{cid}/resume")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ZERO_TOUCH_INTAKE_INCOMPLETE"
    assert zero.get(case_id=UUID(cid)) == before
    assert target.calls == ["search"]


def test_explicitly_completed_intake_review_continues_without_another_start():
    client, zero, _, target, cid, _ = initial_intake()
    completed = client.post(
        f"/api/clm/zero-touch/cases/{cid}/intake/complete",
        json={"expected_document_count": 1},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "WAITING_FOR_REVIEW"
    assert completed.json()["current_stage"] == "DOCUMENT"
    assert zero.get(case_id=UUID(cid)).started_at is not None
    document = client.get(f"/api/onboarding/cases/{cid}/documents").json()[0]
    with patch.object(zero, "_advance_locked", wraps=zero._advance_locked) as advance:
        batch = current_batch(client, cid, document)
        confirmed = client.post(f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch)
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "WAITING_FOR_REVIEW"
        assert confirmed.json()["current_stage"] == "READINESS"
        assert advance.call_count == 1
        duplicate = client.post(f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch)
        assert duplicate.status_code == 409 and advance.call_count == 1
    assert target.calls == ["search"]


def test_single_document_compatibility_upload_still_starts_without_intake_complete():
    client, zero, _, target, _ = build_system(require_confirmation=True)
    created = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"}).json()
    cid = created["case"]["case_id"]
    attached = client.post(
        f"/api/clm/zero-touch/cases/{cid}/documents", content=PDF,
        headers={"Content-Type": "application/pdf", "X-Document-Name": "compatible.pdf"},
    )
    assert attached.status_code == 200
    assert attached.json()["status"] == "WAITING_FOR_REVIEW"
    assert attached.json()["current_stage"] == "READINESS"
    assert zero.get(case_id=UUID(cid)).started_at is not None
    assert attached.json()["case"]["target_dispatch_confirmation"] is None
    assert attached.json()["case"]["goldtier_result"] is None and target.calls == ["search"]


def test_initial_failed_replacement_reupload_event_does_not_authorize_auto_start():
    client, zero, documents, target, cid, document = initial_intake()
    with patch.object(documents, "_idp", MockIdpProvider(MockIdpScenario.PROCESSOR_FAILURE)):
        failed = client.post(
            f"/api/clm/zero-touch/cases/{cid}/documents/{document['document_id']}/replacement",
            content=PDF,
            headers={
                "Content-Type": "application/pdf",
                "X-Document-Name": "failed-replacement.pdf",
                "X-Document-Event-Count": str(len(document["events"])),
            },
        )
    assert failed.status_code == 503
    pending = zero.get(case_id=UUID(cid))
    assert (
        pending.started_at is None and pending.events[-1].event_type == "DOCUMENT_REUPLOAD_REQUIRED"
    )
    current = next(
        item for item in documents.list_documents(case_id=UUID(cid)) if item.is_current_evidence
    )
    retried = client.post(
        f"/api/clm/zero-touch/cases/{cid}/intake/documents/{current.document_id}/retry",
        content=PDF,
        headers={"Content-Type": "application/pdf", "X-Document-Name": "initial-retry.pdf"},
    )
    assert retried.status_code == 201
    after = zero.get(case_id=UUID(cid))
    assert after.status == "PENDING_INPUTS" and after.started_at is None
    assert after.events == pending.events and after.version == pending.version
    assert target.calls == ["search"]
