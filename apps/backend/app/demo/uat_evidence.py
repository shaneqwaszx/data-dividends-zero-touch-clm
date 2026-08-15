"""Whitelisted, synthetic-only Phase 07 UAT evidence projection."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.demo.scenarios import SimulationProfile
from app.demo.zero_touch_control import ZeroTouchDemoScenario
from app.domain.clm import ClmOrchestrationRecord
from app.domain.zero_touch import (
    AutomationStage,
    AutomationStatus,
    ZeroTouchAutomationRecord,
)


class UatEvidenceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_type: str
    stage: AutomationStage
    status: AutomationStatus
    outcome: str
    timestamp: datetime
    code: str | None
    message: str


class UatEvidenceExport(BaseModel):
    """Submission-safe UAT evidence with no raw provider or document content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_schema: Literal["PHASE_07_UAT_EVIDENCE_V1"] = "PHASE_07_UAT_EVIDENCE_V1"
    uat_case_id: str = Field(pattern=r"^(UAT-[0-9]{2}|SUPPORTING-[A-Z-]+)$")
    scenario: ZeroTouchDemoScenario
    case_id: UUID
    synthetic_uen: str
    final_state: AutomationStatus
    current_stage: AutomationStage
    completed_stages: tuple[AutomationStage, ...]
    active_blockers: tuple[str, ...]
    human_interventions: int
    exceptions_raised: int
    exceptions_resolved: int
    stage_durations_ms: dict[AutomationStage, int]
    total_duration_ms: int | None
    target_calls: tuple[str, ...]
    target_outcome: str | None
    warnings: tuple[str, ...]
    environment: SimulationProfile
    timeline: tuple[UatEvidenceEvent, ...]
    exported_at: datetime


_UAT_CASE_BY_SCENARIO = {
    ZeroTouchDemoScenario.STRAIGHT_THROUGH: "UAT-01",
    ZeroTouchDemoScenario.DOCUMENT_DISCREPANCY: "UAT-02",
    ZeroTouchDemoScenario.LOW_CONFIDENCE: "UAT-03",
    ZeroTouchDemoScenario.LOW_CONFIDENCE_DOCUMENT: "UAT-03",
    ZeroTouchDemoScenario.MULTIPLE_DOCUMENT_BLOCKERS: "UAT-04",
    ZeroTouchDemoScenario.OWNERSHIP_CYCLE: "UAT-05",
    ZeroTouchDemoScenario.OWNERSHIP_EXCEPTION: "UAT-05",
    ZeroTouchDemoScenario.OWNERSHIP_INCOMPLETE: "UAT-06",
    ZeroTouchDemoScenario.MULTIPLE_OWNERSHIP_PATHS: "UAT-07",
    ZeroTouchDemoScenario.EXISTING_PARTY: "UAT-08",
    ZeroTouchDemoScenario.TARGET_FAILURE: "UAT-09",
    ZeroTouchDemoScenario.PARTIAL_AMEND: "UAT-10",
    ZeroTouchDemoScenario.RECOVERY: "UAT-11",
    ZeroTouchDemoScenario.TECHNICAL_FAILURE: "SUPPORTING-IDP-FAILURE",
}


def build_uat_evidence(
    *,
    automation: ZeroTouchAutomationRecord,
    clm: ClmOrchestrationRecord,
    scenario: ZeroTouchDemoScenario,
    synthetic_uen: str,
    simulation: SimulationProfile,
    target_calls: tuple[str, ...],
    exported_at: datetime,
) -> UatEvidenceExport:
    return UatEvidenceExport(
        uat_case_id=_UAT_CASE_BY_SCENARIO[scenario],
        scenario=scenario,
        case_id=automation.case_id,
        synthetic_uen=synthetic_uen,
        final_state=automation.status,
        current_stage=automation.current_stage,
        completed_stages=automation.completed_stages,
        active_blockers=tuple(
            blocker
            for exception in automation.active_exceptions
            for blocker in exception.blocker_codes
        ),
        human_interventions=automation.metrics.human_interventions,
        exceptions_raised=automation.metrics.exceptions_raised,
        exceptions_resolved=automation.metrics.exceptions_resolved,
        stage_durations_ms=dict(automation.metrics.stage_durations_ms),
        total_duration_ms=automation.metrics.total_duration_ms,
        target_calls=target_calls,
        target_outcome=automation.metrics.final_outcome,
        warnings=tuple(warning.value for warning in clm.readiness.warnings),
        environment=simulation,
        timeline=tuple(
            UatEvidenceEvent(
                event_type=event.event_type.value,
                stage=event.stage,
                status=event.status,
                outcome=event.outcome.value,
                timestamp=event.timestamp,
                code=event.code,
                message=event.message,
            )
            for event in automation.events
        ),
        exported_at=exported_at,
    )
