"""Synchronous onboarding across configured ACRA and Mock GoldTier boundaries."""

from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from threading import Lock, RLock
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
from app.connectors.registry import (
    AcraRegistryProviderAdapter,
    RegistryProviderRouter,
)
from app.domain.access import CasePriority, TeamId
from app.domain.jurisdiction import (
    JurisdictionCode,
    JurisdictionObservation,
    JurisdictionObservationSource,
    JurisdictionResolutionStatus,
    JurisdictionResolver,
    is_eligible_singapore_uen,
)
from app.domain.models import (
    EventOutcome,
    GoldTierResult,
    OnboardingCase,
    RegistryAcquisitionStatus,
    RegistryOperationStatus,
    SafeError,
    WorkflowEvent,
    WorkflowState,
)
from app.domain.reconciliation import ReconciliationField
from app.domain.target_submission import (
    GoldTierExecutionClassification,
    GoldTierExecutionError,
    GoldTierExecutionLedgerEntry,
    GoldTierExecutionLedgerState,
    GoldTierExecutionReceipt,
    GoldTierExecutionResult,
    GoldTierIdempotencyBindings,
    GoldTierOperationMarker,
    GoldTierSubmissionInput,
    GoldTierTargetOutcome,
    SubmissionCanonicalEntity,
    SubmissionRegisteredAddress,
)
from app.mappers.goldtier import (
    build_amend_request,
    build_policy_request,
    build_search_request,
    build_shell_request,
)
from app.services.canonical_validation import validate_entity
from app.services.errors import OnboardingInfrastructureError
from app.services.repository import OnboardingCaseRepository
from app.services.target_execution_repository import (
    InMemoryTargetExecutionRepository,
    TargetExecutionRepository,
    TargetExecutionRepositoryConflictError,
)
from app.services.target_response_validation import (
    InvalidTargetResponseError,
    validate_amend_response,
    validate_policy_response,
    validate_search_response,
    validate_shell_response,
)

T = TypeVar("T")

MALFORMED_TARGET_RESPONSE_CODE = "GT_MALFORMED_TARGET_RESPONSE"
MALFORMED_TARGET_RESPONSE_MESSAGE = "Mock GoldTier returned an invalid response."
TARGET_OUTCOME_FALLBACK_CODE = "GT_TARGET_OUTCOME_RECORDING_FAILED"
TARGET_OUTCOME_FALLBACK_MESSAGE = "Mock GoldTier outcome recording failed safely."


class _TargetOutcomeFallbackRecorded(Exception):
    """Internal signal that a constant-only failure outcome replaced rich facts."""


def _submission_fingerprint(submission_input: GoldTierSubmissionInput) -> str:
    return sha256(submission_input.model_dump_json().encode("utf-8")).hexdigest()


def _idempotency_fingerprint(submission_input: GoldTierSubmissionInput) -> str:
    return sha256(submission_input.idempotency.model_dump_json().encode("utf-8")).hexdigest()


def _map_execution_result(
    outcome: GoldTierTargetOutcome,
) -> GoldTierExecutionResult | None:
    """Build the rich receipt result only after the safe outcome is retained."""

    if outcome.party_id is None or outcome.shell_status is None:
        return None
    return GoldTierExecutionResult(
        party_id=outcome.party_id,
        shell_status=outcome.shell_status,
        policy_id=outcome.policy_id,
        policy_status=outcome.policy_status,
        amend_status=outcome.amend_status,
    )


def _map_execution_error(
    outcome: GoldTierTargetOutcome,
) -> GoldTierExecutionError | None:
    """Build the rich receipt error from fixed safe outcome facts."""

    if outcome.error_code is None or outcome.error_message is None:
        return None
    return GoldTierExecutionError(
        code=outcome.error_code,
        message=outcome.error_message,
    )


def _controlled_target_failure_message(code: str) -> str:
    messages = {
        "GT_SHELL_FAILED": "GoldTier shell creation returned a controlled failure.",
        "GT_POLICY_VALIDATION_FAILED": (
            "GoldTier policy validation returned a controlled failure."
        ),
        "GT_AMEND_FAILED": "GoldTier amendment returned a controlled failure.",
    }
    return messages.get(code, "Mock GoldTier operation returned a controlled failure.")


def _project_target_error_code(code: str | None, *, allowed: frozenset[str], fallback: str) -> str:
    """Retain only locally recognized Mock business codes after shape validation."""

    return code if code in allowed else fallback


class OnboardingService:
    """Run the minimal complete flow while preserving terminal failure semantics."""

    def __init__(
        self,
        acra: AcraConnector | None,
        goldtier: GoldTierConnector,
        repository: OnboardingCaseRepository,
        registry_router: RegistryProviderRouter | None = None,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
        target_finalization_fault: Callable[[UUID], bool] | None = None,
        target_execution_repository: TargetExecutionRepository | None = None,
    ) -> None:
        if registry_router is None:
            if acra is None:
                raise ValueError("Onboarding service requires a registry provider router")
            registry_router = RegistryProviderRouter(AcraRegistryProviderAdapter(acra))
        self._registry_router = registry_router
        self._jurisdiction_resolver = JurisdictionResolver()
        self._goldtier = goldtier
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4
        self._target_finalization_fault = target_finalization_fault
        self._case_locks: dict[UUID, RLock] = {}
        self._case_locks_guard = Lock()
        self._execution_ledger_guard = RLock()
        self._target_executions = target_execution_repository or InMemoryTargetExecutionRepository()

    def case_lock(self, case_id: UUID) -> RLock:
        """Share one in-process evidence/submission boundary per case."""

        with self._case_locks_guard:
            return self._case_locks.setdefault(case_id, RLock())

    @property
    def case_repository(self) -> OnboardingCaseRepository:
        return self._repository

    def create_case(
        self,
        uen: str,
        country_of_incorporation: JurisdictionCode | str | None = None,
        *,
        team_id: TeamId | None = None,
        priority: CasePriority | None = None,
    ) -> OnboardingCase:
        """Preserve the Phase 01 API as staged intake plus Mock GoldTier submission."""

        case = self.create_staged_case(
            uen, country_of_incorporation, team_id=team_id, priority=priority
        )
        if case.state != WorkflowState.VALIDATED:
            return case
        return self.submit_staged_case(case.case_id, complete_legacy_flow=True)

    def create_staged_case(
        self,
        uen: str,
        country_of_incorporation: JurisdictionCode | str | None = None,
        *,
        team_id: TeamId | None = None,
        priority: CasePriority | None = None,
    ) -> OnboardingCase:
        """Resolve jurisdiction, route, and validate registry data without GoldTier."""

        now = self._clock()
        case_id = self._uuid_factory()
        correlation_id = self._uuid_factory()
        normalised_uen = uen.strip().upper()
        if not normalised_uen:
            raise ValueError("Onboarding service requires a normalized non-empty UEN")

        explicit_jurisdiction = (
            JurisdictionCode(country_of_incorporation)
            if country_of_incorporation is not None
            else None
        )
        observations: list[JurisdictionObservation] = []
        if explicit_jurisdiction is not None:
            observations.append(
                JurisdictionObservation(
                    jurisdiction=explicit_jurisdiction,
                    source=JurisdictionObservationSource.USER_INPUT,
                    observed_at=now,
                    source_reference="request.country_of_incorporation",
                )
            )
        if is_eligible_singapore_uen(normalised_uen):
            observations.append(
                JurisdictionObservation(
                    jurisdiction=JurisdictionCode.SINGAPORE,
                    source=JurisdictionObservationSource.IDENTIFIER_FORMAT,
                    observed_at=now,
                    source_reference="request.uen:accepted_sg_format",
                )
            )
        resolution = self._jurisdiction_resolver.resolve(observations, resolved_at=now)

        source_case_id = f"CASE-{normalised_uen}-{str(case_id)[:8]}"
        case = OnboardingCase(
            case_id=case_id,
            source_case_id=source_case_id,
            correlation_id=correlation_id,
            requested_uen=normalised_uen,
            team_id=team_id,
            priority=priority,
            jurisdiction_resolution=resolution,
            state=WorkflowState.REQUESTED,
            created_at=now,
            updated_at=now,
        )
        self._record(case, WorkflowState.REQUESTED, EventOutcome.SUCCEEDED, "Case requested.")

        if resolution.status == JurisdictionResolutionStatus.UNRESOLVED:
            return self._terminate(
                case,
                WorkflowState.REVIEW_REQUIRED,
                EventOutcome.REVIEW_REQUIRED,
                "JURISDICTION_UNRESOLVED",
                "Jurisdiction could not be resolved from the supplied onboarding evidence.",
            )
        if resolution.status == JurisdictionResolutionStatus.CONFLICT:
            return self._terminate(
                case,
                WorkflowState.REVIEW_REQUIRED,
                EventOutcome.REVIEW_REQUIRED,
                "JURISDICTION_CONFLICT",
                "Conflicting jurisdiction evidence requires review before registry retrieval.",
            )

        resolved_jurisdiction = resolution.resolved_jurisdiction
        if resolved_jurisdiction is None:
            raise RuntimeError("resolved jurisdiction invariant was not satisfied")
        route, registry_provider = self._registry_router.route(
            resolved_jurisdiction,
            decided_at=self._clock(),
        )
        case.registry_route = route
        if registry_provider is None:
            return self._terminate(
                case,
                WorkflowState.REVIEW_REQUIRED,
                EventOutcome.REVIEW_REQUIRED,
                "REGISTRY_PROVIDER_NOT_IMPLEMENTED",
                "The registry provider for the resolved jurisdiction is not implemented.",
            )
        if resolved_jurisdiction == JurisdictionCode.SINGAPORE and not is_eligible_singapore_uen(
            normalised_uen
        ):
            return self._terminate(
                case,
                WorkflowState.REVIEW_REQUIRED,
                EventOutcome.REVIEW_REQUIRED,
                "REGISTRY_IDENTIFIER_NOT_ELIGIBLE",
                "The identifier is not eligible for Singapore ACRA retrieval.",
            )

        acquisition = self._run_required_stage(
            case,
            code="ACRA_RETRIEVAL_UNEXPECTED_FAILURE",
            message="Corporate registry retrieval could not be completed.",
            operation=lambda: registry_provider.retrieve_acquisition(normalised_uen),
        )
        if acquisition is None:
            return self._terminate(
                case,
                WorkflowState.FAILED,
                EventOutcome.FAILED,
                "ACRA_ENTITY_NOT_FOUND",
                "No ACRA entity was found for this UEN.",
            )

        case.registry_acquisition = acquisition
        entity = acquisition.entity_profile
        case.entity = entity
        self._record(
            case,
            WorkflowState.REGISTRY_FETCHED,
            (
                EventOutcome.SUCCEEDED
                if acquisition.status == RegistryAcquisitionStatus.COMPLETE
                else EventOutcome.PARTIAL
            ),
            (
                "Project-owned ACRA registry acquisition completed."
                if acquisition.status == RegistryAcquisitionStatus.COMPLETE
                else "Project-owned ACRA registry acquisition returned partial results."
            ),
        )
        if acquisition.status == RegistryAcquisitionStatus.FAILED:
            failed_operation = next(
                result
                for result in acquisition.operation_results
                if result.status == RegistryOperationStatus.FAILED
            )
            failure = failed_operation.error
            return self._terminate(
                case,
                WorkflowState.FAILED,
                EventOutcome.FAILED,
                (failure.code if failure is not None else "REGISTRY_OPERATION_UNAVAILABLE"),
                (
                    failure.message
                    if failure is not None
                    else "Registry acquisition could not be completed."
                ),
            )
        if acquisition.status == RegistryAcquisitionStatus.PARTIAL:
            issue = acquisition.issues[0]
            return self._terminate(
                case,
                WorkflowState.REVIEW_REQUIRED,
                EventOutcome.REVIEW_REQUIRED,
                issue.code,
                issue.message,
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

        return case.model_copy(deep=True)

    def submit_staged_case(
        self, case_id: UUID, *, complete_legacy_flow: bool = False
    ) -> OnboardingCase:
        """Execute the accepted Mock GoldTier base sequence for a validated case."""

        with self.case_lock(case_id):
            case = self._repository.get(case_id)
            if case is None:
                raise ValueError("Onboarding case was not found")
            if case.state != WorkflowState.VALIDATED or case.entity is None:
                raise ValueError("Onboarding case is not eligible for Mock GoldTier submission")
            submission_input = self.build_submission_input(
                case,
                correlation_id=case.correlation_id,
            )
            receipt = self.execute_submission_input(
                submission_input,
                complete_legacy_flow=complete_legacy_flow,
            )
            if receipt.infrastructure_failure:
                error = receipt.error or GoldTierExecutionError(
                    code="GT_OPERATION_FAILED",
                    message="Mock GoldTier submission could not be completed.",
                )
                raise OnboardingInfrastructureError(
                    case_id=case_id,
                    correlation_id=case.correlation_id,
                    code=error.code,
                    public_message=error.message,
                ) from None
            current = self._repository.get(case_id)
            if current is None:
                raise ValueError("Onboarding case was not found after submission")
            return current

    def build_submission_input(
        self,
        case: OnboardingCase,
        *,
        submission_id: UUID | None = None,
        correlation_id: UUID | None = None,
        accepted_at: datetime | None = None,
    ) -> GoldTierSubmissionInput:
        """Freeze validated canonical business data and stable target identifiers."""

        entity = case.entity
        if entity is None or validate_entity(entity):
            raise ValueError("Canonical entity is not eligible for target submission")
        address = entity.registered_address
        if (
            entity.legal_name is None
            or entity.country_of_incorporation is None
            or entity.party_type is None
            or address is None
        ):
            raise ValueError("Canonical entity is not eligible for target submission")
        return GoldTierSubmissionInput(
            submission_id=submission_id or self._uuid_factory(),
            case_id=case.case_id,
            source_case_id=case.source_case_id,
            correlation_id=correlation_id or self._uuid_factory(),
            accepted_at=accepted_at or self._clock(),
            canonical_entity=SubmissionCanonicalEntity(
                registration_number=entity.registration_number,
                legal_name=entity.legal_name,
                country_of_incorporation=entity.country_of_incorporation,
                party_type=entity.party_type,
                registration_date=entity.registration_date,
                entity_status=entity.entity_status,
                registered_address=SubmissionRegisteredAddress.model_validate(address.model_dump()),
            ),
            idempotency=GoldTierIdempotencyBindings(
                search=self._uuid_factory(),
                shell=self._uuid_factory(),
                policy=self._uuid_factory(),
                amend=self._uuid_factory(),
            ),
        )

    def execute_submission_input(
        self,
        submission_input: GoldTierSubmissionInput,
        *,
        complete_legacy_flow: bool = False,
    ) -> GoldTierExecutionReceipt:
        """Execute once and retain the target outcome before rich receipt mapping."""

        with self.case_lock(submission_input.case_id):
            entry = self._stored_execution_entry(submission_input)
            if entry is not None:
                if entry.receipt is not None:
                    return entry.receipt.model_copy(deep=True)
                if entry.target_outcome is not None:
                    return self._finalize_execution_receipt(
                        submission_input,
                        entry.target_outcome,
                    )
                raise RuntimeError("Mock GoldTier submission is already in progress")

            case = self._repository.get(submission_input.case_id)
            if case is None:
                raise ValueError("Onboarding case was not found")
            if (
                case.source_case_id != submission_input.source_case_id
                or case.state != WorkflowState.VALIDATED
                or validate_entity(submission_input.canonical_entity)
            ):
                raise ValueError("Submission input is not eligible for Mock GoldTier")

            self._start_execution(submission_input)
            try:
                self._submit_to_goldtier(
                    case,
                    submission_input,
                    complete_legacy_flow=complete_legacy_flow,
                )
            except OnboardingInfrastructureError:
                pass
            finally:
                self._ensure_execution_owner_exit(submission_input)

            recorded = self.get_target_outcome(submission_input.submission_id)
            if recorded is None:
                raise RuntimeError("Mock GoldTier execution outcome was not retained")
            return self._finalize_execution_receipt(submission_input, recorded)

    def get_execution_receipt(self, submission_id: UUID) -> GoldTierExecutionReceipt | None:
        with self._execution_ledger_guard:
            stored = self._target_executions.get(submission_id)
            if stored is None or stored.receipt is None:
                return None
            return stored.receipt.model_copy(deep=True)

    def get_target_outcome(self, submission_id: UUID) -> GoldTierTargetOutcome | None:
        with self._execution_ledger_guard:
            stored = self._target_executions.get(submission_id)
            if stored is None or stored.target_outcome is None:
                return None
            return stored.target_outcome.model_copy(deep=True)

    def get_execution_state(self, submission_id: UUID) -> GoldTierExecutionLedgerState:
        with self._execution_ledger_guard:
            stored = self._target_executions.get(submission_id)
            return stored.state if stored is not None else GoldTierExecutionLedgerState.NOT_STARTED

    def is_execution_outcome_uncertain(self, submission_id: UUID) -> bool:
        """Consult one authoritative ledger snapshot without invoking the target."""

        with self._execution_ledger_guard:
            stored = self._target_executions.get(submission_id)
            return bool(
                stored is not None
                and stored.state == GoldTierExecutionLedgerState.IN_PROGRESS
                and stored.attempted_operations
                and stored.target_outcome is None
                and stored.receipt is None
            )

    def _stored_execution_entry(
        self, submission_input: GoldTierSubmissionInput
    ) -> GoldTierExecutionLedgerEntry | None:
        with self._execution_ledger_guard:
            stored = self._target_executions.get(submission_input.submission_id)
            if stored is None:
                return None
            if stored.submission_input != submission_input:
                raise ValueError("Submission identity was reused with different input")
            return stored.model_copy(deep=True)

    def _start_execution(self, submission_input: GoldTierSubmissionInput) -> None:
        entry = GoldTierExecutionLedgerEntry(
            submission_input=submission_input.model_copy(deep=True),
            state=GoldTierExecutionLedgerState.IN_PROGRESS,
        )
        with self._execution_ledger_guard:
            try:
                self._target_executions.create(entry)
            except TargetExecutionRepositoryConflictError:
                raise RuntimeError("Mock GoldTier submission identity already exists") from None

    def _mark_operation_attempted(
        self,
        submission_input: GoldTierSubmissionInput,
        operation: GoldTierOperationMarker,
    ) -> None:
        with self._execution_ledger_guard:
            entry = self._target_executions.get(submission_input.submission_id)
            if (
                entry is None
                or entry.submission_input != submission_input
                or entry.state != GoldTierExecutionLedgerState.IN_PROGRESS
            ):
                raise ValueError("Target operation does not match an active submission")
            if operation in entry.attempted_operations:
                raise ValueError("Target operation was attempted more than once")
            attempted = (*entry.attempted_operations, operation)
            candidate = GoldTierExecutionLedgerEntry(
                submission_input=entry.submission_input,
                state=GoldTierExecutionLedgerState.IN_PROGRESS,
                attempted_operations=attempted,
            )
            self._target_executions.replace(
                candidate, expected_state=GoldTierExecutionLedgerState.IN_PROGRESS.value
            )

    def _ensure_execution_owner_exit(self, submission_input: GoldTierSubmissionInput) -> None:
        with self._execution_ledger_guard:
            entry = self._target_executions.get(submission_input.submission_id)
            if entry is None or entry.state != GoldTierExecutionLedgerState.IN_PROGRESS:
                return
            attempted = entry.attempted_operations
            if not attempted:
                self._target_executions.delete_if_unattempted(submission_input.submission_id)
                return
        self._record_fixed_failure_outcome(
            submission_input,
            completed_operations=attempted,
            code=TARGET_OUTCOME_FALLBACK_CODE,
            message=TARGET_OUTCOME_FALLBACK_MESSAGE,
        )

    def _record_target_outcome(
        self,
        submission_input: GoldTierSubmissionInput,
        *,
        classification: GoldTierExecutionClassification,
        onboarding_state: WorkflowState,
        completed_operations: tuple[GoldTierOperationMarker, ...],
        party_id: str | None = None,
        shell_status: str | None = None,
        policy_id: str | None = None,
        policy_status: str | None = None,
        amend_status: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        infrastructure_failure: bool = False,
    ) -> GoldTierTargetOutcome:
        try:
            outcome = self._build_target_outcome(
                submission_input,
                classification=classification,
                onboarding_state=onboarding_state,
                completed_operations=completed_operations,
                party_id=party_id,
                shell_status=shell_status,
                policy_id=policy_id,
                policy_status=policy_status,
                amend_status=amend_status,
                error_code=error_code,
                error_message=error_message,
                infrastructure_failure=infrastructure_failure,
            )
        except Exception:
            self._record_fixed_failure_outcome(
                submission_input,
                completed_operations=completed_operations,
                code=TARGET_OUTCOME_FALLBACK_CODE,
                message=TARGET_OUTCOME_FALLBACK_MESSAGE,
            )
            raise _TargetOutcomeFallbackRecorded from None
        return self._store_target_outcome(submission_input, outcome)

    def _build_target_outcome(
        self,
        submission_input: GoldTierSubmissionInput,
        *,
        classification: GoldTierExecutionClassification,
        onboarding_state: WorkflowState,
        completed_operations: tuple[GoldTierOperationMarker, ...],
        party_id: str | None = None,
        shell_status: str | None = None,
        policy_id: str | None = None,
        policy_status: str | None = None,
        amend_status: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        infrastructure_failure: bool = False,
    ) -> GoldTierTargetOutcome:
        return GoldTierTargetOutcome(
            submission_id=submission_input.submission_id,
            case_id=submission_input.case_id,
            correlation_id=submission_input.correlation_id,
            input_fingerprint=_submission_fingerprint(submission_input),
            idempotency_fingerprint=_idempotency_fingerprint(submission_input),
            classification=classification,
            onboarding_state=onboarding_state,
            completed_operations=completed_operations,
            party_id=party_id,
            shell_status=shell_status,
            policy_id=policy_id,
            policy_status=policy_status,
            amend_status=amend_status,
            error_code=error_code,
            error_message=error_message,
            infrastructure_failure=infrastructure_failure,
        )

    def _record_fixed_failure_outcome(
        self,
        submission_input: GoldTierSubmissionInput,
        *,
        completed_operations: tuple[GoldTierOperationMarker, ...],
        code: str,
        message: str,
    ) -> GoldTierTargetOutcome:
        outcome = GoldTierTargetOutcome(
            submission_id=submission_input.submission_id,
            case_id=submission_input.case_id,
            correlation_id=submission_input.correlation_id,
            input_fingerprint=_submission_fingerprint(submission_input),
            idempotency_fingerprint=_idempotency_fingerprint(submission_input),
            classification=GoldTierExecutionClassification.FAILED,
            onboarding_state=WorkflowState.FAILED,
            completed_operations=completed_operations,
            error_code=code,
            error_message=message,
            infrastructure_failure=True,
        )
        return self._store_target_outcome(submission_input, outcome)

    def _store_target_outcome(
        self,
        submission_input: GoldTierSubmissionInput,
        outcome: GoldTierTargetOutcome,
    ) -> GoldTierTargetOutcome:
        with self._execution_ledger_guard:
            entry = self._target_executions.get(submission_input.submission_id)
            if entry is None or entry.submission_input != submission_input:
                raise ValueError("Target outcome does not match an active submission")
            if entry.target_outcome is not None:
                if entry.target_outcome != outcome:
                    raise ValueError("Target execution produced conflicting outcomes")
                return entry.target_outcome.model_copy(deep=True)
            candidate = GoldTierExecutionLedgerEntry(
                submission_input=entry.submission_input,
                state=GoldTierExecutionLedgerState.TARGET_OUTCOME_RECORDED,
                attempted_operations=outcome.completed_operations,
                target_outcome=outcome,
            )
            self._target_executions.replace(
                candidate, expected_state=GoldTierExecutionLedgerState.IN_PROGRESS.value
            )
        return outcome.model_copy(deep=True)

    def _finalize_execution_receipt(
        self,
        submission_input: GoldTierSubmissionInput,
        outcome: GoldTierTargetOutcome,
    ) -> GoldTierExecutionReceipt:
        receipt = self._build_execution_receipt(submission_input, outcome)
        with self._execution_ledger_guard:
            entry = self._target_executions.get(submission_input.submission_id)
            if (
                entry is None
                or entry.submission_input != submission_input
                or entry.target_outcome != outcome
            ):
                raise ValueError("Receipt does not match the retained target outcome")
            candidate = GoldTierExecutionLedgerEntry(
                submission_input=entry.submission_input,
                state=GoldTierExecutionLedgerState.FINALIZED,
                attempted_operations=outcome.completed_operations,
                target_outcome=outcome,
                receipt=receipt,
            )
            self._target_executions.replace(
                candidate,
                expected_state=GoldTierExecutionLedgerState.TARGET_OUTCOME_RECORDED.value,
            )
        return receipt.model_copy(deep=True)

    def _submit_to_goldtier(
        self,
        case: OnboardingCase,
        submission_input: GoldTierSubmissionInput,
        *,
        complete_legacy_flow: bool,
    ) -> OnboardingCase:
        entity = submission_input.canonical_entity

        self._mark_operation_attempted(submission_input, GoldTierOperationMarker.SEARCH)
        untrusted_search = self._run_required_stage(
            case,
            code="GT_SEARCH_UNEXPECTED_FAILURE",
            message="GoldTier party search could not be completed.",
            on_failure=lambda code, message: self._record_target_outcome(
                submission_input,
                classification=GoldTierExecutionClassification.FAILED,
                onboarding_state=WorkflowState.FAILED,
                completed_operations=(GoldTierOperationMarker.SEARCH,),
                error_code=code,
                error_message=message,
                infrastructure_failure=True,
            ),
            operation=lambda: self._goldtier.search_party(
                build_search_request(entity),
                self._metadata(
                    submission_input,
                    submission_input.idempotency.search,
                ),
            ),
        )
        try:
            search = validate_search_response(untrusted_search)
        except InvalidTargetResponseError:
            return self._malformed_target_response(
                case,
                submission_input,
                completed_operations=(GoldTierOperationMarker.SEARCH,),
            )
        if search.outcome == GoldTierSearchOutcome.MATCH_FOUND:
            self._record_target_outcome(
                submission_input,
                classification=GoldTierExecutionClassification.REVIEW_REQUIRED,
                onboarding_state=WorkflowState.REVIEW_REQUIRED,
                completed_operations=(GoldTierOperationMarker.SEARCH,),
                error_code="GT_EXISTING_PARTY_REVIEW_REQUIRED",
                error_message=("An existing GoldTier party candidate requires human review."),
            )
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
            self._record_target_outcome(
                submission_input,
                classification=GoldTierExecutionClassification.FAILED,
                onboarding_state=WorkflowState.FAILED,
                completed_operations=(GoldTierOperationMarker.SEARCH,),
                error_code="GT_SEARCH_FAILED",
                error_message="GoldTier party search returned a controlled failure.",
            )
            return self._terminate(
                case,
                WorkflowState.FAILED,
                EventOutcome.FAILED,
                "GT_SEARCH_FAILED",
                "GoldTier party search returned a controlled failure.",
            )
        if search.outcome != GoldTierSearchOutcome.NO_MATCH:
            self._record_target_outcome(
                submission_input,
                classification=GoldTierExecutionClassification.FAILED,
                onboarding_state=WorkflowState.FAILED,
                completed_operations=(GoldTierOperationMarker.SEARCH,),
                error_code="GT_SEARCH_RESULT_UNSUPPORTED",
                error_message="GoldTier party search returned an unsupported result.",
            )
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

        self._mark_operation_attempted(submission_input, GoldTierOperationMarker.SHELL)
        untrusted_shell = self._run_required_stage(
            case,
            code="GT_SHELL_UNEXPECTED_FAILURE",
            message="GoldTier shell customer creation could not be completed.",
            on_failure=lambda code, message: self._record_target_outcome(
                submission_input,
                classification=GoldTierExecutionClassification.FAILED,
                onboarding_state=WorkflowState.FAILED,
                completed_operations=(
                    GoldTierOperationMarker.SEARCH,
                    GoldTierOperationMarker.SHELL,
                ),
                error_code=code,
                error_message=message,
                infrastructure_failure=True,
            ),
            operation=lambda: self._goldtier.create_shell_customer(
                build_shell_request(
                    entity,
                    submission_input.source_case_id,
                    submission_input.accepted_at,
                ),
                self._metadata(
                    submission_input,
                    submission_input.idempotency.shell,
                ),
            ),
        )
        try:
            shell = validate_shell_response(untrusted_shell)
        except InvalidTargetResponseError:
            return self._malformed_target_response(
                case,
                submission_input,
                completed_operations=(
                    GoldTierOperationMarker.SEARCH,
                    GoldTierOperationMarker.SHELL,
                ),
            )
        if shell.outcome != GoldTierOutcome.SUCCESS or shell.party_id is None:
            code = _project_target_error_code(
                shell.error_code,
                allowed=frozenset({"GT_SHELL_FAILED"}),
                fallback="GT_OPERATION_FAILED",
            )
            message = _controlled_target_failure_message(code)
            self._record_target_outcome(
                submission_input,
                classification=GoldTierExecutionClassification.FAILED,
                onboarding_state=WorkflowState.FAILED,
                completed_operations=(
                    GoldTierOperationMarker.SEARCH,
                    GoldTierOperationMarker.SHELL,
                ),
                error_code=code,
                error_message=message,
            )
            return self._goldtier_failure(case, code, message)
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

        self._mark_operation_attempted(submission_input, GoldTierOperationMarker.POLICY)
        untrusted_policy = self._run_required_stage(
            case,
            code="GT_POLICY_UNEXPECTED_FAILURE",
            message="GoldTier policy creation could not be completed.",
            on_failure=lambda code, message: self._record_target_outcome(
                submission_input,
                classification=GoldTierExecutionClassification.FAILED,
                onboarding_state=WorkflowState.FAILED,
                completed_operations=(
                    GoldTierOperationMarker.SEARCH,
                    GoldTierOperationMarker.SHELL,
                    GoldTierOperationMarker.POLICY,
                ),
                party_id=party_id,
                shell_status=shell.status,
                error_code=code,
                error_message=message,
                infrastructure_failure=True,
            ),
            operation=lambda: self._goldtier.create_policy(
                build_policy_request(
                    entity,
                    party_id,
                    submission_input.source_case_id,
                    submission_input.accepted_at,
                ),
                self._metadata(
                    submission_input,
                    submission_input.idempotency.policy,
                ),
            ),
        )
        try:
            policy = validate_policy_response(untrusted_policy, expected_party_id=party_id)
        except InvalidTargetResponseError:
            return self._malformed_target_response(
                case,
                submission_input,
                completed_operations=(
                    GoldTierOperationMarker.SEARCH,
                    GoldTierOperationMarker.SHELL,
                    GoldTierOperationMarker.POLICY,
                ),
            )
        if policy.outcome != GoldTierOutcome.SUCCESS or policy.policy_id is None:
            code = _project_target_error_code(
                policy.error_code,
                allowed=frozenset(
                    {
                        "GT_POLICY_EXTERNAL_REFERENCE_REQUIRED",
                        "GT_POLICY_VALIDATION_FAILED",
                    }
                ),
                fallback="GT_OPERATION_FAILED",
            )
            message = _controlled_target_failure_message(code)
            self._record_target_outcome(
                submission_input,
                classification=GoldTierExecutionClassification.FAILED,
                onboarding_state=WorkflowState.FAILED,
                completed_operations=(
                    GoldTierOperationMarker.SEARCH,
                    GoldTierOperationMarker.SHELL,
                    GoldTierOperationMarker.POLICY,
                ),
                party_id=party_id,
                shell_status=shell.status,
                policy_status=policy.status,
                error_code=code,
                error_message=message,
            )
            case.goldtier_result.policy_status = policy.status
            return self._goldtier_failure(case, code, message)
        case.goldtier_result.policy_id = policy.policy_id
        case.goldtier_result.policy_status = policy.status
        self._record(
            case,
            WorkflowState.GT_POLICY_CREATED,
            EventOutcome.SUCCEEDED,
            "Mock Singapore policy created.",
        )

        self._mark_operation_attempted(submission_input, GoldTierOperationMarker.AMEND)
        untrusted_amend = self._run_required_stage(
            case,
            code="GT_AMEND_UNEXPECTED_FAILURE",
            message="GoldTier party enrichment could not be completed.",
            on_failure=lambda code, message: self._record_target_outcome(
                submission_input,
                classification=GoldTierExecutionClassification.FAILED,
                onboarding_state=WorkflowState.FAILED,
                completed_operations=(
                    GoldTierOperationMarker.SEARCH,
                    GoldTierOperationMarker.SHELL,
                    GoldTierOperationMarker.POLICY,
                    GoldTierOperationMarker.AMEND,
                ),
                party_id=party_id,
                shell_status=shell.status,
                policy_id=policy.policy_id,
                policy_status=policy.status,
                error_code=code,
                error_message=message,
                infrastructure_failure=True,
            ),
            operation=lambda: self._goldtier.amend_party(
                party_id,
                build_amend_request(
                    entity,
                    submission_input.source_case_id,
                    submission_input.accepted_at,
                ),
                self._metadata(
                    submission_input,
                    submission_input.idempotency.amend,
                ),
            ),
        )
        try:
            amend = validate_amend_response(untrusted_amend, expected_party_id=party_id)
        except InvalidTargetResponseError:
            return self._malformed_target_response(
                case,
                submission_input,
                completed_operations=(
                    GoldTierOperationMarker.SEARCH,
                    GoldTierOperationMarker.SHELL,
                    GoldTierOperationMarker.POLICY,
                    GoldTierOperationMarker.AMEND,
                ),
            )
        if amend.outcome == GoldTierOutcome.PARTIAL_SUCCESS:
            code = _project_target_error_code(
                amend.error_code,
                allowed=frozenset({"GT_OPTIONAL_SECTION_REVIEW"}),
                fallback="GT_PARTIAL_SUCCESS",
            )
            message = "Human review required for the partial mock GoldTier amendment."
            self._record_target_outcome(
                submission_input,
                classification=GoldTierExecutionClassification.REVIEW_REQUIRED,
                onboarding_state=WorkflowState.REVIEW_REQUIRED,
                completed_operations=(
                    GoldTierOperationMarker.SEARCH,
                    GoldTierOperationMarker.SHELL,
                    GoldTierOperationMarker.POLICY,
                    GoldTierOperationMarker.AMEND,
                ),
                party_id=party_id,
                shell_status=shell.status,
                policy_id=policy.policy_id,
                policy_status=policy.status,
                amend_status=amend.status,
                error_code=code,
                error_message=message,
            )
            case.goldtier_result.amend_status = amend.status
            self._record(
                case,
                WorkflowState.GT_ENRICHED,
                EventOutcome.PARTIAL,
                "Mock GoldTier amendment completed partially.",
                code,
            )
            return self._terminate(
                case,
                WorkflowState.REVIEW_REQUIRED,
                EventOutcome.REVIEW_REQUIRED,
                code,
                message,
            )
        if amend.outcome != GoldTierOutcome.SUCCESS:
            code = _project_target_error_code(
                amend.error_code,
                allowed=frozenset({"GT_AMEND_FAILED"}),
                fallback="GT_OPERATION_FAILED",
            )
            message = _controlled_target_failure_message(code)
            self._record_target_outcome(
                submission_input,
                classification=GoldTierExecutionClassification.FAILED,
                onboarding_state=WorkflowState.FAILED,
                completed_operations=(
                    GoldTierOperationMarker.SEARCH,
                    GoldTierOperationMarker.SHELL,
                    GoldTierOperationMarker.POLICY,
                    GoldTierOperationMarker.AMEND,
                ),
                party_id=party_id,
                shell_status=shell.status,
                policy_id=policy.policy_id,
                policy_status=policy.status,
                amend_status=amend.status,
                error_code=code,
                error_message=message,
            )
            case.goldtier_result.amend_status = amend.status
            return self._goldtier_failure(case, code, message)
        self._record_target_outcome(
            submission_input,
            classification=GoldTierExecutionClassification.SUCCESS,
            onboarding_state=(
                WorkflowState.COMPLETED if complete_legacy_flow else WorkflowState.GT_ENRICHED
            ),
            completed_operations=(
                GoldTierOperationMarker.SEARCH,
                GoldTierOperationMarker.SHELL,
                GoldTierOperationMarker.POLICY,
                GoldTierOperationMarker.AMEND,
            ),
            party_id=party_id,
            shell_status=shell.status,
            policy_id=policy.policy_id,
            policy_status=policy.status,
            amend_status=amend.status,
        )
        case.goldtier_result.amend_status = amend.status
        self._record(
            case,
            WorkflowState.GT_ENRICHED,
            EventOutcome.SUCCEEDED,
            "Mock GoldTier party enriched.",
        )
        if complete_legacy_flow:
            self._record(
                case,
                WorkflowState.COMPLETED,
                EventOutcome.SUCCEEDED,
                "Required onboarding stages completed with Mock GoldTier.",
            )
        return case.model_copy(deep=True)

    def _malformed_target_response(
        self,
        case: OnboardingCase,
        submission_input: GoldTierSubmissionInput,
        *,
        completed_operations: tuple[GoldTierOperationMarker, ...],
    ) -> OnboardingCase:
        self._record_fixed_failure_outcome(
            submission_input,
            completed_operations=completed_operations,
            code=MALFORMED_TARGET_RESPONSE_CODE,
            message=MALFORMED_TARGET_RESPONSE_MESSAGE,
        )
        return self._terminate(
            case,
            WorkflowState.FAILED,
            EventOutcome.FAILED,
            MALFORMED_TARGET_RESPONSE_CODE,
            MALFORMED_TARGET_RESPONSE_MESSAGE,
        )

    def get_case(self, case_id: UUID) -> OnboardingCase | None:
        return self._repository.get(case_id)

    @property
    def repository(self) -> OnboardingCaseRepository:
        """Expose the configured store only to the reconciliation unit of work."""

        return self._repository

    @property
    def process_local_repository(self) -> OnboardingCaseRepository:
        """Backward-compatible alias retained for focused Phase 11 tests."""

        return self._repository

    def canonical_entity_fingerprint(self, case_id: UUID) -> str:
        """Bind reconciliation decisions to the current canonical case value."""

        case = self._repository.get(case_id)
        if case is None or case.entity is None:
            raise ValueError("canonical entity is unavailable")
        return sha256(case.entity.model_dump_json().encode("utf-8")).hexdigest()

    def prepare_reconciled_value(
        self,
        *,
        case_id: UUID,
        field_name: ReconciliationField,
        selected_value: str,
        expected_entity_fingerprint: str,
    ) -> OnboardingCase:
        """Prepare one backend-authorized value without persisting either aggregate.

        Phase 11 permits document selection only for legal name. Registration identity,
        country/routing, and structured address updates cannot be applied safely from the
        current flat document field without inventing extra mapping or routing policy.
        """

        with self.case_lock(case_id):
            case = self._repository.get(case_id)
            if case is None or case.entity is None:
                raise ValueError("canonical entity is unavailable")
            current_fingerprint = sha256(case.entity.model_dump_json().encode("utf-8")).hexdigest()
            if current_fingerprint != expected_entity_fingerprint:
                raise ValueError("canonical entity changed before reconciliation")
            if field_name != ReconciliationField.LEGAL_NAME:
                raise ValueError("selected document value is not safely applicable")
            normalized = selected_value.strip()
            if (
                not normalized
                or len(normalized) > 512
                or any(ord(character) < 32 for character in normalized)
            ):
                raise ValueError("selected document value is invalid")
            candidate = case.model_copy(deep=True)
            candidate_entity = case.entity.model_copy(deep=True)
            candidate_entity.legal_name = normalized
            if validate_entity(candidate_entity):
                raise ValueError("selected document value violates canonical validation")
            candidate.entity = candidate_entity
            timestamp = self._clock()
            candidate.state = WorkflowState.VALIDATED
            candidate.updated_at = timestamp
            candidate.events.append(
                WorkflowEvent(
                    sequence=len(candidate.events) + 1,
                    stage=WorkflowState.VALIDATED,
                    outcome=EventOutcome.SUCCEEDED,
                    timestamp=timestamp,
                    case_id=candidate.case_id,
                    correlation_id=candidate.correlation_id,
                    code="RECONCILIATION_CANONICAL_UPDATED",
                    message=(
                        "Canonical legal name updated by an explicit reconciliation decision."
                    ),
                )
            )
            return OnboardingCase.model_validate(candidate)

    def get_attempted_target_operations(
        self, submission_id: UUID
    ) -> tuple[GoldTierOperationMarker, ...]:
        """Return only the safe ordered operation markers for local UAT evidence."""

        with self._execution_ledger_guard:
            entry = self._target_executions.get(submission_id)
            return tuple(entry.attempted_operations) if entry is not None else ()

    def _metadata(
        self, submission_input: GoldTierSubmissionInput, idempotency_key: UUID
    ) -> GoldTierRequestMetadata:
        return GoldTierRequestMetadata(
            correlation_id=submission_input.correlation_id,
            source_case_id=submission_input.source_case_id,
            idempotency_key=idempotency_key,
        )

    def _build_execution_receipt(
        self,
        submission_input: GoldTierSubmissionInput,
        outcome: GoldTierTargetOutcome,
    ) -> GoldTierExecutionReceipt:
        if self._target_finalization_fault is not None and self._target_finalization_fault(
            submission_input.case_id
        ):
            raise RuntimeError("Synthetic demo finalization fault")
        if (
            outcome.submission_id != submission_input.submission_id
            or outcome.case_id != submission_input.case_id
            or outcome.correlation_id != submission_input.correlation_id
            or outcome.input_fingerprint != _submission_fingerprint(submission_input)
            or outcome.idempotency_fingerprint != _idempotency_fingerprint(submission_input)
        ):
            raise ValueError("Target outcome does not match the immutable submission")

        result = _map_execution_result(outcome)
        error = _map_execution_error(outcome)
        return GoldTierExecutionReceipt(
            submission_id=submission_input.submission_id,
            case_id=submission_input.case_id,
            correlation_id=submission_input.correlation_id,
            input_fingerprint=outcome.input_fingerprint,
            classification=outcome.classification,
            onboarding_state=outcome.onboarding_state,
            result=result,
            error=error,
            infrastructure_failure=outcome.infrastructure_failure,
        )

    def _run_required_stage(
        self,
        case: OnboardingCase,
        *,
        code: str,
        message: str,
        operation: Callable[[], T],
        on_failure: Callable[[str, str], object] | None = None,
    ) -> T:
        try:
            return operation()
        except ConnectorError as exc:
            public_error = public_connector_error(exc)
            if on_failure is not None:
                on_failure(public_error.code, public_error.message)
            self._raise_terminal_infrastructure(
                case,
                code=public_error.code,
                message=public_error.message,
            )
        except Exception:
            if on_failure is not None:
                on_failure(code, message)
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
