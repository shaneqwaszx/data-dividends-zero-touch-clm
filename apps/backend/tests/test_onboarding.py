from datetime import UTC, datetime
from uuid import UUID

from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.demo.scenarios import (
    GOLDTIER_FAILURE_UEN,
    GOLDTIER_PARTIAL_UEN,
    INCOMPLETE_ENTITY_UEN,
    VALID_SME_UEN,
    Phase01MockScenarioCatalogue,
)
from app.domain.models import (
    OnboardingCase,
    SourceEnvironment,
    SourceSystem,
    WorkflowState,
)
from app.mappers.acra import map_acra_company
from app.services.errors import OnboardingInfrastructureError
from app.services.onboarding import OnboardingService
from app.services.repository import InMemoryOnboardingCaseRepository

FIXED_TIME = datetime(2026, 8, 10, 2, 0, tzinfo=UTC)


def build_service() -> OnboardingService:
    catalogue = Phase01MockScenarioCatalogue()
    return OnboardingService(
        acra=MockAcraConnector(clock=lambda: FIXED_TIME),
        goldtier=MockGoldTierConnector(
            policy_validation_failure_keys=catalogue.policy_validation_failure_uens(),
            partial_amend_external_keys=catalogue.partial_amend_uens(),
        ),
        repository=InMemoryOnboardingCaseRepository(),
        clock=lambda: FIXED_TIME,
    )


def stages(case_state: OnboardingCase) -> list[WorkflowState]:
    return [event.stage for event in case_state.events]


def run_confirmed_target_flow(service: OnboardingService, uen: str) -> OnboardingCase:
    case = service.create_case(uen)
    if case.state != WorkflowState.VALIDATED:
        return case
    service.confirm_target_dispatch(
        case_id=case.case_id,
        actor_id="onboarding-test-operator",
        expected_case_event_count=len(case.events),
        clm_version=None,
        destination="GOLDTIER_MOCK",
    )
    try:
        return service.submit_staged_case(case.case_id, complete_legacy_flow=True)
    except OnboardingInfrastructureError:
        retained = service.get_case(case.case_id)
        assert retained is not None
        return retained


def test_mock_acra_payload_maps_to_minimum_canonical_entity() -> None:
    payload = MockAcraConnector(clock=lambda: FIXED_TIME).fetch_company(VALID_SME_UEN)

    assert payload is not None
    entity = map_acra_company(payload)

    assert entity.registration_number == VALID_SME_UEN
    assert entity.legal_name == "MERLION CIRCULAR LABS PTE. LTD."
    assert entity.country_of_incorporation == "SG"
    assert entity.registered_address is not None
    assert entity.source.source_system == SourceSystem.ACRA
    assert entity.source.environment == SourceEnvironment.MOCK
    assert entity.source.registry_source_link.endswith(VALID_SME_UEN)


def test_happy_path_progresses_in_order_and_is_persisted() -> None:
    service = build_service()

    case = run_confirmed_target_flow(service, VALID_SME_UEN)

    assert case.state == WorkflowState.COMPLETED
    assert stages(case) == [
        WorkflowState.REQUESTED,
        WorkflowState.REQUESTED,  # Exact-registration target search unsupported by current port.
        WorkflowState.REGISTRY_FETCHED,
        WorkflowState.VALIDATED,
        WorkflowState.VALIDATED,
        WorkflowState.GT_SEARCHED,
        WorkflowState.GT_SHELL_CREATED,
        WorkflowState.GT_POLICY_CREATED,
        WorkflowState.GT_ENRICHED,
        WorkflowState.COMPLETED,
    ]
    assert case.goldtier_result is not None
    assert case.goldtier_result.party_id.startswith("GT-MOCK-")
    assert case.goldtier_result.policy_status == "POLICY_CREATED"
    assert service.get_case(case.case_id) == case
    assert all(event.case_id == case.case_id for event in case.events)
    assert all(event.correlation_id == case.correlation_id for event in case.events)


def test_unknown_uen_fails_safely_before_registry_mapping() -> None:
    case = build_service().create_case("999999999Z")

    assert case.state == WorkflowState.REVIEW_REQUIRED
    assert case.entity is None
    assert case.goldtier_result is None
    assert case.error is not None
    assert case.error.code == "ACRA_ENTITY_NOT_FOUND"
    assert stages(case) == [
        WorkflowState.REQUESTED, WorkflowState.REQUESTED, WorkflowState.REVIEW_REQUIRED,
    ]
    assert case.events[1].code == "GOLDTIER_SEARCH_SKIPPED_UNSUPPORTED_IDENTIFIER"


def test_incomplete_entity_requires_review_before_goldtier() -> None:
    case = build_service().create_case(INCOMPLETE_ENTITY_UEN)

    assert case.state == WorkflowState.REVIEW_REQUIRED
    assert case.entity is not None
    assert case.entity.registered_address is None
    assert case.goldtier_result is None
    assert WorkflowState.GT_SEARCHED not in stages(case)


def test_goldtier_validation_failure_never_reports_completion() -> None:
    service = build_service()
    case = run_confirmed_target_flow(service, GOLDTIER_FAILURE_UEN)

    assert case.state == WorkflowState.FAILED
    assert case.error is not None
    assert case.error.code == "GT_POLICY_VALIDATION_FAILED"
    assert WorkflowState.GT_SHELL_CREATED in stages(case)
    assert WorkflowState.GT_POLICY_CREATED not in stages(case)
    assert WorkflowState.COMPLETED not in stages(case)


def test_partial_amend_is_recorded_and_requires_review() -> None:
    service = build_service()
    case = run_confirmed_target_flow(service, GOLDTIER_PARTIAL_UEN)

    assert case.state == WorkflowState.REVIEW_REQUIRED
    assert case.goldtier_result is not None
    assert case.goldtier_result.amend_status == "PARTIALLY_ENRICHED"
    assert stages(case)[-2:] == [WorkflowState.GT_ENRICHED, WorkflowState.REVIEW_REQUIRED]
    assert WorkflowState.COMPLETED not in stages(case)


def test_identifiers_are_safe_uuid_values() -> None:
    case = build_service().create_case(VALID_SME_UEN)

    assert isinstance(case.case_id, UUID)
    assert isinstance(case.correlation_id, UUID)
    assert case.source_case_id.startswith(f"CASE-{VALID_SME_UEN}-")
