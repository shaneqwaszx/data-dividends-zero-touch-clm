from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from phase13_test_settings import ordinary_test_settings

from app.domain.access import SYNTHETIC_PROFILE_BY_ID, AuthenticatedActor, TeamId
from app.domain.case_management import (
    CasePortfolioPage,
    CasePortfolioQuery,
    CasePortfolioRecord,
    CaseTimingDataInvalidError,
    project_case_timing,
)
from app.domain.zero_touch import AutomationStage, AutomationStatus
from app.main import create_app
from app.services.authorization import CaseAccessPolicy
from app.services.case_portfolio_repository import InMemoryCasePortfolioRepository
from app.services.case_query import CaseQueryService

OBSERVED_AT = datetime(2026, 9, 21, 12, 0, 0, tzinfo=UTC)
CASE_A = UUID("00000000-0000-4000-8000-000000000191")
CASE_B = UUID("00000000-0000-4000-8000-000000000192")


def test_timing_projection_covers_active_completed_never_started_and_boundaries() -> None:
    active = project_case_timing(
        created_at=OBSERVED_AT - timedelta(days=2, hours=5),
        updated_at=OBSERVED_AT,
        started_at=OBSERVED_AT - timedelta(hours=3, minutes=14),
        completed_at=None,
        recorded_total_duration_ms=None,
        observed_at=OBSERVED_AT,
    )
    assert active.model_dump() == {
        "case_elapsed_ms": 190_800_000,
        "time_since_last_update_ms": 0,
        "automation_elapsed_ms": 11_640_000,
        "recorded_total_duration_ms": None,
    }

    completed_at = OBSERVED_AT - timedelta(hours=2)
    completed = project_case_timing(
        created_at=completed_at - timedelta(seconds=41),
        updated_at=completed_at,
        started_at=completed_at - timedelta(seconds=12, milliseconds=999),
        completed_at=completed_at,
        recorded_total_duration_ms=12_999,
        observed_at=OBSERVED_AT,
    )
    assert completed.case_elapsed_ms == 41_000
    assert completed.time_since_last_update_ms == 7_200_000
    assert completed.automation_elapsed_ms == 12_999
    assert completed.recorded_total_duration_ms == 12_999

    never_started = project_case_timing(
        created_at=OBSERVED_AT - timedelta(microseconds=999),
        updated_at=OBSERVED_AT,
        started_at=None,
        completed_at=OBSERVED_AT,
        recorded_total_duration_ms=None,
        observed_at=OBSERVED_AT,
    )
    assert never_started.case_elapsed_ms == 0
    assert never_started.automation_elapsed_ms is None


@pytest.mark.parametrize(
    "change",
    [
        {"created_at": OBSERVED_AT + timedelta(microseconds=1)},
        {"updated_at": OBSERVED_AT + timedelta(microseconds=1)},
        {"updated_at": OBSERVED_AT - timedelta(hours=2)},
        {"started_at": OBSERVED_AT - timedelta(hours=2)},
        {"started_at": OBSERVED_AT + timedelta(microseconds=1)},
        {"completed_at": OBSERVED_AT + timedelta(microseconds=1)},
        {"completed_at": OBSERVED_AT - timedelta(hours=2)},
        {
            "started_at": OBSERVED_AT - timedelta(minutes=45),
            "completed_at": OBSERVED_AT - timedelta(minutes=50),
        },
        {"created_at": datetime(2026, 9, 21, 11, 0, 0)},
        {"updated_at": datetime(2026, 9, 21, 11, 30, 0, tzinfo=timezone(timedelta(hours=8)))},
        {"recorded_total_duration_ms": True},
        {"recorded_total_duration_ms": -1},
    ],
)
def test_timing_projection_rejects_untruthful_or_malformed_inputs(
    change: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "created_at": OBSERVED_AT - timedelta(hours=1),
        "updated_at": OBSERVED_AT - timedelta(minutes=30),
        "started_at": OBSERVED_AT - timedelta(minutes=45),
        "completed_at": None,
        "recorded_total_duration_ms": None,
        "observed_at": OBSERVED_AT,
    }
    values.update(change)
    with pytest.raises(CaseTimingDataInvalidError):
        project_case_timing(**values)  # type: ignore[arg-type]


def _record(
    case_id: UUID,
    *,
    created_at: datetime,
    updated_at: datetime,
    started_at: datetime | None,
    completed_at: datetime | None,
    recorded_total_duration_ms: int | None,
) -> CasePortfolioRecord:
    return CasePortfolioRecord(
        case_id=case_id,
        requested_uen=f"{case_id.int % 10_000_000:07d}A",
        legal_name="TIMING PTE. LTD.",
        team_id=TeamId.TEAM_A,
        priority=None,
        status=(
            AutomationStatus.COMPLETED
            if completed_at is not None
            else AutomationStatus.RUNNING
        ),
        current_stage=(
            AutomationStage.COMPLETE
            if completed_at is not None
            else AutomationStage.DOCUMENT
        ),
        created_at=created_at,
        updated_at=updated_at,
        started_at=started_at,
        completed_at=completed_at,
        recorded_total_duration_ms=recorded_total_duration_ms,
        active_exception_count=0,
        active_exception_types=(),
        human_interventions=0,
        final_outcome=("MOCK_GOLDTIER_SUBMITTED" if completed_at is not None else None),
        mock_goldtier_party_id=None,
    )


class _PageRepository:
    def __init__(self, items: tuple[CasePortfolioRecord, ...]) -> None:
        self.items = items
        self.query: CasePortfolioQuery | None = None

    def list_authorized(self, scope: object, *, status: object = None) -> list[object]:
        del scope, status
        return []

    def list_activity(self, query: object) -> object:
        raise AssertionError(query)

    def list_page(self, query: CasePortfolioQuery) -> CasePortfolioPage:
        self.query = query
        return CasePortfolioPage(
            items=self.items,
            offset=query.offset,
            limit=query.limit,
            has_more=False,
        )


def test_service_uses_one_observation_for_every_row_and_stabilizes_completed_case() -> None:
    repository = _PageRepository(
        (
            _record(
                CASE_A,
                created_at=OBSERVED_AT - timedelta(hours=3),
                updated_at=OBSERVED_AT - timedelta(minutes=28),
                started_at=OBSERVED_AT - timedelta(hours=2),
                completed_at=None,
                recorded_total_duration_ms=None,
            ),
            _record(
                CASE_B,
                created_at=OBSERVED_AT - timedelta(days=1),
                updated_at=OBSERVED_AT - timedelta(hours=2),
                started_at=OBSERVED_AT - timedelta(hours=23),
                completed_at=OBSERVED_AT - timedelta(hours=22),
                recorded_total_duration_ms=3_600_000,
            ),
        )
    )
    calls = 0

    def clock() -> datetime:
        nonlocal calls
        calls += 1
        return OBSERVED_AT

    service = CaseQueryService(
        cases=object(),  # type: ignore[arg-type]
        case_repository=object(),  # type: ignore[arg-type]
        automation_repository=object(),  # type: ignore[arg-type]
        access_policy=CaseAccessPolicy(),
        teams=object(),  # type: ignore[arg-type]
        portfolio_repository=repository,
        clock=clock,
    )
    actor = AuthenticatedActor(profile=SYNTHETIC_PROFILE_BY_ID["maya-lim"])

    page = service.list_portfolio(actor)

    assert calls == 1
    assert page.observed_at == OBSERVED_AT
    assert page.items[0].timing.case_elapsed_ms == 10_800_000
    assert page.items[0].timing.time_since_last_update_ms == 1_680_000
    assert page.items[1].timing.case_elapsed_ms == 7_200_000
    assert page.items[1].timing.automation_elapsed_ms == 3_600_000
    assert page.items[1].timing.recorded_total_duration_ms == 3_600_000


def test_api_adds_timing_only_to_paged_and_detail_contracts() -> None:
    client = RawTestClient(
        create_app(
            ordinary_test_settings(),
            e2e_portfolio_seed_count=1,
            clock=lambda: OBSERVED_AT,
        )
    )
    login = client.post(
        "/api/auth/login",
        json={"user_id": "maya-lim", "password": TEST_PASSWORD},
    )
    assert login.status_code == 200

    legacy = client.get("/api/clm/zero-touch/cases")
    page = client.get("/api/clm/zero-touch/case-portfolio")

    assert legacy.status_code == 200
    assert "timing" not in legacy.json()[0]
    assert page.status_code == 200
    page_body = page.json()
    assert page_body["observed_at"] == "2026-09-21T12:00:00Z"
    assert set(page_body["items"][0]["timing"]) == {
        "case_elapsed_ms",
        "time_since_last_update_ms",
        "automation_elapsed_ms",
        "recorded_total_duration_ms",
    }

    detail = client.get(
        f"/api/clm/zero-touch/cases/{page_body['items'][0]['case_id']}"
    )
    assert detail.status_code == 200
    assert detail.json()["timing"] == {
        **page_body["items"][0]["timing"],
        "observed_at": "2026-09-21T12:00:00Z",
    }


def test_api_maps_invalid_authorized_timing_to_existing_sanitized_portfolio_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = _record(
        CASE_A,
        created_at=OBSERVED_AT + timedelta(seconds=1),
        updated_at=OBSERVED_AT + timedelta(seconds=1),
        started_at=None,
        completed_at=None,
        recorded_total_duration_ms=None,
    )

    def page_with_future_timing(
        _repository: InMemoryCasePortfolioRepository,
        query: CasePortfolioQuery,
    ) -> CasePortfolioPage:
        return CasePortfolioPage(
            items=(invalid,),
            offset=query.offset,
            limit=query.limit,
            has_more=False,
        )

    monkeypatch.setattr(InMemoryCasePortfolioRepository, "list_page", page_with_future_timing)
    client = RawTestClient(create_app(ordinary_test_settings(), clock=lambda: OBSERVED_AT))
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
