"""D-096: HR spending controls on AI Models: the daily allowance, the calls per activation, the
ledger's lifetime cap and a read-only refresh of the OpenRouter key's limit. A mock OpenRouter,
the fake CLM backend and a test ledger only; nothing is spent and no real key is read."""

import sqlite3
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from ai_assistant import model_admin, remote_test
from ai_assistant.budget import BudgetLedger
from ai_assistant.model_admin import ModelSelector
from ai_assistant.model_admin_store import ModelAdminStore, RevisionConflict
from ai_assistant.model_profiles import OPENROUTER_PROFILE_ID
from ai_assistant.model_qualification import qualification_basis
from tests.test_model_management import API
from tests.test_remote_test import SENTINEL, Journey, _settle_verification

CONTROLS = f"{API}/budget/controls"
LIFETIME = f"{API}/budget/lifetime-cap"
REFRESH = f"{API}/budget/provider-refresh"


def _controls(
    journey: Journey, daily: Any, calls: Any, revision: int | None = None, confirm: Any = None
) -> Any:
    if revision is None:
        revision = journey.client.get(f"{API}/budget").json()["controls"]["revision"]
    return journey.client.put(
        CONTROLS,
        json={
            "expected_revision": revision,
            "daily_cap_micro_usd": daily,
            "max_calls": calls,
            # D-098: a raise of the daily limit needs the same amount confirmed.
            **({} if confirm is None else {"confirm_daily_cap_micro_usd": confirm}),
        },
    )


def _ledger(journey: Journey) -> BudgetLedger:
    return BudgetLedger.open(Path(journey.settings.budget_ledger_path))


def _ledger_rows(journey: Journey) -> tuple[Any, list[Any], list[Any]]:
    with sqlite3.connect(journey.settings.budget_ledger_path) as db:
        meta = db.execute("SELECT ledger_id, opening_usage_micro_usd FROM ledger_meta").fetchone()
        calls = db.execute("SELECT * FROM calls ORDER BY id").fetchall()
        events = db.execute("SELECT event, amount_micro_usd FROM operator_events").fetchall()
    return meta, calls, events


def _actions(journey: Journey) -> list[tuple[str, str]]:
    events = journey.client.get(f"{API}/audit").json()["events"]
    return [(event["action"], event["outcome"]) for event in events]


# --- the view ----------------------------------------------------------------------------------


def test_until_hr_sets_them_the_environment_values_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, local_api_test_max_calls=7)
    controls = journey.client.get(f"{API}/budget").json()["controls"]
    assert controls["revision"] == 0 and controls["readable"]
    assert controls["daily_cap_micro_usd"] == 1_000_000
    assert controls["daily_cap_source"] == "environment"
    assert controls["max_calls"] == 7 and controls["max_calls_source"] == "environment"
    assert controls["max_calls_range"] == [1, 200]
    assert controls["calls_used"] is None  # the remote model is not active
    assert controls["lifetime"] == {
        "opening_usage_micro_usd": 0,
        "cap_micro_usd": 1_000_000,
        "max_cap_micro_usd": 10**12,  # D-098: only the technical bound
        "committed_micro_usd": 0,
    }
    # The overview carries the same view.
    assert journey.client.get(API).json()["budget"]["controls"] == controls


# --- daily allowance and call limit -------------------------------------------------------------


def test_hr_sets_both_controls_and_they_persist_for_every_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    saved = _controls(journey, 250_000, 40)
    assert saved.status_code == 200, saved.text
    controls = saved.json()["controls"]
    assert controls["revision"] == 1 and controls["changed_by"] == "hr-admin"
    assert (controls["daily_cap_micro_usd"], controls["daily_cap_source"]) == (250_000, "hr")
    assert (controls["max_calls"], controls["max_calls_source"]) == (40, "hr")
    assert saved.json()["daily"]["cap_micro_usd"] == 250_000
    assert saved.json()["daily_cap_micro_usd"] == 250_000
    assert ("SPENDING_CONTROLS_CHANGED", "applied") in _actions(journey)

    # A restart, or a second service process on the same state database, reads them.
    store = ModelAdminStore(Path(journey.settings.model_admin_db_path))
    assert store.spending_controls().daily_cap_micro_usd == 250_000
    other = ModelSelector(journey.settings, None, store)
    assert other.controlled().budget_daily_cap_micro_usd == 250_000
    assert other.controlled().local_api_test_max_calls == 40

    # A stale view cannot overwrite a newer change.
    stale = _controls(journey, 1_000_000, 200, revision=0)
    assert stale.status_code == 409 and stale.json()["detail"]["code"] == "CONTROLS_CONFLICT"
    assert journey.client.get(f"{API}/budget").json()["controls"]["daily_cap_micro_usd"] == 250_000


@pytest.mark.parametrize(
    ("daily", "calls", "status"),
    [
        (10**12 + 1, 20, 400),  # D-098: above the technical bound (no US$1 ceiling)
        (-1, 20, 400),
        (500_000, 0, 400),
        (500_000, 201, 400),
        (0.5, 20, 422),  # whole micro-USD only
        ("500000", 20, 422),
        (True, 20, 422),
        (500_000, 20.0, 422),
    ],
)
def test_out_of_range_controls_are_refused_and_nothing_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, daily: Any, calls: Any, status: int
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    reply = _controls(journey, daily, calls, revision=0)
    assert reply.status_code == status, reply.text
    if status == 400:
        assert reply.json()["detail"]["code"] == "CONTROLS_INVALID"
    assert journey.client.get(f"{API}/budget").json()["controls"]["revision"] == 0


def test_the_store_itself_refuses_values_beyond_the_hard_bounds(tmp_path: Path) -> None:
    store = ModelAdminStore(tmp_path / "state.sqlite3")
    for daily, calls in ((10**12 + 1, 1), (0, 0), (0, 201)):
        with pytest.raises(ValueError):
            store.set_spending_controls(0, daily, calls, "hr-admin")
    # Even a direct write past the API cannot store more (the table's CHECKs).
    with sqlite3.connect(tmp_path / "state.sqlite3") as db, pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO spending_controls VALUES (1, 1, 1000000000001, 20, 'now', 'someone')"
        )
    assert store.set_spending_controls(0, 0, 1, "hr-admin") == 1
    with pytest.raises(RevisionConflict):
        store.set_spending_controls(0, 0, 1, "hr-admin")


def test_only_hr_from_the_page_may_change_spending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    for session in ("rm-session", "co-session", "director-session"):
        journey.client.cookies.set("clm_session", session)
        for reply in (
            _controls(journey, 500_000, 10, revision=0),
            journey.client.put(LIFETIME, json={"cap_micro_usd": 500_000}),
            journey.client.post(REFRESH),
        ):
            assert reply.status_code == 403, reply.text
    journey.client.cookies.set("clm_session", "hr-session")
    no_origin = TestClient(journey.app)
    no_origin.cookies.set("clm_session", "hr-session")
    for reply in (
        no_origin.put(
            CONTROLS,
            json={"expected_revision": 0, "daily_cap_micro_usd": 500_000, "max_calls": 10},
        ),
        no_origin.put(LIFETIME, json={"cap_micro_usd": 500_000}),
        no_origin.post(REFRESH),
    ):
        assert reply.status_code == 403 and reply.json()["detail"]["code"] == "ORIGIN_REQUIRED"
    assert journey.client.get(f"{API}/budget").json()["controls"]["revision"] == 0
    assert _ledger(journey).status().cap == 1_000_000


def test_a_lost_capability_between_view_and_change_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    loads = {"n": 0}
    original = journey.backend.handler

    def revoke_on_recheck(request: httpx.Request) -> httpx.Response:
        loads["n"] += 1
        if loads["n"] > 1:  # the first load passes, the recheck inside the lock does not
            journey.backend.revoked.add("hr-session")
        return original(request)

    journey.backend.handler = revoke_on_recheck  # type: ignore[method-assign]
    reply = _controls(journey, 500_000, 10, revision=0)
    assert reply.status_code in (401, 403)
    store = ModelAdminStore(Path(journey.settings.model_admin_db_path))
    assert store.spending_controls().revision == 0


def test_spending_changes_are_rate_limited(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(model_admin, "BUDGET_ATTEMPTS", 2)
    journey = Journey(tmp_path, monkeypatch)
    assert _controls(journey, 500_000, 10).status_code == 200
    assert _controls(journey, 400_000, 10).status_code == 200
    limited = _controls(journey, 300_000, 10)
    assert limited.status_code == 429
    assert limited.json()["detail"]["code"] == "BUDGET_RATE_LIMITED"


def test_a_lower_daily_limit_applies_to_the_active_model_at_once_and_keeps_todays_spend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    activation = journey.client.get(API).json()
    revision, qualification = activation["revision"], activation["active"]["qualification_id"]
    assert journey.ask()["answered_by"] == "model"
    _settle_verification()
    spent = _ledger(journey).daily_status().settled_today
    assert spent > 0

    # Below one reservation: the very next call is refused (case-data answer), nothing sent.
    chats = len(journey.openrouter.chats)
    assert _controls(journey, 1_000, 20).status_code == 200
    reply = journey.ask()
    assert reply["answered_by"] == "case_data"
    assert len(journey.openrouter.chats) == chats
    budget = journey.client.get(f"{API}/budget").json()
    assert budget["daily"]["settled_today_micro_usd"] == spent  # never reset
    assert budget["refusal"] == "DAILY_ALLOWANCE_EXHAUSTED"

    # Back up: the same activation answers again; no restart, no new activation, no
    # requalification (the qualification basis does not include these controls).
    basis = qualification_basis()
    # D-098: a raise needs the amount confirmed (and the key's finite limit, checked now).
    assert _controls(journey, 1_000_000, 20).json()["detail"]["code"] == (
        "DAILY_CONFIRMATION_REQUIRED"
    )
    assert _controls(journey, 1_000_000, 20, confirm=1_000_000).status_code == 200
    assert journey.ask()["answered_by"] == "model"
    _settle_verification()
    after = journey.client.get(API).json()
    assert after["revision"] == revision
    assert after["active"]["qualification_id"] == qualification
    assert after["active"]["profile_id"] == OPENROUTER_PROFILE_ID
    remote = next(p for p in after["profiles"] if p["profile_id"] == OPENROUTER_PROFILE_ID)
    assert remote["activation_blockers"] == [] and remote["qualification"]["current"]
    assert qualification_basis() == basis
    assert _ledger(journey).daily_status().settled_today > spent


def test_the_call_limit_changes_without_resetting_the_activations_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    for _ in range(2):
        assert journey.ask()["answered_by"] == "model"
        _settle_verification()
    controls = journey.client.get(f"{API}/budget").json()["controls"]
    assert controls["calls_used"] == 2 and controls["calls_remaining"] == 18

    # Lowered to the calls already made: the next call is refused; the count stays 2.
    assert _controls(journey, 1_000_000, 2).status_code == 200
    assert journey.ask()["answered_by"] == "case_data"
    controls = journey.client.get(f"{API}/budget").json()["controls"]
    assert controls["calls_used"] == 2 and controls["calls_remaining"] == 0

    # Raised: calls resume, counted from the same activation.
    assert _controls(journey, 1_000_000, 3).status_code == 200
    assert journey.ask()["answered_by"] == "model"
    _settle_verification()
    assert journey.ask()["answered_by"] == "case_data"  # 3 of 3
    controls = journey.client.get(f"{API}/budget").json()["controls"]
    assert controls["calls_used"] == 3 and controls["calls_remaining"] == 0


def test_another_process_applies_a_change_on_its_next_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    # A second service process on the same state database and ledger.
    selector = ModelSelector(
        journey.settings,
        None,
        ModelAdminStore(Path(journey.settings.model_admin_db_path)),
        environ={"OPENROUTER_API_KEY": SENTINEL},
        transport=journey.openrouter.transport(),
    )
    active = selector.current()
    assert active.model is not None
    assert active.model._settings.budget_daily_cap_micro_usd == 1_000_000  # noqa: SLF001

    assert _controls(journey, 1_000, 5).status_code == 200  # changed through the first app
    active = selector.current()
    settings = active.model._settings  # noqa: SLF001
    assert settings.budget_daily_cap_micro_usd == 1_000 and settings.local_api_test_max_calls == 5
    assert active.model._inner._daily_cap == 1_000  # noqa: SLF001 - the budget guard's cap


def test_unreadable_controls_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()

    def broken(self: ModelAdminStore) -> Any:
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(ModelAdminStore, "spending_controls", broken)
    chats = len(journey.openrouter.chats)
    assert journey.ask()["answered_by"] == "case_data"
    assert len(journey.openrouter.chats) == chats
    controls = journey.client.get(f"{API}/budget").json()["controls"]
    assert not controls["readable"] and controls["daily_cap_micro_usd"] == 0


def test_the_qualification_honours_the_hr_daily_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    test = journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/connection-test")
    assert test.json()["outcome"] == "passed"
    assert _controls(journey, 0, 20).status_code == 200  # no daily allowance
    # D-098: refused before it starts, since not every paid call fits the daily limit.
    started = journey.start_qualification()
    assert started.status_code == 409, started.text
    assert started.json()["detail"]["code"] == "QUALIFICATION_BUDGET_INSUFFICIENT"
    assert journey.client.get(API).json()["running"] is None
    assert journey.openrouter.chats == []  # no paid call was made


# --- the lifetime cap ---------------------------------------------------------------------------


def test_hr_lowers_and_raises_the_lifetime_cap_within_the_allocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    assert journey.ask()["answered_by"] == "model"
    _settle_verification()
    (ledger_id, opening), calls_before, events_before = _ledger_rows(journey)

    lowered = journey.client.put(LIFETIME, json={"cap_micro_usd": 400_000})
    assert lowered.status_code == 200, lowered.text
    assert lowered.json()["controls"]["lifetime"]["cap_micro_usd"] == 400_000

    # A raise needs the same amount confirmed.
    for body in (
        {"cap_micro_usd": 900_000, "expected_cap_micro_usd": 400_000},
        {"cap_micro_usd": 900_000, "confirm_cap_micro_usd": 1, "expected_cap_micro_usd": 400_000},
    ):
        refused = journey.client.put(LIFETIME, json=body)
        assert refused.status_code == 400
        assert refused.json()["detail"]["code"] == "CAP_CONFIRMATION_REQUIRED"
    # Never beyond the technical bound (D-098: no US$1 ceiling), never below the opening usage.
    for cap in (10**12 + 1, opening - 1):
        refused = journey.client.put(
            LIFETIME,
            json={
                "cap_micro_usd": cap,
                "confirm_cap_micro_usd": cap,
                "expected_cap_micro_usd": 400_000,
            },
        )
        assert refused.status_code in (409, 422)
    assert _ledger(journey).status().cap == 400_000

    key_reads = sum(1 for r in journey.openrouter.requests if r.url.path.endswith("/key"))
    raised = journey.client.put(
        LIFETIME,
        json={
            "cap_micro_usd": 900_000,
            "confirm_cap_micro_usd": 900_000,
            "expected_cap_micro_usd": 400_000,
        },
    )
    assert raised.status_code == 200, raised.text
    # The reconciliation check read the key's usage (GET /key only; nothing was changed).
    key_requests = [r for r in journey.openrouter.requests if r.url.path.endswith("/key")]
    assert len(key_requests) == key_reads + 1 and all(r.method == "GET" for r in key_requests)
    status = _ledger(journey).status()
    assert status.cap == 900_000

    # The same ledger: its id, opening usage, every call and every earlier event are kept.
    (ledger_id_after, opening_after), calls_after, events_after = _ledger_rows(journey)
    assert (ledger_id_after, opening_after) == (ledger_id, opening)
    assert calls_after == calls_before
    assert events_after[: len(events_before)] == events_before
    assert events_after[len(events_before) :] == [("cap_lowered", 400_000), ("cap_raised", 900_000)]
    audited = [a for a in _actions(journey) if a[0] == "LIFETIME_CAP_CHANGED"]
    assert ("LIFETIME_CAP_CHANGED", "applied") in audited and len(audited) >= 3


def test_a_raise_needs_the_ledger_reconciled_with_openrouter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    assert journey.client.put(LIFETIME, json={"cap_micro_usd": 500_000}).status_code == 200
    original = journey.openrouter.handler

    def unaccounted(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/key"):  # usage the ledger has not seen
            data = {"limit": 1.0, "limit_reset": None, "limit_remaining": 0.8, "usage": 0.2}
            return httpx.Response(200, json={"data": data})
        return original(request)

    journey.selector.transport = httpx.MockTransport(unaccounted)
    body = {
        "cap_micro_usd": 800_000,
        "confirm_cap_micro_usd": 800_000,
        "expected_cap_micro_usd": 500_000,
    }
    refused = journey.client.put(LIFETIME, json=body)
    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "RECONCILIATION_REQUIRED"
    assert _ledger(journey).status().cap == 500_000

    # An unreadable key check refuses too.
    journey.selector.transport = httpx.MockTransport(lambda request: httpx.Response(500))
    refused = journey.client.put(LIFETIME, json=body)
    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "PROVIDER_CHECK_FAILED"

    # An open breaker refuses a raise; lowering stays possible.
    journey.selector.transport = journey.openrouter.transport()
    _ledger(journey).open_breaker("reconcile_drift")
    refused = journey.client.put(LIFETIME, json=body)
    assert refused.json()["detail"]["code"] == "RECONCILIATION_REQUIRED"
    assert journey.client.put(LIFETIME, json={"cap_micro_usd": 300_000}).status_code == 200
    assert _ledger(journey).status().cap == 300_000


def test_a_missing_ledger_is_never_created(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    journey = Journey(tmp_path, monkeypatch)
    Path(journey.settings.budget_ledger_path).unlink()
    refused = journey.client.put(
        LIFETIME,
        json={
            "cap_micro_usd": 500_000,
            "confirm_cap_micro_usd": 500_000,
            "expected_cap_micro_usd": 1_000_000,
        },
    )
    assert refused.status_code == 409 and refused.json()["detail"]["code"] == "LEDGER_UNAVAILABLE"
    assert not Path(journey.settings.budget_ledger_path).exists()
    assert journey.client.get(f"{API}/budget").json()["controls"]["lifetime"] is None


# --- the provider limit -------------------------------------------------------------------------


def test_refresh_reads_the_key_limit_and_makes_no_inference_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    remote_test.forget_provider()  # the reading is process memory; start from none
    assert journey.client.get(f"{API}/budget").json()["provider"] is None
    refreshed = journey.client.post(REFRESH)
    assert refreshed.status_code == 200, refreshed.text
    provider = refreshed.json()["provider"]
    assert provider["passed"] and provider["remaining_micro_usd"] == 1_000_000
    assert provider["checked_at"]
    assert journey.openrouter.chats == []
    assert all(r.method == "GET" for r in journey.openrouter.requests)
    assert SENTINEL not in refreshed.text
    assert ("PROVIDER_LIMITS_REFRESHED", "passed") in _actions(journey)
    # The effective allowance is the strictest of the three limits.
    view = refreshed.json()
    assert view["effective_remaining_micro_usd"] == min(
        view["daily"]["remaining_micro_usd"],
        view["ledger"]["headroom_micro_usd"],
        provider["remaining_micro_usd"],
    )


def test_every_d096_refusal_message_is_one_the_page_may_show() -> None:
    """The page shows only fixed messages it lists (aiAssistant.ts); a missing one would read as
    a generic error."""

    page = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "aiAssistant.ts").read_text(
        encoding="utf-8"
    )
    codes = (
        "CONTROLS_INVALID",
        "CONTROLS_CONFLICT",
        "BUDGET_RATE_LIMITED",
        "LEDGER_UNAVAILABLE",
        "CAP_OUT_OF_RANGE",
        "CAP_CONFIRMATION_REQUIRED",
        "RECONCILIATION_REQUIRED",
        "PROVIDER_CHECK_FAILED",
    )
    for code in codes:
        assert f'"{model_admin.MESSAGES[code]}"' in page, code


def test_without_model_management_no_spending_change_is_made_unaudited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QG D-096 F2: with no model state database there is no audit history, so nothing may
    change (the lifetime cap included) and no refresh runs."""

    journey = Journey(tmp_path, monkeypatch, model_profiles_file="")
    assert journey.selector.store is None
    for reply in (
        _controls(journey, 500_000, 10, revision=0),
        journey.client.put(LIFETIME, json={"cap_micro_usd": 500_000}),
        journey.client.put(
            LIFETIME, json={"cap_micro_usd": 900_000, "confirm_cap_micro_usd": 900_000}
        ),
        journey.client.post(REFRESH),
    ):
        assert reply.status_code == 409, reply.text
        assert reply.json()["detail"]["code"] == "MODEL_MANAGEMENT_OFF"
    assert _ledger(journey).status().cap == 1_000_000
    assert journey.openrouter.requests == []


def test_a_late_reader_never_puts_an_older_limit_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QG D-096 R2: a request that read the controls just before an HR change must not apply
    them after the change (the read happens inside the lock that applies them)."""

    import threading

    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    selector = journey.selector
    store = selector.store
    assert store is not None
    store.set_spending_controls(0, 1_000_000, 20, "hr-admin")  # revision 1: US$1.00
    real = ModelAdminStore.spending_controls
    reading, release = threading.Event(), threading.Event()
    first = threading.Event()

    def slow_first_read(self: ModelAdminStore) -> Any:
        value = real(self)
        if not first.is_set():
            first.set()
            reading.set()
            release.wait(5)  # read, then stall before applying
        return value

    monkeypatch.setattr(ModelAdminStore, "spending_controls", slow_first_read)
    selector._controls_applied = None  # noqa: SLF001 - force both syncs to apply
    late = threading.Thread(target=selector.sync_controls)
    late.start()
    assert reading.wait(5)
    store.set_spending_controls(1, 10_000, 20, "hr-admin")  # revision 2: US$0.01
    change = threading.Thread(target=selector.sync_controls)
    change.start()
    change.join(0.5)  # without the fix this applies at once; with it, it waits for the read
    release.set()
    late.join(5)
    change.join(5)
    model = selector._active.model  # noqa: SLF001 - as left by the two syncs, not re-synced
    assert model._inner._daily_cap == 10_000  # noqa: SLF001 - the newer, lower limit holds
    assert model._settings.budget_daily_cap_micro_usd == 10_000  # noqa: SLF001
