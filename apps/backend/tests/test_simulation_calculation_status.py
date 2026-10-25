"""Presentation-only status for a completed declared-overlay simulation.

The historical D-077 five-layer simulation is mathematically complete, so the API reports
`simulation_calculated` instead of leaving the UI with a generic calculation-error warning.
The flag never changes the analysis, its issues, readiness or POC acceptance, and genuine
defects (including ones masked by the priority-chosen legal-form issue) keep it false.
Offline only: allowlisted protocol transport, in-memory persistence, Mock GoldTier.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from scripts.five_layer_hybrid_fixture import FIVE_LAYER_FIELDS
from test_hybrid_five_layer_overlay import analyze, build, by_name
from test_poc_ownership_acceptance import (
    garden_transport,
    lane,
    ownership_of,
    runtime,
    summary_of,
)
from test_slice_b_registry_demo import start

from app.connectors.hybrid_ownership_overlay import FIVE_LAYER_ROOT_UEN, POC_EQUAL_UNITS_PROVIDER
from app.domain.ownership import (
    OwnershipAnalysisIssue,
    OwnershipAnalysisRecord,
    OwnershipAnalysisState,
    OwnershipIssueCode,
    OwnershipProvenance,
    OwnershipThresholdResult,
)
from app.persistence.composition import build_persistence_bundle
from app.services.ownership_analysis import simulation_calculation_complete

FIVE_LAYER_AGGREGATES = {
    "BEATRICE LIM (SYNTHETIC PERSON)": Decimal("30"),
    "DIANA KOH (SYNTHETIC PERSON)": Decimal("25"),
    "ALEX TAN (SYNTHETIC PERSON)": Decimal("20"),
    "EDWARD NG (SYNTHETIC PERSON)": Decimal("15"),
    "CHARLES ONG (SYNTHETIC PERSON)": Decimal("10"),
}


def five_layer() -> OwnershipAnalysisRecord:
    onboarding, ownership, _ = build()
    return analyze(onboarding, ownership, FIVE_LAYER_ROOT_UEN)


def test_the_historical_five_layer_simulation_is_reported_as_calculated_unchanged() -> None:
    record = five_layer()
    # Scenario A arithmetic and review state are exactly the historical values.
    assert {
        name: item.aggregated_ownership_percent for name, item in by_name(record).items()
    } == FIVE_LAYER_AGGREGATES
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert {item.code for item in record.issues} == {
        OwnershipIssueCode.SYNTHETIC_OWNERSHIP_EVIDENCE,
        OwnershipIssueCode.OWNERSHIP_METHOD_UNSUPPORTED,
    }
    assert record.poc_acceptance is None
    assert simulation_calculation_complete(record) is True


def test_a_poc_equal_unit_case_keeps_its_own_presentation() -> None:
    # Garden carries D-081 links; its calculated-for-verification banner is unchanged.
    from test_poc_ownership_acceptance import accepted_record

    _, ownership, record = accepted_record()
    assert any(
        edge.provenance.provider == POC_EQUAL_UNITS_PROVIDER for edge in record.relationships
    )
    assert simulation_calculation_complete(record) is False
    assert ownership.simulation_calculated(record) is False


def _issue(code: OwnershipIssueCode) -> Any:
    return lambda r: {"issues": [*r.issues, OwnershipAnalysisIssue(code=code, message="Synth.")]}


DEFECTS: dict[str, Any] = {
    "an independent contradiction": _issue(OwnershipIssueCode.CONTRADICTORY_OWNERSHIP_EVIDENCE),
    "an unresolved corporate branch": _issue(OwnershipIssueCode.CORPORATE_OWNERSHIP_UNRESOLVED),
    "a cycle": _issue(OwnershipIssueCode.CYCLE_DETECTED),
    "an unresolved person identity issue": _issue(OwnershipIssueCode.PERSON_IDENTITY_UNRESOLVED),
    "an unexplained review issue": _issue(OwnershipIssueCode.UBO_REVIEW_REQUIRED),
    "a duplicated issue": _issue(OwnershipIssueCode.SYNTHETIC_OWNERSHIP_EVIDENCE),
    "no synthetic marker": lambda r: {
        "issues": [
            item
            for item in r.issues
            if item.code != OwnershipIssueCode.SYNTHETIC_OWNERSHIP_EVIDENCE
        ]
    },
    "an incomplete topology": lambda r: {
        "discovery": r.discovery.model_copy(update={"topology_complete": False})
    },
    "an unresolved person": lambda r: {
        "discovery": r.discovery.model_copy(
            update={"unresolved_person_party_ids": (r.candidates[0].party.party_id,)}
        )
    },
    "an uncalculated person": lambda r: {
        "candidates": [
            r.candidates[0].model_copy(
                update={"synthetic_basis_threshold_result": OwnershipThresholdResult.INDETERMINATE}
            ),
            *r.candidates[1:],
        ]
    },
    "a non-overlay link": lambda r: {
        "relationships": [
            r.relationships[0].model_copy(
                update={
                    "provenance": OwnershipProvenance(
                        provider="ACRA_REGISTRY_ACQUISITION",
                        environment="MOCK",
                        source_reference="SYNTHETIC",
                        sourced_at=r.relationships[0].provenance.sourced_at,
                    )
                }
            ),
            *r.relationships[1:],
        ]
    },
    # A genuine defect hidden behind the priority-chosen OWNERSHIP_METHOD_UNSUPPORTED code.
    "masked unquantified share evidence": lambda r: {
        "evidence": (
            *r.evidence,
            _evidence(r, kind="SHARE_UNITS", raw_value="1", entity_identifier=FIVE_LAYER_ROOT_UEN),
        )
    },
    "masked unbound evidence": lambda r: {
        "evidence": (*r.evidence, _evidence(r, kind="CONTROL", entity_identifier=None))
    },
    # QG P3: an ownership-like root role hidden by the legal-form issue is not "calculated".
    "a masked ownership-like root role": lambda r: {
        "evidence": (*r.evidence, _evidence(r, kind="ROLE", raw_value="OWNER"))
    },
    # QG P3-A: an ownership-like role retained on an intermediate issuer is not "calculated".
    "an ownership-like intermediate role": lambda r: _intermediate_role(r, "OWNER"),
    "a non-review state": lambda r: {"state": OwnershipAnalysisState.ANALYZED},
    "a non-hybrid source": lambda r: {"source_classification": "SINGLE_SOURCE"},
    "no relationships": lambda r: {"relationships": []},
}


def _evidence(record: OwnershipAnalysisRecord, **update: Any) -> Any:
    from datetime import UTC, datetime

    from app.domain.ownership_evidence import OwnershipEvidence

    base = {
        "evidence_id": "e-" + "0" * 48,
        "entity_identifier": FIVE_LAYER_ROOT_UEN,
        "party_id": "SYNTHETIC-DEFECT",
        "kind": "CONTROL",
        "raw_value": "CONTROL",
        "source_operation": "OFFICERS",
        "provider": "ACRA_REGISTRY_ACQUISITION",
        "environment": "MOCK",
        "retrieved_at": datetime(2026, 10, 25, tzinfo=UTC),
        "evidence_version": 1,
    }
    return OwnershipEvidence.model_construct(**{**base, **update})


def _intermediate_role(record: OwnershipAnalysisRecord, role: str) -> dict[str, Any]:
    from datetime import UTC, datetime

    from app.domain.ownership import OfficialOfficerRoleObservation

    observation = OfficialOfficerRoleObservation(
        role=role,
        status="CURRENT",
        source_operation="OFFICERS",
        retrieved_at=datetime(2026, 10, 25, tzinfo=UTC),
    )
    first = record.discovery.records[0].model_copy(  # type: ignore[union-attr]
        update={
            "identity_basis": "OFFICIAL_MOCK_ENTITY_PROFILE",
            "official_officer_roles": (observation,),
        }
    )
    return {
        "discovery": record.discovery.model_copy(  # type: ignore[union-attr]
            update={"records": (first, *record.discovery.records[1:])}  # type: ignore[union-attr]
        )
    }


def test_a_non_ownership_intermediate_role_keeps_the_simulation_status() -> None:
    record = five_layer()
    assert simulation_calculation_complete(
        record.model_copy(update=_intermediate_role(record, "DIRECTOR"))
    )


@pytest.mark.parametrize("name", sorted(DEFECTS))
def test_genuine_defects_keep_the_simulation_status_false(name: str) -> None:
    record = five_layer()
    assert simulation_calculation_complete(record) is True
    mutated = record.model_copy(update=DEFECTS[name](record))
    assert simulation_calculation_complete(mutated) is False


@pytest.mark.parametrize("acceptance", ["disabled", "accept_eligible_poc"])
def test_the_api_reports_the_status_without_any_readiness_or_acceptance(acceptance: str) -> None:
    settings = lane(acceptance)
    with runtime(settings, build_persistence_bundle(settings), garden_transport()) as client:
        case_id = start(client, FIVE_LAYER_FIELDS, "five-layer-marketplace-hybrid-client.pdf")[
            "case"
        ]["case_id"]
        ownership = ownership_of(client, case_id)
        summary = summary_of(client, case_id)
    assert (
        ownership["state"],
        ownership["simulation_calculated"],
        ownership["poc_basis_accepted"],
        ownership["poc_acceptance"],
    ) == ("REVIEW_REQUIRED", True, False, None)
    assert {
        item["party"]["display_name"]: Decimal(item["aggregated_ownership_percent"])
        for item in ownership["candidates"]
    } == FIVE_LAYER_AGGREGATES
    assert all(item["classification"] == "REVIEW_REQUIRED" for item in ownership["candidates"])
    # The authoritative workflow is unchanged: ownership still blocks; nothing is sent.
    assert "OWNERSHIP_REVIEW_REQUIRED" in summary["clm"]["readiness"]["blockers"]
    assert (summary["status"], summary["current_stage"]) == ("WAITING_FOR_REVIEW", "OWNERSHIP")
    assert summary["case"].get("goldtier_result") is None


def test_entity_effective_interests_come_from_the_engine_paths_and_change_nothing() -> None:
    onboarding, ownership, _ = build()
    record = analyze(onboarding, ownership, FIVE_LAYER_ROOT_UEN)
    names = {party.party_id: party.display_name for party in record.parties}
    interests = ownership.entity_effective_interests(record)
    totals = {
        names[party_id]: sum((path.effective_ownership_percent for path in paths), Decimal("0"))
        for party_id, paths in interests.items()
    }
    assert totals == {
        "FIVE LAYER L2 HOLDINGS (SYNTHETIC)": Decimal("80"),
        "FIVE LAYER L3 INVESTMENTS (SYNTHETIC)": Decimal("50"),
        "FIVE LAYER L4A CAPITAL (SYNTHETIC)": Decimal("30"),
        "FIVE LAYER L4B VENTURES (SYNTHETIC)": Decimal("20"),
        "FIVE LAYER L5 HOLDCO (SYNTHETIC)": Decimal("40"),
    }
    l5 = next(
        paths
        for party_id, paths in interests.items()
        if names[party_id].startswith("FIVE LAYER L5")
    )
    assert sorted(path.calculation for path in l5) == [
        "80% x 62.5% x 40% x 50% = 10%",
        "80% x 62.5% x 60% x 100% = 30%",
    ]
    # Only legal entities; the root and every person are excluded, and the analysis,
    # its candidates and readiness are untouched (presentation only).
    assert all(
        record.parties[[p.party_id for p in record.parties].index(party_id)].party_type
        == "LEGAL_ENTITY"
        for party_id in interests
    )
    assert record.root_party_id not in interests
    assert {
        item.party.display_name: item.aggregated_ownership_percent for item in record.candidates
    } == FIVE_LAYER_AGGREGATES
    assert ownership.get(case_id=record.case_id) == record


def _limited(onboarding: Any, **limits: int) -> Any:
    from test_hybrid_five_layer_overlay import settings as five_layer_settings

    from app.composition import build_ownership_analysis_service

    return build_ownership_analysis_service(
        onboarding, five_layer_settings().model_copy(update=limits)
    )


def _extra_edge(record: OwnershipAnalysisRecord, parent: str, child: str, percent: str) -> Any:
    template = record.relationships[0]
    by_name = {party.display_name: party.party_id for party in record.parties}
    # Validated eagerly with a safe id, so a test never passes through a validation catch.
    edge = type(template).model_validate(
        {
            **template.model_dump(),
            "relationship_id": "SYNTHETIC-EXTRA-EDGE",
            "parent_party_id": by_name[parent],
            "child_party_id": by_name[child],
            "ownership_percent": Decimal(percent),
        }
    )
    return record.model_copy(update={"relationships": [*record.relationships, edge]})


def _entity_totals(record: OwnershipAnalysisRecord) -> tuple[dict[str, Decimal], set[str]]:
    """The engine's opted-in entity totals and issue codes for a record (test oracle)."""
    from app.connectors.ownership import OwnershipSourceResult
    from app.services.ownership_analysis import build_ownership_graph, calculate_ownership_paths

    calculation = calculate_ownership_paths(
        build_ownership_graph(
            OwnershipSourceResult(
                root_party_id=record.root_party_id,
                parties=list(record.parties),
                relationships=list(record.relationships),
            )
        ),
        max_depth=8,
        max_paths_per_candidate=64,
        max_total_paths=256,
        include_entity_paths=True,
    )
    names = {party.party_id: party.display_name for party in record.parties}
    totals = {
        names[party_id]: sum((path.effective_ownership_percent for path in paths), Decimal("0"))
        for party_id, paths in calculation.entity_paths_by_party.items()
    }
    return totals, {issue.code.value for issue in calculation.issues}


L2 = "FIVE LAYER L2 HOLDINGS (SYNTHETIC)"
L5 = "FIVE LAYER L5 HOLDCO (SYNTHETIC)"


def test_entity_interests_fail_closed_when_bounded_cyclic_or_over_allocated() -> None:
    onboarding, ownership, _ = build()
    record = analyze(onboarding, ownership, FIVE_LAYER_ROOT_UEN)
    assert ownership.entity_effective_interests(record)
    # Depth or path limit: a partial traversal is never shown.
    assert _limited(onboarding, ownership_max_depth=2).entity_effective_interests(record) == {}
    assert (
        _limited(onboarding, ownership_max_total_paths=3).entity_effective_interests(record) == {}
    )
    # An excluded cycle (L5 back to L2) and an over-allocated entity (a parallel 60% into
    # L2, total 140) are withheld rather than shown with an unqualified aggregate.
    cyclic = _extra_edge(record, L5, L2, "10")
    assert "CYCLE_DETECTED" in _entity_totals(cyclic)[1]
    assert ownership.entity_effective_interests(cyclic) == {}
    root = next(
        party.display_name for party in record.parties if party.party_id == record.root_party_id
    )
    over = _extra_edge(record, root, L2, "60")
    # The oracle proves the graph builds and only the over-100 rule withholds it.
    totals, codes = _entity_totals(over)
    assert totals[L2] == Decimal("140")
    assert not codes & {"PATH_LIMIT_EXCEEDED", "MAXIMUM_DEPTH_EXCEEDED", "CYCLE_DETECTED"}
    assert ownership.entity_effective_interests(over) == {}
    assert (
        ownership.entity_effective_interests(record.model_copy(update={"relationships": []})) == {}
    )


def test_analysis_never_builds_entity_paths_so_its_outcomes_are_mains() -> None:
    # QG P2-A: the analysis, discovery and advice use the default, which records no entity
    # evidence; only the presentation method opts in.
    from app.connectors.ownership import OwnershipSourceResult
    from app.services.ownership_analysis import build_ownership_graph, calculate_ownership_paths

    onboarding, ownership, _ = build()
    record = analyze(onboarding, ownership, FIVE_LAYER_ROOT_UEN)
    graph = build_ownership_graph(
        OwnershipSourceResult(
            root_party_id=record.root_party_id,
            parties=list(record.parties),
            relationships=list(record.relationships),
        )
    )
    default = calculate_ownership_paths(
        graph, max_depth=8, max_paths_per_candidate=64, max_total_paths=256
    )
    opted = calculate_ownership_paths(
        graph,
        max_depth=8,
        max_paths_per_candidate=64,
        max_total_paths=256,
        include_entity_paths=True,
    )
    assert default.entity_paths_by_party == {}
    assert opted.entity_paths_by_party
    assert (default.paths_by_party, default.issues, default.unresolved_entity_shares) == (
        opted.paths_by_party,
        opted.issues,
        opted.unresolved_entity_shares,
    )
