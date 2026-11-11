"""What a hosted Stage A service must look like, checked before anything is opened.

The checks are additive. They never relax a gate in ``ai_assistant``. They make sure a hosted
process cannot satisfy the development-machine interlocks by accident, by refusing to start on
any setting that could open a remote path.

Refusals are closed codes. A value is never printed, because some of the inputs are secrets.
"""

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from ai_assistant.config import AiAssistantSettings
from ai_assistant.key_sources import ENV_FILE
from ai_assistant.llm import is_local_model_url

# The chat baseline points at the discard port on the container's own loopback. Nothing listens
# there, so every model call fails at once and the answer comes from the case data. Model
# management needs a baseline to open its state and audit store (model_admin.open_selector).
NO_MODEL_NAME = "no-model-configured"
NO_MODEL_URL = "http://127.0.0.1:9/v1"

# Settings that open a remote path. Stage A leaves every one of them empty.
REMOTE_SETTINGS = (
    "remote_inference_decision",
    "remote_live_decision",
    "openrouter_endpoint",
    "local_api_test_decision",
    "local_api_test_owner_attests",
    "synthetic_dev_decision",
    "anthropic_decision",
    "anthropic_owner_attests",
    "anthropic_workspace_id",
)
SECRET_VARIABLES = (
    "OPENROUTER_API_KEY",
    "AI_ASSISTANT_ANTHROPIC_API_KEY",
    "AI_ASSISTANT_LLM_API_KEY",
    "AI_ASSISTANT_MODEL_KEY_OLLAMA",
    "AI_ASSISTANT_MODEL_KEY_LM_STUDIO",
    "AI_ASSISTANT_MODEL_KEY_VLLM",
    "AI_ASSISTANT_MODEL_KEY_LOCAL",
)
PROXY_VARIABLES = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)


@dataclass(frozen=True)
class Limits:
    """Storage bounds the readiness check reports against."""

    data_quota_bytes: int
    min_free_bytes: int


def limits(environ: Mapping[str, str] | None = None) -> Limits:
    env = os.environ if environ is None else environ
    return Limits(
        data_quota_bytes=int(env.get("ASSISTANT_HOSTING_DATA_QUOTA_MB", "2048")) * 1024 * 1024,
        min_free_bytes=int(env.get("ASSISTANT_HOSTING_MIN_FREE_MB", "256")) * 1024 * 1024,
    )


def _https_origin(origin: str) -> bool:
    try:
        parts = urlsplit(origin)
        return (
            parts.scheme == "https"
            and bool(parts.hostname)
            and not parts.path
            and not parts.query
            and not parts.fragment
            and not parts.username
            and not parts.password
        )
    except ValueError:
        return False


def _profiles_empty(path: str) -> bool:
    # Model management must open, and must list no model of its own: any listed profile could
    # be an IT-configured endpoint, which is a route out of this service.
    try:
        with open(path, "rb") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and data.get("profiles") == []


def refusals(
    settings: AiAssistantSettings,
    environ: Mapping[str, str] | None = None,
    *,
    env_files: tuple[Path, ...] = (ENV_FILE, Path(".env")),
) -> list[str]:
    """Every reason this configuration may not run as a Stage A service (empty: it may)."""

    env = os.environ if environ is None else environ
    found: list[str] = []
    if not settings.data_dir:
        found.append("DATA_ROOT_REQUIRED")
    if not settings.llm_enabled or settings.llm_model != NO_MODEL_NAME:
        found.append("NO_MODEL_BASELINE_REQUIRED")
    if settings.llm_base_url != NO_MODEL_URL or not is_local_model_url(settings.llm_base_url):
        found.append("NO_MODEL_URL_REQUIRED")
    if settings.llm_profile != "local_openai_compatible":
        found.append("REMOTE_PROFILE_REFUSED")
    if settings.llm_warm_up:
        found.append("WARM_UP_REFUSED")
    if not is_local_model_url(settings.embed_base_url):
        found.append("EMBEDDINGS_MUST_BE_LOOPBACK")
    # A loopback backend URL or local origins would satisfy the development-machine interlock
    # (remote_test.readiness). Hosted values must never look like a development machine.
    backend = urlsplit(settings.clm_backend_url)
    if backend.scheme != "http" or not backend.hostname or backend.path not in ("", "/"):
        found.append("CLM_BACKEND_URL_INVALID")
    if is_local_model_url(settings.clm_backend_url) or backend.hostname == "localhost":
        found.append("CLM_BACKEND_LOOPBACK_REFUSED")
    if not settings.allowed_origins or not all(map(_https_origin, settings.allowed_origins)):
        found.append("HTTPS_ORIGIN_REQUIRED")
    if any(str(getattr(settings, name)).strip() for name in REMOTE_SETTINGS):
        found.append("REMOTE_SETTING_REFUSED")
    if (
        settings.anthropic_workspace_limit_micro_usd
        or settings.remote_low_reasoning_profile_enabled
    ):
        found.append("REMOTE_SETTING_REFUSED")
    if any(env.get(name) for name in SECRET_VARIABLES):
        found.append("PROVIDER_KEY_REFUSED")
    if any(env.get(name) for name in PROXY_VARIABLES):
        found.append("PROXY_SETTING_REFUSED")
    if any(path.exists() for path in env_files):
        found.append("ENV_FILE_REFUSED")
    if not settings.model_profiles_file or not _profiles_empty(settings.model_profiles_file):
        found.append("EMPTY_PROFILES_FILE_REQUIRED")
    return sorted(set(found))
