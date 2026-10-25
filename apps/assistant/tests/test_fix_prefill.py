"""A Director's fix can start from the request's answer record (D-084, proposed).

The fix-start lines are the record's own text (the AI's left-out lines, and any shown model
line that is not an allowed line), one sentence per line and redacted against the
request's case. No model is called and nothing is saved until Save; the save rules are the
same as for any fix, and the saved version records that it started from the AI's answer.
"""

import sqlite3
from pathlib import Path
from typing import Any

import pytest

import tests.test_knowledge_review as review
from ai_assistant.answer_records import POLICY_LINES, fix_start_lines, fix_title
from ai_assistant.knowledge.service import KnowledgeBase
from ai_assistant.knowledge.store import SCHEMA_VERSION, KnowledgeStore
from tests.test_ai_assistant import FakeModel
from tests.test_answer_records import (
    allowed_line,
    app_client,
    ask,
    rate,
    record,
)
from tests.test_knowledge_review import kb  # noqa: F401 - kb is a pytest fixture

DROPPED = "Ask GARDEN BUSINESS for the tenancy agreement. Then check UEN 11111999A on it."


def request_with_dropped_lines(kb: KnowledgeBase, model: FakeModel | None = None) -> int:  # noqa: F811
    line = allowed_line(kb)
    answer = f"{line}\n{DROPPED}"
    answer_id = ask(kb, model or FakeModel(answer=answer))["answer_id"]
    return int(rate(kb, answer_id).json()["feedback_id"])


def fix_start(kb: KnowledgeBase, request_id: int, session: str = "director-session") -> Any:  # noqa: F811
    return app_client(kb, session).get(f"/assistant/knowledge/feedback/{request_id}/fix-start")


# --- what the form starts from ------------------------------------------------------------


def test_the_fix_starts_from_the_ais_left_out_lines_one_sentence_each_redacted(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    request_id = request_with_dropped_lines(kb)
    reply = fix_start(kb, request_id)
    assert reply.status_code == 200
    body = reply.json()
    assert body["title"] == "Document source conflict"
    assert body["lines"] == [
        "Ask [COMPANY] for the tenancy agreement.",
        "Then check UEN [UEN] on it.",
    ]
    # The allowed line the RM was shown is the app's wording: not part of the fix.
    assert allowed_line(kb) not in body["lines"]


def test_notices_and_fixed_disclaimers_are_left_out() -> None:
    disclaimer = sorted(POLICY_LINES)[0]
    stored = {
        "allowed_lines": [{"text": "Shown allowed line.", "source": "case"}],
        "chosen_lines": ["Shown allowed line.", "A shown line that is not allowed."],
        "dropped_lines": [
            "- Ask for the lease.",
            disclaimer,
            "I left out 1 statement that I could not check against the case data.",
            "Ask for the lease.",
        ],
        "result": {
            "notices": ["I left out 1 statement that I could not check against the case data."]
        },
    }
    assert fix_start_lines(stored, lambda text: text) == [
        "Ask for the lease.",
        "A shown line that is not allowed.",
    ]


def test_a_name_with_full_stops_is_redacted_before_the_line_is_split() -> None:
    stored = {"dropped_lines": ["Ask MERLION LABS PTE. LTD. for the lease. Then wait."]}

    def redact(text: str) -> str:
        return text.replace("MERLION LABS PTE. LTD.", "[COMPANY]")

    assert fix_start_lines(stored, redact) == ["Ask [COMPANY] for the lease.", "Then wait."]


def test_the_title_comes_from_the_blocker_type() -> None:
    assert fix_title(["OWNERSHIP_REQUIRED", "DOCUMENT_SOURCE_CONFLICT"]) == "Ownership required"
    assert fix_title([]) == "General"


def test_no_model_is_called_for_the_fix_start(kb: KnowledgeBase) -> None:  # noqa: F811
    model = FakeModel(answer=f"{allowed_line(kb)}\n{DROPPED}")
    request_id = request_with_dropped_lines(kb, model)
    calls = len(model.calls)
    assert fix_start(kb, request_id).status_code == 200
    assert len(model.calls) == calls


def test_a_request_without_an_answer_record_starts_empty(kb: KnowledgeBase) -> None:  # noqa: F811
    note_only = int(rate(kb, None).json()["feedback_id"])
    reply = fix_start(kb, note_only)
    assert reply.status_code == 404


@pytest.mark.parametrize(
    "session, status",
    [("rm-session", 403), ("hr-session", 403), ("director-b-session", 404)],
)
def test_only_a_director_in_scope_gets_the_fix_start(
    kb: KnowledgeBase,  # noqa: F811
    session: str,
    status: int,
) -> None:
    request_id = request_with_dropped_lines(kb)
    answer_id = next(g for g in kb.store.feedback(helpful=False) if g["id"] == request_id)[
        "answer_id"
    ]
    assert fix_start(kb, request_id, session).status_code == status
    assert kb.store.answer_views(answer_id) == []


def test_reading_the_fix_start_is_a_logged_view(kb: KnowledgeBase) -> None:  # noqa: F811
    request_id = request_with_dropped_lines(kb)
    answer_id = next(g for g in kb.store.feedback(helpful=False) if g["id"] == request_id)[
        "answer_id"
    ]
    fix_start(kb, request_id)
    assert [view["viewer"] for view in kb.store.answer_views(answer_id)] == ["director-dan"]


# --- saving: the same rules, and the origin is recorded ----------------------------------


def save(kb: KnowledgeBase, request_id: int, session: str = "director-session", **fix: Any) -> Any:  # noqa: F811
    body = {"kind": "resolution", "title": "Document source conflict", **fix}
    return app_client(kb, session).post(
        f"/assistant/knowledge/feedback/{request_id}/draft", json=body
    )


def test_the_saved_version_records_that_it_started_from_the_ais_answer(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    request_id = request_with_dropped_lines(kb)
    assert fix_start(kb, request_id).json()["lines"]
    # The Director rewrote the started text in general terms.
    rewritten = "Ask the client for the tenancy agreement for the new address."
    saved = save(kb, request_id, body=rewritten, started_from_answer=True)
    assert saved.status_code == 200, saved.text
    entry = saved.json()
    assert entry["started_from_answer"] is True
    director = app_client(kb, "director-session")
    # In the review queue and in the entry's review history.
    [pending] = director.get("/assistant/knowledge/reviews").json()["pending"]
    assert pending["started_from_answer"] is True
    history = director.get(f"/assistant/knowledge/entries/{entry['entry_id']}").json()
    assert [version["started_from_answer"] for version in history["versions"]] == [True]


def test_a_fix_written_from_scratch_or_cleared_is_not_marked(kb: KnowledgeBase) -> None:  # noqa: F811
    request_id = request_with_dropped_lines(kb)
    saved = save(kb, request_id, body="Ask for the tenancy agreement first.")
    assert saved.json()["started_from_answer"] is False


def test_a_request_without_a_record_cannot_be_marked(kb: KnowledgeBase) -> None:  # noqa: F811
    note_only = int(rate(kb, None).json()["feedback_id"])
    saved = save(
        kb, note_only, body="Ask for the tenancy agreement first.", started_from_answer=True
    )
    assert saved.status_code == 200
    assert saved.json()["started_from_answer"] is False


def test_the_save_still_redacts_and_refuses_hr(kb: KnowledgeBase) -> None:  # noqa: F811
    request_id = request_with_dropped_lines(kb)
    # Text the Director did not rewrite is still redacted against the case on save.
    saved = save(
        kb, request_id, body="Ask GARDEN BUSINESS for the lease.", started_from_answer=True
    )
    assert saved.json()["body"] == "Ask [COMPANY] for the lease."
    other = request_with_dropped_lines(kb)
    refused = save(
        kb, other, "hr-session", body="Ask for the lease first.", started_from_answer=True
    )
    assert refused.status_code == 403


@pytest.mark.parametrize(
    "fix, left",
    [
        ({"body": "Ask [COMPANY] for the lease at [ADDRESS]."}, "[COMPANY], [ADDRESS]"),
        ({"title": "Lease for [NAME]", "body": "Ask for the lease first."}, "[NAME]"),
        ({"body": "Ask for the lease first.", "follow_ups": ["Is [UEN] right?"]}, "[UEN]"),
        ({"body": "Ask for the lease at [SOME_NEW_TOKEN]."}, "[SOME_NEW_TOKEN]"),
    ],
)
def test_a_fix_that_keeps_a_placeholder_is_refused(
    kb: KnowledgeBase,  # noqa: F811
    fix: dict[str, Any],
    left: str,
) -> None:
    request_id = request_with_dropped_lines(kb)
    refused = save(kb, request_id, started_from_answer=True, **fix)
    assert refused.status_code == 422
    assert refused.json()["detail"] == {
        "code": "PLACEHOLDER_NOT_REWRITTEN",
        "message": f"Rewrite {left} in general terms before saving.",
    }
    # Nothing is saved and the request stays open.
    assert (
        app_client(kb, "director-session").get("/assistant/knowledge/reviews").json()["pending"]
        == []
    )
    assert [g["id"] for g in kb.store.feedback(status="open")] == [request_id]


def test_a_knowledge_tag_is_not_a_placeholder(kb: KnowledgeBase) -> None:  # noqa: F811
    request_id = request_with_dropped_lines(kb)
    saved = save(kb, request_id, body="Ask for the certified register [G1] first.")
    assert saved.status_code == 200, saved.text


def test_hr_is_refused_before_any_placeholder_check(kb: KnowledgeBase) -> None:  # noqa: F811
    request_id = request_with_dropped_lines(kb)
    assert save(kb, request_id, "hr-session", body="Ask [COMPANY] first.").status_code == 403


def test_a_version_edited_from_it_keeps_the_origin(kb: KnowledgeBase) -> None:  # noqa: F811
    request_id = request_with_dropped_lines(kb)
    entry = save(kb, request_id, body="Ask for the lease first.", started_from_answer=True).json()
    edited = review.edit(
        kb,
        "director-2-session",
        entry["entry_id"],
        entry["version"],
        body="Ask for the lease and a utility bill.",
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["started_from_answer"] is True
    assert record(kb, entry_answer(kb, request_id))["linked_request_id"] == request_id


def entry_answer(kb: KnowledgeBase, request_id: int) -> str:  # noqa: F811
    return str(next(g for g in kb.store.feedback() if g["id"] == request_id)["answer_id"])


# --- schema ---------------------------------------------------------------------------------


@pytest.mark.parametrize("version", ["1", "2", "3", "4", "5"])
def test_every_earlier_store_gains_the_origin_column(tmp_path: Path, version: str) -> None:
    path = tmp_path / f"v{version}.sqlite3"
    KnowledgeStore(path)
    with sqlite3.connect(path) as db:
        db.execute("ALTER TABLE entries DROP COLUMN started_from_answer")
        if version != "5":
            db.executescript(review.DROP_V5_TABLES)
        db.execute("UPDATE meta SET value = ? WHERE key = 'schema_version'", (version,))
    KnowledgeStore(path)
    with sqlite3.connect(path) as db:
        columns = {row[1] for row in db.execute("PRAGMA table_info(entries)")}
        stamped = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
    assert "started_from_answer" in columns and stamped == str(SCHEMA_VERSION)
