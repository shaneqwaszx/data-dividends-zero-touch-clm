"""Typed historical dashboard read model over canonical CLM case data."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.access import CasePriority, Role, TeamId
from app.domain.dashboard_attention import AttentionLevel, AttentionReason, SlaStatus
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
    """Selected-cohort counts for one team; additive fields default for compatibility."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    team_id: TeamId
    team_display_name: str
    client_scope_label: str
    count: int = Field(ge=0)
    status_breakdown: tuple[DashboardStatusCount, ...] = Field(default_factory=tuple)
    zero_touch_count: int = Field(default=0, ge=0)
    sla_met_count: int = Field(default=0, ge=0)
    overdue_count: int = Field(default=0, ge=0)
    high_attention_count: int = Field(default=0, ge=0)
    mean_end_to_end_ms: int | None = Field(default=None, ge=0)
    resolved_blockers: int = Field(default=0, ge=0)
    mean_fix_ms: int | None = Field(default=None, ge=0)


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
    jurisdiction: JurisdictionCode | None = None
    sla_status: SlaStatus | None = None
    sla_due_at: datetime | None = None
    attention_level: AttentionLevel | None = None
    attention_reasons: tuple[AttentionReason, ...] = Field(default_factory=tuple)
    open_exception_types: tuple[BusinessExceptionType, ...] = Field(default_factory=tuple)
    oldest_open_blocker_age_ms: int | None = Field(default=None, ge=0)


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
    """Recorded processing-attempt durations; excludes blocker-resolution and waiting time.

    ``reached_count`` counts cases with a recorded duration or a retained blocker at the step.
    ``resolution_*`` reports elapsed blocker creation-to-resolution time for RESOLVED
    blockers raised at the step, separately from processing time; it is not working time.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: AutomationStage
    clean_mean_ms: int | None = Field(default=None, ge=0)
    clean_count: int = Field(ge=0)
    with_blocker_mean_ms: int | None = Field(default=None, ge=0)
    with_blocker_count: int = Field(ge=0)
    combined_mean_ms: int | None = Field(default=None, ge=0)
    blocked_count: int = Field(ge=0)
    top_cases: tuple[DashboardStageCaseTiming, ...] = Field(default_factory=tuple, max_length=3)
    reached_count: int = Field(default=0, ge=0)
    resolution_mean_ms: int | None = Field(default=None, ge=0)
    resolution_count: int = Field(default=0, ge=0)
    processing_total_ms: int = Field(default=0, ge=0)
    resolution_total_ms: int = Field(default=0, ge=0)
    open_blocked_count: int = Field(default=0, ge=0)


class DashboardExceptionCount(BaseModel):
    """Retained blockers of one type; fix times are elapsed creation-to-resolution time."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    exception_type: BusinessExceptionType
    count: int = Field(ge=0)
    open_count: int = Field(default=0, ge=0)
    resolved_count: int = Field(default=0, ge=0)
    mean_fix_ms: int | None = Field(default=None, ge=0)
    total_fix_ms: int = Field(default=0, ge=0)
    by_jurisdiction: dict[JurisdictionCode, int] = Field(default_factory=dict)
    unresolved_jurisdiction_count: int = Field(default=0, ge=0)
    weekly_counts: tuple[int, ...] = Field(default_factory=tuple, max_length=8)


class DashboardWeeklyOnboarded(BaseModel):
    """Completed-case counts for one UTC week-of-Monday bucket, by resolved jurisdiction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    week_start: date
    by_jurisdiction: dict[JurisdictionCode, int] = Field(default_factory=dict)
    unresolved_count: int = Field(default=0, ge=0)
    zero_touch_count: int = Field(default=0, ge=0)
    mean_end_to_end_ms: int | None = Field(default=None, ge=0)


class DashboardWorkloadRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: str
    display_name: str
    open_cases: int = Field(ge=0)
    oldest_open_age_ms: int | None = Field(default=None, ge=0)
    completed_cases: int = Field(ge=0)
    blockers_resolved: int = Field(ge=0)
    mean_fix_time_ms: int | None = Field(default=None, ge=0)
    running_cases: int = Field(default=0, ge=0)
    blocked_cases: int = Field(default=0, ge=0)
    overdue_cases: int = Field(default=0, ge=0)
    high_attention_cases: int = Field(default=0, ge=0)


class DashboardTrendDay(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    day: date
    created_count: int = Field(ge=0)
    completed_count: int = Field(ge=0)


class DashboardAttentionPolicy(BaseModel):
    """The provisional D-127 rules the SLA and attention fields were calculated with."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: str
    classification: Literal["PROJECT_DEFINED_PROVISIONAL"] = "PROJECT_DEFINED_PROVISIONAL"
    sla_target_ms: int = Field(ge=0)
    at_risk_window_ms: int = Field(ge=0)
    stale_blocker_ms: int = Field(ge=0)
    inactivity_ms: int = Field(ge=0)


class DashboardKpis(BaseModel):
    """Selected-cohort management figures; rates and means are null without a denominator."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    open_cases: int = Field(ge=0)
    running_cases: int = Field(ge=0)
    blocked_cases: int = Field(ge=0)
    awaiting_review_cases: int = Field(ge=0)
    completed_cases: int = Field(ge=0)
    zero_touch_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    mean_processing_ms: int | None = Field(default=None, ge=0)
    mean_end_to_end_ms: int | None = Field(default=None, ge=0)
    sla_met_cases: int = Field(ge=0)
    sla_compliance_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    overdue_cases: int = Field(ge=0)
    at_risk_cases: int = Field(ge=0)
    high_attention_cases: int = Field(ge=0)


class DashboardPeriodComparison(BaseModel):
    """Completion figures for the equally long window before the selected one."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    created_from: date
    created_to: date
    total_cases: int = Field(ge=0)
    completed_cases: int = Field(ge=0)
    zero_touch_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    mean_processing_ms: int | None = Field(default=None, ge=0)
    mean_end_to_end_ms: int | None = Field(default=None, ge=0)
    sla_compliance_rate: float | None = Field(default=None, ge=0.0, le=1.0)


class DashboardRework(BaseModel):
    """D-127 S4: cases with two or more retained blockers at the same pipeline step."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    total_cases: int = Field(ge=0)
    cases_with_blockers: int = Field(ge=0)
    rework_cases: int = Field(ge=0)


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
    attention_policy: DashboardAttentionPolicy
    kpis: DashboardKpis
    previous_period: DashboardPeriodComparison | None = None
    rework: DashboardRework
