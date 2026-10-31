"""B2-0: the application's own time around a Claude answer (development tool only, offline).

    cd apps/assistant
    ../../.venv/Scripts/python scripts/benchmark_claude_overhead.py --answers 12

Runs the real assistant app in-process with the test suite's fake CLM backend and an instant
fake Claude (no network, no key, no spend): a Claude Fast configuration is qualified and
activated against the fake, then the RM asks streamed questions. Because the fake answers at
once, the times are what the service itself adds (case reads, eligibility, prompt building,
preflight, the ledger's durable reservation and settlement, the line guard and the stream),
never how fast Claude is. At most 17 answers: the 20-call limit per activation holds here too.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import pytest  # noqa: E402

from tests.test_claude_runtime import FAST, ClaudeJourney  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--answers", type=int, default=12, choices=range(1, 18))
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        monkeypatch = pytest.MonkeyPatch()
        try:
            journey = ClaudeJourney(Path(tmp), monkeypatch)
            journey.activate_claude(FAST.profile_id)
            journey.ask(stream=True)  # warm-up, not counted
            times: list[float] = []
            for _ in range(args.answers):
                start = time.perf_counter()
                reply = journey.ask(stream=True)
                times.append((time.perf_counter() - start) * 1000)
                if reply["answered_by"] != "model":
                    raise SystemExit(f"not answered by the model: {reply['answered_by']}")
        finally:
            monkeypatch.undo()
    ordered = sorted(times)
    result = {
        "answers": len(times),
        "median_ms": round(statistics.median(times), 1),
        "p95_ms": round(ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))], 1),
        "max_ms": round(max(times), 1),
        "note": "service overhead around an instant fake Claude; not model latency",
    }
    print(json.dumps(result, indent=1))
    if args.out:
        args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
