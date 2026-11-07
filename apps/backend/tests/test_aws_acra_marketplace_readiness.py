"""AWS staging readiness for the official ACRA API Marketplace Mock lane.

Every provider call here goes to a recorded fake or the local Mock. No genuine call runs.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError
from scripts.zero_touch_happy_path_fixtures import COMPANIES, GOVERNMENT
from test_evidence_poc_discovery import UnitsRegistry
from test_recursive_ownership_discovery import DISCOVERY, ROOT, Issuer, company, person, policy

from app.composition import (
    build_acra_connector,
    build_acra_diagnostic_service,
    build_onboarding_service,
    build_ownership_analysis_service,
)
from app.config import Settings, get_settings
from app.connectors.acra_api_marketplace_auth import AcraMarketplaceTokenHttpResponse
from app.connectors.acra_api_marketplace_mock import (
    ACRA_API_MARKETPLACE_MOCK_BASE_URL,
    AcraApiMarketplaceMockConnector,
)
from app.connectors.acra_sandbox import AcraHttpResponse
from app.connectors.errors import AcraOperationUnsupportedError
from app.connectors.mock_acra import MockAcraConnector
from app.domain.ownership import OwnershipAnalysisState
from app.services import ownership_analysis
from app.services.registry_cache_repository import InMemoryRegistrySnapshotRepository

CLIENT = "fixture-client-id"
SECRET = "fixture-secret-value"
UEN = "202400001A"
OFFICIAL_ENTITY = f"{ACRA_API_MARKETPLACE_MOCK_BASE_URL}/entityQuery/entityBasicInformation"


def staging(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "staging",
        "clm_persistence_mode": "mongo",
        "mongo_uri": "mongodb://127.0.0.1:1/?tls=true",
        "mongo_database": "clm_staging",
        "phase13_browser_origin": "https://clm-staging.example",
    }
    return Settings(_env_file=None, **(values | overrides))  # type: ignore[arg-type]


def official(**overrides: object) -> Settings:
    return staging(
        acra_connector_mode="api_marketplace_mock",
        acra_api_marketplace_mock_client_id=CLIENT,
        acra_api_marketplace_mock_secret_key=SECRET,
        **overrides,
    )


# Startup configuration


@pytest.mark.parametrize(
    "credentials",
    [
        {},
        {"acra_api_marketplace_mock_client_id": CLIENT},
        {"acra_api_marketplace_mock_secret_key": SECRET},
        {
            "acra_api_marketplace_mock_client_id": "",
            "acra_api_marketplace_mock_secret_key": "",
        },
        {
            "acra_api_marketplace_mock_client_id": CLIENT,
            "acra_api_marketplace_mock_secret_key": "   ",
        },
    ],
    ids=["none", "no-secret", "no-client", "blank", "whitespace"],
)
def test_staging_official_lane_needs_both_credentials(credentials: dict[str, str]) -> None:
    with pytest.raises(ValidationError, match="Marketplace Mock credentials"):
        staging(acra_connector_mode="api_marketplace_mock", **credentials)


def test_staging_local_mock_stays_the_credential_free_default() -> None:
    settings = staging()
    assert settings.acra_connector_mode == "mock"
    assert settings.goldtier_connector_mode == "mock"
    assert isinstance(build_acra_connector(settings), MockAcraConnector)


def test_a_rejected_staging_start_does_not_render_the_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in {
        "APP_ENV": "staging",
        "CLM_PERSISTENCE_MODE": "mongo",
        "MONGO_URI": "mongodb://127.0.0.1:1/?tls=true",
        "MONGO_DATABASE": "clm_staging",
        "ACRA_CONNECTOR_MODE": "api_marketplace_mock",
        "ACRA_API_MARKETPLACE_MOCK_SECRET_KEY": SECRET,
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("ACRA_API_MARKETPLACE_MOCK_CLIENT_ID", raising=False)
    get_settings.cache_clear()
    try:
        with pytest.raises(ValueError, match="^Invalid staging configuration") as failure:
            get_settings()
        assert SECRET not in str(failure.value)
        assert failure.value.__suppress_context__
    finally:
        get_settings.cache_clear()


def test_staging_refuses_the_generic_sandbox_seam() -> None:
    with pytest.raises(ValidationError, match="Mock ACRA connector"):
        staging(acra_connector_mode="sandbox")


# Lane identity


def test_each_lane_composes_its_own_connector_and_label() -> None:
    connector = build_acra_connector(official())
    assert isinstance(connector, AcraApiMarketplaceMockConnector)

    configuration = build_acra_diagnostic_service(connector, official())._configuration  # noqa: SLF001
    assert configuration.provider == "ACRA_API_MARKETPLACE_MOCK"
    assert configuration.classification == "MOCK"
    assert configuration.safe_host == "api-sandbox.bizfile.gov.sg"

    local = build_acra_diagnostic_service(MockAcraConnector(), staging())._configuration  # noqa: SLF001
    assert local.provider == "ACRA_MOCK" and local.safe_host is None


def test_staging_official_lane_composes_no_synthetic_ownership_by_default() -> None:
    settings = official()
    service = composed_ownership(settings)

    assert settings.garden_supplement_enabled is False
    assert settings.acra_marketplace_ownership_overlay == "garden_legacy_supplement"
    assert service._hybrid_overlay is None  # noqa: SLF001


class EmptyHolders:
    """Answers one explicit empty shareholder collection, as the official Mock can."""

    def __init__(self) -> None:
        self.calls = 0

    def get(self, url: str, *, headers: object, timeout_seconds: float) -> AcraHttpResponse:
        self.calls += 1
        return AcraHttpResponse(
            status_code=200,
            body={"entities": []},
            content_type="application/json",
            response_bytes=15,
        )


def token_response(*_: object, **__: object) -> AcraMarketplaceTokenHttpResponse:
    body = json.dumps({
        "access_token": "fixture-token",
        "expires_in": 1799,
        "scope": "fixture",
        "token_type": "fixture",
    }).encode()
    return AcraMarketplaceTokenHttpResponse(
        status_code=200,
        content_type="application/json",
        body=body,
        response_bytes=len(body),
    )


def official_connector(transport: EmptyHolders) -> AcraApiMarketplaceMockConnector:
    return build_acra_connector(  # type: ignore[return-value]
        official(),
        transport=transport,
        marketplace_token_transport=SimpleNamespace(post=token_response),
    )


def test_an_empty_official_register_stays_empty() -> None:
    transport = EmptyHolders()
    payload = official_connector(transport).fetch_ownership_parties(UEN)

    assert payload.ownership_parties == ()
    assert payload.source_environment == "MOCK"
    assert transport.calls == 1


def test_relationships_stop_without_a_provider_call() -> None:
    transport = EmptyHolders()
    with pytest.raises(AcraOperationUnsupportedError):
        official_connector(transport).fetch_relationships(UEN)
    assert transport.calls == 0


# Retained cases from another lane


class OfficialSourceAcra(MockAcraConnector):
    """Synthetic company data carrying the official source reference."""

    def fetch_company(self, uen: str) -> Any:
        company = super().fetch_company(uen)
        return company.model_copy(update={"source_endpoint": OFFICIAL_ENTITY})


def composed_ownership(settings: Settings, acra: MockAcraConnector | None = None) -> Any:
    cases = build_onboarding_service(
        settings=settings,
        acra_connector=acra or MockAcraConnector(),
        registry_snapshot_repository=InMemoryRegistrySnapshotRepository(),
    )
    return build_ownership_analysis_service(cases, settings)


def review_record(service: Any) -> Any:
    case = service._cases.create_staged_case(UEN)  # noqa: SLF001
    return SimpleNamespace(case_id=case.case_id, state=OwnershipAnalysisState.REVIEW_REQUIRED)


@pytest.fixture
def current_analysis(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolates the lane rule: everything else about the analysis is current and eligible."""

    monkeypatch.setattr(
        ownership_analysis.OwnershipAnalysisService,
        "_current_for_readiness",
        lambda *_: True,
    )
    monkeypatch.setattr(ownership_analysis, "poc_acceptance_current", lambda *_: True)
    monkeypatch.setattr(
        ownership_analysis.OwnershipAnalysisService, "_poc_scenario", lambda *_: None
    )


class OfficialUnits(UnitsRegistry):
    """A registry whose evidence carries the official source reference."""

    def _endpoint(self, uen: str, suffix: str = "") -> str:
        return OFFICIAL_ENTITY


def real_lane(registry: type[UnitsRegistry], issuers: dict, seed: Any = None) -> tuple:
    """The composed staging services with nothing about the analysis replaced."""

    now = lambda: datetime.now(UTC)  # noqa: E731
    snapshots = InMemoryRegistrySnapshotRepository()
    if seed is not None:
        snapshots.create(seed.snapshot(now()))
    connector = registry(issuers, now)
    settings = official()
    cases = build_onboarding_service(
        settings=settings,
        acra_connector=connector,
        registry_snapshot_repository=snapshots,
        policy_snapshot_provider=lambda: policy(DISCOVERY),
    )
    return cases, build_ownership_analysis_service(cases, settings)


def analyze(cases: Any, service: Any) -> Any:
    case = cases.create_staged_case(ROOT)
    service.load(case_id=case.case_id)
    return service.analyze(case_id=case.case_id)


UNITS = {ROOT: Issuer("ROOT CO", (person("A", "600"), person("B", "400")))}


def test_a_real_official_analysis_is_accepted_on_its_evidence() -> None:
    _, service = (lane := real_lane(OfficialUnits, UNITS))
    record = analyze(*lane)

    assert record.poc_acceptance is not None
    assert service.poc_basis_accepted(record) is True


def test_a_real_local_mock_analysis_records_no_acceptance() -> None:
    _, service = (lane := real_lane(UnitsRegistry, UNITS))
    record = analyze(*lane)

    assert record.poc_acceptance is None
    assert service.clears_review(record) is False


@pytest.mark.parametrize("seed", COMPANIES[:2], ids=lambda item: item.code)
def test_a_seeded_holder_never_merges_under_an_official_root(seed: Any) -> None:
    issuers = {ROOT: Issuer("ROOT CO", (company(seed.uen, "800"), person("X", "200")))}
    _, service = (lane := real_lane(OfficialUnits, issuers, seed))
    record = analyze(*lane)

    assert not any(seed.code in item.display_name for item in record.parties)
    assert record.poc_acceptance is None
    # D-121: the unresolved holder keeps the review open; it stays advisory, never accepted.
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert service.poc_basis_accepted(record) is False


def test_only_staging_official_stops_reading_seeds_for_provider_lanes() -> None:
    def coordinator(settings: Settings) -> Any:
        cases = build_onboarding_service(
            settings=settings,
            acra_connector=MockAcraConnector(),
            registry_snapshot_repository=InMemoryRegistrySnapshotRepository(),
        )
        return cases._registry_acquisition_coordinator  # noqa: SLF001

    assert coordinator(official())._read_seed_for_provider_lanes is False  # noqa: SLF001
    assert coordinator(staging())._read_seed_for_provider_lanes is True  # noqa: SLF001


@pytest.mark.parametrize("settings", [official, staging], ids=["official", "local"])
def test_the_government_register_stays_available_in_staging(settings: Any) -> None:
    seed = GOVERNMENT
    now = datetime.now(UTC)
    snapshots = InMemoryRegistrySnapshotRepository()
    snapshots.create(seed.snapshot(now))
    cases = build_onboarding_service(
        settings=settings(),
        acra_connector=MockAcraConnector(),
        registry_snapshot_repository=snapshots,
    )

    register = cases._registry_acquisition_coordinator.read_government_register(seed.uen)  # noqa: SLF001

    assert register is not None
    assert register.entity_profile.source.registry_source_link.startswith("local-synthetic:")


@pytest.mark.usefixtures("current_analysis")
def test_a_retained_local_mock_case_gets_no_official_lane_allowance() -> None:
    service = composed_ownership(official())
    record = review_record(service)

    assert service.review_is_advisory(record) is False
    assert service.poc_basis_accepted(record) is False
    assert service.clears_review(record) is False


@pytest.mark.usefixtures("current_analysis")
def test_an_official_case_keeps_the_official_lane_allowances() -> None:
    service = composed_ownership(official(), OfficialSourceAcra())
    record = review_record(service)

    assert service.review_is_advisory(record) is True
    assert service.poc_basis_accepted(record) is True


@pytest.mark.usefixtures("current_analysis")
def test_outside_staging_the_accepted_local_lane_is_unchanged() -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        acra_connector_mode="api_marketplace_mock",
        acra_api_marketplace_mock_client_id=CLIENT,
        acra_api_marketplace_mock_secret_key=SECRET,
    )
    service = composed_ownership(settings)
    record = review_record(service)

    assert service._official_registry_source_prefix is None  # noqa: SLF001
    assert service.review_is_advisory(record) is True
