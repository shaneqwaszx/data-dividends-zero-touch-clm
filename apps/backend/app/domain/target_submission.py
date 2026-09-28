"""Immutable provider-neutral input and safe receipt for target submission."""

from datetime import UTC, date, datetime
from enum import StrEnum

from pydantic import UUID4, BaseModel, ConfigDict, Field, model_validator

from app.domain.models import WorkflowState
from app.domain.policy import GoldTierTargetPolicySnapshot
from app.domain.target_safety import (
    SafeTargetErrorCode,
    SafeTargetIdentifier,
    SafeTargetMessage,
    SafeTargetStatus,
)

_NEW_PARTY_OPERATION_ORDER = ("SEARCH", "SHELL", "POLICY", "AMEND", "READBACK")
_EXISTING_PARTY_OPERATION_ORDER = ("SEARCH", "AMEND", "READBACK")


def _is_valid_operation_prefix(
    operations: tuple["GoldTierOperationMarker", ...],
) -> bool:
    values = tuple(item.value for item in operations)
    return values in {
        _NEW_PARTY_OPERATION_ORDER[: len(values)],
        _EXISTING_PARTY_OPERATION_ORDER[: len(values)],
    }


def _is_ordered_operation_subsequence(
    operations: tuple["GoldTierOperationMarker", ...],
    attempted: tuple["GoldTierOperationMarker", ...],
) -> bool:
    """Return whether definitive outcomes preserve attempted-operation order."""

    iterator = iter(attempted)
    return all(any(candidate == operation for candidate in iterator) for operation in operations)


class SubmissionRegisteredAddress(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    address_line_1: str
    address_line_2: str | None = None
    postal_code: str
    country_code: str = "SG"


class SubmissionCanonicalEntity(BaseModel):
    """Canonical business fields allowed to cross the Mock target boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    registration_number: str
    legal_name: str
    country_of_incorporation: str
    party_type: str
    registration_date: date | None = None
    entity_status: str | None = None
    registered_address: SubmissionRegisteredAddress


class GoldTierIdempotencyBindings(BaseModel):
    """Stable per-operation identifiers retained with one logical submission."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    search: UUID4
    shell: UUID4
    policy: UUID4
    amend: UUID4


class GoldTierProviderMode(StrEnum):
    MOCK = "MOCK"
    SANDBOX = "SANDBOX"


class GoldTierProviderClassification(StrEnum):
    MOCK = "MOCK"
    SANDBOX_PARTIAL = "SANDBOX_PARTIAL"


class GoldTierSubmissionInput(BaseModel):
    """Exact immutable business and identifier input consumed by target mappers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    submission_id: UUID4
    case_id: UUID4
    source_case_id: str = Field(min_length=1, max_length=96)
    correlation_id: UUID4
    accepted_at: datetime
    provider_mode: GoldTierProviderMode = GoldTierProviderMode.MOCK
    policy_catalogue_version: int = Field(default=0, ge=0)
    target_external_key: str | None = Field(default=None, min_length=1, max_length=96)
    target_policy: GoldTierTargetPolicySnapshot | None = None
    canonical_entity: SubmissionCanonicalEntity
    idempotency: GoldTierIdempotencyBindings


class GoldTierExecutionClassification(StrEnum):
    SUCCESS = "SUCCESS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAILED = "FAILED"


class GoldTierExecutionLedgerState(StrEnum):
    """Process-local lifecycle for one immutable logical target submission."""

    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    TARGET_OUTCOME_RECORDED = "TARGET_OUTCOME_RECORDED"
    FINALIZED = "FINALIZED"


class GoldTierOperationMarker(StrEnum):
    SEARCH = "SEARCH"
    SHELL = "SHELL"
    POLICY = "POLICY"
    AMEND = "AMEND"
    READBACK = "READBACK"


class GoldTierRecoveryAuthority(StrEnum):
    PROVIDER_VERIFIED_RECOVERY = "PROVIDER_VERIFIED_RECOVERY"


class GoldTierRecoveryOrigin(StrEnum):
    UNCERTAIN_DURABLE_LEDGER = "UNCERTAIN_DURABLE_LEDGER"
    HISTORICAL_LOCAL_LEDGER_LOST = "HISTORICAL_LOCAL_LEDGER_LOST"


class GoldTierProviderReconciliation(StrEnum):
    PROVIDER_VERIFIED_FAILURE = "PROVIDER_VERIFIED_FAILURE"


class GoldTierProviderFailureStatus(StrEnum):
    PROVIDER_VALIDATION_FAILED = "PROVIDER_VALIDATION_FAILED"


class ProviderVerifiedRecovery(BaseModel):
    """Auditable provider evidence that resolves one uncertain operation without replay."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    authority: GoldTierRecoveryAuthority = (
        GoldTierRecoveryAuthority.PROVIDER_VERIFIED_RECOVERY
    )
    origin: GoldTierRecoveryOrigin
    operation: GoldTierOperationMarker = GoldTierOperationMarker.SHELL
    recovered_party_id: SafeTargetIdentifier
    legal_name: str = Field(min_length=1, max_length=300)
    registration_number: str = Field(min_length=1, max_length=32)
    country_of_incorporation: str = Field(min_length=2, max_length=3)
    actor_id: str = Field(min_length=1, max_length=96)
    verified_at: datetime
    candidate_count: int = Field(ge=1, le=1)
    provider_policy: SafeTargetMessage | None = None
    provider_policy_status: SafeTargetMessage | None = None
    original_outcome_uncertain: bool = True
    replayed: bool = False

    @model_validator(mode="after")
    def validate_recovery(self) -> "ProviderVerifiedRecovery":
        if self.operation not in {
            GoldTierOperationMarker.SHELL,
            GoldTierOperationMarker.POLICY,
        }:
            raise ValueError("Provider recovery may resolve only Shell or Policy")
        if self.operation == GoldTierOperationMarker.POLICY:
            if self.provider_policy is None or self.provider_policy_status is None:
                raise ValueError("Policy recovery requires provider policy evidence")
        elif self.provider_policy is not None or self.provider_policy_status is not None:
            raise ValueError("Shell recovery cannot contain provider policy evidence")
        if not self.original_outcome_uncertain or self.replayed:
            raise ValueError("Provider recovery must retain uncertain/no-replay history")
        if self.verified_at.tzinfo is None or self.verified_at.utcoffset() != UTC.utcoffset(
            self.verified_at
        ):
            raise ValueError("Provider recovery timestamp must be timezone-aware UTC")
        return self


class ProviderVerifiedFailure(BaseModel):
    """Safe provider evidence resolving an uncertain mutation as failed, not complete."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: GoldTierOperationMarker = GoldTierOperationMarker.AMEND
    provider_reconciliation: GoldTierProviderReconciliation = (
        GoldTierProviderReconciliation.PROVIDER_VERIFIED_FAILURE
    )
    origin: GoldTierRecoveryOrigin = GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER
    provider_status: GoldTierProviderFailureStatus
    provider_status_evidence: SafeTargetMessage
    recovered_party_id: SafeTargetIdentifier
    actor_id: str = Field(min_length=1, max_length=96)
    verified_at: datetime
    original_outcome_uncertain: bool = True
    replayed: bool = False

    @model_validator(mode="after")
    def validate_failure(self) -> "ProviderVerifiedFailure":
        if self.operation != GoldTierOperationMarker.AMEND:
            raise ValueError("Provider failure reconciliation currently supports only Amend")
        if not self.original_outcome_uncertain or self.replayed:
            raise ValueError("Provider failure must retain uncertain/no-replay history")
        if self.verified_at.tzinfo is None or self.verified_at.utcoffset() != UTC.utcoffset(
            self.verified_at
        ):
            raise ValueError("Provider failure timestamp must be timezone-aware UTC")
        return self


class GoldTierSearchResolution(StrEnum):
    """Trusted disposition carried from the early read-only Search checkpoint."""

    NO_MATCH = "NO_MATCH"
    EXACT_MATCH = "EXACT_MATCH"


class GoldTierTargetOutcome(BaseModel):
    """Minimal trusted target facts retained before rich receipt mapping."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    submission_id: UUID4
    case_id: UUID4
    correlation_id: UUID4
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    idempotency_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    classification: GoldTierExecutionClassification
    onboarding_state: WorkflowState
    completed_operations: tuple[GoldTierOperationMarker, ...] = Field(max_length=5)
    party_id: SafeTargetIdentifier | None = None
    shell_status: SafeTargetStatus | None = None
    policy_id: SafeTargetIdentifier | None = None
    policy_status: SafeTargetStatus | None = None
    amend_status: SafeTargetStatus | None = None
    readback_party_id: SafeTargetIdentifier | None = None
    readback_status: SafeTargetStatus | None = None
    error_code: SafeTargetErrorCode | None = None
    error_message: SafeTargetMessage | None = None
    infrastructure_failure: bool = False

    @model_validator(mode="after")
    def validate_terminal_shape(self) -> "GoldTierTargetOutcome":
        if not self.completed_operations or not _is_valid_operation_prefix(
            self.completed_operations
        ):
            raise ValueError("Target operation markers must form an ordered prefix")
        if self.classification == GoldTierExecutionClassification.SUCCESS:
            if self.error_code is not None or self.error_message is not None:
                raise ValueError("Successful target outcome cannot contain an error")
            if self.party_id is None or self.shell_status is None:
                raise ValueError("Successful target outcome requires safe target identifiers")
            if self.onboarding_state not in {
                WorkflowState.GT_ENRICHED,
                WorkflowState.COMPLETED,
            }:
                raise ValueError("Successful target outcome has an invalid terminal state")
        elif self.error_code is None or self.error_message is None:
            raise ValueError("Non-success target outcome requires a safe error")
        elif (
            self.classification == GoldTierExecutionClassification.REVIEW_REQUIRED
            and self.onboarding_state != WorkflowState.REVIEW_REQUIRED
        ):
            raise ValueError("Review target outcome has an invalid terminal state")
        elif (
            self.classification == GoldTierExecutionClassification.FAILED
            and self.onboarding_state != WorkflowState.FAILED
        ):
            raise ValueError("Failed target outcome has an invalid terminal state")
        if (
            self.infrastructure_failure
            and self.classification != GoldTierExecutionClassification.FAILED
        ):
            raise ValueError("Infrastructure failure must be a failed target outcome")
        if self.readback_party_id is not None and self.readback_party_id != self.party_id:
            raise ValueError("GoldTier read-back identity must match the retained party")
        if (
            self.classification == GoldTierExecutionClassification.SUCCESS
            and GoldTierOperationMarker.READBACK in self.completed_operations
            and (
            self.readback_party_id is None or self.readback_status is None
            )
        ):
            raise ValueError("Completed GoldTier read-back requires retained equality evidence")
        if (
            self.readback_party_id is not None
            and GoldTierOperationMarker.READBACK not in self.completed_operations
        ):
            raise ValueError("Retained GoldTier read-back requires a completed read-back operation")
        return self


class GoldTierExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    party_id: SafeTargetIdentifier
    shell_status: SafeTargetStatus
    policy_id: SafeTargetIdentifier | None = None
    policy_status: SafeTargetStatus | None = None
    amend_status: SafeTargetStatus | None = None
    readback_party_id: SafeTargetIdentifier | None = None
    readback_status: SafeTargetStatus | None = None


class GoldTierExecutionError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: SafeTargetErrorCode
    message: SafeTargetMessage


class GoldTierExecutionReceipt(BaseModel):
    """Safe process-local proof that target execution reached a terminal outcome."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    submission_id: UUID4
    case_id: UUID4
    correlation_id: UUID4
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    classification: GoldTierExecutionClassification
    onboarding_state: WorkflowState
    result: GoldTierExecutionResult | None = None
    error: GoldTierExecutionError | None = None
    infrastructure_failure: bool = False


class GoldTierExecutionLedgerEntry(BaseModel):
    """Defensive process-local state for one target execution identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    submission_input: GoldTierSubmissionInput
    state: GoldTierExecutionLedgerState
    attempted_operations: tuple[GoldTierOperationMarker, ...] = Field(default=(), max_length=5)
    completed_operations: tuple[GoldTierOperationMarker, ...] | None = Field(
        default=None, max_length=5
    )
    resolved_operations: tuple[GoldTierOperationMarker, ...] | None = Field(
        default=None, max_length=5
    )
    provider_verified_recovery: ProviderVerifiedRecovery | None = None
    provider_verified_policy_recovery: ProviderVerifiedRecovery | None = None
    provider_verified_amend_failure: ProviderVerifiedFailure | None = None
    search_resolution: GoldTierSearchResolution | None = None
    resolved_party_id: SafeTargetIdentifier | None = None
    shell_status: SafeTargetStatus | None = None
    policy_id: SafeTargetIdentifier | None = None
    policy_status: SafeTargetStatus | None = None
    amend_status: SafeTargetStatus | None = None
    readback_party_id: SafeTargetIdentifier | None = None
    readback_status: SafeTargetStatus | None = None
    target_outcome: GoldTierTargetOutcome | None = None
    receipt: GoldTierExecutionReceipt | None = None

    @model_validator(mode="after")
    def validate_lifecycle_shape(self) -> "GoldTierExecutionLedgerEntry":
        if not _is_valid_operation_prefix(self.attempted_operations):
            raise ValueError("Attempted target operations must form an ordered prefix")
        completed = self.completed_operations
        if completed is not None and not _is_ordered_operation_subsequence(
            completed, self.attempted_operations
        ):
            raise ValueError("Completed operations must preserve attempted-operation order")
        resolved = self.resolved_operations
        if resolved is not None:
            if not _is_valid_operation_prefix(resolved):
                raise ValueError("Resolved target operations must form an ordered prefix")
            if resolved != self.attempted_operations[: len(resolved)]:
                raise ValueError("Resolved operations must be a prefix of attempted operations")
        recoveries = self.provider_verified_recoveries
        if self.provider_verified_recovery is not None and (
            self.provider_verified_recovery.operation != GoldTierOperationMarker.SHELL
        ):
            raise ValueError("Shell recovery field must contain a Shell recovery")
        if self.provider_verified_policy_recovery is not None and (
            self.provider_verified_policy_recovery.operation
            != GoldTierOperationMarker.POLICY
        ):
            raise ValueError("Policy recovery field must contain a Policy recovery")
        if len({item.operation for item in recoveries}) != len(recoveries):
            raise ValueError("Provider recovery operations must be unique")
        for recovery in recoveries:
            if recovery.operation not in self.attempted_operations:
                raise ValueError("Provider recovery requires the original attempted operation")
            if recovery.operation in (completed or ()):
                raise ValueError("Provider recovery cannot overwrite a definitive outcome")
            if resolved is None or recovery.operation not in resolved:
                raise ValueError("Provider recovery must resolve the uncertain operation")
            if self.resolved_party_id != recovery.recovered_party_id:
                raise ValueError("Provider recovery must match the retained target identity")
        recovered_operations = tuple(item.operation for item in recoveries)
        resolved_without_definitive = tuple(
            operation for operation in (resolved or ()) if operation not in (completed or ())
        )
        if resolved_without_definitive != recovered_operations:
            raise ValueError("Only matching provider recovery may resolve an uncompleted operation")
        failure = self.provider_verified_amend_failure
        if failure is not None:
            if self.state != GoldTierExecutionLedgerState.IN_PROGRESS:
                raise ValueError("Provider-verified failure requires an in-progress ledger")
            if failure.operation not in self.attempted_operations:
                raise ValueError("Provider-verified failure requires the attempted operation")
            if failure.operation in self.lifecycle_resolved_operations:
                raise ValueError("Provider-verified failure cannot mark Amend resolved")
            if failure.operation in self.definitively_completed_operations:
                raise ValueError("Provider-verified failure cannot mark Amend complete")
            if self.attempted_operations[-1] != GoldTierOperationMarker.AMEND:
                raise ValueError("Provider-verified Amend failure must be the stopped operation")
            if self.resolved_party_id != failure.recovered_party_id:
                raise ValueError(
                    "Provider-verified failure must match the retained target identity"
                )
            if self.target_outcome is not None or self.receipt is not None:
                raise ValueError(
                    "Provider-verified failure cannot contain a terminal success record"
                )
        if self.search_resolution is not None and (
            not self.attempted_operations
            or self.attempted_operations[0] != GoldTierOperationMarker.SEARCH
        ):
            raise ValueError("Search resolution requires an attempted Search")
        if self.search_resolution == GoldTierSearchResolution.EXACT_MATCH and (
            self.resolved_party_id is None or self.shell_status is None
        ):
            raise ValueError("Exact Search resolution requires the retained target identity")
        if (
            self.search_resolution == GoldTierSearchResolution.NO_MATCH
            and self.resolved_party_id is not None
            and GoldTierOperationMarker.SHELL not in self.lifecycle_resolved_operations
        ):
            raise ValueError("No-match Search resolution cannot retain a target identity")
        if self.policy_id is not None and self.resolved_party_id is None:
            raise ValueError("Policy progress requires a resolved target identity")
        if (
            self.amend_status is not None
            and self.policy_status is None
            and self.shell_status != "EXISTING_PARTY_REUSED"
        ):
            raise ValueError("Amend progress requires policy progress")
        if self.readback_party_id is not None and self.readback_party_id != self.resolved_party_id:
            raise ValueError("Read-back progress must match the resolved target identity")
        if self.readback_status is not None and self.readback_party_id is None:
            raise ValueError("Read-back status requires a retained target identity")
        if self.state == GoldTierExecutionLedgerState.IN_PROGRESS:
            if self.target_outcome is not None or self.receipt is not None:
                raise ValueError("In-progress execution cannot have a terminal outcome")
        elif self.state == GoldTierExecutionLedgerState.TARGET_OUTCOME_RECORDED:
            if self.target_outcome is None or self.receipt is not None:
                raise ValueError("Recorded target outcome cannot contain a rich receipt")
        elif self.state == GoldTierExecutionLedgerState.FINALIZED and (
            self.target_outcome is None or self.receipt is None
        ):
            raise ValueError("Finalized execution requires outcome and receipt")
        if (
            self.target_outcome is not None
            and self.lifecycle_resolved_operations
            != self.target_outcome.completed_operations
        ):
            raise ValueError("Ledger operations must match the retained target outcome")
        if (
            self.target_outcome is not None
            and self.lifecycle_resolved_operations != self.attempted_operations
        ):
            raise ValueError("Terminal ledger operations must be lifecycle-resolved")
        return self

    @property
    def definitively_completed_operations(self) -> tuple[GoldTierOperationMarker, ...]:
        """Treat legacy terminal rows as complete while leaving old in-flight rows uncertain."""

        if self.completed_operations is not None:
            return self.completed_operations
        if self.target_outcome is not None:
            return self.attempted_operations
        return ()

    @property
    def lifecycle_resolved_operations(self) -> tuple[GoldTierOperationMarker, ...]:
        """Operations safe to advance past, including provider-verified recoveries."""

        if self.resolved_operations is not None:
            return self.resolved_operations
        return self.definitively_completed_operations

    @property
    def provider_verified_recoveries(self) -> tuple[ProviderVerifiedRecovery, ...]:
        """Return retained recovery facts in target-operation order."""

        return tuple(
            item
            for item in (
                self.provider_verified_recovery,
                self.provider_verified_policy_recovery,
            )
            if item is not None
        )

    def provider_recovery_for(
        self, operation: GoldTierOperationMarker
    ) -> ProviderVerifiedRecovery | None:
        return next(
            (item for item in self.provider_verified_recoveries if item.operation == operation),
            None,
        )
