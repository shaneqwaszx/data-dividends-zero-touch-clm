"""Phase B live gate, account checks and provider verification (D-092, proposed).

Everything here is offline: the live gate is checked up to the point where a client would be
built, account checks and the harness run against ``httpx.MockTransport``, and the suite's
socket guard (conftest) refuses any real connection. The key is a sentinel searched for in
every output.
"""

import importlib.util
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import pytest

from ai_assistant.budget import BudgetLedger, BudgetRefusedError, LedgerError, reservation_for
from ai_assistant.llm import ModelCallError
from ai_assistant.model_factory import build_account_client, build_chat_model
from ai_assistant.model_profiles import (
    APPROVED_PROFILES,
    DEEPINFRA_BF16,
    LIVE_DECISION_ID,
    OPENROUTER_MODEL_ID,
    OPENROUTER_PROFILE_ID,
    ProfileConfigError,
)
from ai_assistant.openrouter import (
    LIVE_NETWORK,
    OpenRouterChatModel,
    require_allowed_transport,
    require_offline_transport,
)
from ai_assistant.openrouter_account import AccountCheckError, KeyStatus, OpenRouterAccount
from assistant_eval import live
from assistant_eval.runner import Workspace, run
from assistant_eval.scenarios import EVAL_FIXTURES, load_scenarios
from tests.remote_fixtures import (
    ENDPOINT,
    ENVIRON,
    SENTINEL_KEY,
    TEST_REGISTRY,
    Chunks,
    chunk,
    happy_stream,
    new_ledger,
    remote_settings,
    sse,
)

ASSISTANT_DIR = Path(__file__).resolve().parents[1]
PHASE_B_QUESTIONS = EVAL_FIXTURES / "phase_b_questions.json"


def _live_settings(**changes: Any) -> Any:
    return remote_settings(**{"remote_live_decision": LIVE_DECISION_ID, **changes})


def _code(error: pytest.ExceptionInfo[BaseException]) -> str:
    assert SENTINEL_KEY not in str(error.value)
    return str(getattr(error.value, "code", ""))


# --- the approved endpoint -------------------------------------------------------------------


def test_registry_holds_exactly_the_recorded_endpoint() -> None:
    profile = APPROVED_PROFILES[OPENROUTER_PROFILE_ID]
    assert profile.endpoints == (DEEPINFRA_BF16,)
    record = DEEPINFRA_BF16
    assert record.slug == "deepinfra/bf16" and record.provider_name == "DeepInfra"
    assert (record.prompt_price_per_m, record.completion_price_per_m) == (
        Decimal("0.037"),
        Decimal("0.17"),
    )
    assert record.request_price == 0 and record.quantization == "bf16"
    # No endpoint evidence that max_tokens bounds reasoning: reserve the listed maximum.
    assert record.max_completion_tokens == 117964 and not record.max_tokens_includes_reasoning


def test_reservation_for_the_recorded_endpoint_is_conservative() -> None:
    messages = [{"role": "system", "content": "x" * 10_000}, {"role": "user", "content": "q"}]
    reservation = reservation_for(messages, DEEPINFRA_BF16, 2000)
    assert reservation.output_bound_tokens == 117964
    # 11,065 prompt-bound tokens x 0.037/M + 117,964 x 0.17/M, rounded up to micro-USD.
    assert reservation.micro_usd == 20464


# --- L1: the live gate -----------------------------------------------------------------------


def test_marker_is_not_an_offline_transport() -> None:
    with pytest.raises(ProfileConfigError) as error:
        require_offline_transport(LIVE_NETWORK)
    assert _code(error) == "TRANSPORT_NOT_ALLOWED"
    assert require_allowed_transport(LIVE_NETWORK) is None
    with httpx.HTTPTransport() as real:  # closed at once: the suite runs near handle limits
        others = (object(), real, httpx.BaseTransport(), httpx.AsyncHTTPTransport)
        for other in others:
            with pytest.raises(ProfileConfigError):
                require_allowed_transport(other)


@pytest.mark.parametrize(
    ("changes", "kwargs", "code"),
    [
        ({}, {}, "PROFILE_DORMANT"),  # live decision named, but the caller did not ask
        ({"remote_live_decision": ""}, {"allow_live_network": True}, "LIVE_INTERLOCK"),
        ({"remote_live_decision": "D-091"}, {"allow_live_network": True}, "LIVE_INTERLOCK"),
        ({"remote_live_decision": "d-092"}, {"allow_live_network": True}, "LIVE_INTERLOCK"),
        ({}, {"allow_live_network": 1}, "PROFILE_DORMANT"),  # only the literal True opens it
        ({"remote_inference_decision": ""}, {"allow_live_network": True}, "DECISION_INTERLOCK"),
        (
            {"openrouter_endpoint": "deepinfra"},
            {"allow_live_network": True},
            "ENDPOINT_NOT_APPROVED",
        ),
    ],
)
def test_live_gate_refusals(
    tmp_path: Path, changes: dict[str, Any], kwargs: dict[str, Any], code: str
) -> None:
    settings = _live_settings(**{"openrouter_endpoint": DEEPINFRA_BF16.slug, **changes})
    with pytest.raises(ProfileConfigError) as error:
        build_chat_model(
            settings,
            environ=ENVIRON,
            budget_ledger=new_ledger(tmp_path / "ledger.sqlite3"),
            **kwargs,
        )
    assert _code(error) == code


def test_live_gate_refuses_an_injected_transport_too(tmp_path: Path) -> None:
    with pytest.raises(ProfileConfigError) as error:
        build_chat_model(
            _live_settings(openrouter_endpoint=DEEPINFRA_BF16.slug),
            transport=httpx.MockTransport(lambda _: httpx.Response(500)),
            environ=ENVIRON,
            budget_ledger=new_ledger(tmp_path / "ledger.sqlite3"),
            allow_live_network=True,
        )
    assert _code(error) == "TRANSPORT_NOT_ALLOWED"


def test_live_gate_keeps_the_ledger_and_credential_locks(tmp_path: Path) -> None:
    settings = _live_settings(openrouter_endpoint=DEEPINFRA_BF16.slug)
    with pytest.raises(ProfileConfigError) as error:
        build_chat_model(
            settings, environ=ENVIRON, budget_ledger=tmp_path / "none", allow_live_network=True
        )
    assert _code(error) == "LEDGER_UNAVAILABLE"
    with pytest.raises(ProfileConfigError) as error:
        build_chat_model(
            settings,
            environ={},
            budget_ledger=new_ledger(tmp_path / "ledger.sqlite3"),
            allow_live_network=True,
        )
    assert _code(error) == "CREDENTIAL_MISSING"


class _NoClient:
    """Stands in for httpx's client classes: records the arguments and refuses to connect."""

    calls: list[dict[str, Any]] = []

    def __init__(self, **kwargs: Any) -> None:
        _NoClient.calls.append(kwargs)
        raise httpx.ConnectError("blocked in tests")


def test_open_gate_builds_a_guarded_live_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = build_chat_model(
        _live_settings(openrouter_endpoint=DEEPINFRA_BF16.slug),
        environ=ENVIRON,
        budget_ledger=new_ledger(tmp_path / "ledger.sqlite3"),
        allow_live_network=True,
    )
    assert type(model).__name__ == "BudgetedChatModel"
    inner = model._inner  # type: ignore[attr-defined]
    assert isinstance(inner, OpenRouterChatModel) and inner.live
    assert SENTINEL_KEY not in repr(model)
    payload = inner.payload([{"role": "user", "content": "q"}], stream=True)
    provider = payload["provider"]
    assert provider["only"] == provider["order"] == ["deepinfra/bf16"]
    assert provider["allow_fallbacks"] is False and provider["data_collection"] == "deny"
    assert provider["zdr"] is True and provider["require_parameters"] is True
    assert provider["quantizations"] == ["bf16"]
    assert payload["reasoning"] == {"effort": "low", "exclude": True}
    # The client is httpx's own (no transport injected), without proxies or redirects.
    _NoClient.calls.clear()
    monkeypatch.setattr("ai_assistant.openrouter.httpx.Client", _NoClient)
    with pytest.raises(Exception) as error:
        model.complete([{"role": "user", "content": "q"}])
    assert SENTINEL_KEY not in str(error.value)
    assert _NoClient.calls == [
        {"timeout": 90.0, "transport": None, "trust_env": False, "follow_redirects": False}
    ]
    # The failed attempt was charged at its reservation; nothing was left open.
    status = BudgetLedger.open(tmp_path / "ledger.sqlite3").status()
    assert status.open_calls == 0 and status.local_charged > 0


def test_the_service_never_opens_the_live_gate() -> None:
    """The running service builds its model without ``allow_live_network``; only the harness
    passes it, for its synthetic fixture cases, and (D-094) the local synthetic test mode's
    gated model, which is used only inside the synthetic boundary (tests/test_remote_test.py)."""

    users = [
        path.relative_to(ASSISTANT_DIR).as_posix()
        for folder in ("ai_assistant", "assistant_eval", "scripts")
        for path in (ASSISTANT_DIR / folder).rglob("*.py")
        if "allow_live_network=True" in path.read_text(encoding="utf-8")
    ]
    assert sorted(users) == ["ai_assistant/remote_test.py", "scripts/evaluate_answers.py"]
    main = (ASSISTANT_DIR / "ai_assistant" / "main.py").read_text(encoding="utf-8")
    assert "allow_live_network" not in main and "LIVE_NETWORK" not in main


# --- account checks --------------------------------------------------------------------------


class _Account:
    """A mock OpenRouter account API."""

    def __init__(self, responses: list[httpx.Response]) -> None:
        self.responses = responses
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.responses.pop(0)

    def client(self) -> OpenRouterAccount:
        return build_account_client(
            remote_settings(), transport=httpx.MockTransport(self.handler), environ=ENVIRON
        )


KEY_BODY = {
    "data": {
        "label": "sk-or-v1-abc...xyz",
        "limit": 1.5,
        "limit_reset": None,
        "limit_remaining": 1.25,
        "usage": 0.25,
        "budgets": [],
    }
}


def test_key_status_keeps_only_limit_and_usage() -> None:
    account = _Account([httpx.Response(200, json=KEY_BODY)])
    status = account.client().key_status()
    assert status == KeyStatus(Decimal("1.5"), None, Decimal("1.25"), Decimal("0.25"))
    assert "label" not in repr(status) and "sk-or" not in repr(status)
    request = account.requests[0]
    assert request.method == "GET" and str(request.url) == "https://openrouter.ai/api/v1/key"
    assert request.headers["authorization"] == "Bearer " + SENTINEL_KEY
    assert request.content == b""


@pytest.mark.parametrize(
    ("response", "code"),
    [
        (httpx.Response(401, json={"error": {"message": "bad key " + SENTINEL_KEY}}), "http_401"),
        (httpx.Response(200, content=b"not json"), "malformed"),
        (httpx.Response(200, json={"data": {"usage": "1"}}), "malformed"),
        (httpx.Response(200, json={"data": {"usage": -1}}), "malformed"),
        (httpx.Response(200, content=b"x" * (70 * 1024)), "too_large"),
    ],
)
def test_key_status_failures_are_closed_codes(response: httpx.Response, code: str) -> None:
    with pytest.raises(AccountCheckError) as error:
        _Account([response]).client().key_status()
    assert error.value.code == code and SENTINEL_KEY not in str(error.value)


def _generation(**changes: Any) -> dict[str, Any]:
    data = {
        "id": "gen-1761-test",
        "model": OPENROUTER_MODEL_ID,
        "provider_name": "Fictional Provider",
        "total_cost": 0.00072,
        "tokens_prompt": 3000,
        "tokens_completion": 450,
        "native_tokens_reasoning": 300,
        "cancelled": False,
        "finish_reason": "stop",
        "workspace_id": "ignored",
    }
    data.update(changes)
    return {"data": data}


def test_generation_waits_while_unpublished_then_reads_metadata_only() -> None:
    sleeps: list[float] = []
    account = _Account([httpx.Response(404, json={}), httpx.Response(200, json=_generation())])
    client = build_account_client(
        remote_settings(), transport=httpx.MockTransport(account.handler), environ=ENVIRON
    )
    client._sleep = sleeps.append
    facts = client.generation("gen-1761-test")
    assert facts.provider_name == "Fictional Provider" and facts.total_cost_usd == Decimal(
        "0.00072"
    )
    # Read again after one second (the early reads), not after the caller's 2 s interval.
    assert sleeps == [1.0] and len(account.requests) == 2
    assert all(
        str(r.url) == "https://openrouter.ai/api/v1/generation?id=gen-1761-test"
        for r in account.requests
    )


def _unpublished(attempts: int, wait: float) -> tuple[list[float], int]:
    sleeps: list[float] = []
    account = _Account([httpx.Response(404, json={}) for _ in range(400)])
    client = build_account_client(
        remote_settings(), transport=httpx.MockTransport(account.handler), environ=ENVIRON
    )
    client._sleep = sleeps.append
    with pytest.raises(AccountCheckError) as error:
        client.generation("gen-1761-test", attempts=attempts, wait_seconds=wait)
    assert error.value.code == "not_published"
    return sleeps, len(account.requests)


def test_generation_never_waits_longer_than_the_callers_bound() -> None:
    # The verification's own bound: 25 reads 5 s apart (120 s in total).
    sleeps, reads = _unpublished(25, 5.0)
    assert sum(sleeps) == pytest.approx(120.0)
    assert sleeps[:10] == [1.0] * 10 and set(sleeps[10:]) == {5.0}
    assert reads == len(sleeps) + 1 == 33  # 8 more free metadata reads than before
    # A short bound is still the bound; a short interval is never stretched.
    assert sum(_unpublished(3, 2.0)[0]) == pytest.approx(4.0)
    assert set(_unpublished(5, 0.5)[0]) == {0.5}
    assert _unpublished(1, 5.0) == ([], 1)


def test_generation_refuses_a_bad_reference_without_a_request() -> None:
    account = _Account([])
    with pytest.raises(AccountCheckError) as error:
        account.client().generation("../key")
    assert error.value.code == "bad_reference" and account.requests == []


def test_account_client_has_the_same_gates() -> None:
    mock = httpx.MockTransport(lambda _: httpx.Response(500))
    with pytest.raises(ProfileConfigError) as error:
        build_account_client(remote_settings(llm_profile="local_openai_compatible"), transport=mock)
    assert _code(error) == "PROFILE_UNKNOWN"
    with pytest.raises(ProfileConfigError) as error:
        build_account_client(remote_settings(), environ=ENVIRON)
    assert _code(error) == "PROFILE_DORMANT"
    with pytest.raises(ProfileConfigError) as error:
        build_account_client(remote_settings(), environ=ENVIRON, allow_live_network=True)
    assert _code(error) == "LIVE_INTERLOCK"
    with pytest.raises(ProfileConfigError) as error:
        build_account_client(
            remote_settings(remote_inference_decision=""), transport=mock, environ=ENVIRON
        )
    assert _code(error) == "DECISION_INTERLOCK"
    with pytest.raises(ProfileConfigError) as error:
        build_account_client(remote_settings(), transport=mock, environ={})
    assert _code(error) == "CREDENTIAL_MISSING"


# --- preflight checks ------------------------------------------------------------------------


def _listing(**changes: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    row = {
        "tag": "deepinfra/bf16",
        "model_id": OPENROUTER_MODEL_ID,
        "provider_name": "DeepInfra",
        "quantization": "bf16",
        "max_completion_tokens": 117964,
        "pricing": {"prompt": "0.000000037", "completion": "0.00000017", "discount": 0},
        "supported_parameters": ["reasoning", "max_tokens", "temperature"],
    }
    row.update(changes)
    others = [{"tag": "groq"}, {"tag": "deepinfra-other"}]
    zdr = {"data": [{"tag": "deepinfra/bf16", "model_id": OPENROUTER_MODEL_ID}]}
    return {"data": {"endpoints": [row, *others]}}, zdr


def test_endpoint_check_passes_on_the_recorded_listing() -> None:
    report = live.Preflight()
    live.check_endpoint(report, DEEPINFRA_BF16, *_listing())
    assert report.passed, report.lines()


@pytest.mark.parametrize(
    "changes",
    [
        {"pricing": {"prompt": "0.00000004", "completion": "0.00000017"}},
        {"pricing": {"prompt": "0.000000037", "completion": "0.00000017", "request": "0.001"}},
        {
            "pricing": {
                "prompt": "0.000000037",
                "completion": "0.00000017",
                "internal_reasoning": "0.000001",
            }
        },
        {"max_completion_tokens": 131072},
        {"provider_name": "Other"},
        {"supported_parameters": ["max_tokens"]},
    ],
)
def test_endpoint_check_fails_on_any_change(changes: dict[str, Any]) -> None:
    report = live.Preflight()
    live.check_endpoint(report, DEEPINFRA_BF16, *_listing(**changes))
    assert not report.passed


def test_endpoint_check_fails_when_not_unique_or_not_zdr() -> None:
    listing, zdr = _listing()
    listing["data"]["endpoints"].append({"tag": "deepinfra/bf16/eu"})
    report = live.Preflight()
    live.check_endpoint(report, DEEPINFRA_BF16, listing, zdr)
    assert not report.passed
    listing, _ = _listing()
    report = live.Preflight()
    live.check_endpoint(report, DEEPINFRA_BF16, listing, {"data": []})
    assert not report.passed


def _ledger_status(tmp_path: Path, cap: int, opening: int) -> Any:
    return BudgetLedger.open(new_ledger(tmp_path / "l.sqlite3", cap=cap, opening=opening)).status()


def test_key_and_ledger_check_passes_for_a_one_dollar_allocation(tmp_path: Path) -> None:
    status = _ledger_status(tmp_path, cap=1_250_000, opening=250_000)
    # Key limit = usage + US$1.00 (reset never): the backstop matches the allocation.
    key = KeyStatus(Decimal("1.25"), None, Decimal("1.00"), Decimal("0.25"))
    report = live.Preflight()
    live.check_key_and_ledger(report, key, status, has_calls=False, reservation_micro=30_000)
    assert report.passed, report.lines()


@pytest.mark.parametrize(
    ("key", "cap", "opening"),
    [
        (KeyStatus(None, None, None, Decimal("0.25")), 1_250_000, 250_000),  # no key limit
        (
            KeyStatus(Decimal("1.5"), "monthly", Decimal("1.25"), Decimal("0.25")),
            1_250_000,
            250_000,
        ),
        (KeyStatus(Decimal("1.5"), None, Decimal("0.01"), Decimal("0.25")), 1_250_000, 250_000),
        (KeyStatus(Decimal("5"), None, Decimal("4.75"), Decimal("0.25")), 1_250_001, 250_000),
        (KeyStatus(Decimal("1.5"), None, Decimal("1.2"), Decimal("0.30")), 1_250_000, 250_000),
    ],
)
def test_key_and_ledger_check_fails_closed(
    tmp_path: Path, key: KeyStatus, cap: int, opening: int
) -> None:
    status = _ledger_status(tmp_path, cap=cap, opening=opening)
    report = live.Preflight()
    live.check_key_and_ledger(report, key, status, has_calls=False, reservation_micro=30_000)
    assert not report.passed


def test_owner_attestations_are_required() -> None:
    for flags in ((False, True), (True, False), (False, False)):
        report = live.Preflight()
        live.check_owner(report, *flags)
        assert not report.passed
    report = live.Preflight()
    live.check_owner(report, True, True)
    assert report.passed


# --- verification and the harness ------------------------------------------------------------


def _completed_call(tmp_path: Path, usage_cost: float = 0.00072) -> tuple[BudgetLedger, Any]:
    path = new_ledger(tmp_path / "ledger.sqlite3")
    usage = {  # within the bounds of the one-word prompt below
        "prompt_tokens": 500,
        "completion_tokens": 450,
        "cost": usage_cost,
        "completion_tokens_details": {"reasoning_tokens": 300},
    }
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, stream=Chunks(happy_stream(usage=usage)))
    )
    model = build_chat_model(
        remote_settings(),
        transport=transport,
        environ=ENVIRON,
        registry=TEST_REGISTRY,
        budget_ledger=path,
    )
    ledger = BudgetLedger.open(path)
    return ledger, model


def _settle_one(ledger: BudgetLedger, model: Any) -> Any:
    import anyio

    async def go() -> None:
        async for _ in model.stream([{"role": "user", "content": "q"}]):
            pass

    anyio.run(go)
    return ledger.closed_calls_after(0)[-1]


def _metadata_account(**changes: Any) -> OpenRouterAccount:
    account = _Account([httpx.Response(200, json=_generation(**changes))])
    return account.client()


def test_verified_call(tmp_path: Path) -> None:
    ledger, model = _completed_call(tmp_path)
    call = _settle_one(ledger, model)
    row = live.verify_call(call, ENDPOINT, _metadata_account(), ledger, "P00#0@0")
    assert row.verification == "verified" and row.provider_name == "Fictional Provider"
    assert ledger.closed_calls_after(0)[-1].verification == "verified"
    assert not ledger.status().breaker_open
    with pytest.raises(LedgerError):
        ledger.record_verification(call.call_id, verified=True, breaker_code="routing_anomaly")


@pytest.mark.parametrize(
    ("changes", "breaker"),
    [
        ({"provider_name": "Other Provider"}, "routing_anomaly"),
        ({"provider_name": None}, "routing_anomaly"),
        ({"model": "openai/gpt-oss-20b"}, "routing_anomaly"),
        ({"total_cost": 0.0009}, "reconcile_drift"),
    ],
)
def test_mismatch_quarantines_and_stops_the_batch(
    tmp_path: Path, changes: dict[str, Any], breaker: str
) -> None:
    ledger, model = _completed_call(tmp_path)
    call = _settle_one(ledger, model)
    row = live.verify_call(call, ENDPOINT, _metadata_account(**changes), ledger, "P00#0@0")
    assert row.verification == "quarantined"
    status = ledger.status()
    assert status.breaker_open and status.breaker_code == breaker
    with pytest.raises(BudgetRefusedError):  # the breaker refuses the next call, no request
        _settle_one(ledger, model)


def test_unpublished_metadata_quarantines_after_the_bounded_wait(tmp_path: Path) -> None:
    ledger, model = _completed_call(tmp_path)
    call = _settle_one(ledger, model)
    mock = _Account([httpx.Response(404, json={}) for _ in range(60)])
    account = mock.client()
    sleeps: list[float] = []
    account._sleep = sleeps.append
    row = live.verify_call(call, ENDPOINT, account, ledger, "P00#0@0")
    assert row.verification == "quarantined" and row.verification_note == "metadata not_published"
    assert ledger.status().breaker_open
    # Bounded: the same two minutes in total (25 reads 5 s apart), read every second for the
    # first 10 s, then every 5 s; then fail closed.
    assert sleeps == [1.0] * 10 + [5.0] * 22 and sum(sleeps) == 120.0
    assert len(mock.requests) == 33


def test_metadata_published_late_within_the_wait_verifies(tmp_path: Path) -> None:
    """The smoke call saw no metadata within ~14 s; a later publication still verifies."""

    ledger, model = _completed_call(tmp_path)
    call = _settle_one(ledger, model)
    mock = _Account([httpx.Response(404, json={})] * 10 + [httpx.Response(200, json=_generation())])
    account = mock.client()
    account._sleep = lambda _: None
    row = live.verify_call(call, ENDPOINT, account, ledger, "P00#0@0")
    assert row.verification == "verified" and not ledger.status().breaker_open
    assert len(mock.requests) == 11


def _quarantined_by_missing_metadata(tmp_path: Path) -> BudgetLedger:
    ledger, model = _completed_call(tmp_path)
    call = _settle_one(ledger, model)
    account = _Account([httpx.Response(404, json={}) for _ in range(60)]).client()
    account._sleep = lambda _: None
    live.verify_call(call, ENDPOINT, account, ledger, "P00#0@0")
    status = ledger.status()
    assert status.breaker_open and status.breaker_code == "routing_anomaly"
    return ledger


def _key(usage: str) -> KeyStatus:
    return KeyStatus(Decimal("1.00"), None, Decimal("1.00") - Decimal(usage), Decimal(usage))


def test_recheck_passes_when_late_metadata_matches_and_changes_nothing(tmp_path: Path) -> None:
    ledger = _quarantined_by_missing_metadata(tmp_path)
    before = ledger.status()
    report = live.Preflight()
    rows = live.recheck_quarantined(report, ledger, _metadata_account(), ENDPOINT, _key("0.00072"))
    assert report.passed, report.lines()
    assert [r.verification_note for r in rows] == ["metadata matches"]
    # Read-only: the call stays quarantined and the breaker stays open.
    assert [c.verification for c in ledger.closed_calls_after(0)] == ["quarantined"]
    assert ledger.status() == before


@pytest.mark.parametrize(
    ("changes", "usage", "failing"),
    [
        ({"provider_name": "Other Provider"}, "0.00072", "recheck.call_1"),
        ({"model": "openai/gpt-oss-20b"}, "0.00072", "recheck.call_1"),
        ({"total_cost": 0.0009}, "0.00072", "recheck.call_1"),
        ({}, "0.5", "recheck.usage_accounted"),
    ],
)
def test_recheck_fails_on_any_mismatch(
    tmp_path: Path, changes: dict[str, Any], usage: str, failing: str
) -> None:
    ledger = _quarantined_by_missing_metadata(tmp_path)
    report = live.Preflight()
    live.recheck_quarantined(report, ledger, _metadata_account(**changes), ENDPOINT, _key(usage))
    assert [c.name for c in report.checks if not c.ok] == [failing]
    assert ledger.status().breaker_open


def test_recheck_fails_when_metadata_is_still_unpublished(tmp_path: Path) -> None:
    ledger = _quarantined_by_missing_metadata(tmp_path)
    account = _Account([httpx.Response(404, json={}) for _ in range(60)]).client()
    account._sleep = lambda _: None
    report = live.Preflight()
    rows = live.recheck_quarantined(report, ledger, account, ENDPOINT, _key("0.00072"))
    assert not report.passed and rows[0].verification_note == "metadata not_published"


def test_recheck_needs_a_routing_anomaly_breaker_and_a_quarantined_call(tmp_path: Path) -> None:
    ledger, model = _completed_call(tmp_path)
    _settle_one(ledger, model)
    live.verify_call(
        ledger.closed_calls_after(0)[-1], ENDPOINT, _metadata_account(), ledger, "P00#0@0"
    )
    report = live.Preflight()  # verified call, breaker closed: nothing to recheck
    live.recheck_quarantined(report, ledger, _metadata_account(), ENDPOINT, _key("0.00072"))
    assert {c.name for c in report.checks if not c.ok} == {
        "recheck.breaker_routing_anomaly",
        "recheck.quarantined_calls",
    }
    (tmp_path / "cost").mkdir()
    drift_ledger, drift_model = _completed_call(tmp_path / "cost")
    call = _settle_one(drift_ledger, drift_model)
    live.verify_call(call, ENDPOINT, _metadata_account(total_cost=0.0009), drift_ledger, "x")
    report = live.Preflight()  # breaker opened for reconcile_drift: not a recheck case
    live.recheck_quarantined(report, drift_ledger, _metadata_account(), ENDPOINT, _key("0.00072"))
    assert "recheck.breaker_routing_anomaly" in {c.name for c in report.checks if not c.ok}


def test_recheck_cli_refuses_without_the_gate_and_writes_no_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = _cli()
    monkeypatch.delenv("AI_ASSISTANT_REMOTE_LIVE_DECISION", raising=False)
    monkeypatch.setattr("sys.argv", ["evaluate_answers.py", "recheck", "--out", str(tmp_path)])
    assert cli.main() == 1
    out = capsys.readouterr().out
    assert "RECHECK FAIL" in out and "refused" in out
    (record,) = tmp_path.glob("phase_b/*-recheck/recheck.json")
    data = json.loads(record.read_text(encoding="utf-8"))
    assert data["calls"] == [] and not any(c["ok"] for c in data["checks"])


def test_harness_run_separates_answers_from_telemetry(tmp_path: Path) -> None:
    """The live path end to end with mock transports: verification per turn, the answer text
    only in answers.jsonl, and calls.json content-free."""

    path = new_ledger(tmp_path / "ledger.sqlite3")
    reply = "This answer text must stay out of calls.json\n"
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, stream=Chunks(happy_stream(text=reply)))
    )
    model = build_chat_model(
        remote_settings(),
        transport=transport,
        environ=ENVIRON,
        registry=TEST_REGISTRY,
        budget_ledger=path,
    )
    ledger = BudgetLedger.open(path)
    account = _Account([httpx.Response(200, json=_generation()) for _ in range(4)]).client()
    monitor = live.LiveMonitor(model, ledger, account, ENDPOINT)
    scenarios = load_scenarios(PHASE_B_QUESTIONS)
    before = ledger.status()
    with Workspace() as workspace:
        result = run(scenarios, lambda capture: monitor, workspace=workspace, only={"P02"})
    monitor.finish()
    assert [turn.key for turn in result.turns] == ["P02#0", "P02#1"]
    assert [row.verification for row in monitor.rows] == ["verified", "verified"]
    assert [row.turn for row in monitor.rows] == ["P02#0@0", "P02#1@0"]
    answers, calls = live.write_artifacts(
        tmp_path / "out",
        run=result,
        questions={"P02#0": "Who are the ultimate beneficial owners of this company?"},
        monitor=monitor,
        preflight=live.Preflight(),
        settings={"endpoint": ENDPOINT.slug},
        ledger_before=before,
        ledger_after=ledger.status(),
        extra={},
    )
    calls_text = calls.read_text(encoding="utf-8")
    assert "must stay out" not in calls_text and "beneficial owners" not in calls_text
    assert SENTINEL_KEY not in calls_text and SENTINEL_KEY not in answers.read_text(
        encoding="utf-8"
    )
    assert json.loads(calls_text)["spent_usd"] == "0.001440"
    rows = [json.loads(line) for line in answers.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["question"].startswith("Who are the ultimate") and len(rows) == 2


def test_phase_b_questions_are_synthetic_fixture_cases() -> None:
    scenarios = load_scenarios(PHASE_B_QUESTIONS)
    assert [s.id for s in scenarios.scenarios] == [f"P0{i}" for i in range(8)]
    assert len(scenarios.turn_keys()) == 17
    # Only the saved synthetic Garden fixtures (served by the harness's mock CLM backend).
    assert {s.base for s in scenarios.scenarios} <= {
        "garden_address_conflict",
        "garden_waiting_for_documents",
    }


# --- R1 remediation (QG M1, M2, L1, L3, L4, L5) ----------------------------------------------


def test_a_key_limit_looser_than_the_allocation_fails() -> None:
    """L1: the provider-side backstop may leave at most the allocation plus one call."""

    key = KeyStatus(Decimal("50"), None, Decimal("49.75"), Decimal("0.25"))
    report = live.Preflight()
    live.check_key(report, key, reservation_micro=30_000)
    failed = [check.name for check in report.checks if not check.ok]
    assert failed == ["key.limit_within_allocation"]


@pytest.mark.parametrize(
    "listing",
    [{"data": []}, {"data": {"endpoints": "x"}}, {"data": {"endpoints": [1, None]}}, []],
)
def test_odd_listing_shapes_fail_without_raising(listing: Any) -> None:
    """L5: any unexpected listing shape is a FAIL row, never an exception."""

    report = live.Preflight()
    live.check_endpoint(report, DEEPINFRA_BF16, listing, {"data": "x"})
    assert not report.passed


def test_a_call_without_a_generation_reference_is_quarantined(tmp_path: Path) -> None:
    """M2: missing verification evidence stops the batch, whatever the call's state."""

    path = new_ledger(tmp_path / "ledger.sqlite3")
    transport = httpx.MockTransport(lambda _: httpx.Response(429, json={}))
    model = build_chat_model(
        remote_settings(),
        transport=transport,
        environ=ENVIRON,
        registry=TEST_REGISTRY,
        budget_ledger=path,
    )
    with pytest.raises(ModelCallError):
        model.complete([{"role": "user", "content": "q"}])
    ledger = BudgetLedger.open(path)
    (call,) = ledger.closed_calls_after(0)
    assert call.state == "unsettled" and call.generation_ref is None
    row = live.verify_call(call, ENDPOINT, _Account([]).client(), ledger, "P00#0@0")
    assert row.verification == "quarantined" and ledger.status().breaker_open


def test_a_stream_that_fails_after_its_generation_id_keeps_the_reference(
    tmp_path: Path,
) -> None:
    """M2: a stream cut after its first frame is charged at its reservation, and its
    reference is kept so its serving provider can still be verified."""

    path = new_ledger(tmp_path / "ledger.sqlite3")
    body = [*sse(chunk("Partial"), done=False), b"data: not json\n\n"]
    transport = httpx.MockTransport(lambda _: httpx.Response(200, stream=Chunks(body)))
    model = build_chat_model(
        remote_settings(),
        transport=transport,
        environ=ENVIRON,
        registry=TEST_REGISTRY,
        budget_ledger=path,
    )
    ledger = BudgetLedger.open(path)
    with pytest.raises(ModelCallError) as error:
        _settle_one(ledger, model)
    usage = error.value.usage
    assert usage is not None and usage.generation_ref == "gen-1761-test"
    (call,) = ledger.closed_calls_after(0)
    assert call.state == "unsettled" and call.generation_ref == "gen-1761-test"
    assert call.charged_micro_usd == call.reserved_micro_usd
    row = live.verify_call(call, ENDPOINT, _metadata_account(), ledger, "P00#0@0")
    assert row.verification == "verified" and not ledger.status().breaker_open


def test_earlier_unverified_calls_are_verified_before_a_new_run(tmp_path: Path) -> None:
    """M1: a call an interrupted run never verified is checked by the next preflight."""

    ledger, model = _completed_call(tmp_path)
    _settle_one(ledger, model)  # settled; the run "stops" before verification
    assert [c.verification for c in ledger.unverified_closed_calls()] == ["unverified"]
    report = live.Preflight()
    rows = live.verify_earlier_calls(report, ledger, _metadata_account(), ENDPOINT)
    assert report.passed and [r.verification for r in rows] == ["verified"]
    assert ledger.unverified_closed_calls() == []


def test_an_earlier_mismatching_call_fails_the_next_preflight(tmp_path: Path) -> None:
    ledger, model = _completed_call(tmp_path)
    _settle_one(ledger, model)
    report = live.Preflight()
    account = _metadata_account(provider_name="Other Provider")
    live.verify_earlier_calls(report, ledger, account, ENDPOINT)
    assert not report.passed and ledger.status().breaker_open


def _cli() -> Any:
    spec = importlib.util.spec_from_file_location(
        "evaluate_answers_cli", ASSISTANT_DIR / "scripts" / "evaluate_answers.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("scenarios", "only"),
    [(str(EVAL_FIXTURES / "scenarios.json"), "S01"), (str(PHASE_B_QUESTIONS), "")],
)
def test_live_runs_need_the_phase_b_questions_and_a_selection(
    scenarios: str, only: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """L3: refused before the preflight, so before any key read or request."""

    cli = _cli()
    monkeypatch.setattr(cli, "_preflight", lambda args: pytest.fail("preflight reached"))
    argv = ["evaluate_answers.py", "run", "--model", "openrouter", "--scenarios", scenarios]
    monkeypatch.setattr("sys.argv", argv + (["--only", only] if only else []))
    assert cli.main() == 2
    assert "refused" in capsys.readouterr().out


def _manifest_args(**changes: Any) -> Any:
    import argparse

    values: dict[str, Any] = {
        "scenarios": str(PHASE_B_QUESTIONS),
        "only": "",
        "questions": "P01#1,P02#0",
        "expect_count": 2,
    }
    values.update(changes)
    return argparse.Namespace(**values)


def test_a_paid_run_takes_an_explicit_counted_question_manifest() -> None:
    cli = _cli()
    scenarios = load_scenarios(PHASE_B_QUESTIONS)
    assert cli.question_manifest(_manifest_args(), scenarios) == ["P01#1", "P02#0"]
    assert cli.question_manifest(
        _manifest_args(questions=" P07#1 ", expect_count=1), scenarios
    ) == ["P07#1"]


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"scenarios": str(EVAL_FIXTURES / "scenarios.json")}, "needs --scenarios"),
        ({"only": "P01,P02,P07"}, "not --only"),  # the 8-versus-7 selection mistake
        ({"questions": ""}, "needs --questions"),
        ({"expect_count": None}, "needs --questions"),
        ({"questions": "P01#1,P01#1", "expect_count": 2}, "more than once"),
        ({"questions": "P01#1,P09#0", "expect_count": 2}, "unknown question ids: P09#0"),
        ({"questions": "P01", "expect_count": 1}, "unknown question ids: P01"),
        ({"expect_count": 3}, "lists 2 questions but --expect-count is 3"),
        ({"expect_count": 1}, "lists 2 questions but --expect-count is 1"),
    ],
)
def test_a_paid_run_refuses_any_manifest_doubt(changes: dict[str, Any], reason: str) -> None:
    result = _cli().question_manifest(_manifest_args(**changes), load_scenarios(PHASE_B_QUESTIONS))
    assert isinstance(result, str) and reason in result


def test_a_manifest_mismatch_is_refused_before_the_preflight(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = _cli()
    monkeypatch.setattr(cli, "_preflight", lambda args: pytest.fail("preflight reached"))
    argv = [
        "evaluate_answers.py",
        "run",
        "--model",
        "openrouter",
        "--scenarios",
        str(PHASE_B_QUESTIONS),
        "--questions",
        "P01#0,P01#1,P01#2,P01#3,P02#0,P02#1,P07#0,P07#1",
        "--expect-count",
        "7",
    ]
    monkeypatch.setattr("sys.argv", argv)
    assert cli.main() == 2
    assert "lists 8 questions but --expect-count is 7" in capsys.readouterr().out


def test_the_runner_asks_exactly_the_selected_turns() -> None:
    from assistant_eval.models import SELF_TESTS, Capture, SelectorModel

    scenarios = load_scenarios(PHASE_B_QUESTIONS)
    selector = next(iter(SELF_TESTS.values()))

    def make(capture: Capture) -> Any:
        return SelectorModel(selector(), capture)

    with Workspace() as workspace:
        result = run(scenarios, make, workspace=workspace, turns=frozenset({"P01#1", "P02#0"}))
    assert [turn.key for turn in result.turns] == ["P01#1", "P02#0"]
    with pytest.raises(ValueError, match="unknown turn keys: P09#0"):
        run(scenarios, make, turns=frozenset({"P09#0"}))
    with pytest.raises(ValueError, match="unknown turn keys"):
        run(scenarios, make, turns=frozenset())


def test_a_conversation_cannot_be_split_by_turn() -> None:
    from assistant_eval.scenarios import SCENARIOS_FILE

    scenarios = load_scenarios(SCENARIOS_FILE)
    conversation = next(s for s in scenarios.scenarios if s.conversation)
    with pytest.raises(ValueError, match="is a conversation"):
        run(
            scenarios,
            lambda capture: pytest.fail("built"),
            turns=frozenset({conversation.turn_key(0)}),
        )


def test_live_network_marker_is_used_only_by_the_adapter_and_the_factory() -> None:
    """L4: the marker that opens the real transport appears in exactly two modules."""

    users = sorted(
        path.relative_to(ASSISTANT_DIR).as_posix()
        for folder in ("ai_assistant", "assistant_eval", "scripts")
        for path in (ASSISTANT_DIR / folder).rglob("*.py")
        if "LIVE_NETWORK" in path.read_text(encoding="utf-8")
    )
    assert users == ["ai_assistant/model_factory.py", "ai_assistant/openrouter.py"]
