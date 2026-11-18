"""ADR-017 P2-1 governance migration: dry run, and an owner-approved guarded apply mode.

Usage (the URI is read from ``CLM_MIGRATION_MONGO_URI`` and is never printed):

    # 1. Read-only plan; prints the plan summary and its ``plan_hash``.
    python scripts/p2_1_migration.py --database <name> --dry-run [--window-approval <file>]

    # 2. Apply inside the approved window (backend stopped, backup taken and verified):
    python scripts/p2_1_migration.py --database <name> --apply \\
        --window-approval <file> --expect-plan-hash <plan_hash from step 1> \\
        [--resume-lock <lock_id>]

Apply refuses unless every one of these holds, checked in this order:
- ``--apply`` with ``--database``, ``--window-approval`` and ``--expect-plan-hash``;
- the approval file (``clm-p2-1-migration-window/v1``; see ``WindowApproval`` in
  ``app/persistence/p2_1_migration.py``) names this database, and now is inside its window;
- ``clm_poc`` / ``clm_staging`` only when the approval names exactly that database (never a
  default; ``--database`` is always required);
- the backup manifest named by the approval exists, its SHA-256 equals the recorded hash,
  it is for this database and its boundary is inside the window (and the archive matches,
  when ``archive_path`` is given);
- the database in ``CLM_MIGRATION_MONGO_DATABASE`` and/or the URI path is present and equal
  to ``--database``;
- no live dispatch-fence lease or claim (no P2-0 or P2-1 writer running);
- the exclusive migration lock is acquired (insert-only, durable; backend startup refuses
  while it exists), or the lock of an interrupted run of the same window is resumed by id;
- a fresh dry run in the same invocation is refusal-free and its hash equals
  ``--expect-plan-hash``.
After the lock and the lease re-check it reloads the approval and re-verifies the backup
(refusing if either changed), then inserts the cold copies, writes each marker last,
re-runs the P2-1 verification, and releases the lock. It prints only safe identifiers,
counts, hashes and reason codes.

The lock: only a lock freshly acquired by this run is released, and only on success or
on a refusal before any write. A resumed lock (``--resume-lock``) is never released
except on success, because an earlier run may already have written. To resume: run a
fresh dry run with the same approval and pass its ``plan_hash`` with
``--resume-lock <lock_id>`` (each resume issues a new ``lock_id``; use the one printed
last). A resume re-inserts the plan's cold copies under fresh attempt suffixes (fallback
mode): bounded, identical-hash duplicates that cold readers deduplicate.

A stale lock is never broken automatically: ``expires_at`` is informational only. An
operator clears a lock only through an explicit, separately approved action (after
checking the database state against the plan and the backup), outside this tool.

Exit codes: 0 READY (dry run) or APPLIED_VERIFIED; 1 the plan has refusals or the
post-apply verification failed (lock retained); 2 a precondition refused (nothing written;
a lock acquired by this run is released); 3 unexpected failure before any write (lock
released); 4 interrupted after writes may have started (lock retained: re-run in the same
window with ``--resume-lock <lock_id>``; the migration converges).
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "backend"))

from app.persistence.adr017_backfill import verify_p2_1_definitions
from app.persistence.p2_1_migration import (
    MIGRATION_LOCK_COLLECTION,
    ApplyPreconditionError,
    MigrationLockHeldError,
    SeedBaseline,
    WindowApproval,
    acquire_migration_lock,
    apply_p2_1_migration,
    live_dispatch_leases,
    load_window_approval,
    plan_hash,
    plan_p2_1_migration,
    protected_database_allowed,
    release_migration_lock,
    resume_migration_lock,
    verify_backup,
)
from app.persistence.workflow_governance_store import MongoColdHistoryStore
from pymongo import MongoClient

URI_ENVIRONMENT_KEY = "CLM_MIGRATION_MONGO_URI"
DATABASE_ENVIRONMENT_KEY = "CLM_MIGRATION_MONGO_DATABASE"
REFUSED_FLAGS = ("--execute", "--write", "--commit", "--force")
SEEDER_MODULE = "app.services.workflow_ratchet"
SEEDER_NAME = "seed_baseline"
EXIT_OK, EXIT_PLAN, EXIT_REFUSED, EXIT_FAILED, EXIT_INTERRUPTED = 0, 1, 2, 3, 4


def _print(report: Mapping[str, object]) -> None:
    print(json.dumps(dict(report), sort_keys=True, default=str))


def _refuse(reason: str, **extra: object) -> int:
    _print({"status": "REFUSED", "reason": reason, **extra})
    return EXIT_REFUSED


def _default_seeder() -> SeedBaseline | None:
    try:
        module = importlib.import_module(SEEDER_MODULE)
    except ImportError:
        return None
    seeder = getattr(module, SEEDER_NAME, None)
    return seeder if callable(seeder) else None


def _uri_database(uri: str) -> str | None:
    """The URI path database, parsed locally (no DNS, so ``mongodb+srv`` is not resolved).

    Returns "" when the URI names no database and None when it is not a MongoDB URI.
    """

    for scheme in ("mongodb://", "mongodb+srv://"):
        if uri.startswith(scheme):
            rest = uri[len(scheme) :]
            break
    else:
        return None
    if "/" not in rest:
        return ""
    return unquote(rest.split("/", 1)[1].split("?", 1)[0])


def _confirmed_database(uri: str, environ: Mapping[str, str]) -> set[str] | None:
    """The databases named by the URI path and the environment (None: URI unparsable)."""

    from_uri = _uri_database(uri)
    if from_uri is None:
        return None
    named = {
        value for value in (from_uri, environ.get(DATABASE_ENVIRONMENT_KEY)) if value
    }
    return named


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--database", required=True)
    parser.add_argument("--definitions-collection", default="clm_workflow_definitions")
    parser.add_argument("--cases-collection", default="clm_case_snapshots")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--window-approval", type=Path)
    parser.add_argument("--expect-plan-hash")
    parser.add_argument("--resume-lock")
    for flag in REFUSED_FLAGS:
        parser.add_argument(flag, action="store_true", help=argparse.SUPPRESS)
    return parser


def main(
    argv: list[str] | None = None,
    *,
    client_factory: Callable[[str], Any] | None = None,
    seed_baseline: SeedBaseline | None = None,
    now: datetime | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    args, unknown = _parser().parse_known_args(argv)
    env = os.environ if environ is None else environ

    def clock() -> datetime:
        return now if now is not None else datetime.now(UTC)

    if any(getattr(args, flag.lstrip("-")) for flag in REFUSED_FLAGS):
        return _refuse("UNSUPPORTED_APPLY_FLAG")
    if unknown:
        return _refuse("UNKNOWN_ARGUMENT")
    if args.dry_run == args.apply:
        return _refuse("CHOOSE_DRY_RUN_OR_APPLY")
    if args.apply and (args.window_approval is None or not args.expect_plan_hash):
        return _refuse("APPLY_REQUIRES_APPROVAL_AND_PLAN_HASH")
    if args.resume_lock is not None and not args.apply:
        return _refuse("RESUME_LOCK_REQUIRES_APPLY")
    approval: WindowApproval | None = None
    backup: dict[str, object] = {}
    try:
        if args.window_approval is not None:
            approval = load_window_approval(
                args.window_approval, database=args.database, now=clock()
            )
        if not protected_database_allowed(args.database, approval):
            return _refuse("PROTECTED_DATABASE_NOT_APPROVED")
        if args.apply:
            assert approval is not None
            backup = verify_backup(approval, database=args.database, now=clock())
    except ApplyPreconditionError as exc:
        return _refuse(exc.reason)
    seeder = seed_baseline or _default_seeder()
    if seeder is None:
        return _refuse("BASELINE_SEEDER_UNAVAILABLE")
    uri = env.get(URI_ENVIRONMENT_KEY)
    if not uri:
        return _refuse("URI_NOT_CONFIGURED")
    if args.apply:
        named = _confirmed_database(uri, env)
        if named is None:
            return _refuse("URI_INVALID")
        if not named:
            return _refuse("DATABASE_NOT_CONFIRMED")
        if named != {args.database}:
            return _refuse("DATABASE_MISMATCH")
    factory = client_factory or (
        lambda value: MongoClient(value, serverSelectionTimeoutMS=5_000)
    )
    client = factory(uri)
    try:
        if args.dry_run:
            return _dry_run(args, client, seeder, clock)
        assert approval is not None
        return _apply(args, client, seeder, clock, approval, backup)
    except Exception as exc:  # noqa: BLE001 - never print driver detail or the URI
        _print({"status": "FAILED", "error_type": type(exc).__name__})
        return EXIT_FAILED
    finally:
        client.close()


def _plan(
    args: argparse.Namespace, database: Any, seeder: SeedBaseline, now: datetime
) -> Any:
    return plan_p2_1_migration(
        database[args.definitions_collection].find({}),
        seed_baseline=seeder,
        now=now,
        # Reads only: lookups for conflicting cold records; ``initialize`` is not called here.
        cold=MongoColdHistoryStore(database),
    )


def _dry_run(
    args: argparse.Namespace,
    client: Any,
    seeder: SeedBaseline,
    clock: Callable[[], datetime],
) -> int:
    plan = _plan(args, client[args.database], seeder, clock())
    report: dict[str, object] = {"mode": "DRY_RUN", "plan_hash": plan_hash(plan)}
    report.update(plan.summary())
    report["status"] = "REFUSED" if plan.refused else "READY"
    _print(report)
    return EXIT_PLAN if plan.refused else EXIT_OK


def _apply(
    args: argparse.Namespace,
    client: Any,
    seeder: SeedBaseline,
    clock: Callable[[], datetime],
    approval: WindowApproval,
    backup: Mapping[str, object],
) -> int:
    database = client[args.database]
    definitions = database[args.definitions_collection]
    cases = database[args.cases_collection]
    locks = database[MIGRATION_LOCK_COLLECTION]
    report: dict[str, object] = {
        "mode": "APPLY",
        "approval": approval.summary(),
        **backup,
    }
    if live_dispatch_leases(cases, now=clock()):
        return _refuse("WRITERS_NOT_QUIESCED", **report)
    try:
        if args.resume_lock is not None:
            lock_id = resume_migration_lock(
                locks, approval=approval, expected_lock_id=args.resume_lock, now=clock()
            )
        else:
            lock_id = acquire_migration_lock(locks, approval=approval, now=clock())
    except MigrationLockHeldError as exc:
        return _refuse(exc.reason, lock=exc.lock, **report)
    except ApplyPreconditionError as exc:
        return _refuse(exc.reason, **report)
    report["lock_id"] = lock_id
    # Only a lock acquired fresh by this run may be released before success; a resumed lock
    # belongs to a run that may already have written (cold copies or markers).
    fresh = args.resume_lock is None
    written = False
    resume_step = (
        "run a fresh dry run with the same approval and pass its plan_hash with "
        "--resume-lock <lock_id> inside the same approved window"
    )

    def stop(status: str, code: int, *, release: bool, **extra: object) -> int:
        allowed = release and (status == "APPLIED_VERIFIED" or (fresh and not written))
        released = release_migration_lock(locks, lock_id) if allowed else False
        if not released and status != "APPLIED_VERIFIED":
            extra = {**extra, "next_step": resume_step}
        _print({**report, **extra, "status": status, "lock_released": released})
        return code

    try:
        # Re-check after the lock: a writer that started meanwhile is still refused.
        if live_dispatch_leases(cases, now=clock()):
            return stop(
                "REFUSED", EXIT_REFUSED, release=True, reason="WRITERS_NOT_QUIESCED"
            )
        # Immediately before the apply, writers quiesced: the approval and backup again.
        try:
            again = load_window_approval(
                args.window_approval, database=args.database, now=clock()
            )
            if again != approval:
                raise ApplyPreconditionError("WINDOW_APPROVAL_CHANGED")
            if verify_backup(approval, database=args.database, now=clock()) != backup:
                raise ApplyPreconditionError("BACKUP_CHANGED")
        except ApplyPreconditionError as exc:
            return stop("REFUSED", EXIT_REFUSED, release=True, reason=exc.reason)
        plan = _plan(args, database, seeder, clock())
        digest = plan_hash(plan)
        report.update(plan.summary())
        report["plan_hash"] = digest
        if plan.refused:
            return stop("REFUSED", EXIT_PLAN, release=True, reason="PLAN_HAS_REFUSALS")
        if digest != args.expect_plan_hash:
            return stop(
                "REFUSED", EXIT_REFUSED, release=True, reason="PLAN_HASH_MISMATCH"
            )
        written = True
        cold = MongoColdHistoryStore(database)
        cold.initialize()
        report["applied"] = apply_p2_1_migration(plan, definitions, cold, now=clock())
        findings = verify_p2_1_definitions(definitions.find({}), cold=cold)
        if findings:
            return stop(
                "APPLIED_VERIFY_FAILED",
                EXIT_PLAN,
                release=False,
                verification=[
                    {"id": item.workflow_id, "reason": item.reason} for item in findings
                ],
            )
        return stop("APPLIED_VERIFIED", EXIT_OK, release=True)
    except Exception as exc:  # noqa: BLE001 - sanitized; the lock tells the backend to stay down
        if not written:
            return stop(
                "FAILED", EXIT_FAILED, release=True, error_type=type(exc).__name__
            )
        return stop(
            "INTERRUPTED",
            EXIT_INTERRUPTED,
            release=False,
            error_type=type(exc).__name__,
        )


if __name__ == "__main__":
    raise SystemExit(main())
