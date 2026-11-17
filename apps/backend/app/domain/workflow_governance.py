"""Workflow authoring governance (ADR-017, D-135): the frozen P2-1 contract models (C0).

These models are the contract shared by the repository, the service, the routes and the
frontend. Changing them after the freeze needs a contract-change note and the integrator's
approval (``docs/contracts/WORKFLOW_GOVERNANCE_API.md``).

Storage shape (B-0 final, D-1):
- the workflow definition ``payload`` keeps its exact P2-0 shape (``workflows.py``);
- governance state lives in reserved **top-level** fields of the same document;
- full history lives in three insert-only cold collections.

Nothing here performs I/O, reads a case or calls a provider.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain.workflows import WorkflowField, WorkflowFieldKind, WorkflowStage

# --- Reserved top-level field names (P2-0 tools already refuse documents carrying them) ---

FIELD_REQUIRED_BASELINE = "required_baseline"
FIELD_OPEN_PROPOSAL = "open_proposal"
FIELD_DECIDED_PROPOSALS = "decided_proposals"
FIELD_GOVERNANCE_EVENTS = "governance_events"
FIELD_NOTICES = "notices"
FIELD_OUTBOX = "outbox"
FIELD_VERSION_PROVENANCE = "version_provenance"
FIELD_MIGRATION_MARKER = "p2_1_migration_marker"
FIELD_GOVERNANCE_SEQUENCE = "governance_sequence"
GOVERNANCE_TOP_LEVEL_FIELDS = (
    FIELD_REQUIRED_BASELINE,
    FIELD_OPEN_PROPOSAL,
    FIELD_DECIDED_PROPOSALS,
    FIELD_GOVERNANCE_EVENTS,
    FIELD_NOTICES,
    FIELD_OUTBOX,
    FIELD_VERSION_PROVENANCE,
    FIELD_MIGRATION_MARKER,
    FIELD_GOVERNANCE_SEQUENCE,
)

# --- Cold collections (insert-only; ``_id = <logical_id>#<attempt>``) ---

COLD_VERSIONS = "workflow_versions"
COLD_PROPOSALS = "workflow_proposals"
COLD_EVENTS = "workflow_governance_events"
COLD_COLLECTIONS = (COLD_VERSIONS, COLD_PROPOSALS, COLD_EVENTS)

# --- Limits (ADR-017 §5 byte budget; RD-5 counts are maxima, never truncation) ---

MIB = 1024 * 1024
MAX_ENCODED_VERSION_BYTES = 1 * MIB
MAX_PROPOSAL_RECORD_BYTES = 1 * MIB
MAX_NOTICE_BYTES = 4 * 1024
MAX_OUTBOX_RECORDS = 32
MAX_BASELINE_BYTES = 1 * MIB
COMPACTION_START_BYTES = 4 * MIB
HARD_CEILING_BYTES = 8 * MIB
MAX_HOT_VERSIONS = 16  # the active version plus up to 15 more
MAX_HOT_DECIDED_PROPOSALS = 16
MAX_HOT_EVENTS = 64
MAX_UNACKNOWLEDGED_NOTICES = 64
DRAFT_RELEASE_AFTER_DAYS = 14  # RD-4
DECISION_REASON_MIN = 10
DECISION_REASON_MAX = 240
MAX_RELATED_POLICY_PROPOSALS = 8
NO_ACTIVE_VERSION = 0  # the stored ``active_version`` when nothing is active

PERMANENT_OBLIGATION_WARNING = (
    "Once approved, this required step or field can never be removed or weakened in the product."
)
LEGACY_VERSION_NOTE = (
    "Activated by a Director before approval governance; not independently approved."
)


class GovernanceErrorCode(StrEnum):
    """Frozen error codes (programme §3). HTTP status in ``GOVERNANCE_ERROR_STATUS``."""

    PROPOSAL_OPEN = "WORKFLOW_PROPOSAL_OPEN"
    PROPOSAL_STALE = "WORKFLOW_PROPOSAL_STALE"
    PROPOSAL_NOT_FOUND = "WORKFLOW_PROPOSAL_NOT_FOUND"
    PROPOSAL_STATE_INVALID = "WORKFLOW_PROPOSAL_STATE_INVALID"
    PROPOSAL_CONTENT_CHANGED = "WORKFLOW_PROPOSAL_CONTENT_CHANGED"
    PROPOSAL_KIND_NOT_AVAILABLE = "WORKFLOW_PROPOSAL_KIND_NOT_AVAILABLE"
    PROPOSAL_INVALID = "WORKFLOW_PROPOSAL_INVALID"
    PROPOSAL_EMPTY = "WORKFLOW_PROPOSAL_EMPTY"
    REQUIRED_OBLIGATION_REMOVED = "WORKFLOW_REQUIRED_OBLIGATION_REMOVED"
    REQUIRED_OBLIGATION_WEAKENED = "WORKFLOW_REQUIRED_OBLIGATION_WEAKENED"
    PERMANENT_OBLIGATION_ACK_REQUIRED = "WORKFLOW_PERMANENT_OBLIGATION_ACKNOWLEDGEMENT_REQUIRED"
    SELF_DECISION_REFUSED = "WORKFLOW_SELF_DECISION_REFUSED"
    PROPOSAL_TOO_LARGE = "WORKFLOW_PROPOSAL_TOO_LARGE"
    HISTORY_UNAVAILABLE = "WORKFLOW_HISTORY_UNAVAILABLE"
    GOVERNANCE_NOT_MIGRATED = "WORKFLOW_GOVERNANCE_NOT_MIGRATED"
    DRAFT_NOT_RELEASABLE = "WORKFLOW_DRAFT_NOT_RELEASABLE"
    RUN_CONFIRMATION_IN_PROGRESS = "WORKFLOW_RUN_CONFIRMATION_IN_PROGRESS"
    NOTICES_UNACKNOWLEDGED = "WORKFLOW_NOTICES_UNACKNOWLEDGED"
    ROUTE_RETIRED = "WORKFLOW_ROUTE_RETIRED"


GOVERNANCE_ERROR_STATUS: dict[GovernanceErrorCode, int] = {
    GovernanceErrorCode.PROPOSAL_OPEN: 409,
    GovernanceErrorCode.PROPOSAL_STALE: 409,
    GovernanceErrorCode.PROPOSAL_NOT_FOUND: 404,
    GovernanceErrorCode.PROPOSAL_STATE_INVALID: 409,
    GovernanceErrorCode.PROPOSAL_CONTENT_CHANGED: 409,
    GovernanceErrorCode.PROPOSAL_KIND_NOT_AVAILABLE: 422,
    GovernanceErrorCode.PROPOSAL_INVALID: 422,
    GovernanceErrorCode.PROPOSAL_EMPTY: 422,
    GovernanceErrorCode.REQUIRED_OBLIGATION_REMOVED: 422,
    GovernanceErrorCode.REQUIRED_OBLIGATION_WEAKENED: 422,
    GovernanceErrorCode.PERMANENT_OBLIGATION_ACK_REQUIRED: 409,
    GovernanceErrorCode.SELF_DECISION_REFUSED: 403,
    GovernanceErrorCode.PROPOSAL_TOO_LARGE: 422,
    GovernanceErrorCode.HISTORY_UNAVAILABLE: 503,
    GovernanceErrorCode.GOVERNANCE_NOT_MIGRATED: 503,
    GovernanceErrorCode.DRAFT_NOT_RELEASABLE: 409,
    GovernanceErrorCode.RUN_CONFIRMATION_IN_PROGRESS: 409,
    GovernanceErrorCode.NOTICES_UNACKNOWLEDGED: 409,
    GovernanceErrorCode.ROUTE_RETIRED: 410,
}


class RatchetRule(StrEnum):
    """ADR-017 §2. Removal-type rules map to ``…_REMOVED``; the rest to ``…_WEAKENED``."""

    RR_1 = "RR-1"  # required stage missing
    RR_2 = "RR-2"  # required stage no longer blocks the send
    RR_3 = "RR-3"  # required field missing or optional
    RR_4 = "RR-4"  # required field kind changed
    RR_5 = "RR-5"  # required field normalised label changed
    RR_6 = "RR-6"  # required CHOICE offers an option outside the baseline intersection
    RR_7 = "RR-7"  # required field gained a case_data_key
    RR_8 = "RR-8"  # applicability narrowed (M3; inert until ADR-018)
    RR_9 = "RR-9"  # code-owned mandatory stage or engine order changed
    RR_10 = "RR-10"  # required stage normalised name changed


REMOVAL_RULES = frozenset({RatchetRule.RR_1, RatchetRule.RR_3})


def ratchet_error_code(rule: RatchetRule) -> GovernanceErrorCode:
    if rule in REMOVAL_RULES:
        return GovernanceErrorCode.REQUIRED_OBLIGATION_REMOVED
    return GovernanceErrorCode.REQUIRED_OBLIGATION_WEAKENED


class ProposalState(StrEnum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    STALE = "STALE"


OPEN_PROPOSAL_STATES = frozenset({ProposalState.DRAFT, ProposalState.PENDING_APPROVAL})
TERMINAL_PROPOSAL_STATES = frozenset(set(ProposalState) - OPEN_PROPOSAL_STATES)


class ProposalKind(StrEnum):
    CHANGE = "CHANGE"
    RESTORE_VERSION = "RESTORE_VERSION"  # M2
    RESET_TO_DEFAULT = "RESET_TO_DEFAULT"  # M2
    DEACTIVATE = "DEACTIVATE"  # M2, non-onboarding only
    REACTIVATE = "REACTIVATE"  # M2, non-onboarding only


M1_PROPOSAL_KINDS = frozenset({ProposalKind.CHANGE})


class ProposalOrigin(StrEnum):
    GOVERNED = "GOVERNED"
    PRE_GOVERNANCE_DRAFT = "PRE_GOVERNANCE_DRAFT"  # migrated legacy draft_stages (§1.4)


class VersionOrigin(StrEnum):
    GOVERNED_APPROVAL = "GOVERNED_APPROVAL"
    PRE_GOVERNANCE_DIRECTOR_ACTIVATION = "PRE_GOVERNANCE_DIRECTOR_ACTIVATION"
    EMERGENCY_FALLBACK = "EMERGENCY_FALLBACK"  # M2


class DecisionOutcome(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class PermanentObligationChange(StrEnum):
    NEW_REQUIRED_STAGE = "NEW_REQUIRED_STAGE"
    NEW_REQUIRED_FIELD = "NEW_REQUIRED_FIELD"
    # optional -> required, CHOICE options narrowed, or a case_data_key dropped (CC-2)
    TIGHTENED = "TIGHTENED"


class GovernanceEventKind(StrEnum):
    MIGRATED = "MIGRATED"
    WORKFLOW_CREATED = "WORKFLOW_CREATED"
    PROPOSAL_CREATED = "PROPOSAL_CREATED"
    PROPOSAL_EDITED = "PROPOSAL_EDITED"
    PROPOSAL_SUBMITTED = "PROPOSAL_SUBMITTED"
    PROPOSAL_WITHDRAWN = "PROPOSAL_WITHDRAWN"
    PROPOSAL_APPROVED = "PROPOSAL_APPROVED"
    PROPOSAL_REJECTED = "PROPOSAL_REJECTED"
    PROPOSAL_STALE = "PROPOSAL_STALE"
    VERSION_PUBLISHED = "VERSION_PUBLISHED"
    # M2
    DRAFT_RELEASED = "DRAFT_RELEASED"
    DRAFT_COPIED = "DRAFT_COPIED"
    EMERGENCY_FALLBACK = "EMERGENCY_FALLBACK"
    NOTICE_RAISED = "NOTICE_RAISED"
    NOTICE_ACKNOWLEDGED = "NOTICE_ACKNOWLEDGED"
    DEACTIVATED = "DEACTIVATED"
    REACTIVATED = "REACTIVATED"


class OutboxCollection(StrEnum):
    VERSIONS = COLD_VERSIONS
    PROPOSALS = COLD_PROPOSALS
    EVENTS = COLD_EVENTS


ActorId = Annotated[str, StringConstraints(min_length=1, max_length=64)]
Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
ProposalId = Annotated[str, StringConstraints(pattern=r"^[0-9a-f-]{36}$")]
DecisionReason = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=DECISION_REASON_MIN, max_length=DECISION_REASON_MAX
    ),
]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --- Normalisation and hashing (frozen; the ratchet and content hash depend on them) ---

_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE = re.compile(r"\s+", re.UNICODE)


def normalise_label(value: str) -> str:
    """Case-folded, whitespace collapsed, punctuation removed (ADR-017 §2, RD-1)."""

    text = unicodedata.normalize("NFKC", value).casefold()
    text = _PUNCTUATION.sub("", text)
    return _WHITESPACE.sub(" ", text).strip()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def proposal_content_hash(
    kind: ProposalKind,
    stages: tuple[WorkflowStage, ...],
    restore_target_version: int | None = None,
) -> str:
    """SHA-256 over the canonical JSON of what would be published (ADR-017 §1)."""

    body = {
        "kind": kind.value,
        "restore_target_version": restore_target_version,
        "stages": [stage.model_dump(mode="json") for stage in stages],
    }
    return hashlib.sha256(canonical_json(body)).hexdigest()


def record_content_hash(record: BaseModel) -> str:
    return hashlib.sha256(canonical_json(record.model_dump(mode="json"))).hexdigest()


# --- Obligations and the baseline (ADR-017 §2) ---


class ObligationKey(_Frozen):
    """A required stage (``field_id`` None) or a required field."""

    stage_id: str = Field(min_length=1, max_length=64)
    field_id: str | None = Field(default=None, min_length=1, max_length=64)


class FieldSignature(_Frozen):
    kind: WorkflowFieldKind
    normalised_label: str = Field(min_length=1, max_length=80)
    # The baseline intersection for CHOICE (sorted, normalised); None for other kinds.
    choice_options: tuple[str, ...] | None = None
    has_case_data_key: bool
    # Reserved for ADR-018 (M3). Always None until then; RR-8 is inert.
    applicability: None = None


class BaselineField(_Frozen):
    field_id: str = Field(min_length=1, max_length=64)
    signature: FieldSignature
    representative: WorkflowField  # R1-12; options restricted to the intersection


class BaselineStage(_Frozen):
    stage_id: str = Field(min_length=1, max_length=64)
    normalised_name: str = Field(min_length=1, max_length=80)
    representative_name: str = Field(min_length=1, max_length=80)
    representative_after_node_id: str | None = None
    fields: tuple[BaselineField, ...] = Field(min_length=1)
    first_published_version: int = Field(ge=1)
    last_published_version: int = Field(ge=1)


class RequiredBaseline(_Frozen):
    """The strictest signature ever published per obligation. Only ever becomes stricter."""

    seeded_from_version: int | None = Field(default=None, ge=1)
    updated_at_version: int | None = Field(default=None, ge=1)
    stages: tuple[BaselineStage, ...] = ()


class PermanentObligation(_Frozen):
    key: ObligationKey
    change: PermanentObligationChange
    stage_name: str
    field_label: str | None = None
    detail: str = Field(max_length=240)


# --- Proposals ---


class WorkflowProposal(_Frozen):
    proposal_id: ProposalId
    workflow_id: str = Field(min_length=1, max_length=64)
    kind: ProposalKind = ProposalKind.CHANGE
    state: ProposalState = ProposalState.DRAFT
    origin: ProposalOrigin = ProposalOrigin.GOVERNED
    revision: int = Field(default=1, ge=1)
    base_version: int = Field(ge=NO_ACTIVE_VERSION)
    stages: tuple[WorkflowStage, ...] = Field(default=(), max_length=32)
    restore_target_version: int | None = Field(default=None, ge=1)
    note: ShortText | None = None
    author_id: ActorId | None  # None only for PRE_GOVERNANCE_DRAFT
    legacy_editor: ActorId | None = None
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime
    submitted_at: datetime | None = None
    content_hash: Sha256Hex | None = None  # frozen at submit
    decided_at: datetime | None = None
    decided_by: ActorId | None = None
    decision_reason: DecisionReason | None = None
    acknowledged_permanent_obligations: tuple[ObligationKey, ...] = ()
    published_version: int | None = Field(default=None, ge=1)
    stale_by_version: int | None = Field(default=None, ge=1)
    withdrawn_at: datetime | None = None
    released_by: ActorId | None = None  # M2
    release_reason: ShortText | None = None  # M2
    copied_from: ProposalId | None = None  # M2
    related_policy_proposal_ids: tuple[str, ...] = Field(
        default=(), max_length=MAX_RELATED_POLICY_PROPOSALS
    )

    @model_validator(mode="after")
    def _consistent(self) -> WorkflowProposal:
        # Third self-decision check (role and service are the first two).
        if self.decided_by is not None and self.decided_by == self.author_id:
            raise ValueError("WORKFLOW_SELF_DECISION_REFUSED")
        if self.origin == ProposalOrigin.PRE_GOVERNANCE_DRAFT:
            if self.author_id is not None or self.state != ProposalState.WITHDRAWN:
                raise ValueError("a legacy draft is authorless and WITHDRAWN")
        elif self.author_id is None:
            raise ValueError("a governed proposal has an author")
        submitted = self.state in {
            ProposalState.PENDING_APPROVAL,
            ProposalState.APPROVED,
            ProposalState.REJECTED,
        }
        if submitted and (self.content_hash is None or self.submitted_at is None):
            raise ValueError("a submitted proposal carries its content hash")
        decided = self.state in {ProposalState.APPROVED, ProposalState.REJECTED}
        if decided != (self.decided_by is not None):
            raise ValueError("only decided proposals carry a decider")
        if decided and (self.decided_at is None or self.decision_reason is None):
            raise ValueError("a decision carries its time and reason")
        # An approved DEACTIVATE publishes nothing (ADR-017 §4; CC-5); every other approval does.
        publishes = self.state == ProposalState.APPROVED and self.kind != ProposalKind.DEACTIVATE
        if publishes != (self.published_version is not None):
            raise ValueError("only an approved proposal publishes a version")
        if self.state == ProposalState.STALE and self.stale_by_version is None:
            raise ValueError("a stale proposal names the publication that superseded it")
        if self.kind not in {ProposalKind.RESTORE_VERSION} and self.restore_target_version:
            raise ValueError("only RESTORE_VERSION names a target version")
        return self


class DecidedProposalEntry(_Frozen):
    """Hot summary of a terminal proposal.

    ``record`` keeps the complete proposal until its cold copy is durably acknowledged
    (``archived`` True); only then may it be dropped to a summary. A summary without an
    acknowledged cold copy is an integrity failure.
    """

    proposal_id: ProposalId
    kind: ProposalKind
    state: ProposalState
    origin: ProposalOrigin
    author_id: ActorId | None
    decided_by: ActorId | None
    decided_at: datetime | None
    ended_at: datetime
    published_version: int | None
    content_hash: Sha256Hex | None
    record_hash: Sha256Hex  # hash of the complete record, as archived
    archived: bool = False
    record: WorkflowProposal | None = None

    @model_validator(mode="after")
    def _complete_until_archived(self) -> DecidedProposalEntry:
        if self.state not in TERMINAL_PROPOSAL_STATES:
            raise ValueError("only terminal proposals are decided")
        if not self.archived and self.record is None:
            raise ValueError("the full record stays hot until its cold copy is acknowledged")
        return self


class VersionProvenance(_Frozen):
    version: int = Field(ge=1)
    origin: VersionOrigin
    author_id: ActorId | None  # None for legacy
    approved_by: ActorId | None  # None for legacy and emergency fallback
    proposal_id: ProposalId | None
    activated_by: ActorId | None = None  # legacy D-123 activator
    published_at: datetime
    note: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def _honest(self) -> VersionProvenance:
        if self.origin == VersionOrigin.PRE_GOVERNANCE_DIRECTOR_ACTIVATION and (
            self.approved_by is not None or self.author_id is not None
        ):
            raise ValueError("a legacy version is never shown as approved")
        if self.origin == VersionOrigin.GOVERNED_APPROVAL and (
            self.approved_by is None or self.author_id is None or self.proposal_id is None
        ):
            raise ValueError("a governed version names its author, approver and proposal")
        if self.approved_by is not None and self.approved_by == self.author_id:
            raise ValueError("WORKFLOW_SELF_DECISION_REFUSED")
        return self


class GovernanceEvent(_Frozen):
    sequence: int = Field(ge=1)
    occurred_at: datetime
    actor_id: ActorId | None
    kind: GovernanceEventKind
    proposal_id: ProposalId | None = None
    version: int | None = Field(default=None, ge=1)
    summary: str = Field(min_length=1, max_length=160)
    archived: bool = False


class GovernanceNotice(_Frozen):
    """M2: raised by emergency fallback; stays hot until an HR user acknowledges it."""

    notice_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    kind: GovernanceEventKind = GovernanceEventKind.EMERGENCY_FALLBACK
    raised_at: datetime
    raised_by: ActorId
    version: int = Field(ge=1)
    reason: DecisionReason
    acknowledged_by: ActorId | None = None
    acknowledged_at: datetime | None = None


class OutboxEntry(_Frozen):
    """A reference to a hot record awaiting its durably acknowledged cold copy."""

    collection: OutboxCollection
    logical_id: str = Field(min_length=1, max_length=160)
    content_hash: Sha256Hex
    attempt: int = Field(default=0, ge=0)


class MigrationMarker(_Frozen):
    migrated_at: datetime
    tool_version: str = Field(min_length=1, max_length=32)
    legacy_versions: int = Field(ge=0)
    legacy_draft_converted: bool
    baseline_seeded_from_version: int | None = Field(default=None, ge=1)


class ColdRecord(_Frozen):
    """The envelope of one insert-only cold record (ADR-017 §5, R3-5)."""

    logical_id: str = Field(min_length=1, max_length=160)
    attempt: int = Field(ge=0)
    content_hash: Sha256Hex
    workflow_id: str = Field(min_length=1, max_length=64)
    archived_at: datetime
    archive_confirmations: int = Field(default=0, ge=0)
    record: dict[str, Any]

    @property
    def document_id(self) -> str:
        return f"{self.logical_id}#{self.attempt}"


def version_logical_id(workflow_id: str, version: int) -> str:
    return f"{workflow_id}:{version}"


def event_logical_id(workflow_id: str, sequence: int) -> str:
    return f"{workflow_id}:{sequence}"


class WorkflowGovernanceState(_Frozen):
    """The decoded top-level governance fields of one definition document."""

    migration_marker: MigrationMarker | None = None
    required_baseline: RequiredBaseline = RequiredBaseline()
    open_proposal: WorkflowProposal | None = None
    decided_proposals: tuple[DecidedProposalEntry, ...] = ()
    governance_events: tuple[GovernanceEvent, ...] = ()
    notices: tuple[GovernanceNotice, ...] = ()
    outbox: tuple[OutboxEntry, ...] = Field(default=(), max_length=MAX_OUTBOX_RECORDS)
    version_provenance: tuple[VersionProvenance, ...] = ()
    governance_sequence: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _open_is_open(self) -> WorkflowGovernanceState:
        if self.open_proposal is not None and self.open_proposal.state not in (
            OPEN_PROPOSAL_STATES
        ):
            raise ValueError("the open proposal slot holds only DRAFT or PENDING_APPROVAL")
        return self

    @property
    def migrated(self) -> bool:
        return self.migration_marker is not None
