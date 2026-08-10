"""ACRA connector contract expressed in source-boundary models."""

from datetime import date, datetime
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints

NonBlankSourceText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
TrimmedSourceText = Annotated[str, StringConstraints(strip_whitespace=True)]


def _normalize_optional_source_text(value: object) -> object:
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    return value


OptionalSourceText = Annotated[str | None, BeforeValidator(_normalize_optional_source_text)]


class AcraAddressPayload(BaseModel):
    """Narrow ACRA source address used by the current POC."""

    model_config = ConfigDict(extra="forbid")

    block: NonBlankSourceText
    street: NonBlankSourceText
    unit: OptionalSourceText = None
    building_name: OptionalSourceText = None
    postal_code: NonBlankSourceText
    country_code: NonBlankSourceText


class AcraCompanyPayload(BaseModel):
    """Validated ACRA source DTO that must be mapped before business use."""

    model_config = ConfigDict(extra="forbid")

    uen: NonBlankSourceText
    entity_name: NonBlankSourceText
    country_code: NonBlankSourceText
    entity_type: NonBlankSourceText
    registration_date: date | None = None
    entity_status: TrimmedSourceText | None = None
    registered_address: AcraAddressPayload | None
    source_environment: Literal["MOCK", "SANDBOX"]
    source_endpoint: NonBlankSourceText
    retrieved_at: datetime


class AcraConnector(Protocol):
    """Registry interface consumed by application orchestration."""

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        """Retrieve a source-boundary company payload by UEN."""
