"""The dormant OpenRouter adapter against mocked responses only (Phase A2, D-091 proposed).

T3-04 to T3-19 and T3-21: the fixed request policy, stream and non-stream parsing, usage
read-through, error classes, routing anomalies, secret hygiene and the single request path.
Every response is an in-memory mock; the suite guard fails any remote connection.
"""

import json
import logging
from collections.abc import AsyncIterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import anyio
import httpx
import pytest

from ai_assistant.llm import ModelAnswer, ModelCallError, Piece
from ai_assistant.main import CUT_SHORT_NOTICE, FALLBACK_NOTICE, POLICY_NOTICE
from ai_assistant.openrouter import OpenRouterChatModel
from ai_assistant.telemetry import MemorySink
from tests.remote_fixtures import (
    ENDPOINT,
    MESSAGES,
    SENTINEL_KEY,
    URL,
    USAGE,
    Provider,
    adapter,
    answering,
    chunk,
    completion,
    frame,
    happy_stream,
    sse,
    streaming,
)
from tests.test_telemetry import ALLOWED, CHAT, STREAM, _app

ASSISTANT = Path(__file__).resolve().parents[1]


def _model(provider: Provider, **settings: Any) -> OpenRouterChatModel:
    return adapter(provider.transport(), **settings)


def _stream(model: OpenRouterChatModel, messages: list[dict[str, str]] = MESSAGES) -> list[Piece]:
    async def run() -> list[Piece]:
        return [piece async for piece in model.stream(messages)]

    return anyio.run(run)


def _stream_error(model: OpenRouterChatModel) -> ModelCallError:
    with pytest.raises(ModelCallError) as raised:
        _stream(model)
    return raised.value


def _complete_error(model: OpenRouterChatModel) -> ModelCallError:
    with pytest.raises(ModelCallError) as raised:
        model.complete(MESSAGES)
    return raised.value


def _one_request(provider: Provider) -> httpx.Request:
    assert len(provider.requests) == 1
    request = provider.requests[0]
    assert str(request.url) == URL
    return request


# --- the request (T3-04) --------------------------------------------------------------------


EXPECTED_PROVIDER = {
    "order": [ENDPOINT.slug],
    "only": [ENDPOINT.slug],
    "allow_fallbacks": False,
    "require_parameters": True,
    "data_collection": "deny",
    "zdr": True,
    "max_price": {"prompt": 0.15, "completion": 0.6, "request": 0.0},
    "quantizations": ["fp8"],
}


@pytest.mark.parametrize("stream", [True, False])
def test_the_remote_request_is_exactly_the_fixed_policy(stream: bool) -> None:
    provider = streaming(happy_stream()) if stream else answering(completion())
    model = _model(provider)
    _stream(model) if stream else model.complete(MESSAGES)

    request = _one_request(provider)
    assert json.loads(request.content) == {
        "model": "openai/gpt-oss-120b",
        "messages": MESSAGES,
        "temperature": 0.2,
        "max_tokens": 2000,
        "stream": stream,
        "reasoning": {"effort": "low", "exclude": True},
        "provider": EXPECTED_PROVIDER,
    }
    headers = {key.lower(): value for key, value in request.headers.items()}
    assert headers["authorization"] == "Bearer " + SENTINEL_KEY
    assert headers["accept-encoding"] == ("identity" if stream else "gzip, deflate")
    assert set(headers) == {
        "host",
        "accept",
        "accept-encoding",
        "connection",
        "user-agent",
        "content-length",
        "content-type",
        "authorization",
    }


def test_warm_up_never_sends_anything() -> None:
    provider = answering(completion())
    _model(provider).warm(MESSAGES)

    assert provider.requests == []


# --- stream parsing (T3-05 to T3-11) --------------------------------------------------------


def test_text_is_shown_once_and_usage_is_read_through_to_done() -> None:
    provider = streaming(happy_stream())
    pieces = _stream(_model(provider))

    assert [piece.text for piece in pieces[:-1]] == ["Line one\n"]
    last = pieces[-1]
    assert last.text == "" and last.finish_reason == "stop" and not last.cut_short
    assert last.usage is not None
    assert last.usage.cost == Decimal("0.00072")
    assert (last.usage.prompt_tokens, last.usage.completion_tokens) == (3000, 450)
    assert (last.usage.reasoning_tokens, last.usage.cached_tokens) == (300, 0)
    assert last.usage.generation_ref == "gen-1761-test"
    assert last.usage.anomalies == ()
    _one_request(provider)


def test_a_usage_chunk_with_no_choices_is_accepted() -> None:
    usage_only = frame(
        {"id": "gen-1761-test", "model": "openai/gpt-oss-120b", "choices": [], "usage": USAGE}
    )
    pieces = _stream(_model(streaming(sse(chunk("Line one\n"), chunk("", "stop"), usage_only))))

    assert pieces[-1].usage is not None and pieces[-1].usage.cost == Decimal("0.00072")


def test_a_missing_usage_chunk_leaves_the_cost_unknown() -> None:
    pieces = _stream(_model(streaming(sse(chunk("Line one\n"), chunk("", "stop")))))

    usage = pieces[-1].usage
    assert usage is not None and usage.cost is None
    assert usage.anomalies == ("usage_missing",)
    assert [piece.text for piece in pieces[:-1]] == ["Line one\n"]


@pytest.mark.parametrize(
    "usage",
    [
        {**USAGE, "prompt_tokens": -1},
        {**USAGE, "completion_tokens": 1.5},
        {**USAGE, "cost": "0.001"},
        {**USAGE, "cost": True},
        {**USAGE, "cost": 10**12},
        {key: value for key, value in USAGE.items() if key != "cost"},
        "not an object",
    ],
)
def test_malformed_usage_is_never_trusted(usage: object) -> None:
    pieces = _stream(_model(streaming(happy_stream(usage=usage))))

    last = pieces[-1].usage
    assert last is not None and last.cost is None
    assert "usage_malformed" in last.anomalies
    assert [piece.text for piece in pieces[:-1]] == ["Line one\n"]


def test_a_cost_with_many_places_is_parsed_exactly() -> None:
    pieces = _stream(_model(streaming(happy_stream(usage={**USAGE, "cost": 0.000123456789}))))

    assert pieces[-1].usage is not None
    assert pieces[-1].usage.cost == Decimal("0.000123456789")


def test_a_non_finite_cost_after_the_finish_keeps_the_answer_but_not_the_usage() -> None:
    bad = b'data: {"choices": [], "usage": {"cost": NaN}}\n\n'
    pieces = _stream(_model(streaming(sse(chunk("Line one\n"), chunk("", "stop"), bad))))

    usage = pieces[-1].usage
    assert [piece.text for piece in pieces[:-1]] == ["Line one\n"]
    assert usage is not None and usage.cost is None
    assert {"read_through_incomplete", "usage_missing"} <= set(usage.anomalies)


def test_reasoning_is_never_shown() -> None:
    thought = "THOUGHT_SENTINEL_51"
    reasoning = chunk(None, reasoning=thought)
    event = json.loads(reasoning[len(b"data: ") :])
    event["choices"][0]["delta"] = {"reasoning": thought, "reasoning_details": [{"text": thought}]}
    pieces = _stream(
        _model(
            streaming(
                sse(
                    frame(event),
                    chunk("Line one\n"),
                    chunk("", "stop"),
                    chunk(None, "stop", usage=USAGE),
                )
            )
        )
    )

    assert all(thought not in piece.text for piece in pieces)
    assert thought not in repr(pieces)


def test_content_after_the_finish_is_ignored_and_flagged() -> None:
    late = chunk("INJECTED_AFTER_FINISH", "stop")
    pieces = _stream(
        _model(
            streaming(
                sse(chunk("Line one\n"), chunk("", "stop"), late, chunk(None, "stop", usage=USAGE))
            )
        )
    )

    assert "".join(piece.text for piece in pieces) == "Line one\n"
    assert pieces[-1].usage is not None
    assert "content_after_finish" in pieces[-1].usage.anomalies


def test_a_stream_may_end_after_the_finish_without_done() -> None:
    pieces = _stream(_model(streaming(happy_stream()[:-1])))

    assert pieces[-1].finish_reason == "stop"
    assert pieces[-1].usage is not None and pieces[-1].usage.cost == Decimal("0.00072")


def test_a_stream_that_ends_before_any_finish_fails() -> None:
    assert _stream_error(_model(streaming(sse(chunk("Line one\n"), done=False)))).error_class == (
        "protocol"
    )


def test_a_mid_stream_error_fails_without_keeping_provider_text() -> None:
    secret_text = "PROVIDER_ERROR_TEXT_77"
    error = frame(
        {
            "error": {"code": 502, "message": secret_text, "metadata": {"raw": secret_text}},
            "choices": [{"delta": {"content": ""}, "finish_reason": "error"}],
        }
    )
    failure = _stream_error(_model(streaming(sse(chunk("Line one\n"), error))))

    assert failure.error_class == "upstream_midstream"
    assert secret_text not in str(failure) and secret_text not in repr(failure)


def test_an_error_as_the_only_event_is_a_failure() -> None:
    error = frame({"error": {"code": 503, "message": "x"}})
    assert _stream_error(_model(streaming(sse(error)))).error_class == "upstream_midstream"


def test_an_error_finish_without_an_error_object_is_a_failure() -> None:
    failure = _stream_error(_model(streaming(sse(chunk("Line one\n"), chunk("", "error")))))
    assert failure.error_class == "upstream_midstream"


def test_an_error_frame_after_the_finish_keeps_the_answer() -> None:
    error = frame({"error": {"code": 500, "message": "x"}})
    pieces = _stream(_model(streaming(sse(chunk("Line one\n"), chunk("", "stop"), error))))

    assert "".join(piece.text for piece in pieces) == "Line one\n"
    assert pieces[-1].usage is not None
    assert "read_through_incomplete" in pieces[-1].usage.anomalies


@pytest.mark.parametrize(
    ("reason", "error_class"), [("content_filter", "content_filter"), ("tool_calls", "protocol")]
)
def test_other_documented_finish_reasons_are_failures(reason: str, error_class: str) -> None:
    failure = _stream_error(_model(streaming(sse(chunk("Line one\n"), chunk("", reason)))))
    assert failure.error_class == error_class


def test_the_length_limit_before_any_text_is_reported_as_cut_short() -> None:
    pieces = _stream(
        _model(streaming(sse(chunk("", "length"), chunk(None, "length", usage=USAGE))))
    )

    assert len(pieces) == 1
    assert pieces[0].cut_short and pieces[0].finish_reason == "length" and pieces[0].text == ""


class Slow(httpx.AsyncByteStream):
    def __init__(self, before: list[bytes], after: list[bytes] | None = None) -> None:
        self._before = before
        self._after = after or []

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for item in self._before:
            yield item
        await anyio.sleep(3)
        for item in self._after:
            yield item


def _slow(before: list[bytes]) -> Provider:
    return Provider(lambda _: httpx.Response(200, stream=Slow(before)))


def test_a_deadline_during_content_fails() -> None:
    model = _model(
        _slow([b": OPENROUTER PROCESSING\n\n", chunk("Line one\n")]), llm_timeout_seconds=0.3
    )
    assert _stream_error(model).error_class == "timeout"


def test_a_deadline_during_read_through_keeps_the_answer() -> None:
    model = _model(_slow([chunk("Line one\n"), chunk("", "stop")]), llm_timeout_seconds=0.3)
    pieces = _stream(model)

    assert "".join(piece.text for piece in pieces) == "Line one\n"
    assert pieces[-1].usage is not None and pieces[-1].usage.cost is None
    assert {"read_through_incomplete", "usage_missing"} <= set(pieces[-1].usage.anomalies)


def _padding(count: int) -> list[bytes]:
    return [b": " + b"x" * 60000 + b"\n\n" for _ in range(count)]


def test_the_byte_limit_during_read_through_keeps_the_answer() -> None:
    pieces = _stream(_model(streaming([chunk("Line one\n"), chunk("", "stop"), *_padding(20)])))

    assert "".join(piece.text for piece in pieces) == "Line one\n"
    assert pieces[-1].usage is not None
    assert "read_through_incomplete" in pieces[-1].usage.anomalies


def test_the_byte_limit_during_content_fails() -> None:
    assert _stream_error(_model(streaming([chunk("Line one\n"), *_padding(20)]))).error_class == (
        "protocol"
    )


def test_a_compressed_stream_is_refused() -> None:
    provider = streaming(happy_stream(), **{"content-encoding": "gzip"})
    assert _stream_error(_model(provider)).error_class == "protocol"


@pytest.mark.parametrize(
    "bad",
    [
        frame({"choices": [{"delta": {"content": "a"}}, {"delta": {"content": "b"}}]}),
        b"data: [1, 2]\n\n",
        b"data: {not json\n\n",
        frame({"choices": [{"delta": "text"}]}),
        frame({"choices": [{"delta": {"content": 5}}]}),
        frame({"usage": USAGE}),
    ],
)
def test_an_unreadable_frame_before_the_finish_fails(bad: bytes) -> None:
    assert _stream_error(_model(streaming(sse(bad)))).error_class == "protocol"


# --- routing evidence (T3-12, T3-19) --------------------------------------------------------


def test_a_different_model_in_the_response_is_a_routing_anomaly() -> None:
    other = chunk("", "stop", model="openai/gpt-oss-120b:free")
    pieces = _stream(
        _model(streaming(sse(chunk("Line one\n"), other, chunk(None, "stop", usage=USAGE))))
    )

    assert pieces[-1].usage is not None
    assert "model_mismatch" in pieces[-1].usage.anomalies


@pytest.mark.parametrize(
    ("reported", "anomaly"),
    [("Another Provider", True), ("fictional provider", False), (None, False)],
)
def test_an_undocumented_provider_field_is_advisory(reported: str | None, anomaly: bool) -> None:
    extra = {} if reported is None else {"provider": reported}
    pieces = _stream(
        _model(
            streaming(
                sse(
                    chunk("Line one\n", **extra),
                    chunk("", "stop"),
                    chunk(None, "stop", usage=USAGE),
                )
            )
        )
    )

    assert pieces[-1].usage is not None
    assert ("provider_mismatch" in pieces[-1].usage.anomalies) is anomaly


def test_an_invalid_generation_reference_is_dropped() -> None:
    pieces = _stream(
        _model(streaming(sse(chunk("Line one\n", id="bad id!"), chunk("", "stop", id="bad id!"))))
    )

    usage = pieces[-1].usage
    assert usage is not None and usage.generation_ref is None
    assert "generation_ref_invalid" in usage.anomalies


# --- non-stream (T3-13) ---------------------------------------------------------------------


def test_a_complete_answer_carries_usage_and_reference() -> None:
    answer = _model(answering(completion())).complete(MESSAGES)

    assert isinstance(answer, ModelAnswer)
    assert answer.text == "Line one" and answer.finish_reason == "stop" and not answer.cut_short
    assert answer.usage is not None and answer.usage.cost == Decimal("0.00072")
    assert answer.usage.generation_ref == "gen-1761-test"


def test_a_length_finish_with_content_is_cut_short() -> None:
    answer = _model(answering(completion(finish="length"))).complete(MESSAGES)
    assert answer.cut_short


@pytest.mark.parametrize(
    ("body", "error_class"),
    [
        ({**completion(), "error": {"code": 500, "message": "x"}}, "upstream"),
        (completion(finish="content_filter"), "content_filter"),
        (completion(finish="tool_calls"), "protocol"),
        (completion(finish="error"), "upstream"),
        ({**completion(), "choices": [{"message": {"content": "x"}}]}, "protocol"),
        (completion(content="   ", finish="length"), "empty_content"),
        ({**completion(), "choices": []}, "protocol"),
        ({**completion(), "choices": [{"finish_reason": "stop"}]}, "protocol"),
        ([1, 2], "protocol"),
    ],
)
def test_non_stream_failures_have_closed_classes(body: object, error_class: str) -> None:
    provider = answering(body)
    assert _complete_error(_model(provider)).error_class == error_class
    _one_request(provider)


def test_an_unreadable_or_oversized_body_fails() -> None:
    garbage = Provider(lambda _: httpx.Response(200, content=b"{not json"))
    assert _complete_error(_model(garbage)).error_class == "protocol"
    huge = Provider(lambda _: httpx.Response(200, content=b" " * (1024 * 1024 + 1)))
    assert _complete_error(_model(huge)).error_class == "protocol"


# --- status classes and call counts (T3-14) -------------------------------------------------


STATUSES = [
    (400, "bad_request"),
    (401, "auth"),
    (402, "payment"),
    (403, "forbidden"),
    (404, "not_allowed"),
    (408, "timeout"),
    (429, "rate_limited"),
    (500, "upstream"),
    (502, "upstream"),
    (503, "no_provider"),
    (504, "upstream"),
    (418, "http_other"),
]


@pytest.mark.parametrize(("status", "error_class"), STATUSES)
@pytest.mark.parametrize("stream", [True, False])
def test_each_status_has_one_request_no_retry_and_a_closed_class(
    status: int, error_class: str, stream: bool
) -> None:
    provider = answering({"error": {"code": status, "message": "provider words"}}, status=status)
    model = _model(provider)
    failure = _stream_error(model) if stream else _complete_error(model)

    assert failure.error_class == error_class
    assert "provider words" not in str(failure)
    _one_request(provider)


@pytest.mark.parametrize("stream", [True, False])
def test_an_exhausted_key_limit_is_its_own_class(stream: bool) -> None:
    body = {
        "error": {"code": 402, "message": "x", "metadata": {"limit_source": "openrouter_key_limit"}}
    }
    model = _model(answering(body, status=402))
    failure = _stream_error(model) if stream else _complete_error(model)

    assert failure.error_class == "payment_key_limit"


def test_a_transport_failure_is_classified() -> None:
    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    assert _complete_error(_model(Provider(broken))).error_class == "transport"
    assert _stream_error(_model(Provider(broken))).error_class == "transport"


# --- prompt size (T3-21) --------------------------------------------------------------------


def test_a_prompt_above_the_size_limit_is_refused_before_any_request() -> None:
    provider = streaming(happy_stream())
    model = _model(provider, remote_max_prompt_bytes=1024)
    big = [{"role": "user", "content": "x" * 2000}]

    with pytest.raises(ModelCallError) as raised:
        model.complete(big)
    assert raised.value.error_class == "prompt_too_large"
    with pytest.raises(ModelCallError):
        _stream(model, big)
    assert provider.requests == []


# --- secret hygiene and proxies (T3-15) -----------------------------------------------------


def test_the_key_appears_only_in_the_outgoing_header(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    failures: list[BaseException] = []
    success = streaming(happy_stream())
    _stream(_model(success))
    _model(answering(completion())).complete(MESSAGES)
    failures.append(_stream_error(_model(answering({"error": {"code": 401}}, status=401))))
    failures.append(_stream_error(_model(streaming(sse(frame({"error": {}}))))))
    failures.append(_complete_error(_model(answering({"error": {"code": 401}}, status=401))))
    failures.append(_complete_error(_model(answering({**completion(), "error": {}}))))

    assert _one_request(success).headers["authorization"] == "Bearer " + SENTINEL_KEY
    assert SENTINEL_KEY not in caplog.text
    assert all(SENTINEL_KEY not in f"{error!s} {error!r}" for error in failures)
    assert SENTINEL_KEY not in repr(_model(success))


@pytest.mark.parametrize("stream", [True, False])
def test_proxy_settings_in_the_environment_are_ignored(
    monkeypatch: pytest.MonkeyPatch, stream: bool
) -> None:
    for name in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "https_proxy", "all_proxy"):
        monkeypatch.setenv(name, "http://192.0.2.1:8080")
    provider = streaming(happy_stream()) if stream else answering(completion())
    model = _model(provider)
    _stream(model) if stream else model.complete(MESSAGES)

    _one_request(provider)


# --- through the service: notices unchanged, content-free metrics v2 (T3-10, T3-16, T3-17) ---


def _service(provider: Provider, sink: MemorySink) -> Any:
    return _app(_model(provider), metrics=sink)


def test_a_remote_answer_through_the_service_records_content_free_v2_metrics() -> None:
    sink = MemorySink()
    client = _service(streaming(happy_stream(ALLOWED + "\n")), sink)
    response = client.post(STREAM, json={"message": "What should I do next?"})
    done = json.loads(response.text.strip().splitlines()[-1])
    client = _service(answering(completion(ALLOWED)), sink)
    reply = client.post(CHAT, json={"message": "What should I do next?"}).json()

    assert done["answered_by"] == "model" and reply["answered_by"] == "model"
    assert done["answer"] == ALLOWED and reply["answer"] == ALLOWED
    for record in sink.records:
        assert record.profile == "openrouter_gpt_oss_120b"
        assert record.requested_endpoint == ENDPOINT.slug
        assert record.provider_verified is False
        assert record.usage is not None and record.usage.cost_micro_usd == 720
        assert record.finish_reason == "stop" and record.provider_error_class is None
        text = record.to_json()
        assert "gen-1761-test" not in text and SENTINEL_KEY not in text
        assert "What should I do next" not in text and ALLOWED not in text


def test_reasoning_that_uses_the_whole_limit_keeps_todays_notice() -> None:
    sink = MemorySink()
    client = _service(streaming(sse(chunk("", "length"), chunk(None, "length", usage=USAGE))), sink)
    done = json.loads(
        client.post(STREAM, json={"message": "What should I do next?"})
        .text.strip()
        .splitlines()[-1]
    )

    assert done["answered_by"] == "case_data" and done["notice"] == POLICY_NOTICE
    record = sink.records[0]
    assert record.empty_content and record.fallback_reason == "policy_no_allowed_line"


def test_an_empty_complete_answer_keeps_todays_fallback_notice() -> None:
    sink = MemorySink()
    client = _service(answering(completion(content="", finish="length")), sink)
    reply = client.post(CHAT, json={"message": "What should I do next?"}).json()

    assert reply["answered_by"] == "case_data" and reply["notice"] == FALLBACK_NOTICE
    record = sink.records[0]
    assert record.empty_content and record.provider_error_class == "empty_content"
    assert record.fallback_reason == "model_unavailable"


@pytest.mark.parametrize("reason", ["content_filter", "tool_calls"])
def test_a_failed_remote_stream_keeps_todays_fallback(reason: str) -> None:
    sink = MemorySink()
    client = _service(streaming(sse(chunk("", reason))), sink)
    done = json.loads(
        client.post(STREAM, json={"message": "What should I do next?"})
        .text.strip()
        .splitlines()[-1]
    )

    assert done["answered_by"] == "case_data" and done["notice"] == FALLBACK_NOTICE
    assert sink.records[0].fallback_reason == "model_unavailable"


def test_a_remote_answer_cut_short_keeps_todays_notice() -> None:
    sink = MemorySink()
    client = _service(answering(completion(ALLOWED, finish="length")), sink)
    reply = client.post(CHAT, json={"message": "What should I do next?"}).json()

    assert reply["answered_by"] == "model" and CUT_SHORT_NOTICE in reply["notice"]


# --- the single request path (T3-18) --------------------------------------------------------


def test_no_other_provider_endpoint_or_attribution_header_exists_in_the_code() -> None:
    sources = [
        *ASSISTANT.joinpath("ai_assistant").rglob("*.py"),
        *ASSISTANT.joinpath("scripts").rglob("*.py"),
    ]
    forbidden = ("/generation", "/api/v1/key", "endpoints/zdr", "HTTP-Referer", "X-Title")
    for path in sources:
        text = path.read_text(encoding="utf-8")
        for word in forbidden:
            assert word not in text, f"{word} in {path.name}"
