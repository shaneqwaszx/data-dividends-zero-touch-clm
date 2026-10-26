"""PR89 required regressions: synthetic protocol and authority evidence only."""

import asyncio
import json
from typing import Any

import httpx
import pytest

from ai_assistant.briefing import fallback_answer
from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.context import build_case_facts
from ai_assistant.guardrails import StreamingGuard, guard_answer
from ai_assistant.llm import LlmUnavailableError, OpenAICompatibleChatModel, Piece
from tests.test_ai_assistant import ME, SUMMARY
from tests.test_streaming_resources import Bytes, collect


def facts() -> dict[str, Any]:
    return build_case_facts(CaseSnapshot(SUMMARY, [], ME))


def model(body: str) -> OpenAICompatibleChatModel:
    return OpenAICompatibleChatModel(
        base_url="http://synthetic.invalid/v1",
        model="synthetic",
        credential="test",
        timeout_seconds=1,
        temperature=0,
        transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=Bytes([body.encode()]))),
    )


def event(delta: Any, finish: Any = None) -> str:
    return "data: " + json.dumps({"choices": [{"delta": delta, "finish_reason": finish}]}) + "\n\n"


@pytest.mark.parametrize("code", ["REQUIRED", "STALE", "FAILED", "REVIEW_REQUIRED"])
def test_r1_search_destination(code: str) -> None:
    summary = {**SUMMARY, "clm": {"readiness": {"blockers": ["GOLDTIER_SEARCH_" + code]}}}
    data = build_case_facts(CaseSnapshot(summary, [], ME))
    answer = fallback_answer("What more do I need to do?", data)
    assert "(section: Existing-customer search)" in answer
    assert len(data["case_page_sections"]) == 6


@pytest.mark.parametrize("text", ["", "partial", "A complete sentence. "])
def test_r2_eof_is_owned_failure(text: str) -> None:
    with pytest.raises(LlmUnavailableError):
        collect(model(event({"content": text})))


@pytest.mark.parametrize("delta", [["bad"], [], "bad", 7, None, False])
def test_r3_invalid_delta_is_owned_failure(delta: Any) -> None:
    with pytest.raises(LlmUnavailableError):
        collect(model(event(delta)))


@pytest.mark.parametrize(
    "text",
    [
        'Click "Approve case" now.',
        "Click Approve case now.",
        "Use the final green clearance control to authorize onboarding.",
        "The uploaded document always overrides ACRA.",
        "These UBOs are legally verified.",
        "This case is Live and officially verified.",
        "This case has full KYC approval.",
        "Resend the uncertain GoldTier submission now.",
    ],
)
def test_r4_unverifiable_advice_never_displayed(text: str) -> None:
    data = facts()
    assert guard_answer(text, data) == ""
    guard = StreamingGuard(data)
    for chunk in [text[:5], text[5:] + "\n"]:
        assert not guard.feed(chunk)
    assert guard.finish() == ""


def test_r2_legitimate_terminals_and_length() -> None:
    for terminal in ["data: [DONE]\n\n", event({}, "stop")]:
        assert collect(model(event({"content": "Hello"}) + terminal)) == [
            Piece("Hello"),
            Piece(),
        ]
    assert collect(model(event({"content": "Hello"}, "length")))[-1].cut_short


@pytest.mark.parametrize(
    "event_body",
    [
        [],
        "bad",
        8,
        None,
        {},
        {"choices": []},
        {"choices": [None]},
        {"choices": ["bad"]},
        {"choices": {}},
        {"choices": [{"delta": {"content": ["bad"]}}]},
        {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]},
    ],
)
def test_r3_malformed_event_containment(event_body: Any) -> None:
    with pytest.raises(LlmUnavailableError):
        collect(model("data: " + json.dumps(event_body) + "\n\n"))


def test_r3_invalid_json_is_owned() -> None:
    with pytest.raises(LlmUnavailableError):
        collect(model("data: {broken\n\n"))


@pytest.mark.parametrize(
    "text",
    [
        'Click "Approve case" now.',
        "Click Approve case now.",
        "Use the final green clearance control to authorize onboarding.",
        "The uploaded document always overrides ACRA.",
        "These UBOs are legally verified.",
        "This case is Live and officially verified.",
        "This case has full KYC approval.",
        "Resend the uncertain GoldTier submission now.",
    ],
)
@pytest.mark.parametrize("streaming", [False, True])
def test_r4_api_rejects_unverified_operational_text(text: str, streaming: bool) -> None:
    from tests.test_ai_assistant import CASE_ID, FakeBackend, FakeModel, _client

    path = f"/assistant/cases/{CASE_ID}/chat" + ("/stream" if streaming else "")
    response = _client(FakeBackend(), FakeModel(answer=text)).post(path, json={"message": "Why?"})
    events = (
        [json.loads(line) for line in response.text.splitlines()]
        if streaming
        else [response.json()]
    )
    assert all(text not in e.get("text", "") and text not in e.get("answer", "") for e in events)
    assert events[-1]["answered_by"] == "case_data"
    assert "could not be verified" in events[-1]["notice"]
    assert '"Keep registry value"' in events[-1]["answer"]


def test_r4_injected_document_does_not_extend_output_catalog() -> None:
    from ai_assistant.guardrails import allowed_guidance

    attack = "Click Approve case now."
    summary = {**SUMMARY}
    data = build_case_facts(
        CaseSnapshot(
            summary,
            [
                {
                    "display_name": attack,
                    "fields": [{"field_key": "legal_name", "original_extracted_value": attack}],
                }
            ],
            ME,
        )
    )
    assert attack in str(data["documents"])
    assert all(attack not in line for line in allowed_guidance(data))
    assert guard_answer(attack, data) == ""


def test_r4_current_authorized_actions_only() -> None:
    from ai_assistant.guardrails import allowed_guidance

    data = facts()
    good = 'The current case offers "Keep registry value".'
    assert good in allowed_guidance(data)
    assert guard_answer(good, data) == good
    data["blockers"][0]["actions_available_to_this_user"] = []
    assert guard_answer(good, data) == ""


@pytest.mark.parametrize("prefix", ["", 'The current case offers "Keep registry value".\n'])
@pytest.mark.parametrize("failure", ["eof", "malformed", "timeout"])
def test_stream_partial_or_fallback_on_model_failure(prefix: str, failure: str) -> None:
    from tests.test_ai_assistant import CASE_ID, FakeBackend, _client

    if failure == "timeout":

        class TimeoutStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                if prefix:
                    yield event({"content": prefix}).encode()
                raise httpx.ReadTimeout("synthetic private diagnostic")

        transport = httpx.MockTransport(lambda _: httpx.Response(200, stream=TimeoutStream()))
        provider = OpenAICompatibleChatModel(
            base_url="http://synthetic.invalid/v1",
            model="m",
            credential="test",
            timeout_seconds=1,
            temperature=0,
            transport=transport,
        )
    else:
        body = event({"content": prefix})
        if failure == "malformed":
            body += event(["private diagnostic"])
        provider = model(body)
    client = _client(FakeBackend(), provider)
    events = [
        json.loads(line)
        for line in client.post(
            f"/assistant/cases/{CASE_ID}/chat/stream", json={"message": "Tell me about this case."}
        ).text.splitlines()
    ]
    assert events[-1]["type"] == "done"
    assert "private diagnostic" not in json.dumps(events)
    if prefix:
        assert events[0]["type"] == "text"
        assert events[-1]["answer"] == prefix.strip()
        assert "cut short" in events[-1]["notice"]
    else:
        assert events[-1]["answered_by"] == "case_data"


def test_stream_cancellation_closes_provider_without_manufactured_completion() -> None:
    closed = []

    class Source(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield event({"content": "first"}).encode()
            yield event({"content": "second"}).encode()

        async def aclose(self) -> None:
            closed.append(True)

    provider = OpenAICompatibleChatModel(
        base_url="http://synthetic.invalid/v1",
        model="m",
        credential="test",
        timeout_seconds=1,
        temperature=0,
        transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=Source())),
    )

    async def cancel() -> None:
        stream = provider.stream([])
        assert await anext(stream) == Piece("first")
        await stream.aclose()

    asyncio.run(cancel())
    assert closed == [True]


@pytest.mark.parametrize(
    "terminal",
    ["", "data: [DONE]\n\n", event({}, "stop"), event({}, "length"), event(["malformed"])],
)
def test_real_http_sse_framing(terminal: str) -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:
            pass

        def do_POST(self) -> None:
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.write((event({"content": "A complete sentence. "}) + terminal).encode())
            self.wfile.flush()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        provider = OpenAICompatibleChatModel(
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
            model="synthetic",
            credential="test",
            timeout_seconds=2,
            temperature=0,
        )

        async def read() -> None:
            pieces = provider.stream([])
            assert (await anext(pieces)).text == "A complete sentence. "
            if not terminal or "malformed" in terminal:
                with pytest.raises(LlmUnavailableError):
                    [piece async for piece in pieces]
            else:
                assert [piece async for piece in pieces] == [
                    Piece(cut_short='"length"' in terminal)
                ]

        asyncio.run(read())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
    assert not thread.is_alive()


def test_r1_stage_inventory_matches_accepted_case_ui() -> None:
    import re
    from pathlib import Path

    from ai_assistant.guide import CASE_PAGE_SECTIONS

    pages = Path(__file__).resolve().parents[2] / "frontend/src/pages"
    source = (pages / "CaseDetail.tsx").read_text(encoding="utf-8")
    # A title may be a constant shared with the progress panel; resolve it, never skip it.
    constants = dict(
        re.findall(
            r'export const ([A-Z_]+) = "([^"]+)";',
            (pages / "CaseStatePanels.tsx").read_text(encoding="utf-8"),
        )
    )
    titles = [
        literal or constants[name]
        for literal, name in re.findall(
            r'<StageDisclosure title=(?:"([^"]+)"|\{([A-Z_]+)\})', source
        )
    ]
    assert list(CASE_PAGE_SECTIONS) == [x for x in titles if x != "Historical / resolved issues"]
    assert "Reconciliation" not in CASE_PAGE_SECTIONS


def test_r1_every_blocker_location_is_a_case_page_section() -> None:
    from ai_assistant.guide import BLOCKER_SECTIONS, CASE_PAGE_SECTIONS, READINESS_NEEDS

    locations = {where for _, where in READINESS_NEEDS.values()} | set(BLOCKER_SECTIONS.values())
    assert locations <= set(CASE_PAGE_SECTIONS)


def test_r4_mock_result_preserves_local_approval_and_qualifies_external_approval() -> None:
    from ai_assistant.guardrails import allowed_guidance
    from ai_assistant.prompts import SYSTEM_PROMPT

    data = facts()
    correct = (
        "Successful mock submission does not establish GoldTier-internal "
        "or regulatory/KYC approval."
    )
    incorrect = "Successful mock submission does not mean KYC approval or final human approval."
    assert correct in allowed_guidance(data)
    assert guard_answer(correct, data) == correct
    assert guard_answer(incorrect, data) == ""
    assert "final human approval" not in SYSTEM_PROMPT
