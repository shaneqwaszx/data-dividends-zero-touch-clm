"""ADR-017 P2-1 governance migration: DRY RUN ONLY in M1 (any apply flag refuses).

Usage (the URI is read from ``CLM_MIGRATION_MONGO_URI`` and is never printed):

    python scripts/p2_1_migration.py --database <name> --dry-run

It plans, per workflow definition document, the legacy version provenance, the legacy
draft conversion, the baseline seeded from the active version and the cold copies to
insert, and reports refusals. It reads only: it creates no index and writes nothing. It
prints only counts, workflow identifiers and refusal reasons. It refuses ``clm_poc``.
Applying the migration needs a separately reviewed and approved release (ADR-017 2.2).
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "backend"))

from app.persistence.p2_1_migration import SeedBaseline, plan_p2_1_migration
from app.persistence.workflow_governance_store import MongoColdHistoryStore
from pymongo import MongoClient

FORBIDDEN_DATABASES = frozenset({"clm_poc"})
URI_ENVIRONMENT_KEY = "CLM_MIGRATION_MONGO_URI"
APPLY_FLAGS = ("--apply", "--execute", "--write", "--commit", "--force")
APPLY_REFUSAL = (
    "The P2-1 migration is dry-run only in M1. Applying it needs a separately reviewed "
    "and owner-approved release; nothing was read or written."
)
# Built by the service workstream with the signature Callable[[WorkflowVersion], RequiredBaseline].
SEEDER_MODULE = "app.services.workflow_ratchet"
SEEDER_NAME = "seed_baseline"


def _print(report: dict[str, object]) -> None:
    print(json.dumps(report, sort_keys=True))


def _default_seeder() -> SeedBaseline | None:
    try:
        module = importlib.import_module(SEEDER_MODULE)
    except ImportError:
        return None
    seeder = getattr(module, SEEDER_NAME, None)
    return seeder if callable(seeder) else None


def main(
    argv: list[str] | None = None,
    *,
    client_factory: Callable[[str], Any] | None = None,
    seed_baseline: SeedBaseline | None = None,
    now: datetime | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--database", required=True)
    parser.add_argument("--definitions-collection", default="clm_workflow_definitions")
    parser.add_argument("--dry-run", action="store_true")
    for flag in APPLY_FLAGS:
        parser.add_argument(flag, action="store_true", help=argparse.SUPPRESS)
    args, unknown = parser.parse_known_args(argv)
    if any(getattr(args, flag.lstrip("-").replace("-", "_")) for flag in APPLY_FLAGS):
        _print(
            {
                "status": "REFUSED",
                "reason": "APPLY_NOT_AVAILABLE",
                "message": APPLY_REFUSAL,
            }
        )
        return 2
    if unknown:
        _print(
            {
                "status": "REFUSED",
                "reason": "UNKNOWN_ARGUMENT",
                "message": APPLY_REFUSAL,
            }
        )
        return 2
    if not args.dry_run:
        _print(
            {
                "status": "REFUSED",
                "reason": "DRY_RUN_REQUIRED",
                "message": APPLY_REFUSAL,
            }
        )
        return 2
    if args.database.strip().lower() in FORBIDDEN_DATABASES:
        _print({"status": "REFUSED", "reason": "FORBIDDEN_DATABASE"})
        return 2
    seeder = seed_baseline or _default_seeder()
    if seeder is None:
        _print({"status": "REFUSED", "reason": "BASELINE_SEEDER_UNAVAILABLE"})
        return 2
    uri = os.environ.get(URI_ENVIRONMENT_KEY)
    if not uri:
        _print({"status": "REFUSED", "reason": "URI_NOT_CONFIGURED"})
        return 2
    factory = client_factory or (
        lambda value: MongoClient(value, serverSelectionTimeoutMS=5_000)
    )
    client = factory(uri)
    try:
        database = client[args.database]
        plan = plan_p2_1_migration(
            database[args.definitions_collection].find({}),
            seed_baseline=seeder,
            now=now or datetime.now(UTC),
            # Reads only: lookups for conflicting cold records; ``initialize`` is never called.
            cold=MongoColdHistoryStore(database),
        )
        report: dict[str, object] = {"mode": "DRY_RUN"}
        report.update(plan.summary())
        report["status"] = "REFUSED" if plan.refused else "READY"
        _print(report)
        return 1 if plan.refused else 0
    except Exception as exc:  # noqa: BLE001 - never print driver detail or the URI
        _print({"status": "FAILED", "error_type": type(exc).__name__})
        return 3
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
