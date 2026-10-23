"""Normal zero-touch API journey for the five-layer hybrid case; offline, no network."""

from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import SecretStr
from pypdf import PdfReader
from scripts.five_layer_hybrid_fixture import (
    FIVE_LAYER_FIELDS,
    FIVE_LAYER_ROOT_NAME,
    OfflineFiveLayerProtocolTransport,
)
from scripts.generate_five_layer_marketplace_hybrid_client import render
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
