"""ACRA connector contract expressed in source-boundary models."""

from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal, Protocol
from unicodedata import category
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)


def _normalize_source_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    if any(category(character).startswith("C") for character in value):
        raise ValueError("source text must not contain control characters")
    return value.strip()


NonBlankSourceText = Annotated[
    str,
    BeforeValidator(_normalize_source_text),
    StringConstraints(min_length=1, max_length=512),
]
TrimmedSourceText = Annotated[
    str,
    BeforeValidator(_normalize_source_text),
    StringConstraints(max_length=512),
]
SourceUenText = Annotated[
    str,
    BeforeValidator(_normalize_source_text),
    StringConstraints(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9]+$"),
]
SourceCodeText = Annotated[
    str,
    BeforeValidator(_normalize_source_text),
    StringConstraints(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9 _.-]*$",
    ),
]
SourceCountryCode = Annotated[
    str,
    BeforeValidator(_normalize_source_text),
    StringConstraints(pattern=r"^[A-Za-z]{2,3}$"),
]
SourceEnvironmentText = Annotated[
    Literal["MOCK", "SANDBOX"],
    BeforeValidator(_normalize_source_text),
]


def _normalize_optional_source_text(value: object) -> object:
    if isinstance(value, str):
        normalized = _normalize_source_text(value)
        return normalized or None
    return value


OptionalSourceText = Annotated[
    str | None,
    BeforeValidator(_normalize_optional_source_text),
]


class AcraAddressPayload(BaseModel):
    """Narrow ACRA source address used by the current POC."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    block: NonBlankSourceText
    street: NonBlankSourceText
    unit: OptionalSourceText = Field(default=None, max_length=512)
    building_name: OptionalSourceText = Field(default=None, max_length=512)
    postal_code: NonBlankSourceText
    country_code: SourceCountryCode


class AcraCompanyPayload(BaseModel):
    """Validated ACRA source DTO that must be mapped before business use."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    uen: SourceUenText
    entity_name: NonBlankSourceText
    country_code: SourceCountryCode
    entity_type: SourceCodeText
    registration_date: date | None = None
    entity_status: SourceCodeText | None = None
    registered_address: AcraAddressPayload | None
    source_environment: SourceEnvironmentText
    source_endpoint: NonBlankSourceText = Field(max_length=2048)
    retrieved_at: datetime

    @field_validator("source_endpoint")
    @classmethod
    def source_endpoint_must_be_safe_https_provenance(cls, value: str) -> str:
        try:
            parsed = urlsplit(value)
            _ = parsed.port
        except ValueError as exc:
            raise ValueError("source endpoint must be a valid URL") from exc
        if (
            parsed.scheme.lower() != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "source endpoint must be HTTPS provenance without credentials, query, or fragment"
            )
        return value

    @field_validator("retrieved_at")
    @classmethod
    def retrieved_at_must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("retrieved_at must be timezone-aware UTC")
        return value.astimezone(UTC)


class AcraConnector(Protocol):
    """Registry interface consumed by application orchestration."""

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        """Retrieve a source-boundary company payload by UEN."""
