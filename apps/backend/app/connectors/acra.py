"""ACRA connector contract expressed in source-boundary models."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
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


class AcraOfficerPayload(BaseModel):
    """Strict project-owned Mock officer record pending Q-012."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    officer_id: Annotated[
        str,
        BeforeValidator(_normalize_source_text),
        StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$"),
    ]
    name: Annotated[
        str,
        BeforeValidator(_normalize_source_text),
        StringConstraints(min_length=1, max_length=160),
    ]
    role: SourceCodeText
    appointment_date: date | None = None
    cessation_date: date | None = None
    country: SourceCountryCode | None = None


class AcraOwnershipPartyPayload(BaseModel):
    """Strict project-owned Mock ownership-party record pending Q-012."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    party_id: Annotated[
        str,
        BeforeValidator(_normalize_source_text),
        StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$"),
    ]
    party_type: Literal["NATURAL_PERSON", "LEGAL_ENTITY"]
    name: Annotated[
        str,
        BeforeValidator(_normalize_source_text),
        StringConstraints(min_length=1, max_length=160),
    ]
    registration_identifier: OptionalSourceText = Field(default=None, max_length=64)
    country: SourceCountryCode | None = None
    source_category: SourceCodeText | None = None
    source_status: SourceCodeText | None = None
    share_allotted: Annotated[
        Decimal | None,
        Field(ge=Decimal("0"), max_digits=18, decimal_places=6),
    ] = None
    share_type: OptionalSourceText = Field(default=None, max_length=64)
    currency: OptionalSourceText = Field(default=None, max_length=64)
    ownership_percentage: Annotated[
        Decimal | None,
        Field(gt=Decimal("0"), le=Decimal("100"), max_digits=12, decimal_places=6),
    ] = None

    @field_validator("share_allotted", mode="before")
    @classmethod
    def share_allotted_must_be_exact(cls, value: object) -> object:
        if isinstance(value, (float, bool)):
            raise ValueError("share_allotted must use exact Decimal-compatible input")
        return value


class AcraRelationshipPayload(BaseModel):
    """Strict project-owned Mock registry relationship pending Q-012."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    relationship_id: Annotated[
        str,
        BeforeValidator(_normalize_source_text),
        StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$"),
    ]
    owned_entity_id: Annotated[
        str,
        BeforeValidator(_normalize_source_text),
        StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$"),
    ]
    owner_party_id: Annotated[
        str,
        BeforeValidator(_normalize_source_text),
        StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$"),
    ]
    relationship_type: Literal["SHARE_OWNERSHIP"] = "SHARE_OWNERSHIP"
    ownership_percentage: Annotated[
        Decimal,
        Field(gt=Decimal("0"), le=Decimal("100"), max_digits=12, decimal_places=6),
    ]


class _AcraCollectionPayload(BaseModel):
    """Shared strict envelope for one project-owned collection operation."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    uen: SourceUenText
    source_environment: SourceEnvironmentText
    source_endpoint: NonBlankSourceText = Field(max_length=2048)
    retrieved_at: datetime

    @field_validator("source_endpoint")
    @classmethod
    def source_endpoint_must_be_safe_https_provenance(cls, value: str) -> str:
        return AcraCompanyPayload.source_endpoint_must_be_safe_https_provenance(value)

    @field_validator("retrieved_at")
    @classmethod
    def retrieved_at_must_be_utc(cls, value: datetime) -> datetime:
        return AcraCompanyPayload.retrieved_at_must_be_utc(value)


class AcraOfficersPayload(_AcraCollectionPayload):
    officers: tuple[AcraOfficerPayload, ...] = Field(default=(), max_length=32)


class AcraOwnershipPartiesPayload(_AcraCollectionPayload):
    ownership_parties: tuple[AcraOwnershipPartyPayload, ...] = Field(
        default=(), max_length=64
    )


class AcraRelationshipsPayload(_AcraCollectionPayload):
    relationships: tuple[AcraRelationshipPayload, ...] = Field(default=(), max_length=128)


class AcraConnector(Protocol):
    """Registry interface consumed by application orchestration."""

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        """Retrieve a source-boundary company payload by UEN."""

    def fetch_officers(self, uen: str) -> AcraOfficersPayload:
        """Retrieve the project-owned Mock officer collection."""

    def fetch_ownership_parties(self, uen: str) -> AcraOwnershipPartiesPayload:
        """Retrieve the project-owned Mock ownership-party collection."""

    def fetch_relationships(self, uen: str) -> AcraRelationshipsPayload:
        """Retrieve the project-owned Mock relationship collection."""
