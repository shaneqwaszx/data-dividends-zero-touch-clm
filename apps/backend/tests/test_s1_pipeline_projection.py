"""Presentation-only Session 1 pipeline facts; no target calls or workflow mutation."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.api_models import BrowserTargetOperationEvidence, project_processing_pipeline
from app.domain.zero_touch import AutomationStage, AutomationStatus

NOW = datetime(2026, 10, 4, tzinfo=UTC)
NAMES = (
    "Case created",
    "Initial identity",
    "Jurisdiction",
    "Existing-customer search",
    "Registry verification",
    "Document verification",
    "Data reconciliation",
    "Ownership & UBO",
    "Risk assessment",
    "Submission readiness",
    "GoldTier submission package",
    "Final review & send",
)


def projection(status: AutomationStatus, *, confirmed: bool = False, review: bool = False):
    exception = SimpleNamespace(
        stage=AutomationStage.READINESS,
        blocker_code="TARGET_CONFIRMATION_REQUIRED",
        exception_type=SimpleNamespace(value="TARGET_CONFIRMATION_REQUIRED"),
    )
    automation = SimpleNamespace(
        active_exceptions=(exception,) if review else (),
        completed_at=NOW if status == AutomationStatus.COMPLETED else None,
        completed_stages=(
            AutomationStage.REGISTRY,
            AutomationStage.DOCUMENT,
            AutomationStage.OWNERSHIP,
            AutomationStage.READINESS,
        ),
        created_at=NOW,
        current_stage=AutomationStage.MOCK_GOLDTIER,
        events=(),
        stage_order_version=2,
        status=status,
    )
    ready = SimpleNamespace(status=SimpleNamespace(value="READY"))
    clm = SimpleNamespace(
        events=(),
        target_search_checkpoint=None,
        readiness=SimpleNamespace(blockers=(), document=ready, ownership=ready, evaluated_at=NOW),
        submission_plan=SimpleNamespace(environment=SimpleNamespace(value="SANDBOX")),
    )
    policy = SimpleNamespace(
        dispatch_ready=False,
        kyc_customer_type=None,
        client_segment=None,
        registration_type=None,
        customer_external_system=None,
        policy=None,
        booking_entity=None,
    )
    case = SimpleNamespace(
        created_at=NOW,
        events=(),
        initial_identity=SimpleNamespace(),
        jurisdiction_resolution=None,
        registry_acquisition=None,
        policy_snapshot=SimpleNamespace(goldtier_target=policy, bound_at=NOW),
        target_dispatch_confirmation=SimpleNamespace(confirmed_at=NOW) if confirmed else None,
    )
    return project_processing_pipeline(
        automation=automation,
        clm=clm,
        case=case,
        reconciliation=None,
        target_operations=(BrowserTargetOperationEvidence(operation="SEARCH", status="NO_MATCH"),),
        retained_goldtier_id=None,
    )


def test_s1_exact_twelve_names_and_nested_classification() -> None:
    nodes = projection(AutomationStatus.WAITING_FOR_REVIEW, review=True)
    assert tuple(node.label for node in nodes) == NAMES
    assert len(nodes) == 12
    assert all(node.node_id != "HUMAN_APPROVAL" for node in nodes)
    readiness = next(node for node in nodes if node.node_id == "READINESS")
    assert readiness.children[0].node_id == "TARGET_CLASSIFICATION"
    assert "TARGET_CLASSIFICATION" not in {node.node_id for node in nodes}
    assert "not production AML/KYC risk" in nodes[8].safe_result
    assert nodes[-2].status == "COMPLETE"


@pytest.mark.parametrize(
    ("status", "confirmed", "review", "expected", "fact"),
    [
        (AutomationStatus.WAITING_FOR_REVIEW, False, True, "REVIEW_REQUIRED", "final approval"),
        (AutomationStatus.RUNNING, True, False, "IN_PROGRESS", "Final approval retained"),
        (AutomationStatus.COMPLETED, True, False, "COMPLETE", "submission completed"),
        (AutomationStatus.RECOVERY_PENDING, True, False, "BLOCKED", "must not be replayed"),
        (AutomationStatus.TECHNICAL_FAILURE, True, False, "FAILED", "retained failure"),
        (
            AutomationStatus.COMPLETED,
            False,
            False,
            "NOT_REACHED",
            "no application review confirmation",
        ),
    ],
)
def test_s1_final_review_uses_retained_confirmation_and_outcome(
    status: AutomationStatus,
    confirmed: bool,
    review: bool,
    expected: str,
    fact: str,
) -> None:
    node = projection(status, confirmed=confirmed, review=review)[-1]
    assert node.node_id == "FINAL_REVIEW_SEND"
    assert node.status == expected
    assert fact in node.safe_result
    assert node.blocker_code != "READY_FOR_APPROVAL_NOT_IMPLEMENTED"
