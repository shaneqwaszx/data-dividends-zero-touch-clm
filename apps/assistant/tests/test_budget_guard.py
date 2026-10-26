"""The budget guard around the dormant remote adapter (Phase A2, D-091 proposed).

T4-02 refusals reuse today's fallback, T4-04/05/07 settlement through the guard, T4-06
cancellation, T4-14 the default profile never touches a ledger, and the full service path.
Mock transports and synthetic ledgers only.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

import anyio
import httpx
import pytest

from ai_assistant.budget import BudgetedChatModel, BudgetLedger
from ai_assistant.config import AiAssistantSettings
from ai_assistant.llm import ModelCallError, Piece
from ai_assistant.main import FALLBACK_NOTICE, create_app
from ai_assistant.model_factory import build_chat_model, ledger_path
from ai_assistant.telemetry import MemorySink
from tests.remote_fixtures import (
    ENVIRON,
    MESSAGES,
    TEST_REGISTRY,
    USAGE,
    Provider,
    answering,
    chunk,
    completion,
    happy_stream,
    new_ledger,
    remote_settings,
    sse,
    streaming,
)
from tests.test_ai_assistant import FakeBackend
from tests.test_telemetry import ALLOWED, CHAT, STREAM, _app

QUESTION = {"message": "What should I do next?"}


def _guarded(provider: Provider, ledger: Path, **settings: Any) -> BudgetedChatModel:
    model = build_chat_model(
        remote_settings(**settings),
        transport=provider.transport(),
        environ=ENVIRON,
        registry=TEST_REGISTRY,
        budget_ledger=ledger,
    )
    assert isinstance(model, BudgetedChatModel)
    return model


def _done(response: httpx.Response) -> dict[str, Any]:
    event: dict[str, Any] = json.loads(response.text.strip().splitlines()[-1])
    return event


def _status(path: Path) -> Any:
    return BudgetLedger.open(path).status()


# --- refusals use today's fallback and send nothing (T4-02) ----------------------------------


@pytest.mark.parametrize("route", ["chat", "stream"])
def test_a_refusal_at_the_cap_gives_todays_fallback_and_no_request(
    tmp_path: Path, route: str
) -> None:
    path = new_ledger(tmp_path / "ledger.sqlite3", cap=7_000_000, opening=6_999_999)
    provider = (
        streaming(happy_stream(ALLOWED + "\n"))
        if route == "stream"
        else answering(completion(ALLOWED))
    )
    sink = MemorySink()
    client = _app(_guarded(provider, path), metrics=sink)

    if route == "stream":
        body = _done(client.post(STREAM, json=QUESTION))
    else:
        body = client.post(CHAT, json=QUESTION).json()

    assert body["answered_by"] == "case_data" and body["notice"] == FALLBACK_NOTICE
    assert provider.requests == []
    record = sink.records[0]
    assert record.fallback_reason == "budget_refused"
    assert record.provider_error_class == "budget_refused"
    assert record.budget is not None and record.budget.outcome == "refused_cap"
    assert _status(path).committed == 6_999_999


def test_an_open_breaker_refuses_with_no_request(tmp_path: Path) -> None:
    path = new_ledger(tmp_path / "ledger.sqlite3")
    BudgetLedger.open(path).open_breaker("usage_missing")
    provider = answering(completion(ALLOWED))

    with pytest.raises(ModelCallError) as raised:
        _guarded(provider, path).complete(MESSAGES)
    assert raised.value.error_class == "budget_refused"
    assert raised.value.budget is not None and raised.value.budget.outcome == "refused_breaker"
    assert provider.requests == []


@pytest.mark.parametrize("route", ["chat", "stream"])
def test_a_prompt_above_the_size_limit_is_refused_before_any_reservation(
    tmp_path: Path, route: str
) -> None:
    """QG F-1: nothing is reserved or charged for a prompt the adapter would refuse."""

    path = new_ledger(tmp_path / "ledger.sqlite3")
    provider = streaming(happy_stream()) if route == "stream" else answering(completion(ALLOWED))
    model = _guarded(provider, path, remote_max_prompt_bytes=1024)
    big = [{"role": "user", "content": "x" * 5000}]

    async def stream() -> None:
        async for _ in model.stream(big):
            pass

    with pytest.raises(ModelCallError) as raised:
        anyio.run(stream) if route == "stream" else model.complete(big)
    assert raised.value.error_class == "prompt_too_large"
    status = _status(path)
    assert (status.committed, status.open_calls, status.local_charged) == (0, 0, 0)
    assert provider.requests == []
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM calls").fetchone()[0] == 0


# --- settlement through the guard ------------------------------------------------------------


def test_a_remote_answer_is_settled_at_its_reported_cost(tmp_path: Path) -> None:
    path = new_ledger(tmp_path / "ledger.sqlite3")
    sink = MemorySink()
    client = _app(_guarded(streaming(happy_stream(ALLOWED + "\n")), path), metrics=sink)
    done = _done(client.post(STREAM, json=QUESTION))

    # The model's line, plus any of the topic's required lines the service adds (D-090).
    lines = done["answer"].splitlines()
    assert done["answered_by"] == "model" and lines.index(ALLOWED) not in done["added_lines"]
    status = _status(path)
    assert (status.local_charged, status.open_reserved, status.open_calls) == (720, 0, 0)
    record = sink.records[0]
    assert record.budget is not None
    assert (record.budget.outcome, record.budget.charged_micro_usd) == ("settled", 720)
    assert record.budget.reserved_micro_usd > 720
    assert record.usage is not None and record.usage.cost_micro_usd == 720


def test_a_complete_answer_is_settled_too(tmp_path: Path) -> None:
    path = new_ledger(tmp_path / "ledger.sqlite3")
    answer = _guarded(answering(completion(ALLOWED)), path).complete(MESSAGES)

    assert answer.budget is not None and answer.budget.charged_micro_usd == 720
    assert _status(path).local_charged == 720


def test_missing_usage_stops_the_next_call_before_any_request(tmp_path: Path) -> None:
    path = new_ledger(tmp_path / "ledger.sqlite3")
    first = streaming(sse(chunk(ALLOWED + "\n"), chunk("", "stop")))
    client = _app(_guarded(first, path))
    assert _done(client.post(STREAM, json=QUESTION))["answered_by"] == "model"
    status = _status(path)
    assert status.breaker_code == "usage_missing" and status.open_calls == 0

    second = streaming(happy_stream(ALLOWED + "\n"))
    done = _done(_app(_guarded(second, path)).post(STREAM, json=QUESTION))
    assert done["answered_by"] == "case_data" and second.requests == []


@pytest.mark.parametrize(
    ("status", "opens"), [(401, True), (402, True), (429, False), (502, False)]
)
def test_a_provider_error_is_charged_in_full_and_may_open_the_breaker(
    tmp_path: Path, status: int, opens: bool
) -> None:
    path = new_ledger(tmp_path / "ledger.sqlite3")
    with pytest.raises(ModelCallError) as raised:
        _guarded(answering({"error": {"code": status}}, status=status), path).complete(MESSAGES)

    budget = raised.value.budget
    assert budget is not None and budget.outcome == "unsettled"
    assert budget.charged_micro_usd == budget.reserved_micro_usd
    assert _status(path).breaker_open is opens


def test_a_refusal_with_a_slow_error_body_opens_the_breaker_on_chat(tmp_path: Path) -> None:
    """Re-QG N-1: /chat (non-stream) and /chat/stream treat a refusal the same way."""

    from tests.test_openrouter_adapter import SlowError

    path = new_ledger(tmp_path / "ledger.sqlite3")
    provider = Provider(lambda _: httpx.Response(402, stream=SlowError()))
    with pytest.raises(ModelCallError) as raised:
        _guarded(provider, path, llm_timeout_seconds=0.3).complete(MESSAGES)

    assert raised.value.error_class == "payment"
    assert _status(path).breaker_code == "provider_error"


def test_a_mid_stream_error_is_settled_once(tmp_path: Path) -> None:
    path = new_ledger(tmp_path / "ledger.sqlite3")
    model = _guarded(streaming(sse(chunk("x"), chunk("", "error"))), path)

    async def run() -> None:
        async for _ in model.stream(MESSAGES):
            pass

    with pytest.raises(ModelCallError) as raised:
        anyio.run(run)
    assert raised.value.error_class == "upstream_midstream"
    status = _status(path)
    assert status.open_calls == 0 and status.local_charged == raised.value.budget.reserved_micro_usd  # type: ignore[union-attr]


# --- cancellation (T4-06) ------------------------------------------------------------------


def test_a_client_that_stops_reading_is_charged_in_full(tmp_path: Path) -> None:
    path = new_ledger(tmp_path / "ledger.sqlite3")
    model = _guarded(streaming(happy_stream()), path)

    async def first_piece_only() -> Piece:
        stream = model.stream(MESSAGES)
        piece = await anext(stream)
        await stream.aclose()
        return piece

    assert anyio.run(first_piece_only).text == "Line one\n"
    status = _status(path)
    assert status.open_calls == 0 and status.local_charged > 720 and not status.breaker_open


def test_settlement_survives_cancellation(tmp_path: Path) -> None:
    path = new_ledger(tmp_path / "ledger.sqlite3")
    model = _guarded(streaming(happy_stream()), path)

    async def cancelled() -> None:
        with anyio.CancelScope() as scope:
            async for _ in model.stream(MESSAGES):
                scope.cancel()
                await anyio.sleep(1)

    anyio.run(cancelled)
    status = _status(path)
    assert status.open_calls == 0 and status.local_charged > 0 and not status.breaker_open


def test_a_ledger_that_cannot_record_the_settlement_stops_further_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = new_ledger(tmp_path / "ledger.sqlite3")
    model = _guarded(answering(completion(ALLOWED)), path)

    def broken(*args: Any, **kwargs: Any) -> Any:
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(model._ledger, "settle", broken)
    answer = model.complete(MESSAGES)

    assert answer.budget is not None and answer.budget.outcome == "unsettled"
    status = _status(path)
    assert status.breaker_code == "ledger_write_failed" and status.open_calls == 1


# --- the default profile never touches a ledger (T4-14) -------------------------------------


def test_the_default_profile_creates_and_opens_no_ledger(monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[object] = []
    monkeypatch.setattr(BudgetLedger, "open", classmethod(lambda cls, *a, **k: opened.append(a)))
    settings = AiAssistantSettings(_env_file=None, llm_enabled=True)  # type: ignore[call-arg]
    create_app(settings, clm_transport=httpx.MockTransport(FakeBackend().handler))

    assert opened == []
    assert not ledger_path(settings).exists()
    assert not ledger_path(settings).parent.exists()


def test_usage_is_the_documented_shape() -> None:
    assert set(USAGE) >= {"prompt_tokens", "completion_tokens", "cost"}
