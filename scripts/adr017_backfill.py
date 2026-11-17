"""ADR-017 P2-0 one-time backfill: dry-run by default, ``--apply`` only in an approved window.

Usage (the URI is read from ``CLM_MIGRATION_MONGO_URI`` and is never printed):

    python scripts/adr017_backfill.py --database <name> [--apply]

It sets ``latest_version`` and ``active_version`` to the highest version present (0 if none)
on every workflow definition document that has neither, then re-runs the startup checks.
Valid only for this single P2-0 run (ADR-017 3.5): never after P2-1. It prints only counts,
workflow identifiers and refusal reasons. It refuses ``clm_poc``.
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

from app.persistence.adr017_backfill import (
    BackfillRefusedError,
    apply_backfill,
    plan_backfill,
    verify_definitions,
)
from pymongo import MongoClient

FORBIDDEN_DATABASES = frozenset({"clm_poc"})
URI_ENVIRONMENT_KEY = "CLM_MIGRATION_MONGO_URI"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--database", required=True)
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
        definitions = client[args.database][args.definitions_collection]
        plan = plan_backfill(definitions)
        report: dict[str, object] = {"mode": "APPLY" if args.apply else "DRY_RUN"}
        report.update(plan.summary())
        if not args.apply:
            report["status"] = "REFUSED" if plan.refusals else "READY"
            print(json.dumps(report, sort_keys=True))
            return 1 if plan.refusals else 0
        try:
            report["applied"] = apply_backfill(plan, definitions)
        except BackfillRefusedError as exc:
            report["status"] = "REFUSED"
            report["reason"] = str(exc)
            print(json.dumps(report, sort_keys=True))
            return 1
        findings = verify_definitions(definitions.find({}))
        report["verification"] = [
            {"id": item.workflow_id, "reason": item.reason} for item in findings
        ]
        report["status"] = "APPLIED_VERIFIED" if not findings else "APPLIED_VERIFY_FAILED"
        print(json.dumps(report, sort_keys=True))
        return 0 if not findings else 1
    except Exception as exc:  # noqa: BLE001 - never print driver detail or the URI
        print(json.dumps({"status": "FAILED", "error_type": type(exc).__name__}))
        return 3
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
