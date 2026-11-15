"""AWS staging readiness for GoldTier Sandbox: read-only by default, provenance-bound.

Every provider call here goes to a recorded fake transport. No genuine Sandbox call runs.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from urllib.parse import quote_plus

import pytest
from pydantic import ValidationError
from test_goldtier_xpi_sandbox import (
    PDF,
    FakeXpiTransport,
    _confirm_service_submission,
    _sandbox_zero_touch_system,
    _xpi_connector,
    _xpi_onboarding_service,
)

from app.composition import STAGING_SANDBOX_IDENTITY_POLICY, build_onboarding_service
from app.config import Settings
from app.connectors.acra_api_marketplace_mock import (
    ACRA_API_MARKETPLACE_MOCK_BASE_URL,
    AcraApiMarketplaceMockConnection,
    _query_free_provenance,
)
from app.connectors.goldtier_xpi import GoldTierXpiHttpResponse
from app.connectors.goldtier_xpi_models import XpiCustomerSearchRequest
from app.connectors.mock_acra import MockAcraConnector
from app.domain.models import (
    InitialCustomerIdentity,
    SourceEnvironment,
    SourceSystem,
    WorkflowState,
)
from app.domain.target_identity_evidence import (
    AcceptedIdentitySource,
    TargetIdentityEvidencePolicy,
)
from app.domain.target_submission import GoldTierSearchResolution
from app.services.clm_errors import ClmRequestError
from app.services.errors import TargetRegistryProvenanceError, TargetWritesDisabledError
from app.services.registry_cache_repository import InMemoryRegistrySnapshotRepository
from app.services.zero_touch_errors import ZeroTouchRequestError

OFFICIAL_PREFIX = f"{ACRA_API_MARKETPLACE_MOCK_BASE_URL}/"
OFFICIAL_ENTITY = f"{OFFICIAL_PREFIX}entityQuery/entityBasicInformation"
UEN = "202400001A"


def ok(body: object) -> GoldTierXpiHttpResponse:
    return GoldTierXpiHttpResponse(status_code=200, body=body)


def full_path_transport() -> FakeXpiTransport:
    return FakeXpiTransport([
        ok({"goldTierId": 12345}),
        ok({}),
        ok({}),
        ok([{"goldTierId": 12345}]),
    ])


def methods(transport: FakeXpiTransport) -> list[object]:
    return [call["method"] for call in transport.calls]


def set_writes(service: Any, transport: FakeXpiTransport, *, allowed: bool) -> None:
    service._goldtier = _xpi_connector(transport, allow_writes=allowed)  # noqa: SLF001


def staged_submission(service: Any) -> Any:
    case = service.create_staged_case(UEN)
    submission = service.build_submission_input(case, provider_mode="SANDBOX")
    _confirm_service_submission(service, submission)
    return submission


def advance(service: Any, submission: Any) -> Any:
    return service.advance_incremental_submission_input(
        submission,
        search_resolution=GoldTierSearchResolution.NO_MATCH,
        selected_party_id=None,
    )


class OfficialSourceAcra(MockAcraConnector):
    """Synthetic company data carrying the given source reference."""

    def __init__(self, source: str = OFFICIAL_ENTITY) -> None:
        super().__init__()
        self._source = source

    def fetch_company(self, uen: str) -> Any:
        company = super().fetch_company(uen)
        return company.model_copy(update={"source_endpoint": self._source})


def staging_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "staging",
        "clm_persistence_mode": "mongo",
        "mongo_uri": "mongodb://127.0.0.1:1/?tls=true",
        "mongo_database": "clm_staging",
        "phase13_browser_origin": "https://clm-staging.example",
        "goldtier_connector_mode": "sandbox",
        "goldtier_sandbox_base_url": "https://goldtier.invalid",
        "goldtier_sandbox_environment": "fixture",
        "goldtier_sandbox_user_id": "fixture-user",
        # D-127 E1: staging Sandbox starts only behind the R3 egress proxy.
        "goldtier_sandbox_egress_proxy_url": "http://clm-goldtier-egress:4750",
        "goldtier_sandbox_egress_fqdn": "goldtier.invalid",
    }
    return Settings(_env_file=None, **(values | overrides))  # type: ignore[arg-type]


def composed(settings: Settings, transport: FakeXpiTransport) -> Any:
    return build_onboarding_service(
        settings=settings,
        acra_connector=MockAcraConnector(),
        goldtier_transport=transport,
        registry_snapshot_repository=InMemoryRegistrySnapshotRepository(),
    )


# Read-only lane


def read_only_case_at_confirmation() -> tuple[Any, FakeXpiTransport, Any]:
    transport = FakeXpiTransport([ok([])])
    zero, _, _ = _sandbox_zero_touch_system(transport)
    set_writes(zero._cases, transport, allowed=False)  # noqa: SLF001
    created = zero.create_case(UEN)
    record = zero.attach_document(
        case_id=created.case_id,
        display_name="sandbox-profile.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    assert any(
        item.exception_type == "TARGET_CONFIRMATION_REQUIRED"
        for item in record.active_exceptions
    )
    return zero, transport, record


def confirmation(zero: Any, record: Any) -> dict[str, Any]:
    case = zero._cases.get_case(record.case_id)  # noqa: SLF001
    clm = zero._clm.get(case_id=record.case_id)  # noqa: SLF001
    return {
        "case_id": record.case_id,
        "actor_id": "sandbox-test-operator",
        "expected_automation_version": record.version,
        "expected_clm_version": clm.version,
        "expected_case_event_count": len(case.events),
    }


def test_read_only_send_is_refused_and_burns_nothing() -> None:
    zero, transport, record = read_only_case_at_confirmation()
    before = zero._cases.get_case(record.case_id)  # noqa: SLF001

    with pytest.raises(ZeroTouchRequestError) as refused:
        zero.confirm_target_dispatch(**confirmation(zero, record))

    assert refused.value.code == "CLM_TARGET_WRITES_DISABLED"
    case = zero._cases.get_case(record.case_id)  # noqa: SLF001
    assert case.state == before.state and case.state != WorkflowState.FAILED
    assert len(case.events) == len(before.events)
    assert case.target_dispatch_confirmation is None
    assert zero._cases.has_retained_target_execution(record.case_id) is False  # noqa: SLF001
    assert methods(transport) == ["GET"]


def test_a_refused_case_sends_normally_once_writes_are_enabled() -> None:
    zero, transport, record = read_only_case_at_confirmation()
    with pytest.raises(ZeroTouchRequestError):
        zero.confirm_target_dispatch(**confirmation(zero, record))

    # Confirmation repeats the read-only Search, then runs the full path once.
    transport.responses.extend([ok([]), *full_path_transport().responses])
    set_writes(zero._cases, transport, allowed=True)  # noqa: SLF001
    zero.confirm_target_dispatch(**confirmation(zero, record))

    assert methods(transport) == ["GET", "GET", "POST", "POST", "POST", "GET"]
    result = zero._cases.get_case(record.case_id).goldtier_result  # noqa: SLF001
    assert result is not None and result.party_id == "12345"


def test_writes_disabled_after_confirmation_stops_before_the_first_ledger_entry() -> None:
    zero, transport, record = read_only_case_at_confirmation()
    set_writes(zero._cases, transport, allowed=True)  # noqa: SLF001
    arguments = confirmation(zero, record)
    del arguments["expected_automation_version"]
    transport.responses.append(ok([]))
    zero._clm.confirm_target_dispatch(**arguments)  # noqa: SLF001
    set_writes(zero._cases, transport, allowed=False)  # noqa: SLF001

    with pytest.raises(ClmRequestError) as refused:
        zero._clm.submit(case_id=record.case_id)  # noqa: SLF001

    assert refused.value.code == "CLM_TARGET_WRITES_DISABLED"
    assert zero._cases.has_retained_target_execution(record.case_id) is False  # noqa: SLF001
    assert methods(transport) == ["GET", "GET"]


@pytest.mark.parametrize(
    ("completed_steps", "attempted"),
    [
        (0, ()),
        (1, ("SEARCH", "SHELL")),
        (2, ("SEARCH", "SHELL", "POLICY")),
    ],
    ids=["before-shell", "before-policy", "before-amend"],
)
def test_rollback_mid_flow_keeps_the_ledger_resumable_without_replay(
    completed_steps: int, attempted: tuple[str, ...]
) -> None:
    transport = FakeXpiTransport([ok([]), *full_path_transport().responses])
    service = _xpi_onboarding_service(transport)
    submission = staged_submission(service)
    transport.calls.clear()
    transport.responses.pop(0)
    for _ in range(completed_steps):
        assert advance(service, submission) is None

    set_writes(service, transport, allowed=False)
    posts_before = methods(transport).count("POST")
    state_before = service.get_case(submission.case_id).state
    with pytest.raises(TargetWritesDisabledError):
        advance(service, submission)

    assert methods(transport).count("POST") == posts_before == completed_steps
    assert service.get_case(submission.case_id).state == state_before
    assert service.get_attempted_target_operations(submission.submission_id) == attempted
    assert service.is_execution_outcome_uncertain(submission.submission_id) is False

    set_writes(service, transport, allowed=True)
    receipt = None
    while receipt is None:
        receipt = advance(service, submission)
    assert receipt.classification == "SUCCESS"
    assert methods(transport).count("POST") == 3


class WritesOffAfterShell(FakeXpiTransport):
    """Turns writes off as soon as the Shell has answered, as a rollback restart would."""

    def __init__(self, responses: list[object]) -> None:
        super().__init__(responses)
        self.service: Any = None

    def request(self, method: str, url: str, **options: Any) -> object:
        response = super().request(method, url, **options)
        if method == "POST" and url.endswith("/customers/create"):
            set_writes(self.service, self, allowed=False)
        return response


def test_rollback_pauses_automation_and_the_same_submission_continues() -> None:
    transport = WritesOffAfterShell([ok([])])
    zero, _, _ = _sandbox_zero_touch_system(transport)
    cases = zero._cases  # noqa: SLF001
    transport.service = cases
    created = zero.create_case(UEN)
    record = zero.attach_document(
        case_id=created.case_id,
        display_name="sandbox-profile.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    transport.responses.extend([ok([]), *full_path_transport().responses])

    paused = zero.confirm_target_dispatch(**confirmation(zero, record))

    assert paused.status == "RECOVERY_PENDING" and paused.technical_failure is None
    case = cases.get_case(created.case_id)
    assert case.state == WorkflowState.GT_SHELL_CREATED
    assert methods(transport).count("POST") == 1

    set_writes(cases, transport, allowed=True)
    finished = zero.start(case_id=created.case_id)

    assert finished.status == "COMPLETED"
    assert methods(transport).count("POST") == 3
    assert cases.get_case(created.case_id).goldtier_result.party_id == "12345"


def test_a_restart_between_ledger_entry_and_shell_burns_nothing() -> None:
    transport = FakeXpiTransport([ok([])])
    service = _xpi_onboarding_service(transport)
    submission = staged_submission(service)
    transport.calls.clear()
    # A crash after the Search-only entry was saved, before the Shell call.
    service._start_incremental_execution(  # noqa: SLF001
        submission,
        search_resolution=GoldTierSearchResolution.NO_MATCH,
        selected_party_id=None,
    )
    set_writes(service, transport, allowed=False)

    with pytest.raises(TargetWritesDisabledError):
        advance(service, submission)

    assert service.get_attempted_target_operations(submission.submission_id) == ("SEARCH",)
    assert service.is_execution_outcome_uncertain(submission.submission_id) is False
    assert service.get_case(submission.case_id).state != WorkflowState.FAILED
    assert transport.calls == []


def test_exact_id_readback_still_completes_after_writes_are_disabled() -> None:
    transport = FakeXpiTransport([ok([]), *full_path_transport().responses])
    service = _xpi_onboarding_service(transport)
    submission = staged_submission(service)
    transport.calls.clear()
    transport.responses.pop(0)
    for _ in range(3):
        assert advance(service, submission) is None

    set_writes(service, transport, allowed=False)
    receipt = advance(service, submission)

    assert receipt.classification == "SUCCESS" and receipt.result.party_id == "12345"
    assert transport.calls[-1]["method"] == "GET"
    assert transport.calls[-1]["url"].endswith("/customers/search?goldTierID=12345")


def test_legacy_execution_refuses_before_the_ledger_when_writes_are_disabled() -> None:
    transport = FakeXpiTransport([ok([])])
    service = _xpi_onboarding_service(transport)
    submission = staged_submission(service)
    transport.calls.clear()
    set_writes(service, transport, allowed=False)

    with pytest.raises(TargetWritesDisabledError):
        service.execute_submission_input(submission)

    assert transport.calls == []
    assert service.has_retained_target_execution(submission.case_id) is False


def test_typed_console_criteria_never_leave_under_an_identity_policy() -> None:
    transport = FakeXpiTransport()
    settings = staging_settings()
    service = composed(settings, transport)
    correlation = service.create_staged_case(UEN).correlation_id

    for request in (
        XpiCustomerSearchRequest(legal_name=NAME, country_of_incorporation="SG"),
        XpiCustomerSearchRequest(group_company_name=NAME),
        XpiCustomerSearchRequest(goldtier_id="12345", legal_name=NAME),
    ):
        with pytest.raises(TargetRegistryProvenanceError):
            service.search_sandbox_target(request, correlation_id=correlation)

    assert transport.calls == []


def test_console_exact_id_search_is_available_read_only() -> None:
    transport = FakeXpiTransport([ok([{"goldTierId": 12345}])])
    settings = staging_settings(acra_connector_mode="api_marketplace_mock",
                                acra_api_marketplace_mock_client_id="fixture-client",
                                acra_api_marketplace_mock_secret_key="fixture-key")
    service = composed(settings, transport)

    evidence = service.search_sandbox_target(
        XpiCustomerSearchRequest(goldtier_id="12345"),
        correlation_id=service.create_staged_case(UEN).correlation_id,
    )

    assert service.target_writes_enabled is False
    assert evidence.result.matched_party_id == "12345"
    assert methods(transport) == ["GET"]


# Staging configuration


@pytest.mark.parametrize("target_mode", ["mock", "sandbox"])
def test_staging_rejects_sandbox_writes(target_mode: str) -> None:
    with pytest.raises(ValidationError, match="sandbox writes"):
        staging_settings(
            goldtier_connector_mode=target_mode, goldtier_sandbox_allow_writes=True
        )


def test_writes_stay_available_outside_staging() -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        goldtier_connector_mode="sandbox",
        goldtier_sandbox_base_url="https://goldtier.invalid",
        goldtier_sandbox_environment="fixture",
        goldtier_sandbox_user_id="fixture-user",
        goldtier_sandbox_allow_writes=True,
    )
    assert composed(settings, FakeXpiTransport()).target_writes_enabled is True


def test_mock_target_reports_writes_enabled_and_needs_no_provenance() -> None:
    service = composed(staging_settings(goldtier_connector_mode="mock"), FakeXpiTransport())
    assert service.target_writes_enabled is True
    assert service._target_identity_policy is None  # noqa: SLF001


def test_only_staging_sandbox_binds_the_official_registry_source() -> None:
    staging = composed(staging_settings(), FakeXpiTransport())
    assert staging._target_identity_policy is STAGING_SANDBOX_IDENTITY_POLICY  # noqa: SLF001
    local = composed(
        Settings(
            _env_file=None,
            app_env="test",
            goldtier_connector_mode="sandbox",
            goldtier_sandbox_base_url="https://goldtier.invalid",
            goldtier_sandbox_environment="fixture",
            goldtier_sandbox_user_id="fixture-user",
        ),
        FakeXpiTransport(),
    )
    assert local._target_identity_policy is None  # noqa: SLF001


# Registry provenance at the Sandbox boundary


def bound_service(transport: FakeXpiTransport, acra: MockAcraConnector) -> Any:
    service = _xpi_onboarding_service(transport, acra_connector=acra)
    service._target_identity_policy = STAGING_SANDBOX_IDENTITY_POLICY  # noqa: SLF001
    return service


def search(service: Any, case: Any) -> Any:
    return service.search_target_identity(
        case_id=case.case_id,
        request_id=case.correlation_id,
        provider_mode="SANDBOX",
        searched_at=case.created_at,
    )


@pytest.mark.parametrize(
    "source",
    [
        "https://mock.acra.gov.sg/api/entities/202400001A",
        "https://api-sandbox.bizfile.gov.sg/api/acrafake/entityQuery",
    ],
    ids=["local-mock", "prefix-lookalike"],
)
def test_other_registry_lanes_never_reach_a_sandbox_search(source: str) -> None:
    transport = FakeXpiTransport()
    service = bound_service(transport, OfficialSourceAcra(source))
    case = service.create_staged_case(UEN)

    with pytest.raises(TargetRegistryProvenanceError):
        search(service, case)

    assert transport.calls == []


def test_a_local_seed_identity_never_reaches_a_sandbox_search() -> None:
    transport = FakeXpiTransport()
    service = bound_service(transport, OfficialSourceAcra())
    case = service.create_staged_case(UEN)
    seeded = case.entity.source.model_copy(
        update={"registry_source_link": "local-synthetic:LOCAL_SYNTHETIC_UAT_V1:GAMMA"}
    )
    stored = case.model_copy(update={"entity": case.entity.model_copy(update={"source": seeded})})
    service.case_repository.save(stored)

    with pytest.raises(TargetRegistryProvenanceError):
        search(service, stored)

    assert transport.calls == []


def test_official_marketplace_identity_reaches_the_sandbox_search() -> None:
    transport = FakeXpiTransport([ok([])])
    service = bound_service(transport, OfficialSourceAcra())
    case = service.create_staged_case(UEN)

    assert search(service, case).result.outcome == "NO_MATCH"
    assert methods(transport) == ["GET"]


def test_a_blocked_case_records_a_visible_search_failure() -> None:
    transport = FakeXpiTransport()
    zero, _, _ = _sandbox_zero_touch_system(transport)
    zero._cases._target_identity_policy = STAGING_SANDBOX_IDENTITY_POLICY  # noqa: SLF001

    created = zero.create_case(UEN)

    checkpoint = zero._clm.get(case_id=created.case_id).target_search_checkpoint  # noqa: SLF001
    assert checkpoint.status == "FAILED"
    assert checkpoint.code == "CLM_TARGET_REGISTRY_PROVENANCE_UNSUPPORTED"
    assert transport.calls == []


NAME = "MERLION CIRCULAR LABS PTE. LTD."


def bound_system(transport: FakeXpiTransport) -> Any:
    zero, _, _ = _sandbox_zero_touch_system(transport, reviewed_test_enrichment=False)
    zero._cases._target_identity_policy = STAGING_SANDBOX_IDENTITY_POLICY  # noqa: SLF001
    return zero


def retained_search(zero: Any, case_id: Any) -> Any:
    return zero._clm.get(case_id=case_id).target_search_checkpoint  # noqa: SLF001


@pytest.mark.parametrize(
    "candidates",
    [[], [{"goldTierId": 777, "registrationNumber": UEN, "countryOfIncorporation": "SG"}]],
    ids=["no-match", "exact-match"],
)
def test_a_typed_name_search_never_stands_on_local_mock_evidence(candidates: list) -> None:
    transport = FakeXpiTransport([ok(candidates)])
    zero = bound_system(transport)

    created = zero.create_case(UEN, "SG", legal_name=NAME)

    search_result = retained_search(zero, created.case_id)
    assert search_result.status == "FAILED"
    assert search_result.selected_party_id is None
    assert search_result.code == "CLM_TARGET_REGISTRY_PROVENANCE_UNSUPPORTED"
    assert not any(
        item.exception_type == "TARGET_CONFIRMATION_REQUIRED"
        for item in created.active_exceptions
    )
    # Neither the typed name nor the registry name left the process.
    assert transport.calls == []


def test_a_typed_name_waits_for_accepted_evidence_then_searches_on_it() -> None:
    transport = FakeXpiTransport([ok([])])
    zero, _, _ = _sandbox_zero_touch_system(
        transport, reviewed_test_enrichment=False, acra_connector=OfficialSourceAcra()
    )
    zero._cases._target_identity_policy = STAGING_SANDBOX_IDENTITY_POLICY  # noqa: SLF001

    created = zero.create_case(UEN, "SG", legal_name="A DIFFERENT TYPED NAME")

    case = zero._cases.get_case(created.case_id)  # noqa: SLF001
    assert case.initial_target_search is None
    assert retained_search(zero, created.case_id).status == "COMPLETED"
    assert len(transport.calls) == 1
    assert "DIFFERENT" not in str(transport.calls[0]["url"])
    assert quote_plus(case.entity.legal_name) in str(transport.calls[0]["url"])


@pytest.mark.parametrize(
    ("kind", "source", "accepted"),
    [
        ("Private Company Limited by Shares", OFFICIAL_ENTITY, True),
        ("Statutory Board", OFFICIAL_ENTITY, True),
        ("Private Company Limited by Shares", "https://mock.acra.gov.sg/api/entities/X", False),
        ("Statutory Board", "local-synthetic:LOCAL_SYNTHETIC_UAT_V1:GOV", False),
    ],
    ids=["company-official", "government-official", "company-local", "government-seed"],
)
def test_the_rule_follows_provenance_not_entity_type(
    kind: str, source: str, accepted: bool
) -> None:
    entity = SimpleNamespace(
        party_type=kind,
        source=SimpleNamespace(
            source_system=SourceSystem.ACRA,
            environment=SourceEnvironment.MOCK,
            registry_source_link=source,
        ),
    )
    assert STAGING_SANDBOX_IDENTITY_POLICY.accepts(entity) is accepted


def test_a_future_source_joins_without_loosening_the_rest() -> None:
    government = AcceptedIdentitySource(
        source_system=SourceSystem.ACRA,
        environment=SourceEnvironment.SANDBOX,
        reference_prefix="https://authority.invalid/identity/",
    )
    policy = TargetIdentityEvidencePolicy(
        (*STAGING_SANDBOX_IDENTITY_POLICY.accepted_sources, government)
    )

    def entity(environment: SourceEnvironment, link: str) -> Any:
        return SimpleNamespace(source=SimpleNamespace(
            source_system=SourceSystem.ACRA, environment=environment, registry_source_link=link,
        ))

    assert policy.accepts(entity(SourceEnvironment.SANDBOX, "https://authority.invalid/identity/1"))
    assert not policy.accepts(
        entity(SourceEnvironment.MOCK, "https://authority.invalid/identity/1")
    )
    assert not policy.accepts(entity(SourceEnvironment.MOCK, "https://mock.acra.gov.sg/x"))
    empty = TargetIdentityEvidencePolicy(())
    assert not empty.accepts(entity(SourceEnvironment.MOCK, OFFICIAL_ENTITY))
    assert not policy.accepts(None)
    with pytest.raises(ValueError, match="path boundary"):
        AcceptedIdentitySource(SourceSystem.ACRA, SourceEnvironment.MOCK, "https://a.invalid/x")


@pytest.mark.parametrize(
    "response",
    [
        GoldTierXpiHttpResponse(status_code=400, body={}),
        GoldTierXpiHttpResponse(status_code=500, body={}),
    ],
    ids=["rejected", "unavailable"],
)
def test_a_failed_same_identity_recheck_stays_recoverable(
    response: GoldTierXpiHttpResponse,
) -> None:
    transport = FakeXpiTransport([response, response, ok([])])
    zero, _, _ = _sandbox_zero_touch_system(transport, reviewed_test_enrichment=False)
    created = zero.create_case(UEN, "SG", legal_name=NAME)

    def recheck(record: Any) -> Any:
        case = zero._cases.get_case(record.case_id)  # noqa: SLF001
        clm = zero._clm.get(case_id=record.case_id)  # noqa: SLF001
        return zero.repair_initial_identity_and_recheck(
            case_id=record.case_id,
            actor_id="maya-lim",
            legal_name=NAME,
            registration_number=UEN,
            country_of_incorporation="SG",
            expected_automation_version=record.version,
            expected_clm_version=clm.version,
            expected_case_event_count=len(case.events),
        )

    failed = recheck(created)
    assert failed.status == "TECHNICAL_FAILURE"
    assert failed.current_stage == "GOLDTIER_SEARCH"
    assert zero._cases.has_retained_target_execution(created.case_id) is False  # noqa: SLF001

    recovered = recheck(failed)
    assert recovered.status != "TECHNICAL_FAILURE"
    assert retained_search(zero, created.case_id).status == "COMPLETED"
    assert methods(transport) == ["GET", "GET", "GET"]


def test_registry_evidence_from_another_lane_is_never_sent_on_recheck() -> None:
    transport = FakeXpiTransport()
    zero = bound_system(transport)
    created = zero.create_case(UEN)
    case = zero._cases.get_case(created.case_id)  # noqa: SLF001
    clm = zero._clm.get(case_id=created.case_id)  # noqa: SLF001

    zero.repair_initial_identity_and_recheck(
        case_id=created.case_id,
        actor_id="sandbox-test-operator",
        legal_name="ANY TYPED NAME",
        registration_number=UEN,
        country_of_incorporation="SG",
        expected_automation_version=created.version,
        expected_clm_version=clm.version,
        expected_case_event_count=len(case.events),
        verify_registry=True,
        identity_choice="ENTERED",
    )

    assert transport.calls == []
    assert retained_search(zero, created.case_id).status == "FAILED"


def test_a_recheck_result_is_voided_at_once_on_refused_evidence() -> None:
    transport = FakeXpiTransport([ok([]), ok([])])
    zero, _, _ = _sandbox_zero_touch_system(transport, reviewed_test_enrichment=False)
    created = zero.create_case(UEN, "SG", legal_name=NAME)
    cases, clm = zero._cases, zero._clm  # noqa: SLF001
    case = cases.get_case(created.case_id)
    cases._target_identity_policy = STAGING_SANDBOX_IDENTITY_POLICY  # noqa: SLF001
    assert case.entity is not None

    # A completed recheck reaching CLM while the case holds refused evidence.
    stored = clm._repository.get_for_case(created.case_id)  # noqa: SLF001
    clm.refresh_initial_search_after_recheck(
        case_id=created.case_id, expected_clm_version=stored.version
    )

    saved = clm._repository.get_for_case(created.case_id)  # noqa: SLF001
    assert saved.version > stored.version
    assert saved.target_search_checkpoint.status == "FAILED"
    assert saved.target_search_checkpoint.code == "CLM_TARGET_REGISTRY_PROVENANCE_UNSUPPORTED"


def official_system(responses: list[object]) -> tuple[Any, FakeXpiTransport]:
    transport = FakeXpiTransport(responses)
    zero, _, _ = _sandbox_zero_touch_system(
        transport, reviewed_test_enrichment=False, acra_connector=OfficialSourceAcra()
    )
    zero._cases._target_identity_policy = STAGING_SANDBOX_IDENTITY_POLICY  # noqa: SLF001
    return zero, transport


def test_a_same_identity_recheck_searches_the_accepted_identity_only() -> None:
    zero, transport = official_system([ok([]), ok([])])
    created = zero.create_case(UEN, "SG", legal_name="A DIFFERENT TYPED NAME")
    case = zero._cases.get_case(created.case_id)  # noqa: SLF001
    clm = zero._clm.get(case_id=created.case_id)  # noqa: SLF001

    zero.repair_initial_identity_and_recheck(
        case_id=created.case_id,
        actor_id="maya-lim",
        legal_name="A DIFFERENT TYPED NAME",
        registration_number=UEN,
        country_of_incorporation="SG",
        expected_automation_version=created.version,
        expected_clm_version=clm.version,
        expected_case_event_count=len(case.events),
    )

    assert len(transport.calls) == 2
    assert all("DIFFERENT" not in str(call["url"]) for call in transport.calls)
    assert all(quote_plus(case.entity.legal_name) in str(call["url"]) for call in transport.calls)


@pytest.mark.parametrize(
    "change",
    [
        {"legal_name": "DOCUMENT SUPPLIED NAME"},
        {"registration_number": "202499999Z"},
        {"country_of_incorporation": "AU"},
    ],
    ids=["name", "registration", "country"],
)
def test_an_edited_identity_loses_acceptance_despite_its_source_label(
    change: dict[str, str],
) -> None:
    zero, transport = official_system([ok([])])
    created = zero.create_case(UEN, "SG", legal_name=NAME)
    cases = zero._cases  # noqa: SLF001
    case = cases.get_case(created.case_id)
    assert cases.target_registry_evidence_refused(case) is False
    calls = len(transport.calls)

    edited = case.model_copy(update={"entity": case.entity.model_copy(update=change)})
    cases.case_repository.save(edited)

    assert cases.target_registry_evidence_refused(edited) is True
    # A country outside the route is refused even earlier, by canonical validation.
    with pytest.raises((TargetRegistryProvenanceError, ValueError)):
        search(cases, edited)
    assert len(transport.calls) == calls


def test_a_recheck_ending_in_review_waits_for_review() -> None:
    transport = FakeXpiTransport([ok([]), ok([{"goldTierId": 777, "registrationNumber": UEN,
                                               "countryOfIncorporation": "SG"}])])
    zero, _, _ = _sandbox_zero_touch_system(transport, reviewed_test_enrichment=False)
    created = zero.create_case(UEN, "SG", legal_name="A DIFFERENT TYPED NAME")
    case = zero._cases.get_case(created.case_id)  # noqa: SLF001
    clm = zero._clm.get(case_id=created.case_id)  # noqa: SLF001

    waiting = zero.repair_initial_identity_and_recheck(
        case_id=created.case_id,
        actor_id="maya-lim",
        legal_name="A DIFFERENT TYPED NAME",
        registration_number=UEN,
        country_of_incorporation="SG",
        expected_automation_version=created.version,
        expected_clm_version=clm.version,
        expected_case_event_count=len(case.events),
    )

    assert retained_search(zero, created.case_id).status == "REVIEW_REQUIRED"
    assert waiting.status == "WAITING_FOR_REVIEW"
    assert waiting.current_stage == "GOLDTIER_SEARCH"
    assert [item.exception_type for item in waiting.active_exceptions] == [
        "ENTITY_RESOLUTION_REVIEW_REQUIRED"
    ]
    assert methods(transport) == ["GET", "GET"]


def test_a_changed_name_review_claims_no_registry_stage() -> None:
    candidate = {"goldTierId": 777, "legalName": "X"}
    transport = FakeXpiTransport([ok([]), ok([candidate, {**candidate, "goldTierId": 778}])])
    zero, _, _ = _sandbox_zero_touch_system(transport, reviewed_test_enrichment=False)
    created = zero.create_case(UEN, "SG", legal_name=NAME)
    case = zero._cases.get_case(created.case_id)  # noqa: SLF001
    clm = zero._clm.get(case_id=created.case_id)  # noqa: SLF001

    waiting = zero.repair_initial_identity_and_recheck(
        case_id=created.case_id,
        actor_id="maya-lim",
        legal_name="A CORRECTED NAME",
        registration_number=UEN,
        country_of_incorporation="SG",
        expected_automation_version=created.version,
        expected_clm_version=clm.version,
        expected_case_event_count=len(case.events),
    )

    assert waiting.status == "WAITING_FOR_REVIEW"
    assert zero._cases.get_case(created.case_id).entity is None  # noqa: SLF001
    assert waiting.completed_stages == ()


def test_a_prior_case_without_accepted_evidence_is_not_reused() -> None:
    zero, _ = official_system([ok([])])
    cases = zero._cases  # noqa: SLF001
    created = zero.create_case(UEN, "SG", legal_name=NAME)
    accepted = cases.get_case(created.case_id)
    local = accepted.model_copy(deep=True)
    local.entity.source.registry_source_link = "https://mock.acra.gov.sg/api/entities/X"
    arguments = {
        "registration_number": UEN,
        "legal_name": NAME,
        "country_of_incorporation": "SG",
        "party_id": "777",
    }

    cases._repository.find_verified_target_case = lambda **_: local  # noqa: SLF001
    assert cases._find_verified_target_case(**arguments) is None  # noqa: SLF001

    # D-137 / D-126 item 2: accepted evidence alone is not reuse proof in Sandbox either. A
    # prior case is reused only with a finalized, verified ledger entry for the current mode.
    cases._repository.find_verified_target_case = lambda **_: accepted  # noqa: SLF001
    assert cases._find_verified_target_case(**arguments) is None  # noqa: SLF001


def finalized_sandbox_case() -> tuple[Any, Any, Any]:
    """An official case whose full Sandbox submission finalized and read back verified."""
    transport = FakeXpiTransport([
        ok([]),
        ok([]),
        ok({"goldTierId": 12345}),
        ok({}),
        ok({}),
        ok([{"goldTierId": 12345}]),
    ])
    # Reviewed enrichment, so the submission runs the full path: Shell, Policy, Amend, readback.
    zero, _, _ = _sandbox_zero_touch_system(transport, acra_connector=OfficialSourceAcra())
    zero._cases._target_identity_policy = STAGING_SANDBOX_IDENTITY_POLICY  # noqa: SLF001
    cases = zero._cases  # noqa: SLF001
    case = cases.get_case(zero.create_case(UEN, "SG", legal_name=NAME).case_id)
    submission = cases.build_submission_input(case, provider_mode="SANDBOX")
    _confirm_service_submission(cases, submission)
    assert cases.execute_submission_input(submission).classification == "SUCCESS"
    # Search at creation and at send, then Shell, Policy, Amend and the exact-ID readback.
    assert methods(transport) == ["GET", "GET", "POST", "POST", "POST", "GET"]
    return zero, cases, cases.get_case(case.case_id)


REUSE = {
    "registration_number": UEN,
    "legal_name": NAME,
    "country_of_incorporation": "SG",
    "party_id": "12345",
}


def test_a_finalized_sandbox_ledger_is_reuse_proof_under_the_staging_policy() -> None:
    # D-137 W6: positive path. The accepted official prior case is reused because its own
    # finalized, read-back-verified ledger entry was written in the current (Sandbox) mode.
    _, cases, prior = finalized_sandbox_case()
    assert cases.target_provider_mode == "SANDBOX"
    found = cases._find_verified_target_case(**REUSE)  # noqa: SLF001
    assert found is not None and found.case_id == prior.case_id


def test_a_finalized_ledger_from_another_mode_is_not_reuse_proof() -> None:
    # D-137 W6: the same finalized ledger, recorded under Mock, proves nothing in Sandbox.
    _, cases, prior = finalized_sandbox_case()
    ledger = cases._target_executions  # noqa: SLF001
    entries = ledger.list_for_case(prior.case_id)
    assert entries
    as_mock = tuple(
        entry.model_copy(
            update={
                "submission_input": entry.submission_input.model_copy(
                    update={"provider_mode": "MOCK"}
                )
            }
        )
        for entry in entries
    )
    ledger.list_for_case = lambda _case_id: as_mock
    assert cases._find_verified_target_case(**REUSE) is None  # noqa: SLF001


@pytest.mark.parametrize(
    ("mode", "source"),
    [
        ("MOCK", OFFICIAL_ENTITY),
        ("SANDBOX", "https://mock.acra.gov.sg/api/entities/X"),
    ],
    ids=["mock-submission", "refused-evidence"],
)
def test_shell_recovery_reads_nothing_without_accepted_sandbox_evidence(
    mode: str, source: str
) -> None:
    zero, transport = official_system([ok([])])
    cases = zero._cases  # noqa: SLF001
    case = cases.get_case(zero.create_case(UEN, "SG", legal_name=NAME).case_id)
    submission = cases.build_submission_input(case, provider_mode=mode)
    case.entity.source.registry_source_link = source
    cases.case_repository.save(case)
    calls = len(transport.calls)

    with pytest.raises(ValueError, match="accepted Sandbox submission evidence"):
        cases.recover_uncertain_shell_from_provider(
            submission_input=submission,
            recovered_party_id="999",
            legal_name=case.entity.legal_name,
            registration_number=UEN,
            country_of_incorporation="SG",
            actor_id="director",
            origin="HISTORICAL_LOCAL_LEDGER_LOST",
        )

    assert len(transport.calls) == calls


def test_policy_recovery_records_nothing_on_refused_evidence() -> None:
    zero, _ = official_system([ok([])])
    cases = zero._cases  # noqa: SLF001
    case = cases.get_case(zero.create_case(UEN, "SG", legal_name=NAME).case_id)
    submission = cases.build_submission_input(case, provider_mode="SANDBOX")
    case.entity.source.registry_source_link = "https://mock.acra.gov.sg/api/entities/X"
    cases.case_repository.save(case)

    with pytest.raises(ValueError, match="accepted Sandbox submission evidence"):
        cases.recover_uncertain_policy_from_provider(
            submission_input=submission,
            recovered_party_id="999",
            legal_name=case.entity.legal_name,
            registration_number=UEN,
            country_of_incorporation="SG",
            provider_policy="Singapore",
            provider_policy_status="Requested",
            actor_id="director",
            origin="UNCERTAIN_DURABLE_LEDGER",
        )

    assert cases.has_retained_target_execution(case.case_id) is False


def test_a_whitespace_sandbox_user_id_refuses_to_start() -> None:
    with pytest.raises(ValidationError):
        staging_settings(goldtier_sandbox_user_id="   ")


def test_an_existing_customer_cannot_be_confirmed_on_refused_evidence() -> None:
    transport = FakeXpiTransport([ok([{"goldTierId": 777, "legalName": NAME}])])
    zero, _, _ = _sandbox_zero_touch_system(transport, reviewed_test_enrichment=False)
    created = zero.create_case(UEN, "SG", legal_name=NAME)
    clm = zero._clm.get(case_id=created.case_id)  # noqa: SLF001
    case = zero._cases.get_case(created.case_id)  # noqa: SLF001
    zero._cases._target_identity_policy = STAGING_SANDBOX_IDENTITY_POLICY  # noqa: SLF001

    with pytest.raises(ClmRequestError) as refused:
        zero._clm.confirm_existing_customer(  # noqa: SLF001
            case_id=created.case_id,
            actor_id="maya-lim",
            search_request_id=clm.target_search_checkpoint.request_id,
            expected_clm_version=clm.version,
            expected_case_event_count=len(case.events),
            rationale="Compared retained candidate with independent registry evidence.",
        )

    assert refused.value.code == "CLM_TARGET_REGISTRY_PROVENANCE_UNSUPPORTED"
    assert retained_search(zero, created.case_id).confirmation is None


def test_the_real_connector_reference_satisfies_the_staging_prefix() -> None:
    endpoint = AcraApiMarketplaceMockConnection().company_endpoint(UEN)
    assert _query_free_provenance(endpoint) == OFFICIAL_ENTITY
    assert OFFICIAL_ENTITY.startswith(OFFICIAL_PREFIX)


def test_a_retained_search_does_not_open_the_confirm_gate() -> None:
    zero, transport, record = read_only_case_at_confirmation()
    arguments = confirmation(zero, record)
    del arguments["expected_automation_version"]
    # A retained Search must not count as a prior write.
    assert zero._clm.attempted_target_operations(case_id=record.case_id) == ("SEARCH",)  # noqa: SLF001

    with pytest.raises(ClmRequestError) as refused:
        zero._clm.confirm_target_dispatch(**arguments)  # noqa: SLF001

    assert refused.value.code == "CLM_TARGET_WRITES_DISABLED"
    assert methods(transport) == ["GET"]


def test_read_only_send_refuses_even_an_existing_customer_with_no_write() -> None:
    exact = {"goldTierId": 777, "registrationNumber": UEN, "countryOfIncorporation": "SG"}
    transport = FakeXpiTransport([ok([exact]), ok([exact])])
    zero, _, _ = _sandbox_zero_touch_system(transport, reviewed_test_enrichment=False)
    created = zero.create_case(UEN, "SG", legal_name=NAME)
    record = zero.attach_document(
        case_id=created.case_id,
        display_name="sandbox-profile.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    arguments = confirmation(zero, record)
    del arguments["expected_automation_version"]
    zero._clm.confirm_target_dispatch(**arguments)  # noqa: SLF001
    assert retained_search(zero, created.case_id).disposition == "EXACT_MATCH"
    set_writes(zero._cases, transport, allowed=False)  # noqa: SLF001
    calls = len(transport.calls)

    with pytest.raises(ClmRequestError) as refused:
        zero._clm.submit(case_id=created.case_id)  # noqa: SLF001

    # Read-only means no Send at all, so not even the exact-ID readback runs.
    assert refused.value.code == "CLM_TARGET_WRITES_DISABLED"
    assert len(transport.calls) == calls
    assert zero._cases.has_retained_target_execution(created.case_id) is False  # noqa: SLF001


def test_a_read_never_shows_a_retained_search_as_usable_on_refused_evidence() -> None:
    transport = FakeXpiTransport([ok([])])
    zero, _, _ = _sandbox_zero_touch_system(transport, reviewed_test_enrichment=False)
    created = zero.create_case(UEN, "SG", legal_name=NAME)
    clm = zero._clm  # noqa: SLF001
    assert retained_search(zero, created.case_id).status == "COMPLETED"
    before = clm.get(case_id=created.case_id).readiness.model_dump_json()
    zero._cases._target_identity_policy = STAGING_SANDBOX_IDENTITY_POLICY  # noqa: SLF001

    read = clm.get(case_id=created.case_id)

    # The read path masks the stale decision without persisting a change.
    stored = clm._repository.get_for_case(created.case_id)  # noqa: SLF001
    assert stored.target_search_checkpoint.status == "COMPLETED"
    assert read.readiness.model_dump_json() != before
    assert "GOLDTIER_SEARCH" in read.readiness.model_dump_json()


def test_a_recheck_sends_the_accepted_country_not_a_typed_one() -> None:
    zero, transport = official_system([ok([]), ok([])])
    created = zero.create_case(UEN, "SG", legal_name=NAME)
    cases = zero._cases  # noqa: SLF001
    case = cases.get_case(created.case_id)
    typed = InitialCustomerIdentity(
        legal_name="ANY TYPED NAME", registration_number=UEN, country_of_incorporation="AU",
    )

    cases._run_initial_identity_search(  # noqa: SLF001
        case, identity=typed, request_id=case.correlation_id
    )

    url = str(transport.calls[-1]["url"])
    assert "countryOfIncorporation=SG" in url and "AU" not in url
    assert "TYPED" not in url


def test_a_mismatched_case_is_refused_before_the_ledger() -> None:
    transport = FakeXpiTransport([ok([])])
    service = _xpi_onboarding_service(transport)
    submission = staged_submission(service)
    transport.calls.clear()
    service._target_identity_policy = STAGING_SANDBOX_IDENTITY_POLICY  # noqa: SLF001

    with pytest.raises(TargetRegistryProvenanceError):
        advance(service, submission)
    with pytest.raises(TargetRegistryProvenanceError):
        service.execute_submission_input(submission)

    assert transport.calls == []
    assert service.has_retained_target_execution(submission.case_id) is False


# D-137: one bounded write window (switch, operations, exact cases, end time)

from datetime import UTC, datetime, timedelta  # noqa: E402

from pydantic import SecretStr  # noqa: E402

from app.connectors.goldtier_write_policy import (  # noqa: E402
    GoldTierSandboxWritePolicy,
    GoldTierWritePolicyError,
)
from app.connectors.goldtier_xpi import (  # noqa: E402
    GoldTierXpiSandboxConnection,
    GoldTierXpiSandboxConnector,
    GoldTierXpiWritesDisabledError,
)

T0 = datetime(2026, 11, 15, 9, 0, tzinfo=UTC)


class Clock:
    def __init__(self, now: datetime = T0) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def windowed(
    case_references: frozenset[str],
    *,
    operations: frozenset[str] = frozenset({"SHELL", "POLICY", "AMEND"}),
    not_after: datetime | None = T0 + timedelta(hours=2),
) -> GoldTierSandboxWritePolicy:
    return GoldTierSandboxWritePolicy(
        enabled=True,
        operations=operations,
        case_references=case_references,
        not_after=not_after,
    )


def set_window(
    service: Any,
    transport: FakeXpiTransport,
    policy: GoldTierSandboxWritePolicy,
    clock: Clock,
) -> None:
    service._goldtier = GoldTierXpiSandboxConnector(  # noqa: SLF001
        connection=GoldTierXpiSandboxConnection(
            base_url="https://sandbox.goldtier.invalid",
            environment="synthetic",
            user_id=SecretStr("backend-only-user"),
            timeout_seconds=7.5,
            max_response_bytes=4096,
            allow_writes=policy.enabled,
            write_policy=policy,
        ),
        transport=transport,
        clock=clock,
    )


def window_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "goldtier_sandbox_allow_writes": True,
        "goldtier_sandbox_write_operations": "SHELL",
        "goldtier_sandbox_write_case_references": "CASE-202400001A-0000abcd",
        "goldtier_sandbox_writes_not_after": datetime.now(UTC) + timedelta(hours=2),
    }
    return staging_settings(**(values | overrides))


def test_d137_a_complete_window_lets_staging_start_with_writes_open() -> None:
    settings = window_settings()
    policy = settings.goldtier_sandbox_write_policy()

    assert policy.operations == {"SHELL"}
    assert policy.case_references == {"CASE-202400001A-0000abcd"}
    assert composed(settings, FakeXpiTransport()).target_writes_enabled is True


@pytest.mark.parametrize(
    "overrides",
    [
        {"goldtier_sandbox_write_case_references": ""},
        {"goldtier_sandbox_write_case_references": " , "},
        {"goldtier_sandbox_write_operations": ""},
        {"goldtier_sandbox_writes_not_after": None},
        {"goldtier_sandbox_writes_not_after": datetime.now(UTC) + timedelta(hours=25)},
    ],
    ids=["no-cases", "blank-cases", "no-operations", "no-end", "end-beyond-24h"],
)
def test_d137_staging_refuses_an_incomplete_window(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError, match="staging does not permit GoldTier sandbox writes"):
        window_settings(**overrides)


def test_d137_staging_requires_operations_to_be_named_not_defaulted() -> None:
    values: dict[str, object] = {
        "goldtier_sandbox_allow_writes": True,
        "goldtier_sandbox_write_case_references": "CASE-202400001A-0000abcd",
        "goldtier_sandbox_writes_not_after": datetime.now(UTC) + timedelta(hours=2),
    }
    with pytest.raises(ValidationError, match="D-137 write window"):
        staging_settings(**values)


@pytest.mark.parametrize(
    "overrides",
    [
        {"goldtier_sandbox_write_operations": "SHELL,RP_POLICY"},
        {"goldtier_sandbox_write_operations": "DELETE"},
        {"goldtier_sandbox_writes_not_after": datetime(2026, 11, 15, 12, 0)},
        {"goldtier_sandbox_write_case_references": ",".join(f"CASE-{n}" for n in range(11))},
    ],
    ids=["related-party-op", "unknown-op", "naive-end", "too-many-cases"],
)
def test_d137_a_malformed_window_never_starts(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        window_settings(**overrides)


def test_d137_an_ended_window_still_starts_and_keeps_writes_off() -> None:
    settings = window_settings(
        goldtier_sandbox_writes_not_after=datetime.now(UTC) - timedelta(minutes=1)
    )
    assert composed(settings, FakeXpiTransport()).target_writes_enabled is False


def test_d137_outside_staging_the_plain_switch_is_unchanged() -> None:
    policy = Settings(
        _env_file=None, app_env="test", goldtier_sandbox_allow_writes=True
    ).goldtier_sandbox_write_policy()
    assert policy.operations == {"SHELL", "POLICY", "AMEND"}
    assert policy.case_references == frozenset() and policy.not_after is None
    assert policy.open_at(T0 + timedelta(days=3650)) is True


def test_d137_policy_rejects_unknown_operations_and_naive_end() -> None:
    with pytest.raises(GoldTierWritePolicyError):
        GoldTierSandboxWritePolicy(enabled=True, operations=frozenset({"RP_AMEND"}))
    with pytest.raises(GoldTierWritePolicyError):
        GoldTierSandboxWritePolicy(enabled=True, not_after=datetime(2026, 11, 15))


def test_d137_connector_refuses_an_unlisted_case_or_operation_without_a_call() -> None:
    transport = FakeXpiTransport([ok({"goldTierId": 12345})])
    service = _xpi_onboarding_service(transport)
    submission = staged_submission(service)
    transport.calls.clear()
    clock = Clock()
    listed = submission.source_case_id
    for policy in (
        windowed(frozenset({"CASE-OTHER-00000000"})),
        windowed(frozenset({listed}), operations=frozenset({"POLICY"})),
    ):
        set_window(service, transport, policy, clock)
        connector = service._goldtier  # noqa: SLF001
        with pytest.raises(GoldTierXpiWritesDisabledError):
            connector.create_shell_customer(
                service._goldtier_mapper.build_shell_request(submission),  # noqa: SLF001
                service._metadata(submission, submission.idempotency.shell),  # noqa: SLF001
            )
    assert transport.calls == []


def test_d137_an_unlisted_case_is_refused_before_anything_is_recorded() -> None:
    zero, transport, record = read_only_case_at_confirmation()
    cases = zero._cases  # noqa: SLF001
    before = cases.get_case(record.case_id)
    set_window(cases, transport, windowed(frozenset({"CASE-OTHER-00000000"})), Clock())

    with pytest.raises(ZeroTouchRequestError) as refused:
        zero.confirm_target_dispatch(**confirmation(zero, record))

    assert refused.value.code == "CLM_TARGET_WRITES_DISABLED"
    case = cases.get_case(record.case_id)
    assert case.state == before.state and case.state != WorkflowState.FAILED
    assert case.target_dispatch_confirmation is None
    assert cases.has_retained_target_execution(record.case_id) is False
    assert methods(transport) == ["GET"]


def test_d137_a_listed_case_sends_inside_the_window() -> None:
    zero, transport, record = read_only_case_at_confirmation()
    cases = zero._cases  # noqa: SLF001
    with pytest.raises(ZeroTouchRequestError):
        zero.confirm_target_dispatch(**confirmation(zero, record))
    listed = cases.get_case(record.case_id).source_case_id
    transport.responses.extend([ok([]), *full_path_transport().responses])
    set_window(cases, transport, windowed(frozenset({listed})), Clock())

    zero.confirm_target_dispatch(**confirmation(zero, record))

    assert methods(transport) == ["GET", "GET", "POST", "POST", "POST", "GET"]
    result = cases.get_case(record.case_id).goldtier_result
    assert result is not None and result.party_id == "12345"


def test_d137_an_operation_outside_the_window_pauses_then_resumes_without_replay() -> None:
    transport = FakeXpiTransport([ok([]), *full_path_transport().responses])
    service = _xpi_onboarding_service(transport)
    submission = staged_submission(service)
    transport.calls.clear()
    transport.responses.pop(0)
    clock = Clock()
    listed = frozenset({submission.source_case_id})
    set_window(service, transport, windowed(listed, operations=frozenset({"SHELL"})), clock)

    assert advance(service, submission) is None  # Search entry and Shell
    with pytest.raises(TargetWritesDisabledError):
        advance(service, submission)  # Policy is outside the window

    assert methods(transport).count("POST") == 1
    assert service.get_attempted_target_operations(submission.submission_id) == (
        "SEARCH",
        "SHELL",
    )
    assert service.is_execution_outcome_uncertain(submission.submission_id) is False
    assert service.get_case(submission.case_id).state != WorkflowState.FAILED

    set_window(service, transport, windowed(listed), clock)
    receipt = None
    while receipt is None:
        receipt = advance(service, submission)
    assert receipt.classification == "SUCCESS"
    assert methods(transport).count("POST") == 3


def test_d137_a_window_that_ends_mid_flow_pauses_and_a_new_window_resumes() -> None:
    transport = FakeXpiTransport([ok([]), *full_path_transport().responses])
    service = _xpi_onboarding_service(transport)
    submission = staged_submission(service)
    transport.calls.clear()
    transport.responses.pop(0)
    clock = Clock()
    listed = frozenset({submission.source_case_id})
    set_window(service, transport, windowed(listed), clock)
    assert advance(service, submission) is None  # Search entry and Shell, inside

    clock.now = T0 + timedelta(hours=2)  # exactly the end instant: closed
    assert service.target_writes_enabled is False
    with pytest.raises(TargetWritesDisabledError):
        advance(service, submission)
    assert methods(transport).count("POST") == 1
    assert service.is_execution_outcome_uncertain(submission.submission_id) is False

    set_window(service, transport, windowed(listed, not_after=T0 + timedelta(hours=4)), clock)
    receipt = None
    while receipt is None:
        receipt = advance(service, submission)
    assert receipt.classification == "SUCCESS"
    assert methods(transport).count("POST") == 3


def test_d137_readback_completes_after_the_window_ends() -> None:
    transport = FakeXpiTransport([ok([]), *full_path_transport().responses])
    service = _xpi_onboarding_service(transport)
    submission = staged_submission(service)
    transport.calls.clear()
    transport.responses.pop(0)
    clock = Clock()
    set_window(service, transport, windowed(frozenset({submission.source_case_id})), clock)
    for _ in range(3):
        assert advance(service, submission) is None

    clock.now = T0 + timedelta(days=1)
    receipt = advance(service, submission)

    assert receipt.classification == "SUCCESS" and receipt.result.party_id == "12345"
    assert transport.calls[-1]["method"] == "GET"


def test_d137_the_legacy_one_shot_path_needs_every_operation_in_the_window() -> None:
    transport = FakeXpiTransport([ok([]), *full_path_transport().responses])
    service = _xpi_onboarding_service(transport)
    submission = staged_submission(service)
    transport.calls.clear()
    listed = frozenset({submission.source_case_id})
    set_window(service, transport, windowed(listed, operations=frozenset({"SHELL"})), Clock())

    with pytest.raises(TargetWritesDisabledError):
        service.execute_submission_input(submission)

    assert transport.calls == []
    assert service.has_retained_target_execution(submission.case_id) is False
    assert service.get_case(submission.case_id).state != WorkflowState.FAILED


def test_d137_a_blank_end_time_means_no_end_outside_staging_only() -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        goldtier_sandbox_allow_writes=True,
        goldtier_sandbox_writes_not_after="  ",
    )
    assert settings.goldtier_sandbox_write_policy().not_after is None
    with pytest.raises(ValidationError, match="D-137 write window"):
        window_settings(goldtier_sandbox_writes_not_after="")
