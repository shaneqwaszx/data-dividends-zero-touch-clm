"""Provision process-random hashes for standalone contract-test imports."""

from __future__ import annotations

import os
import secrets

from app.domain.access import SYNTHETIC_USER_PROFILES
from app.services.authentication import (
    credential_setting_key,
    generate_scrypt_password_hash,
)


def provision_contract_hash_environment() -> None:
    credential = secrets.token_urlsafe(24)
    for profile in SYNTHETIC_USER_PROFILES:
        os.environ.setdefault(
            credential_setting_key(profile.user_id),
            generate_scrypt_password_hash(credential),
        )
