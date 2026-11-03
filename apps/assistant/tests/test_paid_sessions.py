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
from ai_assistant.claude_reconciliation import marker_file
from ai_assistant.ledger_migration import migrate_to_format_2, v1_fingerprint
from ai_assistant.llm import ModelUsage
from tests.remote_fixtures import ENDPOINT, new_ledger


@pytest.fixture(autouse=True)
def no_daily_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    # The session is under test here; the D-095 daily allowance has its own tests.
    monkeypatch.setattr("ai_assistant.budget.DEFAULT_DAILY_CAP_MICRO_USD", MAX_MICRO_USD)


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
    assert ledger.profile().accounting_mode == "provider_anchored"


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


# --- conservative-only resume ----------------------------------------------------------------


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


def test_usage_missing_is_resumable_only_while_every_unverified_call_is_conservative(
    tmp_path: Path,
) -> None:
    ledger = _ledger(tmp_path)
    ledger.settle(_admit(ledger, 50_000), usage=_usage("0.010000"), error_class=None)
    ledger.settle(_admit(ledger, 60_000), usage=None, error_class=None)  # usage missing
    # The settled call is still unverified: not proven, so not resumable yet.
    assert ledger.resume_blocker("usage_missing") == "UNPROVEN_CHARGES"
    ledger.record_verification(1, verified=True, breaker_code="routing_anomaly")

    assert ledger.resume_blocker("usage_missing") is None
    ledger.resume_breaker("usage_missing")
    assert not ledger.status().breaker_open


@pytest.mark.parametrize(
    "scenario",
    ["cost_above_reservation", "routing", "provider_refusal", "quarantined_settled", "drift"],
)
def test_genuine_anomalies_are_never_resumable(tmp_path: Path, scenario: str) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, clock)
    if scenario == "cost_above_reservation":
        ledger.settle(_admit(ledger, 1_000), usage=_usage("0.002000"), error_class=None)
    elif scenario == "routing":
        usage = ModelUsage(1, 1, 0, 0, Decimal("0.0001"), "g", anomalies=("provider_mismatch",))
        ledger.settle(_admit(ledger, 1_000), usage=usage, error_class=None)
    elif scenario == "provider_refusal":
        ledger.settle(_admit(ledger, 1_000), usage=None, error_class="payment_key_limit")
    elif scenario == "quarantined_settled":
        ledger.settle(_admit(ledger, 1_000), usage=_usage("0.000500"), error_class=None)
        ledger.record_verification(1, verified=False, breaker_code="routing_anomaly")
    else:
        ledger.settle(_admit(ledger, 1_000), usage=_usage("0.000500"), error_class=None)
        clock.advance(601)
        ledger.reconcile(900_000)  # the provider reports far more than the ledger
    code = ledger.status().breaker_code
    assert code is not None

    assert ledger.resume_blocker(code) is not None
    with pytest.raises(LedgerError) as raised:
        ledger.resume_breaker(code)
    assert raised.value.code == "BREAKER_RESUME_REFUSED"
    assert ledger.status().breaker_open


def test_an_abandoned_breaker_with_a_genuine_charge_behind_it_is_not_resumable(
    tmp_path: Path,
) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, clock)
    ledger.settle(_admit(ledger, 1_000), usage=_usage("0.000500"), error_class=None)
    ledger.record_verification(1, verified=False, breaker_code="routing_anomaly")
    # The breaker code is routing_anomaly; even the conservative code would not pass.
    _rows_update = sqlite3.connect(tmp_path / "ledger.sqlite3", isolation_level=None)
    with closing(_rows_update) as connection:
        connection.execute(
            "UPDATE ledger_meta SET breaker_code = 'abandoned_call', write_token = write_token + 1"
        )
    assert ledger.resume_blocker("abandoned_call") == "UNPROVEN_CHARGES"


# --- the owner's migration of a format-1 ledger ----------------------------------------------


def _v1_ledger(path: Path, *, created_at: int = 1_000) -> None:
    """A ledger exactly as the format-1 code created and wrote it."""

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


def test_migration_keeps_every_v1_row_writes_a_verified_backup_and_fences(tmp_path: Path) -> None:
    path = tmp_path / "ledger.sqlite3"
    _v1_ledger(path)
    with closing(sqlite3.connect(path)) as connection:
        before = v1_fingerprint(connection)
    with pytest.raises(LedgerError) as raised:
        BudgetLedger.open(path)
    assert raised.value.code == "LEDGER_MIGRATION_REQUIRED"

    result = migrate_to_format_2(path, backup=tmp_path / "backup" / "ledger.sqlite3")

    assert (result.calls, result.events, result.fingerprint) == (3, 1, before[0])
    with closing(sqlite3.connect(path)) as connection:
        assert v1_fingerprint(connection) == before
    with closing(sqlite3.connect(result.backup)) as connection:
        assert v1_fingerprint(connection) == before
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
    ledger = BudgetLedger.open(path)
    assert ledger.profile().origin == "migrated" and ledger.session() is None
    with (
        closing(sqlite3.connect(path, isolation_level=None)) as connection,
        pytest.raises(sqlite3.IntegrityError),
    ):
        connection.execute("UPDATE ledger_meta SET cap_micro_usd = 1")


@pytest.mark.parametrize(
    "problem", ["open_call", "recent", "marker", "backup_exists", "breaker", "inconsistent"]
)
def test_a_refused_migration_leaves_the_ledger_byte_identical(tmp_path: Path, problem: str) -> None:
    import time

    path = tmp_path / "ledger.sqlite3"
    _v1_ledger(path, created_at=int(time.time() * 1000) if problem == "recent" else 1_000)
    backup = tmp_path / "backup.sqlite3"
    with closing(sqlite3.connect(path, isolation_level=None)) as connection:
        if problem == "open_call":
            connection.execute(
                "INSERT INTO calls (reservation_id, instance_id, created_at, lease_expires_at,"
                " state, reserved_micro_usd, prompt_bound_tokens, output_bound_tokens,"
                " requested_endpoint, verification, anomaly_bits)"
                " VALUES (?, ?, 1000, 2000, 'open', 5, 1, 1, 'a/b', 'unverified', 0)",
                ("e" * 32, "d" * 32),
            )
            connection.execute("UPDATE ledger_meta SET open_reserved_micro_usd = 5")
        if problem == "inconsistent":
            connection.execute("UPDATE ledger_meta SET local_charged_micro_usd = 1")
        if problem == "breaker":
            connection.execute(
                "UPDATE ledger_meta SET breaker_open = 1, breaker_code = 'routing_anomaly',"
                " breaker_opened_at = 1000"
            )
    if problem == "marker":
        marker_file(path).write_text("{}", encoding="utf-8")
    if problem == "backup_exists":
        backup.write_bytes(b"x")
    snapshot = path.read_bytes()

    with pytest.raises(LedgerError):
        migrate_to_format_2(path, backup=backup)

    assert path.read_bytes() == snapshot
    if problem != "backup_exists":
        assert not backup.exists()


def test_the_service_never_migrates_a_format_1_ledger(tmp_path: Path) -> None:
    path = tmp_path / "ledger.sqlite3"
    _v1_ledger(path)
    snapshot = path.read_bytes()
    for attempt in (BudgetLedger.open, lambda p: BudgetLedger(p).verify()):
        with pytest.raises(LedgerError) as raised:
            attempt(path)
        assert raised.value.code == "LEDGER_MIGRATION_REQUIRED"
    assert path.read_bytes() == snapshot
    assert budget.FORMAT_VERSION == 2


def test_the_environment_defaults_fit_one_us5_session_a_day() -> None:
    from ai_assistant.config import AiAssistantSettings

    settings = AiAssistantSettings(_env_file=None)
    assert settings.budget_daily_cap_micro_usd == SESSION_MAX_MICRO_USD
    assert settings.anthropic_daily_cap_micro_usd == SESSION_MAX_MICRO_USD


# --- QG F1: a genuine trip while a resumable breaker is open is never masked -------------------


def test_a_drift_while_an_abandoned_breaker_is_open_blocks_the_resume(tmp_path: Path) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, clock)
    _admit(ledger, 90_000, lease=10)
    clock.advance(11)
    BudgetLedger.open(tmp_path / "ledger.sqlite3", clock=clock)  # abandoned_call opens it
    assert ledger.resume_blocker("abandoned_call") is None
    clock.advance(601)
    ledger.reconcile(5_000_000)  # the provider reports far more: a genuine discrepancy

    assert ledger.status().breaker_code == "abandoned_call"  # the code is not overwritten
    assert ledger.resume_blocker("abandoned_call") == "MASKED_ANOMALY"
    with pytest.raises(LedgerError):
        ledger.resume_breaker("abandoned_call")
    events = _rows(
        tmp_path / "ledger.sqlite3",
        "SELECT code FROM ledger_events WHERE event = ?",
        "trip_while_open",
    )
    assert events == [("reconcile_drift",)]


def test_a_later_quarantine_of_an_already_covered_call_blocks_the_next_resume(
    tmp_path: Path,
) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, clock)
    ledger.settle(_admit(ledger, 50_000), usage=None, error_class=None)  # usage_missing
    ledger.resume_breaker("usage_missing")  # call 1 unverified, conservatively charged
    _admit(ledger, 60_000, lease=10)
    clock.advance(11)
    BudgetLedger.open(tmp_path / "ledger.sqlite3", clock=clock)  # call 2 abandoned
    # The OpenRouter preflight then finds no generation record for call 1.
    ledger.record_verification(1, verified=False, breaker_code="routing_anomaly")

    assert ledger.status().breaker_code == "abandoned_call"
    assert ledger.resume_blocker("abandoned_call") == "MASKED_ANOMALY"


def test_a_conservative_trip_while_open_stays_resumable(tmp_path: Path) -> None:
    clock = Clock()
    ledger = _ledger(tmp_path, clock)
    _admit(ledger, 90_000, lease=10)
    clock.advance(11)
    BudgetLedger.open(tmp_path / "ledger.sqlite3", clock=clock)  # abandoned_call
    ledger.open_breaker("usage_missing")  # recorded, but conservative
    assert ledger.resume_blocker("abandoned_call") is None


# --- QG F2: the accounting mode follows the provider --------------------------------------------


def test_the_accounting_mode_cannot_be_chosen_against_the_provider(tmp_path: Path) -> None:
    from ai_assistant.anthropic_profiles import LEDGER_PROFILE_ID

    for profile_id, wrong in (
        ("openrouter_gpt_oss_120b", "provider_capped"),
        (LEDGER_PROFILE_ID, "provider_anchored"),
    ):
        with pytest.raises(LedgerError):
            BudgetLedger.initialise(
                tmp_path / f"{wrong}.sqlite3",
                cap_micro_usd=1_000_000,
                opening_usage_micro_usd=0,
                key_alias="key-01",
                profile_id=profile_id,
                accounting_mode=wrong,
            )
    path = tmp_path / "v1.sqlite3"
    _v1_ledger(path)
    migrate_to_format_2(path, backup=tmp_path / "v1-backup.sqlite3")
    assert BudgetLedger(path).profile().accounting_mode == "provider_anchored"


def test_migration_refuses_a_header_that_is_not_v1(tmp_path: Path) -> None:
    path = tmp_path / "ledger.sqlite3"
    _v1_ledger(path)
    with closing(sqlite3.connect(path, isolation_level=None)) as connection:
        connection.execute("PRAGMA ignore_check_constraints = 1")
        connection.execute("UPDATE ledger_meta SET profile_id = 'unknown_profile'")
    snapshot = path.read_bytes()
    with pytest.raises(LedgerError) as raised:
        migrate_to_format_2(path, backup=tmp_path / "backup.sqlite3")
    # SQLite's own integrity check already sees the broken CHECK; the header check is the
    # second line of defence. Either way nothing is copied or changed.
    assert raised.value.code in {"LEDGER_CORRUPT", "LEDGER_SCHEMA_UNSUPPORTED"}
    assert path.read_bytes() == snapshot
    assert not (tmp_path / "backup.sqlite3").exists()
