"""Minimal client for any OpenAI-compatible chat API (Ollama, LM Studio, vLLM, cloud)."""

import json
import time
from collections.abc import AsyncGenerator, AsyncIterator
from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any, Protocol
from urllib.parse import urlsplit

import anyio
import httpx


def is_local_model_url(url: str) -> bool:
    """Allow implicit case-data warm-up only to unambiguous literal loopback URLs.

    DNS names (including localhost), encoded/scoped hosts and URL routing metadata
    are not proof of a local model. This is a fixed restriction, not a cloud opt-in.
    """

    if any(ord(char) <= 32 or ord(char) >= 127 for char in url) or any(
        char in url for char in ("\\", "?", "#")
    ):
        return False
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or "%" in parsed.netloc
            or parsed.netloc.endswith(":")
            or (parsed.port is not None and not 1 <= parsed.port <= 65535)
        ):
            return False
        host = parsed.hostname or ""
        authority = f"[{host}]" if ":" in host else host
        if parsed.port is not None:
            authority += f":{parsed.port}"
        if parsed.netloc != authority:
            return False
        address = ip_address(host)
        return address.is_loopback and (address.version == 4 or address.compressed == "::1")
    except ValueError:
        return False


MAX_SSE_FRAME_BYTES = 64 * 1024
MAX_STREAM_BYTES = 1024 * 1024


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

    def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Piece, None]: ...

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

    def _client(self, *, trust_env: bool = True) -> httpx.Client:
        return httpx.Client(
            timeout=self._timeout,
            transport=self._transport,
            trust_env=trust_env,
            follow_redirects=False,
        )

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._credential}"}

    @staticmethod
    def _choice(event: Any) -> dict[str, Any]:
        if not isinstance(event, dict):
            raise LlmUnavailableError("unreadable model reply")
        choices = event.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise LlmUnavailableError("unreadable model reply")
        choice = choices[0]
        if not isinstance(choice, dict):
            raise LlmUnavailableError("unreadable model reply")
        return choice

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
            choice = self._choice(response.json())
            message = choice.get("message")
            if not isinstance(message, dict):
                raise LlmUnavailableError("unreadable model reply")
            content = message.get("content")
        except (ValueError, KeyError, IndexError, TypeError):
            raise LlmUnavailableError("unreadable model reply") from None
        if not isinstance(content, str) or not content.strip():
            raise LlmUnavailableError("empty model reply")
        return ModelAnswer(content.strip(), cut_short=choice.get("finish_reason") == "length")

    @staticmethod
    async def _sse_frames(reply: httpx.Response, deadline: float) -> AsyncIterator[str]:
        """Bound bytes before decoding/framing; accept LF, CRLF and CR across reads."""
        total = 0
        frame_size = 0
        line = bytearray()
        data: list[str] = []
        skip_lf = False
        first_line = True
        chunks = reply.aiter_raw()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise LlmUnavailableError("model too slow")
            try:
                with anyio.fail_after(remaining):
                    chunk = await anext(chunks)
            except StopAsyncIteration:
                return  # EOF never supplies a missing SSE event terminator.
            total += len(chunk)
            if total > MAX_STREAM_BYTES:
                raise LlmUnavailableError("model response limit exceeded")
            for byte in chunk:
                frame_size += 1
                if frame_size > MAX_SSE_FRAME_BYTES:
                    raise LlmUnavailableError("model frame limit exceeded")
                if skip_lf and byte == 10:
                    skip_lf = False
                    continue
                skip_lf = byte == 13
                if byte not in (10, 13):
                    line.append(byte)
                    continue
                if time.monotonic() >= deadline:
                    raise LlmUnavailableError("model too slow")
                decoded = line.decode("utf-8", errors="strict")
                line.clear()
                if first_line:
                    decoded = decoded.removeprefix("\ufeff")
                    first_line = False
                if not decoded:
                    frame_size = 0
                    if data:
                        yield "\n".join(data)
                        data.clear()
                elif decoded.startswith("data:"):
                    value = decoded[5:]
                    data.append(value[1:] if value.startswith(" ") else value)

    async def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Piece, None]:
        """Cancellable raw SSE reads, with independent frame, total and elapsed bounds."""
        payload = self._payload(messages, stream=True, max_tokens=self._max_answer_tokens)
        cut_short = False
        completed = False
        if self._transport is not None and not isinstance(
            self._transport, httpx.AsyncBaseTransport
        ):
            raise LlmUnavailableError("unsupported model transport")
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                transport=self._transport,
                follow_redirects=False,
            ) as client:
                # Include connection, request write, response headers and every body read.
                deadline = time.monotonic() + self._timeout
                request = client.build_request(
                    "POST",
                    self._url,
                    json=payload,
                    headers={**self._headers(), "Accept-Encoding": "identity"},
                )
                with anyio.fail_after(max(0.0, deadline - time.monotonic())):
                    reply = await client.send(request, stream=True)
                try:
                    if reply.status_code != 200:
                        raise LlmUnavailableError(f"model returned {reply.status_code}")
                    if reply.headers.get("content-encoding", "identity").lower() != "identity":
                        raise LlmUnavailableError("unsupported model encoding")
                    async for data in self._sse_frames(reply, deadline):
                        if time.monotonic() >= deadline:
                            raise LlmUnavailableError("model too slow")
                        if data.strip() == "[DONE]":
                            completed = True
                            break
                        try:
                            event = json.loads(data)
                        except (ValueError, RecursionError):
                            raise LlmUnavailableError("unreadable model reply") from None
                        choice = self._choice(event)
                        delta = choice.get("delta")
                        if not isinstance(delta, dict):
                            raise LlmUnavailableError("unreadable model reply")
                        piece = delta.get("content")
                        if piece is not None and not isinstance(piece, str):
                            raise LlmUnavailableError("unreadable model reply")
                        finish = choice.get("finish_reason")
                        if finish not in (None, "stop", "length"):
                            raise LlmUnavailableError("unsupported model completion")
                        if piece:
                            piece.encode("utf-8", errors="strict")
                            yield Piece(piece)
                        if finish is not None:
                            completed = True
                            cut_short = finish == "length"
                            break
                    if not completed:
                        raise LlmUnavailableError("model stream ended early")
                finally:
                    # ASGI disconnect cancellation must also release the model connection.
                    with anyio.CancelScope(shield=True):
                        await reply.aclose()
            yield Piece(cut_short=cut_short)
        except TimeoutError:
            raise LlmUnavailableError("model too slow") from None
        except UnicodeError:
            raise LlmUnavailableError("unreadable model reply") from None
        except httpx.HTTPError:
            raise LlmUnavailableError("model unreachable") from None

    def warm(self, messages: list[dict[str, str]]) -> None:
        """Have the model read the fixed start of the prompt now, so a later question that
        starts the same way only needs the new part read (the server caches what it read).
        Only literal loopback destinations are eligible; a warm-up flag never grants
        remote data-handling authority. Best effort: transport failures are ignored."""

        # Check the actual transport destination even when callers bypass /brief or
        # supply settings that disagree with this adapter. Never proxy or redirect it.
        if not is_local_model_url(self._url):
            return
        payload = self._payload(messages, stream=False, max_tokens=1)
        try:
            with self._client(trust_env=False) as client:
                client.post(self._url, json=payload, headers=self._headers())
        except httpx.HTTPError:
            return
