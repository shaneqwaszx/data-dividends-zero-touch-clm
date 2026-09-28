"""Report sanitized local runtime composition and startup prerequisites."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "apps" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.composition import build_acra_connector
from app.config import ENV_FILE, Settings
from app.mongo import ping_mongodb


@dataclass(frozen=True)
class PreflightResult:
    facts: dict[str, str]
    messages: tuple[str, ...]
    exit_code: int

    def render(self) -> str:
        lines = [f"{label}: {value}" for label, value in self.facts.items()]
        lines.extend(self.messages)
        return "\n".join(lines)


def _secret_present(value: object | None) -> bool:
    if value is None:
        return False
    get_secret_value = getattr(value, "get_secret_value", None)
    if not callable(get_secret_value):
        return False
    secret = get_secret_value()
    return isinstance(secret, str) and bool(secret.strip())


def inspect_runtime(
    settings: Settings,
    *,
    connector_builder: Callable[[Settings], object] = build_acra_connector,
    mongo_ping: Callable[[Settings], None] = ping_mongodb,
) -> PreflightResult:
    """Inspect only safe configuration facts; never return secret or connection values."""

    client_id_present = _secret_present(settings.acra_api_marketplace_mock_client_id)
    secret_present = _secret_present(settings.acra_api_marketplace_mock_secret_key)
    facts = {
        "Repository root": str(REPOSITORY_ROOT),
        ".env path": str(ENV_FILE),
        "APP_ENV": settings.app_env,
        "Persistence": settings.clm_persistence_mode,
        "ACRA configured mode": settings.acra_connector_mode,
        "ACRA client id present": "yes" if client_id_present else "no",
        "ACRA secret present": "yes" if secret_present else "no",
        "ACRA timeout seconds": str(settings.acra_timeout_seconds),
        "ACRA composed connector": "not-composed",
        "GoldTier configured mode": settings.goldtier_connector_mode,
        "Mongo required": "yes" if settings.clm_persistence_mode == "mongo" else "no",
        "Mongo reachable": "not-required",
    }
    messages: list[str] = []

    if settings.acra_connector_mode == "api_marketplace_mock":
        if not client_id_present:
            messages.append(
                "Missing required configuration field: ACRA_API_MARKETPLACE_MOCK_CLIENT_ID."
            )
        if not secret_present:
            messages.append(
                "Missing required configuration field: ACRA_API_MARKETPLACE_MOCK_SECRET_KEY."
            )

    try:
        connector = connector_builder(settings)
    except Exception:  # noqa: BLE001 - diagnostic boundary must suppress private details
        messages.append("ACRA connector could not be composed safely.")
    else:
        facts["ACRA composed connector"] = type(connector).__name__

    if settings.clm_persistence_mode == "mongo":
        if settings.mongo_uri is None:
            facts["Mongo reachable"] = "no"
            messages.append("Mongo persistence is configured but MONGO_URI is missing.")
        else:
            try:
                mongo_ping(settings)
            except Exception:  # noqa: BLE001 - never expose URI/driver/server details
                facts["Mongo reachable"] = "no"
                messages.append("Mongo persistence is configured but Mongo is unreachable.")
            else:
                facts["Mongo reachable"] = "yes"

    return PreflightResult(
        facts=facts,
        messages=tuple(messages),
        exit_code=1 if messages else 0,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report sanitized local runtime composition and startup prerequisites."
    )
    parser.add_argument(
        "--persistence-mode",
        choices=("memory", "mongo"),
        help="Override only the persistence mode for teammate-profile diagnosis.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    overrides = (
        {"clm_persistence_mode": args.persistence_mode}
        if args.persistence_mode is not None
        else {}
    )
    try:
        settings = Settings(**overrides)
    except ValidationError as error:
        invalid_fields = sorted({str(item["loc"][0]) for item in error.errors() if item["loc"]})
        print("INVALID CONFIG")
        if "acra_connector_mode" in invalid_fields:
            print(
                "Unsupported ACRA connector mode. Current supported modes include "
                "api_marketplace_mock for the official Marketplace Mock."
            )
        if invalid_fields:
            print(f"Invalid configuration field(s): {', '.join(invalid_fields)}")
        return 1

    result = inspect_runtime(settings)
    print(result.render())
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
