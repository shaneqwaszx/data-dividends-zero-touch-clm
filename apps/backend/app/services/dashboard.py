"""Backend-authored, RBAC-scoped historical dashboard calculations."""

from collections import Counter
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from app.domain.access import SYNTHETIC_PROFILE_BY_ID, AuthenticatedActor, Role, TeamId
from app.domain.case_management import (
    CasePortfolioRecord,
    case_created_date_bounds,
    project_case_timing,
)
from app.domain.dashboard import (
    DashboardCaseItem,
    DashboardExceptionCount,
    DashboardPriorityCount,
    DashboardScope,
    DashboardSnapshot,
    DashboardStageCaseTiming,
    DashboardStageTiming,
    DashboardStatusCount,
    DashboardTeamCount,
    DashboardTimingSummary,
    DashboardTotals,
    DashboardTrendDay,
    DashboardWeeklyOnboarded,
    DashboardWorkloadRow,
)
from app.domain.jurisdiction import JurisdictionCode
from app.domain.zero_touch import (
    AutomationStage,
    AutomationStatus,
    BusinessExceptionStatus,
    BusinessExceptionType,
    ZeroTouchAutomationRecord,
)
from app.services.administration import TeamDirectoryService
from app.services.case_query import CaseQueryService
from app.services.zero_touch_repository import ZeroTouchAutomationRepository

DASHBOARD_RECENT_LIMIT = 10
DASHBOARD_TOP_ACTIVE_LIMIT = 5
DASHBOARD_SCOPED_CASES_LIMIT = 200
DASHBOARD_WEEKLY_WEEKS = 8
DASHBOARD_TREND_DAYS = 30
DASHBOARD_STAGE_TOP_CASES = 3
DASHBOARD_DATE_RANGE_DAYS: dict[str, int | None] = {"7d": 7, "30d": 30, "90d": 90, "all": None}
AUTOMATION_STAGES_TOTAL = 6


class DashboardService:
    """Build factual counts and bounded lists from already-authorized records."""

    def __init__(
        self,
        case_query: CaseQueryService,
        teams: TeamDirectoryService,
        automation: ZeroTouchAutomationRepository,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._case_query = case_query
        self._teams = teams
        self._automation = automation
        self._clock = clock or (lambda: datetime.now(UTC))

    def get_dashboard(
        self,
        actor: AuthenticatedActor,
        *,
        team_filter: str | None = None,
        scope: Literal["team", "mine"] = "team",
        date_range: Literal["7d", "30d", "90d", "all"] = "all",
    ) -> DashboardSnapshot:
        authorized_records = self._case_query.list_cases(actor, team_filter=team_filter)
        automation_records = self._automation.list_records()
        data_as_of = self._clock()
        range_days = DASHBOARD_DATE_RANGE_DAYS[date_range]
        # Match the portfolio's inclusive Singapore created-calendar-day contract.
        today = data_as_of.astimezone(timezone(timedelta(hours=8))).date()
        created_from = today - timedelta(days=range_days - 1) if range_days else None
        history_records = [
            item for item in authorized_records
            if scope == "team" or item.created_by_actor_id == actor.profile.user_id
        ]
        # Preserve the legacy view's UTC trend before the new created-date filter.
        historical_trend = _trend(history_records, data_as_of.date())
        from_at, to_at = case_created_date_bounds(
            created_from, today if range_days else None,
        )
        cohort_records = [
            item for item in authorized_records
            if (from_at is None or item.created_at >= from_at)
            and (to_at is None or item.created_at < to_at)
        ]
        # Mine limits creator counts/lists, not the actor's authorized resolver work.
        records = [
            item for item in cohort_records
            if scope == "team" or item.created_by_actor_id == actor.profile.user_id
        ]
        total = len(records)
        completed = sum(item.status == AutomationStatus.COMPLETED for item in records)
        prioritised = sum(item.priority is not None for item in records)
        status_counts = Counter(item.status for item in records)
        priority_counts = Counter(item.priority for item in records)
        recent = sorted(
            records,
            key=lambda item: (item.updated_at, str(item.case_id)),
            reverse=True,
        )[:DASHBOARD_RECENT_LIMIT]
        top_active = [item for item in records if item.status != AutomationStatus.COMPLETED][
            :DASHBOARD_TOP_ACTIVE_LIMIT
        ]
        scoped_ids = {item.case_id for item in records}
        cohort_ids = {item.case_id for item in cohort_records}
        cohort_automations = {
            record.case_id: record
            for record in automation_records
            if record.case_id in cohort_ids
        }
        automations = {
            case_id: record for case_id, record in cohort_automations.items()
            if case_id in scoped_ids
        }

        return DashboardSnapshot(
            scope=self._dashboard_scope(actor, team_filter),
            view=scope,
            historical_trend=historical_trend,
            data_as_of=data_as_of,
            totals=DashboardTotals(
                total_cases=total,
                completed_cases=completed,
                non_completed_cases=total - completed,
                completion_rate=(completed / total if total else 0.0),
                prioritised_cases=prioritised,
                unprioritised_cases=total - prioritised,
            ),
            zero_touch_rate=_zero_touch_rate(records),
            timing=_timing_summary(records),
            status_breakdown=tuple(
                DashboardStatusCount(status=status, count=status_counts[status])
                for status in AutomationStatus
            ),
            priority_breakdown=tuple(
                DashboardPriorityCount(priority=priority, count=priority_counts[priority])
                for priority in (*range(10, 0, -1), None)
            ),
            team_breakdown=(
                self._team_breakdown(actor, records, team_filter) if scope == "team" else ()
            ),
            stage_timing=_stage_timing(records, automations),
            exception_breakdown=_exception_breakdown(automations),
            weekly_onboarded=_weekly_onboarded(records, data_as_of.date()),
            workload_by_person=tuple(
                row for row in self._workload_by_person(
                    cohort_records, cohort_automations, data_as_of,
                )
                if scope == "team" or row.user_id == actor.profile.user_id
            ),
            recent_cases=tuple(self._case_item(item, automations, data_as_of) for item in recent),
            top_active_cases=tuple(
                self._case_item(item, automations, data_as_of) for item in top_active
            ),
            scoped_cases=tuple(
                self._case_item(item, automations, data_as_of)
                for item in records[:DASHBOARD_SCOPED_CASES_LIMIT]
            ),
        )

    def _dashboard_scope(
        self, actor: AuthenticatedActor, team_filter: str | None
    ) -> DashboardScope:
        profile = actor.profile
        if profile.role == Role.DIRECTOR:
            team = None
            if team_filter not in {None, "all", "unassigned"}:
                try:
                    team = self._teams.get(TeamId(str(team_filter)))
                except ValueError:
                    team = None
            return DashboardScope(
                actor_role=profile.role,
                access="GLOBAL",
                team_id=team.team_id if team is not None else None,
                team_display_name=(
                    team.display_name
                    if team is not None
                    else ("Legacy unassigned" if team_filter == "unassigned" else None)
                ),
                client_scope_label=(
                    team.client_scope_label
                    if team is not None
                    else (
                        "Legacy unassigned"
                        if team_filter == "unassigned"
                        else "Global / cross-team"
                    )
                ),
            )
        team = self._teams.get(profile.team_id)
        if team is None:
            raise ValueError("authenticated team metadata is unavailable")
        return DashboardScope(
            actor_role=profile.role,
            access="TEAM",
            team_id=team.team_id,
            team_display_name=team.display_name,
            client_scope_label=team.client_scope_label,
        )

    def _team_breakdown(
        self,
        actor: AuthenticatedActor,
        records: list[CasePortfolioRecord],
        team_filter: str | None,
    ) -> tuple[DashboardTeamCount, ...]:
        counts = Counter(item.team_id for item in records)
        if actor.profile.role == Role.DIRECTOR:
            teams = self._teams.options_for(actor)
            if team_filter == "unassigned":
                teams = []
            elif team_filter not in {None, "all"}:
                teams = [team for team in teams if str(team.team_id) == team_filter]
        else:
            team = self._teams.get(actor.profile.team_id)
            teams = [team] if team is not None else []
        return tuple(
            DashboardTeamCount(
                team_id=team.team_id,
                team_display_name=team.display_name,
                client_scope_label=team.client_scope_label,
                count=counts[team.team_id],
            )
            for team in teams
        )

    def _case_item(
        self,
        record: CasePortfolioRecord,
        automations: dict[UUID, ZeroTouchAutomationRecord],
        observed_at: datetime,
    ) -> DashboardCaseItem:
        team = self._teams.get(record.team_id)
        return DashboardCaseItem(
            case_id=record.case_id,
            requested_uen=record.requested_uen,
            legal_name=record.legal_name,
            team_id=record.team_id,
            team_display_name=team.display_name if team is not None else None,
            priority=record.priority,
            status=record.status,
            current_stage=record.current_stage,
            progress_percent=_progress_percent(record, automations.get(record.case_id)),
            final_outcome=record.final_outcome,
            created_at=record.created_at,
            updated_at=record.updated_at,
            completed_at=record.completed_at,
            case_elapsed_ms=_case_elapsed_ms(record, observed_at),
            delay_note=_delay_note(record, automations.get(record.case_id)),
            created_by_display_name=_creator_display_name(record.created_by_actor_id),
        )

    def _workload_by_person(
        self,
        records: list[CasePortfolioRecord],
        automations: dict[UUID, ZeroTouchAutomationRecord],
        observed_at: datetime,
    ) -> tuple[DashboardWorkloadRow, ...]:
        by_person: dict[str, list[CasePortfolioRecord]] = {}
        for item in records:
            if item.created_by_actor_id is None:
                continue
            by_person.setdefault(item.created_by_actor_id, []).append(item)
        # Case load belongs to the creator; retained resolution evidence belongs to
        # its recorded resolver even when a teammate created the case. Only records
        # in the selected authorized scope enter either aggregation.
        fixes: dict[str, list[int]] = {}
        for automation in automations.values():
            for exception in automation.exceptions:
                if (
                    exception.status != BusinessExceptionStatus.RESOLVED
                    or exception.resolved_at is None
                ):
                    continue
                decision = next(
                    (item for item in reversed(exception.decisions)
                     if item.actor_id is not None and item.recorded_at >= exception.resolved_at),
                    None,
                )
                if decision is None or decision.actor_id is None:
                    continue  # Unknown historical attribution stays unknown.
                user_id = decision.actor_id
                duration = (
                    exception.resolved_at - exception.created_at
                ) // timedelta(milliseconds=1)
                fixes.setdefault(user_id, []).append(duration)
                by_person.setdefault(user_id, [])
        rows: list[DashboardWorkloadRow] = []
        for user_id, items in by_person.items():
            open_items = [item for item in items if item.status != AutomationStatus.COMPLETED]
            completed_items = [item for item in items if item.status == AutomationStatus.COMPLETED]
            oldest_open_age_ms = (
                max(_case_elapsed_ms(item, observed_at) for item in open_items)
                if open_items else None
            )
            fix_durations_ms = fixes.get(user_id, [])
            profile = SYNTHETIC_PROFILE_BY_ID.get(user_id)
            rows.append(
                DashboardWorkloadRow(
                    user_id=user_id,
                    display_name=profile.display_name if profile is not None else user_id,
                    open_cases=len(open_items),
                    oldest_open_age_ms=oldest_open_age_ms,
                    completed_cases=len(completed_items),
                    blockers_resolved=len(fix_durations_ms),
                    mean_fix_time_ms=_mean_ms(fix_durations_ms),
                )
            )
        return tuple(sorted(rows, key=lambda row: (-row.open_cases, row.user_id)))


def _case_elapsed_ms(record: CasePortfolioRecord, observed_at: datetime) -> int:
    return project_case_timing(
        created_at=record.created_at,
        updated_at=record.updated_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        recorded_total_duration_ms=record.recorded_total_duration_ms,
        observed_at=observed_at,
    ).case_elapsed_ms


def _zero_touch_rate(records: list[CasePortfolioRecord]) -> float:
    completed = [item for item in records if item.status == AutomationStatus.COMPLETED]
    if not completed:
        return 0.0
    zero_touch = sum(item.human_interventions == 0 for item in completed)
    return zero_touch / len(completed)


def _timing_summary(records: list[CasePortfolioRecord]) -> DashboardTimingSummary:
    completed = [
        item
        for item in records
        if item.status == AutomationStatus.COMPLETED and item.recorded_total_duration_ms is not None
    ]
    zero_touch = [item for item in completed if item.human_interventions == 0]
    blocked = [item for item in completed if item.human_interventions > 0]
    return DashboardTimingSummary(
        mean_total_duration_ms=_mean_ms(
            item.recorded_total_duration_ms for item in completed
            if item.recorded_total_duration_ms is not None
        ),
        zero_touch_mean_duration_ms=_mean_ms(
            item.recorded_total_duration_ms for item in zero_touch
            if item.recorded_total_duration_ms is not None
        ),
        zero_touch_count=len(zero_touch),
        blocked_mean_duration_ms=_mean_ms(
            item.recorded_total_duration_ms for item in blocked
            if item.recorded_total_duration_ms is not None
        ),
        blocked_count=len(blocked),
    )


def _mean_ms(values: Iterable[int]) -> int | None:
    values = list(values)
    if not values:
        return None
    return sum(values) // len(values)


def _stage_timing(
    records: list[CasePortfolioRecord],
    automations: dict[UUID, ZeroTouchAutomationRecord],
) -> tuple[DashboardStageTiming, ...]:
    rows: list[DashboardStageTiming] = []
    for stage in AutomationStage:
        if stage == AutomationStage.COMPLETE:
            continue
        clean_durations: list[int] = []
        blocked_durations: list[int] = []
        blocked_count = 0
        case_timings: list[DashboardStageCaseTiming] = []
        for record in records:
            automation = automations.get(record.case_id)
            if automation is None:
                continue
            had_blocker = any(exception.stage == stage for exception in automation.exceptions)
            if had_blocker:
                blocked_count += 1
            duration = automation.metrics.stage_durations_ms.get(stage)
            if duration is None:
                continue
            (blocked_durations if had_blocker else clean_durations).append(duration)
            case_timings.append(
                DashboardStageCaseTiming(
                    case_id=record.case_id,
                    requested_uen=record.requested_uen,
                    legal_name=record.legal_name,
                    duration_ms=duration,
                    had_blocker=had_blocker,
                )
            )
        combined = clean_durations + blocked_durations
        top_cases = tuple(
            sorted(case_timings, key=lambda item: item.duration_ms, reverse=True)[
                :DASHBOARD_STAGE_TOP_CASES
            ]
        )
        rows.append(
            DashboardStageTiming(
                stage=stage,
                clean_mean_ms=_mean_ms(clean_durations),
                clean_count=len(clean_durations),
                with_blocker_mean_ms=_mean_ms(blocked_durations),
                with_blocker_count=len(blocked_durations),
                combined_mean_ms=_mean_ms(combined),
                blocked_count=blocked_count,
                top_cases=top_cases,
            )
        )
    return tuple(rows)


def _exception_breakdown(
    automations: dict[UUID, ZeroTouchAutomationRecord],
) -> tuple[DashboardExceptionCount, ...]:
    counts = Counter(
        exception.exception_type
        for automation in automations.values()
        for exception in automation.exceptions
    )
    ranked = sorted(
        (item for item in counts.items() if item[1] > 0),
        key=lambda item: (-item[1], item[0].value),
    )
    return tuple(
        DashboardExceptionCount(exception_type=exception_type, count=count)
        for exception_type, count in ranked
    )


def _weekly_onboarded(
    records: list[CasePortfolioRecord], end_day: date
) -> tuple[DashboardWeeklyOnboarded, ...]:
    end_monday = end_day - timedelta(days=end_day.weekday())
    start_monday = end_monday - timedelta(weeks=DASHBOARD_WEEKLY_WEEKS - 1)
    buckets: dict[date, dict[JurisdictionCode, int]] = {}
    unresolved: dict[date, int] = {}
    for item in records:
        if item.status != AutomationStatus.COMPLETED or item.completed_at is None:
            continue
        day = item.completed_at.astimezone(UTC).date()
        if day < start_monday:
            continue
        week_start = day - timedelta(days=day.weekday())
        if item.resolved_jurisdiction is None:
            unresolved[week_start] = unresolved.get(week_start, 0) + 1
        else:
            week_counts = buckets.setdefault(week_start, {})
            week_counts[item.resolved_jurisdiction] = (
                week_counts.get(item.resolved_jurisdiction, 0) + 1
            )
    return tuple(
        DashboardWeeklyOnboarded(
            week_start=week_start,
            by_jurisdiction=buckets.get(week_start, {}),
            unresolved_count=unresolved.get(week_start, 0),
        )
        for offset in range(DASHBOARD_WEEKLY_WEEKS)
        if (week_start := start_monday + timedelta(weeks=offset)) <= end_monday
    )


def _delay_note(
    record: CasePortfolioRecord, automation: ZeroTouchAutomationRecord | None
) -> str | None:
    if record.status == AutomationStatus.COMPLETED:
        if record.human_interventions == 0:
            return "Zero-touch"
        if automation is None:
            return None
        slowest: tuple[BusinessExceptionType, int] | None = None
        for exception in automation.exceptions:
            if (
                exception.status != BusinessExceptionStatus.RESOLVED
                or exception.resolved_at is None
            ):
                continue
            duration_ms = (
                exception.resolved_at - exception.created_at
            ) // timedelta(milliseconds=1)
            if slowest is None or duration_ms > slowest[1]:
                slowest = (exception.exception_type, duration_ms)
        if slowest is None:
            return None
        exception_type, duration_ms = slowest
        return f"{_exception_label(exception_type)} \u00b7 {_format_hours(duration_ms)} fix"
    if automation is None:
        return None
    open_exceptions = [
        exception
        for exception in automation.exceptions
        if exception.status == BusinessExceptionStatus.OPEN
    ]
    if not open_exceptions:
        return None
    return _exception_label(open_exceptions[0].exception_type)


def _creator_display_name(created_by_actor_id: str | None) -> str | None:
    if created_by_actor_id is None:
        return None
    profile = SYNTHETIC_PROFILE_BY_ID.get(created_by_actor_id)
    return profile.display_name if profile is not None else created_by_actor_id


def _progress_percent(
    record: CasePortfolioRecord, automation: ZeroTouchAutomationRecord | None
) -> int:
    if record.status == AutomationStatus.COMPLETED:
        return 100
    if automation is None:
        return 0
    completed = min(AUTOMATION_STAGES_TOTAL, automation.metrics.automated_stages_completed)
    return round(completed / AUTOMATION_STAGES_TOTAL * 100)


def _exception_label(exception_type: BusinessExceptionType) -> str:
    return exception_type.value.replace("_", " ").capitalize()


def _format_hours(duration_ms: int) -> str:
    return f"{duration_ms / 3_600_000:.1f}h"


def _trend(records: list[CasePortfolioRecord], end_day: date) -> tuple[DashboardTrendDay, ...]:
    start_day = end_day - timedelta(days=DASHBOARD_TREND_DAYS - 1)
    created = Counter(_utc_day(item.created_at) for item in records)
    completed = Counter(
        _utc_day(item.completed_at) for item in records if item.completed_at is not None
    )
    return tuple(
        DashboardTrendDay(
            day=day,
            created_count=created[day],
            completed_count=completed[day],
        )
        for offset in range(DASHBOARD_TREND_DAYS)
        if (day := start_day + timedelta(days=offset)) <= end_day
    )


def _utc_day(value: datetime) -> date:
    return value.astimezone(UTC).date()
