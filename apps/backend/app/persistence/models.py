"""Explicit schema-versioned representation for one durable CLM case."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.access import CasePriority, TeamId
from app.domain.clm import ClmOrchestrationRecord
from app.domain.documents import DocumentProcessingRecord
from app.domain.jurisdiction import JurisdictionResolution, RegistryRoutingDecision
from app.domain.models import (
    CanonicalLegalEntity,
    GoldTierResult,
    OnboardingCase,
    RegistryAcquisitionBundle,
    SafeError,
    WorkflowEvent,
    WorkflowState,
)
from app.domain.ownership import OwnershipAnalysisRecord
from app.domain.policy import CasePolicySnapshot, legacy_phase13_policy_snapshot
from app.domain.reconciliation import ReconciliationCaseRecord
from app.domain.target_submission import GoldTierExecutionLedgerEntry
from app.domain.zero_touch import ZeroTouchAutomationRecord

CASE_SNAPSHOT_SCHEMA_VERSION: Literal[4] = 4


class LegacyOnboardingCaseV1(BaseModel):
    """Exact pre-Phase 13 onboarding shape used only for strict schema-v1 reads."""

    model_config = ConfigDict(extra="forbid")

    case_id: UUID
    source_case_id: str
    correlation_id: UUID
    requested_uen: str
    jurisdiction_resolution: JurisdictionResolution | None = None
    registry_route: RegistryRoutingDecision | None = None
    state: WorkflowState
    entity: CanonicalLegalEntity | None = None
    registry_acquisition: RegistryAcquisitionBundle | None = None
    goldtier_result: GoldTierResult | None = None
    events: list[WorkflowEvent] = Field(default_factory=list)
    error: SafeError | None = None
    created_at: datetime
    updated_at: datetime

    def to_current(self) -> OnboardingCase:
        return OnboardingCase.model_validate(
            {
                **self.model_dump(),
                "team_id": None,
                "priority": None,
                "policy_snapshot": legacy_phase13_policy_snapshot(self.created_at),
                "registry_evidence_binding": None,
            }
        )


class DurableCaseSnapshotV1(BaseModel):
    """Strict Phase 12 envelope accepted read-only and migrated only in memory."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    case_id: UUID
    revision: int = Field(ge=0)
    onboarding: LegacyOnboardingCaseV1
    documents: tuple[DocumentProcessingRecord, ...] = Field(default=(), max_length=40)
    ownership: OwnershipAnalysisRecord | None = None
    reconciliation: ReconciliationCaseRecord | None = None
    clm: ClmOrchestrationRecord | None = None
    automation: ZeroTouchAutomationRecord | None = None
    target_executions: tuple[GoldTierExecutionLedgerEntry, ...] = Field(default=(), max_length=4)
    demo_scenario: str | None = Field(default=None, min_length=1, max_length=64)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_case_bindings(self) -> "DurableCaseSnapshotV1":
        _validate_case_bindings(self)
        return self

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot(
            schema_version=4,
            case_id=self.case_id,
            revision=self.revision,
            onboarding=self.onboarding.to_current(),
            documents=self.documents,
            ownership=self.ownership,
            reconciliation=self.reconciliation,
            clm=self.clm,
            automation=self.automation,
            target_executions=self.target_executions,
            demo_scenario=self.demo_scenario,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class LegacyOnboardingCaseV2(LegacyOnboardingCaseV1):
    """Exact Phase 13 onboarding shape used only for strict schema-v2 reads."""

    team_id: TeamId | None = None
    priority: CasePriority | None = None

    def to_current(self) -> OnboardingCase:
        return OnboardingCase.model_validate(
            {
                **self.model_dump(),
                "policy_snapshot": legacy_phase13_policy_snapshot(self.created_at),
                "registry_evidence_binding": None,
            }
        )


class DurableCaseSnapshotV2(BaseModel):
    """Strict Phase 13 envelope accepted read-only and migrated only in memory."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[2] = 2
    case_id: UUID
    revision: int = Field(ge=0)
    onboarding: LegacyOnboardingCaseV2
    documents: tuple[DocumentProcessingRecord, ...] = Field(default=(), max_length=40)
    ownership: OwnershipAnalysisRecord | None = None
    reconciliation: ReconciliationCaseRecord | None = None
    clm: ClmOrchestrationRecord | None = None
    automation: ZeroTouchAutomationRecord | None = None
    target_executions: tuple[GoldTierExecutionLedgerEntry, ...] = Field(default=(), max_length=4)
    demo_scenario: str | None = Field(default=None, min_length=1, max_length=64)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_case_bindings(self) -> "DurableCaseSnapshotV2":
        _validate_case_bindings(self)
        return self

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot(
            schema_version=4,
            case_id=self.case_id,
            revision=self.revision,
            onboarding=self.onboarding.to_current(),
            documents=self.documents,
            ownership=self.ownership,
            reconciliation=self.reconciliation,
            clm=self.clm,
            automation=self.automation,
            target_executions=self.target_executions,
            demo_scenario=self.demo_scenario,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class LegacyOnboardingCaseV3(LegacyOnboardingCaseV2):
    """Exact Phase 14.5 onboarding shape used only for strict schema-v3 reads."""

    policy_snapshot: CasePolicySnapshot

    def to_current(self) -> OnboardingCase:
        return OnboardingCase.model_validate(
            {
                **self.model_dump(),
                "registry_evidence_binding": None,
            }
        )


class DurableCaseSnapshotV3(BaseModel):
    """Strict pre-Phase-16 envelope accepted without version-only rewrite."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[3] = 3
    case_id: UUID
    revision: int = Field(ge=0)
    onboarding: LegacyOnboardingCaseV3
    documents: tuple[DocumentProcessingRecord, ...] = Field(default=(), max_length=40)
    ownership: OwnershipAnalysisRecord | None = None
    reconciliation: ReconciliationCaseRecord | None = None
    clm: ClmOrchestrationRecord | None = None
    automation: ZeroTouchAutomationRecord | None = None
    target_executions: tuple[GoldTierExecutionLedgerEntry, ...] = Field(default=(), max_length=4)
    demo_scenario: str | None = Field(default=None, min_length=1, max_length=64)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_case_bindings(self) -> "DurableCaseSnapshotV3":
        _validate_case_bindings(self)
        return self

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot(
            schema_version=4,
            case_id=self.case_id,
            revision=self.revision,
            onboarding=self.onboarding.to_current(),
            documents=self.documents,
            ownership=self.ownership,
            reconciliation=self.reconciliation,
            clm=self.clm,
            automation=self.automation,
            target_executions=self.target_executions,
            demo_scenario=self.demo_scenario,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class DurableCaseSnapshot(BaseModel):
    """Bounded authoritative structured state; never raw source/upload payloads."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[4] = 4
    case_id: UUID
    revision: int = Field(ge=0)
    onboarding: OnboardingCase
    documents: tuple[DocumentProcessingRecord, ...] = Field(default=(), max_length=40)
    ownership: OwnershipAnalysisRecord | None = None
    reconciliation: ReconciliationCaseRecord | None = None
    clm: ClmOrchestrationRecord | None = None
    automation: ZeroTouchAutomationRecord | None = None
    target_executions: tuple[GoldTierExecutionLedgerEntry, ...] = Field(default=(), max_length=4)
    demo_scenario: str | None = Field(default=None, min_length=1, max_length=64)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_case_bindings(self) -> "DurableCaseSnapshot":
        _validate_case_bindings(self)
        return self


def _validate_case_bindings(snapshot: Any) -> None:
    if snapshot.onboarding.case_id != snapshot.case_id:
        raise ValueError("onboarding case does not match envelope")
    records: tuple[Any, ...] = (
        *snapshot.documents,
        *(
            item
            for item in (
                snapshot.ownership,
                snapshot.reconciliation,
                snapshot.clm,
                snapshot.automation,
            )
            if item is not None
        ),
    )
    if any(item.case_id != snapshot.case_id for item in records):
        raise ValueError("nested record does not match envelope")
    if any(
        item.submission_input.case_id != snapshot.case_id for item in snapshot.target_executions
    ):
        raise ValueError("target execution does not match envelope")
    submission_ids = [item.submission_input.submission_id for item in snapshot.target_executions]
    if len(set(submission_ids)) != len(submission_ids):
        raise ValueError("duplicate target execution identity")
