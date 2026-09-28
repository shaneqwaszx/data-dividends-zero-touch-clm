"""Source-neutral Phase 05 CLM orchestration and readiness models."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.models import EventOutcome, GoldTierResult, SafeError
from app.domain.target_preparation import GoldTierRequestPreview
from app.domain.target_safety import SafeTargetErrorCode, SafeTargetIdentifier, SafeTargetMessage
from app.domain.target_submission import (
    GoldTierExecutionReceipt,
    GoldTierProviderClassification,
    GoldTierProviderMode,
    GoldTierSubmissionInput,
    SubmissionCanonicalEntity,
)

CLM_READINESS_POLICY_VERSION = "PHASE_05_POC_V1"


class ClmStatus(StrEnum):
    COLLECTING_EVIDENCE = "COLLECTING_EVIDENCE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    READY_FOR_MOCK_SUBMISSION = "READY_FOR_MOCK_SUBMISSION"
    SUBMITTING = "SUBMITTING"
    MOCK_GOLDTIER_SUBMITTED = "MOCK_GOLDTIER_SUBMITTED"
    FAILED = "FAILED"


class ReadinessStageStatus(StrEnum):
    READY = "READY"
    MISSING = "MISSING"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    NOT_SUBMITTED = "NOT_SUBMITTED"
    SUBMITTED = "SUBMITTED"


class ClmBlockerCode(StrEnum):
    REGISTRY_NOT_READY = "REGISTRY_NOT_READY"
    REGISTRY_FAILED = "REGISTRY_FAILED"
    CANONICAL_DATA_INVALID = "CANONICAL_DATA_INVALID"
    DOCUMENT_REQUIRED = "DOCUMENT_REQUIRED"
    DOCUMENT_PROCESSING = "DOCUMENT_PROCESSING"
    DOCUMENT_REVIEW_INCOMPLETE = "DOCUMENT_REVIEW_INCOMPLETE"
    DOCUMENT_PROCESSING_FAILED = "DOCUMENT_PROCESSING_FAILED"
    SOURCE_CONFLICT_REQUIRES_POLICY = "SOURCE_CONFLICT_REQUIRES_POLICY"
    OWNERSHIP_REQUIRED = "OWNERSHIP_REQUIRED"
    OWNERSHIP_ANALYSIS_INCOMPLETE = "OWNERSHIP_ANALYSIS_INCOMPLETE"
    OWNERSHIP_REVIEW_REQUIRED = "OWNERSHIP_REVIEW_REQUIRED"
    OWNERSHIP_ANALYSIS_FAILED = "OWNERSHIP_ANALYSIS_FAILED"
    GOLDTIER_SEARCH_REQUIRED = "GOLDTIER_SEARCH_REQUIRED"
    GOLDTIER_SEARCH_REVIEW_REQUIRED = "GOLDTIER_SEARCH_REVIEW_REQUIRED"
    GOLDTIER_SEARCH_FAILED = "GOLDTIER_SEARCH_FAILED"
    GOLDTIER_SEARCH_STALE = "GOLDTIER_SEARCH_STALE"
    GOLDTIER_CLASSIFICATION_REQUIRED = "GOLDTIER_CLASSIFICATION_REQUIRED"


class ClmWarningCode(StrEnum):
    IDP_PROFILE_PROVISIONAL = "IDP_PROFILE_PROVISIONAL"
    UBO_POLICY_NOT_SPONSOR_CONFIRMED = "UBO_POLICY_NOT_SPONSOR_CONFIRMED"
    LIVE_HIERARCHY_UNAVAILABLE = "LIVE_HIERARCHY_UNAVAILABLE"
    RELATED_PARTY_MAPPING_PENDING = "RELATED_PARTY_MAPPING_PENDING"
    REAL_GOLDTIER_NOT_CONFIGURED = "REAL_GOLDTIER_NOT_CONFIGURED"
    READY_FOR_APPROVAL_UNAVAILABLE = "READY_FOR_APPROVAL_UNAVAILABLE"


class ClmEventType(StrEnum):
    CLM_CASE_CREATED = "CLM_CASE_CREATED"
    REGISTRY_READY = "REGISTRY_READY"
    CLM_REVIEW_REQUIRED = "CLM_REVIEW_REQUIRED"
    CLM_CASE_FAILED = "CLM_CASE_FAILED"
    READINESS_EVALUATED = "READINESS_EVALUATED"
    MOCK_SUBMISSION_STARTED = "MOCK_SUBMISSION_STARTED"
    MOCK_TARGET_EXECUTION_RECORDED = "MOCK_TARGET_EXECUTION_RECORDED"
    MOCK_SUBMISSION_COMPLETED = "MOCK_SUBMISSION_COMPLETED"
    CLM_SUBMISSION_FAILED = "CLM_SUBMISSION_FAILED"
    GOLDTIER_SEARCH_STARTED = "GOLDTIER_SEARCH_STARTED"
    GOLDTIER_SEARCH_COMPLETED = "GOLDTIER_SEARCH_COMPLETED"
    GOLDTIER_SEARCH_REVIEW_REQUIRED = "GOLDTIER_SEARCH_REVIEW_REQUIRED"
    GOLDTIER_SEARCH_FAILED = "GOLDTIER_SEARCH_FAILED"
    GOLDTIER_OPERATION_CHECKPOINTED = "GOLDTIER_OPERATION_CHECKPOINTED"
    TARGET_CLASSIFICATION_BOUND = "TARGET_CLASSIFICATION_BOUND"


class GoldTierSearchCheckpointStatus(StrEnum):
    COMPLETED = "COMPLETED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAILED = "FAILED"
    STALE = "STALE"


class GoldTierSearchDisposition(StrEnum):
    NO_MATCH = "NO_MATCH"
    EXACT_MATCH = "EXACT_MATCH"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAILED = "FAILED"


class RetainedGoldTierCandidate(BaseModel):
    """Bounded safe candidate evidence; raw provider responses never enter the aggregate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    party_id: SafeTargetIdentifier
    registration_number: str | None = Field(default=None, min_length=1, max_length=64)
    country: str | None = Field(default=None, pattern=r"^[A-Za-z]{2,3}$")
    legal_name: str | None = Field(default=None, min_length=1, max_length=160)
    legal_form: str | None = Field(default=None, min_length=1, max_length=80)
    registered_address: str | None = Field(default=None, min_length=1, max_length=240)


class GoldTierSearchCheckpoint(BaseModel):
    """Immutable early Search evidence bound to one canonical identity fingerprint."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: UUID
    identity_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_mode: GoldTierProviderMode
    provider_classification: GoldTierProviderClassification
    status: GoldTierSearchCheckpointStatus
    disposition: GoldTierSearchDisposition
    provider_outcome: str = Field(min_length=1, max_length=32)
    status_code: int = Field(ge=200, le=599)
    candidate_count: int = Field(ge=0, le=25)
    candidates: tuple[RetainedGoldTierCandidate, ...] = Field(default=(), max_length=25)
    selected_party_id: SafeTargetIdentifier | None = None
    resolution_outcome: str | None = Field(default=None, min_length=1, max_length=32)
    code: SafeTargetErrorCode | None = None
    message: SafeTargetMessage
    searched_at: datetime

    @model_validator(mode="after")
    def validate_checkpoint(self) -> "GoldTierSearchCheckpoint":
        if self.candidate_count != len(self.candidates):
            raise ValueError("Search candidate count must match retained candidates")
        if self.disposition == GoldTierSearchDisposition.EXACT_MATCH:
            if (
                self.selected_party_id is None
                or self.status != GoldTierSearchCheckpointStatus.COMPLETED
            ):
                raise ValueError("Exact Search checkpoint requires a selected target identity")
        elif self.selected_party_id is not None:
            raise ValueError("Only an exact Search checkpoint may select a target identity")
        expected = {
            GoldTierProviderMode.MOCK: GoldTierProviderClassification.MOCK,
            GoldTierProviderMode.SANDBOX: GoldTierProviderClassification.SANDBOX_PARTIAL,
        }[self.provider_mode]
        if self.provider_classification != expected:
            raise ValueError("Search checkpoint provider identity is inconsistent")
        return self


class StageReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: ReadinessStageStatus
    reference_id: str | None = Field(default=None, max_length=64)


class ClmReadinessAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = Field(default=CLM_READINESS_POLICY_VERSION, max_length=64)
    registry: StageReadiness
    document: StageReadiness
    ownership: StageReadiness
    goldtier: StageReadiness
    blockers: list[ClmBlockerCode] = Field(default_factory=list)
    warnings: list[ClmWarningCode] = Field(default_factory=list)
    evaluated_at: datetime


class EvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reference_id: UUID
    version: int = Field(ge=0)
    status: str = Field(min_length=1, max_length=64)
    updated_at: datetime


class ProvisionalUboSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_count: int = Field(ge=0)
    internal_party_ids: tuple[str, ...] = Field(default_factory=tuple, max_length=100)
    policy_status: str = "PROJECT_DEFINED_PROVISIONAL"


class RelatedPartySubmissionPreparation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provisional_candidate_count: int = Field(ge=0)
    internal_party_ids: tuple[str, ...] = Field(default_factory=tuple, max_length=100)
    analysis_reference: UUID
    mapping_status: str = "PENDING_SPONSOR_CONFIRMATION"
    write_status: str = "RELATED_PARTY_WRITE_NOT_EXECUTED"


class ClmSubmissionSnapshot(BaseModel):
    """Immutable evidence-bounded input to one Mock GoldTier execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_id: UUID
    target_input: GoldTierSubmissionInput
    document_references: tuple[EvidenceReference, ...]
    ownership_reference: EvidenceReference
    provisional_ubo: ProvisionalUboSummary
    readiness_policy_version: str = CLM_READINESS_POLICY_VERSION
    created_at: datetime

    @property
    def submission_id(self) -> UUID:
        return self.target_input.submission_id

    @property
    def case_id(self) -> UUID:
        return self.target_input.case_id

    @property
    def correlation_id(self) -> UUID:
        return self.target_input.correlation_id

    @property
    def canonical_entity(self) -> SubmissionCanonicalEntity:
        return self.target_input.canonical_entity


class GoldTierSubmissionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    environment: GoldTierProviderMode = GoldTierProviderMode.MOCK
    provider_classification: GoldTierProviderClassification = GoldTierProviderClassification.MOCK
    base_operations: tuple[str, ...] = Field(
        default_factory=lambda: (
            "searchParty",
            "createShellCustomer if NO_MATCH",
            "createPolicy",
            "amendParty",
        )
    )
    match_found_behavior: str = "REVIEW_REQUIRED_NO_WRITES"
    related_party_integration: str = "PENDING_SPONSOR_CONFIRMATION"
    real_ready_for_approval: str = "NOT_AVAILABLE"
    request_preview: GoldTierRequestPreview | None = None

    @model_validator(mode="after")
    def validate_provider_identity(self) -> "GoldTierSubmissionPlan":
        expected = {
            GoldTierProviderMode.MOCK: GoldTierProviderClassification.MOCK,
            GoldTierProviderMode.SANDBOX: (GoldTierProviderClassification.SANDBOX_PARTIAL),
        }[self.environment]
        if self.provider_classification != expected:
            raise ValueError("GoldTier provider identity is internally inconsistent")
        return self


class ClmWorkflowEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence: int = Field(ge=1)
    event_type: ClmEventType
    status: ClmStatus
    outcome: EventOutcome
    timestamp: datetime
    case_id: UUID
    orchestration_id: UUID
    correlation_id: UUID
    code: str | None = Field(default=None, max_length=64)
    message: str = Field(min_length=1, max_length=200)


class ClmOrchestrationRecord(BaseModel):
    """References existing bounded records without duplicating their raw evidence."""

    model_config = ConfigDict(extra="forbid")

    case_id: UUID
    orchestration_id: UUID
    correlation_id: UUID
    version: int = Field(default=0, ge=0)
    status: ClmStatus
    readiness: ClmReadinessAssessment
    submission_plan: GoldTierSubmissionPlan
    target_search_checkpoint: GoldTierSearchCheckpoint | None = None
    submission_snapshot: ClmSubmissionSnapshot | None = None
    execution_receipt: GoldTierExecutionReceipt | None = None
    related_party_preparation: RelatedPartySubmissionPreparation | None = None
    goldtier_result: GoldTierResult | None = None
    events: list[ClmWorkflowEvent] = Field(default_factory=list)
    error: SafeError | None = None
    created_at: datetime
    updated_at: datetime
