"""The one place that turns settings into a chat model (``ChatModel``).

The default profile returns exactly the adapter the service always built. The remote profile
is dormant (D-091) and refuses to compose unless every lock holds:

    L1  an in-memory mock transport is injected; or, for Phase B only (D-092, proposed), the
        caller sets ``allow_live_network`` to True AND AI_ASSISTANT_REMOTE_LIVE_DECISION names
        the live decision. Only the evaluation harness passes that argument (its cases are
        synthetic fixtures served by a mock CLM backend); the service never does, so a running
        service cannot reach the network whatever its settings say.
    L2  the registry holds an approved endpoint record for the selected endpoint slug,
        and that slug was shown to identify exactly one endpoint of the model
    L3  AI_ASSISTANT_REMOTE_INFERENCE_DECISION equals the recorded decision id
    L4  an initialised, healthy budget ledger exists (see ``budget.py``)

Every refusal is a ``ProfileConfigError`` with a closed code and a message that names the
setting, never its value. ``OPENROUTER_API_KEY`` is read last, only for the remote profile,
only after all other checks pass: from the process environment, else (D-095 addendum) the
git-ignored apps/assistant/.env, else a key an HR administrator entered (memory only); see
``key_sources.py``.
"""

import math
import os
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path

from pydantic import SecretStr

from . import key_sources
from .budget import LEASE_GRACE_SECONDS, BudgetedChatModel, BudgetLedger, LedgerError
from .config import AiAssistantSettings
from .llm import ChatModel, OpenAICompatibleChatModel, is_local_model_url
from .model_profiles import (
    APPROVED_PROFILES,
    ENDPOINT_SLUG,
    LIVE_DECISION_ID,
    MAX_REMOTE_TOKENS,
    MIN_REASONING_ALLOWANCE,
    OPENROUTER_PROFILE_ID,
    REMOTE_DECISION_ID,
    ModelProfile,
    ProfileConfigError,
)
from .openrouter import LIVE_NETWORK, OpenRouterChatModel, require_offline_transport
from .openrouter_account import OpenRouterAccount

CREDENTIAL_VARIABLE = key_sources.CREDENTIAL_VARIABLE
_DEFAULTS = AiAssistantSettings.model_fields
ASSISTANT_DIR = Path(__file__).resolve().parents[1]


def ledger_path(settings: AiAssistantSettings) -> Path:
    """The ledger file, relative to apps/assistant unless absolute (git-ignored data/)."""

    path = Path(settings.budget_ledger_path)
    return path if path.is_absolute() else ASSISTANT_DIR / path


# Numeric settings the remote profile uses, re-checked against their declared bounds because
# settings built with ``model_construct`` skip pydantic's own checks.
_BOUNDED = (
    "llm_timeout_seconds",
    "llm_temperature",
    "llm_max_answer_tokens",
    "llm_reasoning_allowance_tokens",
    "remote_max_prompt_bytes",
    "budget_max_in_flight",
    "budget_settle_lag_seconds",
    "budget_daily_cap_micro_usd",
)


def _within_declared_bounds(settings: AiAssistantSettings, name: str) -> bool:
    field = _DEFAULTS[name]
    value = getattr(settings, name)
    expected = type(field.default)
    if isinstance(value, bool) or not isinstance(value, expected | int):
        return False
    if expected is int and not isinstance(value, int):
        return False
    if not math.isfinite(value):
        return False
    for bound in field.metadata:  # pydantic's Gt/Ge/Lt/Le markers from Field(...)
        gt, ge = getattr(bound, "gt", None), getattr(bound, "ge", None)
        lt, le = getattr(bound, "lt", None), getattr(bound, "le", None)
        if (gt is not None and not value > gt) or (ge is not None and not value >= ge):
            return False
        if (lt is not None and not value < lt) or (le is not None and not value <= le):
            return False
    return True


def resolve_remote_credential(environ: Mapping[str, str] | None = None) -> SecretStr:
    """The remote key (``key_sources.resolve``), checked offline for shape only. ``environ``
    given: that mapping only (tests and seams)."""

    key, _ = key_sources.resolve(environ)
    if key is None:
        raise ProfileConfigError(
            "CREDENTIAL_MISSING",
            f"{CREDENTIAL_VARIABLE} is missing or malformed for the remote profile",
        )
    return key


PROXY_VARIABLES = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)


def require_direct_loopback(base_url: str, environ: Mapping[str, str] | None = None) -> None:
    """A local model must be a literal loopback URL reached without any proxy, so the prompt
    cannot leave the machine. Used by the evaluation harness and by model management (D-093).
    The adapter's HTTP client also honours system proxies (the Windows registry and macOS
    settings, through urllib), so those must be empty too when the real environment is used."""

    if not is_local_model_url(base_url):
        raise ProfileConfigError(
            "NOT_LOOPBACK", "only a literal loopback model URL may be evaluated"
        )
    env = os.environ if environ is None else environ
    if any(env.get(name) for name in PROXY_VARIABLES):
        raise ProfileConfigError(
            "PROXY_CONFIGURED", "unset proxy variables before evaluating a local model"
        )
    if environ is None and any(
        value
        for scheme, value in urllib.request.getproxies().items()
        if scheme in ("http", "https", "all")
    ):
        raise ProfileConfigError(
            "PROXY_CONFIGURED", "remove system proxies before evaluating a local model"
        )


def _live_or_mock(settings: AiAssistantSettings, transport: object, allow_live: bool) -> object:
    """L1 for both the model and the account checks: a mock transport, or the live marker
    when the caller asked for it and the live decision is named (never both)."""

    if allow_live is True:
        if transport is not None:
            raise ProfileConfigError(
                "TRANSPORT_NOT_ALLOWED", "a live run must not also inject a transport"
            )
        if settings.remote_live_decision != LIVE_DECISION_ID:
            raise ProfileConfigError(
                "LIVE_INTERLOCK",
                "AI_ASSISTANT_REMOTE_LIVE_DECISION does not name the required decision",
            )
        return LIVE_NETWORK
    if transport is None:
        raise ProfileConfigError(
            "PROFILE_DORMANT", "the remote profile is dormant and cannot reach a network"
        )
    require_offline_transport(transport)
    return transport


def _local(settings: AiAssistantSettings, adapter: Callable[..., ChatModel]) -> ChatModel:
    return adapter(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        credential=settings.llm_api_key.get_secret_value(),
        timeout_seconds=settings.llm_timeout_seconds,
        temperature=settings.llm_temperature,
        max_answer_tokens=settings.llm_max_answer_tokens,
    )


def _remote(
    settings: AiAssistantSettings,
    profile: ModelProfile,
    *,
    transport: object,
    environ: Mapping[str, str] | None,
    budget_ledger: Path | None,
    allow_live_network: bool,
) -> ChatModel:
    # L1: an in-memory mock transport, or the Phase B live gate (both halves, never both modes).
    transport = _live_or_mock(settings, transport, allow_live_network)
    for name in _BOUNDED:
        if not _within_declared_bounds(settings, name):
            raise ProfileConfigError(
                "SETTING_OUT_OF_BOUNDS", f"AI_ASSISTANT_{name.upper()} is outside its bounds"
            )
    if settings.llm_base_url != _DEFAULTS["llm_base_url"].default:
        raise ProfileConfigError(
            "BASE_URL_OVERRIDE", "AI_ASSISTANT_LLM_BASE_URL must not be set for the remote profile"
        )
    if settings.llm_model != _DEFAULTS["llm_model"].default:
        raise ProfileConfigError(
            "MODEL_OVERRIDE", "AI_ASSISTANT_LLM_MODEL must not be set for the remote profile"
        )
    # L3: a deliberate operator act naming the decision that would allow remote inference.
    if settings.remote_inference_decision != REMOTE_DECISION_ID:
        raise ProfileConfigError(
            "DECISION_INTERLOCK",
            "AI_ASSISTANT_REMOTE_INFERENCE_DECISION does not name the required decision",
        )
    # L2: exactly one approved endpoint, identified by its full slug.
    slug = settings.openrouter_endpoint
    if not ENDPOINT_SLUG.fullmatch(slug):
        raise ProfileConfigError(
            "ENDPOINT_SLUG_INVALID", "AI_ASSISTANT_OPENROUTER_ENDPOINT is not one endpoint slug"
        )
    endpoint = profile.endpoint(slug)
    if endpoint is None:
        raise ProfileConfigError(
            "ENDPOINT_NOT_APPROVED", "AI_ASSISTANT_OPENROUTER_ENDPOINT is not an approved endpoint"
        )
    if not endpoint.slug_unique_for_model:
        raise ProfileConfigError(
            "ENDPOINT_NOT_UNIQUE", "the endpoint slug is not shown to identify one endpoint"
        )
    if settings.llm_reasoning_effort not in profile.capabilities.reasoning_efforts:
        raise ProfileConfigError(
            "REASONING_EFFORT_INVALID", "AI_ASSISTANT_LLM_REASONING_EFFORT is not supported"
        )
    allowance = settings.llm_reasoning_allowance_tokens
    if allowance < MIN_REASONING_ALLOWANCE:
        raise ProfileConfigError(
            "REASONING_ALLOWANCE_INVALID",
            "AI_ASSISTANT_LLM_REASONING_ALLOWANCE_TOKENS is below the minimum",
        )
    if settings.llm_max_answer_tokens + allowance > min(
        MAX_REMOTE_TOKENS, endpoint.max_completion_tokens
    ):
        raise ProfileConfigError(
            "MAX_TOKENS_TOO_LARGE", "answer tokens plus the reasoning allowance are too large"
        )
    # L4: an initialised, healthy lifetime ledger. It is never created here.
    try:
        ledger = BudgetLedger.open(budget_ledger or ledger_path(settings))
        ledger_profile = ledger.status().profile_id
    except LedgerError:
        raise ProfileConfigError(
            "LEDGER_UNAVAILABLE", "the remote profile needs an initialised, healthy budget ledger"
        ) from None
    if ledger_profile != profile.profile_id:
        raise ProfileConfigError("LEDGER_UNAVAILABLE", "the budget ledger is for another profile")
    credential = resolve_remote_credential(environ)
    adapter = OpenRouterChatModel(
        endpoint=endpoint,
        credential=credential,
        timeout_seconds=settings.llm_timeout_seconds,
        temperature=settings.llm_temperature,
        answer_tokens=settings.llm_max_answer_tokens,
        reasoning_effort=settings.llm_reasoning_effort,
        reasoning_allowance_tokens=allowance,
        max_prompt_bytes=settings.remote_max_prompt_bytes,
        transport=transport,
    )
    # A remote model is never returned without its budget guard.
    return BudgetedChatModel(
        adapter,
        ledger,
        max_in_flight=settings.budget_max_in_flight,
        lease_seconds=settings.llm_timeout_seconds + LEASE_GRACE_SECONDS,
        daily_cap_micro_usd=settings.budget_daily_cap_micro_usd,
    )


def build_chat_model(
    settings: AiAssistantSettings,
    *,
    local_adapter: Callable[..., ChatModel] = OpenAICompatibleChatModel,
    transport: object = None,
    environ: Mapping[str, str] | None = None,
    registry: Mapping[str, ModelProfile] = APPROVED_PROFILES,
    budget_ledger: Path | None = None,
    allow_live_network: bool = False,
) -> ChatModel:
    """The configured chat model. Validation runs here, not only in pydantic, because some
    callers build settings without validators (``model_construct``).

    ``local_adapter`` is the default profile's adapter class (the service passes its own
    reference, so the default composition is exactly what it always was).
    ``allow_live_network`` is for the evaluation harness only (see L1 above)."""

    profile = registry.get(settings.llm_profile)
    if profile is None:
        raise ProfileConfigError(
            "PROFILE_UNKNOWN", "AI_ASSISTANT_LLM_PROFILE is not a known profile"
        )
    if profile.adapter == "openai_compatible":
        return _local(settings, local_adapter)
    return _remote(
        settings,
        profile,
        transport=transport,
        environ=environ,
        budget_ledger=budget_ledger,
        allow_live_network=allow_live_network,
    )


def build_account_client(
    settings: AiAssistantSettings,
    *,
    transport: object = None,
    environ: Mapping[str, str] | None = None,
    allow_live_network: bool = False,
) -> OpenRouterAccount:
    """Phase B read-only account checks (key limit, generation metadata), behind the same
    profile, decision and live interlocks as the remote model; the key is read last."""

    if settings.llm_profile != OPENROUTER_PROFILE_ID:
        raise ProfileConfigError(
            "PROFILE_UNKNOWN", "AI_ASSISTANT_LLM_PROFILE is not the remote profile"
        )
    transport = _live_or_mock(settings, transport, allow_live_network)
    if settings.remote_inference_decision != REMOTE_DECISION_ID:
        raise ProfileConfigError(
            "DECISION_INTERLOCK",
            "AI_ASSISTANT_REMOTE_INFERENCE_DECISION does not name the required decision",
        )
    credential = resolve_remote_credential(environ)
    return OpenRouterAccount(credential, transport=transport)
