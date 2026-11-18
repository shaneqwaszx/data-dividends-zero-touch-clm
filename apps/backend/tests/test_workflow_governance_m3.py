"""ADR-018 M3-D: the conditional enablement gate, the service-level structure and ratchet checks
at validate/submit/approve, the emergency-fallback applicability refusal (CT-30 service half),
broadest-applicability safe targets, the applicability escalation route (CT-34/CT-38), run
views and the end-to-end Mock send with recording GoldTier counts (CT-36). Memory mode only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from test_workflow_governance_recovery import (
    DIRECTOR,
    HR,
    snapshot,
)
from test_workflow_governance_recovery import World as BaseWorld

from app.api_workflow_governance_models import (
    DecisionRequest,
    SubmitProposalRequest,
    UpdateProposalRequest,
    ValidateProposalRequest,
    WithdrawProposalRequest,
)
from app.domain.workflow_governance import (
    CONDITIONAL_BEFORE_REGISTRY_ISSUE,
    CONDITIONAL_NON_ONBOARDING_MINIMUM_ISSUE,
    CONDITIONAL_NOT_ENABLED_ISSUE,
    CONDITIONAL_OPTIONAL_TO_REQUIRED_ISSUE,
    DecisionOutcome,
    ProposalKind,
    RatchetRule,
)
from app.domain.workflows import (
    ONBOARDING_USE_CASE,
    ONBOARDING_WORKFLOW_ID,
    WorkflowDefinition,
    WorkflowStage,
    WorkflowVersion,
)
from app.persistence.workflow_governance_store import _check_baseline
from app.services import workflow_governance
from app.services.workflow_governance import WorkflowGovernanceError, WorkflowGovernanceService
from app.services.workflow_ratchet import seed_baseline
from app.services.workflow_repository import InMemoryWorkflowDefinitionRepository


def stage(
    stage_id: str,
    fields: list[dict[str, Any]],
    *,
    after: str | None = "DOCUMENT_IDP",
    **extra: Any,
) -> WorkflowStage:
    return WorkflowStage.model_validate(
        {
            "stage_id": stage_id,
            "name": f"Stage {stage_id}",
            "after_node_id": after,
            "fields": fields,
            **extra,
        }
    )


def field(field_id: str, **extra: Any) -> dict[str, Any]:
    return {"field_id": field_id, "label": f"Field {field_id}", "kind": "TEXT", **extra}


ALL_STAGE = stage("signatory", [field("full-name")])
LLP_STAGE = stage("partners", [field("partner-count")], applies_to=("LLP",))
WIDER_LLP_STAGE = stage("partners", [field("partner-count")], applies_to=("COMPANY", "LLP"))


class World(BaseWorld):
    def __init__(
        self, repository: InMemoryWorkflowDefinitionRepository | None = None, *, enabled=True
    ) -> None:
        super().__init__(repository)
        self.governance = self.service(enabled)

    def service(self, enabled: bool) -> WorkflowGovernanceService:
        return WorkflowGovernanceService(
            repository=self.repository,
            runs=self.runs,
            lock=self.workflows.definition_lock,
            clock=lambda: self.now,
            conditional_enabled=enabled,
        )

    def report(self, proposal: Any, stages: tuple[WorkflowStage, ...]) -> Any:
        return self.governance.validate(
            HR, proposal.workflow_id, proposal.proposal_id, ValidateProposalRequest(stages=stages)
        )


def legacy(*versions: tuple[WorkflowStage, ...], enabled: bool = True) -> World:
    repository = InMemoryWorkflowDefinitionRepository()
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    repository.create(
        WorkflowDefinition(
            workflow_id=ONBOARDING_WORKFLOW_ID,
            name="Corporate onboarding",
            use_case=ONBOARDING_USE_CASE,
            country="Singapore",
            versions=tuple(
                WorkflowVersion(version=n, stages=s, activated_at=moment, activated_by="olivia-koh")
                for n, s in enumerate(versions, start=1)
            ),
            created_at=moment,
            updated_at=moment,
        )
    )
    repository.migrate_to_governance(seed_baseline, now=moment)
    return World(repository, enabled=enabled)


def messages(report: Any) -> set[str]:
    return {item.message for item in report.issues}


# --- 1. The enablement gate (ADR-018 §9, B7) ------------------------------------------------


def test_the_gate_refuses_conditional_content_at_create_update_and_validate():
    world = World(enabled=False)
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.create(stages=(ALL_STAGE, LLP_STAGE))
    assert refused.value.code == "WORKFLOW_PROPOSAL_INVALID" and refused.value.status == 422
    assert refused.value.public_message == CONDITIONAL_NOT_ENABLED_ISSUE
    assert [item.message for item in refused.value.issues] == [CONDITIONAL_NOT_ENABLED_ISSUE]
    draft = world.create(stages=(ALL_STAGE,))  # unconditional content is unaffected
    assert CONDITIONAL_NOT_ENABLED_ISSUE in messages(world.report(draft, (ALL_STAGE, LLP_STAGE)))
    assert world.report(draft, (ALL_STAGE,)).valid
    with pytest.raises(WorkflowGovernanceError) as edit:
        world.governance.update_proposal(
            lambda: HR,
            ONBOARDING_WORKFLOW_ID,
            draft.proposal_id,
            UpdateProposalRequest(
                expected_workflow_revision=world.revision(),
                expected_proposal_revision=draft.revision,
                stages=(ALL_STAGE, LLP_STAGE),
            ),
        )
    assert edit.value.public_message == CONDITIONAL_NOT_ENABLED_ISSUE


def test_the_gate_refuses_submit_and_decide_too():
    world = World(enabled=True)
    pending = world.submit(world.create(stages=(ALL_STAGE, LLP_STAGE)))
    acks = tuple(
        item.key
        for item in world.governance.comparison(
            DIRECTOR, ONBOARDING_WORKFLOW_ID, pending.proposal_id
        ).permanent_obligations
    )
    world.governance = world.service(False)  # the gate is off at the next startup
    with pytest.raises(WorkflowGovernanceError) as decided:
        world.governance.decide(
            lambda: DIRECTOR,
            ONBOARDING_WORKFLOW_ID,
            pending.proposal_id,
            DecisionRequest(
                outcome=DecisionOutcome.APPROVE,
                reason="Approved for the gate test.",
                expected_workflow_revision=world.revision(),
                expected_proposal_revision=pending.revision,
                content_hash=pending.content_hash,
                acknowledged_permanent_obligations=acks,
            ),
        )
    assert decided.value.public_message == CONDITIONAL_NOT_ENABLED_ISSUE
    other = World(enabled=True)
    draft = other.create(stages=(ALL_STAGE, LLP_STAGE))
    report = other.report(draft, draft.stages)
    other.governance = other.service(False)
    with pytest.raises(WorkflowGovernanceError) as submitted:
        other.governance.submit_proposal(
            lambda: HR,
            ONBOARDING_WORKFLOW_ID,
            draft.proposal_id,
            SubmitProposalRequest(
                expected_workflow_revision=other.revision(),
                expected_proposal_revision=draft.revision,
                content_hash=report.content_hash,
            ),
        )
    assert submitted.value.public_message == CONDITIONAL_NOT_ENABLED_ISSUE


# --- 2. Structure and ratchet checks run at validate, submit and approve ----------------------


def test_onboarding_conditions_only_from_registry_verification_onwards():
    world = World()
    draft = world.create(stages=(ALL_STAGE,))
    early = stage("early", [field("x")], after="GOLDTIER_SEARCH", applies_to=("LLP",))
    unanchored = stage("loose", [field("y")], after=None, applies_to=("LLP",))
    assert CONDITIONAL_BEFORE_REGISTRY_ISSUE in messages(world.report(draft, (early,)))
    assert CONDITIONAL_BEFORE_REGISTRY_ISSUE in messages(world.report(draft, (unanchored,)))
    at_registry = stage("registry", [field("z")], after="ACRA_REGISTRY", applies_to=("LLP",))
    assert world.report(draft, (at_registry,)).valid


def test_a_non_onboarding_version_keeps_an_all_stage_with_an_all_field():
    world = World()
    workflow_id = world.workflow()  # published DETAILS (all entities)
    draft = world.create(
        workflow_id, stages=(stage("only", [field("a")], after=None, applies_to=("LLP",)),)
    )
    report = world.report(draft, draft.stages)
    assert CONDITIONAL_NON_ONBOARDING_MINIMUM_ISSUE in messages(report)


def test_optional_all_to_conditional_required_and_narrowing_are_reported():
    world = World()
    optional = stage("signatory", [field("full-name"), field("notes", required=False)])
    world.publish((optional,))
    narrowed_field = stage("signatory", [field("full-name"), field("notes", applies_to=("LLP",))])
    draft = world.create(stages=(narrowed_field,))
    assert CONDITIONAL_OPTIONAL_TO_REQUIRED_ISSUE in messages(world.report(draft, draft.stages))
    narrowed_stage = stage(
        "signatory", [field("full-name"), field("notes", required=False)], applies_to=("LLP",)
    )
    report = world.report(draft, (narrowed_stage,))
    assert RatchetRule.RR_8 in {item.rule for item in report.issues}


def test_rr8_narrowing_is_refused_at_submit():
    world = World()
    world.publish((ALL_STAGE,))
    narrowed = stage("signatory", [field("full-name")], applies_to=("LLP",))
    draft = world.create(stages=(narrowed,))
    report = world.report(draft, draft.stages)
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.governance.submit_proposal(
            lambda: HR,
            ONBOARDING_WORKFLOW_ID,
            draft.proposal_id,
            SubmitProposalRequest(
                expected_workflow_revision=world.revision(),
                expected_proposal_revision=draft.revision,
                content_hash=report.content_hash,
            ),
        )
    assert refused.value.code == "WORKFLOW_REQUIRED_OBLIGATION_WEAKENED"
    assert refused.value.rule == RatchetRule.RR_8


def test_restore_and_reset_keep_the_broadest_applicability():
    # The baseline holds the broadest set ever published (here the active legacy version).
    world = legacy((ALL_STAGE, LLP_STAGE), (ALL_STAGE, WIDER_LLP_STAGE))
    proposal = world.create(kind=ProposalKind.RESTORE_VERSION, restore_target_version=1)
    partners = next(item for item in proposal.stages if item.stage_id == "partners")
    assert partners.applies_to == ("COMPANY", "LLP")  # never the narrower v1 set
    world.governance.withdraw_proposal(
        lambda: HR,
        ONBOARDING_WORKFLOW_ID,
        proposal.proposal_id,
        WithdrawProposalRequest(
            expected_workflow_revision=world.revision(),
            expected_proposal_revision=proposal.revision,
        ),
    )
    default = world.create(kind=ProposalKind.RESET_TO_DEFAULT)
    assert next(s for s in default.stages if s.stage_id == "partners").applies_to == (
        "COMPANY",
        "LLP",
    )


def _partners(baseline: Any) -> Any:
    return next(item for item in baseline.stages if item.stage_id == "partners")


def test_a_governed_broadening_publishes_and_the_store_refuses_narrowing():
    world = World()
    world.publish((ALL_STAGE, LLP_STAGE))
    world.publish((ALL_STAGE, WIDER_LLP_STAGE))
    broad = world.state().governance.required_baseline
    assert _partners(broad).applicability == ("COMPANY", "LLP")
    assert _partners(broad).fields[0].signature.applicability == ("COMPANY", "LLP")

    # Persistence defence in depth (ADR-017 2, ADR-018 4.2): broadening is accepted on a
    # publication; narrowing a stage or a field is refused even then.
    def narrowed(*, stage_level: bool) -> Any:
        partners = _partners(broad)
        first = partners.fields[0]
        signature = first.signature.model_copy(update={"applicability": ("LLP",)})
        fields = (first.model_copy(update={"signature": signature}), *partners.fields[1:])
        update = {"applicability": ("LLP",)} if stage_level else {"fields": fields}
        changed = partners.model_copy(update=update)
        return broad.model_copy(
            update={"stages": tuple(changed if s is partners else s for s in broad.stages)}
        )

    for stage_level in (True, False):
        refusals: list[str] = []
        _check_baseline(broad, narrowed(stage_level=stage_level), True, refusals.append)
        assert refusals == ["BASELINE_APPLICABILITY_NARROWED"]
    accepted: list[str] = []
    _check_baseline(narrowed(stage_level=True), broad, True, accepted.append)
    assert accepted == []


# --- CT-30 service half: an emergency fallback never broadens or adds conditions ---------------


def test_a_fallback_that_would_broaden_applicability_is_refused():
    world = legacy((ALL_STAGE, stage("partners", [field("partner-count")])), (ALL_STAGE, LLP_STAGE))
    before = snapshot(world)
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.fallback(target="VERSION", target_version=1)
    assert refused.value.code == "WORKFLOW_PROPOSAL_INVALID"
    assert snapshot(world) == before


def test_a_fallback_that_would_add_a_conditional_obligation_is_refused():
    world = legacy((ALL_STAGE, LLP_STAGE), (ALL_STAGE,))
    before = snapshot(world)
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.fallback(target="VERSION", target_version=1)
    assert {item.stage_id for item in refused.value.issues} == {"partners"}
    assert snapshot(world) == before


def test_the_backstop_refuses_a_stage_only_broadening(monkeypatch):
    # Only the stage's own applicability broadens; its required field stays LLP-only.
    narrow = stage("partners", [field("partner-count", applies_to=("LLP",))], applies_to=("LLP",))
    wide = stage(
        "partners", [field("partner-count", applies_to=("LLP",))], applies_to=("COMPANY", "LLP")
    )
    world = legacy((ALL_STAGE, wide), (ALL_STAGE, narrow))
    # Prove the backstop alone: the permanent-obligation check reports nothing.
    monkeypatch.setattr(workflow_governance, "permanent_obligations", lambda *_a, **_k: ())
    before = snapshot(world)
    with pytest.raises(WorkflowGovernanceError):  # the safe target refuses first
        world.fallback(target="VERSION", target_version=1)
    assert snapshot(world) == before
    # The backstop on its own (QG P3-5): a would-be version whose stage applicability is
    # wider than the stored baseline is refused even when no obligation is reported.
    baseline = world.state().governance.required_baseline
    version = WorkflowVersion(
        version=3, stages=(ALL_STAGE, wide), activated_at=world.now, activated_by="olivia-koh"
    )
    with pytest.raises(WorkflowGovernanceError) as refused:
        workflow_governance._refuse_new_permanent_obligations(  # noqa: SLF001
            version.stages, None, baseline, version
        )
    assert refused.value.public_message == workflow_governance.FALLBACK_OBLIGATION_MESSAGE
    assert [item.stage_id for item in refused.value.issues] == [None]


def test_a_fallback_to_the_default_keeps_a_conditional_baseline_byte_identical():
    world = World()
    world.publish((ALL_STAGE, LLP_STAGE))
    baseline = world.state().governance.required_baseline.model_dump_json()
    assert world.fallback().published_version == 2
    assert world.state().governance.required_baseline.model_dump_json() == baseline
    published = world.state().definition.versions[-1]
    assert next(s for s in published.stages if s.stage_id == "partners").applies_to == ("LLP",)
