"""Physical proof of recursive ownership persistence in a fresh allowlisted database."""

import os
from collections import Counter
from decimal import Decimal
from typing import Any

import pytest
from pydantic import SecretStr
from pymongo import MongoClient
from scripts.five_layer_hybrid_fixture import OfflineFiveLayerProtocolTransport
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)
from test_ownership_discovery_policy import _legacy_catalogue_with_history

from app.composition import build_onboarding_service, build_ownership_analysis_service
from app.config import Settings
from app.connectors.garden_business import GARDEN_BUSINESS_UEN, SIM_LIM_UEN
from app.connectors.hybrid_ownership_overlay import FIVE_LAYER_ROOT_UEN
from app.connectors.mock_acra import MOCK_ACRA_DATASET_NAMESPACE, MockAcraConnector
from app.domain.models import (
    RegistryCacheKey,
    RegistryProviderIdentity,
    SourceEnvironment,
    SourceSystem,
)
from app.domain.ownership import OwnershipAnalysisState, OwnershipDiscoveryOutcome
from app.persistence.composition import build_persistence_bundle
from app.persistence.errors import PersistenceDataInvalidError
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


def test_garden_discovery_survives_restart_with_issuer_cache_and_current_envelope(
    physical_settings,
):
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
        assert raw is not None and raw["schema_version"] == 13
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


def test_hybrid_five_layer_record_survives_restart_and_rejects_schema_eleven(physical_settings):
    settings, client = physical_settings
    hybrid = settings.model_copy(
        update={
            "acra_connector_mode": "api_marketplace_mock",
            "acra_marketplace_ownership_overlay": "hybrid_direct_overlay",
            "acra_api_marketplace_mock_client_id": SecretStr("synthetic-offline-client"),
            "acra_api_marketplace_mock_secret_key": SecretStr("synthetic-offline-key"),
        }
    )
    transport = OfflineFiveLayerProtocolTransport()

    def services(bundle: Any) -> tuple[Any, Any]:
        policy = PolicyManagementService(bundle.policies)
        cases = build_onboarding_service(
            settings=hybrid,
            acra_transport=transport,
            acra_marketplace_token_transport=transport,
            repository=bundle.onboarding,
            target_execution_repository=bundle.target_executions,
            registry_snapshot_repository=bundle.registry_snapshots,
            policy_snapshot_provider=policy.case_snapshot,
        )
        return cases, build_ownership_analysis_service(cases, hybrid, repository=bundle.ownership)

    first = build_persistence_bundle(hybrid)
    try:
        cases, ownership = services(first)
        case = cases.create_staged_case(FIVE_LAYER_ROOT_UEN)
        ownership.load(case_id=case.case_id)
        record = ownership.analyze(case_id=case.case_id)
        assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
        assert record.source_classification == "OFFICIAL_MOCK_PLUS_LOCAL_DIRECT_OVERLAY"
        assert record.discovery is not None and record.discovery.topology_complete is True
        first_gets = transport.get_count
    finally:
        first.close()

    second = build_persistence_bundle(hybrid)
    try:
        cases, ownership = services(second)
        assert second.ownership.get_for_case(case.case_id) == record
        collection = client[hybrid.mongo_database][hybrid.mongo_case_collection]
        raw = collection.find_one({"_id": str(case.case_id)})
        assert raw is not None and raw["schema_version"] == 13
        assert raw["ownership"]["discovery"]["overlay_scenario_id"] == (
            "FIVE_LAYER_MARKETPLACE_HYBRID_V1"
        )
        # Durable official-namespace snapshots and definitive negatives survive restart.
        again = cases.create_staged_case(FIVE_LAYER_ROOT_UEN)
        ownership.load(case_id=again.case_id)
        reused = ownership.analyze(case_id=again.case_id)
        assert transport.get_count == first_gets
        assert reused.discovery is not None and reused.discovery.cache_hits == 5
        # An exact schema-11 envelope can never carry hybrid evidence: fail closed.
        collection.update_one({"_id": str(case.case_id)}, {"$set": {"schema_version": 11}})
        with pytest.raises(PersistenceDataInvalidError):
            second.onboarding.get(case.case_id)
    finally:
        second.close()


def test_official_shareholder_evidence_survives_restart_and_rejects_schema_twelve(
    physical_settings,
):
    settings, client = physical_settings
    hybrid = settings.model_copy(
        update={
            "acra_connector_mode": "api_marketplace_mock",
            "acra_marketplace_ownership_overlay": "hybrid_direct_overlay",
            "acra_api_marketplace_mock_client_id": SecretStr("synthetic-offline-client"),
            "acra_api_marketplace_mock_secret_key": SecretStr("synthetic-offline-key"),
        }
    )
    transport = OfflineFiveLayerProtocolTransport()
    transport.shareholders[SIM_LIM_UEN] = {
        "entities": [
            {
                "uen": SIM_LIM_UEN,
                "name": "SIM LIM PTE. LTD.",
                "shareholders": {
                    "individual": [
                        {
                            "shareholderCategory": category,
                            "shareholderId": identifier,
                            "shareholderName": name,
                            "shareAllotted": units,
                            "status": status,
                        }
                        for category, identifier, name, units, status in (
                            ("Corporate", "SYN-SL-C1", "SYNTHETIC CORPORATE, INC.", 500, "Active"),
                            ("Individual", "SYN-SL-3", "SYNTHETIC HOLDER", 100, "Withdrawn"),
                        )
                    ],
                    "grouping": [],
                },
            }
        ]
    }

    def services(bundle: Any) -> tuple[Any, Any]:
        policy = PolicyManagementService(bundle.policies)
        cases = build_onboarding_service(
            settings=hybrid,
            acra_transport=transport,
            acra_marketplace_token_transport=transport,
            repository=bundle.onboarding,
            target_execution_repository=bundle.target_executions,
            registry_snapshot_repository=bundle.registry_snapshots,
            policy_snapshot_provider=policy.case_snapshot,
        )
        return cases, build_ownership_analysis_service(cases, hybrid, repository=bundle.ownership)

    def sim_lim(record: Any) -> Any:
        assert record.discovery is not None
        return next(
            item for item in record.discovery.records if item.registration_number == SIM_LIM_UEN
        )

    first = build_persistence_bundle(hybrid)
    try:
        cases, ownership = services(first)
        case = cases.create_staged_case(GARDEN_BUSINESS_UEN)
        ownership.load(case_id=case.case_id)
        record = ownership.analyze(case_id=case.case_id)
        assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
        assert sim_lim(record).outcome == OwnershipDiscoveryOutcome.PROVIDER_PARTIAL
        assert [item.current_interest for item in sim_lim(record).official_shareholders] == [
            True,
            False,
        ]
        calls = dict(transport.calls)
    finally:
        first.close()

    second = build_persistence_bundle(hybrid)
    try:
        cases, ownership = services(second)
        assert second.ownership.get_for_case(case.case_id) == record
        database = client[hybrid.mongo_database]
        collection = database[hybrid.mongo_case_collection]
        raw = collection.find_one({"_id": str(case.case_id)})
        assert raw is not None and raw["schema_version"] == 13
        cache = database[hybrid.mongo_registry_cache_collection]
        assert (
            cache.count_documents(
                {"cache_schema_version": 3, "key.normalized_identifier": SIM_LIM_UEN}
            )
            == 1
        )
        # Durable shareholder evidence survives restart and is reused with zero calls.
        again = cases.create_staged_case(GARDEN_BUSINESS_UEN)
        ownership.load(case_id=again.case_id)
        reused = ownership.analyze(case_id=again.case_id)
        assert dict(transport.calls) == calls
        assert sim_lim(reused).official_shareholder_lookup == "SHAREHOLDERS_CACHE_REUSED"
        assert sim_lim(reused).official_shareholders == sim_lim(record).official_shareholders
        # An exact schema-12 envelope can never carry this evidence: fail closed.
        collection.update_one({"_id": str(case.case_id)}, {"$set": {"schema_version": 12}})
        with pytest.raises(PersistenceDataInvalidError):
            second.onboarding.get(case.case_id)
    finally:
        second.close()
