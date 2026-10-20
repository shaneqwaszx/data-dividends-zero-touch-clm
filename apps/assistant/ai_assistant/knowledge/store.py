"""SQLite store: every version of every entry, every review decision, the keyword index,
and the to-do list that keeps the vector index in step.

Rules enforced here, in one transaction per change:

- a new version never overwrites an old one (versions are append-only);
- only a reviewer who is not the author can approve or reject (maker-checker);
- approving a version retires the entry's previous approved version, and the entry it
  replaces, so at most one version of an entry is current;
- only current approved versions are in the keyword index;
- every approve/retire leaves a vector-index task, done (or retried) by the service.
"""

import json
import re
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import Entry, EntryKind, EntryStatus, Visibility

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS entries (
    entry_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('guidance', 'resolution')),
    status TEXT NOT NULL
        CHECK (status IN ('draft', 'pending_review', 'approved', 'rejected', 'retired')),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    blocker_codes TEXT NOT NULL,
    fields TEXT NOT NULL,
    stages TEXT NOT NULL,
    visibility TEXT NOT NULL,
    follow_ups TEXT NOT NULL,
    effective_from TEXT,
    replaces TEXT,
    author TEXT NOT NULL,
    approver TEXT,
    approved_at TEXT,
    source_ref TEXT,
    illustrative INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (entry_id, version)
);
CREATE UNIQUE INDEX IF NOT EXISTS one_current_version
    ON entries (entry_id) WHERE status = 'approved';
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    reviewer TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('approve', 'reject', 'retire')),
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (entry_id, version) REFERENCES entries (entry_id, version)
);
CREATE VIRTUAL TABLE IF NOT EXISTS entry_text
    USING fts5 (key UNINDEXED, kind UNINDEXED, title, body, codes);
CREATE TABLE IF NOT EXISTS index_tasks (
    key TEXT PRIMARY KEY,
    entry_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    kind TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('upsert', 'remove')),
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    updated_at TEXT NOT NULL
);
"""


class KnowledgeError(Exception):
    """A change the knowledge rules do not allow."""


class MakerCheckerError(KnowledgeError):
    """The author of an entry tried to approve or reject it."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _row_to_entry(row: sqlite3.Row) -> Entry:
    return Entry(
        entry_id=row["entry_id"],
        version=row["version"],
        kind=EntryKind(row["kind"]),
        status=EntryStatus(row["status"]),
        title=row["title"],
        body=row["body"],
        blocker_codes=tuple(json.loads(row["blocker_codes"])),
        fields=tuple(json.loads(row["fields"])),
        stages=tuple(json.loads(row["stages"])),
        visibility=Visibility.from_json(row["visibility"]),
        follow_ups=tuple(json.loads(row["follow_ups"])),
        effective_from=row["effective_from"],
        replaces=row["replaces"],
        author=row["author"],
        approver=row["approver"],
        approved_at=row["approved_at"],
        source_ref=row["source_ref"],
        illustrative=bool(row["illustrative"]),
        created_at=row["created_at"],
    )


_FTS_TOKEN = re.compile(r"[A-Za-z0-9_]+")


def _fts_query(text: str) -> str | None:
    """A safe FTS5 query: any of the words, each quoted (no operators from user text)."""

    tokens = [t for t in _FTS_TOKEN.findall(text) if len(t) > 1]
    if not tokens:
        return None
    return " OR ".join(f'"{token}"' for token in dict.fromkeys(tokens))


class KnowledgeStore:
    def __init__(self, path: Path | str, *, clock: Callable[[], str] = _now) -> None:
        self._path = str(path)
        self._clock = clock
        if self._path != ":memory:":
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(_SCHEMA)
            db.execute(
                "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self._path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            with db:  # one transaction: commit on success, roll back on error
                yield db
        finally:
            db.close()

    # --- reading --------------------------------------------------------------------

    def get(self, entry_id: str, version: int | None = None) -> Entry | None:
        with self._connect() as db:
            if version is None:
                row = db.execute(
                    "SELECT * FROM entries WHERE entry_id = ? ORDER BY version DESC LIMIT 1",
                    (entry_id,),
                ).fetchone()
            else:
                row = db.execute(
                    "SELECT * FROM entries WHERE entry_id = ? AND version = ?",
                    (entry_id, version),
                ).fetchone()
        return _row_to_entry(row) if row else None

    def current(self, entry_id: str) -> Entry | None:
        """The approved version of an entry, if any."""

        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM entries WHERE entry_id = ? AND status = 'approved'", (entry_id,)
            ).fetchone()
        return _row_to_entry(row) if row else None

    def versions(self, entry_id: str) -> list[Entry]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM entries WHERE entry_id = ? ORDER BY version", (entry_id,)
            ).fetchall()
        return [_row_to_entry(row) for row in rows]

    def entries(
        self, *, status: EntryStatus | None = None, kind: EntryKind | None = None
    ) -> list[Entry]:
        sql, args = "SELECT * FROM entries WHERE 1 = 1", []
        if status is not None:
            sql += " AND status = ?"
            args.append(status.value)
        if kind is not None:
            sql += " AND kind = ?"
            args.append(kind.value)
        with self._connect() as db:
            rows = db.execute(sql + " ORDER BY entry_id, version", args).fetchall()
        return [_row_to_entry(row) for row in rows]

    def reviews(self, entry_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT entry_id, version, reviewer, decision, notes, created_at "
                "FROM reviews WHERE entry_id = ? ORDER BY id",
                (entry_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def keyword_search(
        self, text: str, *, kinds: tuple[EntryKind, ...] | None = None, limit: int = 20
    ) -> list[tuple[str, float]]:
        """Current approved versions matching any word of ``text``, best first.

        Returns (version key, score) pairs; a higher score is a better match.
        """

        query = _fts_query(text)
        if query is None:
            return []
        sql = "SELECT key, bm25(entry_text) AS rank FROM entry_text WHERE entry_text MATCH ?"
        args: list[Any] = [query]
        if kinds:
            sql += f" AND kind IN ({', '.join('?' for _ in kinds)})"
            args.extend(kind.value for kind in kinds)
        sql += " ORDER BY rank LIMIT ?"
        args.append(limit)
        with self._connect() as db:
            rows = db.execute(sql, args).fetchall()
        # bm25() is lower-is-better (negative); flip it so higher is better.
        return [(row["key"], -float(row["rank"])) for row in rows]

    # --- writing --------------------------------------------------------------------

    def add_version(
        self, entry: Entry, *, status: EntryStatus = EntryStatus.PENDING_REVIEW
    ) -> Entry:
        """Store ``entry`` as the next version of its entry id (never overwrites)."""

        if status not in {EntryStatus.DRAFT, EntryStatus.PENDING_REVIEW}:
            raise KnowledgeError("a new version starts as a draft or pending review")
        if not entry.author:
            raise KnowledgeError("every entry needs an author")
        with self._connect() as db:
            latest = db.execute(
                "SELECT MAX(version) FROM entries WHERE entry_id = ?", (entry.entry_id,)
            ).fetchone()[0]
            stored = entry.with_changes(
                version=(latest or 0) + 1,
                status=status,
                approver=None,
                approved_at=None,
                created_at=self._clock(),
            )
            db.execute(
                "INSERT INTO entries VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    stored.entry_id,
                    stored.version,
                    stored.kind.value,
                    stored.status.value,
                    stored.title,
                    stored.body,
                    json.dumps(list(stored.blocker_codes)),
                    json.dumps(list(stored.fields)),
                    json.dumps(list(stored.stages)),
                    stored.visibility.to_json(),
                    json.dumps(list(stored.follow_ups)),
                    stored.effective_from,
                    stored.replaces,
                    stored.author,
                    None,
                    None,
                    stored.source_ref,
                    int(stored.illustrative),
                    stored.content_hash(),
                    stored.created_at,
                ),
            )
        return stored

    def submit(self, entry_id: str, version: int) -> Entry:
        """Move a draft to pending review."""

        with self._connect() as db:
            entry = self._require(db, entry_id, version)
            if entry.status != EntryStatus.DRAFT:
                raise KnowledgeError("only a draft can be submitted for review")
            db.execute(
                "UPDATE entries SET status = 'pending_review' WHERE entry_id = ? AND version = ?",
                (entry_id, version),
            )
        return entry.with_changes(status=EntryStatus.PENDING_REVIEW)

    def decide(
        self, entry_id: str, version: int, *, reviewer: str, approve: bool, notes: str = ""
    ) -> Entry:
        """Approve or reject a pending version. The author can never decide their own."""

        now = self._clock()
        with self._connect() as db:
            entry = self._require(db, entry_id, version)
            if entry.status != EntryStatus.PENDING_REVIEW:
                raise KnowledgeError("only a version pending review can be decided")
            if not reviewer or reviewer == entry.author:
                raise MakerCheckerError("the author of an entry cannot approve or reject it")
            decision = "approve" if approve else "reject"
            db.execute(
                "INSERT INTO reviews (entry_id, version, reviewer, decision, notes, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (entry_id, version, reviewer, decision, notes, now),
            )
            if not approve:
                db.execute(
                    "UPDATE entries SET status = 'rejected' WHERE entry_id = ? AND version = ?",
                    (entry_id, version),
                )
                return entry.with_changes(status=EntryStatus.REJECTED)
            # Retire what this version supersedes: the entry's own current version and, if
            # set, the current version of the entry it replaces.
            for old_id in {entry_id, entry.replaces} - {None}:
                old = db.execute(
                    "SELECT * FROM entries WHERE entry_id = ? AND status = 'approved'", (old_id,)
                ).fetchone()
                if old is not None:
                    self._retire(db, _row_to_entry(old), by=reviewer, notes="replaced", now=now)
            db.execute(
                "UPDATE entries SET status = 'approved', approver = ?, approved_at = ? "
                "WHERE entry_id = ? AND version = ?",
                (reviewer, now, entry_id, version),
            )
            approved = entry.with_changes(
                status=EntryStatus.APPROVED, approver=reviewer, approved_at=now
            )
            db.execute(
                "INSERT INTO entry_text (key, kind, title, body, codes) VALUES (?, ?, ?, ?, ?)",
                (
                    approved.key,
                    approved.kind.value,
                    approved.title,
                    approved.body,
                    " ".join([*approved.blocker_codes, *approved.fields, *approved.stages]),
                ),
            )
            self._task(db, approved, "upsert", now)
        return approved

    def retire(self, entry_id: str, *, by: str, notes: str) -> Entry | None:
        """Take an entry's current version out of search (revoked, or its rule was removed)."""

        now = self._clock()
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM entries WHERE entry_id = ? AND status = 'approved'", (entry_id,)
            ).fetchone()
            if row is None:
                return None
            entry = _row_to_entry(row)
            self._retire(db, entry, by=by, notes=notes, now=now)
        return entry.with_changes(status=EntryStatus.RETIRED)

    # --- vector-index tasks ---------------------------------------------------------

    def index_tasks(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM index_tasks ORDER BY updated_at, key").fetchall()
        return [dict(row) for row in rows]

    def finish_task(self, key: str) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM index_tasks WHERE key = ?", (key,))

    def fail_task(self, key: str, error: str) -> None:
        with self._connect() as db:
            db.execute(
                "UPDATE index_tasks SET attempts = attempts + 1, last_error = ?, updated_at = ? "
                "WHERE key = ?",
                (error[:200], self._clock(), key),
            )

    def queue_full_reindex(self) -> int:
        """Ask for every current approved version to be (re)indexed."""

        now = self._clock()
        with self._connect() as db:
            rows = db.execute("SELECT * FROM entries WHERE status = 'approved'").fetchall()
            for row in rows:
                self._task(db, _row_to_entry(row), "upsert", now)
        return len(rows)

    # --- internals ------------------------------------------------------------------

    def _require(self, db: sqlite3.Connection, entry_id: str, version: int) -> Entry:
        row = db.execute(
            "SELECT * FROM entries WHERE entry_id = ? AND version = ?", (entry_id, version)
        ).fetchone()
        if row is None:
            raise KnowledgeError("no such entry version")
        return _row_to_entry(row)

    def _retire(
        self, db: sqlite3.Connection, entry: Entry, *, by: str, notes: str, now: str
    ) -> None:
        db.execute(
            "UPDATE entries SET status = 'retired' WHERE entry_id = ? AND version = ?",
            (entry.entry_id, entry.version),
        )
        db.execute(
            "INSERT INTO reviews (entry_id, version, reviewer, decision, notes, created_at) "
            "VALUES (?, ?, ?, 'retire', ?, ?)",
            (entry.entry_id, entry.version, by, notes, now),
        )
        db.execute("DELETE FROM entry_text WHERE key = ?", (entry.key,))
        self._task(db, entry, "remove", now)

    @staticmethod
    def _task(db: sqlite3.Connection, entry: Entry, action: str, now: str) -> None:
        db.execute(
            "INSERT INTO index_tasks (key, entry_id, version, kind, action, attempts, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 0, ?) "
            "ON CONFLICT (key) DO UPDATE SET action = excluded.action, attempts = 0, "
            "last_error = NULL, updated_at = excluded.updated_at",
            (entry.key, entry.entry_id, entry.version, entry.kind.value, action, now),
        )
