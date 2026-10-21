"""Bounded HTTPS adapter for the sponsor-supplied GoldTier XPI sandbox dialect."""

from __future__ import annotations

import json
import re
import ssl
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol
from urllib.parse import urlencode, urlsplit

import httpx
from pydantic import SecretStr, ValidationError

from app.connectors.errors import (
    ConnectorError,
    MutationOutcomeUncertainError,
    MutationUncertaintyReason,
    PublicConnectorError,
    public_connector_error,
)
from app.connectors.goldtier_models import (
    GoldTierOperationResult,
    GoldTierOutcome,
    GoldTierRequestMetadata,
    GoldTierSearchCandidate,
    GoldTierSearchOutcome,
    GoldTierSearchResult,
)
from app.connectors.goldtier_xpi_models import (
    XpiAmendCustomerRequest,
    XpiCreateCustomerPolicyRequest,
    XpiCreateCustomerRequest,
    XpiCustomerSearchRequest,
)
from app.domain.target_submission import GoldTierProviderMode

_ENVIRONMENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")


class GoldTierXpiConfigurationError(ConnectorError):
    code = "GT_XPI_CONFIGURATION_ERROR"
    public_message = "The GoldTier sandbox connector is not configured for authorized use."


class GoldTierXpiWritesDisabledError(ConnectorError):
    code = "GT_XPI_WRITES_DISABLED"
    public_message = "GoldTier sandbox writes are disabled."


class GoldTierXpiTimeoutError(ConnectorError):
    code = "GT_XPI_TIMEOUT"
    public_message = "The GoldTier sandbox request timed out."


def _observed_status(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and 100 <= value <= 599:
        return value
    return None


class GoldTierXpiObservedStatusError(ConnectorError):
    """Fixed public failure that retains only a bounded observed HTTP status."""

    def __init__(
        self,
        internal_context: object | None = None,
        *,
        upstream_status: int | None = None,
    ) -> None:
        super().__init__(internal_context)
        self.upstream_status = _observed_status(upstream_status)


class GoldTierXpiServiceUnavailableError(GoldTierXpiObservedStatusError):
    code = "GT_XPI_SERVICE_UNAVAILABLE"
    public_message = "The GoldTier sandbox service is unavailable."


class GoldTierXpiMalformedResponseError(GoldTierXpiObservedStatusError):
    code = "GT_XPI_MALFORMED_RESPONSE"
    public_message = "The GoldTier sandbox returned an unexpected response."


class GoldTierXpiResponseTooLargeError(GoldTierXpiMalformedResponseError):
    pass


class GoldTierXpiResponseDecodeError(GoldTierXpiMalformedResponseError):
    pass


# Project-defined Search categories for generic HTTP statuses. The XPI contract does
# not define 401/403/429 Search semantics, so these codes claim no sponsor meaning.
class GoldTierXpiAuthorizationError(GoldTierXpiObservedStatusError):
    code = "GT_XPI_AUTHORIZATION_FAILED"
    public_message = "The GoldTier sandbox did not authorize the request."


class GoldTierXpiRateLimitedError(GoldTierXpiObservedStatusError):
    code = "GT_XPI_RATE_LIMITED"
    public_message = "The GoldTier sandbox rate-limited the request."


XPI_SEARCH_FAILURE_CODES = frozenset({"GT_XPI_SEARCH_INVALID", "GT_XPI_SERVICE_UNAVAILABLE"})

_TRUSTED_XPI_SEARCH_ERRORS: tuple[tuple[type[ConnectorError], PublicConnectorError], ...] = (
    (
        GoldTierXpiConfigurationError,
        PublicConnectorError(
            code="GT_XPI_CONFIGURATION_ERROR",
            message="The GoldTier sandbox connector is not configured for authorized use.",
        ),
    ),
    (
        GoldTierXpiTimeoutError,
        PublicConnectorError(
            code="GT_XPI_TIMEOUT",
            message="The GoldTier sandbox request timed out.",
        ),
    ),
    (
        GoldTierXpiServiceUnavailableError,
        PublicConnectorError(
            code="GT_XPI_SERVICE_UNAVAILABLE",
            message="The GoldTier sandbox service is unavailable.",
        ),
    ),
    (
        GoldTierXpiMalformedResponseError,
        PublicConnectorError(
            code="GT_XPI_MALFORMED_RESPONSE",
            message="The GoldTier sandbox returned an unexpected response.",
        ),
    ),
    (
        GoldTierXpiAuthorizationError,
        PublicConnectorError(
            code="GT_XPI_AUTHORIZATION_FAILED",
            message="The GoldTier sandbox did not authorize the request.",
        ),
    ),
    (
        GoldTierXpiRateLimitedError,
        PublicConnectorError(
            code="GT_XPI_RATE_LIMITED",
            message="The GoldTier sandbox rate-limited the request.",
        ),
    ),
)


def public_goldtier_xpi_search_error(error: ConnectorError) -> PublicConnectorError:
    """Return fixed public fields for trusted XPI Search failures only."""

    for error_type, public_error in _TRUSTED_XPI_SEARCH_ERRORS:
        if isinstance(error, error_type):
            return public_error
    return public_connector_error(error)


def observed_goldtier_xpi_search_status(error: ConnectorError) -> int | None:
    """Return the HTTP status a trusted XPI failure observed, if it is retainable (200-599)."""

    if isinstance(error, GoldTierXpiObservedStatusError) and error.upstream_status is not None:
        return error.upstream_status if error.upstream_status >= 200 else None
    return None


def _search_status_error(status_code: int) -> GoldTierXpiObservedStatusError:
    if status_code in {401, 403}:
        return GoldTierXpiAuthorizationError(upstream_status=status_code)
    if status_code == 429:
        return GoldTierXpiRateLimitedError(upstream_status=status_code)
    return GoldTierXpiMalformedResponseError(upstream_status=status_code)


class GoldTierMutationOutcomeUncertainError(MutationOutcomeUncertainError):
    code = "GT_XPI_MUTATION_OUTCOME_UNCERTAIN"
    public_message = (
        "The GoldTier sandbox mutation outcome is uncertain and cannot be replayed automatically."
    )


@dataclass(frozen=True)
class GoldTierXpiHttpResponse:
    status_code: int
    body: object | None = None


class GoldTierXpiHttpTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        json_body: object | None,
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> GoldTierXpiHttpResponse: ...


class HttpxGoldTierXpiTransport:
    """TLS-1.3-only, certificate-verifying transport with bounded response reads."""

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        json_body: object | None,
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> GoldTierXpiHttpResponse:
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.maximum_version = ssl.TLSVersion.TLSv1_3
        body = (
            json.dumps(json_body, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
            if json_body is not None
            else None
        )
        with httpx.Client(verify=context, follow_redirects=False) as client, client.stream(
            method,
            url,
            headers=dict(headers),
            content=body,
            timeout=timeout_seconds,
        ) as response:
            retained = bytearray()
            for chunk in response.iter_bytes():
                retained.extend(chunk)
                if len(retained) > max_response_bytes:
                    raise GoldTierXpiResponseTooLargeError(upstream_status=response.status_code)
            parsed: object | None = None
            if retained:
                try:
                    parsed = json.loads(retained)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    # Only the status survives; the undecodable body is discarded.
                    raise GoldTierXpiResponseDecodeError(
                        upstream_status=response.status_code
                    ) from None
            return GoldTierXpiHttpResponse(
                status_code=response.status_code,
                body=parsed,
            )


@dataclass(frozen=True)
class GoldTierXpiSandboxConnection:
    base_url: str
    environment: str
    user_id: SecretStr
    timeout_seconds: float = 10.0
    max_response_bytes: int = 128 * 1024
    allow_writes: bool = False

    def __post_init__(self) -> None:
        parsed = urlsplit(self.base_url)
        user_id = self.user_id.get_secret_value()
        if not (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and parsed.path in {"", "/"}
            and not parsed.query
            and not parsed.fragment
            and _ENVIRONMENT_PATTERN.fullmatch(self.environment)
            and user_id
            and len(user_id) <= 160
            and not any(ord(character) < 32 for character in user_id)
            and 0 < self.timeout_seconds <= 30
            and 1024 <= self.max_response_bytes <= 1024 * 1024
        ):
            raise GoldTierXpiConfigurationError

    @property
    def _root(self) -> str:
        return f"{self.base_url.rstrip('/')}/{self.environment}/gt-xpi/v1"

    def search_endpoint(self, request: XpiCustomerSearchRequest) -> str:
        return f"{self._root}/customers/search?{urlencode(request.query_items())}"

    def operation_endpoint(
        self,
        operation: Literal["SHELL", "POLICY", "AMEND", "RP_POLICY", "RP_AMEND"],
    ) -> str:
        paths = {
            "SHELL": "/customers/create",
            "POLICY": "/customers/createPolicy",
            "AMEND": "/customers/amendCustomer",
            "RP_POLICY": "/relatedParties/createPolicy",
            "RP_AMEND": "/relatedParties/amendRelatedParty",
        }
        return self._root + paths[operation]

    def headers(self, metadata: GoldTierRequestMetadata) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "user_id": self.user_id.get_secret_value(),
            "X-Correlation-Id": str(metadata.correlation_id),
        }


def _safe_identifier(value: object) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    projected = str(value).strip()
    return projected if _SAFE_ID_PATTERN.fullmatch(projected) else None


def _optional_text(value: object, max_length: int) -> str | None:
    if not isinstance(value, str):
        return None
    projected = value.strip()
    if (
        not projected
        or len(projected) > max_length
        or any(ord(character) < 32 for character in projected)
    ):
        return None
    return projected


def _candidate(raw: object) -> GoldTierSearchCandidate:
    if not isinstance(raw, dict):
        raise GoldTierXpiMalformedResponseError
    party_id = _safe_identifier(raw.get("goldTierId", raw.get("goldTierID")))
    if party_id is None:
        raise GoldTierXpiMalformedResponseError
    country = _optional_text(raw.get("countryOfIncorporation"), 3)
    if country is not None and not re.fullmatch(r"[A-Za-z]{2,3}", country):
        country = None
    address = raw.get("legalRegisteredAddress")
    safe_address = None
    if isinstance(address, str):
        safe_address = _optional_text(address, 240)
    elif isinstance(address, dict):
        address_parts = tuple(
            item
            for item in (
                _optional_text(address.get("street1"), 160),
                _optional_text(address.get("street2"), 160),
                _optional_text(address.get("city"), 80),
                _optional_text(address.get("state"), 80),
                _optional_text(address.get("zip"), 32),
                _optional_text(address.get("countryIso2"), 3),
            )
            if item is not None
        )
        if address_parts:
            safe_address = ", ".join(address_parts)[:240]
    try:
        return GoldTierSearchCandidate(
            party_id=party_id,
            registration_number=_optional_text(raw.get("registrationNumber"), 64),
            country=country,
            legal_name=_optional_text(raw.get("legalName"), 160),
            legal_form=_optional_text(raw.get("legalForm"), 80),
            registered_address=safe_address,
        )
    except ValidationError:
        raise GoldTierXpiMalformedResponseError from None


def _response_identifier(body: object, keys: frozenset[str]) -> str | None:
    found: list[str] = []
    visited = 0

    def visit(value: object, depth: int) -> None:
        nonlocal visited
        visited += 1
        if visited > 64 or depth > 4:
            raise GoldTierXpiMalformedResponseError
        if isinstance(value, dict):
            for name, item in value.items():
                if name in keys:
                    identifier = _safe_identifier(item)
                    if identifier is not None:
                        found.append(identifier)
                elif isinstance(item, (dict, list)):
                    visit(item, depth + 1)
        elif isinstance(value, list):
            for item in value[:25]:
                visit(item, depth + 1)

    visit(body, 0)
    unique = tuple(dict.fromkeys(found))
    if len(unique) > 1:
        raise GoldTierXpiMalformedResponseError
    return unique[0] if unique else None


class GoldTierXpiSandboxConnector:
    """Execute one explicit XPI dialect; never fall back to the Mock adapter."""

    environment = GoldTierProviderMode.SANDBOX

    def __init__(
        self,
        *,
        connection: GoldTierXpiSandboxConnection,
        transport: GoldTierXpiHttpTransport | None = None,
    ) -> None:
        self._connection = connection
        self._transport = transport or HttpxGoldTierXpiTransport()

    def _request(
        self,
        method: Literal["GET", "POST"],
        url: str,
        *,
        metadata: GoldTierRequestMetadata,
        body: object | None = None,
        mutation: bool = False,
    ) -> GoldTierXpiHttpResponse:
        if mutation and not self._connection.allow_writes:
            raise GoldTierXpiWritesDisabledError
        try:
            response = self._transport.request(
                method,
                url,
                headers=self._connection.headers(metadata),
                json_body=body,
                timeout_seconds=self._connection.timeout_seconds,
                max_response_bytes=self._connection.max_response_bytes,
            )
        except GoldTierXpiResponseTooLargeError:
            if mutation:
                raise GoldTierMutationOutcomeUncertainError(
                    reason=MutationUncertaintyReason.RESPONSE_TOO_LARGE
                ) from None
            raise
        except GoldTierXpiResponseDecodeError:
            if mutation:
                raise GoldTierMutationOutcomeUncertainError(
                    reason=MutationUncertaintyReason.RESPONSE_DECODE
                ) from None
            raise
        except ConnectorError:
            raise
        except httpx.TimeoutException:
            if mutation:
                raise GoldTierMutationOutcomeUncertainError(
                    reason=MutationUncertaintyReason.TIMEOUT
                ) from None
            raise GoldTierXpiTimeoutError from None
        except httpx.TransportError:
            if mutation:
                raise GoldTierMutationOutcomeUncertainError(
                    reason=MutationUncertaintyReason.TRANSPORT
                ) from None
            raise GoldTierXpiServiceUnavailableError from None
        except Exception:
            if mutation:
                raise GoldTierMutationOutcomeUncertainError from None
            raise GoldTierXpiServiceUnavailableError from None
        if not isinstance(response, GoldTierXpiHttpResponse):
            if mutation:
                raise GoldTierMutationOutcomeUncertainError
            raise GoldTierXpiMalformedResponseError
        # XPI supplies no atomic no-application guarantee for unexpected statuses.
        # Preserve the attempted ledger operation for read-only reconciliation.
        if mutation and response.status_code not in {200, 400}:
            raise GoldTierMutationOutcomeUncertainError(
                reason=MutationUncertaintyReason.UNEXPECTED_STATUS
            )
        return response

    def search_party(
        self,
        request: XpiCustomerSearchRequest,
        metadata: GoldTierRequestMetadata,
    ) -> GoldTierSearchResult:
        try:
            response = self._request(
                "GET",
                self._connection.search_endpoint(request),
                metadata=metadata,
            )
        except GoldTierXpiResponseDecodeError as exc:
            # A non-JSON error body keeps its status category but remains an exception,
            # so every Search caller retains its existing infrastructure-failure path.
            status = exc.upstream_status
            if status is None:
                raise
            if status >= 500:
                raise GoldTierXpiServiceUnavailableError(upstream_status=status) from None
            if status in {401, 403, 429}:
                raise _search_status_error(status) from None
            raise
        if response.status_code == 400:
            return GoldTierSearchResult(
                outcome=GoldTierSearchOutcome.FAILURE,
                status_code=400,
                error_code="GT_XPI_SEARCH_INVALID",
                message="GoldTier sandbox Search rejected the request.",
            )
        if response.status_code >= 500:
            return GoldTierSearchResult(
                outcome=GoldTierSearchOutcome.FAILURE,
                status_code=response.status_code,
                error_code="GT_XPI_SERVICE_UNAVAILABLE",
                message="GoldTier sandbox Search is unavailable.",
            )
        if response.status_code != 200:
            raise _search_status_error(response.status_code)
        if not isinstance(response.body, list) or len(response.body) > 25:
            raise GoldTierXpiMalformedResponseError(upstream_status=200)
        try:
            candidates = tuple(_candidate(item) for item in response.body)
        except GoldTierXpiMalformedResponseError:
            raise GoldTierXpiMalformedResponseError(upstream_status=200) from None
        if not candidates:
            return GoldTierSearchResult(
                outcome=GoldTierSearchOutcome.NO_MATCH,
                status_code=200,
                message="GoldTier sandbox Search returned no candidate.",
            )
        if len(candidates) == 1:
            return GoldTierSearchResult(
                outcome=GoldTierSearchOutcome.MATCH_FOUND,
                status_code=200,
                matched_party_id=candidates[0].party_id,
                candidates=candidates,
                message="GoldTier sandbox Search returned one bounded candidate.",
            )
        return GoldTierSearchResult(
            outcome=GoldTierSearchOutcome.MULTIPLE_MATCHES,
            status_code=200,
            candidates=candidates,
            message="GoldTier sandbox Search returned multiple bounded candidates.",
        )

    def create_shell_customer(
        self,
        request: XpiCreateCustomerRequest,
        metadata: GoldTierRequestMetadata,
    ) -> GoldTierOperationResult:
        response = self._request(
            "POST",
            self._connection.operation_endpoint("SHELL"),
            metadata=metadata,
            body=request.model_dump(by_alias=True, exclude_none=True),
            mutation=True,
        )
        if response.status_code != 200:
            return GoldTierOperationResult(
                outcome=GoldTierOutcome.VALIDATION_FAILED,
                status_code=response.status_code,
                status="SHELL_FAILED",
                error_code=(
                    "GT_XPI_SHELL_INVALID"
                    if response.status_code == 400
                    else "GT_XPI_SERVICE_UNAVAILABLE"
                ),
                message="GoldTier sandbox Shell returned a controlled failure.",
            )
        try:
            party_id = _response_identifier(
                response.body,
                frozenset({"goldTierId", "goldTierID"}),
            )
        except GoldTierXpiMalformedResponseError:
            raise GoldTierMutationOutcomeUncertainError(
                reason=MutationUncertaintyReason.RESPONSE_DECODE
            ) from None
        if party_id is None:
            raise GoldTierMutationOutcomeUncertainError(
                reason=MutationUncertaintyReason.RESPONSE_DECODE
            )
        return GoldTierOperationResult(
            outcome=GoldTierOutcome.SUCCESS,
            status_code=200,
            party_id=party_id,
            status="SHELL_CREATED",
            message="GoldTier sandbox Shell succeeded.",
        )

    def create_policy(
        self,
        request: XpiCreateCustomerPolicyRequest,
        metadata: GoldTierRequestMetadata,
    ) -> GoldTierOperationResult:
        response = self._request(
            "POST",
            self._connection.operation_endpoint("POLICY"),
            metadata=metadata,
            body=request.model_dump(by_alias=True, exclude_none=True),
            mutation=True,
        )
        if response.status_code != 200:
            return GoldTierOperationResult(
                outcome=GoldTierOutcome.VALIDATION_FAILED,
                status_code=response.status_code,
                party_id=request.goldtier_id,
                status="VALIDATION_FAILED",
                error_code=(
                    "GT_XPI_POLICY_INVALID"
                    if response.status_code == 400
                    else "GT_XPI_SERVICE_UNAVAILABLE"
                ),
                message="GoldTier sandbox Policy returned a controlled failure.",
            )
        try:
            policy_id = _response_identifier(
                response.body, frozenset({"policyId", "policyID"})
            )
        except GoldTierXpiMalformedResponseError:
            raise GoldTierMutationOutcomeUncertainError(
                reason=MutationUncertaintyReason.RESPONSE_DECODE
            ) from None
        return GoldTierOperationResult(
            outcome=GoldTierOutcome.SUCCESS,
            status_code=200,
            party_id=request.goldtier_id,
            policy_id=policy_id,
            status="POLICY_CREATED",
            message="GoldTier sandbox Policy succeeded.",
        )

    def amend_party(
        self,
        party_id: str,
        request: XpiAmendCustomerRequest,
        metadata: GoldTierRequestMetadata,
    ) -> GoldTierOperationResult:
        if request.goldtier_id != party_id:
            raise GoldTierXpiConfigurationError
        response = self._request(
            "POST",
            self._connection.operation_endpoint("AMEND"),
            metadata=metadata,
            body=request.model_dump(by_alias=True, exclude_none=True),
            mutation=True,
        )
        if response.status_code != 200:
            return GoldTierOperationResult(
                outcome=GoldTierOutcome.VALIDATION_FAILED,
                status_code=response.status_code,
                party_id=party_id,
                status="AMEND_FAILED",
                error_code=(
                    "GT_XPI_AMEND_INVALID"
                    if response.status_code == 400
                    else "GT_XPI_SERVICE_UNAVAILABLE"
                ),
                message="GoldTier sandbox Amend returned a controlled failure.",
            )
        return GoldTierOperationResult(
            outcome=GoldTierOutcome.SUCCESS,
            status_code=200,
            party_id=party_id,
            status="ENRICHED",
            message="GoldTier sandbox Amend succeeded.",
        )
