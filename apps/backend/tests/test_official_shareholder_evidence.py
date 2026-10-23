"""D-079 official shareholder evidence for an empty-profile corporate holder; offline only.

SIM LIM (`111111111M`) is discovered from Garden's direct-holder overlay. Its official
Marketplace entity-basic profile is empty while its shareholder operation returns rows.
The rows are retained beside the graph without identity, legal form or percentages, and
the case stays under review. All rows below are synthetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from pydantic import ValidationError
from scripts.five_layer_hybrid_fixture import FIVE_LAYER_FIELDS, OfflineFiveLayerProtocolTransport
from scripts.slice_b_registry_fixture import GARDEN_FIELDS
from test_five_layer_hybrid_journey import system
from test_hybrid_five_layer_overlay import analyze, build, by_name, codes, records
from test_slice_b_registry_demo import start
from test_zero_touch_exception_remediation import successful

from app.composition import build_onboarding_service
from app.config import Settings
from app.connectors.acra_sandbox import AcraHttpResponse
from app.connectors.hybrid_ownership_overlay import (
    FIVE_LAYER_ROOT_UEN,
    OVERLAY_RELATIONSHIP_PROVIDER,
)
from app.domain.models import (
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
    OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE,
    OfficialShareholderObservation,
    OwnershipAnalysisState,
    OwnershipCandidateClassification,
    OwnershipDiscoveryOutcome,
    OwnershipDiscoveryRecord,
    OwnershipIssueCode,
    OwnershipThresholdResult,
    PartyType,
)
from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.models import DurableCaseSnapshot
from app.persistence.mongo_case_store import MongoCaseStore
from app.persistence.mongo_registry_cache_store import MongoRegistryCacheStore
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


def test_empty_profile_corporate_holder_keeps_official_shareholders_beside_the_graph() -> None:
    transport = OfflineFiveLayerProtocolTransport()
    transport.shareholders[SIM] = shareholders()
    onboarding, ownership, _ = build(transport)
    record = analyze(onboarding, ownership, GARDEN)

    # Garden's root still carries only its two declared direct holders.
    assert {edge.provenance.provider for edge in record.relationships} == {
        OVERLAY_RELATIONSHIP_PROVIDER
    }
    assert {party.display_name for party in record.parties} == {
        "GARDEN BUSINESS",
        "SIM LIM PTE. LTD.",
        "LIM CHOON HUAT",
    }
    sim = sim_lim(record)
    assert (sim.outcome, sim.reason_code, sim.official_shareholder_lookup) == (
        OwnershipDiscoveryOutcome.PROVIDER_PARTIAL,
        OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE,
        "SHAREHOLDERS_FETCHED",
    )
    # No identity, legal form or overlay basis is manufactured for SIM LIM.
    assert (sim.identity_basis, sim.official_entity_lookup, sim.official_legal_form) == (
        None,
        None,
        None,
    )
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
    assert {item.source_status for item in rows.values()} == {"Active", "Withdrawn"}
    assert {
        (item.provider, item.environment, item.dataset_namespace, item.source_operation)
        for item in rows.values()
    } == {
        ("ACRA_REGISTRY_ACQUISITION", "MOCK", "ACRA_API_MARKETPLACE_MOCK_V1", "OWNERSHIP_PARTIES")
    }
    # The corporate holder has no supplied registration identifier, so it is never
    # recursed into; no discovery record or lookup exists for it.
    assert rows["SYN-SL-C1"].registration_identifier is None
    assert set(records(record)) == {SIM}
    # The branch stays unresolved: no edge, no percentage, same 62.5% bound.
    assert record.discovery is not None
    assert record.discovery.unresolved_upper_bound_percent == Decimal("62.5")
    assert (record.discovery.topology_complete, record.discovery.graph_complete) == (False, False)
    issue = next(
        item
        for item in record.issues
        if item.code == OwnershipIssueCode.OWNERSHIP_DENOMINATOR_REQUIRED
    )
    assert issue.affected_party_ids == [sim.party_id]
    assert {
        OwnershipIssueCode.INCOMPLETE_LEGAL_ENTITY,
        OwnershipIssueCode.CORPORATE_OWNERSHIP_UNRESOLVED,
        OwnershipIssueCode.SYNTHETIC_OWNERSHIP_EVIDENCE,
        OwnershipIssueCode.UBO_REVIEW_REQUIRED,
    } < codes(record)
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert set(by_name(record)) == {"LIM CHOON HUAT"}
    lim = by_name(record)["LIM CHOON HUAT"]
    assert (lim.threshold_result, lim.classification, lim.synthetic_basis_threshold_result) == (
        OwnershipThresholdResult.INDETERMINATE,
        OwnershipCandidateClassification.REVIEW_REQUIRED,
        OwnershipThresholdResult.MET,
    )
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
    assert second.discovery is not None
    assert (second.discovery.provider_backed_lookups, second.discovery.cache_hits) == (0, 1)


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
    [sim] = ownership["discovery"]["records"]
    assert (sim["outcome"], sim["official_shareholder_lookup"]) == (
        "PROVIDER_PARTIAL",
        "SHAREHOLDERS_FETCHED",
    )
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
    status: RegistryOperationStatus, retrieved_at: datetime
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
    assert entry is not None and entry.cache_schema_version == 3
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


def test_shareholder_cache_entries_are_exclusive_schema_three() -> None:
    at = datetime(2026, 10, 24, tzinfo=UTC)
    good = evidence(RegistryOperationStatus.COMPLETE, at)
    entry = RegistrySnapshotEntry(
        cache_schema_version=3,
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
    ordinary = RegistryCacheKey(provider_identity=MARKETPLACE, normalized_identifier=SIM)
    for invalid in (
        {"cache_schema_version": 2},
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


def test_schema_thirteen_round_trip_and_schema_twelve_rejects_official_shareholders() -> None:
    transport = OfflineFiveLayerProtocolTransport()
    transport.shareholders[SIM] = shareholders()
    onboarding, ownership, _ = build(transport)
    record = analyze(onboarding, ownership, GARDEN)
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
    # An exact schema-12 envelope can never carry D-079 evidence (fail closed)...
    with pytest.raises(PersistenceDataInvalidError):
        codec._decode({**encoded, "schema_version": 12})  # noqa: SLF001
    # ...while ordinary schema-12 content still reads into the current form.
    assert codec._decode({**encoded, "schema_version": 12, "ownership": None}).schema_version == 13  # noqa: SLF001


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
