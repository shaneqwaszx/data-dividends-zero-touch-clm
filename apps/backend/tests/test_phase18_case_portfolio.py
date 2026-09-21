from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from phase13_test_settings import ordinary_test_settings
from pydantic import ValidationError

from app.domain.access import SYNTHETIC_PROFILE_BY_ID, AuthenticatedActor, TeamId
from app.domain.case_management import (
    CasePortfolioPage,
    CasePortfolioQuery,
    CasePortfolioRecord,
    CasePortfolioScope,
    PortfolioScopeKind,
    PriorityFilter,
    PrioritySort,
    case_portfolio_matches,
    case_portfolio_search_pattern,
    order_case_portfolio_records,
)
from app.domain.jurisdiction import JurisdictionCode
from app.domain.zero_touch import (
    AutomationStage,
    AutomationStatus,
    BusinessExceptionStatus,
    BusinessExceptionType,
)
from app.main import create_app
from app.persistence.errors import (
    PersistenceDataInvalidError,
    PersistenceSchemaUnsupportedError,
    PersistenceUnavailableError,
)
from app.persistence.mongo_case_store import MongoCaseStore
from app.services.authorization import CaseAccessPolicy, RouteAccess, classify_route
from app.services.case_portfolio_repository import InMemoryCasePortfolioRepository
from app.services.case_query import CaseQueryService

NOW = datetime(2026, 9, 21, 12, 0, 0, 123456, tzinfo=UTC)
CASE_A = UUID("00000000-0000-4000-8000-000000000181")
CASE_B = UUID("00000000-0000-4000-8000-000000000182")
CASE_C = UUID("00000000-0000-4000-8000-000000000183")


def _record(
    case_id: UUID,
    *,
    priority: int | None,
    updated_at: datetime = NOW,
    uen: str = "202400001A",
    name: str | None = "MERLION PTE. LTD.",
    jurisdiction: JurisdictionCode | None = JurisdictionCode.SINGAPORE,
    exception_types: tuple[BusinessExceptionType, ...] = (),
) -> CasePortfolioRecord:
    return CasePortfolioRecord(
        case_id=case_id,
        requested_uen=uen,
        legal_name=name,
        resolved_jurisdiction=jurisdiction,
        team_id=TeamId.TEAM_A,
        priority=priority,
        status=AutomationStatus.WAITING_FOR_REVIEW,
        current_stage=AutomationStage.DOCUMENT,
        created_at=NOW - timedelta(days=1),
        updated_at=updated_at,
        completed_at=None,
        active_exception_count=len(exception_types),
        active_exception_types=exception_types,
        human_interventions=0,
        final_outcome=None,
        mock_goldtier_party_id=None,
    )


def test_query_normalizes_bounded_literal_search_and_composes_filters() -> None:
    scope = CasePortfolioScope(kind=PortfolioScopeKind.GLOBAL)
    query = CasePortfolioQuery(
        scope=scope,
        priority_filter=PriorityFilter.P9,
        attention_type=BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
        jurisdiction=JurisdictionCode.SINGAPORE,
        search="  MERLION.*[$where]  ",
    )
    assert query.search == "MERLION.*[$where]"
    assert not case_portfolio_matches(
        _record(
            CASE_A,
            priority=9,
            exception_types=(BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,),
        ),
        query,
    )
    literal = query.model_copy(update={"search": "merlion"})
    assert case_portfolio_matches(
        _record(
            CASE_A,
            priority=9,
            exception_types=(BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,),
        ),
        literal,
    )
    assert case_portfolio_matches(
        _record(CASE_A, priority=9),
        CasePortfolioQuery(scope=scope, search=str(CASE_A).upper()),
    )
    assert CasePortfolioQuery(scope=scope, search="   ").search is None
    with pytest.raises(ValidationError):
        CasePortfolioQuery(scope=scope, search="x" * 129)


@pytest.mark.parametrize(
    ("name", "search"),
    [
        ("STRA\u1e9eE PTE. LTD.", "strasse"),
        ("\u0130", "i"),
        ("\u0131", "i"),
    ],
)
def test_memory_search_has_engine_independent_ascii_case_semantics(
    name: str,
    search: str,
) -> None:
    scope = CasePortfolioScope(kind=PortfolioScopeKind.GLOBAL)
    record = _record(CASE_A, priority=9, name=name)

    assert not case_portfolio_matches(
        record,
        CasePortfolioQuery(scope=scope, search=search),
    )


def test_order_preserves_priority_direction_ties_and_unset_tail() -> None:
    records = [
        _record(CASE_A, priority=4, updated_at=NOW),
        _record(CASE_B, priority=4, updated_at=NOW),
        _record(CASE_C, priority=None, updated_at=NOW + timedelta(days=2)),
        _record(UUID("00000000-0000-4000-8000-000000000184"), priority=8),
    ]
    assert [item.case_id for item in order_case_portfolio_records(
        records, PrioritySort.HIGHEST_FIRST
    )] == [
        UUID("00000000-0000-4000-8000-000000000184"),
        CASE_B,
        CASE_A,
        CASE_C,
    ]
    assert [item.priority for item in order_case_portfolio_records(
        records, PrioritySort.LOWEST_FIRST
    )] == [4, 4, 8, None]


def test_memory_page_scopes_before_content_and_correlates_open_attention() -> None:
    exception_a = SimpleNamespace(
        status=BusinessExceptionStatus.OPEN,
        exception_type=BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
    )
    resolved_b = SimpleNamespace(
        status=BusinessExceptionStatus.RESOLVED,
        exception_type=BusinessExceptionType.OWNERSHIP_CYCLE,
    )
    case_a = SimpleNamespace(
        case_id=CASE_A,
        requested_uen="202400001A",
        entity=SimpleNamespace(legal_name="MERLION PTE. LTD."),
        jurisdiction_resolution=SimpleNamespace(
            resolved_jurisdiction=JurisdictionCode.SINGAPORE
        ),
        team_id=TeamId.TEAM_A,
        priority=9,
        goldtier_result=None,
    )
    case_b = SimpleNamespace(case_id=CASE_B, team_id=TeamId.TEAM_B)
    automation_a = SimpleNamespace(
        case_id=CASE_A,
        status=AutomationStatus.WAITING_FOR_REVIEW,
        current_stage=AutomationStage.DOCUMENT,
        created_at=NOW,
        updated_at=NOW,
        completed_at=None,
        exceptions=[exception_a, resolved_b],
        active_exceptions=[exception_a],
        metrics=SimpleNamespace(human_interventions=0, final_outcome=None),
    )
    corrupt_other_team = SimpleNamespace(case_id=CASE_B)
    cases = {CASE_A: case_a, CASE_B: case_b}
    repository = InMemoryCasePortfolioRepository(
        SimpleNamespace(get=lambda case_id: cases.get(case_id)),  # type: ignore[arg-type]
        SimpleNamespace(  # type: ignore[arg-type]
            list_records=lambda: [automation_a, corrupt_other_team]
        ),
    )
    scope = CasePortfolioScope(kind=PortfolioScopeKind.TEAM, team_id=TeamId.TEAM_A)
    matching = repository.list_page(
        CasePortfolioQuery(
            scope=scope,
            attention_type=BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
            search="merlion",
            limit=1,
        )
    )
    assert [item.case_id for item in matching.items] == [CASE_A]
    assert not matching.has_more
    nonmatching = repository.list_page(
        CasePortfolioQuery(
            scope=scope,
            attention_type=BusinessExceptionType.OWNERSHIP_CYCLE,
        )
    )
    assert nonmatching.items == ()


class _AggregateCollection:
    def __init__(self, result: list[dict[str, object]]) -> None:
        self.result = result
        self.calls: list[tuple[list[dict[str, object]], dict[str, object]]] = []

    def aggregate(self, pipeline: list[dict[str, object]], **kwargs: object):
        self.calls.append((pipeline, kwargs))
        return self.result


def _mongo_portfolio_row(case_id: UUID = CASE_A) -> dict[str, object]:
    return {
        "_id": str(case_id),
        "schema_version": 4,
        "case_id": str(case_id),
        "revision": 1,
        "onboarding": {
            "case_id": str(case_id),
            "team_id": "TEAM_A",
            "priority": 9,
            "requested_uen": "202400001A",
            "entity": {"legal_name": "MERLION PTE. LTD."},
            "jurisdiction_resolution": {"resolved_jurisdiction": "SG"},
        },
        "automation": {
            "case_id": str(case_id),
            "status": "WAITING_FOR_REVIEW",
            "current_stage": "DOCUMENT",
            "created_at": "2026-09-21T11:00:00.123456Z",
            "updated_at": "2026-09-21T12:00:00.123456Z",
            "completed_at": None,
            "exceptions": [
                {
                    "status": "OPEN",
                    "exception_type": "DOCUMENT_LOW_CONFIDENCE",
                }
            ],
            "metrics": {"human_interventions": 0, "final_outcome": None},
        },
    }


def test_mongo_page_is_one_scoped_bounded_escaped_aggregation() -> None:
    collection = _AggregateCollection(
        [{"invalid": [], "rows": [_mongo_portfolio_row(), _mongo_portfolio_row()]}]
    )
    store = object.__new__(MongoCaseStore)
    store._collection = collection  # type: ignore[attr-defined]  # noqa: SLF001
    query = CasePortfolioQuery(
        scope=CasePortfolioScope(kind=PortfolioScopeKind.TEAM, team_id=TeamId.TEAM_A),
        attention_type=BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
        search=".*[$where]",
        limit=1,
    )

    page = store.list_portfolio_page(query)

    assert len(collection.calls) == 1
    pipeline, options = collection.calls[0]
    assert pipeline[0] == {
        "$match": {"automation": {"$ne": None}, "onboarding.team_id": "TEAM_A"}
    }
    assert options == {"allowDiskUse": False, "maxTimeMS": 5_000}
    assert "$set" in pipeline[1]
    assert "_portfolio_source_valid" in pipeline[1]["$set"]  # type: ignore[index]
    rows = pipeline[3]["$facet"]["rows"]  # type: ignore[index]
    assert {"$limit": 2} in rows
    row_match = rows[1]["$match"]["$and"]  # type: ignore[index]
    search_clauses = row_match[-1]["$or"]
    assert {
        clause[next(iter(clause))]["$regex"]  # type: ignore[index]
        for clause in search_clauses
    } == {case_portfolio_search_pattern(".*[$where]")}
    assert all(
        "$options" not in clause[next(iter(clause))]  # type: ignore[index]
        for clause in search_clauses
    )
    assert "$elemMatch" in repr(row_match[0])
    assert page.has_more
    assert len(page.items) == 1


def test_mongo_page_fails_closed_on_scoped_invalid_signal() -> None:
    store = object.__new__(MongoCaseStore)
    store._collection = _AggregateCollection(  # type: ignore[attr-defined]  # noqa: SLF001
        [{"invalid": [{"invalid": True}], "rows": []}]
    )
    with pytest.raises(PersistenceDataInvalidError):
        store.list_portfolio_page(
            CasePortfolioQuery(scope=CasePortfolioScope(kind=PortfolioScopeKind.GLOBAL))
        )


class _PageProbe:
    def __init__(self) -> None:
        self.query: CasePortfolioQuery | None = None

    def list_authorized(self, scope: object, *, status: object = None) -> list[object]:
        del scope, status
        return []

    def list_activity(self, query: object) -> object:
        raise AssertionError(query)

    def list_page(self, query: CasePortfolioQuery) -> CasePortfolioPage:
        self.query = query
        return CasePortfolioPage(
            items=(), offset=query.offset, limit=query.limit, has_more=False
        )


def test_service_resolves_actor_scope_before_normalized_page_query() -> None:
    probe = _PageProbe()
    service = CaseQueryService(
        cases=object(),  # type: ignore[arg-type]
        case_repository=object(),  # type: ignore[arg-type]
        automation_repository=object(),  # type: ignore[arg-type]
        access_policy=CaseAccessPolicy(),
        teams=object(),  # type: ignore[arg-type]
        portfolio_repository=probe,
    )
    actor = AuthenticatedActor(profile=SYNTHETIC_PROFILE_BY_ID["maya-lim"])

    service.list_portfolio(actor, search="  MERLION  ", offset=10, limit=25)

    assert probe.query is not None
    assert probe.query.scope == CasePortfolioScope(
        kind=PortfolioScopeKind.TEAM, team_id=TeamId.TEAM_A
    )
    assert probe.query.search == "MERLION"
    assert (probe.query.offset, probe.query.limit) == (10, 25)


def test_api_preserves_old_array_and_adds_safe_authorized_page() -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    login = client.post(
        "/api/auth/login",
        json={"user_id": "maya-lim", "password": TEST_PASSWORD},
    )
    assert login.status_code == 200

    old = client.get("/api/clm/zero-touch/cases")
    page = client.get("/api/clm/zero-touch/case-portfolio")
    assert old.status_code == 200 and isinstance(old.json(), list)
    assert page.status_code == 200
    assert page.json() == {"items": [], "offset": 0, "limit": 50, "has_more": False}
    policy, parameters = classify_route("GET", "/api/clm/zero-touch/case-portfolio")
    assert policy is not None and policy.access == RouteAccess.CASE_PORTFOLIO
    assert parameters == {}
    assert client.get("/api/clm/zero-touch/case-portfolio?limit=101").status_code == 422
    assert client.get("/api/clm/zero-touch/case-portfolio?offset=10001").status_code == 422
    assert client.get("/api/clm/zero-touch/case-portfolio?jurisdiction=ZZ").status_code == 422
    assert client.get(
        f"/api/clm/zero-touch/case-portfolio?search={'x' * 129}"
    ).status_code == 422


@pytest.mark.parametrize(
    "error_type",
    [
        PersistenceDataInvalidError,
        PersistenceSchemaUnsupportedError,
        PersistenceUnavailableError,
    ],
)
def test_api_sanitizes_expected_portfolio_persistence_failures(
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[Exception],
) -> None:
    private_detail = "private database topology and corrupt field path"

    def fail_page(
        _repository: InMemoryCasePortfolioRepository,
        _query: CasePortfolioQuery,
    ) -> CasePortfolioPage:
        raise error_type(private_detail)

    monkeypatch.setattr(InMemoryCasePortfolioRepository, "list_page", fail_page)
    client = RawTestClient(create_app(ordinary_test_settings()))
    login = client.post(
        "/api/auth/login",
        json={"user_id": "maya-lim", "password": TEST_PASSWORD},
    )
    assert login.status_code == 200

    response = client.get("/api/clm/zero-touch/case-portfolio")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "CASE_PORTFOLIO_UNAVAILABLE",
            "message": "The case portfolio is temporarily unavailable.",
        }
    }
    assert private_detail not in response.text


@pytest.mark.parametrize(
    ("inventory_size", "limit", "expected_items", "has_more"),
    [
        (1, 1, 1, False),
        (25, 25, 25, False),
        (105, 100, 100, True),
    ],
)
def test_page_response_stays_bounded_for_synthetic_inventories(
    inventory_size: int,
    limit: int,
    expected_items: int,
    has_more: bool,
) -> None:
    client = RawTestClient(
        create_app(
            ordinary_test_settings(),
            e2e_portfolio_seed_count=inventory_size,
        )
    )
    login = client.post(
        "/api/auth/login",
        json={"user_id": "maya-lim", "password": TEST_PASSWORD},
    )
    assert login.status_code == 200

    response = client.get(f"/api/clm/zero-touch/case-portfolio?limit={limit}")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == expected_items
    assert body["limit"] == limit
    assert body["has_more"] is has_more
