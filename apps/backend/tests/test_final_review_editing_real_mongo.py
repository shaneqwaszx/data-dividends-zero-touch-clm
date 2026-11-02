"""Final-review revision checkpoint, source lineage and physical restart guards."""

from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from scripts.generate_phase08_synthetic_pdfs import text_pdf
from test_batch_review_real_mongo import configured
from test_document_refresh_recovery import assert_retained_history, recovery_headers
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
        retained = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        assert retained["document_refresh_recovery"] == {"can_resume": True}
        history = client.get(f"/api/onboarding/cases/{cid}/documents").json()
        assert len(history) == 2
        assert client.post(f"/api/clm/zero-touch/cases/{cid}/resume").status_code == 409
        resumed = client.post(
            f"/api/clm/zero-touch/cases/{cid}/resume", headers=recovery_headers(retained)
        )
        assert resumed.status_code == 200
        current = resumed.json()
        assert current["status"] == "WAITING_FOR_REVIEW" and current["current_stage"] == "READINESS"
        assert (
            current["target_classification"]["client_segment"]["selected_value"]
            == "Commercial BB (Business Banking)"
        )
        assert current["clm"]["version"] > before["clm"]["version"]
        assert restarted.calls == []
        assert_retained_history(
            history, client.get(f"/api/onboarding/cases/{cid}/documents").json()
        )
        assert current["document_refresh_recovery"] is None
        assert client.post(
            f"/api/clm/zero-touch/cases/{cid}/resume", headers=recovery_headers(current)
        ).status_code == 200
        assert restarted.calls == []
        assert (
            client.post(
                f"/api/clm/zero-touch/cases/{cid}/target-confirmation",
                json=confirmation_versions(before),
            ).status_code
            == 409
        )
        assert restarted.calls == []


def test_physical_am18_retained_409_checkpoint_survives_restart_and_stale_writer(database):
    from test_am18_ownership_checkpoint import current_payload

    config = configured(database)
    target = RecordingMockGoldTier()
    with (
        patch("app.composition.MockGoldTierConnector", lambda **_: target),
        TestClient(create_app(config)) as client,
    ):
        cid, _, _ = prepare_final(client)
        endpoint = f"/api/clm/zero-touch/cases/{cid}/manual-ownership-evidence"
        complete = client.post(endpoint, json=current_payload(client, cid))
        assert complete.status_code == 200, complete.text
        before = complete.json()
        obsolete = before["active_exceptions"][0]["exception_id"]
        incomplete = current_payload(client, cid, complete=False, percent="60")
        retained_error = client.post(endpoint, json=incomplete)
        assert retained_error.status_code == 409
        assert retained_error.json()["detail"]["code"] == (
            "ZERO_TOUCH_MANUAL_OWNERSHIP_REVIEW_REQUIRED"
        )
        blocked = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        graph = client.get(f"/api/onboarding/cases/{cid}/ownership").json()
        assert graph["state"] == "REVIEW_REQUIRED"
        # D-112: this app composes official corporate discovery, which visits the declared
        # corporate holder that has no owners. The holder has no UEN, so no registry call is
        # made: discovery records it UNVERIFIED_UEN, an unresolved branch, and the graph also
        # reports CORPORATE_OWNERSHIP_UNRESOLVED. (The in-memory twin in
        # test_am18_ownership_checkpoint composes no discovery, so it has only the first code.)
        assert {issue["code"] for issue in graph["issues"]} == {
            "INCOMPLETE_LEGAL_ENTITY",
            "CORPORATE_OWNERSHIP_UNRESOLVED",
        }
        assert [
            (item["party_id"], item["outcome"]) for item in graph["discovery"]["records"]
        ] == [("HOLDING_ENTITY", "UNVERIFIED_UEN")]
        assert graph["manual_review_receipt"]["rationale"] is None
        assert blocked["current_stage"] == "OWNERSHIP"
        assert blocked["version"] > before["version"]
        assert blocked["clm"]["version"] > before["clm"]["version"]
        assert [e["blocker_code"] for e in blocked["active_exceptions"]] == ["OWNERSHIP_INCOMPLETE"]
        assert obsolete in {e["exception_id"] for e in blocked["historical_exceptions"]}
        cancelled = next(
            e for e in blocked["historical_exceptions"] if e["exception_id"] == obsolete
        )
        assert cancelled["status"] == "CANCELLED"
        assert blocked["metrics"]["exceptions_resolved"] == before["metrics"]["exceptions_resolved"]
        assert blocked["active_exceptions"][0]["status"] == "OPEN"
        assert "OWNERSHIP_REVIEW_REQUIRED" in blocked["clm"]["readiness"]["blockers"]
        assert target.calls == ["search"]
    restarted_target = RecordingMockGoldTier()
    with (
        patch("app.composition.MockGoldTierConnector", lambda **_: restarted_target),
        TestClient(create_app(config)) as restarted,
    ):
        restored = restarted.get(f"/api/clm/zero-touch/cases/{cid}").json()
        restored_graph = restarted.get(f"/api/onboarding/cases/{cid}/ownership").json()
        assert restored_graph == graph
        for key in [
            "version", "current_stage", "completed_stages", "active_exceptions",
            "historical_exceptions", "ownership_recovery",
        ]:
            assert restored[key] == blocked[key]
        assert restored["clm"]["readiness"]["blockers"] == blocked["clm"]["readiness"]["blockers"]
        assert restored["case"]["target_dispatch_confirmation"] is None
        assert restored["clm"]["submission"] is None
        assert restarted_target.calls == []
        stale = restarted.post(endpoint, json=incomplete)
        assert stale.status_code == 409
        assert stale.json()["detail"]["code"] == "ZERO_TOUCH_MANUAL_OWNERSHIP_STALE"
        assert restarted.get(f"/api/onboarding/cases/{cid}/ownership").json() == graph
        corrected = restarted.post(endpoint, json=current_payload(restarted, cid, percent="60"))
        assert corrected.status_code == 200, corrected.text
        recovered = corrected.json()
        assert recovered["current_stage"] == "READINESS"
        assert recovered["clm"]["readiness"]["blockers"] == []
        assert [e["blocker_code"] for e in recovered["active_exceptions"]] == [
            "TARGET_CONFIRMATION_REQUIRED"
        ]
        assert recovered["active_exceptions"][0]["exception_id"] != obsolete
        assert recovered["metrics"]["exceptions_resolved"] == (
            blocked["metrics"]["exceptions_resolved"] + 1
        )
        retained_cancel = next(
            e for e in recovered["historical_exceptions"] if e["exception_id"] == obsolete
        )
        resolved_owner = next(
            e for e in recovered["historical_exceptions"]
            if e["exception_id"] == blocked["active_exceptions"][0]["exception_id"]
        )
        assert retained_cancel["status"] == "CANCELLED"
        assert resolved_owner["status"] == "RESOLVED"
        assert restarted_target.calls == []
    final_target = RecordingMockGoldTier()
    with (
        patch("app.composition.MockGoldTierConnector", lambda **_: final_target),
        TestClient(create_app(config)) as final,
    ):
        final_summary = final.get(f"/api/clm/zero-touch/cases/{cid}").json()
        assert final_summary["version"] == recovered["version"]
        assert final_summary["active_exceptions"] == recovered["active_exceptions"]
        assert final_summary["clm"]["readiness"]["blockers"] == []
        assert final_summary["case"]["target_dispatch_confirmation"] is None
        assert final_target.calls == []
