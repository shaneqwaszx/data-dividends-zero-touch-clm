"""OpenRouter adapter for one approved ``openai/gpt-oss-120b`` endpoint (D-091; Phase B D-092).

It accepts an in-memory ``httpx.MockTransport`` (not a subclass) or the ``LIVE_NETWORK``
marker, and nothing else. (The check is on the transport's type: a mock's handler is test
code and is not inspected.) Only ``model_factory`` hands out the marker, and only when the
Phase B live gate is open for the evaluation harness (synthetic cases); the adapter then uses
httpx's own HTTPS transport with certificate verification and no retries.

What it sends (fixed, not configurable): one ``POST /chat/completions`` per question to
``https://openrouter.ai/api/v1``, the full endpoint slug in ``provider.order`` and
``provider.only`` with fallbacks off, ``require_parameters``, ``data_collection: deny``,
``zdr``, ``max_price`` from the endpoint record, ``reasoning.exclude`` and no attribution
headers, user or session identifiers, tools, plugins or files. No retries; ``warm`` sends
nothing. Proxies, ``.netrc`` and certificate environment overrides are ignored.

D-138 A1 (proposed, not active): on the hosted deployment only, every live request (the chat,
the account checks and the public listing) goes through the one exact-host egress proxy the
service registered at start-up (``register_hosted_proxy``): an IPv4 address inside the reviewed
internal network, on the reviewed port, and only while the owner's OpenRouter decision and
both data decisions (D-129, OpenRouter's own) are in the code. The tunnel is ``CONNECT
openrouter.ai:443``; TLS stays end to end and is verified for openrouter.ai (certifi, host name
checked). No other proxy source is read (``trust_env=False`` on both the client and the
transport), and there is no retry or fallback.

What it reads: content only before the first ``stop``/``length`` finish, then the stream to
``[DONE]`` for OpenRouter's usage chunk. Reasoning text is never yielded, stored or logged.
Errors become ``ModelCallError`` with a closed class; provider error text is never kept.
"""

import ipaddress
import json
import re
import threading
import time
from collections.abc import AsyncGenerator
from dataclasses import replace
from decimal import Decimal
from typing import Any

import anyio
import httpx
from pydantic import SecretStr

from . import config as assistant_config
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


class _LiveNetwork:
    """Marker for the real HTTPS transport. It carries nothing; the gate is in the factory."""

    def __repr__(self) -> str:
        return "LIVE_NETWORK"


LIVE_NETWORK = _LiveNetwork()


def require_offline_transport(transport: object) -> httpx.MockTransport:
    """Phase A2 containment: only an in-memory mock transport, never a subclass of one,
    a real HTTP transport or a wrapper around one."""

    if type(transport) is not httpx.MockTransport:
        raise ProfileConfigError(
            "TRANSPORT_NOT_ALLOWED",
            "the remote profile accepts only an in-memory mock transport in this build",
        )
    return transport


def require_allowed_transport(transport: object) -> httpx.MockTransport | None:
    """A mock transport, or None for the live marker (httpx then builds its own HTTPS
    transport: certificates verified, no retries, and ``trust_env=False`` on the client)."""

    if transport is LIVE_NETWORK:
        return None
    return require_offline_transport(transport)


# D-138 A1: the hosted egress proxy. The network and port are the reviewed values of
# apps/assistant/deploy/compose.assistant-openrouter.yml; the address comes from the hosting
# layer's own setting and must lie inside the network (never its network address, gateway or
# broadcast address). Comments only: every string constant here joins the synthetic boundary.
HOSTED_PROXY_NETWORK = ipaddress.IPv4Network("172.30.244.0/29")
HOSTED_PROXY_PORT = 4750
_PROXY_FORM = re.compile(r"http://([0-9.]{7,15}):([0-9]{1,5})")
_hosted_proxy: str | None = None
_hosted_proxy_lock = threading.Lock()


def parse_hosted_proxy(text: str) -> str | None:
    # The proxy URL in its one accepted spelling, or None: no name, userinfo, path, IPv6,
    # leading zero or other port.
    match = _PROXY_FORM.fullmatch(text)
    if match is None:
        return None
    try:
        address = ipaddress.IPv4Address(match.group(1))
    except ValueError:
        return None
    network = HOSTED_PROXY_NETWORK
    if (
        str(address) != match.group(1)
        or address not in network
        or address in (network.network_address, network.network_address + 1)
        or address == network.broadcast_address
        or match.group(2) != str(HOSTED_PROXY_PORT)
    ):
        return None
    return text


def register_hosted_proxy(url: str) -> None:
    # Once per process, with the same value only, and only while both owner decisions are in
    # the code; anything else is refused (fail closed).
    global _hosted_proxy
    if (
        assistant_config.HOSTED_OPENROUTER_DECISION is None
        or assistant_config.HOSTED_TRANSMISSION_DECISION is None
        or assistant_config.HOSTED_OPENROUTER_TRANSMISSION_DECISION is None
        or parse_hosted_proxy(url) is None
    ):
        raise ValueError
    with _hosted_proxy_lock:
        if _hosted_proxy is not None and _hosted_proxy != url:
            raise ValueError
        _hosted_proxy = url


def hosted_proxy() -> str | None:
    return _hosted_proxy


def live_transport() -> httpx.HTTPTransport | None:
    # The transport of a live request: None (httpx's own, as before) unless the hosted proxy
    # is registered; then that proxy and nothing else, certificates verified, no retries.
    proxy = _hosted_proxy
    if proxy is None:
        return None
    return httpx.HTTPTransport(proxy=httpx.Proxy(proxy), verify=True, trust_env=False, retries=0)


def live_async_transport() -> httpx.AsyncHTTPTransport | None:
    proxy = _hosted_proxy
    if proxy is None:
        return None
    return httpx.AsyncHTTPTransport(
        proxy=httpx.Proxy(proxy), verify=True, trust_env=False, retries=0
    )


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
    """The ``ChatModel`` for one approved OpenRouter endpoint."""

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
        self._transport = require_allowed_transport(transport)
        self._live = transport is LIVE_NETWORK
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
    def live(self) -> bool:
        return self._live

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

    @property
    def max_prompt_bytes(self) -> int:
        return self._max_prompt_bytes

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

    def _bounded_body(self, response: httpx.Response, limit: int, deadline: float) -> bytes:
        """Read at most ``limit`` bytes of an identity-encoded body before ``deadline``. A
        longer body is cut at the limit (the caller decides whether that is an error)."""

        if response.is_stream_consumed:  # an in-memory body (a mock, or already read)
            return response.content[: limit + 1]
        body = bytearray()
        for chunk in response.iter_raw():
            if time.monotonic() >= deadline:
                raise ModelCallError("timeout")
            body.extend(chunk)
            if len(body) > limit:
                break
        return bytes(body)

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        self._check_size(messages)
        payload = self.payload(messages, stream=False)
        # One deadline for the whole request, and a byte bound applied while reading.
        deadline = time.monotonic() + self._timeout
        try:
            with httpx.Client(
                timeout=self._timeout,
                transport=live_transport() if self._live else self._transport,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                request = client.build_request(
                    "POST",
                    self._url,
                    json=payload,
                    headers={**self._headers(), "Accept-Encoding": "identity"},
                )
                response = client.send(request, stream=True)
                try:
                    status = response.status_code
                    if status != 200:
                        # As on the stream path: a slow or broken error body never hides the
                        # status (a refusal must still be classed, and may open the breaker).
                        try:
                            error_body = self._bounded_body(
                                response, MAX_ERROR_BODY_BYTES, deadline
                            )
                        except (ModelCallError, httpx.HTTPError, httpx.StreamError):
                            error_body = b""
                        raise ModelCallError(
                            _status_class(status, error_body[:MAX_ERROR_BODY_BYTES])
                        )
                    if response.headers.get("content-encoding", "identity").lower() != "identity":
                        raise ModelCallError("protocol")
                    content_bytes = self._bounded_body(response, MAX_STREAM_BYTES, deadline)
                finally:
                    response.close()
        except httpx.TimeoutException:
            raise ModelCallError("timeout") from None
        except httpx.HTTPError:
            raise ModelCallError("transport") from None
        if len(content_bytes) > MAX_STREAM_BYTES:
            raise ModelCallError("protocol")
        if time.monotonic() >= deadline:
            raise ModelCallError("timeout")
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
                transport=live_async_transport() if self._live else self._transport,
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
        except ModelCallError as error:
            # A failure after the generation started keeps its reference (Phase B verifies
            # the serving provider of every call, failed ones included).
            if error.usage is not None or ref is None:
                raise
            raise ModelCallError(
                error.error_class, usage=self._usage(usage, ref, anomalies)
            ) from None
        except TimeoutError:
            raise ModelCallError("timeout", usage=self._seen(usage, ref, anomalies)) from None
        except (UnicodeError, httpx.StreamError):
            raise ModelCallError("protocol", usage=self._seen(usage, ref, anomalies)) from None
        except httpx.TimeoutException:
            raise ModelCallError("timeout", usage=self._seen(usage, ref, anomalies)) from None
        except httpx.HTTPError:
            raise ModelCallError("transport", usage=self._seen(usage, ref, anomalies)) from None

    def _seen(
        self, usage: ModelUsage | None, ref: str | None, anomalies: list[str]
    ) -> ModelUsage | None:
        """What a failed stream had reported, or None when it reported nothing."""

        return None if usage is None and ref is None else self._usage(usage, ref, anomalies)

    def warm(self, messages: list[dict[str, str]]) -> None:
        """Never warms a remote model: case facts are not sent ahead of a question."""

        return None
