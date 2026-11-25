"""Application integration for HR-only, read-only ACRA diagnostics."""

from __future__ import annotations

import secrets
from typing import Any

from phase13_test_clients import RawTestClient
from phase13_test_credentials import build_test_authentication_service
from pydantic import SecretStr

import app.composition as composition
import app.main as main_module
from app.config import Settings
from app.connectors.errors import AcraTimeoutError
from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.domain.access import SYNTHETIC_USER_PROFILES, TeamId
from app.main import create_app
from app.services.acra_diagnostics import AcraDiagnosticService
from app.services.authentication import generate_scrypt_password_hash
from app.services.onboarding import OnboardingService
from app.services.repository import InMemoryOnboardingCaseRepository
from app.services.target_execution_repository import InMemoryTargetExecutionRepository

GARDEN_UEN = "11111999A"


class CountingMockAcra(MockAcraConnector):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, str]] = []
        self.fail_company = False

    def fetch_company(self, uen: str):  # type: ignore[no-untyped-def]
        self.calls.append(("company", uen))
        if self.fail_company:
            raise AcraTimeoutError("private provider endpoint and response")
        return super().fetch_company(uen)

    def fetch_officers(self, uen: str):  # type: ignore[no-untyped-def]
        self.calls.append(("officers", uen))
        return super().fetch_officers(uen)

    def fetch_ownership_parties(self, uen: str):  # type: ignore[no-untyped-def]
        self.calls.append(("shareholders", uen))
        return super().fetch_ownership_parties(uen)

    def fetch_relationships(self, uen: str):  # type: ignore[no-untyped-def]
        self.calls.append(("relationships", uen))
        raise AssertionError("unsupported diagnostic must not reach the connector")


def _authentication() -> tuple[Any, str]:
    generated_credential = secrets.token_urlsafe(24)
    encoded = generate_scrypt_password_hash(generated_credential)
    hashes = {profile.user_id: encoded for profile in SYNTHETIC_USER_PROFILES}
    return build_test_authentication_service(hashes), generated_credential


def _login(client: RawTestClient, user_id: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"user_id": user_id, "password": password},
    )
    assert response.status_code == 200
    return response.json()["csrf_token"]


def _integrated_app() -> tuple[
    Any,
    str,
    CountingMockAcra,
    OnboardingService,
    InMemoryTargetExecutionRepository,
    Any,
]:
    settings = Settings(_env_file=None, app_env="test", idp_connector_mode="mock")
    case_repository = InMemoryOnboardingCaseRepository()
    ledger = InMemoryTargetExecutionRepository()
    onboarding = OnboardingService(
        acra=MockAcraConnector(),
        goldtier=MockGoldTierConnector(),
        repository=case_repository,
        target_execution_repository=ledger,
    )
    retained_case = onboarding.create_staged_case("202400001A", team_id=TeamId.TEAM_A)
    diagnostic_connector = CountingMockAcra()
    diagnostics = composition.build_acra_diagnostic_service(
        diagnostic_connector,
        settings,
    )
    authentication, generated_credential = _authentication()
    application = create_app(
        settings,
        onboarding_service=onboarding,
        acra_diagnostic_service=diagnostics,
        authentication_service=authentication,
    )
    return (
        application,
        generated_credential,
        diagnostic_connector,
        onboarding,
        ledger,
        retained_case,
    )


def test_acra_routes_enforce_auth_hr_capability_and_preserve_case_state() -> None:
    application, password, connector, onboarding, ledger, retained_case = _integrated_app()
    before_case = onboarding.get_case(retained_case.case_id)
    assert before_case is not None
    assert ledger._entries == {}  # noqa: SLF001 - zero-ledger-mutation assertion

    anonymous = RawTestClient(application, base_url="http://127.0.0.1:8000")
    assert anonymous.get("/api/admin/acra/status").status_code == 401
    assert (
        anonymous.post(
            "/api/admin/acra/lookup",
            json={"uen": GARDEN_UEN, "operation": "ENTITY_PROFILE"},
        ).status_code
        == 401
    )

    non_hr = RawTestClient(application, base_url="http://127.0.0.1:8000")
    non_hr_csrf = _login(non_hr, "maya-lim", password)
    forbidden = non_hr.get("/api/admin/acra/status")
    forbidden_lookup = non_hr.post(
        "/api/admin/acra/lookup",
        json={"uen": GARDEN_UEN, "operation": "ENTITY_PROFILE"},
        headers={"X-CSRF-Token": non_hr_csrf},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "PROVIDER_SANDBOX_TEST_FORBIDDEN"
    assert forbidden_lookup.status_code == 403

    hr = RawTestClient(application, base_url="http://127.0.0.1:8000")
    csrf = _login(hr, "biz-ops", password)
    status_response = hr.get("/api/admin/acra/status")
    lookup = hr.post(
        "/api/admin/acra/lookup",
        json={"uen": GARDEN_UEN.lower(), "operation": "ENTITY_PROFILE"},
        headers={"X-CSRF-Token": csrf},
    )
    inaccessible_case = hr.get(f"/api/onboarding/cases/{retained_case.case_id}")

    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["configuration"] == {
        "provider": "ACRA_MOCK",
        "mode": "mock",
        "classification": "MOCK",
        "configured": True,
        "safe_host": None,
        "client_id_present": False,
        "secret_key_present": False,
        "generic_auth_present": False,
        "timeout_seconds": 10.0,
        "max_response_bytes": 262144,
    }
    assert status_body["samples"][0]["classification"] == (
        "DOCUMENTED_SAMPLE_CANDIDATE"
    )
    assert lookup.status_code == 200
    assert lookup.json()["outcome"] == "COMPLETE"
    assert connector.calls == [("company", GARDEN_UEN)]
    assert inaccessible_case.status_code == 404
    assert onboarding.get_case(retained_case.case_id) == before_case
    assert ledger._entries == {}  # noqa: SLF001 - zero-ledger-mutation assertion


def test_acra_lookup_validation_unsupported_and_safe_failure_stop_calls() -> None:
    application, password, connector, onboarding, ledger, retained_case = _integrated_app()
    before_case = onboarding.get_case(retained_case.case_id)
    hr = RawTestClient(application, base_url="http://127.0.0.1:8000")
    csrf = _login(hr, "biz-ops", password)

    invalid = hr.post(
        "/api/admin/acra/lookup",
        json={"uen": "https://unsafe.invalid/?secret=value", "operation": "ENTITY_PROFILE"},
        headers={"X-CSRF-Token": csrf},
    )
    host_override = hr.post(
        "/api/admin/acra/lookup",
        json={
            "uen": GARDEN_UEN,
            "operation": "ENTITY_PROFILE",
            "host": "attacker.invalid",
        },
        headers={"X-CSRF-Token": csrf},
    )
    unsupported = hr.post(
        "/api/admin/acra/lookup",
        json={"uen": GARDEN_UEN, "operation": "RELATIONSHIPS"},
        headers={"X-CSRF-Token": csrf},
    )
    connector.fail_company = True
    failed = hr.post(
        "/api/admin/acra/lookup",
        json={"uen": GARDEN_UEN, "operation": "ENTITY_PROFILE"},
        headers={"X-CSRF-Token": csrf},
    )

    assert invalid.status_code == 422
    assert "secret=value" not in invalid.text
    assert host_override.status_code == 422
    assert unsupported.status_code == 200
    assert unsupported.json()["outcome"] == "UNSUPPORTED"
    assert unsupported.json()["receipt"]["provider_called"] is False
    assert failed.status_code == 200
    assert failed.json()["outcome"] == "FAILED"
    assert failed.json()["code"] == "ACRA_TIMEOUT"
    assert "private" not in failed.text
    assert connector.calls == [("company", GARDEN_UEN)]
    assert onboarding.get_case(retained_case.case_id) == before_case
    assert ledger._entries == {}  # noqa: SLF001 - zero-ledger-mutation assertion


def test_diagnostic_configuration_uses_fixed_hosts_and_credential_presence_only() -> None:
    marketplace = composition.build_acra_diagnostic_service(
        CountingMockAcra(),
        Settings(
            _env_file=None,
            app_env="test",
            acra_connector_mode="api_marketplace_mock",
            acra_api_marketplace_mock_client_id=SecretStr("private-client"),
            acra_api_marketplace_mock_secret_key=SecretStr("private-secret"),
        ),
    ).status()
    sandbox = composition.build_acra_diagnostic_service(
        CountingMockAcra(),
        Settings(
            _env_file=None,
            app_env="test",
            acra_connector_mode="sandbox",
            acra_base_url="https://registry.example.test/provider/path",
            acra_company_path_template="/company/{uen}",
            acra_auth_header_name="X-Test-Key",
            acra_auth_header_value=SecretStr("private-generic-secret"),
        ),
    ).status()

    assert marketplace.configuration.safe_host == "api-sandbox.bizfile.gov.sg"
    assert marketplace.configuration.client_id_present is True
    assert marketplace.configuration.secret_key_present is True
    assert marketplace.configuration.classification == "MOCK"
    assert sandbox.configuration.safe_host == "registry.example.test"
    assert sandbox.configuration.generic_auth_present is True
    assert sandbox.configuration.classification == "PARTIAL"
    serialized = marketplace.model_dump_json() + sandbox.model_dump_json()
    assert "private-client" not in serialized
    assert "private-secret" not in serialized
    assert "private-generic-secret" not in serialized


def test_default_composition_reuses_one_acra_connector_for_cases_and_diagnostics(
    monkeypatch: Any,
) -> None:
    connector = CountingMockAcra()
    captures: dict[str, object] = {}
    original_onboarding_builder = main_module.build_onboarding_service
    original_diagnostic_builder = main_module.build_acra_diagnostic_service

    def connector_builder(settings: Settings) -> CountingMockAcra:
        captures["connector_builds"] = int(captures.get("connector_builds", 0)) + 1
        return connector

    def onboarding_builder(*args: Any, **kwargs: Any) -> OnboardingService:
        captures["onboarding_connector"] = kwargs.get("acra_connector")
        return original_onboarding_builder(*args, **kwargs)

    def diagnostic_builder(
        active_connector: Any,
        settings: Settings,
    ) -> AcraDiagnosticService:
        captures["diagnostic_connector"] = active_connector
        return original_diagnostic_builder(active_connector, settings)

    monkeypatch.setattr(main_module, "build_acra_connector", connector_builder)
    monkeypatch.setattr(main_module, "build_onboarding_service", onboarding_builder)
    monkeypatch.setattr(main_module, "build_acra_diagnostic_service", diagnostic_builder)

    main_module.create_app(Settings(_env_file=None, app_env="test", idp_connector_mode="mock"))

    assert captures == {
        "connector_builds": 1,
        "onboarding_connector": connector,
        "diagnostic_connector": connector,
    }
