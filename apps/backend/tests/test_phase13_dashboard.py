from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from phase13_test_clients import RawTestClient
from phase13_test_credentials import build_test_authentication_service
from phase13_test_settings import ordinary_test_settings

from app.composition import build_onboarding_service
from app.domain.access import (
    SYNTHETIC_USER_PROFILES,
    AuthenticatedActor,
    TeamId,
)
from app.domain.administration import TeamRecord, normalize_display_name
from app.domain.models import OnboardingCase, WorkflowState
from app.domain.zero_touch import (
    AutomationMetrics,
    AutomationStage,
    AutomationStatus,
    ZeroTouchAutomationRecord,
)
from app.main import create_app
from app.services.admin_repository import InMemoryTeamRepository
from app.services.administration import TeamDirectoryService
from app.services.authentication import generate_scrypt_password_hash
from app.services.authorization import CaseAccessPolicy
from app.services.case_query import CaseQueryService
from app.services.dashboard import DashboardService
from app.services.repository import InMemoryOnboardingCaseRepository

NOW = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)


def _teams() -> InMemoryTeamRepository:
    repository = InMemoryTeamRepository()
    for team_id, name in ((TeamId.TEAM_A, "Alpha"), (TeamId.TEAM_B, "Beta")):
        repository.create(
            TeamRecord(
                team_id=team_id,
                display_name=name,
                normalized_display_name=normalize_display_name(name),
                client_scope_label=name,
                normalized_client_scope_label=normalize_display_name(name),
                version=1,
                created_at=NOW,
                updated_at=NOW,
                created_by="system-bootstrap",
                updated_by="system-bootstrap",
            )
        )
    return repository


class StaticAutomationRepository:
    def __init__(self, records: list[ZeroTouchAutomationRecord]) -> None:
        self.records = records
        self.read_count = 0

    def list_records(self) -> list[ZeroTouchAutomationRecord]:
        self.read_count += 1
        return [record.model_copy(deep=True) for record in self.records]


def _actor(user_id: str) -> AuthenticatedActor:
    profile = next(item for item in SYNTHETIC_USER_PROFILES if item.user_id == user_id)
    return AuthenticatedActor(profile=profile)


def _record(
    team_id: TeamId,
    priority: int | None,
    status: AutomationStatus,
    *,
    created_days_ago: int,
    updated_hours_ago: int,
) -> tuple[OnboardingCase, ZeroTouchAutomationRecord]:
    case_id = uuid4()
    created_at = NOW - timedelta(days=created_days_ago)
    updated_at = NOW - timedelta(hours=updated_hours_ago)
    completed_at = updated_at if status == AutomationStatus.COMPLETED else None
    case = OnboardingCase(
        case_id=case_id,
        source_case_id=f"CASE-{case_id}",
        correlation_id=uuid4(),
        requested_uen=f"2024{str(case_id.int)[-5:]}A",
        team_id=team_id,
        priority=priority,
        state=WorkflowState.REQUESTED,
        created_at=created_at,
        updated_at=updated_at,
    )
    automation = ZeroTouchAutomationRecord(
        case_id=case_id,
        automation_id=uuid4(),
        ownership_provider_binding_id="a" * 32,
        status=status,
        current_stage=(
            AutomationStage.COMPLETE
            if status == AutomationStatus.COMPLETED
            else AutomationStage.REGISTRY
        ),
        metrics=AutomationMetrics(
            final_outcome=(
                "MOCK_GOLDTIER_SUBMITTED" if status == AutomationStatus.COMPLETED else None
            )
        ),
        created_at=created_at,
        updated_at=updated_at,
        completed_at=completed_at,
    )
    return case, automation


def _dashboard() -> tuple[DashboardService, StaticAutomationRepository]:
    fixtures = [
        _record(
            TeamId.TEAM_A,
            10,
            AutomationStatus.RUNNING,
            created_days_ago=1,
            updated_hours_ago=1,
        ),
        _record(
            TeamId.TEAM_A,
            None,
            AutomationStatus.COMPLETED,
            created_days_ago=2,
            updated_hours_ago=4,
        ),
        _record(
            TeamId.TEAM_B,
            8,
            AutomationStatus.WAITING_FOR_REVIEW,
            created_days_ago=3,
            updated_hours_ago=2,
        ),
        _record(
            TeamId.TEAM_B,
            1,
            AutomationStatus.COMPLETED,
            created_days_ago=31,
            updated_hours_ago=3,
        ),
    ]
    cases = InMemoryOnboardingCaseRepository()
    for case, _ in fixtures:
        cases.create(case)
    onboarding = build_onboarding_service(settings=ordinary_test_settings(), repository=cases)
    automations = StaticAutomationRepository([record for _, record in fixtures])
    teams = _teams()
    query = CaseQueryService(
        cases=onboarding,
        case_repository=cases,
        automation_repository=automations,  # type: ignore[arg-type]
        access_policy=CaseAccessPolicy(),
        teams=teams,
    )
    return DashboardService(query, TeamDirectoryService(teams), clock=lambda: NOW), automations


def test_empty_dashboard_is_deterministic_and_safe() -> None:
    cases = InMemoryOnboardingCaseRepository()
    onboarding = build_onboarding_service(settings=ordinary_test_settings(), repository=cases)
    automations = StaticAutomationRepository([])
    teams = _teams()
    service = DashboardService(
        CaseQueryService(
            cases=onboarding,
            case_repository=cases,
            automation_repository=automations,  # type: ignore[arg-type]
            access_policy=CaseAccessPolicy(),
            teams=teams,
        ),
        TeamDirectoryService(teams),
        clock=lambda: NOW,
    )

    result = service.get_dashboard(_actor("maya-lim"))

    assert result.totals.model_dump() == {
        "total_cases": 0,
        "completed_cases": 0,
        "non_completed_cases": 0,
        "completion_rate": 0.0,
        "prioritised_cases": 0,
        "unprioritised_cases": 0,
    }
    assert [item.count for item in result.status_breakdown] == [0] * len(AutomationStatus)
    assert [item.priority for item in result.priority_breakdown] == [*range(10, 0, -1), None]
    assert result.recent_cases == result.top_active_cases == ()
    assert len(result.historical_trend) == 30


def test_team_dashboards_are_server_scoped_across_every_metric_and_list() -> None:
    service, repository = _dashboard()

    team_a = service.get_dashboard(_actor("maya-lim"))
    team_b = service.get_dashboard(_actor("sophia-ng"))

    assert team_a.scope.access == "TEAM"
    assert team_a.scope.team_display_name == "Alpha"
    assert team_a.totals.total_cases == 2
    assert team_a.totals.completed_cases == 1
    assert team_a.totals.completion_rate == 0.5
    assert {item.team_id for item in team_a.team_breakdown} == {TeamId.TEAM_A}
    assert {item.team_id for item in (*team_a.recent_cases, *team_a.top_active_cases)} == {
        TeamId.TEAM_A
    }
    assert sum(item.created_count for item in team_a.historical_trend) == 2
    assert sum(item.completed_count for item in team_a.historical_trend) == 1

    assert team_b.scope.team_display_name == "Beta"
    assert team_b.totals.total_cases == 2
    assert {item.team_id for item in team_b.team_breakdown} == {TeamId.TEAM_B}
    assert {item.team_id for item in (*team_b.recent_cases, *team_b.top_active_cases)} == {
        TeamId.TEAM_B
    }
    assert sum(item.created_count for item in team_b.historical_trend) == 1
    assert sum(item.completed_count for item in team_b.historical_trend) == 1
    assert repository.read_count == 2


def test_director_gets_exact_status_priority_team_recent_and_active_views() -> None:
    service, _ = _dashboard()

    result = service.get_dashboard(_actor("olivia-koh"))

    assert result.scope.access == "GLOBAL"
    assert result.totals.model_dump() == {
        "total_cases": 4,
        "completed_cases": 2,
        "non_completed_cases": 2,
        "completion_rate": 0.5,
        "prioritised_cases": 3,
        "unprioritised_cases": 1,
    }
    statuses = {item.status: item.count for item in result.status_breakdown}
    assert statuses[AutomationStatus.COMPLETED] == 2
    assert statuses[AutomationStatus.RUNNING] == 1
    assert statuses[AutomationStatus.WAITING_FOR_REVIEW] == 1
    priorities = {item.priority: item.count for item in result.priority_breakdown}
    assert priorities[10] == priorities[8] == priorities[1] == priorities[None] == 1
    assert [(item.team_id, item.count) for item in result.team_breakdown] == [
        (TeamId.TEAM_A, 2),
        (TeamId.TEAM_B, 2),
    ]
    assert [item.status for item in result.top_active_cases] == [
        AutomationStatus.RUNNING,
        AutomationStatus.WAITING_FOR_REVIEW,
    ]
    assert result.recent_cases[0].updated_at > result.recent_cases[-1].updated_at


def test_dashboard_route_requires_authentication_and_accepts_no_scope_authority() -> None:
    synthetic_login_value = secrets.token_urlsafe(24)
    encoded = generate_scrypt_password_hash(synthetic_login_value)
    application = create_app(
        ordinary_test_settings(),
        authentication_service=build_test_authentication_service(
            {profile.user_id: encoded for profile in SYNTHETIC_USER_PROFILES}
        ),
    )
    anonymous = RawTestClient(application)
    assert anonymous.get("/api/clm/zero-touch/dashboard").status_code == 401

    response = anonymous.post(
        "/api/auth/login",
        json={"user_id": "maya-lim", "password": synthetic_login_value},
    )
    assert response.status_code == 200
    dashboard = anonymous.get("/api/clm/zero-touch/dashboard?team_id=TEAM_B&role=DIRECTOR")
    assert dashboard.status_code == 200
    assert dashboard.json()["scope"] == {
        "actor_role": "CLIENT_ONBOARDER",
        "access": "TEAM",
        "team_id": "TEAM_A",
        "team_display_name": "Alpha",
        "client_scope_label": "Alpha",
    }
