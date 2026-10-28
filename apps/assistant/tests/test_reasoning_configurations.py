"""GPT-OSS 120B naming and the optional low-reasoning ("Fast") configuration on AI Models.

The Fast configuration is the same model, endpoint, key, ledger and limits with reasoning
effort low. It is listed only when AI_ASSISTANT_REMOTE_LOW_REASONING_PROFILE_ENABLED is set,
has its own profile id and fingerprint, and needs its own (mock, here) qualification: the
configured (Balanced) one's never counts. A mock OpenRouter only; nothing is spent."""

from pathlib import Path
from typing import Any

import pytest

from ai_assistant import remote_test
from ai_assistant.model_admin_store import ModelAdminStore
from ai_assistant.model_catalog import OPENROUTER_FAST_PROFILE_ID, load_catalogue
from ai_assistant.model_profiles import OPENROUTER_PROFILE_ID
from ai_assistant.model_qualification import qualification_basis
from tests.test_model_management import API, profile, wait_for, write_profiles
from tests.test_remote_test import Journey, _settle_verification, config

FAST = OPENROUTER_FAST_PROFILE_ID


def _profiles(journey: Journey) -> dict[str, dict[str, Any]]:
    return {item["profile_id"]: item for item in journey.client.get(API).json()["profiles"]}


def _qualify_and_activate(journey: Journey, profile_id: str) -> dict[str, Any]:
    test = journey.client.post(f"{API}/{profile_id}/connection-test")
    assert test.status_code == 200 and test.json()["outcome"] == "passed", test.text
    calls = journey.client.get(API).json()["recovery"]["qualification_cost"]["paid_calls"]
    started = journey.client.post(
        f"{API}/{profile_id}/qualifications", json={"confirm_paid_calls": calls}
    )
    assert started.status_code == 202, started.text
    result = wait_for(journey.client, started.json()["qualification_id"])
    assert result["status"] == "passed", result
    revision = journey.client.get(API).json()["revision"]
    applied = journey.client.post(
        f"{API}/{profile_id}/activate",
        json={"expected_revision": revision, "acknowledge_quality_unscored": True},
    )
    assert applied.status_code == 200, applied.text
    return result


def _efforts(journey: Journey) -> list[str]:
    return [body["reasoning"]["effort"] for body in journey.openrouter.chats]


# --- naming -----------------------------------------------------------------------------------


def test_the_remote_model_is_named_by_model_and_reasoning_not_by_its_decision(
    tmp_path: Path,
) -> None:
    settings = config(tmp_path, write_profiles(tmp_path / "profiles.json", profile()))
    (entry,) = [e for e in load_catalogue(settings).entries if e.source == "code"]
    assert entry.profile_id == OPENROUTER_PROFILE_ID  # stable id
    assert entry.display_name == "GPT-OSS 120B (reasoning medium)"
    assert "D-094" not in entry.display_name and "synthetic" not in entry.display_name
    assert dict(entry.details) == {
        "model": "GPT-OSS 120B",
        "provider": "OPENROUTER_DEEPINFRA",
        "scope": "APPROVED_SYNTHETIC_CASE",
        "reasoning_effort": "medium",
        "decision": "D-094",
    }
    development = config(
        tmp_path,
        write_profiles(tmp_path / "profiles.json", profile()),
        synthetic_dev_decision="D-095",
    )
    (entry,) = [e for e in load_catalogue(development).entries if e.source == "code"]
    assert dict(entry.details)["scope"] == "VERIFIED_SYNTHETIC_CASES"
    assert dict(entry.details)["decision"] == "D-095"
    # The pending (not authorised) entry keeps its own fingerprint and says so.
    from ai_assistant.config import AiAssistantSettings

    (pending,) = [
        e for e in load_catalogue(AiAssistantSettings(_env_file=None)).entries if e.source == "code"
    ]
    assert pending.status == "pending_authorisation"
    assert dict(pending.details)["scope"] == "NOT_AUTHORISED"


def test_the_configured_entry_keeps_its_fingerprint_so_its_qualification_stays_current(
    tmp_path: Path,
) -> None:
    settings = config(tmp_path, write_profiles(tmp_path / "profiles.json", profile()))
    for flag in (False, True):
        variant = settings.model_copy(update={"remote_low_reasoning_profile_enabled": flag})
        entry = load_catalogue(variant).get(OPENROUTER_PROFILE_ID)
        assert entry is not None
        assert entry.fingerprint == remote_test.remote_fingerprint(settings)
        assert entry.settings_update == ()


# --- the Fast configuration ------------------------------------------------------------------


def test_fast_is_not_listed_unless_enabled(tmp_path: Path) -> None:
    settings = config(tmp_path, write_profiles(tmp_path / "profiles.json", profile()))
    assert load_catalogue(settings).get(FAST) is None
    enabled = settings.model_copy(update={"remote_low_reasoning_profile_enabled": True})
    fast = load_catalogue(enabled).get(FAST)
    assert fast is not None and fast.status == "selectable"
    assert fast.display_name == "GPT-OSS 120B (reasoning low)"
    assert dict(fast.details)["reasoning_effort"] == "low"
    assert fast.fingerprint != load_catalogue(enabled).get(OPENROUTER_PROFILE_ID).fingerprint  # type: ignore[union-attr]
    # Already low: no second, identical configuration.
    low = enabled.model_copy(update={"llm_reasoning_effort": "low"})
    assert load_catalogue(low).get(FAST) is None


def test_fast_needs_its_own_qualification_and_then_asks_for_low_reasoning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, remote_low_reasoning_profile_enabled=True)
    _qualify_and_activate(journey, OPENROUTER_PROFILE_ID)
    assert set(_efforts(journey)) == {"medium"}
    profiles = _profiles(journey)
    assert profiles[OPENROUTER_PROFILE_ID]["active"]
    # Balanced's passing qualification does not count for Fast.
    assert profiles[FAST]["activation_blockers"] == ["NOT_QUALIFIED"]
    assert profiles[FAST]["qualification"] is None
    revision = journey.client.get(API).json()["revision"]
    refused = journey.client.post(
        f"{API}/{FAST}/activate",
        json={"expected_revision": revision, "acknowledge_quality_unscored": True},
    )
    assert refused.status_code == 409 and refused.json()["detail"]["code"] == "NOT_QUALIFIED"
    assert journey.client.get(API).json()["revision"] == revision  # nothing changed

    # Its own qualification runs at reasoning effort low, then it may be activated.
    calls = len(journey.openrouter.chats)
    _qualify_and_activate(journey, FAST)
    assert set(_efforts(journey)[calls:]) == {"low"}
    assert _profiles(journey)[FAST]["active"]
    asked = len(journey.openrouter.chats)
    assert journey.ask()["answered_by"] == "model"
    _settle_verification()
    assert _efforts(journey)[asked:] == ["low"]
    # Balanced still qualified, unchanged.
    profiles = _profiles(journey)
    assert profiles[OPENROUTER_PROFILE_ID]["activation_blockers"] == []
    assert profiles[OPENROUTER_PROFILE_ID]["qualification"]["current"]


def test_hr_spending_controls_keep_fasts_reasoning_effort(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, remote_low_reasoning_profile_enabled=True)
    _qualify_and_activate(journey, FAST)
    revision = journey.client.get(f"{API}/budget").json()["controls"]["revision"]
    saved = journey.client.put(
        f"{API}/budget/controls",
        json={"expected_revision": revision, "daily_cap_micro_usd": 900_000, "max_calls": 50},
    )
    assert saved.status_code == 200, saved.text
    asked = len(journey.openrouter.chats)
    assert journey.ask()["answered_by"] == "model"
    _settle_verification()
    assert _efforts(journey)[asked:] == ["low"]
    model = journey.selector.current().model
    assert model._settings.llm_reasoning_effort == "low"  # noqa: SLF001
    assert model._settings.budget_daily_cap_micro_usd == 900_000  # noqa: SLF001


def test_a_stored_fast_activation_reverts_when_fast_is_no_longer_offered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, remote_low_reasoning_profile_enabled=True)
    _qualify_and_activate(journey, FAST)
    store = ModelAdminStore(Path(journey.settings.model_admin_db_path))
    from ai_assistant.model_admin import ModelSelector

    restarted = ModelSelector(
        journey.settings.model_copy(update={"remote_low_reasoning_profile_enabled": False}),
        None,
        store,
        environ=journey.selector.environ,
        transport=journey.selector.transport,
    )
    active = restarted.current()
    assert active.profile_id != FAST and active.reverted == "PROFILE_MISSING"
    actions = [event["action"] for event in store.events(20)]
    assert "STARTUP_REVERTED" in actions


def test_the_qualification_basis_is_the_same_for_both_configurations(tmp_path: Path) -> None:
    # One code basis; the configurations differ only in their fingerprints.
    assert len(qualification_basis()) == 64
    settings = config(
        tmp_path,
        write_profiles(tmp_path / "profiles.json", profile()),
        remote_low_reasoning_profile_enabled=True,
    )
    catalogue = load_catalogue(settings)
    fingerprints = {
        catalogue.get(OPENROUTER_PROFILE_ID).fingerprint,
        catalogue.get(FAST).fingerprint,
    }  # type: ignore[union-attr]
    assert len(fingerprints) == 2
