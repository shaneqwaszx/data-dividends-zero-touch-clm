"""Director-managed workflow definitions and case-bound field collection (D-123).

These records are additive. They never replace the automation stages, and collected
answers never reach ownership, reconciliation or GoldTier mapping.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

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

WorkflowItemId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")]
WorkflowLabel = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
]
WorkflowTag = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)
]


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


class WorkflowStage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_id: WorkflowItemId
    name: WorkflowLabel
    fields: tuple[WorkflowField, ...] = Field(default=(), max_length=32)
    # Onboarding only: the existing stage this one is displayed after.
    after_node_id: str | None = Field(default=None, pattern=r"^[A-Z0-9_]+$", max_length=64)


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
    started_by: str | None = Field(default=None, max_length=64)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def belongs_to_a_case_or_a_company(self) -> WorkflowRun:
        if (self.case_id is None) == (self.company is None):
            raise ValueError("a run needs exactly one of a case or a company")
        return self

    @property
    def is_onboarding(self) -> bool:
        return self.workflow_id == ONBOARDING_WORKFLOW_ID

    @property
    def confirmed_stage_ids(self) -> frozenset[str]:
        return frozenset(item.stage_id for item in self.confirmations)

    @property
    def is_complete(self) -> bool:
        return all(stage.stage_id in self.confirmed_stage_ids for stage in self.stages)
