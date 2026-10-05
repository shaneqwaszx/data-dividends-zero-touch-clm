"""Bounded idempotent manual-UAT seed through the existing snapshot repository."""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "apps/backend")]

from app.domain.models import RegistryFreshnessPolicy  # noqa: E402
from app.persistence.mongo_registry_cache_store import MongoRegistryCacheStore  # noqa: E402
from app.services.registry_cache_repository import RegistrySnapshotRepository  # noqa: E402

from scripts.zero_touch_happy_path_fixtures import COMPANIES  # noqa: E402

_UAT_DATABASE = re.compile(r"^(?:clm_uat_registry|clm_p16)_[0-9a-f]{24}$")


class SeedConflictError(RuntimeError):
    """Safe seed conflict; never overwrite unrelated normalized evidence."""


def require_safe_target(database: str, app_env: str) -> None:
    if app_env not in {"development", "test"}:
        raise ValueError("Seed requires development/test application environment.")
    if not _UAT_DATABASE.fullmatch(database):
        raise ValueError("Seed requires a disposable clm_uat_registry_<24 hex> database.")


def manage_fixtures(
    repository: RegistrySnapshotRepository, *, now: datetime, seed: bool
) -> dict[str, int]:
    counts = {"created": 0, "refreshed": 0, "fresh": 0, "missing": 0, "expired": 0}
    policy = RegistryFreshnessPolicy()
    # Validate all known keys before beginning a batch. Concurrent changes still use CAS.
    pending = []
    for company in COMPANIES:
        candidate = company.snapshot(now)
        current = repository.get(candidate.key)
        if current is not None:
            expected = company.snapshot(current.freshness_anchor).model_copy(
                update={"revision": current.revision},
                deep=True,
            )
            if current != expected or current.written_at > now:
                raise SeedConflictError("Fixture key contains conflicting evidence.")
        pending.append((candidate, current))
    for candidate, current in pending:
        if current is None:
            counts["missing"] += 1
            if seed:
                repository.create(candidate)
                counts["created"] += 1
        elif now < policy.expires_at(current.freshness_anchor):
            counts["fresh"] += 1
        else:
            counts["expired"] += 1
            if seed:
                repository.replace(
                    candidate.model_copy(update={"revision": current.revision}),
                    expected_revision=current.revision,
                )
                counts["refreshed"] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--seed", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--database", required=True)
    args = parser.parse_args()
    client = None
    try:
        require_safe_target(args.database, os.environ.get("APP_ENV", "development"))
        uri = os.environ.get("MONGO_URI")
        if not uri:
            raise ValueError("MONGO_URI must be provisioned in the process environment.")
        from pymongo import MongoClient

        collection = os.environ.get("MONGO_REGISTRY_CACHE_COLLECTION", "clm_registry_snapshots")
        reserved = {
            os.environ.get("MONGO_CASE_COLLECTION", "clm_case_snapshots"),
            os.environ.get("MONGO_ADMIN_TEAMS_COLLECTION", "clm_admin_teams"),
            os.environ.get("MONGO_ADMIN_PROFILES_COLLECTION", "clm_admin_profiles"),
            os.environ.get("MONGO_ADMIN_POLICIES_COLLECTION", "clm_admin_policies"),
        }
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", collection) or collection in reserved:
            raise ValueError("Registry collection must be distinct and bounded.")
        client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        store = MongoRegistryCacheStore(client, database=args.database, collection=collection)
        # Check is read-only; seed establishes the existing owner's exact indexes.
        if args.seed:
            store.initialize()
        counts = manage_fixtures(store, now=datetime.now(UTC), seed=args.seed)
        for company in COMPANIES:
            print(f"{company.name} | {company.uen}")
        print("FIXTURE_COUNT=4; " + "; ".join(f"{k.upper()}={v}" for k, v in counts.items()))
        return 0 if args.seed or counts["fresh"] == 4 else 1
    except Exception:
        print("SEED_CHECK_FAILED: unsafe configuration, conflicting evidence or unavailable store.")
        return 2
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
