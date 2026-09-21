"""Strict lightweight case-management portfolio contracts."""

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
