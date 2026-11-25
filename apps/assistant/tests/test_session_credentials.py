"""D-106: an HR administrator's OpenRouter or Anthropic key is bound to the HR session that
entered it. It is used before an environment or .env key, dropped when that session ends,
held back when the session cannot be checked, and handed to a qualification process on its
standard input only. Fake keys, mock providers and the fake CLM backend only; nothing is
spent and no real key is read."""

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from ai_assistant import anthropic_runtime, key_sources, model_admin
from ai_assistant.anthropic_profiles import BALANCED
from ai_assistant.anthropic_runtime import ClaudeTestModel, resolve_key
from ai_assistant.model_profiles import OPENROUTER_PROFILE_ID, ProfileConfigError
from scripts.qualify_model import MAX_HANDOFF_BYTES, take_handoff
from tests.test_claude_runtime import (
    MESSAGES,
    VAR,
    Claude,
    _ask,
    claude_config,
    claude_ledger,
)
from tests.test_credentials import HR_KEY, HR_KEY_2, _journey
from tests.test_model_management import API

ANTHROPIC_KEY = "sk-" + "ant-" + "api03-" + "HrSessionSentinel" * 3
SERVER_KEY = "sk-" + "ant-" + "api03-" + "ServerKeySentinel" * 3
ADMIN_KEY = "sk-" + "ant-" + "admin01-" + "AdminKeySentinel" * 3
CLAUDE_CREDENTIAL = f"{API}/credential/anthropic"
OPENROUTER_CREDENTIAL = f"{API}/credential"


def _with_check(answers: list[bool | None]) -> list[str]:
    """Install a session check answering ``answers`` in turn; returns the users asked about."""

    asked: list[str] = []

    def check(session: SecretStr, user_id: str) -> bool | None:
        asked.append(user_id)
        return answers.pop(0) if answers else True

    key_sources.install_session_check(check)
    return asked


# --- the store: session-bound, dropped or held back ------------------------------------------


def test_an_ended_session_drops_the_key_and_releases_the_server_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(VAR, SERVER_KEY)
    _with_check([True, False])
    key_sources.ANTHROPIC_STORE.set(SecretStr(ANTHROPIC_KEY), "biz-ops", session=SecretStr("s"))
    key, status, _ = resolve_key(max_age=0)
    assert key is not None and key.get_secret_value() == ANTHROPIC_KEY
    assert status.source == "hr_session" and status.fallback == "environment"
    key, status, _ = resolve_key(max_age=0)  # the HR session ended
    assert key is not None and key.get_secret_value() == SERVER_KEY
    assert status.source == "environment"
    assert key_sources.ANTHROPIC_STORE.snapshot()[0] is None


def test_a_session_that_cannot_be_checked_holds_the_key_back_with_no_fallthrough(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(VAR, SERVER_KEY)
    _with_check([None, True])
    key_sources.ANTHROPIC_STORE.set(SecretStr(ANTHROPIC_KEY), "biz-ops", session=SecretStr("s"))
    key, status, code = resolve_key(max_age=0)
    assert key is None and code == "CREDENTIAL_SESSION_UNVERIFIED"
    assert status.source == "hr_session" and status.status == "unverified"
    # No earlier check vouches for it now: a view within 10 s checks again.
    assert key_sources.ANTHROPIC_STORE.current().held is False  # the next answer is True
    # Held back, not dropped: once the session answers again the HR key is used.
    key, _, _ = resolve_key(max_age=0)
    assert key is not None and key.get_secret_value() == ANTHROPIC_KEY


def test_no_installed_check_means_no_hr_key_is_used() -> None:
    key_sources.HR_STORE.set(SecretStr(HR_KEY), "biz-ops", session=SecretStr("s"))
    key, status = key_sources.resolve(max_age=0)
    assert key is None and status.status == "unverified"


def test_a_key_never_outlives_the_backend_session_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    _with_check([])
    key_sources.HR_STORE.set(SecretStr(HR_KEY), "biz-ops", session=SecretStr("s"))
    key, status = key_sources.resolve()
    assert key is not None and status.expires_at == status.set_at + 8 * 3600  # type: ignore[operator]
    later = time.time() + key_sources.SESSION_LIMIT_SECONDS + 1
    monkeypatch.setattr(key_sources.time, "time", lambda: later)
    assert key_sources.resolve()[0] is None
    assert key_sources.HR_STORE.snapshot()[0] is None


def test_views_reuse_a_recent_check_and_calls_always_check_again() -> None:
    asked = _with_check([])
    key_sources.HR_STORE.set(SecretStr(HR_KEY), "biz-ops", session=SecretStr("s"))
    key_sources.resolve()
    key_sources.resolve()
    assert asked == []  # just entered: verified then
    key_sources.resolve(max_age=0)
    key_sources.resolve(max_age=0)
    assert asked == ["biz-ops", "biz-ops"]


def test_a_check_racing_a_change_never_drops_the_newer_key() -> None:
    def check(session: SecretStr, user_id: str) -> bool | None:
        # The old entry's session ended, but HR entered a new key meanwhile.
        key_sources.HR_STORE.set(SecretStr(HR_KEY_2), "biz-ops", session=SecretStr("new"))
        key_sources.install_session_check(lambda session, user_id: True)
        return False

    key_sources.install_session_check(check)
    key_sources.HR_STORE.set(SecretStr(HR_KEY), "biz-ops", session=SecretStr("old"))
    key, _ = key_sources.resolve(max_age=0)
    assert key is not None and key.get_secret_value() == HR_KEY_2


# --- the service's check: the HR session itself, through the CLM backend ---------------------


def test_the_service_checks_the_entering_hr_session_not_the_rm_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = _journey(tmp_path, monkeypatch)
    journey.client.cookies.set("clm_session", "hr2-session")
    assert journey.client.put(OPENROUTER_CREDENTIAL, json={"api_key": HR_KEY}).status_code == 200
    journey.client.cookies.set("clm_session", "hr-session")
    seen: list[str | None] = []
    handler = journey.backend.handler

    def recording(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/me":
            seen.append(request.headers.get("cookie"))
        return handler(request)

    monkeypatch.setattr(journey.backend, "handler", recording)
    key, status = key_sources.resolve(max_age=0)
    assert key is not None and status.set_by == "hr-second"
    assert seen == ["clm_session=hr2-session"]
    # The second HR administrator signs out: the key is dropped at its next use.
    journey.backend.revoked.add("hr2-session")
    key, status = key_sources.resolve(max_age=0)
    assert key is None and status.source == "none"
    view = journey.client.get(OPENROUTER_CREDENTIAL).json()
    assert view["source"] == "none" and HR_KEY not in json.dumps(view)


def test_an_unreachable_backend_holds_the_key_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = _journey(tmp_path, monkeypatch)
    assert journey.client.put(OPENROUTER_CREDENTIAL, json={"api_key": HR_KEY}).status_code == 200

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    monkeypatch.setattr(journey.backend, "handler", down)
    key, status = key_sources.resolve(max_age=0)
    assert key is None and status.status == "unverified"
    assert key_sources.HR_STORE.snapshot()[0] is not None


def test_the_rm_cannot_keep_using_a_revoked_hr_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_synthetic_eligibility import GARDEN, serve

    journey = _journey(tmp_path, monkeypatch, synthetic_dev_decision="D-095")
    journey.client.cookies.set("clm_session", "hr2-session")
    assert journey.client.put(OPENROUTER_CREDENTIAL, json={"api_key": HR_KEY}).status_code == 200
    journey.client.cookies.set("clm_session", "hr-session")
    journey.activate_remote()
    serve(monkeypatch, GARDEN)
    assert journey.ask()["answered_by"] == "model"
    chats = sum(1 for r in journey.openrouter.requests if r.url.path.endswith("/chat/completions"))
    journey.backend.revoked.add("hr2-session")  # that HR administrator signed out
    # The RM's own session is still valid, but no server key exists: nothing is sent.
    assert journey.ask()["answered_by"] == "case_data"
    after = sum(1 for r in journey.openrouter.requests if r.url.path.endswith("/chat/completions"))
    assert after == chats


# --- Anthropic: its own key section, the same rules ------------------------------------------


def test_hr_enters_tests_and_clears_an_anthropic_session_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = _journey(tmp_path, monkeypatch)
    view = journey.client.get(CLAUDE_CREDENTIAL).json()
    assert view["status"] == "missing" and view["hr_editable"]
    for bad in (ADMIN_KEY, HR_KEY):  # five changes per window: two refusals, set, clear
        refused = journey.client.put(CLAUDE_CREDENTIAL, json={"api_key": bad})
        assert refused.status_code == 400 and bad not in refused.text
    saved = journey.client.put(CLAUDE_CREDENTIAL, json={"api_key": ANTHROPIC_KEY})
    assert saved.status_code == 200, saved.text
    assert saved.json()["source"] == "hr_session" and saved.json()["set_by"] == "biz-ops"
    assert key_sources.HR_STORE.snapshot()[0] is None  # the OpenRouter key is separate
    assert journey.client.get(OPENROUTER_CREDENTIAL).json()["source"] == "none"
    texts = [journey.client.get(p).text for p in (API, f"{API}/audit", f"{API}/budget")]
    assert all(ANTHROPIC_KEY not in text for text in texts)
    events = journey.client.get(f"{API}/audit").json()["events"]
    assert any(e["action"] == "CREDENTIAL_SET" and e["profile_id"] == "anthropic" for e in events)
    cleared = journey.client.delete(CLAUDE_CREDENTIAL)
    assert cleared.status_code == 200 and cleared.json()["source"] == "none"
    assert journey.client.delete(CLAUDE_CREDENTIAL).status_code == 409


@pytest.mark.parametrize("session", ["rm-session", "co-session", "director-session"])
def test_other_roles_cannot_see_or_set_the_anthropic_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, session: str
) -> None:
    journey = _journey(tmp_path, monkeypatch)
    journey.client.cookies.set("clm_session", session)
    assert journey.client.get(CLAUDE_CREDENTIAL).status_code == 403
    assert journey.client.put(CLAUDE_CREDENTIAL, json={"api_key": ANTHROPIC_KEY}).status_code == 403
    assert journey.client.delete(CLAUDE_CREDENTIAL).status_code == 403
    assert key_sources.ANTHROPIC_STORE.snapshot()[0] is None


def test_a_claude_call_uses_the_hr_key_and_must_still_name_the_workspace(
    tmp_path: Path,
) -> None:
    settings = claude_config(tmp_path)
    claude_ledger(settings)
    claude = Claude()
    asked = _with_check([])
    key_sources.ANTHROPIC_STORE.set(SecretStr(ANTHROPIC_KEY), "biz-ops", session=SecretStr("s"))
    model = ClaudeTestModel(settings, BALANCED.profile_id, transport=claude.transport())
    pieces, error = _ask(model, MESSAGES)
    assert error is None and pieces
    assert asked  # the HR session was checked for the call
    assert all(r.headers["x-api-key"] == ANTHROPIC_KEY for r in claude.requests)
    # A key from another workspace is refused before any message is sent.
    claude.workspace = "wrkspc_SomeOtherWorkspace"
    key_sources.ANTHROPIC_STORE.set(SecretStr(SERVER_KEY), "biz-ops", session=SecretStr("s"))
    posts = claude.posts
    _, error = _ask(model, MESSAGES)
    assert error is not None and claude.posts == posts
    anthropic_runtime._last.clear()


# --- the qualification process ---------------------------------------------------------------


def test_the_process_takes_only_valid_handed_over_keys() -> None:
    payload = json.dumps({"openrouter": HR_KEY, "anthropic": ANTHROPIC_KEY}).encode()
    assert take_handoff(payload)
    assert key_sources.HR_STORE.snapshot()[0].get_secret_value() == HR_KEY  # type: ignore[union-attr]
    key, _, _ = resolve_key(max_age=0)
    assert key is not None and key.get_secret_value() == ANTHROPIC_KEY
    assert take_handoff(b"")  # nothing handed over
    for bad in (
        b"not json",
        json.dumps({"other": HR_KEY}).encode(),
        json.dumps({"anthropic": ADMIN_KEY}).encode(),
        json.dumps(["x"]).encode(),
        b"{" + b" " * MAX_HANDOFF_BYTES + b"}",
    ):
        assert not take_handoff(bad)
    assert VAR not in os.environ and key_sources.CREDENTIAL_VARIABLE not in os.environ


def test_a_running_qualification_ends_when_its_handed_key_is_revoked() -> None:
    _with_check([])
    key_sources.ANTHROPIC_STORE.set(SecretStr(ANTHROPIC_KEY), "biz-ops", session=SecretStr("s"))
    payload, generations = model_admin.qualification_handoff("anthropic")
    assert set(generations) == {"anthropic"} and ANTHROPIC_KEY in payload.decode()
    assert not model_admin.handoff_revoked(generations)
    key_sources.ANTHROPIC_STORE.set(SecretStr(SERVER_KEY), "biz-ops", session=SecretStr("s"))
    assert model_admin.handoff_revoked(generations)  # replaced
    _, generations = model_admin.qualification_handoff("anthropic")
    key_sources.ANTHROPIC_STORE.clear()
    assert model_admin.handoff_revoked(generations)  # cleared


def test_the_supervisor_stops_the_run_and_records_why(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = _journey(tmp_path, monkeypatch)
    assert journey.client.put(OPENROUTER_CREDENTIAL, json={"api_key": HR_KEY}).status_code == 200
    generation = key_sources.HR_STORE.snapshot()[3]

    class Forever:
        killed = False

        def poll(self) -> int | None:
            return 0 if self.killed else None

        def kill(self) -> None:
            self.killed = True

        def wait(self) -> int:
            return 0

    handle = Forever()

    def launch(qualification_id: str) -> Any:
        journey.selector.handoffs[qualification_id] = {"openrouter": generation}
        return handle

    journey.selector.launch = launch
    test = journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/connection-test")
    assert test.json()["outcome"] == "passed", test.text
    started = journey.start_qualification()
    assert started.status_code == 202, started.text
    assert journey.client.delete(OPENROUTER_CREDENTIAL).status_code == 200
    qid = started.json()["qualification_id"]
    deadline = time.time() + 10
    while time.time() < deadline:
        item = journey.client.get(f"{API}/qualifications/{qid}").json()
        if item["status"] != "running":
            break
        time.sleep(0.05)
    assert handle.killed
    assert item["status"] == "error" and item["code"] == "CREDENTIAL_REVOKED"
    # Nothing about the model: a key is needed again, then Test connection.
    assert item["diagnosis"]["category"] == "configuration"
    assert item["diagnosis"]["action"] == "TEST_CONNECTION"


# --- QG R1 remediation: M1, L1, L2, I2 --------------------------------------------------------


def test_a_held_back_key_refuses_the_handoff_never_a_server_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """QG M1: an HR key whose session cannot be checked never lets a run use the server key."""

    monkeypatch.setenv(key_sources.CREDENTIAL_VARIABLE, HR_KEY_2)
    _with_check([None])
    key_sources.HR_STORE.set(SecretStr(HR_KEY), "biz-ops", session=SecretStr("s"))
    with pytest.raises(ProfileConfigError) as refused:
        model_admin.qualification_handoff("openrouter")
    assert refused.value.code == "CREDENTIAL_SESSION_UNVERIFIED"


def test_a_held_back_key_refuses_the_qualification_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = _journey(tmp_path, monkeypatch)
    journey.client.cookies.set("clm_session", "hr2-session")
    assert journey.client.put(OPENROUTER_CREDENTIAL, json={"api_key": HR_KEY}).status_code == 200
    journey.client.cookies.set("clm_session", "hr-session")
    test = journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/connection-test")
    assert test.json()["outcome"] == "passed", test.text
    launched: list[str] = []
    journey.selector.launch = lambda qualification_id: launched.append(qualification_id)
    # The backend cannot answer for the session that entered the key: it is held back.
    real = journey.backend.handler

    def down(request: httpx.Request) -> httpx.Response:
        if "hr2-session" in request.headers.get("cookie", ""):
            raise httpx.ConnectError("down")
        return real(request)

    monkeypatch.setattr(journey.backend, "handler", down)
    assert key_sources.HR_STORE.current(max_age=0).held
    started = journey.start_qualification()
    assert started.status_code == 409, started.text
    assert started.json()["detail"]["code"] == "CREDENTIAL_SESSION_UNVERIFIED"
    assert launched == []


def test_the_launch_refuses_a_key_held_after_the_start_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QG M1: the start's check may be up to 10 s old; the launch checks again, refusing."""

    journey = _journey(tmp_path, monkeypatch)
    assert journey.client.put(OPENROUTER_CREDENTIAL, json={"api_key": HR_KEY}).status_code == 200
    test = journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/connection-test")
    assert test.json()["outcome"] == "passed", test.text

    def launch(qualification_id: str) -> Any:
        key_sources.install_session_check(lambda session, user_id: None)
        provider = journey.selector.handoff_providers.pop(qualification_id)
        return model_admin.qualification_handoff(provider)

    journey.selector.launch = launch
    started = journey.start_qualification()
    assert started.status_code == 409, started.text
    assert started.json()["detail"]["code"] == "CREDENTIAL_SESSION_UNVERIFIED"
    events = journey.client.get(f"{API}/audit").json()["events"]
    assert any(e["code"] == "CREDENTIAL_SESSION_UNVERIFIED" for e in events)


def test_only_the_qualified_providers_key_is_handed_over_and_watched() -> None:
    """QG L1: clearing another provider's key never ends a run."""

    _with_check([])
    key_sources.HR_STORE.set(SecretStr(HR_KEY), "biz-ops", session=SecretStr("s"))
    key_sources.ANTHROPIC_STORE.set(SecretStr(ANTHROPIC_KEY), "biz-ops", session=SecretStr("s"))
    payload, generations = model_admin.qualification_handoff("anthropic")
    assert json.loads(payload) == {"anthropic": ANTHROPIC_KEY} and set(generations) == {"anthropic"}
    key_sources.HR_STORE.clear()
    assert not model_admin.handoff_revoked(generations)
    assert model_admin.qualification_handoff(None) == (b"{}", {})


def test_a_key_limit_reading_holds_for_its_key_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QG L2: after an HR key ends, its OpenRouter limit is not shown for the server key."""

    from ai_assistant import remote_test

    journey = _journey(tmp_path, monkeypatch)
    assert journey.client.put(OPENROUTER_CREDENTIAL, json={"api_key": HR_KEY}).status_code == 200
    test = journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/connection-test")
    assert test.json()["outcome"] == "passed", test.text
    assert journey.client.get(f"{API}/budget").json()["provider"] is not None
    monkeypatch.setenv(key_sources.CREDENTIAL_VARIABLE, HR_KEY_2)
    key_sources.HR_STORE.clear()  # e.g. dropped with its session (no route: no forget call)
    assert remote_test.budget_status(journey.settings)["provider"] is None


def test_a_failed_handoff_write_ends_the_process(monkeypatch: pytest.MonkeyPatch) -> None:
    """QG I2: the process is killed and the launch fails if the key cannot be written."""

    import subprocess

    seen: dict[str, bool] = {}

    class Pipe:
        def write(self, data: bytes) -> None:
            raise BrokenPipeError

        def close(self) -> None:
            pass

    class Popen:
        def __init__(self, args: list[str], **kwargs: Any) -> None:
            self.stdin = Pipe()

        def kill(self) -> None:
            seen["killed"] = True

        def wait(self) -> int:
            seen["waited"] = True
            return 1

    monkeypatch.setattr(subprocess, "Popen", Popen)
    monkeypatch.setattr(model_admin, "profiles_path", lambda settings: Path("profiles.json"))
    monkeypatch.setattr(model_admin, "store_file", lambda settings: Path("state.sqlite3"))
    selector = object.__new__(model_admin.ModelSelector)
    selector.settings = type("S", (), {})()
    selector.handoffs, selector.handoff_providers = {}, {}
    with pytest.raises(OSError):
        model_admin.ModelSelector._launch_process(selector, "b" * 32)
    assert seen == {"killed": True, "waited": True} and selector.handoffs == {}
