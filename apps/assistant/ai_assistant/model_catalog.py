"""The models an HR administrator may choose from (D-093, local loopback models only).

    env_default       the model configured by AI_ASSISTANT_LLM_* (today's behaviour): always
                      listed, the baseline, and the model restored when anything is wrong
    file profiles     written by IT in the server-side JSON file named by
                      AI_ASSISTANT_MODEL_PROFILES_FILE; a profile is selectable only when its
                      URL is a literal loopback address
    remote profiles   the code-defined remote profile (D-091 dormant; D-092 proposed for the
                      synthetic evaluation only): listed as pending authorisation, never usable,
                      unless the D-094 local synthetic test mode is configured (remote_test.py);
                      then selectable, and the chat uses it only on the approved synthetic
                      test case (synthetic_boundary.py), or (D-095) on verified synthetic
                      development cases. With
                      AI_ASSISTANT_REMOTE_LOW_REASONING_PROFILE_ENABLED a second configuration
                      of the same model is listed: reasoning effort low, with its own profile
                      id and fingerprint, so it needs its own qualification

The file holds no credential: a profile may name one environment variable from the reviewed
allowlist below, read on the server when the model is built and never shown or stored. The
browser only ever sends a profile id; it cannot supply a URL, model, key or parameter.
"""

import hashlib
import json
import os
import re
from collections.abc import AsyncGenerator, Mapping
from contextlib import aclosing
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from . import remote_test, synthetic_eligibility
from .config import AiAssistantSettings
from .llm import (
    ModelAnswer,
    ModelCallError,
    OpenAICompatibleChatModel,
    Piece,
    is_local_model_url,
    message_bytes,
)
from .model_factory import ASSISTANT_DIR, require_direct_loopback
from .model_profiles import APPROVED_PROFILES, LOCAL_PROFILE_ID, ProfileConfigError

BASELINE_ID = "env_default"
SCHEMA = "clm-assistant-model-profiles/1"
PROFILE_ID = r"^[a-z0-9][a-z0-9_-]{2,47}$"
# The model id a server expects, as Ollama, LM Studio and vLLM write them.
MODEL_ID = r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}$"
# Reviewed allowlist (owner decision 2, D-093): the only environment variables a profile may
# name for its key. Never OPENROUTER_API_KEY or any other secret.
CREDENTIAL_VARIABLES = frozenset(
    {
        "AI_ASSISTANT_MODEL_KEY_OLLAMA",
        "AI_ASSISTANT_MODEL_KEY_LM_STUDIO",
        "AI_ASSISTANT_MODEL_KEY_VLLM",
        "AI_ASSISTANT_MODEL_KEY_LOCAL",
    }
)
_CREDENTIAL = re.compile(r"[\x21-\x7e]{1,256}")
# Sent when a profile names no key (local servers ignore it), as the harness does.
NO_CREDENTIAL = "local"
MAX_FILE_BYTES = 64 * 1024
MAX_PROFILES = 20
# Per-message template allowance (role markers and separators) in the prompt-size bound.
MESSAGE_OVERHEAD_TOKENS = 16

Status = Literal["selectable", "unavailable", "pending_authorisation", "disabled"]


class LocalProfile(BaseModel):
    """One IT-written local model profile. Unknown fields are refused, so a key cannot be
    written into the file under another name."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    profile_id: str = Field(pattern=PROFILE_ID)
    display_name: str = Field(min_length=1, max_length=80)
    deployment: Literal["ollama", "lm_studio", "vllm", "openai_compatible"]
    base_url: str = Field(min_length=1, max_length=200)
    model_id: str = Field(pattern=MODEL_ID)
    model_version: str | None = Field(default=None, min_length=1, max_length=64)
    # What IT says the server holds. Qualification checks it against the server's own token
    # counts before the model can be activated; it is never trusted on its own.
    context_window_tokens: int = Field(ge=2048, le=1_048_576)
    max_answer_tokens: int = Field(default=600, ge=16, le=4000)
    temperature: float = Field(default=0.2, ge=0, le=1)
    timeout_seconds: float = Field(default=90.0, gt=0, le=600)
    streaming: bool = True
    credential_env: str | None = None
    enabled: bool = True

    @field_validator("display_name", "model_version")
    @classmethod
    def _printable(cls, value: str | None) -> str | None:
        if value is not None and not value.isprintable():
            raise ValueError("must be printable text")
        return value

    @field_validator("credential_env")
    @classmethod
    def _allowlisted(cls, value: str | None) -> str | None:
        if value is not None and value not in CREDENTIAL_VARIABLES:
            raise ValueError("is not an allowlisted variable name")
        return value


class ProfilesFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_: Literal["clm-assistant-model-profiles/1"] = Field(alias="schema")
    profiles: list[LocalProfile] = Field(max_length=MAX_PROFILES)

    @field_validator("profiles")
    @classmethod
    def _unique(cls, value: list[LocalProfile]) -> list[LocalProfile]:
        ids = [item.profile_id for item in value]
        if len(set(ids)) != len(ids):
            raise ValueError("profile ids must be unique")
        # D-098: also the no-model state and the Fast configuration (listed or not).
        reserved = {BASELINE_ID, CASE_DATA_ONLY_ID, OPENROUTER_FAST_PROFILE_ID, *APPROVED_PROFILES}
        if reserved & set(ids):
            raise ValueError("a profile id is reserved")
        return value


def fingerprint(values: Mapping[str, object]) -> str:
    """SHA-256 of a profile's validated settings (never a credential value)."""

    return hashlib.sha256(
        json.dumps(values, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def endpoint_label(base_url: str) -> str | None:
    """``host:port`` of a loopback URL; nothing for any other URL (it is not shown)."""

    if not is_local_model_url(base_url):
        return None
    parts = urlsplit(base_url)
    return parts.netloc


@dataclass(frozen=True)
class CatalogueEntry:
    profile_id: str
    display_name: str
    source: Literal["environment", "file", "code"]
    deployment: str
    model_id: str | None
    model_version: str | None
    endpoint: str | None
    context_window_tokens: int | None
    max_answer_tokens: int | None
    temperature: float | None
    timeout_seconds: float | None
    streaming: bool
    fingerprint: str
    status: Status
    reason: str | None
    profile: LocalProfile | None = None
    # Remote configurations only: what the page shows about the model, and the settings this
    # configuration changes from the service's (empty for the configured one).
    details: tuple[tuple[str, str], ...] = ()
    settings_update: tuple[tuple[str, object], ...] = ()

    @property
    def base_url(self) -> str | None:
        return self.profile.base_url if self.profile is not None else None

    def view(self) -> dict[str, object]:
        """What the page shows: no URL path, no credential (not even its variable name)."""

        return {
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "source": self.source,
            "deployment": self.deployment,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "endpoint": self.endpoint,
            "context_window_tokens": self.context_window_tokens,
            "max_answer_tokens": self.max_answer_tokens,
            "temperature": self.temperature,
            "timeout_seconds": self.timeout_seconds,
            "streaming": self.streaming,
            "fingerprint": self.fingerprint[:12],
            "status": self.status,
            "reason": self.reason,
            "details": dict(self.details) if self.details else None,
        }

    def settings_for(self, settings: AiAssistantSettings) -> AiAssistantSettings:
        """The service's settings as this configuration runs (its own reasoning effort)."""

        return (
            settings.model_copy(update=dict(self.settings_update))
            if self.settings_update
            else settings
        )


@dataclass(frozen=True)
class Catalogue:
    configured: bool
    file_status: Literal["not_configured", "ok", "missing", "invalid"]
    file_errors: tuple[str, ...]
    entries: tuple[CatalogueEntry, ...]

    def get(self, profile_id: str) -> CatalogueEntry | None:
        return next((item for item in self.entries if item.profile_id == profile_id), None)


def baseline_fingerprint(settings: AiAssistantSettings) -> str:
    return fingerprint(
        {
            "profile": settings.llm_profile,
            "base_url": settings.llm_base_url,
            "model": settings.llm_model,
            "temperature": settings.llm_temperature,
            "max_answer_tokens": settings.llm_max_answer_tokens,
            "timeout_seconds": settings.llm_timeout_seconds,
        }
    )


def baseline_entry(settings: AiAssistantSettings) -> CatalogueEntry:
    local = settings.llm_profile == LOCAL_PROFILE_ID
    return CatalogueEntry(
        profile_id=BASELINE_ID,
        display_name="Environment baseline",
        source="environment",
        deployment="openai_compatible",
        model_id=settings.llm_model if local else None,
        model_version=None,
        endpoint=endpoint_label(settings.llm_base_url) if local else None,
        context_window_tokens=None,
        max_answer_tokens=settings.llm_max_answer_tokens,
        temperature=settings.llm_temperature,
        timeout_seconds=settings.llm_timeout_seconds,
        streaming=True,
        fingerprint=baseline_fingerprint(settings),
        status="selectable" if settings.llm_enabled else "disabled",
        reason=None if settings.llm_enabled else "MODEL_DISABLED_BY_ENVIRONMENT",
    )


# A second configuration of the remote model, reasoning effort low (same model, endpoint, key
# and limits). The page names the efforts; the server sends only the effort and closed codes.
OPENROUTER_FAST_PROFILE_ID = "openrouter_gpt_oss_120b_low"
# D-098 (owner: GPT-OSS only, no substitute model): what a GPT-OSS activation that can no
# longer be used reverts to. No model at all: every answer is the case-data answer. It is
# stored like an activation (audited, kept across restarts) until HR activates a model.
CASE_DATA_ONLY_ID = "case_data_only"
FAST_REASONING_EFFORT = "low"
MODEL_NAME = "GPT-OSS 120B"


def _remote_details(
    settings: AiAssistantSettings, *, authorised: bool
) -> tuple[tuple[str, str], ...]:
    """What the page shows about the remote model, as closed codes and plain values."""

    if not authorised:
        return (
            ("model", MODEL_NAME),
            ("provider", "OPENROUTER_DEEPINFRA"),
            ("scope", "NOT_AUTHORISED"),
        )
    development = synthetic_eligibility.mode(settings)
    return (
        ("model", MODEL_NAME),
        ("provider", "OPENROUTER_DEEPINFRA"),
        ("scope", "VERIFIED_SYNTHETIC_CASES" if development else "APPROVED_SYNTHETIC_CASE"),
        ("reasoning_effort", settings.llm_reasoning_effort or ""),
        ("decision", "D-095" if development else "D-094"),
    )


def _remote_name(settings: AiAssistantSettings) -> str:
    effort = settings.llm_reasoning_effort
    return f"{MODEL_NAME} (reasoning {effort})" if effort else MODEL_NAME


def _remote_entries(settings: AiAssistantSettings) -> tuple[CatalogueEntry, ...]:
    entries = []
    for profile in APPROVED_PROFILES.values():
        if profile.boundary != "external":
            continue
        problem = remote_test.readiness(settings)
        if problem == "REMOTE_NOT_AUTHORISED":
            # Today's entry, unchanged: D-091 dormant, D-092 synthetic evaluation only.
            entries.append(
                CatalogueEntry(
                    profile_id=profile.profile_id,
                    display_name=MODEL_NAME,
                    source="code",
                    deployment="remote",
                    model_id=profile.model_id,
                    model_version=None,
                    endpoint=None,
                    context_window_tokens=None,
                    max_answer_tokens=None,
                    temperature=None,
                    timeout_seconds=None,
                    streaming=profile.capabilities.streaming,
                    fingerprint=fingerprint({"profile": profile.profile_id}),
                    status="pending_authorisation",
                    reason="REMOTE_NOT_AUTHORISED",
                    details=_remote_details(settings, authorised=False),
                )
            )
            continue
        # D-094 local synthetic test mode (D-095: verified synthetic development cases).
        configurations: list[tuple[str, AiAssistantSettings, tuple[tuple[str, object], ...]]] = [
            (profile.profile_id, settings, ())
        ]
        if (
            settings.remote_low_reasoning_profile_enabled
            and settings.llm_reasoning_effort != FAST_REASONING_EFFORT
        ):
            low: tuple[tuple[str, object], ...] = (("llm_reasoning_effort", FAST_REASONING_EFFORT),)
            configurations.append(
                (OPENROUTER_FAST_PROFILE_ID, settings.model_copy(update=dict(low)), low)
            )
        for profile_id, variant, update in configurations:
            problem = remote_test.readiness(variant)
            entries.append(
                CatalogueEntry(
                    profile_id=profile_id,
                    display_name=_remote_name(variant),
                    source="code",
                    deployment="openrouter",
                    model_id=profile.model_id,
                    model_version=variant.llm_reasoning_effort or None,
                    endpoint=f"openrouter.ai · {variant.openrouter_endpoint or '—'}",
                    context_window_tokens=None,
                    max_answer_tokens=variant.llm_max_answer_tokens,
                    temperature=variant.llm_temperature,
                    timeout_seconds=variant.llm_timeout_seconds,
                    streaming=profile.capabilities.streaming,
                    # The reasoning effort is part of it: Fast never matches the configured one.
                    fingerprint=remote_test.remote_fingerprint(variant),
                    status="selectable" if problem is None else "unavailable",
                    reason=problem,
                    details=_remote_details(variant, authorised=True),
                    settings_update=update,
                )
            )
    return tuple(entries)


def _file_entry(profile: LocalProfile) -> CatalogueEntry:
    status: Status = "selectable"
    reason = None
    if not profile.enabled:
        status, reason = "disabled", "PROFILE_DISABLED"
    elif not is_local_model_url(profile.base_url):
        # Owner decision 3 (D-093): selectable models are literal loopback only.
        status, reason = "unavailable", "NOT_LOOPBACK"
    elif not profile.streaming:
        status, reason = "unavailable", "STREAMING_REQUIRED"
    return CatalogueEntry(
        profile_id=profile.profile_id,
        display_name=profile.display_name,
        source="file",
        deployment=profile.deployment,
        model_id=profile.model_id,
        model_version=profile.model_version,
        endpoint=endpoint_label(profile.base_url),
        context_window_tokens=profile.context_window_tokens,
        max_answer_tokens=profile.max_answer_tokens,
        temperature=profile.temperature,
        timeout_seconds=profile.timeout_seconds,
        streaming=profile.streaming,
        fingerprint=fingerprint(profile.model_dump()),
        status=status,
        reason=reason,
        profile=profile,
    )


def profiles_path(settings: AiAssistantSettings) -> Path | None:
    if not settings.model_profiles_file:
        return None
    path = Path(settings.model_profiles_file)
    return path if path.is_absolute() else ASSISTANT_DIR / path


def _error_fields(error: ValidationError) -> tuple[str, ...]:
    """Where the file is wrong (field paths only; never the values)."""

    fields = {".".join(str(part) for part in item["loc"]) or "file" for item in error.errors()}
    return tuple(sorted(fields))[:20]


def load_catalogue(settings: AiAssistantSettings) -> Catalogue:
    """Every model the page lists. A broken file lists no file profile (never part of one)."""

    fixed = (baseline_entry(settings), *_remote_entries(settings))
    path = profiles_path(settings)
    if path is None:
        return Catalogue(False, "not_configured", (), fixed)
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_FILE_BYTES + 1)
    except FileNotFoundError:
        return Catalogue(True, "missing", (), fixed)
    except OSError:
        return Catalogue(True, "invalid", ("file",), fixed)
    if len(raw) > MAX_FILE_BYTES:
        return Catalogue(True, "invalid", ("file_size",), fixed)
    try:
        parsed = ProfilesFile.model_validate_json(raw)
    except ValidationError as exc:
        return Catalogue(True, "invalid", _error_fields(exc), fixed)
    return Catalogue(True, "ok", (), (*fixed[:1], *map(_file_entry, parsed.profiles), *fixed[1:]))


def resolve_credential(profile: LocalProfile, environ: Mapping[str, str] | None = None) -> str:
    """The profile's key from the process environment, read only here and never returned
    to a caller outside the adapter."""

    if profile.credential_env is None:
        return NO_CREDENTIAL
    if profile.credential_env not in CREDENTIAL_VARIABLES:  # also checked by the schema
        raise ProfileConfigError("CREDENTIAL_NOT_ALLOWED", "credential_env is not allowlisted")
    value = (os.environ if environ is None else environ).get(profile.credential_env)
    if not isinstance(value, str) or not _CREDENTIAL.fullmatch(value):
        raise ProfileConfigError(
            "CREDENTIAL_MISSING", f"{profile.credential_env} is missing or malformed"
        )
    return value


def build_profile_model(
    entry: CatalogueEntry,
    *,
    environ: Mapping[str, str] | None = None,
    transport: object = None,
) -> OpenAICompatibleChatModel:
    """The service's own adapter for a selectable file profile, after the loopback and proxy
    rule the evaluation harness uses (model_factory.require_direct_loopback)."""

    profile = entry.profile
    if profile is None or entry.status != "selectable":
        raise ProfileConfigError("PROFILE_NOT_SELECTABLE", "the profile is not selectable")
    require_direct_loopback(profile.base_url, environ)
    return OpenAICompatibleChatModel(
        base_url=profile.base_url,
        model=profile.model_id,
        credential=resolve_credential(profile, environ),
        timeout_seconds=profile.timeout_seconds,
        temperature=profile.temperature,
        max_answer_tokens=profile.max_answer_tokens,
        transport=transport,  # type: ignore[arg-type]  # tests only
    )


def build_baseline_adapter(
    settings: AiAssistantSettings,
    *,
    environ: Mapping[str, str] | None = None,
    transport: object = None,
    loopback: bool = False,
) -> OpenAICompatibleChatModel:
    """A second adapter for the environment baseline, for its connection test and (when it is
    a literal loopback URL, ``loopback``) its qualification. The service's own baseline model
    is built once at start-up and never replaced."""

    if settings.llm_profile != LOCAL_PROFILE_ID:
        raise ProfileConfigError("PROFILE_NOT_SELECTABLE", "the baseline is not a local profile")
    if loopback:
        require_direct_loopback(settings.llm_base_url, environ)
    return OpenAICompatibleChatModel(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        credential=settings.llm_api_key.get_secret_value(),
        timeout_seconds=settings.llm_timeout_seconds,
        temperature=settings.llm_temperature,
        max_answer_tokens=settings.llm_max_answer_tokens,
        transport=transport,  # type: ignore[arg-type]  # tests only
    )


def fits(messages: list[dict[str, str]], limit: int) -> bool:
    """Whether a prompt is inside the verified bound. UTF-8 bytes bound the content tokens for
    byte-level tokenizers; qualification confirms that for the model before it is used."""

    return message_bytes(messages) + MESSAGE_OVERHEAD_TOKENS * len(messages) <= limit


class BoundedPromptModel:
    """An activated file profile: refuses (as an unavailable model, so the RM gets the
    deterministic case-data answer) any prompt larger than the capacity its qualification
    verified. The baseline is never wrapped; its behaviour is unchanged."""

    def __init__(self, inner: OpenAICompatibleChatModel, prompt_limit: int) -> None:
        self._inner = inner
        self._limit = prompt_limit

    @property
    def name(self) -> str:
        return self._inner.name

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        if not fits(messages, self._limit):
            raise ModelCallError("prompt_too_large")
        return self._inner.complete(messages)

    async def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Piece, None]:
        if not fits(messages, self._limit):
            raise ModelCallError("prompt_too_large")
        # Closing this stream closes the adapter's, which releases the model connection.
        async with aclosing(self._inner.stream(messages)) as source:
            async for piece in source:
                yield piece

    def warm(self, messages: list[dict[str, str]]) -> None:
        if fits(messages, self._limit):
            self._inner.warm(messages)
