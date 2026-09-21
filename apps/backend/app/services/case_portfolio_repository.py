"""Repository boundary for lightweight authorized case portfolio reads."""

from typing import Protocol

from app.domain.case_management import (
    CaseActivityQuery,
    CaseActivityRepositoryPage,
    CaseActivityRepositoryRecord,
    CasePortfolioPage,
    CasePortfolioQuery,
    CasePortfolioRecord,
    CasePortfolioScope,
    PortfolioScopeKind,
    activity_matches_action,
    case_portfolio_matches,
    order_case_activity_records,
    order_case_portfolio_records,
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

    def list_activity(self, query: CaseActivityQuery) -> CaseActivityRepositoryPage: ...

    def list_page(self, query: CasePortfolioQuery) -> CasePortfolioPage: ...


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
            if case is None or not _case_in_scope(case.team_id, scope):
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

    def list_activity(self, query: CaseActivityQuery) -> CaseActivityRepositoryPage:
        records: list[CaseActivityRepositoryRecord] = []
        for automation in self._automation.list_records():
            if query.case_id is not None and automation.case_id != query.case_id:
                continue
            case = self._cases.get(automation.case_id)
            if case is None or not _case_in_scope(case.team_id, query.scope):
                continue
            scoped_events: list[CaseActivityRepositoryRecord] = []
            for expected_sequence, event in enumerate(automation.events, start=1):
                if event.sequence != expected_sequence or event.case_id != case.case_id:
                    raise ValueError("retained automation event identity is invalid")
                record = CaseActivityRepositoryRecord(
                    case_id=case.case_id,
                    sequence=event.sequence,
                    timestamp=event.timestamp,
                    event_type=event.event_type,
                    status=event.status,
                    stage=event.stage,
                    outcome=event.outcome,
                    code=event.code,
                    message=event.message,
                    team_id=case.team_id,
                    current_priority=case.priority,
                )
                scoped_events.append(record)
            records.extend(item for item in scoped_events if _matches_activity(item, query))
        ordered = order_case_activity_records(records)
        lookahead = ordered[query.offset : query.offset + query.limit + 1]
        return CaseActivityRepositoryPage(
            items=tuple(lookahead[: query.limit]),
            offset=query.offset,
            limit=query.limit,
            has_more=len(lookahead) > query.limit,
        )

    def list_page(self, query: CasePortfolioQuery) -> CasePortfolioPage:
        records: list[CasePortfolioRecord] = []
        for automation in self._automation.list_records():
            case = self._cases.get(automation.case_id)
            if case is None or not _case_in_scope(case.team_id, query.scope):
                continue
            record = CasePortfolioRecord(
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
                    [(item.status, item.exception_type) for item in automation.exceptions]
                ),
                human_interventions=automation.metrics.human_interventions,
                final_outcome=automation.metrics.final_outcome,
                mock_goldtier_party_id=(
                    case.goldtier_result.party_id if case.goldtier_result is not None else None
                ),
            )
            if case_portfolio_matches(record, query):
                records.append(record)
        ordered = order_case_portfolio_records(records, query.priority_sort)
        lookahead = ordered[query.offset : query.offset + query.limit + 1]
        return CasePortfolioPage(
            items=tuple(lookahead[: query.limit]),
            offset=query.offset,
            limit=query.limit,
            has_more=len(lookahead) > query.limit,
        )


def _case_in_scope(team_id: object, scope: CasePortfolioScope) -> bool:
    if scope.kind == PortfolioScopeKind.GLOBAL:
        return True
    if scope.kind == PortfolioScopeKind.UNASSIGNED:
        return team_id is None
    return team_id == scope.team_id


def _matches_activity(record: CaseActivityRepositoryRecord, query: CaseActivityQuery) -> bool:
    return (
        (query.action is None or activity_matches_action(record, query.action))
        and (query.stage is None or record.stage == query.stage)
        and (query.outcome is None or record.outcome == query.outcome)
        and (query.from_at is None or record.timestamp >= query.from_at)
        and (query.to_at is None or record.timestamp < query.to_at)
    )
