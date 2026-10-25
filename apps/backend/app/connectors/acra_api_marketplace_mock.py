"""Official ACRA API Marketplace Mock connector.

This lane is fixed to the official Mock host and read-only EIQ operations: entity basic
information, shareholders and (D-088) business profile. It is separate from the local
synthetic Mock and generic sandbox seams and never falls back.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Literal
from urllib.parse import urlencode, urlsplit, urlunsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.connectors.acra import (
    AcraCompanyPayload,
    AcraOfficersPayload,
    AcraOwnershipPartiesPayload,
    AcraRelationshipsPayload,
    NonBlankSourceText,
    OptionalSourceText,
    SourceUenText,
)
from app.connectors.acra_bizfile_sandbox import (
    BizfileMockCompanyDecoder,
    BizfileMockOfficersDecoder,
    BizfileMockOwnershipPartiesDecoder,
)
from app.connectors.acra_sandbox import AcraHttpResponse, AcraHttpTransport, AcraRequestAuthorizer
from app.connectors.errors import (
    AcraAuthenticationError,
    AcraConfigurationError,
    AcraMalformedResponseError,
    AcraOperationUnsupportedError,
    AcraServiceUnavailableError,
    AcraTimeoutError,
    AcraUnexpectedConnectorError,
    ConnectorError,
)

ACRA_API_MARKETPLACE_MOCK_BASE_URL = "https://api-sandbox.bizfile.gov.sg/api/acra"
ACRA_API_MARKETPLACE_MOCK_ENTITY_PATH = "/entityQuery/entityBasicInformation"
ACRA_API_MARKETPLACE_MOCK_SHAREHOLDERS_PATH = "/entityQuery/coShareholdersDetails"
ACRA_API_MARKETPLACE_MOCK_BUSINESS_PROFILE_PATH = "/entityQuery/businessProfile"
ACRA_API_MARKETPLACE_MOCK_RESPONSE_MAX_BYTES = 256 * 1024
ACRA_API_MARKETPLACE_MOCK_DATASET_NAMESPACE = "ACRA_API_MARKETPLACE_MOCK_V1"


def _query_free_provenance(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _has_explicit_empty_entities(body: object) -> bool:
    return (
        isinstance(body, dict)
        and "entities" in body
        and isinstance(body["entities"], list)
        and not body["entities"]
    )


@dataclass(frozen=True)
class AcraApiMarketplaceMockConnection:
    """Fixed official Mock connection with only a bounded timeout configurable."""

    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if not 0 < self.timeout_seconds <= 30:
            raise AcraConfigurationError

    @staticmethod
    def _endpoint(path: str, uen: str) -> str:
        return (
            f"{ACRA_API_MARKETPLACE_MOCK_BASE_URL}{path}?"
            f"{urlencode({'uen': uen})}"
        )

    def company_endpoint(self, uen: str) -> str:
        return self._endpoint(ACRA_API_MARKETPLACE_MOCK_ENTITY_PATH, uen)

    def shareholders_endpoint(self, uen: str) -> str:
        return self._endpoint(ACRA_API_MARKETPLACE_MOCK_SHAREHOLDERS_PATH, uen)

    def business_profile_endpoint(self, uen: str) -> str:
        return self._endpoint(ACRA_API_MARKETPLACE_MOCK_BUSINESS_PROFILE_PATH, uen)


def _exact_count(value: object) -> object:
    """A JSON share count: an integer, or a finite whole JSON number such as 1000.0."""
    if isinstance(value, (bool, str)):
        raise ValueError("share counts must be JSON numbers")
    if isinstance(value, float):
        if not isfinite(value) or not value.is_integer():
            raise ValueError("share counts must be whole numbers")
        return Decimal(int(value))
    return value


def _exact_amount(value: object) -> object:
    """A JSON capital amount, converted through its shortest exact decimal text."""
    if isinstance(value, (bool, str)):
        raise ValueError("capital amounts must be JSON numbers")
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("capital amounts must be finite")
        try:
            return Decimal(repr(value))
        except InvalidOperation:
            raise ValueError("capital amounts must be exact") from None
    return value


class _BusinessProfileShareholder(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category: NonBlankSourceText = Field(max_length=64)
    source_id: NonBlankSourceText = Field(alias="id", max_length=64)
    principal_name: NonBlankSourceText = Field(alias="principalName", max_length=160)
    # The observed operation returns no status; any status it does return is kept so the
    # D-088 current-status assumption can never replace it.
    status: OptionalSourceText = Field(default=None, max_length=64)
    number_of_shares: Decimal = Field(
        alias="numberOfShares", ge=Decimal("0"), max_digits=18, decimal_places=6
    )
    share_type: OptionalSourceText = Field(default=None, alias="shareType", max_length=64)
    currency: OptionalSourceText = Field(default=None, max_length=64)

    _count = field_validator("number_of_shares", mode="before")(_exact_count)

    @field_validator("number_of_shares")
    @classmethod
    def whole_count(cls, value: Decimal) -> Decimal:
        if value != value.to_integral_value():
            raise ValueError("share counts must be whole numbers")
        return value


class _BusinessProfileCapital(BaseModel):
    model_config = ConfigDict(extra="ignore")

    share_type: OptionalSourceText = Field(default=None, alias="shareType", max_length=64)
    currency: OptionalSourceText = Field(default=None, max_length=64)
    number_of_shares: Decimal | None = Field(
        default=None, alias="numberOfShares", ge=Decimal("0"), max_digits=18, decimal_places=6
    )
    amount: Decimal | None = Field(default=None, ge=Decimal("0"), max_digits=24, decimal_places=6)

    _count = field_validator("number_of_shares", mode="before")(_exact_count)
    _amount = field_validator("amount", mode="before")(_exact_amount)

    @field_validator("number_of_shares")
    @classmethod
    def whole_count(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value != value.to_integral_value():
            raise ValueError("share counts must be whole numbers")
        return value


class _BusinessProfileEntity(BaseModel):
    # Officer, address, nationality and activity fields are ignored and never retained.
    model_config = ConfigDict(extra="ignore")

    uen: SourceUenText
    entity_name: NonBlankSourceText = Field(alias="entityName", max_length=160)
    company_type: OptionalSourceText = Field(default=None, alias="companyType", max_length=160)
    status_of_company: OptionalSourceText = Field(
        default=None, alias="statusOfCompany", max_length=80
    )
    shareholder: tuple[_BusinessProfileShareholder, ...] = Field(default=(), max_length=64)
    issued_share_capital: tuple[_BusinessProfileCapital, ...] = Field(
        default=(), alias="issuedShareCapital", max_length=16
    )
    paid_up_capital: tuple[_BusinessProfileCapital, ...] = Field(
        default=(), alias="paidUpCapital", max_length=16
    )


class _BusinessProfileEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore")

    entities: tuple[_BusinessProfileEntity, ...]


class AcraBusinessProfileShareholderPayload(BaseModel):
    """Strict source-boundary businessProfile shareholder row (D-088)."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    source_id: str = Field(min_length=1, max_length=64)
    party_type: Literal["NATURAL_PERSON", "LEGAL_ENTITY"]
    source_category: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    source_status: str | None = Field(default=None, min_length=1, max_length=64)
    number_of_shares: Decimal = Field(ge=0, max_digits=18, decimal_places=6)
    share_type: str | None = Field(default=None, min_length=1, max_length=64)
    currency: str | None = Field(default=None, min_length=1, max_length=64)


class AcraShareCapitalPayload(BaseModel):
    """Strict source-boundary businessProfile issued or paid-up capital line."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    share_type: str | None = Field(default=None, min_length=1, max_length=64)
    currency: str | None = Field(default=None, min_length=1, max_length=64)
    number_of_shares: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    amount: Decimal | None = Field(default=None, ge=0, max_digits=24, decimal_places=6)


class AcraBusinessProfilePayload(BaseModel):
    """Strict source-boundary businessProfile result; entity_present false is empty."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    uen: str = Field(min_length=1, max_length=32)
    entity_present: bool
    entity_name: str | None = Field(default=None, min_length=1, max_length=160)
    company_type: str | None = Field(default=None, min_length=1, max_length=160)
    status_of_company: str | None = Field(default=None, min_length=1, max_length=80)
    shareholders: tuple[AcraBusinessProfileShareholderPayload, ...] = Field(
        default=(), max_length=64
    )
    issued_share_capital: tuple[AcraShareCapitalPayload, ...] = Field(default=(), max_length=16)
    paid_up_capital: tuple[AcraShareCapitalPayload, ...] = Field(default=(), max_length=16)
    source_environment: Literal["MOCK"] = "MOCK"
    source_endpoint: str
    retrieved_at: datetime


class MarketplaceBusinessProfileDecoder:
    """Decode official Mock businessProfile into its shareholder and capital facts.

    Exactly one same-UEN entity is accepted. Only the company labels, shareholder rows
    (category, name, count, class, currency) and capital lines are kept; officers,
    addresses and nationalities never leave this boundary, and the holder's source
    identifier leaves it only to be replaced by the adapter's opaque digest.
    """

    def decode(
        self,
        body: object,
        *,
        requested_uen: str,
        source_endpoint: str,
        retrieved_at: datetime,
    ) -> AcraBusinessProfilePayload:
        try:
            envelope = _BusinessProfileEnvelope.model_validate(body)
        except ValidationError:
            raise AcraMalformedResponseError from None
        if len(envelope.entities) != 1:
            raise AcraMalformedResponseError
        entity = envelope.entities[0]
        if entity.uen.upper() != requested_uen:
            raise AcraMalformedResponseError
        holders: list[AcraBusinessProfileShareholderPayload] = []
        for row in entity.shareholder:
            category = row.category.strip().casefold()
            if category not in {"individual", "corporate"}:
                raise AcraMalformedResponseError
            holders.append(
                AcraBusinessProfileShareholderPayload(
                    source_id=row.source_id,
                    party_type="NATURAL_PERSON" if category == "individual" else "LEGAL_ENTITY",
                    source_category=row.category,
                    name=row.principal_name,
                    source_status=row.status,
                    number_of_shares=row.number_of_shares,
                    share_type=row.share_type,
                    currency=row.currency,
                )
            )
        return AcraBusinessProfilePayload(
            uen=requested_uen,
            entity_present=True,
            entity_name=entity.entity_name,
            company_type=entity.company_type,
            status_of_company=entity.status_of_company,
            shareholders=tuple(holders),
            issued_share_capital=_capital(entity.issued_share_capital),
            paid_up_capital=_capital(entity.paid_up_capital),
            source_endpoint=source_endpoint,
            retrieved_at=retrieved_at,
        )


def _capital(lines: tuple[_BusinessProfileCapital, ...]) -> tuple[AcraShareCapitalPayload, ...]:
    return tuple(
        AcraShareCapitalPayload(
            share_type=line.share_type,
            currency=line.currency,
            number_of_shares=line.number_of_shares,
            amount=line.amount,
        )
        for line in lines
    )


class AcraApiMarketplaceMockConnector:
    """Retrieve strict company/officer/shareholder evidence from official Mock."""

    def __init__(
        self,
        *,
        connection: AcraApiMarketplaceMockConnection,
        transport: AcraHttpTransport,
        authorizer: AcraRequestAuthorizer,
        company_decoder: BizfileMockCompanyDecoder | None = None,
        officers_decoder: BizfileMockOfficersDecoder | None = None,
        ownership_decoder: BizfileMockOwnershipPartiesDecoder | None = None,
        business_profile_decoder: MarketplaceBusinessProfileDecoder | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._connection = connection
        self._transport = transport
        self._authorizer = authorizer
        self._company_decoder = company_decoder or BizfileMockCompanyDecoder()
        self._officers_decoder = officers_decoder or BizfileMockOfficersDecoder()
        self._ownership_decoder = ownership_decoder or BizfileMockOwnershipPartiesDecoder(
            include_withdrawn=True
        )
        self._business_profile_decoder = (
            business_profile_decoder or MarketplaceBusinessProfileDecoder()
        )
        self._clock = clock or (lambda: datetime.now(UTC))

    def _get(self, endpoint: str) -> AcraHttpResponse:
        try:
            headers = dict(self._authorizer.authorization_headers())
            if set(headers) != {"token"} or not headers["token"]:
                raise AcraConfigurationError
            headers["Accept"] = "application/json"
            return self._transport.get(
                endpoint,
                headers=headers,
                timeout_seconds=self._connection.timeout_seconds,
            )
        except ConnectorError:
            raise
        except httpx.TimeoutException:
            raise AcraTimeoutError from None
        except httpx.TransportError:
            raise AcraServiceUnavailableError from None
        except Exception:
            raise AcraUnexpectedConnectorError from None

    @staticmethod
    def _raise_for_status(response: AcraHttpResponse) -> None:
        if response.status_code in {401, 403}:
            raise AcraAuthenticationError
        if response.status_code in {408, 504}:
            raise AcraTimeoutError
        if response.status_code == 429 or response.status_code >= 500:
            raise AcraServiceUnavailableError
        if response.status_code != 200 or response.body is None:
            raise AcraMalformedResponseError
        if response.size_limit_exceeded:
            raise AcraMalformedResponseError
        if (
            response.content_type is not None
            and response.content_type.split(";", 1)[0].strip().lower()
            != "application/json"
        ):
            raise AcraMalformedResponseError
        if (
            response.response_bytes is not None
            and not 0 <= response.response_bytes <= ACRA_API_MARKETPLACE_MOCK_RESPONSE_MAX_BYTES
        ):
            raise AcraMalformedResponseError

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        normalized = uen.strip().upper()
        endpoint = self._connection.company_endpoint(normalized)
        response = self._get(endpoint)
        self._raise_for_status(response)
        if _has_explicit_empty_entities(response.body):
            return None
        try:
            return self._company_decoder.decode(
                response.body,
                requested_uen=normalized,
                source_endpoint=_query_free_provenance(endpoint),
                retrieved_at=self._clock(),
            )
        except AcraMalformedResponseError:
            raise
        except Exception:
            raise AcraMalformedResponseError from None

    def fetch_officers(self, uen: str) -> AcraOfficersPayload:
        normalized = uen.strip().upper()
        endpoint = self._connection.company_endpoint(normalized)
        response = self._get(endpoint)
        self._raise_for_status(response)
        if _has_explicit_empty_entities(response.body):
            raise AcraMalformedResponseError
        try:
            return self._officers_decoder.decode(
                response.body,
                requested_uen=normalized,
                source_endpoint=_query_free_provenance(endpoint),
                retrieved_at=self._clock(),
            )
        except AcraMalformedResponseError:
            raise
        except Exception:
            raise AcraMalformedResponseError from None

    def fetch_ownership_parties(self, uen: str) -> AcraOwnershipPartiesPayload:
        normalized = uen.strip().upper()
        endpoint = self._connection.shareholders_endpoint(normalized)
        response = self._get(endpoint)
        self._raise_for_status(response)
        if _has_explicit_empty_entities(response.body):
            return AcraOwnershipPartiesPayload(
                uen=normalized,
                ownership_parties=(),
                source_environment="MOCK",
                source_endpoint=_query_free_provenance(endpoint),
                retrieved_at=self._clock(),
            )
        try:
            return self._ownership_decoder.decode(
                response.body,
                requested_uen=normalized,
                source_endpoint=_query_free_provenance(endpoint),
                retrieved_at=self._clock(),
            )
        except AcraMalformedResponseError:
            raise
        except Exception:
            raise AcraMalformedResponseError from None

    def fetch_business_profile(self, uen: str) -> AcraBusinessProfilePayload:
        """D-088: one read-only businessProfile GET; an explicit empty list is empty."""

        normalized = uen.strip().upper()
        endpoint = self._connection.business_profile_endpoint(normalized)
        response = self._get(endpoint)
        self._raise_for_status(response)
        if _has_explicit_empty_entities(response.body):
            return AcraBusinessProfilePayload(
                uen=normalized,
                entity_present=False,
                source_endpoint=_query_free_provenance(endpoint),
                retrieved_at=self._clock(),
            )
        try:
            return self._business_profile_decoder.decode(
                response.body,
                requested_uen=normalized,
                source_endpoint=_query_free_provenance(endpoint),
                retrieved_at=self._clock(),
            )
        except AcraMalformedResponseError:
            raise
        except Exception:
            raise AcraMalformedResponseError from None

    def fetch_relationships(self, uen: str) -> AcraRelationshipsPayload:
        """Stop without dispatch or invented evidence: the contract is unsupported."""

        raise AcraOperationUnsupportedError
