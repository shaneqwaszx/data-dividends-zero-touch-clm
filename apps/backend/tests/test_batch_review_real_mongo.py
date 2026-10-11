"""Generated disposable Mongo only: native evidence, interrupted group and restart."""

from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from scripts.generate_phase08_synthetic_pdfs import text_pdf
from test_synthetic_company_pack import settings
from test_synthetic_company_pack_real_mongo import MONGO_URI, pytestmark  # noqa: F401
from test_synthetic_company_pack_real_mongo import database as disposable_database
from test_zero_touch_orchestration import RecordingMockGoldTier

from app.connectors.idp import IdpProcessingError
from app.main import create_app
from app.persistence.repositories import MongoDocumentProcessingRepository

database = disposable_database


@pytest.mark.parametrize("failed_sibling", [False, True])
def test_pending_confirmation_replacement_and_restart_preserve_current_slot(
    database, failed_sibling,
):
    config = configured(database)
    target = RecordingMockGoldTier()
    original = text_pdf(
        {
            "Legal Name": "OTHER SYNTHETIC NAME",
            "UEN": "202400099Z",
            "Registered Address": "18 OTHER ROAD, SG",
            "Country": "MY",
        }
    )
    replacement = text_pdf(
        {
            "Legal Name": "MERLION CIRCULAR LABS PTE. LTD.",
            "UEN": "202400001A",
            "Registered Address": "18 INNOVATION WAY, #04-01, 018956, SG",
            "Country": "SG",
            "KYC Customer Type": "Company - Private",
            "Client Segment": "Corporate",
        }
    )
    with (
        patch("app.composition.MockGoldTierConnector", lambda **_: target),
        TestClient(create_app(config)) as client,
    ):
        current = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"}).json()
        cid = current["case"]["case_id"]
        uploaded = client.post(
            f"/api/clm/zero-touch/cases/{cid}/intake/documents",
            content=original,
            headers={"Content-Type": "application/pdf", "X-Document-Name": "original.pdf"},
        )
        assert uploaded.status_code == 201
        doc = client.get(f"/api/onboarding/cases/{cid}/documents").json()[0]
        if failed_sibling:
            with patch(
                "app.connectors.local_pdf_idp.LocalPdfTextIdpProvider.process",
                side_effect=IdpProcessingError(),
            ):
                failed_upload = client.post(
                    f"/api/clm/zero-touch/cases/{cid}/intake/documents",
                    content=replacement,
                    headers={"Content-Type": "application/pdf", "X-Document-Name": "sibling.pdf"},
                )
            assert failed_upload.status_code == 503
            current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        batch = {
            "expected_automation_version": current["version"],
            "expected_case_event_count": len(current["case"]["events"]),
            "documents": [
                {
                    "document_id": doc["document_id"],
                    "expected_event_count": len(doc["events"]),
                    "source_fingerprint": doc["review_source_fingerprint"],
                    "decisions": [
                        {"field_key": f["field_key"], "decision": "REJECTED"} for f in doc["fields"]
                    ],
                }
            ],
        }
        confirmed = client.post(f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch)
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == (
            "PENDING_INPUTS" if failed_sibling else "WAITING_FOR_REVIEW"
        )
        assert confirmed.json()["current_stage"] == "DOCUMENT"
        reviewed = client.get(f"/api/onboarding/cases/{cid}/documents").json()[0]
        edited = client.post(
            f"/api/clm/zero-touch/cases/{cid}/documents/{doc['document_id']}/replacement",
            content=replacement,
            headers={
                "Content-Type": "application/pdf",
                "X-Document-Name": "replacement.pdf",
                "X-Document-Event-Count": str(len(reviewed["events"])),
            },
        )
        assert edited.status_code == 200
        after = edited.json()
        assert after["current_stage"] == ("DOCUMENT" if failed_sibling else "READINESS")
        retained = client.get(f"/api/onboarding/cases/{cid}/documents").json()
        old = next(d for d in retained if d["document_id"] == doc["document_id"])
        assert all(f["review_status"] == "REJECTED" for f in old["fields"])
        active = [d for d in retained if d["superseded_by_document_id"] is None]
        assert len(active) == (2 if failed_sibling else 1)
        assert sum(d["supersedes_document_id"] == doc["document_id"] for d in active) == 1
        assert target.calls == ["search"]
    restarted = RecordingMockGoldTier()
    with (
        patch("app.composition.MockGoldTierConnector", lambda **_: restarted),
        TestClient(create_app(config)) as client,
    ):
        restored = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        assert restored["status"] == after["status"] == (
            "PENDING_INPUTS" if failed_sibling else "WAITING_FOR_REVIEW"
        )
        assert restored["version"] == after["version"]
        assert restored["current_stage"] == ("DOCUMENT" if failed_sibling else "READINESS")
        assert client.get(f"/api/onboarding/cases/{cid}/documents").json() == retained
        assert restored["case"]["target_dispatch_confirmation"] is None
        assert restored["case"]["goldtier_result"] is None and restarted.calls == []
        if failed_sibling:
            failed = next(d for d in retained if d["state"] == "FAILED")
            retried = client.post(
                f"/api/clm/zero-touch/cases/{cid}/intake/documents/{failed['document_id']}/retry",
                content=replacement,
                headers={"Content-Type": "application/pdf", "X-Document-Name": "retry.pdf"},
            )
            assert retried.status_code == 201
            assert retried.json()["supersedes_document_id"] == failed["document_id"]
            final = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
            assert final["status"] == "WAITING_FOR_REVIEW" and final["current_stage"] == "READINESS"
            assert final["case"]["target_dispatch_confirmation"] is None
            assert final["case"]["goldtier_result"] is None and restarted.calls == []


def configured(database):
    return settings(
        acra_connector_mode="mock",
        clm_persistence_mode="mongo",
        mongo_uri=SecretStr(MONGO_URI),
        mongo_database=database,
    )


def prepare(client, *, count=1):
    current = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"}).json()
    cid = current["case"]["case_id"]
    # Valid native PDF, deliberately missing identity labels; no invented accepted value.
    content = text_pdf({}, extra_lines=("LOCAL SYNTHETIC MISSING EVIDENCE ONLY",))
    for index in range(count):
        response = client.post(
            f"/api/clm/zero-touch/cases/{cid}/intake/documents",
            content=content,
            headers={
                "Content-Type": "application/pdf",
                "X-Document-Name": f"synthetic-missing-{index}.pdf",
            },
        )
        assert response.status_code == 201
    current = client.post(
        f"/api/clm/zero-touch/cases/{cid}/intake/complete", json={"expected_document_count": count}
    ).json()
    documents = client.get(f"/api/onboarding/cases/{cid}/documents").json()
    batch = {
        "expected_automation_version": current["version"],
        "expected_case_event_count": len(current["case"]["events"]),
        "documents": [
            {
                "document_id": doc["document_id"],
                "expected_event_count": len(doc["events"]),
                "source_fingerprint": doc["review_source_fingerprint"],
                "decisions": [
                    {"field_key": field["field_key"], "decision": "REJECTED"}
                    for field in doc["fields"]
                ],
            }
            for doc in documents
        ],
    }
    return cid, batch


def test_native_batch_restart_preserves_receipts_blockers_and_no_target_calls(database):
    config = configured(database)
    target = RecordingMockGoldTier()
    with (
        patch("app.composition.MockGoldTierConnector", lambda **_: target),
        TestClient(create_app(config)) as client,
    ):
        cid, batch = prepare(client)
        before = list(target.calls)
        response = client.post(f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch)
        assert response.status_code == 200
        assert response.json()["status"] == "WAITING_FOR_REVIEW"
        documents = client.get(f"/api/onboarding/cases/{cid}/documents").json()
        assert target.calls == before
    restarted = RecordingMockGoldTier()
    with (
        patch("app.composition.MockGoldTierConnector", lambda **_: restarted),
        TestClient(create_app(config)) as client,
    ):
        assert client.get(f"/api/onboarding/cases/{cid}/documents").json() == documents
        current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        assert (
            current["status"] == "WAITING_FOR_REVIEW" and current["case"]["goldtier_result"] is None
        )
        assert restarted.calls == []


def test_partial_document_checkpoints_resume_after_physical_restart(database):
    config = configured(database)
    with TestClient(create_app(config)) as client:
        cid, batch = prepare(client, count=2)
        save = MongoDocumentProcessingRepository.save
        count = 0

        def fail_second(repository, record):
            nonlocal count
            count += 1
            if count == 2:
                raise RuntimeError("synthetic checkpoint failure")
            save(repository, record)

        with patch.object(MongoDocumentProcessingRepository, "save", fail_second):
            response = client.post(f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch)
            assert response.status_code == 503
    target = RecordingMockGoldTier()
    with (
        patch("app.composition.MockGoldTierConnector", lambda **_: target),
        TestClient(create_app(config)) as client,
    ):
        response = client.post(f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch)
        assert response.status_code == 200, response.json()
        docs = client.get(f"/api/onboarding/cases/{cid}/documents").json()
        assert all(
            len(
                [
                    event
                    for event in doc["events"]
                    if event["event_type"] == "DOCUMENT_FIELD_REJECTED"
                ]
            )
            == 4
            for doc in docs
        )
        assert response.json()["status"] == "WAITING_FOR_REVIEW" and target.calls == []


@pytest.mark.parametrize("use_document", [False, True])
@pytest.mark.parametrize("group_size", [1, 2])
def test_source_commit_then_automation_failure_repairs_after_physical_restart(
    database, use_document, group_size
):
    from app.services.zero_touch_errors import ZeroTouchInfrastructureError

    config = configured(database)
    target = RecordingMockGoldTier()
    with (
        patch("app.composition.MockGoldTierConnector", lambda **_: target),
        TestClient(create_app(config)) as client,
    ):
        cid = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"}).json()["case"][
            "case_id"
        ]
        content = text_pdf(
            {
                "Legal Name": "OTHER SYNTHETIC COMPANY",
                "UEN": "202400001A",
                "Registered Address": (
                    "18 OTHER SYNTHETIC ROAD, SG" if group_size == 2
                    else "18 INNOVATION WAY, #04-01, 018956, SG"
                ),
                "Country": "SG",
            }
        )
        uploaded = client.post(
            f"/api/clm/zero-touch/cases/{cid}/intake/documents",
            content=content,
            headers={"Content-Type": "application/pdf", "X-Document-Name": "synthetic-source.pdf"},
        )
        assert uploaded.status_code == 201
        assert (
            client.post(
                f"/api/clm/zero-touch/cases/{cid}/intake/complete",
                json={"expected_document_count": 1},
            ).status_code
            == 200
        )
        current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        choices = [
            d
            for d in current["reconciliation"]["discrepancies"]
            if d["status"] == "OPEN"
        ]
        assert len(choices) == group_size
        batch = {
            "expected_automation_version": current["version"],
            "expected_case_event_count": len(current["case"]["events"]),
            "expected_reconciliation_version": current["reconciliation"]["version"],
            "reconciliation": [
                {
                    "discrepancy_id": choice["discrepancy_id"],
                    "action": (
                        "USE_DOCUMENT_VALUE"
                        if use_document and choice["field_name"] == "legal_name"
                        else "KEEP_REGISTRY_VALUE"
                    ),
                    "evidence_fingerprint": choice["evidence_fingerprint"],
                } for choice in choices
            ],
        }
        before = list(target.calls)
        from app.services.zero_touch_orchestration import ZeroTouchOrchestrator

        def fail_retention(previous, record):
            raise ZeroTouchInfrastructureError(
                case_id=UUID(cid),
                automation_id=record.automation_id,
                code="TEST_CHECKPOINT_FAILURE",
                message="Synthetic checkpoint retention failure.",
            )

        with patch.object(ZeroTouchOrchestrator, "_save", side_effect=fail_retention):
            assert (
                client.post(
                    f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch
                ).status_code
                == 503
            )
        assert target.calls == before
    with (
        patch("app.composition.MockGoldTierConnector", lambda **_: target),
        TestClient(create_app(config)) as restarted,
    ):
        restored = restarted.get(f"/api/clm/zero-touch/cases/{cid}").json()
        assert restored["reconciliation"]["status"] == "RESOLVED"
        source_documents = restarted.get(f"/api/onboarding/cases/{cid}/documents").json()
        assert source_documents[0]["semantic_completion"] == "RECONCILIATION_RESOLVED"
        assert any(field["review_status"] == "PENDING" for field in source_documents[0]["fields"])
        expected_name = (
            "OTHER SYNTHETIC COMPANY" if use_document else "MERLION CIRCULAR LABS PTE. LTD."
        )
        assert restored["case"]["entity"]["legal_name"] == expected_name
        if group_size == 2:
            before_retry = restored["reconciliation"]["version"]
            subset = {**batch, "reconciliation": batch["reconciliation"][:1]}
            assert restarted.post(
                f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=subset
            ).status_code == 409
            after_retry = restarted.get(f"/api/clm/zero-touch/cases/{cid}").json()
            assert after_retry["reconciliation"]["version"] == before_retry
            assert after_retry["version"] == restored["version"]
            if not use_document:
                repaired = restarted.post(
                    f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=batch
                )
                assert repaired.status_code == 200
                assert [e["blocker_code"] for e in repaired.json()["active_exceptions"]] == [
                    "TARGET_CONFIRMATION_REQUIRED"
                ]
        resumed = restarted.post(f"/api/clm/zero-touch/cases/{cid}/resume")
        assert resumed.status_code == 200
        assert [e["blocker_code"] for e in resumed.json()["active_exceptions"]] == [
            "TARGET_CONFIRMATION_REQUIRED"
        ]
        assert not any(call in {"shell", "policy", "amend"} for call in target.calls)
