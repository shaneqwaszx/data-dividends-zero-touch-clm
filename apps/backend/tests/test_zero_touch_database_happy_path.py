"""Offline database-first new-customer flow, strict absence boundary and four scans."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from pypdf import PdfReader
from scripts.generate_zero_touch_happy_path_documents import DOCUMENT_DIRECTORY
from scripts.run_s3_sandbox_acceptance import OfflineAcceptanceTransport
from scripts.seed_zero_touch_happy_path_companies import (
    SeedConflictError,
    manage_fixtures,
    require_safe_target,
)
from scripts.zero_touch_happy_path_fixtures import COMPANIES, SHARE_COMPANIES
from test_slice_b_registry_demo import confirm

from app.composition import build_onboarding_service
from app.config import Settings
from app.connectors.goldtier_xpi import GoldTierXpiHttpResponse
from app.connectors.goldtier_xpi_models import XpiCustomerSearchRequest
from app.connectors.registry import AcraRegistryProviderAdapter
from app.domain.models import RegistryCacheKey, RegistryFreshnessPolicy
from app.domain.registry_dataset import local_synthetic_registry_identity
from app.main import create_app
from app.persistence.composition import build_persistence_bundle
from app.services.registry_acquisition import (
    RegistryAcquisitionCoordinator,
    RegistryCacheInvalidError,
)
from app.services.registry_cache_repository import InMemoryRegistrySnapshotRepository

NOW = datetime(2026, 10, 5, tzinfo=UTC)
TESSERACT = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")


class RecordingTarget(OfflineAcceptanceTransport):
    def __init__(self, name, uen):
        super().__init__(name, uen)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, urlsplit(url).path, parse_qs(urlsplit(url).query)))
        return super().request(method, url, **kwargs)


class NoAcra:
    def __init__(self):
        self.calls = []

    def fetch_company(self, uen):
        self.calls.append("ENTITY_PROFILE")
        raise AssertionError("No ACRA operation is allowed on a fresh database path")

    def fetch_officers(self, uen):
        self.calls.append("OFFICERS")
        raise AssertionError("No ACRA operation allowed")

    def fetch_ownership_parties(self, uen):
        self.calls.append("OWNERSHIP_PARTIES")
        raise AssertionError("No ACRA operation allowed")

    def fetch_relationships(self, uen):
        self.calls.append("RELATIONSHIPS")
        raise AssertionError("No ACRA operation allowed")


def sandbox_settings(**overrides):
    values = dict(
        _env_file=None,
        app_env="test",
        acra_connector_mode="api_marketplace_mock",
        goldtier_connector_mode="sandbox",
        goldtier_sandbox_base_url="https://sandbox.goldtier.invalid",
        goldtier_sandbox_environment="synthetic",
        goldtier_sandbox_user_id=SecretStr("synthetic-api-user"),
        goldtier_sandbox_allow_writes=True,
        idp_connector_mode="local_pdf_text",
    )
    values.update(overrides)
    return Settings(**values)


def prepare(client, company, *, scan=False):
    response = client.post(
        "/api/clm/zero-touch/cases",
        json={
            "uen": company.uen,
            "legal_name": company.name,
            "country_of_incorporation": "SG",
        },
    )
    assert response.status_code == 201, response.json()
    created = response.json()
    assert created["clm"]["target_search_checkpoint"]["disposition"] == "NO_MATCH"
    assert "GOLDTIER_SEARCH" in created["completed_stages"]
    assert created["case"]["registry_evidence_binding"]["disposition"] == "CACHE_HIT"
    case_id = created["case"]["case_id"]
    content = (
        (DOCUMENT_DIRECTORY / company.document_name).read_bytes()
        if scan
        else "\n".join(
            f"{k}: {v}" for k, v in {**company.fields, **company.target_profile}.items()
        ).encode()
    )
    uploaded = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
        content=content,
        headers={
            "Content-Type": "application/pdf" if scan else "text/plain",
            "X-Document-Name": company.document_name if scan else "fictional-profile.txt",
        },
    )
    assert uploaded.status_code == 201, uploaded.json()
    result = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/complete", json={"expected_document_count": 1}
    )
    assert result.status_code == 200, result.json()
    return result.json()


def assert_prepared(client, current, company):
    case_id = current["case"]["case_id"]
    documents = client.get(f"/api/onboarding/cases/{case_id}/documents").json()
    # API collection wrapper is checked by current implementation.
    records = documents["documents"] if isinstance(documents, dict) else documents
    document = records[0]
    assert document["completion_method"] == "AUTO_CONFIRMED"
    assert all(item["review_status"] == "ACCEPTED" for item in document["fields"])
    assert all(item["confidence"] >= 0.85 for item in document["fields"])
    ownership = client.get(f"/api/onboarding/cases/{case_id}/ownership").json()
    assert ownership["state"] == "ANALYZED", ownership.get("issues")
    assert ownership["manual_review_receipt"] is None
    percentages = {
        item["party"]["party_id"]: Decimal(item["aggregated_ownership_percent"])
        for item in ownership["candidates"]
    }
    assert {
        item["party"]["party_id"]
        for item in ownership["candidates"]
        if item["classification"] == "PROVISIONAL_UBO_CANDIDATE"
    } == {f"DEMO_{company.code}_{key}" for key, value in company.expected if Decimal(value) >= 25}
    assert percentages == {
        f"DEMO_{company.code}_{key}": Decimal(value) for key, value in company.expected
    }
    assert [item["blocker_code"] for item in current["active_exceptions"]] == [
        "TARGET_CONFIRMATION_REQUIRED",
    ]
    return document, ownership


# D-101: Gamma has no registry shares; its agreement journey is in test_zero_touch_entity_types.
@pytest.mark.parametrize("company", SHARE_COMPANIES, ids=lambda item: item.code)
def test_four_database_happy_paths_complete_without_acra_manual_ownership_or_replay(company):
    settings = sandbox_settings()
    bundle = build_persistence_bundle(settings)
    manage_fixtures(bundle.registry_snapshots, now=datetime.now(UTC), seed=True)
    acra = NoAcra()
    target = RecordingTarget(company.name, company.uen)
    with (
        patch("app.main.build_persistence_bundle", return_value=bundle),
        TestClient(create_app(settings, acra_connector=acra, goldtier_transport=target)) as client,
    ):
        current = prepare(client, company)
        assert_prepared(client, current, company)
        final = confirm(client, current)
        assert final["status"] == "COMPLETED"
        assert final["target_submission"]["state"] == "SUBMISSION_CONFIRMED"
        assert final["target_submission"]["goldtier_id"] == "SYNTHETIC-GT-S3"
        assert {item["operation"]: item["status"] for item in final["target_operations"]} == {
            "SEARCH": "NO_MATCH",
            "SHELL": "CREATED",
            "POLICY": "CREATED",
            "AMEND": "SKIPPED",
            "READBACK": "SUCCESS",
        }
        assert [call[0] for call in target.calls] == ["GET", "GET", "POST", "POST", "GET"]
        assert target.calls[-1][2] == {"goldTierID": ["SYNTHETIC-GT-S3"]}
        counts = list(target.calls)
        repeated = client.post(
            f"/api/clm/zero-touch/cases/{current['case']['case_id']}/target-confirmation",
            json={
                "expected_automation_version": final["version"],
                "expected_clm_version": final["clm"]["version"],
                "expected_case_event_count": len(final["case"]["events"]),
            },
        )
        assert repeated.status_code == 409
        assert target.calls == counts
        assert acra.calls == []


@pytest.mark.skipif(not TESSERACT.is_file(), reason="Local Tesseract unavailable")
# D-101: Gamma has no registry shares; its agreement journey is in test_zero_touch_entity_types.
@pytest.mark.parametrize("company", SHARE_COMPANIES, ids=lambda item: item.code)
def test_each_actual_image_only_pdf_auto_confirms_through_local_tesseract(company):
    assert PdfReader(DOCUMENT_DIRECTORY / company.document_name).pages[0].extract_text() == ""
    settings = sandbox_settings(local_ocr_executable=str(TESSERACT))
    bundle = build_persistence_bundle(settings)
    manage_fixtures(bundle.registry_snapshots, now=datetime.now(UTC), seed=True)
    with (
        patch("app.main.build_persistence_bundle", return_value=bundle),
        TestClient(
            create_app(
                settings,
                acra_connector=NoAcra(),
                goldtier_transport=OfflineAcceptanceTransport(company.name, company.uen),
            )
        ) as client,
    ):
        document, _ = assert_prepared(client, prepare(client, company, scan=True), company)
        assert "LOCAL_TESSERACT_OCR" in str(document)


@pytest.mark.parametrize("failure", ["rejected", "timeout", "transport", "malformed"])
def test_search_failure_never_becomes_no_match_or_dispatches(failure):
    company = COMPANIES[0]

    class FailingSearch:
        def request(self, method, url, **kwargs):
            assert method == "GET"
            if failure == "timeout":
                raise httpx.ReadTimeout("synthetic")
            if failure == "transport":
                raise httpx.ConnectError("synthetic")
            return GoldTierXpiHttpResponse(
                400 if failure == "rejected" else 200, {} if failure == "malformed" else []
            )

    settings = sandbox_settings()
    bundle = build_persistence_bundle(settings)
    manage_fixtures(bundle.registry_snapshots, now=datetime.now(UTC), seed=True)
    acra = NoAcra()
    with (
        patch("app.main.build_persistence_bundle", return_value=bundle),
        TestClient(
            create_app(
                settings,
                acra_connector=acra,
                goldtier_transport=FailingSearch(),
            )
        ) as client,
    ):
        result = client.post(
            "/api/clm/zero-touch/cases",
            json={
                "uen": company.uen,
                "legal_name": company.name,
                "country_of_incorporation": "SG",
            },
        ).json()
        search = result["clm"]["target_search_checkpoint"]
        assert search["disposition"] == "FAILED"
        if failure == "rejected":
            assert "SEARCH_REQUEST_REJECTED" in str(search)
        case_id = result["case"]["case_id"]
        assert result["case"]["registry_evidence_binding"]["disposition"] == "CACHE_HIT"
        assert result["case"]["goldtier_result"] is None
        assert (
            client.post(
                f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
                json={
                    "expected_automation_version": result["version"],
                    "expected_clm_version": result["clm"]["version"],
                    "expected_case_event_count": len(result["case"]["events"]),
                },
            ).status_code
            == 409
        )
        assert acra.calls == []


def test_search_query_omits_empty_criteria_and_encodes_exact_documented_aliases():
    request = XpiCustomerSearchRequest(
        legal_name="DEMO A & B + TEST PTE. LTD.", country_of_incorporation="SG"
    )
    from app.connectors.goldtier_xpi import GoldTierXpiSandboxConnection

    connection = GoldTierXpiSandboxConnection(
        "https://sandbox.goldtier.invalid", "synthetic", SecretStr("synthetic-user")
    )
    query = parse_qs(urlsplit(connection.search_endpoint(request)).query, keep_blank_values=True)
    assert query == {"legalName": [request.legal_name], "countryOfIncorporation": ["SG"]}


def test_seed_all_complete_idempotent_and_deep_copy():
    repository = InMemoryRegistrySnapshotRepository()
    # D-101: nine seeds, including the PARTIAL Government identity.
    assert manage_fixtures(repository, now=NOW, seed=True)["created"] == 9
    # D-101: nine seeds, including the PARTIAL Government identity.
    assert manage_fixtures(repository, now=NOW + timedelta(hours=1), seed=True)["fresh"] == 9
    # D-101: Gamma and Government are PARTIAL seeds (no registry share graph).
    for company in SHARE_COMPANIES:
        entry = repository.get(company.snapshot(NOW).key)
        assert entry.revision == 0 and entry.acquisition.status == "COMPLETE"
        totals = {}
        for edge in entry.acquisition.relationships:
            totals[edge.owned_entity_id] = (
                totals.get(edge.owned_entity_id, Decimal(0)) + edge.ownership_percentage
            )
        assert set(totals.values()) == {Decimal("100")}
        assert all(
            p.registration_identifier is None
            for p in entry.acquisition.ownership_parties
            if p.party_type == "NATURAL_PERSON"
        )
        assert all(p.name.startswith("DEMO ") for p in entry.acquisition.ownership_parties)
        entry.acquisition.entity_profile.legal_name = "changed local copy"
        assert repository.get(entry.key).acquisition.entity_profile.legal_name == company.name
    # D-101: nine seeds, including the PARTIAL Government identity.
    assert manage_fixtures(repository, now=NOW + timedelta(days=90), seed=True)["refreshed"] == 9


def test_seed_conflict_does_not_overwrite_any_known_key():
    repository = InMemoryRegistrySnapshotRepository()
    entry = COMPANIES[-1].snapshot(NOW)
    entry.acquisition.entity_profile.legal_name = "CONFLICTING DEMO DATA"
    repository.create(entry)
    with pytest.raises(SeedConflictError):
        manage_fixtures(repository, now=NOW, seed=True)
    assert repository.get(COMPANIES[0].snapshot(NOW).key) is None


@pytest.mark.parametrize(
    "database",
    [
        "clm_poc",
        "production",
        "clm_uat_demo",
        "clm_uat_" + "x" * 24,
        "clm_p16_" + "0" * 23,
    ],
)
def test_seed_rejects_unsafe_database_names(database):
    with pytest.raises(ValueError):
        require_safe_target(database, "test")


def test_seed_refuses_production_and_auto_cache_is_bounded():
    with pytest.raises(ValueError):
        require_safe_target("clm_uat_" + "a" * 24, "production")
    assert Settings(_env_file=None).registry_cache_enabled
    assert not Settings(_env_file=None, app_env="production").registry_cache_enabled
    assert not Settings(_env_file=None, acra_connector_mode="sandbox").registry_cache_enabled
    assert not Settings(_env_file=None, registry_cache_mode="disabled").registry_cache_enabled


@pytest.mark.parametrize(
    "miss",
    [
        "missing",
        "expired",
        "wrong_uen",
        "wrong_dataset",
        "incomplete",
        "provider_contract",
        "provider_dataset",
    ],
)
def test_unusable_seed_falls_back_to_configured_provider_without_mixing(miss):
    company = COMPANIES[0]
    repository = InMemoryRegistrySnapshotRepository()
    entry = company.snapshot(NOW)
    if miss == "wrong_uen":
        entry = COMPANIES[1].snapshot(NOW)
    if miss == "wrong_dataset":
        identity = local_synthetic_registry_identity().model_copy(
            update={"dataset_namespace": "WRONG"}
        )
        key = RegistryCacheKey(provider_identity=identity, normalized_identifier=company.uen)
        entry = entry.model_copy(update={"key": key, "cache_id": key.digest})
    if miss == "incomplete":
        from app.connectors.mock_acra import MISSING_OWNERSHIP_UEN, MockAcraConnector

        partial = AcraRegistryProviderAdapter(
            MockAcraConnector(clock=lambda: NOW), clock=lambda: NOW
        ).retrieve_acquisition(MISSING_OWNERSHIP_UEN)
        # Use its valid same-identifier key; query that identifier below.
        key = RegistryCacheKey(
            provider_identity=local_synthetic_registry_identity(),
            normalized_identifier=MISSING_OWNERSHIP_UEN,
        )
        entry = entry.model_copy(
            update={"key": key, "cache_id": key.digest, "acquisition": partial}
        )
    if miss != "missing":
        repository.create(entry)
    calls = []

    class Provider:
        cache_identity = local_synthetic_registry_identity().model_copy(
            update={"dataset_namespace": "ACRA_API_MARKETPLACE_MOCK_V1"}
        )

        def retrieve_acquisition(self, identifier, **kwargs):
            calls.append(identifier)
            return None

    if miss == "provider_contract":
        Provider.cache_identity = Provider.cache_identity.model_copy(
            update={"acquisition_contract_version": "WRONG_CONTRACT"}
        )
    if miss == "provider_dataset":
        Provider.cache_identity = Provider.cache_identity.model_copy(
            update={"dataset_namespace": "WRONG_PROVIDER_DATASET"}
        )
    now = NOW + timedelta(days=90) if miss == "expired" else NOW
    coordinator = RegistryAcquisitionCoordinator(
        repository,
        RegistryFreshnessPolicy(),
        clock=lambda: now,
        local_seed_identity=local_synthetic_registry_identity(),
    )
    identifier = entry.key.normalized_identifier if miss == "incomplete" else company.uen
    assert coordinator.acquire(Provider(), identifier).acquisition is None
    assert calls == [identifier]


def test_database_hit_returns_current_deep_case_copy_and_corruption_fails_closed():
    company = COMPANIES[0]
    repository = InMemoryRegistrySnapshotRepository()
    manage_fixtures(repository, now=NOW, seed=True)
    service = build_onboarding_service(
        settings=Settings(_env_file=None),
        acra_connector=NoAcra(),
        registry_snapshot_repository=repository,
    )
    coordinator = service._registry_acquisition_coordinator
    coordinator._clock = lambda: NOW
    provider = service._registry_router.route("SG", decided_at=NOW)[1]
    first = coordinator.acquire(provider, company.uen)
    assert first.binding.disposition == "CACHE_HIT"
    assert first.binding.bound_to_case_at == NOW
    first.acquisition.entity_profile.legal_name = "changed copy"
    assert (
        coordinator.acquire(provider, company.uen).acquisition.entity_profile.legal_name
        == company.name
    )

    class WrongRepository:
        def get(self, key):
            return COMPANIES[1].snapshot(NOW)

    corrupt = RegistryAcquisitionCoordinator(
        WrongRepository(),
        RegistryFreshnessPolicy(),
        clock=lambda: NOW,
        local_seed_identity=local_synthetic_registry_identity(),
    )
    with pytest.raises(RegistryCacheInvalidError):
        corrupt.acquire(provider, company.uen)
