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
