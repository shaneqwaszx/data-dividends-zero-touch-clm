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
            assert all(item["schema_version"] == 11 for item in raw_documents)

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
            assert raw_after_rejected_mutation["schema_version"] == 11

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
            assert raw_after_restart["schema_version"] == 11

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

    from app.domain.zero_touch import (
        AUTOMATION_STAGE_ORDER,
        AutomationStage,
        AutomationStatus,
        BusinessExceptionType,
        validate_automation_record,
    )
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
        assert result.scoped_cases[0].case_elapsed_ms == 45 * 86_400_000
        completed, completion = _record(
            TeamId.TEAM_A, None, AutomationStatus.COMPLETED,
            created_days_ago=2, updated_hours_ago=1, created_by_actor_id="ethan-tan",
        )
        # Read-model helpers omit the retained completion prefix; physical fixtures
        # must satisfy the canonical domain validator before any durable create.
        prefix = tuple(AutomationStage(stage) for stage in AUTOMATION_STAGE_ORDER)
        completion = completion.model_copy(update={
            "completed_stages": prefix,
            "started_at": completed.created_at,
            "metrics": completion.metrics.model_copy(update={
                "automated_stages_completed": len(prefix), "human_interventions": 2,
            }),
            "exceptions": [_resolved_exception(
                completed.case_id, BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
                AutomationStage.DOCUMENT, created_at=completed.created_at,
                resolved_at=completed.created_at + timedelta(milliseconds=duration),
                actor_id="maya-lim",
            ) for duration in (1, 1001)],
        })
        validate_automation_record(completion)
        store.create(DurableCaseSnapshot(
            case_id=completed.case_id, revision=0, onboarding=completed, automation=completion,
            created_at=completed.created_at, updated_at=completed.updated_at,
        ))
        memory, _ = _service_for([(case, automation), (completed, completion)])
        for view in ("team", "mine"):
            observed = service.get_dashboard(_actor("ethan-tan"), scope=view)
            assert observed == memory.get_dashboard(_actor("ethan-tan"), scope=view)
            assert next(item for item in observed.scoped_cases
                        if item.case_id == completed.case_id).case_elapsed_ms == 169_200_000
        resolver = service.get_dashboard(_actor("maya-lim"), scope="mine")
        assert resolver.totals.total_cases == 0 and resolver.scoped_cases == ()
        assert resolver.workload_by_person[0].blockers_resolved == 3
        assert resolver.workload_by_person[0].mean_fix_time_ms == 2_400_334
        # Reversed chronology is accepted by retained domain loading, but may never
        # produce a negative workload/delay projection. Compare both storage modes.
        from app.domain.case_management import CaseTimingDataInvalidError

        for invalid_case, retained in ((case, automation), (completed, completion)):
            original_automation = client[database]["clm_case_snapshots"].find_one(
                {"_id": str(invalid_case.case_id)},
            )["automation"]
            for recorded_resolver in (True, False):
                bad = retained.exceptions[0].model_copy(update={
                    "resolved_at": retained.exceptions[0].created_at - timedelta(seconds=1),
                    "decisions": retained.exceptions[0].decisions if recorded_resolver else (),
                })
                invalid = retained.model_copy(update={"exceptions": [bad]})
                client[database]["clm_case_snapshots"].update_one(
                    {"_id": str(invalid_case.case_id)},
                    {"$set": {
                        "automation.exceptions.0.resolved_at": bad.resolved_at.isoformat(),
                        "automation.exceptions.0.decisions": (
                            original_automation["exceptions"][0]["decisions"]
                            if recorded_resolver else []
                        ),
                    }},
                )
                memory_invalid, _ = _service_for([(invalid_case, invalid)])
                for dashboard in (service, memory_invalid):
                    with pytest.raises(CaseTimingDataInvalidError):
                        dashboard.get_dashboard(_actor("maya-lim"))
            client[database]["clm_case_snapshots"].update_one(
                {"_id": str(invalid_case.case_id)},
                {"$set": {"automation": original_automation}},
            )

    finally:
        try:
            cleanup_ephemeral_mongo_database(client, database)
        finally:
            client.close()


@pytest.mark.parametrize("schema_version", [9, 10])
def test_pr95_r2_activity_validates_creator_before_filter_in_physical_mongo(schema_version):
    from test_phase17_case_activity_real_mongo import _event
    from test_phase18_case_portfolio import _mongo_portfolio_row

    from app.domain.case_management import (
        CaseActivityQuery,
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

    def row(creator, *, team="TEAM_A", version=schema_version):
        from uuid import uuid4

        raw = _mongo_portfolio_row(uuid4())
        raw["schema_version"] = version
        raw["onboarding"]["team_id"] = team
        raw["onboarding"]["created_by_actor_id"] = creator
        raw["automation"]["events"] = [
            _event(UUID(raw["case_id"]), seq, f"2026-09-21T12:00:0{seq}Z")
            for seq in (1, 2, 3)
        ]
        collection.insert_one(raw)
        return raw

    try:
        matching = row("maya-lim")
        row("ethan-tan")  # Valid nonmatching rows never leak into the page.
        row(None)  # Retained nullable creator.
        row(None, version=8)  # Legacy absent creator.
        collection.update_many({"schema_version": 8}, {
            "$unset": {"onboarding.created_by_actor_id": ""},
        })
        row("INVALID", team="TEAM_B")  # Other-team malformed data is irrelevant.
        query = CaseActivityQuery(scope=scope, created_by="maya-lim", limit=2)
        page = store.list_activity(query)
        assert [item.sequence for item in page.items] == [3, 2]
        assert all(str(item.case_id) == matching["case_id"] for item in page.items)
        assert page.has_more
        tail = store.list_activity(query.model_copy(update={"offset": 2}))
        assert [item.sequence for item in tail.items] == [1]
        assert not tail.has_more
        assert store.list_activity(query.model_copy(update={"offset": 3})).items == ()
        malformed = row("INVALID")
        # Creator filtering must not suppress the invalid authorized envelope.
        for bad in ("INVALID", True, 123, [], {}, ""):
            collection.update_one({"_id": malformed["_id"]}, {
                "$set": {"onboarding.created_by_actor_id": bad},
            })
            with pytest.raises(PersistenceDataInvalidError):
                store.list_activity(query)
        # Case selection is still an authorization-constrained validation boundary.
        selected = query.model_copy(update={"case_id": UUID(matching["case_id"])})
        assert len(store.list_activity(selected).items) == 2
    finally:
        try:
            cleanup_ephemeral_mongo_database(client, database)
        finally:
            client.close()



def _pr95_r5_dashboard(store, clock):
    from test_phase13_dashboard import _teams

    from app.persistence.repositories import (
        MongoCasePortfolioRepository,
        MongoOnboardingCaseRepository,
        MongoZeroTouchAutomationRepository,
    )
    from app.services.administration import TeamDirectoryService
    from app.services.authorization import CaseAccessPolicy
    from app.services.case_query import CaseQueryService
    from app.services.dashboard import DashboardService

    teams = _teams()
    automation = MongoZeroTouchAutomationRepository(store)
    return DashboardService(CaseQueryService(
        cases=object(), case_repository=MongoOnboardingCaseRepository(store),
        automation_repository=automation, access_policy=CaseAccessPolicy(), teams=teams,
        portfolio_repository=MongoCasePortfolioRepository(store),
    ), TeamDirectoryService(teams), automation, clock=clock)


@pytest.mark.parametrize("invalid_scope", ["other_team", "excluded_date", "selected"])
def test_pr95_r5_physical_scoped_corruption_and_safe_http(monkeypatch, invalid_scope):
    from test_phase13_dashboard import NOW, _actor
    from test_pr95_r5_scoped_dashboard import fixture

    from app.persistence.mongo_case_store import MongoCaseStore
    from app.services.dashboard import DashboardService

    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p13")
    client = MongoClient(MONGO_URI)
    counters = _install_counting_connectors(monkeypatch)
    try:
        store = MongoCaseStore(client, database=database, collection="clm_case_snapshots")
        store.initialize()
        current = fixture()
        bad = fixture(
            team=TeamId.TEAM_B if invalid_scope == "other_team" else TeamId.TEAM_A,
            days=45 if invalid_scope == "excluded_date" else 1,
        )
        for value in (current, bad):
            store.create(store._decode(value[2]))
        collection = client[database]["clm_case_snapshots"]
        collection.update_one({"_id": str(bad[0].case_id)}, {"$set": {
            "automation.unprojected_unknown": "synthetic-invalid",
        }})
        before = list(collection.find({}))
        service = _pr95_r5_dashboard(store, lambda: NOW)
        original = service.get_dashboard
        monkeypatch.setattr(DashboardService, "get_dashboard", lambda self, actor, **kwargs:
                            original(actor, **kwargs))
        with RawTestClient(create_app(Settings(_env_file=None, app_env="test")),
                           raise_server_exceptions=False) as api:
            _login(api, "maya-lim")
            response = api.get("/api/clm/zero-touch/dashboard?date_range=7d")
            if invalid_scope == "selected":
                assert response.status_code == 503
                assert response.json() == {"detail": {
                    "code": "DASHBOARD_UNAVAILABLE",
                    "message": "Dashboard data is temporarily unavailable.",
                }}
            else:
                assert response.status_code == 200
                assert response.json()["totals"]["total_cases"] == 1
                assert response.json()["scoped_cases"][0]["case_id"] == str(current[0].case_id)
        assert list(collection.find({})) == before
        assert all(value == 0 for value in counters.values())
        if invalid_scope != "selected":
            from app.persistence.errors import PersistenceDataInvalidError
            with pytest.raises(PersistenceDataInvalidError):
                service.get_dashboard(_actor("olivia-koh"), date_range="all")
    finally:
        try:
            cleanup_ephemeral_mongo_database(client, database)
        finally:
            client.close()


@pytest.mark.parametrize("duration, days, expected", [(-1, 1, 503), (-1, 45, 200), (0, 1, 200)])
def test_pr95_r5_physical_stage_duration_error_containment(monkeypatch, duration, days, expected):
    from test_phase13_dashboard import NOW
    from test_pr95_r5_scoped_dashboard import fixture

    from app.persistence.mongo_case_store import MongoCaseStore
    from app.services.dashboard import DashboardService

    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p13")
    client = MongoClient(MONGO_URI)
    try:
        store = MongoCaseStore(client, database=database, collection="clm_case_snapshots")
        store.initialize()
        value = fixture(days=days, duration=duration)
        store.create(store._decode(value[2]))  # Canonical codec deliberately remains unchanged.
        service = _pr95_r5_dashboard(store, lambda: NOW)
        original = service.get_dashboard
        monkeypatch.setattr(DashboardService, "get_dashboard", lambda self, actor, **kwargs:
                            original(actor, **kwargs))
        before = list(client[database]["clm_case_snapshots"].find({}))
        with RawTestClient(create_app(Settings(_env_file=None, app_env="test")),
                           raise_server_exceptions=False) as api:
            _login(api, "maya-lim")
            response = api.get("/api/clm/zero-touch/dashboard?date_range=7d")
            assert response.status_code == expected
            if expected == 503:
                assert response.json() == {"detail": {
                    "code": "DASHBOARD_UNAVAILABLE",
                    "message": "Dashboard data is temporarily unavailable.",
                }}
            elif days == 1:
                assert response.json()["stage_timing"][0]["combined_mean_ms"] == 0
            else:
                assert response.json()["totals"]["total_cases"] == 0
        assert list(client[database]["clm_case_snapshots"].find({})) == before
    finally:
        try:
            cleanup_ephemeral_mongo_database(client, database)
        finally:
            client.close()


def test_pr95_r5_physical_finite_batch_parity_midnight_and_deletion():
    from contextlib import contextmanager
    from datetime import UTC, datetime
    from uuid import uuid4

    from test_phase13_dashboard import NOW, _actor, _service_for
    from test_pr95_r5_scoped_dashboard import fixture

    from app.persistence.mongo_case_store import MongoCaseStore
    from app.persistence.repositories import MongoZeroTouchAutomationRepository

    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p13")
    client = MongoClient(MONGO_URI)
    try:
        store = MongoCaseStore(client, database=database, collection="clm_case_snapshots")
        store.initialize()
        values = [fixture(creator="ethan-tan") for _ in range(201)]
        values.extend((fixture(team=TeamId.TEAM_B), fixture(team=None), fixture(days=45)))
        for value in values:
            store.create(store._decode(value[2]))
        collection = client[database]["clm_case_snapshots"]
        queries = []
        class TrackedCollection:
            def __getattr__(self, name):
                return getattr(collection, name)
            def find(self, query, *args, **kwargs):
                if "_id" in query and "$in" in query["_id"]:
                    queries.append(query)
                return collection.find(query, *args, **kwargs)
        store._collection = TrackedCollection()
        service = _pr95_r5_dashboard(store, lambda: NOW)
        memory, _ = _service_for([(value[0], value[1]) for value in values])
        for actor_id, team_filter in (("maya-lim", None), ("ethan-tan", None),
                                      ("sophia-ng", None), ("olivia-koh", "all"),
                                      ("olivia-koh", "TEAM_A"), ("olivia-koh", "unassigned")):
            for scope in ("team", "mine"):
                before_queries = len(queries)
                actual = service.get_dashboard(
                    _actor(actor_id), team_filter=team_filter, scope=scope,
                )
                assert len(queries) == before_queries + 1
                authorized = memory._case_query.list_cases(
                    _actor(actor_id), team_filter=team_filter,
                )
                assert queries[-1] == {"_id": {"$in": sorted(
                    str(item.case_id) for item in authorized
                )}}
                assert actual == memory.get_dashboard(
                    _actor(actor_id), team_filter=team_filter, scope=scope,
                )
        large = service.get_dashboard(_actor("ethan-tan"), scope="mine")
        assert large.totals.total_cases == 201 and len(large.scoped_cases) == 200
        repo = MongoZeroTouchAutomationRepository(store)
        before_empty = len(queries)
        with repo.capture_for_cases(frozenset()) as empty:
            assert empty.read_selected(frozenset()) == []
        assert len(queries) == before_empty
        ids = frozenset({values[0][0].case_id})
        with repo.capture_for_cases(ids) as guarded:
            with pytest.raises(ValueError):
                guarded.read_selected(frozenset({values[1][0].case_id}))
            with pytest.raises(ValueError):
                guarded.read_selected(ids)
        with pytest.raises(ValueError):
            guarded.read_selected(ids)
        captured_ids = frozenset({values[0][0].case_id, uuid4()})
        with repo.capture_for_cases(captured_ids) as batch:
            client[database]["clm_case_snapshots"].delete_one({"_id": str(values[0][0].case_id)})
            assert [v.case_id for v in batch.read_selected(captured_ids)] == [values[0][0].case_id]
        with repo.capture_for_cases(captured_ids) as batch:
            assert batch.read_selected(captured_ids) == []
        collection = client[database]["clm_case_snapshots"]
        collection.delete_many({})  # This generated test database only; establish midnight fixture.
        crossing = fixture(days=7)
        created = datetime(2026, 9, 1, 16, tzinfo=UTC)
        crossing[2]["onboarding"]["created_at"] = created.isoformat()
        crossing[2]["automation"]["created_at"] = created.isoformat()
        crossing[2]["automation"]["started_at"] = created.isoformat()
        crossing[2]["created_at"] = created.isoformat()
        store.create(store._decode(crossing[2]))
        observations = []
        now = [datetime(2026, 9, 8, 15, 59, 59, 999000, tzinfo=UTC)]
        original_capture = store.capture_for_cases
        captured = []
        @contextmanager
        def capture(ids):
            with original_capture(ids) as batch:
                assert now[0].hour == 15
                captured.append(True)
                now[0] = datetime(2026, 9, 8, 16, tzinfo=UTC)
                yield batch
        store.capture_for_cases = capture
        def clock():
            assert len(captured) == 1
            observations.append(True)
            return now[0]
        midnight = _pr95_r5_dashboard(store, clock)
        result = midnight.get_dashboard(_actor("maya-lim"), date_range="7d")
        assert result.totals.total_cases == 0 and len(observations) == 1
        assert result.data_as_of == datetime(2026, 9, 8, 16, tzinfo=UTC)
    finally:
        try:
            cleanup_ephemeral_mongo_database(client, database)
        finally:
            client.close()
