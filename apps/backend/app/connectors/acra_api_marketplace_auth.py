"""Strict OAuth client for the official ACRA API Marketplace Mock environment."""

from __future__ import annotations

import json
import ssl
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from typing import Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StrictInt, StrictStr, ValidationError

from app.connectors.errors import (
    AcraAuthenticationError,
    AcraConfigurationError,
    AcraMalformedResponseError,
    AcraServiceUnavailableError,
    AcraTimeoutError,
    AcraUnexpectedConnectorError,
    ConnectorError,
)

ACRA_API_MARKETPLACE_MOCK_TOKEN_ENDPOINT = (
    "https://api-sandbox.bizfile.gov.sg/authorizeServer/oauth/token"
    "?grant_type=client_credentials"
)
ACRA_API_MARKETPLACE_TOKEN_HEADER_NAME = "token"
ACRA_API_MARKETPLACE_TOKEN_LIFETIME_SECONDS = 60 * 60
ACRA_API_MARKETPLACE_TOKEN_RESPONSE_MAX_BYTES = 16 * 1024
ACRA_API_MARKETPLACE_TOKEN_RENEWAL_LEEWAY_SECONDS = 60.0


def build_acra_api_marketplace_mock_basic_auth(
    *,
    client_id: SecretStr | None,
    secret_key: SecretStr | None,
) -> httpx.BasicAuth:
    """Build Mock HTTP Basic client authentication without exposing credentials."""

    if client_id is None or secret_key is None:
        raise AcraConfigurationError
    client_value = client_id.get_secret_value()
    secret_value = secret_key.get_secret_value()
    if not client_value.strip() or not secret_value.strip():
        raise AcraConfigurationError
    return httpx.BasicAuth(username=client_value, password=secret_value)


@dataclass(frozen=True)
class AcraMarketplaceTokenHttpResponse:
    """Transport-neutral, bounded token response."""

    status_code: int
    content_type: str
    body: bytes | None = field(repr=False)
    response_bytes: int
    size_limit_exceeded: bool = False


class AcraMarketplaceTokenTransport(Protocol):
    """Minimal injectable token-request seam."""

    def post(
        self,
        url: str,
        *,
        auth: httpx.BasicAuth,
        headers: Mapping[str, str],
        body: bytes,
        timeout_seconds: float,
    ) -> AcraMarketplaceTokenHttpResponse: ...


class HttpxAcraMarketplaceTokenTransport:
    """Certificate-verifying, no-redirect Mock token transport."""

    def post(
        self,
        url: str,
        *,
        auth: httpx.BasicAuth,
        headers: Mapping[str, str],
        body: bytes,
        timeout_seconds: float,
    ) -> AcraMarketplaceTokenHttpResponse:
        with (
            httpx.Client(
                auth=auth,
                follow_redirects=False,
                verify=ssl.create_default_context(),
                trust_env=False,
            ) as client,
            client.stream(
                "POST",
                url,
                headers=dict(headers),
                content=body,
                timeout=timeout_seconds,
            ) as response,
        ):
            content_type = (
                response.headers.get("content-type", "")
                .split(";", 1)[0]
                .strip()
                .lower()
            )
            declared = response.headers.get("content-length")
            if declared is not None:
                try:
                    if int(declared) > ACRA_API_MARKETPLACE_TOKEN_RESPONSE_MAX_BYTES:
                        return AcraMarketplaceTokenHttpResponse(
                            status_code=response.status_code,
                            content_type=content_type,
                            body=None,
                            response_bytes=0,
                            size_limit_exceeded=True,
                        )
                except ValueError:
                    return AcraMarketplaceTokenHttpResponse(
                        status_code=response.status_code,
                        content_type=content_type,
                        body=None,
                        response_bytes=0,
                        size_limit_exceeded=True,
                    )
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > ACRA_API_MARKETPLACE_TOKEN_RESPONSE_MAX_BYTES:
                    return AcraMarketplaceTokenHttpResponse(
                        status_code=response.status_code,
                        content_type=content_type,
                        body=None,
                        response_bytes=total,
                        size_limit_exceeded=True,
                    )
                chunks.append(chunk)
        return AcraMarketplaceTokenHttpResponse(
            status_code=response.status_code,
            content_type=content_type,
            body=b"".join(chunks),
            response_bytes=total,
        )


class _ObservedTokenResponse(BaseModel):
    """Exact schema observed from the official Mock token endpoint."""

    model_config = ConfigDict(extra="forbid")

    access_token: StrictStr = Field(min_length=1, max_length=8192, repr=False)
    expires_in: StrictInt = Field(gt=0, le=86_400)
    scope: StrictStr = Field(max_length=4096)
    token_type: StrictStr = Field(min_length=1, max_length=128)


@dataclass(frozen=True)
class _CachedToken:
    value: str = field(repr=False)
    renew_at: float


class AcraApiMarketplaceMockTokenClient:
    """Thread-safe in-memory token owner for the official Mock lane."""

    def __init__(
        self,
        *,
        client_id: SecretStr | None,
        secret_key: SecretStr | None,
        timeout_seconds: float,
        transport: AcraMarketplaceTokenTransport | None = None,
        monotonic_clock: Callable[[], float] = monotonic,
        renewal_leeway_seconds: float = ACRA_API_MARKETPLACE_TOKEN_RENEWAL_LEEWAY_SECONDS,
    ) -> None:
        if not 0 < timeout_seconds <= 30 or not 0 <= renewal_leeway_seconds <= 300:
            raise AcraConfigurationError
        self._auth = build_acra_api_marketplace_mock_basic_auth(
            client_id=client_id,
            secret_key=secret_key,
        )
        self._timeout_seconds = timeout_seconds
        self._transport = transport or HttpxAcraMarketplaceTokenTransport()
        self._clock = monotonic_clock
        self._renewal_leeway_seconds = renewal_leeway_seconds
        self._cached: _CachedToken | None = None
        self._lock = Lock()

    def access_token(self) -> str:
        """Return a cached token or obtain one without persisting/logging it."""

        with self._lock:
            now = self._clock()
            if self._cached is not None and now < self._cached.renew_at:
                return self._cached.value
            token = self._request_token()
            renew_at = now + max(
                0.0,
                float(token.expires_in) - self._renewal_leeway_seconds,
            )
            self._cached = _CachedToken(value=token.access_token, renew_at=renew_at)
            return token.access_token

    def _request_token(self) -> _ObservedTokenResponse:
        try:
            response = self._transport.post(
                ACRA_API_MARKETPLACE_MOCK_TOKEN_ENDPOINT,
                auth=self._auth,
                headers={"Content-Type": "application/json"},
                body=b"",
                timeout_seconds=self._timeout_seconds,
            )
        except ConnectorError:
            raise
        except httpx.TimeoutException:
            raise AcraTimeoutError from None
        except httpx.TransportError:
            raise AcraServiceUnavailableError from None
        except Exception:
            raise AcraUnexpectedConnectorError from None

        if response.status_code in {401, 403}:
            raise AcraAuthenticationError
        if response.status_code in {408, 504}:
            raise AcraTimeoutError
        if response.status_code == 429 or response.status_code >= 500:
            raise AcraServiceUnavailableError
        if response.status_code != 200:
            raise AcraMalformedResponseError
        if (
            response.size_limit_exceeded
            or response.body is None
            or response.content_type != "application/json"
            or response.response_bytes != len(response.body)
        ):
            raise AcraMalformedResponseError
        try:
            raw = json.loads(response.body)
            token = _ObservedTokenResponse.model_validate(raw)
        except (UnicodeDecodeError, ValueError, ValidationError):
            raise AcraMalformedResponseError from None
        if token.access_token != token.access_token.strip() or any(
            ord(character) < 32 or ord(character) == 127
            for character in token.access_token
        ):
            raise AcraMalformedResponseError
        return token


class AcraApiMarketplaceMockRequestAuthorizer:
    """Inject the raw access token into the provider-defined downstream header."""

    def __init__(self, token_client: AcraApiMarketplaceMockTokenClient) -> None:
        self._token_client = token_client

    def authorization_headers(self) -> Mapping[str, str]:
        return {
            ACRA_API_MARKETPLACE_TOKEN_HEADER_NAME: self._token_client.access_token(),
        }
