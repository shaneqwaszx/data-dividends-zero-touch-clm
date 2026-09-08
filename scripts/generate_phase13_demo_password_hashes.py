"""Generate environment-only hashes for the five synthetic person profiles."""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "apps" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))


def main() -> int:
    from app.domain.access import SYNTHETIC_USER_PROFILES
    from app.services.authentication import (
        credential_setting_key,
        generate_scrypt_password_hash,
    )

    for profile in SYNTHETIC_USER_PROFILES:
        credential = getpass.getpass(
            f"Password for synthetic operator {profile.display_name} ({profile.user_id}): "
        )
        confirmation = getpass.getpass("Confirm credential: ")
        if not credential or credential != confirmation:
            print(
                f"Password confirmation failed for {profile.user_id}.", file=sys.stderr
            )
            return 1
        encoded = generate_scrypt_password_hash(credential)
        print(f"{credential_setting_key(profile.user_id)}={encoded}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
