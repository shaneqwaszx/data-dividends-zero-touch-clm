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
            assert all(item["schema_version"] == 10 for item in raw_documents)

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
            assert raw_after_rejected_mutation["schema_version"] == 10

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
            assert raw_after_restart["schema_version"] == 10

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


@pytest.mark.parametrize("mode", ["memory", "mongo"])
def test_pr95_creator_dashboard_activity_parity_and_authorization(mode: str) -> None:
    """The exact same HTTP assertions exercise both repository implementations."""
    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p13")
    settings = Settings(
        _env_file=None, app_env="test", clm_persistence_mode=mode,
        mongo_uri=MONGO_URI if mode == "mongo" else None, mongo_database=database,
        acra_connector_mode="mock", goldtier_connector_mode="mock",
    )
    cleanup: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    try:
        with RawTestClient(create_app(settings)) as maya:
            app = maya.app
            ethan, sophia = RawTestClient(app), RawTestClient(app)
            director, hr = RawTestClient(app), RawTestClient(app)
            maya_id = _create(maya, _login(maya, "maya-lim"), "202400001A")
            ethan_id = _create(ethan, _login(ethan, "ethan-tan"), "202400002B")
            sophia_id = _create(sophia, _login(sophia, "sophia-ng"), "202400007G")
            _login(director, "olivia-koh")
            _login(hr, "hr-admin")
            endpoint = "/api/clm/zero-touch/dashboard?date_range=all"
            assert maya.get(endpoint + "&scope=mine").json()["totals"]["total_cases"] == 1
            team = ethan.get(endpoint).json()
            assert {row["case_id"] for row in team["scoped_cases"]} == {maya_id, ethan_id}
            assert {row["user_id"] for row in team["workload_by_person"]} == {
                "maya-lim", "ethan-tan",
            }
            assert all(row["created_by_display_name"] for row in team["scoped_cases"])
            assert director.get(endpoint).json()["totals"]["total_cases"] == 3
            assert director.get(endpoint + "&team_filter=TEAM_B").json()["totals"][
                "total_cases"
            ] == 1
            assert maya.get(endpoint + "&team_filter=TEAM_B").status_code == 403
            assert hr.get(endpoint).status_code == 403
            activity = "/api/clm/zero-touch/activity"
            filtered = ethan.get(activity + "?created_by=maya-lim").json()
            assert {row["case_id"] for row in filtered["items"]} == {maya_id}
            assert maya.get(activity + "?created_by=sophia-ng").json()["items"] == []
            selected = director.get(activity + "?created_by=sophia-ng&team_filter=TEAM_B")
            assert {row["case_id"] for row in selected.json()["items"]} == {sophia_id}
            assert hr.get(activity + "?created_by=maya-lim").status_code == 403
            assert maya.get(activity + "?created_by=%7B%22%24ne%22:null%7D").status_code == 422
            hidden = maya.get(activity + f"?case_id={sophia_id}&created_by=maya-lim")
            absent = maya.get(activity + "?case_id=00000000-0000-4000-8000-000000000095")
            assert hidden.status_code == absent.status_code == 404
            assert hidden.json() == absent.json()
    finally:
        try:
            cleanup_ephemeral_mongo_database(cleanup, database)
        finally:
            cleanup.close()


def test_pr95_physical_creator_validation_and_legacy_unknown() -> None:
    from test_phase17_case_activity_real_mongo import _event
    from test_phase18_case_portfolio import _mongo_portfolio_row

    from app.domain.case_management import (
        CaseActivityQuery,
        CasePortfolioQuery,
        CasePortfolioScope,
        PortfolioScopeKind,
    )
    from app.persistence.errors import PersistenceDataInvalidError
    from app.persistence.mongo_case_store import MongoCaseStore

    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p13")
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    collection = client[database]["clm_case_snapshots"]
    store = MongoCaseStore(client, database=database, collection="clm_case_snapshots")
    scope = CasePortfolioScope(kind=PortfolioScopeKind.TEAM, team_id=TeamId.TEAM_A)
    try:
        raw = _mongo_portfolio_row()
        raw["schema_version"] = 10
        raw["onboarding"]["created_by_actor_id"] = "maya-lim"
        raw["automation"]["events"] = [
            _event(UUID(raw["case_id"]), 1, "2026-09-21T12:00:00Z")
        ]
        collection.insert_one(raw)
        assert store.list_portfolio(scope)[0].created_by_actor_id == "maya-lim"
        assert store.list_portfolio_page(CasePortfolioQuery(scope=scope)).items[
            0
        ].created_by_actor_id == "maya-lim"
        assert len(store.list_activity(CaseActivityQuery(
            scope=scope, created_by="maya-lim",
        )).items) == 1
        for invalid in (True, 123, [], {}, "INVALID", ""):
            collection.update_one({"_id": raw["_id"]}, {
                "$set": {"onboarding.created_by_actor_id": invalid},
            })
            for read in (
                lambda: store.list_portfolio(scope),
                lambda: store.list_portfolio_page(CasePortfolioQuery(scope=scope)),
                lambda: store.list_activity(CaseActivityQuery(scope=scope)),
            ):
                with pytest.raises(PersistenceDataInvalidError):
                    read()
        collection.update_one({"_id": raw["_id"]}, {
            "$set": {"schema_version": 8}, "$unset": {"onboarding.created_by_actor_id": ""},
        })
        assert store.list_portfolio(scope)[0].created_by_actor_id is None
        assert store.list_activity(CaseActivityQuery(
            scope=scope, created_by="maya-lim",
        )).items == ()
    finally:
        try:
            cleanup_ephemeral_mongo_database(client, database)
        finally:
            client.close()


def test_pr95_physical_workload_and_legacy_trend_match_memory_after_restart() -> None:
    from datetime import timedelta
    from uuid import uuid4

    from test_phase13_dashboard import (
        NOW,
        _actor,
        _record,
        _resolved_exception,
        _service_for,
        _teams,
    )

    from app.domain.zero_touch import AutomationStage, AutomationStatus, BusinessExceptionType
    from app.persistence.models import DurableCaseSnapshot
    from app.persistence.mongo_case_store import MongoCaseStore
    from app.persistence.repositories import (
        MongoCasePortfolioRepository,
        MongoOnboardingCaseRepository,
        MongoZeroTouchAutomationRepository,
    )
    from app.services.administration import TeamDirectoryService
    from app.services.authorization import CaseAccessPolicy
    from app.services.case_query import CaseQueryService
    from app.services.dashboard import DashboardService

    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p13")
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    try:
        store = MongoCaseStore(client, database=database, collection="clm_case_snapshots")
        case, automation = _record(
            TeamId.TEAM_A, None, AutomationStatus.RUNNING,
            created_days_ago=45, updated_hours_ago=1, created_by_actor_id="ethan-tan",
        )
        resolution = _resolved_exception(
            case.case_id, BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
            AutomationStage.DOCUMENT, created_at=case.created_at,
            resolved_at=case.created_at + timedelta(hours=2), actor_id="maya-lim",
        )
        duplicate = resolution.decisions[0].model_copy(update={"decision_id": uuid4()})
        resolution = resolution.model_copy(update={
            "decisions": (*resolution.decisions, duplicate),
        })
        automation = automation.model_copy(update={
            "started_at": case.created_at, "exceptions": [resolution],
        })
        store.create(DurableCaseSnapshot(
            case_id=case.case_id, revision=0, onboarding=case, automation=automation,
            created_at=case.created_at, updated_at=case.updated_at,
        ))
        # Reconstruct independent adapters from retained bytes, without a write or provider.
        restored = MongoCaseStore(client, database=database, collection="clm_case_snapshots")
        teams = _teams()
        automation_repository = MongoZeroTouchAutomationRepository(restored)
        service = DashboardService(CaseQueryService(
            cases=object(), case_repository=MongoOnboardingCaseRepository(restored),
            automation_repository=automation_repository, access_policy=CaseAccessPolicy(),
            teams=teams, portfolio_repository=MongoCasePortfolioRepository(restored),
        ), TeamDirectoryService(teams), automation_repository, clock=lambda: NOW)
        memory, _ = _service_for([(case, automation)])
        for actor_id in ("maya-lim", "ethan-tan", "sophia-ng", "olivia-koh"):
            for date_range in ("all", "7d", "30d", "90d"):
                for view in ("team", "mine"):
                    assert service.get_dashboard(
                        _actor(actor_id), date_range=date_range, scope=view,
                    ) == memory.get_dashboard(_actor(actor_id), date_range=date_range, scope=view)
        mine = service.get_dashboard(_actor("maya-lim"), scope="mine", date_range="90d")
        assert mine.totals.total_cases == 0 and mine.scoped_cases == ()
        assert len(mine.workload_by_person) == 1
        assert mine.workload_by_person[0].user_id == "maya-lim"
        assert mine.workload_by_person[0].blockers_resolved == 1
        assert mine.workload_by_person[0].mean_fix_time_ms == 7_200_000
        assert service.get_dashboard(
            _actor("maya-lim"), scope="mine", date_range="30d",
        ).workload_by_person == ()
        result = service.get_dashboard(_actor("maya-lim"))
        assert result.totals.total_cases == 1
        assert len(result.historical_trend) == 30
        rows = {row.user_id: row for row in result.workload_by_person}
        assert rows["maya-lim"].open_cases == 0
        assert rows["maya-lim"].blockers_resolved == 1
        assert rows["maya-lim"].mean_fix_time_ms == 7_200_000
        assert rows["ethan-tan"].open_cases == 1
    finally:
        try:
            cleanup_ephemeral_mongo_database(client, database)
        finally:
            client.close()
