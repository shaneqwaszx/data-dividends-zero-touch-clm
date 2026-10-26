"""Speed work: smaller prompt, cache-friendly order, streaming, pre-warming, length notice."""

import json
from typing import Any

import httpx

from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.context import build_case_facts
from ai_assistant.guardrails import StreamingGuard
from ai_assistant.llm import OpenAICompatibleChatModel, Piece
from ai_assistant.prompts import build_messages, prefix_messages, trim_history
from tests.test_ai_assistant import CASE_ID, DOCUMENTS, ME, SUMMARY, FakeBackend, FakeModel, _client
from tests.test_streaming_resources import Bytes, collect

FACTS = build_case_facts(CaseSnapshot(summary=SUMMARY, documents=DOCUMENTS, actor=ME))
STREAM = f"/assistant/cases/{CASE_ID}/chat/stream"


def _events(response: httpx.Response) -> list[dict[str, Any]]:
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def test_prompt_is_small_and_keeps_the_facts_the_rm_needs() -> None:
    messages = build_messages(FACTS, [], "What should I do next?")
    # D-090: the question's topic message is bounded on its own; the rest was about 11,900.
    topic = [m["content"] for m in messages if m["content"].startswith("QUESTION TOPIC:")]
    assert len(topic) == 1 and len(topic[0]) < 1000
    assert sum(len(m["content"]) for m in messages) - len(topic[0]) < 9000
    facts = messages[1]["content"]
    for needed in ("Keep registry value", "11111999A", "18 GARDEN WALK", "Ownership & UBO"):
        assert needed in facts
    for internal in ("DOCUMENT_SOURCE_CONFLICT", "HUMAN_DECISION", "case_page_terms"):
        assert internal not in facts


def test_glossary_is_only_sent_when_the_question_asks_about_a_label() -> None:
    plain = build_messages(FACTS, [], "What should I do next?")
    assert not any(m["content"].startswith("CASE PAGE TERMS") for m in plain)
    asked = build_messages(FACTS, [], "What does evidence score mean?")
    terms = next(m["content"] for m in asked if m["content"].startswith("CASE PAGE TERMS"))
    assert "evidence score" in terms and "canonical" not in terms


def test_fixed_part_of_the_prompt_comes_first_so_it_can_be_cached() -> None:
    history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "Hello"}]
    first = build_messages(FACTS, [], "Why is this case blocked?")
    later = build_messages(FACTS, history, "What does canonical mean?")
    assert first[:2] == later[:2] == prefix_messages(FACTS)


def test_history_is_trimmed_to_a_budget_but_recent_turns_are_kept() -> None:
    history = []
    for number in range(20):
        history.append({"role": "user", "content": f"question {number} " + "x" * 200})
        history.append({"role": "assistant", "content": f"answer {number} " + "y" * 900})
    kept = trim_history(history)
    assert kept and kept[0]["role"] == "user"
    assert kept[-1]["content"].startswith("answer 19")
    assert sum(len(turn["content"]) for turn in kept) <= 2400
    assert all(len(turn["content"]) <= 702 for turn in kept)


def test_answer_streams_in_finished_sentences_then_ends_with_the_full_answer() -> None:
    first = 'The current case offers "Keep registry value".'
    second = 'Open the "Ownership & UBO" section to inspect the current case evidence.'
    model = FakeModel(answer=first + "\n" + second)
    response = _client(FakeBackend(), model).post(
        STREAM, json={"message": "Tell me about this case."}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    events = _events(response)
    texts = [event["text"] for event in events if event["type"] == "text"]
    assert texts[0] == first
    assert events[-1]["type"] == "done"
    assert events[-1]["answered_by"] == "model"
    assert events[-1]["answer"] == first + "\n" + second


def test_a_sentence_the_guardrails_drop_is_never_shown_while_streaming() -> None:
    model = FakeModel(
        answer='Click "Approve case" now.\nThe current case offers "Keep registry value".'
    )
    events = _events(
        _client(FakeBackend(), model).post(STREAM, json={"message": "Tell me about this case."})
    )
    assert all("Approve case" not in json.dumps(event) for event in events)
    assert events[-1]["answer"] == 'The current case offers "Keep registry value".'


def test_streaming_falls_back_to_case_data_when_the_model_is_down() -> None:
    events = _events(
        _client(FakeBackend(), FakeModel(fail=True)).post(STREAM, json={"message": "Why?"})
    )
    assert [event["type"] for event in events] == ["done"]
    assert events[0]["answered_by"] == "case_data" and "Keep registry value" in events[0]["answer"]


def test_small_talk_is_answered_at_once_on_the_stream_too() -> None:
    model = FakeModel()
    events = _events(_client(FakeBackend(), model).post(STREAM, json={"message": "okay thanks"}))
    assert events[0]["answer"].startswith("You're welcome")
    assert model.calls == []


def test_an_answer_that_hits_the_length_limit_says_so() -> None:
    model = FakeModel(answer=FakeModel.ANSWER, cut_short=True)
    client = _client(FakeBackend(), model)
    streamed = _events(client.post(STREAM, json={"message": "Tell me everything"}))[-1]
    plain = client.post(f"/assistant/cases/{CASE_ID}/chat", json={"message": "Tell me everything"})
    for reply in (streamed, plain.json()):
        assert reply["notice"] == "This answer was cut short. Ask me to continue for the rest."


def test_opening_the_panel_prewarms_the_model_once_with_the_same_prompt_start() -> None:
    model = FakeModel()
    client = _client(FakeBackend(), model)
    client.get(f"/assistant/cases/{CASE_ID}/brief")
    client.get(f"/assistant/cases/{CASE_ID}/brief")
    assert len(model.warmed) == 1  # the same case is not re-read within the interval
    client.post(STREAM, json={"message": "What next?"})
    assert model.calls[0][:2] == model.warmed[0]


def test_streaming_guard_waits_for_a_complete_catalog_line() -> None:
    guard = StreamingGuard(FACTS)
    assert guard.feed('The current case offers "Keep regis') is None
    assert guard.feed('try value".\nUnverified trailing advice') == FakeModel.ANSWER
    assert guard.finish() == FakeModel.ANSWER


def test_openai_compatible_client_reads_a_streamed_reply() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        chunks = [
            {"choices": [{"delta": {"role": "assistant"}}]},
            {"choices": [{"delta": {"content": "Hel"}}]},
            {"choices": [{"delta": {"content": "lo"}, "finish_reason": "length"}]},
        ]
        body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks) + "data: [DONE]\n\n"
        return httpx.Response(
            200, stream=Bytes([body.encode()]), headers={"content-type": "text/event-stream"}
        )

    model = OpenAICompatibleChatModel(
        base_url="http://127.0.0.1:11434/v1",
        model="m",
        credential="test_key",
        timeout_seconds=5,
        temperature=0,
        transport=httpx.MockTransport(handler),
    )
    pieces = collect(model, [{"role": "user", "content": "hi"}])
    assert pieces == [Piece("Hel"), Piece("lo"), Piece(cut_short=True)]
    assert seen["body"]["stream"] is True and seen["body"]["max_tokens"] == 600
