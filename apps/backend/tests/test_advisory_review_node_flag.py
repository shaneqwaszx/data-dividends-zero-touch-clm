"""D-141: the OWNERSHIP_UBO node says when its completion rests on an advisory review (D-121).

Presentation only: the node status, readiness, the audit code and blocking mode are unchanged.
"""

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from test_marketplace_mock_partnerships import mock_lane, xyz_at_ownership, xyz_declaration
from test_s1_pipeline_projection import NOW
from test_zero_touch_entity_types import blockers, submit_partners

from app.api_models import BrowserProcessingNode, project_processing_pipeline
from app.domain.zero_touch import AutomationStatus
from app.services.ownership_analysis import OwnershipAnalysisService


def ownership_node(summary: dict) -> dict:
    return next(n for n in summary["processing_pipeline"] if n["node_id"] == "OWNERSHIP_UBO")


def other_flags(summary: dict) -> set[object]:
    return {
        node.get("advisory_review")
        for node in summary["processing_pipeline"]
        if node["node_id"] != "OWNERSHIP_UBO"
    }


def read(client, current: dict) -> dict:
    response = client.get(f"/api/clm/zero-touch/cases/{current['case']['case_id']}")
    assert response.status_code == 200, response.json()
    return response.json()


# API: the XYZ partnership on the official Mock lane -----------------------------------------


def test_xyz_unconfirmed_shares_are_complete_for_readiness_and_flagged_advisory() -> None:
    with mock_lane() as (client, _):
        current = read(client, xyz_at_ownership(client))
        ownership = client.get(
            f"/api/onboarding/cases/{current['case']['case_id']}/ownership"
        ).json()
        assert ownership["state"] == "REVIEW_REQUIRED"
        assert ownership["poc_basis_accepted"] is False
        assert "OWNERSHIP_REVIEW_REQUIRED" not in current["clm"]["readiness"]["blockers"]
        assert "UBO_REVIEW_REQUIRED" not in blockers(current)
        node = ownership_node(current)
        assert node["status"] == "COMPLETE"  # D-121 unchanged
        assert node["advisory_review"] is True
        assert other_flags(current) == {None}
        assert current["entity_type_basis"]["partnership_state"] == "AWAITING_RM_CONFIRMATION"


def test_xyz_confirmed_shares_are_complete_without_the_flag() -> None:
    with mock_lane() as (client, _):
        current = xyz_at_ownership(client)
        response = submit_partners(client, current, xyz_declaration(client, current))
        assert response.status_code == 200, response.json()
        current = read(client, response.json())
        node = ownership_node(current)
        assert node["status"] == "COMPLETE"
        assert node["advisory_review"] is None


@pytest.mark.usefixtures("blocking_ubo_review")
def test_blocking_mode_keeps_the_review_required_node_without_the_flag() -> None:
    with mock_lane() as (client, _):
        current = read(client, xyz_at_ownership(client))
        assert "OWNERSHIP_REVIEW_REQUIRED" in current["clm"]["readiness"]["blockers"]
        assert "UBO_REVIEW_REQUIRED" in blockers(current)
        node = ownership_node(current)
        assert node["status"] == "REVIEW_REQUIRED"
        assert node["advisory_review"] is None


def test_a_lane_that_does_not_qualify_never_flags() -> None:
    # Non-Mock lanes and blocking mode both compose the service with ubo_review_advisory=False.
    with (
        mock_lane() as (client, _),
        patch.object(OwnershipAnalysisService, "review_is_advisory", return_value=False),
    ):
        node = ownership_node(read(client, xyz_at_ownership(client)))
        assert node["advisory_review"] is None


def test_a_stale_analysis_never_flags() -> None:
    with mock_lane() as (client, _):
        current = xyz_at_ownership(client)
        assert ownership_node(read(client, current))["advisory_review"] is True
        with patch.object(OwnershipAnalysisService, "_current_for_readiness", return_value=False):
            assert ownership_node(read(client, current))["advisory_review"] is None


def test_an_accepted_basis_never_flags() -> None:
    with (
        mock_lane() as (client, _),
        patch.object(OwnershipAnalysisService, "poc_basis_accepted", return_value=True),
    ):
        node = ownership_node(read(client, xyz_at_ownership(client)))
        assert node["advisory_review"] is None


# Projection: the flag can never disagree with the node status --------------------------------


def projected(*, readiness: str, reference_id: str | None, analysis_id, advisory: bool):
    stage = SimpleNamespace(status=SimpleNamespace(value=readiness), reference_id=reference_id)
    ready = SimpleNamespace(status=SimpleNamespace(value="READY"), reference_id=None)
    automation = SimpleNamespace(
        active_exceptions=(), completed_at=None, completed_stages=(), created_at=NOW,
        current_stage=None, events=(), stage_order_version=2, status=AutomationStatus.RUNNING,
    )
    clm = SimpleNamespace(
        events=(), target_search_checkpoint=None,
        readiness=SimpleNamespace(blockers=(), document=ready, ownership=stage, evaluated_at=NOW),
        submission_plan=SimpleNamespace(environment=SimpleNamespace(value="SANDBOX")),
    )
    target = SimpleNamespace(
        dispatch_ready=False, kyc_customer_type=None, client_segment=None,
        registration_type=None, customer_external_system=None, policy=None,
        booking_entity=None,
    )
    case = SimpleNamespace(
        created_at=NOW, events=(), initial_identity=SimpleNamespace(),
        jurisdiction_resolution=None, registry_acquisition=None,
        policy_snapshot=SimpleNamespace(goldtier_target=target, bound_at=NOW),
        target_dispatch_confirmation=None,
    )
    nodes = project_processing_pipeline(
        automation=automation, clm=clm, case=case, reconciliation=None,
        target_operations=(), retained_goldtier_id=None,
        ownership=SimpleNamespace(analysis_id=analysis_id),
        ownership_review_advisory=advisory,
    )
    return next(node for node in nodes if node.node_id == "OWNERSHIP_UBO"), nodes


def test_the_projection_flags_only_the_record_readiness_completed() -> None:
    analysis_id = uuid4()
    node, nodes = projected(
        readiness="READY", reference_id=str(analysis_id), analysis_id=analysis_id, advisory=True
    )
    assert (node.status, node.advisory_review) == ("COMPLETE", True)
    assert {n.advisory_review for n in nodes if n.node_id != "OWNERSHIP_UBO"} == {None}


def test_a_superseded_record_never_flags() -> None:
    node, _ = projected(
        readiness="READY", reference_id=str(uuid4()), analysis_id=uuid4(), advisory=True
    )
    assert (node.status, node.advisory_review) == ("COMPLETE", None)


@pytest.mark.parametrize("readiness", ["REVIEW_REQUIRED", "FAILED", "IN_PROGRESS", "MISSING"])
def test_a_node_that_is_not_complete_never_flags(readiness: str) -> None:
    analysis_id = uuid4()
    node, _ = projected(
        readiness=readiness, reference_id=str(analysis_id), analysis_id=analysis_id, advisory=True
    )
    assert node.status != "COMPLETE"
    assert node.advisory_review is None


def test_without_the_callers_verdict_the_node_is_never_flagged() -> None:
    analysis_id = uuid4()
    node, _ = projected(
        readiness="READY", reference_id=str(analysis_id), analysis_id=analysis_id, advisory=False
    )
    assert node.advisory_review is None


def test_the_flag_is_optional_and_defaults_to_none() -> None:
    field = BrowserProcessingNode.model_fields["advisory_review"]
    assert field.default is None
    assert not field.is_required()
