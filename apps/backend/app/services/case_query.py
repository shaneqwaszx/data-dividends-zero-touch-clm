"""Authorized case portfolio query and atomic priority mutation owner."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError

from app.domain.access import AuthenticatedActor, CasePriority, Role, TeamId
from app.domain.case_management import (
    CaseActivityAction,
    CaseActivityItem,
    CaseActivityPage,
    CaseActivityQuery,
    CasePortfolioPage,
    CasePortfolioQuery,
    CasePortfolioRecord,
    CasePortfolioScope,
    PortfolioScopeKind,
    order_case_portfolio_records,
)
from app.domain.case_management import PriorityFilter as PriorityFilter
from app.domain.case_management import PrioritySort as PrioritySort
from app.domain.jurisdiction import JurisdictionCode
from app.domain.models import EventOutcome, OnboardingCase, WorkflowEvent
from app.domain.zero_touch import AutomationStage, AutomationStatus, BusinessExceptionType
from app.services.admin_repository import TeamRepository
from app.services.authorization import CaseAccessPolicy
from app.services.case_portfolio_repository import (
    CasePortfolioRepository,
    InMemoryCasePortfolioRepository,
)
from app.services.onboarding import OnboardingService
from app.services.repository import OnboardingCaseRepository
from app.services.zero_touch_repository import ZeroTouchAutomationRepository


class CaseTeamFilterForbiddenError(Exception):
    pass


class CaseTeamFilterInvalidError(Exception):
    pass


class CaseActivityQueryInvalidError(Exception):
    pass


class CasePortfolioQueryInvalidError(Exception):
    pass


class CaseQueryService:
    """Join canonical cases to automation, filter access, and own final ordering."""

    def __init__(
        self,
        *,
        cases: OnboardingService,
        case_repository: OnboardingCaseRepository,
        automation_repository: ZeroTouchAutomationRepository,
        access_policy: CaseAccessPolicy,
        teams: TeamRepository,
        portfolio_repository: CasePortfolioRepository | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._cases = cases
        self._case_repository = case_repository
        self._automation_repository = automation_repository
        self._portfolio_repository = portfolio_repository or InMemoryCasePortfolioRepository(
            case_repository, automation_repository
        )
        self._access_policy = access_policy
        self._teams = teams
        self._clock = clock or (lambda: datetime.now(UTC))

    def list_cases(
        self,
        actor: AuthenticatedActor,
        *,
        status: AutomationStatus | None = None,
        priority_filter: PriorityFilter = PriorityFilter.ALL,
        priority_sort: PrioritySort = PrioritySort.HIGHEST_FIRST,
        team_filter: str | None = None,
        attention_type: BusinessExceptionType | None = None,
    ) -> list[CasePortfolioRecord]:
        scope = self._resolve_scope(actor, team_filter)
        authorized = self._portfolio_repository.list_authorized(scope, status=status)
        filtered = [
            item
            for item in authorized
            if _matches_priority(item.priority, priority_filter)
            and (attention_type is None or attention_type in item.active_exception_types)
        ]
        return order_case_portfolio_records(filtered, priority_sort)

    def list_portfolio(
        self,
        actor: AuthenticatedActor,
        *,
        status: AutomationStatus | None = None,
        priority_filter: PriorityFilter = PriorityFilter.ALL,
        priority_sort: PrioritySort = PrioritySort.HIGHEST_FIRST,
        team_filter: str | None = None,
        attention_type: BusinessExceptionType | None = None,
        jurisdiction: JurisdictionCode | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> CasePortfolioPage:
        scope = self._resolve_scope(actor, team_filter)
        try:
            query = CasePortfolioQuery(
                scope=scope,
                status=status,
                priority_filter=priority_filter,
                priority_sort=priority_sort,
                attention_type=attention_type,
                jurisdiction=jurisdiction,
                search=search,
                limit=limit,
                offset=offset,
            )
        except ValidationError:
            raise CasePortfolioQueryInvalidError from None
        return self._portfolio_repository.list_page(query)

    def list_activity(
        self,
        actor: AuthenticatedActor,
        *,
        case_id: UUID | None = None,
        team_filter: str | None = None,
        action: CaseActivityAction | None = None,
        stage: AutomationStage | None = None,
        outcome: EventOutcome | None = None,
        from_at: datetime | None = None,
        to_at: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> CaseActivityPage:
        scope = self._resolve_scope(actor, team_filter)
        if case_id is not None:
            self._access_policy.require_case_access(actor, case_id, self._cases)
        try:
            query = CaseActivityQuery(
                scope=scope,
                case_id=case_id,
                action=action,
                stage=stage,
                outcome=outcome,
                from_at=from_at,
                to_at=to_at,
                limit=limit,
                offset=offset,
            )
        except ValidationError:
            raise CaseActivityQueryInvalidError from None
        repository_page = self._portfolio_repository.list_activity(query)
        team_labels = {item.team_id: item.client_scope_label for item in self._teams.list()}
        return CaseActivityPage(
            items=tuple(
                CaseActivityItem(
                    case_id=item.case_id,
                    sequence=item.sequence,
                    timestamp=item.timestamp,
                    event_type=item.event_type,
                    status=item.status,
                    stage=item.stage,
                    outcome=item.outcome,
                    code=item.code,
                    message=item.message,
                    current_priority=item.current_priority,
                    current_client_scope_label=(
                        team_labels.get(item.team_id) if item.team_id is not None else None
                    ),
                )
                for item in repository_page.items
            ),
            offset=repository_page.offset,
            limit=repository_page.limit,
            has_more=repository_page.has_more,
        )

    def _resolve_scope(
        self, actor: AuthenticatedActor, team_filter: str | None
    ) -> CasePortfolioScope:
        if actor.profile.role != Role.DIRECTOR and team_filter is not None:
            raise CaseTeamFilterForbiddenError
        if actor.profile.role != Role.DIRECTOR or team_filter in {None, "all"}:
            return self._access_policy.portfolio_scope(actor)
        if team_filter == "unassigned":
            return CasePortfolioScope(kind=PortfolioScopeKind.UNASSIGNED)
        try:
            selected_team = TeamId(str(team_filter))
        except ValueError:
            raise CaseTeamFilterInvalidError from None
        if self._teams.get(selected_team) is None:
            raise CaseTeamFilterInvalidError
        return CasePortfolioScope(kind=PortfolioScopeKind.TEAM, team_id=selected_team)

    def update_priority(
        self,
        actor: AuthenticatedActor,
        case_id: UUID,
        priority: CasePriority | None,
    ) -> OnboardingCase:
        with self._cases.case_lock(case_id):
            case = self._access_policy.require_case_access(actor, case_id, self._cases)
            now = self._clock()
            updated = case.model_copy(deep=True)
            updated.priority = priority
            updated.updated_at = now
            updated.events.append(
                WorkflowEvent(
                    sequence=len(updated.events) + 1,
                    stage=updated.state,
                    outcome=EventOutcome.SUCCEEDED,
                    timestamp=now,
                    case_id=updated.case_id,
                    correlation_id=updated.correlation_id,
                    code="CASE_PRIORITY_UPDATED",
                    message=(
                        "Case priority was cleared."
                        if priority is None
                        else "Case priority was updated."
                    ),
                )
            )
            self._case_repository.save(updated)
            return updated.model_copy(deep=True)


def _matches_priority(priority: CasePriority | None, expected: PriorityFilter) -> bool:
    if expected == PriorityFilter.ALL:
        return True
    if expected == PriorityFilter.PRIORITISED:
        return priority is not None
    if expected == PriorityFilter.UNSET:
        return priority is None
    return priority == int(expected)
