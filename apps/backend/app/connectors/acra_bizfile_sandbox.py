"""Real Bizfile Sandbox ACRA connector adapter, mapping actual entityQuery
API responses onto the source-boundary contract defined in `acra.py`.

Base URL confirmed: https://api-sandbox.bizfile.gov.sg/api/acra
This is still "SANDBOX" tier per the existing `SourceEnvironmentText`
Literal in acra.py -- no change needed there. This module is meant to
replace the placeholder decoder/connection in acra_sandbox.py (which was
built against a fictional `{"company": {...}}` fixture shape and a
path-param URL style neither of which match the real API -- see the
code-walkthrough in chat for details), not add a new tier alongside it.

Built from two sample Postman responses:
  - GET {base}/entityQuery/entityBasicInformation?uen=...
  - GET {base}/entityQuery/coShareholdersDetails?uen=...

IMPORTANT -- read before wiring this in:
  1. Auth: confirmed via Postman that these endpoints need no
     Authorization header at all (200 with none sent). Use
     `NoAuthAcraAuthorizer` below. The OAuth2 class is kept on standby
     in case another Marketplace endpoint needs it later.
  2. `source_environment` is tagged "MOCK" (matching the existing
     Literal in acra.py) based on the "APIMarketplace-Mock" Postman
     environment name and the lack of auth -- confirm this against your
     API Marketplace dashboard, since "MOCK" and "SANDBOX" mean
     different things elsewhere in this codebase (see mock_acra.py vs.
     acra_sandbox.py).
  3. Every field marked NOTE below is a best-effort mapping made from a
     single sample response and needs confirming against full API docs
     or a second sample before this goes near real filings:
       - entity_status: not present in the sample at all -- left None.
       - country_code: not present in the sample -- defaulted to "SG".
       - entity_type: mapped from entityConstnDetailsAndType.constitution;
         confirm this is the right analog across entity types.
       - ownership_percentage: the shareholders response gives raw
         `shareAllotted` counts, not percentages, and no total issued
         share figure -- left unset rather than guessed.
       - "grouping" array in shareholders response is unmapped (always
         empty in the sample; shape unconfirmed).
  4. No sample was provided for a relationships/ownership-graph endpoint,
     so `fetch_relationships` fails closed, same as the sandbox adapter.
"""

import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from urllib.parse import urlencode, urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.connectors.acra import (
    AcraAddressPayload,
    AcraCompanyPayload,
    AcraOfficerPayload,
    AcraOfficersPayload,
    AcraOwnershipPartiesPayload,
    AcraOwnershipPartyPayload,
    AcraRelationshipsPayload,
    NonBlankSourceText,
    OptionalSourceText,
    TrimmedSourceText,
)
from app.connectors.acra_sandbox import (
    AcraHttpResponse,
    AcraHttpTransport,
    AcraRequestAuthorizer,
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


@dataclass(frozen=True)
class AcraBizfileConnection:
    """Non-secret transport settings for the real entityQuery endpoints."""

    base_url: str = "https://api-sandbox.bizfile.gov.sg/api/acra"
    company_query_path: str = "/entityQuery/entityBasicInformation"
    shareholders_query_path: str = "/entityQuery/coShareholdersDetails"
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
        valid_paths = all(
            path.startswith("/")
            and not path.startswith("//")
            and "?" not in path
            and "#" not in path
            for path in (self.company_query_path, self.shareholders_query_path)
        )
        if not valid_base or not valid_paths or not 0 < self.timeout_seconds <= 60:
            raise AcraConfigurationError

    def _endpoint(self, path: str, uen: str) -> str:
        query = urlencode({"uen": uen})
        return f"{self.base_url.rstrip('/')}{path}?{query}"

    def company_endpoint(self, uen: str) -> str:
        return self._endpoint(self.company_query_path, uen)

    def shareholders_endpoint(self, uen: str) -> str:
        return self._endpoint(self.shareholders_query_path, uen)


class NoAuthAcraAuthorizer:
    """No-op authorizer for the confirmed no-auth-required Mock endpoints.

    Confirmed via Postman: GET requests to these entityQuery endpoints
    return 200 with no Authorization header at all. Use this rather than
    the OAuth2 authorizer below unless/until you hit an endpoint that
    actually demands a token.
    """

    def authorization_headers(self) -> Mapping[str, str]:
        return {}


class OAuth2ClientCredentialsAcraAuthorizer:
    """Fetch and cache a bearer token via the OAuth2 client-credentials grant.

    NOT CURRENTLY NEEDED: confirmed via Postman that these entityQuery
    endpoints return 200 with no auth at all -- use `NoAuthAcraAuthorizer`
    above instead. Keeping this here in case a different ACRA API
    Marketplace endpoint (filing, subscriptions, etc.) does require OAuth2.

    FILL IN before use: `token_url` -- get this from your Postman
    collection/request's Authorization tab -> "Configure New Token" ->
    "Access Token URL". Client id/secret should come from env vars /
    secrets manager, never hardcoded.

    Caches the token in memory and refetches shortly before it expires.
    Thread-safe enough for a typical request-per-thread web app; swap for
    a shared cache (Redis etc.) if you run multiple processes.
    """

    def __init__(
        self,
        *,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: str | None = None,
        transport: httpx.Client | None = None,
        clock: Callable[[], float] | None = None,
        expiry_leeway_seconds: float = 30.0,
    ) -> None:
        parsed = urlsplit(token_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise AcraConfigurationError
        if not client_id or not client_secret:
            raise AcraConfigurationError
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._scope = scope
        self._transport = transport
        self._clock = clock or time.monotonic
        self._expiry_leeway_seconds = expiry_leeway_seconds
        self._lock = threading.Lock()
        self._cached_token: str | None = None
        self._cached_expiry: float = 0.0

    def authorization_headers(self) -> Mapping[str, str]:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def _get_token(self) -> str:
        with self._lock:
            if self._cached_token is not None and self._clock() < self._cached_expiry:
                return self._cached_token
            token, ttl_seconds = self._request_token()
            self._cached_token = token
            self._cached_expiry = self._clock() + max(
                ttl_seconds - self._expiry_leeway_seconds, 0
            )
            return token

    def _request_token(self) -> tuple[str, float]:
        data = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        if self._scope:
            data["scope"] = self._scope
        try:
            client = self._transport or httpx.Client(verify=True)
            with client as http_client:
                response = http_client.post(self._token_url, data=data, timeout=10.0)
        except httpx.TimeoutException:
            raise AcraTimeoutError from None
        except httpx.TransportError:
            raise AcraServiceUnavailableError from None
        if response.status_code != 200:
            raise AcraAuthenticationError
        try:
            body = response.json()
            access_token = str(body["access_token"])
            expires_in = float(body.get("expires_in", 300))
        except (ValueError, KeyError, TypeError):
            raise AcraAuthenticationError from None
        return access_token, expires_in


def _combine_unit(level_no: str | None, unit_no: str | None) -> str | None:
    """Merge separate levelNo/unitNo fields into the DTO's single `unit` string."""

    if not level_no and not unit_no:
        return None
    level = level_no.zfill(2) if level_no and level_no.isdigit() else level_no
    unit = unit_no.zfill(2) if unit_no and unit_no.isdigit() else unit_no
    if level and unit:
        return f"#{level}-{unit}"
    return f"#{level or unit}"


# ---------------------------------------------------------------------------
# entityBasicInformation response models (raw, tolerant of unknown fields --
# real government API responses may carry more fields than this sample showed)
# ---------------------------------------------------------------------------


class _RealAddress(BaseModel):
    model_config = ConfigDict(extra="ignore")

    blkhse_no: NonBlankSourceText = Field(alias="blkhseNo")
    street_name: NonBlankSourceText = Field(alias="streetName")
    level_no: OptionalSourceText = Field(default=None, alias="levelNo")
    unit_no: OptionalSourceText = Field(default=None, alias="unitNo")
    building_name: OptionalSourceText = Field(default=None, alias="buildingName")
    postal_code: NonBlankSourceText = Field(alias="postalCode")


class _RealAddressDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")

    registered_address: _RealAddress | None = Field(default=None, alias="registeredAddress")


class _RealKeyDates(BaseModel):
    model_config = ConfigDict(extra="ignore")

    registration_date: date | None = Field(default=None, alias="registrationDate")
    # NOTE: no entity-status field observed anywhere in the sample response,
    # despite "entityStatusEffectiveDate" implying one exists somewhere in
    # the full schema. Add the real field here once confirmed.


class _RealConstitution(BaseModel):
    model_config = ConfigDict(extra="ignore")

    constitution: TrimmedSourceText | None = None


class _RealOfficer(BaseModel):
    model_config = ConfigDict(extra="ignore")

    officer_id: NonBlankSourceText = Field(alias="officerId")
    officer_name: NonBlankSourceText = Field(alias="officerName")
    position: TrimmedSourceText | None = None
    appointed_date: date | None = Field(default=None, alias="appointedDate")
    withdrawal_date: date | None = Field(default=None, alias="withdrawalDate")
    status: TrimmedSourceText | None = None


class _RealOfficersRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    officer_appointment_details: tuple[_RealOfficer, ...] = Field(
        default=(), alias="officerAppointmentDetails"
    )


class _RealEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    uen: NonBlankSourceText
    name: NonBlankSourceText
    entity_registration_key_dates: _RealKeyDates | None = Field(
        default=None, alias="entityRegistrationKeyDates"
    )
    entity_registered_address_details: _RealAddressDetails | None = Field(
        default=None, alias="entityRegisteredAddressDetails"
    )
    entity_constn_details_and_type: _RealConstitution | None = Field(
        default=None, alias="entityConstnDetailsAndType"
    )
    entity_officers_record: _RealOfficersRecord | None = Field(
        default=None, alias="entityOfficersRecord"
    )


class _RealEntityEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore")

    entities: tuple[_RealEntity, ...] = ()


class BizfileMockCompanyDecoder:
    """Decode a real `entityBasicInformation` response into the source DTO."""

    def decode(
        self,
        body: object,
        *,
        requested_uen: str,
        source_endpoint: str,
        retrieved_at: datetime,
    ) -> AcraCompanyPayload:
        try:
            envelope = _RealEntityEnvelope.model_validate(body)
        except ValidationError:
            raise AcraMalformedResponseError from None
        if not envelope.entities:
            raise AcraMalformedResponseError
        entity = envelope.entities[0]
        if entity.uen.upper() != requested_uen:
            raise AcraMalformedResponseError

        registered_address = None
        details = entity.entity_registered_address_details
        if details is not None and details.registered_address is not None:
            raw = details.registered_address
            registered_address = AcraAddressPayload(
                block=raw.blkhse_no,
                street=raw.street_name,
                unit=_combine_unit(raw.level_no, raw.unit_no),
                building_name=raw.building_name,
                postal_code=raw.postal_code,
                country_code="SG",  # NOTE: not present in sample; defaulted
            )

        constitution = entity.entity_constn_details_and_type
        entity_type = (
            constitution.constitution
            if constitution is not None and constitution.constitution
            else "UNKNOWN"
        )

        registration_date = None
        if entity.entity_registration_key_dates is not None:
            registration_date = entity.entity_registration_key_dates.registration_date

        return AcraCompanyPayload(
            uen=entity.uen.upper(),
            entity_name=entity.name,
            country_code="SG",  # NOTE: not present in sample; defaulted
            entity_type=entity_type,
            registration_date=registration_date,
            entity_status=None,  # NOTE: no status field observed in sample
            registered_address=registered_address,
            source_environment="MOCK",
            source_endpoint=source_endpoint,
            retrieved_at=retrieved_at,
        )


class BizfileMockOfficersDecoder:
    """Decode officers embedded in the entityBasicInformation response.

    Reuses the same response body as BizfileMockCompanyDecoder -- the
    real API returns officers alongside company details in one call, so
    the connector calls the same endpoint for both.
    """

    def decode(
        self,
        body: object,
        *,
        requested_uen: str,
        source_endpoint: str,
        retrieved_at: datetime,
    ) -> AcraOfficersPayload:
        try:
            envelope = _RealEntityEnvelope.model_validate(body)
        except ValidationError:
            raise AcraMalformedResponseError from None
        if not envelope.entities:
            raise AcraMalformedResponseError
        entity = envelope.entities[0]
        if entity.uen.upper() != requested_uen:
            raise AcraMalformedResponseError

        raw_officers: tuple[_RealOfficer, ...] = ()
        if entity.entity_officers_record is not None:
            raw_officers = entity.entity_officers_record.officer_appointment_details

        officers = tuple(
            AcraOfficerPayload(
                officer_id=officer.officer_id,
                name=officer.officer_name,
                role=officer.position or "UNKNOWN",
                appointment_date=officer.appointed_date,
                cessation_date=officer.withdrawal_date,
                country=None,  # NOTE: not present in sample
            )
            for officer in raw_officers
        )
        return AcraOfficersPayload(
            uen=entity.uen.upper(),
            officers=officers,
            source_environment="MOCK",
            source_endpoint=source_endpoint,
            retrieved_at=retrieved_at,
        )


# ---------------------------------------------------------------------------
# coShareholdersDetails response models
# ---------------------------------------------------------------------------


class _RealShareholder(BaseModel):
    model_config = ConfigDict(extra="ignore")

    shareholder_category: TrimmedSourceText = Field(alias="shareholderCategory")
    shareholder_id: NonBlankSourceText = Field(alias="shareholderId")
    shareholder_name: NonBlankSourceText = Field(alias="shareholderName")
    status: TrimmedSourceText | None = None


class _RealShareholders(BaseModel):
    model_config = ConfigDict(extra="ignore")

    individual: tuple[_RealShareholder, ...] = ()
    grouping: tuple[_RealShareholder, ...] = ()  # NOTE: shape unconfirmed, always [] in sample


class _RealShareholderEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    uen: NonBlankSourceText
    name: NonBlankSourceText
    shareholders: _RealShareholders | None = None


class _RealShareholderEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore")

    entities: tuple[_RealShareholderEntity, ...] = ()


class BizfileMockOwnershipPartiesDecoder:
    """Decode `coShareholdersDetails` into ownership-party records.

    Withdrawn shareholders are filtered out (only active holdings are
    surfaced) -- confirm this matches the intended business meaning of
    "ownership parties" before relying on it.
    """

    def decode(
        self,
        body: object,
        *,
        requested_uen: str,
        source_endpoint: str,
        retrieved_at: datetime,
    ) -> AcraOwnershipPartiesPayload:
        try:
            envelope = _RealShareholderEnvelope.model_validate(body)
        except ValidationError:
            raise AcraMalformedResponseError from None
        if not envelope.entities:
            raise AcraMalformedResponseError
        entity = envelope.entities[0]
        if entity.uen.upper() != requested_uen:
            raise AcraMalformedResponseError

        raw_shareholders = entity.shareholders.individual if entity.shareholders else ()
        active = (
            holder
            for holder in raw_shareholders
            if not holder.status or holder.status.strip().lower() != "withdrawn"
        )
        parties = tuple(
            AcraOwnershipPartyPayload(
                party_id=holder.shareholder_id,
                party_type=(
                    "LEGAL_ENTITY"
                    if holder.shareholder_category.strip().lower() == "corporate"
                    else "NATURAL_PERSON"
                ),
                name=holder.shareholder_name,
                registration_identifier=None,
                country=None,  # NOTE: not present in sample
                ownership_percentage=None,  # NOTE: see module docstring, point 3
            )
            for holder in active
        )
        return AcraOwnershipPartiesPayload(
            uen=entity.uen.upper(),
            ownership_parties=parties,
            source_environment="MOCK",
            source_endpoint=source_endpoint,
            retrieved_at=retrieved_at,
        )


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------


class BizfileMockAcraConnector:
    """Retrieve company/officer/shareholder data via the Bizfile API
    Marketplace Mock-tier entityQuery endpoints.

    No auth required for these endpoints -- confirmed via Postman. The
    `authorizer` param defaults to `NoAuthAcraAuthorizer`; only override it
    if a specific endpoint you add later turns out to need one.
    """

    def __init__(
        self,
        *,
        connection: AcraBizfileConnection,
        transport: AcraHttpTransport,
        authorizer: AcraRequestAuthorizer | None = None,
        company_decoder: BizfileMockCompanyDecoder | None = None,
        officers_decoder: BizfileMockOfficersDecoder | None = None,
        ownership_decoder: BizfileMockOwnershipPartiesDecoder | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._connection = connection
        self._transport = transport
        self._authorizer = authorizer or NoAuthAcraAuthorizer()
        self._company_decoder = company_decoder or BizfileMockCompanyDecoder()
        self._officers_decoder = officers_decoder or BizfileMockOfficersDecoder()
        self._ownership_decoder = ownership_decoder or BizfileMockOwnershipPartiesDecoder()
        self._clock = clock or (lambda: datetime.now(UTC))

    def _get(self, endpoint: str) -> AcraHttpResponse:
        try:
            headers = dict(self._authorizer.authorization_headers())
            headers["Accept"] = "application/json"
            return self._transport.get(
                endpoint, headers=headers, timeout_seconds=self._connection.timeout_seconds
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

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        normalised_uen = uen.strip().upper()
        endpoint = self._connection.company_endpoint(normalised_uen)
        response = self._get(endpoint)
        if response.status_code == 404:
            return None
        self._raise_for_status(response)
        try:
            return self._company_decoder.decode(
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
        normalised_uen = uen.strip().upper()
        endpoint = self._connection.company_endpoint(normalised_uen)
        response = self._get(endpoint)
        self._raise_for_status(response)
        try:
            return self._officers_decoder.decode(
                response.body,
                requested_uen=normalised_uen,
                source_endpoint=endpoint,
                retrieved_at=self._clock(),
            )
        except AcraMalformedResponseError:
            raise
        except Exception:
            raise AcraMalformedResponseError from None

    def fetch_ownership_parties(self, uen: str) -> AcraOwnershipPartiesPayload:
        normalised_uen = uen.strip().upper()
        endpoint = self._connection.shareholders_endpoint(normalised_uen)
        response = self._get(endpoint)
        self._raise_for_status(response)
        try:
            return self._ownership_decoder.decode(
                response.body,
                requested_uen=normalised_uen,
                source_endpoint=endpoint,
                retrieved_at=self._clock(),
            )
        except AcraMalformedResponseError:
            raise
        except Exception:
            raise AcraMalformedResponseError from None

    def fetch_relationships(self, uen: str) -> AcraRelationshipsPayload:
        """No confirmed real relationships endpoint -- fail closed."""

        del uen
        raise AcraServiceUnavailableError