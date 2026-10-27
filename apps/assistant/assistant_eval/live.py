"""Phase B live evaluation (D-092, proposed): synthetic cases only, budget-limited, verified.

The live model is the service's own remote profile, built by ``build_chat_model`` with the
live gate open, so the request policy, the exact-line guard and the budget ledger are the
reviewed ones. The harness serves only synthetic fixture cases through its mock CLM backend,
which is why only the harness may open the gate.

Before the first call, ``preflight`` must pass every check (it fails closed):

    endpoint   the public listing still shows the approved endpoint with the recorded prices,
               maximum completion, quantization and provider, its slug matches no other
               endpoint of the model, and it is in the public ZDR list
    key        the key has a spending limit that never resets and room for one reservation
    ledger     initialised for this key, breaker closed, no open calls, its cap allows at most
               the allocation (US$1.00 here) beyond the key's usage when the ledger was made,
               and the key's provider-reported usage is fully accounted for
    owner      the owner attests auto top-up is off and prompt logging is off (neither is
               readable through the API)

After every turn the monitor fetches generation metadata for each new call (waiting, bounded,
while it is not yet published): serving provider, model and total cost must match, or the
call is quarantined and the ledger breaker opens, which refuses every later call (the batch
stops). ``recheck_quarantined`` takes a later, read-only look at quarantined calls. Answer
text goes to ``answers.jsonl``; everything else is content-free and goes to ``calls.json``.
"""

import json
from collections.abc import AsyncGenerator, Callable
from contextlib import aclosing
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ai_assistant.budget import RECONCILE_TOLERANCE_MICRO_USD, BudgetLedger, LedgerStatus
from ai_assistant.llm import ModelAnswer, Piece, micro_usd
from ai_assistant.model_profiles import ApprovedEndpoint
from ai_assistant.openrouter_account import AccountCheckError, KeyStatus, OpenRouterAccount

# The checks moved to the runtime package (D-094) and are re-exported here unchanged.
from ai_assistant.remote_checks import (
    ALLOCATION_LIMIT_USD,
    METADATA_ATTEMPTS,
    METADATA_WAIT_SECONDS,
    CallRow,
    Check,
    Preflight,
    _compare,
    _metadata,
    _row,
    _usd,
    check_endpoint,
    check_key,
    check_key_and_ledger,
    check_ledger,
    check_owner,
    fetch_public,
    typical_reservation,
    verify_call,
    verify_earlier_calls,
)

__all__ = [
    "ALLOCATION_LIMIT_USD",
    "METADATA_ATTEMPTS",
    "METADATA_WAIT_SECONDS",
    "CallRow",
    "Check",
    "Preflight",
    "_compare",
    "_metadata",
    "_row",
    "_usd",
    "check_endpoint",
    "check_key",
    "check_key_and_ledger",
    "check_ledger",
    "check_owner",
    "fetch_public",
    "typical_reservation",
    "verify_call",
    "verify_earlier_calls",
    "LiveMonitor",
    "recheck_quarantined",
    "write_artifacts",
]


def recheck_quarantined(
    report: Preflight,
    ledger: BudgetLedger,
    account: OpenRouterAccount,
    endpoint: ApprovedEndpoint,
    key: KeyStatus,
) -> list[CallRow]:
    """A read-only second look at quarantined calls, for example when generation metadata
    was not yet published during the run. It never changes a call's verification (one-way)
    or the breaker: it only reports, and passes only when every quarantined call now matches,
    the breaker is open for ``routing_anomaly`` alone and the key's usage is accounted for.
    Continuing is still the operator's reconcile and ``reset-breaker`` (budget_ledger.py)."""

    status = ledger.status()
    calls = [c for c in ledger.closed_calls_after(0) if c.verification == "quarantined"]
    report.add(
        "recheck.breaker_routing_anomaly",
        status.breaker_open and status.breaker_code == "routing_anomaly",
        f"breaker {'open (' + str(status.breaker_code) + ')' if status.breaker_open else 'closed'}",
    )
    report.add("recheck.quarantined_calls", bool(calls), f"{len(calls)} quarantined call(s)")
    rows: list[CallRow] = []
    for call in calls:
        row = _row(call, "recheck")
        rows.append(row)
        if call.generation_ref is None:
            row.verification_note = "no generation reference"
        else:
            try:
                mismatches = _compare(row, call, _metadata(account, call.generation_ref), endpoint)
                row.verification_note = ", ".join(mismatches) or "metadata matches"
            except AccountCheckError as error:
                row.verification_note = "metadata " + error.code
        report.add(
            f"recheck.call_{call.call_id}",
            row.verification_note == "metadata matches",
            f"{row.verification_note}; provider {row.provider_name}, model"
            f" {row.metadata_model}, metadata cost {row.metadata_cost_usd},"
            f" charged {row.charged_usd}",
        )
    usage = micro_usd(key.usage_usd)
    accounted = status.baseline + status.local_charged
    report.add(
        "recheck.usage_accounted",
        status.last_provider_usage <= usage <= accounted + RECONCILE_TOLERANCE_MICRO_USD,
        f"provider-reported key usage {_usd(usage)} within ledger {_usd(accounted)}"
        f" + tolerance {_usd(RECONCILE_TOLERANCE_MICRO_USD)}",
    )
    return rows


class LiveMonitor:
    """A ``ChatModel`` proxy for the harness: verifies each turn's calls before the next."""

    def __init__(
        self,
        inner: Any,
        ledger: BudgetLedger,
        account: OpenRouterAccount,
        endpoint: ApprovedEndpoint,
    ) -> None:
        self._inner = inner
        self._ledger = ledger
        self._account = account
        self._endpoint = endpoint
        self._turn = ""
        self._boundary = ledger.last_call_id()
        self.rows: list[CallRow] = []

    @property
    def name(self) -> str:
        name: str = self._inner.name
        return name

    @property
    def profile_id(self) -> str:
        profile: str = self._inner.profile_id
        return profile

    @property
    def endpoint_slug(self) -> str:
        slug: str = self._inner.endpoint_slug
        return slug

    def _verify_pending(self) -> None:
        for call in self._ledger.closed_calls_after(self._boundary):
            self.rows.append(
                verify_call(call, self._endpoint, self._account, self._ledger, self._turn)
            )
            self._boundary = call.call_id

    def begin(self, key: str, rep: int) -> None:
        self._verify_pending()
        self._turn = f"{key}@{rep}"

    def finish(self) -> None:
        self._verify_pending()

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        answer: ModelAnswer = self._inner.complete(messages)
        return answer

    async def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Piece, None]:
        # Closing this generator must close the guarded one, so its ledger settlement runs.
        async with aclosing(self._inner.stream(messages)) as source:
            async for piece in source:
                yield piece

    def warm(self, messages: list[dict[str, str]]) -> None:
        return None


# --- artifacts -------------------------------------------------------------------------------


def write_artifacts(
    out: Path,
    *,
    run: Any,
    questions: dict[str, str],
    monitor: LiveMonitor,
    preflight: Preflight,
    settings: dict[str, Any],
    ledger_before: LedgerStatus,
    ledger_after: LedgerStatus,
    extra: dict[str, str],
    metrics_of: Callable[[Any], dict[str, Any]] = lambda turn: dict(turn.metrics),
) -> tuple[Path, Path]:
    """``answers.jsonl``: synthetic questions and answers (content). ``calls.json``: telemetry,
    ledger and verification only (content-free)."""

    out.mkdir(parents=True, exist_ok=True)
    answers = out / "answers.jsonl"
    with answers.open("w", encoding="utf-8") as handle:
        for turn in run.turns:
            handle.write(
                json.dumps(
                    {
                        "key": turn.key,
                        "rep": turn.rep,
                        "question": questions.get(turn.key, ""),
                        "answered_by": turn.answered_by,
                        "fallback_reason": turn.fallback_reason,
                        "answer": turn.answer_text,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    calls = out / "calls.json"
    data = {
        "note": "Content-free. Synthetic Phase B run (D-092, proposed); answers are separate.",
        "manifest": {**run.manifest, **extra, "model": run.model},
        "settings": settings,
        "preflight": [asdict(check) for check in preflight.checks],
        "ledger_before": asdict(ledger_before),
        "ledger_after": asdict(ledger_after),
        "spent_usd": _usd(
            ledger_after.baseline
            + ledger_after.local_charged
            - ledger_before.baseline
            - ledger_before.local_charged
        ),
        "turns": [
            {
                "key": turn.key,
                "rep": turn.rep,
                "answered_by": turn.answered_by,
                "fallback_reason": turn.fallback_reason,
                "shown": list(turn.shown),
                "unmapped": turn.unmapped,
                "offered": len(turn.offered),
                "cited_entries": list(turn.cited_entries),
                "metrics": metrics_of(turn),
            }
            for turn in run.turns
        ],
        "calls": [asdict(row) for row in monitor.rows],
    }
    calls.write_text(json.dumps(data, indent=1, default=str) + "\n", encoding="utf-8")
    return answers, calls
