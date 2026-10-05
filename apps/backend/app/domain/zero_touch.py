"""Source-neutral zero-touch automation, exception, and metric models."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain.models import EventOutcome, SafeError

ZERO_TOUCH_POLICY_VERSION = "PHASE_06_POC_V1"
LEGACY_AUTOMATION_STAGE_ORDER_VERSION: Literal[1] = 1
AUTOMATION_STAGE_ORDER_VERSION: Literal[2] = 2
LEGACY_AUTOMATION_STAGE_ORDER = (
    "REGISTRY",
    "DOCUMENT",
    "OWNERSHIP",
    "READINESS",
    "MOCK_GOLDTIER",
)
AUTOMATION_STAGE_ORDER = (
    "REGISTRY",
    "GOLDTIER_SEARCH",
    "DOCUMENT",
    "OWNERSHIP",
    "READINESS",
    "MOCK_GOLDTIER",
)


class AutomationStatus(StrEnum):
    PENDING_INPUTS = "PENDING_INPUTS"
    RUNNING = "RUNNING"
    WAITING_FOR_REVIEW = "WAITING_FOR_REVIEW"
    RESUMING = "RESUMING"
    RECOVERY_PENDING = "RECOVERY_PENDING"
    COMPLETED = "COMPLETED"
    TECHNICAL_FAILURE = "TECHNICAL_FAILURE"


class AutomationStage(StrEnum):
    REGISTRY = "REGISTRY"
    GOLDTIER_SEARCH = "GOLDTIER_SEARCH"
    DOCUMENT = "DOCUMENT"
    OWNERSHIP = "OWNERSHIP"
    READINESS = "READINESS"
    MOCK_GOLDTIER = "MOCK_GOLDTIER"
    COMPLETE = "COMPLETE"


class BusinessExceptionType(StrEnum):
    REGISTRY_REVIEW_REQUIRED = "REGISTRY_REVIEW_REQUIRED"
    JURISDICTION_UNRESOLVED = "JURISDICTION_UNRESOLVED"
    JURISDICTION_CONFLICT = "JURISDICTION_CONFLICT"
    REGISTRY_PROVIDER_NOT_IMPLEMENTED = "REGISTRY_PROVIDER_NOT_IMPLEMENTED"
    REGISTRY_IDENTIFIER_NOT_ELIGIBLE = "REGISTRY_IDENTIFIER_NOT_ELIGIBLE"
    DOCUMENT_SOURCE_CONFLICT = "DOCUMENT_SOURCE_CONFLICT"
    DOCUMENT_LOW_CONFIDENCE = "DOCUMENT_LOW_CONFIDENCE"
    DOCUMENT_REQUIRED_FIELD_MISSING = "DOCUMENT_REQUIRED_FIELD_MISSING"
    DOCUMENT_REVIEW_REQUIRED = "DOCUMENT_REVIEW_REQUIRED"
    RECONCILIATION_INVALID = "RECONCILIATION_INVALID"
    OWNERSHIP_CYCLE = "OWNERSHIP_CYCLE"
    OWNERSHIP_INCOMPLETE = "OWNERSHIP_INCOMPLETE"
    OWNERSHIP_REVIEW_REQUIRED = "OWNERSHIP_REVIEW_REQUIRED"
    MOCK_RISK_REVIEW_REQUIRED = "MOCK_RISK_REVIEW_REQUIRED"
    ENTITY_RESOLUTION_REVIEW_REQUIRED = "ENTITY_RESOLUTION_REVIEW_REQUIRED"
    EXISTING_PARTY_REVIEW_REQUIRED = "EXISTING_PARTY_REVIEW_REQUIRED"
    TARGET_PARTIAL_REVIEW_REQUIRED = "TARGET_PARTIAL_REVIEW_REQUIRED"
    TARGET_CLASSIFICATION_REQUIRED = "TARGET_CLASSIFICATION_REQUIRED"
    TARGET_CONFIRMATION_REQUIRED = "TARGET_CONFIRMATION_REQUIRED"


class BusinessExceptionStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


class ExceptionResolutionAction(StrEnum):
    KEEP_REGISTRY_VALUE = "KEEP_REGISTRY_VALUE"
    USE_DOCUMENT_VALUE = "USE_DOCUMENT_VALUE"
    REQUEST_ADDITIONAL_INFORMATION = "REQUEST_ADDITIONAL_INFORMATION"


class BlockerDecisionClassification(StrEnum):
    AUTO_RESOLVED_WITH_NOTE = "AUTO_RESOLVED_WITH_NOTE"
    CONTINUE_WITH_WARNING = "CONTINUE_WITH_WARNING"
    USER_ACTION_REQUIRED = "USER_ACTION_REQUIRED"
    EXTERNAL_DEPENDENCY = "EXTERNAL_DEPENDENCY"
    HARD_STOP = "HARD_STOP"


class BlockerDecisionOwner(StrEnum):
    CASE_OPERATOR = "CASE_OPERATOR"
    DOCUMENT_REVIEW_OWNER = "DOCUMENT_REVIEW_OWNER"
    IDENTITY_REVIEW_OWNER = "IDENTITY_REVIEW_OWNER"
    REGISTRY_INTEGRATION_OWNER = "REGISTRY_INTEGRATION_OWNER"
    OWNERSHIP_REVIEW_OWNER = "OWNERSHIP_REVIEW_OWNER"
    POLICY_OWNER = "POLICY_OWNER"
    TARGET_OPERATIONS_OWNER = "TARGET_OPERATIONS_OWNER"
    TARGET_PROVIDER_OWNER = "TARGET_PROVIDER_OWNER"


class BlockerDecisionAction(StrEnum):
    ESCALATE_TO_OWNER = "ESCALATE_TO_OWNER"
    CORRECT_INITIAL_IDENTITY = "CORRECT_INITIAL_IDENTITY"
    RESOLVE_JURISDICTION_EVIDENCE = "RESOLVE_JURISDICTION_EVIDENCE"
    RUN_READ_ONLY_SEARCH_RECHECK = "RUN_READ_ONLY_SEARCH_RECHECK"
    CONFIRM_EXISTING_GOLDTIER_CUSTOMER = "CONFIRM_EXISTING_GOLDTIER_CUSTOMER"
    REVIEW_ENTITY_IDENTITY = "REVIEW_ENTITY_IDENTITY"
    PROVIDE_REGISTRY_EVIDENCE = "PROVIDE_REGISTRY_EVIDENCE"
    ENABLE_SUPPORTED_REGISTRY_PROVIDER = "ENABLE_SUPPORTED_REGISTRY_PROVIDER"
    UPLOAD_DOCUMENT = "UPLOAD_DOCUMENT"
    UPLOAD_REPLACEMENT_DOCUMENT = "UPLOAD_REPLACEMENT_DOCUMENT"
    COMPLETE_DOCUMENT_REVIEW = "COMPLETE_DOCUMENT_REVIEW"
    KEEP_REGISTRY_VALUE = "KEEP_REGISTRY_VALUE"
    USE_DOCUMENT_VALUE = "USE_DOCUMENT_VALUE"
    REQUEST_ADDITIONAL_INFORMATION = "REQUEST_ADDITIONAL_INFORMATION"
    PROVIDE_CORRECTED_OWNERSHIP_EVIDENCE = "PROVIDE_CORRECTED_OWNERSHIP_EVIDENCE"
    RERUN_OWNERSHIP_ANALYSIS = "RERUN_OWNERSHIP_ANALYSIS"
    REVIEW_MOCK_RISK = "REVIEW_MOCK_RISK"
    SELECT_TARGET_CLASSIFICATION = "SELECT_TARGET_CLASSIFICATION"
    CONFIRM_FROZEN_TARGET_SUBMISSION = "CONFIRM_FROZEN_TARGET_SUBMISSION"
    VERIFY_TARGET_OUTCOME_WITHOUT_REPLAY = "VERIFY_TARGET_OUTCOME_WITHOUT_REPLAY"
    DIAGNOSE_PROVIDER_VALIDATION = "DIAGNOSE_PROVIDER_VALIDATION"
    FINALIZE_RETAINED_TARGET_OUTCOME = "FINALIZE_RETAINED_TARGET_OUTCOME"
    WAIT_FOR_CURRENT_PROCESSING = "WAIT_FOR_CURRENT_PROCESSING"
    RETAIN_INDEPENDENT_EVIDENCE_ONLY = "RETAIN_INDEPENDENT_EVIDENCE_ONLY"
    RETAIN_SUPERSESSION_NOTE = "RETAIN_SUPERSESSION_NOTE"
    RETAIN_READINESS_WARNING = "RETAIN_READINESS_WARNING"
    RETAIN_AUTO_CONFIRM_NOTE = "RETAIN_AUTO_CONFIRM_NOTE"


class BlockerMinimumInput(StrEnum):
    CURRENT_CASE_VERSION = "CURRENT_CASE_VERSION"
    CURRENT_EXCEPTION_VERSION = "CURRENT_EXCEPTION_VERSION"
    CURRENT_CANONICAL_IDENTITY = "CURRENT_CANONICAL_IDENTITY"
    CORRECTED_IDENTITY_WITH_RATIONALE = "CORRECTED_IDENTITY_WITH_RATIONALE"
    CURRENT_JURISDICTION_EVIDENCE = "CURRENT_JURISDICTION_EVIDENCE"
    CURRENT_SEARCH_CHECKPOINT = "CURRENT_SEARCH_CHECKPOINT"
    CURRENT_REGISTRY_EVIDENCE = "CURRENT_REGISTRY_EVIDENCE"
    CURRENT_DOCUMENT_EVIDENCE = "CURRENT_DOCUMENT_EVIDENCE"
    CURRENT_DOCUMENT_REVIEW = "CURRENT_DOCUMENT_REVIEW"
    CURRENT_RECONCILIATION_EVIDENCE = "CURRENT_RECONCILIATION_EVIDENCE"
    AUTHORIZED_RECONCILIATION_ACTION = "AUTHORIZED_RECONCILIATION_ACTION"
    CURRENT_OWNERSHIP_EVIDENCE = "CURRENT_OWNERSHIP_EVIDENCE"
    CORRECTED_OWNERSHIP_EVIDENCE = "CORRECTED_OWNERSHIP_EVIDENCE"
    CURRENT_ENTITY_RESOLUTION_EVIDENCE = "CURRENT_ENTITY_RESOLUTION_EVIDENCE"
    CURRENT_MOCK_RISK_EVIDENCE = "CURRENT_MOCK_RISK_EVIDENCE"
    CURRENT_TARGET_CLASSIFICATION = "CURRENT_TARGET_CLASSIFICATION"
    CURRENT_FROZEN_TARGET_REVIEW = "CURRENT_FROZEN_TARGET_REVIEW"
    CURRENT_TARGET_LEDGER = "CURRENT_TARGET_LEDGER"
    PROVIDER_VERIFICATION = "PROVIDER_VERIFICATION"
    PROVIDER_DIAGNOSIS = "PROVIDER_DIAGNOSIS"
    CURRENT_REPLACEMENT_DOCUMENT = "CURRENT_REPLACEMENT_DOCUMENT"
    CANCELLED_SUPERSEDED_EXCEPTION = "CANCELLED_SUPERSEDED_EXCEPTION"
    RETAINED_SEARCH_FAILURE = "RETAINED_SEARCH_FAILURE"
    INDEPENDENT_EVIDENCE_AUTHORIZED = "INDEPENDENT_EVIDENCE_AUTHORIZED"
    CURRENT_READINESS_WARNING = "CURRENT_READINESS_WARNING"
    EQUIVALENT_NORMALIZED_VALUES = "EQUIVALENT_NORMALIZED_VALUES"


class InvalidatedDependency(StrEnum):
    CUSTOMER_IDENTITY = "CUSTOMER_IDENTITY"
    SEARCH_CHECKPOINT = "SEARCH_CHECKPOINT"
    REGISTRY_EVIDENCE = "REGISTRY_EVIDENCE"
    DOCUMENT_RECONCILIATION = "DOCUMENT_RECONCILIATION"
    OWNERSHIP_ANALYSIS = "OWNERSHIP_ANALYSIS"
    ADVISORY_INTELLIGENCE = "ADVISORY_INTELLIGENCE"
    READINESS_SNAPSHOT = "READINESS_SNAPSHOT"
    TARGET_CLASSIFICATION = "TARGET_CLASSIFICATION"
    TARGET_CONFIRMATION = "TARGET_CONFIRMATION"
    TARGET_PLAN = "TARGET_PLAN"
    TARGET_MUTATIONS = "TARGET_MUTATIONS"


class ResumeTransition(StrEnum):
    NO_AUTOMATIC_RESUME = "NO_AUTOMATIC_RESUME"
    RECHECK_FROM_STAGE = "RECHECK_FROM_STAGE"
    REPLACE_EVIDENCE_AND_RECHECK = "REPLACE_EVIDENCE_AND_RECHECK"
    APPLY_AUTHORIZED_DECISION_AND_RECHECK = "APPLY_AUTHORIZED_DECISION_AND_RECHECK"
    VERIFY_WITHOUT_REPLAY = "VERIFY_WITHOUT_REPLAY"
    CONTINUE_INDEPENDENT_EVIDENCE_ONLY = "CONTINUE_INDEPENDENT_EVIDENCE_ONLY"
    RETAIN_NOTE_WITHOUT_WORKFLOW_CHANGE = "RETAIN_NOTE_WITHOUT_WORKFLOW_CHANGE"


SafeBlockerCode = Annotated[
    str,
    StringConstraints(min_length=1, max_length=64, pattern=r"^[A-Z][A-Z0-9_]*$"),
]
SafeRuleVersion = Annotated[
    str,
    StringConstraints(min_length=1, max_length=64, pattern=r"^[A-Z0-9][A-Z0-9_.-]*$"),
]


class BlockerDecisionMetadata(BaseModel):
    """Immutable policy output without workflow-transition authority."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    blocker_code: SafeBlockerCode
    exception_type: BusinessExceptionType | None = None
    classification: BlockerDecisionClassification
    policy_version: str = Field(pattern=r"^BLOCKER_DECISION_POC_V[1-9][0-9]*$")
    rule_version: SafeRuleVersion
    owner: BlockerDecisionOwner
    minimum_inputs: tuple[BlockerMinimumInput, ...] = Field(max_length=16)
    permitted_actions: tuple[BlockerDecisionAction, ...] = Field(max_length=8)
    currently_available_actions: tuple[BlockerDecisionAction, ...] = Field(max_length=8)
    resume_stage: AutomationStage | None
    resume_transition: ResumeTransition
    resume_ready: bool
    invalidated_dependencies: tuple[InvalidatedDependency, ...] = Field(max_length=12)
    explanation: str = Field(min_length=1, max_length=300)
    unknowns: tuple[SafeBlockerCode, ...] = Field(default_factory=tuple, max_length=8)

    @model_validator(mode="after")
    def validate_non_authoritative_shape(self) -> "BlockerDecisionMetadata":
        non_blocking = self.classification in {
            BlockerDecisionClassification.AUTO_RESOLVED_WITH_NOTE,
            BlockerDecisionClassification.CONTINUE_WITH_WARNING,
        }
        if non_blocking == (self.exception_type is not None):
            raise ValueError("non-blocking metadata cannot classify an existing exception")
        if self.classification == BlockerDecisionClassification.AUTO_RESOLVED_WITH_NOTE and (
            self.resume_stage is not None
            or self.resume_transition != ResumeTransition.RETAIN_NOTE_WITHOUT_WORKFLOW_CHANGE
        ):
            raise ValueError("auto-resolved metadata cannot advance workflow state")
        return self


class BlockerDecisionRecord(BaseModel):
    """Durable evidence-bound decision metadata; never an authorization grant."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    decision_id: UUID
    case_id: UUID
    exception_id: UUID | None = None
    evidence_version: str = Field(min_length=1, max_length=128)
    automation_version: int = Field(ge=1)
    recorded_at: datetime
    metadata: BlockerDecisionMetadata
    actor_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.@-]{0,95}$")
    reviewer_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.@-]{0,95}$")

    @model_validator(mode="after")
    def validate_exception_binding(self) -> "BlockerDecisionRecord":
        is_blocking = self.metadata.classification not in {
            BlockerDecisionClassification.AUTO_RESOLVED_WITH_NOTE,
            BlockerDecisionClassification.CONTINUE_WITH_WARNING,
        }
        if is_blocking != (self.exception_id is not None):
            raise ValueError("blocking decision metadata must bind exactly one exception")
        return self


class AutomationEventType(StrEnum):
    ONBOARDING_CREATED = "ONBOARDING_CREATED"
    ONBOARDING_STARTED = "ONBOARDING_STARTED"
    REGISTRY_AUTOMATED = "REGISTRY_AUTOMATED"
    GOLDTIER_SEARCH_COMPLETED = "GOLDTIER_SEARCH_COMPLETED"
    GOLDTIER_SEARCH_REVIEW_REQUIRED = "GOLDTIER_SEARCH_REVIEW_REQUIRED"
    GOLDTIER_SEARCH_FAILED = "GOLDTIER_SEARCH_FAILED"
    DOCUMENT_AUTO_CONFIRMED = "DOCUMENT_AUTO_CONFIRMED"
    DOCUMENT_REVIEW_REQUIRED = "DOCUMENT_REVIEW_REQUIRED"
    DOCUMENT_REUPLOAD_REQUIRED = "DOCUMENT_REUPLOAD_REQUIRED"
    RECONCILIATION_EVALUATED = "RECONCILIATION_EVALUATED"
    RECONCILIATION_DECISION_RECORDED = "RECONCILIATION_DECISION_RECORDED"
    DOCUMENT_EXCEPTION_RESOLVED = "DOCUMENT_EXCEPTION_RESOLVED"
    OWNERSHIP_AUTOMATED = "OWNERSHIP_AUTOMATED"
    OWNERSHIP_REVIEW_REQUIRED = "OWNERSHIP_REVIEW_REQUIRED"
    INTELLIGENCE_EVALUATED = "INTELLIGENCE_EVALUATED"
    READINESS_AUTOMATED = "READINESS_AUTOMATED"
    TARGET_CLASSIFICATION_RECORDED = "TARGET_CLASSIFICATION_RECORDED"
    POLICY_SNAPSHOT_REBOUND = "POLICY_SNAPSHOT_REBOUND"
    TARGET_DISPATCH_CONFIRMED = "TARGET_DISPATCH_CONFIRMED"
    MOCK_SUBMISSION_STARTED = "MOCK_SUBMISSION_STARTED"
    MOCK_FINALIZATION_RECOVERY_PENDING = "MOCK_FINALIZATION_RECOVERY_PENDING"
    TARGET_OPERATION_RECOVERY_PENDING = "TARGET_OPERATION_RECOVERY_PENDING"
    TARGET_OPERATION_CHECKPOINTED = "TARGET_OPERATION_CHECKPOINTED"
    MOCK_SUBMISSION_COMPLETED = "MOCK_SUBMISSION_COMPLETED"
    BUSINESS_EXCEPTION_RAISED = "BUSINESS_EXCEPTION_RAISED"
    BUSINESS_EXCEPTION_RESOLVED = "BUSINESS_EXCEPTION_RESOLVED"
    AUTOMATION_RESUMING = "AUTOMATION_RESUMING"
    AUTOMATION_TECHNICAL_FAILURE = "AUTOMATION_TECHNICAL_FAILURE"
    AUTOMATION_NO_PROGRESS = "AUTOMATION_NO_PROGRESS"


class SafeExceptionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reference_id: UUID | None = None
    field_key: str | None = Field(default=None, max_length=64)
    registry_value: str | None = Field(default=None, max_length=512)
    document_value: str | None = Field(default=None, max_length=512)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    comparison: str | None = Field(default=None, max_length=64)
    source: str | None = Field(default=None, max_length=64)
    observed_value: str | None = Field(default=None, max_length=16)
    observed_at: datetime | None = None
    evidence_reference: str | None = Field(default=None, max_length=128)


class BusinessException(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exception_id: UUID
    case_id: UUID
    exception_type: BusinessExceptionType
    stage: AutomationStage
    status: BusinessExceptionStatus = BusinessExceptionStatus.OPEN
    blocker_code: str = Field(min_length=1, max_length=64)
    blocker_codes: tuple[str, ...] = Field(default_factory=tuple, max_length=8)
    explanation: str = Field(min_length=1, max_length=200)
    evidence_version: str = Field(min_length=1, max_length=128)
    authoritative_evidence_digest: str = Field(
        min_length=64, max_length=64, exclude=True, repr=False
    )
    automation_version: int = Field(ge=1)
    registry_evidence_generation: int | None = Field(default=None, ge=0, le=16)
    evidence: tuple[SafeExceptionEvidence, ...] = Field(default_factory=tuple, max_length=4)
    available_actions: tuple[ExceptionResolutionAction, ...] = Field(
        default_factory=tuple, max_length=4
    )
    decisions: tuple[BlockerDecisionRecord, ...] = Field(default_factory=tuple, max_length=8)
    created_at: datetime
    resolved_at: datetime | None = None
    resolution: ExceptionResolutionAction | None = None

    @model_validator(mode="after")
    def validate_decision_bindings(self) -> "BusinessException":
        if len({item.decision_id for item in self.decisions}) != len(self.decisions):
            raise ValueError("exception decision identifiers must be unique")
        for item in self.decisions:
            if (
                item.case_id != self.case_id
                or item.exception_id != self.exception_id
                or item.evidence_version != self.evidence_version
                or item.automation_version != self.automation_version
                or item.metadata.exception_type != self.exception_type
                or item.metadata.blocker_code not in self.blocker_codes
            ):
                raise ValueError("exception decision metadata binding is inconsistent")
        return self


class AutomationMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    automated_stages_completed: int = Field(default=0, ge=0, le=6)
    human_interventions: int = Field(default=0, ge=0)
    exceptions_raised: int = Field(default=0, ge=0)
    exceptions_resolved: int = Field(default=0, ge=0)
    final_outcome: str | None = Field(default=None, max_length=64)
    total_duration_ms: int | None = Field(default=None, ge=0)
    stage_durations_ms: dict[AutomationStage, int] = Field(default_factory=dict)


class AutomationEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence: int = Field(ge=1)
    event_type: AutomationEventType
    status: AutomationStatus
    stage: AutomationStage
    outcome: EventOutcome
    timestamp: datetime
    case_id: UUID
    code: str | None = Field(default=None, max_length=64)
    message: str = Field(min_length=1, max_length=200)


class ZeroTouchAutomationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: UUID
    automation_id: UUID
    version: int = Field(default=0, ge=0)
    stage_order_version: Literal[1, 2] = AUTOMATION_STAGE_ORDER_VERSION
    policy_version: str = ZERO_TOUCH_POLICY_VERSION
    ownership_provider_binding_id: str = Field(
        min_length=32, max_length=64, exclude=True, repr=False
    )
    status: AutomationStatus
    current_stage: AutomationStage
    completed_stages: tuple[AutomationStage, ...] = Field(default_factory=tuple, max_length=6)
    exceptions: list[BusinessException] = Field(default_factory=list)
    non_blocking_decisions: list[BlockerDecisionRecord] = Field(
        default_factory=list, max_length=64
    )
    technical_failure: SafeError | None = None
    metrics: AutomationMetrics = Field(default_factory=AutomationMetrics)
    events: list[AutomationEvent] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_decision_history(self) -> "ZeroTouchAutomationRecord":
        if len({item.decision_id for item in self.non_blocking_decisions}) != len(
            self.non_blocking_decisions
        ):
            raise ValueError("non-blocking decision identifiers must be unique")
        if any(
            item.case_id != self.case_id
            or item.metadata.classification
            not in {
                BlockerDecisionClassification.AUTO_RESOLVED_WITH_NOTE,
                BlockerDecisionClassification.CONTINUE_WITH_WARNING,
            }
            for item in self.non_blocking_decisions
        ):
            raise ValueError("non-blocking decision history binding is inconsistent")
        return self

    @property
    def active_exceptions(self) -> list[BusinessException]:
        return [item for item in self.exceptions if item.status == BusinessExceptionStatus.OPEN]


LEGAL_AUTOMATION_TRANSITIONS: dict[AutomationStatus, frozenset[AutomationStatus]] = {
    AutomationStatus.PENDING_INPUTS: frozenset(
        {
            AutomationStatus.PENDING_INPUTS,
            AutomationStatus.RUNNING,
            AutomationStatus.RESUMING,
            AutomationStatus.WAITING_FOR_REVIEW,
            AutomationStatus.TECHNICAL_FAILURE,
        }
    ),
    AutomationStatus.RUNNING: frozenset(
        {
            AutomationStatus.PENDING_INPUTS,
            AutomationStatus.RUNNING,
            AutomationStatus.WAITING_FOR_REVIEW,
            AutomationStatus.RECOVERY_PENDING,
            AutomationStatus.COMPLETED,
            AutomationStatus.TECHNICAL_FAILURE,
        }
    ),
    AutomationStatus.WAITING_FOR_REVIEW: frozenset(
        {
            AutomationStatus.WAITING_FOR_REVIEW,
            AutomationStatus.RESUMING,
            AutomationStatus.TECHNICAL_FAILURE,
        }
    ),
    AutomationStatus.RESUMING: frozenset(
        {
            AutomationStatus.RUNNING,
            AutomationStatus.WAITING_FOR_REVIEW,
            AutomationStatus.COMPLETED,
            AutomationStatus.TECHNICAL_FAILURE,
            AutomationStatus.RECOVERY_PENDING,
        }
    ),
    AutomationStatus.RECOVERY_PENDING: frozenset(
        {
            AutomationStatus.RECOVERY_PENDING,
            AutomationStatus.RUNNING,
            AutomationStatus.WAITING_FOR_REVIEW,
            AutomationStatus.COMPLETED,
            AutomationStatus.TECHNICAL_FAILURE,
        }
    ),
    AutomationStatus.COMPLETED: frozenset({AutomationStatus.COMPLETED}),
    AutomationStatus.TECHNICAL_FAILURE: frozenset(
        {AutomationStatus.TECHNICAL_FAILURE, AutomationStatus.RESUMING}
    ),
}


def validate_automation_transition(
    previous: ZeroTouchAutomationRecord,
    candidate: ZeroTouchAutomationRecord,
) -> None:
    """Reject status or checkpoint changes outside the Phase 06 state table."""

    if candidate.stage_order_version < previous.stage_order_version:
        raise ValueError("zero-touch automation stage order cannot be downgraded")
    pending_completed_stages = (
        (AutomationStage.REGISTRY,)
        if candidate.stage_order_version == LEGACY_AUTOMATION_STAGE_ORDER_VERSION
        else (AutomationStage.REGISTRY, AutomationStage.GOLDTIER_SEARCH)
    )
    document_reupload_recovery = (
        previous.status == AutomationStatus.WAITING_FOR_REVIEW
        and previous.current_stage == AutomationStage.DOCUMENT
        and candidate.status == AutomationStatus.PENDING_INPUTS
        and candidate.current_stage == AutomationStage.DOCUMENT
        and candidate.completed_stages == pending_completed_stages
        and bool(candidate.events)
        and candidate.events[-1].event_type == AutomationEventType.DOCUMENT_REUPLOAD_REQUIRED
    )
    if (
        candidate.status not in LEGAL_AUTOMATION_TRANSITIONS[previous.status]
        and not document_reupload_recovery
        and not (
            previous.status == AutomationStatus.WAITING_FOR_REVIEW
            and previous.current_stage == AutomationStage.GOLDTIER_SEARCH
            and candidate.status == AutomationStatus.PENDING_INPUTS
            and candidate.current_stage == AutomationStage.DOCUMENT
            and candidate.completed_stages == pending_completed_stages
            and candidate.events
            and candidate.events[-1].code == "EXISTING_GOLDTIER_CUSTOMER_CONFIRMED"
        )
    ):
        raise ValueError("illegal zero-touch automation status transition")
    validate_automation_record(candidate)


def validate_automation_record(record: ZeroTouchAutomationRecord) -> None:
    """Validate status, stage, blocker, and completed-prefix invariants."""

    stage_order = (
        LEGACY_AUTOMATION_STAGE_ORDER
        if record.stage_order_version == LEGACY_AUTOMATION_STAGE_ORDER_VERSION
        else AUTOMATION_STAGE_ORDER
    )
    expected_prefix = tuple(AutomationStage(value) for value in stage_order)
    if record.completed_stages != expected_prefix[: len(record.completed_stages)]:
        raise ValueError("completed automation stages must be an ordered unique prefix")
    first_incomplete = (
        expected_prefix[len(record.completed_stages)]
        if len(record.completed_stages) < len(expected_prefix)
        else AutomationStage.COMPLETE
    )

    open_exceptions = record.active_exceptions
    if record.status == AutomationStatus.PENDING_INPUTS:
        required_completed_stages = (
            (AutomationStage.REGISTRY,)
            if record.stage_order_version == LEGACY_AUTOMATION_STAGE_ORDER_VERSION
            else (AutomationStage.REGISTRY, AutomationStage.GOLDTIER_SEARCH)
        )
        if (
            record.current_stage != AutomationStage.DOCUMENT
            or record.completed_stages != required_completed_stages
            or open_exceptions
            or record.technical_failure is not None
        ):
            raise ValueError("pending-input automation record is inconsistent")
    elif record.status == AutomationStatus.WAITING_FOR_REVIEW:
        if not open_exceptions or record.technical_failure is not None:
            raise ValueError("review-wait automation record is inconsistent")
        earliest_open_stage = min(
            (item.stage for item in open_exceptions),
            key=expected_prefix.index,
        )
        if record.current_stage != earliest_open_stage:
            raise ValueError("current review stage must be the earliest open blocker")
    elif record.status in {AutomationStatus.RUNNING, AutomationStatus.RESUMING}:
        if (
            open_exceptions
            or record.technical_failure is not None
            or record.current_stage != first_incomplete
            or record.started_at is None
        ):
            raise ValueError("progressing automation cannot retain an open blocker")
    elif record.status == AutomationStatus.RECOVERY_PENDING:
        if (
            open_exceptions
            or record.technical_failure is not None
            or record.current_stage != AutomationStage.MOCK_GOLDTIER
            or record.completed_stages != expected_prefix[:-1]
            or record.started_at is None
        ):
            raise ValueError("finalization-recovery automation record is inconsistent")
    elif record.status == AutomationStatus.COMPLETED:
        if (
            record.current_stage != AutomationStage.COMPLETE
            or record.completed_stages != expected_prefix
            or record.completed_at is None
            or record.metrics.final_outcome != "MOCK_GOLDTIER_SUBMITTED"
            or open_exceptions
            or record.technical_failure is not None
        ):
            raise ValueError("completed automation record is inconsistent")
    elif record.status == AutomationStatus.TECHNICAL_FAILURE and (
        record.technical_failure is None or open_exceptions
    ):
        raise ValueError("technical-failure automation record is inconsistent")
