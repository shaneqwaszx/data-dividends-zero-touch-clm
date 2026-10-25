"""SQLite store: every version of every entry, every review decision, the keyword index,
and the to-do list that keeps the vector index in step.

Rules enforced here, in one transaction per change:

- a new version never overwrites an old one (versions are append-only). A reviewer's edit
  is stored as a new version written by that reviewer; the version it revises is kept,
  unchanged, and taken out of review;
- only a reviewer who wrote no version in the chain being decided can approve or reject it
  (maker-checker), and only the exact content they were shown (content hash). In the POC's
  single-reviewer mode (D-083, proposed) an author or editor may decide it too, an approval
  only once confirmed, and the review row records it as single-reviewer;
- an entry may only replace an entry of the same kind (a past resolution never retires
  official guidance);
- approving a version retires the entry's previous approved version, and the entry it
  replaces, so at most one version of an entry is current;
- only current approved versions are in the keyword index;
- every approve/retire leaves a vector-index task, done (or retried) by the service;
- an RM's "Not helpful" is an enhancement request: a reviewer writes its fix or closes it
  with a reason, only while it is open. The request is linked to the exact version of the fix
  (``entry_id``, ``entry_version``), and a reviewer's edit moves the link to the new version.
  Approving that version resolves the request; rejecting it opens the request again. A
  decision on any other version of the same entry leaves the request alone;
- an answer record (schema v5, D-084, proposed) is written once and never changed, apart
  from being rated: it may be rated once, by the user who asked, on the same case, before it
  expires, and "Not helpful" links it to the new request. Expired records are deleted:
  unlinked ones some days after the answer, linked ones some days after their request was
  resolved or closed. Every view of a record is logged.
"""

import json
import re
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .models import Entry, EntryKind, EntryStatus, Visibility

SCHEMA_VERSION = 5

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
    single_reviewer INTEGER NOT NULL DEFAULT 0,
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
    status TEXT NOT NULL CHECK (status IN ('open', 'drafted', 'resolved', 'closed')),
    created_at TEXT NOT NULL,
    closed_by TEXT,
    closed_at TEXT,
    close_reason TEXT,
    entry_version INTEGER
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
CREATE TABLE IF NOT EXISTS retire_requests (
    entry_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    requested_by TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (entry_id, version)
);
CREATE TABLE IF NOT EXISTS answer_records (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    team TEXT,
    created_at TEXT NOT NULL,
    question TEXT NOT NULL,
    earlier_answer_ids TEXT NOT NULL,
    case_snapshot TEXT NOT NULL,
    knowledge TEXT NOT NULL,
    allowed_lines TEXT NOT NULL,
    chosen_lines TEXT NOT NULL,
    dropped_lines TEXT NOT NULL,
    result TEXT NOT NULL,
    shown_answer TEXT NOT NULL,
    rated_at TEXT,
    linked_request_id INTEGER REFERENCES feedback (id)
);
CREATE INDEX IF NOT EXISTS answer_records_by_request ON answer_records (linked_request_id);
CREATE TABLE IF NOT EXISTS answer_record_views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL REFERENCES answer_records (id) ON DELETE CASCADE,
    viewer TEXT NOT NULL,
    viewed_at TEXT NOT NULL
);
"""

# The JSON columns of an answer record.
_ANSWER_JSON = (
    "earlier_answer_ids",
    "case_snapshot",
    "knowledge",
    "allowed_lines",
    "chosen_lines",
    "dropped_lines",
    "result",
    "shown_answer",
)

# How long a write waits for another writer to finish before reporting a stale request.
_BUSY_TIMEOUT_SECONDS = 10.0


class KnowledgeError(Exception):
    """A change the knowledge rules do not allow."""


class MakerCheckerError(KnowledgeError):
    """Someone who wrote or edited an entry tried to approve or reject it."""


class SecondReviewerError(MakerCheckerError):
    """The same person tried to both ask for and confirm a retirement."""


class ConfirmationRequiredError(MakerCheckerError):
    """In single-reviewer mode, an author approved their own entry without confirming it."""


class ContentChangedError(KnowledgeError):
    """The version was decided against content other than what it now says, or another
    request changed it first."""


class AnswerNotFoundError(KnowledgeError):
    """No answer record the caller may rate or view (whatever the reason)."""


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


def _answer_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    for key in _ANSWER_JSON:
        item[key] = json.loads(item[key])
    return item


def _days_before(now: str, days: int) -> str:
    """The store-clock timestamp ``days`` before ``now`` (both ISO 8601, same format)."""

    return (datetime.fromisoformat(now) - timedelta(days=days)).isoformat(timespec="seconds")


def _feedback_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["helpful"] = bool(item["helpful"])
    for key in ("blocker_codes", "fields", "stages"):
        item[key] = json.loads(item[key])
    return item


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
            # Also at 4: earlier builds of this branch (never on main) stamped 4 on table
            # shapes without every v4 column; the v4 step only adds what is missing.
            if version is not None and int(version[0]) <= 4:
                self._migrate_to_4(db)
            if version is not None and int(version[0]) == 5:
                self._repair_5(db)
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

    @contextmanager
    def _write(self, authorize: Callable[[], None] | None = None) -> Iterator[sqlite3.Connection]:
        """One change, holding SQLite's write lock from its first read (BEGIN IMMEDIATE).

        A check (status, content hash, maker-checker) and the change it allows therefore
        cannot interleave with another writer: a second, concurrent decision or edit sees the
        first one's result and is refused. A writer that cannot get the lock in time, or a
        constraint broken by a concurrent change, is reported as a stale request (409), never
        as a crash.

        ``authorize`` (the caller's permission check) runs first once the lock is held, before
        any check or change: if it raises, nothing is written and its error is raised as is.
        """

        db = sqlite3.connect(self._path, isolation_level=None, timeout=_BUSY_TIMEOUT_SECONDS)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            try:
                db.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError:
                raise ContentChangedError("the knowledge store is busy") from None
            try:
                if authorize is not None:
                    authorize()
                yield db
            except sqlite3.IntegrityError:
                db.execute("ROLLBACK")
                raise ContentChangedError("a concurrent change came first") from None
            except BaseException:
                db.execute("ROLLBACK")
                raise
            db.execute("COMMIT")
        finally:
            db.close()

    @staticmethod
    def _set_status(
        db: sqlite3.Connection,
        entry: Entry,
        status: str,
        *,
        extra: str = "",
        args: tuple[Any, ...] = (),
    ) -> None:
        """Move a pending version on, but only if it is still pending (compare-and-swap)."""

        changed = db.execute(
            f"UPDATE entries SET status = ?{extra} "
            "WHERE entry_id = ? AND version = ? AND status = 'pending_review'",
            (status, *args, entry.entry_id, entry.version),
        ).rowcount
        if changed != 1:
            raise ContentChangedError("the version was already decided or edited")

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
                "SELECT entry_id, version, reviewer, decision, notes, created_at, single_reviewer "
                "FROM reviews WHERE entry_id = ? ORDER BY id",
                (entry_id,),
            ).fetchall()
        return [{**dict(row), "single_reviewer": bool(row["single_reviewer"])} for row in rows]

    def single_reviewer_approvals(self) -> set[str]:
        """Keys (``entry_id@vN``) of the versions approved by a single reviewer."""

        with self._connect() as db:
            rows = db.execute(
                "SELECT entry_id, version FROM reviews "
                "WHERE decision = 'approve' AND single_reviewer = 1"
            ).fetchall()
        return {f"{row['entry_id']}@v{row['version']}" for row in rows}

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
        self,
        entry: Entry,
        *,
        status: EntryStatus = EntryStatus.PENDING_REVIEW,
        authorize: Callable[[], None] | None = None,
    ) -> Entry:
        """Store ``entry`` as the next version of its entry id (never overwrites)."""

        if status not in {EntryStatus.DRAFT, EntryStatus.PENDING_REVIEW}:
            raise KnowledgeError("a new version starts as a draft or pending review")
        if not entry.author:
            raise KnowledgeError("every entry needs an author")
        with self._write(authorize) as db:
            return self._add_version(db, entry, status)

    def _add_version(self, db: sqlite3.Connection, entry: Entry, status: EntryStatus) -> Entry:
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

        with self._write() as db:
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
        authorize: Callable[[], None] | None = None,
        single_reviewer: bool = False,
        confirmed: bool = False,
    ) -> Entry:
        """Approve or reject a pending version.

        Nobody who wrote this version, or a version it was revised from, can decide it, unless
        ``single_reviewer`` (the POC setting, D-083): then they may, an approval only when
        ``confirmed``, and the review row is marked single-reviewer. When ``expected_hash`` is
        given (always, from the review API) the decision applies only if the version still
        says exactly what the reviewer was shown.
        """

        now = self._clock()
        with self._write(authorize) as db:
            entry = self._require(db, entry_id, version)
            if entry.status != EntryStatus.PENDING_REVIEW:
                raise KnowledgeError("only a version pending review can be decided")
            if expected_hash is not None and expected_hash != entry.content_hash():
                raise ContentChangedError("the version no longer says what was reviewed")
            if not reviewer:
                raise MakerCheckerError("a decision needs a reviewer")
            own = reviewer in self._chain_authors(db, entry)
            if own and not single_reviewer:
                raise MakerCheckerError("an author or editor of an entry cannot decide it")
            if own and approve and not confirmed:
                raise ConfirmationRequiredError("approving your own entry must be confirmed")
            self._check_replaces(db, entry)
            decision = "approve" if approve else "reject"
            db.execute(
                "INSERT INTO reviews (entry_id, version, reviewer, decision, notes, created_at, "
                "single_reviewer) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (entry_id, version, reviewer, decision, notes, now, int(own)),
            )
            if not approve:
                self._set_status(db, entry, "rejected")
                # The request this was drafted from needs handling again.
                db.execute(
                    "UPDATE feedback SET status = 'open' WHERE entry_id = ? "
                    "AND entry_version = ? AND status = 'drafted' AND helpful = 0",
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
            self._set_status(
                db, entry, "approved", extra=", approver = ?, approved_at = ?", args=(reviewer, now)
            )
            db.execute(
                "UPDATE feedback SET status = 'resolved', closed_by = ?, closed_at = ? "
                "WHERE entry_id = ? AND entry_version = ? AND status = 'drafted' AND helpful = 0",
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
        """Take an entry's current version out of search at once.

        For repository maintenance only (a guidance file was removed): people retire through
        ``request_retirement``, which needs two of them.
        """

        now = self._clock()
        with self._write() as db:
            row = db.execute(
                "SELECT * FROM entries WHERE entry_id = ? AND status = 'approved'", (entry_id,)
            ).fetchone()
            if row is None:
                return None
            entry = _row_to_entry(row)
            self._retire(db, entry, by=by, notes=notes, now=now)
        return entry.with_changes(status=EntryStatus.RETIRED)

    def request_retirement(
        self,
        entry_id: str,
        *,
        by: str,
        notes: str,
        authorize: Callable[[], None] | None = None,
    ) -> tuple[Entry, bool]:
        """Retire an approved entry with two people: one asks, a different one confirms.

        Returns the current version and whether it is now retired. The first call records the
        request; a call by the same person again is refused; a call by someone else retires
        it, naming both in the history. A request for a version that has since been replaced
        no longer counts.
        """

        if not by:
            raise KnowledgeError("a retirement needs a reviewer")
        now = self._clock()
        with self._write(authorize) as db:
            row = db.execute(
                "SELECT * FROM entries WHERE entry_id = ? AND status = 'approved'", (entry_id,)
            ).fetchone()
            if row is None:
                raise KnowledgeError("no approved version to retire")
            entry = _row_to_entry(row)
            request = db.execute(
                "SELECT * FROM retire_requests WHERE entry_id = ? AND version = ?",
                (entry_id, entry.version),
            ).fetchone()
            if request is None:
                db.execute("DELETE FROM retire_requests WHERE entry_id = ?", (entry_id,))
                db.execute(
                    "INSERT INTO retire_requests (entry_id, version, requested_by, notes, "
                    "created_at) VALUES (?, ?, ?, ?, ?)",
                    (entry_id, entry.version, by, notes, now),
                )
                return entry, False
            if request["requested_by"] == by:
                raise SecondReviewerError("a different reviewer must confirm the retirement")
            self._retire(
                db,
                entry,
                by=by,
                notes=f"{notes} (asked by {request['requested_by']}: {request['notes']})",
                now=now,
            )
            db.execute("DELETE FROM retire_requests WHERE entry_id = ?", (entry_id,))
        return entry.with_changes(status=EntryStatus.RETIRED), True

    def retirement_request(self, entry_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM retire_requests WHERE entry_id = ?", (entry_id,)
            ).fetchone()
        return dict(row) if row else None

    # --- vector-index tasks ---------------------------------------------------------

    def index_tasks(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM index_tasks ORDER BY updated_at, key").fetchall()
        return [dict(row) for row in rows]

    def finish_task(self, key: str) -> None:
        with self._write() as db:
            db.execute("DELETE FROM index_tasks WHERE key = ?", (key,))

    def fail_task(self, key: str, error: str) -> None:
        with self._write() as db:
            db.execute(
                "UPDATE index_tasks SET attempts = attempts + 1, last_error = ?, updated_at = ? "
                "WHERE key = ?",
                (error[:200], self._clock(), key),
            )

    def queue_full_reindex(self, *, authorize: Callable[[], None] | None = None) -> int:
        """Ask for every current approved version to be (re)indexed."""

        now = self._clock()
        with self._write(authorize) as db:
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
        authorize: Callable[[], None] | None = None,
        **changes: Any,
    ) -> Entry:
        """A reviewer tidies a pending version (wording, redaction, follow-ups, visibility,
        what it replaces) before it is decided.

        The edit is a new pending version written by the editor; the version it revises is
        kept unchanged (retired from review, with an 'edit' row in its history). The editor,
        like the original author, can then not decide it: a different reviewer must.
        Team and role visibility can only be narrowed by an edit, never widened.
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
        with self._write(authorize) as db:
            entry = self._require(db, entry_id, version)
            if entry.status != EntryStatus.PENDING_REVIEW:
                raise KnowledgeError("only a version pending review can be edited")
            if expected_hash is not None and expected_hash != entry.content_hash():
                raise ContentChangedError("the version no longer says what was reviewed")
            new_visibility = changes.get("visibility")
            if isinstance(new_visibility, Visibility) and not (
                _narrows(entry.visibility.teams, new_visibility.teams)
                and _narrows(entry.visibility.roles, new_visibility.roles)
            ):
                raise KnowledgeRuleError("an edit can only narrow who sees an entry")
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
            # Take the revised version out of review first, and only if nobody did already.
            self._set_status(db, entry, "retired")
            self._insert(db, revised)
            # A request whose fix this was now waits for the revised version.
            db.execute(
                "UPDATE feedback SET entry_version = ? WHERE entry_id = ? "
                "AND entry_version = ? AND status = 'drafted' AND helpful = 0",
                (revised.version, entry_id, version),
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
        answer_id: str | None = None,
        answer_days: int = 7,
    ) -> int:
        """Record a rating. With ``answer_id`` it rates that answer record, which must be
        this user's, on this case, not rated yet and not older than ``answer_days``
        (``AnswerNotFoundError`` otherwise, whatever the reason). "Not helpful" links the
        record to the new request."""

        with self._write() as db:
            now = self._clock()
            if answer_id is not None:
                record = db.execute(
                    "SELECT 1 FROM answer_records WHERE id = ? AND user_id = ? AND case_id = ? "
                    "AND rated_at IS NULL AND created_at >= ?",
                    (answer_id, user_id, case_id, _days_before(now, answer_days)),
                ).fetchone()
                if record is None:
                    raise AnswerNotFoundError("no such answer")
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
                    now,
                ),
            )
            feedback_id = int(cursor.lastrowid or 0)
            if answer_id is not None:
                db.execute(
                    "UPDATE answer_records SET rated_at = ?, linked_request_id = ? WHERE id = ?",
                    (now, None if helpful else feedback_id, answer_id),
                )
            return feedback_id

    def feedback(
        self, *, status: str | None = None, helpful: bool | None = None
    ) -> list[dict[str, Any]]:
        # Each request names its answer record, if it has one (since schema v5).
        sql = (
            "SELECT f.*, (SELECT a.id FROM answer_records a WHERE a.linked_request_id = f.id)"
            " AS answer_id FROM feedback f WHERE 1 = 1"
        )
        args = list[Any]()
        if status is not None:
            sql += " AND f.status = ?"
            args.append(status)
        if helpful is not None:
            sql += " AND f.helpful = ?"
            args.append(int(helpful))
        with self._connect() as db:
            rows = db.execute(sql + " ORDER BY f.id", args).fetchall()
        return [_feedback_row(row) for row in rows]

    def draft_request(
        self,
        feedback_id: int,
        build: Callable[[dict[str, Any]], Entry],
        *,
        authorize: Callable[[], None] | None = None,
    ) -> Entry:
        """Draft a past resolution, pending review, from an open enhancement request.

        ``build`` makes the entry from the request as read inside the write lock. The request
        is linked to the draft and leaves the open list; approving the draft resolves it,
        rejecting it opens it again (``decide``).
        """

        with self._write(authorize) as db:
            row = self._open_request(db, feedback_id)
            entry = self._add_version(db, build(row), EntryStatus.PENDING_REVIEW)
            db.execute(
                "UPDATE feedback SET status = 'drafted', entry_id = ?, entry_version = ? "
                "WHERE id = ?",
                (entry.entry_id, entry.version, feedback_id),
            )
        return entry

    def close_feedback(
        self,
        feedback_id: int,
        *,
        by: str,
        reason: str,
        authorize: Callable[[], None] | None = None,
    ) -> None:
        """Close an open enhancement request without drafting knowledge, giving a reason."""

        if not by or not reason.strip():
            raise KnowledgeRuleError("closing a request needs a reviewer and a reason")
        with self._write(authorize) as db:
            self._open_request(db, feedback_id)
            db.execute(
                "UPDATE feedback SET status = 'closed', closed_by = ?, closed_at = ?, "
                "close_reason = ? WHERE id = ?",
                (by, self._clock(), reason.strip(), feedback_id),
            )

    @staticmethod
    def _open_request(db: sqlite3.Connection, feedback_id: int) -> dict[str, Any]:
        """The enhancement request ("Not helpful" feedback), if it is still open."""

        row = db.execute(
            "SELECT * FROM feedback WHERE id = ? AND helpful = 0", (feedback_id,)
        ).fetchone()
        if row is None:
            raise KnowledgeError("no such enhancement request")
        if row["status"] != "open":
            raise ContentChangedError("the request was already handled")
        return _feedback_row(row)

    # --- answer records (schema v5) --------------------------------------------------

    def add_answer_record(
        self, record: dict[str, Any], *, purge_days: tuple[int, int] | None = None
    ) -> None:
        """Store a new answer record (insert only; its id must be new). With ``purge_days``
        (unrated, closed), expired records are deleted in the same write."""

        with self._write() as db:
            now = self._clock()
            if purge_days is not None:
                self._purge_answers(db, now, *purge_days)
            db.execute(
                "INSERT INTO answer_records (id, case_id, user_id, team, created_at, question, "
                + ", ".join(_ANSWER_JSON)
                + ") VALUES ("
                + ", ".join("?" * (6 + len(_ANSWER_JSON)))
                + ")",
                (
                    record["id"],
                    record["case_id"],
                    record["user_id"],
                    record["team"],
                    now,
                    record["question"],
                    *(json.dumps(record[key]) for key in _ANSWER_JSON),
                ),
            )

    def owned_answers(self, ids: list[str], *, user_id: str, case_id: str) -> list[str]:
        """The ids, in order and without repeats, of this user's records on this case."""

        wanted = list(dict.fromkeys(ids))
        if not wanted:
            return []
        with self._connect() as db:
            rows = db.execute(
                "SELECT id FROM answer_records WHERE user_id = ? AND case_id = ? AND id IN ("
                + ", ".join("?" * len(wanted))
                + ")",
                (user_id, case_id, *wanted),
            ).fetchall()
        found = {row["id"] for row in rows}
        return [answer_id for answer_id in wanted if answer_id in found]

    def answer_record(self, answer_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM answer_records WHERE id = ?", (answer_id,)).fetchone()
        return _answer_row(row) if row is not None else None

    def view_answer(
        self,
        answer_id: str,
        *,
        viewer: str,
        allow: Callable[[dict[str, Any]], bool],
        authorize: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        """The record, if ``allow`` lets this viewer see it, with the view logged in the same
        write (``AnswerNotFoundError`` otherwise, and nothing is logged)."""

        with self._write(authorize) as db:
            row = db.execute("SELECT * FROM answer_records WHERE id = ?", (answer_id,)).fetchone()
            record = _answer_row(row) if row is not None else None
            if record is None or not allow(record):
                raise AnswerNotFoundError("no such answer")
            db.execute(
                "INSERT INTO answer_record_views (record_id, viewer, viewed_at) VALUES (?, ?, ?)",
                (answer_id, viewer, self._clock()),
            )
        return record

    def answer_views(self, answer_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT viewer, viewed_at FROM answer_record_views WHERE record_id = ? ORDER BY id",
                (answer_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def purge_answer_records(self, *, unrated_days: int, closed_days: int) -> int:
        with self._write() as db:
            return self._purge_answers(db, self._clock(), unrated_days, closed_days)

    @staticmethod
    def _purge_answers(
        db: sqlite3.Connection, now: str, unrated_days: int, closed_days: int
    ) -> int:
        """Delete records not linked to a request (unrated, or rated "Yes, helpful") older than
        ``unrated_days``, and linked records whose request was resolved or closed more than
        ``closed_days`` ago. Their logged views go with them."""

        unlinked = db.execute(
            "DELETE FROM answer_records WHERE linked_request_id IS NULL AND created_at < ?",
            (_days_before(now, unrated_days),),
        ).rowcount
        linked = db.execute(
            "DELETE FROM answer_records WHERE linked_request_id IN (SELECT id FROM feedback "
            "WHERE status IN ('resolved', 'closed') AND closed_at IS NOT NULL AND closed_at < ?)",
            (_days_before(now, closed_days),),
        ).rowcount
        return int(unlinked) + int(linked)

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
            INSERT INTO reviews (id, entry_id, version, reviewer, decision, notes, created_at)
                SELECT id, entry_id, version, reviewer, decision, notes, created_at
                FROM reviews_v1;
            DROP TABLE reviews_v1;
            """
        )

    @staticmethod
    def _migrate_to_3(db: sqlite3.Connection) -> None:
        """Version 3 records which version a reviewer's edit revises."""

        columns = {row[1] for row in db.execute("PRAGMA table_info(entries)")}
        if "revises" not in columns:
            db.execute("ALTER TABLE entries ADD COLUMN revises INTEGER")

    @staticmethod
    def _repair_5(db: sqlite3.Connection) -> None:
        """An earlier build of this branch (never on main) stamped 5 on an answer_records
        table without ``shown_answer``, so every new record failed to insert. Add the column
        (stored as JSON like the others); records made before it have an empty shown answer."""

        columns = {row[1] for row in db.execute("PRAGMA table_info(answer_records)")}
        if columns and "shown_answer" not in columns:
            db.execute(
                "ALTER TABLE answer_records ADD COLUMN shown_answer TEXT NOT NULL DEFAULT '\"\"'"
            )
            db.commit()

    @staticmethod
    def _migrate_to_4(db: sqlite3.Connection) -> None:
        """Version 4 marks single-reviewer decisions (D-083): reviews gain ``single_reviewer``
        (0 for every existing row). It also lets an enhancement request be 'resolved' (its
        draft was approved) and records why one was closed: rebuild the feedback table.
        Existing rows keep their values; none has a close reason or a linked fix version
        (``entry_version``: requests are linked to the exact version of their fix). The
        rebuild is one transaction. A store without a feedback table gets the new one from
        the schema; one already rebuilt is left alone, except that a rebuild from before
        ``entry_version`` existed gains that column."""

        reviews = {row[1] for row in db.execute("PRAGMA table_info(reviews)")}
        if reviews and "single_reviewer" not in reviews:
            db.execute("ALTER TABLE reviews ADD COLUMN single_reviewer INTEGER NOT NULL DEFAULT 0")
            db.commit()
        existing = {row[1] for row in db.execute("PRAGMA table_info(feedback)")}
        if not existing:
            return
        if "close_reason" in existing:
            if "entry_version" not in existing:
                db.execute("ALTER TABLE feedback ADD COLUMN entry_version INTEGER")
                db.commit()
            return
        columns = (
            "id, case_id, user_id, role, team, helpful, note, blocker_codes, fields, stages, "
            "entry_id, status, created_at, closed_by, closed_at"
        )
        db.executescript(
            f"""
            BEGIN;
            ALTER TABLE feedback RENAME TO feedback_v3;
            CREATE TABLE feedback (
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
                status TEXT NOT NULL
                    CHECK (status IN ('open', 'drafted', 'resolved', 'closed')),
                created_at TEXT NOT NULL,
                closed_by TEXT,
                closed_at TEXT,
                close_reason TEXT,
                entry_version INTEGER
            );
            INSERT INTO feedback ({columns}) SELECT {columns} FROM feedback_v3;
            DROP TABLE feedback_v3;
            COMMIT;
            """
        )

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
        """Everyone who wrote or edited ``entry`` or a version it was revised from.

        Editors come from the 'edit' rows of every version in the chain. That also covers a
        store from before schema v3, where a reviewer's edit changed the pending version in
        place and left only an 'edit' row on it: that editor stays barred after migration.
        """

        authors = {entry.author}
        chain = [entry.version]
        revises, seen = entry.revises, {entry.version}
        while revises is not None and revises not in seen:
            seen.add(revises)
            chain.append(revises)
            row = db.execute(
                "SELECT author, revises FROM entries WHERE entry_id = ? AND version = ?",
                (entry.entry_id, revises),
            ).fetchone()
            if row is None:
                break
            authors.add(row["author"])
            revises = row["revises"]
        marks = ", ".join("?" for _ in chain)
        editors = db.execute(
            f"SELECT reviewer FROM reviews WHERE entry_id = ? AND decision = 'edit' "
            f"AND version IN ({marks})",
            (entry.entry_id, *chain),
        ).fetchall()
        return authors | {row["reviewer"] for row in editors}

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
