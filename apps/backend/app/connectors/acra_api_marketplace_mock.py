"""Official ACRA API Marketplace Mock connector.

This lane is fixed to the official Mock host and two read-only EIQ operations. It is
separate from the local synthetic Mock and generic sandbox seams and never falls back.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlencode, urlsplit, urlunsplit

import httpx

from app.connectors.acra import (
    AcraCompanyPayload,
    AcraOfficersPayload,
    AcraOwnershipPartiesPayload,
    AcraRelationshipsPayload,
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
ACRA_API_MARKETPLACE_MOCK_RESPONSE_MAX_BYTES = 256 * 1024


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

    def fetch_relationships(self, uen: str) -> AcraRelationshipsPayload:
        """Stop without dispatch or invented evidence: the contract is unsupported."""

        raise AcraOperationUnsupportedError
