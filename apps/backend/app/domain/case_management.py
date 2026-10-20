"""Strict lightweight case-management portfolio contracts."""

import re
from datetime import UTC, date, datetime, time, timedelta, timezone
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

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
    INTELLIGENCE = "INTELLIGENCE"
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
    created_by: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9-]{2,31}$")
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
    started_at: datetime | None = None
    completed_at: datetime | None = None
    recorded_total_duration_ms: StrictInt | None = Field(default=None, ge=0)
    active_exception_count: int = Field(ge=0)
    active_exception_types: tuple[BusinessExceptionType, ...] = Field(
        max_length=len(BusinessExceptionType)
    )
    human_interventions: int = Field(ge=0)
    final_outcome: str | None = Field(default=None, max_length=64)
    mock_goldtier_party_id: str | None = Field(default=None, min_length=1, max_length=96)
    created_by_actor_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9-]{2,31}$")

    @model_validator(mode="after")
    def validate_timestamps(self) -> "CasePortfolioRecord":
        for value in (self.created_at, self.updated_at, self.started_at, self.completed_at):
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


class CaseTimingProjection(BaseModel):
    """Factual durations calculated from one server-authored UTC observation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_elapsed_ms: StrictInt = Field(ge=0)
    time_since_last_update_ms: StrictInt = Field(ge=0)
    automation_elapsed_ms: StrictInt | None = Field(default=None, ge=0)
    recorded_total_duration_ms: StrictInt | None = Field(default=None, ge=0)


class CaseTimingDataInvalidError(ValueError):
    """Retained timing facts cannot produce a truthful non-negative projection."""


def project_case_timing(
    *,
    created_at: datetime,
    updated_at: datetime,
    started_at: datetime | None,
    completed_at: datetime | None,
    recorded_total_duration_ms: int | None,
    observed_at: datetime,
) -> CaseTimingProjection:
    """Project factual elapsed milliseconds without inference or clamping."""

    timestamps = (created_at, updated_at, started_at, completed_at, observed_at)
    if any(
        value is not None
        and (value.tzinfo is None or value.utcoffset() != timedelta(0))
        for value in timestamps
    ):
        raise CaseTimingDataInvalidError("case timing timestamps must be timezone-aware UTC")
    if recorded_total_duration_ms is not None and (
        type(recorded_total_duration_ms) is not int or recorded_total_duration_ms < 0
    ):
        raise CaseTimingDataInvalidError("recorded total duration is invalid")
    if updated_at < created_at:
        raise CaseTimingDataInvalidError("case update cannot precede case creation")
    if started_at is not None and started_at < created_at:
        raise CaseTimingDataInvalidError("automation start cannot precede case creation")
    if completed_at is not None and completed_at > observed_at:
        raise CaseTimingDataInvalidError("case completion cannot follow the observation")

    case_end = completed_at or observed_at
    automation_end = completed_at or observed_at
    deltas = (
        case_end - created_at,
        observed_at - updated_at,
        automation_end - started_at if started_at is not None else None,
    )
    if any(delta is not None and delta < timedelta(0) for delta in deltas):
        raise CaseTimingDataInvalidError("retained case timing chronology is invalid")

    return CaseTimingProjection(
        case_elapsed_ms=_timedelta_milliseconds(deltas[0]),
        time_since_last_update_ms=_timedelta_milliseconds(deltas[1]),
        automation_elapsed_ms=(
            _timedelta_milliseconds(deltas[2]) if deltas[2] is not None else None
        ),
        recorded_total_duration_ms=recorded_total_duration_ms,
    )


def _timedelta_milliseconds(value: timedelta) -> int:
    return value.days * 86_400_000 + value.seconds * 1_000 + value.microseconds // 1_000


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
    created_from_at: datetime | None = None
    created_to_at: datetime | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10_000)

    @field_validator("search", mode="before")
    @classmethod
    def normalize_search(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("created_from_at", "created_to_at")
    @classmethod
    def normalize_created_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created timestamps must include an explicit timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_created_window(self) -> "CasePortfolioQuery":
        if (
            self.created_from_at is not None
            and self.created_to_at is not None
            and self.created_from_at >= self.created_to_at
        ):
            raise ValueError("created from timestamp must be earlier than to timestamp")
        return self


def case_created_date_bounds(
    created_from: date | None,
    created_to: date | None,
) -> tuple[datetime | None, datetime | None]:
    """Convert inclusive Singapore calendar dates to a half-open UTC window.

    The POC uses Singapore's UTC+08:00 calendar-day convention. This explicit
    offset keeps Windows and Linux behavior identical without system tzdata.
    """

    if created_from is not None and created_to is not None and created_from > created_to:
        raise ValueError("created from date must not follow created to date")
    singapore = timezone(timedelta(hours=8), name="Asia/Singapore")
    try:
        start = (
            datetime.combine(created_from, time.min, singapore).astimezone(UTC)
            if created_from is not None
            else None
        )
        end = (
            datetime.combine(created_to + timedelta(days=1), time.min, singapore).astimezone(UTC)
            if created_to is not None
            else None
        )
    except (OverflowError, ValueError):
        raise ValueError("created date range is not representable") from None
    return start, end


class CasePortfolioPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: tuple[CasePortfolioRecord, ...]
    offset: int = Field(ge=0, le=10_000)
    limit: int = Field(ge=1, le=100)
    has_more: bool


class ObservedCasePortfolioRecord(CasePortfolioRecord):
    """Portfolio record enriched by the query service at response observation time."""

    timing: CaseTimingProjection


class ObservedCasePortfolioPage(BaseModel):
    """One response observation shared by every timing projection in the page."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observed_at: datetime
    items: tuple[ObservedCasePortfolioRecord, ...]
    offset: int = Field(ge=0, le=10_000)
    limit: int = Field(ge=1, le=100)
    has_more: bool

    @field_validator("observed_at")
    @classmethod
    def require_observed_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("portfolio observation must be timezone-aware UTC")
        return value


def case_portfolio_matches(record: CasePortfolioRecord, query: CasePortfolioQuery) -> bool:
    """Apply the composed non-scope portfolio predicates."""

    if query.status is not None and record.status != query.status:
        return False
    if query.created_from_at is not None and record.created_at < query.created_from_at:
        return False
    if query.created_to_at is not None and record.created_at >= query.created_to_at:
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
    if action == CaseActivityAction.INTELLIGENCE:
        return record.event_type == AutomationEventType.INTELLIGENCE_EVALUATED
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
