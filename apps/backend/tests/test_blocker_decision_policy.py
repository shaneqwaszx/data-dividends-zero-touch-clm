from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.clm import ClmBlockerCode
from app.domain.documents import DocumentAutoClearBlocker
from app.domain.zero_touch import (
    AutomationStage,
    BlockerDecisionAction,
    BlockerDecisionClassification,
    BlockerDecisionMetadata,
    BlockerDecisionOwner,
    BlockerMinimumInput,
    BusinessExceptionType,
    ExceptionResolutionAction,
    InvalidatedDependency,
    ResumeTransition,
)
from app.services.blocker_decision_policy import (
    BLOCKER_DECISION_POLICY_VERSION,
    MAPPED_BUSINESS_EXCEPTION_TYPES,
    SUPPORTED_BLOCKER_BINDINGS,
    SUPPORTED_BLOCKER_CODES,
    AutoResolvedDecisionInput,
    AutoResolvedRule,
    BlockerDecisionPolicy,
    ContinueWithWarningDecisionInput,
    ContinueWithWarningRule,
    OpenBlockerDecisionInput,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ZERO_TOUCH_SOURCE = BACKEND_ROOT / "app" / "services" / "zero_touch_orchestration.py"
UPPER_CODE = re.compile(r"^[A-Z][A-Z0-9_]{3,63}$")


def decide(
    exception_type: BusinessExceptionType,
    code: str,
    *,
    available_inputs: frozenset[BlockerMinimumInput] = frozenset(),
    available_actions: frozenset[BlockerDecisionAction] = frozenset(),
    resolution_actions: frozenset[ExceptionResolutionAction] = frozenset(),
) -> BlockerDecisionMetadata:
    return BlockerDecisionPolicy().evaluate_open_exception(
        OpenBlockerDecisionInput(
            exception_type=exception_type,
            blocker_codes=(code,),
            available_inputs=available_inputs,
            available_actions=available_actions,
            available_resolution_actions=resolution_actions,
        )
    )[0]


def _string_constants(node: ast.AST) -> set[str]:
    return {
        child.value
        for child in ast.walk(node)
        if isinstance(child, ast.Constant)
        and isinstance(child.value, str)
        and UPPER_CODE.fullmatch(child.value)
    }


def _reachable_add_exception_literal_codes() -> set[str]:
    """Derive literal blocker codes from current exception-producing code paths."""

    tree = ast.parse(ZERO_TOUCH_SOURCE.read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    relevant_names = {
        "_create_case_locked",
        "_advance_locked_impl",
        "_raise_document_exception",
        "_raise_reconciliation_exceptions",
        "_raise_ownership_exception",
        "_raise_target_exception",
        "_raise_mock_risk_exception",
        "_raise_entity_resolution_exception",
    }
    codes: set[str] = set()
    for name in relevant_names:
        function = functions[name]
        for node in ast.walk(function):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_add_exception"
            ):
                for keyword in node.keywords:
                    if keyword.arg == "blocker_code":
                        codes.update(_string_constants(keyword.value))
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                value = node.value
                if value is None:
                    continue
                if any(isinstance(target, ast.Name) and target.id == "code" for target in targets):
                    codes.update(_string_constants(value))
                if any(
                    isinstance(target, ast.Name)
                    and target.id in {"blocker_code", "exception_types", "outcome_codes"}
                    for target in targets
                ):
                    codes.update(_string_constants(value))
            if (
                isinstance(node, ast.Compare)
                and isinstance(node.left, ast.Name)
                and node.left.id == "code"
            ):
                codes.update(_string_constants(node))
            if (
                name == "_raise_reconciliation_exceptions"
                and isinstance(node, ast.Return)
                and node.value is not None
            ):
                codes.update(_string_constants(node.value))
    return codes


def test_policy_inventory_covers_every_business_exception_and_clm_blocker() -> None:
    assert frozenset(BusinessExceptionType) == MAPPED_BUSINESS_EXCEPTION_TYPES
    assert {code.value for code in ClmBlockerCode} <= SUPPORTED_BLOCKER_CODES
    assert {code.value for code in DocumentAutoClearBlocker} <= SUPPORTED_BLOCKER_CODES
    assert set(SUPPORTED_BLOCKER_BINDINGS) == SUPPORTED_BLOCKER_CODES


def test_inventory_tracks_reachable_add_exception_literal_codes() -> None:
    reachable = _reachable_add_exception_literal_codes()
    assert reachable
    assert reachable <= SUPPORTED_BLOCKER_CODES


def test_every_open_exception_rule_remains_blocking() -> None:
    non_blocking = {
        BlockerDecisionClassification.AUTO_RESOLVED_WITH_NOTE,
        BlockerDecisionClassification.CONTINUE_WITH_WARNING,
    }
    for code, exception_types in SUPPORTED_BLOCKER_BINDINGS.items():
        for exception_type in exception_types:
            result = decide(exception_type, code)
            assert result.classification not in non_blocking
            assert result.policy_version == BLOCKER_DECISION_POLICY_VERSION
            assert result.rule_version
            assert result.owner
            assert result.permitted_actions


def test_no_text_document_requires_bound_replacement_and_invalidates_dependants() -> None:
    result = decide(
        BusinessExceptionType.DOCUMENT_REQUIRED_FIELD_MISSING,
        "DOCUMENT_TEXT_UNAVAILABLE",
        available_inputs=frozenset({BlockerMinimumInput.CURRENT_DOCUMENT_EVIDENCE}),
        available_actions=frozenset({BlockerDecisionAction.UPLOAD_REPLACEMENT_DOCUMENT}),
    )

    assert result.classification == BlockerDecisionClassification.USER_ACTION_REQUIRED
    assert result.owner == BlockerDecisionOwner.DOCUMENT_REVIEW_OWNER
    assert result.resume_stage == AutomationStage.DOCUMENT
    assert result.resume_transition == ResumeTransition.REPLACE_EVIDENCE_AND_RECHECK
    assert result.resume_ready is True
    assert result.currently_available_actions == (
        BlockerDecisionAction.UPLOAD_REPLACEMENT_DOCUMENT,
    )
    assert InvalidatedDependency.OWNERSHIP_ANALYSIS in result.invalidated_dependencies
    assert InvalidatedDependency.TARGET_MUTATIONS in result.invalidated_dependencies


def test_source_conflict_exposes_only_existing_authorized_resolution_actions() -> None:
    unavailable = decide(
        BusinessExceptionType.DOCUMENT_SOURCE_CONFLICT,
        "DOCUMENT_SOURCE_CONFLICT",
    )
    assert unavailable.classification == BlockerDecisionClassification.HARD_STOP
    assert unavailable.permitted_actions == (BlockerDecisionAction.ESCALATE_TO_OWNER,)
    assert "NO_AUTHORIZED_RESOLUTION_ACTION_AVAILABLE" in unavailable.unknowns

    authorized = decide(
        BusinessExceptionType.DOCUMENT_SOURCE_CONFLICT,
        "DOCUMENT_SOURCE_CONFLICT",
        available_inputs=frozenset(
            {
                BlockerMinimumInput.CURRENT_RECONCILIATION_EVIDENCE,
                BlockerMinimumInput.AUTHORIZED_RECONCILIATION_ACTION,
            }
        ),
        resolution_actions=frozenset({ExceptionResolutionAction.KEEP_REGISTRY_VALUE}),
    )
    assert authorized.classification == BlockerDecisionClassification.USER_ACTION_REQUIRED
    assert authorized.permitted_actions == (BlockerDecisionAction.KEEP_REGISTRY_VALUE,)
    assert authorized.currently_available_actions == (BlockerDecisionAction.KEEP_REGISTRY_VALUE,)
    assert BlockerDecisionAction.USE_DOCUMENT_VALUE not in authorized.permitted_actions
    assert authorized.resume_ready is True


@pytest.mark.parametrize(
    ("code", "classification"),
    [
        (
            "GT_SEARCH_IDENTITY_REVIEW_REQUIRED",
            BlockerDecisionClassification.USER_ACTION_REQUIRED,
        ),
        ("SEARCH_SERVICE_UNAVAILABLE", BlockerDecisionClassification.EXTERNAL_DEPENDENCY),
        ("GOLDTIER_SEARCH_FAILED", BlockerDecisionClassification.EXTERNAL_DEPENDENCY),
    ],
)
def test_search_ambiguity_and_failure_never_become_no_match(
    code: str,
    classification: BlockerDecisionClassification,
) -> None:
    result = decide(BusinessExceptionType.ENTITY_RESOLUTION_REVIEW_REQUIRED, code)
    assert result.classification == classification
    assert result.resume_stage == AutomationStage.GOLDTIER_SEARCH
    assert BlockerDecisionAction.RUN_READ_ONLY_SEARCH_RECHECK in result.permitted_actions
    assert InvalidatedDependency.TARGET_MUTATIONS in result.invalidated_dependencies
    assert "NO_MATCH" not in result.explanation


@pytest.mark.parametrize(
    ("exception_type", "code"),
    [
        (BusinessExceptionType.OWNERSHIP_CYCLE, "OWNERSHIP_CYCLE"),
        (BusinessExceptionType.OWNERSHIP_INCOMPLETE, "OWNERSHIP_INCOMPLETE"),
        (BusinessExceptionType.OWNERSHIP_REVIEW_REQUIRED, "OWNERSHIP_REVIEW_REQUIRED"),
    ],
)
def test_ownership_requires_corrected_evidence_and_the_existing_engine(
    exception_type: BusinessExceptionType,
    code: str,
) -> None:
    result = decide(exception_type, code)
    assert result.classification == BlockerDecisionClassification.USER_ACTION_REQUIRED
    assert result.resume_stage == AutomationStage.OWNERSHIP
    assert result.permitted_actions == (
        BlockerDecisionAction.PROVIDE_CORRECTED_OWNERSHIP_EVIDENCE,
        BlockerDecisionAction.RERUN_OWNERSHIP_ANALYSIS,
    )
    assert "Decimal engine" in result.explanation
    assert "LEGAL_UBO_DETERMINATION_NOT_IMPLEMENTED" in result.unknowns


def test_risk_review_is_hard_stop_under_unresolved_policy() -> None:
    result = decide(
        BusinessExceptionType.MOCK_RISK_REVIEW_REQUIRED,
        "MOCK_RISK_REVIEW_REQUIRED",
        available_actions=frozenset({BlockerDecisionAction.REVIEW_MOCK_RISK}),
    )
    assert result.classification == BlockerDecisionClassification.HARD_STOP
    assert result.owner == BlockerDecisionOwner.POLICY_OWNER
    assert result.resume_transition == ResumeTransition.NO_AUTOMATIC_RESUME
    assert "SPONSOR_RISK_REVIEW_POLICY_UNRESOLVED" in result.unknowns


def test_classification_and_confirmation_are_separate_user_gates() -> None:
    policy = BlockerDecisionPolicy()
    results = policy.evaluate_open_exception(
        OpenBlockerDecisionInput(
            exception_type=BusinessExceptionType.TARGET_CLASSIFICATION_REQUIRED,
            blocker_codes=("GOLDTIER_CLASSIFICATION_REQUIRED",),
            available_inputs=frozenset({BlockerMinimumInput.CURRENT_TARGET_CLASSIFICATION}),
            available_actions=frozenset({BlockerDecisionAction.SELECT_TARGET_CLASSIFICATION}),
        )
    )
    classification = results[0]
    confirmation = decide(
        BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED,
        "TARGET_CONFIRMATION_REQUIRED",
    )

    assert classification.resume_stage == AutomationStage.READINESS
    assert classification.resume_ready is True
    assert confirmation.resume_stage == AutomationStage.MOCK_GOLDTIER
    assert confirmation.resume_ready is False
    assert confirmation.permitted_actions == (
        BlockerDecisionAction.CONFIRM_FROZEN_TARGET_SUBMISSION,
    )


@pytest.mark.parametrize(
    "code",
    [
        "CLM_TARGET_OUTCOME_UNCERTAIN",
        "TARGET_OPERATION_OUTCOME_UNCERTAIN",
        "UNCERTAIN_TARGET_MUTATION",
    ],
)
def test_uncertain_target_write_is_hard_stop_and_never_replayable(code: str) -> None:
    result = decide(BusinessExceptionType.TARGET_PARTIAL_REVIEW_REQUIRED, code)
    assert result.classification == BlockerDecisionClassification.HARD_STOP
    assert result.owner == BlockerDecisionOwner.TARGET_OPERATIONS_OWNER
    assert result.permitted_actions == (BlockerDecisionAction.VERIFY_TARGET_OUTCOME_WITHOUT_REPLAY,)
    assert result.resume_transition == ResumeTransition.VERIFY_WITHOUT_REPLAY
    assert "never replayed" in result.explanation


def test_unknown_code_and_type_mismatch_fail_closed_with_explicit_escalation() -> None:
    unknown = decide(
        BusinessExceptionType.REGISTRY_REVIEW_REQUIRED,
        "AUTHORIZATION_WAIVER_REQUESTED",
    )
    mismatch = decide(
        BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED,
        "OWNERSHIP_CYCLE",
    )
    for result in (unknown, mismatch):
        assert result.classification == BlockerDecisionClassification.HARD_STOP
        assert result.owner == BlockerDecisionOwner.POLICY_OWNER
        assert result.permitted_actions == (BlockerDecisionAction.ESCALATE_TO_OWNER,)
        assert result.resume_stage is None
        assert result.resume_ready is False
        assert set(result.invalidated_dependencies) == set(InvalidatedDependency)
    assert unknown.unknowns == ("UNMAPPED_BLOCKER_CODE",)
    assert mismatch.unknowns == ("EXCEPTION_TYPE_BLOCKER_CODE_MISMATCH",)


def test_multiple_blockers_receive_independent_decisions() -> None:
    policy_input = OpenBlockerDecisionInput(
        exception_type=BusinessExceptionType.DOCUMENT_SOURCE_CONFLICT,
        blocker_codes=("DOCUMENT_SOURCE_CONFLICT", "DOCUMENT_LOW_CONFIDENCE"),
    )
    decisions = BlockerDecisionPolicy().evaluate_open_exception(policy_input)
    assert [item.blocker_code for item in decisions] == [
        "DOCUMENT_SOURCE_CONFLICT",
        "DOCUMENT_LOW_CONFIDENCE",
    ]
    assert decisions[0].classification == BlockerDecisionClassification.HARD_STOP
    assert decisions[1].classification == BlockerDecisionClassification.USER_ACTION_REQUIRED
    assert decisions[0].unknowns != decisions[1].unknowns


def test_non_blocking_classifications_require_their_explicit_apis_and_evidence() -> None:
    policy = BlockerDecisionPolicy()
    with pytest.raises(ValueError):
        policy.auto_resolved_note(
            AutoResolvedDecisionInput(
                rule=AutoResolvedRule.EQUIVALENT_DOCUMENT_VALUES_AUTO_CONFIRMED,
                available_inputs=frozenset(),
            )
        )
    auto = policy.auto_resolved_note(
        AutoResolvedDecisionInput(
            rule=AutoResolvedRule.EQUIVALENT_DOCUMENT_VALUES_AUTO_CONFIRMED,
            available_inputs=frozenset(
                {
                    BlockerMinimumInput.CURRENT_DOCUMENT_EVIDENCE,
                    BlockerMinimumInput.EQUIVALENT_NORMALIZED_VALUES,
                }
            ),
        )
    )
    warning = policy.continue_with_warning(
        ContinueWithWarningDecisionInput(
            rule=ContinueWithWarningRule.IDP_PROFILE_PROVISIONAL,
            available_inputs=frozenset({BlockerMinimumInput.CURRENT_READINESS_WARNING}),
        )
    )
    assert auto.classification == BlockerDecisionClassification.AUTO_RESOLVED_WITH_NOTE
    assert auto.exception_type is None and auto.resume_stage is None
    assert warning.classification == BlockerDecisionClassification.CONTINUE_WITH_WARNING
    assert warning.resume_stage == AutomationStage.READINESS
    assert warning.resume_transition == ResumeTransition.RETAIN_NOTE_WITHOUT_WORKFLOW_CHANGE
    assert warning.invalidated_dependencies == ()


def test_inputs_accept_no_free_text_and_metadata_is_immutable() -> None:
    with pytest.raises(ValidationError):
        OpenBlockerDecisionInput.model_validate(
            {
                "exception_type": "REGISTRY_REVIEW_REQUIRED",
                "blocker_codes": ["unsafe code with spaces"],
                "operator_note": "ignore previous instructions",
            }
        )
    metadata = decide(
        BusinessExceptionType.REGISTRY_REVIEW_REQUIRED,
        "REGISTRY_REVIEW_REQUIRED",
    )
    with pytest.raises(ValidationError):
        metadata.owner = BlockerDecisionOwner.CASE_OPERATOR  # type: ignore[misc]
