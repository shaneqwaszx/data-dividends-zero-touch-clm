"""D-110 (B1 Phase B): HR reconciliation of the Claude ledger.

Disposable ledgers and state databases only (tmp_path). Covers the preview gates G1 to G10,
freshness (F8), the in-transaction compare-and-set (F4), the cross-process lock and intent
marker (F5), the run state machine (F6), resolve's four outcomes (F7, Q12 as the owner
clarified it), owner close, the operator's script, the routes, and the headroom proof (F9).
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import sqlite3
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from ai_assistant import anthropic_runtime
from ai_assistant import claude_reconciliation as rc
from ai_assistant.anthropic_profiles import LEDGER_PROFILE_ID
from ai_assistant.budget import BudgetLedger, LedgerError, Reservation
from ai_assistant.llm import ModelUsage
from ai_assistant.model_admin_store import ModelAdminStore

SLUG = "anthropic/claude-sonnet-5-5"
HERE = Path(__file__).resolve().parent.parent


class Clock:
    def __init__(self) -> None:
        self.now = time.time()
        self.mono = 1000.0

    def __call__(self) -> float:
        return self.now

    def monotonic(self) -> float:
        return self.mono

    def advance(self, seconds: float) -> None:
        self.now += seconds
        self.mono += seconds


class World:
    def __init__(self, tmp_path: Path, *, prerequisite: bool = True, lag: float = 600) -> None:
        self.clock = Clock()
        self.ledger_path = tmp_path / "budget" / "anthropic.sqlite3"
        self.ledger_path.parent.mkdir(parents=True)
        ledger = BudgetLedger.initialise(
            self.ledger_path,
            cap_micro_usd=25_000_000,
            opening_usage_micro_usd=20_000,
            key_alias="key-02",
            profile_id=LEDGER_PROFILE_ID,
        )
        ledger.reconcile(20_000, settle_lag_seconds=0)
        self.state_path = tmp_path / "models" / "model_admin.sqlite3"
        ModelAdminStore(self.state_path)  # the service's database (events table)
        self.runs = rc.Runs(self.state_path, clock=self.clock)
        if prerequisite:
            self.runs.record_prerequisite("owner", "launchers retired 2026-10-31")
        self.lag = lag
        self.recon = rc.Reconciler(
            lambda: self.ledger_path,
            self.runs,
            lambda: self.lag,
            clock=self.clock,
            monotonic=self.clock.monotonic,
        )

    def ledger(self) -> BudgetLedger:
        return BudgetLedger(self.ledger_path)

    def call(self, cost: str, closed_ago: float = 7200, verify: bool = True) -> None:
        at = self.clock.now - closed_ago
        past = BudgetLedger(self.ledger_path, clock=lambda: at)
        reservation = past.reserve(
            Reservation(100, 100, 100_000),
            endpoint_slug=SLUG,
            max_in_flight=1,
            lease_seconds=60,
            profile_id=LEDGER_PROFILE_ID,
        )
        past.settle(
            reservation,
            usage=ModelUsage(prompt_tokens=10, completion_tokens=10, cost=Decimal(cost)),
            error_class=None,
        )
        if verify:
            anthropic_runtime.verify_calls(self.ledger())

    def reading(
        self,
        usage: int,
        *,
        as_of_ago: float = 60,
        viewed_ago: float = 30,
        kind: str = rc.KIND_REFRESHED,
        scopes: tuple[bool, bool, bool] = (True, True, True),
    ) -> rc.Reading:
        viewed = int((self.clock.now - viewed_ago) * 1000)
        as_of = viewed if kind == rc.KIND_VIEWED else int((self.clock.now - as_of_ago) * 1000)
        return rc.Reading(usage, as_of, kind, viewed, *scopes)

    def preview(self, usage: int, actor: str = "hr-admin", **kwargs: Any) -> dict[str, Any]:
        return self.recon.preview(self.reading(usage, **kwargs), actor=actor, session="s1")

    def apply(self, preview: dict[str, Any], *, confirm: int | None = None) -> dict[str, Any]:
        usage = preview["inputs"]["usage_micro_usd"]
        return self.recon.apply(
            preview["preview_id"],
            confirm_usage_micro_usd=usage if confirm is None else confirm,
            scopes=(True, True, True),
            actor="hr-admin",
            role="HR",
            session="s1",
        )

    def resolve(self, run_id: str) -> dict[str, Any]:
        return self.recon.resolve(run_id, actor="hr-admin", role="HR")

    def past_bound(self) -> None:
        self.clock.advance(rc.APPLY_SECONDS + rc.BUSY_SECONDS + rc.RESOLVE_GRACE_SECONDS + 1)

    def marker(self) -> dict[str, Any] | None:
        return rc.read_marker(self.ledger_path)

    def only_run(self) -> dict[str, Any]:
        runs = self.runs.all()
        assert len(runs) == 1, runs
        return runs[0]


def _refused(code: str) -> Any:
    return pytest.raises(rc.ReconcileRefused, match=f"^{code}$")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- happy paths and outcomes ------------------------------------------------------------


def test_a_matching_reading_is_applied_and_the_windows_renew(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.call("0.011")
    world.clock.advance(1)
    before = world.ledger().status()
    preview = world.preview(31_000)
    assert preview["drift_micro_usd"] == 0
    assert preview["breaker_opens"] is False
    result = world.apply(preview)
    assert result["outcome"] == "applied"
    run = world.only_run()
    assert run["status"] == "applied"
    assert run["attribution_basis"] == "apply_returned"
    status = world.ledger().status()
    assert status.last_provider_usage == 31_000
    assert status.local_charged == 0
    assert status.cap == before.cap  # F9/F10: no limit changes
    assert world.ledger().last_reconciled_ms() == int(world.clock.now * 1000)
    assert world.marker() is None
    with sqlite3.connect(world.ledger_path) as db:
        last = db.execute("SELECT id, event, amount_micro_usd FROM operator_events").fetchall()
    assert last[-1][1:] == ("reconciled", 31_000)
    assert run["event_id"] == last[-1][0]


def test_an_undercount_above_tolerance_opens_the_breaker_and_needs_a_second_reconcile(
    tmp_path: Path,
) -> None:
    world = World(tmp_path)
    preview = world.preview(120_000)  # 100,000 more than the ledger estimated
    assert preview["breaker_opens"] is True
    world.apply(preview)
    status = world.ledger().status()
    assert status.breaker_code == "reconcile_drift"
    assert status.baseline == 120_000
    # HR never resets the breaker, and the owner needs a reconcile after it opened.
    with pytest.raises(LedgerError, match="reconcile before resetting"):
        world.ledger().reset_breaker("reconcile_drift")


def test_an_overcount_within_tolerance_is_kept(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.call("0.03")  # ledger charged 30,000
    preview = world.preview(30_000)  # Console shows 10,000 more, ledger 30,000: 20,000 kept
    assert preview["drift_micro_usd"] == -20_000
    world.apply(preview)
    status = world.ledger().status()
    assert status.baseline == 50_000  # the higher estimate is kept (no release)
    assert status.last_provider_usage == 30_000


def test_headroom_never_increases_from_a_preview_expectation() -> None:
    rng = random.Random(110)
    for _ in range(2000):
        baseline = rng.randint(0, 5_000_000)
        last = rng.randint(0, baseline)
        charged = rng.randint(0, 2_000_000)
        state = {
            "meta": {
                "baseline_micro_usd": baseline,
                "local_charged_micro_usd": charged,
                "last_provider_usage_micro_usd": last,
                "baseline_high_water_call_id": 3,
                "breaker_open": 0,
                "breaker_code": None,
                "last_reconciled_at": 1,
                "breaker_opened_at": None,
                "cap_micro_usd": 25_000_000,
            },
            "max_call_id": 5,
        }
        usage = rng.randint(last, last + 3_000_000)
        after = rc.expected_after(state, usage)
        assert after["baseline_micro_usd"] + after["local_charged_micro_usd"] >= baseline + charged
        assert after["cap_micro_usd"] == 25_000_000


# --- preview gates (G1 to G10) and the prerequisite ---------------------------------------


def test_no_prerequisite_refuses(tmp_path: Path) -> None:
    world = World(tmp_path, prerequisite=False)
    with _refused("PREREQUISITE_MISSING"):
        world.preview(20_000)


def test_scope_confirmations_are_required(tmp_path: Path) -> None:
    world = World(tmp_path)
    with _refused("SCOPE_UNCONFIRMED"):
        world.preview(20_000, scopes=(True, False, True))


def test_an_open_breaker_refuses(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.ledger().open_breaker("usage_missing")
    with _refused("BREAKER_OPEN"):
        world.preview(20_000)


def test_an_open_call_refuses_and_is_never_recovered(tmp_path: Path) -> None:
    world = World(tmp_path)
    BudgetLedger(world.ledger_path, clock=lambda: time.time() - 3600).reserve(
        Reservation(10, 10, 1_000),
        endpoint_slug=SLUG,
        max_in_flight=1,
        lease_seconds=1,
        profile_id=LEDGER_PROFILE_ID,
    )
    before = _digest(world.ledger_path)
    with _refused("CALL_OPEN"):
        world.preview(20_000)
    assert _digest(world.ledger_path) == before


def test_unverified_and_uncovered_quarantined_calls_refuse(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.call("0.01", verify=False)
    with _refused("CALLS_UNVERIFIED"):
        world.preview(30_000)
    with sqlite3.connect(world.ledger_path) as db:
        db.execute("UPDATE calls SET verification = 'quarantined'")
    with _refused("CALLS_QUARANTINED"):
        world.preview(30_000)


def test_a_lower_figure_refuses(tmp_path: Path) -> None:
    world = World(tmp_path)
    with _refused("USAGE_LOWER"):
        world.preview(19_999)


def test_a_stale_figure_with_charges_since_refuses(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.call("0.08")  # 80,000 charged since
    with _refused("USAGE_BEHIND"):
        world.preview(20_000)  # the same figure as last time
    with _refused("USAGE_BEHIND"):
        world.preview(40_000)  # 60,000 behind
    assert world.preview(51_000)["drift_micro_usd"] == -49_000  # 49,000 behind: allowed


def test_a_carried_overcount_never_blocks(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.call("0.03")
    world.apply(world.preview(30_000))  # 20,000 carried from now on
    world.clock.advance(3600)
    preview = world.preview(30_000)
    assert preview["carried_micro_usd"] == 20_000


def test_an_open_run_or_marker_refuses(tmp_path: Path) -> None:
    world = World(tmp_path)
    rc.write_marker(world.ledger_path, {"run_id": "a" * 32, "overridden": False})
    with _refused("RUN_UNRESOLVED"):
        world.preview(20_000)


# --- freshness (F8) ---------------------------------------------------------------------


def test_future_and_stale_readings_refuse(tmp_path: Path) -> None:
    world = World(tmp_path)
    with _refused("EVIDENCE_FUTURE"):
        world.preview(20_000, as_of_ago=-120, viewed_ago=-120)
    with _refused("EVIDENCE_STALE"):
        world.preview(20_000, as_of_ago=8000, viewed_ago=7300)
    with _refused("EVIDENCE_STALE"):  # lag above 86,400 s
        world.preview(20_000, as_of_ago=86_000, viewed_ago=60)


def test_a_call_after_the_reading_minus_the_margin_refuses_with_the_earliest_time(
    tmp_path: Path,
) -> None:
    world = World(tmp_path)
    world.call("0.01", closed_ago=900)
    with pytest.raises(rc.ReconcileRefused) as refused:
        world.preview(30_000, as_of_ago=600)  # call closed 300 s before the reading
    assert refused.value.code == "CALL_TOO_RECENT"
    assert refused.value.facts["earliest_as_of"]
    assert world.preview(30_000, as_of_ago=0)["settle_lag_seconds"] == 600


def test_the_viewed_fallback_uses_the_one_hour_margin(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.call("0.01", closed_ago=1800)
    with _refused("CALL_TOO_RECENT"):
        world.preview(30_000, kind=rc.KIND_VIEWED, viewed_ago=0)
    world.clock.advance(1900)
    preview = world.preview(30_000, kind=rc.KIND_VIEWED, viewed_ago=0)
    assert preview["fallback"] is True
    assert preview["margin_seconds"] == 3600


def test_the_margin_is_never_below_the_configured_lag(tmp_path: Path) -> None:
    world = World(tmp_path, lag=5000)
    world.call("0.01", closed_ago=4000)
    with _refused("CALL_TOO_RECENT"):
        world.preview(30_000, as_of_ago=0)


# --- apply: confirmation, single use, compare-and-set ------------------------------------


def test_the_typed_figure_must_match(tmp_path: Path) -> None:
    world = World(tmp_path)
    preview = world.preview(20_000)
    with _refused("USAGE_CONFIRMATION_REQUIRED"):
        world.apply(preview, confirm=20_001)
    assert world.runs.all() == []


def test_a_preview_is_single_use_and_bound_to_its_administrator(tmp_path: Path) -> None:
    world = World(tmp_path)
    preview = world.preview(20_000)
    with _refused("PREVIEW_UNKNOWN"):
        world.recon.apply(
            preview["preview_id"],
            confirm_usage_micro_usd=20_000,
            scopes=(True, True, True),
            actor="someone-else",
            role="HR",
            session="s1",
        )
    # Another administrator's attempt never uses it up; its own administrator's does.
    assert world.apply(preview)["outcome"] == "applied"
    with _refused("PREVIEW_UNKNOWN"):
        world.apply(preview)


def test_an_expired_preview_refuses(tmp_path: Path) -> None:
    world = World(tmp_path)
    preview = world.preview(20_000)
    world.clock.advance(rc.PREVIEW_SECONDS + 1)
    with _refused("PREVIEW_EXPIRED"):
        world.apply(preview)


def _change_cap(world: World) -> None:
    world.ledger().set_cap(24_000_000)


def _settle_a_call(world: World) -> None:
    world.call("0.001", closed_ago=10_000)


def _cli_reconcile(world: World) -> None:
    world.ledger().reconcile(20_000, settle_lag_seconds=0)


def _quarantine(world: World) -> None:
    world.call("0.001", closed_ago=10_000, verify=False)


@pytest.mark.parametrize("change", [_change_cap, _settle_a_call, _cli_reconcile, _quarantine])
def test_any_ledger_write_between_preview_and_apply_refuses_without_writing(
    tmp_path: Path, change: Any
) -> None:
    world = World(tmp_path)
    preview = world.preview(20_000)
    change(world)
    before = _digest(world.ledger_path)
    with _refused("CONTROLS_CONFLICT"):
        world.apply(preview)
    assert _digest(world.ledger_path) == before
    run = world.only_run()
    assert run["status"] == "refused"
    assert world.marker() is None


def test_a_second_tab_cannot_reuse_the_state(tmp_path: Path) -> None:
    world = World(tmp_path)
    first = world.preview(20_000, actor="hr-admin")
    second = world.preview(20_000, actor="hr-two")
    world.apply(first)
    with _refused("PREVIEW_UNKNOWN"):  # invalidated when the first intent was written
        world.recon.apply(
            second["preview_id"],
            confirm_usage_micro_usd=20_000,
            scopes=(True, True, True),
            actor="hr-two",
            role="HR",
            session="s1",
        )


# --- the lock and the marker (F5) ---------------------------------------------------------


def test_the_lock_is_exclusive_within_the_process(tmp_path: Path) -> None:
    world = World(tmp_path)
    preview = world.preview(20_000)
    held = threading.Event()
    release = threading.Event()

    def hold() -> None:
        with rc.reconcile_lock(world.ledger_path):
            held.set()
            release.wait(5)

    thread = threading.Thread(target=hold)
    thread.start()
    held.wait(5)
    try:
        with _refused("LEDGER_BUSY"):
            world.apply(preview)
    finally:
        release.set()
        thread.join()
    assert world.runs.all() == []  # nothing written before the lock


def test_the_lock_is_exclusive_across_processes_and_ends_with_the_process(
    tmp_path: Path,
) -> None:
    world = World(tmp_path)
    script = (
        "import sys, time\n"
        "from ai_assistant import claude_reconciliation as rc\n"
        "with rc.reconcile_lock(sys.argv[1]):\n"
        "    print('held', flush=True)\n"
        "    time.sleep(60)\n"
    )
    env = {**os.environ, "PYTHONPATH": str(HERE)}
    child = subprocess.Popen(
        [sys.executable, "-c", script, str(world.ledger_path)],
        stdout=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        assert child.stdout is not None
        assert child.stdout.readline().strip() == "held"
        with _refused("LEDGER_BUSY"), rc.reconcile_lock(world.ledger_path):
            pass
    finally:
        child.kill()
        child.wait(10)
    # The OS releases it with the process (on Windows shortly after, not at once).
    for _ in range(50):
        try:
            with rc.reconcile_lock(world.ledger_path):
                break
        except rc.ReconcileRefused:
            time.sleep(0.1)
    else:
        pytest.fail("the lock outlived its process")
    assert rc.lock_file(world.ledger_path).exists()  # never deleted


def test_operator_writes_refuse_while_a_marker_exists_and_the_override_is_recorded(
    tmp_path: Path,
) -> None:
    world = World(tmp_path)
    rc.write_marker(world.ledger_path, {"run_id": "b" * 32, "overridden": False})
    with _refused("RUN_UNRESOLVED"), rc.operator_write(world.ledger_path):
        pass
    with _refused("RUN_UNRESOLVED"), rc.operator_write(world.ledger_path, override_run="c" * 32):
        pass
    with rc.operator_write(world.ledger_path, override_run="b" * 32):
        pass
    marker = world.marker()
    assert marker is not None and marker["overridden"] is True and marker["overridden_at"]


def test_the_marker_is_checked_under_the_lock(tmp_path: Path, monkeypatch: Any) -> None:
    # rev 9 L1: an HR apply that writes its marker between an operator's lock attempt and its
    # check can never be passed by that operator: the check happens after the lock is held.
    world = World(tmp_path)
    order: list[str] = []
    original = rc.read_marker

    def watched(path: Any) -> Any:
        order.append("marker")
        return original(path)

    original_lock = rc.reconcile_lock

    def watched_lock(path: Any) -> Any:
        order.append("lock")
        return original_lock(path)

    monkeypatch.setattr(rc, "read_marker", watched)
    monkeypatch.setattr(rc, "reconcile_lock", watched_lock)
    with rc.operator_write(world.ledger_path):
        pass
    assert order == ["lock", "marker"]


def test_a_marker_is_cleared_only_by_its_own_run(tmp_path: Path) -> None:
    world = World(tmp_path)
    rc.write_marker(world.ledger_path, {"run_id": "d" * 32, "overridden": True})
    assert rc.clear_marker(world.ledger_path, "e" * 32) is False
    assert world.marker() is not None


def test_no_directory_fsync_on_windows(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(rc.sys, "platform", "win32")
    calls: list[Any] = []
    monkeypatch.setattr(rc.os, "open", lambda *a, **k: calls.append(a))
    rc._fsync_directory(tmp_path)
    assert calls == []


# --- crashes and resolve (F7, Q12) -------------------------------------------------------


class Crash(BaseException):
    pass


def _crash_before_the_ledger(world: World, monkeypatch: Any, usage: int = 20_000) -> str:
    monkeypatch.setattr(rc.CheckedLedger, "verify", lambda self: (_ for _ in ()).throw(Crash()))
    preview = world.preview(usage)
    with pytest.raises(Crash):
        world.apply(preview)
    monkeypatch.undo()
    run = world.only_run()
    assert run["status"] == "requested" and world.marker() is not None
    return str(run["run_id"])


def _crash_after_the_commit(world: World, monkeypatch: Any, usage: int) -> str:
    original = rc.Runs.finish

    def finish(self: rc.Runs, run_id: str, status: str, **kwargs: Any) -> None:
        if status == "applied":
            raise Crash()
        original(self, run_id, status, **kwargs)

    monkeypatch.setattr(rc.Runs, "finish", finish)
    preview = world.preview(usage)
    with pytest.raises(Crash):
        world.apply(preview)
    monkeypatch.undo()
    run = world.only_run()
    assert run["status"] == "requested" and world.marker() is not None
    assert world.ledger().status().last_provider_usage == usage  # committed
    return str(run["run_id"])


def test_resolve_waits_for_the_bound(tmp_path: Path, monkeypatch: Any) -> None:
    world = World(tmp_path)
    run_id = _crash_before_the_ledger(world, monkeypatch)
    with _refused("RESOLVE_NOT_YET"):
        world.resolve(run_id)
    assert world.only_run()["status"] == "requested"


def test_a_crash_before_the_ledger_resolves_failed(tmp_path: Path, monkeypatch: Any) -> None:
    world = World(tmp_path)
    run_id = _crash_before_the_ledger(world, monkeypatch)
    world.past_bound()
    assert world.resolve(run_id)["outcome"] == "failed"
    assert world.only_run()["reason"] == "event_absent"
    assert world.marker() is None


def test_a_crash_after_the_commit_resolves_applied(tmp_path: Path, monkeypatch: Any) -> None:
    world = World(tmp_path)
    run_id = _crash_after_the_commit(world, monkeypatch, 20_000)
    world.past_bound()
    assert world.resolve(run_id)["outcome"] == "applied"
    run = world.only_run()
    assert run["attribution_basis"] == "marker_and_prerequisite"
    assert world.marker() is None


def test_a_commit_then_chat_still_resolves_applied(tmp_path: Path, monkeypatch: Any) -> None:
    world = World(tmp_path)
    run_id = _crash_after_the_commit(world, monkeypatch, 20_000)
    world.past_bound()
    world.call("0.002", closed_ago=1)  # chat reserves and settles (no event)
    assert world.resolve(run_id)["outcome"] == "applied"


def test_a_commit_with_the_drift_breaker_resolves_applied(tmp_path: Path, monkeypatch: Any) -> None:
    world = World(tmp_path)
    run_id = _crash_after_the_commit(world, monkeypatch, 200_000)
    world.past_bound()
    assert world.resolve(run_id)["outcome"] == "applied"


def test_an_override_after_the_commit_is_unresolved(tmp_path: Path, monkeypatch: Any) -> None:
    world = World(tmp_path)
    run_id = _crash_after_the_commit(world, monkeypatch, 20_000)
    with rc.operator_write(world.ledger_path, override_run=run_id):
        pass
    world.past_bound()
    assert world.resolve(run_id)["outcome"] == "unresolved"
    assert world.only_run()["reason"] == "marker_overridden"


def test_x1_an_overridden_cli_reconcile_with_the_same_figure_is_unresolved(
    tmp_path: Path, monkeypatch: Any
) -> None:
    world = World(tmp_path)
    run_id = _crash_before_the_ledger(world, monkeypatch)
    with rc.operator_write(world.ledger_path, override_run=run_id):
        world.ledger().reconcile(20_000, settle_lag_seconds=0)
    world.past_bound()
    assert world.resolve(run_id)["outcome"] == "unresolved"
    assert world.marker() is not None  # kept until the owner closes the run


def test_a_cli_release_with_the_same_figure_resolves_failed(
    tmp_path: Path, monkeypatch: Any
) -> None:
    world = World(tmp_path)
    world.call("0.03")
    run_id = _crash_before_the_ledger(world, monkeypatch, usage=30_000)
    with rc.operator_write(world.ledger_path, override_run=run_id):
        world.ledger().reconcile(30_000, release=True, settle_lag_seconds=0)
    world.past_bound()
    assert world.resolve(run_id)["outcome"] == "failed"
    assert world.only_run()["reason"] == "event_released"
    # QG L1: the override marker is kept for the owner, who clears it with owner close.
    marker = world.marker()
    assert marker is not None and marker["overridden"] is True
    world.recon.owner_close(run_id, by="owner", reference="seen", acknowledged_event_id=None)
    assert world.marker() is None
    assert world.only_run()["status"] == "failed"


def test_another_writer_at_p_plus_one_resolves_failed(tmp_path: Path, monkeypatch: Any) -> None:
    world = World(tmp_path)
    run_id = _crash_before_the_ledger(world, monkeypatch)
    with rc.operator_write(world.ledger_path, override_run=run_id):
        world.ledger().set_cap(24_000_000)
    world.past_bound()
    assert world.resolve(run_id)["outcome"] == "failed"
    assert world.only_run()["reason"] == "event_other"


def test_a_refused_run_sharing_p_does_not_block_applied(tmp_path: Path, monkeypatch: Any) -> None:
    world = World(tmp_path)
    preview = world.preview(20_000)
    monkeypatch.setattr(rc, "settle_lag", lambda *a: rc.MAX_LAG_SECONDS + 1)
    with _refused("RECONCILE_REFUSED"):
        world.apply(preview)
    monkeypatch.undo()
    assert world.only_run()["status"] == "refused"
    world.clock.advance(1)
    original = rc.Runs.finish

    def finish(self: rc.Runs, run_id: str, status: str, **kwargs: Any) -> None:
        if status == "applied":
            raise Crash()
        original(self, run_id, status, **kwargs)

    monkeypatch.setattr(rc.Runs, "finish", finish)
    with pytest.raises(Crash):
        world.apply(world.preview(20_000))
    monkeypatch.undo()
    pending = [run for run in world.runs.all() if run["status"] == "requested"]
    world.past_bound()
    assert world.resolve(pending[0]["run_id"])["outcome"] == "applied"


def test_an_error_at_commit_is_uncertain_then_proven(tmp_path: Path, monkeypatch: Any) -> None:
    world = World(tmp_path)
    original = BudgetLedger._transaction

    def committed_then_error(self: BudgetLedger, work: Any) -> Any:
        result = original(self, work)
        if isinstance(self, rc.CheckedLedger) and self.work_returned:
            raise sqlite3.OperationalError("disk I/O error")
        return result

    monkeypatch.setattr(BudgetLedger, "_transaction", committed_then_error)
    assert world.apply(world.preview(20_000))["outcome"] == "uncertain"
    monkeypatch.undo()
    run = world.only_run()
    assert run["status"] == "requested" and world.marker() is not None
    world.past_bound()
    assert world.resolve(run["run_id"])["outcome"] == "applied"


def test_a_ledger_binding_change_is_unresolved(tmp_path: Path, monkeypatch: Any) -> None:
    world = World(tmp_path)
    run_id = _crash_after_the_commit(world, monkeypatch, 20_000)
    with sqlite3.connect(world.state_path) as db:
        db.execute("UPDATE claude_reconciliation_runs SET ledger_id = ?", ("f" * 32,))
    world.past_bound()
    assert world.resolve(run_id)["outcome"] == "unresolved"
    assert world.only_run()["reason"] == "ledger_changed"


def test_an_unreadable_ledger_is_busy_and_finalises_nothing(
    tmp_path: Path, monkeypatch: Any
) -> None:
    world = World(tmp_path)
    run_id = _crash_after_the_commit(world, monkeypatch, 20_000)
    world.past_bound()
    blocker = sqlite3.connect(world.ledger_path, isolation_level=None)
    try:
        blocker.execute("BEGIN EXCLUSIVE")
        with _refused("LEDGER_BUSY"):
            world.resolve(run_id)
    finally:
        blocker.execute("ROLLBACK")
        blocker.close()
    assert world.only_run()["status"] == "requested"


def test_a_stale_marker_after_a_finished_run_is_cleared_by_resolve(
    tmp_path: Path, monkeypatch: Any
) -> None:
    world = World(tmp_path)
    monkeypatch.setattr(rc, "clear_marker", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    world.apply(world.preview(20_000))
    monkeypatch.undo()
    run = world.only_run()
    assert run["status"] == "applied" and world.marker() is not None
    with _refused("RUN_UNRESOLVED"):
        world.preview(20_000)
    world.resolve(run["run_id"])
    assert world.marker() is None
    world.preview(20_000)


def test_an_open_run_blocks_a_new_apply(tmp_path: Path, monkeypatch: Any) -> None:
    world = World(tmp_path)
    run_id = _crash_before_the_ledger(world, monkeypatch)
    with _refused("RUN_UNRESOLVED"):
        world.preview(20_000)
    world.past_bound()
    world.resolve(run_id)
    world.preview(20_000)


# --- owner close (F6) ---------------------------------------------------------------------


def test_owner_close_records_an_acknowledgement_and_never_applied(
    tmp_path: Path, monkeypatch: Any
) -> None:
    world = World(tmp_path)
    run_id = _crash_before_the_ledger(world, monkeypatch)
    with rc.operator_write(world.ledger_path, override_run=run_id):
        world.ledger().reconcile(20_000, settle_lag_seconds=0)
    world.past_bound()
    world.resolve(run_id)
    before = _digest(world.ledger_path)
    event = world.ledger().status()  # noqa: F841 - read only
    with sqlite3.connect(world.ledger_path) as db:
        last_event = db.execute("SELECT MAX(id) FROM operator_events").fetchone()[0]
    result = world.recon.owner_close(
        run_id, by="owner", reference="checked Console 2026-11-01", acknowledged_event_id=last_event
    )
    assert result["outcome"] == "owner_closed"
    run = world.only_run()
    assert run["status"] == "owner_closed"
    assert run["acknowledged_state"] == "present"
    assert run["attribution_basis"] is None
    assert _digest(world.ledger_path) == before
    assert world.marker() is None


def test_owner_close_of_a_requested_run_waits_for_the_bound(
    tmp_path: Path, monkeypatch: Any
) -> None:
    world = World(tmp_path)
    run_id = _crash_before_the_ledger(world, monkeypatch)
    with _refused("RUN_UNRESOLVED"):
        world.recon.owner_close(run_id, by="owner", reference="x", acknowledged_event_id=None)
    world.past_bound()
    assert (
        world.recon.owner_close(run_id, by="owner", reference="x", acknowledged_event_id=None)[
            "outcome"
        ]
        == "owner_closed"
    )


def test_transitions_are_closed(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.apply(world.preview(20_000))
    run_id = world.only_run()["run_id"]
    with pytest.raises(rc.RunConflict):
        world.runs.finish(run_id, "failed", expected="applied", actor="x")
    with pytest.raises(rc.RunConflict):
        world.runs.finish(run_id, "applied", expected="requested", actor="x")


def test_reads_never_write(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.apply(world.preview(20_000))
    before = (_digest(world.ledger_path), _digest(world.state_path))
    for _ in range(3):
        world.recon.listing()
        rc.read_snapshot(world.ledger_path, events_after=0)
    assert (_digest(world.ledger_path), _digest(world.state_path)) == before


# --- the operator's script (F12) -----------------------------------------------------------


@pytest.fixture
def cli_world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[World]:
    world = World(tmp_path)
    monkeypatch.setenv("AI_ASSISTANT_MODEL_ADMIN_DB_PATH", str(world.state_path))
    yield world


def _cli(world: World, *args: str) -> int:
    sys.path.insert(0, str(HERE / "scripts"))
    try:
        import budget_ledger

        return int(budget_ledger.main(["--ledger", str(world.ledger_path), *args]))
    finally:
        sys.path.remove(str(HERE / "scripts"))


@pytest.mark.parametrize(
    "args",
    [
        ("reconcile", "--provider-usage", "0.02"),
        ("set-cap", "--usd", "24.00"),
        ("reset-breaker", "--code", "usage_missing"),
        ("verify",),
    ],
)
def test_cli_writes_refuse_while_a_marker_exists(cli_world: World, args: tuple[str, ...]) -> None:
    rc.write_marker(cli_world.ledger_path, {"run_id": "1" * 32, "overridden": False})
    before = _digest(cli_world.ledger_path)
    assert _cli(cli_world, *args) == 2
    assert _digest(cli_world.ledger_path) == before


def test_cli_reconcile_with_the_override_proceeds(cli_world: World) -> None:
    rc.write_marker(cli_world.ledger_path, {"run_id": "1" * 32, "overridden": False})
    assert (
        _cli(cli_world, "reconcile", "--provider-usage", "0.02", "--override-intent", "1" * 32) == 0
    )
    marker = cli_world.marker()
    assert marker is not None and marker["overridden"] is True


def test_cli_verify_attest_runs_and_owner_close(cli_world: World, monkeypatch: Any) -> None:
    cli_world.call("0.01", verify=False)
    assert _cli(cli_world, "verify") == 0
    assert _cli(cli_world, "attest-legacy-retired", "--reference", "retired all") == 0
    assert cli_world.runs.prerequisite()["owner_reference"] == "retired all"
    assert _cli(cli_world, "runs") == 0


def test_cli_reading_at_lengthens_the_lag(cli_world: World) -> None:
    cli_world.call("0.01", closed_ago=900)
    reading = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(time.time() - 600))
    assert _cli(cli_world, "reconcile", "--provider-usage", "0.03", "--reading-at", reading) == 2


# --- the routes ---------------------------------------------------------------------------


def _journey(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    from tests.test_claude_runtime import ClaudeJourney

    journey = ClaudeJourney(tmp_path, monkeypatch)
    journey.selector.reconciler.runs.record_prerequisite("owner", "retired")
    return journey


def _body(usage: int, viewed: float | None = None) -> dict[str, Any]:
    at = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(viewed or time.time() - 30))
    return {
        "usage_micro_usd": usage,
        "as_of": at,
        "as_of_kind": "console_refreshed",
        "viewed_at": at,
        "scope_workspace": True,
        "scope_only": True,
        "scope_cumulative": True,
    }


def test_hr_reconciles_through_the_routes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.test_model_management import API

    journey = _journey(tmp_path, monkeypatch)
    active = journey.client.get(API).json()["active"]
    preview = journey.client.post(f"{API}/budget/claude/reconciliation/preview", json=_body(0))
    assert preview.status_code == 200, preview.text
    applied = journey.client.post(
        f"{API}/budget/claude/reconciliation/apply",
        json={
            "preview_id": preview.json()["preview_id"],
            "confirm_usage_micro_usd": 0,
            "scope_workspace": True,
            "scope_only": True,
            "scope_cumulative": True,
        },
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["outcome"] == "applied"
    assert applied.json()["budget"]["claude"]["reconciliation"]["chat_fresh"] is True
    listing = journey.client.get(f"{API}/budget/claude/reconciliation").json()
    assert listing["runs"][0]["status"] == "applied"
    assert journey.client.get(API).json()["active"] == active  # F10: activation unchanged
    audit = journey.client.get(f"{API}/audit").json()
    assert any(event["action"] == "CLAUDE_RECONCILIATION" for event in audit["events"])


def test_refusals_carry_a_code_and_are_audited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_model_management import API

    journey = _journey(tmp_path, monkeypatch)
    body = _body(0)
    body["scope_only"] = False
    response = journey.client.post(f"{API}/budget/claude/reconciliation/preview", json=body)
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "SCOPE_UNCONFIRMED"
    refused = [e for e in journey.client.get(f"{API}/audit").json()["events"] if e["code"]]
    assert any(event["code"] == "SCOPE_UNCONFIRMED" for event in refused)


def test_the_routes_need_the_hr_capability_and_the_page_origin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_model_management import API

    journey = _journey(tmp_path, monkeypatch)
    no_origin = journey.client.post(
        f"{API}/budget/claude/reconciliation/preview", json=_body(0), headers={"Origin": ""}
    )
    assert no_origin.status_code == 403
    journey.client.cookies.set("clm_session", "rm-session")
    for method, path in (
        ("get", "/budget/claude/reconciliation"),
        ("post", "/budget/claude/reconciliation/preview"),
        ("post", "/budget/claude/reconciliation/apply"),
        ("post", f"/budget/claude/reconciliation/runs/{'a' * 32}/resolve"),
    ):
        kwargs = {"json": _body(0)} if method == "post" else {}
        response = getattr(journey.client, method)(f"{API}{path}", **kwargs)
        assert response.status_code in (403, 422), (path, response.status_code)
        assert response.status_code != 200


def test_the_listing_route_writes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.test_model_management import API

    journey = _journey(tmp_path, monkeypatch)
    ledger = Path(journey.settings.anthropic_ledger_path)
    gptoss = Path(journey.settings.budget_ledger_path)
    before = (_digest(ledger), _digest(gptoss) if gptoss.exists() else None)
    for _ in range(3):
        assert journey.client.get(f"{API}/budget/claude/reconciliation").status_code == 200
    assert (_digest(ledger), _digest(gptoss) if gptoss.exists() else None) == before
    assert not rc.lock_file(ledger).exists()
    assert not rc.marker_file(ledger).exists()


def test_the_new_module_is_not_a_basis_file_and_moves_no_basis() -> None:
    from ai_assistant import model_qualification

    names = {str(path) for path in model_qualification.BASIS_FILES}
    assert not any("claude_reconciliation" in name for name in names)
    assert not any("model_admin" in name for name in names)
    data = json.loads((HERE / "ai_assistant" / "synthetic_boundary.json").read_text("utf-8"))
    assert "reconciliations" not in data["code_vocabulary"]


# --- QG round 1 remediation (H1, M1, M2, L1 to L4) ----------------------------------------


def _copy_run(world: World, **changes: Any) -> None:
    run = dict(world.runs.all()[0])
    run.update(changes)
    with sqlite3.connect(world.state_path) as db:
        db.execute(
            f"INSERT INTO claude_reconciliation_runs ({', '.join(run)})"
            f" VALUES ({', '.join('?' for _ in run)})",
            tuple(run.values()),
        )


def test_h1_the_cli_guard_fails_closed_when_the_profile_cannot_be_read(
    cli_world: World, monkeypatch: Any
) -> None:
    rc.write_marker(cli_world.ledger_path, {"run_id": "2" * 32, "overridden": False})

    def busy(path: Any) -> str:
        raise LedgerError("LEDGER_BUSY", "busy")

    monkeypatch.setattr(anthropic_runtime, "ledger_profile", busy)
    before = _digest(cli_world.ledger_path)
    for args in (
        ("reconcile", "--provider-usage", "0.02"),
        ("set-cap", "--usd", "24.00"),
        ("reset-breaker", "--code", "usage_missing"),
        ("verify",),
    ):
        assert _cli(cli_world, *args) == 2, args
    assert _digest(cli_world.ledger_path) == before
    marker = cli_world.marker()
    assert marker is not None and marker["overridden"] is False


def test_m1_owner_close_clears_the_stale_marker_of_a_finished_run(
    tmp_path: Path, monkeypatch: Any
) -> None:
    world = World(tmp_path)
    monkeypatch.setattr(rc, "clear_marker", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    world.apply(world.preview(20_000))
    monkeypatch.undo()
    run_id = world.only_run()["run_id"]
    assert world.marker() is not None
    result = world.recon.owner_close(run_id, by="owner", reference="x", acknowledged_event_id=None)
    assert result["outcome"] == "applied"  # unchanged; only the stale marker went
    assert world.marker() is None
    with sqlite3.connect(world.state_path) as db:
        outcomes = [row[0] for row in db.execute("SELECT outcome FROM events")]
    assert "stale_marker_cleared" in outcomes


@pytest.mark.parametrize(
    ("marker", "reason"),
    [
        (None, "marker_missing"),
        ({"run_id": "9" * 32, "overridden": False}, "marker_missing"),
        ("other_p", "marker_missing"),
    ],
)
def test_a_marker_that_is_missing_or_not_this_runs_is_unresolved(
    tmp_path: Path, monkeypatch: Any, marker: Any, reason: str
) -> None:
    world = World(tmp_path)
    run_id = _crash_after_the_commit(world, monkeypatch, 20_000)
    current = world.marker()
    assert current is not None
    if marker is None:
        rc.marker_file(world.ledger_path).unlink()
    elif marker == "other_p":
        rc.write_marker(world.ledger_path, {**current, "pre_event_id": current["pre_event_id"] + 7})
    else:
        rc.write_marker(world.ledger_path, marker)
    world.past_bound()
    assert world.resolve(run_id)["outcome"] == "unresolved"
    assert world.only_run()["reason"] == reason


def test_an_event_after_the_bound_is_unresolved(tmp_path: Path, monkeypatch: Any) -> None:
    world = World(tmp_path)
    run_id = _crash_after_the_commit(world, monkeypatch, 20_000)
    run = world.only_run()
    with sqlite3.connect(world.ledger_path) as db:
        db.execute(
            "UPDATE operator_events SET created_at = ? WHERE id = ?",
            (run["deadline_at"] + 60_000, run["pre_event_id"] + 1),
        )
    world.past_bound()
    world.clock.advance(120)
    assert world.resolve(run_id)["outcome"] == "unresolved"
    assert world.only_run()["reason"] == "event_after_bound"


def test_a_missing_predicted_breaker_event_is_unresolved(tmp_path: Path, monkeypatch: Any) -> None:
    world = World(tmp_path)
    run_id = _crash_after_the_commit(world, monkeypatch, 20_000)
    run = world.only_run()
    expected = json.loads(run["expected"])
    expected["breaker_open"] = 1
    with sqlite3.connect(world.state_path) as db:
        db.execute("UPDATE claude_reconciliation_runs SET expected = ?", (json.dumps(expected),))
    world.past_bound()
    assert world.resolve(run_id)["outcome"] == "unresolved"
    assert world.only_run()["reason"] == "sequence_mismatch"


def test_another_run_holding_the_same_event_is_unresolved(tmp_path: Path, monkeypatch: Any) -> None:
    world = World(tmp_path)
    run_id = _crash_after_the_commit(world, monkeypatch, 20_000)
    _copy_run(world, run_id="8" * 32, status="unresolved")
    world.past_bound()
    assert world.resolve(run_id)["outcome"] == "unresolved"
    assert world.runs.get(run_id)["reason"] == "shared_event"


def test_a_missing_prerequisite_at_resolve_is_unresolved(tmp_path: Path, monkeypatch: Any) -> None:
    world = World(tmp_path)
    run_id = _crash_after_the_commit(world, monkeypatch, 20_000)
    with sqlite3.connect(world.state_path) as db:
        db.execute("DELETE FROM claude_reconciliation_prerequisite")
    world.past_bound()
    assert world.resolve(run_id)["outcome"] == "unresolved"
    assert world.only_run()["reason"] == "prerequisite_missing"


def test_an_unreadable_marker_is_busy_and_finalises_nothing(
    tmp_path: Path, monkeypatch: Any
) -> None:
    world = World(tmp_path)
    run_id = _crash_after_the_commit(world, monkeypatch, 20_000)
    rc.marker_file(world.ledger_path).write_text("{not json", encoding="utf-8")
    world.past_bound()
    with _refused("LEDGER_BUSY"):
        world.resolve(run_id)
    assert world.only_run()["status"] == "requested"


def test_an_unexpected_ledger_write_is_rolled_back_and_failed(
    tmp_path: Path, monkeypatch: Any
) -> None:
    # The ledger opens the breaker before its reconcile time (a clock step back): the check
    # after the accounting catches it, the transaction rolls back, and the run is failed.
    world = World(tmp_path)
    preview = world.preview(200_000)
    before = _digest(world.ledger_path)
    original = BudgetLedger._open_breaker

    def stepped(self: BudgetLedger, connection: Any, code: str) -> None:
        original(self, connection, code)
        connection.execute("UPDATE ledger_meta SET breaker_opened_at = last_reconciled_at - 1")

    monkeypatch.setattr(BudgetLedger, "_open_breaker", stepped)
    with _refused("CONTROLS_CONFLICT"):
        world.apply(preview)
    monkeypatch.undo()
    assert _digest(world.ledger_path) == before
    assert world.only_run()["status"] == "failed"


def test_p1_dependency_a_lockless_legacy_writer_would_be_misattributed(
    tmp_path: Path, monkeypatch: Any
) -> None:
    # Documents why P1 (earlier script copies retired, attested) is binding: a writer that
    # ignores the lock and marker leaves an intact marker, and resolve cannot tell.
    world = World(tmp_path)
    run_id = _crash_before_the_ledger(world, monkeypatch)
    BudgetLedger(world.ledger_path).reconcile(20_000, settle_lag_seconds=0)
    world.past_bound()
    assert world.resolve(run_id)["outcome"] == "applied"


def test_applied_is_never_written_without_its_proof(tmp_path: Path, monkeypatch: Any) -> None:
    world = World(tmp_path)
    run_id = _crash_before_the_ledger(world, monkeypatch)
    for fields in ({}, {"event_id": 3}, {"attribution_basis": "x"}):
        with pytest.raises(rc.RunConflict):
            world.runs.finish(run_id, "applied", expected="requested", actor="x", **fields)
    assert world.only_run()["status"] == "requested"


def test_an_open_run_found_at_the_intent_step_refuses(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.apply(world.preview(20_000))
    world.clock.advance(1)
    preview = world.preview(20_000)
    _copy_run(world, run_id="7" * 32, status="unresolved")
    with _refused("RUN_UNRESOLVED"):
        world.apply(preview)
    assert [run["status"] for run in world.runs.all()].count("requested") == 0


def test_a_ledger_of_another_profile_refuses(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.ledger_path.unlink()
    from ai_assistant.model_profiles import OPENROUTER_PROFILE_ID

    BudgetLedger.initialise(
        world.ledger_path,
        cap_micro_usd=1_000_000,
        opening_usage_micro_usd=0,
        key_alias="key-01",
        profile_id=OPENROUTER_PROFILE_ID,
    )
    with _refused("LEDGER_PROFILE_MISMATCH"):
        world.preview(0)


def test_the_prerequisite_is_checked_again_at_apply(tmp_path: Path) -> None:
    world = World(tmp_path)
    preview = world.preview(20_000)
    with sqlite3.connect(world.state_path) as db:
        db.execute("DELETE FROM claude_reconciliation_prerequisite")
    with _refused("PREREQUISITE_MISSING"):
        world.apply(preview)
    assert world.runs.all() == []


def test_the_viewing_age_is_checked_again_at_apply(tmp_path: Path) -> None:
    world = World(tmp_path)
    preview = world.preview(20_000, as_of_ago=7150, viewed_ago=7150)
    world.clock.advance(100)
    with _refused("EVIDENCE_STALE"):
        world.apply(preview)
    assert world.runs.all() == []


def test_resolve_while_an_apply_holds_the_lock_is_busy(tmp_path: Path, monkeypatch: Any) -> None:
    world = World(tmp_path)
    run_id = _crash_before_the_ledger(world, monkeypatch)
    world.past_bound()
    held, release = threading.Event(), threading.Event()

    def hold() -> None:
        with rc.reconcile_lock(world.ledger_path):
            held.set()
            release.wait(5)

    thread = threading.Thread(target=hold)
    thread.start()
    held.wait(5)
    try:
        with _refused("LEDGER_BUSY"):
            world.resolve(run_id)
    finally:
        release.set()
        thread.join()
    assert world.only_run()["status"] == "requested"


def test_the_prerequisite_is_audited_as_recorded(tmp_path: Path) -> None:
    world = World(tmp_path)
    with sqlite3.connect(world.state_path) as db:
        rows = db.execute("SELECT outcome FROM events WHERE code = 'PREREQUISITE'").fetchall()
    assert rows == [("recorded",)]
