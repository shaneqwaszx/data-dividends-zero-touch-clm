"""Typed historical dashboard read model over canonical CLM case data."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.access import CasePriority, Role, TeamId
from app.domain.jurisdiction import JurisdictionCode
from app.domain.zero_touch import AutomationStage, AutomationStatus, BusinessExceptionType


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
    current_stage: AutomationStage
    progress_percent: int = Field(ge=0, le=100)
    final_outcome: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    case_elapsed_ms: int = Field(ge=0)
    delay_note: str | None = None
    created_by_display_name: str | None = None


class DashboardTimingSummary(BaseModel):
    """Recorded workflow-start-to-completion duration, split by exception interventions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mean_total_duration_ms: int | None = Field(default=None, ge=0)
    zero_touch_mean_duration_ms: int | None = Field(default=None, ge=0)
    zero_touch_count: int = Field(ge=0)
    blocked_mean_duration_ms: int | None = Field(default=None, ge=0)
    blocked_count: int = Field(ge=0)


class DashboardStageCaseTiming(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: UUID
    requested_uen: str
    legal_name: str | None
    duration_ms: int = Field(ge=0)
    had_blocker: bool


class DashboardStageTiming(BaseModel):
    """Recorded processing-attempt durations; excludes blocker-resolution and waiting time."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: AutomationStage
    clean_mean_ms: int | None = Field(default=None, ge=0)
    clean_count: int = Field(ge=0)
    with_blocker_mean_ms: int | None = Field(default=None, ge=0)
    with_blocker_count: int = Field(ge=0)
    combined_mean_ms: int | None = Field(default=None, ge=0)
    blocked_count: int = Field(ge=0)
    top_cases: tuple[DashboardStageCaseTiming, ...] = Field(default_factory=tuple, max_length=3)


class DashboardExceptionCount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    exception_type: BusinessExceptionType
    count: int = Field(ge=0)


class DashboardWeeklyOnboarded(BaseModel):
    """Completed-case counts for one UTC week-of-Monday bucket, by resolved jurisdiction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    week_start: date
    by_jurisdiction: dict[JurisdictionCode, int] = Field(default_factory=dict)
    unresolved_count: int = Field(default=0, ge=0)


class DashboardWorkloadRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: str
    display_name: str
    open_cases: int = Field(ge=0)
    oldest_open_age_ms: int | None = Field(default=None, ge=0)
    completed_cases: int = Field(ge=0)
    blockers_resolved: int = Field(ge=0)
    mean_fix_time_ms: int | None = Field(default=None, ge=0)


class DashboardTrendDay(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    day: date
    created_count: int = Field(ge=0)
    completed_count: int = Field(ge=0)


class DashboardSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scope: DashboardScope
    view: Literal["team", "mine"]
    data_as_of: datetime
    totals: DashboardTotals
    historical_trend: tuple[DashboardTrendDay, ...]
    zero_touch_rate: float = Field(ge=0.0, le=1.0)
    timing: DashboardTimingSummary
    status_breakdown: tuple[DashboardStatusCount, ...]
    priority_breakdown: tuple[DashboardPriorityCount, ...]
    team_breakdown: tuple[DashboardTeamCount, ...]
    stage_timing: tuple[DashboardStageTiming, ...]
    exception_breakdown: tuple[DashboardExceptionCount, ...]
    weekly_onboarded: tuple[DashboardWeeklyOnboarded, ...]
    workload_by_person: tuple[DashboardWorkloadRow, ...]
    recent_cases: tuple[DashboardCaseItem, ...]
    top_active_cases: tuple[DashboardCaseItem, ...]
    scoped_cases: tuple[DashboardCaseItem, ...]
