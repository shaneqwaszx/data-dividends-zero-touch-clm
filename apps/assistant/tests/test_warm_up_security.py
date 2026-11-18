"""P1 regressions: synthetic case facts and captured transports; no model network."""

import json
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from ai_assistant.config import AiAssistantSettings
from ai_assistant.llm import OpenAICompatibleChatModel
from ai_assistant.main import create_app
from tests.test_ai_assistant import CASE_ID, ORIGIN, FakeBackend, FakeModel
from tests.test_streaming_resources import Bytes

MESSAGES = [{"role": "system", "content": "CASE FACTS: synthetic document value PRIVATE_TEST"}]
BRIEF = f"/assistant/cases/{CASE_ID}/brief"
REMOTE = "https://model.synthetic.invalid/v1"


def model(url: str, requests: list[httpx.Request]) -> OpenAICompatibleChatModel:
    def capture(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        payload = json.loads(request.content)
        if payload.get("stream"):
            chunk = {"choices": [{"delta": {"content": FakeModel.ANSWER}, "finish_reason": "stop"}]}
            return httpx.Response(
                200, stream=Bytes([("data: " + json.dumps(chunk) + "\n\n").encode()])
            )
        return httpx.Response(200, json={"choices": [{"message": {"content": FakeModel.ANSWER}}]})

    return OpenAICompatibleChatModel(
        base_url=url,
        model="synthetic",
        credential="synthetic-test-key",
        timeout_seconds=1,
        temperature=0,
        transport=httpx.MockTransport(capture),
    )


def client(url: str, warm: bool, requests: list[httpx.Request]) -> tuple[TestClient, FakeBackend]:
    settings = AiAssistantSettings(
        _env_file=None, llm_enabled=True, llm_base_url=url, llm_warm_up=warm
    )
    backend = FakeBackend()
    app = create_app(
        settings,
        clm_transport=httpx.MockTransport(backend.handler),
        chat_model=model(url, requests),
    )
    browser = TestClient(app, headers={"Origin": ORIGIN})
    browser.cookies.set("clm_session", "valid-session")
    return browser, backend


@pytest.mark.parametrize(
    "url",
    [
        REMOTE,
        "http://192.168.1.1/v1",
        "http://0.0.0.0:11434/v1",
        "http://[::]/v1",
        "http://localhost/v1",
        "http://localhost.example/v1",
        "http://127.0.0.1.evil.invalid/v1",
        "http://127.0.0.1.nip.io/v1",
        "http://127.1/v1",
        "http://2130706433/v1",
        "http://0177.0.0.1/v1",
        "http://0x7f000001/v1",
        "http://[::ffff:127.0.0.1]/v1",
        "http://[::1%25lo0]/v1",
        "http://[::1]evil.invalid/v1",
        "http://[::1].evil.invalid/v1",
        "http://[::1]:80:90/v1",
        "http://127.0.0.1:0011434/v1",
        "http://user@127.0.0.1/v1",
        "http://127.0.0.1@remote.invalid/v1",
        "http://127.0.0.1:0/v1",
        "http://127.0.0.1:65536/v1",
        "http://127.0.0.1:/v1",
        "http://127.0.0.1/v1?relay=remote",
        "http://127.0.0.1/v1#fragment",
        "http://127%2e0%2e0%2e1/v1",
        " http://127.0.0.1/v1",
        "http://127.0.0.1/va\tlue",
        "http://127.0.0.1\\@remote.invalid/v1",
        "ftp://127.0.0.1/v1",
        "//127.0.0.1/v1",
        "",
        "not a URL",
        "http://[::1",
        "http:///v1",
    ],
)
def test_warm_transport_rejects_remote_or_ambiguous_destinations(url: str) -> None:
    requests: list[httpx.Request] = []
    model(url, requests).warm(MESSAGES)
    assert requests == []


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:11434/v1",
        "http://127.0.0.2/v1/",
        "https://127.0.0.1/v1",
        "http://[::1]:11434/v1",
        "https://[0:0:0:0:0:0:0:1]/v1",
    ],
)
def test_warm_transport_preserves_literal_local_models(url: str) -> None:
    requests: list[httpx.Request] = []
    model(url, requests).warm(MESSAGES)
    assert len(requests) == 1
    assert requests[0].method == "POST"
    payload = json.loads(requests[0].content)
    assert payload["messages"] == MESSAGES
    assert payload["max_tokens"] == 1 and payload["stream"] is False


@pytest.mark.parametrize(
    ("url", "warm", "expected"),
    [
        ("http://127.0.0.1:11434/v1", True, 1),
        ("http://[::1]:11434/v1", True, 1),
        ("http://127.0.0.1:11434/v1", False, 0),
        (REMOTE, True, 0),
        (REMOTE, False, 0),
        ("http://localhost:11434/v1", True, 0),
        ("not a URL", True, 0),
    ],
)
def test_panel_brief_has_no_untrusted_automatic_model_post(
    url: str, warm: bool, expected: int
) -> None:
    requests: list[httpx.Request] = []
    browser, backend = client(url, warm, requests)
    assert requests == []
    assert browser.get("/assistant/health").status_code == 200
    for _ in range(2):
        response = browser.get(BRIEF)
        assert response.status_code == 200
        assert response.json()["company"] == "GARDEN BUSINESS"
    if requests:
        payload = json.loads(requests[0].content)
        assert "11111999A" in payload["messages"][1]["content"]
        assert "18 GARDEN WALK" in payload["messages"][1]["content"]
    assert len(requests) == expected
    assert {request.method for request in backend.requests} == {"GET"}
    if expected:
        assert "11111999A" in json.loads(requests[0].content)["messages"][1]["content"]


def test_warm_guard_uses_transport_destination_even_if_settings_claim_local() -> None:
    requests: list[httpx.Request] = []
    settings = AiAssistantSettings(_env_file=None, llm_enabled=True, llm_warm_up=True)
    app = create_app(
        settings,
        clm_transport=httpx.MockTransport(FakeBackend().handler),
        chat_model=model(REMOTE, requests),
    )
    browser = TestClient(app, headers={"Origin": ORIGIN})
    browser.cookies.set("clm_session", "valid-session")
    assert browser.get(BRIEF).status_code == 200
    assert requests == []


def test_warm_client_cannot_use_environment_proxy_or_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_client = httpx.Client
    requests: list[httpx.Request] = []
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.synthetic.invalid:8080")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.synthetic.invalid:8080")
    monkeypatch.setenv("ALL_PROXY", "http://proxy.synthetic.invalid:8080")
    monkeypatch.setenv("NO_PROXY", "")

    def inspect_client(**kwargs: Any) -> httpx.Client:
        assert kwargs.get("trust_env") is False
        assert kwargs.get("follow_redirects", False) is False
        return real_client(**kwargs)

    monkeypatch.setattr(httpx, "Client", inspect_client)
    model("http://127.0.0.1/v1", requests).warm(MESSAGES)
    assert len(requests) == 1


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_local_warm_never_follows_provider_redirects(status: int) -> None:
    requests: list[httpx.Request] = []

    def redirect(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status, headers={"Location": REMOTE + "/chat/completions"})

    provider = OpenAICompatibleChatModel(
        base_url="http://127.0.0.1/v1",
        model="synthetic",
        credential="test",
        timeout_seconds=1,
        temperature=0,
        transport=httpx.MockTransport(redirect),
    )
    provider.warm(MESSAGES)
    assert len(requests) == 1 and requests[0].url.host == "127.0.0.1"


@pytest.mark.parametrize("streaming", [False, True])
def test_remote_explicit_question_remains_a_separate_boundary(streaming: bool) -> None:
    requests: list[httpx.Request] = []
    browser, _ = client(REMOTE, True, requests)
    assert browser.get(BRIEF).status_code == 200
    assert requests == []
    path = f"/assistant/cases/{CASE_ID}/chat" + ("/stream" if streaming else "")
    # D-142 R4: a supported intent; the remote model receives only its canonical question.
    reply = browser.post(path, json={"message": "Why is this case blocked?"})
    assert reply.status_code == 200
    body = json.loads(reply.text.splitlines()[-1]) if streaming else reply.json()
    # R4: the canonical topic's required lines come first, then the model's checked text.
    assert body["answered_by"] == "model" and body["answer"].endswith(FakeModel.ANSWER)
    assert len(requests) == 1
    # D-142: a model on a remote endpoint gets the case facts through the privacy boundary,
    # so the UEN leaves as a placeholder.
    facts = json.loads(requests[0].content)["messages"][1]["content"]
    assert "CASE FACTS" in facts and "11111999A" not in facts and "[ID-" in facts


def test_environment_flag_cannot_enable_remote_warm_up_in_normal_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ai_assistant.main as main_module

    requests: list[httpx.Request] = []
    real_model = OpenAICompatibleChatModel
    monkeypatch.setenv("AI_ASSISTANT_LLM_BASE_URL", REMOTE)
    monkeypatch.setenv("AI_ASSISTANT_LLM_WARM_UP", "true")
    monkeypatch.setenv("AI_ASSISTANT_LLM_ENABLED", "true")

    def captured_model(**kwargs: Any) -> OpenAICompatibleChatModel:
        def capture(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={})

        return real_model(**kwargs, transport=httpx.MockTransport(capture))

    monkeypatch.setattr(main_module, "OpenAICompatibleChatModel", captured_model)
    settings = AiAssistantSettings(_env_file=None)
    assert settings.llm_warm_up is True and settings.llm_base_url == REMOTE
    app = create_app(settings, clm_transport=httpx.MockTransport(FakeBackend().handler))
    browser = TestClient(app, headers={"Origin": ORIGIN})
    browser.cookies.set("clm_session", "valid-session")
    assert browser.get(BRIEF).status_code == 200
    assert requests == []


def test_remote_brief_skips_prompt_building_and_custom_model_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ai_assistant.main as main_module

    def forbidden_prompt(_: Any) -> list[dict[str, str]]:
        raise AssertionError("An untrusted warm-up must not build a case prompt")

    monkeypatch.setattr(main_module, "prefix_messages", forbidden_prompt)
    settings = AiAssistantSettings(_env_file=None, llm_base_url=REMOTE, llm_warm_up=True)
    fake = FakeModel()
    app = create_app(
        settings, clm_transport=httpx.MockTransport(FakeBackend().handler), chat_model=fake
    )
    browser = TestClient(app, headers={"Origin": ORIGIN})
    browser.cookies.set("clm_session", "valid-session")
    assert browser.get(BRIEF).status_code == 200
    assert fake.warmed == [] and fake.calls == []


@pytest.mark.parametrize(
    "path", [BRIEF, f"/assistant/cases/{CASE_ID}/chat", f"/assistant/cases/{CASE_ID}/chat/stream"]
)
@pytest.mark.parametrize(
    ("cookie", "case_status", "expected"),
    [
        (None, 200, 401),
        ("expired-session", 200, 401),
        ("valid-session", 404, 404),
    ],
)
def test_brief_and_chat_preserve_backend_access_before_model_calls(
    path: str,
    cookie: str | None,
    case_status: int,
    expected: int,
) -> None:
    requests: list[httpx.Request] = []
    settings = AiAssistantSettings(_env_file=None, llm_warm_up=True)
    backend = FakeBackend(case_status=case_status)
    app = create_app(
        settings,
        clm_transport=httpx.MockTransport(backend.handler),
        chat_model=model(settings.llm_base_url, requests),
    )
    browser = TestClient(app, headers={"Origin": ORIGIN})
    if cookie:
        browser.cookies.set("clm_session", cookie)
    reply = browser.get(path) if path == BRIEF else browser.post(path, json={"message": "Why?"})
    assert reply.status_code == expected
    assert requests == []
    assert all(request.method == "GET" for request in backend.requests)


def test_background_warm_up_logs_no_case_values_or_session_material(
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    caplog.set_level(logging.DEBUG)
    for url in ["http://127.0.0.1/v1", REMOTE]:
        requests: list[httpx.Request] = []
        browser, _ = client(url, True, requests)
        assert browser.get(BRIEF).status_code == 200
        for request in requests:
            assert "clm_session" not in str(request.headers)
            assert "valid-session" not in request.content.decode()
    for protected in [
        "GARDEN BUSINESS",
        "11111999A",
        "18 GARDEN WALK",
        "valid-session",
        "synthetic-test-key",
    ]:
        assert protected not in caplog.text


@pytest.mark.parametrize("streaming", [False, True])
def test_remote_model_unavailable_falls_back_after_safe_brief(streaming: bool) -> None:
    requests: list[httpx.Request] = []

    def unavailable(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        raise httpx.ConnectError("synthetic private diagnostic")

    provider = OpenAICompatibleChatModel(
        base_url=REMOTE,
        model="synthetic",
        credential="test",
        timeout_seconds=1,
        temperature=0,
        transport=httpx.MockTransport(unavailable),
    )
    settings = AiAssistantSettings(_env_file=None, llm_base_url=REMOTE, llm_warm_up=True)
    app = create_app(
        settings, clm_transport=httpx.MockTransport(FakeBackend().handler), chat_model=provider
    )
    browser = TestClient(app, headers={"Origin": ORIGIN})
    browser.cookies.set("clm_session", "valid-session")
    assert browser.get(BRIEF).status_code == 200 and requests == []
    path = f"/assistant/cases/{CASE_ID}/chat" + ("/stream" if streaming else "")
    # D-142 R4: a supported intent, so the remote endpoint is tried before the fallback.
    reply = browser.post(path, json={"message": "What is the next step?"})
    body = json.loads(reply.text.splitlines()[-1]) if streaming else reply.json()
    assert body["answered_by"] == "case_data"
    assert "model is not available" in body["notice"]
    assert "Keep registry value" in body["answer"]
    assert "private diagnostic" not in reply.text
    assert len(requests) == 1
