"""Production-shaped ACRA sandbox adapter with isolated transport and auth seams."""

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol, cast
from urllib.parse import quote, urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.connectors.acra import (
    AcraAddressPayload,
    AcraCompanyPayload,
    AcraOfficersPayload,
    AcraOwnershipPartiesPayload,
    AcraRelationshipsPayload,
    NonBlankSourceText,
    OptionalSourceText,
    TrimmedSourceText,
)
from app.connectors.errors import (
    AcraAuthenticationError,
    AcraConfigurationError,
    AcraMalformedResponseError,
    AcraServiceUnavailableError,
    AcraTimeoutError,
    AcraUnexpectedConnectorError,
    ConnectorError,
)

_HEADER_NAME_PATTERN = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")


@dataclass(frozen=True)
class AcraHttpResponse:
    """Transport-neutral response; raw client objects stop at the transport seam."""

    status_code: int
    body: object | None = None


class AcraHttpTransport(Protocol):
    """Minimal HTTP seam used by the sandbox connector."""

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> AcraHttpResponse: ...


class AcraRequestAuthorizer(Protocol):
    """Supply request authorization without exposing its mechanism downstream."""

    def authorization_headers(self) -> Mapping[str, str]: ...


class AcraResponseDecoder(Protocol):
    """Convert one external response body into the narrow ACRA source DTO."""

    def decode(
        self,
        body: object,
        *,
        requested_uen: str,
        source_endpoint: str,
        retrieved_at: datetime,
    ) -> AcraCompanyPayload: ...


@dataclass(frozen=True)
class AcraSandboxConnection:
    """Non-secret transport settings for one authorized ACRA sandbox operation."""

    base_url: str
    company_path_template: str
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        parsed = urlsplit(self.base_url)
        valid_base = (
            parsed.scheme == "https"
            and bool(parsed.netloc)
            and parsed.username is None
            and parsed.password is None
            and not parsed.query
            and not parsed.fragment
        )
        valid_path = (
            self.company_path_template.startswith("/")
            and not self.company_path_template.startswith("//")
            and self.company_path_template.count("{uen}") == 1
            and "?" not in self.company_path_template
            and "#" not in self.company_path_template
        )
        if not valid_base or not valid_path or not 0 < self.timeout_seconds <= 60:
            raise AcraConfigurationError

    def company_endpoint(self, uen: str) -> str:
        """Build a query-free endpoint reference using a safely encoded UEN."""

        encoded_uen = quote(uen, safe="")
        path = self.company_path_template.replace("{uen}", encoded_uen)
        return f"{self.base_url.rstrip('/')}{path}"


class StaticHeaderAcraRequestAuthorizer:
    """Generic static-header boundary; exact header semantics remain contract-owned."""

    def __init__(self, header_name: str, header_value: str) -> None:
        if (
            not _HEADER_NAME_PATTERN.fullmatch(header_name)
            or not header_value
            or "\r" in header_value
            or "\n" in header_value
        ):
            raise AcraConfigurationError
        self._header_name = header_name
        self._header_value = header_value

    def authorization_headers(self) -> Mapping[str, str]:
        return {self._header_name: self._header_value}


class HttpxAcraTransport:
    """TLS-verifying HTTP implementation kept behind `AcraHttpTransport`."""

    _MAX_RESPONSE_BYTES = 256 * 1024

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> AcraHttpResponse:
        with (
            httpx.Client(follow_redirects=False, verify=True) as client,
            client.stream("GET", url, headers=dict(headers), timeout=timeout_seconds) as response,
        ):
            if response.status_code != 200:
                return AcraHttpResponse(status_code=response.status_code)
            content_type = response.headers.get("content-type", "")
            if content_type.split(";", 1)[0].strip().lower() != "application/json":
                return AcraHttpResponse(status_code=response.status_code)
            declared = response.headers.get("content-length")
            if declared is not None:
                try:
                    if int(declared) > self._MAX_RESPONSE_BYTES:
                        return AcraHttpResponse(status_code=response.status_code)
                except ValueError:
                    return AcraHttpResponse(status_code=response.status_code)
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > self._MAX_RESPONSE_BYTES:
                    return AcraHttpResponse(status_code=response.status_code)
                chunks.append(chunk)
        try:
            body = cast(object, json.loads(b"".join(chunks)))
        except (UnicodeDecodeError, ValueError):
            body = None
        return AcraHttpResponse(status_code=response.status_code, body=body)


class _ProjectAddressResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block: NonBlankSourceText
    street_name: NonBlankSourceText = Field(alias="streetName")
    unit: OptionalSourceText = None
    building_name: OptionalSourceText = Field(default=None, alias="buildingName")
    postal_code: NonBlankSourceText = Field(alias="postalCode")
    country_code: NonBlankSourceText = Field(alias="countryCode")


class _ProjectCompanyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uen: NonBlankSourceText
    entity_name: NonBlankSourceText = Field(alias="entityName")
    country_code: NonBlankSourceText = Field(alias="countryCode")
    entity_type: NonBlankSourceText = Field(alias="entityType")
    registration_date: date | None = Field(default=None, alias="registrationDate")
    entity_status: TrimmedSourceText | None = Field(default=None, alias="entityStatus")
    registered_address: _ProjectAddressResponse | None = Field(
        default=None, alias="registeredAddress"
    )


class _ProjectCompanyEnvelope(BaseModel):
    """Provisional project adapter shape; not claimed as an ACRA-owned schema."""

    model_config = ConfigDict(extra="forbid")

    company: _ProjectCompanyResponse


class ProjectAcraResponseDecoder:
    """Decode sanitized Phase 02 fixtures pending the subscriber contract."""

    def decode(
        self,
        body: object,
        *,
        requested_uen: str,
        source_endpoint: str,
        retrieved_at: datetime,
    ) -> AcraCompanyPayload:
        try:
            response = _ProjectCompanyEnvelope.model_validate(body).company
        except ValidationError:
            raise AcraMalformedResponseError from None
        if response.uen.upper() != requested_uen:
            raise AcraMalformedResponseError

        address = response.registered_address
        source_address = None
        if address is not None:
            source_address = AcraAddressPayload(
                block=address.block,
                street=address.street_name,
                unit=address.unit,
                building_name=address.building_name,
                postal_code=address.postal_code,
                country_code=address.country_code,
            )
        return AcraCompanyPayload(
            uen=response.uen.upper(),
            entity_name=response.entity_name,
            country_code=response.country_code,
            entity_type=response.entity_type,
            registration_date=response.registration_date,
            entity_status=response.entity_status,
            registered_address=source_address,
            source_environment="SANDBOX",
            source_endpoint=source_endpoint,
            retrieved_at=retrieved_at,
        )


class AcraSandboxConnector:
    """Retrieve a company by UEN without leaking HTTP or auth into orchestration."""

    def __init__(
        self,
        *,
        connection: AcraSandboxConnection,
        transport: AcraHttpTransport,
        authorizer: AcraRequestAuthorizer,
        decoder: AcraResponseDecoder,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._connection = connection
        self._transport = transport
        self._authorizer = authorizer
        self._decoder = decoder
        self._clock = clock or (lambda: datetime.now(UTC))

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        normalised_uen = uen.strip().upper()
        endpoint = self._connection.company_endpoint(normalised_uen)
        try:
            headers = dict(self._authorizer.authorization_headers())
            headers["Accept"] = "application/json"
            response = self._transport.get(
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

        # PROJECT-DEFINED PROVISIONAL ADAPTER POLICY pending Q-012 confirmation.
        if response.status_code == 404:
            return None
        if response.status_code in {401, 403}:
            raise AcraAuthenticationError
        if response.status_code in {408, 504}:
            raise AcraTimeoutError
        if response.status_code == 429 or response.status_code >= 500:
            raise AcraServiceUnavailableError
        if response.status_code != 200 or response.body is None:
            raise AcraMalformedResponseError

        try:
            return self._decoder.decode(
                response.body,
                requested_uen=normalised_uen,
                source_endpoint=endpoint,
                retrieved_at=self._clock(),
            )
        except AcraMalformedResponseError:
            raise
        except Exception:
            raise AcraMalformedResponseError from None

    def fetch_officers(self, uen: str) -> AcraOfficersPayload:
        """Fail closed: Q-012 supplies no authoritative sandbox operation."""

        del uen
        raise AcraServiceUnavailableError

    def fetch_ownership_parties(self, uen: str) -> AcraOwnershipPartiesPayload:
        """Fail closed: Q-012 supplies no authoritative sandbox operation."""

        del uen
        raise AcraServiceUnavailableError

    def fetch_relationships(self, uen: str) -> AcraRelationshipsPayload:
        """Fail closed: Q-012 supplies no authoritative sandbox operation."""

        del uen
        raise AcraServiceUnavailableError
