# Claude Sonnet 5.5 on AI Models (D-099 Option B, PROPOSED): two configurations.
#
# Two configurations of ONE model, ``claude-sonnet-5-5`` on the Anthropic Messages API (Fast
# is not a separate model):
#
#     anthropic_claude_sonnet_5_5_medium   Balanced: effort medium, adaptive thinking
#                                          (recommended)
#     anthropic_claude_sonnet_5_5_low      Fast: effort low, thinking ``between_tools``
#                                          (Sonnet 5.5 cannot turn thinking off with
#                                          ``disabled``)
#
# Ids name the effort, as GPT-OSS Fast's does (``openrouter_gpt_oss_120b_low``); the page shows
# "Balanced" and "Fast" from the effort (D-097), so no label adds words to the boundary.
#
# Both match the owner-scored benchmark (``.ai-pipeline/reports/CLAUDE_API_MODEL_BENCHMARK.md``
# sections 9 and 10: same model ID, API version, effort, thinking mode and ``max_tokens``). Each
# has its own profile id and fingerprint, so a qualification of one never counts for the other or
# for GPT-OSS.
#
# The D-091 to D-098 remote controls rest on three provider-side checks that a direct Anthropic
# API key cannot give (MISSING_CONTROLS):
#
#     provider_limit_readable          OpenRouter ``GET /key`` shows the key's own finite,
#                                      never-resetting limit (D-098 R8). Anthropic spend limits
#                                      (organisation or workspace, monthly) are set and enforced
#                                      in the Console but cannot be read with an API key.
#     per_call_cost_verification       OpenRouter generation metadata confirms each call's
#                                      serving provider, model and cost (D-092 P4). Anthropic
#                                      returns usage in the response only; there is no separate
#                                      per-call cost record.
#     provider_usage_reconciliation    the ledger is anchored on and reconciled against the key's
#                                      provider-reported usage (D-091 X5). Anthropic usage and
#                                      cost are readable only through the Admin API (an
#                                      organisation Admin key, never used here).
#
# D-099 Option B (owner-approved policy, NOT equivalent to OpenRouter) replaces them with
# Anthropic-specific safeguards, all in ``anthropic_runtime``: an owner-attested monthly limit
# of at most US$5 on a dedicated workspace, a separate Anthropic ledger (LEDGER_PROFILE_ID)
# with a non-resetting US$5 lifetime ceiling, US$1 a day, 20 calls per activation, in-band
# checks of the workspace, model and routing of every reply, and manual reconciliation against
# the Console. Until every one of them holds, both configurations stay unavailable.

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Literal

from .model_profiles import ApprovedEndpoint

DECISION_ID = "D-099"
PROVIDER = "ANTHROPIC"
BASE_URL = "https://api.anthropic.com"
API_VERSION = "2026-10-21"
MODEL_ID = "claude-sonnet-5-5"
MODEL_NAME = "Claude Sonnet 5.5"
# Standard (global) prices per million tokens, prompts up to any length; thinking is billed
# as output. Evidence: platform.claude.com pricing and models overview, read 2026-10-29, and
# the benchmark's reconciled spend (Console US$0.83 for both runs).
INPUT_USD_PER_MTOK = Decimal("2")
OUTPUT_USD_PER_MTOK = Decimal("10")
MAX_TOKENS = 3000
TIMEOUT_SECONDS = 90.0
# The provider-side controls a direct Anthropic key cannot give (see the header).
MISSING_CONTROLS = (
    "provider_limit_readable",
    "per_call_cost_verification",
    "provider_usage_reconciliation",
)

# The separate Anthropic ledger's profile (budget.PROFILES): both configurations share it.
LEDGER_PROFILE_ID = "anthropic_claude_sonnet_5_5"
# The record the unchanged budget guard reserves against: the worst case bounds the prompt by
# its bytes at the input price and every allowed output token (thinking is billed as output
# and counts towards ``max_tokens``) at the output price. No per-request price.
ENDPOINT = ApprovedEndpoint(
    slug="anthropic/claude-sonnet-5-5",
    prompt_price_per_m=INPUT_USD_PER_MTOK,
    completion_price_per_m=OUTPUT_USD_PER_MTOK,
    request_price=Decimal("0"),
    max_completion_tokens=MAX_TOKENS,
    max_tokens_includes_reasoning=True,
    slug_unique_for_model=True,
    evidence_date=date(2026, 10, 29),
)

Thinking = Literal["adaptive", "between_tools"]


@dataclass(frozen=True)
class ClaudeConfiguration:
    profile_id: str
    effort: str
    thinking: Thinking
    recommended: bool

    def request_fields(self) -> dict[str, Any]:
        # Everything sent besides the system blocks and messages: no sampling parameters,
        # tools, metadata, service tier, speed, inference geography or server-side fallback.
        return {
            "model": MODEL_ID,
            "max_tokens": MAX_TOKENS,
            "thinking": {"type": self.thinking},
            "output_config": {"effort": self.effort},
        }

    def identity(self) -> dict[str, Any]:
        # What a qualification of this configuration is tied to (never a credential).
        return {
            "profile": self.profile_id,
            "provider": PROVIDER,
            "base_url": BASE_URL,
            "api_version": API_VERSION,
            "request": self.request_fields(),
            "timeout_seconds": TIMEOUT_SECONDS,
            "prices": {"input": str(INPUT_USD_PER_MTOK), "output": str(OUTPUT_USD_PER_MTOK)},
        }


BALANCED = ClaudeConfiguration(
    profile_id="anthropic_claude_sonnet_5_5_medium",
    effort="medium",
    thinking="adaptive",
    recommended=True,
)
FAST = ClaudeConfiguration(
    profile_id="anthropic_claude_sonnet_5_5_low",
    effort="low",
    thinking="between_tools",
    recommended=False,
)
CONFIGURATIONS = MappingProxyType({item.profile_id: item for item in (BALANCED, FAST)})
PROFILE_IDS = frozenset(CONFIGURATIONS)


Status = Literal["pending_authorisation", "unavailable", "selectable"]


def availability(settings: Any) -> tuple[Status, str | None]:
    # (catalogue status, reason): selectable only when every Option B condition the runtime
    # checks without a network call or a key holds (anthropic_runtime.readiness).
    from . import anthropic_runtime  # the runtime imports this module

    reason = anthropic_runtime.readiness(settings)
    if reason == "ANTHROPIC_NOT_AUTHORISED":
        return "pending_authorisation", reason
    return ("selectable", None) if reason is None else ("unavailable", reason)
