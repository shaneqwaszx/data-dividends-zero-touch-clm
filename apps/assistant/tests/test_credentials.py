"""D-095 addendum: the OpenRouter key from the process environment, the git-ignored .env, or an
HR administrator (server memory only). Fake keys, a mock OpenRouter and the fake CLM backend
only; no real key is read and nothing is spent."""

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from ai_assistant import credentials, model_admin
from ai_assistant.budget import BudgetLedger
from ai_assistant.main import create_app
from ai_assistant.model_factory import resolve_remote_credential
from ai_assistant.model_profiles import OPENROUTER_PROFILE_ID, ProfileConfigError
from tests.test_model_management import API, ORIGIN
from tests.test_remote_test import Journey, _settle_verification

# Fake keys in an OpenRouter-like shape, built at run time so the secret scanner never sees a
# key-shaped literal; the variable name likewise (no literal assignment to it).
NAME = credentials.CREDENTIAL_VARIABLE
_PREFIX = "sk-" + "or-"
ENV_KEY = _PREFIX + "v1-fake-environment-key-000000000001"
FILE_KEY = _PREFIX + "v1-fake-dotenv-key-0000000000000002"
HR_KEY = _PREFIX + "v1-fake-hr-entered-key-000000000003"
HR_KEY_2 = _PREFIX + "v1-fake-hr-replacement-key-0000004"
KEYS = (ENV_KEY, FILE_KEY, HR_KEY, HR_KEY_2)
CREDENTIAL = f"{API}/credential"


def _dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, text: str) -> Path:
    path = tmp_path / ".env"
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(credentials, "ENV_FILE", path)
    return path


# --- resolution order -------------------------------------------------------------------------


def test_a_missing_key_is_reported_and_refused() -> None:
    key, status = credentials.resolve()
    assert key is None and status.view()["status"] == "missing"
    assert status.view()["source"] == "none" and status.hr_editable
    with pytest.raises(ProfileConfigError) as refused:
        resolve_remote_credential()
    assert refused.value.code == "CREDENTIAL_MISSING"


def test_the_process_environment_key_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", ENV_KEY)
    key, status = credentials.resolve()
    assert key is not None and key.get_secret_value() == ENV_KEY
    assert (status.source, status.status, status.hr_editable) == (
        "environment",
        "configured",
        False,
    )


def test_the_dotenv_key_is_used_without_touching_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _dotenv(
        tmp_path,
        monkeypatch,
        f"# local only\nAI_ASSISTANT_LLM_ENABLED=true\n{NAME}={FILE_KEY}\n",
    )
    key, status = credentials.resolve()
    assert key is not None and key.get_secret_value() == FILE_KEY
    assert status.source == "env_file" and not status.hr_editable
    assert "OPENROUTER_API_KEY" not in os.environ
    assert resolve_remote_credential().get_secret_value() == FILE_KEY


def test_quoted_and_exported_dotenv_lines_are_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _dotenv(tmp_path, monkeypatch, f'export {NAME}="{FILE_KEY}"\r\n')
    key, _ = credentials.resolve()
    assert key is not None and key.get_secret_value() == FILE_KEY


def test_the_hr_key_is_the_last_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    credentials.HR_STORE.set(SecretStr(HR_KEY), "hr-admin")
    key, status = credentials.resolve()
    assert key is not None and key.get_secret_value() == HR_KEY
    assert status.view()["source"] == "hr_memory" and status.view()["persistence"] == "memory_only"
    _dotenv(tmp_path, monkeypatch, f"{NAME}={FILE_KEY}\n")
    assert credentials.resolve()[0].get_secret_value() == FILE_KEY  # type: ignore[union-attr]
    monkeypatch.setenv("OPENROUTER_API_KEY", ENV_KEY)
    assert credentials.resolve()[0].get_secret_value() == ENV_KEY  # type: ignore[union-attr]


def test_an_invalid_key_does_not_fall_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    credentials.HR_STORE.set(SecretStr(HR_KEY), "hr-admin")
    monkeypatch.setenv("OPENROUTER_API_KEY", "bad key with spaces")
    key, status = credentials.resolve()
    assert key is None and (status.source, status.status) == ("environment", "invalid")
    monkeypatch.delenv("OPENROUTER_API_KEY")
    _dotenv(tmp_path, monkeypatch, f"{NAME}=bad key\n")
    key, status = credentials.resolve()
    assert key is None and (status.source, status.status) == ("env_file", "invalid")


def test_explicit_mappings_ignore_dotenv_and_hr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tests and seams that pass their own mapping get exactly that mapping."""

    credentials.HR_STORE.set(SecretStr(HR_KEY), "hr-admin")
    _dotenv(tmp_path, monkeypatch, f"{NAME}={FILE_KEY}\n")
    assert credentials.resolve({})[0] is None
    assert credentials.resolve({NAME: ENV_KEY})[0].get_secret_value() == ENV_KEY  # type: ignore[union-attr]


def test_a_restart_forgets_the_hr_key() -> None:
    credentials.HR_STORE.set(SecretStr(HR_KEY), "hr-admin")
    restarted = credentials.HrCredential()
    key, status = credentials.resolve(os.environ, store=restarted)
    assert key is None and status.view()["status"] == "missing"


def test_the_status_and_the_secret_never_show_the_key() -> None:
    credentials.HR_STORE.set(SecretStr(HR_KEY), "hr-admin")
    key, status = credentials.resolve()
    assert HR_KEY not in repr(key) and HR_KEY not in str(key)
    assert HR_KEY not in repr(status) and HR_KEY not in str(status.view())
    assert HR_KEY not in str(credentials.identity(key))


# --- the AI Models page: HR only, never the key back -------------------------------------------


def _journey(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **extra: Any) -> Journey:
    journey = Journey(tmp_path, monkeypatch, **extra)
    journey.selector.environ = None  # the service's own resolution: env, .env, HR memory
    return journey


def _put(journey: Journey, key: Any = HR_KEY, **kwargs: Any) -> Any:
    return journey.client.put(CREDENTIAL, json={"api_key": key}, **kwargs)


def test_hr_sees_not_configured_then_saves_tests_and_clears_a_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    journey = _journey(tmp_path, monkeypatch)
    status = journey.client.get(CREDENTIAL).json()
    assert status["status"] == "missing" and status["hr_editable"]
    test = journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/connection-test").json()
    assert test["outcome"] == "failed"

    saved = _put(journey)
    assert saved.status_code == 200, saved.text
    assert saved.json()["source"] == "hr_memory" and saved.json()["status"] == "configured"
    assert saved.json()["set_by"] == "hr-admin"
    test = journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/connection-test").json()
    assert test["outcome"] == "passed", test
    # The key went to OpenRouter (the mock) as the bearer token, nowhere else.
    assert any(
        request.headers.get("authorization") == f"Bearer {HR_KEY}"
        for request in journey.openrouter.requests
    )

    cleared = journey.client.delete(CREDENTIAL)
    assert cleared.status_code == 200 and cleared.json()["status"] == "missing"
    again = journey.client.delete(CREDENTIAL)
    assert (
        again.status_code == 409 and again.json()["detail"]["code"] == "CREDENTIAL_NOT_HR_MANAGED"
    )

    texts = [
        journey.client.get(API).text,
        journey.client.get(f"{API}/audit").text,
        journey.client.get(f"{API}/budget").text,
        caplog.text,
    ]
    assert all(HR_KEY not in text for text in texts)
    actions = [event["action"] for event in journey.client.get(f"{API}/audit").json()["events"]]
    assert "CREDENTIAL_SET" in actions and "CREDENTIAL_CLEARED" in actions


def test_an_environment_or_dotenv_key_cannot_be_replaced_or_cleared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = _journey(tmp_path, monkeypatch)
    _dotenv(tmp_path, monkeypatch, f"{NAME}={FILE_KEY}\n")
    status = journey.client.get(CREDENTIAL).json()
    assert status["source"] == "env_file" and not status["hr_editable"]
    for reply in (_put(journey), journey.client.delete(CREDENTIAL)):
        assert reply.status_code == 409
        assert reply.json()["detail"]["code"] == "CREDENTIAL_ENVIRONMENT_MANAGED"
    monkeypatch.setenv("OPENROUTER_API_KEY", ENV_KEY)
    assert journey.client.get(CREDENTIAL).json()["source"] == "environment"
    assert _put(journey).status_code == 409
    assert credentials.HR_STORE.snapshot()[0] is None
    assert (
        ENV_KEY not in journey.client.get(API).text and FILE_KEY not in journey.client.get(API).text
    )


@pytest.mark.parametrize("session", ["rm-session", "co-session", "director-session"])
def test_other_roles_cannot_see_or_change_the_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, session: str
) -> None:
    journey = _journey(tmp_path, monkeypatch)
    journey.client.cookies.set("clm_session", session)
    assert journey.client.get(CREDENTIAL).status_code == 403
    assert _put(journey).status_code == 403
    assert journey.client.delete(CREDENTIAL).status_code == 403
    assert credentials.HR_STORE.snapshot()[0] is None
    journey.client.cookies.set("clm_session", "hr-session")
    events = journey.client.get(f"{API}/audit").json()["events"]
    assert any(event["action"] == "ACCESS_REFUSED" for event in events)


@pytest.mark.parametrize(
    "body",
    [
        {"api_key": "not-an-openrouter-key"},
        {"api_key": "sk-or-short"},
        {"api_key": HR_KEY + " extra"},
        {"api_key": HR_KEY, "other": 1},
        {"key": HR_KEY},
        {"api_key": 12345},
    ],
)
def test_an_invalid_key_is_refused_without_echoing_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: dict[str, Any]
) -> None:
    journey = _journey(tmp_path, monkeypatch)
    reply = journey.client.put(CREDENTIAL, json=body)
    assert reply.status_code == 400 and reply.json()["detail"]["code"] == "CREDENTIAL_INVALID"
    assert "not-an-openrouter-key" not in reply.text and HR_KEY not in reply.text
    assert credentials.HR_STORE.snapshot()[0] is None


def test_a_change_needs_an_allowed_origin_and_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = _journey(tmp_path, monkeypatch)
    no_origin = journey.client.put(CREDENTIAL, json={"api_key": HR_KEY}, headers={"Origin": ""})
    assert no_origin.status_code == 403
    other = journey.client.put(
        CREDENTIAL, json={"api_key": HR_KEY}, headers={"Origin": "http://evil.example"}
    )
    assert other.status_code == 403
    form = journey.client.put(
        CREDENTIAL,
        content=HR_KEY,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert form.status_code == 400
    assert journey.client.delete(CREDENTIAL, headers={"Origin": ""}).status_code == 403
    assert credentials.HR_STORE.snapshot()[0] is None


def test_key_changes_are_rate_limited(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    journey = _journey(tmp_path, monkeypatch)
    for _ in range(model_admin.CREDENTIAL_ATTEMPTS):
        assert _put(journey, "wrong").status_code == 400
    limited = _put(journey)
    assert limited.status_code == 429
    assert limited.json()["detail"]["code"] == "CREDENTIAL_RATE_LIMITED"
    assert credentials.HR_STORE.snapshot()[0] is None


def test_the_qualification_process_gets_an_hr_key_only_in_its_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert model_admin.qualification_environment() is None  # no key: inherit as before
    monkeypatch.setenv("OPENROUTER_API_KEY", ENV_KEY)
    assert model_admin.qualification_environment() is None  # inherited from the environment
    monkeypatch.delenv("OPENROUTER_API_KEY")
    credentials.HR_STORE.set(SecretStr(HR_KEY), "hr-admin")
    env = model_admin.qualification_environment()
    assert env is not None and env[NAME] == HR_KEY

    seen: dict[str, Any] = {}

    class Popen:
        def __init__(self, args: list[str], **kwargs: Any) -> None:
            seen["args"], seen["env"] = args, kwargs.get("env")

    monkeypatch.setattr(subprocess, "Popen", Popen)
    selector = object.__new__(model_admin.ModelSelector)
    selector.settings = type("S", (), {})()  # only what _launch_process reads
    monkeypatch.setattr(model_admin, "profiles_path", lambda settings: Path("profiles.json"))
    monkeypatch.setattr(model_admin, "store_file", lambda settings: Path("state.sqlite3"))
    model_admin.ModelSelector._launch_process(selector, "a" * 32)
    assert all(HR_KEY not in str(arg) for arg in seen["args"])
    assert seen["env"][NAME] == HR_KEY


def test_hr_key_qualifies_activates_and_a_new_key_cannot_evade_the_daily_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = _journey(tmp_path, monkeypatch, synthetic_dev_decision="D-095")
    assert _put(journey).status_code == 200
    journey.activate_remote()
    assert journey.ask()["answered_by"] == "model"
    _settle_verification()
    ledger = BudgetLedger.open(Path(journey.settings.budget_ledger_path))
    before = ledger.daily_status().settled_today
    key_checks = sum(1 for r in journey.openrouter.requests if r.url.path.endswith("/key"))

    # Replace the key: the next call rebuilds with it and runs the full preflight again.
    assert journey.client.delete(CREDENTIAL).status_code == 200
    assert journey.ask()["answered_by"] == "case_data"  # no key: nothing is sent
    assert _put(journey, HR_KEY_2).status_code == 200
    assert journey.ask()["answered_by"] == "model"
    _settle_verification()
    assert sum(1 for r in journey.openrouter.requests if r.url.path.endswith("/key")) > key_checks
    chats = [r for r in journey.openrouter.requests if r.url.path.endswith("/chat/completions")]
    assert chats[-1].headers["authorization"] == f"Bearer {HR_KEY_2}"
    # Today's spend carried over the key change: the daily allowance is the ledger's.
    assert ledger.daily_status().settled_today == before + 720
    budget = journey.client.get(f"{API}/budget").json()
    assert budget["daily"]["settled_today_micro_usd"] == before + 720
    assert budget["credential"]["source"] == "hr_memory"
    assert all(key not in journey.client.get(API).text for key in KEYS)


def test_after_a_restart_an_hr_key_must_be_entered_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = _journey(tmp_path, monkeypatch)
    assert _put(journey).status_code == 200
    journey.activate_remote()
    # The service restarts: its memory, and so the HR key, is gone.
    monkeypatch.setattr(credentials, "HR_STORE", credentials.HrCredential())
    app = create_app(
        journey.settings,
        clm_transport=httpx.MockTransport(lambda request: journey.backend.handler(request)),
    )
    client = TestClient(app, headers={"Origin": ORIGIN})
    client.cookies.set("clm_session", "hr-session")
    overview = client.get(API).json()
    assert overview["active"]["profile_id"] != OPENROUTER_PROFILE_ID
    assert overview["active"]["reverted"] == "CREDENTIAL_MISSING"
    assert overview["budget"]["credential"]["status"] == "missing"
    assert overview["budget"]["credential"]["persistence"] == "memory_only"
