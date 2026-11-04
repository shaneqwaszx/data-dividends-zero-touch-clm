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
reset-breaker  only after a reconcile that is newer than the breaker, and naming its code. The
               earlier design's command: refused on a D-118 session store (use
               resume-after-review there, which records the review).
resume-after-review  D-118 amendment P7, owner only, after reviewing a routing or ledger-integrity
               stop on a session store: closes the breaker (every charge kept), with
               --confirm-reviewed. Financial stops are resumed by HR in AI Models instead.

D-110 (HR reconciliation in AI Models): on the Anthropic ledger, reconcile, reset-breaker,
set-cap and verify take the reconcile lock beside the ledger and refuse while an HR run's
intent marker is there (resolve the run in AI Models, or close it with owner-close). Only
`reconcile --override-intent RUN` proceeds past it, recording the override on the marker
first; that run can then never be proven to be HR's.

verify         check every closed, unverified Claude call in-band (offline), as the chat's
               free preflight does.
runs           the HR reconciliation runs (read-only).
resolve-report what resolve would decide for a run now (read-only; nothing is written).
owner-close    the owner closes an unresolved run (or a requested one past its bound) with a
               reference. It records an owner acknowledgement, never that HR applied it, and
               never changes the ledger.
attest-legacy-retired
               the owner records that every earlier copy of this script and every earlier
               launcher has been retired (D-110 P1). HR reconciliation needs it.

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

--data-dir     (B0) the assistant's data root (AI_ASSISTANT_DATA_DIR), so the configured
               relative ledger paths resolve where the running service keeps them. The
               ledger path used is printed on stderr. --ledger, when given, wins.

This script makes no network request: it reads no key and never contacts OpenRouter.
Phase A2 creates no real ledger; the remote profile is dormant.
"""

import argparse
import json
import sqlite3
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from pydantic import ValidationError  # noqa: E402

from ai_assistant import anthropic_runtime  # noqa: E402
from ai_assistant import claude_reconciliation as reconciliation  # noqa: E402
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


def _settings(args: argparse.Namespace) -> AiAssistantSettings:
    # The process environment only (never .env, which may hold a key); --data-dir overrides
    # AI_ASSISTANT_DATA_DIR. An invalid data root is refused (DATA_DIR_INVALID).
    overrides = {"data_dir": args.data_dir} if args.data_dir else {}
    return AiAssistantSettings(_env_file=None, **overrides)


def _path(args: argparse.Namespace) -> Path:
    if args.ledger:
        path = Path(args.ledger)
    else:
        settings = _settings(args)
        path = anthropic_runtime.ledger_file(settings) if args.anthropic else ledger_path(settings)
    print(f"ledger: {path}", file=sys.stderr)
    return path


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
    settings = _settings(args)
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


def _is_anthropic(path: Path) -> bool:
    # Read without recovering. QG H1: an unreadable or busy ledger is never taken to be
    # another provider's (the lock and marker rules would be skipped): the error stands.
    return anthropic_runtime.ledger_profile(path) == LEDGER_PROFILE_ID


def _is_openrouter(path: Path) -> bool:
    try:
        return anthropic_runtime.ledger_profile(path) == OPENROUTER_PROFILE_ID
    except LedgerError:
        return False


@contextmanager
def _guarded(path: Path, override_run: str | None = None) -> Iterator[None]:
    # Every ledger not proven to be GPT-OSS's takes the reconcile lock and the marker rules.
    if not _is_openrouter(path):
        with reconciliation.operator_write(path, override_run=override_run):
            yield
    else:
        if override_run is not None:
            raise LedgerError("INVALID_INPUT", "--override-intent is for the Anthropic ledger")
        yield


def cmd_set_cap(args: argparse.Namespace) -> int:
    path = _path(args)
    with _guarded(path):
        return _set_cap(args, path)


def _set_cap(args: argparse.Namespace, path: Path) -> int:
    ledger = BudgetLedger.open(path)
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
    configured = float(_settings(args).budget_settle_lag_seconds)
    if args.settle_lag_seconds is None:
        return configured
    if args.settle_lag_seconds < configured:
        raise LedgerError(
            "RECONCILE_REFUSED", "the settle lag cannot be shorter than the configured lag"
        )
    lag: float = args.settle_lag_seconds
    return lag


def _reading_lag(args: argparse.Namespace, lag: float) -> float:
    # D-110 F8: with --reading-at (the Console's refresh time), every call must have closed
    # at least the margin before that reading.
    if args.reading_at is None:
        return lag
    reading = reconciliation.parse_moment(args.reading_at) / 1000
    margin = max(float(reconciliation.REFRESHED_MARGIN_SECONDS), lag)
    return max(lag, max(time.time() - reading, 0) + margin)


def cmd_reconcile(args: argparse.Namespace) -> int:
    path = _path(args)
    with _guarded(path, args.override_intent):
        ledger = BudgetLedger.open(path)
        unverified = len(ledger.unverified_closed_calls())
        if unverified and not _is_openrouter(path):
            print(
                f"warning: {unverified} closed call(s) not verified; run verify first",
                file=sys.stderr,
            )
        drift = ledger.reconcile(
            args.provider_usage,
            release=args.release,
            settle_lag_seconds=_reading_lag(args, _settle_lag(args)),
        )
    sign = "-" if drift < 0 else ""
    print(f"reconciled; provider minus ledger: {sign}{usd(abs(drift))}")
    return 0


def cmd_reset_breaker(args: argparse.Namespace) -> int:
    path = _path(args)
    with _guarded(path):
        # Read-only first (never recovered here), so a refusal writes nothing at all.
        probe = BudgetLedger(path)
        probe.verify()
        if probe.profile().accounting_mode == "provider_capped":
            # D-118: on a session store the owner's review is recorded by resume-after-review;
            # reset-breaker would close the stop without that record, so later HR resumes
            # would stay blocked.
            raise LedgerError(
                "USE_RESUME_AFTER_REVIEW",
                "a session store: run resume-after-review --code CODE --confirm-reviewed",
            )
        BudgetLedger.open(path).reset_breaker(args.code)
    print("breaker reset")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    path = _path(args)
    if not _is_anthropic(path):
        raise LedgerError("INVALID_INPUT", "verify is for the Anthropic ledger")
    with _guarded(path):
        checked, quarantined = anthropic_runtime.verify_calls(BudgetLedger.open(path))
    print(f"checked {checked} call(s); quarantined {quarantined}")
    return 0


def _reconciler(args: argparse.Namespace, path: Path) -> reconciliation.Reconciler:
    from ai_assistant.model_admin import store_file

    settings = _settings(args)
    return reconciliation.Reconciler(
        lambda: path,
        reconciliation.Runs(store_file(settings)),
        lambda: float(settings.budget_settle_lag_seconds),
    )


def cmd_runs(args: argparse.Namespace) -> int:
    print(json.dumps(_reconciler(args, _path(args)).listing(), indent=1))
    return 0


def cmd_resolve_report(args: argparse.Namespace) -> int:
    path = _path(args)
    recon = _reconciler(args, path)
    run = recon.runs.get(args.run)
    if run is None:
        raise reconciliation.ReconcileRefused("RUN_UNKNOWN")
    if run["status"] != reconciliation.REQUESTED:
        print(f"{run['status']} (already decided; nothing to resolve)")
        return 0
    snapshot = reconciliation.read_snapshot(path, events_after=int(run["pre_event_id"]))
    status, reason = reconciliation.classify(
        run,
        snapshot,
        reconciliation.read_marker(path),
        sharing=recon.runs.sharing(run["ledger_id"], run["pre_event_id"], run["run_id"]),
        prerequisite=recon.runs.prerequisite(),
    )
    bound = reconciliation.iso(reconciliation.resolve_bound_ms(run))
    print(f"report only: would be {status} ({reason}); resolvable after {bound}")
    return 0


def cmd_owner_close(args: argparse.Namespace) -> int:
    path = _path(args)
    result = _reconciler(args, path).owner_close(
        args.run, by=args.by, reference=args.reference, acknowledged_event_id=args.acknowledge_event
    )
    print(json.dumps(result, indent=1))
    return 0


def cmd_attest_legacy_retired(args: argparse.Namespace) -> int:
    path = _path(args)
    if not args.reference.strip():
        raise LedgerError("INVALID_INPUT", "a reference is required")
    _reconciler(args, path).runs.record_prerequisite(args.by, args.reference.strip()[:200])
    print("recorded: earlier copies of this script and earlier launchers are retired")
    return 0


def cmd_resume_after_review(args: argparse.Namespace) -> int:
    if not args.confirm_reviewed:
        raise LedgerError("BREAKER_RESUME_REFUSED", "review the stop, then pass --confirm-reviewed")
    path = _path(args)
    with _guarded(path):
        covered = BudgetLedger.open(path).resume_breaker(args.code, owner_reviewed=True)
    print(f"breaker resumed after review (calls up to {covered}; every charge kept)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--ledger", help="ledger file (default: the configured path)")
    parser.add_argument("--data-dir", help="the assistant data root (AI_ASSISTANT_DATA_DIR)")
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
    reconcile.add_argument("--reading-at", help="the Console's refresh time (ISO 8601)")
    reconcile.add_argument("--override-intent", metavar="RUN", default=None)
    reconcile.set_defaults(run=cmd_reconcile)

    reset = commands.add_parser("reset-breaker")
    reset.add_argument("--code", required=True)
    reset.set_defaults(run=cmd_reset_breaker)

    commands.add_parser("verify").set_defaults(run=cmd_verify)
    commands.add_parser("runs").set_defaults(run=cmd_runs)

    report = commands.add_parser("resolve-report")
    report.add_argument("run")
    report.set_defaults(run=cmd_resolve_report)

    close = commands.add_parser("owner-close")
    close.add_argument("run")
    close.add_argument("--reference", required=True)
    close.add_argument("--acknowledge-event", type=int, default=None)
    close.add_argument("--by", default="owner")
    close.set_defaults(run=cmd_owner_close)

    attest = commands.add_parser("attest-legacy-retired")
    attest.add_argument("--reference", required=True)
    attest.add_argument("--by", default="owner")
    attest.set_defaults(run=cmd_attest_legacy_retired)

    review = commands.add_parser("resume-after-review")
    review.add_argument("--code", required=True)
    review.add_argument("--confirm-reviewed", action="store_true")
    review.set_defaults(run=cmd_resume_after_review)

    args = parser.parse_args(argv)
    try:
        code: int = args.run(args)
    except LedgerError as error:
        print(f"refused ({error.code}): {error}", file=sys.stderr)
        return 2
    except reconciliation.ReconcileRefused as refused:
        facts = f" {json.dumps(refused.facts)}" if refused.facts else ""
        print(f"refused ({refused.code}){facts}", file=sys.stderr)
        if refused.code == "RUN_UNRESOLVED":
            print(
                "an HR reconciliation run is open or its marker remains: resolve it in AI Models,"
                " or the owner runs: owner-close RUN --reference TEXT",
                file=sys.stderr,
            )
        return 2
    except reconciliation.RunConflict as conflict:
        print(f"refused (RUN_CONFLICT): run {conflict} changed meanwhile", file=sys.stderr)
        return 2
    except sqlite3.Error:
        print("refused (RUN_STORE_UNAVAILABLE): the model state database", file=sys.stderr)
        return 2
    except ValidationError as error:
        # QG L3: name the failing settings (field names only, never values).
        fields = sorted({str(item["loc"][0]) for item in error.errors() if item.get("loc")})
        if fields:
            print(
                f"refused (SETTINGS_INVALID): invalid settings: {', '.join(fields)}",
                file=sys.stderr,
            )
        else:
            print(
                "refused (DATA_DIR_INVALID): the data root and its store paths must be an"
                " existing absolute directory and paths inside it",
                file=sys.stderr,
            )
        return 2
    return code


if __name__ == "__main__":
    raise SystemExit(main())
