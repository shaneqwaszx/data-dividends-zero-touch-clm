"""Director-managed workflow definitions and case-bound field collection (D-123).

These records are additive. They never replace the automation stages, and collected
answers never reach ownership, reconciliation or GoldTier mapping.

ADR-018 (M3, contract CC-8): optional, add-only ``applies_to`` on stages and fields, and the
run's applicability basis. Every new field defaults to "nothing conditional" and is left out
of dumps while unset, so M1/M2 payloads, content hashes and fixtures are byte-identical.
Pre-M3 readers decode these models with ``extra="forbid"`` and therefore refuse any document
that carries a new key (ADR-018 §2.3, §9): conditional authoring stays behind the enablement
gate (``workflow_governance.CONDITIONAL_APPLICABILITY_ENABLED_DEFAULT`` is False).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.domain.models import SourceEnvironment
from app.domain.registry_legal_form import ConditionalLegalForm

ONBOARDING_WORKFLOW_ID = "corporate-onboarding"
ONBOARDING_USE_CASE = "Onboarding"
MAX_WORKFLOW_VERSIONS = 64
MAX_WORKFLOW_AUDIT_EVENTS = 256
MAX_ANSWER_LENGTH = 512

# The existing onboarding stages a Director may place an added stage after. Final review
# & send is excluded, so an added stage always precedes the send step.
ONBOARDING_ANCHOR_STAGES: tuple[tuple[str, str], ...] = (
    ("CASE_START", "Case created"),
    ("INITIAL_IDENTITY", "Initial identity"),
    ("JURISDICTION", "Jurisdiction"),
    ("GOLDTIER_SEARCH", "Existing-customer search"),
    ("ACRA_REGISTRY", "Registry verification"),
    ("DOCUMENT_IDP", "Document verification"),
    ("RECONCILIATION", "Data reconciliation"),
    ("OWNERSHIP_UBO", "Ownership & UBO"),
    ("ADVISORY", "Risk assessment"),
    ("GOLDTIER_DETAILS", "GoldTier Details & Status"),
)
ONBOARDING_LOCKED_STAGES: tuple[tuple[str, str], ...] = (
    *ONBOARDING_ANCHOR_STAGES,
    ("FINAL_REVIEW_SEND", "Final review & send"),
)
# ADR-018 §2.1 (B2): on onboarding, conditional content is allowed only at the registry stage
# or a later anchor, where the registry basis exists before the stage is reached.
CONDITIONAL_ONBOARDING_ANCHORS: frozenset[str] = frozenset(
    node_id
    for node_id, _ in ONBOARDING_ANCHOR_STAGES[
        [item[0] for item in ONBOARDING_ANCHOR_STAGES].index("ACRA_REGISTRY") :
    ]
)
MAX_APPLIES_TO = len(ConditionalLegalForm) - 1  # the full set is refused: use ALL (None)
# ADR-018 §3.3: ``ever_touched`` holds each stage and field key at most once.
MAX_RUN_TOUCHED_KEYS = 32 * (1 + 32)

WorkflowItemId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")]
WorkflowLabel = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
]
WorkflowTag = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)
]
AppliesTo = tuple[ConditionalLegalForm, ...]


def canonical_applies_to(value: AppliesTo | None) -> AppliesTo | None:
    """ADR-018 §2.1: None is ALL; a set is non-empty, duplicate-free, sorted, not the full set."""

    if value is None:
        return None
    forms = tuple(ConditionalLegalForm(item) for item in value)
    if not forms:
        raise ValueError("applies_to is None (all entities) or a non-empty set")
    if len(set(forms)) != len(forms):
        raise ValueError("applies_to must not repeat a legal form")
    if len(forms) > MAX_APPLIES_TO:
        raise ValueError("applies_to naming every legal form must be All entities (None)")
    return tuple(sorted(forms, key=lambda item: item.value))


def applies_to_includes(outer: AppliesTo | None, inner: AppliesTo | None) -> bool:
    """Whether ``outer`` covers ``inner`` (ALL is the top element)."""

    if outer is None:
        return True
    if inner is None:
        return False
    return set(inner) <= set(outer)


def field_within_stage(stage: AppliesTo | None, field: AppliesTo | None) -> bool:
    """ADR-018 §2.1: a field that names forms names only forms of its stage.

    A field without ``applies_to`` inherits its stage (effective = stage ∩ ALL = stage).
    """

    return field is None or applies_to_includes(stage, field)


def effective_applies_to(stage: AppliesTo | None, field: AppliesTo | None) -> AppliesTo | None:
    """ADR-018 §2.1: the field's effective applicability, stage ∩ field (ALL is the identity)."""

    if stage is None:
        return field
    if field is None:
        return stage
    return tuple(item for item in stage if item in set(field))


def _omit_none(value: object) -> bool:
    return value is None


class WorkflowFieldKind(StrEnum):
    TEXT = "TEXT"
    DATE = "DATE"
    NUMBER = "NUMBER"
    YES_NO = "YES_NO"
    CHOICE = "CHOICE"


class WorkflowCaseSource(StrEnum):
    EXISTING_CASE = "EXISTING_CASE"
    NEW_CASE = "NEW_CASE"


class WorkflowAnswerSource(StrEnum):
    MANUAL = "MANUAL"
    DOCUMENT = "DOCUMENT"
    CASE = "CASE"


class WorkflowField(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    field_id: WorkflowItemId
    label: WorkflowLabel
    kind: WorkflowFieldKind
    required: bool = True
    options: tuple[WorkflowLabel, ...] = Field(default=(), max_length=32)
    autofill: bool = False
    document_label: WorkflowLabel | None = None
    # Which onboarded-case value this field starts with, for existing-case workflows.
    case_data_key: str | None = Field(default=None, pattern=r"^[A-Z_]+$", max_length=40)
    # ADR-018 §2.1: None = ALL (unconditional). Left out of dumps while None (CT-21).
    applies_to: AppliesTo | None = Field(default=None, exclude_if=_omit_none)

    @field_validator("applies_to", mode="after")
    @classmethod
    def _canonical_applies_to(cls, value: AppliesTo | None) -> AppliesTo | None:
        return canonical_applies_to(value)


class WorkflowStage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_id: WorkflowItemId
    name: WorkflowLabel
    fields: tuple[WorkflowField, ...] = Field(default=(), max_length=32)
    # Onboarding only: the existing stage this one is displayed after.
    after_node_id: str | None = Field(default=None, pattern=r"^[A-Z0-9_]+$", max_length=64)
    # ADR-018 §2.1: None = ALL (unconditional). Left out of dumps while None (CT-21).
    applies_to: AppliesTo | None = Field(default=None, exclude_if=_omit_none)

    @field_validator("applies_to", mode="after")
    @classmethod
    def _canonical_applies_to(cls, value: AppliesTo | None) -> AppliesTo | None:
        return canonical_applies_to(value)

    @model_validator(mode="after")
    def _fields_within_stage(self) -> WorkflowStage:
        if any(not field_within_stage(self.applies_to, f.applies_to) for f in self.fields):
            raise ValueError("a field's applies_to must be within its stage's applies_to")
        return self

    @property
    def is_conditional(self) -> bool:
        return self.applies_to is not None or any(f.applies_to is not None for f in self.fields)


class WorkflowVersion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: int = Field(ge=1)
    stages: tuple[WorkflowStage, ...] = Field(max_length=32)
    activated_at: datetime
    activated_by: str = Field(min_length=1, max_length=64)


class WorkflowAuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    occurred_at: datetime
    actor_id: str = Field(min_length=1, max_length=64)
    action: str = Field(min_length=1, max_length=32)
    summary: str = Field(min_length=1, max_length=160)


WORKFLOW_WRITE_NONCE_PATTERN = r"^[0-9a-f]{32}$"


class WorkflowDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workflow_id: WorkflowItemId
    name: WorkflowLabel
    use_case: WorkflowTag
    country: WorkflowTag
    case_source: WorkflowCaseSource = WorkflowCaseSource.EXISTING_CASE
    revision: int = Field(default=1, ge=1)
    draft_stages: tuple[WorkflowStage, ...] = Field(default=(), max_length=32)
    versions: tuple[WorkflowVersion, ...] = Field(default=(), max_length=MAX_WORKFLOW_VERSIONS)
    audit: tuple[WorkflowAuditEvent, ...] = Field(
        default=(), max_length=MAX_WORKFLOW_AUDIT_EVENTS
    )
    created_at: datetime
    updated_at: datetime
    # ADR-017 section 3.2: the per-write nonce of the stored document, carried from the
    # read to the compare-and-set. Backend-only: never in the payload or an API body.
    write_nonce: str | None = Field(
        default=None, pattern=WORKFLOW_WRITE_NONCE_PATTERN, exclude=True
    )
    # ADR-017 section 3.5 (writer release): the stored top-level authoritative active version
    # (0 = none) and the monotonic high-water mark. Backend-only; set only by provisioning,
    # the one-time P2-0 backfill and (from P2-1) governed publication. None = not backfilled.
    stored_active_version: int | None = Field(default=None, ge=0, exclude=True)
    latest_version: int | None = Field(default=None, ge=0, exclude=True)

    @property
    def is_onboarding(self) -> bool:
        return self.workflow_id == ONBOARDING_WORKFLOW_ID

    @property
    def active_version(self) -> WorkflowVersion | None:
        return self.versions[-1] if self.versions else None


class WorkflowAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_id: WorkflowItemId
    field_id: WorkflowItemId
    value: str = Field(min_length=1, max_length=MAX_ANSWER_LENGTH)
    source: WorkflowAnswerSource = WorkflowAnswerSource.MANUAL
    document_id: UUID | None = None
    page_number: int | None = Field(default=None, ge=1, le=500)


class WorkflowStageConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_id: WorkflowItemId
    confirmed_by: str = Field(min_length=1, max_length=64)
    confirmed_at: datetime


class WorkflowCompany(BaseModel):
    """Company details held by a workflow-only case; no onboarding case exists for it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    legal_name: str = Field(min_length=1, max_length=160)
    registration_id: str = Field(min_length=1, max_length=32)
    jurisdiction: str | None = Field(default=None, min_length=2, max_length=3)
    priority: int | None = Field(default=None, ge=1, le=10)
    team_id: str = Field(min_length=1, max_length=64)


class ApplicabilityBasisStatus(StrEnum):
    """ADR-018 §3.2 (B11): bound and classified, not proven correct."""

    REGISTRY_BOUND = "REGISTRY_BOUND"
    UNVERIFIED = "UNVERIFIED"


class ApplicabilityBasisReason(StrEnum):
    REGISTRY_BINDING = "REGISTRY_BINDING"
    NO_ENTITY = "NO_ENTITY"
    NO_BINDING = "NO_BINDING"
    OTHER_FORM = "OTHER_FORM"
    CONFLICTING_CLASSIFICATION = "CONFLICTING_CLASSIFICATION"
    AMBIGUOUS_BINDING = "AMBIGUOUS_BINDING"
    TOO_LATE_TO_NARROW = "TOO_LATE_TO_NARROW"
    NO_CASE_RECORD = "NO_CASE_RECORD"
    READ_FAILED = "READ_FAILED"


class BindingRef(BaseModel):
    """Safe identifiers of a registry evidence binding; never source text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cache_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    cache_revision: int = Field(ge=0)
    bound_to_case_at: datetime


class ApplicabilityBasis(BaseModel):
    """ADR-018 §3.3: the legal-form basis a run's stage copy was resolved with."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    legal_form: ConditionalLegalForm | None  # None when UNVERIFIED
    status: ApplicabilityBasisStatus
    reason: ApplicabilityBasisReason
    source_environment: SourceEnvironment | None = None
    evaluated_at: datetime
    evaluated_from_version: int = Field(ge=1)
    # Onboarding: False until the freeze write (§3.5). Non-onboarding runs are always True.
    frozen: bool
    binding_ref: BindingRef | None = None

    @model_validator(mode="after")
    def _consistent(self) -> ApplicabilityBasis:
        bound = self.status == ApplicabilityBasisStatus.REGISTRY_BOUND
        if bound != (self.legal_form is not None):
            raise ValueError("only a REGISTRY_BOUND basis names a legal form")
        if bound != (self.reason == ApplicabilityBasisReason.REGISTRY_BINDING):
            raise ValueError("REGISTRY_BINDING is the reason of a REGISTRY_BOUND basis only")
        if bound and self.binding_ref is None:
            raise ValueError("a REGISTRY_BOUND basis names its binding")
        return self


class BasisConflict(BaseModel):
    """ADR-018 §3.5 F5/F6: a later binding that disagrees with a frozen REGISTRY_BOUND basis."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    detected_at: datetime
    observed_status: ApplicabilityBasisStatus
    observed_legal_form: ConditionalLegalForm | None = None
    binding_ref: BindingRef | None = None
    escalated_by: str | None = Field(default=None, min_length=1, max_length=64)
    escalated_at: datetime | None = None
    escalation_reason: (
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=10, max_length=240)
        ]
        | None
    ) = None

    @model_validator(mode="after")
    def _escalation_complete(self) -> BasisConflict:
        parts = (self.escalated_by, self.escalated_at, self.escalation_reason)
        if any(item is not None for item in parts) and any(item is None for item in parts):
            raise ValueError("an escalation records who, when and why")
        return self

    @property
    def escalated(self) -> bool:
        return self.escalated_at is not None


class RunItemKey(BaseModel):
    """A stage (``field_id`` None) or a field of a run, for ``ever_touched``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_id: WorkflowItemId
    field_id: WorkflowItemId | None = None


def _omit_empty(value: object) -> bool:
    return not value


class WorkflowRun(BaseModel):
    """Frozen stages and collected answers for one workflow version.

    It belongs to an onboarded case, or holds its own company for a workflow-only case.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    case_id: UUID | None = None
    company: WorkflowCompany | None = None
    workflow_id: WorkflowItemId
    workflow_name: WorkflowLabel
    use_case: WorkflowTag
    workflow_version: int = Field(ge=1)
    stages: tuple[WorkflowStage, ...] = Field(max_length=32)
    answers: tuple[WorkflowAnswer, ...] = Field(default=(), max_length=1024)
    confirmations: tuple[WorkflowStageConfirmation, ...] = Field(default=(), max_length=32)
    revision: int = Field(default=0, ge=0)
    # Set only while a rebased run is in memory: the revision its stored copy has.
    stored_revision: int | None = Field(default=None, exclude=True)
    started_by: str | None = Field(default=None, max_length=64)
    created_at: datetime
    updated_at: datetime
    # ADR-018 §3.3–§3.5. Each is left out of dumps while unset, so M1/M2 runs are unchanged.
    # A run without a basis is UNVERIFIED (every conditional obligation applies).
    applicability_basis: ApplicabilityBasis | None = Field(default=None, exclude_if=_omit_none)
    basis_conflict: BasisConflict | None = Field(default=None, exclude_if=_omit_none)
    # Monotonic: a key is only ever added, even after its answer is cleared (§3.5 F3).
    ever_touched: tuple[RunItemKey, ...] = Field(
        default=(), max_length=MAX_RUN_TOUCHED_KEYS, exclude_if=_omit_empty
    )

    @model_validator(mode="after")
    def belongs_to_a_case_or_a_company(self) -> WorkflowRun:
        if (self.case_id is None) == (self.company is None):
            raise ValueError("a run needs exactly one of a case or a company")
        if len(set(self.ever_touched)) != len(self.ever_touched):
            raise ValueError("ever_touched holds each key once")
        if self.basis_conflict is not None and not (
            self.applicability_basis is not None
            and self.applicability_basis.frozen
            and self.applicability_basis.status == ApplicabilityBasisStatus.REGISTRY_BOUND
        ):
            raise ValueError("only a frozen REGISTRY_BOUND basis can conflict")
        return self

    @property
    def effective_legal_form(self) -> ConditionalLegalForm | None:
        """ADR-018 §3.3 effective basis; None means UNVERIFIED (every condition applies).

        UNVERIFIED before the freeze, the frozen basis after it, and UNVERIFIED permanently once
        a conflict is escalated.
        """

        basis = self.applicability_basis
        if basis is None or not basis.frozen:
            return None
        if self.basis_conflict is not None and self.basis_conflict.escalated:
            return None
        return basis.legal_form

    @property
    def is_onboarding(self) -> bool:
        return self.workflow_id == ONBOARDING_WORKFLOW_ID

    @property
    def confirmed_stage_ids(self) -> frozenset[str]:
        return frozenset(item.stage_id for item in self.confirmations)

    @property
    def is_complete(self) -> bool:
        return all(stage.stage_id in self.confirmed_stage_ids for stage in self.stages)
