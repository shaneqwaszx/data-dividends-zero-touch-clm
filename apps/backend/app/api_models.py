"""Browser-facing API models that exclude internal registry proof references."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.models import (
    GoldTierResult,
    OnboardingCase,
    RegisteredAddress,
    SafeError,
    SourceEnvironment,
    SourceSystem,
    WorkflowEvent,
    WorkflowState,
)


class BrowserSourceMetadata(BaseModel):
    """Source metadata needed by the UI, excluding the internal endpoint reference."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    source_system: SourceSystem
    environment: SourceEnvironment
    retrieved_at: datetime


class BrowserCanonicalLegalEntity(BaseModel):
    """Canonical entity projection safe for browser delivery."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    registration_number: str
    legal_name: str | None = None
    country_of_incorporation: str | None = None
    party_type: str | None = None
    registration_date: date | None = None
    entity_status: str | None = None
    registered_address: RegisteredAddress | None = None
    source: BrowserSourceMetadata


class OnboardingCaseResponse(BaseModel):
    """Application case response with internal proof metadata minimized."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    case_id: UUID
    source_case_id: str
    correlation_id: UUID
    requested_uen: str
    state: WorkflowState
    entity: BrowserCanonicalLegalEntity | None = None
    goldtier_result: GoldTierResult | None = None
    events: list[WorkflowEvent]
    error: SafeError | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, case: OnboardingCase) -> "OnboardingCaseResponse":
        """Project a domain case without serializing its registry source link."""

        return cls.model_validate(case)
