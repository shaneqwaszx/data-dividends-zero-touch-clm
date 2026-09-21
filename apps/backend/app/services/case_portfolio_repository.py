"""Repository boundary for lightweight authorized case portfolio reads."""

from typing import Protocol

from app.domain.case_management import (
    CasePortfolioRecord,
    CasePortfolioScope,
    ordered_active_exception_types,
)
from app.domain.zero_touch import AutomationStatus
from app.services.repository import OnboardingCaseRepository
from app.services.zero_touch_repository import ZeroTouchAutomationRepository


class CasePortfolioRepository(Protocol):
    def list_authorized(
        self,
        scope: CasePortfolioScope,
        *,
        status: AutomationStatus | None = None,
    ) -> list[CasePortfolioRecord]: ...


class InMemoryCasePortfolioRepository:
    """Build strict summaries from process-local canonical owners."""

    def __init__(
        self,
        cases: OnboardingCaseRepository,
        automation: ZeroTouchAutomationRepository,
    ) -> None:
        self._cases = cases
        self._automation = automation

    def list_authorized(
        self,
        scope: CasePortfolioScope,
        *,
        status: AutomationStatus | None = None,
    ) -> list[CasePortfolioRecord]:
        records: list[CasePortfolioRecord] = []
        for automation in self._automation.list_records():
            if status is not None and automation.status != status:
                continue
            case = self._cases.get(automation.case_id)
            if case is None or (scope.team_id is not None and case.team_id != scope.team_id):
                continue
            records.append(
                CasePortfolioRecord(
                    case_id=case.case_id,
                    requested_uen=case.requested_uen,
                    legal_name=(case.entity.legal_name if case.entity is not None else None),
                    resolved_jurisdiction=(
                        case.jurisdiction_resolution.resolved_jurisdiction
                        if case.jurisdiction_resolution is not None
                        else None
                    ),
                    team_id=case.team_id,
                    priority=case.priority,
                    status=automation.status,
                    current_stage=automation.current_stage,
                    created_at=automation.created_at,
                    updated_at=automation.updated_at,
                    completed_at=automation.completed_at,
                    active_exception_count=len(automation.active_exceptions),
                    active_exception_types=ordered_active_exception_types(
                        [
                            (item.status, item.exception_type)
                            for item in automation.exceptions
                        ]
                    ),
                    human_interventions=automation.metrics.human_interventions,
                    final_outcome=automation.metrics.final_outcome,
                    mock_goldtier_party_id=(
                        case.goldtier_result.party_id if case.goldtier_result is not None else None
                    ),
                )
            )
        return records
