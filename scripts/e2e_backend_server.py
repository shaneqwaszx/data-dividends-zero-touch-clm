"""Start the real backend in an explicit, credential-contained E2E process."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "apps" / "backend"

_SYSTEM_ENV_KEYS = (
    "APPDATA",
    "COMSPEC",
    "HOME",
    "HOMEDRIVE",
    "HOMEPATH",
    "LANG",
    "LC_ALL",
    "LOCALAPPDATA",
    "PATH",
    "PATHEXT",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "WINDIR",
)


def _required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise RuntimeError("CLM_E2E_BACKEND_PORT must be an integer") from exc
    if not 1024 <= port <= 65535:
        raise RuntimeError("CLM_E2E_BACKEND_PORT must be between 1024 and 65535")
    return port


def _loopback_origin(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or parsed.port is None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise RuntimeError("CLM_E2E_FRONTEND_ORIGIN must be an HTTP loopback origin")
    return f"http://{parsed.hostname}:{parsed.port}"


def main() -> int:
    ephemeral_credential = _required("CLM_E2E_PASSWORD")
    port = _port(_required("CLM_E2E_BACKEND_PORT"))
    frontend_origin = _loopback_origin(_required("CLM_E2E_FRONTEND_ORIGIN"))
    diagnostics_enabled = os.environ.get("CLM_E2E_DIAGNOSTICS") == "1"
    garden_protocol_fixture = os.environ.get("CLM_E2E_GARDEN_PROTOCOL") == "1"
    registry_demo = os.environ.get("CLM_E2E_REGISTRY_DEMO")
    recovery_demo = os.environ.get("CLM_E2E_RECOVERY_DEMO")
    sandbox_demo = os.environ.get("CLM_E2E_SANDBOX_DEMO")
    synthetic_seed_port = _port(os.environ.get("CLM_E2E_SYNTHETIC_MONGO_PORT", "27185"))
    classification_database = (
        _required("CLM_E2E_CLASSIFICATION_DATABASE")
        if registry_demo == "synthetic-seed" or sandbox_demo in {"database-alpha", "database-partnership", "database-government"}
        or (sandbox_demo is not None and sandbox_demo.startswith("sponsor-"))
        else None
    )
    sys.path.insert(0, str(ROOT))
    from scripts.run_e2e import RECOVERY_DEMO_MODES, SANDBOX_DEMO_MODES

    if recovery_demo not in {None, *RECOVERY_DEMO_MODES}:
        raise RuntimeError("Unknown isolated recovery fixture")
    if sandbox_demo not in {None, *SANDBOX_DEMO_MODES}:
        raise RuntimeError("Unknown isolated Sandbox fixture")
    if sandbox_demo and (recovery_demo or registry_demo or garden_protocol_fixture):
        raise RuntimeError("Sandbox fixtures require separate compositions")
    if recovery_demo and (registry_demo or garden_protocol_fixture):
        raise RuntimeError("Recovery fixtures require separate compositions")
    if registry_demo not in {None, "garden-partnership", "synthetic-cache", "synthetic-seed", "synthetic-target-ambiguity", "synthetic-target-reuse"}:
        raise RuntimeError("Unknown isolated registry fixture")
    if registry_demo and garden_protocol_fixture:
        raise RuntimeError("Registry fixtures require separate compositions")

    system_environment = {
        key: os.environ[key] for key in _SYSTEM_ENV_KEYS if key in os.environ
    }
    os.environ.clear()
    os.environ.update(system_environment)
    os.environ.update(
        {
            "APP_ENV": "test",
            "ACRA_CONNECTOR_MODE": "mock",
            "GOLDTIER_CONNECTOR_MODE": "mock",
            "IDP_CONNECTOR_MODE": "local_pdf_text",
            "OWNERSHIP_CONNECTOR_MODE": "mock",
            "CLM_PERSISTENCE_MODE": "memory",
            "DEMO_CONTROLS_ENABLED": "false",
            "PHASE13_COOKIE_SECURE": "false",
            "PHASE13_BROWSER_ORIGIN": frontend_origin,
            "PYTHONIOENCODING": "utf-8",
            **(
                {
                    "CLM_E2E_DIAGNOSTICS": "1",
                    "CLM_E2E_BACKEND_PORT": str(port),
                }
                if diagnostics_enabled
                else {}
            ),
        }
    )
    sys.path.insert(0, str(BACKEND_ROOT))
    sys.path.insert(0, str(ROOT))

    from app.config import Settings
    from app.domain.access import SYNTHETIC_USER_PROFILES
    from app.services.authentication import (
        credential_setting_key,
        generate_scrypt_password_hash,
    )
    from pydantic import SecretStr

    # Importing app.main creates its conventional module-level app. Disable its
    # configured dotenv source first, then also pass an explicit Settings instance
    # to the task-owned application used by Uvicorn.
    Settings.model_config = {**Settings.model_config, "env_file": None}
    encoded = generate_scrypt_password_hash(ephemeral_credential)
    user_ids = [profile.user_id for profile in SYNTHETIC_USER_PROFILES] + ["hr-admin"]
    for user_id in user_ids:
        os.environ[credential_setting_key(user_id)] = encoded

    from app import main as application_module

    setting_values: dict[str, object] = {
        "app_env": "test",
        "acra_connector_mode": "mock",
        "goldtier_connector_mode": "mock",
        "idp_connector_mode": "local_pdf_text",
        "ownership_connector_mode": "mock",
        "clm_persistence_mode": "memory",
        "demo_controls_enabled": False,
        "phase13_cookie_secure": False,
        "phase13_browser_origin": frontend_origin,
    }
    for user_id in user_ids:
        setting_values[credential_setting_key(user_id).lower()] = encoded
    settings = Settings(_env_file=None, **setting_values)
    fixture_connector = None
    protocol_fixture = garden_protocol_fixture or registry_demo == 'garden-partnership'
    if registry_demo:
        settings = settings.model_copy(update={
            'registry_cache_mode': 'mock', 'registry_cache_freshness_seconds': 7776000,
        })
    if protocol_fixture:
        import secrets

        from app.composition import build_acra_connector

        from scripts.garden_protocol_fixture import OfflineGardenProtocolTransport

        settings = settings.model_copy(update={
            "acra_connector_mode": "api_marketplace_mock",
            "acra_api_marketplace_mock_client_id": SecretStr(secrets.token_urlsafe(32)),
            "acra_api_marketplace_mock_secret_key": SecretStr(secrets.token_urlsafe(32)),
        })
        if registry_demo == "garden-partnership":
            from scripts.slice_b_registry_fixture import (
                GardenPartnershipProtocolTransport,
            )

            transport: OfflineGardenProtocolTransport = GardenPartnershipProtocolTransport()
        else:
            transport = OfflineGardenProtocolTransport()
        fixture_connector = build_acra_connector(
            settings, transport=transport, marketplace_token_transport=transport,
        )
    if registry_demo == "synthetic-cache":
        from scripts.slice_b_registry_fixture import CountingSyntheticRegistry

        fixture_connector = CountingSyntheticRegistry()
    recovery_fixture = None
    if recovery_demo:
        from scripts.slice_c_recovery_fixture import build_offline_recovery_fixture

        recovery_fixture = build_offline_recovery_fixture(settings, recovery_demo)
        settings = recovery_fixture.settings
    ambiguity_fixture = None
    if registry_demo == "synthetic-target-ambiguity":
        from scripts.slice_f_target_fixture import build_local_ambiguity_fixture
        ambiguity_fixture = build_local_ambiguity_fixture(settings)
        fixture_connector = ambiguity_fixture.registry
    reuse_fixture = None
    if registry_demo == "synthetic-target-reuse":
        from scripts.slice_f_target_fixture import build_local_reuse_fixture
        reuse_fixture = build_local_reuse_fixture(settings)
        fixture_connector = reuse_fixture.registry
    database_fixture = None
    sponsor_fixture = None
    sandbox_transport = None
    if sandbox_demo:
        from scripts.run_s3_sandbox_acceptance import SyntheticAcceptanceAcra
        from scripts.s3_sandbox_fixture import (
            S3_SYNTHETIC_NAME,
            S3_SYNTHETIC_UEN,
            OfflineS3SandboxTransport,
        )
        settings = Settings(_env_file=None, **{
            **setting_values, "goldtier_connector_mode": "sandbox",
            "goldtier_sandbox_base_url": "https://sandbox.goldtier.invalid",
            "goldtier_sandbox_environment": "synthetic",
            "goldtier_sandbox_user_id": SecretStr("synthetic-offline-user"),
            "goldtier_sandbox_allow_writes": True,
        })
        fixture_connector = SyntheticAcceptanceAcra(S3_SYNTHETIC_NAME, S3_SYNTHETIC_UEN)
        sandbox_transport = OfflineS3SandboxTransport(
            "success" if sandbox_demo.startswith("sponsor-") else sandbox_demo,
        )
        if sandbox_demo == "garden-existing-customer":
            from app.composition import build_acra_connector

            from scripts.slice_b_registry_fixture import (
                GardenPartnershipProtocolTransport,
            )

            settings = settings.model_copy(update={
                "acra_connector_mode": "api_marketplace_mock",
                "acra_api_marketplace_mock_client_id": SecretStr("synthetic-offline-client"),
                "acra_api_marketplace_mock_secret_key": SecretStr("synthetic-offline-key"),
            })
            garden_transport = GardenPartnershipProtocolTransport()
            fixture_connector = build_acra_connector(
                settings, transport=garden_transport,
                marketplace_token_transport=garden_transport,
            )
            protocol_fixture = True
    if sandbox_demo in {"database-alpha", "database-partnership", "database-government"}:
        from scripts.zero_touch_classification_browser_fixture import (
            DatabaseClassificationFixture,
        )
        assert classification_database is not None
        database_fixture = DatabaseClassificationFixture(
            settings, sandbox_demo, classification_database, synthetic_seed_port,
        )
        settings = database_fixture.settings
        fixture_connector = database_fixture.registry
        sandbox_transport = database_fixture.target
        application_module.build_persistence_bundle = lambda _settings: database_fixture.bundle
    if sandbox_demo and sandbox_demo.startswith("sponsor-"):
        from scripts.sponsor_demo_browser_fixture import SponsorDemoBrowserFixture
        assert classification_database is not None
        sponsor_fixture = SponsorDemoBrowserFixture(
            settings, sandbox_demo, classification_database, synthetic_seed_port,
        )
        settings = sponsor_fixture.settings
        fixture_connector = sponsor_fixture.registry
        sandbox_transport = sponsor_fixture.target
        # The legacy banner flag is intentionally memory-only. This separate
        # physical fixture reports its offline classification through its metadata.
        protocol_fixture = False
    if registry_demo == "synthetic-seed":
        import secrets
        from datetime import UTC, datetime

        from app import composition
        from app.connectors import acra_api_marketplace_auth
        from app.persistence.composition import build_persistence_bundle

        from scripts.mongo_test_safety import require_ephemeral_mongo_database
        from scripts.seed_zero_touch_happy_path_companies import manage_fixtures
        from scripts.synthetic_company_pack_test_transport import NoMarketplaceRequests

        assert classification_database is not None
        require_ephemeral_mongo_database(classification_database)
        settings = Settings(_env_file=None, **{
            **setting_values, "acra_connector_mode": "api_marketplace_mock",
            "clm_persistence_mode": "mongo", "registry_cache_mode": "auto",
            "mongo_database": classification_database,
            "mongo_uri": SecretStr("mongodb" + f"://127.0.0.1:{synthetic_seed_port}"),
            "acra_api_marketplace_mock_client_id": SecretStr(secrets.token_urlsafe(32)),
            "acra_api_marketplace_mock_secret_key": SecretStr(secrets.token_urlsafe(32)),
        })
        # Explicit isolated test fixture preparation, never production startup seeding.
        seed_bundle = build_persistence_bundle(settings)
        try:
            manage_fixtures(seed_bundle.registry_snapshots, now=datetime.now(UTC), seed=True)
        finally:
            seed_bundle.close()
        seed_transport = NoMarketplaceRequests()
        composition.HttpxAcraTransport = lambda **_: seed_transport
        acra_api_marketplace_auth.HttpxAcraMarketplaceTokenTransport = lambda: seed_transport
        # create_app builds its actual configured connector and normal Mongo composition.

    application = application_module.create_app(
        settings=settings,
        onboarding_service=(recovery_fixture.onboarding if recovery_fixture else
                            ambiguity_fixture.onboarding if ambiguity_fixture else
                            reuse_fixture.onboarding if reuse_fixture else None),
        ownership_analysis_service=reuse_fixture.ownership if reuse_fixture else None,
        acra_connector=fixture_connector,
        goldtier_transport=sandbox_transport,
        e2e_acra_protocol_fixture=protocol_fixture,
        e2e_portfolio_seed_count=(
            0 if protocol_fixture or registry_demo or recovery_demo or sandbox_demo else 105
        ),
    )

    if sandbox_transport:
        @application.get("/api/__s3/sandbox-counts", include_in_schema=False)
        def sandbox_counts() -> dict[str, object]:
            assert sandbox_transport is not None
            return {"fixture": sandbox_demo, "calls": dict(sandbox_transport.counts),
                    "external_calls": 0,
                    **(database_fixture.metadata() if database_fixture else {}),
                    **(sponsor_fixture.metadata() if sponsor_fixture else {})}

    if ambiguity_fixture:
        @application.get("/api/__slice_f/target-metadata", include_in_schema=False)
        def target_metadata() -> dict[str, object]:
            assert ambiguity_fixture is not None
            return ambiguity_fixture.metadata()

    if recovery_fixture:
        @application.get("/api/__slice_c/recovery-metadata", include_in_schema=False)
        def recovery_metadata() -> dict[str, object]:
            assert recovery_fixture is not None
            return recovery_fixture.metadata()

    if registry_demo:
        # This endpoint exists only in this isolated test server, never app.main.
        # It returns synthetic safe counters, no payload/authentication/provider details.
        @application.get("/api/__slice_b/registry-counts", include_in_schema=False)
        def registry_counts() -> dict[str, object]:
            if registry_demo == "synthetic-seed":
                return {"fixture": registry_demo, **seed_transport.metadata()}
            if registry_demo == "garden-partnership":
                return {"fixture": registry_demo, "calls": list(transport.calls), "external_calls": 0}
            from scripts.slice_b_registry_fixture import CountingSyntheticRegistry
            assert isinstance(fixture_connector, CountingSyntheticRegistry)
            return {"fixture": registry_demo, "calls": list(fixture_connector.calls), "external_calls": 0}

    import uvicorn

    try:
        uvicorn.run(application, host="127.0.0.1", port=port, access_log=False, log_level="warning")
    finally:
        if database_fixture is not None:
            database_fixture.close()
        if sponsor_fixture is not None:
            sponsor_fixture.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
