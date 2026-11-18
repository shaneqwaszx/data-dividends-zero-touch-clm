"""OPQ S1: the computed per-stage presentation verdict (report section 7 matrix).

Synthetic, in memory, no network. Presentation only: node ``status``, ``advisory_review``,
readiness and every gate stay as they were (see test_stage_presentation_invariance.py).
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from test_marketplace_mock_partnerships import mock_lane, xyz_at_ownership
from test_ownership_analysis import run_scenario
from test_phase24_identity import attach_conflict, correction
from test_s1_pipeline_projection import NOW
from test_stage_presentation_invariance import (
    DEMO_SCENARIOS,
    opq_at_review,
    opq_body,
    opq_lane,
    summary_of,
)
from test_zero_touch_orchestration import build_system, start_demo

from app.api_models import BrowserProcessingNode, project_processing_pipeline
from app.connectors.mock_ownership import MockOwnershipScenario
from app.domain.access import TeamId
from app.domain.clm import ClmBlockerCode
from app.domain.zero_touch import AutomationStage, AutomationStatus
from app.stage_presentation import BrowserStagePresentation

S = AutomationStage
EXEMPT = "EXEMPT PRIVATE COMPANY LIMITED BY SHARES"


# Projection helpers ----------------------------------------------------------------------


def stage(value: str, reference_id: str | None = None):
    return SimpleNamespace(status=SimpleNamespace(value=value), reference_id=reference_id)


def exception(stage_value: AutomationStage, kind: str, exception_id=None):
    return SimpleNamespace(
        exception_id=exception_id or uuid4(), stage=stage_value, blocker_code=kind,
        exception_type=SimpleNamespace(value=kind), status="OPEN",
    )


def ownership_record(*, state="REVIEW_REQUIRED", relationships=1, issues=(), met=False):
    candidate = SimpleNamespace(
        threshold_result="MET" if met else "NOT_MET",
        classification="PROVISIONAL_UBO_CANDIDATE" if met else "BELOW_PROVISIONAL_THRESHOLD",
    )
    return SimpleNamespace(
        analysis_id=uuid4(), state=state, relationships=[object()] * relationships,
        issues=[SimpleNamespace(code=item) for item in issues], candidates=[candidate],
    )


def project(
    *,
    status=AutomationStatus.WAITING_FOR_REVIEW,
    current=S.READINESS,
    completed=(S.REGISTRY, S.GOLDTIER_SEARCH, S.DOCUMENT, S.OWNERSHIP),
    exceptions=(),
    registry="READY",
    document="READY",
    ownership_readiness="READY",
    blockers=(),
    evaluated=True,
    ownership=None,
    advisory=False,
    poc=False,
    reconciliation=None,
    acquisition=None,
    existing_target_state=None,
    error=None,
    ownership_reference: str | None = None,
) -> dict[str, BrowserProcessingNode]:
    automation = SimpleNamespace(
        active_exceptions=tuple(exceptions), completed_at=None, completed_stages=completed,
        created_at=NOW, current_stage=current, events=(), stage_order_version=2, status=status,
    )
    reference = ownership_reference or (
        str(ownership.analysis_id) if ownership is not None else None
    )
    clm = SimpleNamespace(
        events=(), target_search_checkpoint=None,
        readiness=SimpleNamespace(
            blockers=[ClmBlockerCode(item) for item in blockers],
            registry=stage(registry),
            document=stage(document),
            ownership=stage(ownership_readiness, reference),
            evaluated_at=NOW if evaluated else None,
        ),
        submission_plan=SimpleNamespace(environment=SimpleNamespace(value="SANDBOX")),
    )
    target = SimpleNamespace(
        dispatch_ready=False, kyc_customer_type=None, client_segment=None,
        registration_type=None, customer_external_system=None, policy=None, booking_entity=None,
    )
    case = SimpleNamespace(
        created_at=NOW, events=(), initial_identity=SimpleNamespace(),
        jurisdiction_resolution=None, registry_acquisition=acquisition,
        existing_target_state=existing_target_state, error=error,
        policy_snapshot=SimpleNamespace(goldtier_target=target, bound_at=NOW),
        target_dispatch_confirmation=None,
    )
    nodes = project_processing_pipeline(
        automation=automation, clm=clm, case=case, reconciliation=reconciliation,
        target_operations=(), retained_goldtier_id=None, ownership=ownership,
        ownership_review_advisory=advisory, ownership_poc_basis_accepted=poc,
    )
    return {node.node_id: node for node in nodes}


def verdict(node: BrowserProcessingNode) -> tuple:
    p = node.presentation
    assert p is not None
    return p.state, p.reason_code, p.counts_as_done, p.blocks_send


def discrepancy(field: str, discrepancy_id, status="OPEN"):
    return SimpleNamespace(discrepancy_id=discrepancy_id, field_name=field, status=status)


def reconciliation_with(*items, status="REVIEW_REQUIRED"):
    return SimpleNamespace(
        status=SimpleNamespace(value=status), discrepancies=list(items), updated_at=NOW,
    )


# Contract ---------------------------------------------------------------------------------


def test_the_field_is_optional_additive_and_on_top_level_stages_only() -> None:
    field = BrowserProcessingNode.model_fields["presentation"]
    assert field.default is None and not field.is_required()
    nodes = project()
    assert all(node.presentation is not None for node in nodes.values())
    assert all(
        child.presentation is None for node in nodes.values() for child in node.children
    )
    assert set(BrowserStagePresentation.model_fields) == {
        "state", "reason_code", "owned_exception_ids", "linked_exception_ids",
        "counts_as_done", "blocks_send",
    }


def test_the_existing_node_fields_are_identical_with_and_without_the_verdict() -> None:
    owned = ownership_record(issues=("OWNERSHIP_METHOD_UNSUPPORTED",), relationships=0)
    for node in project(ownership=owned, advisory=True).values():
        assert node.model_dump(exclude={"presentation"}) == node.model_copy(
            update={"presentation": None}
        ).model_dump(exclude={"presentation"})
    assert project(ownership=owned, advisory=True)["OWNERSHIP_UBO"].status == "COMPLETE"


# Matrix rows: generic states ----------------------------------------------------------------


def test_not_started_waiting_for_earlier_steps_does_not_block_or_count() -> None:
    nodes = project(
        status=AutomationStatus.RUNNING, current=S.REGISTRY, completed=(),
        registry="IN_PROGRESS", document="MISSING", ownership_readiness="MISSING",
        blockers=("DOCUMENT_REQUIRED", "OWNERSHIP_REQUIRED"),
    )
    assert nodes["OWNERSHIP_UBO"].status == "BLOCKED"
    assert verdict(nodes["OWNERSHIP_UBO"]) == (
        "NOT_STARTED", "WAITING_FOR_EARLIER_STEPS", False, False
    )
    assert verdict(nodes["DOCUMENT_IDP"])[0] == "NOT_STARTED"
    assert verdict(nodes["FINAL_REVIEW_SEND"]) == ("NOT_STARTED", None, False, False)


def test_running_is_not_done() -> None:
    nodes = project(
        status=AutomationStatus.RUNNING, current=S.DOCUMENT, completed=(S.REGISTRY,),
        document="IN_PROGRESS", blockers=("DOCUMENT_PROCESSING",),
    )
    assert verdict(nodes["DOCUMENT_IDP"]) == ("RUNNING", None, False, True)


def test_complete_counts_and_does_not_block() -> None:
    nodes = project()
    for node_id in ("CASE_START", "DOCUMENT_IDP", "OWNERSHIP_UBO", "READINESS"):
        assert verdict(nodes[node_id]) == ("COMPLETE", None, True, False)


def test_failed_stage_blocks() -> None:
    nodes = project(ownership_readiness="FAILED", blockers=("OWNERSHIP_ANALYSIS_FAILED",))
    state, _, done, blocks = verdict(nodes["OWNERSHIP_UBO"])
    assert (state, done, blocks) == ("FAILED", False, True)


def test_readiness_blocked_only_by_earlier_stages_references_without_recounting() -> None:
    nodes = project(
        current=S.READINESS, ownership_readiness="REVIEW_REQUIRED",
        blockers=("OWNERSHIP_REVIEW_REQUIRED",),
    )
    assert verdict(nodes["READINESS"])[:2] == ("BLOCKED", "EARLIER_STAGE_BLOCKERS")
    assert nodes["READINESS"].presentation.owned_exception_ids == ()
    assert verdict(nodes["GOLDTIER_TARGET"])[:2] == ("BLOCKED", "EARLIER_STAGE_BLOCKERS")


def test_readiness_owns_the_classification_blocker() -> None:
    nodes = project(blockers=("GOLDTIER_CLASSIFICATION_REQUIRED",))
    assert verdict(nodes["READINESS"]) == (
        "ACTION_REQUIRED", "GOLDTIER_CLASSIFICATION_REQUIRED", False, True
    )
    assert verdict(nodes["OWNERSHIP_UBO"]) == ("COMPLETE", None, True, False)
    assert verdict(nodes["GOLDTIER_TARGET"])[:2] == ("BLOCKED", "EARLIER_STAGE_BLOCKERS")


def test_final_confirmation_is_an_action_but_neither_an_issue_nor_a_send_blocker() -> None:
    nodes = project(exceptions=(exception(S.READINESS, "TARGET_CONFIRMATION_REQUIRED"),))
    final = nodes["FINAL_REVIEW_SEND"]
    assert final.status == "REVIEW_REQUIRED"
    assert verdict(final) == ("ACTION_REQUIRED", "FINAL_CONFIRMATION_REQUIRED", False, False)
    assert all(not node.presentation.owned_exception_ids for node in nodes.values())


# Matrix rows: Registry verification ----------------------------------------------------------


def test_registry_partial_source_is_complete_with_an_informational_reason() -> None:
    acquisition = SimpleNamespace(
        status=SimpleNamespace(value="PARTIAL"), operation_results=(), retrieved_at=NOW,
    )
    nodes = project(acquisition=acquisition)
    assert nodes["ACRA_REGISTRY"].status == "COMPLETE"
    assert verdict(nodes["ACRA_REGISTRY"]) == (
        "COMPLETE", "OWNERSHIP_SOURCE_PARTIAL", True, False
    )


def test_registry_skipped_after_a_verified_match_counts_as_done() -> None:
    nodes = project(existing_target_state=SimpleNamespace(target_party_id="GT-1"))
    assert nodes["ACRA_REGISTRY"].status == "SKIPPED"
    assert verdict(nodes["ACRA_REGISTRY"]) == (
        "SKIPPED", "VERIFIED_GOLDTIER_MATCH", True, False
    )


def test_registry_failure_is_failed() -> None:
    acquisition = SimpleNamespace(
        status=SimpleNamespace(value="FAILED"), operation_results=(), retrieved_at=NOW,
    )
    nodes = project(
        acquisition=acquisition, error=SimpleNamespace(code="ACRA_UNAVAILABLE"),
        blockers=("REGISTRY_FAILED",),
    )
    assert verdict(nodes["ACRA_REGISTRY"]) == ("FAILED", "ACRA_UNAVAILABLE", False, True)


def test_uen_conflict_is_owned_by_document_and_linked_from_registry_once() -> None:
    conflict_id = uuid4()
    other_id = uuid4()
    nodes = project(
        current=S.DOCUMENT, completed=(S.REGISTRY, S.GOLDTIER_SEARCH),
        document="REVIEW_REQUIRED", ownership_readiness="MISSING",
        blockers=("DOCUMENT_REVIEW_INCOMPLETE", "OWNERSHIP_REQUIRED"),
        exceptions=(
            exception(S.DOCUMENT, "DOCUMENT_SOURCE_CONFLICT", conflict_id),
            exception(S.DOCUMENT, "DOCUMENT_SOURCE_CONFLICT", other_id),
        ),
        reconciliation=reconciliation_with(
            discrepancy("registration_identifier", conflict_id),
            discrepancy("legal_name", other_id),
        ),
    )
    registry = nodes["ACRA_REGISTRY"]
    assert registry.status == "COMPLETE"  # execution status unchanged (phase24 pin)
    assert verdict(registry) == (
        "ACTION_REQUIRED", "IDENTITY_CONFIRMATION_REQUIRED", False, True
    )
    assert registry.presentation.linked_exception_ids == (str(conflict_id),)
    assert registry.presentation.owned_exception_ids == ()
    document = nodes["DOCUMENT_IDP"].presentation
    assert document.state == "ACTION_REQUIRED"
    assert document.owned_exception_ids == (str(conflict_id), str(other_id))
    assert set(nodes["RECONCILIATION"].presentation.linked_exception_ids) == {
        str(conflict_id), str(other_id)
    }
    owned = [item for node in nodes.values() for item in node.presentation.owned_exception_ids]
    assert sorted(owned) == sorted([str(conflict_id), str(other_id)])
    assert verdict(nodes["OWNERSHIP_UBO"]) == (
        "NOT_STARTED", "WAITING_FOR_EARLIER_STEPS", False, False
    )


@pytest.mark.parametrize("closed", ["RESOLVED", "CANCELLED"])
def test_a_closed_identity_discrepancy_returns_registry_to_complete(closed: str) -> None:
    conflict_id = uuid4()
    nodes = project(reconciliation=reconciliation_with(
        discrepancy("registration_identifier", conflict_id, status=closed), status="RESOLVED",
    ))
    assert verdict(nodes["ACRA_REGISTRY"]) == ("COMPLETE", None, True, False)
    assert nodes["ACRA_REGISTRY"].presentation.linked_exception_ids == ()


# Matrix rows: Ownership & UBO ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("relationships", "issues"),
    [
        (0, ("INCOMPLETE_LEGAL_ENTITY", "OWNERSHIP_METHOD_UNSUPPORTED")),  # OPQ A1
        (0, ("OWNERSHIP_REQUIRED",)),  # OPQ A2, empty register
        (2, ("OWNERSHIP_METHOD_UNSUPPORTED",)),
    ],
)
def test_advisory_review_without_evidence_is_advised_and_not_done(relationships, issues) -> None:
    owned = ownership_record(relationships=relationships, issues=issues)
    node = project(ownership=owned, advisory=True)["OWNERSHIP_UBO"]
    assert (node.status, node.advisory_review) == ("COMPLETE", True)  # D-121/D-141 unchanged
    assert verdict(node) == ("REVIEW_ADVISED", "EVIDENCE_ABSENT", False, False)


def test_advisory_review_with_a_calculated_structure_reports_review_issues() -> None:
    owned = ownership_record(relationships=2, issues=("OWNERSHIP_DENOMINATOR_REQUIRED",))
    node = project(ownership=owned, advisory=True)["OWNERSHIP_UBO"]
    assert verdict(node) == ("REVIEW_ADVISED", "REVIEW_ISSUES", False, False)


def test_an_accepted_poc_basis_is_complete_with_its_reason() -> None:
    owned = ownership_record(relationships=2, issues=("UBO_REVIEW_REQUIRED",))
    node = project(ownership=owned, poc=True)["OWNERSHIP_UBO"]
    assert node.advisory_review is None
    assert verdict(node) == ("COMPLETE", "POC_BASIS_ACCEPTED", True, False)


def test_a_valid_zero_ubo_analysis_is_complete_not_an_error() -> None:
    record = run_scenario(MockOwnershipScenario.BELOW_THRESHOLD)
    assert record.state == "ANALYZED" and record.relationships and record.candidates
    node = project(ownership=record)["OWNERSHIP_UBO"]
    assert verdict(node) == ("COMPLETE", "NO_QUALIFYING_UBO", True, False)


def test_an_analysis_with_a_qualifying_ubo_is_plain_complete() -> None:
    owned = ownership_record(state="ANALYZED", relationships=2, met=True)
    assert verdict(project(ownership=owned)["OWNERSHIP_UBO"]) == ("COMPLETE", None, True, False)


def test_blocking_mode_review_is_action_required_and_blocks() -> None:
    owned = ownership_record(relationships=2, issues=("UBO_REVIEW_REQUIRED",))
    node = project(
        ownership=owned, ownership_readiness="REVIEW_REQUIRED",
        blockers=("OWNERSHIP_REVIEW_REQUIRED",),
    )["OWNERSHIP_UBO"]
    assert node.status == "REVIEW_REQUIRED"
    assert verdict(node)[0::2] == ("ACTION_REQUIRED", False)
    assert node.presentation.blocks_send is True


def test_a_superseded_analysis_is_never_advised_or_given_an_ownership_reason() -> None:
    owned = ownership_record(relationships=0, issues=("OWNERSHIP_REQUIRED",))
    node = project(ownership=owned, advisory=True, ownership_reference=str(uuid4()))[
        "OWNERSHIP_UBO"
    ]
    assert (node.status, node.advisory_review) == ("COMPLETE", None)  # D-141 unchanged
    assert verdict(node) == ("COMPLETE", None, True, False)


def test_an_open_ownership_exception_outranks_any_completion() -> None:
    owned = ownership_record(relationships=0, issues=("OWNERSHIP_REQUIRED",))
    held = exception(S.OWNERSHIP, "OWNERSHIP_REVIEW_REQUIRED")
    node = project(ownership=owned, advisory=True, exceptions=(held,))["OWNERSHIP_UBO"]
    assert verdict(node) == ("ACTION_REQUIRED", "OWNERSHIP_REVIEW_REQUIRED", False, True)
    assert node.presentation.owned_exception_ids == (str(held.exception_id),)


def test_every_open_exception_is_owned_by_exactly_one_stage() -> None:
    items = (
        exception(S.REGISTRY, "REGISTRY_REVIEW_REQUIRED"),
        exception(S.REGISTRY, "JURISDICTION_UNRESOLVED"),
        exception(S.GOLDTIER_SEARCH, "EXISTING_PARTY_REVIEW_REQUIRED"),
        exception(S.DOCUMENT, "DOCUMENT_LOW_CONFIDENCE"),
        exception(S.OWNERSHIP, "OWNERSHIP_INCOMPLETE"),
        exception(S.READINESS, "TARGET_CLASSIFICATION_REQUIRED"),
        exception(S.MOCK_GOLDTIER, "TARGET_PARTIAL_REVIEW_REQUIRED"),
        exception(S.READINESS, "TARGET_CONFIRMATION_REQUIRED"),
    )
    nodes = project(exceptions=items)
    owned = [item for node in nodes.values() for item in node.presentation.owned_exception_ids]
    assert sorted(owned) == sorted(str(item.exception_id) for item in items[:-1])
    assert nodes["JURISDICTION"].presentation.owned_exception_ids == (str(items[1].exception_id),)


# API: OPQ-like, XYZ, UEN conflict and demo cases ---------------------------------------------


def stages(summary: dict) -> dict[str, dict]:
    return {node["node_id"]: node for node in summary["processing_pipeline"]}


@pytest.mark.parametrize(
    ("constitution", "company_type"), [(None, EXEMPT), (EXEMPT, None)],
    ids=["company_type_only", "empty_register"],
)
def test_opq_like_zero_evidence_review_is_advised_and_not_done(constitution, company_type):
    with opq_lane(opq_body(constitution=constitution, company_type=company_type)) as (client, _):
        summary = summary_of(client, opq_at_review(client)["case"]["case_id"])
        node = stages(summary)["OWNERSHIP_UBO"]
        assert (node["status"], node["advisory_review"]) == ("COMPLETE", True)
        presentation = node["presentation"]
        assert presentation["state"] == "REVIEW_ADVISED"
        assert presentation["reason_code"] == "EVIDENCE_ABSENT"
        assert presentation["counts_as_done"] is False
        # Existing gates: the advisory review holds nothing (D-121); only the separate
        # classification blocker holds the company-type-only variant.
        assert presentation["blocks_send"] is False
        readiness = stages(summary)["READINESS"]["presentation"]
        blockers = summary["clm"]["readiness"]["blockers"]
        assert readiness["blocks_send"] is bool(blockers)
        assert ("GOLDTIER_CLASSIFICATION_REQUIRED" in blockers) is (constitution is None)


def test_xyz_advisory_and_blocking_modes(monkeypatch) -> None:
    with mock_lane() as (client, _):
        advised = stages(summary_of(client, xyz_at_ownership(client)["case"]["case_id"]))
    assert advised["OWNERSHIP_UBO"]["presentation"]["state"] == "REVIEW_ADVISED"
    assert advised["OWNERSHIP_UBO"]["presentation"]["counts_as_done"] is False
    monkeypatch.setenv("ACRA_MARKETPLACE_UBO_REVIEW_MODE", "blocking")
    with mock_lane() as (client, _):
        held = stages(summary_of(client, xyz_at_ownership(client)["case"]["case_id"]))
    assert held["OWNERSHIP_UBO"]["status"] == "REVIEW_REQUIRED"
    assert held["OWNERSHIP_UBO"]["presentation"]["state"] == "ACTION_REQUIRED"
    assert held["OWNERSHIP_UBO"]["presentation"]["blocks_send"] is True


def conflict_case():
    client, zero, documents, target, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic",
                              team_id=TeamId.TEAM_A, created_by_actor_id="maya-lim")
    record = attach_conflict(zero, record)
    return client, zero, documents, record


def test_uen_conflict_registry_links_the_document_exception() -> None:
    client, _, _, record = conflict_case()
    summary = summary_of(client, str(record.case_id))
    nodes = stages(summary)
    [conflict] = [item for item in summary["active_exceptions"] if item["stage"] == "DOCUMENT"]
    registry = nodes["ACRA_REGISTRY"]
    assert registry["status"] == "COMPLETE"
    assert registry["presentation"]["state"] == "ACTION_REQUIRED"
    assert registry["presentation"]["reason_code"] == "IDENTITY_CONFIRMATION_REQUIRED"
    assert registry["presentation"]["linked_exception_ids"] == [conflict["exception_id"]]
    assert registry["presentation"]["owned_exception_ids"] == []
    assert nodes["DOCUMENT_IDP"]["presentation"]["owned_exception_ids"] == [
        conflict["exception_id"]
    ]
    owned = [i for n in nodes.values() for i in n["presentation"]["owned_exception_ids"]]
    assert owned == [conflict["exception_id"]]
    assert nodes["OWNERSHIP_UBO"]["presentation"]["state"] == "NOT_STARTED"


def test_uen_conflict_resolves_on_the_entered_choice() -> None:
    client, zero, _, record = conflict_case()
    current = zero._repository.get_for_case(record.case_id)
    assert correction(client, zero, current, choice="ENTERED", uen="202400001A").status_code == 200
    nodes = stages(summary_of(client, str(record.case_id)))
    assert nodes["ACRA_REGISTRY"]["presentation"]["state"] == "COMPLETE"
    assert nodes["ACRA_REGISTRY"]["presentation"]["linked_exception_ids"] == []
    assert nodes["DOCUMENT_IDP"]["presentation"]["state"] == "COMPLETE"
    assert nodes["FINAL_REVIEW_SEND"]["presentation"]["reason_code"] == (
        "FINAL_CONFIRMATION_REQUIRED"
    )


def test_uen_conflict_resolves_on_the_document_choice() -> None:
    client, zero, documents, record = conflict_case()
    document = documents.list_documents(case_id=record.case_id)[0]
    current = zero._repository.get_for_case(record.case_id)
    response = correction(
        client, zero, current, choice="DOCUMENT", uen="202400009I",
        document_id=str(document.document_id),
        expected_document_event_count=len(document.events),
    )
    assert response.status_code == 200
    summary = summary_of(client, str(record.case_id))
    nodes = stages(summary)
    registry = nodes["ACRA_REGISTRY"]["presentation"]
    assert registry["reason_code"] != "IDENTITY_CONFIRMATION_REQUIRED"
    assert registry["linked_exception_ids"] == []
    document_exceptions = sorted(
        item["exception_id"] for item in summary["active_exceptions"]
        if item["stage"] == "DOCUMENT"
    )
    # Any new name/address conflicts from the synthetic registry are owned by Document only.
    assert sorted(nodes["DOCUMENT_IDP"]["presentation"]["owned_exception_ids"]) == (
        document_exceptions
    )


@pytest.mark.parametrize("scenario", DEMO_SCENARIOS)
def test_demo_cases_count_each_open_exception_once(scenario: str) -> None:
    client, _, _, _, _ = build_system(require_confirmation=True)
    summary = summary_of(
        client, start_demo(client, scenario, confirm_if_required=False)["case"]["case_id"]
    )
    nodes = summary["processing_pipeline"]
    owned = [i for n in nodes for i in n["presentation"]["owned_exception_ids"]]
    expected = [
        item["exception_id"] for item in summary["active_exceptions"]
        if item["exception_type"] != "TARGET_CONFIRMATION_REQUIRED"
    ]
    assert sorted(owned) == sorted(expected)
    for node in nodes:
        presentation = node["presentation"]
        assert presentation["counts_as_done"] is (
            presentation["state"] in {"COMPLETE", "SKIPPED"}
        )
        assert all(child.get("presentation") is None for child in node["children"])
