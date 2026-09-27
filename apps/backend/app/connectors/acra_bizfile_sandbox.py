"""Dormant BizFile connector plus strict official-Mock-compatible decoders.

The connector in this module remains uncomposed. Its strict decoders are reused by the
separate official API Marketplace Mock connector after the authorized 2026-09-26
observations proved compatibility for two response shapes. Q-012 remains open; this
proves neither subscriber Sandbox nor Live interoperability:

  - GET {base}/entityQuery/entityBasicInformation?uen=...
  - GET {base}/entityQuery/coShareholdersDetails?uen=...

IMPORTANT -- read before wiring this in:
  1. Auth: `NoAuthAcraAuthorizer` remains only as a historical direct-test seam. The
     official runtime uses its dedicated OAuth client and raw `token` header; the
     dormant connector does not own authentication.
  2. `source_environment` is `MOCK` for the fixed official Mock lane only. It is not a
     generic Sandbox, Production, or Live claim.
  3. Every field marked NOTE below remains project-derived or incomplete even though
     the observed official Mock entity/shareholder payloads decoded successfully:
       - entity_status: not present in the sample at all -- left None.
       - country_code: not present in the sample -- defaulted to "SG".
       - entity_type: mapped from entityConstnDetailsAndType.constitution;
         confirm this is the right analog across entity types.
       - ownership_percentage: the shareholders response gives raw `shareAllotted`
         counts. A separate capital identity does not establish a compatible
         same-entity denominator -- left unset rather than guessed.
       - non-empty "grouping" is rejected because its member and ownership semantics
         remain unconfirmed.
   4. No sample was provided for a relationships/ownership-graph endpoint,
      so `fetch_relationships` makes no network call and returns an explicitly
      empty typed result; this is not evidence of an authoritative endpoint.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal
from urllib.parse import urlencode, urlsplit, urlunsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

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
    """Non-secret URL construction for the dormant sample-shaped endpoints."""

    base_url: str = "https://api-sandbox.bizfile.gov.sg/api/acra"
    company_query_path: str = "/entityQuery/entityBasicInformation"
    shareholders_query_path: str = "/entityQuery/coShareholdersDetails"
    business_profile_query_path: str = "/entityQuery/businessProfile"
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
            for path in (
                self.company_query_path,
                self.shareholders_query_path,
                self.business_profile_query_path,
            )
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

    def business_profile_endpoint(self, uen: str) -> str:
        """Construct the dormant URL only; no connector operation calls it."""

        return self._endpoint(self.business_profile_query_path, uen)


class NoAuthAcraAuthorizer:
    """Historical no-op authorizer retained only for isolated decoder/transport tests.

    Authentication for any other operation remains deferred pending the
    authoritative ACRA contract requested by Q-012.
    """

    def authorization_headers(self) -> Mapping[str, str]:
        return {}


def _provenance_endpoint(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _has_explicit_empty_entities(body: object) -> bool:
    return (
        isinstance(body, Mapping)
        and "entities" in body
        and isinstance(body["entities"], (list, tuple))
        and not body["entities"]
    )


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
        if len(envelope.entities) != 1:
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
        if len(envelope.entities) != 1:
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
    share_allotted: Decimal | None = Field(
        default=None,
        alias="shareAllotted",
        ge=Decimal("0"),
        max_digits=18,
        decimal_places=6,
    )

    @field_validator("share_allotted", mode="before")
    @classmethod
    def share_allotted_must_be_exact(cls, value: object) -> object:
        if isinstance(value, (float, bool)):
            raise ValueError("shareAllotted must use exact Decimal-compatible input")
        return value


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

    def __init__(self, *, include_withdrawn: bool = False) -> None:
        self._include_withdrawn = include_withdrawn

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
        if len(envelope.entities) != 1:
            raise AcraMalformedResponseError
        entity = envelope.entities[0]
        if entity.uen.upper() != requested_uen:
            raise AcraMalformedResponseError

        if entity.shareholders is not None and entity.shareholders.grouping:
            # The supplied collection names grouping but provides no authoritative
            # member schema or ownership semantics. Fail closed instead of flattening.
            raise AcraMalformedResponseError
        raw_shareholders = entity.shareholders.individual if entity.shareholders else ()
        selected = (
            raw_shareholders
            if self._include_withdrawn
            else tuple(
                holder
                for holder in raw_shareholders
                if not holder.status or holder.status.strip().lower() != "withdrawn"
            )
        )
        parties: list[AcraOwnershipPartyPayload] = []
        for holder in selected:
            category = holder.shareholder_category.strip().lower()
            party_type: Literal["NATURAL_PERSON", "LEGAL_ENTITY"]
            if category == "corporate":
                party_type = "LEGAL_ENTITY"
            elif category == "individual":
                party_type = "NATURAL_PERSON"
            else:
                raise AcraMalformedResponseError
            parties.append(
                AcraOwnershipPartyPayload(
                    party_id=holder.shareholder_id,
                    party_type=party_type,
                    name=holder.shareholder_name,
                    registration_identifier=None,
                    country=None,  # NOTE: not present in sample
                    source_category=holder.shareholder_category,
                    source_status=holder.status,
                    share_allotted=holder.share_allotted,
                    ownership_percentage=None,  # NOTE: see module docstring, point 3
                )
            )
        return AcraOwnershipPartiesPayload(
            uen=entity.uen.upper(),
            ownership_parties=tuple(parties),
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

    Direct construction retains a historical no-auth test seam. Runtime composition
    refuses that default: authoritative authentication remains blocked by Q-012.
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
        if _has_explicit_empty_entities(response.body):
            return None
        try:
            return self._company_decoder.decode(
                response.body,
                requested_uen=normalised_uen,
                source_endpoint=_provenance_endpoint(endpoint),
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
        if _has_explicit_empty_entities(response.body):
            return AcraOfficersPayload(
                uen=normalised_uen,
                officers=(),
                source_environment="MOCK",
                source_endpoint=_provenance_endpoint(endpoint),
                retrieved_at=self._clock(),
            )
        try:
            return self._officers_decoder.decode(
                response.body,
                requested_uen=normalised_uen,
                source_endpoint=_provenance_endpoint(endpoint),
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
        if _has_explicit_empty_entities(response.body):
            return AcraOwnershipPartiesPayload(
                uen=normalised_uen,
                ownership_parties=(),
                source_environment="MOCK",
                source_endpoint=_provenance_endpoint(endpoint),
                retrieved_at=self._clock(),
            )
        try:
            return self._ownership_decoder.decode(
                response.body,
                requested_uen=normalised_uen,
                source_endpoint=_provenance_endpoint(endpoint),
                retrieved_at=self._clock(),
            )
        except AcraMalformedResponseError:
            raise
        except Exception:
            raise AcraMalformedResponseError from None

    def fetch_relationships(self, uen: str) -> AcraRelationshipsPayload:
        """Return valid absence; no relationship transport contract is claimed."""

        normalised_uen = uen.strip().upper()
        return AcraRelationshipsPayload(
            uen=normalised_uen,
            relationships=(),
            source_environment="MOCK",
            source_endpoint=_provenance_endpoint(
                self._connection.shareholders_endpoint(normalised_uen)
            ),
            retrieved_at=self._clock(),
        )
