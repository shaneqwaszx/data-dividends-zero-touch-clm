"""Deterministic, metadata-only decisions for zero-touch POC blockers.

The policy does not resolve exceptions or advance workflow state. The existing
zero-touch orchestrator, evidence owners, authorization service, and target ledger
remain authoritative for every mutation and transition.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from app.domain.access import ROLE_CAPABILITIES, Capability, Role
from app.domain.zero_touch import (
    AutomationStage,
    BlockerDecisionAction,
    BlockerDecisionClassification,
    BlockerDecisionMetadata,
    BlockerDecisionOwner,
    BlockerMinimumInput,
    BusinessExceptionType,
    ExceptionResolutionAction,
    InvalidatedDependency,
    ResumeTransition,
    SafeBlockerCode,
)

BLOCKER_DECISION_POLICY_VERSION: Final = "BLOCKER_DECISION_POC_V1"


class OpenBlockerDecisionInput(BaseModel):
    """Typed current facts for an existing blocker; no free-text input is accepted."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    exception_type: BusinessExceptionType
    blocker_codes: tuple[SafeBlockerCode, ...] = Field(min_length=1, max_length=8)
    available_inputs: frozenset[BlockerMinimumInput] = Field(default_factory=frozenset)
    available_actions: frozenset[BlockerDecisionAction] = Field(default_factory=frozenset)
    available_resolution_actions: frozenset[ExceptionResolutionAction] = Field(
        default_factory=frozenset
    )

    @model_validator(mode="after")
    def blocker_codes_must_be_unique(self) -> OpenBlockerDecisionInput:
        if len(self.blocker_codes) != len(set(self.blocker_codes)):
            raise ValueError("blocker codes must be unique")
        return self


class AutoResolvedRule(StrEnum):
    EQUIVALENT_DOCUMENT_VALUES_AUTO_CONFIRMED = (
        "EQUIVALENT_DOCUMENT_VALUES_AUTO_CONFIRMED"
    )


class ContinueWithWarningRule(StrEnum):
    IDP_PROFILE_PROVISIONAL = "IDP_PROFILE_PROVISIONAL"
    UBO_POLICY_NOT_SPONSOR_CONFIRMED = "UBO_POLICY_NOT_SPONSOR_CONFIRMED"
    LIVE_HIERARCHY_UNAVAILABLE = "LIVE_HIERARCHY_UNAVAILABLE"
    RELATED_PARTY_MAPPING_PENDING = "RELATED_PARTY_MAPPING_PENDING"
    REAL_GOLDTIER_NOT_CONFIGURED = "REAL_GOLDTIER_NOT_CONFIGURED"
    READY_FOR_APPROVAL_UNAVAILABLE = "READY_FOR_APPROVAL_UNAVAILABLE"


class AutoResolvedDecisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule: AutoResolvedRule
    available_inputs: frozenset[BlockerMinimumInput]


class ContinueWithWarningDecisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule: ContinueWithWarningRule
    available_inputs: frozenset[BlockerMinimumInput]


@dataclass(frozen=True)
class _RuleSpec:
    codes: frozenset[str]
    exception_types: frozenset[BusinessExceptionType]
    classification: BlockerDecisionClassification
    rule_version: str
    owner: BlockerDecisionOwner
    minimum_inputs: tuple[BlockerMinimumInput, ...]
    permitted_actions: tuple[BlockerDecisionAction, ...]
    resume_stage: AutomationStage | None
    resume_transition: ResumeTransition
    invalidated_dependencies: tuple[InvalidatedDependency, ...]
    explanation: str
    unknowns: tuple[str, ...] = ()
    use_resolution_actions: bool = False


_IDENTITY_INVALIDATIONS = (
    InvalidatedDependency.CUSTOMER_IDENTITY,
    InvalidatedDependency.SEARCH_CHECKPOINT,
    InvalidatedDependency.REGISTRY_EVIDENCE,
    InvalidatedDependency.DOCUMENT_RECONCILIATION,
    InvalidatedDependency.OWNERSHIP_ANALYSIS,
    InvalidatedDependency.ADVISORY_INTELLIGENCE,
    InvalidatedDependency.READINESS_SNAPSHOT,
    InvalidatedDependency.TARGET_CONFIRMATION,
    InvalidatedDependency.TARGET_PLAN,
    InvalidatedDependency.TARGET_MUTATIONS,
)
_DOCUMENT_INVALIDATIONS = (
    InvalidatedDependency.DOCUMENT_RECONCILIATION,
    InvalidatedDependency.OWNERSHIP_ANALYSIS,
    InvalidatedDependency.ADVISORY_INTELLIGENCE,
    InvalidatedDependency.READINESS_SNAPSHOT,
    InvalidatedDependency.TARGET_CONFIRMATION,
    InvalidatedDependency.TARGET_PLAN,
    InvalidatedDependency.TARGET_MUTATIONS,
)
_OWNERSHIP_INVALIDATIONS = (
    InvalidatedDependency.OWNERSHIP_ANALYSIS,
    InvalidatedDependency.ADVISORY_INTELLIGENCE,
    InvalidatedDependency.READINESS_SNAPSHOT,
    InvalidatedDependency.TARGET_CONFIRMATION,
    InvalidatedDependency.TARGET_PLAN,
    InvalidatedDependency.TARGET_MUTATIONS,
)
_TARGET_INVALIDATIONS = (
    InvalidatedDependency.TARGET_CONFIRMATION,
    InvalidatedDependency.TARGET_PLAN,
    InvalidatedDependency.TARGET_MUTATIONS,
)
_DOCUMENT_EXCEPTION_TYPES = frozenset(
    {
        BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
        BusinessExceptionType.DOCUMENT_REQUIRED_FIELD_MISSING,
        BusinessExceptionType.DOCUMENT_REVIEW_REQUIRED,
        BusinessExceptionType.DOCUMENT_SOURCE_CONFLICT,
        BusinessExceptionType.RECONCILIATION_INVALID,
    }
)


_RULE_SPECS: tuple[_RuleSpec, ...] = (
    _RuleSpec(
        codes=frozenset({
            "INITIAL_IDENTITY_INCOMPLETE", "REGISTRY_IDENTIFIER_NOT_ELIGIBLE",
            "INITIAL_IDENTITY_NOT_ELIGIBLE", "ACRA_ENTITY_NOT_FOUND",
        }),
        exception_types=frozenset(
            {
                BusinessExceptionType.REGISTRY_REVIEW_REQUIRED,
                BusinessExceptionType.REGISTRY_IDENTIFIER_NOT_ELIGIBLE,
            }
        ),
        classification=BlockerDecisionClassification.USER_ACTION_REQUIRED,
        rule_version="BPD-IDENTITY-1",
        owner=BlockerDecisionOwner.IDENTITY_REVIEW_OWNER,
        minimum_inputs=(
            BlockerMinimumInput.CURRENT_CASE_VERSION,
            BlockerMinimumInput.CORRECTED_IDENTITY_WITH_RATIONALE,
        ),
        permitted_actions=(BlockerDecisionAction.CORRECT_INITIAL_IDENTITY,),
        resume_stage=AutomationStage.GOLDTIER_SEARCH,
        resume_transition=ResumeTransition.RECHECK_FROM_STAGE,
        invalidated_dependencies=_IDENTITY_INVALIDATIONS,
        explanation=(
            "Correct the same-case canonical identity, then run the authorized read-only "
            "Search recheck; identity-dependent evidence is not reused automatically."
        ),
    ),
    _RuleSpec(
        codes=frozenset({"REGISTRY_RECHECK_INCOMPLETE"}),
        exception_types=frozenset({BusinessExceptionType.REGISTRY_REVIEW_REQUIRED}),
        classification=BlockerDecisionClassification.USER_ACTION_REQUIRED,
        rule_version="BPD-REGISTRY-RECTIFICATION-1",
        owner=BlockerDecisionOwner.IDENTITY_REVIEW_OWNER,
        minimum_inputs=(
            BlockerMinimumInput.CURRENT_CASE_VERSION,
            BlockerMinimumInput.CORRECTED_IDENTITY_WITH_RATIONALE,
            BlockerMinimumInput.CURRENT_REGISTRY_EVIDENCE,
        ),
        permitted_actions=(BlockerDecisionAction.CORRECT_INITIAL_IDENTITY,),
        resume_stage=AutomationStage.REGISTRY,
        resume_transition=ResumeTransition.RECHECK_FROM_STAGE,
        invalidated_dependencies=_IDENTITY_INVALIDATIONS,
        explanation=(
            "The retained registry evidence is incomplete. An eligible same-case UEN may be "
            "verified through the owning correction path; missing provider data cannot be "
            "overridden or treated as verified evidence."
        ),
    ),
    _RuleSpec(
        codes=frozenset({"CANONICAL_DATA_INCOMPLETE"}),
        exception_types=frozenset({BusinessExceptionType.REGISTRY_REVIEW_REQUIRED}),
        classification=BlockerDecisionClassification.HARD_STOP,
        rule_version="BPD-CANONICAL-INCOMPLETE-1",
        owner=BlockerDecisionOwner.REGISTRY_INTEGRATION_OWNER,
        minimum_inputs=(BlockerMinimumInput.CURRENT_REGISTRY_EVIDENCE,),
        permitted_actions=(BlockerDecisionAction.ESCALATE_TO_OWNER,),
        resume_stage=AutomationStage.REGISTRY,
        resume_transition=ResumeTransition.NO_AUTOMATIC_RESUME,
        invalidated_dependencies=_IDENTITY_INVALIDATIONS[2:],
        explanation=(
            "Canonical presence validation failed. There is no generic browser canonical-data "
            "override; retain the registry evidence for the owning review. A separate guarded "
            "identity correction cannot fabricate missing provider fields."
        ),
    ),
    _RuleSpec(
        codes=frozenset({"JURISDICTION_UNRESOLVED", "JURISDICTION_CONFLICT"}),
        exception_types=frozenset(
            {
                BusinessExceptionType.JURISDICTION_UNRESOLVED,
                BusinessExceptionType.JURISDICTION_CONFLICT,
            }
        ),
        classification=BlockerDecisionClassification.USER_ACTION_REQUIRED,
        rule_version="BPD-JURISDICTION-1",
        owner=BlockerDecisionOwner.IDENTITY_REVIEW_OWNER,
        minimum_inputs=(BlockerMinimumInput.CURRENT_JURISDICTION_EVIDENCE,),
        permitted_actions=(BlockerDecisionAction.RESOLVE_JURISDICTION_EVIDENCE,),
        resume_stage=AutomationStage.REGISTRY,
        resume_transition=ResumeTransition.RECHECK_FROM_STAGE,
        invalidated_dependencies=_IDENTITY_INVALIDATIONS[2:],
        explanation=(
            "Jurisdiction evidence must be resolved by the owning review path before a "
            "registry route can be selected."
        ),
        unknowns=("SPONSOR_SOURCE_PRECEDENCE_UNRESOLVED",),
    ),
    _RuleSpec(
        codes=frozenset({"REGISTRY_PROVIDER_NOT_IMPLEMENTED"}),
        exception_types=frozenset({BusinessExceptionType.REGISTRY_PROVIDER_NOT_IMPLEMENTED}),
        classification=BlockerDecisionClassification.EXTERNAL_DEPENDENCY,
        rule_version="BPD-REGISTRY-PROVIDER-1",
        owner=BlockerDecisionOwner.REGISTRY_INTEGRATION_OWNER,
        minimum_inputs=(BlockerMinimumInput.CURRENT_CANONICAL_IDENTITY,),
        permitted_actions=(BlockerDecisionAction.ENABLE_SUPPORTED_REGISTRY_PROVIDER,),
        resume_stage=AutomationStage.REGISTRY,
        resume_transition=ResumeTransition.NO_AUTOMATIC_RESUME,
        invalidated_dependencies=_IDENTITY_INVALIDATIONS[2:],
        explanation="No implemented registry route exists for the resolved jurisdiction.",
    ),
    _RuleSpec(
        codes=frozenset({"REGISTRY_EXPECTED_DATA_MISSING"}),
        exception_types=frozenset({BusinessExceptionType.REGISTRY_REVIEW_REQUIRED}),
        classification=BlockerDecisionClassification.USER_ACTION_REQUIRED,
        rule_version="BPD-REGISTRY-EVIDENCE-1",
        owner=BlockerDecisionOwner.REGISTRY_INTEGRATION_OWNER,
        minimum_inputs=(BlockerMinimumInput.CURRENT_REGISTRY_EVIDENCE,),
        permitted_actions=(BlockerDecisionAction.PROVIDE_REGISTRY_EVIDENCE,),
        resume_stage=AutomationStage.REGISTRY,
        resume_transition=ResumeTransition.REPLACE_EVIDENCE_AND_RECHECK,
        invalidated_dependencies=_OWNERSHIP_INVALIDATIONS,
        explanation=(
            "Missing registry evidence must be supplied or replaced through an authorized "
            "evidence path; ignore-and-continue is not permitted."
        ),
        unknowns=("REGISTRY_OWNERSHIP_COMPLETENESS_AUTHORITY_UNRESOLVED",),
    ),
    _RuleSpec(
        codes=frozenset({"REGISTRY_REVIEW_REQUIRED", "REGISTRY_NOT_READY"}),
        exception_types=frozenset({BusinessExceptionType.REGISTRY_REVIEW_REQUIRED}),
        classification=BlockerDecisionClassification.HARD_STOP,
        rule_version="BPD-REGISTRY-REVIEW-1",
        owner=BlockerDecisionOwner.REGISTRY_INTEGRATION_OWNER,
        minimum_inputs=(BlockerMinimumInput.CURRENT_REGISTRY_EVIDENCE,),
        permitted_actions=(BlockerDecisionAction.ESCALATE_TO_OWNER,),
        resume_stage=AutomationStage.REGISTRY,
        resume_transition=ResumeTransition.NO_AUTOMATIC_RESUME,
        invalidated_dependencies=_IDENTITY_INVALIDATIONS[2:],
        explanation="Registry evidence is not sufficient for a safe automatic decision.",
    ),
    _RuleSpec(
        codes=frozenset({"REGISTRY_FAILED", "CANONICAL_DATA_INVALID"}),
        exception_types=frozenset({BusinessExceptionType.REGISTRY_REVIEW_REQUIRED}),
        classification=BlockerDecisionClassification.EXTERNAL_DEPENDENCY,
        rule_version="BPD-REGISTRY-FAILURE-1",
        owner=BlockerDecisionOwner.REGISTRY_INTEGRATION_OWNER,
        minimum_inputs=(BlockerMinimumInput.CURRENT_REGISTRY_EVIDENCE,),
        permitted_actions=(BlockerDecisionAction.ESCALATE_TO_OWNER,),
        resume_stage=AutomationStage.REGISTRY,
        resume_transition=ResumeTransition.NO_AUTOMATIC_RESUME,
        invalidated_dependencies=_IDENTITY_INVALIDATIONS[2:],
        explanation="Registry or canonical validation failed and cannot be waived by policy.",
    ),
    _RuleSpec(
        codes=frozenset({"DOCUMENT_REQUIRED"}),
        exception_types=_DOCUMENT_EXCEPTION_TYPES,
        classification=BlockerDecisionClassification.USER_ACTION_REQUIRED,
        rule_version="BPD-DOCUMENT-REQUIRED-1",
        owner=BlockerDecisionOwner.CASE_OPERATOR,
        minimum_inputs=(BlockerMinimumInput.CURRENT_CASE_VERSION,),
        permitted_actions=(BlockerDecisionAction.UPLOAD_DOCUMENT,),
        resume_stage=AutomationStage.DOCUMENT,
        resume_transition=ResumeTransition.REPLACE_EVIDENCE_AND_RECHECK,
        invalidated_dependencies=_DOCUMENT_INVALIDATIONS,
        explanation="A current supporting document is required before evidence review can run.",
    ),
    _RuleSpec(
        codes=frozenset(
            {
                "DOCUMENT_TEXT_UNAVAILABLE",
                "DOCUMENT_AMBIGUOUS_EXTRACTION",
                "DOCUMENT_PROCESSING_FAILED",
                "DOCUMENT_REUPLOAD_REQUIRED",
                "IDP_PROCESSING_FAILED",
            }
        ),
        exception_types=_DOCUMENT_EXCEPTION_TYPES,
        classification=BlockerDecisionClassification.USER_ACTION_REQUIRED,
        rule_version="BPD-DOCUMENT-REPLACEMENT-1",
        owner=BlockerDecisionOwner.DOCUMENT_REVIEW_OWNER,
        minimum_inputs=(BlockerMinimumInput.CURRENT_DOCUMENT_EVIDENCE,),
        permitted_actions=(BlockerDecisionAction.UPLOAD_REPLACEMENT_DOCUMENT,),
        resume_stage=AutomationStage.DOCUMENT,
        resume_transition=ResumeTransition.REPLACE_EVIDENCE_AND_RECHECK,
        invalidated_dependencies=_DOCUMENT_INVALIDATIONS,
        explanation=(
            "Unreadable or failed current evidence requires a case-bound replacement; "
            "missing text is never inferred or waived."
        ),
    ),
    _RuleSpec(
        codes=frozenset(
            {
                "DOCUMENT_LOW_CONFIDENCE",
                "DOCUMENT_REQUIRED_FIELD_MISSING",
                "DOCUMENT_REVIEW_INCOMPLETE",
                "DOCUMENT_REVIEW_REQUIRED",
                "DOCUMENT_REVIEW_STATE_INVALID",
            }
        ),
        exception_types=_DOCUMENT_EXCEPTION_TYPES,
        classification=BlockerDecisionClassification.USER_ACTION_REQUIRED,
        rule_version="BPD-DOCUMENT-REVIEW-1",
        owner=BlockerDecisionOwner.DOCUMENT_REVIEW_OWNER,
        minimum_inputs=(
            BlockerMinimumInput.CURRENT_DOCUMENT_EVIDENCE,
            BlockerMinimumInput.CURRENT_DOCUMENT_REVIEW,
        ),
        permitted_actions=(
            BlockerDecisionAction.COMPLETE_DOCUMENT_REVIEW,
            BlockerDecisionAction.UPLOAD_REPLACEMENT_DOCUMENT,
        ),
        resume_stage=AutomationStage.DOCUMENT,
        resume_transition=ResumeTransition.REPLACE_EVIDENCE_AND_RECHECK,
        invalidated_dependencies=_DOCUMENT_INVALIDATIONS,
        explanation="Current document evidence requires review or replacement before reuse.",
    ),
    _RuleSpec(
        codes=frozenset({"DOCUMENT_PROCESSING"}),
        exception_types=_DOCUMENT_EXCEPTION_TYPES,
        classification=BlockerDecisionClassification.HARD_STOP,
        rule_version="BPD-DOCUMENT-PROCESSING-1",
        owner=BlockerDecisionOwner.DOCUMENT_REVIEW_OWNER,
        minimum_inputs=(BlockerMinimumInput.CURRENT_DOCUMENT_EVIDENCE,),
        permitted_actions=(BlockerDecisionAction.WAIT_FOR_CURRENT_PROCESSING,),
        resume_stage=AutomationStage.DOCUMENT,
        resume_transition=ResumeTransition.NO_AUTOMATIC_RESUME,
        invalidated_dependencies=_DOCUMENT_INVALIDATIONS,
        explanation="In-flight document processing is not treated as completed evidence.",
    ),
    _RuleSpec(
        codes=frozenset({"DOCUMENT_SOURCE_CONFLICT", "SOURCE_CONFLICT_REQUIRES_POLICY"}),
        exception_types=_DOCUMENT_EXCEPTION_TYPES,
        classification=BlockerDecisionClassification.USER_ACTION_REQUIRED,
        rule_version="BPD-RECONCILIATION-CONFLICT-1",
        owner=BlockerDecisionOwner.DOCUMENT_REVIEW_OWNER,
        minimum_inputs=(
            BlockerMinimumInput.CURRENT_RECONCILIATION_EVIDENCE,
            BlockerMinimumInput.AUTHORIZED_RECONCILIATION_ACTION,
        ),
        permitted_actions=(
            BlockerDecisionAction.KEEP_REGISTRY_VALUE,
            BlockerDecisionAction.USE_DOCUMENT_VALUE,
            BlockerDecisionAction.REQUEST_ADDITIONAL_INFORMATION,
        ),
        resume_stage=AutomationStage.DOCUMENT,
        resume_transition=ResumeTransition.APPLY_AUTHORIZED_DECISION_AND_RECHECK,
        invalidated_dependencies=_DOCUMENT_INVALIDATIONS,
        explanation=(
            "Only a reconciliation action already authorized by the evidence owner may be used; "
            "this policy establishes no source precedence."
        ),
        unknowns=("SPONSOR_SOURCE_PRECEDENCE_UNRESOLVED",),
        use_resolution_actions=True,
    ),
    _RuleSpec(
        codes=frozenset({"RECONCILIATION_INVALID"}),
        exception_types=_DOCUMENT_EXCEPTION_TYPES,
        classification=BlockerDecisionClassification.HARD_STOP,
        rule_version="BPD-RECONCILIATION-INVALID-1",
        owner=BlockerDecisionOwner.DOCUMENT_REVIEW_OWNER,
        minimum_inputs=(BlockerMinimumInput.CURRENT_RECONCILIATION_EVIDENCE,),
        permitted_actions=(BlockerDecisionAction.ESCALATE_TO_OWNER,),
        resume_stage=AutomationStage.DOCUMENT,
        resume_transition=ResumeTransition.NO_AUTOMATIC_RESUME,
        invalidated_dependencies=_DOCUMENT_INVALIDATIONS,
        explanation="Invalid reconciliation evidence cannot be converted into a source decision.",
    ),
    _RuleSpec(
        codes=frozenset({"OWNERSHIP_REQUIRED"}),
        exception_types=frozenset({BusinessExceptionType.OWNERSHIP_INCOMPLETE}),
        classification=BlockerDecisionClassification.USER_ACTION_REQUIRED,
        rule_version="BPD-OWNERSHIP-REQUIRED-1",
        owner=BlockerDecisionOwner.OWNERSHIP_REVIEW_OWNER,
        minimum_inputs=(BlockerMinimumInput.CORRECTED_OWNERSHIP_EVIDENCE,),
        permitted_actions=(BlockerDecisionAction.PROVIDE_CORRECTED_OWNERSHIP_EVIDENCE,),
        resume_stage=AutomationStage.OWNERSHIP,
        resume_transition=ResumeTransition.REPLACE_EVIDENCE_AND_RECHECK,
        invalidated_dependencies=_OWNERSHIP_INVALIDATIONS,
        explanation="Ownership evidence is required before the Decimal engine may run.",
    ),
    _RuleSpec(
        codes=frozenset(
            {
                "OWNERSHIP_ANALYSIS_INCOMPLETE",
                "OWNERSHIP_CYCLE",
                "OWNERSHIP_INCOMPLETE",
                "OWNERSHIP_REVIEW_REQUIRED",
                "OWNERSHIP_DENOMINATOR_REQUIRED",
                "UBO_REVIEW_REQUIRED",
                "OWNERSHIP_METHOD_UNSUPPORTED",
                "CONTRADICTORY_OWNERSHIP_EVIDENCE",
            }
        ),
        exception_types=frozenset(
            {
                BusinessExceptionType.OWNERSHIP_CYCLE,
                BusinessExceptionType.OWNERSHIP_INCOMPLETE,
                BusinessExceptionType.OWNERSHIP_REVIEW_REQUIRED,
            }
        ),
        classification=BlockerDecisionClassification.USER_ACTION_REQUIRED,
        rule_version="BPD-OWNERSHIP-REVIEW-1",
        owner=BlockerDecisionOwner.OWNERSHIP_REVIEW_OWNER,
        minimum_inputs=(
            BlockerMinimumInput.CURRENT_OWNERSHIP_EVIDENCE,
            BlockerMinimumInput.CORRECTED_OWNERSHIP_EVIDENCE,
        ),
        permitted_actions=(
            BlockerDecisionAction.PROVIDE_CORRECTED_OWNERSHIP_EVIDENCE,
            BlockerDecisionAction.RERUN_OWNERSHIP_ANALYSIS,
        ),
        resume_stage=AutomationStage.OWNERSHIP,
        resume_transition=ResumeTransition.REPLACE_EVIDENCE_AND_RECHECK,
        invalidated_dependencies=_OWNERSHIP_INVALIDATIONS,
        explanation=(
            "Cycle, incomplete, or indeterminate ownership evidence must be corrected and "
            "recalculated by the existing Decimal engine."
        ),
        unknowns=("CURRENT_OWNERSHIP_EVIDENCE_REQUIRES_REVIEW",),
    ),
    _RuleSpec(
        codes=frozenset({"OWNERSHIP_ANALYSIS_FAILED"}),
        exception_types=frozenset({BusinessExceptionType.OWNERSHIP_REVIEW_REQUIRED}),
        classification=BlockerDecisionClassification.HARD_STOP,
        rule_version="BPD-OWNERSHIP-FAILURE-1",
        owner=BlockerDecisionOwner.OWNERSHIP_REVIEW_OWNER,
        minimum_inputs=(BlockerMinimumInput.CURRENT_OWNERSHIP_EVIDENCE,),
        permitted_actions=(BlockerDecisionAction.ESCALATE_TO_OWNER,),
        resume_stage=AutomationStage.OWNERSHIP,
        resume_transition=ResumeTransition.NO_AUTOMATIC_RESUME,
        invalidated_dependencies=_OWNERSHIP_INVALIDATIONS,
        explanation="Failed ownership analysis cannot be waived or recalculated by this policy.",
    ),
    _RuleSpec(
        codes=frozenset({"GT_SEARCH_IDENTITY_REVIEW_REQUIRED", "GOLDTIER_SEARCH_REVIEW_REQUIRED"}),
        exception_types=frozenset({BusinessExceptionType.ENTITY_RESOLUTION_REVIEW_REQUIRED}),
        classification=BlockerDecisionClassification.USER_ACTION_REQUIRED,
        rule_version="BPD-SEARCH-AMBIGUITY-2",
        owner=BlockerDecisionOwner.IDENTITY_REVIEW_OWNER,
        minimum_inputs=(
            BlockerMinimumInput.CURRENT_CANONICAL_IDENTITY,
            BlockerMinimumInput.CURRENT_SEARCH_CHECKPOINT,
        ),
        permitted_actions=(
            BlockerDecisionAction.CORRECT_INITIAL_IDENTITY,
            BlockerDecisionAction.RUN_READ_ONLY_SEARCH_RECHECK,
            BlockerDecisionAction.CONFIRM_EXISTING_GOLDTIER_CUSTOMER,
        ),
        resume_stage=AutomationStage.GOLDTIER_SEARCH,
        resume_transition=ResumeTransition.RECHECK_FROM_STAGE,
        invalidated_dependencies=_IDENTITY_INVALIDATIONS[1:],
        explanation=(
            "Target identity requires a bounded current-evidence decision or corrected identity "
            "and a new read-only Search; incomplete or multiple candidates are never auto-selected."
        ),
    ),
    _RuleSpec(
        codes=frozenset(
            {
                "GOLDTIER_SEARCH_FAILED",
                "GOLDTIER_SEARCH_REQUIRED",
                "GOLDTIER_SEARCH_STALE",
                "GT_SEARCH_FAILED",
                "SEARCH_SERVICE_UNAVAILABLE",
            }
        ),
        exception_types=frozenset({BusinessExceptionType.ENTITY_RESOLUTION_REVIEW_REQUIRED}),
        classification=BlockerDecisionClassification.EXTERNAL_DEPENDENCY,
        rule_version="BPD-SEARCH-FAILURE-1",
        owner=BlockerDecisionOwner.TARGET_PROVIDER_OWNER,
        minimum_inputs=(
            BlockerMinimumInput.CURRENT_CANONICAL_IDENTITY,
            BlockerMinimumInput.CURRENT_SEARCH_CHECKPOINT,
        ),
        permitted_actions=(BlockerDecisionAction.RUN_READ_ONLY_SEARCH_RECHECK,),
        resume_stage=AutomationStage.GOLDTIER_SEARCH,
        resume_transition=ResumeTransition.RECHECK_FROM_STAGE,
        invalidated_dependencies=_TARGET_INVALIDATIONS,
        explanation=(
            "Search failure, absence, or staleness never proves no match; target mutation remains "
            "blocked until a current read-only Search succeeds."
        ),
    ),
    _RuleSpec(
        codes=frozenset({"ENTITY_RESOLUTION_REVIEW_REQUIRED"}),
        exception_types=frozenset({BusinessExceptionType.ENTITY_RESOLUTION_REVIEW_REQUIRED}),
        classification=BlockerDecisionClassification.USER_ACTION_REQUIRED,
        rule_version="BPD-ENTITY-REVIEW-1",
        owner=BlockerDecisionOwner.IDENTITY_REVIEW_OWNER,
        minimum_inputs=(BlockerMinimumInput.CURRENT_ENTITY_RESOLUTION_EVIDENCE,),
        permitted_actions=(BlockerDecisionAction.REVIEW_ENTITY_IDENTITY,),
        resume_stage=AutomationStage.READINESS,
        resume_transition=ResumeTransition.RECHECK_FROM_STAGE,
        invalidated_dependencies=_TARGET_INVALIDATIONS,
        explanation="Ambiguous advisory entity evidence cannot establish canonical identity.",
    ),
    _RuleSpec(
        codes=frozenset({"MOCK_RISK_REVIEW_REQUIRED"}),
        exception_types=frozenset({BusinessExceptionType.MOCK_RISK_REVIEW_REQUIRED}),
        classification=BlockerDecisionClassification.HARD_STOP,
        rule_version="BPD-MOCK-RISK-1",
        owner=BlockerDecisionOwner.POLICY_OWNER,
        minimum_inputs=(BlockerMinimumInput.CURRENT_MOCK_RISK_EVIDENCE,),
        permitted_actions=(BlockerDecisionAction.REVIEW_MOCK_RISK,),
        resume_stage=AutomationStage.READINESS,
        resume_transition=ResumeTransition.NO_AUTOMATIC_RESUME,
        invalidated_dependencies=_TARGET_INVALIDATIONS,
        explanation="Mock advisory risk is not a compliance decision and cannot be waived here.",
        unknowns=("SPONSOR_RISK_REVIEW_POLICY_UNRESOLVED",),
    ),
    _RuleSpec(
        codes=frozenset({"GOLDTIER_CLASSIFICATION_REQUIRED"}),
        exception_types=frozenset({BusinessExceptionType.TARGET_CLASSIFICATION_REQUIRED}),
        classification=BlockerDecisionClassification.USER_ACTION_REQUIRED,
        rule_version="BPD-TARGET-CLASSIFICATION-1",
        owner=BlockerDecisionOwner.CASE_OPERATOR,
        minimum_inputs=(BlockerMinimumInput.CURRENT_TARGET_CLASSIFICATION,),
        permitted_actions=(BlockerDecisionAction.SELECT_TARGET_CLASSIFICATION,),
        resume_stage=AutomationStage.READINESS,
        resume_transition=ResumeTransition.RECHECK_FROM_STAGE,
        invalidated_dependencies=_TARGET_INVALIDATIONS,
        explanation="A valid case-bound target classification is required before review freezing.",
    ),
    _RuleSpec(
        codes=frozenset({"TARGET_CONFIRMATION_REQUIRED"}),
        exception_types=frozenset({BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED}),
        classification=BlockerDecisionClassification.USER_ACTION_REQUIRED,
        rule_version="BPD-TARGET-CONFIRMATION-1",
        owner=BlockerDecisionOwner.CASE_OPERATOR,
        minimum_inputs=(BlockerMinimumInput.CURRENT_FROZEN_TARGET_REVIEW,),
        permitted_actions=(BlockerDecisionAction.CONFIRM_FROZEN_TARGET_SUBMISSION,),
        resume_stage=AutomationStage.MOCK_GOLDTIER,
        resume_transition=ResumeTransition.RECHECK_FROM_STAGE,
        invalidated_dependencies=(InvalidatedDependency.TARGET_MUTATIONS,),
        explanation="Current durable confirmation is required before the first target mutation.",
    ),
    _RuleSpec(
        codes=frozenset({"GT_EXISTING_PARTY_REVIEW_REQUIRED"}),
        exception_types=frozenset({BusinessExceptionType.EXISTING_PARTY_REVIEW_REQUIRED}),
        classification=BlockerDecisionClassification.USER_ACTION_REQUIRED,
        rule_version="BPD-EXISTING-PARTY-1",
        owner=BlockerDecisionOwner.IDENTITY_REVIEW_OWNER,
        minimum_inputs=(
            BlockerMinimumInput.CURRENT_CANONICAL_IDENTITY,
            BlockerMinimumInput.CURRENT_SEARCH_CHECKPOINT,
        ),
        permitted_actions=(BlockerDecisionAction.REVIEW_ENTITY_IDENTITY,),
        resume_stage=AutomationStage.GOLDTIER_SEARCH,
        resume_transition=ResumeTransition.RECHECK_FROM_STAGE,
        invalidated_dependencies=_TARGET_INVALIDATIONS,
        explanation=(
            "An existing target party requires exact identity review; duplicate creation stops."
        ),
    ),
    _RuleSpec(
        codes=frozenset(
            {
                "GT_PARTIAL_SUCCESS",
                "GT_OPTIONAL_SECTION_REVIEW",
                "GT_READBACK_IDENTITY_REVIEW_REQUIRED",
                "PROVIDER_VALIDATION_FAILED",
                "TARGET_REVIEW_REQUIRED",
            }
        ),
        exception_types=frozenset({BusinessExceptionType.TARGET_PARTIAL_REVIEW_REQUIRED}),
        classification=BlockerDecisionClassification.HARD_STOP,
        rule_version="BPD-TARGET-PARTIAL-1",
        owner=BlockerDecisionOwner.TARGET_PROVIDER_OWNER,
        minimum_inputs=(
            BlockerMinimumInput.CURRENT_TARGET_LEDGER,
            BlockerMinimumInput.PROVIDER_DIAGNOSIS,
        ),
        permitted_actions=(BlockerDecisionAction.DIAGNOSE_PROVIDER_VALIDATION,),
        resume_stage=AutomationStage.MOCK_GOLDTIER,
        resume_transition=ResumeTransition.NO_AUTOMATIC_RESUME,
        invalidated_dependencies=(InvalidatedDependency.TARGET_MUTATIONS,),
        explanation=(
            "Partial or provider-rejected target work requires diagnosis before any new attempt."
        ),
        unknowns=("SAFE_TARGET_RETRY_NOT_AUTHORIZED",),
    ),
    _RuleSpec(
        codes=frozenset(
            {
                "BLOCKED_CHILD_ID_LIFECYCLE",
                "READY_FOR_APPROVAL_NOT_IMPLEMENTED",
            }
        ),
        exception_types=frozenset({BusinessExceptionType.TARGET_PARTIAL_REVIEW_REQUIRED}),
        classification=BlockerDecisionClassification.EXTERNAL_DEPENDENCY,
        rule_version="BPD-TARGET-CONTRACT-1",
        owner=BlockerDecisionOwner.POLICY_OWNER,
        minimum_inputs=(BlockerMinimumInput.CURRENT_TARGET_LEDGER,),
        permitted_actions=(BlockerDecisionAction.ESCALATE_TO_OWNER,),
        resume_stage=None,
        resume_transition=ResumeTransition.NO_AUTOMATIC_RESUME,
        invalidated_dependencies=(InvalidatedDependency.TARGET_MUTATIONS,),
        explanation=(
            "The required target contract or approval transition is not implemented and "
            "cannot be inferred by this POC policy."
        ),
        unknowns=("SPONSOR_TARGET_CONTRACT_AUTHORITY_UNRESOLVED",),
    ),
    _RuleSpec(
        codes=frozenset(
            {
                "CLM_TARGET_OUTCOME_UNCERTAIN",
                "TARGET_OPERATION_OUTCOME_UNCERTAIN",
                "UNCERTAIN_TARGET_MUTATION",
            }
        ),
        exception_types=frozenset({BusinessExceptionType.TARGET_PARTIAL_REVIEW_REQUIRED}),
        classification=BlockerDecisionClassification.HARD_STOP,
        rule_version="BPD-TARGET-UNCERTAIN-1",
        owner=BlockerDecisionOwner.TARGET_OPERATIONS_OWNER,
        minimum_inputs=(
            BlockerMinimumInput.CURRENT_TARGET_LEDGER,
            BlockerMinimumInput.PROVIDER_VERIFICATION,
        ),
        permitted_actions=(BlockerDecisionAction.VERIFY_TARGET_OUTCOME_WITHOUT_REPLAY,),
        resume_stage=AutomationStage.MOCK_GOLDTIER,
        resume_transition=ResumeTransition.VERIFY_WITHOUT_REPLAY,
        invalidated_dependencies=(InvalidatedDependency.TARGET_MUTATIONS,),
        explanation=(
            "An uncertain write must be verified against the provider and is never replayed."
        ),
        unknowns=("ORIGINAL_TARGET_MUTATION_OUTCOME_UNCERTAIN",),
    ),
    _RuleSpec(
        codes=frozenset({"CLM_FINALIZATION_RETRY_REQUIRED"}),
        exception_types=frozenset({BusinessExceptionType.TARGET_PARTIAL_REVIEW_REQUIRED}),
        classification=BlockerDecisionClassification.HARD_STOP,
        rule_version="BPD-TARGET-FINALIZATION-1",
        owner=BlockerDecisionOwner.TARGET_OPERATIONS_OWNER,
        minimum_inputs=(BlockerMinimumInput.CURRENT_TARGET_LEDGER,),
        permitted_actions=(BlockerDecisionAction.FINALIZE_RETAINED_TARGET_OUTCOME,),
        resume_stage=AutomationStage.MOCK_GOLDTIER,
        resume_transition=ResumeTransition.VERIFY_WITHOUT_REPLAY,
        invalidated_dependencies=(InvalidatedDependency.TARGET_MUTATIONS,),
        explanation=(
            "Only finalization of the retained target outcome is permitted; no call is replayed."
        ),
    ),
)


def _build_rule_index() -> dict[str, _RuleSpec]:
    index: dict[str, _RuleSpec] = {}
    for spec in _RULE_SPECS:
        for code in spec.codes:
            if code in index:
                raise RuntimeError("duplicate blocker decision rule")
            index[code] = spec
    return index


_RULE_INDEX = _build_rule_index()
SUPPORTED_BLOCKER_CODES: Final[frozenset[str]] = frozenset(_RULE_INDEX)
SUPPORTED_BLOCKER_BINDINGS: Final[Mapping[str, frozenset[BusinessExceptionType]]] = (
    MappingProxyType({code: spec.exception_types for code, spec in _RULE_INDEX.items()})
)
MAPPED_BUSINESS_EXCEPTION_TYPES: Final[frozenset[BusinessExceptionType]] = frozenset(
    exception_type for spec in _RULE_SPECS for exception_type in spec.exception_types
)


class BlockerDecisionPolicy:
    """Pure policy lookup that cannot resolve, cancel, or resume an exception."""

    def evaluate_open_exception(
        self, policy_input: OpenBlockerDecisionInput
    ) -> tuple[BlockerDecisionMetadata, ...]:
        return tuple(
            self._evaluate_code(policy_input=policy_input, blocker_code=blocker_code)
            for blocker_code in policy_input.blocker_codes
        )

    def auto_resolved_note(
        self, policy_input: AutoResolvedDecisionInput
    ) -> BlockerDecisionMetadata:
        required = frozenset(
            {
                BlockerMinimumInput.CURRENT_DOCUMENT_EVIDENCE,
                BlockerMinimumInput.EQUIVALENT_NORMALIZED_VALUES,
            }
        )
        if not required.issubset(policy_input.available_inputs):
            raise ValueError("auto-resolution note requires proved equivalent document values")
        return BlockerDecisionMetadata(
            blocker_code="EQUIVALENT_DOCUMENT_VALUES_AUTO_CONFIRMED",
            classification=BlockerDecisionClassification.AUTO_RESOLVED_WITH_NOTE,
            policy_version=BLOCKER_DECISION_POLICY_VERSION,
            rule_version="BPD-NONBLOCKING-AUTO-CONFIRM-1",
            owner=BlockerDecisionOwner.DOCUMENT_REVIEW_OWNER,
            minimum_inputs=tuple(sorted(required, key=str)),
            permitted_actions=(BlockerDecisionAction.RETAIN_AUTO_CONFIRM_NOTE,),
            currently_available_actions=(BlockerDecisionAction.RETAIN_AUTO_CONFIRM_NOTE,),
            resume_stage=None,
            resume_transition=ResumeTransition.RETAIN_NOTE_WITHOUT_WORKFLOW_CHANGE,
            resume_ready=True,
            invalidated_dependencies=(),
            explanation=(
                "The owning document workflow already proved normalized value equivalence and "
                "auto-confirmed the document; this API records metadata only."
            ),
            unknowns=(),
        )

    def continue_with_warning(
        self, policy_input: ContinueWithWarningDecisionInput
    ) -> BlockerDecisionMetadata:
        required = frozenset({BlockerMinimumInput.CURRENT_READINESS_WARNING})
        if not required.issubset(policy_input.available_inputs):
            raise ValueError("warning continuation requires an existing readiness warning")
        return BlockerDecisionMetadata(
            blocker_code=policy_input.rule.value,
            classification=BlockerDecisionClassification.CONTINUE_WITH_WARNING,
            policy_version=BLOCKER_DECISION_POLICY_VERSION,
            rule_version=f"BPD-READINESS-{policy_input.rule.value}-1",
            owner=BlockerDecisionOwner.POLICY_OWNER,
            minimum_inputs=tuple(sorted(required, key=str)),
            permitted_actions=(BlockerDecisionAction.RETAIN_READINESS_WARNING,),
            currently_available_actions=(BlockerDecisionAction.RETAIN_READINESS_WARNING,),
            resume_stage=AutomationStage.READINESS,
            resume_transition=ResumeTransition.RETAIN_NOTE_WITHOUT_WORKFLOW_CHANGE,
            resume_ready=True,
            invalidated_dependencies=(),
            explanation=(
                "The existing readiness owner already permits continuation with this retained "
                "warning; the decision record does not authorize a transition."
            ),
            unknowns=(),
        )

    def _evaluate_code(
        self,
        *,
        policy_input: OpenBlockerDecisionInput,
        blocker_code: str,
    ) -> BlockerDecisionMetadata:
        spec = _RULE_INDEX.get(blocker_code)
        if spec is None:
            return _unknown_decision(policy_input.exception_type, blocker_code)
        if policy_input.exception_type not in spec.exception_types:
            return _unknown_decision(
                policy_input.exception_type,
                blocker_code,
                unknown="EXCEPTION_TYPE_BLOCKER_CODE_MISMATCH",
            )

        permitted_actions = spec.permitted_actions
        if spec.use_resolution_actions:
            translated = _translate_resolution_actions(policy_input.available_resolution_actions)
            permitted_actions = tuple(
                action for action in spec.permitted_actions if action in translated
            )
        currently_available = tuple(
            action for action in permitted_actions if action in policy_input.available_actions
        )
        if spec.use_resolution_actions:
            currently_available = permitted_actions
        classification = spec.classification
        unknowns = spec.unknowns
        if (
            spec.classification == BlockerDecisionClassification.USER_ACTION_REQUIRED
            and not permitted_actions
        ):
            classification = BlockerDecisionClassification.HARD_STOP
            permitted_actions = (BlockerDecisionAction.ESCALATE_TO_OWNER,)
            currently_available = ()
            unknowns = (*unknowns, "NO_AUTHORIZED_RESOLUTION_ACTION_AVAILABLE")

        required_inputs = frozenset(spec.minimum_inputs)
        resume_ready = (
            classification == BlockerDecisionClassification.USER_ACTION_REQUIRED
            and spec.resume_transition != ResumeTransition.NO_AUTOMATIC_RESUME
            and required_inputs.issubset(policy_input.available_inputs)
            and bool(currently_available)
        )
        return BlockerDecisionMetadata(
            blocker_code=blocker_code,
            exception_type=policy_input.exception_type,
            classification=classification,
            policy_version=BLOCKER_DECISION_POLICY_VERSION,
            rule_version=spec.rule_version,
            owner=spec.owner,
            minimum_inputs=spec.minimum_inputs,
            permitted_actions=permitted_actions,
            currently_available_actions=currently_available,
            resume_stage=spec.resume_stage,
            resume_transition=spec.resume_transition,
            resume_ready=resume_ready,
            invalidated_dependencies=spec.invalidated_dependencies,
            explanation=spec.explanation,
            unknowns=unknowns,
        )


def _translate_resolution_actions(
    actions: frozenset[ExceptionResolutionAction],
) -> frozenset[BlockerDecisionAction]:
    translations = {
        ExceptionResolutionAction.KEEP_REGISTRY_VALUE: (BlockerDecisionAction.KEEP_REGISTRY_VALUE),
        ExceptionResolutionAction.USE_DOCUMENT_VALUE: (BlockerDecisionAction.USE_DOCUMENT_VALUE),
        ExceptionResolutionAction.REQUEST_ADDITIONAL_INFORMATION: (
            BlockerDecisionAction.REQUEST_ADDITIONAL_INFORMATION
        ),
    }
    return frozenset(translations[action] for action in actions)


def _unknown_decision(
    exception_type: BusinessExceptionType,
    blocker_code: str,
    *,
    unknown: str = "UNMAPPED_BLOCKER_CODE",
) -> BlockerDecisionMetadata:
    return BlockerDecisionMetadata(
        blocker_code=blocker_code,
        exception_type=exception_type,
        classification=BlockerDecisionClassification.HARD_STOP,
        policy_version=BLOCKER_DECISION_POLICY_VERSION,
        rule_version="BPD-UNKNOWN-1",
        owner=BlockerDecisionOwner.POLICY_OWNER,
        minimum_inputs=(
            BlockerMinimumInput.CURRENT_CASE_VERSION,
            BlockerMinimumInput.CURRENT_EXCEPTION_VERSION,
        ),
        permitted_actions=(BlockerDecisionAction.ESCALATE_TO_OWNER,),
        currently_available_actions=(BlockerDecisionAction.ESCALATE_TO_OWNER,),
        resume_stage=None,
        resume_transition=ResumeTransition.NO_AUTOMATIC_RESUME,
        resume_ready=False,
        invalidated_dependencies=tuple(InvalidatedDependency),
        explanation=(
            "No versioned POC rule matches this blocker; identity, ownership, authorization, "
            "and target-write safety remain blocking."
        ),
        unknowns=(unknown,),
    )

# Descriptive catalogue metadata lives beside the existing policy. It does not
# participate in authorization, persistence, exception resolution, or progression.
@dataclass(frozen=True)
class BlockerActionPath:
    action: BlockerDecisionAction
    browser_control: str | None
    backend_owner: str | None
    current_action_predicate: str
    no_action_reason: str
    capability: Capability | None = None
    roles: tuple[Role, ...] = ()
    backend_source: str | None = None
    browser_source: str | None = None


@dataclass(frozen=True)
class BlockerCatalogueEntry:
    code: str
    exception_types: tuple[BusinessExceptionType, ...]
    domain_stage: str
    classification: str
    policy_classification: BlockerDecisionClassification
    rule_version: str
    owner: BlockerDecisionOwner
    explanation: str
    required_inputs: tuple[BlockerMinimumInput, ...]
    declared_actions: tuple[BlockerDecisionAction, ...]
    action_paths: tuple[BlockerActionPath, ...]
    current_action_predicate: str
    no_action_reason: str
    resume_stage: AutomationStage | None
    resume_transition: ResumeTransition
    invalidated_dependencies: tuple[InvalidatedDependency, ...]
    auto_resume: str
    external_dependency: str
    local_demo_scenario: str
    test_coverage: tuple[str, ...]


@dataclass(frozen=True)
class UnknownBlockerGuidance:
    code: str
    classification: str = "HARD_STOP"
    action_paths: tuple[BlockerActionPath, ...] = ()
    resume_transition: ResumeTransition = ResumeTransition.NO_AUTOMATIC_RESUME
    no_action_reason: str = (
        "An unknown technical/provider code has no authorized local corrective action or "
        "automatic retry. Retain the sanitized code and correlation/history evidence for "
        "the owning operator; never infer a business waiver or replay a target write."
    )


_CASE_ROLES = tuple(
    role
    for role, capabilities in ROLE_CAPABILITIES.items()
    if Capability.CASE_ACCESS in capabilities
)
_ZERO_TOUCH_SOURCE = "apps/backend/app/services/zero_touch_orchestration.py"
_CASE_DETAIL_SOURCE = "apps/frontend/src/pages/CaseDetail.tsx"
_CASE_SCOPE = (
    "Authenticated CASE_ACCESS actor in the case team (Director may use CASE_GLOBAL); "
    "backend reauthorization inside the owning lock; current expected revisions; "
    "no completed case, target confirmation, target result, or frozen submission."
)


def _local_action(
    action: BlockerDecisionAction,
    control: str,
    owner: str,
    predicate: str,
    absence: str,
) -> BlockerActionPath:
    return BlockerActionPath(
        action=action,
        browser_control=control,
        backend_owner=owner,
        current_action_predicate=f"{_CASE_SCOPE} {predicate}",
        no_action_reason=absence,
        capability=Capability.CASE_ACCESS,
        roles=_CASE_ROLES,
        backend_source=_ZERO_TOUCH_SOURCE,
        browser_source=_CASE_DETAIL_SOURCE,
    )


def _unavailable_action(
    action: BlockerDecisionAction,
    reason: str,
    *,
    owner: str | None = None,
    capability: Capability | None = None,
) -> BlockerActionPath:
    return BlockerActionPath(
        action=action,
        browser_control=None,
        backend_owner=owner,
        current_action_predicate="No browser mutation is implemented for this declared action.",
        no_action_reason=reason,
        capability=capability,
        roles=tuple(
            role for role, capabilities in ROLE_CAPABILITIES.items()
            if capability is not None and capability in capabilities
        ),
    )


_ACTION_PATHS: Final[Mapping[BlockerDecisionAction, BlockerActionPath]] = MappingProxyType({
    BlockerDecisionAction.CONFIRM_EXISTING_GOLDTIER_CUSTOMER: _local_action(
        BlockerDecisionAction.CONFIRM_EXISTING_GOLDTIER_CUSTOMER,
        "Registry verification > Confirm existing GoldTier customer",
        "ZeroTouchOrchestrator.confirm_existing_customer > "
        "ClmOrchestrationService.confirm_existing_customer",
        "Creator-only CASE_ACCESS; one retained incomplete Sandbox candidate, matching legal "
        "name and no known identity contradiction; exact request/automation/CLM/case versions "
        "and a rationale. The server derives the provider ID. Confirmation makes no target call.",
        "Unavailable for stale/frozen cases, conflicts, multiple candidates, unsupported provider "
        "identity or prior target execution. Continue evidence review separately after recording.",
    ),
    BlockerDecisionAction.CORRECT_INITIAL_IDENTITY: _local_action(
        BlockerDecisionAction.CORRECT_INITIAL_IDENTITY,
        "Registry identity > IdentityCorrectionForm > verify/correct identity",
        "ZeroTouchOrchestrator.repair_initial_identity_and_recheck > "
        "OnboardingService.repair_initial_identity_and_recheck",
        "Only the server-bound case creator may decide evidence. Use registry-identity for "
        "a retained registry/UEN issue: eligible SG UEN is verified "
        "before canonical mutation. DOCUMENT choice requires current document ID/event count, "
        "eligible non-rejected UEN and sufficient reviewed/confident field. Initial missing "
        "identity uses identity-search-recheck. Histories must each have room below 16 entries.",
        "Unavailable when identity is frozen, versions/history are stale/full, the chosen "
        "document is unusable, or registry verification cannot validate the supplied UEN.",
    ),
    BlockerDecisionAction.RUN_READ_ONLY_SEARCH_RECHECK: _local_action(
        BlockerDecisionAction.RUN_READ_ONLY_SEARCH_RECHECK,
        "Registry identity > IdentityCorrectionForm > identity Search recheck",
        "ZeroTouchOrchestrator.repair_initial_identity_and_recheck",
        "Only the server-bound case creator may revise identity. identity-search-recheck "
        "requires a retained completed/failed/review Search checkpoint "
        "or INITIAL_IDENTITY_INCOMPLETE with no initial identity. It is a bounded read-only "
        "Search, not candidate confirmation or target approval.",
        "No recheck when checkpoint/initial-identity guard, frozen-state, history capacity "
        "or expected versions fail; provider failure is not NO_MATCH.",
    ),
    BlockerDecisionAction.RESOLVE_JURISDICTION_EVIDENCE: _local_action(
        BlockerDecisionAction.RESOLVE_JURISDICTION_EVIDENCE,
        "Registry identity > IdentityCorrectionForm > explicit SG correction",
        "ZeroTouchOrchestrator.repair_initial_identity_and_recheck",
        "Only the server-bound case creator may revise identity. Only explicit SG correction "
        "can be verified via registry-identity; "
        "the operator must provide eligible UEN/name/country. No source precedence is inferred.",
        "No arbitrary-jurisdiction resolver or unsupported registry route is available; "
        "an unresolved non-SG case remains blocked.",
    ),
    BlockerDecisionAction.UPLOAD_DOCUMENT: _local_action(
        BlockerDecisionAction.UPLOAD_DOCUMENT,
        "Documents & reconciliation > Upload supporting document",
        "ZeroTouchOrchestrator.intake_document / start",
        "PENDING_INPUTS or _allows_retained_evidence_intake, or the guarded pre-confirmation "
        "OWNERSHIP review; required failed-document reuploads must be resolved first. "
        "Pending intake exposes the exact Continue/Start action; upload alone is not start.",
        "Intake closes outside its owning stage; invalid media is rejected before extraction.",
    ),
    BlockerDecisionAction.UPLOAD_REPLACEMENT_DOCUMENT: _local_action(
        BlockerDecisionAction.UPLOAD_REPLACEMENT_DOCUMENT,
        "Documents & reconciliation > DocumentEvidencePanel > Replace document / targeted reupload",
        "ZeroTouchOrchestrator.replace_document / retry_intake_document",
        "Current non-superseded document at DOCUMENT review, or the exact interrupted intake "
        "record via targeted reupload; server validates evidence and refreshes checkpoints.",
        "No replacement of historical evidence or unrelated record during interrupted intake; "
        "failed replacement exposes targeted reupload/Continue instead of silently progressing.",
    ),
    BlockerDecisionAction.COMPLETE_DOCUMENT_REVIEW: _local_action(
        BlockerDecisionAction.COMPLETE_DOCUMENT_REVIEW,
        "Documents & reconciliation > DocumentEvidencePanel > review required field",
        "ZeroTouchOrchestrator.review_document_field > DocumentProcessingService.review_field",
        "Only the server-bound case creator may decide evidence. Current pending field at "
        "PENDING_INPUTS/DOCUMENT review or guarded OWNERSHIP review; "
        "the document owner permits the chosen confirm/correct/reject decision. Final identical "
        "review is idempotent; low confidence/missing value cannot authorize source selection.",
        "Unverifiable/rejected evidence requires replacement; stale or superseded document "
        "review cannot mutate the current case.",
    ),
    **{
        action: _local_action(
            action,
            "Documents & reconciliation > current discrepancy decision",
            "ZeroTouchOrchestrator.resolve_exception > ReconciliationService.resolve_discrepancy",
            "Only the server-bound case creator may decide evidence. OPEN DOCUMENT exception "
            "with current automation version, evidence version/digest "
            "and discrepancy fingerprint; action must be in exception.available_actions. "
            "Each decision is field-bound; no silent winner or blanket precedence.",
            "No value-selection action for unverifiable/invalid evidence; absent authorized "
            "resolution actions leaves the exception hard-stopped.",
        )
        for action in (
            BlockerDecisionAction.KEEP_REGISTRY_VALUE,
            BlockerDecisionAction.USE_DOCUMENT_VALUE,
            BlockerDecisionAction.REQUEST_ADDITIONAL_INFORMATION,
        )
    },
    BlockerDecisionAction.PROVIDE_CORRECTED_OWNERSHIP_EVIDENCE: _local_action(
        BlockerDecisionAction.PROVIDE_CORRECTED_OWNERSHIP_EVIDENCE,
        "Ownership & UBO > ManualOwnershipEvidenceForm > submit reviewed declaration",
        "ZeroTouchOrchestrator.submit_manual_ownership_evidence > "
        "OwnershipAnalysisService.replace_review_required_source",
        "Only the server-bound case creator may decide evidence. WAITING_FOR_REVIEW with "
        "current REVIEW_REQUIRED or ANALYZED analysis; backend ownership_edit_authorized "
        "controls calculable edits before target intent/submission. Provide rationale and "
        "current case/document/evidence versions, explicit source selection and structured "
        "parties/relationships. Preserve original evidence and receipt; Decimal engine "
        "recalculates and stale readiness/final confirmation is invalidated.",
        "No generic skip/retry; absent current reviewed evidence, stale analysis, frozen "
        "target state or unsupported declaration stays blocking.",
    ),
    BlockerDecisionAction.SELECT_TARGET_CLASSIFICATION: _local_action(
        BlockerDecisionAction.SELECT_TARGET_CLASSIFICATION,
        "Classification & readiness > TargetClassificationPanel > save classification",
        "ZeroTouchOrchestrator.bind_target_classification > "
        "OnboardingService.bind_goldtier_case_classification",
        "Backend target_classification exposes current case-bound editable vocabulary values; "
        "expected automation/case revisions and valid selected customer type/segment are required.",
        "Invalid vocabulary and frozen/confirmed/submitted state cannot be overridden.",
    ),
    BlockerDecisionAction.CONFIRM_FROZEN_TARGET_SUBMISSION: _local_action(
        BlockerDecisionAction.CONFIRM_FROZEN_TARGET_SUBMISSION,
        "Review & Send > confirm reviewed target dispatch",
        "ZeroTouchOrchestrator.confirm_target_dispatch > OnboardingService.confirm_target_dispatch",
        "Current readiness, review digest, automation/CLM/case revisions and required "
        "document/classification evidence; confirmation-time Search must satisfy resolver rules. "
        "Changed Search/plan returns a new explicit review. Review & Send is this application's "
        "final human approval; downstream GoldTier approval is outside this workflow.",
        "No confirmation while an authoritative prerequisite is unresolved, stale, or invalid.",
    ),
    BlockerDecisionAction.FINALIZE_RETAINED_TARGET_OUTCOME: BlockerActionPath(
        action=BlockerDecisionAction.FINALIZE_RETAINED_TARGET_OUTCOME,
        browser_control="Target preparation / submission state > Complete safe recovery",
        backend_owner="ZeroTouchOrchestrator.start / _advance_locked_impl > "
        "ClmOrchestrationService.submit > OnboardingService.finalize_recorded_execution",
        current_action_predicate="CASE_ACCESS and current case scope; status=RECOVERY_PENDING "
        "with retained target outcome. The owning ledger permits finalization without replay.",
        no_action_reason="No safe finalization when retained outcome is absent or uncertain; "
        "this control never reconstructs/replays an attempted write.",
        capability=Capability.CASE_ACCESS,
        roles=_CASE_ROLES,
        backend_source=_ZERO_TOUCH_SOURCE,
        browser_source=_CASE_DETAIL_SOURCE,
    ),
    BlockerDecisionAction.WAIT_FOR_CURRENT_PROCESSING: _unavailable_action(
        BlockerDecisionAction.WAIT_FOR_CURRENT_PROCESSING,
        "In-flight document processing is not a retry/waiver. Wait for the owner to finish; "
        "an interrupted record needs its explicit targeted reupload path.",
        owner="DocumentProcessingService",
    ),
    BlockerDecisionAction.RERUN_OWNERSHIP_ANALYSIS: _unavailable_action(
        BlockerDecisionAction.RERUN_OWNERSHIP_ANALYSIS,
        "No independent browser rerun exists for this declared action. A valid reviewed "
        "manual declaration invokes the existing Decimal engine through its owning mutation.",
        owner="OwnershipAnalysisService",
    ),
    BlockerDecisionAction.PROVIDE_REGISTRY_EVIDENCE: _unavailable_action(
        BlockerDecisionAction.PROVIDE_REGISTRY_EVIDENCE,
        "No direct registry-evidence upload/override exists. Same-case identity verification "
        "cannot manufacture missing registry ownership/provider evidence.",
        owner="RegistryAcquisitionCoordinator",
    ),
    BlockerDecisionAction.ENABLE_SUPPORTED_REGISTRY_PROVIDER: _unavailable_action(
        BlockerDecisionAction.ENABLE_SUPPORTED_REGISTRY_PROVIDER,
        "Only SG ACRA is implemented; no browser provider-enablement mutation exists.",
    ),
    BlockerDecisionAction.REVIEW_ENTITY_IDENTITY: _unavailable_action(
        BlockerDecisionAction.REVIEW_ENTITY_IDENTITY,
        "No advisory-candidate confirmation/manual target-ID assignment exists. The separate "
        "bounded identity/Search correction may be used only when its own guards authorize it.",
    ),
    BlockerDecisionAction.REVIEW_MOCK_RISK: _unavailable_action(
        BlockerDecisionAction.REVIEW_MOCK_RISK,
        "Sponsor risk-review/waiver policy is unresolved; no local risk approval or waiver exists.",
    ),
    BlockerDecisionAction.VERIFY_TARGET_OUTCOME_WITHOUT_REPLAY: _unavailable_action(
        BlockerDecisionAction.VERIFY_TARGET_OUTCOME_WITHOUT_REPLAY,
        "No provider-verification browser form is implemented. The target-recovery API requires "
        "Director TARGET_RECOVERY, retained submission/ledger and verified provider evidence; "
        "it never permits replay. External verification is outside this offline Slice C.",
        owner="OnboardingService.recover_uncertain_shell_from_provider / "
        "recover_uncertain_policy_from_provider",
        capability=Capability.TARGET_RECOVERY,
    ),
    BlockerDecisionAction.DIAGNOSE_PROVIDER_VALIDATION: _unavailable_action(
        BlockerDecisionAction.DIAGNOSE_PROVIDER_VALIDATION,
        "No local provider diagnosis/target retry mutation exists; inspect sanitized retained "
        "outcome and obtain the owner's contract/evidence decision.",
    ),
    BlockerDecisionAction.ESCALATE_TO_OWNER: _unavailable_action(
        BlockerDecisionAction.ESCALATE_TO_OWNER,
        "Escalation is descriptive guidance, not an in-product action, authorization, or waiver.",
    ),
})

# These are documentation categories only. Durable metadata keeps its existing enum.
_OPERATOR_REVIEW_RULES = frozenset({
    "BPD-REGISTRY-EVIDENCE-1",
    "BPD-DOCUMENT-REVIEW-1",
    "BPD-RECONCILIATION-CONFLICT-1",
    "BPD-ENTITY-REVIEW-1",
    "BPD-EXISTING-PARTY-1",
})
_RULE_SCENARIOS: Final[Mapping[str, str]] = MappingProxyType({
    "BPD-IDENTITY-1": "wrong_uen",
    "BPD-REGISTRY-RECTIFICATION-1": "registry_incomplete",
    "BPD-CANONICAL-INCOMPLETE-1": "canonical_incomplete",
    "BPD-JURISDICTION-1": "jurisdiction",
    "BPD-REGISTRY-PROVIDER-1": "unsupported_registry",
    "BPD-REGISTRY-EVIDENCE-1": "registry_evidence_missing",
    "BPD-REGISTRY-REVIEW-1": "registry_review",
    "BPD-REGISTRY-FAILURE-1": "registry_failure",
    "BPD-DOCUMENT-REQUIRED-1": "document_required",
    "BPD-DOCUMENT-REPLACEMENT-1": "document_replacement",
    "BPD-DOCUMENT-REVIEW-1": "document_review",
    "BPD-DOCUMENT-PROCESSING-1": "document_processing",
    "BPD-RECONCILIATION-CONFLICT-1": "document_discrepancy",
    "BPD-RECONCILIATION-INVALID-1": "reconciliation_invalid",
    "BPD-OWNERSHIP-REQUIRED-1": "ownership",
    "BPD-OWNERSHIP-REVIEW-1": "ownership",
    "BPD-OWNERSHIP-FAILURE-1": "ownership_failure",
    "BPD-SEARCH-AMBIGUITY-2": "search_review",
    "BPD-SEARCH-FAILURE-1": "search_failure",
    "BPD-ENTITY-REVIEW-1": "advisory_review",
    "BPD-MOCK-RISK-1": "risk_review",
    "BPD-TARGET-CLASSIFICATION-1": "classification",
    "BPD-TARGET-CONFIRMATION-1": "confirmation",
    "BPD-EXISTING-PARTY-1": "existing_party",
    "BPD-TARGET-PARTIAL-1": "target_partial",
    "BPD-TARGET-CONTRACT-1": "target_contract",
    "BPD-TARGET-UNCERTAIN-1": "target_uncertain",
    "BPD-TARGET-FINALIZATION-1": "target_finalization",
})
_POLICY_TEST = "apps/backend/tests/test_blocker_decision_policy.py"
_CATALOGUE_TEST = "apps/backend/tests/test_slice_c_blocker_catalogue.py"
_ORCHESTRATION_TEST = "apps/backend/tests/test_zero_touch_orchestration.py"
_SCENARIO_TESTS: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType({
    "wrong_uen": (
        "apps/backend/tests/test_phase24_identity.py",
        "apps/frontend/e2e/phase24-identity.e2e.ts",
        "apps/frontend/e2e/slice-c-recovery.e2e.ts",
    ),
    "registry_incomplete": ("apps/backend/tests/test_phase24_identity.py",),
    "jurisdiction": ("apps/backend/tests/test_phase09_jurisdiction_gateway.py",),
    "document_required": (_ORCHESTRATION_TEST, "apps/frontend/e2e/authenticated-zero-touch.e2e.ts"),
    "document_replacement": (
        _ORCHESTRATION_TEST, "apps/frontend/e2e/authenticated-zero-touch.e2e.ts",
    ),
    "document_review": (_ORCHESTRATION_TEST, "apps/frontend/e2e/slice-c-recovery.e2e.ts"),
    "document_discrepancy": (
        _ORCHESTRATION_TEST,
        "apps/backend/tests/test_phase11_reconciliation.py",
        "apps/frontend/e2e/zero-touch-exception.e2e.ts",
        "apps/frontend/e2e/slice-c-recovery.e2e.ts",
    ),
    "ownership": (
        _ORCHESTRATION_TEST,
        "apps/backend/tests/test_phase24_ownership_evidence.py",
        "apps/backend/tests/test_slice_b_registry_demo.py",
        "apps/frontend/e2e/slice-b-registry-demo.e2e.ts",
        "apps/frontend/e2e/authenticated-zero-touch.e2e.ts",
    ),
    "search_review": (_ORCHESTRATION_TEST, "apps/frontend/e2e/authenticated-zero-touch.e2e.ts"),
    "search_failure": (_ORCHESTRATION_TEST, "apps/frontend/e2e/slice-c-recovery.e2e.ts"),
    "classification": (_ORCHESTRATION_TEST, "apps/frontend/e2e/slice-c-recovery.e2e.ts"),
    "confirmation": (
        _ORCHESTRATION_TEST,
        "apps/frontend/e2e/slice-c-recovery.e2e.ts",
        "apps/frontend/e2e/slice-b-registry-demo.e2e.ts",
    ),
    "target_finalization": (_ORCHESTRATION_TEST,),
    "existing_party": (_ORCHESTRATION_TEST,),
})


def blocker_catalogue() -> tuple[BlockerCatalogueEntry, ...]:
    """Describe every supported OPEN rule without declaring a current case action.

    All decision facts come from _RULE_SPECS through its validated index. Paths are
    traceable documentation, not predicates executed as a second workflow owner.
    """
    entries = []
    for code, spec in sorted(_RULE_INDEX.items()):
        scenario = _RULE_SCENARIOS[spec.rule_version]
        classification = spec.classification.value
        if spec.rule_version in _OPERATOR_REVIEW_RULES:
            classification = "OPERATOR_REVIEW_REQUIRED"
        if spec.rule_version == "BPD-TARGET-FINALIZATION-1":
            classification = "AUTOMATIC_RECOVERY"
        paths = tuple(_ACTION_PATHS[action] for action in spec.permitted_actions)
        controls = tuple(path for path in paths if path.browser_control is not None)
        automatic = (
            "No. A required local action is not implemented; retain the blocker."
            if not controls
            else "Conditional. The owning mutation re-evaluates current evidence and automatically "
            "continues when its predicates pass; otherwise the exact remaining action is shown."
        )
        if scenario == "document_required":
            automatic = "No on initial upload alone. Use the authorized Continue/Start action."
        if scenario == "target_finalization":
            automatic = (
                "Bounded automatic finalization attempts use the retained outcome without replay. "
                "If RECOVERY_PENDING remains, use Complete safe recovery; no replay occurs."
            )
        external = (
            "Yes. Required provider/contract evidence remains unavailable; no local waiver."
            if spec.classification == BlockerDecisionClassification.EXTERNAL_DEPENDENCY
            else "This catalogue authorizes no external call. Mock/LOCAL recovery stays local; "
            "registry/Search correction uses the configured provider under its existing guards."
        )
        if scenario == "target_uncertain":
            external = (
                "Yes. Exact verified provider evidence is required before the Director "
                "TARGET_RECOVERY API can retain an outcome; no browser verification or replay."
            )
        entries.append(BlockerCatalogueEntry(
            code=code,
            exception_types=tuple(sorted(spec.exception_types, key=str)),
            domain_stage=(
                "REGISTRY > GOLDTIER_SEARCH"
                if scenario in {"wrong_uen", "registry_incomplete", "jurisdiction"}
                else spec.resume_stage.value if spec.resume_stage is not None else "TARGET_CONTRACT"
            ),
            classification=classification,
            policy_classification=spec.classification,
            rule_version=spec.rule_version,
            owner=spec.owner,
            explanation=spec.explanation,
            required_inputs=spec.minimum_inputs,
            declared_actions=spec.permitted_actions,
            action_paths=paths,
            current_action_predicate=(
                "Declared capability is not a currently valid action. Decision metadata intersects "
                "declared actions with owner-supplied available actions (or current reconciliation "
                "allowed_actions). Required inputs control resume_ready. Browser mutations also "
                "require the current backend summary/action and the owning guards below."
            ),
            no_action_reason=(
                "When those current guards fail, no mutation/automatic resume is authorized. "
                "See each declared action's absence reason; do not invent a retry or waiver."
            ),
            resume_stage=spec.resume_stage,
            resume_transition=spec.resume_transition,
            invalidated_dependencies=spec.invalidated_dependencies,
            auto_resume=automatic,
            external_dependency=external,
            local_demo_scenario=scenario,
            test_coverage=(_POLICY_TEST, _CATALOGUE_TEST, *_SCENARIO_TESTS.get(scenario, ())),
        ))
    return tuple(entries)


def unknown_blocker_guidance(code: str) -> UnknownBlockerGuidance:
    """Constrain an unknown safe code; never accept or repeat free-text failure details."""
    safe_code = TypeAdapter(SafeBlockerCode).validate_python(code)
    if safe_code in SUPPORTED_BLOCKER_CODES:
        raise ValueError("supported blocker code must use its catalogue entry")
    return UnknownBlockerGuidance(code=safe_code)
