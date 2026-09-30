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

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
        codes=frozenset({"INITIAL_IDENTITY_INCOMPLETE", "REGISTRY_IDENTIFIER_NOT_ELIGIBLE"}),
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
        unknowns=("LEGAL_UBO_DETERMINATION_NOT_IMPLEMENTED",),
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
        rule_version="BPD-SEARCH-AMBIGUITY-1",
        owner=BlockerDecisionOwner.IDENTITY_REVIEW_OWNER,
        minimum_inputs=(
            BlockerMinimumInput.CURRENT_CANONICAL_IDENTITY,
            BlockerMinimumInput.CURRENT_SEARCH_CHECKPOINT,
        ),
        permitted_actions=(
            BlockerDecisionAction.CORRECT_INITIAL_IDENTITY,
            BlockerDecisionAction.RUN_READ_ONLY_SEARCH_RECHECK,
        ),
        resume_stage=AutomationStage.GOLDTIER_SEARCH,
        resume_transition=ResumeTransition.RECHECK_FROM_STAGE,
        invalidated_dependencies=_IDENTITY_INVALIDATIONS[1:],
        explanation=(
            "Ambiguous target identity requires corrected identity evidence and a new read-only "
            "Search; no candidate is selected automatically."
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
