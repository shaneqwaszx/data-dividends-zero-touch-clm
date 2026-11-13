"""Provisional Dashboard SLA and attention rules (D-127, PROJECT_DEFINED_PROVISIONAL).

Display and ordering aids only: nothing here changes workflow state, readiness, priority,
routing, approval or GoldTier behaviour, and none of it is a compliance or staff measure.
"""

from datetime import timedelta
from enum import StrEnum

from app.domain.zero_touch import AutomationStatus

SLA_TARGET_MS = 10 * 24 * 3_600_000
AT_RISK_WINDOW_MS = 2 * 24 * 3_600_000
STALE_BLOCKER_MS = 7 * 24 * 3_600_000
INACTIVITY_MS = 5 * 24 * 3_600_000
SLA_RULES_DECISION = "D-127"


class SlaStatus(StrEnum):
    ON_TRACK = "ON_TRACK"
    AT_RISK = "AT_RISK"
    OVERDUE = "OVERDUE"
    MET = "MET"
    MISSED = "MISSED"


class AttentionLevel(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AttentionReason(StrEnum):
    OVERDUE = "OVERDUE"
    BLOCKER_OPEN_OVER_7_DAYS = "BLOCKER_OPEN_OVER_7_DAYS"
    NO_UPDATE_5_DAYS = "NO_UPDATE_5_DAYS"
    SLA_AT_RISK = "SLA_AT_RISK"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    AWAITING_RECOVERY = "AWAITING_RECOVERY"
    AWAITING_INPUTS = "AWAITING_INPUTS"
    TECHNICAL_FAILURE = "TECHNICAL_FAILURE"


_HIGH_REASONS = frozenset({
    AttentionReason.OVERDUE,
    AttentionReason.BLOCKER_OPEN_OVER_7_DAYS,
    AttentionReason.NO_UPDATE_5_DAYS,
})
_WAITING_REASONS = {
    AutomationStatus.WAITING_FOR_REVIEW: AttentionReason.AWAITING_REVIEW,
    AutomationStatus.RECOVERY_PENDING: AttentionReason.AWAITING_RECOVERY,
    AutomationStatus.PENDING_INPUTS: AttentionReason.AWAITING_INPUTS,
    AutomationStatus.TECHNICAL_FAILURE: AttentionReason.TECHNICAL_FAILURE,
}


def sla_status(status: AutomationStatus, case_elapsed_ms: int) -> SlaStatus:
    """S2: completed cases are MET/MISSED; open cases are ON_TRACK/AT_RISK/OVERDUE."""

    if status == AutomationStatus.COMPLETED:
        return SlaStatus.MET if case_elapsed_ms <= SLA_TARGET_MS else SlaStatus.MISSED
    if case_elapsed_ms > SLA_TARGET_MS:
        return SlaStatus.OVERDUE
    if case_elapsed_ms >= SLA_TARGET_MS - AT_RISK_WINDOW_MS:
        return SlaStatus.AT_RISK
    return SlaStatus.ON_TRACK


def attention(
    status: AutomationStatus,
    sla: SlaStatus,
    *,
    oldest_open_blocker_age_ms: int | None,
    since_update: timedelta,
) -> tuple[AttentionLevel | None, tuple[AttentionReason, ...]]:
    """S3: the level and every reason that produced it; completed cases have no level."""

    if status == AutomationStatus.COMPLETED:
        return None, ()
    reasons: list[AttentionReason] = []
    if sla == SlaStatus.OVERDUE:
        reasons.append(AttentionReason.OVERDUE)
    if oldest_open_blocker_age_ms is not None and oldest_open_blocker_age_ms > STALE_BLOCKER_MS:
        reasons.append(AttentionReason.BLOCKER_OPEN_OVER_7_DAYS)
    if since_update > timedelta(milliseconds=INACTIVITY_MS):
        reasons.append(AttentionReason.NO_UPDATE_5_DAYS)
    if sla == SlaStatus.AT_RISK:
        reasons.append(AttentionReason.SLA_AT_RISK)
    if status in _WAITING_REASONS:
        reasons.append(_WAITING_REASONS[status])
    if any(reason in _HIGH_REASONS for reason in reasons):
        return AttentionLevel.HIGH, tuple(reasons)
    if reasons:
        return AttentionLevel.MEDIUM, tuple(reasons)
    return AttentionLevel.LOW, ()
