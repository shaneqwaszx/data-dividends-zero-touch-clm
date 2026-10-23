"""Physical proof of recursive ownership persistence in a fresh allowlisted database."""

import os
from collections import Counter
from decimal import Decimal
from typing import Any

import pytest
from pymongo import MongoClient
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)
from test_ownership_discovery_policy import _legacy_catalogue_with_history

from app.composition import build_onboarding_service, build_ownership_analysis_service
from app.config import Settings
from app.connectors.garden_business import GARDEN_BUSINESS_UEN, SIM_LIM_UEN
from app.connectors.mock_acra import MOCK_ACRA_DATASET_NAMESPACE, MockAcraConnector
from app.domain.models import (
    RegistryCacheKey,
    RegistryProviderIdentity,
    SourceEnvironment,
    SourceSystem,
)
from app.domain.ownership import OwnershipAnalysisState, OwnershipDiscoveryOutcome
from app.persistence.composition import build_persistence_bundle
from app.services.policy_management import PolicyManagementService

URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not URI, reason="PHASE12_MONGO_URI is not configured")


class CountingConnector(MockAcraConnector):
    def __init__(self) -> None:
        super().__init__()
        self.calls: Counter[str] = Counter()

    def fetch_company(self, uen: str) -> Any:
        self.calls[uen] += 1
        return super().fetch_company(uen)


@pytest.fixture
def physical_settings():
    assert URI is not None
    database = generate_ephemeral_mongo_database("p16")
    settings = Settings(
        _env_file=None,
        app_env="test",
        clm_persistence_mode="mongo",
        mongo_uri=URI,
        mongo_database=database,
        registry_cache_mode="mock",
        registry_cache_freshness_seconds=7776000,
    )
    client: MongoClient[dict[str, Any]] = MongoClient(URI)
    try:
        client.admin.command("ping")
        yield settings, client
    finally:
        try:
            cleanup_ephemeral_mongo_database(client, database)
        finally:
            client.close()


def _services(settings: Settings, bundle: Any, connector: CountingConnector) -> tuple[Any, Any]:
    policy = PolicyManagementService(bundle.policies)
    cases = build_onboarding_service(
        settings=settings,
        acra_connector=connector,
        repository=bundle.onboarding,
        target_execution_repository=bundle.target_executions,
        registry_snapshot_repository=bundle.registry_snapshots,
        policy_snapshot_provider=policy.case_snapshot,
    )
    return cases, build_ownership_analysis_service(cases, settings, repository=bundle.ownership)


def test_garden_discovery_survives_restart_with_issuer_cache_and_v11_envelope(physical_settings):
    settings, client = physical_settings
    connector = CountingConnector()
    first = build_persistence_bundle(settings)
    try:
        cases, ownership = _services(settings, first, connector)
        case = cases.create_staged_case(GARDEN_BUSINESS_UEN)
        ownership.load(case_id=case.case_id)
        record = ownership.analyze(case_id=case.case_id)
        assert record.state == OwnershipAnalysisState.ANALYZED
        assert record.discovery is not None
        assert [item.outcome for item in record.discovery.records] == [
            OwnershipDiscoveryOutcome.FETCHED
        ]
        assert connector.calls[SIM_LIM_UEN] == 1
    finally:
        first.close()

    second = build_persistence_bundle(settings)
    try:
        cases, ownership = _services(settings, second, connector)
        restored = second.ownership.get_for_case(case.case_id)
        assert restored == record
        assert second.onboarding.get(case.case_id).policy_snapshot.ownership_discovery is not None
        raw = client[settings.mongo_database][settings.mongo_case_collection].find_one(
            {"_id": str(case.case_id)}
        )
        assert raw is not None and raw["schema_version"] == 11
        identity = RegistryProviderIdentity(
            provider=SourceSystem.ACRA,
            environment=SourceEnvironment.MOCK,
            acquisition_contract_version="PHASE10_ACQUISITION_V1",
            dataset_namespace=MOCK_ACRA_DATASET_NAMESPACE,
        )
        entry = second.registry_snapshots.get(
            RegistryCacheKey(provider_identity=identity, normalized_identifier=SIM_LIM_UEN)
        )
        assert entry is not None and entry.acquisition is not None
        assert entry.acquisition.requested_identifier == SIM_LIM_UEN

        again = cases.create_staged_case(GARDEN_BUSINESS_UEN)
        ownership.load(case_id=again.case_id)
        reused = ownership.analyze(case_id=again.case_id)
        assert connector.calls[SIM_LIM_UEN] == 1
        assert reused.discovery is not None
        assert [item.outcome for item in reused.discovery.records] == [
            OwnershipDiscoveryOutcome.CACHE_HIT
        ]
        abcd = next(i for i in reused.candidates if i.party.display_name == "ABCD123")
        assert abcd.aggregated_ownership_percent == Decimal("51.13636375")
    finally:
        second.close()


def test_history_bearing_catalogue_migrates_once_through_mongo(physical_settings):
    settings, _ = physical_settings
    legacy = _legacy_catalogue_with_history()
    first = build_persistence_bundle(settings)
    try:
        first.policies.create(legacy)
        migrated = PolicyManagementService(first.policies).catalogue()
        assert migrated.active_origin == "MIGRATED"
        assert migrated.catalogue_schema_version == 3
    finally:
        first.close()
    second = build_persistence_bundle(settings)
    try:
        restarted = PolicyManagementService(second.policies)
        assert restarted.catalogue() == migrated
        assert len(restarted.catalogue().rules) == 39
        assert restarted.case_snapshot().ownership_discovery is not None
    finally:
        second.close()
