"""Authority-bounded authentication facts for ACRA API Marketplace Mock."""

import httpx
from pydantic import SecretStr

from app.connectors.errors import AcraConfigurationError

ACRA_API_MARKETPLACE_MOCK_TOKEN_ENDPOINT = (
    "https://api-sandbox.bizfile.gov.sg/authorizeServer/oauth/token"
    "?grant_type=client_credentials"
)
ACRA_API_MARKETPLACE_TOKEN_HEADER_NAME = "token"
ACRA_API_MARKETPLACE_TOKEN_LIFETIME_SECONDS = 60 * 60


def build_acra_api_marketplace_mock_basic_auth(
    *,
    client_id: str | None,
    secret_key: SecretStr | None,
) -> httpx.BasicAuth:
    """Build HTTP Basic client authentication without constructing or sending a request."""

    if client_id is None or not client_id.strip() or secret_key is None:
        raise AcraConfigurationError
    secret_value = secret_key.get_secret_value()
    if not secret_value.strip():
        raise AcraConfigurationError
    return httpx.BasicAuth(username=client_id, password=secret_value)
