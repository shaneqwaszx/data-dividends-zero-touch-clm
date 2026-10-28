"""The D-095 daily allowance: at most US$1.00 reserved plus settled per Singapore calendar day,
enforced in the ledger's own admission transaction. Synthetic micro-USD amounts only; no real
ledger and no network."""

import multiprocessing
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ai_assistant.budget import (
    DAILY_CAP_CEILING_MICRO_USD,
    BudgetLedger,
    BudgetRefusedError,
    Reservation,
    daily_cap_for,
    next_singapore_reset_ms,
    singapore_day_start_ms,
)
from ai_assistant.llm import ModelUsage
from tests.remote_fixtures import ENDPOINT, new_ledger

# 2027-01-15 08:00 UTC is 16:00 in Singapore; Singapore midnight is 16:00 UTC.
NOON_SGT = datetime(2027, 1, 15, 4, 0, tzinfo=UTC).timestamp()
BEFORE_MIDNIGHT_SGT = datetime(2027, 1, 15, 15, 59, 30, tzinfo=UTC).timestamp()
AFTER_MIDNIGHT_SGT = datetime(2027, 1, 15, 16, 0, 1, tzinfo=UTC).timestamp()


class Clock:
    def __init__(self, start: float = NOON_SGT) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


def _ledger(tmp_path: Path, clock: Clock, *, cap: int = 7_000_000) -> BudgetLedger:
    path = new_ledger(tmp_path / "ledger.sqlite3", cap=cap, clock=clock)
    return BudgetLedger.open(path, clock=clock)


def _admit(ledger: BudgetLedger, micro: int, daily: int | None = None) -> str:
    return ledger.reserve(
        Reservation(1_000, 1_000, micro),
        endpoint_slug=ENDPOINT.slug,
        max_in_flight=1000,
        lease_seconds=3600,
        daily_cap_micro_usd=daily,
    )


def _refusal(ledger: BudgetLedger, micro: int, daily: int | None = None) -> str:
    with pytest.raises(BudgetRefusedError) as raised:
        _admit(ledger, micro, daily)
    assert raised.value.budget is not None
    return raised.value.budget.outcome


def _usage(cost: str) -> ModelUsage:
    from decimal import Decimal

    return ModelUsage(
        prompt_tokens=10, completion_tokens=10, cost=Decimal(cost), generation_ref="gen-1"
    )


def test_singapore_day_boundaries() -> None:
    noon = int(NOON_SGT * 1000)
    start = singapore_day_start_ms(noon)
    assert datetime.fromtimestamp(start / 1000, UTC) == datetime(2027, 1, 14, 16, tzinfo=UTC)
    assert next_singapore_reset_ms(noon) == start + 86_400_000
    after = int(AFTER_MIDNIGHT_SGT * 1000)
    assert singapore_day_start_ms(after) == start + 86_400_000


def test_the_ceiling_is_one_dollar_and_a_setting_may_only_lower_it() -> None:
    assert DAILY_CAP_CEILING_MICRO_USD == 1_000_000
    assert daily_cap_for(None) == 1_000_000
    assert daily_cap_for(250_000) == 250_000
    assert daily_cap_for(1_000_001) is None and daily_cap_for(-1) is None
    assert daily_cap_for(True) is None  # type: ignore[arg-type]


def test_settled_spend_plus_open_reservations_never_exceed_the_daily_cap(
    tmp_path: Path,
) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, clock)
    first = _admit(ledger, 400_000)
    ledger.settle(first, usage=_usage("0.300000"), error_class=None)
    _admit(ledger, 400_000)  # open: counts at its reservation
    status = ledger.daily_status()
    assert (status.settled_today, status.open_reserved, status.remaining) == (
        300_000,
        400_000,
        300_000,
    )
    assert _refusal(ledger, 300_001) == "refused_daily_cap"
    _admit(ledger, 300_000)
    assert _refusal(ledger, 1) == "refused_daily_cap"
    # The lifetime ledger was not touched by the refusals.
    assert ledger.status().committed == 1_000_000


def test_a_lower_setting_applies_and_an_out_of_range_setting_refuses(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, Clock())
    _admit(ledger, 200_000, daily=250_000)
    assert _refusal(ledger, 50_001, daily=250_000) == "refused_daily_cap"
    assert _refusal(ledger, 1, daily=2_000_000) == "refused_daily_cap"
    assert ledger.status().open_calls == 1


def test_the_stricter_lifetime_cap_still_applies(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, Clock(), cap=150_000)
    _admit(ledger, 100_000)
    assert _refusal(ledger, 60_000) == "refused_cap"


def test_midnight_moves_the_window_without_erasing_history(tmp_path: Path) -> None:
    clock = Clock(BEFORE_MIDNIGHT_SGT)
    ledger = _ledger(tmp_path, clock)
    settled = _admit(ledger, 600_000)
    ledger.settle(settled, usage=_usage("0.600000"), error_class=None)
    still_open = _admit(ledger, 300_000)
    assert _refusal(ledger, 200_000) == "refused_daily_cap"
    lifetime = ledger.status().committed

    clock.now = AFTER_MIDNIGHT_SGT
    status = ledger.daily_status()
    # Yesterday's settled call left the window; yesterday's OPEN call still counts today.
    assert (status.settled_today, status.open_reserved) == (0, 300_000)
    _admit(ledger, 700_000)
    assert _refusal(ledger, 1) == "refused_daily_cap"
    # Nothing was erased: the lifetime totals and every call row remain.
    assert ledger.status().committed == lifetime + 700_000
    assert len(ledger.closed_calls_after(0)) == 1
    ledger.settle(still_open, usage=_usage("0.100000"), error_class=None)
    # Settled after midnight but reserved yesterday: it stays yesterday's spend.
    assert ledger.daily_status().settled_today == 0


def test_a_restart_keeps_todays_spend(tmp_path: Path) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, clock)
    rid = _admit(ledger, 900_000)
    ledger.settle(rid, usage=_usage("0.900000"), error_class=None)
    reopened = BudgetLedger.open(tmp_path / "ledger.sqlite3", clock=clock)
    assert reopened.daily_status().settled_today == 900_000
    assert _refusal(reopened, 100_001) == "refused_daily_cap"


def test_missing_usage_and_a_crashed_call_are_charged_in_full_today(tmp_path: Path) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, clock)
    rid = _admit(ledger, 300_000)
    # A timed-out call without a provider cost is charged its full reservation.
    ledger.settle(rid, usage=None, error_class="timeout")
    _admit(ledger, 300_000)  # this process "crashes" with the call open
    clock.now += 7200  # past the lease
    reopened = BudgetLedger.open(tmp_path / "ledger.sqlite3", clock=clock)
    status = reopened.daily_status()
    assert (status.settled_today, status.open_reserved) == (600_000, 0)
    assert reopened.status().breaker_open  # the abandoned call trips it


def test_reconciliation_does_not_reset_the_daily_allowance(tmp_path: Path) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, clock)
    rid = _admit(ledger, 800_000)
    ledger.settle(rid, usage=_usage("0.800000"), error_class=None)
    clock.now += 3600
    ledger.reconcile(800_000)
    assert ledger.daily_status().settled_today == 800_000
    assert _refusal(ledger, 200_001) == "refused_daily_cap"


def test_threads_near_the_cap_never_overshoot(tmp_path: Path) -> None:
    clock = Clock()
    path = new_ledger(tmp_path / "ledger.sqlite3", cap=7_000_000, clock=clock)
    admitted: list[str] = []
    lock = threading.Lock()

    def worker() -> None:
        ledger = BudgetLedger.open(path, clock=clock, busy_timeout=10.0)
        for _ in range(5):
            try:
                rid = _admit(ledger, 70_000)
            except BudgetRefusedError:
                continue
            with lock:
                admitted.append(rid)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(admitted) == 14  # 14 x 70,000 = 980,000; a 15th would pass US$1.00
    assert BudgetLedger.open(path, clock=clock).daily_status().committed == 980_000


def _process_worker(path: str, count: int, results: Any) -> None:
    ledger = BudgetLedger.open(Path(path), busy_timeout=10.0)
    for _ in range(count):
        try:
            _admit(ledger, 100_000)
            results.put(1)
        except BudgetRefusedError:
            results.put(0)


def test_two_processes_share_one_daily_allowance(tmp_path: Path) -> None:
    path = new_ledger(tmp_path / "ledger.sqlite3", cap=7_000_000)
    context = multiprocessing.get_context("spawn")
    results = context.Queue()
    workers = [
        context.Process(target=_process_worker, args=(str(path), 8, results)) for _ in range(2)
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=120)
        assert worker.exitcode == 0
    assert sum(results.get(timeout=10) for _ in range(16)) == 10
    assert BudgetLedger.open(path).daily_status().committed == 1_000_000
