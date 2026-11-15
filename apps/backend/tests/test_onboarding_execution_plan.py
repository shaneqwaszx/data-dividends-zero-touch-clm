"""P1: the read-only onboarding execution plan (B1-B9).

The plan must describe what the backend actually runs: pinned to the engine order, the
D-123 business stages, the policy catalogue and the environment's identity policy.
Reading it never creates, changes or calls anything.
"""

from __future__ import annotations

import ast
import inspect
import json
import re
import textwrap
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, get_args
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from phase13_test_clients import RawTestClient
from phase13_test_settings import ordinary_test_settings
from test_aws_goldtier_sandbox_readiness import FakeXpiTransport, composed, staging_settings
from test_legacy_clm_workflow_send_hold import (
    OPTIONAL_STAGE,
    corrupt_store,
    storage,
    unavailable_store,
)
from test_workflow_manager import STAGE, login
from test_zero_touch_database_happy_path import NoAcra, RecordingTarget, sandbox_settings

import app
import app.domain.policy as policy_domain
from app.config import Settings
from app.domain.onboarding_execution_plan import (
    ADVISORY_ENTITY_RESOLUTION_CONDITION,
    APPROVAL_GATE_ID,
    ENTITY_RESOLUTION_CONSUMERS,
    ENTITY_RESOLUTION_NON_WORKFLOW_CONSUMERS,
    ENTITY_RESOLUTION_PRIMARY_STAGE_ID,
    ENTITY_RESOLUTION_RULE_IDS,
    WORKFLOW_WIDE_FIXED_CONTROLS,
    WORKFLOW_WIDE_POLICY_RULE_IDS,
    PolicyRuleReference,
    plan_stages,
    policy_placement_problems,
)
from app.domain.target_submission import GoldTierProviderMode
from app.domain.workflows import ONBOARDING_LOCKED_STAGES, ONBOARDING_WORKFLOW_ID
from app.domain.zero_touch import AUTOMATION_STAGE_ORDER
from app.main import create_app
from app.services import clm_orchestration, zero_touch_orchestration
from app.services.onboarding import OnboardingService
from app.services.onboarding_execution_plan import (
    _IDP_CLASS,
    _REGISTRY_CLASS,
    _TARGET_CLASS,
    ExecutionPlanService,
)
from app.services.onboarding_intelligence import OnboardingIntelligenceProjectionService
from app.services.policy_management import PolicyManagementService, default_policy_catalogue
from app.services.workflow_management import WorkflowManagementService

PLAN_URL = "/api/workflows/onboarding/execution-plan"
ORDERS = ("SEARCH_THEN_REGISTRY", "REGISTRY_THEN_SEARCH")


def all_bound_rule_ids(order: str) -> list[str]:
    bound = [rule for stage in plan_stages(order) for rule in stage.policy_rule_ids]
    return [*bound, *WORKFLOW_WIDE_POLICY_RULE_IDS]


# B1 - complete catalogue coverage, one authoritative (primary) binding per rule, no
# invented rule, and every usage reference points at that primary binding.
@pytest.mark.parametrize("order", ORDERS)
def test_every_rule_has_one_primary_binding_and_valid_references(order) -> None:
    catalogue = {rule.policy_id for rule in default_policy_catalogue(datetime.now(UTC)).rules}
    stages = plan_stages(order)
    bound = all_bound_rule_ids(order)
    assert len(catalogue) == 39
    assert sorted(bound) == sorted(catalogue)
    assert len(bound) == len(set(bound))
    assert policy_placement_problems(stages, WORKFLOW_WIDE_POLICY_RULE_IDS) == []
    referenced = {ref.rule_id for stage in stages for ref in stage.policy_rule_references}
    assert referenced <= catalogue


def test_placement_check_rejects_a_second_primary_or_a_dangling_reference() -> None:
    stages = plan_stages("SEARCH_THEN_REGISTRY")
    rule = ENTITY_RESOLUTION_RULE_IDS[0]
    doubled = tuple(
        stage.model_copy(update={"policy_rule_ids": (*stage.policy_rule_ids, rule)})
        if stage.stage_id == "GOLDTIER_SEARCH"
        else stage
        for stage in stages
    )
    assert f"{rule} has two primary bindings" in policy_placement_problems(
        doubled, WORKFLOW_WIDE_POLICY_RULE_IDS
    )
    wrong = PolicyRuleReference(
        rule_id=rule, primary_stage_id="OWNERSHIP_UBO", consumer="x", effect="y"
    )
    dangling = tuple(
        stage.model_copy(update={"policy_rule_references": (wrong,)})
        if stage.stage_id == "JURISDICTION"
        else stage
        for stage in stages
    )
    assert f"{rule} reference names the wrong primary stage" in policy_placement_problems(
        dangling, WORKFLOW_WIDE_POLICY_RULE_IDS
    )


# B1b - the entity-resolution rules are shown under every stage whose code reads them.
@pytest.mark.parametrize("order", ORDERS)
def test_entity_resolution_rules_are_referenced_by_every_consuming_stage(order) -> None:
    stages = {stage.stage_id: stage for stage in plan_stages(order)}
    assert set(ENTITY_RESOLUTION_RULE_IDS) <= set(
        stages[ENTITY_RESOLUTION_PRIMARY_STAGE_ID].policy_rule_ids
    )
    using = {
        stage_id
        for stage_id, stage in stages.items()
        if {ref.rule_id for ref in stage.policy_rule_references} == set(ENTITY_RESOLUTION_RULE_IDS)
    }
    assert using == set(ENTITY_RESOLUTION_CONSUMERS) - {ENTITY_RESOLUTION_PRIMARY_STAGE_ID}
    for stage_id in using:
        for reference in stages[stage_id].policy_rule_references:
            assert reference.primary_stage_id == ENTITY_RESOLUTION_PRIMARY_STAGE_ID
            assert reference.consumer == ENTITY_RESOLUTION_CONSUMERS[stage_id]
            assert reference.effect


def _calls(function: object) -> set[str]:
    tree = ast.parse(textwrap.dedent(inspect.getsource(function)))  # type: ignore[arg-type]
    return {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }


APP_DIR = Path(app.__file__).resolve().parent

# Every place under app/ that calls the entity resolver, with the plan stage it is drawn
# under, or EXCLUDED when it is not part of the onboarding workflow (reason in the domain's
# ENTITY_RESOLUTION_NON_WORKFLOW_CONSUMERS). A new call site anywhere must be added here.
KNOWN_RESOLVER_CALL_SITES: dict[str, str] = {
    "services/onboarding.py::OnboardingService._resolve_target_candidates": "GOLDTIER_SEARCH",
    "services/onboarding_intelligence.py::OnboardingIntelligenceProjectionService.evaluate": (
        "ADVISORY"
    ),
    "services/onboarding.py::OnboardingService._submit_to_goldtier": "FINAL_REVIEW_SEND",
    "services/onboarding.py::OnboardingService.search_sandbox_target": "EXCLUDED",
    "services/intelligence_evaluation.py::evaluate_synthetic_intelligence_bundle": "EXCLUDED",
}


def resolver_call_sites(files: Iterable[Path], root: Path) -> set[str]:
    """``module::Class.function`` for every ``resolve_entity(...)`` call in ``files``."""

    sites: set[str] = set()
    for path in files:
        module = path.resolve().relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))

        def visit(node: ast.AST, scope: tuple[str, ...], module: str = module) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    visit(child, (*scope, child.name))
                    continue
                if isinstance(child, ast.Call):
                    function = child.func
                    name = (
                        function.attr
                        if isinstance(function, ast.Attribute)
                        else function.id
                        if isinstance(function, ast.Name)
                        else None
                    )
                    if name == "resolve_entity":
                        sites.add(f"{module}::{'.'.join(scope) or '<module>'}")
                visit(child, scope)

        visit(tree, ())
    return sites


def app_modules() -> list[Path]:
    return sorted(APP_DIR.rglob("*.py"))


# B1d - negative controls: a resolver call added in another class or module is detected, so
# the B1c inventory would fail until it is classified. Synthetic files only; app/ untouched.
@pytest.mark.parametrize(
    ("relative", "source", "site"),
    [
        (
            "services/clm_orchestration.py",
            "class ClmOrchestrationService:\n"
            "    def advise(self, case):\n"
            "        return self._resolver.resolve_entity(case, (), None)\n",
            "services/clm_orchestration.py::ClmOrchestrationService.advise",
        ),
        (
            "services/new_consumer.py",
            "def score(resolver, case):\n"
            "    return resolver.resolve_entity(source=case, candidates=(), policy=None)\n",
            "services/new_consumer.py::score",
        ),
        (
            "domain/bare_call.py",
            "from somewhere import resolve_entity\n"
            "RESULT = resolve_entity(source=None, candidates=(), policy=None)\n",
            "domain/bare_call.py::<module>",
        ),
    ],
)
def test_a_new_resolver_call_anywhere_breaks_the_inventory(
    tmp_path: Path, relative: str, source: str, site: str
) -> None:
    synthetic = tmp_path / relative
    synthetic.parent.mkdir(parents=True)
    synthetic.write_text(source, encoding="utf-8")
    found = resolver_call_sites(app_modules(), APP_DIR) | resolver_call_sites([synthetic], tmp_path)
    assert site in found
    assert found != set(KNOWN_RESOLVER_CALL_SITES)


# B1c - the references are traced from every resolver call site under app/, not from stage
# names or a fixed list of classes.
def test_entity_resolution_consumers_are_the_actual_resolver_call_sites() -> None:
    assert len(app_modules()) > 100
    assert resolver_call_sites(app_modules(), APP_DIR) == set(KNOWN_RESOLVER_CALL_SITES)
    workflow = {
        stage: site.split("::", 1)[1]
        for site, stage in KNOWN_RESOLVER_CALL_SITES.items()
        if stage != "EXCLUDED"
    }
    assert workflow == ENTITY_RESOLUTION_CONSUMERS
    excluded = {
        site.split("::", 1)[1]
        for site, stage in KNOWN_RESOLVER_CALL_SITES.items()
        if stage == "EXCLUDED"
    }
    assert excluded == set(ENTITY_RESOLUTION_NON_WORKFLOW_CONSUMERS)
    assert all(reason.strip() for reason in ENTITY_RESOLUTION_NON_WORKFLOW_CONSUMERS.values())
    # Each workflow consumer is reached from the stage it is drawn under.
    assert "_resolve_target_candidates" in _calls(OnboardingService.search_target_identity)
    assert "search_target_identity" in inspect.getsource(clm_orchestration)
    assert "_submit_to_goldtier" in _calls(OnboardingService.execute_submission_input)
    assert "_intelligence_evaluator" in inspect.getsource(zero_touch_orchestration)
    # All three read the same values: the case policy snapshot built from these eight rules.
    snapshot = inspect.getsource(PolicyManagementService._intelligence_snapshot)
    for rule_id in ENTITY_RESOLUTION_RULE_IDS:
        constant = next(
            name
            for name, value in vars(policy_domain).items()
            if value == rule_id and name.endswith("_ID")
        )
        assert constant in snapshot


# B1e - Risk assessment owns the rules in the catalogue but reads them at runtime only when
# demo candidate data is enabled; Search and Send always read them.
@pytest.mark.parametrize("demo", [False, True])
@pytest.mark.parametrize("order", ORDERS)
def test_advisory_entity_resolution_is_conditional_on_demo_candidates(order, demo) -> None:
    stages = {s.stage_id: s for s in plan_stages(order, demo_entity_candidates=demo)}
    advisory = stages[ENTITY_RESOLUTION_PRIMARY_STAGE_ID]
    assert set(ENTITY_RESOLUTION_RULE_IDS) <= set(advisory.policy_rule_ids)
    (usage,) = advisory.conditional_rule_usage
    assert usage.rule_ids == ENTITY_RESOLUTION_RULE_IDS
    assert usage.consumer == ENTITY_RESOLUTION_CONSUMERS["ADVISORY"]
    assert usage.condition == ADVISORY_ENTITY_RESOLUTION_CONDITION
    assert usage.runs_in_this_environment is demo
    assert [s.stage_id for s in stages.values() if s.conditional_rule_usage] == ["ADVISORY"]
    for stage_id in ("GOLDTIER_SEARCH", "FINAL_REVIEW_SEND"):
        assert {r.rule_id for r in stages[stage_id].policy_rule_references} == set(
            ENTITY_RESOLUTION_RULE_IDS
        )
    assert plan_stages(order) == plan_stages(order, demo_entity_candidates=False)


@pytest.mark.parametrize("demo", [False, True])
def test_the_plan_reports_the_running_demo_candidate_setting(demo) -> None:
    plan = plan_service(settings=ordinary_test_settings(demo_controls_enabled=demo)).plan()
    advisory = next(stage for stage in plan.stages if stage.stage_id == "ADVISORY")
    assert advisory.conditional_rule_usage[0].runs_in_this_environment is demo


def test_the_condition_mirrors_the_composed_candidate_resolver() -> None:
    # The advisory projection gets a candidate resolver only with demo controls on; without
    # one it never calls the resolver (see OnboardingIntelligenceProjectionService.evaluate).
    composition = re.sub(r"\s+", " ", inspect.getsource(app.main))
    assert (
        "candidate_resolver=( zero_touch_demo.entity_candidates_for if "
        "active_settings.demo_controls_enabled else None )"
    ) in composition
    evaluate = inspect.getsource(OnboardingIntelligenceProjectionService.evaluate)
    assert "if self._candidate_resolver is not None" in evaluate


def test_the_d127_constants_are_shown_read_only_with_their_values() -> None:
    values = {control.source: control.value for control in WORKFLOW_WIDE_FIXED_CONTROLS}
    assert values == {
        "SLA_TARGET_MS": "10 days",
        "AT_RISK_WINDOW_MS": "2 days",
        "STALE_BLOCKER_MS": "7 days",
        "INACTIVITY_MS": "5 days",
    }


# B2 - the twelve business stages are the D-123 stages plus the human gate, in engine order.
@pytest.mark.parametrize("order", ORDERS)
def test_business_stages_match_d123_and_follow_the_engine_order(order) -> None:
    stages = plan_stages(order)
    assert len(stages) == 12
    expected = {node_id for node_id, _ in ONBOARDING_LOCKED_STAGES} | {APPROVAL_GATE_ID}
    assert {stage.stage_id for stage in stages} == expected
    engine = [s.engine_stage for s in stages if s.engine_stage in AUTOMATION_STAGE_ORDER]
    creation = {"REGISTRY", "GOLDTIER_SEARCH"}
    # Outside the creation pair, the engine stages appear exactly in engine order; two
    # business stages share DOCUMENT and two share OWNERSHIP, so collapse repeats first.
    later = [stage for stage in engine if stage not in creation]
    collapsed = [stage for i, stage in enumerate(later) if i == 0 or later[i - 1] != stage]
    assert collapsed == [stage for stage in AUTOMATION_STAGE_ORDER if stage not in creation]
    assert set(engine) == set(AUTOMATION_STAGE_ORDER)


# B3 - shared engine stages, fixed stages and consistent, earlier-only prerequisites.
@pytest.mark.parametrize("order", ORDERS)
def test_shared_engine_stages_and_dependencies_are_truthful(order) -> None:
    stages = {stage.stage_id: stage for stage in plan_stages(order)}
    position = {stage_id: index for index, stage_id in enumerate(stages)}
    assert stages["DOCUMENT_IDP"].engine_stage == stages["RECONCILIATION"].engine_stage
    assert stages["OWNERSHIP_UBO"].engine_stage == stages["ADVISORY"].engine_stage
    for stage in stages.values():
        assert stage.mandatory and stage.fixed and stage.fixed_reason
        for prerequisite in stage.prerequisites:
            assert position[prerequisite.stage_id] < position[stage.stage_id]
    advisory = set(stages["ADVISORY"].policy_rule_ids)
    assert {rule for rule in advisory if rule.startswith("ENTITY_RESOLUTION_")} == {
        rule for rule in all_bound_rule_ids(order) if rule.startswith("ENTITY_RESOLUTION_")
    }
    # Search has no rule of its own; it reads the shared entity-resolution rules by reference.
    assert not stages["GOLDTIER_SEARCH"].policy_rule_ids
    assert stages["GOLDTIER_SEARCH"].policy_rule_references
    assert {"DATA"} <= {p.kind for p in stages["OWNERSHIP_UBO"].prerequisites}


# B4 - the Registry/Search order is the environment's real identity policy.
def test_environment_order_follows_the_composed_identity_policy() -> None:
    staging = composed(staging_settings(), FakeXpiTransport())
    local = composed(staging_settings(goldtier_connector_mode="mock"), FakeXpiTransport())
    assert staging.search_follows_registry is True
    assert local.search_follows_registry is False
    for onboarding, order in ((staging, "REGISTRY_THEN_SEARCH"), (local, "SEARCH_THEN_REGISTRY")):
        plan = plan_service(onboarding=onboarding).plan()
        ids = [stage.stage_id for stage in plan.stages]
        assert plan.registry_search_order == order
        registry_first = ids.index("ACRA_REGISTRY") < ids.index("GOLDTIER_SEARCH")
        assert registry_first is (order == "REGISTRY_THEN_SEARCH")


def plan_service(
    *, onboarding: Any = None, store: Any = None, settings: Settings | None = None
) -> ExecutionPlanService:
    active = settings or ordinary_test_settings()
    backing = store or storage(stage=None)
    return ExecutionPlanService(
        settings=active,
        search_follows_registry=bool(onboarding and onboarding.search_follows_registry),
        target_provider_mode=(
            onboarding.target_provider_mode if onboarding else GoldTierProviderMode.MOCK
        ),
        workflows=WorkflowManagementService(
            definitions=backing.definitions,
            runs=backing.runs,
            cases=object(),  # type: ignore[arg-type]
        ),
    )


def app_with(store: Any, **overrides: Any) -> Any:
    with patch("app.main.build_workflow_persistence", return_value=store):
        return create_app(ordinary_test_settings(**overrides))


# B5 - added stages appear after their anchor; they block the send, never pause automation.
@pytest.mark.parametrize(("stage", "blocks"), [(STAGE, True), (OPTIONAL_STAGE, False)])
def test_active_added_stages_are_shown_with_send_hold_semantics(stage, blocks) -> None:
    hr = login(app_with(storage(stage=stage)), "hr-admin")
    body = hr.get(PLAN_URL).json()
    optional = body["optional_steps"]
    assert optional["state"] == "ACTIVE" and optional["version"] == 1
    (step,) = optional["steps"]
    assert step["stage_id"] == stage["stage_id"] and step["shown_after"] == "DOCUMENT_IDP"
    assert step["blocks_send"] is blocks
    assert step["pauses_automation"] is False
    assert body["branches_supported"] is False


def test_no_active_workflow_is_reported_as_such() -> None:
    body = login(app_with(storage(stage=None)), "hr-admin").get(PLAN_URL).json()
    assert body["optional_steps"]["state"] == "NO_ACTIVE_WORKFLOW"
    assert body["optional_steps"]["steps"] == []
    assert body["optional_steps"]["enforced_at_send"] is False


# B6 - reading the plan creates nothing, changes nothing and calls no provider.
class SpyDefinitions:
    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.writes: list[str] = []

    def get(self, workflow_id: str) -> Any:
        return self.inner.get(workflow_id)

    def list(self) -> Any:
        return self.inner.list()

    def create(self, definition: Any) -> Any:
        self.writes.append("create")
        return self.inner.create(definition)

    def update(self, definition: Any, *, expected_revision: int) -> Any:
        self.writes.append("update")
        return self.inner.update(definition, expected_revision=expected_revision)


def test_reading_the_plan_is_strictly_read_only() -> None:
    store = storage(stage=None)
    spy = SpyDefinitions(store.definitions)
    store = type(store)(definitions=spy, runs=store.runs, close=store.close)
    target = RecordingTarget("Unused", "209990101A")
    with (
        patch("app.main.build_workflow_persistence", return_value=store),
        TestClient(
            create_app(
                sandbox_settings(workflow_manager_enabled=True),
                acra_connector=NoAcra(),
                goldtier_transport=target,
            )
        ) as client,
    ):
        hr = login(client.app, "hr-admin")
        first = hr.get(PLAN_URL)
        second = hr.get(PLAN_URL)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert spy.writes == []
    assert store.definitions.get(ONBOARDING_WORKFLOW_ID) is None  # no baseline created
    assert target.calls == []


# B7 - HR and Directors only; the session is required.
@pytest.mark.parametrize(
    ("user_id", "status"),
    [
        ("hr-admin", 200),
        ("olivia-koh", 200),
        ("maya-lim", 403),
        ("ethan-tan", 403),
        ("support-user", 403),
    ],
)
def test_only_hr_and_directors_can_read_the_plan(user_id, status) -> None:
    response = login(app_with(storage(stage=None)), user_id).get(PLAN_URL)
    assert response.status_code == status
    if status == 403:
        assert response.json()["detail"]["code"] == "EXECUTION_PLAN_FORBIDDEN"


def test_an_unauthenticated_request_is_refused() -> None:
    response = RawTestClient(app_with(storage(stage=None))).get(PLAN_URL)
    assert response.status_code == 401


# B8 - with the manager off, stored stages are still shown as enforced; failures are explicit.
@pytest.mark.parametrize(
    ("store", "state", "steps"),
    [
        (storage, "ACTIVE", 1),
        (lambda: storage(stage=None), "NO_ACTIVE_WORKFLOW", 0),
        (unavailable_store, "ACTIVE", 1),
        (corrupt_store, "UNAVAILABLE", 0),
    ],
)
def test_manager_off_still_shows_what_the_send_check_enforces(store, state, steps) -> None:
    app = app_with(store(), workflow_manager_enabled=False)
    assert login(app, "olivia-koh").get("/api/workflows").status_code == 404
    optional = login(app, "hr-admin").get(PLAN_URL).json()["optional_steps"]
    assert optional["manager_enabled"] is False
    assert optional["state"] == state and len(optional["steps"]) == steps
    assert optional["enforced_at_send"] is (state != "NO_ACTIVE_WORKFLOW")


def test_an_unreadable_definition_store_is_reported_unavailable_not_empty() -> None:
    class Broken:
        def get(self, workflow_id: str) -> Any:
            raise RuntimeError("store down")

    service = plan_service(
        store=type(storage(stage=None))(
            definitions=Broken(),
            runs=storage(stage=None).runs,
            close=lambda: None,  # type: ignore[arg-type]
        )
    )
    optional = service.plan().optional_steps
    assert optional.state == "UNAVAILABLE" and optional.steps == ()
    assert optional.enforced_at_send is True


# B9 - no case data, identifiers or provider payloads in the response.
def test_the_plan_contains_no_case_data() -> None:
    app = app_with(storage())
    maya = login(app, "maya-lim")
    created = maya.post(
        "/api/clm/zero-touch/cases",
        json={
            "uen": "202400001A",
            "legal_name": "Plan Privacy Probe Pte. Ltd.",
            "country_of_incorporation": "SG",
        },
    )
    assert created.status_code == 201, created.text
    case_id = created.json()["case"]["case_id"]
    text = login(app, "hr-admin").get(PLAN_URL).text
    for secret in (case_id, "202400001A", "Plan Privacy Probe"):
        assert secret not in text
    assert set(json.loads(text)) == {
        "registry_search_order",
        "order_explanation",
        "stages",
        "workflow_wide_policy_rule_ids",
        "workflow_wide_fixed_controls",
        "optional_steps",
        "branches_supported",
        "provider_lanes",
    }


def test_provider_lanes_cover_every_mode_and_are_never_live() -> None:
    fields = Settings.model_fields
    assert set(_REGISTRY_CLASS) == set(get_args(fields["acra_connector_mode"].annotation))
    assert set(_IDP_CLASS) == set(get_args(fields["idp_connector_mode"].annotation))
    assert set(_TARGET_CLASS) == set(GoldTierProviderMode)
    lanes = plan_service().plan().provider_lanes
    assert {lane.lane for lane in lanes} == {"REGISTRY", "GOLDTIER", "IDP", "PERSISTENCE"}
    every_class = [*_REGISTRY_CLASS.values(), *_IDP_CLASS.values(), *_TARGET_CLASS.values()]
    assert "LIVE" not in every_class
