"""Runtime-only Phase 13 test credentials; no stable plaintext or hash is committed."""

import os
import secrets
from collections.abc import Callable, Mapping
from datetime import datetime

from app.domain.access import SYNTHETIC_USER_PROFILES
from app.services.admin_repository import (
    InMemoryProfileRepository,
    InMemoryTeamRepository,
    bootstrap_administration,
)
from app.services.authentication import (
    AuthenticationService,
    credential_setting_key,
    generate_scrypt_password_hash,
)

TEST_PASSWORD = secrets.token_urlsafe(24)


def provision_test_hash_environment() -> None:
    encoded = generate_scrypt_password_hash(TEST_PASSWORD)
    for profile in SYNTHETIC_USER_PROFILES:
        os.environ[credential_setting_key(profile.user_id)] = encoded
    os.environ[credential_setting_key("hr-admin")] = encoded
    os.environ[credential_setting_key("support-user")] = encoded


def build_test_authentication_service(
    hashes: Mapping[str, str],
    *,
    clock: Callable[[], datetime] | None = None,
    max_active_sessions: int = 256,
) -> AuthenticationService:
    """Compose repository-backed auth for unit tests without inherited persistence."""

    teams = InMemoryTeamRepository()
    profiles = InMemoryProfileRepository()
    values = dict(hashes)
    for bootstrap_user_id in ("hr-admin", "support-user"):
        if bootstrap_user_id not in values and values:
            values[bootstrap_user_id] = next(iter(values.values()))
    bootstrap_administration(teams, profiles, values)
    return AuthenticationService(
        profiles,
        teams,
        clock=clock,
        max_active_sessions=max_active_sessions,
    )
