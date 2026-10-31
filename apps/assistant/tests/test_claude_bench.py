"""Claude API benchmark controls (evaluation only).

Offline: the SDK talks to an in-memory transport, and the suite's socket guard (conftest)
refuses any real connection. The key is a sentinel searched for in every output.
"""

import importlib.util
import json
import sys
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any

import anyio
import pytest

from ai_assistant.llm import ModelCallError, Piece
from assistant_eval import claude_bench as cb
from assistant_eval.runner import Workspace, run
from assistant_eval.scenarios import EVAL_FIXTURES, load_scenarios

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_claude.py"
PHASE_B = EVAL_FIXTURES / "phase_b_questions.json"
# Built at run time so the secret scanner never sees a key-shaped literal.
SENTINEL = "sk-" + "ant-" + "api03-" + "S3nt1nelBenchKey" * 4
ENVIRON = {cb.KEY_VARIABLE: SENTINEL}
SYSTEM = [{"role": "system", "content": "RULES"}, {"role": "system", "content": "CASE FACTS"}]
MESSAGES = [*SYSTEM, {"role": "user", "content": "Is this case ready for review?"}]


def _script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("benchmark_claude", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ledger(tmp_path: Path, **changes: int) -> cb.ClaudeLedger:
    values = {"cap_micro_usd": 6_000_000, "per_call_micro_usd": 100_000, "call_limit": 51}
    return cb.ClaudeLedger.create(tmp_path / "ledger.sqlite3", **{**values, **changes})


# --- settings, mapping and money ------------------------------------------------------------


def test_only_approved_models_and_settings() -> None:
    with pytest.raises(cb.BenchConfigError):
        cb.BenchConfig("gpt-oss")
    with pytest.raises(cb.BenchConfigError):
        cb.BenchConfig("opus", thinking="off")  # Opus 5.5 cannot turn thinking off
    with pytest.raises(cb.BenchConfigError):
        cb.BenchConfig("haiku", effort="max")
    with pytest.raises(cb.BenchConfigError):
        cb.BenchConfig("haiku", max_tokens=8000)
    assert cb.BenchConfig("haiku", thinking="off").request_fields()["thinking"] == {
        "type": "disabled"
    }
    assert cb.BenchConfig("sonnet", thinking="off").request_fields()["thinking"] == {
        "type": "between_tools"
    }


def test_request_fields_send_no_sampling_tools_or_fallbacks() -> None:
    fields = cb.BenchConfig("sonnet").request_fields()
    assert fields == {
        "max_tokens": 3000,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": "medium"},
    }
    assert (
        cb.BenchConfig("sonnet").fingerprint()
        != cb.BenchConfig("sonnet", effort="low").fingerprint()
    )


def test_leading_system_messages_become_system_blocks_in_order() -> None:
    system, conversation = cb.to_anthropic(MESSAGES)
    assert system == [{"type": "text", "text": "RULES"}, {"type": "text", "text": "CASE FACTS"}]
    assert conversation == [{"role": "user", "content": "Is this case ready for review?"}]


@pytest.mark.parametrize(
    "messages",
    [
        # The service's knowledge/topic messages after history: no faithful place, refused.
        [
            *SYSTEM,
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
            {"role": "system", "content": "TOPIC"},
            {"role": "user", "content": "c"},
        ],
        [*SYSTEM, {"role": "assistant", "content": "b"}],
        [{"role": "user", "content": "no system prompt"}],
        SYSTEM,
    ],
)
def test_prompts_that_cannot_be_sent_unchanged_are_refused(messages: list[dict[str, str]]) -> None:
    with pytest.raises(cb.UnsupportedPromptError):
        cb.to_anthropic(messages)


def test_reservation_and_cost_use_the_published_prices() -> None:
    opus = cb.APPROVED_MODELS["opus"]
    # 4,000 input at US$4/M x 1.25 = 0.02, 3,000 output at US$20/M = 0.06.
    assert cb.reservation_micro(opus, 4000, 3000) == 80_000
    usage = cb.Usage(input_tokens=4000, output_tokens=500)
    assert cb.cost_micro(opus, usage) == 26_000
    haiku = cb.APPROVED_MODELS["haiku"]
    assert cb.cost_micro(haiku, cb.Usage(input_tokens=4000, output_tokens=500)) == 650
    assert cb.price_anomalies(cb.Usage(1, 1, inference_geo="us", speed="fast")) == [
        "inference_geo",
        "speed",
    ]


def test_key_problems_are_described_without_the_value() -> None:
    assert cb.key_problem(ENVIRON) is None
    assert cb.read_key({cb.KEY_VARIABLE: f"  {SENTINEL}\r\n"}) == SENTINEL
    assert cb.key_problem({}) == "missing"
    for bad in (
        SENTINEL[:-1] + "!",
        "sk-" + "ant-" + "admin01-" + "x" * 40,
        "sk-" + "ant-" + "sid01-" + "x" * 40,
        SENTINEL[:20],
    ):
        problem = cb.key_problem({cb.KEY_VARIABLE: bad})
        assert problem is not None and bad not in problem and bad[13:25] not in problem


def test_the_key_comes_only_from_the_benchmark_variable() -> None:
    assert cb.read_key(ENVIRON) == SENTINEL
    for environ in ({}, {"ANTHROPIC_API_KEY": SENTINEL}, {cb.KEY_VARIABLE: "not-a-key"}):
        with pytest.raises(cb.LedgerRefusedError):
            cb.read_key(environ)


# --- ledger ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "changes",
    [{"cap_micro_usd": 6_000_001}, {"per_call_micro_usd": 100_001}, {"call_limit": 52}],
)
def test_ledger_limits_cannot_exceed_the_owner_ceilings(
    tmp_path: Path, changes: dict[str, int]
) -> None:
    with pytest.raises(cb.LedgerRefusedError):
        _ledger(tmp_path, **changes)


def _reserve(ledger: cb.ClaudeLedger, amount: int = 50_000) -> int:
    return ledger.reserve(
        run_label="t",
        turn="P00#0@0",
        model_id="claude-haiku-5-5",
        config_fingerprint="f",
        prompt="p",
        reserved_micro_usd=amount,
    )


def _close(ledger: cb.ClaudeLedger, call: int, charged: int | None, *anomalies: str) -> int:
    return ledger.close_call(
        call,
        charged_micro_usd=charged,
        response_model="claude-haiku-5-5",
        message_id=None,
        stop_reason="end_turn",
        error_class=None,
        usage=None,
        timings={},
        anomalies=list(anomalies),
    )


def test_ledger_admits_one_call_at_a_time_within_cap_ceiling_and_count(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, cap_micro_usd=100_500, call_limit=3)
    call = _reserve(ledger)
    with pytest.raises(cb.LedgerRefusedError, match="call_open"):
        _reserve(ledger)
    _close(ledger, call, 1_000)
    with pytest.raises(cb.LedgerRefusedError, match="per_call_ceiling"):
        _reserve(ledger, 100_001)
    with pytest.raises(cb.LedgerRefusedError, match="run_cap"):
        _reserve(ledger, 100_000)
    _close(ledger, _reserve(ledger, 60_000), None)  # unknown cost: charged its reservation
    status = ledger.status()
    assert status.committed_micro_usd == 61_000 and status.conservative_micro_usd == 60_000
    _close(ledger, _reserve(ledger, 1_000), 10)
    with pytest.raises(cb.LedgerRefusedError, match="call_limit"):
        _reserve(ledger, 1)


def test_anomalies_and_overcharges_open_the_breaker(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    _close(ledger, _reserve(ledger, 1_000), 2_000)
    assert ledger.status().breaker_code == "cost_above_reservation"
    with pytest.raises(cb.LedgerRefusedError, match="breaker_open"):
        _reserve(ledger)
    other = _ledger(tmp_path / "b")
    _close(other, _reserve(other), 10, "model_mismatch")
    assert other.status().breaker_code == "model_mismatch"


def test_console_usage_above_the_ledger_opens_the_breaker(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    _close(ledger, _reserve(ledger), 20_000)
    assert ledger.record_provider_usage(25_000, 10_000) == "within_ledger"
    assert not ledger.status().breaker_open
    assert ledger.record_provider_usage(40_000, 10_000) == "above_ledger"
    assert ledger.status().breaker_code == "provider_discrepancy"


# --- the model, against an in-memory Messages API -------------------------------------------


def _sdk_or_skip() -> Any:
    try:
        return cb.load_sdk()
    except ImportError:
        pytest.skip("the anthropic SDK is not installed (scripts/benchmark_claude.py docstring)")


def _sse(*events: dict[str, Any]) -> bytes:
    return b"".join(
        f"event: {event['type']}\ndata: {json.dumps(event)}\n\n".encode() for event in events
    )


def _stream_body(
    text: str, *, model: str = "claude-haiku-5-5", stop: str = "end_turn", thinking: bool = True
) -> bytes:
    events: list[dict[str, Any]] = [
        {
            "type": "message_start",
            "message": {
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": model,
                "content": [],
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 4000, "output_tokens": 1},
            },
        }
    ]
    index = 0
    if thinking:
        events += [
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "thinking", "thinking": "", "signature": ""},
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "signature_delta", "signature": "c2ln"},
            },
            {"type": "content_block_stop", "index": 0},
        ]
        index = 1
    events += [
        {
            "type": "content_block_start",
            "index": index,
            "content_block": {"type": "text", "text": ""},
        },
        {
            "type": "content_block_delta",
            "index": index,
            "delta": {"type": "text_delta", "text": text},
        },
        {"type": "content_block_stop", "index": index},
        {
            "type": "message_delta",
            "delta": {"stop_reason": stop, "stop_sequence": None},
            "usage": {"output_tokens": 500},
        },
        {"type": "message_stop"},
    ]
    return _sse(*events)


class Api:
    """The Messages API in memory: records each request, answers from a queue."""

    def __init__(self, *replies: tuple[int, bytes]) -> None:
        self.replies = list(replies)
        self.requests: list[Any] = []

    def transport(self) -> Any:
        httpx2 = __import__("httpx2")

        def handler(request: Any) -> Any:
            self.requests.append(request)
            status, body = self.replies.pop(0)
            headers = {"content-type": "text/event-stream" if status == 200 else "application/json"}
            return httpx2.Response(status, content=body, headers=headers)

        return httpx2.MockTransport(handler)


def _model(
    tmp_path: Path,
    api: Api,
    *,
    alias: str = "haiku",
    counted: dict[str, int] | None = None,
    environ: dict[str, str] | None = None,
) -> tuple[cb.ClaudeBenchModel, cb.ClaudeLedger]:
    _sdk_or_skip()
    ledger = _ledger(tmp_path)
    model = cb.ClaudeBenchModel(
        cb.BenchConfig(alias),
        ledger,
        counted=counted if counted is not None else {cb.prompt_sha(MESSAGES): 4000},
        run_label="test",
        environ=ENVIRON if environ is None else environ,
        transport=api.transport(),
    )
    model.begin("P04#0", 0)
    return model, ledger


def _collect(model: cb.ClaudeBenchModel, messages: list[dict[str, str]]) -> list[Piece]:
    pieces, error = _partial(model, messages)
    if error is not None:
        raise error
    return pieces


def _partial(
    model: cb.ClaudeBenchModel, messages: list[dict[str, str]]
) -> tuple[list[Piece], ModelCallError | None]:
    pieces: list[Piece] = []

    async def gather() -> ModelCallError | None:
        try:
            async for piece in model.stream(messages):
                pieces.append(piece)
        except ModelCallError as error:
            return error
        return None

    return pieces, anyio.run(gather)


def test_a_call_is_pinned_settled_and_content_free(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A base URL or token in the environment (Claude Code sets one) must never be used.
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "other-token")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    api = Api((200, _stream_body("Line one.")))
    model, ledger = _model(tmp_path, api)
    pieces = _collect(model, MESSAGES)
    assert "".join(p.text for p in pieces) == "Line one."
    last = pieces[-1]
    assert last.finish_reason == "stop" and not last.cut_short
    assert last.usage is not None and last.usage.prompt_tokens == 4000
    assert last.usage.cost == Decimal("0.00065")
    request = api.requests[0]
    assert str(request.url) == "https://api.anthropic.com/v1/messages"
    # SDK 2.x sends an API key as a bearer credential; only ours, never the environment's.
    assert request.headers["authorization"] == f"Bearer {SENTINEL}"
    assert "x-api-key" not in request.headers and "anthropic-beta" not in request.headers
    body = json.loads(request.content)
    assert body["model"] == "claude-haiku-5-5"
    assert body["system"] == [
        {"type": "text", "text": "RULES"},
        {"type": "text", "text": "CASE FACTS"},
    ]
    assert body["thinking"] == {"type": "adaptive"}
    assert body["output_config"] == {"effort": "medium"}
    assert set(body) == {
        "model",
        "system",
        "messages",
        "max_tokens",
        "thinking",
        "output_config",
        "stream",
    }
    status = ledger.status()
    assert status.settled_micro_usd == 650 and not status.breaker_open
    [call] = ledger.calls()
    assert call["state"] == "settled" and call["response_model"] == "claude-haiku-5-5"
    assert json.loads(call["timings_json"])["first_block"] is not None
    stored = (tmp_path / "ledger.sqlite3").read_bytes()
    assert SENTINEL.encode() not in stored and b"Line one" not in stored
    assert SENTINEL not in json.dumps([r.__dict__ for r in model.records])


@pytest.mark.parametrize("name", cb.SDK_ENVIRONMENT_REFUSED)
def test_sdk_environment_that_adds_headers_or_logs_requests_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.setenv(name, "debug")
    api = Api()
    model, ledger = _model(tmp_path, api)
    pieces, error = _partial(model, MESSAGES)
    assert error is not None and error.error_class == "not_allowed"
    assert api.requests == [] and ledger.calls() == []
    assert model.records[-1].refused == "sdk_environment"


def test_another_model_answering_stops_before_any_text(tmp_path: Path) -> None:
    api = Api((200, _stream_body("Line one.", model="claude-opus-5-5")))
    model, ledger = _model(tmp_path, api)
    pieces, error = _partial(model, MESSAGES)
    assert error is not None and error.error_class == "protocol" and pieces == []
    status = ledger.status()
    assert status.breaker_code == "model_mismatch"
    assert status.conservative_micro_usd == cb.reservation_micro(
        cb.APPROVED_MODELS["haiku"], 4000, 3000
    )


@pytest.mark.parametrize(
    ("status", "error_class", "stops"),
    [
        (401, "auth", True),
        (400, "bad_request", True),
        (429, "rate_limited", False),
        (529, "upstream", False),
    ],
)
def test_errors_are_closed_classes_charged_at_reservation(
    tmp_path: Path, status: int, error_class: str, stops: bool
) -> None:
    body = json.dumps({"type": "error", "error": {"type": "x", "message": "m"}}).encode()
    api = Api((status, body))
    model, ledger = _model(tmp_path, api)
    with pytest.raises(ModelCallError) as error:
        _collect(model, MESSAGES)
    assert error.value.error_class == error_class
    assert len(api.requests) == 1  # no retries
    state = ledger.status()
    assert state.breaker_open is stops
    assert state.conservative_micro_usd > 0


def test_refusal_and_truncation_are_reported(tmp_path: Path) -> None:
    api = Api((200, _stream_body("", stop="refusal", thinking=False)))
    model, ledger = _model(tmp_path, api)
    with pytest.raises(ModelCallError) as error:
        _collect(model, MESSAGES)
    assert error.value.error_class == "content_filter"
    assert ledger.calls()[0]["state"] == "settled"
    api2 = Api((200, _stream_body("Line", stop="max_tokens")))
    model2, _ = _model(tmp_path / "b", api2)
    pieces = _collect(model2, MESSAGES)
    assert pieces[-1].cut_short and pieces[-1].finish_reason == "length"


@pytest.mark.parametrize(
    ("messages", "counted", "environ", "code"),
    [
        # Outside the D-094 synthetic text boundary (non-ASCII): refused before anything.
        ([*SYSTEM, {"role": "user", "content": "Ünknown"}], None, None, "synthetic_text"),
        (MESSAGES, {}, None, "prompt_not_approved"),
        (MESSAGES, None, {}, "credential_missing_or_malformed"),
    ],
)
def test_refusals_send_nothing(
    tmp_path: Path, messages: Any, counted: Any, environ: Any, code: str
) -> None:
    api = Api()
    model, ledger = _model(tmp_path, api, counted=counted, environ=environ)
    with pytest.raises(ModelCallError):
        _collect(model, messages)
    assert api.requests == [] and ledger.calls() == []
    assert model.records[-1].refused == code
    # A refusal is a privacy or spending-control failure: the run stops.
    assert ledger.status().breaker_code == f"refused_{code}"


# --- through the real service ----------------------------------------------------------------


def _offline_harness_answer(tmp_path: Path, text_for: Any) -> Any:
    _sdk_or_skip()
    build_prompts = _script().build_prompts

    scenarios = load_scenarios(PHASE_B)
    prompts, preps = build_prompts(scenarios)
    key = "P04#0"
    counted = {cb.prompt_sha(prompts[key]): 4000}
    api = Api((200, _stream_body(text_for(preps[key]))))
    ledger = _ledger(tmp_path)
    model = cb.ClaudeBenchModel(
        cb.BenchConfig("haiku"),
        ledger,
        counted=counted,
        run_label="t",
        environ=ENVIRON,
        transport=api.transport(),
    )
    with Workspace() as workspace:
        result = run(scenarios, lambda capture: model, workspace=workspace, turns=frozenset({key}))
    return result.turns[0], ledger


def test_through_the_service_allowed_lines_show_and_prose_is_withheld(tmp_path: Path) -> None:
    from assistant_eval.snapshot import offered_lines  # noqa: PLC0415

    turn, ledger = _offline_harness_answer(tmp_path, lambda prep: offered_lines(prep)[0][2])
    assert turn.answered_by == "model" and turn.unmapped == 0 and len(turn.shown) == 1
    assert ledger.status().settled_micro_usd == 650
    prose, _ = _offline_harness_answer(tmp_path / "b", lambda prep: "Sure, it is approved.")
    assert prose.answered_by == "case_data" and prose.unmapped == 0


# --- review remediation (QG F1-F7) ----------------------------------------------------------


@pytest.mark.parametrize("asynchronous", [True, False])
def test_the_real_client_never_routes_through_a_proxy(
    monkeypatch: pytest.MonkeyPatch, asynchronous: bool
) -> None:
    # The SDK's default clients mount proxies from getproxies() unless given a transport.
    httpx2 = _sdk_or_skip() and __import__("httpx2")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:9")
    make = cb.make_async_client if asynchronous else cb.make_client
    client = make(SENTINEL)
    http = client._client
    transport = http._transport_for_url(httpx2.URL("https://api.anthropic.com/v1/messages"))
    assert "Proxy" not in type(transport._pool).__name__
    assert not http._mounts


def _usage_body(usage: dict[str, Any], *, at_start: bool) -> bytes:
    """The live API reports tier, geography and speed in message_start's usage."""

    body = _stream_body("Line one.", model="claude-opus-5-5")
    if at_start:
        start = {"input_tokens": 4000, "output_tokens": 1, **usage}
        return body.replace(
            b'"usage": {"input_tokens": 4000, "output_tokens": 1}',
            json.dumps({"usage": start})[1:-1].encode(),
        )
    replacement = json.dumps({"usage": {"output_tokens": 500, **usage}})[1:-1].encode()
    return body.replace(b'"usage": {"output_tokens": 500}', replacement)


@pytest.mark.parametrize(
    ("usage", "anomaly"),
    [
        ({"speed": "fast"}, "speed"),
        ({"inference_geo": "us"}, "inference_geo"),
        ({"service_tier": "priority"}, "service_tier"),
        ({"cache_read_input_tokens": 100}, "unrequested_cache"),
    ],
)
def test_price_anomalies_through_the_stream_are_charged_conservatively(
    tmp_path: Path, usage: dict[str, Any], anomaly: str
) -> None:
    api = Api((200, _usage_body(usage, at_start=anomaly != "unrequested_cache")))
    model, ledger = _model(tmp_path, api, alias="opus")
    pieces, error = _partial(model, MESSAGES)
    assert error is None
    [call] = ledger.calls()
    reserved = cb.reservation_micro(cb.APPROVED_MODELS["opus"], 4000, 3000)
    assert call["state"] == "charged_reservation"
    assert call["charged_micro_usd"] >= reserved  # never the standard price
    assert anomaly in call["anomalies"]
    assert ledger.status().breaker_open


def test_missing_input_tokens_are_an_anomaly(tmp_path: Path) -> None:
    body = _stream_body("Line one.").replace(b'"input_tokens": 4000', b'"input_tokens": 0')
    model, ledger = _model(tmp_path, Api((200, body)))
    _partial(model, MESSAGES)
    assert ledger.status().breaker_code == "usage_missing"


def test_abandoning_the_stream_charges_the_reservation_once(tmp_path: Path) -> None:
    api = Api((200, _stream_body("Line one.")))
    model, ledger = _model(tmp_path, api)

    async def first_piece_then_close() -> None:
        source = model.stream(MESSAGES)
        piece = await source.__anext__()
        assert piece.text == "Line one."
        await source.aclose()

    anyio.run(first_piece_then_close)
    [call] = ledger.calls()
    assert call["state"] == "charged_reservation" and call["error_class"] == "upstream_midstream"
    assert ledger.status().open_calls == 0


def test_the_whole_call_has_one_deadline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    httpx2 = _sdk_or_skip() and __import__("httpx2")
    monkeypatch.setattr(cb, "TIMEOUT_SECONDS", 0.2)

    async def slow(request: Any) -> Any:
        await anyio.sleep(2)
        return httpx2.Response(200, content=_stream_body("late"))

    ledger = _ledger(tmp_path)
    model = cb.ClaudeBenchModel(
        cb.BenchConfig("haiku"),
        ledger,
        counted={cb.prompt_sha(MESSAGES): 4000},
        run_label="t",
        environ=ENVIRON,
        transport=httpx2.MockTransport(slow),
    )
    pieces, error = _partial(model, MESSAGES)
    assert error is not None and error.error_class == "timeout" and pieces == []
    [call] = ledger.calls()
    assert call["state"] == "charged_reservation" and not ledger.status().breaker_open


def test_run_stops_all_requests_when_the_breaker_opens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    httpx2 = _sdk_or_skip() and __import__("httpx2")
    script = _script()
    monkeypatch.setattr(script, "OUT", tmp_path)
    monkeypatch.setattr(script, "APPROVED", tmp_path / "approved_prompts.json")
    script._select_ledger("speed")
    monkeypatch.setattr(script, "LEDGER", tmp_path / "speed.sqlite3")
    monkeypatch.setattr(script, "PREFLIGHT", tmp_path / "preflight-speed.json")
    prompts, _ = script.build_prompts(script._scenarios())
    configs = [cb.BenchConfig(a, effort="low", thinking="off") for a in ("haiku", "sonnet")]
    cb.ClaudeLedger.create(
        script.LEDGER, cap_micro_usd=1_500_000, per_call_micro_usd=100_000, call_limit=34
    )
    script._write_json(
        script.PREFLIGHT,
        {
            "passed": True,
            "at": script.datetime.now(script.UTC).isoformat(),
            "prompt_version": script.prompt_version(),
            "configs": {c.alias: {"fingerprint": c.fingerprint()} for c in configs},
            "models": {},
            "counted": {
                c.alias: {cb.prompt_sha(m): 4000 for m in prompts.values()} for c in configs
            },
        },
    )
    requests: list[Any] = []

    def wrong_model(request: Any) -> Any:
        requests.append(request)
        return httpx2.Response(
            200,
            content=_stream_body("x", model="claude-opus-5-5"),
            headers={"content-type": "text/event-stream"},
        )

    original = cb.make_async_client
    monkeypatch.setattr(
        cb,
        "make_async_client",
        lambda key, transport=None: original(key, httpx2.MockTransport(wrong_model)),
    )
    monkeypatch.setenv(cb.KEY_VARIABLE, SENTINEL)
    args = script.argparse.Namespace(
        models="haiku,sonnet",
        effort="low",
        thinking="off",
        max_tokens=3000,
        expect_calls=34,
        label="t",
    )
    assert script.cmd_run(args) == 4
    assert len(requests) == 1  # the provider mismatch stopped every later request
    assert cb.ClaudeLedger(script.LEDGER).status().breaker_code == "model_mismatch"
    stale = json.loads(script.PREFLIGHT.read_text(encoding="utf-8"))
    stale["at"] = "2026-01-01T00:00:00+00:00"
    script._write_json(script.PREFLIGHT, stale)
    assert script._usable_preflight(configs) == "the preflight is older than 12 hours"
