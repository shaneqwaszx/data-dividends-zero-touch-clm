"""D-102 (proposed): Claude's US$30.00 ceiling and its HR-editable spending controls, offline.

An HR administrator sets Claude's daily allowance (up to US$5.00 a Singapore day), its calls per
activation (1 to 20) and its Anthropic ledger's lifetime cap (up to the lower of US$30.00 and the
owner-attested workspace limit) on AI Models. Raises need the amount confirmed and a
reconciliation within 24 hours; lowering never does. GPT-OSS's controls and ledger are separate
and never touched. The same mock Anthropic API, ledgers and journey as test_claude_runtime.py.
"""

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from ai_assistant import anthropic_runtime
from ai_assistant.anthropic_profiles import BALANCED
from ai_assistant.anthropic_runtime import ClaudeTestModel, readiness
from ai_assistant.budget import BudgetLedger
from ai_assistant.model_admin_store import (
    CLAUDE_DAILY_CAP_RANGE,
    CLAUDE_MAX_CALLS_RANGE,
    ModelAdminStore,
    RevisionConflict,
    apply_claude_controls,
)
from tests.test_claude_runtime import (
    KEY,
    ClaudeJourney,
    anchored_on_the_console,
    claude_config,
    reconciled_ago,
)
from tests.test_model_management import API
from tests.test_remote_test import config

CONTROLS = f"{API}/budget/claude/controls"
LIFETIME = f"{API}/budget/claude/lifetime-cap"


def _claude(journey: ClaudeJourney) -> dict[str, Any]:
    response = journey.client.get(f"{API}/budget")
    assert response.status_code == 200, response.text
    return dict(response.json()["claude"])


def _save(journey: ClaudeJourney, daily: int, calls: int, **extra: Any) -> Any:
    revision = _claude(journey)["controls"]["revision"]
    body = {"expected_revision": revision, "daily_cap_micro_usd": daily, "max_calls": calls}
    return journey.client.put(CONTROLS, json={**body, **extra})


def _cap(journey: ClaudeJourney, cap: int, **extra: Any) -> Any:
    return journey.client.put(LIFETIME, json={"cap_micro_usd": cap, **extra})


def _code(response: Any) -> str:
    return str(response.json()["detail"]["code"])


def _events(journey: ClaudeJourney, action: str) -> list[tuple[str, str | None]]:
    events = journey.client.get(f"{API}/audit").json()["events"]
    return [(e["outcome"], e["code"]) for e in events if e["action"] == action]


def _ledger(journey: ClaudeJourney) -> BudgetLedger:
    return BudgetLedger(Path(journey.settings.anthropic_ledger_path))


# --- the ceilings and the store --------------------------------------------------------------


def test_the_ceilings_are_us30_lifetime_us5_daily_and_20_calls(tmp_path: Path) -> None:
    assert anthropic_runtime.LIFETIME_CEILING_MICRO_USD == 30_000_000
    assert anthropic_runtime.DAILY_CEILING_MICRO_USD == 5_000_000
    assert anthropic_runtime.MAX_CALLS_CEILING == 20
    # The store's bounds are the runtime's ceilings.
    assert CLAUDE_DAILY_CAP_RANGE == (1, anthropic_runtime.DAILY_CEILING_MICRO_USD)
    assert CLAUDE_MAX_CALLS_RANGE == (1, anthropic_runtime.MAX_CALLS_CEILING)
    settings = claude_config(
        tmp_path,
        anthropic_workspace_limit_micro_usd=30_000_000,
        anthropic_daily_cap_micro_usd=5_000_000,
    )
    assert readiness(settings) is None


def test_claude_controls_have_their_own_row_bounds_and_revision(tmp_path: Path) -> None:
    store = ModelAdminStore(tmp_path / "admin.sqlite3")
    assert store.claude_spending_controls().revision == 0
    assert store.set_claude_spending_controls(0, 5_000_000, 20, "hr-admin") == 1
    assert store.spending_controls().revision == 0  # GPT-OSS's row is untouched
    with pytest.raises(RevisionConflict):
        store.set_claude_spending_controls(0, 500_000, 5, "hr-admin")
    for daily, calls in ((0, 5), (5_000_001, 5), (500_000, 0), (500_000, 21), (True, 5)):
        with pytest.raises(ValueError):
            store.set_claude_spending_controls(1, daily, calls, "hr-admin")
    # The table's own CHECKs refuse a writer that skips the store.
    with sqlite3.connect(tmp_path / "admin.sqlite3") as db, pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE claude_spending_controls SET daily_cap_micro_usd = 5000001")
    stored = store.claude_spending_controls()
    assert (stored.revision, stored.daily_cap_micro_usd, stored.max_calls) == (1, 5_000_000, 20)


def test_unreadable_claude_controls_fail_closed(tmp_path: Path) -> None:
    settings = claude_config(tmp_path)
    closed = apply_claude_controls(settings, None)
    assert closed.anthropic_daily_cap_micro_usd == 0
    assert readiness(closed) == "ANTHROPIC_SETTINGS_INVALID"
    # GPT-OSS's settings are not Claude's controls.
    assert closed.budget_daily_cap_micro_usd == settings.budget_daily_cap_micro_usd
    plain = config(tmp_path)
    assert apply_claude_controls(plain, None).budget_daily_cap_micro_usd == (
        plain.budget_daily_cap_micro_usd
    )


# --- daily allowance and calls ------------------------------------------------------------


def test_hr_lowers_claude_limits_and_the_active_model_uses_them_at_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    journey.activate_claude()
    gpt_oss = journey.client.get(f"{API}/budget").json()["controls"]
    view = _claude(journey)["controls"]
    assert view["daily_cap_source"] == "environment" and view["max_calls"] == 20
    assert view["daily_cap_range"] == [1, 5_000_000] and view["max_calls_range"] == [1, 20]

    saved = _save(journey, 500_000, 1)  # lowering needs no confirmation or reconciliation
    assert saved.status_code == 200, saved.text
    controls = saved.json()["claude"]["controls"]
    assert controls["daily_cap_micro_usd"] == 500_000 and controls["daily_cap_source"] == "hr"
    assert controls["max_calls"] == 1 and controls["changed_by"]
    model = journey.selector.current().model
    assert isinstance(model, ClaudeTestModel)
    assert model._settings.anthropic_daily_cap_micro_usd == 500_000
    assert model._settings.anthropic_max_calls == 1
    # GPT-OSS's controls are unchanged.
    assert saved.json()["controls"]["revision"] == gpt_oss["revision"]
    assert saved.json()["controls"]["daily_cap_micro_usd"] == gpt_oss["daily_cap_micro_usd"]

    # One call per activation now: the second answer comes from the case data, unsent.
    assert journey.ask(stream=True)["answered_by"] == "model"
    sent = journey.claude.posts
    assert journey.ask(stream=True)["answered_by"] == "case_data"
    assert journey.claude.posts == sent and journey.openrouter.chats == []
    assert _claude(journey)["controls"]["calls_remaining"] == 0
    assert _events(journey, "CLAUDE_SPENDING_CONTROLS_CHANGED") == [
        ("applied", "DAILY_500000_MICRO_USD_CALLS_1")
    ]


def test_raising_claude_daily_allowance_needs_confirmation_and_a_recent_reconciliation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    anchored_on_the_console(journey.settings)  # D-118: the gating applies to such a store
    unconfirmed = _save(journey, 5_000_000, 20)
    assert unconfirmed.status_code == 400 and _code(unconfirmed) == "DAILY_CONFIRMATION_REQUIRED"
    reconciled_ago(journey.settings, 2 * 86_400)
    stale = _save(journey, 5_000_000, 20, confirm_daily_cap_micro_usd=5_000_000)
    assert stale.status_code == 409 and _code(stale) == "RECONCILIATION_REQUIRED"
    message = stale.json()["detail"]["message"]
    assert "Anthropic Console" in message and "OpenRouter" not in message
    reconciled_ago(journey.settings, 0)
    raised = _save(journey, 5_000_000, 20, confirm_daily_cap_micro_usd=5_000_000)
    assert raised.status_code == 200, raised.text
    assert raised.json()["claude"]["daily"]["cap_micro_usd"] == 5_000_000
    for daily, calls in ((5_000_001, 20), (0, 20), (1_000_000, 21), (1_000_000, 0)):
        invalid = _save(journey, daily, calls, confirm_daily_cap_micro_usd=daily)
        assert invalid.status_code == 400 and _code(invalid) == "CONTROLS_INVALID"
        assert "1 to 20" in invalid.json()["detail"]["message"]
    assert _claude(journey)["controls"]["revision"] == 1
    codes = [code for _, code in _events(journey, "CLAUDE_SPENDING_CONTROLS_CHANGED")]
    assert "RECONCILIATION_REQUIRED" in codes and "DAILY_CONFIRMATION_REQUIRED" in codes


def test_a_stale_claude_view_is_refused_and_nothing_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    assert _save(journey, 500_000, 10).status_code == 200
    stale = journey.client.put(
        CONTROLS, json={"expected_revision": 0, "daily_cap_micro_usd": 400_000, "max_calls": 5}
    )
    assert stale.status_code == 409 and _code(stale) == "CONTROLS_CONFLICT"
    assert _claude(journey)["controls"]["max_calls"] == 10


def test_claude_raises_are_refused_until_claude_is_configured_but_lowering_is_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch, anthropic_decision="")
    raised = _save(journey, 2_000_000, 20, confirm_daily_cap_micro_usd=2_000_000)
    assert raised.status_code == 409 and _code(raised) == "ANTHROPIC_NOT_AUTHORISED"
    assert "can only be lowered" in raised.json()["detail"]["message"]
    assert _save(journey, 500_000, 20).status_code == 200
    assert journey.claude.requests == []


# --- the lifetime cap ------------------------------------------------------------------------


def test_hr_raises_claude_lifetime_cap_up_to_us30_with_confirmation_and_reconciliation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch, anthropic_workspace_limit_micro_usd=30_000_000)
    anchored_on_the_console(journey.settings)  # D-118: the gating applies to such a store
    gpt_oss = BudgetLedger(Path(journey.settings.budget_ledger_path)).status().cap
    lifetime = _claude(journey)["controls"]["lifetime"]
    assert lifetime["cap_micro_usd"] == 5_000_000 and lifetime["max_cap_micro_usd"] == 30_000_000

    missing_view = _cap(journey, 30_000_000, confirm_cap_micro_usd=30_000_000)
    assert missing_view.status_code == 409 and _code(missing_view) == "CONTROLS_CONFLICT"
    unconfirmed = _cap(journey, 30_000_000, expected_cap_micro_usd=5_000_000)
    assert unconfirmed.status_code == 400 and _code(unconfirmed) == "CAP_CONFIRMATION_REQUIRED"
    above = _cap(
        journey, 30_000_001, confirm_cap_micro_usd=30_000_001, expected_cap_micro_usd=5_000_000
    )
    assert above.status_code == 409 and _code(above) == "CAP_OUT_OF_RANGE"
    reconciled_ago(journey.settings, 2 * 86_400)
    raise_body = {"confirm_cap_micro_usd": 30_000_000, "expected_cap_micro_usd": 5_000_000}
    stale = _cap(journey, 30_000_000, **raise_body)
    assert stale.status_code == 409 and _code(stale) == "RECONCILIATION_REQUIRED"
    assert _ledger(journey).status().cap == 5_000_000

    reconciled_ago(journey.settings, 0)
    raised = _cap(journey, 30_000_000, **raise_body)
    assert raised.status_code == 200, raised.text
    assert _ledger(journey).status().cap == 30_000_000
    assert raised.json()["claude"]["ledger"]["cap_micro_usd"] == 30_000_000
    # Lowering needs no confirmation or reconciliation; the GPT-OSS ledger is never touched.
    reconciled_ago(journey.settings, 30 * 86_400)
    assert _cap(journey, 2_000_000).status_code == 200
    assert _ledger(journey).status().cap == 2_000_000
    assert BudgetLedger(Path(journey.settings.budget_ledger_path)).status().cap == gpt_oss
    assert ("applied", "RAISED_TO_30000000_MICRO_USD") in _events(
        journey, "CLAUDE_LIFETIME_CAP_CHANGED"
    )
    texts = [journey.client.get(f"{API}/budget").text, journey.client.get(f"{API}/audit").text]
    assert all(KEY not in text for text in texts)


def test_claude_lifetime_cap_never_exceeds_the_attested_workspace_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch, anthropic_workspace_limit_micro_usd=10_000_000)
    assert _claude(journey)["controls"]["lifetime"]["max_cap_micro_usd"] == 10_000_000
    body = {"confirm_cap_micro_usd": 10_000_001, "expected_cap_micro_usd": 5_000_000}
    refused = _cap(journey, 10_000_001, **body)
    assert refused.status_code == 409 and _code(refused) == "CAP_OUT_OF_RANGE"
    # At or below the opening usage (US$0) is out of range too.
    assert _code(_cap(journey, 0)) == "CAP_OUT_OF_RANGE"
    body = {"confirm_cap_micro_usd": 10_000_000, "expected_cap_micro_usd": 5_000_000}
    assert _cap(journey, 10_000_000, **body).status_code == 200


def test_a_low_hr_daily_allowance_stops_a_paid_claude_qualification_before_it_starts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    # Below one worst-case reservation: nothing may be spent today.
    low = anthropic_runtime.worst_reservation() - 1
    assert _save(journey, low, 20).status_code == 200
    profile_id = BALANCED.profile_id
    assert journey.client.post(f"{API}/{profile_id}/connection-test").json()["outcome"] == (
        "failed"
    )
    refused = journey.start_qualification(profile_id)
    assert refused.status_code == 409
    assert journey.claude.posts == 0 and journey.openrouter.chats == []


# --- QG remediation: L1 call-limit raises, L2 reductions, L3 per-provider call counts ---------


def test_raising_claude_calls_needs_confirmation_and_a_recent_reconciliation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    anchored_on_the_console(journey.settings)  # D-118: the gating applies to such a store
    assert _save(journey, 1_000_000, 5).status_code == 200  # lowering: no confirmation
    unconfirmed = _save(journey, 1_000_000, 10)
    assert unconfirmed.status_code == 400 and _code(unconfirmed) == "CALLS_CONFIRMATION_REQUIRED"
    assert unconfirmed.json()["detail"]["message"].startswith("Confirm the new call limit")
    mismatched = _save(journey, 1_000_000, 10, confirm_max_calls=11)
    assert _code(mismatched) == "CALLS_CONFIRMATION_REQUIRED"
    reconciled_ago(journey.settings, 30 * 86_400)
    stale = _save(journey, 1_000_000, 10, confirm_max_calls=10)
    assert stale.status_code == 409 and _code(stale) == "RECONCILIATION_REQUIRED"
    assert _claude(journey)["controls"]["max_calls"] == 5
    reconciled_ago(journey.settings, 0)
    raised = _save(journey, 1_000_000, 10, confirm_max_calls=10)
    assert raised.status_code == 200, raised.text
    assert raised.json()["claude"]["controls"]["max_calls"] == 10
    codes = [code for _, code in _events(journey, "CLAUDE_SPENDING_CONTROLS_CHANGED")]
    assert codes.count("CALLS_CONFIRMATION_REQUIRED") == 2
    # GPT-OSS's request keeps its own shape: the Claude-only field is refused there.
    revision = journey.client.get(f"{API}/budget").json()["controls"]["revision"]
    gpt_oss = journey.client.put(
        f"{API}/budget/controls",
        json={
            "expected_revision": revision,
            "daily_cap_micro_usd": 500_000,
            "max_calls": 5,
            "confirm_max_calls": 5,
        },
    )
    assert gpt_oss.status_code == 422


def test_claude_call_raises_are_refused_until_claude_is_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch, anthropic_decision="")
    assert _save(journey, 1_000_000, 5).status_code == 200
    raised = _save(journey, 1_000_000, 6, confirm_max_calls=6)
    assert raised.status_code == 409 and _code(raised) == "ANTHROPIC_NOT_AUTHORISED"
    assert _claude(journey)["controls"]["max_calls"] == 5
    assert journey.claude.requests == []


def test_hr_lowers_claude_lifetime_cap_without_an_attested_workspace_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch, anthropic_workspace_limit_micro_usd=0)
    assert readiness(journey.settings) == "WORKSPACE_LIMIT_NOT_ATTESTED"
    assert _claude(journey)["controls"]["lifetime"]["max_cap_micro_usd"] == 0
    # Strictly lower (and above the opening usage): allowed, even with a stale reconciliation.
    reconciled_ago(journey.settings, 30 * 86_400)
    lowered = _cap(journey, 2_000_000, expected_cap_micro_usd=5_000_000)
    assert lowered.status_code == 200, lowered.text
    assert _ledger(journey).status().cap == 2_000_000
    # The same cap, a higher one or one at the opening usage: refused, nothing changes.
    assert _code(_cap(journey, 2_000_000)) == "CAP_OUT_OF_RANGE"
    body = {"confirm_cap_micro_usd": 3_000_000, "expected_cap_micro_usd": 2_000_000}
    assert _code(_cap(journey, 3_000_000, **body)) == "CAP_OUT_OF_RANGE"
    assert _code(_cap(journey, 0)) == "CAP_OUT_OF_RANGE"
    assert _ledger(journey).status().cap == 2_000_000
    # A stale view of the cap is still refused for a reduction.
    stale = _cap(journey, 1_000_000, expected_cap_micro_usd=5_000_000)
    assert stale.status_code == 409 and _code(stale) == "CONTROLS_CONFLICT"
    # Claude stays unavailable: nothing is enabled, nothing is sent.
    assert readiness(journey.settings) == "WORKSPACE_LIMIT_NOT_ATTESTED"
    assert journey.settings.anthropic_workspace_limit_micro_usd == 0
    assert journey.claude.requests == []
    assert ("applied", "LOWERED_TO_2000000_MICRO_USD") in _events(
        journey, "CLAUDE_LIFETIME_CAP_CHANGED"
    )


def test_a_cap_above_a_reduced_workspace_limit_may_be_lowered_in_steps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The owner lowered the workspace limit below the ledger cap: calls stop, and HR may
    # lower the cap step by step (each strictly lower), never raise it.
    journey = ClaudeJourney(tmp_path, monkeypatch, anthropic_workspace_limit_micro_usd=3_000_000)
    assert _cap(journey, 4_000_000, expected_cap_micro_usd=5_000_000).status_code == 200
    assert _cap(journey, 3_000_000, expected_cap_micro_usd=4_000_000).status_code == 200
    body = {"confirm_cap_micro_usd": 3_500_000, "expected_cap_micro_usd": 3_000_000}
    assert _code(_cap(journey, 3_500_000, **body)) == "CAP_OUT_OF_RANGE"
    assert _ledger(journey).status().cap == 3_000_000


def test_each_provider_view_counts_only_its_own_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    journey.activate_claude()
    assert journey.ask(stream=True)["answered_by"] == "model"
    view = journey.client.get(f"{API}/budget").json()
    assert view["controls"]["calls_used"] is None  # GPT-OSS is not the active model
    assert view["controls"]["calls_remaining"] is None
    assert view["claude"]["controls"]["calls_used"] == 1
    assert view["claude"]["controls"]["calls_remaining"] == 19


def test_on_a_session_store_a_raise_needs_only_its_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # D-118 amendment P4: no reconciliation (never reconciled, or long ago) gates a raise.
    journey = ClaudeJourney(tmp_path, monkeypatch)
    reconciled_ago(journey.settings, 9 * 86_400)
    assert _save(journey, 1_000_000, 5).status_code == 200
    unconfirmed = _save(journey, 5_000_000, 20)
    assert unconfirmed.status_code == 400 and _code(unconfirmed) == "DAILY_CONFIRMATION_REQUIRED"
    raised = _save(
        journey, 5_000_000, 20, confirm_daily_cap_micro_usd=5_000_000, confirm_max_calls=20
    )
    assert raised.status_code == 200, raised.text
