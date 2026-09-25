from __future__ import annotations

import base64
import inspect
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from pydantic import SecretStr

import app.connectors.acra_api_marketplace_auth as marketplace_auth
from app.config import Settings
from app.connectors.errors import AcraConfigurationError

CLIENT_ID = "test_client_id"
SECRET_VALUE = "test_secret_key"
SECRET_KEY = SecretStr(SECRET_VALUE)


def build_basic_auth(
    client_id: str | None = CLIENT_ID,
    secret_key: SecretStr | None = SECRET_KEY,
) -> httpx.BasicAuth:
    return marketplace_auth.build_acra_api_marketplace_mock_basic_auth(
        client_id=client_id,
        secret_key=secret_key,
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
        ("", SecretStr(SECRET_VALUE)),
        ("   ", SecretStr(SECRET_VALUE)),
        (CLIENT_ID, None),
        (CLIENT_ID, SecretStr("")),
        (CLIENT_ID, SecretStr("   ")),
    ],
)
def test_basic_auth_rejects_missing_or_blank_credentials_without_disclosure(
    client_id: str | None,
    secret_key: SecretStr | None,
) -> None:
    with pytest.raises(AcraConfigurationError) as caught:
        build_basic_auth(client_id, secret_key)

    diagnostic = f"{caught.value!s} {caught.value!r}"
    assert CLIENT_ID not in diagnostic
    assert SECRET_VALUE not in diagnostic


def test_basic_auth_uses_basic_scheme_without_exposing_secret_in_repr() -> None:
    auth = build_basic_auth()
    request = httpx.Request("GET", "https://example.invalid/auth-boundary-only")
    authorized_request = next(auth.auth_flow(request))
    scheme, encoded_credentials = authorized_request.headers["Authorization"].split(
        " ", maxsplit=1
    )

    assert scheme == "Basic"
    assert base64.b64decode(encoded_credentials, validate=True).decode() == (
        f"{CLIENT_ID}:{SECRET_VALUE}"
    )
    assert "Bearer" not in authorized_request.headers["Authorization"]
    assert SECRET_VALUE not in repr(auth)
    assert SECRET_VALUE not in str(auth)


def test_auth_foundation_contains_no_production_host_or_bearer_implementation() -> None:
    source = inspect.getsource(marketplace_auth)

    assert "api.bizfile.gov.sg" not in source
    assert "Bearer" not in source


def test_optional_settings_are_backend_only_and_redact_the_secret() -> None:
    settings = Settings(
        _env_file=None,
        acra_api_marketplace_mock_client_id=CLIENT_ID,
        acra_api_marketplace_mock_secret_key=SecretStr(SECRET_VALUE),
    )

    assert settings.acra_api_marketplace_mock_client_id == CLIENT_ID
    assert settings.acra_api_marketplace_mock_secret_key is not None
    assert settings.acra_api_marketplace_mock_secret_key.get_secret_value() == SECRET_VALUE
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

    assert settings.acra_api_marketplace_mock_client_id == CLIENT_ID
    assert settings.acra_api_marketplace_mock_secret_key is not None
    assert settings.acra_api_marketplace_mock_secret_key.get_secret_value() == SECRET_VALUE
    assert settings.acra_connector_mode == "mock"
