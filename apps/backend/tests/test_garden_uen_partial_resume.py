"""Garden correction against strict offline PARTIAL registry and XPI Sandbox inputs."""

from dataclasses import replace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from scripts.s3_sandbox_fixture import OfflineS3SandboxTransport
from scripts.slice_b_registry_fixture import GardenCorrectionProtocolTransport
from test_garden_protocol_fixture import fixture_settings
from test_phase12_persistence import MemoryEnvelopeStore
from test_slice_b_registry_demo import FIXTURES
from test_zero_touch_exception_remediation import current_document, successful

import app.main as application
from app.composition import build_acra_connector
from app.connectors.goldtier_xpi import GoldTierXpiHttpResponse
from app.main import create_app
from app.persistence.composition import build_persistence_bundle
from app.persistence.repositories import (
    MongoClmOrchestrationRepository,
    MongoDocumentProcessingRepository,
    MongoOnboardingCaseRepository,
    MongoOnboardingIntelligenceRepository,
    MongoOwnershipAnalysisRepository,
    MongoReconciliationRepository,
    MongoReconciliationUnitOfWork,
    MongoTargetExecutionRepository,
    MongoZeroTouchAutomationRepository,
)


class NoMatchGardenTarget(OfflineS3SandboxTransport):
    def request(self, method: str, url: str, **kwargs: Any) -> GoldTierXpiHttpResponse:
        # Delegate first to retain the exact existing URL/method/identity allowlist.
        response = super().request(method, url, **kwargs)
        return GoldTierXpiHttpResponse(200, []) if self.counts["SEARCH"] else response


def garden_system(monkeypatch, *, no_match=False, store=None, target=None):
    settings = fixture_settings().model_copy(
        update={
            "idp_connector_mode": "local_pdf_text",
            "goldtier_connector_mode": "sandbox",
            "goldtier_sandbox_base_url": "https://sandbox.goldtier.invalid",
            "goldtier_sandbox_user_id": SecretStr("synthetic-offline-user"),
            "goldtier_sandbox_environment": "synthetic",
            "goldtier_sandbox_allow_writes": False,
        }
    )
    transport = GardenCorrectionProtocolTransport()
    connector = build_acra_connector(
        settings,
        transport=transport,
        marketplace_token_transport=transport,
    )
    if target is None:
        target_type = NoMatchGardenTarget if no_match else OfflineS3SandboxTransport
        target = target_type("garden-existing-customer")
    if store is not None:
        bundle = build_persistence_bundle(settings)
        bundle = replace(
            bundle,
            onboarding=MongoOnboardingCaseRepository(store),
            documents=MongoDocumentProcessingRepository(store),
            ownership=MongoOwnershipAnalysisRepository(store),
            intelligence=MongoOnboardingIntelligenceRepository(store),
            reconciliation=MongoReconciliationRepository(store),
            reconciliation_unit_of_work=MongoReconciliationUnitOfWork(store),
            clm=MongoClmOrchestrationRepository(store),
            automation=MongoZeroTouchAutomationRepository(store),
            target_executions=MongoTargetExecutionRepository(store),
        )
        monkeypatch.setattr(application, "build_persistence_bundle", lambda _: bundle)
    return (
        TestClient(
            create_app(
                settings,
                acra_connector=connector,
                goldtier_transport=target,
                e2e_acra_protocol_fixture=True,
            )
        ),
        transport,
        target,
    )


def start_wrong_garden(client):
    created = successful(
        client.post(
            "/api/clm/zero-touch/cases",
            json={
                "uen": "11111998B",
                "legal_name": "GARDEN BUSINESS",
                "country_of_incorporation": "SG",
            },
        ),
        201,
    )
    case_id = created["case"]["case_id"]
    successful(
        client.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
            content=(FIXTURES / "garden-partnership-reviewed-client.pdf").read_bytes(),
            headers={"Content-Type": "application/pdf", "X-Document-Name": "garden-demo.pdf"},
        ),
        201,
    )
    current = successful(
        client.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
            json={"expected_document_count": 1},
        )
    )
    assert current["current_stage"] == "REGISTRY"
    assert "ACRA_ENTITY_NOT_FOUND" in {
        item["blocker_code"] for item in current["active_exceptions"]
    }
    return current, current_document(client, case_id)


def correction_request(current, *, choice="OTHER", document=None, uen="11111999A"):
    request = {
        "legal_name": "GARDEN BUSINESS",
        "registration_number": uen,
        "country_of_incorporation": "SG",
        "choice": choice,
        "expected_automation_version": current["version"],
        "expected_clm_version": current["clm"]["version"],
        "expected_case_event_count": len(current["case"]["events"]),
    }
    if document is not None:
        request.update(
            document_id=document["document_id"],
            expected_document_event_count=len(document["events"]),
        )
    return request


def correct(client, current, **kwargs):
    return client.post(
        f"/api/clm/zero-touch/cases/{current['case']['case_id']}/registry-identity",
        json=correction_request(current, **kwargs),
    )


@pytest.mark.parametrize("mode", ["memory", "mongo-adapters"])
@pytest.mark.parametrize("no_match", [False, True])
@pytest.mark.parametrize("choice", ["OTHER", "ENTERED", "DOCUMENT"])
def test_garden_partial_correction_retains_document_and_continues(
    monkeypatch,
    mode,
    no_match,
    choice,
):
    store = MemoryEnvelopeStore() if mode == "mongo-adapters" else None
    client, transport, target = garden_system(monkeypatch, no_match=no_match, store=store)
    current, document = start_wrong_garden(client)
    case_id = current["case"]["case_id"]
    if choice == "ENTERED":
        current = successful(correct(client, current))
    request = correction_request(
        current,
        choice=choice,
        document=document if choice == "DOCUMENT" else None,
    )
    body = successful(
        client.post(
            f"/api/clm/zero-touch/cases/{case_id}/registry-identity",
            json=request,
        )
    )
    assert body["case"]["requested_uen"] == "11111999A"
    assert body["case"]["case_id"] == case_id
    acquisition = body["case"]["registry_acquisition"]
    assert acquisition["status"] == "PARTIAL"
    assert [item["status"] for item in acquisition["operation_results"]] == [
        "COMPLETE",
        "COMPLETE",
        "UNSUPPORTED",
        "UNSUPPORTED",
    ]
    assert acquisition["ownership_parties"] == acquisition["relationships"] == []
    assert body["case"]["registry_evidence_binding"] is None
    assert body["current_stage"] != "REGISTRY"
    assert all(
        item["blocker_code"] != "ACRA_ENTITY_NOT_FOUND" for item in body["active_exceptions"]
    )
    assert any(
        item["blocker_code"] == "ACRA_ENTITY_NOT_FOUND" and item["status"] == "CANCELLED"
        for item in body["historical_exceptions"]
    )
    assert body["status"] != "COMPLETED"
    assert body["case"]["target_dispatch_confirmation"] is None
    if not no_match:
        assert body["current_stage"] == "GOLDTIER_SEARCH"
        assert body["active_exceptions"][0]["blocker_code"] == "GT_SEARCH_IDENTITY_REVIEW_REQUIRED"
        assert body["clm"]["target_search_checkpoint"]["provider_outcome"] == "MATCH_FOUND"
        assert any(
            "CONFIRM_EXISTING_GOLDTIER_CUSTOMER" in item["metadata"]["currently_available_actions"]
            for item in body["active_exceptions"][0]["decisions"]
        )
    else:
        assert body["current_stage"] == "READINESS"
    retained = current_document(client, case_id)
    assert retained["document_id"] == document["document_id"]
    assert retained["created_at"] == document["created_at"]
    assert retained["superseded_by_document_id"] is None
    assert [
        (field["original_extracted_value"], field["provenance"]) for field in retained["fields"]
    ] == [(field["original_extracted_value"], field["provenance"]) for field in document["fields"]]
    assert sum(event["code"] == "IDENTITY_RECHECK_RETAINED" for event in body["timeline"]) == (
        2 if choice == "ENTERED" else 1
    )
    counts = dict(target.counts)
    registry_calls = list(transport.calls)
    # Exact repeated/stale request rejects before any provider/evidence mutation.
    stale = client.post(f"/api/clm/zero-touch/cases/{case_id}/registry-identity", json=request)
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "ZERO_TOUCH_IDENTITY_RECHECK_STALE"
    assert target.counts == counts and transport.calls == registry_calls
    for _ in range(2):
        observed = successful(client.get(f"/api/clm/zero-touch/cases/{case_id}"))
        assert observed["version"] == body["version"]
        assert observed["active_exceptions"] == body["active_exceptions"]
        assert observed["case"]["registry_acquisition"] == acquisition
    if store is not None:
        restarted, restarted_registry, _ = garden_system(
            monkeypatch,
            no_match=no_match,
            store=store,
            target=target,
        )
        restored = successful(restarted.get(f"/api/clm/zero-touch/cases/{case_id}"))
        assert restored["case"] == body["case"]
        assert restored["active_exceptions"] == body["active_exceptions"]
        assert current_document(restarted, case_id)["document_id"] == document["document_id"]
        assert restarted_registry.calls == []
    assert target.counts["SEARCH"] == (3 if choice == "ENTERED" else 2)
    assert target.counts["SHELL"] == target.counts["POLICY"] == target.counts["AMEND"] == 0
    assert target.counts == counts


def test_garden_wrong_entered_uen_and_invalid_manual_correction_have_no_effect(monkeypatch):
    client, transport, target = garden_system(monkeypatch)
    current, _ = start_wrong_garden(client)
    counts, calls = dict(target.counts), list(transport.calls)
    wrong_choice = correct(client, current, choice="ENTERED")
    assert wrong_choice.status_code == 409
    assert wrong_choice.json()["detail"]["code"] == "IDENTITY_CHOICE_INVALID"
    invalid = correct(client, current, uen="NOT-A-UEN")
    assert invalid.status_code == 409
    assert invalid.json()["detail"]["code"] == "ZERO_TOUCH_IDENTITY_RECHECK_INVALID"
    assert target.counts == counts and transport.calls == calls
    observed = successful(client.get(f"/api/clm/zero-touch/cases/{current['case']['case_id']}"))
    assert observed["case"] == current["case"]
