"""D-118 acceptance: a fresh teammate deployment sets up Claude or GPT-OSS in AI Models with no
CLI step, no P1 record and no routine reconciliation; the US$5 session is shared by the paid
qualification and the chat, survives a restart, and a genuine anomaly still stops safely.
Mock providers and a fake CLM backend only; nothing is spent and no real key is read."""

from pathlib import Path
from typing import Any

import pytest

from ai_assistant.anthropic_profiles import BALANCED
from ai_assistant.budget import BudgetLedger
from ai_assistant.model_admin import ModelSelector
from ai_assistant.model_admin_store import ModelAdminStore
from tests.test_claude_hr_enablement import READ, HrJourney
from tests.test_claude_runtime import WORKSPACE
from tests.test_model_management import API

ROUTINE_FORBIDDEN = ("RECONCILIATION", "RECONCILED", "PREREQUISITE", "WINDOW", "P1")


def _fresh_claude(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> HrJourney:
    journey = HrJourney(tmp_path, monkeypatch)
    # A teammate's new data root: no ledger was ever initialised with the script.
    Path(journey.settings.anthropic_ledger_path).unlink()
    return journey


def _setup_view(journey: HrJourney, provider: str) -> dict[str, Any]:
    response = journey.client.get(f"{API}/setup")
    assert response.status_code == 200, response.text
    view: dict[str, Any] = response.json()["providers"][provider]
    return view


def _codes(journey: HrJourney) -> list[str]:
    recovery = journey.client.get(f"{API}/recovery").json()
    return [problem["code"] for problem in recovery["problems"]]


def test_a_fresh_teammate_sets_up_and_chats_with_claude_through_the_ui_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_synthetic_eligibility import GARDEN, serve

    journey = _fresh_claude(tmp_path, monkeypatch)
    view = _setup_view(journey, "anthropic")
    assert view["ledger"] == "missing"
    assert [b["action"] for b in view["blockers"]] == ["ENABLE_CLAUDE"]

    assert journey.client.post(READ).json()["workspace_id"] == WORKSPACE
    # Correction 2: never zero by default; the opening must be stated.
    missing = journey.enable()
    assert missing.status_code == 409
    assert missing.json()["detail"]["code"] == "OPENING_REQUIRED"
    assert not Path(journey.settings.anthropic_ledger_path).exists()
    enabled = journey.enable(opening="new_workspace")
    assert enabled.status_code == 200, enabled.text

    ledger = BudgetLedger(Path(journey.settings.anthropic_ledger_path))
    profile = ledger.profile()
    assert (profile.origin, profile.accounting_mode, profile.opening_basis) == (
        "fresh",
        "provider_capped",
        "new_workspace_confirmed",
    )
    assert ledger.last_reconciled_ms() is None  # never reconciled, and never needs to be
    # The record keeps the FYP-end key revocation commitment (correction 2).
    assert "key_revoked_at_fyp_end" in journey.setup()["record"]["confirmations"]

    journey.activate_claude(BALANCED.profile_id)
    serve(monkeypatch, GARDEN)
    assert journey.ask(stream=True)["answered_by"] == "model"

    view = _setup_view(journey, "anthropic")
    assert view["blockers"] == []
    session = view["session"]
    assert session["allowance_micro_usd"] == 5_000_000
    assert session["calls"] == 3 and session["chat_calls"] == 1  # 2 qualification + 1 chat
    assert 0 < session["committed_micro_usd"] < 5_000_000
    assert not any(word in code for code in _codes(journey) for word in ROUTINE_FORBIDDEN)


def test_an_existing_claude_ledger_never_reopens_at_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = HrJourney(tmp_path, monkeypatch)  # a ledger already exists
    journey.client.post(READ)
    refused = journey.enable(opening="new_workspace")
    assert refused.status_code == 409 and refused.json()["detail"]["code"] == "LEDGER_EXISTS"


def test_a_workspace_with_earlier_usage_opens_at_the_console_figure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered = _fresh_claude(tmp_path, monkeypatch)
    entered.client.post(READ)
    above = entered.enable(opening="console_usage", opening_usage_micro_usd=5_000_000)
    assert above.status_code == 400 and above.json()["detail"]["code"] == "OPENING_INVALID"
    ok = entered.enable(opening="console_usage", opening_usage_micro_usd=1_234_567)
    assert ok.status_code == 200, ok.text
    status = BudgetLedger(Path(entered.settings.anthropic_ledger_path)).status()
    assert status.opening_usage == 1_234_567


def test_the_session_survives_a_restart_and_an_exhausted_one_is_never_renewed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_synthetic_eligibility import GARDEN, serve

    journey = _fresh_claude(tmp_path, monkeypatch)
    journey.client.post(READ)
    journey.enable(opening="new_workspace")
    journey.activate_claude(BALANCED.profile_id)
    serve(monkeypatch, GARDEN)
    assert journey.ask(stream=True)["answered_by"] == "model"
    before = _setup_view(journey, "anthropic")["session"]

    # A restart is a new selector on the same stores; the session and its spend are kept.
    store = ModelAdminStore(Path(journey.settings.model_admin_db_path))
    ModelSelector(
        journey.settings,
        None,
        store,
        environ=journey.selector.environ,
        transport=journey.selector.transport,
    ).current()
    after = _setup_view(journey, "anthropic")["session"]
    assert after["session_id"] == before["session_id"]
    assert after["committed_micro_usd"] == before["committed_micro_usd"]

    # HR lowers the allowance below what was used: paid calls stop, nothing renews it.
    lowered = journey.client.put(
        f"{API}/session/allowance",
        json={"provider": "anthropic", "allowance_micro_usd": 1, "expected_revision": 1},
    )
    assert lowered.status_code == 200, lowered.text
    assert [b["action"] for b in lowered.json()["blockers"]] == ["NEW_SESSION"]
    posts = journey.claude.posts
    assert journey.ask(stream=True)["answered_by"] == "case_data"
    assert journey.claude.posts == posts
    over = journey.client.put(
        f"{API}/session/allowance",
        json={"provider": "anthropic", "allowance_micro_usd": 5_000_001, "expected_revision": 2},
    )
    assert over.status_code == 422

    # Only HR's explicit new session (on the session it saw) gives a fresh allowance.
    stale = journey.client.post(
        f"{API}/session/start",
        json={"provider": "anthropic", "allowance_micro_usd": 5_000_000},
    )
    assert stale.status_code == 409 and stale.json()["detail"]["code"] == "SESSION_CHANGED"
    started = journey.client.post(
        f"{API}/session/start",
        json={
            "provider": "anthropic",
            "allowance_micro_usd": 5_000_000,
            "expected_session_id": before["session_id"],
        },
    )
    assert started.status_code == 200, started.text
    assert started.json()["session"]["committed_micro_usd"] == 0
    assert journey.ask(stream=True)["answered_by"] == "model"
    actions = [e["action"] for e in journey.client.get(f"{API}/audit").json()["events"]]
    assert "PAID_SESSION_STARTED" in actions and "PAID_SESSION_ALLOWANCE_CHANGED" in actions


def test_a_genuine_anomaly_stops_claude_and_hr_cannot_resume_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_synthetic_eligibility import GARDEN, serve

    journey = _fresh_claude(tmp_path, monkeypatch)
    journey.client.post(READ)
    journey.enable(opening="new_workspace")
    journey.activate_claude(BALANCED.profile_id)
    serve(monkeypatch, GARDEN)
    journey.claude.reply_model = "claude-opus-5-5"  # a routing anomaly
    assert journey.ask(stream=True)["answered_by"] == "case_data"

    view = _setup_view(journey, "anthropic")
    assert view["breaker_open"] and view["breaker_code"] == "routing_anomaly"
    assert view["blockers"][0]["who"] == "owner" and not view["resumable"]
    refused = journey.client.post(
        f"{API}/budget/resume", json={"provider": "anthropic", "code": "usage_missing"}
    )
    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "BREAKER_RESUME_REFUSED"
    invalid = journey.client.post(
        f"{API}/budget/resume", json={"provider": "anthropic", "code": "routing_anomaly"}
    )
    assert invalid.status_code == 422
    assert _setup_view(journey, "anthropic")["breaker_open"]


def test_an_incomplete_call_is_charged_in_full_and_hr_resumes_it_on_proof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_synthetic_eligibility import GARDEN, serve

    journey = _fresh_claude(tmp_path, monkeypatch)
    journey.client.post(READ)
    journey.enable(opening="new_workspace")
    journey.activate_claude(BALANCED.profile_id)
    serve(monkeypatch, GARDEN)
    journey.claude.finished = False  # the stream ends without its usage report
    journey.ask(stream=True)
    journey.claude.finished = True
    path = Path(journey.settings.anthropic_ledger_path)
    last = BudgetLedger(path).closed_calls_after(0)[-1]
    assert last.charged_micro_usd == last.reserved_micro_usd  # conservative

    # The next preflight verifies it in-band (quarantined, usage_missing): HR may resume.
    journey.client.post(f"{API}/{BALANCED.profile_id}/connection-test")
    view = _setup_view(journey, "anthropic")
    assert view["breaker_code"] == "usage_missing" and view["resumable"], view
    resumed = journey.client.post(
        f"{API}/budget/resume", json={"provider": "anthropic", "code": "usage_missing"}
    )
    assert resumed.status_code == 200, resumed.text
    assert not resumed.json()["breaker_open"]
    assert BudgetLedger(path).closed_calls_after(0)[-1].charged_micro_usd == last.reserved_micro_usd
    assert journey.ask(stream=True)["answered_by"] == "model"


def test_resume_needs_hr_and_the_page_origin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = _fresh_claude(tmp_path, monkeypatch)
    headers = {k: v for k, v in journey.client.headers.items() if k.lower() != "origin"}
    response = journey.client.post(
        f"{API}/session/start",
        json={"provider": "anthropic", "allowance_micro_usd": 5_000_000},
        headers={**headers, "origin": ""},
    )
    assert response.status_code == 403


def test_a_fresh_teammate_sets_up_gpt_oss_and_its_ledger_opens_from_the_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ai_assistant.model_profiles import OPENROUTER_PROFILE_ID
    from tests.test_remote_test import Journey

    journey = Journey(tmp_path, monkeypatch)
    Path(journey.settings.budget_ledger_path).unlink()  # a new data root, no script run
    assert _setup_view(journey, "openrouter")["ledger"] == "missing"  # type: ignore[arg-type]

    journey.activate_remote()  # Test connection creates the ledger from the key's own figures

    ledger = BudgetLedger(Path(journey.settings.budget_ledger_path))
    profile = ledger.profile()
    assert (profile.origin, profile.accounting_mode, profile.opening_basis) == (
        "fresh",
        "provider_anchored",
        "provider_reported",
    )
    assert ledger.status().opening_usage == 0
    assert ledger.status().cap == 1_000_000  # opening + the key's remaining limit (US$1.00)
    assert journey.ask()["answered_by"] == "model"
    view = _setup_view(journey, "openrouter")  # type: ignore[arg-type]
    assert view["blockers"] == [] and view["session"]["chat_calls"] == 1
    assert view["session"]["calls"] == 3  # 2 qualification + 1 chat, one allowance
    events = journey.client.get(f"{API}/audit").json()["events"]
    assert not any("RECONCIL" in str(e.get("code") or "") for e in events)
    assert journey.client.get(API).json()["active"]["profile_id"] == OPENROUTER_PROFILE_ID


def test_a_refused_enablement_leaves_no_ledger_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # QG F4: the ledger is created only once the setup record is stored.
    journey = _fresh_claude(tmp_path, monkeypatch)
    journey.client.post(READ)
    stale = journey.enable(opening="new_workspace", expected_revision=7)
    assert stale.status_code == 409 and stale.json()["detail"]["code"] == "ENABLEMENT_CONFLICT"
    assert not Path(journey.settings.anthropic_ledger_path).exists()
    assert journey.enable(opening="new_workspace").status_code == 200
    assert Path(journey.settings.anthropic_ledger_path).exists()
