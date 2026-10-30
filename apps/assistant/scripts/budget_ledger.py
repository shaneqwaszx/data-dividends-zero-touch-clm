"""Operator commands for the remote profile's lifetime budget ledger (offline; D-091 proposed).

    cd apps/assistant
    ../../.venv/bin/python scripts/budget_ledger.py status
    ../../.venv/bin/python scripts/budget_ledger.py init --cap 7.00 \\
        --opening-provider-usage 0.00 --key-alias key-01
    ../../.venv/bin/python scripts/budget_ledger.py set-cap --usd 5.00
    ../../.venv/bin/python scripts/budget_ledger.py set-cap --usd 7.50 --raise \
        --confirm-new-cap 7.50
    ../../.venv/bin/python scripts/budget_ledger.py reconcile --provider-usage 3.21 [--release]
    ../../.venv/bin/python scripts/budget_ledger.py reset-breaker --code usage_missing

init           create a ledger where none exists. The opening provider usage is the key's
               current cumulative usage as the OpenRouter dashboard shows it, so a new ledger
               never resets what the key already spent. The cap is the key's lifetime usage
               limit for this ledger, opening usage included.
status         amounts (USD) and codes only, with today's D-095 allowance (Asia/Singapore day).
set-cap        lowering is always allowed; raising needs --raise and the same amount again.
reconcile      anchor the ledger on the key's cumulative usage from the dashboard. Refused
               while a call is open, too soon after the last call (the configured
               AI_ASSISTANT_BUDGET_SETTLE_LAG_SECONDS, default 600; a flag may lengthen it,
               never shorten it), or if usage would fall.
               An undercount is adopted (and opens the breaker above US$0.05); an over-count
               is kept unless --release is given.
reset-breaker  only after a reconcile that is newer than the breaker, and naming its code.

--anthropic    (D-099 Option B) the separate Anthropic ledger for Claude Sonnet 5.5
               (AI_ASSISTANT_ANTHROPIC_LEDGER_PATH). Its provider usage is the dedicated
               workspace's cumulative cost as the Claude Console shows it. Its cap may never
               exceed US$30.00 (lifetime, never reset; D-102; a cap above the attested
               workspace limit is refused at every call), and raising it needs a reconcile
               within the last 24 hours; these rules follow
               the ledger's own profile, whichever path names it. HR may also change the cap
               on AI Models within the same rules (D-102).

    ../../.venv/bin/python scripts/budget_ledger.py --anthropic init --cap 5.00 \\
        --opening-provider-usage 0.00 --key-alias key-01
    ../../.venv/bin/python scripts/budget_ledger.py --anthropic reconcile --provider-usage 0.42

This script makes no network request: it reads no key and never contacts OpenRouter.
Phase A2 creates no real ledger; the remote profile is dormant.
"""

import argparse
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from ai_assistant import anthropic_runtime  # noqa: E402
from ai_assistant.anthropic_profiles import LEDGER_PROFILE_ID  # noqa: E402
from ai_assistant.budget import (  # noqa: E402
    KEY_ALIASES,
    MAX_MICRO_USD,
    SINGAPORE,
    BudgetLedger,
    LedgerError,
)
from ai_assistant.config import AiAssistantSettings  # noqa: E402
from ai_assistant.model_factory import ledger_path  # noqa: E402
from ai_assistant.model_profiles import OPENROUTER_PROFILE_ID  # noqa: E402

_MICRO = Decimal("0.000001")
_MAX_USD = Decimal(MAX_MICRO_USD) * _MICRO


def micro(text: str) -> int:
    """An exact USD amount with at most 6 decimal places, as micro-USD."""

    try:
        value = Decimal(text)
        exact = value.is_finite() and 0 <= value <= _MAX_USD and value == value.quantize(_MICRO)
    except InvalidOperation:
        raise argparse.ArgumentTypeError("not an amount") from None
    if not exact:
        raise argparse.ArgumentTypeError("not an amount with at most 6 decimal places")
    return int(value / _MICRO)


def usd(amount: int) -> str:
    return f"{Decimal(amount) * _MICRO:.6f}"


def _path(args: argparse.Namespace) -> Path:
    if args.ledger:
        return Path(args.ledger)
    settings = AiAssistantSettings(_env_file=None)
    return anthropic_runtime.ledger_file(settings) if args.anthropic else ledger_path(settings)


def cmd_init(args: argparse.Namespace) -> int:
    if args.anthropic and args.cap > anthropic_runtime.LIFETIME_CEILING_MICRO_USD:
        raise LedgerError("INVALID_INPUT", "above the Anthropic lifetime ceiling")
    BudgetLedger.initialise(
        _path(args),
        cap_micro_usd=args.cap,
        opening_usage_micro_usd=args.opening_provider_usage,
        key_alias=args.key_alias,
        profile_id=LEDGER_PROFILE_ID if args.anthropic else OPENROUTER_PROFILE_ID,
    )
    print("ledger created")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    ledger = BudgetLedger.open(_path(args))
    status = ledger.status()
    settings = AiAssistantSettings(_env_file=None)
    anthropic = status.profile_id == LEDGER_PROFILE_ID
    daily = ledger.daily_status(
        settings.anthropic_daily_cap_micro_usd if anthropic else settings.budget_daily_cap_micro_usd
    )
    reconciled = ledger.last_reconciled_ms()
    reset = datetime.fromtimestamp(daily.next_reset_at / 1000, SINGAPORE)
    for name, value in (
        ("cap", usd(status.cap)),
        ("opening usage", usd(status.opening_usage)),
        ("baseline", usd(status.baseline)),
        ("charged since baseline", usd(status.local_charged)),
        ("open reservations", usd(status.open_reserved)),
        ("committed", usd(status.committed)),
        ("headroom", usd(status.headroom)),
        ("last provider usage", usd(status.last_provider_usage)),
        ("open calls", str(status.open_calls)),
        ("breaker", status.breaker_code or "closed"),
        ("key alias", status.key_alias),
        ("profile", status.profile_id),
        (
            "last reconciled",
            "never"
            if reconciled is None
            else datetime.fromtimestamp(reconciled / 1000, SINGAPORE).isoformat(),
        ),
        ("daily cap", usd(daily.cap)),
        ("settled today", usd(daily.settled_today)),
        ("in flight today", usd(daily.open_reserved)),
        ("remaining today", usd(daily.remaining)),
        ("next daily reset", reset.isoformat()),
    ):
        print(f"{name}: {value}")
    return 0


def cmd_set_cap(args: argparse.Namespace) -> int:
    ledger = BudgetLedger.open(_path(args))
    status = ledger.status()
    # D-099: the Anthropic rules, checked against the cap the change is then made from.
    expected = None
    if status.profile_id == LEDGER_PROFILE_ID:
        anthropic_runtime.check_cap_change(ledger, args.usd, raising=args.usd > status.cap)
        expected = status.cap
    ledger.set_cap(
        args.usd, allow_raise=args.raise_cap, confirm=args.confirm_new_cap, expected=expected
    )
    print("cap set")
    return 0


def _settle_lag(args: argparse.Namespace) -> float:
    configured = float(AiAssistantSettings(_env_file=None).budget_settle_lag_seconds)
    if args.settle_lag_seconds is None:
        return configured
    if args.settle_lag_seconds < configured:
        raise LedgerError(
            "RECONCILE_REFUSED", "the settle lag cannot be shorter than the configured lag"
        )
    lag: float = args.settle_lag_seconds
    return lag


def cmd_reconcile(args: argparse.Namespace) -> int:
    drift = BudgetLedger.open(_path(args)).reconcile(
        args.provider_usage, release=args.release, settle_lag_seconds=_settle_lag(args)
    )
    sign = "-" if drift < 0 else ""
    print(f"reconciled; provider minus ledger: {sign}{usd(abs(drift))}")
    return 0


def cmd_reset_breaker(args: argparse.Namespace) -> int:
    BudgetLedger.open(_path(args)).reset_breaker(args.code)
    print("breaker reset")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--ledger", help="ledger file (default: the configured path)")
    parser.add_argument(
        "--anthropic", action="store_true", help="the separate Anthropic ledger (D-099)"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init")
    init.add_argument("--cap", type=micro, required=True)
    init.add_argument("--opening-provider-usage", type=micro, required=True)
    init.add_argument("--key-alias", choices=KEY_ALIASES, required=True)
    init.set_defaults(run=cmd_init)

    commands.add_parser("status").set_defaults(run=cmd_status)

    set_cap = commands.add_parser("set-cap")
    set_cap.add_argument("--usd", type=micro, required=True)
    set_cap.add_argument("--raise", dest="raise_cap", action="store_true")
    set_cap.add_argument("--confirm-new-cap", type=micro)
    set_cap.set_defaults(run=cmd_set_cap)

    reconcile = commands.add_parser("reconcile")
    reconcile.add_argument("--provider-usage", type=micro, required=True)
    reconcile.add_argument("--release", action="store_true")
    reconcile.add_argument("--settle-lag-seconds", type=float, default=None)
    reconcile.set_defaults(run=cmd_reconcile)

    reset = commands.add_parser("reset-breaker")
    reset.add_argument("--code", required=True)
    reset.set_defaults(run=cmd_reset_breaker)

    args = parser.parse_args(argv)
    try:
        code: int = args.run(args)
    except LedgerError as error:
        print(f"refused ({error.code}): {error}", file=sys.stderr)
        return 2
    return code


if __name__ == "__main__":
    raise SystemExit(main())
