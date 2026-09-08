"""Backend-authored, RBAC-scoped historical dashboard calculations."""

from collections import Counter
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

from app.domain.access import TEAM_BY_ID, AuthenticatedActor, Role
from app.domain.dashboard import (
    DashboardCaseItem,
    DashboardPriorityCount,
    DashboardScope,
    DashboardSnapshot,
    DashboardStatusCount,
    DashboardTeamCount,
    DashboardTotals,
    DashboardTrendDay,
)
from app.domain.zero_touch import AutomationStatus
from app.services.case_query import AuthorizedCaseRecord, CaseQueryService

DASHBOARD_RECENT_LIMIT = 10
DASHBOARD_TOP_ACTIVE_LIMIT = 5
DASHBOARD_TREND_DAYS = 30


class DashboardService:
    """Build factual counts and bounded lists from already-authorized records."""

    def __init__(
        self,
        case_query: CaseQueryService,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._case_query = case_query
        self._clock = clock or (lambda: datetime.now(UTC))

    def get_dashboard(self, actor: AuthenticatedActor) -> DashboardSnapshot:
        data_as_of = self._clock()
        records = self._case_query.list_cases(actor)
        total = len(records)
        completed = sum(item.automation.status == AutomationStatus.COMPLETED for item in records)
        prioritised = sum(item.case.priority is not None for item in records)
        status_counts = Counter(item.automation.status for item in records)
        priority_counts = Counter(item.case.priority for item in records)
        recent = sorted(
            records,
            key=lambda item: (item.automation.updated_at, str(item.automation.case_id)),
            reverse=True,
        )[:DASHBOARD_RECENT_LIMIT]
        top_active = [
            item for item in records if item.automation.status != AutomationStatus.COMPLETED
        ][:DASHBOARD_TOP_ACTIVE_LIMIT]

        return DashboardSnapshot(
            scope=_dashboard_scope(actor),
            data_as_of=data_as_of,
            totals=DashboardTotals(
                total_cases=total,
                completed_cases=completed,
                non_completed_cases=total - completed,
                completion_rate=(completed / total if total else 0.0),
                prioritised_cases=prioritised,
                unprioritised_cases=total - prioritised,
            ),
            status_breakdown=tuple(
                DashboardStatusCount(status=status, count=status_counts[status])
                for status in AutomationStatus
            ),
            priority_breakdown=tuple(
                DashboardPriorityCount(priority=priority, count=priority_counts[priority])
                for priority in (*range(10, 0, -1), None)
            ),
            team_breakdown=_team_breakdown(actor, records),
            recent_cases=tuple(_case_item(item) for item in recent),
            top_active_cases=tuple(_case_item(item) for item in top_active),
            historical_trend=_trend(records, data_as_of.date()),
        )


def _dashboard_scope(actor: AuthenticatedActor) -> DashboardScope:
    profile = actor.profile
    if profile.role == Role.DIRECTOR:
        return DashboardScope(
            actor_role=profile.role,
            access="GLOBAL",
            team_id=None,
            team_display_name=None,
            client_scope_label=profile.client_scope_label,
        )
    team = TEAM_BY_ID[profile.team_id]  # type: ignore[index]
    return DashboardScope(
        actor_role=profile.role,
        access="TEAM",
        team_id=team.team_id,
        team_display_name=team.display_name,
        client_scope_label=team.client_scope_label,
    )


def _team_breakdown(
    actor: AuthenticatedActor, records: list[AuthorizedCaseRecord]
) -> tuple[DashboardTeamCount, ...]:
    counts = Counter(item.case.team_id for item in records)
    team_ids = (
        tuple(TEAM_BY_ID) if actor.profile.role == Role.DIRECTOR else (actor.profile.team_id,)
    )
    return tuple(
        DashboardTeamCount(
            team_id=team_id,
            team_display_name=TEAM_BY_ID[team_id].display_name,
            client_scope_label=TEAM_BY_ID[team_id].client_scope_label,
            count=counts[team_id],
        )
        for team_id in team_ids
        if team_id is not None
    )


def _case_item(record: AuthorizedCaseRecord) -> DashboardCaseItem:
    team = TEAM_BY_ID.get(record.case.team_id) if record.case.team_id is not None else None
    return DashboardCaseItem(
        case_id=record.case.case_id,
        requested_uen=record.case.requested_uen,
        legal_name=(record.case.entity.legal_name if record.case.entity is not None else None),
        team_id=record.case.team_id,
        team_display_name=team.display_name if team is not None else None,
        priority=record.case.priority,
        status=record.automation.status,
        final_outcome=record.automation.metrics.final_outcome,
        created_at=record.automation.created_at,
        updated_at=record.automation.updated_at,
        completed_at=record.automation.completed_at,
    )


def _trend(records: list[AuthorizedCaseRecord], end_day: date) -> tuple[DashboardTrendDay, ...]:
    start_day = end_day - timedelta(days=DASHBOARD_TREND_DAYS - 1)
    created = Counter(_utc_day(item.automation.created_at) for item in records)
    completed = Counter(
        _utc_day(item.automation.completed_at)
        for item in records
        if item.automation.completed_at is not None
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
