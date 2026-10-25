"""D-086 explicitly selected OPQ -> GARDEN BUSINESS -> SIM LIM demonstration scenario.

OPQ keeps its official Marketplace Mock root identity, Garden its official
BUSINESS_PARTNERSHIP profile and SIM LIM its official shareholder-operation rows. Only
the relationships are declared: OPQ -> Garden is an owner-declared 100%
LOCAL_SYNTHETIC_RELATIONSHIP (no share units), and Garden's owner-supplied register is
unchanged. Offline only: allowlisted protocol transport, in-memory persistence, Mock
GoldTier. Nothing here is an observed ACRA response.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError
from scripts.five_layer_hybrid_fixture import FIVE_LAYER_FIELDS
from test_official_shareholder_evidence import SIM
from test_poc_ownership_acceptance import (
    garden_transport,
    lane,
    ownership_of,
    runtime,
    service_lane,
    summary_of,
)
from test_simulation_calculation_status import FIVE_LAYER_AGGREGATES
from test_slice_b_registry_demo import confirm, start

from app.connectors.hybrid_ownership_overlay import (
    FIVE_LAYER_ROOT_UEN,
    FIVE_LAYER_SCENARIO_ID,
    GARDEN_DIRECT_OVERLAY_SCENARIO_ID,
    OPQ_GARDEN_SIM_LIM_SCENARIO,
    OPQ_GARDEN_SIM_LIM_SCENARIO_ID,
    OVERLAY_RELATIONSHIP_PROVIDER,
    OWNER_DECLARED_PERCENT_SUFFIX,
    POC_EQUAL_UNITS_PROVIDER,
    HybridOwnershipOverlayCatalogue,
    OverlayHolder,
    OverlayIssuer,
    hybrid_overlay_scenarios,
)
from app.domain.ownership import OwnershipAnalysisRecord, OwnershipAnalysisState
from app.persistence.composition import build_persistence_bundle
from app.services.ownership_analysis import simulation_calculation_complete

GARDEN_UEN = "11111999A"
CHAIN = {"acra_marketplace_opq_scenario": "garden_sim_lim_chain"}
EXPECTED = {
    "ABCD123": Decimal("51.13636375"),
    "LIM CHOON HUAT": Decimal("37.5"),
    "TAN WEI LING": Decimal("5.681818125"),
    "EFGH2345": Decimal("5.681818125"),
}


def opq_transport(positions: tuple[tuple[str, bool], ...] = ()) -> Any:
    """Garden + SIM LIM protocol shapes, with OPQ officers mirroring a position list."""

    transport = garden_transport()
    if positions:
        profile: Any = transport.profiles[FIVE_LAYER_ROOT_UEN]
        profile["entities"][0]["entityOfficersRecord"] = {
            "officerAppointmentDetails": [
                {
                    "officerId": f"SYNTHETIC-OPQ-OFFICER-{index}",
                    "officerName": f"Synthetic OPQ Officer {index}",
                    "position": position,
                    "appointedDate": "2015-01-01",
                    **({"withdrawalDate": "2020-01-01"} if ceased else {}),
                }
                for index, (position, ceased) in enumerate(positions, start=1)
            ]
        }
    return transport


# The owner-authorized single read (2026-10-25) observed 2 current and 1 ceased DIRECTOR
# plus 1 current SECRETARY; no ownership-like role. Synthetic identities only.
OBSERVED_OPQ_POSITIONS = (
    ("DIRECTOR", False),
    ("DIRECTOR", False),
    ("DIRECTOR", True),
    ("SECRETARY", False),
)


def analysed(acceptance: str = "accept_eligible_poc", **kwargs: Any) -> tuple[Any, Any]:
    transport = kwargs.pop("transport", None) or opq_transport(OBSERVED_OPQ_POSITIONS)
    onboarding, ownership = service_lane(acceptance, transport, **{**CHAIN, **kwargs})
    case = onboarding.create_staged_case(FIVE_LAYER_ROOT_UEN)
    ownership.load(case_id=case.case_id)
    return ownership, ownership.analyze(case_id=case.case_id)


def names(record: OwnershipAnalysisRecord) -> dict[str, str]:
    return {party.party_id: party.display_name for party in record.parties}


# --- Operator selection: explicit, default-preserving, hybrid lane only -------------------


def test_the_five_layer_simulation_stays_the_default_and_the_variant_is_explicit() -> None:
    assert lane().acra_marketplace_opq_scenario == "five_layer_simulation"
    default = HybridOwnershipOverlayCatalogue()
    assert default.scenario(FIVE_LAYER_SCENARIO_ID) is not None
    assert default.scenario(OPQ_GARDEN_SIM_LIM_SCENARIO_ID) is None
    selected = HybridOwnershipOverlayCatalogue(hybrid_overlay_scenarios("garden_sim_lim_chain"))
    assert selected.scenario(OPQ_GARDEN_SIM_LIM_SCENARIO_ID) is not None
    # Exactly one OPQ scenario at a time: never an ambiguous automatic choice.
    assert selected.scenario(FIVE_LAYER_SCENARIO_ID) is None
    assert {item.scenario_id for item in selected.scenarios} == {
        GARDEN_DIRECT_OVERLAY_SCENARIO_ID,
        OPQ_GARDEN_SIM_LIM_SCENARIO_ID,
    }
    for update in (
        {"acra_marketplace_ownership_overlay": "garden_legacy_supplement"},
        {
            "acra_connector_mode": "mock",
            "acra_marketplace_ownership_overlay": "garden_legacy_supplement",
        },
    ):
        with pytest.raises(ValidationError, match="OPQ scenario variant requires"):
            lane("disabled", **{**CHAIN, **update})
    with pytest.raises(ValidationError):
        lane("disabled", acra_marketplace_opq_scenario="client_choice")


def test_the_default_selector_keeps_the_historical_five_layer_result() -> None:
    _, record = analysed(acra_marketplace_opq_scenario="five_layer_simulation")
    assert record.discovery is not None
    assert record.discovery.overlay_scenario_id == FIVE_LAYER_SCENARIO_ID
    assert {
        item.party.display_name: item.aggregated_ownership_percent for item in record.candidates
    } == FIVE_LAYER_AGGREGATES
    assert record.poc_acceptance is None


# --- The declared register: a percentage, never invented share units -------------------


def test_the_owner_declared_register_is_a_complete_percentage_without_units() -> None:
    [opq, garden] = OPQ_GARDEN_SIM_LIM_SCENARIO.issuers
    assert opq.denominator_basis == "OWNER_DECLARED_COMPLETE_PERCENTAGES"
    assert opq.declared_active_units is None
    [holder] = opq.holders
    assert (holder.holder_id, holder.declared_percent, holder.share_units) == (
        GARDEN_UEN,
        Decimal("100"),
        None,
    )
    # Garden's owner-supplied register is reused unchanged from the Garden scenario.
    assert (
        garden
        == HybridOwnershipOverlayCatalogue().scenario(GARDEN_DIRECT_OVERLAY_SCENARIO_ID).issuers[0]
    )  # type: ignore[union-attr]
    corporate = {"category": "Corporate", "registration_number": GARDEN_UEN}
    for invalid in (
        # An incomplete register would hide an unknown remainder.
        {
            "holders": (
                OverlayHolder(
                    holder_id=GARDEN_UEN,
                    holder_name="G",
                    declared_percent=Decimal("60"),
                    **corporate,
                ),
            )
        },
        # Units and a declared percentage never mix.
        {
            "holders": (
                OverlayHolder(
                    holder_id=GARDEN_UEN, holder_name="G", share_units=Decimal("1"), **corporate
                ),
            )
        },
        {"declared_active_units": Decimal("1")},
        {
            "holders": (
                OverlayHolder(
                    holder_id=GARDEN_UEN,
                    holder_name="G",
                    declared_percent=Decimal("100"),
                    status="Withdrawn",
                    **corporate,
                ),
            )
        },
    ):
        with pytest.raises(ValidationError):
            OverlayIssuer.model_validate({**opq.model_dump(), **invalid})
    with pytest.raises(ValidationError, match="exactly one of units or a percentage"):
        OverlayHolder(
            holder_id=GARDEN_UEN,
            holder_name="G",
            share_units=Decimal("1"),
            declared_percent=Decimal("1"),
            **corporate,
        )
    with pytest.raises(ValidationError, match="exactly one of units or a percentage"):
        OverlayHolder(holder_id=GARDEN_UEN, holder_name="G", **corporate)


# --- The calculated chain, its provenance and identities --------------------------------


def test_the_chain_reuses_the_engine_with_truthful_identities_and_provenance() -> None:
    _, record = analysed()
    by_id = names(record)
    edges = {
        (by_id[edge.parent_party_id], by_id[edge.child_party_id]): edge
        for edge in record.relationships
    }
    declared = edges[("OPQ PTE. LTD.", "GARDEN BUSINESS")]
    assert declared.ownership_percent == Decimal("100")
    assert declared.provenance.provider == OVERLAY_RELATIONSHIP_PROVIDER
    assert declared.provenance.environment == "LOCAL"
    assert declared.provenance.source_reference.endswith(OWNER_DECLARED_PERCENT_SUFFIX)
    for child, percent in (("SIM LIM PTE. LTD.", "62.5"), ("LIM CHOON HUAT", "37.5")):
        edge = edges[("GARDEN BUSINESS", child)]
        assert edge.ownership_percent == Decimal(percent)
        assert edge.provenance.provider == OVERLAY_RELATIONSHIP_PROVIDER
        assert not edge.provenance.source_reference.endswith(OWNER_DECLARED_PERCENT_SUFFIX)
    for child, percent in (
        ("ABCD123", "81.818182"),
        ("TAN WEI LING", "9.090909"),
        ("EFGH2345", "9.090909"),
    ):
        edge = edges[("SIM LIM PTE. LTD.", child)]
        assert (edge.ownership_percent, edge.provenance.provider) == (
            Decimal(percent),
            POC_EQUAL_UNITS_PROVIDER,
        )
    assert len(record.relationships) == 6
    # No share-unit evidence is invented for the declared 100%.
    assert not any(
        item.kind == "SHARE_UNITS" and item.entity_identifier == FIVE_LAYER_ROOT_UEN
        for item in (*record.evidence, *record.supplemental_evidence)
    )
    # Effective interests are exactly the Garden case's, through the declared 100%.
    assert {
        item.party.display_name: item.aggregated_ownership_percent for item in record.candidates
    } == EXPECTED
    abcd = next(item for item in record.candidates if item.party.display_name == "ABCD123")
    assert [path.calculation for path in abcd.paths] == ["100% x 62.5% x 81.818182% = 51.13636375%"]
    # Identities: OPQ official root, Garden official partnership, SIM LIM operation-scoped.
    assert record.identity_registration_number == FIVE_LAYER_ROOT_UEN
    assert (record.provider_name, record.provider_environment) == (
        "ACRA_REGISTRY_ACQUISITION",
        "MOCK",
    )
    assert record.legal_form == "OTHER"
    audit = record.discovery
    assert audit is not None and audit.overlay_scenario_id == OPQ_GARDEN_SIM_LIM_SCENARIO_ID
    issuers = {item.registration_number: item for item in audit.records}
    assert set(issuers) == {GARDEN_UEN, SIM}
    garden = issuers[GARDEN_UEN]
    assert (garden.outcome, garden.identity_basis, garden.official_legal_form) == (
        "LOCAL_SYNTHETIC_OVERLAY",
        "OFFICIAL_MOCK_ENTITY_PROFILE",
        "BUSINESS_PARTNERSHIP",
    )
    sim = issuers[SIM]
    assert sim.reason_code == "OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS"
    assert sim.identity_basis is None
    assert [
        (
            row.source_category,
            row.source_status,
            row.share_allotted,
            row.share_type,
            row.current_interest,
        )
        for row in sim.official_shareholders
    ] == [
        ("Corporate", "Withdrawn", Decimal("10000"), "Ordinary", False),
        ("Individual", "Active", Decimal("900"), "Ordinary", True),
        ("Individual", "Active", Decimal("100"), "Preference", True),
        ("Individual", "Active", Decimal("100"), "Others", True),
    ]
    assert audit.topology_complete is True and not audit.unresolved_person_party_ids


def without_garden_officers(transport: Any) -> Any:
    """Test-only counterfactual: Garden's profile without officer records (not observed)."""

    profile: Any = transport.profiles[GARDEN_UEN]
    profile["entities"][0].pop("entityOfficersRecord", None)
    return transport


def roles_by_issuer(record: OwnershipAnalysisRecord) -> dict[str, list[tuple[str, str]]]:
    """Root roles from the analysis evidence; intermediate roles from discovery records."""

    found: dict[str, list[tuple[str, str]]] = {}
    for item in record.evidence:
        assert item.kind == "ROLE"
        found.setdefault(item.entity_identifier or "", []).append(
            (item.raw_value, item.source_status or "CURRENT")
        )
    assert record.discovery is not None
    for issuer in record.discovery.records:
        for role in issuer.official_officer_roles:
            found.setdefault(issuer.registration_number or "", []).append((role.role, role.status))
    return {key: sorted(value) for key, value in found.items()}


def test_officer_roles_of_root_and_intermediate_stay_descriptive_and_never_holdings() -> None:
    _, record = analysed()
    # D-086 fail closed: Garden's official OFFICERS roles are kept beside the graph on its
    # discovery record (role and status only) instead of being silently dropped.
    assert roles_by_issuer(record) == {
        FIVE_LAYER_ROOT_UEN: [
            ("DIRECTOR", "CEASED"),
            ("DIRECTOR", "CURRENT"),
            ("DIRECTOR", "CURRENT"),
            ("SECRETARY", "CURRENT"),
        ],
        GARDEN_UEN: [
            ("OWNER", "CEASED"),
            ("OWNER", "CURRENT"),
            ("OWNER", "CURRENT"),
            ("OWNER", "CURRENT"),
        ],
    }
    assert record.discovery is not None
    garden = next(
        item for item in record.discovery.records if item.registration_number == GARDEN_UEN
    )
    assert {
        (role.source_operation, role.provider, role.environment)
        for role in garden.official_officer_roles
    } == {("OFFICERS", "ACRA_REGISTRY_ACQUISITION", "MOCK")}
    # Roles carry no identity and never become parties, edges or analysis evidence.
    assert set(type(garden.official_officer_roles[0]).model_fields) == {
        "role",
        "status",
        "source_operation",
        "provider",
        "environment",
        "retrieved_at",
    }
    assert all(item.entity_identifier == FIVE_LAYER_ROOT_UEN for item in record.evidence)
    role_parties = {item.party_id for item in record.evidence}
    assert not role_parties & {party.party_id for party in record.parties}
    # The calculation itself is unchanged by the retained roles.
    assert {
        item.party.display_name: item.aggregated_ownership_percent for item in record.candidates
    } == EXPECTED


# --- D-085 eligibility on the declared scenario (owner decision: fail closed) ------------


def test_garden_intermediate_owner_roles_keep_the_chain_in_review_without_readiness() -> None:
    ownership, record = analysed()
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert sorted(item.code for item in record.issues) == [
        "OWNERSHIP_DENOMINATOR_REQUIRED",
        "OWNERSHIP_METHOD_UNSUPPORTED",
        "SYNTHETIC_OWNERSHIP_EVIDENCE",
    ]
    assert all(item.classification == "REVIEW_REQUIRED" for item in record.candidates)
    # DESCRIPTIVE_OFFICER_ROLES is neither declared nor extended to intermediate issuers,
    # so the unresolved Garden roles block POC acceptance (open owner question, D-086).
    assert record.poc_acceptance is None
    assert not ownership.poc_basis_accepted(record)
    assert simulation_calculation_complete(record) is False


def test_the_same_chain_qualifies_only_when_no_intermediate_role_is_unresolved() -> None:
    # Counterfactual mechanism check: with no Garden officer records, the identical chain
    # satisfies the declared assumptions. This proves the block above is the role evidence.
    ownership, record = analysed(
        transport=without_garden_officers(opq_transport(OBSERVED_OPQ_POSITIONS))
    )
    acceptance = record.poc_acceptance
    assert acceptance is not None
    assert acceptance.overlay_scenario_id == OPQ_GARDEN_SIM_LIM_SCENARIO_ID
    assert list(acceptance.accepted_assumptions) == [
        "EQUAL_UNIT_DENOMINATOR",
        "SIMULATED_RELATIONSHIPS",
        "UNCLASSIFIED_LEGAL_FORM",
    ]
    assert (
        acceptance.descriptive_current_role_count,
        acceptance.descriptive_ceased_role_count,
    ) == (0, 0)
    assert ownership.poc_basis_accepted(record)
    assert {
        item.party.display_name: item.aggregated_ownership_percent for item in record.candidates
    } == EXPECTED


@pytest.mark.parametrize(
    ("position", "blocked"), [("SHAREHOLDER", True), ("PARTNER", True), ("DIRECTOR", False)]
)
def test_any_intermediate_officer_role_is_evaluated_never_silently_dropped(
    position: str, blocked: bool
) -> None:
    transport = opq_transport(OBSERVED_OPQ_POSITIONS)
    profile: Any = transport.profiles[GARDEN_UEN]
    for officer in profile["entities"][0]["entityOfficersRecord"]["officerAppointmentDetails"]:
        officer["position"] = position
    ownership, record = analysed(transport=transport)
    assert [role for role, _ in roles_by_issuer(record)[GARDEN_UEN]] == [position] * 4
    # Ownership-like intermediate roles are outside every declared assumption: blocked.
    # A non-ownership role (DIRECTOR) is retained as descriptive context only.
    assert (record.poc_acceptance is None) is blocked
    assert ownership.poc_basis_accepted(record) is not blocked


@pytest.mark.parametrize(
    ("positions", "reason"),
    [
        ((("OWNER", False),), "an ownership-like root officer role contradicts the declaration"),
        ((("PARTNER", False), ("DIRECTOR", False)), "an ownership-like root officer role"),
    ],
)
def test_contradicting_root_evidence_is_never_bypassed(
    positions: tuple[tuple[str, bool], ...], reason: str
) -> None:
    ownership, record = analysed(transport=without_garden_officers(opq_transport(positions)))
    assert record.poc_acceptance is None, reason
    assert not ownership.poc_basis_accepted(record)


def test_default_off_and_switching_the_selector_back_withdraw_authority() -> None:
    _, disabled = analysed(
        "disabled", transport=without_garden_officers(opq_transport(OBSERVED_OPQ_POSITIONS))
    )
    assert disabled.poc_acceptance is None
    ownership, record = analysed(
        transport=without_garden_officers(opq_transport(OBSERVED_OPQ_POSITIONS))
    )
    assert ownership.poc_basis_accepted(record)
    # The same persisted analysis under a five-layer composition: its scenario is gone.
    onboarding, reverted = service_lane(
        "accept_eligible_poc", opq_transport(OBSERVED_OPQ_POSITIONS)
    )
    assert reverted._poc_scenario(record) is None
    assert not reverted.poc_basis_accepted(record)


def test_the_observed_chain_stays_blocked_at_ownership_and_sends_nothing() -> None:
    settings = lane(**CHAIN)
    bundle = build_persistence_bundle(settings)
    with runtime(settings, bundle, opq_transport(OBSERVED_OPQ_POSITIONS)) as client:
        case_id = start(client, FIVE_LAYER_FIELDS, "five-layer-marketplace-hybrid-client.pdf")[
            "case"
        ]["case_id"]
        ownership = ownership_of(client, case_id)
        summary = summary_of(client, case_id)
    assert (ownership["poc_basis_accepted"], ownership["simulation_calculated"]) == (
        False,
        False,
    )
    assert ownership["state"] == "REVIEW_REQUIRED"
    assert {
        item["party"]["display_name"]: Decimal(item["aggregated_ownership_percent"])
        for item in ownership["candidates"]
    } == EXPECTED
    # Only the declared link is marked; the internal source reference is not projected.
    marked = {
        (edge["parent_party_id"], edge["child_party_id"])
        for edge in ownership["relationships"]
        if edge["provenance"]["owner_declared_percentage"]
    }
    assert marked == {(ownership["root_party_id"], GARDEN_UEN)}
    assert all("source_reference" not in edge["provenance"] for edge in ownership["relationships"])
    # D-086 presentation only: entity interests from the engine's own path products.
    names = {party["party_id"]: party["display_name"] for party in ownership["parties"]}
    assert {
        names[item["party_id"]]: Decimal(item["effective_ownership_percent"])
        for item in ownership["entity_effective_interests"]
    } == {"GARDEN BUSINESS": Decimal("100"), "SIM LIM PTE. LTD.": Decimal("62.5")}
    assert "OWNERSHIP_REVIEW_REQUIRED" in summary["clm"]["readiness"]["blockers"]
    assert (summary["status"], summary["current_stage"]) == ("WAITING_FOR_REVIEW", "OWNERSHIP")
    assert "TARGET_CONFIRMATION_REQUIRED" not in [
        item["exception_type"] for item in summary["active_exceptions"]
    ]
    assert summary["case"].get("goldtier_result") is None
    assert summary["clm"]["submission"] is None
    assert bundle.target_executions.list_for_case(UUID(case_id)) == ()


def test_an_eligible_chain_still_needs_explicit_confirmation_before_any_mock_send() -> None:
    # Counterfactual eligible shape (no Garden officer records) exercises the target guard.
    settings = lane(**CHAIN)
    bundle = build_persistence_bundle(settings)
    transport = without_garden_officers(opq_transport(OBSERVED_OPQ_POSITIONS))
    with runtime(settings, bundle, transport) as client:
        case_id = start(client, FIVE_LAYER_FIELDS, "five-layer-marketplace-hybrid-client.pdf")[
            "case"
        ]["case_id"]
        ownership = ownership_of(client, case_id)
        summary = summary_of(client, case_id)
        assert ownership["poc_basis_accepted"] is True
        assert summary["clm"]["readiness"]["blockers"] == []
        assert [item["exception_type"] for item in summary["active_exceptions"]] == [
            "TARGET_CONFIRMATION_REQUIRED"
        ]
        assert summary["case"].get("goldtier_result") is None
        assert summary["clm"]["submission"] is None
        assert bundle.target_executions.list_for_case(UUID(case_id)) == ()
        # Only an explicit confirmation sends to Mock GoldTier, with no provisional UBO id.
        sent = confirm(client, summary)
    assert sent["status"] == "COMPLETED"
    snapshot = bundle.clm.get_for_case(UUID(case_id)).submission_snapshot
    assert snapshot is not None
    assert snapshot.provisional_ubo.candidate_count == 0
    assert snapshot.ownership_reference.status == "REVIEW_REQUIRED"


def test_retained_roles_round_trip_in_schema_fifteen_and_older_readers_reject_them() -> None:
    from test_official_shareholder_evidence import snapshot_of

    from app.domain.ownership import OwnershipDiscoveryRecord
    from app.persistence.models import DurableCaseSnapshot, reject_scenario_poc_legacy_fields

    onboarding, ownership = service_lane(
        "accept_eligible_poc", opq_transport(OBSERVED_OPQ_POSITIONS), **CHAIN
    )
    case = onboarding.create_staged_case(FIVE_LAYER_ROOT_UEN)
    ownership.load(case_id=case.case_id)
    record = ownership.analyze(case_id=case.case_id)
    encoded = snapshot_of(onboarding, record).model_dump(mode="json")
    assert encoded["schema_version"] == 15
    assert DurableCaseSnapshot.model_validate(encoded).ownership == record
    with pytest.raises(ValueError, match="D-086 officer role observations"):
        reject_scenario_poc_legacy_fields(encoded)
    empty = {"ownership": {"discovery": {"records": [{"official_officer_roles": []}]}}}
    reject_scenario_poc_legacy_fields(empty)
    # Role observations require the issuer's official entity profile.
    garden = next(
        item.model_dump()
        for item in record.discovery.records  # type: ignore[union-attr]
        if item.registration_number == GARDEN_UEN
    )
    with pytest.raises(ValidationError, match="require an official entity profile"):
        OwnershipDiscoveryRecord.model_validate(
            {**garden, "identity_basis": "LOCAL_SYNTHETIC_IDENTITY"}
        )
