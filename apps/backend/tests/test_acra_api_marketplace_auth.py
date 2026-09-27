from __future__ import annotations

import base64
import inspect
import json
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from pydantic import SecretStr

import app.connectors.acra_api_marketplace_auth as marketplace_auth
from app.config import Settings
from app.connectors.acra_api_marketplace_auth import (
    AcraApiMarketplaceMockTokenClient,
    AcraMarketplaceTokenHttpResponse,
)
from app.connectors.errors import (
    AcraAuthenticationError,
    AcraConfigurationError,
    AcraMalformedResponseError,
    AcraServiceUnavailableError,
    AcraTimeoutError,
)

CLIENT_ID = "test_client_id"
SECRET_VALUE = "test_secret_key"
OPAQUE_TOKEN_VALUE = "opaque-test-token"
SECRET_KEY = SecretStr(SECRET_VALUE)


def token_response(
    *,
    opaque_value: object = OPAQUE_TOKEN_VALUE,
    expires_in: object = 120,
    scope: object = "read",
    token_type: object = "opaque",
) -> AcraMarketplaceTokenHttpResponse:
    body = json.dumps(
        {
            "access_token": opaque_value,
            "expires_in": expires_in,
            "scope": scope,
            "token_type": token_type,
        }
    ).encode()
    return AcraMarketplaceTokenHttpResponse(
        status_code=200,
        content_type="application/json",
        body=body,
        response_bytes=len(body),
    )


@dataclass(frozen=True)
class TokenCall:
    url: str
    auth: httpx.BasicAuth
    headers: Mapping[str, str]
    body: bytes
    timeout_seconds: float


class RecordingTokenTransport:
    def __init__(
        self,
        responses: list[AcraMarketplaceTokenHttpResponse] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.responses = responses or [token_response()]
        self.error = error
        self.calls: list[TokenCall] = []
        self._lock = Lock()

    def post(
        self,
        url: str,
        *,
        auth: httpx.BasicAuth,
        headers: Mapping[str, str],
        body: bytes,
        timeout_seconds: float,
    ) -> AcraMarketplaceTokenHttpResponse:
        with self._lock:
            self.calls.append(
                TokenCall(url, auth, dict(headers), body, timeout_seconds)
            )
            index = len(self.calls) - 1
        if self.error is not None:
            raise self.error
        return self.responses[min(index, len(self.responses) - 1)]


def build_client(
    transport: RecordingTokenTransport,
    *,
    clock: list[float] | None = None,
) -> AcraApiMarketplaceMockTokenClient:
    values = clock or [0.0]
    return AcraApiMarketplaceMockTokenClient(
        client_id=SecretStr(CLIENT_ID),
        secret_key=SECRET_KEY,
        timeout_seconds=10,
        transport=transport,
        monotonic_clock=lambda: values[0],
    )


def test_official_mock_auth_constants_are_exact_and_mock_scoped() -> None:
    endpoint = urlsplit(marketplace_auth.ACRA_API_MARKETPLACE_MOCK_TOKEN_ENDPOINT)

    assert endpoint.scheme == "https"
    assert endpoint.hostname == "api-sandbox.bizfile.gov.sg"
    assert endpoint.path == "/authorizeServer/oauth/token"
    assert parse_qs(endpoint.query) == {"grant_type": ["client_credentials"]}
    assert marketplace_auth.ACRA_API_MARKETPLACE_TOKEN_HEADER_NAME == "token"
    assert marketplace_auth.ACRA_API_MARKETPLACE_TOKEN_LIFETIME_SECONDS == 3_600


@pytest.mark.parametrize(
    ("client_id", "secret_key"),
    [
        (None, SecretStr(SECRET_VALUE)),
        (SecretStr(""), SecretStr(SECRET_VALUE)),
        (SecretStr("   "), SecretStr(SECRET_VALUE)),
        (SecretStr(CLIENT_ID), None),
        (SecretStr(CLIENT_ID), SecretStr("")),
        (SecretStr(CLIENT_ID), SecretStr("   ")),
    ],
)
def test_basic_auth_rejects_missing_or_blank_credentials_without_disclosure(
    client_id: SecretStr | None,
    secret_key: SecretStr | None,
) -> None:
    with pytest.raises(AcraConfigurationError) as caught:
        marketplace_auth.build_acra_api_marketplace_mock_basic_auth(
            client_id=client_id,
            secret_key=secret_key,
        )

    diagnostic = f"{caught.value!s} {caught.value!r}"
    assert CLIENT_ID not in diagnostic
    assert SECRET_VALUE not in diagnostic


def test_token_request_uses_exact_basic_auth_json_contract() -> None:
    transport = RecordingTokenTransport()
    client = build_client(transport)

    assert client.access_token() == OPAQUE_TOKEN_VALUE
    assert len(transport.calls) == 1
    call = transport.calls[0]
    request = httpx.Request("POST", call.url)
    authorized = next(call.auth.auth_flow(request))
    scheme, encoded = authorized.headers["Authorization"].split(" ", maxsplit=1)

    assert scheme == "Basic"
    assert base64.b64decode(encoded, validate=True).decode() == (
        f"{CLIENT_ID}:{SECRET_VALUE}"
    )
    assert urlsplit(call.url).hostname == "api-sandbox.bizfile.gov.sg"
    assert urlsplit(call.url).path == "/authorizeServer/oauth/token"
    assert parse_qs(urlsplit(call.url).query) == {"grant_type": ["client_credentials"]}
    assert call.headers == {"Content-Type": "application/json"}
    assert call.body == b""
    assert call.timeout_seconds == 10


@pytest.mark.parametrize(
    "response",
    [
        AcraMarketplaceTokenHttpResponse(200, "application/json", b"{", 1),
        AcraMarketplaceTokenHttpResponse(
            200,
            "application/json",
            b'{"expires_in": 120, "scope": "read", "token_type": "opaque"}',
            61,
        ),
        token_response(expires_in=0),
        token_response(expires_in=-1),
        token_response(expires_in="120"),
        token_response(expires_in=True),
        token_response(opaque_value=" "),
        token_response(token_type=None),
    ],
)
def test_malformed_token_responses_fail_closed(
    response: AcraMarketplaceTokenHttpResponse,
) -> None:
    client = build_client(RecordingTokenTransport([response]))

    with pytest.raises(AcraMalformedResponseError):
        client.access_token()


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (401, AcraAuthenticationError),
        (403, AcraAuthenticationError),
        (429, AcraServiceUnavailableError),
        (500, AcraServiceUnavailableError),
        (503, AcraServiceUnavailableError),
    ],
)
def test_non_success_token_statuses_are_sanitized(
    status: int,
    error_type: type[Exception],
) -> None:
    response = AcraMarketplaceTokenHttpResponse(
        status_code=status,
        content_type="application/json",
        body=b"",
        response_bytes=0,
    )
    with pytest.raises(error_type) as caught:
        build_client(RecordingTokenTransport([response])).access_token()

    assert SECRET_VALUE not in f"{caught.value!s} {caught.value!r}"
    assert OPAQUE_TOKEN_VALUE not in f"{caught.value!s} {caught.value!r}"


@pytest.mark.parametrize(
    ("error", "error_type"),
    [
        (httpx.ReadTimeout("safe"), AcraTimeoutError),
        (httpx.ConnectError("safe"), AcraServiceUnavailableError),
    ],
)
def test_token_transport_failures_are_sanitized(
    error: Exception,
    error_type: type[Exception],
) -> None:
    with pytest.raises(error_type) as caught:
        build_client(RecordingTokenTransport(error=error)).access_token()

    diagnostic = f"{caught.value!s} {caught.value!r}"
    assert SECRET_VALUE not in diagnostic
    assert OPAQUE_TOKEN_VALUE not in diagnostic


def test_token_response_content_type_and_size_are_bounded() -> None:
    oversized = AcraMarketplaceTokenHttpResponse(
        status_code=200,
        content_type="application/json",
        body=None,
        response_bytes=16_385,
        size_limit_exceeded=True,
    )
    wrong_type = AcraMarketplaceTokenHttpResponse(
        status_code=200,
        content_type="text/html",
        body=b"safe",
        response_bytes=4,
    )

    for response in (oversized, wrong_type):
        with pytest.raises(AcraMalformedResponseError):
            build_client(RecordingTokenTransport([response])).access_token()


def test_token_cache_reuses_then_renews_before_expiry() -> None:
    clock = [0.0]
    transport = RecordingTokenTransport(
        [
            token_response(opaque_value="token-one"),
            token_response(opaque_value="token-two"),
        ]
    )
    client = build_client(transport, clock=clock)

    assert client.access_token() == "token-one"
    clock[0] = 59.999
    assert client.access_token() == "token-one"
    assert len(transport.calls) == 1
    clock[0] = 60.0
    assert client.access_token() == "token-two"
    assert len(transport.calls) == 2


def test_concurrent_access_performs_one_token_request() -> None:
    transport = RecordingTokenTransport()
    client = build_client(transport)

    with ThreadPoolExecutor(max_workers=8) as executor:
        tokens = list(executor.map(lambda _: client.access_token(), range(16)))

    assert tokens == [OPAQUE_TOKEN_VALUE] * 16
    assert len(transport.calls) == 1


def test_auth_objects_and_failures_do_not_expose_secrets() -> None:
    transport = RecordingTokenTransport()
    client = build_client(transport)
    client.access_token()
    response = token_response()

    assert SECRET_VALUE not in repr(client)
    assert SECRET_VALUE not in str(client)
    assert OPAQUE_TOKEN_VALUE not in repr(client)
    assert OPAQUE_TOKEN_VALUE not in str(client)
    assert OPAQUE_TOKEN_VALUE not in repr(response)
    assert SECRET_VALUE not in repr(transport.calls[0].auth)


def test_auth_transport_has_no_production_host_bearer_or_tls_bypass() -> None:
    source = inspect.getsource(marketplace_auth)

    assert "api.bizfile.gov.sg" not in source
    assert "Bearer" not in source
    assert "follow_redirects=False" in source
    assert "ssl.create_default_context()" in source
    assert "verify=False" not in source


def test_optional_settings_are_backend_only_and_redact_the_secret() -> None:
    settings = Settings(
        _env_file=None,
        acra_api_marketplace_mock_client_id=CLIENT_ID,
        acra_api_marketplace_mock_secret_key=SecretStr(SECRET_VALUE),
    )

    assert settings.acra_api_marketplace_mock_client_id is not None
    assert settings.acra_api_marketplace_mock_client_id.get_secret_value() == CLIENT_ID
    assert settings.acra_api_marketplace_mock_secret_key is not None
    assert settings.acra_api_marketplace_mock_secret_key.get_secret_value() == SECRET_VALUE
    assert CLIENT_ID not in repr(settings)
    assert CLIENT_ID not in str(settings)
    assert SECRET_VALUE not in repr(settings)
    assert SECRET_VALUE not in str(settings)
    assert "acra_api_marketplace_mock_access_token" not in Settings.model_fields
    assert "acra_api_marketplace_mock_token" not in Settings.model_fields


def test_optional_credentials_load_from_their_dedicated_environment_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ACRA_API_MARKETPLACE_MOCK_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("ACRA_API_MARKETPLACE_MOCK_SECRET_KEY", SECRET_VALUE)

    settings = Settings(_env_file=None)

    assert settings.acra_api_marketplace_mock_client_id is not None
    assert settings.acra_api_marketplace_mock_client_id.get_secret_value() == CLIENT_ID
    assert settings.acra_api_marketplace_mock_secret_key is not None
    assert settings.acra_api_marketplace_mock_secret_key.get_secret_value() == SECRET_VALUE
    assert settings.acra_connector_mode == "mock"
