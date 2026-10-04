"""Source-neutral ownership graph and provisional ownership-based UBO models."""

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal
from unicodedata import category
from uuid import UUID

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from app.domain.documents import DocumentOwnershipObservation
from app.domain.models import EventOutcome, SafeError
from app.domain.ownership_evidence import OwnershipEvidence, OwnershipTaggingResult
from app.domain.registry_legal_form import RegistryLegalForm


def _normalize_safe_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    if not normalized:
        raise ValueError("ownership text must not be blank")
    if any(category(character).startswith("C") for character in normalized):
        raise ValueError("ownership text must not contain control characters")
    return normalized


SafePartyId = Annotated[
    str,
    BeforeValidator(_normalize_safe_text),
    StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$"),
]
SafeRelationshipId = Annotated[
    str,
    BeforeValidator(_normalize_safe_text),
    StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$"),
]
SafePartyName = Annotated[
    str,
    BeforeValidator(_normalize_safe_text),
    StringConstraints(min_length=1, max_length=160),
]
SafeProviderName = Annotated[
    str,
    BeforeValidator(_normalize_safe_text),
    StringConstraints(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$",
    ),
]


def _normalize_source_reference(value: object) -> object:
    normalized = _normalize_safe_text(value)
    if not isinstance(normalized, str):
        return normalized
    reserved_terms = {
        "apikey",
        "authorization",
        "bearer",
        "credential",
        "password",
        "passwd",
        "secret",
        "token",
    }
    compact = normalized.casefold().replace(".", "").replace("_", "").replace("-", "")
    if any(term in compact for term in reserved_terms):
        raise ValueError("ownership source reference must not contain credential-like terms")
    return normalized


SafeSourceReference = Annotated[
    str,
    BeforeValidator(_normalize_source_reference),
    StringConstraints(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$",
    ),
]
SafeOptionalIdentifier = Annotated[
    str,
    BeforeValidator(_normalize_safe_text),
    StringConstraints(min_length=1, max_length=64),
]
OwnershipPercent = Annotated[
    Decimal,
    Field(gt=Decimal("0"), le=Decimal("100"), allow_inf_nan=False, max_digits=12, decimal_places=6),
]
CalculatedPercent = Annotated[
    Decimal,
    Field(ge=Decimal("0"), le=Decimal("100"), allow_inf_nan=False),
]


class PartyType(StrEnum):
    LEGAL_ENTITY = "LEGAL_ENTITY"
    NATURAL_PERSON = "NATURAL_PERSON"


class OwnershipRelationshipType(StrEnum):
    OWNERSHIP = "OWNERSHIP"


class OwnershipBasis(StrEnum):
    SHARE_OWNERSHIP = "SHARE_OWNERSHIP"
    ECONOMIC_INTEREST = "ECONOMIC_INTEREST"


class OwnershipEnvironment(StrEnum):
    MOCK = "MOCK"
    LOCAL = "LOCAL"
    SANDBOX = "SANDBOX"
    LIVE = "LIVE"


class OwnershipAnalysisState(StrEnum):
    LOADING = "LOADING"
    LOADED = "LOADED"
    ANALYZING = "ANALYZING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    ANALYZED = "ANALYZED"
    FAILED = "FAILED"


class OwnershipEventType(StrEnum):
    OWNERSHIP_LOAD_STARTED = "OWNERSHIP_LOAD_STARTED"
    OWNERSHIP_LOADED = "OWNERSHIP_LOADED"
    OWNERSHIP_ANALYSIS_STARTED = "OWNERSHIP_ANALYSIS_STARTED"
    OWNERSHIP_ANALYSIS_COMPLETED = "OWNERSHIP_ANALYSIS_COMPLETED"
    OWNERSHIP_REVIEW_REQUIRED = "OWNERSHIP_REVIEW_REQUIRED"
    OWNERSHIP_ANALYSIS_FAILED = "OWNERSHIP_ANALYSIS_FAILED"
    OWNERSHIP_SOURCE_REPLACED = "OWNERSHIP_SOURCE_REPLACED"


class OwnershipIssueCode(StrEnum):
    CONTRADICTORY_OWNERSHIP_EVIDENCE = "CONTRADICTORY_OWNERSHIP_EVIDENCE"
    OWNERSHIP_DENOMINATOR_REQUIRED = "OWNERSHIP_DENOMINATOR_REQUIRED"
    OWNERSHIP_REQUIRED = "OWNERSHIP_REQUIRED"
    UBO_REVIEW_REQUIRED = "UBO_REVIEW_REQUIRED"
    OWNERSHIP_METHOD_UNSUPPORTED = "OWNERSHIP_METHOD_UNSUPPORTED"
    CYCLE_DETECTED = "CYCLE_DETECTED"
    INCOMPLETE_LEGAL_ENTITY = "INCOMPLETE_LEGAL_ENTITY"
    MAXIMUM_DEPTH_EXCEEDED = "MAXIMUM_DEPTH_EXCEEDED"
    PATH_LIMIT_EXCEEDED = "PATH_LIMIT_EXCEEDED"


class OwnershipThresholdResult(StrEnum):
    MET = "MET"
    NOT_MET = "NOT_MET"
    INDETERMINATE = "INDETERMINATE"


class OwnershipCandidateClassification(StrEnum):
    PROVISIONAL_UBO_CANDIDATE = "PROVISIONAL_UBO_CANDIDATE"
    BELOW_PROVISIONAL_THRESHOLD = "BELOW_PROVISIONAL_THRESHOLD"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    INDETERMINATE = "INDETERMINATE"


class Party(BaseModel):
    """A source-neutral legal entity or natural person in an ownership graph."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    party_id: SafePartyId
    display_name: SafePartyName
    party_type: PartyType
    registration_number: SafeOptionalIdentifier | None = None
    country: (
        Annotated[
            str,
            BeforeValidator(_normalize_safe_text),
            StringConstraints(min_length=2, max_length=3, pattern=r"^[A-Z]{2,3}$"),
        ]
        | None
    ) = None


class OwnershipProvenance(BaseModel):
    """Bounded relationship provenance without raw source data or private URLs."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    provider: SafeProviderName
    environment: OwnershipEnvironment
    source_reference: SafeSourceReference
    sourced_at: datetime

    @field_validator("sourced_at")
    @classmethod
    def sourced_at_must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("ownership sourcing timestamp must be timezone-aware UTC")
        return value


class OwnershipRelationship(BaseModel):
    """Directed edge from an owned party to one of its owners."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    relationship_id: SafeRelationshipId
    parent_party_id: SafePartyId
    child_party_id: SafePartyId
    ownership_percent: OwnershipPercent
    relationship_type: OwnershipRelationshipType = OwnershipRelationshipType.OWNERSHIP
    basis: OwnershipBasis = OwnershipBasis.SHARE_OWNERSHIP
    provenance: OwnershipProvenance


class OwnershipPathEdge(BaseModel):
    """One immutable edge in deterministic calculation evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    relationship_id: SafeRelationshipId
    parent_party_id: SafePartyId
    parent_display_name: SafePartyName
    child_party_id: SafePartyId
    child_display_name: SafePartyName
    ownership_percent: OwnershipPercent


class OwnershipPathEvidence(BaseModel):
    """Ordered path and exact effective ownership for one natural person."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    path_id: str = Field(pattern=r"^path-v1-[a-f0-9]{64}$")
    edges: list[OwnershipPathEdge] = Field(min_length=1, max_length=64)
    effective_ownership_percent: CalculatedPercent
    is_direct: bool
    calculation: str = Field(min_length=1, max_length=1024)


class OwnershipAnalysisIssue(BaseModel):
    """Safe deterministic diagnostic that avoids raw provider content."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    code: OwnershipIssueCode
    message: str = Field(min_length=1, max_length=200)
    affected_party_ids: list[SafePartyId] = Field(default_factory=list, max_length=16)


class OwnershipCandidate(BaseModel):
    """Ownership-only natural-person result under a provisional project rule."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    party: Party
    direct_ownership_percent: CalculatedPercent
    indirect_ownership_percent: CalculatedPercent
    aggregated_ownership_percent: CalculatedPercent
    threshold_percent: OwnershipPercent
    threshold_comparator: str = Field(pattern=r"^GREATER_THAN_OR_EQUAL_TO$")
    threshold_result: OwnershipThresholdResult
    classification: OwnershipCandidateClassification
    paths: list[OwnershipPathEvidence]


class OwnershipWorkflowEvent(BaseModel):
    """Audit-safe lifecycle event containing counts and identifiers, not graph data."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    sequence: int = Field(ge=1)
    event_type: OwnershipEventType
    state: OwnershipAnalysisState
    outcome: EventOutcome
    timestamp: datetime
    case_id: UUID
    analysis_id: UUID
    correlation_id: UUID
    code: str | None = Field(default=None, max_length=64)
    message: str = Field(min_length=1, max_length=200)
    party_count: int | None = Field(default=None, ge=0)
    relationship_count: int | None = Field(default=None, ge=0)
    candidate_count: int | None = Field(default=None, ge=0)


class OwnershipDocumentBinding(BaseModel):
    """Current document decision version; extraction version remains on each observation."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")
    document_id: UUID
    event_count: int = Field(ge=1)


class OwnershipDocumentDiscrepancy(BaseModel):
    """Source agreement is independent of extraction quality and creator verification."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")
    observation_id: UUID
    document_id: UUID
    document_version: Literal[1] = 1
    agreement: Literal["MATCH", "MISMATCH", "NOT_COMPARABLE", "AMBIGUOUS"]
    compared_relationship_ids: tuple[SafeRelationshipId, ...] = Field(default=(), max_length=16)
    current_percentage: CalculatedPercent | None = None
    proposed_percentage: CalculatedPercent | None = None
    reason_code: Literal[
        "OWNERSHIP_PROPOSAL_REVIEW_REQUIRED",
        "OWNERSHIP_DOCUMENT_CONFLICT",
        "OWNERSHIP_DOCUMENT_INCOMPLETE",
        "OWNERSHIP_DOCUMENT_AMBIGUOUS",
    ]
    verification_state: Literal["REVIEW_REQUIRED", "REVIEWED"] = "REVIEW_REQUIRED"


class ManualOwnershipReviewReceipt(BaseModel):
    """Immutable safe receipt for one reviewed local manual declaration."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    case_id: UUID
    actor_id: Annotated[
        str,
        BeforeValidator(_normalize_safe_text),
        StringConstraints(pattern=r"^[a-z][a-z0-9-]{2,31}$"),
    ]
    reviewed_at: datetime
    rationale: Annotated[
        str,
        BeforeValidator(_normalize_safe_text),
        StringConstraints(min_length=10, max_length=240),
    ]
    evidence_document_id: UUID
    evidence_document_version: int = Field(ge=1)
    evidence_reference: str = Field(pattern=r"^MANUAL_DOC_[a-f0-9]{32}_V[1-9][0-9]*$")
    source_type: Literal["USER_SUPPLIED_DECLARATION"] = "USER_SUPPLIED_DECLARATION"
    source_selection: Literal[
        "USER_SUPPLIED_DECLARATION", "CURRENT_EVIDENCE", "DOCUMENT_OBSERVATIONS"
    ] = "USER_SUPPLIED_DECLARATION"
    observed_document_versions: tuple[OwnershipDocumentBinding, ...] = Field(
        default=(), max_length=32
    )
    selected_observation_ids: tuple[UUID, ...] = Field(default=(), max_length=128)
    replaced_analysis_id: UUID | None = None
    replaced_ownership_version: int | None = Field(default=None, ge=1)
    provider_name: Literal["MANUAL_DECLARATION_POC"] = "MANUAL_DECLARATION_POC"
    provider_environment: Literal["LOCAL"] = "LOCAL"
    as_of_date: date

    @field_validator("reviewed_at")
    @classmethod
    def reviewed_at_must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("manual ownership review timestamp must be UTC")
        return value


class PriorOwnershipAnalysisSnapshot(BaseModel):
    """Immutable bounded copy of a replaced terminal analysis."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    version: int = Field(ge=1)
    evidence: tuple[OwnershipEvidence, ...] = Field(default=(), max_length=256)
    document_observations: tuple[DocumentOwnershipObservation, ...] = Field(
        default=(), max_length=128
    )
    document_bindings: tuple[OwnershipDocumentBinding, ...] = Field(default=(), max_length=32)
    document_discrepancies: tuple[OwnershipDocumentDiscrepancy, ...] = Field(
        default=(), max_length=128
    )
    supplemental_parties: tuple[Party, ...] = Field(default=(), max_length=100)
    supplemental_relationships: tuple[OwnershipRelationship, ...] = Field(
        default=(), max_length=200
    )
    supplemental_evidence: tuple[OwnershipEvidence, ...] = Field(default=(), max_length=256)
    source_classification: Literal["SINGLE_SOURCE", "OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT"] = (
        "SINGLE_SOURCE"
    )
    identity_registration_number: SafeOptionalIdentifier | None = None
    identity_correction_version: int | None = Field(default=None, ge=0)
    tagging: OwnershipTaggingResult | None = None
    legal_form: RegistryLegalForm | None = None
    analysis_id: UUID
    correlation_id: UUID
    root_party_id: SafePartyId | None = None
    provider_name: SafeProviderName | None = None
    provider_environment: OwnershipEnvironment | None = None
    state: OwnershipAnalysisState
    parties: tuple[Party, ...] = Field(default_factory=tuple, max_length=100)
    relationships: tuple[OwnershipRelationship, ...] = Field(default_factory=tuple, max_length=200)
    candidates: tuple[OwnershipCandidate, ...] = Field(default_factory=tuple, max_length=100)
    issues: tuple[OwnershipAnalysisIssue, ...] = Field(default_factory=tuple, max_length=100)
    threshold_percent: OwnershipPercent
    events: tuple[OwnershipWorkflowEvent, ...] = Field(default_factory=tuple, max_length=128)
    error: SafeError | None = None
    created_at: datetime
    loaded_at: datetime | None = None
    analyzed_at: datetime | None = None
    updated_at: datetime
    manual_review_receipt: ManualOwnershipReviewReceipt | None = None


class OwnershipAnalysisRecord(BaseModel):
    """Case-linked ownership record isolated from onboarding and document aggregates."""

    model_config = ConfigDict(extra="forbid")

    case_id: UUID
    identity_registration_number: SafeOptionalIdentifier | None = None
    identity_correction_version: int | None = Field(default=None, ge=0)
    evidence: tuple[OwnershipEvidence, ...] = Field(default=(), max_length=256)
    document_observations: tuple[DocumentOwnershipObservation, ...] = Field(
        default=(), max_length=128
    )
    document_bindings: tuple[OwnershipDocumentBinding, ...] = Field(default=(), max_length=32)
    document_discrepancies: tuple[OwnershipDocumentDiscrepancy, ...] = Field(
        default=(), max_length=128
    )
    supplemental_parties: tuple[Party, ...] = Field(default=(), max_length=100)
    supplemental_relationships: tuple[OwnershipRelationship, ...] = Field(
        default=(), max_length=200
    )
    supplemental_evidence: tuple[OwnershipEvidence, ...] = Field(default=(), max_length=256)
    source_classification: Literal["SINGLE_SOURCE", "OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT"] = (
        "SINGLE_SOURCE"
    )
    tagging: OwnershipTaggingResult | None = None
    legal_form: RegistryLegalForm | None = None
    version: int = Field(default=0, ge=0)
    analysis_id: UUID
    correlation_id: UUID
    root_party_id: SafePartyId | None = None
    provider_name: SafeProviderName | None = None
    provider_environment: OwnershipEnvironment | None = None
    state: OwnershipAnalysisState
    parties: list[Party] = Field(default_factory=list)
    relationships: list[OwnershipRelationship] = Field(default_factory=list)
    candidates: list[OwnershipCandidate] = Field(default_factory=list)
    issues: list[OwnershipAnalysisIssue] = Field(default_factory=list)
    threshold_percent: OwnershipPercent
    threshold_comparator: str = Field(default="GREATER_THAN_OR_EQUAL_TO")
    events: list[OwnershipWorkflowEvent] = Field(default_factory=list)
    prior_analyses: tuple[PriorOwnershipAnalysisSnapshot, ...] = Field(
        default_factory=tuple, max_length=4
    )
    manual_review_receipt: ManualOwnershipReviewReceipt | None = None
    error: SafeError | None = None
    created_at: datetime
    loaded_at: datetime | None = None
    analyzed_at: datetime | None = None
    updated_at: datetime
