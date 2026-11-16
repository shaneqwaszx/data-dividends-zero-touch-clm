"""D-134 (proposed): the hard GPT-OSS daily ceiling, enforced in the ledger's own admission
transaction: settled spend today plus every open reservation plus this call's worst case (its
attempts included) never exceeds the registered ceiling, whatever the configured daily cap is.
Synthetic micro-USD amounts only; no real ledger, no provider and no network."""

import multiprocessing
import threading
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from ai_assistant import budget
from ai_assistant.anthropic_profiles import LEDGER_PROFILE_ID as ANTHROPIC_LEDGER_PROFILE_ID
from ai_assistant.budget import (
    GPT_OSS_DAILY_CEILING_MICRO_USD,
    MAX_ATTEMPTS,
    BudgetLedger,
    BudgetRefusedError,
    LedgerError,
    Reservation,
    daily_ceiling,
    register_daily_ceiling,
)
from ai_assistant.llm import ModelUsage
from ai_assistant.model_profiles import OPENROUTER_PROFILE_ID
from tests.remote_fixtures import ENDPOINT, new_ledger

CEILING = GPT_OSS_DAILY_CEILING_MICRO_USD
# A configured daily cap above the ceiling (the D-118 environment default, an HR value).
ABOVE = 5_000_000
# Singapore midnight is 16:00 UTC.
NOON_SGT = datetime(2027, 1, 15, 4, 0, tzinfo=UTC).timestamp()
BEFORE_MIDNIGHT_SGT = datetime(2027, 1, 15, 15, 59, 30, tzinfo=UTC).timestamp()
AFTER_MIDNIGHT_SGT = datetime(2027, 1, 15, 16, 0, 1, tzinfo=UTC).timestamp()


class Clock:
    def __init__(self, start: float = NOON_SGT) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


def _ledger(tmp_path: Path, clock: Clock, *, cap: int = 50_000_000) -> BudgetLedger:
    path = new_ledger(tmp_path / "ledger.sqlite3", cap=cap, clock=clock)
    return BudgetLedger.open(path, clock=clock)


def _admit(
    ledger: BudgetLedger,
    micro: int,
    daily: int | None = ABOVE,
    *,
    attempts: int = 1,
    lease: float = 3600,
) -> str:
    return ledger.reserve(
        Reservation(1_000, 1_000, micro),
        endpoint_slug=ENDPOINT.slug,
        max_in_flight=1000,
        lease_seconds=lease,
        daily_cap_micro_usd=daily,
        attempts=attempts,
    )


def _refusal(ledger: BudgetLedger, micro: int, daily: int | None = ABOVE, **options: Any) -> str:
    with pytest.raises(BudgetRefusedError) as raised:
        _admit(ledger, micro, daily, **options)
    assert raised.value.budget is not None
    return raised.value.budget.outcome


def _usage(cost: str) -> ModelUsage:
    return ModelUsage(
        prompt_tokens=10, completion_tokens=10, cost=Decimal(cost), generation_ref="gen-1"
    )


def _new_session(ledger: BudgetLedger) -> None:
    # D-118: a paid session holds US$5.00 at most; these tests are about the day, not the
    # session, so HR's explicit new session is started whenever the last call has closed.
    current = ledger.session()
    ledger.start_session(
        budget.SESSION_MAX_MICRO_USD,
        expected_session_id=None if current is None else current.session_id,
    )


# --- the registration ------------------------------------------------------------------------


def test_the_ceiling_is_three_dollars_and_nothing_is_registered_by_default() -> None:
    assert CEILING == 3_000_000
    assert daily_ceiling(OPENROUTER_PROFILE_ID) == CEILING  # standing, nothing registered
    assert daily_ceiling(ANTHROPIC_LEDGER_PROFILE_ID) is None


@pytest.mark.parametrize("value", [0, -1, CEILING + 1, 10**12, True, 1.5, "3000000", None])
def test_a_ceiling_outside_one_micro_usd_to_three_dollars_is_refused(value: Any) -> None:
    with pytest.raises(LedgerError) as raised:
        register_daily_ceiling(value)
    assert raised.value.code == "INVALID_INPUT"
    assert daily_ceiling(OPENROUTER_PROFILE_ID) == CEILING  # standing, nothing registered


def test_the_ceiling_is_registered_once_and_never_replaced_or_raised() -> None:
    register_daily_ceiling(2_000_000)
    register_daily_ceiling(2_000_000)  # the same value again is harmless
    for other in (CEILING, 1_999_999, 1):
        with pytest.raises(LedgerError) as raised:
            register_daily_ceiling(other)
        assert raised.value.code == "CEILING_REGISTERED"
    assert daily_ceiling(OPENROUTER_PROFILE_ID) == 2_000_000
    assert daily_ceiling(ANTHROPIC_LEDGER_PROFILE_ID) is None


def test_without_a_registered_ceiling_the_standing_ceiling_still_applies(tmp_path: Path) -> None:
    # Owner directive 2026-11-15: on a development machine too, a configured US$5.00 day
    # admits at most US$3.00 (nothing registered; the standing ceiling applies).
    ledger = _ledger(tmp_path, Clock())
    _admit(ledger, 2_900_000)
    status = ledger.daily_status(ABOVE)
    assert (status.cap, status.ceiling, status.remaining) == (CEILING, CEILING, 100_000)
    assert _refusal(ledger, 100_001) == "refused_daily_cap"
    _admit(ledger, 100_000)


# --- the arithmetic at the boundary ----------------------------------------------------------


def test_spent_plus_open_plus_this_call_stays_within_the_ceiling_exactly(tmp_path: Path) -> None:
    register_daily_ceiling(CEILING)
    ledger = _ledger(tmp_path, Clock())
    first = _admit(ledger, 1_200_000)
    ledger.settle(first, usage=_usage("1.000000"), error_class=None)  # charged 1,000,000
    _admit(ledger, 1_500_000)  # open: counts at its whole reservation
    status = ledger.daily_status(ABOVE)
    assert (status.cap, status.ceiling) == (CEILING, CEILING)
    assert (status.settled_today, status.open_reserved, status.remaining) == (
        1_000_000,
        1_500_000,
        500_000,
    )
    # 1,000,000 + 1,500,000 + 500,001 = 3,000,001: one micro-USD too much.
    assert _refusal(ledger, 500_001) == "refused_daily_cap"
    # 1,000,000 + 1,500,000 + 500,000 = 3,000,000: exactly the ceiling.
    _admit(ledger, 500_000)
    assert ledger.daily_status(ABOVE).remaining == 0
    assert _refusal(ledger, 1) == "refused_daily_cap"
    # A refusal reserves nothing.
    assert ledger.status().committed == 3_000_000


@pytest.mark.parametrize("configured", [ABOVE, 10**12, CEILING, None])
def test_no_configured_daily_cap_admits_more_than_the_ceiling(
    tmp_path: Path, configured: int | None
) -> None:
    register_daily_ceiling(CEILING)
    ledger = _ledger(tmp_path, Clock())
    limit = min(CEILING, budget.daily_cap_for(configured) or 0)
    _admit(ledger, limit, configured)
    assert _refusal(ledger, 1, configured) == "refused_daily_cap"


def test_a_lower_configured_cap_still_wins(tmp_path: Path) -> None:
    register_daily_ceiling(CEILING)
    ledger = _ledger(tmp_path, Clock())
    _admit(ledger, 250_000, 250_000)
    assert _refusal(ledger, 1, 250_000) == "refused_daily_cap"
    status = ledger.daily_status(250_000)
    assert (status.cap, status.ceiling, status.remaining) == (250_000, CEILING, 0)


def test_a_lower_registered_ceiling_is_the_limit(tmp_path: Path) -> None:
    register_daily_ceiling(700_000)
    ledger = _ledger(tmp_path, Clock())
    _admit(ledger, 700_000)
    assert _refusal(ledger, 1) == "refused_daily_cap"
    assert ledger.daily_status(ABOVE).cap == 700_000


# --- retries ---------------------------------------------------------------------------------


def test_a_call_is_admitted_only_if_every_attempt_fits(tmp_path: Path) -> None:
    register_daily_ceiling(CEILING)
    ledger = _ledger(tmp_path, Clock())
    _admit(ledger, 900_000)  # 2,100,000 left today
    # Three attempts of 700,001 need 2,100,003; one attempt would fit.
    assert _refusal(ledger, 700_001, attempts=3) == "refused_daily_cap"
    # Three attempts of 700,000 need exactly 2,100,000. The row reserves one attempt; each
    # further attempt reserves again, atomically, when it is made.
    _admit(ledger, 700_000, attempts=3)
    assert ledger.daily_status(ABOVE).open_reserved == 1_600_000
    _admit(ledger, 700_000)
    _admit(ledger, 700_000)
    assert _refusal(ledger, 1) == "refused_daily_cap"


@pytest.mark.parametrize("attempts", [0, -1, MAX_ATTEMPTS + 1, True, 1.0, "2"])
def test_an_attempt_count_that_is_not_a_small_whole_number_is_refused(
    tmp_path: Path, attempts: Any
) -> None:
    ledger = _ledger(tmp_path, Clock())
    assert _refusal(ledger, 10, attempts=attempts) == "refused_reservation"
    assert ledger.status().committed == 0


def test_attempts_also_count_against_the_lifetime_cap(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, Clock(), cap=1_000_000)
    assert _refusal(ledger, 500_001, attempts=2) == "refused_cap"
    _admit(ledger, 500_000, attempts=2)


# --- uncertain outcomes ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("usage", "error_class", "cancelled", "state"),
    [
        (None, "timeout", False, "unsettled"),  # the provider never answered
        (None, None, True, "unsettled"),  # the caller went away mid-answer
        (None, None, False, "unsettled"),  # an answer without usage
    ],
)
def test_an_uncertain_outcome_is_charged_its_whole_reservation(
    tmp_path: Path, usage: Any, error_class: str | None, cancelled: bool, state: str
) -> None:
    register_daily_ceiling(CEILING)
    ledger = _ledger(tmp_path, Clock())
    held = _admit(ledger, 2_999_000)
    closed = ledger.settle(held, usage=usage, error_class=error_class, cancelled=cancelled)
    assert (closed.outcome, closed.charged_micro_usd) == (state, 2_999_000)
    status = ledger.daily_status(ABOVE)
    assert (status.settled_today, status.open_reserved, status.remaining) == (2_999_000, 0, 1_000)


def test_a_cost_above_the_reservation_is_charged_and_stops_the_ledger(tmp_path: Path) -> None:
    register_daily_ceiling(CEILING)
    ledger = _ledger(tmp_path, Clock())
    held = _admit(ledger, 1_000_000)
    ledger.settle(held, usage=_usage("1.400000"), error_class=None)
    assert ledger.daily_status(ABOVE).settled_today == 1_400_000
    assert ledger.status().breaker_code == "cost_above_reservation"
    assert _refusal(ledger, 1) == "refused_breaker"


# --- restart ---------------------------------------------------------------------------------


def test_a_restart_keeps_todays_spend_and_every_open_reservation(tmp_path: Path) -> None:
    register_daily_ceiling(CEILING)
    clock = Clock()
    before = _ledger(tmp_path, clock)
    done = _admit(before, 1_000_000)
    before.settle(done, usage=_usage("0.800000"), error_class=None)
    _admit(before, 1_200_000, lease=600)  # still open when the process stops

    # A new process: another ledger object on the same file (the ceiling is registered again
    # at start-up; here it is the same registration).
    clock.now += 60
    after = BudgetLedger.open(tmp_path / "ledger.sqlite3", clock=clock)
    assert after.instance_id != before.instance_id
    status = after.daily_status(ABOVE)
    assert (status.settled_today, status.open_reserved, status.open_calls) == (
        800_000,
        1_200_000,
        1,
    )
    assert _refusal(after, 1_000_001) == "refused_daily_cap"
    _admit(after, 1_000_000)
    assert after.daily_status(ABOVE).remaining == 0


def test_a_call_left_open_by_a_stopped_process_is_charged_in_full(tmp_path: Path) -> None:
    register_daily_ceiling(CEILING)
    clock = Clock()
    before = _ledger(tmp_path, clock)
    _admit(before, 1_200_000, lease=120)
    clock.now += 600  # its lease has run out
    after = BudgetLedger.open(tmp_path / "ledger.sqlite3", clock=clock)
    status = after.daily_status(ABOVE)
    assert (status.settled_today, status.open_reserved) == (1_200_000, 0)
    assert after.status().breaker_code == "abandoned_call"
    assert _refusal(after, 1) == "refused_breaker"  # an operator or HR decides, never a retry


# --- concurrency -----------------------------------------------------------------------------


def test_concurrent_requests_in_one_process_never_exceed_the_ceiling(tmp_path: Path) -> None:
    register_daily_ceiling(CEILING)
    path = new_ledger(tmp_path / "ledger.sqlite3", cap=50_000_000)
    admitted: list[str] = []
    refused: list[str] = []
    lock = threading.Lock()
    start = threading.Barrier(24)

    def worker() -> None:
        ledger = BudgetLedger(path, busy_timeout=60)
        start.wait()
        try:
            held = _admit(ledger, 250_000)
        except BudgetRefusedError as error:
            assert error.budget is not None
            with lock:
                refused.append(error.budget.outcome)
            return
        with lock:
            admitted.append(held)

    threads = [threading.Thread(target=worker) for _ in range(24)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(120)
        assert not thread.is_alive()
    assert len(admitted) == 12 and len(set(admitted)) == 12
    assert refused == ["refused_daily_cap"] * 12
    status = BudgetLedger.open(path).daily_status(ABOVE)
    assert (status.open_reserved, status.remaining) == (CEILING, 0)


def _process_worker(path: str, tries: int, results: Any) -> None:
    register_daily_ceiling(CEILING)  # as each process does at start-up
    ledger = BudgetLedger(Path(path), busy_timeout=60)
    for _ in range(tries):
        try:
            _admit(ledger, 250_000)
            results.put(1)
        except BudgetRefusedError:
            results.put(0)


def test_two_processes_share_one_ceiling(tmp_path: Path) -> None:
    path = new_ledger(tmp_path / "ledger.sqlite3", cap=50_000_000)
    context = multiprocessing.get_context("spawn")
    results = context.Queue()
    workers = [
        context.Process(target=_process_worker, args=(str(path), 10, results)) for _ in range(2)
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=120)
        assert worker.exitcode == 0
    assert sum(results.get(timeout=10) for _ in range(20)) == 12
    register_daily_ceiling(CEILING)
    assert BudgetLedger.open(path).daily_status(ABOVE).committed == CEILING


# --- the day -----------------------------------------------------------------------------------


def test_the_day_turns_at_singapore_midnight_and_nothing_is_erased(tmp_path: Path) -> None:
    register_daily_ceiling(CEILING)
    clock = Clock(BEFORE_MIDNIGHT_SGT)
    ledger = _ledger(tmp_path, clock)
    for cost in ("1.500000", "1.400000"):
        ledger.settle(_admit(ledger, 1_500_000), usage=_usage(cost), error_class=None)
    assert _refusal(ledger, 100_001) == "refused_daily_cap"
    reset_at = ledger.daily_status(ABOVE).next_reset_at
    assert datetime.fromtimestamp(reset_at / 1000, UTC) == datetime(2027, 1, 15, 16, tzinfo=UTC)

    clock.now = AFTER_MIDNIGHT_SGT
    _new_session(ledger)
    status = ledger.daily_status(ABOVE)
    assert (status.settled_today, status.remaining) == (0, CEILING)
    assert status.day_started_at == reset_at
    _admit(ledger, CEILING)
    assert _refusal(ledger, 1) == "refused_daily_cap"
    # Yesterday's calls are all still in the ledger's lifetime total.
    assert ledger.status().committed == 2_900_000 + CEILING


def test_a_call_still_open_from_yesterday_counts_today(tmp_path: Path) -> None:
    register_daily_ceiling(CEILING)
    clock = Clock(BEFORE_MIDNIGHT_SGT)
    ledger = _ledger(tmp_path, clock)
    _admit(ledger, 1_000_000)  # stays open across midnight
    clock.now = AFTER_MIDNIGHT_SGT
    assert ledger.daily_status(ABOVE).open_reserved == 1_000_000
    assert _refusal(ledger, 2_000_001) == "refused_daily_cap"
    _admit(ledger, 2_000_000)


# --- Claude is untouched ---------------------------------------------------------------------


def test_the_ceiling_never_applies_to_the_anthropic_ledger(tmp_path: Path) -> None:
    register_daily_ceiling(1)  # the strictest GPT-OSS ceiling there is
    clock = Clock()
    path = tmp_path / "anthropic.sqlite3"
    BudgetLedger.initialise(
        path,
        cap_micro_usd=30_000_000,
        opening_usage_micro_usd=0,
        key_alias="key-01",
        profile_id=ANTHROPIC_LEDGER_PROFILE_ID,
        clock=clock,
    )
    ledger = BudgetLedger.open(path, clock=clock)
    held = ledger.reserve(
        Reservation(1_000, 1_000, 4_000_000),
        endpoint_slug="anthropic",
        max_in_flight=1,
        lease_seconds=600,
        daily_cap_micro_usd=5_000_000,
        profile_id=ANTHROPIC_LEDGER_PROFILE_ID,
    )
    assert held
    status = ledger.daily_status(5_000_000)
    assert (status.cap, status.ceiling, status.remaining) == (5_000_000, None, 1_000_000)
