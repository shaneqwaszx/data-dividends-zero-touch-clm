"""Synchronous onboarding across configured ACRA and Mock GoldTier boundaries."""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from threading import Lock, RLock
from typing import Literal, Never, Protocol, TypeVar, cast
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.connectors.acra import AcraConnector
from app.connectors.errors import (
    ConnectorError,
    MutationOutcomeUncertainError,
    MutationUncertaintyReason,
    public_connector_error,
)
from app.connectors.goldtier import GoldTierConnector, GoldTierRequestMapper
from app.connectors.goldtier_models import (
    GoldTierOutcome,
    GoldTierRequestMetadata,
    GoldTierSearchCandidate,
    GoldTierSearchOutcome,
    GoldTierSearchResult,
    SearchPartyRequest,
)
from app.connectors.goldtier_xpi import observed_goldtier_xpi_search_status
from app.connectors.goldtier_xpi_models import XpiCustomerSearchRequest
from app.connectors.registry import (
    AcraIdentifierNotEligibleError,
    AcraRegistryProviderAdapter,
    BusinessProfileEvidenceProvider,
    RegistryProvider,
    RegistryProviderRouter,
    ShareholderEvidenceProvider,
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
    IDENTITY_RECHECK_HISTORY_LIMIT,
    STATUTE_MATCH_RULE,
    EventOutcome,
    ExistingTargetStateProvenance,
    GoldTierResult,
    GovernmentBodyType,
    GovernmentStatusConfirmation,
    IdentityCorrectionEvidence,
    InitialCustomerIdentity,
    InitialGoldTierSearchAttempt,
    InitialGoldTierSearchEvidence,
    OnboardingCase,
    RegistryAcquisitionBundle,
    RegistryAcquisitionStatus,
    RegistryEvidenceBinding,
    RegistryEvidenceDisposition,
    RegistryOperationStatus,
    SafeError,
    TargetDispatchConfirmation,
    WorkflowEvent,
    WorkflowState,
)
from app.domain.onboarding_intelligence import (
    EntityIdentity,
    EntityResolutionOutcome,
    EntityResolutionResult,
    FeatureAssessment,
)
from app.domain.policy import (
    GOLDTIER_BOOKING_ENTITY_POC_VALUE,
    GOLDTIER_CLIENT_SEGMENT_VALUES,
    GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM_POC_VALUE,
    GOLDTIER_KYC_CUSTOMER_TYPE_VALUES,
    GOLDTIER_POLICY_POC_VALUE,
    GOLDTIER_REGISTRATION_TYPE_POC_VALUE,
    AuthorityLabelledTargetValue,
    CasePolicyRebindAudit,
    CasePolicySnapshot,
    GoldTierTargetPolicySnapshot,
    IntelligencePolicySnapshot,
    PolicyAuthority,
    RegistryPolicySnapshot,
    legacy_phase13_policy_snapshot,
)
from app.domain.reconciliation import ReconciliationField
from app.domain.target_classification import (
    TargetClassificationAssessment,
    TargetClassificationKey,
    TargetClassificationSelection,
    bounded_classification_compatible,
    classification_incompatibility_message,
)
from app.domain.target_identity_evidence import TargetIdentityEvidencePolicy
from app.domain.target_preparation import GoldTierRequestPreview
from app.domain.target_submission import (
    WORKFLOW_DISPATCH_WRITE_OPERATIONS,
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
from app.domain.uen_route import UenRoute, UenRouteDecision, route_change_message, route_uen
from app.domain.workflow_governance import (
    CASE_EVENT_APPLICABILITY_BASIS_CONFLICT,
    CASE_EVENT_APPLICABILITY_ESCALATED,
)
from app.mappers.goldtier import MockGoldTierRequestMapper
from app.services.canonical_validation import validate_entity
from app.services.dispatch_fence import DispatchFence, default_memory_fence
from app.services.errors import (
    DispatchFenceRefusedError,
    OnboardingInfrastructureError,
    TargetProviderContextMismatchError,
    TargetRegistryProvenanceError,
    TargetWritesDisabledError,
)
from app.services.registry_acquisition import (
    RegistryAcquisitionBusyError,
    RegistryAcquisitionCoordinator,
    RegistryCacheError,
    SubsidiaryBusinessProfileEvidence,
    SubsidiaryRegistryEvidence,
    SubsidiaryShareholderEvidence,
)
from app.services.repository import OnboardingCaseRepository
from app.services.target_execution_repository import (
    InMemoryTargetExecutionRepository,
    TargetExecutionRepository,
    TargetExecutionRepositoryConflictError,
    has_write_marker,
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
    "REGISTRY_PROVENANCE_UNSUPPORTED": (
        "REGISTRY_PROVENANCE_UNSUPPORTED",
        409,
        TargetRegistryProvenanceError.public_message,
    ),
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


@dataclass(frozen=True)
class TargetStatusCheckEvidence:
    """Read-only customer evidence; never proof of Policy or submission completion."""

    submission_id: UUID
    checked_at: datetime
    result: Literal[
        "NO_MATCH", "IDENTITY_UNVERIFIED", "CUSTOMER_IDENTITY_VERIFIED",
        "AMBIGUOUS", "CHECK_FAILED",
    ]
    verified_party_id: str | None = None


@dataclass(frozen=True)
class CompletedTargetVerificationEvidence:
    """Ephemeral exact-ID observation; retained submission facts never change."""

    submission_id: UUID
    goldtier_id: str
    checked_at: datetime
    result: Literal["VERIFIED", "REQUIRES_REVIEW", "UNAVAILABLE"]
    legal_name: str | None = None
    registration_number: str | None = None
    country: str | None = None


MALFORMED_TARGET_RESPONSE_CODE = "GT_MALFORMED_TARGET_RESPONSE"
MALFORMED_TARGET_RESPONSE_MESSAGE = "GoldTier target returned an invalid response."
TARGET_OUTCOME_FALLBACK_CODE = "GT_TARGET_OUTCOME_RECORDING_FAILED"
TARGET_OUTCOME_FALLBACK_MESSAGE = "GoldTier target outcome recording failed safely."
# D-114 RM guidance for the registry the UEN routes to.
GOVERNMENT_IDENTITY_NOT_FOUND_MESSAGE = (
    "No current government register record was found for this UEN. Check the UEN against "
    "the authority's letter."
)
ENTITY_CATEGORY_MISMATCH_MESSAGE = (
    "This UEN has a government body record in the government register, but its format routes "
    "it to ACRA. Check the UEN; the case stays in review."
)


def uen_entity_type_unsupported_message(route: UenRouteDecision) -> str:
    return (
        "This UEN belongs to an entity type this POC doesn't onboard "
        f"({route.entity_type}). Check the UEN."
    )


class _TargetOutcomeFallbackRecorded(Exception):
    """Internal signal that a constant-only failure outcome replaced rich facts."""


def _readback_identity_matches(
    submission: GoldTierSubmissionInput, readback: GoldTierSearchResult, party_id: str
) -> bool:
    """Compare every projected identity field; Search cannot prove Policy or KYC."""
    if not (
        readback.outcome == GoldTierSearchOutcome.MATCH_FOUND
        and len(readback.candidates) == 1
        and readback.matched_party_id == party_id
        and readback.candidates[0].party_id == party_id
    ):
        return False
    candidate = readback.candidates[0]
    entity = submission.canonical_entity
    address = entity.registered_address
    expected_address = ", ".join(
        item
        for item in (
            address.address_line_1,
            address.address_line_2,
            address.postal_code,
            address.country_code,
        )
        if item
    )
    comparisons = (
        (candidate.legal_name, entity.legal_name),
        (candidate.registration_number, entity.registration_number),
        (candidate.country, entity.country_of_incorporation),
        (candidate.legal_form, entity.party_type),
        (candidate.registered_address, expected_address),
    )
    return all(
        returned is None
        or " ".join(returned.split()).casefold() == " ".join(expected.split()).casefold()
        for returned, expected in comparisons
    )


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


def _validate_sg_policy_rebind_identity(case: OnboardingCase) -> None:
    requested = case.requested_uen.strip().upper()
    if not is_eligible_singapore_uen(requested):
        raise ValueError("Case is not eligible for the Singapore policy rebind")
    if case.initial_identity is not None and (
        case.initial_identity.registration_number.strip().upper() != requested
        or case.initial_identity.country_of_incorporation.strip().upper()
        != JurisdictionCode.SINGAPORE.value
    ):
        raise ValueError("Initial identity does not match the Singapore case UEN")
    if case.entity is not None and (
        case.entity.registration_number.strip().upper() != requested
        or (case.entity.country_of_incorporation or "").strip().upper()
        != JurisdictionCode.SINGAPORE.value
    ):
        raise ValueError("Canonical identity does not match the Singapore case UEN")
    if case.initial_identity is None and case.entity is None:
        raise ValueError("Case has no canonical or initial Singapore identity")


def _validated_current_sg_target_policy(
    snapshot: CasePolicySnapshot,
) -> GoldTierTargetPolicySnapshot:
    target = snapshot.goldtier_target
    expected = {
        "customer_external_system": (
            GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM_POC_VALUE,
            PolicyAuthority.SPONSOR_DOCUMENTED,
        ),
        "registration_type": (
            GOLDTIER_REGISTRATION_TYPE_POC_VALUE,
            PolicyAuthority.USER_AUTHORIZED_POC,
        ),
        "policy": (GOLDTIER_POLICY_POC_VALUE, PolicyAuthority.SPONSOR_DOCUMENTED),
        "booking_entity": (
            GOLDTIER_BOOKING_ENTITY_POC_VALUE,
            PolicyAuthority.USER_AUTHORIZED_POC,
        ),
    }
    if target is None or snapshot.catalogue_version < 1:
        raise ValueError("Current catalogue has no accepted SG target policy")
    if any(
        getattr(target, field).value != value or getattr(target, field).authority != authority
        for field, (value, authority) in expected.items()
    ):
        raise ValueError("Current catalogue contradicts the accepted SG target policy")
    return target


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
        target_identity_policy: TargetIdentityEvidencePolicy | None = None,
    ) -> None:
        self._target_identity_policy = target_identity_policy
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
        self._active_target_submissions: set[UUID] = set()
        self._target_executions = target_execution_repository or InMemoryTargetExecutionRepository()
        # ADR-017: the dispatch fence is the only path to a first GoldTier write.
        self._dispatch_fence: DispatchFence | None = None
        # ADR-018 §3.5 F1/F5: the workflow owner's basis hook, called after a committed
        # registry binding write under the case lock. Unset: nothing is frozen (UNVERIFIED).
        self._registry_binding_hook: Callable[[UUID], str] | None = None
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

    @property
    def search_follows_registry(self) -> bool:
        """Read-only: True when the GoldTier Search waits for the accepted registry identity.

        With a target identity policy (staging Sandbox) the typed name is never sent and
        Search runs after ACRA; without one, case creation searches first (ADR-006).
        """
        return self._target_identity_policy is not None

    @property
    def target_writes_enabled(self) -> bool:
        """False only for a target that refuses mutations; Search stays available."""
        return bool(getattr(self._goldtier, "writes_enabled", True))

    def target_read_budget_usage(self, now: datetime) -> tuple[int | None, int | None]:
        """ST-7: (daily read limit, reads used today); (None, None) when reads are not counted."""
        budget = getattr(self._goldtier, "read_budget", None)
        if budget is None or budget.limit is None:
            return None, None
        try:
            return budget.limit, budget.used(now)
        except Exception:
            return budget.limit, None

    def target_writes_permitted(
        self, source_case_id: str, operation: str | None = None
    ) -> bool:
        """D-137: the write window admits this case (and operation), not just some case."""
        if not self.target_writes_enabled:
            return False
        permits = getattr(self._goldtier, "writes_permitted", None)
        return permits is None or bool(
            permits(source_case_id=source_case_id, operation=operation)
        )

    def _require_target_writes(
        self,
        submission_input: GoldTierSubmissionInput | None = None,
        operation: str | None = None,
    ) -> None:
        """Stop before the ledger marks an attempt, so a refused write burns nothing."""
        if not self.target_writes_enabled:
            raise TargetWritesDisabledError
        if submission_input is not None and not self.target_writes_permitted(
            submission_input.source_case_id, operation
        ):
            raise TargetWritesDisabledError

    def _holds_accepted_identity(self, case: OnboardingCase) -> bool:
        """The canonical identity must still be what the accepted source itself returned."""
        policy = self._target_identity_policy
        if policy is None:
            return True
        entity = case.entity
        acquired = (
            case.registry_acquisition.entity_profile
            if case.registry_acquisition is not None
            else None
        )
        return (
            entity is not None
            and acquired is not None
            and policy.accepts(entity)
            and policy.accepts(acquired)
            and entity.legal_name == acquired.legal_name
            and entity.registration_number == acquired.registration_number
            and entity.country_of_incorporation == acquired.country_of_incorporation
        )

    def target_registry_evidence_refused(self, case: OnboardingCase) -> bool:
        """True when this case holds identity evidence the target does not accept."""
        return case.entity is not None and not self._holds_accepted_identity(case)

    def _require_target_registry_provenance(self, case: OnboardingCase) -> None:
        """Where a policy applies, nothing reaches the target without accepted evidence."""
        if not self._holds_accepted_identity(case):
            raise TargetRegistryProvenanceError


    def _find_verified_target_case(
        self,
        *,
        registration_number: str,
        legal_name: str,
        country_of_incorporation: str,
        party_id: str,
        candidate: GoldTierSearchCandidate | None = None,
    ) -> OnboardingCase | None:
        """Keep target reuse subordinate to the existing case and its finalized ledger (D-137)."""
        prior = self._repository.find_verified_target_case(
            registration_number=registration_number,
            legal_name=legal_name,
            country_of_incorporation=country_of_incorporation,
            party_id=party_id,
        )
        if (
            prior is not None
            and self._target_identity_policy is not None
            and not self._holds_accepted_identity(prior)
        ):
            return None
        if prior is None:
            return None
        if (
            prior.state not in {WorkflowState.GT_ENRICHED, WorkflowState.COMPLETED}
            or prior.goldtier_result is None
            or prior.goldtier_result.readback_status != "VERIFIED"
        ):
            return None
        for entry in self._target_executions.list_for_case(prior.case_id):
            outcome = entry.target_outcome
            if (
                entry.state == GoldTierExecutionLedgerState.FINALIZED
                and entry.submission_input.provider_mode == self.target_provider_mode
                and entry.receipt is not None
                and entry.receipt.classification == GoldTierExecutionClassification.SUCCESS
                and entry.receipt.result is not None
                and entry.receipt.result.party_id == party_id
                and entry.receipt.result.readback_party_id == party_id
                and entry.receipt.result.readback_status == "VERIFIED"
                and outcome is not None
                and outcome.classification == GoldTierExecutionClassification.SUCCESS
                and outcome.party_id == party_id
                and outcome.readback_party_id == party_id
                and outcome.readback_status == "VERIFIED"
                and GoldTierOperationMarker.READBACK in entry.definitively_completed_operations
                and GoldTierOperationMarker.AMEND in entry.definitively_completed_operations
                and entry.amend_status == "ENRICHED"
                # Finalized labels alone do not bind proof to this immutable submission.
                and entry.submission_input.case_id == prior.case_id
                and entry.receipt.case_id == entry.submission_input.case_id
                and entry.receipt.submission_id == entry.submission_input.submission_id
                and entry.receipt.correlation_id == entry.submission_input.correlation_id
                and outcome.case_id == entry.submission_input.case_id
                and outcome.submission_id == entry.submission_input.submission_id
                and outcome.correlation_id == entry.submission_input.correlation_id
                and entry.receipt.input_fingerprint
                == _submission_fingerprint(entry.submission_input)
                == outcome.input_fingerprint
                and outcome.idempotency_fingerprint
                == _idempotency_fingerprint(entry.submission_input)
                and entry.resolved_party_id == party_id
                and entry.readback_party_id == party_id
                and entry.readback_status == "VERIFIED"
                and entry.shell_status == outcome.shell_status
                and entry.policy_id == outcome.policy_id
                and entry.policy_status == outcome.policy_status
                and entry.amend_status == outcome.amend_status
                and entry.receipt.onboarding_state == outcome.onboarding_state
                and entry.receipt.error is None
                and not entry.receipt.infrastructure_failure
                and entry.receipt.result.shell_status == outcome.shell_status
                and entry.receipt.result.policy_id == outcome.policy_id
                and entry.receipt.result.policy_status == outcome.policy_status
                and entry.receipt.result.amend_status == outcome.amend_status
                and prior.goldtier_result.model_dump() == entry.receipt.result.model_dump()
                and " ".join(entry.submission_input.canonical_entity.legal_name.split()).casefold()
                == " ".join(legal_name.split()).casefold()
                and entry.submission_input.canonical_entity.registration_number.upper()
                == registration_number.upper()
                and entry.submission_input.canonical_entity.country_of_incorporation.upper()
                == country_of_incorporation.upper()
                and (
                    candidate is None
                    or _readback_identity_matches(
                        entry.submission_input,
                        GoldTierSearchResult(
                            outcome=GoldTierSearchOutcome.MATCH_FOUND,
                            status_code=200,
                            matched_party_id=party_id,
                            candidates=(candidate,),
                            message="Current local provider identity.",
                        ),
                        party_id,
                    )
                )
            ):
                return prior
        return None

    def _mock_reuse_is_verified(
        self,
        submission_input: GoldTierSubmissionInput,
        party_id: str,
        candidate: GoldTierSearchCandidate | None = None,
    ) -> bool:
        if submission_input.provider_mode != GoldTierProviderMode.MOCK:
            return True
        entity = submission_input.canonical_entity
        prior = self._find_verified_target_case(
            registration_number=entity.registration_number,
            legal_name=entity.legal_name,
            country_of_incorporation=entity.country_of_incorporation,
            party_id=party_id,
            candidate=candidate,
        )
        return prior is not None and prior.case_id != submission_input.case_id

    def confirm_target_dispatch(
        self,
        *,
        case_id: UUID,
        actor_id: str,
        expected_case_event_count: int,
        clm_version: int | None,
        destination: Literal["GOLDTIER_MOCK", "GOLDTIER_XPI_SANDBOX"],
        warnings: tuple[str, ...] = (),
        reauthorize: Callable[[], None] | None = None,
    ) -> OnboardingCase:
        """Durably confirm one frozen local-POC review before target mutation."""

        with self.case_lock(case_id):
            if reauthorize is not None:
                reauthorize()
            case = self._repository.get(case_id)
            if case is None:
                raise ValueError("Onboarding case was not found")
            expected_destination = self._target_destination(self.target_provider_mode)
            if destination != expected_destination:
                raise ValueError("Target destination does not match the configured provider")
            if case.state != WorkflowState.VALIDATED or case.entity is None:
                raise ValueError("Onboarding case is not ready for target confirmation")
            preview = self.build_request_preview(case, provider_mode=self.target_provider_mode)
            if not preview.dispatch_ready:
                raise ValueError("Required GoldTier target enrichment is unavailable.")

            digest = self._target_review_digest(case, preview)
            existing = case.target_dispatch_confirmation
            if (
                existing is not None
                and existing.actor_id == actor_id
                and existing.clm_version == clm_version
                and existing.destination == destination
                and existing.warnings == warnings
                and existing.review_digest == digest
                and existing.case_event_count == expected_case_event_count
            ):
                return case.model_copy(deep=True)
            if len(case.events) != expected_case_event_count:
                raise ValueError("Onboarding case changed before target confirmation")

            timestamp = self._clock()
            updated = case.model_copy(deep=True)
            updated.target_dispatch_confirmation = TargetDispatchConfirmation(
                confirmation_id=self._uuid_factory(),
                actor_id=actor_id,
                confirmed_at=timestamp,
                case_event_count=expected_case_event_count,
                clm_version=clm_version,
                destination=destination,
                warnings=warnings,
                review_digest=digest,
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
                    code="TARGET_DISPATCH_CONFIRMED",
                    message=(
                        "A local-POC operator confirmed the frozen target review; "
                        "this is not approval."
                    ),
                )
            )
            validated = OnboardingCase.model_validate(updated)
            self._repository.save(validated)
            return validated.model_copy(deep=True)

    def invalidate_target_dispatch_confirmation(
        self, *, case_id: UUID, expected_case_event_count: int,
    ) -> OnboardingCase:
        """Invalidate pre-submission review after accepted evidence revision.

        The workflow caller owns evidence authorization and submission freeze checks;
        this canonical owner additionally rejects any retained target attempt/result.
        """
        with self.case_lock(case_id):
            case = self.get_case(case_id)
            if case is None or len(case.events) != expected_case_event_count:
                raise ValueError("The onboarding case changed before evidence revision.")
            if case.goldtier_result is not None or self._target_executions.list_for_case(case_id):
                raise ValueError("Submitted target evidence cannot be revised.")
            updated = case.model_copy(deep=True)
            updated.target_dispatch_confirmation = None
            now = self._clock()
            updated.updated_at = now
            updated.events.append(
                WorkflowEvent(
                    sequence=len(updated.events) + 1,
                    stage=updated.state,
                    outcome=EventOutcome.SUCCEEDED,
                    timestamp=now,
                    case_id=updated.case_id,
                    correlation_id=updated.correlation_id,
                    code="OWNERSHIP_EVIDENCE_REVISED",
                    message="Reviewed ownership evidence changed; final review is required.",
                )
            )
            self._repository.save(OnboardingCase.model_validate(updated.model_dump()))
            return updated.model_copy(deep=True)

    def confirm_government_status(
        self,
        *,
        case_id: UUID,
        actor_id: str,
        expected_case_event_count: int,
        document_id: UUID,
        document_event_count: int,
        evidence_fingerprint: str,
        founding_statute: str,
        government_body_type: GovernmentBodyType,
        statute_section: str | None = None,
    ) -> OnboardingCase:
        """D-101: retain one RM Government-status confirmation; the caller owns evidence.

        D-125: the caller has already matched the founding statute to the document.
        """

        with self.case_lock(case_id):
            case = self.get_case(case_id)
            if case is None or len(case.events) != expected_case_event_count:
                raise ValueError("The onboarding case changed before Government confirmation.")
            if case.goldtier_result is not None or self._target_executions.list_for_case(case_id):
                raise ValueError("Submitted target evidence cannot be revised.")
            timestamp = self._clock()
            updated = case.model_copy(deep=True)
            updated.government_status_confirmation = GovernmentStatusConfirmation(
                confirmation_id=self._uuid_factory(),
                actor_id=actor_id,
                confirmed_at=timestamp,
                case_event_count=expected_case_event_count,
                document_id=document_id,
                document_event_count=document_event_count,
                evidence_fingerprint=evidence_fingerprint,
                founding_statute=founding_statute,
                statute_section=statute_section,
                government_body_type=government_body_type,
                statute_match=STATUTE_MATCH_RULE,
            )
            basis = founding_statute if statute_section is None else (
                f"{founding_statute}, {statute_section}"
            )
            updated.target_dispatch_confirmation = None
            updated.updated_at = timestamp
            updated.events.append(
                WorkflowEvent(
                    sequence=len(updated.events) + 1,
                    stage=updated.state,
                    outcome=EventOutcome.SUCCEEDED,
                    timestamp=timestamp,
                    case_id=updated.case_id,
                    correlation_id=updated.correlation_id,
                    code="GOVERNMENT_STATUS_CONFIRMED",
                    message=(
                        "The RM confirmed Government status from a reviewed document, "
                        f"founded under {basis}; this is not approval."
                    ),
                )
            )
            validated = OnboardingCase.model_validate(updated)
            self._repository.save(validated)
            return validated.model_copy(deep=True)

    def has_valid_target_dispatch_confirmation(
        self, case: OnboardingCase, *, clm_version: int | None = None
    ) -> bool:
        confirmation = case.target_dispatch_confirmation
        try:
            preview = self.build_request_preview(
                case,
                provider_mode=self.target_provider_mode,
            )
        except ValueError:
            return False
        return bool(
            confirmation is not None
            and confirmation.destination == self._target_destination(self.target_provider_mode)
            and (clm_version is None or confirmation.clm_version == clm_version)
            and confirmation.review_digest == self._target_review_digest(case, preview)
        )

    @staticmethod
    def _target_destination(
        provider_mode: GoldTierProviderMode,
    ) -> Literal["GOLDTIER_MOCK", "GOLDTIER_XPI_SANDBOX"]:
        return (
            "GOLDTIER_XPI_SANDBOX"
            if provider_mode == GoldTierProviderMode.SANDBOX
            else "GOLDTIER_MOCK"
        )

    @staticmethod
    def _target_review_digest(
        case: OnboardingCase,
        preview: GoldTierRequestPreview,
    ) -> str:
        material_preview = {
            "environment": preview.environment,
            "policy_version": preview.policy_version,
            "dispatch_ready": preview.dispatch_ready,
            "operations": [
                {
                    "operation": operation.operation,
                    "missing_fields": operation.missing_fields,
                    "validation": operation.validation.value,
                    "fields": [field.model_dump(mode="json") for field in operation.fields],
                }
                for operation in preview.operations
            ],
        }
        frozen_review = {
            "case_id": str(case.case_id),
            "source_case_id": case.source_case_id,
            "requested_uen": case.requested_uen,
            "initial_identity": (
                case.initial_identity.model_dump(mode="json")
                if case.initial_identity is not None
                else None
            ),
            "initial_target_search": (
                case.initial_target_search.model_dump(mode="json")
                if case.initial_target_search is not None
                else None
            ),
            "existing_target_state": (
                case.existing_target_state.model_dump(mode="json")
                if case.existing_target_state is not None
                else None
            ),
            "policy_snapshot": case.policy_snapshot.model_dump(mode="json"),
            "entity": case.entity.model_dump(mode="json") if case.entity is not None else None,
            "registry_acquisition": (
                case.registry_acquisition.model_dump(mode="json")
                if case.registry_acquisition is not None
                else None
            ),
            "registry_evidence_binding": (
                case.registry_evidence_binding.model_dump(mode="json")
                if case.registry_evidence_binding is not None
                else None
            ),
            "target_request_preview": material_preview,
        }
        return sha256(
            json.dumps(frozen_review, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def repair_initial_identity_and_recheck(
        self,
        *,
        case_id: UUID,
        actor_id: str,
        legal_name: str,
        registration_number: str,
        country_of_incorporation: str,
        expected_case_event_count: int,
        verify_registry: bool = False,
        identity_choice: Literal["ENTERED", "DOCUMENT", "OTHER"] = "OTHER",
        source_document_id: UUID | None = None,
        source_document_event_count: int | None = None,
        reauthorize: Callable[[], None] | None = None,
    ) -> OnboardingCase:
        """Correct pre-submission identity and run one durable read-only Search recheck."""

        identity = InitialCustomerIdentity(
            legal_name=" ".join(legal_name.strip().split()),
            registration_number=registration_number.strip().upper(),
            country_of_incorporation=country_of_incorporation.strip().upper(),
        )
        if (
            identity.country_of_incorporation != JurisdictionCode.SINGAPORE.value
            or not is_eligible_singapore_uen(identity.registration_number)
        ):
            raise ValueError("Corrected identity is not eligible for the Singapore route")
        with self.case_lock(case_id):
            if reauthorize is not None:
                reauthorize()
            case = self._repository.get(case_id)
            if case is None:
                raise ValueError("Onboarding case was not found")
            previous_search = case.initial_target_search
            previous_identity = case.initial_identity
            if (
                previous_identity is None
                and case.entity is not None
                and case.entity.legal_name is not None
            ):
                previous_identity = InitialCustomerIdentity(
                    legal_name=case.entity.legal_name,
                    registration_number=case.entity.registration_number,
                    country_of_incorporation=case.entity.country_of_incorporation or "",
                )
            missing_identity_repair = bool(
                previous_search is None
                and case.initial_identity is None
                and case.error is not None
                and case.error.code == "INITIAL_IDENTITY_INCOMPLETE"
            )
            if (
                not missing_identity_repair
                and not verify_registry
                and (
                    previous_identity is None
                    or (
                        previous_search is not None
                        and previous_search.disposition
                        not in {"FAILED", "REVIEW_REQUIRED", "NO_MATCH", "EXACT_MATCH"}
                    )
                )
            ):
                raise ValueError("Identity is not editable in the current pre-submission state")
            if len(case.events) != expected_case_event_count:
                raise ValueError("Onboarding case changed before identity repair")
            if case.target_dispatch_confirmation is not None or case.goldtier_result is not None:
                raise ValueError("Target execution state is already frozen")

            if len(case.initial_target_search_attempts) >= IDENTITY_RECHECK_HISTORY_LIMIT or (
                (verify_registry or previous_identity != identity)
                and len(case.identity_corrections) >= IDENTITY_RECHECK_HISTORY_LIMIT
            ):
                raise ValueError(
                    "Identity recheck history is full; no further correction can be retained."
                )

            verified: tuple[RegistryAcquisitionBundle, RegistryEvidenceBinding | None] | None = None
            if verify_registry:
                verified = self._verify_registry_correction(
                    identity, case_policy=case.policy_snapshot
                )
                identity = InitialCustomerIdentity(
                    legal_name=verified[0].entity_profile.legal_name or identity.legal_name,
                    registration_number=verified[0].entity_profile.registration_number,
                    country_of_incorporation="SG",
                )

            changed_identity = previous_identity != identity
            request_id = self._uuid_factory()
            requested_at = self._clock()
            requested = case.model_copy(deep=True)
            if changed_identity or verify_registry:
                requested.identity_corrections = (
                    *requested.identity_corrections,
                    IdentityCorrectionEvidence(
                        correction_id=self._uuid_factory(),
                        actor_id=actor_id,
                        previous_identity=previous_identity,
                        previous_entity=case.entity,
                        previous_registry_acquisition=case.registry_acquisition,
                        choice=identity_choice,
                        source_document_id=source_document_id,
                        source_document_event_count=source_document_event_count,
                        corrected_identity=identity,
                        previous_search_request_id=(
                            previous_search.request_id if previous_search is not None else None
                        ),
                        corrected_at=requested_at,
                    ),
                )
            requested.initial_identity = identity
            requested.requested_uen = identity.registration_number
            requested.existing_target_state = None
            requested.target_dispatch_confirmation = None
            requested.goldtier_result = None
            if changed_identity or verify_registry:
                requested.entity = None
                requested.registry_acquisition = None
                requested.registry_evidence_binding = None
                requested.registry_route = None
            requested.initial_target_search_attempts = (
                *requested.initial_target_search_attempts,
                InitialGoldTierSearchAttempt(
                    request_id=request_id,
                    actor_id=actor_id,
                    identity=identity,
                    status="REQUESTED",
                    requested_at=requested_at,
                ),
            )
            requested.updated_at = requested_at
            previous_route = case.uen_route or (
                route_uen(previous_identity.registration_number)
                if previous_identity is not None
                else None
            )
            corrected_route = route_uen(identity.registration_number)
            # D-114: the recorded route always describes the corrected UEN, even when the
            # registry is not re-read after this correction (QG F2).
            requested.uen_route = corrected_route
            if (
                previous_route is not None
                and corrected_route is not None
                and previous_route.route != corrected_route.route
            ):
                # Part of this identity correction's evidence, never a separate choice.
                requested.events.append(
                    WorkflowEvent(
                        sequence=len(requested.events) + 1,
                        stage=requested.state,
                        outcome=EventOutcome.SUCCEEDED,
                        timestamp=requested_at,
                        case_id=requested.case_id,
                        correlation_id=requested.correlation_id,
                        code="UEN_ROUTE_CHANGED",
                        message=route_change_message(previous_route, corrected_route),
                    )
                )
            requested.events.append(
                WorkflowEvent(
                    sequence=len(requested.events) + 1,
                    stage=requested.state,
                    outcome=EventOutcome.SUCCEEDED,
                    timestamp=requested_at,
                    case_id=requested.case_id,
                    correlation_id=requested.correlation_id,
                    code="GOLDTIER_SEARCH_RECHECK_REQUESTED",
                    message="An authorized read-only GoldTier Search recheck was requested.",
                )
            )
            self._repository.save(OnboardingCase.model_validate(requested.model_dump()))

            if verified is not None:
                requested = self._acquire_registry_after_identity_recheck(
                    requested, identity, verified=verified
                )

            evidence, reused_case = self._run_initial_identity_search(
                requested,
                identity=identity,
                request_id=request_id,
            )
            completed_at = self._clock()
            completed = requested.model_copy(deep=True)
            completed.initial_target_search = evidence
            completed.initial_target_search_attempts = (
                *completed.initial_target_search_attempts[:-1],
                completed.initial_target_search_attempts[-1].model_copy(
                    update={
                        "status": "COMPLETED",
                        "completed_at": completed_at,
                        "result": evidence,
                    }
                ),
            )
            completed.error = None
            if reused_case is not None and reused_case.entity is not None:
                final_state = WorkflowState.GT_SEARCHED
                outcome = EventOutcome.SUCCEEDED
                code = "GOLDTIER_SEARCH_RECHECK_EXACT_MATCH"
            elif evidence.disposition == "NO_MATCH":
                final_state = (
                    WorkflowState.VALIDATED
                    if completed.entity is not None
                    else WorkflowState.GT_SEARCHED
                )
                outcome = EventOutcome.SUCCEEDED
                code = "GOLDTIER_SEARCH_RECHECK_NO_MATCH"
            else:
                final_state = WorkflowState.REVIEW_REQUIRED
                outcome = (
                    EventOutcome.FAILED
                    if evidence.disposition == "FAILED"
                    else EventOutcome.REVIEW_REQUIRED
                )
                code = (
                    evidence.provider_outcome
                    if evidence.disposition == "FAILED"
                    else "GT_SEARCH_IDENTITY_REVIEW_REQUIRED"
                )
            completed.state = final_state
            completed.updated_at = completed_at
            completed.events.append(
                WorkflowEvent(
                    sequence=len(completed.events) + 1,
                    stage=final_state,
                    outcome=outcome,
                    timestamp=completed_at,
                    case_id=completed.case_id,
                    correlation_id=completed.correlation_id,
                    code=code,
                    message="Authorized read-only GoldTier Search recheck completed.",
                )
            )
            validated = OnboardingCase.model_validate(completed.model_dump())
            self._repository.save(validated)
            # A verified registry correction remains usable independently of Search
            # review/failure, as in initial acquisition. Rebind the retained bundle
            # through normal canonical validation; never refetch or upgrade PARTIAL.
            if evidence.disposition in {"NO_MATCH", "EXACT_MATCH"} or verified is not None:
                retained = (
                    (validated.registry_acquisition, validated.registry_evidence_binding)
                    if validated.registry_acquisition is not None
                    else None
                )
                acquired = self._acquire_registry_after_identity_recheck(
                    validated, identity, verified=retained
                )
                if (
                    acquired.state == WorkflowState.VALIDATED
                    and reused_case is not None
                    and acquired.initial_target_search is not None
                    and acquired.initial_target_search.disposition == "EXACT_MATCH"
                ):
                    acquired.existing_target_state = ExistingTargetStateProvenance(
                        source_case_id=reused_case.case_id,
                        target_party_id=evidence.selected_party_id or "",
                        verified_at=completed_at,
                    )
                    acquired = OnboardingCase.model_validate(acquired.model_dump())
                    self._repository.save(acquired)
                return acquired.model_copy(deep=True)
            return validated.model_copy(deep=True)

    def has_retained_target_execution(self, case_id: UUID) -> bool:
        """Read-only capability guard; mutations recheck inside the owning boundary."""
        return bool(self._target_executions.list_for_case(case_id))

    def _run_initial_identity_search(
        self,
        case: OnboardingCase,
        *,
        identity: InitialCustomerIdentity,
        request_id: UUID,
    ) -> tuple[InitialGoldTierSearchEvidence, OnboardingCase | None]:
        if self._target_identity_policy is not None and case.entity is not None:
            # Typed values are unverified: a recheck searches the accepted identity only.
            identity = identity.model_copy(update={
                "legal_name": case.entity.legal_name,
                "country_of_incorporation": case.entity.country_of_incorporation,
            })
        request = (
            XpiCustomerSearchRequest(
                legal_name=identity.legal_name,
                country_of_incorporation=identity.country_of_incorporation,
            )
            if self.target_provider_mode == GoldTierProviderMode.SANDBOX
            else SearchPartyRequest(registration_number=identity.registration_number)
        )
        try:
            self._require_target_registry_provenance(case)
            result = validate_search_response(
                self._goldtier.search_party(
                    request,
                    GoldTierRequestMetadata(
                        correlation_id=case.correlation_id,
                        source_case_id=case.source_case_id,
                        idempotency_key=request_id,
                    ),
                )
            )
        except TargetRegistryProvenanceError:
            result = _initial_search_failure("REGISTRY_PROVENANCE_UNSUPPORTED")
        except ConnectorError as exc:
            result = _initial_search_failure(
                exc.code, status_code=observed_goldtier_xpi_search_status(exc)
            )
        except InvalidTargetResponseError:
            result = _initial_search_failure("GT_XPI_MALFORMED_RESPONSE")

        disposition: Literal["NO_MATCH", "EXACT_MATCH", "REVIEW_REQUIRED", "FAILED"] = (
            "REVIEW_REQUIRED"
        )
        selected_party_id: str | None = None
        reused_case: OnboardingCase | None = None
        if result.outcome == GoldTierSearchOutcome.NO_MATCH:
            disposition = "NO_MATCH"
        elif result.outcome == GoldTierSearchOutcome.FAILURE:
            result = _initial_search_failure(result.error_code, status_code=result.status_code)
            disposition = "FAILED"
        elif result.outcome == GoldTierSearchOutcome.MATCH_FOUND and len(result.candidates) == 1:
            candidate = result.candidates[0]
            reused_case = self._find_verified_target_case(
                registration_number=identity.registration_number,
                legal_name=identity.legal_name,
                country_of_incorporation=identity.country_of_incorporation,
                party_id=candidate.party_id,
                candidate=candidate,
            )
            if reused_case is not None and reused_case.entity is not None:
                disposition = "EXACT_MATCH"
                selected_party_id = candidate.party_id
            else:
                reused_case = None
            if (
                self.target_provider_mode == GoldTierProviderMode.SANDBOX
                and candidate.registration_number is not None
                and candidate.registration_number.strip().upper()
                == identity.registration_number.strip().upper()
                and candidate.country is not None
                and candidate.country.strip().upper() == identity.country_of_incorporation.upper()
            ):
                disposition = "EXACT_MATCH"
                selected_party_id = candidate.party_id
        evidence = InitialGoldTierSearchEvidence(
            request_id=request_id,
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
            candidate_registration_numbers=tuple(
                item.registration_number for item in result.candidates
            ),
            candidate_countries=tuple(item.country for item in result.candidates),
            selected_party_id=selected_party_id,
            searched_at=self._clock(),
        )
        return evidence, reused_case

    def _acquire_registry_after_identity_recheck(
        self,
        case: OnboardingCase,
        identity: InitialCustomerIdentity,
        *,
        verified: tuple[RegistryAcquisitionBundle, RegistryEvidenceBinding | None] | None = None,
    ) -> OnboardingCase:
        resolution = self._jurisdiction_resolver.resolve(
            (
                JurisdictionObservation(
                    jurisdiction=JurisdictionCode.SINGAPORE,
                    source=JurisdictionObservationSource.USER_INPUT,
                    observed_at=self._clock(),
                    source_reference="identity-correction.country_of_incorporation",
                ),
            ),
            resolved_at=self._clock(),
        )
        route, provider = self._registry_router.route(
            JurisdictionCode.SINGAPORE, decided_at=self._clock()
        )
        if provider is None:
            raise ValueError("Singapore registry provider is unavailable")
        updated = case.model_copy(deep=True)
        updated.jurisdiction_resolution = resolution
        updated.registry_route = route
        return self._acquire_required_registry_evidence(
            updated, provider, identity.registration_number, verified=verified
        )

    def _verify_registry_correction(
        self,
        identity: InitialCustomerIdentity,
        *,
        case_policy: CasePolicySnapshot,
    ) -> tuple[RegistryAcquisitionBundle, RegistryEvidenceBinding | None]:
        """The single request-bound registry verification path for every UEN choice.

        Verification precedes canonical mutation and performs no target operation.
        D-114: the UEN's own entity type picks the register; a government body is never
        verified through the ACRA provider.
        """
        _, provider = self._registry_router.route(
            JurisdictionCode.SINGAPORE, decided_at=self._clock()
        )
        if provider is None:
            raise ValueError("Registry verification could not verify this UEN.")
        route = route_uen(identity.registration_number)
        if route is not None and route.route == UenRoute.UNSUPPORTED:
            raise ValueError(uen_entity_type_unsupported_message(route))
        coordinator = self._registry_acquisition_coordinator
        try:
            government = (
                coordinator.read_government_register(
                    identity.registration_number,
                    case_policy=case_policy.registry,
                    policy_version=case_policy.catalogue_version,
                )
                if coordinator is not None
                else None
            )
        except RegistryCacheError:
            raise ValueError("Registry verification could not verify this UEN.") from None
        result = None
        acquisition: RegistryAcquisitionBundle | None
        if route is not None and route.route == UenRoute.GOVERNMENT_REGISTER:
            if government is None:
                raise ValueError(GOVERNMENT_IDENTITY_NOT_FOUND_MESSAGE)
            acquisition = government
        elif government is not None:
            raise ValueError(ENTITY_CATEGORY_MISMATCH_MESSAGE)
        else:
            try:
                result = (
                    coordinator.acquire(
                        provider,
                        identity.registration_number,
                        case_policy=case_policy.registry,
                        policy_version=case_policy.catalogue_version,
                    )
                    if coordinator is not None
                    else None
                )
                acquisition = (
                    result.acquisition
                    if result is not None
                    else provider.retrieve_acquisition(identity.registration_number)
                )
            except (ConnectorError, RegistryCacheError):
                raise ValueError("Registry verification could not verify this UEN.") from None
        if (
            acquisition is None
            or acquisition.status
            not in {RegistryAcquisitionStatus.COMPLETE, RegistryAcquisitionStatus.PARTIAL}
            or acquisition.requested_identifier != identity.registration_number
            or validate_entity(acquisition.entity_profile)
        ):
            raise ValueError("Registry verification could not verify this UEN.")
        return acquisition, result.binding if result is not None else None

    def bind_goldtier_case_classification(
        self,
        *,
        case_id: UUID,
        kyc_customer_type: str | None = None,
        client_segment: str | None = None,
        expected_case_event_count: int | None = None,
        document_selections: tuple[TargetClassificationSelection, ...] | None = None,
        classification_assessment: TargetClassificationAssessment | None = None,
        actor_id: str | None = None,
    ) -> OnboardingCase:
        """One pre-dispatch owner for document and explicit user selection."""
        with self.case_lock(case_id):
            case = self._repository.get(case_id)
            if case is None:
                raise ValueError("Onboarding case was not found")
            if (
                expected_case_event_count is not None
                and len(case.events) != expected_case_event_count
            ):
                raise ValueError("Onboarding case changed before target classification")
            target = case.policy_snapshot.goldtier_target
            if target is None:
                raise ValueError("GoldTier target policy is unavailable for this case")
            if (
                case.target_dispatch_confirmation is not None
                or case.goldtier_result is not None
                or self.has_retained_target_execution(case_id)
                or case.state
                in {
                    WorkflowState.GT_SHELL_CREATED,
                    WorkflowState.GT_POLICY_CREATED,
                    WorkflowState.GT_ENRICHED,
                    WorkflowState.COMPLETED,
                }
            ):
                raise ValueError("GoldTier submission is already frozen and recovery-controlled")
            previous = {item.field_key: item for item in case.target_classification_selections}
            automatic = {item.field_key: item for item in document_selections or ()}
            inputs = {
                TargetClassificationKey.KYC_CUSTOMER_TYPE: kyc_customer_type,
                TargetClassificationKey.CLIENT_SEGMENT: client_segment,
            }
            selections = dict(previous)
            values: dict[str, AuthorityLabelledTargetValue] = {}
            timestamp = self._clock()
            for key in TargetClassificationKey:
                prior = previous.get(key)
                if document_selections is not None:
                    if prior is not None and prior.source == "USER":
                        continue
                    selection = automatic.get(key)
                    if selection is not None:
                        if prior is not None and prior.model_dump(
                            exclude={"classified_at"}
                        ) == selection.model_dump(exclude={"classified_at"}):
                            selection = prior
                        selections[key] = selection
                        values[key] = AuthorityLabelledTargetValue(
                            value=selection.value, authority=PolicyAuthority.PROJECT_DERIVED_POC
                        )
                    elif prior is not None and prior.source == "DOCUMENT":
                        selections.pop(key)
                        values[key] = AuthorityLabelledTargetValue(
                            value="TBD_SPONSOR", authority=PolicyAuthority.TBD_SPONSOR
                        )
                else:
                    value = inputs[key]
                    if value is None:
                        continue
                    vocabulary = (
                        GOLDTIER_KYC_CUSTOMER_TYPE_VALUES
                        if key == TargetClassificationKey.KYC_CUSTOMER_TYPE
                        else GOLDTIER_CLIENT_SEGMENT_VALUES
                    )
                    if value not in vocabulary:
                        raise ValueError("GoldTier classification is not in the current vocabulary")
                    if (
                        prior is not None
                        and prior.source == "DOCUMENT"
                        and (
                            classification_assessment is None
                            or (
                                prior.evidence_fingerprint
                                == classification_assessment.evidence_fingerprint
                                and any(
                                    candidate.field_key == key and candidate.value == prior.value
                                    for candidate in classification_assessment.candidates
                                )
                            )
                        )
                    ):
                        if value != prior.value:
                            raise ValueError(
                                "Current automatic classification requires document review "
                                "before changing"
                            )
                        continue
                    if (
                        prior is not None
                        and prior.source == "USER"
                        and value == prior.value
                        and prior.actor_id == actor_id
                        and prior.evidence_fingerprint
                        == (
                            classification_assessment.evidence_fingerprint
                            if classification_assessment is not None
                            else None
                        )
                    ):
                        continue
                    if classification_assessment is not None and any(
                        candidate.field_key == key and candidate.value != value
                        for candidate in classification_assessment.candidates
                    ):
                        raise ValueError(
                            "The selected value disagrees with current trusted evidence"
                        )
                    selections[key] = TargetClassificationSelection(
                        field_key=key,
                        value=value,
                        source="USER",
                        actor_id=actor_id,
                        evidence_fingerprint=(
                            classification_assessment.evidence_fingerprint
                            if classification_assessment is not None
                            else None
                        ),
                        classified_at=timestamp,
                        policy_version=case.policy_snapshot.catalogue_version,
                    )
                    values[key] = AuthorityLabelledTargetValue(
                        value=value, authority=PolicyAuthority.USER_AUTHORIZED_POC
                    )
            selected_target = target.model_copy(update=values, deep=True)
            kyc_selection = selections.get(TargetClassificationKey.KYC_CUSTOMER_TYPE)
            if (
                case.entity is not None
                and not bounded_classification_compatible(
                    case.entity.party_type,
                    selected_target.kyc_customer_type.value,
                    automatic=kyc_selection is not None and kyc_selection.source == "DOCUMENT",
                )
            ):
                if document_selections is None:
                    raise ValueError(
                        classification_incompatibility_message(
                            case.entity.party_type, selected_target.kyc_customer_type.value
                        )
                    )
                key = TargetClassificationKey.KYC_CUSTOMER_TYPE
                selections.pop(key, None)
                selected_target = selected_target.model_copy(
                    update={
                        key: AuthorityLabelledTargetValue(
                            value="TBD_SPONSOR", authority=PolicyAuthority.TBD_SPONSOR
                        )
                    }
                )
            ordered = tuple(selections[key] for key in TargetClassificationKey if key in selections)
            if target == selected_target and case.target_classification_selections == ordered:
                return case.model_copy(deep=True)
            updated = case.model_copy(deep=True)
            updated.policy_snapshot = case.policy_snapshot.model_copy(
                update={"goldtier_target": selected_target}, deep=True
            )
            updated.target_classification_selections = ordered
            updated.target_dispatch_confirmation = None
            updated.updated_at = timestamp
            updated.events.append(
                WorkflowEvent(
                    sequence=len(updated.events) + 1,
                    stage=updated.state,
                    outcome=EventOutcome.SUCCEEDED,
                    timestamp=timestamp,
                    case_id=case_id,
                    correlation_id=case.correlation_id,
                    code="GOLDTIER_CASE_CLASSIFICATION_BOUND",
                    message=(
                        "Case-specific target selection evidence was retained before submission."
                    ),
                )
            )
            validated = OnboardingCase.model_validate(updated)
            self._repository.save(validated)
            return validated.model_copy(deep=True)

    def rebind_case_policy_snapshot(
        self,
        *,
        case_id: UUID,
        actor_id: str,
        rationale: str,
        expected_case_event_count: int,
        reauthorize: Callable[[], None] | None = None,
    ) -> OnboardingCase:
        """Rebind only accepted SG target constants while retaining case-owned policy choices."""

        with self.case_lock(case_id):
            if reauthorize is not None:
                reauthorize()
            case = self._repository.get(case_id)
            if case is None:
                raise ValueError("Onboarding case was not found")
            if len(case.events) != expected_case_event_count:
                raise ValueError("Onboarding case changed before policy rebind")
            if (
                case.target_dispatch_confirmation is not None
                or case.goldtier_result is not None
                or case.state
                in {
                    WorkflowState.GT_SHELL_CREATED,
                    WorkflowState.GT_POLICY_CREATED,
                    WorkflowState.GT_ENRICHED,
                    WorkflowState.COMPLETED,
                }
            ):
                raise ValueError("Case policy is frozen after target execution begins")
            _validate_sg_policy_rebind_identity(case)

            current_catalogue = self._policy_snapshot_provider()
            current_target = _validated_current_sg_target_policy(current_catalogue)
            previous = case.policy_snapshot
            previous_target = previous.goldtier_target
            retained_target = previous_target or current_target

            def retained_operator_choice(
                old: AuthorityLabelledTargetValue,
                current: AuthorityLabelledTargetValue,
                allowed: tuple[str, ...],
            ) -> AuthorityLabelledTargetValue:
                retained_document_choice = any(
                    selection.source == "DOCUMENT" and selection.value == old.value
                    for selection in case.target_classification_selections
                )
                if old.value in allowed and (
                    old.authority == PolicyAuthority.USER_AUTHORIZED_POC
                    or (old.authority == PolicyAuthority.PROJECT_DERIVED_POC
                        and retained_document_choice)
                ):
                    return old
                return current

            rebound_target = GoldTierTargetPolicySnapshot(
                kyc_customer_type=retained_operator_choice(
                    retained_target.kyc_customer_type,
                    current_target.kyc_customer_type,
                    GOLDTIER_KYC_CUSTOMER_TYPE_VALUES,
                ),
                client_segment=retained_operator_choice(
                    retained_target.client_segment,
                    current_target.client_segment,
                    GOLDTIER_CLIENT_SEGMENT_VALUES,
                ),
                customer_external_system=current_target.customer_external_system,
                registration_type=current_target.registration_type,
                policy=current_target.policy,
                booking_entity=current_target.booking_entity,
                account_entity_type=retained_target.account_entity_type,
                product_type=retained_target.product_type,
            )
            fixed_fields: tuple[
                tuple[
                    Literal[
                        "customerExternalSystem",
                        "registrationType",
                        "policy",
                        "bookingEntity",
                    ],
                    Literal[
                        "customer_external_system",
                        "registration_type",
                        "policy",
                        "booking_entity",
                    ],
                ],
                ...,
            ] = (
                ("customerExternalSystem", "customer_external_system"),
                ("registrationType", "registration_type"),
                ("policy", "policy"),
                ("bookingEntity", "booking_entity"),
            )
            changed_fields = tuple(
                browser_name
                for browser_name, attribute in fixed_fields
                if previous_target is None
                or getattr(previous_target, attribute) != getattr(rebound_target, attribute)
            )
            if not changed_fields:
                return case.model_copy(deep=True)
            if len(case.policy_rebind_history) >= 8:
                raise ValueError("Case policy rebind history capacity is exhausted")

            now = self._clock()
            next_revision = case.policy_snapshot_revision + 1
            try:
                audit = CasePolicyRebindAudit(
                    previous_revision=case.policy_snapshot_revision,
                    resulting_revision=next_revision,
                    previous_snapshot=previous,
                    actor_id=actor_id,
                    rebound_at=now,
                    rationale=rationale,
                    changed_fields=changed_fields,
                    source_catalogue_version=current_catalogue.catalogue_version,
                )
            except ValidationError:
                raise ValueError("Policy rebind audit metadata is invalid") from None
            rebound_snapshot = previous.model_copy(
                update={
                    # Existing SG target-only repair does not rebind frozen
                    # business policy/version/parameters or its original timestamp.
                    "goldtier_target": rebound_target,
                },
                deep=True,
            )
            updated = case.model_copy(deep=True)
            updated.policy_snapshot = CasePolicySnapshot.model_validate(rebound_snapshot)
            updated.policy_snapshot_revision = next_revision
            updated.policy_rebind_history = (*case.policy_rebind_history, audit)
            updated.target_dispatch_confirmation = None
            updated.updated_at = now
            updated.events.append(
                WorkflowEvent(
                    sequence=len(updated.events) + 1,
                    stage=updated.state,
                    outcome=EventOutcome.SUCCEEDED,
                    timestamp=now,
                    case_id=updated.case_id,
                    correlation_id=updated.correlation_id,
                    code="SG_POC_POLICY_SNAPSHOT_REBOUND",
                    message="Accepted SG POC target constants were rebound to the case.",
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
        ``resolution`` is ``None`` when no identity assessment exists: the provider
        Search failed, or the existing resolver could compare no identity feature.
        """

        if self.target_provider_mode != GoldTierProviderMode.SANDBOX:
            raise ValueError("GoldTier sandbox Search is not configured")
        if self._target_identity_policy is not None and (
            request.goldtier_id is None
            or request.legal_name is not None
            or request.group_company_name is not None
        ):
            # Typed names are unverified identity. An exact target ID is an HR-only lookup.
            raise TargetRegistryProvenanceError
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
        if result.outcome == GoldTierSearchOutcome.FAILURE:
            # A failed provider Search establishes nothing about customer existence.
            return TargetIdentitySearchEvidence(result=result, resolution=None)
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
        if resolution.candidates and all(
            feature.assessment == FeatureAssessment.NOT_ASSESSED
            for candidate in resolution.candidates
            for feature in candidate.features
        ):
            # Retrieval without comparable evidence (for example an ID-only Search) is
            # not an identity no-match; a resolver CONFLICT is always retained.
            return TargetIdentitySearchEvidence(result=result, resolution=None)
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
        created_by_actor_id: str | None = None,
    ) -> OnboardingCase:
        """Preserve the legacy intake route while stopping before target mutation."""

        case = self.create_staged_case(
            uen,
            country_of_incorporation,
            legal_name=legal_name,
            team_id=team_id,
            priority=priority,
            created_by_actor_id=created_by_actor_id,
        )
        return case

    def create_staged_case(
        self,
        uen: str,
        country_of_incorporation: JurisdictionCode | str | None = None,
        *,
        legal_name: str | None = None,
        team_id: TeamId | None = None,
        priority: CasePriority | None = None,
        created_by_actor_id: str | None = None,
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
            created_by_actor_id=created_by_actor_id,
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
        created_by_actor_id: str | None = None,
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
                created_by_actor_id=created_by_actor_id,
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
        created_by_actor_id: str | None,
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
            created_by_actor_id=created_by_actor_id,
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

        # Under an identity policy the typed name is unverified, so it is never sent. The
        # target Search then runs on the accepted registry identity, once that exists.
        if legal_name is not None and self._target_identity_policy is None:
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
                result = _initial_search_failure(
                    exc.code, status_code=observed_goldtier_xpi_search_status(exc)
                )
            except InvalidTargetResponseError:
                result = _initial_search_failure("GT_XPI_MALFORMED_RESPONSE")

            disposition: Literal["NO_MATCH", "EXACT_MATCH", "REVIEW_REQUIRED", "FAILED"] = (
                "REVIEW_REQUIRED"
            )
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
                result.outcome == GoldTierSearchOutcome.MATCH_FOUND and len(result.candidates) == 1
            ):
                candidate = result.candidates[0]
                prior = self._find_verified_target_case(
                    registration_number=normalised_uen,
                    legal_name=legal_name,
                    country_of_incorporation=explicit_jurisdiction.value,
                    party_id=candidate.party_id,
                    candidate=candidate,
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
                if (
                    self.target_provider_mode == GoldTierProviderMode.SANDBOX
                    and candidate.registration_number is not None
                    and candidate.registration_number.strip().upper() == normalised_uen
                    and candidate.country is not None
                    and candidate.country.strip().upper() == explicit_jurisdiction.value
                ):
                    disposition = "EXACT_MATCH"
                    selected_party_id = candidate.party_id
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
                candidate_registration_numbers=tuple(
                    item.registration_number for item in result.candidates
                ),
                candidate_countries=tuple(item.country for item in result.candidates),
                selected_party_id=selected_party_id,
                searched_at=self._clock(),
            )
            if disposition == "EXACT_MATCH":
                self._record(
                    case,
                    WorkflowState.VALIDATED,
                    EventOutcome.SUCCEEDED,
                    (
                        "Exact existing GoldTier target state was hydrated; Shell and new "
                        "Policy are skipped while required registry evidence is acquired."
                    ),
                    "GOLDTIER_FIRST_EXACT_MATCH",
                )
            if disposition == "REVIEW_REQUIRED":
                self._record(
                    case,
                    WorkflowState.GT_SEARCHED,
                    EventOutcome.REVIEW_REQUIRED,
                    (
                        "GoldTier candidates require exact identity review; independent "
                        "registry evidence may continue while target writes remain blocked."
                    ),
                    "GT_SEARCH_IDENTITY_REVIEW_REQUIRED",
                )
            if disposition == "FAILED":
                self._record(
                    case,
                    WorkflowState.GT_SEARCHED,
                    EventOutcome.FAILED,
                    result.message,
                    result.error_code or "SEARCH_SERVICE_UNAVAILABLE",
                )
            elif disposition == "NO_MATCH":
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

        if legal_name is None:
            self._record(
                case,
                case.state,
                EventOutcome.SUCCEEDED,
                "Exact registration-identifier GoldTier lookup is unsupported; "
                "registry resolution continues.",
                "GOLDTIER_SEARCH_SKIPPED_UNSUPPORTED_IDENTIFIER",
            )
        return self._acquire_required_registry_evidence(
            case, registry_provider, normalised_uen
        )

    def acquire_subsidiary_registry_evidence(
        self,
        identifier: str,
        *,
        case_policy: RegistryPolicySnapshot | None,
        policy_version: int,
        cancelled: Callable[[], bool] | None = None,
    ) -> SubsidiaryRegistryEvidence:
        """Read one corporate owner's own registry evidence without touching any case.

        This narrow interface reuses the closed Singapore route and the single registry
        coordinator: a fresh eligible snapshot is a zero-call cache hit; a miss or stale
        entry uses the configured provider once under the existing per-key single-flight.
        It never replaces a case acquisition, binding, lock or event history.
        """

        normalized = identifier.strip().upper()
        if not is_eligible_singapore_uen(normalized):
            raise AcraIdentifierNotEligibleError
        _, provider = self._registry_router.route(
            JurisdictionCode.SINGAPORE, decided_at=self._clock()
        )
        if provider is None:
            raise AcraIdentifierNotEligibleError
        coordinator = self._registry_acquisition_coordinator
        if coordinator is None:
            if cancelled is not None and cancelled():
                raise RegistryAcquisitionBusyError
            return SubsidiaryRegistryEvidence(
                identifier=normalized,
                acquisition=provider.retrieve_acquisition(normalized),
                disposition=None,
                provider_backed=True,
            )
        result = coordinator.acquire(
            provider,
            normalized,
            case_policy=case_policy,
            policy_version=policy_version,
            cancelled=cancelled,
        )
        disposition = result.binding.disposition if result.binding is not None else None
        cache_hit = disposition == RegistryEvidenceDisposition.CACHE_HIT
        return SubsidiaryRegistryEvidence(
            identifier=normalized,
            acquisition=result.acquisition,
            disposition=disposition,
            provider_backed=not (cache_hit or result.negative_cache_hit),
            negative_cache_hit=result.negative_cache_hit,
            entity_profile_reused=cache_hit or result.entity_profile_reused,
        )

    def acquire_subsidiary_shareholder_evidence(
        self,
        identifier: str,
        *,
        case_policy: RegistryPolicySnapshot | None,
        policy_version: int,
        cancelled: Callable[[], bool] | None = None,
    ) -> SubsidiaryShareholderEvidence | None:
        """D-079: one corporate holder's shareholder operation without an entity profile.

        Returns `None` without any call unless the routed provider is the official
        Marketplace Mock composition. It reuses the single registry coordinator under
        its own contract key and never touches a case.
        """

        normalized = identifier.strip().upper()
        if not is_eligible_singapore_uen(normalized):
            raise AcraIdentifierNotEligibleError
        _, provider = self._registry_router.route(
            JurisdictionCode.SINGAPORE, decided_at=self._clock()
        )
        if provider is None:
            raise AcraIdentifierNotEligibleError
        if not getattr(provider, "supports_shareholder_evidence", False):
            return None
        shareholder_provider = cast(ShareholderEvidenceProvider, provider)
        coordinator = self._registry_acquisition_coordinator
        if coordinator is None:
            if cancelled is not None and cancelled():
                raise RegistryAcquisitionBusyError
            return SubsidiaryShareholderEvidence(
                identifier=normalized,
                evidence=shareholder_provider.retrieve_shareholder_evidence(normalized),
                provider_backed=True,
            )
        result = coordinator.acquire_shareholder_evidence(
            shareholder_provider,
            normalized,
            case_policy=case_policy,
            policy_version=policy_version,
            cancelled=cancelled,
        )
        return SubsidiaryShareholderEvidence(
            identifier=normalized,
            evidence=result.evidence,
            provider_backed=not result.cache_hit,
        )

    def acquire_subsidiary_business_profile_evidence(
        self,
        identifier: str,
        *,
        case_policy: RegistryPolicySnapshot | None,
        policy_version: int,
        cancelled: Callable[[], bool] | None = None,
    ) -> SubsidiaryBusinessProfileEvidence | None:
        """D-088: one corporate holder's businessProfile operation without an entity profile.

        Returns `None` without any call unless the routed provider is the official
        Marketplace Mock composition. It reuses the single registry coordinator under
        its own contract key and never touches a case.
        """

        normalized = identifier.strip().upper()
        if not is_eligible_singapore_uen(normalized):
            raise AcraIdentifierNotEligibleError
        _, provider = self._registry_router.route(
            JurisdictionCode.SINGAPORE, decided_at=self._clock()
        )
        if provider is None:
            raise AcraIdentifierNotEligibleError
        if not getattr(provider, "supports_business_profile_evidence", False):
            return None
        profile_provider = cast(BusinessProfileEvidenceProvider, provider)
        coordinator = self._registry_acquisition_coordinator
        if coordinator is None:
            if cancelled is not None and cancelled():
                raise RegistryAcquisitionBusyError
            return SubsidiaryBusinessProfileEvidence(
                identifier=normalized,
                evidence=profile_provider.retrieve_business_profile_evidence(normalized),
                provider_backed=True,
            )
        result = coordinator.acquire_business_profile_evidence(
            profile_provider,
            normalized,
            case_policy=case_policy,
            policy_version=policy_version,
            cancelled=cancelled,
        )
        return SubsidiaryBusinessProfileEvidence(
            identifier=normalized,
            evidence=result.evidence,
            provider_backed=not result.cache_hit,
        )

    def _read_government_register(
        self, case: OnboardingCase, normalised_uen: str
    ) -> RegistryAcquisitionBundle | None:
        """D-114: the government register only; without a coordinator there is no register."""
        coordinator = self._registry_acquisition_coordinator
        if coordinator is None:
            return None
        return coordinator.read_government_register(
            normalised_uen,
            case_policy=case.policy_snapshot.registry,
            policy_version=case.policy_snapshot.catalogue_version,
        )

    def _acquire_required_registry_evidence(
        self,
        case: OnboardingCase,
        registry_provider: RegistryProvider,
        normalised_uen: str,
        *,
        verified: tuple[RegistryAcquisitionBundle, RegistryEvidenceBinding | None] | None = None,
    ) -> OnboardingCase:
        """Acquire or validate current case evidence through the single registry owner."""

        acquisition: RegistryAcquisitionBundle | None
        binding = verified[1] if verified is not None else None
        registry_coordinator = self._registry_acquisition_coordinator
        # D-114: the UEN's own entity type picks the register; the system records it.
        route = route_uen(normalised_uen)
        case.uen_route = route
        government: RegistryAcquisitionBundle | None = None
        if verified is None and route is not None:
            if route.route == UenRoute.UNSUPPORTED:
                return self._terminate(
                    case,
                    WorkflowState.REVIEW_REQUIRED,
                    EventOutcome.REVIEW_REQUIRED,
                    "UEN_ENTITY_TYPE_UNSUPPORTED",
                    uen_entity_type_unsupported_message(route),
                )
            government = self._run_required_stage(
                case,
                code="REGISTRY_CACHE_FAILURE",
                message="Registry evidence could not be prepared safely.",
                operation=lambda: self._read_government_register(case, normalised_uen),
            )
            if route.route == UenRoute.GOVERNMENT_REGISTER and government is None:
                # Never the ACRA provider for a government body.
                return self._terminate(
                    case,
                    WorkflowState.REVIEW_REQUIRED,
                    EventOutcome.REVIEW_REQUIRED,
                    "GOVERNMENT_IDENTITY_NOT_FOUND",
                    GOVERNMENT_IDENTITY_NOT_FOUND_MESSAGE,
                )
            if route.route == UenRoute.ACRA and government is not None:
                # A government record under an ACRA-format UEN stops before ACRA.
                return self._terminate(
                    case,
                    WorkflowState.REVIEW_REQUIRED,
                    EventOutcome.REVIEW_REQUIRED,
                    "ENTITY_CATEGORY_MISMATCH",
                    ENTITY_CATEGORY_MISMATCH_MESSAGE,
                )
        if verified is not None:
            acquisition = verified[0]
        elif route is not None and route.route == UenRoute.GOVERNMENT_REGISTER:
            acquisition = government
        elif registry_coordinator is None:
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
                    case_policy=case.policy_snapshot.registry,
                    policy_version=case.policy_snapshot.catalogue_version,
                ),
            )
            acquisition = coordinated.acquisition
            binding = coordinated.binding
        if acquisition is None:
            return self._terminate(
                case,
                WorkflowState.REVIEW_REQUIRED,
                EventOutcome.REVIEW_REQUIRED,
                "ACRA_ENTITY_NOT_FOUND",
                "No ACRA entity was found for this UEN.",
            )

        case.registry_acquisition = acquisition
        entity = acquisition.entity_profile
        case.entity = entity
        case.registry_evidence_binding = binding
        registry_identity_conflict = False
        if (
            case.initial_target_search is not None
            and case.initial_target_search.disposition == "EXACT_MATCH"
        ):
            identity = case.initial_identity
            if (
                identity is None
                or entity.registration_number.strip().upper() != identity.registration_number
                or " ".join((entity.legal_name or "").split()).casefold()
                != " ".join(identity.legal_name.split()).casefold()
                or (entity.country_of_incorporation or "").strip().upper()
                != identity.country_of_incorporation
            ):
                # Never relabel an earlier Search as proof of a different registry identity.
                case.existing_target_state = None
                if case.initial_target_search is not None:
                    case.initial_target_search = InitialGoldTierSearchEvidence.model_validate(
                        {
                            **case.initial_target_search.model_dump(),
                            "disposition": "REVIEW_REQUIRED",
                            "selected_party_id": None,
                        }
                    )
                if (
                    case.initial_target_search_attempts
                    and case.initial_target_search is not None
                    and case.initial_target_search_attempts[-1].request_id
                    == case.initial_target_search.request_id
                ):
                    case.initial_target_search_attempts = (
                        *case.initial_target_search_attempts[:-1],
                        case.initial_target_search_attempts[-1].model_copy(
                            update={"result": case.initial_target_search}
                        ),
                    )
                registry_identity_conflict = True
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
        # ADR-018 §3.5 F1: the binding write is committed; freeze (or flag) the basis.
        self._after_registry_binding(case)
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
        if registry_identity_conflict:
            return self._terminate(
                case,
                WorkflowState.REVIEW_REQUIRED,
                EventOutcome.REVIEW_REQUIRED,
                "GT_SEARCH_IDENTITY_REVIEW_REQUIRED",
                "Current registry identity differs from the verified target identity.",
            )
        # Acquisition completeness includes ownership evidence. Its absence does not
        # invalidate registry identity; the ownership owner retains that separate gap.
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
            accepted_at=case.created_at,
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
            self._require_target_registry_provenance(case)
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
        resolution = self._entity_resolver.resolve_entity(
            source=source,
            candidates=self._target_candidate_identities(result),
            policy=policy,
        )
        if (
            resolution.outcome == EntityResolutionOutcome.EXACT_MATCH
            and resolution.selected_candidate_id is not None
            and not self._mock_reuse_is_verified(
                submission_input, resolution.selected_candidate_id, result.candidates[0]
            )
        ):
            return None
        return resolution

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

            if not self.has_valid_target_dispatch_confirmation(case):
                raise ValueError("Target dispatch requires a current frozen-review confirmation")

            self._require_target_registry_provenance(case)
            # D-137: this one-shot path cannot pause between steps, so the window must admit
            # every operation it may run before the ledger records anything.
            for operation in ("SHELL", "POLICY", "AMEND"):
                self._require_target_writes(submission_input, operation)
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
                with self._execution_ledger_guard:
                    self._active_target_submissions.discard(submission_input.submission_id)
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
        reauthorize: Callable[[], None] | None = None,
    ) -> GoldTierExecutionReceipt | None:
        """Clear volatile sending activity on every normal, failed or uncertain exit."""

        try:
            return self._advance_incremental_submission_input(
                submission_input,
                search_resolution=search_resolution,
                selected_party_id=selected_party_id,
                reauthorize=reauthorize,
            )
        except MutationOutcomeUncertainError as exc:
            with self.case_lock(submission_input.case_id):
                entry = self.get_target_execution_entry(submission_input.submission_id)
                case = self._repository.get(submission_input.case_id)
                reason = getattr(exc, "reason", MutationUncertaintyReason.UNKNOWN)
                if not isinstance(reason, MutationUncertaintyReason):
                    reason = MutationUncertaintyReason.UNKNOWN
                if (
                    case is not None
                    and entry is not None
                    and entry.attempted_operations != entry.lifecycle_resolved_operations
                ):
                    code = f"GT_TARGET_OUTCOME_UNCERTAIN_{reason.value}"
                    if not case.events or not (
                        case.events[-1].code or ""
                    ).startswith("GT_TARGET_OUTCOME_UNCERTAIN_"):
                        self._record(
                            case,
                            case.state,
                            EventOutcome.FAILED,
                            "A target attempt has no definitive outcome; replay remains blocked.",
                            code,
                        )
            raise
        finally:
            with self._execution_ledger_guard:
                self._active_target_submissions.discard(submission_input.submission_id)

    def _advance_incremental_submission_input(
        self,
        submission_input: GoldTierSubmissionInput,
        *,
        search_resolution: GoldTierSearchResolution,
        selected_party_id: str | None,
        reauthorize: Callable[[], None] | None = None,
    ) -> GoldTierExecutionReceipt | None:
        """Advance at most one mutation after a retained early Search checkpoint."""

        if (
            submission_input.provider_mode != self._goldtier_mapper.environment
            or submission_input.provider_mode != self._goldtier.environment
        ):
            raise TargetProviderContextMismatchError
        with self.case_lock(submission_input.case_id):
            if reauthorize is not None:
                reauthorize()
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

            if not self.has_valid_target_dispatch_confirmation(case):
                raise ValueError("Target dispatch requires a current frozen-review confirmation")

            self._require_target_registry_provenance(case)
            entry = self._stored_execution_entry(submission_input)
            if entry is None:
                if search_resolution == GoldTierSearchResolution.NO_MATCH:
                    self._require_target_writes(submission_input, "SHELL")
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
                raise ValueError("Amend has a provider-verified failure and must not be replayed")
            if entry.attempted_operations != entry.lifecycle_resolved_operations:
                raise MutationOutcomeUncertainError

            party_id = entry.resolved_party_id
            if party_id is None:
                return self._advance_shell(case, submission_input, entry)
            if (
                entry.policy_status is None
                and entry.search_resolution == GoldTierSearchResolution.NO_MATCH
            ):
                return self._advance_policy(case, submission_input, entry, party_id)
            if entry.amend_status is None:
                return self._advance_amend(case, submission_input, entry, party_id)
            if (
                entry.readback_status is None
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
        if search_resolution in {
            GoldTierSearchResolution.EXACT_MATCH, GoldTierSearchResolution.CONFIRMED_EXISTING,
        }:
            if selected_party_id is None:
                raise ValueError("Exact target Search requires a selected party")
            if not self._mock_reuse_is_verified(submission_input, selected_party_id):
                raise ValueError("Mock customer reuse requires prior finalized readback proof")
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
                workflow_dispatch=entry.workflow_dispatch,
                state=entry.state,
                attempted_operations=entry.attempted_operations,
                completed_operations=completed,
                resolved_operations=resolved,
                provider_verified_recovery=entry.provider_verified_recovery,
                provider_verified_policy_recovery=(entry.provider_verified_policy_recovery),
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
                candidate,
                expected_state=GoldTierExecutionLedgerState.IN_PROGRESS.value,
                expected_attempted=entry.attempted_operations,
            )
            return candidate.model_copy(deep=True)

    def _advance_shell(
        self,
        case: OnboardingCase,
        submission_input: GoldTierSubmissionInput,
        entry: GoldTierExecutionLedgerEntry,
    ) -> GoldTierExecutionReceipt | None:
        self._require_target_writes(submission_input, "SHELL")
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
        self._require_target_writes(submission_input, "POLICY")
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
        if not self._goldtier_mapper.requires_amend(submission_input):
            with self._execution_ledger_guard:
                current = self._stored_execution_entry(submission_input)
                if (
                    current is None
                    or current.attempted_operations != current.lifecycle_resolved_operations
                ):
                    raise MutationOutcomeUncertainError
                skipped = GoldTierExecutionLedgerEntry.model_validate(
                    {
                        **current.model_dump(),
                        "amend_status": "AMEND_NOT_REQUIRED",
                        # Excluded from dumps; a copy must still carry the claim.
                        "workflow_dispatch": current.workflow_dispatch,
                    }
                )
                self._target_executions.replace(
                    skipped,
                    expected_state=GoldTierExecutionLedgerState.IN_PROGRESS.value,
                    expected_attempted=current.attempted_operations,
                )
            self._record(
                case,
                case.state,
                EventOutcome.SUCCEEDED,
                "No supported customer enrichment remains; Amend is not required.",
                "AMEND_NOT_REQUIRED",
            )
            return None
        self._require_target_writes(submission_input, "AMEND")
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
        case.goldtier_result = GoldTierResult(
            party_id=party_id,
            shell_status=entry.shell_status or "EXISTING_PARTY_REUSED",
            policy_id=entry.policy_id,
            policy_status=entry.policy_status,
            amend_status=amend.status,
        )
        existing_party = entry.search_resolution in {
            GoldTierSearchResolution.EXACT_MATCH, GoldTierSearchResolution.CONFIRMED_EXISTING,
        }
        self._record(
            case,
            WorkflowState.VALIDATED if existing_party else WorkflowState.GT_POLICY_CREATED,
            EventOutcome.SUCCEEDED,
            (
                "Existing GoldTier party amendment succeeded; read-back verification is pending."
                if existing_party
                else "GoldTier party amendment succeeded; read-back verification is pending."
            ),
            "GT_READBACK_PENDING",
        )
        return None

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

        verified = _readback_identity_matches(submission_input, readback, party_id)
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
            "GoldTier submission read-back verified the retained customer identity.",
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

    def get_target_execution_activity_snapshot(
        self, submission_id: UUID
    ) -> tuple[GoldTierExecutionLedgerEntry | None, bool]:
        """Read activity and durable facts under the same projection guard."""

        with self._execution_ledger_guard:
            stored = self._target_executions.get(submission_id)
            return (
                stored.model_copy(deep=True) if stored is not None else None,
                submission_id in self._active_target_submissions,
            )

    def is_execution_outcome_uncertain(self, submission_id: UUID) -> bool:
        """Consult one authoritative ledger snapshot without invoking the target."""

        with self._execution_ledger_guard:
            stored = self._target_executions.get(submission_id)
            return bool(
                stored is not None
                and submission_id not in self._active_target_submissions
                and stored.state == GoldTierExecutionLedgerState.IN_PROGRESS
                and stored.attempted_operations != stored.lifecycle_resolved_operations
                and stored.target_outcome is None
                and stored.receipt is None
            )

    def is_target_submission_active(self, submission_id: UUID) -> bool:
        """Volatile activity explains an in-flight call; the ledger still owns outcomes."""

        with self._execution_ledger_guard:
            return submission_id in self._active_target_submissions

    def verify_completed_target(
        self,
        *,
        case_id: UUID,
        submission_id: UUID,
        reauthorize: Callable[[], None],
    ) -> CompletedTargetVerificationEvidence:
        """One exact retained-ID Search after completion; no writes or replay."""

        with self.case_lock(case_id):
            reauthorize()
            case = self._repository.get(case_id)
            entry = self.get_target_execution_entry(submission_id)
            outcome = entry.target_outcome if entry is not None else None
            if (
                self.target_provider_mode != GoldTierProviderMode.SANDBOX
                or self._goldtier.environment != GoldTierProviderMode.SANDBOX
                or case is None or case.entity is None or entry is None
                or entry.submission_input.case_id != case_id
                or entry.submission_input.provider_mode != GoldTierProviderMode.SANDBOX
                or entry.state != GoldTierExecutionLedgerState.FINALIZED
                or entry.receipt is None
                or entry.receipt.classification != GoldTierExecutionClassification.SUCCESS
                or outcome is None
                or outcome.classification != GoldTierExecutionClassification.SUCCESS
                or outcome.party_id is None
                or outcome.readback_party_id != outcome.party_id
                or outcome.readback_status != "VERIFIED"
                or self.is_target_submission_active(submission_id)
            ):
                raise ValueError("Completed Sandbox verification is unavailable")
            expected = entry.submission_input.canonical_entity
            if (
                case.entity.registration_number != expected.registration_number
                or case.entity.legal_name != expected.legal_name
                or case.entity.country_of_incorporation != expected.country_of_incorporation
                or entry.resolved_party_id not in {None, outcome.party_id}
            ):
                raise ValueError("Completed Sandbox identity is no longer current")
            retained_id = str(outcome.party_id)
            result: Literal["VERIFIED", "REQUIRES_REVIEW", "UNAVAILABLE"] = "UNAVAILABLE"
            name = registration = country = None
            try:
                response = validate_search_response(self._goldtier.search_party(
                    XpiCustomerSearchRequest(goldtier_id=outcome.party_id),
                    self._metadata(
                        entry.submission_input, entry.submission_input.idempotency.search
                    ),
                ))
            except (ConnectorError, InvalidTargetResponseError):
                pass
            else:
                result = "REQUIRES_REVIEW"
                if (
                    response.outcome == GoldTierSearchOutcome.MATCH_FOUND
                    and len(response.candidates) == 1
                ):
                    candidate = response.candidates[0]
                    pairs = (
                        (candidate.legal_name, expected.legal_name),
                        (candidate.registration_number, expected.registration_number),
                        (candidate.country, expected.country_of_incorporation),
                    )
                    if str(candidate.party_id) == retained_id and all(
                        actual is not None and " ".join(actual.split()).casefold()
                        == " ".join(wanted.split()).casefold()
                        for actual, wanted in pairs
                    ):
                        result = "VERIFIED"
                        name, registration, country = (
                            candidate.legal_name, candidate.registration_number, candidate.country
                        )
            return CompletedTargetVerificationEvidence(
                submission_id=submission_id, goldtier_id=retained_id,
                checked_at=self._clock(), result=result, legal_name=name,
                registration_number=registration, country=country,
            )

    def check_uncertain_target_status(
        self,
        *,
        case_id: UUID,
        submission_id: UUID,
        reauthorize: Callable[[], None],
    ) -> TargetStatusCheckEvidence:
        """One bounded Search for the retained identity, with no mutation or recovery."""

        with self.case_lock(case_id):
            reauthorize()
            case = self._repository.get(case_id)
            entry = self.get_target_execution_entry(submission_id)
            if (
                self.target_provider_mode != GoldTierProviderMode.SANDBOX
                or self._goldtier.environment != GoldTierProviderMode.SANDBOX
                or case is None or case.entity is None or entry is None
                or entry.submission_input.provider_mode != GoldTierProviderMode.SANDBOX
                or entry.submission_input.case_id != case_id
                or not self.is_execution_outcome_uncertain(submission_id)
            ):
                raise ValueError(
                    "Read-only status checking requires the retained uncertain submission"
                )
            submission = entry.submission_input
            expected = submission.canonical_entity
            if (case.requested_uen != expected.registration_number
                    or case.entity.legal_name != expected.legal_name
                    or case.entity.country_of_incorporation != expected.country_of_incorporation):
                raise ValueError("Read-only status checking requires the frozen current identity")
            request = (
                XpiCustomerSearchRequest(goldtier_id=entry.resolved_party_id)
                if entry.resolved_party_id is not None
                else self._goldtier_mapper.build_search_request(submission)
            )
            verified_party_id: str | None = None
            try:
                response = validate_search_response(self._goldtier.search_party(
                    request, self._metadata(submission, submission.idempotency.search)
                ))
            except (ConnectorError, InvalidTargetResponseError):
                result: Literal[
                    "NO_MATCH", "IDENTITY_UNVERIFIED", "CUSTOMER_IDENTITY_VERIFIED",
                    "AMBIGUOUS", "CHECK_FAILED",
                ] = "CHECK_FAILED"
            else:
                if response.outcome == GoldTierSearchOutcome.NO_MATCH:
                    result = "NO_MATCH"
                elif response.outcome == GoldTierSearchOutcome.MULTIPLE_MATCHES:
                    result = "AMBIGUOUS"
                elif response.outcome != GoldTierSearchOutcome.MATCH_FOUND:
                    result = "CHECK_FAILED"
                elif len(response.candidates) != 1:
                    result = "IDENTITY_UNVERIFIED"
                else:
                    candidate = response.candidates[0]
                    pairs = (
                        (candidate.legal_name, expected.legal_name),
                        (candidate.registration_number, expected.registration_number),
                        (candidate.country, expected.country_of_incorporation),
                    )
                    exact = all(
                        actual is not None and " ".join(actual.split()).casefold()
                        == " ".join(wanted.split()).casefold()
                        for actual, wanted in pairs
                    ) and (
                        entry.resolved_party_id is None
                        or candidate.party_id == entry.resolved_party_id
                    )
                    result = "CUSTOMER_IDENTITY_VERIFIED" if exact else "IDENTITY_UNVERIFIED"
                    if exact:
                        verified_party_id = candidate.party_id
            return TargetStatusCheckEvidence(
                submission_id=submission_id, checked_at=self._clock(), result=result,
                verified_party_id=verified_party_id,
            )

    def target_recovery_operation(
        self, submission: GoldTierSubmissionInput,
    ) -> Literal["SHELL", "POLICY"] | None:
        """Presentation eligibility only; existing recovery owners validate evidence again."""
        with self.case_lock(submission.case_id):
            case = self._repository.get(submission.case_id)
            entry = self.get_target_execution_entry(submission.submission_id)
            if (
                case is None or case.entity is None or entry is None
                or entry.submission_input != submission
                or submission.provider_mode != GoldTierProviderMode.SANDBOX
                or self.target_provider_mode != submission.provider_mode
                or self._goldtier.environment != submission.provider_mode
                or not self.has_valid_target_dispatch_confirmation(case)
                or entry.state != GoldTierExecutionLedgerState.IN_PROGRESS
                or entry.target_outcome is not None or entry.receipt is not None
                or entry.provider_verified_amend_failure is not None
                or entry.search_resolution != GoldTierSearchResolution.NO_MATCH
            ):
                return None
            try:
                current = self.build_submission_input(case, provider_mode=submission.provider_mode)
            except ValueError:
                return None
            if (
                current.canonical_entity != submission.canonical_entity
                or current.target_policy != submission.target_policy
                or current.policy_catalogue_version != submission.policy_catalogue_version
            ):
                return None
            if (
                entry.attempted_operations == (
                    GoldTierOperationMarker.SEARCH, GoldTierOperationMarker.SHELL,
                )
                and entry.lifecycle_resolved_operations == (GoldTierOperationMarker.SEARCH,)
                and entry.resolved_party_id is None
            ):
                return "SHELL"
            if (
                entry.attempted_operations == (
                    GoldTierOperationMarker.SEARCH, GoldTierOperationMarker.SHELL,
                    GoldTierOperationMarker.POLICY,
                )
                and entry.lifecycle_resolved_operations == (
                    GoldTierOperationMarker.SEARCH, GoldTierOperationMarker.SHELL,
                )
                and entry.resolved_party_id is not None
                and case.goldtier_result is not None
                and case.goldtier_result.party_id == entry.resolved_party_id
                and entry.policy_status is None and entry.policy_id is None
                and submission.target_policy is not None
            ):
                return "POLICY"
            return None

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

    # ADR-017 section 3.7: re-confirmation and the "sent" predicate.

    RECONFIRMATION_EVENT = "DISPATCH_RECONFIRMATION_REQUIRED"

    @property
    def target_execution_repository(self) -> TargetExecutionRepository:
        return self._target_executions

    def case_is_sent(self, case_id: UUID) -> bool:
        """Sent = a Shell/Policy/Amend write attempt marker, or a retained target outcome or
        receipt. Never a confirmation, a TENTATIVE/AUTHORISED claim or a frozen snapshot.
        (Automation COMPLETE is the caller's third condition.)"""

        return any(
            has_write_marker(entry) or entry.target_outcome is not None
            or entry.receipt is not None
            for entry in self._target_executions.list_for_case(case_id)
        )

    def supersede_dispatch_confirmation(self, case_id: UUID) -> bool:
        """RD-3: a newly applicable requirement supersedes an existing confirmation.

        Under the case lock, and only while no write was started: the confirmation is
        removed (the frozen submission is kept) and the audit event records which
        confirmation was SUPERSEDED_BY_WORKFLOW_CHANGE. Returns whether it changed anything.
        """

        with self.case_lock(case_id):
            case = self.get_case(case_id)
            if case is None or case.target_dispatch_confirmation is None:
                return False
            if self.case_is_sent(case_id):
                return False
            superseded = case.target_dispatch_confirmation.confirmation_id
            updated = case.model_copy(deep=True)
            updated.target_dispatch_confirmation = None
            now = self._clock()
            updated.updated_at = now
            updated.events.append(
                WorkflowEvent(
                    sequence=len(updated.events) + 1,
                    stage=updated.state,
                    outcome=EventOutcome.SUCCEEDED,
                    timestamp=now,
                    case_id=updated.case_id,
                    correlation_id=updated.correlation_id,
                    code=self.RECONFIRMATION_EVENT,
                    message=(
                        f"Confirmation {superseded} SUPERSEDED_BY_WORKFLOW_CHANGE; confirm the "
                        "new workflow stage, then confirm the send again."
                    ),
                )
            )
            self._repository.save(OnboardingCase.model_validate(updated.model_dump()))
            return True

    def reconfirmation_required(self, case_id: UUID) -> bool:
        """True while the latest confirmation-related event is a supersession."""

        case = self.get_case(case_id)
        if case is None or case.target_dispatch_confirmation is not None:
            return False
        for event in reversed(case.events):
            if event.code == self.RECONFIRMATION_EVENT:
                return True
            if event.code == "TARGET_DISPATCH_CONFIRMED":
                return False
        return False

    def bind_registry_binding_hook(self, hook: Callable[[UUID], str]) -> None:
        """Bind ``WorkflowManagementService.freeze_onboarding_basis`` (ADR-018 §3.5)."""

        self._registry_binding_hook = hook

    def record_applicability_event(self, case_id: UUID, code: str) -> OnboardingCase:
        """ADR-018 §3.5 F6: append one case event through ``_record`` (revision-and-nonce
        compare-and-set) with a ``code`` string only. ``stage`` stays ``case.state``, the
        outcome is an existing value, and no case field changes. The run is the audit
        authority; this only makes it visible in case history."""

        messages = {
            CASE_EVENT_APPLICABILITY_BASIS_CONFLICT: (
                "Workflow applicability changed after the registry basis was frozen; "
                "an operator must apply all conditional steps before sending."
            ),
            CASE_EVENT_APPLICABILITY_ESCALATED: (
                "All conditional workflow steps now apply to this case."
            ),
        }
        if code not in messages:
            raise ValueError("unknown workflow applicability event")
        with self.case_lock(case_id):
            case = self._repository.get(case_id)
            if case is None:
                raise ValueError("Onboarding case was not found")
            outcome = (
                EventOutcome.SUCCEEDED
                if code == CASE_EVENT_APPLICABILITY_ESCALATED
                else EventOutcome.REVIEW_REQUIRED
            )
            self._record(case, case.state, outcome, messages[code], code)
            return case.model_copy(deep=True)

    def _after_registry_binding(self, case: OnboardingCase) -> None:
        """Run the basis hook after the committed REGISTRY_FETCHED write (F1, F5). A newly
        persisted conflict is also appended to case history (code string only)."""

        hook = self._registry_binding_hook
        if hook is None:
            return
        try:
            outcome = hook(case.case_id)
        except Exception:  # noqa: BLE001 - the hook fails safe (UNVERIFIED); never the case
            logging.getLogger(__name__).warning(
                "workflow basis hook failed", extra={"case_id": str(case.case_id)}
            )
            return
        if outcome == "CONFLICT_RECORDED":
            self._record(
                case,
                case.state,
                EventOutcome.REVIEW_REQUIRED,
                "Workflow applicability changed after the registry basis was frozen; "
                "an operator must apply all conditional steps before sending.",
                CASE_EVENT_APPLICABILITY_BASIS_CONFLICT,
            )

    def bind_dispatch_fence(self, fence: DispatchFence) -> None:
        """Bind the application's fence (its workflow store, send hold and health)."""

        self._dispatch_fence = fence

    def _fence(self) -> DispatchFence:
        if self._dispatch_fence is None:
            if not isinstance(self._target_executions, InMemoryTargetExecutionRepository):
                # A durable ledger without the application's fence is never dispatched.
                raise DispatchFenceRefusedError("WORKFLOW_STAGE_CHECK_UNAVAILABLE")
            self._dispatch_fence = default_memory_fence(self._target_executions, self._clock)
        return self._dispatch_fence

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
            if operation.value in WORKFLOW_DISPATCH_WRITE_OPERATIONS and not has_write_marker(
                entry
            ):
                # The first write attempt marker is recorded only by the fence (D1-D5).
                # A refusal raises before any provider call (D6 is the caller's next line).
                self._active_target_submissions.add(submission_input.submission_id)
                self._fence().authorise_first_write(
                    case_id=submission_input.case_id,
                    submission_id=submission_input.submission_id,
                    operation=operation,
                )
                return
            attempted = (*entry.attempted_operations, operation)
            self._active_target_submissions.add(submission_input.submission_id)
            candidate = GoldTierExecutionLedgerEntry(
                submission_input=entry.submission_input,
                workflow_dispatch=entry.workflow_dispatch,
                state=GoldTierExecutionLedgerState.IN_PROGRESS,
                attempted_operations=attempted,
                completed_operations=entry.completed_operations,
                resolved_operations=entry.resolved_operations,
                provider_verified_recovery=entry.provider_verified_recovery,
                provider_verified_policy_recovery=(entry.provider_verified_policy_recovery),
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
                candidate,
                expected_state=GoldTierExecutionLedgerState.IN_PROGRESS.value,
                expected_attempted=entry.attempted_operations,
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
                workflow_dispatch=entry.workflow_dispatch,
                state=GoldTierExecutionLedgerState.TARGET_OUTCOME_RECORDED,
                attempted_operations=entry.attempted_operations,
                completed_operations=definitive,
                resolved_operations=outcome.completed_operations,
                provider_verified_recovery=entry.provider_verified_recovery,
                provider_verified_policy_recovery=(entry.provider_verified_policy_recovery),
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
                candidate,
                expected_state=GoldTierExecutionLedgerState.IN_PROGRESS.value,
                expected_attempted=entry.attempted_operations,
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
                workflow_dispatch=entry.workflow_dispatch,
                state=GoldTierExecutionLedgerState.FINALIZED,
                attempted_operations=entry.attempted_operations,
                completed_operations=entry.completed_operations,
                resolved_operations=entry.resolved_operations,
                provider_verified_recovery=entry.provider_verified_recovery,
                provider_verified_policy_recovery=(entry.provider_verified_policy_recovery),
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
                expected_attempted=entry.attempted_operations,
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
            if (
                case is None or case.entity is None
                or case.entity.legal_name is None or case.entity.country_of_incorporation is None
            ):
                raise ValueError("Recovery requires the owning canonical case identity")
            if (
                submission_input.provider_mode != GoldTierProviderMode.SANDBOX
                or self.target_registry_evidence_refused(case)
            ):
                raise ValueError("Recovery requires accepted Sandbox submission evidence")
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
                or normalized(case.entity.legal_name) != normalized(expected.legal_name)
                or case.entity.registration_number.strip().upper()
                != expected.registration_number.strip().upper()
                or case.entity.country_of_incorporation.strip().upper()
                != expected.country_of_incorporation.strip().upper()
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
                if (
                    idempotent_recovery is None
                    and stored is not None
                    and (
                        stored.state != GoldTierExecutionLedgerState.IN_PROGRESS
                        or stored.attempted_operations
                        != (GoldTierOperationMarker.SEARCH, GoldTierOperationMarker.SHELL)
                        or stored.definitively_completed_operations
                        not in {(), (GoldTierOperationMarker.SEARCH,)}
                        or stored.search_resolution not in {None, GoldTierSearchResolution.NO_MATCH}
                        or stored.resolved_party_id is not None
                    )
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
                or not _readback_identity_matches(submission_input, result, recovered_party_id)
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
            if reauthorize is not None:
                reauthorize()
            candidate = GoldTierExecutionLedgerEntry(
                submission_input=submission_input.model_copy(deep=True),
                workflow_dispatch=None if stored is None else stored.workflow_dispatch,
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
                            expected_attempted=stored.attempted_operations,
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

        if (
            self.target_provider_mode != GoldTierProviderMode.SANDBOX
            or self._goldtier.environment != GoldTierProviderMode.SANDBOX
            or submission_input.provider_mode != GoldTierProviderMode.SANDBOX
        ):
            raise ValueError("Provider-verified recovery requires the GoldTier sandbox")
        if origin != GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER:
            raise ValueError("Policy recovery requires the retained uncertain ledger")
        with self.case_lock(submission_input.case_id):
            if reauthorize is not None:
                reauthorize()
            case = self._repository.get(submission_input.case_id)
            if case is None or case.entity is None:
                raise ValueError("Recovery requires the owning canonical case identity")
            if (
                submission_input.provider_mode != GoldTierProviderMode.SANDBOX
                or self.target_registry_evidence_refused(case)
            ):
                raise ValueError("Recovery requires accepted Sandbox submission evidence")
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
                or case.entity.legal_name is None
                or case.entity.country_of_incorporation is None
                or normalized(case.entity.legal_name) != normalized(expected.legal_name)
                or case.entity.registration_number.strip().upper()
                != expected.registration_number.strip().upper()
                or case.entity.country_of_incorporation.strip().upper()
                != expected.country_of_incorporation.strip().upper()
                or recovered_party_id.strip()
                != (case.goldtier_result.party_id if case.goldtier_result else None)
            ):
                raise ValueError("Recovery identity does not exactly match the owning case")
            target_policy = submission_input.target_policy
            if (
                target_policy is None
                or target_policy != case.policy_snapshot.goldtier_target
                or submission_input.policy_catalogue_version
                != case.policy_snapshot.catalogue_version
                or provider_policy != target_policy.policy.value
            ):
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
                    or not (
                        (
                            stored.definitively_completed_operations
                            == (GoldTierOperationMarker.SEARCH, GoldTierOperationMarker.SHELL)
                            and stored.provider_verified_recovery is None
                            and stored.shell_status == "SHELL_CREATED"
                            and case.goldtier_result is not None
                            and case.goldtier_result.shell_status == "SHELL_CREATED"
                        )
                        or (
                            stored.definitively_completed_operations
                            == (GoldTierOperationMarker.SEARCH,)
                            and stored.provider_verified_recovery is not None
                            and stored.provider_verified_recovery.operation
                            == GoldTierOperationMarker.SHELL
                            and stored.shell_status == "PROVIDER_VERIFIED_RECOVERY"
                            and case.goldtier_result is not None
                            and case.goldtier_result.shell_status == "PROVIDER_VERIFIED_RECOVERY"
                        )
                    )
                    or stored.lifecycle_resolved_operations
                    != (GoldTierOperationMarker.SEARCH, GoldTierOperationMarker.SHELL)
                    or stored.search_resolution != GoldTierSearchResolution.NO_MATCH
                    or stored.resolved_party_id != recovered_party_id
                    or stored.policy_id is not None
                    or stored.policy_status is not None
                    or stored.target_outcome is not None
                    or stored.receipt is not None
                    or case.goldtier_result is None
                    or case.goldtier_result.policy_id is not None
                    or case.goldtier_result.policy_status is not None
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
                workflow_dispatch=stored.workflow_dispatch,
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
                        expected_attempted=stored.attempted_operations,
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
                    raise ValueError("A conflicting provider Amend failure is already retained")
                if (
                    stored.state != GoldTierExecutionLedgerState.IN_PROGRESS
                    or stored.attempted_operations
                    != (
                        GoldTierOperationMarker.SEARCH,
                        GoldTierOperationMarker.SHELL,
                        GoldTierOperationMarker.POLICY,
                        GoldTierOperationMarker.AMEND,
                    )
                    or stored.definitively_completed_operations != (GoldTierOperationMarker.SEARCH,)
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
                        # Excluded from dumps; a copy must still carry the claim.
                        "workflow_dispatch": stored.workflow_dispatch,
                    }
                )
                try:
                    self._target_executions.replace(
                        candidate,
                        expected_state=GoldTierExecutionLedgerState.IN_PROGRESS.value,
                        expected_attempted=stored.attempted_operations,
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
                if (
                    resolution.outcome == EntityResolutionOutcome.EXACT_MATCH
                    and resolution.selected_candidate_id is not None
                    and self._mock_reuse_is_verified(
                        submission_input, resolution.selected_candidate_id, search.candidates[0]
                    )
                ):
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
                policy = validate_policy_response(untrusted_policy, expected_party_id=party_id)
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

        amend_status = "AMEND_NOT_REQUIRED"
        if self._goldtier_mapper.requires_amend(submission_input):
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
            amend_status = amend.status
        readback_party_id: str | None = None
        readback_status: str | None = None
        if submission_input.provider_mode in {
            GoldTierProviderMode.MOCK, GoldTierProviderMode.SANDBOX,
        }:
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
                    amend_status=amend_status,
                    error_code=code,
                    error_message=message,
                    infrastructure_failure=True,
                ),
                operation=lambda: self._goldtier.search_party(
                    self._goldtier_mapper.build_readback_request(submission_input, party_id),
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
            verified = _readback_identity_matches(submission_input, readback, party_id)
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
                    amend_status=amend_status,
                    error_code=code,
                    error_message=message,
                )
                case.goldtier_result.amend_status = amend_status
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
            amend_status=amend_status,
            readback_party_id=readback_party_id,
            readback_status=readback_status,
        )
        case.goldtier_result.amend_status = amend_status
        case.goldtier_result.readback_party_id = readback_party_id
        case.goldtier_result.readback_status = readback_status
        self._record(
            case,
            WorkflowState.GT_ENRICHED,
            EventOutcome.SUCCEEDED,
            "GoldTier target submission completed.",
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
            if candidate_entity != case.entity:
                # This binding attests equality to the original acquired entity.
                # Keep that evidence immutable when an authorized decision changes it.
                candidate.registry_evidence_binding = None
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
