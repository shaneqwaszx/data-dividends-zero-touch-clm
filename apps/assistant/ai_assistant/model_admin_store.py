"""Model management state (D-093): which model is active, the last one that worked, test and
qualification results, and the audit history. Local SQLite under apps/assistant/data (not in
Git), separate from the knowledge store and the budget ledger.

The activation is one row changed only by compare-and-set on its revision, so two
administrators (or two service processes) can never both apply a change made from the same
view. Audit rows are content-free: who, what, which profile, the outcome and a closed code;
never a URL, a credential, a prompt, an answer or case data. Retention is by class, so one
class can never push another out: model changes (an activation, rollback or revert that was
applied) are always kept; refused access by callers without the capability keeps its newest
``MAX_REFUSED_EVENTS``; all other activity its newest ``MAX_EVENTS``.

Only one qualification may run at a time across every process sharing the database: a run
holds the ``running`` row and refreshes its heartbeat; a run whose heartbeat is older than
``STALE_SECONDS`` is closed as an error before another may start. The service refreshes the
heartbeat while it supervises the process; the process refreshes it between steps.

D-098: the supervising service also stamps ``supervised_at`` every second. A running row whose
stamp is older than ``SUPERVISOR_STALE_SECONDS`` has lost its supervisor (the service stopped
or restarted): the service closes it as interrupted and never starts it again. A process that
is still alive sees its row closed at its next heartbeat and stops; the ledger, not this row,
accounts for any paid call it had open.

HR spending controls (D-096): the remote model's daily allowance and its call limit per
activation, as an HR administrator set them. One row, changed only by compare-and-set on its
own revision; until it exists the environment settings apply. Its CHECKs repeat the
hard bounds (1 to 200 calls; D-098: the daily allowance has no US$1 ceiling, only the
ledger's technical bound), so no writer can store more.

Claude's HR spending controls (D-102, proposed): the same shape in their own row and table,
never shared with GPT-OSS's, within D-099's policy limits (US$0.000001 to US$5.00 a day and
1 to 20 calls per activation; the CHECKs repeat them).
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

from .config import AiAssistantSettings

MAX_EVENTS = 5000
MAX_REFUSED_EVENTS = 1000
# Longer than the longest step without a heartbeat from the process (the connection test's
# three calls at the 600-second maximum model timeout), plus a margin.
STALE_SECONDS = 2100
# D-098: a supervisor stamps its run every second; this long without a stamp means none is left.
SUPERVISOR_STALE_SECONDS = 30
# Outcomes of an applied model change: never pruned.
CHANGE_OUTCOMES = ("applied", "reverted")

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
# D-098: no US$1 daily ceiling; the bound is the ledger's technical MAX_MICRO_USD (10**12).
_SPENDING_CONTROLS = """
CREATE TABLE IF NOT EXISTS {name} (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    revision INTEGER NOT NULL CHECK (revision >= 1),
    daily_cap_micro_usd INTEGER NOT NULL
        CHECK (daily_cap_micro_usd BETWEEN 0 AND 1000000000000),
    max_calls INTEGER NOT NULL CHECK (max_calls BETWEEN 1 AND 200),
    changed_at TEXT NOT NULL,
    changed_by TEXT NOT NULL
);
"""
# D-102: Claude's own controls (anthropic_runtime.DAILY_CEILING_MICRO_USD, MAX_CALLS_CEILING).
_CLAUDE_SPENDING_CONTROLS = """
CREATE TABLE IF NOT EXISTS claude_spending_controls (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    revision INTEGER NOT NULL CHECK (revision >= 1),
    daily_cap_micro_usd INTEGER NOT NULL CHECK (daily_cap_micro_usd BETWEEN 1 AND 5000000),
    max_calls INTEGER NOT NULL CHECK (max_calls BETWEEN 1 AND 20),
    changed_at TEXT NOT NULL,
    changed_by TEXT NOT NULL
);
"""
# The D-096 table's daily CHECK, which an existing database still has until it is upgraded.
_D096_DAILY_CHECK = "BETWEEN 0 AND 1000000)"

QUALIFICATION_STATES = frozenset({"running", "passed", "failed", "cancelled", "error"})
# The hard bounds of the HR spending controls (the table's CHECKs say the same). D-098: the
# daily bound is only technical (budget.MAX_MICRO_USD); US$1.00 is the default, not a ceiling.
DAILY_CAP_MAX_MICRO_USD = 10**12
MAX_CALLS_RANGE = (1, 200)
# D-102: Claude's bounds (the D-099 policy ceilings; a test keeps them equal to the runtime's).
CLAUDE_DAILY_CAP_RANGE = (1, 5_000_000)
CLAUDE_MAX_CALLS_RANGE = (1, 20)


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
class SpendingControls:
    """The HR spending controls as stored (revision 0: never set, the environment applies)."""

    revision: int
    daily_cap_micro_usd: int | None
    max_calls: int | None
    changed_at: str | None
    changed_by: str | None


def valid_controls(daily_cap_micro_usd: object, max_calls: object) -> bool:
    low, high = MAX_CALLS_RANGE
    return (
        type(daily_cap_micro_usd) is int
        and 0 <= daily_cap_micro_usd <= DAILY_CAP_MAX_MICRO_USD
        and type(max_calls) is int
        and low <= max_calls <= high
    )


def apply_controls(
    settings: AiAssistantSettings, controls: SpendingControls | None, *, calls: bool = True
) -> AiAssistantSettings:
    """The settings with the HR spending controls in place of the environment defaults.
    ``None`` (the controls could not be read) fails closed: no daily allowance."""

    if controls is None:
        return settings.model_copy(update={"budget_daily_cap_micro_usd": 0})
    update: dict[str, int] = {}
    if controls.daily_cap_micro_usd is not None:
        update["budget_daily_cap_micro_usd"] = controls.daily_cap_micro_usd
    if calls and controls.max_calls is not None:
        update["local_api_test_max_calls"] = controls.max_calls
    return settings.model_copy(update=update) if update else settings


def valid_claude_controls(daily_cap_micro_usd: object, max_calls: object) -> bool:
    low_cap, high_cap = CLAUDE_DAILY_CAP_RANGE
    low, high = CLAUDE_MAX_CALLS_RANGE
    return (
        type(daily_cap_micro_usd) is int
        and low_cap <= daily_cap_micro_usd <= high_cap
        and type(max_calls) is int
        and low <= max_calls <= high
    )


def apply_claude_controls(
    settings: AiAssistantSettings, controls: SpendingControls | None, *, calls: bool = True
) -> AiAssistantSettings:
    """D-102: the settings with Claude's HR controls in place of the environment defaults.
    ``None`` (unreadable) fails closed: a daily allowance of 0, which Claude's readiness
    refuses, so no Claude call is made until the controls can be read."""

    if controls is None:
        return settings.model_copy(update={"anthropic_daily_cap_micro_usd": 0})
    update: dict[str, int] = {}
    if controls.daily_cap_micro_usd is not None:
        update["anthropic_daily_cap_micro_usd"] = controls.daily_cap_micro_usd
    if calls and controls.max_calls is not None:
        update["anthropic_max_calls"] = controls.max_calls
    return settings.model_copy(update=update) if update else settings


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
            db.executescript(
                _SCHEMA
                + _SPENDING_CONTROLS.format(name="spending_controls")
                + _CLAUDE_SPENDING_CONTROLS
            )
        self._upgrade()

    def _upgrade(self) -> None:
        """D-098 changes to a database an earlier version made (each applied once, in one
        transaction, keeping every row): the supervisor stamp on qualifications, and the
        spending controls table without the US$1 daily CHECK (SQLite cannot alter a CHECK,
        so the one row is copied as it is into the new table, then the old one is dropped)."""

        with self._write() as db:
            columns = {row["name"] for row in db.execute("PRAGMA table_info(qualifications)")}
            if "supervised_at" not in columns:
                db.execute("ALTER TABLE qualifications ADD COLUMN supervised_at TEXT")
            row = db.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'spending_controls'"
            ).fetchone()
            if row is not None and _D096_DAILY_CHECK in str(row["sql"]):
                db.execute(_SPENDING_CONTROLS.format(name="spending_controls_d098"))
                db.execute(
                    "INSERT INTO spending_controls_d098 (id, revision, daily_cap_micro_usd,"
                    " max_calls, changed_at, changed_by) SELECT id, revision,"
                    " daily_cap_micro_usd, max_calls, changed_at, changed_by"
                    " FROM spending_controls"
                )
                db.execute("DROP TABLE spending_controls")
                db.execute("ALTER TABLE spending_controls_d098 RENAME TO spending_controls")

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

    # --- HR spending controls (D-096) -------------------------------------------------------

    def spending_controls(self) -> SpendingControls:
        return self._controls("spending_controls")

    def claude_spending_controls(self) -> SpendingControls:
        """D-102: Claude's own row (revision 0: never set, the environment applies)."""

        return self._controls("claude_spending_controls")

    def _controls(self, table: str) -> SpendingControls:
        with self._connect() as db:
            row = db.execute(f"SELECT * FROM {table} WHERE id = 1").fetchone()  # noqa: S608
        if row is None:
            return SpendingControls(0, None, None, None, None)
        return SpendingControls(
            revision=int(row["revision"]),
            daily_cap_micro_usd=int(row["daily_cap_micro_usd"]),
            max_calls=int(row["max_calls"]),
            changed_at=row["changed_at"],
            changed_by=row["changed_by"],
        )

    def set_spending_controls(
        self, expected_revision: int, daily_cap_micro_usd: int, max_calls: int, by: str
    ) -> int:
        """Store both controls only if the revision is still ``expected_revision`` (0 when
        never set). Returns the new revision. Nothing else (spend, calls) is touched."""

        if not valid_controls(daily_cap_micro_usd, max_calls):
            raise ValueError("spending controls out of range")
        return self._set_controls(
            "spending_controls", expected_revision, daily_cap_micro_usd, max_calls, by
        )

    def set_claude_spending_controls(
        self, expected_revision: int, daily_cap_micro_usd: int, max_calls: int, by: str
    ) -> int:
        """D-102: Claude's controls, compare-and-set on their own revision, as above."""

        if not valid_claude_controls(daily_cap_micro_usd, max_calls):
            raise ValueError("Claude spending controls out of range")
        return self._set_controls(
            "claude_spending_controls", expected_revision, daily_cap_micro_usd, max_calls, by
        )

    def _set_controls(
        self, table: str, expected_revision: int, daily_cap_micro_usd: int, max_calls: int, by: str
    ) -> int:
        # ``table`` is one of the two names above, never caller input.
        with self._write() as db:
            row = db.execute(f"SELECT revision FROM {table} WHERE id = 1").fetchone()  # noqa: S608
            current = int(row["revision"]) if row else 0
            if current != expected_revision:
                raise RevisionConflict
            if row is None:
                db.execute(
                    f"INSERT INTO {table} (id, revision, daily_cap_micro_usd, max_calls,"  # noqa: S608
                    " changed_at, changed_by) VALUES (1, 1, ?, ?, ?, ?)",
                    (daily_cap_micro_usd, max_calls, now(), by),
                )
            else:
                db.execute(
                    f"UPDATE {table} SET revision = revision + 1,"  # noqa: S608
                    " daily_cap_micro_usd = ?, max_calls = ?, changed_at = ?, changed_by = ?"
                    " WHERE id = 1 AND revision = ?",
                    (daily_cap_micro_usd, max_calls, now(), by, expected_revision),
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
            if outcome in CHANGE_OUTCOMES:
                return
            # Each class is trimmed only within itself.
            refused = action == "ACCESS_REFUSED"
            kind = (
                "action = 'ACCESS_REFUSED'"
                if refused
                else "action != 'ACCESS_REFUSED' AND outcome NOT IN ('applied', 'reverted')"
            )
            db.execute(
                f"DELETE FROM events WHERE {kind} AND seq NOT IN"  # noqa: S608 (fixed text)
                f" (SELECT seq FROM events WHERE {kind} ORDER BY seq DESC LIMIT ?)",
                (MAX_REFUSED_EVENTS if refused else MAX_EVENTS,),
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

    def touch(self, qualification_id: str) -> None:
        """The service's supervisor: the process is still alive."""

        with self._write() as db:
            stamp = now()
            db.execute(
                "UPDATE qualifications SET heartbeat_at = ?, supervised_at = ?"
                " WHERE qualification_id = ? AND status = 'running'",
                (stamp, stamp, qualification_id),
            )

    def unsupervised(self, grace_seconds: float = SUPERVISOR_STALE_SECONDS) -> list[str]:
        """Running runs with no supervisor stamp (or none since they started) for longer than
        ``grace_seconds``: their supervising service has gone."""

        cutoff = (datetime.now(UTC) - timedelta(seconds=grace_seconds)).isoformat(
            timespec="seconds"
        )
        with self._connect() as db:
            rows = db.execute(
                "SELECT qualification_id FROM qualifications WHERE status = 'running'"
                " AND COALESCE(supervised_at, started_at) < ?",
                (cutoff,),
            ).fetchall()
        return [row["qualification_id"] for row in rows]

    def finished_qualifications(self) -> int:
        """How many runs have finished (any outcome): it grows whenever a run ends, in any
        process, so the active model's eligibility is checked again (D-098 decision 6a)."""

        with self._connect() as db:
            row = db.execute(
                "SELECT COUNT(*) AS n FROM qualifications WHERE status != 'running'"
            ).fetchone()
        return int(row["n"])

    def qualifications_for(self, profile_id: str) -> list[dict[str, Any]]:
        """Every run of one profile, newest first (D-098 eligibility reads them in order)."""

        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM qualifications WHERE profile_id = ?"
                " ORDER BY started_at DESC, rowid DESC",
                (profile_id,),
            ).fetchall()
        return [_qualification(row) for row in rows]

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
