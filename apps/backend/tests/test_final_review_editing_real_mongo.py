"""Final-review revision checkpoint, source lineage and physical restart guards."""

from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from scripts.generate_phase08_synthetic_pdfs import text_pdf
from test_batch_review_real_mongo import configured
from test_final_review_editing import confirmation_versions
from test_synthetic_company_pack_real_mongo import database as disposable_database
from test_synthetic_company_pack_real_mongo import pytestmark  # noqa: F401
from test_zero_touch_orchestration import RecordingMockGoldTier

from app.main import create_app
from app.services.clm_errors import ClmInfrastructureError
from app.services.clm_orchestration import ClmOrchestrationService

database = disposable_database
FIELDS = {
    "Legal Name": "MERLION CIRCULAR LABS PTE. LTD.",
    "UEN": "202400001A",
    "Registered Address": "18 INNOVATION WAY, #04-01, 018956, SG",
    "Country": "SG",
    "KYC Customer Type": "Company - Private",
    "Client Segment": "Corporate",
}


def prepare_final(client):
    created = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"}).json()
    cid = created["case"]["case_id"]
    uploaded = client.post(
        f"/api/clm/zero-touch/cases/{cid}/intake/documents",
        content=text_pdf(FIELDS),
        headers={"Content-Type": "application/pdf", "X-Document-Name": "physical-original.pdf"},
    )
    assert uploaded.status_code == 201
    started = client.post(
        f"/api/clm/zero-touch/cases/{cid}/intake/complete", json={"expected_document_count": 1}
    )
    assert started.status_code == 200
    before = started.json()
    assert [e["blocker_code"] for e in before["active_exceptions"]] == [
        "TARGET_CONFIRMATION_REQUIRED"
    ]
    document = client.get(f"/api/onboarding/cases/{cid}/documents").json()[0]
    return cid, before, document


def replacement(client, cid, before, document):
    return client.post(
        f"/api/clm/zero-touch/cases/{cid}/documents/{document['document_id']}/replacement",
        content=text_pdf(FIELDS | {"Client Segment": "Commercial BB (Business Banking)"}),
        headers={
            "Content-Type": "application/pdf",
            "X-Document-Name": "physical-revised.pdf",
            "X-Document-Event-Count": str(len(document["events"])),
            "X-Automation-Version": str(before["version"]),
            "X-Clm-Version": str(before["clm"]["version"]),
            "X-Case-Event-Count": str(len(before["case"]["events"])),
        },
    )


def test_physical_final_document_edit_retains_fresh_classification_and_restart_guard(database):
    config = configured(database)
    target = RecordingMockGoldTier()
    with (
        patch("app.composition.MockGoldTierConnector", lambda **_: target),
        TestClient(create_app(config)) as client,
    ):
        cid, before, document = prepare_final(client)
        edited = replacement(client, cid, before, document)
        assert edited.status_code == 200, edited.text
        current = edited.json()
        assert (
            current["target_classification"]["client_segment"]["selected_value"]
            == "Commercial BB (Business Banking)"
        )
        assert current["clm"]["version"] > before["clm"]["version"]
        assert target.calls == ["search"]
    restarted = RecordingMockGoldTier()
    with (
        patch("app.composition.MockGoldTierConnector", lambda **_: restarted),
        TestClient(create_app(config)) as client,
    ):
        current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        documents = client.get(f"/api/onboarding/cases/{cid}/documents").json()
        assert (
            len(documents) == 2
            and len([d for d in documents if not d["superseded_by_document_id"]]) == 1
        )
        assert current["status"] == "WAITING_FOR_REVIEW"
        assert (
            current["target_classification"]["client_segment"]["selection"]["source"] == "DOCUMENT"
        )
        stale = client.post(
            f"/api/clm/zero-touch/cases/{cid}/target-confirmation",
            json=confirmation_versions(before),
        )
        assert stale.status_code == 409 and restarted.calls == []
        assert (
            client.post(
                f"/api/clm/zero-touch/cases/{cid}/target-confirmation",
                json=confirmation_versions(current),
            ).json()["status"]
            == "COMPLETED"
        )
        assert restarted.calls.count("shell") == 1
        assert restarted.calls.count("policy") == 1
        assert restarted.calls.count("amend") == 1


def test_physical_partial_preview_refresh_restarts_from_document_without_stale_confirmation(
    database,
):
    config = configured(database)
    target = RecordingMockGoldTier()
    with (
        patch("app.composition.MockGoldTierConnector", lambda **_: target),
        TestClient(create_app(config)) as client,
    ):
        cid, before, document = prepare_final(client)
        with patch.object(
            ClmOrchestrationService,
            "refresh_pre_submission_evidence",
            side_effect=ClmInfrastructureError(
                case_id=UUID(cid),
                orchestration_id=uuid4(),
                correlation_id=uuid4(),
                code="CLM_PERSISTENCE_UNAVAILABLE",
                message="Current review checkpoint is unavailable.",
            ),
        ):
            failed = replacement(client, cid, before, document)
        assert failed.status_code == 503
        current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        assert all(
            e["blocker_code"] != "TARGET_CONFIRMATION_REQUIRED"
            for e in current["active_exceptions"]
        )
        assert target.calls == ["search"]
    restarted = RecordingMockGoldTier()
    with (
        patch("app.composition.MockGoldTierConnector", lambda **_: restarted),
        TestClient(create_app(config)) as client,
    ):
        resumed = client.post(f"/api/clm/zero-touch/cases/{cid}/resume")
        assert resumed.status_code == 200
        current = resumed.json()
        assert current["status"] == "WAITING_FOR_REVIEW" and current["current_stage"] == "READINESS"
        assert (
            current["target_classification"]["client_segment"]["selected_value"]
            == "Commercial BB (Business Banking)"
        )
        assert current["clm"]["version"] > before["clm"]["version"]
        assert restarted.calls == []
        assert (
            client.post(
                f"/api/clm/zero-touch/cases/{cid}/target-confirmation",
                json=confirmation_versions(before),
            ).status_code
            == 409
        )
        assert restarted.calls == []
