"""D-079 official shareholder evidence for an empty-profile corporate holder; offline only.

SIM LIM (`111111111M`) is discovered from Garden's direct-holder overlay. Its official
Marketplace entity-basic profile is empty while its shareholder operation returns rows.
The rows are retained beside the graph without identity, legal form or percentages, and
the case stays under review. All rows below are synthetic.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from fractions import Fraction
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from s2_legacy_schema_fixtures import without_d101_fields
from scripts.five_layer_hybrid_fixture import FIVE_LAYER_FIELDS, OfflineFiveLayerProtocolTransport
from scripts.slice_b_registry_fixture import GARDEN_FIELDS
from test_five_layer_hybrid_journey import system
from test_hybrid_five_layer_overlay import (
    analyze,
    build,
    by_name,
    codes,
    company_profile,
    custom_service,
    records,
    settings,
)
from test_slice_b_registry_demo import start
from test_zero_touch_exception_remediation import successful

from app.composition import build_onboarding_service, build_ownership_analysis_service
from app.config import Settings
from app.connectors.acra_sandbox import AcraHttpResponse
from app.connectors.garden_business import SIM_LIM_MOCK_SHAREHOLDERS_BODY
from app.connectors.hybrid_ownership_overlay import (
    FIVE_LAYER_ROOT_UEN,
    L2_UEN,
    OVERLAY_RELATIONSHIP_PROVIDER,
    POC_EQUAL_UNITS_PROVIDER,
    HybridOverlayScenario,
    OverlayHolder,
    OverlayIssuer,
)
from app.domain.models import (
    LEGACY_SHAREHOLDER_EVIDENCE_CONTRACT_VERSION,
    SHAREHOLDER_EVIDENCE_CONTRACT_VERSION,
    RegistryCacheKey,
    RegistryEvidenceProvenance,
    RegistryFreshnessPolicy,
    RegistryOperation,
    RegistryOperationResult,
    RegistryOperationStatus,
    RegistryOwnershipParty,
    RegistryPartyType,
    RegistryProviderIdentity,
    RegistryShareholderEvidence,
    RegistrySnapshotEntry,
    SourceEnvironment,
    SourceSystem,
)
from app.domain.ownership import (
    OFFICIAL_SHAREHOLDERS_EMPTY,
    OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS,
    OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE,
    OfficialShareholderObservation,
    OwnershipAnalysisState,
    OwnershipCandidateClassification,
    OwnershipDiscoveryOutcome,
    OwnershipDiscoveryRecord,
    OwnershipEnvironment,
    OwnershipIssueCode,
    OwnershipThresholdResult,
    PartyType,
)
from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.models import DurableCaseSnapshot
from app.persistence.mongo_case_store import _SUPPORTED_SCHEMA_VERSIONS, MongoCaseStore
from app.persistence.mongo_registry_cache_store import MongoRegistryCacheStore
from app.services import ownership_discovery
from app.services.ownership_analysis import OwnershipGraphError
from app.services.ownership_discovery import _DiscoveryRun
from app.services.ownership_errors import OwnershipRequestError
from app.services.ownership_repository import InMemoryOwnershipAnalysisRepository
from app.services.registry_acquisition import (
    RegistryAcquisitionBusyError,
    RegistryAcquisitionCoordinator,
    RegistryCacheInvalidError,
    RegistryCacheReadError,
)
from app.services.registry_cache_repository import InMemoryRegistrySnapshotRepository

SIM = "111111111M"
GARDEN = "11111999A"
SHAREHOLDERS_PATH = "/entityQuery/coShareholdersDetails"


# D-121: these tests pin the blocking review, the rollback mode.
pytestmark = pytest.mark.usefixtures("blocking_ubo_review")


def holder(identifier: str, name: str, category: str, units: int, status: str) -> dict:
    return {
        "shareholderCategory": category,
        "shareholderId": identifier,
        "shareholderName": name,
        "shareAllotted": units,
        "shareType": "Ordinary",
        "currency": "SINGAPORE DOLLAR",
        "appointmentDate": "2020-01-01",
        "status": status,
    }


ROWS = [
    holder("SYN-SL-C1", "SYNTHETIC CORPORATE HOLDER, INC.", "Corporate", 500, "Active"),
    holder("SYN-SL-1", "SYNTHETIC HOLDER ONE", "Individual", 300, "Active"),
    holder("SYN-SL-2", "SYNTHETIC HOLDER TWO", "Individual", 200, "Active"),
    holder("SYN-SL-3", "SYNTHETIC HOLDER THREE", "Individual", 100, "Withdrawn"),
]


def shareholders(rows: list[dict] = ROWS, *, uen: str = SIM, grouping: list | None = None) -> dict:
    return {
        "entities": [
            {
                "uen": uen,
                "name": "SIM LIM PTE. LTD.",
                "shareholders": {"individual": rows, "grouping": grouping or []},
            }
        ]
    }


@dataclass
class ShareholderFaultTransport(OfflineFiveLayerProtocolTransport):
    """The offline transport with a fault on SIM LIM's shareholder read alone."""

    shareholder_fault: int | Exception | None = None

    def get(self, url: str, *, headers, timeout_seconds: float) -> AcraHttpResponse:
        parsed = urlsplit(url)
        uen = parse_qs(parsed.query).get("uen", [""])[0]
        if self.shareholder_fault is not None and parsed.path.endswith(SHAREHOLDERS_PATH):
            self.calls[("SHAREHOLDERS", uen)] += 1
            if isinstance(self.shareholder_fault, Exception):
                raise self.shareholder_fault
            return AcraHttpResponse(self.shareholder_fault, {}, "application/json", 2)
        return super().get(url, headers=headers, timeout_seconds=timeout_seconds)


def sim_lim(record) -> OwnershipDiscoveryRecord:
    return records(record)[SIM]


def test_empty_profile_corporate_holder_rows_are_retained_and_poc_distributed() -> None:
    transport = OfflineFiveLayerProtocolTransport()
    transport.shareholders[SIM] = shareholders()
    onboarding, ownership, _ = build(transport)
    record = analyze(onboarding, ownership, GARDEN)

    sim = sim_lim(record)
    assert (sim.outcome, sim.reason_code, sim.official_shareholder_lookup) == (
        OwnershipDiscoveryOutcome.PROVIDER_PARTIAL,
        OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS,
        "SHAREHOLDERS_FETCHED",
    )
    # No identity, legal form or overlay basis is manufactured for SIM LIM.
    assert (sim.identity_basis, sim.official_entity_lookup, sim.official_legal_form) == (
        None,
        None,
        None,
    )
    # D-079/D-080: every official row is retained unchanged, withdrawn included.
    rows = {item.source_party_id: item for item in sim.official_shareholders}
    assert set(rows) == {"SYN-SL-C1", "SYN-SL-1", "SYN-SL-2", "SYN-SL-3"}
    assert {
        key: (item.display_name, item.party_type, item.share_allotted, item.current_interest)
        for key, item in rows.items()
    } == {
        "SYN-SL-C1": (
            "SYNTHETIC CORPORATE HOLDER, INC.",
            PartyType.LEGAL_ENTITY,
            Decimal("500"),
            True,
        ),
        "SYN-SL-1": ("SYNTHETIC HOLDER ONE", PartyType.NATURAL_PERSON, Decimal("300"), True),
        "SYN-SL-2": ("SYNTHETIC HOLDER TWO", PartyType.NATURAL_PERSON, Decimal("200"), True),
        "SYN-SL-3": ("SYNTHETIC HOLDER THREE", PartyType.NATURAL_PERSON, Decimal("100"), False),
    }
    assert {(item.share_type, item.currency) for item in rows.values()} == {
        ("Ordinary", "SINGAPORE DOLLAR")
    }
    assert {
        (item.provider, item.environment, item.dataset_namespace, item.source_operation)
        for item in rows.values()
    } == {
        ("ACRA_REGISTRY_ACQUISITION", "MOCK", "ACRA_API_MARKETPLACE_MOCK_V1", "OWNERSHIP_PARTIES")
    }
    # D-081: SIM LIM's own current units (500 + 300 + 200) form its POC 100%; the
    # withdrawn row is never a link. Garden's two links stay local synthetic.
    names = {party.party_id: party.display_name for party in record.parties}
    links = {
        names[edge.child_party_id]: (edge.ownership_percent, edge.provenance.provider)
        for edge in record.relationships
    }
    assert links == {
        "SIM LIM PTE. LTD.": (Decimal("62.5"), OVERLAY_RELATIONSHIP_PROVIDER),
        "LIM CHOON HUAT": (Decimal("37.5"), OVERLAY_RELATIONSHIP_PROVIDER),
        "SYNTHETIC CORPORATE HOLDER, INC.": (Decimal("50"), POC_EQUAL_UNITS_PROVIDER),
        "SYNTHETIC HOLDER ONE": (Decimal("30"), POC_EQUAL_UNITS_PROVIDER),
        "SYNTHETIC HOLDER TWO": (Decimal("20"), POC_EQUAL_UNITS_PROVIDER),
    }
    assert {
        edge.provenance.environment
        for edge in record.relationships
        if edge.provenance.provider == POC_EQUAL_UNITS_PROVIDER
    } == {OwnershipEnvironment.LOCAL}
    # The corporate holder has no supplied registration identifier: it is never
    # recursed into and stays an unresolved, unverified corporate branch.
    assert rows["SYN-SL-C1"].registration_identifier is None
    corporate = next(item for item in records(record).values() if item.party_id != sim.party_id)
    assert (corporate.display_name, corporate.outcome, corporate.registration_number) == (
        "SYNTHETIC CORPORATE HOLDER, INC.",
        OwnershipDiscoveryOutcome.UNVERIFIED_UEN,
        None,
    )
    assert record.discovery is not None
    assert record.discovery.unresolved_upper_bound_percent == Decimal("31.25")
    assert (
        record.discovery.topology_complete,
        record.discovery.graph_complete,
        record.discovery.quantitative_evidence_complete,
    ) == (False, False, False)
    issue = next(
        item
        for item in record.issues
        if item.code == OwnershipIssueCode.OWNERSHIP_DENOMINATOR_REQUIRED
    )
    assert issue.affected_party_ids == [sim.party_id]
    assert issue.message == (
        "4 official Marketplace Mock shareholder row(s) are retained without an entity "
        "profile; percentages shown assume equal POC units, not an ACRA denominator."
    )
    assert {
        OwnershipIssueCode.INCOMPLETE_LEGAL_ENTITY,
        OwnershipIssueCode.CORPORATE_OWNERSHIP_UNRESOLVED,
        OwnershipIssueCode.SYNTHETIC_OWNERSHIP_EVIDENCE,
        OwnershipIssueCode.UBO_REVIEW_REQUIRED,
    } < codes(record)
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    candidates = by_name(record)
    assert {
        name: (
            item.aggregated_ownership_percent,
            item.classification,
            item.synthetic_basis_threshold_result,
        )
        for name, item in candidates.items()
    } == {
        "LIM CHOON HUAT": (
            Decimal("37.5"),
            OwnershipCandidateClassification.REVIEW_REQUIRED,
            OwnershipThresholdResult.MET,
        ),
        "SYNTHETIC HOLDER ONE": (
            Decimal("18.75"),
            OwnershipCandidateClassification.REVIEW_REQUIRED,
            OwnershipThresholdResult.INDETERMINATE,
        ),
        "SYNTHETIC HOLDER TWO": (
            Decimal("12.5"),
            OwnershipCandidateClassification.REVIEW_REQUIRED,
            OwnershipThresholdResult.INDETERMINATE,
        ),
    }
    # A cache miss makes only the bounded official reads for SIM LIM.
    assert dict(transport.calls) == {
        ("ENTITY_PROFILE", GARDEN): 2,
        ("ENTITY_PROFILE", SIM): 1,
        ("SHAREHOLDERS", SIM): 1,
    }
    assert (record.discovery.registry_lookups, record.discovery.provider_backed_lookups) == (1, 1)


def test_repeat_onboarding_reuses_cached_shareholder_evidence_with_zero_calls() -> None:
    transport = OfflineFiveLayerProtocolTransport()
    transport.shareholders[SIM] = shareholders()
    onboarding, ownership, _ = build(transport)
    first = analyze(onboarding, ownership, GARDEN)
    calls = dict(transport.calls)
    second = analyze(onboarding, ownership, GARDEN)
    assert dict(transport.calls) == calls
    assert sim_lim(second).official_shareholder_lookup == "SHAREHOLDERS_CACHE_REUSED"
    assert sim_lim(second).official_shareholders == sim_lim(first).official_shareholders
    # The reused evidence yields the same POC links without any further request.
    assert sorted(
        edge.ownership_percent
        for edge in second.relationships
        if edge.provenance.provider == POC_EQUAL_UNITS_PROVIDER
    ) == [Decimal("20"), Decimal("30"), Decimal("50")]
    assert sim_lim(second).reason_code == OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS
    assert second.discovery is not None
    assert (second.discovery.provider_backed_lookups, second.discovery.cache_hits) == (0, 1)


def test_poc_records_exist_only_inside_a_hybrid_overlay_audit() -> None:
    transport = OfflineFiveLayerProtocolTransport()
    transport.shareholders[SIM] = shareholders()
    onboarding, ownership, _ = build(transport)
    record = analyze(onboarding, ownership, GARDEN)
    assert record.discovery is not None
    outside_hybrid = {
        **record.discovery.model_dump(),
        "overlay_scenario_id": None,
        "topology_complete": None,
        "official_identity_complete": None,
        "quantitative_evidence_complete": None,
    }
    with pytest.raises(ValidationError):
        type(record.discovery).model_validate(outside_hybrid)
    # The POC reason is valid only as a retained-rows partial outcome with positive
    # current units.
    sim = sim_lim(record)
    with pytest.raises(ValidationError):
        type(sim).model_validate(
            {**sim.model_dump(), "official_shareholders": (), "official_shareholder_lookup": None}
        )
    for outcome in (
        OwnershipDiscoveryOutcome.NOT_FOUND,
        OwnershipDiscoveryOutcome.PROVIDER_FAILED,
        OwnershipDiscoveryOutcome.UNVERIFIED_UEN,
    ):
        with pytest.raises(ValidationError):
            type(sim).model_validate(
                {
                    **sim.model_dump(),
                    "outcome": outcome,
                    "official_shareholders": (),
                    "official_shareholder_lookup": None,
                }
            )
    withdrawn = tuple(
        item.model_copy(update={"current_interest": False, "source_status": "Withdrawn"})
        for item in sim.official_shareholders
    )
    unitless = tuple(
        item.model_copy(update={"share_allotted": None}) if item.current_interest else item
        for item in sim.official_shareholders
    )
    for rows in (withdrawn, unitless):
        # Valid D-079 retained evidence, but no positive current units for the POC reason.
        type(sim).model_validate(
            {
                **sim.model_dump(),
                "reason_code": OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE,
                "official_shareholders": rows,
            }
        )
        with pytest.raises(ValidationError):
            type(sim).model_validate({**sim.model_dump(), "official_shareholders": rows})


@pytest.mark.parametrize(
    ("payload", "fault", "reason"),
    [
        (shareholders(grouping=[ROWS[0]]), None, "REGISTRY_OPERATION_MALFORMED_RESPONSE"),
        (
            {"entities": [{"uen": SIM, "name": "SIM"}]},
            None,
            "REGISTRY_OPERATION_MALFORMED_RESPONSE",
        ),
        (shareholders(uen="200811111M"), None, "REGISTRY_OPERATION_MALFORMED_RESPONSE"),
        (
            shareholders([{**ROWS[1], "shareAllotted": 1.5}]),
            None,
            "REGISTRY_OPERATION_MALFORMED_RESPONSE",
        ),
        # Malformed quantities: negative, non-numeric, boolean, beyond six decimals or
        # eighteen digits. Each is rejected; none is coerced, truncated or retained.
        *(
            (
                shareholders([{**ROWS[1], "shareAllotted": units}]),
                None,
                "REGISTRY_OPERATION_MALFORMED_RESPONSE",
            )
            for units in (-1, "300 units", True, "300.0000001", 10**18)
        ),
        (None, httpx.ReadTimeout("synthetic"), "REGISTRY_OPERATION_TIMEOUT"),
        (None, 401, "REGISTRY_OPERATION_UNAVAILABLE"),
        (None, 403, "REGISTRY_OPERATION_UNAVAILABLE"),
        (None, 500, "REGISTRY_OPERATION_UNAVAILABLE"),
    ],
)
def test_shareholder_read_failures_stop_safely_and_are_never_cached(
    payload: dict | None, fault: int | Exception | None, reason: str
) -> None:
    transport = ShareholderFaultTransport(shareholder_fault=fault)
    if payload is not None:
        transport.shareholders[SIM] = payload
    onboarding, ownership, _ = build(transport)
    record = analyze(onboarding, ownership, GARDEN)
    sim = sim_lim(record)
    assert (sim.outcome, sim.reason_code) == (OwnershipDiscoveryOutcome.PROVIDER_FAILED, reason)
    assert (sim.official_shareholders, sim.official_shareholder_lookup) == ((), None)
    assert OwnershipIssueCode.OWNERSHIP_DENOMINATOR_REQUIRED not in codes(record)
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert record.discovery is not None
    assert record.discovery.unresolved_upper_bound_percent == Decimal("62.5")
    # Failures are not cached: the next run reads the shareholder operation again.
    analyze(onboarding, ownership, GARDEN)
    assert transport.calls[("SHAREHOLDERS", SIM)] == 2


def test_empty_official_shareholders_keep_not_found_and_are_cached() -> None:
    transport = OfflineFiveLayerProtocolTransport()  # SIM LIM shareholders default to empty
    onboarding, ownership, _ = build(transport)
    record = analyze(onboarding, ownership, GARDEN)
    sim = sim_lim(record)
    assert (sim.outcome, sim.reason_code, sim.official_shareholders) == (
        OwnershipDiscoveryOutcome.NOT_FOUND,
        OFFICIAL_SHAREHOLDERS_EMPTY,
        (),
    )
    assert OwnershipIssueCode.OWNERSHIP_DENOMINATOR_REQUIRED not in codes(record)
    analyze(onboarding, ownership, GARDEN)
    assert transport.calls[("SHAREHOLDERS", SIM)] == 1


class PreD079Onboarding:
    """The onboarding service as discovery saw it before D-079: no shareholder read."""

    def __init__(self, onboarding: object) -> None:
        self._onboarding = onboarding

    def __getattr__(self, name: str) -> object:
        if name == "acquire_subsidiary_shareholder_evidence":
            raise AttributeError(name)
        return getattr(self._onboarding, name)


def test_a_case_analysed_before_d079_is_kept_and_only_a_fresh_case_retains_rows() -> None:
    transport = OfflineFiveLayerProtocolTransport()
    transport.shareholders[SIM] = shareholders()
    onboarding, _, _ = build(transport)
    stored = InMemoryOwnershipAnalysisRepository()
    legacy = build_ownership_analysis_service(
        PreD079Onboarding(onboarding),  # type: ignore[arg-type]
        settings(),
        repository=stored,
    )
    old = analyze(onboarding, legacy, GARDEN)
    assert (sim_lim(old).outcome, sim_lim(old).reason_code, sim_lim(old).official_shareholders) == (
        OwnershipDiscoveryOutcome.NOT_FOUND,
        None,
        (),
    )
    assert OwnershipIssueCode.OWNERSHIP_DENOMINATOR_REQUIRED not in codes(old)
    assert transport.calls[("SHAREHOLDERS", SIM)] == 0
    calls = dict(transport.calls)

    # The current service shares the stored analyses and never re-analyses that case:
    # the same three graph parties, no shareholder read, no rewrite.
    current = build_ownership_analysis_service(onboarding, settings(), repository=stored)
    assert current.get(case_id=old.case_id) == old
    assert current.analyze(case_id=old.case_id) == old
    with pytest.raises(OwnershipRequestError) as refused:
        current.load(case_id=old.case_id)
    assert refused.value.code == "OWNERSHIP_ALREADY_LOADED"
    assert dict(transport.calls) == calls

    # A fresh case for the same root reuses the negative entity-profile cache, misses the
    # shareholder cache and makes exactly one shareholder read.
    fresh = analyze(onboarding, current, GARDEN)
    # The old case keeps its three parties; only the fresh case gains SIM LIM's holders.
    assert {party.display_name for party in old.parties} == {
        "GARDEN BUSINESS",
        "SIM LIM PTE. LTD.",
        "LIM CHOON HUAT",
    }
    assert {party.display_name for party in fresh.parties} > {
        party.display_name for party in old.parties
    }
    assert (
        sim_lim(fresh).outcome,
        sim_lim(fresh).reason_code,
        sim_lim(fresh).official_shareholder_lookup,
    ) == (
        OwnershipDiscoveryOutcome.PROVIDER_PARTIAL,
        OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS,
        "SHAREHOLDERS_FETCHED",
    )
    assert len(sim_lim(fresh).official_shareholders) == len(ROWS)
    assert OwnershipIssueCode.OWNERSHIP_DENOMINATOR_REQUIRED in codes(fresh)
    assert transport.calls[("ENTITY_PROFILE", SIM)] == calls[("ENTITY_PROFILE", SIM)]
    assert transport.calls[("SHAREHOLDERS", SIM)] == 1
    assert current.get(case_id=old.case_id) == old


def test_garden_sim_lim_live_shape_distributes_current_units_as_poc_equal_units() -> None:
    # The class/unit shape observed in the bounded live Mock read of 2026-10-24 (D-080),
    # with synthetic identifiers: one withdrawn corporate row and three active classes.
    live_shape = [
        holder("SYN-FGH", "FGH SERVICES, INC.", "Corporate", 10000, "Withdrawn"),
        holder("SYN-ABCD", "ABCD123", "Individual", 900, "Active"),
        {
            **holder("SYN-TWL", "TAN WEI LING", "Individual", 100, "Active"),
            "shareType": "Preference",
        },
        {**holder("SYN-EFGH", "EFGH2345", "Individual", 100, "Active"), "shareType": "Others"},
    ]
    transport = OfflineFiveLayerProtocolTransport()
    transport.shareholders[SIM] = shareholders(live_shape)
    onboarding, ownership, _ = build(transport)
    record = analyze(onboarding, ownership, GARDEN)
    sim = sim_lim(record)
    # The official rows keep their true classes, units and status (D-079/D-080).
    assert {
        item.display_name: (item.share_type, item.share_allotted, item.current_interest)
        for item in sim.official_shareholders
    } == {
        "FGH SERVICES, INC.": ("Ordinary", Decimal("10000"), False),
        "ABCD123": ("Ordinary", Decimal("900"), True),
        "TAN WEI LING": ("Preference", Decimal("100"), True),
        "EFGH2345": ("Others", Decimal("100"), True),
    }
    assert (sim.outcome, sim.reason_code) == (
        OwnershipDiscoveryOutcome.PROVIDER_PARTIAL,
        OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS,
    )
    # D-081: SIM LIM's own current units, pooled as equal POC units: 900 + 100 + 100.
    current = {
        item.display_name: Fraction(item.share_allotted or 0)
        for item in sim.official_shareholders
        if item.current_interest
    }
    names = {party.party_id: party.display_name for party in record.parties}
    poc_links = {
        names[edge.child_party_id]: edge.ownership_percent
        for edge in record.relationships
        if edge.provenance.provider == POC_EQUAL_UNITS_PROVIDER
    }
    assert poc_links == {
        "ABCD123": Decimal("81.818182"),
        "TAN WEI LING": Decimal("9.090909"),
        "EFGH2345": Decimal("9.090909"),
    }
    # Each link is its holder's exact unit share rounded to six decimals.
    for name, link in poc_links.items():
        assert link.as_tuple().exponent == -6
        exact = current[name] * 100 / sum(current.values())
        assert abs(Fraction(link) - exact) <= Fraction(1, 2_000_000)
    assert sum(poc_links.values()) == Decimal("100")
    assert "FGH SERVICES, INC." not in names.values()
    # The existing engine multiplies through Garden's 62.5% link.
    assert {
        name: (
            item.aggregated_ownership_percent,
            item.classification,
            item.threshold_result,
            item.synthetic_basis_threshold_result,
        )
        for name, item in by_name(record).items()
    } == {
        "ABCD123": (
            Decimal("51.13636375"),
            OwnershipCandidateClassification.REVIEW_REQUIRED,
            OwnershipThresholdResult.INDETERMINATE,
            OwnershipThresholdResult.MET,
        ),
        "LIM CHOON HUAT": (
            Decimal("37.5"),
            OwnershipCandidateClassification.REVIEW_REQUIRED,
            OwnershipThresholdResult.INDETERMINATE,
            OwnershipThresholdResult.MET,
        ),
        "TAN WEI LING": (
            Decimal("5.681818125"),
            OwnershipCandidateClassification.REVIEW_REQUIRED,
            OwnershipThresholdResult.INDETERMINATE,
            OwnershipThresholdResult.NOT_MET,
        ),
        "EFGH2345": (
            Decimal("5.681818125"),
            OwnershipCandidateClassification.REVIEW_REQUIRED,
            OwnershipThresholdResult.INDETERMINATE,
            OwnershipThresholdResult.NOT_MET,
        ),
    }
    [issue] = [
        item
        for item in record.issues
        if item.code == OwnershipIssueCode.OWNERSHIP_DENOMINATOR_REQUIRED
    ]
    assert issue.message == (
        "4 official Marketplace Mock shareholder row(s) are retained without an entity "
        "profile; current rows mix share classes; percentages shown assume equal POC units, "
        "not an ACRA denominator."
    )
    assert OwnershipIssueCode.CORPORATE_OWNERSHIP_UNRESOLVED not in codes(record)
    assert record.discovery is not None
    assert (
        record.discovery.topology_complete,
        record.discovery.graph_complete,
        record.discovery.official_identity_complete,
        record.discovery.quantitative_evidence_complete,
        record.discovery.unresolved_upper_bound_percent,
        record.discovery.classification_certainty,
    ) == (True, False, False, False, Decimal("0"), "UNCERTAIN")
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert transport.calls[("SHAREHOLDERS", SIM)] == 1


def test_only_current_rows_decide_whether_share_classes_are_mixed() -> None:
    rows = [
        {
            **holder("SYN-CW-1", "SYNTHETIC WITHDRAWN", "Individual", 50, "Withdrawn"),
            "shareType": "Preference",
        },
        holder("SYN-CW-2", "SYNTHETIC CURRENT ONE", "Individual", 30, "Active"),
        holder("SYN-CW-3", "SYNTHETIC CURRENT TWO", "Individual", 20, "Active"),
    ]
    transport = OfflineFiveLayerProtocolTransport()
    transport.shareholders[SIM] = shareholders(rows)
    onboarding, ownership, _ = build(transport)
    record = analyze(onboarding, ownership, GARDEN)
    assert [item.share_type for item in sim_lim(record).official_shareholders] == [
        "Preference",
        "Ordinary",
        "Ordinary",
    ]
    [issue] = [
        item
        for item in record.issues
        if item.code == OwnershipIssueCode.OWNERSHIP_DENOMINATOR_REQUIRED
    ]
    # The withdrawn Preference row is history, so the current rows are one class and
    # only they form SIM LIM's POC denominator (30 + 20).
    assert issue.message == (
        "3 official Marketplace Mock shareholder row(s) are retained without an entity "
        "profile; percentages shown assume equal POC units, not an ACRA denominator."
    )
    names = {party.party_id: party.display_name for party in record.parties}
    assert {
        names[edge.child_party_id]: edge.ownership_percent
        for edge in record.relationships
        if edge.provenance.provider == POC_EQUAL_UNITS_PROVIDER
    } == {"SYNTHETIC CURRENT ONE": Decimal("60"), "SYNTHETIC CURRENT TWO": Decimal("40")}


def test_ordinary_acquisitions_keep_the_untrusted_share_class() -> None:
    # D-112 (owner O2) narrows D-080: a COMPANY-form issuer's ordinary acquisition keeps
    # the untrusted class and currency, so mixed classes are detected and never combined.
    transport = OfflineFiveLayerProtocolTransport()
    transport.profiles[L2_UEN] = company_profile(
        L2_UEN, "OFFICIAL SYNTHETIC L2 PTE. LTD.", "PRIVATE COMPANY LIMITED BY SHARES"
    )
    transport.shareholders[L2_UEN] = shareholders(
        [
            {
                **holder("SYN-L2-1", "SYNTHETIC L2 HOLDER", "Individual", 10, "Active"),
                "shareType": "Preference",
            }
        ],
        uen=L2_UEN,
    )
    onboarding, _, _ = build(transport)
    evidence = onboarding.acquire_subsidiary_registry_evidence(
        L2_UEN, case_policy=None, policy_version=0
    )
    bundle = evidence.acquisition
    assert transport.calls[("SHAREHOLDERS", L2_UEN)] == 1
    assert bundle is not None
    assert [
        (item.share_allotted, item.share_type, item.currency) for item in bundle.ownership_parties
    ] == [(Decimal("10"), "Preference", "SINGAPORE DOLLAR")]
    # The retained label round-trips through validation (stored and cached bundles).
    assert type(bundle).model_validate(bundle.model_dump()) == bundle


def test_rows_named_like_the_local_fixture_keep_the_mock_values_and_provenance() -> None:
    # The official Mock's SIM LIM sample names three individuals the same way as the
    # local synthetic SIM LIM fixture. Only the Marketplace response may be retained.
    local = {
        row["shareholderName"]: row
        for row in SIM_LIM_MOCK_SHAREHOLDERS_BODY["entities"][0]["shareholders"]["individual"]
    }
    official = [
        holder("SYN-OFF-C", "SYNTHETIC OFFICIAL CORPORATE, INC.", "Corporate", 7, "Withdrawn"),
        *(
            holder(f"SYN-OFF-{index}", name, "Individual", units, "Active")
            for index, (name, units) in enumerate(
                (("ABCD123", 11), ("TAN WEI LING", 13), ("EFGH2345", 17)), start=1
            )
        ),
    ]
    assert {row["shareholderName"] for row in official[1:]} < set(local)
    transport = OfflineFiveLayerProtocolTransport()
    transport.shareholders[SIM] = shareholders(official)
    onboarding, ownership, _ = build(transport)
    record = analyze(onboarding, ownership, GARDEN)
    retained = {
        item.display_name: (item.source_party_id, item.share_allotted, item.current_interest)
        for item in sim_lim(record).official_shareholders
    }
    assert retained == {
        "SYNTHETIC OFFICIAL CORPORATE, INC.": ("SYN-OFF-C", Decimal("7"), False),
        "ABCD123": ("SYN-OFF-1", Decimal("11"), True),
        "TAN WEI LING": ("SYN-OFF-2", Decimal("13"), True),
        "EFGH2345": ("SYN-OFF-3", Decimal("17"), True),
    }
    assert {item.dataset_namespace for item in sim_lim(record).official_shareholders} == {
        "ACRA_API_MARKETPLACE_MOCK_V1"
    }
    # The POC links follow the Mock's own units (11 + 13 + 17), never the local fixture's
    # identifiers or its 900/100/100 basis.
    dumped = record.model_dump_json()
    for row in local.values():
        assert row["shareholderId"] not in dumped
    assert "81.818182" not in dumped and "9.090909" not in dumped
    names = {party.party_id: party.display_name for party in record.parties}
    assert {
        names[edge.child_party_id]: (edge.ownership_percent, edge.provenance.provider)
        for edge in record.relationships
        if names[edge.parent_party_id] == "SIM LIM PTE. LTD."
    } == {
        "ABCD123": (Decimal("26.829268"), POC_EQUAL_UNITS_PROVIDER),
        "TAN WEI LING": (Decimal("31.707317"), POC_EQUAL_UNITS_PROVIDER),
        "EFGH2345": (Decimal("41.463415"), POC_EQUAL_UNITS_PROVIDER),
    }


def test_only_the_official_marketplace_lane_reads_shareholders_alone() -> None:
    # The local synthetic composition never answers (no call, legacy NOT_FOUND meaning).
    local = build_onboarding_service(settings=Settings(_env_file=None, app_env="test"))
    assert (
        local.acquire_subsidiary_shareholder_evidence(SIM, case_policy=None, policy_version=0)
        is None
    )
    # The default flattened Garden supplement never enters discovery or this read.
    legacy = OfflineFiveLayerProtocolTransport()
    legacy.shareholders[SIM] = shareholders()
    onboarding, ownership, _ = build(legacy, overlay="garden_legacy_supplement")
    analyze(onboarding, ownership, GARDEN)
    assert legacy.calls[("SHAREHOLDERS", SIM)] == 0
    # OPQ's scenario-overlay issuers keep D-077 behaviour: no shareholder reads.
    five = OfflineFiveLayerProtocolTransport()
    onboarding, ownership, _ = build(five)
    analyze(onboarding, ownership, FIVE_LAYER_ROOT_UEN)
    assert not any(operation == "SHAREHOLDERS" for operation, _ in five.calls)


def test_api_projects_retained_rows_and_keeps_readiness_blocked() -> None:
    client, transport = system()
    transport.shareholders[SIM] = shareholders()
    current = start(client, GARDEN_FIELDS, "garden-partnership-reviewed-client.pdf")
    case_id = current["case"]["case_id"]
    assert (current["status"], current["current_stage"]) == ("WAITING_FOR_REVIEW", "OWNERSHIP")
    ownership = successful(client.get(f"/api/onboarding/cases/{case_id}/ownership"))
    [sim] = [
        item for item in ownership["discovery"]["records"] if item["registration_number"] == SIM
    ]
    assert (sim["outcome"], sim["reason_code"], sim["official_shareholder_lookup"]) == (
        "PROVIDER_PARTIAL",
        OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS,
        "SHAREHOLDERS_FETCHED",
    )
    # The POC links reach the existing API graph with their own provenance label.
    assert sorted(
        (edge["ownership_percent"], edge["provenance"]["environment"])
        for edge in ownership["relationships"]
        if edge["provenance"]["provider"] == POC_EQUAL_UNITS_PROVIDER
    ) == [("20.000000", "LOCAL"), ("30.000000", "LOCAL"), ("50.000000", "LOCAL")]
    assert [item["display_name"] for item in sim["official_shareholders"]] == [
        row["shareholderName"] for row in ROWS
    ]
    assert all("ownership_percent" not in item for item in sim["official_shareholders"])
    assert "OWNERSHIP_DENOMINATOR_REQUIRED" in {item["code"] for item in ownership["issues"]}
    summary = successful(client.get(f"/api/clm/zero-touch/cases/{case_id}"))
    assert "OWNERSHIP_REVIEW_REQUIRED" in summary["clm"]["readiness"]["blockers"]
    assert summary["case"].get("goldtier_result") is None
    assert summary["clm"]["submission"] is None
    # The five-layer journey is unaffected by the new read.
    five = start(client, FIVE_LAYER_FIELDS, "five-layer-marketplace-hybrid-client.pdf")
    assert five["status"] == "WAITING_FOR_REVIEW"
    assert transport.metadata()["external_calls"] == 0


def observation(**update) -> OfficialShareholderObservation:
    values = {
        "source_party_id": "SYN-SL-1",
        "display_name": "SYNTHETIC HOLDER ONE",
        "party_type": PartyType.NATURAL_PERSON,
        "source_category": "Individual",
        "source_status": "Active",
        "share_allotted": Decimal("300"),
        "current_interest": True,
        "retrieved_at": datetime(2026, 10, 24, tzinfo=UTC),
        "evidence_reference": "ACRA_OWNERSHIP_PARTIES_111111111M",
    }
    return OfficialShareholderObservation.model_validate({**values, **update})


def test_observation_and_record_validators_fail_closed() -> None:
    assert observation(source_status="Withdrawn", current_interest=False).current_interest is False
    for invalid in (
        {"source_status": "Withdrawn"},  # a withdrawn row can never be current
        {"source_status": None},  # an unknown status is not current either
        {"share_allotted": 1.5},  # inexact units
        {"retrieved_at": datetime(2026, 10, 24)},  # naive time
        {"dataset_namespace": "MOCK_ACRA_SYNTHETIC_V2"},  # only the official namespace
    ):
        with pytest.raises(ValidationError):
            observation(**invalid)
    base = {
        "party_id": "111111111M",
        "display_name": "SIM LIM PTE. LTD.",
        "registration_number": SIM,
        "depth": 1,
    }
    retained = {
        **base,
        "outcome": OwnershipDiscoveryOutcome.PROVIDER_PARTIAL,
        "reason_code": OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE,
        "official_shareholders": (observation(),),
        "official_shareholder_lookup": "SHAREHOLDERS_FETCHED",
    }
    assert OwnershipDiscoveryRecord.model_validate(retained).official_shareholders
    for invalid in (
        {**retained, "official_shareholder_lookup": None},
        {**retained, "official_shareholders": ()},
        {**retained, "reason_code": None},
        {**retained, "outcome": OwnershipDiscoveryOutcome.NOT_FOUND},
        {**retained, "official_shareholders": (observation(), observation())},
        {
            **base,
            "outcome": OwnershipDiscoveryOutcome.FETCHED,
            "official_shareholders": (observation(),),
            "official_shareholder_lookup": "SHAREHOLDERS_FETCHED",
        },
        {
            **base,
            "outcome": OwnershipDiscoveryOutcome.PROVIDER_PARTIAL,
            "reason_code": OFFICIAL_SHAREHOLDERS_EMPTY,
        },
    ):
        with pytest.raises(ValidationError):
            OwnershipDiscoveryRecord.model_validate(invalid)


MARKETPLACE = RegistryProviderIdentity(
    provider=SourceSystem.ACRA,
    environment=SourceEnvironment.MOCK,
    acquisition_contract_version="PHASE10_ACQUISITION_V1",
    dataset_namespace="ACRA_API_MARKETPLACE_MOCK_V1",
)
SHAREHOLDER_KEY = RegistryCacheKey(
    provider_identity=MARKETPLACE.model_copy(
        update={"acquisition_contract_version": SHAREHOLDER_EVIDENCE_CONTRACT_VERSION}
    ),
    normalized_identifier=SIM,
)


def evidence(
    status: RegistryOperationStatus, retrieved_at: datetime, *, share_class: bool = True
) -> RegistryShareholderEvidence:
    provenance = RegistryEvidenceProvenance(
        provider=SourceSystem.ACRA,
        environment=SourceEnvironment.MOCK,
        operation=RegistryOperation.OWNERSHIP_PARTIES,
        retrieved_at=retrieved_at,
        evidence_reference="ACRA_OWNERSHIP_PARTIES_111111111M",
    )
    parties = (
        (
            RegistryOwnershipParty(
                party_id="SYN-SL-1",
                party_type=RegistryPartyType.NATURAL_PERSON,
                name="SYNTHETIC HOLDER ONE",
                source_category="Individual",
                source_status="Active",
                share_allotted=Decimal("300"),
                share_type="Ordinary" if share_class else None,
                currency="SINGAPORE DOLLAR" if share_class else None,
                provenance=provenance,
            ),
        )
        if status == RegistryOperationStatus.COMPLETE
        else ()
    )
    return RegistryShareholderEvidence(
        requested_identifier=SIM,
        operation_result=RegistryOperationResult(
            operation=RegistryOperation.OWNERSHIP_PARTIES,
            status=status,
            record_count=len(parties),
            provenance=provenance,
            error=(
                {"code": "REGISTRY_OPERATION_TIMEOUT", "message": "Registry operation timed out."}
                if status == RegistryOperationStatus.FAILED
                else None
            ),
        ),
        ownership_parties=parties,
    )


class FakeShareholderProvider:
    cache_identity = MARKETPLACE
    supports_shareholder_evidence = True

    def __init__(self, status: RegistryOperationStatus, clock) -> None:
        self.status, self.clock, self.calls = status, clock, 0

    def retrieve_shareholder_evidence(self, identifier: str) -> RegistryShareholderEvidence:
        assert identifier == SIM
        self.calls += 1
        return evidence(self.status, self.clock())


@pytest.mark.parametrize(
    ("status", "fresh_for", "cached"),
    [
        (RegistryOperationStatus.COMPLETE, timedelta(days=90), True),
        (RegistryOperationStatus.EMPTY, timedelta(seconds=600), True),
        (RegistryOperationStatus.FAILED, timedelta(0), False),
    ],
)
def test_coordinator_caches_complete_and_empty_evidence_under_its_own_key(
    status: RegistryOperationStatus, fresh_for: timedelta, cached: bool
) -> None:
    now = [datetime(2026, 10, 24, tzinfo=UTC)]
    repository = InMemoryRegistrySnapshotRepository()
    coordinator = RegistryAcquisitionCoordinator(
        repository, RegistryFreshnessPolicy(), clock=lambda: now[0]
    )
    provider = FakeShareholderProvider(status, lambda: now[0])
    first = coordinator.acquire_shareholder_evidence(provider, SIM)
    assert (first.cache_hit, provider.calls) == (False, 1)
    entry = repository.get(SHAREHOLDER_KEY)
    if not cached:
        assert entry is None
        assert coordinator.acquire_shareholder_evidence(provider, SIM).cache_hit is False
        assert provider.calls == 2
        return
    assert entry is not None and entry.cache_schema_version == 4
    assert entry.shareholder_evidence == first.evidence
    # The ordinary acquisition key for the same UEN is untouched.
    assert (
        repository.get(RegistryCacheKey(provider_identity=MARKETPLACE, normalized_identifier=SIM))
        is None
    )
    now[0] += fresh_for - timedelta(seconds=1)
    hit = coordinator.acquire_shareholder_evidence(provider, SIM)
    assert (hit.cache_hit, hit.evidence, provider.calls) == (True, first.evidence, 1)
    now[0] += timedelta(seconds=1)
    assert coordinator.acquire_shareholder_evidence(provider, SIM).cache_hit is False
    assert provider.calls == 2


LEGACY_SHAREHOLDER_KEY = RegistryCacheKey(
    provider_identity=MARKETPLACE.model_copy(
        update={"acquisition_contract_version": LEGACY_SHAREHOLDER_EVIDENCE_CONTRACT_VERSION}
    ),
    normalized_identifier=SIM,
)


def legacy_entry(at: datetime) -> RegistrySnapshotEntry:
    """A D-079 (V1 key, schema 3) entry: rows without a share class."""
    return RegistrySnapshotEntry(
        cache_schema_version=3,
        cache_id=LEGACY_SHAREHOLDER_KEY.digest,
        key=LEGACY_SHAREHOLDER_KEY,
        revision=0,
        acquisition=None,
        shareholder_evidence=evidence(RegistryOperationStatus.COMPLETE, at, share_class=False),
        freshness_anchor=at,
        written_at=at,
    )


def test_a_fresh_d079_cache_entry_is_neither_reused_nor_rewritten() -> None:
    now = [datetime(2026, 10, 24, tzinfo=UTC)]
    repository = InMemoryRegistrySnapshotRepository()
    legacy = legacy_entry(now[0])
    repository.create(legacy)
    coordinator = RegistryAcquisitionCoordinator(
        repository, RegistryFreshnessPolicy(), clock=lambda: now[0]
    )
    provider = FakeShareholderProvider(RegistryOperationStatus.COMPLETE, lambda: now[0])
    result = coordinator.acquire_shareholder_evidence(provider, SIM)
    # The V2 key misses: one read, and the new entry keeps the source share class.
    assert (result.cache_hit, provider.calls) == (False, 1)
    assert [item.share_type for item in result.evidence.ownership_parties] == ["Ordinary"]
    assert repository.get(SHAREHOLDER_KEY) is not None
    assert repository.get(LEGACY_SHAREHOLDER_KEY) == legacy


def test_shareholder_cache_entries_are_exclusive_by_contract_version() -> None:
    at = datetime(2026, 10, 24, tzinfo=UTC)
    good = evidence(RegistryOperationStatus.COMPLETE, at)
    entry = RegistrySnapshotEntry(
        cache_schema_version=4,
        cache_id=SHAREHOLDER_KEY.digest,
        key=SHAREHOLDER_KEY,
        revision=0,
        acquisition=None,
        shareholder_evidence=good,
        freshness_anchor=at,
        written_at=at,
    )
    codec = MongoRegistryCacheStore
    assert codec._decode(codec._encode(entry)) == entry  # noqa: SLF001
    # D-079 entries stay readable exactly, without a share class.
    legacy = legacy_entry(at)
    assert codec._decode(codec._encode(legacy)) == legacy  # noqa: SLF001
    for invalid in (
        {"shareholder_evidence": good},
        {"cache_schema_version": 4},
        {
            "key": SHAREHOLDER_KEY,
            "cache_id": SHAREHOLDER_KEY.digest,
            "shareholder_evidence": legacy.shareholder_evidence,
        },
    ):
        with pytest.raises(ValidationError):
            RegistrySnapshotEntry.model_validate({**legacy.model_dump(), **invalid})
    ordinary = RegistryCacheKey(provider_identity=MARKETPLACE, normalized_identifier=SIM)
    for invalid in (
        {"cache_schema_version": 2},
        {"cache_schema_version": 3},
        {"key": ordinary, "cache_id": ordinary.digest},
        {"shareholder_evidence": None, "negative_result": "NOT_FOUND"},
        {"shareholder_evidence": evidence(RegistryOperationStatus.FAILED, at)},
        {"freshness_anchor": at - timedelta(seconds=1)},
        {"written_at": at - timedelta(seconds=1)},
    ):
        with pytest.raises(ValidationError):
            RegistrySnapshotEntry.model_validate({**entry.model_dump(), **invalid})
    # A percentage can never ride on entity-less shareholder evidence.
    with pytest.raises(ValidationError):
        RegistryShareholderEvidence.model_validate(
            {
                **good.model_dump(),
                "ownership_parties": (
                    {**good.ownership_parties[0].model_dump(), "ownership_percentage": "100"},
                ),
            }
        )


def without_share_class(encoded: dict) -> dict:
    """The same envelope as an exact schema-13 writer produced it: rows without a class."""
    legacy = deepcopy(encoded)
    for item in legacy["ownership"]["discovery"]["records"]:
        for row in item["official_shareholders"]:
            del row["share_type"], row["currency"]
    return {**legacy, "schema_version": 13}


def snapshot_of(onboarding, record) -> DurableCaseSnapshot:
    case = onboarding.get_case(record.case_id)
    assert case is not None
    now = datetime.now(UTC)
    return DurableCaseSnapshot(
        case_id=case.case_id,
        revision=0,
        onboarding=case,
        ownership=record,
        created_at=now,
        updated_at=now,
    )


def refuse_poc_distribution(*args: object, **kwargs: object) -> None:
    raise ValueError("synthetic refusal")


def test_rows_that_cannot_support_the_convention_keep_the_d079_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Units that cannot form a positive issuer total (all current rows zero) fail closed.
    zero = [holder("SYN-Z-1", "SYNTHETIC ZERO", "Individual", 0, "Active")]
    transport = OfflineFiveLayerProtocolTransport()
    transport.shareholders[SIM] = shareholders(zero)
    onboarding, ownership, _ = build(transport)
    record = analyze(onboarding, ownership, GARDEN)
    assert (sim_lim(record).outcome, sim_lim(record).reason_code) == (
        OwnershipDiscoveryOutcome.PROVIDER_PARTIAL,
        OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE,
    )
    assert {edge.provenance.provider for edge in record.relationships} == {
        OVERLAY_RELATIONSHIP_PROVIDER
    }
    assert record.discovery is not None
    assert record.discovery.unresolved_upper_bound_percent == Decimal("62.5")
    assert OwnershipIssueCode.CORPORATE_OWNERSHIP_UNRESOLVED in codes(record)
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    # Any other refusal from the distribution boundary leaves the same retained state.
    monkeypatch.setattr(
        "app.services.ownership_discovery.official_equal_unit_component",
        refuse_poc_distribution,
    )
    transport = OfflineFiveLayerProtocolTransport()
    transport.shareholders[SIM] = shareholders()
    onboarding, ownership, _ = build(transport)
    refused = analyze(onboarding, ownership, GARDEN)
    assert sim_lim(refused).reason_code == OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE
    assert len(sim_lim(refused).official_shareholders) == len(ROWS)
    assert set(by_name(refused)) == {"LIM CHOON HUAT"}


BASE_ROWS = [
    holder("SYN-B-1", "SYNTHETIC BASE ONE", "Individual", 300, "Active"),
    holder("SYN-B-2", "SYNTHETIC BASE TWO", "Individual", 200, "Active"),
]


def assert_d079_retained(record, rows: int) -> None:
    """Nothing attached: the D-079 retained-evidence outcome, exactly as before D-081."""
    sim = sim_lim(record)
    assert (sim.outcome, sim.reason_code, len(sim.official_shareholders)) == (
        OwnershipDiscoveryOutcome.PROVIDER_PARTIAL,
        OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE,
        rows,
    )
    assert {edge.provenance.provider for edge in record.relationships} == {
        OVERLAY_RELATIONSHIP_PROVIDER
    }
    assert record.discovery is not None
    assert record.discovery.unresolved_upper_bound_percent == Decimal("62.5")
    assert OwnershipIssueCode.CORPORATE_OWNERSHIP_UNRESOLVED in codes(record)
    assert set(by_name(record)) == {"LIM CHOON HUAT"}
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED


@pytest.mark.parametrize(
    "rows",
    [
        [
            *BASE_ROWS,
            {
                **holder("SYN-N", "SYNTHETIC NO UNITS", "Individual", 1, "Active"),
                "shareAllotted": None,
            },
        ],
        [*BASE_ROWS, holder("SYN-Z", "SYNTHETIC ZERO", "Individual", 0, "Active")],
        [*BASE_ROWS, holder("syn-b-1", "SYNTHETIC CASE VARIANT", "Individual", 50, "Active")],
        [*BASE_ROWS, holder(SIM, "SIM LIM SELF", "Corporate", 50, "Active")],
        [*BASE_ROWS, holder(SIM.lower(), "SIM LIM SELF", "Corporate", 50, "Withdrawn")],
        [{**row, "status": "Withdrawn"} for row in BASE_ROWS],
    ],
    ids=[
        "missing-units",
        "zero-units",
        "case-variant-duplicate",
        "self-identifier",
        "withdrawn-self-identifier",
        "no-current-rows",
    ],
)
def test_rows_the_convention_cannot_support_attach_nothing(rows: list[dict]) -> None:
    transport = OfflineFiveLayerProtocolTransport()
    transport.shareholders[SIM] = shareholders(rows)
    onboarding, ownership, _ = build(transport)
    assert_d079_retained(analyze(onboarding, ownership, GARDEN), len(rows))


def poc_source(edges) -> bool:
    return any(edge.provenance.provider == POC_EQUAL_UNITS_PROVIDER for edge in edges)


@pytest.mark.parametrize("refusal", ["resource-cap", "merge", "graph-validation"])
def test_a_refused_poc_attachment_keeps_the_d079_outcome(
    monkeypatch: pytest.MonkeyPatch, refusal: str
) -> None:
    transport = OfflineFiveLayerProtocolTransport()
    transport.shareholders[SIM] = shareholders(BASE_ROWS)
    onboarding, ownership, _ = build(transport)
    if refusal == "resource-cap":
        # Garden, SIM LIM and LIM CHOON HUAT leave no room for two more holders.
        ownership.max_parties = 4
    elif refusal == "merge":
        merge = _DiscoveryRun._merge

        def refuse_poc_merge(run, node, uen, issuer):
            if poc_source(issuer.relationships):
                return OwnershipDiscoveryOutcome.PROVIDER_PARTIAL, "SYNTHETIC_MERGE_REFUSAL"
            return merge(run, node, uen, issuer)

        monkeypatch.setattr(_DiscoveryRun, "_merge", refuse_poc_merge)
    else:
        validate = ownership_discovery.validate_ownership_graph

        def refuse_poc_graph(graph):
            if poc_source(edge for edges in graph.adjacency.values() for edge in edges):
                raise OwnershipGraphError
            return validate(graph)

        monkeypatch.setattr(ownership_discovery, "validate_ownership_graph", refuse_poc_graph)
    assert_d079_retained(analyze(onboarding, ownership, GARDEN), len(BASE_ROWS))


def test_rounded_poc_links_above_one_hundred_leave_the_bound_unavailable() -> None:
    # Six equal holders round to 16.666667 each, 100.000002 in total. The unchanged
    # coordinator treats an issuer above 100 as over-allocated, so it reports no bound;
    # the case stays under review and no threshold result is claimed.
    rows = [
        holder(f"SYN-S-{index}", f"SYNTHETIC SIXTH {index}", "Individual", 1, "Active")
        for index in range(1, 7)
    ]
    transport = OfflineFiveLayerProtocolTransport()
    transport.shareholders[SIM] = shareholders(rows)
    onboarding, ownership, _ = build(transport)
    record = analyze(onboarding, ownership, GARDEN)
    links = [
        edge.ownership_percent
        for edge in record.relationships
        if edge.provenance.provider == POC_EQUAL_UNITS_PROVIDER
    ]
    assert links == [Decimal("16.666667")] * 6
    assert sum(links) == Decimal("100.000002")
    assert sim_lim(record).reason_code == OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS
    assert record.discovery is not None
    assert (
        record.discovery.topology_complete,
        record.discovery.graph_complete,
        record.discovery.unresolved_upper_bound_percent,
        record.discovery.classification_certainty,
    ) == (True, False, None, "UNCERTAIN")
    assert {item.classification for item in record.candidates} == {
        OwnershipCandidateClassification.REVIEW_REQUIRED
    }
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED


def test_issue_wording_separates_poc_issuers_from_issuers_without_percentages() -> None:
    uens = ["300000020A", "300000021A", "300000022A"]
    transport = OfflineFiveLayerProtocolTransport(allowlist=frozenset(uens))
    transport.profiles = {uen: None for uen in uens}
    transport.profiles[uens[0]] = company_profile(uens[0], "MIXED ROOT (SYNTHETIC)")
    transport.shareholders[uens[1]] = shareholders(BASE_ROWS, uen=uens[1])
    transport.shareholders[uens[2]] = shareholders(
        [holder("SYN-Z-9", "SYNTHETIC ZERO", "Individual", 0, "Active")], uen=uens[2]
    )
    scenario = HybridOverlayScenario(
        scenario_id="TEST_MIXED_EVIDENCE",
        root_uen=uens[0],
        issuers=(
            OverlayIssuer(
                issuer_uen=uens[0],
                local_display_name="MIXED ROOT (SYNTHETIC)",
                declared_active_units=Decimal("2"),
                holders=tuple(
                    OverlayHolder(
                        holder_id=uen,
                        holder_name=f"C{index} (SYNTHETIC)",
                        category="Corporate",
                        registration_number=uen,
                        share_units=Decimal("1"),
                    )
                    for index, uen in enumerate(uens[1:], start=1)
                ),
            ),
        ),
    )
    onboarding, _, _ = build(transport)
    record = analyze(onboarding, custom_service(onboarding, (scenario,)), uens[0])
    found = records(record)
    assert (found[uens[1]].reason_code, found[uens[2]].reason_code) == (
        OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS,
        OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE,
    )
    messages = {item.code: item.message for item in record.issues}
    assert messages[OwnershipIssueCode.OWNERSHIP_DENOMINATOR_REQUIRED] == (
        "3 official Marketplace Mock shareholder row(s) are retained without an entity "
        "profile; 1 of 2 issuers show POC-unit percentages; no ACRA denominator exists."
    )
    assert messages[OwnershipIssueCode.SYNTHETIC_OWNERSHIP_EVIDENCE] == (
        "Ownership links are LOCAL_SYNTHETIC_RELATIONSHIP declarations or "
        "LOCAL_POC_ASSUMED_EQUAL_UNITS estimates, not ACRA-returned ownership; unverified "
        "issuers keep LOCAL_SYNTHETIC_IDENTITY."
    )
    assert OwnershipIssueCode.CORPORATE_OWNERSHIP_UNRESOLVED in messages
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED


LIVE_SHAPE = [
    holder("SYN-FGH", "FGH SERVICES, INC.", "Corporate", 10000, "Withdrawn"),
    holder("SYN-ABCD", "ABCD123", "Individual", 900, "Active"),
    {**holder("SYN-TWL", "TAN WEI LING", "Individual", 100, "Active"), "shareType": "Preference"},
    {**holder("SYN-EFGH", "EFGH2345", "Individual", 100, "Active"), "shareType": "Others"},
]
POC_REFUSAL = "OWNERSHIP_POC_EVIDENCE_REVIEW_REQUIRED"


def garden_poc_case() -> tuple[TestClient, OfflineFiveLayerProtocolTransport, str]:
    client, transport = system()
    transport.shareholders[SIM] = shareholders(LIVE_SHAPE)
    current = start(client, GARDEN_FIELDS, "garden-partnership-reviewed-client.pdf")
    return client, transport, current["case"]["case_id"]


def manual_decision(
    client: TestClient,
    case_id: str,
    *,
    source_selection: str = "CURRENT_EVIDENCE",
    percents: dict[str, str] | None = None,
    version_offset: int = 0,
) -> httpx.Response:
    """The creator's ownership decision over the current graph, optionally re-valued."""
    summary = successful(client.get(f"/api/clm/zero-touch/cases/{case_id}"))
    ownership = successful(client.get(f"/api/onboarding/cases/{case_id}/ownership"))
    documents = successful(client.get(f"/api/onboarding/cases/{case_id}/documents"))
    [document] = [item for item in documents if not item["superseded_by_document_id"]]
    names = {party["party_id"]: party["display_name"] for party in ownership["parties"]}
    return client.post(
        f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
        json={
            "root_registration_number": summary["case"]["entity"]["registration_number"],
            "evidence_document_id": document["document_id"],
            "evidence_document_version": len(document["events"]),
            "as_of_date": "2026-10-20",
            "rationale": None,
            "root_party_id": ownership["root_party_id"],
            "parties": ownership["parties"],
            "relationships": [
                {
                    "relationship_id": edge["relationship_id"],
                    "parent_party_id": edge["parent_party_id"],
                    "child_party_id": edge["child_party_id"],
                    "ownership_percent": (percents or {}).get(
                        names[edge["child_party_id"]], edge["ownership_percent"]
                    ),
                }
                for edge in ownership["relationships"]
            ],
            "observed_document_versions": ownership["document_bindings"],
            "selected_observation_ids": [],
            "source_selection": source_selection,
            "expected_automation_version": summary["version"],
            "expected_ownership_version": ownership["version"] + version_offset,
            "expected_case_event_count": len(summary["case"]["events"]),
        },
    )


def gate_state(summary: dict) -> tuple:
    return (
        summary["version"],
        summary["status"],
        summary["current_stage"],
        [item["exception_type"] for item in summary["active_exceptions"]],
        summary["clm"]["readiness"]["blockers"],
        len(summary["case"]["events"]),
        summary["case"].get("goldtier_result"),
        summary["clm"]["submission"],
    )


def test_poc_links_can_be_neither_kept_nor_redeclared_by_the_creator() -> None:
    client, transport, case_id = garden_poc_case()
    ownership = successful(client.get(f"/api/onboarding/cases/{case_id}/ownership"))
    summary = successful(client.get(f"/api/clm/zero-touch/cases/{case_id}"))
    [sim] = [
        item for item in ownership["discovery"]["records"] if item["registration_number"] == SIM
    ]
    # The active holdings come from the official Marketplace Mock rows; withdrawn is history.
    assert (sim["reason_code"], sim["official_shareholder_lookup"]) == (
        OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS,
        "SHAREHOLDERS_FETCHED",
    )
    assert {
        (row["provider"], row["environment"], row["dataset_namespace"])
        for row in sim["official_shareholders"]
    } == {("ACRA_REGISTRY_ACQUISITION", "MOCK", "ACRA_API_MARKETPLACE_MOCK_V1")}
    names = {party["party_id"]: party["display_name"] for party in ownership["parties"]}
    poc = {
        names[edge["child_party_id"]]: (
            edge["ownership_percent"],
            edge["provenance"]["environment"],
        )
        for edge in ownership["relationships"]
        if edge["provenance"]["provider"] == POC_EQUAL_UNITS_PROVIDER
    }
    assert poc == {
        "ABCD123": ("81.818182", "LOCAL"),
        "TAN WEI LING": ("9.090909", "LOCAL"),
        "EFGH2345": ("9.090909", "LOCAL"),
    }
    assert set(poc) == {
        row["display_name"] for row in sim["official_shareholders"] if row["current_interest"]
    }
    assert {
        item["party"]["display_name"]: (
            Decimal(item["aggregated_ownership_percent"]),
            item["classification"],
            item["threshold_result"],
        )
        for item in ownership["candidates"]
    } == {
        "ABCD123": (Decimal("51.13636375"), "REVIEW_REQUIRED", "INDETERMINATE"),
        "LIM CHOON HUAT": (Decimal("37.5"), "REVIEW_REQUIRED", "INDETERMINATE"),
        "TAN WEI LING": (Decimal("5.681818125"), "REVIEW_REQUIRED", "INDETERMINATE"),
        "EFGH2345": (Decimal("5.681818125"), "REVIEW_REQUIRED", "INDETERMINATE"),
    }
    assert ownership["state"] == "REVIEW_REQUIRED"
    # D-112 (O7): no scenario declares acceptance, so this hybrid Garden demonstration is
    # never accepted and the ownership review blocker holds, even with the switch on.
    assert ownership["poc_acceptance"] is None
    assert ownership["poc_basis_accepted"] is False
    assert "OWNERSHIP_REVIEW_REQUIRED" in summary["clm"]["readiness"]["blockers"]

    # D-081 owner decision (F1): keeping, redeclaring unchanged, or keeping any single POC
    # value is refused before any replacement, confirmation reset or readiness change.
    for refused in (
        manual_decision(client, case_id),
        manual_decision(client, case_id, source_selection="USER_SUPPLIED_DECLARATION"),
        manual_decision(
            client,
            case_id,
            source_selection="USER_SUPPLIED_DECLARATION",
            percents={"TAN WEI LING": "12.181818", "EFGH2345": "6.000000"},
        ),
    ):
        assert refused.status_code == 409
        assert refused.json()["detail"]["code"] == POC_REFUSAL
    assert successful(client.get(f"/api/onboarding/cases/{case_id}/ownership")) == ownership
    assert gate_state(successful(client.get(f"/api/clm/zero-touch/cases/{case_id}"))) == (
        gate_state(summary)
    )
    # A stale decision still meets the existing CAS refusal first.
    stale = manual_decision(client, case_id, version_offset=1)
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "ZERO_TOUCH_MANUAL_OWNERSHIP_STALE"
    assert successful(client.get(f"/api/onboarding/cases/{case_id}/ownership")) == ownership
    assert transport.metadata()["external_calls"] == 0


def test_an_independent_declaration_on_a_poc_case_follows_the_existing_rules() -> None:
    client, _, case_id = garden_poc_case()
    hybrid = successful(client.get(f"/api/onboarding/cases/{case_id}/ownership"))
    accepted = manual_decision(
        client,
        case_id,
        source_selection="USER_SUPPLIED_DECLARATION",
        percents={"ABCD123": "60.000000", "TAN WEI LING": "25.000000", "EFGH2345": "15.000000"},
    )
    assert accepted.status_code == 200
    ownership = successful(client.get(f"/api/onboarding/cases/{case_id}/ownership"))
    assert (ownership["state"], ownership["provider_name"]) == (
        "ANALYZED",
        "MANUAL_DECLARATION_POC",
    )
    assert ownership["manual_review_receipt"]["source_selection"] == "USER_SUPPLIED_DECLARATION"
    [prior] = ownership["prior_analyses"]
    assert prior["analysis_id"] == hybrid["analysis_id"]
    assert POC_EQUAL_UNITS_PROVIDER in {
        edge["provenance"]["provider"] for edge in prior["relationships"]
    }
    assert {
        item["party"]["display_name"]: (
            Decimal(item["aggregated_ownership_percent"]),
            item["classification"],
        )
        for item in ownership["candidates"]
    } == {
        "ABCD123": (Decimal("37.5"), "PROVISIONAL_UBO_CANDIDATE"),
        "LIM CHOON HUAT": (Decimal("37.5"), "PROVISIONAL_UBO_CANDIDATE"),
        "TAN WEI LING": (Decimal("15.625"), "BELOW_PROVISIONAL_THRESHOLD"),
        "EFGH2345": (Decimal("9.375"), "BELOW_PROVISIONAL_THRESHOLD"),
    }
    summary = successful(client.get(f"/api/clm/zero-touch/cases/{case_id}"))
    assert summary["clm"]["readiness"]["blockers"] == []
    # Target confirmation still precedes any GoldTier target mutation.
    assert [item["exception_type"] for item in summary["active_exceptions"]] == [
        "TARGET_CONFIRMATION_REQUIRED"
    ]
    assert summary["case"].get("goldtier_result") is None
    assert summary["clm"]["submission"] is None


def test_a_graph_kept_before_the_rule_cannot_be_kept_or_redeclared_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, case_id = garden_poc_case()
    with monkeypatch.context() as patch:
        # The relabelling the earlier candidate allowed: POC links copied under the
        # manual label by keeping current evidence.
        patch.setattr(
            "app.services.ownership_analysis._poc_assumed_edges", lambda record: frozenset()
        )
        assert manual_decision(client, case_id).status_code == 200
    kept = successful(client.get(f"/api/onboarding/cases/{case_id}/ownership"))
    assert {edge["provenance"]["provider"] for edge in kept["relationships"]} == {
        "MANUAL_DECLARATION_POC"
    }
    for source_selection in ("CURRENT_EVIDENCE", "USER_SUPPLIED_DECLARATION"):
        refused = manual_decision(client, case_id, source_selection=source_selection)
        assert refused.status_code == 409
        assert refused.json()["detail"]["code"] == POC_REFUSAL
    assert successful(client.get(f"/api/onboarding/cases/{case_id}/ownership")) == kept


def test_schema_fourteen_round_trip_and_older_schemas_reject_later_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = OfflineFiveLayerProtocolTransport()
    transport.shareholders[SIM] = shareholders()
    onboarding, ownership, _ = build(transport)
    record = analyze(onboarding, ownership, GARDEN)
    codec = object.__new__(MongoCaseStore)
    encoded = codec._encode(snapshot_of(onboarding, record))  # noqa: SLF001
    decoded = codec._decode(encoded)  # noqa: SLF001
    assert decoded.schema_version == 20
    assert list(range(1, 21)) == _SUPPORTED_SCHEMA_VERSIONS
    assert decoded.ownership is not None and decoded.ownership == record
    assert {row.share_type for row in sim_lim(decoded.ownership).official_shareholders} == {
        "Ordinary"
    }
    # An exact schema-13 envelope can carry neither a D-080 share class nor D-081 POC
    # links and their reason, even without the class (fail closed).
    for legacy_poc in ({**encoded, "schema_version": 13}, without_share_class(encoded)):
        with pytest.raises(PersistenceDataInvalidError):
            codec._decode(legacy_poc)  # noqa: SLF001
    # A D-079-shaped case (the distribution refused) has rows only; without a class its
    # exact schema-13 envelope reads into the current form, unchanged.
    monkeypatch.setattr(
        "app.services.ownership_discovery.official_equal_unit_component",
        refuse_poc_distribution,
    )
    retained = analyze(onboarding, ownership, GARDEN)
    assert sim_lim(retained).reason_code == OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE
    d079 = without_d101_fields(
        without_share_class(codec._encode(snapshot_of(onboarding, retained)))  # noqa: SLF001
    )
    legacy = codec._decode(d079)  # noqa: SLF001
    assert legacy.schema_version == 20 and legacy.ownership is not None
    assert {row.share_type for row in sim_lim(legacy.ownership).official_shareholders} == {None}
    # An exact schema-12 envelope can never carry D-079 evidence at all...
    with pytest.raises(PersistenceDataInvalidError):
        codec._decode({**d079, "schema_version": 12})  # noqa: SLF001
    # ...while ordinary schema-12 content still reads into the current form.
    assert codec._decode(  # noqa: SLF001
        {**without_d101_fields(encoded), "schema_version": 12, "ownership": None}
    ).schema_version == 20


def test_a_cached_empty_profile_with_a_fresh_shareholder_read_counts_as_provider_backed() -> None:
    transport = ShareholderFaultTransport(shareholder_fault=500)
    transport.shareholders[SIM] = shareholders()
    onboarding, ownership, _ = build(transport)
    failed = analyze(onboarding, ownership, GARDEN)
    assert sim_lim(failed).outcome == OwnershipDiscoveryOutcome.PROVIDER_FAILED
    transport.shareholder_fault = None
    record = analyze(onboarding, ownership, GARDEN)
    # The entity profile NOT_FOUND came from the negative cache; the shareholder read did not.
    assert transport.calls[("ENTITY_PROFILE", SIM)] == 1
    assert sim_lim(record).official_shareholder_lookup == "SHAREHOLDERS_FETCHED"
    assert record.discovery is not None
    assert (
        record.discovery.registry_lookups,
        record.discovery.provider_backed_lookups,
        record.discovery.cache_hits,
    ) == (1, 1, 0)


@pytest.mark.parametrize(
    ("error", "outcome", "reason"),
    [
        (
            RegistryCacheReadError(),
            OwnershipDiscoveryOutcome.CACHE_FAILURE,
            RegistryCacheReadError.code,
        ),
        (
            RegistryAcquisitionBusyError(),
            OwnershipDiscoveryOutcome.HARD_LIMIT,
            "REGISTRY_ACQUISITION_BUSY",
        ),
    ],
)
def test_shareholder_cache_and_busy_failures_stop_safely(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    outcome: OwnershipDiscoveryOutcome,
    reason: str,
) -> None:
    transport = OfflineFiveLayerProtocolTransport()
    transport.shareholders[SIM] = shareholders()
    onboarding, ownership, _ = build(transport)

    def fail(*args: object, **kwargs: object) -> None:
        raise error

    coordinator = onboarding._registry_acquisition_coordinator  # noqa: SLF001
    monkeypatch.setattr(coordinator, "acquire_shareholder_evidence", fail)
    record = analyze(onboarding, ownership, GARDEN)
    sim = sim_lim(record)
    assert (sim.outcome, sim.reason_code, sim.official_shareholders) == (outcome, reason, ())
    assert OwnershipIssueCode.OWNERSHIP_DENOMINATOR_REQUIRED not in codes(record)
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert record.discovery is not None
    assert record.discovery.unresolved_upper_bound_percent == Decimal("62.5")


def test_coordinator_refuses_evidence_that_expires_during_its_own_fetch() -> None:
    now = [datetime(2026, 10, 24, tzinfo=UTC)]
    retrieved = now[0]
    repository = InMemoryRegistrySnapshotRepository()
    coordinator = RegistryAcquisitionCoordinator(
        repository, RegistryFreshnessPolicy(), clock=lambda: now[0]
    )

    class SlowProvider(FakeShareholderProvider):
        def retrieve_shareholder_evidence(self, identifier: str) -> RegistryShareholderEvidence:
            self.calls += 1
            result = evidence(RegistryOperationStatus.COMPLETE, retrieved)
            now[0] = retrieved + timedelta(days=90)  # the fixed policy window has elapsed
            return result

    provider = SlowProvider(RegistryOperationStatus.COMPLETE, lambda: now[0])
    with pytest.raises(RegistryCacheInvalidError):
        coordinator.acquire_shareholder_evidence(provider, SIM)
    assert provider.calls == 1
    assert repository.get(SHAREHOLDER_KEY) is None
