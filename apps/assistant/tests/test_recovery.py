"""D-098: the AI Models page's recovery view, the paid-qualification confirmation, and a
qualification that outlives the HR session that started it. Offline: mock OpenRouter, fake CLM
backend, no paid call."""

import sqlite3
import threading
from pathlib import Path
from typing import Any

import pytest

from ai_assistant import model_admin
from ai_assistant.model_admin import (
    CASE_DATA_ONLY_ID,
    HEALTHY,
    OPERATOR_REQUIRED,
    POLICY_BLOCKED,
    QUALIFICATION_REQUIRED,
    RECOVERABLE_BY_HR,
    TEMPORARILY_UNAVAILABLE,
    ModelSelector,
    diagnose_qualification,
    diagnose_service,
)
from ai_assistant.model_admin_store import ModelAdminStore, RevisionConflict
from ai_assistant.model_catalog import BASELINE_ID, OPENROUTER_FAST_PROFILE_ID, load_catalogue
from ai_assistant.model_profiles import OPENROUTER_PROFILE_ID
from ai_assistant.model_qualification import qualification_basis
from tests.test_model_management import API, ThreadRun
from tests.test_remote_test import SENTINEL, Journey, _settle_verification, wait_for

# --- classification (pure) ----------------------------------------------------------------------


def _run(code: str, **extra: Any) -> dict[str, Any]:
    return {"status": "failed", "code": code, "summary": extra.get("summary") or {}}


@pytest.mark.parametrize(
    ("code", "category", "action", "retryable"),
    [
        ("GATES_FAILED:G-3", POLICY_BLOCKED, "CONTACT_IT", False),
        ("GATES_FAILED:G-6", OPERATOR_REQUIRED, "CONTACT_IT", False),
        ("GATES_FAILED:G-7", OPERATOR_REQUIRED, "CONTACT_IT", False),
        ("GATES_FAILED:G-8", OPERATOR_REQUIRED, "CONTACT_OPERATOR", False),
        ("GATES_FAILED:G-2", TEMPORARILY_UNAVAILABLE, "RUN_QUALIFICATION", True),
        ("CANCELLED", QUALIFICATION_REQUIRED, "RUN_QUALIFICATION", True),
        ("PROCESS_EXITED", TEMPORARILY_UNAVAILABLE, "RUN_QUALIFICATION", True),
        ("REMOTE_MANIFEST_MISSING", OPERATOR_REQUIRED, "CONTACT_IT", False),
        ("SOMETHING_NEW", OPERATOR_REQUIRED, "CONTACT_OPERATOR", False),
    ],
)
def test_each_failed_qualification_gets_one_category_and_action(
    code: str, category: str, action: str, retryable: bool
) -> None:
    diagnosis = diagnose_qualification(_run(code))
    assert diagnosis is not None
    assert (diagnosis["category"], diagnosis["action"], diagnosis["retryable"]) == (
        category,
        action,
        retryable,
    )


def test_a_safety_gate_is_never_retryable_even_beside_a_retryable_one() -> None:
    diagnosis = diagnose_qualification(_run("GATES_FAILED:G-2,G-3"))
    assert diagnosis is not None
    assert diagnosis["category"] == POLICY_BLOCKED and not diagnosis["retryable"]
    assert [f["gate"] for f in diagnosis["findings"]] == ["G-2", "G-3"]


def test_a_failed_connection_gate_is_explained_by_its_preflight_checks() -> None:
    connection = {
        "checks": [
            {"check": "key.status", "ok": True, "detail": "x"},
            {"check": "ledger.daily_room_for_one_call", "ok": False, "detail": "x"},
        ]
    }
    diagnosis = diagnose_qualification(_run("GATES_FAILED:G-1", summary={"connection": connection}))
    assert diagnosis is not None
    assert diagnosis["category"] == RECOVERABLE_BY_HR and diagnosis["action"] == "REVIEW_BUDGET"
    assert [f["code"] for f in diagnosis["findings"]] == ["ledger.daily_room_for_one_call"]
    # A changed provider listing is for IT, not a retry.
    connection["checks"].append({"check": "endpoint.price", "ok": False, "detail": "x"})
    diagnosis = diagnose_qualification(_run("GATES_FAILED:G-1", summary={"connection": connection}))
    assert diagnosis is not None and diagnosis["category"] == POLICY_BLOCKED


def test_passed_and_running_runs_need_no_diagnosis() -> None:
    assert diagnose_qualification({"status": "passed", "code": None}) is None
    assert diagnose_qualification({"status": "running", "code": None}) is None
    assert diagnose_qualification(None) is None


def _profile(profile_id: str, *, active: bool, blockers: list[str], run: Any = None) -> Any:
    return {
        "profile_id": profile_id,
        "source": "code",
        "deployment": "openrouter",
        "status": "selectable",
        "active": active,
        "activation_blockers": blockers,
        "qualification": run,
        "previous_pass_current": not blockers,
    }


def test_fast_failing_while_balanced_is_active_keeps_balanced_and_explains_fast() -> None:
    profiles = [
        _profile(OPENROUTER_PROFILE_ID, active=True, blockers=[]),
        _profile(
            OPENROUTER_FAST_PROFILE_ID,
            active=False,
            blockers=["NOT_QUALIFIED"],
            run=_run("GATES_FAILED:G-6"),
        ),
    ]
    budget = {"configured": True, "refusal": None, "controls": {"calls_remaining": 5}}
    view = diagnose_service(
        active={"profile_id": OPENROUTER_PROFILE_ID}, profiles=profiles, budget=budget
    )
    assert view["status"] == HEALTHY and view["remote_active"]
    fast = next(p for p in view["remote_profiles"] if p["profile_id"] == OPENROUTER_FAST_PROFILE_ID)
    assert not fast["qualified"] and fast["state"]["category"] == OPERATOR_REQUIRED
    assert view["other_qualified"] == []


@pytest.mark.parametrize(
    ("refusal", "remaining", "category", "action"),
    [
        ("DAILY_ALLOWANCE_EXHAUSTED", 5, RECOVERABLE_BY_HR, "REVIEW_BUDGET"),
        ("PROVIDER_LIMIT_EXHAUSTED", 5, OPERATOR_REQUIRED, "CONTACT_OPERATOR"),
        ("BREAKER_OPEN:QUARANTINED", 5, OPERATOR_REQUIRED, "CONTACT_OPERATOR"),
        ("PROVIDER_CHECK_FAILED", 5, TEMPORARILY_UNAVAILABLE, "REFRESH_LIMITS"),
        ("CREDENTIAL_MISSING", 5, RECOVERABLE_BY_HR, "ENTER_KEY"),
        (None, 0, RECOVERABLE_BY_HR, "REVIEW_BUDGET"),
    ],
)
def test_what_stops_the_active_remote_model_is_classified(
    refusal: str | None, remaining: int, category: str, action: str
) -> None:
    profiles = [_profile(OPENROUTER_PROFILE_ID, active=True, blockers=[])]
    budget = {"configured": True, "refusal": refusal, "controls": {"calls_remaining": remaining}}
    view = diagnose_service(
        active={"profile_id": OPENROUTER_PROFILE_ID}, profiles=profiles, budget=budget
    )
    assert (view["status"], view["action"]) == (category, action)


def test_an_out_of_date_qualification_reverts_and_asks_for_a_new_one() -> None:
    profiles = [
        _profile("local_baseline", active=True, blockers=[])
        | {"source": "env", "deployment": "local"},
        _profile(OPENROUTER_PROFILE_ID, active=False, blockers=["QUALIFICATION_OUT_OF_DATE"]),
    ]
    budget = {"configured": True, "refusal": None, "controls": {}}
    view = diagnose_service(
        active={"profile_id": "local_baseline", "reverted": "QUALIFICATION_OUT_OF_DATE"},
        profiles=profiles,
        budget=budget,
    )
    assert view["status"] == QUALIFICATION_REQUIRED and view["action"] == "RUN_QUALIFICATION"
    assert not view["remote_active"]


# --- the service: confirmation, duplicates, the session -----------------------------------------


def _cost(journey: Journey) -> dict[str, Any]:
    return dict(journey.client.get(API).json()["recovery"]["qualification_cost"])


def _events(journey: Journey) -> list[dict[str, Any]]:
    return list(journey.client.get(f"{API}/audit").json()["events"])


def test_a_paid_qualification_needs_its_call_count_confirmed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    cost = _cost(journey)
    assert cost["paid_calls"] == 2 and cost["budget_ok"] and cost["call_limit_ok"]
    assert cost["worst_case_ok"]
    assert cost["needed_micro_usd"] == 2 * cost["reservation_micro_usd"]
    for body in (None, {}, {"confirm_paid_calls": 1}, {"confirm_paid_calls": 3}):
        refused = journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/qualifications", json=body)
        assert refused.status_code == 409, body
        assert refused.json()["detail"]["code"] == "PAID_CONFIRMATION_REQUIRED"
    wrong_type = journey.client.post(
        f"{API}/{OPENROUTER_PROFILE_ID}/qualifications", json={"confirm_paid_calls": "2"}
    )
    assert wrong_type.status_code == 422
    assert journey.openrouter.chats == [] and journey.client.get(API).json()["running"] is None
    refusals = [e for e in _events(journey) if e["action"] == "QUALIFICATION_STARTED"]
    assert {e["code"] for e in refusals} == {"PAID_CONFIRMATION_REQUIRED"}


def test_a_qualification_the_call_limit_cannot_finish_is_not_started(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, local_api_test_max_calls=1)
    cost = _cost(journey)
    assert not cost["call_limit_ok"]
    refused = journey.client.post(
        f"{API}/{OPENROUTER_PROFILE_ID}/qualifications",
        json={"confirm_paid_calls": cost["paid_calls"]},
    )
    assert refused.json()["detail"]["code"] == "QUALIFICATION_BUDGET_TOO_LOW"
    assert journey.openrouter.chats == []


class _Held:
    """Launches the run on a thread only when released (a qualification still running)."""

    def __init__(self, journey: Journey) -> None:
        self.release = threading.Event()
        self.launch = journey.selector.launch

        def launch(qualification_id: str) -> ThreadRun:
            def run() -> None:
                self.release.wait(30)
                self.launch(qualification_id).wait()

            return ThreadRun(run)

        journey.selector.launch = launch


def test_a_qualification_outlives_the_session_that_started_it_and_is_never_repeated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    held = _Held(journey)
    calls = _cost(journey)["paid_calls"]
    started = journey.client.post(
        f"{API}/{OPENROUTER_PROFILE_ID}/qualifications", json={"confirm_paid_calls": calls}
    )
    assert started.status_code == 202, started.text
    qualification_id = started.json()["qualification_id"]

    # A second start (another tab, a double click, the other administrator) is refused.
    again = journey.client.post(
        f"{API}/{OPENROUTER_PROFILE_ID}/qualifications", json={"confirm_paid_calls": calls}
    )
    assert again.status_code == 409 and again.json()["detail"]["code"] == "QUALIFICATION_BUSY"

    # The HR session ends (signed in elsewhere, or the backend restarted): the page's poll is
    # refused, and that is recorded once with codes only.
    journey.backend.revoked.add("hr-session")
    for _ in range(3):
        poll = journey.client.get(f"{API}/qualifications/{qualification_id}")
        assert poll.status_code == 401
    journey.backend.revoked.clear()
    refused = [e for e in _events(journey) if e["action"] == "SESSION_REFUSED"]
    assert len(refused) == 1 and refused[0]["profile_id"] == OPENROUTER_PROFILE_ID
    assert refused[0]["actor"] == "unknown"

    # The run carries on; another HR session finds it and its result.
    journey.client.cookies.set("clm_session", "hr2-session")
    assert journey.client.get(API).json()["running"]["qualification_id"] == qualification_id
    held.release.set()
    result = wait_for(journey.client, qualification_id)
    assert result["status"] == "passed"
    # Exactly the manifest's paid calls: nothing was cancelled, restarted or repeated.
    assert len(journey.openrouter.chats) == calls
    _settle_verification()
    texts = [journey.client.get(API).text, journey.client.get(f"{API}/audit").text]
    assert all(SENTINEL not in text for text in texts)


def test_the_overview_shows_recovery_with_no_key_or_case_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    overview = journey.client.get(API)
    recovery = overview.json()["recovery"]
    assert recovery["status"] == QUALIFICATION_REQUIRED and not recovery["remote_active"]
    balanced = next(
        p for p in recovery["remote_profiles"] if p["profile_id"] == OPENROUTER_PROFILE_ID
    )
    assert balanced["state"]["code"] == "NOT_QUALIFIED" and not balanced["previous_pass_current"]
    assert SENTINEL not in overview.text

    journey.activate_remote()
    recovery = journey.client.get(API).json()["recovery"]
    assert recovery["remote_active"] and recovery["status"] == HEALTHY
    balanced = next(
        p for p in recovery["remote_profiles"] if p["profile_id"] == OPENROUTER_PROFILE_ID
    )
    assert balanced["qualified"] and balanced["previous_pass_current"]
    # RM accounts cannot read it.
    journey.client.cookies.set("clm_session", "rm-session")
    assert journey.client.get(API).status_code == 403


def test_a_failed_run_after_a_pass_leaves_the_earlier_pass_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    _settle_verification()
    store = journey.selector.store
    assert store is not None
    passed = store.latest_qualification(OPENROUTER_PROFILE_ID)
    assert passed is not None
    failed = store.begin_qualification(
        OPENROUTER_PROFILE_ID, passed["fingerprint"], passed["basis"], "hr", 0
    )
    store.finish_qualification(failed, "cancelled", "CANCELLED", None)
    overview = journey.client.get(API).json()
    balanced = next(
        p
        for p in overview["recovery"]["remote_profiles"]
        if p["profile_id"] == OPENROUTER_PROFILE_ID
    )
    assert balanced["previous_pass_current"]
    assert balanced["qualification"]["code"] == "CANCELLED"
    # The active model is not replaced by a failed run.
    assert overview["active"]["profile_id"] == OPENROUTER_PROFILE_ID
    assert overview["recovery"]["last_failure"]["code"] == "CANCELLED"


@pytest.mark.parametrize("gate", ["G-3", "G-6", "G-7", "G-8"])
def test_a_safety_or_quality_gate_failure_cannot_be_rerun_until_it_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, gate: str
) -> None:
    """QG F1: re-running the same configuration and code until a run passes would bypass the
    gate, so the server refuses it. A failure under other code (another basis) or another
    configuration (another fingerprint) does not block."""

    journey = Journey(tmp_path, monkeypatch)
    store = journey.selector.store
    assert store is not None
    entry = load_catalogue(journey.settings).get(OPENROUTER_PROFILE_ID)
    assert entry is not None
    for fingerprint, basis in ((entry.fingerprint, "0" * 64), ("f" * 64, qualification_basis())):
        elsewhere = store.begin_qualification(entry.profile_id, fingerprint, basis, "hr", 0)
        store.finish_qualification(elsewhere, "failed", f"GATES_FAILED:{gate}", None)
    calls = _cost(journey)["paid_calls"]
    started = journey.client.post(
        f"{API}/{OPENROUTER_PROFILE_ID}/qualifications", json={"confirm_paid_calls": calls}
    )
    assert started.status_code == 202, started.text
    wait_for(journey.client, started.json()["qualification_id"])

    failed = store.begin_qualification(
        entry.profile_id, entry.fingerprint, qualification_basis(), "hr-admin", 0
    )
    store.finish_qualification(failed, "failed", f"GATES_FAILED:G-2,{gate}", None)
    chats = len(journey.openrouter.chats)
    refused = journey.client.post(
        f"{API}/{OPENROUTER_PROFILE_ID}/qualifications", json={"confirm_paid_calls": calls}
    )
    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "ESCALATION_REQUIRED"
    assert len(journey.openrouter.chats) == chats
    assert journey.client.get(API).json()["running"] is None
    assert ("QUALIFICATION_STARTED", "refused", "ESCALATION_REQUIRED") in [
        (e["action"], e["outcome"], e["code"]) for e in _events(journey)
    ]


def test_a_retryable_failure_can_be_run_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    store = journey.selector.store
    assert store is not None
    entry = load_catalogue(journey.settings).get(OPENROUTER_PROFILE_ID)
    assert entry is not None
    failed = store.begin_qualification(
        entry.profile_id, entry.fingerprint, qualification_basis(), "hr-admin", 0
    )
    store.finish_qualification(failed, "failed", "GATES_FAILED:G-2,G-4", None)
    calls = _cost(journey)["paid_calls"]
    started = journey.client.post(
        f"{API}/{OPENROUTER_PROFILE_ID}/qualifications", json={"confirm_paid_calls": calls}
    )
    assert started.status_code == 202, started.text
    assert wait_for(journey.client, started.json()["qualification_id"])["status"] == "passed"


def test_a_gate_failure_recorded_while_a_start_is_under_way_still_blocks_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QG R2 F1: the block is decided in the start's own transaction, so a run that fails
    after the request's earlier reads still blocks the new run; and an earlier blocking
    failure counts even when a later, different configuration ran in between."""

    journey = Journey(tmp_path, monkeypatch)
    store = journey.selector.store
    assert store is not None
    entry = load_catalogue(journey.settings).get(OPENROUTER_PROFILE_ID)
    assert entry is not None
    calls = _cost(journey)["paid_calls"]
    original = model_admin.qualification_manifest
    done = []

    def fails_meanwhile(*args: Any, **kwargs: Any) -> Any:
        # Between the request's reads and its start, an earlier run of the same
        # configuration ends with an unsafe line (as a concurrent run's process would).
        if not done:
            done.append(True)
            run = store.begin_qualification(
                entry.profile_id, entry.fingerprint, qualification_basis(), "hr-admin", 0
            )
            store.finish_qualification(run, "failed", "GATES_FAILED:G-3", None)
        return original(*args, **kwargs)

    monkeypatch.setattr(model_admin, "qualification_manifest", fails_meanwhile)
    refused = journey.client.post(
        f"{API}/{OPENROUTER_PROFILE_ID}/qualifications", json={"confirm_paid_calls": calls}
    )
    assert refused.status_code == 409, refused.text
    assert refused.json()["detail"]["code"] == "ESCALATION_REQUIRED"
    assert journey.openrouter.chats == []
    # Another fingerprint (IT changed the settings) is not blocked by it...
    assert not store_blocked(store, entry.profile_id, "f" * 64, qualification_basis())
    # ...and switching back after other runs does not clear it.
    other = store.begin_qualification(entry.profile_id, "f" * 64, qualification_basis(), "hr", 0)
    store.finish_qualification(other, "passed", None, None)
    assert store_blocked(store, entry.profile_id, entry.fingerprint, qualification_basis())


def store_blocked(store: Any, profile_id: str, fingerprint: str, basis: str) -> bool:
    try:
        run = store.begin_qualification(
            profile_id, fingerprint, basis, "hr", 0, blocked=model_admin.escalation_gates_failed
        )
    except model_admin.QualificationBlocked:
        return True
    store.finish_qualification(run, "cancelled", "CANCELLED", None)
    return False


# --- D-098 owner decision: GPT-OSS only, no substitute model -------------------------------------


def _restart(journey: Journey, **update: Any) -> Any:
    settings = journey.settings.model_copy(update=update) if update else journey.settings
    return ModelSelector(
        settings,
        journey.baseline,
        ModelAdminStore(Path(journey.settings.model_admin_db_path)),
        environ=journey.selector.environ,
        transport=journey.selector.transport,
    )


def test_an_unusable_gpt_oss_activation_reverts_to_no_model_not_the_local_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    _settle_verification()
    # The answer code changes (as the D-098 ceiling removal does): the qualification is out
    # of date at the next start.
    monkeypatch.setattr(model_admin, "qualification_basis", lambda: "2" * 64)
    restarted = _restart(journey)
    active = restarted.current()
    assert (active.profile_id, active.model, active.reverted) == (
        CASE_DATA_ONLY_ID,
        None,
        "QUALIFICATION_OUT_OF_DATE",
    )
    events = restarted.store.events(5)  # type: ignore[union-attr]
    assert (events[0]["action"], events[0]["code"], events[0]["profile_id"]) == (
        "STARTUP_REVERTED",
        "QUALIFICATION_OUT_OF_DATE",
        OPENROUTER_PROFILE_ID,
    )
    # The running service follows the stored change: case-data answers, no model called
    # (neither GPT-OSS nor the environment baseline), nothing sent to OpenRouter.
    chats, local = len(journey.openrouter.chats), journey.baseline.calls
    for stream in (False, True):
        assert journey.ask(stream=stream)["answered_by"] == "case_data"
    assert (len(journey.openrouter.chats), journey.baseline.calls) == (chats, local)
    overview = journey.client.get(API).json()
    assert overview["active"]["profile_id"] == CASE_DATA_ONLY_ID
    assert overview["active"]["model_id"] is None
    assert overview["recovery"]["status"] == QUALIFICATION_REQUIRED
    # It stays so across another restart, and "no model" is never offered as a rollback
    # target (the earlier last good model, if any, stays).
    again = _restart(journey).current()
    assert (again.profile_id, again.model) == (CASE_DATA_ONLY_ID, None)
    assert overview["last_good"] is None or overview["last_good"]["profile_id"] != (
        CASE_DATA_ONLY_ID
    )


def test_hr_may_still_choose_the_local_baseline_by_hand(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    _settle_verification()
    monkeypatch.setattr(model_admin, "qualification_basis", lambda: "2" * 64)
    _restart(journey).current()
    revision = journey.client.get(API).json()["revision"]
    chosen = journey.client.post(
        f"{API}/{BASELINE_ID}/activate",
        json={"expected_revision": revision, "acknowledge_quality_unscored": True},
    )
    assert chosen.status_code == 200, chosen.text
    assert chosen.json()["active"]["profile_id"] == BASELINE_ID
    actions = [(e["action"], e["outcome"]) for e in _events(journey)]
    assert ("ACTIVATED", "applied") in actions


def test_a_local_profile_still_reverts_to_the_environment_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Local-only configurations keep their D-093 behaviour (an IT profile reverts to the
    environment baseline): the D-098 change is for the GPT-OSS configurations only."""

    journey = Journey(tmp_path, monkeypatch)
    store = journey.selector.store
    assert store is not None
    stored = store.activation(journey.selector.baseline_choice())
    from ai_assistant.model_admin_store import Choice

    store.activate(stored.revision, Choice("lmstudio_qwen3_8b", "0" * 12, None, None), None, "hr")
    active = _restart(journey).current()
    assert active.profile_id == BASELINE_ID and active.reverted is not None


def test_a_failed_run_never_invalidates_the_active_still_valid_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    _settle_verification()
    store = journey.selector.store
    assert store is not None
    entry = load_catalogue(journey.settings).get(OPENROUTER_PROFILE_ID)
    assert entry is not None
    failed = store.begin_qualification(
        entry.profile_id, entry.fingerprint, qualification_basis(), "hr-admin", 0
    )
    store.finish_qualification(failed, "failed", "GATES_FAILED:G-6", None)
    # In this process and after a restart, the activation keeps its own passing run.
    assert journey.ask()["answered_by"] == "model"
    active = _restart(journey).current()
    assert active.profile_id == OPENROUTER_PROFILE_ID and active.reverted is None
    view = journey.client.get(API).json()
    balanced = next(
        p for p in view["recovery"]["remote_profiles"] if p["profile_id"] == OPENROUTER_PROFILE_ID
    )
    # Its activation stays valid; a new activation (or a re-run) is what the failure blocks.
    assert balanced["active"] and balanced["active_qualification_current"]
    assert not balanced["qualified"]
    assert view["recovery"]["remote_active"] and view["recovery"]["issues"] == []


@pytest.mark.parametrize("failure", ["write_fails", "conflicts", "revision_unreadable"])
def test_no_start_up_failure_puts_the_baseline_in_place_of_gpt_oss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """QG R4 F1: the state database cannot store the revert (locked, read-only), keeps
    conflicting, or cannot be read at all at start: the service answers with no model, never
    with the environment baseline (which may be a local LLM)."""

    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    _settle_verification()
    monkeypatch.setattr(model_admin, "qualification_basis", lambda: "2" * 64)
    store = ModelAdminStore(Path(journey.settings.model_admin_db_path))

    def locked(*args: Any, **kwargs: Any) -> Any:
        raise sqlite3.OperationalError("database is locked")

    def conflict(*args: Any, **kwargs: Any) -> Any:
        raise RevisionConflict

    if failure == "write_fails":
        monkeypatch.setattr(store, "activate", locked)
    elif failure == "conflicts":
        monkeypatch.setattr(store, "activate", conflict)
    else:
        monkeypatch.setattr(store, "revision", locked)
    restarted = ModelSelector(
        journey.settings,
        journey.baseline,
        store,
        environ=journey.selector.environ,
        transport=journey.selector.transport,
    )
    for _ in range(2):  # and on the next request too
        active = restarted.current()
        assert (active.profile_id, active.model) == (CASE_DATA_ONLY_ID, None), failure
    assert journey.baseline.calls == 0


def test_a_running_gpt_oss_model_is_kept_when_the_state_cannot_be_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other side: a usable GPT-OSS model already in use is not dropped because the state
    database is briefly unreadable (the existing "keep the current model" rule)."""

    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    store = journey.selector.store
    assert store is not None

    def locked(*args: Any, **kwargs: Any) -> Any:
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(store, "revision", locked)
    assert journey.selector.current().profile_id == OPENROUTER_PROFILE_ID
