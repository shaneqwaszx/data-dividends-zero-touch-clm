"""Case-bound manual ownership declarations for the local proof of concept.

This module validates structured, operator-reviewed evidence. It deliberately does
not read registry evidence or present the declaration as official registry data.
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Final, Literal, Never, Protocol
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

from app.connectors.ownership import (
    OwnershipProviderError,
    OwnershipProviderMetadata,
    OwnershipProviderRequest,
    OwnershipSourceResult,
)
from app.domain.documents import DocumentProcessingRecord, DocumentProcessingState
from app.domain.models import OnboardingCase
from app.domain.ownership import (
    ManualOwnershipReviewReceipt,
    OwnershipBasis,
    OwnershipDocumentBinding,
    OwnershipEnvironment,
    OwnershipPercent,
    OwnershipProvenance,
    OwnershipRelationship,
    OwnershipRelationshipType,
    Party,
    PartyType,
    SafePartyId,
    SafeRelationshipId,
)
from app.domain.reconciliation import ReconciliationCaseRecord

MANUAL_OWNERSHIP_PROVIDER: Final[Literal["MANUAL_DECLARATION_POC"]] = "MANUAL_DECLARATION_POC"
MANUAL_OWNERSHIP_SOURCE_TYPE: Final[Literal["USER_SUPPLIED_DECLARATION"]] = (
    "USER_SUPPLIED_DECLARATION"
)
MAX_MANUAL_PARTIES = 100
MAX_MANUAL_RELATIONSHIPS = 200

_PROMPT_MARKERS = (
    "assistant:",
    "developer message",
    "ignore previous",
    "ignore prior",
    "override instructions",
    "system prompt",
    "<script",
    "javascript:",
)


def _normalize_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    if not normalized:
        raise ValueError("manual ownership text must not be blank")
    if any(category(character).startswith("C") for character in normalized):
        raise ValueError("manual ownership text must not contain control characters")
    if any(marker in normalized.casefold() for marker in _PROMPT_MARKERS):
        raise ValueError("manual ownership text contains a prohibited instruction marker")
    return normalized


def _normalize_uen(value: object) -> object:
    if not isinstance(value, str):
        return value
    return value.strip().upper()


def _decimal_input(value: object) -> object:
    if isinstance(value, (float, bool)):
        raise ValueError("economic interest must use an exact decimal value")
    return value


SafeReviewText = Annotated[
    str,
    BeforeValidator(_normalize_text),
    StringConstraints(min_length=10, max_length=240),
]
SafeActorId = Annotated[
    str,
    BeforeValidator(_normalize_text),
    StringConstraints(pattern=r"^[a-z][a-z0-9-]{2,31}$"),
]
CanonicalUen = Annotated[
    str,
    BeforeValidator(_normalize_uen),
    StringConstraints(pattern=r"^[0-9A-Z]{9,10}$"),
]
ExactOwnershipPercent = Annotated[OwnershipPercent, BeforeValidator(_decimal_input)]


class ManualOwnershipEvidenceError(OwnershipProviderError):
    """Safe failure for rejected or stale manual ownership evidence."""

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ManualOwnershipCaseReader(Protocol):
    def get_case(self, case_id: UUID) -> OnboardingCase | None: ...


class ManualOwnershipDocumentReader(Protocol):
    def get(self, document_id: UUID) -> DocumentProcessingRecord | None: ...


class ManualOwnershipReconciliationReader(Protocol):
    def resolved_document_checkpoint(
        self, *, case_id: UUID, document_id: UUID, event_count: int
    ) -> ReconciliationCaseRecord | None: ...


class ManualEconomicInterest(BaseModel):
    """One direct, declared economic-interest edge without provider provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    relationship_id: SafeRelationshipId
    parent_party_id: SafePartyId
    child_party_id: SafePartyId
    ownership_percent: ExactOwnershipPercent
    relationship_type: Literal["DIRECT_ECONOMIC_INTEREST"] = "DIRECT_ECONOMIC_INTEREST"


class ManualOwnershipDeclaration(BaseModel):
    """Bounded structured declaration reviewed against one current case document."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    case_id: UUID
    root_registration_number: CanonicalUen
    evidence_document_id: UUID
    evidence_document_version: int = Field(ge=1)
    source_type: Literal["USER_SUPPLIED_DECLARATION"] = MANUAL_OWNERSHIP_SOURCE_TYPE
    as_of_date: date
    rationale: SafeReviewText
    source_selection: Literal[
        "USER_SUPPLIED_DECLARATION", "CURRENT_EVIDENCE", "DOCUMENT_OBSERVATIONS"
    ] = "USER_SUPPLIED_DECLARATION"
    observed_document_versions: tuple[OwnershipDocumentBinding, ...] = Field(
        default=(), max_length=32
    )
    selected_observation_ids: tuple[UUID, ...] = Field(default=(), max_length=128)
    root_party_id: SafePartyId
    parties: tuple[Party, ...] = Field(min_length=2, max_length=MAX_MANUAL_PARTIES)
    relationships: tuple[ManualEconomicInterest, ...] = Field(
        min_length=1,
        max_length=MAX_MANUAL_RELATIONSHIPS,
    )

    @field_validator("parties")
    @classmethod
    def reject_instruction_like_party_names(cls, parties: tuple[Party, ...]) -> tuple[Party, ...]:
        for party in parties:
            _normalize_text(party.display_name)
        return parties

    @model_validator(mode="after")
    def validate_declared_graph(self) -> ManualOwnershipDeclaration:
        party_by_id = {party.party_id: party for party in self.parties}
        if len(party_by_id) != len(self.parties):
            raise ValueError("manual ownership party IDs must be unique")
        root = party_by_id.get(self.root_party_id)
        if root is None or root.party_type != PartyType.LEGAL_ENTITY:
            raise ValueError("manual ownership root must be a declared legal entity")
        if root.registration_number != self.root_registration_number:
            raise ValueError("manual ownership root must match the declared UEN")

        relationship_ids: set[str] = set()
        edge_pairs: set[tuple[str, str]] = set()
        totals: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        adjacency: defaultdict[str, list[str]] = defaultdict(list)
        known = set(party_by_id)
        for relationship in self.relationships:
            if relationship.relationship_id in relationship_ids:
                raise ValueError("manual ownership relationship IDs must be unique")
            relationship_ids.add(relationship.relationship_id)
            pair = (relationship.parent_party_id, relationship.child_party_id)
            if pair in edge_pairs:
                raise ValueError("manual ownership edges must be unique")
            edge_pairs.add(pair)
            if pair[0] not in known or pair[1] not in known:
                raise ValueError("manual ownership relationship endpoints must exist")
            if pair[0] == pair[1]:
                raise ValueError("manual ownership self-relationships are invalid")
            if party_by_id[pair[0]].party_type != PartyType.LEGAL_ENTITY:
                raise ValueError("manual ownership parents must be legal entities")
            totals[pair[0]] += relationship.ownership_percent
            adjacency[pair[0]].append(pair[1])

        # Retaining current evidence must not infer missing percentages. The owning
        # service still validates and compares the exact current graph before replacement.
        if self.source_selection == "CURRENT_EVIDENCE" and any(
            total > Decimal("100") for total in totals.values()
        ):
            raise ValueError("each retained parent economic-interest total must not exceed 100")
        if self.source_selection != "CURRENT_EVIDENCE" and any(
            total != Decimal("100") for total in totals.values()
        ):
            raise ValueError("each declared parent economic-interest total must equal 100")
        _reject_cycles(adjacency, known)
        _reject_disconnected(self.root_party_id, adjacency, known)
        return self


class ManualOwnershipEvidenceProvider:
    """Read-only local provider for one reviewed, case-bound declaration."""

    def __init__(
        self,
        *,
        declaration: ManualOwnershipDeclaration,
        reviewed_by_actor_id: SafeActorId,
        cases: ManualOwnershipCaseReader,
        documents: ManualOwnershipDocumentReader,
        reconciliation: ManualOwnershipReconciliationReader | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._declaration = declaration
        self._cases = cases
        self._documents = documents
        self._reconciliation = reconciliation
        self._clock = clock or (lambda: datetime.now(UTC))
        reviewed_at = self._clock()
        _require_utc(reviewed_at)
        self._validate_current_bindings(reviewed_at)
        self._receipt = ManualOwnershipReviewReceipt(
            case_id=declaration.case_id,
            actor_id=reviewed_by_actor_id,
            reviewed_at=reviewed_at,
            rationale=declaration.rationale,
            evidence_document_id=declaration.evidence_document_id,
            evidence_document_version=declaration.evidence_document_version,
            evidence_reference=_evidence_reference(declaration),
            as_of_date=declaration.as_of_date,
            source_selection=declaration.source_selection,
            observed_document_versions=declaration.observed_document_versions,
            selected_observation_ids=declaration.selected_observation_ids,
        )
        self._source = _build_source(declaration, reviewed_at)

    @property
    def metadata(self) -> OwnershipProviderMetadata:
        return OwnershipProviderMetadata(
            provider_name=MANUAL_OWNERSHIP_PROVIDER,
            environment=OwnershipEnvironment.LOCAL,
        )

    @property
    def review_receipt(self) -> ManualOwnershipReviewReceipt:
        return self._receipt.model_copy(deep=True)

    def load(self, request: OwnershipProviderRequest) -> OwnershipSourceResult:
        now = self._clock()
        _require_utc(now)
        if request.case_id != self._declaration.case_id:
            _reject(
                "MANUAL_OWNERSHIP_CASE_MISMATCH",
                "The declaration does not belong to this case.",
            )
        if (
            _normalize_uen(request.registration_number)
            != self._declaration.root_registration_number
        ):
            _reject(
                "MANUAL_OWNERSHIP_IDENTITY_MISMATCH",
                "The declaration does not match the canonical case identity.",
            )
        self._validate_current_bindings(now)
        return self._source.model_copy(deep=True)

    def _validate_current_bindings(self, now: datetime) -> None:
        declaration = self._declaration
        if declaration.as_of_date > now.date():
            _reject("MANUAL_OWNERSHIP_FUTURE_DATE", "The declaration date cannot be in the future.")

        case = self._cases.get_case(declaration.case_id)
        if case is None:
            _reject("MANUAL_OWNERSHIP_CASE_NOT_FOUND", "The onboarding case was not found.")
        if case.case_id != declaration.case_id or case.entity is None:
            _reject(
                "MANUAL_OWNERSHIP_CASE_MISMATCH",
                "The declaration does not belong to the current canonical case.",
            )
        if _normalize_uen(case.entity.registration_number) != declaration.root_registration_number:
            _reject(
                "MANUAL_OWNERSHIP_IDENTITY_MISMATCH",
                "The declaration does not match the canonical case identity.",
            )

        document = self._documents.get(declaration.evidence_document_id)
        if document is None:
            _reject("MANUAL_OWNERSHIP_DOCUMENT_NOT_FOUND", "The evidence document was not found.")
        if document.case_id != declaration.case_id:
            _reject(
                "MANUAL_OWNERSHIP_DOCUMENT_CASE_MISMATCH",
                "The evidence document does not belong to this case.",
            )
        if (
            not document.is_current_evidence
            or len(document.events) != declaration.evidence_document_version
        ):
            _reject(
                "MANUAL_OWNERSHIP_DOCUMENT_STALE",
                "The evidence document is no longer the reviewed current version.",
            )
        completed_at = document.reviewed_at
        if document.state != DocumentProcessingState.REVIEWED or completed_at is None:
            checkpoint = (
                self._reconciliation.resolved_document_checkpoint(
                    case_id=declaration.case_id,
                    document_id=document.document_id,
                    event_count=declaration.evidence_document_version,
                )
                if self._reconciliation is not None else None
            )
            completed_at = checkpoint.updated_at if checkpoint is not None else None
        if completed_at is None:
            _reject(
                "MANUAL_OWNERSHIP_DOCUMENT_NOT_REVIEWED",
                "The evidence document has not completed review.",
            )
        if completed_at.tzinfo is None or completed_at.utcoffset() != UTC.utcoffset(
            completed_at
        ):
            _reject(
                "MANUAL_OWNERSHIP_DOCUMENT_DATE_INVALID",
                "The evidence review date must be timezone-aware UTC.",
            )
        if completed_at > now:
            _reject(
                "MANUAL_OWNERSHIP_FUTURE_DATE",
                "The evidence review date cannot be in the future.",
            )


def _build_source(
    declaration: ManualOwnershipDeclaration,
    reviewed_at: datetime,
) -> OwnershipSourceResult:
    provenance = OwnershipProvenance(
        provider=MANUAL_OWNERSHIP_PROVIDER,
        environment=OwnershipEnvironment.LOCAL,
        source_reference=_evidence_reference(declaration),
        sourced_at=reviewed_at,
    )
    relationships = [
        OwnershipRelationship(
            relationship_id=relationship.relationship_id,
            parent_party_id=relationship.parent_party_id,
            child_party_id=relationship.child_party_id,
            ownership_percent=relationship.ownership_percent,
            relationship_type=OwnershipRelationshipType.OWNERSHIP,
            basis=OwnershipBasis.ECONOMIC_INTEREST,
            provenance=provenance,
        )
        for relationship in declaration.relationships
    ]
    return OwnershipSourceResult(
        root_party_id=declaration.root_party_id,
        parties=list(declaration.parties),
        relationships=relationships,
    )


def _evidence_reference(declaration: ManualOwnershipDeclaration) -> str:
    return (
        f"MANUAL_DOC_{declaration.evidence_document_id.hex}"
        f"_V{declaration.evidence_document_version}"
    )


def _reject_cycles(adjacency: dict[str, list[str]], known: set[str]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(party_id: str) -> None:
        if party_id in visiting:
            raise ValueError("manual ownership graph must not contain cycles")
        if party_id in visited:
            return
        visiting.add(party_id)
        for child_id in adjacency.get(party_id, ()):
            visit(child_id)
        visiting.remove(party_id)
        visited.add(party_id)

    for party_id in sorted(known):
        visit(party_id)


def _reject_disconnected(
    root_party_id: str,
    adjacency: dict[str, list[str]],
    known: set[str],
) -> None:
    reachable = {root_party_id}
    queue = deque([root_party_id])
    while queue:
        parent = queue.popleft()
        for child in adjacency.get(parent, ()):
            if child not in reachable:
                reachable.add(child)
                queue.append(child)
    if reachable != known:
        raise ValueError("manual ownership graph must not contain disconnected parties")


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("manual ownership clock must return timezone-aware UTC")


def _reject(code: str, message: str) -> Never:
    raise ManualOwnershipEvidenceError(code=code, message=message)
