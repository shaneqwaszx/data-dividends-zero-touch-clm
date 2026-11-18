"""CT-26 (ADR-018 §7): synthetic simulation resolves each scenario's steps by legal form."""

from __future__ import annotations

import ast
import builtins
import socket
from pathlib import Path

import pytest

from app.domain.registry_legal_form import ConditionalLegalForm
from app.domain.workflow_governance import (
    CONDITIONAL_BEFORE_REGISTRY_ISSUE,
    ProposalKind,
    proposal_content_hash,
)
from app.domain.workflows import (
    ONBOARDING_LOCKED_STAGES,
    WorkflowField,
    WorkflowFieldKind,
    WorkflowStage,
)
from app.services import workflow_simulation
from app.services.workflow_simulation import (
    SimulationInputError,
    resolve_stages,
    scenarios,
    simulate,
)

LLP = (ConditionalLegalForm.LLP,)
LOCKED = [node_id for node_id, _ in ONBOARDING_LOCKED_STAGES]
FORM_OF = {item.scenario_id: item.legal_form for item in scenarios()}
INCLUDES_LLP_STAGE = {"LLP", "UNVERIFIED", "OTHER"}


def field(
    field_id: str,
    label: str,
    *,
    required: bool = True,
    applies_to: tuple[ConditionalLegalForm, ...] | None = None,
) -> WorkflowField:
    return WorkflowField(
        field_id=field_id,
        label=label,
        kind=WorkflowFieldKind.TEXT,
        required=required,
        applies_to=applies_to,
    )


def stage(
    stage_id: str,
    name: str,
    *fields: WorkflowField,
    after: str | None = None,
    applies_to: tuple[ConditionalLegalForm, ...] | None = None,
) -> WorkflowStage:
    return WorkflowStage(
        stage_id=stage_id, name=name, fields=fields, after_node_id=after, applies_to=applies_to
    )


LLP_STAGE = stage(
    "llp-partners",
    "LLP partner register",
    field("p", "Partners listed"),
    after="OWNERSHIP_UBO",
    applies_to=LLP,
)
ALL_STAGE = stage(
    "sanctions", "Sanctions attestation", field("by", "Screened by"), after="ADVISORY"
)


def by_form(result: object) -> dict[str, object]:
    return {o.scenario.legal_form: o for o in result.outcomes}  # type: ignore[attr-defined]


def test_llp_only_stage_is_in_llp_unverified_and_other_and_nowhere_else() -> None:
    result = simulate((LLP_STAGE,), is_onboarding=True, scenario_ids=())
    assert {o.scenario.legal_form for o in result.outcomes} == set(FORM_OF.values())
    with_stage = LOCKED[: LOCKED.index("OWNERSHIP_UBO") + 1] + ["llp-partners"]
    with_stage += LOCKED[LOCKED.index("OWNERSHIP_UBO") + 1 :]
    for outcome in result.outcomes:
        ids = [step.node_id for step in outcome.steps]
        included = outcome.scenario.legal_form in INCLUDES_LLP_STAGE
        assert ids == (with_stage if included else LOCKED)
        assert outcome.held_before_send is included
        assert [s.node_id for s in outcome.steps if not s.added] == LOCKED
        assert all(not s.blocks_send for s in outcome.steps if not s.added)
        assert ids[-1] == "FINAL_REVIEW_SEND"
        assert len(outcome.summary) <= 240
    outcomes = by_form(result)
    assert "LLP partner register" in outcomes["LLP"].summary  # type: ignore[attr-defined]
    company = outcomes["COMPANY"].summary  # type: ignore[attr-defined]
    assert "No added stage holds the send" in company and "1 step" in company
    assert "company" in company
    assert "not verified" in outcomes["UNVERIFIED"].summary  # type: ignore[attr-defined]
    assert "not verified" in outcomes["OTHER"].summary  # type: ignore[attr-defined]


def test_unconditional_stages_are_unchanged_beside_a_conditional_one() -> None:
    result = simulate((ALL_STAGE, LLP_STAGE), is_onboarding=True, scenario_ids=())
    for outcome in result.outcomes:
        added = [s.node_id for s in outcome.steps if s.added]
        expected = ["llp-partners", "sanctions"]  # OWNERSHIP_UBO precedes ADVISORY
        if outcome.scenario.legal_form not in INCLUDES_LLP_STAGE:
            expected = ["sanctions"]
        assert added == expected
        assert outcome.held_before_send  # the ALL required stage holds every scenario


def test_field_level_conditions_change_required_labels_and_holds() -> None:
    mixed = stage(
        "extra",
        "Extra checks",
        field("note", "Note", required=False),
        field("deed", "Partnership deed", applies_to=LLP),
        after="DOCUMENT_IDP",
    )
    outcomes = by_form(simulate((mixed,), is_onboarding=True, scenario_ids=()))
    llp = next(s for s in outcomes["LLP"].steps if s.added)  # type: ignore[attr-defined]
    company = next(s for s in outcomes["COMPANY"].steps if s.added)  # type: ignore[attr-defined]
    assert llp.required_field_labels == ("Partnership deed",) and llp.blocks_send
    assert company.required_field_labels == () and not company.blocks_send
    assert not outcomes["COMPANY"].held_before_send  # type: ignore[attr-defined]
    assert "1 field" in outcomes["COMPANY"].summary  # type: ignore[attr-defined]


def test_emptied_stage_is_dropped_and_zero_field_stage_follows_its_own_condition() -> None:
    emptied = stage("emptied", "Only LLP fields", field("x", "X", applies_to=LLP), after="ADVISORY")
    bare = stage("bare", "Bare ALL stage", after="ADVISORY")
    bare_llp = stage("bare-llp", "Bare LLP stage", after="ADVISORY", applies_to=LLP)
    candidate = (emptied, bare, bare_llp)
    company = resolve_stages(candidate, "COMPANY")
    assert [s.stage_id for s in company] == ["bare"]
    assert company[0] is bare
    llp = resolve_stages(candidate, "LLP")
    assert [s.stage_id for s in llp] == ["emptied", "bare", "bare-llp"]
    assert resolve_stages(candidate, "UNVERIFIED") == candidate
    assert resolve_stages(candidate, "OTHER") == candidate


def test_resolved_copy_keeps_applies_to_and_hash_covers_the_unresolved_candidate() -> None:
    mixed = stage(
        "mixed", "Mixed", field("a", "A"), field("b", "B", applies_to=LLP), after="ADVISORY"
    )
    (resolved,) = resolve_stages((mixed,), "LLP")
    assert resolved == mixed
    (narrowed,) = resolve_stages((mixed,), "LP")
    assert [f.field_id for f in narrowed.fields] == ["a"] and narrowed.applies_to is None
    (llp_copy,) = resolve_stages((LLP_STAGE,), "LLP")
    assert llp_copy.applies_to == LLP
    result = simulate((mixed,), is_onboarding=True, scenario_ids=())
    assert result.content_hash == proposal_content_hash(ProposalKind.CHANGE, (mixed,))


def test_non_onboarding_resolves_without_locked_stages() -> None:
    base = stage("base", "Base", field("x", "X"))
    llp_only = stage("llp", "LLP only", field("y", "Y"), applies_to=LLP)
    outcomes = by_form(simulate((base, llp_only), is_onboarding=False, scenario_ids=()))
    assert [s.node_id for s in outcomes["LLP"].steps] == ["base", "llp"]  # type: ignore[attr-defined]
    assert [s.node_id for s in outcomes["COMPANY"].steps] == ["base"]  # type: ignore[attr-defined]
    assert not any(o.held_before_send for o in outcomes.values())  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "anchor", ["CASE_START", "INITIAL_IDENTITY", "JURISDICTION", "GOLDTIER_SEARCH"]
)
def test_conditional_content_before_registry_is_refused(anchor: str) -> None:
    candidates = (
        stage("c", "C", field("f", "F"), after=anchor, applies_to=LLP),
        stage("c", "C", field("f", "F", applies_to=LLP), after=anchor),
    )
    for candidate in candidates:
        with pytest.raises(SimulationInputError) as caught:
            simulate((candidate,), is_onboarding=True, scenario_ids=())
        assert caught.value.public_message == CONDITIONAL_BEFORE_REGISTRY_ISSUE


def test_simulation_is_deterministic_and_does_no_io(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("simulation must do no I/O")

    candidate = (ALL_STAGE, LLP_STAGE)
    first = simulate(candidate, is_onboarding=True, scenario_ids=())
    monkeypatch.setattr(builtins, "open", refuse)
    monkeypatch.setattr(socket, "socket", refuse)
    again = simulate(candidate, is_onboarding=True, scenario_ids=())
    picked = simulate(candidate, is_onboarding=True, scenario_ids=("synthetic-llp",))
    assert first == again
    assert picked.outcomes == tuple(o for o in first.outcomes if o.scenario.legal_form == "LLP")


def test_module_imports_no_case_store_provider_or_io() -> None:
    tree = ast.parse(Path(workflow_simulation.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert imported == {
        "__future__",
        "app.api_workflow_governance_models",
        "app.domain.registry_legal_form",
        "app.domain.workflow_governance",
        "app.domain.workflows",
        "app.services.workflow_applicability",
        "app.services.workflow_management",
    }


def test_catalogue_is_synthetic_with_no_real_names() -> None:
    for item in scenarios():
        assert item.synthetic and item.scenario_id.startswith("synthetic-")
        assert "synthetic" in item.description.lower()
        assert "party_type" not in item.description
