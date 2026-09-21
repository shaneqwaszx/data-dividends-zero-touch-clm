"""Strict lightweight case-management portfolio contracts."""

from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.access import CasePriority, TeamId
from app.domain.jurisdiction import JurisdictionCode
from app.domain.zero_touch import (
    AutomationStage,
    AutomationStatus,
    BusinessExceptionStatus,
    BusinessExceptionType,
)


class PortfolioScopeKind(StrEnum):
    GLOBAL = "GLOBAL"
    TEAM = "TEAM"


class CasePortfolioScope(BaseModel):
    """Server-authored visibility scope accepted by portfolio repositories."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: PortfolioScopeKind
    team_id: TeamId | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> "CasePortfolioScope":
        if (self.kind == PortfolioScopeKind.GLOBAL) != (self.team_id is None):
            raise ValueError("portfolio scope kind and team must agree")
        return self


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
