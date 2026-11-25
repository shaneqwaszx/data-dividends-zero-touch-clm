"""P2-1 workflow governance service (ADR-017 section 1, contract C0): memory mode only.

Service-level analogues of CT-1 (one atomic decision), CT-2 (a second decision is refused),
CT-3 (self-decision refused three ways) and CT-15 (a stricter publication interleaved before
approval is refused), plus the acknowledgement set, stale and changed content, the 503 paths,
startup, the publication report and the send hold after publication. No Mongo, no provider.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from threading import RLock
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError
from workflow_publication_seed import publish_draft

from app.api_workflow_governance_models import (
    CreateProposalRequest,
    DecisionRequest,
    SimulateProposalRequest,
    SubmitProposalRequest,
    UpdateProposalRequest,
    ValidateProposalRequest,
    WithdrawProposalRequest,
)
from app.domain.access import AuthenticatedActor, Role, UserProfile
from app.domain.target_submission import WorkflowDispatchState
from app.domain.workflow_governance import (
    DecisionOutcome,
    ObligationKey,
    OutboxCollection,
    ProposalKind,
    ProposalState,
    VersionOrigin,
    WorkflowProposal,
)
from app.domain.workflows import (
    ONBOARDING_USE_CASE,
    ONBOARDING_WORKFLOW_ID,
    WorkflowDefinition,
    WorkflowStage,
)
from app.persistence.errors import PersistenceConflictError, PersistenceOutcomeAmbiguousError
from app.persistence.workflow_governance_store import WorkflowHistoryUnavailableError
from app.services import workflow_governance
from app.services.workflow_governance import (
    GovernanceStartup,
    WorkflowGovernanceError,
    WorkflowGovernanceService,
    start_governance,
)
from app.services.workflow_management import (
    HOLD_INCOMPLETE,
    WorkflowConflictError,
    WorkflowForbiddenError,
    WorkflowManagementService,
    WorkflowNotFoundError,
)
from app.services.workflow_ratchet import seed_baseline
from app.services.workflow_repository import (
    InMemoryWorkflowDefinitionRepository,
    InMemoryWorkflowRunRepository,
    WorkflowGovernanceNotMigratedError,
)

NOW = datetime(2030, 6, 1, tzinfo=UTC)
STAGE = WorkflowStage.model_validate(
    {
        "stage_id": "signatory",
        "name": "Authorised signatory details",
        "after_node_id": "DOCUMENT_IDP",
        "fields": [
            {"field_id": "full-name", "label": "Full name", "kind": "TEXT", "required": True},
            {"field_id": "notes", "label": "Notes", "kind": "TEXT", "required": False},
        ],
    }
)
SIGNATORY = ObligationKey(stage_id="signatory")
FULL_NAME = ObligationKey(stage_id="signatory", field_id="full-name")
REASON = "Reviewed and approved for onboarding."


def actor(user_id: str, role: Role, team: str | None = None) -> AuthenticatedActor:
    profile = UserProfile(user_id=user_id, display_name=user_id, role=role, team_id=team)
    return AuthenticatedActor.model_construct(profile=profile)


HR = actor("biz-ops", Role.HR)
HR_2 = actor("hr-second", Role.HR)
DIRECTOR = actor("olivia-koh", Role.DIRECTOR)
ONBOARDER = actor("maya-lim", Role.CLIENT_ONBOARDER, "TEAM_A")
RM = actor("ethan-tan", Role.RELATIONSHIP_MANAGER, "TEAM_A")


class Cases:
    def __init__(self) -> None:
        self.case = SimpleNamespace(case_id=uuid4(), created_at=NOW + timedelta(days=1))

    def get_case(self, case_id: Any) -> Any:
        return self.case if case_id == self.case.case_id else None

    def case_lock(self, case_id: Any) -> RLock:
        return RLock()


class World:
    def __init__(self, *, ledger: Any = None, startup: GovernanceStartup | None = None) -> None:
        self.repository = InMemoryWorkflowDefinitionRepository()
        self.runs = InMemoryWorkflowRunRepository()
        self.cases = Cases()
        self.workflows = WorkflowManagementService(
            definitions=self.repository,
            runs=self.runs,
            cases=self.cases,  # type: ignore[arg-type]
            clock=lambda: NOW,
        )
        self.workflows.provision_onboarding()
        self.governance = WorkflowGovernanceService(
            repository=self.repository,
            runs=self.runs,
            lock=self.workflows.definition_lock,
            ledger=ledger,
            startup=startup,
            clock=lambda: NOW,
        )

    def revision(self, workflow_id: str = ONBOARDING_WORKFLOW_ID) -> int:
        definition = self.repository.get(workflow_id)
        assert definition is not None
        return definition.revision

    def create(self, stages=(STAGE,), *, by=HR, workflow_id=ONBOARDING_WORKFLOW_ID) -> Any:
        return self.governance.create_proposal(
            lambda: by,
            workflow_id,
            CreateProposalRequest(
                expected_workflow_revision=self.revision(workflow_id), stages=tuple(stages)
            ),
        )

    def submit(self, proposal: Any, *, by=HR, content_hash: str | None = None) -> Any:
        report = self.governance.validate(
            by, proposal.workflow_id, proposal.proposal_id, ValidateProposalRequest()
        )
        return self.governance.submit_proposal(
            lambda: by,
            proposal.workflow_id,
            proposal.proposal_id,
            SubmitProposalRequest(
                expected_workflow_revision=self.revision(proposal.workflow_id),
                expected_proposal_revision=proposal.revision,
                content_hash=content_hash or report.content_hash,
            ),
        )

    def decide(
        self,
        proposal: Any,
        *,
        by=DIRECTOR,
        outcome=DecisionOutcome.APPROVE,
        acks: tuple[ObligationKey, ...] | None = None,
        workflow_revision: int | None = None,
    ) -> Any:
        if acks is None:
            acks = (SIGNATORY, FULL_NAME) if outcome == DecisionOutcome.APPROVE else ()
        return self.governance.decide(
            lambda: by,
            proposal.workflow_id,
            proposal.proposal_id,
            DecisionRequest(
                outcome=outcome,
                reason=REASON,
                expected_workflow_revision=workflow_revision or self.revision(proposal.workflow_id),
                expected_proposal_revision=proposal.revision,
                content_hash=proposal.content_hash,
                acknowledged_permanent_obligations=acks,
            ),
        )

    def state(self, workflow_id: str = ONBOARDING_WORKFLOW_ID) -> Any:
        governed = self.repository.get_governed(workflow_id)
        assert governed is not None
        return governed


def code(error: pytest.ExceptionInfo[WorkflowGovernanceError]) -> str:
    return error.value.code


# --- Lifecycle -----------------------------------------------------------------------


def test_the_full_lifecycle_publishes_one_governed_version():
    world = World()
    assert world.state().governance.migrated  # born governed in a fresh store
    draft = world.create(())
    edited = world.governance.update_proposal(
        lambda: HR,
        ONBOARDING_WORKFLOW_ID,
        draft.proposal_id,
        UpdateProposalRequest(
            expected_workflow_revision=world.revision(),
            expected_proposal_revision=draft.revision,
            stages=(STAGE,),
        ),
    )
    assert edited.revision == 2 and edited.can_edit and edited.can_submit
    simulated = world.governance.simulate(
        HR, ONBOARDING_WORKFLOW_ID, draft.proposal_id, SimulateProposalRequest()
    )
    assert simulated.synthetic and all(item.held_before_send for item in simulated.outcomes)
    pending = world.submit(edited)
    assert pending.state == ProposalState.PENDING_APPROVAL and pending.content_hash
    assert not pending.can_edit and pending.can_withdraw

    decision = world.decide(pending)

    assert decision.published_version == 1 and decision.active_version == 1
    assert decision.proposal.state == ProposalState.APPROVED
    assert decision.provenance is not None
    assert decision.provenance.origin == VersionOrigin.GOVERNED_APPROVAL
    assert (decision.provenance.author_id, decision.provenance.approved_by) == (
        "biz-ops",
        "olivia-koh",
    )
    governed = world.state()
    definition, state = governed.definition, governed.governance
    assert definition.stored_active_version == definition.latest_version == 1
    assert definition.versions[-1].stages == (STAGE,)
    assert definition.versions[-1].activated_by == "olivia-koh"
    assert state.open_proposal is None
    assert [item.stage_id for item in state.required_baseline.stages] == ["signatory"]
    kinds = [item.kind.value for item in state.governance_events]
    assert kinds[-2:] == ["PROPOSAL_APPROVED", "VERSION_PUBLISHED"]
    # Drained after commit: the outbox is empty and every record has its cold copy.
    assert state.outbox == ()
    (entry,) = state.decided_proposals
    assert entry.archived and entry.record is not None
    cold = world.repository._cold  # noqa: SLF001
    assert cold.find(OutboxCollection.VERSIONS, f"{ONBOARDING_WORKFLOW_ID}:1")
    assert cold.find(OutboxCollection.PROPOSALS, pending.proposal_id)
    assert world.repository.verify_governance_state() == []
    assert world.repository.verify_dispatch_state() == []


def test_a_decision_is_one_compare_and_set_and_a_second_decision_is_refused():
    world = World()
    pending = world.submit(world.create())
    writes: list[Any] = []
    original = world.repository.write_governance

    def spy(*args: Any, **kwargs: Any) -> Any:
        writes.append(kwargs)
        return original(*args, **kwargs)

    world.repository.write_governance = spy  # type: ignore[method-assign]
    before = world.revision()
    world.decide(pending, workflow_revision=before)
    assert len(writes) == 1
    assert writes[0]["active_version"] == writes[0]["latest_version"] == 1

    with pytest.raises(WorkflowConflictError):  # the revision moved on
        world.decide(pending, workflow_revision=before)
    with pytest.raises(WorkflowGovernanceError) as refused:  # fresh revision: the state
        world.decide(pending)
    assert code(refused) == "WORKFLOW_PROPOSAL_STATE_INVALID"
    assert len(writes) == 1
    assert world.state().definition.latest_version == 1


def test_self_decision_is_refused_three_ways():
    world = World()
    pending = world.submit(world.create())
    # 1. Role: HR (the author's role) holds no POLICY_APPROVE.
    with pytest.raises(WorkflowForbiddenError):
        world.decide(pending, by=HR)
    # 2. Service identity check: a deciding identity equal to the author.
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.decide(pending, by=actor("biz-ops", Role.DIRECTOR))
    assert code(refused) == "WORKFLOW_SELF_DECISION_REFUSED"
    assert refused.value.status == 403
    # 3. The model validator, and the service mapping of it.
    data = {**pending.model_dump(include=set(WorkflowProposal.model_fields))}
    with pytest.raises(ValidationError, match="WORKFLOW_SELF_DECISION_REFUSED"):
        WorkflowProposal.model_validate(
            {
                **data,
                "state": ProposalState.REJECTED,
                "decided_by": "biz-ops",
                "decided_at": NOW,
                "decision_reason": REASON,
            }
        )
    with pytest.raises(WorkflowGovernanceError) as mapped:
        workflow_governance._proposal(  # noqa: SLF001
            {
                **data,
                "state": ProposalState.REJECTED,
                "decided_by": "biz-ops",
                "decided_at": NOW,
                "decision_reason": REASON,
            }
        )
    assert code(mapped) == "WORKFLOW_SELF_DECISION_REFUSED"
    assert world.state().governance.open_proposal.state == ProposalState.PENDING_APPROVAL


@pytest.mark.parametrize(
    "acks",
    [
        (),
        (SIGNATORY,),
        (SIGNATORY, FULL_NAME, ObligationKey(stage_id="other")),
        (SIGNATORY, FULL_NAME, FULL_NAME),
    ],
)
def test_approval_needs_exactly_the_permanent_obligation_set(acks):
    world = World()
    pending = world.submit(world.create())
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.decide(pending, acks=acks)
    assert code(refused) == "WORKFLOW_PERMANENT_OBLIGATION_ACKNOWLEDGEMENT_REQUIRED"
    assert refused.value.status == 409
    assert world.state().definition.versions == ()
    # The set is order-insensitive.
    assert world.decide(pending, acks=(FULL_NAME, SIGNATORY)).published_version == 1


def test_a_rejection_acknowledges_nothing_and_publishes_nothing():
    world = World()
    pending = world.submit(world.create())
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.decide(pending, outcome=DecisionOutcome.REJECT, acks=(SIGNATORY,))
    assert code(refused) == "WORKFLOW_PROPOSAL_INVALID"
    rejected = world.decide(pending, outcome=DecisionOutcome.REJECT)
    assert rejected.proposal.state == ProposalState.REJECTED
    assert rejected.published_version is None and rejected.publication_report is None
    governed = world.state()
    assert governed.definition.versions == () and governed.definition.latest_version == 0
    assert governed.governance.decided_proposals[-1].state == ProposalState.REJECTED
    assert world.repository.verify_governance_state() == []


def test_submit_refuses_changed_content_and_a_stale_base():
    world = World()
    draft = world.create()
    with pytest.raises(WorkflowGovernanceError) as changed:
        world.submit(draft, content_hash="0" * 64)
    assert code(changed) == "WORKFLOW_PROPOSAL_CONTENT_CHANGED"
    # Another version reaches the store first (test seed): the base is no longer active.
    publish_draft(world.repository, ONBOARDING_WORKFLOW_ID, stages=(STAGE,), now=NOW)
    with pytest.raises(WorkflowGovernanceError) as stale:
        world.submit(draft)
    assert code(stale) == "WORKFLOW_PROPOSAL_STALE"


def test_an_interleaved_stricter_publication_is_refused_at_approval():
    """CT-15 analogue: a publication between submit and decision makes the base stale."""

    world = World()
    pending = world.submit(world.create())
    publish_draft(world.repository, ONBOARDING_WORKFLOW_ID, stages=(STAGE,), now=NOW)
    with pytest.raises(WorkflowGovernanceError) as stale:
        world.decide(pending)
    assert code(stale) == "WORKFLOW_PROPOSAL_STALE"
    assert world.state().definition.latest_version == 1  # only the seeded version


def test_the_ratchet_reruns_against_the_current_baseline_at_approval():
    world = World()
    pending = world.submit(world.create())
    # The baseline becomes stricter while the proposal waits (same active version).
    stricter = WorkflowStage.model_validate(
        {
            "stage_id": "sanctions",
            "name": "Sanctions",
            "after_node_id": "ADVISORY",
            "fields": [{"field_id": "checked", "label": "Checked", "kind": "YES_NO"}],
        }
    )
    baseline = seed_baseline(_version(1, (stricter,)))
    repo = world.repository
    repo._governance[ONBOARDING_WORKFLOW_ID] = repo._governance[  # noqa: SLF001
        ONBOARDING_WORKFLOW_ID
    ].model_copy(update={"required_baseline": baseline})
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.decide(pending)
    assert code(refused) == "WORKFLOW_REQUIRED_OBLIGATION_REMOVED"
    assert refused.value.rule is not None and refused.value.rule.value == "RR-1"
    assert refused.value.issues
    assert world.state().definition.versions == ()


def _version(number: int, stages: tuple[WorkflowStage, ...]) -> Any:
    from app.domain.workflows import WorkflowVersion

    return WorkflowVersion(version=number, stages=stages, activated_at=NOW, activated_by="d")


# --- Proposal rules ------------------------------------------------------------------


def test_one_open_proposal_and_change_only_in_m1():
    world = World()
    world.create()
    with pytest.raises(WorkflowGovernanceError) as open_:
        world.create()
    assert code(open_) == "WORKFLOW_PROPOSAL_OPEN"
    other = World()
    with pytest.raises(WorkflowGovernanceError) as kind:
        other.governance.create_proposal(
            lambda: HR,
            ONBOARDING_WORKFLOW_ID,
            # M2 (CC-4): the recovery kinds exist; onboarding is never deactivated.
            CreateProposalRequest(
                kind=ProposalKind.DEACTIVATE, expected_workflow_revision=other.revision()
            ),
        )
    assert code(kind) == "WORKFLOW_PROPOSAL_KIND_NOT_AVAILABLE" and kind.value.status == 422


def test_only_the_author_edits_submits_or_withdraws_and_withdrawal_frees_the_slot():
    world = World()
    draft = world.create()
    with pytest.raises(WorkflowForbiddenError):
        world.submit(draft, by=HR_2)
    with pytest.raises(WorkflowForbiddenError):
        world.governance.withdraw_proposal(
            lambda: HR_2,
            ONBOARDING_WORKFLOW_ID,
            draft.proposal_id,
            WithdrawProposalRequest(
                expected_workflow_revision=world.revision(),
                expected_proposal_revision=draft.revision,
            ),
        )
    pending = world.submit(draft)
    with pytest.raises(WorkflowGovernanceError) as frozen:
        world.governance.update_proposal(
            lambda: HR,
            ONBOARDING_WORKFLOW_ID,
            pending.proposal_id,
            UpdateProposalRequest(
                expected_workflow_revision=world.revision(),
                expected_proposal_revision=pending.revision,
                stages=(),
            ),
        )
    assert code(frozen) == "WORKFLOW_PROPOSAL_STATE_INVALID"
    withdrawn = world.governance.withdraw_proposal(
        lambda: HR,
        ONBOARDING_WORKFLOW_ID,
        pending.proposal_id,
        WithdrawProposalRequest(
            expected_workflow_revision=world.revision(),
            expected_proposal_revision=pending.revision,
        ),
    )
    assert withdrawn.state == ProposalState.WITHDRAWN
    assert world.create().state == ProposalState.DRAFT
    assert world.repository.verify_governance_state() == []


def test_directors_do_not_author_and_onboarders_or_rms_reach_nothing():
    world = World()
    with pytest.raises(WorkflowForbiddenError):
        world.create(by=DIRECTOR)
    for outsider in (ONBOARDER, RM):
        with pytest.raises(WorkflowForbiddenError):
            world.create(by=outsider)
        with pytest.raises(WorkflowForbiddenError):
            world.governance.approvals_inbox(outsider)
        with pytest.raises(WorkflowForbiddenError):
            world.governance.list_workflows(outsider)
        with pytest.raises(WorkflowForbiddenError):
            world.governance.simulation_scenarios(outsider)
    with pytest.raises(WorkflowForbiddenError):
        world.governance.approvals_inbox(HR)
    with pytest.raises(WorkflowNotFoundError):
        world.governance.get_workflow(HR, "not-a-workflow")


def test_empty_non_onboarding_workflows_stay_unpublished_until_approved():
    world = World()
    with pytest.raises(WorkflowForbiddenError):
        world.workflows.create_workflow(
            lambda: DIRECTOR, name="Refresh", use_case="Refresh", country="SG"
        )
    created = world.workflows.create_workflow(
        lambda: HR, name="Refresh", use_case="Refresh", country="SG"
    )
    assert created.versions == () and created.stored_active_version == 0
    assert world.workflows.startable_workflows(ONBOARDER) == []
    empty = world.create((), workflow_id=created.workflow_id)
    report = world.governance.validate(
        HR, created.workflow_id, empty.proposal_id, ValidateProposalRequest()
    )
    assert not report.valid and report.issues[0].code == "WORKFLOW_PROPOSAL_EMPTY"
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.submit(empty)
    assert code(refused) == "WORKFLOW_PROPOSAL_EMPTY"
    assert world.workflows.startable_workflows(ONBOARDER) == []
    with pytest.raises(Exception, match="WORKFLOW_USE_CASE_RESERVED|Onboarding"):
        world.workflows.create_workflow(
            lambda: HR, name="X", use_case=ONBOARDING_USE_CASE, country="SG"
        )


def test_inbox_and_comparison_are_for_the_director():
    world = World()
    pending = world.submit(world.create())
    (item,) = world.governance.approvals_inbox(DIRECTOR).items
    assert item.proposal.proposal_id == pending.proposal_id and item.proposal.can_decide
    assert item.permanent_obligation_count == 2 and item.changes.stages_added == 1
    comparison = world.governance.comparison(DIRECTOR, ONBOARDING_WORKFLOW_ID, pending.proposal_id)
    assert {item.key for item in comparison.permanent_obligations} == {SIGNATORY, FULL_NAME}
    assert comparison.permanent_obligation_warning.startswith("Once approved")
    assert comparison.validation.valid and comparison.locked_stages
    assert comparison.affected_cases.open_runs_on_active_version == 0
    with pytest.raises(WorkflowForbiddenError):
        world.governance.comparison(HR, ONBOARDING_WORKFLOW_ID, pending.proposal_id)
    with pytest.raises(WorkflowGovernanceError) as missing:
        world.governance.comparison(DIRECTOR, ONBOARDING_WORKFLOW_ID, str(uuid4()))
    assert code(missing) == "WORKFLOW_PROPOSAL_NOT_FOUND" and missing.value.status == 404


# --- Availability --------------------------------------------------------------------


def unmigrated_world() -> World:
    world = World.__new__(World)
    world.repository = InMemoryWorkflowDefinitionRepository()
    world.repository.create(  # a P2-0 document (no migration marker)
        WorkflowDefinition(
            workflow_id=ONBOARDING_WORKFLOW_ID,
            name="Corporate onboarding",
            use_case=ONBOARDING_USE_CASE,
            country="Singapore",
            created_at=NOW,
            updated_at=NOW,
        )
    )
    world.runs = InMemoryWorkflowRunRepository()
    world.cases = Cases()
    world.workflows = WorkflowManagementService(
        definitions=world.repository, runs=world.runs, cases=world.cases, clock=lambda: NOW
    )
    world.governance = WorkflowGovernanceService(
        repository=world.repository, runs=world.runs, lock=world.workflows.definition_lock
    )
    return world


def test_an_unmigrated_store_refuses_every_mutation_and_reads_show_no_governance():
    world = unmigrated_world()
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.create()
    assert code(refused) == "WORKFLOW_GOVERNANCE_NOT_MIGRATED" and refused.value.status == 503
    definition, view = world.governance.get_workflow(HR, ONBOARDING_WORKFLOW_ID)
    assert view is None and definition.workflow_id == ONBOARDING_WORKFLOW_ID
    with pytest.raises(WorkflowGovernanceNotMigratedError):
        world.workflows.create_workflow(lambda: HR, name="R", use_case="R", country="SG")
    assert [item.workflow_id for item in world.repository.list()] == [ONBOARDING_WORKFLOW_ID]


def test_history_failures_are_503_and_ambiguous_outcomes_are_never_retried():
    world = World()

    def unavailable(*_args: Any, **_kwargs: Any) -> int:
        raise WorkflowHistoryUnavailableError

    drain = world.repository.drain_outbox
    world.repository.drain_outbox = unavailable  # type: ignore[method-assign]
    with pytest.raises(WorkflowGovernanceError) as history:
        world.create()
    assert code(history) == "WORKFLOW_HISTORY_UNAVAILABLE" and history.value.status == 503
    world.repository.drain_outbox = drain  # type: ignore[method-assign]

    calls: list[int] = []

    def ambiguous(*_args: Any, **_kwargs: Any) -> Any:
        calls.append(1)
        raise PersistenceOutcomeAmbiguousError

    world.repository.write_governance = ambiguous  # type: ignore[method-assign]
    with pytest.raises(PersistenceOutcomeAmbiguousError):
        world.create()
    assert calls == [1]

    blocked = World(startup=GovernanceStartup(available=False, blocked={}))
    with pytest.raises(WorkflowGovernanceError) as down:
        blocked.create()
    assert code(down) == "WORKFLOW_HISTORY_UNAVAILABLE"
    _definition, view = blocked.governance.get_workflow(HR, ONBOARDING_WORKFLOW_ID)
    assert view is not None and not view.can_create_proposal  # reads still work


def test_a_nonce_only_conflict_is_retried_once_inside_the_lock():
    world = World()
    repo = world.repository
    original = repo.write_governance
    calls: list[int] = []

    def concurrent_drain(definition: Any, governance: Any, **kwargs: Any) -> Any:
        calls.append(1)
        if len(calls) == 1:
            # A concurrent housekeeping write rotated the nonce and kept the revision.
            current = repo._items[ONBOARDING_WORKFLOW_ID]  # noqa: SLF001
            repo._items[ONBOARDING_WORKFLOW_ID] = current.model_copy(  # noqa: SLF001
                update={"write_nonce": "f" * 32}
            )
            raise PersistenceConflictError
        return original(definition, governance, **kwargs)

    repo.write_governance = concurrent_drain  # type: ignore[method-assign]
    assert world.create().state == ProposalState.DRAFT
    assert len(calls) == 2

    calls.clear()

    def revision_moved(*_args: Any, **_kwargs: Any) -> Any:
        calls.append(1)
        raise PersistenceConflictError

    repo.write_governance = revision_moved  # type: ignore[method-assign]
    with pytest.raises(WorkflowConflictError):
        world.governance.withdraw_proposal(
            lambda: HR,
            ONBOARDING_WORKFLOW_ID,
            world.state().governance.open_proposal.proposal_id,
            WithdrawProposalRequest(
                expected_workflow_revision=world.revision(), expected_proposal_revision=1
            ),
        )
    assert calls == [1]  # the nonce did not move, so the client's 409 is not retried


def test_startup_migrates_memory_stores_only_and_fails_closed():
    memory = unmigrated_world()
    assert start_governance(memory.repository, memory_mode=True, now=NOW).available
    assert memory.repository.get_governed(ONBOARDING_WORKFLOW_ID).governance.migrated

    mongo_like = unmigrated_world()
    startup = start_governance(mongo_like.repository, memory_mode=False, now=NOW)
    assert startup.available and startup.blocked == {}  # "not migrated" is not a block
    assert not mongo_like.repository.get_governed(ONBOARDING_WORKFLOW_ID).governance.migrated

    broken = World()

    def fail() -> Any:
        raise WorkflowHistoryUnavailableError

    broken.repository.verify_governance_state = fail  # type: ignore[method-assign]
    assert not start_governance(broken.repository, memory_mode=True, now=NOW).available


# --- Publication report and the send hold --------------------------------------------


def _entry(*, writes: tuple[str, ...] = (), claim: Any = None) -> Any:
    return SimpleNamespace(
        attempted_operations=tuple(SimpleNamespace(value=item) for item in writes),
        workflow_dispatch=claim,
    )


def _claim(state: WorkflowDispatchState, version: int, lease: timedelta) -> Any:
    return SimpleNamespace(state=state, version=version, lease_until=NOW + lease, first_write=None)


def test_the_publication_report_counts_case_ledger_records_only():
    rows = [
        (uuid4(), (_entry(writes=("SEARCH", "SHELL")),)),
        (uuid4(), (_entry(claim=_claim(WorkflowDispatchState.AUTHORISED, 0, -timedelta(1))),)),
        (uuid4(), (_entry(claim=_claim(WorkflowDispatchState.TENTATIVE, 0, timedelta(60))),)),
        (uuid4(), (_entry(claim=_claim(WorkflowDispatchState.TENTATIVE, 0, -timedelta(60))),)),
        (uuid4(), (_entry(writes=("SEARCH",)),)),
    ]
    world = World(ledger=lambda: rows)
    report = world.decide(world.submit(world.create())).publication_report
    assert report is not None and report.published_version == 1
    assert report.cases_past_first_write_under_earlier_version == 1
    assert report.cases_authorised_under_earlier_version == 1
    assert report.cases_possibly_authorised == 1  # live TENTATIVE only

    def failing() -> Any:
        raise RuntimeError("ledger down")

    failed = World(ledger=failing)
    decision = failed.decide(failed.submit(failed.create()))
    assert decision.published_version == 1 and decision.publication_report is None


def test_after_publication_a_new_onboarding_case_is_held_until_the_stage_is_confirmed():
    world = World()
    case_id = world.cases.case.case_id
    assert world.workflows.send_hold_code(case_id) is None
    world.decide(world.submit(world.create()))

    assert world.workflows.send_hold_code(case_id) == HOLD_INCOMPLETE
    run = world.workflows.case_view(world.cases.case).onboarding  # type: ignore[arg-type]
    assert run is not None and run.workflow_version == 1
    saved = world.workflows.save_answers(
        lambda: ONBOARDER,
        case_id=case_id,
        run_id=run.run_id,
        stage_id="signatory",
        expected_revision=run.revision,
        values={"full-name": "Synthetic Signatory"},
    )
    world.workflows.confirm_stage(
        lambda: ONBOARDER,
        case_id=case_id,
        run_id=run.run_id,
        stage_id="signatory",
        expected_revision=saved.revision,
    )
    assert world.workflows.send_hold_code(case_id) is None


def test_a_failure_while_counting_the_report_never_fails_the_committed_decision():
    def raising_bucket() -> Any:
        yield (uuid4(), (SimpleNamespace(attempted_operations=None, workflow_dispatch=None),))

    world = World(ledger=raising_bucket)  # has_write_marker raises on this row
    decision = world.decide(world.submit(world.create()))
    assert decision.published_version == 1 and decision.publication_report is None
    assert world.state().definition.latest_version == 1


def test_one_unreadable_workflow_never_fails_the_approval_inbox():
    world = World()
    world.decide(world.submit(world.create()))  # onboarding version 1 is now active
    pending = world.submit(world.create((STAGE,)))  # a second, identical pending proposal
    refresh = world.workflows.create_workflow(
        lambda: HR, name="Refresh", use_case="Refresh", country="SG"
    )
    other_stage = STAGE.model_copy(update={"after_node_id": None})
    other = world.submit(world.create((other_stage,), workflow_id=refresh.workflow_id))
    # The active onboarding version can no longer be read (hot copy and cold copy gone).
    repo = world.repository
    current = repo._items[ONBOARDING_WORKFLOW_ID]  # noqa: SLF001
    repo._items[ONBOARDING_WORKFLOW_ID] = current.model_copy(update={"versions": ()})  # noqa: SLF001
    repo.get_version = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    items = world.governance.approvals_inbox(DIRECTOR).items
    assert [item.workflow_id for item in items] == [refresh.workflow_id]
    assert items[0].proposal.proposal_id == other.proposal_id
    with pytest.raises(WorkflowGovernanceError) as comparison:
        world.governance.comparison(DIRECTOR, ONBOARDING_WORKFLOW_ID, pending.proposal_id)
    assert code(comparison) == "WORKFLOW_HISTORY_UNAVAILABLE"
    with pytest.raises(WorkflowGovernanceError) as decision:
        world.decide(pending, acks=())
    assert code(decision) == "WORKFLOW_HISTORY_UNAVAILABLE"


def test_a_role_revoked_mid_request_is_refused_inside_the_lock_and_writes_nothing():
    world = World()
    lock = world.workflows.definition_lock
    owned: list[bool] = []
    reads: list[bool] = []

    def revoked() -> AuthenticatedActor:
        owned.append(lock._is_owned())  # type: ignore[attr-defined]  # noqa: SLF001
        return ONBOARDER  # the HR role was removed after the request was accepted

    original = world.repository.get_governed

    def spy(workflow_id: str) -> Any:
        reads.append(True)
        return original(workflow_id)

    before = world.state()
    world.repository.get_governed = spy  # type: ignore[method-assign]
    with pytest.raises(WorkflowForbiddenError):
        world.governance.create_proposal(
            revoked,
            ONBOARDING_WORKFLOW_ID,
            CreateProposalRequest(expected_workflow_revision=world.revision(), stages=(STAGE,)),
        )
    assert owned == [True] and reads == []  # refused inside the lock, before any read
    world.repository.get_governed = original  # type: ignore[method-assign]
    after = world.state()
    assert after.definition == before.definition and after.governance == before.governance

    pending = world.submit(world.create())
    with pytest.raises(WorkflowForbiddenError):  # a Director demoted to HR cannot decide
        world.decide(pending, by=actor("olivia-koh", Role.HR))
    assert world.state().governance.open_proposal.state == ProposalState.PENDING_APPROVAL
    assert world.state().definition.versions == ()
