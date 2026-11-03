"""The owner's migration of an existing format-1 budget ledger to format 2 (D-118 S7).

Never run by the service: only ``scripts/budget_ledger.py migrate-v2``, on a stopped service,
under the owner's separate approval. It refuses unless the ledger is quiet, then writes a
verified backup, migrates in one exclusive transaction and proves that every v1 row and event
is unchanged. A refusal leaves the ledger as it was. Nothing here is sent anywhere.
"""

import hashlib
import sqlite3
import time
from collections.abc import Callable
from contextlib import closing, suppress
from dataclasses import dataclass
from pathlib import Path

from .budget import (
    PROFILES,
    RESUMABLE_BREAKER_CODES,
    SCHEMA_VERSION,
    V1_COLUMNS,
    BudgetLedger,
    LedgerError,
    _apply_format_2,
    accounting_mode_for,
    check_structure,
)
from .claude_reconciliation import ReconcileRefused, read_marker, reconcile_lock

DEFAULT_QUIET_SECONDS = 300
MIN_QUIET_SECONDS = 60


@dataclass(frozen=True)
class MigrationResult:
    backup: Path
    fingerprint: str
    calls: int
    events: int


def v1_fingerprint(connection: sqlite3.Connection) -> tuple[str, int, int]:
    """SHA-256 over every v1 row (v1 columns only, by id), with the call and event counts."""

    digest = hashlib.sha256()
    counts = {}
    for table, columns in V1_COLUMNS.items():
        rows = connection.execute(
            f"SELECT {', '.join(columns)} FROM {table} ORDER BY id"
        ).fetchall()
        counts[table] = len(rows)
        digest.update(table.encode())
        for row in rows:
            digest.update(repr(tuple(row)).encode("utf-8"))
    return digest.hexdigest(), counts["calls"], counts["operator_events"]


def _connect(path: Path, mode: str) -> sqlite3.Connection:
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode={mode}", uri=True, isolation_level=None)


def _check_totals(connection: sqlite3.Connection) -> None:
    # The same consistency the ledger itself requires: header totals equal the call rows.
    high, local, reserved, baseline, provider = connection.execute(
        "SELECT baseline_high_water_call_id, local_charged_micro_usd, open_reserved_micro_usd,"
        " baseline_micro_usd, last_provider_usage_micro_usd FROM ledger_meta"
    ).fetchone()
    found = connection.execute(
        "SELECT"
        " COALESCE(SUM(CASE WHEN state != 'open' AND id > ? THEN charged_micro_usd END), 0),"
        " COALESCE(SUM(CASE WHEN state = 'open' THEN reserved_micro_usd END), 0)"
        " FROM calls",
        (high,),
    ).fetchone()
    if tuple(found) != (local, reserved) or baseline < provider:
        raise LedgerError("LEDGER_INCONSISTENT", "the ledger totals do not match its calls")


def _check_quiet(connection: sqlite3.Connection, now_ms: int, quiet_seconds: int) -> None:
    open_calls, last_call, last_close = connection.execute(
        "SELECT COALESCE(SUM(state = 'open'), 0), MAX(created_at), MAX(closed_at) FROM calls"
    ).fetchone()
    last_event = connection.execute("SELECT MAX(created_at) FROM operator_events").fetchone()[0]
    if open_calls:
        raise LedgerError("MIGRATION_REFUSED", "a call is open")
    latest = max(value or 0 for value in (last_call, last_close, last_event))
    if latest > now_ms - quiet_seconds * 1000:
        raise LedgerError("MIGRATION_REFUSED", "the ledger was written during the quiet period")
    breaker_open, code = connection.execute(
        "SELECT breaker_open, breaker_code FROM ledger_meta"
    ).fetchone()
    if breaker_open and code not in RESUMABLE_BREAKER_CODES:
        raise LedgerError("MIGRATION_REFUSED", "the breaker is open for the owner")


def migrate_to_format_2(
    path: Path,
    *,
    backup: Path,
    quiet_seconds: int = DEFAULT_QUIET_SECONDS,
    clock: Callable[[], float] = time.time,
) -> MigrationResult:
    # The accounting mode follows the ledger's own provider (QG F2): never chosen here.
    if type(quiet_seconds) is not int or quiet_seconds < MIN_QUIET_SECONDS:
        raise LedgerError("INVALID_INPUT", "the quiet period is at least 60 seconds")
    if not path.is_file():
        raise LedgerError("LEDGER_MISSING", "the budget ledger does not exist")
    if backup.exists():
        raise LedgerError("BACKUP_EXISTS", "the backup path already exists")
    try:
        if read_marker(path) is not None:
            raise LedgerError("MIGRATION_REFUSED", "a reconciliation intent marker exists")
    except ReconcileRefused:
        raise LedgerError("MIGRATION_REFUSED", "a reconciliation intent marker exists") from None
    try:
        with reconcile_lock(path):
            return _migrate(path, backup, quiet_seconds, clock)
    except ReconcileRefused:
        raise LedgerError("LEDGER_BUSY", "the ledger is locked by a reconciliation") from None


def _migrate(
    path: Path,
    backup: Path,
    quiet_seconds: int,
    clock: Callable[[], float],
) -> MigrationResult:
    now = int(clock() * 1000)
    source = _connect(path, "rw")
    with closing(source):
        # The read transaction holds the file still while it is checked and copied.
        source.execute("BEGIN")
        try:
            if source.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise LedgerError("LEDGER_CORRUPT", "the ledger failed its integrity check")
            check_structure(source, 1)
            headers = source.execute(
                "SELECT schema_version, profile_id FROM ledger_meta"
            ).fetchall()
            if len(headers) != 1:
                raise LedgerError("LEDGER_INCONSISTENT", "the ledger has no single header")
            if headers[0][0] != SCHEMA_VERSION or headers[0][1] not in PROFILES:
                raise LedgerError("LEDGER_SCHEMA_UNSUPPORTED", "the ledger header is not v1")
            accounting_mode = accounting_mode_for(headers[0][1])
            _check_totals(source)
            _check_quiet(source, now, quiet_seconds)
            before = v1_fingerprint(source)
            backup.parent.mkdir(parents=True, exist_ok=True)
            copy = _connect(backup, "rwc")
            with closing(copy):
                source.backup(copy)
                if copy.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise LedgerError("BACKUP_INVALID", "the backup failed its integrity check")
                check_structure(copy, 1)
                if v1_fingerprint(copy) != before:
                    raise LedgerError("BACKUP_INVALID", "the backup differs from the ledger")
        finally:
            with suppress(sqlite3.Error):
                source.execute("ROLLBACK")
        # One exclusive transaction: nothing else reads or writes while the format changes.
        try:
            source.execute("BEGIN EXCLUSIVE")
        except sqlite3.OperationalError:
            raise LedgerError("LEDGER_BUSY", "the ledger is in use") from None
        try:
            check_structure(source, 1)
            _check_quiet(source, int(clock() * 1000), quiet_seconds)
            if v1_fingerprint(source) != before:
                raise LedgerError("MIGRATION_REFUSED", "the ledger changed after the backup")
            _apply_format_2(
                source,
                origin="migrated",
                accounting_mode=accounting_mode,
                opening_basis="migrated",
                now=int(clock() * 1000),
            )
            check_structure(source, 2)
            if v1_fingerprint(source) != before:
                raise LedgerError("MIGRATION_REFUSED", "the v1 rows would change")
            source.execute("COMMIT")
        except BaseException:
            with suppress(sqlite3.Error):
                source.execute("ROLLBACK")
            raise
    BudgetLedger(path).verify()
    fingerprint, calls, events = before
    return MigrationResult(backup=backup, fingerprint=fingerprint, calls=calls, events=events)
