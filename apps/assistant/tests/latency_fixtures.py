"""A mock OpenRouter with scenario timing, for the offline latency benchmark
(scripts/benchmark_chat_latency.py). No network; delays are scenario inputs, never
measurements of the provider."""

import asyncio
import json
import threading
import time
from collections import defaultdict
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass

import httpx

from ai_assistant.model_profiles import OPENROUTER_MODEL_ID
from tests.remote_fixtures import chunk, completion
from tests.test_remote_test import _reply_lines

USAGE = {
    "prompt_tokens": 3000,
    "completion_tokens": 450,
    "total_tokens": 3450,
    "cost": 0.00072,
    "prompt_tokens_details": {"cached_tokens": 0},
    "completion_tokens_details": {"reasoning_tokens": 300},
}


@dataclass
class Provider:
    """What the mock OpenRouter does (all seconds)."""

    network: float = 0.05  # each preflight read and the request round trip
    prefill_per_kchar: float = 0.0  # extra time to first output per 1,000 prompt characters
    reasoning: float = 0.3  # hidden reasoning before the first content token
    tokens_per_second: float = 200.0  # visible output rate (about 4 characters a token)
    newline_pause: float = 0.0  # extra pause before each line break
    stall: float = 0.0  # no output at all for this long (a timeout when above the limit)
    metadata_lag: float = 0.0  # generation metadata published this long after the answer
    lines: int | None = None  # answer lines (None: what the prompt's topic offers)


class TimedOpenRouter:
    """The mock OpenRouter with scenario timing (async stream with real pauses)."""

    def __init__(self) -> None:
        self.provider = Provider()
        self.completed_at: list[float] = []
        self.marks: dict[str, list[float]] = defaultdict(list)
        self.lock = threading.Lock()

    def handler(self, request: httpx.Request) -> httpx.Response:
        p = self.provider
        path = request.url.path
        if path.endswith("/key"):
            time.sleep(p.network)
            data = {"limit": 1.0, "limit_reset": None, "limit_remaining": 1.0, "usage": 0}
            return httpx.Response(200, json={"data": data})
        if path.endswith("/generation"):
            time.sleep(p.network)
            with self.lock:
                done = self.completed_at[-1] if self.completed_at else None
            if done is None or time.monotonic() < done + p.metadata_lag:
                return httpx.Response(404, json={"error": {"message": "not found"}})
            data = {
                "id": "gen-1761-test",
                "model": OPENROUTER_MODEL_ID,
                "provider_name": "DeepInfra",
                "total_cost": 0.00072,
                "cancelled": False,
            }
            return httpx.Response(200, json={"data": data})
        body = json.loads(request.content)
        self.marks["provider_request"].append(time.monotonic())
        text = _reply_lines(body)
        if not body.get("stream"):  # the plain /chat path (the qualification's)
            with self.lock:
                self.completed_at.append(time.monotonic())
            return httpx.Response(200, json=completion(text.rstrip("\n")))
        if p.lines is not None:
            lines = [line for line in text.splitlines() if line.strip()]
            text = "\n".join((lines * p.lines)[: p.lines]) + "\n"
        chars = sum(len(str(m.get("content", ""))) for m in body["messages"])
        first_delay = p.network + p.prefill_per_kchar * chars / 1000 + p.reasoning + p.stall
        return httpx.Response(
            200,
            stream=_Timed(self, text, first_delay),
            headers={"content-type": "text/event-stream"},
        )

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)


class _Timed(httpx.AsyncByteStream):
    def __init__(self, owner: TimedOpenRouter, text: str, first_delay: float) -> None:
        self.owner, self.text, self.first_delay = owner, text, first_delay

    async def __aiter__(self) -> AsyncIterator[bytes]:
        p = self.owner.provider
        yield b": OPENROUTER PROCESSING\n\n"
        await asyncio.sleep(self.first_delay)
        first = True
        per_char = 1 / (p.tokens_per_second * 4)
        for piece in _pieces(self.text):
            if piece == "\n" and p.newline_pause:
                await asyncio.sleep(p.newline_pause)
            else:
                await asyncio.sleep(per_char * len(piece))
            if first:
                self.owner.marks["first_content"].append(time.monotonic())
                first = False
            yield chunk(piece)
        yield chunk("", "stop")
        with self.owner.lock:  # before the last frames: the reader stops at [DONE]
            self.owner.completed_at.append(time.monotonic())
        yield chunk(None, "stop", usage=USAGE)
        yield b"data: [DONE]\n\n"


def _pieces(text: str) -> Iterator[str]:
    """About one token per piece; a line break is its own piece."""

    for line in text.splitlines(keepends=True):
        body = line.rstrip("\n")
        for start in range(0, len(body), 4):
            yield body[start : start + 4]
        if line.endswith("\n"):
            yield "\n"
