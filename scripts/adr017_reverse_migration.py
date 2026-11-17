"""ADR-017 P2-0 reverse migration: dry-run by default, ``--apply`` only in an approved window.

Usage (the URI is read from ``CLM_MIGRATION_MONGO_URI`` and is never printed):

    python scripts/adr017_reverse_migration.py --database <name> [--apply]

It prints only counts, document identifiers and refusal reasons. It refuses ``clm_poc``.
Stop every backend process first: a concurrent write stops the apply part-way.
Running it against any deployed database requires a separate owner approval and a
read-only inventory first (ADR-017 "Security and persistence implications").
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "backend"))

from app.persistence.adr017_migrations import (
    ReverseMigrationRefusedError,
    apply_reverse_migration,
    plan_reverse_migration,
)
from app.persistence.mongo_case_store import MongoCaseStore
from pymongo import MongoClient

FORBIDDEN_DATABASES = frozenset({"clm_poc"})
URI_ENVIRONMENT_KEY = "CLM_MIGRATION_MONGO_URI"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--database", required=True)
    parser.add_argument("--cases-collection", default="clm_case_snapshots")
    parser.add_argument("--definitions-collection", default="clm_workflow_definitions")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if args.database in FORBIDDEN_DATABASES:
        print(json.dumps({"status": "REFUSED", "reason": "FORBIDDEN_DATABASE"}))
        return 2
    uri = os.environ.get(URI_ENVIRONMENT_KEY)
    if not uri:
        print(json.dumps({"status": "REFUSED", "reason": "URI_NOT_CONFIGURED"}))
        return 2
    client: MongoClient = MongoClient(uri, serverSelectionTimeoutMS=5_000)
    try:
        database = client[args.database]
        cases = database[args.cases_collection]
        definitions = database[args.definitions_collection]
        codec = object.__new__(MongoCaseStore)
        plan = plan_reverse_migration(
            cases,
            definitions,
            decode_legacy_case=codec._decode,
        )
        report: dict[str, object] = {"mode": "APPLY" if args.apply else "DRY_RUN"}
        report.update(plan.summary())
        if not args.apply:
            report["status"] = "REFUSED" if plan.refused else "READY"
            print(json.dumps(report, sort_keys=True))
            return 1 if plan.refused else 0
        try:
            report["reverted"] = apply_reverse_migration(plan, cases, definitions)
            report["status"] = "APPLIED"
        except ReverseMigrationRefusedError as exc:
            report["status"] = "REFUSED"
            report["reason"] = str(exc)
            print(json.dumps(report, sort_keys=True))
            return 1
        print(json.dumps(report, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - never print driver detail or the URI
        print(json.dumps({"status": "FAILED", "error_type": type(exc).__name__}))
        return 3
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
