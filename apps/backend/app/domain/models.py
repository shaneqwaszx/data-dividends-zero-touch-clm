"""Minimal canonical models for the current onboarding vertical slice."""

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowState(StrEnum):
    """Application workflow states exposed to the user."""

    REQUESTED = "REQUESTED"
    REGISTRY_FETCHED = "REGISTRY_FETCHED"
    VALIDATED = "VALIDATED"
    GT_SEARCHED = "GT_SEARCHED"
    GT_SHELL_CREATED = "GT_SHELL_CREATED"
    GT_POLICY_CREATED = "GT_POLICY_CREATED"
    GT_ENRICHED = "GT_ENRICHED"
    COMPLETED = "COMPLETED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAILED = "FAILED"


class EventOutcome(StrEnum):
    """Safe outcome values for case history."""

    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAILED = "FAILED"


class SourceSystem(StrEnum):
    """Business source independent of connector implementation mode."""

    ACRA = "ACRA"


class SourceEnvironment(StrEnum):
    """Environment in which source evidence was obtained."""

    MOCK = "MOCK"
    SANDBOX = "SANDBOX"


class RegisteredAddress(BaseModel):
    """Small canonical address needed by the Phase 01 UI and target mapper."""

    address_line_1: str
    address_line_2: str | None = None
    postal_code: str
    country_code: str = "SG"


class SourceMetadata(BaseModel):
    """Provenance for the canonical entity without retaining a raw payload."""

    source_system: SourceSystem
    environment: SourceEnvironment
    registry_source_link: str
    retrieved_at: datetime


class CanonicalLegalEntity(BaseModel):
    """Minimum source-neutral representation of a Singapore legal entity."""

    registration_number: str
    legal_name: str | None = None
    country_of_incorporation: str | None = None
    party_type: str | None = None
    registration_date: date | None = None
    entity_status: str | None = None
    registered_address: RegisteredAddress | None = None
    source: SourceMetadata


class WorkflowEvent(BaseModel):
    """Audit-safe workflow event; raw corporate payloads are deliberately excluded."""

    sequence: int = Field(ge=1)
    stage: WorkflowState
    outcome: EventOutcome
    timestamp: datetime
    case_id: UUID
    correlation_id: UUID
    code: str | None = None
    message: str


class GoldTierResult(BaseModel):
    """User-facing summary of the mock target result."""

    party_id: str
    shell_status: str
    policy_id: str | None = None
    policy_status: str | None = None
    amend_status: str | None = None


class SafeError(BaseModel):
    """Sanitised application error safe for API and history responses."""

    code: str
    message: str


class OnboardingCase(BaseModel):
    """Canonical aggregate returned by the application-facing API."""

    case_id: UUID
    source_case_id: str
    correlation_id: UUID
    requested_uen: str
    state: WorkflowState
    entity: CanonicalLegalEntity | None = None
    goldtier_result: GoldTierResult | None = None
    events: list[WorkflowEvent] = Field(default_factory=list)
    error: SafeError | None = None
    created_at: datetime
    updated_at: datetime
