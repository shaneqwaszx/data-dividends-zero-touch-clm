"""Offline latency benchmark for the RM chat with the remote model (development tool only).

    ../../.venv/Scripts/python scripts/benchmark_chat_latency.py --reps 30 --out data/bench.json

Runs the real assistant app (``create_app``) under uvicorn on a loopback port, so the NDJSON
stream is flushed exactly as in the service, with:

- the fake CLM backend of the test suite serving a synthetic Garden or Multiple Owner case (with
  per-request delay) and its document digests (D-095 verified synthetic cases);
- a timed mock OpenRouter: preflight reads (public listing, key) with a network delay; a
  streamed chat completion whose hidden reasoning time, prefill time per prompt character,
  output rate, newline pauses, stalls and usage chunk are set per scenario; and generation
  metadata that is published only after a set lag.

Nothing leaves the machine and no key is used: every OpenRouter response is a mock, so these
numbers say where the application spends time around the model, never how fast GPT-OSS itself
is, nor how a reasoning setting changes its speed or answers. Provider delays are scenario
inputs, not measurements.

Each pipeline stage is timed by wrapping the existing functions at run time (the assistant's
code is not changed): case retrieval, document digests, synthetic eligibility, the remote
model's readiness (preflight or earlier-call verification), budget admission, the provider
request, the first content chunk, the first checked line the client receives, the final answer
and the background post-answer verification.

``--candidate`` switches on prototypes evaluated against the same scenarios:
``poll1s``: generation metadata read every second within the same total wait (the prototype
measured before the bounded early reads in openrouter_account.py were implemented).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import socket
import statistics
import sys
import tempfile
import threading
import time
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import httpx  # noqa: E402
import pytest  # noqa: E402
import uvicorn  # noqa: E402

from ai_assistant import main as assistant_main  # noqa: E402
from ai_assistant import openrouter_account, remote_test  # noqa: E402
from ai_assistant.budget import BudgetLedger  # noqa: E402
from ai_assistant.clm_client import ClmBackendClient  # noqa: E402
from tests import test_model_management as fake_clm  # noqa: E402
from tests.latency_fixtures import Provider, TimedOpenRouter  # noqa: E402
from tests.test_model_management import CASE_ID, ORIGIN  # noqa: E402
from tests.test_remote_test import Journey, _settle_verification  # noqa: E402
from tests.test_synthetic_eligibility import GARDEN, MULTIPLE_OWNER, digests_for  # noqa: E402

CASES = {"garden": GARDEN, "multiple_owner": MULTIPLE_OWNER}


@dataclass
class Scenario:
    name: str
    case: str = "garden"
    provider: Provider = field(default_factory=Provider)
    backend_delay: float = 0.008  # per CLM backend request (measured in-process: 3-16 ms)
    cold_preflight: bool = False  # every question runs the full preflight
    follow_up: str = "settled"  # "settled": earlier verification done; "immediate": not yet
    history_turns: int = 0  # earlier turns sent with the question (a longer prompt)
    concurrency: int = 1
    cancel_after_first_line: bool = False
    timeout_seconds: float = 90.0
    # False: the first counted question is the first one asked (a timeout or a cancellation
    # opens the ledger breaker, so what follows it shows the after-effect, also counted).
    warm_up: bool = True


# --- stage timing ---------------------------------------------------------------------------


class Stages:
    def __init__(self) -> None:
        self.durations: dict[str, list[float]] = defaultdict(list)
        self.lock = threading.Lock()

    def add(self, name: str, seconds: float) -> None:
        with self.lock:
            self.durations[name].append(seconds)

    def clear(self) -> None:
        with self.lock:
            self.durations.clear()

    def timed(self, name: str, function: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            began = time.monotonic()
            try:
                return function(*args, **kwargs)
            finally:
                self.add(name, time.monotonic() - began)

        return wrapper


def instrument(monkeypatch: pytest.MonkeyPatch, stages: Stages) -> None:
    patches = [
        (ClmBackendClient, "load_case", "case_retrieval"),
        (ClmBackendClient, "load_document_digests", "document_digests"),
        (assistant_main, "synthetic_eligibility_check", "eligibility_check"),
        (remote_test.RemoteTestModel, "_ready", "model_readiness_total"),
        (remote_test, "preflight", "preflight"),
        (remote_test, "verify_earlier_calls", "earlier_call_verification"),
        (remote_test.RemoteTestModel, "verify_now", "post_answer_verification"),
        (BudgetLedger, "reserve", "budget_admission"),
    ]
    for owner, name, stage in patches:
        monkeypatch.setattr(owner, name, stages.timed(stage, getattr(owner, name)))


def candidate_poll1s(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prototype: poll every second within the caller's same total wait."""

    original = openrouter_account.OpenRouterAccount.generation

    def generation(self: Any, ref: str, *, attempts: int = 8, wait_seconds: float = 2.0) -> Any:
        total = max(0.0, (attempts - 1) * wait_seconds)
        step = min(wait_seconds, 1.0)
        return original(self, ref, attempts=int(total / step) + 1, wait_seconds=step)

    monkeypatch.setattr(openrouter_account.OpenRouterAccount, "generation", generation)


# --- one run ---------------------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@contextlib.contextmanager
def serve_app(app: Any) -> Iterator[str]:
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(10)


def ask(base: str, question: str, history: list[dict[str, str]], cancel: bool) -> dict[str, Any]:
    """One streamed question as the chat panel sends it; client-side clock."""

    t0 = time.monotonic()
    marks: dict[str, Any] = {"t0": t0}
    client = httpx.Client(base_url=base, timeout=200, cookies={"clm_session": "rm-session"})
    with (
        client as c,
        c.stream(
            "POST",
            f"/assistant/cases/{CASE_ID}/chat/stream",
            json={"message": question, "history": history},
            headers={"Origin": ORIGIN},
        ) as response,
    ):
        marks["headers"] = time.monotonic() - t0
        for line in response.iter_lines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event["type"] == "text" and "first_line" not in marks:
                marks["first_line"] = time.monotonic() - t0
                if cancel:
                    marks["cancelled"] = True
                    break
            if event["type"] == "done":
                marks["done"] = time.monotonic() - t0
                marks["answered_by"] = event["answered_by"]
                marks["lines"] = len([x for x in event["answer"].splitlines() if x.strip()])
    marks.setdefault("first_line", marks.get("done"))
    return marks


def _pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))]


def summarise(values: list[float]) -> dict[str, float | None]:
    ms = [v * 1000 for v in values]
    return {
        "n": len(ms),
        "p50_ms": round(statistics.median(ms), 1) if ms else None,
        "p95_ms": round(_pct(ms, 0.95), 1) if ms else None,  # type: ignore[arg-type]
    }


def run_scenario(scenario: Scenario, reps: int, candidates: set[str]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp, pytest.MonkeyPatch.context() as mp:
        journey = Journey(
            Path(tmp),
            mp,
            synthetic_dev_decision="D-095",
            local_api_test_max_calls=200,
            local_api_test_preflight_seconds=0 if scenario.cold_preflight else 300,
            llm_timeout_seconds=scenario.timeout_seconds,
        )
        provider = TimedOpenRouter()
        journey.openrouter = provider  # type: ignore[assignment]
        journey.selector.transport = provider.transport()
        summary, documents = CASES[scenario.case]
        mp.setattr(fake_clm, "SUMMARY", summary)
        mp.setattr(fake_clm, "DOCUMENTS", documents)
        mp.setattr(fake_clm, "DIGESTS", digests_for(documents))
        backend = journey.backend.handler

        def slow_backend(request: httpx.Request) -> httpx.Response:
            time.sleep(scenario.backend_delay)
            return backend(request)

        journey.backend.handler = slow_backend  # type: ignore[method-assign]
        mp.setattr(remote_test, "fetch_public", _slow_listing(provider))
        journey.selector.fetch = _slow_listing(provider)
        if "poll1s" in candidates:
            candidate_poll1s(mp)
        journey.activate_remote()  # mock qualification and activation, nothing paid
        _settle_verification()
        provider.provider = scenario.provider
        stages = Stages()
        instrument(mp, stages)
        history: list[dict[str, str]] = []
        for turn in range(scenario.history_turns):
            history += [
                {"role": "user", "content": f"Earlier question {turn} about this case?"},
                {"role": "assistant", "content": "The case is waiting for review. " * 6},
            ]
        results: list[dict[str, Any]] = []
        with serve_app(journey.app) as base:
            if scenario.warm_up:
                ask(base, "What should I do next?", history, False)  # warm-up, not counted
                _settle_verification()
            stages.clear()
            provider.marks.clear()
            for _ in range(reps):
                if scenario.follow_up == "settled":
                    _settle_verification()
                if scenario.concurrency > 1:
                    with __import__("concurrent.futures").futures.ThreadPoolExecutor(
                        scenario.concurrency
                    ) as pool:
                        batch = list(
                            pool.map(
                                lambda _: ask(base, "What should I do next?", history, False),
                                range(scenario.concurrency),
                            )
                        )
                    results += batch
                else:
                    results.append(
                        ask(
                            base,
                            "What should I do next?",
                            history,
                            scenario.cancel_after_first_line,
                        )
                    )
            _settle_verification()
            ledger = BudgetLedger.open(Path(journey.settings.budget_ledger_path)).status()
        client = {
            "time_to_headers": summarise([r["headers"] for r in results]),
            "time_to_first_displayed_line": summarise(
                [r["first_line"] for r in results if r.get("first_line") is not None]
            ),
            "total": summarise([r["done"] for r in results if r.get("done") is not None]),
        }
        if scenario.concurrency == 1:
            # Sequential: the n-th provider request belongs to the n-th question (a question
            # answered from case data alone makes none, so pair only when the counts agree).
            requests, firsts = provider.marks["provider_request"], provider.marks["first_content"]
            if len(requests) == len(results):
                client["time_to_provider_request"] = summarise(
                    [r0 - r["t0"] for r0, r in zip(requests, results, strict=True)]
                )
            if len(firsts) == len(results):
                client["time_to_first_model_text"] = summarise(
                    [f - r["t0"] for f, r in zip(firsts, results, strict=True)]
                )
        stage = {name: summarise(values) for name, values in sorted(stages.durations.items())}
        answered = defaultdict(int)
        for r in results:
            answered[r.get("answered_by", "cancelled" if r.get("cancelled") else "none")] += 1
        first = results[0] if results else {}
        return {
            "first_question": {
                k: round(v * 1000, 1) if isinstance(v, float) else v
                for k, v in first.items()
                if k != "t0"
            },
            "scenario": asdict(scenario),
            "candidates": sorted(candidates),
            "client": client,
            "stages": stage,
            "answered_by": dict(answered),
            "ledger_after": {"open_calls": ledger.open_calls, "breaker_open": ledger.breaker_open},
        }


def _slow_listing(provider: TimedOpenRouter) -> Callable[[str], Any]:
    def fetch(path: str) -> Any:
        time.sleep(provider.provider.network)
        return remote_test_listing(path)

    return fetch


def remote_test_listing(path: str) -> Any:
    from tests.test_remote_test import listing

    return listing(path)


SCENARIOS = {
    "fast_warm": Scenario("fast_warm"),
    "fast_warm_multiple_owner": Scenario("fast_warm_multiple_owner", case="multiple_owner"),
    "fast_cold_preflight": Scenario("fast_cold_preflight", cold_preflight=True),
    "slow_warm": Scenario("slow_warm", provider=Provider(reasoning=3.0, tokens_per_second=50)),
    "long_prompt": Scenario(
        "long_prompt", history_turns=6, provider=Provider(prefill_per_kchar=0.02)
    ),
    "multi_line_answer": Scenario("multi_line_answer", provider=Provider(lines=6)),
    "newline_delay": Scenario("newline_delay", provider=Provider(lines=4, newline_pause=0.4)),
    "provider_timeout": Scenario(
        "provider_timeout", timeout_seconds=1.5, provider=Provider(stall=3.0), warm_up=False
    ),
    "cancelled_stream": Scenario(
        "cancelled_stream",
        cancel_after_first_line=True,
        provider=Provider(lines=4),
        warm_up=False,
    ),
    # Calibrated on the 17 real Medium turns (Phase B): about 11 s before visible content,
    # then ~60 output tokens at ~58 tokens/s. Inputs, not a measurement of the provider.
    "medium_like": Scenario(
        "medium_like", provider=Provider(network=0.15, reasoning=10.5, tokens_per_second=58)
    ),
    # A PROJECTION input only: half the hidden reasoning time at the same output rate.
    "low_projection_half_reasoning": Scenario(
        "low_projection_half_reasoning",
        provider=Provider(network=0.15, reasoning=5.25, tokens_per_second=58),
    ),
    "concurrent_3": Scenario("concurrent_3", concurrency=3),
    "followup_pending_verification": Scenario(
        "followup_pending_verification",
        follow_up="immediate",
        provider=Provider(metadata_lag=3.0),
    ),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reps", type=int, default=30)
    parser.add_argument("--scenario", action="append", choices=sorted(SCENARIOS))
    parser.add_argument("--candidate", action="append", choices=["poll1s"], default=[])
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    names = args.scenario or list(SCENARIOS)
    report = []
    for name in names:
        result = run_scenario(SCENARIOS[name], args.reps, set(args.candidate))
        report.append(result)
        c = result["client"]
        model_text = c.get("time_to_first_model_text", {})
        print(
            f"{name:32s} first model text p50/p95 "
            f"{model_text.get('p50_ms')}/{model_text.get('p95_ms')} ms"
        )
        print(
            f"{name:32s} first line p50/p95 "
            f"{c['time_to_first_displayed_line']['p50_ms']}/"
            f"{c['time_to_first_displayed_line']['p95_ms']} ms  total p50/p95 "
            f"{c['total']['p50_ms']}/{c['total']['p95_ms']} ms  {result['answered_by']}",
            flush=True,
        )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
