"""Replaceable IDP provider boundary and validated untrusted source result."""

from dataclasses import dataclass, field
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.documents import (
    DocumentFieldKey,
    DocumentProfile,
    IdpEnvironment,
    SafeProviderName,
    SafeSourceReference,
)


@dataclass(frozen=True)
class IdpDocumentInput:
    """Transient provider input; bytes are excluded from representations."""

    profile: DocumentProfile
    content: bytes = field(repr=False)


class IdpProviderMetadata(BaseModel):
    """Provider-neutral identity validated before provider output is retained."""

    model_config = ConfigDict(extra="forbid")

    provider_name: SafeProviderName
    environment: IdpEnvironment


class IdpSourceField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_key: DocumentFieldKey
    value: str | None = Field(default=None, max_length=512)
    confidence: float = Field(ge=0.0, le=1.0)
    page_number: int | None = Field(default=None, ge=1, le=500)
    source_reference: SafeSourceReference

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


class IdpSourceResult(BaseModel):
    """Strict four-field provisional result; not a sponsor-approved contract."""

    model_config = ConfigDict(extra="forbid")

    profile: DocumentProfile
    fields: list[IdpSourceField] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def require_each_provisional_field_once(self) -> "IdpSourceResult":
        keys = [item.field_key for item in self.fields]
        if len(keys) != len(set(keys)):
            raise ValueError("source field keys must be unique")
        if set(keys) != set(DocumentFieldKey):
            raise ValueError("source result must contain the provisional four-field profile")
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
