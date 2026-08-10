"""Browser-facing API models that exclude internal registry proof references."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.documents import (
    ComparisonStatus,
    DocumentFieldKey,
    DocumentProcessingRecord,
    DocumentProcessingState,
    DocumentProfile,
    DocumentWorkflowEvent,
    FieldReviewStatus,
    IdpEnvironment,
)
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


class BrowserFieldProvenance(BaseModel):
    """Safe source/page metadata without raw provider output."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    provider: str
    environment: IdpEnvironment
    page_number: int | None
    source_reference: str


class BrowserExtractedField(BaseModel):
    """Provider suggestion, comparison, and separately retained human decision."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    field_key: DocumentFieldKey
    original_extracted_value: str | None
    normalized_value: str | None
    confidence: float
    provenance: BrowserFieldProvenance
    canonical_value: str | None
    comparison_status: ComparisonStatus
    review_status: FieldReviewStatus
    reviewed_value: str | None
    reviewed_at: datetime | None
    review_note: str | None


class DocumentProcessingResponse(BaseModel):
    """Document response without bytes, paths, or raw provider evidence."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    case_id: UUID
    document_id: UUID
    correlation_id: UUID
    display_name: str
    media_type: str
    profile: DocumentProfile
    provider_environment: IdpEnvironment | None
    state: DocumentProcessingState
    fields: list[BrowserExtractedField]
    events: list[DocumentWorkflowEvent]
    error: SafeError | None = None
    created_at: datetime
    processed_at: datetime | None = None
    reviewed_at: datetime | None = None
    updated_at: datetime

    @classmethod
    def from_domain(cls, record: DocumentProcessingRecord) -> "DocumentProcessingResponse":
        return cls.model_validate(record)
