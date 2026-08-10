"""Synchronous onboarding across configured ACRA and Mock GoldTier boundaries."""

import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Never, TypeVar
from uuid import UUID, uuid4

from app.connectors.acra import AcraConnector
from app.connectors.errors import ConnectorError, public_connector_error
from app.connectors.goldtier import GoldTierConnector
from app.connectors.goldtier_models import (
    GoldTierOutcome,
    GoldTierRequestMetadata,
    GoldTierSearchOutcome,
)
from app.domain.models import (
    CanonicalLegalEntity,
    EventOutcome,
    GoldTierResult,
    OnboardingCase,
    SafeError,
    WorkflowEvent,
    WorkflowState,
)
from app.mappers.acra import map_acra_company
from app.mappers.errors import MappingError
from app.mappers.goldtier import (
    build_amend_request,
    build_policy_request,
    build_search_request,
    build_shell_request,
)
from app.services.errors import OnboardingInfrastructureError
from app.services.repository import OnboardingCaseRepository

UEN_PATTERN = re.compile(r"^[0-9]{9}[A-Z]$")
T = TypeVar("T")


class OnboardingService:
    """Run the minimal complete flow while preserving terminal failure semantics."""

    def __init__(
        self,
        acra: AcraConnector,
        goldtier: GoldTierConnector,
        repository: OnboardingCaseRepository,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self._acra = acra
        self._goldtier = goldtier
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4

    def create_case(self, uen: str) -> OnboardingCase:
        now = self._clock()
        case_id = self._uuid_factory()
        correlation_id = self._uuid_factory()
        normalised_uen = uen.strip().upper()
        if not normalised_uen:
            raise ValueError("Onboarding service requires a normalized non-empty UEN")

        source_case_id = f"CASE-{normalised_uen}-{str(case_id)[:8]}"
        case = OnboardingCase(
            case_id=case_id,
            source_case_id=source_case_id,
            correlation_id=correlation_id,
            requested_uen=normalised_uen,
            state=WorkflowState.REQUESTED,
            created_at=now,
            updated_at=now,
        )
        self._record(case, WorkflowState.REQUESTED, EventOutcome.SUCCEEDED, "Case requested.")

        source_payload = self._run_required_stage(
            case,
            code="ACRA_RETRIEVAL_UNEXPECTED_FAILURE",
            message="Corporate registry retrieval could not be completed.",
            operation=lambda: self._acra.fetch_company(normalised_uen),
        )
        if source_payload is None:
            return self._terminate(
                case,
                WorkflowState.FAILED,
                EventOutcome.FAILED,
                "ACRA_ENTITY_NOT_FOUND",
                "No ACRA entity was found for this UEN.",
            )

        try:
            entity = map_acra_company(source_payload)
        except MappingError:
            self._raise_terminal_infrastructure(
                case,
                code="ACRA_SOURCE_MAPPING_FAILED",
                message="Registry data could not be mapped safely.",
            )
        except Exception:
            self._raise_terminal_infrastructure(
                case,
                code="ACRA_MAPPING_UNEXPECTED_FAILURE",
                message="Registry data could not be mapped safely.",
            )
        case.entity = entity
        self._record(
            case,
            WorkflowState.REGISTRY_FETCHED,
            EventOutcome.SUCCEEDED,
            f"Company information retrieved from ACRA {entity.source.environment.value}.",
        )

        validation_errors = validate_entity(entity)
        if validation_errors:
            return self._terminate(
                case,
                WorkflowState.REVIEW_REQUIRED,
                EventOutcome.REVIEW_REQUIRED,
                "CANONICAL_DATA_INCOMPLETE",
                "Human review required: " + "; ".join(validation_errors),
            )
        self._record(
            case,
            WorkflowState.VALIDATED,
            EventOutcome.SUCCEEDED,
            "Canonical presence checks passed.",
        )

        search = self._run_required_stage(
            case,
            code="GT_SEARCH_UNEXPECTED_FAILURE",
            message="GoldTier party search could not be completed.",
            operation=lambda: self._goldtier.search_party(
                build_search_request(entity), self._metadata(case)
            ),
        )
        if search.outcome == GoldTierSearchOutcome.MATCH_FOUND:
            self._record(
                case,
                WorkflowState.GT_SEARCHED,
                EventOutcome.SUCCEEDED,
                "Existing GoldTier party candidate found; duplicate shell creation was skipped.",
            )
            return self._terminate(
                case,
                WorkflowState.REVIEW_REQUIRED,
                EventOutcome.REVIEW_REQUIRED,
                "GT_EXISTING_PARTY_REVIEW_REQUIRED",
                "An existing GoldTier party candidate requires human review.",
            )
        if search.outcome == GoldTierSearchOutcome.FAILURE:
            return self._terminate(
                case,
                WorkflowState.FAILED,
                EventOutcome.FAILED,
                "GT_SEARCH_FAILED",
                "GoldTier party search returned a controlled failure.",
            )
        if search.outcome != GoldTierSearchOutcome.NO_MATCH:
            return self._terminate(
                case,
                WorkflowState.FAILED,
                EventOutcome.FAILED,
                "GT_SEARCH_RESULT_UNSUPPORTED",
                "GoldTier party search returned an unsupported result.",
            )
        self._record(
            case,
            WorkflowState.GT_SEARCHED,
            EventOutcome.SUCCEEDED,
            "Mock GoldTier search completed; no existing party was found.",
        )

        shell = self._run_required_stage(
            case,
            code="GT_SHELL_UNEXPECTED_FAILURE",
            message="GoldTier shell customer creation could not be completed.",
            operation=lambda: self._goldtier.create_shell_customer(
                build_shell_request(entity, case.source_case_id, self._clock()),
                self._metadata(case),
            ),
        )
        if shell.outcome != GoldTierOutcome.SUCCESS or shell.party_id is None:
            return self._goldtier_failure(case, shell.error_code, shell.message)
        party_id = shell.party_id
        case.goldtier_result = GoldTierResult(
            party_id=party_id,
            shell_status=shell.status,
        )
        self._record(
            case,
            WorkflowState.GT_SHELL_CREATED,
            EventOutcome.SUCCEEDED,
            "Mock GoldTier shell customer created.",
        )

        policy = self._run_required_stage(
            case,
            code="GT_POLICY_UNEXPECTED_FAILURE",
            message="GoldTier policy creation could not be completed.",
            operation=lambda: self._goldtier.create_policy(
                build_policy_request(
                    entity, party_id, case.source_case_id, self._clock()
                ),
                self._metadata(case),
            ),
        )
        case.goldtier_result.policy_status = policy.status
        if policy.outcome != GoldTierOutcome.SUCCESS or policy.policy_id is None:
            return self._goldtier_failure(case, policy.error_code, policy.message)
        case.goldtier_result.policy_id = policy.policy_id
        self._record(
            case,
            WorkflowState.GT_POLICY_CREATED,
            EventOutcome.SUCCEEDED,
            "Mock Singapore policy created.",
        )

        amend = self._run_required_stage(
            case,
            code="GT_AMEND_UNEXPECTED_FAILURE",
            message="GoldTier party enrichment could not be completed.",
            operation=lambda: self._goldtier.amend_party(
                party_id,
                build_amend_request(entity, case.source_case_id, self._clock()),
                self._metadata(case),
            ),
        )
        case.goldtier_result.amend_status = amend.status
        if amend.outcome == GoldTierOutcome.PARTIAL_SUCCESS:
            self._record(
                case,
                WorkflowState.GT_ENRICHED,
                EventOutcome.PARTIAL,
                amend.message,
                amend.error_code,
            )
            return self._terminate(
                case,
                WorkflowState.REVIEW_REQUIRED,
                EventOutcome.REVIEW_REQUIRED,
                amend.error_code or "GT_PARTIAL_SUCCESS",
                "Human review required for the partial mock GoldTier amendment.",
            )
        if amend.outcome != GoldTierOutcome.SUCCESS:
            return self._goldtier_failure(case, amend.error_code, amend.message)
        self._record(
            case,
            WorkflowState.GT_ENRICHED,
            EventOutcome.SUCCEEDED,
            "Mock GoldTier party enriched.",
        )
        self._record(
            case,
            WorkflowState.COMPLETED,
            EventOutcome.SUCCEEDED,
            "Required onboarding stages completed with Mock GoldTier.",
        )
        return case.model_copy(deep=True)

    def get_case(self, case_id: UUID) -> OnboardingCase | None:
        return self._repository.get(case_id)

    def _metadata(self, case: OnboardingCase) -> GoldTierRequestMetadata:
        return GoldTierRequestMetadata(
            correlation_id=case.correlation_id,
            source_case_id=case.source_case_id,
            idempotency_key=self._uuid_factory(),
        )

    def _run_required_stage(
        self,
        case: OnboardingCase,
        *,
        code: str,
        message: str,
        operation: Callable[[], T],
    ) -> T:
        try:
            return operation()
        except ConnectorError as exc:
            public_error = public_connector_error(exc)
            self._raise_terminal_infrastructure(
                case,
                code=public_error.code,
                message=public_error.message,
            )
        except Exception:
            self._raise_terminal_infrastructure(case, code=code, message=message)

    def _raise_terminal_infrastructure(
        self,
        case: OnboardingCase,
        *,
        code: str,
        message: str,
    ) -> Never:
        self._terminate(
            case,
            WorkflowState.FAILED,
            EventOutcome.FAILED,
            code,
            message,
        )
        raise OnboardingInfrastructureError(
            case_id=case.case_id,
            correlation_id=case.correlation_id,
            code=code,
            public_message=message,
        ) from None

    def _record(
        self,
        case: OnboardingCase,
        stage: WorkflowState,
        outcome: EventOutcome,
        message: str,
        code: str | None = None,
    ) -> None:
        timestamp = self._clock()
        case.state = stage
        case.updated_at = timestamp
        case.events.append(
            WorkflowEvent(
                sequence=len(case.events) + 1,
                stage=stage,
                outcome=outcome,
                timestamp=timestamp,
                case_id=case.case_id,
                correlation_id=case.correlation_id,
                code=code,
                message=message,
            )
        )
        self._repository.save(case)

    def _terminate(
        self,
        case: OnboardingCase,
        state: WorkflowState,
        outcome: EventOutcome,
        code: str,
        message: str,
    ) -> OnboardingCase:
        case.error = SafeError(code=code, message=message)
        self._record(case, state, outcome, message, code)
        return case.model_copy(deep=True)

    def _goldtier_failure(
        self, case: OnboardingCase, code: str | None, message: str
    ) -> OnboardingCase:
        return self._terminate(
            case,
            WorkflowState.FAILED,
            EventOutcome.FAILED,
            code or "GT_OPERATION_FAILED",
            message,
        )


def validate_entity(entity: CanonicalLegalEntity) -> list[str]:
    """Enforce small source-neutral minimums before any GoldTier operation."""

    errors: list[str] = []
    if not UEN_PATTERN.fullmatch(entity.registration_number):
        errors.append("registration number is not in the Phase 01 synthetic UEN format")
    if entity.legal_name is None or not entity.legal_name.strip():
        errors.append("legal name is missing")
    if entity.country_of_incorporation != "SG":
        errors.append("country of incorporation must be SG for this phase")
    if entity.party_type is None or not entity.party_type.strip():
        errors.append("party type is missing")
    if entity.registered_address is None:
        errors.append("registered address is missing")
    else:
        address = entity.registered_address
        if not address.address_line_1.strip():
            errors.append("registered address line 1 is missing")
        if not address.postal_code.strip():
            errors.append("registered address postal code is missing")
        if not address.country_code.strip():
            errors.append("registered address country is missing")
    return errors
