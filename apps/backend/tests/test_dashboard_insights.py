"""D-127 provisional SLA/attention rules and the Dashboard management figures built on them."""

from __future__ import annotations

from datetime import timedelta

import pytest
from test_phase13_dashboard import (
    NOW,
    _actor,
    _open_exception,
    _record,
    _resolved_exception,
    _service_for,
)

from app.domain.access import TeamId
from app.domain.case_management import CaseTimingDataInvalidError
from app.domain.dashboard_attention import (
    AT_RISK_WINDOW_MS,
    SLA_TARGET_MS,
    AttentionLevel,
    AttentionReason,
    SlaStatus,
    attention,
    sla_status,
)
from app.domain.jurisdiction import (
    JurisdictionObservation,
    JurisdictionObservationSource,
    JurisdictionResolver,
)
from app.domain.zero_touch import AutomationStage, AutomationStatus, BusinessExceptionType

DAY_MS = 86_400_000


@pytest.mark.parametrize(
    ("status", "elapsed", "expected"),
    [
        (AutomationStatus.RUNNING, 0, SlaStatus.ON_TRACK),
        (AutomationStatus.RUNNING, SLA_TARGET_MS - AT_RISK_WINDOW_MS - 1, SlaStatus.ON_TRACK),
        (AutomationStatus.RUNNING, SLA_TARGET_MS - AT_RISK_WINDOW_MS, SlaStatus.AT_RISK),
        (AutomationStatus.RUNNING, SLA_TARGET_MS, SlaStatus.AT_RISK),
        (AutomationStatus.RUNNING, SLA_TARGET_MS + 1, SlaStatus.OVERDUE),
        (AutomationStatus.COMPLETED, SLA_TARGET_MS, SlaStatus.MET),
        (AutomationStatus.COMPLETED, SLA_TARGET_MS + 1, SlaStatus.MISSED),
    ],
)
def test_sla_status_boundaries(status, elapsed, expected) -> None:
    assert SLA_TARGET_MS == 10 * DAY_MS
    assert sla_status(status, elapsed) == expected


def test_attention_levels_list_every_reason_and_skip_completed_cases() -> None:
    quiet = timedelta(hours=1)
    assert attention(
        AutomationStatus.COMPLETED, SlaStatus.MISSED,
        oldest_open_blocker_age_ms=None, since_update=timedelta(days=30),
    ) == (None, ())
    assert attention(
        AutomationStatus.RUNNING, SlaStatus.ON_TRACK,
        oldest_open_blocker_age_ms=None, since_update=quiet,
    ) == (AttentionLevel.LOW, ())
    assert attention(
        AutomationStatus.PENDING_INPUTS, SlaStatus.ON_TRACK,
        oldest_open_blocker_age_ms=None, since_update=quiet,
    ) == (AttentionLevel.MEDIUM, (AttentionReason.AWAITING_INPUTS,))
    assert attention(
        AutomationStatus.RUNNING, SlaStatus.ON_TRACK,
        oldest_open_blocker_age_ms=None, since_update=timedelta(days=5),
    ) == (AttentionLevel.LOW, ())
    assert attention(
        AutomationStatus.RUNNING, SlaStatus.ON_TRACK,
        oldest_open_blocker_age_ms=None, since_update=timedelta(days=5, milliseconds=1),
    ) == (AttentionLevel.HIGH, (AttentionReason.NO_UPDATE_5_DAYS,))
    assert attention(
        AutomationStatus.WAITING_FOR_REVIEW, SlaStatus.AT_RISK,
        oldest_open_blocker_age_ms=7 * DAY_MS + 1, since_update=quiet,
    ) == (AttentionLevel.HIGH, (
        AttentionReason.BLOCKER_OPEN_OVER_7_DAYS,
        AttentionReason.SLA_AT_RISK,
        AttentionReason.AWAITING_REVIEW,
    ))
    assert attention(
        AutomationStatus.WAITING_FOR_REVIEW, SlaStatus.ON_TRACK,
        oldest_open_blocker_age_ms=7 * DAY_MS, since_update=quiet,
    ) == (AttentionLevel.MEDIUM, (AttentionReason.AWAITING_REVIEW,))


def _cohort():
    clean, clean_auto = _record(
        TeamId.TEAM_A, None, AutomationStatus.COMPLETED, created_days_ago=2, updated_hours_ago=1,
        created_by_actor_id="maya-lim",
        stage_durations_ms={AutomationStage.REGISTRY: 1_000, AutomationStage.DOCUMENT: 3_000},
    )
    slow, slow_auto = _record(
        TeamId.TEAM_A, None, AutomationStatus.COMPLETED, created_days_ago=12, updated_hours_ago=1,
        created_by_actor_id="maya-lim", human_interventions=1,
        stage_durations_ms={AutomationStage.DOCUMENT: 8_000},
    )
    slow_auto = slow_auto.model_copy(update={"exceptions": [
        _resolved_exception(
            slow.case_id, BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE, AutomationStage.DOCUMENT,
            created_at=slow.created_at + timedelta(hours=1),
            resolved_at=slow.created_at + timedelta(hours=3), actor_id="maya-lim",
        ),
        _resolved_exception(
            slow.case_id, BusinessExceptionType.DOCUMENT_REQUIRED_FIELD_MISSING,
            AutomationStage.DOCUMENT, created_at=slow.created_at + timedelta(hours=4),
            resolved_at=slow.created_at + timedelta(hours=5), actor_id="maya-lim",
        ),
    ]})
    overdue, overdue_auto = _record(
        TeamId.TEAM_A, None, AutomationStatus.RUNNING, created_days_ago=11, updated_hours_ago=1,
        created_by_actor_id="maya-lim",
    )
    waiting, waiting_auto = _record(
        TeamId.TEAM_A, None, AutomationStatus.WAITING_FOR_REVIEW,
        created_days_ago=9, updated_hours_ago=1, created_by_actor_id="maya-lim",
    )
    waiting_auto = waiting_auto.model_copy(update={"exceptions": [_open_exception(
        waiting.case_id, BusinessExceptionType.OWNERSHIP_INCOMPLETE, AutomationStage.OWNERSHIP,
        created_at=NOW - timedelta(days=8),
    )]})
    inputs, inputs_auto = _record(
        TeamId.TEAM_A, None, AutomationStatus.PENDING_INPUTS, created_days_ago=1,
        updated_hours_ago=1, created_by_actor_id="maya-lim",
    )
    idle, idle_auto = _record(
        TeamId.TEAM_A, None, AutomationStatus.RUNNING, created_days_ago=6, updated_hours_ago=144,
        created_by_actor_id="maya-lim",
    )
    fresh, fresh_auto = _record(
        TeamId.TEAM_A, None, AutomationStatus.RUNNING, created_days_ago=1, updated_hours_ago=1,
        created_by_actor_id="maya-lim",
    )
    cases = {
        "clean": (clean, clean_auto), "slow": (slow, slow_auto), "overdue": (overdue, overdue_auto),
        "waiting": (waiting, waiting_auto), "inputs": (inputs, inputs_auto),
        "idle": (idle, idle_auto), "fresh": (fresh, fresh_auto),
    }
    return cases


def test_kpis_case_facts_workload_and_rework_follow_d127() -> None:
    cases = _cohort()
    service, _ = _service_for(list(cases.values()))

    result = service.get_dashboard(_actor("maya-lim"), date_range="all")

    assert result.attention_policy.decision == "D-127"
    assert result.attention_policy.classification == "PROJECT_DEFINED_PROVISIONAL"
    assert result.attention_policy.sla_target_ms == SLA_TARGET_MS
    clean_e2e = 47 * 3_600_000
    slow_e2e = (12 * 24 - 1) * 3_600_000
    assert result.kpis.model_dump() == {
        "open_cases": 5,
        "running_cases": 4,
        "blocked_cases": 1,
        "awaiting_review_cases": 1,
        "completed_cases": 2,
        "zero_touch_rate": 0.5,
        "mean_processing_ms": 6_000,
        "mean_end_to_end_ms": (clean_e2e + slow_e2e) // 2,
        "sla_met_cases": 1,
        "sla_compliance_rate": 0.5,
        "overdue_cases": 1,
        "at_risk_cases": 1,
        "high_attention_cases": 3,
    }
    assert result.previous_period is None

    items = {item.case_id: item for item in result.scoped_cases}
    def item(name):
        return items[cases[name][0].case_id]
    assert (item("clean").sla_status, item("clean").attention_level) == (SlaStatus.MET, None)
    assert item("slow").sla_status == SlaStatus.MISSED
    assert (item("overdue").sla_status, item("overdue").attention_level) == (
        SlaStatus.OVERDUE, AttentionLevel.HIGH,
    )
    waiting = item("waiting")
    assert waiting.sla_status == SlaStatus.AT_RISK
    assert waiting.attention_reasons == (
        AttentionReason.BLOCKER_OPEN_OVER_7_DAYS,
        AttentionReason.SLA_AT_RISK,
        AttentionReason.AWAITING_REVIEW,
    )
    assert waiting.oldest_open_blocker_age_ms == 8 * DAY_MS
    assert waiting.sla_due_at == cases["waiting"][0].created_at + timedelta(days=10)
    assert waiting.open_exception_types == (BusinessExceptionType.OWNERSHIP_INCOMPLETE,)
    assert item("inputs").attention_reasons == (AttentionReason.AWAITING_INPUTS,)
    assert item("inputs").attention_level == AttentionLevel.MEDIUM
    assert item("idle").attention_reasons == (AttentionReason.NO_UPDATE_5_DAYS,)
    assert (item("fresh").attention_level, item("fresh").oldest_open_blocker_age_ms) == (
        AttentionLevel.LOW, None,
    )

    maya = next(row for row in result.workload_by_person if row.user_id == "maya-lim")
    assert (maya.running_cases, maya.blocked_cases, maya.overdue_cases) == (4, 1, 1)
    assert maya.high_attention_cases == 3
    assert result.rework.model_dump() == {
        "total_cases": 7, "cases_with_blockers": 2, "rework_cases": 1,
    }
    this_week = result.weekly_onboarded[-1]
    assert this_week.mean_end_to_end_ms == (clean_e2e + slow_e2e) // 2
    document = next(row for row in result.stage_timing if row.stage == AutomationStage.DOCUMENT)
    assert document.processing_total_ms == 11_000
    assert document.resolution_total_ms == 3 * 3_600_000


def test_previous_period_uses_the_equal_window_before_the_range_and_respects_mine() -> None:
    current, current_auto = _record(
        TeamId.TEAM_A, None, AutomationStatus.COMPLETED, created_days_ago=2, updated_hours_ago=1,
        created_by_actor_id="maya-lim",
    )
    earlier, earlier_auto = _record(
        TeamId.TEAM_A, None, AutomationStatus.COMPLETED, created_days_ago=10,
        updated_hours_ago=216, created_by_actor_id="maya-lim", human_interventions=1,
        stage_durations_ms={AutomationStage.REGISTRY: 2_000},
    )
    teammate, teammate_auto = _record(
        TeamId.TEAM_A, None, AutomationStatus.RUNNING, created_days_ago=9, updated_hours_ago=1,
        created_by_actor_id="sophia-ng",
    )
    too_old, too_old_auto = _record(
        TeamId.TEAM_A, None, AutomationStatus.COMPLETED, created_days_ago=20,
        updated_hours_ago=400, created_by_actor_id="maya-lim",
    )
    service, _ = _service_for([
        (current, current_auto), (earlier, earlier_auto),
        (teammate, teammate_auto), (too_old, too_old_auto),
    ])

    team = service.get_dashboard(_actor("maya-lim"), date_range="7d")
    assert team.totals.total_cases == 1
    previous = team.previous_period
    assert previous is not None
    assert (str(previous.created_from), str(previous.created_to)) == ("2026-08-26", "2026-09-01")
    assert (previous.total_cases, previous.completed_cases) == (2, 1)
    assert previous.zero_touch_rate == 0.0
    assert previous.mean_processing_ms == 2_000
    assert previous.mean_end_to_end_ms == DAY_MS
    assert previous.sla_compliance_rate == 1.0

    mine = service.get_dashboard(_actor("maya-lim"), scope="mine", date_range="7d")
    assert mine.previous_period is not None
    assert mine.previous_period.total_cases == 1


def test_exceptions_report_country_and_weekly_counts() -> None:
    case, automation = _record(
        TeamId.TEAM_A, None, AutomationStatus.WAITING_FOR_REVIEW,
        created_days_ago=1, updated_hours_ago=1,
    )
    resolution = JurisdictionResolver().resolve([JurisdictionObservation(
        jurisdiction="SG", source=JurisdictionObservationSource.USER_INPUT,
        observed_at=case.created_at,
    )], resolved_at=case.created_at)
    case = case.model_copy(update={"jurisdiction_resolution": resolution})
    automation = automation.model_copy(update={"exceptions": [_open_exception(
        case.case_id, BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE, AutomationStage.DOCUMENT,
        created_at=NOW - timedelta(hours=2),
    )]})
    unresolved, unresolved_auto = _record(
        TeamId.TEAM_A, None, AutomationStatus.WAITING_FOR_REVIEW,
        created_days_ago=20, updated_hours_ago=1,
    )
    unresolved_auto = unresolved_auto.model_copy(update={"exceptions": [_open_exception(
        unresolved.case_id, BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
        AutomationStage.DOCUMENT, created_at=NOW - timedelta(days=15),
    )]})
    service, _ = _service_for([(case, automation), (unresolved, unresolved_auto)])

    result = service.get_dashboard(_actor("maya-lim"), date_range="all")

    row = result.exception_breakdown[0]
    assert row.by_jurisdiction == {"SG": 1}
    assert row.unresolved_jurisdiction_count == 1
    assert row.weekly_counts == (0, 0, 0, 0, 0, 1, 0, 1)
    sg_case = next(item for item in result.scoped_cases if item.case_id == case.case_id)
    assert sg_case.jurisdiction == "SG"


def test_open_blocker_newer_than_the_observation_fails_closed() -> None:
    case, automation = _record(
        TeamId.TEAM_A, None, AutomationStatus.WAITING_FOR_REVIEW,
        created_days_ago=1, updated_hours_ago=1,
    )
    automation = automation.model_copy(update={"exceptions": [_open_exception(
        case.case_id, BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE, AutomationStage.DOCUMENT,
        created_at=NOW + timedelta(minutes=5),
    )]})
    service, _ = _service_for([(case, automation)])

    with pytest.raises(CaseTimingDataInvalidError):
        service.get_dashboard(_actor("maya-lim"), date_range="all")


def test_team_rows_report_sla_attention_end_to_end_and_fix_time() -> None:
    cases = _cohort()
    beta, beta_auto = _record(
        TeamId.TEAM_B, None, AutomationStatus.COMPLETED, created_days_ago=3, updated_hours_ago=3,
        created_by_actor_id="ryan-lee",
    )
    service, _ = _service_for([*cases.values(), (beta, beta_auto)])

    result = service.get_dashboard(_actor("olivia-koh"), date_range="all")
    teams = {row.team_id: row for row in result.team_breakdown}

    alpha = teams[TeamId.TEAM_A]
    clean_e2e = 47 * 3_600_000
    slow_e2e = (12 * 24 - 1) * 3_600_000
    assert (alpha.sla_met_count, alpha.overdue_count, alpha.high_attention_count) == (1, 1, 3)
    assert alpha.mean_end_to_end_ms == (clean_e2e + slow_e2e) // 2
    # Two resolved DOCUMENT blockers (2h and 1h); the open ownership blocker is not a fix.
    assert (alpha.resolved_blockers, alpha.mean_fix_ms) == (2, 5_400_000)
    beta_row = teams[TeamId.TEAM_B]
    assert (beta_row.count, beta_row.sla_met_count, beta_row.overdue_count) == (1, 1, 0)
    assert beta_row.mean_end_to_end_ms == 69 * 3_600_000
    assert (beta_row.resolved_blockers, beta_row.mean_fix_ms) == (0, None)

    team_a_member = service.get_dashboard(_actor("maya-lim"), date_range="all")
    assert [row.team_id for row in team_a_member.team_breakdown] == [TeamId.TEAM_A]
