"""Minimal client for any OpenAI-compatible chat API (Ollama, LM Studio, vLLM, cloud)."""

import json
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Protocol

import httpx


class LlmUnavailableError(Exception):
    """The model could not answer (not running, not installed, too slow, bad reply)."""


@dataclass(frozen=True)
class ModelAnswer:
    text: str
    # True when the model stopped because it reached the answer-length safety limit.
    cut_short: bool = False


@dataclass(frozen=True)
class Piece:
    """Part of a streamed answer. The last piece of a stream says whether it was cut short."""

    text: str = ""
    cut_short: bool = False


class ChatModel(Protocol):
    @property
    def name(self) -> str: ...

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer: ...

    def stream(self, messages: list[dict[str, str]]) -> Iterator[Piece]: ...

    def warm(self, messages: list[dict[str, str]]) -> None: ...


class OpenAICompatibleChatModel:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        credential: str,
        timeout_seconds: float,
        temperature: float,
        max_answer_tokens: int = 600,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._model = model
        self._credential = credential
        self._timeout = timeout_seconds
        self._temperature = temperature
        self._max_answer_tokens = max_answer_tokens
        self._transport = transport

    @property
    def name(self) -> str:
        return self._model

    def _payload(
        self, messages: list[dict[str, str]], *, stream: bool, max_tokens: int
    ) -> dict[str, Any]:
        return {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=self._timeout, transport=self._transport)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._credential}"}

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        payload = self._payload(messages, stream=False, max_tokens=self._max_answer_tokens)
        try:
            with self._client() as client:
                response = client.post(self._url, json=payload, headers=self._headers())
        except httpx.HTTPError:
            raise LlmUnavailableError("model unreachable") from None
        if response.status_code != 200:
            raise LlmUnavailableError(f"model returned {response.status_code}")
        try:
            choice = response.json()["choices"][0]
            content = choice["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise LlmUnavailableError("unreadable model reply") from None
        if not isinstance(content, str) or not content.strip():
            raise LlmUnavailableError("empty model reply")
        return ModelAnswer(content.strip(), cut_short=choice.get("finish_reason") == "length")

    def stream(self, messages: list[dict[str, str]]) -> Iterator[Piece]:
        """Yield the answer as the model writes it (server-sent events, OpenAI format).

        The timeout is the longest wait for the next piece, and also for the whole answer.
        """

        payload = self._payload(messages, stream=True, max_tokens=self._max_answer_tokens)
        deadline = time.monotonic() + self._timeout
        cut_short = False
        try:
            with (
                self._client() as client,
                client.stream("POST", self._url, json=payload, headers=self._headers()) as reply,
            ):
                if reply.status_code != 200:
                    raise LlmUnavailableError(f"model returned {reply.status_code}")
                for line in reply.iter_lines():
                    if time.monotonic() > deadline:
                        raise LlmUnavailableError("model too slow")
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if data == "[DONE]":
                        break
                    try:
                        choice = json.loads(data)["choices"][0]
                        delta = choice.get("delta") or {}
                    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
                        raise LlmUnavailableError("unreadable model reply") from None
                    piece = delta.get("content")
                    if isinstance(piece, str) and piece:
                        yield Piece(piece)
                    if choice.get("finish_reason") == "length":
                        cut_short = True
                yield Piece(cut_short=cut_short)
        except httpx.HTTPError:
            raise LlmUnavailableError("model unreachable") from None

    def warm(self, messages: list[dict[str, str]]) -> None:
        """Have the model read the fixed start of the prompt now, so a later question that
        starts the same way only needs the new part read (the server caches what it read).
        Best effort: any failure is ignored."""

        payload = self._payload(messages, stream=False, max_tokens=1)
        try:
            with self._client() as client:
                client.post(self._url, json=payload, headers=self._headers())
        except httpx.HTTPError:
            return
