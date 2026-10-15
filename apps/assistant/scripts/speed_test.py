"""Measure how fast the AI Assistant's model answers, before and after the speed work.

Runs on your own machine against Ollama directly, using a saved sample case (no backend,
no login needed). It asks the same 4 questions as one conversation in two ways:

  before  the full fact sheet and glossary every time, old ordering, no pre-warming
  after   the smaller prompt, glossary only when asked, cache-friendly order, pre-warmed

and prints, per question: time to the first word (what the RM feels), total time, how many
long the prompt was and how long reading it took, and the writing speed.

    cd apps/assistant
    ../../.venv/bin/python scripts/speed_test.py              # both modes
    ../../.venv/bin/python scripts/speed_test.py --mode after

Close other heavy apps first and run it twice: the first run also loads the model.
"""

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from ai_assistant.clm_client import CaseSnapshot  # noqa: E402
from ai_assistant.context import build_case_facts  # noqa: E402
from ai_assistant.guardrails import compact_facts  # noqa: E402
from ai_assistant.prompts import SYSTEM_PROMPT, build_messages, prefix_messages  # noqa: E402

FIXTURES = HERE / "tests" / "fixtures"
QUESTIONS = [
    "Why is this case blocked?",
    "Can I use the document address instead of ACRA's?",
    "What does evidence score mean?",
    "What do I still need to do before GoldTier?",
]


def _load_facts() -> dict[str, Any]:
    def read(name: str) -> Any:
        return json.loads((FIXTURES / name).read_text())

    documents = read("garden_documents.json")
    if isinstance(documents, dict):
        documents = documents.get("documents", [])
    snapshot = CaseSnapshot(
        summary=read("garden_address_conflict_summary.json"),
        documents=documents,
        actor=read("me_client_onboarder.json"),
    )
    return build_case_facts(snapshot)


def _before_messages(
    facts: dict[str, Any], history: list[dict[str, str]], question: str
) -> list[dict[str, str]]:
    """How the prompt was built before the speed work (full fact sheet, all history)."""

    full = "CASE FACTS (current, from the onboarding app):\n" + json.dumps(
        compact_facts(facts), ensure_ascii=False, default=str
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": full},
        *history[-8:],
        {"role": "user", "content": question},
    ]


def _chat(base: str, model: str, messages: list[dict[str, str]], max_tokens: int) -> dict[str, Any]:
    """One streamed call to Ollama's own chat API, which reports token counts and timings."""

    body = json.dumps(
        {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": 0.2, "num_predict": max_tokens},
        }
    ).encode()
    request = urllib.request.Request(
        f"{base}/api/chat", data=body, headers={"Content-Type": "application/json"}
    )
    start = time.monotonic()
    first: float | None = None
    text = ""
    final: dict[str, Any] = {}
    with urllib.request.urlopen(request, timeout=600) as response:
        for raw in response:
            if not raw.strip():
                continue
            event = json.loads(raw)
            piece = (event.get("message") or {}).get("content") or ""
            if piece and first is None:
                first = time.monotonic() - start
            text += piece
            if event.get("done"):
                final = event
    total = time.monotonic() - start
    written = final.get("eval_count") or 0
    writing_seconds = (final.get("eval_duration") or 0) / 1e9
    return {
        "first_word_s": first if first is not None else total,
        "total_s": total,
        "prompt_tokens": final.get("prompt_eval_count"),
        "reading_s": (final.get("prompt_eval_duration") or 0) / 1e9,
        "answer_tokens": written,
        "tokens_per_s": written / writing_seconds if writing_seconds else 0.0,
        "answer": text.strip(),
    }


def run(mode: str, base: str, model: str) -> list[dict[str, Any]]:
    facts = _load_facts()
    history: list[dict[str, str]] = []
    rows = []
    if mode == "after":
        _chat(base, model, prefix_messages(facts), 1)  # what opening the panel now does
    for question in QUESTIONS:
        if mode == "after":
            messages, cap = build_messages(facts, history, question), 600
        else:
            messages, cap = _before_messages(facts, history, question), 2048
        result = _chat(base, model, messages, cap)
        rows.append({"question": question, **result})
        history += [
            {"role": "user", "content": question},
            {"role": "assistant", "content": result["answer"]},
        ]
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--mode", choices=["before", "after", "both"], default="both")
    parser.add_argument("--ollama", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="ministral-3:8b")
    parser.add_argument("--show-answers", action="store_true")
    args = parser.parse_args()

    modes = ["before", "after"] if args.mode == "both" else [args.mode]
    summary = {}
    for mode in modes:
        print(f"\n== {mode.upper()} ==")
        print(
            f"{'question':44} {'first word':>10} {'total':>7} "
            f"{'prompt':>7} {'reading':>8} {'tok/s':>6}"
        )
        rows = run(mode, args.ollama, args.model)
        for row in rows:
            print(
                f"{row['question'][:44]:44} {row['first_word_s']:9.1f}s {row['total_s']:6.1f}s "
                f"{row['prompt_tokens'] or 0:7} {row['reading_s']:7.1f}s {row['tokens_per_s']:6.1f}"
            )
            if args.show_answers:
                print("   ", row["answer"].replace("\n", "\n    "))
        summary[mode] = (
            sum(r["first_word_s"] for r in rows) / len(rows),
            sum(r["total_s"] for r in rows) / len(rows),
        )
    print()
    for mode, (first, total) in summary.items():
        print(f"{mode:6}: average first word {first:.1f}s, average total {total:.1f}s")
    print(
        "\nprompt = size of the prompt in tokens; reading = time the model spent reading it "
        "(short when the start was cached); tok/s = writing speed."
    )


if __name__ == "__main__":
    main()
