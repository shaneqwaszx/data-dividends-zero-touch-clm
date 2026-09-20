"""Browser-facing API models that exclude internal registry proof references."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.access import CasePriority, TeamId
from app.domain.administration import TeamRecord
from app.domain.case_management import CasePortfolioRecord
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
    RegistryAcquisitionIssue,
    RegistryAcquisitionStatus,
    RegistryEvidenceDisposition,
    RegistryOperation,
    RegistryOperationStatus,
    RegistryPartyType,
    RegistryRelationshipType,
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
from app.domain.policy import CasePolicySnapshot
from app.domain.reconciliation import (
    DiscrepancyStatus,
    ObservationValidity,
    ReconciliationCaseRecord,
    ReconciliationDecisionAction,
    ReconciliationField,
    ReconciliationObservation,
    ReconciliationOutcome,
    ReconciliationSourceKind,
    ReconciliationStatus,
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
    evidence_reference: str | None = Field(default=None, validation_alias="source_reference")
    confidence: float | None = None


class BrowserJurisdictionResolution(BaseModel):
    """Browser-safe decision and all retained jurisdiction observations."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    status: JurisdictionResolutionStatus
    resolved_jurisdiction: JurisdictionCode | None = None
    observations: tuple[BrowserJurisdictionObservation, ...]
    resolved_at: datetime


class BrowserRegistryProvenance(BaseModel):
    """Safe operation provenance without raw endpoints or connector configuration."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    provider: SourceSystem
    environment: SourceEnvironment
    operation: RegistryOperation
    retrieved_at: datetime
    evidence_reference: str


class BrowserRegistryOfficer(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    officer_id: str
    name: str
    role: str
    appointment_date: date | None
    cessation_date: date | None
    country: str | None
    provenance: BrowserRegistryProvenance


class BrowserRegistryOwnershipParty(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    party_id: str
    party_type: RegistryPartyType
    name: str
    registration_identifier: str | None
    country: str | None
    ownership_percentage: Decimal | None
    provenance: BrowserRegistryProvenance


class BrowserRegistryRelationship(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    relationship_id: str
    owned_entity_id: str
    owner_party_id: str
    relationship_type: RegistryRelationshipType
    ownership_percentage: Decimal
    provenance: BrowserRegistryProvenance


class BrowserRegistryOperationResult(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    operation: RegistryOperation
    status: RegistryOperationStatus
    record_count: int
    provenance: BrowserRegistryProvenance | None
    error: RegistryAcquisitionIssue | None


class BrowserRegistryAcquisition(BaseModel):
    """Bounded normalized evidence for truthful multi-step browser display."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    requested_identifier: str
    status: RegistryAcquisitionStatus
    officers: tuple[BrowserRegistryOfficer, ...]
    ownership_parties: tuple[BrowserRegistryOwnershipParty, ...]
    relationships: tuple[BrowserRegistryRelationship, ...]
    operation_results: tuple[BrowserRegistryOperationResult, ...]
    issues: tuple[RegistryAcquisitionIssue, ...]
    retrieved_at: datetime


class BrowserRegistryEvidenceBinding(BaseModel):
    """Minimized case-use evidence for the provisional Mock registry cache."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    disposition: RegistryEvidenceDisposition
    bound_to_case_at: datetime
    expires_at: datetime
    freshness_policy_id: Literal["MOCK_ACRA_FIXED_90D"]
    freshness_policy_version: Literal[1]
    freshness_duration_seconds: Literal[7_776_000]
    freshness_comparator: Literal["EVALUATION_NOW_LT_EXPIRES_AT"]


class OnboardingCaseResponse(BaseModel):
    """Application case response with internal proof metadata minimized."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    case_id: UUID
    source_case_id: str
    correlation_id: UUID
    requested_uen: str
    policy_snapshot: CasePolicySnapshot
    team_id: TeamId | None = None
    priority: CasePriority | None = None
    client_scope_label: str | None = None
    jurisdiction_resolution: BrowserJurisdictionResolution | None = None
    registry_route: RegistryRoutingDecision | None = None
    state: WorkflowState
    entity: BrowserCanonicalLegalEntity | None = None
    registry_acquisition: BrowserRegistryAcquisition | None = None
    registry_evidence_binding: BrowserRegistryEvidenceBinding | None = None
    goldtier_result: GoldTierResult | None = None
    events: list[WorkflowEvent]
    error: SafeError | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(
        cls, case: OnboardingCase, team: TeamRecord | None = None
    ) -> "OnboardingCaseResponse":
        """Project a domain case without serializing its registry source link."""

        binding = case.registry_evidence_binding
        if (
            binding is not None
            and binding.cache_key.provider_identity.environment != SourceEnvironment.MOCK
        ):
            raise ValueError("browser registry evidence binding requires Mock provenance")
        browser_binding = (
            BrowserRegistryEvidenceBinding(
                disposition=binding.disposition,
                bound_to_case_at=binding.bound_to_case_at,
                expires_at=binding.expires_at,
                freshness_policy_id=binding.freshness_policy.policy_id,
                freshness_policy_version=binding.freshness_policy.version,
                freshness_duration_seconds=binding.freshness_policy.duration_seconds,
                freshness_comparator=binding.freshness_policy.comparator,
            )
            if binding is not None
            else None
        )
        projected_values = {
            name: getattr(case, name)
            for name in cls.model_fields
            if name not in {"client_scope_label", "registry_evidence_binding"}
        }
        return cls.model_validate(
            {
                **projected_values,
                "client_scope_label": (
                    team.client_scope_label if team is not None else None
                ),
                "registry_evidence_binding": browser_binding,
            }
        )


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
    size_bytes: int
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
        cls,
        record: ClmOrchestrationRecord,
        case: OnboardingCase,
        team: TeamRecord | None = None,
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
            case=OnboardingCaseResponse.from_domain(case, team),
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


class BrowserReconciliationObservation(BaseModel):
    """Normalized browser evidence; raw source text remains in backend domain records."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: UUID
    field_name: ReconciliationField
    normalized_value: str | None
    source_kind: ReconciliationSourceKind
    source_system: str | None
    environment: str | None
    observed_at: datetime
    evidence_reference: str | None
    document_id: UUID | None
    document_display_name: str | None
    confidence: float | None
    validity: ObservationValidity


class BrowserReconciliationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action: ReconciliationDecisionAction
    selected_observation_id: UUID
    selected_value: str
    decided_at: datetime
    reconciliation_version: int


class BrowserReconciliationDiscrepancy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    discrepancy_id: UUID
    field_name: ReconciliationField
    outcome: ReconciliationOutcome
    observations: tuple[BrowserReconciliationObservation, ...]
    status: DiscrepancyStatus
    allowed_actions: tuple[ReconciliationDecisionAction, ...]
    evidence_fingerprint: str
    decision: BrowserReconciliationDecision | None


class BrowserFieldReconciliation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    field_name: ReconciliationField
    observations: tuple[BrowserReconciliationObservation, ...]
    outcome: ReconciliationOutcome
    discrepancy_id: UUID | None


class ReconciliationResponse(BaseModel):
    """Safe current state plus retained discrepancy decisions and superseded history."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    reconciliation_id: UUID
    version: int
    status: ReconciliationStatus
    source_document_ids: tuple[UUID, ...]
    source_document_event_counts: tuple[int, ...]
    fields: tuple[BrowserFieldReconciliation, ...]
    discrepancies: tuple[BrowserReconciliationDiscrepancy, ...]
    updated_at: datetime

    @classmethod
    def from_domain(cls, record: ReconciliationCaseRecord) -> "ReconciliationResponse":
        def observations(
            values: tuple[ReconciliationObservation, ...],
        ) -> tuple[BrowserReconciliationObservation, ...]:
            return tuple(
                BrowserReconciliationObservation(
                    observation_id=item.observation_id,
                    field_name=item.field_name,
                    normalized_value=item.normalized_value,
                    source_kind=item.source_kind,
                    source_system=item.source_system,
                    environment=item.environment,
                    observed_at=item.observed_at,
                    evidence_reference=item.evidence_reference,
                    document_id=item.source_record_id,
                    document_display_name=item.source_display_name,
                    confidence=item.confidence,
                    validity=item.validity,
                )
                for item in values
            )

        return cls(
            reconciliation_id=record.reconciliation_id,
            version=record.version,
            status=record.status,
            source_document_ids=record.source_document_ids,
            source_document_event_counts=record.source_document_event_counts,
            fields=tuple(
                BrowserFieldReconciliation(
                    field_name=item.field_name,
                    observations=observations(item.observations),
                    outcome=item.outcome,
                    discrepancy_id=item.discrepancy_id,
                )
                for item in record.fields
            ),
            discrepancies=tuple(
                BrowserReconciliationDiscrepancy(
                    discrepancy_id=item.discrepancy_id,
                    field_name=item.field_name,
                    outcome=item.outcome,
                    observations=observations(item.observations),
                    status=item.status,
                    allowed_actions=item.allowed_actions,
                    evidence_fingerprint=item.evidence_fingerprint,
                    decision=(
                        BrowserReconciliationDecision(
                            action=item.decision.action,
                            selected_observation_id=(item.decision.selected_observation_id),
                            selected_value=item.decision.selected_value,
                            decided_at=item.decision.decided_at,
                            reconciliation_version=(item.decision.reconciliation_version),
                        )
                        if item.decision is not None
                        else None
                    ),
                )
                for item in record.discrepancies
            ),
            updated_at=record.updated_at,
        )


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
    reconciliation: ReconciliationResponse | None
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
        reconciliation: ReconciliationCaseRecord | None = None,
        target_operations: tuple["BrowserTargetOperationEvidence", ...] = (),
        team: TeamRecord | None = None,
    ) -> "ZeroTouchCaseSummaryResponse":
        return cls(
            case=OnboardingCaseResponse.from_domain(case, team),
            clm=ClmCaseSummaryResponse.from_domain(clm_record, case, team),
            automation_id=record.automation_id,
            version=record.version,
            status=record.status,
            current_stage=record.current_stage,
            completed_stages=record.completed_stages,
            active_exceptions=[
                BusinessExceptionResponse.model_validate(item) for item in record.active_exceptions
            ],
            reconciliation=(
                ReconciliationResponse.from_domain(reconciliation)
                if reconciliation is not None
                else None
            ),
            technical_failure=record.technical_failure,
            metrics=record.metrics,
            target_operations=target_operations,
            timeline=record.events,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class ZeroTouchCaseListItemResponse(BaseModel):
    """Lightweight process-local portfolio item with no evidence graph or payloads."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: UUID
    requested_uen: str
    legal_name: str | None
    status: AutomationStatus
    current_stage: AutomationStage
    updated_at: datetime
    active_exception_count: int
    human_interventions: int
    final_outcome: str | None
    team_id: TeamId | None
    client_scope_label: str | None
    priority: CasePriority | None
    resolved_jurisdiction: JurisdictionCode | None
    created_at: datetime
    completed_at: datetime | None
    mock_goldtier_party_id: str | None

    @classmethod
    def from_domain(
        cls, record: CasePortfolioRecord, team: TeamRecord | None = None
    ) -> "ZeroTouchCaseListItemResponse":
        return cls(
            case_id=record.case_id,
            requested_uen=record.requested_uen,
            legal_name=record.legal_name,
            status=record.status,
            current_stage=record.current_stage,
            updated_at=record.updated_at,
            active_exception_count=record.active_exception_count,
            human_interventions=record.human_interventions,
            final_outcome=record.final_outcome,
            team_id=record.team_id,
            client_scope_label=team.client_scope_label if team is not None else None,
            priority=record.priority,
            resolved_jurisdiction=record.resolved_jurisdiction,
            created_at=record.created_at,
            completed_at=record.completed_at,
            mock_goldtier_party_id=record.mock_goldtier_party_id,
        )


class CasePriorityResponse(BaseModel):
    """Authoritative priority result without workflow or access-policy internals."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: UUID
    team_id: TeamId | None
    priority: CasePriority | None
    updated_at: datetime

    @classmethod
    def from_domain(cls, case: OnboardingCase) -> "CasePriorityResponse":
        return cls(
            case_id=case.case_id,
            team_id=case.team_id,
            priority=case.priority,
            updated_at=case.updated_at,
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
