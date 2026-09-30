import json
from collections.abc import Mapping
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app.config import Settings
from app.connectors.acra_api_marketplace_mock import AcraApiMarketplaceMockConnector
from app.connectors.acra_sandbox import (
    AcraHttpResponse,
    AcraSandboxConnector,
)
from app.connectors.errors import AcraConfigurationError
from app.connectors.mock_acra import MockAcraConnector
from app.demo.scenarios import VALID_SME_UEN
from app.domain.models import SourceEnvironment, WorkflowState
from app.main import build_acra_connector, build_onboarding_service, create_app

FIXTURE = Path(__file__).parent / "fixtures" / "acra" / "synthetic_company_success.json"


class SafeFakeAuthorizer:
    def authorization_headers(self) -> Mapping[str, str]:
        return {"X-Synthetic-Authorization": "fixture-only-value"}


class ContractFixtureTransport:
    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> AcraHttpResponse:
        del url, headers, timeout_seconds
        document = json.loads(FIXTURE.read_text(encoding="utf-8"))
        return AcraHttpResponse(status_code=200, body=document["response"])


def sandbox_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        demo_controls_enabled=True,
        acra_connector_mode="sandbox",
        acra_base_url="https://sandbox.synthetic-acra.example",
        acra_company_path_template="/business-profile/{uen}",
        acra_timeout_seconds=8,
    )


def test_mock_mode_is_the_safe_default_composition() -> None:
    connector = build_acra_connector(
        Settings(
            _env_file=None,
            app_env="test",
            acra_api_marketplace_mock_client_id="test_client_id",
            acra_api_marketplace_mock_secret_key=SecretStr("test_secret_key"),
        )
    )

    assert isinstance(connector, MockAcraConnector)


def test_api_marketplace_mock_selects_only_official_mock_connector() -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        acra_connector_mode="api_marketplace_mock",
        acra_api_marketplace_mock_client_id="test_client_id",
        acra_api_marketplace_mock_secret_key=SecretStr("test_secret_key"),
        acra_auth_header_name="Authorization",
        acra_auth_header_value=SecretStr("test_generic_value"),
    )

    connector = build_acra_connector(
        settings,
        transport=ContractFixtureTransport(),
    )

    assert isinstance(connector, AcraApiMarketplaceMockConnector)
    assert not isinstance(connector, AcraSandboxConnector)
    assert "test_generic_value" not in repr(connector)


def test_marketplace_credentials_do_not_substitute_for_generic_sandbox_auth() -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        acra_connector_mode="sandbox",
        acra_base_url="https://sandbox.synthetic-acra.example",
        acra_company_path_template="/business-profile/{uen}",
        acra_api_marketplace_mock_client_id="test_client_id",
        acra_api_marketplace_mock_secret_key=SecretStr("test_secret_key"),
    )

    with pytest.raises(AcraConfigurationError):
        build_acra_connector(settings, transport=ContractFixtureTransport())


def test_marketplace_mode_requires_dedicated_credentials() -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        acra_connector_mode="api_marketplace_mock",
        acra_auth_header_name="token",
        acra_auth_header_value=SecretStr("generic-value"),
    )

    with pytest.raises(AcraConfigurationError):
        build_acra_connector(settings, transport=ContractFixtureTransport())


def test_retired_bizfile_mock_mode_is_invalid() -> None:
    with pytest.raises(ValidationError, match="Unsupported ACRA connector mode"):
        Settings.model_validate({"app_env": "test", "acra_connector_mode": "bizfile_mock"})


def test_sandbox_mode_composes_with_safe_injected_boundaries() -> None:
    connector = build_acra_connector(
        sandbox_settings(),
        transport=ContractFixtureTransport(),
        authorizer=SafeFakeAuthorizer(),
    )

    assert isinstance(connector, AcraSandboxConnector)
    payload = connector.fetch_company(VALID_SME_UEN)
    assert payload is not None
    assert payload.source_environment == "SANDBOX"


@pytest.mark.parametrize(
    "settings",
    [
        Settings(_env_file=None, app_env="test", acra_connector_mode="sandbox"),
        Settings(
            _env_file=None,
            app_env="test",
            acra_connector_mode="sandbox",
            acra_base_url="http://insecure.synthetic-acra.example",
            acra_company_path_template="/business-profile/{uen}",
        ),
        Settings(
            _env_file=None,
            app_env="test",
            acra_connector_mode="sandbox",
            acra_base_url="https://sandbox.synthetic-acra.example",
            acra_company_path_template="/missing-placeholder",
        ),
        Settings(
            _env_file=None,
            app_env="test",
            acra_connector_mode="sandbox",
            acra_base_url="https://sandbox.synthetic-acra.example",
            acra_company_path_template="/business-profile/{uen}",
        ),
    ],
)
def test_missing_or_invalid_sandbox_configuration_fails_safely(settings: Settings) -> None:
    with pytest.raises(AcraConfigurationError) as caught:
        build_acra_connector(settings)

    assert str(caught.value) == (
        "The ACRA sandbox connector is not configured for authorized use."
    )
    assert "synthetic-acra" not in str(caught.value)


def test_expanded_mock_operations_do_not_fabricate_sandbox_contracts() -> None:
    mock_case = build_onboarding_service(
        settings=Settings(_env_file=None, app_env="test")
    ).create_case(
        VALID_SME_UEN
    )
    sandbox_case = build_onboarding_service(
        settings=sandbox_settings(),
        acra_transport=ContractFixtureTransport(),
        acra_authorizer=SafeFakeAuthorizer(),
    ).create_case(VALID_SME_UEN)

    assert mock_case.state == WorkflowState.VALIDATED
    assert sandbox_case.state == WorkflowState.FAILED
    assert mock_case.entity is not None
    assert sandbox_case.entity is not None
    assert mock_case.entity.source.environment == SourceEnvironment.MOCK
    assert sandbox_case.entity.source.environment == SourceEnvironment.SANDBOX
    assert sandbox_case.registry_acquisition is not None
    assert sandbox_case.registry_acquisition.status == "FAILED"
    assert [item.status for item in sandbox_case.registry_acquisition.operation_results] == [
        "COMPLETE",
        "FAILED",
        "NOT_ATTEMPTED",
        "NOT_ATTEMPTED",
    ]
    assert sandbox_case.error is not None
    assert sandbox_case.error.code == "REGISTRY_OPERATION_UNAVAILABLE"
    assert sandbox_case.goldtier_result is None


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_safe_discovery_reports_sandbox_without_scenarios_or_secrets() -> None:
    service = build_onboarding_service(settings=Settings(_env_file=None, app_env="test"))
    application = create_app(sandbox_settings(), onboarding_service=service)
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/onboarding/mock-scenarios")

    assert response.status_code == 200
    body = response.json()
    assert body["simulation"]["registry_environment"] == "SANDBOX"
    assert body["simulation"]["target_environment"] == "MOCK"
    assert body["scenarios"] == []
    assert "header" not in response.text.lower()
    assert "fixture-only-value" not in response.text
