"""D-100: conversations, the End conversation rating, history, Support's review list and drafts,
and Support's chat without a case (approved rules and the active policy only)."""

from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

import tests.test_knowledge_review as review
from ai_assistant.config import AiAssistantSettings
from ai_assistant.knowledge.service import KnowledgeBase
from ai_assistant.main import create_app
from ai_assistant.support_chat import NOTHING_FOUND, policy_lines, select_lines
from tests.test_ai_assistant import CASE_ID, ORIGIN, FakeModel
from tests.test_knowledge_review import _profile, kb  # noqa: F401 - kb is a pytest fixture

SUPPORT_CAPABILITIES = ["POLICY_VIEW", "KNOWLEDGE_REVIEW", "KNOWLEDGE_CASE_READ"]
QUESTION = "Tell me about this case."
CATALOGUE = {
    "rules": [
        {
            "policy_id": "ownership.ubo_threshold_percent",
            "name": "UBO threshold",
            "description": "Ownership at or above this percentage makes a beneficial owner.",
            "value": "25",
        },
        {
            "policy_id": "registry.cache_enabled",
            "name": "Registry cache",
            "description": "Reuse a fresh registry snapshot.",
            "value": True,
        },
    ]
}


@pytest.fixture(autouse=True)
def users(monkeypatch: pytest.MonkeyPatch) -> None:
    support = _profile("support-user", "SUPPORT", SUPPORT_CAPABILITIES, team=None)  # type: ignore[arg-type]
    monkeypatch.setitem(review.USERS, "support-session", support)
    monkeypatch.setitem(
        review.USERS,
        "rm-2-session",
        _profile("ravi-tan", "RELATIONSHIP_MANAGER", ["CASE_ACCESS", "POLICY_VIEW"]),
    )
    real_handler = review.handler

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/policies" and review.USERS.get(
            request.headers.get("cookie", "").split("clm_session=")[-1].split(";")[0]
        ):
            return httpx.Response(200, json=CATALOGUE)
        return real_handler(request)

    monkeypatch.setattr(review, "handler", handler)


def app_client(
    kb: KnowledgeBase,  # noqa: F811
    session: str,
    model: FakeModel | None = None,
) -> TestClient:
    config = AiAssistantSettings(  # type: ignore[call-arg]
        _env_file=None, llm_enabled=False, knowledge_single_reviewer=True
    )
    app = create_app(
        config,
        clm_transport=httpx.MockTransport(lambda request: review.handler(request)),
        chat_model=model,
        knowledge=kb,
    )
    c = TestClient(app, headers={"Origin": ORIGIN})
    c.cookies.set("clm_session", session)
    return c


def ask(kb: KnowledgeBase, session: str = "rm-session", **body: Any) -> dict[str, Any]:  # noqa: F811
    reply = app_client(kb, session).post(
        f"/assistant/cases/{CASE_ID}/chat", json={"message": QUESTION, **body}
    )
    assert reply.status_code == 200, reply.text
    return dict(reply.json())


def end(
    kb: KnowledgeBase,  # noqa: F811
    conversation_id: str,
    session: str = "rm-session",
    **body: Any,
) -> httpx.Response:
    return app_client(kb, session).post(
        f"/assistant/conversations/{conversation_id}/end", json=body
    )


def rated(kb: KnowledgeBase, satisfaction: str, resolved: bool, comment: str = "Better.") -> str:  # noqa: F811
    first = ask(kb)
    ask(kb, conversation_id=first["conversation_id"])
    reply = end(
        kb, first["conversation_id"], resolved=resolved, satisfaction=satisfaction, comment=comment
    )
    assert reply.status_code == 200, reply.text
    return str(first["conversation_id"])


# --- conversations and the rating --------------------------------------------------------


def test_answers_join_the_users_open_conversation_only(kb: KnowledgeBase) -> None:  # noqa: F811
    first = ask(kb)
    assert first["conversation_id"]
    again = ask(kb, conversation_id=first["conversation_id"])
    assert again["conversation_id"] == first["conversation_id"]
    # Someone else's conversation id is not joined: a new conversation starts.
    other = ask(kb, session="rm-2-session", conversation_id=first["conversation_id"])
    assert other["conversation_id"] != first["conversation_id"]
    records = kb.store.conversation_records(first["conversation_id"])
    assert [r["id"] for r in records] == [first["answer_id"], again["answer_id"]]


@pytest.mark.parametrize(
    ("resolved", "satisfaction", "comment"),
    [
        (True, "unsatisfied", ""),
        (True, "very_unsatisfied", ""),
        (False, "satisfied", "Improve it."),
        (False, "very_satisfied", "Improve it."),
        (False, "neutral", ""),  # "How should it be improved" is required
    ],
)
def test_the_form_offers_only_its_ratings(
    kb: KnowledgeBase,  # noqa: F811
    resolved: bool,
    satisfaction: str,
    comment: str,
) -> None:
    conversation = ask(kb)["conversation_id"]
    reply = end(kb, conversation, resolved=resolved, satisfaction=satisfaction, comment=comment)
    assert reply.status_code == 422


def test_ending_rates_once_and_sets_the_priority(kb: KnowledgeBase) -> None:  # noqa: F811
    conversation = ask(kb)["conversation_id"]
    someone_else = end(kb, conversation, "rm-2-session", resolved=True, satisfaction="satisfied")
    assert someone_else.status_code == 404
    first = end(
        kb, conversation, resolved=False, satisfaction="very_unsatisfied", comment="Wrong."
    )
    assert first.status_code == 200, first.text
    assert end(kb, conversation, resolved=True, satisfaction="satisfied").status_code == 404
    row = kb.store.conversation(conversation)
    assert row is not None
    assert (row["priority"], row["review_status"]) == ("high", "not_reviewed")
    assert row["resolved"] is False
    # An ended conversation takes no more answers: the next question starts a new one.
    assert ask(kb, conversation_id=conversation)["conversation_id"] != conversation


def test_satisfied_needs_no_review(kb: KnowledgeBase) -> None:  # noqa: F811
    conversation = rated(kb, "very_satisfied", True, comment="")
    row = kb.store.conversation(conversation)
    assert row is not None
    assert (row["priority"], row["review_status"]) == (None, "no_review")
    assert kb.store.feedback(status="open") == []


def test_the_comment_is_redacted(kb: KnowledgeBase) -> None:  # noqa: F811
    conversation = ask(kb)["conversation_id"]
    comment = "GARDEN BUSINESS PTE. LTD. was wrong."
    end(kb, conversation, resolved=False, satisfaction="unsatisfied", comment=comment)
    row = kb.store.conversation(conversation)
    assert row is not None and "GARDEN" not in row["comment"]


# --- history -------------------------------------------------------------------------------


def test_history_lists_and_opens_only_the_users_own_chats(kb: KnowledgeBase) -> None:  # noqa: F811
    mine = rated(kb, "satisfied", True)
    ask(kb, session="rm-2-session")
    listed = app_client(kb, "rm-session").get("/assistant/conversations").json()
    assert [item["conversation_id"] for item in listed["items"]] == [mine]
    assert listed["items"][0]["satisfaction"] == "satisfied"
    opened = app_client(kb, "rm-session").get(f"/assistant/conversations/{mine}")
    assert opened.status_code == 200
    assert [turn["question"] for turn in opened.json()["turns"]] == [QUESTION, QUESTION]
    assert app_client(kb, "rm-2-session").get(f"/assistant/conversations/{mine}").status_code == 404


# --- Support's review list and drafts -----------------------------------------------------


def test_support_lists_rated_conversations_by_priority_with_filters(kb: KnowledgeBase) -> None:  # noqa: F811
    low = rated(kb, "neutral", True)
    none = rated(kb, "satisfied", True)
    high = rated(kb, "very_unsatisfied", False)
    medium = rated(kb, "unsatisfied", False)
    ask(kb)  # open, not rated: not listed
    support = app_client(kb, "support-session")
    listed = support.get("/assistant/knowledge/conversations").json()
    assert [item["conversation_id"] for item in listed["items"]] == [high, medium, low, none]
    assert [item["priority"] for item in listed["items"]] == ["high", "medium", "low", None]
    assert listed["total"] == 4 and listed["page_size"] == 10
    unresolved = support.get("/assistant/knowledge/conversations?resolved=false").json()
    assert [item["conversation_id"] for item in unresolved["items"]] == [high, medium]
    neutral = support.get("/assistant/knowledge/conversations?satisfaction=neutral").json()
    assert [item["conversation_id"] for item in neutral["items"]] == [low]
    status = support.get("/assistant/knowledge/conversations?status=no_review").json()
    assert [item["conversation_id"] for item in status["items"]] == [none]
    assert app_client(kb, "rm-session").get("/assistant/knowledge/conversations").status_code == 403


def test_the_list_pages_ten_at_a_time(kb: KnowledgeBase) -> None:  # noqa: F811
    for _ in range(11):
        conversation = ask(kb)["conversation_id"]
        end(kb, conversation, resolved=True, satisfaction="satisfied")
    support = app_client(kb, "support-session")
    first = support.get("/assistant/knowledge/conversations").json()
    second = support.get("/assistant/knowledge/conversations?page=2").json()
    assert (len(first["items"]), len(second["items"]), first["total"]) == (10, 1, 11)


def test_support_saves_and_discards_a_draft(kb: KnowledgeBase) -> None:  # noqa: F811
    conversation = rated(kb, "unsatisfied", False)
    support = app_client(kb, "support-session")
    saved = support.put(
        f"/assistant/knowledge/conversations/{conversation}/draft",
        json={"kind": "resolution", "title": "Proof list", "body": "GARDEN BUSINESS needs one."},
    )
    assert saved.status_code == 200, saved.text
    assert "GARDEN" not in saved.json()["draft"]["body"]
    detail = support.get(f"/assistant/knowledge/conversations/{conversation}").json()
    assert detail["review_status"] == "draft" and detail["draft"]["title"] == "Proof list"
    assert detail["request"]["id"] == kb.store.conversation(conversation)["feedback_id"]  # type: ignore[index]
    assert len(detail["turns"]) == 2
    discarded = support.delete(f"/assistant/knowledge/conversations/{conversation}/draft")
    assert discarded.status_code == 200
    assert kb.store.conversation(conversation)["review_status"] == "not_reviewed"  # type: ignore[index]


def test_a_saved_fix_ends_the_draft_and_publishing_marks_it_fixed(kb: KnowledgeBase) -> None:  # noqa: F811
    conversation = rated(kb, "very_unsatisfied", False)
    support = app_client(kb, "support-session")
    support.put(
        f"/assistant/knowledge/conversations/{conversation}/draft",
        json={"title": "Proof list", "body": "Ask for the proof list."},
    )
    feedback_id = kb.store.conversation(conversation)["feedback_id"]  # type: ignore[index]
    entry = support.post(
        f"/assistant/knowledge/feedback/{feedback_id}/draft",
        json={"kind": "resolution", "title": "Proof list", "body": "Ask for the proof list."},
    ).json()
    row = kb.store.conversation(conversation)
    assert row is not None and row["draft"] is None and row["review_status"] == "awaiting_publish"
    published = support.post(
        f"/assistant/knowledge/entries/{entry['entry_id']}/versions/{entry['version']}/decision",
        json={
            "approve": True,
            "content_hash": entry["content_hash"],
            "confirm_single_reviewer": True,
        },
    )
    assert published.status_code == 200, published.text
    assert kb.store.conversation(conversation)["review_status"] == "fixed"  # type: ignore[index]


def test_no_draft_for_a_conversation_without_priority(kb: KnowledgeBase) -> None:  # noqa: F811
    conversation = rated(kb, "satisfied", True)
    reply = app_client(kb, "support-session").put(
        f"/assistant/knowledge/conversations/{conversation}/draft", json={"title": "x"}
    )
    assert reply.status_code == 404


# --- Support's chat without a case ---------------------------------------------------------


def test_support_chat_is_for_support_only(kb: KnowledgeBase) -> None:  # noqa: F811
    reply = app_client(kb, "rm-session").post("/assistant/support/chat", json={"message": "Hi"})
    assert reply.status_code == 403


def test_support_chat_answers_from_policy_lines(kb: KnowledgeBase) -> None:  # noqa: F811
    line = policy_lines(CATALOGUE)[0]
    model = FakeModel(answer=f"{line}\nSomething invented.")
    reply = app_client(kb, "support-session", model).post(
        "/assistant/support/chat", json={"message": "What is the UBO threshold?"}
    )
    assert reply.status_code == 200, reply.text
    body = reply.json()
    assert body["answer"] == line and body["answered_by"] == "model"
    assert "left out 1 statement" in body["notice"]
    # The model saw the policy line among its allowed lines, and no case facts.
    sent = "\n".join(message["content"] for message in model.calls[0])
    assert line in sent and CASE_ID not in sent


def test_support_chat_without_a_model_lists_matching_lines(kb: KnowledgeBase) -> None:  # noqa: F811
    reply = app_client(kb, "support-session").post(
        "/assistant/support/chat", json={"message": "Is the registry cache on?"}
    ).json()
    assert reply["answered_by"] == "case_data"
    assert "Registry cache: on." in reply["answer"]


def test_lines_are_selected_exactly() -> None:
    allowed = ["UBO threshold: 25. Ownership counts. [p1]", NOTHING_FOUND]
    kept, left_out = select_lines("- UBO threshold: 25. Ownership counts. [p1]\nNew rule.", allowed)
    assert kept == [allowed[0]] and left_out == 1


def test_policy_values_read_as_values() -> None:
    lines = policy_lines(
        {
            "rules": [
                {
                    "policy_id": "A",
                    "name": "Threshold",
                    "value": {"type": "DECIMAL", "value": "25.000000"},
                },
                {"policy_id": "B", "name": "Cache", "value": {"type": "BOOLEAN", "value": False}},
            ]
        }
    )
    assert lines == ["Threshold: 25. [A]", "Cache: off. [B]"]


# --- point 5: Support investigates and previews a change -----------------------------------


def test_support_case_chat_on_a_review_page_keeps_no_record(kb: KnowledgeBase) -> None:  # noqa: F811
    reply = app_client(kb, "support-session").post(
        f"/assistant/cases/{CASE_ID}/chat", json={"message": QUESTION}
    )
    assert reply.status_code == 200, reply.text
    assert reply.json()["answer_id"] is None and reply.json()["conversation_id"] is None
    rows, total = kb.store.conversations(user_id="support-user")
    assert (rows, total) == ([], 0)


def test_try_a_change_offers_its_sentences_and_saves_nothing(kb: KnowledgeBase) -> None:  # noqa: F811
    conversation = rated(kb, "unsatisfied", False)
    entries_before = len(kb.store.entries())
    support = app_client(kb, "support-session")
    tried = support.post(
        f"/assistant/knowledge/conversations/{conversation}/try",
        json={"kind": "guidance", "title": "Proof list", "body": "Ask the client for the lease."},
    )
    assert tried.status_code == 200, tried.text
    body = tried.json()
    assert body["question"] == QUESTION
    assert body["offered_lines"] == [f"Ask the client for the lease. [{body['tag']}]"]
    assert len(kb.store.entries()) == entries_before
    assert kb.store.conversation(conversation)["review_status"] == "not_reviewed"  # type: ignore[index]
    rm = app_client(kb, "rm-session").post(
        f"/assistant/knowledge/conversations/{conversation}/try", json={"body": "x"}
    )
    assert rm.status_code == 403
