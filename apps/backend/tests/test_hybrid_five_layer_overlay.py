"""Hybrid official-Marketplace-Mock plus whitelisted local direct overlay (D-077).

Every test is offline: the real official connector, decoders, registry cache, discovery
coordinator and single Decimal engine run against an allowlisted in-process transport.
Nothing here is an observed ACRA response or a Live/Marketplace interoperability claim.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
from pydantic import SecretStr, ValidationError
from scripts.five_layer_hybrid_fixture import (
    ALLOWLISTED_UENS,
    FIVE_LAYER_ROOT_NAME,
    OfflineFiveLayerProtocolTransport,
)

from app.composition import build_onboarding_service, build_ownership_analysis_service
from app.config import Settings
from app.connectors.hybrid_ownership_overlay import (
    FIVE_LAYER_ROOT_UEN,
    FIVE_LAYER_SCENARIO_ID,
    GARDEN_DIRECT_OVERLAY_SCENARIO_ID,
    HYBRID_OVERLAY_SCENARIOS,
    L2_UEN,
    L3_UEN,
    L4A_UEN,
    L4B_UEN,
    L5_UEN,
    OVERLAY_RELATIONSHIP_PROVIDER,
    HybridOverlayScenario,
    HybridOwnershipOverlayCatalogue,
    OverlayHolder,
    OverlayIssuer,
    official_marketplace_root_is_eligible,
)
from app.domain.models import (
    RegistryCacheKey,
    RegistryProviderIdentity,
    SourceEnvironment,
    SourceSystem,
)
from app.domain.ownership import (
    OwnershipAnalysisRecord,
    OwnershipAnalysisState,
    OwnershipCandidate,
    OwnershipCandidateClassification,
    OwnershipDiscoveryAudit,
    OwnershipDiscoveryOutcome,
    OwnershipDiscoveryRecord,
    OwnershipEnvironment,
    OwnershipIssueCode,
    OwnershipThresholdResult,
)
from app.domain.policy import (
    CasePolicySnapshot,
    EvidenceClassifierPolicy,
    OwnershipDiscoveryPolicySnapshot,
    RegistryPolicySnapshot,
)
from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.models import DurableCaseSnapshot
from app.persistence.mongo_case_store import MongoCaseStore
from app.services.errors import OnboardingInfrastructureError
from app.services.onboarding import OnboardingService
from app.services.ownership_analysis import (
    OwnershipAnalysisService,
    synthetic_basis_threshold_results,
)
from app.services.ownership_discovery import OwnershipDiscoveryCoordinator
from app.services.ownership_errors import OwnershipInfrastructureError, OwnershipRequestError
from app.services.ownership_repository import InMemoryOwnershipAnalysisRepository
from app.services.registry_cache_repository import (
    InMemoryRegistrySnapshotRepository,
    RegistrySnapshotRepositoryInvalidError,
)

# Sanitized operation-specific candidate index from the user-supplied seven-page sample
# catalogue (Last updated 18 November 2025): UEN -> page/operation reference only.
SAMPLE_CATALOGUE = {
    "201511222D": "p.6 Entity Basic Information (Co_Profile_Local)",
    "200811111M": "p.1-2 Entity Directory Search / Verification / Key Dates",
    "201688888A": "p.7 Business Profile (Co_Profile_Local)",
    "200811111K": "p.3 Foreign and Redomiciliation Company Details",
    "199801111H": "p.5 Company FYE / LLP Annual Declaration",
    "111111111K": "p.4 Company Capital Details",
    "11111999A": "p.6 Entity Basic Information (Biz_Profile)",
    "111111111M": "p.2-5 operation-specific Co_Profile_Local samples",
}
DISCOVERY = OwnershipDiscoveryPolicySnapshot(
    trace_threshold_percent=Decimal("10.000000"),
    max_corporate_depth=5,
    call_budget_enabled=False,
    call_budget_max=10,
)


def case_policy(
    discovery: OwnershipDiscoveryPolicySnapshot | None = DISCOVERY,
) -> CasePolicySnapshot:
    return CasePolicySnapshot(
        snapshot_label="SYNTHETIC_HYBRID_TEST",
        catalogue_version=1,
        idp_review_confidence_threshold=Decimal("0.85"),
        ubo_threshold_percent=Decimal("25.000000"),
        registry=RegistryPolicySnapshot(),
        evidence_classifier=EvidenceClassifierPolicy(),
        ownership_discovery=discovery,
        policy_identity="b" * 64,
        bound_at=datetime(2026, 10, 23, tzinfo=UTC),
    )


def settings(overlay: str = "hybrid_direct_overlay") -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        clm_persistence_mode="memory",
        registry_cache_mode="auto",
        acra_connector_mode="api_marketplace_mock",
        goldtier_connector_mode="mock",
        acra_marketplace_ownership_overlay=overlay,
        acra_api_marketplace_mock_client_id=SecretStr("synthetic-offline-client"),
        acra_api_marketplace_mock_secret_key=SecretStr("synthetic-offline-key"),
    )


def build(
    transport: OfflineFiveLayerProtocolTransport | None = None,
    *,
    overlay: str = "hybrid_direct_overlay",
    discovery: OwnershipDiscoveryPolicySnapshot | None = DISCOVERY,
    repository: Any = None,
) -> tuple[OnboardingService, OwnershipAnalysisService, OfflineFiveLayerProtocolTransport]:
    active = transport or OfflineFiveLayerProtocolTransport()
    active_settings = settings(overlay)
    onboarding = build_onboarding_service(
        settings=active_settings,
        acra_transport=active,
        acra_marketplace_token_transport=active,
        policy_snapshot_provider=lambda: case_policy(discovery),
        registry_snapshot_repository=repository,
    )
    return onboarding, build_ownership_analysis_service(onboarding, active_settings), active


def analyze(
    onboarding: OnboardingService, ownership: OwnershipAnalysisService, uen: str
) -> OwnershipAnalysisRecord:
    case = onboarding.create_staged_case(uen)
    ownership.load(case_id=case.case_id)
    return ownership.analyze(case_id=case.case_id)


def custom_service(
    onboarding: OnboardingService, scenarios: tuple[HybridOverlayScenario, ...]
) -> OwnershipAnalysisService:
    """The composition's hybrid wiring with a test-only scenario catalogue."""
    from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider

    return OwnershipAnalysisService(
        cases=onboarding,
        provider=RegistryAcquisitionOwnershipProvider(onboarding),
        hybrid_overlay=HybridOwnershipOverlayCatalogue(scenarios),
        discovery=OwnershipDiscoveryCoordinator(onboarding),
        repository=InMemoryOwnershipAnalysisRepository(),
        threshold_percent=Decimal("25"),
        max_parties=100,
        max_relationships=200,
        max_depth=8,
        max_paths_per_candidate=64,
        max_total_paths=256,
    )


def by_name(record: OwnershipAnalysisRecord) -> dict[str, OwnershipCandidate]:
    return {item.party.display_name: item for item in record.candidates}


def records(record: OwnershipAnalysisRecord) -> dict[str, OwnershipDiscoveryRecord]:
    assert record.discovery is not None
    return {item.registration_number or item.party_id: item for item in record.discovery.records}


def codes(record: OwnershipAnalysisRecord) -> set[OwnershipIssueCode]:
    return {item.code for item in record.issues}


def company_profile(uen: str, name: str, constitution: str | None = None) -> dict[str, object]:
    entity: dict[str, object] = {"uen": uen, "name": name}
    if constitution is not None:
        entity["entityConstnDetailsAndType"] = {"constitution": constitution}
    return {"entities": [entity]}


# --- 1. Catalogue traceability and strict overlay authoring --------------------------


def test_every_scenario_issuer_and_corporate_holder_is_traceable_to_the_sample_catalogue() -> None:
    five = next(
        item for item in HYBRID_OVERLAY_SCENARIOS if item.scenario_id == FIVE_LAYER_SCENARIO_ID
    )
    assert five.root_uen == FIVE_LAYER_ROOT_UEN
    corporate_layers = {L2_UEN, L3_UEN, L4A_UEN, L4B_UEN, L5_UEN}
    assert {item.issuer_uen for item in five.issuers} == {FIVE_LAYER_ROOT_UEN, *corporate_layers}
    for scenario in HYBRID_OVERLAY_SCENARIOS:
        for issuer in scenario.issuers:
            assert issuer.issuer_uen in SAMPLE_CATALOGUE
            for holder in issuer.holders:
                if holder.category == "Corporate":
                    assert holder.registration_number in SAMPLE_CATALOGUE
    # Below the official root every declared identity is visibly synthetic.
    for issuer in five.issuers:
        for holder in issuer.holders:
            assert "(SYNTHETIC" in holder.holder_name
    assert frozenset(SAMPLE_CATALOGUE) == ALLOWLISTED_UENS


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"declared_active_units": Decimal("9999")}, "denominator"),
        ({"holders": ()}, "at least 1"),
        ({"issuer_uen": "NOT-A-UEN"}, "Singapore UEN"),
    ],
)
def test_overlay_issuers_fail_closed_on_incomplete_or_invalid_registers(
    change: dict[str, Any], message: str
) -> None:
    issuer = HYBRID_OVERLAY_SCENARIOS[1].issuers[0]
    with pytest.raises(ValidationError, match=message):
        OverlayIssuer.model_validate({**issuer.model_dump(), **change})


def test_overlay_holders_reject_float_units_group_semantics_and_unverified_corporates() -> None:
    base = {"holder_id": "SYN-X", "holder_name": "X (SYNTHETIC)", "category": "Individual"}
    with pytest.raises(ValidationError, match="exact Decimal"):
        OverlayHolder.model_validate({**base, "share_units": 1.5})
    for category in ("Group", "Member"):
        with pytest.raises(ValidationError):
            OverlayHolder.model_validate({**base, "category": category, "share_units": "1"})
    with pytest.raises(ValidationError, match="registration"):
        OverlayHolder.model_validate({**base, "category": "Corporate", "share_units": "1"})
    with pytest.raises(ValidationError, match="UEN"):
        OverlayHolder.model_validate(
            {
                **base,
                "holder_id": "ABC",
                "category": "Corporate",
                "registration_number": "ABC",
                "share_units": "1",
            }
        )
    with pytest.raises(ValidationError):
        OverlayHolder.model_validate({**base, "share_units": "1", "share_class": "PREFERENCE"})


def test_withdrawn_rows_never_count_and_duplicate_or_self_holders_fail() -> None:
    active = OverlayHolder(
        holder_id="SYN-A",
        holder_name="A (SYNTHETIC)",
        category="Individual",
        share_units=Decimal("3"),
    )
    withdrawn = OverlayHolder(
        holder_id="SYN-W",
        holder_name="W (SYNTHETIC)",
        category="Individual",
        share_units=Decimal("97"),
        status="Withdrawn",
    )
    issuer = OverlayIssuer(
        issuer_uen="300000001A",
        local_display_name="T (SYNTHETIC)",
        declared_active_units=Decimal("3"),
        holders=(active, withdrawn),
    )
    assert issuer.declared_active_units == Decimal("3")
    with pytest.raises(ValidationError, match="unique"):
        OverlayIssuer(
            issuer_uen="300000001A",
            local_display_name="T",
            declared_active_units=Decimal("6"),
            holders=(active, active),
        )
    with pytest.raises(ValidationError, match="external"):
        OverlayIssuer(
            issuer_uen="300000001A",
            local_display_name="T",
            declared_active_units=Decimal("1"),
            holders=(
                OverlayHolder(
                    holder_id="300000001A",
                    holder_name="SELF",
                    category="Corporate",
                    registration_number="300000001A",
                    share_units=Decimal("1"),
                ),
            ),
        )


def test_hybrid_mode_is_exclusive_and_official_lane_only() -> None:
    with pytest.raises(ValidationError, match="official Marketplace Mock"):
        Settings(
            _env_file=None,
            acra_connector_mode="mock",
            acra_marketplace_ownership_overlay="hybrid_direct_overlay",
        )
    onboarding, _, _ = build()
    with pytest.raises(ValueError, match="exclusive"):
        OwnershipAnalysisService(
            cases=onboarding,
            provider=object(),  # type: ignore[arg-type]
            repository=InMemoryOwnershipAnalysisRepository(),
            threshold_percent=Decimal("25"),
            garden_supplement_enabled=True,
            hybrid_overlay=HybridOwnershipOverlayCatalogue(),
            max_parties=1,
            max_relationships=1,
            max_depth=1,
            max_paths_per_candidate=1,
            max_total_paths=1,
        )


# --- 2. Five-layer onboarding: topology, Decimal paths, provenance, review ------------


def test_five_layer_case_attaches_five_corporate_levels_with_exact_paths_and_review() -> None:
    onboarding, ownership, transport = build()
    record = analyze(onboarding, ownership, FIVE_LAYER_ROOT_UEN)

    assert record.source_classification == "OFFICIAL_MOCK_PLUS_LOCAL_DIRECT_OVERLAY"
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    root = next(item for item in record.parties if item.party_id == record.root_party_id)
    assert (root.display_name, root.registration_number) == (
        FIVE_LAYER_ROOT_NAME,
        FIVE_LAYER_ROOT_UEN,
    )
    # Every edge is a local synthetic link; none claims ACRA or Mock provenance.
    assert {
        (edge.provenance.provider, edge.provenance.environment) for edge in record.relationships
    } == {(OVERLAY_RELATIONSHIP_PROVIDER, OwnershipEnvironment.LOCAL)}
    found = records(record)
    assert {uen: item.depth for uen, item in found.items()} == {
        L2_UEN: 1,
        L3_UEN: 2,
        L4A_UEN: 3,
        L4B_UEN: 3,
        L5_UEN: 4,
    }
    for item in found.values():
        assert item.outcome == OwnershipDiscoveryOutcome.LOCAL_SYNTHETIC_OVERLAY
        assert item.identity_basis == "LOCAL_SYNTHETIC_IDENTITY"
        assert item.official_entity_lookup == "NOT_FOUND"
    assert found[L5_UEN].max_effective_percent == Decimal("40")

    candidates = by_name(record)
    expected = {
        "ALEX TAN (SYNTHETIC PERSON)": ("20", ["20"], OwnershipThresholdResult.NOT_MET),
        "BEATRICE LIM (SYNTHETIC PERSON)": ("30", ["30"], OwnershipThresholdResult.MET),
        "CHARLES ONG (SYNTHETIC PERSON)": ("10", ["10"], OwnershipThresholdResult.NOT_MET),
        "DIANA KOH (SYNTHETIC PERSON)": ("25", ["18.75", "6.25"], OwnershipThresholdResult.MET),
        "EDWARD NG (SYNTHETIC PERSON)": ("15", ["11.25", "3.75"], OwnershipThresholdResult.NOT_MET),
    }
    assert set(candidates) == set(expected)
    for name, (total, paths, basis) in expected.items():
        candidate = candidates[name]
        assert candidate.aggregated_ownership_percent == Decimal(total)
        assert sorted(path.effective_ownership_percent for path in candidate.paths) == sorted(
            Decimal(value) for value in paths
        )
        # The authoritative classification stays review; the comparison is labelled apart.
        assert candidate.classification == OwnershipCandidateClassification.REVIEW_REQUIRED
        assert candidate.threshold_result == OwnershipThresholdResult.INDETERMINATE
        assert candidate.synthetic_basis_threshold_result == basis
    # L1 -> L2 -> L3 -> L4A/L4B -> L5 -> person: five corporate levels on both diamond arms.
    five_edge = {
        path.calculation
        for path in candidates["DIANA KOH (SYNTHETIC PERSON)"].paths
        if len(path.edges) == 5
    }
    assert five_edge == {
        "80% x 62.5% x 60% x 100% x 62.5% = 18.75%",
        "80% x 62.5% x 40% x 50% x 62.5% = 6.25%",
    }

    assert {
        OwnershipIssueCode.SYNTHETIC_OWNERSHIP_EVIDENCE,
        OwnershipIssueCode.OWNERSHIP_METHOD_UNSUPPORTED,
    } <= codes(record)
    assert OwnershipIssueCode.CORPORATE_OWNERSHIP_UNRESOLVED not in codes(record)
    audit = record.discovery
    assert audit is not None
    assert (
        audit.overlay_scenario_id,
        audit.graph_complete,
        audit.topology_complete,
        audit.official_identity_complete,
        audit.quantitative_evidence_complete,
        audit.classification_certainty,
    ) == (FIVE_LAYER_SCENARIO_ID, False, True, False, False, "UNCERTAIN")
    assert (audit.registry_lookups, audit.provider_backed_lookups, audit.cache_hits) == (5, 5, 0)
    # Root entity profile twice (company + embedded officers), each issuer once; the
    # diamond's L5 is retrieved once; no relationship or shareholder GET is dispatched.
    assert transport.calls == {
        ("ENTITY_PROFILE", FIVE_LAYER_ROOT_UEN): 2,
        **{("ENTITY_PROFILE", uen): 1 for uen in (L2_UEN, L3_UEN, L4A_UEN, L4B_UEN, L5_UEN)},
    }
    assert transport.token_requests == 1
    assert record.supplemental_evidence and {
        item.provider for item in record.supplemental_evidence
    } == {OVERLAY_RELATIONSHIP_PROVIDER}


def test_repeat_onboarding_reuses_the_official_namespace_with_zero_http_gets() -> None:
    onboarding, ownership, transport = build()
    analyze(onboarding, ownership, FIVE_LAYER_ROOT_UEN)
    first_gets, first_tokens = transport.get_count, transport.token_requests
    second = analyze(onboarding, ownership, FIVE_LAYER_ROOT_UEN)
    assert (transport.get_count, transport.token_requests) == (first_gets, first_tokens)
    audit = second.discovery
    assert audit is not None
    assert (audit.registry_lookups, audit.provider_backed_lookups, audit.cache_hits) == (5, 0, 5)
    assert {item.official_entity_lookup for item in audit.records} == {"NOT_FOUND_CACHE_REUSED"}
    assert by_name(second)["DIANA KOH (SYNTHETIC PERSON)"].aggregated_ownership_percent == Decimal(
        "25"
    )


def test_an_official_issuer_profile_supplies_identity_while_links_stay_local() -> None:
    transport = OfflineFiveLayerProtocolTransport()
    transport.profiles[L2_UEN] = company_profile(
        L2_UEN, "OFFICIAL SYNTHETIC L2 PTE. LTD.", "PRIVATE COMPANY LIMITED BY SHARES"
    )
    onboarding, ownership, _ = build(transport)
    record = analyze(onboarding, ownership, FIVE_LAYER_ROOT_UEN)
    l2 = records(record)[L2_UEN]
    assert (l2.outcome, l2.identity_basis, l2.official_entity_lookup, l2.official_legal_form) == (
        OwnershipDiscoveryOutcome.LOCAL_SYNTHETIC_OVERLAY,
        "OFFICIAL_MOCK_ENTITY_PROFILE",
        "ENTITY_PROFILE_FETCHED",
        "COMPANY",
    )
    assert l2.display_name == "OFFICIAL SYNTHETIC L2 PTE. LTD."
    assert record.discovery is not None and not record.discovery.official_identity_complete
    # A COMPANY profile dispatches the supported (empty) shareholder operation once.
    assert transport.calls[("SHAREHOLDERS", L2_UEN)] == 1
    again = analyze(onboarding, ownership, FIVE_LAYER_ROOT_UEN)
    assert records(again)[L2_UEN].official_entity_lookup == "ENTITY_PROFILE_CACHE_REUSED"
    # A cached entity prefix never counts as a complete hit: the required (empty)
    # shareholder operation is read again and the lookup stays provider-backed.
    assert transport.calls[("SHAREHOLDERS", L2_UEN)] == 2
    assert again.discovery is not None and again.discovery.provider_backed_lookups == 1


def test_official_shareholder_rows_are_never_overridden_by_the_overlay() -> None:
    transport = OfflineFiveLayerProtocolTransport()
    transport.profiles[L2_UEN] = company_profile(
        L2_UEN, "OFFICIAL SYNTHETIC L2 PTE. LTD.", "PRIVATE COMPANY LIMITED BY SHARES"
    )
    transport.shareholders[L2_UEN] = {
        "entities": [
            {
                "uen": L2_UEN,
                "name": "OFFICIAL L2",
                "shareholders": {
                    "individual": [
                        {
                            "shareholderCategory": "Individual",
                            "shareholderId": "SYN-OFFICIAL-1",
                            "shareholderName": "OFFICIAL HOLDER (SYNTHETIC)",
                            "shareAllotted": 10,
                            "shareType": "Ordinary",
                            "currency": "SINGAPORE DOLLAR",
                            "appointmentDate": "2020-01-01",
                            "status": "Active",
                        }
                    ],
                    "grouping": [],
                },
            }
        ]
    }
    onboarding, ownership, _ = build(transport)
    record = analyze(onboarding, ownership, FIVE_LAYER_ROOT_UEN)
    l2 = records(record)[L2_UEN]
    assert (l2.outcome, l2.reason_code) == (
        OwnershipDiscoveryOutcome.PROVIDER_PARTIAL,
        "OFFICIAL_QUANTITY_PRECLUDES_OVERLAY",
    )
    assert OwnershipIssueCode.CORPORATE_OWNERSHIP_UNRESOLVED in codes(record)
    assert set(by_name(record)) == {"ALEX TAN (SYNTHETIC PERSON)"}
    assert by_name(record)["ALEX TAN (SYNTHETIC PERSON)"].synthetic_basis_threshold_result == (
        OwnershipThresholdResult.INDETERMINATE
    )


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        (500, "REGISTRY_PROVIDER_FAILED"),
        (429, "REGISTRY_PROVIDER_FAILED"),
        (401, "REGISTRY_PROVIDER_FAILED"),
        (httpx.ReadTimeout("synthetic"), "REGISTRY_PROVIDER_FAILED"),
    ],
)
def test_provider_failure_never_selects_the_overlay(failure: int | Exception, reason: str) -> None:
    transport = OfflineFiveLayerProtocolTransport(failures={L3_UEN: failure})
    onboarding, ownership, _ = build(transport)
    record = analyze(onboarding, ownership, FIVE_LAYER_ROOT_UEN)
    l3 = records(record)[L3_UEN]
    assert (l3.outcome, l3.reason_code, l3.identity_basis) == (
        OwnershipDiscoveryOutcome.PROVIDER_FAILED,
        reason,
        None,
    )
    assert L4A_UEN not in records(record) and L5_UEN not in records(record)
    assert {
        OwnershipIssueCode.CORPORATE_OWNERSHIP_UNRESOLVED,
        OwnershipIssueCode.INCOMPLETE_LEGAL_ENTITY,
    } <= codes(record)
    people = by_name(record)
    assert people["BEATRICE LIM (SYNTHETIC PERSON)"].synthetic_basis_threshold_result == (
        OwnershipThresholdResult.MET
    )
    # 20% plus an undisclosed 50% branch could still cross 25%: no NOT_MET is claimed.
    assert people["ALEX TAN (SYNTHETIC PERSON)"].synthetic_basis_threshold_result == (
        OwnershipThresholdResult.INDETERMINATE
    )
    assert record.discovery is not None and record.discovery.topology_complete is False


def test_mismatched_issuer_identity_fails_closed_without_overlay() -> None:
    transport = OfflineFiveLayerProtocolTransport()
    transport.profiles[L4A_UEN] = company_profile("200811111X", "OTHER UEN")
    onboarding, ownership, _ = build(transport)
    record = analyze(onboarding, ownership, FIVE_LAYER_ROOT_UEN)
    assert records(record)[L4A_UEN].outcome == OwnershipDiscoveryOutcome.PROVIDER_FAILED
    assert OwnershipIssueCode.CORPORATE_OWNERSHIP_UNRESOLVED in codes(record)


# --- 3. Garden: official root, direct-only overlay, official SIM LIM lookup ------------


def test_garden_hybrid_uses_direct_holders_only_and_looks_up_sim_lim_officially() -> None:
    onboarding, ownership, transport = build()
    record = analyze(onboarding, ownership, "11111999A")
    assert record.source_classification == "OFFICIAL_MOCK_PLUS_LOCAL_DIRECT_OVERLAY"
    direct = {
        next(
            p.display_name for p in record.parties if p.party_id == edge.child_party_id
        ): edge.ownership_percent
        for edge in record.relationships
    }
    assert direct == {"SIM LIM PTE. LTD.": Decimal("62.5"), "LIM CHOON HUAT": Decimal("37.5")}
    assert {edge.provenance.provider for edge in record.relationships} == {
        OVERLAY_RELATIONSHIP_PROVIDER
    }
    # No flattened 900/100/100 SIM LIM subtree under any label.
    assert {p.display_name for p in record.parties}.isdisjoint(
        {"ABCD123", "TAN WEI LING", "EFGH2345"}
    )
    assert transport.calls[("ENTITY_PROFILE", "111111111M")] == 1
    sim_lim = records(record)["111111111M"]
    assert (sim_lim.outcome, sim_lim.identity_basis) == (OwnershipDiscoveryOutcome.NOT_FOUND, None)
    assert {
        OwnershipIssueCode.CORPORATE_OWNERSHIP_UNRESOLVED,
        OwnershipIssueCode.SYNTHETIC_OWNERSHIP_EVIDENCE,
    } <= codes(record)
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    lim = by_name(record)["LIM CHOON HUAT"]
    assert (lim.classification, lim.synthetic_basis_threshold_result) == (
        OwnershipCandidateClassification.REVIEW_REQUIRED,
        OwnershipThresholdResult.MET,
    )
    assert record.discovery is not None
    assert record.discovery.overlay_scenario_id == GARDEN_DIRECT_OVERLAY_SCENARIO_ID


def sim_lim_unit_rows() -> dict[str, object]:
    def row(identifier: str, name: str, units: int, status: str) -> dict[str, object]:
        return {
            "shareholderCategory": "Individual",
            "shareholderId": identifier,
            "shareholderName": name,
            "shareAllotted": units,
            "shareType": "Ordinary",
            "currency": "SINGAPORE DOLLAR",
            "appointmentDate": "2020-01-01",
            "status": status,
        }

    return {
        "entities": [
            {
                "uen": "111111111M",
                "name": "SIM LIM PTE. LTD.",
                "shareholders": {
                    "individual": [
                        row("SYN-SL-1", "OFFICIAL HOLDER ONE (SYNTHETIC)", 600, "Active"),
                        row("SYN-SL-2", "OFFICIAL HOLDER TWO (SYNTHETIC)", 400, "Active"),
                        row("SYN-SL-3", "OFFICIAL HOLDER THREE (SYNTHETIC)", 100, "Withdrawn"),
                    ],
                    "grouping": [],
                },
            }
        ]
    }


@pytest.mark.parametrize("unit_rows", [False, True])
def test_an_officially_found_non_scenario_issuer_stays_unresolved(unit_rows: bool) -> None:
    # The Marketplace Mock lane has no relationships operation and no authoritative
    # denominator (Q-012), so an official SIM LIM profile, with or without unit-only
    # rows, never resolves the branch: no overlay, no local fixture, no inferred percent.
    transport = OfflineFiveLayerProtocolTransport()
    transport.profiles["111111111M"] = company_profile(
        "111111111M", "SIM LIM PTE. LTD.", "PRIVATE COMPANY LIMITED BY SHARES"
    )
    if unit_rows:
        transport.shareholders["111111111M"] = sim_lim_unit_rows()
    onboarding, ownership, _ = build(transport)
    record = analyze(onboarding, ownership, "11111999A")

    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    sim_lim = records(record)["111111111M"]
    assert (sim_lim.outcome, sim_lim.identity_basis, sim_lim.official_entity_lookup) == (
        OwnershipDiscoveryOutcome.PROVIDER_UNSUPPORTED,
        None,
        None,
    )
    assert sim_lim.max_effective_percent == Decimal("62.5")
    assert {edge.provenance.provider for edge in record.relationships} == {
        OVERLAY_RELATIONSHIP_PROVIDER
    }
    assert {party.display_name for party in record.parties} == {
        "GARDEN BUSINESS",
        "SIM LIM PTE. LTD.",
        "LIM CHOON HUAT",
    }
    assert record.discovery is not None
    assert (
        record.discovery.graph_complete,
        record.discovery.topology_complete,
        record.discovery.official_identity_complete,
        record.discovery.unresolved_upper_bound_percent,
    ) == (False, False, False, Decimal("62.5"))
    assert {
        OwnershipIssueCode.INCOMPLETE_LEGAL_ENTITY,
        OwnershipIssueCode.CORPORATE_OWNERSHIP_UNRESOLVED,
        OwnershipIssueCode.SYNTHETIC_OWNERSHIP_EVIDENCE,
    } <= codes(record)
    lim = by_name(record)["LIM CHOON HUAT"]
    assert (
        lim.aggregated_ownership_percent,
        lim.threshold_result,
        lim.classification,
        lim.synthetic_basis_threshold_result,
    ) == (
        Decimal("37.5"),
        OwnershipThresholdResult.INDETERMINATE,
        OwnershipCandidateClassification.REVIEW_REQUIRED,
        OwnershipThresholdResult.MET,
    )
    assert transport.calls[("SHAREHOLDERS", "111111111M")] == 1


def test_default_official_lane_keeps_the_accepted_flattened_garden_supplement() -> None:
    onboarding, ownership, transport = build(overlay="garden_legacy_supplement")
    record = analyze(onboarding, ownership, "11111999A")
    assert record.source_classification == "OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT"
    assert record.discovery is None
    assert by_name(record)["ABCD123"].aggregated_ownership_percent == Decimal("51.13636375")
    assert transport.calls[("ENTITY_PROFILE", "111111111M")] == 0
    five = analyze(onboarding, ownership, FIVE_LAYER_ROOT_UEN)
    assert (five.source_classification, five.relationships) == ("SINGLE_SOURCE", [])


# --- 4. Root eligibility, depth, cycles and persistence -------------------------------


def test_root_overlay_requires_fresh_successful_official_evidence() -> None:
    onboarding, ownership, _ = build()
    case = onboarding.create_staged_case(FIVE_LAYER_ROOT_UEN)
    now = datetime.now(UTC)
    assert official_marketplace_root_is_eligible(case, FIVE_LAYER_ROOT_UEN, now)
    assert not official_marketplace_root_is_eligible(case, L2_UEN, now)
    assert not official_marketplace_root_is_eligible(
        case, FIVE_LAYER_ROOT_UEN, now + timedelta(days=91)
    )
    assert HybridOwnershipOverlayCatalogue().root_scenario(case, now + timedelta(days=91)) is None
    garden_case = onboarding.create_staged_case("11111999A")
    assert (
        HybridOwnershipOverlayCatalogue().root_scenario(garden_case, datetime.now(UTC)) is not None
    )


def _chain(depth: int, uens: list[str]) -> HybridOverlayScenario:
    issuers = []
    for index in range(depth):
        holder = (
            OverlayHolder(
                holder_id=uens[index + 1],
                holder_name=f"C{index + 1} (SYNTHETIC)",
                category="Corporate",
                registration_number=uens[index + 1],
                share_units=Decimal("1"),
            )
            if index + 1 < depth
            else OverlayHolder(
                holder_id="SYN-END",
                holder_name="END (SYNTHETIC PERSON)",
                category="Individual",
                share_units=Decimal("1"),
            )
        )
        issuers.append(
            OverlayIssuer(
                issuer_uen=uens[index],
                local_display_name=f"C{index} (SYNTHETIC)",
                declared_active_units=Decimal("1"),
                holders=(holder,),
            )
        )
    return HybridOverlayScenario(scenario_id="TEST_CHAIN", root_uen=uens[0], issuers=tuple(issuers))


def test_a_depth_six_corporate_issuer_stays_unresolved_under_depth_five() -> None:
    uens = [f"30000000{index}A" for index in range(8)]
    transport = OfflineFiveLayerProtocolTransport(allowlist=frozenset(uens))
    transport.profiles = {uen: None for uen in uens}
    transport.profiles[uens[0]] = company_profile(uens[0], "CHAIN ROOT (SYNTHETIC)")
    onboarding, _, _ = build(transport)
    ownership = custom_service(onboarding, (_chain(8, uens),))
    record = analyze(onboarding, ownership, uens[0])
    found = records(record)
    assert {uen: (item.depth, item.outcome) for uen, item in found.items()}[uens[6]] == (
        6,
        OwnershipDiscoveryOutcome.DEPTH_LIMIT,
    )
    assert all(
        found[uens[level]].outcome == OwnershipDiscoveryOutcome.LOCAL_SYNTHETIC_OVERLAY
        for level in range(1, 6)
    )
    assert transport.calls[("ENTITY_PROFILE", uens[6])] == 0
    assert OwnershipIssueCode.CORPORATE_OWNERSHIP_UNRESOLVED in codes(record)
    assert record.candidates == []


def test_a_declared_cycle_is_review_with_no_synthetic_threshold_claim() -> None:
    uens = ["300000010A", "300000011A", "300000012A"]
    transport = OfflineFiveLayerProtocolTransport(allowlist=frozenset(uens))
    transport.profiles = {uen: None for uen in uens}
    transport.profiles[uens[0]] = company_profile(uens[0], "CYCLE ROOT (SYNTHETIC)")
    scenario = HybridOverlayScenario(
        scenario_id="TEST_CYCLE",
        root_uen=uens[0],
        issuers=(
            OverlayIssuer(
                issuer_uen=uens[0],
                local_display_name="R",
                declared_active_units=Decimal("2"),
                holders=(
                    OverlayHolder(
                        holder_id=uens[1],
                        holder_name="C1 (SYNTHETIC)",
                        category="Corporate",
                        registration_number=uens[1],
                        share_units=Decimal("1"),
                    ),
                    OverlayHolder(
                        holder_id="SYN-P",
                        holder_name="P (SYNTHETIC PERSON)",
                        category="Individual",
                        share_units=Decimal("1"),
                    ),
                ),
            ),
            OverlayIssuer(
                issuer_uen=uens[1],
                local_display_name="C1 (SYNTHETIC)",
                declared_active_units=Decimal("1"),
                holders=(
                    OverlayHolder(
                        holder_id=uens[0],
                        holder_name="R",
                        category="Corporate",
                        registration_number=uens[0],
                        share_units=Decimal("1"),
                    ),
                ),
            ),
        ),
    )
    onboarding, _, _ = build(transport)
    record = analyze(onboarding, custom_service(onboarding, (scenario,)), uens[0])
    assert OwnershipIssueCode.CYCLE_DETECTED in codes(record)
    assert {item.synthetic_basis_threshold_result for item in record.candidates} == {
        OwnershipThresholdResult.INDETERMINATE
    }


def test_hybrid_records_round_trip_in_schema_twelve_and_are_rejected_in_schema_eleven() -> None:
    onboarding, ownership, _ = build()
    record = analyze(onboarding, ownership, FIVE_LAYER_ROOT_UEN)
    case = onboarding.get_case(record.case_id)
    assert case is not None
    now = datetime.now(UTC)
    snapshot = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=0,
        onboarding=case,
        ownership=record,
        created_at=now,
        updated_at=now,
    )
    codec = object.__new__(MongoCaseStore)
    encoded = codec._encode(snapshot)  # noqa: SLF001
    decoded = codec._decode(encoded)  # noqa: SLF001
    assert decoded.schema_version == 13
    assert decoded.ownership is not None and decoded.ownership.discovery == record.discovery
    assert decoded.ownership.candidates == record.candidates
    # An exact schema-11 envelope can never carry hybrid evidence (fail closed)...
    with pytest.raises(PersistenceDataInvalidError):
        codec._decode({**encoded, "schema_version": 11})  # noqa: SLF001
    # ...while ordinary schema-11 content still reads into the current form.
    assert codec._decode({**encoded, "schema_version": 11, "ownership": None}).schema_version == 13  # noqa: SLF001


# --- 5. Domain invariants and the labelled comparator ----------------------------------


def test_overlay_records_and_audits_cannot_claim_more_than_the_evidence() -> None:
    base = {"party_id": "N1", "display_name": "N", "registration_number": L2_UEN, "depth": 1}
    with pytest.raises(ValidationError, match="explicit official lookup"):
        OwnershipDiscoveryRecord.model_validate({**base, "outcome": "LOCAL_SYNTHETIC_OVERLAY"})
    with pytest.raises(ValidationError, match="disagrees"):
        OwnershipDiscoveryRecord.model_validate(
            {
                **base,
                "outcome": "LOCAL_SYNTHETIC_OVERLAY",
                "identity_basis": "OFFICIAL_MOCK_ENTITY_PROFILE",
                "official_entity_lookup": "NOT_FOUND",
            }
        )
    overlay_record = OwnershipDiscoveryRecord.model_validate(
        {
            **base,
            "outcome": "LOCAL_SYNTHETIC_OVERLAY",
            "identity_basis": "LOCAL_SYNTHETIC_IDENTITY",
            "official_entity_lookup": "NOT_FOUND",
        }
    )
    audit = {
        "trace_threshold_percent": "10",
        "ubo_threshold_percent": "25",
        "max_corporate_depth": 5,
        "call_budget_enabled": False,
        "call_budget_max": 10,
        "graph_complete": False,
        "classification_certainty": "UNCERTAIN",
        "registry_lookups": 1,
        "provider_backed_lookups": 1,
        "cache_hits": 0,
        "records": [overlay_record],
    }
    with pytest.raises(ValidationError, match="only for hybrid"):
        OwnershipDiscoveryAudit.model_validate(audit)
    hybrid = {
        **audit,
        "overlay_scenario_id": FIVE_LAYER_SCENARIO_ID,
        "topology_complete": True,
        "official_identity_complete": False,
        "quantitative_evidence_complete": False,
    }
    assert OwnershipDiscoveryAudit.model_validate(hybrid).topology_complete is True
    for field_name, value in (
        ("quantitative_evidence_complete", True),
        ("official_identity_complete", True),
    ):
        with pytest.raises(ValidationError, match="disagrees"):
            OwnershipDiscoveryAudit.model_validate({**hybrid, field_name: value})


def test_a_synthetic_basis_comparison_requires_a_review_classification() -> None:
    onboarding, ownership, _ = build()
    candidate = analyze(onboarding, ownership, FIVE_LAYER_ROOT_UEN).candidates[0]
    with pytest.raises(ValidationError, match="review classification"):
        OwnershipCandidate.model_validate(
            {
                **candidate.model_dump(),
                "classification": OwnershipCandidateClassification.PROVISIONAL_UBO_CANDIDATE,
                "threshold_result": OwnershipThresholdResult.MET,
            }
        )


def test_the_labelled_comparator_only_claims_sound_outcomes() -> None:
    from app.domain.ownership import OwnershipAnalysisIssue

    aggregated = {
        "a": (Decimal("0"), Decimal("25"), Decimal("25")),
        "b": (Decimal("0"), Decimal("20"), Decimal("20")),
    }
    incomplete = [
        OwnershipAnalysisIssue(code=OwnershipIssueCode.INCOMPLETE_LEGAL_ENTITY, message="x")
    ]
    assert synthetic_basis_threshold_results(
        aggregated, [], threshold_percent=Decimal("25"), unresolved_upper_bound_percent=None
    ) == {"a": OwnershipThresholdResult.MET, "b": OwnershipThresholdResult.NOT_MET}
    assert (
        synthetic_basis_threshold_results(
            aggregated,
            incomplete,
            threshold_percent=Decimal("25"),
            unresolved_upper_bound_percent=Decimal("4.999999"),
        )["b"]
        == OwnershipThresholdResult.NOT_MET
    )
    assert (
        synthetic_basis_threshold_results(
            aggregated,
            incomplete,
            threshold_percent=Decimal("25"),
            unresolved_upper_bound_percent=Decimal("5"),
        )["b"]
        == OwnershipThresholdResult.INDETERMINATE
    )
    cycle = [OwnershipAnalysisIssue(code=OwnershipIssueCode.CYCLE_DETECTED, message="x")]
    assert set(
        synthetic_basis_threshold_results(
            aggregated, cycle, threshold_percent=Decimal("25"), unresolved_upper_bound_percent=None
        ).values()
    ) == {OwnershipThresholdResult.INDETERMINATE}


# --- 6. Cache namespace isolation, staleness and fail-closed acquisition --------------


def _key(uen: str, namespace: str) -> RegistryCacheKey:
    return RegistryCacheKey(
        provider_identity=RegistryProviderIdentity(
            provider=SourceSystem.ACRA,
            environment=SourceEnvironment.MOCK,
            acquisition_contract_version="PHASE10_ACQUISITION_V1",
            dataset_namespace=namespace,
        ),
        normalized_identifier=uen,
    )


def test_issuer_lookups_use_only_the_official_namespace_and_refetch_after_negative_ttl() -> None:
    repository = InMemoryRegistrySnapshotRepository()
    onboarding, ownership, transport = build(repository=repository)
    analyze(onboarding, ownership, FIVE_LAYER_ROOT_UEN)
    for uen in (FIVE_LAYER_ROOT_UEN, L2_UEN, L3_UEN, L4A_UEN, L4B_UEN, L5_UEN):
        assert repository.get(_key(uen, "ACRA_API_MARKETPLACE_MOCK_V1")) is not None
        assert repository.get(_key(uen, "MOCK_ACRA_SYNTHETIC_V2")) is None
    assert repository.get(_key(L5_UEN, "ACRA_API_MARKETPLACE_MOCK_V1")).negative_result == (
        "NOT_FOUND"
    )
    before = transport.get_count
    coordinator = onboarding._registry_acquisition_coordinator  # noqa: SLF001
    assert coordinator is not None
    # Past the 600 s definitive-negative TTL, issuers are re-read; the root's fresh
    # entity prefix (90-day policy) is still reused with zero GETs.
    coordinator._clock = lambda: datetime.now(UTC) + timedelta(seconds=601)  # noqa: SLF001
    stale = analyze(onboarding, ownership, FIVE_LAYER_ROOT_UEN)
    assert transport.get_count - before == 5
    assert stale.discovery is not None and stale.discovery.provider_backed_lookups == 5


class _CorruptIssuerCache(InMemoryRegistrySnapshotRepository):
    def get(self, key: RegistryCacheKey) -> Any:
        if key.normalized_identifier == L3_UEN:
            raise RegistrySnapshotRepositoryInvalidError
        return super().get(key)


def test_corrupt_issuer_cache_fails_closed_without_overlay() -> None:
    onboarding, ownership, transport = build(repository=_CorruptIssuerCache())
    record = analyze(onboarding, ownership, FIVE_LAYER_ROOT_UEN)
    l3 = records(record)[L3_UEN]
    assert (l3.outcome, l3.reason_code, l3.identity_basis) == (
        OwnershipDiscoveryOutcome.CACHE_FAILURE,
        "REGISTRY_CACHE_INVALID",
        None,
    )
    assert transport.calls[("ENTITY_PROFILE", L3_UEN)] == 0
    assert OwnershipIssueCode.CORPORATE_OWNERSHIP_UNRESOLVED in codes(record)


def test_token_rejection_never_reaches_the_overlay() -> None:
    onboarding, ownership, transport = build(OfflineFiveLayerProtocolTransport(token_status=401))
    with pytest.raises(OnboardingInfrastructureError) as raised:
        onboarding.create_staged_case(FIVE_LAYER_ROOT_UEN)
    assert transport.get_count == 0
    case = onboarding.get_case(raised.value.case_id)
    assert case is not None and case.registry_acquisition is None
    with pytest.raises((OwnershipInfrastructureError, OwnershipRequestError)):
        ownership.load(case_id=case.case_id)
    assert HybridOwnershipOverlayCatalogue().root_scenario(case, datetime.now(UTC)) is None
