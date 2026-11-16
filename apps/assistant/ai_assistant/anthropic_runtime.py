# D-099 Option B (PROPOSED): Claude Sonnet 5.5 in the CLM's own chat, gated per call.
#
# NOT equivalent to the OpenRouter controls. A direct Anthropic key cannot read its spend limit,
# has no per-call cost record and cannot read provider usage without an organisation Admin key
# (anthropic_profiles.MISSING_CONTROLS). The owner approved these Anthropic-specific
# safeguards instead, for verified synthetic development cases only (the same cases GPT-OSS may
# answer: main.py applies the D-094/D-095 boundary to this model unchanged), never real data.
# Nothing here changes the GPT-OSS gate (remote_test.py), its ledger or its HR controls.
#
# D-107: an HR administrator enables Claude in AI Models (model_admin_store's
# anthropic_enablement row): the Anthropic workspace the key itself reported, its monthly limit
# as the owner confirmed it and the four owner confirmations, kept with an audit row. While
# that row exists it replaces the decision and attestation settings below, and the D-091,
# D-092 and D-094 decision names are not needed: the runtime checks they stood for still apply
# (the model switched on, a literal loopback CLM backend and local browser origins). Without
# the row the environment configuration below applies unchanged. Either way, off unless:
#
#
#     decision     AI_ASSISTANT_ANTHROPIC_DECISION names D-099, on top of the D-094 local test
#                  decision and the D-091 and D-092 decisions the remote profile needs
#     environment  a development machine (as remote_test: loopback backend, local origins)
#     owner        AI_ASSISTANT_ANTHROPIC_OWNER_ATTESTS holds exactly OWNER_ATTESTATIONS
#     workspace    the dedicated workspace's id and its monthly limit (at most US$30.00, D-102)
#     limits       at most US$5.00 a day, 20 calls and 32 KiB prompts (policy ceilings,
#                  re-checked here because ``model_construct`` skips pydantic's bounds); an HR
#                  administrator may set the daily allowance and calls within them (D-102)
#
# Every call then also needs (``ClaudeTestModel``):
#
#     admission    the D-095 eligibility ticket (development mode) or the D-094 text check, and
#                  the adapter decides again for the very messages it sends (QG F2)
#     key          D-106: an inference key an HR administrator entered for their own signed-in
#                  session (memory only, checked against that session for every call), else
#                  AI_ASSISTANT_ANTHROPIC_API_KEY from the process environment, else the
#                  git-ignored .env; an Admin key or any other shape refuses. A key change
#                  rebuilds the adapter and re-runs the network preflight, so any key must
#                  name the attested workspace before it is used.
#     ledger       the separate Anthropic ledger: its own profile, breaker closed, no open call,
#                  every earlier call verified, a cap of at most the lower of US$30.00
#                  (lifetime, never reset; D-102) and the workspace limit, and room for one
#                  worst-case reservation in it and in today's allowance (Asia/Singapore day)
#     reconciled   the operator anchored it on the Console's workspace usage within 7 days
#                  (chat) or 24 hours (paid qualification, activation, a cap raise)
#     preflight    a free ``GET /v1/models/claude-sonnet-5-5`` whose reply names the attested
#                  workspace and the model, reused for AI_ASSISTANT_LOCAL_API_TEST_PREFLIGHT_SECONDS
#
# Each reply must name the attested workspace (response header) and the pinned model before any
# text, with a standard tier, geography and speed (anthropic_chat.py). After each call the call
# is verified in-band: settled from complete reported usage with no anomaly; otherwise it is
# quarantined and the breaker opens until the operator reconciles (scripts/budget_ledger.py).
# Uncertain calls are charged at their full reservation. There is never an automatic switch to
# GPT-OSS or any other model.
#
# Residual risks (owner-accepted): the workspace limit and its id's dedication are attested,
# not read; a reply's usage is the provider's own claim with no separate record; Console usage
# lags and is reconciled by hand, so drift can exist for up to the reconciliation window
# (bounded by the daily cap, the lifetime ceiling and the workspace limit Anthropic enforces).

import hashlib
import json
import logging
import os
import re
import sqlite3
import threading
import time
from collections.abc import AsyncGenerator, Callable, Mapping
from contextlib import aclosing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import urlsplit

import anyio
import httpx
from pydantic import SecretStr

from . import anthropic_profiles, key_sources, remote_test, synthetic_eligibility
from . import config as assistant_config
from .anthropic_chat import (
    LIVE_NETWORK,
    WORKSPACE_HEADER,
    AnthropicChatModel,
    PromptShapeError,
    system_and_conversation,
)
from .anthropic_profiles import ENDPOINT, LEDGER_PROFILE_ID, MODEL_ID
from .budget import (
    ANOMALY_BITS,
    LEASE_GRACE_SECONDS,
    BudgetedChatModel,
    BudgetLedger,
    ClosedCall,
    LedgerError,
    next_singapore_reset_ms,
)
from .config import AiAssistantSettings, external_conversational
from .llm import (
    ROUTING_ANOMALIES,
    ChatModel,
    LlmUnavailableError,
    ModelAnswer,
    ModelCallError,
    Piece,
    is_local_model_url,
)
from .model_admin_store import AnthropicEnablement, read_anthropic_enablement
from .model_factory import ASSISTANT_DIR, ledger_path
from .model_profiles import LIVE_DECISION_ID, REMOTE_DECISION_ID, ProfileConfigError
from .openrouter import require_offline_transport
from .remote_checks import Preflight, check_daily, typical_reservation
from .synthetic_boundary import check_messages

log = logging.getLogger("ai_assistant.anthropic_runtime")

OWNER_ATTESTATIONS = frozenset(
    {"dedicated_workspace", "workspace_limit_set", "inference_key_only", "key_revoked_at_fyp_end"}
)
CREDENTIAL_VARIABLE = "AI_ASSISTANT_ANTHROPIC_API_KEY"
# D-102 (proposed): raised from US$5.00 and US$1.00 by the owner; HR sets values within them.
LIFETIME_CEILING_MICRO_USD = 30_000_000
DAILY_CEILING_MICRO_USD = 5_000_000
MAX_CALLS_CEILING = 20
MAX_PROMPT_BYTES = 32_768
CHAT_RECONCILE_SECONDS = 7 * 86_400
PAID_RECONCILE_SECONDS = 86_400
PREFLIGHT_TIMEOUT_SECONDS = 15.0
MODEL_URL = f"{anthropic_profiles.BASE_URL}/v1/models/{MODEL_ID}"
_MAX_PREFLIGHT_BODY_BYTES = 65_536
_WORKSPACE = re.compile(r"wrkspc_[A-Za-z0-9]{8,64}")
# Inference keys only (the console's API keys and user keys); never an Admin key.
_KEY = re.compile(r"sk-ant-(?:api\d{2}|usr)-[A-Za-z0-9_-]{20,300}")
# D-106: what an HR administrator may enter (the same inference-key shape).
HR_KEY = _KEY
_ROUTING_BITS = sum(ANOMALY_BITS[code] for code in ROUTING_ANOMALIES)


class Notices(NamedTuple):
    # Which model answered, or why it did not (main.py shows them as the lead notice).
    answered: str
    boundary: str
    dev_answered: str
    eligibility: str


NOTICES = Notices(
    answered="Answered by Claude Sonnet 5.5 through Anthropic (D-094 local synthetic test mode).",
    boundary=(
        "Claude Sonnet 5.5 through Anthropic is used only on the approved synthetic test case, "
        "so this answer comes straight from the case data."
    ),
    dev_answered=(
        "Answered by Claude Sonnet 5.5 through Anthropic (D-095 development mode, verified "
        "synthetic case)."
    ),
    eligibility=(
        "Claude Sonnet 5.5 through Anthropic is used only on verified synthetic development "
        "cases, so this answer comes straight from the case data."
    ),
)


# R2.2: the hosted deployment's lead notice on a conversational Claude answer.
HOSTED_ANSWERED = "Answered by Claude Sonnet 5.5 through Anthropic."


def attestations(settings: AiAssistantSettings) -> frozenset[str]:
    return frozenset(
        part.strip() for part in settings.anthropic_owner_attests.split(",") if part.strip()
    )


def _bounded(value: object, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def enablement(settings: AiAssistantSettings) -> AnthropicEnablement | None:
    # D-107: the HR record in the service's model state database (read-only; never created
    # here). None: no record, so the environment configuration applies. Raises when it cannot
    # be read (callers fail closed).
    path = Path(settings.model_admin_db_path)
    return read_anthropic_enablement(path if path.is_absolute() else ASSISTANT_DIR / path)


def _enablement(settings: AiAssistantSettings) -> tuple[AnthropicEnablement | None, bool]:
    # (record, readable).
    try:
        return enablement(settings), True
    except (ValueError, sqlite3.Error, OSError):
        return None, False


def valid_workspace(value: str) -> bool:
    return bool(_WORKSPACE.fullmatch(value or ""))


class HostedDeployment(NamedTuple):
    # R2.2 (D-129 proposed): the hosted service's one browser origin and its own lifetime
    # ceiling, registered by the hosting layer once every startup refusal passed. Never read
    # from a setting: a development machine cannot become a hosted deployment by configuration.
    origin: str
    lifetime_ceiling_micro_usd: int


_hosted: HostedDeployment | None = None
_hosted_lock = threading.Lock()


def register_hosted_deployment(origin: str, lifetime_ceiling_micro_usd: int) -> None:
    # Once per process, with the same values only; anything else is refused (fail closed).
    global _hosted
    parts = urlsplit(origin)
    if (
        # D-129: no hosted deployment before the owner's acceptance is recorded in the code.
        assistant_config.HOSTED_TRANSMISSION_DECISION is None
        or parts.scheme != urlsplit(anthropic_profiles.BASE_URL).scheme
        or not parts.hostname
        or is_local_model_url(origin)
        or origin != f"{parts.scheme}://{parts.netloc}"
        or not _bounded(lifetime_ceiling_micro_usd, 1, LIFETIME_CEILING_MICRO_USD)
    ):
        raise ValueError
    wanted = HostedDeployment(origin, lifetime_ceiling_micro_usd)
    with _hosted_lock:
        if _hosted is not None and _hosted != wanted:
            raise ValueError
        _hosted = wanted


def hosted_deployment() -> HostedDeployment | None:
    return _hosted


# D-130: the paid qualification's extra turns, one per hosted chat path it enables (OD-G6).
HOSTED_QUALIFICATION_TURNS: tuple[tuple[str, str], ...] = (
    ("H-G1", "general"),
    ("H-S1", "support"),
    ("H-T1", "try_change"),
    # Fifth path (D-130 amendment draft): only while HOSTED_INSIGHTS_DECISION is set.
    ("H-D1", "dashboard_insights"),
)


def hosted_paths() -> frozenset[str]:
    # D-130: the chat paths hosted Claude may answer besides the case chat. Empty unless the
    # owner's decision is in the code and this process is the registered hosted deployment.
    if assistant_config.HOSTED_CHAT_DECISION is None or _hosted is None:
        return frozenset()
    paths = set(assistant_config.HOSTED_CHAT_PATHS)
    if assistant_config.HOSTED_INSIGHTS_DECISION is not None:
        paths.add("dashboard_insights")
    return frozenset(paths)


def hosted_chat(model: object, path: str) -> bool:
    # D-130: hosted Claude (and nothing else) may answer this path. Every per-call control
    # (readiness, the HR session key, the ledger, the preflight, the ticket) is still checked
    # by the model itself for the very messages sent.
    return path in hosted_paths() and getattr(model, "hosted_claude", False) is True


def hosted_qualification_turns() -> tuple[str, ...]:
    paths = hosted_paths()
    return tuple(key for key, path in HOSTED_QUALIFICATION_TURNS if path in paths)


def lifetime_ceiling() -> int:
    # D-102's ceiling, lowered on a hosted deployment to the owner's hosted ceiling (its ledger
    # counts only its own calls, so the hosted and local ledgers share no cap).
    hosted = _hosted
    if hosted is None:
        return LIFETIME_CEILING_MICRO_USD
    return min(LIFETIME_CEILING_MICRO_USD, hosted.lifetime_ceiling_micro_usd)


def local_deployment(settings: AiAssistantSettings) -> bool:
    # The approved local development deployment: the model switched on, a literal loopback
    # CLM backend and only local browser origins (as remote_test checks for GPT-OSS). R2.2: or
    # the registered hosted deployment, served to its one exact origin and never on loopback.
    hosted = _hosted
    if hosted is not None:
        return (
            settings.llm_enabled
            and list(settings.allowed_origins) == [hosted.origin]
            and not is_local_model_url(settings.clm_backend_url)
            and urlsplit(settings.clm_backend_url).hostname != "localhost"
        )
    return (
        settings.llm_enabled
        and is_local_model_url(settings.clm_backend_url)
        and bool(settings.allowed_origins)
        and all(map(remote_test._local_origin, settings.allowed_origins))
    )


def hr_enabled(settings: AiAssistantSettings) -> bool:
    # D-107: an HR administrator enabled Claude (a readable record that is switched on).
    record, _ = _enablement(settings)
    return record is not None and record.enabled


def configured(settings: AiAssistantSettings) -> bool:
    # Claude is set up for this service: by HR (D-107) or by the environment (D-099).
    record, readable = _enablement(settings)
    if record is not None or not readable:
        return record is not None and record.enabled
    return settings.anthropic_decision == anthropic_profiles.DECISION_ID


def workspace_id(settings: AiAssistantSettings) -> str:
    # The workspace every reply must name: HR's confirmed one (D-107), else the environment's.
    record, readable = _enablement(settings)
    if record is not None or not readable:
        return record.workspace_id if record is not None and record.enabled else ""
    return settings.anthropic_workspace_id


def workspace_limit(settings: AiAssistantSettings) -> int:
    # The workspace's monthly limit as the owner confirmed it (never read from Anthropic).
    record, readable = _enablement(settings)
    if record is not None or not readable:
        return record.workspace_limit_micro_usd if record is not None and record.enabled else 0
    return settings.anthropic_workspace_limit_micro_usd


def synthetic_mode(settings: AiAssistantSettings) -> bool:
    # Claude's D-095 mode (verified synthetic cases with provenance): under HR enablement the
    # approved local deployment itself; under the environment configuration the shared D-095
    # interlocks (D-104 A1, unchanged). The eligibility check and its ticket are the same.
    record, readable = _enablement(settings)
    if record is not None or not readable:
        return record is not None and record.enabled and local_deployment(settings)
    return synthetic_eligibility.shared_mode(settings)


def readiness(settings: AiAssistantSettings) -> str | None:
    # None when the configurations may be offered; otherwise the first closed reason.
    record, readable = _enablement(settings)
    if not readable:
        return "ANTHROPIC_ENABLEMENT_UNREADABLE"
    if record is not None:
        # D-107: HR's record, then the runtime checks the decision names stood for.
        if not record.enabled:
            return "ANTHROPIC_NOT_ENABLED"
        if not settings.llm_enabled:
            return "MODEL_DISABLED_BY_ENVIRONMENT"
        if not local_deployment(settings):
            return "NOT_DEVELOPMENT_ENVIRONMENT"
        if record.confirmations != OWNER_ATTESTATIONS:
            return "ANTHROPIC_ATTESTATION_MISSING"
        if not _WORKSPACE.fullmatch(record.workspace_id):
            return "WORKSPACE_NOT_ATTESTED"
        # A workspace also set on the server must be the same one (never a silent choice).
        if (
            settings.anthropic_workspace_id
            and settings.anthropic_workspace_id != record.workspace_id
        ):
            return "WORKSPACE_MISMATCH"
        if not _bounded(record.workspace_limit_micro_usd, 1, LIFETIME_CEILING_MICRO_USD):
            return "WORKSPACE_LIMIT_NOT_ATTESTED"
        return _limits_problem(settings)
    if settings.anthropic_decision != anthropic_profiles.DECISION_ID:
        return "ANTHROPIC_NOT_AUTHORISED"
    if not settings.llm_enabled:
        return "MODEL_DISABLED_BY_ENVIRONMENT"
    if (
        settings.local_api_test_decision != remote_test.TEST_DECISION_ID
        or settings.remote_inference_decision != REMOTE_DECISION_ID
        or settings.remote_live_decision != LIVE_DECISION_ID
    ):
        return "DECISION_INTERLOCK"
    if not is_local_model_url(settings.clm_backend_url) or not (
        settings.allowed_origins and all(map(remote_test._local_origin, settings.allowed_origins))
    ):
        return "NOT_DEVELOPMENT_ENVIRONMENT"
    if attestations(settings) != OWNER_ATTESTATIONS:
        return "ANTHROPIC_ATTESTATION_MISSING"
    if not _WORKSPACE.fullmatch(settings.anthropic_workspace_id or ""):
        return "WORKSPACE_NOT_ATTESTED"
    if not _bounded(settings.anthropic_workspace_limit_micro_usd, 1, LIFETIME_CEILING_MICRO_USD):
        return "WORKSPACE_LIMIT_NOT_ATTESTED"
    return _limits_problem(settings)


def _limits_problem(settings: AiAssistantSettings) -> str | None:
    if not (
        _bounded(settings.anthropic_daily_cap_micro_usd, 1, DAILY_CEILING_MICRO_USD)
        and _bounded(settings.anthropic_max_calls, 1, MAX_CALLS_CEILING)
        and _bounded(settings.remote_max_prompt_bytes, 1024, MAX_PROMPT_BYTES)
        and _bounded(settings.local_api_test_preflight_seconds, 0, 3600)
    ):
        return "ANTHROPIC_SETTINGS_INVALID"
    # QG M-1: one ledger file per provider, so neither provider's checks touch the other's.
    if ledger_file(settings).resolve() == ledger_path(settings).resolve():
        return "LEDGER_PATH_SHARED"
    return None


# --- the key ---------------------------------------------------------------------------------


def resolve_key(
    environ: Mapping[str, str] | None = None,
    *,
    env_file: Path | None = None,
    store: key_sources.HrCredential | None = None,
    max_age: float = key_sources.REVALIDATE_SECONDS,
) -> tuple[SecretStr | None, key_sources.CredentialStatus, str | None]:
    # The key, its status for the page (never the key) and the closed refusal code. Given an
    # ``environ`` (tests), that mapping only unless ``env_file`` or ``store`` is also given.
    # D-106: the HR session's key first (key_sources.ANTHROPIC_STORE), then the process
    # environment, then the .env. The first source holding a value decides, even a malformed
    # one (nothing falls through); an HR key whose session cannot be checked now holds.
    if environ is None:
        environ = os.environ
        env_file = key_sources.ENV_FILE if env_file is None else env_file
        store = key_sources.ANTHROPIC_STORE if store is None else store
    key, status = key_sources.resolve_from(
        CREDENTIAL_VARIABLE, _KEY, environ, env_file, store, max_age
    )
    if key is not None:
        return key, status, None
    if status.status == "missing":
        return None, status, "CREDENTIAL_MISSING"
    if status.status == "unverified":
        return None, status, "CREDENTIAL_SESSION_UNVERIFIED"
    value = (
        environ.get(CREDENTIAL_VARIABLE)
        if status.source == "environment"
        else key_sources.env_file_value(env_file, CREDENTIAL_VARIABLE)
        if env_file is not None
        else None
    ) or ""
    code = "CREDENTIAL_ADMIN_REFUSED" if value.startswith("sk-ant-admin") else None
    return None, status, code or "CREDENTIAL_INVALID"


# --- the ledger ------------------------------------------------------------------------------


def ledger_file(settings: AiAssistantSettings) -> Path:
    path = Path(settings.anthropic_ledger_path)
    return path if path.is_absolute() else ASSISTANT_DIR / path


def worst_reservation() -> int:
    return typical_reservation(ENDPOINT, anthropic_profiles.MAX_TOKENS)


def _usd(micro: int | None) -> str | None:
    return None if micro is None else f"{micro / 1_000_000:.6f}"


def _iso(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, UTC).isoformat().replace("+00:00", "Z")


def ledger_profile(path: Path) -> str:
    # The ledger's profile, read without recovering it (``BudgetLedger.open`` abandons expired
    # calls), so another provider's ledger is never changed by a check here (QG L-4).
    probe = BudgetLedger(path)
    probe.verify()
    return probe.status().profile_id


def open_own(path: Path) -> BudgetLedger:
    # The Anthropic ledger, opened (and recovered) only once its profile is known.
    if ledger_profile(path) != LEDGER_PROFILE_ID:
        raise LedgerError("LEDGER_PROFILE_MISMATCH", "not the Anthropic ledger")
    return BudgetLedger.open(path)


def verify_calls(ledger: BudgetLedger) -> tuple[int, int]:
    # In-band verification of every closed call not yet verified: verified only when it settled
    # from complete reported usage with no anomaly (the reply named the attested workspace, the
    # pinned model and a standard route before any text). Anything else is quarantined and
    # opens the breaker. Returns (checked, quarantined).
    # QG M-1: never on another provider's ledger (its calls follow that provider's rules).
    if ledger.status().profile_id != LEDGER_PROFILE_ID:
        raise LedgerError("INVALID_INPUT", "not the Anthropic ledger")
    calls = ledger.unverified_closed_calls()
    quarantined = 0
    for call in calls:
        verified = call.state == "settled" and call.anomaly_bits == 0
        breaker = "routing_anomaly" if call.anomaly_bits & _ROUTING_BITS else "reconcile_drift"
        if (
            call.state in ("unsettled", "abandoned")
            and call.charged_micro_usd == call.reserved_micro_usd
            and call.anomaly_bits == 0
        ):
            # D-118 S6: charged in full with no usage and no anomaly: conservative, not a
            # billing discrepancy (still quarantined; only HR's proven resume closes it).
            breaker = "usage_missing"
        ledger.record_verification(call.call_id, verified=verified, breaker_code=breaker)
        quarantined += not verified
    return len(calls), quarantined


def provider_capped(ledger: BudgetLedger) -> bool:
    # D-118 S4: a provider-capped ledger is bounded by Anthropic's own workspace limit and
    # conservative in-band accounting; its reconciliation windows gate nothing routine.
    return ledger.profile().accounting_mode == "provider_capped"


def reconciled_within(ledger: BudgetLedger, seconds: int, *, clock: Callable[[], float]) -> bool:
    reconciled = ledger.last_reconciled_ms()
    if reconciled is None:
        return False
    age = clock() * 1000 - reconciled
    return 0 <= age <= seconds * 1000


def check_cap_change(
    ledger: BudgetLedger,
    cap_micro_usd: int,
    *,
    raising: bool,
    clock: Callable[[], float] = time.time,
) -> None:
    # Every cap change on the Anthropic ledger (the operator's script or HR, D-102): never above
    # the US$30.00 lifetime ceiling, and a raise only within 24 hours of a reconciliation.
    if ledger.status().profile_id != LEDGER_PROFILE_ID:
        raise LedgerError("INVALID_INPUT", "not the Anthropic ledger")
    if cap_micro_usd > lifetime_ceiling():
        raise LedgerError("CAP_RAISE_REFUSED", "above the Anthropic lifetime ceiling")
    # D-118 amendment P4: a session store (provider-capped) needs no reconciliation to raise.
    if (
        raising
        and not provider_capped(ledger)
        and not reconciled_within(ledger, PAID_RECONCILE_SECONDS, clock=clock)
    ):
        raise LedgerError("CAP_RAISE_REFUSED", "reconcile within the last day before raising")


def check_ledger(
    report: Preflight,
    settings: AiAssistantSettings,
    *,
    within_seconds: int,
    clock: Callable[[], float] = time.time,
) -> None:
    try:
        profile = ledger_profile(ledger_file(settings))
    except LedgerError as error:
        report.add("ledger.healthy", False, f"refused: {error.code}")
        return
    # QG M-1/L-4: the profile first, read without recovering; another provider's ledger is
    # never recovered or verified here.
    report.add(
        "ledger.profile",
        profile == LEDGER_PROFILE_ID,
        f"profile {profile} (the separate Anthropic ledger)",
    )
    if profile != LEDGER_PROFILE_ID:
        return
    try:
        ledger = open_own(ledger_file(settings))
        checked, quarantined = verify_calls(ledger)
        status = ledger.status()
        capped = provider_capped(ledger)
        fresh = capped or reconciled_within(ledger, within_seconds, clock=clock)
    except LedgerError as error:
        report.add("ledger.healthy", False, f"refused: {error.code}")
        return
    report.add("ledger.healthy", True, f"alias {status.key_alias}")
    report.add(
        "ledger.earlier_calls_verified",
        quarantined == 0,
        f"{checked} earlier call(s) checked in-band, {quarantined} quarantined",
    )
    report.add(
        "ledger.breaker_closed_no_open_calls",
        not status.breaker_open and status.open_calls == 0,
        f"breaker {status.breaker_code or 'closed'}, open calls {status.open_calls}",
    )
    ceiling = min(lifetime_ceiling(), workspace_limit(settings))
    report.add(
        "ledger.cap_within_ceiling",
        status.opening_usage < status.cap <= ceiling,
        f"cap {_usd(status.cap)} <= {_usd(ceiling)} (lifetime ceiling and workspace limit),"
        f" above opening usage {_usd(status.opening_usage)}",
    )
    report.add(
        "ledger.reconciled_recently",
        fresh,
        "provider-capped: Anthropic's workspace limit bounds billing; no routine reconciliation"
        if capped
        else f"reconciled against the Console within the last {within_seconds} seconds",
    )
    reservation = worst_reservation()
    report.add(
        "ledger.headroom_for_one_call",
        status.headroom >= reservation,
        f"headroom {_usd(status.headroom)} >= one reservation {_usd(reservation)}",
    )
    check_daily(report, ledger, settings.anthropic_daily_cap_micro_usd, reservation)


# --- the free preflight ----------------------------------------------------------------------


def check_workspace(
    report: Preflight, settings: AiAssistantSettings, key: SecretStr, transport: object
) -> None:
    # ``GET /v1/models/{model}``: free, no content. The reply must name the attested workspace
    # and the pinned model. No retries; proxies and environment overrides are ignored.
    mock = None if transport is None else require_offline_transport(transport)
    headers = {
        "x-api-key": key.get_secret_value(),
        "anthropic-version": anthropic_profiles.API_VERSION,
        "accept-encoding": "identity",
    }
    try:
        with httpx.Client(
            timeout=httpx.Timeout(PREFLIGHT_TIMEOUT_SECONDS),
            transport=mock,
            trust_env=False,
            follow_redirects=False,
        ) as client:
            reply = client.get(MODEL_URL, headers=headers)
            body = reply.content[: _MAX_PREFLIGHT_BODY_BYTES + 1]
    except httpx.HTTPError as error:
        report.add("anthropic.models_reachable", False, f"unreadable ({type(error).__name__})")
        return
    report.add("anthropic.models_reachable", reply.status_code == 200, f"HTTP {reply.status_code}")
    if reply.status_code != 200:
        return
    report.add(
        "anthropic.workspace_matches",
        reply.headers.get(WORKSPACE_HEADER) == workspace_id(settings),
        "the reply names the attested workspace",
    )
    try:
        named = json.loads(body).get("id") if len(body) <= _MAX_PREFLIGHT_BODY_BYTES else None
    except (ValueError, AttributeError, RecursionError, UnicodeError):
        named = None
    report.add("anthropic.model_available", named == MODEL_ID, f"model {MODEL_ID}")


# The last preflight (content-free, process memory), for the spending view.
_last: dict[str, Any] = {}
_last_lock = threading.Lock()


def preflight(
    settings: AiAssistantSettings,
    *,
    within_seconds: int = CHAT_RECONCILE_SECONDS,
    environ: Mapping[str, str] | None = None,
    env_file: Path | None = None,
    transport: object = None,
    key: SecretStr | None = None,
    network: bool = True,
    clock: Callable[[], float] = time.time,
) -> Preflight:
    # Every check a call needs, failing closed at the first one that cannot be evaluated; the
    # local checks come first, so nothing is sent unless they pass. ``key`` pins the very key
    # the call then uses.
    report = Preflight()
    code = readiness(settings)
    if code is not None:
        report.add("anthropic.ready", False, f"refused: {code}")
        return report
    report.add("anthropic.ready", True, "D-099 and its interlocks named; owner attested")
    key_code = None
    if key is None:
        key, _, key_code = resolve_key(environ, env_file=env_file)
    report.add(
        "anthropic.inference_key",
        key is not None,
        "present (not shown)" if key is not None else f"refused: {key_code}",
    )
    if key is None:
        return report
    check_ledger(report, settings, within_seconds=within_seconds, clock=clock)
    if network and report.passed:
        check_workspace(report, settings, key, transport)
        with _last_lock:
            _last.clear()
            _last.update(
                checked_at=time.time(),
                # QG L-2: the result holds for this key only.
                key=key_sources.identity(key),
                passed=report.passed,
                checks=[{"check": c.name, "ok": c.ok, "detail": c.detail} for c in report.checks],
            )
    return report


def read_workspace(
    settings: AiAssistantSettings,
    *,
    environ: Mapping[str, str] | None = None,
    env_file: Path | None = None,
    transport: object = None,
) -> dict[str, Any]:
    # D-107 setup: the free GET /v1/models/{model} with the key in force (D-106 order, the HR
    # session checked now), before Claude is enabled, so HR can confirm the workspace the key
    # itself reports. Only on the approved local deployment. No inference, no case data, no
    # ledger; the reply's workspace id is shown to HR (not secret) and nothing is stored here.
    if not local_deployment(settings):
        return {"outcome": "refused", "code": "NOT_DEVELOPMENT_ENVIRONMENT", "workspace_id": None}
    key, _, code = resolve_key(environ, env_file=env_file, max_age=0)
    if key is None:
        return {"outcome": "refused", "code": code, "workspace_id": None}
    mock = None if transport is None else require_offline_transport(transport)
    headers = {
        "x-api-key": key.get_secret_value(),
        "anthropic-version": anthropic_profiles.API_VERSION,
        "accept-encoding": "identity",
    }
    try:
        with httpx.Client(
            timeout=httpx.Timeout(PREFLIGHT_TIMEOUT_SECONDS),
            transport=mock,
            trust_env=False,
            follow_redirects=False,
        ) as client:
            reply = client.get(MODEL_URL, headers=headers)
            body = reply.content[: _MAX_PREFLIGHT_BODY_BYTES + 1]
    except httpx.HTTPError as error:
        return {
            "outcome": "failed",
            "code": f"UNREACHABLE:{type(error).__name__}",
            "workspace_id": None,
        }
    if reply.status_code != 200:
        return {"outcome": "failed", "code": f"HTTP_{reply.status_code}", "workspace_id": None}
    named = reply.headers.get(WORKSPACE_HEADER) or ""
    try:
        model = json.loads(body).get("id") if len(body) <= _MAX_PREFLIGHT_BODY_BYTES else None
    except (ValueError, AttributeError, RecursionError, UnicodeError):
        model = None
    workspace = named if _WORKSPACE.fullmatch(named) else None
    ok = workspace is not None and model == MODEL_ID
    return {
        "outcome": "passed" if ok else "failed",
        "code": None
        if ok
        else ("WORKSPACE_NOT_NAMED" if workspace is None else "MODEL_UNAVAILABLE"),
        "workspace_id": workspace,
        "key": key_sources.identity(key),
    }


def connection_check(
    settings: AiAssistantSettings, *, within_seconds: int = CHAT_RECONCILE_SECONDS, **kwargs: Any
) -> dict[str, Any]:
    # Model management's connection test: the preflight, no inference.
    report = preflight(settings, within_seconds=within_seconds, **kwargs)
    failed = [check.name for check in report.checks if not check.ok]
    return {
        "outcome": "passed" if report.passed else "failed",
        "code": None if report.passed else "PREFLIGHT_FAILED:" + ",".join(failed),
        "listed": None,
        "complete_ms": None,
        "stream_ms": None,
        "first_piece_ms": None,
        "checks": [{"check": c.name, "ok": c.ok, "detail": c.detail} for c in report.checks],
    }


def budget_status(
    settings: AiAssistantSettings,
    *,
    within_seconds: int = PAID_RECONCILE_SECONDS,
    environ: Mapping[str, str] | None = None,
    env_file: Path | None = None,
    clock: Callable[[], float] = time.time,
) -> dict[str, Any]:
    # The Anthropic spending view (read-only: the ledger is checked, never recovered or
    # changed; nothing is sent). Amounts are micro-USD integers with a USD string beside each.
    view: dict[str, Any] = {
        "configured": configured(settings),
        "provider": anthropic_profiles.PROVIDER,
        "timezone": "Asia/Singapore",
        "daily_cap_micro_usd": settings.anthropic_daily_cap_micro_usd,
        "workspace_limit_micro_usd": workspace_limit(settings),
        "lifetime_ceiling_micro_usd": lifetime_ceiling(),
    }
    key, credential, key_code = resolve_key(environ, env_file=env_file)
    view["credential"] = credential.view()
    now = clock()
    view["next_reset_at"] = _iso(next_singapore_reset_ms(int(now * 1000)) / 1000)
    with _last_lock:
        last = dict(_last)
    if last and last.get("key") != key_sources.identity(key):
        last = {}  # another key's preflight (QG L-2)
    view["preflight"] = (
        {"checked_at": _iso(last["checked_at"]), "passed": last["passed"], "checks": last["checks"]}
        if last
        else None
    )
    refusal = readiness(settings)
    try:
        ledger = BudgetLedger(ledger_file(settings))
        ledger.verify()
        status = ledger.status()
        daily = ledger.daily_status(settings.anthropic_daily_cap_micro_usd)
        capped = provider_capped(ledger)
        fresh = capped or reconciled_within(ledger, within_seconds, clock=clock)
        reconciled = ledger.last_reconciled_ms()
    except LedgerError as error:
        view.update(ledger=None, daily=None, effective_remaining_micro_usd=0)
        view["effective_remaining_usd"] = _usd(0)
        view["refusal"] = refusal or error.code
        return view
    reservation = worst_reservation()
    view["ledger"] = {
        "profile_ok": status.profile_id == LEDGER_PROFILE_ID,
        "cap_micro_usd": status.cap,
        "committed_micro_usd": status.committed,
        "headroom_micro_usd": status.headroom,
        "headroom_usd": _usd(max(status.headroom, 0)),
        "open_calls": status.open_calls,
        "breaker_open": status.breaker_open,
        "breaker_code": status.breaker_code,
        "reconciled_at": None if reconciled is None else _iso(reconciled / 1000),
        "accounting_mode": "provider_capped" if capped else "provider_anchored",
    }
    view["daily"] = {
        "cap_micro_usd": daily.cap,
        "settled_today_micro_usd": daily.settled_today,
        "in_flight_micro_usd": daily.open_reserved,
        "remaining_micro_usd": daily.remaining,
        "remaining_usd": _usd(daily.remaining),
    }
    effective = min(daily.remaining, max(status.headroom, 0))
    view["effective_remaining_micro_usd"] = effective
    view["effective_remaining_usd"] = _usd(effective)
    view["reservation_micro_usd"] = reservation
    ceiling = min(lifetime_ceiling(), workspace_limit(settings))
    checks = (
        (key_code, key_code),
        (status.profile_id != LEDGER_PROFILE_ID, "LEDGER_PROFILE_MISMATCH"),
        (status.breaker_open, f"BREAKER_OPEN:{status.breaker_code}"),
        (status.open_calls > 0, "BREAKER_OPEN:open_call"),
        (not status.opening_usage < status.cap <= ceiling, "LIFETIME_CEILING_EXCEEDED"),
        (not fresh, "RECONCILIATION_STALE"),
        (daily.cap == 0, "DAILY_CAP_INVALID"),
        (daily.remaining < reservation, "DAILY_ALLOWANCE_EXHAUSTED"),
        (status.headroom < reservation, "LIFETIME_CAP_EXHAUSTED"),
        # The free preflight (workspace and model) must have passed in this process.
        (not last, "PROVIDER_LIMIT_NOT_CHECKED"),
        (bool(last) and not last.get("passed"), "PROVIDER_CHECK_FAILED"),
    )
    for failed, code in checks:
        if refusal is None and failed:
            refusal = str(code)
    view["refusal"] = refusal
    return view


# --- the model the chat uses -----------------------------------------------------------------


def _digest(messages: list[dict[str, str]]) -> str:
    text = json.dumps(messages, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ClaudeTestModel:
    # One Claude configuration as the chat uses it. Refuses a call (as an unavailable model, so
    # the RM gets the case-data answer) unless every condition in the header still holds.

    # The chat checks the synthetic boundary before it sends anything to this model.
    requires_synthetic_boundary = True
    notices = NOTICES

    @property
    def attribution(self) -> str | None:
        # R2.2: on the hosted deployment a conversational answer (D-122) names the model that
        # wrote it; an answer this model did not write never carries it (main.remote_gate).
        return HOSTED_ANSWERED if _hosted is not None else None

    # D-130 OD-G8: every prompt this model sends goes to Anthropic, so it carries no user
    # identifier (provider_payload); the role stays where the case facts need it.
    anthropic_bound = True

    @property
    def hosted_claude(self) -> bool:
        # D-130: this model runs on the registered hosted deployment (hosted_chat).
        return _hosted is not None

    def development_mode(self) -> bool:
        # D-104 A1: D-095 mode never depends on OpenRouter's endpoint, reasoning settings or
        # attestations; D-107: under HR enablement it is the approved local deployment
        # (synthetic_mode). Claude's own readiness (enablement or decision, four confirmations,
        # workspace, limits, ledger) is checked again in _ready before every call, and the
        # eligibility check and its ticket are GPT-OSS's.
        return synthetic_mode(self._settings)

    def __init__(
        self,
        settings: AiAssistantSettings,
        profile_id: str,
        *,
        environ: Mapping[str, str] | None = None,
        env_file: Path | None = None,
        transport: object = None,
        clock: Callable[[], float] = time.monotonic,
        within_seconds: int = CHAT_RECONCILE_SECONDS,
        purpose: str = "chat",
    ) -> None:
        code = readiness(settings)
        if code is not None:
            raise ProfileConfigError(code, "the Claude configuration is not ready")
        configuration = anthropic_profiles.CONFIGURATIONS.get(profile_id)
        if configuration is None:
            raise ProfileConfigError("PROFILE_UNKNOWN", "not an approved Claude configuration")
        if transport is not None:
            require_offline_transport(transport)
        self._settings = settings
        self._configuration = configuration
        self._environ = environ
        self._env_file = env_file
        self._transport = transport
        self._clock = clock
        self._within = within_seconds
        # D-118: a paid qualification's calls share the session's money, not its chat calls.
        self._purpose = purpose
        self._ledger_file = ledger_file(settings)
        try:
            self._start_call = open_own(self._ledger_file).last_call_id()
        except LedgerError:
            raise ProfileConfigError(
                "LEDGER_UNAVAILABLE", "the Anthropic ledger is not usable"
            ) from None
        self._lock = threading.Lock()
        self._cleared_lock = threading.Lock()
        self._cleared: dict[str, float] = {}
        self._inner: ChatModel | None = None
        self._credential: str | None = None
        self._checked_at: float | None = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._configuration.profile_id!r})"

    @property
    def name(self) -> str:
        return MODEL_ID

    @property
    def profile_id(self) -> str:
        return self._configuration.profile_id

    @property
    def endpoint_slug(self) -> str:
        return ENDPOINT.slug

    def _admit_in_adapter(self, messages: list[dict[str, str]]) -> bool:
        # QG F2: decided again for the very messages sent: the ticket this model took for them
        # in ``_ready`` (still in D-095 mode now), or the D-094 text check.
        with self._cleared_lock:
            cleared = self._cleared.pop(_digest(messages), None)
        if (
            cleared is not None
            and self._clock() - cleared <= synthetic_eligibility.TICKET_SECONDS
            and (external_conversational(self._settings) or self.development_mode())
        ):
            return True
        return check_messages(messages) is None

    def _build_inner(self, key: SecretStr) -> ChatModel:
        adapter = AnthropicChatModel(
            configuration=self._configuration,
            credential=key,
            max_prompt_bytes=self._settings.remote_max_prompt_bytes,
            transport=LIVE_NETWORK if self._transport is None else self._transport,
            admit=self._admit_in_adapter,
            expected_workspace=workspace_id(self._settings),
        )
        return BudgetedChatModel(
            adapter,
            open_own(self._ledger_file),
            max_in_flight=1,
            lease_seconds=anthropic_profiles.TIMEOUT_SECONDS + LEASE_GRACE_SECONDS,
            daily_cap_micro_usd=self._settings.anthropic_daily_cap_micro_usd,
        )

    def _refuse(self, reason: str) -> ModelCallError:
        log.warning("Claude call refused: %s", reason)
        return ModelCallError("budget_refused")

    def _ready(self, messages: list[dict[str, str]]) -> ChatModel:
        # Blocking (ledger, preflight request): never on the event loop. Returns the guarded
        # adapter to call (rebuilt when the key changed).
        ticket = synthetic_eligibility.admitted(messages)
        # D-122: conversational answers rest on the ticket alone, on any case.
        development = ticket and (
            external_conversational(self._settings) or self.development_mode()
        )
        if not development and check_messages(messages) is not None:
            raise self._refuse("text outside the synthetic boundary")
        # A prompt the Messages API cannot take (not the service's known shape; D-099-FU1) is
        # refused here, before anything is reserved, so it costs nothing and never opens the
        # breaker. Admission and the ticket above are for these exact messages, unconverted.
        try:
            system_and_conversation(messages)
        except PromptShapeError:
            raise self._refuse("prompt shape") from None
        if development:
            now = self._clock()
            with self._cleared_lock:
                for digest, at in list(self._cleared.items()):
                    if now - at > synthetic_eligibility.TICKET_SECONDS:
                        del self._cleared[digest]
                self._cleared[_digest(messages)] = now
        with self._lock:
            if readiness(self._settings) is not None:
                raise self._refuse("not ready")
            # D-106: the HR session is checked again for every call (never a cached answer).
            key, _, _ = resolve_key(self._environ, env_file=self._env_file, max_age=0)
            if key is None:
                raise self._refuse("no usable key")
            marker = key_sources.identity(key)
            if self._inner is None or marker != self._credential:
                try:
                    self._inner = self._build_inner(key)
                except (ProfileConfigError, LedgerError):
                    raise self._refuse("model build") from None
                self._credential, self._checked_at = marker, None
                with _last_lock:
                    _last.clear()  # the shown preflight was another key's (QG L-2)
            try:
                ledger = open_own(self._ledger_file)
                # D-118: chat calls in the open session, read from the ledger (a restart or
                # re-activation never resets them); the ledger enforces it again on admission.
                session = ledger.session()
            except LedgerError:
                raise self._refuse("ledger") from None
            limit = self._settings.anthropic_max_calls
            chat = self._purpose == "chat"
            if chat and session is not None and session.chat_calls >= limit:
                raise self._refuse("call limit")
            if isinstance(self._inner, BudgetedChatModel):
                self._inner.purpose = self._purpose
                self._inner.session_call_limit = limit if chat else None
            now = self._clock()
            network = (
                self._checked_at is None
                or now - self._checked_at > self._settings.local_api_test_preflight_seconds
            )
            report = preflight(
                self._settings,
                within_seconds=self._within,
                transport=self._transport,
                key=key,
                network=network,
            )
            if not report.passed:
                self._checked_at = None
                raise self._refuse("preflight")
            if network:
                self._checked_at = now
            return self._inner

    def verify_now(self) -> Preflight:
        # Verify every closed call not yet verified (in-band; no request).
        report = Preflight()
        with self._lock:
            try:
                checked, quarantined = verify_calls(open_own(self._ledger_file))
            except LedgerError as error:
                report.add("ledger.calls_verified", False, f"refused: {error.code}")
                return report
        report.add(
            "ledger.calls_verified",
            quarantined == 0,
            f"{checked} call(s) checked in-band, {quarantined} quarantined",
        )
        return report

    def calls_since_start(self) -> list[ClosedCall]:
        return open_own(self._ledger_file).closed_calls_after(self._start_call)

    def calls_used(self) -> int:
        # Read-only: the ledger is checked, never recovered or changed. D-118: the chat calls
        # of the open session.
        ledger = BudgetLedger(self._ledger_file)
        ledger.verify()
        session = ledger.session()
        return 0 if session is None else session.chat_calls

    def _verify_after(self) -> None:
        try:
            self.verify_now()
        except Exception:  # the next call verifies again before it is made
            log.error("Claude call verification failed; the next call checks again")

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        # Streaming only; refused before anything is reserved or sent.
        raise LlmUnavailableError("streaming only")

    async def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Piece, None]:
        inner = await anyio.to_thread.run_sync(self._ready, messages)
        try:
            # Closing this generator closes the guarded one, so its ledger settlement runs.
            async with aclosing(inner.stream(messages)) as source:
                async for piece in source:
                    yield piece
        finally:
            self._verify_after()

    def warm(self, messages: list[dict[str, str]]) -> None:
        return None  # no warm-up for a remote model
