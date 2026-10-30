"""PR #99 review on 9cae747: every review or guidance change reloads the caller from the CLM
backend inside its write transaction (P1), reindex re-embeds every current entry (P2), and an
explicit null clears what a draft replaces (P2)."""

import copy
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

import tests.test_knowledge_review as review
from ai_assistant.config import AiAssistantSettings
from ai_assistant.knowledge.ingest import ingest_guidance
from ai_assistant.knowledge.models import Entry, EntryKind, EntryStatus
from ai_assistant.knowledge.service import KnowledgeBase
from ai_assistant.knowledge.store import KnowledgeStore
from ai_assistant.knowledge.vector_index import VectorIndex, document_text
from ai_assistant.main import create_app
from tests.test_ai_assistant import CASE_ID, ORIGIN, FakeModel, _session
from tests.test_knowledge_review import (  # noqa: F401
    USERS,
    _profile,
    client,
    decide,
    drafted,
    edit,
    kb,
    shown_hash,
)
from tests.test_knowledge_store import HashEmbedder

RETIRE = "/assistant/knowledge/entries/guidance.address-mismatch/retire"


@pytest.fixture
def quiet_kb(tmp_path: Path) -> KnowledgeBase:
    """The review tests' knowledge base, kept free of vectors.

    Once a persistent Chroma index holds a vector it keeps four files open for the rest of the
    run, and this module builds dozens of indexes: on Windows that left later tests short of
    file handles. With the embedder down nothing is embedded; these tests are about who may
    change what, not about search."""

    embedder = HashEmbedder()
    embedder.down = True
    knowledge = KnowledgeBase(
        store=KnowledgeStore(tmp_path / "knowledge.sqlite3"),
        index=VectorIndex(tmp_path / "chroma"),
        embedder=embedder,
    )
    ingest_guidance(knowledge)
    return knowledge


def _locked(path: Path) -> bool:
    """True while another connection holds the knowledge store's write lock."""

    db = sqlite3.connect(path, timeout=0, isolation_level=None)
    try:
        db.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError:
        return True
    else:
        db.execute("ROLLBACK")
        return False
    finally:
        db.close()


def _dump(path: Path) -> list[str]:
    db = sqlite3.connect(path)
    try:
        return list(db.iterdump())
    finally:
        db.close()


class ReversedEmbedder(HashEmbedder):
    """Another embedding model: the same text gives a different vector."""

    name = "hash-test-reversed"

    def _vector(self, text: str) -> list[float]:
        return super()._vector(text)[::-1]


def _vectors(kb: KnowledgeBase) -> dict[str, list[float]]:  # noqa: F811
    stored: dict[str, list[float]] = {}
    for kind in EntryKind:
        got = kb.index._collections[kind].get(include=["embeddings"])
        for key, vector in zip(got["ids"], got["embeddings"], strict=True):
            stored[key] = [float(x) for x in vector]
    return stored


def _state(kb: KnowledgeBase, path: Path) -> tuple[list[str], dict[str, list[float]]]:  # noqa: F811
    """Everything a change could touch: every SQLite row and every stored vector."""

    return _dump(path), _vectors(kb)


class Backend:
    """The CLM backend for one signed-in caller. The first /api/auth/me (the route's own check)
    answers with their profile; each later one (the check inside the change) answers with
    ``later`` and records whether the knowledge store's write lock was held at that moment."""

    def __init__(self, session: str, later: Callable[[], httpx.Response], store: Path) -> None:
        self.session, self.later, self.store = session, later, store
        self.me_calls = 0
        self.locked: list[bool] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/me" and _session(request) == self.session:
            self.me_calls += 1
            if self.me_calls > 1:
                self.locked.append(_locked(self.store))
                return self.later()
        return review.handler(request)

    def client(self, kb: KnowledgeBase) -> TestClient:  # noqa: F811
        settings = AiAssistantSettings(  # type: ignore[call-arg]
            _env_file=None, llm_enabled=False, knowledge_single_reviewer=False
        )
        app = create_app(
            settings, clm_transport=httpx.MockTransport(self), chat_model=FakeModel(), knowledge=kb
        )
        c = TestClient(app, headers={"Origin": ORIGIN})
        c.cookies.set("clm_session", self.session)
        return c


def _now_as(session: str, **profile: Any) -> Callable[[], httpx.Response]:
    """/api/auth/me for the same session after the backend changed ``profile``."""

    me = copy.deepcopy(USERS[session])
    me["profile"].update(profile)
    return lambda: httpx.Response(200, json=me)


Mutation = tuple[str, str, dict[str, Any] | None]


def _edit(kb: KnowledgeBase) -> Mutation:  # noqa: F811
    entry_id = drafted(kb)
    body = {"content_hash": shown_hash(kb, entry_id, 1), "title": "Tidied title for review"}
    return "director-session", f"/assistant/knowledge/entries/{entry_id}/versions/1/edit", body


def _decision(kb: KnowledgeBase) -> Mutation:  # noqa: F811
    entry_id = drafted(kb)
    body = {"approve": True, "content_hash": shown_hash(kb, entry_id, 1)}
    return "director-session", f"/assistant/knowledge/entries/{entry_id}/versions/1/decision", body


def _retire_request(kb: KnowledgeBase) -> Mutation:  # noqa: F811
    return "director-session", RETIRE, {"notes": "outdated"}


def _retire_confirm(kb: KnowledgeBase) -> Mutation:  # noqa: F811
    asked = client(kb, "director-2-session").post(RETIRE, json={"notes": "outdated"})
    assert asked.json()["retirement"] == "requested"
    return "director-session", RETIRE, {"notes": "agreed, outdated"}


def _close_gap(kb: KnowledgeBase) -> Mutation:  # noqa: F811
    reply = client(kb, "rm-session").post(
        f"/assistant/cases/{CASE_ID}/feedback", json={"helpful": False, "note": "No proof list."}
    )
    assert reply.status_code == 200
    gap = kb.store.feedback(status="open")[0]["id"]
    return "director-session", f"/assistant/knowledge/feedback/{gap}/close", {"reason": "Dup."}


def _draft_from_gap(kb: KnowledgeBase) -> Mutation:  # noqa: F811
    reply = client(kb, "rm-session").post(
        f"/assistant/cases/{CASE_ID}/feedback", json={"helpful": False, "note": "No proof list."}
    )
    assert reply.status_code == 200
    gap = kb.store.feedback(status="open")[0]["id"]
    return "director-session", f"/assistant/knowledge/feedback/{gap}/draft", review.fix()


def _reindex(kb: KnowledgeBase) -> Mutation:  # noqa: F811
    return "director-session", "/assistant/knowledge/reindex", None


def _propose_guidance(kb: KnowledgeBase) -> Mutation:  # noqa: F811
    body = {
        "entry_id": "guidance.new-rule",
        "title": "A new rule",
        "body": "A new rule written for this test.",
        "source_ref": "D-030",
    }
    return "hr-session", "/assistant/knowledge/guidance", body


MUTATIONS: dict[str, Callable[[KnowledgeBase], Mutation]] = {
    "edit": _edit,
    "decision": _decision,
    "retire-request": _retire_request,
    "retire-confirm": _retire_confirm,
    "close-gap": _close_gap,
    "draft-from-gap": _draft_from_gap,
    "reindex": _reindex,
    "propose-guidance": _propose_guidance,
}


# --- P1: the caller is checked again inside the change ----------------------------------


@pytest.mark.parametrize(
    ("revoked", "status", "code"),
    [
        ("capability", 403, "FORBIDDEN"),
        ("session", 401, "AUTHENTICATION_REQUIRED"),
        ("another-user", 401, "AUTHENTICATION_REQUIRED"),
        ("backend-down", 502, "CLM_BACKEND_ERROR"),
    ],
)
@pytest.mark.parametrize("mutation", MUTATIONS)
def test_a_caller_revoked_during_the_request_changes_nothing(
    quiet_kb: KnowledgeBase,
    tmp_path: Path,
    mutation: str,
    revoked: str,
    status: int,
    code: str,
) -> None:
    session, path, body = MUTATIONS[mutation](quiet_kb)
    later = {
        "capability": _now_as(session, capabilities=["POLICY_VIEW"]),
        "session": lambda: httpx.Response(401, json={"detail": "auth"}),
        "another-user": _now_as(session, user_id="someone-else"),
        "backend-down": lambda: httpx.Response(500, json={"detail": "error"}),
    }[revoked]
    backend = Backend(session, later, tmp_path / "knowledge.sqlite3")
    quiet_kb.embedder = ReversedEmbedder()  # so a reindex that went ahead would store vectors
    before = _state(quiet_kb, tmp_path / "knowledge.sqlite3")
    reply = backend.client(quiet_kb).post(path, json=body)
    assert reply.status_code == status, reply.text
    assert reply.json()["detail"]["code"] == code
    # Nothing written: no new version, review, retire request, index task or vector; the
    # draft is still pending and the gap still open.
    assert _state(quiet_kb, tmp_path / "knowledge.sqlite3") == before
    # The route's own check, the in-transaction recheck, and for the fix to a request also
    # the case load between them (which already fails for a revoked session or a down backend).
    loads_case = mutation == "draft-from-gap" and revoked in {"capability", "another-user"}
    assert backend.me_calls == (3 if loads_case else 2)
    if loads_case:
        assert backend.locked == [False, True]  # the refusal came from inside the write


@pytest.mark.parametrize("mutation", ["edit", "decision", "close-gap", "draft-from-gap"])
def test_a_reviewer_moved_to_another_team_during_the_request_changes_nothing(
    quiet_kb: KnowledgeBase,
    tmp_path: Path,
    mutation: str,
) -> None:
    session, path, body = MUTATIONS[mutation](quiet_kb)
    backend = Backend(session, _now_as(session, team_id="TEAM_B"), tmp_path / "knowledge.sqlite3")
    before = _state(quiet_kb, tmp_path / "knowledge.sqlite3")
    reply = backend.client(quiet_kb).post(path, json=body)
    assert reply.status_code == 404, reply.text
    assert _state(quiet_kb, tmp_path / "knowledge.sqlite3") == before


@pytest.mark.parametrize("mutation", MUTATIONS)
def test_the_caller_is_reloaded_while_the_write_lock_is_held(
    quiet_kb: KnowledgeBase,
    tmp_path: Path,
    mutation: str,
) -> None:
    session, path, body = MUTATIONS[mutation](quiet_kb)
    backend = Backend(
        session, lambda: httpx.Response(200, json=USERS[session]), tmp_path / "knowledge.sqlite3"
    )
    reply = backend.client(quiet_kb).post(path, json=body)
    assert reply.status_code == 200, reply.text
    # Reindex checks once before it removes any vector, then again inside its write. Writing
    # the fix for a request first loads the request's case (to redact the fix against it)
    # with the caller's session, outside the write; the recheck still runs inside it.
    unlocked_first = mutation in {"reindex", "draft-from-gap"}
    assert backend.locked == ([False, True] if unlocked_first else [True])


class Refused(Exception):
    pass


def _seeded(path: Path) -> KnowledgeStore:
    """A pending resolution, an approved guidance entry (indexed) and an open gap."""

    store = KnowledgeStore(path)
    store.add_version(
        Entry(
            entry_id="resolution.r",
            kind=EntryKind.RESOLUTION,
            title="T",
            body="Body text here.",
            author="maya-lim",
        )
    )
    guidance = store.add_version(
        Entry(
            entry_id="guidance.g",
            kind=EntryKind.GUIDANCE,
            title="Rule",
            body="A rule for the demo.",
            author="hr-hana",
        )
    )
    approved = store.decide(guidance.entry_id, 1, reviewer="director-dan", approve=True)
    store.finish_task(approved.key)
    store.add_feedback(
        case_id=CASE_ID,
        user_id="maya-lim",
        role="CLIENT_ONBOARDER",
        team="TEAM_A",
        helpful=False,
        note="No proof list.",
        blocker_codes=(),
        fields=(),
        stages=(),
        entry_id=None,
    )
    return store


StoreCall = Callable[[KnowledgeStore, Callable[[], None]], object]
STORE_CALLS: dict[str, StoreCall] = {
    "add_version": lambda store, check: store.add_version(
        Entry(
            entry_id="resolution.new",
            kind=EntryKind.RESOLUTION,
            title="New",
            body="A new draft.",
            author="maya-lim",
        ),
        authorize=check,
    ),
    "decide": lambda store, check: store.decide(
        "resolution.r", 1, reviewer="director-dee", approve=True, authorize=check
    ),
    "revise_pending": lambda store, check: store.revise_pending(
        "resolution.r", 1, editor="director-dan", authorize=check, body="Edited body text."
    ),
    "request_retirement": lambda store, check: store.request_retirement(
        "guidance.g", by="director-dan", notes="old", authorize=check
    ),
    "close_feedback": lambda store, check: store.close_feedback(
        1, by="director-dan", reason="Duplicate.", authorize=check
    ),
    "draft_request": lambda store, check: store.draft_request(
        1,
        lambda row: Entry(
            entry_id="resolution.from-request",
            kind=EntryKind.RESOLUTION,
            title="Draft",
            body=row["note"],
            author="director-dan",
        ),
        authorize=check,
    ),
    "queue_full_reindex": lambda store, check: store.queue_full_reindex(authorize=check),
}


@pytest.mark.parametrize("call", STORE_CALLS)
def test_authorize_runs_first_inside_the_write_lock_and_its_error_rolls_back(
    tmp_path: Path, call: str
) -> None:
    path = tmp_path / "k.sqlite3"
    store = _seeded(path)
    before = _dump(path)
    seen: list[tuple[bool, bool]] = []

    def refuse() -> None:
        seen.append((_locked(path), _dump(path) == before))
        raise Refused

    with pytest.raises(Refused):
        STORE_CALLS[call](store, refuse)
    # It ran once, with the write lock held and before anything was written.
    assert seen == [(True, True)]
    assert _dump(path) == before
    # When it passes, the change goes ahead.
    STORE_CALLS[call](store, lambda: None)
    assert _dump(path) != before


# --- P2: reindex re-embeds every current entry ------------------------------------------


def test_reindex_re_embeds_every_entry_with_the_current_model(kb: KnowledgeBase) -> None:  # noqa: F811
    before = _vectors(kb)
    approved = kb.store.entries(status=EntryStatus.APPROVED)
    assert before and set(before) == {entry.key for entry in approved}
    kb.embedder = ReversedEmbedder()  # e.g. AI_ASSISTANT_EMBED_MODEL changed
    reply = client(kb, "director-session").post("/assistant/knowledge/reindex")
    assert reply.status_code == 200, reply.text
    assert reply.json() == {"indexed": len(approved), "removed": 0, "waiting": 0}
    after = _vectors(kb)
    assert set(after) == set(before)
    for entry in approved:
        expected = ReversedEmbedder().embed_documents([document_text(entry)])[0]
        assert after[entry.key] == pytest.approx(expected, abs=1e-6)
        assert after[entry.key] != pytest.approx(before[entry.key], abs=1e-6)


# --- P2: a reviewer can clear what a draft replaces -------------------------------------


def test_an_explicit_null_clears_what_a_draft_replaces(
    quiet_kb: KnowledgeBase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        USERS, "director-3-session", _profile("director-dov", "SUPPORT", ["KNOWLEDGE_REVIEW"])
    )
    first = drafted(quiet_kb)
    assert decide(quiet_kb, "director-session", first, 1).status_code == 200
    second = drafted(quiet_kb, note="Newer, clearer resolution.")
    replacing = edit(quiet_kb, "director-session", second, 1, replaces=first)
    assert replacing.json()["replaces"] == first
    # Leaving "replaces" out keeps it.
    kept = edit(quiet_kb, "director-2-session", second, 2, title="Tidied title, still replacing")
    assert kept.status_code == 200 and kept.json()["replaces"] == first
    # An explicit null clears it, so approving no longer retires the older entry.
    cleared = edit(quiet_kb, "director-2-session", second, 3, replaces=None)
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["replaces"] is None
    assert quiet_kb.store.get(second, 4).replaces is None
    assert decide(quiet_kb, "director-3-session", second, 4).status_code == 200
    assert quiet_kb.store.current(first) is not None
    assert quiet_kb.store.current(second).version == 4
