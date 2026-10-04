"""Replaceable IDP provider boundary and validated untrusted source result."""

from dataclasses import dataclass, field
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.documents import (
    DocumentFieldCandidate,
    DocumentFieldKey,
    DocumentPageEvidence,
    DocumentProfile,
    ExtractionMetadata,
    ExtractionQuality,
    IdpEnvironment,
    OwnershipObservationValues,
    SafeProviderName,
    SafeSourceReference,
)


@dataclass(frozen=True)
class IdpDocumentInput:
    """Transient provider input; bytes are excluded from representations."""

    profile: DocumentProfile
    content: bytes = field(repr=False)
    media_type: str = "application/pdf"
    extracted_text: str | None = field(default=None, repr=False)


class IdpProviderMetadata(BaseModel):
    """Provider-neutral identity validated before provider output is retained."""

    model_config = ConfigDict(extra="forbid", revalidate_instances="always")

    provider_name: SafeProviderName
    environment: IdpEnvironment


class IdpSourceField(ExtractionMetadata):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")

    field_key: DocumentFieldKey
    value: str | None = Field(default=None, max_length=512)
    confidence: float = Field(ge=0.0, le=1.0)
    page_number: int | None = Field(default=None, ge=1, le=500)
    source_reference: SafeSourceReference
    candidates: tuple[DocumentFieldCandidate, ...] = Field(default=(), max_length=32)

    @field_validator("value")
    @classmethod
    def optional_value_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("source value must not be blank")
        if any(ord(character) < 32 for character in normalized):
            raise ValueError("source value must not contain control characters")
        return normalized

    @model_validator(mode="after")
    def candidate_value_agrees(self) -> "IdpSourceField":
        values = {candidate.value for candidate in self.candidates}
        if len(values) > 1 and (
            self.value is not None or self.extraction_quality != ExtractionQuality.AMBIGUOUS
        ):
            raise ValueError("ambiguous source candidates cannot select a value")
        if values and self.value is not None and self.value not in values:
            raise ValueError("source value must agree with candidate evidence")
        return self


class IdpSourceResult(BaseModel):
    """Strict four-field provisional result; not a sponsor-approved contract."""

    model_config = ConfigDict(extra="forbid", revalidate_instances="always")

    profile: DocumentProfile
    fields: list[IdpSourceField] = Field(min_length=4, max_length=4)
    pages: tuple[DocumentPageEvidence, ...] = Field(default=(), max_length=10)
    ownership_observations: tuple[OwnershipObservationValues, ...] = Field(
        default=(), max_length=128
    )

    @model_validator(mode="after")
    def require_each_provisional_field_once(self) -> "IdpSourceResult":
        keys = [item.field_key for item in self.fields]
        if len(keys) != len(set(keys)):
            raise ValueError("source field keys must be unique")
        if set(keys) != set(DocumentFieldKey):
            raise ValueError("source result must contain the provisional four-field profile")
        page_numbers = [page.page_number for page in self.pages]
        if len(page_numbers) != len(set(page_numbers)):
            raise ValueError("source page evidence must be unique")
        bound_pages = set(page_numbers)
        if any(observation.page_number not in bound_pages for observation
               in self.ownership_observations):
            raise ValueError("ownership observations require page evidence")
        if any(candidate.page_number not in bound_pages for item in self.fields
               for candidate in item.candidates):
            raise ValueError("field candidates require page evidence")
        return self


class IdpProvider(Protocol):
    """Provider interface independent of OCR, cloud, VLM, or LLM implementations."""

    @property
    def metadata(self) -> object: ...

    def process(self, document: IdpDocumentInput) -> object: ...


class IdpProviderError(Exception):
    """Base provider error whose private cause is never projected automatically."""


class IdpProcessingError(IdpProviderError):
    """Controlled provider failure with an application-owned public projection."""


class LocalDocumentProcessingError(IdpProcessingError):
    """Application-owned processing code, never derived from engine error output."""

    def __init__(self, code: str) -> None:
        self.code = code if code in {
            "DOCUMENT_RUNTIME_UNAVAILABLE", "DOCUMENT_PROCESSING_TIMEOUT",
            "DOCUMENT_STRUCTURE_INVALID", "DOCUMENT_OUTPUT_LIMIT_EXCEEDED",
            "OCR_RUNTIME_UNAVAILABLE", "OCR_PROCESSING_TIMEOUT", "OCR_PROCESSING_FAILED",
            "OCR_OUTPUT_INVALID",
        } else "IDP_PROCESSING_FAILED"
        super().__init__(self.code)
