"""Explicit schema-versioned representation for one durable CLM case."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.access import CasePriority, TeamId
from app.domain.clm import ClmOrchestrationRecord
from app.domain.documents import DocumentFieldKey, DocumentProcessingRecord
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
from app.domain.reconciliation import (
    ObservationValidity,
    ReconciliationCaseRecord,
    ReconciliationField,
)
from app.domain.target_submission import GoldTierExecutionLedgerEntry
from app.domain.zero_touch import ZeroTouchAutomationRecord

CASE_SNAPSHOT_SCHEMA_VERSION: Literal[15] = 15


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

    @model_validator(mode="before")
    @classmethod
    def reject_later_evidence(cls, value: Any) -> Any:
        reject_session2_legacy_fields(value)
        return value

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot(
            schema_version=CASE_SNAPSHOT_SCHEMA_VERSION,
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

    @model_validator(mode="before")
    @classmethod
    def reject_later_evidence(cls, value: Any) -> Any:
        reject_session2_legacy_fields(value)
        return value

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot(
            schema_version=CASE_SNAPSHOT_SCHEMA_VERSION,
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

    @model_validator(mode="before")
    @classmethod
    def reject_later_evidence(cls, value: Any) -> Any:
        reject_session2_legacy_fields(value)
        return value

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot(
            schema_version=CASE_SNAPSHOT_SCHEMA_VERSION,
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

    @model_validator(mode="before")
    @classmethod
    def reject_later_evidence(cls, value: Any) -> Any:
        reject_session2_legacy_fields(value)
        return value

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot(
            schema_version=CASE_SNAPSHOT_SCHEMA_VERSION,
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

    @model_validator(mode="before")
    @classmethod
    def reject_later_evidence(cls, value: Any) -> Any:
        reject_session2_legacy_fields(value)
        return value

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot(
            schema_version=CASE_SNAPSHOT_SCHEMA_VERSION,
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

    @model_validator(mode="before")
    @classmethod
    def reject_later_evidence(cls, value: Any) -> Any:
        reject_session2_legacy_fields(value)
        return value

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot(
            schema_version=CASE_SNAPSHOT_SCHEMA_VERSION,
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

    @model_validator(mode="before")
    @classmethod
    def reject_later_evidence(cls, value: Any) -> Any:
        reject_session2_legacy_fields(value)
        return value

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot(
            schema_version=CASE_SNAPSHOT_SCHEMA_VERSION,
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


class DurableCaseSnapshotV8(BaseModel):
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

    @model_validator(mode="before")
    @classmethod
    def reject_later_evidence(cls, value: Any) -> Any:
        reject_session2_legacy_fields(value)
        return value

    @model_validator(mode="after")
    def validate_case_bindings(self) -> "DurableCaseSnapshotV8":
        _validate_case_bindings(self)
        return self


    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot(
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


class DurableCaseSnapshotV9(BaseModel):
    """Bounded authoritative structured state; never raw source/upload payloads."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[9] = 9
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

    @model_validator(mode="before")
    @classmethod
    def reject_later_evidence(cls, value: Any) -> Any:
        reject_classification_legacy_fields(value)
        reject_hybrid_overlay_legacy_fields(value)
        reject_official_shareholder_legacy_fields(value)
        return value

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot.model_validate(
            {**self.model_dump(), "schema_version": CASE_SNAPSHOT_SCHEMA_VERSION}
        )

    @model_validator(mode="after")
    def validate_case_bindings(self) -> "DurableCaseSnapshotV9":
        _validate_case_bindings(self)
        return self


class DurableCaseSnapshotV10(BaseModel):
    """Exact schema-10 envelope: no frozen discovery policy or discovery audit."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[10] = 10
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

    @model_validator(mode="before")
    @classmethod
    def reject_later_evidence(cls, value: Any) -> Any:
        reject_ownership_discovery_legacy_fields(value)
        reject_hybrid_overlay_legacy_fields(value)
        reject_official_shareholder_legacy_fields(value)
        return value

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot.model_validate(
            {**self.model_dump(), "schema_version": CASE_SNAPSHOT_SCHEMA_VERSION}
        )

    @model_validator(mode="after")
    def validate_case_bindings(self) -> "DurableCaseSnapshotV10":
        _validate_case_bindings(self)
        return self


class DurableCaseSnapshotV11(BaseModel):
    """Exact schema-11 envelope: no hybrid official-Mock plus local overlay evidence."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[11] = 11
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

    @model_validator(mode="before")
    @classmethod
    def reject_later_evidence(cls, value: Any) -> Any:
        reject_hybrid_overlay_legacy_fields(value)
        reject_official_shareholder_legacy_fields(value)
        return value

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot.model_validate(
            {**self.model_dump(), "schema_version": CASE_SNAPSHOT_SCHEMA_VERSION}
        )

    @model_validator(mode="after")
    def validate_case_bindings(self) -> "DurableCaseSnapshotV11":
        _validate_case_bindings(self)
        return self


class DurableCaseSnapshotV12(BaseModel):
    """Exact schema-12 envelope: no D-079 official shareholder evidence."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[12] = 12
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

    @model_validator(mode="before")
    @classmethod
    def reject_later_evidence(cls, value: Any) -> Any:
        reject_official_shareholder_legacy_fields(value)
        return value

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot.model_validate(
            {**self.model_dump(), "schema_version": CASE_SNAPSHOT_SCHEMA_VERSION}
        )

    @model_validator(mode="after")
    def validate_case_bindings(self) -> "DurableCaseSnapshotV12":
        _validate_case_bindings(self)
        return self


class DurableCaseSnapshotV13(BaseModel):
    """Exact schema-13 envelope: D-079 official rows without a D-080 share class."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[13] = 13
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

    @model_validator(mode="before")
    @classmethod
    def reject_later_evidence(cls, value: Any) -> Any:
        reject_share_class_legacy_fields(value)
        return value

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot.model_validate(
            {**self.model_dump(), "schema_version": CASE_SNAPSHOT_SCHEMA_VERSION}
        )

    @model_validator(mode="after")
    def validate_case_bindings(self) -> "DurableCaseSnapshotV13":
        _validate_case_bindings(self)
        return self


class DurableCaseSnapshotV14(BaseModel):
    """Exact schema-14 envelope: D-080..D-082 evidence without a D-085 acceptance."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[14] = 14
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

    @model_validator(mode="before")
    @classmethod
    def reject_later_evidence(cls, value: Any) -> Any:
        reject_scenario_poc_legacy_fields(value)
        return value

    def to_current(self) -> "DurableCaseSnapshot":
        return DurableCaseSnapshot.model_validate(
            {**self.model_dump(), "schema_version": CASE_SNAPSHOT_SCHEMA_VERSION}
        )

    @model_validator(mode="after")
    def validate_case_bindings(self) -> "DurableCaseSnapshotV14":
        _validate_case_bindings(self)
        return self


class DurableCaseSnapshot(BaseModel):
    """Bounded authoritative structured state; never raw source/upload payloads."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[15] = 15
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


def _explicit_fields(value: Any) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return {name: getattr(value, name) for name in value.model_fields_set}
    return value if isinstance(value, dict) else {}


def reject_classification_legacy_fields(value: Any) -> None:
    raw = _explicit_fields(value)
    if "target_classification_selections" in _explicit_fields(raw.get("onboarding")):
        raise ValueError("Historical schema cannot contain target selection evidence")
    if any(
        "classification_observations" in _explicit_fields(doc) for doc in raw.get("documents", ())
    ):
        raise ValueError("Historical schema cannot contain classification observations")


def reject_ownership_discovery_legacy_fields(value: Any) -> None:
    """Schema <= 10 envelopes cannot carry a frozen discovery policy or audit.

    Like the Phase24C policy-parameter rule, an explicit null is the legacy meaning.
    """
    raw = _explicit_fields(value)
    onboarding = _explicit_fields(raw.get("onboarding"))
    snapshots = (
        onboarding.get("policy_snapshot"),
        *(
            _explicit_fields(item).get("previous_snapshot")
            for item in onboarding.get("policy_rebind_history", ())
        ),
    )
    if any(_explicit_fields(item).get("ownership_discovery") is not None for item in snapshots):
        raise ValueError("Historical schema cannot contain ownership discovery policy.")
    ownership = _explicit_fields(raw.get("ownership"))
    for record in (ownership, *ownership.get("prior_analyses", ())):
        if _explicit_fields(record).get("discovery") is not None:
            raise ValueError("Historical schema cannot contain ownership discovery audit.")


_HYBRID_AUDIT_FIELDS = (
    "overlay_scenario_id",
    "topology_complete",
    "official_identity_complete",
    "quantitative_evidence_complete",
)
_HYBRID_RECORD_FIELDS = ("identity_basis", "official_entity_lookup", "official_legal_form")


def reject_hybrid_overlay_legacy_fields(value: Any) -> None:
    """Schema <= 11 envelopes cannot carry hybrid official-Mock plus local overlay evidence.

    As for the discovery audit, an explicit null keeps the legacy meaning.
    """
    raw = _explicit_fields(value)
    ownership = _explicit_fields(raw.get("ownership"))
    for record in (ownership, *ownership.get("prior_analyses", ())):
        fields = _explicit_fields(record)
        if str(fields.get("source_classification")) == "OFFICIAL_MOCK_PLUS_LOCAL_DIRECT_OVERLAY":
            raise ValueError("Historical schema cannot contain hybrid overlay ownership.")
        audit = _explicit_fields(fields.get("discovery"))
        if any(audit.get(name) is not None for name in _HYBRID_AUDIT_FIELDS) or any(
            str(_explicit_fields(item).get("outcome")) == "LOCAL_SYNTHETIC_OVERLAY"
            or any(_explicit_fields(item).get(name) is not None for name in _HYBRID_RECORD_FIELDS)
            for item in audit.get("records", ())
        ):
            raise ValueError("Historical schema cannot contain hybrid overlay discovery.")
        if any(
            _explicit_fields(item).get("synthetic_basis_threshold_result") is not None
            for item in fields.get("candidates", ())
        ) or any(
            str(_explicit_fields(item).get("code")) == "SYNTHETIC_OWNERSHIP_EVIDENCE"
            for item in fields.get("issues", ())
        ):
            raise ValueError("Historical schema cannot contain hybrid overlay analysis.")


def reject_official_shareholder_legacy_fields(value: Any) -> None:
    """Schema <= 12 envelopes cannot carry D-079 official shareholder evidence.

    An explicit empty collection or null lookup keeps the legacy meaning.
    """
    raw = _explicit_fields(value)
    ownership = _explicit_fields(raw.get("ownership"))
    for record in (ownership, *ownership.get("prior_analyses", ())):
        audit = _explicit_fields(_explicit_fields(record).get("discovery"))
        for item in audit.get("records", ()):
            fields = _explicit_fields(item)
            if (
                fields.get("official_shareholders")
                or fields.get("official_shareholder_lookup") is not None
                or str(fields.get("reason_code"))
                in {
                    "OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE",
                    "OFFICIAL_SHAREHOLDERS_EMPTY",
                    "OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS",
                }
            ):
                raise ValueError("Historical schema cannot contain official shareholder evidence.")


def reject_share_class_legacy_fields(value: Any) -> None:
    """Schema <= 13 envelopes cannot carry D-080 share class/currency, D-081 POC links
    or a D-082 POC acceptance.

    An explicit null keeps the legacy meaning. Older schemas already reject the rows.
    """
    raw = _explicit_fields(value)
    ownership = _explicit_fields(raw.get("ownership"))
    for record in (ownership, *ownership.get("prior_analyses", ())):
        analysis = _explicit_fields(record)
        if analysis.get("poc_acceptance") is not None:
            raise ValueError("Historical schema cannot contain a POC ownership acceptance.")
        if any(
            str(_explicit_fields(_explicit_fields(edge).get("provenance")).get("provider"))
            == "LOCAL_POC_ASSUMED_EQUAL_UNITS"
            for edge in analysis.get("relationships", ()) or ()
        ):
            raise ValueError("Historical schema cannot contain POC equal-unit links.")
        audit = _explicit_fields(analysis.get("discovery"))
        for item in audit.get("records", ()):
            reason = str(_explicit_fields(item).get("reason_code"))
            if reason == "OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS":
                raise ValueError("Historical schema cannot contain POC equal-unit evidence.")
            for row in _explicit_fields(item).get("official_shareholders", ()) or ():
                fields = _explicit_fields(row)
                if fields.get("share_type") is not None or fields.get("currency") is not None:
                    raise ValueError("Historical schema cannot contain an official share class.")


def reject_scenario_poc_legacy_fields(value: Any) -> None:
    """Schema <= 14 envelopes cannot carry a D-085 scenario-declared POC acceptance.

    A D-082 acceptance stays readable in schema 14; explicit empty assumptions keep the
    legacy meaning. Older schemas already reject every acceptance.
    """
    raw = _explicit_fields(value)
    ownership = _explicit_fields(raw.get("ownership"))
    for record in (ownership, *ownership.get("prior_analyses", ())):
        acceptance = _explicit_fields(_explicit_fields(record).get("poc_acceptance"))
        if (
            str(acceptance.get("policy")) == "D085_SCENARIO_DECLARED_POC_BASIS_V1"
            or acceptance.get("accepted_assumptions")
        ):
            raise ValueError("Historical schema cannot contain a D-085 POC acceptance.")
        audit = _explicit_fields(_explicit_fields(record).get("discovery"))
        if any(
            _explicit_fields(item).get("official_officer_roles")
            for item in audit.get("records", ()) or ()
        ):
            raise ValueError("Historical schema cannot contain D-086 officer role observations.")


def reject_session2_legacy_fields(value: Any) -> None:
    """Reject later evidence in exact historical envelope versions, even if null."""
    reject_classification_legacy_fields(value)
    reject_hybrid_overlay_legacy_fields(value)
    reject_official_shareholder_legacy_fields(value)
    raw = _explicit_fields(value)
    reconciliation = _explicit_fields(raw.get("reconciliation"))
    for result in (*reconciliation.get("fields", ()), *reconciliation.get("discrepancies", ())):
        for observation in _explicit_fields(result).get("observations", ()):
            fields = _explicit_fields(observation)
            if (
                fields.get("validity") == "AMBIGUOUS"
                or fields.get("evidence_reference") == "DOCUMENT_AMBIGUOUS_EXTRACTION"
            ):
                raise ValueError(
                    "Historical schema cannot contain ambiguous extraction observations."
                )
    if "created_by_actor_id" in _explicit_fields(raw.get("onboarding")):
        raise ValueError("Historical schema cannot contain a creator binding.")
    metadata = {
        "extraction_method", "extraction_quality", "score_kind", "score_formula",
        "raw_ocr_mean_confidence", "raw_ocr_word_count", "candidates",
    }
    for document in raw.get("documents", ()):
        doc = _explicit_fields(document)
        if {"document_version", "pages", "ownership_observations"} & doc.keys():
            raise ValueError("Historical schema cannot contain later document evidence.")
        if doc.get("media_type") not in {
            "application/pdf", "text/plain",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }:
            raise ValueError("Historical schema cannot contain image intake.")
        if any(metadata & _explicit_fields(field).keys() for field in doc.get("fields", ())):
            raise ValueError("Historical schema cannot contain later extraction metadata.")
    ownership = _explicit_fields(raw.get("ownership"))
    new_ownership = {
        "document_observations", "document_bindings", "document_discrepancies",
        "source_classification",
        "supplemental_parties", "supplemental_relationships", "supplemental_evidence",
    }
    new_receipt = {
        "source_selection", "observed_document_versions", "selected_observation_ids",
        "replaced_analysis_id", "replaced_ownership_version",
    }
    for index, record in enumerate((ownership, *ownership.get("prior_analyses", ()))):
        fields = _explicit_fields(record)
        if new_ownership & fields.keys() or (index and "manual_review_receipt" in fields):
            raise ValueError("Historical schema cannot contain later ownership evidence.")
        if new_receipt & _explicit_fields(fields.get("manual_review_receipt")).keys():
            raise ValueError("Historical schema cannot contain later ownership decisions.")


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
    documents = {item.document_id: item for item in snapshot.documents}
    if len(documents) != len(snapshot.documents):
        raise ValueError("duplicate document identity")
    for selection in getattr(snapshot.onboarding, "target_classification_selections", ()):
        evidence = selection.document_evidence
        if evidence is None:
            continue
        document = documents.get(evidence.document_id)
        if document is None or evidence.document_event_count > len(document.events):
            raise ValueError("Target selection requires its original document event version")
        if not any(
            obs.field_key == selection.field_key
            and obs.document_version == evidence.document_version
            and obs.page_number == evidence.page_number
            and obs.source_reference == evidence.source_reference
            and obs.value == evidence.extracted_exact_value
            and obs.evidence_score == evidence.evidence_score
            and obs.extraction_method == evidence.extraction_method
            and obs.extraction_quality == evidence.extraction_quality
            for obs in document.classification_observations
        ):
            raise ValueError("Target selection differs from original classification observation")
    observations = {}
    for document in snapshot.documents:
        for observation in document.ownership_observations:
            if (
                observation.document_id != document.document_id
                or observation.document_version != document.document_version
                or observation.observation_id in observations
            ):
                raise ValueError("document ownership observation binding does not match")
            observations[observation.observation_id] = observation
    if snapshot.ownership is not None:
        for record in (snapshot.ownership, *snapshot.ownership.prior_analyses):
            for observation in record.document_observations:
                if observations.get(observation.observation_id) != observation:
                    raise ValueError(
                        "ownership observation differs from original document evidence"
                    )
            for binding in record.document_bindings:
                document = documents.get(binding.document_id)
                if document is None or binding.event_count > len(document.events):
                    raise ValueError("ownership decision version exceeds retained document")
            record_observations = {
                item.observation_id: item for item in record.document_observations
            }
            receipt = record.manual_review_receipt
            if receipt is not None:
                original_document = documents.get(receipt.evidence_document_id)
                if (
                    original_document is None
                    or receipt.evidence_document_version > len(original_document.events)
                    or (
                        snapshot.onboarding.created_by_actor_id is not None
                        and receipt.actor_id != snapshot.onboarding.created_by_actor_id
                    )
                    or receipt.evidence_reference != (
                        f"MANUAL_DOC_{receipt.evidence_document_id.hex}"
                        f"_V{receipt.evidence_document_version}"
                    )
                ):
                    raise ValueError("manual receipt lacks its retained document provenance")
                for binding in receipt.observed_document_versions:
                    document = documents.get(binding.document_id)
                    if document is None or binding.event_count > len(document.events):
                        raise ValueError("manual receipt exceeds retained document version")
                if any(identifier not in record_observations
                       for identifier in receipt.selected_observation_ids):
                    raise ValueError("manual receipt lacks its original observation")
            for discrepancy in record.document_discrepancies:
                observation = record_observations.get(discrepancy.observation_id)
                if (
                    observation is None
                    or observation.document_id != discrepancy.document_id
                    or observation.document_version != discrepancy.document_version
                ):
                    raise ValueError("ownership discrepancy lacks retained observation")
    if snapshot.reconciliation is not None:
        field_keys = {
            ReconciliationField.LEGAL_NAME: DocumentFieldKey.LEGAL_NAME,
            ReconciliationField.REGISTRATION_IDENTIFIER: DocumentFieldKey.REGISTRATION_NUMBER,
            ReconciliationField.REGISTERED_ADDRESS: DocumentFieldKey.REGISTERED_ADDRESS,
            ReconciliationField.COUNTRY_OF_INCORPORATION: DocumentFieldKey.COUNTRY_OF_INCORPORATION,
        }
        for result in (*snapshot.reconciliation.fields, *snapshot.reconciliation.discrepancies):
            for observation in result.observations:
                if observation.validity != ObservationValidity.AMBIGUOUS:
                    continue
                document = documents.get(observation.source_record_id)
                extracted = next((item for item in document.fields
                                  if item.field_key == field_keys[observation.field_name]), None) \
                    if document is not None else None
                if extracted is None or extracted.extraction_quality != "AMBIGUOUS" \
                        or len({item.value for item in extracted.candidates}) < 2:
                    raise ValueError("ambiguous reconciliation lacks original candidates")
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
