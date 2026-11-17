"""Task-owned schema10 review binding survives restart without read-time repair."""

import os
from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient
from scripts.seed_zero_touch_happy_path_companies import manage_fixtures
from scripts.zero_touch_happy_path_fixtures import COMPANIES
from test_classification_conflict_review import conflict_case
from test_target_classification_continuation import save, upload
from test_zero_touch_database_happy_path import NoAcra, RecordingTarget, sandbox_settings
from test_zero_touch_database_real_mongo import database as database
from test_zero_touch_database_real_mongo import open_store

from app.main import create_app

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")


@pytest.mark.parametrize("mode", ["mock", "sandbox"])
def test_schema10_stale_fresh_and_changed_review_survive_restart_without_read_time_write(
    database, mode
):
    first, store = open_store(database)
    manage_fixtures(store, now=datetime.now(UTC), seed=True)
    first.close()
    settings = sandbox_settings(
        clm_persistence_mode="mongo",
        mongo_uri=MONGO_URI,
        mongo_database=database,
        goldtier_connector_mode=mode,
    )
    acra = NoAcra()
    target = RecordingTarget(COMPANIES[0].name, COMPANIES[0].uen)
    with MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000) as inspection:
        collection = inspection[database][settings.mongo_case_collection]
        with TestClient(
            create_app(settings, acra_connector=acra, goldtier_transport=target)
        ) as client:
            current, old = conflict_case(client)
            cid = current["case"]["case_id"]
            conflict_fingerprint = current["target_classification"]["evidence_fingerprint"]
            assert current["target_classification"]["state"] == "CONFLICT"
            original = collection.find_one({"_id": cid})
            assert original["schema_version"] == 21
        with TestClient(
            create_app(settings, acra_connector=acra, goldtier_transport=target)
        ) as client:
            assert collection.find_one({"_id": cid}) == original
            current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
            assert current["target_classification"]["evidence_fingerprint"] == conflict_fingerprint
            assert not current["target_classification"]["current"]
            assert current["target_classification"]["kyc_customer_type"]["selection"] == old
            assert collection.find_one({"_id": cid}) == original
            response = save(client, current)
            assert response.status_code == 200
            current = response.json()
            reviewed = current["target_classification"]["kyc_customer_type"]["selection"]
            assert reviewed["evidence_fingerprint"] == conflict_fingerprint
            assert reviewed["actor_id"] == "maya-lim"
            reviewed_raw = collection.find_one({"_id": cid})
        with TestClient(
            create_app(settings, acra_connector=acra, goldtier_transport=target)
        ) as client:
            assert collection.find_one({"_id": cid}) == reviewed_raw
            current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
            assert current["target_classification"]["current"]
            assert current["target_classification"]["state"] == "CURRENT"
            assert current["clm"]["readiness"]["blockers"] == []
            assert collection.find_one({"_id": cid}) == reviewed_raw
            upload(client, current, COMPANIES[0].target_profile)
            changed_raw = collection.find_one({"_id": cid})
        with TestClient(
            create_app(settings, acra_connector=acra, goldtier_transport=target)
        ) as client:
            assert collection.find_one({"_id": cid}) == changed_raw
            changed = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
            assert not changed["target_classification"]["current"]
            assert changed["target_classification"]["evidence_fingerprint"] != conflict_fingerprint
            assert changed["target_classification"]["kyc_customer_type"]["selection"] == reviewed
            assert changed_raw["clm"]["submission_snapshot"] is None
            assert collection.find_one({"_id": cid}) == changed_raw
            assert not changed_raw["target_executions"]
            assert UUID(cid) == UUID(changed["case"]["case_id"])
    assert acra.calls == []
    assert all(call[0] == "GET" for call in target.calls)
