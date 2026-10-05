"""Canonical fail-safe settings owner for ordinary backend tests."""

from __future__ import annotations

import os
from typing import Any

from app.config import Settings

ORDINARY_TEST_DATABASE = "clm_ordinary_tests"
ORDINARY_TEST_BROWSER_ORIGIN = "http://testserver"
LOOPBACK_NON_SERVICE_URI = "mongodb://127.0.0.1:1"


def enforce_ordinary_test_environment() -> None:
    """Prevent root environment values from selecting shared persistence during tests."""

    Settings.model_config = {**Settings.model_config, "env_file": None}
    os.environ["APP_ENV"] = "test"
    os.environ["CLM_PERSISTENCE_MODE"] = "memory"
    os.environ["MONGO_URI"] = LOOPBACK_NON_SERVICE_URI
    os.environ["MONGO_DATABASE"] = ORDINARY_TEST_DATABASE
    os.environ["ACRA_CONNECTOR_MODE"] = "mock"
    os.environ["GOLDTIER_CONNECTOR_MODE"] = "mock"
    os.environ["PHASE13_BROWSER_ORIGIN"] = ORDINARY_TEST_BROWSER_ORIGIN


def ordinary_test_settings(**overrides: Any) -> Settings:
    """Build deterministic in-memory settings without loading the repository `.env`."""

    forbidden = {"clm_persistence_mode", "mongo_uri", "mongo_database", "_env_file"}
    attempted = forbidden.intersection(overrides)
    if attempted:
        raise ValueError("ordinary test persistence settings cannot be overridden")
    values: dict[str, Any] = {
        "app_env": "test",
        "clm_persistence_mode": "memory",
        "mongo_uri": None,
        "mongo_database": ORDINARY_TEST_DATABASE,
        "acra_connector_mode": "mock",
        "goldtier_connector_mode": "mock",
        "phase13_browser_origin": ORDINARY_TEST_BROWSER_ORIGIN,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)
