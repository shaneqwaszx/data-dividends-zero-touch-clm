"""Strict lightweight case-management portfolio contracts."""

import re
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.access import CasePriority, TeamId
from app.domain.jurisdiction import JurisdictionCode
from app.domain.models import EventOutcome
from app.domain.zero_touch import (
    AutomationEventType,
    AutomationStage,
    AutomationStatus,
    BusinessExceptionStatus,
    BusinessExceptionType,
)


class PortfolioScopeKind(StrEnum):
    GLOBAL = "GLOBAL"
    TEAM = "TEAM"
    UNASSIGNED = "UNASSIGNED"


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


class CasePortfolioScope(BaseModel):
    """Server-authored visibility scope accepted by portfolio repositories."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: PortfolioScopeKind
    team_id: TeamId | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> "CasePortfolioScope":
        if (self.kind == PortfolioScopeKind.TEAM) != (self.team_id is not None):
            raise ValueError("portfolio scope kind and team must agree")
        return self


class CaseActivityAction(StrEnum):
    """Existing Audit Trail presentation buckets; values may overlap."""

    CREATED = "CREATED"
    DOCUMENT = "DOCUMENT"
    RECONCILIATION = "RECONCILIATION"
    OWNERSHIP = "OWNERSHIP"
    TARGET = "TARGET"
    COMPLETED = "COMPLETED"


class CaseActivityQuery(BaseModel):
    """Typed server-owned repository query with a bounded live offset window."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    scope: CasePortfolioScope
    case_id: UUID | None = None
    action: CaseActivityAction | None = None
    stage: AutomationStage | None = None
    outcome: EventOutcome | None = None
    from_at: datetime | None = None
    to_at: datetime | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10_000)

    @field_validator("from_at", "to_at")
    @classmethod
    def normalize_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("activity timestamps must include an explicit timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_window(self) -> "CaseActivityQuery":
        if self.from_at is not None and self.to_at is not None and self.from_at >= self.to_at:
            raise ValueError("activity from timestamp must be earlier than to timestamp")
        return self


class CaseActivityRepositoryRecord(BaseModel):
    """Strict retained-event projection before current team-label resolution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: UUID
    sequence: int = Field(ge=1)
    timestamp: datetime
    event_type: AutomationEventType
    status: AutomationStatus
    stage: AutomationStage
    outcome: EventOutcome
    code: str | None = Field(default=None, max_length=64)
    message: str = Field(min_length=1, max_length=200)
    team_id: TeamId | None = None
    current_priority: CasePriority | None = None

    @field_validator("timestamp")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("activity timestamp must be timezone-aware UTC")
        return value


class CaseActivityItem(BaseModel):
    """Minimized authorized browser item with explicitly current case metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: UUID
    sequence: int = Field(ge=1)
    timestamp: datetime
    event_type: AutomationEventType
    status: AutomationStatus
    stage: AutomationStage
    outcome: EventOutcome
    code: str | None = Field(default=None, max_length=64)
    message: str = Field(min_length=1, max_length=200)
    current_priority: CasePriority | None = None
    current_client_scope_label: str | None = Field(default=None, max_length=80)


class CaseActivityRepositoryPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: tuple[CaseActivityRepositoryRecord, ...]
    offset: int = Field(ge=0, le=10_000)
    limit: int = Field(ge=1, le=100)
    has_more: bool


class CaseActivityPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: tuple[CaseActivityItem, ...]
    offset: int = Field(ge=0, le=10_000)
    limit: int = Field(ge=1, le=100)
    has_more: bool


class CasePortfolioRecord(BaseModel):
    """Bounded scalar projection used by lists and Dashboard."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: UUID
    requested_uen: str = Field(min_length=1, max_length=32)
    legal_name: str | None = Field(default=None, max_length=512)
    resolved_jurisdiction: JurisdictionCode | None = None
    team_id: TeamId | None = None
    priority: CasePriority | None = None
    status: AutomationStatus
    current_stage: AutomationStage
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    active_exception_count: int = Field(ge=0)
    active_exception_types: tuple[BusinessExceptionType, ...] = Field(
        max_length=len(BusinessExceptionType)
    )
    human_interventions: int = Field(ge=0)
    final_outcome: str | None = Field(default=None, max_length=64)
    mock_goldtier_party_id: str | None = Field(default=None, min_length=1, max_length=96)

    @model_validator(mode="after")
    def validate_timestamps(self) -> "CasePortfolioRecord":
        for value in (self.created_at, self.updated_at, self.completed_at):
            if value is not None and (value.tzinfo is None or value.utcoffset() != timedelta(0)):
                raise ValueError("portfolio timestamps must be timezone-aware UTC")
        canonical_types = tuple(
            exception_type
            for exception_type in BusinessExceptionType
            if exception_type in self.active_exception_types
        )
        if self.active_exception_types != canonical_types:
            raise ValueError("active exception types must be unique and in canonical order")
        return self


class CasePortfolioQuery(BaseModel):
    """Typed server-owned bounded portfolio page query."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    scope: CasePortfolioScope
    status: AutomationStatus | None = None
    priority_filter: PriorityFilter = PriorityFilter.ALL
    priority_sort: PrioritySort = PrioritySort.HIGHEST_FIRST
    attention_type: BusinessExceptionType | None = None
    jurisdiction: JurisdictionCode | None = None
    search: str | None = Field(default=None, max_length=128)
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10_000)

    @field_validator("search", mode="before")
    @classmethod
    def normalize_search(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None


class CasePortfolioPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: tuple[CasePortfolioRecord, ...]
    offset: int = Field(ge=0, le=10_000)
    limit: int = Field(ge=1, le=100)
    has_more: bool


def case_portfolio_matches(record: CasePortfolioRecord, query: CasePortfolioQuery) -> bool:
    """Apply the composed non-scope portfolio predicates."""

    if query.status is not None and record.status != query.status:
        return False
    if query.priority_filter == PriorityFilter.PRIORITISED and record.priority is None:
        return False
    if query.priority_filter == PriorityFilter.UNSET and record.priority is not None:
        return False
    if query.priority_filter not in {
        PriorityFilter.ALL,
        PriorityFilter.PRIORITISED,
        PriorityFilter.UNSET,
    } and record.priority != int(query.priority_filter):
        return False
    if (
        query.attention_type is not None
        and query.attention_type not in record.active_exception_types
    ):
        return False
    if query.jurisdiction is not None and record.resolved_jurisdiction != query.jurisdiction:
        return False
    if query.search is not None:
        pattern = case_portfolio_search_pattern(query.search)
        searchable = (record.requested_uen, record.legal_name, str(record.case_id))
        if not any(
            value is not None and re.search(pattern, value) is not None
            for value in searchable
        ):
            return False
    return True


def case_portfolio_search_pattern(search: str) -> str:
    """Return one engine-independent ASCII-case-insensitive literal pattern.

    ASCII letters become explicit two-code-point character classes. Every other
    code point is escaped literally, so Python and Mongo do not delegate semantics to
    different Unicode case-folding implementations.
    """

    parts: list[str] = []
    for character in search:
        if "a" <= character <= "z":
            parts.append(f"[{character}{character.upper()}]")
        elif "A" <= character <= "Z":
            parts.append(f"[{character.lower()}{character}]")
        else:
            parts.append(re.escape(character))
    return "".join(parts)


def order_case_portfolio_records(
    records: list[CasePortfolioRecord],
    priority_sort: PrioritySort,
) -> list[CasePortfolioRecord]:
    """Preserve priority-first ordering with deterministic recency/UUID ties."""

    tie_ordered = sorted(
        records,
        key=lambda item: (item.updated_at, str(item.case_id)),
        reverse=True,
    )
    prioritised = [item for item in tie_ordered if item.priority is not None]
    unset = [item for item in tie_ordered if item.priority is None]
    prioritised.sort(
        key=lambda item: int(item.priority or 0),
        reverse=priority_sort == PrioritySort.HIGHEST_FIRST,
    )
    return prioritised + unset


def ordered_active_exception_types(
    exceptions: list[tuple[BusinessExceptionStatus, BusinessExceptionType]],
) -> tuple[BusinessExceptionType, ...]:
    """Return unique OPEN exception types in canonical enum declaration order."""

    open_types = {
        exception_type
        for exception_status, exception_type in exceptions
        if exception_status == BusinessExceptionStatus.OPEN
    }
    return tuple(
        exception_type
        for exception_type in BusinessExceptionType
        if exception_type in open_types
    )


def activity_matches_action(
    record: CaseActivityRepositoryRecord, action: CaseActivityAction
) -> bool:
    """Preserve the existing overlapping Audit Trail presentation semantics."""

    event_type = record.event_type.value
    if action == CaseActivityAction.CREATED:
        return "CREATED" in event_type
    if action == CaseActivityAction.DOCUMENT:
        return record.stage == AutomationStage.DOCUMENT
    if action == CaseActivityAction.RECONCILIATION:
        return "RECONCILIATION" in event_type
    if action == CaseActivityAction.OWNERSHIP:
        return record.stage == AutomationStage.OWNERSHIP
    if action == CaseActivityAction.TARGET:
        return (
            record.stage == AutomationStage.MOCK_GOLDTIER
            or "MOCK_SUBMISSION" in event_type
        )
    return "COMPLETED" in event_type or record.stage == AutomationStage.COMPLETE


def order_case_activity_records(
    records: list[CaseActivityRepositoryRecord],
) -> list[CaseActivityRepositoryRecord]:
    """Apply timestamp-desc, case-UUID-asc, sequence-desc with stable sorts."""

    ordered = list(records)
    ordered.sort(key=lambda item: item.sequence, reverse=True)
    ordered.sort(key=lambda item: str(item.case_id))
    ordered.sort(key=lambda item: item.timestamp, reverse=True)
    return ordered
