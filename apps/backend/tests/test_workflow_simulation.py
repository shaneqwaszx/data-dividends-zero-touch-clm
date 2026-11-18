"""Synthetic workflow simulation (ADR-017 §6): ordering, holds, determinism, catalogue."""

from __future__ import annotations

import pytest

from app.domain.registry_legal_form import ConditionalLegalForm, RegistryLegalForm
from app.domain.workflow_governance import ProposalKind, proposal_content_hash
from app.domain.workflows import (
    ONBOARDING_ANCHOR_STAGES,
    ONBOARDING_LOCKED_STAGES,
    WorkflowField,
    WorkflowFieldKind,
    WorkflowStage,
)
from app.services.workflow_simulation import SimulationInputError, scenarios, simulate


def field(field_id: str, label: str, *, required: bool = True) -> WorkflowField:
    return WorkflowField(
        field_id=field_id, label=label, kind=WorkflowFieldKind.TEXT, required=required
    )


def stage(
    stage_id: str, name: str, *fields: WorkflowField, after: str | None = None
) -> WorkflowStage:
    return WorkflowStage(stage_id=stage_id, name=name, fields=fields, after_node_id=after)


BLOCKING = stage("sanctions", "Sanctions attestation", field("by", "Screened by"), after="ADVISORY")
EARLY = stage("early", "Early note", field("n", "Note", required=False), after="CASE_START")
SECOND = stage("second", "Second check", field("s", "Checked"), after="ADVISORY")


def test_catalogue_is_fixed_synthetic_and_uses_registry_legal_forms() -> None:
    # ADR-018 §7 (M3): one scenario per selectable legal form, plus UNVERIFIED and OTHER.
    items = scenarios()
    assert len(items) == len(ConditionalLegalForm) + 2
    assert items == scenarios()
    assert all(item.synthetic for item in items)
    forms = [item.legal_form for item in items]
    assert len(set(forms)) == len(forms)
    assert set(forms) == {form.value for form in ConditionalLegalForm} | {"UNVERIFIED", "OTHER"}
    assert set(forms) <= {form.value for form in RegistryLegalForm} | {"UNVERIFIED"}
    assert all("synthetic" in item.description.lower() for item in items)


def test_onboarding_interleaves_added_stages_after_their_anchors_and_send_is_last() -> None:
    result = simulate((SECOND, EARLY, BLOCKING), is_onboarding=True, scenario_ids=())
    steps = result.outcomes[0].steps
    ids = [step.node_id for step in steps]
    locked = [node_id for node_id, _ in ONBOARDING_LOCKED_STAGES]
    assert [i for i in ids if i in locked] == locked
    assert ids[-1] == "FINAL_REVIEW_SEND"
    assert ids[ids.index("CASE_START") + 1] == "early"
    advisory = ids.index("ADVISORY")
    assert ids[advisory + 1 : advisory + 3] == ["second", "sanctions"]  # candidate order
    assert len(steps) == len(ONBOARDING_LOCKED_STAGES) + 3
    added = {step.node_id: step for step in steps if step.added}
    assert added["sanctions"].blocks_send and not added["early"].blocks_send
    assert added["sanctions"].required_field_labels == ("Screened by",)
    assert added["early"].required_field_labels == ()
    assert all(not step.blocks_send for step in steps if not step.added)


def test_held_before_send_only_when_an_added_stage_blocks_the_send() -> None:
    held = simulate((BLOCKING,), is_onboarding=True, scenario_ids=())
    assert all(outcome.held_before_send for outcome in held.outcomes)
    assert "Sanctions attestation" in held.outcomes[0].summary
    two = simulate((BLOCKING, SECOND), is_onboarding=True, scenario_ids=())
    assert "2 added required stages" in two.outcomes[0].summary
    free = simulate((EARLY,), is_onboarding=True, scenario_ids=())
    assert not any(outcome.held_before_send for outcome in free.outcomes)
    empty = simulate((), is_onboarding=True, scenario_ids=())
    assert [s.node_id for s in empty.outcomes[0].steps] == [
        node_id for node_id, _ in ONBOARDING_LOCKED_STAGES
    ]


def test_unconditional_content_gives_every_scenario_the_same_outcome() -> None:
    # ADR-018 §7: the M1 "does not depend on legal form" note became the truthful statement
    # that no step of this unconditional candidate depends on legal form.
    result = simulate((BLOCKING,), is_onboarding=True, scenario_ids=())
    outcomes = result.outcomes
    assert len({(o.steps, o.held_before_send, o.summary) for o in outcomes}) == 1
    assert all("no step depends on legal form" in o.summary for o in outcomes)
    assert all(len(o.summary) <= 240 for o in outcomes)


def test_non_onboarding_runs_stages_in_order_without_locked_stages_or_send() -> None:
    a = stage("a", "Alpha", field("x", "X"))
    b = stage("b", "Beta", field("y", "Y", required=False))
    result = simulate((a, b), is_onboarding=False, scenario_ids=())
    outcome = result.outcomes[0]
    assert [s.node_id for s in outcome.steps] == ["a", "b"]
    assert all(s.added for s in outcome.steps)
    assert not outcome.held_before_send
    assert "Alpha" in outcome.summary


def test_scenario_selection_order_dedupe_and_unknown_id() -> None:
    ids = tuple(item.scenario_id for item in scenarios())
    picked = simulate((BLOCKING,), is_onboarding=True, scenario_ids=(ids[1], ids[0], ids[1]))
    assert [o.scenario.scenario_id for o in picked.outcomes] == [ids[1], ids[0]]
    everything = simulate((BLOCKING,), is_onboarding=True, scenario_ids=())
    assert [o.scenario.scenario_id for o in everything.outcomes] == list(ids)
    with pytest.raises(ValueError) as caught:
        simulate((BLOCKING,), is_onboarding=True, scenario_ids=("not-a-scenario",))
    assert isinstance(caught.value, SimulationInputError)
    assert caught.value.code == "WORKFLOW_PROPOSAL_INVALID"
    assert str(caught.value) == "WORKFLOW_PROPOSAL_INVALID"


@pytest.mark.parametrize(
    ("candidate", "is_onboarding"),
    [
        (stage("x", "X", field("f", "F")), True),  # unanchored onboarding stage
        (stage("x", "X", field("f", "F"), after="FINAL_REVIEW_SEND"), True),
        (stage("x", "X", field("f", "F"), after="ADVISORY"), False),
    ],
)
def test_unplaceable_stages_are_refused(candidate: WorkflowStage, is_onboarding: bool) -> None:
    with pytest.raises(SimulationInputError):
        simulate((candidate,), is_onboarding=is_onboarding, scenario_ids=())


def test_simulation_is_deterministic_and_hashes_the_candidate() -> None:
    candidate = (BLOCKING, EARLY)
    first = simulate(candidate, is_onboarding=True, scenario_ids=())
    assert first == simulate(candidate, is_onboarding=True, scenario_ids=())
    assert first.synthetic is True
    assert first.content_hash == proposal_content_hash(ProposalKind.CHANGE, candidate)
    assert len(ONBOARDING_ANCHOR_STAGES) + 1 == len(ONBOARDING_LOCKED_STAGES)
