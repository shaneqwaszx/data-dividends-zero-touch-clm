"""D-086a: the operator OPQ selector chooses a variant only at a case's first overlay analysis.

A case that already recorded ``discovery.overlay_scenario_id`` keeps that catalogued
variant on every later analysis, whatever the current selector says. An unknown id, an id
for another root, or missing/stale official evidence gives no overlay, never a fallback to
the selector. Provenance labels, the official-evidence gate and D-112 O7 are unchanged.
Offline only: allowlisted protocol transport, in-memory persistence, Mock GoldTier.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from test_opq_garden_sim_lim_scenario import EXPECTED, OBSERVED_OPQ_POSITIONS, opq_transport
from test_poc_ownership_acceptance import lane, service_lane
from test_simulation_calculation_status import FIVE_LAYER_AGGREGATES

from app.composition import build_ownership_analysis_service
from app.connectors.hybrid_ownership_overlay import (
    FIVE_LAYER_ROOT_UEN,
    FIVE_LAYER_SCENARIO_ID,
    GARDEN_DIRECT_OVERLAY_SCENARIO_ID,
    OFFICIAL_MARKETPLACE_PROFILE_REFERENCE,
    OPQ_GARDEN_ABC_SCENARIO_ID,
    OPQ_GARDEN_SIM_LIM_SCENARIO_ID,
    OVERLAY_RELATIONSHIP_PROVIDER,
    HybridOwnershipOverlayCatalogue,
    catalogued_hybrid_overlay_scenarios,
    hybrid_overlay_scenarios,
)
from app.domain.ownership import (
    OwnershipAnalysisRecord,
    OwnershipAnalysisState,
    OwnershipDocumentBinding,
    OwnershipEnvironment,
)
from app.services.ownership_analysis import (
    OwnershipAnalysisService,
    _recorded_overlay_scenario_id,
)
from app.services.ownership_repository import InMemoryOwnershipAnalysisRepository

GARDEN_UEN = "11111999A"
CHAIN = "garden_sim_lim_chain"
FIVE_LAYER = "five_layer_simulation"
VARIANTS = (FIVE_LAYER, CHAIN, "garden_abc_multi_holder")
ALL_IDS = {
    GARDEN_DIRECT_OVERLAY_SCENARIO_ID,
    FIVE_LAYER_SCENARIO_ID,
    OPQ_GARDEN_SIM_LIM_SCENARIO_ID,
    OPQ_GARDEN_ABC_SCENARIO_ID,
}


class Lane:
    """One onboarding owner and one durable ownership repository across restarts."""

    def __init__(self, first_variant: str) -> None:
        self.onboarding, _ = service_lane(
            "accept_eligible_poc",
            opq_transport(OBSERVED_OPQ_POSITIONS),
            acra_marketplace_opq_scenario=first_variant,
        )
        self.repository = InMemoryOwnershipAnalysisRepository()

    def composed(self, variant: str) -> OwnershipAnalysisService:
        """A restarted composition with the operator selector at ``variant``."""

        return build_ownership_analysis_service(
            self.onboarding,
            lane(acra_marketplace_opq_scenario=variant),
            repository=self.repository,
        )

    def first(self, uen: str, variant: str) -> tuple[UUID, OwnershipAnalysisRecord]:
        case = self.onboarding.create_staged_case(uen)
        ownership = self.composed(variant)
        ownership.load(case_id=case.case_id)
        return case.case_id, ownership.analyze(case_id=case.case_id)

    def reanalysed(
        self, case_id: UUID, variant: str, monkeypatch: pytest.MonkeyPatch
    ) -> OwnershipAnalysisRecord:
        """Re-analyse an existing case after a selector switch (a document rebind)."""

        ownership = self.composed(variant)
        rebound = (OwnershipDocumentBinding(document_id=uuid4(), event_count=1),)
        monkeypatch.setattr(ownership, "_document_inputs", lambda case_id: ((), rebound))
        ownership.load(case_id=case_id)
        return ownership.analyze(case_id=case_id)


def scenario_of(record: OwnershipAnalysisRecord) -> str | None:
    return None if record.discovery is None else record.discovery.overlay_scenario_id


def aggregates(record: OwnershipAnalysisRecord) -> dict[str, Any]:
    return {
        item.party.display_name: item.aggregated_ownership_percent for item in record.candidates
    }


# --- Catalogue: by-root for new analyses, by-id for recorded ids ------------------------


def test_scenario_resolves_every_catalogued_id_while_by_root_holds_one_opq_variant() -> None:
    assert {item.scenario_id for item in catalogued_hybrid_overlay_scenarios()} == ALL_IDS
    for variant in VARIANTS:
        catalogue = HybridOwnershipOverlayCatalogue(hybrid_overlay_scenarios(variant))
        for scenario_id in ALL_IDS:
            resolved = catalogue.scenario(scenario_id)
            assert resolved is not None and resolved.scenario_id == scenario_id
            # D-112 O7: no catalogued scenario declares POC acceptance.
            assert resolved.poc_acceptance is None
        assert {item.scenario_id for item in catalogue.catalogued_scenarios} == ALL_IDS
        # New analyses: exactly Garden plus the operator-selected OPQ variant.
        assert tuple(catalogue.scenarios) == hybrid_overlay_scenarios(variant)
        assert catalogue.scenario("UNKNOWN_SCENARIO_V1") is None
        assert catalogue.scenario(None) is None
    default = HybridOwnershipOverlayCatalogue()
    assert {item.scenario_id for item in default.scenarios} == {
        GARDEN_DIRECT_OVERLAY_SCENARIO_ID,
        FIVE_LAYER_SCENARIO_ID,
    }


def test_a_recorded_id_never_falls_back_and_never_crosses_roots() -> None:
    onboarding = Lane(CHAIN).onboarding
    opq = onboarding.create_staged_case(FIVE_LAYER_ROOT_UEN)
    garden = onboarding.create_staged_case(GARDEN_UEN)
    now = datetime.now(UTC)
    catalogue = HybridOwnershipOverlayCatalogue(hybrid_overlay_scenarios(CHAIN))
    # A new case follows the selector.
    selected = catalogue.root_scenario(opq, now)
    assert selected is not None and selected.scenario_id == OPQ_GARDEN_SIM_LIM_SCENARIO_ID
    # A recorded catalogued id with the same root is kept, whatever the selector.
    for recorded in (
        FIVE_LAYER_SCENARIO_ID,
        OPQ_GARDEN_SIM_LIM_SCENARIO_ID,
        OPQ_GARDEN_ABC_SCENARIO_ID,
    ):
        kept = catalogue.root_scenario(opq, now, recorded_scenario_id=recorded)
        assert kept is not None and kept.scenario_id == recorded
    # Unknown or uncatalogued id: no overlay, never the selector's scenario.
    assert catalogue.root_scenario(opq, now, recorded_scenario_id="UNKNOWN_SCENARIO_V1") is None
    # Another root's id: no overlay, in both directions.
    assert (
        catalogue.root_scenario(opq, now, recorded_scenario_id=GARDEN_DIRECT_OVERLAY_SCENARIO_ID)
        is None
    )
    assert catalogue.root_scenario(garden, now, recorded_scenario_id=FIVE_LAYER_SCENARIO_ID) is None
    kept_garden = catalogue.root_scenario(
        garden, now, recorded_scenario_id=GARDEN_DIRECT_OVERLAY_SCENARIO_ID
    )
    assert kept_garden is not None and kept_garden.scenario_id == GARDEN_DIRECT_OVERLAY_SCENARIO_ID


def test_stale_or_missing_official_evidence_gives_no_overlay_even_with_a_recorded_id() -> None:
    onboarding = Lane(CHAIN).onboarding
    opq = onboarding.create_staged_case(FIVE_LAYER_ROOT_UEN)
    catalogue = HybridOwnershipOverlayCatalogue(hybrid_overlay_scenarios(CHAIN))
    stale = datetime.now(UTC) + timedelta(days=91)
    for recorded in (None, FIVE_LAYER_SCENARIO_ID, OPQ_GARDEN_SIM_LIM_SCENARIO_ID):
        assert catalogue.root_scenario(opq, stale, recorded_scenario_id=recorded) is None
    missing = opq.model_copy(update={"registry_acquisition": None})
    for recorded in (None, FIVE_LAYER_SCENARIO_ID, OPQ_GARDEN_SIM_LIM_SCENARIO_ID):
        assert (
            catalogue.root_scenario(missing, datetime.now(UTC), recorded_scenario_id=recorded)
            is None
        )


# --- Analysis: case-sticky through the existing repository and load path -----------------


def test_a_chain_case_stays_the_chain_after_the_selector_switches_to_five_layer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lane_ = Lane(CHAIN)
    case_id, first = lane_.first(FIVE_LAYER_ROOT_UEN, CHAIN)
    assert scenario_of(first) == OPQ_GARDEN_SIM_LIM_SCENARIO_ID
    again = lane_.reanalysed(case_id, FIVE_LAYER, monkeypatch)
    assert again.version > first.version
    assert scenario_of(again) == OPQ_GARDEN_SIM_LIM_SCENARIO_ID
    assert aggregates(again) == EXPECTED
    # A new case follows the current selector.
    _, fresh = lane_.first(FIVE_LAYER_ROOT_UEN, FIVE_LAYER)
    assert scenario_of(fresh) == FIVE_LAYER_SCENARIO_ID
    assert aggregates(fresh) == FIVE_LAYER_AGGREGATES


def test_a_five_layer_case_stays_five_layer_after_the_switch_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lane_ = Lane(FIVE_LAYER)
    case_id, first = lane_.first(FIVE_LAYER_ROOT_UEN, FIVE_LAYER)
    assert scenario_of(first) == FIVE_LAYER_SCENARIO_ID
    again = lane_.reanalysed(case_id, CHAIN, monkeypatch)
    assert scenario_of(again) == FIVE_LAYER_SCENARIO_ID
    assert aggregates(again) == FIVE_LAYER_AGGREGATES
    _, fresh = lane_.first(FIVE_LAYER_ROOT_UEN, CHAIN)
    assert scenario_of(fresh) == OPQ_GARDEN_SIM_LIM_SCENARIO_ID
    assert aggregates(fresh) == EXPECTED


def test_three_demonstrations_coexist_without_overwriting_each_other(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lane_ = Lane(CHAIN)
    chain_id, chain = lane_.first(FIVE_LAYER_ROOT_UEN, CHAIN)
    garden_id, garden = lane_.first(GARDEN_UEN, CHAIN)
    five_id, five = lane_.first(FIVE_LAYER_ROOT_UEN, FIVE_LAYER)
    # Re-analyse every case under the opposite selector: each keeps its recorded scenario.
    for case_id, before, variant in (
        (chain_id, chain, FIVE_LAYER),
        (garden_id, garden, FIVE_LAYER),
        (five_id, five, CHAIN),
    ):
        after = lane_.reanalysed(case_id, variant, monkeypatch)
        assert scenario_of(after) == scenario_of(before)
        assert aggregates(after) == aggregates(before)


def test_the_garden_direct_scenario_is_unchanged_in_both_selector_states(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = []
    for variant in (CHAIN, FIVE_LAYER):
        lane_ = Lane(variant)
        case_id, record = lane_.first(GARDEN_UEN, variant)
        assert scenario_of(record) == GARDEN_DIRECT_OVERLAY_SCENARIO_ID
        results.append(aggregates(record))
        other = FIVE_LAYER if variant == CHAIN else CHAIN
        assert aggregates(lane_.reanalysed(case_id, other, monkeypatch)) == results[-1]
    assert results[0] == results[1]


def labels(record: OwnershipAnalysisRecord) -> tuple[Any, ...]:
    """Every provenance label of the analysis, independent of generated ids and times."""

    return (
        sorted(
            (edge.provenance.provider, str(edge.provenance.environment))
            for edge in record.relationships
        ),
        sorted(
            (
                str(item.kind),
                item.entity_identifier or "",
                item.source_operation,
                item.provider,
                item.environment,
                item.authoritative,
            )
            for item in (*record.evidence, *record.supplemental_evidence)
        ),
    )


def test_provenance_labels_and_d112_o7_are_unchanged_on_a_sticky_reanalysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for first_variant, switched in ((CHAIN, FIVE_LAYER), (FIVE_LAYER, CHAIN)):
        lane_ = Lane(first_variant)
        case_id, first = lane_.first(FIVE_LAYER_ROOT_UEN, first_variant)
        again = lane_.reanalysed(case_id, switched, monkeypatch)
        assert labels(again) == labels(first)
        for record in (first, again):
            overlay_links = [
                edge
                for edge in record.relationships
                if edge.provenance.provider == OVERLAY_RELATIONSHIP_PROVIDER
            ]
            assert overlay_links
            for edge in overlay_links:
                # Synthetic links stay LOCAL and never carry the official source reference.
                assert edge.provenance.environment == OwnershipEnvironment.LOCAL
                assert edge.provenance.source_reference != OFFICIAL_MARKETPLACE_PROFILE_REFERENCE
            # The official root acquisition stays classified MOCK (no Live claim).
            assert record.provider_environment == OwnershipEnvironment.MOCK
            # D-112 O7: a hybrid analysis never gets POC acceptance and stays in review.
            assert record.poc_acceptance is None
            assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED


# --- The recorded id comes only from the existing persisted record -----------------------


def test_the_recorded_id_is_the_latest_overlay_id_of_the_persisted_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lane_ = Lane(CHAIN)
    case_id, first = lane_.first(FIVE_LAYER_ROOT_UEN, CHAIN)
    assert _recorded_overlay_scenario_id(None) is None
    assert _recorded_overlay_scenario_id(first) == OPQ_GARDEN_SIM_LIM_SCENARIO_ID
    assert first.discovery is not None
    # An intervening load without discovery (for example a terminal failure) keeps the
    # recorded variant through the bounded prior-analysis snapshots.
    later = lane_.reanalysed(case_id, FIVE_LAYER, monkeypatch)
    without = later.model_copy(update={"discovery": None})
    assert _recorded_overlay_scenario_id(without) == OPQ_GARDEN_SIM_LIM_SCENARIO_ID
    no_overlay = first.model_copy(
        update={"discovery": first.discovery.model_copy(update={"overlay_scenario_id": None})}
    )
    assert _recorded_overlay_scenario_id(no_overlay) is None
