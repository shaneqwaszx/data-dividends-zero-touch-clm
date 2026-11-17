"""Synthetic workflow simulation (ADR-017 §6, D-5).

A fixed, code-owned catalogue of synthetic scenarios. Simulation reads no case store, makes
no provider call and writes nothing. In M1 an outcome does not depend on the scenario's
legal form: conditional applicability arrives with ADR-018 (M3), and each summary says so.
"""

from __future__ import annotations

from app.api_workflow_governance_models import (
    SimulatedStep,
    SimulationOutcome,
    SimulationResult,
    SimulationScenario,
)
from app.domain.registry_legal_form import RegistryLegalForm
from app.domain.workflow_governance import (
    GovernanceErrorCode,
    ProposalKind,
    proposal_content_hash,
)
from app.domain.workflows import ONBOARDING_ANCHOR_STAGES, ONBOARDING_LOCKED_STAGES, WorkflowStage
from app.services.workflow_management import stage_blocks_send

MAX_SUMMARY = 240
_M1_NOTE = "Synthetic scenario; in this release the result does not depend on legal form."

_CATALOGUE: tuple[SimulationScenario, ...] = (
    SimulationScenario(
        scenario_id="synthetic-company",
        label="Synthetic company",
        description="A synthetic Singapore company used only for simulation.",
        legal_form=RegistryLegalForm.COMPANY.value,
    ),
    SimulationScenario(
        scenario_id="synthetic-llp",
        label="Synthetic limited liability partnership",
        description="A synthetic Singapore limited liability partnership used only for simulation.",
        legal_form=RegistryLegalForm.LLP.value,
    ),
    SimulationScenario(
        scenario_id="synthetic-lp",
        label="Synthetic limited partnership",
        description="A synthetic Singapore limited partnership used only for simulation.",
        legal_form=RegistryLegalForm.LP.value,
    ),
    SimulationScenario(
        scenario_id="synthetic-business-partnership",
        label="Synthetic business partnership",
        description="A synthetic Singapore business partnership used only for simulation.",
        legal_form=RegistryLegalForm.BUSINESS_PARTNERSHIP.value,
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


def _steps(stages: tuple[WorkflowStage, ...], *, is_onboarding: bool) -> tuple[SimulatedStep, ...]:
    if not is_onboarding:
        if any(stage.after_node_id is not None for stage in stages):
            raise SimulationInputError("Only onboarding stages follow an existing stage.")
        return tuple(_added_step(stage) for stage in stages)
    if any(stage.after_node_id not in _ANCHOR_IDS for stage in stages):
        raise SimulationInputError("Choose which onboarding stage each added stage follows.")
    steps: list[SimulatedStep] = []
    for node_id, label in ONBOARDING_ANCHOR_STAGES:
        steps.append(_locked_step(node_id, label))
        steps.extend(_added_step(stage) for stage in stages if stage.after_node_id == node_id)
    final_id, final_label = ONBOARDING_LOCKED_STAGES[-1]
    steps.append(_locked_step(final_id, final_label))
    return tuple(steps)


def _summary(steps: tuple[SimulatedStep, ...], *, is_onboarding: bool) -> str:
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
    text = f"{lead} {_M1_NOTE}"
    return text if len(text) <= MAX_SUMMARY else text[: MAX_SUMMARY - 1] + "…"


def _selected(scenario_ids: tuple[str, ...]) -> tuple[SimulationScenario, ...]:
    if not scenario_ids:
        return _CATALOGUE
    unknown = [item for item in scenario_ids if item not in _BY_ID]
    if unknown:
        raise SimulationInputError("Choose scenarios from the synthetic catalogue.")
    return tuple(_BY_ID[item] for item in dict.fromkeys(scenario_ids))


def simulate(
    stages: tuple[WorkflowStage, ...],
    *,
    is_onboarding: bool,
    scenario_ids: tuple[str, ...],
) -> SimulationResult:
    """Run the candidate against synthetic scenarios. Empty ``scenario_ids`` runs them all.

    ``held_before_send`` is True only for onboarding, when an added stage blocks the send;
    a non-onboarding workflow has no send step.
    """

    selected = _selected(scenario_ids)
    steps = _steps(stages, is_onboarding=is_onboarding)
    held = is_onboarding and any(step.added and step.blocks_send for step in steps)
    summary = _summary(steps, is_onboarding=is_onboarding)
    return SimulationResult(
        content_hash=proposal_content_hash(ProposalKind.CHANGE, stages),
        outcomes=tuple(
            SimulationOutcome(
                scenario=scenario, steps=steps, held_before_send=held, summary=summary
            )
            for scenario in selected
        ),
    )
