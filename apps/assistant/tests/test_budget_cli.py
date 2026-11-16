"""The offline budget-ledger CLI (Phase A2, D-091 proposed; T4-13). Temporary ledgers only."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from ai_assistant.budget import BudgetLedger, Reservation

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "budget_ledger.py"


def _cli() -> ModuleType:
    spec = importlib.util.spec_from_file_location("budget_ledger_cli", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CLI = _cli()


def _run(path: Path, *args: str) -> int:
    code: int = CLI.main(["--ledger", str(path), *args])
    return code


def _init(path: Path, cap: str = "7.00", opening: str = "3.00") -> None:
    assert (
        _run(
            path, "init", "--cap", cap, "--opening-provider-usage", opening, "--key-alias", "key-01"
        )
        == 0
    )


def test_init_and_status_show_amounts_and_codes_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "ledger.sqlite3"
    _init(path)
    capsys.readouterr()

    assert _run(path, "status") == 0
    out = capsys.readouterr().out
    assert "cap: 7.000000" in out and "opening usage: 3.000000" in out
    assert "committed: 3.000000" in out and "headroom: 4.000000" in out
    assert "breaker: closed" in out and "key alias: key-01" in out
    # D-095: today's allowance, from the same ledger (nothing spent yet).
    # D-118: US$5.00 by default, held to the standing US$3.00 GPT-OSS day (D-138 R2).
    assert "daily cap: 3.000000" in out and "remaining today: 3.000000" in out
    assert "next daily reset: " in out and "+08:00" in out


def test_init_refuses_an_existing_ledger(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "ledger.sqlite3"
    _init(path)

    code = _run(
        path, "init", "--cap", "1", "--opening-provider-usage", "0", "--key-alias", "key-01"
    )
    assert code == 2 and "LEDGER_EXISTS" in capsys.readouterr().err
    assert BudgetLedger.open(path).status().opening_usage == 3_000_000


def test_status_of_a_missing_ledger_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "missing.sqlite3"
    assert _run(path, "status") == 2
    assert "LEDGER_MISSING" in capsys.readouterr().err and not path.exists()


@pytest.mark.parametrize("amount", ["-1", "0.0000001", "NaN", "abc", "1e400"])
def test_amounts_must_be_exact_usd_with_six_places(tmp_path: Path, amount: str) -> None:
    with pytest.raises(SystemExit):
        _run(
            tmp_path / "x.sqlite3",
            "init",
            "--cap",
            amount,
            "--opening-provider-usage",
            "0",
            "--key-alias",
            "key-01",
        )


def test_only_an_approved_key_alias_is_accepted(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        _run(
            tmp_path / "x.sqlite3",
            "init",
            "--cap",
            "1",
            "--opening-provider-usage",
            "0",
            "--key-alias",
            "Acme",
        )
    assert not (tmp_path / "x.sqlite3").exists()


def test_the_cap_is_lowered_freely_and_raised_only_with_confirmation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "ledger.sqlite3"
    _init(path)

    assert _run(path, "set-cap", "--usd", "5.00") == 0
    assert _run(path, "set-cap", "--usd", "7.50") == 2
    assert "CAP_RAISE_REFUSED" in capsys.readouterr().err
    assert _run(path, "set-cap", "--usd", "7.50", "--raise", "--confirm-new-cap", "7.49") == 2
    assert _run(path, "set-cap", "--usd", "7.50", "--raise", "--confirm-new-cap", "7.50") == 0
    assert BudgetLedger.open(path).status().cap == 7_500_000


def test_reconcile_and_breaker_reset_follow_the_rules(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_ASSISTANT_BUDGET_SETTLE_LAG_SECONDS", "0")  # configured: no lag
    path = tmp_path / "ledger.sqlite3"
    _init(path)
    # The earlier design's reset-breaker rules, on a store an operator anchored (D-118: a
    # session store refuses reset-breaker and uses resume-after-review instead).
    import sqlite3

    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE ledger_profile SET accounting_mode = 'provider_anchored'")
    ledger = BudgetLedger.open(path)
    rid = ledger.reserve(
        Reservation(10, 10, 72_452),
        endpoint_slug="fictional-provider/fp8",
        max_in_flight=1,
        lease_seconds=150,
    )
    ledger.settle(rid, usage=None, error_class=None)  # usage missing: breaker opens
    capsys.readouterr()

    assert _run(path, "reset-breaker", "--code", "usage_missing") == 2
    assert _run(path, "reconcile", "--provider-usage", "3.10", "--settle-lag-seconds", "0") == 0
    assert "provider minus ledger: 0.027548" in capsys.readouterr().out
    assert _run(path, "reconcile", "--provider-usage", "3.00", "--settle-lag-seconds", "0") == 2
    assert _run(path, "reset-breaker", "--code", "usage_missing") == 0
    status = BudgetLedger.open(path).status()
    assert not status.breaker_open and status.committed == 3_100_000


def _settled(path: Path) -> None:
    _init(path)
    ledger = BudgetLedger.open(path)
    rid = ledger.reserve(
        Reservation(10, 10, 72_452),
        endpoint_slug="fictional-provider/fp8",
        max_in_flight=1,
        lease_seconds=150,
    )
    ledger.settle(rid, usage=None, error_class=None, cancelled=True)


@pytest.mark.parametrize("lag", ["-1", "0", "599"])
def test_the_settle_lag_cannot_be_shortened_below_the_configured_lag(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], lag: str
) -> None:
    """QG F-2: the default configured lag is 600 s; a flag may lengthen it, never shorten it."""

    path = tmp_path / "ledger.sqlite3"
    _settled(path)
    capsys.readouterr()

    assert _run(path, "reconcile", "--provider-usage", "3.10", "--settle-lag-seconds", lag) == 2
    assert "RECONCILE_REFUSED" in capsys.readouterr().err
    assert BudgetLedger.open(path).status().last_provider_usage == 3_000_000


def test_the_configured_settle_lag_is_read(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "ledger.sqlite3"
    _settled(path)
    capsys.readouterr()

    assert _run(path, "reconcile", "--provider-usage", "3.10") == 2  # default 600 s: too soon
    monkeypatch.setenv("AI_ASSISTANT_BUDGET_SETTLE_LAG_SECONDS", "0")
    assert _run(path, "reconcile", "--provider-usage", "3.10") == 0
    assert _run(path, "reconcile", "--provider-usage", "3.20", "--settle-lag-seconds", "86400") == 2


def test_the_ledger_refuses_a_negative_or_non_finite_settle_lag(tmp_path: Path) -> None:
    from ai_assistant.budget import LedgerError

    path = tmp_path / "ledger.sqlite3"
    _settled(path)
    ledger = BudgetLedger.open(path)
    for lag in (-1, -0.001, float("nan"), float("inf"), 86_401):
        with pytest.raises(LedgerError) as raised:
            ledger.reconcile(3_100_000, settle_lag_seconds=lag)
        assert raised.value.code == "INVALID_INPUT"


def test_the_cli_reads_no_key_and_makes_no_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_remote_connections: list[str]
) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    before = list(no_remote_connections)
    path = tmp_path / "ledger.sqlite3"
    _init(path)
    _run(path, "status")
    _run(path, "reconcile", "--provider-usage", "3.00")

    assert no_remote_connections == before
    assert "OPENROUTER_API_KEY" not in SCRIPT.read_text(encoding="utf-8")


def test_resume_after_review_needs_the_owner_confirmation_and_keeps_the_charges(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # D-118 amendment P7: the owner clears a routing or integrity stop after review.
    path = tmp_path / "ledger.sqlite3"
    _init(path)
    ledger = BudgetLedger.open(path)
    ledger.open_breaker("routing_anomaly")
    charged = ledger.status().local_charged
    capsys.readouterr()

    assert _run(path, "resume-after-review", "--code", "routing_anomaly") == 2
    assert "BREAKER_RESUME_REFUSED" in capsys.readouterr().err
    assert BudgetLedger(path).status().breaker_open
    assert _run(path, "resume-after-review", "--code", "routing_anomaly", "--confirm-reviewed") == 0
    status = BudgetLedger(path).status()
    assert not status.breaker_open and status.local_charged == charged


def test_reset_breaker_is_refused_on_a_session_store_and_names_the_review_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # PR #156 QG note 3: reset-breaker records no review, so on a session store it would leave
    # later HR resumes blocked; the script refuses it there and writes nothing.
    path = tmp_path / "ledger.sqlite3"
    _init(path)
    ledger = BudgetLedger.open(path)
    ledger.open_breaker("routing_anomaly")
    before = path.read_bytes()
    capsys.readouterr()

    assert _run(path, "reset-breaker", "--code", "routing_anomaly") == 2
    err = capsys.readouterr().err
    assert "USE_RESUME_AFTER_REVIEW" in err and "resume-after-review" in err
    assert path.read_bytes() == before
    assert _run(path, "resume-after-review", "--code", "routing_anomaly", "--confirm-reviewed") == 0
    assert not BudgetLedger(path).status().breaker_open


def test_a_refused_reset_breaker_writes_nothing_even_with_an_expired_lease(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # PR #156 QG (cleanup round): the refusal is decided on a read-only open, so not even the
    # routine abandonment of an expired call is written.
    import time

    path = tmp_path / "ledger.sqlite3"
    _init(path)
    ledger = BudgetLedger.open(path)
    ledger.reserve(
        Reservation(10, 10, 1_000),
        endpoint_slug="fictional-provider/fp8",
        max_in_flight=1,
        lease_seconds=0.001,
    )
    ledger.open_breaker("routing_anomaly")
    time.sleep(0.05)  # the open call's lease has now expired
    before = path.read_bytes()
    capsys.readouterr()

    assert _run(path, "reset-breaker", "--code", "routing_anomaly") == 2
    assert "USE_RESUME_AFTER_REVIEW" in capsys.readouterr().err
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "args",
    [
        ["owner-close", "RUN1", "--reference", "ticket-1"],
        ["resolve-report", "RUN1"],
    ],
)
def test_the_run_commands_reach_their_handler(tmp_path: Path, args: list[str]) -> None:
    # D-138 R4 review N1: the run id used to overwrite the subcommand handler ("run"), so
    # these commands crashed with a TypeError before doing anything. Now they reach their
    # handler, which refuses cleanly on a ledger that does not exist (exit 2, nothing created).
    path = tmp_path / "missing.sqlite3"
    assert CLI.main(["--anthropic", "--ledger", str(path), *args]) == 2
    assert not path.exists()
