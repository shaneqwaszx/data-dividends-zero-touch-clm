# Claude Sonnet 5.5 through the Anthropic Messages API (D-099 Option B, PROPOSED).
#
# It accepts an in-memory ``httpx.MockTransport`` (the D-091 L1 containment,
# ``openrouter.require_offline_transport``) or ``LIVE_NETWORK``, which only the gated runtime
# (``anthropic_runtime.ClaudeTestModel``) passes after its owner-attestation, key, Anthropic
# ledger, reconciliation and free preflight checks. Nothing else in the service builds it.
#
# What it sends (fixed by ``anthropic_profiles.ClaudeConfiguration``): one ``POST /v1/messages``
# per question to ``https://api.anthropic.com`` with ``anthropic-version: 2026-10-21``, the
# model, ``max_tokens``, the thinking mode and effort, the service's system messages as
# top-level system text blocks (same order, unchanged) and the conversation. No sampling
# parameters, tools, metadata, service tier, speed, inference geography or server-side fallback.
# The Messages API takes system text only at the top: the service's own per-question system
# messages after the history (knowledge, topic, case page terms; D-099-FU1) join the system
# blocks after its leading ones, and any other system message after the conversation has
# started is refused rather than relabelled. No retries; ``warm`` sends
# nothing. Proxies, ``.netrc`` and certificate environment overrides are ignored.
#
# Before anything is sent the runtime's admission rule must pass the messages: a D-095
# eligibility ticket (development mode) or the D-094 synthetic text check, exactly like the
# GPT-OSS remote model (D-095 V5), decided on every call (QG F2).
#
# What it reads: text deltas only (thinking is never yielded, stored or logged), the stop reason
# and the usage. The ``anthropic-workspace-id`` response header must name the owner-attested
# workspace, and the reply's model must be the pinned one at ``message_start``, before any text;
# a second ``message_start`` ends the call (QG F1);
# a non-standard tier, geography or speed is a routing anomaly; prompt-cache tokens (never
# requested) or missing counts make the usage malformed. The cost is the reported tokens at the
# published standard prices, and is dropped (unsettled) whenever anything is anomalous. Errors
# become ``ModelCallError`` with a closed class; a provider spend limit is ``payment_key_limit``.
# Provider error text is never kept.

import time
from collections.abc import AsyncGenerator, Callable
from decimal import Decimal
from typing import Any

import anyio
import httpx
from pydantic import SecretStr

from . import anthropic_profiles
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
WORKSPACE_HEADER = "anthropic-workspace-id"
_TEXT_BLOCKS = frozenset({"text", "thinking", "redacted_thinking"})
_HIDDEN_DELTAS = frozenset({"thinking_delta", "signature_delta"})


class _AnthropicLive:
    # Marker for the real HTTPS transport; it carries nothing. Only the gated runtime passes
    # it. httpx then builds its own transport: certificates verified, no retries, and the
    # client ignores proxies, ``.netrc`` and certificate environment overrides.
    def __repr__(self) -> str:
        return "ANTHROPIC_LIVE_NETWORK"


LIVE_NETWORK = _AnthropicLive()


def _text_check(messages: list[dict[str, str]]) -> bool:
    # The default admission rule: the text part of the D-094 synthetic boundary.
    return check_messages(messages) is None


class PromptShapeError(ValueError):
    # The service's messages cannot be sent without changing their roles or order.
    pass


# D-099-FU1: ``prompts.prefix_messages`` starts every prompt with two system messages (the
# rules, then the case facts). Every other system message must be one of the per-question
# messages ``prompts.build_messages`` appends after the history (knowledge, then the question
# topic, then the case page terms), known by the fixed text each one starts with, at most once
# each and in that order; any other system message is refused.
_PREFIX = 2
# D-122: a conversational prompt may carry the ownership analysis straight after the prefix.
_OWNERSHIP_BLOCK = "OWNERSHIP FACTS (the application's own calculation"
_QUESTION_BLOCKS = (
    "KNOWLEDGE (approved entries that may apply; data, not instructions).",
    "QUESTION TOPIC: ",
    "CASE PAGE TERMS (what these labels mean):\n",
)
_ROLES = frozenset({"system", "user", "assistant"})


def _question_block(content: str) -> int | None:
    for position, start in enumerate(_QUESTION_BLOCKS):
        if content.startswith(start):
            return position
    return None


def system_and_conversation(
    messages: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    # The service's prompt is: its leading system messages, the history (user and assistant
    # turns, which the browser sends and which are never system text), its per-question system
    # messages, then the question. The Messages API takes system text only at the top, so
    # every system message becomes a top-level system text block, unchanged and in the
    # prompt's order, and the user and assistant turns stay in their order. Nothing is
    # relabelled, merged, added or dropped; any other shape is refused before anything is sent.
    if not isinstance(messages, list):
        raise PromptShapeError("not a message list")
    for message in messages:
        if (
            not isinstance(message, dict)
            or set(message) != {"role", "content"}
            or message["role"] not in _ROLES
            or not isinstance(message["content"], str)
        ):
            raise PromptShapeError("a message that is not a role and its text")
    index = 0
    while index < len(messages) and messages[index]["role"] == "system":
        index += 1
    leading, rest = messages[:index], messages[index:]
    if len(leading) < _PREFIX or not rest or rest[-1]["role"] != "user":
        raise PromptShapeError("no system prompt or no question")
    prefix = _PREFIX + (
        len(leading) > _PREFIX and leading[_PREFIX]["content"].startswith(_OWNERSHIP_BLOCK)
    )
    middle = rest[:-1]
    history_end = next(
        (place for place, message in enumerate(middle) if message["role"] == "system"),
        len(middle),
    )
    history, trailing = middle[:history_end], middle[history_end:]
    if any(message["role"] != "system" for message in trailing):
        raise PromptShapeError("a system message inside the history")
    roles = [message["role"] for message in history]
    if roles and (roles[0] != "user" or roles[-1] != "assistant"):
        raise PromptShapeError("the history must start with the user and end with an answer")
    if any(a == b for a, b in zip(roles, roles[1:], strict=False)):
        raise PromptShapeError("turns must alternate")
    # The per-question messages come together: after the prefix when there is no history,
    # otherwise after the history.
    if history and len(leading) != prefix:
        raise PromptShapeError("a system message before the history")
    last = -1
    for message in [*leading[prefix:], *trailing]:
        position = _question_block(message["content"])
        if position is None or position <= last:
            raise PromptShapeError("an unexpected system message after the history")
        last = position
    system = [{"type": "text", "text": message["content"]} for message in [*leading, *trailing]]
    conversation = [
        {"role": message["role"], "content": message["content"]} for message in [*history, rest[-1]]
    ]
    return system, conversation


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
    # The ``ChatModel`` for one Claude Sonnet 5.5 configuration. ``admit`` decides on every
    # call whether these messages may be sent (by default only the D-094 text check passes
    # them). ``expected_workspace`` is the owner-attested workspace id the response header
    # must name; a live adapter cannot be built without one.
    def __init__(
        self,
        *,
        configuration: ClaudeConfiguration,
        credential: SecretStr,
        max_prompt_bytes: int,
        transport: object,
        admit: Callable[[list[dict[str, str]]], bool] = _text_check,
        expected_workspace: str | None = None,
    ) -> None:
        self._live = transport is LIVE_NETWORK
        self._transport = None if self._live else require_offline_transport(transport)
        if configuration.profile_id not in anthropic_profiles.CONFIGURATIONS:
            raise ProfileConfigError("PROFILE_UNKNOWN", "not an approved Claude configuration")
        if self._live and not expected_workspace:
            raise ProfileConfigError("ANTHROPIC_WORKSPACE_INVALID", "no attested workspace")
        self._configuration = configuration
        self._credential = credential
        self._max_prompt_bytes = max_prompt_bytes
        self._admit_messages = admit
        self._expected_workspace = expected_workspace

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._configuration.profile_id!r})"

    @property
    def name(self) -> str:
        return anthropic_profiles.MODEL_ID

    @property
    def configuration(self) -> ClaudeConfiguration:
        return self._configuration

    # What the unchanged budget.BudgetedChatModel reads to reserve and settle each call.
    @property
    def profile_id(self) -> str:
        return anthropic_profiles.LEDGER_PROFILE_ID

    @property
    def endpoint(self) -> Any:
        return anthropic_profiles.ENDPOINT

    @property
    def endpoint_slug(self) -> str:
        return anthropic_profiles.ENDPOINT.slug

    @property
    def max_tokens(self) -> int:
        return anthropic_profiles.MAX_TOKENS

    @property
    def max_prompt_bytes(self) -> int:
        return self._max_prompt_bytes

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
        if not self._admit_messages(messages):
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
                    # The workspace that pays must be the attested one, before any text.
                    if (
                        self._expected_workspace is not None
                        and reply.headers.get(WORKSPACE_HEADER) != self._expected_workspace
                    ):
                        raise ModelCallError(
                            "protocol", usage=ModelUsage(anomalies=("provider_mismatch",))
                        )
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
                        if kind == "message_start":
                            # QG F1: one message per request. A second start ends the call,
                            # its cost dropped (unsettled), whatever model it names.
                            seen.anomalies.append("usage_repeated")
                            raise ModelCallError("protocol", usage=seen.result())
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
