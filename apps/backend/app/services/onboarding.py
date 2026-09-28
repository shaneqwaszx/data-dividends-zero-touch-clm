"""Synchronous onboarding across configured ACRA and Mock GoldTier boundaries."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from threading import Lock, RLock
from typing import Never, Protocol, TypeVar
from uuid import UUID, uuid4

from app.connectors.acra import AcraConnector
from app.connectors.errors import (
    ConnectorError,
    MutationOutcomeUncertainError,
    public_connector_error,
)
from app.connectors.goldtier import GoldTierConnector, GoldTierRequestMapper
from app.connectors.goldtier_models import (
    GoldTierOutcome,
    GoldTierRequestMetadata,
    GoldTierSearchOutcome,
    GoldTierSearchResult,
    SearchPartyRequest,
)
from app.connectors.goldtier_xpi_models import XpiCustomerSearchRequest
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
    ExistingTargetStateProvenance,
    GoldTierResult,
    InitialCustomerIdentity,
    InitialGoldTierSearchEvidence,
    OnboardingCase,
    RegistryAcquisitionStatus,
    RegistryOperationStatus,
    SafeError,
    WorkflowEvent,
    WorkflowState,
)
from app.domain.onboarding_intelligence import (
    EntityIdentity,
    EntityResolutionOutcome,
    EntityResolutionResult,
)
from app.domain.policy import (
    GOLDTIER_CLIENT_SEGMENT_VALUES,
    GOLDTIER_KYC_CUSTOMER_TYPE_VALUES,
    AuthorityLabelledTargetValue,
    CasePolicySnapshot,
    IntelligencePolicySnapshot,
    PolicyAuthority,
    legacy_phase13_policy_snapshot,
)
from app.domain.reconciliation import ReconciliationField
from app.domain.target_preparation import GoldTierRequestPreview
from app.domain.target_submission import (
    GoldTierExecutionClassification,
    GoldTierExecutionError,
    GoldTierExecutionLedgerEntry,
    GoldTierExecutionLedgerState,
    GoldTierExecutionReceipt,
    GoldTierExecutionResult,
    GoldTierIdempotencyBindings,
    GoldTierOperationMarker,
    GoldTierProviderFailureStatus,
    GoldTierProviderMode,
    GoldTierRecoveryOrigin,
    GoldTierSearchResolution,
    GoldTierSubmissionInput,
    GoldTierTargetOutcome,
    ProviderVerifiedFailure,
    ProviderVerifiedRecovery,
    SubmissionCanonicalEntity,
    SubmissionRegisteredAddress,
)
from app.mappers.goldtier import MockGoldTierRequestMapper
from app.services.canonical_validation import validate_entity
from app.services.errors import (
    OnboardingInfrastructureError,
    TargetProviderContextMismatchError,
)
from app.services.registry_acquisition import (
    RegistryAcquisitionCoordinator,
    RegistryCacheError,
)
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


_INITIAL_SEARCH_FAILURES: dict[str, tuple[str, int, str]] = {
    "GT_XPI_SEARCH_INVALID": (
        "SEARCH_REQUEST_REJECTED",
        400,
        "GoldTier rejected the customer Search request.",
    ),
    "GT_XPI_TIMEOUT": ("SEARCH_TIMEOUT", 504, "GoldTier customer Search timed out."),
    "GT_XPI_SERVICE_UNAVAILABLE": (
        "SEARCH_SERVICE_UNAVAILABLE",
        503,
        "GoldTier customer Search is unavailable.",
    ),
    "GT_XPI_CONFIGURATION_ERROR": (
        "SEARCH_SERVICE_UNAVAILABLE",
        503,
        "GoldTier customer Search is unavailable.",
    ),
    "GT_XPI_MALFORMED_RESPONSE": (
        "SEARCH_MALFORMED_RESPONSE",
        502,
        "GoldTier customer Search returned an invalid response.",
    ),
}


def _initial_search_failure(
    code: str | None, *, status_code: int | None = None
) -> GoldTierSearchResult:
    safe_code, safe_status, message = _INITIAL_SEARCH_FAILURES.get(
        code or "",
        ("SEARCH_SERVICE_UNAVAILABLE", 503, "GoldTier customer Search could not be completed."),
    )
    return GoldTierSearchResult(
        outcome=GoldTierSearchOutcome.FAILURE,
        status_code=status_code or safe_status,
        error_code=safe_code,
        message=message,
    )


class EntityResolver(Protocol):
    def resolve_entity(
        self,
        *,
        source: EntityIdentity,
        candidates: tuple[EntityIdentity, ...],
        policy: IntelligencePolicySnapshot | None = None,
    ) -> EntityResolutionResult: ...


@dataclass(frozen=True)
class TargetIdentitySearchEvidence:
    """Validated read-only target result plus the existing resolver's decision."""

    result: GoldTierSearchResult
    resolution: EntityResolutionResult | None


MALFORMED_TARGET_RESPONSE_CODE = "GT_MALFORMED_TARGET_RESPONSE"
MALFORMED_TARGET_RESPONSE_MESSAGE = "GoldTier target returned an invalid response."
TARGET_OUTCOME_FALLBACK_CODE = "GT_TARGET_OUTCOME_RECORDING_FAILED"
TARGET_OUTCOME_FALLBACK_MESSAGE = "GoldTier target outcome recording failed safely."


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
        readback_party_id=outcome.readback_party_id,
        readback_status=outcome.readback_status,
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
    return messages.get(code, "GoldTier operation returned a controlled failure.")


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
        registry_acquisition_coordinator: RegistryAcquisitionCoordinator | None = None,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
        target_finalization_fault: Callable[[UUID], bool] | None = None,
        target_execution_repository: TargetExecutionRepository | None = None,
        policy_snapshot_provider: Callable[[], CasePolicySnapshot] | None = None,
        goldtier_mapper: GoldTierRequestMapper | None = None,
        entity_resolver: EntityResolver | None = None,
    ) -> None:
        if registry_router is None:
            if acra is None:
                raise ValueError("Onboarding service requires a registry provider router")
            registry_router = RegistryProviderRouter(AcraRegistryProviderAdapter(acra))
        self._registry_router = registry_router
        self._registry_acquisition_coordinator = registry_acquisition_coordinator
        self._jurisdiction_resolver = JurisdictionResolver()
        self._goldtier = goldtier
        self._goldtier_mapper = goldtier_mapper or MockGoldTierRequestMapper()
        if entity_resolver is None:
            # Local import avoids the service module cycle while ensuring every
            # candidate set uses the single existing entity-resolution engine.
            from app.services.onboarding_intelligence import OnboardingIntelligenceService

            entity_resolver = OnboardingIntelligenceService()
        self._entity_resolver = entity_resolver
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4
        self._target_finalization_fault = target_finalization_fault
        self._case_locks: dict[UUID, RLock] = {}
        self._case_locks_guard = Lock()
        self._execution_ledger_guard = RLock()
        self._target_executions = target_execution_repository or InMemoryTargetExecutionRepository()
        self._policy_snapshot_provider = policy_snapshot_provider or legacy_phase13_policy_snapshot

    def case_lock(self, case_id: UUID) -> RLock:
        """Share one in-process evidence/submission boundary per case."""

        with self._case_locks_guard:
            return self._case_locks.setdefault(case_id, RLock())

    @property
    def case_repository(self) -> OnboardingCaseRepository:
        return self._repository

    @property
    def target_provider_mode(self) -> GoldTierProviderMode:
        return self._goldtier_mapper.environment

    def bind_goldtier_case_classification(
        self,
        *,
        case_id: UUID,
        kyc_customer_type: str,
        client_segment: str,
    ) -> OnboardingCase:
        """Bind one validated operator decision into the case target snapshot."""

        if kyc_customer_type not in GOLDTIER_KYC_CUSTOMER_TYPE_VALUES:
            raise ValueError("GoldTier KYC customer type is not in the current vocabulary")
        if client_segment not in GOLDTIER_CLIENT_SEGMENT_VALUES:
            raise ValueError("GoldTier client segment is not in the current vocabulary")
        with self.case_lock(case_id):
            case = self._repository.get(case_id)
            if case is None:
                raise ValueError("Onboarding case was not found")
            target = case.policy_snapshot.goldtier_target
            if target is None:
                raise ValueError("GoldTier target policy is unavailable for this case")
            if case.goldtier_result is not None or case.state in {
                WorkflowState.GT_SHELL_CREATED,
                WorkflowState.GT_POLICY_CREATED,
                WorkflowState.GT_ENRICHED,
                WorkflowState.COMPLETED,
            }:
                raise ValueError("GoldTier target classification is already frozen")

            already_bound = (
                target.kyc_customer_type.authority != PolicyAuthority.TBD_SPONSOR
                and target.client_segment.authority != PolicyAuthority.TBD_SPONSOR
            )
            if already_bound:
                if (
                    target.kyc_customer_type.value == kyc_customer_type
                    and target.client_segment.value == client_segment
                ):
                    return case.model_copy(deep=True)
                raise ValueError("GoldTier target classification is already frozen")

            timestamp = self._clock()
            selected_target = target.model_copy(
                update={
                    "kyc_customer_type": AuthorityLabelledTargetValue(
                        value=kyc_customer_type,
                        authority=PolicyAuthority.USER_AUTHORIZED_POC,
                    ),
                    "client_segment": AuthorityLabelledTargetValue(
                        value=client_segment,
                        authority=PolicyAuthority.USER_AUTHORIZED_POC,
                    ),
                },
                deep=True,
            )
            updated = case.model_copy(deep=True)
            updated.policy_snapshot = case.policy_snapshot.model_copy(
                update={"goldtier_target": selected_target}, deep=True
            )
            updated.updated_at = timestamp
            updated.events.append(
                WorkflowEvent(
                    sequence=len(updated.events) + 1,
                    stage=updated.state,
                    outcome=EventOutcome.SUCCEEDED,
                    timestamp=timestamp,
                    case_id=updated.case_id,
                    correlation_id=updated.correlation_id,
                    code="GOLDTIER_CASE_CLASSIFICATION_BOUND",
                    message=(
                        "Authorized case-specific GoldTier classifications were bound "
                        "to the case policy snapshot."
                    ),
                )
            )
            validated = OnboardingCase.model_validate(updated)
            self._repository.save(validated)
            return validated.model_copy(deep=True)

    def search_sandbox_target(
        self,
        request: XpiCustomerSearchRequest,
        *,
        correlation_id: UUID,
    ) -> TargetIdentitySearchEvidence:
        """Execute one read-only XPI Search outside the case lifecycle.

        The standalone provider console never obtains access to mutation methods.
        """

        if self.target_provider_mode != GoldTierProviderMode.SANDBOX:
            raise ValueError("GoldTier sandbox Search is not configured")
        result = validate_search_response(
            self._goldtier.search_party(
                request,
                GoldTierRequestMetadata(
                    correlation_id=correlation_id,
                    source_case_id="SANDBOX-CONSOLE",
                    idempotency_key=self._uuid_factory(),
                ),
            )
        )
        source = EntityIdentity(
            candidate_id="SANDBOX-CONSOLE",
            country=request.country_of_incorporation,
            legal_name=request.legal_name or request.group_company_name,
            source_reference="GOLDTIER_SANDBOX_CONSOLE",
        )
        resolution = self._entity_resolver.resolve_entity(
            source=source,
            candidates=self._target_candidate_identities(result),
            policy=self._policy_snapshot_provider().intelligence,
        )
        return TargetIdentitySearchEvidence(result=result, resolution=resolution)

    def reserve_case_identity(self) -> tuple[UUID, UUID]:
        """Allocate the identifiers needed before the lifecycle lock is acquired."""

        return self._uuid_factory(), self._uuid_factory()

    def create_case(
        self,
        uen: str,
        country_of_incorporation: JurisdictionCode | str | None = None,
        *,
        legal_name: str | None = None,
        team_id: TeamId | None = None,
        priority: CasePriority | None = None,
    ) -> OnboardingCase:
        """Preserve the Phase 01 API as staged intake plus Mock GoldTier submission."""

        case = self.create_staged_case(
            uen,
            country_of_incorporation,
            legal_name=legal_name,
            team_id=team_id,
            priority=priority,
        )
        if case.state != WorkflowState.VALIDATED:
            return case
        return self.submit_staged_case(case.case_id, complete_legacy_flow=True)

    def create_staged_case(
        self,
        uen: str,
        country_of_incorporation: JurisdictionCode | str | None = None,
        *,
        legal_name: str | None = None,
        team_id: TeamId | None = None,
        priority: CasePriority | None = None,
    ) -> OnboardingCase:
        """Resolve jurisdiction, route, and validate registry data without GoldTier."""

        case_id, correlation_id = self.reserve_case_identity()
        return self.create_staged_case_with_identity(
            case_id,
            correlation_id,
            uen,
            country_of_incorporation,
            legal_name=legal_name,
            team_id=team_id,
            priority=priority,
        )

    def create_staged_case_with_identity(
        self,
        case_id: UUID,
        correlation_id: UUID,
        uen: str,
        country_of_incorporation: JurisdictionCode | str | None = None,
        *,
        legal_name: str | None = None,
        team_id: TeamId | None = None,
        priority: CasePriority | None = None,
    ) -> OnboardingCase:
        """Create a staged case using an identity reserved by an aggregate owner."""

        with self.case_lock(case_id):
            return self._create_staged_case_locked(
                case_id,
                correlation_id,
                uen,
                country_of_incorporation,
                legal_name=legal_name,
                team_id=team_id,
                priority=priority,
            )

    def _create_staged_case_locked(
        self,
        case_id: UUID,
        correlation_id: UUID,
        uen: str,
        country_of_incorporation: JurisdictionCode | str | None,
        *,
        legal_name: str | None,
        team_id: TeamId | None,
        priority: CasePriority | None,
    ) -> OnboardingCase:
        """Create and mutate one case while its canonical lifecycle lock is held."""

        now = self._clock()
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
            initial_identity=(
                InitialCustomerIdentity(
                    legal_name=legal_name,
                    registration_number=normalised_uen,
                    country_of_incorporation=explicit_jurisdiction.value,
                )
                if legal_name is not None and explicit_jurisdiction is not None
                else None
            ),
            policy_snapshot=self._policy_snapshot_provider(),
            team_id=team_id,
            priority=priority,
            jurisdiction_resolution=resolution,
            state=WorkflowState.REQUESTED,
            created_at=now,
            updated_at=now,
        )
        self._record(
            case,
            WorkflowState.REQUESTED,
            EventOutcome.SUCCEEDED,
            "Case requested.",
            create=True,
        )

        if legal_name is not None:
            if explicit_jurisdiction is None:
                return self._terminate(
                    case,
                    WorkflowState.REVIEW_REQUIRED,
                    EventOutcome.REVIEW_REQUIRED,
                    "INITIAL_IDENTITY_INCOMPLETE",
                    (
                        "Legal name, registration number, and country are required for "
                        "target-first identity."
                    ),
                )
            if resolution.status == JurisdictionResolutionStatus.UNRESOLVED:
                return self._terminate(
                    case,
                    WorkflowState.REVIEW_REQUIRED,
                    EventOutcome.REVIEW_REQUIRED,
                    "JURISDICTION_UNRESOLVED",
                    "Jurisdiction could not be resolved before target Search.",
                )
            if resolution.status == JurisdictionResolutionStatus.CONFLICT:
                return self._terminate(
                    case,
                    WorkflowState.REVIEW_REQUIRED,
                    EventOutcome.REVIEW_REQUIRED,
                    "JURISDICTION_CONFLICT",
                    "Conflicting jurisdiction evidence blocks target Search.",
                )
            if (
                resolution.resolved_jurisdiction != JurisdictionCode.SINGAPORE
                or not is_eligible_singapore_uen(normalised_uen)
            ):
                return self._terminate(
                    case,
                    WorkflowState.REVIEW_REQUIRED,
                    EventOutcome.REVIEW_REQUIRED,
                    "INITIAL_IDENTITY_NOT_ELIGIBLE",
                    "The initial identity is not eligible for the implemented Singapore route.",
                )
            search_request_id = self._uuid_factory()
            search_request = (
                XpiCustomerSearchRequest(
                    legal_name=legal_name,
                    country_of_incorporation=explicit_jurisdiction.value,
                )
                if self.target_provider_mode == GoldTierProviderMode.SANDBOX
                else SearchPartyRequest(registration_number=normalised_uen)
            )
            try:
                result = validate_search_response(
                    self._goldtier.search_party(
                        search_request,
                        GoldTierRequestMetadata(
                            correlation_id=correlation_id,
                            source_case_id=source_case_id,
                            idempotency_key=search_request_id,
                        ),
                    )
                )
            except ConnectorError as exc:
                result = _initial_search_failure(exc.code)
            except InvalidTargetResponseError:
                result = _initial_search_failure("GT_XPI_MALFORMED_RESPONSE")

            disposition = "REVIEW_REQUIRED"
            selected_party_id: str | None = None
            if result.outcome == GoldTierSearchOutcome.NO_MATCH:
                disposition = "NO_MATCH"
            elif result.outcome == GoldTierSearchOutcome.FAILURE:
                result = _initial_search_failure(
                    result.error_code,
                    status_code=result.status_code,
                )
                disposition = "FAILED"
            elif (
                result.outcome == GoldTierSearchOutcome.MATCH_FOUND
                and len(result.candidates) == 1
            ):
                candidate = result.candidates[0]
                prior = self._repository.find_verified_target_case(
                    registration_number=normalised_uen,
                    legal_name=legal_name,
                    country_of_incorporation=explicit_jurisdiction.value,
                    party_id=candidate.party_id,
                )
                if prior is not None and prior.entity is not None:
                    def normalized(value: str) -> str:
                        return " ".join(value.strip().split()).casefold()

                    candidate_identity_matches = (
                        candidate.legal_name is not None
                        and normalized(candidate.legal_name) == normalized(legal_name)
                    ) or (
                        candidate.registration_number is not None
                        and candidate.registration_number.strip().upper() == normalised_uen
                        and candidate.country is not None
                        and candidate.country.strip().upper() == explicit_jurisdiction.value
                    )
                    if candidate_identity_matches:
                        disposition = "EXACT_MATCH"
                        selected_party_id = candidate.party_id
                        case.entity = prior.entity.model_copy(deep=True)
                        case.existing_target_state = ExistingTargetStateProvenance(
                            source_case_id=prior.case_id,
                            target_party_id=candidate.party_id,
                            verified_at=self._clock(),
                        )
            case.initial_target_search = InitialGoldTierSearchEvidence(
                request_id=search_request_id,
                disposition=disposition,
                provider_outcome=(
                    result.error_code
                    if disposition == "FAILED" and result.error_code is not None
                    else result.outcome.value
                ),
                status_code=result.status_code,
                candidate_count=len(result.candidates),
                candidate_party_ids=tuple(item.party_id for item in result.candidates),
                candidate_legal_names=tuple(item.legal_name for item in result.candidates),
                selected_party_id=selected_party_id,
                searched_at=self._clock(),
            )
            if disposition == "EXACT_MATCH":
                self._record(
                    case,
                    WorkflowState.VALIDATED,
                    EventOutcome.SUCCEEDED,
                    (
                        "Exact existing GoldTier target state was hydrated; ACRA and Shell "
                        "are skipped."
                    ),
                    "GOLDTIER_FIRST_EXACT_MATCH",
                )
                return case.model_copy(deep=True)
            if disposition == "REVIEW_REQUIRED":
                return self._terminate(
                    case,
                    WorkflowState.REVIEW_REQUIRED,
                    EventOutcome.REVIEW_REQUIRED,
                    "GT_SEARCH_IDENTITY_REVIEW_REQUIRED",
                    (
                        "GoldTier candidates require exact identity review; ACRA and target "
                        "writes are blocked."
                    ),
                )
            if disposition == "FAILED":
                self._record(
                    case,
                    WorkflowState.GT_SEARCHED,
                    EventOutcome.FAILED,
                    result.message,
                    result.error_code or "SEARCH_SERVICE_UNAVAILABLE",
                )
            else:
                self._record(
                    case,
                    WorkflowState.GT_SEARCHED,
                    EventOutcome.SUCCEEDED,
                    "No GoldTier customer was found; ACRA acquisition may continue.",
                    "GOLDTIER_FIRST_NO_MATCH",
                )

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

        binding = None
        registry_coordinator = self._registry_acquisition_coordinator
        if registry_coordinator is None:
            acquisition = self._run_required_stage(
                case,
                code="ACRA_RETRIEVAL_UNEXPECTED_FAILURE",
                message="Corporate registry retrieval could not be completed.",
                operation=lambda: registry_provider.retrieve_acquisition(normalised_uen),
            )
        else:
            coordinated = self._run_required_stage(
                case,
                code="REGISTRY_CACHE_FAILURE",
                message="Registry evidence could not be prepared safely.",
                operation=lambda: registry_coordinator.acquire(
                    registry_provider,
                    normalised_uen,
                ),
            )
            acquisition = coordinated.acquisition
            binding = coordinated.binding
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
        case.registry_evidence_binding = binding
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
                raise ValueError("Onboarding case is not eligible for GoldTier target submission")
            submission_input = self.build_submission_input(
                case,
                correlation_id=case.correlation_id,
                provider_mode=self.target_provider_mode,
            )
            receipt = self.execute_submission_input(
                submission_input,
                complete_legacy_flow=complete_legacy_flow,
            )
            if receipt.infrastructure_failure:
                error = receipt.error or GoldTierExecutionError(
                    code="GT_OPERATION_FAILED",
                    message="GoldTier target submission could not be completed.",
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
        idempotency: GoldTierIdempotencyBindings | None = None,
        provider_mode: GoldTierProviderMode,
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
            provider_mode=provider_mode,
            policy_catalogue_version=case.policy_snapshot.catalogue_version,
            target_external_key=(
                f"FYP-{case.case_id.hex.upper()}"
                if provider_mode == GoldTierProviderMode.SANDBOX
                else None
            ),
            target_policy=case.policy_snapshot.goldtier_target,
            canonical_entity=SubmissionCanonicalEntity(
                registration_number=entity.registration_number,
                legal_name=entity.legal_name,
                country_of_incorporation=entity.country_of_incorporation,
                party_type=entity.party_type,
                registration_date=entity.registration_date,
                entity_status=entity.entity_status,
                registered_address=SubmissionRegisteredAddress.model_validate(address.model_dump()),
            ),
            idempotency=idempotency
            or GoldTierIdempotencyBindings(
                search=self._uuid_factory(),
                shell=self._uuid_factory(),
                policy=self._uuid_factory(),
                amend=self._uuid_factory(),
            ),
        )

    def build_request_preview(
        self,
        case: OnboardingCase,
        *,
        provider_mode: GoldTierProviderMode,
    ) -> GoldTierRequestPreview:
        """Build a bounded case-scoped preview without reserving execution identity."""

        preview_bindings = GoldTierIdempotencyBindings(
            search=case.case_id,
            shell=case.case_id,
            policy=case.case_id,
            amend=case.case_id,
        )
        preview_input = self.build_submission_input(
            case,
            submission_id=case.case_id,
            correlation_id=case.correlation_id,
            accepted_at=case.updated_at,
            idempotency=preview_bindings,
            provider_mode=provider_mode,
        )
        return self._goldtier_mapper.build_preview(preview_input)

    def search_target_identity(
        self,
        *,
        case_id: UUID,
        request_id: UUID,
        provider_mode: GoldTierProviderMode,
        searched_at: datetime,
    ) -> TargetIdentitySearchEvidence:
        """Run one bounded read-only Search after canonical registry identity exists.

        This does not reserve mutation-ledger ownership and never changes the onboarding
        case state. The CLM aggregate retains the safe checkpoint and later seeds the
        existing target ledger from it.
        """

        if (
            provider_mode != self._goldtier_mapper.environment
            or provider_mode != self._goldtier.environment
        ):
            raise TargetProviderContextMismatchError
        with self.case_lock(case_id):
            case = self._repository.get(case_id)
            if case is None or case.entity is None or validate_entity(case.entity):
                raise ValueError("Canonical registry identity is not ready for target Search")
            search_input = self.build_submission_input(
                case,
                submission_id=request_id,
                correlation_id=case.correlation_id,
                accepted_at=searched_at,
                provider_mode=provider_mode,
                idempotency=GoldTierIdempotencyBindings(
                    search=request_id,
                    shell=request_id,
                    policy=request_id,
                    amend=request_id,
                ),
            )
            untrusted = self._goldtier.search_party(
                self._goldtier_mapper.build_search_request(search_input),
                self._metadata(search_input, request_id),
            )
            result = validate_search_response(untrusted)
        return TargetIdentitySearchEvidence(
                result=result,
                resolution=self._resolve_target_candidates(
                    search_input,
                    result,
                    policy=case.policy_snapshot.intelligence,
                ),
            )

    def _resolve_target_candidates(
        self,
        submission_input: GoldTierSubmissionInput,
        result: GoldTierSearchResult,
        *,
        policy: IntelligencePolicySnapshot | None,
    ) -> EntityResolutionResult | None:
        if not result.candidates or self._entity_resolver is None:
            return None
        entity = submission_input.canonical_entity
        address = entity.registered_address
        address_text = " ".join(
            item
            for item in (
                address.address_line_1,
                address.address_line_2,
                address.postal_code,
                address.country_code,
            )
            if item
        )
        source = EntityIdentity(
            candidate_id=submission_input.source_case_id,
            registration_number=entity.registration_number,
            country=entity.country_of_incorporation,
            legal_name=entity.legal_name,
            legal_form=entity.party_type,
            registered_address=address_text,
            incorporated_on=entity.registration_date,
            source_reference=f"case:{submission_input.case_id}",
        )
        return self._entity_resolver.resolve_entity(
            source=source,
            candidates=self._target_candidate_identities(result),
            policy=policy,
        )

    @staticmethod
    def _target_candidate_identities(
        result: GoldTierSearchResult,
    ) -> tuple[EntityIdentity, ...]:
        return tuple(
            EntityIdentity(
                candidate_id=candidate.party_id,
                registration_number=candidate.registration_number,
                country=candidate.country,
                legal_name=candidate.legal_name,
                legal_form=candidate.legal_form,
                registered_address=candidate.registered_address,
                source_reference=f"goldtier:{candidate.party_id}",
            )
            for candidate in result.candidates
        )

    def execute_submission_input(
        self,
        submission_input: GoldTierSubmissionInput,
        *,
        complete_legacy_flow: bool = False,
    ) -> GoldTierExecutionReceipt:
        """Execute once and retain the target outcome before rich receipt mapping."""

        if (
            submission_input.provider_mode != self._goldtier_mapper.environment
            or submission_input.provider_mode != self._goldtier.environment
        ):
            raise TargetProviderContextMismatchError

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
                raise RuntimeError("GoldTier target submission is already in progress")

            case = self._repository.get(submission_input.case_id)
            if case is None:
                raise ValueError("Onboarding case was not found")
            if (
                case.source_case_id != submission_input.source_case_id
                or case.state != WorkflowState.VALIDATED
                or validate_entity(submission_input.canonical_entity)
            ):
                raise ValueError("Submission input is not eligible for GoldTier target execution")

            if (
                submission_input.policy_catalogue_version != case.policy_snapshot.catalogue_version
                or submission_input.target_policy != case.policy_snapshot.goldtier_target
            ):
                raise ValueError(
                    "Submission target policy does not match the owning case policy snapshot"
                )
            preview = self._goldtier_mapper.build_preview(submission_input)
            if not preview.dispatch_ready:
                raise ValueError("Required GoldTier target enrichment is unavailable.")
            try:
                self._goldtier_mapper.validate_pre_dispatch(submission_input)
            except ValueError:
                raise ValueError("Required GoldTier target preparation is invalid.") from None

            self._start_execution(submission_input)
            outcome_uncertain = False
            try:
                self._submit_to_goldtier(
                    case,
                    submission_input,
                    complete_legacy_flow=complete_legacy_flow,
                )
            except MutationOutcomeUncertainError:
                outcome_uncertain = True
                raise
            except OnboardingInfrastructureError:
                pass
            finally:
                if not outcome_uncertain:
                    self._ensure_execution_owner_exit(submission_input)

            recorded = self.get_target_outcome(submission_input.submission_id)
            if recorded is None:
                raise RuntimeError("GoldTier target execution outcome was not retained")
            return self._finalize_execution_receipt(submission_input, recorded)

    def advance_incremental_submission_input(
        self,
        submission_input: GoldTierSubmissionInput,
        *,
        search_resolution: GoldTierSearchResolution,
        selected_party_id: str | None,
    ) -> GoldTierExecutionReceipt | None:
        """Advance at most one mutation after a retained early Search checkpoint."""

        if (
            submission_input.provider_mode != self._goldtier_mapper.environment
            or submission_input.provider_mode != self._goldtier.environment
        ):
            raise TargetProviderContextMismatchError
        with self.case_lock(submission_input.case_id):
            case = self._repository.get(submission_input.case_id)
            if (
                case is None
                or case.entity is None
                or validate_entity(submission_input.canonical_entity)
            ):
                raise ValueError("Submission input is not eligible for target execution")
            if case.state not in {
                WorkflowState.VALIDATED,
                WorkflowState.GT_SHELL_CREATED,
                WorkflowState.GT_POLICY_CREATED,
                WorkflowState.GT_ENRICHED,
            }:
                raise ValueError("Onboarding case is not eligible for incremental target execution")
            if (
                submission_input.policy_catalogue_version != case.policy_snapshot.catalogue_version
                or submission_input.target_policy != case.policy_snapshot.goldtier_target
            ):
                raise ValueError(
                    "Submission target policy does not match the owning case policy snapshot"
                )

            preview = self._goldtier_mapper.build_preview(submission_input)
            if not preview.dispatch_ready:
                raise ValueError("Required GoldTier target enrichment is unavailable.")

            entry = self._stored_execution_entry(submission_input)
            if entry is None:
                self._start_incremental_execution(
                    submission_input,
                    search_resolution=search_resolution,
                    selected_party_id=selected_party_id,
                )
                entry = self._stored_execution_entry(submission_input)
            if entry is None:
                raise RuntimeError("GoldTier target execution could not be retained")
            if entry.receipt is not None:
                return entry.receipt.model_copy(deep=True)
            if entry.target_outcome is not None:
                return self._finalize_execution_receipt(submission_input, entry.target_outcome)
            if entry.provider_verified_amend_failure is not None:
                raise ValueError(
                    "Amend has a provider-verified failure and must not be replayed"
                )
            if entry.attempted_operations != entry.lifecycle_resolved_operations:
                raise MutationOutcomeUncertainError

            party_id = entry.resolved_party_id
            if party_id is None:
                return self._advance_shell(case, submission_input, entry)
            if (
                entry.policy_status is None
                and entry.search_resolution != GoldTierSearchResolution.EXACT_MATCH
            ):
                return self._advance_policy(case, submission_input, entry, party_id)
            if entry.amend_status is None:
                return self._advance_amend(case, submission_input, entry, party_id)
            if (
                submission_input.provider_mode == GoldTierProviderMode.SANDBOX
                and entry.readback_status is None
            ):
                return self._advance_readback(case, submission_input, entry, party_id)
            raise RuntimeError("GoldTier target execution progress is inconsistent")

    def _start_incremental_execution(
        self,
        submission_input: GoldTierSubmissionInput,
        *,
        search_resolution: GoldTierSearchResolution,
        selected_party_id: str | None,
    ) -> None:
        if search_resolution == GoldTierSearchResolution.EXACT_MATCH:
            if selected_party_id is None:
                raise ValueError("Exact target Search requires a selected party")
            shell_status = "EXISTING_PARTY_REUSED"
        else:
            if selected_party_id is not None:
                raise ValueError("No-match target Search cannot select a party")
            shell_status = None
        entry = GoldTierExecutionLedgerEntry(
            submission_input=submission_input.model_copy(deep=True),
            state=GoldTierExecutionLedgerState.IN_PROGRESS,
            attempted_operations=(GoldTierOperationMarker.SEARCH,),
            completed_operations=(GoldTierOperationMarker.SEARCH,),
            resolved_operations=(GoldTierOperationMarker.SEARCH,),
            search_resolution=search_resolution,
            resolved_party_id=selected_party_id,
            shell_status=shell_status,
        )
        with self._execution_ledger_guard:
            try:
                self._target_executions.create(entry)
            except TargetExecutionRepositoryConflictError:
                raise RuntimeError("GoldTier target submission identity already exists") from None

    def _record_incremental_progress(
        self,
        submission_input: GoldTierSubmissionInput,
        *,
        completed_operation: GoldTierOperationMarker,
        resolved_party_id: str | None,
        shell_status: str | None,
        policy_id: str | None = None,
        policy_status: str | None = None,
        amend_status: str | None = None,
        readback_party_id: str | None = None,
        readback_status: str | None = None,
    ) -> GoldTierExecutionLedgerEntry:
        with self._execution_ledger_guard:
            entry = self._target_executions.get(submission_input.submission_id)
            if (
                entry is None
                or entry.submission_input != submission_input
                or entry.state != GoldTierExecutionLedgerState.IN_PROGRESS
                or not entry.attempted_operations
                or entry.attempted_operations[-1] != completed_operation
            ):
                raise ValueError("Target progress does not match an active operation")
            completed = (*entry.definitively_completed_operations, completed_operation)
            resolved = (*entry.lifecycle_resolved_operations, completed_operation)
            if resolved != entry.attempted_operations:
                raise ValueError("Target progress cannot skip an attempted operation")
            candidate = GoldTierExecutionLedgerEntry(
                submission_input=entry.submission_input,
                state=entry.state,
                attempted_operations=entry.attempted_operations,
                completed_operations=completed,
                resolved_operations=resolved,
                provider_verified_recovery=entry.provider_verified_recovery,
                provider_verified_policy_recovery=(
                    entry.provider_verified_policy_recovery
                ),
                provider_verified_amend_failure=entry.provider_verified_amend_failure,
                search_resolution=entry.search_resolution,
                resolved_party_id=resolved_party_id,
                shell_status=shell_status,
                policy_id=policy_id,
                policy_status=policy_status,
                amend_status=amend_status,
                readback_party_id=readback_party_id,
                readback_status=readback_status,
            )
            self._target_executions.replace(
                candidate, expected_state=GoldTierExecutionLedgerState.IN_PROGRESS.value
            )
            return candidate.model_copy(deep=True)

    def _advance_shell(
        self,
        case: OnboardingCase,
        submission_input: GoldTierSubmissionInput,
        entry: GoldTierExecutionLedgerEntry,
    ) -> GoldTierExecutionReceipt | None:
        request = self._goldtier_mapper.build_shell_request(submission_input)
        self._mark_operation_attempted(submission_input, GoldTierOperationMarker.SHELL)
        try:
            untrusted = self._goldtier.create_shell_customer(
                request,
                self._metadata(submission_input, submission_input.idempotency.shell),
            )
        except MutationOutcomeUncertainError:
            raise
        except ConnectorError as exc:
            public = public_connector_error(exc)
            self._record_fixed_failure_outcome(
                submission_input,
                completed_operations=(
                    *entry.lifecycle_resolved_operations,
                    GoldTierOperationMarker.SHELL,
                ),
                code=public.code,
                message=public.message,
            )
            self._terminate(
                case, WorkflowState.FAILED, EventOutcome.FAILED, public.code, public.message
            )
            return self._finalize_recorded_outcome(submission_input)
        try:
            shell = validate_shell_response(untrusted)
        except InvalidTargetResponseError:
            self._record_fixed_failure_outcome(
                submission_input,
                completed_operations=(
                    *entry.lifecycle_resolved_operations,
                    GoldTierOperationMarker.SHELL,
                ),
                code=MALFORMED_TARGET_RESPONSE_CODE,
                message=MALFORMED_TARGET_RESPONSE_MESSAGE,
            )
            self._terminate(
                case,
                WorkflowState.FAILED,
                EventOutcome.FAILED,
                MALFORMED_TARGET_RESPONSE_CODE,
                MALFORMED_TARGET_RESPONSE_MESSAGE,
            )
            return self._finalize_recorded_outcome(submission_input)
        completed = (*entry.lifecycle_resolved_operations, GoldTierOperationMarker.SHELL)
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
                completed_operations=completed,
                error_code=code,
                error_message=message,
            )
            self._terminate(case, WorkflowState.FAILED, EventOutcome.FAILED, code, message)
            return self._finalize_recorded_outcome(submission_input)
        self._record_incremental_progress(
            submission_input,
            completed_operation=GoldTierOperationMarker.SHELL,
            resolved_party_id=shell.party_id,
            shell_status=shell.status,
        )
        case.goldtier_result = GoldTierResult(party_id=shell.party_id, shell_status=shell.status)
        self._record(
            case,
            WorkflowState.GT_SHELL_CREATED,
            EventOutcome.SUCCEEDED,
            "GoldTier shell customer created.",
        )
        return None

    def _advance_policy(
        self,
        case: OnboardingCase,
        submission_input: GoldTierSubmissionInput,
        entry: GoldTierExecutionLedgerEntry,
        party_id: str,
    ) -> GoldTierExecutionReceipt | None:
        request = self._goldtier_mapper.build_policy_request(submission_input, party_id)
        self._mark_operation_attempted(submission_input, GoldTierOperationMarker.POLICY)
        try:
            untrusted = self._goldtier.create_policy(
                request,
                self._metadata(submission_input, submission_input.idempotency.policy),
            )
        except MutationOutcomeUncertainError:
            raise
        except ConnectorError as exc:
            public = public_connector_error(exc)
            self._record_fixed_failure_outcome(
                submission_input,
                completed_operations=(
                    *entry.lifecycle_resolved_operations,
                    GoldTierOperationMarker.POLICY,
                ),
                code=public.code,
                message=public.message,
            )
            self._terminate(
                case, WorkflowState.FAILED, EventOutcome.FAILED, public.code, public.message
            )
            return self._finalize_recorded_outcome(submission_input)
        try:
            policy = validate_policy_response(untrusted, expected_party_id=party_id)
        except InvalidTargetResponseError:
            self._record_fixed_failure_outcome(
                submission_input,
                completed_operations=(
                    *entry.lifecycle_resolved_operations,
                    GoldTierOperationMarker.POLICY,
                ),
                code=MALFORMED_TARGET_RESPONSE_CODE,
                message=MALFORMED_TARGET_RESPONSE_MESSAGE,
            )
            self._terminate(
                case,
                WorkflowState.FAILED,
                EventOutcome.FAILED,
                MALFORMED_TARGET_RESPONSE_CODE,
                MALFORMED_TARGET_RESPONSE_MESSAGE,
            )
            return self._finalize_recorded_outcome(submission_input)
        completed = (*entry.lifecycle_resolved_operations, GoldTierOperationMarker.POLICY)
        if policy.outcome != GoldTierOutcome.SUCCESS:
            code = _project_target_error_code(
                policy.error_code,
                allowed=frozenset(
                    {"GT_POLICY_EXTERNAL_REFERENCE_REQUIRED", "GT_POLICY_VALIDATION_FAILED"}
                ),
                fallback="GT_OPERATION_FAILED",
            )
            message = _controlled_target_failure_message(code)
            self._record_target_outcome(
                submission_input,
                classification=GoldTierExecutionClassification.FAILED,
                onboarding_state=WorkflowState.FAILED,
                completed_operations=completed,
                party_id=party_id,
                shell_status=entry.shell_status,
                policy_status=policy.status,
                error_code=code,
                error_message=message,
            )
            self._terminate(case, WorkflowState.FAILED, EventOutcome.FAILED, code, message)
            return self._finalize_recorded_outcome(submission_input)
        self._record_incremental_progress(
            submission_input,
            completed_operation=GoldTierOperationMarker.POLICY,
            resolved_party_id=party_id,
            shell_status=entry.shell_status,
            policy_id=policy.policy_id,
            policy_status=policy.status,
        )
        case.goldtier_result = GoldTierResult(
            party_id=party_id,
            shell_status=entry.shell_status or "EXISTING_PARTY_REUSED",
            policy_id=policy.policy_id,
            policy_status=policy.status,
        )
        self._record(
            case,
            WorkflowState.GT_POLICY_CREATED,
            EventOutcome.SUCCEEDED,
            "GoldTier customer policy created.",
        )
        return None

    def _advance_amend(
        self,
        case: OnboardingCase,
        submission_input: GoldTierSubmissionInput,
        entry: GoldTierExecutionLedgerEntry,
        party_id: str,
    ) -> GoldTierExecutionReceipt | None:
        request = self._goldtier_mapper.build_amend_request(submission_input, party_id)
        self._mark_operation_attempted(submission_input, GoldTierOperationMarker.AMEND)
        try:
            untrusted = self._goldtier.amend_party(
                party_id,
                request,
                self._metadata(submission_input, submission_input.idempotency.amend),
            )
        except MutationOutcomeUncertainError:
            raise
        except ConnectorError as exc:
            public = public_connector_error(exc)
            self._record_fixed_failure_outcome(
                submission_input,
                completed_operations=(
                    *entry.lifecycle_resolved_operations,
                    GoldTierOperationMarker.AMEND,
                ),
                code=public.code,
                message=public.message,
            )
            self._terminate(
                case, WorkflowState.FAILED, EventOutcome.FAILED, public.code, public.message
            )
            return self._finalize_recorded_outcome(submission_input)
        try:
            amend = validate_amend_response(untrusted, expected_party_id=party_id)
        except InvalidTargetResponseError:
            self._record_fixed_failure_outcome(
                submission_input,
                completed_operations=(
                    *entry.lifecycle_resolved_operations,
                    GoldTierOperationMarker.AMEND,
                ),
                code=MALFORMED_TARGET_RESPONSE_CODE,
                message=MALFORMED_TARGET_RESPONSE_MESSAGE,
            )
            self._terminate(
                case,
                WorkflowState.FAILED,
                EventOutcome.FAILED,
                MALFORMED_TARGET_RESPONSE_CODE,
                MALFORMED_TARGET_RESPONSE_MESSAGE,
            )
            return self._finalize_recorded_outcome(submission_input)
        completed = (*entry.lifecycle_resolved_operations, GoldTierOperationMarker.AMEND)
        if amend.outcome == GoldTierOutcome.PARTIAL_SUCCESS:
            code = _project_target_error_code(
                amend.error_code,
                allowed=frozenset({"GT_OPTIONAL_SECTION_REVIEW"}),
                fallback="GT_PARTIAL_SUCCESS",
            )
            message = "Human review required for the partial GoldTier amendment."
            self._record_target_outcome(
                submission_input,
                classification=GoldTierExecutionClassification.REVIEW_REQUIRED,
                onboarding_state=WorkflowState.REVIEW_REQUIRED,
                completed_operations=completed,
                party_id=party_id,
                shell_status=entry.shell_status,
                policy_id=entry.policy_id,
                policy_status=entry.policy_status,
                amend_status=amend.status,
                error_code=code,
                error_message=message,
            )
            case.goldtier_result = GoldTierResult(
                party_id=party_id,
                shell_status=entry.shell_status or "EXISTING_PARTY_REUSED",
                policy_id=entry.policy_id,
                policy_status=entry.policy_status,
                amend_status=amend.status,
            )
            self._terminate(
                case, WorkflowState.REVIEW_REQUIRED, EventOutcome.REVIEW_REQUIRED, code, message
            )
            return self._finalize_recorded_outcome(submission_input)
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
                completed_operations=completed,
                party_id=party_id,
                shell_status=entry.shell_status,
                policy_id=entry.policy_id,
                policy_status=entry.policy_status,
                amend_status=amend.status,
                error_code=code,
                error_message=message,
            )
            self._terminate(case, WorkflowState.FAILED, EventOutcome.FAILED, code, message)
            return self._finalize_recorded_outcome(submission_input)
        self._record_incremental_progress(
            submission_input,
            completed_operation=GoldTierOperationMarker.AMEND,
            resolved_party_id=party_id,
            shell_status=entry.shell_status,
            policy_id=entry.policy_id,
            policy_status=entry.policy_status,
            amend_status=amend.status,
        )
        if submission_input.provider_mode == GoldTierProviderMode.SANDBOX:
            case.goldtier_result = GoldTierResult(
                party_id=party_id,
                shell_status=entry.shell_status or "EXISTING_PARTY_REUSED",
                policy_id=entry.policy_id,
                policy_status=entry.policy_status,
                amend_status=amend.status,
            )
            existing_party = entry.search_resolution == GoldTierSearchResolution.EXACT_MATCH
            self._record(
                case,
                WorkflowState.VALIDATED if existing_party else WorkflowState.GT_POLICY_CREATED,
                EventOutcome.SUCCEEDED,
                (
                    "Existing GoldTier party amendment succeeded; read-back verification "
                    "is pending."
                    if existing_party
                    else "GoldTier party amendment succeeded; read-back verification is pending."
                ),
                "GT_READBACK_PENDING",
            )
            return None
        self._record_target_outcome(
            submission_input,
            classification=GoldTierExecutionClassification.SUCCESS,
            onboarding_state=WorkflowState.GT_ENRICHED,
            completed_operations=completed,
            party_id=party_id,
            shell_status=entry.shell_status,
            policy_id=entry.policy_id,
            policy_status=entry.policy_status,
            amend_status=amend.status,
        )
        case.goldtier_result = GoldTierResult(
            party_id=party_id,
            shell_status=entry.shell_status or "EXISTING_PARTY_REUSED",
            policy_id=entry.policy_id,
            policy_status=entry.policy_status,
            amend_status=amend.status,
        )
        self._record(
            case,
            WorkflowState.GT_ENRICHED,
            EventOutcome.SUCCEEDED,
            "GoldTier party enriched.",
        )
        return self._finalize_recorded_outcome(submission_input)

    def _advance_readback(
        self,
        case: OnboardingCase,
        submission_input: GoldTierSubmissionInput,
        entry: GoldTierExecutionLedgerEntry,
        party_id: str,
    ) -> GoldTierExecutionReceipt:
        completed = (*entry.lifecycle_resolved_operations, GoldTierOperationMarker.READBACK)
        self._mark_operation_attempted(submission_input, GoldTierOperationMarker.READBACK)
        try:
            untrusted = self._goldtier.search_party(
                self._goldtier_mapper.build_readback_request(submission_input, party_id),
                self._metadata(
                    submission_input,
                    submission_input.idempotency.amend,
                ),
            )
        except ConnectorError as exc:
            public = public_connector_error(exc)
            self._record_target_outcome(
                submission_input,
                classification=GoldTierExecutionClassification.FAILED,
                onboarding_state=WorkflowState.FAILED,
                completed_operations=completed,
                party_id=party_id,
                shell_status=entry.shell_status,
                policy_id=entry.policy_id,
                policy_status=entry.policy_status,
                amend_status=entry.amend_status,
                error_code=public.code,
                error_message=public.message,
                infrastructure_failure=True,
            )
            self._terminate(
                case, WorkflowState.FAILED, EventOutcome.FAILED, public.code, public.message
            )
            return self._finalize_recorded_outcome(submission_input)
        try:
            readback = validate_search_response(untrusted)
        except InvalidTargetResponseError:
            self._record_target_outcome(
                submission_input,
                classification=GoldTierExecutionClassification.FAILED,
                onboarding_state=WorkflowState.FAILED,
                completed_operations=completed,
                party_id=party_id,
                shell_status=entry.shell_status,
                policy_id=entry.policy_id,
                policy_status=entry.policy_status,
                amend_status=entry.amend_status,
                error_code=MALFORMED_TARGET_RESPONSE_CODE,
                error_message=MALFORMED_TARGET_RESPONSE_MESSAGE,
            )
            self._terminate(
                case,
                WorkflowState.FAILED,
                EventOutcome.FAILED,
                MALFORMED_TARGET_RESPONSE_CODE,
                MALFORMED_TARGET_RESPONSE_MESSAGE,
            )
            return self._finalize_recorded_outcome(submission_input)

        verified = (
            readback.outcome == GoldTierSearchOutcome.MATCH_FOUND
            and len(readback.candidates) == 1
            and readback.matched_party_id == party_id
            and readback.candidates[0].party_id == party_id
        )
        if not verified:
            code = "GT_READBACK_IDENTITY_REVIEW_REQUIRED"
            message = "GoldTier read-back did not prove the retained customer identity."
            self._record_target_outcome(
                submission_input,
                classification=GoldTierExecutionClassification.REVIEW_REQUIRED,
                onboarding_state=WorkflowState.REVIEW_REQUIRED,
                completed_operations=completed,
                party_id=party_id,
                shell_status=entry.shell_status,
                policy_id=entry.policy_id,
                policy_status=entry.policy_status,
                amend_status=entry.amend_status,
                error_code=code,
                error_message=message,
            )
            self._terminate(
                case,
                WorkflowState.REVIEW_REQUIRED,
                EventOutcome.REVIEW_REQUIRED,
                code,
                message,
            )
            return self._finalize_recorded_outcome(submission_input)

        self._record_incremental_progress(
            submission_input,
            completed_operation=GoldTierOperationMarker.READBACK,
            resolved_party_id=party_id,
            shell_status=entry.shell_status,
            policy_id=entry.policy_id,
            policy_status=entry.policy_status,
            amend_status=entry.amend_status,
            readback_party_id=party_id,
            readback_status="VERIFIED",
        )
        self._record_target_outcome(
            submission_input,
            classification=GoldTierExecutionClassification.SUCCESS,
            onboarding_state=WorkflowState.GT_ENRICHED,
            completed_operations=completed,
            party_id=party_id,
            shell_status=entry.shell_status,
            policy_id=entry.policy_id,
            policy_status=entry.policy_status,
            amend_status=entry.amend_status,
            readback_party_id=party_id,
            readback_status="VERIFIED",
        )
        case.goldtier_result = GoldTierResult(
            party_id=party_id,
            shell_status=entry.shell_status or "EXISTING_PARTY_REUSED",
            policy_id=entry.policy_id,
            policy_status=entry.policy_status,
            amend_status=entry.amend_status,
            readback_party_id=party_id,
            readback_status="VERIFIED",
        )
        self._record(
            case,
            WorkflowState.GT_ENRICHED,
            EventOutcome.SUCCEEDED,
            "GoldTier post-amendment read-back verified the retained customer identity.",
            "GT_READBACK_VERIFIED",
        )
        return self._finalize_recorded_outcome(submission_input)

    def _finalize_recorded_outcome(
        self, submission_input: GoldTierSubmissionInput
    ) -> GoldTierExecutionReceipt:
        outcome = self.get_target_outcome(submission_input.submission_id)
        if outcome is None:
            raise RuntimeError("GoldTier target outcome was not retained")
        return self._finalize_execution_receipt(submission_input, outcome)

    def get_execution_receipt(self, submission_id: UUID) -> GoldTierExecutionReceipt | None:
        with self._execution_ledger_guard:
            stored = self._target_executions.get(submission_id)
            if stored is None or stored.receipt is None:
                return None
            return stored.receipt.model_copy(deep=True)

    def finalize_recorded_execution(self, submission_id: UUID) -> GoldTierExecutionReceipt | None:
        """Build a receipt from a retained target outcome without target replay."""

        with self._execution_ledger_guard:
            stored = self._target_executions.get(submission_id)
            if stored is None:
                return None
            if stored.receipt is not None:
                return stored.receipt.model_copy(deep=True)
            submission_input = stored.submission_input.model_copy(deep=True)
            outcome = (
                stored.target_outcome.model_copy(deep=True)
                if stored.target_outcome is not None
                else None
            )
        if outcome is None:
            return None
        return self._finalize_execution_receipt(submission_input, outcome)

    def get_target_outcome(self, submission_id: UUID) -> GoldTierTargetOutcome | None:
        with self._execution_ledger_guard:
            stored = self._target_executions.get(submission_id)
            if stored is None or stored.target_outcome is None:
                return None
            return stored.target_outcome.model_copy(deep=True)

    def get_target_execution_entry(
        self, submission_id: UUID
    ) -> GoldTierExecutionLedgerEntry | None:
        """Return one defensive snapshot for internal safe progress projection."""

        with self._execution_ledger_guard:
            stored = self._target_executions.get(submission_id)
            return stored.model_copy(deep=True) if stored is not None else None

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
                and stored.attempted_operations != stored.lifecycle_resolved_operations
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
            completed_operations=(),
        )
        with self._execution_ledger_guard:
            try:
                self._target_executions.create(entry)
            except TargetExecutionRepositoryConflictError:
                raise RuntimeError("GoldTier target submission identity already exists") from None

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
                completed_operations=entry.completed_operations,
                resolved_operations=entry.resolved_operations,
                provider_verified_recovery=entry.provider_verified_recovery,
                provider_verified_policy_recovery=(
                    entry.provider_verified_policy_recovery
                ),
                provider_verified_amend_failure=entry.provider_verified_amend_failure,
                search_resolution=entry.search_resolution,
                resolved_party_id=entry.resolved_party_id,
                shell_status=entry.shell_status,
                policy_id=entry.policy_id,
                policy_status=entry.policy_status,
                amend_status=entry.amend_status,
                readback_party_id=entry.readback_party_id,
                readback_status=entry.readback_status,
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
        readback_party_id: str | None = None,
        readback_status: str | None = None,
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
                readback_party_id=readback_party_id,
                readback_status=readback_status,
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
        readback_party_id: str | None = None,
        readback_status: str | None = None,
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
            readback_party_id=readback_party_id,
            readback_status=readback_status,
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
            recovered_operations = {
                recovery.operation for recovery in entry.provider_verified_recoveries
            }
            definitive = tuple(
                operation
                for operation in outcome.completed_operations
                if operation not in recovered_operations
            )
            candidate = GoldTierExecutionLedgerEntry(
                submission_input=entry.submission_input,
                state=GoldTierExecutionLedgerState.TARGET_OUTCOME_RECORDED,
                attempted_operations=entry.attempted_operations,
                completed_operations=definitive,
                resolved_operations=outcome.completed_operations,
                provider_verified_recovery=entry.provider_verified_recovery,
                provider_verified_policy_recovery=(
                    entry.provider_verified_policy_recovery
                ),
                provider_verified_amend_failure=entry.provider_verified_amend_failure,
                search_resolution=entry.search_resolution,
                resolved_party_id=outcome.party_id,
                shell_status=outcome.shell_status,
                policy_id=outcome.policy_id,
                policy_status=outcome.policy_status,
                amend_status=outcome.amend_status,
                readback_party_id=outcome.readback_party_id,
                readback_status=outcome.readback_status,
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
                attempted_operations=entry.attempted_operations,
                completed_operations=entry.completed_operations,
                resolved_operations=entry.resolved_operations,
                provider_verified_recovery=entry.provider_verified_recovery,
                provider_verified_policy_recovery=(
                    entry.provider_verified_policy_recovery
                ),
                provider_verified_amend_failure=entry.provider_verified_amend_failure,
                search_resolution=entry.search_resolution,
                resolved_party_id=outcome.party_id,
                shell_status=outcome.shell_status,
                policy_id=outcome.policy_id,
                policy_status=outcome.policy_status,
                amend_status=outcome.amend_status,
                readback_party_id=outcome.readback_party_id,
                readback_status=outcome.readback_status,
                target_outcome=outcome,
                receipt=receipt,
            )
            self._target_executions.replace(
                candidate,
                expected_state=GoldTierExecutionLedgerState.TARGET_OUTCOME_RECORDED.value,
            )
        return receipt.model_copy(deep=True)

    def recover_uncertain_shell_from_provider(
        self,
        *,
        submission_input: GoldTierSubmissionInput,
        recovered_party_id: str,
        legal_name: str,
        registration_number: str,
        country_of_incorporation: str,
        actor_id: str,
        origin: GoldTierRecoveryOrigin,
        reauthorize: Callable[[], None] | None = None,
    ) -> GoldTierExecutionLedgerEntry:
        """Resolve one uncertain Shell from exact later provider evidence, never replay it."""

        if self.target_provider_mode != GoldTierProviderMode.SANDBOX:
            raise ValueError("Provider-verified recovery requires the GoldTier sandbox")
        with self.case_lock(submission_input.case_id):
            if reauthorize is not None:
                reauthorize()
            case = self._repository.get(submission_input.case_id)
            if case is None or case.entity is None:
                raise ValueError("Recovery requires the owning canonical case identity")
            expected = submission_input.canonical_entity

            def normalized(value: str) -> str:
                return " ".join(value.strip().split()).casefold()

            if (
                normalized(legal_name) != normalized(expected.legal_name)
                or registration_number.strip().upper()
                != expected.registration_number.strip().upper()
                or country_of_incorporation.strip().upper()
                != expected.country_of_incorporation.strip().upper()
                or case.requested_uen.strip().upper()
                != expected.registration_number.strip().upper()
            ):
                raise ValueError("Recovery identity does not exactly match the owning case")

            idempotent_recovery: GoldTierExecutionLedgerEntry | None = None
            with self._execution_ledger_guard:
                stored = self._target_executions.get(submission_input.submission_id)
                if stored is not None and stored.submission_input != submission_input:
                    raise ValueError("Recovery submission identity conflicts with retained input")
                if stored is not None and stored.provider_verified_recovery is not None:
                    recovery = stored.provider_verified_recovery
                    if (
                        recovery.recovered_party_id == recovered_party_id
                        and normalized(recovery.legal_name) == normalized(legal_name)
                        and recovery.registration_number.upper()
                        == registration_number.strip().upper()
                        and recovery.country_of_incorporation.upper()
                        == country_of_incorporation.strip().upper()
                        and recovery.origin == origin
                    ):
                        idempotent_recovery = stored.model_copy(deep=True)
                    else:
                        raise ValueError("A conflicting provider recovery is already retained")
                if idempotent_recovery is None and stored is not None and (
                    stored.state != GoldTierExecutionLedgerState.IN_PROGRESS
                    or stored.attempted_operations
                    != (GoldTierOperationMarker.SEARCH, GoldTierOperationMarker.SHELL)
                    or stored.definitively_completed_operations
                    not in {(), (GoldTierOperationMarker.SEARCH,)}
                    or stored.search_resolution
                    not in {None, GoldTierSearchResolution.NO_MATCH}
                    or stored.resolved_party_id is not None
                ):
                    raise ValueError("Only one uncertain Shell may be provider-recovered")
                if (
                    idempotent_recovery is None
                    and stored is None
                    and origin != GoldTierRecoveryOrigin.HISTORICAL_LOCAL_LEDGER_LOST
                ):
                    raise ValueError("The retained uncertain ledger is unavailable")

            if idempotent_recovery is not None:
                self._retain_provider_recovered_shell_on_case(
                    case,
                    recovered_party_id=idempotent_recovery.resolved_party_id,
                )
                return idempotent_recovery

            result = validate_search_response(
                self._goldtier.search_party(
                    XpiCustomerSearchRequest(goldtier_id=recovered_party_id),
                    self._metadata(submission_input, submission_input.idempotency.search),
                )
            )
            if (
                result.outcome != GoldTierSearchOutcome.MATCH_FOUND
                or len(result.candidates) != 1
                or result.matched_party_id != recovered_party_id
                or result.candidates[0].party_id != recovered_party_id
                or result.candidates[0].legal_name is None
                or normalized(result.candidates[0].legal_name) != normalized(legal_name)
            ):
                raise ValueError("Fresh provider evidence did not prove one exact target identity")

            recovery = ProviderVerifiedRecovery(
                origin=origin,
                recovered_party_id=recovered_party_id,
                legal_name=expected.legal_name,
                registration_number=expected.registration_number,
                country_of_incorporation=expected.country_of_incorporation,
                actor_id=actor_id,
                verified_at=self._clock(),
                candidate_count=1,
            )
            candidate = GoldTierExecutionLedgerEntry(
                submission_input=submission_input.model_copy(deep=True),
                state=GoldTierExecutionLedgerState.IN_PROGRESS,
                attempted_operations=(
                    GoldTierOperationMarker.SEARCH,
                    GoldTierOperationMarker.SHELL,
                ),
                completed_operations=(GoldTierOperationMarker.SEARCH,),
                resolved_operations=(
                    GoldTierOperationMarker.SEARCH,
                    GoldTierOperationMarker.SHELL,
                ),
                provider_verified_recovery=recovery,
                search_resolution=GoldTierSearchResolution.NO_MATCH,
                resolved_party_id=recovered_party_id,
                shell_status="PROVIDER_VERIFIED_RECOVERY",
            )
            with self._execution_ledger_guard:
                try:
                    if stored is None:
                        self._target_executions.create(candidate)
                    else:
                        self._target_executions.replace(
                            candidate,
                            expected_state=GoldTierExecutionLedgerState.IN_PROGRESS.value,
                        )
                except TargetExecutionRepositoryConflictError:
                    latest = self._target_executions.get(submission_input.submission_id)
                    if latest != candidate:
                        raise RuntimeError(
                            "Provider recovery lost durable ledger ownership"
                        ) from None
            self._retain_provider_recovered_shell_on_case(
                case,
                recovered_party_id=recovered_party_id,
            )
            return candidate.model_copy(deep=True)

    def _retain_provider_recovered_shell_on_case(
        self,
        case: OnboardingCase,
        *,
        recovered_party_id: str | None,
    ) -> None:
        if recovered_party_id is None:
            raise ValueError("Provider recovery requires a retained target identity")
        result = case.goldtier_result
        if result is not None:
            if (
                result.party_id == recovered_party_id
                and result.shell_status == "PROVIDER_VERIFIED_RECOVERY"
            ):
                return
            raise ValueError("Provider recovery conflicts with the retained case target")
        case.goldtier_result = GoldTierResult(
            party_id=recovered_party_id,
            shell_status="PROVIDER_VERIFIED_RECOVERY",
        )
        self._record(
            case,
            WorkflowState.GT_SHELL_CREATED,
            EventOutcome.SUCCEEDED,
            (
                "Shell outcome remained uncertain; the target identity was subsequently "
                "recovered through exact provider verification without replay."
            ),
            "GT_SHELL_PROVIDER_VERIFIED_RECOVERY",
        )

    def recover_uncertain_policy_from_provider(
        self,
        *,
        submission_input: GoldTierSubmissionInput,
        recovered_party_id: str,
        legal_name: str,
        registration_number: str,
        country_of_incorporation: str,
        provider_policy: str,
        provider_policy_status: str,
        actor_id: str,
        origin: GoldTierRecoveryOrigin,
        reauthorize: Callable[[], None] | None = None,
    ) -> GoldTierExecutionLedgerEntry:
        """Resolve one uncertain Policy from operator-verified provider evidence."""

        if self.target_provider_mode != GoldTierProviderMode.SANDBOX:
            raise ValueError("Provider-verified recovery requires the GoldTier sandbox")
        if origin != GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER:
            raise ValueError("Policy recovery requires the retained uncertain ledger")
        with self.case_lock(submission_input.case_id):
            if reauthorize is not None:
                reauthorize()
            case = self._repository.get(submission_input.case_id)
            if case is None or case.entity is None:
                raise ValueError("Recovery requires the owning canonical case identity")
            expected = submission_input.canonical_entity

            def normalized(value: str) -> str:
                return " ".join(value.strip().split()).casefold()

            if (
                normalized(legal_name) != normalized(expected.legal_name)
                or registration_number.strip().upper()
                != expected.registration_number.strip().upper()
                or country_of_incorporation.strip().upper()
                != expected.country_of_incorporation.strip().upper()
                or case.requested_uen.strip().upper()
                != expected.registration_number.strip().upper()
                or recovered_party_id.strip()
                != (case.goldtier_result.party_id if case.goldtier_result else None)
            ):
                raise ValueError("Recovery identity does not exactly match the owning case")
            target_policy = submission_input.target_policy
            if target_policy is None or provider_policy != target_policy.policy.value:
                raise ValueError("Provider Policy evidence does not match the case policy")
            if provider_policy_status != "Requested":
                raise ValueError("Provider Policy recovery requires Requested status")

            idempotent_recovery: GoldTierExecutionLedgerEntry | None = None
            with self._execution_ledger_guard:
                stored = self._target_executions.get(submission_input.submission_id)
                if stored is None or stored.submission_input != submission_input:
                    raise ValueError("The retained uncertain Policy ledger is unavailable")
                existing = stored.provider_verified_policy_recovery
                if existing is not None:
                    if (
                        existing.recovered_party_id == recovered_party_id
                        and normalized(existing.legal_name) == normalized(legal_name)
                        and existing.registration_number.upper()
                        == registration_number.strip().upper()
                        and existing.country_of_incorporation.upper()
                        == country_of_incorporation.strip().upper()
                        and existing.origin == origin
                        and existing.provider_policy == provider_policy
                        and existing.provider_policy_status == provider_policy_status
                    ):
                        idempotent_recovery = stored.model_copy(deep=True)
                    else:
                        raise ValueError(
                            "A conflicting provider Policy recovery is already retained"
                        )
                if idempotent_recovery is None and (
                    stored.state != GoldTierExecutionLedgerState.IN_PROGRESS
                    or stored.attempted_operations
                    != (
                        GoldTierOperationMarker.SEARCH,
                        GoldTierOperationMarker.SHELL,
                        GoldTierOperationMarker.POLICY,
                    )
                    or stored.definitively_completed_operations
                    != (GoldTierOperationMarker.SEARCH,)
                    or stored.lifecycle_resolved_operations
                    != (GoldTierOperationMarker.SEARCH, GoldTierOperationMarker.SHELL)
                    or stored.provider_verified_recovery is None
                    or stored.provider_verified_recovery.operation
                    != GoldTierOperationMarker.SHELL
                    or stored.search_resolution != GoldTierSearchResolution.NO_MATCH
                    or stored.resolved_party_id != recovered_party_id
                    or stored.policy_id is not None
                    or stored.policy_status is not None
                    or GoldTierOperationMarker.AMEND in stored.attempted_operations
                ):
                    raise ValueError("Only one uncertain Policy may be provider-recovered")

            if idempotent_recovery is not None:
                self._retain_provider_recovered_policy_on_case(
                    case,
                    recovered_party_id=recovered_party_id,
                    provider_policy=provider_policy,
                    provider_policy_status=provider_policy_status,
                )
                return idempotent_recovery

            recovery = ProviderVerifiedRecovery(
                origin=origin,
                operation=GoldTierOperationMarker.POLICY,
                recovered_party_id=recovered_party_id,
                legal_name=expected.legal_name,
                registration_number=expected.registration_number,
                country_of_incorporation=expected.country_of_incorporation,
                actor_id=actor_id,
                verified_at=self._clock(),
                candidate_count=1,
                provider_policy=provider_policy,
                provider_policy_status=provider_policy_status,
            )
            candidate = GoldTierExecutionLedgerEntry(
                submission_input=stored.submission_input,
                state=GoldTierExecutionLedgerState.IN_PROGRESS,
                attempted_operations=stored.attempted_operations,
                completed_operations=stored.completed_operations,
                resolved_operations=(
                    GoldTierOperationMarker.SEARCH,
                    GoldTierOperationMarker.SHELL,
                    GoldTierOperationMarker.POLICY,
                ),
                provider_verified_recovery=stored.provider_verified_recovery,
                provider_verified_policy_recovery=recovery,
                search_resolution=stored.search_resolution,
                resolved_party_id=stored.resolved_party_id,
                shell_status=stored.shell_status,
                policy_status="PROVIDER_VERIFIED_REQUESTED",
            )
            with self._execution_ledger_guard:
                try:
                    self._target_executions.replace(
                        candidate,
                        expected_state=GoldTierExecutionLedgerState.IN_PROGRESS.value,
                    )
                except TargetExecutionRepositoryConflictError:
                    latest = self._target_executions.get(submission_input.submission_id)
                    if latest != candidate:
                        raise RuntimeError(
                            "Provider Policy recovery lost durable ledger ownership"
                        ) from None
            self._retain_provider_recovered_policy_on_case(
                case,
                recovered_party_id=recovered_party_id,
                provider_policy=provider_policy,
                provider_policy_status=provider_policy_status,
            )
            return candidate.model_copy(deep=True)

    def recover_uncertain_amend_failure_from_provider(
        self,
        *,
        submission_input: GoldTierSubmissionInput,
        recovered_party_id: str,
        provider_status: GoldTierProviderFailureStatus,
        provider_status_evidence: str,
        actor_id: str,
        origin: GoldTierRecoveryOrigin,
        reauthorize: Callable[[], None] | None = None,
    ) -> GoldTierExecutionLedgerEntry:
        """Retain provider proof that one uncertain Amend failed, without replay."""

        if self.target_provider_mode != GoldTierProviderMode.SANDBOX:
            raise ValueError("Provider-verified failure requires the GoldTier sandbox")
        if origin != GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER:
            raise ValueError("Amend failure recovery requires the retained uncertain ledger")
        with self.case_lock(submission_input.case_id):
            if reauthorize is not None:
                reauthorize()
            case = self._repository.get(submission_input.case_id)
            if (
                case is None
                or case.entity is None
                or case.goldtier_result is None
                or case.goldtier_result.party_id != recovered_party_id
            ):
                raise ValueError("Provider failure identity does not match the owning case")

            with self._execution_ledger_guard:
                stored = self._target_executions.get(submission_input.submission_id)
                if stored is None or stored.submission_input != submission_input:
                    raise ValueError("The retained uncertain Amend ledger is unavailable")
                existing = stored.provider_verified_amend_failure
                if existing is not None:
                    if (
                        existing.recovered_party_id == recovered_party_id
                        and existing.provider_status == provider_status
                        and existing.provider_status_evidence == provider_status_evidence
                        and existing.origin == origin
                    ):
                        return stored.model_copy(deep=True)
                    raise ValueError(
                        "A conflicting provider Amend failure is already retained"
                    )
                if (
                    stored.state != GoldTierExecutionLedgerState.IN_PROGRESS
                    or stored.attempted_operations
                    != (
                        GoldTierOperationMarker.SEARCH,
                        GoldTierOperationMarker.SHELL,
                        GoldTierOperationMarker.POLICY,
                        GoldTierOperationMarker.AMEND,
                    )
                    or stored.definitively_completed_operations
                    != (GoldTierOperationMarker.SEARCH,)
                    or stored.lifecycle_resolved_operations
                    != (
                        GoldTierOperationMarker.SEARCH,
                        GoldTierOperationMarker.SHELL,
                        GoldTierOperationMarker.POLICY,
                    )
                    or stored.provider_verified_recovery is None
                    or stored.provider_verified_policy_recovery is None
                    or stored.resolved_party_id != recovered_party_id
                    or stored.amend_status is not None
                ):
                    raise ValueError(
                        "Only the single retained uncertain Amend may be provider-reconciled"
                    )

                failure = ProviderVerifiedFailure(
                    origin=origin,
                    provider_status=provider_status,
                    provider_status_evidence=provider_status_evidence,
                    recovered_party_id=recovered_party_id,
                    actor_id=actor_id,
                    verified_at=self._clock(),
                )
                candidate = GoldTierExecutionLedgerEntry.model_validate(
                    {
                        **stored.model_dump(mode="python"),
                        "provider_verified_amend_failure": failure,
                    }
                )
                try:
                    self._target_executions.replace(
                        candidate,
                        expected_state=GoldTierExecutionLedgerState.IN_PROGRESS.value,
                    )
                except TargetExecutionRepositoryConflictError:
                    latest = self._target_executions.get(submission_input.submission_id)
                    if latest != candidate:
                        raise RuntimeError(
                            "Provider Amend failure lost durable ledger ownership"
                        ) from None
                return candidate.model_copy(deep=True)

    def _retain_provider_recovered_policy_on_case(
        self,
        case: OnboardingCase,
        *,
        recovered_party_id: str,
        provider_policy: str,
        provider_policy_status: str,
    ) -> None:
        result = case.goldtier_result
        if result is None or result.party_id != recovered_party_id:
            raise ValueError("Policy recovery conflicts with the retained case target")
        if result.policy_status == "PROVIDER_VERIFIED_REQUESTED":
            return
        if result.policy_status is not None or result.policy_id is not None:
            raise ValueError("Policy recovery conflicts with retained Policy progress")
        result.policy_status = "PROVIDER_VERIFIED_REQUESTED"
        self._record(
            case,
            WorkflowState.GT_POLICY_CREATED,
            EventOutcome.SUCCEEDED,
            (
                f"The {provider_policy} Policy transport outcome remained uncertain; "
                f"provider verification later confirmed one {provider_policy_status} "
                "request without replay."
            ),
            "GT_POLICY_PROVIDER_VERIFIED_RECOVERY",
        )

    def _submit_to_goldtier(
        self,
        case: OnboardingCase,
        submission_input: GoldTierSubmissionInput,
        *,
        complete_legacy_flow: bool,
    ) -> OnboardingCase:
        completed_operations = [GoldTierOperationMarker.SEARCH]
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
                self._goldtier_mapper.build_search_request(submission_input),
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

        party_id: str | None = None
        shell_status: str | None = None
        if search.outcome in {
            GoldTierSearchOutcome.MATCH_FOUND,
            GoldTierSearchOutcome.MULTIPLE_MATCHES,
        }:
            if (
                search.outcome == GoldTierSearchOutcome.MATCH_FOUND
                and len(search.candidates) == 1
                and self._entity_resolver is not None
            ):
                entity = submission_input.canonical_entity
                address = entity.registered_address
                address_text = " ".join(
                    item
                    for item in (
                        address.address_line_1,
                        address.address_line_2,
                        address.postal_code,
                        address.country_code,
                    )
                    if item
                )
                source = EntityIdentity(
                    candidate_id=submission_input.source_case_id,
                    registration_number=entity.registration_number,
                    country=entity.country_of_incorporation,
                    legal_name=entity.legal_name,
                    legal_form=entity.party_type,
                    registered_address=address_text,
                    incorporated_on=entity.registration_date,
                    source_reference=submission_input.source_case_id,
                )
                candidates = tuple(
                    EntityIdentity(
                        candidate_id=candidate.party_id,
                        registration_number=candidate.registration_number,
                        country=candidate.country,
                        legal_name=candidate.legal_name,
                        legal_form=candidate.legal_form,
                        registered_address=candidate.registered_address,
                        source_reference="GOLDTIER_XPI_SEARCH",
                    )
                    for candidate in search.candidates
                )
                resolution = self._entity_resolver.resolve_entity(
                    source=source,
                    candidates=candidates,
                    policy=case.policy_snapshot.intelligence,
                )
                if resolution.outcome == EntityResolutionOutcome.EXACT_MATCH:
                    party_id = resolution.selected_candidate_id
                    shell_status = "EXISTING_PARTY_REUSED"

            if party_id is None:
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
                    "Existing GoldTier candidate evidence was retained without a mutation.",
                )
                return self._terminate(
                    case,
                    WorkflowState.REVIEW_REQUIRED,
                    EventOutcome.REVIEW_REQUIRED,
                    "GT_EXISTING_PARTY_REVIEW_REQUIRED",
                    "An existing GoldTier party candidate requires human review.",
                )
            self._record(
                case,
                WorkflowState.GT_SEARCHED,
                EventOutcome.SUCCEEDED,
                "An exact existing GoldTier party was selected; shell creation was skipped.",
            )

        elif search.outcome == GoldTierSearchOutcome.NO_MATCH:
            self._record(
                case,
                WorkflowState.GT_SEARCHED,
                EventOutcome.SUCCEEDED,
                "GoldTier search completed; no existing party was found.",
            )
        else:
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

        if party_id is None:
            completed_operations.append(GoldTierOperationMarker.SHELL)
            self._mark_operation_attempted(submission_input, GoldTierOperationMarker.SHELL)
            untrusted_shell = self._run_required_stage(
                case,
                code="GT_SHELL_UNEXPECTED_FAILURE",
                message="GoldTier shell customer creation could not be completed.",
                on_failure=lambda code, message: self._record_target_outcome(
                    submission_input,
                    classification=GoldTierExecutionClassification.FAILED,
                    onboarding_state=WorkflowState.FAILED,
                    completed_operations=tuple(completed_operations),
                    error_code=code,
                    error_message=message,
                    infrastructure_failure=True,
                ),
                operation=lambda: self._goldtier.create_shell_customer(
                    self._goldtier_mapper.build_shell_request(submission_input),
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
                    completed_operations=tuple(completed_operations),
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
                    completed_operations=tuple(completed_operations),
                    error_code=code,
                    error_message=message,
                )
                return self._goldtier_failure(case, code, message)
            party_id = shell.party_id
            shell_status = shell.status
            self._record(
                case,
                WorkflowState.GT_SHELL_CREATED,
                EventOutcome.SUCCEEDED,
                "GoldTier shell customer created.",
            )
        if party_id is None or shell_status is None:
            raise RuntimeError("GoldTier party identity was not resolved safely")
        case.goldtier_result = GoldTierResult(
            party_id=party_id,
            shell_status=shell_status,
        )

        policy_id: str | None = None
        policy_status: str | None = None
        if shell_status != "EXISTING_PARTY_REUSED":
            completed_operations.append(GoldTierOperationMarker.POLICY)
            self._mark_operation_attempted(submission_input, GoldTierOperationMarker.POLICY)
            untrusted_policy = self._run_required_stage(
                case,
                code="GT_POLICY_UNEXPECTED_FAILURE",
                message="GoldTier policy creation could not be completed.",
                on_failure=lambda code, message: self._record_target_outcome(
                    submission_input,
                    classification=GoldTierExecutionClassification.FAILED,
                    onboarding_state=WorkflowState.FAILED,
                    completed_operations=tuple(completed_operations),
                    party_id=party_id,
                    shell_status=shell_status,
                    error_code=code,
                    error_message=message,
                    infrastructure_failure=True,
                ),
                operation=lambda: self._goldtier.create_policy(
                    self._goldtier_mapper.build_policy_request(submission_input, party_id),
                    self._metadata(
                        submission_input,
                        submission_input.idempotency.policy,
                    ),
                ),
            )
            try:
                policy = validate_policy_response(
                    untrusted_policy, expected_party_id=party_id
                )
            except InvalidTargetResponseError:
                return self._malformed_target_response(
                    case,
                    submission_input,
                    completed_operations=tuple(completed_operations),
                )
            if policy.outcome != GoldTierOutcome.SUCCESS:
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
                    completed_operations=tuple(completed_operations),
                    party_id=party_id,
                    shell_status=shell_status,
                    policy_status=policy.status,
                    error_code=code,
                    error_message=message,
                )
                case.goldtier_result.policy_status = policy.status
                return self._goldtier_failure(case, code, message)
            policy_id = policy.policy_id
            policy_status = policy.status
            case.goldtier_result.policy_id = policy_id
            case.goldtier_result.policy_status = policy_status
            self._record(
                case,
                WorkflowState.GT_POLICY_CREATED,
                EventOutcome.SUCCEEDED,
                "GoldTier customer policy created.",
            )

        completed_operations.append(GoldTierOperationMarker.AMEND)
        self._mark_operation_attempted(submission_input, GoldTierOperationMarker.AMEND)
        untrusted_amend = self._run_required_stage(
            case,
            code="GT_AMEND_UNEXPECTED_FAILURE",
            message="GoldTier party enrichment could not be completed.",
            on_failure=lambda code, message: self._record_target_outcome(
                submission_input,
                classification=GoldTierExecutionClassification.FAILED,
                onboarding_state=WorkflowState.FAILED,
                completed_operations=tuple(completed_operations),
                party_id=party_id,
                shell_status=shell_status,
                policy_id=policy_id,
                policy_status=policy_status,
                error_code=code,
                error_message=message,
                infrastructure_failure=True,
            ),
            operation=lambda: self._goldtier.amend_party(
                party_id,
                self._goldtier_mapper.build_amend_request(submission_input, party_id),
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
                completed_operations=tuple(completed_operations),
            )
        if amend.outcome == GoldTierOutcome.PARTIAL_SUCCESS:
            code = _project_target_error_code(
                amend.error_code,
                allowed=frozenset({"GT_OPTIONAL_SECTION_REVIEW"}),
                fallback="GT_PARTIAL_SUCCESS",
            )
            message = "Human review required for the partial GoldTier amendment."
            self._record_target_outcome(
                submission_input,
                classification=GoldTierExecutionClassification.REVIEW_REQUIRED,
                onboarding_state=WorkflowState.REVIEW_REQUIRED,
                completed_operations=tuple(completed_operations),
                party_id=party_id,
                shell_status=shell_status,
                policy_id=policy_id,
                policy_status=policy_status,
                amend_status=amend.status,
                error_code=code,
                error_message=message,
            )
            case.goldtier_result.amend_status = amend.status
            self._record(
                case,
                WorkflowState.GT_ENRICHED,
                EventOutcome.PARTIAL,
                "GoldTier amendment completed partially.",
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
                completed_operations=tuple(completed_operations),
                party_id=party_id,
                shell_status=shell_status,
                policy_id=policy_id,
                policy_status=policy_status,
                amend_status=amend.status,
                error_code=code,
                error_message=message,
            )
            case.goldtier_result.amend_status = amend.status
            return self._goldtier_failure(case, code, message)
        readback_party_id: str | None = None
        readback_status: str | None = None
        if submission_input.provider_mode == GoldTierProviderMode.SANDBOX:
            completed_operations.append(GoldTierOperationMarker.READBACK)
            self._mark_operation_attempted(submission_input, GoldTierOperationMarker.READBACK)
            untrusted_readback = self._run_required_stage(
                case,
                code="GT_READBACK_UNEXPECTED_FAILURE",
                message="GoldTier customer read-back could not be completed.",
                on_failure=lambda code, message: self._record_target_outcome(
                    submission_input,
                    classification=GoldTierExecutionClassification.FAILED,
                    onboarding_state=WorkflowState.FAILED,
                    completed_operations=tuple(completed_operations),
                    party_id=party_id,
                    shell_status=shell_status,
                    policy_id=policy_id,
                    policy_status=policy_status,
                    amend_status=amend.status,
                    error_code=code,
                    error_message=message,
                    infrastructure_failure=True,
                ),
                operation=lambda: self._goldtier.search_party(
                    self._goldtier_mapper.build_readback_request(
                        submission_input, party_id
                    ),
                    self._metadata(
                        submission_input,
                        submission_input.idempotency.amend,
                    ),
                ),
            )
            try:
                readback = validate_search_response(untrusted_readback)
            except InvalidTargetResponseError:
                return self._malformed_target_response(
                    case,
                    submission_input,
                    completed_operations=tuple(completed_operations),
                )
            verified = (
                readback.outcome == GoldTierSearchOutcome.MATCH_FOUND
                and len(readback.candidates) == 1
                and readback.matched_party_id == party_id
                and readback.candidates[0].party_id == party_id
            )
            if not verified:
                code = "GT_READBACK_IDENTITY_REVIEW_REQUIRED"
                message = "GoldTier read-back did not prove the retained customer identity."
                self._record_target_outcome(
                    submission_input,
                    classification=GoldTierExecutionClassification.REVIEW_REQUIRED,
                    onboarding_state=WorkflowState.REVIEW_REQUIRED,
                    completed_operations=tuple(completed_operations),
                    party_id=party_id,
                    shell_status=shell_status,
                    policy_id=policy_id,
                    policy_status=policy_status,
                    amend_status=amend.status,
                    error_code=code,
                    error_message=message,
                )
                case.goldtier_result.amend_status = amend.status
                return self._terminate(
                    case,
                    WorkflowState.REVIEW_REQUIRED,
                    EventOutcome.REVIEW_REQUIRED,
                    code,
                    message,
                )
            readback_party_id = party_id
            readback_status = "VERIFIED"
        self._record_target_outcome(
            submission_input,
            classification=GoldTierExecutionClassification.SUCCESS,
            onboarding_state=(
                WorkflowState.COMPLETED if complete_legacy_flow else WorkflowState.GT_ENRICHED
            ),
            completed_operations=tuple(completed_operations),
            party_id=party_id,
            shell_status=shell_status,
            policy_id=policy_id,
            policy_status=policy_status,
            amend_status=amend.status,
            readback_party_id=readback_party_id,
            readback_status=readback_status,
        )
        case.goldtier_result.amend_status = amend.status
        case.goldtier_result.readback_party_id = readback_party_id
        case.goldtier_result.readback_status = readback_status
        self._record(
            case,
            WorkflowState.GT_ENRICHED,
            EventOutcome.SUCCEEDED,
            "GoldTier party enriched.",
        )
        if complete_legacy_flow:
            self._record(
                case,
                WorkflowState.COMPLETED,
                EventOutcome.SUCCEEDED,
                "Required onboarding stages completed with GoldTier.",
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
        except RegistryCacheError as exc:
            if on_failure is not None:
                on_failure(exc.code, exc.public_message)
            self._raise_terminal_infrastructure(
                case,
                code=exc.code,
                message=exc.public_message,
            )
        except MutationOutcomeUncertainError:
            raise
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
        *,
        create: bool = False,
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
        if create:
            self._repository.create(case)
        else:
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
