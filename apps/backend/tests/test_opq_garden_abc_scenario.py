"""D-088/D-089 OPQ multi-holder variant: GARDEN BUSINESS 50% and ABC COMPANY 50%.

OPQ keeps its official Marketplace Mock root. Its register is owner-declared (the only two
new synthetic declarations). Garden keeps its unchanged owner-supplied register and SIM
LIM's official rows (D-081). ABC COMPANY's own holder comes from its official
businessProfile: 1000 ORDINARY shares over 1000 issued ORDINARY shares under the D-088
issued-capital POC interpretation, with the status-free row assumed current only on that
exact match. Offline only: allowlisted protocol transport, Mock GoldTier.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError
from scripts.five_layer_hybrid_fixture import (
    ABC_SYNTHETIC_HOLDER_NAME,
    FIVE_LAYER_FIELDS,
    abc_business_profile,
)
from test_opq_garden_sim_lim_scenario import OBSERVED_OPQ_POSITIONS, garden_roles, opq_transport
from test_poc_ownership_acceptance import lane, ownership_of, runtime, service_lane, summary_of
from test_slice_b_registry_demo import start

from app.connectors.hybrid_ownership_overlay import (
    ABC_COMPANY_UEN,
    FIVE_LAYER_ROOT_UEN,
    OPQ_GARDEN_ABC_SCENARIO,
    OPQ_GARDEN_ABC_SCENARIO_ID,
    OVERLAY_RELATIONSHIP_PROVIDER,
    OWNER_DECLARED_PERCENT_SUFFIX,
    POC_EQUAL_UNITS_PROVIDER,
    POC_ISSUED_CAPITAL_PROVIDER,
    HybridOverlayScenario,
    hybrid_overlay_scenarios,
    issued_capital_matches,
)
from app.domain.ownership import (
    OwnershipAnalysisRecord,
    OwnershipAnalysisState,
    OwnershipDiscoveryOutcome,
)
from app.persistence.composition import build_persistence_bundle

GARDEN_UEN = "11111999A"
MULTI = {"acra_marketplace_opq_scenario": "garden_abc_multi_holder"}
EXPECTED = {
    ABC_SYNTHETIC_HOLDER_NAME: Decimal("50"),
    "ABCD123": Decimal("25.568181875"),
    "LIM CHOON HUAT": Decimal("18.75"),
    "TAN WEI LING": Decimal("2.8409090625"),
    "EFGH2345": Decimal("2.8409090625"),
}


def transport(profile: dict[str, object] | None = None) -> Any:
    value = opq_transport(OBSERVED_OPQ_POSITIONS)
    if profile is not None:
        value.business_profiles[ABC_COMPANY_UEN] = profile
    return value


def analysed(
    acceptance: str = "accept_eligible_poc", profile: dict[str, object] | None = None, **kwargs: Any
) -> tuple[Any, OwnershipAnalysisRecord, Any]:
    channel = kwargs.pop("transport", None) or transport(profile)
    onboarding, ownership = service_lane(acceptance, channel, **{**MULTI, **kwargs})
    case = onboarding.create_staged_case(FIVE_LAYER_ROOT_UEN)
    ownership.load(case_id=case.case_id)
    return ownership, ownership.analyze(case_id=case.case_id), channel


def by_name(record: OwnershipAnalysisRecord) -> dict[str, Decimal]:
    return {
        item.party.display_name: item.aggregated_ownership_percent for item in record.candidates
    }


def abc_record(record: OwnershipAnalysisRecord) -> Any:
    assert record.discovery is not None
    [item] = [
        item for item in record.discovery.records if item.registration_number == ABC_COMPANY_UEN
    ]
    return item


def mutated(**changes: Any) -> dict[str, object]:
    profile: Any = abc_business_profile()
    entity = profile["entities"][0]
    for key, value in changes.items():
        if key.startswith("holder_"):
            entity["shareholder"][0][key.removeprefix("holder_")] = value
        elif key.startswith("issued_"):
            entity["issuedShareCapital"][0][key.removeprefix("issued_")] = value
        elif key.startswith("paid_"):
            entity["paidUpCapital"][0][key.removeprefix("paid_")] = value
        else:
            entity[key] = value
    return profile


# --- Selection: a separate operator-selected variant; the defaults are unchanged ---------


def test_the_variant_is_explicit_and_keeps_the_other_scenarios_unchanged() -> None:
    selected = hybrid_overlay_scenarios("garden_abc_multi_holder")
    assert {item.scenario_id for item in selected} == {
        "GARDEN_DIRECT_OVERLAY_V1",
        OPQ_GARDEN_ABC_SCENARIO_ID,
    }
    assert lane().acra_marketplace_opq_scenario == "five_layer_simulation"
    assert {item.scenario_id for item in hybrid_overlay_scenarios("garden_sim_lim_chain")} == {
        "GARDEN_DIRECT_OVERLAY_V1",
        "OPQ_GARDEN_SIM_LIM_V1",
    }
    for variant in ("five_layer_simulation", "garden_sim_lim_chain"):
        assert all(not item.business_profile_issuers for item in hybrid_overlay_scenarios(variant))
    [opq, garden] = OPQ_GARDEN_ABC_SCENARIO.issuers
    # The only two new synthetic declarations: OPQ's 50 / 50 owner-declared register.
    assert [(item.holder_id, item.declared_percent, item.share_units) for item in opq.holders] == [
        (GARDEN_UEN, Decimal("50"), None),
        (ABC_COMPANY_UEN, Decimal("50"), None),
    ]
    assert garden == hybrid_overlay_scenarios()[0].issuers[0]
    assert OPQ_GARDEN_ABC_SCENARIO.business_profile_issuers == {ABC_COMPANY_UEN}
    with pytest.raises(ValidationError, match="OPQ scenario variant requires"):
        lane("disabled", acra_marketplace_ownership_overlay="garden_legacy_supplement", **MULTI)


def test_profile_issuers_must_be_declared_non_overlay_holders() -> None:
    data = OPQ_GARDEN_ABC_SCENARIO.model_dump()
    for issuers in ({GARDEN_UEN}, {FIVE_LAYER_ROOT_UEN}, {"200811111M"}):
        with pytest.raises(ValidationError, match="business profile issuers"):
            HybridOverlayScenario.model_validate({**data, "business_profile_issuers": issuers})
    # D-112 (O7): no scenario declares the issued-capital assumption any more, so an
    # unnamed profile issuer set is simply a scenario that reads no business profile.
    assert not HybridOverlayScenario.model_validate(
        {**data, "business_profile_issuers": set()}
    ).business_profile_issuers


# --- The calculation: unchanged engine, exact declared and derived values ----------------


def test_the_multi_holder_graph_calculates_the_approved_values_with_provenance() -> None:
    ownership, record, channel = analysed()
    names = {party.party_id: party.display_name for party in record.parties}
    edges = {
        (names[edge.parent_party_id], names[edge.child_party_id]): edge
        for edge in record.relationships
    }
    for child in ("GARDEN BUSINESS", "ABC COMPANY PTE. LTD."):
        declared = edges[("OPQ PTE. LTD.", child)]
        assert declared.ownership_percent == Decimal("50")
        assert (declared.provenance.provider, declared.provenance.environment) == (
            OVERLAY_RELATIONSHIP_PROVIDER,
            "LOCAL",
        )
        assert declared.provenance.source_reference.endswith(OWNER_DECLARED_PERCENT_SUFFIX)
    # Garden's register and SIM LIM's rows are unchanged.
    assert edges[("GARDEN BUSINESS", "SIM LIM PTE. LTD.")].ownership_percent == Decimal("62.5")
    assert edges[("GARDEN BUSINESS", "LIM CHOON HUAT")].ownership_percent == Decimal("37.5")
    assert edges[("SIM LIM PTE. LTD.", "ABCD123")].provenance.provider == POC_EQUAL_UNITS_PROVIDER
    # ABC's holder: 1000 / 1000 issued ORDINARY, a labelled POC link, never OPQ shares.
    abc_link = edges[("ABC COMPANY PTE. LTD.", ABC_SYNTHETIC_HOLDER_NAME)]
    assert abc_link.ownership_percent == Decimal("100")
    assert (abc_link.provenance.provider, abc_link.provenance.environment) == (
        POC_ISSUED_CAPITAL_PROVIDER,
        "LOCAL",
    )
    assert len(record.relationships) == 8
    assert by_name(record) == EXPECTED
    met = {
        item.party.display_name
        for item in record.candidates
        if item.synthetic_basis_threshold_result == "MET"
    }
    assert met == {ABC_SYNTHETIC_HOLDER_NAME, "ABCD123"}
    assert all(item.classification == "REVIEW_REQUIRED" for item in record.candidates)
    abc = next(item for item in record.candidates if item.party.display_name == "ABCD123")
    assert [path.calculation for path in abc.paths] == ["50% x 62.5% x 81.818182% = 25.568181875%"]
    entities = {
        names[key]: sum((path.effective_ownership_percent for path in value), Decimal("0"))
        for key, value in ownership.entity_effective_interests(record).items()
    }
    assert entities == {
        "GARDEN BUSINESS": Decimal("50"),
        "SIM LIM PTE. LTD.": Decimal("31.25"),
        "ABC COMPANY PTE. LTD.": Decimal("50"),
    }
    # Exactly one businessProfile read, for ABC only.
    assert channel.calls[("BUSINESS_PROFILE", ABC_COMPANY_UEN)] == 1
    assert (
        sum(count for (label, _), count in channel.calls.items() if label == "BUSINESS_PROFILE")
        == 1
    )


def test_the_business_profile_is_retained_as_returned_with_the_assumption_separate() -> None:
    _, record, _ = analysed()
    item = abc_record(record)
    assert (item.outcome, item.reason_code) == (
        OwnershipDiscoveryOutcome.PROVIDER_PARTIAL,
        "OFFICIAL_BUSINESS_PROFILE_ISSUED_CAPITAL",
    )
    assert item.identity_basis is None and not item.official_shareholders
    profile = item.official_business_profile
    assert profile is not None
    assert (profile.entity_name, profile.company_type, profile.status_of_company) == (
        "ABC COMPANY PTE. LTD.",
        "EXEMPT PRIVATE COMPANY LIMITED BY SHARES",
        "LIVE COMPANY",
    )
    [row] = profile.shareholders
    assert (row.display_name, row.source_category, row.number_of_shares, row.share_type) == (
        ABC_SYNTHETIC_HOLDER_NAME,
        "Individual",
        Decimal("1000"),
        "ORDINARY",
    )
    # The provider returned no status; the current status is a separate recorded assumption.
    assert (row.provider_status, row.assumed_current) == (None, True)
    assert row.source_party_id.startswith("BP-") and "SYNTHETIC" not in row.source_party_id
    [issued] = profile.issued_share_capital
    [paid] = profile.paid_up_capital
    assert (issued.number_of_shares, issued.currency, issued.amount) == (
        Decimal("1000"),
        "SINGAPORE DOLLAR",
        Decimal("1000.0"),
    )
    assert paid.number_of_shares == Decimal("1000")
    assert (profile.source_operation, profile.environment, profile.lookup) == (
        "BUSINESS_PROFILE",
        "MOCK",
        "BUSINESS_PROFILE_FETCHED",
    )
    assert profile.evidence_reference == f"acra:business_profile:{ABC_COMPANY_UEN}"


# --- POC acceptance and readiness ----------------------------------------------------------


def test_the_observed_variant_is_calculated_but_never_accepted() -> None:
    ownership, record, _ = analysed()
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert sorted(item.code for item in record.issues) == [
        "OWNERSHIP_DENOMINATOR_REQUIRED",
        "OWNERSHIP_METHOD_UNSUPPORTED",
        "SYNTHETIC_OWNERSHIP_EVIDENCE",
    ]
    # D-112 (O7): the issued-capital link is still derived and labelled, but no scenario
    # declaration accepts the variant for readiness.
    assert f"{ABC_COMPANY_UEN}.BPIC_{ABC_COMPANY_UEN}_1" in {
        edge.relationship_id for edge in record.relationships
    }
    assert record.poc_acceptance is None
    assert not ownership.poc_basis_accepted(record)
    assert garden_roles(record)[0] == ("OWNER", "CEASED")
    synthetic = next(i for i in record.issues if i.code == "SYNTHETIC_OWNERSHIP_EVIDENCE")
    assert "LOCAL_POC_ISSUED_CAPITAL_BASIS" in synthetic.message
    assert abc_record(record).party_id in synthetic.affected_party_ids


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"holder_numberOfShares": 999.0}, "rows short of issued capital"),
        ({"issued_numberOfShares": 2000.0}, "issued capital larger than the rows"),
        ({"holder_shareType": "PREFERENCE"}, "different share class"),
        ({"holder_currency": "AUSTRALIA DOLLAR"}, "different currency"),
        ({"paid_numberOfShares": 500.0}, "paid-up capital contradicts issued capital"),
        ({"holder_category": "Corporate"}, "a corporate row is outside the interpretation"),
        ({"issuedShareCapital": []}, "missing issued capital"),
        ({"holder_status": "Withdrawn"}, "a returned status is never assumed away"),
        ({"holder_status": "Active"}, "even an Active status is outside the status-free rule"),
    ],
)
def test_incompatible_profiles_are_retained_but_never_accepted(
    changes: dict[str, object], reason: str
) -> None:
    profile: Any = mutated(**{k: v for k, v in changes.items() if k != "holder_status"})
    if "holder_status" in changes:
        profile["entities"][0]["shareholder"][0]["status"] = changes["holder_status"]
    ownership, record, _ = analysed(profile=profile)
    item = abc_record(record)
    assert item.reason_code == "OFFICIAL_BUSINESS_PROFILE_RETAINED", reason
    assert item.official_business_profile is not None
    assert not any(row.assumed_current for row in item.official_business_profile.shareholders)
    assert not any(
        e.provenance.provider == POC_ISSUED_CAPITAL_PROVIDER for e in record.relationships
    )
    assert record.poc_acceptance is None, reason
    assert not ownership.poc_basis_accepted(record)
    assert record.discovery is not None and record.discovery.topology_complete is False


@pytest.mark.parametrize(
    ("profile", "outcome", "reason"),
    [
        ({"entities": []}, OwnershipDiscoveryOutcome.NOT_FOUND, "OFFICIAL_BUSINESS_PROFILE_EMPTY"),
        (
            {"entities": [{"uen": "999999999Z", "entityName": "X"}]},
            OwnershipDiscoveryOutcome.PROVIDER_FAILED,
            "REGISTRY_OPERATION_MALFORMED_RESPONSE",
        ),
        (
            mutated(holder_numberOfShares=1000.5),
            OwnershipDiscoveryOutcome.PROVIDER_FAILED,
            "REGISTRY_OPERATION_MALFORMED_RESPONSE",
        ),
    ],
)
def test_empty_or_malformed_profiles_fail_closed(
    profile: dict[str, object], outcome: OwnershipDiscoveryOutcome, reason: str
) -> None:
    ownership, record, _ = analysed(profile=profile)
    item = abc_record(record)
    assert (item.outcome, item.reason_code, item.official_business_profile) == (
        outcome,
        reason,
        None,
    )
    assert record.poc_acceptance is None
    assert not ownership.poc_basis_accepted(record)


def test_a_provider_failure_retains_nothing_and_blocks() -> None:
    channel = transport()
    channel.business_profiles[ABC_COMPANY_UEN] = abc_business_profile()
    original = channel.get

    def failing(url: str, **kwargs: Any) -> Any:
        if "businessProfile" in url:
            from app.connectors.acra_sandbox import AcraHttpResponse

            return AcraHttpResponse(503, {}, "application/json", 2)
        return original(url, **kwargs)

    channel.get = failing  # type: ignore[method-assign]
    ownership, record, _ = analysed(transport=channel)
    item = abc_record(record)
    assert item.outcome == OwnershipDiscoveryOutcome.PROVIDER_FAILED
    assert item.official_business_profile is None
    assert record.poc_acceptance is None


def test_the_profile_read_never_happens_outside_the_named_issuers() -> None:
    for variant in ("five_layer_simulation", "garden_sim_lim_chain"):
        _, _, channel = analysed(acra_marketplace_opq_scenario=variant)
        assert not any(label == "BUSINESS_PROFILE" for label, _ in channel.calls)


def test_the_match_rule_is_exact_and_status_free_only() -> None:
    _, record, _ = analysed()
    profile = abc_record(record).official_business_profile
    assert profile is not None
    assert issued_capital_matches(profile.shareholders, profile.issued_share_capital)
    [row] = profile.shareholders
    for change in (
        {"provider_status": "Active", "assumed_current": False},
        {"number_of_shares": Decimal("0")},
        {"share_type": None},
    ):
        assert not issued_capital_matches(
            (row.model_copy(update=change),), profile.issued_share_capital
        )
    assert not issued_capital_matches((row,), profile.issued_share_capital * 2), (
        "two issued classes are never combined"
    )


def test_no_composition_or_variant_grants_authority() -> None:
    _, disabled, _ = analysed("disabled")
    assert disabled.poc_acceptance is None
    ownership, record, _ = analysed()
    # D-112 (O7): enabled or not, the scenario variant is never accepted.
    assert record.poc_acceptance is None
    assert not ownership.poc_basis_accepted(record)
    _, reverted = service_lane(
        "accept_eligible_poc", transport(), acra_marketplace_opq_scenario="garden_sim_lim_chain"
    )
    assert not reverted.poc_basis_accepted(record)
    _, off = service_lane("disabled", transport(), **MULTI)
    assert not off.poc_basis_accepted(record)


def test_the_case_is_calculated_but_held_for_ownership_review() -> None:
    settings = lane(**MULTI)
    assert settings.goldtier_connector_mode == "mock"
    bundle = build_persistence_bundle(settings)
    with runtime(settings, bundle, transport()) as client:
        case_id = start(client, FIVE_LAYER_FIELDS, "five-layer-marketplace-hybrid-client.pdf")[
            "case"
        ]["case_id"]
        ownership = ownership_of(client, case_id)
        summary = summary_of(client, case_id)
        assert (ownership["poc_basis_accepted"], ownership["state"]) == (False, "REVIEW_REQUIRED")
        assert ownership["poc_acceptance"] is None
        assert {
            item["party"]["display_name"]: Decimal(item["aggregated_ownership_percent"])
            for item in ownership["candidates"]
        } == EXPECTED
        providers = {edge["provenance"]["provider"] for edge in ownership["relationships"]}
        assert POC_ISSUED_CAPITAL_PROVIDER in providers
        assert all(
            "source_reference" not in edge["provenance"] for edge in ownership["relationships"]
        )
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


def test_the_records_round_trip_in_schema_fifteen_and_older_readers_reject_them() -> None:
    from test_official_shareholder_evidence import snapshot_of

    from app.persistence.models import DurableCaseSnapshot, reject_scenario_poc_legacy_fields

    onboarding, ownership = service_lane("accept_eligible_poc", transport(), **MULTI)
    case = onboarding.create_staged_case(FIVE_LAYER_ROOT_UEN)
    ownership.load(case_id=case.case_id)
    record = ownership.analyze(case_id=case.case_id)
    encoded = snapshot_of(onboarding, record).model_dump(mode="json")
    assert encoded["schema_version"] == 20
    # Backend-only: a dump omits the ledger, and its absence fails closed.
    assert DurableCaseSnapshot.model_validate(encoded).ownership == record.model_copy(
        update={"poc_interest_ledger": None}
    )
    profile_only = {
        "ownership": {
            "discovery": {
                "records": [
                    {"official_business_profile": {"entity_name": "X"}},
                ]
            }
        }
    }
    with pytest.raises(ValueError, match="D-088 business profile"):
        reject_scenario_poc_legacy_fields(profile_only)
    legacy_links = {
        "ownership": {
            "poc_acceptance": {
                "policy": "D082_HYBRID_POC_EQUAL_UNITS_V1",
                "issued_capital_relationship_ids": ["X"],
            }
        }
    }
    with pytest.raises(ValueError, match="D-085 POC acceptance"):
        reject_scenario_poc_legacy_fields(legacy_links)


def test_an_unnamed_holder_is_never_read_or_interpreted(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.connectors import hybrid_ownership_overlay as overlay

    assert OPQ_GARDEN_ABC_SCENARIO.poc_acceptance is None
    unnamed = HybridOverlayScenario.model_validate(
        {**OPQ_GARDEN_ABC_SCENARIO.model_dump(), "business_profile_issuers": set()}
    )
    monkeypatch.setitem(overlay._OPQ_VARIANTS, "garden_abc_multi_holder", unnamed)
    ownership, record, channel = analysed()
    item = abc_record(record)
    assert (item.outcome, item.reason_code, item.official_business_profile) == (
        OwnershipDiscoveryOutcome.NOT_FOUND,
        "OFFICIAL_SHAREHOLDERS_EMPTY",
        None,
    )
    assert not any(label == "BUSINESS_PROFILE" for label, _ in channel.calls)
    assert not any(
        e.provenance.provider == POC_ISSUED_CAPITAL_PROVIDER for e in record.relationships
    )
    assert record.poc_acceptance is None
    assert not ownership.poc_basis_accepted(record)


def test_mixed_class_rows_that_total_the_issued_count_are_never_assumed_current() -> None:
    # D-088 QG P3-1: two rows of different classes may sum to the issued count; classes
    # are never combined, so the profile is retained and nothing attaches.
    profile: Any = abc_business_profile()
    entity = profile["entities"][0]
    first = dict(entity["shareholder"][0], numberOfShares=500.0)
    second = dict(first, id="SYNTHETIC-ABC-HOLDER-2", principalName="SYNTHETIC ABC HOLDER 2")
    second["shareType"] = "PREFERENCE"
    entity["shareholder"] = [first, second]
    ownership, record, _ = analysed(profile=profile)
    item = abc_record(record)
    assert item.reason_code == "OFFICIAL_BUSINESS_PROFILE_RETAINED"
    assert item.official_business_profile is not None
    assert [row.assumed_current for row in item.official_business_profile.shareholders] == [
        False,
        False,
    ]
    assert record.poc_acceptance is None
    assert not ownership.poc_basis_accepted(record)


def test_a_returned_status_can_never_be_recorded_as_assumed_current() -> None:
    # D-088 QG P3-2: the provider status and the POC assumption stay separate.
    from app.domain.ownership import OfficialBusinessProfileShareholder

    row = {
        "source_party_id": "BP-" + "0" * 24,
        "display_name": "SYNTHETIC ABC HOLDER",
        "party_type": "NATURAL_PERSON",
        "source_category": "Individual",
        "number_of_shares": Decimal("1000"),
        "share_type": "ORDINARY",
        "currency": "SINGAPORE DOLLAR",
    }
    OfficialBusinessProfileShareholder.model_validate({**row, "assumed_current": True})
    OfficialBusinessProfileShareholder.model_validate(
        {**row, "provider_status": "Active", "assumed_current": False}
    )
    with pytest.raises(ValidationError, match="never replaced"):
        OfficialBusinessProfileShareholder.model_validate(
            {**row, "provider_status": "Active", "assumed_current": True}
        )


# D-112 (owner O7, 2026-11-01): obsolete, not weakened. It asserted tampering against
# the scenario's own recorded acceptance; no scenario declares acceptance any more.
RETIRED_D089_EXPECTATIONS = ("test_tampered_issued_capital_links_are_never_accepted",)
