"""Owned disposable physical Mongo and offline target for guarded browser acceptance."""

import shutil
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings
from app.persistence.composition import build_persistence_bundle
from pydantic import SecretStr
from pymongo import MongoClient

from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    require_ephemeral_mongo_database,
)
from scripts.s3_sandbox_fixture import OfflineS3SandboxTransport
from scripts.seed_zero_touch_happy_path_companies import manage_fixtures
from scripts.zero_touch_happy_path_fixtures import COMPANIES, GOVERNMENT


class NoRegistryCalls:
    def __init__(self):
        self.calls = []

    def _refuse(self, *args):
        self.calls.append("FORBIDDEN_ACRA")
        raise AssertionError("Fresh physical seed path forbids registry provider calls")

    fetch_company = fetch_officers = fetch_ownership_parties = fetch_relationships = (
        _refuse
    )


class DatabaseClassificationFixture:
    """Test-server only; neither a runtime provider nor a seed endpoint."""

    def __init__(self, settings: Settings, mode: str, database: str, port: int = 27185):
        if (
            mode
            not in {"database-alpha", "database-partnership", "database-government"}
            or settings.app_env != "test"
        ):
            raise ValueError("Unknown isolated classification fixture")
        if not 1024 <= port <= 65535:
            raise ValueError("Classification Mongo port is outside the allowed range")
        self.database = require_ephemeral_mongo_database(database)
        self.cleanup_client = MongoClient(
            host="127.0.0.1", port=port, serverSelectionTimeoutMS=3000
        )
        # Only the task-owned loopback Mongo container on the reserved port is used.
        tesseract = shutil.which("tesseract")
        local_windows_ocr = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
        if tesseract is None and local_windows_ocr.is_file():
            tesseract = str(local_windows_ocr)
        if tesseract is None:
            self.cleanup_client.close()
            raise RuntimeError(
                "Classification browser acceptance requires actual local Tesseract"
            )
        self.settings = settings.model_copy(
            update={
                "clm_persistence_mode": "mongo",
                "mongo_uri": SecretStr("mongodb" + f"://127.0.0.1:{port}"),
                "mongo_database": self.database,
                "acra_connector_mode": "api_marketplace_mock",
                "local_ocr_executable": tesseract,
            }
        )
        # D-101: every mode, Government included, is served by the local synthetic seed.
        self.registry = NoRegistryCalls()
        self.target = OfflineS3SandboxTransport(mode)
        self.company = (
            GOVERNMENT
            if mode == "database-government"
            else COMPANIES[0 if mode == "database-alpha" else 2]
        )
        self.target.name, self.target.uen = self.company.name, self.company.uen
        try:
            self.bundle = build_persistence_bundle(self.settings)
            manage_fixtures(
                self.bundle.registry_snapshots, now=datetime.now(UTC), seed=True
            )
        except Exception:  # noqa: BLE001 - test setup failure is sanitized and cleaned
            cleanup_ephemeral_mongo_database(self.cleanup_client, self.database)
            self.cleanup_client.close()
            raise RuntimeError(
                "Isolated classification fixture could not start safely"
            ) from None

    def metadata(self):
        return {
            "registry_calls": list(self.registry.calls),
            "mutation_attempt_count": sum(
                self.target.counts[op] for op in ("SHELL", "POLICY", "AMEND")
            ),
            "persistence": "MONGO",
            "synthetic_only": True,
        }

    def close(self):
        self.bundle.close()
        try:
            cleanup_ephemeral_mongo_database(self.cleanup_client, self.database)
            assert self.database not in self.cleanup_client.list_database_names()
        finally:
            self.cleanup_client.close()
