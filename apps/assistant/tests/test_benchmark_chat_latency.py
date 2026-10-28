"""The offline latency benchmark (scripts/benchmark_chat_latency.py) still runs end to end on
the real app with the mock OpenRouter: one short scenario, two questions, nothing spent."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_chat_latency.py"


def _bench() -> ModuleType:
    spec = importlib.util.spec_from_file_location("benchmark_chat_latency", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # its dataclasses look their module up
    spec.loader.exec_module(module)
    return module


def test_the_benchmark_measures_every_stage_of_a_verified_synthetic_question() -> None:
    bench = _bench()
    result = bench.run_scenario(bench.SCENARIOS["fast_warm"], 2, set())
    assert result["answered_by"] == {"model": 2}
    client = result["client"]
    for metric in ("time_to_headers", "time_to_first_model_text", "time_to_first_displayed_line"):
        assert client[metric]["n"] == 2
    # Ordered as the pipeline runs: reply started, model text, first checked line, answer.
    assert (
        client["time_to_headers"]["p50_ms"]
        < client["time_to_first_model_text"]["p50_ms"]
        < client["time_to_first_displayed_line"]["p50_ms"]
        <= client["total"]["p50_ms"]
    )
    for stage in ("case_retrieval", "document_digests", "eligibility_check", "budget_admission"):
        assert result["stages"][stage]["n"] >= 2
    assert result["ledger_after"] == {"open_calls": 0, "breaker_open": False}
