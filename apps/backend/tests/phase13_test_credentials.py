"""Runtime-only Phase 13 test credentials; no stable plaintext or hash is committed."""

import os
import secrets

from app.domain.access import SYNTHETIC_USER_PROFILES
from app.services.authentication import (
    credential_setting_key,
    generate_scrypt_password_hash,
)

TEST_PASSWORD = secrets.token_urlsafe(24)


def provision_test_hash_environment() -> None:
    encoded = generate_scrypt_password_hash(TEST_PASSWORD)
    for profile in SYNTHETIC_USER_PROFILES:
        os.environ[credential_setting_key(profile.user_id)] = encoded
