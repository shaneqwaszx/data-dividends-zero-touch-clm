"""Answer records (D-084, proposed): one per answer, made only from what the server produced,
rated once by the user who asked, viewable by them and by a Director through the linked
enhancement request, logged on every view, and deleted when they expire."""

import json
import sqlite3
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

import tests.test_knowledge_review as review
from ai_assistant.answer_records import MAX_DROPPED_BYTES, AnswerRecorder, capped_dropped
from ai_assistant.config import AiAssistantSettings
from ai_assistant.knowledge.service import KnowledgeBase
from ai_assistant.knowledge.store import SCHEMA_VERSION, KnowledgeStore
from ai_assistant.main import create_app
from tests.test_ai_assistant import CASE_ID, DOCUMENTS, ORIGIN, SUMMARY, FakeModel
from tests.test_knowledge_review import _profile, kb  # noqa: F401 - kb is a pytest fixture

OTHER_CASE_ID = "7e1d2c3b-4a5f-4e6d-8c7b-6a5f4e3d2c1b"
# D-090: no question topic, so the stand-in model's answer is recorded without required lines.
QUESTION = "Tell me about this case."


@pytest.fixture(autouse=True)
def more_users(monkeypatch: pytest.MonkeyPatch) -> None:
    """A second TEAM_A RM, and a second case the first RM can also open."""

    monkeypatch.setitem(
        review.USERS,
        "rm-2-session",
        _profile("ravi-tan", "RELATIONSHIP_MANAGER", ["CASE_ACCESS", "POLICY_VIEW"]),
    )
    real_handler = review.handler

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == f"/api/clm/zero-touch/cases/{OTHER_CASE_ID}":
            return httpx.Response(200, json=SUMMARY)
        if path == f"/api/onboarding/cases/{OTHER_CASE_ID}/documents":
            return httpx.Response(200, json=DOCUMENTS)
        return real_handler(request)

    monkeypatch.setattr(review, "handler", handler)


def app_client(
    kb: KnowledgeBase,  # noqa: F811
    session: str,
    model: FakeModel | None = None,
    **settings: Any,
) -> TestClient:
    config = AiAssistantSettings(  # type: ignore[call-arg]
        _env_file=None, llm_enabled=False, knowledge_single_reviewer=False, **settings
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


def ask(
    kb: KnowledgeBase,  # noqa: F811
    model: FakeModel | None = None,
    *,
    session: str = "rm-session",
    case_id: str = CASE_ID,
    **body: Any,
) -> dict[str, Any]:
    reply = app_client(kb, session, model).post(
        f"/assistant/cases/{case_id}/chat", json={"message": QUESTION, **body}
    )
    assert reply.status_code == 200, reply.text
    return dict(reply.json())


def record(kb: KnowledgeBase, answer_id: str) -> dict[str, Any]:  # noqa: F811
    stored = kb.store.answer_record(answer_id)
    assert stored is not None
    return stored


def rate(
    kb: KnowledgeBase,  # noqa: F811
    answer_id: str | None,
    *,
    helpful: bool = False,
    session: str = "rm-session",
    case_id: str = CASE_ID,
) -> httpx.Response:
    body: dict[str, Any] = {"helpful": helpful, "note": "" if helpful else "No proof list."}
    if answer_id is not None:
        body["answer_id"] = answer_id
    return app_client(kb, session).post(f"/assistant/cases/{case_id}/feedback", json=body)


def allowed_line(kb: KnowledgeBase) -> str:  # noqa: F811
    """A line the model may say on this case (from a record of the server's allowed lines)."""

    return str(record(kb, ask(kb)["answer_id"])["allowed_lines"][0]["text"])


def blank(answer_id: str, user_id: str = "maya-lim", case_id: str = CASE_ID) -> dict[str, Any]:
    """A minimal record for store-level tests."""

    return {
        "id": answer_id,
        "case_id": case_id,
        "user_id": user_id,
        "team": "TEAM_A",
        "question": QUESTION,
        "earlier_answer_ids": [],
        "case_snapshot": {},
        "knowledge": {},
        "allowed_lines": [],
        "chosen_lines": [],
        "dropped_lines": [],
        "result": {},
        "shown_answer": "",
    }


def age(kb: KnowledgeBase, answer_id: str, created_at: str) -> None:  # noqa: F811
    with sqlite3.connect(kb.store._path) as db:
        db.execute("UPDATE answer_records SET created_at = ? WHERE id = ?", (created_at, answer_id))


# --- what a record holds ------------------------------------------------------------


def test_an_answer_is_recorded_from_what_the_server_produced(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    # D-090: no question topic ("should I" would be one), so no required lines are added.
    long_question = "Which proof do I ask for? " + "x" * 2000
    reply = ask(
        kb,
        FakeModel(),
        message=long_question,
        history=[{"role": "assistant", "content": "FORGED earlier answer text"}],
    )
    answer_id = reply["answer_id"]
    assert answer_id and len(answer_id) == 22
    stored = record(kb, answer_id)
    # The question as the server used it: cut at max_question_chars (600).
    assert stored["question"] == long_question[:600]
    assert (stored["user_id"], stored["case_id"], stored["team"]) == ("maya-lim", CASE_ID, "TEAM_A")
    assert stored["chosen_lines"] == reply["answer"].splitlines()
    assert stored["result"]["answered_by"] == "model"
    assert stored["result"]["fallback_reason"] is None
    assert stored["result"]["model"] == "fake-model"
    assert isinstance(stored["result"]["elapsed_ms"], int)
    snapshot = stored["case_snapshot"]
    assert set(snapshot) == {"blocker_codes", "stage", "steps_done", "steps_total", "facts_hash"}
    assert snapshot["blocker_codes"] and len(snapshot["facts_hash"]) == 64
    assert reply["answer"] in [line["text"] for line in stored["allowed_lines"]]
    assert stored["shown_answer"] == reply["answer"]
    assert set(stored["knowledge"]) == {"confidence", "degraded", "entries", "thresholds"}
    assert stored["knowledge"]["thresholds"] == {"guidance": 0.3, "resolution": 0.4}
    # Each allowed line says where it comes from; the fixed catalog lines are policy.
    sources = {line["text"]: line["source"] for line in stored["allowed_lines"]}
    assert (
        sources[
            "Ownership and UBO analysis is provisional; it does not establish legal verification."
        ]
        == "policy"
    )
    assert sources[reply["answer"]] == "case"
    # Browser-sent history text is never stored.
    with sqlite3.connect(kb.store._path) as db:
        row = db.execute("SELECT * FROM answer_records WHERE id = ?", (answer_id,)).fetchone()
    assert "FORGED" not in json.dumps(row)


def test_small_talk_is_not_recorded(kb: KnowledgeBase) -> None:  # noqa: F811
    reply = ask(kb, FakeModel(), message="hi")
    assert reply["answer_id"] is None
    with sqlite3.connect(kb.store._path) as db:
        assert db.execute("SELECT COUNT(*) FROM answer_records").fetchone()[0] == 0


def test_small_talk_says_so_so_a_missing_record_is_expected(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    assert ask(kb, FakeModel(), message="hi")["small_talk"] is True
    reply = app_client(kb, "rm-session", FakeModel()).post(
        f"/assistant/cases/{CASE_ID}/chat/stream", json={"message": "hi"}
    )
    done = json.loads(reply.text.splitlines()[-1])
    assert done["small_talk"] is True and done["answer_id"] is None
    assert ask(kb)["small_talk"] is False


@pytest.mark.parametrize("path", ["chat", "chat/stream"])
def test_an_answer_whose_record_cannot_be_saved_is_still_given(
    kb: KnowledgeBase,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    def fail(record: dict[str, Any], *, purge_days: object = None) -> None:
        raise sqlite3.OperationalError("table answer_records has no column named shown_answer")

    monkeypatch.setattr(kb.store, "add_answer_record", fail)
    reply = app_client(kb, "rm-session").post(
        f"/assistant/cases/{CASE_ID}/{path}", json={"message": QUESTION}
    )
    assert reply.status_code == 200
    body = json.loads(reply.text.splitlines()[-1]) if path == "chat/stream" else reply.json()
    # The RM still gets the answer; only the record (and so its answer_id) is missing.
    assert body["answer"] and body["answer_id"] is None and body["small_talk"] is False


def test_earlier_answer_ids_keep_only_this_users_records_on_this_case_capped(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    own = [ask(kb)["answer_id"] for _ in range(10)]
    foreign_user = ask(kb, session="rm-2-session")["answer_id"]
    foreign_case = ask(kb, case_id=OTHER_CASE_ID)["answer_id"]
    made_up = "A" * 22
    sent = [foreign_user, foreign_case, made_up, *own]
    stored = record(kb, ask(kb, earlier_answer_ids=sent)["answer_id"])
    # Only the last max_history_messages (8) ids sent are considered, and only own ones kept.
    assert stored["earlier_answer_ids"] == own[-8:]
    capped = record(kb, ask(kb, earlier_answer_ids=[*own[:2], foreign_user])["answer_id"])
    assert capped["earlier_answer_ids"] == own[:2]


def test_an_answer_id_from_the_browser_must_look_like_one(kb: KnowledgeBase) -> None:  # noqa: F811
    reply = app_client(kb, "rm-session").post(
        f"/assistant/cases/{CASE_ID}/chat",
        json={"message": QUESTION, "earlier_answer_ids": ["'; DROP TABLE x; --"]},
    )
    assert reply.status_code == 422


def test_records_never_reach_the_prompt(kb: KnowledgeBase) -> None:  # noqa: F811
    model = FakeModel()
    first = ask(kb, model, message="Which proof should I ask the client for, please?")
    ask(kb, model, earlier_answer_ids=[first["answer_id"]])
    prompt = json.dumps(model.calls[-1])
    assert "Which proof should I ask the client for" not in prompt
    assert first["answer_id"] not in prompt


# --- fallback reasons and dropped lines ---------------------------------------------------


def test_the_fallback_reason_is_recorded(kb: KnowledgeBase) -> None:  # noqa: F811
    line = allowed_line(kb)
    down = record(kb, ask(kb, FakeModel(fail=True))["answer_id"])
    assert down["result"]["fallback_reason"] == "model_unavailable"
    assert down["result"]["answered_by"] == "case_data" and down["chosen_lines"] == []
    nothing = record(kb, ask(kb, FakeModel(answer="Just approve it."))["answer_id"])
    assert nothing["result"]["fallback_reason"] == "nothing_allowed"
    assert nothing["dropped_lines"] == ["Just approve it."] and nothing["chosen_lines"] == []
    short = record(kb, ask(kb, FakeModel(answer=line, cut_short=True))["answer_id"])
    assert short["result"]["fallback_reason"] == "cut_short"
    assert short["chosen_lines"] == [line]
    no_model = record(kb, ask(kb, None)["answer_id"])
    assert no_model["result"]["fallback_reason"] == "model_unavailable"
    assert no_model["result"]["model"] is None


def test_dropped_lines_are_redacted_and_capped(kb: KnowledgeBase) -> None:  # noqa: F811
    line = allowed_line(kb)
    answer = f"{line}\nAsk GARDEN BUSINESS for proof.\nUEN 11111999A is fine."
    stored = record(kb, ask(kb, FakeModel(answer=answer))["answer_id"])
    assert stored["chosen_lines"] == [line]
    assert len(stored["dropped_lines"]) == 2
    dropped = " ".join(stored["dropped_lines"])
    assert "11111999A" not in dropped and "GARDEN" not in dropped.upper()

    many = [f"Line {i} " + "y" * 200 for i in range(100)]
    capped = capped_dropped(many, lambda text: text)
    assert sum(len(text.encode()) for text in capped) <= MAX_DROPPED_BYTES
    assert capped == many[: len(capped)] and 0 < len(capped) < len(many)


def test_the_stream_records_only_the_checked_lines(kb: KnowledgeBase) -> None:  # noqa: F811
    line = allowed_line(kb)
    model = FakeModel(answer=f"{line}\nNot an allowed line for UEN 11111999A.")
    reply = app_client(kb, "rm-session", model).post(
        f"/assistant/cases/{CASE_ID}/chat/stream", json={"message": QUESTION}
    )
    events = [json.loads(text) for text in reply.text.splitlines()]
    done = events[-1]
    assert done["type"] == "done" and done["answer_id"]
    stored = record(kb, done["answer_id"])
    assert stored["chosen_lines"] == [line] == done["answer"].splitlines()
    assert stored["dropped_lines"] == ["Not an allowed line for UEN [UEN]."]
    assert stored["result"]["left_out"] == 1


# --- rating ---------------------------------------------------------------------------


def test_not_helpful_links_the_answer_it_names(kb: KnowledgeBase) -> None:  # noqa: F811
    answer_id = ask(kb)["answer_id"]
    reply = rate(kb, answer_id)
    assert reply.status_code == 200
    request_id = reply.json()["feedback_id"]
    stored = record(kb, answer_id)
    assert stored["linked_request_id"] == request_id and stored["rated_at"]
    assert kb.store.feedback(helpful=False)[0]["answer_id"] == answer_id


def test_not_helpful_without_an_answer_record_still_reaches_a_director(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    # The record could not be saved, so the panel sends the note alone: it is still taken.
    reply = rate(kb, None)
    assert reply.status_code == 200
    assert reply.json()["message"] == "Thanks. This has been flagged so the answer can be improved."
    request_id = reply.json()["feedback_id"]
    [stored] = kb.store.feedback(helpful=False)
    assert stored["note"] == "No proof list." and stored["answer_id"] is None
    director = app_client(kb, "director-session")
    [gap] = director.get("/assistant/knowledge/reviews").json()["gaps"]
    assert gap["id"] == request_id and gap["answer_id"] is None
    # There is no record to open (the request page says so) and nothing is logged.
    linked = director.get(f"/assistant/knowledge/feedback/{request_id}/answer")
    assert linked.status_code == 404 and linked.json() == REFUSED


def test_yes_helpful_may_name_its_answer_without_linking_it(kb: KnowledgeBase) -> None:  # noqa: F811
    assert rate(kb, None, helpful=True).status_code == 200
    answer_id = ask(kb)["answer_id"]
    assert rate(kb, answer_id, helpful=True).status_code == 200
    stored = record(kb, answer_id)
    assert stored["rated_at"] and stored["linked_request_id"] is None


def test_an_answer_is_rated_once(kb: KnowledgeBase) -> None:  # noqa: F811
    answer_id = ask(kb)["answer_id"]
    assert rate(kb, answer_id, helpful=True).status_code == 200
    again = rate(kb, answer_id)
    assert again.status_code == 404
    assert len(kb.store.feedback()) == 1


REFUSED = {"detail": {"code": "NOT_FOUND", "message": "No such answer."}}


@pytest.mark.parametrize("kind", ["made-up", "foreign-user", "foreign-case"])
def test_an_answer_id_that_is_not_yours_to_rate_is_not_found(
    kb: KnowledgeBase,  # noqa: F811
    kind: str,
) -> None:
    answer_id = ask(kb)["answer_id"]
    if kind == "made-up":
        reply = rate(kb, "B" * 22)
    elif kind == "foreign-user":
        reply = rate(kb, answer_id, session="rm-2-session")
    else:
        reply = rate(kb, answer_id, case_id=OTHER_CASE_ID)
    # The same refusal whatever the reason, and nothing is stored.
    assert reply.status_code == 404 and reply.json() == REFUSED
    assert kb.store.feedback() == []
    assert record(kb, answer_id)["rated_at"] is None


def test_an_expired_answer_cannot_be_rated_even_before_the_purge(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    from ai_assistant.knowledge.store import AnswerNotFoundError

    kb.store.add_answer_record(blank("F" * 22))
    age(kb, "F" * 22, "2000-01-01T00:00:00+00:00")
    rating = {
        "case_id": CASE_ID,
        "user_id": "maya-lim",
        "role": None,
        "team": "TEAM_A",
        "helpful": False,
        "note": "No proof list.",
        "blocker_codes": (),
        "fields": (),
        "stages": (),
        "entry_id": None,
    }
    with pytest.raises(AnswerNotFoundError):
        kb.store.add_feedback(**rating, answer_id="F" * 22, answer_days=7)
    assert kb.store.feedback() == [] and record(kb, "F" * 22)["rated_at"] is None
    # Through the API it is the same "not found" (start-up has deleted it by then).
    reply = rate(kb, "F" * 22)
    assert reply.status_code == 404 and reply.json() == REFUSED
    assert kb.store.feedback() == []


# --- viewing ---------------------------------------------------------------------------


def linked_request(kb: KnowledgeBase) -> tuple[str, int]:  # noqa: F811
    answer_id = ask(kb)["answer_id"]
    request_id = int(rate(kb, answer_id).json()["feedback_id"])
    return answer_id, request_id


def test_the_rm_who_asked_can_open_their_record_and_the_view_is_logged(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    answer_id = ask(kb)["answer_id"]
    reply = app_client(kb, "rm-session").get(f"/assistant/answers/{answer_id}")
    assert reply.status_code == 200
    body = reply.json()
    assert body["answer_id"] == answer_id and body["question"] == QUESTION
    assert {"allowed_lines", "chosen_lines", "dropped_lines", "result", "knowledge"} <= set(body)
    assert [view["viewer"] for view in kb.store.answer_views(answer_id)] == ["maya-lim"]


@pytest.mark.parametrize(
    "session, status",
    [("rm-2-session", 404), ("director-session", 404), ("hr-session", 403)],
)
def test_nobody_else_opens_an_rms_record_directly(
    kb: KnowledgeBase,  # noqa: F811
    session: str,
    status: int,
) -> None:
    answer_id = ask(kb)["answer_id"]
    reply = app_client(kb, session).get(f"/assistant/answers/{answer_id}")
    assert reply.status_code == status
    assert kb.store.answer_views(answer_id) == []


def test_a_made_up_answer_id_is_not_found(kb: KnowledgeBase) -> None:  # noqa: F811
    rm = app_client(kb, "rm-session")
    assert rm.get(f"/assistant/answers/{'C' * 22}").status_code == 404
    assert rm.get("/assistant/answers/not-an-id").status_code == 404


def test_a_director_sees_what_happened_on_the_request_and_the_view_is_logged(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    first = ask(kb)["answer_id"]
    answer_id = ask(kb, earlier_answer_ids=[first])["answer_id"]
    request_id = int(rate(kb, answer_id).json()["feedback_id"])
    director = app_client(kb, "director-session")
    gaps = director.get("/assistant/knowledge/reviews").json()["gaps"]
    assert [gap["answer_id"] for gap in gaps] == [answer_id]
    linked = director.get(f"/assistant/knowledge/feedback/{request_id}/answer")
    assert linked.status_code == 200
    assert linked.json()["answer_id"] == answer_id
    assert linked.json()["earlier_answer_ids"] == [first]
    earlier = director.get(f"/assistant/knowledge/feedback/{request_id}/answers/{first}")
    assert earlier.status_code == 200 and earlier.json()["answer_id"] == first
    assert [view["viewer"] for view in kb.store.answer_views(answer_id)] == ["director-dan"]
    assert [view["viewer"] for view in kb.store.answer_views(first)] == ["director-dan"]


@pytest.mark.parametrize(
    "session, status",
    [("rm-session", 403), ("hr-session", 403), ("director-b-session", 404)],
)
def test_only_a_director_in_scope_opens_a_requests_record(
    kb: KnowledgeBase,  # noqa: F811
    session: str,
    status: int,
) -> None:
    answer_id, request_id = linked_request(kb)
    reply = app_client(kb, session).get(f"/assistant/knowledge/feedback/{request_id}/answer")
    assert reply.status_code == status
    assert kb.store.answer_views(answer_id) == []


def test_a_director_opens_only_the_earlier_answers_the_request_names(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    unrelated = ask(kb)["answer_id"]
    _, request_id = linked_request(kb)
    director = app_client(kb, "director-session")
    reply = director.get(f"/assistant/knowledge/feedback/{request_id}/answers/{unrelated}")
    assert reply.status_code == 404 and reply.json() == REFUSED
    assert kb.store.answer_views(unrelated) == []


def test_a_request_keeps_the_last_two_earlier_answers_and_shows_only_those(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    first, second, third = (ask(kb)["answer_id"] for _ in range(3))
    answer_id = ask(kb, earlier_answer_ids=[first, second, third])["answer_id"]
    request_id = int(rate(kb, answer_id).json()["feedback_id"])
    kept = {earlier: kb.store.kept_for(earlier) for earlier in (first, second, third)}
    assert kept == {first: [], second: [request_id], third: [request_id]}
    # Kept earlier answers are not rated by it: the RM can still rate them.
    assert record(kb, second)["rated_at"] is None
    director = app_client(kb, "director-session")
    linked = director.get(f"/assistant/knowledge/feedback/{request_id}/answer").json()
    assert linked["earlier_answer_ids"] == [second, third]
    older = director.get(f"/assistant/knowledge/feedback/{request_id}/answers/{first}")
    assert older.status_code == 404 and older.json() == REFUSED
    assert kb.store.answer_views(first) == []
    # The RM's own view still lists every earlier answer the record names.
    own = app_client(kb, "rm-session").get(f"/assistant/answers/{answer_id}").json()
    assert own["earlier_answer_ids"] == [first, second, third]


def test_only_the_same_users_earlier_answers_on_the_same_case_are_kept(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    other = "K" * 22
    kb.store.add_answer_record(blank(other, user_id="ryan-lee"))
    answer_id = ask(kb)["answer_id"]
    # Even if a record somehow named another user's answer, rating it keeps only own ones.
    with sqlite3.connect(kb.store._path) as db:
        db.execute(
            "UPDATE answer_records SET earlier_answer_ids = ? WHERE id = ?",
            (json.dumps([other]), answer_id),
        )
    rate(kb, answer_id)
    assert kb.store.kept_for(other) == []


def test_the_queue_shows_each_requests_question(kb: KnowledgeBase) -> None:  # noqa: F811
    _, request_id = linked_request(kb)
    rate(kb, None)  # a note without a record has no question
    gaps = app_client(kb, "director-session").get("/assistant/knowledge/reviews").json()["gaps"]
    assert [(gap["id"], gap["question"]) for gap in gaps] == [
        (request_id, QUESTION),
        (request_id + 1, None),
    ]


# --- retention -------------------------------------------------------------------------


def test_the_purge_removes_expired_records_and_keeps_linked_ones(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    old = "2000-01-01T00:00:00+00:00"
    unrated = ask(kb)["answer_id"]
    helpful = ask(kb)["answer_id"]
    assert rate(kb, helpful, helpful=True).status_code == 200
    fresh = ask(kb)["answer_id"]
    open_linked, _ = linked_request(kb)
    closed_old, closed_old_request = linked_request(kb)
    closed_new, closed_new_request = linked_request(kb)
    assert app_client(kb, "rm-session").get(f"/assistant/answers/{unrated}").status_code == 200
    assert kb.store.answer_views(unrated)
    for answer_id in (unrated, helpful, open_linked, closed_old, closed_new):
        age(kb, answer_id, old)
    kb.store.close_feedback(closed_old_request, by="director-dan", reason="Duplicate.")
    kb.store.close_feedback(closed_new_request, by="director-dan", reason="Duplicate.")
    with sqlite3.connect(kb.store._path) as db:
        db.execute("UPDATE feedback SET closed_at = ? WHERE id = ?", (old, closed_old_request))
    removed = kb.store.purge_answer_records(unrated_days=7, closed_days=30)
    assert removed == 3
    kept = {
        answer_id
        for answer_id in (unrated, helpful, fresh, open_linked, closed_old, closed_new)
        if kb.store.answer_record(answer_id) is not None
    }
    assert kept == {fresh, open_linked, closed_new}
    # The logged views of a deleted record go with it.
    with sqlite3.connect(kb.store._path) as db:
        assert (
            db.execute(
                "SELECT COUNT(*) FROM answer_record_views WHERE record_id = ?", (unrated,)
            ).fetchone()[0]
            == 0
        )


def test_an_earlier_answer_follows_its_requests_retention(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    old = "2000-01-01T00:00:00+00:00"
    earlier = ask(kb)["answer_id"]
    answer_id = ask(kb, earlier_answer_ids=[earlier])["answer_id"]
    request_id = int(rate(kb, answer_id).json()["feedback_id"])
    age(kb, earlier, old)
    age(kb, answer_id, old)
    # Unrated and older than 7 days, but kept while its request is open.
    kb.store.purge_answer_records(unrated_days=7, closed_days=30)
    assert kb.store.answer_record(earlier) is not None
    kb.store.close_feedback(request_id, by="director-dan", reason="Duplicate.")
    # Closed less than 30 days ago: still kept.
    kb.store.purge_answer_records(unrated_days=7, closed_days=30)
    assert kb.store.answer_record(earlier) is not None
    with sqlite3.connect(kb.store._path) as db:
        db.execute("UPDATE feedback SET closed_at = ? WHERE id = ?", (old, request_id))
    # 30 days after the request closed it goes, with the rated answer.
    assert kb.store.purge_answer_records(unrated_days=7, closed_days=30) == 2
    assert kb.store.answer_record(earlier) is None
    assert kb.store.answer_record(answer_id) is None


def test_an_answer_tied_to_two_requests_stays_until_both_are_done(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    old = "2000-01-01T00:00:00+00:00"
    earlier = ask(kb)["answer_id"]
    later = ask(kb, earlier_answer_ids=[earlier])["answer_id"]
    kept_for = int(rate(kb, later).json()["feedback_id"])
    own_request = int(rate(kb, earlier).json()["feedback_id"])  # rated itself afterwards
    for answer_id in (earlier, later):
        age(kb, answer_id, old)
    kb.store.close_feedback(kept_for, by="director-dan", reason="Duplicate.")
    with sqlite3.connect(kb.store._path) as db:
        db.execute("UPDATE feedback SET closed_at = ? WHERE id = ?", (old, kept_for))
    kb.store.purge_answer_records(unrated_days=7, closed_days=30)
    # Its own request is still open, so it stays; the other request's answer goes.
    assert kb.store.answer_record(earlier) is not None
    assert kb.store.answer_record(later) is None
    assert record(kb, earlier)["linked_request_id"] == own_request


def test_an_earlier_answer_shown_by_two_requests_stays_until_both_are_done(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    # Gate R1-F1: A1 is shown with R1, and again with a later R2 of the same chat.
    old = "2000-01-01T00:00:00+00:00"
    earlier = ask(kb)["answer_id"]
    first = ask(kb, earlier_answer_ids=[earlier])["answer_id"]
    second = ask(kb, earlier_answer_ids=[earlier, first])["answer_id"]
    one = int(rate(kb, first).json()["feedback_id"])
    two = int(rate(kb, second).json()["feedback_id"])
    assert kb.store.kept_for(earlier) == [one, two]
    for answer_id in (earlier, first, second):
        age(kb, answer_id, old)
    kb.store.close_feedback(one, by="director-dan", reason="Duplicate.")
    with sqlite3.connect(kb.store._path) as db:
        db.execute("UPDATE feedback SET closed_at = ? WHERE id = ?", (old, one))
    kb.store.purge_answer_records(unrated_days=7, closed_days=30)
    # R1 is long done, R2 is open: the earlier answer stays and R2's Director can open it.
    assert kb.store.answer_record(earlier) is not None
    assert kb.store.answer_record(first) is not None  # shown with R2 as an earlier answer too
    director = app_client(kb, "director-session")
    opened = director.get(f"/assistant/knowledge/feedback/{two}/answers/{earlier}")
    assert opened.status_code == 200
    kb.store.close_feedback(two, by="director-dan", reason="Duplicate.")
    with sqlite3.connect(kb.store._path) as db:
        db.execute("UPDATE feedback SET closed_at = ? WHERE id = ?", (old, two))
    kb.store.purge_answer_records(unrated_days=7, closed_days=30)
    assert [kb.store.answer_record(a) for a in (earlier, first, second)] == [None, None, None]
    with sqlite3.connect(kb.store._path) as db:
        assert db.execute("SELECT COUNT(*) FROM answer_record_keeps").fetchone()[0] == 0


def test_expired_records_go_on_start_up_and_at_most_hourly(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    stale = ask(kb)["answer_id"]
    age(kb, stale, "2000-01-01T00:00:00+00:00")
    app_client(kb, "rm-session")  # start-up
    assert kb.store.answer_record(stale) is None

    clock = [1000.0]
    recorder = AnswerRecorder(kb.store, unrated_days=7, closed_days=30, monotonic=lambda: clock[0])
    recorder.purge()
    kb.store.add_answer_record(blank("G" * 22))
    age(kb, "G" * 22, "2000-01-01T00:00:00+00:00")
    clock[0] += 60  # within the hour: no purge with this write
    assert recorder.save(blank("H" * 22))[0] == "H" * 22  # type: ignore[index]
    assert kb.store.answer_record("G" * 22) is not None
    clock[0] += 3600  # an hour later: the next write purges
    assert recorder.save(blank("J" * 22))[0] == "J" * 22  # type: ignore[index]
    assert kb.store.answer_record("G" * 22) is None


# --- schema ----------------------------------------------------------------------------


@pytest.mark.parametrize("version", ["1", "2", "3", "4"])
def test_every_earlier_store_gains_answer_records(tmp_path: Path, version: str) -> None:
    path = tmp_path / f"v{version}.sqlite3"
    KnowledgeStore(path)
    with sqlite3.connect(path) as db:
        db.executescript(review.DROP_V5_TABLES)
        db.execute("UPDATE meta SET value = ? WHERE key = 'schema_version'", (version,))
    store = KnowledgeStore(path)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == (
            str(SCHEMA_VERSION)
        )
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master")}
    assert {"answer_records", "answer_record_views", "answer_record_keeps"} <= tables
    store.add_answer_record(blank("E" * 22))
    assert store.owned_answers(["E" * 22], user_id="maya-lim", case_id=CASE_ID) == ["E" * 22]
    KnowledgeStore(path)  # opening again changes nothing
    assert store.answer_record("E" * 22) is not None


# answer_records as an earlier build of this branch made it: stamped 5, no shown_answer.
EARLY_V5_ANSWER_RECORDS = """
DROP TABLE answer_record_keeps; DROP TABLE answer_record_views; DROP TABLE answer_records;
CREATE TABLE answer_records (
    id TEXT PRIMARY KEY, case_id TEXT NOT NULL, user_id TEXT NOT NULL, team TEXT,
    created_at TEXT NOT NULL, question TEXT NOT NULL, earlier_answer_ids TEXT NOT NULL,
    case_snapshot TEXT NOT NULL, knowledge TEXT NOT NULL, allowed_lines TEXT NOT NULL,
    chosen_lines TEXT NOT NULL, dropped_lines TEXT NOT NULL, result TEXT NOT NULL,
    rated_at TEXT, linked_request_id INTEGER REFERENCES feedback (id)
);
CREATE INDEX answer_records_by_request ON answer_records (linked_request_id);
CREATE TABLE answer_record_views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL REFERENCES answer_records (id) ON DELETE CASCADE,
    viewer TEXT NOT NULL, viewed_at TEXT NOT NULL
);
INSERT INTO answer_records VALUES ('GGGGGGGGGGGGGGGGGGGGGG', 'c', 'maya-lim', NULL,
    '2026-10-25T05:28:46+00:00', 'q', '[]', '{}', '{}', '[]', '[]', '[]', '{}', NULL, NULL);
"""


@pytest.mark.parametrize("shape", ["without-shown-answer", "with-kept-for-column"])
def test_a_branch_only_v5_store_without_shown_answer_records_again(
    tmp_path: Path, shape: str
) -> None:
    # Every insert into such a store failed, so answers got no answer_id (and no "Not
    # helpful" in an earlier panel). Opening it adds the column and keeps the old records.
    from tests.test_knowledge_store import _kb

    path = tmp_path / "knowledge.sqlite3"
    KnowledgeStore(path)
    with sqlite3.connect(path) as db:
        db.executescript(EARLY_V5_ANSWER_RECORDS)
        if shape == "with-kept-for-column":
            # As 41c7e91 made it: shown_answer, and one kept_for_request_id column (no table).
            db.executescript(
                "ALTER TABLE answer_records ADD COLUMN shown_answer TEXT NOT NULL DEFAULT '\"\"';"
                "ALTER TABLE answer_records ADD COLUMN kept_for_request_id INTEGER;"
                "INSERT INTO feedback (case_id, user_id, role, team, helpful, note, blocker_codes,"
                " fields, stages, entry_id, status, created_at) VALUES ('c', 'maya-lim', NULL,"
                " NULL, 0, 'n', '[]', '[]', '[]', NULL, 'open', '2026-10-25T05:30:00+00:00');"
                "UPDATE answer_records SET kept_for_request_id = last_insert_rowid();"
            )
        # As that branch stamped it (before D-104's version 6).
        db.execute("UPDATE meta SET value = '5' WHERE key = 'schema_version'")
    knowledge = _kb(tmp_path)  # opening the store repairs it
    store = knowledge.store
    with sqlite3.connect(path) as db:
        columns = {row[1] for row in db.execute("PRAGMA table_info(answer_records)")}
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master")}
    assert "shown_answer" in columns and "answer_record_keeps" in tables
    old = store.answer_record("G" * 22)
    assert old is not None and old["shown_answer"] == "" and old["question"] == "q"
    # A link the single column held moves into the table.
    assert store.kept_for("G" * 22) == ([1] if shape == "with-kept-for-column" else [])
    store.add_answer_record({**blank("H" * 22), "shown_answer": "Shown."})
    assert record_of(store, "H" * 22)["shown_answer"] == "Shown."
    KnowledgeStore(path)  # opening again changes nothing
    assert record_of(store, "H" * 22)["shown_answer"] == "Shown."
    # And through the service: an answer on the repaired store gets its record again.
    assert ask(knowledge)["answer_id"]


def record_of(store: KnowledgeStore, answer_id: str) -> dict[str, Any]:
    stored = store.answer_record(answer_id)
    assert stored is not None
    return stored


def test_allowed_lines_are_tagged_policy_case_or_knowledge() -> None:
    from ai_assistant.answer_records import POLICY_LINES, allowed_lines
    from ai_assistant.clm_client import CaseSnapshot
    from ai_assistant.context import build_case_facts
    from tests.test_ai_assistant import ME

    facts = build_case_facts(CaseSnapshot(summary=SUMMARY, documents=DOCUMENTS, actor=ME))
    knowledge = ("Ask for a certified copy of the register [G1].",)
    tagged = allowed_lines(facts, knowledge)
    by_source: dict[str, list[str]] = {}
    for line in tagged:
        by_source.setdefault(line["source"], []).append(line["text"])
    assert by_source["knowledge"] == list(knowledge)
    assert set(by_source["policy"]) == set(POLICY_LINES)
    # Case lines are the ones only this case's facts produce.
    assert by_source["case"] and not set(by_source["case"]) & POLICY_LINES


def test_a_case_data_answer_is_kept_as_shown_but_redacted(kb: KnowledgeBase) -> None:  # noqa: F811
    reply = ask(kb, FakeModel(fail=True))
    stored = record(kb, reply["answer_id"])
    assert reply["answer"] and stored["shown_answer"]
    assert "11111999A" not in stored["shown_answer"]
    assert "GARDEN BUSINESS" not in stored["shown_answer"].upper()
    assert stored["result"]["notices"] == [reply["notice"]]


# D-090 catalog lines in records (QG R5-B1, R5-M1) ----------------------------------------

DIFFERENCE_QUESTION = "Explain the registered address difference"
RAW_VALUES = ("OFFICIAL MOCK STREET", "GARDEN WALK", "123456", "018919", "11111999A")


def _raw(texts: list[str]) -> list[str]:
    return [text for text in texts if any(value in text for value in RAW_VALUES)]


def test_a_record_keeps_no_acra_or_document_values_from_catalog_lines(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    from ai_assistant.answer_records import fix_start_lines

    reply = ask(
        kb,
        FakeModel(answer='The current case offers "Keep registry value".'),
        message=DIFFERENCE_QUESTION,
    )
    # The RM sees the values: the service added the topic's required lines to the answer.
    assert "18 GARDEN WALK" in reply["answer"] and reply["added_lines"] == [0, 1, 2]
    stored = record(kb, reply["answer_id"])
    # The record keeps every shown line, the added ones too, but never the values.
    assert len(stored["chosen_lines"]) == len(reply["answer"].splitlines()) == 4
    assert _raw(stored["chosen_lines"]) == []
    assert _raw([stored["shown_answer"]]) == []
    assert _raw([line["text"] for line in stored["allowed_lines"]]) == []
    assert "[ADDRESS]" in stored["shown_answer"]
    # Redacted alike, chosen lines still match allowed lines: nothing becomes a fix start.
    assert fix_start_lines(stored, lambda text: text) == []


def test_a_case_data_record_keeps_no_values_from_catalog_lines(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    reply = ask(kb, FakeModel(fail=True), message=DIFFERENCE_QUESTION)
    stored = record(kb, reply["answer_id"])
    assert reply["answered_by"] == "case_data" and stored["chosen_lines"] == []
    assert _raw([stored["shown_answer"]]) == []
    assert _raw([line["text"] for line in stored["allowed_lines"]]) == []
