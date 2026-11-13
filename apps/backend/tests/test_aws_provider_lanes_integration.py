"""Combined ACRA and GoldTier staging lanes, through the real composition.

Every provider call goes to a recorded fake. No genuine provider call runs.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from phase13_test_clients import RawTestClient
from pydantic import ValidationError
from scripts.zero_touch_happy_path_fixtures import COMPANIES, GOVERNMENT
from test_acra_api_marketplace_mock_connector import COMPANY_BODY, SHAREHOLDERS_BODY, UEN
from test_goldtier_xpi_sandbox import FakeXpiTransport, _sandbox_submission

from app.composition import (
    build_clm_orchestration_service,
    build_document_processing_service,
    build_onboarding_service,
    build_ownership_analysis_service,
    build_reconciliation_service,
    build_zero_touch_orchestrator,
)
from app.config import Settings
from app.connectors.acra_api_marketplace_mock import (
    ACRA_API_MARKETPLACE_MOCK_BASE_URL,
    AcraApiMarketplaceMockConnection,
    AcraApiMarketplaceMockConnector,
)
from app.connectors.acra_sandbox import AcraHttpResponse
from app.connectors.goldtier_xpi import GoldTierXpiHttpResponse
from app.connectors.goldtier_xpi_models import XpiCustomerSearchRequest
from app.connectors.mock_acra import MockAcraConnector
from app.main import create_app
from app.persistence.composition import build_persistence_bundle, build_workflow_persistence
from app.services.admin_repository import InMemoryPolicyRepository
from app.services.clm_errors import ClmRequestError
from app.services.clm_repository import InMemoryClmOrchestrationRepository
from app.services.errors import (
    TargetProviderContextMismatchError,
    TargetRegistryProvenanceError,
)
from app.services.policy_management import PolicyManagementService
from app.services.registry_cache_repository import InMemoryRegistrySnapshotRepository
from app.services.repository import InMemoryOnboardingCaseRepository
from app.services.target_execution_repository import InMemoryTargetExecutionRepository
from app.services.zero_touch_repository import InMemoryZeroTouchAutomationRepository

OFFICIAL = f"{ACRA_API_MARKETPLACE_MOCK_BASE_URL}/"
ORIGIN = "https://clm-staging.example"
PROVENANCE = "CLM_TARGET_REGISTRY_PROVENANCE_UNSUPPORTED"


def settings_for(acra: str, target: str, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "staging",
        "clm_persistence_mode": "mongo",
        "mongo_uri": "mongodb://127.0.0.1:1/?tls=true",
        "mongo_database": "clm_staging",
        "phase13_browser_origin": ORIGIN,
        "idp_connector_mode": "mock",
        "acra_connector_mode": acra,
        "goldtier_connector_mode": target,
    }
    if acra == "api_marketplace_mock":
        values |= {
            "acra_api_marketplace_mock_client_id": "fixture-client",
            "acra_api_marketplace_mock_secret_key": "fixture-key",
        }
    if target == "sandbox":
        values |= {
            "goldtier_sandbox_base_url": "https://goldtier.invalid",
            "goldtier_sandbox_environment": "fixture",
            "goldtier_sandbox_user_id": "fixture-user",
            # D-127 E1: staging Sandbox starts only behind the R3 egress proxy.
            "goldtier_sandbox_egress_proxy_url": "http://clm-goldtier-egress:4750",
            "goldtier_sandbox_egress_fqdn": "goldtier.invalid",
        }
    return Settings(_env_file=None, **(values | overrides))  # type: ignore[arg-type]


class OfficialAcraTransport:
    """Answers the official operations with the recorded contract bodies."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def get(self, url: str, *, headers: object, timeout_seconds: float) -> AcraHttpResponse:
        self.calls.append(url)
        body = COMPANY_BODY if "entityBasicInformation" in url else SHAREHOLDERS_BODY
        return AcraHttpResponse(
            status_code=200,
            body=deepcopy(body),
            content_type="application/json",
            response_bytes=100,
        )


class FixtureAuthorizer:
    def authorization_headers(self) -> dict[str, str]:
        return {"token": "fixture-token"}


def official_acra(transport: OfficialAcraTransport) -> AcraApiMarketplaceMockConnector:
    return AcraApiMarketplaceMockConnector(
        connection=AcraApiMarketplaceMockConnection(),
        transport=transport,
        authorizer=FixtureAuthorizer(),
    )


@dataclass
class Durable:
    """What survives a backend replacement in shared staging."""

    cases: Any = field(default_factory=InMemoryOnboardingCaseRepository)
    ledger: Any = field(default_factory=InMemoryTargetExecutionRepository)
    clm: Any = field(default_factory=InMemoryClmOrchestrationRepository)
    automation: Any = field(default_factory=InMemoryZeroTouchAutomationRepository)
    snapshots: Any = field(default_factory=InMemoryRegistrySnapshotRepository)


@dataclass
class Stack:
    settings: Settings
    cases: Any
    clm: Any
    zero: Any
    target: FakeXpiTransport
    durable: Durable
    ownership: Any


def stack(
    settings: Settings,
    acra: Any,
    durable: Durable | None = None,
    responses: list[object] | None = None,
) -> Stack:
    store = durable or Durable()
    target = FakeXpiTransport(responses)
    policy = PolicyManagementService(InMemoryPolicyRepository()).case_snapshot().model_copy(
        update={"goldtier_target": _sandbox_submission().target_policy}, deep=True
    )
    cases = build_onboarding_service(
        settings=settings,
        acra_connector=acra,
        goldtier_transport=target,
        repository=store.cases,
        target_execution_repository=store.ledger,
        registry_snapshot_repository=store.snapshots,
        policy_snapshot_provider=lambda: policy,
    )
    documents = build_document_processing_service(cases, settings)
    ownership = build_ownership_analysis_service(cases, settings, documents=documents)
    reconciliation = build_reconciliation_service(cases, documents)
    clm = build_clm_orchestration_service(
        cases, documents, ownership, reconciliation, repository=store.clm
    )
    zero = build_zero_touch_orchestrator(
        cases, documents, ownership, clm, reconciliation, settings, repository=store.automation
    )
    return Stack(settings, cases, clm, zero, target, store, ownership)


def state(lane: Stack, case_id: Any) -> tuple:
    """Everything a denied operation must leave untouched."""

    case = lane.cases.get_case(case_id)
    return (
        case.model_dump_json(),
        lane.durable.clm.get_for_case(case_id).model_dump_json(),
        tuple(item.model_dump_json() for item in lane.durable.ledger.list_for_case(case_id)),
    )


def confirmation(lane: Stack, case_id: Any) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "actor_id": "maya-lim",
        "expected_clm_version": lane.durable.clm.get_for_case(case_id).version,
        "expected_case_event_count": len(lane.cases.get_case(case_id).events),
    }


def seeded(store: Durable, company: Any) -> Durable:
    store.snapshots.create(company.snapshot(datetime.now(UTC)))
    return store


def search_of(lane: Stack, case_id: Any) -> Any:
    return lane.durable.clm.get_for_case(case_id).target_search_checkpoint


# Staging startup


@pytest.fixture
def offline_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    plain = Settings(_env_file=None, app_env="test")
    bundle = build_persistence_bundle(plain)
    monkeypatch.setattr("app.main.build_persistence_bundle", lambda _: bundle)
    monkeypatch.setattr(
        "app.main.build_workflow_persistence", lambda _: build_workflow_persistence(plain)
    )


@pytest.mark.usefixtures("offline_startup")
@pytest.mark.parametrize("acra", ["mock", "api_marketplace_mock"])
@pytest.mark.parametrize("target", ["mock", "sandbox"])
def test_every_selected_lane_pair_starts_with_writes_off(acra: str, target: str) -> None:
    settings = settings_for(acra, target)

    with RawTestClient(create_app(settings), base_url=ORIGIN) as client:
        assert client.get("/health").json()["environment"] == "staging"

    assert settings.goldtier_sandbox_allow_writes is False
    assert settings.demo_controls_enabled is False


def test_the_defaults_stay_mock() -> None:
    settings = Settings(
        _env_file=None,
        app_env="staging",
        clm_persistence_mode="mongo",
        mongo_uri="mongodb://127.0.0.1:1/?tls=true",
        mongo_database="clm_staging",
        phase13_browser_origin=ORIGIN,
    )
    assert settings.acra_connector_mode == "mock"
    assert settings.goldtier_connector_mode == "mock"


@pytest.mark.parametrize(
    "overrides",
    [
        {"goldtier_sandbox_allow_writes": True},
        {"acra_api_marketplace_mock_secret_key": " "},
        {"goldtier_sandbox_user_id": ""},
        {"mongo_database": "clm_poc"},
    ],
    ids=["writes", "blank-secret", "blank-user", "wrong-database"],
)
def test_unsafe_staging_refuses_to_start(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        settings_for("api_marketplace_mock", "sandbox", **overrides)


# Local Mock keeps working for Government and seeded cases


@pytest.mark.parametrize("acra_mode", ["mock", "api_marketplace_mock"])
def test_government_onboarding_keeps_working_with_mock_goldtier(acra_mode: str) -> None:
    durable = seeded(Durable(), GOVERNMENT)
    lane = stack(settings_for(acra_mode, "mock"), MockAcraConnector(), durable)

    created = lane.zero.create_case(GOVERNMENT.uen, "SG", legal_name=GOVERNMENT.name)

    case = lane.cases.get_case(created.case_id)
    assert case.entity is not None and case.entity.party_type == "GOVERNMENT"
    assert case.entity.source.registry_source_link.startswith("local-synthetic:")
    assert search_of(lane, created.case_id).code != PROVENANCE
    assert lane.target.calls == []


def test_a_seeded_company_keeps_working_on_the_local_lane_with_mock_goldtier() -> None:
    company = COMPANIES[0]
    durable = seeded(Durable(), company)
    lane = stack(settings_for("mock", "mock"), MockAcraConnector(), durable)

    created = lane.zero.create_case(company.uen, "SG", legal_name=company.name)

    case = lane.cases.get_case(created.case_id)
    assert case.entity.source.registry_source_link.startswith("local-synthetic:")
    assert search_of(lane, created.case_id).code != PROVENANCE


# Unverified identities never reach Sandbox


def test_a_government_register_identity_makes_no_sandbox_request() -> None:
    durable = seeded(Durable(), GOVERNMENT)
    lane = stack(settings_for("api_marketplace_mock", "sandbox"), MockAcraConnector(), durable)

    created = lane.zero.create_case(GOVERNMENT.uen, "SG", legal_name=GOVERNMENT.name)

    case = lane.cases.get_case(created.case_id)
    assert case.entity.source.registry_source_link.startswith("local-synthetic:")
    assert search_of(lane, created.case_id).code == PROVENANCE
    assert lane.target.calls == []


def test_a_government_register_identity_gets_no_official_lane_allowance() -> None:
    durable = seeded(Durable(), GOVERNMENT)
    lane = stack(settings_for("api_marketplace_mock", "mock"), MockAcraConnector(), durable)
    created = lane.zero.create_case(GOVERNMENT.uen, "SG", legal_name=GOVERNMENT.name)
    record = SimpleNamespace(case_id=created.case_id, state="REVIEW_REQUIRED")

    assert lane.ownership._on_required_registry_lane(record) is False  # noqa: SLF001
    assert lane.ownership.review_is_advisory(record) is False
    assert lane.ownership.poc_basis_accepted(record) is False


def test_a_local_mock_identity_makes_no_sandbox_request() -> None:
    lane = stack(settings_for("mock", "sandbox"), MockAcraConnector())

    created = lane.zero.create_case("202400001A", "SG", legal_name="ANY TYPED NAME")

    assert search_of(lane, created.case_id).code == PROVENANCE
    assert lane.target.calls == []


def test_a_seed_is_not_used_for_a_company_on_the_official_lane() -> None:
    company = replace(COMPANIES[0], uen=UEN)
    durable = seeded(Durable(), company)
    acra = OfficialAcraTransport()
    lane = stack(
        settings_for("api_marketplace_mock", "sandbox"),
        official_acra(acra),
        durable,
        [GoldTierXpiHttpResponse(status_code=200, body=[])],
    )

    case = lane.cases.create_staged_case(UEN)

    entity = lane.cases.get_case(case.case_id).entity
    assert entity.source.registry_source_link.startswith(OFFICIAL)
    assert entity.legal_name != company.name
    assert acra.calls


# Official identity through to read-only Sandbox


def official_case(durable: Durable | None = None) -> tuple[Stack, Any, OfficialAcraTransport]:
    acra = OfficialAcraTransport()
    lane = stack(
        settings_for("api_marketplace_mock", "sandbox"),
        official_acra(acra),
        durable,
        [GoldTierXpiHttpResponse(status_code=200, body=[]) for _ in range(3)],
    )
    return lane, lane.zero.create_case(UEN, "SG", legal_name="A TYPED NAME"), acra


def test_official_acquisition_drives_one_read_only_search() -> None:
    lane, created, _ = official_case()

    case = lane.cases.get_case(created.case_id)
    assert case.entity.source.registry_source_link.startswith(OFFICIAL)
    assert search_of(lane, created.case_id).status == "COMPLETED"
    assert [call["method"] for call in lane.target.calls] == ["GET"]
    assert "TYPED" not in str(lane.target.calls[0]["url"])


def test_writes_disabled_send_changes_nothing() -> None:
    lane, created, _ = official_case()
    before = state(lane, created.case_id)
    calls = len(lane.target.calls)

    with pytest.raises(ClmRequestError) as refused:
        lane.clm.confirm_target_dispatch(**confirmation(lane, created.case_id))

    assert refused.value.code == "CLM_TARGET_WRITES_DISABLED"
    assert state(lane, created.case_id) == before
    assert len(lane.target.calls) == calls


def test_typed_console_search_changes_nothing() -> None:
    lane, created, _ = official_case()
    before = state(lane, created.case_id)
    calls = len(lane.target.calls)

    with pytest.raises(TargetRegistryProvenanceError):
        lane.cases.search_sandbox_target(
            XpiCustomerSearchRequest(legal_name="ANY NAME", country_of_incorporation="SG"),
            correlation_id=created.case_id,
        )

    assert state(lane, created.case_id) == before
    assert len(lane.target.calls) == calls


# Provider-mode changes on retained data


def test_a_retained_local_case_cannot_cross_into_sandbox() -> None:
    durable = Durable()
    local = stack(settings_for("mock", "mock"), MockAcraConnector(), durable)
    created = local.zero.create_case("202400001A", "SG", legal_name="ANY TYPED NAME")
    assert local.cases.get_case(created.case_id).entity is not None

    flipped = stack(
        settings_for("api_marketplace_mock", "sandbox"),
        official_acra(OfficialAcraTransport()),
        durable,
    )
    before = state(flipped, created.case_id)

    with pytest.raises(ClmRequestError) as refused:
        flipped.clm.confirm_target_dispatch(**confirmation(flipped, created.case_id))

    assert refused.value.code == PROVENANCE
    assert state(flipped, created.case_id) == before
    flipped.clm.evaluate(case_id=created.case_id)
    assert search_of(flipped, created.case_id).code == PROVENANCE
    assert flipped.target.calls == []


def test_an_official_case_frozen_for_mock_goldtier_refuses_sandbox_search() -> None:
    durable = Durable()
    acra = OfficialAcraTransport()
    mock_target = stack(settings_for("api_marketplace_mock", "mock"), official_acra(acra), durable)
    created = mock_target.zero.create_case(UEN, "SG", legal_name="A TYPED NAME")
    plan = durable.clm.get_for_case(created.case_id).submission_plan
    assert plan.environment == "MOCK"

    sandbox = stack(settings_for("api_marketplace_mock", "sandbox"), official_acra(acra), durable)

    with pytest.raises(TargetProviderContextMismatchError):
        sandbox.cases.search_target_identity(
            case_id=created.case_id,
            request_id=created.case_id,
            provider_mode=plan.environment,
            searched_at=datetime.now(UTC),
        )
    assert sandbox.target.calls == []


def test_returning_to_mock_goldtier_keeps_sandbox_state_inert() -> None:
    durable = Durable()
    lane, created, _ = official_case(durable)
    plan = durable.clm.get_for_case(created.case_id).submission_plan
    assert plan.environment == "SANDBOX"

    back = stack(settings_for("api_marketplace_mock", "mock"), MockAcraConnector(), durable)

    with pytest.raises(TargetProviderContextMismatchError):
        back.cases.search_target_identity(
            case_id=created.case_id,
            request_id=created.case_id,
            provider_mode=plan.environment,
            searched_at=datetime.now(UTC),
        )
    assert durable.ledger.list_for_case(created.case_id) == ()
    assert lane.target.calls and back.target.calls == []
