"""Proof that hostile root-style environment values cannot activate shared Mongo."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from phase13_test_settings import ORDINARY_TEST_DATABASE, ordinary_test_settings

from app.config import Settings
from app.main import create_app


def test_child_probe_ordinary_composition_is_in_memory() -> None:
    settings = Settings()
    assert settings.clm_persistence_mode == "memory"
    assert settings.mongo_database == ORDINARY_TEST_DATABASE
    assert settings.acra_connector_mode == "mock"
    application = create_app(ordinary_test_settings())
    assert application is not None


def test_hostile_environment_cannot_activate_shared_database() -> None:
    test_file = Path(__file__).resolve()
    hostile_environment = os.environ.copy()
    hostile_environment.update(
        {
            "CLM_PERSISTENCE_MODE": "mongo",
            "MONGO_DATABASE": "clm_poc",
            "MONGO_URI": "mongodb://127.0.0.1:1",
            # The child runs at repository root, so constrain imports to this exact
            # backend source tree instead of inheriting any ambient module location.
            "PYTHONPATH": str(test_file.parents[1]),
        }
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(test_file),
            "-k",
            "child_probe",
            "--tb=no",
            "-q",
        ],
        cwd=test_file.parents[3],
        env=hostile_environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0
