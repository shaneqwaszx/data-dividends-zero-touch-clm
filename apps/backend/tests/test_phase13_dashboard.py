from __future__ import annotations

import secrets
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
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
    BlockerDecisionClassification,
    BlockerDecisionMetadata,
    BlockerDecisionOwner,
    BlockerDecisionRecord,
    BusinessException,
    BusinessExceptionStatus,
    BusinessExceptionType,
    ResumeTransition,
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

    @contextmanager
    def capture_for_cases(self, case_ids):
        # The existing read hook still models the source-capture interleaving.
        captured = [record for record in self.list_records() if record.case_id in case_ids]
        class Batch:
            def read_selected(self, selected):
                assert selected <= case_ids
                return [record.model_copy(deep=True) for record in captured
                        if record.case_id in selected]
        yield Batch()


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
    created_by_actor_id: str | None = None,
    stage_durations_ms: dict[AutomationStage, int] | None = None,
    exceptions: tuple[BusinessException, ...] = (),
    human_interventions: int = 0,
    automated_stages_completed: int = 0,
    current_stage: AutomationStage | None = None,
) -> tuple[OnboardingCase, ZeroTouchAutomationRecord]:
    case_id = uuid4()
    created_at = NOW - timedelta(days=created_days_ago)
    updated_at = NOW - timedelta(hours=updated_hours_ago)
    completed_at = updated_at if status == AutomationStatus.COMPLETED else None
    total_duration_ms = (
        int((completed_at - created_at).total_seconds() * 1000) if completed_at else None
    )
    case = OnboardingCase(
        case_id=case_id,
        source_case_id=f"CASE-{case_id}",
        correlation_id=uuid4(),
        requested_uen=f"2024{str(case_id.int)[-5:]}A",
        team_id=team_id,
        priority=priority,
        created_by_actor_id=created_by_actor_id,
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
            current_stage
            if current_stage is not None
            else (
                AutomationStage.COMPLETE
                if status == AutomationStatus.COMPLETED
                else AutomationStage.REGISTRY
            )
        ),
        metrics=AutomationMetrics(
            final_outcome=(
                "MOCK_GOLDTIER_SUBMITTED" if status == AutomationStatus.COMPLETED else None
            ),
            human_interventions=human_interventions,
            automated_stages_completed=automated_stages_completed,
            stage_durations_ms=stage_durations_ms or {},
            total_duration_ms=total_duration_ms,
        ),
        exceptions=list(exceptions),
        created_at=created_at,
        updated_at=updated_at,
        completed_at=completed_at,
    )
    return case, automation


def _resolved_exception(
    case_id,
    exception_type: BusinessExceptionType,
    stage: AutomationStage,
    *,
    created_at: datetime,
    resolved_at: datetime,
    actor_id: str,
    blocker_code: str = "TEST_BLOCKER",
) -> BusinessException:
    """Build a RESOLVED BusinessException with one bound BlockerDecisionRecord."""

    exception = BusinessException(
        exception_id=uuid4(),
        case_id=case_id,
        exception_type=exception_type,
        stage=stage,
        status=BusinessExceptionStatus.RESOLVED,
        blocker_code=blocker_code,
        blocker_codes=(blocker_code,),
        explanation="Synthetic test blocker.",
        evidence_version="v1",
        authoritative_evidence_digest="a" * 64,
        automation_version=1,
        created_at=created_at,
        resolved_at=resolved_at,
    )
    metadata = BlockerDecisionMetadata(
        blocker_code=blocker_code,
        exception_type=exception_type,
        classification=BlockerDecisionClassification.USER_ACTION_REQUIRED,
        policy_version="BLOCKER_DECISION_POC_V1",
        rule_version="RULE1",
        owner=BlockerDecisionOwner.CASE_OPERATOR,
        minimum_inputs=(),
        permitted_actions=(),
        currently_available_actions=(),
        resume_stage=None,
        resume_transition=ResumeTransition.NO_AUTOMATIC_RESUME,
        resume_ready=False,
        invalidated_dependencies=(),
        explanation="Synthetic resolution.",
    )
    decision = BlockerDecisionRecord(
        decision_id=uuid4(),
        case_id=case_id,
        exception_id=exception.exception_id,
        evidence_version=exception.evidence_version,
        automation_version=exception.automation_version,
        recorded_at=resolved_at,
        metadata=metadata,
        actor_id=actor_id,
    )
    return exception.model_copy(update={"decisions": (decision,)})


def _service_for(
    fixtures: list[tuple[OnboardingCase, ZeroTouchAutomationRecord]],
) -> tuple[DashboardService, StaticAutomationRepository]:
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
    service = DashboardService(
        query, TeamDirectoryService(teams), automations, clock=lambda: NOW
    )
    return service, automations


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
    return _service_for(fixtures)


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
        automations,
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
    assert result.recent_cases == result.top_active_cases == result.scoped_cases == ()
    assert len(result.historical_trend) == 30
    assert result.zero_touch_rate == 0.0
    assert result.timing.mean_total_duration_ms is None
    assert len(result.stage_timing) == 6
    assert result.exception_breakdown == ()
    assert len(result.weekly_onboarded) == 8
    assert result.workload_by_person == ()


def test_team_dashboards_are_server_scoped_across_every_metric_and_list() -> None:
    service, repository = _dashboard()

    team_a = service.get_dashboard(_actor("maya-lim"), date_range="all")
    team_b = service.get_dashboard(_actor("sophia-ng"), date_range="all")

    assert team_a.scope.access == "TEAM"
    assert team_a.scope.team_display_name == "Alpha"
    assert team_a.totals.total_cases == 2
    assert team_a.totals.completed_cases == 1
    assert team_a.totals.completion_rate == 0.5
    assert {item.team_id for item in team_a.team_breakdown} == {TeamId.TEAM_A}
    assert {item.team_id for item in (*team_a.recent_cases, *team_a.top_active_cases)} == {
        TeamId.TEAM_A
    }
    assert sum(
        sum(week.by_jurisdiction.values()) + week.unresolved_count
        for week in team_a.weekly_onboarded
    ) == 1

    assert team_b.scope.team_display_name == "Beta"
    assert team_b.totals.total_cases == 2
    assert {item.team_id for item in team_b.team_breakdown} == {TeamId.TEAM_B}
    assert {item.team_id for item in (*team_b.recent_cases, *team_b.top_active_cases)} == {
        TeamId.TEAM_B
    }
    assert sum(
        sum(week.by_jurisdiction.values()) + week.unresolved_count
        for week in team_b.weekly_onboarded
    ) == 1
    assert sum(item.created_count for item in team_a.historical_trend) == 2
    assert sum(item.completed_count for item in team_a.historical_trend) == 1
    assert sum(item.created_count for item in team_b.historical_trend) == 1
    assert sum(item.completed_count for item in team_b.historical_trend) == 1
    assert repository.read_count == 4


def test_director_gets_exact_status_priority_team_recent_and_active_views() -> None:
    service, _ = _dashboard()

    result = service.get_dashboard(_actor("olivia-koh"), date_range="all")

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


def test_stage_timing_splits_clean_and_blocked_durations_with_top_cases() -> None:
    clean_case, clean_automation = _record(
        TeamId.TEAM_A,
        None,
        AutomationStatus.RUNNING,
        created_days_ago=1,
        updated_hours_ago=1,
        stage_durations_ms={AutomationStage.DOCUMENT: 600_000},
    )
    blocked_case, blocked_automation = _record(
        TeamId.TEAM_A,
        None,
        AutomationStatus.RUNNING,
        created_days_ago=1,
        updated_hours_ago=1,
        stage_durations_ms={AutomationStage.DOCUMENT: 1_800_000},
    )
    exception = _resolved_exception(
        blocked_case.case_id,
        BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
        AutomationStage.DOCUMENT,
        created_at=blocked_case.created_at,
        resolved_at=blocked_case.created_at + timedelta(hours=2),
        actor_id="maya-lim",
    )
    blocked_automation = blocked_automation.model_copy(update={"exceptions": [exception]})

    service, _ = _service_for(
        [(clean_case, clean_automation), (blocked_case, blocked_automation)]
    )
    result = service.get_dashboard(_actor("maya-lim"), date_range="all")

    document_row = next(
        row for row in result.stage_timing if row.stage == AutomationStage.DOCUMENT
    )
    assert document_row.clean_mean_ms == 600_000
    assert document_row.clean_count == 1
    assert document_row.with_blocker_mean_ms == 1_800_000
    assert document_row.with_blocker_count == 1
    assert document_row.combined_mean_ms == 1_200_000
    assert document_row.blocked_count == 1
    assert [item.duration_ms for item in document_row.top_cases] == [1_800_000, 600_000]
    assert document_row.top_cases[0].had_blocker is True
    assert document_row.top_cases[1].had_blocker is False


def test_exception_breakdown_counts_by_type_sorted_by_frequency() -> None:
    fixtures = []
    for exception_type in (
        BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
        BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
        BusinessExceptionType.OWNERSHIP_CYCLE,
    ):
        case, automation = _record(
            TeamId.TEAM_A,
            None,
            AutomationStatus.RUNNING,
            created_days_ago=1,
            updated_hours_ago=1,
        )
        exception = _resolved_exception(
            case.case_id,
            exception_type,
            AutomationStage.DOCUMENT,
            created_at=case.created_at,
            resolved_at=case.created_at + timedelta(hours=1),
            actor_id="maya-lim",
        )
        automation = automation.model_copy(update={"exceptions": [exception]})
        fixtures.append((case, automation))

    service, _ = _service_for(fixtures)
    result = service.get_dashboard(_actor("maya-lim"), date_range="all")

    assert [(item.exception_type, item.count) for item in result.exception_breakdown] == [
        (BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE, 2),
        (BusinessExceptionType.OWNERSHIP_CYCLE, 1),
    ]


def test_workload_by_person_tracks_cases_and_blocker_fix_time() -> None:
    maya_open, maya_open_automation = _record(
        TeamId.TEAM_A,
        None,
        AutomationStatus.RUNNING,
        created_days_ago=5,
        updated_hours_ago=1,
        created_by_actor_id="maya-lim",
    )
    maya_completed, maya_completed_automation = _record(
        TeamId.TEAM_A,
        None,
        AutomationStatus.COMPLETED,
        created_days_ago=2,
        updated_hours_ago=1,
        created_by_actor_id="maya-lim",
    )
    exception = _resolved_exception(
        maya_completed.case_id,
        BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
        AutomationStage.DOCUMENT,
        created_at=maya_completed.created_at,
        resolved_at=maya_completed.created_at + timedelta(hours=2),
        actor_id="maya-lim",
    )
    maya_completed_automation = maya_completed_automation.model_copy(
        update={"exceptions": [exception]}
    )
    ethan_open, ethan_open_automation = _record(
        TeamId.TEAM_A,
        None,
        AutomationStatus.RUNNING,
        created_days_ago=1,
        updated_hours_ago=1,
        created_by_actor_id="ethan-tan",
    )

    service, _ = _service_for(
        [
            (maya_open, maya_open_automation),
            (maya_completed, maya_completed_automation),
            (ethan_open, ethan_open_automation),
        ]
    )
    result = service.get_dashboard(_actor("maya-lim"), date_range="all")

    rows = {row.user_id: row for row in result.workload_by_person}
    assert rows["maya-lim"].open_cases == 1
    assert rows["maya-lim"].completed_cases == 1
    assert rows["maya-lim"].blockers_resolved == 1
    assert rows["maya-lim"].mean_fix_time_ms == 7_200_000
    assert rows["maya-lim"].oldest_open_age_ms == int(timedelta(days=5).total_seconds() * 1000)
    assert rows["ethan-tan"].open_cases == 1
    assert rows["ethan-tan"].completed_cases == 0
    assert rows["ethan-tan"].blockers_resolved == 0
    assert rows["ethan-tan"].mean_fix_time_ms is None

    scoped_by_case = {item.case_id: item for item in result.scoped_cases}
    assert scoped_by_case[maya_open.case_id].created_by_display_name == "Maya Lim"
    assert scoped_by_case[ethan_open.case_id].created_by_display_name == "Ethan Tan"


def test_scope_mine_filters_to_cases_created_by_the_caller() -> None:
    mine_a, mine_a_automation = _record(
        TeamId.TEAM_A,
        None,
        AutomationStatus.RUNNING,
        created_days_ago=1,
        updated_hours_ago=1,
        created_by_actor_id="maya-lim",
    )
    mine_b, mine_b_automation = _record(
        TeamId.TEAM_A,
        None,
        AutomationStatus.COMPLETED,
        created_days_ago=2,
        updated_hours_ago=1,
        created_by_actor_id="maya-lim",
    )
    other, other_automation = _record(
        TeamId.TEAM_A,
        None,
        AutomationStatus.RUNNING,
        created_days_ago=1,
        updated_hours_ago=1,
        created_by_actor_id="ethan-tan",
    )

    service, _ = _service_for(
        [(mine_a, mine_a_automation), (mine_b, mine_b_automation), (other, other_automation)]
    )
    mine = service.get_dashboard(_actor("maya-lim"), scope="mine", date_range="all")
    team = service.get_dashboard(_actor("maya-lim"), scope="team", date_range="all")

    assert mine.view == "mine"
    assert mine.totals.total_cases == 2
    assert {item.case_id for item in mine.scoped_cases} == {mine_a.case_id, mine_b.case_id}
    assert mine.team_breakdown == ()
    assert team.view == "team"
    assert team.totals.total_cases == 3


def test_zero_touch_rate_and_timing_split_zero_touch_vs_blocked() -> None:
    zero_touch, zero_touch_automation = _record(
        TeamId.TEAM_A,
        None,
        AutomationStatus.COMPLETED,
        created_days_ago=1,
        updated_hours_ago=23,
        human_interventions=0,
    )
    blocked, blocked_automation = _record(
        TeamId.TEAM_A,
        None,
        AutomationStatus.COMPLETED,
        created_days_ago=1,
        updated_hours_ago=19,
        human_interventions=2,
    )

    service, _ = _service_for(
        [(zero_touch, zero_touch_automation), (blocked, blocked_automation)]
    )
    result = service.get_dashboard(_actor("maya-lim"), date_range="all")

    assert result.zero_touch_rate == 0.5
    assert result.timing.zero_touch_count == 1
    assert result.timing.zero_touch_mean_duration_ms == 3_600_000
    assert result.timing.blocked_count == 1
    assert result.timing.blocked_mean_duration_ms == 18_000_000
    assert result.timing.mean_total_duration_ms == 10_800_000


def test_progress_percent_reflects_automated_stages_or_completion() -> None:
    in_progress, in_progress_automation = _record(
        TeamId.TEAM_A,
        None,
        AutomationStatus.RUNNING,
        created_days_ago=1,
        updated_hours_ago=1,
        automated_stages_completed=3,
    )
    completed, completed_automation = _record(
        TeamId.TEAM_A,
        None,
        AutomationStatus.COMPLETED,
        created_days_ago=1,
        updated_hours_ago=1,
        automated_stages_completed=2,
    )

    service, _ = _service_for(
        [(in_progress, in_progress_automation), (completed, completed_automation)]
    )
    result = service.get_dashboard(_actor("maya-lim"), date_range="all")

    progress_by_case = {item.case_id: item.progress_percent for item in result.scoped_cases}
    assert progress_by_case[in_progress.case_id] == 50
    assert progress_by_case[completed.case_id] == 100


def test_date_range_filters_cases_by_creation_date() -> None:
    recent, recent_automation = _record(
        TeamId.TEAM_A, None, AutomationStatus.RUNNING, created_days_ago=5, updated_hours_ago=1
    )
    old, old_automation = _record(
        TeamId.TEAM_A, None, AutomationStatus.RUNNING, created_days_ago=45, updated_hours_ago=1
    )

    service, _ = _service_for([(recent, recent_automation), (old, old_automation)])
    default_30d = service.get_dashboard(_actor("maya-lim"), date_range="30d")
    last_90d = service.get_dashboard(_actor("maya-lim"), date_range="90d")
    everything = service.get_dashboard(_actor("maya-lim"), date_range="all")

    assert default_30d.totals.total_cases == 1
    assert last_90d.totals.total_cases == 2
    assert everything.totals.total_cases == 2


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


def test_workload_attributes_teammate_case_fix_to_resolver_once_and_ignores_open() -> None:
    case, automation = _record(
        TeamId.TEAM_A, None, AutomationStatus.RUNNING,
        created_days_ago=2, updated_hours_ago=1, created_by_actor_id="ethan-tan",
    )
    resolved = _resolved_exception(
        case.case_id, BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE, AutomationStage.DOCUMENT,
        created_at=case.created_at, resolved_at=case.created_at + timedelta(hours=2),
        actor_id="maya-lim",
    )
    # Multiple retained decisions are one resolved exception, not multiple fixes.
    duplicate = resolved.decisions[0].model_copy(update={"decision_id": uuid4()})
    resolved = resolved.model_copy(update={"decisions": (*resolved.decisions, duplicate)})
    open_blocker = resolved.model_copy(update={
        "exception_id": uuid4(), "status": BusinessExceptionStatus.OPEN, "resolved_at": None,
    })
    automation = automation.model_copy(update={"exceptions": [resolved, open_blocker]})
    service, _ = _service_for([(case, automation)])
    result = service.get_dashboard(_actor("maya-lim"), date_range="all")
    rows = {row.user_id: row for row in result.workload_by_person}
    assert rows["maya-lim"].open_cases == 0
    assert rows["maya-lim"].blockers_resolved == 1
    assert rows["maya-lim"].mean_fix_time_ms == 7_200_000
    assert rows["ethan-tan"].open_cases == 1
    assert rows["ethan-tan"].blockers_resolved == 0
    assert service.get_dashboard(_actor("sophia-ng")).workload_by_person == ()


def test_date_range_contains_exactly_selected_singapore_calendar_days() -> None:
    from datetime import date

    from app.domain.case_management import case_created_date_bounds

    start, _ = case_created_date_bounds(date(2026, 9, 2), None)
    assert start is not None
    fixtures = []
    for created in (start - timedelta(microseconds=1), start):
        case, automation = _record(
            TeamId.TEAM_A, None, AutomationStatus.RUNNING,
            created_days_ago=1, updated_hours_ago=1,
        )
        automation = automation.model_copy(update={"created_at": created})
        fixtures.append((case, automation))
    service, _ = _service_for(fixtures)
    result = service.get_dashboard(_actor("maya-lim"), date_range="7d")
    assert result.totals.total_cases == 1


def test_legacy_dashboard_default_and_trend_keep_all_history_with_v2_filters() -> None:
    old, automation = _record(
        TeamId.TEAM_A, None, AutomationStatus.COMPLETED,
        created_days_ago=45, updated_hours_ago=1, created_by_actor_id="maya-lim",
    )
    service, _ = _service_for([(old, automation)])
    legacy = service.get_dashboard(_actor("maya-lim"))
    assert legacy.totals.total_cases == 1
    assert len(legacy.historical_trend) == 30
    assert legacy.historical_trend[0].day == (NOW - timedelta(days=29)).date()
    assert sum(row.created_count for row in legacy.historical_trend) == 0
    assert sum(row.completed_count for row in legacy.historical_trend) == 1
    v2 = service.get_dashboard(_actor("maya-lim"), date_range="30d")
    assert v2.totals.total_cases == 0
    assert v2.historical_trend == legacy.historical_trend


def test_draft_actor_and_cancelled_blocker_do_not_become_successful_fixes() -> None:
    case, automation = _record(
        TeamId.TEAM_A, None, AutomationStatus.COMPLETED,
        created_days_ago=2, updated_hours_ago=1, created_by_actor_id="ethan-tan",
        human_interventions=1,
    )
    resolved = _resolved_exception(
        case.case_id, BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE, AutomationStage.DOCUMENT,
        created_at=case.created_at, resolved_at=case.created_at + timedelta(hours=2),
        actor_id="maya-lim",
    )
    draft = resolved.decisions[0].model_copy(update={
        "recorded_at": case.created_at + timedelta(hours=1),
    })
    resolved = resolved.model_copy(update={"decisions": (draft,)})
    cancelled = resolved.model_copy(update={
        "exception_id": uuid4(), "status": BusinessExceptionStatus.CANCELLED,
    })
    automation = automation.model_copy(update={"exceptions": [resolved, cancelled]})
    service, _ = _service_for([(case, automation)])
    result = service.get_dashboard(_actor("maya-lim"))
    assert all(row.blockers_resolved == 0 for row in result.workload_by_person)
    assert result.scoped_cases[0].delay_note.endswith("2.0h fix")


def test_api_omitted_date_range_retains_all_history_and_legacy_trend() -> None:
    from phase13_test_credentials import TEST_PASSWORD

    now = [NOW - timedelta(days=45)]
    app = create_app(
        ordinary_test_settings(), e2e_portfolio_seed_count=3, clock=lambda: now[0],
    )
    now[0] = NOW
    client = RawTestClient(app)
    assert client.post("/api/auth/login", json={
        "user_id": "maya-lim", "password": TEST_PASSWORD,
    }).status_code == 200
    legacy = client.get("/api/clm/zero-touch/dashboard")
    v2 = client.get("/api/clm/zero-touch/dashboard?date_range=30d")
    assert legacy.status_code == v2.status_code == 200
    assert legacy.json()["totals"]["total_cases"] == 3
    assert v2.json()["totals"]["total_cases"] == 0
    assert len(legacy.json()["historical_trend"]) == 30
    assert legacy.json()["historical_trend"] == v2.json()["historical_trend"]


def test_mine_keeps_authorized_resolver_work_without_widening_creator_lists() -> None:
    fixtures = []
    for team, age, hours in (
        (TeamId.TEAM_A, 1, 2), (TeamId.TEAM_A, 45, 4), (TeamId.TEAM_B, 1, 8),
    ):
        case, automation = _record(
            team, None, AutomationStatus.RUNNING, created_days_ago=age,
            updated_hours_ago=1, created_by_actor_id="ethan-tan",
        )
        resolved = _resolved_exception(
            case.case_id, BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
            AutomationStage.DOCUMENT, created_at=case.created_at,
            resolved_at=case.created_at + timedelta(hours=hours), actor_id="maya-lim",
        )
        automation = automation.model_copy(update={"exceptions": [resolved]})
        fixtures.append((case, automation))
    service, _ = _service_for(fixtures)
    mine = service.get_dashboard(_actor("maya-lim"), scope="mine", date_range="30d")
    assert mine.totals.total_cases == 0
    assert mine.scoped_cases == mine.recent_cases == mine.top_active_cases == ()
    assert len(mine.workload_by_person) == 1
    row = mine.workload_by_person[0]
    assert row.user_id == "maya-lim"
    assert row.open_cases == row.completed_cases == 0
    assert row.oldest_open_age_ms is None
    assert row.blockers_resolved == 1
    assert row.mean_fix_time_ms == 7_200_000
    assert mine.exception_breakdown == ()
    rm = service.get_dashboard(_actor("ethan-tan"), scope="mine", date_range="30d")
    assert rm.totals.total_cases == 1
    assert all(row.user_id == "ethan-tan" for row in rm.workload_by_person)


def test_recorded_timings_keep_processing_and_started_clock_semantics() -> None:
    case, automation = _record(
        TeamId.TEAM_A, None, AutomationStatus.COMPLETED,
        created_days_ago=2, updated_hours_ago=1, human_interventions=1,
        stage_durations_ms={AutomationStage.DOCUMENT: 12},
    )
    resolved = _resolved_exception(
        case.case_id, BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE, AutomationStage.DOCUMENT,
        created_at=case.created_at, resolved_at=case.created_at + timedelta(hours=2),
        actor_id="maya-lim",
    )
    started_at = automation.completed_at - timedelta(hours=1)
    automation = automation.model_copy(update={
        "started_at": started_at, "exceptions": [resolved],
        "metrics": automation.metrics.model_copy(update={"total_duration_ms": 3_600_000}),
    })
    service, _ = _service_for([(case, automation)])
    result = service.get_dashboard(_actor("maya-lim"))
    assert result.timing.mean_total_duration_ms == 3_600_000
    document = next(row for row in result.stage_timing if row.stage == AutomationStage.DOCUMENT)
    assert document.with_blocker_mean_ms == 12
    assert result.scoped_cases[0].delay_note.endswith("2.0h fix")



def test_dashboard_ages_share_one_server_observation_and_completed_duration() -> None:
    fixtures = [
        _record(TeamId.TEAM_A, None, status, created_days_ago=2,
                updated_hours_ago=1, created_by_actor_id="maya-lim")
        for status in (AutomationStatus.RUNNING, AutomationStatus.COMPLETED)
    ]
    service, _ = _service_for(fixtures)
    calls = []

    def clock():
        calls.append(NOW)
        return NOW + timedelta(days=len(calls) - 1)

    service._clock = clock
    result = service.get_dashboard(_actor("maya-lim"))
    elapsed = {item.status: item.case_elapsed_ms for item in result.scoped_cases}
    assert elapsed[AutomationStatus.RUNNING] == 172_800_000
    assert elapsed[AutomationStatus.COMPLETED] == 169_200_000
    assert result.workload_by_person[0].oldest_open_age_ms == 172_800_000
    assert result.data_as_of == NOW
    assert len(calls) == 1
    later = service.get_dashboard(_actor("maya-lim"))
    assert next(item for item in later.scoped_cases
                if item.status == AutomationStatus.COMPLETED).case_elapsed_ms == 169_200_000


def test_dashboard_rejects_future_timing_with_sanitized_api_response(monkeypatch) -> None:
    from phase13_test_credentials import TEST_PASSWORD

    original = CaseQueryService.list_cases

    def invalid_timing(self, *args, **kwargs):
        return [item.model_copy(update={"updated_at": NOW + timedelta(microseconds=1)})
                for item in original(self, *args, **kwargs)]

    app = create_app(ordinary_test_settings(), e2e_portfolio_seed_count=3, clock=lambda: NOW)
    client = RawTestClient(app)
    assert client.post("/api/auth/login", json={
        "user_id": "maya-lim", "password": TEST_PASSWORD,
    }).status_code == 200
    monkeypatch.setattr(CaseQueryService, "list_cases", invalid_timing)
    response = client.get("/api/clm/zero-touch/dashboard")
    assert response.status_code == 503
    assert response.json() == {"detail": {
        "code": "DASHBOARD_UNAVAILABLE", "message": "Dashboard data is temporarily unavailable.",
    }}



def test_observation_follows_both_reads_and_includes_concurrent_resolution(monkeypatch) -> None:
    case, automation = _record(
        TeamId.TEAM_A, None, AutomationStatus.RUNNING,
        created_days_ago=2, updated_hours_ago=1, created_by_actor_id="maya-lim",
    )
    service, repository = _service_for([(case, automation)])
    actor = _actor("maya-lim")
    records = service._case_query.list_cases(actor)
    now = [NOW]
    calls = []

    def read_cases(*args, **kwargs):
        calls.append("cases")
        now[0] += timedelta(milliseconds=1)
        return [item.model_copy(update={"updated_at": now[0]}) for item in records]

    def read_automation():
        calls.append("automation")
        now[0] += timedelta(milliseconds=1)
        resolved = _resolved_exception(
            case.case_id, BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
            AutomationStage.DOCUMENT, created_at=case.created_at,
            resolved_at=now[0], actor_id="maya-lim",
        )
        return [automation.model_copy(update={"updated_at": now[0], "exceptions": [resolved]})]

    def observe():
        calls.append("clock")
        return now[0]

    monkeypatch.setattr(service._case_query, "list_cases", read_cases)
    monkeypatch.setattr(repository, "list_records", read_automation)
    service._clock = observe
    result = service.get_dashboard(actor, scope="mine")
    assert calls == ["cases", "automation", "clock"]
    assert result.data_as_of == NOW + timedelta(milliseconds=2)
    assert result.scoped_cases[0].case_elapsed_ms == 172_800_002
    assert result.workload_by_person[0].oldest_open_age_ms == 172_800_002
    assert result.workload_by_person[0].blockers_resolved == 1
    assert result.workload_by_person[0].mean_fix_time_ms == 172_800_002


def test_final_observation_anchors_singapore_cohort_and_legacy_utc_trend(monkeypatch) -> None:
    for initial, final, created, expected_total in (
        (datetime(2026, 9, 8, 15, 59, 59, 999000, tzinfo=UTC),
         datetime(2026, 9, 8, 16, 0, tzinfo=UTC),
         datetime(2026, 9, 1, 16, 0, tzinfo=UTC), 0),
        (datetime(2026, 9, 8, 23, 59, 59, 999000, tzinfo=UTC),
         datetime(2026, 9, 9, 0, 0, tzinfo=UTC),
         datetime(2026, 9, 7, 12, 0, tzinfo=UTC), 1),
    ):
        case, automation = _record(
            TeamId.TEAM_A, None, AutomationStatus.RUNNING,
            created_days_ago=1, updated_hours_ago=1, created_by_actor_id="maya-lim",
        )
        case = case.model_copy(update={"created_at": created})
        automation = automation.model_copy(update={"created_at": created})
        service, _ = _service_for([(case, automation)])
        now = [initial]
        original = service._case_query.list_cases

        def read_cases(*args, original=original, now=now, final=final, **kwargs):
            records = original(*args, **kwargs)
            now[0] = final
            return records

        monkeypatch.setattr(service._case_query, "list_cases", read_cases)
        service._clock = lambda now=now: now[0]
        result = service.get_dashboard(_actor("maya-lim"), date_range="7d")
        assert result.data_as_of == final
        assert result.totals.total_cases == expected_total
        assert result.historical_trend[-1].day == final.date()
        assert len(result.historical_trend) == 30


def test_resolution_milliseconds_and_mean_are_exact_with_submillisecond_floor() -> None:
    for durations, expected in (
        ([timedelta(milliseconds=1001)], 1001),
        ([timedelta(milliseconds=1001), timedelta(milliseconds=3003)], 2002),
        ([timedelta(microseconds=999)], 0),
    ):
        case, automation = _record(
            TeamId.TEAM_A, None, AutomationStatus.RUNNING,
            created_days_ago=2, updated_hours_ago=1, created_by_actor_id="ethan-tan",
        )
        exceptions = [_resolved_exception(
            case.case_id, BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
            AutomationStage.DOCUMENT, created_at=case.created_at,
            resolved_at=case.created_at + duration, actor_id="maya-lim",
        ) for duration in durations]
        automation = automation.model_copy(update={"exceptions": exceptions})
        service, _ = _service_for([(case, automation)])
        result = service.get_dashboard(_actor("maya-lim"), scope="mine")
        assert result.totals.total_cases == 0
        assert result.scoped_cases == ()
        row = result.workload_by_person[0]
        assert row.user_id == "maya-lim"
        assert row.blockers_resolved == len(durations)
        assert row.mean_fix_time_ms == expected


def _r2_dashboard_response(monkeypatch, service, *, query=""):
    from phase13_test_credentials import TEST_PASSWORD

    original = service.get_dashboard
    monkeypatch.setattr(DashboardService, "get_dashboard", lambda self, actor, **kwargs:
                        original(actor, **kwargs))
    client = RawTestClient(create_app(ordinary_test_settings(), clock=lambda: NOW))
    assert client.post("/api/auth/login", json={
        "user_id": "maya-lim", "password": TEST_PASSWORD,
    }).status_code == 200
    return client.get("/api/clm/zero-touch/dashboard" + query)


def _r2_assert_unavailable(response):
    assert response.status_code == 503
    assert response.json() == {"detail": {
        "code": "DASHBOARD_UNAVAILABLE", "message": "Dashboard data is temporarily unavailable.",
    }}


@pytest.mark.parametrize("resolver", ["maya-lim", None])
@pytest.mark.parametrize("status", [AutomationStatus.RUNNING, AutomationStatus.COMPLETED])
def test_pr95_r2_reversed_resolution_fails_closed_for_resolver_and_delay(
    monkeypatch, resolver, status,
):
    case, automation = _record(
        TeamId.TEAM_A, None, status, created_days_ago=2, updated_hours_ago=1,
        human_interventions=1, created_by_actor_id="ethan-tan",
    )
    exception = _resolved_exception(
        case.case_id, BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
        AutomationStage.DOCUMENT, created_at=case.created_at + timedelta(hours=2),
        resolved_at=case.created_at + timedelta(hours=1), actor_id="maya-lim",
    )
    if resolver is None:
        exception = exception.model_copy(update={"decisions": ()})
    automation = automation.model_copy(update={"exceptions": [exception]})
    service, _ = _service_for([(case, automation)])
    with monkeypatch.context() as patch:
        _r2_assert_unavailable(_r2_dashboard_response(patch, service))


def test_pr95_r2_invalid_completed_timing_beyond_display_cap_fails_closed(monkeypatch):
    fixtures = [_record(
        TeamId.TEAM_A, 10, AutomationStatus.COMPLETED,
        created_days_ago=2, updated_hours_ago=1,
    ) for _ in range(200)]
    case, automation = _record(
        TeamId.TEAM_A, None, AutomationStatus.COMPLETED,
        created_days_ago=2, updated_hours_ago=24,
    )
    automation = automation.model_copy(update={
        "completed_at": case.created_at - timedelta(seconds=1),
    })
    service, _ = _service_for([*fixtures, (case, automation)])
    selected = service._case_query.list_cases(_actor("maya-lim"))
    assert len(selected) == 201 and selected[-1].case_id == case.case_id
    _r2_assert_unavailable(_r2_dashboard_response(monkeypatch, service))


def test_pr95_r2_valid_large_cohort_keeps_cap_totals_and_trend():
    fixtures = [_record(
        TeamId.TEAM_A, None, AutomationStatus.COMPLETED,
        created_days_ago=2, updated_hours_ago=1,
    ) for _ in range(201)]
    service, automation = _service_for(fixtures)
    result = service.get_dashboard(_actor("maya-lim"))
    assert len(result.scoped_cases) == 200
    assert result.totals.total_cases == result.totals.completed_cases == 201
    assert sum(row.created_count for row in result.historical_trend) == 201
    assert automation.read_count == 2  # Existing case-query plus dashboard automation reads.


def test_pr95_r2_invalid_out_of_team_and_out_of_date_evidence_is_not_disclosed():
    fixtures = []
    for team, age in ((TeamId.TEAM_A, 1), (TeamId.TEAM_A, 45), (TeamId.TEAM_B, 1)):
        case, automation = _record(
            team, None, AutomationStatus.COMPLETED,
            created_days_ago=age, updated_hours_ago=1,
        )
        if team == TeamId.TEAM_B or age == 45:
            exception = _resolved_exception(
                case.case_id, BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
                AutomationStage.DOCUMENT, created_at=case.created_at + timedelta(hours=2),
                resolved_at=case.created_at + timedelta(hours=1), actor_id="maya-lim",
            )
            automation = automation.model_copy(update={"exceptions": [exception],
                "completed_at": case.created_at - timedelta(seconds=1)})
        fixtures.append((case, automation))
    service, _ = _service_for(fixtures)
    result = service.get_dashboard(_actor("maya-lim"), date_range="7d")
    assert result.totals.total_cases == 1
    assert len(result.scoped_cases) == 1
    assert len(result.historical_trend) == 30
