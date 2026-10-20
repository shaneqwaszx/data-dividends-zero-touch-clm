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
    "rm-session": ME,  # maya-lim, CLIENT_ONBOARDER, CASE_ACCESS + POLICY_VIEW
    "director-session": _profile("director-dan", "DIRECTOR", ["CASE_ACCESS", "POLICY_APPROVE"]),
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


def test_director_edits_then_approves_and_it_becomes_searchable(kb: KnowledgeBase) -> None:
    entry_id = solved(kb)
    director = client(kb, "director-session")
    edited = director.post(
        f"/assistant/knowledge/entries/{entry_id}/versions/1/edit",
        json={"title": "Address differs from ACRA after the client moved office"},
    )
    assert edited.status_code == 200
    approved = director.post(
        f"/assistant/knowledge/entries/{entry_id}/versions/1/decision",
        json={"approve": True, "notes": "Checked redaction."},
    ).json()
    assert approved["status"] == "approved" and approved["approver"] == "director-dan"
    assert f"{entry_id}@v1" in kb.index.keys(EntryKind.RESOLUTION)
    history = director.get(f"/assistant/knowledge/entries/{entry_id}").json()["reviews"]
    assert [row["decision"] for row in history] == ["edit", "approve"]


def test_an_rm_can_never_approve_and_the_author_never_decides(kb: KnowledgeBase) -> None:
    entry_id = solved(kb)
    rm = client(kb, "rm-session")
    decision = f"/assistant/knowledge/entries/{entry_id}/versions/1/decision"
    assert rm.post(decision, json={"approve": True}).status_code == 403
    # Even a Director cannot approve an entry they wrote themselves.
    USERS["self-approver"] = _profile("maya-lim", "DIRECTOR", ["CASE_ACCESS", "POLICY_APPROVE"])
    try:
        reply = client(kb, "self-approver").post(decision, json={"approve": True})
        assert reply.json()["detail"]["code"] == "MAKER_CHECKER"
        assert reply.status_code == 403 and "you wrote" in reply.json()["detail"]["message"]
    finally:
        del USERS["self-approver"]


def test_the_author_can_see_their_own_draft(kb: KnowledgeBase) -> None:
    entry_id = solved(kb)
    assert (
        client(kb, "rm-session").get(f"/assistant/knowledge/entries/{entry_id}").status_code == 200
    )


def test_approving_as_a_replacement_retires_the_older_entry(kb: KnowledgeBase) -> None:
    director = client(kb, "director-session")
    first = solved(kb)
    director.post(
        f"/assistant/knowledge/entries/{first}/versions/1/decision", json={"approve": True}
    )
    second = solved(kb, note="Newer, clearer resolution.")
    director.post(
        f"/assistant/knowledge/entries/{second}/versions/1/edit", json={"replaces": first}
    )
    director.post(
        f"/assistant/knowledge/entries/{second}/versions/1/decision", json={"approve": True}
    )
    assert kb.store.current(first) is None
    assert kb.index.keys(EntryKind.RESOLUTION) == {f"{second}@v1"}


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
    assert (
        hr.post(
            "/assistant/knowledge/entries/guidance.address-mismatch/versions/2/decision",
            json={"approve": True},
        ).status_code
        == 403
    )
    client(kb, "director-session").post(
        "/assistant/knowledge/entries/guidance.address-mismatch/versions/2/decision",
        json={"approve": True},
    )
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
        assert db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == "2"
    assert store.entries() == []


def test_the_whole_loop_a_resolved_case_helps_the_next_similar_question(
    kb: KnowledgeBase,
) -> None:
    """Ask, mark solved, Director approves, ask again: the approved case and its follow-up
    question are used (Milestone 5: follow-up learning)."""

    question = {"message": "Client moved office, can I use the document address?"}
    before = client(kb, "rm-session").post(f"/assistant/cases/{CASE_ID}/chat", json=question)
    assert not [s for s in before.json()["sources"] if s["kind"] == "resolution"]

    entry_id = solved(kb, note="ACRA was current; kept the registry value.")
    client(kb, "director-session").post(
        f"/assistant/knowledge/entries/{entry_id}/versions/1/decision", json={"approve": True}
    )

    after = client(kb, "rm-session").post(f"/assistant/cases/{CASE_ID}/chat", json=question)
    body = after.json()
    resolutions = [s for s in body["sources"] if s["kind"] == "resolution"]
    assert [s["entry_id"] for s in resolutions] == [entry_id]
    assert "What about the ownership step for UEN [UEN]?" in body["suggested_questions"]
