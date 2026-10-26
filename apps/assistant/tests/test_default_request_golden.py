"""The default profile still sends exactly what it sent before Phase A2 (T3-01, T3-02).

The expected requests were captured from the unchanged adapter at the A2 base commit
(``769c149``) with these fixed messages: URL, every header and the body bytes.
"""

import asyncio
import functools
import hashlib
from collections.abc import Iterator, Mapping
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from ai_assistant.config import AiAssistantSettings
from ai_assistant.llm import OpenAICompatibleChatModel
from ai_assistant.main import create_app
from ai_assistant.model_factory import build_chat_model
from tests.remote_fixtures import SENTINEL_KEY, Chunks
from tests.test_ai_assistant import CASE_ID, ORIGIN, FakeBackend

MESSAGES = [
    {"role": "system", "content": "Rules: choose allowed lines only."},
    {
        "role": "system",
        "content": 'CASE FACTS {"stage": "review", "name": "Synth\u00e9tique Pte"}',
    },
    {"role": "user", "content": "What is blocking this case? \u2014 \u4f60\u597d"},
]
URL = "http://127.0.0.1:11434/v1/chat/completions"
PREFIX = (
    '{"model":"ministral-3:8b","messages":[{"role":"system","content":"Rules: choose allowed'
    ' lines only."},{"role":"system","content":"CASE FACTS {\\"stage\\": \\"review\\",'
    ' \\"name\\": \\"Synth\u00e9tique Pte\\"}"},{"role":"user","content":"What is blocking'
    ' this case? \u2014 \u4f60\u597d"}],"temperature":0.2,'
)
GOLDEN = {
    "complete": (
        PREFIX + '"max_tokens":600,"stream":false}',
        "b6f28b18dea5c41501b7c153fc8508dc9fb733e0bbbb48c3c4f0b11addb7e363",
        "gzip, deflate",
    ),
    "stream": (
        PREFIX + '"max_tokens":600,"stream":true}',
        "5c6383cb05688b0b7cd48313ad6c993afbf8ade67f4bf06948a31b5fdc29ea60",
        "identity",
    ),
    "warm": (
        PREFIX + '"max_tokens":1,"stream":false}',
        "acef2cd9f7e98ebb62f541225507a1e0a2c41d9bc1b65ad7155bf31c9a1370d1",
        "gzip, deflate",
    ),
}


def _headers(body: bytes, encoding: str) -> list[tuple[str, str]]:
    return [
        ("accept", "*/*"),
        ("accept-encoding", encoding),
        ("authorization", "Bearer ollama"),
        ("connection", "keep-alive"),
        ("content-length", str(len(body))),
        ("content-type", "application/json"),
        ("host", "127.0.0.1:11434"),
        ("user-agent", "python-httpx/0.28.1"),
    ]


class NoRemoteKeyAccess(Mapping[str, str]):
    """An environment mapping that fails the test if anything reads it."""

    def __getitem__(self, key: str) -> str:
        raise AssertionError("the default profile read the environment")

    def __iter__(self) -> Iterator[str]:
        raise AssertionError("the default profile read the environment")

    def __len__(self) -> int:
        raise AssertionError("the default profile read the environment")


def _default_settings() -> AiAssistantSettings:
    return AiAssistantSettings(_env_file=None, llm_enabled=True)  # type: ignore[call-arg]


def _captured() -> dict[str, httpx.Request]:
    captured: dict[str, httpx.Request] = {}

    def sync(request: httpx.Request) -> httpx.Response:
        key = "warm" if b'"max_tokens":1,' in request.content else "complete"
        captured[key] = request
        body = {"choices": [{"message": {"content": "x"}, "finish_reason": "stop"}]}
        return httpx.Response(200, json=body)

    def asynchronous(request: httpx.Request) -> httpx.Response:
        captured["stream"] = request
        sse = b'data: {"choices":[{"delta":{"content":"x"},"finish_reason":"stop"}]}\n\n'
        return httpx.Response(200, stream=Chunks([sse, b"data: [DONE]\n\n"]))

    def build(transport: httpx.MockTransport) -> Any:
        adapter = functools.partial(OpenAICompatibleChatModel, transport=transport)
        return build_chat_model(
            _default_settings(), local_adapter=adapter, environ=NoRemoteKeyAccess()
        )

    build(httpx.MockTransport(sync)).complete(MESSAGES)
    build(httpx.MockTransport(sync)).warm(MESSAGES)

    async def stream() -> None:
        async for _ in build(httpx.MockTransport(asynchronous)).stream(MESSAGES):
            pass

    asyncio.run(stream())
    return captured


@pytest.mark.parametrize("call", ["complete", "stream", "warm"])
def test_default_requests_are_byte_identical_to_the_base(call: str) -> None:
    request = _captured()[call]
    body, digest, encoding = GOLDEN[call]

    assert request.method == "POST"
    assert str(request.url) == URL
    assert request.content == body.encode("utf-8")
    assert hashlib.sha256(request.content).hexdigest() == digest
    assert sorted((key.lower(), value) for key, value in request.headers.items()) == _headers(
        request.content, encoding
    )


def test_the_default_profile_builds_todays_adapter_without_reading_the_environment() -> None:
    model = build_chat_model(_default_settings(), environ=NoRemoteKeyAccess())

    assert type(model) is OpenAICompatibleChatModel
    assert model.name == "ministral-3:8b"
    assert vars(model) == vars(
        OpenAICompatibleChatModel(
            base_url="http://127.0.0.1:11434/v1",
            model="ministral-3:8b",
            credential="ollama",
            timeout_seconds=90.0,
            temperature=0.2,
            max_answer_tokens=600,
        )
    )


def test_the_service_composes_the_default_adapter_with_the_same_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ai_assistant.main as main_module

    calls: list[dict[str, Any]] = []
    real = OpenAICompatibleChatModel

    def spy(**kwargs: Any) -> OpenAICompatibleChatModel:
        calls.append(kwargs)
        return real(**kwargs)

    monkeypatch.setattr(main_module, "OpenAICompatibleChatModel", spy)
    create_app(_default_settings(), clm_transport=httpx.MockTransport(FakeBackend().handler))

    assert calls == [
        {
            "base_url": "http://127.0.0.1:11434/v1",
            "model": "ministral-3:8b",
            "credential": "ollama",
            "timeout_seconds": 90.0,
            "temperature": 0.2,
            "max_answer_tokens": 600,
        }
    ]


def test_a_remote_key_in_the_environment_never_reaches_the_local_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ai_assistant.main as main_module

    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        body = {"choices": [{"message": {"content": "x"}, "finish_reason": "stop"}]}
        return httpx.Response(200, json=body)

    monkeypatch.setenv("OPENROUTER_API_KEY", SENTINEL_KEY)
    monkeypatch.setattr(
        main_module,
        "OpenAICompatibleChatModel",
        functools.partial(OpenAICompatibleChatModel, transport=httpx.MockTransport(handler)),
    )
    app = create_app(_default_settings(), clm_transport=httpx.MockTransport(FakeBackend().handler))
    client = TestClient(app, headers={"Origin": ORIGIN})
    client.cookies.set("clm_session", "valid-session")
    client.post(f"/assistant/cases/{CASE_ID}/chat", json={"message": "What should I do next?"})

    assert len(seen) == 1
    assert seen[0].headers["authorization"] == "Bearer ollama"
    assert SENTINEL_KEY.encode() not in seen[0].content
    assert all(SENTINEL_KEY not in value for value in seen[0].headers.values())
