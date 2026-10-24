"""Normal zero-touch API journey for the five-layer hybrid case; offline, no network."""

from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from httpx import Response
from pydantic import SecretStr
from pypdf import PdfReader
from scripts.five_layer_hybrid_fixture import (
    FIVE_LAYER_FIELDS,
    FIVE_LAYER_ROOT_NAME,
    OfflineFiveLayerProtocolTransport,
)
from scripts.generate_five_layer_marketplace_hybrid_client import render
from scripts.slice_b_registry_fixture import GARDEN_FIELDS
from test_slice_b_registry_demo import start
from test_zero_touch_exception_remediation import current_document, successful

from app.composition import build_acra_connector
from app.config import Settings
from app.main import create_app

PDF_NAME = "five-layer-marketplace-hybrid-client.pdf"
PDF = Path(__file__).parent / "fixtures/uat" / PDF_NAME


def system() -> tuple[TestClient, OfflineFiveLayerProtocolTransport]:
    settings = Settings(
        _env_file=None,
        app_env="test",
        clm_persistence_mode="memory",
        registry_cache_mode="auto",
        acra_connector_mode="api_marketplace_mock",
        acra_marketplace_ownership_overlay="hybrid_direct_overlay",
        goldtier_connector_mode="mock",
        idp_connector_mode="local_pdf_text",
        demo_controls_enabled=False,
        acra_api_marketplace_mock_client_id=SecretStr("synthetic-offline-client"),
        acra_api_marketplace_mock_secret_key=SecretStr("synthetic-offline-key"),
    )
    transport = OfflineFiveLayerProtocolTransport()
    connector = build_acra_connector(
        settings, transport=transport, marketplace_token_transport=transport
    )
    application = create_app(settings, acra_connector=connector, e2e_acra_protocol_fixture=True)
    return TestClient(application), transport


def test_generated_pdf_is_reproducible_selectable_and_declares_no_ownership_values() -> None:
    assert PDF.read_bytes() == render()
    reader = PdfReader(PDF, strict=True)
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    for key, value in FIVE_LAYER_FIELDS.items():
        assert f"{key}: {value}" in text
    assert "Registered Address:" not in text
    assert "not ACRA-returned ownership" in text and "not an ACRA extract" in text
    assert "%" not in text and "percent" not in text.lower()


def test_upload_onboards_the_root_and_stops_at_review_with_five_corporate_levels() -> None:
    client, transport = system()
    current = start(client, FIVE_LAYER_FIELDS, PDF_NAME)
    case_id = current["case"]["case_id"]
    entity = current["case"]["entity"]
    assert (entity["legal_name"], entity["registration_number"]) == (
        FIVE_LAYER_ROOT_NAME,
        "201511222D",
    )
    assert current["case"]["registry_acquisition"]["status"] == "PARTIAL"

    document = current_document(client, case_id)
    assert document["completion_method"] == "AUTO_CONFIRMED"
    assert document["ownership_observations"] == []
    extracted = {item["field_key"]: item["normalized_value"] for item in document["fields"]}
    assert extracted["legal_name"] == FIVE_LAYER_ROOT_NAME
    assert extracted["registration_number"] == "201511222D"
    assert {
        item["comparison_status"] for item in document["fields"] if item["normalized_value"]
    } == {"MATCH"}
    reconciliation = current["reconciliation"]
    assert reconciliation["status"] == "MATCHED"
    outcomes = {item["field_name"]: item["outcome"] for item in reconciliation["fields"]}
    assert outcomes.pop("registered_address") == "REGISTRY_ONLY"
    assert set(outcomes.values()) == {"MATCH"}
    # The zero-touch run stops at the ownership review gate.
    assert (current["status"], current["current_stage"]) == ("WAITING_FOR_REVIEW", "OWNERSHIP")

    ownership = successful(client.get(f"/api/onboarding/cases/{case_id}/ownership"))
    assert ownership["state"] == "REVIEW_REQUIRED"
    assert ownership["source_classification"] == "OFFICIAL_MOCK_PLUS_LOCAL_DIRECT_OVERLAY"
    audit = ownership["discovery"]
    assert audit["overlay_scenario_id"] == "FIVE_LAYER_MARKETPLACE_HYBRID_V1"
    assert sorted(item["depth"] for item in audit["records"]) == [1, 2, 3, 3, 4]
    assert {item["provenance"]["provider"] for item in ownership["relationships"]} == {
        "LOCAL_SYNTHETIC_RELATIONSHIP"
    }
    candidates = {item["party"]["display_name"]: item for item in ownership["candidates"]}
    assert Decimal(candidates["DIANA KOH (SYNTHETIC PERSON)"]["aggregated_ownership_percent"]) == (
        Decimal("25")
    )
    assert {item["classification"] for item in candidates.values()} == {"REVIEW_REQUIRED"}
    assert {
        name: item["synthetic_basis_threshold_result"] for name, item in candidates.items()
    } == {
        "ALEX TAN (SYNTHETIC PERSON)": "NOT_MET",
        "BEATRICE LIM (SYNTHETIC PERSON)": "MET",
        "CHARLES ONG (SYNTHETIC PERSON)": "NOT_MET",
        "DIANA KOH (SYNTHETIC PERSON)": "MET",
        "EDWARD NG (SYNTHETIC PERSON)": "NOT_MET",
    }
    # Review blocks every target mutation: nothing was sent to GoldTier.
    assert current["case"].get("goldtier_result") is None
    assert current["status"] != "COMPLETED"

    first_gets, first_tokens = transport.get_count, transport.token_requests
    second = start(client, FIVE_LAYER_FIELDS, PDF_NAME)
    second_ownership = successful(
        client.get(f"/api/onboarding/cases/{second['case']['case_id']}/ownership")
    )
    assert (transport.get_count, transport.token_requests) == (first_gets, first_tokens)
    assert second_ownership["discovery"]["cache_hits"] == 5
    assert transport.metadata()["external_calls"] == 0


def keep_current_evidence(client: TestClient, case_id: str) -> Response:
    """The creator's CURRENT_EVIDENCE decision for the exact current graph."""
    summary = successful(client.get(f"/api/clm/zero-touch/cases/{case_id}"))
    ownership = successful(client.get(f"/api/onboarding/cases/{case_id}/ownership"))
    documents = successful(client.get(f"/api/onboarding/cases/{case_id}/documents"))
    [document] = [item for item in documents if not item["superseded_by_document_id"]]
    return client.post(
        f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
        json={
            "root_registration_number": summary["case"]["entity"]["registration_number"],
            "evidence_document_id": document["document_id"],
            "evidence_document_version": len(document["events"]),
            "as_of_date": "2026-10-20",
            "rationale": None,
            "root_party_id": ownership["root_party_id"],
            "parties": ownership["parties"],
            "relationships": [
                {
                    key: edge[key]
                    for key in (
                        "relationship_id",
                        "parent_party_id",
                        "child_party_id",
                        "ownership_percent",
                    )
                }
                for edge in ownership["relationships"]
            ],
            "observed_document_versions": ownership["document_bindings"],
            "selected_observation_ids": [],
            "source_selection": "CURRENT_EVIDENCE",
            "expected_automation_version": summary["version"],
            "expected_ownership_version": ownership["version"],
            "expected_case_event_count": len(summary["case"]["events"]),
        },
    )


def test_garden_hybrid_journey_keeps_the_unresolved_sim_lim_branch_out_of_readiness() -> None:
    client, transport = system()
    current = start(client, GARDEN_FIELDS, "garden-partnership-reviewed-client.pdf")
    case_id = current["case"]["case_id"]
    assert (current["status"], current["current_stage"]) == ("WAITING_FOR_REVIEW", "OWNERSHIP")

    ownership = successful(client.get(f"/api/onboarding/cases/{case_id}/ownership"))
    assert ownership["state"] == "REVIEW_REQUIRED"
    assert ownership["discovery"]["overlay_scenario_id"] == "GARDEN_DIRECT_OVERLAY_V1"
    [sim_lim] = ownership["discovery"]["records"]
    assert (sim_lim["registration_number"], sim_lim["outcome"]) == ("111111111M", "NOT_FOUND")
    assert Decimal(sim_lim["max_effective_percent"]) == Decimal("62.5")
    assert Decimal(ownership["discovery"]["unresolved_upper_bound_percent"]) == Decimal("62.5")
    # Independent reasons: the unresolved SIM LIM branch, the synthetic links and the
    # official partnership roles that no overlay link explains.
    assert {item["code"] for item in ownership["issues"]} == {
        "INCOMPLETE_LEGAL_ENTITY",
        "CORPORATE_OWNERSHIP_UNRESOLVED",
        "SYNTHETIC_OWNERSHIP_EVIDENCE",
        "UBO_REVIEW_REQUIRED",
    }
    [lim] = ownership["candidates"]
    assert (lim["threshold_result"], lim["classification"]) == ("INDETERMINATE", "REVIEW_REQUIRED")
    assert lim["synthetic_basis_threshold_result"] == "MET"

    summary = successful(client.get(f"/api/clm/zero-touch/cases/{case_id}"))
    assert "OWNERSHIP_REVIEW_REQUIRED" in summary["clm"]["readiness"]["blockers"]
    assert summary["case"].get("goldtier_result") is None
    assert summary["clm"]["submission"] is None

    # Keeping the current, still incomplete evidence is not a resolution.
    retained = keep_current_evidence(client, case_id)
    assert retained.status_code == 409
    assert retained.json()["detail"]["code"] == "ZERO_TOUCH_MANUAL_OWNERSHIP_REVIEW_REQUIRED"
    after = successful(client.get(f"/api/clm/zero-touch/cases/{case_id}"))
    assert (after["status"], after["current_stage"]) == ("WAITING_FOR_REVIEW", "OWNERSHIP")
    assert "OWNERSHIP_REVIEW_REQUIRED" in after["clm"]["readiness"]["blockers"]
    assert after["case"].get("goldtier_result") is None
    assert transport.metadata()["external_calls"] == 0


def test_a_creator_may_keep_the_synthetic_graph_through_the_accountable_path() -> None:
    # D-078: keeping the complete synthetic graph is the creator's own declaration,
    # bound to a receipt and the retained hybrid analysis, and still gated by target
    # confirmation before any GoldTier target mutation.
    client, _ = system()
    current = start(client, FIVE_LAYER_FIELDS, PDF_NAME)
    case_id = current["case"]["case_id"]
    hybrid = successful(client.get(f"/api/onboarding/cases/{case_id}/ownership"))
    assert hybrid["state"] == "REVIEW_REQUIRED"

    assert keep_current_evidence(client, case_id).status_code == 200

    summary = successful(client.get(f"/api/clm/zero-touch/cases/{case_id}"))
    assert summary["status"] == "WAITING_FOR_REVIEW"
    assert [item["exception_type"] for item in summary["active_exceptions"]] == [
        "TARGET_CONFIRMATION_REQUIRED"
    ]
    assert summary["case"].get("goldtier_result") is None
    assert summary["clm"]["submission"] is None

    ownership = successful(client.get(f"/api/onboarding/cases/{case_id}/ownership"))
    assert (ownership["state"], ownership["provider_name"]) == (
        "ANALYZED",
        "MANUAL_DECLARATION_POC",
    )
    assert {item["provenance"]["provider"] for item in ownership["relationships"]} == {
        "MANUAL_DECLARATION_POC"
    }
    receipt = ownership["manual_review_receipt"]
    assert receipt["source_selection"] == "CURRENT_EVIDENCE"
    assert receipt["replaced_analysis_id"] == hybrid["analysis_id"]
    assert receipt["actor_id"]
    [prior] = ownership["prior_analyses"]
    assert prior["analysis_id"] == hybrid["analysis_id"]
    assert prior["source_classification"] == "OFFICIAL_MOCK_PLUS_LOCAL_DIRECT_OVERLAY"
    assert "SYNTHETIC_OWNERSHIP_EVIDENCE" in {item["code"] for item in prior["issues"]}
    assert {item["provenance"]["provider"] for item in prior["relationships"]} == {
        "LOCAL_SYNTHETIC_RELATIONSHIP"
    }
    candidates = {item["party"]["display_name"]: item for item in ownership["candidates"]}
    assert Decimal(candidates["DIANA KOH (SYNTHETIC PERSON)"]["aggregated_ownership_percent"]) == (
        Decimal("25")
    )
    assert {
        name
        for name, item in candidates.items()
        if item["classification"] == "PROVISIONAL_UBO_CANDIDATE"
    } == {"BEATRICE LIM (SYNTHETIC PERSON)", "DIANA KOH (SYNTHETIC PERSON)"}
