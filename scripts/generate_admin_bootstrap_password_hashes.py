"""Generate environment-only hashes for every bootstrap demonstration profile."""

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

    profiles = [
        *(
            (profile.user_id, profile.display_name)
            for profile in SYNTHETIC_USER_PROFILES
        ),
        ("hr-admin", "POC HR Administrator"),
    ]
    for user_id, display_name in profiles:
        credential = getpass.getpass(
            f"Password for bootstrap operator {display_name} ({user_id}): "
        )
        confirmation = getpass.getpass("Confirm credential: ")
        if not credential or credential != confirmation:
            print(f"Password confirmation failed for {user_id}.", file=sys.stderr)
            return 1
        encoded = generate_scrypt_password_hash(credential)
        print(f"{credential_setting_key(user_id)}={encoded}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
