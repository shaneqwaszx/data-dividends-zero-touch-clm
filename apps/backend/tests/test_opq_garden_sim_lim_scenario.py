"""D-086 explicitly selected OPQ -> GARDEN BUSINESS -> SIM LIM demonstration scenario.

OPQ keeps its official Marketplace Mock root identity, Garden its official
BUSINESS_PARTNERSHIP profile and SIM LIM its official shareholder-operation rows. Only
the relationships are declared: OPQ -> Garden is an owner-declared 100%
LOCAL_SYNTHETIC_RELATIONSHIP (no share units), and Garden's owner-supplied register is
unchanged. Offline only: allowlisted protocol transport, in-memory persistence, Mock
GoldTier. Nothing here is an observed ACRA response.
"""

from __future__ import annotations

from datetime import UTC, datetime
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
from test_slice_b_registry_demo import start

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
from app.services.ownership_analysis import (
    eligible_poc_acceptance,
    simulation_calculation_complete,
)

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
    assert {item.scenario_id for item in default.scenarios} == {
        GARDEN_DIRECT_OVERLAY_SCENARIO_ID,
        FIVE_LAYER_SCENARIO_ID,
    }
    selected = HybridOwnershipOverlayCatalogue(hybrid_overlay_scenarios("garden_sim_lim_chain"))
    # D-086a: a recorded id resolves any catalogued scenario (case-sticky) ...
    assert selected.scenario(OPQ_GARDEN_SIM_LIM_SCENARIO_ID) is not None
    assert selected.scenario(FIVE_LAYER_SCENARIO_ID) is not None
    # ... but a new analysis selects exactly one OPQ scenario at a time: never an
    # ambiguous automatic choice.
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
    # Garden's official OFFICERS roles are kept beside the graph on its discovery record
    # (role and status only), never silently dropped (D-086) and never holdings (D-087).
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


# --- Garden's intermediate Owner roles: descriptive context, never a privilege -------


def garden_roles(record: OwnershipAnalysisRecord) -> list[tuple[str, str]]:
    assert record.discovery is not None
    [garden] = [item for item in record.discovery.records if item.registration_number == GARDEN_UEN]
    return sorted((role.role, role.status) for role in garden.official_officer_roles)


def test_observed_garden_owner_roles_are_descriptive_context_for_the_chain() -> None:
    ownership, record = analysed()
    # Review state, issues and classifications are unchanged.
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert sorted(item.code for item in record.issues) == [
        "OWNERSHIP_DENOMINATOR_REQUIRED",
        "OWNERSHIP_METHOD_UNSUPPORTED",
        "SYNTHETIC_OWNERSHIP_EVIDENCE",
    ]
    assert all(item.classification == "REVIEW_REQUIRED" for item in record.candidates)
    # D-112 (O7): the scenario declares nothing, so its simulated chain is labelled
    # demonstration evidence only and is never accepted for readiness.
    assert record.poc_acceptance is None
    assert not ownership.poc_basis_accepted(record)
    # The retained evidence is unchanged: status, provenance and no holdings.
    assert garden_roles(record) == [
        ("OWNER", "CEASED"),
        ("OWNER", "CURRENT"),
        ("OWNER", "CURRENT"),
        ("OWNER", "CURRENT"),
    ]
    assert len(record.relationships) == 6
    assert {
        item.party.display_name: item.aggregated_ownership_percent for item in record.candidates
    } == EXPECTED
    # Presentation status is unchanged: OPQ is not a pure declared-link simulation.
    assert simulation_calculation_complete(record) is False


def test_the_chain_without_garden_officer_records_is_still_never_accepted() -> None:
    # Counterfactual: the identical chain with no Garden officer records. D-112 (O7): the
    # calculation is unchanged and, with no scenario privilege, it stays in review.
    ownership, record = analysed(
        transport=without_garden_officers(opq_transport(OBSERVED_OPQ_POSITIONS))
    )
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert record.poc_acceptance is None
    assert not ownership.poc_basis_accepted(record)
    assert {
        item.party.display_name: item.aggregated_ownership_percent for item in record.candidates
    } == EXPECTED


@pytest.mark.parametrize(
    "positions",
    [
        ("OWNER",),
        ("SHAREHOLDER",),
        ("PARTNER",),
        ("MEMBER",),
        ("OWNER", "SHAREHOLDER"),
        ("DIRECTOR",),
    ],
)
def test_no_intermediate_role_kind_grants_acceptance(positions: tuple[str, ...]) -> None:
    transport = opq_transport(OBSERVED_OPQ_POSITIONS)
    profile: Any = transport.profiles[GARDEN_UEN]
    officers = profile["entities"][0]["entityOfficersRecord"]["officerAppointmentDetails"]
    for index, officer in enumerate(officers):
        officer["position"] = positions[index % len(positions)]
    ownership, record = analysed(transport=transport)
    assert len(garden_roles(record)) == 4
    # D-112 (O7): no declaration names Garden's roles any more; none is accepted.
    assert record.poc_acceptance is None
    assert not ownership.poc_basis_accepted(record)
    # Whatever the outcome, no role becomes a holding and the arithmetic is unchanged.
    assert {
        item.party.display_name: item.aggregated_ownership_percent for item in record.candidates
    } == EXPECTED


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
    ownership, record = analysed(transport=opq_transport(positions))
    assert record.poc_acceptance is None, reason
    assert not ownership.poc_basis_accepted(record)


def test_no_composition_or_selector_grants_the_chain_authority() -> None:
    _, disabled = analysed("disabled")
    assert disabled.poc_acceptance is None
    ownership, record = analysed()
    # D-112 (O7): enabled or not, the scenario chain is never accepted.
    assert record.poc_acceptance is None
    assert not ownership.poc_basis_accepted(record)
    # The same persisted analysis under a five-layer composition. D-086a: its recorded
    # scenario still resolves (case-sticky), and resolution grants no authority (D-112 O7).
    _, reverted = service_lane("accept_eligible_poc", opq_transport(OBSERVED_OPQ_POSITIONS))
    resolved = reverted._poc_scenario(record)
    assert resolved is not None and resolved.scenario_id == OPQ_GARDEN_SIM_LIM_SCENARIO_ID
    assert resolved.poc_acceptance is None
    assert (
        eligible_poc_acceptance(
            record,
            scenario=resolved,
            accepted_at=datetime.now(UTC),
            ownership_version=record.version,
        )
        is None
    )
    assert not reverted.poc_basis_accepted(record)
    # The same analysis under a composition with the policy disabled.
    _, off = service_lane("disabled", opq_transport(OBSERVED_OPQ_POSITIONS), **CHAIN)
    assert not off.poc_basis_accepted(record)


def test_the_observed_chain_is_calculated_but_held_for_ownership_review() -> None:
    settings = lane(**CHAIN)
    bundle = build_persistence_bundle(settings)
    with runtime(settings, bundle, opq_transport(OBSERVED_OPQ_POSITIONS)) as client:
        case_id = start(client, FIVE_LAYER_FIELDS, "five-layer-marketplace-hybrid-client.pdf")[
            "case"
        ]["case_id"]
        ownership = ownership_of(client, case_id)
        summary = summary_of(client, case_id)
        # D-112 (O7): calculated and labelled, but no scenario privilege accepts it.
        assert (ownership["poc_basis_accepted"], ownership["state"]) == (False, "REVIEW_REQUIRED")
        assert ownership["poc_acceptance"] is None
        assert {
            item["party"]["display_name"]: Decimal(item["aggregated_ownership_percent"])
            for item in ownership["candidates"]
        } == EXPECTED
        assert all(item["classification"] == "REVIEW_REQUIRED" for item in ownership["candidates"])
        # Only the declared link is marked; the internal source reference is not projected.
        marked = {
            (edge["parent_party_id"], edge["child_party_id"])
            for edge in ownership["relationships"]
            if edge["provenance"]["owner_declared_percentage"]
        }
        assert marked == {(ownership["root_party_id"], GARDEN_UEN)}
        assert all(
            "source_reference" not in edge["provenance"] for edge in ownership["relationships"]
        )
        names = {party["party_id"]: party["display_name"] for party in ownership["parties"]}
        assert {
            names[item["party_id"]]: Decimal(item["effective_ownership_percent"])
            for item in ownership["entity_effective_interests"]
        } == {"GARDEN BUSINESS": Decimal("100"), "SIM LIM PTE. LTD.": Decimal("62.5")}
        # Ownership holds readiness; no target confirmation is offered and nothing is sent.
        readiness = summary["clm"]["readiness"]
        assert "OWNERSHIP_REVIEW_REQUIRED" in readiness["blockers"]
        assert readiness["ownership"]["status"] != "READY"
        assert "TARGET_CONFIRMATION_REQUIRED" not in [
            item["exception_type"] for item in summary["active_exceptions"]
        ]
        assert summary["case"].get("goldtier_result") is None
        assert summary["clm"]["submission"] is None
        assert bundle.target_executions.list_for_case(UUID(case_id)) == ()


# --- Live persistence and domain guards for hybrid records ----------------------------


def test_hybrid_records_round_trip_and_older_readers_still_reject_their_fields() -> None:
    """Live persistence and domain guards kept from the retired D-087 round-trip test."""
    from test_official_shareholder_evidence import snapshot_of
    from test_poc_ownership_acceptance import accepted_record

    from app.domain.ownership import OwnershipDiscoveryRecord, OwnershipPocAcceptance
    from app.persistence.models import DurableCaseSnapshot, reject_scenario_poc_legacy_fields

    onboarding, ownership = service_lane(
        "accept_eligible_poc", opq_transport(OBSERVED_OPQ_POSITIONS), **CHAIN
    )
    case = onboarding.create_staged_case(FIVE_LAYER_ROOT_UEN)
    ownership.load(case_id=case.case_id)
    record = ownership.analyze(case_id=case.case_id)
    assert record.poc_acceptance is None
    encoded = snapshot_of(onboarding, record).model_dump(mode="json")
    assert encoded["schema_version"] == 20
    # Backend-only: a dump omits the ledger, and its absence fails closed.
    assert DurableCaseSnapshot.model_validate(encoded).ownership == record.model_copy(
        update={"poc_interest_ledger": None}
    )
    # Older schemas still reject the D-086 officer role observations hybrid records carry.
    with pytest.raises(ValueError, match="D-086 officer role observations"):
        reject_scenario_poc_legacy_fields(encoded)
    legacy_counts = {
        "ownership": {
            "poc_acceptance": {
                "policy": "D082_HYBRID_POC_EQUAL_UNITS_V1",
                "descriptive_intermediate_current_role_count": 1,
            }
        }
    }
    with pytest.raises(ValueError, match="D-085 POC acceptance"):
        reject_scenario_poc_legacy_fields(legacy_counts)
    reject_scenario_poc_legacy_fields(
        {"ownership": {"discovery": {"records": [{"official_officer_roles": []}]}}}
    )
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
    # A stored D-082 acceptance can never carry intermediate role counts.
    _, _, generic = accepted_record()
    assert generic.poc_acceptance is not None
    legacy = {
        **generic.poc_acceptance.model_dump(),
        "policy": "D082_HYBRID_POC_EQUAL_UNITS_V1",
        "overlay_scenario_id": "GARDEN_DIRECT_OVERLAY_V1",
        "accepted_assumptions": (),
        "accepted_issue_codes": (
            "OWNERSHIP_DENOMINATOR_REQUIRED",
            "SYNTHETIC_OWNERSHIP_EVIDENCE",
            "UBO_REVIEW_REQUIRED",
        ),
    }
    OwnershipPocAcceptance.model_validate(legacy)
    with pytest.raises(ValidationError):
        OwnershipPocAcceptance.model_validate(
            {**legacy, "descriptive_intermediate_current_role_count": 1}
        )


# D-112 (owner O7, 2026-11-01): these D-087/D-089 expectations are obsolete, not
# weakened. They asserted acceptance through the scenario's own declaration (declared
# intermediate roles, their validators and runtime guards, revocation of a recorded
# scenario acceptance, and its schema fields). No scenario declares acceptance now, so
# the chain is never accepted; see the tests above for what remains asserted. The
# round-trip test's live persistence guards moved to
# test_hybrid_records_round_trip_and_older_readers_still_reject_their_fields.
RETIRED_D087_EXPECTATIONS = (
    "test_intermediate_roles_need_the_trusted_declaration_naming_their_issuer",
    "test_malformed_or_improperly_bound_intermediate_roles_still_block",
    "test_a_changed_intermediate_role_revokes_the_recorded_acceptance",
    "test_withdrawing_the_policy_reinstates_the_ownership_hold",
    # Acceptance part retired; its live guards are kept in the round-trip test above.
    "test_the_acceptance_round_trips_in_schema_fifteen_and_older_readers_reject_it",
    "test_each_intermediate_role_runtime_guard_stands_alone",
    # Kept as the D-082 intermediate-count check in the round-trip test above.
    "test_a_legacy_d082_acceptance_never_carries_intermediate_counts",
    "_declared",
    "_with_garden",
    "_role_copy",
    "_unvalidated",
)
