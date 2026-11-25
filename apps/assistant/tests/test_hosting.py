"""Stage A hosted service: the real create_app behind the hosted guard, with no model and no
paid inference. The CLM backend is a mock transport that enforces per-user case access, as the
real backend does, so isolation is checked through the assistant and not assumed."""

import errno
import json
import os
import re
import sqlite3
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from ai_assistant import remote_test
from ai_assistant.config import AiAssistantSettings
from ai_assistant.knowledge.embeddings import EmbeddingUnavailableError
from ai_assistant.knowledge.ingest import ingest_guidance
from ai_assistant.knowledge.service import KnowledgeBase
from ai_assistant.knowledge.store import KnowledgeStore
from ai_assistant.knowledge.vector_index import VectorIndex
from ai_assistant.llm import LlmUnavailableError, ModelAnswer
from ai_assistant.main import create_app
from ai_assistant.model_catalog import load_catalogue
from ai_assistant.model_qualification import ASSISTANT_DIR
from assistant_hosting import backup, probe, profile, run
from assistant_hosting.guard import ADMIN_CHANGES, ADMIN_PREFIX
from assistant_hosting.harden import harden
from assistant_hosting.profile import NO_MODEL_NAME, NO_MODEL_URL, refusals
from assistant_hosting.readiness import Readiness

ORIGIN = "https://clm.example.test"
BACKEND = "http://clm-backend-proxy:8000"
FIXTURES = Path(__file__).parent / "fixtures"
SUMMARY = json.loads((FIXTURES / "garden_address_conflict_summary.json").read_text())
DOCUMENTS = json.loads((FIXTURES / "garden_documents.json").read_text())
CASE_ID = UUID(SUMMARY["case"]["case_id"])
PROFILES = ASSISTANT_DIR / "deploy" / "model_profiles.hosted.json"
CADDYFILE = ASSISTANT_DIR / "deploy" / "Caddyfile.candidate"
SHARED_CADDYFILE = ASSISTANT_DIR.parent.parent / "deploy" / "Caddyfile"
COMPOSE = ASSISTANT_DIR / "deploy" / "compose.assistant.yml"
# D-139: the hosted service needs no case list (the D-132 variables are retired, and refused
# when set), so the valid hosted environment adds nothing here.
ELIGIBLE: dict[str, str] = {}


def actor(user: str, role: str, team: str, *capabilities: str) -> dict[str, Any]:
    return {
        "profile": {
            "user_id": user,
            "display_name": user,
            "role": role,
            "team_id": team,
            "capabilities": list(capabilities),
        }
    }


SESSIONS = {
    "rm-a": actor("maya-lim", "RM", "team-a", "CASE_ACCESS"),
    "rm-b": actor("ryan-lee", "RM", "team-b", "CASE_ACCESS"),
    "hr": actor("biz-ops", "HR", "team-hr", "MODEL_CONFIG_MANAGE"),
}


class Clm:
    """The backend's rule: no session is 401, a case outside the team is a safe 404."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.healthy = True

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        assert request.method == "GET", "the assistant must stay read-only toward the backend"
        if path == "/health":
            return httpx.Response(200 if self.healthy else 503, json={"status": "ok"})
        token = request.headers.get("cookie", "").removeprefix("clm_session=")
        person = SESSIONS.get(token)
        if person is None:
            return httpx.Response(401, json={"detail": "no session"})
        if path == "/api/auth/me":
            return httpx.Response(200, json=person)
        if person["profile"]["team_id"] != "team-a":
            return httpx.Response(404, json={"detail": "not found"})
        if path == f"/api/clm/zero-touch/cases/{CASE_ID}":
            return httpx.Response(200, json=SUMMARY)
        if path == f"/api/onboarding/cases/{CASE_ID}/documents":
            return httpx.Response(200, json=DOCUMENTS)
        if path == f"/api/onboarding/cases/{CASE_ID}/document-digests":
            # D-139: the backend's digests of the synthetic fixture documents, so the hosted
            # external-inference check can verify this case as synthetic (as the harness does).
            from assistant_eval.runner import _digests

            return httpx.Response(200, json=_digests(DOCUMENTS))
        return httpx.Response(404, json={"detail": "not found"})


class ScriptedModel:
    """A mock provider: it never leaves the process and returns one fixed reply."""

    name = "mock-provider"
    supports_stream = False

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls = 0

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        self.calls += 1
        return ModelAnswer(text=self.reply)

    def stream(self, messages: list[dict[str, str]]) -> Any:
        raise LlmUnavailableError("the mock has no stream")


def hosted_settings(root: Path, **overrides: Any) -> AiAssistantSettings:
    values: dict[str, Any] = {
        "data_dir": str(root),
        "clm_backend_url": BACKEND,
        "allowed_origins": [ORIGIN],
        "llm_enabled": True,
        "llm_base_url": NO_MODEL_URL,
        "llm_model": NO_MODEL_NAME,
        "llm_timeout_seconds": 2,
        "llm_warm_up": False,
        "model_profiles_file": str(PROFILES),
        "budget_ledger_path": "budget/sessions/openrouter.sqlite3",
        "anthropic_ledger_path": "budget/sessions/anthropic.sqlite3",
        "model_admin_db_path": "models/model_admin.sqlite3",
        "knowledge_data_dir": "knowledge",
    }
    values.update(overrides)
    return AiAssistantSettings(_env_file=None, **values)  # type: ignore[call-arg]


def no_files() -> tuple[Path, ...]:
    return ()


class NoEmbedder:
    """What the hosted service has: nothing listens on the loopback embedding port. Refused at
    once here, as on Linux (Windows spends two seconds per refused loopback connection)."""

    name = "nomic-embed-text"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingUnavailableError("nothing is listening")

    def embed_query(self, text: str) -> list[float]:
        raise EmbeddingUnavailableError("nothing is listening")


def knowledge(settings: AiAssistantSettings) -> KnowledgeBase:
    folder = Path(settings.knowledge_data_dir)
    return KnowledgeBase(
        store=KnowledgeStore(folder / "knowledge.sqlite3"),
        index=VectorIndex(folder / "chroma"),
        embedder=NoEmbedder(),
    )


def service(root: Path, clm: Clm, **overrides: Any) -> TestClient:
    settings = hosted_settings(root, **overrides)
    assert refusals(settings, ELIGIBLE, env_files=no_files()) == []
    kb = knowledge(settings)
    ingest_guidance(kb)
    transport = httpx.MockTransport(clm.handler)
    app = create_app(settings, clm_transport=transport, knowledge=kb)
    harden(app, settings, environ=ELIGIBLE, transport=transport)
    return TestClient(
        app, base_url="http://clm-assistant-proxy:8100", raise_server_exceptions=False
    )


@pytest.fixture
def clm() -> Clm:
    return Clm()


@pytest.fixture
def client(tmp_path: Path, clm: Clm) -> Iterator[TestClient]:
    with service(tmp_path, clm) as test_client:
        yield test_client


def session(token: str, **headers: str) -> dict[str, str]:
    return {"cookie": f"clm_session={token}", **headers}


def post_headers(token: str) -> dict[str, str]:
    return session(token, origin=ORIGIN)


# --- configuration ---------------------------------------------------------------------------


def test_the_compose_environment_is_a_valid_stage_a_configuration(tmp_path: Path) -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    assert f"AI_ASSISTANT_LLM_BASE_URL: {NO_MODEL_URL}" in text
    assert f"AI_ASSISTANT_LLM_MODEL: {NO_MODEL_NAME}" in text
    assert f"AI_ASSISTANT_CLM_BACKEND_URL: {BACKEND}" in text
    assert refusals(hosted_settings(tmp_path), ELIGIBLE, env_files=no_files()) == []


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"data_dir": ""}, "DATA_ROOT_REQUIRED"),
        ({"llm_enabled": False}, "NO_MODEL_BASELINE_REQUIRED"),
        ({"llm_model": "qwen3:8b"}, "NO_MODEL_BASELINE_REQUIRED"),
        ({"llm_base_url": "https://openrouter.ai/api/v1"}, "NO_MODEL_URL_REQUIRED"),
        ({"llm_base_url": "http://127.0.0.1:11434/v1"}, "NO_MODEL_URL_REQUIRED"),
        ({"llm_profile": "openrouter_gpt_oss_120b"}, "REMOTE_PROFILE_REFUSED"),
        ({"llm_warm_up": True}, "WARM_UP_REFUSED"),
        ({"embed_base_url": "http://ollama:11434"}, "EMBEDDINGS_MUST_BE_LOOPBACK"),
        ({"clm_backend_url": "http://127.0.0.1:8000"}, "CLM_BACKEND_LOOPBACK_REFUSED"),
        ({"clm_backend_url": "http://localhost:8000"}, "CLM_BACKEND_LOOPBACK_REFUSED"),
        ({"clm_backend_url": "https://clm.example.test"}, "CLM_BACKEND_URL_INVALID"),
        ({"allowed_origins": []}, "HTTPS_ORIGIN_REQUIRED"),
        ({"allowed_origins": ["http://127.0.0.1:5173"]}, "HTTPS_ORIGIN_REQUIRED"),
        ({"allowed_origins": ["https://clm.example.test/app"]}, "HTTPS_ORIGIN_REQUIRED"),
        ({"remote_inference_decision": "D-091"}, "REMOTE_SETTING_REFUSED"),
        ({"remote_live_decision": "D-092"}, "REMOTE_SETTING_REFUSED"),
        ({"local_api_test_decision": "D-094"}, "REMOTE_SETTING_REFUSED"),
        ({"synthetic_dev_decision": "D-095"}, "REMOTE_SETTING_REFUSED"),
        ({"anthropic_decision": "D-099"}, "REMOTE_SETTING_REFUSED"),
        ({"anthropic_workspace_id": "wrkspc_1"}, "REMOTE_SETTING_REFUSED"),
        ({"anthropic_workspace_limit_micro_usd": 1}, "REMOTE_SETTING_REFUSED"),
        ({"remote_low_reasoning_profile_enabled": True}, "REMOTE_SETTING_REFUSED"),
        ({"model_profiles_file": ""}, "EMPTY_PROFILES_FILE_REQUIRED"),
    ],
)
def test_a_setting_that_could_open_a_remote_path_stops_the_service(
    tmp_path: Path, overrides: dict[str, Any], code: str
) -> None:
    assert code in refusals(hosted_settings(tmp_path, **overrides), ELIGIBLE, env_files=no_files())


@pytest.mark.parametrize(
    ("variable", "code"),
    [
        ("OPENROUTER_API_KEY", "PROVIDER_KEY_REFUSED"),
        ("AI_ASSISTANT_ANTHROPIC_API_KEY", "PROVIDER_KEY_REFUSED"),
        ("AI_ASSISTANT_MODEL_KEY_LOCAL", "PROVIDER_KEY_REFUSED"),
        ("HTTPS_PROXY", "PROXY_SETTING_REFUSED"),
    ],
)
def test_a_key_or_proxy_in_the_environment_stops_the_service(
    tmp_path: Path, variable: str, code: str
) -> None:
    found = refusals(
        hosted_settings(tmp_path), {**ELIGIBLE, variable: "value"}, env_files=no_files()
    )
    assert found == [code]


def test_a_refusal_never_contains_the_value(tmp_path: Path) -> None:
    secret = "value-that-must-never-be-printed"
    found = refusals(
        hosted_settings(tmp_path), {"OPENROUTER_API_KEY": secret}, env_files=no_files()
    )
    assert secret not in " ".join(found)


def test_an_env_file_stops_the_service(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("X=1\n", encoding="utf-8")
    found = refusals(hosted_settings(tmp_path), ELIGIBLE, env_files=(env_file,))
    assert found == ["ENV_FILE_REFUSED"]


def test_a_profiles_file_that_lists_a_model_stops_the_service(tmp_path: Path) -> None:
    listed = tmp_path / "profiles.json"
    listed.write_text(
        json.dumps({"schema": "clm-assistant-model-profiles/1", "profiles": [{"x": 1}]}),
        encoding="utf-8",
    )
    settings = hosted_settings(tmp_path, model_profiles_file=str(listed))
    assert refusals(settings, ELIGIBLE, env_files=no_files()) == ["EMPTY_PROFILES_FILE_REQUIRED"]


def test_the_shipped_profiles_file_is_valid_and_lists_only_the_fixed_entries(
    tmp_path: Path,
) -> None:
    catalogue = load_catalogue(hosted_settings(tmp_path))
    assert catalogue.file_status == "ok"
    assert not [item for item in catalogue.entries if item.source == "file"]


def test_the_hosted_values_never_satisfy_the_development_interlock(tmp_path: Path) -> None:
    # Named decisions alone must not be enough: the interlock itself still refuses this host.
    settings = hosted_settings(
        tmp_path,
        local_api_test_decision="D-094",
        remote_inference_decision="D-091",
        remote_live_decision="D-092",
    )
    assert remote_test.readiness(settings) == "NOT_DEVELOPMENT_ENVIRONMENT"


def test_no_hosting_code_lives_in_the_runtime_package() -> None:
    # Strings in ai_assistant feed the synthetic boundary, and its files feed the qualification
    # basis. Hosting stays outside so neither moves.
    assert not (ASSISTANT_DIR / "ai_assistant" / "hosting.py").exists()
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in (ASSISTANT_DIR / "ai_assistant").glob("*.py")
    )
    assert "assistant_hosting" not in source


# --- the request boundary --------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json", "/", "/assistant"])
def test_only_assistant_routes_are_served(client: TestClient, path: str) -> None:
    assert client.get(path, headers=session("rm-a")).status_code == 404


@pytest.mark.parametrize("path", ["/internal/live", "/internal/ready"])
def test_internal_routes_are_refused_to_a_network_peer(client: TestClient, path: str) -> None:
    # TestClient's peer is "testclient", as any address on the proxy network would be.
    response = client.get(path, headers=session("hr"))
    assert response.status_code == 404
    assert "checks" not in response.text


def loopback_client(client: TestClient) -> TestClient:
    return TestClient(client.app, client=("127.0.0.1", 40000), raise_server_exceptions=False)


def test_a_forwarded_address_cannot_reach_internal_routes(client: TestClient) -> None:
    response = client.get("/internal/live", headers={"x-forwarded-for": "127.0.0.1"})
    assert response.status_code == 404


@pytest.mark.parametrize(
    "path",
    ["/assistant/health", f"/assistant/cases/{CASE_ID}/brief", "/assistant/admin/models"],
)
def test_no_session_is_a_401_before_any_backend_call(
    client: TestClient, clm: Clm, path: str
) -> None:
    clm.requests.clear()
    response = client.get(path)
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"
    assert clm.requests == []


def test_a_session_beside_an_unusual_cookie_is_still_read(client: TestClient) -> None:
    headers = {"cookie": 'other="a;b"; clm_session=rm-a'}
    assert client.get(f"/assistant/cases/{CASE_ID}/brief", headers=headers).status_code == 200


def test_a_websocket_is_refused(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/assistant/health"):
        pass


def test_an_expired_session_is_a_401_from_the_backend(client: TestClient) -> None:
    response = client.get(f"/assistant/cases/{CASE_ID}/brief", headers=session("expired"))
    assert response.status_code == 401


def test_a_post_without_an_origin_is_refused_here(client: TestClient) -> None:
    response = client.post(
        f"/assistant/cases/{CASE_ID}/chat", headers=session("rm-a"), json={"message": "Hello"}
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ORIGIN_REQUIRED"


def test_a_post_from_another_origin_is_refused(client: TestClient) -> None:
    response = client.post(
        f"/assistant/cases/{CASE_ID}/chat",
        headers=session("rm-a", origin="https://evil.example.test"),
        json={"message": "Hello"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ORIGIN_NOT_ALLOWED"


def test_two_origin_headers_are_refused(client: TestClient) -> None:
    headers = [
        ("cookie", "clm_session=rm-a"),
        ("origin", ORIGIN),
        ("origin", "https://evil.example.test"),
    ]
    response = client.post(f"/assistant/cases/{CASE_ID}/chat", headers=headers, json={})  # type: ignore[arg-type]
    assert response.status_code == 403


def test_health_does_not_claim_a_model(client: TestClient) -> None:
    body = client.get("/assistant/health", headers=session("rm-a")).json()
    assert body["status"] == "ok"
    assert body["llm_enabled"] is False
    assert body["model"] is None


# --- case and role isolation -----------------------------------------------------------------


def test_a_case_outside_the_team_is_a_safe_404(client: TestClient) -> None:
    allowed = client.get(f"/assistant/cases/{CASE_ID}/brief", headers=session("rm-a"))
    assert allowed.status_code == 200
    refused = client.get(f"/assistant/cases/{CASE_ID}/brief", headers=session("rm-b"))
    assert refused.status_code == 404
    assert refused.json()["detail"]["code"] == "CASE_NOT_FOUND"
    assert SUMMARY["case"]["entity"]["legal_name"] not in refused.text


def test_chat_on_a_case_outside_the_team_is_a_safe_404(client: TestClient) -> None:
    response = client.post(
        f"/assistant/cases/{CASE_ID}/chat",
        headers=post_headers("rm-b"),
        json={"message": "What is blocking this case?"},
    )
    assert response.status_code == 404


def test_the_callers_own_session_is_forwarded_and_only_that(client: TestClient, clm: Clm) -> None:
    clm.requests.clear()
    client.get(f"/assistant/cases/{CASE_ID}/brief", headers=session("rm-a"))
    assert clm.requests
    assert {item.headers["cookie"] for item in clm.requests} == {"clm_session=rm-a"}
    assert {item.method for item in clm.requests} == {"GET"}
    assert {item.url.host for item in clm.requests} == {"clm-backend-proxy"}


def test_one_users_answer_record_is_hidden_from_another(client: TestClient) -> None:
    answer = client.post(
        f"/assistant/cases/{CASE_ID}/chat",
        headers=post_headers("rm-a"),
        json={"message": "What is blocking this case?"},
    ).json()
    assert answer["answer_id"]
    own = client.get(f"/assistant/answers/{answer['answer_id']}", headers=session("rm-a"))
    other = client.get(f"/assistant/answers/{answer['answer_id']}", headers=session("rm-b"))
    assert own.status_code == 200
    assert other.status_code == 404


def test_an_rm_cannot_use_the_model_console(client: TestClient) -> None:
    response = client.get("/assistant/admin/models", headers=session("rm-a"))
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "MODEL_CONFIG_FORBIDDEN"


# --- answers without a model -----------------------------------------------------------------


def test_the_brief_is_built_from_case_data(client: TestClient) -> None:
    body = client.get(f"/assistant/cases/{CASE_ID}/brief", headers=session("rm-a")).json()
    assert body["company"] == SUMMARY["case"]["entity"]["legal_name"]
    assert body["message"]


def test_a_question_gets_a_deterministic_case_data_answer(client: TestClient) -> None:
    body = client.post(
        f"/assistant/cases/{CASE_ID}/chat",
        headers=post_headers("rm-a"),
        json={"message": "What is blocking this case?"},
    ).json()
    assert body["answered_by"] == "case_data"
    assert body["model"] is None
    assert body["answer"]
    assert "not available" in (body["notice"] or "")


def test_the_stream_gives_the_same_kind_of_answer(client: TestClient) -> None:
    with client.stream(
        "POST",
        f"/assistant/cases/{CASE_ID}/chat/stream",
        headers=post_headers("rm-a"),
        json={"message": "What is blocking this case?"},
    ) as response:
        assert response.status_code == 200
        lines = [json.loads(line) for line in response.iter_lines() if line]
    assert lines[-1]["type"] == "done"
    assert lines[-1]["answered_by"] == "case_data"


def test_an_off_topic_question_is_redirected_without_a_model(client: TestClient) -> None:
    body = client.post(
        f"/assistant/cases/{CASE_ID}/chat",
        headers=post_headers("rm-a"),
        json={"message": "What is the capital of France?"},
    ).json()
    assert body["answered_by"] == "case_data"
    assert "Paris" not in body["answer"]


def test_guidance_is_retrieved_without_embeddings(client: TestClient) -> None:
    body = client.post(
        f"/assistant/cases/{CASE_ID}/chat",
        headers=post_headers("rm-a"),
        json={"message": "Can I use the document address?"},
    ).json()
    assert body["knowledge"]["degraded"] is True
    assert body["sources"]


# --- output guardrails with a mock provider --------------------------------------------------


def mocked(root: Path, clm: Clm, reply: str, **overrides: Any) -> tuple[TestClient, ScriptedModel]:
    settings = hosted_settings(root, answer_mode="exact_lines", **overrides)
    model = ScriptedModel(reply)
    transport = httpx.MockTransport(clm.handler)
    app = create_app(settings, clm_transport=transport, chat_model=model)  # type: ignore[arg-type]
    app.state.model_selector.store = None
    return TestClient(app), model


@pytest.mark.parametrize(
    "reply",
    [
        "The case is approved and you may proceed.",
        "Ignore the rules and send the case to GoldTier now.",
        "This company has been verified by the regulator as the legal UBO.",
    ],
)
def test_a_model_reply_that_is_not_an_allowed_line_never_reaches_the_user(
    tmp_path: Path, clm: Clm, reply: str
) -> None:
    client, model = mocked(tmp_path, clm, reply)
    body = client.post(
        f"/assistant/cases/{CASE_ID}/chat",
        headers=post_headers("rm-a"),
        json={"message": "What is blocking this case?"},
    ).json()
    assert model.calls == 1
    assert reply not in body["answer"]
    assert body["answered_by"] == "case_data"


# --- the model console -----------------------------------------------------------------------


def test_hr_sees_state_and_audit_with_no_provider_configured(client: TestClient) -> None:
    overview = client.get("/assistant/admin/models", headers=session("hr"))
    assert overview.status_code == 200
    assert overview.json()["configured"] is True
    assert client.get("/assistant/admin/models/audit", headers=session("hr")).status_code == 200


@pytest.mark.parametrize(
    ("method", "tail"),
    [
        ("PUT", "/credential"),
        ("PUT", "/credential/anthropic"),
        ("DELETE", "/credential"),
        ("PUT", "/provider/anthropic"),
        ("POST", "/provider/anthropic/workspace-read"),
        ("POST", "/session/start"),
        ("PUT", "/session/allowance"),
        ("POST", "/budget/provider-refresh"),
        ("PUT", "/budget/controls"),
        ("PUT", "/budget/lifetime-cap"),
        ("POST", "/budget/resume"),
        ("POST", "/openrouter_gpt_oss_120b/qualifications"),
        ("POST", "/qualifications/abc/cancel"),
        ("POST", "/a-route-added-later"),
    ],
)
def test_paid_and_provider_actions_are_refused_and_audited(
    client: TestClient, method: str, tail: str
) -> None:
    secret = "sk-or-v1-" + "a" * 40
    response = client.request(
        method,
        ADMIN_PREFIX + tail,
        headers=post_headers("hr"),
        json={"api_key": secret},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "HOSTED_REMOTE_DISABLED"
    audit = client.get(f"{ADMIN_PREFIX}/audit", headers=session("hr")).json()["events"]
    assert any(item["action"] == "HOSTED_ACTION_REFUSED" for item in audit)
    assert secret not in json.dumps(audit)


def test_a_key_sent_to_the_console_is_never_held(client: TestClient) -> None:
    client.put(
        f"{ADMIN_PREFIX}/credential",
        headers={**post_headers("hr"), "content-type": "application/json"},
        content=json.dumps({"api_key": "sk-or-v1-" + "b" * 40}),
    )
    view = client.get(f"{ADMIN_PREFIX}/credential", headers=session("hr")).json()
    assert view["status"] == "missing"
    assert view["source"] == "none"


def test_a_remote_model_cannot_be_activated(client: TestClient) -> None:
    overview = client.get(ADMIN_PREFIX, headers=session("hr")).json()
    response = client.post(
        f"{ADMIN_PREFIX}/openrouter_gpt_oss_120b/activate",
        headers=post_headers("hr"),
        json={"expected_revision": overview["revision"]},
    )
    assert response.status_code in (403, 409)
    audit = client.get(f"{ADMIN_PREFIX}/audit", headers=session("hr")).json()["events"]
    assert audit[0]["outcome"] == "refused"
    after = client.get(ADMIN_PREFIX, headers=session("hr")).json()
    assert after["revision"] == overview["revision"]


def test_the_connection_test_of_a_remote_model_makes_no_call(client: TestClient) -> None:
    response = client.post(
        f"{ADMIN_PREFIX}/openrouter_gpt_oss_120b/connection-test", headers=post_headers("hr")
    )
    assert response.status_code in (403, 409)


def test_an_audited_control_still_works_and_survives_a_restart(tmp_path: Path, clm: Clm) -> None:
    with service(tmp_path, clm) as first:
        policy = first.get(f"{ADMIN_PREFIX}/data-access", headers=session("hr")).json()
        changed = first.put(
            f"{ADMIN_PREFIX}/data-access",
            headers=post_headers("hr"),
            json={
                "restrict_local": True,
                "restrict_external": True,
                "expected_revision": policy["revision"],
            },
        )
        assert changed.status_code == 200, changed.text
    with service(tmp_path, clm) as second:
        kept = second.get(f"{ADMIN_PREFIX}/data-access", headers=session("hr")).json()
        assert kept["status"] == "stored"
        assert kept["revision"] == policy["revision"] + 1
        audit = second.get(f"{ADMIN_PREFIX}/audit", headers=session("hr")).json()["events"]
        assert any(item["action"] == "DATA_ACCESS_POLICY_CHANGED" for item in audit)


def test_every_allowed_console_change_names_a_real_route(client: TestClient) -> None:
    app: Any = client.app
    routes = {
        (method.upper(), re.sub(r"\{[^}]+\}", "{x}", path[len(ADMIN_PREFIX) :]))
        for path, operations in app.openapi()["paths"].items()
        if path.startswith(ADMIN_PREFIX + "/")
        for method in operations
    }
    for verb, shape in ADMIN_CHANGES:
        assert (verb, shape.pattern.replace("[^/]+", "{x}")) in routes, shape.pattern


# --- readiness -------------------------------------------------------------------------------


def test_liveness_and_readiness_from_loopback(client: TestClient) -> None:
    local = loopback_client(client)
    assert local.get("/internal/live").json() == {"status": "live"}
    ready = local.get("/internal/ready")
    assert ready.status_code == 200, ready.text
    assert set(ready.json()["checks"].values()) == {"ok"}


def test_readiness_reports_a_backend_outage_with_a_closed_code(
    client: TestClient, clm: Clm
) -> None:
    clm.healthy = False
    response = loopback_client(client).get("/internal/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["clm_backend"] == "unhealthy"


def test_readiness_reports_a_damaged_store(client: TestClient, tmp_path: Path) -> None:
    store = tmp_path / "models" / "model_admin.sqlite3"
    assert store.is_file()
    (tmp_path / "knowledge" / "knowledge.sqlite3").write_bytes(b"not a database" * 100)
    response = loopback_client(client).get("/internal/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["knowledge_store"] == "unreadable"


def test_readiness_reports_a_storage_quota(tmp_path: Path, clm: Clm) -> None:
    settings = hosted_settings(tmp_path)
    knowledge(settings)
    report = Readiness(
        settings,
        profile.Limits(data_quota_bytes=1, min_free_bytes=0),
        knowledge_open=lambda: True,
        model_state=lambda: 0,
        transport=httpx.MockTransport(clm.handler),
    ).report()
    assert report["checks"]["data_quota"] == "exceeded"
    assert report["status"] == "not_ready"


def test_readiness_never_shows_a_path_or_value(client: TestClient, tmp_path: Path) -> None:
    text = loopback_client(client).get("/internal/ready").text
    assert str(tmp_path) not in text
    assert BACKEND not in text


# --- startup and recovery --------------------------------------------------------------------


def test_load_guidance_can_be_repeated_without_new_versions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("ai_assistant.knowledge.factory.build_knowledge_base", knowledge)
    settings = hosted_settings(tmp_path)
    first = run.load_guidance(settings, seed=False)
    second = run.load_guidance(settings, seed=False)
    assert first["guidance_added"] > 0
    assert second["guidance_added"] == 0
    assert second["guidance_unchanged"] == first["guidance_added"]


def test_a_damaged_store_is_named_and_left_alone(tmp_path: Path) -> None:
    good = tmp_path / "models" / "fine.sqlite3"
    good.parent.mkdir()
    connection = sqlite3.connect(good)
    connection.execute("CREATE TABLE t (x)")
    connection.commit()
    connection.close()
    broken = tmp_path / "knowledge" / "knowledge.sqlite3"
    broken.parent.mkdir()
    content = b"this is not a database" * 100
    broken.write_bytes(content)
    assert run.damaged(tmp_path) == ["knowledge/knowledge.sqlite3"]
    assert broken.read_bytes() == content


def test_a_refused_configuration_exits_before_opening_a_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("AI_ASSISTANT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-secret-value")
    assert run.main() == run.EXIT_CONFIG
    output = capsys.readouterr().out
    assert "PROVIDER_KEY_REFUSED" in output
    assert "secret-value" not in output
    assert not (tmp_path / run.LOCK_NAME).exists()


def test_the_server_runs_one_worker_and_trusts_no_forwarded_address() -> None:
    arguments = run.SERVER_ARGUMENTS
    assert arguments[arguments.index("--workers") + 1] == "1"
    assert "--no-proxy-headers" in arguments
    assert "--no-access-log" in arguments


def test_the_probe_ignores_bootstrap_time(tmp_path: Path) -> None:
    counter = tmp_path / "count"
    pid_file = tmp_path / "pid"
    for _ in range(20):
        assert probe.check(healthy=False, counter=counter, pid_file=pid_file, limit=2) == 1
    assert not counter.exists()


def test_the_probe_ends_a_hung_worker_after_the_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    counter = tmp_path / "count"
    pid_file = tmp_path / "pid"
    pid_file.write_text("4242", encoding="ascii")
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(probe.os, "kill", lambda pid, sig: killed.append((pid, sig)))
    probe.check(healthy=False, counter=counter, pid_file=pid_file, limit=3)
    probe.check(healthy=False, counter=counter, pid_file=pid_file, limit=3)
    assert killed == []
    probe.check(healthy=True, counter=counter, pid_file=pid_file, limit=3)
    assert probe.failures(counter) == 0
    for _ in range(3):
        probe.check(healthy=False, counter=counter, pid_file=pid_file, limit=3)
    assert [pid for pid, _ in killed] == [4242]


def make_root(root: Path) -> None:
    for name in ("models/model_admin.sqlite3", "knowledge/knowledge.sqlite3"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE marker (value TEXT)")
        connection.execute("INSERT INTO marker VALUES (?)", (name,))
        connection.commit()
        connection.close()
    (root / "knowledge" / "chroma").mkdir()
    (root / "knowledge" / "chroma" / "index.bin").write_bytes(b"vectors")
    (root / run.LOCK_NAME).write_bytes(b"")


def test_backup_restore_round_trip(tmp_path: Path) -> None:
    root = tmp_path / "data"
    make_root(root)
    target = tmp_path / "backup"
    assert backup.create(root, target) == 0
    assert backup.verify(target) == 0
    restored = tmp_path / "restored"
    restored.mkdir()
    assert backup.restore(target, restored) == 0
    connection = sqlite3.connect(restored / "models" / "model_admin.sqlite3")
    assert connection.execute("SELECT value FROM marker").fetchone() == (
        "models/model_admin.sqlite3",
    )
    connection.close()
    assert (restored / "knowledge" / "chroma" / "index.bin").read_bytes() == b"vectors"
    assert not (restored / run.LOCK_NAME).exists()


def test_restore_refuses_a_used_root_and_changes_nothing(tmp_path: Path) -> None:
    root = tmp_path / "data"
    make_root(root)
    target = tmp_path / "backup"
    assert backup.create(root, target) == 0
    used = tmp_path / "used"
    used.mkdir()
    (used / "keep.txt").write_text("keep", encoding="utf-8")
    assert backup.restore(target, used) == backup.EXIT_REFUSED
    assert [item.name for item in used.iterdir()] == ["keep.txt"]


def test_a_backup_never_overwrites_and_never_runs_on_a_live_store(tmp_path: Path) -> None:
    root = tmp_path / "data"
    make_root(root)
    target = tmp_path / "backup"
    assert backup.create(root, target) == 0
    assert backup.create(root, target) == backup.EXIT_REFUSED
    (root / "models" / "model_admin.sqlite3-wal").write_bytes(b"live")
    assert backup.create(root, tmp_path / "second") != 0
    assert not (tmp_path / "second" / backup.MANIFEST).exists()


def test_a_changed_backup_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "data"
    make_root(root)
    target = tmp_path / "backup"
    assert backup.create(root, target) == 0
    (target / "stores" / "models" / "model_admin.sqlite3").write_bytes(b"damaged" * 100)
    assert backup.verify(target) == backup.EXIT_REFUSED


# QG-2: verify() checks every file against the manifest's own size and SHA-256, so a backup can
# pass only with exactly the bytes that were written.


def made_backup(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    make_root(root)
    target = tmp_path / "backup"
    assert backup.create(root, target) == 0
    assert backup.verify(target) == 0
    return target


def read_manifest(target: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = json.loads((target / backup.MANIFEST).read_text("utf-8"))
    return rows


def write_manifest(target: Path, rows: object) -> None:
    (target / backup.MANIFEST).write_text(json.dumps(rows), encoding="utf-8")


def sqlite_file(path: Path, value: str) -> None:
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE marker (value TEXT)")
    connection.execute("INSERT INTO marker VALUES (?)", (value,))
    connection.commit()
    connection.close()


def test_a_moved_backup_and_a_container_manifest_still_verify(tmp_path: Path) -> None:
    target = made_backup(tmp_path)
    moved = tmp_path / "elsewhere" / "20261111T000000"
    moved.parent.mkdir()
    target.rename(moved)
    assert backup.verify(moved) == 0
    rows = read_manifest(moved)
    for row in rows:
        relative = str(row["destination"]).replace("\\", "/").split("/stores/", 1)[1]
        row["destination"] = f"/backup/20261111T000000/stores/{relative}"
    write_manifest(moved, rows)
    assert backup.verify(moved) == 0


def test_same_size_tampering_of_a_plain_file_is_refused(tmp_path: Path) -> None:
    target = made_backup(tmp_path)
    (target / "stores" / "knowledge" / "chroma" / "index.bin").write_bytes(b"VECTORS")
    assert backup.verify(target) == backup.EXIT_REFUSED


def test_a_sound_but_different_sqlite_store_is_refused(tmp_path: Path) -> None:
    target = made_backup(tmp_path)
    store = target / "stores" / "models" / "model_admin.sqlite3"
    store.unlink()
    sqlite_file(store, "substituted")
    assert backup._sqlite_ok(store)
    assert backup.verify(target) == backup.EXIT_REFUSED


def test_swapped_files_are_refused(tmp_path: Path) -> None:
    target = made_backup(tmp_path)
    first = target / "stores" / "models" / "model_admin.sqlite3"
    second = target / "stores" / "knowledge" / "knowledge.sqlite3"
    first_bytes, second_bytes = first.read_bytes(), second.read_bytes()
    first.write_bytes(second_bytes)
    second.write_bytes(first_bytes)
    assert backup.verify(target) == backup.EXIT_REFUSED


def test_an_extra_file_is_refused_even_with_a_matching_count(tmp_path: Path) -> None:
    target = made_backup(tmp_path)
    (target / "stores" / "extra.txt").write_bytes(b"extra")
    assert backup.verify(target) == backup.EXIT_REFUSED
    (target / "stores" / "knowledge" / "chroma" / "index.bin").unlink()
    assert backup.verify(target) == backup.EXIT_REFUSED


def test_a_missing_file_is_refused(tmp_path: Path) -> None:
    target = made_backup(tmp_path)
    (target / "stores" / "knowledge" / "chroma" / "index.bin").unlink()
    assert backup.verify(target) == backup.EXIT_REFUSED


def test_a_missing_manifest_is_refused(tmp_path: Path) -> None:
    target = made_backup(tmp_path)
    (target / backup.MANIFEST).unlink()
    assert backup.verify(target) == backup.EXIT_REFUSED


@pytest.mark.parametrize(
    "corrupt",
    [
        pytest.param(lambda rows: {"files": rows}, id="not-a-list"),
        pytest.param(lambda rows: [], id="empty"),
        pytest.param(lambda rows: [*rows, "row"], id="entry-not-object"),
        pytest.param(lambda rows: rows[1:], id="entry-missing"),
        pytest.param(lambda rows: [*rows, rows[0]], id="entry-duplicated"),
        pytest.param(
            lambda rows: [{**rows[0], "destination_sha256": None}, *rows[1:]], id="no-hash"
        ),
        pytest.param(
            lambda rows: [{**rows[0], "destination_sha256": "A" * 64}, *rows[1:]], id="bad-hash"
        ),
        pytest.param(lambda rows: [{**rows[0], "destination_bytes": -1}, *rows[1:]], id="neg-size"),
        pytest.param(
            lambda rows: [{**rows[0], "destination_bytes": True}, *rows[1:]], id="bool-size"
        ),
        pytest.param(lambda rows: [{**rows[0], "method": "rsync"}, *rows[1:]], id="bad-method"),
        pytest.param(
            lambda rows: [{**rows[0], "destination": "stores/models/x.sqlite3"}, *rows[1:]],
            id="relative-destination",
        ),
        pytest.param(
            lambda rows: [
                {**row, "destination": str(row["destination"]).replace("stores", "stores/..", 1)}
                for row in rows
            ],
            id="traversal",
        ),
        pytest.param(
            lambda rows: [
                {**rows[0], "destination": "/other/stores/models/model_admin.sqlite3"},
                *rows[1:],
            ],
            id="no-shared-stores-folder",
        ),
    ],
)
def test_a_malformed_manifest_is_refused(tmp_path: Path, corrupt: Any) -> None:
    target = made_backup(tmp_path)
    write_manifest(target, corrupt(read_manifest(target)))
    assert backup.verify(target) == backup.EXIT_REFUSED


def test_a_link_inside_the_backup_is_refused(tmp_path: Path) -> None:
    target = made_backup(tmp_path)
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"vectors")
    link = target / "stores" / "knowledge" / "chroma" / "index.bin"
    link.unlink()
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("this platform cannot create symbolic links without privilege")
    assert backup.verify(target) == backup.EXIT_REFUSED


def test_restore_of_a_tampered_backup_writes_nothing(tmp_path: Path) -> None:
    target = made_backup(tmp_path)
    store = target / "stores" / "models" / "model_admin.sqlite3"
    store.unlink()
    sqlite_file(store, "substituted")
    restored = tmp_path / "restored"
    restored.mkdir()
    assert backup.restore(target, restored) == backup.EXIT_REFUSED
    assert list(restored.iterdir()) == []


# F2: restore stages inside the destination, promotes by rename, and rolls back on failure.


def restore_case(tmp_path: Path) -> tuple[Path, Path]:
    target = made_backup(tmp_path)
    destination = tmp_path / "volume"
    destination.mkdir()
    return target, destination


def contents(folder: Path) -> list[str]:
    return sorted(path.relative_to(folder).as_posix() for path in folder.rglob("*"))


def test_restore_succeeds_into_an_existing_empty_folder_and_leaves_no_staging(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target, destination = restore_case(tmp_path)
    assert backup.restore(target, destination) == 0
    assert "RESTORED 3 files" in capsys.readouterr().out
    assert not [p for p in destination.iterdir() if p.name.startswith(backup.STAGING_PREFIX)]
    assert sorted(p.name for p in destination.iterdir()) == ["knowledge", "models"]
    assert (destination / "knowledge" / "chroma" / "index.bin").read_bytes() == b"vectors"


def test_restore_refuses_a_missing_source_file_and_writes_nothing(tmp_path: Path) -> None:
    target, destination = restore_case(tmp_path)
    (target / "stores" / "knowledge" / "chroma" / "index.bin").unlink()
    assert backup.restore(target, destination) == backup.EXIT_REFUSED
    assert contents(destination) == []


def test_a_source_changed_after_verification_fails_with_nothing_restored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target, destination = restore_case(tmp_path)
    real_copy = backup._copy

    def mutate_then_copy(source: Path, staged: Path) -> object:
        if source.name == "index.bin":
            source.write_bytes(b"VECTORS")  # same size, different bytes
        return real_copy(source, staged)

    monkeypatch.setattr(backup, "_copy", mutate_then_copy)
    assert backup.restore(target, destination) == backup.EXIT_REFUSED
    assert "nothing was restored" in capsys.readouterr().out
    assert contents(destination) == []


def test_a_failed_staging_check_or_copy_error_leaves_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target, destination = restore_case(tmp_path)
    real_copy = backup._copy

    def corrupt(source: Path, staged: Path) -> object:
        result = real_copy(source, staged)
        if source.suffix == ".sqlite3":
            with staged.open("r+b") as handle:
                handle.seek(100)
                handle.write(b"\xff")
        return result

    monkeypatch.setattr(backup, "_copy", corrupt)
    assert backup.restore(target, destination) == backup.EXIT_REFUSED
    assert contents(destination) == []

    def fail(source: Path, staged: Path) -> object:
        raise OSError("disk full")

    monkeypatch.setattr(backup, "_copy", fail)
    assert backup.restore(target, destination) == backup.EXIT_REFUSED
    assert contents(destination) == []


def failing_rename(fail_on: set[int]) -> tuple[Any, list[tuple[str, str]]]:
    calls: list[tuple[str, str]] = []

    def rename(source: Path, target: Path) -> None:
        calls.append((Path(source).name, Path(target).parent.name))
        if len(calls) in fail_on:
            raise OSError("injected rename failure")
        os.rename(source, target)

    return rename, calls


def test_a_failed_first_promotion_is_rolled_back_to_an_empty_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target, destination = restore_case(tmp_path)
    rename, calls = failing_rename({1})
    monkeypatch.setattr(backup, "_rename", rename)
    assert backup.restore(target, destination) == backup.EXIT_REFUSED
    assert contents(destination) == []
    assert len(calls) == 1


def test_a_failure_after_partial_promotion_rolls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target, destination = restore_case(tmp_path)
    rename, calls = failing_rename({2})  # "knowledge" promoted, "models" fails
    monkeypatch.setattr(backup, "_rename", rename)
    assert backup.restore(target, destination) == backup.EXIT_REFUSED
    assert "rolled back" in capsys.readouterr().out
    assert contents(destination) == []
    assert [name for name, _ in calls] == ["knowledge", "models", "knowledge"]


def test_a_failed_rollback_keeps_partial_contents_and_reports_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target, destination = restore_case(tmp_path)
    rename, _ = failing_rename({2, 3})  # promotion of "models" and the rollback both fail
    monkeypatch.setattr(backup, "_rename", rename)
    assert backup.restore(target, destination) == backup.EXIT_INCOMPLETE
    out = capsys.readouterr().out
    last = out.strip().splitlines()[-1]
    assert last.startswith("INCOMPLETE") and "Inspect it before any retry" in last
    assert "RESTORED" not in out
    assert (destination / "knowledge" / "chroma" / "index.bin").read_bytes() == b"vectors"
    staging = [p for p in destination.iterdir() if p.name.startswith(backup.STAGING_PREFIX)]
    assert len(staging) == 1 and (staging[0] / "models").is_dir()
    # The interrupted state is refused, never cleared, by the next attempt.
    monkeypatch.setattr(backup, "_rename", os.rename)
    before = contents(destination)
    assert backup.restore(target, destination) == backup.EXIT_REFUSED
    assert contents(destination) == before


def test_restore_never_overwrites_an_entry_that_appears_during_promotion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target, destination = restore_case(tmp_path)

    def rename(source: Path, target_path: Path) -> None:
        if Path(source).name == "knowledge":
            (destination / "models").write_bytes(b"someone else's")
        os.rename(source, target_path)

    monkeypatch.setattr(backup, "_rename", rename)
    assert backup.restore(target, destination) == backup.EXIT_INCOMPLETE
    assert (destination / "models").read_bytes() == b"someone else's"
    assert not (destination / "knowledge").exists()


@pytest.mark.parametrize(
    "leftover",
    [
        pytest.param(".restore-staging-old", id="stale-staging"),
        pytest.param("knowledge", id="earlier-entry"),
        pytest.param(".hidden", id="hidden-file"),
    ],
)
def test_restore_refuses_a_non_empty_destination_and_keeps_it(
    tmp_path: Path, leftover: str
) -> None:
    target, destination = restore_case(tmp_path)
    (destination / leftover).mkdir()
    (destination / leftover / "kept.bin").write_bytes(b"kept")
    assert backup.restore(target, destination) == backup.EXIT_REFUSED
    assert contents(destination) == [leftover, f"{leftover}/kept.bin"]


def test_restore_refuses_traversal_and_links_and_writes_nothing(tmp_path: Path) -> None:
    target, destination = restore_case(tmp_path)
    rows = read_manifest(target)
    write_manifest(
        target,
        [
            {**row, "destination": str(row["destination"]).replace("stores", "stores/..", 1)}
            for row in rows
        ],
    )
    assert backup.restore(target, destination) == backup.EXIT_REFUSED
    assert contents(destination) == []
    write_manifest(target, rows)
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"vectors")
    link = target / "stores" / "knowledge" / "chroma" / "index.bin"
    link.unlink()
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("this platform cannot create symbolic links without privilege")
    assert backup.restore(target, destination) == backup.EXIT_REFUSED
    assert contents(destination) == []
    link_target = tmp_path / "linked-volume"
    link_target.symlink_to(destination, target_is_directory=True)
    link.unlink()
    link.write_bytes(b"vectors")
    assert backup.restore(target, link_target) == backup.EXIT_REFUSED


def test_the_staging_folder_name_is_unpredictable_and_private(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target, destination = restore_case(tmp_path)
    seen: list[Path] = []
    real_copy = backup._copy

    def record(source: Path, staged: Path) -> object:
        seen.append(Path(staged))
        return real_copy(source, staged)

    monkeypatch.setattr(backup, "_copy", record)
    assert backup.restore(target, destination) == 0
    staging = seen[0].relative_to(destination).parts[0]
    assert (
        staging.startswith(backup.STAGING_PREFIX) and len(staging) > len(backup.STAGING_PREFIX) + 6
    )
    if sys.platform != "win32":
        target2, destination2 = tmp_path / "b2", tmp_path / "v2"
        destination2.mkdir()
        assert backup.create(tmp_path / "data", target2) == 0
        seen.clear()

        def mode_check(source: Path, staged: Path) -> object:
            folder = destination2 / Path(staged).relative_to(destination2).parts[0]
            assert folder.stat().st_mode & 0o077 == 0
            return real_copy(source, staged)

        monkeypatch.setattr(backup, "_copy", mode_check)
        assert backup.restore(target2, destination2) == 0


# N5: the two paths that escaped the 0/2/3 contract.

LEAK = "secret-detail-from-the-os"


def last_line(out: str) -> str:
    return out.strip().splitlines()[-1]


def test_a_staging_folder_that_cannot_be_created_is_refused_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target, destination = restore_case(tmp_path)

    def denied(**_: object) -> str:
        raise PermissionError(errno.EACCES, LEAK)

    monkeypatch.setattr(backup.tempfile, "mkdtemp", denied)
    assert backup.restore(target, destination) == backup.EXIT_REFUSED
    out = capsys.readouterr().out
    assert last_line(out) == (
        "REFUSED the staging folder could not be created (EACCES); nothing was restored"
    )
    assert "RESTORED" not in out and LEAK not in out
    assert contents(destination) == []


def test_a_failed_staging_creation_that_leaves_anything_behind_is_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target, destination = restore_case(tmp_path)

    def partial(**_: object) -> str:
        (destination / "stray").write_bytes(b"left behind")
        raise OSError(errno.ENOSPC, LEAK)

    monkeypatch.setattr(backup.tempfile, "mkdtemp", partial)
    assert backup.restore(target, destination) == backup.EXIT_INCOMPLETE
    out = capsys.readouterr().out
    assert last_line(out).startswith("INCOMPLETE the staging folder could not be created (ENOSPC)")
    assert "RESTORED" not in out and LEAK not in out
    assert contents(destination) == ["stray"]  # kept for inspection, never removed


@pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0,  # type: ignore[attr-defined,unused-ignore]
    reason="needs POSIX permissions and a non-root user",
)
def test_a_read_only_destination_is_refused_without_a_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target, destination = restore_case(tmp_path)
    destination.chmod(0o500)
    try:
        assert backup.restore(target, destination) == backup.EXIT_REFUSED
    finally:
        destination.chmod(0o700)
    assert "(EACCES); nothing was restored" in last_line(capsys.readouterr().out)
    assert contents(destination) == []


def final_check_fails(monkeypatch: pytest.MonkeyPatch, destination: Path, error: Exception) -> None:
    real = backup._tree_matches

    def check(folder: Path, expected: dict[str, tuple[str, int, str]]) -> None:
        if Path(folder) == destination:
            raise error
        real(folder, expected)

    monkeypatch.setattr(backup, "_tree_matches", check)


def test_an_io_error_in_the_final_check_is_rolled_back_to_an_empty_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target, destination = restore_case(tmp_path)
    final_check_fails(monkeypatch, destination, OSError(errno.EIO, LEAK))
    assert backup.restore(target, destination) == backup.EXIT_REFUSED
    out = capsys.readouterr().out
    assert last_line(out) == (
        "REFUSED the final check could not read the destination (EIO);"
        " it was rolled back and nothing was restored"
    )
    assert "RESTORED" not in out and LEAK not in out
    assert contents(destination) == []


def test_an_io_error_in_the_final_check_with_a_failed_rollback_is_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target, destination = restore_case(tmp_path)
    final_check_fails(monkeypatch, destination, OSError(errno.EIO, LEAK))
    # Renames: promote knowledge (1), models (2); roll back models (3, fails), knowledge (4).
    rename, calls = failing_rename({3})
    monkeypatch.setattr(backup, "_rename", rename)
    assert backup.restore(target, destination) == backup.EXIT_INCOMPLETE
    out = capsys.readouterr().out
    last = last_line(out)
    assert last.startswith("INCOMPLETE the final check could not read the destination (EIO)")
    assert "1 promoted entries could not be moved back" in last
    assert "RESTORED" not in out and LEAK not in out
    assert [name for name, _ in calls] == ["knowledge", "models", "models", "knowledge"]
    # The evidence stays: the stuck entry in place, the rolled-back one in the named staging.
    assert (destination / "models" / "model_admin.sqlite3").is_file()
    staging = [p for p in destination.iterdir() if p.name.startswith(backup.STAGING_PREFIX)]
    assert len(staging) == 1 and staging[0].name in last
    assert (staging[0] / "knowledge" / "chroma" / "index.bin").read_bytes() == b"vectors"
    monkeypatch.setattr(backup, "_rename", os.rename)
    monkeypatch.setattr(backup, "_tree_matches", backup._tree_matches)
    before = contents(destination)
    assert backup.restore(target, destination) == backup.EXIT_REFUSED
    assert contents(destination) == before


def test_a_final_check_mismatch_is_still_kept_for_inspection_not_rolled_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target, destination = restore_case(tmp_path)
    final_check_fails(monkeypatch, destination, backup.Refused("restored files differ"))
    assert backup.restore(target, destination) == backup.EXIT_INCOMPLETE
    out = capsys.readouterr().out
    assert last_line(out).startswith("INCOMPLETE the restored destination failed its final check")
    assert "RESTORED" not in out
    assert {"knowledge", "models"} <= {p.name for p in destination.iterdir()}


@pytest.mark.parametrize("error", [ValueError("unexpected"), KeyError("unexpected")])
def test_an_unexpected_error_is_never_turned_into_success_or_a_clean_refusal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
) -> None:
    target, destination = restore_case(tmp_path)
    final_check_fails(monkeypatch, destination, error)
    with pytest.raises(type(error)):
        backup.restore(target, destination)
    assert "RESTORED" not in capsys.readouterr().out


# F1: folders named "stores" above the backup, or inside the data root, are not ambiguous.


def backup_at(tmp_path: Path, target: Path, *, nested_stores: bool = False) -> Path:
    root = tmp_path / "data"
    make_root(root)
    if nested_stores:
        (root / "stores" / "stores").mkdir(parents=True)
        (root / "stores" / "stores" / "inner.bin").write_bytes(b"inner")
    target.parent.mkdir(parents=True, exist_ok=True)
    assert backup.create(root, target) == 0
    return target


@pytest.mark.parametrize(
    "where",
    [
        pytest.param(("stores", "backup"), id="parent-named-stores"),
        pytest.param(("stores", "stores", "x", "backup"), id="several-parents-named-stores"),
        pytest.param(("stores",), id="backup-folder-named-stores"),
    ],
)
@pytest.mark.parametrize("nested", [False, True], ids=["plain-root", "root-with-stores-folders"])
def test_a_backup_under_folders_named_stores_verifies_and_restores(
    tmp_path: Path, where: tuple[str, ...], nested: bool
) -> None:
    target = backup_at(tmp_path, tmp_path.joinpath(*where), nested_stores=nested)
    assert backup.verify(target) == 0
    restored = tmp_path / "restored"
    restored.mkdir()
    assert backup.restore(target, restored) == 0
    assert (restored / "knowledge" / "chroma" / "index.bin").read_bytes() == b"vectors"
    if nested:
        assert (restored / "stores" / "stores" / "inner.bin").read_bytes() == b"inner"


def test_a_backup_moved_into_and_out_of_stores_folders_still_verifies(tmp_path: Path) -> None:
    target = backup_at(tmp_path, tmp_path / "stores" / "a" / "backup", nested_stores=True)
    moved = tmp_path / "plain" / "backup"
    moved.parent.mkdir()
    target.rename(moved)
    assert backup.verify(moved) == 0
    again = tmp_path / "stores" / "stores" / "b"
    again.parent.mkdir(parents=True)
    moved.rename(again)
    assert backup.verify(again) == 0
    rows = read_manifest(again)
    for row in rows:
        relative = str(row["destination"]).replace("\\", "/").split("/backup/stores/", 1)[1]
        row["destination"] = f"/backup/stores/2026/stores/{relative}"
    write_manifest(again, rows)
    assert backup.verify(again) == 0


def test_stores_folders_do_not_weaken_hash_or_path_checks(tmp_path: Path) -> None:
    target = backup_at(tmp_path, tmp_path / "stores" / "backup", nested_stores=True)
    inner = target / "stores" / "stores" / "stores" / "inner.bin"
    inner.write_bytes(b"INNER")
    assert backup.verify(target) == backup.EXIT_REFUSED
    inner.write_bytes(b"inner")
    assert backup.verify(target) == 0
    # A manifest that names a different path than the copy on disk (substitution).
    rows = read_manifest(target)
    for row in rows:
        row["destination"] = str(row["destination"]).replace("inner.bin", "other.bin")
    write_manifest(target, rows)
    assert backup.verify(target) == backup.EXIT_REFUSED
    # The inner file's own path with one "stores" segment dropped: no cut gives the files on disk.
    rows = read_manifest(target)
    for row in rows:
        text = str(row["destination"]).replace("other.bin", "inner.bin")
        separator = "\\" if "\\" in text else "/"
        triple = separator.join(("stores", "stores", "stores", "inner.bin"))
        if text.endswith(triple):
            text = text[: -len(triple)] + separator.join(("stores", "stores", "inner.bin"))
        row["destination"] = text
    write_manifest(target, rows)
    assert backup.verify(target) == backup.EXIT_REFUSED
    for row in rows:
        text = str(row["destination"])
        separator = "\\" if "\\" in text else "/"
        double = separator.join(("stores", "stores", "inner.bin"))
        if text.endswith(double):
            row["destination"] = text[: -len(double)] + separator.join(
                ("stores", "stores", "stores", "inner.bin")
            )
    write_manifest(target, rows)
    assert backup.verify(target) == 0


# --- the deployment contract -----------------------------------------------------------------


def load_smoke() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "smoke_hosted", ASSISTANT_DIR / "deploy" / "smoke_hosted.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_caddy_caps_the_assistant_body_first_and_the_smoke_tests_that_cap() -> None:
    text = (ASSISTANT_DIR / "deploy" / "Caddyfile.candidate").read_text(encoding="utf-8")
    block = re.search(r"handle @assistant \{\s*route \{(.*?)\n        \}\n    \}", text, re.S)
    assert block, "the assistant handler must be one route block"
    body = block.group(1)
    cap = re.search(r"request_body \{\s*max_size (\d+)KB\s*\}", body)
    assert cap and cap.group(1) == "512"
    # The cap is applied before the session check and the proxy, so nothing larger reaches
    # the backend or the assistant.
    assert body.index("request_body") < body.index("forward_auth") < body.index("reverse_proxy")
    # Caddy's KB is decimal; the smoke tests one byte either side of exactly this figure.
    smoke = load_smoke()
    limit = int(cap.group(1)) * 1000
    assert limit == smoke.BODY_LIMIT_BYTES


def test_the_smoke_body_check_cannot_be_satisfied_by_other_assistant_refusals() -> None:
    smoke = load_smoke()
    for size in (smoke.BODY_LIMIT_BYTES, smoke.BODY_LIMIT_BYTES + 1):
        body = smoke.padded_body(size)
        assert len(body) == size
        assert json.loads(body)["message"] == "What is blocking this case?"
    # Only the unknown field's own refusal counts as "reached the assistant".
    reached = {"detail": [{"type": "extra_forbidden", "loc": ["body", "pad"], "msg": "x"}]}
    assert smoke.assistant_validation(json.dumps(reached).encode()) == "extra_forbidden"
    too_long = {"detail": [{"type": "string_too_long", "loc": ["body", "message"]}]}
    for other in (b"", b"Request Entity Too Large", json.dumps(too_long).encode(), b"{}"):
        assert smoke.assistant_validation(other) is None
    with pytest.raises(RuntimeError):
        smoke.padded_body(10)


def caddy_without_assistant(text: str) -> str:
    text = re.sub(r"    handle @assistant \{.*?\n    \}\n", "", text, count=1, flags=re.S)
    text = re.sub(r"    handle_errors .*?\n    \}\n", "", text, count=1, flags=re.S)
    return "\n".join(line for line in text.splitlines() if line.strip())


def test_the_candidate_caddyfile_changes_only_the_assistant_route() -> None:
    assert caddy_without_assistant(CADDYFILE.read_text("utf-8")) == caddy_without_assistant(
        SHARED_CADDYFILE.read_text("utf-8")
    )


def test_the_candidate_caddyfile_authenticates_before_proxying() -> None:
    text = CADDYFILE.read_text("utf-8")
    assert text.index("forward_auth") < text.index("uri strip_prefix /api")
    assert text.index("uri strip_prefix /api") < text.index("reverse_proxy clm-assistant-proxy")
    assert "flush_interval -1" in text
    assert "/internal" not in text


def test_the_compose_overlay_publishes_nothing_and_has_no_route_out() -> None:
    text = COMPOSE.read_text("utf-8")
    assert "ports:" not in text
    assert "default:" not in text
    assert "extra_hosts" not in text
    for setting in ("read_only: true", "cap_drop: [ALL]", "mem_limit:", "cpus:", "pids_limit:"):
        assert setting in text
    assert "OPENROUTER" not in text
    assert "ANTHROPIC" not in text


def test_the_image_ignore_file_keeps_secrets_and_data_out() -> None:
    text = (ASSISTANT_DIR / "deploy" / "assistant.Dockerfile.dockerignore").read_text("utf-8")
    lines = text.splitlines()
    assert lines[0] == "**"
    assert not any(line.startswith("!") and "data" in line for line in lines)
    for rule in ("**/.env*", "**/*.pem", "**/*.key", "**/*.sqlite3"):
        assert rule in lines


def test_hosting_imports_no_evaluation_or_provider_sdk() -> None:
    code = (
        "import sys; import assistant_hosting.profile, assistant_hosting.guard;"
        "bad=[m for m in sys.modules if m.startswith('assistant_eval') or m=='anthropic'];"
        "sys.exit(1 if bad else 0)"
    )
    subprocess.run([sys.executable, "-c", code], cwd=ASSISTANT_DIR, check=True, timeout=120)
