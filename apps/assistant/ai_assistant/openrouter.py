"""Dormant OpenRouter adapter for one approved ``openai/gpt-oss-120b`` endpoint (D-091, proposed).

Phase A2 builds and tests this adapter offline only. It accepts no transport except an
in-memory ``httpx.MockTransport`` (not a subclass), so in this build it cannot open a network
connection, whatever is injected or configured. Sending a real request needs a reviewed
Phase B change and the owner's separate decisions.

What it sends (fixed, not configurable): one ``POST /chat/completions`` per question to
``https://openrouter.ai/api/v1``, the full endpoint slug in ``provider.order`` and
``provider.only`` with fallbacks off, ``require_parameters``, ``data_collection: deny``,
``zdr``, ``max_price`` from the endpoint record, ``reasoning.exclude`` and no attribution
headers, user or session identifiers, tools, plugins or files. No retries; ``warm`` sends
nothing. Proxies, ``.netrc`` and certificate environment overrides are ignored.

What it reads: content only before the first ``stop``/``length`` finish, then the stream to
``[DONE]`` for OpenRouter's usage chunk. Reasoning text is never yielded, stored or logged.
Errors become ``ModelCallError`` with a closed class; provider error text is never kept.
"""

import json
import re
import time
from collections.abc import AsyncGenerator
from dataclasses import replace
from decimal import Decimal
from typing import Any

import anyio
import httpx
from pydantic import SecretStr

from .llm import (
    MAX_STREAM_BYTES,
    LlmUnavailableError,
    ModelAnswer,
    ModelCallError,
    ModelUsage,
    OpenAICompatibleChatModel,
    Piece,
    message_bytes,
)
from .model_profiles import (
    MAX_REMOTE_TOKENS,
    MIN_REASONING_ALLOWANCE,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL_ID,
    OPENROUTER_PROFILE_ID,
    ApprovedEndpoint,
    ProfileConfigError,
)

MAX_ERROR_BODY_BYTES = 16 * 1024
GENERATION_REF = re.compile(r"[A-Za-z0-9_-]{1,80}")
_MAX_COUNT = 10**9
_MAX_COST = Decimal("1000")

_STATUS_CLASSES = {
    400: "bad_request",
    401: "auth",
    402: "payment",
    403: "forbidden",
    404: "not_allowed",
    408: "timeout",
    429: "rate_limited",
    500: "upstream",
    502: "upstream",
    503: "no_provider",
}
_FINISH_CLASSES = {"content_filter": "content_filter", "tool_calls": "protocol"}


def require_offline_transport(transport: object) -> httpx.MockTransport:
    """Phase A2 containment: only an in-memory mock transport, never a subclass of one,
    a real HTTP transport or a wrapper around one."""

    if type(transport) is not httpx.MockTransport:
        raise ProfileConfigError(
            "TRANSPORT_NOT_ALLOWED",
            "the remote profile accepts only an in-memory mock transport in this build",
        )
    return transport


def _reject_constant(name: str) -> Any:
    raise ValueError("non-finite number")


def _loads(text: str | bytes) -> Any:
    return json.loads(text, parse_float=Decimal, parse_constant=_reject_constant)


def _event(data: str) -> dict[str, Any] | None:
    """One SSE data frame as a JSON object, or None when it is not one."""

    try:
        event = _loads(data)
    except (ValueError, RecursionError):
        return None
    return event if isinstance(event, dict) else None


def _count(value: object) -> int | None:
    return value if type(value) is int and 0 <= value < _MAX_COUNT else None


def _cost(value: object) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, int | Decimal):
        return None
    cost = Decimal(value)
    return cost if cost.is_finite() and 0 <= cost <= _MAX_COST else None


def parse_usage(raw: object) -> ModelUsage:
    """Strict usage parsing. Counts and cost all valid, or the cost is dropped (unsettled)."""

    if not isinstance(raw, dict):
        return ModelUsage(anomalies=("usage_malformed",))
    prompt, completion = _count(raw.get("prompt_tokens")), _count(raw.get("completion_tokens"))
    prompt_details = raw.get("prompt_tokens_details")
    completion_details = raw.get("completion_tokens_details")
    cached = (
        _count(prompt_details.get("cached_tokens")) if isinstance(prompt_details, dict) else None
    )
    reasoning = (
        _count(completion_details.get("reasoning_tokens"))
        if isinstance(completion_details, dict)
        else None
    )
    cost = _cost(raw.get("cost"))
    if prompt is None or completion is None or cost is None:
        return ModelUsage(prompt, completion, reasoning, cached, None, None, ("usage_malformed",))
    return ModelUsage(prompt, completion, reasoning, cached, cost)


def _status_class(status: int, body: bytes) -> str:
    error_class = _STATUS_CLASSES.get(status, "upstream" if 500 <= status < 600 else "http_other")
    if status == 402:
        try:
            error = _loads(body).get("error")
            sources = [error.get("limit_source"), (error.get("metadata") or {}).get("limit_source")]
        except (ValueError, AttributeError, TypeError, RecursionError, UnicodeError):
            sources = []
        if "openrouter_key_limit" in sources:
            return "payment_key_limit"
    return error_class


def _read_class(error: BaseException) -> str:
    if isinstance(error, TimeoutError | httpx.TimeoutException):
        return "timeout"
    if isinstance(error, LlmUnavailableError) and "slow" in str(error):
        return "timeout"
    if isinstance(error, httpx.HTTPError):
        return "transport"
    return "protocol"


class OpenRouterChatModel:
    """The ``ChatModel`` for one approved OpenRouter endpoint (dormant in Phase A2)."""

    def __init__(
        self,
        *,
        endpoint: ApprovedEndpoint,
        credential: SecretStr,
        timeout_seconds: float,
        temperature: float,
        answer_tokens: int,
        reasoning_effort: str,
        reasoning_allowance_tokens: int,
        max_prompt_bytes: int,
        transport: object,
    ) -> None:
        self._transport = require_offline_transport(transport)
        max_tokens = answer_tokens + reasoning_allowance_tokens
        if reasoning_allowance_tokens < MIN_REASONING_ALLOWANCE or max_tokens > min(
            MAX_REMOTE_TOKENS, endpoint.max_completion_tokens
        ):
            raise ProfileConfigError(
                "MAX_TOKENS_TOO_LARGE", "remote max_tokens is outside the allowed bounds"
            )
        self._endpoint = endpoint
        self._credential = credential
        self._timeout = timeout_seconds
        self._temperature = temperature
        self._effort = reasoning_effort
        self._max_tokens = max_tokens
        self._max_prompt_bytes = max_prompt_bytes
        self._url = OPENROUTER_BASE_URL + "/chat/completions"

    def __repr__(self) -> str:
        slug = self._endpoint.slug
        return f"OpenRouterChatModel(model={OPENROUTER_MODEL_ID!r}, endpoint={slug!r})"

    @property
    def name(self) -> str:
        return OPENROUTER_MODEL_ID

    @property
    def profile_id(self) -> str:
        return OPENROUTER_PROFILE_ID

    @property
    def endpoint(self) -> ApprovedEndpoint:
        return self._endpoint

    @property
    def endpoint_slug(self) -> str:
        return self._endpoint.slug

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @property
    def timeout_seconds(self) -> float:
        return self._timeout

    def payload(self, messages: list[dict[str, str]], *, stream: bool) -> dict[str, Any]:
        endpoint = self._endpoint
        provider: dict[str, Any] = {
            "order": [endpoint.slug],
            "only": [endpoint.slug],
            "allow_fallbacks": False,
            "require_parameters": True,
            "data_collection": "deny",
            "zdr": True,
            "max_price": {
                "prompt": float(endpoint.prompt_price_per_m),
                "completion": float(endpoint.completion_price_per_m),
                "request": float(endpoint.request_price),
            },
        }
        if endpoint.quantization is not None:
            provider["quantizations"] = [endpoint.quantization]
        return {
            "model": OPENROUTER_MODEL_ID,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "stream": stream,
            "reasoning": {"effort": self._effort, "exclude": True},
            "provider": provider,
        }

    def _headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer " + self._credential.get_secret_value()}

    def _check_size(self, messages: list[dict[str, str]]) -> None:
        if message_bytes(messages) > self._max_prompt_bytes:
            raise ModelCallError("prompt_too_large")

    def _note(self, event: dict[str, Any], anomalies: list[str], ref: str | None) -> str | None:
        """Generation reference (first valid id) and routing checks on one response object."""

        if ref is None and "id" in event:
            value = event.get("id")
            if isinstance(value, str) and GENERATION_REF.fullmatch(value):
                ref = value
            else:
                anomalies.append("generation_ref_invalid")
        model = event.get("model")
        if model is not None and model != OPENROUTER_MODEL_ID:
            anomalies.append("model_mismatch")
        reported = event.get("provider")
        expected = self._endpoint.provider_name
        if isinstance(reported, str) and expected and reported.casefold() != expected.casefold():
            anomalies.append("provider_mismatch")
        return ref

    @staticmethod
    def _usage(usage: ModelUsage | None, ref: str | None, anomalies: list[str]) -> ModelUsage:
        codes = list(anomalies)
        if usage is None:
            usage = ModelUsage()
            codes.append("usage_missing")
        return replace(
            usage, generation_ref=ref, anomalies=tuple(sorted({*usage.anomalies, *codes}))
        )

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        self._check_size(messages)
        payload = self.payload(messages, stream=False)
        try:
            with httpx.Client(
                timeout=self._timeout,
                transport=self._transport,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                response = client.post(self._url, json=payload, headers=self._headers())
        except httpx.TimeoutException:
            raise ModelCallError("timeout") from None
        except httpx.HTTPError:
            raise ModelCallError("transport") from None
        content_bytes = response.content
        if response.status_code != 200:
            raise ModelCallError(
                _status_class(response.status_code, content_bytes[:MAX_ERROR_BODY_BYTES])
            )
        if len(content_bytes) > MAX_STREAM_BYTES:
            raise ModelCallError("protocol")
        try:
            body = _loads(content_bytes.decode("utf-8"))
        except (ValueError, UnicodeError, RecursionError):
            raise ModelCallError("protocol") from None
        if not isinstance(body, dict):
            raise ModelCallError("protocol")
        anomalies: list[str] = []
        ref = self._note(body, anomalies, None)
        usage = self._usage(parse_usage(body["usage"]) if "usage" in body else None, ref, anomalies)
        if "error" in body:
            raise ModelCallError("upstream", usage=usage)
        choices = body.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise ModelCallError("protocol", usage=usage)
        choice = choices[0]
        message = choice.get("message")
        finish = choice.get("finish_reason")
        if finish not in ("stop", "length"):
            error_class = "protocol" if finish is None else _FINISH_CLASSES.get(str(finish))
            raise ModelCallError(error_class or "upstream", usage=usage)
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise ModelCallError("protocol", usage=usage)
        if not content.strip():
            raise ModelCallError("empty_content", usage=usage)
        return ModelAnswer(
            content.strip(), cut_short=finish == "length", usage=usage, finish_reason=finish
        )

    async def _error_body(self, reply: httpx.Response, deadline: float) -> bytes:
        """At most 16 KiB of an error body, read only to find a closed limit code."""

        if reply.is_stream_consumed:
            return reply.content[:MAX_ERROR_BODY_BYTES]
        body = bytearray()
        try:
            with anyio.fail_after(max(0.0, deadline - time.monotonic())):
                async for chunk in reply.aiter_raw():
                    body.extend(chunk)
                    if len(body) >= MAX_ERROR_BODY_BYTES:
                        break
        except (TimeoutError, httpx.HTTPError, httpx.StreamError):
            pass
        return bytes(body[:MAX_ERROR_BODY_BYTES])

    async def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Piece, None]:
        self._check_size(messages)
        payload = self.payload(messages, stream=True)
        anomalies: list[str] = []
        usage: ModelUsage | None = None
        ref: str | None = None
        finish: str | None = None
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                transport=self._transport,
                trust_env=False,
                follow_redirects=False,
            ) as client:
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
                        body = await self._error_body(reply, deadline)
                        raise ModelCallError(_status_class(reply.status_code, body))
                    if reply.headers.get("content-encoding", "identity").lower() != "identity":
                        raise ModelCallError("protocol")
                    frames = OpenAICompatibleChatModel._sse_frames(reply, deadline)
                    while True:
                        try:
                            data = await anext(frames)
                        except StopAsyncIteration:
                            break
                        except (
                            LlmUnavailableError,
                            TimeoutError,
                            httpx.HTTPError,
                            UnicodeError,
                        ) as error:
                            if finish is None:
                                raise ModelCallError(_read_class(error)) from None
                            anomalies.append("read_through_incomplete")
                            break
                        if data.strip() == "[DONE]":
                            break
                        event = _event(data)
                        # After the finish the answer is complete and already checked: a bad
                        # accounting frame costs the usage (unsettled), never the answer.
                        if event is None or "error" in event:
                            if finish is not None:
                                anomalies.append("read_through_incomplete")
                                break
                            if event is None:
                                raise ModelCallError("protocol")
                            raise ModelCallError(
                                "upstream_midstream", usage=self._usage(usage, ref, anomalies)
                            )
                        ref = self._note(event, anomalies, ref)
                        if "usage" in event and event["usage"] is not None:
                            if usage is None:
                                usage = parse_usage(event["usage"])
                            else:
                                anomalies.append("usage_repeated")
                        choices = event.get("choices")
                        if finish is None:
                            if (
                                not isinstance(choices, list)
                                or len(choices) != 1
                                or not isinstance(choices[0], dict)
                            ):
                                raise ModelCallError("protocol")
                            delta = choices[0].get("delta")
                            if not isinstance(delta, dict):
                                raise ModelCallError("protocol")
                            piece = delta.get("content")
                            if piece is not None and not isinstance(piece, str):
                                raise ModelCallError("protocol")
                            reason = choices[0].get("finish_reason")
                            if piece:
                                piece.encode("utf-8", errors="strict")
                                yield Piece(piece)
                            if reason in ("stop", "length"):
                                finish = reason
                            elif reason is not None:
                                raise ModelCallError(
                                    _FINISH_CLASSES.get(str(reason), "upstream_midstream"),
                                    usage=self._usage(usage, ref, anomalies),
                                )
                            continue
                        # After the finish: accounting only. Nothing more is shown.
                        if choices is None:
                            continue
                        if (
                            not isinstance(choices, list)
                            or len(choices) > 1
                            or (choices and not isinstance(choices[0], dict))
                        ):
                            anomalies.append("read_through_incomplete")
                            break
                        if choices:
                            delta = choices[0].get("delta")
                            if isinstance(delta, dict) and delta.get("content"):
                                anomalies.append("content_after_finish")
                            reason = choices[0].get("finish_reason")
                            if reason is not None and reason != finish:
                                anomalies.append("finish_mismatch")
                finally:
                    # Cancellation of the answer must also release the provider connection.
                    with anyio.CancelScope(shield=True):
                        await reply.aclose()
            if finish is None:
                raise ModelCallError("protocol")
            yield Piece(
                cut_short=finish == "length",
                usage=self._usage(usage, ref, anomalies),
                finish_reason=finish,
            )
        except TimeoutError:
            raise ModelCallError("timeout") from None
        except (UnicodeError, httpx.StreamError):
            raise ModelCallError("protocol") from None
        except httpx.TimeoutException:
            raise ModelCallError("timeout") from None
        except httpx.HTTPError:
            raise ModelCallError("transport") from None

    def warm(self, messages: list[dict[str, str]]) -> None:
        """Never warms a remote model: case facts are not sent ahead of a question."""

        return None
