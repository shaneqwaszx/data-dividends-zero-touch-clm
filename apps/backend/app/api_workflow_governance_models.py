"""Frozen request and response models for the workflow governance routes (C0, ADR-017 §6).

Routes (all ``ACTOR_ONLY`` in ``ROUTE_POLICIES``; reauthorized inside the definition lock):

M1 (HR, ``POLICY_MUTATE``):
    POST /api/workflows/{wid}/proposals                       CreateProposalRequest
    PUT  /api/workflows/{wid}/proposals/{pid}                 UpdateProposalRequest
    POST /api/workflows/{wid}/proposals/{pid}/validate        ValidateProposalRequest
    POST /api/workflows/{wid}/proposals/{pid}/simulate        SimulateProposalRequest
    POST /api/workflows/{wid}/proposals/{pid}/submit          SubmitProposalRequest
    POST /api/workflows/{wid}/proposals/{pid}/withdraw        WithdrawProposalRequest
    GET  /api/workflows/simulation-scenarios
M1 (Director, ``POLICY_APPROVE``):
    GET  /api/workflow-approvals
    GET  /api/workflows/{wid}/proposals/{pid}/comparison
    POST /api/workflows/{wid}/proposals/{pid}/decision        DecisionRequest
M1 (HR and Director, read-only): GET /api/workflows/{wid} adds ``governance``.
Retired: POST …/activate (PR-4), PUT …/draft (PR-5); both return 410 WORKFLOW_ROUTE_RETIRED.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.workflow_governance import (
    DecisionOutcome,
    DecisionReason,
    GovernanceEvent,
    GovernanceNotice,
    ObligationKey,
    PermanentObligation,
    ProposalKind,
    ProposalOrigin,
    ProposalState,
    RatchetRule,
    ShortText,
    VersionProvenance,
    WorkflowProposal,
)
from app.domain.workflows import WorkflowField, WorkflowStage, WorkflowVersion


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --- Requests ---


class CreateProposalRequest(_Contract):
    kind: ProposalKind = ProposalKind.CHANGE  # M1 accepts CHANGE only (else 422 KIND)
    expected_workflow_revision: int = Field(ge=1)
    # Omitted: start from the active version's stages (or empty when nothing is active).
    stages: tuple[WorkflowStage, ...] | None = Field(default=None, max_length=32)
    restore_target_version: int | None = Field(default=None, ge=1)  # M2
    note: ShortText | None = None


class UpdateProposalRequest(_Contract):
    expected_workflow_revision: int = Field(ge=1)
    expected_proposal_revision: int = Field(ge=1)
    stages: tuple[WorkflowStage, ...] = Field(max_length=32)
    note: ShortText | None = None


class ValidateProposalRequest(_Contract):
    """Read-only. ``stages`` validates unsaved editor content; omitted, the stored content."""

    stages: tuple[WorkflowStage, ...] | None = Field(default=None, max_length=32)


class SimulateProposalRequest(_Contract):
    """Read-only, synthetic only. Empty ``scenario_ids`` runs the whole catalogue."""

    stages: tuple[WorkflowStage, ...] | None = Field(default=None, max_length=32)
    scenario_ids: tuple[str, ...] = Field(default=(), max_length=8)


class SubmitProposalRequest(_Contract):
    expected_workflow_revision: int = Field(ge=1)
    expected_proposal_revision: int = Field(ge=1)
    # The hash the author validated; a mismatch is 409 WORKFLOW_PROPOSAL_CONTENT_CHANGED.
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class WithdrawProposalRequest(_Contract):
    expected_workflow_revision: int = Field(ge=1)
    expected_proposal_revision: int = Field(ge=1)


class DecisionRequest(_Contract):
    outcome: DecisionOutcome
    reason: DecisionReason
    expected_workflow_revision: int = Field(ge=1)
    expected_proposal_revision: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    # APPROVE: exactly the comparison's permanent-obligation set (order-insensitive).
    # REJECT: must be empty.
    acknowledged_permanent_obligations: tuple[ObligationKey, ...] = Field(
        default=(), max_length=1024
    )


# --- Validation and simulation ---


class ValidationIssue(_Contract):
    code: str  # a GovernanceErrorCode value or an existing WORKFLOW_* structure code
    rule: RatchetRule | None = None
    stage_id: str | None = None
    field_id: str | None = None
    message: str = Field(max_length=240)


class ValidationReport(_Contract):
    valid: bool
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    encoded_bytes: int = Field(ge=0)
    max_encoded_bytes: int = Field(ge=1)
    base_version: int = Field(ge=0)
    active_version: int = Field(ge=0)
    issues: tuple[ValidationIssue, ...] = ()
    permanent_obligations: tuple[PermanentObligation, ...] = ()


class SimulationScenario(_Contract):
    scenario_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    label: str = Field(max_length=80)
    description: str = Field(max_length=240)
    legal_form: str = Field(max_length=64)  # synthetic RegistryLegalForm label only
    synthetic: Literal[True] = True


class SimulatedStep(_Contract):
    node_id: str  # a locked onboarding node id or an added stage_id
    name: str
    added: bool
    blocks_send: bool
    required_field_labels: tuple[str, ...] = ()


class SimulationOutcome(_Contract):
    scenario: SimulationScenario
    steps: tuple[SimulatedStep, ...]
    held_before_send: bool  # an added required stage would hold the send until confirmed
    summary: str = Field(max_length=240)


class SimulationResult(_Contract):
    synthetic: Literal[True] = True
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcomes: tuple[SimulationOutcome, ...]


# --- Proposal views ---


class ProposalResponse(_Contract):
    proposal_id: str
    workflow_id: str
    kind: ProposalKind
    state: ProposalState
    origin: ProposalOrigin
    revision: int
    base_version: int
    stages: tuple[WorkflowStage, ...]
    note: str | None
    author_id: str | None
    legacy_editor: str | None
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime
    submitted_at: datetime | None
    content_hash: str | None
    decided_at: datetime | None
    decided_by: str | None
    decision_reason: str | None
    published_version: int | None
    stale_by_version: int | None
    # Server-computed for the caller (never trusted from the client):
    can_edit: bool
    can_submit: bool
    can_withdraw: bool
    can_decide: bool

    @classmethod
    def from_domain(
        cls,
        item: WorkflowProposal,
        *,
        can_edit: bool,
        can_submit: bool,
        can_withdraw: bool,
        can_decide: bool,
    ) -> ProposalResponse:
        return cls(
            proposal_id=item.proposal_id,
            workflow_id=item.workflow_id,
            kind=item.kind,
            state=item.state,
            origin=item.origin,
            revision=item.revision,
            base_version=item.base_version,
            stages=item.stages,
            note=item.note,
            author_id=item.author_id,
            legacy_editor=item.legacy_editor,
            created_at=item.created_at,
            updated_at=item.updated_at,
            last_activity_at=item.last_activity_at,
            submitted_at=item.submitted_at,
            content_hash=item.content_hash,
            decided_at=item.decided_at,
            decided_by=item.decided_by,
            decision_reason=item.decision_reason,
            published_version=item.published_version,
            stale_by_version=item.stale_by_version,
            can_edit=can_edit,
            can_submit=can_submit,
            can_withdraw=can_withdraw,
            can_decide=can_decide,
        )


class DecidedProposalSummaryResponse(_Contract):
    proposal_id: str
    kind: ProposalKind
    state: ProposalState
    origin: ProposalOrigin
    author_id: str | None
    decided_by: str | None
    decided_at: datetime | None
    ended_at: datetime
    published_version: int | None


class BaselineSummary(_Contract):
    seeded_from_version: int | None
    updated_at_version: int | None
    required_stages: int = Field(ge=0)
    required_fields: int = Field(ge=0)


class WorkflowGovernanceView(_Contract):
    """Added to ``GET /api/workflows/{wid}`` (and the list) once the marker exists."""

    migrated: bool
    latest_version: int = Field(ge=0)
    open_proposal: ProposalResponse | None
    decided_proposals: tuple[DecidedProposalSummaryResponse, ...]
    version_provenance: tuple[VersionProvenance, ...]
    baseline: BaselineSummary
    recent_events: tuple[GovernanceEvent, ...]
    unacknowledged_notices: tuple[GovernanceNotice, ...]  # M2; empty in M1
    can_create_proposal: bool


# --- Director views ---


class ChangeCounts(_Contract):
    stages_added: int = Field(ge=0)
    stages_removed: int = Field(ge=0)
    stages_changed: int = Field(ge=0)
    fields_added: int = Field(ge=0)
    fields_removed: int = Field(ge=0)
    fields_changed: int = Field(ge=0)


class ApprovalInboxItem(_Contract):
    workflow_id: str
    workflow_name: str
    use_case: str
    is_onboarding: bool
    workflow_revision: int
    proposal: ProposalResponse
    active_version: int = Field(ge=0)
    changes: ChangeCounts
    permanent_obligation_count: int = Field(ge=0)


class ApprovalInboxResponse(_Contract):
    items: tuple[ApprovalInboxItem, ...]


FieldChange = Literal["ADDED", "REMOVED", "CHANGED", "UNCHANGED"]


class FieldDiff(_Contract):
    field_id: str
    change: FieldChange
    before: WorkflowField | None
    after: WorkflowField | None


class StageDiff(_Contract):
    stage_id: str
    change: FieldChange
    name_before: str | None
    name_after: str | None
    after_node_id_before: str | None
    after_node_id_after: str | None
    blocks_send_before: bool
    blocks_send_after: bool
    fields: tuple[FieldDiff, ...]


class AffectedCases(_Contract):
    """Director only. Counts from ledger records and runs, never from case content."""

    open_runs_on_active_version: int = Field(ge=0)
    counted_at: datetime


class ComparisonResponse(_Contract):
    workflow_id: str
    workflow_name: str
    is_onboarding: bool
    workflow_revision: int
    proposal: ProposalResponse
    active_version: WorkflowVersion | None
    active_provenance: VersionProvenance | None
    stages: tuple[StageDiff, ...]
    locked_stages: tuple[tuple[str, str], ...]  # (node_id, label), onboarding only
    validation: ValidationReport  # re-run now against the active version and baseline
    permanent_obligations: tuple[PermanentObligation, ...]
    permanent_obligation_warning: str
    affected_cases: AffectedCases


class PublicationReport(_Contract):
    """After an approval commits: from case ledger records (§1.1), never the D3 counter."""

    published_version: int = Field(ge=1)
    cases_past_first_write_under_earlier_version: int = Field(ge=0)
    cases_authorised_under_earlier_version: int = Field(ge=0)
    cases_possibly_authorised: int = Field(ge=0)  # live TENTATIVE claims (R1-4)
    counted_at: datetime


class DecisionResponse(_Contract):
    proposal: ProposalResponse
    workflow_revision: int
    active_version: int = Field(ge=0)
    published_version: int | None
    provenance: VersionProvenance | None
    publication_report: PublicationReport | None


class GovernanceErrorBody(_Contract):
    """``HTTPException.detail`` for every governance error (same shape as existing routes)."""

    code: str
    message: str = Field(max_length=240)
    rule: RatchetRule | None = None
    issues: tuple[ValidationIssue, ...] = ()


# --- M2 contract addendum (CC-4): recovery and administration (ADR-017 §1.2, §4, §5) ---
#
# M2 routes (all ACTOR_ONLY; reauthorized inside the definition lock):
#   POST /api/workflows/{wid}/proposals  kind RESTORE_VERSION (restore_target_version) or
#        RESET_TO_DEFAULT (HR; the published content is the SAFE TARGET: base ∪ required_baseline),
#        DEACTIVATE / REACTIVATE (HR; non-onboarding only; REACTIVATE carries full stages)
#        — each is decided through the existing decision route by one Director.
#   POST /api/workflows/{wid}/emergency-fallback        EmergencyFallbackRequest  (Director alone)
#   POST /api/workflows/{wid}/proposals/{pid}/release   ReleaseDraftRequest       (HR, not author)
#   POST /api/workflows/{wid}/proposals/{pid}/copy      CopyProposalRequest       (HR)
#   GET  /api/workflows/{wid}/versions/{n}              WorkflowVersionResponse   (HR, Director)
#   GET  /api/workflows/notices                         NoticeListResponse        (HR, Director)
#   POST /api/workflows/notices/{notice_id}/acknowledge AcknowledgeNoticeRequest  (HR)


class EmergencyFallbackRequest(_Contract):
    """Director alone, mandatory reason. Publishes the safe target (origin EMERGENCY_FALLBACK)."""

    reason: DecisionReason
    expected_workflow_revision: int = Field(ge=1)
    target: Literal["VERSION", "DEFAULT"]
    target_version: int | None = Field(default=None, ge=1)  # required when target == "VERSION"


class EmergencyFallbackResponse(_Contract):
    workflow_revision: int
    active_version: int = Field(ge=1)
    published_version: int = Field(ge=1)
    provenance: VersionProvenance
    notice: GovernanceNotice
    staled_proposal_ids: tuple[str, ...] = ()
    publication_report: PublicationReport | None = None


class ReleaseDraftRequest(_Contract):
    """Any HR user except the author, after 14 days without activity or when the author is gone."""

    reason: ShortText
    expected_workflow_revision: int = Field(ge=1)
    expected_proposal_revision: int = Field(ge=1)


class CopyProposalRequest(_Contract):
    """A new DRAFT authored by the copier, with copied_from; authorship is never transferred."""

    expected_workflow_revision: int = Field(ge=1)
    note: ShortText | None = None


class WorkflowVersionResponse(_Contract):
    """One published version, hot or cold (``get_version``)."""

    workflow_id: str
    version: WorkflowVersion
    provenance: VersionProvenance | None
    is_active: bool


class NoticeItem(_Contract):
    workflow_id: str
    workflow_name: str
    workflow_revision: int
    notice: GovernanceNotice


class NoticeListResponse(_Contract):
    items: tuple[NoticeItem, ...]


class AcknowledgeNoticeRequest(_Contract):
    workflow_id: str = Field(min_length=1, max_length=64)
    expected_workflow_revision: int = Field(ge=1)
