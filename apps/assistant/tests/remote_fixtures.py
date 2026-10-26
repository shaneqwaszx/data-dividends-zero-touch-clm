"""Synthetic fixtures for the dormant remote profile (Phase A2, D-091 proposed).

Nothing here is an approved endpoint, a real price, a real provider or a real key. The
endpoint slug is fictional, prices are test values and the key is a sentinel that tests
search for in every output.
"""

import json
from collections.abc import AsyncIterator, Callable, Iterable
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from ai_assistant.budget import BudgetLedger
from ai_assistant.config import AiAssistantSettings
from ai_assistant.model_factory import resolve_remote_credential
from ai_assistant.model_profiles import (
    APPROVED_PROFILES,
    OPENROUTER_MODEL_ID,
    OPENROUTER_PROFILE,
    OPENROUTER_PROFILE_ID,
    ApprovedEndpoint,
    ModelProfile,
)
from ai_assistant.openrouter import OpenRouterChatModel

SENTINEL_KEY = "test_sentinel_remote_key_7f3a91c2"
ENVIRON = {"OPENROUTER_API_KEY": SENTINEL_KEY}
URL = "https://openrouter.ai/api/v1/chat/completions"
ENDPOINT = ApprovedEndpoint(
    slug="fictional-provider/fp8",
    prompt_price_per_m=Decimal("0.15"),
    completion_price_per_m=Decimal("0.60"),
    request_price=Decimal("0"),
    max_completion_tokens=117964,
    max_tokens_includes_reasoning=False,
    slug_unique_for_model=True,
    evidence_date=date(2026, 10, 26),
    quantization="fp8",
    provider_name="Fictional Provider",
)
TEST_PROFILE = replace(OPENROUTER_PROFILE, endpoints=(ENDPOINT,))
TEST_REGISTRY: dict[str, ModelProfile] = {
    **APPROVED_PROFILES,
    OPENROUTER_PROFILE_ID: TEST_PROFILE,
}
MESSAGES = [
    {"role": "system", "content": "Rules."},
    {"role": "user", "content": "What is blocking this case?"},
]
USAGE = {
    "prompt_tokens": 3000,
    "completion_tokens": 450,
    "total_tokens": 3450,
    "cost": 0.00072,
    "prompt_tokens_details": {"cached_tokens": 0},
    "completion_tokens_details": {"reasoning_tokens": 300},
}


def remote_settings(**changes: Any) -> AiAssistantSettings:
    values: dict[str, Any] = {
        "llm_enabled": True,
        "llm_profile": OPENROUTER_PROFILE_ID,
        "remote_inference_decision": "D-091",
        "openrouter_endpoint": ENDPOINT.slug,
        "llm_reasoning_effort": "low",
        "llm_reasoning_allowance_tokens": 1400,
    }
    values.update(changes)
    return AiAssistantSettings(_env_file=None, **values)  # type: ignore[call-arg]


def adapter(transport: httpx.MockTransport, **changes: Any) -> OpenRouterChatModel:
    """The remote adapter alone (no budget guard), built from the test settings."""

    settings = remote_settings(**changes)
    return OpenRouterChatModel(
        endpoint=ENDPOINT,
        credential=resolve_remote_credential(ENVIRON),
        timeout_seconds=settings.llm_timeout_seconds,
        temperature=settings.llm_temperature,
        answer_tokens=settings.llm_max_answer_tokens,
        reasoning_effort=settings.llm_reasoning_effort,
        reasoning_allowance_tokens=settings.llm_reasoning_allowance_tokens,
        max_prompt_bytes=settings.remote_max_prompt_bytes,
        transport=transport,
    )


def new_ledger(
    path: Path, *, cap: int = 7_000_000, opening: int = 0, clock: Callable[[], float] | None = None
) -> Path:
    """A fresh synthetic ledger file (test cap and opening usage, never a real budget)."""

    extra: dict[str, Any] = {} if clock is None else {"clock": clock}
    BudgetLedger.initialise(
        path, cap_micro_usd=cap, opening_usage_micro_usd=opening, key_alias="key-01", **extra
    )
    return path


class Chunks(httpx.AsyncByteStream):
    def __init__(self, chunks: Iterable[bytes]) -> None:
        self._chunks = list(chunks)

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk


def frame(event: object) -> bytes:
    return b"data: " + json.dumps(event).encode() + b"\n\n"


def chunk(content: str | None = None, finish: str | None = None, **extra: Any) -> bytes:
    delta: dict[str, Any] = {} if content is None else {"content": content}
    event: dict[str, Any] = {
        "id": "gen-1761-test",
        "model": OPENROUTER_MODEL_ID,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }
    event.update(extra)
    return frame(event)


def sse(*frames: bytes, done: bool = True) -> list[bytes]:
    body = [b": OPENROUTER PROCESSING\n\n", *frames]
    if done:
        body.append(b"data: [DONE]\n\n")
    return body


def happy_stream(text: str = "Line one\n", usage: object = USAGE) -> list[bytes]:
    return sse(chunk(text), chunk("", "stop"), chunk(None, "stop", usage=usage))


class Provider:
    """A mock OpenRouter: records every request and answers from a factory."""

    def __init__(self, respond: Callable[[httpx.Request], httpx.Response]) -> None:
        self.requests: list[httpx.Request] = []
        self._respond = respond

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._respond(request)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)


def streaming(chunks: Iterable[bytes], status: int = 200, **headers: str) -> Provider:
    return Provider(
        lambda _: httpx.Response(
            status,
            stream=Chunks(chunks),
            headers={"content-type": "text/event-stream", **headers},
        )
    )


def answering(body: object, status: int = 200) -> Provider:
    return Provider(lambda _: httpx.Response(status, json=body))


def completion(content: str = "Line one", finish: str = "stop", **extra: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "id": "gen-1761-test",
        "model": OPENROUTER_MODEL_ID,
        "choices": [{"message": {"content": content}, "finish_reason": finish}],
        "usage": USAGE,
    }
    body.update(extra)
    return body
