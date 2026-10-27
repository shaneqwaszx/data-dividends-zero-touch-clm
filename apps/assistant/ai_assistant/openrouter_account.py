"""Phase B (D-092, proposed) read-only OpenRouter account checks: no inference, no content.

Two authenticated GET requests, both to ``https://openrouter.ai/api/v1`` with the same key the
adapter uses:

    GET /key                  this key's limit, reset period and cumulative usage (USD)
    GET /generation?id=...    one generation's serving provider, model and total cost (USD)

Neither request can return prompt or completion text (the generation schema has no content
field; content is a different endpoint that this module never calls). Only the fields named
below are parsed and kept; the key's label, budgets, workspace and every other field are
discarded unread. Errors are closed codes; provider error text and the key never appear in
an exception, a return value or a log. No retries except the bounded wait for generation
metadata, which OpenRouter publishes shortly after a call ends.
"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx
from pydantic import SecretStr

from .model_profiles import OPENROUTER_BASE_URL
from .openrouter import GENERATION_REF, require_allowed_transport

MAX_BODY_BYTES = 64 * 1024
_MAX_USD = Decimal("100000")


class AccountCheckError(Exception):
    """A read-only account check failed. The code is closed; the message holds no data."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class KeyStatus:
    """The key's own spending limit. ``limit_usd`` None: no limit. ``limit_reset`` None:
    the limit never resets (anything else is a periodic limit, not a lifetime one)."""

    limit_usd: Decimal | None
    limit_reset: str | None
    limit_remaining_usd: Decimal | None
    usage_usd: Decimal


@dataclass(frozen=True)
class GenerationFacts:
    provider_name: str | None
    model: str
    total_cost_usd: Decimal
    tokens_prompt: int | None
    tokens_completion: int | None
    native_tokens_reasoning: int | None
    cancelled: bool | None
    finish_reason: str | None


def _usd(value: object, *, optional: bool = False) -> Decimal | None:
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, int | Decimal):
        raise AccountCheckError("malformed")
    amount = Decimal(value)
    if not amount.is_finite() or not 0 <= amount <= _MAX_USD:
        raise AccountCheckError("malformed")
    return amount


def _count(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise AccountCheckError("malformed")
    return value


def _short_text(value: object, *, optional: bool = True) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not 0 < len(value) <= 120:
        raise AccountCheckError("malformed")
    return value


class OpenRouterAccount:
    """The two read-only account checks, over the live network or an injected mock."""

    def __init__(
        self,
        credential: SecretStr,
        *,
        transport: object,
        timeout_seconds: float = 20.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._credential = credential
        self._transport = require_allowed_transport(transport)
        self._timeout = timeout_seconds
        self._sleep = sleep

    def __repr__(self) -> str:
        return "OpenRouterAccount()"

    def _get(self, path: str, params: dict[str, str] | None = None) -> tuple[int, Any]:
        try:
            with httpx.Client(
                timeout=self._timeout,
                transport=self._transport,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                headers = {
                    "Authorization": "Bearer " + self._credential.get_secret_value(),
                    "Accept-Encoding": "identity",
                }
                with client.stream(
                    "GET", OPENROUTER_BASE_URL + path, params=params, headers=headers
                ) as response:
                    status = response.status_code
                    body = bytearray()
                    if response.is_stream_consumed:  # an in-memory body (a mock)
                        body.extend(response.content)
                    else:
                        for chunk in response.iter_raw():
                            body.extend(chunk)
                            if len(body) > MAX_BODY_BYTES:
                                break
                    if len(body) > MAX_BODY_BYTES:
                        raise AccountCheckError("too_large")
        except httpx.TimeoutException:
            raise AccountCheckError("timeout") from None
        except httpx.HTTPError:
            raise AccountCheckError("transport") from None
        if status != 200:
            return status, None
        try:
            parsed = json.loads(bytes(body).decode("utf-8"), parse_float=Decimal)
        except (ValueError, UnicodeError, RecursionError):
            raise AccountCheckError("malformed") from None
        if not isinstance(parsed, dict) or not isinstance(parsed.get("data"), dict):
            raise AccountCheckError("malformed")
        return status, parsed["data"]

    def key_status(self) -> KeyStatus:
        status, data = self._get("/key")
        if status != 200:
            raise AccountCheckError(f"http_{status}" if 400 <= status < 600 else "http_other")
        reset = data.get("limit_reset")
        if reset is not None and (not isinstance(reset, str) or len(reset) > 32):
            raise AccountCheckError("malformed")
        usage = _usd(data.get("usage"))
        assert usage is not None
        return KeyStatus(
            limit_usd=_usd(data.get("limit"), optional=True),
            limit_reset=reset,
            limit_remaining_usd=_usd(data.get("limit_remaining"), optional=True),
            usage_usd=usage,
        )

    def generation(
        self, ref: str, *, attempts: int = 8, wait_seconds: float = 2.0
    ) -> GenerationFacts:
        """Metadata for one generation, waiting (bounded) while it is not yet published."""

        if not GENERATION_REF.fullmatch(ref) or not ref.startswith("gen-"):
            raise AccountCheckError("bad_reference")
        for attempt in range(max(1, attempts)):
            status, data = self._get("/generation", {"id": ref})
            if status == 200:
                return self._facts(data)
            if status != 404:
                raise AccountCheckError(f"http_{status}" if 400 <= status < 600 else "http_other")
            if attempt + 1 < attempts:
                self._sleep(wait_seconds)
        raise AccountCheckError("not_published")

    @staticmethod
    def _facts(data: dict[str, Any]) -> GenerationFacts:
        cancelled = data.get("cancelled")
        if cancelled is not None and not isinstance(cancelled, bool):
            raise AccountCheckError("malformed")
        model = _short_text(data.get("model"), optional=False)
        cost = _usd(data.get("total_cost"))
        assert model is not None and cost is not None
        return GenerationFacts(
            provider_name=_short_text(data.get("provider_name")),
            model=model,
            total_cost_usd=cost,
            tokens_prompt=_count(data.get("tokens_prompt")),
            tokens_completion=_count(data.get("tokens_completion")),
            native_tokens_reasoning=_count(data.get("native_tokens_reasoning")),
            cancelled=cancelled,
            finish_reason=_short_text(data.get("finish_reason")),
        )
