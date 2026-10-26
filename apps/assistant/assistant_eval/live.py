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

After every turn the monitor fetches generation metadata for each new call: serving provider,
model and total cost must match, or the call is quarantined and the ledger breaker opens,
which refuses every later call (the batch stops). Answer text goes to ``answers.jsonl``;
everything else is content-free and goes to ``calls.json``.
"""

import json
from collections.abc import AsyncGenerator, Callable
from contextlib import aclosing
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from ai_assistant.budget import (
    RECONCILE_TOLERANCE_MICRO_USD,
    BudgetLedger,
    ClosedCall,
    LedgerStatus,
    reservation_for,
)
from ai_assistant.llm import ModelAnswer, Piece, micro_usd
from ai_assistant.model_profiles import OPENROUTER_BASE_URL, OPENROUTER_MODEL_ID, ApprovedEndpoint
from ai_assistant.openrouter_account import (
    AccountCheckError,
    GenerationFacts,
    KeyStatus,
    OpenRouterAccount,
)

# Owner directive (Phase B initial batch): at most US$1 of inference credits.
ALLOCATION_LIMIT_USD = Decimal("1.00")
_PUBLIC_TIMEOUT = 20.0


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


@dataclass
class Preflight:
    checks: list[Check] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str) -> None:
        self.checks.append(Check(name, ok, detail))

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.ok for check in self.checks)

    def lines(self) -> list[str]:
        return [f"{'PASS' if c.ok else 'FAIL'}  {c.name}: {c.detail}" for c in self.checks]


def _usd(micro: int) -> str:
    return f"{Decimal(micro) / Decimal(1_000_000):.6f}"


def fetch_public(path: str) -> Any:
    """An unauthenticated GET of OpenRouter's public model listing (no key, no content)."""

    with httpx.Client(timeout=_PUBLIC_TIMEOUT, trust_env=False, follow_redirects=False) as client:
        response = client.get(OPENROUTER_BASE_URL + path)
        response.raise_for_status()
        return json.loads(response.text, parse_float=Decimal)


def _price_per_m(value: object) -> Decimal | None:
    try:
        return Decimal(str(value)) * Decimal(1_000_000)
    except ArithmeticError:
        return None


def check_endpoint(report: Preflight, endpoint: ApprovedEndpoint, listing: Any, zdr: Any) -> None:
    """Re-verify the endpoint record against today's public listing and ZDR list."""

    try:
        _check_endpoint(report, endpoint, listing, zdr)
    except (AttributeError, TypeError, ValueError, ArithmeticError):
        report.add("endpoint.listing", False, "the public listing has an unexpected shape")


def _check_endpoint(report: Preflight, endpoint: ApprovedEndpoint, listing: Any, zdr: Any) -> None:
    endpoints = listing.get("data", {}).get("endpoints", []) if isinstance(listing, dict) else []
    endpoints = [item for item in endpoints if isinstance(item, dict)]
    tags = [item.get("tag") for item in endpoints]
    matching = [
        tag
        for tag in tags
        if isinstance(tag, str) and (tag == endpoint.slug or tag.startswith(endpoint.slug + "/"))
    ]
    report.add(
        "endpoint.slug_unique",
        matching == [endpoint.slug],
        f"{endpoint.slug} matches {len(matching)} of {len(tags)} listed endpoints",
    )
    row = next((item for item in endpoints if item.get("tag") == endpoint.slug), None)
    if row is None:
        report.add("endpoint.listed", False, "the approved endpoint is not listed")
        return
    pricing = row.get("pricing") or {}
    prompt, completion = (
        _price_per_m(pricing.get("prompt")),
        _price_per_m(pricing.get("completion")),
    )
    request = _price_per_m(pricing.get("request") or 0)
    extra = sorted(
        key
        for key in pricing
        if key not in ("prompt", "completion", "request", "discount", "input_cache_read")
        and _price_per_m(pricing[key]) not in (None, Decimal(0))
    )
    report.add(
        "endpoint.prices",
        prompt == endpoint.prompt_price_per_m
        and completion == endpoint.completion_price_per_m
        and request is not None
        and request / Decimal(1_000_000) == endpoint.request_price
        and not extra,
        f"listed prompt {prompt}/M completion {completion}/M (record "
        f"{endpoint.prompt_price_per_m}/{endpoint.completion_price_per_m}); other prices {extra}",
    )
    report.add(
        "endpoint.max_completion",
        row.get("max_completion_tokens") == endpoint.max_completion_tokens,
        f"listed {row.get('max_completion_tokens')} (record {endpoint.max_completion_tokens})",
    )
    report.add(
        "endpoint.identity",
        row.get("quantization") == endpoint.quantization
        and row.get("provider_name") == endpoint.provider_name
        and row.get("model_id") == OPENROUTER_MODEL_ID,
        f"provider {row.get('provider_name')}, quantization {row.get('quantization')}",
    )
    params = set(row.get("supported_parameters") or [])
    needed = {"reasoning", "max_tokens", "temperature"}
    report.add(
        "endpoint.parameters",
        needed <= params,
        f"supports {sorted(needed & params)} of {sorted(needed)}",
    )
    zdr_rows = zdr.get("data", []) if isinstance(zdr, dict) else []
    in_zdr = any(
        isinstance(item, dict)
        and item.get("tag") == endpoint.slug
        and item.get("model_id") == OPENROUTER_MODEL_ID
        for item in zdr_rows
    )
    report.add("endpoint.zdr_listed", in_zdr, f"in public ZDR list: {in_zdr}")


def check_key(
    report: Preflight,
    key: KeyStatus,
    reservation_micro: int,
    allocation: Decimal = ALLOCATION_LIMIT_USD,
) -> None:
    """The key's own limit (read before the ledger, whose opening usage must equal it). It
    is the provider-side backstop, so it may not leave more than the allocation plus one
    reservation (plan section 8.1 nesting)."""

    report.add(
        "key.limit_set",
        key.limit_usd is not None and key.limit_remaining_usd is not None,
        ("the key has a credit limit" if key.limit_usd is not None else "the key has no limit")
        + f"; provider-reported key usage {_usd(micro_usd(key.usage_usd))}",
    )
    report.add(
        "key.limit_never_resets",
        key.limit_reset is None,
        "limit_reset is null (never)" if key.limit_reset is None else "the limit resets",
    )
    remaining = micro_usd(key.limit_remaining_usd) if key.limit_remaining_usd is not None else -1
    report.add(
        "key.room_for_one_call",
        remaining >= reservation_micro,
        f"limit remaining {_usd(max(remaining, 0))} >= one reservation {_usd(reservation_micro)}",
    )
    backstop = micro_usd(allocation) + reservation_micro
    report.add(
        "key.limit_within_allocation",
        0 <= remaining <= backstop,
        f"limit remaining {_usd(max(remaining, 0))} <= allocation + one reservation"
        f" {_usd(backstop)}",
    )


def check_ledger(
    report: Preflight,
    key: KeyStatus,
    status: LedgerStatus,
    has_calls: bool,
    reservation_micro: int,
    allocation: Decimal = ALLOCATION_LIMIT_USD,
) -> None:
    report.add(
        "ledger.breaker_closed_no_open_calls",
        not status.breaker_open and status.open_calls == 0,
        f"breaker {'open (' + str(status.breaker_code) + ')' if status.breaker_open else 'closed'},"
        f" open calls {status.open_calls}",
    )
    allowed = micro_usd(allocation)
    report.add(
        "ledger.cap_within_allocation",
        0 < status.cap - status.opening_usage <= allowed,
        f"cap {_usd(status.cap)} - opening usage {_usd(status.opening_usage)}"
        f" <= allocation {_usd(allowed)}",
    )
    usage = micro_usd(key.usage_usd)
    accounted = status.baseline + status.local_charged
    if has_calls:
        ok = status.last_provider_usage <= usage <= accounted + RECONCILE_TOLERANCE_MICRO_USD
        detail = (
            f"provider usage {_usd(usage)} within ledger {_usd(accounted)}"
            f" + tolerance {_usd(RECONCILE_TOLERANCE_MICRO_USD)}"
        )
    else:
        ok = usage == status.opening_usage
        detail = f"provider usage {_usd(usage)} equals opening usage {_usd(status.opening_usage)}"
    report.add("ledger.usage_reconciled", ok, detail)
    report.add(
        "ledger.headroom_for_one_call",
        status.headroom >= reservation_micro,
        f"headroom {_usd(status.headroom)} >= one reservation {_usd(reservation_micro)}",
    )


def check_key_and_ledger(
    report: Preflight,
    key: KeyStatus,
    status: LedgerStatus,
    has_calls: bool,
    reservation_micro: int,
    allocation: Decimal = ALLOCATION_LIMIT_USD,
) -> None:
    check_key(report, key, reservation_micro)
    check_ledger(report, key, status, has_calls, reservation_micro, allocation)


def check_owner(report: Preflight, auto_topup_off: bool, prompt_logging_off: bool) -> None:
    report.add(
        "owner.auto_topup_off",
        auto_topup_off,
        "owner-attested (not readable through the API)",
    )
    report.add(
        "owner.prompt_logging_off",
        prompt_logging_off,
        "owner-attested (not readable through the API)",
    )


def typical_reservation(endpoint: ApprovedEndpoint, max_tokens: int) -> int:
    """A reservation for a large prompt (the 32 KiB prompt limit), for the headroom checks."""

    messages = [{"role": "system", "content": "x" * 32_000}, {"role": "user", "content": "x"}]
    return reservation_for(messages, endpoint, max_tokens).micro_usd


# --- per-turn verification -------------------------------------------------------------------


@dataclass
class CallRow:
    """One call, content-free: what the ledger recorded and what verification found."""

    turn: str
    call_id: int
    state: str
    error_class: str | None
    reserved_usd: str
    charged_usd: str
    prompt_tokens: int | None
    completion_tokens: int | None
    reasoning_tokens: int | None
    verification: str
    provider_name: str | None = None
    metadata_model: str | None = None
    metadata_cost_usd: str | None = None
    metadata_cancelled: bool | None = None
    verification_note: str = ""


def verify_call(
    call: ClosedCall,
    endpoint: ApprovedEndpoint,
    account: OpenRouterAccount,
    ledger: BudgetLedger,
    turn: str,
) -> CallRow:
    row = CallRow(
        turn=turn,
        call_id=call.call_id,
        state=call.state,
        error_class=call.error_class,
        reserved_usd=_usd(call.reserved_micro_usd),
        charged_usd=_usd(call.charged_micro_usd),
        prompt_tokens=call.prompt_tokens,
        completion_tokens=call.completion_tokens,
        reasoning_tokens=call.reasoning_tokens,
        verification=call.verification,
    )
    if call.verification != "unverified":
        row.verification_note = "already " + call.verification
        return row
    facts: GenerationFacts | None = None
    if call.generation_ref is None:
        # Missing verification evidence stops the batch (plan 6.7), whatever the call's state:
        # a refusal, a cancellation or a failure before any generation id was seen.
        ledger.record_verification(call.call_id, verified=False, breaker_code="routing_anomaly")
        row.verification, row.verification_note = "quarantined", "no generation reference"
        return row
    try:
        facts = account.generation(call.generation_ref)
    except AccountCheckError as error:
        ledger.record_verification(call.call_id, verified=False, breaker_code="routing_anomaly")
        row.verification, row.verification_note = "quarantined", "metadata " + error.code
        return row
    row.provider_name = facts.provider_name
    row.metadata_model = facts.model
    row.metadata_cost_usd = f"{facts.total_cost_usd:.8f}"
    row.metadata_cancelled = facts.cancelled
    expected = (endpoint.provider_name or "").casefold()
    provider_ok = facts.provider_name is not None and facts.provider_name.casefold() == expected
    model_ok = facts.model == OPENROUTER_MODEL_ID
    cost_ok = (
        call.state != "settled"
        or abs(micro_usd(facts.total_cost_usd) - call.charged_micro_usd) <= 1
    )
    if provider_ok and model_ok and cost_ok:
        ledger.record_verification(call.call_id, verified=True, breaker_code="routing_anomaly")
        row.verification = "verified"
        return row
    code = "routing_anomaly" if not (provider_ok and model_ok) else "reconcile_drift"
    ledger.record_verification(call.call_id, verified=False, breaker_code=code)
    row.verification = "quarantined"
    row.verification_note = ", ".join(
        note
        for ok, note in (
            (provider_ok, "provider mismatch"),
            (model_ok, "model mismatch"),
            (cost_ok, "cost mismatch"),
        )
        if not ok
    )
    return row


def verify_earlier_calls(
    report: Preflight,
    ledger: BudgetLedger,
    account: OpenRouterAccount,
    endpoint: ApprovedEndpoint,
) -> list[CallRow]:
    """Verify closed calls an earlier, interrupted run left unverified (M1). A mismatch
    quarantines them and opens the breaker, which the ledger checks then report."""

    rows = [
        verify_call(call, endpoint, account, ledger, "earlier-run")
        for call in ledger.unverified_closed_calls()
    ]
    quarantined = sum(1 for row in rows if row.verification != "verified")
    report.add(
        "ledger.earlier_calls_verified",
        quarantined == 0,
        f"{len(rows)} earlier unverified call(s) checked, {quarantined} quarantined",
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
