"""Browser-facing API models that exclude internal registry proof references."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.access import CasePriority, TeamId
from app.domain.administration import TeamRecord
from app.domain.case_management import (
    CaseActivityItem,
    CaseActivityPage,
    CasePortfolioRecord,
    CaseTimingProjection,
    ObservedCasePortfolioPage,
    ObservedCasePortfolioRecord,
)
from app.domain.clm import (
    ClmOrchestrationRecord,
    ClmReadinessAssessment,
    ClmStatus,
    ClmWorkflowEvent,
    GoldTierSearchCheckpoint,
    GoldTierSearchDisposition,
    GoldTierSubmissionPlan,
    RelatedPartySubmissionPreparation,
    can_confirm_existing_customer,
)
from app.domain.documents import (
    ComparisonStatus,
    DocumentCompletionMethod,
    DocumentFieldCandidate,
    DocumentFieldKey,
    DocumentOwnershipObservation,
    DocumentPageEvidence,
    DocumentProcessingRecord,
    DocumentProcessingState,
    DocumentProfile,
    DocumentWorkflowEvent,
    ExtractionMetadata,
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
    EventOutcome,
    GoldTierResult,
    InitialCustomerIdentity,
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
    TargetDispatchConfirmation,
    WorkflowEvent,
    WorkflowState,
)
from app.domain.onboarding_intelligence import (
    ClassificationConsistencyAdvisory,
    assess_classification_consistency,
)
from app.domain.ownership import (
    OWNER_DECLARED_PERCENT_SOURCE_SUFFIX,
    ManualOwnershipReviewReceipt,
    OwnershipAnalysisIssue,
    OwnershipAnalysisRecord,
    OwnershipAnalysisState,
    OwnershipBasis,
    OwnershipCandidate,
    OwnershipDiscoveryAudit,
    OwnershipDocumentBinding,
    OwnershipDocumentDiscrepancy,
    OwnershipEnvironment,
    OwnershipPathEvidence,
    OwnershipPocAcceptance,
    OwnershipProvenance,
    OwnershipRelationshipType,
    OwnershipSourceClassification,
    OwnershipWorkflowEvent,
    Party,
)
from app.domain.ownership_evidence import OwnershipEvidence, OwnershipTaggingResult
from app.domain.policy import (
    GOLDTIER_BOOKING_ENTITY_POC_VALUE,
    GOLDTIER_CLIENT_SEGMENT_VALUES,
    GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM_POC_VALUE,
    GOLDTIER_KYC_CUSTOMER_TYPE_VALUES,
    GOLDTIER_POLICY_POC_VALUE,
    GOLDTIER_REGISTRATION_TYPE_POC_VALUE,
    CasePolicySnapshot,
    PolicyAuthority,
)
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
from app.domain.registry_dataset import local_synthetic_registry_identity
from app.domain.registry_legal_form import RegistryLegalForm
from app.domain.target_classification import (
    ClassificationAssessmentState,
    TargetClassificationAssessment,
    TargetClassificationKey,
    TargetClassificationSelection,
)
from app.domain.zero_touch import (
    LEGACY_AUTOMATION_STAGE_ORDER_VERSION,
    AutomationEvent,
    AutomationEventType,
    AutomationMetrics,
    AutomationStage,
    AutomationStatus,
    BlockerDecisionMetadata,
    BusinessExceptionStatus,
    BusinessExceptionType,
    ExceptionResolutionAction,
    SafeExceptionEvidence,
    ZeroTouchAutomationRecord,
)
from app.services.government_status import (
    government_profile_applies,
    government_status_confirmed,
    government_status_evidence,
)
from app.services.partnership_agreement import registry_partner_names

ProcessingNodeStatus = Literal[
    "UNSUPPORTED",
    "COMPLETE",
    "IN_PROGRESS",
    "EMPTY",
    "SKIPPED",
    "REVIEW_REQUIRED",
    "BLOCKED",
    "FAILED",
    "NOT_REACHED",
]


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
    source_category: str | None = None
    source_status: str | None = None
    share_allotted: Decimal | None = None
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

    synthetic_seed_namespace: Literal["LOCAL_SYNTHETIC_UAT_V1"] | None = None
    disposition: RegistryEvidenceDisposition
    bound_to_case_at: datetime
    expires_at: datetime
    freshness_policy_id: Literal["MOCK_ACRA_FIXED_90D", "MOCK_ACRA_APPROVED_POLICY"]
    freshness_policy_version: int
    freshness_duration_seconds: int
    freshness_comparator: Literal["EVALUATION_NOW_LT_EXPIRES_AT"]


class BrowserPolicyRebindMetadata(BaseModel):
    """Safe policy authority categories and latest case-owned rebind receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    revision: int = Field(ge=1)
    configuration_status: Literal["CURRENT_ACCEPTED_POC", "REQUIRES_REBIND"]
    accepted_poc_fields: tuple[str, ...]
    editable_fields: tuple[str, ...] = ("kycCustomerType", "clientSegment")
    upstream_fields: tuple[str, ...] = ("registrationNumber",)
    unavailable_fields: tuple[str, ...]
    last_rebound_by: str | None = None
    last_rebound_at: datetime | None = None
    last_rationale: str | None = None
    last_changed_fields: tuple[str, ...] = ()

    @classmethod
    def from_domain(cls, case: OnboardingCase) -> "BrowserPolicyRebindMetadata":
        target = case.policy_snapshot.goldtier_target
        expected = {
            "customerExternalSystem": (
                "customer_external_system",
                GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM_POC_VALUE,
                PolicyAuthority.SPONSOR_DOCUMENTED,
            ),
            "registrationType": (
                "registration_type",
                GOLDTIER_REGISTRATION_TYPE_POC_VALUE,
                PolicyAuthority.USER_AUTHORIZED_POC,
            ),
            "policy": (
                "policy",
                GOLDTIER_POLICY_POC_VALUE,
                PolicyAuthority.SPONSOR_DOCUMENTED,
            ),
            "bookingEntity": (
                "booking_entity",
                GOLDTIER_BOOKING_ENTITY_POC_VALUE,
                PolicyAuthority.USER_AUTHORIZED_POC,
            ),
        }
        accepted = tuple(
            name
            for name, (attribute, value, authority) in expected.items()
            if target is not None
            and getattr(target, attribute).value == value
            and getattr(target, attribute).authority == authority
        )
        unavailable = tuple(
            name
            for name, attribute in (
                ("accountEntityType", "account_entity_type"),
                ("productType", "product_type"),
            )
            if target is None
            or getattr(target, attribute).authority
            in {PolicyAuthority.TBD_SPONSOR, PolicyAuthority.PROJECT_DEFINED_PROVISIONAL}
            or getattr(target, attribute).value == "TBD_SPONSOR"
        )
        latest = case.policy_rebind_history[-1] if case.policy_rebind_history else None
        return cls(
            revision=case.policy_snapshot_revision,
            configuration_status=(
                "CURRENT_ACCEPTED_POC"
                if len(accepted) == len(expected)
                else "REQUIRES_REBIND"
            ),
            accepted_poc_fields=accepted,
            unavailable_fields=unavailable,
            last_rebound_by=latest.actor_id if latest is not None else None,
            last_rebound_at=latest.rebound_at if latest is not None else None,
            last_rationale=latest.rationale if latest is not None else None,
            last_changed_fields=latest.changed_fields if latest is not None else (),
        )


class BrowserIdentityCorrectionEvidence(BaseModel):
    """Correction receipt; previous canonical/provider evidence stays backend-only."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")
    correction_id: UUID
    actor_id: str
    evidence_type: str
    previous_identity: InitialCustomerIdentity | None = None
    corrected_identity: InitialCustomerIdentity
    previous_search_request_id: UUID | None = None
    choice: Literal["ENTERED", "DOCUMENT", "OTHER"] = "OTHER"
    source_document_id: UUID | None = None
    source_document_event_count: int | None = None
    corrected_at: datetime


class OnboardingCaseResponse(BaseModel):
    """Application case response with internal proof metadata minimized."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    case_id: UUID
    source_case_id: str
    correlation_id: UUID
    requested_uen: str
    initial_identity: InitialCustomerIdentity | None = None
    identity_corrections: tuple[BrowserIdentityCorrectionEvidence, ...] = ()
    target_dispatch_confirmation: TargetDispatchConfirmation | None = None
    policy_snapshot: CasePolicySnapshot
    policy_snapshot_revision: int
    policy_rebind: BrowserPolicyRebindMetadata
    team_id: TeamId | None = None
    created_by_actor_id: str | None = None
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
                synthetic_seed_namespace=(
                    "LOCAL_SYNTHETIC_UAT_V1"
                    if binding.cache_key.provider_identity == local_synthetic_registry_identity()
                    else None
                ),
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
            if name
            not in {"client_scope_label", "registry_evidence_binding", "policy_rebind"}
        }
        return cls.model_validate(
            {
                **projected_values,
                "client_scope_label": (team.client_scope_label if team is not None else None),
                "registry_evidence_binding": browser_binding,
                "policy_rebind": BrowserPolicyRebindMetadata.from_domain(case),
            }
        )


class BrowserFieldProvenance(BaseModel):
    """Safe source/page metadata without raw provider output."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    provider: str
    environment: IdpEnvironment
    page_number: int | None
    source_reference: str


class BrowserExtractedField(ExtractionMetadata):
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
    candidates: tuple[DocumentFieldCandidate, ...] = ()


class DocumentProcessingResponse(BaseModel):
    """Document response without bytes, paths, or raw provider evidence."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    case_id: UUID
    document_id: UUID
    document_version: Literal[1] | None = None
    correlation_id: UUID
    display_name: str
    media_type: str
    size_bytes: int
    profile: DocumentProfile
    provider_environment: IdpEnvironment | None
    state: DocumentProcessingState
    fields: list[BrowserExtractedField]
    pages: tuple[DocumentPageEvidence, ...] = ()
    ownership_observations: tuple[DocumentOwnershipObservation, ...] = ()
    events: list[DocumentWorkflowEvent]
    error: SafeError | None = None
    created_at: datetime
    processed_at: datetime | None = None
    reviewed_at: datetime | None = None
    completion_method: DocumentCompletionMethod | None = None
    semantic_completion: Literal["RECONCILIATION_RESOLVED"] | None = None
    reconciliation_version: int | None = None
    supersedes_document_id: UUID | None = None
    superseded_by_document_id: UUID | None = None
    superseded_at: datetime | None = None
    updated_at: datetime
    review_source_fingerprint: str | None = None

    @classmethod
    def from_domain(cls, record: DocumentProcessingRecord) -> "DocumentProcessingResponse":
        from app.domain.review_decisions import document_review_source_fingerprint

        return cls.model_validate(record).model_copy(update={
            "review_source_fingerprint": document_review_source_fingerprint(record),
        })


class DocumentDigestResponse(BaseModel):
    """D-095: one document's backend-computed content digest, for the AI assistant's synthetic
    fixture check only. Not part of the browser document projection; never document content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: UUID
    document_version: Literal[1] | None = None
    content_sha256: str | None = None


class OwnershipAnalysisResponse(BaseModel):
    """Browser-required ownership graph and deterministic evidence only."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    case_id: UUID
    evidence: tuple[OwnershipEvidence, ...] = ()
    document_observations: tuple[DocumentOwnershipObservation, ...] = ()
    document_bindings: tuple[OwnershipDocumentBinding, ...] = ()
    document_discrepancies: tuple[OwnershipDocumentDiscrepancy, ...] = ()
    source_classification: OwnershipSourceClassification = "SINGLE_SOURCE"
    prior_analyses: tuple["BrowserPriorOwnershipSnapshot", ...] = ()
    supplemental_parties: tuple[Party, ...] = ()
    supplemental_relationships: tuple["BrowserOwnershipRelationship", ...] = ()
    supplemental_evidence: tuple[OwnershipEvidence, ...] = ()
    tagging: OwnershipTaggingResult | None = None
    legal_form: RegistryLegalForm | None = None
    # Optional reviewer-safe corporate discovery audit: issuer identities, outcomes,
    # bounded root-equivalent exposure and lookup counts; never raw provider data.
    discovery: OwnershipDiscoveryAudit | None = None
    version: int
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
    manual_review_receipt: ManualOwnershipReviewReceipt | None = None
    # D-082: the persisted acceptance (audit) and whether the backend honours it now.
    poc_acceptance: OwnershipPocAcceptance | None = None
    poc_basis_accepted: bool = False
    # Presentation only: a declared-overlay simulation whose arithmetic completed. Never
    # readiness, verification or acceptance.
    simulation_calculated: bool = False
    # D-086 presentation only: engine path products reaching intermediate entities.
    entity_effective_interests: list["BrowserEntityEffectiveInterest"] = Field(
        default_factory=list
    )
    created_at: datetime
    loaded_at: datetime | None = None
    analyzed_at: datetime | None = None
    updated_at: datetime

    @classmethod
    def from_domain(
        cls,
        record: OwnershipAnalysisRecord,
        *,
        poc_basis_accepted: bool = False,
        simulation_calculated: bool = False,
        entity_effective_interests: dict[str, tuple[OwnershipPathEvidence, ...]] | None = None,
    ) -> "OwnershipAnalysisResponse":
        return cls.model_validate(record).model_copy(
            update={
                "poc_basis_accepted": poc_basis_accepted,
                "simulation_calculated": simulation_calculated,
                "entity_effective_interests": [
                    BrowserEntityEffectiveInterest(
                        party_id=party_id,
                        effective_ownership_percent=sum(
                            (path.effective_ownership_percent for path in paths),
                            start=Decimal("0"),
                        ),
                        paths=list(paths),
                    )
                    for party_id, paths in (entity_effective_interests or {}).items()
                ],
            }
        )


class BrowserEntityEffectiveInterest(BaseModel):
    """D-086 presentation only: a legal entity's root-equivalent interest from the engine.

    The exact sum of the engine's path products reaching the entity, with each path.
    Never a UBO candidate, classification, threshold result or readiness input.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    party_id: str
    effective_ownership_percent: Decimal
    paths: list[OwnershipPathEvidence]


class BrowserOwnershipProvenance(BaseModel):
    """Browser-safe provenance without internal source routing/reference data."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    provider: str
    environment: OwnershipEnvironment
    sourced_at: datetime
    # D-086: an owner-declared overlay percentage (never an ACRA quantity). Only this
    # boolean is projected; the internal source reference itself stays server-side.
    owner_declared_percentage: bool = False

    @model_validator(mode="before")
    @classmethod
    def mark_owner_declared_percentage(cls, value: Any) -> Any:
        if isinstance(value, OwnershipProvenance):
            return {
                "provider": value.provider,
                "environment": value.environment,
                "sourced_at": value.sourced_at,
                "owner_declared_percentage": value.source_reference.endswith(
                    OWNER_DECLARED_PERCENT_SOURCE_SUFFIX
                ),
            }
        return value


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


class BrowserPriorOwnershipSnapshot(BaseModel):
    """Retained safe graph and decisions for explainable pre-submission revisions."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")
    version: int
    analysis_id: UUID
    root_party_id: str | None
    provider_name: str | None
    provider_environment: OwnershipEnvironment | None
    state: OwnershipAnalysisState
    parties: list[Party]
    relationships: list[BrowserOwnershipRelationship]
    candidates: list[OwnershipCandidate]
    issues: list[OwnershipAnalysisIssue]
    evidence: tuple[OwnershipEvidence, ...] = ()
    document_observations: tuple[DocumentOwnershipObservation, ...] = ()
    document_bindings: tuple[OwnershipDocumentBinding, ...] = ()
    document_discrepancies: tuple[OwnershipDocumentDiscrepancy, ...] = ()
    source_classification: OwnershipSourceClassification = "SINGLE_SOURCE"
    manual_review_receipt: ManualOwnershipReviewReceipt | None = None
    supplemental_parties: tuple[Party, ...] = ()
    supplemental_relationships: tuple[BrowserOwnershipRelationship, ...] = ()
    supplemental_evidence: tuple[OwnershipEvidence, ...] = ()
    created_at: datetime
    analyzed_at: datetime | None


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
    target_search_checkpoint: GoldTierSearchCheckpoint | None
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
            target_search_checkpoint=record.target_search_checkpoint,
            related_party_preparation=record.related_party_preparation,
            submission=submission,
            goldtier_result=record.goldtier_result,
            timeline=record.events,
            error=record.error,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class BrowserBlockerDecision(BaseModel):
    """Safe immutable decision metadata; it grants no browser-side authority."""

    model_config = ConfigDict(from_attributes=True, extra="forbid", frozen=True)

    decision_id: UUID
    case_id: UUID
    exception_id: UUID | None
    evidence_version: str
    automation_version: int
    recorded_at: datetime
    metadata: BlockerDecisionMetadata
    actor_id: str | None
    reviewer_id: str | None


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
    decisions: tuple[BrowserBlockerDecision, ...]
    created_at: datetime
    resolved_at: datetime | None
    resolution: ExceptionResolutionAction | None


class BrowserAuthorizedInterventionAction(BaseModel):
    """One backend-authorized action and its operator-facing meaning."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action: ExceptionResolutionAction
    label: str = Field(min_length=1, max_length=96)
    description: str = Field(min_length=1, max_length=200)


class BrowserGoldTierCandidateSummary(BaseModel):
    """Bounded candidate identity fields already retained by the CLM aggregate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    party_id: str = Field(min_length=1, max_length=96)
    registration_number: str | None = Field(default=None, max_length=64)
    country: str | None = Field(default=None, max_length=3)
    legal_name: str | None = Field(default=None, max_length=160)
    legal_form: str | None = Field(default=None, max_length=80)


class BrowserInterventionEvidenceAction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    target: Literal[
        "DOCUMENTS",
        "OWNERSHIP_DETAILS",
        "OWNERSHIP_UPLOAD",
        "CLASSIFICATION",
        "IDENTITY",
        "REVIEW_SEND",
    ]
    label: str = Field(min_length=1, max_length=96)


class ExistingCustomerConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    search_request_id: UUID
    expected_automation_version: int = Field(ge=0)
    expected_clm_version: int = Field(ge=0)
    expected_case_event_count: int = Field(ge=0)
    rationale: str = Field(min_length=3, max_length=240, pattern=r"^[^\x00-\x1f]+$")

    @field_validator("rationale")
    @classmethod
    def require_rationale(cls, value: str) -> str:
        if len(value.strip()) < 3:
            raise ValueError("A bounded confirmation rationale is required")
        return value.strip()


class BrowserHumanIntervention(BaseModel):
    """Backend-authored operator projection without a second resolution engine."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    intervention_id: UUID
    owning_stage: AutomationStage
    owning_stage_label: str = Field(min_length=1, max_length=96)
    title: str = Field(min_length=1, max_length=120)
    blocker_code: str = Field(min_length=1, max_length=64)
    explanation: str = Field(min_length=1, max_length=300)
    required_evidence_or_input: tuple[str, ...] = Field(default_factory=tuple, max_length=4)
    authorized_actions: tuple[BrowserAuthorizedInterventionAction, ...] = Field(
        default_factory=tuple, max_length=4
    )
    no_action_reason: str | None = Field(default=None, max_length=240)
    expected_next_step: str = Field(min_length=1, max_length=300)
    candidate_summaries: tuple[BrowserGoldTierCandidateSummary, ...] = Field(
        default_factory=tuple, max_length=4
    )
    identity_correction_action: Literal["IDENTITY_SEARCH_RECHECK"] | None = None
    existing_customer_confirmation_action: (
        Literal["CONFIRM_EXISTING_GOLDTIER_CUSTOMER"] | None
    ) = None
    decisions: tuple[BrowserBlockerDecision, ...] = Field(default_factory=tuple, max_length=8)
    blocker_class: Literal[
        "WARNING", "RECOVERABLE_INPUT", "HUMAN_DECISION", "WAITING_EXTERNAL", "HARD_SAFETY_STOP"
    ] = "HARD_SAFETY_STOP"
    evidence_actions: tuple[BrowserInterventionEvidenceAction, ...] = Field(
        default_factory=tuple, max_length=4
    )
    dependent_stages: tuple[str, ...] = Field(default_factory=tuple, max_length=12)
    backend_mutation_owner: str = Field(min_length=1, max_length=96)
    resolution_condition: str = Field(min_length=1, max_length=300)
    resume_target: AutomationStage | None = None


_INTERVENTION_STAGE_LABELS: dict[AutomationStage, str] = {
    AutomationStage.REGISTRY: "ACRA registry",
    AutomationStage.GOLDTIER_SEARCH: "GoldTier Search / customer identity",
    AutomationStage.DOCUMENT: "Documents / reconciliation",
    AutomationStage.OWNERSHIP: "Ownership / UBO",
    AutomationStage.READINESS: "Readiness / target classification",
    AutomationStage.MOCK_GOLDTIER: "GoldTier target mutation",
    AutomationStage.COMPLETE: "Completed workflow",
}

_INTERVENTION_ACTIONS: dict[ExceptionResolutionAction, tuple[str, str]] = {
    ExceptionResolutionAction.KEEP_REGISTRY_VALUE: (
        "Keep registry value",
        "Retain the current registry observation for the bounded discrepancy.",
    ),
    ExceptionResolutionAction.USE_DOCUMENT_VALUE: (
        "Use document value",
        "Apply the supported document value through the existing reconciliation owner.",
    ),
    ExceptionResolutionAction.REQUEST_ADDITIONAL_INFORMATION: (
        "Request additional information",
        "Record that additional evidence is required before the workflow can continue.",
    ),
}


def project_human_interventions(
    *,
    automation: ZeroTouchAutomationRecord,
    clm: ClmOrchestrationRecord,
    case: OnboardingCase,
    ownership: OwnershipAnalysisRecord | None = None,
) -> tuple[BrowserHumanIntervention, ...]:
    """Project current blockers and only actions already authorized by their owners."""

    checkpoint = clm.target_search_checkpoint
    projections: list[BrowserHumanIntervention] = []
    if case.initial_identity is None and not any(
        item.blocker_code == "INITIAL_IDENTITY_INCOMPLETE" for item in automation.active_exceptions
    ):
        projections.append(
            BrowserHumanIntervention(
                intervention_id=uuid5(
                    NAMESPACE_URL,
                    f"initial-identity-incomplete:{case.case_id}",
                ),
                owning_stage=AutomationStage.REGISTRY,
                owning_stage_label=_INTERVENTION_STAGE_LABELS[AutomationStage.REGISTRY],
                title="Initial identity incomplete",
                blocker_code="INITIAL_IDENTITY_INCOMPLETE",
                explanation=(
                    "The retained case is missing an initial legal name, registration ID, "
                    "or country value required for target identity Search."
                ),
                required_evidence_or_input=(
                    "The missing legal name, registration ID, or country field.",
                ),
                authorized_actions=(),
                no_action_reason=None,
                expected_next_step=(
                    "Correct the identity and run the authorized read-only Search recheck on "
                    "this retained case before any target mutation."
                ),
                identity_correction_action="IDENTITY_SEARCH_RECHECK",
                blocker_class="RECOVERABLE_INPUT",
                evidence_actions=(
                    BrowserInterventionEvidenceAction(target="IDENTITY", label="Correct identity"),
                ),
                backend_mutation_owner="ZERO_TOUCH_ORCHESTRATION",
                resolution_condition="Supply complete canonical identity and a safe Search result.",
                resume_target=AutomationStage.GOLDTIER_SEARCH,
                decisions=(),
            )
        )
    for exception in automation.active_exceptions:
        if exception.blocker_code == "TARGET_CONFIRMATION_REQUIRED":
            # Submission control is rendered in Review and Send, separately from exceptions.
            continue
        required: tuple[str, ...] = ("Review the retained evidence identified by the blocker.",)
        title = f"Action required — {_INTERVENTION_STAGE_LABELS[exception.stage]}"
        explanation = exception.explanation
        expected = (
            "Use only a backend-authorized action below. The owning service will "
            "re-evaluate retained evidence after it accepts the decision."
        )
        no_action: str | None = (
            "No safe resolution action is authorized for this retained blocker. "
            "The workflow remains fail-closed."
        )
        candidates: tuple[BrowserGoldTierCandidateSummary, ...] = ()
        identity_correction_action: Literal["IDENTITY_SEARCH_RECHECK"] | None = None
        existing_confirmation_action: Literal["CONFIRM_EXISTING_GOLDTIER_CUSTOMER"] | None = None
        evidence_actions: tuple[BrowserInterventionEvidenceAction, ...] = ()
        classification: Literal[
            "WARNING", "RECOVERABLE_INPUT", "HUMAN_DECISION", "WAITING_EXTERNAL", "HARD_SAFETY_STOP"
        ] = "HARD_SAFETY_STOP"
        if exception.decisions:
            decision_class = exception.decisions[0].metadata.classification.value
            classes: dict[
                str,
                Literal[
                    "WARNING",
                    "RECOVERABLE_INPUT",
                    "HUMAN_DECISION",
                    "WAITING_EXTERNAL",
                    "HARD_SAFETY_STOP",
                ],
            ] = {
                "USER_ACTION_REQUIRED": "HUMAN_DECISION",
                "EXTERNAL_DEPENDENCY": "WAITING_EXTERNAL",
                "CONTINUE_WITH_WARNING": "WARNING",
            }
            classification = classes.get(decision_class, "HARD_SAFETY_STOP")

        if exception.blocker_code == "GT_SEARCH_IDENTITY_REVIEW_REQUIRED":
            title = "Possible existing customer found"
            required = (
                "Additional registration identity or provider customer-detail verification.",
            )
            expected = (
                "Case-specific documents may be retained while target identity stays unresolved. "
                "Shell, target binding, and Amend remain blocked until exact identity is proved."
            )
            no_action = (
                "The backend has not authorized candidate confirmation, manual GoldTier-ID entry, "
                "or a new-customer Shell while identity is ambiguous."
            )
            identity_correction_action = "IDENTITY_SEARCH_RECHECK"
            if (
                can_confirm_existing_customer(case, checkpoint)
                and clm.submission_snapshot is None
                and automation.current_stage == AutomationStage.GOLDTIER_SEARCH
            ):
                existing_confirmation_action = "CONFIRM_EXISTING_GOLDTIER_CUSTOMER"
                identity_correction_action = None
                no_action = None
                required = ("Compare the retained candidate and confirm with a bounded rationale.",)
                expected = (
                    "The creator may confirm this retained existing customer. Confirmation makes "
                    "no target call; document and ownership review and final Review & Send remain."
                )
            if checkpoint is not None:
                candidates = tuple(
                    BrowserGoldTierCandidateSummary(
                        party_id=str(item.party_id),
                        registration_number=item.registration_number,
                        country=item.country,
                        legal_name=item.legal_name,
                        legal_form=item.legal_form,
                    )
                    for item in checkpoint.candidates[:4]
                )
        elif exception.blocker_code == "REGISTRY_EXPECTED_DATA_MISSING":
            title = "Registry evidence incomplete"
            required = (
                "Complete ownership or relationship evidence, or an explicitly authorized "
                "manual-review decision.",
            )
            expected = (
                "The successful registry connection remains retained. Continue only through an "
                "action listed below; ignoring the missing evidence is not authorized."
            )
            no_action = (
                "No ignore-and-continue action is authorized. Supply complete evidence or await an "
                "approved manual-review path."
            )
        elif exception.blocker_code == "INITIAL_IDENTITY_INCOMPLETE":
            title = "Initial identity incomplete"
            required = ("The missing legal name, registration ID, or country field.",)
            expected = (
                "Correct the identity and run the authorized read-only Search recheck on this "
                "retained case before any target mutation."
            )
            no_action = None
            identity_correction_action = "IDENTITY_SEARCH_RECHECK"
        elif (
            exception.blocker_code in {
                "INITIAL_IDENTITY_NOT_ELIGIBLE",
                "REGISTRY_IDENTIFIER_NOT_ELIGIBLE",
                "ACRA_ENTITY_NOT_FOUND",
                "REGISTRY_RECHECK_INCOMPLETE",
            }
            and case.target_dispatch_confirmation is None
            and case.goldtier_result is None
            and clm.submission_snapshot is None
            and automation.status != AutomationStatus.COMPLETED
        ):
            title = "Registry identity requires correction"
            classification = "RECOVERABLE_INPUT"
            required = ("A valid Singapore UEN and current same-case identity.",)
            expected = (
                "Correct the UEN on this case. The registry owner verifies it and invalidates "
                "identity-dependent evidence before the bounded read-only Search recheck."
            )
            no_action = None
            identity_correction_action = "IDENTITY_SEARCH_RECHECK"
        elif exception.blocker_code in {
            "UNCERTAIN_TARGET_MUTATION",
            "TARGET_OPERATION_OUTCOME_UNCERTAIN",
        }:
            title = "Provider verification required"
            classification = "HARD_SAFETY_STOP"
            required = ("Provider-side verification of the retained attempted operation.",)
            expected = "Verify the provider outcome without replaying the mutation."
            no_action = "Automatic retry or replay is not authorized for an uncertain mutation."
        elif exception.blocker_code == "PROVIDER_VALIDATION_FAILED":
            title = "Provider validation failed"
            required = ("Provider diagnosis and authority for any corrected future request.",)
            expected = (
                "Retain the failed outcome and diagnose it before any separately authorized "
                "attempt."
            )
            no_action = (
                "Retry is not authorized because safe idempotency and corrected input are unproved."
            )
        elif exception.stage == AutomationStage.DOCUMENT:
            title = "Document or reconciliation review required"
            required = ("Current document evidence or a supported reconciliation decision.",)
            evidence_actions = (
                BrowserInterventionEvidenceAction(
                    target="DOCUMENTS", label="Review document evidence"
                ),
            )
            no_action = None
            if "MISSING" in exception.blocker_code or exception.blocker_code == "DOCUMENT_REQUIRED":
                classification = "RECOVERABLE_INPUT"
        elif exception.exception_type == BusinessExceptionType.GOVERNMENT_STATUS_REQUIRED:
            # D-101: never offer ownership inputs for a Government entity.
            title = "Government status — needs confirmation"
            classification = "RECOVERABLE_INPUT"
            required = (
                "One current reviewed status document with the legal name, UEN, founding "
                "instrument, KYC Customer Type: Government and Client Segment: DI - Government.",
            )
            expected = (
                "The case creator confirms Government status in the Government status step; "
                "no ownership or UBO analysis applies and automation then resumes."
            )
            no_action = None
        elif exception.stage == AutomationStage.OWNERSHIP and (
            ownership is not None
            and ownership.state == OwnershipAnalysisState.REVIEW_REQUIRED
            and automation.current_stage == AutomationStage.OWNERSHIP
            and case.target_dispatch_confirmation is None
            and case.goldtier_result is None
            and clm.submission_snapshot is None
            and clm.status != ClmStatus.SUBMITTING
        ):
            title = "Ownership and UBO — needs input"
            classification = "RECOVERABLE_INPUT"
            required = (
                "Case-bound ownership percentages, as-of date and "
                "client-supplied evidence; reviewer note is optional.",
            )
            expected = (
                "Save valid structured ownership evidence; the existing Decimal engine "
                "recalculates UBOs and resumes automatically."
            )
            no_action = None
            evidence_actions = (
                BrowserInterventionEvidenceAction(
                    target="OWNERSHIP_DETAILS", label="Add structured ownership details"
                ),
                BrowserInterventionEvidenceAction(
                    target="OWNERSHIP_UPLOAD", label="Upload ownership evidence"
                ),
            )
            acquisition = case.registry_acquisition
            if (
                ownership.provider_name == "ACRA_REGISTRY_ACQUISITION"
                and acquisition is not None
                and any(
                    operation.operation == RegistryOperation.OWNERSHIP_PARTIES
                    and operation.status == RegistryOperationStatus.EMPTY
                    for operation in acquisition.operation_results
                )
            ):
                explanation = (
                    "ACRA did not provide sufficient ownership information for this entity. "
                    "Provide reviewed client-supplied ownership information "
                    "to continue UBO analysis."
                )
        elif exception.stage == AutomationStage.READINESS:
            title = "Readiness input required"
            required = ("Complete the backend-declared case classification or readiness evidence.",)
            if (
                exception.blocker_code == "GOLDTIER_CLASSIFICATION_REQUIRED"
                and clm.submission_snapshot is None
                and case.target_dispatch_confirmation is None
            ):
                classification = "RECOVERABLE_INPUT"
                title = "Target classification — needs input"
                evidence_actions = (
                    BrowserInterventionEvidenceAction(
                        target="CLASSIFICATION", label="Set target classification"
                    ),
                )
                no_action = None

        if identity_correction_action is not None:
            evidence_actions = (
                BrowserInterventionEvidenceAction(
                    target="IDENTITY", label="Correct identity and recheck"
                ),
            )
        actions = tuple(
            BrowserAuthorizedInterventionAction(
                action=action,
                label=_INTERVENTION_ACTIONS[action][0],
                description=_INTERVENTION_ACTIONS[action][1],
            )
            for action in exception.available_actions
        )
        projections.append(
            BrowserHumanIntervention(
                intervention_id=exception.exception_id,
                owning_stage=exception.stage,
                owning_stage_label=_INTERVENTION_STAGE_LABELS[exception.stage],
                title=title,
                blocker_code=exception.blocker_code,
                explanation=explanation,
                required_evidence_or_input=required,
                authorized_actions=actions,
                no_action_reason=None if actions else no_action,
                expected_next_step=expected,
                candidate_summaries=candidates,
                identity_correction_action=identity_correction_action,
                existing_customer_confirmation_action=existing_confirmation_action,
                blocker_class=classification,
                evidence_actions=evidence_actions,
                dependent_stages=tuple(
                    dependency.value
                    for dependency in (
                        exception.decisions[0].metadata.invalidated_dependencies
                        if exception.decisions else ()
                    )
                ),
                backend_mutation_owner=(
                    exception.decisions[0].metadata.owner.value
                    if exception.decisions else "ZERO_TOUCH_ORCHESTRATION"
                ),
                resolution_condition=expected,
                resume_target=(
                    exception.decisions[0].metadata.resume_stage
                    if exception.decisions else None
                ),
                decisions=tuple(
                    BrowserBlockerDecision.model_validate(item) for item in exception.decisions
                ),
            )
        )
    return tuple(projections)


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
    document_required: bool
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
                    document_required=item.document_required,
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


class BrowserProcessingNode(BaseModel):
    """Safe backend-authored workflow node; never includes raw provider evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str = Field(pattern=r"^[A-Z0-9_]+$", max_length=64)
    label: str = Field(min_length=1, max_length=96)
    status: ProcessingNodeStatus
    provider: str | None = Field(default=None, max_length=64)
    environment: str | None = Field(default=None, max_length=64)
    operation: str | None = Field(default=None, max_length=64)
    backend_stage: AutomationStage | None = None
    timestamp: datetime | None = None
    safe_result: str | None = Field(default=None, max_length=160)
    record_count: int | None = Field(default=None, ge=0, le=128)
    blocker_code: str | None = Field(default=None, max_length=64)
    retained_goldtier_id: str | None = Field(default=None, min_length=1, max_length=96)
    children: tuple["BrowserProcessingNode", ...] = Field(default_factory=tuple, max_length=12)


class BrowserTargetClassificationField(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    selection: TargetClassificationSelection | None = None
    allowed_values: tuple[str, ...]
    selected_value: str | None = None
    authority: PolicyAuthority | None = None
    required: Literal[True] = True


class BrowserTargetClassification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    vocabulary_version: Literal["GOLDTIER_OPENAPI_V1_0_0"] = "GOLDTIER_OPENAPI_V1_0_0"
    editable: bool
    evidence_state: ClassificationAssessmentState | None = None
    evidence_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    current: bool | None = None
    review_required: bool = False
    evidence_values: dict[TargetClassificationKey, tuple[str, ...]] = Field(default_factory=dict)
    state: Literal["CURRENT", "REVIEW_REQUIRED", "CONFLICT"] = "REVIEW_REQUIRED"
    kyc_customer_type: BrowserTargetClassificationField
    client_segment: BrowserTargetClassificationField

    @classmethod
    def from_case(
        cls,
        case: OnboardingCase,
        assessment: TargetClassificationAssessment | None = None,
        *,
        review_required: bool = False,
    ) -> "BrowserTargetClassification":
        target = case.policy_snapshot.goldtier_target

        def selected(item: object) -> tuple[str | None, PolicyAuthority | None]:
            if item is None:
                return None, None
            value = getattr(item, "value", None)
            authority = getattr(item, "authority", None)
            if authority == PolicyAuthority.TBD_SPONSOR or value == "TBD_SPONSOR":
                return None, None
            return value, authority

        kyc_value, kyc_authority = selected(target.kyc_customer_type if target else None)
        segment_value, segment_authority = selected(target.client_segment if target else None)
        frozen = (
            case.target_dispatch_confirmation is not None
            or case.goldtier_result is not None
            or case.state
            in {
                WorkflowState.GT_SHELL_CREATED,
                WorkflowState.GT_POLICY_CREATED,
                WorkflowState.GT_ENRICHED,
                WorkflowState.COMPLETED,
            }
        )
        return cls(
            editable=target is not None and not frozen,
            evidence_state=assessment.state if assessment else None,
            evidence_fingerprint=assessment.evidence_fingerprint if assessment else None,
            current=assessment.selections_are_current(case.target_classification_selections)
            if assessment
            else None,
            review_required=review_required,
            evidence_values=(
                {field.field_key: field.trusted_values for field in assessment.fields}
                if assessment
                else {}
            ),
            state=(
                "CONFLICT"
                if review_required
                and assessment is not None
                and assessment.state == ClassificationAssessmentState.CONFLICT
                else "REVIEW_REQUIRED"
                if review_required
                else "CURRENT"
            ),
            kyc_customer_type=BrowserTargetClassificationField(
                selection=next(
                    (
                        item
                        for item in case.target_classification_selections
                        if item.field_key == "kyc_customer_type"
                    ),
                    None,
                ),
                allowed_values=GOLDTIER_KYC_CUSTOMER_TYPE_VALUES,
                selected_value=kyc_value,
                authority=kyc_authority,
            ),
            client_segment=BrowserTargetClassificationField(
                selection=next(
                    (
                        item
                        for item in case.target_classification_selections
                        if item.field_key == "client_segment"
                    ),
                    None,
                ),
                allowed_values=GOLDTIER_CLIENT_SEGMENT_VALUES,
                selected_value=segment_value,
                authority=segment_authority,
            ),
        )


GOVERNMENT_IDENTITY_LABEL: Literal[
    "Local synthetic identity: not ACRA-registered; government status from reviewed document"
] = "Local synthetic identity: not ACRA-registered; government status from reviewed document"
PARTNERSHIP_CONFIRMED_LABEL: Literal["Partner shares from partnership agreement, RM-confirmed"] = (
    "Partner shares from partnership agreement, RM-confirmed"
)
PARTNERSHIP_PENDING_LABEL: Literal[
    "Partner shares from partnership agreement, awaiting RM confirmation"
] = "Partner shares from partnership agreement, awaiting RM confirmation"


class BrowserGovernmentStatus(BaseModel):
    """D-101 Government status step; never an ACRA verification or approval."""

    model_config = ConfigDict(extra="forbid")

    state: Literal["EVIDENCE_REQUIRED", "CONFIRMATION_REQUIRED", "CONFIRMED"]
    document_id: UUID | None = None
    document_event_count: int | None = None
    founding_instrument: str | None = None
    confirmed_by_actor_id: str | None = None
    confirmed_at: datetime | None = None


class BrowserEntityTypeBasis(BaseModel):
    """D-101 derived labels for the non-company demo entity types (not stored)."""

    model_config = ConfigDict(extra="forbid")

    entity_type: Literal["PARTNERSHIP", "GOVERNMENT"]
    label: str = Field(min_length=1, max_length=120)
    partnership_state: Literal["AWAITING_RM_CONFIRMATION", "RM_CONFIRMED"] | None = None
    government_status: BrowserGovernmentStatus | None = None


def project_entity_type_basis(
    case: OnboardingCase,
    ownership: OwnershipAnalysisRecord | None,
    documents: list[DocumentProcessingRecord],
) -> BrowserEntityTypeBasis | None:
    threshold = float(case.policy_snapshot.idp_review_confidence_threshold)
    if government_profile_applies(case):
        evidence = government_status_evidence(case, documents, confidence_threshold=threshold)
        confirmation = case.government_status_confirmation
        confirmed = government_status_confirmed(case, documents, confidence_threshold=threshold)
        return BrowserEntityTypeBasis(
            entity_type="GOVERNMENT",
            label=GOVERNMENT_IDENTITY_LABEL,
            government_status=BrowserGovernmentStatus(
                state=(
                    "CONFIRMED" if confirmed
                    else "CONFIRMATION_REQUIRED" if evidence is not None
                    else "EVIDENCE_REQUIRED"
                ),
                document_id=evidence.document_id if evidence is not None else None,
                document_event_count=(
                    evidence.document_event_count if evidence is not None else None
                ),
                founding_instrument=(
                    evidence.founding_instrument if evidence is not None else None
                ),
                confirmed_by_actor_id=(
                    confirmation.actor_id if confirmed and confirmation is not None else None
                ),
                confirmed_at=(
                    confirmation.confirmed_at if confirmed and confirmation is not None else None
                ),
            ),
        )
    if registry_partner_names(case.registry_acquisition):
        confirmed = (
            ownership is not None
            and ownership.state == OwnershipAnalysisState.ANALYZED
            and ownership.manual_review_receipt is not None
        )
        return BrowserEntityTypeBasis(
            entity_type="PARTNERSHIP",
            label=PARTNERSHIP_CONFIRMED_LABEL if confirmed else PARTNERSHIP_PENDING_LABEL,
            partnership_state="RM_CONFIRMED" if confirmed else "AWAITING_RM_CONFIRMATION",
        )
    return None


class BrowserOwnershipRecovery(BaseModel):
    """Safe current ownership action metadata and optional manual review receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    analysis_id: UUID
    version: int = Field(ge=1)
    state: OwnershipAnalysisState
    manual_evidence_action: Literal["MANUAL_OWNERSHIP_EVIDENCE"] | None = None
    review_receipt: ManualOwnershipReviewReceipt | None = None


class BrowserTargetSubmissionEvidence(BaseModel):
    """Derived presentation only; the existing target ledger owns completion."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    submission_id: UUID | None
    state: Literal[
        "NOT_SUBMITTED", "SENDING", "SUBMISSION_CONFIRMED", "SUBMISSION_FAILED",
        "SUBMISSION_OUTCOME_UNCERTAIN", "FINALIZATION_PENDING",
    ]
    goldtier_id: str | None = Field(default=None, max_length=96)
    status_check_available: bool = False
    verification_available: bool = False
    customer_handling: Literal["EXISTING_REUSED", "NEW_CREATED"] | None = None
    recovery_operation: Literal["SHELL", "POLICY"] | None = None
    recovery_available: bool = False
    provider_policy: str | None = None
    uncertainty_reason: Literal[
        "TIMEOUT", "TRANSPORT", "RESPONSE_DECODE", "RESPONSE_TOO_LARGE",
        "UNEXPECTED_STATUS", "UNKNOWN",
    ] | None = None
    ledger_state: str | None = None
    attempted_operations: tuple[str, ...] = ()
    definitively_completed_operations: tuple[str, ...] = ()
    lifecycle_resolved_operations: tuple[str, ...] = ()


class BrowserDocumentRefreshRecovery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    can_resume: bool


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
    historical_exceptions: list[BusinessExceptionResponse]
    non_blocking_decisions: tuple[BrowserBlockerDecision, ...]
    interventions: tuple[BrowserHumanIntervention, ...]
    reconciliation: ReconciliationResponse | None
    technical_failure: SafeError | None
    metrics: AutomationMetrics
    target_operations: tuple["BrowserTargetOperationEvidence", ...]
    target_submission: BrowserTargetSubmissionEvidence | None = None
    stage_order_version: Literal[1, 2]
    processing_pipeline: tuple[BrowserProcessingNode, ...]
    target_classification: BrowserTargetClassification
    classification_consistency: ClassificationConsistencyAdvisory
    ownership_recovery: BrowserOwnershipRecovery | None
    evidence_decision_authorized: bool = False
    document_replacement_authorized: bool = False
    document_refresh_recovery: BrowserDocumentRefreshRecovery | None = None
    ownership_edit_authorized: bool = False
    entity_type_basis: BrowserEntityTypeBasis | None = None
    timeline: list[AutomationEvent]
    created_at: datetime
    updated_at: datetime
    timing: "CaseDetailTimingResponse"

    @classmethod
    def from_domain(
        cls,
        record: ZeroTouchAutomationRecord,
        clm_record: ClmOrchestrationRecord,
        case: OnboardingCase,
        timing: "CaseDetailTimingResponse",
        reconciliation: ReconciliationCaseRecord | None = None,
        target_operations: tuple["BrowserTargetOperationEvidence", ...] = (),
        target_submission: BrowserTargetSubmissionEvidence | None = None,
        processing_pipeline: tuple[BrowserProcessingNode, ...] = (),
        team: TeamRecord | None = None,
        ownership: OwnershipAnalysisRecord | None = None,
        classification_assessment: TargetClassificationAssessment | None = None,
        evidence_decision_authorized: bool = False,
        document_replacement_authorized: bool = False,
        document_refresh_recovery_authorized: bool | None = None,
        ownership_edit_authorized: bool = False,
        entity_type_basis: BrowserEntityTypeBasis | None = None,
    ) -> "ZeroTouchCaseSummaryResponse":
        target_classification = BrowserTargetClassification.from_case(
            case, classification_assessment,
            review_required="GOLDTIER_CLASSIFICATION_REQUIRED" in clm_record.readiness.blockers,
        )
        if clm_record.submission_snapshot is not None:
            target_classification = target_classification.model_copy(update={"editable": False})
        return cls(
            case=OnboardingCaseResponse.from_domain(case, team),
            evidence_decision_authorized=evidence_decision_authorized,
            document_replacement_authorized=document_replacement_authorized,
            document_refresh_recovery=(
                BrowserDocumentRefreshRecovery(can_resume=document_refresh_recovery_authorized)
                if document_refresh_recovery_authorized is not None else None
            ),
            ownership_edit_authorized=ownership_edit_authorized,
            entity_type_basis=entity_type_basis,
            clm=ClmCaseSummaryResponse.from_domain(clm_record, case, team),
            automation_id=record.automation_id,
            version=record.version,
            status=record.status,
            current_stage=record.current_stage,
            completed_stages=record.completed_stages,
            active_exceptions=[
                BusinessExceptionResponse.model_validate(item) for item in record.active_exceptions
            ],
            historical_exceptions=[
                BusinessExceptionResponse.model_validate(item)
                for item in record.exceptions
                if item.status != BusinessExceptionStatus.OPEN
            ],
            non_blocking_decisions=tuple(
                BrowserBlockerDecision.model_validate(item)
                for item in record.non_blocking_decisions
            ),
            interventions=project_human_interventions(
                automation=record,
                clm=clm_record,
                case=case,
                ownership=ownership,
            ),
            reconciliation=(
                ReconciliationResponse.from_domain(reconciliation)
                if reconciliation is not None
                else None
            ),
            technical_failure=record.technical_failure,
            metrics=record.metrics,
            target_operations=target_operations,
            target_submission=target_submission,
            stage_order_version=record.stage_order_version,
            processing_pipeline=processing_pipeline,
            target_classification=target_classification,
            classification_consistency=assess_classification_consistency(
                legal_form=case.entity.party_type if case.entity is not None else None,
                kyc_customer_type=target_classification.kyc_customer_type.selected_value,
            ),
            ownership_recovery=(
                BrowserOwnershipRecovery(
                    analysis_id=ownership.analysis_id,
                    version=ownership.version,
                    state=ownership.state,
                    manual_evidence_action=(
                        "MANUAL_OWNERSHIP_EVIDENCE"
                        if ownership.state == OwnershipAnalysisState.REVIEW_REQUIRED
                        and record.current_stage == AutomationStage.OWNERSHIP
                        else None
                    ),
                    review_receipt=ownership.manual_review_receipt,
                )
                if ownership is not None
                else None
            ),
            timeline=record.events,
            created_at=record.created_at,
            updated_at=record.updated_at,
            timing=timing,
        )


class CaseTimingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_elapsed_ms: int = Field(ge=0)
    time_since_last_update_ms: int = Field(ge=0)
    automation_elapsed_ms: int | None = Field(default=None, ge=0)
    recorded_total_duration_ms: int | None = Field(default=None, ge=0)

    @classmethod
    def from_domain(cls, timing: CaseTimingProjection) -> "CaseTimingResponse":
        return cls.model_validate(timing.model_dump())


class CaseDetailTimingResponse(CaseTimingResponse):
    observed_at: datetime


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
    active_exception_types: tuple[BusinessExceptionType, ...]

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
            active_exception_types=record.active_exception_types,
        )


class CasePortfolioItemResponse(ZeroTouchCaseListItemResponse):
    timing: CaseTimingResponse

    @classmethod
    def from_observed_domain(
        cls, record: ObservedCasePortfolioRecord, team: TeamRecord | None = None
    ) -> "CasePortfolioItemResponse":
        return cls(
            **ZeroTouchCaseListItemResponse.from_domain(record, team).model_dump(),
            timing=CaseTimingResponse.from_domain(record.timing),
        )


class CasePortfolioPageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observed_at: datetime
    items: tuple[CasePortfolioItemResponse, ...]
    offset: int
    limit: int
    has_more: bool

    @classmethod
    def from_domain(
        cls,
        page: ObservedCasePortfolioPage,
        teams: dict[TeamId, TeamRecord],
    ) -> "CasePortfolioPageResponse":
        return cls(
            observed_at=page.observed_at,
            items=tuple(
                CasePortfolioItemResponse.from_observed_domain(
                    item,
                    teams.get(item.team_id) if item.team_id is not None else None,
                )
                for item in page.items
            ),
            offset=page.offset,
            limit=page.limit,
            has_more=page.has_more,
        )


class CaseActivityItemResponse(BaseModel):
    """Minimized retained automation event with current case context."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: UUID
    sequence: int
    timestamp: datetime
    event_type: AutomationEventType
    status: AutomationStatus
    stage: AutomationStage
    outcome: EventOutcome
    code: str | None
    message: str
    current_priority: CasePriority | None
    current_client_scope_label: str | None

    @classmethod
    def from_domain(cls, item: CaseActivityItem) -> "CaseActivityItemResponse":
        return cls.model_validate(item.model_dump())


class CaseActivityPageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: tuple[CaseActivityItemResponse, ...]
    offset: int
    limit: int
    has_more: bool

    @classmethod
    def from_domain(cls, page: CaseActivityPage) -> "CaseActivityPageResponse":
        return cls(
            items=tuple(CaseActivityItemResponse.from_domain(item) for item in page.items),
            offset=page.offset,
            limit=page.limit,
            has_more=page.has_more,
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

    operation: Literal["SEARCH", "SHELL", "POLICY", "AMEND", "READBACK"]
    status: Literal[
        "NOT_ATTEMPTED",
        "IN_PROGRESS",
        "OUTCOME_UNCERTAIN",
        "NO_MATCH",
        "MATCH_FOUND",
        "SKIPPED",
        "RECOVERED",
        "REVIEW_REQUIRED",
        "CREATED",
        "SUCCESS",
        "FAILED",
    ]


def project_processing_pipeline(
    *,
    automation: ZeroTouchAutomationRecord,
    clm: ClmOrchestrationRecord,
    case: OnboardingCase,
    reconciliation: ReconciliationCaseRecord | None,
    target_operations: tuple[BrowserTargetOperationEvidence, ...],
    retained_goldtier_id: str | None,
    target_submission: BrowserTargetSubmissionEvidence | None = None,
) -> tuple[BrowserProcessingNode, ...]:
    """Build the exact, presentation-safe workflow order from retained backend facts."""

    def exception_code(stage: AutomationStage) -> str | None:
        return next(
            (item.blocker_code for item in automation.active_exceptions if item.stage == stage),
            None,
        )

    def stage_timestamp(stage: AutomationStage) -> datetime | None:
        timestamps = [item.timestamp for item in automation.events if item.stage == stage]
        return max(timestamps) if timestamps else None

    def stage_status(stage: AutomationStage) -> ProcessingNodeStatus:
        if stage in automation.completed_stages:
            return "COMPLETE"
        if automation.current_stage != stage:
            return "NOT_REACHED"
        if automation.status == AutomationStatus.TECHNICAL_FAILURE:
            return "FAILED"
        if automation.status == AutomationStatus.WAITING_FOR_REVIEW:
            return "REVIEW_REQUIRED"
        if automation.status in {
            AutomationStatus.PENDING_INPUTS,
            AutomationStatus.RECOVERY_PENDING,
        }:
            return "BLOCKED"
        return "IN_PROGRESS"

    def readiness_status(value: object) -> ProcessingNodeStatus:
        normalized = str(value)
        return {
            "READY": "COMPLETE",
            "SUBMITTED": "COMPLETE",
            "IN_PROGRESS": "IN_PROGRESS",
            "REVIEW_REQUIRED": "REVIEW_REQUIRED",
            "FAILED": "FAILED",
            "BLOCKED": "BLOCKED",
            "MISSING": "BLOCKED",
            "NOT_SUBMITTED": "NOT_REACHED",
        }.get(normalized, "NOT_REACHED")  # type: ignore[return-value]

    def operation_status(value: str) -> ProcessingNodeStatus:
        return {
            "NOT_ATTEMPTED": "NOT_REACHED",
            "IN_PROGRESS": "IN_PROGRESS",
            "OUTCOME_UNCERTAIN": "BLOCKED",
            "NO_MATCH": "COMPLETE",
            "MATCH_FOUND": "COMPLETE",
            "SKIPPED": "SKIPPED",
            "RECOVERED": "COMPLETE",
            "REVIEW_REQUIRED": "REVIEW_REQUIRED",
            "CREATED": "COMPLETE",
            "SUCCESS": "COMPLETE",
            "FAILED": "FAILED",
        }[value]  # type: ignore[return-value]

    jurisdiction = case.jurisdiction_resolution
    jurisdiction_status: ProcessingNodeStatus = "NOT_REACHED"
    jurisdiction_result: str | None = None
    jurisdiction_timestamp: datetime | None = None
    if jurisdiction is not None:
        jurisdiction_timestamp = jurisdiction.resolved_at
        if jurisdiction.status.value == "RESOLVED":
            jurisdiction_status = "COMPLETE"
            jurisdiction_result = "Jurisdiction resolved"
        else:
            jurisdiction_status = "REVIEW_REQUIRED"
            jurisdiction_result = "Jurisdiction requires review"

    acquisition = case.registry_acquisition
    existing_target_state = getattr(case, "existing_target_state", None)
    initial_identity = getattr(case, "initial_identity", None)
    initial_target_search = getattr(case, "initial_target_search", None)
    initial_search_disposition = getattr(initial_target_search, "disposition", None)
    registry_children: tuple[BrowserProcessingNode, ...] = ()
    registry_status = stage_status(AutomationStage.REGISTRY)
    registry_provider: str | None = None
    registry_environment: str | None = None
    registry_timestamp = stage_timestamp(AutomationStage.REGISTRY)
    if acquisition is not None:
        operation_nodes: list[BrowserProcessingNode] = []
        for item in acquisition.operation_results:
            provenance = item.provenance
            if provenance is not None and registry_provider is None:
                registry_provider = provenance.provider.value
                registry_environment = provenance.environment.value
            mapped_status: ProcessingNodeStatus = {
                "COMPLETE": "COMPLETE",
                "EMPTY": "EMPTY",
                "FAILED": "FAILED",
                "NOT_ATTEMPTED": "NOT_REACHED",
                "UNSUPPORTED": "UNSUPPORTED",
            }[item.status.value]  # type: ignore[assignment]
            operation_nodes.append(
                BrowserProcessingNode(
                    node_id=f"ACRA_{item.operation.value}",
                    label=(
                        "Shareholders"
                        if item.operation.value == "OWNERSHIP_PARTIES"
                        else item.operation.value.replace("_", " ").title()
                    ),
                    status=mapped_status,
                    provider=provenance.provider.value if provenance is not None else "ACRA",
                    environment=provenance.environment.value if provenance is not None else None,
                    operation=item.operation.value,
                    backend_stage=AutomationStage.REGISTRY,
                    timestamp=provenance.retrieved_at if provenance is not None else None,
                    safe_result=(
                        "Operation returned no records"
                        if mapped_status == "EMPTY"
                        else "Operation unsupported; no provider call occurred"
                        if mapped_status == "UNSUPPORTED"
                        else "Operation evidence retained"
                        if mapped_status == "COMPLETE"
                        else "Operation failed"
                        if mapped_status == "FAILED"
                        else "Operation was not attempted"
                    ),
                    record_count=item.record_count,
                    blocker_code=item.error.code if item.error is not None else None,
                )
            )
        registry_children = tuple(operation_nodes)
        registry_timestamp = acquisition.retrieved_at
        registry_status = {
            "COMPLETE": "COMPLETE",
            "PARTIAL": (
                "COMPLETE" if AutomationStage.REGISTRY in automation.completed_stages
                else "REVIEW_REQUIRED"
            ),
            "FAILED": "FAILED",
        }[acquisition.status.value]
    elif existing_target_state is not None and (
        registry_status == "COMPLETE" or automation.status == AutomationStatus.COMPLETED
    ):
        registry_status = "SKIPPED"
    elif initial_search_disposition == "REVIEW_REQUIRED" or initial_identity is None:
        registry_status = "NOT_REACHED"

    target_by_name = {item.operation: item for item in target_operations}
    checkpoint = clm.target_search_checkpoint
    search_evidence = target_by_name.get(
        "SEARCH", BrowserTargetOperationEvidence(operation="SEARCH", status="NOT_ATTEMPTED")
    )
    search_status = operation_status(search_evidence.status)
    if (
        checkpoint is None
        and search_evidence.status == "NOT_ATTEMPTED"
        and automation.current_stage == AutomationStage.GOLDTIER_SEARCH
    ):
        search_status = stage_status(AutomationStage.GOLDTIER_SEARCH)
    elif (
        checkpoint is None
        and initial_identity is None
        and search_evidence.status == "NOT_ATTEMPTED"
    ):
        search_status = "BLOCKED"
    search_event_timestamps = [
        item.timestamp
        for item in clm.events
        if item.event_type.value.startswith("GOLDTIER_SEARCH_")
    ]
    search_timestamp = (
        checkpoint.searched_at
        if checkpoint is not None
        else max(search_event_timestamps)
        if search_event_timestamps
        else None
    )
    search_result = (
        "No existing customer found. Continuing as a new customer."
        if checkpoint is not None
        and checkpoint.disposition == GoldTierSearchDisposition.NO_MATCH
        else (
            "GoldTier Search failed. This does not mean the customer does not exist. "
            "Case evidence may continue, but GoldTier target mutations remain blocked."
        )
        if checkpoint is not None
        and checkpoint.disposition == GoldTierSearchDisposition.FAILED
        else
        f"{checkpoint.candidate_count} candidate(s) retained"
        if checkpoint is not None and search_status == "COMPLETE"
        else f"{checkpoint.candidate_count} candidate(s) require review"
        if checkpoint is not None and search_status == "REVIEW_REQUIRED"
        else {
            "IN_PROGRESS": "Search in progress",
            "REVIEW_REQUIRED": "Search requires review",
            "BLOCKED": "Search blocked",
            "FAILED": "Search failed",
            "SKIPPED": "Search skipped",
            "EMPTY": "Search returned no candidates",
            "COMPLETE": "Search completed",
            "NOT_REACHED": "Search not reached",
        }[search_status]
    )
    branch_statuses: dict[str, ProcessingNodeStatus] = {
        "EXACT_MATCH": "NOT_REACHED",
        "NO_MATCH": "NOT_REACHED",
        "MULTIPLE_OR_AMBIGUOUS": "NOT_REACHED",
    }
    if (
        checkpoint is not None
        and checkpoint.disposition == GoldTierSearchDisposition.CONFIRMED_EXISTING
    ):
        branch_statuses["CONFIRMED_EXISTING"] = "NOT_REACHED"
    if checkpoint is not None:
        branch_statuses = {name: "SKIPPED" for name in branch_statuses}
        if checkpoint.disposition == GoldTierSearchDisposition.EXACT_MATCH:
            branch_statuses["EXACT_MATCH"] = "COMPLETE"
        elif checkpoint.disposition == GoldTierSearchDisposition.CONFIRMED_EXISTING:
            branch_statuses["CONFIRMED_EXISTING"] = "COMPLETE"
        elif checkpoint.disposition == GoldTierSearchDisposition.NO_MATCH:
            branch_statuses["NO_MATCH"] = "COMPLETE"
        elif checkpoint.disposition == GoldTierSearchDisposition.REVIEW_REQUIRED:
            branch_statuses["MULTIPLE_OR_AMBIGUOUS"] = "REVIEW_REQUIRED"
    search_children = tuple(
        BrowserProcessingNode(
            node_id=f"GOLDTIER_SEARCH_{name}",
            label={
                "EXACT_MATCH": "Exact match",
                "CONFIRMED_EXISTING": "Human-confirmed existing customer",
                "NO_MATCH": "No match",
                "MULTIPLE_OR_AMBIGUOUS": "Multiple or ambiguous matches",
            }[name],
            status=status,
            provider="GOLDTIER",
            environment=clm.submission_plan.environment.value,
            operation="SEARCH",
            backend_stage=AutomationStage.GOLDTIER_SEARCH,
            timestamp=checkpoint.searched_at if checkpoint is not None else None,
            safe_result=(
                f"{checkpoint.candidate_count} candidate(s) retained"
                if checkpoint is not None and status not in {"SKIPPED", "NOT_REACHED"}
                else None
            ),
            record_count=(
                checkpoint.candidate_count
                if checkpoint is not None and status not in {"SKIPPED", "NOT_REACHED"}
                else None
            ),
            blocker_code=(
                str(checkpoint.code)
                if checkpoint is not None and status == "REVIEW_REQUIRED"
                else None
            ),
            retained_goldtier_id=(
                retained_goldtier_id
                if name in {"EXACT_MATCH", "CONFIRMED_EXISTING"} and status == "COMPLETE" else None
            ),
        )
        for name, status in branch_statuses.items()
    )

    reconciliation_status: ProcessingNodeStatus = "NOT_REACHED"
    reconciliation_result: str | None = None
    reconciliation_timestamp: datetime | None = None
    if reconciliation is not None:
        reconciliation_timestamp = reconciliation.updated_at
        reconciliation_status = {
            "NOT_STARTED": "NOT_REACHED",
            "MATCHED": "COMPLETE",
            "RESOLVED": "COMPLETE",
            "REVIEW_REQUIRED": "REVIEW_REQUIRED",
            "FAILED": "FAILED",
        }[reconciliation.status.value]  # type: ignore[assignment]
        reconciliation_result = f"{len(reconciliation.discrepancies)} discrepancy record(s)"

    intelligence_events = [
        item
        for item in automation.events
        if item.event_type == AutomationEventType.INTELLIGENCE_EVALUATED
    ]
    advisory_status: ProcessingNodeStatus = "COMPLETE" if intelligence_events else "NOT_REACHED"
    advisory_timestamp = intelligence_events[-1].timestamp if intelligence_events else None
    projected_readiness_status = (
        "COMPLETE"
        if clm.readiness.evaluated_at is not None and not clm.readiness.blockers
        else stage_status(AutomationStage.READINESS)
    )
    if (
        projected_readiness_status == "NOT_REACHED"
        and clm.readiness.evaluated_at is not None
        and clm.readiness.blockers
    ):
        projected_readiness_status = "BLOCKED"

    case_policy_snapshot = getattr(case, "policy_snapshot", None)
    target_policy = (
        case_policy_snapshot.goldtier_target if case_policy_snapshot is not None else None
    )
    classification_event_times = [
        item.timestamp
        for item in getattr(case, "events", ())
        if item.code == "GOLDTIER_CASE_CLASSIFICATION_BOUND"
    ]
    classification_timestamp = (
        max(classification_event_times) if classification_event_times else None
    )
    if (
        classification_timestamp is None
        and target_policy is not None
        and case_policy_snapshot is not None
    ):
        classification_timestamp = case_policy_snapshot.bound_at
    classification_fields = (
        (
            "KYC_CUSTOMER_TYPE",
            "KYC customer type",
            target_policy.kyc_customer_type if target_policy is not None else None,
        ),
        (
            "CLIENT_SEGMENT",
            "Client segment",
            target_policy.client_segment if target_policy is not None else None,
        ),
        (
            "REGISTRATION_TYPE",
            "Registration type",
            target_policy.registration_type if target_policy is not None else None,
        ),
        (
            "CUSTOMER_EXTERNAL_SYSTEM",
            "Customer external system",
            target_policy.customer_external_system if target_policy is not None else None,
        ),
        (
            "POLICY",
            "Policy",
            target_policy.policy if target_policy is not None else None,
        ),
        (
            "BOOKING_ENTITY",
            "Booking entity",
            target_policy.booking_entity if target_policy is not None else None,
        ),
    )
    classification_children = tuple(
        BrowserProcessingNode(
            node_id=f"TARGET_CLASSIFICATION_{field_id}",
            label=label,
            status=(
                "REVIEW_REQUIRED"
                if item is None
                or item.authority == PolicyAuthority.TBD_SPONSOR
                or item.value == "TBD_SPONSOR"
                else "COMPLETE"
            ),
            backend_stage=AutomationStage.READINESS,
            timestamp=classification_timestamp,
            safe_result=(f"{item.value} · {item.authority.value}" if item is not None else None),
            blocker_code=(
                "GOLDTIER_CLASSIFICATION_REQUIRED"
                if item is None
                or item.authority == PolicyAuthority.TBD_SPONSOR
                or item.value == "TBD_SPONSOR"
                else None
            ),
        )
        for field_id, label, item in classification_fields
    )
    classification_status: ProcessingNodeStatus = (
        "COMPLETE"
        if target_policy is not None and target_policy.dispatch_ready
        else "REVIEW_REQUIRED"
    )
    classification_nodes = (
        (
            BrowserProcessingNode(
                node_id="TARGET_CLASSIFICATION",
                label="Target classification",
                status=classification_status,
                backend_stage=AutomationStage.READINESS,
                timestamp=classification_timestamp,
                safe_result=(
                    "Case target values are bound"
                    if classification_status == "COMPLETE"
                    else "Case target classification is required"
                ),
                blocker_code=(
                    None
                    if classification_status == "COMPLETE"
                    else "GOLDTIER_CLASSIFICATION_REQUIRED"
                ),
                children=classification_children,
            ),
        )
        if target_policy is not None
        and clm.submission_plan.environment.value == "SANDBOX"
        else ()
    )

    target_operation_children = tuple(
        BrowserProcessingNode(
            node_id=f"GOLDTIER_{item.operation}",
            label={
                "SEARCH": "Search",
                "SHELL": "Customer shell",
                "POLICY": "Customer policy",
                "AMEND": "Customer amendment",
                "READBACK": "Customer identity readback",
            }[item.operation],
            status=operation_status(item.status),
            provider="GOLDTIER",
            environment=clm.submission_plan.environment.value,
            operation=item.operation,
            backend_stage=AutomationStage.MOCK_GOLDTIER,
            safe_result=(
                "Recovered from provider verification · Original transport outcome: "
                "Uncertain · Replay: No"
                if item.status == "RECOVERED"
                else (f"GoldTier {item.operation.title()} outcome is uncertain "
                      "from an earlier submission attempt.")
                if item.status == "OUTCOME_UNCERTAIN"
                else item.status.replace("_", " ").title()
            ),
            retained_goldtier_id=(
                retained_goldtier_id
                if item.operation in {"SHELL", "POLICY", "AMEND", "READBACK"}
                and operation_status(item.status) in {"COMPLETE", "SKIPPED"}
                else None
            ),
        )
        for item in target_operations
        if item.operation != "SEARCH"
        or automation.stage_order_version == LEGACY_AUTOMATION_STAGE_ORDER_VERSION
    )
    completed_status: ProcessingNodeStatus = (
        "COMPLETE" if automation.status == AutomationStatus.COMPLETED else "NOT_REACHED"
    )
    target_children = (
        *target_operation_children,
        BrowserProcessingNode(
            node_id="GOLDTIER_COMPLETED",
            label="Completed",
            status=completed_status,
            backend_stage=AutomationStage.COMPLETE,
            timestamp=automation.completed_at,
            safe_result=(
                "Automation completed" if completed_status == "COMPLETE" else "Not completed"
            ),
            retained_goldtier_id=(
                retained_goldtier_id if completed_status == "COMPLETE" else None
            ),
        ),
    )
    target_status = stage_status(AutomationStage.MOCK_GOLDTIER)
    if checkpoint is not None and checkpoint.disposition in {
        GoldTierSearchDisposition.FAILED,
        GoldTierSearchDisposition.REVIEW_REQUIRED,
    }:
        target_status = "BLOCKED"
    if target_operation_children:
        child_states = {item.status for item in target_operation_children}
        if "FAILED" in child_states:
            target_status = "FAILED"
        elif "REVIEW_REQUIRED" in child_states:
            target_status = "REVIEW_REQUIRED"
        elif "IN_PROGRESS" in child_states:
            target_status = "IN_PROGRESS"
        elif all(
            item.status in {"COMPLETE", "SKIPPED"} for item in target_operation_children
        ):
            target_status = "COMPLETE"

    common_prefix = (
        BrowserProcessingNode(
            node_id="CASE_START",
            label="Case created",
            status="COMPLETE",
            timestamp=automation.created_at,
            safe_result="Automation record created",
        ),
        BrowserProcessingNode(
            node_id="JURISDICTION",
            label="Jurisdiction",
            status=jurisdiction_status,
            timestamp=jurisdiction_timestamp,
            safe_result=jurisdiction_result,
            blocker_code=exception_code(AutomationStage.REGISTRY),
        ),
        BrowserProcessingNode(
            node_id="ACRA_REGISTRY",
            label="Registry verification",
            status=registry_status,
            provider=registry_provider or "ACRA",
            environment=registry_environment,
            backend_stage=AutomationStage.REGISTRY,
            timestamp=registry_timestamp,
            safe_result=(
                "ACRA skipped after exact verified GoldTier match"
                if registry_status == "SKIPPED"
                else "Registry acquisition failed"
                if registry_status == "FAILED"
                else "Required registry evidence is unavailable"
                if registry_status == "REVIEW_REQUIRED" and acquisition is None
                else "Waiting for GoldTier customer identity resolution"
                if initial_search_disposition == "REVIEW_REQUIRED"
                else "Registry identity validated; source ownership evidence remains partial"
                if acquisition is not None and acquisition.status.value == "PARTIAL"
                and registry_status == "COMPLETE"
                else "Registry acquisition retained"
                if acquisition is not None
                else "Registry acquisition not reached"
            ),
            blocker_code=(
                case.error.code
                if registry_status == "FAILED" and case.error is not None
                else "GT_SEARCH_IDENTITY_REVIEW_REQUIRED"
                if initial_search_disposition == "REVIEW_REQUIRED"
                else exception_code(AutomationStage.REGISTRY)
            ),
            children=registry_children,
        ),
    )
    early_search = BrowserProcessingNode(
        node_id="GOLDTIER_SEARCH",
        label="Existing-customer search",
        status=search_status,
        provider="GOLDTIER",
        environment=clm.submission_plan.environment.value,
        operation="SEARCH",
        backend_stage=AutomationStage.GOLDTIER_SEARCH,
        timestamp=search_timestamp,
        safe_result=search_result,
        record_count=checkpoint.candidate_count if checkpoint is not None else None,
        blocker_code=(
            str(checkpoint.code)
            if checkpoint is not None and checkpoint.code
            else exception_code(AutomationStage.GOLDTIER_SEARCH)
        ),
        retained_goldtier_id=(
            retained_goldtier_id
            if checkpoint is not None
            and checkpoint.disposition in {
                GoldTierSearchDisposition.EXACT_MATCH,
                GoldTierSearchDisposition.CONFIRMED_EXISTING,
            }
            else None
        ),
        children=search_children,
    )
    initial_identity_node = BrowserProcessingNode(
        node_id="INITIAL_IDENTITY",
        label="Initial identity",
        status=(
            "COMPLETE" if initial_identity is not None
            else "NOT_REACHED" if automation.status == AutomationStatus.COMPLETED
            else "REVIEW_REQUIRED"
        ),
        timestamp=getattr(case, "created_at", None) if initial_identity is not None else None,
        safe_result=(
            "Legal name, registration ID, and country retained"
            if initial_identity is not None
            else "Initial identity not supplied"
        ),
        blocker_code=(None if initial_identity is not None else "INITIAL_IDENTITY_INCOMPLETE"),
    )
    existing_target_node = BrowserProcessingNode(
        node_id="EXISTING_TARGET_STATE",
        label="Existing GoldTier state",
        status="COMPLETE" if existing_target_state is not None else "NOT_REACHED",
        provider="GOLDTIER" if existing_target_state is not None else None,
        environment=(
            clm.submission_plan.environment.value
            if existing_target_state is not None
            else None
        ),
        retained_goldtier_id=(
            existing_target_state.target_party_id
            if existing_target_state is not None
            else None
        ),
        safe_result=(
            "Verified prior target state hydrated"
            if existing_target_state is not None
            else "No existing target state hydrated"
        ),
    )
    confirmation = getattr(case, "target_dispatch_confirmation", None)
    final_review_required = any(
        item.exception_type.value == "TARGET_CONFIRMATION_REQUIRED"
        for item in automation.active_exceptions
    )
    prerequisites_ready = clm.readiness.evaluated_at is not None and not clm.readiness.blockers
    retained_submission = (
        target_submission is not None and target_submission.state != "NOT_SUBMITTED"
    )
    package_prepared = retained_submission or (
        prerequisites_ready and (
            confirmation is not None or final_review_required
            or automation.status == AutomationStatus.COMPLETED
        )
    )
    final_review_status: ProcessingNodeStatus = "NOT_REACHED"
    final_review_result = "Final review awaits authoritative readiness"
    if confirmation is not None:
        if target_submission is not None and target_submission.state != "NOT_SUBMITTED":
            submission_states: dict[str, tuple[ProcessingNodeStatus, str]] = {
                "SENDING": ("IN_PROGRESS", "Sending to GoldTier"),
                "SUBMISSION_CONFIRMED": (
                    "COMPLETE",
                    "Submission confirmed; provider outcome and local completion retained",
                ),
                "SUBMISSION_FAILED": ("FAILED", "Submission failed; retained provider failure"),
                "SUBMISSION_OUTCOME_UNCERTAIN": (
                    "BLOCKED",
                    "Submission outcome uncertain; read-only verification required, no replay",
                ),
                "FINALIZATION_PENDING": (
                    "BLOCKED",
                    "Retained target operations resolved; safe finalization pending without replay",
                ),
            }
            final_review_status, final_review_result = submission_states[target_submission.state]
        elif automation.status == AutomationStatus.COMPLETED:
            final_review_status = "COMPLETE"
            final_review_result = "Reviewed submission completed; provider outcome retained"
        elif automation.status == AutomationStatus.RECOVERY_PENDING:
            final_review_status = "BLOCKED"
            final_review_result = (
                "Submission recovery pending; retained target "
                "outcomes must be inspected and must not be replayed"
            )
        elif target_status == "FAILED" or automation.status == AutomationStatus.TECHNICAL_FAILURE:
            final_review_status = "FAILED"
            final_review_result = (
                "Reviewed submission stopped; retained "
                "failure requires inspection"
            )
        else:
            final_review_status = target_status
            final_review_result = (
                "Final approval retained; ledger-owned submission "
                "outcome remains authoritative"
            )
    elif final_review_required and not prerequisites_ready:
        final_review_status = "BLOCKED"
        final_review_result = "Final review awaits current submission readiness"
    elif final_review_required:
        final_review_status = "REVIEW_REQUIRED"
        final_review_result = (
            "Review & Send is this application's final "
            "approval before target submission"
        )
    elif automation.status == AutomationStatus.COMPLETED:
        final_review_result = (
            "Historical target completion retained; no "
            "application review confirmation recorded"
        )

    common_suffix = (
        BrowserProcessingNode(
            node_id="DOCUMENT_IDP",
            label="Document verification",
            status=readiness_status(clm.readiness.document.status.value),
            backend_stage=AutomationStage.DOCUMENT,
            timestamp=stage_timestamp(AutomationStage.DOCUMENT),
            safe_result=clm.readiness.document.status.value.replace("_", " ").title(),
            blocker_code=exception_code(AutomationStage.DOCUMENT),
        ),
        BrowserProcessingNode(
            node_id="RECONCILIATION",
            label="Data reconciliation",
            status=reconciliation_status,
            backend_stage=AutomationStage.DOCUMENT,
            timestamp=reconciliation_timestamp,
            safe_result=reconciliation_result,
            blocker_code=exception_code(AutomationStage.DOCUMENT),
        ),
        BrowserProcessingNode(
            node_id="OWNERSHIP_UBO",
            label="Ownership & UBO",
            status=readiness_status(clm.readiness.ownership.status.value),
            backend_stage=AutomationStage.OWNERSHIP,
            timestamp=stage_timestamp(AutomationStage.OWNERSHIP),
            safe_result=clm.readiness.ownership.status.value.replace("_", " ").title(),
            blocker_code=exception_code(AutomationStage.OWNERSHIP),
        ),
        BrowserProcessingNode(
            node_id="ADVISORY",
            label="Risk assessment",
            status=advisory_status,
            backend_stage=AutomationStage.OWNERSHIP,
            timestamp=advisory_timestamp,
            safe_result=(
                "Bounded POC advisory assessment retained; not production AML/KYC risk"
                if intelligence_events
                else "Bounded POC advisory assessment not reached; not production AML/KYC risk"
            ),
        ),
        BrowserProcessingNode(
            node_id="READINESS",
            label="Submission readiness",
            status=projected_readiness_status,
            backend_stage=AutomationStage.READINESS,
            timestamp=clm.readiness.evaluated_at,
            safe_result=(
                "Ready for target submission"
                if not clm.readiness.blockers
                else f"{len(clm.readiness.blockers)} blocker(s) retained"
            ),
            blocker_code=(clm.readiness.blockers[0].value if clm.readiness.blockers else None),
            children=classification_nodes,
        ),
        BrowserProcessingNode(
            node_id="GOLDTIER_TARGET",
            label="GoldTier submission package",
            status="COMPLETE" if package_prepared else projected_readiness_status,
            provider="GOLDTIER",
            environment=clm.submission_plan.environment.value,
            backend_stage=AutomationStage.READINESS,
            timestamp=clm.readiness.evaluated_at,
            safe_result=(
                "Frozen submission package retained; see final submission outcome"
                if target_submission is not None and target_submission.state != "NOT_SUBMITTED"
                else "Prepared target plan retained" if package_prepared
                else "Submission preparation awaits authoritative readiness"
            ),
            blocker_code=(clm.readiness.blockers[0].value if clm.readiness.blockers else None),
        ),
        BrowserProcessingNode(
            node_id="FINAL_REVIEW_SEND",
            label="Final review & send",
            status=final_review_status,
            provider="GOLDTIER",
            environment=clm.submission_plan.environment.value,
            backend_stage=AutomationStage.MOCK_GOLDTIER,
            timestamp=(
                automation.completed_at
                or getattr(confirmation, "confirmed_at", None)
            ),
            safe_result=final_review_result,
            blocker_code=(
                exception_code(AutomationStage.MOCK_GOLDTIER)
                if confirmation is not None
                else clm.readiness.blockers[0].value
                if final_review_required and clm.readiness.blockers
                else "TARGET_CONFIRMATION_REQUIRED" if final_review_required else None
            ),
            retained_goldtier_id=retained_goldtier_id,
            children=target_children,
        ),
    )
    # Business-stage presentation does not change historical event/operation order.
    search_with_state = early_search.model_copy(update={
        "children": (*search_children, existing_target_node)
        if existing_target_state is not None else search_children,
    })
    return (
        common_prefix[0],
        initial_identity_node,
        common_prefix[1],
        search_with_state,
        common_prefix[2],
        *common_suffix,
    )


ZeroTouchCaseSummaryResponse.model_rebuild()
