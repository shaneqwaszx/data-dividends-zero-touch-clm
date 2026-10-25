"""Milestone 4: feedback from RMs and the Director review loop (maker-checker, permissions)."""

import copy
import re
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from ai_assistant.config import AiAssistantSettings
from ai_assistant.knowledge.ingest import ingest_guidance
from ai_assistant.knowledge.models import Entry, EntryKind, EntryStatus, Visibility
from ai_assistant.knowledge.service import KnowledgeBase
from ai_assistant.knowledge.store import KnowledgeStore
from ai_assistant.knowledge_api import GUIDANCE_ID
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
    # The TEAM_A Director who drafts knowledge from enhancement requests in these tests, so
    # the two above can edit and decide those drafts.
    "drafter-session": _profile("director-drew", "DIRECTOR", ["CASE_ACCESS", "POLICY_APPROVE"]),
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


def client(kb: KnowledgeBase, session: str, *, single_reviewer: bool = False) -> TestClient:
    """A signed-in browser. Two-person review unless ``single_reviewer`` (the POC setting,
    D-083, which defaults to on): these tests prove the two-person rule unchanged."""

    settings = AiAssistantSettings(  # type: ignore[call-arg]
        _env_file=None, llm_enabled=False, knowledge_single_reviewer=single_reviewer
    )
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


def asked(kb: KnowledgeBase, session: str = "rm-session", case_id: str = CASE_ID) -> str:
    """Ask a question as ``session``: the id of the answer record (which feedback rates)."""

    reply = client(kb, session).post(
        f"/assistant/cases/{case_id}/chat", json={"message": "What should I do next?"}
    )
    assert reply.status_code == 200, reply.text
    answer_id = reply.json()["answer_id"]
    assert answer_id
    return str(answer_id)


def not_helpful(kb: KnowledgeBase, note: str = "No proof list.") -> int:
    """An RM's "Not helpful" with a note: an enhancement request. Returns its id."""

    reply = client(kb, "rm-session").post(
        f"/assistant/cases/{CASE_ID}/feedback",
        json={"helpful": False, "note": note, "answer_id": asked(kb)},
    )
    assert reply.status_code == 200, reply.text
    return int(reply.json()["feedback_id"])


def fix(note: str = "Client confirmed ACRA is current.") -> dict[str, Any]:
    """A Director's fix for a request, written as a past resolution."""

    return {"kind": "resolution", "title": "Proof list for moved offices", "body": f"Fix: {note}"}


def drafted(
    kb: KnowledgeBase,
    note: str = "Client confirmed ACRA is current.",
    session: str = "drafter-session",
) -> str:
    """A past resolution pending review: an RM's enhancement request for which a Director
    (by default director-drew) writes the fix. Returns the entry id."""

    feedback_id = not_helpful(kb, note)
    reply = client(kb, session).post(
        f"/assistant/knowledge/feedback/{feedback_id}/draft", json=fix(note)
    )
    assert reply.status_code == 200, reply.text
    return str(reply.json()["entry_id"])


def legacy_rm_draft(kb: KnowledgeBase) -> str:
    """A pending past resolution written by the RM maya-lim, as "Solved it" drafted them
    before D-083. Such drafts can still be in a store, so the author view must keep working."""

    entry = kb.propose(
        Entry(
            entry_id="resolution.legacy-rm",
            kind=EntryKind.RESOLUTION,
            title="Draft: Documents disagree",
            body="What resolved it (RM's note): Client confirmed ACRA is current.",
            blocker_codes=("DOCUMENT_SOURCE_CONFLICT",),
            visibility=Visibility(teams=("TEAM_A",)),
            author="maya-lim",
            source_ref="RM feedback",
        )
    )
    return entry.entry_id


def resolutions(kb: KnowledgeBase) -> list[Entry]:
    return [entry for entry in kb.store.entries() if entry.kind == EntryKind.RESOLUTION]


def test_yes_helpful_only_records_the_rating_with_its_case_context(kb: KnowledgeBase) -> None:
    reply = client(kb, "rm-session").post(
        f"/assistant/cases/{CASE_ID}/feedback", json={"helpful": True, "note": ""}
    )
    assert reply.status_code == 200
    assert reply.json() == {
        "feedback_id": reply.json()["feedback_id"],
        "message": "Thanks for your feedback.",
    }
    # No draft and nothing to review.
    assert resolutions(kb) == []
    queue = client(kb, "director-session").get("/assistant/knowledge/reviews").json()
    assert queue == {"pending": [], "gaps": []}
    (row,) = kb.store.feedback()
    assert row["helpful"] is True and row["entry_id"] is None
    assert "DOCUMENT_SOURCE_CONFLICT" in row["blocker_codes"]
    assert row["fields"] and row["stages"]


def test_not_helpful_starts_a_redacted_enhancement_request(kb: KnowledgeBase) -> None:
    reply = client(kb, "rm-session").post(
        f"/assistant/cases/{CASE_ID}/feedback",
        json={
            "helpful": False,
            "note": " It did not say what proof to ask GARDEN BUSINESS for. ",
            "answer_id": asked(kb),
        },
    )
    assert reply.status_code == 200
    assert reply.json()["message"] == "Thanks. This has been flagged so the answer can be improved."
    assert resolutions(kb) == []
    gaps = client(kb, "director-session").get("/assistant/knowledge/reviews").json()["gaps"]
    assert [gap["note"] for gap in gaps] == ["It did not say what proof to ask [COMPANY] for."]
    assert gaps[0]["status"] == "open" and "DOCUMENT_SOURCE_CONFLICT" in gaps[0]["blocker_codes"]


@pytest.mark.parametrize("note", ["", "   ", "\n\t "], ids=["empty", "spaces", "whitespace"])
def test_not_helpful_needs_a_note(kb: KnowledgeBase, note: str) -> None:
    reply = client(kb, "rm-session").post(
        f"/assistant/cases/{CASE_ID}/feedback",
        json={"helpful": False, "note": note, "answer_id": asked(kb)},
    )
    assert reply.status_code == 422
    assert kb.store.feedback() == []


def test_feedback_no_longer_takes_the_conversation(kb: KnowledgeBase) -> None:
    reply = client(kb, "rm-session").post(
        f"/assistant/cases/{CASE_ID}/feedback",
        json={"helpful": False, "note": "No proof list.", "turns": TURNS, "answer_id": asked(kb)},
    )
    assert reply.status_code == 422
    assert kb.store.feedback() == []


def test_a_directors_fix_is_a_redacted_draft_another_reviewer_approves(
    kb: KnowledgeBase,
) -> None:
    feedback_id = not_helpful(kb, "It did not list the proof to ask for.")
    written = {
        "kind": "resolution",
        "title": "Proof list for GARDEN BUSINESS",
        "body": "Asked Lim Choon Huat at ubo@client.example; GARDEN BUSINESS sent the lease.",
        "follow_ups": ["What about UEN 11111999A?"],
    }
    reply = client(kb, "drafter-session").post(
        f"/assistant/knowledge/feedback/{feedback_id}/draft", json=written
    )
    assert reply.status_code == 200
    draft = reply.json()
    assert draft["status"] == "pending_review" and draft["kind"] == "resolution"
    assert draft["author"] == "director-drew" and draft["visibility"]["teams"] == ["TEAM_A"]
    assert draft["source_ref"] == f"Enhancement request {feedback_id}"
    # The Director's text is redacted against the request's case, then by pattern.
    text = draft["title"] + draft["body"] + " ".join(draft["follow_ups"])
    for secret in ("GARDEN BUSINESS", "ubo@client.example", "Lim Choon Huat", "11111999A"):
        assert secret not in text
    for placeholder in ("[COMPANY]", "[EMAIL]", "[PERSON]"):
        assert placeholder in draft["body"]
    assert draft["follow_ups"] == ["What about UEN [UEN]?"]
    assert "DOCUMENT_SOURCE_CONFLICT" in draft["blocker_codes"]
    assert kb.index.keys(EntryKind.RESOLUTION) == set()  # not searchable until approved
    # The request is linked to the draft and leaves the open list.
    (row,) = kb.store.feedback()
    assert (row["status"], row["entry_id"]) == ("drafted", draft["entry_id"])
    queue = client(kb, "director-session").get("/assistant/knowledge/reviews").json()
    assert queue["gaps"] == [] and [e["entry_id"] for e in queue["pending"]] == [draft["entry_id"]]
    # The two-person rule: the author never decides it; a different reviewer can.
    own = decide(kb, "drafter-session", draft["entry_id"], 1)
    assert own.status_code == 403 and own.json()["detail"]["code"] == "MAKER_CHECKER"
    assert kb.store.feedback()[0]["status"] == "drafted"
    assert decide(kb, "director-session", draft["entry_id"], 1).status_code == 200
    (row,) = kb.store.feedback()
    assert (row["status"], row["closed_by"]) == ("resolved", "director-dan")


def test_approving_an_edited_draft_also_resolves_its_request(kb: KnowledgeBase) -> None:
    entry_id = drafted(kb)
    edited = edit(kb, "director-session", entry_id, 1, title="Proof list for moved offices")
    assert edited.status_code == 200
    assert kb.store.feedback()[0]["status"] == "drafted"  # an edit is not a decision
    assert decide(kb, "director-2-session", entry_id, 2).status_code == 200
    assert kb.store.feedback()[0]["status"] == "resolved"


@pytest.mark.parametrize("version", [1, 2], ids=["draft", "edited-draft"])
def test_rejecting_the_draft_opens_its_request_again(kb: KnowledgeBase, version: int) -> None:
    entry_id = drafted(kb)
    if version == 2:
        edit(kb, "director-session", entry_id, 1, title="Proof list for moved offices")
    assert decide(kb, "director-2-session", entry_id, version, approve=False).status_code == 200
    (row,) = kb.store.feedback()
    assert row["status"] == "open" and row["closed_by"] is None
    gaps = client(kb, "director-session").get("/assistant/knowledge/reviews").json()["gaps"]
    assert [gap["id"] for gap in gaps] == [row["id"]]
    # It can be drafted again, as a new entry.
    again = client(kb, "director-session").post(
        f"/assistant/knowledge/feedback/{row['id']}/draft", json=fix()
    )
    assert again.status_code == 200 and again.json()["entry_id"] != entry_id


def test_closing_a_request_needs_a_reason_and_records_it(kb: KnowledgeBase) -> None:
    feedback_id = not_helpful(kb)
    director = client(kb, "director-session")
    path = f"/assistant/knowledge/feedback/{feedback_id}/close"
    for body in ({}, {"reason": ""}, {"reason": "   "}):
        assert director.post(path, json=body).status_code == 422
    assert kb.store.feedback()[0]["status"] == "open"
    reply = director.post(path, json={"reason": "  Covered by the proof-list guidance. "})
    assert reply.status_code == 200 and reply.json() == {"status": "closed"}
    (row,) = kb.store.feedback()
    assert (row["status"], row["closed_by"]) == ("closed", "director-dan")
    assert row["close_reason"] == "Covered by the proof-list guidance."
    assert director.get("/assistant/knowledge/reviews").json()["gaps"] == []


def test_only_an_open_request_can_be_drafted_or_closed(kb: KnowledgeBase) -> None:
    director = client(kb, "director-session")
    closed = not_helpful(kb)
    director.post(f"/assistant/knowledge/feedback/{closed}/close", json={"reason": "Duplicate."})
    entry_id = drafted(kb)
    pending = next(row["id"] for row in kb.store.feedback() if row["entry_id"] == entry_id)
    for feedback_id in (closed, pending):
        for action, body in (("draft", fix()), ("close", {"reason": "Again."})):
            reply = director.post(
                f"/assistant/knowledge/feedback/{feedback_id}/{action}", json=body
            )
            assert reply.status_code == 409, (feedback_id, action)
            assert reply.json()["detail"] == {
                "code": "CHANGED",
                "message": "This request was already handled. Refresh and try again.",
            }
    assert [entry.entry_id for entry in resolutions(kb)] == [entry_id]
    assert {row["status"] for row in kb.store.feedback()} == {"closed", "drafted"}


def test_a_helpful_rating_or_a_missing_request_is_not_an_enhancement_request(
    kb: KnowledgeBase,
) -> None:
    client(kb, "rm-session").post(
        f"/assistant/cases/{CASE_ID}/feedback", json={"helpful": True, "note": "Great."}
    )
    rating = kb.store.feedback()[0]["id"]
    director = client(kb, "director-session")
    for feedback_id in (rating, 999):
        for action, body in (("draft", fix()), ("close", {"reason": "Not needed."})):
            reply = director.post(
                f"/assistant/knowledge/feedback/{feedback_id}/{action}", json=body
            )
            assert reply.status_code == 404
            assert reply.json()["detail"]["message"] == "No such enhancement request."
    assert kb.store.feedback()[0]["close_reason"] is None and resolutions(kb) == []


def test_only_a_director_handles_enhancement_requests(kb: KnowledgeBase) -> None:
    # HR has no case access: it neither writes the fix nor closes a request.
    feedback_id = not_helpful(kb)
    for session in ("rm-session", "hr-session"):
        c = client(kb, session)
        drafting = c.post(f"/assistant/knowledge/feedback/{feedback_id}/draft", json=fix())
        assert drafting.status_code == 403
        closed = c.post(f"/assistant/knowledge/feedback/{feedback_id}/close", json={"reason": "x"})
        assert closed.status_code == 403
    assert kb.store.feedback()[0]["status"] == "open" and resolutions(kb) == []


def test_stats_show_confidence_by_topic(kb: KnowledgeBase) -> None:
    rm = client(kb, "rm-session")
    for helpful, note in ((True, ""), (True, ""), (False, "No proof list.")):
        rated = rm.post(
            f"/assistant/cases/{CASE_ID}/feedback",
            json={"helpful": helpful, "note": note, "answer_id": asked(kb)},
        )
        assert rated.status_code == 200, rated.text
    codes = kb.store.feedback()[0]["blocker_codes"]
    assert codes  # the synthetic case has blockers
    stats = client(kb, "director-session").get("/assistant/knowledge/stats").json()
    assert stats["feedback"] == {
        "total": 3,
        "helpful": 2,
        "not_helpful": 1,
        "helpful_rate": 0.667,
        "open_gaps": 1,
    }
    assert stats["by_topic"] == {code: {"helpful": 2, "not_helpful": 1} for code in sorted(codes)}
    # A request handled no longer counts as open; the ratings still count.
    gap = kb.store.feedback(helpful=False)[0]["id"]
    client(kb, "director-session").post(
        f"/assistant/knowledge/feedback/{gap}/close", json={"reason": "Duplicate."}
    )
    stats = client(kb, "director-session").get("/assistant/knowledge/stats").json()
    assert stats["feedback"]["open_gaps"] == 0 and stats["feedback"]["total"] == 3


def test_only_a_director_sees_the_review_queue(kb: KnowledgeBase) -> None:
    drafted(kb)
    assert client(kb, "rm-session").get("/assistant/knowledge/reviews").status_code == 403
    assert client(kb, "hr-session").get("/assistant/knowledge/reviews").status_code == 403
    pending = client(kb, "director-session").get("/assistant/knowledge/reviews").json()["pending"]
    assert len(pending) == 1


def test_a_director_edit_is_a_new_version_another_director_must_approve(
    kb: KnowledgeBase,
) -> None:
    entry_id = drafted(kb)
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
    # Append-only: the edit is v2 written by the editor; v1 keeps its own text and author.
    assert revised["version"] == 2 and revised["revises"] == 1
    assert revised["author"] == "director-dan" and revised["status"] == "pending_review"
    kept = kb.store.get(entry_id, 1)
    assert kept.title == original.title and kept.author == "director-drew"
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
    entry_id = drafted(kb)
    assert (
        edit(kb, "director-session", entry_id, 1, title="Tidied title for review").status_code
        == 200
    )
    reply = decide(kb, "drafter-session", entry_id, 2)
    assert reply.status_code == 403 and reply.json()["detail"]["code"] == "MAKER_CHECKER"


def test_a_decision_binds_to_the_content_the_reviewer_saw(kb: KnowledgeBase) -> None:
    entry_id = drafted(kb)
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

    entry_id = drafted(kb)
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
    entry_id = drafted(kb)
    assert decide(kb, "rm-session", entry_id, 1).status_code == 403
    # Even a Director cannot approve an entry they wrote themselves.
    reply = decide(kb, "drafter-session", entry_id, 1)
    assert reply.json()["detail"]["code"] == "MAKER_CHECKER"
    assert reply.status_code == 403 and "you wrote" in reply.json()["detail"]["message"]
    # Nor can an RM who wrote a draft before D-083, once a Director.
    legacy = legacy_rm_draft(kb)
    USERS["self-approver"] = _profile("maya-lim", "DIRECTOR", ["CASE_ACCESS", "POLICY_APPROVE"])
    try:
        reply = decide(kb, "self-approver", legacy, 1)
        assert reply.status_code == 403 and reply.json()["detail"]["code"] == "MAKER_CHECKER"
    finally:
        del USERS["self-approver"]


def test_a_director_from_another_team_sees_and_decides_nothing_of_team_a(
    kb: KnowledgeBase,
) -> None:
    entry_id = drafted(kb)
    not_helpful(kb)
    other = client(kb, "director-b-session")
    queue = other.get("/assistant/knowledge/reviews").json()
    assert queue == {"pending": [], "gaps": []}
    assert other.get(f"/assistant/knowledge/entries/{entry_id}").status_code == 404
    assert decide(kb, "director-b-session", entry_id, 1).status_code == 404
    assert edit(kb, "director-b-session", entry_id, 1, title="Not my team").status_code == 404
    own = client(kb, "director-session").get("/assistant/knowledge/reviews").json()
    assert [e["entry_id"] for e in own["pending"]] == [entry_id] and len(own["gaps"]) == 1
    gap_id = own["gaps"][0]["id"]
    closing = other.post(f"/assistant/knowledge/feedback/{gap_id}/close", json={"reason": "x"})
    assert closing.status_code == 404
    assert (
        other.post(f"/assistant/knowledge/feedback/{gap_id}/draft", json=fix()).status_code == 404
    )
    assert kb.store.feedback(status="open")[0]["id"] == gap_id
    # Once approved, the resolution is searchable for TEAM_A only.
    decide(kb, "director-session", entry_id, 1)
    approved = kb.store.current(entry_id)
    assert approved.visibility.teams == ("TEAM_A",)
    assert approved.visibility.allows("CLIENT_ONBOARDER", "TEAM_A")
    assert not approved.visibility.allows("CLIENT_ONBOARDER", "TEAM_B")
    assert other.get("/assistant/knowledge/entries?kind=resolution").json() == []


def test_an_edit_can_narrow_but_never_widen_team_visibility(kb: KnowledgeBase) -> None:
    entry_id = drafted(kb)
    widened = edit(kb, "director-session", entry_id, 1, visibility={"roles": [], "teams": []})
    assert widened.status_code == 409 and widened.json()["detail"]["code"] == "NOT_ALLOWED"
    other_team = edit(
        kb, "director-session", entry_id, 1, visibility={"roles": [], "teams": ["TEAM_B"]}
    )
    assert other_team.status_code == 409
    assert kb.store.get(entry_id, 1).visibility.teams == ("TEAM_A",)


def test_the_author_can_see_their_own_draft(kb: KnowledgeBase) -> None:
    entry_id = legacy_rm_draft(kb)
    assert (
        client(kb, "rm-session").get(f"/assistant/knowledge/entries/{entry_id}").status_code == 200
    )


def test_the_author_sees_only_the_versions_they_wrote(kb: KnowledgeBase) -> None:
    # QG_PR99_23c452b K5c: no reviewer's edited version and no review notes for the author.
    entry_id = legacy_rm_draft(kb)
    edit(kb, "director-session", entry_id, 1, title="Tidied title written by the Director")
    client(kb, "director-2-session").post(
        f"/assistant/knowledge/entries/{entry_id}/versions/2/decision",
        json={
            "approve": False,
            "content_hash": shown_hash(kb, entry_id, 2),
            "notes": "Private reviewer note",
        },
    )
    own = client(kb, "rm-session").get(f"/assistant/knowledge/entries/{entry_id}")
    assert own.status_code == 200
    assert [v["version"] for v in own.json()["versions"]] == [1]
    assert own.json()["reviews"] == []
    assert "Tidied title" not in own.text and "Private reviewer note" not in own.text
    full = client(kb, "director-session").get(f"/assistant/knowledge/entries/{entry_id}").json()
    assert [v["version"] for v in full["versions"]] == [1, 2]
    assert "Private reviewer note" in [row["notes"] for row in full["reviews"]]
    other = client(kb, "director-b-session").get(f"/assistant/knowledge/entries/{entry_id}")
    assert other.status_code == 404


def test_approving_as_a_replacement_retires_the_older_entry(kb: KnowledgeBase) -> None:
    first = drafted(kb)
    decide(kb, "director-session", first, 1)
    second = drafted(kb, note="Newer, clearer resolution.")
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


def _legacy_kb(
    tmp_path: Path,
    *,
    editor: str = "director-dan",
    title: str = "Director title LEGACYEDITMARK",
    body: str = "Director body LEGACYBODYMARK.",
) -> KnowledgeBase:
    """A schema-v2 store in the shape ad4661c's in-place edit left, opened (migrated) as v3.

    Under schema v2 a Director's edit changed the RM's pending version in place and kept the
    RM as its author; only an 'edit' row records it. ``editor`` made that edit and ``title``
    and ``body`` are what it wrote (the author's own store-level edit left the same shape).
    """

    import sqlite3

    with sqlite3.connect(tmp_path / "knowledge.sqlite3") as db:
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
            "CREATE TABLE reviews (id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " entry_id TEXT NOT NULL, version INTEGER NOT NULL, reviewer TEXT NOT NULL,"
            " decision TEXT NOT NULL CHECK (decision IN ('approve', 'reject', 'retire', 'edit')),"
            " notes TEXT NOT NULL, created_at TEXT NOT NULL,"
            " FOREIGN KEY (entry_id, version) REFERENCES entries (entry_id, version));"
            # The RM's draft as ad4661c's in-place edit left it: the editor's title and body,
            # the RM still the author, and an 'edit' row by the editor.
            "INSERT INTO entries VALUES ('resolution.legacy', 1, 'resolution', 'pending_review',"
            f" '{title}', '{body}', '[]', '[]',"
            " '[]', '{\"roles\": [], \"teams\": [\"TEAM_A\"]}', '[]', NULL, NULL, 'maya-lim',"
            " NULL, NULL, 'RM feedback', 0, 'x', '2026-10-01T00:00:00+00:00');"
            "INSERT INTO reviews (entry_id, version, reviewer, decision, notes, created_at)"
            f" VALUES ('resolution.legacy', 1, '{editor}', 'edit', 'body, title',"
            " '2026-10-01T00:05:00+00:00');"
        )
    return _kb(tmp_path)  # opening the store migrates it to schema v3


def test_the_author_view_leaves_out_a_version_a_reviewer_edited_in_place(
    tmp_path: Path,
) -> None:
    """QG_PR99_6399814 K7."""

    kb = _legacy_kb(tmp_path)
    legacy = kb.store.get("resolution.legacy", 1)
    assert legacy is not None and legacy.author == "maya-lim" and legacy.revises is None
    own = client(kb, "rm-session").get("/assistant/knowledge/entries/resolution.legacy")
    assert own.status_code == 200 and own.json() == {"versions": [], "reviews": []}
    assert "LEGACY" not in own.text and "Director" not in own.text
    # The Director, in the entry's team, still sees the full record.
    full = client(kb, "director-2-session").get("/assistant/knowledge/entries/resolution.legacy")
    assert "LEGACYEDITMARK" in full.text and full.json()["reviews"][0]["decision"] == "edit"


@pytest.mark.parametrize(
    "edits",
    [
        [("director-2-session", 1)],  # another Director edits the legacy draft
        [("director-session", 1)],  # the Director who edited it in place edits it again
        [("director-2-session", 1), ("director-session", 2)],  # a chain v1 -> v2 -> v3
    ],
    ids=["other-director", "same-director", "chain"],
)
def test_a_later_edit_does_not_bring_back_a_version_edited_in_place(
    tmp_path: Path, edits: list[tuple[str, int]]
) -> None:
    """QG_PR99_b037d4e K9: a normal (v3) edit after the migration adds a version that revises
    the legacy one; the legacy version must still stay out of the RM's view."""

    kb = _legacy_kb(tmp_path)
    queue = client(kb, "director-2-session").get("/assistant/knowledge/reviews").json()
    assert "resolution.legacy" in [entry["entry_id"] for entry in queue["pending"]]
    for number, (session, version) in enumerate(edits, start=1):
        reply = edit(kb, session, "resolution.legacy", version, title=f"Tidied title {number}")
        assert reply.status_code == 200 and reply.json()["version"] == version + 1
    own = client(kb, "rm-session").get("/assistant/knowledge/entries/resolution.legacy")
    assert own.status_code == 200 and own.json() == {"versions": [], "reviews": []}
    assert "LEGACY" not in own.text and "Tidied" not in own.text


# The author's own words, written into their draft by their own in-place edit under schema v2.
OWN_TITLE, OWN_BODY = "RM title OWNEDITMARK", "RM body OWNBODYMARK."


def test_a_later_edit_also_leaves_out_the_authors_own_in_place_edit(tmp_path: Path) -> None:
    """QG_PR99_8457f02 G5: the author edited the draft in place under schema v2, then a
    Director edited it normally. The version holds the author's own text but is left out:
    the stated over-hide, on the safe side (ADR-012 section C)."""

    kb = _legacy_kb(tmp_path, editor="maya-lim", title=OWN_TITLE, body=OWN_BODY)
    reply = edit(kb, "director-session", "resolution.legacy", 1, title="Tidied title")
    assert reply.status_code == 200 and reply.json()["version"] == 2
    reviews = kb.store.reviews("resolution.legacy")  # two 'edit' rows on v1; only v2 revises it
    assert [(row["version"], row["reviewer"], row["decision"]) for row in reviews] == [
        (1, "maya-lim", "edit"),
        (1, "director-dan", "edit"),
    ]
    own = client(kb, "rm-session").get("/assistant/knowledge/entries/resolution.legacy")
    assert own.status_code == 200 and own.json() == {"versions": [], "reviews": []}


def test_the_author_still_sees_a_version_only_they_edited_in_place(tmp_path: Path) -> None:
    """QG_PR99_8457f02 G6: the author edited the draft in place under schema v2 and nobody
    else edited it, so the version holds only their own text and stays in their view."""

    kb = _legacy_kb(tmp_path, editor="maya-lim", title=OWN_TITLE, body=OWN_BODY)
    own = client(kb, "rm-session").get("/assistant/knowledge/entries/resolution.legacy")
    assert own.status_code == 200 and own.json()["reviews"] == []
    versions = own.json()["versions"]
    assert [(v["version"], v["author"], v["title"], v["body"]) for v in versions] == [
        (1, "maya-lim", OWN_TITLE, OWN_BODY)
    ]


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("\u0410pprove \u00fcn\u00efcode title", "guidance.pprove-n-code-title"),
        ("Registered address: a new rule!", "guidance.registered-address-a-new-rule"),
    ],
)
def test_a_guidance_id_from_a_title_uses_ascii_letters_and_digits_only(
    kb: KnowledgeBase, title: str, expected: str
) -> None:
    # QG_PR99_23c452b K5b: a Cyrillic title once gave a non-ASCII id.
    reply = client(kb, "hr-session").post(
        "/assistant/knowledge/guidance",
        json={"title": title, "body": "A new rule written for this test.", "source_ref": "D-030"},
    )
    assert reply.status_code == 200 and reply.json()["entry_id"] == expected
    assert re.fullmatch(GUIDANCE_ID, expected)


@pytest.mark.parametrize(
    "title", ["\u0423\u0442\u0432\u0435\u0440\u0434\u0438\u0442\u044c", "ab \u00e9\u00e9"]
)
def test_a_title_without_enough_ascii_needs_an_entry_id(kb: KnowledgeBase, title: str) -> None:
    before = len(kb.store.entries())
    reply = client(kb, "hr-session").post(
        "/assistant/knowledge/guidance",
        json={"title": title, "body": "A new rule written for this test.", "source_ref": "D-030"},
    )
    assert reply.status_code == 422 and reply.json()["detail"]["code"] == "INVALID_ENTRY_ID"
    assert len(kb.store.entries()) == before


def test_rm_cannot_propose_guidance(kb: KnowledgeBase) -> None:
    reply = client(kb, "rm-session").post(
        "/assistant/knowledge/guidance",
        json={"title": "My rule", "body": "Something I made up today.", "source_ref": "none"},
    )
    assert reply.status_code == 403


def test_directors_can_retire_with_two_people_and_see_stats(kb: KnowledgeBase) -> None:
    # Retiring takes two reviewers since the second independent gate (G2 on 79621fe): the
    # first request leaves the entry current, a different Director's request retires it.
    director = client(kb, "director-session")
    retire = "/assistant/knowledge/entries/guidance.environments/retire"
    first = director.post(retire, json={"notes": "outdated"})
    assert first.status_code == 200 and first.json()["retirement"] == "requested"
    assert kb.store.current("guidance.environments") is not None
    second = client(kb, "director-2-session").post(retire, json={"notes": "agreed, outdated"})
    assert second.status_code == 200 and second.json()["retirement"] == "done"
    assert kb.store.current("guidance.environments") is None
    rated = client(kb, "rm-session").post(
        f"/assistant/cases/{CASE_ID}/feedback", json={"helpful": True, "note": ""}
    )
    assert rated.status_code == 200
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
        "single_reviewer": False,
    }


# Seeding uses the current store; an older shape has none of the schema v5 tables.
DROP_V5_TABLES = "DROP TABLE answer_record_views; DROP TABLE answer_records;"


def test_a_store_from_before_this_change_is_migrated(tmp_path: Path) -> None:
    import sqlite3

    path = tmp_path / "old.sqlite3"
    KnowledgeStore(path)
    with sqlite3.connect(path) as db:
        db.executescript(DROP_V5_TABLES)
        db.execute("UPDATE meta SET value = '1' WHERE key = 'schema_version'")
    store = KnowledgeStore(path)  # migrates
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == "5"
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


# The feedback table of schema v1 to v3: no 'resolved' status and no close reason.
V3_FEEDBACK = (
    "CREATE TABLE feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL,"
    " user_id TEXT NOT NULL, role TEXT, team TEXT, helpful INTEGER NOT NULL, note TEXT NOT NULL,"
    " blocker_codes TEXT NOT NULL, fields TEXT NOT NULL, stages TEXT NOT NULL, entry_id TEXT,"
    " status TEXT NOT NULL CHECK (status IN ('open', 'drafted', 'closed')),"
    " created_at TEXT NOT NULL, closed_by TEXT, closed_at TEXT);"
)


# The reviews table of schema v2 and v3: no single-reviewer mark.
V3_REVIEWS = (
    "CREATE TABLE reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, entry_id TEXT NOT NULL,"
    " version INTEGER NOT NULL, reviewer TEXT NOT NULL, decision TEXT NOT NULL"
    " CHECK (decision IN ('approve', 'reject', 'retire', 'edit')), notes TEXT NOT NULL,"
    " created_at TEXT NOT NULL,"
    " FOREIGN KEY (entry_id, version) REFERENCES entries (entry_id, version));"
)


def test_a_version_3_store_gains_request_statuses_and_close_reasons(tmp_path: Path) -> None:
    import sqlite3

    path = tmp_path / "v3.sqlite3"
    seeded = KnowledgeStore(path)
    rule = seeded.add_version(
        Entry(
            entry_id="guidance.rule",
            kind=EntryKind.GUIDANCE,
            title="Rule",
            body="A rule for the demo.",
            author="hr-hana",
        )
    )
    seeded.decide(rule.entry_id, 1, reviewer="director-dan", approve=True)
    with sqlite3.connect(path) as db:
        db.executescript(
            DROP_V5_TABLES
            + "ALTER TABLE reviews RENAME TO reviews_v4;"
            + V3_REVIEWS
            + "INSERT INTO reviews SELECT id, entry_id, version, reviewer, decision, notes,"
            " created_at FROM reviews_v4; DROP TABLE reviews_v4;"
            "DROP TABLE feedback;"
            + V3_FEEDBACK
            + "UPDATE meta SET value = '3' WHERE key = 'schema_version';"
            "INSERT INTO feedback (case_id, user_id, role, team, helpful, note, blocker_codes,"
            " fields, stages, entry_id, status, created_at, closed_by, closed_at) VALUES"
            " ('c1', 'maya-lim', 'CLIENT_ONBOARDER', 'TEAM_A', 1, 'Solved.', '[\"B1\"]', '[]',"
            "  '[]', 'resolution.old', 'drafted', '2026-10-01T00:00:00+00:00', NULL, NULL),"
            " ('c1', 'maya-lim', 'CLIENT_ONBOARDER', 'TEAM_A', 0, 'No proof list.', '[\"B1\"]',"
            "  '[\"f\"]', '[\"s\"]', NULL, 'open', '2026-10-02T00:00:00+00:00', NULL, NULL),"
            " ('c2', 'ravi', NULL, NULL, 0, 'Handled.', '[]', '[]', '[]', NULL, 'closed',"
            "  '2026-10-03T00:00:00+00:00', 'director-dan', '2026-10-04T00:00:00+00:00');"
        )
        before = [tuple(row) for row in db.execute("SELECT * FROM feedback ORDER BY id")]
    store = KnowledgeStore(path)  # migrates
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == "5"
        after = [tuple(row) for row in db.execute("SELECT * FROM feedback ORDER BY id")]
        assert (
            db.execute("SELECT name FROM sqlite_master WHERE name = 'feedback_v3'").fetchone()
            is None
        )
    # Every row keeps its values; none has a close reason or a linked fix version, and no
    # earlier decision was a single-reviewer one.
    assert after == [(*row, None, None) for row in before]
    assert [(r["decision"], r["single_reviewer"]) for r in store.reviews("guidance.rule")] == [
        ("approve", False)
    ]
    assert store.single_reviewer_approvals() == set()
    # The open request can now be closed with a reason; new rows continue the ids.
    store.close_feedback(2, by="director-dan", reason="Covered by guidance.")
    assert store.feedback(status="closed", helpful=False)[0]["close_reason"] == (
        "Covered by guidance."
    )
    new_id = store.add_feedback(
        case_id="c3",
        user_id="maya-lim",
        role=None,
        team="TEAM_A",
        helpful=False,
        note="Missing.",
        blocker_codes=(),
        fields=(),
        stages=(),
        entry_id=None,
    )
    assert new_id == 4
    # The status check still holds after the rebuild.
    with sqlite3.connect(path) as db, pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE feedback SET status = 'unknown' WHERE id = 4")
    # Opening the migrated store again changes nothing.
    KnowledgeStore(path)
    assert [row["id"] for row in store.feedback()] == [1, 2, 3, 4]


def test_the_whole_loop_a_resolved_case_helps_the_next_similar_question(
    kb: KnowledgeBase,
) -> None:
    """Ask, mark not helpful with a note, a Director drafts knowledge from it and adds a
    follow-up question, another approves, ask again: the approved case and its follow-up
    question are used (Milestone 5: follow-up learning)."""

    question = {"message": "Client moved office, can I use the document address?"}
    before = client(kb, "rm-session").post(f"/assistant/cases/{CASE_ID}/chat", json=question)
    assert not [s for s in before.json()["sources"] if s["kind"] == "resolution"]

    entry_id = drafted(kb, note="ACRA was current; kept the registry value.")
    follow_up = "What about the ownership step for UEN [UEN]?"
    assert edit(kb, "director-session", entry_id, 1, follow_ups=[follow_up]).status_code == 200
    assert decide(kb, "director-2-session", entry_id, 2).status_code == 200

    after = client(kb, "rm-session").post(f"/assistant/cases/{CASE_ID}/chat", json=question)
    body = after.json()
    resolutions = [s for s in body["sources"] if s["kind"] == "resolution"]
    assert [(s["tag"], s["title"]) for s in resolutions] == [("P1", kb.store.get(entry_id).title)]
    assert follow_up in body["suggested_questions"]


# Stores written by earlier builds of this branch (never on main) are stamped schema 4 but lack
# v4 columns: 6d090a7 has neither reviews.single_reviewer nor feedback.entry_version, 81a59c2
# lacks feedback.entry_version (independent gate R1-F1 on 0ed9055).
EARLY_V4_SHAPES = {
    "6d090a7": "ALTER TABLE reviews DROP COLUMN single_reviewer;"
    " ALTER TABLE feedback DROP COLUMN entry_version;",
    "81a59c2": "ALTER TABLE feedback DROP COLUMN entry_version;",
}


@pytest.mark.parametrize("shape", EARLY_V4_SHAPES)
def test_a_branch_only_v4_store_gains_its_missing_columns(tmp_path: Path, shape: str) -> None:
    import sqlite3

    path = tmp_path / f"{shape}.sqlite3"
    seeded = KnowledgeStore(path)
    request_id = seeded.add_feedback(
        case_id="c1",
        user_id="maya-lim",
        role="CLIENT_ONBOARDER",
        team="TEAM_A",
        helpful=False,
        note="No proof list.",
        blocker_codes=("B1",),
        fields=(),
        stages=(),
        entry_id=None,
    )
    with sqlite3.connect(path) as db:
        # A v4 store: no v5 tables, stamped '4', and missing this shape's v4 columns.
        db.executescript(
            DROP_V5_TABLES
            + "UPDATE meta SET value = '4' WHERE key = 'schema_version';"
            + EARLY_V4_SHAPES[shape]
        )
        assert db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == "4"
    store = KnowledgeStore(path)  # repairs
    with sqlite3.connect(path) as db:
        feedback = {row[1] for row in db.execute("PRAGMA table_info(feedback)")}
        reviews = {row[1] for row in db.execute("PRAGMA table_info(reviews)")}
    assert {"close_reason", "entry_version"} <= feedback and "single_reviewer" in reviews
    assert [row["id"] for row in store.feedback()] == [request_id]
    # What failed before the repair: listing single-reviewer approvals, writing a fix (it
    # records the fix version), and deciding it.
    assert store.single_reviewer_approvals() == set()
    fix = store.draft_request(
        request_id,
        lambda row: Entry(
            entry_id="resolution.fix",
            kind=EntryKind.RESOLUTION,
            title="Fix",
            body=str(row["note"]),
            author="olivia-koh",
        ),
    )
    store.decide(
        fix.entry_id,
        fix.version,
        reviewer="olivia-koh",
        approve=True,
        single_reviewer=True,
        confirmed=True,
    )
    assert store.single_reviewer_approvals() == {fix.key}
    assert store.feedback()[0]["status"] == "resolved"
    KnowledgeStore(path)  # opening again changes nothing
    assert [row["status"] for row in KnowledgeStore(path).feedback()] == ["resolved"]


def guidance_fix_for(kb: KnowledgeBase, session: str, entry_id: str) -> tuple[int, int]:
    """An RM's request whose fix ``session`` writes as a new version of ``entry_id``.
    Returns (request id, fix version)."""

    request_id = not_helpful(kb)
    reply = client(kb, session).post(
        f"/assistant/knowledge/feedback/{request_id}/draft",
        json={
            "kind": "guidance",
            "entry_id": entry_id,
            "title": "Ask for the tenancy agreement first",
            "body": "When the registered office moved, ask for the tenancy agreement first.",
            "source_ref": "docs/decisions/DECISION_LOG.md#D-030",
        },
    )
    assert reply.status_code == 200, reply.text
    return request_id, int(reply.json()["version"])


def statuses(kb: KnowledgeBase) -> dict[int, str]:
    return {row["id"]: row["status"] for row in kb.store.feedback(helpful=False)}


def test_two_requests_fixed_in_the_same_guidance_are_resolved_by_their_own_versions(
    kb: KnowledgeBase,
) -> None:
    """QG F1 on 81a59c2: a decision on one version changed every request linked to the id."""

    guidance = "guidance.address-mismatch"
    first, first_version = guidance_fix_for(kb, "drafter-session", guidance)
    second, second_version = guidance_fix_for(kb, "drafter-session", guidance)
    links = {row["id"]: row["entry_version"] for row in kb.store.feedback()}
    assert links == {first: first_version, second: second_version}
    assert decide(kb, "director-session", guidance, first_version).status_code == 200
    assert statuses(kb) == {first: "resolved", second: "drafted"}
    assert (
        decide(kb, "director-session", guidance, second_version, approve=False).status_code == 200
    )
    assert statuses(kb) == {first: "resolved", second: "open"}
    gaps = client(kb, "director-session").get("/assistant/knowledge/reviews").json()["gaps"]
    assert [gap["id"] for gap in gaps] == [second]


def test_a_decision_on_another_version_of_the_guidance_leaves_the_request_alone(
    kb: KnowledgeBase,
) -> None:
    guidance = "guidance.address-mismatch"
    request_id, fix_version = guidance_fix_for(kb, "drafter-session", guidance)
    current = kb.store.current(guidance)
    assert current is not None
    for approve in (False, True):
        hr = kb.propose(
            current.with_changes(body=f"HR's own wording, approve={approve}.", author="hr-hana")
        )
        assert (
            decide(kb, "director-session", guidance, hr.version, approve=approve).status_code == 200
        )
        assert statuses(kb) == {request_id: "drafted"}
    # Only the fix's own version resolves it, and a reviewer's edit carries the link along.
    edited = edit(kb, "director-session", guidance, fix_version, title="Tidied by the Director")
    assert edited.status_code == 200
    (row,) = kb.store.feedback(helpful=False)
    assert row["entry_version"] == edited.json()["version"]
    assert decide(kb, "director-2-session", guidance, edited.json()["version"]).status_code == 200
    assert statuses(kb) == {request_id: "resolved"}


def test_a_guidance_fix_takes_scope_and_visibility_from_the_current_approved_version(
    kb: KnowledgeBase,
) -> None:
    """QG F3 on 81a59c2: the newest (pending) version was used instead."""

    rule = Entry(
        entry_id="guidance.team-b-rule",
        kind=EntryKind.GUIDANCE,
        title="Team B rule",
        body="A rule only Team B follows.",
        visibility=Visibility(teams=("TEAM_B",)),
        author="hr-hana",
        source_ref="D-030",
    )
    approved = kb.propose(rule)
    assert decide(kb, "director-b-session", rule.entry_id, approved.version).status_code == 200
    # A pending version visible to TEAM_A does not bring the rule into TEAM_A's scope.
    kb.propose(
        rule.with_changes(
            body="A pending rewrite for Team A.", visibility=Visibility(teams=("TEAM_A",))
        )
    )
    request_id = not_helpful(kb)
    body = {
        "kind": "guidance",
        "entry_id": rule.entry_id,
        "title": "Team B rule, clarified",
        "body": "A clarified rule only Team B follows.",
        "source_ref": "D-030",
    }
    refused = client(kb, "director-session").post(
        f"/assistant/knowledge/feedback/{request_id}/draft", json=body
    )
    assert refused.status_code == 404
    assert statuses(kb) == {request_id: "open"}
    # A reviewer who sees the current version inherits its visibility, not the pending one's.
    USERS["director-ab-session"] = _profile(
        "director-abe", "DIRECTOR", ["CASE_ACCESS", "POLICY_APPROVE"], team=None
    )  # type: ignore[arg-type]
    try:
        written = client(kb, "director-ab-session").post(
            f"/assistant/knowledge/feedback/{request_id}/draft", json=body
        )
        assert written.status_code == 200, written.text
        assert written.json()["visibility"]["teams"] == ["TEAM_B"]
    finally:
        del USERS["director-ab-session"]
