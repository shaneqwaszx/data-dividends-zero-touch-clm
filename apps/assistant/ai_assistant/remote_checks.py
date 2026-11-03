"""Phase B provider checks (D-092 P3/P4, proposed), shared by the evaluation harness and the
D-094 local synthetic test mode (``remote_test.py``). Moved unchanged from the harness so the
service can use them without importing it.

    endpoint   the public listing still shows the approved endpoint with the recorded prices,
               maximum completion, quantization and provider, its slug matches no other
               endpoint of the model, and it is in the public ZDR list
    key        the key has a spending limit that never resets and room for one reservation
    ledger     initialised for this key, breaker closed, no open calls, its cap allows at most
               the allocation (US$1.00 here) beyond the key's usage when the ledger was made,
               and the key's provider-reported usage is fully accounted for

D-098: the CLM's own use (``remote_test.py``) passes ``allocation=None``. There is then no US$1
allocation ceiling: the key's limit must still be set, never reset and be finite
(``key.limit_finite``), and the ledger cap must stay above the key's opening usage
(``ledger.cap_above_opening``); the daily allowance, the lifetime cap and the key's own limit
are independent and the strictest wins. The Phase B harness keeps its D-092 allocation.
    owner      the owner attests auto top-up is off and prompt logging is off (neither is
               readable through the API)

``verify_call`` fetches generation metadata for one closed call (waiting, bounded, while it
is not yet published): serving provider, model and total cost must match, or the call is
quarantined and the ledger breaker opens, which refuses every later call.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from .budget import (
    MAX_MICRO_USD,
    RECONCILE_TOLERANCE_MICRO_USD,
    BudgetLedger,
    ClosedCall,
    LedgerError,
    LedgerStatus,
    reservation_for,
)
from .config import AiAssistantSettings
from .llm import micro_usd
from .model_profiles import (
    APPROVED_PROFILES,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL_ID,
    OPENROUTER_PROFILE_ID,
    ApprovedEndpoint,
    ProfileConfigError,
)
from .openrouter_account import AccountCheckError, GenerationFacts, KeyStatus, OpenRouterAccount

# Owner directive (Phase B initial batch): at most US$1 of inference credits.
ALLOCATION_LIMIT_USD = Decimal("1.00")
_PUBLIC_TIMEOUT = 20.0
# Generation metadata can lag the answer: the first live smoke call saw none within ~14 s
# (8 attempts, 2 s apart). Wait at most two minutes (25 attempts, 5 s apart) before a call
# counts as unverifiable; the wait stays bounded and the outcome still fails closed.
METADATA_ATTEMPTS = 25
METADATA_WAIT_SECONDS = 5.0


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


@dataclass
class Preflight:
    checks: list[Check] = field(default_factory=list)
    # The key's provider-reported remaining limit when it was read (D-095 budget status).
    key_remaining_micro_usd: int | None = None
    # D-098: the key's own limit, usage and reset policy as /key reported them (never the
    # account's credits, which are not read).
    key_limit_micro_usd: int | None = None
    key_usage_micro_usd: int | None = None
    key_limit_reset: str | None = None

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
    allocation: Decimal | None = ALLOCATION_LIMIT_USD,
) -> None:
    """The key's own limit (read before the ledger, whose opening usage must equal it). It
    is the provider-side backstop, so it may not leave more than the allocation plus one
    reservation (plan section 8.1 nesting). With no allocation (D-098) it must be finite."""

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
    if allocation is None:
        # D-098: a missing or unbounded provider limit never reads as permission to spend.
        report.add(
            "key.limit_finite",
            key.limit_usd is not None and 0 <= remaining <= MAX_MICRO_USD,
            f"limit remaining {_usd(max(remaining, 0))} is a finite provider-side limit",
        )
        return
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
    allocation: Decimal | None = ALLOCATION_LIMIT_USD,
) -> None:
    report.add(
        "ledger.breaker_closed_no_open_calls",
        not status.breaker_open and status.open_calls == 0,
        f"breaker {'open (' + str(status.breaker_code) + ')' if status.breaker_open else 'closed'},"
        f" open calls {status.open_calls}",
    )
    if allocation is None:
        # D-098: the HR lifetime cap has no allocation ceiling; it must allow some spend.
        report.add(
            "ledger.cap_above_opening",
            status.cap - status.opening_usage > 0,
            f"cap {_usd(status.cap)} > opening usage {_usd(status.opening_usage)}",
        )
    else:
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
    allocation: Decimal | None = ALLOCATION_LIMIT_USD,
) -> None:
    check_key(report, key, reservation_micro, allocation)
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


# --- per-call verification -------------------------------------------------------------------


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


def _row(call: ClosedCall, turn: str) -> CallRow:
    return CallRow(
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


def _metadata(account: OpenRouterAccount, ref: str) -> GenerationFacts:
    return account.generation(ref, attempts=METADATA_ATTEMPTS, wait_seconds=METADATA_WAIT_SECONDS)


def _compare(
    row: CallRow, call: ClosedCall, facts: GenerationFacts, endpoint: ApprovedEndpoint
) -> list[str]:
    """Copy the metadata into ``row`` and return what does not match (empty: all match)."""

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
    return [
        note
        for ok, note in (
            (provider_ok, "provider mismatch"),
            (model_ok, "model mismatch"),
            (cost_ok, "cost mismatch"),
        )
        if not ok
    ]


def verify_call(
    call: ClosedCall,
    endpoint: ApprovedEndpoint,
    account: OpenRouterAccount,
    ledger: BudgetLedger,
    turn: str,
) -> CallRow:
    row = _row(call, turn)
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
        facts = _metadata(account, call.generation_ref)
    except AccountCheckError as error:
        ledger.record_verification(call.call_id, verified=False, breaker_code="routing_anomaly")
        row.verification, row.verification_note = "quarantined", "metadata " + error.code
        return row
    mismatches = _compare(row, call, facts, endpoint)
    if not mismatches:
        ledger.record_verification(call.call_id, verified=True, breaker_code="routing_anomaly")
        row.verification = "verified"
        return row
    breaker = "reconcile_drift" if mismatches == ["cost mismatch"] else "routing_anomaly"
    ledger.record_verification(call.call_id, verified=False, breaker_code=breaker)
    row.verification = "quarantined"
    row.verification_note = ", ".join(mismatches)
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


def run_preflight(
    settings: AiAssistantSettings,
    open_account: Callable[[], OpenRouterAccount],
    *,
    ledger_file: Path,
    owner_attests_auto_topup_off: bool,
    owner_attests_prompt_logging_off: bool,
    fetch: Callable[[str], Any] = fetch_public,
    allocation: Decimal | None = ALLOCATION_LIMIT_USD,
) -> tuple[Preflight, BudgetLedger | None, OpenRouterAccount | None]:
    """Every check a live call needs, failing closed at the first one that cannot be
    evaluated. ``open_account`` opens the account client behind the caller's own gate.
    ``allocation`` None (D-098, the CLM's own use): no allocation ceiling, see the module."""

    report = Preflight()
    endpoint = APPROVED_PROFILES[OPENROUTER_PROFILE_ID].endpoint(settings.openrouter_endpoint)
    if endpoint is None:
        report.add("endpoint.approved", False, "the endpoint is not in the approved registry")
        return report, None, None
    try:
        account = open_account()
    except ProfileConfigError as error:
        report.add("gate.account", False, f"refused: {error.code}")
        return report, None, None
    report.add("gate.account", True, "live gate and decisions named; key present (not shown)")
    try:
        listing = fetch("/models/openai/gpt-oss-120b/endpoints")
        zdr = fetch("/endpoints/zdr")
    except Exception as error:  # noqa: BLE001 - any failure to read the listing refuses
        report.add("endpoint.listing", False, f"unreadable ({type(error).__name__})")
        return report, None, account
    check_endpoint(report, endpoint, listing, zdr)
    try:
        key = account.key_status()
    except AccountCheckError as error:
        report.add("key.status", False, f"refused: {error.code}")
        return report, None, account
    max_tokens = settings.llm_max_answer_tokens + settings.llm_reasoning_allowance_tokens
    reservation = typical_reservation(endpoint, max_tokens)
    check_key(report, key, reservation, allocation)
    if key.limit_remaining_usd is not None:
        report.key_remaining_micro_usd = micro_usd(key.limit_remaining_usd)
    if key.limit_usd is not None:
        report.key_limit_micro_usd = micro_usd(key.limit_usd)
    report.key_usage_micro_usd = micro_usd(key.usage_usd)
    report.key_limit_reset = key.limit_reset
    check_owner(report, owner_attests_auto_topup_off, owner_attests_prompt_logging_off)
    if allocation is None and report.passed and not ledger_file.exists():
        initialise_fresh(report, ledger_file, key)
    try:
        # D-099 (QG M-1/L-4): the profile is read without recovering, so another provider's
        # ledger is never recovered or verified here.
        probe = BudgetLedger(ledger_file)
        probe.verify()
        if probe.status().profile_id != OPENROUTER_PROFILE_ID:
            raise LedgerError("LEDGER_PROFILE_MISMATCH", "not the OpenRouter ledger")
        ledger = BudgetLedger.open(ledger_file)
        ledger.recover()
        status = ledger.status()
    except LedgerError as error:
        report.add("ledger.healthy", False, f"refused: {error.code}")
        return report, None, account
    report.add("ledger.healthy", True, f"profile {status.profile_id}, alias {status.key_alias}")
    try:
        verify_earlier_calls(report, ledger, account, endpoint)
        if allocation is None:
            auto_reconcile(report, ledger, key)
        status = ledger.status()
    except LedgerError as error:
        report.add("ledger.earlier_calls_verified", False, f"refused: {error.code}")
        return report, None, account
    check_ledger(report, key, status, ledger.last_call_id() > 0, reservation, allocation)
    check_daily(report, ledger, settings.budget_daily_cap_micro_usd, reservation)
    return report, ledger, account


# D-118 S5: a fresh deployment's ledger, and routine reconciliation, from the key's own
# provider-reported figures (read with the inference key; free). Never a paid call.
FRESH_CAP_ABOVE_OPENING_MICRO_USD = 30_000_000
FRESH_KEY_ALIAS = "key-01"
AUTO_RECONCILE_SETTLE_SECONDS = 600


def initialise_fresh(report: Preflight, ledger_file: Path, key: KeyStatus) -> None:
    """Create the OpenRouter ledger where none exists, only for a key whose provider limit is
    set, finite and never resets; its opening usage is the key's reported usage."""

    if key.limit_usd is None or key.limit_remaining_usd is None or key.limit_reset is not None:
        report.add("ledger.fresh_initialised", False, "the key has no fixed provider limit")
        return
    opening = micro_usd(key.usage_usd)
    room = min(micro_usd(key.limit_remaining_usd), FRESH_CAP_ABOVE_OPENING_MICRO_USD)
    try:
        BudgetLedger.initialise(
            ledger_file,
            cap_micro_usd=min(opening + max(room, 0), MAX_MICRO_USD),
            opening_usage_micro_usd=opening,
            key_alias=FRESH_KEY_ALIAS,
            profile_id=OPENROUTER_PROFILE_ID,
            accounting_mode="provider_anchored",
            opening_basis="provider_reported",
        )
    except LedgerError as error:
        report.add("ledger.fresh_initialised", False, f"refused: {error.code}")
        return
    report.add(
        "ledger.fresh_initialised",
        True,
        f"new ledger from provider-reported usage {_usd(opening)}",
    )


def auto_reconcile(report: Preflight, ledger: BudgetLedger, key: KeyStatus) -> None:
    """Adopt the key's reported usage when it is within the existing tolerance of the ledger
    (never a release, never above tolerance: that stays a failed check and the breaker)."""

    if ledger.profile().accounting_mode != "provider_anchored":
        return
    status = ledger.status()
    usage = micro_usd(key.usage_usd)
    accounted = status.baseline + status.local_charged
    if (
        status.breaker_open
        or status.open_calls
        or usage == status.last_provider_usage
        or not status.last_provider_usage <= usage <= accounted + RECONCILE_TOLERANCE_MICRO_USD
    ):
        return
    try:
        drift = ledger.reconcile(
            usage, settle_lag_seconds=AUTO_RECONCILE_SETTLE_SECONDS, automatic=True
        )
    except LedgerError as error:
        report.add("ledger.auto_reconciled", True, f"not yet: {error.code}")
        return
    report.add("ledger.auto_reconciled", True, f"provider usage adopted (drift {_usd(drift)})")


def check_daily(
    report: Preflight, ledger: BudgetLedger, daily_cap_micro_usd: int, reservation_micro: int
) -> None:
    """D-095: today's allowance (Asia/Singapore day) has room for one reservation. A daily cap
    setting outside 0..MAX_MICRO_USD reads as no allowance, so it fails closed."""

    try:
        daily = ledger.daily_status(daily_cap_micro_usd)
    except LedgerError as error:
        report.add("ledger.daily_room_for_one_call", False, f"refused: {error.code}")
        return
    report.add(
        "ledger.daily_room_for_one_call",
        daily.remaining >= reservation_micro,
        f"today's remaining allowance {_usd(daily.remaining)} of {_usd(daily.cap)}"
        f" (Asia/Singapore day) >= one reservation {_usd(reservation_micro)}",
    )
