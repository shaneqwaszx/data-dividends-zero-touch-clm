"""Minimal client for any OpenAI-compatible chat API (Ollama, LM Studio, vLLM, cloud)."""

from typing import Any, Protocol

import httpx


class LlmUnavailableError(Exception):
    """The model could not answer (not running, not installed, too slow, bad reply)."""


class ChatModel(Protocol):
    @property
    def name(self) -> str: ...

    def complete(self, messages: list[dict[str, str]]) -> str: ...


class OpenAICompatibleChatModel:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        credential: str,
        timeout_seconds: float,
        temperature: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._model = model
        self._credential = credential
        self._timeout = timeout_seconds
        self._temperature = temperature
        self._transport = transport

    @property
    def name(self) -> str:
        return self._model

    def complete(self, messages: list[dict[str, str]]) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "stream": False,
        }
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                response = client.post(
                    self._url,
                    json=payload,
                    headers={"Authorization": f"Bearer {self._credential}"},
                )
        except httpx.HTTPError:
            raise LlmUnavailableError("model unreachable") from None
        if response.status_code != 200:
            raise LlmUnavailableError(f"model returned {response.status_code}")
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise LlmUnavailableError("unreadable model reply") from None
        if not isinstance(content, str) or not content.strip():
            raise LlmUnavailableError("empty model reply")
        return content.strip()
