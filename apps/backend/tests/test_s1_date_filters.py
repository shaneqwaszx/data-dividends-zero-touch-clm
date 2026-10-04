"""Created-date filters preserve Singapore boundaries, scope and page ordering."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from phase13_test_settings import ordinary_test_settings
from pydantic import ValidationError
from s1_date_filter_fixtures import (
    END,
    OBSERVED,
    START,
    date_filter_documents,
    memory_date_filter_repository,
)

from app.domain.access import SYNTHETIC_PROFILE_BY_ID, AuthenticatedActor, TeamId
from app.domain.case_management import (
    CasePortfolioQuery,
    CasePortfolioScope,
    PortfolioScopeKind,
    case_created_date_bounds,
)
from app.domain.zero_touch import AutomationStatus
from app.main import create_app
from app.persistence.mongo_case_store import MongoCaseStore
from app.services.authorization import CaseAccessPolicy
from app.services.case_query import (
    CasePortfolioQueryInvalidError,
    CaseQueryService,
    CaseTeamFilterForbiddenError,
)

DAY = date(2026, 10, 4)
SCOPE = CasePortfolioScope(kind=PortfolioScopeKind.TEAM, team_id=TeamId.TEAM_A)


def test_singapore_inclusive_dates_become_exact_half_open_utc_bounds() -> None:
    assert case_created_date_bounds(DAY, DAY) == (START, END)
    assert case_created_date_bounds(DAY, None) == (START, None)
    assert case_created_date_bounds(None, DAY) == (None, END)
    assert case_created_date_bounds(None, None) == (None, None)
    assert case_created_date_bounds(date(2024, 2, 29), date(2024, 2, 29)) == (
        datetime(2024, 2, 28, 16, tzinfo=UTC), datetime(2024, 2, 29, 16, tzinfo=UTC),
    )
    for invalid in ((DAY, DAY - timedelta(days=1)), (date.min, None), (None, date.max)):
        with pytest.raises(ValueError):
            case_created_date_bounds(*invalid)


def test_domain_rejects_naive_or_empty_windows_and_normalizes_offsets() -> None:
    with pytest.raises(ValidationError):
        CasePortfolioQuery(scope=SCOPE, created_from_at=datetime(2026, 10, 4))
    with pytest.raises(ValidationError):
        CasePortfolioQuery(scope=SCOPE, created_from_at=START, created_to_at=START)
    query = CasePortfolioQuery(scope=SCOPE, created_from_at="2026-10-04T00:00:00+08:00")
    assert query.created_from_at == START


def test_memory_date_filter_uses_automation_creation_before_scope_sort_and_paging() -> None:
    documents = date_filter_documents()
    repository = memory_date_filter_repository(documents)
    first = repository.list_page(CasePortfolioQuery(
        scope=SCOPE, created_from_at=START, created_to_at=END, limit=1,
    ))
    assert str(first.items[0].case_id) == documents[1]["case_id"]
    assert first.has_more
    tail = repository.list_page(CasePortfolioQuery(
        scope=SCOPE, created_from_at=START, created_to_at=END, limit=2, offset=1,
    ))
    assert [str(item.case_id) for item in tail.items] == [
        documents[2]["case_id"], documents[3]["case_id"],
    ]
    assert not tail.has_more


def _service() -> CaseQueryService:
    return CaseQueryService(
        cases=object(),  # type: ignore[arg-type]
        case_repository=object(),  # type: ignore[arg-type]
        automation_repository=object(),  # type: ignore[arg-type]
        access_policy=CaseAccessPolicy(),
        teams=SimpleNamespace(get=lambda _: object()),  # type: ignore[arg-type]
        portfolio_repository=memory_date_filter_repository(date_filter_documents()),
        clock=lambda: OBSERVED,
    )


def test_both_service_paths_compose_completed_dates_and_authoritative_actor_scope() -> None:
    service = _service()
    actor = AuthenticatedActor(profile=SYNTHETIC_PROFILE_BY_ID["maya-lim"])
    kwargs = {"status": AutomationStatus.COMPLETED, "created_from": DAY, "created_to": DAY}
    legacy = service.list_cases(actor, **kwargs)
    page = service.list_portfolio(actor, **kwargs, limit=1, offset=1)
    assert len(legacy) == 2
    assert page.items[0].case_id == legacy[1].case_id
    assert not page.has_more
    for list_method in (service.list_cases, service.list_portfolio):
        with pytest.raises(CaseTeamFilterForbiddenError):
            list_method(actor, created_from=DAY, team_filter="TEAM_B")
        with pytest.raises(CasePortfolioQueryInvalidError):
            list_method(actor, created_from=DAY, created_to=DAY - timedelta(days=1))
    director = AuthenticatedActor(profile=SYNTHETIC_PROFILE_BY_ID["olivia-koh"])
    director_page = service.list_portfolio(
        director, created_from=DAY, created_to=DAY, team_filter="TEAM_B",
    )
    assert [item.team_id for item in director_page.items] == [TeamId.TEAM_B]


class _PipelineProbe:
    def __init__(self) -> None:
        self.pipeline: list[dict[str, object]] = []

    def aggregate(self, pipeline: list[dict[str, object]], **_kwargs: object):
        self.pipeline = pipeline
        return [{"invalid": [], "rows": []}]


def test_mongo_creation_predicates_use_lossless_timestamp_before_page_window() -> None:
    collection = _PipelineProbe()
    store = object.__new__(MongoCaseStore)
    store._collection = collection  # type: ignore[attr-defined]  # noqa: SLF001
    store.list_portfolio_page(CasePortfolioQuery(
        scope=SCOPE, created_from_at=START, created_to_at=END, limit=1, offset=1,
    ))
    assert collection.pipeline[0] == {
        "$match": {"automation": {"$ne": None}, "onboarding.team_id": "TEAM_A"},
    }
    rows = collection.pipeline[3]["$facet"]["rows"]  # type: ignore[index]
    conditions = rows[1]["$match"]["$and"]
    assert conditions[0]["$expr"]["$gte"][1] == "2026-10-03T16:00:00.000000Z"
    assert conditions[1]["$expr"]["$lt"][1] == "2026-10-04T16:00:00.000000Z"
    assert "$automation.created_at" in repr(conditions)
    assert rows[4] == {"$skip": 1}
    assert rows[5] == {"$limit": 2}


@pytest.mark.parametrize("path", ["cases", "case-portfolio"])
@pytest.mark.parametrize(
    ("created_at", "expected_in_day", "expected_next_day"),
    [(START, 3, 0), (END - timedelta(microseconds=1), 3, 0), (END, 0, 3)],
)
def test_api_date_filters_validate_range_and_scope_and_include_selected_day(
    path: str, created_at: datetime, expected_in_day: int, expected_next_day: int,
) -> None:
    client = RawTestClient(create_app(
        ordinary_test_settings(), e2e_portfolio_seed_count=3,
        clock=lambda: created_at,
    ))
    assert client.post("/api/auth/login", json={
        "user_id": "maya-lim", "password": TEST_PASSWORD,
    }).status_code == 200
    endpoint = f"/api/clm/zero-touch/{path}"
    selected = client.get(f"{endpoint}?created_from=2026-10-04&created_to=2026-10-04")
    assert selected.status_code == 200
    body = selected.json()
    assert len(body if path == "cases" else body["items"]) == expected_in_day
    next_day = client.get(f"{endpoint}?created_from=2026-10-05")
    assert next_day.status_code == 200
    body = next_day.json()
    assert len(body if path == "cases" else body["items"]) == expected_next_day
    for query in (
        "created_from=2026-10-05&created_to=2026-10-04",
        "created_from=not-a-date", "created_to=2026-02-30", "created_to=9999-12-31",
    ):
        assert client.get(f"{endpoint}?{query}").status_code == 422
    assert client.get(f"{endpoint}?created_from=2026-10-04&team_filter=TEAM_B").status_code == 403
    assert client.get(
        f"{endpoint}?created_from=2026-10-05&created_to=2026-10-04&team_filter=TEAM_B"
    ).status_code == 403
