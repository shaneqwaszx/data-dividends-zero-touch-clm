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
status         amounts (USD) and codes only.
set-cap        lowering is always allowed; raising needs --raise and the same amount again.
reconcile      anchor the ledger on the key's cumulative usage from the dashboard. Refused
               while a call is open, too soon after the last call, or if usage would fall.
               An undercount is adopted (and opens the breaker above US$0.05); an over-count
               is kept unless --release is given.
reset-breaker  only after a reconcile that is newer than the breaker, and naming its code.

This script makes no network request: it reads no key and never contacts OpenRouter.
Phase A2 creates no real ledger; the remote profile is dormant.
"""

import argparse
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from ai_assistant.budget import (  # noqa: E402
    KEY_ALIASES,
    MAX_MICRO_USD,
    BudgetLedger,
    LedgerError,
)
from ai_assistant.config import AiAssistantSettings  # noqa: E402
from ai_assistant.model_factory import ledger_path  # noqa: E402

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
    return ledger_path(AiAssistantSettings(_env_file=None))


def cmd_init(args: argparse.Namespace) -> int:
    BudgetLedger.initialise(
        _path(args),
        cap_micro_usd=args.cap,
        opening_usage_micro_usd=args.opening_provider_usage,
        key_alias=args.key_alias,
    )
    print("ledger created")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    status = BudgetLedger.open(_path(args)).status()
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
    ):
        print(f"{name}: {value}")
    return 0


def cmd_set_cap(args: argparse.Namespace) -> int:
    BudgetLedger.open(_path(args)).set_cap(
        args.usd, allow_raise=args.raise_cap, confirm=args.confirm_new_cap
    )
    print("cap set")
    return 0


def cmd_reconcile(args: argparse.Namespace) -> int:
    drift = BudgetLedger.open(_path(args)).reconcile(
        args.provider_usage, release=args.release, settle_lag_seconds=args.settle_lag_seconds
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
    reconcile.add_argument("--settle-lag-seconds", type=float, default=600.0)
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
