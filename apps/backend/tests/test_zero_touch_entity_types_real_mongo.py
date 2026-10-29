"""D-101 physical MongoDB proof (case snapshot schema 17) for the new demo entity types.

Opt-in like every ``*_real_mongo`` suite: it runs only when ``PHASE12_MONGO_URI`` is set. Each
test uses a newly generated allowlisted database (``clm_p16_<24 hex>``) that is dropped and
verified absent afterwards; ``clm_poc`` and every other database are never touched. A
"restart" is a new application composition with new Mongo clients over the same database.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient
from scripts.seed_zero_touch_happy_path_companies import manage_fixtures
from scripts.zero_touch_happy_path_fixtures import COMPANIES, GOVERNMENT
from test_slice_b_registry_demo import confirm
from test_zero_touch_database_happy_path import NoAcra, RecordingTarget, sandbox_settings
from test_zero_touch_database_real_mongo import MONGO_URI, database, open_store  # noqa: F401
from test_zero_touch_entity_types import (
    blockers,
    confirm_government,
    gamma_at_ownership,
    gamma_declaration,
    government_at_status,
    submit_partners,
)

from app.main import create_app

pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")


def seeded_settings(database):  # noqa: F811 - the fixture value, not the fixture
    client, store = open_store(database)
    manage_fixtures(store, now=datetime.now(UTC), seed=True)
    client.close()
    return sandbox_settings(
        clm_persistence_mode="mongo", mongo_uri=MONGO_URI, mongo_database=database
    )


def raw_case(database, case_id):  # noqa: F811
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    try:
        return client[database]["clm_case_snapshots"].find_one({"_id": case_id})
    finally:
        client.close()


def test_government_confirmation_survives_restart_and_is_never_replayed(database):  # noqa: F811
    settings = seeded_settings(database)
    acra, target = NoAcra(), RecordingTarget(GOVERNMENT.name, GOVERNMENT.uen)
    with TestClient(create_app(settings, acra_connector=acra, goldtier_transport=target)) as app:
        waiting = government_at_status(app)
        assert blockers(waiting) == ["GOVERNMENT_STATUS_REQUIRED"]
        confirmed = confirm_government(app, waiting)
        assert confirmed.status_code == 200, confirmed.json()
        current = confirmed.json()
        case_id = current["case"]["case_id"]
    raw = raw_case(database, case_id)
    assert raw is not None and raw["schema_version"] == 17
    retained = raw["onboarding"]["government_status_confirmation"]
    assert retained["classification"] == "USER_AUTHORIZED_POC"
    assert retained["document_id"] == current["entity_type_basis"]["government_status"][
        "document_id"
    ]
    assert raw["documents"][0]["government_status_observations"][0]["field_key"] == (
        "FOUNDING_INSTRUMENT"
    )
    with TestClient(create_app(settings, acra_connector=acra, goldtier_transport=target)) as app:
        restored = app.get(f"/api/clm/zero-touch/cases/{case_id}").json()
        assert restored["entity_type_basis"] == current["entity_type_basis"]
        assert restored["entity_type_basis"]["government_status"]["state"] == "CONFIRMED"
        assert blockers(restored) == ["TARGET_CONFIRMATION_REQUIRED"]
        again = confirm_government(app, {
            **restored,
            "entity_type_basis": current["entity_type_basis"],
        })
        assert again.status_code == 409  # no open hold: never re-confirmed or replayed
        final = confirm(app, restored)
        assert final["status"] == "COMPLETED"
    assert acra.calls == []


def test_partnership_rm_confirmed_shares_survive_restart(database):  # noqa: F811
    gamma = COMPANIES[2]
    settings = seeded_settings(database)
    acra, target = NoAcra(), RecordingTarget(gamma.name, gamma.uen)
    with TestClient(create_app(settings, acra_connector=acra, goldtier_transport=target)) as app:
        current = gamma_at_ownership(app)
        response = submit_partners(app, current, gamma_declaration(app, current))
        assert response.status_code == 200, response.json()
        case_id = response.json()["case"]["case_id"]
        ownership = app.get(f"/api/onboarding/cases/{case_id}/ownership").json()
    assert raw_case(database, case_id)["schema_version"] == 17
    with TestClient(create_app(settings, acra_connector=acra, goldtier_transport=target)) as app:
        restored = app.get(f"/api/clm/zero-touch/cases/{case_id}").json()
        assert restored["entity_type_basis"]["label"] == (
            "Partner shares from partnership agreement, RM-confirmed"
        )
        assert app.get(f"/api/onboarding/cases/{case_id}/ownership").json() == ownership
        assert {
            item["party"]["display_name"]: Decimal(item["aggregated_ownership_percent"])
            for item in ownership["candidates"]
            if item["classification"] == "PROVISIONAL_UBO_CANDIDATE"
        } == {"DEMO GAMMA PERSON P1": Decimal("30"), "DEMO GAMMA PERSON P2": Decimal("25")}
    assert acra.calls == []
