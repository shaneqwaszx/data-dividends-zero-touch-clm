"""Authorized case portfolio query and atomic priority mutation owner."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.domain.access import AuthenticatedActor, CasePriority
from app.domain.models import EventOutcome, OnboardingCase, WorkflowEvent
from app.domain.zero_touch import AutomationStatus, ZeroTouchAutomationRecord
from app.services.authorization import CaseAccessPolicy
from app.services.onboarding import OnboardingService
from app.services.repository import OnboardingCaseRepository
from app.services.zero_touch_repository import ZeroTouchAutomationRepository


@dataclass(frozen=True)
class AuthorizedCaseRecord:
    automation: ZeroTouchAutomationRecord
    case: OnboardingCase


class CaseQueryService:
    """Join canonical cases to automation, filter access, and own final ordering."""

    def __init__(
        self,
        *,
        cases: OnboardingService,
        case_repository: OnboardingCaseRepository,
        automation_repository: ZeroTouchAutomationRepository,
        access_policy: CaseAccessPolicy,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._cases = cases
        self._case_repository = case_repository
        self._automation_repository = automation_repository
        self._access_policy = access_policy
        self._clock = clock or (lambda: datetime.now(UTC))

    def list_cases(
        self,
        actor: AuthenticatedActor,
        *,
        status: AutomationStatus | None = None,
    ) -> list[AuthorizedCaseRecord]:
        result: list[AuthorizedCaseRecord] = []
        for automation in self._automation_repository.list_records():
            if status is not None and automation.status != status:
                continue
            case = self._cases.get_case(automation.case_id)
            if case is not None and self._access_policy.can_access(actor, case):
                result.append(AuthorizedCaseRecord(automation=automation, case=case))
        return sorted(result, key=_portfolio_sort_key, reverse=True)

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


def _portfolio_sort_key(item: AuthorizedCaseRecord) -> tuple[bool, int, datetime, str]:
    priority = item.case.priority
    return (
        priority is not None,
        priority if priority is not None else 0,
        item.automation.updated_at,
        str(item.automation.case_id),
    )
