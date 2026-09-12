"""Authorized case portfolio query and atomic priority mutation owner."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from app.domain.access import AuthenticatedActor, CasePriority
from app.domain.case_management import CasePortfolioRecord
from app.domain.models import EventOutcome, OnboardingCase, WorkflowEvent
from app.domain.zero_touch import AutomationStatus
from app.services.authorization import CaseAccessPolicy
from app.services.case_portfolio_repository import (
    CasePortfolioRepository,
    InMemoryCasePortfolioRepository,
)
from app.services.onboarding import OnboardingService
from app.services.repository import OnboardingCaseRepository
from app.services.zero_touch_repository import ZeroTouchAutomationRepository


class PriorityFilter(StrEnum):
    ALL = "all"
    PRIORITISED = "prioritised"
    UNSET = "unset"
    P10 = "10"
    P9 = "9"
    P8 = "8"
    P7 = "7"
    P6 = "6"
    P5 = "5"
    P4 = "4"
    P3 = "3"
    P2 = "2"
    P1 = "1"


class PrioritySort(StrEnum):
    HIGHEST_FIRST = "highest_first"
    LOWEST_FIRST = "lowest_first"


class CaseQueryService:
    """Join canonical cases to automation, filter access, and own final ordering."""

    def __init__(
        self,
        *,
        cases: OnboardingService,
        case_repository: OnboardingCaseRepository,
        automation_repository: ZeroTouchAutomationRepository,
        access_policy: CaseAccessPolicy,
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
        self._clock = clock or (lambda: datetime.now(UTC))

    def list_cases(
        self,
        actor: AuthenticatedActor,
        *,
        status: AutomationStatus | None = None,
        priority_filter: PriorityFilter = PriorityFilter.ALL,
        priority_sort: PrioritySort = PrioritySort.HIGHEST_FIRST,
    ) -> list[CasePortfolioRecord]:
        authorized = self._portfolio_repository.list_authorized(
            self._access_policy.portfolio_scope(actor), status=status
        )
        filtered = [
            item for item in authorized if _matches_priority(item.priority, priority_filter)
        ]
        tie_ordered = sorted(filtered, key=_portfolio_tie_key, reverse=True)
        prioritised = [item for item in tie_ordered if item.priority is not None]
        unset = [item for item in tie_ordered if item.priority is None]
        prioritised.sort(
            key=lambda item: int(item.priority or 0),
            reverse=priority_sort == PrioritySort.HIGHEST_FIRST,
        )
        return prioritised + unset

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


def _portfolio_tie_key(item: CasePortfolioRecord) -> tuple[datetime, str]:
    return item.updated_at, str(item.case_id)
