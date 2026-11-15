"""D-118: paid-model sessions in the budget ledger (format 2), the fence against earlier
writers, the conservative-only breaker resume and the owner's format-1 migration. Synthetic
micro-USD only; every ledger is a disposable file and nothing reaches a network.
"""

import multiprocessing
import sqlite3
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from ai_assistant import budget
from ai_assistant.budget import (
    MAX_MICRO_USD,
    SCHEMA,
    SCHEMA_VERSION,
    SESSION_DEFAULT_MICRO_USD,
    SESSION_MAX_MICRO_USD,
    BudgetLedger,
    BudgetRefusedError,
    LedgerError,
    Reservation,
)
from ai_assistant.llm import ModelUsage
from tests.remote_fixtures import ENDPOINT, new_ledger


@pytest.fixture(autouse=True)
def no_daily_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    # The session is under test here; the D-095 daily allowance and the standing US$3.00
    # GPT-OSS day (test_gptoss_daily_ceiling, test_real_inference_controls) have their own tests.
    monkeypatch.setattr("ai_assistant.budget.DEFAULT_DAILY_CAP_MICRO_USD", MAX_MICRO_USD)
    monkeypatch.setattr("ai_assistant.budget.STANDING_DAILY_CEILINGS", {})


class Clock:
    def __init__(self, start: float = 1_800_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _ledger(tmp_path: Path, clock: Clock | None = None, cap: int = 30_000_000) -> BudgetLedger:
    clock = clock or Clock()
    path = new_ledger(tmp_path / "ledger.sqlite3", cap=cap, opening=0, clock=clock)
    return BudgetLedger.open(path, clock=clock)


def _admit(ledger: BudgetLedger, micro_usd: int, **kw: Any) -> str:
    return ledger.reserve(
        Reservation(11_152, 2_000, micro_usd),
        endpoint_slug=ENDPOINT.slug,
        max_in_flight=kw.pop("in_flight", 4),
        lease_seconds=kw.pop("lease", 150),
        **kw,
    )


def _refusal(ledger: BudgetLedger, micro_usd: int, **kw: Any) -> str:
    with pytest.raises(BudgetRefusedError) as raised:
        _admit(ledger, micro_usd, **kw)
    assert raised.value.budget is not None
    return raised.value.budget.outcome


def _usage(cost: str) -> ModelUsage:
    return ModelUsage(3_000, 450, 300, 0, Decimal(cost), "gen-1761-test")


def _rows(path: Path, sql: str, *params: Any) -> list[tuple[Any, ...]]:
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute(sql, params).fetchall()


# --- sessions ----------------------------------------------------------------------------------


def test_the_first_paid_call_opens_one_default_us5_session(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    assert ledger.session() is None
    assert SESSION_DEFAULT_MICRO_USD == SESSION_MAX_MICRO_USD == 5_000_000

    ledger.settle(_admit(ledger, 100_000), usage=_usage("0.040000"), error_class=None)
    session = ledger.session()

    assert session is not None
    assert session.allowance == 5_000_000
    assert session.committed == 40_000 and session.calls == 1 and session.chat_calls == 1
    events = _rows(tmp_path / "ledger.sqlite3", "SELECT event FROM ledger_events ORDER BY id")
    assert [row[0] for row in events] == ["fresh_init", "session_started"]
    assert ledger.profile().accounting_mode == "provider_capped"


def test_the_allowance_admits_exactly_up_to_us5_and_then_stops(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    for _ in range(4):
        ledger.settle(_admit(ledger, 1_000_000), usage=None, error_class="timeout")
    held = _admit(ledger, 1_000_000)  # 5.00 committed: four full charges and one open call

    assert _refusal(ledger, 1) == "refused_session_allowance"
    ledger.settle(held, usage=_usage("0.400000"), error_class=None)
    assert ledger.session().remaining == 600_000  # type: ignore[union-attr]
    _admit(ledger, 600_000)
    assert _refusal(ledger, 1) == "refused_session_allowance"


def test_an_exhausted_session_is_never_renewed_by_a_restart_or_reopen(tmp_path: Path) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, clock)
    ledger.settle(_admit(ledger, 5_000_000), usage=None, error_class="timeout")
    session = ledger.session()

    for _ in range(3):  # a restart is a new process opening the same file
        reopened = BudgetLedger.open(tmp_path / "ledger.sqlite3", clock=clock)
        assert _refusal(reopened, 1) == "refused_session_allowance"
        assert reopened.session() == session
    assert _rows(tmp_path / "ledger.sqlite3", "SELECT COUNT(*) FROM sessions") == [(1,)]


def test_hr_starts_a_new_session_only_explicitly_and_on_the_session_it_saw(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.settle(_admit(ledger, 5_000_000), usage=None, error_class="timeout")
    old = ledger.session()
    assert old is not None

    with pytest.raises(LedgerError) as raised:
        ledger.start_session(5_000_000, expected_session_id=None)
    assert raised.value.code == "SESSION_CHANGED"
    for bad in (0, -1, SESSION_MAX_MICRO_USD + 1, 2.5, "5"):
        with pytest.raises(LedgerError):
            ledger.start_session(bad, expected_session_id=old.session_id)  # type: ignore[arg-type]

    new_id = ledger.start_session(2_000_000, expected_session_id=old.session_id)
    new = ledger.session()
    assert new is not None and new.session_id == new_id != old.session_id
    assert new.allowance == 2_000_000 and new.committed == 0
    states = _rows(
        tmp_path / "ledger.sqlite3", "SELECT state, close_reason FROM sessions ORDER BY id"
    )
    assert states == [("closed", "replaced"), ("open", None)]
    # The lifetime spend is unchanged: nothing is reset.
    assert ledger.status().local_charged == 5_000_000


def test_a_new_session_waits_for_open_calls(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    _admit(ledger, 1_000)
    session = ledger.session()
    with pytest.raises(LedgerError) as raised:
        ledger.start_session(5_000_000, expected_session_id=session.session_id)  # type: ignore[union-attr]
    assert raised.value.code == "SESSION_BUSY"


def test_lowering_and_raising_the_allowance_is_bounded_and_compare_and_set(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.settle(_admit(ledger, 300_000), usage=_usage("0.300000"), error_class=None)
    session = ledger.session()
    assert session is not None

    ledger.set_session_allowance(200_000, expected_revision=session.revision)
    assert _refusal(ledger, 1) == "refused_session_allowance"  # below what was used
    with pytest.raises(LedgerError) as raised:
        ledger.set_session_allowance(5_000_000, expected_revision=session.revision)
    assert raised.value.code == "SESSION_CHANGED"
    with pytest.raises(LedgerError):
        ledger.set_session_allowance(5_000_001, expected_revision=session.revision + 1)
    ledger.set_session_allowance(5_000_000, expected_revision=session.revision + 1)
    _admit(ledger, 1_000)
    events = [
        row[0] for row in _rows(tmp_path / "ledger.sqlite3", "SELECT event FROM ledger_events")
    ]
    assert events.count("session_allowance_changed") == 2


def test_chat_calls_are_limited_per_session_and_survive_a_restart(tmp_path: Path) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, clock)
    for _ in range(2):
        ledger.settle(
            _admit(ledger, 1_000, session_call_limit=3), usage=_usage("0.001"), error_class=None
        )
    reopened = BudgetLedger.open(tmp_path / "ledger.sqlite3", clock=clock)
    reopened.settle(
        _admit(reopened, 1_000, session_call_limit=3), usage=_usage("0.001"), error_class=None
    )

    assert _refusal(reopened, 1_000, session_call_limit=3) == "refused_session_calls"
    # Qualification shares the money allowance but is not a chat call.
    _admit(reopened, 1_000, session_call_limit=3, purpose="qualification")
    assert reopened.session().calls == 4  # type: ignore[union-attr]
    assert reopened.session().chat_calls == 3  # type: ignore[union-attr]


def test_qualification_and_chat_share_the_money_allowance(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.settle(
        _admit(ledger, 4_900_000, purpose="qualification"), usage=None, error_class="timeout"
    )
    assert ledger.session().committed == 4_900_000  # type: ignore[union-attr]
    assert _refusal(ledger, 200_000) == "refused_session_allowance"
    _admit(ledger, 100_000)


def _race_worker(args: tuple[str, int]) -> int:
    path, attempts = args
    budget.STANDING_DAILY_CEILINGS.clear()  # a spawned process: as no_daily_cap does above
    ledger = BudgetLedger(Path(path))
    admitted = 0
    for _ in range(attempts):
        try:
            ledger.reserve(
                Reservation(11_152, 2_000, 400_000),
                endpoint_slug="openai/gpt-oss-120b",
                max_in_flight=100,
                lease_seconds=600,
                daily_cap_micro_usd=MAX_MICRO_USD,
                purpose="chat",
            )
            admitted += 1
        except BudgetRefusedError:
            pass
    return admitted


def test_two_processes_racing_at_the_boundary_admit_exactly_the_allowance(tmp_path: Path) -> None:
    import time

    path = new_ledger(tmp_path / "ledger.sqlite3", cap=30_000_000, opening=0, clock=time.time)
    BudgetLedger.open(path).start_session(5_000_000, expected_session_id=None)
    context = multiprocessing.get_context("spawn")
    with context.Pool(2) as pool:
        counts = pool.map(_race_worker, [(str(path), 10), (str(path), 10)])

    assert sum(counts) == 12  # 12 x 0.40 = 4.80; a 13th would pass US$5.00
    session = BudgetLedger(path).session()
    assert session is not None and session.committed == 4_800_000


# --- the fence against earlier writers -------------------------------------------------------


def test_an_earlier_writer_can_neither_insert_a_call_nor_change_the_header(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    _admit(ledger, 1_000)
    path = tmp_path / "ledger.sqlite3"
    with closing(sqlite3.connect(path, isolation_level=None)) as connection:
        with pytest.raises(sqlite3.IntegrityError):  # the v1 INSERT has no purpose or session
            connection.execute(
                "INSERT INTO calls (reservation_id, instance_id, created_at, lease_expires_at,"
                " state, reserved_micro_usd, prompt_bound_tokens, output_bound_tokens,"
                " requested_endpoint, verification, anomaly_bits)"
                " VALUES (?, ?, 1, 2, 'open', 5, 1, 1, 'a/b', 'unverified', 0)",
                ("a" * 32, "b" * 32),
            )
        with pytest.raises(sqlite3.IntegrityError):  # a v1 header update keeps the token
            connection.execute("UPDATE ledger_meta SET cap_micro_usd = 1")
    ledger.verify()


# --- console resume of financial stops; routing and integrity stay with the owner -------------


def test_an_abandoned_call_is_resumable_and_keeps_its_full_charge(tmp_path: Path) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, clock)
    _admit(ledger, 90_000, lease=10)
    clock.advance(11)
    BudgetLedger.open(tmp_path / "ledger.sqlite3", clock=clock)  # the lease ran out
    assert ledger.status().breaker_code == "abandoned_call"
    assert ledger.resume_blocker("abandoned_call") is None

    covered = ledger.resume_breaker("abandoned_call")

    status = ledger.status()
    assert not status.breaker_open and status.local_charged == 90_000
    assert _rows(tmp_path / "ledger.sqlite3", "SELECT state, charged_micro_usd FROM calls") == [
        ("abandoned", 90_000)
    ]
    assert _rows(
        tmp_path / "ledger.sqlite3",
        "SELECT event, code, call_id FROM ledger_events WHERE event = ?",
        "breaker_resumed",
    ) == [("breaker_resumed", "abandoned_call", covered)]
    _admit(ledger, 1_000)


def _stop(ledger: BudgetLedger, clock: Clock, scenario: str) -> None:
    if scenario == "usage_missing":
        ledger.settle(_admit(ledger, 60_000), usage=None, error_class=None)
    elif scenario == "cost_above_reservation":
        ledger.settle(_admit(ledger, 1_000), usage=_usage("0.002000"), error_class=None)
    elif scenario == "provider_refusal":
        ledger.settle(_admit(ledger, 1_000), usage=None, error_class="payment_key_limit")
    elif scenario == "drift":
        ledger.settle(_admit(ledger, 1_000), usage=_usage("0.000500"), error_class=None)
        clock.advance(601)
        ledger.reconcile(900_000)  # the provider reports far more than the ledger
    elif scenario == "routing":
        usage = ModelUsage(1, 1, 0, 0, Decimal("0.0001"), "g", anomalies=("provider_mismatch",))
        ledger.settle(_admit(ledger, 1_000), usage=usage, error_class=None)
    elif scenario == "quarantined_routing":
        ledger.settle(_admit(ledger, 1_000), usage=_usage("0.000500"), error_class=None)
        ledger.record_verification(1, verified=False, breaker_code="routing_anomaly")
    else:
        ledger.open_breaker("ledger_write_failed")


@pytest.mark.parametrize(
    "scenario", ["usage_missing", "cost_above_reservation", "provider_refusal", "drift"]
)
def test_hr_resumes_a_financial_stop_and_every_charge_is_kept(
    tmp_path: Path, scenario: str
) -> None:
    # D-118 amendment P6: a deliberate console action, never automatic, nothing retried.
    clock = Clock()
    ledger = _ledger(tmp_path, clock)
    _stop(ledger, clock, scenario)
    status = ledger.status()
    code = status.breaker_code
    assert code is not None and ledger.resume_blocker(code) is None

    ledger.resume_breaker(code)

    after = ledger.status()
    assert not after.breaker_open
    assert (after.baseline, after.local_charged) == (status.baseline, status.local_charged)


@pytest.mark.parametrize("scenario", ["routing", "quarantined_routing", "ledger_write_failed"])
def test_routing_and_integrity_stops_stay_with_the_owner(tmp_path: Path, scenario: str) -> None:
    # D-118 amendment P7: a data-protection or integrity stop is never HR-resumable.
    clock = Clock()
    ledger = _ledger(tmp_path, clock)
    _stop(ledger, clock, scenario)
    code = ledger.status().breaker_code
    assert code in ("routing_anomaly", "ledger_write_failed")

    assert ledger.resume_blocker(code) == "OWNER_REVIEW_REQUIRED"
    with pytest.raises(LedgerError) as raised:
        ledger.resume_breaker(code)
    assert raised.value.code == "BREAKER_RESUME_REFUSED"
    assert ledger.status().breaker_open
    ledger.resume_breaker(code, owner_reviewed=True)  # the operator script after review
    assert not ledger.status().breaker_open


def test_a_routing_trip_while_a_financial_stop_is_open_blocks_the_hr_resume(
    tmp_path: Path,
) -> None:
    # QG F1: an open breaker never hides a later routing stop.
    clock = Clock()
    ledger = _ledger(tmp_path, clock)
    ledger.settle(_admit(ledger, 50_000), usage=_usage("0.010000"), error_class=None)
    _admit(ledger, 60_000, lease=10)
    clock.advance(11)
    BudgetLedger.open(tmp_path / "ledger.sqlite3", clock=clock)  # abandoned_call
    ledger.record_verification(1, verified=False, breaker_code="routing_anomaly")

    assert ledger.status().breaker_code == "abandoned_call"
    assert ledger.resume_blocker("abandoned_call") == "MASKED_ANOMALY"
    assert _rows(
        tmp_path / "ledger.sqlite3",
        "SELECT code FROM ledger_events WHERE event = ?",
        "trip_while_open",
    ) == [("routing_anomaly",)]
    ledger.resume_breaker("abandoned_call", owner_reviewed=True)


def test_a_misrouted_call_since_the_last_resume_blocks_the_hr_resume(tmp_path: Path) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, clock)
    _admit(ledger, 60_000, lease=10)
    clock.advance(11)
    BudgetLedger.open(tmp_path / "ledger.sqlite3", clock=clock)  # abandoned_call
    with closing(sqlite3.connect(tmp_path / "ledger.sqlite3", isolation_level=None)) as db:
        db.execute("UPDATE calls SET anomaly_bits = ?", (budget.ANOMALY_BITS["model_mismatch"],))
    assert ledger.resume_blocker("abandoned_call") == "MASKED_ANOMALY"


def test_a_financial_trip_while_open_stays_resumable(tmp_path: Path) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, clock)
    _admit(ledger, 90_000, lease=10)
    clock.advance(11)
    BudgetLedger.open(tmp_path / "ledger.sqlite3", clock=clock)  # abandoned_call
    clock.advance(601)
    ledger.reconcile(5_000_000)  # a financial drift, recorded while the breaker is open
    assert ledger.resume_blocker("abandoned_call") is None


def test_every_session_store_is_provider_capped(tmp_path: Path) -> None:
    from ai_assistant.anthropic_profiles import LEDGER_PROFILE_ID

    for profile_id in ("openrouter_gpt_oss_120b", LEDGER_PROFILE_ID):
        with pytest.raises(LedgerError):
            BudgetLedger.initialise(
                tmp_path / f"anchored-{len(profile_id)}.sqlite3",
                cap_micro_usd=1_000_000,
                opening_usage_micro_usd=0,
                key_alias="key-01",
                profile_id=profile_id,
                accounting_mode="provider_anchored",
            )
        ledger = BudgetLedger.initialise(
            tmp_path / f"{len(profile_id)}.sqlite3",
            cap_micro_usd=1_000_000,
            opening_usage_micro_usd=0,
            key_alias="key-01",
            profile_id=profile_id,
        )
        assert ledger.profile().accounting_mode == "provider_capped"


# --- the earlier design's stores: never used, archived without change ------------------------


def _v1_ledger(path: Path, *, created_at: int = 1_000) -> None:
    """A ledger exactly as the format-1 code created and wrote it."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, isolation_level=None)) as connection:
        connection.execute("BEGIN")
        for statement in SCHEMA.split(";"):
            if statement.strip():
                connection.execute(statement)
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        connection.execute(
            "INSERT INTO ledger_meta VALUES (1, 1, ?, ?, 'openrouter_gpt_oss_120b', 'key-02',"
            " 30000000, 54136, 54136, 0, 54136, 18003, 0, 0, NULL, NULL, ?)",
            ("c" * 32, created_at, created_at),
        )
        for index in range(3):
            connection.execute(
                "INSERT INTO calls (reservation_id, instance_id, created_at, lease_expires_at,"
                " state, reserved_micro_usd, charged_micro_usd, prompt_bound_tokens,"
                " output_bound_tokens, requested_endpoint, verification, anomaly_bits, closed_at)"
                " VALUES (?, ?, ?, ?, 'settled', 9000, ?, 10, 10, 'a/b', 'verified', 0, ?)",
                (f"{index:032x}", "d" * 32, created_at, created_at + 1, 6000 + index, created_at),
            )
        connection.execute(
            "INSERT INTO operator_events (created_at, event, amount_micro_usd)"
            " VALUES (?, 'init', 1)",
            (created_at,),
        )
        connection.execute("COMMIT")


def test_the_runtime_refuses_an_earlier_design_store_and_never_changes_it(tmp_path: Path) -> None:
    path = tmp_path / "ledger.sqlite3"
    _v1_ledger(path)
    snapshot = path.read_bytes()
    for attempt in (BudgetLedger.open, lambda p: BudgetLedger(p).verify()):
        with pytest.raises(LedgerError) as raised:
            attempt(path)
        assert raised.value.code == "LEGACY_STORE"
    assert path.read_bytes() == snapshot
    assert budget.FORMAT_VERSION == 2


def _archive_tool() -> Any:
    import importlib.util

    script = Path(__file__).resolve().parents[1] / "scripts" / "storage"
    spec = importlib.util.spec_from_file_location(
        "archive_accounting_stores", script / "archive_accounting_stores.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_archive_copies_every_row_and_never_touches_the_sources(tmp_path: Path) -> None:
    root = tmp_path / "root"
    sources = [root / "budget" / "ledger.sqlite3", root / "budget" / "anthropic_fyp_ledger.sqlite3"]
    for source in sources:
        _v1_ledger(source)
    marker = sources[1].with_name(sources[1].name + ".reconcile.intent")
    marker.write_text('{"run_id": "r"}', encoding="utf-8")
    before = {path: path.read_bytes() for path in [*sources, marker]}
    tool = _archive_tool()
    archive = tmp_path / "archive"

    assert tool.main([str(root), str(archive)]) == 0

    assert {path: path.read_bytes() for path in before} == before  # sources unchanged
    for source in sources:
        copy = archive / "budget" / source.name
        assert tool.rows(copy) == tool.rows(source)
    assert (archive / "budget" / marker.name).read_bytes() == before[marker]
    assert (archive / "manifest.json").is_file()
    assert tool.main([str(root), str(archive)]) == 2  # never into an existing folder
    assert tool.main([str(tmp_path / "empty"), str(tmp_path / "other")]) == 2


def test_the_environment_defaults_fit_one_us5_session_a_day_in_fresh_stores() -> None:
    from ai_assistant.config import AiAssistantSettings

    settings = AiAssistantSettings(_env_file=None)
    assert settings.budget_daily_cap_micro_usd == SESSION_MAX_MICRO_USD
    assert settings.anthropic_daily_cap_micro_usd == SESSION_MAX_MICRO_USD
    fields = AiAssistantSettings.model_fields  # the defaults (tests redirect the stores)
    assert fields["budget_ledger_path"].default == "data/budget/sessions/openrouter.sqlite3"
    assert fields["anthropic_ledger_path"].default == "data/budget/sessions/anthropic.sqlite3"
