"""Run guarded Phase 12/13 physical Mongo tests with sanitized output."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "apps" / "backend"
for import_root in (ROOT, BACKEND_ROOT):
    sys.path.insert(0, str(import_root))

from app.config import Settings

from scripts.mongo_test_safety import EPHEMERAL_MONGO_DATABASE_PATTERN


def main() -> int:
    initial = Settings()
    if initial.mongo_uri is None:
        print("PHYSICAL_MONGO_CONFIGURATION=UNAVAILABLE")
        return 1
    uri = initial.mongo_uri.get_secret_value()
    shared_database = initial.mongo_database
    collection = initial.mongo_case_collection
    os.environ["PHASE12_MONGO_URI"] = uri

    result = pytest.main(
        [
            str(BACKEND_ROOT / "tests" / "test_phase12_real_mongo.py"),
            str(BACKEND_ROOT / "tests" / "test_phase13_real_mongo.py"),
            "-p",
            "no:cacheprovider",
            "--tb=no",
        ]
    )

    client: MongoClient[dict[str, object]] | None = None
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5_000)
        remaining = sum(
            1
            for name in client.list_database_names()
            if EPHEMERAL_MONGO_DATABASE_PATTERN.fullmatch(name)
        )
        shared_count = client[shared_database][collection].count_documents({})
    except Exception as exc:  # noqa: BLE001 - redact all remote connection detail
        print(f"PHYSICAL_POSTCHECK_FAILED={type(exc).__name__}")
        return 1
    finally:
        if client is not None:
            client.close()

    print(f"PHYSICAL_TEST_DATABASES_REMAINING={remaining}")
    print(f"SHARED_CLM_POC_COUNT_AFTER={shared_count}")
    if result != pytest.ExitCode.OK or remaining:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
