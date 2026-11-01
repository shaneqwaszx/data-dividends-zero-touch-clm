"""Slice C: reachable producers and generated guidance stay bound to the policy owner."""

from __future__ import annotations

import ast
import importlib
import re
from collections import Counter
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.access import ROLE_CAPABILITIES
from app.domain.zero_touch import (
    BlockerDecisionAction,
    BlockerDecisionClassification,
    BusinessExceptionType,
    ResumeTransition,
)
from app.services import blocker_decision_policy as policy

ROOT = Path(__file__).resolve().parents[3]
GAPS = {
    "INITIAL_IDENTITY_NOT_ELIGIBLE": BusinessExceptionType.REGISTRY_REVIEW_REQUIRED,
    "ACRA_ENTITY_NOT_FOUND": BusinessExceptionType.REGISTRY_REVIEW_REQUIRED,
    "REGISTRY_RECHECK_INCOMPLETE": BusinessExceptionType.REGISTRY_REVIEW_REQUIRED,
    "CANONICAL_DATA_INCOMPLETE": BusinessExceptionType.REGISTRY_REVIEW_REQUIRED,
    "CONTRADICTORY_OWNERSHIP_EVIDENCE": BusinessExceptionType.OWNERSHIP_INCOMPLETE,
}
CATEGORIES = {
    "USER_ACTION_REQUIRED",
    "OPERATOR_REVIEW_REQUIRED",
    "AUTOMATIC_RECOVERY",
    "EXTERNAL_DEPENDENCY",
    "HARD_STOP",
}


@pytest.mark.parametrize(("code", "exception_type"), GAPS.items())
def test_reachable_producer_gap_has_a_versioned_current_rule(code, exception_type):
    metadata = policy.BlockerDecisionPolicy().evaluate_open_exception(
        policy.OpenBlockerDecisionInput(exception_type=exception_type, blocker_codes=(code,))
    )[0]
    assert code in policy.SUPPORTED_BLOCKER_CODES
    assert metadata.rule_version != "BPD-UNKNOWN-1"
    assert "UNMAPPED_BLOCKER_CODE" not in metadata.unknowns
    assert metadata.classification == (
        BlockerDecisionClassification.HARD_STOP
        if code == "CANONICAL_DATA_INCOMPLETE"
        else BlockerDecisionClassification.USER_ACTION_REQUIRED
    )
    assert metadata.currently_available_actions == ()
    assert metadata.resume_ready is False


def test_inventory_includes_registry_error_producers_and_dynamic_ownership_code():
    onboarding = ROOT / "apps/backend/app/services/onboarding.py"
    tree = ast.parse(onboarding.read_text(encoding="utf-8"))
    functions = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    produced = set()
    for name in (
        "_create_staged_case_locked",
        "_acquire_registry_after_identity_recheck",
        "_acquire_required_registry_evidence",
    ):
        assert name in functions
        for node in ast.walk(functions[name]):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_terminate"
            ):
                continue
            produced.update(
                value.value
                for value in node.args
                if isinstance(value, ast.Constant) and value.value in GAPS
            )
    assert produced == set(GAPS) - {
        "CONTRADICTORY_OWNERSHIP_EVIDENCE",
        "REGISTRY_RECHECK_INCOMPLETE",
    }
    # G preserves this rule for retained records; current rechecks use typed source outcomes.
    assert "REGISTRY_RECHECK_INCOMPLETE" in policy.SUPPORTED_BLOCKER_CODES
    orchestration = (ROOT / "apps/backend/app/services/zero_touch_orchestration.py").read_text(
        encoding="utf-8"
    )
    assert '"CONTRADICTORY_OWNERSHIP_EVIDENCE"' in orchestration
    assert set(GAPS) <= policy.SUPPORTED_BLOCKER_CODES


def test_catalogue_core_is_derived_from_every_rule_spec_and_has_complete_guidance():
    catalogue = policy.blocker_catalogue()
    assert tuple(entry.code for entry in catalogue) == tuple(sorted(policy.SUPPORTED_BLOCKER_CODES))
    assert len(catalogue) == 65  # D-101 +1 Government status; D-114 +2 government register
    for entry in catalogue:
        spec = policy._RULE_INDEX[entry.code]
        assert entry.exception_types == tuple(sorted(spec.exception_types, key=str))
        assert entry.rule_version == spec.rule_version
        assert entry.policy_classification == spec.classification
        assert entry.explanation == spec.explanation
        assert entry.required_inputs == spec.minimum_inputs
        assert entry.declared_actions == spec.permitted_actions
        assert entry.resume_transition == spec.resume_transition
        assert entry.invalidated_dependencies == spec.invalidated_dependencies
        assert entry.classification in CATEGORIES
        assert entry.domain_stage and entry.current_action_predicate and entry.no_action_reason
        assert entry.auto_resume and entry.external_dependency and entry.local_demo_scenario
        assert entry.test_coverage
        assert {path.action for path in entry.action_paths} == set(entry.declared_actions)
        for path in entry.action_paths:
            assert path.current_action_predicate and path.no_action_reason
            if path.browser_control is not None:
                assert path.backend_owner and path.capability is not None and path.roles
                assert all(path.capability in ROLE_CAPABILITIES[role] for role in path.roles)
                assert path.browser_source and (ROOT / path.browser_source).is_file()
                assert path.backend_source and (ROOT / path.backend_source).is_file()
            else:
                assert path.no_action_reason


def test_categories_describe_recovery_without_changing_durable_enums():
    catalogue = policy.blocker_catalogue()
    counts = Counter(entry.classification for entry in catalogue)
    assert set(counts) == CATEGORIES
    assert sum(counts.values()) == 65  # D-101 +1 Government status; D-114 +2 government register
    assert "OPERATOR_REVIEW_REQUIRED" not in {item.value for item in BlockerDecisionClassification}
    assert "AUTOMATIC_RECOVERY" not in {item.value for item in BlockerDecisionClassification}
    finalization = next(
        entry for entry in catalogue if entry.code == "CLM_FINALIZATION_RETRY_REQUIRED"
    )
    assert finalization.classification == "AUTOMATIC_RECOVERY"
    assert "replay" in finalization.auto_resume.lower()


@pytest.mark.parametrize("code", ["TIMEOUT_FROM_FUTURE_PROVIDER", "PERSISTENCE_UNAVAILABLE"])
def test_unknown_technical_codes_remain_explicitly_fail_closed(code):
    guidance = policy.unknown_blocker_guidance(code)
    assert guidance.code == code
    assert guidance.classification == "HARD_STOP"
    assert guidance.action_paths == ()
    assert guidance.resume_transition == ResumeTransition.NO_AUTOMATIC_RESUME
    assert "technical" in guidance.no_action_reason.lower()
    assert "retry" in guidance.no_action_reason.lower()


def test_unknown_technical_guidance_rejects_raw_error_text():
    with pytest.raises(ValidationError):
        policy.unknown_blocker_guidance("Timeout: private provider details")


def test_declared_provider_and_advisory_actions_have_no_fabricated_browser_path():
    catalogue = policy.blocker_catalogue()
    unavailable = {
        BlockerDecisionAction.ENABLE_SUPPORTED_REGISTRY_PROVIDER,
        BlockerDecisionAction.PROVIDE_REGISTRY_EVIDENCE,
        BlockerDecisionAction.REVIEW_ENTITY_IDENTITY,
        BlockerDecisionAction.REVIEW_MOCK_RISK,
        BlockerDecisionAction.VERIFY_TARGET_OUTCOME_WITHOUT_REPLAY,
        BlockerDecisionAction.DIAGNOSE_PROVIDER_VALIDATION,
        BlockerDecisionAction.RERUN_OWNERSHIP_ANALYSIS,
        BlockerDecisionAction.ESCALATE_TO_OWNER,
    }
    for entry in catalogue:
        for path in entry.action_paths:
            if path.action in unavailable:
                assert path.browser_control is None
                assert path.no_action_reason


def test_rectification_guide_is_generated_from_current_catalogue():
    generator = importlib.import_module("scripts.generate_blocker_rectification_guide")
    guide = ROOT / "docs/demo/BLOCKER_RECTIFICATION_GUIDE.md"
    assert guide.read_text(encoding="utf-8") == generator.render_guide()
    for entry in policy.blocker_catalogue():
        assert f"| {entry.code} |" in generator.render_guide()
    for reference in (
        "apps/frontend/e2e/slice-c-recovery.e2e.ts",
        "apps/frontend/e2e/phase24-identity.e2e.ts",
        "apps/frontend/e2e/authenticated-zero-touch.e2e.ts",
        "apps/frontend/e2e/zero-touch-exception.e2e.ts",
        "apps/frontend/e2e/slice-b-registry-demo.e2e.ts",
    ):
        assert reference in generator.render_guide()
    assert "Coverage references are not an execution claim" in generator.render_guide()


def test_catalogue_coverage_and_local_owners_point_to_current_sources():
    for entry in policy.blocker_catalogue():
        for reference in entry.test_coverage:
            assert (ROOT / reference).is_file(), reference
        for path in entry.action_paths:
            if path.browser_control is None:
                continue
            assert path.backend_owner is not None
            assert path.backend_source is not None
            method = re.search(r"ZeroTouchOrchestrator\.([a-z_]+)", path.backend_owner)
            assert method is not None, path.backend_owner
            owner_source = (ROOT / path.backend_source).read_text(encoding="utf-8")
            assert f"def {method[1]}(" in owner_source, path.backend_owner


def test_unknown_guidance_cannot_mask_a_supported_rule():
    with pytest.raises(ValueError, match="supported"):
        policy.unknown_blocker_guidance("ACRA_ENTITY_NOT_FOUND")


def test_registry_incomplete_does_not_claim_a_generic_canonical_override():
    entries = {entry.code: entry for entry in policy.blocker_catalogue()}
    canonical = entries["CANONICAL_DATA_INCOMPLETE"]
    assert canonical.classification == "HARD_STOP"
    assert all(path.browser_control is None for path in canonical.action_paths)
    assert canonical.auto_resume.startswith("No.")
    recheck = entries["REGISTRY_RECHECK_INCOMPLETE"]
    assert recheck.classification == "USER_ACTION_REQUIRED"
    assert recheck.declared_actions == (BlockerDecisionAction.CORRECT_INITIAL_IDENTITY,)
