"""Physical proof of recursive ownership persistence in a fresh allowlisted database."""

import os
from collections import Counter
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from pymongo import MongoClient
from scripts.five_layer_hybrid_fixture import OfflineFiveLayerProtocolTransport
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)
from test_ownership_discovery_policy import _legacy_catalogue_with_history
from test_poc_ownership_acceptance import garden_transport
from test_zero_touch_exception_remediation import successful

from app.composition import (
    build_acra_connector,
    build_onboarding_service,
    build_ownership_analysis_service,
)
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
from app.main import create_app
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
        assert raw is not None and raw["schema_version"] == 20
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
        assert raw is not None and raw["schema_version"] == 20
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
    physical_settings, monkeypatch
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
                            "shareType": share_type,
                            "currency": "SINGAPORE DOLLAR",
                            "status": status,
                        }
                        for category, identifier, name, units, share_type, status in (
                            (
                                "Corporate",
                                "SYN-SL-C1",
                                "SYNTHETIC CORPORATE, INC.",
                                500,
                                "Ordinary",
                                "Active",
                            ),
                            (
                                "Individual",
                                "SYN-SL-3",
                                "SYNTHETIC HOLDER",
                                100,
                                "Preference",
                                "Withdrawn",
                            ),
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
        assert [item.share_type for item in sim_lim(record).official_shareholders] == [
            "Ordinary",
            "Preference",
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
        assert raw is not None and raw["schema_version"] == 20
        cache = database[hybrid.mongo_registry_cache_collection]
        assert (
            cache.count_documents(
                {"cache_schema_version": 4, "key.normalized_identifier": SIM_LIM_UEN}
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
        # An exact schema-13 envelope can never carry a D-080 share class, and a
        # schema-12 envelope never carries the rows at all: both fail closed.
        for legacy in (13, 12):
            collection.update_one({"_id": str(case.case_id)}, {"$set": {"schema_version": legacy}})
            with pytest.raises(PersistenceDataInvalidError):
                second.onboarding.get(case.case_id)

        # A D-079 (schema-13) envelope, which has retained rows without a class and no
        # D-081 POC links, reads into the current form, and is not rewritten. The D-079
        # shape comes from a case whose POC distribution was refused.
        def refuse(*args: Any, **kwargs: Any) -> None:
            raise ValueError("synthetic refusal")

        monkeypatch.setattr(
            "app.services.ownership_discovery.official_equal_unit_component", refuse
        )
        d079 = cases.create_staged_case(GARDEN_BUSINESS_UEN)
        ownership.load(case_id=d079.case_id)
        retained = ownership.analyze(case_id=d079.case_id)
        assert sim_lim(retained).reason_code == "OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE"
        rows = "ownership.discovery.records.$[].official_shareholders.$[]"
        collection.update_one(
            {"_id": str(d079.case_id)},
            {
                "$set": {"schema_version": 13},
                "$unset": {
                    f"{rows}.share_type": "", f"{rows}.currency": "",
                    # D-101 (schema 17) keys never existed in schema 13.
                    "onboarding.government_status_confirmation": "",
                    "documents.$[].government_status_observations": "",
                    "onboarding.uen_route": "",  # D-114 (schema 18)
                    "ownership.poc_interest_ledger": "",  # D-120 (schema 19)
                },
            },
        )
        before = collection.find_one({"_id": str(d079.case_id)})
        assert second.onboarding.get(d079.case_id) is not None
        legacy_record = second.ownership.get_for_case(d079.case_id)
        assert legacy_record is not None
        assert [item.share_type for item in sim_lim(legacy_record).official_shareholders] == [
            None,
            None,
        ]
        assert collection.find_one({"_id": str(d079.case_id)}) == before
    finally:
        second.close()


def test_poc_acceptance_survives_restart_but_grants_readiness_only_while_enabled(
    physical_settings,
):
    """D-082: enabled -> accepted -> restart disabled or outside the lane -> blocked.

    D-112 (O7): the accepted case is an ordinary company with no scenario, accepted on the
    generic evidence rule; acceptance is default on (O5), so "disabled" is explicit.
    """
    from evidence_poc_fixture import add_generic_company, start_generic

    settings, client = physical_settings
    hybrid = {
        "acra_connector_mode": "api_marketplace_mock",
        "acra_marketplace_ownership_overlay": "hybrid_direct_overlay",
        "goldtier_connector_mode": "mock",
        "idp_connector_mode": "local_pdf_text",
        "acra_api_marketplace_mock_client_id": SecretStr("synthetic-offline-client"),
        "acra_api_marketplace_mock_secret_key": SecretStr("synthetic-offline-key"),
    }
    enabled = settings.model_copy(
        update={**hybrid, "acra_marketplace_poc_ownership_acceptance": "accept_eligible_poc"}
    )
    disabled = settings.model_copy(
        update={**hybrid, "acra_marketplace_poc_ownership_acceptance": "disabled"}
    )
    legacy = disabled.model_copy(
        update={"acra_marketplace_ownership_overlay": "garden_legacy_supplement"}
    )
    local_mock = legacy.model_copy(update={"acra_connector_mode": "mock"})
    transport = add_generic_company(garden_transport())

    def application(active: Settings) -> TestClient:
        connector = (
            build_acra_connector(active, transport=transport, marketplace_token_transport=transport)
            if active.acra_connector_mode == "api_marketplace_mock"
            else None
        )
        return TestClient(create_app(active, acra_connector=connector))

    def confirmation(current: dict) -> dict:
        return {
            "expected_automation_version": current["version"],
            "expected_clm_version": current["clm"]["version"],
            "expected_case_event_count": len(current["case"]["events"]),
        }

    collection = client[settings.mongo_database][settings.mongo_case_collection]
    with application(enabled) as first:
        case_id = start_generic(first)["case"]["case_id"]
        accepted = successful(first.get(f"/api/onboarding/cases/{case_id}/ownership"))
        summary = successful(first.get(f"/api/clm/zero-touch/cases/{case_id}"))
        assert (accepted["state"], accepted["poc_basis_accepted"]) == ("REVIEW_REQUIRED", True)
        assert summary["clm"]["readiness"]["blockers"] == []
        assert [item["exception_type"] for item in summary["active_exceptions"]] == [
            "TARGET_CONFIRMATION_REQUIRED"
        ]
    raw = collection.find_one({"_id": case_id})
    assert raw is not None and raw["schema_version"] == 20
    assert raw["ownership"]["poc_acceptance"]["policy"] == "D085_SCENARIO_DECLARED_POC_BASIS_V1"
    assert raw["ownership"]["poc_acceptance"]["overlay_scenario_id"] == "EVIDENCE_POC_BASIS_V1"
    assert raw["ownership"]["poc_acceptance"]["accepted_assumptions"] == [
        "DESCRIPTIVE_OFFICER_ROLES",
        "EQUAL_UNIT_DENOMINATOR",
    ]

    for restarted in (disabled, legacy, local_mock):
        with application(restarted) as other:
            ownership = successful(other.get(f"/api/onboarding/cases/{case_id}/ownership"))
            # The durable acceptance is unchanged audit evidence and grants nothing here.
            assert ownership["poc_acceptance"] == accepted["poc_acceptance"]
            assert ownership["poc_basis_accepted"] is False
            current = successful(other.get(f"/api/clm/zero-touch/cases/{case_id}"))
            assert "OWNERSHIP_REVIEW_REQUIRED" in current["clm"]["readiness"]["blockers"]
            refused = other.post(
                f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
                json=confirmation(current),
            )
            assert refused.status_code == 409
            after = successful(other.get(f"/api/clm/zero-touch/cases/{case_id}"))
            assert after["case"].get("goldtier_result") is None
            assert after["clm"]["submission"] is None
        stored = collection.find_one({"_id": case_id})
        assert stored is not None and stored["ownership"] == raw["ownership"]

    def resume(active: TestClient) -> dict:
        current = successful(active.get(f"/api/clm/zero-touch/cases/{case_id}"))
        return successful(
            active.post(
                f"/api/clm/zero-touch/cases/{case_id}/resume",
                headers={
                    "X-Automation-Id": current["automation_id"],
                    "X-Automation-Version": str(current["version"]),
                    "X-Clm-Version": str(current["clm"]["version"]),
                    "X-Case-Event-Count": str(len(current["case"]["events"])),
                },
            )
        )

    def exceptions(summary: dict) -> list[str]:
        return sorted(item["exception_type"] for item in summary["active_exceptions"])

    # Resuming without the policy restores the ordinary ownership hold before any send,
    # and the stale target confirmation is withdrawn (F2).
    with application(disabled) as other:
        held = resume(other)
        assert (held["status"], held["current_stage"]) == ("WAITING_FOR_REVIEW", "OWNERSHIP")
        assert exceptions(held) == ["OWNERSHIP_INCOMPLETE"]
        refused = other.post(
            f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
            json=confirmation(held),
        )
        assert refused.status_code == 409
        assert held["case"].get("goldtier_result") is None
    # Re-enabled: the next resume clears that stale hold, so readiness and the workflow
    # agree again at target confirmation; nothing is sent automatically.
    with application(enabled) as again:
        ownership = successful(again.get(f"/api/onboarding/cases/{case_id}/ownership"))
        assert ownership["poc_basis_accepted"] is True
        resumed = resume(again)
        assert (resumed["status"], resumed["current_stage"]) == ("WAITING_FOR_REVIEW", "READINESS")
        assert exceptions(resumed) == ["TARGET_CONFIRMATION_REQUIRED"]
        assert resumed["clm"]["readiness"]["blockers"] == []
        assert resumed["case"].get("goldtier_result") is None

    # Corrupted policy authority and an exact schema-13 envelope both fail closed.
    bundle = build_persistence_bundle(enabled)
    try:
        assert bundle.ownership.get_for_case(UUID(case_id)) is not None
        collection.update_one(
            {"_id": case_id},
            {"$set": {"ownership.poc_acceptance.policy": "D082_UNREVIEWED_POLICY"}},
        )
        with pytest.raises(PersistenceDataInvalidError):
            bundle.onboarding.get(UUID(case_id))
        collection.update_one(
            {"_id": case_id},
            {
                "$set": {
                    "ownership.poc_acceptance": raw["ownership"]["poc_acceptance"],
                    "schema_version": 13,
                }
            },
        )
        with pytest.raises(PersistenceDataInvalidError):
            bundle.onboarding.get(UUID(case_id))
    finally:
        bundle.close()
