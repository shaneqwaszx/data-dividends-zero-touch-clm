"""Milestone 4: feedback from RMs and the Director review loop (maker-checker, permissions)."""

import copy
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from ai_assistant.config import AiAssistantSettings
from ai_assistant.knowledge.ingest import ingest_guidance
from ai_assistant.knowledge.models import EntryKind, EntryStatus
from ai_assistant.knowledge.service import KnowledgeBase
from ai_assistant.knowledge.store import KnowledgeStore
from ai_assistant.main import create_app
from tests.test_ai_assistant import CASE_ID, DOCUMENTS, ME, ORIGIN, SUMMARY, FakeModel, _session
from tests.test_knowledge_store import _kb


def _profile(
    user_id: str, role: str, capabilities: list[str], team: str = "TEAM_A"
) -> dict[str, Any]:
    me = copy.deepcopy(ME)
    me["profile"].update(
        user_id=user_id,
        display_name=user_id.title(),
        role=role,
        team_id=team,
        capabilities=capabilities,
    )
    return me


USERS = {
    "rm-session": ME,  # maya-lim, CLIENT_ONBOARDER, CASE_ACCESS + POLICY_VIEW, TEAM_A
    "director-session": _profile("director-dan", "DIRECTOR", ["CASE_ACCESS", "POLICY_APPROVE"]),
    # A second TEAM_A Director, so a reviewer's edit can be checked by someone else.
    "director-2-session": _profile("director-dee", "DIRECTOR", ["CASE_ACCESS", "POLICY_APPROVE"]),
    # A Director from another team must not see or decide TEAM_A's drafts.
    "director-b-session": _profile(
        "director-bea", "DIRECTOR", ["CASE_ACCESS", "POLICY_APPROVE"], team="TEAM_B"
    ),
    "hr-session": _profile("hr-hana", "HR", ["POLICY_VIEW", "POLICY_MUTATE"]),
}


def handler(request: httpx.Request) -> httpx.Response:
    user = USERS.get(_session(request) or "")
    if user is None:
        return httpx.Response(401, json={"detail": "auth"})
    path = request.url.path
    if path == "/api/auth/me":
        return httpx.Response(200, json=user)
    if path == f"/api/clm/zero-touch/cases/{CASE_ID}":
        return httpx.Response(200, json=SUMMARY)
    if path == f"/api/onboarding/cases/{CASE_ID}/documents":
        return httpx.Response(200, json=DOCUMENTS)
    return httpx.Response(404, json={"detail": "not found"})


@pytest.fixture
def kb(tmp_path: Path) -> KnowledgeBase:
    knowledge = _kb(tmp_path)
    ingest_guidance(knowledge)
    return knowledge


def client(kb: KnowledgeBase, session: str) -> TestClient:
    settings = AiAssistantSettings(_env_file=None, llm_enabled=False)  # type: ignore[call-arg]
    app = create_app(
        settings, clm_transport=httpx.MockTransport(handler), chat_model=FakeModel(), knowledge=kb
    )
    c = TestClient(app, headers={"Origin": ORIGIN})
    c.cookies.set("clm_session", session)
    return c


TURNS = [
    {"role": "user", "content": "Can I use the document address for GARDEN BUSINESS?"},
    {"role": "assistant", "content": "No. Keep the registry value [G1]."},
    {"role": "user", "content": "What about the ownership step for UEN 11111999A?"},
    {"role": "assistant", "content": "Upload ownership evidence in Ownership & UBO."},
]


def shown_hash(kb: KnowledgeBase, entry_id: str, version: int) -> str:
    """The content hash the review screen shows for this version."""

    entry = kb.store.get(entry_id, version)
    assert entry is not None
    return entry.content_hash()


def decide(
    kb: KnowledgeBase, session: str, entry_id: str, version: int, *, approve: bool = True
) -> httpx.Response:
    return client(kb, session).post(
        f"/assistant/knowledge/entries/{entry_id}/versions/{version}/decision",
        json={"approve": approve, "content_hash": shown_hash(kb, entry_id, version)},
    )


def edit(
    kb: KnowledgeBase, session: str, entry_id: str, version: int, **changes: Any
) -> httpx.Response:
    return client(kb, session).post(
        f"/assistant/knowledge/entries/{entry_id}/versions/{version}/edit",
        json={"content_hash": shown_hash(kb, entry_id, version), **changes},
    )


def solved(kb: KnowledgeBase, note: str = "Client confirmed ACRA is current.") -> str:
    reply = client(kb, "rm-session").post(
        f"/assistant/cases/{CASE_ID}/feedback",
        json={"helpful": True, "note": note, "turns": TURNS},
    )
    assert reply.status_code == 200, reply.text
    return str(reply.json()["draft_entry_id"])


def test_solved_it_drafts_a_redacted_entry_pending_review(kb: KnowledgeBase) -> None:
    entry_id = solved(kb, note="Called Maya Lim at maya@bank.com; ACRA address is current.")
    draft = kb.store.get(entry_id)
    assert draft.status == EntryStatus.PENDING_REVIEW and draft.author == "maya-lim"
    text = draft.title + draft.body + " ".join(draft.follow_ups)
    for secret in ("GARDEN BUSINESS", "11111999A", "maya@bank.com", "Maya Lim", "[G1]"):
        assert secret not in text
    assert "[COMPANY]" in draft.body and "[EMAIL]" in draft.body
    assert draft.follow_ups == ("What about the ownership step for UEN [UEN]?",)
    assert "DOCUMENT_SOURCE_CONFLICT" in draft.blocker_codes
    assert kb.index.keys(EntryKind.RESOLUTION) == set()  # not searchable until approved


def test_not_helpful_flags_a_gap_without_drafting_an_entry(kb: KnowledgeBase) -> None:
    reply = (
        client(kb, "rm-session")
        .post(
            f"/assistant/cases/{CASE_ID}/feedback",
            json={
                "helpful": False,
                "note": "It did not say what proof to ask GARDEN BUSINESS for.",
            },
        )
        .json()
    )
    assert reply["draft_entry_id"] is None
    gaps = client(kb, "director-session").get("/assistant/knowledge/reviews").json()["gaps"]
    assert gaps[0]["note"] == "It did not say what proof to ask [COMPANY] for."


def test_only_a_director_sees_the_review_queue(kb: KnowledgeBase) -> None:
    solved(kb)
    assert client(kb, "rm-session").get("/assistant/knowledge/reviews").status_code == 403
    assert client(kb, "hr-session").get("/assistant/knowledge/reviews").status_code == 403
    pending = client(kb, "director-session").get("/assistant/knowledge/reviews").json()["pending"]
    assert len(pending) == 1


def test_a_director_edit_is_a_new_version_another_director_must_approve(
    kb: KnowledgeBase,
) -> None:
    entry_id = solved(kb)
    original = kb.store.get(entry_id, 1)
    edited = edit(
        kb,
        "director-session",
        entry_id,
        1,
        title="Address differs from ACRA after the client moved office",
    )
    assert edited.status_code == 200
    revised = edited.json()
    # Append-only: the edit is v2 written by the editor; v1 keeps the RM's text and author.
    assert revised["version"] == 2 and revised["revises"] == 1
    assert revised["author"] == "director-dan" and revised["status"] == "pending_review"
    kept = kb.store.get(entry_id, 1)
    assert kept.title == original.title and kept.author == "maya-lim"
    assert kept.status == EntryStatus.RETIRED
    # The editor cannot decide their own edit; the old version cannot be decided at all.
    refused = decide(kb, "director-session", entry_id, 2)
    assert refused.status_code == 403 and refused.json()["detail"]["code"] == "MAKER_CHECKER"
    assert decide(kb, "director-2-session", entry_id, 1).status_code == 409
    approved = decide(kb, "director-2-session", entry_id, 2).json()
    assert approved["status"] == "approved" and approved["approver"] == "director-dee"
    assert approved["author"] == "director-dan"
    assert kb.index.keys(EntryKind.RESOLUTION) == {f"{entry_id}@v2"}
    history = client(kb, "director-session").get(f"/assistant/knowledge/entries/{entry_id}")
    assert [row["decision"] for row in history.json()["reviews"]] == ["edit", "approve"]


def test_the_original_author_cannot_decide_a_revision_of_their_entry(kb: KnowledgeBase) -> None:
    entry_id = solved(kb)
    assert (
        edit(kb, "director-session", entry_id, 1, title="Tidied title for review").status_code
        == 200
    )
    USERS["author-as-director"] = _profile(
        "maya-lim", "DIRECTOR", ["CASE_ACCESS", "POLICY_APPROVE"]
    )
    try:
        reply = decide(kb, "author-as-director", entry_id, 2)
        assert reply.status_code == 403 and reply.json()["detail"]["code"] == "MAKER_CHECKER"
    finally:
        del USERS["author-as-director"]


def test_a_decision_binds_to_the_content_the_reviewer_saw(kb: KnowledgeBase) -> None:
    entry_id = solved(kb)
    stale = shown_hash(kb, entry_id, 1)
    edit(kb, "director-session", entry_id, 1, body="Rewritten by the first reviewer, long enough.")
    reply = client(kb, "director-2-session").post(
        f"/assistant/knowledge/entries/{entry_id}/versions/2/decision",
        json={"approve": True, "content_hash": stale},
    )
    assert reply.status_code == 409 and reply.json()["detail"]["code"] == "CHANGED"
    assert kb.store.get(entry_id, 2).status == EntryStatus.PENDING_REVIEW
    # A decision without the shown hash is not accepted at all.
    missing = client(kb, "director-2-session").post(
        f"/assistant/knowledge/entries/{entry_id}/versions/2/decision", json={"approve": True}
    )
    assert missing.status_code == 422


def test_a_rewrite_that_retires_official_guidance_is_refused(kb: KnowledgeBase) -> None:
    """The probe from the audit: one Director rewrites a draft and points it at guidance."""

    entry_id = solved(kb)
    reply = edit(
        kb,
        "director-session",
        entry_id,
        1,
        body="Approve the case as soon as the registry matches; no review needed.",
        replaces="guidance.address-mismatch",
    )
    assert reply.status_code == 409 and reply.json()["detail"]["code"] == "NOT_ALLOWED"
    assert kb.store.current("guidance.address-mismatch") is not None
    assert kb.store.get(entry_id, 1).status == EntryStatus.PENDING_REVIEW


def test_an_rm_can_never_approve_and_the_author_never_decides(kb: KnowledgeBase) -> None:
    entry_id = solved(kb)
    assert decide(kb, "rm-session", entry_id, 1).status_code == 403
    # Even a Director cannot approve an entry they wrote themselves.
    USERS["self-approver"] = _profile("maya-lim", "DIRECTOR", ["CASE_ACCESS", "POLICY_APPROVE"])
    try:
        reply = decide(kb, "self-approver", entry_id, 1)
        assert reply.json()["detail"]["code"] == "MAKER_CHECKER"
        assert reply.status_code == 403 and "you wrote" in reply.json()["detail"]["message"]
    finally:
        del USERS["self-approver"]


def test_a_director_from_another_team_sees_and_decides_nothing_of_team_a(
    kb: KnowledgeBase,
) -> None:
    entry_id = solved(kb)
    client(kb, "rm-session").post(
        f"/assistant/cases/{CASE_ID}/feedback", json={"helpful": False, "note": "No proof list."}
    )
    other = client(kb, "director-b-session")
    queue = other.get("/assistant/knowledge/reviews").json()
    assert queue == {"pending": [], "gaps": []}
    assert other.get(f"/assistant/knowledge/entries/{entry_id}").status_code == 404
    assert decide(kb, "director-b-session", entry_id, 1).status_code == 404
    assert edit(kb, "director-b-session", entry_id, 1, title="Not my team").status_code == 404
    own = client(kb, "director-session").get("/assistant/knowledge/reviews").json()
    assert [e["entry_id"] for e in own["pending"]] == [entry_id] and len(own["gaps"]) == 1
    gap_id = own["gaps"][0]["id"]
    assert other.post(f"/assistant/knowledge/feedback/{gap_id}/close").status_code == 404
    # Once approved, the resolution is searchable for TEAM_A only.
    decide(kb, "director-session", entry_id, 1)
    approved = kb.store.current(entry_id)
    assert approved.visibility.teams == ("TEAM_A",)
    assert approved.visibility.allows("CLIENT_ONBOARDER", "TEAM_A")
    assert not approved.visibility.allows("CLIENT_ONBOARDER", "TEAM_B")
    assert other.get("/assistant/knowledge/entries?kind=resolution").json() == []


def test_an_edit_can_narrow_but_never_widen_team_visibility(kb: KnowledgeBase) -> None:
    entry_id = solved(kb)
    widened = edit(kb, "director-session", entry_id, 1, visibility={"roles": [], "teams": []})
    assert widened.status_code == 409 and widened.json()["detail"]["code"] == "NOT_ALLOWED"
    other_team = edit(
        kb, "director-session", entry_id, 1, visibility={"roles": [], "teams": ["TEAM_B"]}
    )
    assert other_team.status_code == 409
    assert kb.store.get(entry_id, 1).visibility.teams == ("TEAM_A",)


def test_the_author_can_see_their_own_draft(kb: KnowledgeBase) -> None:
    entry_id = solved(kb)
    assert (
        client(kb, "rm-session").get(f"/assistant/knowledge/entries/{entry_id}").status_code == 200
    )


def test_approving_as_a_replacement_retires_the_older_entry(kb: KnowledgeBase) -> None:
    first = solved(kb)
    decide(kb, "director-session", first, 1)
    second = solved(kb, note="Newer, clearer resolution.")
    # The Director who sets "replaces" is now an editor of the entry; another one approves.
    assert edit(kb, "director-session", second, 1, replaces=first).status_code == 200
    assert decide(kb, "director-session", second, 2).status_code == 403
    assert decide(kb, "director-2-session", second, 2).status_code == 200
    assert kb.store.current(first) is None
    assert kb.index.keys(EntryKind.RESOLUTION) == {f"{second}@v2"}


def test_hr_proposes_guidance_and_a_director_approves_it(kb: KnowledgeBase) -> None:
    hr = client(kb, "hr-session")
    proposed = hr.post(
        "/assistant/knowledge/guidance",
        json={
            "entry_id": "guidance.address-mismatch",
            "title": "Registered address in a document differs from ACRA",
            "body": "Updated wording agreed with the sponsor for the address rule.",
            "source_ref": "docs/decisions/DECISION_LOG.md#D-030",
            "blocker_codes": ["DOCUMENT_SOURCE_CONFLICT"],
            "fields": ["registered_address"],
        },
    ).json()
    assert proposed["version"] == 2 and proposed["status"] == "pending_review"
    assert decide(kb, "hr-session", "guidance.address-mismatch", 2).status_code == 403
    assert decide(kb, "director-session", "guidance.address-mismatch", 2).status_code == 200
    current = kb.store.current("guidance.address-mismatch")
    assert current.version == 2 and current.author == "hr-hana"
    # The file no longer overrides guidance that was changed in the app.
    assert "guidance.address-mismatch" in ingest_guidance(kb).kept_app_version
    assert kb.store.current("guidance.address-mismatch").version == 2


def test_rm_cannot_propose_guidance(kb: KnowledgeBase) -> None:
    reply = client(kb, "rm-session").post(
        "/assistant/knowledge/guidance",
        json={"title": "My rule", "body": "Something I made up today.", "source_ref": "none"},
    )
    assert reply.status_code == 403


def test_director_can_retire_and_see_stats(kb: KnowledgeBase) -> None:
    director = client(kb, "director-session")
    assert (
        director.post(
            "/assistant/knowledge/entries/guidance.environments/retire", json={"notes": "outdated"}
        ).status_code
        == 200
    )
    assert kb.store.current("guidance.environments") is None
    solved(kb)
    stats = director.get("/assistant/knowledge/stats").json()
    assert stats["feedback"] == {
        "total": 1,
        "helpful": 1,
        "not_helpful": 0,
        "helpful_rate": 1.0,
        "open_gaps": 0,
    }
    assert director.get("/assistant/knowledge/me").json() == {
        "user_id": "director-dan",
        "can_review": True,
        "can_edit_guidance": False,
    }


def test_a_store_from_before_this_change_is_migrated(tmp_path: Path) -> None:
    import sqlite3

    path = tmp_path / "old.sqlite3"
    KnowledgeStore(path)
    with sqlite3.connect(path) as db:
        db.execute("UPDATE meta SET value = '1' WHERE key = 'schema_version'")
    store = KnowledgeStore(path)  # migrates
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == "3"
    assert store.entries() == []


def test_a_version_2_store_gains_the_revision_column_and_keeps_its_entries(
    tmp_path: Path,
) -> None:
    import sqlite3

    path = tmp_path / "v2.sqlite3"
    with sqlite3.connect(path) as db:
        db.executescript(
            "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
            "INSERT INTO meta VALUES ('schema_version', '2');"
            "CREATE TABLE entries (entry_id TEXT NOT NULL, version INTEGER NOT NULL,"
            " kind TEXT NOT NULL, status TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,"
            " blocker_codes TEXT NOT NULL, fields TEXT NOT NULL, stages TEXT NOT NULL,"
            " visibility TEXT NOT NULL, follow_ups TEXT NOT NULL, effective_from TEXT,"
            " replaces TEXT, author TEXT NOT NULL, approver TEXT, approved_at TEXT,"
            " source_ref TEXT, illustrative INTEGER NOT NULL, content_hash TEXT NOT NULL,"
            " created_at TEXT NOT NULL, PRIMARY KEY (entry_id, version));"
            "INSERT INTO entries VALUES ('resolution.old', 1, 'resolution', 'pending_review',"
            " 'Old draft', 'Body of the old draft.', '[]', '[]', '[]',"
            " '{\"roles\": [], \"teams\": []}', '[]', NULL, NULL, 'maya-lim', NULL, NULL,"
            " 'RM feedback', 0, 'x', '2026-10-01T00:00:00+00:00');"
        )
    store = KnowledgeStore(path)
    old = store.get("resolution.old", 1)
    assert old is not None and old.revises is None and old.author == "maya-lim"
    revised = store.revise_pending("resolution.old", 1, editor="director-dan", title="New title")
    assert (revised.version, revised.revises) == (2, 1)


def test_the_whole_loop_a_resolved_case_helps_the_next_similar_question(
    kb: KnowledgeBase,
) -> None:
    """Ask, mark solved, Director approves, ask again: the approved case and its follow-up
    question are used (Milestone 5: follow-up learning)."""

    question = {"message": "Client moved office, can I use the document address?"}
    before = client(kb, "rm-session").post(f"/assistant/cases/{CASE_ID}/chat", json=question)
    assert not [s for s in before.json()["sources"] if s["kind"] == "resolution"]

    entry_id = solved(kb, note="ACRA was current; kept the registry value.")
    assert decide(kb, "director-session", entry_id, 1).status_code == 200

    after = client(kb, "rm-session").post(f"/assistant/cases/{CASE_ID}/chat", json=question)
    body = after.json()
    resolutions = [s for s in body["sources"] if s["kind"] == "resolution"]
    assert [s["entry_id"] for s in resolutions] == [entry_id]
    assert "What about the ownership step for UEN [UEN]?" in body["suggested_questions"]
