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
            _failed(_gates(G_7=(False, {"cut_short_rate": 0.5}))),
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
    body = {"cap_micro_usd": 3_000_000, "confirm_cap_micro_usd": 3_000_000}
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
