"""Typed historical dashboard read model over canonical CLM case data."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.access import CasePriority, Role, TeamId
from app.domain.zero_touch import AutomationStatus


class DashboardScope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    actor_role: Role
    access: Literal["TEAM", "GLOBAL"]
    team_id: TeamId | None
    team_display_name: str | None
    client_scope_label: str


class DashboardTotals(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    total_cases: int = Field(ge=0)
    completed_cases: int = Field(ge=0)
    non_completed_cases: int = Field(ge=0)
    completion_rate: float = Field(ge=0.0, le=1.0)
    prioritised_cases: int = Field(ge=0)
    unprioritised_cases: int = Field(ge=0)


class DashboardStatusCount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: AutomationStatus
    count: int = Field(ge=0)


class DashboardPriorityCount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    priority: CasePriority | None
    count: int = Field(ge=0)


class DashboardTeamCount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    team_id: TeamId
    team_display_name: str
    client_scope_label: str
    count: int = Field(ge=0)


class DashboardCaseItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: UUID
    requested_uen: str
    legal_name: str | None
    team_id: TeamId | None
    team_display_name: str | None
    priority: CasePriority | None
    status: AutomationStatus
    final_outcome: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class DashboardTrendDay(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    day: date
    created_count: int = Field(ge=0)
    completed_count: int = Field(ge=0)


class DashboardSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scope: DashboardScope
    data_as_of: datetime
    totals: DashboardTotals
    status_breakdown: tuple[DashboardStatusCount, ...]
    priority_breakdown: tuple[DashboardPriorityCount, ...]
    team_breakdown: tuple[DashboardTeamCount, ...]
    recent_cases: tuple[DashboardCaseItem, ...]
    top_active_cases: tuple[DashboardCaseItem, ...]
    historical_trend: tuple[DashboardTrendDay, ...]
