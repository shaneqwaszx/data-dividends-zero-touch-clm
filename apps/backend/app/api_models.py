"""Browser-facing API models that exclude internal registry proof references."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.clm import (
    ClmOrchestrationRecord,
    ClmReadinessAssessment,
    ClmStatus,
    ClmWorkflowEvent,
    GoldTierSubmissionPlan,
    RelatedPartySubmissionPreparation,
)
from app.domain.documents import (
    ComparisonStatus,
    DocumentFieldKey,
    DocumentProcessingRecord,
    DocumentProcessingState,
    DocumentProfile,
    DocumentWorkflowEvent,
    FieldReviewStatus,
    IdpEnvironment,
)
from app.domain.jurisdiction import (
    JurisdictionCode,
    JurisdictionObservationSource,
    JurisdictionResolutionStatus,
    RegistryRoutingDecision,
)
from app.domain.models import (
    GoldTierResult,
    OnboardingCase,
    RegisteredAddress,
    SafeError,
    SourceEnvironment,
    SourceSystem,
    WorkflowEvent,
    WorkflowState,
)
from app.domain.ownership import (
    OwnershipAnalysisIssue,
    OwnershipAnalysisRecord,
    OwnershipAnalysisState,
    OwnershipBasis,
    OwnershipCandidate,
    OwnershipEnvironment,
    OwnershipRelationshipType,
    OwnershipWorkflowEvent,
    Party,
)
from app.domain.zero_touch import (
    AutomationEvent,
    AutomationMetrics,
    AutomationStage,
    AutomationStatus,
    BusinessExceptionStatus,
    BusinessExceptionType,
    ExceptionResolutionAction,
    SafeExceptionEvidence,
    ZeroTouchAutomationRecord,
)


class BrowserSourceMetadata(BaseModel):
    """Source metadata needed by the UI, excluding the internal endpoint reference."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    source_system: SourceSystem
    environment: SourceEnvironment
    retrieved_at: datetime


class BrowserCanonicalLegalEntity(BaseModel):
    """Canonical entity projection safe for browser delivery."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    registration_number: str
    legal_name: str | None = None
    country_of_incorporation: str | None = None
    party_type: str | None = None
    registration_date: date | None = None
    entity_status: str | None = None
    registered_address: RegisteredAddress | None = None
    source: BrowserSourceMetadata


class BrowserJurisdictionObservation(BaseModel):
    """Safe browser evidence with a clearly scoped non-provider reference."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    jurisdiction: JurisdictionCode
    source: JurisdictionObservationSource
    observed_at: datetime
    evidence_reference: str | None = Field(
        default=None, validation_alias="source_reference"
    )
    confidence: float | None = None


class BrowserJurisdictionResolution(BaseModel):
    """Browser-safe decision and all retained jurisdiction observations."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    status: JurisdictionResolutionStatus
    resolved_jurisdiction: JurisdictionCode | None = None
    observations: tuple[BrowserJurisdictionObservation, ...]
    resolved_at: datetime


class OnboardingCaseResponse(BaseModel):
    """Application case response with internal proof metadata minimized."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    case_id: UUID
    source_case_id: str
    correlation_id: UUID
    requested_uen: str
    jurisdiction_resolution: BrowserJurisdictionResolution | None = None
    registry_route: RegistryRoutingDecision | None = None
    state: WorkflowState
    entity: BrowserCanonicalLegalEntity | None = None
    goldtier_result: GoldTierResult | None = None
    events: list[WorkflowEvent]
    error: SafeError | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, case: OnboardingCase) -> "OnboardingCaseResponse":
        """Project a domain case without serializing its registry source link."""

        return cls.model_validate(case)


class BrowserFieldProvenance(BaseModel):
    """Safe source/page metadata without raw provider output."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    provider: str
    environment: IdpEnvironment
    page_number: int | None
    source_reference: str


class BrowserExtractedField(BaseModel):
    """Provider suggestion, comparison, and separately retained human decision."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    field_key: DocumentFieldKey
    original_extracted_value: str | None
    normalized_value: str | None
    confidence: float
    provenance: BrowserFieldProvenance
    canonical_value: str | None
    comparison_status: ComparisonStatus
    review_status: FieldReviewStatus
    reviewed_value: str | None
    reviewed_at: datetime | None
    review_note: str | None


class DocumentProcessingResponse(BaseModel):
    """Document response without bytes, paths, or raw provider evidence."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    case_id: UUID
    document_id: UUID
    correlation_id: UUID
    display_name: str
    media_type: str
    profile: DocumentProfile
    provider_environment: IdpEnvironment | None
    state: DocumentProcessingState
    fields: list[BrowserExtractedField]
    events: list[DocumentWorkflowEvent]
    error: SafeError | None = None
    created_at: datetime
    processed_at: datetime | None = None
    reviewed_at: datetime | None = None
    supersedes_document_id: UUID | None = None
    superseded_by_document_id: UUID | None = None
    superseded_at: datetime | None = None
    updated_at: datetime

    @classmethod
    def from_domain(cls, record: DocumentProcessingRecord) -> "DocumentProcessingResponse":
        return cls.model_validate(record)


class OwnershipAnalysisResponse(BaseModel):
    """Browser-required ownership graph and deterministic evidence only."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    case_id: UUID
    analysis_id: UUID
    correlation_id: UUID
    root_party_id: str | None
    provider_name: str | None
    provider_environment: OwnershipEnvironment | None
    state: OwnershipAnalysisState
    parties: list[Party]
    relationships: list["BrowserOwnershipRelationship"]
    candidates: list[OwnershipCandidate]
    issues: list[OwnershipAnalysisIssue]
    threshold_percent: Decimal
    threshold_comparator: str
    events: list[OwnershipWorkflowEvent]
    error: SafeError | None = None
    created_at: datetime
    loaded_at: datetime | None = None
    analyzed_at: datetime | None = None
    updated_at: datetime

    @classmethod
    def from_domain(cls, record: OwnershipAnalysisRecord) -> "OwnershipAnalysisResponse":
        return cls.model_validate(record)


class BrowserOwnershipProvenance(BaseModel):
    """Browser-safe provenance without internal source routing/reference data."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    provider: str
    environment: OwnershipEnvironment
    sourced_at: datetime


class BrowserOwnershipRelationship(BaseModel):
    """Ownership edge projection with minimized provenance."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    relationship_id: str
    parent_party_id: str
    child_party_id: str
    ownership_percent: Decimal
    relationship_type: OwnershipRelationshipType
    basis: OwnershipBasis
    provenance: BrowserOwnershipProvenance


OwnershipAnalysisResponse.model_rebuild()


class BrowserClmSubmission(BaseModel):
    """Safe immutable-snapshot references without the internal business snapshot."""

    model_config = ConfigDict(extra="forbid")

    snapshot_id: UUID
    submission_id: UUID
    created_at: datetime
    readiness_policy_version: str
    document_reference_count: int
    ownership_reference_id: UUID


class ClmCaseSummaryResponse(BaseModel):
    """Unified operational picture without raw subsystem/provider evidence."""

    model_config = ConfigDict(extra="forbid")

    case: OnboardingCaseResponse
    orchestration_id: UUID
    correlation_id: UUID
    version: int
    status: ClmStatus
    readiness: ClmReadinessAssessment
    submission_plan: GoldTierSubmissionPlan
    related_party_preparation: RelatedPartySubmissionPreparation | None
    submission: BrowserClmSubmission | None
    goldtier_result: GoldTierResult | None
    timeline: list[ClmWorkflowEvent]
    error: SafeError | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(
        cls, record: ClmOrchestrationRecord, case: OnboardingCase
    ) -> "ClmCaseSummaryResponse":
        snapshot = record.submission_snapshot
        submission = (
            BrowserClmSubmission(
                snapshot_id=snapshot.snapshot_id,
                submission_id=snapshot.submission_id,
                created_at=snapshot.created_at,
                readiness_policy_version=snapshot.readiness_policy_version,
                document_reference_count=len(snapshot.document_references),
                ownership_reference_id=snapshot.ownership_reference.reference_id,
            )
            if snapshot is not None
            else None
        )
        return cls(
            case=OnboardingCaseResponse.from_domain(case),
            orchestration_id=record.orchestration_id,
            correlation_id=record.correlation_id,
            version=record.version,
            status=record.status,
            readiness=record.readiness,
            submission_plan=record.submission_plan,
            related_party_preparation=record.related_party_preparation,
            submission=submission,
            goldtier_result=record.goldtier_result,
            timeline=record.events,
            error=record.error,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class BusinessExceptionResponse(BaseModel):
    """Browser-safe exception projection; server authority digests never leave the API."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    exception_id: UUID
    case_id: UUID
    exception_type: BusinessExceptionType
    stage: AutomationStage
    status: BusinessExceptionStatus
    blocker_code: str
    blocker_codes: tuple[str, ...]
    explanation: str
    evidence_version: str
    automation_version: int
    evidence: tuple[SafeExceptionEvidence, ...]
    available_actions: tuple[ExceptionResolutionAction, ...]
    created_at: datetime
    resolved_at: datetime | None
    resolution: ExceptionResolutionAction | None


class ZeroTouchCaseSummaryResponse(BaseModel):
    """Sponsor-facing authoritative automation and bounded CLM summary."""

    model_config = ConfigDict(extra="forbid")

    case: OnboardingCaseResponse
    clm: ClmCaseSummaryResponse
    automation_id: UUID
    version: int
    status: AutomationStatus
    current_stage: AutomationStage
    completed_stages: tuple[AutomationStage, ...]
    active_exceptions: list[BusinessExceptionResponse]
    technical_failure: SafeError | None
    metrics: AutomationMetrics
    target_operations: tuple["BrowserTargetOperationEvidence", ...]
    timeline: list[AutomationEvent]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(
        cls,
        record: ZeroTouchAutomationRecord,
        clm_record: ClmOrchestrationRecord,
        case: OnboardingCase,
        target_operations: tuple["BrowserTargetOperationEvidence", ...] = (),
    ) -> "ZeroTouchCaseSummaryResponse":
        return cls(
            case=OnboardingCaseResponse.from_domain(case),
            clm=ClmCaseSummaryResponse.from_domain(clm_record, case),
            automation_id=record.automation_id,
            version=record.version,
            status=record.status,
            current_stage=record.current_stage,
            completed_stages=record.completed_stages,
            active_exceptions=[
                BusinessExceptionResponse.model_validate(item)
                for item in record.active_exceptions
            ],
            technical_failure=record.technical_failure,
            metrics=record.metrics,
            target_operations=target_operations,
            timeline=record.events,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class BrowserTargetOperationEvidence(BaseModel):
    """Minimal server-authored Mock GoldTier operation status for sponsor display."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["SEARCH", "SHELL", "POLICY", "AMEND"]
    status: Literal[
        "NOT_ATTEMPTED",
        "IN_PROGRESS",
        "NO_MATCH",
        "MATCH_FOUND",
        "CREATED",
        "SUCCESS",
        "FAILED",
    ]


ZeroTouchCaseSummaryResponse.model_rebuild()
