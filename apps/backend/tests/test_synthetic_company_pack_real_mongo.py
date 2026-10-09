"""Physical owner-based warm, exact namespace/restart/case reuse and no target replay."""

import os
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
    require_ephemeral_mongo_database,
)
from scripts.seed_zero_touch_happy_path_companies import manage_fixtures
from scripts.synthetic_company_pack_test_transport import NoMarketplaceRequests
from scripts.zero_touch_happy_path_fixtures import ALL_COMPANIES, NEW_COMPANIES
from test_slice_b_registry_demo import confirm
from test_synthetic_company_pack import assert_prepared, marketplace_seams, settings, start
from test_zero_touch_orchestration import RecordingMockGoldTier

from app.domain.models import RegistryCacheKey
from app.domain.registry_dataset import local_synthetic_registry_identity as provider_identity
from app.main import create_app
from app.persistence.mongo_registry_cache_store import MongoRegistryCacheStore

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI not configured")


@pytest.fixture
def database():
    name = require_ephemeral_mongo_database(generate_ephemeral_mongo_database("p16"))
    cleanup = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    try:
        yield name
    finally:
        try:
            cleanup_ephemeral_mongo_database(cleanup, name)
            assert name not in cleanup.list_database_names()
        finally:
            cleanup.close()


def test_physical_warm_preserves_four_exact_bundles_and_original_microseconds(database):
    now = datetime(2026, 10, 9, tzinfo=UTC).replace(microsecond=123456)
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    store = MongoRegistryCacheStore(client, database=database, collection="clm_registry_snapshots")
    try:
        store.initialize()
        assert manage_fixtures(store, now=now, seed=True)["created"] == 8
        originals = [
            store.get(
                RegistryCacheKey(provider_identity=provider_identity(), normalized_identifier=c.uen)
            )
            for c in ALL_COMPANIES
        ]
        assert client[database]["clm_registry_snapshots"].count_documents({}) == 8
    finally:
        client.close()
    second = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    restored = MongoRegistryCacheStore(
        second, database=database, collection="clm_registry_snapshots"
    )
    try:
        restored.initialize()
        assert manage_fixtures(restored, now=now, seed=True)["fresh"] == 8
        for entry in originals:
            assert restored.get(entry.key) == entry
            assert entry.acquisition.retrieved_at == now
            assert entry.acquisition.status == "COMPLETE"
            assert entry.key.provider_identity.dataset_namespace == "LOCAL_SYNTHETIC_UAT_V1"
            official = provider_identity().model_copy(
                update={
                    "dataset_namespace": "ACRA_API_MARKETPLACE_MOCK_V1",
                }
            )
            assert (
                restored.get(
                    RegistryCacheKey(
                        provider_identity=official,
                        normalized_identifier=entry.key.normalized_identifier,
                    )
                )
                is None
            )
    finally:
        second.close()


@pytest.mark.parametrize("company", NEW_COMPANIES, ids=lambda c: c.code)
def test_physical_warmed_cache_normal_case_and_completed_restart_without_replay(database, company):
    connection = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    try:
        store = MongoRegistryCacheStore(
            connection, database=database, collection="clm_registry_snapshots"
        )
        store.initialize()
        manage_fixtures(store, now=datetime.now(UTC), seed=True)
    finally:
        connection.close()
    configured = settings(
        clm_persistence_mode="mongo", mongo_uri=MONGO_URI, mongo_database=database
    )
    registry, target = NoMarketplaceRequests(), RecordingMockGoldTier()
    with (
        marketplace_seams(registry),
        patch("app.composition.MockGoldTierConnector", lambda **_: target),
    ):
        with TestClient(create_app(configured)) as client:
            current = start(client, company)
            case_id = current["case"]["case_id"]
            assert current["case"]["registry_evidence_binding"]["disposition"] == "CACHE_HIT"
            ownership = assert_prepared(client, current, company)
            assert registry.calls == [] and target.calls == ["search"]
            final = confirm(client, current)
            assert final["status"] == "COMPLETED"
            assert final["target_submission"]["state"] == "SUBMISSION_CONFIRMED"
            assert target.calls == ["search", "search", "shell", "policy", "amend", "search"]
        before = list(target.calls)
        with TestClient(create_app(configured)) as client:
            restored = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
            assert restored["status"] == "COMPLETED"
            assert restored["target_submission"] == final["target_submission"]
            assert restored["target_operations"] == final["target_operations"]
            assert restored["case"]["registry_acquisition"] == final["case"]["registry_acquisition"]
            assert client.get(f"/api/onboarding/cases/{case_id}/ownership").json() == ownership
        assert target.calls == before and registry.calls == []
