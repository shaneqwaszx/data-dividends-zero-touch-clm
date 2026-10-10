"""Batch confirmation through real owners and HTTP; no external writes."""

from unittest.mock import patch
from uuid import UUID

import pytest
from test_phase11_reconciliation import FieldOverrideIdp
from test_zero_touch_orchestration import PDF, build_system

from app.domain.documents import DocumentFieldKey, ReviewDecision
from app.domain.review_decisions import ReviewDecisionBatch
from app.services.zero_touch_errors import ZeroTouchRequestError


def create_review(*, two_documents=False):
    client, zero, documents, target, _ = build_system(require_confirmation=True)
    created = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"}).json()
    case_id = created["case"]["case_id"]
    for index in range(2 if two_documents else 1):
        zero.intake_document(
            case_id=UUID(case_id),
            display_name=f"synthetic-{index}.pdf",
            content_type="application/pdf",
            content=PDF,
            idp_provider=FieldOverrideIdp({}, confidence={key: 0.6 for key in DocumentFieldKey}),
        )
    zero.start(case_id=UUID(case_id), expected_document_count=2 if two_documents else 1)
    current = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
    records = client.get(f"/api/onboarding/cases/{case_id}/documents").json()
    batch = {
        "expected_automation_version": current["version"],
        "expected_case_event_count": len(current["case"]["events"]),
        "documents": [
            {
                "document_id": doc["document_id"],
                "expected_event_count": len(doc["events"]),
                "source_fingerprint": doc["review_source_fingerprint"],
                "decisions": [
                    {"field_key": f["field_key"], "decision": "ACCEPTED"} for f in doc["fields"]
                ],
            }
            for doc in records
        ],
    }
    return client, zero, documents, target, case_id, batch


def test_four_choices_have_one_save_and_one_reconciliation_boundary():
    client, zero, documents, target, cid, batch = create_review()
    before = list(target.calls)
    with (
        patch.object(documents._repository, "save", wraps=documents._repository.save) as writes,
        patch.object(
            zero._reconciliation, "reconcile_current", wraps=zero._reconciliation.reconcile_current
        ) as reconcile,
        patch.object(zero, "_advance_locked", wraps=zero._advance_locked) as advance,
    ):
        response = client.post(f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch)
        assert response.status_code == 200, response.json()
        assert writes.call_count == 1 and reconcile.call_count == 1 and advance.call_count == 0
    assert response.json()["status"] == "WAITING_FOR_REVIEW"  # Low evidence is never waived.
    final = documents.list_documents(case_id=UUID(cid))[0]
    assert all(f.review_status == "ACCEPTED" and f.confidence == 0.6 for f in final.fields)
    assert len([e for e in final.events if e.event_type == "DOCUMENT_FIELD_ACCEPTED"]) == 4
    assert target.calls == before


def test_same_case_concurrent_group_cannot_duplicate_receipts_or_continue_twice():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    client, zero, documents, target, cid, batch = create_review()
    barrier = Barrier(2)
    before = list(target.calls)

    def confirm():
        barrier.wait(timeout=10)
        return client.post(f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch)

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: confirm(), range(2)))
    assert sorted(response.status_code for response in responses) == [200, 409]
    current = documents.list_documents(case_id=UUID(cid))[0]
    assert len([e for e in current.events if e.event_type == "DOCUMENT_FIELD_ACCEPTED"]) == 4
    assert target.calls == before


def test_http_batch_authorization_and_csrf_reject_before_source_validation():
    import secrets

    from phase13_test_clients import RawTestClient
    from phase13_test_credentials import build_test_authentication_service
    from test_phase13_auth_rbac import _login

    from app.domain.access import SYNTHETIC_USER_PROFILES
    from app.services.authentication import generate_scrypt_password_hash

    # Runtime-generated credentials remain process-local; none is logged or persisted.
    credential = secrets.token_urlsafe(24)
    encoded = generate_scrypt_password_hash(credential)
    authentication = build_test_authentication_service(
        {profile.user_id: encoded for profile in SYNTHETIC_USER_PROFILES}
    )
    from phase13_test_settings import ordinary_test_settings

    from app.main import create_app

    application = create_app(ordinary_test_settings(), authentication_service=authentication)
    creator = RawTestClient(application)
    csrf = _login(creator, "maya-lim", credential)
    created = creator.post(
        "/api/clm/zero-touch/cases", json={"uen": "202400001A"}, headers={"X-CSRF-Token": csrf}
    )
    assert created.status_code == 201
    current = created.json()
    cid = current["case"]["case_id"]
    path = f"/api/clm/zero-touch/cases/{cid}/review-decisions"
    body = {
        "expected_automation_version": current["version"],
        "expected_case_event_count": len(current["case"]["events"]),
        "documents": [
            {
                "document_id": "00000000-0000-4000-8000-000000000001",
                "expected_event_count": 1,
                "source_fingerprint": "0" * 64,
                "decisions": [{"field_key": "legal_name", "decision": "ACCEPTED"}],
            }
        ],
    }
    assert creator.post(path, json={}).status_code == 403
    anonymous = RawTestClient(application)
    assert anonymous.post(path, json={}).status_code == 401
    for actor, expected in [("sophia-ng", 404), ("ethan-tan", 403), ("olivia-koh", 403)]:
        other = RawTestClient(application)
        other_csrf = _login(other, actor, credential)
        assert (
            other.post(path, json=body, headers={"X-CSRF-Token": other_csrf}).status_code
            == expected
        )


@pytest.mark.parametrize("tamper", ["version", "fingerprint", "duplicate", "invalid_correction"])
def test_invalid_group_has_zero_writes(tamper):
    client, zero, documents, target, cid, batch = create_review()
    initial = documents.list_documents(case_id=UUID(cid))
    if tamper == "version":
        batch["expected_automation_version"] += 1
    if tamper == "fingerprint":
        batch["documents"][0]["source_fingerprint"] = "0" * 64
    if tamper == "duplicate":
        batch["documents"][0]["decisions"][1] = batch["documents"][0]["decisions"][0]
    if tamper == "invalid_correction":
        batch["documents"][0]["decisions"][-1].update(decision="CORRECTED", corrected_value=" ")
    before = list(target.calls)
    with patch.object(documents._repository, "save", wraps=documents._repository.save) as writes:
        response = client.post(f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch)
        assert response.status_code in {409, 422}, response.json()
        assert writes.call_count == 0
    assert documents.list_documents(case_id=UUID(cid)) == initial and target.calls == before


def test_later_document_validation_cannot_partially_apply_first():
    client, zero, documents, target, cid, batch = create_review(two_documents=True)
    initial = documents.list_documents(case_id=UUID(cid))
    batch["documents"][1]["source_fingerprint"] = "0" * 64
    response = client.post(f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch)
    assert response.status_code == 409
    assert documents.list_documents(case_id=UUID(cid)) == initial


def test_partial_section_failure_is_stopped_and_exact_group_resumes_without_duplicate_receipts():
    client, zero, documents, target, cid, batch = create_review(two_documents=True)
    saved = documents._repository.save
    count = 0

    def fail_second(record):
        nonlocal count
        count += 1
        if count == 2:
            raise RuntimeError("synthetic persistence fault")
        saved(record)

    before = list(target.calls)
    with (
        patch.object(documents._repository, "save", side_effect=fail_second),
        patch.object(
            zero,
            "_refresh_document_checkpoint_locked",
            wraps=zero._refresh_document_checkpoint_locked,
        ) as checkpoint,
    ):
        failed = client.post(f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch)
        assert failed.status_code == 503 and checkpoint.call_count == 0
    assert zero.get(case_id=UUID(cid)).version == batch["expected_automation_version"]
    resumed = client.post(f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch)
    assert resumed.status_code == 200, resumed.json()
    for doc in documents.list_documents(case_id=UUID(cid)):
        assert len([e for e in doc.events if e.event_type == "DOCUMENT_FIELD_ACCEPTED"]) == 4
    assert target.calls == before


def test_reauthorization_runs_inside_lock_before_any_write():
    client, zero, documents, target, cid, batch = create_review()
    initial = documents.list_documents(case_id=UUID(cid))

    def reject():
        raise ZeroTouchRequestError(code="TEST_REVOKED", message="Authorization revoked.")

    with pytest.raises(ZeroTouchRequestError, match="Authorization revoked"):
        zero.apply_review_decisions(
            case_id=UUID(cid), batch=ReviewDecisionBatch.model_validate(batch), reauthorize=reject
        )
    assert documents.list_documents(case_id=UUID(cid)) == initial


def test_changed_receipt_between_preparation_and_retention_is_not_overwritten():
    from app.services.document_errors import DocumentRequestError

    client, zero, documents, target, cid, batch = create_review()
    group = ReviewDecisionBatch.model_validate(batch).documents[0]
    prepared = documents.prepare_review_group(case_id=UUID(cid), group=group)
    documents.review_field(
        case_id=UUID(cid),
        document_id=group.document_id,
        field_key=DocumentFieldKey.LEGAL_NAME,
        decision=ReviewDecision.REJECTED,
    )
    changed = documents.list_documents(case_id=UUID(cid))
    with pytest.raises(DocumentRequestError) as failure:
        documents.retain_review_group(candidate=prepared)
    assert failure.value.code == "DOCUMENT_REVIEW_STALE"
    assert documents.list_documents(case_id=UUID(cid)) == changed


@pytest.mark.parametrize("correction", [False, True])
def test_same_event_type_cannot_overwrite_a_changed_review_value_or_note(correction):
    from app.services.document_errors import DocumentRequestError

    client, zero, documents, target, cid, batch = create_review()
    batch["documents"][0]["decisions"].sort(key=lambda item: item["field_key"] != "legal_name")
    choice = batch["documents"][0]["decisions"][0]
    choice["decision"] = "CORRECTED" if correction else "ACCEPTED"
    choice["note"] = "First synthetic review note"
    if correction:
        choice["corrected_value"] = "FIRST SYNTHETIC CORRECTION"
    group = ReviewDecisionBatch.model_validate(batch).documents[0]
    fixed_time = (
        documents.get_document(case_id=UUID(cid), document_id=group.document_id)
        .events[-1]
        .timestamp
    )
    with patch.object(documents, "_clock", return_value=fixed_time):
        prepared = documents.prepare_review_group(case_id=UUID(cid), group=group)
        changed = documents.review_field(
            case_id=UUID(cid),
            document_id=group.document_id,
            field_key=DocumentFieldKey.LEGAL_NAME,
            decision=ReviewDecision.CORRECTED if correction else ReviewDecision.ACCEPTED,
            corrected_value="SECOND SYNTHETIC CORRECTION" if correction else None,
            note="Second synthetic review note",
        )
    # The fixed synthetic clock makes audit event prefixes identical despite
    # distinct reviewed values/notes. Event counts alone cannot protect a receipt.
    assert changed.events == prepared.events[: len(changed.events)]
    with pytest.raises(DocumentRequestError) as failure:
        documents.retain_review_group(candidate=prepared)
    assert failure.value.code == "DOCUMENT_REVIEW_STALE"
    assert documents.get_document(case_id=UUID(cid), document_id=group.document_id) == changed


def source_review():
    client, zero, documents, target, _ = build_system(require_confirmation=True)
    created = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"}).json()
    cid = UUID(created["case"]["case_id"])
    zero.attach_document(
        case_id=cid,
        display_name="synthetic-conflicts.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=FieldOverrideIdp(
            {
                DocumentFieldKey.LEGAL_NAME: "OTHER SYNTHETIC COMPANY",
                DocumentFieldKey.REGISTERED_ADDRESS: "18 OTHER SYNTHETIC ROAD, SG",
            }
        ),
    )
    for doc in documents.list_documents(case_id=cid):
        for field in doc.fields:
            if field.review_status == "PENDING":
                zero.review_document_field(
                    case_id=cid,
                    document_id=doc.document_id,
                    field_key=field.field_key,
                    decision=ReviewDecision.ACCEPTED,
                )
    current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
    choices = [
        item for item in current["reconciliation"]["discrepancies"] if item["status"] == "OPEN"
    ]
    assert len(choices) == 2
    batch = {
        "expected_automation_version": current["version"],
        "expected_case_event_count": len(current["case"]["events"]),
        "expected_reconciliation_version": current["reconciliation"]["version"],
        "reconciliation": [
            {
                "discrepancy_id": d["discrepancy_id"],
                "action": "KEEP_REGISTRY_VALUE",
                "evidence_fingerprint": d["evidence_fingerprint"],
            }
            for d in choices
        ],
    }
    return client, zero, documents, target, cid, batch


def test_multiple_source_decisions_use_one_uow_and_stop_at_final_confirmation():
    client, zero, documents, target, cid, batch = source_review()
    before = list(target.calls)
    with (
        patch.object(
            zero._reconciliation._unit_of_work,
            "commit_resolution",
            wraps=zero._reconciliation._unit_of_work.commit_resolution,
        ) as commit,
        patch.object(zero, "_advance_locked", wraps=zero._advance_locked) as advance,
    ):
        response = client.post(f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch)
        assert response.status_code == 200, response.json()
        assert commit.call_count == 1 and advance.call_count == 1
    assert target.calls == before
    assert [e["blocker_code"] for e in response.json()["active_exceptions"]] == [
        "TARGET_CONFIRMATION_REQUIRED"
    ]


@pytest.mark.parametrize("use_document", [False, True])
def test_committed_source_group_repairs_automation_checkpoint_through_explicit_resume(use_document):
    from app.services.zero_touch_errors import ZeroTouchInfrastructureError

    client, zero, documents, target, cid, batch = source_review()
    if use_document:
        legal = next(
            d
            for d in zero._reconciliation.get(case_id=cid).open_discrepancies
            if d.field_name == "legal_name"
        )
        next(
            c for c in batch["reconciliation"] if c["discrepancy_id"] == str(legal.discrepancy_id)
        )["action"] = "USE_DOCUMENT_VALUE"
    before = list(target.calls)
    failure = ZeroTouchInfrastructureError(
        case_id=cid,
        automation_id=zero.get(case_id=cid).automation_id,
        code="TEST_CHECKPOINT_FAILURE",
        message="Synthetic checkpoint retention failure.",
    )
    with patch.object(zero, "_save", side_effect=failure):
        response = client.post(f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch)
    assert response.status_code == 503
    retained = zero._reconciliation.get(case_id=cid)
    assert (
        not retained.open_discrepancies
        and len([d for d in retained.discrepancies if d.decision]) == 2
    )
    assert target.calls == before
    # Source receipts/canonical updates are already retained. Resume reads them; it
    # does not issue hidden duplicate decisions or use a target mutation as repair.
    resumed = client.post(f"/api/clm/zero-touch/cases/{cid}/resume")
    assert resumed.status_code == 200
    # A changed canonical legal name invalidates the prior read-only Search.
    # Its one authorized recheck is required; no target mutation is dispatched.
    assert target.calls == before + (["search"] if use_document else [])
    assert [e["blocker_code"] for e in resumed.json()["active_exceptions"]] == [
        "TARGET_CONFIRMATION_REQUIRED",
    ]
