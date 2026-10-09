"""Greetings and thanks are answered at once, without waiting for the AI model."""

import pytest

from copilot.small_talk import small_talk_reply
from tests.test_copilot import CASE_ID, FakeBackend, FakeModel, _client

FACTS = {
    "viewer": {"name": "Maya Lim"},
    "company": {"legal_name": "MERLION CIRCULAR LABS PTE. LTD."},
    "blockers": [{"title": "Address conflict"}],
    "overall": {"status": "paused", "steps_done": 5, "steps_total": 12},
}


@pytest.mark.parametrize("message", ["hi", "Hi!", "hello there", "hey copilot", "Good morning :)"])
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
