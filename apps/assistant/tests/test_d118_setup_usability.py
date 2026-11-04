"""D-118 usability remediation: the paid qualification's question list has an approved default,
its estimate names every limit (the session included) and which one blocks, and a start is
never refused as a budget shortfall unless a named limit causes it. Mock providers, fake CLM
backend and disposable stores only; nothing is spent and no real key is read."""

from pathlib import Path
from typing import Any

import httpx
import pytest
from dotenv import dotenv_values

from ai_assistant.anthropic_profiles import FAST
from ai_assistant.budget import BudgetLedger
from ai_assistant.config import (
    APPROVED_QUALIFICATION_COUNT,
    APPROVED_QUALIFICATION_QUESTIONS,
    AiAssistantSettings,
)
from ai_assistant.model_profiles import OPENROUTER_PROFILE_ID
from ai_assistant.remote_test import qualification_manifest
from tests.test_claude_hr_enablement import READ, HrJourney
from tests.test_model_management import API

ASSISTANT_DIR = Path(__file__).resolve().parents[1]


def _settings(**values: Any) -> AiAssistantSettings:
    return AiAssistantSettings(_env_file=None, **values)


# --- the approved question list ---------------------------------------------------------------


def test_the_approved_two_questions_apply_by_default_and_when_both_are_left_blank() -> None:
    assert (APPROVED_QUALIFICATION_QUESTIONS, APPROVED_QUALIFICATION_COUNT) == ("P01#1,P02#0", 2)
    for settings in (
        _settings(),
        # The example file's empty values (copied into a teammate's .env).
        _settings(local_api_test_qualification_questions="", local_api_test_qualification_count=0),
        _settings(
            local_api_test_qualification_questions="  ", local_api_test_qualification_count=0
        ),
    ):
        assert qualification_manifest(settings) == ["P01#1", "P02#0"]


@pytest.mark.parametrize(
    ("questions", "count"),
    [("", 2), ("P01#1", 2), ("P01#1,P02#0", 3), ("P01#1,P01#1", 2), ("nonsense", 1)],
)
def test_an_inconsistent_list_is_kept_as_given_and_refused_by_name(
    questions: str, count: int
) -> None:
    settings = _settings(
        local_api_test_qualification_questions=questions, local_api_test_qualification_count=count
    )
    assert settings.local_api_test_qualification_questions == questions  # never replaced
    assert qualification_manifest(settings) is None


def test_an_explicit_valid_list_is_kept() -> None:
    settings = _settings(
        local_api_test_qualification_questions="P01#1,P02#0,P06#1",
        local_api_test_qualification_count=3,
    )
    assert qualification_manifest(settings) == ["P01#1", "P02#0", "P06#1"]


def test_the_example_env_file_gives_the_approved_list() -> None:
    values = dotenv_values(ASSISTANT_DIR / ".env.example", interpolate=False)
    settings = _settings(
        local_api_test_qualification_questions=values[
            "AI_ASSISTANT_LOCAL_API_TEST_QUALIFICATION_QUESTIONS"
        ],
        local_api_test_qualification_count=int(
            values["AI_ASSISTANT_LOCAL_API_TEST_QUALIFICATION_COUNT"] or 0
        ),
    )
    assert qualification_manifest(settings) == ["P01#1", "P02#0"]


# --- Claude: the estimate and the start ----------------------------------------------------------


def _claude(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **extra: Any) -> HrJourney:
    journey = HrJourney(tmp_path, monkeypatch, **extra)
    Path(journey.settings.anthropic_ledger_path).unlink()  # a fresh session store, from the page
    assert journey.client.post(READ).status_code == 200
    assert journey.enable().status_code == 200
    test = journey.client.post(f"{API}/{FAST.profile_id}/connection-test")
    assert test.status_code == 200 and test.json()["outcome"] == "passed", test.text
    return journey


def _estimate(journey: HrJourney, profile_id: str = FAST.profile_id) -> dict[str, Any]:
    estimate: dict[str, Any] = journey.profile(profile_id)["paid_qualification"]
    return estimate


def _allowance(journey: HrJourney, provider: str, amount: int) -> None:
    started = journey.client.post(
        f"{API}/session/start",
        json={"provider": provider, "allowance_micro_usd": amount, "expected_session_id": None},
    )
    assert started.status_code == 200, started.text


def _start(journey: HrJourney, profile_id: str = FAST.profile_id) -> Any:
    return journey.client.post(f"{API}/{profile_id}/qualifications", json={"confirm_paid_calls": 2})


def test_a_deliberate_us1_session_qualifies_and_keeps_its_allowance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_model_management import wait_for

    journey = _claude(tmp_path, monkeypatch)
    estimate = _estimate(journey)
    # No session yet: the default allowance the first paid action opens.
    assert estimate["limits"]["session"] == 5_000_000
    _allowance(journey, "anthropic", 1_000_000)
    estimate = _estimate(journey)
    assert (
        estimate["calls"] == 2
        and estimate["estimate_micro_usd"] == 2 * estimate["reservation_micro_usd"]
    )
    assert estimate["limits"]["session"] == 1_000_000
    assert set(estimate["limits"]) == {"session", "daily", "lifetime"}  # no key limit for Claude
    assert estimate["effective_remaining_micro_usd"] == 1_000_000  # the session is the strictest
    assert (estimate["refusal"], estimate["blocking"], estimate["unavailable"]) == (
        None,
        None,
        None,
    )
    assert estimate["sufficient"] is True

    started = _start(journey)
    assert started.status_code == 202, started.text
    assert wait_for(journey.client, started.json()["qualification_id"])["status"] == "passed"
    session = journey.client.get(f"{API}/setup").json()["providers"]["anthropic"]["session"]
    assert session["allowance_micro_usd"] == 1_000_000  # never reset or raised
    assert session["calls"] == 2


def test_a_session_too_small_for_every_call_is_named_and_nothing_is_sent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = _claude(tmp_path, monkeypatch)
    reservation = _estimate(journey)["reservation_micro_usd"]
    _allowance(journey, "anthropic", reservation + 1)  # room for one call, not two
    estimate = _estimate(journey)
    assert estimate["blocking"] == "session" and estimate["sufficient"] is False
    assert estimate["refusal"] == "SESSION_ALLOWANCE_INSUFFICIENT"
    posts = journey.claude.posts
    refused = _start(journey)
    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "SESSION_ALLOWANCE_INSUFFICIENT"
    assert journey.claude.posts == posts  # no paid call


def test_a_daily_cap_below_the_estimate_is_named_as_the_daily_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ai_assistant.anthropic_runtime import worst_reservation

    reservation = worst_reservation()
    journey = _claude(tmp_path, monkeypatch, anthropic_daily_cap_micro_usd=reservation + 1)
    estimate = _estimate(journey)
    assert estimate["reservation_micro_usd"] == reservation
    assert estimate["blocking"] == "daily" and estimate["limits"]["session"] == 5_000_000
    assert estimate["refusal"] == "QUALIFICATION_BUDGET_INSUFFICIENT"
    assert _start(journey).json()["detail"]["code"] == "QUALIFICATION_BUDGET_INSUFFICIENT"


def test_a_lifetime_cap_below_the_estimate_is_named_as_the_lifetime_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = _claude(tmp_path, monkeypatch)
    reservation = _estimate(journey)["reservation_micro_usd"]
    # Calls admitted elsewhere in this store leave the lifetime cap with room for one call only.
    ledger = BudgetLedger(Path(journey.settings.anthropic_ledger_path))
    used = ledger.status().headroom - reservation - 1
    monkeypatch.setattr(
        type(ledger),
        "status",
        _with_headroom(type(ledger).status, used),
    )
    estimate = _estimate(journey)
    assert estimate["blocking"] == "lifetime" and estimate["sufficient"] is False
    assert _start(journey).json()["detail"]["code"] == "QUALIFICATION_BUDGET_INSUFFICIENT"


def _with_headroom(original: Any, used: int) -> Any:
    import dataclasses

    def status(self: BudgetLedger) -> Any:
        real = original(self)
        return dataclasses.replace(real, local_charged=real.local_charged + used)

    return status


def test_a_missing_question_list_is_a_setup_state_never_a_budget_shortfall(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = _claude(
        tmp_path,
        monkeypatch,
        local_api_test_qualification_questions="P01#1",
        local_api_test_qualification_count=2,
    )
    estimate = _estimate(journey)
    assert (estimate["calls"], estimate["estimate_micro_usd"]) == (None, None)
    assert estimate["unavailable"] == estimate["refusal"] == "REMOTE_MANIFEST_MISSING"
    assert estimate["blocking"] is None and estimate["limits"]["session"] == 5_000_000
    refused = journey.client.post(
        f"{API}/{FAST.profile_id}/qualifications", json={"confirm_paid_calls": 2}
    )
    assert refused.json()["detail"]["code"] == "REMOTE_MANIFEST_MISSING"


def test_a_missing_key_is_returned_by_name_with_the_setup_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = _claude(tmp_path, monkeypatch)
    journey.selector.environ = {}  # the key is gone (a restart, or the HR session ended)
    estimate = _estimate(journey)
    assert estimate["refusal"] == "CREDENTIAL_MISSING" and estimate["blocking"] is None
    refused = _start(journey)
    assert refused.status_code == 409
    detail = refused.json()["detail"]
    assert detail["code"] == "CREDENTIAL_MISSING"
    assert "not ready for a paid run" in detail["message"]
    assert "spending limits" not in detail["message"]


def test_an_existing_enablement_without_a_store_creates_it_when_confirmed_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = _claude(tmp_path, monkeypatch)
    path = Path(journey.settings.anthropic_ledger_path)
    path.unlink()  # an enablement record from before D-118: no session store
    view = journey.client.get(f"{API}/setup").json()["providers"]["anthropic"]
    assert view["ledger"] == "missing"
    assert _start(journey).json()["detail"]["code"] == "SPENDING_STORE_NOT_READY"
    assert journey.client.post(READ).status_code == 200
    assert journey.enable().status_code == 200  # the same record, confirmed again
    assert path.exists()
    assert BudgetLedger(path).profile().opening_basis == "session_store"


# --- GPT-OSS: the store and the key's own limit --------------------------------------------------


def test_gpt_oss_before_its_first_check_reports_the_store_not_a_shortfall(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_remote_test import Journey

    journey = Journey(tmp_path, monkeypatch)
    Path(journey.settings.budget_ledger_path).unlink()
    estimate = journey.client.get(API).json()["profiles"]
    remote = next(p for p in estimate if p["profile_id"] == OPENROUTER_PROFILE_ID)
    assert remote["paid_qualification"]["unavailable"] == "LEDGER_MISSING"
    refused = journey.start_qualification()
    assert refused.json()["detail"]["code"] == "SPENDING_STORE_NOT_READY"


def test_gpt_oss_key_limit_below_the_estimate_is_named_as_the_provider_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_remote_test import Journey

    journey = Journey(tmp_path, monkeypatch)
    test = journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/connection-test")
    assert test.json()["outcome"] == "passed", test.text
    profiles = journey.client.get(API).json()["profiles"]
    reservation = next(p for p in profiles if p["profile_id"] == OPENROUTER_PROFILE_ID)[
        "paid_qualification"
    ]["reservation_micro_usd"]
    remaining = (reservation + reservation // 2) / 1_000_000
    original = journey.openrouter.handler

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/key"):
            data = {"limit": 1.0, "limit_reset": None, "limit_remaining": remaining, "usage": 0}
            return httpx.Response(200, json={"data": data})
        return original(request)

    journey.selector.transport = httpx.MockTransport(handler)
    assert journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/connection-test").status_code == 200
    profiles = journey.client.get(API).json()["profiles"]
    estimate = next(p for p in profiles if p["profile_id"] == OPENROUTER_PROFILE_ID)[
        "paid_qualification"
    ]
    assert estimate["blocking"] == "provider" and "provider" in estimate["limits"]
    assert journey.start_qualification().json()["detail"]["code"] == "PROVIDER_KEY_LIMIT_EXHAUSTED"
    assert journey.openrouter.chats == []
