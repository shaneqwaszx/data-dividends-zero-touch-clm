"""Genuine Mongo restart proof for Phase 13 team ownership and priority."""

from __future__ import annotations

import os
from typing import Any
from uuid import UUID, uuid4

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from pymongo import MongoClient
from test_phase12_real_mongo import _install_counting_connectors

from app.config import Settings
from app.domain.access import TeamId
from app.main import create_app
from app.persistence.composition import build_persistence_bundle
from app.services.repository import CaseTeamImmutableError

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")


def _login(client: RawTestClient, user_id: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"user_id": user_id, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["csrf_token"]


def _create(client: RawTestClient, csrf: str, uen: str) -> str:
    response = client.post(
        "/api/clm/zero-touch/cases",
        json={"uen": uen},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 201, response.text
    return response.json()["case"]["case_id"]


def _set_priority(
    client: RawTestClient,
    csrf: str,
    case_id: str,
    priority: int | None,
) -> None:
    response = client.patch(
        f"/api/clm/zero-touch/cases/{case_id}/priority",
        json={"priority": priority},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200, response.text


def test_real_mongo_restart_preserves_team_scope_priority_and_provider_free_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert MONGO_URI is not None
    database = f"clm_phase13_test_{uuid4().hex}"
    settings = Settings(
        _env_file=None,
        app_env="test",
        clm_persistence_mode="mongo",
        mongo_uri=MONGO_URI,
        mongo_database=database,
        mongo_case_collection="clm_case_snapshots",
    )
    cleanup: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    counters = _install_counting_connectors(monkeypatch)
    try:
        with RawTestClient(create_app(settings)) as first_a, RawTestClient(
            first_a.app
        ) as first_b:
            csrf_a = _login(first_a, "team-a-onboarder")
            csrf_b = _login(first_b, "team-b-onboarder")
            a_high = _create(first_a, csrf_a, "202400001A")
            a_unset = _create(first_a, csrf_a, "202400002B")
            b_mid = _create(first_b, csrf_b, "202400007G")
            _set_priority(first_a, csrf_a, a_high, 10)
            _set_priority(first_a, csrf_a, a_unset, None)
            _set_priority(first_b, csrf_b, b_mid, 8)

            collection = cleanup[database][settings.mongo_case_collection]
            raw_documents = list(collection.find({}))
            assert len(raw_documents) == 3
            assert all(type(item["schema_version"]) is int for item in raw_documents)
            assert all(item["schema_version"] == 2 for item in raw_documents)

            physical = build_persistence_bundle(settings)
            try:
                persisted = physical.onboarding.get(UUID(a_high))
                assert persisted is not None
                assert persisted.team_id == TeamId.TEAM_A
                assert persisted.priority == 10
                with pytest.raises(CaseTeamImmutableError):
                    physical.onboarding.save(
                        persisted.model_copy(update={"team_id": TeamId.TEAM_B}, deep=True)
                    )
                unchanged = physical.onboarding.get(UUID(a_high))
                assert unchanged is not None
                assert unchanged.team_id == TeamId.TEAM_A
                assert unchanged.priority == 10
            finally:
                physical.close()

            raw_after_rejected_mutation = collection.find_one({"_id": a_high})
            assert raw_after_rejected_mutation is not None
            assert raw_after_rejected_mutation["onboarding"]["team_id"] == "TEAM_A"
            assert raw_after_rejected_mutation["onboarding"]["priority"] == 10
            assert type(raw_after_rejected_mutation["schema_version"]) is int
            assert raw_after_rejected_mutation["schema_version"] == 2

            assert [item["case_id"] for item in first_a.get(
                "/api/clm/zero-touch/cases"
            ).json()] == [a_high, a_unset]
            assert [item["case_id"] for item in first_b.get(
                "/api/clm/zero-touch/cases"
            ).json()] == [b_mid]

        before_restart = counters.copy()
        with RawTestClient(create_app(settings)) as second_director:
            csrf_director = _login(second_director, "director")
            listed = second_director.get("/api/clm/zero-touch/cases")
            assert listed.status_code == 200
            assert [item["case_id"] for item in listed.json()] == [
                a_high,
                b_mid,
                a_unset,
            ]
            assert [item["priority"] for item in listed.json()] == [10, 8, None]
            assert [item["team_id"] for item in listed.json()] == [
                "TEAM_A",
                "TEAM_B",
                "TEAM_A",
            ]
            for case_id in (a_high, b_mid, a_unset):
                detail = second_director.get(f"/api/clm/zero-touch/cases/{case_id}")
                assert detail.status_code == 200
            assert counters == before_restart

            raw_after_restart = cleanup[database][settings.mongo_case_collection].find_one(
                {"_id": a_high}
            )
            assert raw_after_restart is not None
            assert raw_after_restart["onboarding"]["team_id"] == "TEAM_A"
            assert raw_after_restart["onboarding"]["priority"] == 10
            assert type(raw_after_restart["schema_version"]) is int
            assert raw_after_restart["schema_version"] == 2

            cleared = second_director.patch(
                f"/api/clm/zero-touch/cases/{a_high}/priority",
                json={"priority": None},
                headers={"X-CSRF-Token": csrf_director},
            )
            assert cleared.status_code == 200
    finally:
        assert database.startswith("clm_phase13_test_")
        cleanup.drop_database(database)
        cleanup.close()
