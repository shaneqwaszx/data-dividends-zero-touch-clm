"""Cases page "Show" view: in progress (every status except COMPLETED) or onboarded."""

from __future__ import annotations

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from phase13_test_settings import ordinary_test_settings
from pydantic import ValidationError
from test_phase18_case_portfolio import CASE_A, _AggregateCollection, _mongo_portfolio_row, _record

from app.domain.access import TeamId
from app.domain.case_management import (
    CasePortfolioQuery,
    CasePortfolioScope,
    PortfolioScopeKind,
    case_portfolio_matches,
)
from app.domain.zero_touch import AutomationStatus
from app.main import create_app
from app.persistence.mongo_case_store import MongoCaseStore

SCOPE = CasePortfolioScope(kind=PortfolioScopeKind.GLOBAL)


@pytest.mark.parametrize("status", list(AutomationStatus))
def test_memory_progress_splits_completed_from_every_other_status(status):
    record = _record(CASE_A, priority=None).model_copy(update={"status": status})
    completed = status == AutomationStatus.COMPLETED
    assert case_portfolio_matches(record, CasePortfolioQuery(scope=SCOPE))
    assert case_portfolio_matches(
        record, CasePortfolioQuery(scope=SCOPE, progress="onboarded")
    ) is completed
    assert case_portfolio_matches(
        record, CasePortfolioQuery(scope=SCOPE, progress="in_progress")
    ) is not completed


def test_progress_composes_with_an_exact_status():
    waiting = _record(CASE_A, priority=None)
    assert not case_portfolio_matches(waiting, CasePortfolioQuery(
        scope=SCOPE, progress="onboarded", status=AutomationStatus.WAITING_FOR_REVIEW,
    ))
    assert case_portfolio_matches(waiting, CasePortfolioQuery(
        scope=SCOPE, progress="in_progress", status=AutomationStatus.WAITING_FOR_REVIEW,
    ))


def test_progress_accepts_only_the_two_views():
    with pytest.raises(ValidationError):
        CasePortfolioQuery(scope=SCOPE, progress="archived")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("progress", "clause"),
    [
        ("onboarded", {"automation.status": "COMPLETED"}),
        ("in_progress", {"automation.status": {"$ne": "COMPLETED"}}),
    ],
)
def test_mongo_progress_is_one_bounded_status_clause(progress, clause):
    collection = _AggregateCollection([{"invalid": [], "rows": [_mongo_portfolio_row()]}])
    store = object.__new__(MongoCaseStore)
    store._collection = collection  # type: ignore[attr-defined]  # noqa: SLF001
    store.list_portfolio_page(CasePortfolioQuery(
        scope=CasePortfolioScope(kind=PortfolioScopeKind.TEAM, team_id=TeamId.TEAM_A),
        progress=progress,
    ))
    pipeline, _ = collection.calls[0]
    rows = pipeline[3]["$facet"]["rows"]  # type: ignore[index]
    match = rows[1]["$match"]  # type: ignore[index]
    assert clause in match.get("$and", [match])


def test_api_accepts_the_two_views_and_rejects_anything_else():
    client = RawTestClient(create_app(ordinary_test_settings()))
    assert client.post(
        "/api/auth/login", json={"user_id": "maya-lim", "password": TEST_PASSWORD},
    ).status_code == 200
    for progress in ("in_progress", "onboarded"):
        response = client.get(f"/api/clm/zero-touch/case-portfolio?progress={progress}")
        assert response.status_code == 200, response.json()
    assert client.get("/api/clm/zero-touch/case-portfolio?progress=archived").status_code == 422
