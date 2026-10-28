"""The lifetime budget ledger (Phase A2, D-091 proposed): accounting, invariants, recovery,
integrity, concurrency and a genuinely content-free schema (S3). All amounts are synthetic
micro-USD; no real ledger is created and nothing reaches a network.

Worked-example steps refer to the plan, section 8.3; T4-* ids to section 10.2.
"""

import multiprocessing
import os
import random
import sqlite3
import stat
import threading
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from ai_assistant.budget import (
    ANOMALY_BITS,
    KEY_ALIASES,
    MAX_MICRO_USD,
    PER_MESSAGE_OVERHEAD,
    TEMPLATE_OVERHEAD,
    BudgetLedger,
    BudgetRefusedError,
    LedgerError,
    Reservation,
    reservation_for,
)
from ai_assistant.llm import ModelUsage, message_bytes
from tests.remote_fixtures import ENDPOINT, new_ledger

DAY = 86_400.0


@pytest.fixture(autouse=True)
def lifetime_cap_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """These D-091 tests exercise the lifetime cap with multi-dollar synthetic amounts in one
    day; the D-095 daily allowance is lifted for them and tested in test_budget_daily.py."""

    monkeypatch.setattr("ai_assistant.budget.DAILY_CAP_CEILING_MICRO_USD", MAX_MICRO_USD)


class Clock:
    def __init__(self, start: float = 1_800_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _ledger(
    tmp_path: Path, *, cap: int = 7_000_000, opening: int = 0, clock: Clock | None = None, **kw: Any
) -> BudgetLedger:
    clock = clock or Clock()
    path = new_ledger(tmp_path / "ledger.sqlite3", cap=cap, opening=opening, clock=clock)
    return BudgetLedger.open(path, clock=clock, **kw)


def _reservation(micro_usd: int, prompt: int = 11_152, output: int = 2_000) -> Reservation:
    return Reservation(prompt, output, micro_usd)


def _admit(ledger: BudgetLedger, micro_usd: int, *, in_flight: int = 4, lease: float = 150) -> str:
    return ledger.reserve(
        _reservation(micro_usd),
        endpoint_slug=ENDPOINT.slug,
        max_in_flight=in_flight,
        lease_seconds=lease,
    )


def _refusal(ledger: BudgetLedger, micro_usd: int, **kw: Any) -> str:
    with pytest.raises(BudgetRefusedError) as raised:
        _admit(ledger, micro_usd, **kw)
    assert raised.value.error_class == "budget_refused"
    assert raised.value.budget is not None
    return raised.value.budget.outcome


def _usage(cost: str, prompt: int = 3_000, completion: int = 450, **kw: Any) -> ModelUsage:
    return ModelUsage(prompt, completion, 300, 0, Decimal(cost), "gen-1761-test", **kw)


def _committed(ledger: BudgetLedger) -> int:
    return ledger.status().committed


def _rows(path: Path, sql: str, *params: Any) -> list[tuple[Any, ...]]:
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute(sql, params).fetchall()


def _assert_invariants(ledger: BudgetLedger, path: Path) -> None:
    """INV-2 (single counting, stored totals equal the rows) and INV-5 (B >= P_last)."""

    status = ledger.status()
    local, reserved = _rows(
        path,
        "SELECT COALESCE(SUM(CASE WHEN state != 'open' AND id > ? THEN charged_micro_usd END), 0),"
        " COALESCE(SUM(CASE WHEN state = 'open' THEN reserved_micro_usd END), 0) FROM calls",
        status.high_water,
    )[0]
    assert (local, reserved) == (status.local_charged, status.open_reserved)
    assert status.baseline >= status.last_provider_usage
    ledger.verify()


# --- the reservation (T4-01, T4-27 to T4-30) ---------------------------------------------


def test_the_reservation_bounds_bytes_envelope_and_template() -> None:
    messages = [{"role": "user", "content": "café 你好 \U0001f600"}]
    reservation = reservation_for(messages, ENDPOINT, 2000)

    content = message_bytes(messages)
    assert content == len(b"user") + len(messages[0]["content"].encode("utf-8"))
    assert reservation.prompt_bound_tokens == content + PER_MESSAGE_OVERHEAD + TEMPLATE_OVERHEAD
    # No documented max_tokens guarantee in this record: the documented maximum completion.
    assert reservation.output_bound_tokens == ENDPOINT.max_completion_tokens


def _sized(total_bytes: int, count: int) -> list[dict[str, str]]:
    """``count`` messages whose roles and contents add up to exactly ``total_bytes``."""

    messages = [{"role": "user", "content": ""} for _ in range(count)]
    remaining = total_bytes - 4 * count
    for message in messages:
        size = remaining // count
        message["content"] = "x" * size
    messages[0]["content"] += "x" * (total_bytes - message_bytes(messages))
    assert message_bytes(messages) == total_bytes
    return messages


@pytest.mark.parametrize(
    ("total", "count", "prompt", "completion", "guaranteed", "expected"),
    [
        (10_000, 8, "0.15", "0.60", True, 2_873),
        (10_000, 8, "0.15", "0.60", False, 72_452),
        (32_768, 10, "0.35", "0.95", False, 123_949),
    ],
)
def test_the_worked_reservations_reproduce_exactly(
    total: int, count: int, prompt: str, completion: str, guaranteed: bool, expected: int
) -> None:
    from dataclasses import replace

    endpoint = replace(
        ENDPOINT,
        prompt_price_per_m=Decimal(prompt),
        completion_price_per_m=Decimal(completion),
        max_tokens_includes_reasoning=guaranteed,
    )
    reservation = reservation_for(_sized(total, count), endpoint, 2000)

    assert reservation.micro_usd == expected
    assert reservation.prompt_bound_tokens == total + 16 * count + 1024


def test_the_reservation_takes_the_highest_listed_prices_and_the_request_price() -> None:
    from dataclasses import replace

    plain = reservation_for(_sized(10_000, 8), ENDPOINT, 2000).micro_usd
    endpoint = replace(
        ENDPOINT,
        cache_write_price_per_m=Decimal("0.30"),
        internal_reasoning_price_per_m=Decimal("1.20"),
        request_price=Decimal("0.0004"),
    )
    priced = reservation_for(_sized(10_000, 8), endpoint, 2000).micro_usd

    # 11,152 x 0.30 + 117,964 x 1.20 per million, plus 400 micro-USD per request.
    assert priced == 3346 + 141_557 + 400
    assert priced > plain


# --- admission, settlement and the worked accounting example (T4-17 to T4-25) ---------------


def test_the_worked_example_never_loses_or_double_counts(tmp_path: Path) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, cap=7_000_000, opening=3_000_000, clock=clock)
    path = tmp_path / "ledger.sqlite3"
    # Step 0: local closes of 2.000000 and an open obligation of 0.500000.
    for _ in range(2):
        ledger.settle(_admit(ledger, 1_000_000), usage=_usage("1.000000"), error_class=None)
    big = _admit(ledger, 500_000)
    assert _committed(ledger) == 5_500_000 and ledger.status().headroom == 1_500_000
    # Step 1: admit 0.075000.
    small = _admit(ledger, 75_000)
    assert _committed(ledger) == 5_575_000
    # Step 2: the 0.500000 obligation closes at 0.120000.
    budget = ledger.settle(big, usage=_usage("0.120000"), error_class=None)
    assert (budget.outcome, budget.charged_micro_usd) == ("settled", 120_000)
    assert _committed(ledger) == 5_195_000
    # Step 3: the 0.075000 call is cancelled: the obligation becomes a charge.
    ledger.settle(small, usage=None, error_class=None, cancelled=True)
    status = ledger.status()
    assert (status.local_charged, status.open_reserved, status.committed) == (
        2_195_000,
        0,
        5_195_000,
    )
    assert not status.breaker_open
    _assert_invariants(ledger, path)
    # Step 4a: reconcile with an over-count of 0.045000, kept.
    clock.advance(601)
    assert ledger.reconcile(5_150_000) == -45_000
    status = ledger.status()
    assert (status.baseline, status.local_charged, status.committed) == (5_195_000, 0, 5_195_000)
    _assert_invariants(ledger, path)


def test_reconcile_can_release_an_over_count_but_never_below_the_provider(tmp_path: Path) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, opening=3_000_000, clock=clock)
    ledger.settle(_admit(ledger, 2_195_000), usage=None, error_class=None, cancelled=True)
    clock.advance(601)

    assert ledger.reconcile(5_150_000, release=True) == -45_000  # step 4b
    status = ledger.status()
    assert status.baseline == status.last_provider_usage == 5_150_000
    events = _rows(
        tmp_path / "ledger.sqlite3", "SELECT event, amount_micro_usd FROM operator_events"
    )
    assert ("released", 45_000) in events
    _assert_invariants(ledger, tmp_path / "ledger.sqlite3")


def test_an_undercount_is_adopted_and_a_large_one_opens_the_breaker(tmp_path: Path) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, opening=3_000_000, clock=clock)
    ledger.settle(_admit(ledger, 2_195_000), usage=None, error_class=None, cancelled=True)
    clock.advance(601)

    assert ledger.reconcile(5_230_000) == 35_000  # within US$0.05: adopted, no breaker
    assert ledger.status().committed == 5_230_000 and not ledger.status().breaker_open
    clock.advance(601)
    assert ledger.reconcile(5_300_000) == 70_000  # step 4c: above the tolerance
    status = ledger.status()
    assert status.committed == 5_300_000
    assert status.breaker_open and status.breaker_code == "reconcile_drift"


def test_stale_or_regressed_reconciliation_is_refused(tmp_path: Path) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, opening=3_000_000, clock=clock)
    open_call = _admit(ledger, 100_000)
    with pytest.raises(LedgerError) as raised:
        ledger.reconcile(3_000_000)
    assert raised.value.code == "RECONCILE_REFUSED"  # a call is still open
    ledger.settle(open_call, usage=_usage("0.000720"), error_class=None)
    with pytest.raises(LedgerError):
        ledger.reconcile(3_000_720)  # inside the settle lag
    clock.advance(601)
    ledger.reconcile(3_000_720)
    clock.advance(601)
    with pytest.raises(LedgerError) as raised:
        ledger.reconcile(2_900_000)  # step 5: cumulative usage cannot fall
    assert raised.value.code == "RECONCILE_REFUSED"
    with pytest.raises(LedgerError):
        ledger.reconcile(2_999_999)  # also below the opening usage


def test_non_zero_opening_usage_counts_against_the_cap(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, cap=7_000_000, opening=6_900_000)

    assert _refusal(ledger, 100_001) == "refused_cap"
    rid = _admit(ledger, 100_000)  # exactly at the cap
    assert _committed(ledger) == 7_000_000
    assert _refusal(ledger, 1) == "refused_cap"
    ledger.settle(rid, usage=_usage("0.010000"), error_class=None)
    assert _committed(ledger) == 6_910_000


def test_the_cap_boundary_holds_across_a_restart(tmp_path: Path) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, cap=7_000_000, opening=6_925_000, clock=clock)
    reopened = BudgetLedger.open(tmp_path / "ledger.sqlite3", clock=clock)

    assert _refusal(reopened, 75_001) == "refused_cap"  # step 7
    _admit(reopened, 75_000)
    assert _committed(ledger) == 7_000_000


def test_a_cost_above_the_reservation_is_recorded_and_opens_the_breaker(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, cap=7_000_000, opening=6_900_000)
    rid = _admit(ledger, 50_000)
    budget = ledger.settle(rid, usage=_usage("0.080000"), error_class=None)  # step 8

    status = ledger.status()
    assert budget.charged_micro_usd == 80_000
    assert status.committed == 6_980_000 and status.breaker_code == "cost_above_reservation"
    assert _refusal(ledger, 1) == "refused_breaker"
    bits = _rows(tmp_path / "ledger.sqlite3", "SELECT anomaly_bits FROM calls")[0][0]
    assert bits & ANOMALY_BITS["cost_above_reservation"]


def test_the_overshoot_is_bounded_by_the_overrun(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, cap=7_000_000, opening=6_950_000)
    rid = _admit(ledger, 50_000)
    assert _committed(ledger) == 7_000_000
    ledger.settle(rid, usage=_usage("0.080000"), error_class=None)

    assert _committed(ledger) - 7_000_000 == 30_000  # INV-4: c - r
    assert ledger.status().breaker_open


def test_tokens_above_the_bound_open_the_breaker_even_when_the_cost_fits(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    rid = ledger.reserve(
        _reservation(72_452, prompt=1_000, output=2_000),
        endpoint_slug=ENDPOINT.slug,
        max_in_flight=1,
        lease_seconds=150,
    )
    ledger.settle(rid, usage=_usage("0.000720", prompt=1_001), error_class=None)

    assert ledger.status().breaker_code == "token_bound_exceeded"


def test_missing_usage_is_charged_in_full_and_stops_further_calls(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    rid = _admit(ledger, 72_452)
    budget = ledger.settle(rid, usage=ModelUsage(anomalies=("usage_missing",)), error_class=None)

    assert (budget.outcome, budget.charged_micro_usd) == ("unsettled", 72_452)
    assert ledger.status().breaker_code == "usage_missing"
    assert _refusal(ledger, 1) == "refused_breaker"


def test_a_cancelled_call_is_charged_in_full_without_opening_the_breaker(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    budget = ledger.settle(_admit(ledger, 72_452), usage=None, error_class=None, cancelled=True)

    assert (budget.outcome, budget.charged_micro_usd) == ("unsettled", 72_452)
    assert not ledger.status().breaker_open


@pytest.mark.parametrize(
    ("error_class", "opens"),
    [
        ("bad_request", True),
        ("auth", True),
        ("payment", True),
        ("payment_key_limit", True),
        ("forbidden", True),
        ("not_allowed", True),
        ("no_provider", True),
        ("timeout", False),
        ("rate_limited", False),
        ("upstream", False),
        ("transport", False),
        ("upstream_midstream", False),
        ("protocol", False),
    ],
)
def test_provider_errors_settle_conservatively_and_open_the_breaker_per_class(
    tmp_path: Path, error_class: str, opens: bool
) -> None:
    ledger = _ledger(tmp_path)
    budget = ledger.settle(_admit(ledger, 72_452), usage=None, error_class=error_class)

    assert budget.charged_micro_usd == 72_452
    assert ledger.status().breaker_open is opens


def test_an_error_with_reported_cost_is_charged_at_that_cost(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    budget = ledger.settle(
        _admit(ledger, 72_452), usage=_usage("0.000900"), error_class="content_filter"
    )

    assert (budget.outcome, budget.charged_micro_usd) == ("settled", 900)
    assert not ledger.status().breaker_open


def test_a_routing_anomaly_quarantines_the_call(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    usage = _usage("0.000720", anomalies=("model_mismatch",))
    ledger.settle(_admit(ledger, 72_452), usage=usage, error_class=None)

    assert _rows(tmp_path / "ledger.sqlite3", "SELECT verification FROM calls") == [
        ("quarantined",)
    ]
    assert ledger.status().breaker_code == "routing_anomaly"


def test_every_remote_call_is_unverified_in_this_build(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.settle(_admit(ledger, 72_452), usage=_usage("0.000720"), error_class=None)

    assert _rows(tmp_path / "ledger.sqlite3", "SELECT verification FROM calls") == [("unverified",)]


def test_a_call_is_closed_only_once(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    rid = _admit(ledger, 72_452)
    first = ledger.settle(rid, usage=_usage("0.000720"), error_class=None)
    second = ledger.settle(rid, usage=None, error_class=None, cancelled=True)

    assert first == second and ledger.status().local_charged == 720
    _assert_invariants(ledger, tmp_path / "ledger.sqlite3")


# --- recovery, persistence and lifetime (T4-09, T4-23) -------------------------------------


def test_a_crashed_call_is_abandoned_after_its_lease_and_opens_the_breaker(tmp_path: Path) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, clock=clock)
    _admit(ledger, 75_000, lease=150)
    clock.advance(151)  # the process that held it stopped (step 6)
    reopened = BudgetLedger.open(tmp_path / "ledger.sqlite3", clock=clock)

    status = reopened.status()
    assert (status.open_reserved, status.local_charged, status.committed) == (0, 75_000, 75_000)
    assert status.breaker_code == "abandoned_call"
    assert _rows(tmp_path / "ledger.sqlite3", "SELECT state FROM calls") == [("abandoned",)]


def test_a_live_lease_of_another_instance_is_left_alone(tmp_path: Path) -> None:
    clock = Clock()
    first = _ledger(tmp_path, clock=clock)
    rid = _admit(first, 75_000, lease=150)
    clock.advance(100)
    second = BudgetLedger.open(tmp_path / "ledger.sqlite3", clock=clock)

    assert second.status().open_calls == 1 and not second.status().breaker_open
    first.settle(rid, usage=_usage("0.000720"), error_class=None)
    assert second.status().local_charged == 720


def test_an_expired_lease_is_also_abandoned_at_the_next_admission(tmp_path: Path) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, clock=clock)
    _admit(ledger, 75_000, lease=150)
    clock.advance(151)

    assert _refusal(ledger, 1) == "refused_breaker"
    assert ledger.status().breaker_code == "abandoned_call"


def test_nothing_resets_with_time(tmp_path: Path) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, cap=1_000_000, clock=clock)
    ledger.settle(_admit(ledger, 900_000), usage=_usage("0.900000"), error_class=None)
    for days in (31, 365, 3650):
        clock.advance(days * DAY)
        reopened = BudgetLedger.open(tmp_path / "ledger.sqlite3", clock=clock)
        assert reopened.status().committed == 900_000
        assert _refusal(reopened, 100_001) == "refused_cap"


# --- creation, missing and corrupt ledgers (T4-10, T4-11, T4-24) -------------------------


def test_a_fresh_ledger_starts_at_the_keys_usage_and_never_overwrites(tmp_path: Path) -> None:
    path = tmp_path / "ledger.sqlite3"
    BudgetLedger.initialise(
        path, cap_micro_usd=7_000_000, opening_usage_micro_usd=5_300_000, key_alias="key-01"
    )
    assert BudgetLedger.open(path).status().committed == 5_300_000  # step 9

    with pytest.raises(LedgerError) as raised:
        BudgetLedger.initialise(
            path, cap_micro_usd=7_000_000, opening_usage_micro_usd=0, key_alias="key-01"
        )
    assert raised.value.code == "LEDGER_EXISTS"
    assert BudgetLedger.open(path).status().committed == 5_300_000


def test_a_missing_ledger_is_refused_and_never_created(tmp_path: Path) -> None:
    path = tmp_path / "nowhere" / "ledger.sqlite3"
    with pytest.raises(LedgerError) as raised:
        BudgetLedger.open(path)

    assert raised.value.code == "LEDGER_MISSING"
    assert not path.exists() and not path.parent.exists()


def _corrupt(path: Path, how: str) -> None:
    if how == "garbage":
        path.write_bytes(b"\x00garbage" * 4096)
    elif how == "truncated":
        data = path.read_bytes()
        path.write_bytes(data[: len(data) // 3])
    else:
        with closing(sqlite3.connect(path, isolation_level=None)) as connection:
            if how == "newer":
                connection.execute("PRAGMA user_version = 2")
            elif how == "dropped_table":
                connection.execute("DROP TABLE operator_events")
            elif how == "deleted_call":
                connection.execute("DELETE FROM calls")
            elif how == "lowered_total":
                connection.execute("UPDATE ledger_meta SET local_charged_micro_usd = 0")
            elif how == "extra_table":
                connection.execute("CREATE TABLE notes (text TEXT)")
            elif how == "baseline_below_provider":
                connection.execute(
                    "UPDATE ledger_meta SET last_provider_usage_micro_usd = baseline_micro_usd + 1"
                )


@pytest.mark.parametrize(
    ("how", "code"),
    [
        ("garbage", "LEDGER_CORRUPT"),
        ("truncated", "LEDGER_CORRUPT"),
        ("newer", "LEDGER_SCHEMA_UNSUPPORTED"),
        ("dropped_table", "LEDGER_SCHEMA_UNSUPPORTED"),
        ("extra_table", "LEDGER_SCHEMA_UNSUPPORTED"),
        ("deleted_call", "LEDGER_INCONSISTENT"),
        ("lowered_total", "LEDGER_INCONSISTENT"),
        ("baseline_below_provider", "LEDGER_INCONSISTENT"),
    ],
)
def test_a_corrupt_newer_or_tampered_ledger_is_refused_and_never_repaired(
    tmp_path: Path, how: str, code: str
) -> None:
    ledger = _ledger(tmp_path)
    ledger.settle(_admit(ledger, 72_452), usage=_usage("0.000720"), error_class=None)
    path = tmp_path / "ledger.sqlite3"
    _corrupt(path, how)
    before = path.read_bytes()

    with pytest.raises(LedgerError) as raised:
        BudgetLedger.open(path)
    assert raised.value.code in {code, "LEDGER_CORRUPT"}
    assert path.read_bytes() == before


def test_a_locked_ledger_refuses_as_busy(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, busy_timeout=0.1)
    holder = sqlite3.connect(tmp_path / "ledger.sqlite3", isolation_level=None)
    try:
        holder.execute("BEGIN EXCLUSIVE")
        assert _refusal(ledger, 1) == "refused_busy"
    finally:
        holder.execute("ROLLBACK")
        holder.close()


def test_a_read_only_ledger_fails_closed(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    path = tmp_path / "ledger.sqlite3"
    os.chmod(path, stat.S_IREAD)
    try:
        assert _refusal(ledger, 1) == "refused_ledger"
    finally:
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE)


# --- operator actions (cap, breaker) --------------------------------------------------------


def test_the_cap_can_be_lowered_but_raised_only_with_confirmation(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, cap=7_000_000)
    ledger.set_cap(5_000_000)
    for raise_kwargs in ({}, {"allow_raise": True}, {"allow_raise": True, "confirm": 7_000_001}):
        with pytest.raises(LedgerError) as raised:
            ledger.set_cap(7_000_000, **raise_kwargs)  # type: ignore[arg-type]
        assert raised.value.code == "CAP_RAISE_REFUSED"
    ledger.set_cap(7_000_000, allow_raise=True, confirm=7_000_000)

    assert ledger.status().cap == 7_000_000
    events = [
        row[0] for row in _rows(tmp_path / "ledger.sqlite3", "SELECT event FROM operator_events")
    ]
    assert events == ["init", "cap_lowered", "cap_raised"]


def test_the_breaker_resets_only_after_a_newer_reconcile_naming_its_code(tmp_path: Path) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, clock=clock)
    ledger.settle(_admit(ledger, 72_452), usage=None, error_class=None)  # usage missing
    for code in ("usage_missing", "provider_error"):
        with pytest.raises(LedgerError) as raised:
            ledger.reset_breaker(code)
        assert raised.value.code == "BREAKER_RESET_REFUSED"
    clock.advance(601)
    ledger.reconcile(72_452)
    with pytest.raises(LedgerError):
        ledger.reset_breaker("provider_error")
    ledger.reset_breaker("usage_missing")

    assert not ledger.status().breaker_open
    _admit(ledger, 1)


# --- content-free schema and key aliases (S3, T4-08) ---------------------------------------


def test_only_an_approved_opaque_key_alias_is_accepted(tmp_path: Path) -> None:
    for alias in ("CLM - AI Assistant", "Acme Pte Ltd", "maya-lim", "key-05", "", "case-123"):
        with pytest.raises(LedgerError) as raised:
            BudgetLedger.initialise(
                tmp_path / f"{len(alias)}.sqlite3",
                cap_micro_usd=1,
                opening_usage_micro_usd=0,
                key_alias=alias,
            )
        assert raised.value.code == "INVALID_INPUT"
        assert not alias or alias not in str(raised.value)
    assert KEY_ALIASES == ("key-01", "key-02", "key-03", "key-04")


def test_every_text_column_is_a_closed_code_or_an_opaque_identifier(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.settle(_admit(ledger, 72_452), usage=_usage("0.000720"), error_class=None)
    path = tmp_path / "ledger.sqlite3"
    text = "Maya Lim asked about GARDEN BUSINESS PTE LTD (201511222D)"
    probes = {
        "ledger_meta": ["ledger_id", "profile_id", "key_alias", "breaker_code"],
        "calls": [
            "reservation_id",
            "instance_id",
            "state",
            "requested_endpoint",
            "generation_ref",
            "verification",
            "error_class",
        ],
        "operator_events": ["event", "code"],
    }
    with closing(sqlite3.connect(path, isolation_level=None)) as connection:
        for table, columns in probes.items():
            declared = {row[1]: row[2] for row in connection.execute(f"PRAGMA table_info({table})")}
            assert set(declared.values()) <= {"INTEGER", "TEXT"}
            assert {name for name, kind in declared.items() if kind == "TEXT"} == set(columns)
            for column in columns:
                with pytest.raises(sqlite3.IntegrityError):
                    connection.execute(f"UPDATE {table} SET {column} = ?", (text,))
        for table, column in [("calls", "prompt_tokens"), ("ledger_meta", "cap_micro_usd")]:
            with pytest.raises(sqlite3.IntegrityError):  # STRICT tables refuse text in numbers
                connection.execute(f"UPDATE {table} SET {column} = ?", (text,))
    assert text.encode() not in path.read_bytes()


def test_the_ledger_never_stores_a_key_or_key_hash(tmp_path: Path) -> None:
    from tests.remote_fixtures import SENTINEL_KEY

    ledger = _ledger(tmp_path)
    ledger.settle(_admit(ledger, 72_452), usage=_usage("0.000720"), error_class=None)
    data = (tmp_path / "ledger.sqlite3").read_bytes()

    assert SENTINEL_KEY.encode() not in data
    import hashlib

    assert hashlib.sha256(SENTINEL_KEY.encode()).hexdigest().encode() not in data


# --- concurrency (T4-03) ------------------------------------------------------------------


def test_concurrent_threads_never_exceed_the_cap(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, cap=1_000_000, busy_timeout=5.0)
    admitted: list[str] = []
    lock = threading.Lock()

    def worker() -> None:
        for _ in range(10):
            try:
                rid = _admit(ledger, 100_000, in_flight=100)
            except BudgetRefusedError:
                continue
            with lock:
                admitted.append(rid)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(admitted) == 10 and _committed(ledger) == 1_000_000
    _assert_invariants(ledger, tmp_path / "ledger.sqlite3")


def test_the_in_flight_limit_counts_open_calls_in_the_ledger(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    other = BudgetLedger.open(tmp_path / "ledger.sqlite3")
    rid = _admit(ledger, 1_000, in_flight=1)

    assert _refusal(other, 1_000, in_flight=1) == "refused_busy"
    ledger.settle(rid, usage=_usage("0.000720"), error_class=None)
    _admit(other, 1_000, in_flight=1)


def _process_worker(path: str, count: int, results: Any) -> None:
    ledger = BudgetLedger.open(Path(path), busy_timeout=10.0)
    for _ in range(count):
        try:
            ledger.reserve(
                Reservation(10, 10, 100_000),
                endpoint_slug="fictional-provider/fp8",
                max_in_flight=1000,
                lease_seconds=3600,
            )
            results.put(1)
        except BudgetRefusedError:
            results.put(0)


def test_two_processes_on_one_file_never_exceed_the_cap(tmp_path: Path) -> None:
    # Below the D-095 daily allowance, which the spawned processes keep (no monkeypatch there).
    path = new_ledger(tmp_path / "ledger.sqlite3", cap=900_000)
    context = multiprocessing.get_context("spawn")
    results = context.Queue()
    workers = [
        context.Process(target=_process_worker, args=(str(path), 12, results)) for _ in range(2)
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=120)
        assert worker.exitcode == 0
    outcomes = [results.get(timeout=10) for _ in range(24)]

    assert sum(outcomes) == 9
    assert BudgetLedger.open(path).status().committed == 900_000


# --- randomised invariants (T4-26, T4-32) --------------------------------------------------


@dataclass
class _Shadow:
    provider: int
    baseline: int


def _random_sequence(path: Path, seed: int) -> None:
    rng = random.Random(seed)
    clock = Clock()
    cap = rng.randrange(200_000, 2_000_000)
    opening = rng.randrange(0, cap // 2)
    BudgetLedger.initialise(
        path, cap_micro_usd=cap, opening_usage_micro_usd=opening, key_alias="key-02", clock=clock
    )
    ledger = BudgetLedger.open(path, clock=clock, durable=False)
    open_calls: list[tuple[str, int]] = []
    shadow = _Shadow(provider=opening, baseline=opening)
    for _ in range(rng.randrange(6, 14)):
        action = rng.random()
        before = ledger.status()
        if action < 0.4:
            amount = rng.randrange(1, 300_000)
            try:
                rid = _admit(ledger, amount, in_flight=3, lease=150)
                open_calls.append((rid, amount))
                assert ledger.status().committed <= ledger.status().cap  # INV-3
            except BudgetRefusedError:
                pass
        elif action < 0.65 and open_calls:
            rid, amount = open_calls.pop(rng.randrange(len(open_calls)))
            cost = Decimal(rng.randrange(0, int(amount * 1.2) + 1)) / Decimal(1_000_000)
            ledger.settle(rid, usage=_usage(str(cost)), error_class=None)
        elif action < 0.75 and open_calls:
            rid, _ = open_calls.pop()
            ledger.settle(rid, usage=None, error_class=None, cancelled=True)
        elif action < 0.8 and open_calls:
            clock.advance(151)  # a crash: the next open abandons every expired lease
            ledger = BudgetLedger.open(path, clock=clock, durable=False)
            open_calls.clear()
        elif action < 0.92 and not open_calls:
            clock.advance(601)
            estimate = before.baseline + before.local_charged
            provider = max(shadow.provider, estimate + rng.randrange(-80_000, 80_000))
            release = rng.random() < 0.5
            drift = ledger.reconcile(provider, release=release)
            after = ledger.status()
            assert drift == provider - estimate
            assert after.baseline >= provider  # INV-5
            assert after.baseline >= shadow.baseline or release  # INV-6
            shadow = _Shadow(provider=provider, baseline=after.baseline)
            if after.breaker_code is not None:
                try:  # allowed only after a reconcile newer than the breaker
                    ledger.reset_breaker(after.breaker_code)
                except LedgerError as refused:
                    assert refused.code == "BREAKER_RESET_REFUSED"
        else:
            clock.advance(rng.choice([1.0, 31 * DAY, 400 * DAY]))  # INV-7: time changes nothing
            assert ledger.status() == before
        _assert_invariants(ledger, path)


def test_random_operation_sequences_keep_the_invariants(tmp_path: Path) -> None:
    for seed in range(1000):
        _random_sequence(tmp_path / f"ledger-{seed}.sqlite3", seed)


def test_the_ledger_has_no_way_to_set_the_baseline_directly() -> None:
    public = {name for name in dir(BudgetLedger) if not name.startswith("_")}

    assert public == {
        "initialise",
        "open",
        "verify",
        "status",
        "recover",
        "open_breaker",
        "reserve",
        "settle",
        "set_cap",
        "reconcile",
        "reset_breaker",
        # Phase B (D-092, proposed): content-free reads and the one-way verification mark.
        "closed_calls_after",
        "last_call_id",
        "record_verification",
        "unverified_closed_calls",
        # D-095: today's allowance, read-only.
        "daily_status",
    }
    assert MAX_MICRO_USD == 10**12


def test_amount_inputs_must_be_micro_usd_counts(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    bad: list[Callable[[], Any]] = [
        lambda: ledger.set_cap(-1),
        lambda: ledger.set_cap(1.5),  # type: ignore[arg-type]
        lambda: ledger.reconcile(-1),
        lambda: BudgetLedger.initialise(
            tmp_path / "x.sqlite3", cap_micro_usd=-1, opening_usage_micro_usd=0, key_alias="key-01"
        ),
    ]
    for call in bad:
        with pytest.raises(LedgerError) as raised:
            call()
        assert raised.value.code == "INVALID_INPUT"
