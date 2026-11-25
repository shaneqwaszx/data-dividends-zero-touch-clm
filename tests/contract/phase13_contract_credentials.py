"""Provision process-random hashes for standalone contract-test imports."""

from __future__ import annotations

import os
import secrets

from app.config import Settings
from app.domain.access import SYNTHETIC_USER_PROFILES
from app.services.authentication import (
    credential_setting_key,
    generate_scrypt_password_hash,
)


def provision_contract_hash_environment() -> None:
    # Standalone imports must not load owner dotenv or contact ambient Mongo/providers.
    Settings.model_config = {**Settings.model_config, "env_file": None}
    os.environ.update({
        "APP_ENV": "test", "CLM_PERSISTENCE_MODE": "memory",
        "ACRA_CONNECTOR_MODE": "mock", "GOLDTIER_CONNECTOR_MODE": "mock",
        "GARDEN_SUPPLEMENT_ENABLED": "false", "MONGO_DATABASE": "clm_contract_tests",
        "MONGO_URI": "mongodb" + "://127.0.0.1:1",
    })
    credential = secrets.token_urlsafe(24)
    for profile in SYNTHETIC_USER_PROFILES:
        os.environ.setdefault(
            credential_setting_key(profile.user_id),
            generate_scrypt_password_hash(credential),
        )
    for bootstrap_user_id in ("biz-ops", "support-user"):
        os.environ.setdefault(
            credential_setting_key(bootstrap_user_id),
            generate_scrypt_password_hash(credential),
        )
