"""HR recovery centre: diagnosis of current problems, permitted actions and owner requests.

Pure diagnosis over synthetic overview dicts, then the routes on a disposable Claude journey
(tmp_path ledgers and state databases only; no paid call, no live store).
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from ai_assistant import recovery
from ai_assistant.budget import BudgetLedger
from ai_assistant.model_admin_store import ModelAdminStore, RecoveryRequestRefused

NOW = datetime(2026, 11, 6, 2, 0, tzinfo=UTC)


def _claude(**changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "configured": True,
        "next_reset_at": "2026-11-06T16:00:00+00:00",
        "lifetime_ceiling_micro_usd": 25_000_000,
        "ledger": {
            "breaker_open": False,
            "breaker_code": None,
            "cap_micro_usd": 10_000_000,
            "headroom_micro_usd": 5_000_000,
            "committed_micro_usd": 5_000_000,
        },
        "daily": {"cap_micro_usd": 1_000_000, "remaining_micro_usd": 500_000},
        "credential": {"source": "environment", "status": "configured", "hr_editable": True},
        "reconciliation": {
            "reconciled_at": "2026-10-31T01:42:37+00:00",
            "chat_deadline_at": "2026-11-07T01:42:37+00:00",
            "paid_deadline_at": "2026-11-01T01:42:37+00:00",
            "chat_fresh": True,
            "paid_fresh": False,
            "open_reserved_micro_usd": 0,
            "calls": {"open": 0, "quarantined": 0, "unverified": 0},
        },
    }
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = {**base[key], **value}
        else:
            base[key] = value
    return base


def _overview(claude: dict[str, Any] | None = None, **changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "basis": "abc123",
        "active": {"profile_id": "claude_fast", "unavailable": False, "config_changed": False},
        "last_good": None,
        "running": None,
        "profiles": [
            {
                "profile_id": "claude_fast",
                "display_name": "Claude Sonnet 5.5 Fast",
                "deployment": "anthropic",
                "status": "selectable",
                "qualification": {"status": "passed", "current": True, "finished_at": "x"},
                "eligible_qualification": {"qualification_id": "q1"},
                "activation_blockers": [],
                "connection_test": {"outcome": "passed", "at": "x"},
            }
        ],
        "budget": {"configured": False, "claude": claude or _claude()},
        "anthropic_setup": {"enabled": True, "readiness": None},
    }
    base.update(changes)
    return base


def _listing(**changes: Any) -> dict[str, Any]:
    return {
        "runs": [],
        "prerequisite_recorded": True,
        "marker_readable": True,
        "marker_run_id": None,
        "marker_overridden": False,
        **changes,
    }


def diagnose(overview: dict[str, Any], listing: dict[str, Any] | None = None, **kw: Any) -> Any:
    return recovery.diagnose(
        overview,
        listing=_listing() if listing is None else listing,
        listing_error=kw.get("listing_error"),
        now=kw.get("now", NOW),
        hr_allowed=kw.get("hr_allowed", True),
    )


def problem(view: dict[str, Any], code: str) -> dict[str, Any]:
    found = [p for p in view["problems"] if p["code"] == code]
    assert len(found) == 1, [p["code"] for p in view["problems"]]
    return found[0]


# --- diagnosis -----------------------------------------------------------------------------


def test_paid_window_expired_and_due_soon_offer_reconciliation_with_separate_expiries() -> None:
    view = diagnose(_overview())
    paid = problem(view, "CLAUDE_PAID_WINDOW_EXPIRED")
    due = problem(view, "CLAUDE_RECONCILIATION_DUE_SOON")
    for item in (paid, due):
        action = item["actions"][0]
        assert action["kind"] == "RECONCILE" and action["permitted"]
        assert action["section"] == "spending"
    assert view["healthy"] is True  # chat still answers
    assert view["expiries"]["claude_chat_deadline_at"] == "2026-11-07T01:42:37+00:00"
    assert view["expiries"]["claude_paid_deadline_at"] == "2026-11-01T01:42:37+00:00"
    assert view["expiries"]["qualifications"][0]["current"] is True


def test_chat_window_expired_blocks_and_renewal_is_only_through_reconciliation() -> None:
    claude = _claude(reconciliation={"chat_fresh": False, "paid_fresh": False})
    view = diagnose(_overview(claude), now=NOW + timedelta(days=2))
    item = problem(view, "CLAUDE_CHAT_WINDOW_EXPIRED")
    assert item["severity"] == "blocking" and view["healthy"] is False
    assert [a["kind"] for a in item["actions"]] == ["RECONCILE"]
    assert not item["owner_request_allowed"]


def test_reconciliation_is_not_permitted_while_a_blocker_holds_and_names_it() -> None:
    claude = _claude(
        reconciliation={
            "chat_fresh": False,
            "calls": {"open": 0, "quarantined": 1, "unverified": 2},
        },
        ledger={"breaker_open": True, "breaker_code": "reconcile_drift"},
    )
    view = diagnose(_overview(claude), _listing(prerequisite_recorded=False))
    action = problem(view, "CLAUDE_CHAT_WINDOW_EXPIRED")["actions"][0]
    assert action["permitted"] is False
    assert set(action["blocked_by"]) == {
        "CLAUDE_BREAKER_OPEN",
        "CLAUDE_QUARANTINED_CALLS",
        "CLAUDE_UNVERIFIED_CALLS",
        "CLAUDE_RECONCILIATION_PREREQUISITE",
    }
    # D-110 R8: HR never resets the breaker; only an owner request is offered.
    breaker = problem(view, "CLAUDE_BREAKER_OPEN")
    assert [a["kind"] for a in breaker["actions"]] == ["OWNER_REQUEST"]
    assert breaker["owner_request_allowed"]
    assert {"label": "Breaker code", "value": "reconcile_drift"} in breaker["evidence"]
    # Unverified calls are verified by HR's free Test connection, quarantined ones are not.
    unverified = problem(view, "CLAUDE_UNVERIFIED_CALLS")
    assert unverified["actions"][0]["kind"] == "TEST_CONNECTION"
    assert unverified["actions"][0]["profile_id"] == "claude_fast"
    assert problem(view, "CLAUDE_QUARANTINED_CALLS")["actions"][0]["authority"] == "OWNER"


def test_runs_pending_resolve_and_unresolved() -> None:
    pending = {
        "run_id": "a" * 32,
        "status": "requested",
        "intent_at": "x",
        "resolvable_after": (NOW - timedelta(minutes=1)).isoformat(),
    }
    later = (NOW + timedelta(minutes=5)).isoformat()
    early = {**pending, "run_id": "b" * 32, "resolvable_after": later}
    unresolved = {"run_id": "c" * 32, "status": "unresolved", "reason": "X1"}
    acknowledged = {**unresolved, "run_id": "d" * 32, "acknowledged_state": "unresolved"}
    view = diagnose(
        _overview(),
        _listing(runs=[pending, early, unresolved, acknowledged], marker_run_id="a" * 32),
    )
    pendings = [p for p in view["problems"] if p["code"] == "CLAUDE_RECONCILIATION_RUN_PENDING"]
    kinds = sorted(p["actions"][0]["kind"] for p in pendings)
    assert kinds == ["RESOLVE_RUN", "WAIT"]
    resolve = next(p for p in pendings if p["actions"][0]["kind"] == "RESOLVE_RUN")
    assert resolve["actions"][0]["run_id"] == "a" * 32 and resolve["actions"][0]["permitted"]
    # The marker belongs to the pending run, so it is not reported separately.
    assert "CLAUDE_RECONCILIATION_MARKER" not in recovery.present_codes(view)
    unresolved_view = problem(view, "CLAUDE_RECONCILIATION_RUN_UNRESOLVED")
    assert unresolved_view["actions"][0]["authority"] == "OWNER"


def test_limits_credentials_and_unreadable_ledger() -> None:
    claude = _claude(
        daily={"remaining_micro_usd": 0},
        ledger={"headroom_micro_usd": 0},
        credential={"source": "none", "status": "missing", "hr_editable": True},
    )
    view = diagnose(_overview(claude))
    assert problem(view, "CLAUDE_DAILY_LIMIT_REACHED")["actions"][0]["kind"] == "EDIT_DAILY_LIMIT"
    lifetime = problem(view, "CLAUDE_LIFETIME_LIMIT_REACHED")
    assert lifetime["actions"][0]["kind"] == "EDIT_LIFETIME_LIMIT"
    assert problem(view, "CLAUDE_KEY_MISSING")["actions"][0]["kind"] == "ENTER_KEY"

    at_ceiling = _claude(ledger={"headroom_micro_usd": 0, "cap_micro_usd": 25_000_000})
    item = problem(diagnose(_overview(at_ceiling)), "CLAUDE_LIFETIME_CEILING_REACHED")
    assert item["actions"][0]["authority"] == "OWNER"

    server = _claude(credential={"source": "none", "status": "missing", "hr_editable": False})
    item = problem(diagnose(_overview(server)), "CLAUDE_SERVER_KEY_UNAVAILABLE")
    assert [a["kind"] for a in item["actions"]] == ["OWNER_REQUEST", "TEST_CONNECTION"]

    ending = _claude(
        credential={
            "source": "hr_session",
            "status": "configured",
            "hr_editable": True,
            "expires_at": (NOW + timedelta(minutes=20)).timestamp(),
        }
    )
    view = diagnose(_overview(ending))
    assert problem(view, "CLAUDE_HR_KEY_ENDING")["severity"] == "info"
    assert view["expiries"]["claude_hr_key_ends_at"].startswith("2026-11-06T02:20")

    unreadable = _claude(ledger=None)
    view = diagnose(_overview(unreadable))
    assert problem(view, "CLAUDE_LEDGER_UNREADABLE")["severity"] == "blocking"

    view = diagnose(_overview(), None, listing_error="RUN_STORE_UNAVAILABLE")
    assert problem(view, "CLAUDE_RECONCILIATION_UNAVAILABLE")


def test_model_unavailable_offers_activation_rollback_or_qualification() -> None:
    overview = _overview(active={"profile_id": "unavailable", "unavailable": True})
    overview["profiles"][0]["qualification"] = {"status": "passed", "current": False}
    item = problem(diagnose(overview), "MODEL_UNAVAILABLE")
    assert [a["kind"] for a in item["actions"]] == ["ACTIVATE"]
    overview["profiles"][0]["eligible_qualification"] = None
    overview["last_good"] = {"profile_id": "local", "display_name": "Local"}
    assert [a["kind"] for a in problem(diagnose(overview), "MODEL_UNAVAILABLE")["actions"]] == [
        "ROLLBACK"
    ]
    overview["last_good"] = None
    view = diagnose(overview)
    assert [a["kind"] for a in problem(view, "MODEL_UNAVAILABLE")["actions"]] == ["QUALIFY"]
    stale = problem(view, "QUALIFICATION_OUT_OF_DATE")
    assert [a["kind"] for a in stale["actions"]] == ["TEST_CONNECTION", "QUALIFY"]


def test_without_the_capability_no_action_is_permitted() -> None:
    claude = _claude(reconciliation={"chat_fresh": False})
    view = diagnose(_overview(claude), hr_allowed=False)
    assert all(not a["permitted"] for p in view["problems"] for a in p["actions"])


def test_a_healthy_service_reports_nothing_blocking() -> None:
    claude = _claude(
        reconciliation={"paid_fresh": True, "chat_deadline_at": "2026-11-20T00:00:00+00:00"}
    )
    view = diagnose(_overview(claude))
    assert view["problems"] == [] and view["healthy"]


def test_the_diagnosis_does_not_mutate_its_input() -> None:
    overview = _overview(_claude(reconciliation={"chat_fresh": False}))
    before = copy.deepcopy(overview)
    diagnose(overview)
    assert overview == before


# --- the store -----------------------------------------------------------------------------


def test_requests_are_one_per_problem_audited_and_closed_once(tmp_path: Path) -> None:
    store = ModelAdminStore(tmp_path / "state.sqlite3")
    evidence = [{"label": "Breaker code", "value": "reconcile_drift"}]
    request_id = store.open_recovery_request("CLAUDE_BREAKER_OPEN", evidence, None, "biz-ops")
    with pytest.raises(RecoveryRequestRefused) as refused:
        store.open_recovery_request("CLAUDE_BREAKER_OPEN", evidence, None, "biz-ops")
    assert refused.value.code == "RECOVERY_REQUEST_EXISTS"
    assert store.recovery_request(request_id)["evidence"] == evidence
    store.close_recovery_request(request_id, "withdrawn", "biz-ops")
    with pytest.raises(RecoveryRequestRefused) as refused:
        store.close_recovery_request(request_id, "resolved", "biz-ops")
    assert refused.value.code == "RECOVERY_REQUEST_CLOSED"
    actions = [event["action"] for event in store.events(10)]
    assert actions[:2] == ["RECOVERY_WITHDRAWN", "RECOVERY_REQUESTED"]
    # Withdrawn requests free the problem for a new one.
    store.open_recovery_request("CLAUDE_BREAKER_OPEN", evidence, None, "biz-ops")


# --- the routes ----------------------------------------------------------------------------


def _journey(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    from tests.test_claude_runtime import ClaudeJourney

    journey = ClaudeJourney(tmp_path, monkeypatch)
    journey.selector.reconciler.runs.record_prerequisite("owner", "retired")
    return journey


def test_routes_report_the_breaker_and_record_an_owner_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_model_management import API

    journey = _journey(tmp_path, monkeypatch)
    ledger_path = Path(journey.settings.anthropic_ledger_path)
    before = BudgetLedger(ledger_path).status()
    view = journey.client.get(f"{API}/recovery")
    assert view.status_code == 200, view.text
    assert "CLAUDE_BREAKER_OPEN" not in recovery.present_codes(view.json())

    # No owner request for a problem that is not present, or one HR can fix itself.
    absent = journey.client.post(
        f"{API}/recovery/requests", json={"problem_code": "CLAUDE_BREAKER_OPEN"}
    )
    assert absent.status_code == 409
    assert absent.json()["detail"]["code"] == "RECOVERY_PROBLEM_NOT_PRESENT"

    BudgetLedger(ledger_path).open_breaker("routing_anomaly")
    view = journey.client.get(f"{API}/recovery").json()
    breaker = problem(view, "CLAUDE_BREAKER_OPEN")
    assert breaker["actions"][0]["kind"] == "OWNER_REQUEST"

    keyish = journey.client.post(
        f"{API}/recovery/requests",
        json={"problem_code": "CLAUDE_BREAKER_OPEN", "note": "use sk-ant-api03-abc"},
    )
    assert keyish.status_code == 422
    assert keyish.json()["detail"]["code"] == "RECOVERY_NOTE_REFUSED"

    created = journey.client.post(
        f"{API}/recovery/requests",
        json={"problem_code": "CLAUDE_BREAKER_OPEN", "note": "Seen after the 3 Nov demo."},
    )
    assert created.status_code == 200, created.text
    requests = created.json()["requests"]
    assert len(requests) == 1 and requests[0]["problem_present"] is True
    assert {"label": "Breaker code", "value": "routing_anomaly"} in requests[0]["evidence"]

    # Resolved is refused while the server still reports the problem.
    request_id = requests[0]["request_id"]
    still = journey.client.post(
        f"{API}/recovery/requests/{request_id}/close", json={"status": "resolved"}
    )
    assert still.status_code == 409
    assert still.json()["detail"]["code"] == "RECOVERY_PROBLEM_STILL_PRESENT"
    withdrawn = journey.client.post(
        f"{API}/recovery/requests/{request_id}/close", json={"status": "withdrawn"}
    )
    assert withdrawn.status_code == 200
    # The recovery centre wrote nothing to the ledger.
    after = BudgetLedger(ledger_path).status()
    assert (after.committed, after.baseline, after.open_calls, after.breaker_code) == (
        before.committed,
        before.baseline,
        before.open_calls,
        "routing_anomaly",
    )
    audit = [e["action"] for e in journey.client.get(f"{API}/audit").json()["events"]]
    assert "RECOVERY_REQUESTED" in audit and "RECOVERY_WITHDRAWN" in audit


def test_routes_need_the_capability_origin_and_strict_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_model_management import API

    journey = _journey(tmp_path, monkeypatch)
    no_origin = journey.client.post(
        f"{API}/recovery/requests",
        json={"problem_code": "CLAUDE_BREAKER_OPEN"},
        headers={"Origin": ""},
    )
    assert no_origin.status_code == 403
    extra = journey.client.post(
        f"{API}/recovery/requests", json={"problem_code": "X_Y", "figure": 1}
    )
    assert extra.status_code == 422
    journey.client.cookies.set("clm_session", "rm-session")
    for method, path in (
        ("get", "/recovery"),
        ("post", "/recovery/requests"),
        ("post", f"/recovery/requests/{'a' * 32}/close"),
    ):
        # QG F6: valid bodies, so only the missing capability can refuse them.
        body = {"status": "withdrawn"} if path.endswith("/close") else {
            "problem_code": "CLAUDE_BREAKER_OPEN"
        }
        kwargs = {"json": body} if method == "post" else {}
        response = getattr(journey.client, method)(f"{API}{path}", **kwargs)
        assert response.status_code == 403, (path, response.status_code)



def test_resolved_is_accepted_once_the_problem_has_cleared_and_never_from_a_partial_view(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ai_assistant import claude_reconciliation as rc
    from tests.test_claude_runtime import ClaudeJourney, anchored_on_the_console
    from tests.test_model_management import API

    journey = ClaudeJourney(tmp_path, monkeypatch)  # no P1 attestation recorded yet
    anchored_on_the_console(journey.settings)  # D-118: P1 applies to an anchored ledger only
    created = journey.client.post(
        f"{API}/recovery/requests", json={"problem_code": "CLAUDE_RECONCILIATION_PREREQUISITE"}
    )
    assert created.status_code == 200, created.text
    request_id = created.json()["requests"][0]["request_id"]
    # The owner records the attestation with the script (simulated here).
    journey.selector.reconciler.runs.record_prerequisite("owner", "retired")
    # A partial diagnosis (the run store unreadable) proves nothing.
    original = rc.Reconciler.listing

    def broken(self: object) -> dict[str, object]:
        raise rc.ReconcileRefused("RUN_STORE_UNAVAILABLE")

    monkeypatch.setattr(rc.Reconciler, "listing", broken)
    refused = journey.client.post(
        f"{API}/recovery/requests/{request_id}/close", json={"status": "resolved"}
    )
    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "RECOVERY_PROBLEM_STILL_PRESENT"
    monkeypatch.setattr(rc.Reconciler, "listing", original)
    resolved = journey.client.post(
        f"{API}/recovery/requests/{request_id}/close", json={"status": "resolved"}
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["requests"][0]["status"] == "resolved"


def test_problem_coverage() -> None:
    view = {"covered": ["MODEL", "CLAUDE"]}
    assert recovery.problem_covered(view, "CLAUDE_BREAKER_OPEN")
    assert not recovery.problem_covered(view, "CLAUDE_RECONCILIATION_MARKER")
    assert not recovery.problem_covered(view, "GPT_OSS_BREAKER_OPEN")
    assert recovery.problem_covered(view, "MODEL_UNAVAILABLE")
