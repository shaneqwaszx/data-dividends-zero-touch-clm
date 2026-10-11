"""Guarded physical Garden PARTIAL correction/restart; no external provider writes."""
import os

import pytest
from pymongo import MongoClient
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)
from test_garden_uen_partial_resume import (
    correct,
    garden_system,
    start_wrong_garden,
)
from test_zero_touch_exception_remediation import current_document, successful

from app.persistence.mongo_case_store import MongoCaseStore

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")


@pytest.mark.parametrize("no_match", [False, True])
def test_garden_partial_correction_real_mongo_restart(monkeypatch, no_match):
    database = generate_ephemeral_mongo_database("p12")
    mongo = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    assert mongo[database].list_collection_names() == []
    try:
        store = MongoCaseStore(mongo, database=database, collection="clm_case_snapshots")
        store.initialize()
        client, _, target = garden_system(monkeypatch, no_match=no_match, store=store)
        before, document = start_wrong_garden(client)
        case_id = before["case"]["case_id"]
        corrected = successful(correct(client, before, choice="DOCUMENT", document=document))
        assert corrected["case"]["registry_acquisition"]["status"] == "PARTIAL"
        assert corrected["current_stage"] == ("READINESS" if no_match else "GOLDTIER_SEARCH")
        counts = dict(target.counts)
        reloaded_store = MongoCaseStore(
            mongo, database=database, collection="clm_case_snapshots",
        )
        restarted, registry, _ = garden_system(
            monkeypatch, no_match=no_match, store=reloaded_store, target=target,
        )
        retained = successful(restarted.get(f"/api/clm/zero-touch/cases/{case_id}"))
        assert retained["case"] == corrected["case"]
        assert retained["version"] == corrected["version"]
        assert retained["active_exceptions"] == corrected["active_exceptions"]
        assert current_document(restarted, case_id)["document_id"] == document["document_id"]
        assert correct(restarted, before).status_code == 409
        assert target.counts == counts and registry.calls == []
        assert counts["SHELL"] == counts["POLICY"] == counts["AMEND"] == 0
    finally:
        cleanup_ephemeral_mongo_database(mongo, database)
        assert mongo[database].list_collection_names() == []
        mongo.close()
