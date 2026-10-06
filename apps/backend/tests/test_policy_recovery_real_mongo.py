"""Generated disposable Mongo: Policy recovery survives restart without read rewrites."""

import os
from contextlib import contextmanager
from copy import deepcopy
from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from pymongo import MongoClient
from scripts.mongo_test_safety import require_ephemeral_mongo_database
from scripts.seed_zero_touch_happy_path_companies import manage_fixtures
from test_policy_provider_recovery import (
    UncertainPolicyTransport,
    login_as,
    recovery_payload,
)
from test_s2_intelligence_real_mongo import physical_database  # noqa: F401
from test_target_classification_continuation import COMPANIES, confirm, prepare
from test_zero_touch_database_happy_path import NoAcra

from app.main import create_app
from app.persistence.composition import build_persistence_bundle
from app.persistence.mongo_case_store import MongoCaseStore

pytestmark = pytest.mark.skipif(
    not os.environ.get("PHASE12_MONGO_URI"),
    reason="Disposable physical Mongo is not configured",
)


@contextmanager
def physical_runtime(settings, target, *, seed=False):
    bundle = build_persistence_bundle(settings)
    if seed:
        from datetime import UTC, datetime

        manage_fixtures(bundle.registry_snapshots, now=datetime.now(UTC), seed=True)
    with (
        patch("app.main.build_persistence_bundle", return_value=bundle),
        TestClient(
            create_app(settings, acra_connector=NoAcra(), goldtier_transport=target)
        ) as client,
    ):
        yield client, bundle


def test_normal_shell_policy_recovery_restart_read_only_then_same_intent_resume(
    physical_database,  # noqa: F811
):
    settings = physical_database.model_copy(
        update={
            "acra_connector_mode": "api_marketplace_mock",
            "goldtier_connector_mode": "sandbox",
            "goldtier_sandbox_base_url": "https://sandbox.goldtier.invalid",
            "goldtier_sandbox_environment": "synthetic",
            "goldtier_sandbox_user_id": SecretStr("synthetic-api-user"),
            "goldtier_sandbox_allow_writes": True,
        }
    )
    require_ephemeral_mongo_database(settings.mongo_database)
    target = UncertainPolicyTransport(COMPANIES[0].name, COMPANIES[0].uen)
    with physical_runtime(settings, target, seed=True) as (client, bundle):
        current = confirm(client, prepare(client, COMPANIES[0]))
        cid = UUID(current["case"]["case_id"])
        path = f"/api/clm/zero-touch/cases/{cid}"
        original = bundle.target_executions.list_for_case(cid)[0]
        confirmation = bundle.onboarding.get(cid).target_dispatch_confirmation
        login_as(client, "olivia-koh")
        assert (
            client.post(path + "/target-recovery", json=recovery_payload(current)).status_code
            == 200
        )
        recovered = bundle.target_executions.list_for_case(cid)[0]
        assert recovered.provider_verified_recovery is None
        assert [str(x) for x in recovered.definitively_completed_operations] == ["SEARCH", "SHELL"]
        assert bundle.automation.get_for_case(cid).status == "RECOVERY_PENDING"
    counts = deepcopy(target.calls)
    uri = os.environ["PHASE12_MONGO_URI"]
    store = MongoCaseStore(
        MongoClient(uri),
        database=settings.mongo_database,
        collection=settings.mongo_case_collection,
    )
    try:
        before = deepcopy(store._collection.find_one({"_id": str(cid)}))
        for _ in range(3):
            restored = store.get(cid)
            assert restored.target_executions == (recovered,)
        assert store._collection.find_one({"_id": str(cid)}) == before
        with physical_runtime(settings, target) as (client, bundle):
            assert bundle.target_executions.list_for_case(cid) == (recovered,)
            assert target.calls == counts
            assert store._collection.find_one({"_id": str(cid)}) == before
            login_as(client, "olivia-koh")
            assert (
                client.post(path + "/target-recovery", json=recovery_payload(current)).status_code
                == 200
            )
            assert store._collection.find_one({"_id": str(cid)}) == before
            final = client.post(path + "/resume")
            assert final.status_code == 200 and final.json()["status"] == "COMPLETED"
            entries = bundle.target_executions.list_for_case(cid)
            assert len(entries) == 1 and entries[0].submission_input == original.submission_input
            assert entries[0].shell_status == "SHELL_CREATED"
            assert bundle.onboarding.get(cid).target_dispatch_confirmation == confirmation
        final_raw = deepcopy(store._collection.find_one({"_id": str(cid)}))
        with physical_runtime(settings, target) as (client, _):
            final = client.get(path)
            assert final.status_code == 200 and final.json()["status"] == "COMPLETED"
            assert store._collection.find_one({"_id": str(cid)}) == final_raw
        assert len([c for c in target.calls if c[1].endswith("/createPolicy")]) == 1
        assert len([c for c in target.calls if c[1].endswith("/customers/create")]) == 1
        assert all(not c[1].endswith("/amendCustomer") for c in target.calls)
    finally:
        store.close()
