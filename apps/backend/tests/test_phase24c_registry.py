"""Offline operation reuse and definitive negative-cache regression contracts."""

from datetime import timedelta

from test_phase16_registry_cache import (
    VALID_UEN,
    CountingAcraConnector,
    CountingRepository,
    MutableClock,
    identity,
)

from app.connectors.registry import AcraRegistryProviderAdapter
from app.domain.models import RegistryFreshnessPolicy
from app.services.registry_acquisition import RegistryAcquisitionCoordinator


def setup():
    clock = MutableClock()
    connector = CountingAcraConnector(clock)
    repository = CountingRepository()
    provider = AcraRegistryProviderAdapter(connector, clock=clock, cache_identity=identity())
    coordinator = RegistryAcquisitionCoordinator(repository, RegistryFreshnessPolicy(), clock=clock)
    return clock, connector, repository, provider, coordinator


def test_definitive_not_found_repeated_inside_ttl_does_not_call_provider():
    clock, connector, repository, provider, coordinator = setup()
    identifier = "209999999Z"
    assert coordinator.acquire(provider, identifier).acquisition is None
    before = dict(connector.calls)
    assert coordinator.acquire(provider, identifier).acquisition is None
    assert connector.calls == before
    clock.value += timedelta(seconds=600)
    assert coordinator.acquire(provider, identifier).acquisition is None
    assert connector.calls["ENTITY_PROFILE"] == 2


def test_failed_operation_refresh_reuses_only_successful_operations():
    clock, connector, repository, provider, coordinator = setup()
    connector.fail_operation = "RELATIONSHIPS"
    first = coordinator.acquire(provider, VALID_UEN)
    assert first.acquisition.status.value == "FAILED"
    connector.fail_operation = None
    before = dict(connector.calls)
    second = coordinator.acquire(provider, VALID_UEN)
    assert second.acquisition.status.value == "COMPLETE"
    for operation in ("ENTITY_PROFILE", "OFFICERS", "OWNERSHIP_PARTIES"):
        assert connector.calls[operation] == before[operation]
    assert connector.calls["RELATIONSHIPS"] == before["RELATIONSHIPS"] + 1


def test_approved_freshness_and_negative_ttls_are_frozen_per_request():
    from app.domain.policy import RegistryPolicySnapshot

    clock, connector, repository, provider, coordinator = setup()
    short = RegistryPolicySnapshot(freshness_seconds=60, negative_seconds=1)
    long = RegistryPolicySnapshot(freshness_seconds=120, negative_seconds=600)
    first = coordinator.acquire(provider, VALID_UEN, case_policy=short, policy_version=2)
    assert first.binding.freshness_policy.version == 2
    clock.value += timedelta(seconds=60)
    long_hit = coordinator.acquire(provider, VALID_UEN, case_policy=long, policy_version=3)
    assert connector.total_calls == 4
    assert long_hit.binding.freshness_policy.duration_seconds == 120
    coordinator.acquire(provider, VALID_UEN, case_policy=short, policy_version=2)
    assert connector.total_calls == 8
    missing = "209999999Z"
    coordinator.acquire(provider, missing, case_policy=short, policy_version=2)
    clock.value += timedelta(seconds=1)
    before = connector.total_calls
    coordinator.acquire(provider, missing, case_policy=long, policy_version=3)
    assert connector.total_calls == before
    coordinator.acquire(provider, missing, case_policy=short, policy_version=2)
    assert connector.total_calls == before + 1


def test_expiry_during_missing_operation_fetch_cannot_bind_stale_prefix():
    import pytest

    from app.domain.policy import RegistryPolicySnapshot
    from app.services.registry_acquisition import RegistryCacheInvalidError

    clock, connector, repository, provider, coordinator = setup()
    connector.fail_operation = "RELATIONSHIPS"
    policy = RegistryPolicySnapshot(freshness_seconds=60)
    first = coordinator.acquire(provider, VALID_UEN, case_policy=policy, policy_version=1)
    clock.value += timedelta(seconds=59)
    connector.fail_operation = None
    original = connector.fetch_relationships

    def slow(identifier):
        clock.value += timedelta(seconds=1)
        return original(identifier)

    connector.fetch_relationships = slow
    with pytest.raises(RegistryCacheInvalidError):
        coordinator.acquire(provider, VALID_UEN, case_policy=policy, policy_version=1)
    assert first.binding is None and coordinator.active_lock_count == 0
    assert repository.replaces == 0
    connector.fetch_relationships = original
    recovered = coordinator.acquire(provider, VALID_UEN, case_policy=policy, policy_version=1)
    assert recovered.binding is not None
    assert recovered.binding.freshness_anchor == clock.value


def test_repository_cannot_return_changed_negative_or_freshness_metadata():
    import pytest

    from app.services.registry_acquisition import RegistryCacheInvalidError

    clock, connector, repository, provider, coordinator = setup()
    original = repository.create

    def corrupt(entry):
        persisted = original(entry)
        return persisted.model_copy(
            update={
                "written_at": persisted.written_at + timedelta(seconds=1),
                "freshness_anchor": persisted.freshness_anchor + timedelta(seconds=1),
            }
        )

    repository.create = corrupt
    with pytest.raises(RegistryCacheInvalidError):
        coordinator.acquire(provider, "209999999Z")
    assert coordinator.active_lock_count == 0


def test_lock_capacity_timeout_and_cancellation_are_bounded_and_retire():
    from concurrent.futures import ThreadPoolExecutor

    import pytest

    from app.domain.models import RegistryCacheKey
    from app.services.registry_acquisition import RegistryAcquisitionBusyError

    clock, connector, repository, provider, _ = setup()
    coordinator = RegistryAcquisitionCoordinator(
        repository,
        RegistryFreshnessPolicy(),
        clock=clock,
        max_active_keys=1,
        max_users_per_key=2,
        wait_timeout_seconds=0.01,
    )
    key = RegistryCacheKey(provider_identity=identity(), normalized_identifier=VALID_UEN)
    with coordinator._key_lock(key.digest):
        with pytest.raises(RegistryAcquisitionBusyError):
            coordinator.acquire(provider, "202400002B")
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(coordinator.acquire, provider, VALID_UEN)
            with pytest.raises(RegistryAcquisitionBusyError):
                future.result(timeout=1)
        assert coordinator.active_lock_count == 1
    assert coordinator.active_lock_count == 0 and connector.total_calls == 0
    with pytest.raises(RegistryAcquisitionBusyError):
        coordinator.acquire(provider, VALID_UEN, cancelled=lambda: True)
    assert coordinator.active_lock_count == 0 and connector.total_calls == 0


def test_leader_cancellation_does_not_commit_provider_result():
    import pytest

    from app.services.registry_acquisition import RegistryAcquisitionBusyError

    clock, connector, repository, provider, coordinator = setup()
    checks = iter((False, False, False, True))
    with pytest.raises(RegistryAcquisitionBusyError):
        coordinator.acquire(provider, VALID_UEN, cancelled=lambda: next(checks))
    assert repository.creates == 0 and connector.total_calls == 4
    assert coordinator.active_lock_count == 0


def test_a_b_a_identifier_cache_isolation_and_offline_reuse():
    clock, connector, repository, provider, coordinator = setup()
    a = coordinator.acquire(provider, VALID_UEN)
    b = coordinator.acquire(provider, "202400002B")
    assert a.acquisition.requested_identifier != b.acquisition.requested_identifier
    connector.fail_operation = "ENTITY_PROFILE"
    before = connector.total_calls
    again = coordinator.acquire(provider, VALID_UEN)
    assert connector.total_calls == before
    assert again.acquisition == a.acquisition and again.binding.cache_id == a.binding.cache_id
    assert repository.creates == 2


def test_official_mock_normalized_cache_isolated_and_transport_free_on_hit():
    from phase13_test_settings import ordinary_test_settings
    from test_acra_api_marketplace_mock_connector import (
        COMPANY_BODY,
        SHAREHOLDERS_BODY,
        RecordingTransport,
        connector,
    )

    from app.composition import build_onboarding_service
    from app.connectors.acra_sandbox import AcraHttpResponse
    from app.services.registry_cache_repository import InMemoryRegistrySnapshotRepository

    settings = ordinary_test_settings(
        acra_connector_mode="api_marketplace_mock",
        registry_cache_mode="mock",
        registry_cache_freshness_seconds=7776000,
    )
    transport = RecordingTransport(
        [
            AcraHttpResponse(200, COMPANY_BODY),
            AcraHttpResponse(200, COMPANY_BODY),
            AcraHttpResponse(200, SHAREHOLDERS_BODY),
        ]
    )
    repository = InMemoryRegistrySnapshotRepository()
    service = build_onboarding_service(
        settings=settings,
        acra_connector=connector(transport),
        registry_snapshot_repository=repository,
    )
    first = service.create_staged_case(VALID_UEN)
    assert len(transport.calls) == 3
    assert first.registry_evidence_binding is None
    from app.domain.models import RegistryCacheKey

    provider_identity = identity().model_copy(
        update={"dataset_namespace": "ACRA_API_MARKETPLACE_MOCK_V1"}
    )
    key = RegistryCacheKey(provider_identity=provider_identity, normalized_identifier=VALID_UEN)
    stored = repository.get(key)
    assert stored is not None and stored.cache_schema_version == 2
    assert stored.acquisition.status.value == "PARTIAL"
    transport.error = RuntimeError("offline synthetic transport")
    second = service.create_staged_case(VALID_UEN)
    assert len(transport.calls) == 3
    assert second.registry_acquisition == first.registry_acquisition
    assert second.registry_evidence_binding is None
    assert repository.get(key.model_copy(update={"provider_identity": identity()})) is None


def test_just_verified_correction_reuses_one_acquisition_and_fresh_cache_correction_calls_zero():
    from test_phase16_registry_cache import build_cached_service

    clock, connector, _, _, _ = setup()
    service, coordinator, repository = build_cached_service(clock, connector)
    missing = service.create_staged_case("209999999Z")
    before = connector.total_calls
    repaired = service.repair_initial_identity_and_recheck(
        case_id=missing.case_id,
        actor_id="synthetic-operator",
        legal_name="Synthetic correction",
        registration_number=VALID_UEN,
        country_of_incorporation="SG",
        expected_case_event_count=len(missing.events),
        verify_registry=True,
    )
    assert repaired.registry_acquisition.requested_identifier == VALID_UEN
    assert connector.total_calls == before + 4  # one necessary acquisition, no immediate replay
    another = service.create_staged_case("209999999Z")
    before, reads = connector.total_calls, repository.reads
    repaired = service.repair_initial_identity_and_recheck(
        case_id=another.case_id,
        actor_id="synthetic-operator",
        legal_name="Synthetic correction",
        registration_number=VALID_UEN,
        country_of_incorporation="SG",
        expected_case_event_count=len(another.events),
        verify_registry=True,
    )
    assert connector.total_calls == before and repository.reads == reads + 1
    assert repaired.registry_evidence_binding.disposition.value == "CACHE_HIT"
    assert coordinator.active_lock_count == 0


def test_uncertain_failed_acquisition_cannot_poison_definitive_negative_cache():
    import pytest

    from app.connectors.errors import (
        AcraMalformedResponseError,
        AcraServiceUnavailableError,
        AcraTimeoutError,
    )

    clock, connector, repository, provider, coordinator = setup()
    original = connector.fetch_company
    for failure in (AcraTimeoutError, AcraMalformedResponseError, AcraServiceUnavailableError):

        def fail(identifier, failure=failure):
            connector._record("ENTITY_PROFILE")
            raise failure()

        connector.fetch_company = fail
        with pytest.raises(failure):
            coordinator.acquire(provider, VALID_UEN)
        assert repository.creates == 0 and coordinator.active_lock_count == 0
    connector.fetch_company = original
    assert coordinator.acquire(provider, VALID_UEN).binding is not None
    assert repository.creates == 1
