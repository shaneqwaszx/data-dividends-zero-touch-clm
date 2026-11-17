"""C2 on physical Mongo: a stored activation is enforced with the manager switched off.

An empty workflow store sends as before; a stored required stage holds every send route;
a corrupt stored definition fails closed. Each test uses a newly generated allowlisted
disposable database, never ``clm_poc``.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import SecretStr
from pymongo import MongoClient
from test_final_review_editing import confirmation_versions
from test_final_review_editing_real_mongo import prepare_final
from test_synthetic_company_pack import settings
from test_synthetic_company_pack_real_mongo import MONGO_URI, pytestmark  # noqa: F401
from test_synthetic_company_pack_real_mongo import database as disposable_database
from test_workflow_manager import STAGE, login
from test_zero_touch_orchestration import RecordingMockGoldTier
from workflow_publication_seed import publish_stored_draft_mongo

from app.domain.workflows import ONBOARDING_WORKFLOW_ID
from app.main import create_app
from app.services.workflow_management import HOLD_INCOMPLETE, HOLD_UNAVAILABLE

database = disposable_database


def physical(database, *, enabled):
    return settings(
        acra_connector_mode="mock",
        clm_persistence_mode="mongo",
        mongo_uri=SecretStr(MONGO_URI),
        mongo_database=database,
        workflow_manager_enabled=enabled,
    )


def activate_onboarding_physical(director, configured):
    """Save the draft through the API, then publish it on the Mongo path (F-6).

    Activation is frozen by ADR-017 P2-0, and the shared ``activate_onboarding`` helper publishes
    into a memory store only. This physical test needs the version in its disposable database.
    """

    baseline = director.get(f"/api/workflows/{ONBOARDING_WORKFLOW_ID}").json()
    saved = director.put(
        f"/api/workflows/{ONBOARDING_WORKFLOW_ID}/draft",
        json={"expected_revision": baseline["revision"], "stages": [STAGE]},
    )
    assert saved.status_code == 200, saved.json()
    publish_stored_draft_mongo(
        MONGO_URI,
        configured.mongo_database,
        configured.mongo_workflow_definitions_collection,
        ONBOARDING_WORKFLOW_ID,
        actor_id="olivia-koh",
    )
    active = director.get(f"/api/workflows/{ONBOARDING_WORKFLOW_ID}")
    assert active.status_code == 200, active.json()
    assert active.json()["active_version"] is not None, active.json()


def legacy_body(client, case_id):
    summary = client.get(f"/api/clm/cases/{case_id}").json()
    return {
        "expected_clm_version": summary["version"],
        "expected_case_event_count": len(summary["case"]["events"]),
    }


def assert_every_send_route_held(client, case_id, current, code):
    zero_touch = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
        json=confirmation_versions(current),
    )
    assert zero_touch.status_code >= 400, zero_touch.text
    assert zero_touch.json()["detail"]["code"] == code
    # ADR-017 3.7 (P2-0 writer): the legacy target confirmation is retired (404), and legacy
    # submit is still held by the same code, exactly as the memory twin asserts.
    retired = client.post(
        f"/api/clm/cases/{case_id}/target-confirmation", json=legacy_body(client, case_id)
    )
    assert retired.status_code == 404, retired.text
    submitted = client.post(f"/api/clm/cases/{case_id}/submit")
    assert submitted.status_code == 409, submitted.text
    assert submitted.json()["detail"]["code"] == code


def test_physical_switched_off_manager_enforces_a_stored_stage_and_fails_closed(database):
    enabled = physical(database, enabled=True)
    with (
        patch("app.composition.MockGoldTierConnector", lambda **_: RecordingMockGoldTier()),
        TestClient(create_app(enabled)) as client,
    ):
        activate_onboarding_physical(login(client.app, "olivia-koh"), enabled)

    disabled = physical(database, enabled=False)
    target = RecordingMockGoldTier()
    with (
        patch("app.composition.MockGoldTierConnector", lambda **_: target),
        TestClient(create_app(disabled)) as client,
    ):
        refused = login(client.app, "olivia-koh").get("/api/workflows")
        assert refused.status_code == 404
        assert refused.json()["detail"]["code"] == "WORKFLOW_MANAGER_DISABLED"
        case_id, current, _ = prepare_final(client)
        calls = list(target.calls)
        assert_every_send_route_held(client, case_id, current, HOLD_INCOMPLETE)
        assert target.calls == calls
        assert not {"shell", "policy", "amend"} & set(target.calls)

    cleanup = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    try:
        collection = cleanup[database][disabled.mongo_workflow_definitions_collection]
        corrupted = collection.update_one(
            {"_id": ONBOARDING_WORKFLOW_ID}, {"$set": {"payload": {"corrupt": True}}}
        )
        assert corrupted.matched_count == 1
    finally:
        cleanup.close()

    restarted = RecordingMockGoldTier()
    with (
        patch("app.composition.MockGoldTierConnector", lambda **_: restarted),
        TestClient(create_app(disabled)) as client,
    ):
        current = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
        assert_every_send_route_held(client, case_id, current, HOLD_UNAVAILABLE)
        assert restarted.calls == []


def test_physical_empty_workflow_store_sends_as_before_with_the_manager_off(database):
    target = RecordingMockGoldTier()
    with (
        patch("app.composition.MockGoldTierConnector", lambda **_: target),
        TestClient(create_app(physical(database, enabled=False))) as client,
    ):
        case_id, current, _ = prepare_final(client)
        completed = client.post(
            f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
            json=confirmation_versions(current),
        )
        assert completed.status_code == 200, completed.text
        assert completed.json()["status"] == "COMPLETED"
        assert target.calls.count("shell") == 1
