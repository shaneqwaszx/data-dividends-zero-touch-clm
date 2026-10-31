"""B1 Phase A: HR's read-only view of the Claude ledger's accounting and reconciliation windows.

The view reads the ledger with its own read methods (never ``BudgetLedger.open``, which closes
expired calls), never opens the GPT-OSS ledger and changes no store.
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from ai_assistant import anthropic_runtime, model_admin
from ai_assistant.anthropic_profiles import LEDGER_PROFILE_ID
from ai_assistant.budget import RECONCILE_TOLERANCE_MICRO_USD, BudgetLedger, Reservation
from ai_assistant.model_profiles import OPENROUTER_PROFILE_ID
from tests.test_claude_runtime import ClaudeJourney, reconciled_ago
from tests.test_model_management import API


def _view(journey: ClaudeJourney) -> dict[str, Any]:
    response = journey.client.get(f"{API}/budget")
    assert response.status_code == 200, response.text
    return dict(response.json()["claude"])


def _digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _ms(text: str) -> int:
    return int(datetime.fromisoformat(text).timestamp() * 1000)


def _claude_ledger(journey: ClaudeJourney) -> Path:
    return Path(journey.settings.anthropic_ledger_path)


def test_the_view_shows_the_ledger_and_its_reconciliation_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    view = _view(journey)["reconciliation"]
    reconciled = BudgetLedger(_claude_ledger(journey)).last_reconciled_ms()
    assert reconciled is not None
    assert view["key_alias"] == "key-01"
    assert abs(_ms(view["reconciled_at"]) - reconciled) < 1000
    chat = anthropic_runtime.CHAT_RECONCILE_SECONDS * 1000
    paid = anthropic_runtime.PAID_RECONCILE_SECONDS * 1000
    assert abs(_ms(view["chat_deadline_at"]) - (reconciled + chat)) < 1000
    assert abs(_ms(view["paid_deadline_at"]) - (reconciled + paid)) < 1000
    assert (view["chat_window_seconds"], view["paid_window_seconds"]) == (7 * 86_400, 86_400)
    assert view["chat_fresh"] is True
    assert view["paid_fresh"] is True
    assert view["tolerance_micro_usd"] == RECONCILE_TOLERANCE_MICRO_USD
    assert (
        view["estimate_micro_usd"] == view["baseline_micro_usd"] + view["local_charged_micro_usd"]
    )
    assert view["calls"] == {
        "total": 0,
        "open": 0,
        "settled": 0,
        "unsettled": 0,
        "abandoned": 0,
        "verified": 0,
        "quarantined": 0,
        "unverified": 0,
        "charged_micro_usd": 0,
    }


def test_a_claude_call_is_counted_and_charged_in_the_claude_view_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    journey.activate_claude()  # its qualification's paid calls are Claude calls too
    before = _view(journey)["reconciliation"]["calls"]
    assert journey.ask(stream=True)["answered_by"] == "model"
    view = _view(journey)["reconciliation"]
    ledger = BudgetLedger(_claude_ledger(journey))
    status = ledger.status()
    assert view["calls"]["total"] == before["total"] + 1 == ledger.last_call_id()
    assert view["calls"]["settled"] == before["settled"] + 1
    assert view["calls"]["open"] == 0
    assert view["calls"]["charged_micro_usd"] == status.local_charged > 0
    assert view["local_charged_micro_usd"] == status.local_charged
    assert view["estimate_micro_usd"] == status.baseline + status.local_charged
    # The GPT-OSS ledger's own view is a different ledger (never this block).
    assert "reconciliation" not in journey.client.get(f"{API}/budget").json()


@pytest.mark.parametrize(
    ("ago", "chat_fresh", "paid_fresh"),
    [(2 * 86_400, True, False), (8 * 86_400, False, False)],
)
def test_stale_windows_are_shown_as_stale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ago: int,
    chat_fresh: bool,
    paid_fresh: bool,
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    reconciled_ago(journey.settings, ago)
    view = _view(journey)["reconciliation"]
    assert view["chat_fresh"] is chat_fresh
    assert view["paid_fresh"] is paid_fresh
    now = time.time() * 1000
    assert (_ms(view["chat_deadline_at"]) < now) is not chat_fresh
    assert _ms(view["paid_deadline_at"]) < now


def test_reading_the_view_changes_no_ledger_and_closes_no_expired_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    claude = _claude_ledger(journey)
    gptoss = Path(journey.settings.budget_ledger_path)
    # An open Claude call whose lease ran out an hour ago: BudgetLedger.open would close it.
    past = BudgetLedger(claude, clock=lambda: time.time() - 3600)
    past.reserve(
        Reservation(10, 10, 1_000),
        endpoint_slug="anthropic/claude-sonnet-5-5",
        max_in_flight=1,
        lease_seconds=1,
        profile_id=LEDGER_PROFILE_ID,
    )
    before = (_digest(claude), _digest(gptoss))
    for _ in range(3):
        view = _view(journey)["reconciliation"]
    assert (_digest(claude), _digest(gptoss)) == before
    assert view["calls"]["open"] == 1
    assert view["calls"]["total"] == 1
    assert view["open_reserved_micro_usd"] == 1_000
    assert BudgetLedger(claude).status().open_calls == 1


def test_no_reconciliation_block_without_the_claude_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    claude = _claude_ledger(journey)
    claude.unlink()
    assert _view(journey)["reconciliation"] is None
    assert not claude.exists()  # the view never creates a ledger


def test_a_gptoss_ledger_at_the_claude_path_is_not_shown_or_changed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    claude = _claude_ledger(journey)
    claude.unlink()
    BudgetLedger.initialise(
        claude,
        cap_micro_usd=1_000_000,
        opening_usage_micro_usd=0,
        key_alias="key-02",
        profile_id=OPENROUTER_PROFILE_ID,
    )
    before = _digest(claude)
    assert _view(journey)["reconciliation"] is None
    assert _digest(claude) == before


def test_the_view_needs_the_hr_capability(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    journey.client.cookies.set("clm_session", "rm-session")  # an RM, without MODEL_CONFIG_MANAGE
    response = journey.client.get(f"{API}/budget")
    assert response.status_code == 403
    assert "reconciliation" not in response.text


# --- QG L1: one consistent ledger state per response ---------------------------------------


def _reserve(path: Path, lease_seconds: float = 600) -> str:
    return BudgetLedger(path).reserve(
        Reservation(10, 10, 1_000),
        endpoint_slug="anthropic/claude-sonnet-5-5",
        max_in_flight=1,
        lease_seconds=lease_seconds,
        profile_id=LEDGER_PROFILE_ID,
    )


def _settle_during_reads(
    monkeypatch: pytest.MonkeyPatch, path: Path, reservation: str | None, every_time: bool = False
) -> list[int]:
    # Another writer (a live call, another process) closes a call between the view's reads:
    # just before the reconciliation block lists the closed calls, after budget_status and
    # status() already saw the call open. Returns how often the hook ran.
    original = BudgetLedger.closed_calls_after
    runs: list[int] = []

    def hooked(self: BudgetLedger, call_id: int) -> Any:
        if every_time or not runs:
            # The first change closes the given open call; later ones open and close a new one.
            call = reservation if reservation is not None and not runs else _reserve(path)
            BudgetLedger(path).settle(call, usage=None, error_class="timeout")
        runs.append(1)
        return original(self, call_id)

    monkeypatch.setattr(BudgetLedger, "closed_calls_after", hooked)
    return runs


def _consistent(view: dict[str, Any], path: Path) -> None:
    # Every figure matches one ledger state (the current one: nothing changes after the view).
    ledger = BudgetLedger(path)
    status = ledger.status()
    closed = ledger.closed_calls_after(0)
    rec = view["reconciliation"]
    assert rec["calls"]["total"] == ledger.last_call_id() == len(closed) + status.open_calls
    assert rec["calls"]["open"] == status.open_calls == view["ledger"]["open_calls"]
    assert rec["calls"]["unsettled"] == sum(call.state == "unsettled" for call in closed)
    assert rec["open_reserved_micro_usd"] == status.open_reserved
    assert rec["local_charged_micro_usd"] == status.local_charged
    assert view["ledger"]["committed_micro_usd"] == status.committed
    assert view["ledger"]["headroom_micro_usd"] == status.headroom


def test_a_call_settled_during_the_reads_is_never_counted_twice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    claude = _claude_ledger(journey)
    reservation = _reserve(claude)
    runs = _settle_during_reads(monkeypatch, claude, reservation)
    view = _view(journey)
    assert len(runs) == 2  # the first read saw the change and the view was read again
    assert view["reconciliation"]["calls"]["open"] == 0
    assert view["reconciliation"]["calls"]["unsettled"] == 1
    assert view["reconciliation"]["calls"]["total"] == 1
    _consistent(view, claude)


def test_with_one_attempt_a_change_during_the_reads_withholds_the_figures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Without the re-read, the same change would have counted the call open and unsettled at
    # once; the view withholds the figures instead of returning that mix.
    monkeypatch.setattr(model_admin, "CLAUDE_VIEW_ATTEMPTS", 1)
    journey = ClaudeJourney(tmp_path, monkeypatch)
    claude = _claude_ledger(journey)
    _settle_during_reads(monkeypatch, claude, _reserve(claude))
    view = _view(journey)
    assert view["reconciliation"] is None
    assert view["ledger"] is None
    assert view["daily"] is None
    assert view["effective_remaining_micro_usd"] == 0
    assert view["refusal"]
    assert view["controls"]["lifetime"] is None


def test_a_ledger_that_keeps_changing_is_withheld_after_the_last_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    claude = _claude_ledger(journey)
    runs = _settle_during_reads(monkeypatch, claude, None, every_time=True)
    view = _view(journey)
    assert len(runs) == model_admin.CLAUDE_VIEW_ATTEMPTS
    assert view["reconciliation"] is None
    assert view["ledger"] is None
    assert view["refusal"] == "LEDGER_BUSY"


def test_the_consistency_check_never_writes_or_recovers_the_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The expired call (which BudgetLedger.open would close) stays open through every read,
    # and the file is unchanged: the read-only data_version connection never writes.
    journey = ClaudeJourney(tmp_path, monkeypatch)
    claude = _claude_ledger(journey)
    BudgetLedger(claude, clock=lambda: time.time() - 3600).reserve(
        Reservation(10, 10, 1_000),
        endpoint_slug="anthropic/claude-sonnet-5-5",
        max_in_flight=1,
        lease_seconds=1,
        profile_id=LEDGER_PROFILE_ID,
    )
    before = _digest(claude)
    view = _view(journey)
    assert _digest(claude) == before
    assert view["reconciliation"]["calls"]["open"] == 1
    _consistent(view, claude)


# --- GPT-OSS isolation --------------------------------------------------------------------


def test_the_reconciliation_reads_open_only_the_claude_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    claude = _claude_ledger(journey).resolve()
    gptoss = Path(journey.settings.budget_ledger_path).resolve()
    seen: list[Path] = []
    for name in ("closed_calls_after", "last_reconciled_ms"):
        original = getattr(BudgetLedger, name)

        def spy(self: BudgetLedger, *args: Any, _original: Any = original) -> Any:
            seen.append(Path(self._path).resolve())
            return _original(self, *args)

        monkeypatch.setattr(BudgetLedger, name, spy)
    assert _view(journey)["reconciliation"] is not None
    assert seen
    assert set(seen) == {claude}
    assert gptoss not in seen


def test_an_unreadable_gptoss_ledger_does_not_affect_the_claude_view(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    gptoss = Path(journey.settings.budget_ledger_path)
    gptoss.write_bytes(b"not a database")
    response = journey.client.get(f"{API}/budget")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ledger"] is None  # GPT-OSS's own block reports its ledger as unreadable
    assert body["claude"]["reconciliation"]["key_alias"] == "key-01"
    assert body["claude"]["ledger"] is not None
    assert gptoss.read_bytes() == b"not a database"


def test_an_unreadable_version_on_a_retry_withholds_instead_of_reading_unchecked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # QG L-a: the first attempt sees a change; the retry cannot read data_version (a writer
    # holds the lock). The view must not fall back to an unchecked read that could mix states.
    journey = ClaudeJourney(tmp_path, monkeypatch)
    claude = _claude_ledger(journey)
    _settle_during_reads(monkeypatch, claude, _reserve(claude))
    real_connect = model_admin.sqlite3.connect
    versions: list[int] = []

    class Busy:
        def __init__(self, connection: Any) -> None:
            self._connection = connection

        def execute(self, sql: str) -> Any:
            if "data_version" in sql:
                versions.append(1)
                if len(versions) == 3:  # before, after (changed), then the retry's before
                    raise model_admin.sqlite3.OperationalError("database is locked")
            return self._connection.execute(sql)

        def close(self) -> None:
            self._connection.close()

    def connect(database: Any, *args: Any, **kwargs: Any) -> Any:
        connection = real_connect(database, *args, **kwargs)
        watched = str(database) == f"{claude.resolve().as_uri()}?mode=ro"
        return Busy(connection) if watched else connection

    monkeypatch.setattr(model_admin.sqlite3, "connect", connect)
    view = _view(journey)
    assert len(versions) == 3
    assert view["reconciliation"] is None
    assert view["ledger"] is None
    assert view["refusal"] == "LEDGER_BUSY"
