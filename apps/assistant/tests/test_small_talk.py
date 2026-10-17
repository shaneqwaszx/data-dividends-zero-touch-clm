"""Greetings and thanks are answered at once, without waiting for the AI model."""

import pytest

from ai_assistant.small_talk import small_talk_reply
from tests.test_ai_assistant import CASE_ID, FakeBackend, FakeModel, _client

FACTS = {
    "viewer": {"name": "Maya Lim"},
    "company": {"legal_name": "MERLION CIRCULAR LABS PTE. LTD."},
    "blockers": [{"title": "Address conflict"}],
    "overall": {"status": "paused", "steps_done": 5, "steps_total": 12},
}


@pytest.mark.parametrize(
    "message", ["hi", "Hi!", "hello there", "hey assistant", "Good morning :)"]
)
def test_greetings_get_a_friendly_case_status(message: str) -> None:
    reply = small_talk_reply(message, FACTS)
    assert reply is not None
    assert reply.startswith("Hi Maya!")
    assert "1 issue" in reply and "5 of 12" in reply


@pytest.mark.parametrize("message", ["thanks", "Thank you so much!", "ok", "bye", "who are you"])
def test_other_small_talk_is_answered(message: str) -> None:
    assert small_talk_reply(message, FACTS)


@pytest.mark.parametrize(
    "message",
    ["hi, why is this case blocked?", "hello what did ACRA return", "thanks but what next", "why"],
)
def test_real_questions_still_go_to_the_model(message: str) -> None:
    assert small_talk_reply(message, FACTS) is None


def test_chat_answers_hi_without_calling_the_model() -> None:
    model = FakeModel()
    client = _client(FakeBackend(), model)
    body = client.post(
        f"/assistant/cases/{CASE_ID}/chat", json={"message": "hi", "history": []}
    ).json()
    assert model.calls == []
    assert body["answer"].startswith("Hi Maya!")
    assert body["notice"] is None


def test_fallback_explains_case_page_labels_instead_of_dumping_acra() -> None:
    from ai_assistant.briefing import fallback_answer

    answer = fallback_answer(
        "the page says canonical and suggestion, is canonical from acra?", FACTS
    )
    assert "Canonical: the official value from the registry (ACRA)" in answer
    assert "Suggestion: the value our system read from the uploaded document" in answer


def test_retrieved_time_is_readable() -> None:
    from ai_assistant.context import readable_time

    assert readable_time("2026-10-12T18:08:11.400356Z") == "12 Oct 2026, 18:08 UTC"


@pytest.mark.parametrize(
    ("message", "start"),
    [
        ("okay thanks", "You're welcome"),
        ("ok thank you!", "You're welcome"),
        ("got it, cheers", "You're welcome"),
        ("thanks bye", "Bye for now"),
        ("hi there okay", "Hi "),
        ("ok cool", "Okay."),
    ],
)
def test_mixed_small_talk_answers_what_was_meant(message: str, start: str) -> None:
    reply = small_talk_reply(message, FACTS)
    assert reply and reply.startswith(start)
