"""Compose the read-only onboarding execution plan for the workflow designer (P1).

Inputs are the static stage description, the running environment's real configuration
and the stored active onboarding version. Nothing here calls a provider, reads a case,
or writes anything.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.config import Settings
from app.domain.onboarding_execution_plan import (
    WORKFLOW_WIDE_FIXED_CONTROLS,
    WORKFLOW_WIDE_POLICY_RULE_IDS,
    FixedControl,
    PlanStage,
    RegistrySearchOrder,
    plan_stages,
)
from app.domain.target_submission import GoldTierProviderMode
from app.services.workflow_management import WorkflowManagementService, stage_blocks_send

EvidenceClass = Literal["MOCK", "PARTIAL", "LOCAL", "UNCLASSIFIED"]

# Exhaustive over the Settings literals; tests pin every value. Nothing is ever Live.
_REGISTRY_CLASS: dict[str, EvidenceClass] = {
    "mock": "MOCK",
    "api_marketplace_mock": "MOCK",
    "sandbox": "PARTIAL",
}
_IDP_CLASS: dict[str, EvidenceClass] = {"mock": "MOCK", "local_pdf_text": "LOCAL"}
_TARGET_CLASS: dict[GoldTierProviderMode, EvidenceClass] = {
    GoldTierProviderMode.MOCK: "MOCK",
    GoldTierProviderMode.SANDBOX: "PARTIAL",
}


class ProviderLane(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    lane: Literal["REGISTRY", "GOLDTIER", "IDP", "PERSISTENCE"]
    mode: str
    evidence_class: EvidenceClass


class OptionalStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_id: str
    name: str
    shown_after: str | None
    field_count: int
    required_field_count: int
    blocks_send: bool
    pauses_automation: Literal[False] = False


class OptionalSteps(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: Literal["ACTIVE", "NO_ACTIVE_WORKFLOW", "UNAVAILABLE"]
    version: int | None
    manager_enabled: bool
    enforced_at_send: bool
    explanation: str
    steps: tuple[OptionalStep, ...]


class ExecutionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    registry_search_order: RegistrySearchOrder
    order_explanation: str
    stages: tuple[PlanStage, ...]
    workflow_wide_policy_rule_ids: tuple[str, ...]
    workflow_wide_fixed_controls: tuple[FixedControl, ...]
    optional_steps: OptionalSteps
    branches_supported: Literal[False] = False
    provider_lanes: tuple[ProviderLane, ...]


class ExecutionPlanService:
    def __init__(
        self,
        *,
        settings: Settings,
        search_follows_registry: bool,
        target_provider_mode: GoldTierProviderMode,
        workflows: WorkflowManagementService,
    ) -> None:
        self._settings = settings
        self._search_follows_registry = search_follows_registry
        self._target_provider_mode = target_provider_mode
        self._workflows = workflows

    def plan(self) -> ExecutionPlan:
        order: RegistrySearchOrder = (
            "REGISTRY_THEN_SEARCH" if self._search_follows_registry else "SEARCH_THEN_REGISTRY"
        )
        explanation = (
            "This environment uses the staging identity policy: the unverified typed name is "
            "never sent, so the GoldTier Search waits for the accepted ACRA registry identity."
            if self._search_follows_registry
            else "This environment searches GoldTier first (ADR-006) when the creator supplies "
            "a legal name and country. A case created with only a UEN searches after the "
            "registry instead."
        )
        return ExecutionPlan(
            registry_search_order=order,
            order_explanation=explanation,
            stages=plan_stages(order, demo_entity_candidates=self._settings.demo_controls_enabled),
            workflow_wide_policy_rule_ids=WORKFLOW_WIDE_POLICY_RULE_IDS,
            workflow_wide_fixed_controls=WORKFLOW_WIDE_FIXED_CONTROLS,
            optional_steps=self._optional_steps(),
            provider_lanes=self._provider_lanes(),
        )

    def _optional_steps(self) -> OptionalSteps:
        active = self._workflows.active_onboarding_stages()
        enabled = self._settings.workflow_manager_enabled
        if active.state == "UNAVAILABLE":
            explanation = (
                "The workflow store cannot be read, so every send that has not started is "
                "refused (D-136 E2)."
            )
        elif active.state == "NO_ACTIVE_WORKFLOW":
            explanation = "No onboarding workflow version is active; no added stage is enforced."
        elif enabled:
            explanation = (
                "Added stages are confirmed by the RM or onboarder. Required ones must be "
                "confirmed before Final review & send; they do not pause automation."
            )
        else:
            explanation = (
                "The workflow manager is switched off, but these stored required stages are "
                "still enforced at every send path and cannot be filled or confirmed until it "
                "is switched back on (D-136 E4)."
            )
        steps = tuple(
            OptionalStep(
                stage_id=stage.stage_id,
                name=stage.name,
                shown_after=stage.after_node_id,
                field_count=len(stage.fields),
                required_field_count=sum(1 for field in stage.fields if field.required),
                blocks_send=stage_blocks_send(stage),
            )
            for stage in active.stages
        )
        return OptionalSteps(
            state=active.state,
            version=active.version,
            manager_enabled=enabled,
            enforced_at_send=active.state != "NO_ACTIVE_WORKFLOW",
            explanation=explanation,
            steps=steps,
        )

    def _provider_lanes(self) -> tuple[ProviderLane, ...]:
        settings = self._settings
        return (
            ProviderLane(
                lane="REGISTRY",
                mode=settings.acra_connector_mode,
                evidence_class=_REGISTRY_CLASS.get(settings.acra_connector_mode, "UNCLASSIFIED"),
            ),
            ProviderLane(
                lane="GOLDTIER",
                mode=self._target_provider_mode.value,
                evidence_class=_TARGET_CLASS.get(self._target_provider_mode, "UNCLASSIFIED"),
            ),
            ProviderLane(
                lane="IDP",
                mode=settings.idp_connector_mode,
                evidence_class=_IDP_CLASS.get(settings.idp_connector_mode, "UNCLASSIFIED"),
            ),
            ProviderLane(
                lane="PERSISTENCE",
                mode=settings.clm_persistence_mode,
                evidence_class="LOCAL",
            ),
        )
