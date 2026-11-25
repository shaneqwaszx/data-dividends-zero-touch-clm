"""M2 workflow governance recovery and administration (contract CC-4, ADR-017 1.2, 4, 5).

Memory mode only, no Mongo and no provider: restore and reset publish the safe target,
deactivation and reactivation (with the confirmation gate), the Director's emergency
fallback and its notices, draft release and copy, the version read, and RBAC for every
new route across the five roles.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from threading import RLock
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from test_workflow_manager import enabled_app, governed_publish, login

from app.api_workflow_governance_models import (
    AcknowledgeNoticeRequest,
    CopyProposalRequest,
    CreateProposalRequest,
    DecisionRequest,
    EmergencyFallbackRequest,
    ReleaseDraftRequest,
    SubmitProposalRequest,
    UpdateProposalRequest,
    ValidateProposalRequest,
    WithdrawProposalRequest,
)
from app.domain.access import AuthenticatedActor, Role, UserProfile
from app.domain.workflow_governance import (
    MAX_UNACKNOWLEDGED_NOTICES,
    DecisionOutcome,
    GovernanceEventKind,
    GovernanceNotice,
    ProposalKind,
    ProposalOrigin,
    ProposalState,
    RatchetRule,
    VersionOrigin,
)
from app.domain.workflows import (
    ONBOARDING_USE_CASE,
    ONBOARDING_WORKFLOW_ID,
    WorkflowCaseSource,
    WorkflowDefinition,
    WorkflowStage,
    WorkflowVersion,
)
from app.services import workflow_governance
from app.services.workflow_governance import WorkflowGovernanceError, WorkflowGovernanceService
from app.services.workflow_management import (
    WorkflowConflictError,
    WorkflowForbiddenError,
    WorkflowManagementService,
    WorkflowNotFoundError,
    WorkflowValidationError,
)
from app.services.workflow_ratchet import SafeTargetError, seed_baseline
from app.services.workflow_repository import (
    InMemoryWorkflowDefinitionRepository,
    InMemoryWorkflowRunRepository,
)

NOW = datetime(2030, 6, 1, tzinfo=UTC)
REASON = "Reviewed and approved for this change."


def stage(stage_id: str, field_id: str, *, after: str | None = None) -> WorkflowStage:
    return WorkflowStage.model_validate(
        {
            "stage_id": stage_id,
            "name": f"Stage {stage_id}",
            "after_node_id": after,
            "fields": [
                {
                    "field_id": field_id,
                    "label": f"Field {field_id}",
                    "kind": "TEXT",
                    "required": True,
                },
            ],
        }
    )


SIGNATORY = stage("signatory", "full-name", after="DOCUMENT_IDP")
CONTROLLER = stage("controller", "controller-name", after="DOCUMENT_IDP")
DETAILS = stage("details", "reference")


def actor(user_id: str, role: Role, team: str | None = None) -> AuthenticatedActor:
    profile = UserProfile(user_id=user_id, display_name=user_id, role=role, team_id=team)
    return AuthenticatedActor.model_construct(profile=profile)


HR = actor("biz-ops", Role.HR)
HR_2 = actor("hr-second", Role.HR)
DIRECTOR = actor("olivia-koh", Role.DIRECTOR)
RM = actor("ethan-tan", Role.RELATIONSHIP_MANAGER, "TEAM_A")


class Cases:
    def __init__(self) -> None:
        self.case = SimpleNamespace(case_id=uuid4(), created_at=NOW + timedelta(days=1))

    def get_case(self, case_id: Any) -> Any:
        return self.case if case_id == self.case.case_id else None

    def case_lock(self, case_id: Any) -> RLock:
        return RLock()


class World:
    def __init__(self, repository: InMemoryWorkflowDefinitionRepository | None = None) -> None:
        self.now = NOW
        self.repository = repository or InMemoryWorkflowDefinitionRepository()
        self.runs = InMemoryWorkflowRunRepository()
        self.cases = Cases()
        self.workflows = WorkflowManagementService(
            definitions=self.repository,
            runs=self.runs,
            cases=self.cases,  # type: ignore[arg-type]
            case_is_onboarded=lambda _case_id: True,
            clock=lambda: self.now,
        )
        self.workflows.provision_onboarding()
        self.governance = WorkflowGovernanceService(
            repository=self.repository,
            runs=self.runs,
            lock=self.workflows.definition_lock,
            clock=lambda: self.now,
        )

    def revision(self, workflow_id: str = ONBOARDING_WORKFLOW_ID) -> int:
        definition = self.repository.get(workflow_id)
        assert definition is not None
        return definition.revision

    def state(self, workflow_id: str = ONBOARDING_WORKFLOW_ID) -> Any:
        governed = self.repository.get_governed(workflow_id)
        assert governed is not None
        return governed

    def create(self, workflow_id: str = ONBOARDING_WORKFLOW_ID, *, by=HR, **request: Any) -> Any:
        return self.governance.create_proposal(
            lambda: by,
            workflow_id,
            CreateProposalRequest(expected_workflow_revision=self.revision(workflow_id), **request),
        )

    def submit(self, proposal: Any, *, by=HR) -> Any:
        report = self.governance.validate(
            by, proposal.workflow_id, proposal.proposal_id, ValidateProposalRequest()
        )
        assert report.valid, report.issues
        return self.governance.submit_proposal(
            lambda: by,
            proposal.workflow_id,
            proposal.proposal_id,
            SubmitProposalRequest(
                expected_workflow_revision=self.revision(proposal.workflow_id),
                expected_proposal_revision=proposal.revision,
                content_hash=report.content_hash,
            ),
        )

    def decide(self, pending: Any, *, outcome=DecisionOutcome.APPROVE, by=DIRECTOR) -> Any:
        acks: tuple[Any, ...] = ()
        if outcome == DecisionOutcome.APPROVE:
            comparison = self.governance.comparison(by, pending.workflow_id, pending.proposal_id)
            acks = tuple(item.key for item in comparison.permanent_obligations)
        return self.governance.decide(
            lambda: by,
            pending.workflow_id,
            pending.proposal_id,
            DecisionRequest(
                outcome=outcome,
                reason=REASON,
                expected_workflow_revision=self.revision(pending.workflow_id),
                expected_proposal_revision=pending.revision,
                content_hash=pending.content_hash,
                acknowledged_permanent_obligations=acks,
            ),
        )

    def publish(self, stages: tuple[WorkflowStage, ...], workflow_id=ONBOARDING_WORKFLOW_ID) -> Any:
        return self.decide(self.submit(self.create(workflow_id, stages=stages)))

    def workflow(self, case_source=WorkflowCaseSource.NEW_CASE) -> str:
        created = self.workflows.create_workflow(
            lambda: HR, name="Refresh", use_case="Refresh", country="SG", case_source=case_source
        )
        self.publish((DETAILS,), created.workflow_id)
        return created.workflow_id

    def fallback(self, workflow_id=ONBOARDING_WORKFLOW_ID, *, by=DIRECTOR, **request: Any) -> Any:
        body = {"target": "DEFAULT", "reason": "Emergency rollback after an incident.", **request}
        return self.governance.emergency_fallback(
            lambda: by,
            workflow_id,
            EmergencyFallbackRequest(expected_workflow_revision=self.revision(workflow_id), **body),
        )

    def deactivate(self, workflow_id: str) -> Any:
        """The governed path: HR proposes DEACTIVATE, one Director approves (ADR-017 4)."""

        return self.decide(self.submit(self.create(workflow_id, kind=ProposalKind.DEACTIVATE)))


def code(error: pytest.ExceptionInfo[WorkflowGovernanceError]) -> str:
    return error.value.code


# --- Restore and reset publish the safe target ----------------------------------------------


def test_restore_publishes_the_safe_target_and_never_drops_a_baseline_obligation():
    world = World()
    world.publish((SIGNATORY,))
    world.publish((SIGNATORY, CONTROLLER))
    proposal = world.create(kind=ProposalKind.RESTORE_VERSION, restore_target_version=1)
    # base v1 = signatory only; the baseline keeps controller (published in v2).
    assert [item.stage_id for item in proposal.stages] == ["signatory", "controller"]
    assert not proposal.can_edit
    decision = world.decide(world.submit(proposal))
    assert decision.published_version == 3 and decision.active_version == 3
    assert decision.provenance.origin == VersionOrigin.GOVERNED_APPROVAL
    definition = world.state().definition
    assert definition.versions[-1].stages == proposal.stages


def test_restore_reads_a_cold_version():
    world = World()
    world.publish((SIGNATORY,))
    world.publish((SIGNATORY, CONTROLLER))
    # Simulate compaction: version 1 is only in the cold store now.
    stored = world.repository._items[ONBOARDING_WORKFLOW_ID]  # noqa: SLF001
    world.repository._items[ONBOARDING_WORKFLOW_ID] = stored.model_copy(  # noqa: SLF001
        update={"versions": stored.versions[1:]}
    )
    proposal = world.create(kind=ProposalKind.RESTORE_VERSION, restore_target_version=1)
    assert [item.stage_id for item in proposal.stages] == ["signatory", "controller"]
    read = world.governance.get_version(HR, ONBOARDING_WORKFLOW_ID, 1)
    assert read.version.version == 1 and not read.is_active


def test_reset_to_default_publishes_the_baseline_only():
    world = World()
    world.publish((SIGNATORY,))
    proposal = world.create(kind=ProposalKind.RESET_TO_DEFAULT)
    assert [item.stage_id for item in proposal.stages] == ["signatory"]
    decision = world.decide(world.submit(proposal))
    assert decision.published_version == 2
    assert world.state().governance.required_baseline.stages[0].stage_id == "signatory"


def test_client_stages_and_unknown_targets_are_refused_for_recovery_kinds():
    world = World()
    world.publish((SIGNATORY,))
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.create(kind=ProposalKind.RESET_TO_DEFAULT, stages=(SIGNATORY,))
    assert code(refused) == "WORKFLOW_PROPOSAL_INVALID" and refused.value.status == 422
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.create(
            kind=ProposalKind.RESTORE_VERSION, restore_target_version=1, stages=(SIGNATORY,)
        )
    assert code(refused) == "WORKFLOW_PROPOSAL_INVALID"
    with pytest.raises(WorkflowGovernanceError) as missing:
        world.create(kind=ProposalKind.RESTORE_VERSION, restore_target_version=9)
    assert code(missing) == "WORKFLOW_PROPOSAL_INVALID"
    proposal = world.create(kind=ProposalKind.RESET_TO_DEFAULT)
    with pytest.raises(WorkflowGovernanceError) as edit:
        world.governance.update_proposal(
            lambda: HR,
            ONBOARDING_WORKFLOW_ID,
            proposal.proposal_id,
            UpdateProposalRequest(
                expected_workflow_revision=world.revision(),
                expected_proposal_revision=proposal.revision,
                stages=(),
            ),
        )
    assert code(edit) == "WORKFLOW_PROPOSAL_INVALID"
    with pytest.raises(WorkflowGovernanceError) as validate:
        world.governance.validate(
            HR, ONBOARDING_WORKFLOW_ID, proposal.proposal_id, ValidateProposalRequest(stages=())
        )
    assert code(validate) == "WORKFLOW_PROPOSAL_INVALID"


def test_a_safe_target_error_is_a_422(monkeypatch):
    world = World()
    world.publish((SIGNATORY,))

    def refuse(*_args: Any) -> Any:
        raise SafeTargetError("The safe target would be too large.")

    monkeypatch.setattr(workflow_governance, "safe_target", refuse)
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.create(kind=ProposalKind.RESET_TO_DEFAULT)
    assert code(refused) == "WORKFLOW_PROPOSAL_INVALID" and refused.value.status == 422


# --- Deactivate and reactivate ----------------------------------------------------------------


@pytest.mark.parametrize("kind", [ProposalKind.DEACTIVATE, ProposalKind.REACTIVATE])
def test_onboarding_cannot_be_deactivated_or_reactivated(kind):
    world = World()
    world.publish((SIGNATORY,))
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.create(kind=kind)
    assert code(refused) == "WORKFLOW_PROPOSAL_KIND_NOT_AVAILABLE"


def test_deactivation_is_refused_while_a_confirmation_is_in_progress():
    world = World()
    workflow_id = world.workflow()
    with pytest.raises(WorkflowGovernanceError) as staged:
        world.create(workflow_id, kind=ProposalKind.DEACTIVATE, stages=())
    assert code(staged) == "WORKFLOW_PROPOSAL_INVALID"
    pending = world.submit(world.create(workflow_id, kind=ProposalKind.DEACTIVATE))
    assert pending.stages == ()
    gate = world.workflows.confirmation_gate
    with gate.confirming(workflow_id), pytest.raises(WorkflowGovernanceError) as busy:
        world.decide(pending)
    assert code(busy) == "WORKFLOW_RUN_CONFIRMATION_IN_PROGRESS" and busy.value.status == 409
    # Refused before any write: nothing changed.
    governed = world.state(workflow_id)
    assert governed.definition.stored_active_version == 1
    assert governed.governance.open_proposal.state == ProposalState.PENDING_APPROVAL
    decision = world.decide(pending)
    assert decision.proposal.state == ProposalState.APPROVED
    assert decision.published_version is None and decision.provenance is None
    assert decision.active_version == 0 and decision.publication_report is None
    governed = world.state(workflow_id)
    assert governed.definition.stored_active_version == 0
    assert governed.definition.latest_version == 1
    assert governed.governance.required_baseline.stages[0].stage_id == "details"
    kinds = [item.kind for item in governed.governance.governance_events[-2:]]
    assert kinds == [GovernanceEventKind.PROPOSAL_APPROVED, GovernanceEventKind.DEACTIVATED]
    assert governed.governance.outbox == ()  # drained after commit
    assert world.repository.verify_governance_state() == []
    assert world.repository.verify_dispatch_state() == []
    assert not world.repository.authorise_dispatch(workflow_id, 1)


def test_a_confirmation_counts_itself_and_waits_for_a_held_gate():
    world = World()
    workflow_id = world.workflow()
    gate = world.workflows.confirmation_gate
    assert world.governance._gate is gate  # noqa: SLF001 - shared through the lock
    run = world.workflows.create_workflow_case(
        lambda: RM,
        workflow_id,
        legal_name="A Pte Ltd",
        registration_id="202400001A",
        jurisdiction=None,
        priority=None,
    )
    run = world.workflows.save_workflow_case_answers(
        lambda: RM,
        workflow_id=workflow_id,
        run_id=run.run_id,
        stage_id="details",
        expected_revision=run.revision,
        values={"reference": "R-1"},
    )
    seen: list[int] = []

    def reauthorize() -> AuthenticatedActor:
        seen.append(gate.in_progress(workflow_id))
        return RM

    done = threading.Event()

    def confirm() -> None:
        world.workflows.confirm_workflow_case_stage(
            reauthorize,
            workflow_id=workflow_id,
            run_id=run.run_id,
            stage_id="details",
            expected_revision=run.revision,
        )
        done.set()

    with gate.holding(workflow_id):
        worker = threading.Thread(target=confirm)
        worker.start()
        assert not done.wait(0.2)  # cannot begin while the deactivation holds the gate
        assert gate.in_progress(workflow_id) == 0
    worker.join(5)
    # Authorized outside the gate first, then reauthorized inside it (QG P3-1).
    assert done.is_set() and seen == [0, 1] and gate.in_progress(workflow_id) == 0


def test_a_deactivated_workflow_starts_no_run_but_existing_runs_complete_and_it_reactivates():
    world = World()
    workflow_id = world.workflow()
    existing_id = world.workflow(WorkflowCaseSource.EXISTING_CASE)
    run = world.workflows.create_workflow_case(
        lambda: RM,
        workflow_id,
        legal_name="A Pte Ltd",
        registration_id="202400001A",
        jurisdiction=None,
        priority=None,
    )
    runs_before = world.runs.list_for_workflow(workflow_id)
    world.deactivate(workflow_id)
    world.deactivate(existing_id)
    assert world.runs.list_for_workflow(workflow_id) == runs_before  # no run modified
    with pytest.raises(WorkflowValidationError):
        world.workflows.create_workflow_case(
            lambda: RM,
            workflow_id,
            legal_name="B Pte Ltd",
            registration_id="202400002A",
            jurisdiction=None,
            priority=None,
        )
    with pytest.raises(WorkflowValidationError):
        world.workflows.start_run(lambda: RM, existing_id, case_id=world.cases.case.case_id)
    assert workflow_id not in {item.workflow_id for item in world.workflows.startable_workflows(RM)}
    answered = world.workflows.save_workflow_case_answers(
        lambda: RM,
        workflow_id=workflow_id,
        run_id=run.run_id,
        stage_id="details",
        expected_revision=run.revision,
        values={"reference": "R-1"},
    )
    confirmed = world.workflows.confirm_workflow_case_stage(
        lambda: RM,
        workflow_id=workflow_id,
        run_id=run.run_id,
        stage_id="details",
        expected_revision=answered.revision,
    )
    assert confirmed.is_complete
    # A CHANGE or a fallback is refused; only a reactivation applies.
    with pytest.raises(WorkflowGovernanceError) as change:
        world.create(existing_id, stages=(DETAILS,))
    assert code(change) == "WORKFLOW_PROPOSAL_KIND_NOT_AVAILABLE"
    with pytest.raises(WorkflowGovernanceError) as fallback:
        world.fallback(existing_id)
    assert code(fallback) == "WORKFLOW_PROPOSAL_KIND_NOT_AVAILABLE"
    # A reactivation must satisfy the baseline (it cannot drop the required stage).
    weaker = world.create(existing_id, kind=ProposalKind.REACTIVATE, stages=())
    report = world.governance.validate(
        HR, existing_id, weaker.proposal_id, ValidateProposalRequest()
    )
    assert not report.valid
    assert {item.rule for item in report.issues if item.rule} == {RatchetRule.RR_1}
    world.governance.withdraw_proposal(
        lambda: HR,
        existing_id,
        world.state(existing_id).governance.open_proposal.proposal_id,
        WithdrawProposalRequest(
            expected_workflow_revision=world.revision(existing_id),
            expected_proposal_revision=world.state(existing_id).governance.open_proposal.revision,
        ),
    )
    reactivate = world.create(existing_id, kind=ProposalKind.REACTIVATE)
    assert reactivate.stages == (DETAILS,)  # defaults to the latest version's stages
    decision = world.decide(world.submit(reactivate))
    assert decision.published_version == 2 and decision.active_version == 2
    kinds = [item.kind for item in world.state(existing_id).governance.governance_events]
    assert GovernanceEventKind.REACTIVATED in kinds
    assert world.repository.verify_governance_state() == []
    started = world.workflows.start_run(lambda: RM, existing_id, case_id=world.cases.case.case_id)
    assert started.workflow_version == 2


# --- Emergency fallback and notices --------------------------------------------------------


def test_emergency_fallback_is_the_directors_alone():
    world = World()
    world.publish((SIGNATORY,))
    with pytest.raises(WorkflowForbiddenError):
        world.fallback(by=HR)


def test_emergency_fallback_publishes_the_safe_target_stales_and_raises_a_notice():
    world = World()
    world.publish((SIGNATORY,))
    world.publish((SIGNATORY, CONTROLLER))
    draft = world.create(stages=(SIGNATORY, CONTROLLER))
    with pytest.raises(WorkflowGovernanceError) as missing:
        world.fallback(target="VERSION")
    assert code(missing) == "WORKFLOW_PROPOSAL_INVALID"
    result = world.fallback(target="VERSION", target_version=1)
    assert result.published_version == result.active_version == 3
    assert result.provenance.origin == VersionOrigin.EMERGENCY_FALLBACK
    assert result.provenance.approved_by is None and result.provenance.author_id is None
    assert result.provenance.activated_by == "olivia-koh"
    assert result.staled_proposal_ids == (draft.proposal_id,)
    assert result.notice.acknowledged_at is None and result.notice.raised_by == "olivia-koh"
    governed = world.state()
    # Safe target: v1 (signatory) plus the baseline obligation (controller), never weaker.
    assert [item.stage_id for item in governed.definition.versions[-1].stages] == [
        "signatory",
        "controller",
    ]
    state = governed.governance
    assert state.open_proposal is None
    stale = next(item for item in state.decided_proposals if item.proposal_id == draft.proposal_id)
    assert stale.state == ProposalState.STALE and stale.record.stale_by_version == 3
    assert stale.record.stages == draft.stages  # content kept
    kinds = [item.kind for item in state.governance_events[-4:]]
    assert kinds == [
        GovernanceEventKind.PROPOSAL_STALE,
        GovernanceEventKind.EMERGENCY_FALLBACK,
        GovernanceEventKind.VERSION_PUBLISHED,
        GovernanceEventKind.NOTICE_RAISED,
    ]
    assert state.outbox == ()  # drained after commit
    read = world.governance.get_version(DIRECTOR, ONBOARDING_WORKFLOW_ID, 3)
    assert read.is_active and read.provenance.approved_by is None
    listed = world.governance.notices(HR)
    assert [item.notice.notice_id for item in listed.items] == [result.notice.notice_id]


def test_hr_acknowledges_a_notice_and_a_director_cannot():
    world = World()
    world.publish((SIGNATORY,))
    notice = world.fallback().notice
    request = AcknowledgeNoticeRequest(
        workflow_id=ONBOARDING_WORKFLOW_ID, expected_workflow_revision=world.revision()
    )
    with pytest.raises(WorkflowForbiddenError):
        world.governance.acknowledge_notice(lambda: DIRECTOR, notice.notice_id, request)
    with pytest.raises(WorkflowNotFoundError):
        world.governance.acknowledge_notice(lambda: HR, str(uuid4()), request)
    acknowledged = world.governance.acknowledge_notice(lambda: HR, notice.notice_id, request)
    assert acknowledged.notice.acknowledged_by == "biz-ops"
    assert acknowledged.notice.acknowledged_at == NOW
    assert world.governance.notices(DIRECTOR).items == ()
    events = world.state().governance.governance_events
    assert events[-1].kind == GovernanceEventKind.NOTICE_ACKNOWLEDGED
    with pytest.raises(WorkflowConflictError):
        world.governance.acknowledge_notice(
            lambda: HR,
            notice.notice_id,
            AcknowledgeNoticeRequest(
                workflow_id=ONBOARDING_WORKFLOW_ID, expected_workflow_revision=world.revision()
            ),
        )


def test_the_64_notice_limit_refuses_a_fallback():
    world = World()
    world.publish((SIGNATORY,))
    state = world.repository._governance[ONBOARDING_WORKFLOW_ID]  # noqa: SLF001
    notices = tuple(
        GovernanceNotice(
            notice_id=str(uuid4()),
            raised_at=NOW,
            raised_by="olivia-koh",
            version=1,
            reason="An earlier emergency fallback.",
        )
        for _ in range(MAX_UNACKNOWLEDGED_NOTICES)
    )
    world.repository._governance[ONBOARDING_WORKFLOW_ID] = state.model_copy(  # noqa: SLF001
        update={"notices": notices}
    )
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.fallback()
    assert code(refused) == "WORKFLOW_NOTICES_UNACKNOWLEDGED" and refused.value.status == 409
    world.governance.acknowledge_notice(
        lambda: HR,
        notices[0].notice_id,
        AcknowledgeNoticeRequest(
            workflow_id=ONBOARDING_WORKFLOW_ID, expected_workflow_revision=world.revision()
        ),
    )
    assert world.fallback().published_version == 2


# --- Release and copy ------------------------------------------------------------------------


def release(world: World, proposal: Any, *, by=HR_2) -> Any:
    return world.governance.release_proposal(
        lambda: by,
        proposal.workflow_id,
        proposal.proposal_id,
        ReleaseDraftRequest(
            reason="The author left the team.",
            expected_workflow_revision=world.revision(proposal.workflow_id),
            expected_proposal_revision=proposal.revision,
        ),
    )


def test_release_needs_14_days_and_someone_other_than_the_author():
    world = World()
    draft = world.create(stages=(SIGNATORY,))
    world.now = NOW + timedelta(days=13, hours=23)
    with pytest.raises(WorkflowGovernanceError) as early:
        release(world, draft)
    assert code(early) == "WORKFLOW_DRAFT_NOT_RELEASABLE" and early.value.status == 409
    world.now = NOW + timedelta(days=14)
    with pytest.raises(WorkflowForbiddenError):
        release(world, draft, by=HR)  # the author withdraws instead
    with pytest.raises(WorkflowForbiddenError):
        release(world, draft, by=DIRECTOR)
    released = release(world, draft)
    assert released.state == ProposalState.WITHDRAWN and released.stages == (SIGNATORY,)
    assert released.released_by == "hr-second"
    assert released.release_reason == "The author left the team."
    entry = world.state().governance.decided_proposals[-1]
    assert entry.record.released_by == "hr-second"
    assert entry.record.release_reason == "The author left the team."
    assert world.state().governance.governance_events[-1].kind == GovernanceEventKind.DRAFT_RELEASED


def test_a_pending_proposal_is_never_released():
    world = World()
    pending = world.submit(world.create(stages=(SIGNATORY,)))
    world.now = NOW + timedelta(days=30)
    with pytest.raises(WorkflowGovernanceError) as refused:
        release(world, pending)
    assert code(refused) == "WORKFLOW_PROPOSAL_STATE_INVALID"


def copy(world: World, proposal_id: str, *, by=HR_2, workflow_id=ONBOARDING_WORKFLOW_ID) -> Any:
    return world.governance.copy_proposal(
        lambda: by,
        workflow_id,
        proposal_id,
        CopyProposalRequest(expected_workflow_revision=world.revision(workflow_id)),
    )


def test_copy_makes_a_new_draft_authored_by_the_copier():
    world = World()
    world.publish((SIGNATORY,))
    draft = world.create(stages=(SIGNATORY, CONTROLLER))
    world.now = NOW + timedelta(days=15)
    with pytest.raises(WorkflowGovernanceError) as open_:
        copy(world, draft.proposal_id)
    assert code(open_) == "WORKFLOW_PROPOSAL_OPEN"
    release(world, draft)
    with pytest.raises(WorkflowGovernanceError) as missing:
        copy(world, str(uuid4()))
    assert code(missing) == "WORKFLOW_PROPOSAL_NOT_FOUND"
    copied = copy(world, draft.proposal_id)
    assert copied.state == ProposalState.DRAFT and copied.author_id == "hr-second"
    assert copied.stages == draft.stages and copied.base_version == 1 and copied.can_edit
    record = world.state().governance.open_proposal
    assert record.copied_from == draft.proposal_id
    assert world.state().governance.governance_events[-1].kind == GovernanceEventKind.DRAFT_COPIED
    with pytest.raises(WorkflowForbiddenError):
        copy(world, draft.proposal_id, by=DIRECTOR)


def test_a_legacy_pre_governance_draft_can_be_copied_and_legacy_is_never_approved():
    repository = InMemoryWorkflowDefinitionRepository()
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    repository.create(
        WorkflowDefinition(
            workflow_id=ONBOARDING_WORKFLOW_ID,
            name="Corporate onboarding",
            use_case=ONBOARDING_USE_CASE,
            country="Singapore",
            draft_stages=(SIGNATORY, CONTROLLER),
            versions=(
                WorkflowVersion(
                    version=1, stages=(SIGNATORY,), activated_at=moment, activated_by="olivia-koh"
                ),
            ),
            created_at=moment,
            updated_at=moment,
        )
    )
    repository.migrate_to_governance(seed_baseline, now=moment)
    world = World(repository)
    (legacy,) = world.state().governance.decided_proposals
    assert legacy.origin == ProposalOrigin.PRE_GOVERNANCE_DRAFT
    copied = copy(world, legacy.proposal_id, by=HR)
    assert copied.author_id == "biz-ops" and copied.stages == (SIGNATORY, CONTROLLER)
    read = world.governance.get_version(HR, ONBOARDING_WORKFLOW_ID, 1)
    assert read.provenance.origin == VersionOrigin.PRE_GOVERNANCE_DIRECTOR_ACTIVATION
    assert read.provenance.approved_by is None and read.is_active
    with pytest.raises(WorkflowNotFoundError):
        world.governance.get_version(HR, ONBOARDING_WORKFLOW_ID, 7)


# --- Routes: shadowing and RBAC for every new route (five roles) -----------------------------


def test_fallback_notices_and_versions_over_http():
    app = enabled_app()
    director = login(app, "olivia-koh")
    governed_publish(director, ONBOARDING_WORKFLOW_ID, [SIGNATORY.model_dump(mode="json")])
    hr = login(app, "biz-ops")
    url = f"/api/workflows/{ONBOARDING_WORKFLOW_ID}"
    fallback = director.post(
        f"{url}/emergency-fallback",
        json={
            "reason": "Emergency rollback after an incident.",
            "expected_workflow_revision": director.get(url).json()["revision"],
            "target": "DEFAULT",
        },
    )
    assert fallback.status_code == 200, fallback.json()
    assert fallback.json()["provenance"]["origin"] == "EMERGENCY_FALLBACK"
    listed = hr.get("/api/workflows/notices")
    assert listed.status_code == 200 and len(listed.json()["items"]) == 1
    notice_id = listed.json()["items"][0]["notice"]["notice_id"]
    body = {
        "workflow_id": ONBOARDING_WORKFLOW_ID,
        "expected_workflow_revision": hr.get(url).json()["revision"],
    }
    assert (
        director.post(f"/api/workflows/notices/{notice_id}/acknowledge", json=body).status_code
        == 403
    )
    acknowledged = hr.post(f"/api/workflows/notices/{notice_id}/acknowledge", json=body)
    assert acknowledged.status_code == 200, acknowledged.json()
    assert acknowledged.json()["notice"]["acknowledged_by"] == "biz-ops"
    version = director.get(f"{url}/versions/2")
    assert version.status_code == 200 and version.json()["provenance"]["approved_by"] is None
    missing = director.get(f"{url}/versions/9")
    assert missing.status_code == 404 and missing.json()["detail"]["code"] == "WORKFLOW_NOT_FOUND"


MISSING = "00000000-0000-4000-8000-000000000000"
_URL = f"/api/workflows/{ONBOARDING_WORKFLOW_ID}"
_ROUTES: list[tuple[str, str, Any, set[str]]] = [
    # (method, path, body, roles that pass the capability check)
    (
        "POST",
        f"{_URL}/emergency-fallback",
        {
            "reason": "Emergency rollback test.",
            "expected_workflow_revision": 999,
            "target": "DEFAULT",
        },
        {"olivia-koh"},
    ),
    (
        "POST",
        f"{_URL}/proposals/{MISSING}/release",
        {"reason": "Released.", "expected_workflow_revision": 999, "expected_proposal_revision": 1},
        {"biz-ops"},
    ),
    (
        "POST",
        f"{_URL}/proposals/{MISSING}/copy",
        {"expected_workflow_revision": 999},
        {"biz-ops"},
    ),
    ("GET", f"{_URL}/versions/1", None, {"biz-ops", "olivia-koh"}),
    ("GET", "/api/workflows/notices", None, {"biz-ops", "olivia-koh"}),
    (
        "POST",
        f"/api/workflows/notices/{MISSING}/acknowledge",
        {"workflow_id": ONBOARDING_WORKFLOW_ID, "expected_workflow_revision": 999},
        {"biz-ops"},
    ),
]


@pytest.mark.parametrize(
    "user_id", ["maya-lim", "ethan-tan", "support-user", "biz-ops", "olivia-koh"]
)
def test_every_new_route_is_capability_checked_for_each_role(user_id):
    app = enabled_app()
    client = login(app, user_id)
    for method, path, body, allowed in _ROUTES:
        response = client.request(method, path, json=body)
        if user_id in allowed:
            assert response.status_code != 403, (method, path, response.json())
        else:
            assert response.status_code == 403, (method, path, response.json())
            assert response.json()["detail"]["code"] == "WORKFLOW_FORBIDDEN"


# --- QG notes (P3-1 gate bounded, P3-2 fallback transparency, CC-6 fields) -------------------


def test_junk_workflow_ids_never_grow_the_confirmation_gate():
    world = World()
    gate = world.workflows.confirmation_gate
    for index in range(1000):
        with pytest.raises(WorkflowNotFoundError):
            world.workflows.confirm_workflow_case_stage(
                lambda: RM,
                workflow_id=f"junk-{index}",
                run_id=uuid4(),
                stage_id="details",
                expected_revision=1,
            )
        with gate.confirming(f"direct-{index}"):
            pass
        with gate.holding(f"held-{index}"):
            pass
    assert gate.tracked() == 0


def legacy_world(*versions: tuple[WorkflowStage, ...]) -> World:
    """A migrated legacy store: the baseline is seeded from the active (last) version only."""

    repository = InMemoryWorkflowDefinitionRepository()
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    repository.create(
        WorkflowDefinition(
            workflow_id=ONBOARDING_WORKFLOW_ID,
            name="Corporate onboarding",
            use_case=ONBOARDING_USE_CASE,
            country="Singapore",
            versions=tuple(
                WorkflowVersion(
                    version=number, stages=stages, activated_at=moment, activated_by="olivia-koh"
                )
                for number, stages in enumerate(versions, start=1)
            ),
            created_at=moment,
            updated_at=moment,
        )
    )
    repository.migrate_to_governance(seed_baseline, now=moment)
    return World(repository)


def snapshot(world: World) -> tuple[Any, ...]:
    governed = world.state()
    return (
        governed.definition.revision,
        governed.definition.versions,
        governed.definition.stored_active_version,
        governed.governance.required_baseline.model_dump_json(),
        governed.governance.notices,
        # The pre-write drain may archive history (housekeeping); no event is added.
        tuple((item.sequence, item.kind) for item in governed.governance.governance_events),
    )


FALLBACK_REFUSAL = (
    "This would add a permanent obligation; propose it through normal approval instead."
)


def test_a_fallback_that_would_add_a_permanent_obligation_is_refused_and_writes_nothing():
    world = legacy_world((CONTROLLER,), (SIGNATORY,))
    before = snapshot(world)
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.fallback(target="VERSION", target_version=1)
    assert code(refused) == "WORKFLOW_PROPOSAL_INVALID" and refused.value.status == 422
    body = refused.value.body()
    assert {(item.stage_id, item.field_id) for item in body.issues} == {
        ("controller", None),
        ("controller", "controller-name"),
    }
    assert {item.message for item in body.issues} == {FALLBACK_REFUSAL}
    assert snapshot(world) == before


def test_a_fallback_to_the_default_keeps_every_obligation_and_the_baseline_identical():
    world = World()
    world.publish((SIGNATORY,))
    world.publish((SIGNATORY, CONTROLLER))
    baseline = world.state().governance.required_baseline.model_dump_json()
    result = world.fallback()
    assert result.published_version == 3
    governed = world.state()
    assert governed.governance.required_baseline.model_dump_json() == baseline
    published = governed.definition.versions[-1]
    required = {
        (item.stage_id, field.field_id)
        for item in published.stages
        for field in item.fields
        if field.required
    }
    assert required == {("signatory", "full-name"), ("controller", "controller-name")}
    event = next(
        item
        for item in governed.governance.governance_events
        if item.kind == GovernanceEventKind.EMERGENCY_FALLBACK
    )
    assert event.summary == "Emergency fallback to the default (version 3)"


def test_a_fallback_to_a_version_within_the_baseline_keeps_the_baseline():
    world = World()
    world.publish((SIGNATORY,))
    world.publish((SIGNATORY, CONTROLLER))
    baseline = world.state().governance.required_baseline.model_dump_json()
    assert world.fallback(target="VERSION", target_version=1).published_version == 3
    assert world.state().governance.required_baseline.model_dump_json() == baseline


CHOICE = WorkflowStage.model_validate(
    {
        "stage_id": "risk",
        "name": "Risk rating",
        "after_node_id": "DOCUMENT_IDP",
        "fields": [
            {
                "field_id": "rating",
                "label": "Rating",
                "kind": "CHOICE",
                "required": True,
                "options": ["Low", "High"],
            },
        ],
    }
)


def test_a_fallback_that_would_narrow_a_choice_is_refused(monkeypatch):
    # The safe target uses the baseline representatives, so narrowing cannot arise from
    # stored data today; the guard is exercised with a narrowed target directly.
    world = World()
    world.publish((CHOICE,))
    narrowed = CHOICE.model_copy(
        update={"fields": (CHOICE.fields[0].model_copy(update={"options": ("Low",)}),)}
    )
    monkeypatch.setattr(workflow_governance, "safe_target", lambda *_args: (narrowed,))
    before = snapshot(world)
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.fallback()
    assert code(refused) == "WORKFLOW_PROPOSAL_INVALID"
    assert {(item.stage_id, item.field_id) for item in refused.value.issues} == {("risk", "rating")}
    assert snapshot(world) == before


def test_the_same_obligation_is_added_through_a_proposal_and_approval():
    world = legacy_world((CONTROLLER,), (SIGNATORY,))
    decision = world.publish((SIGNATORY, CONTROLLER))  # HR proposes, a Director approves
    assert decision.published_version == 3
    stage_ids = {item.stage_id for item in world.state().governance.required_baseline.stages}
    assert stage_ids == {"signatory", "controller"}
    baseline = world.state().governance.required_baseline.model_dump_json()
    assert world.fallback(target="VERSION", target_version=1).published_version == 4
    assert world.state().governance.required_baseline.model_dump_json() == baseline


def test_cc6_fields_appear_in_route_responses():
    app = enabled_app()
    director = login(app, "olivia-koh")
    governed_publish(director, ONBOARDING_WORKFLOW_ID, [SIGNATORY.model_dump(mode="json")])
    hr = login(app, "biz-ops")
    url = f"/api/workflows/{ONBOARDING_WORKFLOW_ID}"
    restore = hr.post(
        f"{url}/proposals",
        json={
            "kind": "RESTORE_VERSION",
            "restore_target_version": 1,
            "expected_workflow_revision": hr.get(url).json()["revision"],
        },
    )
    assert restore.status_code == 201, restore.json()
    body = restore.json()
    assert body["restore_target_version"] == 1
    assert body["copied_from"] is None and body["released_by"] is None
    assert "release_reason" in body
    withdrawn = hr.post(
        f"{url}/proposals/{body['proposal_id']}/withdraw",
        json={
            "expected_workflow_revision": hr.get(url).json()["revision"],
            "expected_proposal_revision": body["revision"],
        },
    )
    assert withdrawn.status_code == 200, withdrawn.json()
    copied = hr.post(
        f"{url}/proposals/{body['proposal_id']}/copy",
        json={"expected_workflow_revision": hr.get(url).json()["revision"]},
    )
    assert copied.status_code == 201, copied.json()
    assert copied.json()["copied_from"] == body["proposal_id"]
    assert copied.json()["kind"] == "CHANGE"
