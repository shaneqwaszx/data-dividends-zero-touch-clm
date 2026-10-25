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
    model_validator,
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


def _normalize_optional_review_note(value: object) -> object:
    if value is None or isinstance(value, str) and not value.strip():
        return None
    normalized = _normalize_safe_text(value)
    if isinstance(normalized, str) and any(
        marker in normalized.casefold()
        for marker in (
            "assistant:", "developer message", "ignore previous", "ignore prior",
            "override instructions", "system prompt", "<script", "javascript:",
        )
    ):
        raise ValueError("ownership review note contains a prohibited instruction marker")
    return normalized


SafeOwnershipReviewNote = Annotated[
    Annotated[str, StringConstraints(min_length=10, max_length=240)] | None,
    BeforeValidator(_normalize_optional_review_note),
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
    CORPORATE_OWNERSHIP_UNRESOLVED = "CORPORATE_OWNERSHIP_UNRESOLVED"
    PERSON_IDENTITY_UNRESOLVED = "PERSON_IDENTITY_UNRESOLVED"
    SYNTHETIC_OWNERSHIP_EVIDENCE = "SYNTHETIC_OWNERSHIP_EVIDENCE"


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
    # Hybrid demonstration only: the same inclusive comparator applied to the declared
    # local synthetic basis. It never replaces the review classification above.
    synthetic_basis_threshold_result: OwnershipThresholdResult | None = None

    @model_validator(mode="after")
    def synthetic_basis_stays_under_review(self) -> "OwnershipCandidate":
        if self.synthetic_basis_threshold_result is not None and self.classification not in {
            OwnershipCandidateClassification.REVIEW_REQUIRED,
            OwnershipCandidateClassification.INDETERMINATE,
        }:
            raise ValueError("a synthetic-basis comparison requires a review classification")
        return self


class OwnershipDiscoveryOutcome(StrEnum):
    """Bounded per-corporate-owner retrieval outcome; never a legal finding."""

    CACHE_HIT = "CACHE_HIT"
    FETCHED = "FETCHED"
    DEFERRED_BELOW_TRACE_THRESHOLD = "DEFERRED_BELOW_TRACE_THRESHOLD"
    DEPTH_LIMIT = "DEPTH_LIMIT"
    BUSINESS_BUDGET = "BUSINESS_BUDGET"
    HARD_LIMIT = "HARD_LIMIT"
    UNVERIFIED_UEN = "UNVERIFIED_UEN"
    FOREIGN_UNSUPPORTED = "FOREIGN_UNSUPPORTED"
    UNSUPPORTED_LEGAL_FORM = "UNSUPPORTED_LEGAL_FORM"
    NOT_FOUND = "NOT_FOUND"
    PROVIDER_UNSUPPORTED = "PROVIDER_UNSUPPORTED"
    PROVIDER_PARTIAL = "PROVIDER_PARTIAL"
    PROVIDER_FAILED = "PROVIDER_FAILED"
    PROVIDER_INVALID = "PROVIDER_INVALID"
    CACHE_FAILURE = "CACHE_FAILURE"
    # Topology attached from an explicitly whitelisted local synthetic overlay after a
    # definitive official lookup; evidentially unresolved, never a registry result.
    LOCAL_SYNTHETIC_OVERLAY = "LOCAL_SYNTHETIC_OVERLAY"


RESOLVED_DISCOVERY_OUTCOMES = frozenset(
    {OwnershipDiscoveryOutcome.CACHE_HIT, OwnershipDiscoveryOutcome.FETCHED}
)
# Branches whose holders are attached, whatever the evidence basis.
TOPOLOGY_RESOLVED_DISCOVERY_OUTCOMES = RESOLVED_DISCOVERY_OUTCOMES | {
    OwnershipDiscoveryOutcome.LOCAL_SYNTHETIC_OVERLAY
}
OfficialEntityLookup = Literal[
    "ENTITY_PROFILE_FETCHED",
    "ENTITY_PROFILE_CACHE_REUSED",
    "NOT_FOUND",
    "NOT_FOUND_CACHE_REUSED",
]
OwnershipSourceClassification = Literal[
    "SINGLE_SOURCE",
    "OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT",
    "OFFICIAL_MOCK_PLUS_LOCAL_DIRECT_OVERLAY",
]


OfficialShareholderLookup = Literal["SHAREHOLDERS_FETCHED", "SHAREHOLDERS_CACHE_REUSED"]
# D-079 discovery reason codes for an issuer whose entity-basic profile is NOT_FOUND.
OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE = "OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE"
OFFICIAL_SHAREHOLDERS_EMPTY = "OFFICIAL_SHAREHOLDERS_EMPTY"
# D-081: the same retained rows, also distributed in the hybrid lane as POC equal units.
OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS = "OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS"
OFFICIAL_SHAREHOLDER_RETAINED_REASONS = frozenset(
    {OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE, OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS}
)


class OfficialShareholderObservation(BaseModel):
    """One official Marketplace Mock shareholder row kept beside the graph (D-079).

    Retained for a corporate holder whose entity-basic profile is a definitive NOT_FOUND.
    It is never a graph party, edge, identity, legal-form or percentage claim. Only an
    explicitly Active row is a current interest; withdrawn rows remain history.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    source_party_id: SafePartyId
    display_name: SafePartyName
    party_type: PartyType
    source_category: SafeOptionalIdentifier | None = None
    source_status: SafeOptionalIdentifier | None = None
    share_allotted: Decimal | None = Field(
        default=None, ge=0, allow_inf_nan=False, max_digits=18, decimal_places=6
    )
    # D-080: the row's own source share class and currency. Units are comparable only
    # within one class; no class rule, weighting or denominator is implied.
    share_type: SafeOptionalIdentifier | None = None
    currency: SafeOptionalIdentifier | None = None
    current_interest: bool
    registration_identifier: SafeOptionalIdentifier | None = None
    provider: Literal["ACRA_REGISTRY_ACQUISITION"] = "ACRA_REGISTRY_ACQUISITION"
    environment: Literal["MOCK"] = "MOCK"
    dataset_namespace: Literal["ACRA_API_MARKETPLACE_MOCK_V1"] = "ACRA_API_MARKETPLACE_MOCK_V1"
    source_operation: Literal["OWNERSHIP_PARTIES"] = "OWNERSHIP_PARTIES"
    retrieved_at: datetime
    evidence_reference: str = Field(
        min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
    )

    @field_validator("share_allotted", mode="before")
    @classmethod
    def exact_share_units(cls, value: object) -> object:
        if isinstance(value, (float, bool)):
            raise ValueError("share units must be exact")
        return value

    @field_validator("retrieved_at")
    @classmethod
    def retrieved_at_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("official shareholder evidence time must be UTC")
        return value

    @model_validator(mode="after")
    def only_active_rows_are_current(self) -> "OfficialShareholderObservation":
        active = (
            self.source_status is not None and self.source_status.strip().casefold() == "active"
        )
        if self.current_interest != active:
            raise ValueError("only an explicitly Active row is a current interest")
        return self


class OwnershipDiscoveryRecord(BaseModel):
    """One corporate owner's discovery decision with its root-equivalent exposure.

    `max_effective_percent` is the exact sum of current path products reaching the
    corporate owner when it was decided: the most root-equivalent interest that an
    unresolved branch could still hide. Overlay records also keep the separate official
    entity lookup observation and the resulting identity basis.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    party_id: SafePartyId
    display_name: SafePartyName
    registration_number: SafeOptionalIdentifier | None = None
    depth: int = Field(ge=1, le=64)
    outcome: OwnershipDiscoveryOutcome
    max_effective_percent: CalculatedPercent | None = None
    reason_code: SafeProviderName | None = None
    identity_basis: Literal["OFFICIAL_MOCK_ENTITY_PROFILE", "LOCAL_SYNTHETIC_IDENTITY"] | None = (
        None
    )
    official_entity_lookup: OfficialEntityLookup | None = None
    official_legal_form: RegistryLegalForm | None = None
    # D-079 only: official shareholder rows retained without an entity profile.
    official_shareholders: tuple[OfficialShareholderObservation, ...] = Field(
        default=(), max_length=64
    )
    official_shareholder_lookup: OfficialShareholderLookup | None = None

    @model_validator(mode="after")
    def official_shareholders_are_explicit(self) -> "OwnershipDiscoveryRecord":
        retained = (
            self.outcome == OwnershipDiscoveryOutcome.PROVIDER_PARTIAL
            and self.reason_code in OFFICIAL_SHAREHOLDER_RETAINED_REASONS
        )
        if retained != bool(self.official_shareholders) or retained != (
            self.official_shareholder_lookup is not None
        ):
            raise ValueError("official shareholder rows require their partial outcome and lookup")
        if len({item.source_party_id for item in self.official_shareholders}) != len(
            self.official_shareholders
        ):
            raise ValueError("official shareholder rows must be unique")
        current = [item for item in self.official_shareholders if item.current_interest]
        if self.reason_code == OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS and (
            not retained
            or not current
            or any(item.share_allotted is None or item.share_allotted <= 0 for item in current)
        ):
            raise ValueError("POC equal-unit records require retained positive current units")
        if (
            self.reason_code == OFFICIAL_SHAREHOLDERS_EMPTY
            and self.outcome != OwnershipDiscoveryOutcome.NOT_FOUND
        ):
            raise ValueError("empty official shareholders keep the NOT_FOUND outcome")
        return self

    @model_validator(mode="after")
    def overlay_identity_is_explicit(self) -> "OwnershipDiscoveryRecord":
        overlay = self.outcome == OwnershipDiscoveryOutcome.LOCAL_SYNTHETIC_OVERLAY
        if overlay != (self.identity_basis is not None) or overlay != (
            self.official_entity_lookup is not None
        ):
            raise ValueError("overlay records require an explicit official lookup and identity")
        if overlay:
            official = self.official_entity_lookup in {
                "ENTITY_PROFILE_FETCHED",
                "ENTITY_PROFILE_CACHE_REUSED",
            }
            if official != (self.identity_basis == "OFFICIAL_MOCK_ENTITY_PROFILE") or official != (
                self.official_legal_form is not None
            ):
                raise ValueError("overlay identity basis disagrees with the official lookup")
        elif self.official_legal_form is not None:
            raise ValueError("official legal form is retained only for overlay records")
        return self


def discovery_topology_resolved(record: OwnershipDiscoveryRecord) -> bool:
    """Holders are attached, whatever the evidence basis (registry, overlay or D-081 POC)."""
    return record.outcome in TOPOLOGY_RESOLVED_DISCOVERY_OUTCOMES or (
        record.outcome == OwnershipDiscoveryOutcome.PROVIDER_PARTIAL
        and record.reason_code == OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS
    )


class OwnershipDiscoveryAudit(BaseModel):
    """Reviewer-safe corporate discovery audit kept beside the authoritative graph.

    `graph_complete` describes evidence completeness; `classification_certainty`
    describes what the bound can say despite omissions. Neither relaxes the existing
    review rule for an incomplete graph.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    method: Literal["REGISTRY_CORPORATE_DISCOVERY_V1"] = "REGISTRY_CORPORATE_DISCOVERY_V1"
    trace_threshold_percent: OwnershipPercent
    ubo_threshold_percent: OwnershipPercent
    max_corporate_depth: int = Field(ge=1, le=7)
    call_budget_enabled: bool
    call_budget_max: int = Field(ge=1, le=32)
    graph_complete: bool
    classification_certainty: Literal["COMPLETE", "BOUNDED_NO_THRESHOLD_CHANGE", "UNCERTAIN"]
    unresolved_upper_bound_percent: CalculatedPercent | None = None
    registry_lookups: int = Field(ge=0, le=64)
    provider_backed_lookups: int = Field(ge=0, le=64)
    cache_hits: int = Field(ge=0, le=64)
    records: tuple[OwnershipDiscoveryRecord, ...] = Field(default=(), max_length=100)
    unresolved_person_party_ids: tuple[SafePartyId, ...] = Field(default=(), max_length=32)
    # Hybrid official-Mock plus local direct overlay only. Topology, official identity
    # and quantitative evidence completeness stay separate from certainty/readiness.
    overlay_scenario_id: SafeProviderName | None = None
    topology_complete: bool | None = None
    official_identity_complete: bool | None = None
    quantitative_evidence_complete: bool | None = None

    @model_validator(mode="after")
    def consistent_audit(self) -> "OwnershipDiscoveryAudit":
        if self.provider_backed_lookups + self.cache_hits != self.registry_lookups:
            raise ValueError("discovery lookup counts are inconsistent")
        if len({item.party_id for item in self.records}) != len(self.records):
            raise ValueError("discovery records must be unique per party")
        complete = all(item.outcome in RESOLVED_DISCOVERY_OUTCOMES for item in self.records)
        if self.graph_complete != complete:
            raise ValueError("graph completeness disagrees with discovery records")
        if self.classification_certainty == "COMPLETE" and (
            not self.graph_complete or self.unresolved_person_party_ids
        ):
            raise ValueError("complete certainty requires a complete unambiguous graph")
        if self.trace_threshold_percent > self.ubo_threshold_percent:
            raise ValueError("trace threshold cannot exceed the UBO threshold")
        separated = (
            self.topology_complete,
            self.official_identity_complete,
            self.quantitative_evidence_complete,
        )
        overlay_records = [
            item
            for item in self.records
            if item.outcome == OwnershipDiscoveryOutcome.LOCAL_SYNTHETIC_OVERLAY
        ]
        poc_records = [
            item
            for item in self.records
            if item.reason_code == OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS
        ]
        if self.overlay_scenario_id is None:
            if any(value is not None for value in separated) or overlay_records or poc_records:
                raise ValueError("evidence separation is retained only for hybrid overlays")
            return self
        if any(value is None for value in separated):
            raise ValueError("hybrid overlays require explicit evidence separation")
        topology = all(discovery_topology_resolved(item) for item in self.records)
        official = all(
            item.outcome in RESOLVED_DISCOVERY_OUTCOMES
            or item.identity_basis == "OFFICIAL_MOCK_ENTITY_PROFILE"
            for item in self.records
        )
        if (
            self.topology_complete != topology
            or self.official_identity_complete != official
            # The root's own direct holders always come from the local overlay.
            or self.quantitative_evidence_complete is not False
            or self.classification_certainty == "COMPLETE"
        ):
            raise ValueError("hybrid evidence separation disagrees with discovery records")
        return self


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
    rationale: SafeOwnershipReviewNote = None
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


# D-082: the one opt-in demonstration policy that may accept a declared POC basis.
OWNERSHIP_POC_ACCEPTANCE_POLICY = "D082_HYBRID_POC_EQUAL_UNITS_V1"
POC_ACCEPTANCE_REQUIRED_ISSUES = frozenset(
    {
        OwnershipIssueCode.OWNERSHIP_DENOMINATOR_REQUIRED,
        OwnershipIssueCode.SYNTHETIC_OWNERSHIP_EVIDENCE,
    }
)
POC_ACCEPTANCE_ISSUES = POC_ACCEPTANCE_REQUIRED_ISSUES | {OwnershipIssueCode.UBO_REVIEW_REQUIRED}


class OwnershipPocAcceptance(BaseModel):
    """D-082 acceptance of a declared POC equal-unit basis at the readiness boundary.

    Recorded beside the unchanged review state, issues and classifications, and bound
    to one analysis version and its exact content. It is never ownership verification,
    a legal UBO determination or a provisional classification, and it grants readiness
    only while the current runtime still enables the policy.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    policy: Literal["D082_HYBRID_POC_EQUAL_UNITS_V1"]
    accepted_at: datetime
    case_id: UUID
    analysis_id: UUID
    ownership_version: int = Field(ge=1)
    identity_registration_number: SafeOptionalIdentifier
    identity_correction_version: int = Field(ge=0)
    overlay_scenario_id: SafeProviderName
    accepted_issue_codes: tuple[OwnershipIssueCode, ...] = Field(min_length=2, max_length=3)
    poc_relationship_ids: tuple[SafeRelationshipId, ...] = Field(min_length=1, max_length=200)
    # D1=B (R1): how many exact observed official OFFICERS Owner role records (current and
    # ceased) were matched against the protected allowlist and kept as descriptive context.
    # They stay in the analysis evidence; no identifier or digest is stored here, and they
    # are neither shareholdings nor corroboration of the synthetic links.
    descriptive_current_role_count: int = Field(default=0, ge=0, le=16)
    descriptive_ceased_role_count: int = Field(default=0, ge=0, le=16)
    basis_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")

    @field_validator("accepted_at")
    @classmethod
    def accepted_at_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("POC acceptance time must be UTC")
        return value

    @model_validator(mode="after")
    def accepts_only_declared_poc_assumptions(self) -> "OwnershipPocAcceptance":
        codes = set(self.accepted_issue_codes)
        if (
            self.accepted_issue_codes != tuple(sorted(codes))
            or not POC_ACCEPTANCE_REQUIRED_ISSUES <= codes <= POC_ACCEPTANCE_ISSUES
            or (OwnershipIssueCode.UBO_REVIEW_REQUIRED in codes)
            != bool(self.descriptive_current_role_count + self.descriptive_ceased_role_count)
            or self.poc_relationship_ids != tuple(sorted(set(self.poc_relationship_ids)))
        ):
            raise ValueError("POC acceptance covers only declared POC assumption issues")
        return self


def _poc_acceptance_is_bound(
    acceptance: OwnershipPocAcceptance | None,
    *,
    analysis_id: UUID,
    state: OwnershipAnalysisState,
    source_classification: str,
    manual_review_receipt: object,
) -> bool:
    return acceptance is None or (
        acceptance.analysis_id == analysis_id
        and state == OwnershipAnalysisState.REVIEW_REQUIRED
        and source_classification == "OFFICIAL_MOCK_PLUS_LOCAL_DIRECT_OVERLAY"
        and manual_review_receipt is None
    )


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
    source_classification: OwnershipSourceClassification = "SINGLE_SOURCE"
    identity_registration_number: SafeOptionalIdentifier | None = None
    identity_correction_version: int | None = Field(default=None, ge=0)
    tagging: OwnershipTaggingResult | None = None
    legal_form: RegistryLegalForm | None = None
    discovery: OwnershipDiscoveryAudit | None = None
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
    poc_acceptance: OwnershipPocAcceptance | None = None

    @model_validator(mode="after")
    def poc_acceptance_is_bound(self) -> "PriorOwnershipAnalysisSnapshot":
        if not _poc_acceptance_is_bound(
            self.poc_acceptance,
            analysis_id=self.analysis_id,
            state=self.state,
            source_classification=self.source_classification,
            manual_review_receipt=self.manual_review_receipt,
        ):
            raise ValueError("a POC acceptance binds only its own hybrid review analysis")
        return self


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
    source_classification: OwnershipSourceClassification = "SINGLE_SOURCE"
    tagging: OwnershipTaggingResult | None = None
    legal_form: RegistryLegalForm | None = None
    discovery: OwnershipDiscoveryAudit | None = None
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
    # D-082 only: accepted declared POC basis; the review state and issues stay intact.
    poc_acceptance: OwnershipPocAcceptance | None = None
    error: SafeError | None = None
    created_at: datetime
    loaded_at: datetime | None = None
    analyzed_at: datetime | None = None
    updated_at: datetime

    @model_validator(mode="after")
    def poc_acceptance_is_bound(self) -> "OwnershipAnalysisRecord":
        if not _poc_acceptance_is_bound(
            self.poc_acceptance,
            analysis_id=self.analysis_id,
            state=self.state,
            source_classification=self.source_classification,
            manual_review_receipt=self.manual_review_receipt,
        ) or (self.poc_acceptance is not None and self.poc_acceptance.case_id != self.case_id):
            raise ValueError("a POC acceptance binds only its own hybrid review analysis")
        return self
