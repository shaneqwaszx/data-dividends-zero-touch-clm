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
    ExistingTargetStateProvenance,
    GoldTierResult,
    InitialCustomerIdentity,
    InitialGoldTierSearchEvidence,
    OnboardingCase,
    RegistryAcquisitionBundle,
    RegistryEvidenceBinding,
    SafeError,
    WorkflowEvent,
    WorkflowState,
)
from app.domain.onboarding_intelligence import OnboardingIntelligenceRecord
from app.domain.ownership import OwnershipAnalysisRecord
from app.domain.policy import CasePolicySnapshot, legacy_phase13_policy_snapshot
from app.domain.reconciliation import ReconciliationCaseRecord
from app.domain.target_submission import GoldTierExecutionLedgerEntry
from app.domain.zero_touch import ZeroTouchAutomationRecord

CASE_SNAPSHOT_SCHEMA_VERSION: Literal[8] = 8


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
            schema_version=8,
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
            schema_version=8,
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
            schema_version=8,
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


class DurableCaseSnapshotV4(BaseModel):
    """Strict pre-intelligence envelope accepted without a read-time rewrite."""

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
    def validate_case_bindings(self) -> "DurableCaseSnapshotV4":
        _validate_case_bindings(self)
        if self.onboarding.policy_snapshot.intelligence is not None:
            raise ValueError("schema-v4 policy snapshot cannot contain intelligence policy")
        return self

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot(
            schema_version=8,
            case_id=self.case_id,
            revision=self.revision,
            onboarding=self.onboarding,
            documents=self.documents,
            ownership=self.ownership,
            reconciliation=self.reconciliation,
            clm=self.clm,
            automation=self.automation,
            target_executions=self.target_executions,
            demo_scenario=self.demo_scenario,
            intelligence=None,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class DurableCaseSnapshotV5(BaseModel):
    """Strict pre-GoldTier-first envelope accepted and migrated in memory."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[5] = 5
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
    intelligence: OnboardingIntelligenceRecord | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_case_bindings(self) -> "DurableCaseSnapshotV5":
        _validate_case_bindings(self)
        return self

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot(
            schema_version=8,
            case_id=self.case_id,
            revision=self.revision,
            onboarding=self.onboarding,
            documents=self.documents,
            ownership=self.ownership,
            reconciliation=self.reconciliation,
            clm=self.clm,
            automation=self.automation,
            target_executions=self.target_executions,
            demo_scenario=self.demo_scenario,
            intelligence=self.intelligence,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class LegacyOnboardingCaseV6(BaseModel):
    """Exact schema-v6 onboarding shape before recovery and confirmation fields."""

    model_config = ConfigDict(extra="forbid")

    case_id: UUID
    source_case_id: str
    correlation_id: UUID
    requested_uen: str
    initial_identity: InitialCustomerIdentity | None = None
    initial_target_search: InitialGoldTierSearchEvidence | None = None
    existing_target_state: ExistingTargetStateProvenance | None = None
    policy_snapshot: CasePolicySnapshot
    team_id: TeamId | None = None
    priority: CasePriority | None = None
    jurisdiction_resolution: JurisdictionResolution | None = None
    registry_route: RegistryRoutingDecision | None = None
    state: WorkflowState
    entity: CanonicalLegalEntity | None = None
    registry_acquisition: RegistryAcquisitionBundle | None = None
    registry_evidence_binding: RegistryEvidenceBinding | None = None
    goldtier_result: GoldTierResult | None = None
    events: list[WorkflowEvent] = Field(default_factory=list)
    error: SafeError | None = None
    created_at: datetime
    updated_at: datetime

    def to_current(self) -> OnboardingCase:
        return OnboardingCase.model_validate(
            {
                **self.model_dump(),
                "identity_corrections": (),
                "initial_target_search_attempts": (),
                "target_dispatch_confirmation": None,
            }
        )


class DurableCaseSnapshotV6(BaseModel):
    """Strict pre-recoverable-review envelope accepted without rewrite."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[6] = 6
    case_id: UUID
    revision: int = Field(ge=0)
    onboarding: LegacyOnboardingCaseV6
    documents: tuple[DocumentProcessingRecord, ...] = Field(default=(), max_length=40)
    ownership: OwnershipAnalysisRecord | None = None
    reconciliation: ReconciliationCaseRecord | None = None
    clm: ClmOrchestrationRecord | None = None
    automation: ZeroTouchAutomationRecord | None = None
    target_executions: tuple[GoldTierExecutionLedgerEntry, ...] = Field(default=(), max_length=4)
    demo_scenario: str | None = Field(default=None, min_length=1, max_length=64)
    intelligence: OnboardingIntelligenceRecord | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_case_bindings(self) -> "DurableCaseSnapshotV6":
        _validate_case_bindings(self)
        return self

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot(
            schema_version=8,
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
            intelligence=self.intelligence,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class DurableCaseSnapshotV7(BaseModel):
    """Bounded authoritative structured state; never raw source/upload payloads."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[7] = 7
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
    intelligence: OnboardingIntelligenceRecord | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_case_bindings(self) -> "DurableCaseSnapshotV7":
        _validate_case_bindings(self)
        return self

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot.model_validate({**self.model_dump(), "schema_version": 8})


class DurableCaseSnapshot(BaseModel):
    """Bounded authoritative structured state; never raw source/upload payloads."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[8] = 8
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
    intelligence: OnboardingIntelligenceRecord | None = None
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
    intelligence = getattr(snapshot, "intelligence", None)
    if intelligence is not None:
        if intelligence.case_id != snapshot.case_id:
            raise ValueError("intelligence record does not match envelope")
        policy_snapshot = snapshot.onboarding.policy_snapshot
        if policy_snapshot.intelligence is None:
            raise ValueError("intelligence record requires immutable case policy")
        intelligence.validate_policy_binding(
            catalogue_version=policy_snapshot.catalogue_version,
            policy=policy_snapshot.intelligence,
        )
    if any(
        item.submission_input.case_id != snapshot.case_id for item in snapshot.target_executions
    ):
        raise ValueError("target execution does not match envelope")
    submission_ids = [item.submission_input.submission_id for item in snapshot.target_executions]
    if len(set(submission_ids)) != len(submission_ids):
        raise ValueError("duplicate target execution identity")
    clm = snapshot.clm
    if clm is not None and clm.submission_snapshot is not None:
        provider_mode = clm.submission_plan.environment
        target_input = clm.submission_snapshot.target_input
        if target_input.provider_mode != provider_mode:
            raise ValueError("GoldTier provider identity does not match the retained plan")
        for item in snapshot.target_executions:
            if (
                item.submission_input.submission_id == target_input.submission_id
                and item.submission_input.provider_mode != provider_mode
            ):
                raise ValueError(
                    "GoldTier provider identity does not match retained target execution"
                )
