"""Source-neutral document extraction, comparison, and review models."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal
from unicodedata import category
from uuid import UUID

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.domain.models import EventOutcome, SafeError
from app.domain.target_classification import TargetClassificationKey


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

    CERTIFICATE_OF_INCORPORATION_POC = "CERTIFICATE_OF_INCORPORATION_POC"
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


class ExtractionMethod(StrEnum):
    UNKNOWN = "UNKNOWN"
    NATIVE_PDF_TEXT = "NATIVE_PDF_TEXT"
    NATIVE_DOCX_TEXT = "NATIVE_DOCX_TEXT"
    NATIVE_TXT_TEXT = "NATIVE_TXT_TEXT"
    LOCAL_TESSERACT_OCR = "LOCAL_TESSERACT_OCR"


class ExtractionQuality(StrEnum):
    UNKNOWN = "UNKNOWN"
    HIGH = "HIGH"
    LOW = "LOW"
    UNAVAILABLE = "UNAVAILABLE"
    AMBIGUOUS = "AMBIGUOUS"


class ExtractionScoreKind(StrEnum):
    LEGACY_UNSPECIFIED = "LEGACY_UNSPECIFIED"
    DETERMINISTIC_EVIDENCE_SCORE = "DETERMINISTIC_EVIDENCE_SCORE"


class ExtractionMetadata(BaseModel):
    """Extraction evidence, independent of source agreement and verification."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")
    extraction_method: ExtractionMethod = ExtractionMethod.UNKNOWN
    extraction_quality: ExtractionQuality = ExtractionQuality.UNKNOWN
    score_kind: ExtractionScoreKind = ExtractionScoreKind.LEGACY_UNSPECIFIED
    score_formula: Literal[
        "LEGACY_UNSPECIFIED", "LABEL_SCORE", "LABEL_SCORE_TIMES_OCR_MEAN_OVER_100"
    ] = "LEGACY_UNSPECIFIED"
    raw_ocr_mean_confidence: float | None = Field(default=None, ge=0, le=100)
    raw_ocr_word_count: int | None = Field(default=None, ge=0, le=64000)


class DocumentPageEvidence(ExtractionMetadata):
    """Safe page metadata only: full page text is transient."""

    page_number: int = Field(ge=1, le=10)
    source_reference: SafeSourceReference


class DocumentFieldCandidate(ExtractionMetadata):
    value: str = Field(min_length=1, max_length=512)
    page_number: int = Field(ge=1, le=10)
    source_reference: SafeSourceReference

    @field_validator("value")
    @classmethod
    def safe_candidate(cls, value: str) -> str:
        return str(_normalize_safe_provenance(value))


class OwnershipObservationValues(ExtractionMetadata):
    """Bounded explicit source scalars, without application identity bindings."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")
    page_number: int = Field(ge=1, le=10)
    source_reference: SafeSourceReference
    evidence_score: float = Field(ge=0, le=1)
    owner_name: str = Field(min_length=1, max_length=160)
    owner_type: Literal["NATURAL_PERSON", "LEGAL_ENTITY"] | None = None
    owner_registration_identifier: str | None = Field(default=None, min_length=1, max_length=64)
    owned_entity_name: str | None = Field(default=None, min_length=1, max_length=160)
    owned_entity_registration_identifier: str | None = Field(
        default=None, min_length=1, max_length=64
    )
    share_count: Decimal | None = Field(
        default=None, ge=0, max_digits=24, decimal_places=6, allow_inf_nan=False
    )
    explicit_percentage: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=12, decimal_places=6, allow_inf_nan=False
    )
    explicit_total_shares: Decimal | None = Field(
        default=None, gt=0, max_digits=24, decimal_places=6, allow_inf_nan=False
    )
    share_class: str | None = Field(default=None, min_length=1, max_length=128)
    as_of_date: date | None = None
    decision_state: Literal["PROPOSED"] = "PROPOSED"

    @field_validator(
        "owner_name", "owner_registration_identifier", "owned_entity_name",
        "owned_entity_registration_identifier", "share_class",
    )
    @classmethod
    def safe_scalar(cls, value: str | None) -> str | None:
        return None if value is None else str(_normalize_safe_provenance(value))

    @field_validator("share_count", "explicit_percentage", "explicit_total_shares", mode="before")
    @classmethod
    def exact_scalar(cls, value: object) -> object:
        if isinstance(value, (float, bool)):
            raise ValueError("ownership observations require exact decimals")
        return value


class DocumentOwnershipObservation(OwnershipObservationValues):
    """Server-bound proposed scalar evidence; this is never an ownership decision."""

    observation_id: UUID
    document_id: UUID
    document_version: Literal[1]


class DocumentCompletionMethod(StrEnum):
    AUTO_CONFIRMED = "AUTO_CONFIRMED"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    EXCEPTION_RESOLVED = "EXCEPTION_RESOLVED"


class DocumentAutoClearBlocker(StrEnum):
    TEXT_UNAVAILABLE = "DOCUMENT_TEXT_UNAVAILABLE"
    SOURCE_CONFLICT = "DOCUMENT_SOURCE_CONFLICT"
    LOW_CONFIDENCE = "DOCUMENT_LOW_CONFIDENCE"
    AMBIGUOUS_EXTRACTION = "DOCUMENT_AMBIGUOUS_EXTRACTION"
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


class ExtractedField(ExtractionMetadata):
    """Original provider suggestion plus a separately retained human decision."""

    model_config = ConfigDict(extra="forbid", frozen=False)

    field_key: DocumentFieldKey
    original_extracted_value: str | None = Field(default=None, max_length=512)
    normalized_value: str | None = Field(default=None, max_length=512)
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: FieldProvenance
    candidates: tuple[DocumentFieldCandidate, ...] = Field(default=(), max_length=32)
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


class ClassificationObservationValues(DocumentFieldCandidate):
    value: str = Field(min_length=1, max_length=160)

    @field_validator("value")
    @classmethod
    def safe_label_value(cls, value: str) -> str:
        if any(category(character).startswith("C") for character in value):
            raise ValueError("Classification observation must not contain control characters")
        return value

    field_key: TargetClassificationKey
    evidence_score: float = Field(ge=0, le=1)


class DocumentClassificationObservation(ClassificationObservationValues):
    document_id: UUID
    document_version: Literal[1]


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
    media_type: str = Field(
        pattern=(
            r"^(?:application/pdf|"
            r"application/vnd\.openxmlformats-officedocument\.wordprocessingml\.document|"
            r"text/plain|image/png|image/jpeg|image/tiff)$"
        )
    )
    size_bytes: int = Field(gt=0)
    profile: DocumentProfile
    provider_environment: IdpEnvironment | None = None
    state: DocumentProcessingState
    fields: list[ExtractedField] = Field(default_factory=list, max_length=4)
    document_version: Literal[1] | None = None
    pages: tuple[DocumentPageEvidence, ...] = Field(default=(), max_length=10)
    ownership_observations: tuple[DocumentOwnershipObservation, ...] = Field(
        default=(), max_length=128
    )
    classification_observations: tuple[DocumentClassificationObservation, ...] = Field(
        default=(), max_length=64
    )
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

    @model_validator(mode="after")
    def bind_proposed_evidence(self) -> "DocumentProcessingRecord":
        pages = {page.page_number for page in self.pages}
        if len(pages) != len(self.pages):
            raise ValueError("document page evidence must be unique")
        if any(candidate.page_number not in pages for item in self.fields
               for candidate in item.candidates):
            raise ValueError("document candidate requires its retained page")
        observations: tuple[
            DocumentOwnershipObservation | DocumentClassificationObservation, ...
        ] = (
            *self.ownership_observations,
            *self.classification_observations,
        )
        if any(
            observation.document_id != self.document_id
            or observation.document_version != self.document_version
            or observation.page_number not in pages
            for observation in observations
        ):
            raise ValueError("document ownership proposal requires its original version and page")
        for item in self.fields:
            values = {candidate.value for candidate in item.candidates}
            if len(values) > 1 and (
                item.original_extracted_value is not None or item.normalized_value is not None
                or item.extraction_quality != ExtractionQuality.AMBIGUOUS
            ):
                raise ValueError("ambiguous document candidates cannot select an original value")
            if values and item.original_extracted_value is not None \
                    and item.original_extracted_value not in values:
                raise ValueError("document original value differs from its candidate evidence")
        return self

    @property
    def is_current_evidence(self) -> bool:
        return self.superseded_by_document_id is None
