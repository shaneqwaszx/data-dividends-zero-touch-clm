from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from phase13_test_settings import ordinary_test_settings
from pydantic import ValidationError

from app.domain.access import SYNTHETIC_PROFILE_BY_ID, AuthenticatedActor, TeamId
from app.domain.case_management import (
    CaseActivityAction,
    CaseActivityQuery,
    CaseActivityRepositoryPage,
    CaseActivityRepositoryRecord,
    CasePortfolioScope,
    PortfolioScopeKind,
    activity_matches_action,
    order_case_activity_records,
)
from app.domain.models import EventOutcome
from app.domain.zero_touch import (
    AutomationEvent,
    AutomationEventType,
    AutomationStage,
    AutomationStatus,
)
from app.main import create_app
from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.mongo_case_store import MongoCaseStore
from app.services.authorization import CaseAccessPolicy
from app.services.case_portfolio_repository import InMemoryCasePortfolioRepository
from app.services.case_query import CaseActivityQueryInvalidError, CaseQueryService

NOW = datetime(2026, 9, 21, 12, 0, 0, 123456, tzinfo=UTC)
CASE_A = UUID("00000000-0000-4000-8000-000000000171")
CASE_B = UUID("00000000-0000-4000-8000-000000000172")


def _event(
    case_id: UUID,
    sequence: int,
    *,
    timestamp: datetime = NOW,
    event_type: AutomationEventType = AutomationEventType.ONBOARDING_CREATED,
    stage: AutomationStage = AutomationStage.REGISTRY,
    outcome: EventOutcome = EventOutcome.SUCCEEDED,
    message: str = "Retained safe event.",
) -> AutomationEvent:
    return AutomationEvent(
        sequence=sequence,
        event_type=event_type,
        status=AutomationStatus.RUNNING,
        stage=stage,
        outcome=outcome,
        timestamp=timestamp,
        case_id=case_id,
        code=None,
        message=message,
    )


def _case(
    case_id: UUID,
    team_id: TeamId | None,
    priority: int | None,
    *,
    created_by_actor_id: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        case_id=case_id,
        team_id=team_id,
        priority=priority,
        created_by_actor_id=created_by_actor_id,
    )


def _automation(case_id: UUID, events: list[AutomationEvent]) -> SimpleNamespace:
    return SimpleNamespace(case_id=case_id, events=events)


def _repository(
    cases: dict[UUID, SimpleNamespace],
    automations: list[SimpleNamespace],
) -> InMemoryCasePortfolioRepository:
    return InMemoryCasePortfolioRepository(
        SimpleNamespace(get=lambda case_id: cases.get(case_id)),  # type: ignore[arg-type]
        SimpleNamespace(list_records=lambda: automations),  # type: ignore[arg-type]
    )


def test_activity_query_requires_explicit_timezone_and_valid_window() -> None:
    scope = CasePortfolioScope(kind=PortfolioScopeKind.GLOBAL)
    with pytest.raises(ValidationError):
        CaseActivityQuery(scope=scope, from_at=datetime(2026, 9, 21))
    with pytest.raises(ValidationError):
        CaseActivityQuery(scope=scope, from_at=NOW, to_at=NOW)

    query = CaseActivityQuery(
        scope=scope,
        from_at=NOW.astimezone(timezone(timedelta(hours=8))),
        to_at=NOW + timedelta(seconds=1),
    )
    assert query.from_at == NOW


def test_action_buckets_preserve_existing_overlapping_semantics() -> None:
    target = CaseActivityRepositoryRecord(
        case_id=CASE_A,
        sequence=1,
        timestamp=NOW,
        event_type=AutomationEventType.MOCK_SUBMISSION_COMPLETED,
        status=AutomationStatus.COMPLETED,
        stage=AutomationStage.MOCK_GOLDTIER,
        outcome=EventOutcome.SUCCEEDED,
        code=None,
        message="Mock submission completed.",
        team_id=TeamId.TEAM_A,
        current_priority=9,
    )
    assert activity_matches_action(target, CaseActivityAction.TARGET)
    assert activity_matches_action(target, CaseActivityAction.COMPLETED)
    assert not activity_matches_action(target, CaseActivityAction.DOCUMENT)

    intelligence = target.model_copy(
        update={
            "event_type": AutomationEventType.INTELLIGENCE_EVALUATED,
            "stage": AutomationStage.OWNERSHIP,
        }
    )
    assert activity_matches_action(intelligence, CaseActivityAction.INTELLIGENCE)
    assert activity_matches_action(intelligence, CaseActivityAction.OWNERSHIP)


def test_memory_activity_scopes_before_events_filters_before_paging_and_orders_ties() -> None:
    cases = {
        CASE_A: _case(CASE_A, TeamId.TEAM_A, 8),
        CASE_B: _case(CASE_B, TeamId.TEAM_B, 2),
    }
    team_a_events = [
        _event(CASE_A, 1, timestamp=NOW - timedelta(microseconds=1)),
        _event(
            CASE_A,
            2,
            event_type=AutomationEventType.DOCUMENT_REVIEW_REQUIRED,
            stage=AutomationStage.DOCUMENT,
            outcome=EventOutcome.REVIEW_REQUIRED,
        ),
    ]
    corrupt_other_team = [_event(CASE_A, 9)]
    repository = _repository(
        cases,
        [
            _automation(CASE_A, team_a_events),
            _automation(CASE_B, corrupt_other_team),
        ],
    )
    query = CaseActivityQuery(
        scope=CasePortfolioScope(kind=PortfolioScopeKind.TEAM, team_id=TeamId.TEAM_A),
        stage=AutomationStage.DOCUMENT,
        outcome=EventOutcome.REVIEW_REQUIRED,
        from_at=NOW,
        to_at=NOW + timedelta(seconds=1),
        limit=1,
    )

    page = repository.list_activity(query)

    assert [(item.case_id, item.sequence) for item in page.items] == [(CASE_A, 2)]
    assert not page.has_more
    assert page.items[0].current_priority == 8


def test_memory_activity_filters_by_created_by_actor_id() -> None:
    cases = {
        CASE_A: _case(CASE_A, TeamId.TEAM_A, 8, created_by_actor_id="maya-lim"),
        CASE_B: _case(CASE_B, TeamId.TEAM_A, 2, created_by_actor_id="ethan-tan"),
    }
    repository = _repository(
        cases,
        [
            _automation(CASE_A, [_event(CASE_A, 1)]),
            _automation(CASE_B, [_event(CASE_B, 1)]),
        ],
    )
    query = CaseActivityQuery(
        scope=CasePortfolioScope(kind=PortfolioScopeKind.TEAM, team_id=TeamId.TEAM_A),
        created_by="maya-lim",
    )

    page = repository.list_activity(query)

    assert [item.case_id for item in page.items] == [CASE_A]


def test_memory_activity_rejects_malformed_scoped_sequence_and_naive_time() -> None:
    case = _case(CASE_A, TeamId.TEAM_A, None)
    repository = _repository({CASE_A: case}, [_automation(CASE_A, [_event(CASE_A, 2)])])
    query = CaseActivityQuery(
        scope=CasePortfolioScope(kind=PortfolioScopeKind.TEAM, team_id=TeamId.TEAM_A)
    )
    with pytest.raises(ValueError, match="identity"):
        repository.list_activity(query)

    naive = _event(CASE_A, 1).model_copy(update={"timestamp": datetime(2026, 9, 21)})
    repository = _repository({CASE_A: case}, [_automation(CASE_A, [naive])])
    with pytest.raises(ValidationError):
        repository.list_activity(query)


def test_global_order_uses_case_uuid_ascending_and_sequence_descending_for_ties() -> None:
    records = [
        CaseActivityRepositoryRecord(
            case_id=case_id,
            sequence=sequence,
            timestamp=NOW,
            event_type=AutomationEventType.ONBOARDING_CREATED,
            status=AutomationStatus.RUNNING,
            stage=AutomationStage.REGISTRY,
            outcome=EventOutcome.SUCCEEDED,
            code=None,
            message="Created.",
        )
        for case_id, sequence in ((CASE_B, 1), (CASE_A, 1), (CASE_A, 2))
    ]
    assert [(item.case_id, item.sequence) for item in order_case_activity_records(records)] == [
        (CASE_A, 2),
        (CASE_A, 1),
        (CASE_B, 1),
    ]


class _ActivityCollection:
    def __init__(self, result: list[dict[str, object]]) -> None:
        self.result = result
        self.calls: list[tuple[list[dict[str, object]], dict[str, object]]] = []

    def aggregate(self, pipeline: list[dict[str, object]], **kwargs: object):
        self.calls.append((pipeline, kwargs))
        return self.result


def _mongo_row(case_id: UUID = CASE_A) -> dict[str, object]:
    return {
        "case_id": str(case_id),
        "sequence": 2,
        "timestamp": "2026-09-21T12:00:00.123456Z",
        "event_type": "DOCUMENT_REVIEW_REQUIRED",
        "status": "WAITING_FOR_REVIEW",
        "stage": "DOCUMENT",
        "outcome": "REVIEW_REQUIRED",
        "code": "DOCUMENT_LOW_CONFIDENCE",
        "message": "Review is required.",
        "team_id": "TEAM_A",
        "current_priority": 7,
    }


def test_mongo_activity_uses_one_bounded_aggregation_and_limit_lookahead() -> None:
    collection = _ActivityCollection([{"invalid": [], "rows": [_mongo_row(), _mongo_row()]}])
    store = object.__new__(MongoCaseStore)
    store._collection = collection  # type: ignore[attr-defined]  # noqa: SLF001
    query = CaseActivityQuery(
        scope=CasePortfolioScope(kind=PortfolioScopeKind.TEAM, team_id=TeamId.TEAM_A),
        action=CaseActivityAction.DOCUMENT,
        limit=1,
    )

    page = store.list_activity(query)

    assert len(collection.calls) == 1
    pipeline, options = collection.calls[0]
    assert pipeline[0] == {
        "$match": {"automation": {"$ne": None}, "onboarding.team_id": "TEAM_A"}
    }
    assert options == {"allowDiskUse": False, "maxTimeMS": 5_000}
    rows_pipeline = pipeline[2]["$facet"]["rows"]  # type: ignore[index]
    assert {"$limit": 2} in rows_pipeline
    assert page.has_more
    assert len(page.items) == 1
    assert page.items[0].timestamp.microsecond == 123456


def test_mongo_activity_invalid_signal_fails_closed() -> None:
    store = object.__new__(MongoCaseStore)
    store._collection = _ActivityCollection(  # type: ignore[attr-defined]  # noqa: SLF001
        [{"invalid": [{"invalid": True}], "rows": []}]
    )
    with pytest.raises(PersistenceDataInvalidError):
        store.list_activity(
            CaseActivityQuery(scope=CasePortfolioScope(kind=PortfolioScopeKind.GLOBAL))
        )


class _ActivityProbe:
    def list_authorized(self, scope: object, *, status: object = None) -> list[object]:
        del scope, status
        return []

    def list_activity(self, query: CaseActivityQuery) -> CaseActivityRepositoryPage:
        record = CaseActivityRepositoryRecord(
            **_mongo_row(),
        )
        assert query.scope.kind == PortfolioScopeKind.TEAM
        return CaseActivityRepositoryPage(
            items=(record,), offset=query.offset, limit=query.limit, has_more=False
        )


class _Teams:
    def get(self, team_id: TeamId) -> SimpleNamespace | None:
        return SimpleNamespace(team_id=team_id, client_scope_label="Alpha")

    def list(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(team_id=TeamId.TEAM_A, client_scope_label="Alpha")]


def test_query_service_resolves_current_scope_metadata_once() -> None:
    actor = AuthenticatedActor(profile=SYNTHETIC_PROFILE_BY_ID["maya-lim"])
    service = CaseQueryService(
        cases=object(),  # type: ignore[arg-type]
        case_repository=object(),  # type: ignore[arg-type]
        automation_repository=object(),  # type: ignore[arg-type]
        access_policy=CaseAccessPolicy(),
        teams=_Teams(),  # type: ignore[arg-type]
        portfolio_repository=_ActivityProbe(),
    )

    page = service.list_activity(actor)

    assert page.items[0].current_priority == 7
    assert page.items[0].current_client_scope_label == "Alpha"
    with pytest.raises(CaseActivityQueryInvalidError):
        service.list_activity(actor, from_at=NOW, to_at=NOW)


def test_activity_api_is_portfolio_authorized_and_uses_safe_validation() -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    login = client.post(
        "/api/auth/login",
        json={"user_id": "maya-lim", "password": TEST_PASSWORD},
    )
    assert login.status_code == 200

    assert client.get("/api/clm/zero-touch/activity").status_code == 200
    assert client.get("/api/clm/zero-touch/activity?limit=101").status_code == 422
    assert client.get("/api/clm/zero-touch/activity?action=UNKNOWN").status_code == 422
    assert client.get("/api/clm/zero-touch/activity?from=2026-09-21T12:00:00").status_code == 422
    missing = client.get(f"/api/clm/zero-touch/activity?case_id={CASE_A}")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "CASE_NOT_FOUND"


def test_activity_api_preserves_non_enumerating_team_and_capability_boundaries() -> None:
    application = create_app(ordinary_test_settings())
    team_a = RawTestClient(application)
    team_b = RawTestClient(application)
    director = RawTestClient(application)
    hr = RawTestClient(application)
    team_b_csrf = ""

    for client, user_id in (
        (team_a, "maya-lim"),
        (team_b, "sophia-ng"),
        (director, "olivia-koh"),
        (hr, "biz-ops"),
    ):
        login = client.post(
            "/api/auth/login",
            json={"user_id": user_id, "password": TEST_PASSWORD},
        )
        assert login.status_code == 200
        if user_id == "sophia-ng":
            team_b_csrf = login.json()["csrf_token"]

    created = team_b.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "202400001A"},
        headers={"X-CSRF-Token": team_b_csrf},
    )
    assert created.status_code == 201
    other_team_case = created.json()["case"]["case_id"]

    inaccessible = team_a.get(
        f"/api/clm/zero-touch/activity?case_id={other_team_case}"
    )
    absent = team_a.get(f"/api/clm/zero-touch/activity?case_id={CASE_A}")
    assert inaccessible.status_code == absent.status_code == 404
    assert inaccessible.json() == absent.json()
    assert team_a.get(
        "/api/clm/zero-touch/activity?team_filter=TEAM_B"
    ).status_code == 403
    assert hr.get("/api/clm/zero-touch/activity").status_code == 403
    assert director.get(
        "/api/clm/zero-touch/activity?team_filter=%7B%22%24ne%22%3Anull%7D"
    ).status_code == 422
    assert director.get(
        "/api/clm/zero-touch/activity?action=%7B%22%24ne%22%3Anull%7D"
    ).status_code == 422
