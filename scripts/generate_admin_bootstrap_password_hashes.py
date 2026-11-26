"""Generate environment-only hashes for every bootstrap demonstration profile."""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "apps" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))


def main(argv: list[str] | None = None) -> int:
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
        ("biz-ops", "POC Biz Ops Administrator"),
        ("support-user", "Support User"),
    ]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user",
        action="append",
        choices=[user_id for user_id, _ in profiles],
        help="generate only this bootstrap profile's hash (repeatable)",
    )
    selected = parser.parse_args([] if argv is None else argv).user
    if selected:
        profiles = [item for item in profiles if item[0] in selected]
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
    raise SystemExit(main(sys.argv[1:]))
