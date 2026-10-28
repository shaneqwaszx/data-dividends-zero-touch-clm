"""D-098: AI model qualification lifecycle and HR recovery (mock OpenRouter only; nothing
is spent and no real model is called).

A. a run whose supervising service has gone is closed as interrupted, never restarted.
"""

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from ai_assistant.model_admin import ModelSelector
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
