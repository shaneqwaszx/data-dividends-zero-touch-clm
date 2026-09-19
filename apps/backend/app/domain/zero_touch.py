"""Source-neutral zero-touch automation, exception, and metric models."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import EventOutcome, SafeError

ZERO_TOUCH_POLICY_VERSION = "PHASE_06_POC_V1"
AUTOMATION_STAGE_ORDER = (
    "REGISTRY",
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
    EXISTING_PARTY_REVIEW_REQUIRED = "EXISTING_PARTY_REVIEW_REQUIRED"
    TARGET_PARTIAL_REVIEW_REQUIRED = "TARGET_PARTIAL_REVIEW_REQUIRED"


class BusinessExceptionStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


class ExceptionResolutionAction(StrEnum):
    KEEP_REGISTRY_VALUE = "KEEP_REGISTRY_VALUE"
    USE_DOCUMENT_VALUE = "USE_DOCUMENT_VALUE"
    REQUEST_ADDITIONAL_INFORMATION = "REQUEST_ADDITIONAL_INFORMATION"


class AutomationEventType(StrEnum):
    ONBOARDING_CREATED = "ONBOARDING_CREATED"
    ONBOARDING_STARTED = "ONBOARDING_STARTED"
    REGISTRY_AUTOMATED = "REGISTRY_AUTOMATED"
    DOCUMENT_AUTO_CONFIRMED = "DOCUMENT_AUTO_CONFIRMED"
    DOCUMENT_REVIEW_REQUIRED = "DOCUMENT_REVIEW_REQUIRED"
    DOCUMENT_REUPLOAD_REQUIRED = "DOCUMENT_REUPLOAD_REQUIRED"
    RECONCILIATION_EVALUATED = "RECONCILIATION_EVALUATED"
    RECONCILIATION_DECISION_RECORDED = "RECONCILIATION_DECISION_RECORDED"
    DOCUMENT_EXCEPTION_RESOLVED = "DOCUMENT_EXCEPTION_RESOLVED"
    OWNERSHIP_AUTOMATED = "OWNERSHIP_AUTOMATED"
    OWNERSHIP_REVIEW_REQUIRED = "OWNERSHIP_REVIEW_REQUIRED"
    READINESS_AUTOMATED = "READINESS_AUTOMATED"
    MOCK_SUBMISSION_STARTED = "MOCK_SUBMISSION_STARTED"
    MOCK_FINALIZATION_RECOVERY_PENDING = "MOCK_FINALIZATION_RECOVERY_PENDING"
    TARGET_OPERATION_RECOVERY_PENDING = "TARGET_OPERATION_RECOVERY_PENDING"
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
    evidence: tuple[SafeExceptionEvidence, ...] = Field(default_factory=tuple, max_length=4)
    available_actions: tuple[ExceptionResolutionAction, ...] = Field(
        default_factory=tuple, max_length=4
    )
    created_at: datetime
    resolved_at: datetime | None = None
    resolution: ExceptionResolutionAction | None = None


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
    policy_version: str = ZERO_TOUCH_POLICY_VERSION
    ownership_provider_binding_id: str = Field(
        min_length=32, max_length=64, exclude=True, repr=False
    )
    status: AutomationStatus
    current_stage: AutomationStage
    completed_stages: tuple[AutomationStage, ...] = Field(default_factory=tuple, max_length=6)
    exceptions: list[BusinessException] = Field(default_factory=list)
    technical_failure: SafeError | None = None
    metrics: AutomationMetrics = Field(default_factory=AutomationMetrics)
    events: list[AutomationEvent] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @property
    def active_exceptions(self) -> list[BusinessException]:
        return [item for item in self.exceptions if item.status == BusinessExceptionStatus.OPEN]


LEGAL_AUTOMATION_TRANSITIONS: dict[AutomationStatus, frozenset[AutomationStatus]] = {
    AutomationStatus.PENDING_INPUTS: frozenset(
        {
            AutomationStatus.PENDING_INPUTS,
            AutomationStatus.RUNNING,
            AutomationStatus.WAITING_FOR_REVIEW,
            AutomationStatus.TECHNICAL_FAILURE,
        }
    ),
    AutomationStatus.RUNNING: frozenset(
        {
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
    AutomationStatus.TECHNICAL_FAILURE: frozenset({AutomationStatus.TECHNICAL_FAILURE}),
}


def validate_automation_transition(
    previous: ZeroTouchAutomationRecord,
    candidate: ZeroTouchAutomationRecord,
) -> None:
    """Reject status or checkpoint changes outside the Phase 06 state table."""

    document_reupload_recovery = (
        previous.status == AutomationStatus.WAITING_FOR_REVIEW
        and previous.current_stage == AutomationStage.DOCUMENT
        and candidate.status == AutomationStatus.PENDING_INPUTS
        and candidate.current_stage == AutomationStage.DOCUMENT
        and candidate.completed_stages == (AutomationStage.REGISTRY,)
        and bool(candidate.events)
        and candidate.events[-1].event_type == AutomationEventType.DOCUMENT_REUPLOAD_REQUIRED
    )
    if (
        candidate.status not in LEGAL_AUTOMATION_TRANSITIONS[previous.status]
        and not document_reupload_recovery
    ):
        raise ValueError("illegal zero-touch automation status transition")
    validate_automation_record(candidate)


def validate_automation_record(record: ZeroTouchAutomationRecord) -> None:
    """Validate status, stage, blocker, and completed-prefix invariants."""

    expected_prefix = tuple(AutomationStage(value) for value in AUTOMATION_STAGE_ORDER)
    if record.completed_stages != expected_prefix[: len(record.completed_stages)]:
        raise ValueError("completed automation stages must be an ordered unique prefix")
    first_incomplete = (
        expected_prefix[len(record.completed_stages)]
        if len(record.completed_stages) < len(expected_prefix)
        else AutomationStage.COMPLETE
    )

    open_exceptions = record.active_exceptions
    if record.status == AutomationStatus.PENDING_INPUTS:
        if (
            record.current_stage != AutomationStage.DOCUMENT
            or record.completed_stages != (AutomationStage.REGISTRY,)
            or open_exceptions
            or record.technical_failure is not None
        ):
            raise ValueError("pending-input automation record is inconsistent")
    elif record.status == AutomationStatus.WAITING_FOR_REVIEW:
        if not open_exceptions or record.technical_failure is not None:
            raise ValueError("review-wait automation record is inconsistent")
        if any(item.stage != record.current_stage for item in open_exceptions):
            raise ValueError("open exceptions must match the current review stage")
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
