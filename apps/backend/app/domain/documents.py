"""Source-neutral document extraction, comparison, and review models."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated
from unicodedata import category
from uuid import UUID

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from app.domain.models import EventOutcome, SafeError


class DocumentProcessingState(StrEnum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REVIEWED = "REVIEWED"
    FAILED = "FAILED"


class DocumentEventType(StrEnum):
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_PROCESSING_STARTED = "DOCUMENT_PROCESSING_STARTED"
    DOCUMENT_PROCESSED = "DOCUMENT_PROCESSED"
    DOCUMENT_REVIEW_REQUIRED = "DOCUMENT_REVIEW_REQUIRED"
    DOCUMENT_FIELD_ACCEPTED = "DOCUMENT_FIELD_ACCEPTED"
    DOCUMENT_FIELD_REJECTED = "DOCUMENT_FIELD_REJECTED"
    DOCUMENT_FIELD_CORRECTED = "DOCUMENT_FIELD_CORRECTED"
    DOCUMENT_REVIEW_COMPLETED = "DOCUMENT_REVIEW_COMPLETED"
    DOCUMENT_AUTO_CONFIRMED = "DOCUMENT_AUTO_CONFIRMED"
    DOCUMENT_EXCEPTION_RESOLVED = "DOCUMENT_EXCEPTION_RESOLVED"
    DOCUMENT_PROCESSING_FAILED = "DOCUMENT_PROCESSING_FAILED"
    DOCUMENT_SUPERSEDED = "DOCUMENT_SUPERSEDED"


class IdpEnvironment(StrEnum):
    MOCK = "MOCK"
    LOCAL = "LOCAL"
    SANDBOX = "SANDBOX"
    LIVE = "LIVE"


def _normalize_safe_provenance(value: object) -> object:
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    if not normalized:
        raise ValueError("provider provenance must not be blank")
    if any(category(character).startswith("C") for character in normalized):
        raise ValueError("provider provenance must not contain control characters")
    return normalized


SafeProviderName = Annotated[
    str,
    BeforeValidator(_normalize_safe_provenance),
    StringConstraints(min_length=1, max_length=64),
]
SafeSourceReference = Annotated[
    str,
    BeforeValidator(_normalize_safe_provenance),
    StringConstraints(min_length=1, max_length=128),
]


class DocumentProfile(StrEnum):
    """Project-defined provisional profile pending sponsor answer Q-003."""

    PROVISIONAL_CORPORATE = "PROVISIONAL_CORPORATE"


class DocumentFieldKey(StrEnum):
    REGISTRATION_NUMBER = "registration_number"
    LEGAL_NAME = "legal_name"
    REGISTERED_ADDRESS = "registered_address"
    COUNTRY_OF_INCORPORATION = "country_of_incorporation"


class ComparisonStatus(StrEnum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    MISSING_FROM_DOCUMENT = "MISSING_FROM_DOCUMENT"
    MISSING_FROM_REGISTRY = "MISSING_FROM_REGISTRY"
    NOT_COMPARABLE = "NOT_COMPARABLE"


class FieldReviewStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CORRECTED = "CORRECTED"


class ReviewDecision(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CORRECTED = "CORRECTED"


class DocumentCompletionMethod(StrEnum):
    AUTO_CONFIRMED = "AUTO_CONFIRMED"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    EXCEPTION_RESOLVED = "EXCEPTION_RESOLVED"


class DocumentAutoClearBlocker(StrEnum):
    TEXT_UNAVAILABLE = "DOCUMENT_TEXT_UNAVAILABLE"
    SOURCE_CONFLICT = "DOCUMENT_SOURCE_CONFLICT"
    LOW_CONFIDENCE = "DOCUMENT_LOW_CONFIDENCE"
    REQUIRED_FIELD_MISSING = "DOCUMENT_REQUIRED_FIELD_MISSING"
    REVIEW_STATE_INVALID = "DOCUMENT_REVIEW_STATE_INVALID"


class DocumentAutoClearAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    eligible: bool
    blockers: tuple[DocumentAutoClearBlocker, ...] = Field(default_factory=tuple)


class DocumentSourceConflictResolution(BaseModel):
    """Explicit journey decision; extracted and reviewed evidence remains immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    field_key: DocumentFieldKey
    action: str = Field(pattern=r"^KEEP_REGISTRY_VALUE$")
    registry_value: str = Field(min_length=1, max_length=512)
    resolved_at: datetime


class FieldProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: SafeProviderName
    environment: IdpEnvironment
    page_number: int | None = Field(default=None, ge=1, le=500)
    source_reference: SafeSourceReference


class ExtractedField(BaseModel):
    """Original provider suggestion plus a separately retained human decision."""

    model_config = ConfigDict(extra="forbid")

    field_key: DocumentFieldKey
    original_extracted_value: str | None = Field(default=None, max_length=512)
    normalized_value: str | None = Field(default=None, max_length=512)
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: FieldProvenance
    canonical_value: str | None = Field(default=None, max_length=512)
    comparison_status: ComparisonStatus
    review_status: FieldReviewStatus = FieldReviewStatus.PENDING
    reviewed_value: str | None = Field(default=None, max_length=512)
    reviewed_at: datetime | None = None
    review_note: str | None = Field(default=None, max_length=240)

    @field_validator(
        "original_extracted_value",
        "normalized_value",
        "canonical_value",
        "reviewed_value",
        "review_note",
    )
    @classmethod
    def optional_text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("optional document text must not be blank")
        if any(ord(character) < 32 for character in normalized):
            raise ValueError("document text must not contain control characters")
        return normalized


class DocumentWorkflowEvent(BaseModel):
    """Audit-safe event with no filename, extracted value, note, or PDF content."""

    sequence: int = Field(ge=1)
    event_type: DocumentEventType
    state: DocumentProcessingState
    outcome: EventOutcome
    timestamp: datetime
    case_id: UUID
    document_id: UUID
    correlation_id: UUID
    field_key: DocumentFieldKey | None = None
    code: str | None = None
    message: str


class DocumentProcessingRecord(BaseModel):
    """Case-linked document record without retained binary or raw provider payload."""

    case_id: UUID
    document_id: UUID
    correlation_id: UUID
    display_name: str = Field(min_length=5, max_length=99)
    media_type: str = Field(pattern=r"^application/pdf$")
    profile: DocumentProfile
    provider_environment: IdpEnvironment | None = None
    state: DocumentProcessingState
    fields: list[ExtractedField] = Field(default_factory=list, max_length=4)
    events: list[DocumentWorkflowEvent] = Field(default_factory=list)
    error: SafeError | None = None
    created_at: datetime
    processed_at: datetime | None = None
    reviewed_at: datetime | None = None
    completion_method: DocumentCompletionMethod | None = None
    source_conflict_resolutions: list[DocumentSourceConflictResolution] = Field(
        default_factory=list, max_length=32
    )
    supersedes_document_id: UUID | None = None
    superseded_by_document_id: UUID | None = None
    superseded_at: datetime | None = None
    updated_at: datetime

    @property
    def is_current_evidence(self) -> bool:
        return self.superseded_by_document_id is None
