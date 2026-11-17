"""Single owner of workflow governance mutations (ADR-017 section 1, D-135; contract C0).

HR (``POLICY_MUTATE``) authors proposals; one Director (``POLICY_APPROVE``) decides. Every
mutation runs inside the one definition lock owned by ``WorkflowManagementService``: the
actor is reauthorized inside the lock, the outbox is drained first, the change is ONE
governance compare-and-set (revision and ``write_nonce``), and the outbox is drained again
after the commit. Runs, answers, confirmations and the send check stay with
``WorkflowManagementService``; nothing here reads case content, calls a provider or
touches the dispatch fence. Simulation is synthetic only.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager, contextmanager, nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.api_workflow_governance_models import (
    AcknowledgeNoticeRequest,
    AffectedCases,
    ApprovalInboxItem,
    ApprovalInboxResponse,
    BaselineSummary,
    ComparisonResponse,
    CopyProposalRequest,
    CreateProposalRequest,
    DecidedProposalSummaryResponse,
    DecisionRequest,
    DecisionResponse,
    EmergencyFallbackRequest,
    EmergencyFallbackResponse,
    GovernanceErrorBody,
    NoticeItem,
    NoticeListResponse,
    ProposalResponse,
    PublicationReport,
    ReleaseDraftRequest,
    SimulateProposalRequest,
    SimulationResult,
    SimulationScenario,
    SubmitProposalRequest,
    UpdateProposalRequest,
    ValidateProposalRequest,
    ValidationIssue,
    ValidationReport,
    WithdrawProposalRequest,
    WorkflowGovernanceView,
    WorkflowVersionResponse,
)
from app.domain.access import ROLE_CAPABILITIES, AuthenticatedActor, Capability
from app.domain.target_submission import GoldTierExecutionLedgerEntry, WorkflowDispatchState
from app.domain.workflow_governance import (
    DRAFT_RELEASE_AFTER_DAYS,
    GOVERNANCE_ERROR_STATUS,
    MAX_ENCODED_VERSION_BYTES,
    MAX_UNACKNOWLEDGED_NOTICES,
    NO_ACTIVE_VERSION,
    PERMANENT_OBLIGATION_WARNING,
    DecisionOutcome,
    GovernanceErrorCode,
    GovernanceEvent,
    GovernanceEventKind,
    GovernanceNotice,
    OutboxEntry,
    ProposalKind,
    ProposalOrigin,
    ProposalState,
    RatchetRule,
    VersionOrigin,
    VersionProvenance,
    WorkflowGovernanceState,
    WorkflowProposal,
    proposal_content_hash,
)
from app.domain.workflows import (
    ONBOARDING_LOCKED_STAGES,
    WorkflowDefinition,
    WorkflowStage,
    WorkflowVersion,
)
from app.persistence.errors import PersistenceConflictError, PersistenceError
from app.persistence.workflow_governance_store import (
    GovernedDefinition,
    WorkflowGovernanceNotMigratedError,
    WorkflowHistoryUnavailableError,
    decided_entry,
    outbox_for_event,
    outbox_for_proposal,
    outbox_for_version,
)
from app.services.target_execution_repository import has_write_marker
from app.services.workflow_management import (
    ConfirmationGate,
    WorkflowConflictError,
    WorkflowForbiddenError,
    WorkflowNotFoundError,
    confirmation_gate_for,
)
from app.services.workflow_ratchet import (
    SafeTargetError,
    advance_baseline,
    change_counts,
    permanent_obligations,
    safe_target,
    seed_baseline,
    stage_diff,
    validate_candidate,
)
from app.services.workflow_repository import WorkflowGovernanceRepository, WorkflowRunRepository
from app.services.workflow_simulation import SimulationInputError, scenarios, simulate

LOGGER = logging.getLogger(__name__)
RECENT_EVENTS = 20
NOT_MIGRATED_FINDING = "P2_1_NOT_MIGRATED"
STRUCTURE_ERROR_STATUS = 422

Reauthorize = Callable[[], AuthenticatedActor]
# Existing read-only case ledger access: (case id, that case's ledger entries) per case.
LedgerReader = Callable[[], Iterable[tuple[UUID, Sequence[GoldTierExecutionLedgerEntry]]]]
# An event to append: (kind, actor, proposal or None, version or None).
EventSpec = tuple[GovernanceEventKind, AuthenticatedActor, "WorkflowProposal | None", int | None]

# M2 (CC-4): the backend computes the content of these kinds; client stages are refused.
COMPUTED_KINDS = frozenset(
    {ProposalKind.RESTORE_VERSION, ProposalKind.RESET_TO_DEFAULT, ProposalKind.DEACTIVATE}
)
RECOVERY_KINDS = frozenset({ProposalKind.RESTORE_VERSION, ProposalKind.RESET_TO_DEFAULT})
LIFECYCLE_KINDS = frozenset({ProposalKind.DEACTIVATE, ProposalKind.REACTIVATE})

_MESSAGES: dict[GovernanceErrorCode, str] = {
    GovernanceErrorCode.PROPOSAL_OPEN: "This workflow already has an open proposal.",
    GovernanceErrorCode.PROPOSAL_STALE: (
        "Another version was published first. Start a new proposal from the active version."
    ),
    GovernanceErrorCode.PROPOSAL_NOT_FOUND: "The proposal was not found.",
    GovernanceErrorCode.PROPOSAL_STATE_INVALID: "The proposal is not in a state that allows this.",
    GovernanceErrorCode.PROPOSAL_CONTENT_CHANGED: (
        "The proposal content changed. Validate it again before continuing."
    ),
    GovernanceErrorCode.PROPOSAL_KIND_NOT_AVAILABLE: "This kind of proposal is not available yet.",
    GovernanceErrorCode.PROPOSAL_INVALID: "The proposal is not valid.",
    GovernanceErrorCode.PERMANENT_OBLIGATION_ACK_REQUIRED: (
        "Acknowledge exactly the permanent obligations this proposal adds."
    ),
    GovernanceErrorCode.SELF_DECISION_REFUSED: "You cannot decide a proposal you wrote.",
    GovernanceErrorCode.HISTORY_UNAVAILABLE: "Workflow history is unavailable right now.",
    GovernanceErrorCode.GOVERNANCE_NOT_MIGRATED: (
        "Workflow approval governance is not available on this workflow yet."
    ),
    GovernanceErrorCode.ROUTE_RETIRED: "This action has been retired.",
    GovernanceErrorCode.DRAFT_NOT_RELEASABLE: (
        "This draft can be released only after 14 days without activity."
    ),
    GovernanceErrorCode.RUN_CONFIRMATION_IN_PROGRESS: (
        "A stage confirmation is in progress on this workflow. Try again shortly."
    ),
    GovernanceErrorCode.NOTICES_UNACKNOWLEDGED: (
        "Too many governance notices are unacknowledged. HR must acknowledge them first."
    ),
}


class WorkflowGovernanceError(Exception):
    """A governance refusal, projected as ``GovernanceErrorBody`` with its HTTP status."""

    def __init__(
        self,
        code: GovernanceErrorCode | str,
        message: str | None = None,
        *,
        rule: RatchetRule | None = None,
        issues: Sequence[ValidationIssue] = (),
    ) -> None:
        value = code.value if isinstance(code, GovernanceErrorCode) else code
        super().__init__(value)
        self.code = value
        known = GovernanceErrorCode(value) if value in GovernanceErrorCode else None
        self.status = (
            GOVERNANCE_ERROR_STATUS[known] if known is not None else STRUCTURE_ERROR_STATUS
        )
        self.public_message = (
            message
            or (_MESSAGES.get(known) if known is not None else None)
            or "The proposal is not valid."
        )[:240]
        self.rule = rule
        self.issues = tuple(issues)

    def body(self) -> GovernanceErrorBody:
        return GovernanceErrorBody(
            code=self.code, message=self.public_message, rule=self.rule, issues=self.issues
        )


@dataclass(frozen=True)
class GovernanceStartup:
    """Startup outcome (ADR-017 3.4, 3.5): a failure makes governance unavailable (503)
    without failing reads or the rest of the application."""

    available: bool
    blocked: Mapping[str, str]  # workflow id -> verification reason (not "not migrated")


def start_governance(
    repository: WorkflowGovernanceRepository,
    *,
    memory_mode: bool,
    now: datetime | None = None,
) -> GovernanceStartup:
    """Run after provisioning: memory-mode migration, ``drain_all``, then verification.

    MEMORY MODE ONLY migrates (a process-local store has no legacy persisted data). Mongo
    mode never auto-migrates: the reviewed dry-run tool and an owner-approved window do.
    """

    moment = now or datetime.now(UTC)
    try:
        if memory_mode:
            migrate = getattr(repository, "migrate_to_governance", None)
            if callable(migrate):
                migrate(seed_baseline, now=moment)
        repository.drain_all(now=moment)
        findings = repository.verify_governance_state()
    except Exception:  # noqa: BLE001 - any startup failure is unavailability, never a guess
        LOGGER.warning("workflow governance unavailable at startup")
        return GovernanceStartup(available=False, blocked={})
    blocked = {
        workflow_id: reason for workflow_id, reason in findings if reason != NOT_MIGRATED_FINDING
    }
    if blocked:
        LOGGER.warning(
            "workflow governance blocked for some workflows",
            extra={"workflows": sorted(blocked)},
        )
    return GovernanceStartup(available=True, blocked=blocked)


@dataclass(frozen=True)
class _Write:
    definition: WorkflowDefinition
    governance: WorkflowGovernanceState
    publish_version: int | None = None
    # A non-publication deactivation: active_version 0, latest and baseline kept (CC-5).
    deactivate: bool = False


def _has(actor: AuthenticatedActor, capability: Capability) -> bool:
    return capability in ROLE_CAPABILITIES[actor.profile.role]


def _fields(model: Any) -> dict[str, Any]:
    return {name: getattr(model, name) for name in type(model).model_fields}


class WorkflowGovernanceService:
    def __init__(
        self,
        *,
        repository: WorkflowGovernanceRepository,
        runs: WorkflowRunRepository,
        lock: RLock,
        ledger: LedgerReader | None = None,
        startup: GovernanceStartup | None = None,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
        confirmation_gate: ConfirmationGate | None = None,
    ) -> None:
        self._repository = repository
        self._runs = runs
        self._lock = lock
        # Shared with ``WorkflowManagementService`` through the same definition lock.
        self._gate = confirmation_gate or confirmation_gate_for(lock)
        self._ledger = ledger
        self._startup = startup or GovernanceStartup(available=True, blocked={})
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4

    # --- Reads -------------------------------------------------------------------------

    def list_workflows(
        self, actor: AuthenticatedActor
    ) -> list[tuple[WorkflowDefinition, WorkflowGovernanceView | None]]:
        self._require_reader(actor)
        return [
            (item.definition, self._view(actor, item)) for item in self._repository.list_governed()
        ]

    def get_workflow(
        self, actor: AuthenticatedActor, workflow_id: str
    ) -> tuple[WorkflowDefinition, WorkflowGovernanceView | None]:
        self._require_reader(actor)
        governed = self._load(workflow_id)
        return governed.definition, self._view(actor, governed)

    def simulation_scenarios(self, actor: AuthenticatedActor) -> tuple[SimulationScenario, ...]:
        self._require(actor, Capability.POLICY_MUTATE)
        return scenarios()

    def validate(
        self,
        actor: AuthenticatedActor,
        workflow_id: str,
        proposal_id: str,
        request: ValidateProposalRequest,
    ) -> ValidationReport:
        """Read-only: structure, budget and the ratchet against the active version and
        the required baseline. Unsaved editor content may be validated."""

        self._require(actor, Capability.POLICY_MUTATE)
        governed = self._migrated(workflow_id)
        proposal = self._open(governed, proposal_id)
        _refuse_client_stages(proposal.kind, request.stages)
        stages = proposal.stages if request.stages is None else request.stages
        return self._report(governed, proposal, stages)

    def simulate(
        self,
        actor: AuthenticatedActor,
        workflow_id: str,
        proposal_id: str,
        request: SimulateProposalRequest,
    ) -> SimulationResult:
        self._require(actor, Capability.POLICY_MUTATE)
        governed = self._migrated(workflow_id)
        proposal = self._open(governed, proposal_id)
        _refuse_client_stages(proposal.kind, request.stages)
        stages = proposal.stages if request.stages is None else request.stages
        try:
            return simulate(
                stages,
                is_onboarding=governed.definition.is_onboarding,
                scenario_ids=request.scenario_ids,
            )
        except SimulationInputError as error:
            raise WorkflowGovernanceError(
                GovernanceErrorCode.PROPOSAL_INVALID, error.public_message
            ) from None

    def approvals_inbox(self, actor: AuthenticatedActor) -> ApprovalInboxResponse:
        self._require(actor, Capability.POLICY_APPROVE)
        items: list[ApprovalInboxItem] = []
        for governed in self._repository.list_governed():
            proposal = governed.governance.open_proposal
            if proposal is None or proposal.state != ProposalState.PENDING_APPROVAL:
                continue
            definition = governed.definition
            try:
                number, active = self._active(governed)
            except (WorkflowGovernanceError, PersistenceError) as error:
                # One unreadable workflow never fails the inbox; its comparison and
                # decision still fail closed (503) on their own.
                LOGGER.warning(
                    "approval inbox item unavailable",
                    extra={"workflow_id": definition.workflow_id, "reason": type(error).__name__},
                )
                continue
            items.append(
                ApprovalInboxItem(
                    workflow_id=definition.workflow_id,
                    workflow_name=definition.name,
                    use_case=definition.use_case,
                    is_onboarding=definition.is_onboarding,
                    workflow_revision=definition.revision,
                    proposal=self._response(actor, proposal),
                    active_version=number,
                    changes=change_counts(
                        stage_diff(active.stages if active else (), proposal.stages)
                    ),
                    permanent_obligation_count=len(
                        permanent_obligations(
                            proposal.stages,
                            active=active,
                            baseline=governed.governance.required_baseline,
                        )
                    ),
                )
            )
        return ApprovalInboxResponse(items=tuple(items))

    def comparison(
        self, actor: AuthenticatedActor, workflow_id: str, proposal_id: str
    ) -> ComparisonResponse:
        self._require(actor, Capability.POLICY_APPROVE)
        governed = self._migrated(workflow_id)
        proposal = self._open(governed, proposal_id)
        if proposal.state != ProposalState.PENDING_APPROVAL:
            raise WorkflowGovernanceError(GovernanceErrorCode.PROPOSAL_STATE_INVALID)
        number, active = self._active(governed)
        definition = governed.definition
        report = self._report(governed, proposal, proposal.stages)
        provenance = next(
            (item for item in governed.governance.version_provenance if item.version == number),
            None,
        )
        open_runs = sum(
            1
            for run in self._runs.list_for_workflow(workflow_id)
            if number and run.workflow_version == number and not run.is_complete
        )
        return ComparisonResponse(
            workflow_id=definition.workflow_id,
            workflow_name=definition.name,
            is_onboarding=definition.is_onboarding,
            workflow_revision=definition.revision,
            proposal=self._response(actor, proposal),
            active_version=active,
            active_provenance=provenance,
            stages=stage_diff(active.stages if active else (), proposal.stages),
            locked_stages=ONBOARDING_LOCKED_STAGES if definition.is_onboarding else (),
            validation=report,
            permanent_obligations=report.permanent_obligations,
            permanent_obligation_warning=PERMANENT_OBLIGATION_WARNING,
            affected_cases=AffectedCases(
                open_runs_on_active_version=open_runs, counted_at=self._clock()
            ),
        )

    # --- HR mutations ------------------------------------------------------------------

    def create_proposal(
        self, reauthorize: Reauthorize, workflow_id: str, request: CreateProposalRequest
    ) -> ProposalResponse:
        def change(actor: AuthenticatedActor, governed: GovernedDefinition, now: datetime) -> Any:
            self._expect_workflow(governed, request.expected_workflow_revision)
            state = governed.governance
            if state.open_proposal is not None:
                raise WorkflowGovernanceError(GovernanceErrorCode.PROPOSAL_OPEN)
            number, _active = self._active(governed)
            stages = self._initial_stages(governed, request)
            proposal = _proposal(
                {
                    "proposal_id": str(self._uuid_factory()),
                    "workflow_id": governed.definition.workflow_id,
                    "kind": request.kind,
                    "base_version": number,
                    "stages": stages,
                    "restore_target_version": request.restore_target_version,
                    "note": request.note,
                    "author_id": actor.profile.user_id,
                    "created_at": now,
                    "updated_at": now,
                    "last_activity_at": now,
                }
            )
            return proposal, self._write(
                governed,
                now,
                open_proposal=proposal,
                events=((GovernanceEventKind.PROPOSAL_CREATED, actor, proposal, None),),
            )

        actor, proposal = self._mutate(reauthorize, workflow_id, Capability.POLICY_MUTATE, change)
        return self._response(actor, proposal)

    def update_proposal(
        self,
        reauthorize: Reauthorize,
        workflow_id: str,
        proposal_id: str,
        request: UpdateProposalRequest,
    ) -> ProposalResponse:
        def change(actor: AuthenticatedActor, governed: GovernedDefinition, now: datetime) -> Any:
            current = self._authored(
                actor,
                governed,
                proposal_id,
                request.expected_workflow_revision,
                request.expected_proposal_revision,
                {ProposalState.DRAFT},
            )
            _refuse_client_stages(current.kind, request.stages)
            proposal = _proposal(
                {
                    **_fields(current),
                    "stages": request.stages,
                    "note": request.note,
                    "revision": current.revision + 1,
                    "updated_at": now,
                    "last_activity_at": now,
                }
            )
            return proposal, self._write(
                governed,
                now,
                open_proposal=proposal,
                events=((GovernanceEventKind.PROPOSAL_EDITED, actor, proposal, None),),
            )

        actor, proposal = self._mutate(reauthorize, workflow_id, Capability.POLICY_MUTATE, change)
        return self._response(actor, proposal)

    def submit_proposal(
        self,
        reauthorize: Reauthorize,
        workflow_id: str,
        proposal_id: str,
        request: SubmitProposalRequest,
    ) -> ProposalResponse:
        def change(actor: AuthenticatedActor, governed: GovernedDefinition, now: datetime) -> Any:
            current = self._authored(
                actor,
                governed,
                proposal_id,
                request.expected_workflow_revision,
                request.expected_proposal_revision,
                {ProposalState.DRAFT},
            )
            _refuse_invalid(self._report(governed, current, current.stages))
            content_hash = proposal_content_hash(
                current.kind, current.stages, current.restore_target_version
            )
            if request.content_hash != content_hash:
                raise WorkflowGovernanceError(GovernanceErrorCode.PROPOSAL_CONTENT_CHANGED)
            number, _active = self._active(governed)
            if current.base_version != number:
                raise WorkflowGovernanceError(GovernanceErrorCode.PROPOSAL_STALE)
            proposal = _proposal(
                {
                    **_fields(current),
                    "state": ProposalState.PENDING_APPROVAL,
                    "content_hash": content_hash,
                    "submitted_at": now,
                    "revision": current.revision + 1,
                    "updated_at": now,
                    "last_activity_at": now,
                }
            )
            return proposal, self._write(
                governed,
                now,
                open_proposal=proposal,
                events=((GovernanceEventKind.PROPOSAL_SUBMITTED, actor, proposal, None),),
            )

        actor, proposal = self._mutate(reauthorize, workflow_id, Capability.POLICY_MUTATE, change)
        return self._response(actor, proposal)

    def withdraw_proposal(
        self,
        reauthorize: Reauthorize,
        workflow_id: str,
        proposal_id: str,
        request: WithdrawProposalRequest,
    ) -> ProposalResponse:
        def change(actor: AuthenticatedActor, governed: GovernedDefinition, now: datetime) -> Any:
            current = self._authored(
                actor,
                governed,
                proposal_id,
                request.expected_workflow_revision,
                request.expected_proposal_revision,
                {ProposalState.DRAFT, ProposalState.PENDING_APPROVAL},
            )
            proposal = _proposal(
                {
                    **_fields(current),
                    "state": ProposalState.WITHDRAWN,
                    "withdrawn_at": now,
                    "revision": current.revision + 1,
                    "updated_at": now,
                    "last_activity_at": now,
                }
            )
            return proposal, self._write(
                governed,
                now,
                open_proposal=None,
                decided=proposal,
                events=((GovernanceEventKind.PROPOSAL_WITHDRAWN, actor, proposal, None),),
            )

        actor, proposal = self._mutate(reauthorize, workflow_id, Capability.POLICY_MUTATE, change)
        return self._response(actor, proposal)

    # --- Director decision -------------------------------------------------------------

    def decide(
        self,
        reauthorize: Reauthorize,
        workflow_id: str,
        proposal_id: str,
        request: DecisionRequest,
    ) -> DecisionResponse:
        """One durable compare-and-set (ADR-017 1.1). A second decision fails on revision
        or state; a decision never publishes twice."""

        def change(actor: AuthenticatedActor, governed: GovernedDefinition, now: datetime) -> Any:
            self._expect_workflow(governed, request.expected_workflow_revision)
            current = self._open(governed, proposal_id)
            if current.revision != request.expected_proposal_revision:
                raise WorkflowConflictError
            if current.state != ProposalState.PENDING_APPROVAL:
                raise WorkflowGovernanceError(GovernanceErrorCode.PROPOSAL_STATE_INVALID)
            # Second self-decision check: the service identity check.
            if current.author_id == actor.profile.user_id:
                raise WorkflowGovernanceError(GovernanceErrorCode.SELF_DECISION_REFUSED)
            recomputed = proposal_content_hash(
                current.kind, current.stages, current.restore_target_version
            )
            if request.content_hash != current.content_hash or current.content_hash != recomputed:
                raise WorkflowGovernanceError(GovernanceErrorCode.PROPOSAL_CONTENT_CHANGED)
            number, active = self._active(governed)
            if current.base_version != number:
                raise WorkflowGovernanceError(GovernanceErrorCode.PROPOSAL_STALE)
            approve = request.outcome == DecisionOutcome.APPROVE
            if approve:
                # The ratchet re-runs against the CURRENT active version and baseline.
                report = self._report(governed, current, current.stages)
                _refuse_invalid(report)
                expected = {item.key for item in report.permanent_obligations}
                acknowledged = set(request.acknowledged_permanent_obligations)
                if acknowledged != expected or len(acknowledged) != len(
                    request.acknowledged_permanent_obligations
                ):
                    raise WorkflowGovernanceError(
                        GovernanceErrorCode.PERMANENT_OBLIGATION_ACK_REQUIRED
                    )
            elif request.acknowledged_permanent_obligations:
                raise WorkflowGovernanceError(
                    GovernanceErrorCode.PROPOSAL_INVALID,
                    "A rejection acknowledges no permanent obligations.",
                )
            deactivating = approve and current.kind == ProposalKind.DEACTIVATE
            # Inside the held confirmation gate (ADR-017 4, R1-9 and R2-5).
            if deactivating and self._gate.in_progress(workflow_id):
                raise WorkflowGovernanceError(GovernanceErrorCode.RUN_CONFIRMATION_IN_PROGRESS)
            definition = governed.definition
            # An approved DEACTIVATE publishes no version (CC-5).
            published = (
                (definition.latest_version or 0) + 1 if approve and not deactivating else None
            )
            decided = _proposal(
                {
                    **_fields(current),
                    "state": ProposalState.APPROVED if approve else ProposalState.REJECTED,
                    "decided_at": now,
                    "decided_by": actor.profile.user_id,
                    "decision_reason": request.reason,
                    "acknowledged_permanent_obligations": (
                        request.acknowledged_permanent_obligations
                    ),
                    "published_version": published,
                    "revision": current.revision + 1,
                    "updated_at": now,
                    "last_activity_at": now,
                }
            )
            if deactivating:
                # Never modifies a run; the gate stays held until this CAS completes.
                return (decided, None, None), self._write(
                    governed,
                    now,
                    open_proposal=None,
                    decided=decided,
                    deactivate=True,
                    events=(
                        (GovernanceEventKind.PROPOSAL_APPROVED, actor, decided, None),
                        (GovernanceEventKind.DEACTIVATED, actor, decided, None),
                    ),
                )
            if published is None:
                return (decided, None, None), self._write(
                    governed,
                    now,
                    open_proposal=None,
                    decided=decided,
                    events=((GovernanceEventKind.PROPOSAL_REJECTED, actor, decided, None),),
                )
            version = WorkflowVersion(
                version=published,
                stages=decided.stages,
                activated_at=now,
                activated_by=actor.profile.user_id,
            )
            provenance = _provenance(
                version=published,
                author_id=decided.author_id,
                approved_by=actor.profile.user_id,
                proposal_id=decided.proposal_id,
                published_at=now,
            )
            state = governed.governance
            events: list[EventSpec] = [
                (GovernanceEventKind.PROPOSAL_APPROVED, actor, decided, published),
                (GovernanceEventKind.VERSION_PUBLISHED, actor, decided, published),
            ]
            if decided.kind == ProposalKind.REACTIVATE:
                events.append((GovernanceEventKind.REACTIVATED, actor, decided, published))
            return (decided, version, provenance), self._write(
                governed,
                now,
                open_proposal=None,
                decided=decided,
                version=version,
                required_baseline=self._advanced(state.required_baseline, version),
                version_provenance=(*state.version_provenance, provenance),
                events=events,
            )

        with self._lock:
            actor, outcome, stored = self._mutate_locked(
                reauthorize,
                workflow_id,
                Capability.POLICY_APPROVE,
                change,
                gate=self._deactivation_gate(workflow_id, proposal_id),
            )
        decided, version, provenance = outcome
        report = None if version is None else self._publication_report(stored, version.version)
        return DecisionResponse(
            proposal=self._response(actor, decided),
            workflow_revision=stored.definition.revision,
            active_version=stored.definition.stored_active_version or NO_ACTIVE_VERSION,
            published_version=None if version is None else version.version,
            provenance=provenance,
            publication_report=report,
        )

    # --- M2 recovery and administration (CC-4) -------------------------------------------

    def emergency_fallback(
        self, reauthorize: Reauthorize, workflow_id: str, request: EmergencyFallbackRequest
    ) -> EmergencyFallbackResponse:
        """The Director's single-actor exception (ADR-017 4, D6): publishes the safe target
        with origin ``EMERGENCY_FALLBACK``, stales the open proposal (kept) and raises a
        persisted notice, in one compare-and-set. It never bypasses the ratchet."""

        def change(actor: AuthenticatedActor, governed: GovernedDefinition, now: datetime) -> Any:
            self._expect_workflow(governed, request.expected_workflow_revision)
            definition, state = governed.definition, governed.governance
            if self._deactivated(governed):
                # A single actor never reactivates a workflow (that needs two people).
                raise WorkflowGovernanceError(
                    GovernanceErrorCode.PROPOSAL_KIND_NOT_AVAILABLE,
                    "This workflow is deactivated. Propose a reactivation instead.",
                )
            unacknowledged = sum(1 for item in state.notices if item.acknowledged_at is None)
            if unacknowledged >= MAX_UNACKNOWLEDGED_NOTICES:
                raise WorkflowGovernanceError(GovernanceErrorCode.NOTICES_UNACKNOWLEDGED)
            if request.target == "VERSION":
                if request.target_version is None:
                    raise WorkflowGovernanceError(
                        GovernanceErrorCode.PROPOSAL_INVALID, "Choose the version to fall back to."
                    )
                target = self._version(governed, request.target_version)
                if target is None:
                    raise WorkflowGovernanceError(
                        GovernanceErrorCode.PROPOSAL_INVALID, "That version does not exist."
                    )
                base = target.stages
            else:
                if request.target_version is not None:
                    raise WorkflowGovernanceError(
                        GovernanceErrorCode.PROPOSAL_INVALID,
                        "A fallback to the default names no version.",
                    )
                base = ()
            stages = _safe_target(base, governed)
            number, active = self._active(governed)
            _refuse_invalid(
                validate_candidate(
                    stages,
                    active=active,
                    baseline=state.required_baseline,
                    is_onboarding=definition.is_onboarding,
                    base_version=number,
                    active_version=number,
                )
            )
            director = actor.profile.user_id
            published = (definition.latest_version or 0) + 1
            # Transparency only (QG P3-2; publication unchanged): obligations this
            # fallback makes permanent without the section 1.3 acknowledgement.
            added = permanent_obligations(stages, active=active, baseline=state.required_baseline)
            if added:
                LOGGER.warning(
                    "emergency fallback adds permanent obligations",
                    extra={
                        "workflow_id": definition.workflow_id,
                        "version": published,
                        "obligations": [
                            f"{item.key.stage_id}/{item.key.field_id or '-'}" for item in added
                        ],
                    },
                )
            target_label = (
                f"v{request.target_version}" if request.target == "VERSION" else "the default"
            )
            plural = "" if len(added) == 1 else "s"
            fallback_summary = (
                f"Emergency fallback to {target_label} (version {published}); "
                f"{len(added)} new permanent obligation{plural}"
            )[:160]
            version = WorkflowVersion(
                version=published, stages=stages, activated_at=now, activated_by=director
            )
            provenance = VersionProvenance(
                version=published,
                origin=VersionOrigin.EMERGENCY_FALLBACK,
                author_id=None,
                approved_by=None,
                proposal_id=None,
                activated_by=director,
                published_at=now,
                note=request.reason,
            )
            notice = GovernanceNotice(
                notice_id=str(self._uuid_factory()),
                kind=GovernanceEventKind.EMERGENCY_FALLBACK,
                raised_at=now,
                raised_by=director,
                version=published,
                reason=request.reason,
            )
            open_proposal = state.open_proposal
            staled = None
            events: list[EventSpec] = []
            if open_proposal is not None:
                staled = _proposal(
                    {
                        **_fields(open_proposal),
                        "state": ProposalState.STALE,
                        "stale_by_version": published,
                        "revision": open_proposal.revision + 1,
                        "updated_at": now,
                    }
                )
                events.append((GovernanceEventKind.PROPOSAL_STALE, actor, staled, published))
            events.extend(
                (
                    (GovernanceEventKind.EMERGENCY_FALLBACK, actor, None, published),
                    (GovernanceEventKind.VERSION_PUBLISHED, actor, None, published),
                    (GovernanceEventKind.NOTICE_RAISED, actor, None, published),
                )
            )
            outcome = (version, provenance, notice, () if staled is None else (staled.proposal_id,))
            return outcome, self._write(
                governed,
                now,
                open_proposal=None,
                decided=staled,
                version=version,
                required_baseline=self._advanced(state.required_baseline, version),
                version_provenance=(*state.version_provenance, provenance),
                notices=(*state.notices, notice),
                events=events,
                summaries={GovernanceEventKind.EMERGENCY_FALLBACK: fallback_summary},
            )

        with self._lock:
            _actor, outcome, stored = self._mutate_locked(
                reauthorize, workflow_id, Capability.POLICY_APPROVE, change
            )
        version, provenance, notice, staled_ids = outcome
        return EmergencyFallbackResponse(
            workflow_revision=stored.definition.revision,
            active_version=stored.definition.stored_active_version or version.version,
            published_version=version.version,
            provenance=provenance,
            notice=notice,
            staled_proposal_ids=staled_ids,
            publication_report=self._publication_report(stored, version.version),
        )

    def release_proposal(
        self,
        reauthorize: Reauthorize,
        workflow_id: str,
        proposal_id: str,
        request: ReleaseDraftRequest,
    ) -> ProposalResponse:
        """ADR-017 1.2: any HR user except the author releases an abandoned draft. Only the
        14-day inactivity rule applies: the backend has no reliable disabled or deleted
        account signal to read (the synthetic identities are fixed)."""

        def change(actor: AuthenticatedActor, governed: GovernedDefinition, now: datetime) -> Any:
            self._expect_workflow(governed, request.expected_workflow_revision)
            current = self._open(governed, proposal_id)
            if current.author_id == actor.profile.user_id:
                # The author withdraws instead; a release is always someone else's.
                raise WorkflowForbiddenError
            if current.revision != request.expected_proposal_revision:
                raise WorkflowConflictError
            if current.state != ProposalState.DRAFT:
                raise WorkflowGovernanceError(GovernanceErrorCode.PROPOSAL_STATE_INVALID)
            if now - current.last_activity_at < timedelta(days=DRAFT_RELEASE_AFTER_DAYS):
                raise WorkflowGovernanceError(GovernanceErrorCode.DRAFT_NOT_RELEASABLE)
            released = _proposal(
                {
                    **_fields(current),
                    "state": ProposalState.WITHDRAWN,
                    "withdrawn_at": now,
                    "released_by": actor.profile.user_id,
                    "release_reason": request.reason,
                    "revision": current.revision + 1,
                    "updated_at": now,
                }
            )
            return released, self._write(
                governed,
                now,
                open_proposal=None,
                decided=released,
                events=((GovernanceEventKind.DRAFT_RELEASED, actor, released, None),),
            )

        actor, proposal = self._mutate(reauthorize, workflow_id, Capability.POLICY_MUTATE, change)
        return self._response(actor, proposal)

    def copy_proposal(
        self,
        reauthorize: Reauthorize,
        workflow_id: str,
        proposal_id: str,
        request: CopyProposalRequest,
    ) -> ProposalResponse:
        """A new DRAFT authored by the copier, with ``copied_from``; authorship is never
        transferred. One open proposal per workflow still applies.

        Only a decided proposal whose full record is still hot can be copied. One whose
        record exists only in cold storage (archived and compacted) returns
        ``503 WORKFLOW_HISTORY_UNAVAILABLE``: the governance port reads cold versions,
        not cold proposals (QG P3-5).
        """

        def change(actor: AuthenticatedActor, governed: GovernedDefinition, now: datetime) -> Any:
            self._expect_workflow(governed, request.expected_workflow_revision)
            state = governed.governance
            if state.open_proposal is not None:
                raise WorkflowGovernanceError(GovernanceErrorCode.PROPOSAL_OPEN)
            entry = next(
                (item for item in state.decided_proposals if item.proposal_id == proposal_id),
                None,
            )
            if entry is None:
                raise WorkflowGovernanceError(GovernanceErrorCode.PROPOSAL_NOT_FOUND)
            if entry.record is None:
                # Archived to cold; the governance port reads only cold versions.
                raise WorkflowGovernanceError(GovernanceErrorCode.HISTORY_UNAVAILABLE)
            number, _active = self._active(governed)
            kind = ProposalKind.REACTIVATE if self._deactivated(governed) else ProposalKind.CHANGE
            copied = _proposal(
                {
                    "proposal_id": str(self._uuid_factory()),
                    "workflow_id": governed.definition.workflow_id,
                    "kind": kind,
                    "origin": ProposalOrigin.GOVERNED,
                    "base_version": number,
                    "stages": entry.record.stages,
                    "note": request.note,
                    "author_id": actor.profile.user_id,
                    "created_at": now,
                    "updated_at": now,
                    "last_activity_at": now,
                    "copied_from": proposal_id,
                }
            )
            return copied, self._write(
                governed,
                now,
                open_proposal=copied,
                events=((GovernanceEventKind.DRAFT_COPIED, actor, copied, None),),
            )

        actor, proposal = self._mutate(reauthorize, workflow_id, Capability.POLICY_MUTATE, change)
        return self._response(actor, proposal)

    def get_version(
        self, actor: AuthenticatedActor, workflow_id: str, number: int
    ) -> WorkflowVersionResponse:
        """One published version, hot then cold; an unknown one is a safe 404."""

        self._require_reader(actor)
        governed = self._load(workflow_id)
        version = self._version(governed, number) if number >= 1 else None
        if version is None:
            raise WorkflowNotFoundError
        provenance = next(
            (item for item in governed.governance.version_provenance if item.version == number),
            None,
        )
        return WorkflowVersionResponse(
            workflow_id=workflow_id,
            version=version,
            provenance=provenance,
            is_active=(governed.definition.stored_active_version or NO_ACTIVE_VERSION) == number,
        )

    def notices(self, actor: AuthenticatedActor) -> NoticeListResponse:
        """Every unacknowledged governance notice, across workflows (HR and Director)."""

        self._require_reader(actor)
        items = [
            NoticeItem(
                workflow_id=governed.definition.workflow_id,
                workflow_name=governed.definition.name,
                workflow_revision=governed.definition.revision,
                notice=notice,
            )
            for governed in self._repository.list_governed()
            for notice in governed.governance.notices
            if notice.acknowledged_at is None
        ]
        return NoticeListResponse(items=tuple(items))

    def acknowledge_notice(
        self, reauthorize: Reauthorize, notice_id: str, request: AcknowledgeNoticeRequest
    ) -> NoticeItem:
        """HR only. Sets ``acknowledged_by`` and ``acknowledged_at`` (the only permitted
        change) and records a ``NOTICE_ACKNOWLEDGED`` event."""

        def change(actor: AuthenticatedActor, governed: GovernedDefinition, now: datetime) -> Any:
            self._expect_workflow(governed, request.expected_workflow_revision)
            state = governed.governance
            current = next((item for item in state.notices if item.notice_id == notice_id), None)
            if current is None:
                raise WorkflowNotFoundError
            if current.acknowledged_at is not None:
                raise WorkflowConflictError
            acknowledged = current.model_copy(
                update={"acknowledged_by": actor.profile.user_id, "acknowledged_at": now}
            )
            return acknowledged, self._write(
                governed,
                now,
                open_proposal=state.open_proposal,
                notices=tuple(
                    acknowledged if item.notice_id == notice_id else item for item in state.notices
                ),
                events=(
                    (GovernanceEventKind.NOTICE_ACKNOWLEDGED, actor, None, current.version),
                ),
            )

        with self._lock:
            _actor, notice, stored = self._mutate_locked(
                reauthorize, request.workflow_id, Capability.POLICY_MUTATE, change
            )
        return NoticeItem(
            workflow_id=stored.definition.workflow_id,
            workflow_name=stored.definition.name,
            workflow_revision=stored.definition.revision,
            notice=notice,
        )

    # --- Internals ---------------------------------------------------------------------

    def _mutate(
        self,
        reauthorize: Reauthorize,
        workflow_id: str,
        capability: Capability,
        change: Callable[[AuthenticatedActor, GovernedDefinition, datetime], Any],
    ) -> tuple[AuthenticatedActor, Any]:
        with self._lock:
            actor, outcome, _stored = self._mutate_locked(
                reauthorize, workflow_id, capability, change
            )
        return actor, outcome

    def _mutate_locked(
        self,
        reauthorize: Reauthorize,
        workflow_id: str,
        capability: Capability,
        change: Callable[[AuthenticatedActor, GovernedDefinition, datetime], Any],
        *,
        gate: AbstractContextManager[None] | None = None,
    ) -> tuple[AuthenticatedActor, Any, GovernedDefinition]:
        with gate or nullcontext():
            return self._mutate_checked(reauthorize, workflow_id, capability, change)

    def _mutate_checked(
        self,
        reauthorize: Reauthorize,
        workflow_id: str,
        capability: Capability,
        change: Callable[[AuthenticatedActor, GovernedDefinition, datetime], Any],
    ) -> tuple[AuthenticatedActor, Any, GovernedDefinition]:
        # Inside the definition lock: reauthorize first, then every check on fresh state.
        actor = reauthorize()
        self._require(actor, capability)
        self._migrated(workflow_id)
        if not self._startup.available or workflow_id in self._startup.blocked:
            raise WorkflowGovernanceError(GovernanceErrorCode.HISTORY_UNAVAILABLE)
        now = self._clock()
        with _persistence_errors():
            self._repository.drain_outbox(workflow_id, now=now)
        stored: GovernedDefinition | None = None
        for attempt in range(2):
            # Always built from the freshly read stored state (append, never rebuild).
            governed = self._migrated(workflow_id)
            outcome, write = change(actor, governed, now)
            try:
                with _persistence_errors():
                    stored = self._repository.write_governance(
                        write.definition,
                        write.governance,
                        expected_revision=governed.definition.revision,
                        active_version=write.publish_version,
                        latest_version=write.publish_version,
                        deactivate=write.deactivate,
                    )
                break
            except WorkflowConflictError:
                # A nonce-only conflict (a concurrent drain kept the revision) is re-read and
                # retried once inside the lock; a revision change is the client's 409. An
                # ambiguous outcome is never retried (it propagates as 503).
                if attempt or not self._nonce_only_conflict(workflow_id, governed):
                    raise
        assert stored is not None
        try:
            self._repository.drain_outbox(workflow_id, now=now)
        except PersistenceError:
            # Committed: archival is retried by the next drain (never truncated).
            LOGGER.warning("workflow history archival deferred", extra={"workflow_id": workflow_id})
        return actor, outcome, stored

    def _nonce_only_conflict(self, workflow_id: str, read: GovernedDefinition) -> bool:
        current = self._load(workflow_id)
        return (
            current.definition.revision == read.definition.revision
            and current.definition.write_nonce != read.definition.write_nonce
        )

    def _write(
        self,
        governed: GovernedDefinition,
        now: datetime,
        *,
        open_proposal: WorkflowProposal | None,
        events: Sequence[EventSpec],
        decided: WorkflowProposal | None = None,
        version: WorkflowVersion | None = None,
        deactivate: bool = False,
        summaries: Mapping[GovernanceEventKind, str] | None = None,
        **changes: Any,
    ) -> _Write:
        definition, state = governed.definition, governed.governance
        workflow_id = definition.workflow_id
        outbox: list[OutboxEntry] = list(state.outbox)
        decided_entries = list(state.decided_proposals)
        payload: dict[str, Any] = {"revision": definition.revision + 1, "updated_at": now}
        if version is not None:
            payload["versions"] = (*definition.versions, version)
            outbox.append(outbox_for_version(workflow_id, version))
        if decided is not None:
            decided_entries.append(decided_entry(decided, ended_at=now))
            outbox.append(outbox_for_proposal(decided))
        sequence = state.governance_sequence
        new_events: list[GovernanceEvent] = []
        for kind, actor, proposal, number in events:
            sequence += 1
            event = GovernanceEvent(
                sequence=sequence,
                occurred_at=now,
                actor_id=actor.profile.user_id,
                kind=kind,
                proposal_id=None if proposal is None else proposal.proposal_id,
                version=number,
                summary=(summaries or {}).get(kind) or _event_summary(kind, number),
            )
            new_events.append(event)
            outbox.append(outbox_for_event(workflow_id, event))
        try:
            governance = WorkflowGovernanceState.model_validate(
                {
                    **_fields(state),
                    "open_proposal": open_proposal,
                    "decided_proposals": tuple(decided_entries),
                    "governance_events": (*state.governance_events, *new_events),
                    "outbox": tuple(outbox),
                    "governance_sequence": sequence,
                    **changes,
                }
            )
        except ValidationError:
            # e.g. the outbox is full because archival keeps failing: never truncate.
            raise WorkflowGovernanceError(GovernanceErrorCode.HISTORY_UNAVAILABLE) from None
        return _Write(
            definition=definition.model_copy(update=payload),
            governance=governance,
            publish_version=None if version is None else version.version,
            deactivate=deactivate,
        )

    def _publication_report(
        self, stored: GovernedDefinition, published: int
    ) -> PublicationReport | None:
        """From case ledger records only (ADR-017 1.1), never the D3 counter. A failure
        to count never undoes or fails the committed decision."""

        now = self._clock()
        if stored.definition.is_onboarding and self._ledger is None:
            return None
        try:
            past_first_write = authorised = possibly = 0
            if stored.definition.is_onboarding:
                assert self._ledger is not None
                for _case_id, entries in self._ledger():
                    bucket = _case_bucket(entries, published, now)
                    past_first_write += bucket == "WRITE"
                    authorised += bucket == "AUTHORISED"
                    possibly += bucket == "TENTATIVE"
            return PublicationReport(
                published_version=published,
                cases_past_first_write_under_earlier_version=past_first_write,
                cases_authorised_under_earlier_version=authorised,
                cases_possibly_authorised=possibly,
                counted_at=now,
            )
        except Exception as error:  # noqa: BLE001 - the decision is already committed
            LOGGER.warning(
                "publication report unavailable",
                extra={
                    "workflow_id": stored.definition.workflow_id,
                    "reason": type(error).__name__,
                },
            )
            return None

    def _report(
        self,
        governed: GovernedDefinition,
        proposal: WorkflowProposal,
        stages: tuple[WorkflowStage, ...],
    ) -> ValidationReport:
        number, active = self._active(governed)
        kind = proposal.kind
        if kind == ProposalKind.DEACTIVATE:
            return self._deactivation_report(governed, proposal, stages, number)
        report = validate_candidate(
            stages,
            active=active,
            baseline=governed.governance.required_baseline,
            is_onboarding=governed.definition.is_onboarding,
            base_version=proposal.base_version,
            active_version=number,
            kind=kind,
        )
        issues = list(report.issues)
        if kind in LIFECYCLE_KINDS and governed.definition.is_onboarding:
            issues.insert(0, _kind_issue("Onboarding cannot be deactivated or reactivated."))
        if kind == ProposalKind.REACTIVATE and not self._deactivated(governed):
            issues.insert(0, _kind_issue("Only a deactivated workflow can be reactivated."))
        if kind in RECOVERY_KINDS:
            target = self._recovery_target(governed, kind, proposal.restore_target_version)
            if stages != target:
                issues.insert(
                    0,
                    ValidationIssue(
                        code=GovernanceErrorCode.PROPOSAL_INVALID.value,
                        message="The content no longer equals the safe target. Start again.",
                    ),
                )
        return report.model_copy(
            update={
                "valid": not issues,
                "issues": tuple(issues),
                "content_hash": proposal_content_hash(
                    kind, stages, proposal.restore_target_version
                ),
            }
        )

    def _deactivation_report(
        self,
        governed: GovernedDefinition,
        proposal: WorkflowProposal,
        stages: tuple[WorkflowStage, ...],
        number: int,
    ) -> ValidationReport:
        issues: list[ValidationIssue] = []
        if governed.definition.is_onboarding:
            issues.append(_kind_issue("Onboarding cannot be deactivated."))
        if number == NO_ACTIVE_VERSION:
            issues.append(_kind_issue("This workflow has no active version to deactivate."))
        if stages:
            issues.append(
                ValidationIssue(
                    code=GovernanceErrorCode.PROPOSAL_INVALID.value,
                    message="A deactivation carries no stages.",
                )
            )
        return ValidationReport(
            valid=not issues,
            content_hash=proposal_content_hash(ProposalKind.DEACTIVATE, ()),
            encoded_bytes=0,
            max_encoded_bytes=MAX_ENCODED_VERSION_BYTES,
            base_version=proposal.base_version,
            active_version=number,
            issues=tuple(issues),
        )

    # --- M2 helpers (CC-4) ---------------------------------------------------------------

    @staticmethod
    def _deactivated(governed: GovernedDefinition) -> bool:
        definition = governed.definition
        return (definition.stored_active_version or NO_ACTIVE_VERSION) == NO_ACTIVE_VERSION and (
            definition.latest_version or 0
        ) > 0

    def _version(self, governed: GovernedDefinition, number: int) -> WorkflowVersion | None:
        for item in governed.definition.versions:
            if item.version == number:
                return item
        with _persistence_errors():
            return self._repository.get_version(governed.definition.workflow_id, number)

    def _recovery_target(
        self,
        governed: GovernedDefinition,
        kind: ProposalKind,
        restore_target_version: int | None,
    ) -> tuple[WorkflowStage, ...]:
        """The safe target ``base ∪ required_baseline`` (ADR-017 2, 4); base is the target
        version's stages (hot, then cold) or the built-in default (no added stages)."""

        base: tuple[WorkflowStage, ...] = ()
        if kind == ProposalKind.RESTORE_VERSION:
            if restore_target_version is None:
                raise WorkflowGovernanceError(
                    GovernanceErrorCode.PROPOSAL_INVALID, "Choose the version to restore."
                )
            version = self._version(governed, restore_target_version)
            if version is None:
                raise WorkflowGovernanceError(
                    GovernanceErrorCode.PROPOSAL_INVALID, "That version does not exist."
                )
            base = version.stages
        return _safe_target(base, governed)

    def _initial_stages(
        self, governed: GovernedDefinition, request: CreateProposalRequest
    ) -> tuple[WorkflowStage, ...]:
        kind = request.kind
        definition = governed.definition
        deactivated = self._deactivated(governed)
        if kind in LIFECYCLE_KINDS and definition.is_onboarding:
            raise WorkflowGovernanceError(
                GovernanceErrorCode.PROPOSAL_KIND_NOT_AVAILABLE,
                "Onboarding cannot be deactivated or reactivated.",
            )
        _refuse_client_stages(kind, request.stages)
        if kind == ProposalKind.DEACTIVATE:
            if deactivated or (definition.stored_active_version or 0) == NO_ACTIVE_VERSION:
                raise WorkflowGovernanceError(
                    GovernanceErrorCode.PROPOSAL_KIND_NOT_AVAILABLE,
                    "This workflow has no active version to deactivate.",
                )
            return ()
        if kind == ProposalKind.REACTIVATE:
            if not deactivated:
                raise WorkflowGovernanceError(
                    GovernanceErrorCode.PROPOSAL_KIND_NOT_AVAILABLE,
                    "Only a deactivated workflow can be reactivated.",
                )
            if request.stages is not None:
                return request.stages
            latest = self._version(governed, definition.latest_version or 0)
            if latest is None:
                raise WorkflowGovernanceError(GovernanceErrorCode.HISTORY_UNAVAILABLE)
            return latest.stages
        if deactivated:
            raise WorkflowGovernanceError(
                GovernanceErrorCode.PROPOSAL_KIND_NOT_AVAILABLE,
                "This workflow is deactivated. Propose a reactivation instead.",
            )
        if kind in RECOVERY_KINDS:
            return self._recovery_target(governed, kind, request.restore_target_version)
        _number, active = self._active(governed)
        if request.stages is not None:
            return request.stages
        return active.stages if active is not None else ()

    @staticmethod
    def _advanced(baseline: Any, version: WorkflowVersion) -> Any:
        try:
            return advance_baseline(baseline, version)
        except ValueError:
            # Defence in depth: a version that did not pass the ratchet never publishes.
            raise WorkflowGovernanceError(GovernanceErrorCode.PROPOSAL_INVALID) from None

    def _deactivation_gate(
        self, workflow_id: str, proposal_id: str
    ) -> AbstractContextManager[None] | None:
        """Hold the confirmation gate for a deactivation decision (under the definition
        lock, so the open proposal's kind cannot change before the decision runs)."""

        with _persistence_errors():
            governed = self._repository.get_governed(workflow_id)
        proposal = None if governed is None else governed.governance.open_proposal
        if (
            proposal is not None
            and proposal.proposal_id == proposal_id
            and proposal.kind == ProposalKind.DEACTIVATE
        ):
            return self._gate.holding(workflow_id)
        return None

    def _active(self, governed: GovernedDefinition) -> tuple[int, WorkflowVersion | None]:
        definition = governed.definition
        number = definition.stored_active_version or NO_ACTIVE_VERSION
        if number == NO_ACTIVE_VERSION:
            return NO_ACTIVE_VERSION, None
        for item in definition.versions:
            if item.version == number:
                return number, item
        with _persistence_errors():
            version = self._repository.get_version(definition.workflow_id, number)
        if version is None:
            raise WorkflowGovernanceError(GovernanceErrorCode.HISTORY_UNAVAILABLE)
        return number, version

    def _load(self, workflow_id: str) -> GovernedDefinition:
        with _persistence_errors():
            governed = self._repository.get_governed(workflow_id)
        if governed is None:
            raise WorkflowNotFoundError
        return governed

    def _migrated(self, workflow_id: str) -> GovernedDefinition:
        governed = self._load(workflow_id)
        if not governed.governance.migrated:
            raise WorkflowGovernanceError(GovernanceErrorCode.GOVERNANCE_NOT_MIGRATED)
        return governed

    @staticmethod
    def _open(governed: GovernedDefinition, proposal_id: str) -> WorkflowProposal:
        proposal = governed.governance.open_proposal
        if proposal is not None and proposal.proposal_id == proposal_id:
            return proposal
        if any(item.proposal_id == proposal_id for item in governed.governance.decided_proposals):
            # A decided proposal: a second decision or edit fails on its state.
            raise WorkflowGovernanceError(GovernanceErrorCode.PROPOSAL_STATE_INVALID)
        raise WorkflowGovernanceError(GovernanceErrorCode.PROPOSAL_NOT_FOUND)

    @staticmethod
    def _expect_workflow(governed: GovernedDefinition, expected_revision: int) -> None:
        if governed.definition.revision != expected_revision:
            raise WorkflowConflictError

    def _authored(
        self,
        actor: AuthenticatedActor,
        governed: GovernedDefinition,
        proposal_id: str,
        expected_workflow_revision: int,
        expected_proposal_revision: int,
        states: set[ProposalState],
    ) -> WorkflowProposal:
        self._expect_workflow(governed, expected_workflow_revision)
        proposal = self._open(governed, proposal_id)
        if proposal.author_id != actor.profile.user_id:
            raise WorkflowForbiddenError
        if proposal.revision != expected_proposal_revision:
            raise WorkflowConflictError
        if proposal.state not in states:
            raise WorkflowGovernanceError(GovernanceErrorCode.PROPOSAL_STATE_INVALID)
        return proposal

    def _view(
        self, actor: AuthenticatedActor, governed: GovernedDefinition
    ) -> WorkflowGovernanceView | None:
        state = governed.governance
        if not state.migrated:
            return None
        open_proposal = state.open_proposal
        baseline = state.required_baseline
        return WorkflowGovernanceView(
            migrated=True,
            latest_version=governed.definition.latest_version or 0,
            open_proposal=None if open_proposal is None else self._response(actor, open_proposal),
            decided_proposals=tuple(
                DecidedProposalSummaryResponse(
                    proposal_id=item.proposal_id,
                    kind=item.kind,
                    state=item.state,
                    origin=item.origin,
                    author_id=item.author_id,
                    decided_by=item.decided_by,
                    decided_at=item.decided_at,
                    ended_at=item.ended_at,
                    published_version=item.published_version,
                )
                for item in state.decided_proposals
            ),
            version_provenance=state.version_provenance,
            baseline=BaselineSummary(
                seeded_from_version=baseline.seeded_from_version,
                updated_at_version=baseline.updated_at_version,
                required_stages=len(baseline.stages),
                required_fields=sum(len(stage.fields) for stage in baseline.stages),
            ),
            recent_events=state.governance_events[-RECENT_EVENTS:],
            unacknowledged_notices=tuple(
                item for item in state.notices if item.acknowledged_at is None
            ),
            can_create_proposal=(
                _has(actor, Capability.POLICY_MUTATE)
                and open_proposal is None
                and self._startup.available
                and governed.definition.workflow_id not in self._startup.blocked
            ),
        )

    @staticmethod
    def _response(actor: AuthenticatedActor, proposal: WorkflowProposal) -> ProposalResponse:
        author = proposal.author_id == actor.profile.user_id
        hr = _has(actor, Capability.POLICY_MUTATE)
        draft = proposal.state == ProposalState.DRAFT
        pending = proposal.state == ProposalState.PENDING_APPROVAL
        return ProposalResponse.from_domain(
            proposal,
            can_edit=hr and author and draft and proposal.kind not in COMPUTED_KINDS,
            can_submit=hr and author and draft,
            can_withdraw=hr and author and (draft or pending),
            can_decide=_has(actor, Capability.POLICY_APPROVE) and pending and not author,
        )

    @staticmethod
    def _require(actor: AuthenticatedActor, capability: Capability) -> None:
        if not _has(actor, capability):
            raise WorkflowForbiddenError

    @staticmethod
    def _require_reader(actor: AuthenticatedActor) -> None:
        if not (_has(actor, Capability.POLICY_MUTATE) or _has(actor, Capability.POLICY_APPROVE)):
            raise WorkflowForbiddenError


@contextmanager
def _persistence_errors() -> Iterator[None]:
    """Map repository errors to the governance contract (ADR-017 5, section 4).

    Ambiguous outcomes and unavailability propagate (503) and are never retried here.
    """

    try:
        yield
    except PersistenceConflictError:
        raise WorkflowConflictError from None
    except WorkflowGovernanceNotMigratedError:
        raise WorkflowGovernanceError(GovernanceErrorCode.GOVERNANCE_NOT_MIGRATED) from None
    except WorkflowHistoryUnavailableError:
        raise WorkflowGovernanceError(GovernanceErrorCode.HISTORY_UNAVAILABLE) from None


def _proposal(data: dict[str, Any]) -> WorkflowProposal:
    try:
        return WorkflowProposal.model_validate(data)
    except ValidationError as error:
        if "WORKFLOW_SELF_DECISION_REFUSED" in str(error):
            # Third self-decision check: the model validator.
            raise WorkflowGovernanceError(GovernanceErrorCode.SELF_DECISION_REFUSED) from None
        raise WorkflowGovernanceError(GovernanceErrorCode.PROPOSAL_INVALID) from None


def _provenance(
    *,
    version: int,
    author_id: str | None,
    approved_by: str,
    proposal_id: str,
    published_at: datetime,
) -> VersionProvenance:
    try:
        return VersionProvenance(
            version=version,
            origin=VersionOrigin.GOVERNED_APPROVAL,
            author_id=author_id,
            approved_by=approved_by,
            proposal_id=proposal_id,
            published_at=published_at,
        )
    except ValidationError as error:
        if "WORKFLOW_SELF_DECISION_REFUSED" in str(error):
            raise WorkflowGovernanceError(GovernanceErrorCode.SELF_DECISION_REFUSED) from None
        raise WorkflowGovernanceError(GovernanceErrorCode.PROPOSAL_INVALID) from None


def _refuse_client_stages(
    kind: ProposalKind, stages: tuple[WorkflowStage, ...] | None
) -> None:
    if kind in COMPUTED_KINDS and stages is not None:
        raise WorkflowGovernanceError(
            GovernanceErrorCode.PROPOSAL_INVALID,
            "The server computes this proposal's content; stages cannot be supplied.",
        )


def _kind_issue(message: str) -> ValidationIssue:
    return ValidationIssue(
        code=GovernanceErrorCode.PROPOSAL_KIND_NOT_AVAILABLE.value, message=message
    )


def _safe_target(
    base: tuple[WorkflowStage, ...], governed: GovernedDefinition
) -> tuple[WorkflowStage, ...]:
    try:
        return safe_target(base, governed.governance.required_baseline)
    except SafeTargetError as error:
        raise WorkflowGovernanceError(
            GovernanceErrorCode.PROPOSAL_INVALID, error.public_message
        ) from None


def _refuse_invalid(report: ValidationReport) -> None:
    if report.valid:
        return
    first = report.issues[0]
    raise WorkflowGovernanceError(first.code, first.message, rule=first.rule, issues=report.issues)


_EVENT_SUMMARIES: dict[GovernanceEventKind, str] = {
    GovernanceEventKind.PROPOSAL_CREATED: "Proposal created",
    GovernanceEventKind.PROPOSAL_EDITED: "Proposal edited",
    GovernanceEventKind.PROPOSAL_SUBMITTED: "Proposal submitted for approval",
    GovernanceEventKind.PROPOSAL_WITHDRAWN: "Proposal withdrawn by its author",
    GovernanceEventKind.PROPOSAL_APPROVED: "Proposal approved",
    GovernanceEventKind.PROPOSAL_REJECTED: "Proposal rejected",
    GovernanceEventKind.VERSION_PUBLISHED: "Version published",
    GovernanceEventKind.PROPOSAL_STALE: "Proposal superseded by an emergency fallback",
    GovernanceEventKind.DRAFT_RELEASED: "Abandoned draft released",
    GovernanceEventKind.DRAFT_COPIED: "Proposal copied into a new draft",
    GovernanceEventKind.EMERGENCY_FALLBACK: "Emergency fallback by a Director",
    GovernanceEventKind.NOTICE_RAISED: "Governance notice raised",
    GovernanceEventKind.NOTICE_ACKNOWLEDGED: "Governance notice acknowledged",
    GovernanceEventKind.REACTIVATED: "Workflow reactivated",
    GovernanceEventKind.DEACTIVATED: "Workflow deactivated for new runs",
}


def _event_summary(kind: GovernanceEventKind, version: int | None) -> str:
    text = _EVENT_SUMMARIES.get(kind, kind.value)
    return text if version is None else f"{text} (version {version})"


def _case_bucket(
    entries: Sequence[GoldTierExecutionLedgerEntry], published: int, now: datetime
) -> str | None:
    """The strongest earlier-version dispatch evidence of one case, from its ledger."""

    best: str | None = None
    for entry in entries:
        claim = entry.workflow_dispatch
        if has_write_marker(entry):
            first = claim.first_write if claim is not None else None
            # Without a recorded dispatch version the write predates this publication.
            if first is None or first.version < published:
                return "WRITE"
            continue
        if claim is None or claim.version >= published:
            continue
        if claim.state == WorkflowDispatchState.AUTHORISED:
            best = "AUTHORISED"
        elif claim.lease_until > now and best is None:
            best = "TENTATIVE"
    return best
