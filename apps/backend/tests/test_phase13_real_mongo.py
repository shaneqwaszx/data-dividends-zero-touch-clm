"""Genuine Mongo restart proof for Phase 13 team ownership and priority."""

from __future__ import annotations

import os
from typing import Any
from uuid import UUID

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from pymongo import MongoClient
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)
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


def _create(
    client: RawTestClient,
    csrf: str,
    uen: str,
    *,
    priority: int | None | object = ...,
) -> str:
    body: dict[str, object] = {"uen": uen}
    if priority is not ...:
        body["priority"] = priority
    response = client.post(
        "/api/clm/zero-touch/cases",
        json=body,
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 201, response.text
    return response.json()["case"]["case_id"]


def test_real_mongo_restart_preserves_team_scope_priority_and_provider_free_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p13")
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
        with RawTestClient(create_app(settings)) as first_a, RawTestClient(first_a.app) as first_b:
            csrf_a = _login(first_a, "maya-lim")
            csrf_b = _login(first_b, "sophia-ng")
            a_high = _create(first_a, csrf_a, "202400001A", priority=10)
            a_unset = _create(first_a, csrf_a, "202400002B")
            b_mid = _create(first_b, csrf_b, "202400007G", priority=8)

            collection = cleanup[database][settings.mongo_case_collection]
            raw_documents = list(collection.find({}))
            assert len(raw_documents) == 3
            assert all(type(item["schema_version"]) is int for item in raw_documents)
            assert all(item["schema_version"] == 9 for item in raw_documents)

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
            assert raw_after_rejected_mutation["schema_version"] == 9

            assert [
                item["case_id"] for item in first_a.get("/api/clm/zero-touch/cases").json()
            ] == [a_high, a_unset]
            assert [
                item["case_id"] for item in first_b.get("/api/clm/zero-touch/cases").json()
            ] == [b_mid]
            dashboard_a = first_a.get("/api/clm/zero-touch/dashboard")
            dashboard_b = first_b.get("/api/clm/zero-touch/dashboard")
            assert dashboard_a.status_code == dashboard_b.status_code == 200
            assert dashboard_a.json()["totals"]["total_cases"] == 2
            assert dashboard_b.json()["totals"]["total_cases"] == 1
            assert {item["team_id"] for item in dashboard_a.json()["recent_cases"]} == {"TEAM_A"}
            assert {item["team_id"] for item in dashboard_b.json()["recent_cases"]} == {"TEAM_B"}

        before_restart = counters.copy()
        with (
            RawTestClient(create_app(settings)) as second_director,
            RawTestClient(second_director.app) as second_a,
            RawTestClient(second_director.app) as second_b,
        ):
            csrf_director = _login(second_director, "olivia-koh")
            _login(second_a, "maya-lim")
            _login(second_b, "sophia-ng")
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

            dashboard_a = second_a.get("/api/clm/zero-touch/dashboard").json()
            dashboard_b = second_b.get("/api/clm/zero-touch/dashboard").json()
            dashboard_director = second_director.get("/api/clm/zero-touch/dashboard").json()
            assert dashboard_a["totals"]["total_cases"] == 2
            assert dashboard_b["totals"]["total_cases"] == 1
            assert dashboard_director["totals"]["total_cases"] == 3
            assert [item["team_id"] for item in dashboard_a["team_breakdown"]] == ["TEAM_A"]
            assert [item["team_id"] for item in dashboard_b["team_breakdown"]] == ["TEAM_B"]
            assert [item["team_id"] for item in dashboard_director["team_breakdown"]] == [
                "TEAM_A",
                "TEAM_B",
            ]
            assert [item["priority"] for item in dashboard_director["top_active_cases"]] == [
                10,
                8,
                None,
            ]
            assert counters == before_restart

            raw_after_restart = cleanup[database][settings.mongo_case_collection].find_one(
                {"_id": a_high}
            )
            assert raw_after_restart is not None
            assert raw_after_restart["onboarding"]["team_id"] == "TEAM_A"
            assert raw_after_restart["onboarding"]["priority"] == 10
            assert type(raw_after_restart["schema_version"]) is int
            assert raw_after_restart["schema_version"] == 9

            cleared = second_director.patch(
                f"/api/clm/zero-touch/cases/{a_high}/priority",
                json={"priority": None},
                headers={"X-CSRF-Token": csrf_director},
            )
            assert cleared.status_code == 200
    finally:
        try:
            cleanup_ephemeral_mongo_database(cleanup, database)
        finally:
            cleanup.close()
