"""Model management (D-093): IT's local profiles, HR-only administration, technical
qualification, atomic activation, rollback, restart behaviour and audit. Offline only: the
"model server" is an in-memory fake and the CLM backend is a fake."""

import copy
import json
import threading
import time
from collections.abc import AsyncGenerator, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import anyio
import httpx
import pytest
from fastapi.testclient import TestClient

from ai_assistant import model_admin, model_qualification
from ai_assistant.config import AiAssistantSettings
from ai_assistant.llm import ModelAnswer, ModelCallError, OpenAICompatibleChatModel, Piece
from ai_assistant.main import create_app
from ai_assistant.model_admin import ModelSelector
from ai_assistant.model_admin_store import Choice, ModelAdminStore
from ai_assistant.model_catalog import (
    BASELINE_ID,
    BoundedPromptModel,
    baseline_entry,
    load_catalogue,
)
from ai_assistant.model_qualification import (
    WatchedModel,
    connection_test,
    gates,
    verify_capacity,
)
from assistant_eval.qualification import QualificationJob, run_job

FIXTURES = Path(__file__).parent / "fixtures"
SUMMARY = json.loads((FIXTURES / "garden_address_conflict_summary.json").read_text())
DOCUMENTS = json.loads((FIXTURES / "garden_documents.json").read_text())
ME = json.loads((FIXTURES / "me_client_onboarder.json").read_text())
CASE_ID = SUMMARY["case"]["case_id"]
ORIGIN = "http://127.0.0.1:5173"
BASE_URL = "http://127.0.0.1:1234/v1"
SECRET = "sk-local-test-value-0123456789"
API = "/assistant/admin/models"

HR_CAPABILITIES = [
    "IDENTITY_ADMIN",
    "MODEL_CONFIG_MANAGE",
    "POLICY_MUTATE",
    "POLICY_VIEW",
    "PROVIDER_SANDBOX_TEST",
    "TEAM_ADMIN",
]
USERS = {
    "hr-session": ("hr-admin", "HR", None, HR_CAPABILITIES),
    "hr2-session": ("hr-second", "HR", None, HR_CAPABILITIES),
    "rm-session": ("ethan-tan", "RELATIONSHIP_MANAGER", "TEAM_A", ["CASE_ACCESS", "POLICY_VIEW"]),
    "co-session": ("maya-lim", "CLIENT_ONBOARDER", "TEAM_A", ["CASE_ACCESS", "POLICY_VIEW"]),
    "director-session": (
        "olivia-koh",
        "DIRECTOR",
        None,
        ["CASE_ACCESS", "CASE_GLOBAL", "POLICY_APPROVE", "POLICY_VIEW", "TARGET_RECOVERY"],
    ),
}


def _session(request: httpx.Request) -> str | None:
    for part in request.headers.get("cookie", "").split(";"):
        name, _, value = part.strip().partition("=")
        if name == "clm_session":
            return value
    return None


class Backend:
    """/api/auth/me for each synthetic user, plus one case for the chat checks."""

    def __init__(self) -> None:
        self.revoked: set[str] = set()

    def handler(self, request: httpx.Request) -> httpx.Response:
        session = _session(request)
        if session not in USERS or session in self.revoked:
            return httpx.Response(401, json={"detail": "auth"})
        user_id, role, team, capabilities = USERS[session]
        path = request.url.path
        if path == "/api/auth/me":
            me = copy.deepcopy(ME)
            me["profile"].update(
                user_id=user_id, role=role, team_id=team, capabilities=list(capabilities)
            )
            return httpx.Response(200, json=me)
        if path == f"/api/clm/zero-touch/cases/{CASE_ID}":
            return httpx.Response(200, json=SUMMARY)
        if path == f"/api/onboarding/cases/{CASE_ID}/documents":
            return httpx.Response(200, json=DOCUMENTS)
        return httpx.Response(404, json={"detail": "not found"})


class _Chunks(httpx.AsyncByteStream):
    """A streamed reply body (the adapter reads raw SSE bytes as they arrive)."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    async def __aiter__(self) -> AsyncGenerator[bytes, None]:
        yield self._body


class ModelServer:
    """An OpenAI-compatible local server. ``num_ctx`` truncates prompts as Ollama does;
    ``usage`` False leaves usage out; ``status`` makes every completion fail."""

    def __init__(
        self,
        model_id: str = "qwen3:8b",
        *,
        num_ctx: int | None = None,
        usage: bool = True,
        status: int = 200,
        reply: str = 'The current case offers "Keep registry value".',  # an allowed line
    ) -> None:
        self.model_id = model_id
        self.num_ctx = num_ctx
        self.usage = usage
        self.status = status
        self.reply = reply
        self.requests: list[httpx.Request] = []

    @staticmethod
    def tokens(messages: list[dict[str, str]]) -> int:
        return sum(len(m["content"].encode("utf-8")) // 4 + 4 for m in messages)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": self.model_id}]})
        if self.status != 200:
            return httpx.Response(self.status, json={"error": "nope"})
        body = json.loads(request.content)
        if body["stream"]:
            events = [
                {"choices": [{"delta": {"content": self.reply}, "finish_reason": None}]},
                {"choices": [{"delta": {}, "finish_reason": "stop"}]},
            ]
            text = "".join(f"data: {json.dumps(e)}\n\n" for e in events) + "data: [DONE]\n\n"
            return httpx.Response(
                200, stream=_Chunks(text.encode()), headers={"content-type": "text/event-stream"}
            )
        tokens = self.tokens(body["messages"])
        if self.num_ctx is not None:
            tokens = min(tokens, self.num_ctx)
        reply: dict[str, Any] = {
            "choices": [{"message": {"content": self.reply}, "finish_reason": "stop"}]
        }
        if self.usage:
            reply["usage"] = {"prompt_tokens": tokens, "completion_tokens": 1}
        return httpx.Response(200, json=reply)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)


def profile(**overrides: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "profile_id": "lmstudio_qwen3_8b",
        "display_name": "Qwen3 8B (LM Studio)",
        "deployment": "lm_studio",
        "base_url": BASE_URL,
        "model_id": "qwen3:8b",
        "model_version": "Q4_K_M",
        "context_window_tokens": 32768,
        "max_answer_tokens": 600,
        "temperature": 0.2,
        "timeout_seconds": 30.0,
        "streaming": True,
        "credential_env": "AI_ASSISTANT_MODEL_KEY_LM_STUDIO",
    }
    item.update(overrides)
    return item


def write_profiles(path: Path, *profiles: dict[str, Any]) -> Path:
    path.write_text(
        json.dumps({"schema": "clm-assistant-model-profiles/1", "profiles": list(profiles)}),
        encoding="utf-8",
    )
    return path


def settings(
    tmp_path: Path, profiles_file: Path | None = None, **extra: Any
) -> AiAssistantSettings:
    return AiAssistantSettings(
        clm_backend_url="http://127.0.0.1:8000",
        llm_enabled=True,
        llm_base_url="http://127.0.0.1:11434/v1",
        llm_model="ministral-3:8b",
        knowledge_enabled=False,
        llm_warm_up=False,
        model_profiles_file=str(profiles_file or ""),
        model_admin_db_path=str(tmp_path / "state" / "admin.sqlite3"),
        **extra,
    )


class Baseline:
    """The environment baseline as a fake model (it is never wrapped or rebuilt)."""

    name = "ministral-3:8b"

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        self.calls += 1
        return ModelAnswer('The current case offers "Keep registry value".')

    async def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Piece, None]:
        self.calls += 1
        yield Piece('The current case offers "Keep registry value".')
        yield Piece()

    def warm(self, messages: list[dict[str, str]]) -> None:
        return None


@pytest.fixture
def server() -> ModelServer:
    return ModelServer()


@pytest.fixture
def backend() -> Backend:
    return Backend()


# The job class the in-process launcher runs (tests swap in a fixed-rule harness model).
JOB: dict[str, type[QualificationJob]] = {"class": QualificationJob}


class ThreadRun:
    """A qualification run on a thread, shaped like the process the service supervises."""

    def __init__(self, target: Any) -> None:
        self.thread = threading.Thread(target=target, name="qualification-run", daemon=True)
        self.thread.start()

    def poll(self) -> int | None:
        return None if self.thread.is_alive() else 0

    def wait(self, timeout: float | None = None) -> None:
        self.thread.join(timeout)

    def kill(self) -> None:
        return None


def in_process(selector: ModelSelector) -> Any:
    """Run the harness side of a qualification in this process, with the fake model server."""

    def launch(qualification_id: str) -> ThreadRun:
        return ThreadRun(
            lambda: run_job(
                qualification_id,
                selector.settings,
                environ=selector.environ,
                transport=selector.transport,
                job_class=JOB["class"],
            )
        )

    return launch


def build_app(
    tmp_path: Path,
    backend: Backend,
    server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    *profiles: dict[str, Any],
) -> TestClient:
    path = write_profiles(tmp_path / "profiles.json", *(profiles or (profile(),)))
    config = settings(tmp_path, path)
    baseline = Baseline()
    monkeypatch.setattr("ai_assistant.main.build_chat_model", lambda *args, **kwargs: baseline)
    app = create_app(config, clm_transport=httpx.MockTransport(backend.handler))
    selector: ModelSelector = app.state.model_selector
    selector.environ = {"AI_ASSISTANT_MODEL_KEY_LM_STUDIO": SECRET}
    selector.transport = server.transport()
    selector.launch = in_process(selector)
    monkeypatch.setattr(model_admin, "SUPERVISE_SECONDS", 0.05)
    client = TestClient(app, headers={"Origin": ORIGIN})
    client.cookies.set("clm_session", "hr-session")
    return client


@pytest.fixture
def perfect_harness(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive qualification turns with the evaluator's gold-copying selector (a fixed rule,
    not a model) so the gates can pass; connection and capacity still use the fake server."""

    from assistant_eval import gold as gold_mod
    from assistant_eval.models import GoldSelector, SelectorModel
    from assistant_eval.snapshot import SnapshotSet

    snapshots = SnapshotSet.model_validate_json(
        (FIXTURES / "eval" / "snapshots.json").read_text(encoding="utf-8")
    )
    gold = gold_mod.self_test_gold(snapshots)
    choices = {
        key: [*turn.primary, *(x for x in turn.relevant if x not in turn.primary)]
        for key, turn in gold.turns.items()
    }

    class PerfectJob(QualificationJob):
        def harness_model(self, capture: Any, watched: WatchedModel) -> Any:
            watched.inner = SelectorModel(GoldSelector(choices), capture)
            return watched

    monkeypatch.setitem(JOB, "class", PerfectJob)


def wait_for(client: TestClient, qualification_id: str, timeout: float = 120) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        item = client.get(f"{API}/qualifications/{qualification_id}").json()
        if item["status"] != "running":
            # Let the service's supervisor record the outcome in the audit history.
            for thread in threading.enumerate():
                if thread.name == "model-qualification":
                    thread.join(10)
            return item
        time.sleep(0.2)
    raise AssertionError("qualification did not finish")


def qualify(client: TestClient, profile_id: str = "lmstudio_qwen3_8b") -> dict[str, Any]:
    started = client.post(f"{API}/{profile_id}/qualifications")
    assert started.status_code == 202, started.text
    return wait_for(client, started.json()["qualification_id"])


def ask(client: TestClient) -> dict[str, Any]:
    client.cookies.set("clm_session", "rm-session")
    try:
        reply = client.post(
            f"/assistant/cases/{CASE_ID}/chat", json={"message": "What should I do next?"}
        )
    finally:
        client.cookies.set("clm_session", "hr-session")
    assert reply.status_code == 200, reply.text
    return reply.json()


# --- the profiles file ---------------------------------------------------------------------


def test_a_valid_file_lists_baseline_file_profiles_and_the_pending_remote(tmp_path: Path) -> None:
    path = write_profiles(
        tmp_path / "p.json",
        profile(),
        profile(profile_id="remote_box", base_url="http://10.0.0.5:11434/v1"),
        profile(profile_id="no_stream", streaming=False),
        profile(profile_id="switched_off", enabled=False),
    )
    catalogue = load_catalogue(settings(tmp_path, path))
    status = {entry.profile_id: (entry.status, entry.reason) for entry in catalogue.entries}
    assert catalogue.file_status == "ok"
    assert status == {
        BASELINE_ID: ("selectable", None),
        "lmstudio_qwen3_8b": ("selectable", None),
        "remote_box": ("unavailable", "NOT_LOOPBACK"),
        "no_stream": ("unavailable", "STREAMING_REQUIRED"),
        "switched_off": ("disabled", "PROFILE_DISABLED"),
        "openrouter_gpt_oss_120b": ("pending_authorisation", "REMOTE_NOT_AUTHORISED"),
    }
    remote_box = catalogue.get("remote_box")
    assert remote_box is not None and remote_box.view()["endpoint"] is None
    shown = json.dumps([entry.view() for entry in catalogue.entries])
    assert "10.0.0.5" not in shown and "/v1" not in shown
    assert "AI_ASSISTANT_MODEL_KEY" not in shown


@pytest.mark.parametrize(
    ("bad", "field"),
    [
        ({"api_key": "sk-not-allowed"}, "profiles.0.api_key"),
        ({"credential_env": "OPENROUTER_API_KEY"}, "profiles.0.credential_env"),
        ({"credential_env": "AWS_SECRET_ACCESS_KEY"}, "profiles.0.credential_env"),
        ({"profile_id": BASELINE_ID}, "profiles"),
        ({"profile_id": "openrouter_gpt_oss_120b"}, "profiles"),
        ({"max_answer_tokens": 5000}, "profiles.0.max_answer_tokens"),
        ({"context_window_tokens": "32768"}, "profiles.0.context_window_tokens"),
        ({"profile_id": "Bad Id"}, "profiles.0.profile_id"),
    ],
)
def test_a_wrong_file_lists_no_file_profile_and_names_only_the_field(
    tmp_path: Path, bad: dict[str, Any], field: str
) -> None:
    path = write_profiles(tmp_path / "p.json", profile(**bad))
    catalogue = load_catalogue(settings(tmp_path, path))
    assert catalogue.file_status == "invalid"
    assert field in catalogue.file_errors
    assert [entry.source for entry in catalogue.entries] == ["environment", "code"]
    assert "sk-not-allowed" not in json.dumps(catalogue.file_errors)


def test_duplicate_ids_a_huge_file_and_a_missing_file_are_refused(tmp_path: Path) -> None:
    duplicate = write_profiles(tmp_path / "d.json", profile(), profile())
    assert load_catalogue(settings(tmp_path, duplicate)).file_status == "invalid"
    huge = tmp_path / "h.json"
    huge.write_text(" " * (70 * 1024), encoding="utf-8")
    assert load_catalogue(settings(tmp_path, huge)).file_errors == ("file_size",)
    assert load_catalogue(settings(tmp_path, tmp_path / "none.json")).file_status == "missing"


# --- permissions ---------------------------------------------------------------------------


@pytest.mark.parametrize("session", ["rm-session", "co-session", "director-session"])
def test_only_hr_may_use_any_management_endpoint_and_refusals_are_audited(
    tmp_path: Path,
    backend: Backend,
    server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    session: str,
) -> None:
    client = build_app(tmp_path, backend, server, monkeypatch)
    client.cookies.set("clm_session", session)
    calls = [
        client.get(API),
        client.get(f"{API}/audit"),
        client.post(f"{API}/lmstudio_qwen3_8b/connection-test"),
        client.post(f"{API}/lmstudio_qwen3_8b/qualifications"),
        client.post(f"{API}/lmstudio_qwen3_8b/activate", json={"expected_revision": 0}),
        client.post(f"{API}/rollback", json={"expected_revision": 0}),
    ]
    assert {reply.status_code for reply in calls} == {403}
    assert {reply.json()["detail"]["code"] for reply in calls} == {"MODEL_CONFIG_FORBIDDEN"}
    assert server.requests == []
    client.cookies.set("clm_session", "hr-session")
    events = client.get(f"{API}/audit").json()["events"]
    refused = [e for e in events if e["action"] == "ACCESS_REFUSED"]
    assert len(refused) == 6
    assert {e["actor"] for e in refused} == {USERS[session][0]}
    assert {e["role"] for e in refused} == {USERS[session][1]}


def test_no_session_is_401_and_a_foreign_origin_is_refused(
    tmp_path: Path, backend: Backend, server: ModelServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = build_app(tmp_path, backend, server, monkeypatch)
    client.cookies.clear()
    assert client.get(API).status_code == 401
    client.cookies.set("clm_session", "hr-session")
    assert client.get(API, headers={"Origin": "https://evil.example"}).status_code == 403


def test_hr_sees_the_overview_without_any_case_or_credential(
    tmp_path: Path, backend: Backend, server: ModelServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = build_app(tmp_path, backend, server, monkeypatch)
    reply = client.get(API)
    assert reply.status_code == 200
    body = reply.json()
    assert body["configured"] is True
    assert body["active"]["profile_id"] == BASELINE_ID
    assert body["quality"] == {"status": "NOT_SCORED", "reason": "OWNER_GOLD_NOT_LABELLED"}
    assert SECRET not in reply.text and "/v1" not in reply.text
    assert CASE_ID not in reply.text


# --- remote profiles -----------------------------------------------------------------------


def test_the_remote_profile_is_refused_for_every_action_before_any_network_call(
    tmp_path: Path, backend: Backend, server: ModelServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = build_app(tmp_path, backend, server, monkeypatch)
    remote = "openrouter_gpt_oss_120b"
    calls = [
        client.post(f"{API}/{remote}/connection-test"),
        client.post(f"{API}/{remote}/qualifications"),
        client.post(
            f"{API}/{remote}/activate",
            json={"expected_revision": 0, "acknowledge_quality_unscored": True},
        ),
    ]
    assert {reply.status_code for reply in calls} == {409}
    assert {reply.json()["detail"]["code"] for reply in calls} == {"REMOTE_NOT_AUTHORISED"}
    assert server.requests == []


# --- connection test -----------------------------------------------------------------------


def test_the_connection_test_uses_synthetic_text_and_the_server_side_key(
    tmp_path: Path, backend: Backend, server: ModelServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = build_app(tmp_path, backend, server, monkeypatch)
    reply = client.post(f"{API}/lmstudio_qwen3_8b/connection-test")
    assert reply.status_code == 200
    assert reply.json()["outcome"] == "passed" and reply.json()["listed"] is True
    assert SECRET not in reply.text
    assert {r.headers["authorization"] for r in server.requests} == {f"Bearer {SECRET}"}
    sent = b"".join(r.content for r in server.requests)
    assert b"connection test with no case data" in sent
    assert SUMMARY["case"]["case_id"].encode() not in sent


def test_a_missing_key_or_a_proxy_refuses_before_any_request(
    tmp_path: Path, backend: Backend, server: ModelServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = build_app(tmp_path, backend, server, monkeypatch)
    selector: ModelSelector = client.app.state.model_selector  # type: ignore[attr-defined]
    selector.environ = {}
    reply = client.post(f"{API}/lmstudio_qwen3_8b/connection-test")
    assert reply.status_code == 409 and reply.json()["detail"]["code"] == "CREDENTIAL_MISSING"
    selector.environ = {"AI_ASSISTANT_MODEL_KEY_LM_STUDIO": SECRET, "HTTPS_PROXY": "http://p:1"}
    reply = client.post(f"{API}/lmstudio_qwen3_8b/connection-test")
    assert reply.status_code == 409 and reply.json()["detail"]["code"] == "PROXY_CONFIGURED"
    assert server.requests == []


def test_connection_failures_are_closed_codes() -> None:
    def adapter(srv: ModelServer) -> OpenAICompatibleChatModel:
        return OpenAICompatibleChatModel(
            base_url=BASE_URL,
            model="qwen3:8b",
            credential="x",
            timeout_seconds=5,
            temperature=0.2,
            transport=srv.transport(),
        )

    assert anyio.run(connection_test, adapter(ModelServer(status=500)), "qwen3:8b")["code"] == (
        "HTTP_500"
    )
    assert anyio.run(connection_test, adapter(ModelServer("other")), "qwen3:8b")["code"] == (
        "MODEL_NOT_LISTED"
    )


# --- capacity ------------------------------------------------------------------------------


def _adapter(srv: ModelServer) -> OpenAICompatibleChatModel:
    return OpenAICompatibleChatModel(
        base_url=BASE_URL,
        model="qwen3:8b",
        credential="x",
        timeout_seconds=5,
        temperature=0.2,
        transport=srv.transport(),
    )


LARGEST = [{"role": "system", "content": "rules " * 900}, {"role": "user", "content": "q?"}]


def test_capacity_is_verified_from_server_counts_and_bounds_the_prompt() -> None:
    result = verify_capacity(
        _adapter(ModelServer()),
        declared_tokens=16384,
        max_answer_tokens=600,
        largest_prompt=LARGEST,
    )
    assert result["status"] == "verified", result
    assert 16384 * 0.9 < result["probed_tokens"] <= 16384
    assert 0 < result["prompt_limit"] < result["probed_tokens"] - 600


def test_a_server_that_truncates_below_the_declared_window_is_caught() -> None:
    # IT declared 16k; the server really holds 4k (Ollama's default) and truncates silently.
    result = verify_capacity(
        _adapter(ModelServer(num_ctx=4096)),
        declared_tokens=16384,
        max_answer_tokens=600,
        largest_prompt=LARGEST,
    )
    assert result["status"] == "unverified" and result["code"] == "TRUNCATION_DETECTED"
    assert result["prompt_limit"] is None


def test_capacity_without_usage_or_with_a_rejecting_server_is_not_verified() -> None:
    no_usage = verify_capacity(
        _adapter(ModelServer(usage=False)),
        declared_tokens=8192,
        max_answer_tokens=600,
        largest_prompt=LARGEST,
    )
    assert no_usage["code"] == "USAGE_NOT_REPORTED"
    rejected = verify_capacity(
        _adapter(ModelServer(status=400)),
        declared_tokens=8192,
        max_answer_tokens=600,
        largest_prompt=LARGEST,
    )
    assert rejected["status"] == "failed" and rejected["code"] == "CAPACITY_HTTP_400"


def test_a_tokenizer_that_makes_more_tokens_than_bytes_is_not_trusted() -> None:
    class Dense(ModelServer):
        @staticmethod
        def tokens(messages: list[dict[str, str]]) -> int:
            return sum(len(m["content"].encode()) * 2 for m in messages)

    result = verify_capacity(
        _adapter(Dense()), declared_tokens=16384, max_answer_tokens=600, largest_prompt=LARGEST
    )
    assert result["code"] == "TOKENIZER_BOUND_NOT_CONFIRMED"


def test_an_activated_model_refuses_a_prompt_beyond_its_verified_bound() -> None:
    model = BoundedPromptModel(_adapter(ModelServer()), prompt_limit=100)
    with pytest.raises(ModelCallError) as caught:
        model.complete([{"role": "user", "content": "x" * 200}])
    assert caught.value.error_class == "prompt_too_large"


# --- gates ---------------------------------------------------------------------------------


class _Turn:
    def __init__(self, reason: str = "none", kept: int = 1, left_out: int = 0) -> None:
        self.metrics = {"kept_lines": kept, "left_out_lines": left_out}
        self.fallback_reason = reason


def _gates(turns: list[_Turn], **overall: Any) -> dict[str, dict[str, Any]]:
    reasons: dict[str, int] = {}
    for turn in turns:
        reasons[turn.fallback_reason] = reasons.get(turn.fallback_reason, 0) + 1
    result = gates(
        connection={"outcome": "passed"},
        completed=True,
        turns=turns,
        expected_turns=len(turns),
        overall={
            "fallback_reasons": reasons,
            "unsafe_display": 0,
            "cut_short_rate": 0.0,
            **overall,
        },
        capacity={"status": "verified", "prompt_limit": 1000},
        largest_bound=900,
    )
    return {item["gate"]: item for item in result}


def test_a_model_that_writes_no_line_never_passes_line_validity() -> None:
    result = _gates([_Turn("policy_no_allowed_line", kept=0, left_out=0)] * 20)
    assert result["G-6"]["passed"] is False and result["G-6"]["value"] is None


def test_no_allowed_line_selected_is_reported_but_not_gated() -> None:
    turns = [_Turn("policy_no_allowed_line", kept=0, left_out=1)] * 5 + [_Turn()] * 15
    result = _gates(turns)
    assert result["G-5"]["gating"] is False and result["G-5"]["value"] == 0.25


def test_the_approved_thresholds() -> None:
    unavailable = [_Turn("model_unavailable", kept=0)] * 2 + [_Turn()] * 18
    assert _gates(unavailable)["G-4"]["passed"] is False  # 10% > 5%
    assert _gates([_Turn("model_unavailable", kept=0)] + [_Turn()] * 19)["G-4"]["passed"]
    assert _gates([_Turn(kept=7, left_out=3)])["G-6"]["passed"]  # exactly 0.70
    assert not _gates([_Turn(kept=6, left_out=4)])["G-6"]["passed"]
    assert not _gates([_Turn()], unsafe_display=1)["G-3"]["passed"]
    assert not _gates([_Turn()], cut_short_rate=0.2)["G-7"]["passed"]


# --- qualification, activation, rollback ----------------------------------------------------


def test_full_flow_qualify_acknowledge_activate_answer_and_roll_back(
    tmp_path: Path,
    backend: Backend,
    server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    perfect_harness: None,
) -> None:
    client = build_app(tmp_path, backend, server, monkeypatch)
    assert ask(client)["model"] == "ministral-3:8b"

    item = qualify(client)
    assert item["status"] == "passed", item
    assert item["quality"]["status"] == "NOT_SCORED"
    gating = {gate["gate"]: gate["passed"] for gate in item["gates"] if gate["gating"]}
    assert gating == dict.fromkeys(["G-1", "G-2", "G-3", "G-4", "G-6", "G-7"], True)
    assert item["capacity"]["status"] == "verified"
    assert item["lines"]["model_selected_lines"] > 0
    assert set(item["reproducibility"]) >= {"harness_version", "basis", "turns", "model_id"}

    overview = client.get(API).json()
    assert overview["profiles"][1]["activation_blockers"] == []
    revision = overview["revision"]
    refused = client.post(f"{API}/lmstudio_qwen3_8b/activate", json={"expected_revision": revision})
    assert refused.json()["detail"]["code"] == "ACKNOWLEDGEMENT_REQUIRED"
    stale = client.post(
        f"{API}/lmstudio_qwen3_8b/activate",
        json={"expected_revision": revision + 5, "acknowledge_quality_unscored": True},
    )
    assert stale.status_code == 409 and stale.json()["detail"]["code"] == "REVISION_CONFLICT"
    applied = client.post(
        f"{API}/lmstudio_qwen3_8b/activate",
        json={"expected_revision": revision, "acknowledge_quality_unscored": True},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["active"]["profile_id"] == "lmstudio_qwen3_8b"
    assert applied.json()["last_good"]["profile_id"] == BASELINE_ID
    assert ask(client)["model"] == "qwen3:8b"

    back = client.post(f"{API}/rollback", json={"expected_revision": applied.json()["revision"]})
    assert back.status_code == 200
    assert back.json()["active"]["profile_id"] == BASELINE_ID
    assert ask(client)["model"] == "ministral-3:8b"

    events = client.get(f"{API}/audit").json()["events"]
    actions = [(e["action"], e["outcome"]) for e in reversed(events)]
    assert ("QUALIFICATION_STARTED", "started") in actions
    assert ("QUALIFICATION_FINISHED", "passed") in actions
    assert ("ACTIVATED", "refused") in actions and ("ACTIVATED", "applied") in actions
    assert ("ROLLED_BACK", "applied") in actions
    acknowledged = [e for e in events if e["action"] == "ACTIVATED" and e["outcome"] == "applied"]
    assert acknowledged[0]["code"] == "QUALITY_NOT_SCORED_ACKNOWLEDGED"
    stored = (tmp_path / "state" / "admin.sqlite3").read_bytes()
    assert SECRET.encode() not in stored and b"127.0.0.1:1234" not in stored


def test_an_unqualified_or_out_of_date_model_cannot_be_activated(
    tmp_path: Path,
    backend: Backend,
    server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    perfect_harness: None,
) -> None:
    client = build_app(tmp_path, backend, server, monkeypatch)
    body = {"expected_revision": 0, "acknowledge_quality_unscored": True}
    reply = client.post(f"{API}/lmstudio_qwen3_8b/activate", json=body)
    assert reply.json()["detail"]["code"] == "NOT_QUALIFIED"
    assert qualify(client)["status"] == "passed"
    # Code the answers depend on changed (for example a prompt edit): qualify again.
    monkeypatch.setattr(model_admin, "qualification_basis", lambda: "0" * 64)
    reply = client.post(f"{API}/lmstudio_qwen3_8b/activate", json=body)
    assert reply.json()["detail"]["code"] == "NOT_QUALIFIED"


def test_a_failing_qualification_blocks_activation(
    tmp_path: Path, backend: Backend, monkeypatch: pytest.MonkeyPatch, perfect_harness: None
) -> None:
    client = build_app(tmp_path, backend, ModelServer(num_ctx=4096), monkeypatch)
    item = qualify(client)
    assert item["status"] == "failed" and "G-7" in item["code"]
    reply = client.post(
        f"{API}/lmstudio_qwen3_8b/activate",
        json={"expected_revision": 0, "acknowledge_quality_unscored": True},
    )
    assert reply.json()["detail"]["code"] == "NOT_QUALIFIED"


def test_one_qualification_at_a_time_and_cancel(
    tmp_path: Path, backend: Backend, server: ModelServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = threading.Event()

    class SlowJob(QualificationJob):
        def harness_model(self, capture: Any, watched: WatchedModel) -> Any:
            release.wait(30)
            return watched

    monkeypatch.setitem(JOB, "class", SlowJob)
    client = build_app(tmp_path, backend, server, monkeypatch)
    first = client.post(f"{API}/lmstudio_qwen3_8b/qualifications")
    assert first.status_code == 202
    second = client.post(f"{API}/lmstudio_qwen3_8b/qualifications")
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "QUALIFICATION_BUSY"
    qualification_id = first.json()["qualification_id"]
    assert client.post(f"{API}/qualifications/{qualification_id}/cancel").status_code == 200
    release.set()
    item = wait_for(client, qualification_id)
    assert item["status"] == "cancelled" and item["code"] == "CANCELLED"
    assert client.get(f"{API}/qualifications/{'f' * 32}").status_code == 404
    assert client.get(f"{API}/qualifications/not-an-id").status_code == 404


def test_a_qualification_past_its_time_limit_stops(tmp_path: Path, server: ModelServer) -> None:
    store = ModelAdminStore(tmp_path / "jobs.sqlite3")
    qualification_id = store.begin_qualification("p", "f", "b", "hr-admin", 84)
    job = QualificationJob(
        store=store,
        qualification_id=qualification_id,
        profile_id="p",
        model=_adapter(server),
        model_id="qwen3:8b",
        declared_tokens=8192,
        max_answer_tokens=600,
        basis="b",
        started_by="hr-admin",
        deadline=time.monotonic() - 1,
    )
    job.run()
    item = store.qualification(qualification_id)
    assert item is not None and (item["status"], item["code"]) == ("error", "DEADLINE")


# --- atomic switching and restarts ---------------------------------------------------------


def _activate_directly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    """Pretend a passing qualification exists and activate through the API."""

    selector: ModelSelector = client.app.state.model_selector  # type: ignore[attr-defined]
    store = selector.store
    assert store is not None
    entry = load_catalogue(selector.settings).get("lmstudio_qwen3_8b")
    assert entry is not None
    qualification_id = store.begin_qualification(
        entry.profile_id, entry.fingerprint, model_qualification.qualification_basis(), "hr", 84
    )
    store.finish_qualification(
        qualification_id, "passed", None, {"capacity": {"prompt_limit": 60000}}
    )
    reply = client.post(
        f"{API}/lmstudio_qwen3_8b/activate",
        json={"expected_revision": store.revision(), "acknowledge_quality_unscored": True},
    )
    assert reply.status_code == 200, reply.text


def test_an_answer_keeps_the_model_it_started_with(
    tmp_path: Path, backend: Backend, server: ModelServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = build_app(tmp_path, backend, server, monkeypatch)
    selector: ModelSelector = client.app.state.model_selector  # type: ignore[attr-defined]
    before = selector.current()
    _activate_directly(tmp_path, monkeypatch, client)
    after = selector.current()
    assert before.model is not None and before.model.name == "ministral-3:8b"
    assert after.model is not None and after.model.name == "qwen3:8b"
    assert before.revision < after.revision and before.profile_id == BASELINE_ID


def test_a_restart_restores_the_activation_and_reverts_when_the_file_changed(
    tmp_path: Path, backend: Backend, server: ModelServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = build_app(tmp_path, backend, server, monkeypatch)
    _activate_directly(tmp_path, monkeypatch, client)
    selector: ModelSelector = client.app.state.model_selector  # type: ignore[attr-defined]
    store = selector.store
    assert store is not None
    environ = {"AI_ASSISTANT_MODEL_KEY_LM_STUDIO": SECRET}

    restarted = ModelSelector(selector.settings, Baseline(), store, environ=environ)
    assert restarted.current().profile_id == "lmstudio_qwen3_8b"

    write_profiles(tmp_path / "profiles.json", profile(temperature=0.7))
    reverted = ModelSelector(selector.settings, Baseline(), store, environ=environ)
    active = reverted.current()
    assert (active.profile_id, active.reverted) == (BASELINE_ID, "PROFILE_CHANGED")
    events = store.events(5)
    assert (events[0]["action"], events[0]["code"]) == ("STARTUP_REVERTED", "PROFILE_CHANGED")
    assert events[0]["actor"] == "system"


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ("missing_key", "CREDENTIAL_MISSING"),
        ("basis", "QUALIFICATION_OUT_OF_DATE"),
        ("removed", "PROFILE_MISSING"),
        ("disabled", "MODEL_DISABLED_BY_ENVIRONMENT"),
    ],
)
def test_a_restart_falls_back_to_the_baseline_with_an_audited_reason(
    tmp_path: Path,
    backend: Backend,
    server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
    code: str,
) -> None:
    client = build_app(tmp_path, backend, server, monkeypatch)
    _activate_directly(tmp_path, monkeypatch, client)
    selector: ModelSelector = client.app.state.model_selector  # type: ignore[attr-defined]
    store = selector.store
    assert store is not None
    environ: dict[str, str] = {"AI_ASSISTANT_MODEL_KEY_LM_STUDIO": SECRET}
    config = selector.settings
    if change == "missing_key":
        environ = {}
    elif change == "basis":
        monkeypatch.setattr(model_admin, "qualification_basis", lambda: "1" * 64)
    elif change == "removed":
        write_profiles(tmp_path / "profiles.json", profile(profile_id="another_model"))
    else:
        config = config.model_copy(update={"llm_enabled": False})
    restarted = ModelSelector(config, None, store, environ=environ)
    assert (restarted.current().profile_id, restarted.current().reverted) == (BASELINE_ID, code)


def test_two_processes_see_the_same_activation(
    tmp_path: Path, backend: Backend, server: ModelServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = build_app(tmp_path, backend, server, monkeypatch)
    selector: ModelSelector = client.app.state.model_selector  # type: ignore[attr-defined]
    assert selector.store is not None
    other = ModelSelector(
        selector.settings,
        Baseline(),
        ModelAdminStore(tmp_path / "state" / "admin.sqlite3"),
        environ={"AI_ASSISTANT_MODEL_KEY_LM_STUDIO": SECRET},
    )
    assert other.current().profile_id == BASELINE_ID
    _activate_directly(tmp_path, monkeypatch, client)
    assert other.current().profile_id == "lmstudio_qwen3_8b"


def test_concurrent_activations_from_one_view_apply_once(tmp_path: Path) -> None:
    store = ModelAdminStore(tmp_path / "cas.sqlite3")
    baseline = Choice(BASELINE_ID, "b")
    results: list[str] = []

    def attempt(name: str) -> None:
        try:
            store.activate(0, Choice(name, "f"), baseline, name)
            results.append("applied")
        except Exception as exc:
            results.append(type(exc).__name__)

    threads = [threading.Thread(target=attempt, args=(f"p{i}",)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == ["RevisionConflict"] * 7 + ["applied"]
    assert store.revision() == 1


def test_the_audit_keeps_only_the_newest_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("ai_assistant.model_admin_store.MAX_EVENTS", 5)
    store = ModelAdminStore(tmp_path / "a.sqlite3")
    for index in range(12):
        store.record(actor="hr-admin", role="HR", action="CONNECTION_TEST", outcome=str(index))
    assert [event["outcome"] for event in store.events(100)] == ["11", "10", "9", "8", "7"]


# --- unchanged behaviour -------------------------------------------------------------------


def test_without_a_profiles_file_nothing_is_managed_and_the_baseline_answers(
    tmp_path: Path, backend: Backend, monkeypatch: pytest.MonkeyPatch
) -> None:
    baseline = Baseline()
    monkeypatch.setattr("ai_assistant.main.build_chat_model", lambda *a, **k: baseline)
    app = create_app(settings(tmp_path), clm_transport=httpx.MockTransport(backend.handler))
    client = TestClient(app, headers={"Origin": ORIGIN})
    client.cookies.set("clm_session", "hr-session")
    body = client.get(API).json()
    assert body["configured"] is False and body["file_status"] == "not_configured"
    reply = client.post(f"{API}/{BASELINE_ID}/connection-test")
    assert reply.json()["detail"]["code"] == "MODEL_MANAGEMENT_OFF"
    assert not (tmp_path / "state").exists()
    assert ask(client)["model"] == "ministral-3:8b"


def test_an_injected_model_has_no_management_routes(tmp_path: Path, backend: Backend) -> None:
    app = create_app(
        settings(tmp_path),
        clm_transport=httpx.MockTransport(backend.handler),
        chat_model=Baseline(),
    )
    assert not [route for route in app.routes if API in getattr(route, "path", "")]


def test_the_baseline_entry_never_shows_a_non_loopback_host(tmp_path: Path) -> None:
    config = settings(tmp_path).model_copy(update={"llm_base_url": "http://gpu.internal:8000/v1"})
    assert baseline_entry(config).view()["endpoint"] is None


@pytest.fixture(autouse=True)
def _no_threads_left() -> Iterator[None]:
    yield
    for thread in threading.enumerate():
        if thread.name in {"model-qualification", "qualification-run"}:
            thread.join(30)


# --- the real qualification process ----------------------------------------------------------


class _LoopbackModel(BaseHTTPRequestHandler):
    """A real OpenAI-compatible HTTP server on 127.0.0.1 for the process test."""

    protocol_version = "HTTP/1.0"
    reply = 'The current case offers "Keep registry value".'

    def log_message(self, *args: Any) -> None:
        return None

    def _send(self, body: bytes, kind: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (http.server naming)
        self._send(json.dumps({"data": [{"id": "qwen3:8b"}]}).encode(), "application/json")

    def do_POST(self) -> None:  # noqa: N802 (http.server naming)
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if body["stream"]:
            events = [
                {"choices": [{"delta": {"content": self.reply}, "finish_reason": None}]},
                {"choices": [{"delta": {}, "finish_reason": "stop"}]},
            ]
            text = "".join(f"data: {json.dumps(e)}\n\n" for e in events) + "data: [DONE]\n\n"
            self._send(text.encode(), "text/event-stream")
            return
        tokens = ModelServer.tokens(body["messages"])
        self._send(
            json.dumps(
                {
                    "choices": [{"message": {"content": self.reply}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": tokens, "completion_tokens": 1},
                }
            ).encode(),
            "application/json",
        )


def test_the_service_runs_qualification_in_its_own_process(
    tmp_path: Path, backend: Backend, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real path: the service starts scripts/qualify_model.py, which runs the harness
    against a real loopback HTTP model; the service never imports the harness itself."""

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _LoopbackModel)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        port = httpd.server_address[1]
        path = write_profiles(
            tmp_path / "profiles.json",
            profile(base_url=f"http://127.0.0.1:{port}/v1", credential_env=None),
        )
        monkeypatch.setattr("ai_assistant.main.build_chat_model", lambda *a, **k: Baseline())
        monkeypatch.setattr(model_admin, "SUPERVISE_SECONDS", 0.2)
        app = create_app(
            settings(tmp_path, path), clm_transport=httpx.MockTransport(backend.handler)
        )
        selector: ModelSelector = app.state.model_selector
        selector.environ = {}
        client = TestClient(app, headers={"Origin": ORIGIN})
        client.cookies.set("clm_session", "hr-session")
        started = client.post(f"{API}/lmstudio_qwen3_8b/qualifications")
        assert started.status_code == 202, started.text
        item = wait_for(client, started.json()["qualification_id"], timeout=300)
        assert item["status"] in {"passed", "failed"}, item
        assert item["total_turns"] == 84 and item["done_turns"] == 84
        assert item["connection"]["outcome"] == "passed"
        assert item["capacity"]["status"] == "verified"
        assert {gate["gate"] for gate in item["gates"]} == {f"G-{n}" for n in range(1, 8)}
        assert next(g for g in item["gates"] if g["gate"] == "G-3")["passed"] is True
        events = client.get(f"{API}/audit").json()["events"]
        assert events[0]["action"] == "QUALIFICATION_FINISHED"
    finally:
        httpd.shutdown()


def test_the_documented_example_file_is_valid(tmp_path: Path) -> None:
    example = Path(__file__).resolve().parents[1] / "model_profiles.example.json"
    catalogue = load_catalogue(settings(tmp_path, example))
    assert catalogue.file_status == "ok", catalogue.file_errors
    assert {entry.status for entry in catalogue.entries if entry.source == "file"} == {"selectable"}
