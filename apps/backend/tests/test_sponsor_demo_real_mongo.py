"""Actual physical native/seed/Sandbox flow and restart without target replay."""

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from scripts.s3_sandbox_fixture import OfflineS3SandboxTransport
from scripts.seed_zero_touch_happy_path_companies import main as seed_cli
from scripts.seed_zero_touch_happy_path_companies import manage_fixtures
from scripts.synthetic_company_pack_test_transport import NoMarketplaceRequests
from scripts.zero_touch_happy_path_fixtures import SPONSOR_DEMO_COMPANIES
from test_sponsor_demo_fixtures import exercise_native_registry_annex
from test_synthetic_company_pack import marketplace_seams, settings
from test_synthetic_company_pack_real_mongo import MONGO_URI, pytestmark  # noqa: F401
from test_synthetic_company_pack_real_mongo import database as disposable_database

from app.main import create_app
from app.persistence.mongo_registry_cache_store import MongoRegistryCacheStore

database = disposable_database


def test_physical_shortlist_cli_preserves_legacy_and_is_idempotent(
    database, monkeypatch, capsys,
):
    from datetime import UTC, datetime

    from pymongo import MongoClient
    from scripts.zero_touch_happy_path_fixtures import ALL_COMPANIES

    with MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000) as connection:
        store = MongoRegistryCacheStore(
            connection, database=database, collection="clm_registry_snapshots",
        )
        store.initialize()
        now = datetime.now(UTC)
        assert manage_fixtures(store, now=now, seed=True)["created"] == 8
        original = {c.uen: store.get(c.snapshot(now).key) for c in ALL_COMPANIES}
        monkeypatch.setenv("APP_ENV", "test")
        monkeypatch.setenv("MONGO_URI", MONGO_URI)
        for action in ("--seed", "--seed", "--check"):
            monkeypatch.setattr(
                "sys.argv", ["seed", action, "--sponsor-demo", "--database", database],
            )
            assert seed_cli() == 0
            output = capsys.readouterr().out
            assert "FIXTURE_COUNT=4" in output
            if MONGO_URI in output:
                pytest.fail("Seed CLI exposed connection configuration")
        assert connection[database]["clm_registry_snapshots"].count_documents({}) == 9
        assert all(store.get(c.snapshot(now).key) == original[c.uen] for c in ALL_COMPANIES)
        assert manage_fixtures(
            store, now=datetime.now(UTC), seed=False, companies=SPONSOR_DEMO_COMPANIES,
        )["fresh"] == 4


@pytest.mark.parametrize("company", SPONSOR_DEMO_COMPANIES, ids=lambda c: c.code)
def test_physical_annex_native_complete_and_restart_never_replays(company, database):
    configured = settings(
        clm_persistence_mode="mongo",
        mongo_uri=SecretStr(MONGO_URI),
        mongo_database=database,
        goldtier_connector_mode="sandbox",
        goldtier_sandbox_base_url="https://sandbox.goldtier.invalid",
        goldtier_sandbox_environment="synthetic",
        goldtier_sandbox_user_id="synthetic-offline-user",
        goldtier_sandbox_allow_writes=True,
    )
    cid = exercise_native_registry_annex(company, configured=configured)
    target = OfflineS3SandboxTransport("success")
    target.name, target.uen = company.name, company.uen
    guard = NoMarketplaceRequests()
    with (
        marketplace_seams(guard),
        TestClient(create_app(configured, goldtier_transport=target)) as client,
    ):
        retained = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        assert retained["status"] == "COMPLETED"
        assert retained["target_submission"]["state"] == "SUBMISSION_CONFIRMED"
        assert retained["document_replacement_authorized"] is False
        assert retained["ownership_edit_authorized"] is False
        ownership = client.get(f"/api/onboarding/cases/{cid}/ownership").json()
        assert ownership["state"] == "ANALYZED" and ownership["manual_review_receipt"] is None
        assert target.counts == {"SEARCH": 0, "SHELL": 0, "POLICY": 0, "AMEND": 0, "READBACK": 0}
        assert guard.calls == []
