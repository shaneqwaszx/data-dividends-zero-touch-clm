"""Backend-authored, RBAC-scoped historical dashboard calculations."""

from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from app.domain.access import SYNTHETIC_PROFILE_BY_ID, AuthenticatedActor, Role, TeamId
from app.domain.case_management import (
    CasePortfolioRecord,
    CaseTimingDataInvalidError,
    case_created_date_bounds,
    project_case_timing,
)
from app.domain.dashboard import (
    DashboardAttentionPolicy,
    DashboardCaseItem,
    DashboardExceptionCount,
    DashboardKpis,
    DashboardPeriodComparison,
    DashboardPriorityCount,
    DashboardRework,
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
from app.domain.dashboard_attention import (
    AT_RISK_WINDOW_MS,
    INACTIVITY_MS,
    SLA_RULES_DECISION,
    SLA_TARGET_MS,
    STALE_BLOCKER_MS,
    AttentionLevel,
    AttentionReason,
    SlaStatus,
    attention,
    sla_status,
)
from app.domain.jurisdiction import JurisdictionCode
from app.domain.zero_touch import (
    AutomationStage,
    AutomationStatus,
    BusinessException,
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
# Statuses the Dashboard presents as blocked; matches the browser's existing grouping.
DASHBOARD_BLOCKED_STATUSES = frozenset({
    AutomationStatus.WAITING_FOR_REVIEW,
    AutomationStatus.RECOVERY_PENDING,
    AutomationStatus.TECHNICAL_FAILURE,
})


@dataclass(frozen=True)
class _CaseFacts:
    """Per-case derived values sharing the response's single observation instant."""

    elapsed_ms: int
    sla: SlaStatus
    attention_level: AttentionLevel | None
    attention_reasons: tuple[AttentionReason, ...]
    oldest_open_blocker_age_ms: int | None


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
        with self._automation.capture_for_cases(frozenset(
            item.case_id for item in authorized_records
        )) as batch:
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
            # The equally long window before a bounded range, for period comparison only.
            previous_window: tuple[date, date] | None = None
            previous_records: list[CasePortfolioRecord] = []
            if range_days and created_from is not None:
                previous_window = (
                    created_from - timedelta(days=range_days),
                    created_from - timedelta(days=1),
                )
                previous_from_at, previous_to_at = case_created_date_bounds(*previous_window)
                previous_records = [
                    item for item in authorized_records
                    if (scope == "team" or item.created_by_actor_id == actor.profile.user_id)
                    and previous_from_at is not None and previous_to_at is not None
                    and previous_from_at <= item.created_at < previous_to_at
                ]
            # The batch is one-shot, so both cohorts are selected in one read.
            automation_records = batch.read_selected(frozenset(
                item.case_id for item in (*cohort_records, *previous_records)
            ))
            # Validate every selected authorized case before any display-list cap.
            for item in (*cohort_records, *previous_records):
                _case_elapsed_ms(item, data_as_of)
            for automation in automation_records:
                if any(type(value) is not int or value < 0
                       for value in automation.metrics.stage_durations_ms.values()):
                    raise CaseTimingDataInvalidError("recorded stage duration is invalid")
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
            previous_ids = {item.case_id for item in previous_records}
            previous_automations = {
                record.case_id: record
                for record in automation_records
                if record.case_id in previous_ids
            }

            # One chronology guard covers resolver workload and completed delay notes,
            # including successful resolutions whose resolver was not recorded.
            for automation in cohort_automations.values():
                for exception in automation.exceptions:
                    if (
                        exception.status == BusinessExceptionStatus.RESOLVED
                        and exception.resolved_at is not None
                    ):
                        project_case_timing(
                            created_at=exception.created_at,
                            updated_at=exception.resolved_at,
                            started_at=None,
                            completed_at=exception.resolved_at,
                            recorded_total_duration_ms=None,
                            observed_at=data_as_of,
                        )

            facts = {
                item.case_id: _case_facts(item, cohort_automations.get(item.case_id), data_as_of)
                for item in cohort_records
            }
            previous_facts = {
                item.case_id: _case_facts(
                    item, previous_automations.get(item.case_id), data_as_of,
                )
                for item in previous_records
            }
            week_starts = _week_starts(data_as_of.date())

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
                    self._team_breakdown(actor, records, team_filter, facts, automations)
                    if scope == "team" else ()
                ),
                stage_timing=_stage_timing(records, automations),
                exception_breakdown=_exception_breakdown(records, automations, week_starts),
                weekly_onboarded=_weekly_onboarded(records, facts, week_starts),
                workload_by_person=tuple(
                    row for row in self._workload_by_person(
                        cohort_records, cohort_automations, data_as_of, facts,
                    )
                    if scope == "team" or row.user_id == actor.profile.user_id
                ),
                recent_cases=tuple(
                    self._case_item(item, automations, data_as_of, facts) for item in recent
                ),
                top_active_cases=tuple(
                    self._case_item(item, automations, data_as_of, facts) for item in top_active
                ),
                scoped_cases=tuple(
                    self._case_item(item, automations, data_as_of, facts)
                    for item in records[:DASHBOARD_SCOPED_CASES_LIMIT]
                ),
                attention_policy=DashboardAttentionPolicy(
                    decision=SLA_RULES_DECISION,
                    sla_target_ms=SLA_TARGET_MS,
                    at_risk_window_ms=AT_RISK_WINDOW_MS,
                    stale_blocker_ms=STALE_BLOCKER_MS,
                    inactivity_ms=INACTIVITY_MS,
                ),
                kpis=_kpis(records, automations, facts),
                previous_period=(
                    _period_comparison(
                        previous_window, previous_records, previous_automations, previous_facts,
                    )
                    if previous_window is not None else None
                ),
                rework=_rework(records, automations),
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
        facts: dict[UUID, _CaseFacts],
        automations: dict[UUID, ZeroTouchAutomationRecord],
    ) -> tuple[DashboardTeamCount, ...]:
        counts = Counter(item.team_id for item in records)
        by_team: dict[TeamId | None, list[CasePortfolioRecord]] = {}
        for item in records:
            by_team.setdefault(item.team_id, []).append(item)
        status_counts = Counter((item.team_id, item.status) for item in records)
        zero_touch = Counter(
            item.team_id
            for item in records
            if item.status == AutomationStatus.COMPLETED and item.human_interventions == 0
        )
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
                status_breakdown=tuple(
                    DashboardStatusCount(status=status, count=status_counts[(team.team_id, status)])
                    for status in AutomationStatus
                ),
                zero_touch_count=zero_touch[team.team_id],
                sla_met_count=outcomes.sla_met_count,
                overdue_count=outcomes.overdue_count,
                high_attention_count=outcomes.high_attention_count,
                mean_end_to_end_ms=outcomes.mean_end_to_end_ms,
                resolved_blockers=outcomes.resolved_blockers,
                mean_fix_ms=outcomes.mean_fix_ms,
            )
            for team in teams
            for outcomes in (_team_outcomes(by_team.get(team.team_id, []), facts, automations),)
        )

    def _case_item(
        self,
        record: CasePortfolioRecord,
        automations: dict[UUID, ZeroTouchAutomationRecord],
        observed_at: datetime,
        facts: dict[UUID, _CaseFacts],
    ) -> DashboardCaseItem:
        team = self._teams.get(record.team_id)
        case_facts = facts[record.case_id]
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
            jurisdiction=record.resolved_jurisdiction,
            sla_status=case_facts.sla,
            sla_due_at=record.created_at + timedelta(milliseconds=SLA_TARGET_MS),
            attention_level=case_facts.attention_level,
            attention_reasons=case_facts.attention_reasons,
            open_exception_types=record.active_exception_types,
            oldest_open_blocker_age_ms=case_facts.oldest_open_blocker_age_ms,
        )

    def _workload_by_person(
        self,
        records: list[CasePortfolioRecord],
        automations: dict[UUID, ZeroTouchAutomationRecord],
        observed_at: datetime,
        facts: dict[UUID, _CaseFacts],
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
                    running_cases=sum(
                        item.status not in DASHBOARD_BLOCKED_STATUSES for item in open_items
                    ),
                    blocked_cases=sum(
                        item.status in DASHBOARD_BLOCKED_STATUSES for item in open_items
                    ),
                    overdue_cases=sum(
                        facts[item.case_id].sla == SlaStatus.OVERDUE for item in open_items
                    ),
                    high_attention_cases=sum(
                        facts[item.case_id].attention_level == AttentionLevel.HIGH
                        for item in open_items
                    ),
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
        open_blocked_count = 0
        reached_count = 0
        resolution_durations: list[int] = []
        case_timings: list[DashboardStageCaseTiming] = []
        for record in records:
            automation = automations.get(record.case_id)
            if automation is None:
                continue
            had_blocker = any(exception.stage == stage for exception in automation.exceptions)
            if had_blocker:
                blocked_count += 1
            if any(
                exception.stage == stage and exception.status == BusinessExceptionStatus.OPEN
                for exception in automation.exceptions
            ):
                open_blocked_count += 1
            resolution_durations.extend(
                duration_ms
                for exception in automation.exceptions
                if exception.stage == stage
                and (duration_ms := _resolution_ms(exception)) is not None
            )
            duration = automation.metrics.stage_durations_ms.get(stage)
            if had_blocker or duration is not None:
                reached_count += 1
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
                reached_count=reached_count,
                resolution_mean_ms=_mean_ms(resolution_durations),
                resolution_count=len(resolution_durations),
                processing_total_ms=sum(combined),
                resolution_total_ms=sum(resolution_durations),
                open_blocked_count=open_blocked_count,
            )
        )
    return tuple(rows)


def _exception_breakdown(
    records: list[CasePortfolioRecord],
    automations: dict[UUID, ZeroTouchAutomationRecord],
    week_starts: tuple[date, ...],
) -> tuple[DashboardExceptionCount, ...]:
    jurisdictions = {item.case_id: item.resolved_jurisdiction for item in records}
    exceptions = [
        exception for automation in automations.values() for exception in automation.exceptions
    ]
    by_jurisdiction: dict[BusinessExceptionType, Counter[JurisdictionCode]] = {}
    unresolved = Counter[BusinessExceptionType]()
    weekly: dict[BusinessExceptionType, list[int]] = {}
    week_index = {week: index for index, week in enumerate(week_starts)}
    for exception in exceptions:
        jurisdiction = jurisdictions.get(exception.case_id)
        if jurisdiction is None:
            unresolved[exception.exception_type] += 1
        else:
            by_jurisdiction.setdefault(exception.exception_type, Counter())[jurisdiction] += 1
        index = week_index.get(_week_start(exception.created_at.astimezone(UTC).date()))
        if index is not None:
            weekly.setdefault(exception.exception_type, [0] * len(week_starts))[index] += 1
    counts = Counter(exception.exception_type for exception in exceptions)
    open_counts = Counter(
        exception.exception_type
        for exception in exceptions
        if exception.status == BusinessExceptionStatus.OPEN
    )
    fixes: dict[BusinessExceptionType, list[int]] = {}
    for exception in exceptions:
        duration_ms = _resolution_ms(exception)
        if duration_ms is not None:
            fixes.setdefault(exception.exception_type, []).append(duration_ms)
    ranked = sorted(
        (item for item in counts.items() if item[1] > 0),
        key=lambda item: (-item[1], item[0].value),
    )
    return tuple(
        DashboardExceptionCount(
            exception_type=exception_type,
            count=count,
            open_count=open_counts[exception_type],
            resolved_count=len(fixes.get(exception_type, [])),
            mean_fix_ms=_mean_ms(fixes.get(exception_type, [])),
            total_fix_ms=sum(fixes.get(exception_type, [])),
            by_jurisdiction=dict(by_jurisdiction.get(exception_type, Counter())),
            unresolved_jurisdiction_count=unresolved[exception_type],
            weekly_counts=tuple(weekly.get(exception_type, [0] * len(week_starts))),
        )
        for exception_type, count in ranked
    )


def _resolution_ms(exception: BusinessException) -> int | None:
    """Elapsed RESOLVED blocker time, matching workload fix-time arithmetic."""

    if exception.status != BusinessExceptionStatus.RESOLVED or exception.resolved_at is None:
        return None
    return (exception.resolved_at - exception.created_at) // timedelta(milliseconds=1)


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _week_starts(end_day: date) -> tuple[date, ...]:
    """Eight UTC Monday weeks ending with the week that contains ``end_day``."""

    end_monday = _week_start(end_day)
    return tuple(
        end_monday - timedelta(weeks=DASHBOARD_WEEKLY_WEEKS - 1 - offset)
        for offset in range(DASHBOARD_WEEKLY_WEEKS)
    )


def _weekly_onboarded(
    records: list[CasePortfolioRecord],
    facts: dict[UUID, _CaseFacts],
    week_starts: tuple[date, ...],
) -> tuple[DashboardWeeklyOnboarded, ...]:
    buckets: dict[date, dict[JurisdictionCode, int]] = {}
    unresolved: dict[date, int] = {}
    zero_touch: dict[date, int] = {}
    end_to_end: dict[date, list[int]] = {}
    for item in records:
        if item.status != AutomationStatus.COMPLETED or item.completed_at is None:
            continue
        week_start = _week_start(item.completed_at.astimezone(UTC).date())
        if week_start < week_starts[0]:
            continue
        end_to_end.setdefault(week_start, []).append(facts[item.case_id].elapsed_ms)
        if item.human_interventions == 0:
            zero_touch[week_start] = zero_touch.get(week_start, 0) + 1
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
            zero_touch_count=zero_touch.get(week_start, 0),
            mean_end_to_end_ms=_mean_ms(end_to_end.get(week_start, [])),
        )
        for week_start in week_starts
    )


def _case_facts(
    record: CasePortfolioRecord,
    automation: ZeroTouchAutomationRecord | None,
    observed_at: datetime,
) -> _CaseFacts:
    elapsed_ms = _case_elapsed_ms(record, observed_at)
    sla = sla_status(record.status, elapsed_ms)
    open_ages: list[int] = []
    for exception in automation.exceptions if automation is not None else ():
        if exception.status != BusinessExceptionStatus.OPEN:
            continue
        age_ms = (observed_at - exception.created_at) // timedelta(milliseconds=1)
        if age_ms < 0:
            raise CaseTimingDataInvalidError("open blocker is newer than the observation")
        open_ages.append(age_ms)
    oldest = max(open_ages) if open_ages else None
    level, reasons = attention(
        record.status,
        sla,
        oldest_open_blocker_age_ms=oldest,
        since_update=observed_at - record.updated_at,
    )
    return _CaseFacts(
        elapsed_ms=elapsed_ms,
        sla=sla,
        attention_level=level,
        attention_reasons=reasons,
        oldest_open_blocker_age_ms=oldest,
    )


def _completion_figures(
    records: list[CasePortfolioRecord],
    automations: dict[UUID, ZeroTouchAutomationRecord],
    facts: dict[UUID, _CaseFacts],
) -> tuple[int, float | None, int | None, int | None, int, float | None]:
    """Completed count, zero-touch rate, mean processing, mean end-to-end, SLA met, compliance."""

    completed = [item for item in records if item.status == AutomationStatus.COMPLETED]
    processing = [
        sum(automation.metrics.stage_durations_ms.values())
        for item in completed
        if (automation := automations.get(item.case_id)) is not None
        and automation.metrics.stage_durations_ms
    ]
    met = sum(facts[item.case_id].sla == SlaStatus.MET for item in completed)
    return (
        len(completed),
        (sum(item.human_interventions == 0 for item in completed) / len(completed))
        if completed else None,
        _mean_ms(processing),
        _mean_ms(facts[item.case_id].elapsed_ms for item in completed),
        met,
        met / len(completed) if completed else None,
    )


def _kpis(
    records: list[CasePortfolioRecord],
    automations: dict[UUID, ZeroTouchAutomationRecord],
    facts: dict[UUID, _CaseFacts],
) -> DashboardKpis:
    open_items = [item for item in records if item.status != AutomationStatus.COMPLETED]
    completed, zero_touch, processing, end_to_end, met, compliance = _completion_figures(
        records, automations, facts,
    )
    return DashboardKpis(
        open_cases=len(open_items),
        running_cases=sum(item.status not in DASHBOARD_BLOCKED_STATUSES for item in open_items),
        blocked_cases=sum(item.status in DASHBOARD_BLOCKED_STATUSES for item in open_items),
        awaiting_review_cases=sum(
            item.status == AutomationStatus.WAITING_FOR_REVIEW for item in open_items
        ),
        completed_cases=completed,
        zero_touch_rate=zero_touch,
        mean_processing_ms=processing,
        mean_end_to_end_ms=end_to_end,
        sla_met_cases=met,
        sla_compliance_rate=compliance,
        overdue_cases=sum(facts[item.case_id].sla == SlaStatus.OVERDUE for item in open_items),
        at_risk_cases=sum(facts[item.case_id].sla == SlaStatus.AT_RISK for item in open_items),
        high_attention_cases=sum(
            facts[item.case_id].attention_level == AttentionLevel.HIGH for item in open_items
        ),
    )


def _period_comparison(
    window: tuple[date, date],
    records: list[CasePortfolioRecord],
    automations: dict[UUID, ZeroTouchAutomationRecord],
    facts: dict[UUID, _CaseFacts],
) -> DashboardPeriodComparison:
    completed, zero_touch, processing, end_to_end, _met, compliance = _completion_figures(
        records, automations, facts,
    )
    return DashboardPeriodComparison(
        created_from=window[0],
        created_to=window[1],
        total_cases=len(records),
        completed_cases=completed,
        zero_touch_rate=zero_touch,
        mean_processing_ms=processing,
        mean_end_to_end_ms=end_to_end,
        sla_compliance_rate=compliance,
    )


@dataclass(frozen=True)
class _TeamOutcomes:
    sla_met_count: int
    overdue_count: int
    high_attention_count: int
    mean_end_to_end_ms: int | None
    resolved_blockers: int
    mean_fix_ms: int | None


def _team_outcomes(
    records: list[CasePortfolioRecord],
    facts: dict[UUID, _CaseFacts],
    automations: dict[UUID, ZeroTouchAutomationRecord],
) -> _TeamOutcomes:
    """Per-team SLA, attention, end-to-end and blocker-fix figures over the team's cases."""

    completed = [item for item in records if item.status == AutomationStatus.COMPLETED]
    open_items = [item for item in records if item.status != AutomationStatus.COMPLETED]
    fixes = [
        duration_ms
        for item in records
        if (automation := automations.get(item.case_id)) is not None
        for exception in automation.exceptions
        if (duration_ms := _resolution_ms(exception)) is not None
    ]
    return _TeamOutcomes(
        sla_met_count=sum(facts[item.case_id].sla == SlaStatus.MET for item in completed),
        overdue_count=sum(facts[item.case_id].sla == SlaStatus.OVERDUE for item in open_items),
        high_attention_count=sum(
            facts[item.case_id].attention_level == AttentionLevel.HIGH for item in open_items
        ),
        mean_end_to_end_ms=_mean_ms(facts[item.case_id].elapsed_ms for item in completed),
        resolved_blockers=len(fixes),
        mean_fix_ms=_mean_ms(fixes),
    )


def _rework(
    records: list[CasePortfolioRecord],
    automations: dict[UUID, ZeroTouchAutomationRecord],
) -> DashboardRework:
    with_blockers = 0
    rework = 0
    for item in records:
        automation = automations.get(item.case_id)
        if automation is None or not automation.exceptions:
            continue
        with_blockers += 1
        per_stage = Counter(exception.stage for exception in automation.exceptions)
        if any(count >= 2 for count in per_stage.values()):
            rework += 1
    return DashboardRework(
        total_cases=len(records), cases_with_blockers=with_blockers, rework_cases=rework,
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
