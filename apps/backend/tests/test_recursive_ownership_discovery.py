"""Registry-driven recursive corporate ownership discovery (synthetic Mock only)."""

from collections import Counter
from collections.abc import Callable, Iterable
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.connectors.acra import (
    AcraAddressPayload,
    AcraCompanyPayload,
    AcraOfficersPayload,
    AcraOwnershipPartiesPayload,
    AcraOwnershipPartyPayload,
    AcraRelationshipPayload,
    AcraRelationshipsPayload,
)
from app.connectors.acra_bizfile_sandbox import BizfileMockOwnershipPartiesDecoder
from app.connectors.errors import AcraMalformedResponseError, AcraServiceUnavailableError
from app.connectors.garden_business import (
    GARDEN_BUSINESS_MOCK_SHAREHOLDERS_BODY,
    GARDEN_BUSINESS_UEN,
    SIM_LIM_MOCK_SHAREHOLDERS_BODY,
    SIM_LIM_UEN,
    derive_garden_ownership,
    derive_issuer_direct_ownership,
    synthetic_issuer_shareholders,
)
from app.connectors.mock_acra import MOCK_ACRA_DATASET_NAMESPACE, MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.connectors.registry import AcraRegistryProviderAdapter, RegistryProviderRouter
from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
from app.domain.models import (
    OnboardingCase,
    RegistryCacheKey,
    RegistryEvidenceDisposition,
    RegistryFreshnessPolicy,
    RegistryProviderIdentity,
    RegistrySnapshotEntry,
    SourceEnvironment,
    SourceSystem,
)
from app.domain.ownership import (
    OwnershipAnalysisRecord,
    OwnershipAnalysisState,
    OwnershipBasis,
    OwnershipCandidateClassification,
    OwnershipDiscoveryOutcome,
    OwnershipIssueCode,
    OwnershipThresholdResult,
)
from app.domain.policy import (
    CasePolicySnapshot,
    EvidenceClassifierPolicy,
    OwnershipDiscoveryPolicySnapshot,
    RegistryPolicySnapshot,
)
from app.services.onboarding import OnboardingService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_discovery import (
    OwnershipDiscoveryCoordinator,
    VerifiedPersonBinding,
)
from app.services.ownership_errors import OwnershipInfrastructureError
from app.services.ownership_repository import InMemoryOwnershipAnalysisRepository
from app.services.registry_acquisition import RegistryAcquisitionCoordinator
from app.services.registry_cache_repository import (
    InMemoryRegistrySnapshotRepository,
    RegistrySnapshotRepositoryInvalidError,
)
from app.services.repository import InMemoryOnboardingCaseRepository

NOW = datetime(2026, 10, 23, 2, 0, tzinfo=UTC)
ROOT = "300000000A"
DISCOVERY = OwnershipDiscoveryPolicySnapshot(
    trace_threshold_percent=Decimal("10.000000"),
    max_corporate_depth=5,
    call_budget_enabled=False,
    call_budget_max=10,
)
_ADDRESS = AcraAddressPayload(
    block="1", street="SYNTHETIC ROAD", postal_code="000001", country_code="SG"
)


@dataclass
class Clock:
    now: datetime = NOW

    def __call__(self) -> datetime:
        return self.now


@dataclass(frozen=True)
class Issuer:
    """One fictional issuer and its own direct holders: (id, kind, percent, reg, country)."""

    name: str
    holders: tuple[tuple[str, str, str, str | None, str], ...]
    entity_type: str = "PRIVATE_COMPANY_LIMITED_BY_SHARES"


def person(party_id: str, percent: str) -> tuple[str, str, str, str | None, str]:
    return (party_id, "P", percent, None, "SG")


def company(
    uen: str, percent: str, *, country: str = "SG"
) -> tuple[str, str, str, str | None, str]:
    return (f"CORP_{uen}", "C", percent, uen, country)


class SyntheticRegistry:
    """Credential-free per-issuer Mock connector counting every operation call."""

    def __init__(self, issuers: dict[str, Issuer], clock: Callable[[], datetime]) -> None:
        self.issuers = issuers
        self.clock = clock
        self.calls: Counter[tuple[str, str]] = Counter()
        self.failing_relationships: set[str] = set()

    def issuer_calls(self, uen: str) -> int:
        return sum(count for (key, _), count in self.calls.items() if key == uen)

    def _endpoint(self, uen: str, suffix: str = "") -> str:
        return f"https://mock.acra.gov.sg/api/entities/{uen}{suffix}"

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        self.calls[(uen, "company")] += 1
        issuer = self.issuers.get(uen)
        if issuer is None:
            return None
        return AcraCompanyPayload(
            uen=uen,
            entity_name=issuer.name,
            country_code="SG",
            entity_type=issuer.entity_type,
            registration_date=date(2020, 1, 1),
            entity_status="LIVE",
            registered_address=_ADDRESS,
            source_environment="MOCK",
            source_endpoint=self._endpoint(uen),
            retrieved_at=self.clock(),
        )

    def fetch_officers(self, uen: str) -> AcraOfficersPayload:
        self.calls[(uen, "officers")] += 1
        return AcraOfficersPayload(
            uen=uen,
            officers=(),
            source_environment="MOCK",
            source_endpoint=self._endpoint(uen, "/officers"),
            retrieved_at=self.clock(),
        )

    def fetch_ownership_parties(self, uen: str) -> AcraOwnershipPartiesPayload:
        self.calls[(uen, "parties")] += 1
        holders = self.issuers[uen].holders
        return AcraOwnershipPartiesPayload(
            uen=uen,
            ownership_parties=tuple(
                AcraOwnershipPartyPayload(
                    party_id=party_id,
                    party_type="LEGAL_ENTITY" if kind == "C" else "NATURAL_PERSON",
                    name=f"SYNTHETIC {party_id}",
                    registration_identifier=registration,
                    country=country,
                    ownership_percentage=Decimal(percent),
                )
                for party_id, kind, percent, registration, country in holders
            ),
            source_environment="MOCK",
            source_endpoint=self._endpoint(uen, "/ownership-parties"),
            retrieved_at=self.clock(),
        )

    def fetch_relationships(self, uen: str) -> AcraRelationshipsPayload:
        self.calls[(uen, "relationships")] += 1
        if uen in self.failing_relationships:
            raise AcraServiceUnavailableError
        return AcraRelationshipsPayload(
            uen=uen,
            relationships=tuple(
                AcraRelationshipPayload(
                    relationship_id=f"REL_{index}",
                    owned_entity_id=f"ENTITY_{uen}",
                    owner_party_id=party_id,
                    ownership_percentage=Decimal(percent),
                )
                for index, (party_id, _, percent, _, _) in enumerate(
                    self.issuers[uen].holders, start=1
                )
            ),
            source_environment="MOCK",
            source_endpoint=self._endpoint(uen, "/relationships"),
            retrieved_at=self.clock(),
        )


class CountingConnector:
    """Delegate to a connector while counting each per-issuer operation."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.calls: Counter[tuple[str, str]] = Counter()

    def issuer_calls(self, uen: str) -> int:
        return sum(count for (key, _), count in self.calls.items() if key == uen)

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        self.calls[(uen, "company")] += 1
        return self.inner.fetch_company(uen)  # type: ignore[no-any-return]

    def fetch_officers(self, uen: str) -> AcraOfficersPayload:
        self.calls[(uen, "officers")] += 1
        return self.inner.fetch_officers(uen)  # type: ignore[no-any-return]

    def fetch_ownership_parties(self, uen: str) -> AcraOwnershipPartiesPayload:
        self.calls[(uen, "parties")] += 1
        return self.inner.fetch_ownership_parties(uen)  # type: ignore[no-any-return]

    def fetch_relationships(self, uen: str) -> AcraRelationshipsPayload:
        self.calls[(uen, "relationships")] += 1
        return self.inner.fetch_relationships(uen)  # type: ignore[no-any-return]


def policy(discovery: OwnershipDiscoveryPolicySnapshot | None = DISCOVERY) -> CasePolicySnapshot:
    return CasePolicySnapshot(
        snapshot_label="SYNTHETIC_DISCOVERY_TEST",
        catalogue_version=1,
        idp_review_confidence_threshold=Decimal("0.85"),
        ubo_threshold_percent=Decimal("25.000000"),
        registry=RegistryPolicySnapshot(),
        evidence_classifier=EvidenceClassifierPolicy(),
        ownership_discovery=discovery,
        policy_identity="a" * 64,
        bound_at=NOW,
    )


def identity(namespace: str = MOCK_ACRA_DATASET_NAMESPACE) -> RegistryProviderIdentity:
    return RegistryProviderIdentity(
        provider=SourceSystem.ACRA,
        environment=SourceEnvironment.MOCK,
        acquisition_contract_version="PHASE10_ACQUISITION_V1",
        dataset_namespace=namespace,
    )


@dataclass
class Harness:
    connector: Any
    repository: Any
    onboarding: OnboardingService
    ownership: OwnershipAnalysisService
    clock: Clock = field(default_factory=Clock)

    def analyze(self, uen: str) -> OwnershipAnalysisRecord:
        case = self.onboarding.create_staged_case(uen)
        self.ownership.load(case_id=case.case_id)
        return self.ownership.analyze(case_id=case.case_id)


def harness(
    connector: Any,
    *,
    discovery: OwnershipDiscoveryPolicySnapshot | None = DISCOVERY,
    repository: Any = None,
    clock: Clock | None = None,
    bindings: Iterable[VerifiedPersonBinding] = (),
    reader_wrapper: Callable[[OnboardingService], Any] | None = None,
    cases_wrapper: Callable[[OnboardingService], Any] | None = None,
    coordinator_options: dict[str, Any] | None = None,
) -> Harness:
    active_clock = clock or Clock()
    active_repository = repository or InMemoryRegistrySnapshotRepository()
    onboarding = OnboardingService(
        acra=None,
        registry_router=RegistryProviderRouter(
            AcraRegistryProviderAdapter(connector, cache_identity=identity(), clock=active_clock)
        ),
        registry_acquisition_coordinator=RegistryAcquisitionCoordinator(
            active_repository,
            RegistryFreshnessPolicy.model_validate({"duration_seconds": 7_776_000}),
            clock=active_clock,
        ),
        goldtier=MockGoldTierConnector(),
        repository=InMemoryOnboardingCaseRepository(),
        clock=active_clock,
        policy_snapshot_provider=lambda: policy(discovery),
    )
    reader = reader_wrapper(onboarding) if reader_wrapper is not None else onboarding
    ownership = OwnershipAnalysisService(
        cases=cases_wrapper(onboarding) if cases_wrapper is not None else onboarding,
        provider=RegistryAcquisitionOwnershipProvider(onboarding),
        discovery=OwnershipDiscoveryCoordinator(
            reader, verified_person_bindings=bindings, **(coordinator_options or {})
        ),
        repository=InMemoryOwnershipAnalysisRepository(),
        threshold_percent=Decimal("25"),
        max_parties=100,
        max_relationships=200,
        max_depth=8,
        max_paths_per_candidate=64,
        max_total_paths=256,
        clock=active_clock,
    )
    return Harness(connector, active_repository, onboarding, ownership, active_clock)


def synthetic(issuers: dict[str, Issuer], **options: Any) -> Harness:
    clock = options.pop("clock", None) or Clock()
    return harness(SyntheticRegistry(issuers, clock), clock=clock, **options)


def by_name(record: OwnershipAnalysisRecord) -> dict[str, Any]:
    return {item.party.display_name: item for item in record.candidates}


def outcomes(record: OwnershipAnalysisRecord) -> dict[str, OwnershipDiscoveryOutcome]:
    assert record.discovery is not None
    return {
        item.registration_number or item.party_id: item.outcome
        for item in record.discovery.records
    }


def codes(record: OwnershipAnalysisRecord) -> set[OwnershipIssueCode]:
    return {item.code for item in record.issues}


# --- A. Garden source contract, fixture boundary and actual onboarding trigger ---


def test_garden_body_classifies_nested_corporate_row_by_category() -> None:
    rows = synthetic_issuer_shareholders(
        GARDEN_BUSINESS_MOCK_SHAREHOLDERS_BODY, requested_uen=GARDEN_BUSINESS_UEN
    )
    assert [(row.shareholder_id, row.shareholder_category) for row in rows] == [
        (SIM_LIM_UEN, "Corporate"),
        ("S9988776F", "Individual"),
    ]
    decoded = BizfileMockOwnershipPartiesDecoder(include_withdrawn=True).decode(
        GARDEN_BUSINESS_MOCK_SHAREHOLDERS_BODY,
        requested_uen=GARDEN_BUSINESS_UEN,
        source_endpoint="https://mock.acra.gov.sg/api/entities/11111999A/shareholders",
        retrieved_at=NOW,
    )
    # The row nested under `individual` is still classified as a legal entity.
    assert decoded.ownership_parties[0].party_type == "LEGAL_ENTITY"

    parties, relationships = derive_issuer_direct_ownership(GARDEN_BUSINESS_UEN)  # type: ignore[misc]
    assert [(p.party_id, p.party_type, p.registration_identifier) for p in parties] == [
        (SIM_LIM_UEN, "LEGAL_ENTITY", SIM_LIM_UEN),
        ("S9988776F", "NATURAL_PERSON", None),
    ]
    assert [
        (r.relationship_id, r.owned_entity_id, r.owner_party_id, r.ownership_percentage)
        for r in relationships
    ] == [
        ("REL_GARDEN_DIRECT_1", "ENTITY_11111999A", SIM_LIM_UEN, Decimal("62.500000")),
        ("REL_GARDEN_DIRECT_2", "ENTITY_11111999A", "S9988776F", Decimal("37.500000")),
    ]


def test_sim_lim_is_its_own_mock_issuer_with_own_direct_holders() -> None:
    connector = MockAcraConnector(clock=lambda: NOW)
    profile = connector.fetch_company(SIM_LIM_UEN)
    assert profile is not None
    assert (profile.uen, profile.entity_name, profile.entity_type) == (
        SIM_LIM_UEN,
        "SIM LIM PTE. LTD.",
        "PRIVATE_COMPANY_LIMITED_BY_SHARES",
    )
    parties = connector.fetch_ownership_parties(SIM_LIM_UEN)
    relationships = connector.fetch_relationships(SIM_LIM_UEN)
    assert parties.uen == relationships.uen == SIM_LIM_UEN
    assert [p.party_id for p in parties.ownership_parties] == [
        "S123AC1234E",
        "S2222222E",
        "S23BT2997U",
    ]
    assert "T16UF3333A" not in {p.party_id for p in parties.ownership_parties}
    assert [r.ownership_percentage for r in relationships.relationships] == [
        Decimal("81.818182"),
        Decimal("9.090909"),
        Decimal("9.090909"),
    ]
    assert {r.owned_entity_id for r in relationships.relationships} == {"ENTITY_111111111M"}
    # Garden's own response never contains SIM LIM's holders.
    garden = connector.fetch_ownership_parties(GARDEN_BUSINESS_UEN)
    assert [p.party_id for p in garden.ownership_parties] == [SIM_LIM_UEN, "S9988776F"]


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("shareType",), "Preference"),
        (("shareholderCategory",), "Trust"),
        (("status",), "Unknown"),
        (("shareAllotted",), 1.5),
        (("shareAllotted",), 0),
    ),
)
def test_synthetic_issuer_fixture_fails_closed_on_unsupported_semantics(
    path: tuple[str, ...], value: object
) -> None:
    body = deepcopy(SIM_LIM_MOCK_SHAREHOLDERS_BODY)
    body["entities"][0]["shareholders"]["individual"][1][path[0]] = value
    with pytest.raises((ValidationError, ValueError, AcraMalformedResponseError)):
        synthetic_issuer_shareholders(body, requested_uen=SIM_LIM_UEN)


def test_synthetic_issuer_fixture_rejects_identity_mismatch_and_groups() -> None:
    with pytest.raises((ValueError, AcraMalformedResponseError)):
        synthetic_issuer_shareholders(
            GARDEN_BUSINESS_MOCK_SHAREHOLDERS_BODY, requested_uen=SIM_LIM_UEN
        )
    grouped = deepcopy(GARDEN_BUSINESS_MOCK_SHAREHOLDERS_BODY)
    grouped["entities"][0]["shareholders"]["grouping"] = [
        grouped["entities"][0]["shareholders"]["individual"][0]
    ]
    with pytest.raises((ValidationError, ValueError, AcraMalformedResponseError)):
        synthetic_issuer_shareholders(grouped, requested_uen=GARDEN_BUSINESS_UEN)


def test_garden_onboarding_discovers_sim_lim_from_its_own_record_once() -> None:
    connector = CountingConnector(MockAcraConnector(clock=lambda: NOW))
    h = harness(connector)
    case = h.onboarding.create_staged_case(GARDEN_BUSINESS_UEN)
    assert case.registry_acquisition is not None
    assert [p.party_id for p in case.registry_acquisition.ownership_parties] == [
        SIM_LIM_UEN,
        "S9988776F",
    ]
    assert connector.issuer_calls(SIM_LIM_UEN) == 0

    h.ownership.load(case_id=case.case_id)
    record = h.ownership.analyze(case_id=case.case_id)

    assert connector.calls[(SIM_LIM_UEN, "company")] == 1
    assert connector.calls[(SIM_LIM_UEN, "parties")] == 1
    assert connector.calls[(SIM_LIM_UEN, "relationships")] == 1
    assert connector.issuer_calls(SIM_LIM_UEN) == 4
    assert connector.issuer_calls(GARDEN_BUSINESS_UEN) == 4
    assert record.state == OwnershipAnalysisState.ANALYZED
    root_edge = next(
        edge for edge in record.relationships if edge.child_party_id == SIM_LIM_UEN
    )
    assert root_edge.parent_party_id == f"ENTITY_{GARDEN_BUSINESS_UEN}"
    assert root_edge.ownership_percent == Decimal("62.500000")
    assert root_edge.basis == OwnershipBasis.SHARE_OWNERSHIP
    sim_lim_edges = sorted(
        (edge.child_party_id, edge.ownership_percent)
        for edge in record.relationships
        if edge.parent_party_id == SIM_LIM_UEN
    )
    assert sim_lim_edges == [
        ("111111111M.S123AC1234E", Decimal("81.818182")),
        ("111111111M.S2222222E", Decimal("9.090909")),
        ("111111111M.S23BT2997U", Decimal("9.090909")),
    ]
    candidates = by_name(record)
    assert candidates["ABCD123"].aggregated_ownership_percent == Decimal("51.13636375")
    assert candidates["LIM CHOON HUAT"].direct_ownership_percent == Decimal("37.500000")
    assert candidates["TAN WEI LING"].aggregated_ownership_percent == Decimal("5.681818125")
    assert candidates["EFGH2345"].aggregated_ownership_percent == Decimal("5.681818125")
    assert candidates["ABCD123"].classification == (
        OwnershipCandidateClassification.PROVISIONAL_UBO_CANDIDATE
    )
    assert candidates["LIM CHOON HUAT"].classification == (
        OwnershipCandidateClassification.PROVISIONAL_UBO_CANDIDATE
    )
    assert candidates["TAN WEI LING"].classification == (
        OwnershipCandidateClassification.BELOW_PROVISIONAL_THRESHOLD
    )
    assert len(candidates["ABCD123"].paths) == 1
    audit = record.discovery
    assert audit is not None
    assert audit.graph_complete is True
    assert audit.classification_certainty == "COMPLETE"
    assert (audit.registry_lookups, audit.provider_backed_lookups, audit.cache_hits) == (1, 1, 0)
    assert [
        (r.registration_number, r.outcome, r.depth, r.max_effective_percent)
        for r in audit.records
    ] == [(SIM_LIM_UEN, OwnershipDiscoveryOutcome.FETCHED, 1, Decimal("62.500000"))]
    # Every attached edge keeps truthful synthetic Mock provenance.
    assert {edge.provenance.environment.value for edge in record.relationships} == {"MOCK"}


def test_second_garden_case_uses_fresh_sim_lim_snapshot_with_zero_calls() -> None:
    connector = CountingConnector(MockAcraConnector(clock=lambda: NOW))
    h = harness(connector)
    h.analyze(GARDEN_BUSINESS_UEN)
    before = Counter(connector.calls)

    second = h.analyze(GARDEN_BUSINESS_UEN)

    assert connector.calls == before
    assert outcomes(second) == {SIM_LIM_UEN: OwnershipDiscoveryOutcome.CACHE_HIT}
    assert second.discovery is not None
    assert (second.discovery.provider_backed_lookups, second.discovery.cache_hits) == (0, 1)
    assert by_name(second)["ABCD123"].aggregated_ownership_percent == Decimal("51.13636375")


def test_expired_sim_lim_snapshot_is_refetched_once_and_saved() -> None:
    clock = Clock()
    connector = CountingConnector(MockAcraConnector(clock=clock))
    h = harness(connector, clock=clock)
    h.analyze(GARDEN_BUSINESS_UEN)
    clock.now = NOW + timedelta(days=90)

    refreshed = h.analyze(GARDEN_BUSINESS_UEN)

    assert connector.issuer_calls(SIM_LIM_UEN) == 8
    assert outcomes(refreshed) == {SIM_LIM_UEN: OwnershipDiscoveryOutcome.FETCHED}
    key = RegistryCacheKey(provider_identity=identity(), normalized_identifier=SIM_LIM_UEN)
    entry = h.repository.get(key)
    assert entry is not None and entry.revision == 1


def test_historical_policy_snapshot_never_fetches_subsidiaries() -> None:
    connector = CountingConnector(MockAcraConnector(clock=lambda: NOW))
    record = harness(connector, discovery=None).analyze(GARDEN_BUSINESS_UEN)

    assert connector.issuer_calls(SIM_LIM_UEN) == 0
    assert record.discovery is None
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert OwnershipIssueCode.INCOMPLETE_LEGAL_ENTITY in codes(record)
    assert all(
        item.threshold_result == OwnershipThresholdResult.INDETERMINATE
        for item in record.candidates
    )


class FlattenedGardenConnector(MockAcraConnector):
    """The pre-V2 local fixture shape, used only to seed an obsolete V1 cache entry."""

    def fetch_ownership_parties(self, uen: str) -> AcraOwnershipPartiesPayload:
        payload = super().fetch_ownership_parties(uen)
        if uen != GARDEN_BUSINESS_UEN:
            return payload
        return payload.model_copy(update={"ownership_parties": derive_garden_ownership()[0]})

    def fetch_relationships(self, uen: str) -> AcraRelationshipsPayload:
        payload = super().fetch_relationships(uen)
        if uen != GARDEN_BUSINESS_UEN:
            return payload
        return payload.model_copy(update={"relationships": derive_garden_ownership()[1]})


def test_old_flattened_v1_cache_is_isolated_and_never_double_counted() -> None:
    repository = InMemoryRegistrySnapshotRepository()
    legacy_adapter = AcraRegistryProviderAdapter(
        FlattenedGardenConnector(clock=lambda: NOW),
        cache_identity=identity("MOCK_ACRA_SYNTHETIC_V1"),
    )
    legacy = RegistryAcquisitionCoordinator(
        repository,
        RegistryFreshnessPolicy.model_validate({"duration_seconds": 7_776_000}),
        clock=lambda: NOW,
    ).acquire(legacy_adapter, GARDEN_BUSINESS_UEN)
    assert legacy.acquisition is not None and len(legacy.acquisition.ownership_parties) == 5

    connector = CountingConnector(MockAcraConnector(clock=lambda: NOW))
    h = harness(connector, repository=repository)
    case = h.onboarding.create_staged_case(GARDEN_BUSINESS_UEN)

    assert connector.issuer_calls(GARDEN_BUSINESS_UEN) == 4
    assert case.registry_acquisition is not None
    assert len(case.registry_acquisition.ownership_parties) == 2
    h.ownership.load(case_id=case.case_id)
    record = h.ownership.analyze(case_id=case.case_id)
    abcd = by_name(record)["ABCD123"]
    assert abcd.aggregated_ownership_percent == Decimal("51.13636375")
    assert len(abcd.paths) == 1
    assert sum(1 for item in record.candidates if item.party.display_name == "ABCD123") == 1


# --- B. Decimal aggregation and identity binding -------------------------------


def two_branch_registry(**extra: Issuer) -> dict[str, Issuer]:
    return {
        ROOT: Issuer("ROOT CO", (company("300000001B", "50"), company("300000002C", "50"))),
        **extra,
    }


def test_same_source_person_in_two_issuers_is_not_merged_without_binding() -> None:
    record = synthetic(
        two_branch_registry(
            **{
                "300000001B": Issuer("B CO", (person("P", "30"), person("X", "70"))),
                "300000002C": Issuer("C CO", (person("P", "30"), person("Y", "70"))),
            }
        )
    ).analyze(ROOT)

    p_nodes = sorted(
        item.party.party_id for item in record.candidates if item.party.party_id.endswith(".P")
    )
    assert p_nodes == ["300000001B.P", "300000002C.P"]
    assert OwnershipIssueCode.PERSON_IDENTITY_UNRESOLVED in codes(record)
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert record.discovery is not None
    assert record.discovery.classification_certainty == "UNCERTAIN"


def test_verified_person_binding_aggregates_fifteen_plus_fifteen() -> None:
    record = synthetic(
        two_branch_registry(
            **{
                "300000001B": Issuer("B CO", (person("P", "30"), person("X", "70"))),
                "300000002C": Issuer("C CO", (person("P", "30"), person("Y", "70"))),
            }
        ),
        bindings=(
            VerifiedPersonBinding("300000001B", "P", "VERIFIED-PERSON-1"),
            VerifiedPersonBinding("300000002C", "P", "VERIFIED-PERSON-1"),
        ),
    ).analyze(ROOT)

    p = next(item for item in record.candidates if item.party.party_id.endswith(".P"))
    assert p.indirect_ownership_percent == Decimal("30.00")
    assert p.aggregated_ownership_percent == Decimal("30")
    assert len(p.paths) == 2
    assert p.classification == OwnershipCandidateClassification.PROVISIONAL_UBO_CANDIDATE
    assert record.state == OwnershipAnalysisState.ANALYZED


def test_verified_binding_combines_twenty_direct_and_ten_indirect() -> None:
    record = synthetic(
        {
            ROOT: Issuer(
                "ROOT CO",
                (person("P", "20"), company("300000001B", "50"), person("Z", "30")),
            ),
            "300000001B": Issuer("B CO", (person("P", "20"), person("W", "80"))),
        },
        bindings=(
            VerifiedPersonBinding(ROOT, "P", "VERIFIED-PERSON-2"),
            VerifiedPersonBinding("300000001B", "P", "VERIFIED-PERSON-2"),
        ),
    ).analyze(ROOT)

    p = next(item for item in record.candidates if item.party.party_id == "P")
    assert p.direct_ownership_percent == Decimal("20")
    assert p.indirect_ownership_percent == Decimal("10.00")
    assert p.aggregated_ownership_percent == Decimal("30.00")
    assert p.threshold_result == OwnershipThresholdResult.MET


def test_binding_for_another_issuer_cannot_alias_a_person() -> None:
    record = synthetic(
        {
            ROOT: Issuer("ROOT CO", (person("P", "20"), company("300000001B", "80"))),
            "300000001B": Issuer("B CO", (person("P", "10"), person("W", "90"))),
        },
        bindings=(
            VerifiedPersonBinding(ROOT, "P", "VERIFIED-PERSON-3"),
            VerifiedPersonBinding("399999999Z", "P", "VERIFIED-PERSON-3"),
        ),
    ).analyze(ROOT)

    assert {item.party.party_id for item in record.candidates} >= {"P", "300000001B.P"}
    assert OwnershipIssueCode.PERSON_IDENTITY_UNRESOLVED in codes(record)


def test_same_display_name_with_different_identifiers_stays_distinct() -> None:
    record = synthetic(
        two_branch_registry(
            **{
                "300000001B": Issuer("B CO", (person("P1", "100"),)),
                "300000002C": Issuer("C CO", (person("P2", "100"),)),
            }
        )
    ).analyze(ROOT)
    assert record.state == OwnershipAnalysisState.ANALYZED
    assert len(record.candidates) == 2
    assert {item.aggregated_ownership_percent for item in record.candidates} == {Decimal("50")}


def test_exact_twenty_five_percent_indirect_is_inclusive() -> None:
    record = synthetic(
        {
            ROOT: Issuer("ROOT CO", (company("300000001B", "50"), person("Q", "50"))),
            "300000001B": Issuer("B CO", (person("P", "50"), person("R", "50"))),
        }
    ).analyze(ROOT)
    p = by_name(record)["SYNTHETIC P"]
    assert p.aggregated_ownership_percent == Decimal("25.00")
    assert p.classification == OwnershipCandidateClassification.PROVISIONAL_UBO_CANDIDATE


def test_diamond_reaches_one_issuer_twice_with_one_acquisition() -> None:
    h = synthetic(
        {
            ROOT: Issuer("ROOT CO", (company("300000001B", "40"), company("300000002C", "60"))),
            "300000001B": Issuer("B CO", (company("300000003D", "50"), person("X", "50"))),
            "300000002C": Issuer("C CO", (company("300000003D", "50"), person("Y", "50"))),
            "300000003D": Issuer("D CO", (person("Q", "100"),)),
        }
    )
    record = h.analyze(ROOT)
    q = by_name(record)["SYNTHETIC Q"]
    assert len(q.paths) == 2
    assert q.aggregated_ownership_percent == Decimal("50.0000")
    assert h.connector.issuer_calls("300000003D") == 4
    assert record.discovery is not None and record.discovery.registry_lookups == 3
    assert record.state == OwnershipAnalysisState.ANALYZED


# --- C. Topology, depth, cycles and limits --------------------------------------


def chain(length: int) -> dict[str, Issuer]:
    uens = [ROOT, *(f"30000001{index}{chr(65 + index)}" for index in range(1, length + 1))]
    issuers = {
        uen: Issuer(f"LEVEL {index}", (company(uens[index + 1], "100"),))
        for index, uen in enumerate(uens[:-1])
    }
    issuers[uens[-1]] = Issuer(f"LEVEL {length}", (person("P", "100"),))
    return issuers


def test_depth_five_issuers_are_fetched_and_depth_six_stays_unresolved() -> None:
    h = synthetic(chain(6))
    record = h.analyze(ROOT)
    found = outcomes(record)
    assert list(found.values()).count(OwnershipDiscoveryOutcome.FETCHED) == 5
    assert found["300000016G"] == OwnershipDiscoveryOutcome.DEPTH_LIMIT
    assert h.connector.issuer_calls("300000016G") == 0
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert {
        OwnershipIssueCode.INCOMPLETE_LEGAL_ENTITY,
        OwnershipIssueCode.CORPORATE_OWNERSHIP_UNRESOLVED,
    } <= codes(record)
    assert OwnershipIssueCode.MAXIMUM_DEPTH_EXCEEDED not in codes(record)


def test_policy_depth_six_reaches_seven_edge_path_within_unchanged_limit() -> None:
    deeper = OwnershipDiscoveryPolicySnapshot(
        trace_threshold_percent=Decimal("10"),
        max_corporate_depth=6,
        call_budget_enabled=False,
        call_budget_max=10,
    )
    record = synthetic(chain(6), discovery=deeper).analyze(ROOT)
    assert record.state == OwnershipAnalysisState.ANALYZED
    assert len(record.candidates[0].paths[0].edges) == 7


def test_cycle_back_to_root_is_detected_without_refetching_root() -> None:
    h = synthetic(
        {
            ROOT: Issuer("ROOT CO", (company("300000001B", "60"), person("P", "40"))),
            "300000001B": Issuer("B CO", (company(ROOT, "50"), person("Q", "50"))),
        }
    )
    record = h.analyze(ROOT)
    assert h.connector.issuer_calls(ROOT) == 4
    assert OwnershipIssueCode.CYCLE_DETECTED in codes(record)
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert record.discovery is not None
    assert record.discovery.classification_certainty == "UNCERTAIN"


def test_fan_out_hits_technical_ceiling_even_with_business_budget_disabled() -> None:
    owners = [f"3000{index:05d}X" for index in range(1, 41)]
    issuers = {ROOT: Issuer("ROOT CO", tuple(company(uen, "2.5") for uen in owners))}
    issuers.update({uen: Issuer(f"OWNER {uen}", (person(f"P{uen}", "100"),)) for uen in owners})
    record = synthetic(issuers).analyze(ROOT)
    found = list(outcomes(record).values())
    assert record.discovery is not None and record.discovery.registry_lookups == 32
    assert found.count(OwnershipDiscoveryOutcome.FETCHED) == 32
    assert found.count(OwnershipDiscoveryOutcome.HARD_LIMIT) == 8
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED


@pytest.mark.parametrize(("budget", "fetched", "limited"), ((2, 2, 1), (3, 3, 0)))
def test_enabled_business_budget_counts_provider_backed_acquisitions(
    budget: int, fetched: int, limited: int
) -> None:
    capped = OwnershipDiscoveryPolicySnapshot(
        trace_threshold_percent=Decimal("10"),
        max_corporate_depth=5,
        call_budget_enabled=True,
        call_budget_max=budget,
    )
    issuers = {
        ROOT: Issuer(
            "ROOT CO",
            (
                company("300000001B", "30"),
                company("300000002C", "30"),
                company("300000003D", "30"),
                person("P", "10"),
            ),
        ),
        **{
            uen: Issuer(f"{uen} CO", (person(f"H{uen}", "100"),))
            for uen in ("300000001B", "300000002C", "300000003D")
        },
    }
    record = synthetic(issuers, discovery=capped).analyze(ROOT)
    found = list(outcomes(record).values())
    assert found.count(OwnershipDiscoveryOutcome.FETCHED) == fetched
    assert found.count(OwnershipDiscoveryOutcome.BUSINESS_BUDGET) == limited
    assert record.state == (
        OwnershipAnalysisState.ANALYZED if limited == 0 else OwnershipAnalysisState.REVIEW_REQUIRED
    )


def test_small_branch_is_deferred_only_under_a_proved_bound_and_stays_reviewed() -> None:
    h = synthetic(
        {
            ROOT: Issuer(
                "ROOT CO",
                (person("P", "80"), company("300000001B", "5"), person("Q", "15")),
            ),
            "300000001B": Issuer("B CO", (person("H", "100"),)),
        }
    )
    record = h.analyze(ROOT)
    assert h.connector.issuer_calls("300000001B") == 0
    assert outcomes(record) == {
        "300000001B": OwnershipDiscoveryOutcome.DEFERRED_BELOW_TRACE_THRESHOLD
    }
    audit = record.discovery
    assert audit is not None
    assert audit.graph_complete is False
    assert audit.classification_certainty == "BOUNDED_NO_THRESHOLD_CHANGE"
    assert audit.unresolved_upper_bound_percent == Decimal("5")
    assert audit.records[0].max_effective_percent == Decimal("5")
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert all(
        item.classification == OwnershipCandidateClassification.REVIEW_REQUIRED
        for item in record.candidates
    )


def test_several_small_branches_that_could_qualify_together_are_expanded() -> None:
    small = ("300000001B", "300000002C", "300000003D")
    h = synthetic(
        {
            ROOT: Issuer("ROOT CO", (*(company(uen, "9") for uen in small), person("P", "73"))),
            **{uen: Issuer(f"{uen} CO", (person(f"H{uen}", "100"),)) for uen in small},
        }
    )
    record = h.analyze(ROOT)
    assert all(h.connector.issuer_calls(uen) == 4 for uen in small)
    assert record.state == OwnershipAnalysisState.ANALYZED


def test_small_branch_that_could_lift_a_known_person_is_expanded() -> None:
    h = synthetic(
        {
            ROOT: Issuer(
                "ROOT CO",
                (person("P", "20"), company("300000001B", "8"), person("Z", "72")),
            ),
            "300000001B": Issuer("B CO", (person("H", "100"),)),
        }
    )
    record = h.analyze(ROOT)
    assert h.connector.issuer_calls("300000001B") == 4
    assert outcomes(record) == {"300000001B": OwnershipDiscoveryOutcome.FETCHED}


def test_exactly_ten_percent_branch_meets_trace_threshold() -> None:
    h = synthetic(
        {
            ROOT: Issuer("ROOT CO", (company("300000001B", "10"), person("P", "90"))),
            "300000001B": Issuer("B CO", (person("H", "100"),)),
        }
    )
    record = h.analyze(ROOT)
    assert outcomes(record) == {"300000001B": OwnershipDiscoveryOutcome.FETCHED}
    assert record.state == OwnershipAnalysisState.ANALYZED


class SteppingReader:
    """Advance the discovery clock after each acquisition to cross the deadline."""

    def __init__(self, inner: OnboardingService, ticks: list[float]) -> None:
        self.inner = inner
        self.ticks = ticks

    def acquire_subsidiary_registry_evidence(self, identifier: str, **kwargs: Any) -> Any:
        result = self.inner.acquire_subsidiary_registry_evidence(identifier, **kwargs)
        self.ticks[0] += 61
        return result


def test_deadline_stops_further_issuer_acquisition() -> None:
    ticks = [0.0]
    issuers = {
        ROOT: Issuer("ROOT CO", (company("300000001B", "50"), company("300000002C", "50"))),
        "300000001B": Issuer("B CO", (person("H1", "100"),)),
        "300000002C": Issuer("C CO", (person("H2", "100"),)),
    }
    h = synthetic(
        issuers,
        reader_wrapper=lambda onboarding: SteppingReader(onboarding, ticks),
        coordinator_options={"clock": lambda: ticks[0]},
    )
    record = h.analyze(ROOT)
    assert h.connector.issuer_calls("300000002C") == 0
    assert record.discovery is not None
    hard = [
        r for r in record.discovery.records if r.outcome == OwnershipDiscoveryOutcome.HARD_LIMIT
    ]
    assert [r.reason_code for r in hard] == ["DISCOVERY_DEADLINE"]


# --- D. Provider, cache and source failures ------------------------------------


def test_unverified_and_foreign_corporate_owners_are_never_sent_to_acra() -> None:
    h = synthetic(
        {
            ROOT: Issuer(
                "ROOT CO",
                (
                    ("HOLD_SYN", "C", "30", "SYN-HOLD", "SG"),
                    company("300000009Z", "30", country="MY"),
                    person("P", "40"),
                ),
            ),
        }
    )
    record = h.analyze(ROOT)
    assert outcomes(record) == {
        "SYN-HOLD": OwnershipDiscoveryOutcome.UNVERIFIED_UEN,
        "300000009Z": OwnershipDiscoveryOutcome.FOREIGN_UNSUPPORTED,
    }
    assert h.connector.issuer_calls("300000009Z") == 0
    assert record.discovery is not None and record.discovery.registry_lookups == 0
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED


@pytest.mark.parametrize(
    ("issuer", "failing", "expected"),
    (
        (None, False, OwnershipDiscoveryOutcome.NOT_FOUND),
        (Issuer("B CO", (person("H", "100"),)), True, OwnershipDiscoveryOutcome.PROVIDER_FAILED),
        (Issuer("B CO", ()), False, OwnershipDiscoveryOutcome.PROVIDER_PARTIAL),
        (
            Issuer("B LLP", (person("H", "100"),), entity_type="LIMITED LIABILITY PARTNERSHIP"),
            False,
            OwnershipDiscoveryOutcome.UNSUPPORTED_LEGAL_FORM,
        ),
    ),
)
def test_unsupported_or_failed_issuer_lookup_is_a_partial_reviewed_branch(
    issuer: Issuer | None, failing: bool, expected: OwnershipDiscoveryOutcome
) -> None:
    issuers = {ROOT: Issuer("ROOT CO", (company("300000001B", "60"), person("P", "40")))}
    if issuer is not None:
        issuers["300000001B"] = issuer
    h = synthetic(issuers)
    if failing:
        h.connector.failing_relationships.add("300000001B")
    record = h.analyze(ROOT)
    assert outcomes(record) == {"300000001B": expected}
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert OwnershipIssueCode.CORPORATE_OWNERSHIP_UNRESOLVED in codes(record)
    assert record.discovery is not None and record.discovery.graph_complete is False


class CorruptForOne(InMemoryRegistrySnapshotRepository):
    def __init__(self, uen: str) -> None:
        super().__init__()
        self.uen = uen

    def get(self, key: RegistryCacheKey) -> RegistrySnapshotEntry | None:
        if key.normalized_identifier == self.uen:
            raise RegistrySnapshotRepositoryInvalidError
        return super().get(key)


def test_corrupt_subsidiary_cache_fails_closed_without_provider_call() -> None:
    issuers = {
        ROOT: Issuer("ROOT CO", (company("300000001B", "60"), person("P", "40"))),
        "300000001B": Issuer("B CO", (person("H", "100"),)),
    }
    h = synthetic(issuers, repository=CorruptForOne("300000001B"))
    record = h.analyze(ROOT)
    assert h.connector.issuer_calls("300000001B") == 0
    assert record.discovery is not None
    assert [(r.outcome, r.reason_code) for r in record.discovery.records] == [
        (OwnershipDiscoveryOutcome.CACHE_FAILURE, "REGISTRY_CACHE_INVALID")
    ]
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED


class StaleAfterAcquisition:
    """Report a different case identity once a subsidiary acquisition has run."""

    def __init__(self, inner: OnboardingService, state: dict[str, bool]) -> None:
        self._inner = inner
        self._state = state

    def get_case(self, case_id: UUID) -> OnboardingCase | None:
        case = self._inner.get_case(case_id)
        if case is not None and self._state.get("acquired"):
            return case.model_copy(update={"requested_uen": "300000777A"})
        return case

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class FlaggingReader:
    def __init__(self, inner: OnboardingService, state: dict[str, bool]) -> None:
        self._inner = inner
        self._state = state

    def acquire_subsidiary_registry_evidence(self, identifier: str, **kwargs: Any) -> Any:
        result = self._inner.acquire_subsidiary_registry_evidence(identifier, **kwargs)
        self._state["acquired"] = True
        return result


def test_identity_change_during_slow_acquisition_commits_no_derived_analysis() -> None:
    state: dict[str, bool] = {}
    h = synthetic(
        {
            ROOT: Issuer("ROOT CO", (company("300000001B", "60"), person("P", "40"))),
            "300000001B": Issuer("B CO", (person("H", "100"),)),
        },
        reader_wrapper=lambda onboarding: FlaggingReader(onboarding, state),
        cases_wrapper=lambda onboarding: StaleAfterAcquisition(onboarding, state),
    )
    case = h.onboarding.create_staged_case(ROOT)
    with pytest.raises(OwnershipInfrastructureError) as failure:
        h.ownership.load(case_id=case.case_id)
    assert failure.value.code == "OWNERSHIP_SOURCE_STALE"
    retained = h.ownership._repository.get_for_case(case.case_id)  # noqa: SLF001
    assert retained is not None and retained.state == OwnershipAnalysisState.FAILED
    assert retained.candidates == [] and retained.relationships == []


def test_official_mock_local_supplement_is_never_a_discovery_source() -> None:
    from test_s2_ownership_intelligence import FIXED_TIME, Cases, official_garden_case

    case = official_garden_case().model_copy(update={"policy_snapshot": policy()})
    cases = Cases(case)
    lookups: list[str] = []

    class RefusingReader:
        def acquire_subsidiary_registry_evidence(self, identifier: str, **_: Any) -> Any:
            lookups.append(identifier)
            raise AssertionError("the local supplement must not trigger a lookup")

    service = OwnershipAnalysisService(
        cases=cases,
        provider=RegistryAcquisitionOwnershipProvider(
            cases, garden_supplement_enabled=True, clock=lambda: FIXED_TIME
        ),
        garden_supplement_enabled=True,
        discovery=OwnershipDiscoveryCoordinator(RefusingReader()),
        repository=InMemoryOwnershipAnalysisRepository(),
        threshold_percent=Decimal("25"),
        max_parties=100,
        max_relationships=200,
        max_depth=8,
        max_paths_per_candidate=64,
        max_total_paths=256,
        clock=lambda: FIXED_TIME,
    )
    service.load(case_id=case.case_id)
    analyzed = service.analyze(case_id=case.case_id)

    assert lookups == []
    assert analyzed.discovery is None
    assert analyzed.source_classification == "OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT"
    assert {edge.provenance.provider for edge in analyzed.relationships} == {
        "LOCAL_SYNTHETIC_SUPPLEMENT"
    }
    abcd = next(item for item in analyzed.candidates if item.party.party_id == "S123AC1234E")
    assert abcd.aggregated_ownership_percent == Decimal("51.13636375")
    assert len(abcd.paths) == 1


def test_subsidiary_evidence_interface_never_mutates_a_case() -> None:
    connector = CountingConnector(MockAcraConnector(clock=lambda: NOW))
    h = harness(connector)
    case = h.onboarding.create_staged_case(GARDEN_BUSINESS_UEN)
    before = h.onboarding.get_case(case.case_id)

    evidence = h.onboarding.acquire_subsidiary_registry_evidence(
        SIM_LIM_UEN, case_policy=RegistryPolicySnapshot(), policy_version=1
    )
    again = h.onboarding.acquire_subsidiary_registry_evidence(
        SIM_LIM_UEN, case_policy=RegistryPolicySnapshot(), policy_version=1
    )

    assert evidence.disposition == RegistryEvidenceDisposition.PROVIDER_FETCH
    assert evidence.provider_backed is True
    assert again.disposition == RegistryEvidenceDisposition.CACHE_HIT
    assert again.provider_backed is False
    assert connector.issuer_calls(SIM_LIM_UEN) == 4
    assert h.onboarding.get_case(case.case_id) == before
    with pytest.raises(ValueError):
        h.onboarding.acquire_subsidiary_registry_evidence(
            "SYN-NOT-A-UEN", case_policy=None, policy_version=0
        )
