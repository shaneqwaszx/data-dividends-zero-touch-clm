"""Actual Marketplace composition: exact local seed, PDFs, Decimal engine and ledger."""

import secrets
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from pypdf import PdfReader
from scripts.garden_protocol_fixture import OfflineGardenProtocolTransport
from scripts.generate_phase08_synthetic_pdfs import text_pdf
from scripts.seed_zero_touch_happy_path_companies import manage_fixtures
from scripts.synthetic_company_pack import SYNTHETIC_COMPANIES
from scripts.synthetic_company_pack_test_transport import NoMarketplaceRequests
from scripts.zero_touch_happy_path_fixtures import (
    ALL_COMPANIES,
    NEW_COMPANIES,
    SHARE_COMPANIES,
)
from test_slice_b_registry_demo import confirm
from test_zero_touch_database_happy_path import assert_prepared as assert_existing_prepared
from test_zero_touch_database_happy_path import prepare
from test_zero_touch_orchestration import RecordingMockGoldTier

from app.config import Settings
from app.connectors.acra_sandbox import AcraHttpResponse
from app.connectors.mock_acra import MockAcraConnector
from app.domain.registry_dataset import local_synthetic_registry_identity
from app.main import create_app
from app.persistence.composition import build_persistence_bundle
from app.services.registry_cache_repository import InMemoryRegistrySnapshotRepository

NOW = datetime(2026, 10, 9, 0, 0, 0, 123456, tzinfo=UTC)
DOCUMENTS = Path(__file__).parent / "fixtures/uat/zero-touch-database"
OPERATIONS = ["ENTITY_PROFILE", "OFFICERS", "OWNERSHIP_PARTIES", "RELATIONSHIPS"]
EXPECTED = {
    "ORION": {
        "Avery Synthetic": ("70", "0", "70", True),
        "Blair Synthetic": ("30", "0", "30", True),
    },
    "PACIFIC": {
        "Casey Synthetic": ("40", "0", "40", True),
        "Dana Synthetic": ("35", "0", "35", True),
        "Ellis Synthetic": ("25", "0", "25", True),
    },
    "STRAITS": {
        "Fiona Synthetic": ("0", "48", "48", True),
        "Jordan Synthetic": ("40", "0", "40", True),
        "Gabriel Synthetic": ("0", "12", "12", False),
    },
    "MERIDIAN": {
        "Hannah Synthetic": ("0", "30", "30", True),
        "Ian Synthetic": ("0", "20", "20", False),
        "Iris Synthetic": ("30", "0", "30", True),
        "Julian Synthetic": ("20", "0", "20", False),
    },
}


def settings(**overrides):
    values = dict(
        _env_file=None,
        app_env="test",
        acra_connector_mode="api_marketplace_mock",
        clm_persistence_mode="memory",
        registry_cache_mode="auto",
        goldtier_connector_mode="mock",
        idp_connector_mode="local_pdf_text",
        demo_controls_enabled=False,
        acra_api_marketplace_mock_client_id=SecretStr(secrets.token_urlsafe(32)),
        acra_api_marketplace_mock_secret_key=SecretStr(secrets.token_urlsafe(32)),
    )
    values.update(overrides)
    return Settings(**values)


@contextmanager
def marketplace_seams(transport):
    # Patch only default network factories. create_app still builds the configured
    # Official Marketplace connector, router, coordinator, services and repositories.
    with (
        patch("app.composition.HttpxAcraTransport", lambda **_: transport),
        patch(
            "app.connectors.acra_api_marketplace_auth.HttpxAcraMarketplaceTokenTransport",
            lambda: transport,
        ),
    ):
        yield


def start(client, company):
    created = client.post(
        "/api/clm/zero-touch/cases",
        json={
            "uen": company.uen,
            "legal_name": company.name,
            "country_of_incorporation": "SG",
        },
    )
    assert created.status_code == 201, created.json()
    current = created.json()
    case_id = current["case"]["case_id"]
    assert current["target_classification"]["kyc_customer_type"]["selected_value"] is None
    assert current["case"]["goldtier_result"] is None
    uploaded = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
        content=(DOCUMENTS / company.document_name).read_bytes(),
        headers={
            "Content-Type": "application/pdf",
            "X-Document-Name": company.document_name,
        },
    )
    assert uploaded.status_code == 201, uploaded.json()
    complete = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/complete", json={"expected_document_count": 1}
    )
    assert complete.status_code == 200, complete.json()
    return complete.json()


def assert_prepared(client, current, company):
    case_id = current["case"]["case_id"]
    acquisition = current["case"]["registry_acquisition"]
    assert acquisition["status"] == "COMPLETE"
    assert [r["operation"] for r in acquisition["operation_results"]] == OPERATIONS
    assert [r["status"] for r in acquisition["operation_results"]] == ["COMPLETE"] * 4
    assert current["case"]["entity"]["registration_number"] == company.uen
    assert all(r["provenance"]["environment"] == "MOCK" for r in acquisition["operation_results"])
    documents = client.get(f"/api/onboarding/cases/{case_id}/documents").json()
    assert len(documents) == 1
    document = documents[0]
    assert document["completion_method"] == "AUTO_CONFIRMED"
    assert len(document["fields"]) == 4
    assert all(
        f["comparison_status"] == "MATCH"
        and f["review_status"] == "ACCEPTED"
        and Decimal(str(f["confidence"])) == Decimal("0.97")
        for f in document["fields"]
    )
    assert all(f["extraction_quality"] == "HIGH" for f in document["fields"])
    ownership = client.get(f"/api/onboarding/cases/{case_id}/ownership").json()
    assert ownership["state"] == "ANALYZED", ownership["issues"]
    assert ownership["manual_review_receipt"] is None
    actual = {
        c["party"]["display_name"]: (
            Decimal(c["direct_ownership_percent"]),
            Decimal(c["indirect_ownership_percent"]),
            Decimal(c["aggregated_ownership_percent"]),
            c["classification"] == "PROVISIONAL_UBO_CANDIDATE",
        )
        for c in ownership["candidates"]
    }
    assert actual == {
        name: (Decimal(d), Decimal(i), Decimal(a), qualifies)
        for name, (d, i, a, qualifies) in EXPECTED[company.code].items()
    }
    assert not set(actual).intersection(o["name"] for o in acquisition["officers"])
    assert [e["blocker_code"] for e in current["active_exceptions"]] == [
        "TARGET_CONFIRMATION_REQUIRED",
    ]
    classification = current["target_classification"]
    assert classification["current"]
    assert classification["kyc_customer_type"]["selected_value"] == "Company - Private"
    assert classification["client_segment"]["selected_value"] == "Corporate"
    assert all(
        classification[key]["selection"]["source"] == "DOCUMENT"
        for key in ["kyc_customer_type", "client_segment"]
    )
    assert current["case"]["goldtier_result"] is None
    return ownership


def assert_seed(current, company, bundle):
    case = current["case"]
    assert case["jurisdiction_resolution"]["resolved_jurisdiction"] == "SG"
    assert case["registry_route"]["provider"] == "ACRA"
    binding = case["registry_evidence_binding"]
    assert binding["disposition"] == "CACHE_HIT"
    assert binding["synthetic_seed_namespace"] == "LOCAL_SYNTHETIC_UAT_V1"
    seed = bundle.registry_snapshots.get(company.snapshot(datetime.now(UTC)).key)
    assert seed.key.provider_identity == local_synthetic_registry_identity()
    assert seed.acquisition.status == "COMPLETE"
    assert case["registry_acquisition"][
        "retrieved_at"
    ] == seed.acquisition.retrieved_at.isoformat().replace("+00:00", "Z")
    for operation in case["registry_acquisition"]["operation_results"]:
        assert operation["status"] == "COMPLETE"
        assert operation["provenance"]["evidence_reference"].startswith("LOCAL_SYNTHETIC_SEED_")


@pytest.mark.parametrize("company", NEW_COMPANIES, ids=lambda c: c.code)
def test_actual_marketplace_normal_composition_seeded_happy_path_zero_requests(company):
    configured = settings()
    bundle = build_persistence_bundle(configured)
    manage_fixtures(bundle.registry_snapshots, now=datetime.now(UTC), seed=True)
    transport, target = NoMarketplaceRequests(), RecordingMockGoldTier()
    with (
        marketplace_seams(transport),
        patch("app.main.build_persistence_bundle", return_value=bundle),
        patch("app.composition.MockGoldTierConnector", lambda **_: target),
        TestClient(create_app(configured)) as client,
    ):
        profile = client.get("/api/system/execution-profile").json()
        assert profile["registry_provider_mode"] == "API_MARKETPLACE_MOCK"
        current = start(client, company)
        assert current["clm"]["target_search_checkpoint"]["disposition"] == "NO_MATCH"
        assert target.calls == ["search"]
        assert_seed(current, company, bundle)
        ownership = assert_prepared(client, current, company)
        reused = start(client, company)
        assert reused["case"]["case_id"] != current["case"]["case_id"]
        assert reused["case"]["registry_acquisition"] == current["case"]["registry_acquisition"]
        assert_seed(reused, company, bundle)
        final = confirm(client, current)
        assert final["status"] == "COMPLETED"
        assert final["target_submission"]["state"] == "SUBMISSION_CONFIRMED"
        assert final["case"]["goldtier_result"]["readback_status"] == "VERIFIED"
        assert target.calls == ["search", "search", "search", "shell", "policy", "amend", "search"]
        before = list(target.calls)
        case_id = current["case"]["case_id"]
        for _ in range(2):
            reopened = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
            assert reopened["target_operations"] == final["target_operations"]
            assert reopened["status"] == "COMPLETED"
            assert client.get(f"/api/onboarding/cases/{case_id}/ownership").json() == ownership
        assert transport.calls == [] and target.calls == before


# D-101: Gamma has no registry shares; its agreement journey is in test_zero_touch_entity_types.
@pytest.mark.parametrize("company", SHARE_COMPANIES, ids=lambda c: c.code)
def test_existing_four_use_actual_marketplace_composition_without_requests(company):
    configured = settings()
    bundle = build_persistence_bundle(configured)
    manage_fixtures(bundle.registry_snapshots, now=datetime.now(UTC), seed=True)
    transport = NoMarketplaceRequests()
    with (
        marketplace_seams(transport),
        patch("app.main.build_persistence_bundle", return_value=bundle),
        TestClient(create_app(configured)) as client,
    ):
        current = prepare(client, company)
        assert_seed(current, company, bundle)
        assert_existing_prepared(client, current, company)
        assert confirm(client, current)["target_submission"]["state"] == "SUBMISSION_CONFIRMED"
        assert transport.calls == []


@pytest.mark.parametrize("company", SYNTHETIC_COMPANIES, ids=lambda c: c.code)
def test_matching_native_pdf_has_exact_identity_and_explicit_classification(company):
    content = (DOCUMENTS / company.document_name).read_bytes()
    assert content == text_pdf(
        company.document_fields | {
            "KYC Customer Type": "Company - Private", "Client Segment": "Corporate",
        },
        extra_lines=(
            "LOCAL PROJECT SYNTHETIC MOCK - fictional identity only.",
            "Ownership evidence comes from the synthetic registry graph.",
        ),
    )
    reader = PdfReader(DOCUMENTS / company.document_name)
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    for key, value in company.document_fields.items():
        assert f"{key}: {value}" in text
    assert "KYC Customer Type: Company - Private" in text and "Client Segment: Corporate" in text
    assert "SYNTHETIC MOCK" in text and "%" not in text
    assert all(name not in text for _, _, name in company.parties)


def test_same_seed_owner_all_eight_idempotence_expiry_and_namespace():
    repo = InMemoryRegistrySnapshotRepository()
    # D-101: nine seeds, including the PARTIAL Government identity.
    assert manage_fixtures(repo, now=NOW, seed=True)["created"] == 9
    originals = [repo.get(c.snapshot(NOW).key) for c in ALL_COMPANIES]
    # D-101: nine seeds, including the PARTIAL Government identity.
    assert manage_fixtures(repo, now=NOW + timedelta(hours=1), seed=True)["fresh"] == 9
    assert [repo.get(e.key) for e in originals] == originals
    assert all(e.key.provider_identity == local_synthetic_registry_identity() for e in originals)
    # D-101: nine seeds, including the PARTIAL Government identity.
    assert manage_fixtures(repo, now=NOW + timedelta(days=90), seed=True)["refreshed"] == 9
    assert all(repo.get(e.key).revision == 1 for e in originals)


@pytest.mark.parametrize("stale", [False, True], ids=["unseeded-neighbor", "expired-seed"])
def test_unusable_local_seed_falls_through_actual_marketplace_without_synthetic_evidence(stale):
    class AbsentMarketplace(OfflineGardenProtocolTransport):
        def get(self, url, **kwargs):
            self.calls.append("ENTITY_PROFILE")
            return AcraHttpResponse(200, {"entities": []}, "application/json", 16)

    configured = settings()
    bundle = build_persistence_bundle(configured)
    company = NEW_COMPANIES[0]
    manage_fixtures(
        bundle.registry_snapshots,
        now=datetime.now(UTC) - timedelta(days=91) if stale else datetime.now(UTC),
        seed=True,
    )
    uen = company.uen if stale else "202400018R"
    transport = AbsentMarketplace()
    with (
        marketplace_seams(transport),
        patch("app.main.build_persistence_bundle", return_value=bundle),
        TestClient(create_app(configured)) as client,
    ):
        response = client.post(
            "/api/clm/zero-touch/cases",
            json={
                "uen": uen,
                "legal_name": "UNSEEDED SYNTHETIC NEIGHBOR",
                "country_of_incorporation": "SG",
            },
        )
        assert response.status_code == 201
        current = response.json()
        assert transport.calls == ["TOKEN", "ENTITY_PROFILE"]
        assert current["case"]["registry_evidence_binding"] is None
        assert current["case"]["entity"] is None
        assert current["status"] != "COMPLETED"
        assert "ACRA_ENTITY_NOT_FOUND" in str(current)
        assert "LOCAL_SYNTHETIC_SEED" not in str(current)


def test_new_records_are_not_mock_acra_connector_fixtures():
    connector = MockAcraConnector()
    assert all(connector.fetch_company(c.uen) is None for c in NEW_COMPANIES)


def test_seed_cli_rejects_protected_database_before_connection(monkeypatch, capsys):
    from scripts import seed_zero_touch_happy_path_companies as utility

    monkeypatch.setattr("sys.argv", ["seed", "--seed", "--database", "clm_poc"])
    with patch("pymongo.MongoClient") as connect:
        assert utility.main() == 2
        connect.assert_not_called()
    assert "SEED_CHECK_FAILED" in capsys.readouterr().out
