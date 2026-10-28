"""D-094 local synthetic test mode: GPT-OSS 120B through OpenRouter in the CLM's own chat.

Off unless every condition below holds (``readiness``); then the remote profile is listed as
selectable in model management, and an HR administrator may test, qualify and activate it
like a local model. Even when it is the active model, the chat sends a question to it only
when ``synthetic_boundary.check`` finds the case, its documents, the knowledge used, the
history and the question inside the approved synthetic boundary; otherwise the RM gets the
deterministic case-data answer (main.py).

    decision     AI_ASSISTANT_LOCAL_API_TEST_DECISION names D-094, and the D-091 and D-092
                 values the remote profile already needs are named too
    environment  the CLM backend URL is a literal loopback address and every allowed browser
                 origin is a local http origin (a development machine, not a deployment)
    owner        AI_ASSISTANT_LOCAL_API_TEST_OWNER_ATTESTS says auto top-up and prompt
                 logging are off (neither is readable through the API)
    endpoint     the configured endpoint is the approved one (model_profiles.py)

Every call then reuses the Phase B controls unchanged (remote_checks.py): a passing
preflight (reused for AI_ASSISTANT_LOCAL_API_TEST_PREFLIGHT_SECONDS), earlier calls verified
before the next one, the lifetime budget ledger and its breaker (budget.py), the fixed request
policy (openrouter.py), and provider, model and cost verification of each call from generation
metadata after it. The model refuses any message outside the text part of the synthetic
boundary itself, whoever calls it. It makes at most AI_ASSISTANT_LOCAL_API_TEST_MAX_CALLS calls
(open calls included) from when it was activated or the service restarted; the ledger cap is
the money limit across restarts. Its blocking checks run off the event loop.

D-095 (development synthetic mode, synthetic_eligibility.py) adds, without changing the above:
the chat may also send messages that passed the eligibility check (a single-use ticket for
exactly those messages); every call is inside the ledger's daily allowance (US$1.00 per
Singapore day at most, budget.py) and the preflight checks it; the key may come from the
process environment, the git-ignored .env or an HR administrator (credentials.py), and when it
changes the model is rebuilt with it and the full preflight runs again before the next call.
``budget_status`` is the read-only spending view for the AI Models page.
"""

import hashlib
import json
import logging
import re
import threading
import time
from collections.abc import AsyncGenerator, Callable, Mapping
from contextlib import aclosing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import anyio

from . import credentials, synthetic_eligibility
from .budget import (
    DAILY_CAP_CEILING_MICRO_USD,
    BudgetLedger,
    ClosedCall,
    LedgerError,
    next_singapore_reset_ms,
    singapore_day_start_ms,
)
from .config import AiAssistantSettings
from .llm import ChatModel, ModelAnswer, ModelCallError, Piece, is_local_model_url
from .model_factory import build_account_client, build_chat_model, ledger_path
from .model_profiles import (
    APPROVED_PROFILES,
    LIVE_DECISION_ID,
    MAX_REMOTE_TOKENS,
    MIN_REASONING_ALLOWANCE,
    OPENROUTER_MODEL_ID,
    OPENROUTER_PROFILE_ID,
    REMOTE_DECISION_ID,
    ApprovedEndpoint,
    ProfileConfigError,
)
from .openrouter_account import OpenRouterAccount
from .remote_checks import (
    Preflight,
    fetch_public,
    run_preflight,
    typical_reservation,
    verify_earlier_calls,
)
from .synthetic_boundary import check_messages

log = logging.getLogger("ai_assistant.remote_test")

TEST_DECISION_ID = "D-094"
OWNER_ATTESTATIONS = frozenset({"auto_topup_off", "prompt_logging_off"})
_DEFAULTS = AiAssistantSettings.model_fields
_LOCAL_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def _local_origin(origin: str) -> bool:
    try:
        parts = urlsplit(origin)
        return parts.scheme == "http" and parts.hostname in _LOCAL_HOSTS and not parts.path
    except ValueError:
        return False


def attestations(settings: AiAssistantSettings) -> frozenset[str]:
    return frozenset(
        part.strip() for part in settings.local_api_test_owner_attests.split(",") if part.strip()
    )


def readiness(settings: AiAssistantSettings) -> str | None:
    """None when the test mode may be offered; otherwise the first closed reason."""

    if settings.local_api_test_decision != TEST_DECISION_ID:
        return "REMOTE_NOT_AUTHORISED"
    if not settings.llm_enabled:
        return "MODEL_DISABLED_BY_ENVIRONMENT"
    if (
        settings.remote_inference_decision != REMOTE_DECISION_ID
        or settings.remote_live_decision != LIVE_DECISION_ID
    ):
        return "DECISION_INTERLOCK"
    if not is_local_model_url(settings.clm_backend_url) or not (
        settings.allowed_origins and all(map(_local_origin, settings.allowed_origins))
    ):
        return "NOT_DEVELOPMENT_ENVIRONMENT"
    if attestations(settings) != OWNER_ATTESTATIONS:
        return "OWNER_ATTESTATION_MISSING"
    endpoint = endpoint_for(settings)
    if endpoint is None:
        return "ENDPOINT_NOT_APPROVED"
    allowance = settings.llm_reasoning_allowance_tokens
    if (
        settings.llm_reasoning_effort
        not in APPROVED_PROFILES[OPENROUTER_PROFILE_ID].capabilities.reasoning_efforts
        or allowance < MIN_REASONING_ALLOWANCE
        or settings.llm_max_answer_tokens + allowance
        > min(MAX_REMOTE_TOKENS, endpoint.max_completion_tokens)
    ):
        return "REMOTE_SETTINGS_INVALID"
    return None


_QUESTION_ID = re.compile(r"P\d{2}#\d{1,2}")


def qualification_manifest(settings: AiAssistantSettings) -> list[str] | None:
    """The paid qualification's Phase B question ids, or None unless they are listed once
    each and their number equals the configured count (D-092 P10). The qualification process
    also checks every id against the reviewed question file before any call."""

    ids = [
        part.strip()
        for part in settings.local_api_test_qualification_questions.split(",")
        if part.strip()
    ]
    if (
        not ids
        or len(set(ids)) != len(ids)
        or len(ids) != settings.local_api_test_qualification_count
        or not all(_QUESTION_ID.fullmatch(item) for item in ids)
    ):
        return None
    return ids


def endpoint_for(settings: AiAssistantSettings) -> ApprovedEndpoint | None:
    return APPROVED_PROFILES[OPENROUTER_PROFILE_ID].endpoint(settings.openrouter_endpoint)


def remote_settings(settings: AiAssistantSettings) -> AiAssistantSettings:
    """The service's settings as the remote profile reads them: the baseline's own model URL
    and name are not the remote profile's, so they go back to their defaults here."""

    return settings.model_copy(
        update={
            "llm_profile": OPENROUTER_PROFILE_ID,
            "llm_base_url": _DEFAULTS["llm_base_url"].default,
            "llm_model": _DEFAULTS["llm_model"].default,
        }
    )


def remote_fingerprint(settings: AiAssistantSettings) -> str:
    """What a remote qualification is tied to (never a credential)."""

    values = {
        "profile": OPENROUTER_PROFILE_ID,
        "decision": settings.local_api_test_decision,
        "endpoint": settings.openrouter_endpoint,
        "reasoning_effort": settings.llm_reasoning_effort,
        "reasoning_allowance_tokens": settings.llm_reasoning_allowance_tokens,
        "max_answer_tokens": settings.llm_max_answer_tokens,
        "temperature": settings.llm_temperature,
        "timeout_seconds": settings.llm_timeout_seconds,
        "max_prompt_bytes": settings.remote_max_prompt_bytes,
    }
    return hashlib.sha256(
        json.dumps(values, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def preflight(
    settings: AiAssistantSettings,
    *,
    environ: Mapping[str, str] | None = None,
    transport: object = None,
    fetch: Callable[[str], Any] = fetch_public,
) -> tuple[Preflight, BudgetLedger | None, OpenRouterAccount | None]:
    """The Phase B preflight for the test mode (no inference, no case data)."""

    code = readiness(settings)
    if code is not None:
        report = Preflight()
        report.add("test_mode.ready", False, f"refused: {code}")
        return report, None, None
    remote = remote_settings(settings)

    def open_account() -> OpenRouterAccount:
        if transport is not None:  # tests: an in-memory transport only
            return build_account_client(remote, transport=transport, environ=environ)
        return build_account_client(remote, environ=environ, allow_live_network=True)

    result = run_preflight(
        remote,
        open_account,
        ledger_file=ledger_path(remote),
        owner_attests_auto_topup_off="auto_topup_off" in attestations(settings),
        owner_attests_prompt_logging_off="prompt_logging_off" in attestations(settings),
        fetch=fetch,
    )
    _remember_provider(result[0])
    return result


# The provider-side key limit as the last preflight read it (content-free, process memory).
_provider: dict[str, Any] = {}
_provider_lock = threading.Lock()


def _remember_provider(report: Preflight) -> None:
    checks = [c for c in report.checks if c.name.startswith(("key.", "gate.account"))]
    with _provider_lock:
        _provider.clear()
        _provider.update(
            checked_at=time.time(),
            passed=bool(checks) and all(c.ok for c in checks),
            remaining_micro_usd=report.key_remaining_micro_usd,
            checks=[{"check": c.name, "ok": c.ok, "detail": c.detail} for c in checks],
        )


def connection_check(settings: AiAssistantSettings, **kwargs: Any) -> dict[str, Any]:
    """Model management's connection test for the remote profile: the preflight, no call."""

    report, _, _ = preflight(settings, **kwargs)
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


class RemoteTestModel:
    """The remote profile as the chat uses it in the test mode. Refuses a call (as an
    unavailable model, so the RM gets the case-data answer) unless the mode is still ready,
    the preflight passed, every earlier call is verified and the process call limit holds."""

    # The chat checks the synthetic boundary before it sends anything to this model.
    requires_synthetic_boundary = True

    def __init__(
        self,
        settings: AiAssistantSettings,
        *,
        environ: Mapping[str, str] | None = None,
        transport: object = None,
        fetch: Callable[[str], Any] = fetch_public,
        clock: Callable[[], float] = time.monotonic,
        background: bool = True,
    ) -> None:
        code = readiness(settings)
        if code is not None:
            raise ProfileConfigError(code, "the local synthetic test mode is not ready")
        endpoint = endpoint_for(settings)
        assert endpoint is not None  # checked by readiness
        self._settings = settings
        self._endpoint = endpoint
        self._environ = environ
        self._transport = transport
        self._fetch = fetch
        self._clock = clock
        self._background = background
        self._ledger_file = ledger_path(remote_settings(settings))
        self._credential = credentials.identity(credentials.resolve(environ)[0])
        self._inner = self._build_inner()
        try:
            self._start_call = BudgetLedger.open(self._ledger_file).last_call_id()
        except LedgerError:
            raise ProfileConfigError(
                "LEDGER_UNAVAILABLE", "the budget ledger is not usable"
            ) from None
        self._lock = threading.Lock()
        self._checked_at: float | None = None
        self._account: OpenRouterAccount | None = None

    def _build_inner(self) -> ChatModel:
        """The budget-guarded remote adapter with the current key (model_factory.py)."""

        remote = remote_settings(self._settings)
        if self._transport is not None:  # tests: an in-memory transport only
            return build_chat_model(
                remote,
                transport=self._transport,
                environ=self._environ,
                budget_ledger=self._ledger_file,
            )
        return build_chat_model(
            remote,
            environ=self._environ,
            budget_ledger=self._ledger_file,
            allow_live_network=True,
        )

    @property
    def name(self) -> str:
        return OPENROUTER_MODEL_ID

    @property
    def profile_id(self) -> str:
        return OPENROUTER_PROFILE_ID

    @property
    def endpoint_slug(self) -> str:
        return self._endpoint.slug

    def _refuse(self, reason: str) -> ModelCallError:
        log.warning("remote test call refused: %s", reason)
        return ModelCallError("budget_refused")

    def _ready(self, messages: list[dict[str, str]]) -> ChatModel:
        """Blocking (preflight requests, a bounded metadata wait): never on the event loop.
        Returns the guarded adapter to call (rebuilt when the key changed)."""

        # Defence in depth, whoever the caller is: the messages passed the D-095 eligibility
        # check (their single-use ticket) or the text part of the D-094 synthetic boundary.
        ticket = synthetic_eligibility.admitted(messages)
        if not (ticket and synthetic_eligibility.mode(self._settings)) and (
            check_messages(messages) is not None
        ):
            raise self._refuse("text outside the synthetic boundary")
        with self._lock:
            if readiness(self._settings) is not None:
                raise self._refuse("not ready")
            marker = credentials.identity(credentials.resolve(self._environ)[0])
            if marker is None:
                raise self._refuse("no usable key")
            if marker != self._credential:
                # Another key: rebuild with it, and run the full preflight (its limit, its
                # usage against the ledger) before it is used.
                try:
                    self._inner = self._build_inner()
                except ProfileConfigError:
                    raise self._refuse("model rebuild") from None
                self._credential, self._checked_at, self._account = marker, None, None
            ledger = BudgetLedger.open(self._ledger_file)
            # Calls since this model was built (activation or restart), open ones included.
            calls = len(ledger.closed_calls_after(self._start_call)) + ledger.status().open_calls
            if calls >= self._settings.local_api_test_max_calls:
                raise self._refuse("call limit")
            now = self._clock()
            stale = (
                self._checked_at is None
                or self._account is None
                or now - self._checked_at > self._settings.local_api_test_preflight_seconds
            )
            if stale:
                report, _, account = preflight(
                    self._settings,
                    environ=self._environ,
                    transport=self._transport,
                    fetch=self._fetch,
                )
                if not report.passed or account is None:
                    self._checked_at = None
                    raise self._refuse("preflight")
                self._account, self._checked_at = account, now
                return self._inner
            assert self._account is not None
            report = Preflight()
            verify_earlier_calls(report, ledger, self._account, self._endpoint)
            if not report.passed or ledger.status().breaker_open:
                raise self._refuse("verification")
            return self._inner

    def verify_now(self) -> Preflight:
        """Verify every closed call not yet verified (bounded wait for its metadata)."""

        report = Preflight()
        with self._lock:
            if self._account is None:
                report.add("verification.account", False, "no passing preflight yet")
                return report
            verify_earlier_calls(
                report, BudgetLedger.open(self._ledger_file), self._account, self._endpoint
            )
        return report

    def calls_since_start(self) -> list[ClosedCall]:
        """This model's closed calls, content-free (ledger rows)."""

        return BudgetLedger.open(self._ledger_file).closed_calls_after(self._start_call)

    def _verify_after(self) -> None:
        if not self._background:
            self.verify_now()
            return

        def work() -> None:
            try:
                self.verify_now()
            except Exception:  # the next call verifies again before it is made
                log.error("remote call verification failed; the next call checks again")

        threading.Thread(target=work, name="remote-verification", daemon=True).start()

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        inner = self._ready(messages)
        try:
            answer: ModelAnswer = inner.complete(messages)
            return answer
        finally:
            self._verify_after()

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


def is_remote_test_model(model: ChatModel | None) -> bool:
    return bool(getattr(model, "requires_synthetic_boundary", False))


def ledger_file(settings: AiAssistantSettings) -> Path:
    return ledger_path(remote_settings(settings))


def _usd(micro: int | None) -> str | None:
    return None if micro is None else f"{micro / 1_000_000:.6f}"


def _iso(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, UTC).isoformat().replace("+00:00", "Z")


def budget_status(
    settings: AiAssistantSettings, *, environ: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """The remote profile's spending view (read-only: the ledger is checked, never recovered
    or changed, and the provider is not asked; its limit is as the last preflight read it).
    Amounts are micro-USD integers, with a 6-decimal USD string beside each."""

    code = readiness(settings)
    view: dict[str, Any] = {
        "configured": settings.local_api_test_decision == TEST_DECISION_ID,
        "mode": "D-095" if synthetic_eligibility.mode(settings) else "D-094",
        "timezone": "Asia/Singapore",
        "daily_cap_ceiling_micro_usd": DAILY_CAP_CEILING_MICRO_USD,
        "daily_cap_micro_usd": settings.budget_daily_cap_micro_usd,
    }
    _, credential = credentials.resolve(environ)
    view["credential"] = credential.view()
    now = time.time()
    view["next_reset_at"] = _iso(next_singapore_reset_ms(int(now * 1000)) / 1000)
    with _provider_lock:
        provider = dict(_provider)
    view["provider"] = (
        {
            "checked_at": _iso(provider["checked_at"]),
            "passed": provider["passed"],
            "remaining_micro_usd": provider["remaining_micro_usd"],
            "remaining_usd": _usd(provider["remaining_micro_usd"]),
            "checks": provider["checks"],
        }
        if provider
        else None
    )
    refusal: str | None = code
    try:
        ledger = BudgetLedger(ledger_file(settings))
        ledger.verify()
        status = ledger.status()
        daily = ledger.daily_status(settings.budget_daily_cap_micro_usd)
    except LedgerError as error:
        view.update(ledger=None, daily=None, effective_remaining_micro_usd=0)
        view["effective_remaining_usd"] = _usd(0)
        view["refusal"] = refusal or error.code
        return view
    endpoint = endpoint_for(settings)
    reservation = (
        typical_reservation(
            endpoint, settings.llm_max_answer_tokens + settings.llm_reasoning_allowance_tokens
        )
        if endpoint is not None
        else None
    )
    view["ledger"] = {
        "cap_micro_usd": status.cap,
        "committed_micro_usd": status.committed,
        "headroom_micro_usd": status.headroom,
        "headroom_usd": _usd(max(status.headroom, 0)),
        "open_calls": status.open_calls,
        "breaker_open": status.breaker_open,
        "breaker_code": status.breaker_code,
    }
    view["daily"] = {
        "cap_micro_usd": daily.cap,
        "settled_today_micro_usd": daily.settled_today,
        "settled_today_usd": _usd(daily.settled_today),
        "in_flight_micro_usd": daily.open_reserved,
        "in_flight_usd": _usd(daily.open_reserved),
        "in_flight_calls": daily.open_calls,
        "remaining_micro_usd": daily.remaining,
        "remaining_usd": _usd(daily.remaining),
        "day_started_at": _iso(singapore_day_start_ms(int(now * 1000)) / 1000),
    }
    limits = [daily.remaining, max(status.headroom, 0)]
    if provider.get("remaining_micro_usd") is not None:
        limits.append(max(provider["remaining_micro_usd"], 0))
    effective = min(limits)
    view["effective_remaining_micro_usd"] = effective
    view["effective_remaining_usd"] = _usd(effective)
    view["reservation_micro_usd"] = reservation
    if refusal is None and credential.status != "configured":
        refusal = "CREDENTIAL_" + credential.status.upper()
    if refusal is None and status.breaker_open:
        refusal = f"BREAKER_OPEN:{status.breaker_code}"
    if refusal is None and daily.cap == 0:
        refusal = "DAILY_CAP_INVALID"
    if refusal is None and reservation is not None:
        if daily.remaining < reservation:
            refusal = "DAILY_ALLOWANCE_EXHAUSTED"
        elif status.headroom < reservation:
            refusal = "LIFETIME_CAP_EXHAUSTED"
        elif provider.get("remaining_micro_usd") is not None and (
            provider["remaining_micro_usd"] < reservation
        ):
            refusal = "PROVIDER_LIMIT_EXHAUSTED"
    if refusal is None and not provider:
        refusal = "PROVIDER_LIMIT_NOT_CHECKED"
    elif refusal is None and not provider["passed"]:
        refusal = "PROVIDER_CHECK_FAILED"
    view["refusal"] = refusal
    return view
