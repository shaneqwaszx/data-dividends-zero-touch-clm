"""Physical Mongo proofs for Phase 16 registry snapshot durability and isolation."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pymongo import MongoClient
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)

from app.composition import build_onboarding_service
from app.config import Settings
from app.connectors.acra import (
    AcraCompanyPayload,
    AcraOfficersPayload,
    AcraOwnershipPartiesPayload,
    AcraRelationshipsPayload,
)
from app.connectors.mock_acra import (
    MOCK_ACRA_DATASET_NAMESPACE,
    MockAcraConnector,
)
from app.connectors.registry import AcraRegistryProviderAdapter
from app.domain.models import (
    RegistryCacheKey,
    RegistryEvidenceDisposition,
    RegistryFreshnessPolicy,
    RegistryProviderIdentity,
    SourceEnvironment,
    SourceSystem,
)
from app.persistence.composition import build_persistence_bundle
from app.persistence.mongo_registry_cache_store import MongoRegistryCacheStore
from app.services.registry_acquisition import RegistryAcquisitionCoordinator
from app.services.registry_cache_repository import (
    RegistrySnapshotRepositoryConflictError,
    RegistrySnapshotRepositoryInvalidError,
)

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(
    not MONGO_URI,
    reason="PHASE12_MONGO_URI is not configured",
)
NOW = datetime(2026, 1, 2, 3, 4, 5, 123456, tzinfo=UTC)
VALID_UEN = "202400001A"


class MutableClock:
    def __init__(self, value: datetime = NOW) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


class CountingConnector:
    def __init__(self, clock: Callable[[], datetime]) -> None:
        self.delegate = MockAcraConnector(clock=clock)
        self.calls = 0

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        self.calls += 1
        return self.delegate.fetch_company(uen)

    def fetch_officers(self, uen: str) -> AcraOfficersPayload:
        self.calls += 1
        return self.delegate.fetch_officers(uen)

    def fetch_ownership_parties(self, uen: str) -> AcraOwnershipPartiesPayload:
        self.calls += 1
        return self.delegate.fetch_ownership_parties(uen)

    def fetch_relationships(self, uen: str) -> AcraRelationshipsPayload:
        self.calls += 1
        return self.delegate.fetch_relationships(uen)


@pytest.fixture
def isolated_settings() -> Iterator[Settings]:
    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p16")
    settings = Settings(
        _env_file=None,
        app_env="test",
        clm_persistence_mode="mongo",
        mongo_uri=MONGO_URI,
        mongo_database=database,
        registry_cache_mode="mock",
        registry_cache_freshness_seconds=7_776_000,
    )
    cleanup: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    try:
        yield settings
    finally:
        try:
            cleanup_ephemeral_mongo_database(cleanup, database)
        finally:
            cleanup.close()


def _identity() -> RegistryProviderIdentity:
    return RegistryProviderIdentity(
        provider=SourceSystem.ACRA,
        environment=SourceEnvironment.MOCK,
        acquisition_contract_version=(
            AcraRegistryProviderAdapter.ACQUISITION_CONTRACT_VERSION
        ),
        dataset_namespace=MOCK_ACRA_DATASET_NAMESPACE,
    )


def _provider(connector: CountingConnector, clock: MutableClock) -> AcraRegistryProviderAdapter:
    return AcraRegistryProviderAdapter(
        connector,
        clock=clock,
        cache_identity=_identity(),
    )


def _store(settings: Settings) -> tuple[MongoClient[dict[str, Any]], MongoRegistryCacheStore]:
    assert MONGO_URI is not None
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    store = MongoRegistryCacheStore(
        client,
        database=settings.mongo_database,
        collection=settings.mongo_registry_cache_collection,
    )
    store.initialize()
    return client, store


def test_physical_restart_preserves_microseconds_and_exact_expiry(
    isolated_settings: Settings,
) -> None:
    clock = MutableClock()
    first_client, first_store = _store(isolated_settings)
    first_connector = CountingConnector(clock)
    first = RegistryAcquisitionCoordinator(
        first_store,
        RegistryFreshnessPolicy(),
        clock=clock,
    ).acquire(_provider(first_connector, clock), VALID_UEN)
    assert first_connector.calls == 4
    assert first.binding is not None
    assert first.binding.freshness_anchor.microsecond == 123456
    key = first.binding.cache_key
    first_client.close()

    second_client, second_store = _store(isolated_settings)
    try:
        restored = second_store.get(key)
        assert restored is not None
        assert restored.freshness_anchor == NOW
        assert restored.acquisition.retrieved_at == NOW

        second_connector = CountingConnector(clock)
        coordinator = RegistryAcquisitionCoordinator(
            second_store,
            RegistryFreshnessPolicy(),
            clock=clock,
        )
        clock.value = NOW + timedelta(seconds=7_776_000) - timedelta(microseconds=1)
        hit = coordinator.acquire(_provider(second_connector, clock), VALID_UEN)
        assert second_connector.calls == 0
        assert hit.binding is not None
        assert hit.binding.disposition == RegistryEvidenceDisposition.CACHE_HIT
        assert hit.binding.freshness_anchor == NOW

        clock.value = NOW + timedelta(seconds=7_776_000)
        refreshed = coordinator.acquire(_provider(second_connector, clock), VALID_UEN)
        assert second_connector.calls == 4
        assert refreshed.binding is not None
        assert refreshed.binding.disposition == RegistryEvidenceDisposition.PROVIDER_FETCH
        assert refreshed.binding.cache_revision == 1
    finally:
        second_client.close()


def test_physical_expected_revision_cas_has_one_winner(
    isolated_settings: Settings,
) -> None:
    clock = MutableClock()
    first_client, first_store = _store(isolated_settings)
    second_client, second_store = _store(isolated_settings)
    try:
        connector = CountingConnector(clock)
        result = RegistryAcquisitionCoordinator(
            first_store,
            RegistryFreshnessPolicy(),
            clock=clock,
        ).acquire(_provider(connector, clock), VALID_UEN)
        assert result.binding is not None
        key = result.binding.cache_key
        first_copy = first_store.get(key)
        second_copy = second_store.get(key)
        assert first_copy is not None and second_copy is not None
        clock.value += timedelta(seconds=1)
        candidate = first_copy.model_copy(update={"written_at": clock.value}, deep=True)

        winner = first_store.replace(candidate, expected_revision=0)
        with pytest.raises(RegistrySnapshotRepositoryConflictError):
            second_store.replace(second_copy, expected_revision=0)

        assert winner.revision == 1
        assert second_store.get(key) == winner
    finally:
        first_client.close()
        second_client.close()


def test_enabled_startup_rejects_invalid_cache_but_disabled_mode_ignores_it(
    isolated_settings: Settings,
) -> None:
    assert MONGO_URI is not None
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    collection = client[isolated_settings.mongo_database][
        isolated_settings.mongo_registry_cache_collection
    ]
    collection.insert_one({"_id": "bad", "cache_schema_version": 999})
    invalid_store = MongoRegistryCacheStore(
        client,
        database=isolated_settings.mongo_database,
        collection=isolated_settings.mongo_registry_cache_collection,
    )
    with pytest.raises(RegistrySnapshotRepositoryInvalidError):
        invalid_store.initialize()

    disabled = isolated_settings.model_copy(
        update={"registry_cache_mode": "disabled", "registry_cache_freshness_seconds": None}
    )
    persistence = build_persistence_bundle(disabled)
    try:
        assert persistence.registry_snapshots is None
    finally:
        persistence.close()
        client.close()


def test_case_deletion_leaves_cache_and_restart_hits_without_provider(
    isolated_settings: Settings,
) -> None:
    first_persistence = build_persistence_bundle(isolated_settings)
    assert first_persistence.registry_snapshots is not None
    first_connector = CountingConnector(lambda: datetime.now(UTC))
    first_service = build_onboarding_service(
        settings=isolated_settings,
        acra_connector=first_connector,
        repository=first_persistence.onboarding,
        target_execution_repository=first_persistence.target_executions,
        registry_snapshot_repository=first_persistence.registry_snapshots,
    )
    created = first_service.create_staged_case(VALID_UEN)
    binding = created.registry_evidence_binding
    assert binding is not None
    assert first_connector.calls == 4
    first_persistence.deletion.discard(created.case_id)
    assert first_persistence.onboarding.get(created.case_id) is None
    assert first_persistence.registry_snapshots.get(binding.cache_key) is not None
    first_persistence.close()

    second_persistence = build_persistence_bundle(isolated_settings)
    try:
        assert second_persistence.registry_snapshots is not None
        second_connector = CountingConnector(lambda: datetime.now(UTC))
        second_service = build_onboarding_service(
            settings=isolated_settings,
            acra_connector=second_connector,
            repository=second_persistence.onboarding,
            target_execution_repository=second_persistence.target_executions,
            registry_snapshot_repository=second_persistence.registry_snapshots,
        )
        hit = second_service.create_staged_case(VALID_UEN)
        assert hit.registry_evidence_binding is not None
        assert hit.registry_evidence_binding.disposition == (
            RegistryEvidenceDisposition.CACHE_HIT
        )
        assert second_connector.calls == 0
    finally:
        second_persistence.close()


def test_exact_key_dataset_isolation_is_a_miss(isolated_settings: Settings) -> None:
    client, store = _store(isolated_settings)
    try:
        clock = MutableClock()
        connector = CountingConnector(clock)
        coordinator = RegistryAcquisitionCoordinator(
            store,
            RegistryFreshnessPolicy(),
            clock=clock,
        )
        coordinator.acquire(_provider(connector, clock), VALID_UEN)
        adjacent_key = RegistryCacheKey(
            provider_identity=_identity().model_copy(
                update={"dataset_namespace": "MOCK_ACRA_SYNTHETIC_V2"}
            ),
            normalized_identifier=VALID_UEN,
        )

        assert store.get(adjacent_key) is None
    finally:
        client.close()
