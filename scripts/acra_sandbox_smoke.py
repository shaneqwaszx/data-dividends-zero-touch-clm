"""Manual opt-in ACRA sandbox smoke check with payload- and credential-safe output."""

import os
import re

from app.composition import build_acra_connector
from app.config import get_settings
from app.connectors.errors import ConnectorError, public_connector_error

_UEN_PATTERN = re.compile(r"^[0-9]{9}[A-Z]$")


def main() -> int:
    """Execute only when explicitly enabled; never print inputs or source payloads."""

    if os.getenv("ACRA_LIVE_SMOKE_ENABLED", "").strip().lower() != "true":
        print("NOT EXECUTED: ACRA sandbox smoke verification is not enabled.")
        return 0

    try:
        settings = get_settings()
        uen = os.getenv("ACRA_SMOKE_UEN", "").strip().upper()
        if settings.acra_connector_mode != "sandbox" or not _UEN_PATTERN.fullmatch(uen):
            print("FAILED: authorized sandbox mode and a valid opt-in test UEN are required.")
            return 1
        company = build_acra_connector(settings).fetch_company(uen)
    except ConnectorError as exc:
        print(f"FAILED: {public_connector_error(exc).message}")
        return 1
    except Exception:  # noqa: BLE001 - manual boundary must suppress internal details
        print("FAILED: the ACRA sandbox smoke check encountered a sanitized failure.")
        return 1

    if company is None:
        print("FAILED: ACRA returned no entity for the opt-in test UEN.")
        return 1
    print("EXECUTED: ACRA returned a response that passed the configured source decoder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
