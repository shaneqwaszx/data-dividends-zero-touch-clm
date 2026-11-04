# D-110 (B1 Phase B): HR reconciliation of the Claude ledger with the Anthropic Console.
#
# The ledger's own ``BudgetLedger.reconcile`` stays the only accounting rule (budget.py is
# unchanged). This module adds what an HR workflow needs around it:
#
# * a read-only snapshot of the ledger (one read transaction on a ``mode=ro`` connection,
#   bracketed by ``data_version``) and its state token;
# * the preview checks G1 to G10 and the freshness rules (D-110 F3, F8);
# * ``CheckedLedger``: the same ``reconcile`` call, with a compare-and-set before it and a check
#   of exactly what it wrote after it, inside the ledger's own write transaction (F4);
# * the cross-process reconcile lock and the intent marker beside the ledger (F5);
# * the run store in the model state database, with its state machine (F6), and resolve (F7).
#
# Nothing here sends a request, reads a key or reads case data. Every string constant in this
# file feeds the synthetic boundary vocabulary, so explanations are comments.

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import sys
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager, suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .anthropic_profiles import LEDGER_PROFILE_ID
from .budget import META_COLUMNS, RECONCILE_TOLERANCE_MICRO_USD, BudgetLedger, LedgerError
from .model_admin_store import ModelAdminStore

# --- the approved numbers (D-110 R6, R7, F4, F7) ------------------------------------------

TOLERANCE_MICRO_USD = RECONCILE_TOLERANCE_MICRO_USD
# Main path: the Console's own refresh time plus this margin. Fallback (Q4, only when the
# Console shows no refresh time): HR's viewing time plus the longer margin.
REFRESHED_MARGIN_SECONDS = 600
VIEWED_MARGIN_SECONDS = 3600
# A reading may be at most this old when applied, and at most this far in the future.
MAX_VIEWED_AGE_SECONDS = 7200
FUTURE_SKEW_SECONDS = 60
# reconcile() refuses a settle lag above this.
MAX_LAG_SECONDS = 86_400
# From the intent row to the ledger commit; resolve waits this plus the busy timeout plus a
# grace period before it may decide anything.
APPLY_SECONDS = 30
BUSY_SECONDS = 2.0
RESOLVE_GRACE_SECONDS = 10
PREVIEW_SECONDS = 300
SNAPSHOT_ATTEMPTS = 3

KIND_REFRESHED = "console_refreshed"
KIND_VIEWED = "viewed"
KINDS = (KIND_REFRESHED, KIND_VIEWED)

# Run states (F6). LEDGER_BUSY is a reply, never a state.
REQUESTED = "requested"
APPLIED = "applied"
REFUSED = "refused"
FAILED = "failed"
UNRESOLVED = "unresolved"
OWNER_CLOSED = "owner_closed"
OPEN_STATES = (REQUESTED, UNRESOLVED)
FINAL_STATES = (APPLIED, REFUSED, FAILED, OWNER_CLOSED)

ACTION = "CLAUDE_RECONCILIATION"


class ReconcileRefused(Exception):
    # A closed refusal code, with content-free facts for the page (numbers and times).

    def __init__(self, code: str, **facts: Any) -> None:
        super().__init__(code)
        self.code = code
        self.facts = facts


def canonical(path: Path | str) -> str:
    # One spelling per file, so the service and the operator's script lock the same file.
    return os.path.normcase(str(Path(path).resolve()))


def lock_file(path: Path | str) -> Path:
    resolved = Path(path).resolve()
    return resolved.with_name(resolved.name + ".reconcile.lock")


def marker_file(path: Path | str) -> Path:
    resolved = Path(path).resolve()
    return resolved.with_name(resolved.name + ".reconcile.intent")


def iso(ms: int | float | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, UTC).isoformat(timespec="seconds")


def parse_moment(text: object) -> int:
    # An ISO 8601 time with its offset, as epoch milliseconds.
    if not isinstance(text, str) or len(text) > 40:
        raise ReconcileRefused("INVALID_INPUT")
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        raise ReconcileRefused("INVALID_INPUT") from None
    if moment.tzinfo is None:
        raise ReconcileRefused("INVALID_INPUT")
    return int(moment.timestamp() * 1000)


# --- the ledger state and its token --------------------------------------------------------


def _state(connection: sqlite3.Connection) -> dict[str, Any]:
    # Everything any ledger writer changes (QG round 3, check A): the whole meta row, the
    # calls' high-water id, open count, last close, unverified and uncovered quarantined
    # counts, and the operator event sequence.
    row = connection.execute(f"SELECT {', '.join(META_COLUMNS)} FROM ledger_meta").fetchone()
    if row is None:
        raise sqlite3.DatabaseError("no meta row")
    meta = dict(zip(META_COLUMNS, row, strict=True))
    max_call, open_calls, last_close = connection.execute(
        "SELECT COALESCE(MAX(id), 0), COALESCE(SUM(state = 'open'), 0), MAX(closed_at) FROM calls"
    ).fetchone()
    unverified = connection.execute(
        "SELECT COUNT(*) FROM calls WHERE state != 'open' AND verification = 'unverified'"
    ).fetchone()[0]
    quarantined = connection.execute(
        "SELECT COUNT(*) FROM calls WHERE verification = 'quarantined' AND id > ?",
        (meta["baseline_high_water_call_id"],),
    ).fetchone()[0]
    max_event = connection.execute("SELECT COALESCE(MAX(id), 0) FROM operator_events").fetchone()[0]
    sequence = connection.execute(
        "SELECT seq FROM sqlite_sequence WHERE name = 'operator_events'"
    ).fetchone()
    return {
        "meta": meta,
        "max_call_id": int(max_call),
        "open_calls": int(open_calls),
        "last_close": None if last_close is None else int(last_close),
        "unverified": int(unverified),
        "quarantined": int(quarantined),
        "max_event_id": int(max_event),
        "event_sequence": None if sequence is None else int(sequence[0]),
    }


def token_of(state: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class Snapshot:
    state: dict[str, Any]
    token: str
    # (id, event, amount, code, created_at) for each operator event after the asked id.
    events_after: tuple[tuple[int, str, int | None, str | None, int], ...] = ()

    @property
    def meta(self) -> dict[str, Any]:
        return dict(self.state["meta"])


def read_snapshot(path: Path | str, *, events_after: int | None = None) -> Snapshot:
    # One consistent read-only view of the ledger (F3, F7 step 3). Any open or read error,
    # a hot journal, or a ledger that keeps changing is LEDGER_BUSY; a missing file is
    # LEDGER_UNAVAILABLE. Never writes, never recovers.

    resolved = Path(path).resolve()
    if not resolved.is_file():
        raise ReconcileRefused("LEDGER_UNAVAILABLE")
    try:
        connection = sqlite3.connect(
            f"{resolved.as_uri()}?mode=ro", uri=True, timeout=BUSY_SECONDS, isolation_level=None
        )
    except sqlite3.Error:
        raise ReconcileRefused("LEDGER_BUSY") from None
    with closing(connection):
        for _ in range(SNAPSHOT_ATTEMPTS):
            try:
                before = connection.execute("PRAGMA data_version").fetchone()[0]
                connection.execute("BEGIN")
                try:
                    state = _state(connection)
                    events: list[Any] = []
                    if events_after is not None:
                        events = connection.execute(
                            "SELECT id, event, amount_micro_usd, code, created_at"
                            " FROM operator_events WHERE id > ? ORDER BY id",
                            (events_after,),
                        ).fetchall()
                finally:
                    connection.execute("COMMIT")
                after = connection.execute("PRAGMA data_version").fetchone()[0]
            except sqlite3.Error:
                raise ReconcileRefused("LEDGER_BUSY") from None
            if before == after:
                return Snapshot(
                    state=state,
                    token=token_of(state),
                    events_after=tuple(tuple(row) for row in events),
                )
    raise ReconcileRefused("LEDGER_BUSY")


# --- the cross-process lock and the intent marker (F5) -------------------------------------

_process_locks: dict[str, threading.Lock] = {}
_process_locks_guard = threading.Lock()


def _process_lock(key: str) -> threading.Lock:
    with _process_locks_guard:
        return _process_locks.setdefault(key, threading.Lock())


@contextmanager
def reconcile_lock(path: Path | str) -> Iterator[None]:
    # The process lock, then the OS lock on the lock file beside the ledger; neither waits
    # (busy: LEDGER_BUSY). Taken and released by the calling thread. The OS lock belongs to
    # this handle and ends with the process; the file is never truncated or deleted.

    key = canonical(path)
    local = _process_lock(key)
    if not local.acquire(blocking=False):
        raise ReconcileRefused("LEDGER_BUSY")
    try:
        target = lock_file(path)
        try:
            fd = os.open(target, os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0), 0o600)
        except OSError:
            raise ReconcileRefused("LEDGER_BUSY") from None
        try:
            if not _os_lock(fd):
                raise ReconcileRefused("LEDGER_BUSY")
            try:
                yield
            finally:
                _os_unlock(fd)
        finally:
            os.close(fd)
    finally:
        local.release()


if sys.platform == "win32":
    import msvcrt

    def _os_lock(fd: int) -> bool:
        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        return True

    def _os_unlock(fd: int) -> None:
        os.lseek(fd, 0, os.SEEK_SET)
        # Closing the handle releases it as well.
        with suppress(OSError):
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _os_lock(fd: int) -> bool:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return False
        return True

    def _os_unlock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


def read_marker(path: Path | str) -> dict[str, Any] | None:
    # None when there is no marker; an unreadable marker is LEDGER_BUSY (F7 step 5).
    target = marker_file(path)
    try:
        text = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError:
        raise ReconcileRefused("LEDGER_BUSY") from None
    try:
        marker = json.loads(text)
    except ValueError:
        raise ReconcileRefused("LEDGER_BUSY") from None
    if not isinstance(marker, dict) or not isinstance(marker.get("run_id"), str):
        raise ReconcileRefused("LEDGER_BUSY")
    return marker


def _fsync_directory(directory: Path) -> None:
    # POSIX only: Windows cannot open a directory for fsync (rev 9 L5). A marker lost to a
    # power cut resolves as not provable; one that comes back names a finished run (stale).
    if sys.platform == "win32":
        return
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_marker(path: Path | str, marker: dict[str, Any]) -> None:
    target = marker_file(path)
    temporary = target.with_name(target.name + "." + secrets.token_hex(4) + ".part")
    with open(temporary, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(marker, sort_keys=True))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, target)
    _fsync_directory(target.parent)


def clear_marker(
    path: Path | str,
    run_id: str,
    pre_event_id: int | None = None,
    *,
    keep_overridden: bool = False,
) -> bool:
    # Only the marker of this run (and its P, when given) is ever removed (rev 9 L2); with
    # keep_overridden an override marker stays for the owner to close (QG L1).
    marker = read_marker(path)
    if marker is None or marker.get("run_id") != run_id:
        return False
    if pre_event_id is not None and marker.get("pre_event_id") != pre_event_id:
        return False
    if keep_overridden and marker.get("overridden"):
        return False
    marker_file(path).unlink()
    _fsync_directory(marker_file(path).parent)
    return True


# --- freshness and the preview checks (F3, F8) ---------------------------------------------


@dataclass(frozen=True)
class Reading:
    usage_micro_usd: int
    as_of_ms: int
    as_of_kind: str
    viewed_at_ms: int
    scope_workspace: bool
    scope_only: bool
    scope_cumulative: bool

    def inputs(self) -> dict[str, Any]:
        return {
            "usage_micro_usd": self.usage_micro_usd,
            "as_of": iso(self.as_of_ms),
            "as_of_kind": self.as_of_kind,
            "viewed_at": iso(self.viewed_at_ms),
        }


def margin_seconds(kind: str, configured_lag: float) -> float:
    # Never shorter than the operator's configured settle lag (QG round 3 L4).
    path = REFRESHED_MARGIN_SECONDS if kind == KIND_REFRESHED else VIEWED_MARGIN_SECONDS
    return max(float(path), float(configured_lag))


def settle_lag(reading: Reading, configured_lag: float, now_ms: int) -> float:
    # A slightly future as_of counts as now (the stricter direction).
    as_of = min(reading.as_of_ms, now_ms)
    return (now_ms - as_of) / 1000 + margin_seconds(reading.as_of_kind, configured_lag)


def check_freshness(
    reading: Reading, state: dict[str, Any], configured_lag: float, now_ms: int
) -> float:
    # G7: the settle lag this reading needs, or a refusal with the times HR can act on.

    skew = FUTURE_SKEW_SECONDS * 1000
    if reading.as_of_kind not in KINDS:
        raise ReconcileRefused("INVALID_INPUT")
    if reading.viewed_at_ms > now_ms + skew or reading.as_of_ms > now_ms + skew:
        raise ReconcileRefused("EVIDENCE_FUTURE")
    if reading.as_of_kind == KIND_VIEWED and reading.as_of_ms != reading.viewed_at_ms:
        raise ReconcileRefused("INVALID_INPUT")
    if reading.as_of_ms > reading.viewed_at_ms + skew:
        # The Console cannot have refreshed after HR looked at it.
        raise ReconcileRefused("INVALID_INPUT")
    if now_ms - reading.viewed_at_ms > MAX_VIEWED_AGE_SECONDS * 1000:
        raise ReconcileRefused("EVIDENCE_STALE")
    margin = margin_seconds(reading.as_of_kind, configured_lag)
    lag = settle_lag(reading, configured_lag, now_ms)
    if lag > MAX_LAG_SECONDS:
        raise ReconcileRefused(
            "EVIDENCE_STALE",
            latest_refresh_needed=iso(now_ms - (MAX_LAG_SECONDS - margin) * 1000),
        )
    last_close = state["last_close"]
    if last_close is not None and last_close > now_ms - lag * 1000:
        raise ReconcileRefused(
            "CALL_TOO_RECENT",
            earliest_as_of=iso(last_close + margin * 1000),
        )
    return lag


def gate_ledger(state: dict[str, Any]) -> None:
    # G1 to G5 on one ledger state (used by the preview and again inside the transaction).

    meta = state["meta"]
    if meta["profile_id"] != LEDGER_PROFILE_ID:
        raise ReconcileRefused("LEDGER_PROFILE_MISMATCH")
    if meta["breaker_open"]:
        raise ReconcileRefused("BREAKER_OPEN", breaker_code=meta["breaker_code"])
    if state["open_calls"] or meta["open_reserved_micro_usd"]:
        raise ReconcileRefused("CALL_OPEN")
    if state["unverified"]:
        raise ReconcileRefused("CALLS_UNVERIFIED", count=state["unverified"])
    if state["quarantined"]:
        raise ReconcileRefused("CALLS_QUARANTINED", count=state["quarantined"])
    if state["event_sequence"] != state["max_event_id"]:
        # rev 9 L3: event ids must continue from the last one, or P+1 proves nothing.
        raise ReconcileRefused("LEDGER_UNAVAILABLE")


def gate_usage(reading: Reading, state: dict[str, Any]) -> None:
    # G8 and G9 (rev 9 N1: the increment since the last reconciliation, not the carried
    # figure, decides; a repeated stale figure is caught by the same test).

    meta = state["meta"]
    last = int(meta["last_provider_usage_micro_usd"])
    if reading.usage_micro_usd < last:
        raise ReconcileRefused("USAGE_LOWER", last_usage_micro_usd=last)
    increment = reading.usage_micro_usd - last
    behind = int(meta["local_charged_micro_usd"]) - increment
    if behind > TOLERANCE_MICRO_USD:
        raise ReconcileRefused("USAGE_BEHIND", ledger_ahead_micro_usd=behind)


def expected_after(state: dict[str, Any], usage: int) -> dict[str, Any]:
    # Every meta column after ``reconcile(usage, release=False)`` (budget.py 990-1015), except
    # the two times it takes from its own clock.

    meta = dict(state["meta"])
    estimate = int(meta["baseline_micro_usd"]) + int(meta["local_charged_micro_usd"])
    drift = usage - estimate
    meta["baseline_micro_usd"] = usage if drift >= 0 else estimate
    meta["baseline_high_water_call_id"] = (
        state["max_call_id"] or meta["baseline_high_water_call_id"]
    )
    meta["local_charged_micro_usd"] = 0
    meta["last_provider_usage_micro_usd"] = usage
    if drift > TOLERANCE_MICRO_USD:
        meta["breaker_open"] = 1
        meta["breaker_code"] = "reconcile_drift"
    meta.pop("last_reconciled_at")
    meta.pop("breaker_opened_at")
    return meta


def drift_of(state: dict[str, Any], usage: int) -> int:
    meta = state["meta"]
    return usage - int(meta["baseline_micro_usd"]) - int(meta["local_charged_micro_usd"])


# --- the checked reconcile (F4 step 4) ------------------------------------------------------


@dataclass
class Expectation:
    token: str
    ledger_id: str
    pre_event_id: int
    usage_micro_usd: int
    after: dict[str, Any]
    deadline_wall_ms: int
    deadline_monotonic: float


class CheckedLedger(BudgetLedger):
    # ``reconcile`` with a compare-and-set before the unchanged accounting and a check of
    # what it wrote after it, in its one write transaction. Never a release, never recovery.

    def __init__(
        self,
        path: Path,
        expectation: Expectation,
        *,
        clock: Callable[[], float] = time.time,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(path, clock=clock, busy_timeout=BUSY_SECONDS)
        self.expectation = expectation
        self._monotonic = monotonic
        self._armed = False
        self._transactions = 0
        # True once the accounting ran and every check after it passed: from here an error is
        # uncertain (it may have come from COMMIT itself).
        self.work_returned = False
        # True once the accounting itself ran: if a check after it then fails (rolled back),
        # the ledger did something the preview did not predict.
        self.work_ran = False
        self.event_id: int | None = None

    @property
    def diverged(self) -> bool:
        return self.work_ran and not self.work_returned

    def reconcile(
        self, provider_usage_micro_usd: int, *, release: bool = False, settle_lag_seconds: float = 0
    ) -> int:
        if release:
            raise LedgerError("INVALID_INPUT", "no release here")
        self._armed = True
        self._transactions = 0
        self.work_ran = self.work_returned = False
        try:
            return super().reconcile(
                provider_usage_micro_usd, release=False, settle_lag_seconds=settle_lag_seconds
            )
        finally:
            self._armed = False

    def _transaction(self, work: Callable[[sqlite3.Connection], Any]) -> Any:
        if not self._armed:
            return super()._transaction(work)
        self._transactions += 1
        if self._transactions != 1:
            # budget.py changed shape: refuse before any second transaction begins.
            raise LedgerError("CONTROLS_CONFLICT", "unexpected transaction")

        def checked(connection: sqlite3.Connection) -> Any:
            self._before(connection)
            start = self._now()
            result = work(connection)
            self.work_ran = True
            end = self._now()
            self._after(connection, start, end)
            self.work_returned = True
            return result

        return super()._transaction(checked)

    def _in_time(self) -> bool:
        expectation = self.expectation
        return (
            self._monotonic() < expectation.deadline_monotonic
            and self._now() < expectation.deadline_wall_ms
        )

    def _before(self, connection: sqlite3.Connection) -> None:
        expectation = self.expectation
        state = _state(connection)
        if token_of(state) != expectation.token:
            raise LedgerError("CONTROLS_CONFLICT", "the ledger changed")
        if state["meta"]["ledger_id"] != expectation.ledger_id:
            raise LedgerError("CONTROLS_CONFLICT", "another ledger")
        if state["max_event_id"] != expectation.pre_event_id:
            raise LedgerError("CONTROLS_CONFLICT", "the ledger changed")
        try:
            gate_ledger(state)
        except ReconcileRefused:
            raise LedgerError("CONTROLS_CONFLICT", "the ledger changed") from None
        if not self._in_time():
            raise LedgerError("CONTROLS_CONFLICT", "past the deadline")

    def _after(self, connection: sqlite3.Connection, start: int, end: int) -> None:
        expectation = self.expectation
        first = expectation.pre_event_id + 1
        events = connection.execute(
            "SELECT id, event, amount_micro_usd, code FROM operator_events WHERE id > ?"
            " ORDER BY id",
            (expectation.pre_event_id,),
        ).fetchall()
        opens = bool(expectation.after["breaker_open"])
        wanted: list[tuple[int, str, int | None, str | None]] = [
            (first, "reconciled", expectation.usage_micro_usd, None)
        ]
        if opens:
            wanted.append((first + 1, "breaker_opened", None, "reconcile_drift"))
        if [tuple(row) for row in events] != wanted:
            raise LedgerError("CONTROLS_CONFLICT", "unexpected events")
        row = connection.execute(f"SELECT {', '.join(META_COLUMNS)} FROM ledger_meta").fetchone()
        meta = dict(zip(META_COLUMNS, row, strict=True))
        reconciled_at, opened_at = meta.pop("last_reconciled_at"), meta.pop("breaker_opened_at")
        if meta != expectation.after:
            raise LedgerError("CONTROLS_CONFLICT", "unexpected state")
        if reconciled_at is None or not start <= reconciled_at <= end:
            raise LedgerError("CONTROLS_CONFLICT", "unexpected state")
        if opens:
            # QG round 3 L2: a backward clock step must not let reset_breaker skip the second
            # reconcile it needs after this one.
            if opened_at is None or not start <= opened_at <= end or opened_at < reconciled_at:
                raise LedgerError("CONTROLS_CONFLICT", "unexpected state")
        elif opened_at is not None:
            raise LedgerError("CONTROLS_CONFLICT", "unexpected state")
        if not self._in_time():
            raise LedgerError("CONTROLS_CONFLICT", "past the deadline")
        self.event_id = first


# --- the run store (F6) ---------------------------------------------------------------------

_RUNS = """
CREATE TABLE IF NOT EXISTS claude_reconciliation_runs (
    run_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN
        ('requested', 'applied', 'refused', 'failed', 'unresolved', 'owner_closed')),
    actor TEXT NOT NULL,
    role TEXT,
    intent_at INTEGER NOT NULL,
    deadline_at INTEGER NOT NULL,
    ledger_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    ledger_path TEXT NOT NULL,
    token TEXT NOT NULL,
    pre_event_id INTEGER NOT NULL,
    usage_micro_usd INTEGER NOT NULL,
    as_of INTEGER NOT NULL,
    as_of_kind TEXT NOT NULL,
    viewed_at INTEGER NOT NULL,
    drift_micro_usd INTEGER NOT NULL,
    expected TEXT NOT NULL,
    event_id INTEGER,
    reason TEXT,
    attribution_basis TEXT,
    finished_at INTEGER,
    closed_by TEXT,
    owner_reference TEXT,
    acknowledged_event_id INTEGER,
    acknowledged_state TEXT,
    marker_overridden INTEGER
);
CREATE TABLE IF NOT EXISTS claude_reconciliation_prerequisite (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    recorded_by TEXT NOT NULL,
    recorded_at INTEGER NOT NULL,
    owner_reference TEXT NOT NULL
);
"""

# Allowed transitions (F6): every write is UPDATE ... WHERE status = <expected>.
TRANSITIONS = {
    REQUESTED: (APPLIED, REFUSED, FAILED, UNRESOLVED, OWNER_CLOSED),
    UNRESOLVED: (OWNER_CLOSED,),
}


class RunConflict(Exception):
    pass


@dataclass
class Runs:
    # The run table in the model state database. Created on the first write (never at start
    # up); readers treat a missing database or table as no runs. Never trimmed.

    path: Path
    clock: Callable[[], float] = field(default=time.time)

    def _now(self) -> int:
        return int(self.clock() * 1000)

    @contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("BEGIN IMMEDIATE")
            try:
                for statement in _RUNS.split(";"):
                    if statement.strip():
                        db.execute(statement)
                yield db
            except BaseException:
                db.execute("ROLLBACK")
                raise
            db.execute("COMMIT")
        finally:
            db.close()

    def _read(self) -> sqlite3.Connection | None:
        if not self.path.is_file():
            return None
        db = sqlite3.connect(f"{self.path.resolve().as_uri()}?mode=ro", uri=True, timeout=10)
        db.row_factory = sqlite3.Row
        table = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table'"
            " AND name = 'claude_reconciliation_runs'"
        ).fetchone()
        if table is None:
            db.close()
            return None
        return db

    def all(self, limit: int = 50) -> list[dict[str, Any]]:
        db = self._read()
        if db is None:
            return []
        with closing(db):
            rows = db.execute(
                "SELECT * FROM claude_reconciliation_runs ORDER BY intent_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get(self, run_id: str) -> dict[str, Any] | None:
        db = self._read()
        if db is None:
            return None
        with closing(db):
            row = db.execute(
                "SELECT * FROM claude_reconciliation_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        return None if row is None else dict(row)

    def open_for(self, ledger_id: str) -> list[dict[str, Any]]:
        db = self._read()
        if db is None:
            return []
        with closing(db):
            rows = db.execute(
                "SELECT * FROM claude_reconciliation_runs WHERE ledger_id = ?"
                " AND status IN ('requested', 'unresolved') ORDER BY intent_at",
                (ledger_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def sharing(self, ledger_id: str, pre_event_id: int, run_id: str) -> int:
        # rev 8 N2: other runs that could claim the same event (provably uncommitted runs,
        # refused or failed, do not count).
        db = self._read()
        if db is None:
            return 0
        with closing(db):
            row = db.execute(
                "SELECT COUNT(*) FROM claude_reconciliation_runs WHERE ledger_id = ?"
                " AND pre_event_id = ? AND run_id != ?"
                " AND status IN ('requested', 'unresolved', 'applied')",
                (ledger_id, pre_event_id, run_id),
            ).fetchone()
        return int(row[0])

    def prerequisite(self) -> dict[str, Any] | None:
        if not self.path.is_file():
            return None
        db = sqlite3.connect(f"{self.path.resolve().as_uri()}?mode=ro", uri=True, timeout=10)
        db.row_factory = sqlite3.Row
        with closing(db):
            table = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table'"
                " AND name = 'claude_reconciliation_prerequisite'"
            ).fetchone()
            if table is None:
                return None
            row = db.execute(
                "SELECT * FROM claude_reconciliation_prerequisite WHERE id = 1"
            ).fetchone()
        return None if row is None else dict(row)

    def record_prerequisite(self, by: str, reference: str) -> None:
        with self._write() as db:
            db.execute(
                "INSERT INTO claude_reconciliation_prerequisite"
                " (id, recorded_by, recorded_at, owner_reference) VALUES (1, ?, ?, ?)"
                " ON CONFLICT (id) DO UPDATE SET recorded_by = excluded.recorded_by,"
                " recorded_at = excluded.recorded_at, owner_reference = excluded.owner_reference",
                (by, self._now(), reference),
            )
            ModelAdminStore._insert_event(
                db, actor=by, role=None, action=ACTION, outcome="recorded", code="PREREQUISITE"
            )

    def note(self, *, actor: str, outcome: str, code: str) -> None:
        with self._write() as db:
            ModelAdminStore._insert_event(
                db, actor=actor, role=None, action=ACTION, outcome=outcome, code=code
            )

    def begin(self, row: dict[str, Any]) -> None:
        # F4 step 2: refuse while any run for this ledger is open, then insert the intent
        # with its audit row, in one transaction.

        with self._write() as db:
            open_run = db.execute(
                "SELECT run_id FROM claude_reconciliation_runs WHERE ledger_id = ?"
                " AND status IN ('requested', 'unresolved')",
                (row["ledger_id"],),
            ).fetchone()
            if open_run is not None:
                raise RunConflict(str(open_run["run_id"]))
            names = ", ".join(row)
            db.execute(
                f"INSERT INTO claude_reconciliation_runs ({names})"  # noqa: S608 (own keys)
                f" VALUES ({', '.join('?' for _ in row)})",
                tuple(row.values()),
            )
            ModelAdminStore._insert_event(
                db,
                actor=row["actor"],
                role=row["role"],
                action=ACTION,
                outcome=REQUESTED,
                code=f"RUN_{row['run_id']}",
            )

    def finish(
        self,
        run_id: str,
        status: str,
        *,
        expected: str,
        actor: str,
        role: str | None = None,
        code: str | None = None,
        **fields: Any,
    ) -> None:
        if status not in TRANSITIONS.get(expected, ()):
            raise RunConflict(run_id)
        if status == APPLIED and not (fields.get("attribution_basis") and fields.get("event_id")):
            # Q12: applied needs its proof recorded with it (the apply returned, or resolve).
            raise RunConflict(run_id)
        values = {"status": status, "finished_at": self._now(), **fields}
        assignments = ", ".join(f"{name} = ?" for name in values)
        with self._write() as db:
            changed = db.execute(
                f"UPDATE claude_reconciliation_runs SET {assignments}"  # noqa: S608 (own keys)
                " WHERE run_id = ? AND status = ?",
                (*values.values(), run_id, expected),
            ).rowcount
            if changed != 1:
                raise RunConflict(run_id)
            ModelAdminStore._insert_event(
                db,
                actor=actor,
                role=role,
                action=ACTION,
                outcome=status,
                code=code or f"RUN_{run_id}",
            )


# --- resolve (F7) -------------------------------------------------------------------------


def resolve_bound_ms(run: dict[str, Any]) -> int:
    return int(run["deadline_at"]) + int((BUSY_SECONDS + RESOLVE_GRACE_SECONDS) * 1000)


def classify(
    run: dict[str, Any],
    snapshot: Snapshot,
    marker: dict[str, Any] | None,
    *,
    sharing: int,
    prerequisite: dict[str, Any] | None,
) -> tuple[str, str]:
    # The four-outcome rule (Q12 as the owner clarified it). Returns (status, reason).
    # APPLIED needs commit and attribution proven; FAILED needs non-commit proven; anything
    # else is UNRESOLVED. Callers return LEDGER_BUSY before calling this when the ledger, the
    # marker or the lock cannot be read, or the deadline bound has not passed.

    meta = snapshot.state["meta"]
    if (
        meta["ledger_id"] != run["ledger_id"]
        or meta["profile_id"] != run["profile_id"]
        or meta["profile_id"] != LEDGER_PROFILE_ID
    ):
        return UNRESOLVED, "ledger_changed"
    first = int(run["pre_event_id"]) + 1
    events = {row[0]: row for row in snapshot.events_after}
    p1 = events.get(first)
    if p1 is None:
        # The compare-and-set would have put our event at exactly P+1, and past the bound
        # with the lock held nothing can still commit it.
        return FAILED, "event_absent"
    _, event, amount, _, created_at = p1
    if event != "reconciled" or amount != run["usage_micro_usd"]:
        return FAILED, "event_other"
    p2 = events.get(first + 1)
    if p2 is not None and p2[1] == "released":
        # A release follows its own reconcile in one transaction; ours never releases.
        return FAILED, "event_released"
    if created_at > int(run["deadline_at"]) + int(BUSY_SECONDS * 1000):
        return UNRESOLVED, "event_after_bound"
    expected = json.loads(run["expected"])
    if expected["breaker_open"] and (
        p2 is None or p2[1] != "breaker_opened" or p2[3] != "reconcile_drift"
    ):
        # Ours writes the drift breaker right after P+1 in the same transaction.
        return UNRESOLVED, "sequence_mismatch"
    if sharing:
        return UNRESOLVED, "shared_event"
    intact = (
        marker is not None
        and marker.get("run_id") == run["run_id"]
        and marker.get("ledger_id") == run["ledger_id"]
        and marker.get("pre_event_id") == run["pre_event_id"]
        and marker.get("overridden") is False
    )
    if not intact:
        return UNRESOLVED, "marker_overridden" if marker and marker.get("overridden") else (
            "marker_missing"
        )
    if prerequisite is None:
        return UNRESOLVED, "prerequisite_missing"
    return APPLIED, "event_matches"


# --- the workflow: preview, apply, resolve, owner close -----------------------------------


@dataclass
class Preview:
    preview_id: str
    actor: str
    session: str
    created: float
    path: Path
    ledger_key: str
    ledger_id: str
    token: str
    pre_event_id: int
    reading: Reading
    after: dict[str, Any]
    drift: int


class Reconciler:
    # One per service process (the assistant runs as one worker: previews live in memory).
    # ``ledger_path`` and ``configured_lag`` are read per call, as the settings are.

    def __init__(
        self,
        ledger_path: Callable[[], Path],
        runs: Runs,
        configured_lag: Callable[[], float],
        *,
        clock: Callable[[], float] = time.time,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.ledger_path = ledger_path
        self.runs = runs
        self.configured_lag = configured_lag
        self.clock = clock
        self.monotonic = monotonic
        self._previews: dict[str, Preview] = {}
        self._previews_lock = threading.Lock()

    def _now_ms(self) -> int:
        return int(self.clock() * 1000)

    def _invalidate(self, ledger_key: str) -> None:
        with self._previews_lock:
            for key in [k for k, p in self._previews.items() if p.ledger_key == ledger_key]:
                del self._previews[key]

    # -- preview (F3): reads only; the preview itself is kept in memory --------------------

    def preview(self, reading: Reading, *, actor: str, session: str) -> dict[str, Any]:
        if not (reading.scope_workspace and reading.scope_only and reading.scope_cumulative):
            raise ReconcileRefused("SCOPE_UNCONFIRMED")
        if reading.usage_micro_usd < 0:
            raise ReconcileRefused("INVALID_INPUT")
        path = self.ledger_path()
        snapshot = read_snapshot(path)
        state = snapshot.state
        try:
            prerequisite = self.runs.prerequisite()
            open_runs = self.runs.open_for(str(state["meta"]["ledger_id"]))
        except sqlite3.Error:
            raise ReconcileRefused("RUN_STORE_UNAVAILABLE") from None
        if prerequisite is None:
            raise ReconcileRefused("PREREQUISITE_MISSING")
        gate_ledger(state)
        if open_runs:
            raise ReconcileRefused("RUN_UNRESOLVED", run_id=open_runs[0]["run_id"])
        marker = read_marker(path)
        if marker is not None:
            raise ReconcileRefused("RUN_UNRESOLVED", run_id=marker["run_id"])
        gate_usage(reading, state)
        now = self._now_ms()
        lag = check_freshness(reading, state, self.configured_lag(), now)
        after = expected_after(state, reading.usage_micro_usd)
        preview = Preview(
            preview_id=secrets.token_hex(16),
            actor=actor,
            session=session,
            created=self.monotonic(),
            path=Path(path),
            ledger_key=canonical(path),
            ledger_id=str(state["meta"]["ledger_id"]),
            token=snapshot.token,
            pre_event_id=int(state["max_event_id"]),
            reading=reading,
            after=after,
            drift=drift_of(state, reading.usage_micro_usd),
        )
        with self._previews_lock:
            # Expired previews go; each administrator has at most one live preview.
            for key, old in list(self._previews.items()):
                if self.monotonic() - old.created > PREVIEW_SECONDS or old.actor == actor:
                    del self._previews[key]
            self._previews[preview.preview_id] = preview
        return self._preview_view(preview, state, lag, now)

    def _preview_view(
        self, preview: Preview, state: dict[str, Any], lag: float, now: int
    ) -> dict[str, Any]:
        from . import anthropic_runtime  # the windows the chat and paid gates apply

        meta = state["meta"]
        after = preview.after
        chat = anthropic_runtime.CHAT_RECONCILE_SECONDS
        paid = anthropic_runtime.PAID_RECONCILE_SECONDS
        baseline = int(meta["baseline_micro_usd"])
        charged = int(meta["local_charged_micro_usd"])
        return {
            "preview_id": preview.preview_id,
            "expires_at": iso(now + PREVIEW_SECONDS * 1000),
            "inputs": preview.reading.inputs(),
            "fallback": preview.reading.as_of_kind == KIND_VIEWED,
            "settle_lag_seconds": round(lag),
            "margin_seconds": round(
                margin_seconds(preview.reading.as_of_kind, self.configured_lag())
            ),
            "before": {
                "baseline_micro_usd": baseline,
                "local_charged_micro_usd": charged,
                "estimate_micro_usd": baseline + charged,
                "last_provider_usage_micro_usd": meta["last_provider_usage_micro_usd"],
                "reconciled_at": iso(meta["last_reconciled_at"]),
            },
            "after": {
                "baseline_micro_usd": after["baseline_micro_usd"],
                "local_charged_micro_usd": 0,
                "estimate_micro_usd": after["baseline_micro_usd"],
                "last_provider_usage_micro_usd": after["last_provider_usage_micro_usd"],
            },
            # Signed: positive means the Console shows more than the ledger estimated.
            "drift_micro_usd": preview.drift,
            "tolerance_micro_usd": TOLERANCE_MICRO_USD,
            "breaker_opens": bool(after["breaker_open"]),
            # What the ledger already kept above the Console at the last reconciliation.
            "carried_micro_usd": baseline - int(meta["last_provider_usage_micro_usd"]),
            "cap_micro_usd": meta["cap_micro_usd"],
            # If applied now; the ledger takes its own time when it commits.
            "chat_deadline_at": iso(now + chat * 1000),
            "paid_deadline_at": iso(now + paid * 1000),
        }

    # -- apply (F4) ------------------------------------------------------------------------

    def _take(self, preview_id: str, actor: str, session: str) -> Preview:
        with self._previews_lock:
            preview = self._previews.get(preview_id)
            if preview is None or preview.actor != actor or preview.session != session:
                raise ReconcileRefused("PREVIEW_UNKNOWN")
            # Single use, whatever happens next.
            del self._previews[preview_id]
            if self.monotonic() - preview.created > PREVIEW_SECONDS:
                raise ReconcileRefused("PREVIEW_EXPIRED")
        return preview

    def apply(
        self,
        preview_id: str,
        *,
        confirm_usage_micro_usd: int,
        scopes: tuple[bool, bool, bool],
        actor: str,
        role: str | None,
        session: str,
    ) -> dict[str, Any]:
        preview = self._take(preview_id, actor, session)
        if confirm_usage_micro_usd != preview.reading.usage_micro_usd:
            raise ReconcileRefused("USAGE_CONFIRMATION_REQUIRED")
        if not all(scopes):
            raise ReconcileRefused("SCOPE_UNCONFIRMED")
        if canonical(self.ledger_path()) != preview.ledger_key:
            raise ReconcileRefused("LEDGER_PROFILE_MISMATCH")
        if self._now_ms() - preview.reading.viewed_at_ms > MAX_VIEWED_AGE_SECONDS * 1000:
            raise ReconcileRefused("EVIDENCE_STALE")
        try:
            prerequisite = self.runs.prerequisite()
        except sqlite3.Error:
            raise ReconcileRefused("RUN_STORE_UNAVAILABLE") from None
        if prerequisite is None:
            raise ReconcileRefused("PREREQUISITE_MISSING")
        with reconcile_lock(preview.path):
            # Checked only once the lock is held (rev 9 L1).
            marker = read_marker(preview.path)
            if marker is not None:
                raise ReconcileRefused("RUN_UNRESOLVED", run_id=marker["run_id"])
            return self._apply_locked(preview, actor=actor, role=role)

    def _apply_locked(self, preview: Preview, *, actor: str, role: str | None) -> dict[str, Any]:
        path = preview.path
        reading = preview.reading
        start_wall = self._now_ms()
        start_monotonic = self.monotonic()
        run_id = secrets.token_hex(16)
        deadline = start_wall + APPLY_SECONDS * 1000
        try:
            self.runs.begin(
                {
                    "run_id": run_id,
                    "status": REQUESTED,
                    "actor": actor,
                    "role": role,
                    "intent_at": start_wall,
                    "deadline_at": deadline,
                    "ledger_id": preview.ledger_id,
                    "profile_id": LEDGER_PROFILE_ID,
                    "ledger_path": preview.ledger_key,
                    "token": preview.token,
                    "pre_event_id": preview.pre_event_id,
                    "usage_micro_usd": reading.usage_micro_usd,
                    "as_of": reading.as_of_ms,
                    "as_of_kind": reading.as_of_kind,
                    "viewed_at": reading.viewed_at_ms,
                    "drift_micro_usd": preview.drift,
                    "expected": json.dumps(preview.after, sort_keys=True),
                }
            )
        except RunConflict as conflict:
            raise ReconcileRefused("RUN_UNRESOLVED", run_id=str(conflict)) from None
        except sqlite3.Error:
            raise ReconcileRefused("RUN_STORE_UNAVAILABLE") from None
        self._invalidate(preview.ledger_key)

        def finish(status: str, reason: str, **fields: Any) -> bool:
            try:
                self.runs.finish(
                    run_id,
                    status,
                    expected=REQUESTED,
                    actor=actor,
                    role=role,
                    reason=reason,
                    **fields,
                )
            except (RunConflict, sqlite3.Error):
                return False
            return True

        try:
            write_marker(
                path,
                {
                    "run_id": run_id,
                    "ledger_id": preview.ledger_id,
                    "pre_event_id": preview.pre_event_id,
                    "deadline_at": deadline,
                    "overridden": False,
                    "overridden_at": None,
                },
            )
        except OSError:
            # The ledger was never touched: a certain refusal.
            finish(REFUSED, "marker_not_written")
            raise ReconcileRefused("LEDGER_BUSY", run_id=run_id) from None

        ledger = CheckedLedger(
            path,
            Expectation(
                token=preview.token,
                ledger_id=preview.ledger_id,
                pre_event_id=preview.pre_event_id,
                usage_micro_usd=reading.usage_micro_usd,
                after=preview.after,
                deadline_wall_ms=deadline,
                deadline_monotonic=start_monotonic + APPLY_SECONDS,
            ),
            clock=self.clock,
            monotonic=self.monotonic,
        )
        try:
            # F8.0: the lag is worked out again from the apply clock.
            lag = settle_lag(reading, self.configured_lag(), self._now_ms())
            if lag > MAX_LAG_SECONDS:
                raise LedgerError("RECONCILE_REFUSED", "the settle lag")
            ledger.verify()
            ledger.reconcile(reading.usage_micro_usd, settle_lag_seconds=lag)
        except Exception as error:  # noqa: BLE001 - every failure is classified below
            if ledger.work_returned:
                # Raised during or after COMMIT: not known here. The run stays requested and
                # the marker stays in place for resolve.
                return self._run_view(run_id, outcome="uncertain")
            code = error.code if isinstance(error, LedgerError) else "LEDGER_BUSY"
            # A check after the accounting failed (rolled back): the ledger did something the
            # preview did not predict. Anything else is an expected, certain refusal.
            status = FAILED if ledger.diverged else REFUSED
            if finish(status, code.lower()):
                # A marker left behind names a finished run (stale): resolve clears it.
                with suppress(OSError, ReconcileRefused):
                    clear_marker(path, run_id, preview.pre_event_id)
            public = code if code in ("CONTROLS_CONFLICT", "LEDGER_BUSY") else "RECONCILE_REFUSED"
            raise ReconcileRefused(public, run_id=run_id) from None
        if not finish(
            APPLIED, "apply_returned", event_id=ledger.event_id, attribution_basis="apply_returned"
        ):
            # Proven but not recorded: the marker stays, so resolve can prove it again.
            return self._run_view(run_id, outcome="uncertain")
        # A marker left behind names a finished run (stale): resolve clears it.
        with suppress(OSError, ReconcileRefused):
            clear_marker(path, run_id, preview.pre_event_id)
        return self._run_view(run_id, outcome=APPLIED)

    def _run_view(self, run_id: str, *, outcome: str) -> dict[str, Any]:
        try:
            run = self.runs.get(run_id)
        except sqlite3.Error:
            run = None
        return {"outcome": outcome, "run": None if run is None else run_view(run)}

    # -- resolve (F7) ----------------------------------------------------------------------

    def resolve(self, run_id: str, *, actor: str, role: str | None) -> dict[str, Any]:
        try:
            run = self.runs.get(run_id)
        except sqlite3.Error:
            raise ReconcileRefused("RUN_STORE_UNAVAILABLE") from None
        if run is None:
            raise ReconcileRefused("RUN_UNKNOWN")
        path = self.ledger_path()
        with reconcile_lock(path):
            marker = read_marker(path)
            if run["status"] != REQUESTED:
                if run["status"] in FINAL_STATES and marker and marker.get("run_id") == run_id:
                    # Stale (rev 9 L4); an override marker stays for the owner (QG L1).
                    with suppress(OSError):
                        clear_marker(path, run_id, int(run["pre_event_id"]), keep_overridden=True)
                return {"outcome": run["status"], "run": run_view(run)}
            if self._now_ms() < resolve_bound_ms(run):
                raise ReconcileRefused("RESOLVE_NOT_YET", retry_after=iso(resolve_bound_ms(run)))
            if canonical(path) != run["ledger_path"]:
                status, reason = UNRESOLVED, "ledger_changed"
            else:
                snapshot = read_snapshot(path, events_after=int(run["pre_event_id"]))
                try:
                    sharing = self.runs.sharing(run["ledger_id"], run["pre_event_id"], run_id)
                    prerequisite = self.runs.prerequisite()
                except sqlite3.Error:
                    raise ReconcileRefused("RUN_STORE_UNAVAILABLE") from None
                status, reason = classify(
                    run, snapshot, marker, sharing=sharing, prerequisite=prerequisite
                )
            fields: dict[str, Any] = {}
            if status == APPLIED:
                fields = {
                    "event_id": int(run["pre_event_id"]) + 1,
                    "attribution_basis": "marker_and_prerequisite",
                }
            if marker is not None and marker.get("run_id") == run_id:
                fields["marker_overridden"] = int(bool(marker.get("overridden")))
            try:
                self.runs.finish(
                    run_id,
                    status,
                    expected=REQUESTED,
                    actor=actor,
                    role=role,
                    reason=reason,
                    **fields,
                )
            except RunConflict:
                raise ReconcileRefused("RUN_UNRESOLVED", run_id=run_id) from None
            except sqlite3.Error:
                raise ReconcileRefused("RUN_STORE_UNAVAILABLE") from None
            if status in (APPLIED, FAILED):
                # A failed run's override marker stays for the owner's close (QG L1); a clear
                # that fails leaves a stale marker the next resolve or owner close removes.
                with suppress(OSError):
                    clear_marker(path, run_id, int(run["pre_event_id"]), keep_overridden=True)
            return self._run_view(run_id, outcome=status)

    # -- owner close (the operator's script only, F6) -------------------------------------

    def owner_close(
        self, run_id: str, *, by: str, reference: str, acknowledged_event_id: int | None
    ) -> dict[str, Any]:
        if not reference.strip():
            raise ReconcileRefused("INVALID_INPUT")
        run = self.runs.get(run_id)
        if run is None:
            raise ReconcileRefused("RUN_UNKNOWN")
        path = self.ledger_path()
        with reconcile_lock(path):
            status = run["status"]
            if status in FINAL_STATES:
                marker = read_marker(path)
                if marker is None or marker.get("run_id") != run_id:
                    raise ReconcileRefused("RUN_UNRESOLVED", run_id=run_id)
                clear_marker(path, run_id)
                self.runs.note(actor=by, outcome="stale_marker_cleared", code=f"RUN_{run_id}")
                return self._run_view(run_id, outcome="stale_marker_cleared")
            if not (
                status == UNRESOLVED
                or (status == REQUESTED and self._now_ms() >= resolve_bound_ms(run))
            ):
                raise ReconcileRefused("RUN_UNRESOLVED", run_id=run_id)
            marker = read_marker(path)
            seen = "unknown"
            if acknowledged_event_id is not None:
                try:
                    snapshot = read_snapshot(path, events_after=acknowledged_event_id - 1)
                    present = any(row[0] == acknowledged_event_id for row in snapshot.events_after)
                    seen = "present" if present else "absent"
                except ReconcileRefused:
                    seen = "unknown"
            self.runs.finish(
                run_id,
                OWNER_CLOSED,
                expected=status,
                actor=by,
                reason=f"owner_closed_from_{status}:{run.get('reason') or 'none'}",
                closed_by=by,
                owner_reference=reference.strip()[:200],
                acknowledged_event_id=acknowledged_event_id,
                acknowledged_state=seen,
                marker_overridden=int(bool(marker and marker.get("overridden"))),
            )
            if marker is not None and marker.get("run_id") == run_id:
                clear_marker(path, run_id)
            return self._run_view(run_id, outcome=OWNER_CLOSED)

    # -- the read-only listing (F11: nothing is written) ----------------------------------

    def listing(self) -> dict[str, Any]:
        try:
            runs = self.runs.all(20)
            prerequisite = self.runs.prerequisite()
        except sqlite3.Error:
            raise ReconcileRefused("RUN_STORE_UNAVAILABLE") from None
        try:
            marker = read_marker(self.ledger_path())
            readable = True
        except ReconcileRefused:
            marker, readable = None, False
        views = []
        for run in runs:
            view = run_view(run)
            if run["status"] == REQUESTED:
                view["resolvable_after"] = iso(resolve_bound_ms(run))
            views.append(view)
        return {
            "runs": views,
            "prerequisite_recorded": prerequisite is not None,
            "marker_readable": readable,
            "marker_run_id": None if marker is None else marker.get("run_id"),
            "marker_overridden": bool(marker and marker.get("overridden")),
        }


def run_view(run: dict[str, Any]) -> dict[str, Any]:
    # What the page shows of a run: no path, no token, no expected state.
    return {
        "run_id": run["run_id"],
        "status": run["status"],
        "actor": run["actor"],
        "intent_at": iso(run["intent_at"]),
        "finished_at": iso(run.get("finished_at")),
        "usage_micro_usd": run["usage_micro_usd"],
        "drift_micro_usd": run["drift_micro_usd"],
        "as_of": iso(run["as_of"]),
        "as_of_kind": run["as_of_kind"],
        "event_id": run.get("event_id"),
        "reason": run.get("reason"),
        "attribution_basis": run.get("attribution_basis"),
        "owner_reference": run.get("owner_reference"),
        "acknowledged_state": run.get("acknowledged_state"),
    }


# --- the operator's script (F12): the marker rules, under the lock ------------------------


@contextmanager
def operator_write(path: Path | str, *, override_run: str | None = None) -> Iterator[None]:
    # For the script's ledger writes (reconcile, reset-breaker, set-cap, verify): take the
    # reconcile lock, then refuse while an intent marker exists (checked under the lock, rev 9
    # L1). ``override_run`` (reconcile only) first records the owner's override on the marker
    # naming that run, durably, then proceeds.

    with reconcile_lock(path):
        marker = read_marker(path)
        if marker is not None:
            if override_run is None or marker.get("run_id") != override_run:
                raise ReconcileRefused("RUN_UNRESOLVED", run_id=marker.get("run_id"))
            marker["overridden"] = True
            marker["overridden_at"] = int(time.time() * 1000)
            write_marker(path, marker)
        yield
