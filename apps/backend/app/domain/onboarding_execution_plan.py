"""Read-only description of the onboarding process the backend actually runs (P1).

This module describes; it never drives execution. The orchestrator's order lives in
``AUTOMATION_STAGE_ORDER`` and ``ZeroTouchOrchestrator``; the business stages come from
``ONBOARDING_LOCKED_STAGES`` (D-123); policy rule ids come from the policy domain. Tests
pin this description to those owners, so a change there that is not reflected here
fails loudly instead of drawing a wrong diagram.

Every mandatory stage is fixed: with today's backend no mandatory stage can be moved
(P0 findings, D-135 S2). Optional added stages block the final send; they never pause
automation at their displayed anchor (D-123 W5, D-136 E1).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.domain.dashboard_attention import (
    AT_RISK_WINDOW_MS,
    INACTIVITY_MS,
    SLA_TARGET_MS,
    STALE_BLOCKER_MS,
)
from app.domain.policy import (
    ENTITY_RESOLUTION_ADDRESS_WEIGHT_ID,
    ENTITY_RESOLUTION_AMBIGUITY_MARGIN_ID,
    ENTITY_RESOLUTION_AUTO_MATCH_THRESHOLD_ID,
    ENTITY_RESOLUTION_IDENTIFIER_WEIGHT_ID,
    ENTITY_RESOLUTION_INCORPORATION_DATE_WEIGHT_ID,
    ENTITY_RESOLUTION_LEGAL_FORM_WEIGHT_ID,
    ENTITY_RESOLUTION_NAME_WEIGHT_ID,
    ENTITY_RESOLUTION_REVIEW_THRESHOLD_ID,
    GOLDTIER_ACCOUNT_ENTITY_TYPE_ID,
    GOLDTIER_BOOKING_ENTITY_ID,
    GOLDTIER_CLIENT_SEGMENT_ID,
    GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM_ID,
    GOLDTIER_KYC_CUSTOMER_TYPE_ID,
    GOLDTIER_POLICY_ID,
    GOLDTIER_PRODUCT_TYPE_ID,
    GOLDTIER_REGISTRATION_TYPE_ID,
    IDP_POLICY_ID,
    MOCK_RISK_BLOCKS_READINESS_ID,
    MOCK_RISK_HIGH_THRESHOLD_ID,
    MOCK_RISK_MEDIUM_THRESHOLD_ID,
    OWNERSHIP_CALL_BUDGET_ENABLED_ID,
    OWNERSHIP_CALL_BUDGET_MAX_ID,
    OWNERSHIP_DISCOVERY_MAX_DEPTH_ID,
    OWNERSHIP_TRACE_THRESHOLD_ID,
    UBO_ADVISORY_LIKELY_THRESHOLD_ID,
    UBO_ADVISORY_UNLIKELY_THRESHOLD_ID,
    UBO_POLICY_ID,
)
from app.domain.workflows import ONBOARDING_LOCKED_STAGES

APPROVAL_GATE_ID = "APPROVAL_GATE"
EngineStage = Literal[
    "CREATION",
    "REGISTRY",
    "GOLDTIER_SEARCH",
    "DOCUMENT",
    "OWNERSHIP",
    "READINESS",
    "MOCK_GOLDTIER",
    "NONE",
]
PrerequisiteKind = Literal["DATA", "ENGINE_ORDER"]
RegistrySearchOrder = Literal["SEARCH_THEN_REGISTRY", "REGISTRY_THEN_SEARCH"]


class Prerequisite(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_id: str
    kind: PrerequisiteKind
    reason: str


class FixedControl(BaseModel):
    """A fixed safeguard or code constant shown read-only; never a policy-catalogue rule."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str
    value: str
    source: str


class PolicyRuleReference(BaseModel):
    """A stage that also reads a rule whose one authoritative placement is another stage.

    ``policy_rule_ids`` is the single primary binding of a rule (its catalogue definition and
    value are shown there); a reference only says that this stage's code path reads the
    same value, so changing the rule changes this stage too. Tests trace each ``consumer``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    primary_stage_id: str
    consumer: str
    effect: str


class ConditionalRuleUsage(BaseModel):
    """Rules this stage owns in the catalogue but reads at runtime only under a condition.

    Catalogue ownership (``policy_rule_ids``) says where a rule's one definition is shown;
    this says whether the stage's own code path actually reads it in the running environment.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_ids: tuple[str, ...]
    consumer: str
    condition: str
    effect: str
    runs_in_this_environment: bool


class PlanStage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_id: str
    label: str
    engine_stage: EngineStage
    runs: str
    mandatory: Literal[True] = True
    fixed: Literal[True] = True
    fixed_reason: str
    prerequisites: tuple[Prerequisite, ...]
    checkpoints: tuple[str, ...]
    safeguards: tuple[str, ...]
    policy_rule_ids: tuple[str, ...]
    policy_rule_references: tuple[PolicyRuleReference, ...] = ()
    conditional_rule_usage: tuple[ConditionalRuleUsage, ...] = ()
    fixed_controls: tuple[FixedControl, ...] = ()


# The eight entity-resolution rules. Catalogue category "Intelligence": their primary binding
# is the Risk assessment (advisory intelligence) stage. The same case policy snapshot values
# are also read by the GoldTier Search resolution and by existing-party reuse at the send.
ENTITY_RESOLUTION_RULE_IDS: tuple[str, ...] = (
    ENTITY_RESOLUTION_AUTO_MATCH_THRESHOLD_ID,
    ENTITY_RESOLUTION_REVIEW_THRESHOLD_ID,
    ENTITY_RESOLUTION_AMBIGUITY_MARGIN_ID,
    ENTITY_RESOLUTION_IDENTIFIER_WEIGHT_ID,
    ENTITY_RESOLUTION_NAME_WEIGHT_ID,
    ENTITY_RESOLUTION_ADDRESS_WEIGHT_ID,
    ENTITY_RESOLUTION_LEGAL_FORM_WEIGHT_ID,
    ENTITY_RESOLUTION_INCORPORATION_DATE_WEIGHT_ID,
)
ENTITY_RESOLUTION_PRIMARY_STAGE_ID = "ADVISORY"

# Every code path that calls the entity resolver with a case's policy, by plan stage. Tests
# scan every module under ``app/`` for resolver calls and require each one to be listed here
# or in the non-workflow exclusions below, with its reason.
ENTITY_RESOLUTION_CONSUMERS: dict[str, str] = {
    "GOLDTIER_SEARCH": "OnboardingService._resolve_target_candidates",
    "ADVISORY": "OnboardingIntelligenceProjectionService.evaluate",
    "FINAL_REVIEW_SEND": "OnboardingService._submit_to_goldtier",
}
ENTITY_RESOLUTION_NON_WORKFLOW_CONSUMERS: dict[str, str] = {
    "OnboardingService.search_sandbox_target": (
        "HR provider-sandbox search route: a diagnostic outside the onboarding workflow that "
        "reads the current policy, not a case's policy snapshot."
    ),
    "evaluate_synthetic_intelligence_bundle": (
        "Offline synthetic evaluation harness: never runs in the onboarding workflow."
    ),
}
# The advisory (Risk assessment) consumer only has candidates to score when demo candidate
# data is enabled; the composition passes no candidate resolver otherwise.
ADVISORY_ENTITY_RESOLUTION_CONDITION = (
    "Runs only when demo candidate data is enabled (demo controls on). Otherwise this stage "
    "does not run entity resolution; these rules are placed here as their catalogue owner and "
    "are read at Existing-customer search and Final review & send."
)


def _entity_resolution_references(stage_id: str, effect: str) -> tuple[PolicyRuleReference, ...]:
    return tuple(
        PolicyRuleReference(
            rule_id=rule_id,
            primary_stage_id=ENTITY_RESOLUTION_PRIMARY_STAGE_ID,
            consumer=ENTITY_RESOLUTION_CONSUMERS[stage_id],
            effect=effect,
        )
        for rule_id in ENTITY_RESOLUTION_RULE_IDS
    )


def _req(stage_id: str, kind: PrerequisiteKind, reason: str) -> Prerequisite:
    return Prerequisite(stage_id=stage_id, kind=kind, reason=reason)


def _days(milliseconds: int) -> str:
    return f"{milliseconds // (24 * 3_600_000)} days"


_LABELS = dict(ONBOARDING_LOCKED_STAGES)

# Catalogue rules that apply to the workflow as a whole rather than to one stage.
WORKFLOW_WIDE_POLICY_RULE_IDS: tuple[str, ...] = ("WORKFLOW_SUPPORTED_STAGES",)
WORKFLOW_WIDE_FIXED_CONTROLS: tuple[FixedControl, ...] = (
    FixedControl(label="SLA target (D-127)", value=_days(SLA_TARGET_MS), source="SLA_TARGET_MS"),
    FixedControl(
        label="At-risk window (D-127)", value=_days(AT_RISK_WINDOW_MS), source="AT_RISK_WINDOW_MS"
    ),
    FixedControl(
        label="Stale blocker (D-127)", value=_days(STALE_BLOCKER_MS), source="STALE_BLOCKER_MS"
    ),
    FixedControl(label="Inactivity (D-127)", value=_days(INACTIVITY_MS), source="INACTIVITY_MS"),
)


def _search_stage(order: RegistrySearchOrder) -> PlanStage:
    if order == "SEARCH_THEN_REGISTRY":
        runs = (
            "At case creation, before ACRA, on the typed legal name and country "
            "(GoldTier-first identity, ADR-006)."
        )
        prerequisites = (
            _req("JURISDICTION", "DATA", "Runs only for a resolved, eligible Singapore identity."),
        )
    else:
        runs = (
            "After registry verification, on the accepted registry identity; the unverified "
            "typed name is never sent (staging identity policy)."
        )
        prerequisites = (
            _req("ACRA_REGISTRY", "DATA", "Searches with the accepted registry identity."),
        )
    return PlanStage(
        stage_id="GOLDTIER_SEARCH",
        label=_LABELS["GOLDTIER_SEARCH"],
        engine_stage="GOLDTIER_SEARCH",
        runs=runs,
        fixed_reason=(
            "Its position relative to registry verification is set by the running "
            "environment's identity policy, not by workflow data."
        ),
        prerequisites=prerequisites,
        checkpoints=(
            "GOLDTIER_SEARCH_COMPLETED",
            "ENTITY_RESOLUTION_REVIEW_REQUIRED (GT_SEARCH_IDENTITY_REVIEW_REQUIRED)",
            "GOLDTIER_SEARCH_FAILED",
        ),
        safeguards=(
            "Read-only GoldTier Search; a failed or unresolved Search blocks every target "
            "mutation.",
        ),
        policy_rule_ids=(),
        policy_rule_references=_entity_resolution_references(
            "GOLDTIER_SEARCH",
            "Scores the GoldTier Search candidates: decides an exact match (existing party) "
            "or an identity review hold.",
        ),
    )


def _registry_stage(order: RegistrySearchOrder) -> PlanStage:
    prerequisites = [
        _req("JURISDICTION", "DATA", "Needs the resolved jurisdiction and its registry route."),
    ]
    if order == "SEARCH_THEN_REGISTRY":
        prerequisites.append(
            _req(
                "GOLDTIER_SEARCH",
                "ENGINE_ORDER",
                "In this environment the creation call runs the GoldTier Search first.",
            )
        )
    return PlanStage(
        stage_id="ACRA_REGISTRY",
        label=_LABELS["ACRA_REGISTRY"],
        engine_stage="REGISTRY",
        runs="At case creation, inside the same atomic creation call.",
        fixed_reason="Runs at case creation, before any document can exist.",
        prerequisites=tuple(prerequisites),
        checkpoints=("REGISTRY_AUTOMATED", "registry failure stops the case"),
        safeguards=("Singapore ACRA route only; registry evidence freshness and cache rules.",),
        policy_rule_ids=("REGISTRY_FRESHNESS_DAYS", "REGISTRY_NOT_FOUND_TTL_SECONDS"),
    )


def plan_stages(
    order: RegistrySearchOrder, *, demo_entity_candidates: bool = False
) -> tuple[PlanStage, ...]:
    """The twelve business stages in the order this environment actually runs them.

    ``demo_entity_candidates`` is whether demo candidate data is enabled, which decides whether
    the advisory entity-resolution consumer runs at all.
    """

    head = (
        PlanStage(
            stage_id="CASE_START",
            label=_LABELS["CASE_START"],
            engine_stage="CREATION",
            runs="When an onboarder or RM creates the case, under one case lock.",
            fixed_reason="Locked first stage (D-135 S1).",
            prerequisites=(),
            checkpoints=("failed establishment is discarded atomically",),
            safeguards=("Case policy snapshot frozen at creation; insert-only create.",),
            policy_rule_ids=(),
        ),
        PlanStage(
            stage_id="INITIAL_IDENTITY",
            label=_LABELS["INITIAL_IDENTITY"],
            engine_stage="CREATION",
            runs="At case creation, from the creator's UEN, legal name and country.",
            fixed_reason="Locked second stage (D-135 S1); every provider call needs it.",
            prerequisites=(_req("CASE_START", "DATA", "Part of creating the case."),),
            checkpoints=("INITIAL_IDENTITY_INCOMPLETE", "INITIAL_IDENTITY_NOT_ELIGIBLE"),
            safeguards=("Eligibility is checked before any provider call.",),
            policy_rule_ids=(),
        ),
        PlanStage(
            stage_id="JURISDICTION",
            label=_LABELS["JURISDICTION"],
            engine_stage="CREATION",
            runs="At case creation: jurisdiction resolution, then the registry router.",
            fixed_reason="Every registry and GoldTier call depends on the resolved jurisdiction.",
            prerequisites=(
                _req("INITIAL_IDENTITY", "DATA", "Resolves from the identity observations."),
            ),
            checkpoints=(
                "JURISDICTION_UNRESOLVED",
                "JURISDICTION_CONFLICT",
                "REGISTRY_PROVIDER_NOT_IMPLEMENTED",
                "REGISTRY_IDENTIFIER_NOT_ELIGIBLE",
            ),
            safeguards=(
                "Singapore / ACRA is the only implemented route; anything else fails closed.",
            ),
            policy_rule_ids=("REGISTRY_SUPPORTED_JURISDICTIONS", "REGISTRY_PROVIDER"),
        ),
    )
    creation_pair = (
        (_search_stage(order), _registry_stage(order))
        if order == "SEARCH_THEN_REGISTRY"
        else (_registry_stage(order), _search_stage(order))
    )
    tail = (
        PlanStage(
            stage_id="DOCUMENT_IDP",
            label=_LABELS["DOCUMENT_IDP"],
            engine_stage="DOCUMENT",
            runs="After document intake completes (at least one valid document).",
            fixed_reason="Registry and Search run at case creation, before documents exist.",
            prerequisites=(
                _req("ACRA_REGISTRY", "DATA", "Document values are compared with registry values."),
                _req(
                    "GOLDTIER_SEARCH",
                    "ENGINE_ORDER",
                    "The engine runs DOCUMENT only after both creation stages complete.",
                ),
            ),
            checkpoints=(
                "ZERO_TOUCH_DOCUMENTS_REQUIRED",
                "ZERO_TOUCH_INTAKE_INCOMPLETE",
                "document technical failure",
            ),
            safeguards=(
                "Document evidence versions; nothing after creation runs without documents.",
            ),
            policy_rule_ids=(IDP_POLICY_ID, "DOCUMENT_SUPPORTED_MEDIA_TYPES"),
        ),
        PlanStage(
            stage_id="RECONCILIATION",
            label=_LABELS["RECONCILIATION"],
            engine_stage="DOCUMENT",
            runs="Inside the same DOCUMENT engine stage, right after document verification.",
            fixed_reason="Runs inside the DOCUMENT engine stage; it cannot move on its own.",
            prerequisites=(
                _req("DOCUMENT_IDP", "ENGINE_ORDER", "Same engine stage and branch."),
                _req("ACRA_REGISTRY", "DATA", "Reconciles registry and document observations."),
            ),
            checkpoints=("RECONCILIATION_* exceptions", "completes only on MATCHED or RESOLVED"),
            safeguards=("No automatic source precedence.",),
            policy_rule_ids=("RECONCILIATION_SOURCE_PRECEDENCE",),
        ),
        PlanStage(
            stage_id="OWNERSHIP_UBO",
            label=_LABELS["OWNERSHIP_UBO"],
            engine_stage="OWNERSHIP",
            runs="After the DOCUMENT engine stage completes.",
            fixed_reason="Reads registry ownership and the current uploaded documents.",
            prerequisites=(
                _req(
                    "RECONCILIATION",
                    "ENGINE_ORDER",
                    "Runs after the DOCUMENT engine stage completes.",
                ),
                _req("DOCUMENT_IDP", "DATA", "Ownership analysis reads current document inputs."),
                _req("ACRA_REGISTRY", "DATA", "Uses the registry ownership provider."),
            ),
            checkpoints=(
                "OWNERSHIP_* exceptions",
                "Government gate (D-101)",
                "POC basis acceptance (D-085)",
                "advisory review lane (D-121/D-124)",
            ),
            safeguards=("One deterministic Decimal ownership engine; discovery budgets.",),
            policy_rule_ids=(
                UBO_POLICY_ID,
                "OWNERSHIP_UBO_COMPARATOR",
                OWNERSHIP_TRACE_THRESHOLD_ID,
                OWNERSHIP_DISCOVERY_MAX_DEPTH_ID,
                OWNERSHIP_CALL_BUDGET_ENABLED_ID,
                OWNERSHIP_CALL_BUDGET_MAX_ID,
                "EVIDENCE_KIND_WEIGHT",
                "EVIDENCE_BINDING_WEIGHT",
                "EVIDENCE_CONFIDENCE_WEIGHT",
                "EVIDENCE_CLASSIFICATION_THRESHOLD",
            ),
        ),
        PlanStage(
            stage_id="ADVISORY",
            label=_LABELS["ADVISORY"],
            engine_stage="OWNERSHIP",
            runs="Inside the OWNERSHIP engine stage: the advisory intelligence evaluation.",
            fixed_reason="Evaluated inside the OWNERSHIP engine stage; it cannot move on its own.",
            prerequisites=(
                _req(
                    "OWNERSHIP_UBO",
                    "ENGINE_ORDER",
                    "Same engine stage; runs on the ownership outcome.",
                ),
            ),
            checkpoints=(
                "ENTITY_RESOLUTION_REVIEW_REQUIRED",
                "EXISTING_PARTY_REVIEW_REQUIRED",
                "MOCK_RISK_REVIEW_REQUIRED",
            ),
            safeguards=("Advisory only; mock risk is Mock evidence.",),
            conditional_rule_usage=(
                ConditionalRuleUsage(
                    rule_ids=ENTITY_RESOLUTION_RULE_IDS,
                    consumer=ENTITY_RESOLUTION_CONSUMERS["ADVISORY"],
                    condition=ADVISORY_ENTITY_RESOLUTION_CONDITION,
                    effect=(
                        "Scores the case identity against the demo candidate parties for the "
                        "advisory intelligence record."
                    ),
                    runs_in_this_environment=demo_entity_candidates,
                ),
            ),
            policy_rule_ids=(
                *ENTITY_RESOLUTION_RULE_IDS,
                UBO_ADVISORY_LIKELY_THRESHOLD_ID,
                UBO_ADVISORY_UNLIKELY_THRESHOLD_ID,
                MOCK_RISK_MEDIUM_THRESHOLD_ID,
                MOCK_RISK_HIGH_THRESHOLD_ID,
                MOCK_RISK_BLOCKS_READINESS_ID,
            ),
        ),
        PlanStage(
            stage_id="GOLDTIER_DETAILS",
            label=_LABELS["GOLDTIER_DETAILS"],
            engine_stage="READINESS",
            runs="In the READINESS engine stage: authoritative readiness evaluation.",
            fixed_reason="Depends on all evidence and on the GoldTier Search checkpoint.",
            prerequisites=(
                _req(
                    "ADVISORY", "ENGINE_ORDER", "Runs after the OWNERSHIP engine stage completes."
                ),
                _req("GOLDTIER_SEARCH", "DATA", "Readiness needs the resolved Search checkpoint."),
            ),
            checkpoints=(
                "TARGET_CLASSIFICATION_REQUIRED",
                "GoldTier Search failure",
                "AUTOMATION_READINESS_INCONSISTENT",
            ),
            safeguards=(
                "Case-selected KYC customer type and client segment; policy rebind only "
                "before submission.",
            ),
            policy_rule_ids=(
                GOLDTIER_KYC_CUSTOMER_TYPE_ID,
                GOLDTIER_CLIENT_SEGMENT_ID,
                GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM_ID,
                GOLDTIER_REGISTRATION_TYPE_ID,
                GOLDTIER_POLICY_ID,
                GOLDTIER_BOOKING_ENTITY_ID,
                GOLDTIER_ACCOUNT_ENTITY_TYPE_ID,
                GOLDTIER_PRODUCT_TYPE_ID,
            ),
        ),
        PlanStage(
            stage_id="FINAL_REVIEW_SEND",
            label=_LABELS["FINAL_REVIEW_SEND"],
            engine_stage="MOCK_GOLDTIER",
            runs=(
                "TARGET_CONFIRMATION_REQUIRED is raised at READINESS; after an explicit "
                "confirmation the ledger-owned GoldTier write runs."
            ),
            fixed_reason=(
                "Depends on all evidence, the operator's confirmation and the target ledger."
            ),
            prerequisites=(
                _req("GOLDTIER_DETAILS", "DATA", "Sends only a ready, confirmed case."),
            ),
            checkpoints=(
                "TARGET_CONFIRMATION_REQUIRED",
                "WORKFLOW_STAGE_INCOMPLETE / WORKFLOW_STAGE_CHECK_UNAVAILABLE (D-136)",
                "RECOVERY_PENDING",
            ),
            safeguards=(
                "Explicit target confirmation under the case lock with reauthorization.",
                "Every send path enforces stored required workflow stages (D-136).",
                "Ledger-owned ordering and no-replay recovery.",
            ),
            policy_rule_ids=(),
            policy_rule_references=_entity_resolution_references(
                "FINAL_REVIEW_SEND",
                "When the send-time GoldTier Search finds one match, decides whether that "
                "existing party is reused; otherwise the send holds for review.",
            ),
            fixed_controls=(
                FixedControl(
                    label="Explicit confirmation", value="Always", source="target confirmation"
                ),
                FixedControl(
                    label="Required added stages", value="Must be confirmed", source="D-136 E1"
                ),
            ),
        ),
        PlanStage(
            stage_id=APPROVAL_GATE_ID,
            label="Human approval gate",
            engine_stage="NONE",
            runs="Outside automation, after the target submission.",
            fixed_reason="Terminal; approval is never automated.",
            prerequisites=(_req("FINAL_REVIEW_SEND", "DATA", "Follows the target submission."),),
            checkpoints=("unresolved by design",),
            safeguards=("No autonomous or final approval.",),
            policy_rule_ids=(),
        ),
    )
    return (*head, *creation_pair, *tail)


def policy_placement_problems(
    stages: tuple[PlanStage, ...], workflow_wide_rule_ids: tuple[str, ...]
) -> list[str]:
    """Structural check: one primary binding per rule and references that point at it."""

    problems: list[str] = []
    primary: dict[str, str] = {}
    for stage_id, rule_ids in (
        *((stage.stage_id, stage.policy_rule_ids) for stage in stages),
        ("WORKFLOW_WIDE", workflow_wide_rule_ids),
    ):
        for rule_id in rule_ids:
            if rule_id in primary:
                problems.append(f"{rule_id} has two primary bindings")
            primary[rule_id] = stage_id
    for stage in stages:
        seen: set[str] = set()
        for reference in stage.policy_rule_references:
            if reference.rule_id in seen:
                problems.append(f"{stage.stage_id} references {reference.rule_id} twice")
            seen.add(reference.rule_id)
            if primary.get(reference.rule_id) != reference.primary_stage_id:
                problems.append(f"{reference.rule_id} reference names the wrong primary stage")
            if reference.primary_stage_id == stage.stage_id:
                problems.append(f"{stage.stage_id} references its own primary rule")
    return problems
