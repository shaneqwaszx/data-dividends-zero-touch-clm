"""D-098: AI model qualification lifecycle and HR recovery (mock OpenRouter only; nothing
is spent and no real model is called).

A. a run whose supervising service has gone is closed as interrupted, never restarted.
B. each outcome is classified (technical, budget, configuration, quality, billing); a paid
   run needs its calls confirmed and every call to fit the strictest limit; after a genuine
   quality failure the same configuration is not run again from the UI.
D. decision 6a: technical outcomes keep an earlier pass, a quality failure supersedes it for
   Activate, Rollback, the active model and start-up alike; a GPT-OSS configuration that can
   no longer serve leaves "AI unavailable", never another model.
"""

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from ai_assistant import model_admin
from ai_assistant.model_admin import UNAVAILABLE_ID, ModelSelector, diagnose
from ai_assistant.model_admin_store import ModelAdminStore
from ai_assistant.model_profiles import OPENROUTER_PROFILE_ID
from ai_assistant.model_qualification import qualification_basis
from ai_assistant.remote_test import ledger_file
from tests.test_model_management import API
from tests.test_remote_test import Journey


def _store(journey: Journey) -> ModelAdminStore:
    store = journey.selector.store
    assert store is not None
    return store


def _orphan(journey: Journey, profile_id: str = OPENROUTER_PROFILE_ID) -> str:
    """A running row whose supervisor stopped stamping a minute ago (a restarted service)."""

    qualification_id = _store(journey).begin_qualification(
        profile_id, _full_fingerprint(journey, profile_id), qualification_basis(), "hr-admin", 2
    )
    with sqlite3.connect(journey.settings.model_admin_db_path) as db:
        db.execute(
            "UPDATE qualifications SET started_at = '2026-01-01T00:00:00+00:00',"
            " supervised_at = '2026-01-01T00:00:00+00:00' WHERE qualification_id = ?",
            (qualification_id,),
        )
    return qualification_id


def _full_fingerprint(journey: Journey, profile_id: str) -> str:
    from ai_assistant.model_catalog import load_catalogue

    entry = load_catalogue(journey.settings).get(profile_id)
    assert entry is not None
    return entry.fingerprint


def _events(journey: Journey, action: str) -> list[dict[str, Any]]:
    return [e for e in journey.client.get(f"{API}/audit").json()["events"] if e["action"] == action]


def test_an_unsupervised_run_is_closed_as_interrupted_and_never_restarted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    qualification_id = _orphan(journey)
    launched: list[str] = []
    journey.selector.launch = lambda qid: launched.append(qid)  # type: ignore[assignment,func-returns-value]

    overview = journey.client.get(API).json()
    assert overview["running"] is None
    item = journey.client.get(f"{API}/qualifications/{qualification_id}").json()
    assert item["status"] == "error" and item["code"] == "INTERRUPTED"
    assert launched == []  # nothing is started again
    (event,) = _events(journey, "QUALIFICATION_INTERRUPTED")
    assert event["actor"] == "system" and event["code"] == "INTERRUPTED"
    assert journey.openrouter.chats == []  # no paid call


def test_a_supervised_run_is_left_alone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    journey = Journey(tmp_path, monkeypatch)
    store = _store(journey)
    qualification_id = store.begin_qualification(
        OPENROUTER_PROFILE_ID,
        _full_fingerprint(journey, OPENROUTER_PROFILE_ID),
        qualification_basis(),
        "hr-admin",
        2,
    )
    store.touch(qualification_id)  # a live supervisor's stamp
    assert journey.client.get(API).json()["running"]["qualification_id"] == qualification_id
    assert store.qualification(qualification_id)["status"] == "running"  # type: ignore[index]


def test_an_open_paid_call_marks_the_interruption_billing_uncertain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    qualification_id = _orphan(journey)
    with sqlite3.connect(ledger_file(journey.settings)) as db:
        db.execute(
            "UPDATE ledger_meta SET breaker_open = 1, breaker_code = 'abandoned_call',"
            " breaker_opened_at = 1"
        )
    item = journey.client.get(f"{API}/qualifications/{qualification_id}").json()
    assert item["code"] == "INTERRUPTED_BILLING_UNCERTAIN"


def test_cancel_closes_an_unsupervised_run_at_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    qualification_id = _orphan(journey)
    reply = journey.client.post(f"{API}/qualifications/{qualification_id}/cancel")
    assert reply.status_code == 200
    assert reply.json() == {"qualification_id": qualification_id, "cancel_requested": False}
    assert _store(journey).running_qualification() is None
    assert _store(journey).qualification(qualification_id)["code"] == "INTERRUPTED"  # type: ignore[index]


def test_a_restarted_service_closes_the_previous_services_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    qualification_id = _orphan(journey)
    store = ModelAdminStore(Path(journey.settings.model_admin_db_path))
    ModelSelector(journey.settings, journey.baseline, store)  # the new service's start-up
    assert store.qualification(qualification_id)["code"] == "INTERRUPTED"  # type: ignore[index]


# --- B. classification ------------------------------------------------------------------------


def _gates(**results: bool | tuple[bool, Any]) -> list[dict[str, Any]]:
    gates = []
    for gate, result in results.items():
        passed, value = result if isinstance(result, tuple) else (result, None)
        gates.append(
            {"gate": gate.replace("_", "-"), "passed": passed, "gating": True, "value": value}
        )
    return gates


# G-7 values as the gate records them (capacity verified, prompts inside the bound).
CUT_SHORT_HALF = {
    "capacity": "verified",
    "largest_prompt_bound": 100,
    "prompt_limit": 200,
    "cut_short_rate": 0.5,
}


def _failed(
    gates: list[dict[str, Any]], code: str = "GATES_FAILED:x", **metrics: Any
) -> dict[str, Any]:
    return {"status": "failed", "code": code, "summary": {"gates": gates, "metrics": metrics}}


@pytest.mark.parametrize(
    ("item", "category", "cause", "retryable", "supersedes"),
    [
        ({"status": "passed"}, "passed", "PASSED", False, False),
        ({"status": "cancelled", "code": "CANCELLED"}, "cancelled", "CANCELLED", True, False),
        ({"status": "error", "code": "INTERRUPTED"}, "technical", "INTERRUPTED", True, False),
        (
            {"status": "error", "code": "INTERRUPTED_BILLING_UNCERTAIN"},
            "billing_uncertain",
            "INTERRUPTED_BILLING_UNCERTAIN",
            False,
            False,
        ),
        ({"status": "error", "code": "DEADLINE"}, "technical", "DEADLINE", True, False),
        (
            {"status": "error", "code": "CONFIG_MISMATCH"},
            "configuration",
            "CONFIG_MISMATCH",
            True,
            False,
        ),
        (
            {"status": "error", "code": "REMOTE_MANIFEST_MISSING"},
            "configuration",
            "REMOTE_MANIFEST_MISSING",
            False,
            False,
        ),
        # Budget refusals before sending: shown as budget, not as answer quality.
        (
            _failed(
                _gates(G_6=(False, None), G_8=False),
                fallback_reasons={"budget_refused": 2},
                remote_calls=0,
                remote_calls_verified=0,
            ),
            "budget",
            "CALLS_REFUSED",
            True,
            False,
        ),
        (
            _failed(
                _gates(G_4=False),
                fallback_reasons={"model_unavailable": 1},
                call_errors={"rate_limited": 1},
            ),
            "technical",
            "MODEL_UNAVAILABLE",
            True,
            False,
        ),
        (
            _failed(
                _gates(G_4=False),
                fallback_reasons={"model_unavailable": 1},
                call_errors={"payment": 1},
            ),
            "technical",
            "PROVIDER_REFUSED",
            False,
            False,
        ),
        (
            _failed(_gates(G_8=False), remote_calls=2, remote_calls_verified=1),
            "billing_uncertain",
            "CALLS_NOT_VERIFIED",
            False,
            False,
        ),
        # Genuine answer-quality failures supersede an earlier pass.
        (_failed(_gates(G_3=(False, 1))), "quality", "UNSAFE_LINE", False, True),
        (
            _failed(_gates(G_6=(False, 0.5)), fallback_reasons={"budget_refused": 1}),
            "quality",
            "LOW_LINE_VALIDITY",
            False,
            True,
        ),
        (
            _failed(_gates(G_7=(False, CUT_SHORT_HALF)), answers=2),
            "quality",
            "ANSWERS_CUT_SHORT",
            False,
            True,
        ),
    ],
)
def test_each_outcome_is_classified(
    item: dict[str, Any], category: str, cause: str, retryable: bool, supersedes: bool
) -> None:
    result = diagnose(item)
    assert (result.category, result.cause, result.retryable, result.supersedes_pass) == (
        category,
        cause,
        retryable,
        supersedes,
    )


@pytest.mark.parametrize(
    ("check", "category"),
    [
        ("ledger.breaker_closed_no_open_calls", "billing_uncertain"),
        ("ledger.usage_reconciled", "billing_uncertain"),
        ("ledger.daily_room_for_one_call", "budget"),
        ("key.room_for_one_call", "budget"),
        ("owner.auto_topup_off", "configuration"),
        ("key.limit_set", "configuration"),
        ("endpoint.listing", "technical"),
    ],
)
def test_a_failed_preflight_names_who_can_resolve_it(check: str, category: str) -> None:
    connection = {"checks": [{"check": check, "ok": False}, {"check": "gate.account", "ok": True}]}
    item = {"status": "failed", "code": "CONNECTION_FAILED", "summary": {"connection": connection}}
    assert diagnose(item).category == category
    assert not diagnose(item).supersedes_pass


# --- B. paid start: confirmation, budget and escalation --------------------------------------


def _record(journey: Journey, status: str, code: str | None, summary: dict[str, Any] | None) -> str:
    store = _store(journey)
    qualification_id = store.begin_qualification(
        OPENROUTER_PROFILE_ID,
        _full_fingerprint(journey, OPENROUTER_PROFILE_ID),
        qualification_basis(),
        "hr-admin",
        2,
    )
    store.touch(qualification_id)
    store.finish_qualification(qualification_id, status, code, summary)
    return qualification_id


QUALITY_FAILURE = {"gates": _gates(G_3=(False, 1)), "metrics": {}}
BUDGET_FAILURE = {
    "gates": _gates(G_6=(False, None), G_8=False),
    "metrics": {"fallback_reasons": {"budget_refused": 2}, "remote_calls": 0},
}


def _remote(journey: Journey) -> dict[str, Any]:
    return next(
        p
        for p in journey.client.get(API).json()["profiles"]
        if p["profile_id"] == OPENROUTER_PROFILE_ID
    )


def test_a_paid_run_needs_its_calls_confirmed_and_shows_the_estimate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    assert (
        journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/connection-test").json()["outcome"]
        == "passed"
    )
    estimate = _remote(journey)["paid_qualification"]
    calls = journey.settings.local_api_test_qualification_count
    assert estimate["calls"] == calls and estimate["sufficient"] is True
    assert estimate["estimate_micro_usd"] == calls * estimate["reservation_micro_usd"]
    for body in (None, {}, {"confirm_paid_calls": calls + 1}):
        refused = journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/qualifications", json=body)
        assert refused.status_code == 400
        assert refused.json()["detail"]["code"] == "PAID_CONFIRMATION_REQUIRED"
    assert journey.openrouter.chats == [] and journey.client.get(API).json()["running"] is None
    assert journey.start_qualification().status_code == 202


def test_a_paid_run_waits_for_the_key_limit_check_and_an_unreconciled_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    model_admin.forget_provider()  # the key's own limit has not been read in this process
    refused = journey.start_qualification()
    assert refused.json()["detail"]["code"] == "PROVIDER_LIMIT_NOT_CHECKED"
    journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/connection-test")
    with sqlite3.connect(ledger_file(journey.settings)) as db:
        db.execute(
            "UPDATE ledger_meta SET breaker_open = 1, breaker_code = 'reconcile_drift',"
            " breaker_opened_at = 1"
        )
    refused = journey.start_qualification()
    assert refused.json()["detail"]["code"] == "QUALIFICATION_BILLING_UNRECONCILED"
    assert journey.openrouter.chats == []


def test_after_a_quality_failure_hr_cannot_run_the_same_configuration_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/connection-test")
    _record(journey, "failed", "GATES_FAILED:G-3", QUALITY_FAILURE)
    remote = _remote(journey)
    assert remote["qualification"]["diagnosis"]["category"] == "quality"
    assert remote["activation_blockers"] == ["QUALIFICATION_SUPERSEDED"]
    refused = journey.start_qualification()
    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "QUALIFICATION_ESCALATION_REQUIRED"
    events = _events(journey, "QUALIFICATION_STARTED")
    assert events[0]["code"] == "QUALIFICATION_ESCALATION_REQUIRED"


# --- D. decision 6a and the GPT-OSS-only policy -----------------------------------------------


def test_a_technical_failure_keeps_the_earlier_pass_for_activation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    passed = journey.activate_remote()
    revision = journey.client.get(API).json()["revision"]
    journey.client.post(f"{API}/env_default/activate", json={"expected_revision": revision})
    _record(journey, "failed", "GATES_FAILED:G-6,G-8", BUDGET_FAILURE)
    remote = _remote(journey)
    assert remote["qualification"]["diagnosis"]["category"] == "budget"
    assert remote["activation_blockers"] == []
    assert remote["eligible_qualification"]["qualification_id"] == passed["qualification_id"]
    assert remote["eligible_qualification"]["is_latest"] is False
    revision = journey.client.get(API).json()["revision"]
    applied = journey.client.post(
        f"{API}/{OPENROUTER_PROFILE_ID}/activate",
        json={"expected_revision": revision, "acknowledge_quality_unscored": True},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["active"]["qualification_id"] == passed["qualification_id"]


def test_a_quality_failure_ends_the_active_configuration_and_blocks_its_return(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    assert journey.ask()["answered_by"] == "model"
    _record(journey, "failed", "GATES_FAILED:G-3", QUALITY_FAILURE)
    journey.selector.revalidate()  # what the supervisor does when a run finishes

    overview = journey.client.get(API).json()
    assert overview["active"]["profile_id"] == UNAVAILABLE_ID
    assert overview["active"]["unavailable"] is True
    assert overview["active"]["reverted"] == "QUALIFICATION_SUPERSEDED"
    (event,) = _events(journey, "QUALIFICATION_SUPERSEDED")
    assert event["outcome"] == "reverted" and event["profile_id"] == OPENROUTER_PROFILE_ID
    sent = len(journey.openrouter.chats)
    assert journey.ask()["answered_by"] == "case_data"  # labelled case data, no model
    assert len(journey.openrouter.chats) == sent
    assert journey.baseline.calls == 0  # the local baseline never stood in

    revision = overview["revision"]
    activate = journey.client.post(
        f"{API}/{OPENROUTER_PROFILE_ID}/activate",
        json={"expected_revision": revision, "acknowledge_quality_unscored": True},
    )
    assert activate.status_code == 409 and activate.json()["detail"]["code"] == "NOT_QUALIFIED"
    # The last good model is the baseline (never "AI unavailable"); HR may choose it by hand.
    assert overview["last_good"]["profile_id"] == "env_default"
    rollback = journey.client.post(f"{API}/rollback", json={"expected_revision": revision})
    assert rollback.status_code == 200, rollback.text
    assert rollback.json()["active"]["profile_id"] == "env_default"
    assert rollback.json()["last_good"] is None  # "AI unavailable" is never a rollback target


def test_rollback_to_a_superseded_configuration_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    revision = journey.client.get(API).json()["revision"]
    journey.client.post(f"{API}/env_default/activate", json={"expected_revision": revision})
    _record(journey, "failed", "GATES_FAILED:G-3", QUALITY_FAILURE)
    overview = journey.client.get(API).json()
    assert overview["last_good"]["profile_id"] == OPENROUTER_PROFILE_ID
    rollback = journey.client.post(
        f"{API}/rollback",
        json={"expected_revision": overview["revision"], "acknowledge_quality_unscored": True},
    )
    assert rollback.status_code == 409 and rollback.json()["detail"]["code"] == "NOT_QUALIFIED"


def test_start_up_keeps_ai_unavailable_and_never_substitutes_the_local_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    # The answer code changed (as D-098's own budget changes do): the pass is out of date.
    monkeypatch.setattr(model_admin, "qualification_basis", lambda: "0" * 64)
    store = ModelAdminStore(Path(journey.settings.model_admin_db_path))
    selector = ModelSelector(journey.settings, journey.baseline, store)
    assert selector.current().profile_id == UNAVAILABLE_ID
    assert selector.current().model is None
    assert selector.current().reverted == "QUALIFICATION_OUT_OF_DATE"
    events = [e for e in store.events(50) if e["action"] == "STARTUP_REVERTED"]
    assert events and events[0]["profile_id"] == OPENROUTER_PROFILE_ID
    # A second start-up stays unavailable (it is stored, not recomputed into the baseline).
    again = ModelSelector(journey.settings, journey.baseline, store)
    assert again.current().profile_id == UNAVAILABLE_ID


# --- item 9: every fixed refusal message is one the browser may show --------------------------


def test_every_model_management_message_is_in_the_browser_safe_list() -> None:
    import json as _json

    source = (
        Path(__file__).resolve().parents[2] / "frontend" / "src" / "aiAssistant.ts"
    ).read_text(encoding="utf-8")
    block = source.split("const SAFE_ERROR_MESSAGES = new Set([", 1)[1].split("]);", 1)[0]
    shown = {
        _json.loads(line.strip().rstrip(","))
        for line in block.splitlines()
        if line.strip().startswith('"')
    }
    missing = sorted(set(model_admin.MESSAGES.values()) - shown)
    assert missing == []


# --- C. flexible daily and lifetime limits ---------------------------------------------------

CONTROLS = f"{API}/budget/controls"
LIFETIME = f"{API}/budget/lifetime-cap"


def _key(journey: Journey, limit: float | None, remaining: float | None) -> None:
    """The OpenRouter key's own limit as /key reports it (a mock; nothing is changed there)."""

    import httpx

    original = journey.openrouter.handler

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/key"):
            data = {"limit": limit, "limit_reset": None, "limit_remaining": remaining, "usage": 0}
            journey.openrouter.requests.append(request)
            return httpx.Response(200, json={"data": data})
        return original(request)

    journey.selector.transport = httpx.MockTransport(handler)


def _daily(journey: Journey, daily: int, confirm: int | None = None) -> Any:
    revision = journey.client.get(f"{API}/budget").json()["controls"]["revision"]
    body: dict[str, Any] = {
        "expected_revision": revision,
        "daily_cap_micro_usd": daily,
        "max_calls": 20,
    }
    if confirm is not None:
        body["confirm_daily_cap_micro_usd"] = confirm
    return journey.client.put(CONTROLS, json=body)


def test_hr_raises_the_daily_limit_above_one_dollar_only_confirmed_with_a_finite_key_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    _key(journey, None, None)  # a key with no limit is never permission to spend more
    assert _daily(journey, 3_000_000).json()["detail"]["code"] == "DAILY_CONFIRMATION_REQUIRED"
    refused = _daily(journey, 3_000_000, confirm=3_000_000)
    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "PROVIDER_LIMIT_REQUIRED"
    assert journey.client.get(f"{API}/budget").json()["controls"]["revision"] == 0

    _key(journey, 5.0, 5.0)  # a finite, never-resetting key limit (read, never changed)
    applied = _daily(journey, 3_000_000, confirm=3_000_000)
    assert applied.status_code == 200, applied.text
    view = applied.json()
    assert view["controls"]["daily_cap_micro_usd"] == 3_000_000
    assert view["daily"]["cap_micro_usd"] == 3_000_000
    # Lowering needs no confirmation and no provider check.
    assert _daily(journey, 500_000).status_code == 200
    assert all(r.method == "GET" for r in journey.openrouter.requests)
    assert journey.openrouter.chats == []


def test_the_strictest_limit_wins_and_a_higher_daily_limit_cannot_bypass_the_lifetime_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    _key(journey, 5.0, 5.0)
    assert _daily(journey, 4_000_000, confirm=4_000_000).status_code == 200
    journey.client.post(f"{API}/budget/provider-refresh")
    view = journey.client.get(f"{API}/budget").json()
    # Daily US$4, key US$5, lifetime cap US$1 (the ledger): US$1 is what may be spent.
    assert view["daily"]["remaining_micro_usd"] == 4_000_000
    assert view["ledger"]["headroom_micro_usd"] == 1_000_000
    assert view["effective_remaining_micro_usd"] == 1_000_000


def test_hr_raises_the_lifetime_cap_above_one_dollar_keeping_every_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ai_assistant.budget import BudgetLedger

    journey = Journey(tmp_path, monkeypatch)
    _key(journey, None, None)
    body = {
        "cap_micro_usd": 3_000_000,
        "confirm_cap_micro_usd": 3_000_000,
        "expected_cap_micro_usd": 1_000_000,
    }
    refused = journey.client.put(LIFETIME, json=body)
    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "PROVIDER_LIMIT_REQUIRED"
    ledger = BudgetLedger.open(Path(journey.settings.budget_ledger_path))
    assert ledger.status().cap == 1_000_000

    _key(journey, 5.0, 5.0)
    raised = journey.client.put(LIFETIME, json=body)
    assert raised.status_code == 200, raised.text
    assert ledger.status().cap == 3_000_000
    assert ledger.status().opening_usage == 0  # nothing reset
    audited = [
        e
        for e in journey.client.get(f"{API}/audit").json()["events"]
        if e["action"] == "LIFETIME_CAP_CHANGED"
    ]
    assert audited[0]["code"] == "RAISED_TO_3000000_MICRO_USD"
    assert [e["code"] for e in audited if e["outcome"] == "refused"] == [
        "PROVIDER_LIMIT_REQUIRED:key.limit_set,key.limit_finite"
    ]


def test_the_preflight_needs_a_finite_key_limit_but_no_us1_allocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import httpx

    from ai_assistant.remote_test import connection_check
    from tests.test_remote_test import SENTINEL, listing

    journey = Journey(tmp_path, monkeypatch)

    def key(limit: float | None, remaining: float | None) -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/key"):
                data = {
                    "limit": limit,
                    "limit_reset": None,
                    "limit_remaining": remaining,
                    "usage": 0,
                }
                return httpx.Response(200, json={"data": data})
            return journey.openrouter.handler(request)

        return httpx.MockTransport(handler)

    environ = {"OPENROUTER_API_KEY": SENTINEL}
    # A US$5 key limit: refused before D-098 (key.limit_within_allocation), allowed now.
    roomy = connection_check(
        journey.settings, environ=environ, transport=key(5.0, 5.0), fetch=listing
    )
    assert roomy["outcome"] == "passed", roomy
    names = {c["check"] for c in roomy["checks"]}
    assert "key.limit_finite" in names and "ledger.cap_above_opening" in names
    assert "key.limit_within_allocation" not in names
    # No key limit at all: the preflight fails, so the model refuses every call before sending.
    unbounded = connection_check(
        journey.settings, environ=environ, transport=key(None, None), fetch=listing
    )
    assert unbounded["outcome"] == "failed"
    assert {"key.limit_set", "key.limit_finite"} <= {
        c["check"] for c in unbounded["checks"] if not c["ok"]
    }
    assert journey.openrouter.chats == []


def test_an_earlier_database_keeps_its_controls_and_loses_only_the_us1_check(
    tmp_path: Path,
) -> None:
    path = tmp_path / "admin.sqlite3"
    with sqlite3.connect(path) as db:  # the D-096 table, as an earlier version made it
        db.execute(
            "CREATE TABLE spending_controls (id INTEGER PRIMARY KEY CHECK (id = 1),"
            " revision INTEGER NOT NULL CHECK (revision >= 1), daily_cap_micro_usd INTEGER"
            " NOT NULL CHECK (daily_cap_micro_usd BETWEEN 0 AND 1000000), max_calls INTEGER"
            " NOT NULL CHECK (max_calls BETWEEN 1 AND 200), changed_at TEXT NOT NULL,"
            " changed_by TEXT NOT NULL)"
        )
        db.execute(
            "INSERT INTO spending_controls VALUES (1, 4, 250000, 30, '2026-10-28T01:00:00+00:00',"
            " 'hr-admin')"
        )
    store = ModelAdminStore(path)
    kept = store.spending_controls()
    assert (kept.revision, kept.daily_cap_micro_usd, kept.max_calls, kept.changed_by) == (
        4,
        250_000,
        30,
        "hr-admin",
    )
    assert store.set_spending_controls(4, 5_000_000, 30, "hr-admin") == 5
    ModelAdminStore(path)  # opening it again changes nothing more
    assert store.spending_controls().daily_cap_micro_usd == 5_000_000


# --- QG R-1: no supervisor needed for decision 6a ---------------------------------------------


def test_a_quality_failure_stops_the_active_model_in_every_process_without_a_supervisor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    # A second service process on the same state database, already serving the configuration.
    from tests.test_remote_test import SENTINEL

    other = ModelSelector(
        journey.settings,
        journey.baseline,
        ModelAdminStore(Path(journey.settings.model_admin_db_path)),
        environ={"OPENROUTER_API_KEY": SENTINEL},
        transport=journey.openrouter.transport(),
    )
    assert other.current().profile_id == OPENROUTER_PROFILE_ID
    # The run finishes with nobody supervising it (a restarted service, an orphaned process):
    # no revalidate() call, no activation change.
    _record(journey, "failed", "GATES_FAILED:G-3", QUALITY_FAILURE)
    sent = len(journey.openrouter.chats)
    assert journey.ask()["answered_by"] == "case_data"  # the very next answer
    assert len(journey.openrouter.chats) == sent
    assert other.current().profile_id == UNAVAILABLE_ID
    overview = journey.client.get(API).json()
    assert overview["active"]["profile_id"] == UNAVAILABLE_ID
    remote = _remote(journey)
    assert not remote["active"] and remote["activation_blockers"] == ["QUALIFICATION_SUPERSEDED"]


def test_a_technical_failure_never_stops_the_active_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    _record(journey, "failed", "GATES_FAILED:G-6,G-8", BUDGET_FAILURE)
    _record(journey, "error", "INTERRUPTED", None)
    assert journey.ask()["answered_by"] == "model"
    assert journey.client.get(API).json()["active"]["profile_id"] == OPENROUTER_PROFILE_ID


# --- F1: lifetime-cap compare-and-set at the ledger write (ported from PR #128 Z7) ----------


def test_an_hr_raise_never_overwrites_an_operator_lowering_made_in_between(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deterministic interleaving: HR reads cap US$1.00 and asks for US$3.00; while its free
    preflight runs, the operator's script lowers the cap to US$0.40. HR's raise is refused
    and the operator's US$0.40 stays; spend, calls and the daily view are unchanged."""

    from ai_assistant.budget import BudgetLedger
    from tests.test_remote_test import _settle_verification

    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    assert journey.ask()["answered_by"] == "model"
    _settle_verification()
    path = Path(journey.settings.budget_ledger_path)
    before = BudgetLedger.open(path)
    status_before = before.status()
    calls_before = before.closed_calls_after(0)
    daily_before = before.daily_status().settled_today
    _key(journey, 5.0, 5.0)
    original = model_admin.preflight

    def operator_lowers_during_preflight(*args: Any, **kwargs: Any) -> Any:
        BudgetLedger.open(path).set_cap(400_000)  # scripts/budget_ledger.py set-cap
        return original(*args, **kwargs)

    monkeypatch.setattr(model_admin, "preflight", operator_lowers_during_preflight)
    raised = journey.client.put(
        LIFETIME,
        json={
            "cap_micro_usd": 3_000_000,
            "confirm_cap_micro_usd": 3_000_000,
            "expected_cap_micro_usd": 1_000_000,
        },
    )
    assert raised.status_code == 409, raised.text
    assert raised.json()["detail"]["code"] == "CONTROLS_CONFLICT"
    after = BudgetLedger.open(path)
    status = after.status()
    assert status.cap == 400_000  # the operator's lowering stands
    assert (status.committed, status.opening_usage, status.open_calls) == (
        status_before.committed,
        status_before.opening_usage,
        status_before.open_calls,
    )
    assert after.closed_calls_after(0) == calls_before
    assert after.daily_status().settled_today == daily_before
    with sqlite3.connect(path) as db:
        events = [row[0] for row in db.execute("SELECT event FROM operator_events")]
    assert "cap_lowered" in events and "cap_raised" not in events
    audited = [
        e
        for e in journey.client.get(f"{API}/audit").json()["events"]
        if e["action"] == "LIFETIME_CAP_CHANGED"
    ]
    assert audited[0]["outcome"] == "refused" and audited[0]["code"] == "CONTROLS_CONFLICT"


def test_a_raise_from_a_stale_view_is_refused_before_any_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ai_assistant.budget import BudgetLedger

    journey = Journey(tmp_path, monkeypatch)
    _key(journey, 5.0, 5.0)
    for expected in (None, 999_999):
        body: dict[str, Any] = {"cap_micro_usd": 2_000_000, "confirm_cap_micro_usd": 2_000_000}
        if expected is not None:
            body["expected_cap_micro_usd"] = expected
        refused = journey.client.put(LIFETIME, json=body)
        assert refused.status_code == 409
        assert refused.json()["detail"]["code"] == "CONTROLS_CONFLICT"
    assert BudgetLedger.open(Path(journey.settings.budget_ledger_path)).status().cap == 1_000_000


def test_the_ledger_compare_and_set_itself(tmp_path: Path) -> None:
    from ai_assistant.budget import BudgetLedger, LedgerError

    path = tmp_path / "ledger.sqlite3"
    BudgetLedger.initialise(
        path, cap_micro_usd=1_000_000, opening_usage_micro_usd=0, key_alias="key-01"
    )
    ledger = BudgetLedger.open(path)
    with pytest.raises(LedgerError) as raised:
        ledger.set_cap(2_000_000, allow_raise=True, confirm=2_000_000, expected=900_000)
    assert raised.value.code == "CAP_CHANGED"
    assert ledger.status().cap == 1_000_000
    ledger.set_cap(2_000_000, allow_raise=True, confirm=2_000_000, expected=1_000_000)
    assert ledger.status().cap == 2_000_000


# --- F2: GPT-OSS never stood in for by another model (ported from PR #128 R4/R5) -----------


def _selector(journey: Journey, store: Any) -> ModelSelector:
    from tests.test_remote_test import SENTINEL

    return ModelSelector(
        journey.settings,
        journey.baseline,
        store,
        environ={"OPENROUTER_API_KEY": SENTINEL},
        transport=journey.openrouter.transport(),
    )


class _FlakyStore(ModelAdminStore):
    """A store whose reads or writes fail on demand (a locked or failing state database)."""

    fail_reads = False
    fail_activate = False
    fail_record = False
    conflicts = 0

    def revision(self) -> int:
        if self.fail_reads:
            raise sqlite3.OperationalError("database is locked")
        return super().revision()

    def activation(self, baseline: Any) -> Any:
        if self.fail_reads:
            raise sqlite3.OperationalError("database is locked")
        return super().activation(baseline)

    def activate(self, *args: Any, **kwargs: Any) -> int:
        from ai_assistant.model_admin_store import RevisionConflict

        if self.conflicts > 0:
            self.conflicts -= 1
            raise RevisionConflict
        if self.fail_activate:
            raise sqlite3.OperationalError("database is locked")
        return super().activate(*args, **kwargs)

    def record(self, **kwargs: Any) -> None:
        if self.fail_record:
            raise sqlite3.OperationalError("disk I/O error")
        super().record(**kwargs)


def _make_gpt_oss_unusable(journey: Journey, monkeypatch: pytest.MonkeyPatch) -> None:
    journey.activate_remote()
    monkeypatch.setattr(model_admin, "qualification_basis", lambda: "0" * 64)


def test_an_unreadable_state_database_at_start_up_gives_no_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    store = _FlakyStore(Path(journey.settings.model_admin_db_path))
    store.fail_reads = True
    selector = _selector(journey, store)
    active = selector.current()
    assert active.profile_id == UNAVAILABLE_ID and active.model is None
    assert journey.baseline.calls == 0
    store.fail_reads = False  # readable again: the stored (valid) activation is served
    assert selector.current().profile_id == OPENROUTER_PROFILE_ID


def test_a_revert_that_cannot_be_stored_gives_no_model_and_is_retried_and_audited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    _make_gpt_oss_unusable(journey, monkeypatch)
    store = _FlakyStore(Path(journey.settings.model_admin_db_path))
    store.fail_activate = True
    selector = _selector(journey, store)
    active = selector.current()
    assert active.profile_id == UNAVAILABLE_ID and active.model is None
    assert active.revision == -1  # retried on the next request
    assert store.activation(selector.baseline_choice()).active_profile_id == OPENROUTER_PROFILE_ID
    store.fail_activate = False
    active = selector.current()
    assert active.profile_id == UNAVAILABLE_ID and active.revision > 0  # now stored
    assert store.activation(selector.baseline_choice()).active_profile_id == UNAVAILABLE_ID
    events = [e for e in store.events(20) if e["action"] == "STARTUP_REVERTED"]
    assert len(events) == 1 and events[0]["code"] == "QUALIFICATION_OUT_OF_DATE"
    assert journey.baseline.calls == 0


def test_repeated_conflicts_never_stand_in_the_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    _make_gpt_oss_unusable(journey, monkeypatch)
    store = _FlakyStore(Path(journey.settings.model_admin_db_path))
    store.conflicts = 3
    selector = _selector(journey, store)
    active = selector.current()
    assert active.profile_id == UNAVAILABLE_ID and active.model is None
    assert selector.current().profile_id == UNAVAILABLE_ID  # stored on the next request
    assert store.activation(selector.baseline_choice()).active_profile_id == UNAVAILABLE_ID


def test_a_lost_revert_audit_is_written_once_writes_work_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    _make_gpt_oss_unusable(journey, monkeypatch)
    store = _FlakyStore(Path(journey.settings.model_admin_db_path))
    store.fail_record = True
    selector = _selector(journey, store)
    assert selector.current().profile_id == UNAVAILABLE_ID
    assert not [e for e in store.events(20) if e["action"] == "STARTUP_REVERTED"]
    store.fail_record = False
    selector.current()
    events = [e for e in store.events(20) if e["action"] == "STARTUP_REVERTED"]
    assert len(events) == 1


def test_hr_can_activate_while_a_revert_is_not_yet_stored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The page gets the stored revision (never -1), so Activate is a normal CAS request."""

    journey = Journey(tmp_path, monkeypatch)
    _make_gpt_oss_unusable(journey, monkeypatch)
    store = _FlakyStore(Path(journey.settings.model_admin_db_path))
    store.fail_activate = True
    journey.selector.store = store
    journey.selector._active = journey.selector._unavailable(-1)  # noqa: SLF001
    overview = journey.client.get(API).json()
    assert overview["active"]["profile_id"] == UNAVAILABLE_ID
    assert overview["revision"] == store.revision() >= 0
    store.fail_activate = False
    applied = journey.client.post(
        f"{API}/env_default/activate", json={"expected_revision": overview["revision"]}
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["active"]["profile_id"] == "env_default"


def test_a_local_profile_still_reverts_to_the_baseline_as_documented(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ai_assistant.model_admin_store import Choice
    from ai_assistant.model_catalog import load_catalogue
    from tests.test_model_management import Backend, ModelServer, build_app

    client = build_app(tmp_path, Backend(), ModelServer(), monkeypatch)
    selector: ModelSelector = client.app.state.model_selector  # type: ignore[attr-defined]
    store = selector.store
    assert store is not None
    entry = load_catalogue(selector.settings).get("lmstudio_qwen3_8b")
    assert entry is not None
    # A local profile activated with a qualification from older code: at the next start it
    # is out of date and reverts to the baseline (D-093), not to "AI unavailable".
    qid = store.begin_qualification(entry.profile_id, entry.fingerprint, "old", "hr-admin", 1)
    store.finish_qualification(qid, "passed", None, {"capacity": {"prompt_limit": 1000}})
    choice = Choice(entry.profile_id, entry.fingerprint, qid, 1000)
    store.activate(store.revision(), choice, None, "hr-admin")
    restarted = ModelSelector(selector.settings, None, ModelAdminStore(store._path))  # noqa: SLF001
    assert restarted.current().profile_id == "env_default"


# --- UX parity: the key's own limit, and an exhausted key goes to its owner -----------------


def test_the_spending_view_shows_the_keys_limit_usage_and_reset_never_account_credits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/connection-test")
    provider = journey.client.get(f"{API}/budget").json()["provider"]
    assert provider["limit_micro_usd"] == 1_000_000 and provider["limit_usd"] == "1.000000"
    assert provider["usage_micro_usd"] == 0
    assert provider["limit_reset"] is None  # never resets
    assert provider["account_credits"] is None  # never read
    assert all(r.method == "GET" for r in journey.openrouter.requests)


def test_an_exhausted_key_is_an_owner_action_not_an_hr_budget_setting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    connection = {"checks": [{"check": "key.room_for_one_call", "ok": False}]}
    item = {"status": "failed", "code": "CONNECTION_FAILED", "summary": {"connection": connection}}
    result = diagnose(item)
    assert (result.cause, result.action, result.retryable) == (
        "KEY_LIMIT_EXHAUSTED",
        "ESCALATE_KEY_OWNER",
        False,
    )
    journey = Journey(tmp_path, monkeypatch)
    _key(journey, 1.0, 0.0)  # the key's own limit has no room left
    journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/connection-test")
    refused = journey.start_qualification()
    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "PROVIDER_KEY_LIMIT_EXHAUSTED"
    assert journey.openrouter.chats == []


# --- QG Q-1: an undone activation from "AI unavailable" returns to it, never a stand-in -----


@pytest.mark.parametrize("last_good", ["same", "local"])
def test_an_activation_undone_from_ai_unavailable_returns_to_ai_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, last_good: str
) -> None:
    from ai_assistant.model_admin_store import Choice
    from ai_assistant.model_catalog import load_catalogue

    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    store = _store(journey)
    stored = store.activation(journey.selector.baseline_choice())
    balanced = Choice(
        stored.active_profile_id,
        stored.active_fingerprint,
        stored.active_qualification_id,
        stored.active_prompt_limit,
    )
    if last_good == "same":
        previous = balanced
    else:
        local = load_catalogue(journey.settings).get("lmstudio_qwen3_8b")
        assert local is not None
        previous = Choice(local.profile_id, local.fingerprint, None, None)
    # The stored state is "AI unavailable" (a revert), with that last good model.
    store.activate(stored.revision, Choice(UNAVAILABLE_ID, UNAVAILABLE_ID), previous, "system")
    assert journey.selector.current().profile_id == UNAVAILABLE_ID

    # HR activates Balanced; the build fails after the compare-and-set (for example a quality
    # failure finishing during the activation's connection test, or the ledger going away).
    original = journey.selector._build_stored  # noqa: SLF001
    calls = {"n": 0}

    def fail_once(activation: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1 and activation.active_profile_id == OPENROUTER_PROFILE_ID:
            return None, "LEDGER_UNAVAILABLE"
        return original(activation)

    monkeypatch.setattr(journey.selector, "_build_stored", fail_once)
    revision = journey.client.get(API).json()["revision"]
    refused = journey.client.post(
        f"{API}/{OPENROUTER_PROFILE_ID}/activate",
        json={"expected_revision": revision, "acknowledge_quality_unscored": True},
    )
    assert refused.status_code == 409, refused.text
    after = store.activation(journey.selector.baseline_choice())
    assert after.active_profile_id == UNAVAILABLE_ID  # exactly what was stored before
    assert after.last_good_profile_id == previous.profile_id
    assert journey.selector.current().profile_id == UNAVAILABLE_ID
    assert journey.selector.current().model is None
    assert journey.baseline.calls == 0
    (undone,) = _events(journey, "ACTIVATION_UNDONE")
    assert undone["code"] == "LEDGER_UNAVAILABLE"


# --- QG Q-2: a quality failure supersedes a pass whatever explains the run first ------------


@pytest.mark.parametrize(
    ("item", "category"),
    [
        (
            _failed(_gates(G_6=(False, 0.5), G_8=False), remote_calls=2, remote_calls_verified=1),
            "billing_uncertain",
        ),
        (
            _failed(
                _gates(G_7=(False, CUT_SHORT_HALF)),
                fallback_reasons={"budget_refused": 1},
                answers=2,
            ),
            "budget",
        ),
        (
            _failed(
                _gates(G_4=False, G_7=(False, CUT_SHORT_HALF)),
                fallback_reasons={"model_unavailable": 1},
                answers=2,
            ),
            "technical",
        ),
    ],
)
def test_a_quality_failure_supersedes_a_pass_even_behind_another_category(
    item: dict[str, Any], category: str
) -> None:
    result = diagnose(item)
    assert result.category == category  # billing, budget and technical stay distinct
    assert result.supersedes_pass is True and result.retryable is False


def test_billing_alone_never_supersedes_a_pass() -> None:
    item = _failed(_gates(G_8=False), remote_calls=2, remote_calls_verified=1)
    result = diagnose(item)
    assert (result.category, result.supersedes_pass) == ("billing_uncertain", False)


# --- QG Q2-R1: answers cut short by a provider failure mid-answer are technical -------------


def _g7(rate: float) -> dict[str, Any]:
    return {**CUT_SHORT_HALF, "cut_short_rate": rate}


@pytest.mark.parametrize("error", ["timeout", "rate_limited"])
def test_provider_failures_mid_answer_never_take_a_pass_away(error: str) -> None:
    # 10 answers, 2 cut short, both by the provider failing mid-answer (stream_partial).
    item = _failed(
        _gates(G_4=False, G_7=(False, _g7(0.2))),
        answers=10,
        fallback_reasons={"stream_partial": 2},
        call_errors={error: 2},
    )
    result = diagnose(item)
    assert (result.category, result.cause, result.action) == (
        "technical",
        "MODEL_UNAVAILABLE",
        "RETRY_LATER",
    )
    assert result.retryable is True and result.supersedes_pass is False


def test_a_g7_failure_explained_only_by_provider_failures_is_technical() -> None:
    item = _failed(
        _gates(G_7=(False, _g7(0.2))), answers=10, fallback_reasons={"stream_partial": 2}
    )
    result = diagnose(item)
    assert (result.category, result.retryable, result.supersedes_pass) == ("technical", True, False)


def test_genuine_cut_short_answers_beyond_the_provider_failures_still_supersede() -> None:
    # 10 answers, 4 cut short, only 2 by the provider: 20% are the configuration's own.
    item = _failed(
        _gates(G_4=False, G_7=(False, _g7(0.4))),
        answers=10,
        fallback_reasons={"stream_partial": 2},
    )
    result = diagnose(item)
    assert result.category == "technical"  # what HR sees first
    assert result.supersedes_pass is True and result.retryable is False


def test_unverified_capacity_or_an_oversized_prompt_supersedes() -> None:
    for value in (
        {**CUT_SHORT_HALF, "cut_short_rate": 0.0, "capacity": "failed"},
        {**CUT_SHORT_HALF, "cut_short_rate": 0.0, "largest_prompt_bound": 300},
    ):
        result = diagnose(_failed(_gates(G_7=(False, value)), answers=10))
        assert (result.cause, result.supersedes_pass) == ("CAPACITY_NOT_VERIFIED", True)
