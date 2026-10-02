"""Focused Phase 16 Mock registry cache and freshness proofs."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event, Lock
from typing import cast

import pytest
from pydantic import ValidationError

from app.composition import build_onboarding_service
from app.config import Settings
from app.connectors.acra import (
    AcraCompanyPayload,
    AcraOfficersPayload,
    AcraOwnershipPartiesPayload,
    AcraRelationshipsPayload,
)
from app.connectors.errors import AcraServiceUnavailableError
from app.connectors.mock_acra import (
    MISSING_OWNERSHIP_UEN,
    MOCK_ACRA_DATASET_NAMESPACE,
    MockAcraConnector,
)
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.connectors.registry import AcraRegistryProviderAdapter, RegistryProviderRouter
from app.domain.models import (
    RegistryAcquisitionStatus,
    RegistryCacheKey,
    RegistryEvidenceDisposition,
    RegistryFreshnessPolicy,
    RegistryProviderIdentity,
    RegistrySnapshotEntry,
    SourceEnvironment,
    SourceSystem,
    WorkflowState,
)
from app.services.errors import OnboardingInfrastructureError
from app.services.onboarding import OnboardingService
from app.services.registry_acquisition import (
    RegistryAcquisitionCoordinator,
    RegistryCacheInvalidError,
)
from app.services.registry_cache_repository import (
    InMemoryRegistrySnapshotRepository,
    RegistrySnapshotRepository,
    RegistrySnapshotRepositoryConflictError,
    RegistrySnapshotRepositoryUnavailableError,
)
from app.services.repository import InMemoryOnboardingCaseRepository

START = datetime(2026, 1, 2, 3, 4, 5, 123456, tzinfo=UTC)
VALID_UEN = "202400001A"
SECOND_UEN = "202400007G"


class MutableClock:
    def __init__(self, value: datetime = START) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


class CountingAcraConnector:
    def __init__(
        self,
        clock: Callable[[], datetime],
        *,
        block_identifier: str | None = None,
    ) -> None:
        self.delegate = MockAcraConnector(clock=clock)
        self.calls = {
            "ENTITY_PROFILE": 0,
            "OFFICERS": 0,
            "OWNERSHIP_PARTIES": 0,
            "RELATIONSHIPS": 0,
        }
        self.fail_operation: str | None = None
        self.block_identifier = block_identifier
        self.entered = Event()
        self.release = Event()
        self._lock = Lock()

    def _record(self, operation: str) -> None:
        with self._lock:
            self.calls[operation] += 1

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        self._record("ENTITY_PROFILE")
        if self.fail_operation == "ENTITY_PROFILE":
            raise AcraServiceUnavailableError
        if uen == self.block_identifier:
            self.entered.set()
            if not self.release.wait(timeout=5):
                raise AssertionError("controlled registry release was not signalled")
        return self.delegate.fetch_company(uen)

    def fetch_officers(self, uen: str) -> AcraOfficersPayload:
        self._record("OFFICERS")
        if self.fail_operation == "OFFICERS":
            raise AcraServiceUnavailableError
        return self.delegate.fetch_officers(uen)

    def fetch_ownership_parties(self, uen: str) -> AcraOwnershipPartiesPayload:
        self._record("OWNERSHIP_PARTIES")
        if self.fail_operation == "OWNERSHIP_PARTIES":
            raise AcraServiceUnavailableError
        return self.delegate.fetch_ownership_parties(uen)

    def fetch_relationships(self, uen: str) -> AcraRelationshipsPayload:
        self._record("RELATIONSHIPS")
        if self.fail_operation == "RELATIONSHIPS":
            raise AcraServiceUnavailableError
        return self.delegate.fetch_relationships(uen)

    @property
    def total_calls(self) -> int:
        return sum(self.calls.values())


class CountingRepository(InMemoryRegistrySnapshotRepository):
    def __init__(self) -> None:
        super().__init__()
        self.reads = 0
        self.creates = 0
        self.replaces = 0

    def get(self, key: RegistryCacheKey) -> RegistrySnapshotEntry | None:
        self.reads += 1
        return super().get(key)

    def create(self, entry: RegistrySnapshotEntry) -> RegistrySnapshotEntry:
        self.creates += 1
        return super().create(entry)

    def replace(
        self, entry: RegistrySnapshotEntry, *, expected_revision: int
    ) -> RegistrySnapshotEntry:
        self.replaces += 1
        return super().replace(entry, expected_revision=expected_revision)


class ReadFailureRepository(CountingRepository):
    def get(self, key: RegistryCacheKey) -> RegistrySnapshotEntry | None:
        self.reads += 1
        raise RegistrySnapshotRepositoryUnavailableError


class WriteFailureRepository(CountingRepository):
    def create(self, entry: RegistrySnapshotEntry) -> RegistrySnapshotEntry:
        self.creates += 1
        raise RegistrySnapshotRepositoryUnavailableError


class ConflictRepository(CountingRepository):
    def create(self, entry: RegistrySnapshotEntry) -> RegistrySnapshotEntry:
        self.creates += 1
        raise RegistrySnapshotRepositoryConflictError


class WrongKeyRepository(CountingRepository):
    def __init__(self, entry: RegistrySnapshotEntry) -> None:
        super().__init__()
        self.entry = entry

    def get(self, key: RegistryCacheKey) -> RegistrySnapshotEntry | None:
        self.reads += 1
        return self.entry.model_copy(deep=True)


def identity(*, dataset: str = MOCK_ACRA_DATASET_NAMESPACE) -> RegistryProviderIdentity:
    return RegistryProviderIdentity(
        provider=SourceSystem.ACRA,
        environment=SourceEnvironment.MOCK,
        acquisition_contract_version=(
            AcraRegistryProviderAdapter.ACQUISITION_CONTRACT_VERSION
        ),
        dataset_namespace=dataset,
    )


def build_cached_service(
    clock: MutableClock,
    connector: CountingAcraConnector,
    repository: RegistrySnapshotRepository | None = None,
) -> tuple[OnboardingService, RegistryAcquisitionCoordinator, RegistrySnapshotRepository]:
    snapshots = repository or CountingRepository()
    provider = AcraRegistryProviderAdapter(
        connector,
        clock=clock,
        cache_identity=identity(),
    )
    coordinator = RegistryAcquisitionCoordinator(
        snapshots,
        RegistryFreshnessPolicy(),
        clock=clock,
    )
    service = OnboardingService(
        acra=None,
        registry_router=RegistryProviderRouter(provider),
        registry_acquisition_coordinator=coordinator,
        goldtier=MockGoldTierConnector(),
        repository=InMemoryOnboardingCaseRepository(),
        clock=clock,
    )
    return service, coordinator, snapshots


def test_configuration_is_disabled_by_default_and_exact_when_enabled() -> None:
    assert Settings(_env_file=None).registry_cache_mode == "disabled"
    enabled = Settings(
        _env_file=None,
        registry_cache_mode="mock",
        registry_cache_freshness_seconds=7_776_000,
    )
    assert enabled.registry_cache_freshness_seconds == 7_776_000

    with pytest.raises(ValidationError):
        Settings(_env_file=None, registry_cache_mode="mock")
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            registry_cache_mode="mock",
            registry_cache_freshness_seconds=7_775_999,
        )
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            acra_connector_mode="sandbox",
            registry_cache_mode="mock",
            registry_cache_freshness_seconds=7_776_000,
        )
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            registry_cache_mode="mock",
            registry_cache_freshness_seconds=7_776_000,
            mongo_registry_cache_collection="clm_case_snapshots",
        )


def test_enabled_mongo_cache_cannot_silently_fall_back_to_memory() -> None:
    settings = Settings(
        _env_file=None,
        clm_persistence_mode="mongo",
        mongo_uri="mongodb://not-used.invalid",
        registry_cache_mode="mock",
        registry_cache_freshness_seconds=7_776_000,
    )

    with pytest.raises(ValueError, match="requires its repository"):
        build_onboarding_service(
            settings=settings,
            acra_connector=MockAcraConnector(clock=lambda: START),
        )


def test_miss_then_hit_preserves_original_evidence_and_suppresses_provider() -> None:
    clock = MutableClock()
    connector = CountingAcraConnector(clock)
    service, coordinator, repository = build_cached_service(clock, connector)

    fetched = service.create_staged_case(VALID_UEN)
    clock.value += timedelta(hours=1)
    hit = service.create_staged_case(VALID_UEN)

    assert fetched.state == hit.state == WorkflowState.VALIDATED
    assert connector.total_calls == 4
    assert fetched.registry_evidence_binding is not None
    assert hit.registry_evidence_binding is not None
    assert fetched.registry_evidence_binding.disposition == (
        RegistryEvidenceDisposition.PROVIDER_FETCH
    )
    assert hit.registry_evidence_binding.disposition == RegistryEvidenceDisposition.CACHE_HIT
    assert fetched.registry_acquisition == hit.registry_acquisition
    assert hit.registry_acquisition is not fetched.registry_acquisition
    assert hit.registry_acquisition is not None
    assert hit.registry_acquisition.retrieved_at == START
    assert hit.registry_evidence_binding.bound_to_case_at == clock.value
    assert coordinator.active_lock_count == 0
    assert cast(CountingRepository, repository).creates == 1


@pytest.mark.parametrize(
    ("offset", "expected_calls", "expected_disposition"),
    [
        (
            timedelta(seconds=7_776_000) - timedelta(microseconds=1),
            4,
            RegistryEvidenceDisposition.CACHE_HIT,
        ),
        (
            timedelta(seconds=7_776_000),
            8,
            RegistryEvidenceDisposition.PROVIDER_FETCH,
        ),
    ],
)
def test_exact_expiry_boundary_is_exclusive(
    offset: timedelta,
    expected_calls: int,
    expected_disposition: RegistryEvidenceDisposition,
) -> None:
    clock = MutableClock()
    connector = CountingAcraConnector(clock)
    service, _, repository = build_cached_service(clock, connector)
    service.create_staged_case(VALID_UEN)

    clock.value = START + offset
    result = service.create_staged_case(VALID_UEN)

    assert connector.total_calls == expected_calls
    assert result.registry_evidence_binding is not None
    assert result.registry_evidence_binding.disposition == expected_disposition
    expected_replaces = 1 if expected_calls == 8 else 0
    assert cast(CountingRepository, repository).replaces == expected_replaces


@pytest.mark.parametrize(
    ("failed_operation", "expected_refresh_calls"),
    [
        ("ENTITY_PROFILE", 1),
        ("OFFICERS", 2),
        ("OWNERSHIP_PARTIES", 3),
        ("RELATIONSHIPS", 4),
    ],
)
def test_failed_refresh_stops_at_each_operation_and_retains_successful_prefix(
    failed_operation: str,
    expected_refresh_calls: int,
) -> None:
    clock = MutableClock()
    connector = CountingAcraConnector(clock)
    service, _, repository = build_cached_service(clock, connector)
    original = service.create_staged_case(VALID_UEN)
    key = original.registry_evidence_binding.cache_key  # type: ignore[union-attr]
    before = repository.get(key)
    assert before is not None

    clock.value += timedelta(seconds=7_776_000)
    connector.fail_operation = failed_operation
    if failed_operation == "ENTITY_PROFILE":
        with pytest.raises(OnboardingInfrastructureError) as raised:
            service.create_staged_case(VALID_UEN)
        failed = service.get_case(raised.value.case_id)
        assert failed is not None
    else:
        failed = service.create_staged_case(VALID_UEN)
    after = repository.get(key)

    assert failed.state == WorkflowState.FAILED
    if failed_operation == "ENTITY_PROFILE":
        assert failed.registry_acquisition is None
    else:
        assert failed.registry_acquisition is not None
        assert failed.registry_acquisition.status == RegistryAcquisitionStatus.FAILED
    assert failed.registry_evidence_binding is None
    if failed_operation == "ENTITY_PROFILE":
        assert after == before
    else:
        assert after is not None
        assert after.revision == before.revision + 1
        assert after.cache_schema_version == 2
        assert after.acquisition == failed.registry_acquisition
        assert after.freshness_anchor == clock.value
    assert connector.total_calls == 4 + expected_refresh_calls
    assert original.registry_acquisition is not None
    assert original.registry_acquisition.retrieved_at == START


def test_partial_bundle_reuses_successful_operations_without_complete_binding() -> None:
    clock = MutableClock()
    connector = CountingAcraConnector(clock)
    service, _, repository = build_cached_service(clock, connector)

    first = service.create_staged_case(MISSING_OWNERSHIP_UEN)
    second = service.create_staged_case(MISSING_OWNERSHIP_UEN)

    # Missing ownership does not invalidate canonical identity or make partial
    # registry evidence reusable as a complete cache entry.
    assert first.state == second.state == WorkflowState.VALIDATED
    assert first.registry_acquisition is not None
    assert second.registry_acquisition is not None
    assert first.registry_acquisition.status == RegistryAcquisitionStatus.PARTIAL
    assert second.registry_acquisition.status == RegistryAcquisitionStatus.PARTIAL
    assert first.registry_evidence_binding is second.registry_evidence_binding is None
    assert connector.total_calls == 6
    assert connector.calls["ENTITY_PROFILE"] == connector.calls["OFFICERS"] == 1
    assert connector.calls["OWNERSHIP_PARTIES"] == connector.calls["RELATIONSHIPS"] == 2
    assert cast(CountingRepository, repository).creates == 1
    assert cast(CountingRepository, repository).replaces == 1


@pytest.mark.parametrize(
    ("uen", "country"),
    [
        ("NOT-A-UEN", None),
        (VALID_UEN, "AU"),
        ("A123", "AU"),
    ],
)
def test_route_and_identifier_blockers_make_zero_cache_and_provider_calls(
    uen: str, country: str | None
) -> None:
    clock = MutableClock()
    connector = CountingAcraConnector(clock)
    service, _, repository = build_cached_service(clock, connector)

    service.create_staged_case(uen, country)

    assert connector.total_calls == 0
    assert cast(CountingRepository, repository).reads == 0


def test_future_operation_timestamp_fails_closed_without_provider_refresh() -> None:
    clock = MutableClock()
    connector = CountingAcraConnector(clock)
    service, _, repository = build_cached_service(clock, connector)
    fetched = service.create_staged_case(VALID_UEN)
    binding = fetched.registry_evidence_binding
    assert binding is not None
    entry = repository.get(binding.cache_key)
    assert entry is not None

    clock.value = START - timedelta(microseconds=1)
    with pytest.raises(OnboardingInfrastructureError) as raised:
        service.create_staged_case(VALID_UEN)

    assert raised.value.code == RegistryCacheInvalidError.code
    assert connector.total_calls == 4


def test_exact_key_fields_are_isolated_and_unknown_provider_is_rejected() -> None:
    clock = MutableClock()
    connector = CountingAcraConnector(clock)
    service, _, repository = build_cached_service(clock, connector)
    fetched = service.create_staged_case(VALID_UEN)
    binding = fetched.registry_evidence_binding
    assert binding is not None

    adjacent_keys = (
        binding.cache_key.model_copy(update={"normalized_identifier": SECOND_UEN}),
        RegistryCacheKey(
            provider_identity=identity(dataset="MOCK_ACRA_SYNTHETIC_V2"),
            normalized_identifier=VALID_UEN,
        ),
        RegistryCacheKey(
            provider_identity=identity().model_copy(
                update={"acquisition_contract_version": "PHASE10_ACQUISITION_V2"}
            ),
            normalized_identifier=VALID_UEN,
        ),
        RegistryCacheKey(
            provider_identity=identity().model_copy(
                update={"environment": SourceEnvironment.SANDBOX}
            ),
            normalized_identifier=VALID_UEN,
        ),
    )

    assert all(repository.get(key) is None for key in adjacent_keys)
    with pytest.raises(ValidationError):
        RegistryProviderIdentity.model_validate(
            {
                "provider": "FOREIGN_REGISTRY",
                "environment": "MOCK",
                "acquisition_contract_version": "PHASE10_ACQUISITION_V1",
                "dataset_namespace": MOCK_ACRA_DATASET_NAMESPACE,
            }
        )


def test_cache_read_failure_stops_before_provider_and_retains_no_evidence() -> None:
    clock = MutableClock()
    connector = CountingAcraConnector(clock)
    service, _, _ = build_cached_service(clock, connector, ReadFailureRepository())

    with pytest.raises(OnboardingInfrastructureError) as raised:
        service.create_staged_case(VALID_UEN)

    failed = service.get_case(raised.value.case_id)
    assert raised.value.code == "REGISTRY_CACHE_READ_FAILED"
    assert failed is not None
    assert failed.registry_acquisition is None
    assert failed.entity is None
    assert failed.registry_evidence_binding is None
    assert connector.total_calls == 0


def test_cache_write_failure_discards_uncommitted_complete_fetch() -> None:
    clock = MutableClock()
    connector = CountingAcraConnector(clock)
    service, _, _ = build_cached_service(clock, connector, WriteFailureRepository())

    with pytest.raises(OnboardingInfrastructureError) as raised:
        service.create_staged_case(VALID_UEN)

    failed = service.get_case(raised.value.case_id)
    assert raised.value.code == "REGISTRY_CACHE_WRITE_FAILED"
    assert failed is not None
    assert failed.registry_acquisition is None
    assert failed.entity is None
    assert failed.registry_evidence_binding is None
    assert connector.total_calls == 4


def test_cache_create_conflict_has_no_retry_or_uncommitted_case_evidence() -> None:
    clock = MutableClock()
    connector = CountingAcraConnector(clock)
    service, _, repository = build_cached_service(clock, connector, ConflictRepository())

    with pytest.raises(OnboardingInfrastructureError) as raised:
        service.create_staged_case(VALID_UEN)

    failed = service.get_case(raised.value.case_id)
    assert raised.value.code == "REGISTRY_CACHE_CONFLICT"
    assert failed is not None
    assert failed.registry_acquisition is None
    assert failed.entity is None
    assert failed.registry_evidence_binding is None
    assert connector.total_calls == 4
    assert cast(CountingRepository, repository).creates == 1


def test_repository_value_for_wrong_requested_key_is_corruption_not_a_miss() -> None:
    clock = MutableClock()
    seed_connector = CountingAcraConnector(clock)
    seed_service, _, seed_repository = build_cached_service(clock, seed_connector)
    seeded = seed_service.create_staged_case(VALID_UEN)
    binding = seeded.registry_evidence_binding
    assert binding is not None
    entry = seed_repository.get(binding.cache_key)
    assert entry is not None

    connector = CountingAcraConnector(clock)
    service, _, _ = build_cached_service(clock, connector, WrongKeyRepository(entry))
    with pytest.raises(OnboardingInfrastructureError) as raised:
        service.create_staged_case(SECOND_UEN)

    failed = service.get_case(raised.value.case_id)
    assert raised.value.code == "REGISTRY_CACHE_INVALID"
    assert failed is not None
    assert failed.registry_acquisition is None
    assert failed.entity is None
    assert failed.registry_evidence_binding is None
    assert connector.total_calls == 0


def test_same_key_concurrent_misses_single_flight_and_retire_lock() -> None:
    clock = MutableClock()
    connector = CountingAcraConnector(clock, block_identifier=VALID_UEN)
    service, coordinator, _ = build_cached_service(clock, connector)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(service.create_staged_case, VALID_UEN)
        assert connector.entered.wait(timeout=2)
        second = executor.submit(service.create_staged_case, VALID_UEN)
        connector.release.set()
        results = [first.result(timeout=5), second.result(timeout=5)]

    assert connector.total_calls == 4
    assert {item.registry_evidence_binding.disposition for item in results} == {
        RegistryEvidenceDisposition.PROVIDER_FETCH,
        RegistryEvidenceDisposition.CACHE_HIT,
    }
    assert results[0].registry_acquisition is not results[1].registry_acquisition
    assert coordinator.active_lock_count == 0


def test_different_keys_do_not_share_single_flight_lock() -> None:
    clock = MutableClock()
    connector = CountingAcraConnector(clock, block_identifier=VALID_UEN)
    service, coordinator, _ = build_cached_service(clock, connector)

    with ThreadPoolExecutor(max_workers=2) as executor:
        blocked = executor.submit(service.create_staged_case, VALID_UEN)
        assert connector.entered.wait(timeout=2)
        independent = executor.submit(service.create_staged_case, SECOND_UEN)
        second = independent.result(timeout=3)
        connector.release.set()
        first = blocked.result(timeout=5)

    assert first.state == second.state == WorkflowState.VALIDATED
    assert connector.total_calls == 8
    assert coordinator.active_lock_count == 0


def test_memory_restart_misses_and_case_mutation_cannot_change_shared_entry() -> None:
    clock = MutableClock()
    first_connector = CountingAcraConnector(clock)
    first_service, _, first_repository = build_cached_service(clock, first_connector)
    case = first_service.create_staged_case(VALID_UEN)
    binding = case.registry_evidence_binding
    assert binding is not None
    cached_before = first_repository.get(binding.cache_key)
    assert cached_before is not None

    case.entity.legal_name = "LOCAL MUTATION"  # type: ignore[union-attr,misc]
    assert first_repository.get(binding.cache_key) == cached_before

    restarted_connector = CountingAcraConnector(clock)
    restarted_service, _, _ = build_cached_service(clock, restarted_connector)
    restarted = restarted_service.create_staged_case(VALID_UEN)
    assert restarted.registry_evidence_binding is not None
    assert restarted.registry_evidence_binding.disposition == (
        RegistryEvidenceDisposition.PROVIDER_FETCH
    )
    assert restarted_connector.total_calls == 4
