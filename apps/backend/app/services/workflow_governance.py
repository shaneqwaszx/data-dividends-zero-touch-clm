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
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.api_workflow_governance_models import (
    AffectedCases,
    ApprovalInboxItem,
    ApprovalInboxResponse,
    BaselineSummary,
    ComparisonResponse,
    CreateProposalRequest,
    DecidedProposalSummaryResponse,
    DecisionRequest,
    DecisionResponse,
    GovernanceErrorBody,
    ProposalResponse,
    PublicationReport,
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
)
from app.domain.access import ROLE_CAPABILITIES, AuthenticatedActor, Capability
from app.domain.target_submission import GoldTierExecutionLedgerEntry, WorkflowDispatchState
from app.domain.workflow_governance import (
    GOVERNANCE_ERROR_STATUS,
    M1_PROPOSAL_KINDS,
    NO_ACTIVE_VERSION,
    PERMANENT_OBLIGATION_WARNING,
    DecisionOutcome,
    GovernanceErrorCode,
    GovernanceEvent,
    GovernanceEventKind,
    OutboxEntry,
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
    WorkflowConflictError,
    WorkflowForbiddenError,
    WorkflowNotFoundError,
)
from app.services.workflow_ratchet import (
    advance_baseline,
    change_counts,
    permanent_obligations,
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
    ) -> None:
        self._repository = repository
        self._runs = runs
        self._lock = lock
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
            number, active = self._active(governed)
            definition = governed.definition
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
            if request.kind not in M1_PROPOSAL_KINDS:
                raise WorkflowGovernanceError(GovernanceErrorCode.PROPOSAL_KIND_NOT_AVAILABLE)
            self._expect_workflow(governed, request.expected_workflow_revision)
            state = governed.governance
            if state.open_proposal is not None:
                raise WorkflowGovernanceError(GovernanceErrorCode.PROPOSAL_OPEN)
            number, active = self._active(governed)
            stages = request.stages
            if stages is None:
                stages = active.stages if active is not None else ()
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
            definition = governed.definition
            published = (definition.latest_version or 0) + 1 if approve else None
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
            return (decided, version, provenance), self._write(
                governed,
                now,
                open_proposal=None,
                decided=decided,
                version=version,
                required_baseline=advance_baseline(state.required_baseline, version),
                version_provenance=(*state.version_provenance, provenance),
                events=(
                    (GovernanceEventKind.PROPOSAL_APPROVED, actor, decided, published),
                    (GovernanceEventKind.VERSION_PUBLISHED, actor, decided, published),
                ),
            )

        with self._lock:
            actor, outcome, stored = self._mutate_locked(
                reauthorize, workflow_id, Capability.POLICY_APPROVE, change
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
        events: Sequence[
            tuple[GovernanceEventKind, AuthenticatedActor, WorkflowProposal, int | None]
        ],
        decided: WorkflowProposal | None = None,
        version: WorkflowVersion | None = None,
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
                proposal_id=proposal.proposal_id,
                version=number,
                summary=_event_summary(kind, number),
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
        )

    def _publication_report(
        self, stored: GovernedDefinition, published: int
    ) -> PublicationReport | None:
        """From case ledger records only (ADR-017 1.1), never the D3 counter. A failure
        to count never undoes or fails the committed decision."""

        now = self._clock()
        past_first_write = authorised = possibly = 0
        if stored.definition.is_onboarding:
            if self._ledger is None:
                return None
            try:
                rows = list(self._ledger())
            except Exception:  # noqa: BLE001
                LOGGER.warning("publication report unavailable")
                return None
            for _case_id, entries in rows:
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

    def _report(
        self,
        governed: GovernedDefinition,
        proposal: WorkflowProposal,
        stages: tuple[WorkflowStage, ...],
    ) -> ValidationReport:
        number, active = self._active(governed)
        return validate_candidate(
            stages,
            active=active,
            baseline=governed.governance.required_baseline,
            is_onboarding=governed.definition.is_onboarding,
            base_version=proposal.base_version,
            active_version=number,
            kind=proposal.kind,
        )

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
            can_edit=hr and author and draft,
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
