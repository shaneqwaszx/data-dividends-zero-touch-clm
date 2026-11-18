"""Synthetic workflow simulation (ADR-017 §6, D-5; ADR-018 §7).

A fixed, code-owned catalogue of synthetic scenarios: one per selectable legal form, plus
"Legal form not verified" and "Other legal form". Simulation reads no case store, makes no
provider call and writes nothing. Each scenario's steps are resolved with the ADR-018 §3.3
rules: an item applies when its effective ``applies_to`` is ALL or names the scenario's form;
an unverified (or other) legal form gets every item; locked onboarding stages never change.
"""

from __future__ import annotations

from app.api_workflow_governance_models import (
    SimulatedStep,
    SimulationLegalForm,
    SimulationOutcome,
    SimulationResult,
    SimulationScenario,
)
from app.domain.registry_legal_form import ConditionalLegalForm
from app.domain.workflow_governance import (
    CONDITIONAL_BEFORE_REGISTRY_ISSUE,
    GovernanceErrorCode,
    ProposalKind,
    proposal_content_hash,
)
from app.domain.workflows import (
    CONDITIONAL_ONBOARDING_ANCHORS,
    ONBOARDING_ANCHOR_STAGES,
    ONBOARDING_LOCKED_STAGES,
    AppliesTo,
    WorkflowStage,
)
from app.services.workflow_applicability import resolve_stages as _resolve_for_run
from app.services.workflow_management import stage_blocks_send

MAX_SUMMARY = 240
# ADR-018 §3.2/B5: neither form is registry-bound, so every conditional item applies.
_UNVERIFIED_FORMS: frozenset[str] = frozenset({"UNVERIFIED", "OTHER"})
_FORM_LABELS: dict[str, str] = {
    "COMPANY": "company",
    "BUSINESS_PARTNERSHIP": "business partnership",
    "LLP": "limited liability partnership",
    "LP": "limited partnership",
    "GOVERNMENT": "government entity",
}
_UNCONDITIONAL_NOTE = (
    "Synthetic scenario; no step depends on legal form, so every scenario gets these steps."
)

_CATALOGUE: tuple[SimulationScenario, ...] = (
    SimulationScenario(
        scenario_id="synthetic-company",
        label="Synthetic company",
        description="A synthetic Singapore company used only for simulation.",
        legal_form=ConditionalLegalForm.COMPANY.value,
    ),
    SimulationScenario(
        scenario_id="synthetic-llp",
        label="Synthetic limited liability partnership",
        description="A synthetic Singapore limited liability partnership used only for simulation.",
        legal_form=ConditionalLegalForm.LLP.value,
    ),
    SimulationScenario(
        scenario_id="synthetic-lp",
        label="Synthetic limited partnership",
        description="A synthetic Singapore limited partnership used only for simulation.",
        legal_form=ConditionalLegalForm.LP.value,
    ),
    SimulationScenario(
        scenario_id="synthetic-business-partnership",
        label="Synthetic business partnership",
        description="A synthetic Singapore business partnership used only for simulation.",
        legal_form=ConditionalLegalForm.BUSINESS_PARTNERSHIP.value,
    ),
    SimulationScenario(
        scenario_id="synthetic-government",
        label="Synthetic government entity",
        description=(
            "A synthetic Singapore government entity used only for simulation, shown as if its "
            "legal form were verified. A real government case is not yet verified, so it gets "
            "every conditional step."
        ),
        legal_form=ConditionalLegalForm.GOVERNMENT.value,
    ),
    SimulationScenario(
        scenario_id="synthetic-unverified",
        label="Legal form not verified",
        description=(
            "A synthetic entity whose legal form is not verified, used only for simulation. "
            "Every conditional step and field applies."
        ),
        legal_form="UNVERIFIED",
    ),
    SimulationScenario(
        scenario_id="synthetic-other",
        label="Other legal form",
        description=(
            "A synthetic entity with another legal form, used only for simulation. It is "
            "treated as not verified, so every conditional step and field applies."
        ),
        legal_form="OTHER",
    ),
)
_BY_ID = {scenario.scenario_id: scenario for scenario in _CATALOGUE}
_ANCHOR_IDS = frozenset(node_id for node_id, _ in ONBOARDING_ANCHOR_STAGES)


class SimulationInputError(ValueError):
    """Raised for an unknown scenario or unplaceable content; the service maps the code."""

    def __init__(self, message: str) -> None:
        super().__init__(GovernanceErrorCode.PROPOSAL_INVALID.value)
        self.code = GovernanceErrorCode.PROPOSAL_INVALID.value
        self.public_message = message


def scenarios() -> tuple[SimulationScenario, ...]:
    return _CATALOGUE


def _applies(applies_to: AppliesTo | None, form: SimulationLegalForm) -> bool:
    """ADR-018 §3.3: ALL applies; an unverified basis applies everything; else form in set."""

    if applies_to is None or form in _UNVERIFIED_FORMS:
        return True
    return ConditionalLegalForm(form) in applies_to


def resolve_stages(
    stages: tuple[WorkflowStage, ...], form: SimulationLegalForm
) -> tuple[WorkflowStage, ...]:
    """The resolved stage copy for one synthetic legal form (ADR-018 3.3). Pure.

    Delegates to the run evaluator's single rule (``workflow_applicability.resolve_stages``),
    so simulation and real runs can never diverge. UNVERIFIED and OTHER map to the
    unverified basis (None), which receives every condition.
    """

    legal_form = None if form in _UNVERIFIED_FORMS else ConditionalLegalForm(form)
    return _resolve_for_run(stages, legal_form)


def _added_step(stage: WorkflowStage) -> SimulatedStep:
    return SimulatedStep(
        node_id=stage.stage_id,
        name=stage.name,
        added=True,
        blocks_send=stage_blocks_send(stage),
        required_field_labels=tuple(field.label for field in stage.fields if field.required),
    )


def _locked_step(node_id: str, label: str) -> SimulatedStep:
    return SimulatedStep(node_id=node_id, name=label, added=False, blocks_send=False)


def _check_placement(stages: tuple[WorkflowStage, ...], *, is_onboarding: bool) -> None:
    """Refuse unplaceable content on the unresolved candidate, so no scenario hides it."""

    if not is_onboarding:
        if any(stage.after_node_id is not None for stage in stages):
            raise SimulationInputError("Only onboarding stages follow an existing stage.")
        return
    if any(stage.after_node_id not in _ANCHOR_IDS for stage in stages):
        raise SimulationInputError("Choose which onboarding stage each added stage follows.")
    if any(
        stage.is_conditional and stage.after_node_id not in CONDITIONAL_ONBOARDING_ANCHORS
        for stage in stages
    ):
        raise SimulationInputError(CONDITIONAL_BEFORE_REGISTRY_ISSUE)


def _steps(stages: tuple[WorkflowStage, ...], *, is_onboarding: bool) -> tuple[SimulatedStep, ...]:
    if not is_onboarding:
        return tuple(_added_step(stage) for stage in stages)
    steps: list[SimulatedStep] = []
    for node_id, label in ONBOARDING_ANCHOR_STAGES:
        steps.append(_locked_step(node_id, label))
        steps.extend(_added_step(stage) for stage in stages if stage.after_node_id == node_id)
    final_id, final_label = ONBOARDING_LOCKED_STAGES[-1]
    steps.append(_locked_step(final_id, final_label))
    return tuple(steps)


def _counted(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _form_note(
    stages: tuple[WorkflowStage, ...],
    resolved: tuple[WorkflowStage, ...],
    form: SimulationLegalForm,
) -> str:
    """The legal-form-specific outcome, stated from the resolution actually applied."""

    if not any(stage.is_conditional for stage in stages):
        return _UNCONDITIONAL_NOTE
    if form == "UNVERIFIED":
        return "Legal form not verified, so every conditional step and field applies."
    if form == "OTHER":
        return "Other legal form is treated as not verified, so every conditional step applies."
    kept = {stage.stage_id: stage for stage in resolved}
    left_out_stages = sum(1 for stage in stages if stage.stage_id not in kept)
    left_out_fields = sum(
        len(stage.fields) - len(kept[stage.stage_id].fields)
        for stage in stages
        if stage.stage_id in kept
    )
    label = _FORM_LABELS[form]
    if not left_out_stages and not left_out_fields:
        return f"Synthetic verified {label}: every conditional step and field applies."
    parts = []
    if left_out_stages:
        parts.append(_counted(left_out_stages, "step"))
    if left_out_fields:
        parts.append(_counted(left_out_fields, "field"))
    return f"Synthetic verified {label}: {' and '.join(parts)} for other legal forms left out."


def _summary(steps: tuple[SimulatedStep, ...], note: str, *, is_onboarding: bool) -> str:
    blocking = [step for step in steps if step.added and step.blocks_send]
    if not is_onboarding:
        if not blocking:
            lead = "No stage has a required field, so nothing must be confirmed."
        elif len(blocking) == 1:
            lead = f"The workflow completes once '{blocking[0].name}' is confirmed."
        else:
            lead = f"The workflow completes once {len(blocking)} required stages are confirmed."
    elif not blocking:
        lead = "No added stage holds the send."
    elif len(blocking) == 1:
        lead = f"The send is held until '{blocking[0].name}' is confirmed."
    else:
        lead = f"The send is held until {len(blocking)} added required stages are confirmed."
    text = f"{lead} {note}"
    return text if len(text) <= MAX_SUMMARY else text[: MAX_SUMMARY - 1] + "…"


def _selected(scenario_ids: tuple[str, ...]) -> tuple[SimulationScenario, ...]:
    if not scenario_ids:
        return _CATALOGUE
    unknown = [item for item in scenario_ids if item not in _BY_ID]
    if unknown:
        raise SimulationInputError("Choose scenarios from the synthetic catalogue.")
    return tuple(_BY_ID[item] for item in dict.fromkeys(scenario_ids))


def _outcome(
    scenario: SimulationScenario, stages: tuple[WorkflowStage, ...], *, is_onboarding: bool
) -> SimulationOutcome:
    resolved = resolve_stages(stages, scenario.legal_form)
    steps = _steps(resolved, is_onboarding=is_onboarding)
    note = _form_note(stages, resolved, scenario.legal_form)
    return SimulationOutcome(
        scenario=scenario,
        steps=steps,
        held_before_send=is_onboarding and any(step.added and step.blocks_send for step in steps),
        summary=_summary(steps, note, is_onboarding=is_onboarding),
    )


def simulate(
    stages: tuple[WorkflowStage, ...],
    *,
    is_onboarding: bool,
    scenario_ids: tuple[str, ...],
) -> SimulationResult:
    """Run the candidate against synthetic scenarios. Empty ``scenario_ids`` runs them all.

    Each scenario's steps come from the candidate resolved for its legal form.
    ``held_before_send`` is True only for onboarding, when an applicable added stage blocks the
    send; a non-onboarding workflow has no send step.
    """

    selected = _selected(scenario_ids)
    _check_placement(stages, is_onboarding=is_onboarding)
    return SimulationResult(
        content_hash=proposal_content_hash(ProposalKind.CHANGE, stages),
        outcomes=tuple(
            _outcome(scenario, stages, is_onboarding=is_onboarding) for scenario in selected
        ),
    )
