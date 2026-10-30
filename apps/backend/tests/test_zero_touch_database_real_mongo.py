"""Guarded physical seed/restart/reuse and normal Sandbox-fake target journeys."""

import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
    require_ephemeral_mongo_database,
)
from scripts.seed_zero_touch_happy_path_companies import manage_fixtures
from scripts.zero_touch_happy_path_fixtures import COMPANIES, SHARE_COMPANIES
from test_slice_b_registry_demo import confirm
from test_zero_touch_database_happy_path import (
    NoAcra,
    RecordingTarget,
    assert_prepared,
    prepare,
    sandbox_settings,
)

from app.domain.models import RegistryFreshnessPolicy
from app.domain.registry_dataset import local_synthetic_registry_identity
from app.main import create_app
from app.persistence.mongo_registry_cache_store import MongoRegistryCacheStore
from app.services.registry_acquisition import RegistryAcquisitionCoordinator
from app.services.registry_cache_repository import RegistrySnapshotRepositoryConflictError

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")
ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def database():
    name = require_ephemeral_mongo_database(generate_ephemeral_mongo_database("p16"))
    cleanup = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    try:
        yield name
    finally:
        cleanup_ephemeral_mongo_database(cleanup, name)
        assert name not in cleanup.list_database_names()
        cleanup.close()


def open_store(database):
    require_ephemeral_mongo_database(database)
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    store = MongoRegistryCacheStore(client, database=database, collection="clm_registry_snapshots")
    store.initialize()
    return client, store


def test_physical_cli_seed_check_rerun_and_restart_are_safe_idempotent(database):
    env = {**os.environ, "MONGO_URI": MONGO_URI, "APP_ENV": "test"}
    command = [
        sys.executable,
        str(ROOT / "scripts/seed_zero_touch_happy_path_companies.py"),
        "--database",
        database,
    ]
    for flag, expected in (
        # D-101: nine seeds, including the PARTIAL Government identity.
        ("--seed", "CREATED=9"),
        ("--seed", "CREATED=0"),
        ("--check", "FRESH=9"),
    ):
        result = subprocess.run(
            [*command, flag],
            env=env,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        assert result.returncode == 0, "Safe seed/check command failed"
        assert expected in result.stdout
        assert MONGO_URI not in result.stdout + result.stderr
        assert "local-synthetic" not in result.stdout
    first, store = open_store(database)
    originals = [store.get(company.snapshot(datetime.now(UTC)).key) for company in COMPANIES]
    # D-101: nine seeds, including the PARTIAL Government identity.
    assert first[database]["clm_registry_snapshots"].count_documents({}) == 9
    first.close()
    second, restored = open_store(database)
    try:
        assert [restored.get(entry.key) for entry in originals] == originals
        assert all(entry.revision == 0 for entry in originals)
        stale = originals[0]
        refreshed = stale.model_copy(update={"revision": 0})
        restored.replace(refreshed, expected_revision=0)
        with pytest.raises(RegistrySnapshotRepositoryConflictError):
            restored.replace(refreshed, expected_revision=0)
    finally:
        second.close()


# D-101: Gamma has no registry shares; its agreement journey is in test_zero_touch_entity_types.
@pytest.mark.parametrize("company", SHARE_COMPANIES, ids=lambda item: item.code)
def test_normal_mongo_runtime_reuses_seed_and_retains_completed_no_replay_after_restart(
    database, company
):
    client, store = open_store(database)
    manage_fixtures(store, now=datetime.now(UTC), seed=True)
    client.close()
    settings = sandbox_settings(
        clm_persistence_mode="mongo", mongo_uri=MONGO_URI, mongo_database=database
    )
    acra, target = NoAcra(), RecordingTarget(company.name, company.uen)
    with TestClient(create_app(settings, acra_connector=acra, goldtier_transport=target)) as app:
        current = prepare(app, company)
        document, ownership = assert_prepared(app, current, company)
        final = confirm(app, current)
        assert final["target_submission"]["state"] == "SUBMISSION_CONFIRMED"
        counts = list(target.calls)
    with TestClient(create_app(settings, acra_connector=acra, goldtier_transport=target)) as app:
        case_id = current["case"]["case_id"]
        retained = app.get(f"/api/clm/zero-touch/cases/{case_id}").json()
        assert retained["target_submission"] == final["target_submission"]
        assert retained["target_operations"] == final["target_operations"]
        assert (
            retained["case"]["registry_evidence_binding"]
            == final["case"]["registry_evidence_binding"]
        )
        assert app.get(f"/api/onboarding/cases/{case_id}/ownership").json() == ownership
        assert (
            app.post(
                f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
                json={
                    "expected_automation_version": retained["version"],
                    "expected_clm_version": retained["clm"]["version"],
                    "expected_case_event_count": len(retained["case"]["events"]),
                },
            ).status_code
            == 409
        )
        assert target.calls == counts and acra.calls == []


def test_physical_expired_seed_uses_provider_namespace_and_preserves_seed(database):
    now = datetime(2026, 1, 2, 3, 4, 5, 123456, tzinfo=UTC)
    first, store = open_store(database)
    manage_fixtures(store, now=now, seed=True)
    first.close()
    second, restored = open_store(database)
    company = COMPANIES[0]
    entry = restored.get(company.snapshot(now).key)
    calls = []

    class Provider:
        cache_identity = local_synthetic_registry_identity().model_copy(
            update={"dataset_namespace": "ACRA_API_MARKETPLACE_MOCK_V1"}
        )

        def retrieve_acquisition(self, identifier, **kwargs):
            calls.append(identifier)
            return None

    try:
        coordinator = RegistryAcquisitionCoordinator(
            restored,
            RegistryFreshnessPolicy(),
            clock=lambda: now + timedelta(days=90),
            local_seed_identity=local_synthetic_registry_identity(),
        )
        assert coordinator.acquire(Provider(), company.uen).acquisition is None
        assert calls == [company.uen]
        assert restored.get(entry.key) == entry
        assert entry.freshness_anchor.microsecond == 123456
    finally:
        second.close()
