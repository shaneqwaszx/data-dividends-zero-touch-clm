"""PR #99 panel evidence D1: the CLM backend makes every Director global (a Director has no
team), so a Director reviews every team's drafts and gaps. Everyone else keeps the team rule.
The fictional TEAM_A/TEAM_B Directors of test_knowledge_review are team-scoped reviewers."""

import copy
from typing import Any

import httpx
import pytest

import tests.test_knowledge_review as review
from ai_assistant.knowledge.models import EntryStatus
from ai_assistant.knowledge.service import KnowledgeBase
from tests.test_ai_assistant import CASE_ID, DOCUMENTS, ME, SUMMARY, _session
from tests.test_knowledge_review import client, decide, drafted, edit, fix, kb  # noqa: F401

TEAM_B_CASE_ID = "5d0c3a4e-6f1b-4c2d-9e8f-7a6b5c4d3e2f"


def _backend_profile(
    user_id: str, role: str, team: str | None, capabilities: list[str]
) -> dict[str, Any]:
    """An /api/auth/me reply in the backend's shape (app/domain/access.py UserProfile)."""

    me = copy.deepcopy(ME)
    me["profile"].update(
        user_id=user_id,
        display_name=user_id.replace("-", " ").title(),
        role=role,
        team_id=team,
        team_display_name={"TEAM_A": "Alpha", "TEAM_B": "Beta"}.get(team or ""),
        team_type="Corporate Client Onboarding" if team else None,
        capabilities=capabilities,
    )
    return me


SUPPORT_CAPABILITIES = [
    "POLICY_VIEW",
    "KNOWLEDGE_REVIEW",
    "KNOWLEDGE_CASE_READ",
]
BACKEND_USERS = {
    # The backend's seeded Support reviewer: role SUPPORT, team_id None (D-099).
    "director-global-session": _backend_profile(
        "support-user", "SUPPORT", None, SUPPORT_CAPABILITIES
    ),
    # A second global Support reviewer, for the two-person steps.
    "director-global-2-session": _backend_profile(
        "support-gus", "SUPPORT", None, SUPPORT_CAPABILITIES
    ),
    # The backend's seeded Director keeps policy approval but no longer reviews knowledge.
    "director-policy-session": _backend_profile(
        "olivia-koh",
        "DIRECTOR",
        None,
        ["POLICY_VIEW", "POLICY_APPROVE", "CASE_ACCESS", "CASE_GLOBAL", "TARGET_RECOVERY"],
    ),
    "rm-b-session": _backend_profile(
        "ryan-lee", "RELATIONSHIP_MANAGER", "TEAM_B", ["POLICY_VIEW", "CASE_ACCESS"]
    ),
    "hr-global-session": _backend_profile(
        "hr-admin", "HR", None, ["POLICY_VIEW", "POLICY_MUTATE", "IDENTITY_ADMIN", "TEAM_ADMIN"]
    ),
}


DIRECTOR_SESSIONS = {"director-b-session", "director-global-session", "director-global-2-session"}


@pytest.fixture(autouse=True)
def backend_users(monkeypatch: pytest.MonkeyPatch) -> None:
    for session, user in BACKEND_USERS.items():
        monkeypatch.setitem(review.USERS, session, user)
    real_handler = review.handler

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if _session(request) == "rm-b-session" and path != "/api/auth/me":
            # The backend's team scope: the TEAM_B RM reaches TEAM_B's case only.
            if path == f"/api/clm/zero-touch/cases/{TEAM_B_CASE_ID}":
                return httpx.Response(200, json=SUMMARY)
            if path == f"/api/onboarding/cases/{TEAM_B_CASE_ID}/documents":
                return httpx.Response(200, json=DOCUMENTS)
            return httpx.Response(404, json={"detail": "not found"})
        if _session(request) in DIRECTOR_SESSIONS:
            # Directors reach TEAM_B's case too (the fix is redacted against it).
            if path == f"/api/clm/zero-touch/cases/{TEAM_B_CASE_ID}":
                return httpx.Response(200, json=SUMMARY)
            if path == f"/api/onboarding/cases/{TEAM_B_CASE_ID}/documents":
                return httpx.Response(200, json=DOCUMENTS)
        return real_handler(request)

    monkeypatch.setattr(review, "handler", handler)


def drafted_in_team_b(kb: KnowledgeBase, session: str = "director-b-session") -> str:  # noqa: F811
    """A TEAM_B RM's enhancement request, drafted into knowledge by ``session``."""

    reply = client(kb, "rm-b-session").post(
        f"/assistant/cases/{TEAM_B_CASE_ID}/feedback",
        json={"helpful": False, "note": "Kept the registry value."},
    )
    assert reply.status_code == 200, reply.text
    feedback_id = reply.json()["feedback_id"]
    drafted = client(kb, session).post(
        f"/assistant/knowledge/feedback/{feedback_id}/draft", json=fix()
    )
    assert drafted.status_code == 200, drafted.text
    return str(drafted.json()["entry_id"])


def not_helpful(kb: KnowledgeBase, session: str, case_id: str) -> None:  # noqa: F811
    reply = client(kb, session).post(
        f"/assistant/cases/{case_id}/feedback", json={"helpful": False, "note": "No proof list."}
    )
    assert reply.status_code == 200, reply.text


def test_a_global_director_sees_every_teams_drafts_gaps_and_stats(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    team_a, team_b = drafted(kb), drafted_in_team_b(kb)
    not_helpful(kb, "rm-session", CASE_ID)
    not_helpful(kb, "rm-b-session", TEAM_B_CASE_ID)
    director = client(kb, "director-global-session")
    queue = director.get("/assistant/knowledge/reviews").json()
    assert sorted(e["entry_id"] for e in queue["pending"]) == sorted([team_a, team_b])
    assert sorted(gap["team"] for gap in queue["gaps"]) == ["TEAM_A", "TEAM_B"]
    stats = director.get("/assistant/knowledge/stats").json()
    assert stats["entries"]["resolution_pending_review"] == 2
    assert stats["feedback"]["total"] == 4 and stats["feedback"]["open_gaps"] == 2
    full = director.get(f"/assistant/knowledge/entries/{team_b}")
    assert full.status_code == 200 and [v["version"] for v in full.json()["versions"]] == [1]
    # A team-scoped reviewer keeps the team rule.
    own_a = client(kb, "director-session").get("/assistant/knowledge/reviews").json()
    own_b = client(kb, "director-b-session").get("/assistant/knowledge/reviews").json()
    assert [e["entry_id"] for e in own_a["pending"]] == [team_a]
    assert [e["entry_id"] for e in own_b["pending"]] == [team_b]
    assert [gap["team"] for gap in own_b["gaps"]] == ["TEAM_B"]
    gap_b = next(gap["id"] for gap in queue["gaps"] if gap["team"] == "TEAM_B")
    closed = director.post(f"/assistant/knowledge/feedback/{gap_b}/close", json={"reason": "Dup."})
    assert closed.status_code == 200 and closed.json() == {"status": "closed"}
    still_open = [row["team"] for row in kb.store.feedback(status="open")]
    assert still_open == ["TEAM_A"]


def test_a_global_director_approves_a_team_a_rm_draft_with_the_shown_hash(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    entry_id = drafted(kb)
    director = client(kb, "director-global-session")
    shown = next(
        e
        for e in director.get("/assistant/knowledge/reviews").json()["pending"]
        if e["entry_id"] == entry_id
    )
    reply = director.post(
        f"/assistant/knowledge/entries/{entry_id}/versions/1/decision",
        json={"approve": True, "content_hash": shown["content_hash"]},
    )
    assert reply.status_code == 200, reply.text
    assert reply.json()["status"] == "approved" and reply.json()["approver"] == "support-user"
    # Approval does not widen who may search it: TEAM_A only.
    approved = kb.store.current(entry_id)
    assert approved is not None and approved.visibility.teams == ("TEAM_A",)
    listed = director.get("/assistant/knowledge/entries?kind=resolution").json()
    assert [e["entry_id"] for e in listed] == [entry_id]
    # HR, also global in the backend, keeps the team rule.
    hr = client(kb, "hr-global-session")
    assert hr.get("/assistant/knowledge/entries?kind=resolution").json() == []
    assert hr.get(f"/assistant/knowledge/entries/{entry_id}").status_code == 404


def test_a_global_director_cannot_decide_a_version_it_edited(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    entry_id = drafted(kb)
    widened = edit(
        kb, "director-global-session", entry_id, 1, visibility={"roles": [], "teams": []}
    )
    assert widened.status_code == 409 and widened.json()["detail"]["code"] == "NOT_ALLOWED"
    edited = edit(kb, "director-global-session", entry_id, 1, title="Tidied by the Director")
    assert edited.status_code == 200 and edited.json()["version"] == 2
    assert edited.json()["author"] == "support-user"
    refused = decide(kb, "director-global-session", entry_id, 2)
    assert refused.status_code == 403 and refused.json()["detail"]["code"] == "MAKER_CHECKER"
    approved = decide(kb, "director-global-2-session", entry_id, 2)
    assert approved.status_code == 200 and approved.json()["approver"] == "support-gus"


def test_a_team_b_rm_still_cannot_read_list_or_decide_a_team_a_draft(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    entry_id = drafted(kb)
    rm_b = client(kb, "rm-b-session")
    assert rm_b.get(f"/assistant/knowledge/entries/{entry_id}").status_code == 403
    assert rm_b.get("/assistant/knowledge/reviews").status_code == 403
    assert decide(kb, "rm-b-session", entry_id, 1).status_code == 403
    assert rm_b.get(f"/assistant/cases/{CASE_ID}/brief").status_code == 404
    assert kb.store.get(entry_id, 1).status == EntryStatus.PENDING_REVIEW


def test_a_global_director_drafts_a_team_b_request_visible_to_team_b_only(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    # The draft takes the team the request came from, not the drafting Director's (none).
    entry_id = drafted_in_team_b(kb, session="director-global-session")
    draft = kb.store.get(entry_id, 1)
    assert draft is not None and draft.author == "support-user"
    assert draft.visibility.teams == ("TEAM_B",)
    assert (
        client(kb, "director-session").get(f"/assistant/knowledge/entries/{entry_id}").status_code
        == 404
    )
    approved = decide(kb, "director-b-session", entry_id, 1)
    assert approved.status_code == 200, approved.text
    assert [row["status"] for row in kb.store.feedback()] == ["resolved"]


def test_the_full_flow_with_the_real_synthetic_roles(kb: KnowledgeBase) -> None:  # noqa: F811
    """RM maya-lim says "Not helpful"; the one Support reviewer, support-user, writes the fix
    and, in the POC's single-reviewer mode, publishes it after confirming; the request is resolved
    and the next similar question cites it. HR (hr-admin) cannot write the fix."""

    question = {"message": "Client moved office, can I use the document address?"}
    rm = client(kb, "rm-session", single_reviewer=True)
    reply = rm.post(
        f"/assistant/cases/{CASE_ID}/feedback",
        json={"helpful": False, "note": "It did not say which proof to ask for."},
    )
    assert reply.status_code == 200
    request_id = reply.json()["feedback_id"]

    hr = client(kb, "hr-global-session", single_reviewer=True)
    path = f"/assistant/knowledge/feedback/{request_id}/draft"
    assert hr.post(path, json=fix()).status_code == 403

    olivia = client(kb, "director-global-session", single_reviewer=True)
    gaps = olivia.get("/assistant/knowledge/reviews").json()["gaps"]
    assert [gap["id"] for gap in gaps] == [request_id]
    written = olivia.post(
        path,
        json={
            "kind": "resolution",
            "title": "Moved office: keep the registry address",
            "body": "ACRA was current; kept the registry value and asked for the lease.",
        },
    )
    assert written.status_code == 200, written.text
    entry = written.json()
    assert entry["author"] == "support-user"

    def publish(confirm: bool) -> httpx.Response:
        return olivia.post(
            f"/assistant/knowledge/entries/{entry['entry_id']}/versions/1/decision",
            json={
                "approve": True,
                "content_hash": entry["content_hash"],
                "confirm_single_reviewer": confirm,
            },
        )

    assert publish(False).json()["detail"]["code"] == "CONFIRM_SINGLE_REVIEWER"
    published = publish(True)
    assert published.status_code == 200, published.text
    assert published.json()["approver"] == "support-user"
    assert published.json()["single_reviewer"] is True
    assert [(r["reviewer"], r["single_reviewer"]) for r in kb.store.reviews(entry["entry_id"])] == [
        ("support-user", True)
    ]
    (row,) = kb.store.feedback()
    assert (row["status"], row["closed_by"]) == ("resolved", "support-user")
    sources = rm.post(f"/assistant/cases/{CASE_ID}/chat", json=question).json()["sources"]
    assert [s["title"] for s in sources if s["kind"] == "resolution"] == [entry["title"]]


def test_with_two_person_review_the_only_director_cannot_publish_her_own_fix(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    rm = client(kb, "rm-session")
    request_id = rm.post(
        f"/assistant/cases/{CASE_ID}/feedback", json={"helpful": False, "note": "No proof list."}
    ).json()["feedback_id"]
    olivia = client(kb, "director-global-session")
    entry = olivia.post(f"/assistant/knowledge/feedback/{request_id}/draft", json=fix()).json()
    refused = olivia.post(
        f"/assistant/knowledge/entries/{entry['entry_id']}/versions/1/decision",
        json={
            "approve": True,
            "content_hash": entry["content_hash"],
            "confirm_single_reviewer": True,
        },
    )
    assert refused.status_code == 403 and refused.json()["detail"]["code"] == "MAKER_CHECKER"
    assert kb.store.feedback()[0]["status"] == "drafted"


def test_a_director_with_policy_approval_cannot_review_knowledge(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    """D-099: knowledge review is KNOWLEDGE_REVIEW (Support), not POLICY_APPROVE."""

    entry_id = drafted(kb)
    director = client(kb, "director-policy-session")
    assert director.get("/assistant/knowledge/me").json()["can_review"] is False
    for path in ("/assistant/knowledge/reviews", "/assistant/knowledge/stats"):
        assert director.get(path).status_code == 403
    refused = director.post(
        f"/assistant/knowledge/entries/{entry_id}/versions/1/decision",
        json={"approve": True, "content_hash": "0" * 64},
    )
    assert refused.status_code == 403
    assert kb.store.current(entry_id) is None
    support = client(kb, "director-global-session")
    assert support.get("/assistant/knowledge/me").json()["can_review"] is True
