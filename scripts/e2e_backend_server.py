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
        }
    )
    sys.path.insert(0, str(BACKEND_ROOT))

    from app.config import Settings
    from app.domain.access import SYNTHETIC_USER_PROFILES
    from app.services.authentication import (
        credential_setting_key,
        generate_scrypt_password_hash,
    )

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
    application = application_module.create_app(settings=settings)

    import uvicorn

    uvicorn.run(
        application,
        host="127.0.0.1",
        port=port,
        access_log=False,
        log_level="warning",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
