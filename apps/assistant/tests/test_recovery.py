"""D-098: the AI Models page's recovery view, the paid-qualification confirmation, and a
qualification that outlives the HR session that started it. Offline: mock OpenRouter, fake CLM
backend, no paid call."""

import threading
from pathlib import Path
from typing import Any

import pytest

from ai_assistant.model_admin import (
    HEALTHY,
    OPERATOR_REQUIRED,
    POLICY_BLOCKED,
    QUALIFICATION_REQUIRED,
    RECOVERABLE_BY_HR,
    TEMPORARILY_UNAVAILABLE,
    diagnose_qualification,
    diagnose_service,
)
from ai_assistant.model_catalog import OPENROUTER_FAST_PROFILE_ID
from ai_assistant.model_profiles import OPENROUTER_PROFILE_ID
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
