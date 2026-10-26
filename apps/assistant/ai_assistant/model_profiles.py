"""Approved chat-model profiles: which models the AI assistant may use and what each can do.

The registry is code and is reviewed like code. Settings only pick a profile and, for the
remote profile, one approved endpoint and values inside the profile's bounds. Settings can
never add a model, a URL, an endpoint or a price.

    local_openai_compatible   the default: today's OpenAI-compatible adapter, unchanged
    openrouter_gpt_oss_120b   DORMANT (D-091) unless the Phase B live gate (D-092, proposed)
                              is opened by the evaluation harness for synthetic cases only;
                              one approved endpoint, ``deepinfra/bf16``

An OpenRouter provider slug such as ``deepinfra`` matches every endpoint of that provider
(all variants and regions). An endpoint record therefore names the full endpoint slug
(``provider[/variant][/region][/tier]``) and records whether that slug was shown to identify
exactly one endpoint of the model on the evidence date. Nothing here approves an endpoint.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from types import MappingProxyType
from typing import Literal

LOCAL_PROFILE_ID = "local_openai_compatible"
OPENROUTER_PROFILE_ID = "openrouter_gpt_oss_120b"
PROFILE_IDS = frozenset({LOCAL_PROFILE_ID, OPENROUTER_PROFILE_ID})

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL_ID = "openai/gpt-oss-120b"
# The value AI_ASSISTANT_REMOTE_INFERENCE_DECISION must hold before the remote profile composes.
REMOTE_DECISION_ID = "D-091"
# The value AI_ASSISTANT_REMOTE_LIVE_DECISION must hold before a real network transport is used
# (Phase B synthetic-only experiment). The service never opens it; see model_factory.py.
LIVE_DECISION_ID = "D-092"
# Answer tokens plus the reasoning allowance, for any remote request.
MAX_REMOTE_TOKENS = 4000
MIN_REASONING_ALLOWANCE = 256

# provider[/variant][/region][/tier], lower case, as OpenRouter writes endpoint slugs.
ENDPOINT_SLUG = re.compile(r"[a-z0-9][a-z0-9.-]{0,47}(?:/[a-z0-9][a-z0-9._-]{0,47}){0,3}")
QUANTIZATIONS = frozenset({"int4", "int8", "fp4", "fp6", "fp8", "fp16", "bf16", "fp32"})
_MAX_PRICE_PLACES = 6


class ProfileConfigError(ValueError):
    """The model configuration is refused. The message names the setting, never its value."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _price(name: str, value: Decimal) -> None:
    """A price that is finite, not negative, and exact as a JSON number (at most 6 places)."""

    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ProfileConfigError("RESERVATION_INPUT_MISSING", f"{name} must be a price")
    exponent = value.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -_MAX_PRICE_PLACES:
        raise ProfileConfigError("RESERVATION_INPUT_MISSING", f"{name} has too many places")
    if Decimal(repr(float(value))) != value:
        raise ProfileConfigError("RESERVATION_INPUT_MISSING", f"{name} is not exact in JSON")


@dataclass(frozen=True)
class ModelCapabilities:
    streaming: bool
    temperature: bool
    # Reasoning effort values the model accepts; empty means no reasoning control.
    reasoning_efforts: frozenset[str] = frozenset()
    usage_in_response: bool = False


@dataclass(frozen=True)
class ApprovedEndpoint:
    """One OpenRouter endpoint of one model, as listed on the evidence date (Phase B)."""

    slug: str
    prompt_price_per_m: Decimal
    completion_price_per_m: Decimal
    # Per-request price; an explicit 0 only when the listing shows none.
    request_price: Decimal
    max_completion_tokens: int
    # True only with documented evidence that max_tokens also bounds reasoning here.
    max_tokens_includes_reasoning: bool
    # True only with evidence that the slug matched exactly one endpoint of the model.
    slug_unique_for_model: bool
    evidence_date: date
    quantization: str | None = None
    cache_write_price_per_m: Decimal | None = None
    internal_reasoning_price_per_m: Decimal | None = None
    # The provider name as listed, compared case-insensitively with a provider field in a
    # response if one ever appears (undocumented; advisory only).
    provider_name: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.slug, str) or not ENDPOINT_SLUG.fullmatch(self.slug):
            raise ProfileConfigError("ENDPOINT_SLUG_INVALID", "endpoint slug is not valid")
        for name in ("prompt_price_per_m", "completion_price_per_m", "request_price"):
            _price(name, getattr(self, name))
        for name in ("cache_write_price_per_m", "internal_reasoning_price_per_m"):
            value = getattr(self, name)
            if value is not None:
                _price(name, value)
        if type(self.max_completion_tokens) is not int or self.max_completion_tokens < 1:
            raise ProfileConfigError(
                "RESERVATION_INPUT_MISSING", "max_completion_tokens must be a positive count"
            )
        if self.quantization is not None and self.quantization not in QUANTIZATIONS:
            raise ProfileConfigError("ENDPOINT_SLUG_INVALID", "quantization is not known")

    @property
    def input_price_per_m(self) -> Decimal:
        """The highest listed input price (cache writes can cost more than plain input)."""

        prices = [self.prompt_price_per_m]
        if self.cache_write_price_per_m is not None:
            prices.append(self.cache_write_price_per_m)
        return max(prices)

    @property
    def output_price_per_m(self) -> Decimal:
        """The highest listed output price (reasoning is billed as output)."""

        prices = [self.completion_price_per_m]
        if self.internal_reasoning_price_per_m is not None:
            prices.append(self.internal_reasoning_price_per_m)
        return max(prices)


@dataclass(frozen=True)
class ModelProfile:
    profile_id: str
    adapter: Literal["openai_compatible", "openrouter"]
    boundary: Literal["loopback_default", "external"]
    capabilities: ModelCapabilities
    # None: taken from AI_ASSISTANT_LLM_* settings (the local profile only).
    model_id: str | None = None
    base_url: str | None = None
    endpoints: tuple[ApprovedEndpoint, ...] = field(default=())
    requires_budget: bool = False
    dormant: bool = False

    def endpoint(self, slug: str) -> ApprovedEndpoint | None:
        return next((item for item in self.endpoints if item.slug == slug), None)


# The public endpoint listing for openai/gpt-oss-120b and the public ZDR endpoint list,
# both read 2026-10-26T17:05Z (24 endpoints, all ZDR-listed; see D-092). The tag
# ``deepinfra/bf16`` was the only DeepInfra endpoint, so the slug identified one endpoint.
# No request, cache-write or internal-reasoning price was listed. No endpoint-specific
# evidence says max_tokens bounds reasoning, so the reservation uses the 117,964 maximum.
DEEPINFRA_BF16 = ApprovedEndpoint(
    slug="deepinfra/bf16",
    prompt_price_per_m=Decimal("0.037"),
    completion_price_per_m=Decimal("0.17"),
    request_price=Decimal("0"),
    max_completion_tokens=117964,
    max_tokens_includes_reasoning=False,
    slug_unique_for_model=True,
    evidence_date=date(2026, 10, 26),
    quantization="bf16",
    provider_name="DeepInfra",
)

LOCAL_PROFILE = ModelProfile(
    profile_id=LOCAL_PROFILE_ID,
    adapter="openai_compatible",
    boundary="loopback_default",
    capabilities=ModelCapabilities(streaming=True, temperature=True),
)

OPENROUTER_PROFILE = ModelProfile(
    profile_id=OPENROUTER_PROFILE_ID,
    adapter="openrouter",
    boundary="external",
    capabilities=ModelCapabilities(
        streaming=True,
        temperature=True,
        reasoning_efforts=frozenset({"low", "medium", "high"}),
        usage_in_response=True,
    ),
    model_id=OPENROUTER_MODEL_ID,
    base_url=OPENROUTER_BASE_URL,
    # Phase B (D-092, proposed): one endpoint, re-read from the public listing by
    # scripts/phase_b_preflight.py before every live run (a mismatch refuses the run).
    endpoints=(DEEPINFRA_BF16,),
    requires_budget=True,
    dormant=True,
)

APPROVED_PROFILES: Mapping[str, ModelProfile] = MappingProxyType(
    {LOCAL_PROFILE_ID: LOCAL_PROFILE, OPENROUTER_PROFILE_ID: OPENROUTER_PROFILE}
)
