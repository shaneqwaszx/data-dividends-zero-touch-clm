"""Immutable provider-neutral input and safe receipt for target submission."""

from datetime import date, datetime
from enum import StrEnum

from pydantic import UUID4, BaseModel, ConfigDict, Field, model_validator

from app.domain.models import WorkflowState
from app.domain.target_safety import (
    SafeTargetErrorCode,
    SafeTargetIdentifier,
    SafeTargetMessage,
    SafeTargetStatus,
)


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


class GoldTierSubmissionInput(BaseModel):
    """Exact immutable business and identifier input consumed by target mappers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    submission_id: UUID4
    case_id: UUID4
    source_case_id: str = Field(min_length=1, max_length=96)
    correlation_id: UUID4
    accepted_at: datetime
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
    completed_operations: tuple[GoldTierOperationMarker, ...] = Field(max_length=4)
    party_id: SafeTargetIdentifier | None = None
    shell_status: SafeTargetStatus | None = None
    policy_id: SafeTargetIdentifier | None = None
    policy_status: SafeTargetStatus | None = None
    amend_status: SafeTargetStatus | None = None
    error_code: SafeTargetErrorCode | None = None
    error_message: SafeTargetMessage | None = None
    infrastructure_failure: bool = False

    @model_validator(mode="after")
    def validate_terminal_shape(self) -> "GoldTierTargetOutcome":
        operation_order = (
            GoldTierOperationMarker.SEARCH,
            GoldTierOperationMarker.SHELL,
            GoldTierOperationMarker.POLICY,
            GoldTierOperationMarker.AMEND,
        )
        if not self.completed_operations or self.completed_operations != operation_order[
            : len(self.completed_operations)
        ]:
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
        return self


class GoldTierExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    party_id: SafeTargetIdentifier
    shell_status: SafeTargetStatus
    policy_id: SafeTargetIdentifier | None = None
    policy_status: SafeTargetStatus | None = None
    amend_status: SafeTargetStatus | None = None


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
    attempted_operations: tuple[GoldTierOperationMarker, ...] = Field(
        default=(), max_length=4
    )
    target_outcome: GoldTierTargetOutcome | None = None
    receipt: GoldTierExecutionReceipt | None = None

    @model_validator(mode="after")
    def validate_lifecycle_shape(self) -> "GoldTierExecutionLedgerEntry":
        operation_order = (
            GoldTierOperationMarker.SEARCH,
            GoldTierOperationMarker.SHELL,
            GoldTierOperationMarker.POLICY,
            GoldTierOperationMarker.AMEND,
        )
        if self.attempted_operations != operation_order[: len(self.attempted_operations)]:
            raise ValueError("Attempted target operations must form an ordered prefix")
        if self.state == GoldTierExecutionLedgerState.IN_PROGRESS:
            if self.target_outcome is not None or self.receipt is not None:
                raise ValueError("In-progress execution cannot have a terminal outcome")
        elif self.state == GoldTierExecutionLedgerState.TARGET_OUTCOME_RECORDED:
            if self.target_outcome is None or self.receipt is not None:
                raise ValueError("Recorded target outcome cannot contain a rich receipt")
        elif (
            self.state == GoldTierExecutionLedgerState.FINALIZED
            and (self.target_outcome is None or self.receipt is None)
        ):
            raise ValueError("Finalized execution requires outcome and receipt")
        if (
            self.target_outcome is not None
            and self.attempted_operations != self.target_outcome.completed_operations
        ):
            raise ValueError("Ledger operations must match the retained target outcome")
        return self
