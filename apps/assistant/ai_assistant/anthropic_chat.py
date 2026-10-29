# Claude Sonnet 5.5 through the Anthropic Messages API (D-099, PROPOSED): DORMANT adapter.
#
# **Dormant.** It accepts only an in-memory ``httpx.MockTransport`` (the D-091 L1 containment,
# ``openrouter.require_offline_transport``) and ``build`` always refuses, because the provider-side
# spending controls the remote profile relies on are missing for a direct Anthropic key
# (``anthropic_profiles``). Nothing in the service composes it; it exists so the request and
# response handling are reviewed and tested before any decision to enable it.
#
# What it sends (fixed by ``anthropic_profiles.ClaudeConfiguration``): one ``POST /v1/messages``
# per question to ``https://api.anthropic.com`` with ``anthropic-version: 2026-10-21``, the
# model, ``max_tokens``, the thinking mode and effort, the service's leading system messages as
# top-level system text blocks (same order, unchanged) and the conversation. No sampling
# parameters, tools, metadata, service tier, speed, inference geography or server-side fallback.
# A system message after the conversation has started has no faithful place in the Messages API,
# so such a prompt is refused rather than reordered or relabelled. No retries; ``warm`` sends
# nothing. Proxies, ``.netrc`` and certificate environment overrides are ignored.
#
# Before anything is sent the messages must hold a D-095 eligibility ticket (development mode)
# or pass the D-094 synthetic text check, exactly like the GPT-OSS remote model (D-095 V5).
#
# What it reads: text deltas only (thinking is never yielded, stored or logged), the stop reason
# and the usage. The reply's model must be the pinned one at ``message_start``, before any text;
# a non-standard tier, geography or speed is a routing anomaly; prompt-cache tokens (never
# requested) or missing counts make the usage malformed. The cost is the reported tokens at the
# published standard prices, and is dropped (unsettled) whenever anything is anomalous. Errors
# become ``ModelCallError`` with a closed class; a provider spend limit is ``payment_key_limit``.
# Provider error text is never kept.

import time
from collections.abc import AsyncGenerator
from decimal import Decimal
from typing import Any

import anyio
import httpx
from pydantic import SecretStr

from . import anthropic_profiles, synthetic_eligibility
from .anthropic_profiles import ClaudeConfiguration
from .budget import PER_MESSAGE_OVERHEAD, TEMPLATE_OVERHEAD
from .llm import (
    LlmUnavailableError,
    ModelAnswer,
    ModelCallError,
    ModelUsage,
    OpenAICompatibleChatModel,
    Piece,
    message_bytes,
    micro_usd,
)
from .model_profiles import ProfileConfigError
from .openrouter import (
    GENERATION_REF,
    MAX_ERROR_BODY_BYTES,
    _count,
    _event,
    _loads,
    _read_class,
    require_offline_transport,
)
from .synthetic_boundary import check_messages

MESSAGES_URL = anthropic_profiles.BASE_URL + "/v1/messages"
_MILLION = Decimal(1_000_000)
_STATUS_CLASSES = {
    400: "bad_request",
    401: "auth",
    403: "forbidden",
    404: "not_allowed",
    408: "timeout",
    413: "prompt_too_large",
    429: "rate_limited",
}
_TEXT_BLOCKS = frozenset({"text", "thinking", "redacted_thinking"})
_HIDDEN_DELTAS = frozenset({"thinking_delta", "signature_delta"})


class PromptShapeError(ValueError):
    # The service's messages cannot be sent without changing their roles or order.
    pass


def system_and_conversation(
    messages: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    # The leading system messages become system text blocks, in order and unchanged; the
    # rest must be a user/assistant conversation that starts and ends with the user.
    index = 0
    system: list[dict[str, str]] = []
    while index < len(messages) and messages[index].get("role") == "system":
        system.append({"type": "text", "text": str(messages[index].get("content") or "")})
        index += 1
    rest = messages[index:]
    if not system or not rest:
        raise PromptShapeError("no system prompt or no question")
    roles = [message.get("role") for message in rest]
    if any(role not in ("user", "assistant") for role in roles):
        raise PromptShapeError("a system message after the conversation started")
    if roles[0] != "user" or roles[-1] != "user":
        raise PromptShapeError("the conversation must start and end with the user")
    if any(a == b for a, b in zip(roles, roles[1:], strict=False)):
        raise PromptShapeError("turns must alternate")
    return system, [{"role": str(m["role"]), "content": str(m.get("content") or "")} for m in rest]


def reservation_micro_usd(messages: list[dict[str, str]]) -> int:
    # The labelled worst case for one call, as ``budget.reservation_for`` bounds it: content
    # tokens by UTF-8 bytes plus the per-message and template allowances, at the input price,
    # plus every allowed output token (thinking included) at the output price.
    prompt_bound = (
        message_bytes(messages) + PER_MESSAGE_OVERHEAD * len(messages) + TEMPLATE_OVERHEAD
    )
    cost = (
        Decimal(prompt_bound) * anthropic_profiles.INPUT_USD_PER_MTOK
        + Decimal(anthropic_profiles.MAX_TOKENS) * anthropic_profiles.OUTPUT_USD_PER_MTOK
    ) / _MILLION
    return max(1, micro_usd(cost))


def cost_usd(input_tokens: int, output_tokens: int) -> Decimal:
    return (
        Decimal(input_tokens) * anthropic_profiles.INPUT_USD_PER_MTOK
        + Decimal(output_tokens) * anthropic_profiles.OUTPUT_USD_PER_MTOK
    ) / _MILLION


def _status_class(status: int, body: bytes) -> str:
    # Closed error class. A spend limit (the organisation's or workspace's monthly cap, or
    # the limit the owner set) is ``payment_key_limit``: it repeats on every call.
    error_class = _STATUS_CLASSES.get(status, "upstream" if 500 <= status < 600 else "http_other")
    if status not in (400, 429):
        return error_class
    try:
        error = _loads(body).get("error") or {}
        code = (error.get("details") or {}).get("error_code")
        message = str(error.get("message") or "")
    except (ValueError, AttributeError, TypeError, RecursionError, UnicodeError):
        return error_class
    if code == "enforced_spend_limit_reached" or (
        message.startswith("You have reached your") and "usage limits" in message
    ):
        return "payment_key_limit"
    return error_class


class _Usage:
    # What the stream reported so far (content-free).
    def __init__(self) -> None:
        self.input: int | None = None
        self.output: int | None = None
        self.cache: int = 0
        self.ref: str | None = None
        self.anomalies: list[str] = []

    def opening(self, message: dict[str, Any]) -> None:
        ref = message.get("id")
        if isinstance(ref, str) and GENERATION_REF.fullmatch(ref):
            self.ref = ref
        elif ref is not None:
            self.anomalies.append("generation_ref_invalid")
        usage = message.get("usage")
        if not isinstance(usage, dict):
            self.anomalies.append("usage_missing")
            return
        self.input = _count(usage.get("input_tokens"))
        for name in ("cache_creation_input_tokens", "cache_read_input_tokens"):
            value = usage.get(name)
            if value is not None:
                count = _count(value)
                if count is None:
                    self.anomalies.append("usage_malformed")
                else:
                    self.cache += count
        self.routing(usage)

    def routing(self, usage: dict[str, Any]) -> None:
        # A tier, geography or speed the standard price card does not cover.
        if (
            usage.get("service_tier") not in (None, "standard")
            or usage.get("inference_geo") not in (None, "global", "not_available")
            or usage.get("speed") not in (None, "standard")
        ) and "provider_mismatch" not in self.anomalies:
            self.anomalies.append("provider_mismatch")

    def closing(self, usage: object) -> None:
        if not isinstance(usage, dict):
            return
        output = _count(usage.get("output_tokens"))
        if output is None:
            self.anomalies.append("usage_malformed")
        else:
            self.output = output
        self.routing(usage)

    def result(self) -> ModelUsage:
        anomalies = list(dict.fromkeys(self.anomalies))
        if self.cache and "usage_malformed" not in anomalies:
            anomalies.append("usage_malformed")  # prompt caching is never requested
        if (self.input is None or self.output is None) and "usage_missing" not in anomalies:
            anomalies.append("usage_missing")
        cost = (
            cost_usd(self.input, self.output)
            if not anomalies and self.input is not None and self.output is not None
            else None
        )
        prompt = None if self.input is None else self.input + self.cache
        return ModelUsage(
            prompt_tokens=prompt,
            completion_tokens=self.output,
            cached_tokens=self.cache or None,
            cost=cost,
            generation_ref=self.ref,
            anomalies=tuple(anomalies),
        )


class AnthropicChatModel:
    # The ``ChatModel`` for one Claude Sonnet 5.5 configuration (dormant: mock transport).
    def __init__(
        self,
        *,
        configuration: ClaudeConfiguration,
        credential: SecretStr,
        max_prompt_bytes: int,
        transport: object,
        synthetic_dev: bool = False,
    ) -> None:
        self._transport = require_offline_transport(transport)
        if configuration.profile_id not in anthropic_profiles.CONFIGURATIONS:
            raise ProfileConfigError("PROFILE_UNKNOWN", "not an approved Claude configuration")
        self._configuration = configuration
        self._credential = credential
        self._max_prompt_bytes = max_prompt_bytes
        self._synthetic_dev = synthetic_dev

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._configuration.profile_id!r})"

    @property
    def name(self) -> str:
        return anthropic_profiles.MODEL_ID

    @property
    def configuration(self) -> ClaudeConfiguration:
        return self._configuration

    def payload(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        system, conversation = system_and_conversation(messages)
        return {
            **self._configuration.request_fields(),
            "system": system,
            "messages": conversation,
            "stream": True,
        }

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._credential.get_secret_value(),
            "anthropic-version": anthropic_profiles.API_VERSION,
            "content-type": "application/json",
            "accept-encoding": "identity",
        }

    def _admit(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        # Refuse before anything is sent: outside the synthetic boundary, a prompt that cannot
        # be sent unchanged, or one above the byte bound.
        ticket = synthetic_eligibility.admitted(messages) if self._synthetic_dev else False
        if not ticket and check_messages(messages) is not None:
            raise ModelCallError("not_allowed")
        if message_bytes(messages) > self._max_prompt_bytes:
            raise ModelCallError("prompt_too_large")
        try:
            return self.payload(messages)
        except PromptShapeError:
            raise ModelCallError("not_allowed") from None

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        raise LlmUnavailableError("streaming only")

    def warm(self, messages: list[dict[str, str]]) -> None:
        # Never warms a remote model: case facts are not sent ahead of a question.
        return None

    @staticmethod
    async def _error_body(reply: httpx.Response, deadline: float) -> bytes:
        # At most 16 KiB of an error body, read only to find a closed limit code.
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
        payload = self._admit(messages)
        seen = _Usage()
        started = False
        finish: str | None = None
        stop_reason: str | None = None
        blocks: dict[int, str] = {}
        timeout = anthropic_profiles.TIMEOUT_SECONDS
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout),
                transport=self._transport,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                deadline = time.monotonic() + timeout
                request = client.build_request(
                    "POST", MESSAGES_URL, json=payload, headers=self._headers()
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
                            raise ModelCallError(
                                _read_class(error), usage=self._seen(seen, started)
                            ) from None
                        event = _event(data)
                        if event is None:
                            raise ModelCallError("protocol", usage=self._seen(seen, started))
                        kind = event.get("type")
                        if kind == "ping":
                            continue
                        if kind == "error":
                            raise ModelCallError(
                                "upstream_midstream", usage=self._seen(seen, started)
                            )
                        if not started:
                            if kind != "message_start" or not isinstance(
                                event.get("message"), dict
                            ):
                                raise ModelCallError("protocol")
                            message = event["message"]
                            started = True
                            seen.opening(message)
                            # The pinned model, before any text reaches the guard.
                            if message.get("model") != anthropic_profiles.MODEL_ID:
                                seen.anomalies.append("model_mismatch")
                                raise ModelCallError("protocol", usage=seen.result())
                            continue
                        if kind == "content_block_start":
                            block = event.get("content_block")
                            index = event.get("index")
                            kind_of = block.get("type") if isinstance(block, dict) else None
                            if type(index) is not int or kind_of not in _TEXT_BLOCKS:
                                raise ModelCallError("protocol", usage=seen.result())
                            blocks[index] = str(kind_of)
                        elif kind == "content_block_delta":
                            delta = event.get("delta")
                            delta_kind = delta.get("type") if isinstance(delta, dict) else None
                            if delta_kind in _HIDDEN_DELTAS:
                                continue
                            text = delta.get("text") if isinstance(delta, dict) else None
                            if (
                                delta_kind != "text_delta"
                                or blocks.get(event.get("index")) != "text"  # type: ignore[arg-type]
                                or not isinstance(text, str)
                            ):
                                raise ModelCallError("protocol", usage=seen.result())
                            if stop_reason is not None:
                                seen.anomalies.append("content_after_finish")
                                continue
                            if text:
                                text.encode("utf-8", errors="strict")
                                yield Piece(text)
                        elif kind == "message_delta":
                            delta = event.get("delta")
                            reason = delta.get("stop_reason") if isinstance(delta, dict) else None
                            if reason is not None:
                                stop_reason = str(reason)
                            seen.closing(event.get("usage"))
                        elif kind == "message_stop":
                            finish = "done"
                            break
                        # content_block_stop and event types added later carry no text.
                finally:
                    # Cancellation of the answer must also release the provider connection.
                    with anyio.CancelScope(shield=True):
                        await reply.aclose()
            if finish is None or stop_reason is None:
                raise ModelCallError("upstream_midstream", usage=self._seen(seen, started))
            if stop_reason == "refusal":
                raise ModelCallError("content_filter", usage=seen.result())
            if stop_reason not in ("end_turn", "max_tokens"):
                raise ModelCallError("protocol", usage=seen.result())
            cut_short = stop_reason == "max_tokens"
            yield Piece(
                cut_short=cut_short,
                usage=seen.result(),
                finish_reason="length" if cut_short else "stop",
            )
        except ModelCallError:
            raise
        except TimeoutError:
            raise ModelCallError("timeout", usage=self._seen(seen, started)) from None
        except (UnicodeError, httpx.StreamError):
            raise ModelCallError("protocol", usage=self._seen(seen, started)) from None
        except httpx.TimeoutException:
            raise ModelCallError("timeout", usage=self._seen(seen, started)) from None
        except httpx.HTTPError:
            raise ModelCallError("transport", usage=self._seen(seen, started)) from None

    @staticmethod
    def _seen(seen: _Usage, started: bool) -> ModelUsage | None:
        # What a failed stream had reported (never a cost), or None when it reported nothing.
        if not started:
            return None
        usage = seen.result()
        return ModelUsage(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            cached_tokens=usage.cached_tokens,
            cost=None,
            generation_ref=usage.generation_ref,
            anomalies=usage.anomalies,
        )


def build(profile_id: str, settings: Any, **options: Any) -> AnthropicChatModel:
    # Always refused in this build: the configuration is listed but never usable
    # (``anthropic_profiles.availability``), so the service can never compose it.
    _, reason = anthropic_profiles.availability(settings)
    raise ProfileConfigError(reason, "not usable in this build")
