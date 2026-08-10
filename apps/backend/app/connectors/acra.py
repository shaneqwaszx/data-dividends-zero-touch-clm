"""ACRA connector contract expressed in source-boundary models."""

from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel


class AcraAddressPayload(BaseModel):
    """Address shape owned by the mock source connector."""

    block: str
    street: str
    unit: str | None = None
    postal_code: str
    country_code: str


class AcraCompanyPayload(BaseModel):
    """Synthetic ACRA-like payload that must be mapped before business use."""

    uen: str
    entity_name: str | None
    country_code: str | None
    entity_type: str | None
    registered_address: AcraAddressPayload | None
    source_environment: Literal["MOCK", "SANDBOX", "LIVE"]
    source_endpoint: str
    retrieved_at: datetime


class AcraConnector(Protocol):
    """Registry interface consumed by application orchestration."""

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        """Retrieve a source-boundary company payload by UEN."""
