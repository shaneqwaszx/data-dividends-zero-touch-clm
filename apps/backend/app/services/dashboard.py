"""Backend-authored, RBAC-scoped historical dashboard calculations."""

from collections import Counter
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

from app.domain.access import AuthenticatedActor, Role, TeamId
from app.domain.case_management import CasePortfolioRecord
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
from app.services.administration import TeamDirectoryService
from app.services.case_query import CaseQueryService

DASHBOARD_RECENT_LIMIT = 10
DASHBOARD_TOP_ACTIVE_LIMIT = 5
DASHBOARD_TREND_DAYS = 30


class DashboardService:
    """Build factual counts and bounded lists from already-authorized records."""

    def __init__(
        self,
        case_query: CaseQueryService,
        teams: TeamDirectoryService,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._case_query = case_query
        self._teams = teams
        self._clock = clock or (lambda: datetime.now(UTC))

    def get_dashboard(
        self, actor: AuthenticatedActor, *, team_filter: str | None = None
    ) -> DashboardSnapshot:
        data_as_of = self._clock()
        records = self._case_query.list_cases(actor, team_filter=team_filter)
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

        return DashboardSnapshot(
            scope=self._dashboard_scope(actor, team_filter),
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
            team_breakdown=self._team_breakdown(actor, records, team_filter),
            recent_cases=tuple(self._case_item(item) for item in recent),
            top_active_cases=tuple(self._case_item(item) for item in top_active),
            historical_trend=_trend(records, data_as_of.date()),
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

    def _case_item(self, record: CasePortfolioRecord) -> DashboardCaseItem:
        team = self._teams.get(record.team_id)
        return DashboardCaseItem(
            case_id=record.case_id,
            requested_uen=record.requested_uen,
            legal_name=record.legal_name,
            team_id=record.team_id,
            team_display_name=team.display_name if team is not None else None,
            priority=record.priority,
            status=record.status,
            final_outcome=record.final_outcome,
            created_at=record.created_at,
            updated_at=record.updated_at,
            completed_at=record.completed_at,
        )


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
