"""SQLite store: every version of every entry, every review decision, the keyword index,
and the to-do list that keeps the vector index in step.

Rules enforced here, in one transaction per change:

- a new version never overwrites an old one (versions are append-only). A reviewer's edit
  is stored as a new version written by that reviewer; the version it revises is kept,
  unchanged, and taken out of review;
- only a reviewer who wrote no version in the chain being decided can approve or reject it
  (maker-checker), and only the exact content they were shown (content hash);
- an entry may only replace an entry of the same kind (a past resolution never retires
  official guidance);
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

SCHEMA_VERSION = 3

_ENTRY_COLUMNS = (
    "entry_id, version, kind, status, title, body, blocker_codes, fields, stages, visibility, "
    "follow_ups, effective_from, replaces, author, approver, approved_at, source_ref, "
    "illustrative, content_hash, created_at, revises"
)

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
    revises INTEGER,
    PRIMARY KEY (entry_id, version)
);
CREATE UNIQUE INDEX IF NOT EXISTS one_current_version
    ON entries (entry_id) WHERE status = 'approved';
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    reviewer TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('approve', 'reject', 'retire', 'edit')),
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (entry_id, version) REFERENCES entries (entry_id, version)
);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT,
    team TEXT,
    helpful INTEGER NOT NULL,
    note TEXT NOT NULL,
    blocker_codes TEXT NOT NULL,
    fields TEXT NOT NULL,
    stages TEXT NOT NULL,
    entry_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('open', 'drafted', 'closed')),
    created_at TEXT NOT NULL,
    closed_by TEXT,
    closed_at TEXT
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
    """Someone who wrote or edited an entry tried to approve or reject it."""


class ContentChangedError(KnowledgeError):
    """The version was decided against content other than what it now says."""


class KnowledgeRuleError(KnowledgeError):
    """A change the knowledge rules never allow (not a stale or concurrent request)."""


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
        revises=row["revises"],
    )


_FTS_TOKEN = re.compile(r"[A-Za-z0-9_]+")
# Words too common to say anything about which entry applies.
_STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "but",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "doing",
        "for",
        "from",
        "had",
        "has",
        "have",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "me",
        "my",
        "of",
        "on",
        "or",
        "our",
        "should",
        "so",
        "than",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "to",
        "too",
        "us",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
        "about",
        "after",
        "again",
        "also",
        "any",
        "because",
        "before",
        "being",
        "both",
        "each",
        "few",
        "more",
        "most",
        "no",
        "not",
        "now",
        "only",
        "other",
        "out",
        "over",
        "same",
        "some",
        "such",
        "very",
        "just",
        "get",
        "got",
        "need",
        "needs",
        "one",
    ]
)


def _narrows(old: tuple[str, ...], new: tuple[str, ...]) -> bool:
    """True when ``new`` team visibility is the same as ``old`` or a subset of it.

    No teams means every team, so an edit may restrict it but never empty a restricted list.
    """

    if not old:
        return True
    return bool(new) and set(new) <= set(old)


def _fts_query(text: str) -> str | None:
    """A safe FTS5 query: any of the words, each quoted (no operators from user text)."""

    tokens = [t for t in _FTS_TOKEN.findall(text) if len(t) > 1 and t.lower() not in _STOPWORDS]
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
            existing = db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'meta'"
            ).fetchone()
            version = (
                db.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
                if existing
                else None
            )
            if version is not None and int(version[0]) < 2:
                self._migrate_to_2(db)
            if version is not None and int(version[0]) < 3:
                self._migrate_to_3(db)
            db.executescript(_SCHEMA)
            db.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
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

    def get_by_key(self, key: str) -> Entry | None:
        """The exact version a search hit points at (``entry_id@vN``)."""

        entry_id, sep, version = key.rpartition("@v")
        if not sep or not version.isdigit():
            return None
        return self.get(entry_id, int(version))

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
            self._check_replaces(db, entry)
            latest = db.execute(
                "SELECT MAX(version) FROM entries WHERE entry_id = ?", (entry.entry_id,)
            ).fetchone()[0]
            stored = entry.with_changes(
                version=(latest or 0) + 1,
                status=status,
                approver=None,
                approved_at=None,
                created_at=self._clock(),
                revises=None,
            )
            self._insert(db, stored)
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
        self,
        entry_id: str,
        version: int,
        *,
        reviewer: str,
        approve: bool,
        notes: str = "",
        expected_hash: str | None = None,
    ) -> Entry:
        """Approve or reject a pending version.

        Nobody who wrote this version, or a version it was revised from, can decide it. When
        ``expected_hash`` is given (always, from the review API) the decision applies only if
        the version still says exactly what the reviewer was shown.
        """

        now = self._clock()
        with self._connect() as db:
            entry = self._require(db, entry_id, version)
            if entry.status != EntryStatus.PENDING_REVIEW:
                raise KnowledgeError("only a version pending review can be decided")
            if expected_hash is not None and expected_hash != entry.content_hash():
                raise ContentChangedError("the version no longer says what was reviewed")
            if not reviewer or reviewer in self._chain_authors(db, entry):
                raise MakerCheckerError("an author or editor of an entry cannot decide it")
            self._check_replaces(db, entry)
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

    def revise_pending(
        self,
        entry_id: str,
        version: int,
        *,
        editor: str,
        expected_hash: str | None = None,
        **changes: Any,
    ) -> Entry:
        """A reviewer tidies a pending version (wording, redaction, follow-ups, visibility,
        what it replaces) before it is decided.

        The edit is a new pending version written by the editor; the version it revises is
        kept unchanged (retired from review, with an 'edit' row in its history). The editor,
        like the original author, can then not decide it: a different reviewer must.
        Team visibility can only be narrowed by an edit, never widened.
        """

        if not editor:
            raise KnowledgeError("an edit needs an editor")
        allowed = {
            "title",
            "body",
            "blocker_codes",
            "fields",
            "stages",
            "follow_ups",
            "visibility",
            "replaces",
        }
        unknown = set(changes) - allowed
        if unknown:
            raise KnowledgeError(f"cannot change {sorted(unknown)}")
        now = self._clock()
        with self._connect() as db:
            entry = self._require(db, entry_id, version)
            if entry.status != EntryStatus.PENDING_REVIEW:
                raise KnowledgeError("only a version pending review can be edited")
            if expected_hash is not None and expected_hash != entry.content_hash():
                raise ContentChangedError("the version no longer says what was reviewed")
            new_visibility = changes.get("visibility")
            if isinstance(new_visibility, Visibility) and not _narrows(
                entry.visibility.teams, new_visibility.teams
            ):
                raise KnowledgeRuleError("an edit can only narrow which teams see an entry")
            latest = db.execute(
                "SELECT MAX(version) FROM entries WHERE entry_id = ?", (entry_id,)
            ).fetchone()[0]
            revised = entry.with_changes(
                **changes,
                version=int(latest) + 1,
                status=EntryStatus.PENDING_REVIEW,
                author=editor,
                approver=None,
                approved_at=None,
                created_at=now,
                revises=entry.version,
            )
            self._check_replaces(db, revised)
            self._insert(db, revised)
            db.execute(
                "UPDATE entries SET status = 'retired' WHERE entry_id = ? AND version = ?",
                (entry_id, version),
            )
            db.execute(
                "INSERT INTO reviews (entry_id, version, reviewer, decision, notes, created_at) "
                "VALUES (?, ?, ?, 'edit', ?, ?)",
                (
                    entry_id,
                    version,
                    editor,
                    f"revised as v{revised.version}: " + ", ".join(sorted(changes)),
                    now,
                ),
            )
        return revised

    # --- feedback ---------------------------------------------------------------------

    def add_feedback(
        self,
        *,
        case_id: str,
        user_id: str,
        role: str | None,
        team: str | None,
        helpful: bool,
        note: str,
        blocker_codes: tuple[str, ...],
        fields: tuple[str, ...],
        stages: tuple[str, ...],
        entry_id: str | None,
    ) -> int:
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO feedback (case_id, user_id, role, team, helpful, note, "
                "blocker_codes, fields, stages, entry_id, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    case_id,
                    user_id,
                    role,
                    team,
                    int(helpful),
                    note,
                    json.dumps(list(blocker_codes)),
                    json.dumps(list(fields)),
                    json.dumps(list(stages)),
                    entry_id,
                    "drafted" if entry_id else "open",
                    self._clock(),
                ),
            )
            return int(cursor.lastrowid or 0)

    def feedback(self, *, status: str | None = None) -> list[dict[str, Any]]:
        sql, args = "SELECT * FROM feedback", []
        if status is not None:
            sql += " WHERE status = ?"
            args.append(status)
        with self._connect() as db:
            rows = db.execute(sql + " ORDER BY id", args).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["helpful"] = bool(item["helpful"])
            for key in ("blocker_codes", "fields", "stages"):
                item[key] = json.loads(item[key])
            out.append(item)
        return out

    def close_feedback(self, feedback_id: int, *, by: str) -> None:
        with self._connect() as db:
            updated = db.execute(
                "UPDATE feedback SET status = 'closed', closed_by = ?, closed_at = ? "
                "WHERE id = ? AND status != 'closed'",
                (by, self._clock(), feedback_id),
            ).rowcount
        if not updated:
            raise KnowledgeError("no such open feedback")

    # --- internals ------------------------------------------------------------------

    @staticmethod
    def _migrate_to_2(db: sqlite3.Connection) -> None:
        """Version 1 did not allow 'edit' review rows: rebuild the reviews table."""

        db.executescript(
            """
            ALTER TABLE reviews RENAME TO reviews_v1;
            CREATE TABLE reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                reviewer TEXT NOT NULL,
                decision TEXT NOT NULL
                    CHECK (decision IN ('approve', 'reject', 'retire', 'edit')),
                notes TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (entry_id, version) REFERENCES entries (entry_id, version)
            );
            INSERT INTO reviews SELECT * FROM reviews_v1;
            DROP TABLE reviews_v1;
            """
        )

    @staticmethod
    def _migrate_to_3(db: sqlite3.Connection) -> None:
        """Version 3 records which version a reviewer's edit revises."""

        columns = {row[1] for row in db.execute("PRAGMA table_info(entries)")}
        if "revises" not in columns:
            db.execute("ALTER TABLE entries ADD COLUMN revises INTEGER")

    def _insert(self, db: sqlite3.Connection, entry: Entry) -> None:
        db.execute(
            f"INSERT INTO entries ({_ENTRY_COLUMNS}) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entry.entry_id,
                entry.version,
                entry.kind.value,
                entry.status.value,
                entry.title,
                entry.body,
                json.dumps(list(entry.blocker_codes)),
                json.dumps(list(entry.fields)),
                json.dumps(list(entry.stages)),
                entry.visibility.to_json(),
                json.dumps(list(entry.follow_ups)),
                entry.effective_from,
                entry.replaces,
                entry.author,
                None,
                None,
                entry.source_ref,
                int(entry.illustrative),
                entry.content_hash(),
                entry.created_at,
                entry.revises,
            ),
        )

    def _check_replaces(self, db: sqlite3.Connection, entry: Entry) -> None:
        if entry.replaces is None:
            return
        if entry.replaces == entry.entry_id:
            raise KnowledgeRuleError("an entry cannot replace itself")
        target = db.execute(
            "SELECT kind FROM entries WHERE entry_id = ? LIMIT 1", (entry.replaces,)
        ).fetchone()
        if target is not None and target["kind"] != entry.kind.value:
            raise KnowledgeRuleError("an entry can only replace an entry of the same kind")

    def _chain_authors(self, db: sqlite3.Connection, entry: Entry) -> set[str]:
        """Everyone who wrote ``entry`` or a version it was revised from."""

        authors = {entry.author}
        revises, seen = entry.revises, {entry.version}
        while revises is not None and revises not in seen:
            seen.add(revises)
            row = db.execute(
                "SELECT author, revises FROM entries WHERE entry_id = ? AND version = ?",
                (entry.entry_id, revises),
            ).fetchone()
            if row is None:
                break
            authors.add(row["author"])
            revises = row["revises"]
        return authors

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
