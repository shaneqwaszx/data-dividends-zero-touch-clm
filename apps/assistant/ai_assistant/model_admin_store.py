"""Model management state (D-093): which model is active, the last one that worked, test and
qualification results, and the audit history. Local SQLite under apps/assistant/data (not in
Git), separate from the knowledge store and the budget ledger.

The activation is one row changed only by compare-and-set on its revision, so two
administrators (or two service processes) can never both apply a change made from the same
view. Audit rows are content-free: who, what, which profile, the outcome and a closed code;
never a URL, a credential, a prompt, an answer or case data. The newest ``MAX_EVENTS`` are
kept.

Only one qualification may run at a time across every process sharing the database: a run
holds the ``running`` row and refreshes its heartbeat; a run whose heartbeat is older than
``STALE_SECONDS`` is closed as an error before another may start.
"""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

MAX_EVENTS = 5000
STALE_SECONDS = 300

_SCHEMA = """
CREATE TABLE IF NOT EXISTS activation (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    revision INTEGER NOT NULL,
    active_profile_id TEXT NOT NULL,
    active_fingerprint TEXT NOT NULL,
    active_qualification_id TEXT,
    active_prompt_limit INTEGER,
    last_good_profile_id TEXT,
    last_good_fingerprint TEXT,
    last_good_qualification_id TEXT,
    last_good_prompt_limit INTEGER,
    changed_at TEXT NOT NULL,
    changed_by TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    role TEXT,
    action TEXT NOT NULL,
    profile_id TEXT,
    fingerprint TEXT,
    outcome TEXT NOT NULL,
    code TEXT,
    revision INTEGER
);
CREATE TABLE IF NOT EXISTS qualifications (
    qualification_id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    basis TEXT NOT NULL,
    status TEXT NOT NULL,
    code TEXT,
    started_at TEXT NOT NULL,
    started_by TEXT NOT NULL,
    finished_at TEXT,
    heartbeat_at TEXT NOT NULL,
    done_turns INTEGER NOT NULL DEFAULT 0,
    total_turns INTEGER NOT NULL DEFAULT 0,
    cancel_requested INTEGER NOT NULL DEFAULT 0,
    summary TEXT
);
CREATE INDEX IF NOT EXISTS qualifications_profile ON qualifications (profile_id, started_at);
CREATE TABLE IF NOT EXISTS connection_tests (
    profile_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    at TEXT NOT NULL,
    by_user TEXT NOT NULL,
    outcome TEXT NOT NULL,
    code TEXT,
    summary TEXT NOT NULL
);
"""

QUALIFICATION_STATES = frozenset({"running", "passed", "failed", "cancelled", "error"})


class RevisionConflict(Exception):
    """The activation changed since the caller's view."""


class QualificationBusy(Exception):
    """Another qualification is running."""


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Activation:
    revision: int
    active_profile_id: str
    active_fingerprint: str
    active_qualification_id: str | None
    active_prompt_limit: int | None
    last_good_profile_id: str | None
    last_good_fingerprint: str | None
    last_good_qualification_id: str | None
    last_good_prompt_limit: int | None
    changed_at: str | None
    changed_by: str | None


@dataclass(frozen=True)
class Choice:
    """A profile as activated: what it was, which qualification allowed it, its prompt bound."""

    profile_id: str
    fingerprint: str
    qualification_id: str | None = None
    prompt_limit: int | None = None


class ModelAdminStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self._path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
            except BaseException:
                db.execute("ROLLBACK")
                raise
            db.execute("COMMIT")

    # --- activation ------------------------------------------------------------------------

    def revision(self) -> int:
        with self._connect() as db:
            row = db.execute("SELECT revision FROM activation WHERE id = 1").fetchone()
        return int(row["revision"]) if row else 0

    def activation(self, baseline: Choice) -> Activation:
        with self._connect() as db:
            row = db.execute("SELECT * FROM activation WHERE id = 1").fetchone()
        if row is None:
            return Activation(
                0,
                baseline.profile_id,
                baseline.fingerprint,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            )
        values = dict(row)
        del values["id"]
        return Activation(**values)

    def activate(
        self, expected_revision: int, choice: Choice, previous: Choice | None, by: str
    ) -> int:
        """Make ``choice`` active and ``previous`` the last good model, only if the revision
        is still ``expected_revision``. Returns the new revision."""

        values = (
            choice.profile_id,
            choice.fingerprint,
            choice.qualification_id,
            choice.prompt_limit,
            previous.profile_id if previous else None,
            previous.fingerprint if previous else None,
            previous.qualification_id if previous else None,
            previous.prompt_limit if previous else None,
            now(),
            by,
        )
        with self._write() as db:
            row = db.execute("SELECT revision FROM activation WHERE id = 1").fetchone()
            current = int(row["revision"]) if row else 0
            if current != expected_revision:
                raise RevisionConflict
            if row is None:
                db.execute(
                    "INSERT INTO activation (id, revision, active_profile_id, active_fingerprint,"
                    " active_qualification_id, active_prompt_limit, last_good_profile_id,"
                    " last_good_fingerprint, last_good_qualification_id, last_good_prompt_limit,"
                    " changed_at, changed_by) VALUES (1, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    values,
                )
            else:
                db.execute(
                    "UPDATE activation SET revision = revision + 1, active_profile_id = ?,"
                    " active_fingerprint = ?, active_qualification_id = ?,"
                    " active_prompt_limit = ?, last_good_profile_id = ?,"
                    " last_good_fingerprint = ?, last_good_qualification_id = ?,"
                    " last_good_prompt_limit = ?, changed_at = ?, changed_by = ?"
                    " WHERE id = 1 AND revision = ?",
                    (*values, expected_revision),
                )
        return expected_revision + 1

    # --- audit -----------------------------------------------------------------------------

    def record(
        self,
        *,
        actor: str,
        role: str | None,
        action: str,
        outcome: str,
        profile_id: str | None = None,
        fingerprint: str | None = None,
        code: str | None = None,
        revision: int | None = None,
    ) -> None:
        with self._write() as db:
            db.execute(
                "INSERT INTO events (at, actor, role, action, profile_id, fingerprint, outcome,"
                " code, revision) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    now(),
                    actor,
                    role,
                    action,
                    profile_id,
                    fingerprint[:12] if fingerprint else None,
                    outcome,
                    code,
                    revision,
                ),
            )
            db.execute(
                "DELETE FROM events WHERE seq <= (SELECT MAX(seq) FROM events) - ?",
                (MAX_EVENTS,),
            )

    def events(self, limit: int) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM events ORDER BY seq DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    # --- connection tests ------------------------------------------------------------------

    def save_connection_test(
        self,
        profile_id: str,
        fingerprint: str,
        by: str,
        outcome: str,
        code: str | None,
        summary: dict[str, Any],
    ) -> None:
        with self._write() as db:
            db.execute(
                "INSERT OR REPLACE INTO connection_tests (profile_id, fingerprint, at, by_user,"
                " outcome, code, summary) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (profile_id, fingerprint, now(), by, outcome, code, json.dumps(summary)),
            )

    def connection_test(self, profile_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM connection_tests WHERE profile_id = ?", (profile_id,)
            ).fetchone()
        if row is None:
            return None
        values = dict(row)
        return {**values, **json.loads(values.pop("summary"))}

    # --- qualifications --------------------------------------------------------------------

    def begin_qualification(
        self, profile_id: str, fingerprint: str, basis: str, by: str, total_turns: int
    ) -> str:
        stale = (datetime.now(UTC) - timedelta(seconds=STALE_SECONDS)).isoformat(timespec="seconds")
        qualification_id = uuid4().hex
        with self._write() as db:
            db.execute(
                "UPDATE qualifications SET status = 'error', code = 'STALE', finished_at = ?"
                " WHERE status = 'running' AND heartbeat_at < ?",
                (now(), stale),
            )
            if db.execute("SELECT 1 FROM qualifications WHERE status = 'running'").fetchone():
                raise QualificationBusy
            db.execute(
                "INSERT INTO qualifications (qualification_id, profile_id, fingerprint, basis,"
                " status, started_at, started_by, heartbeat_at, total_turns)"
                " VALUES (?, ?, ?, ?, 'running', ?, ?, ?, ?)",
                (qualification_id, profile_id, fingerprint, basis, now(), by, now(), total_turns),
            )
        return qualification_id

    def heartbeat(
        self, qualification_id: str, done_turns: int, *, total_turns: int | None = None
    ) -> bool:
        """Refresh the run; False when it must stop (cancel requested or no longer running)."""

        with self._write() as db:
            db.execute(
                "UPDATE qualifications SET heartbeat_at = ?, done_turns = ?,"
                " total_turns = COALESCE(?, total_turns)"
                " WHERE qualification_id = ? AND status = 'running'",
                (now(), done_turns, total_turns, qualification_id),
            )
            row = db.execute(
                "SELECT status, cancel_requested FROM qualifications WHERE qualification_id = ?",
                (qualification_id,),
            ).fetchone()
        return bool(row) and row["status"] == "running" and not row["cancel_requested"]

    def request_cancel(self, qualification_id: str) -> bool:
        with self._write() as db:
            changed = db.execute(
                "UPDATE qualifications SET cancel_requested = 1"
                " WHERE qualification_id = ? AND status = 'running'",
                (qualification_id,),
            ).rowcount
        return changed == 1

    def finish_qualification(
        self, qualification_id: str, status: str, code: str | None, summary: dict[str, Any] | None
    ) -> None:
        if status not in QUALIFICATION_STATES - {"running"}:
            raise ValueError("unknown qualification status")
        with self._write() as db:
            db.execute(
                "UPDATE qualifications SET status = ?, code = ?, finished_at = ?, summary = ?"
                " WHERE qualification_id = ? AND status = 'running'",
                (status, code, now(), json.dumps(summary) if summary else None, qualification_id),
            )

    def qualification(self, qualification_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM qualifications WHERE qualification_id = ?", (qualification_id,)
            ).fetchone()
        return _qualification(row) if row else None

    def latest_qualification(self, profile_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM qualifications WHERE profile_id = ?"
                " ORDER BY started_at DESC, rowid DESC LIMIT 1",
                (profile_id,),
            ).fetchone()
        return _qualification(row) if row else None

    def running_qualification(self) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM qualifications WHERE status = 'running' LIMIT 1"
            ).fetchone()
        return _qualification(row) if row else None


def _qualification(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["cancel_requested"] = bool(item["cancel_requested"])
    item["summary"] = json.loads(item["summary"]) if item["summary"] else None
    return item
