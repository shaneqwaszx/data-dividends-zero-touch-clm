"""AI model management (D-093): one application-wide active model, chosen by an HR
administrator from IT's local loopback profiles, with connection test, technical
qualification, activation, rollback and an audit history.

    HR (MODEL_CONFIG_MANAGE)   GET  /assistant/admin/models                 overview
                               POST /assistant/admin/models/{id}/connection-test
                               POST /assistant/admin/models/{id}/qualifications
                               GET  /assistant/admin/models/qualifications/{qid}
                               POST /assistant/admin/models/qualifications/{qid}/cancel
                               POST /assistant/admin/models/{id}/activate
                               POST /assistant/admin/models/rollback
                               GET  /assistant/admin/models/audit
                               GET  /assistant/admin/models/budget          (D-095)
                               GET  /assistant/admin/models/credential      (D-095 addendum)
                               PUT  /assistant/admin/models/credential
                               DELETE /assistant/admin/models/credential
                               PUT  /assistant/admin/models/budget/controls     (D-096)
                               PUT  /assistant/admin/models/budget/lifetime-cap
                               POST /assistant/admin/models/budget/provider-refresh

Who is asking, and whether they hold ``MODEL_CONFIG_MANAGE``, always comes from the CLM
backend with the caller's own session; activation and rollback ask again inside the lock
that applies them. Refusals of a signed-in caller are audited. Nothing here reads a case or
an answer record, and the browser can only name a profile id, except that an HR
administrator may hand the server an OpenRouter key when no environment or .env key exists
(key_sources.py): it is kept in server memory only and never sent back, logged or audited;
changing it needs the Origin header of an allowed page and is rate limited.

D-096: an HR administrator also sets the remote model's spending controls here: the daily
allowance per Singapore day (D-098: US$1.00 by default) and the calls per activation (1 to
200), stored in the model state database (compare-and-set, every process reads them per
request, applied to the active model without a restart or a new activation, its call count
kept); the ledger's lifetime cap, from the key's opening provider usage up (a raise of either
limit needs the amount confirmed, a key limit that never resets and the reconciliation checks
against OpenRouter); and a read-only refresh of the key's OpenRouter limit. Spend, calls and
ledger history are never reset, no ledger is created, and neither the key nor its
OpenRouter limit is changed.

Switching is atomic: each answer takes one snapshot of the active model when it starts and
keeps it to the end, and the choice is a compare-and-set on the stored revision, which every
request checks (so a restart, or a second service process, uses the same model). At start,
a stored model that is missing, changed, no longer selectable, qualified against older code,
or cannot be built is replaced by the environment baseline, with the reason audited. A model
failing at run time is never switched automatically: the RM gets the deterministic case-data
answer and an administrator decides.
"""

import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Annotated, Any

import anyio
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StrictInt

from . import key_sources
from .budget import MAX_MICRO_USD, BudgetedChatModel, BudgetLedger, LedgerError
from .clm_client import SESSION_COOKIE_NAME, ClmBackendClient, ClmBackendError
from .config import AiAssistantSettings
from .llm import ChatModel, OpenAICompatibleChatModel
from .model_admin_store import (
    DAILY_CAP_MAX_MICRO_USD,
    MAX_CALLS_RANGE,
    Activation,
    Choice,
    ModelAdminStore,
    QualificationBlocked,
    QualificationBusy,
    RevisionConflict,
    SpendingControls,
    apply_controls,
    valid_controls,
)
from .model_catalog import (
    BASELINE_ID,
    OPENROUTER_FAST_PROFILE_ID,
    BoundedPromptModel,
    Catalogue,
    CatalogueEntry,
    baseline_entry,
    build_baseline_adapter,
    build_profile_model,
    load_catalogue,
    profiles_path,
)
from .model_factory import ASSISTANT_DIR
from .model_profiles import OPENROUTER_PROFILE_ID, ProfileConfigError
from .model_qualification import connection_test, qualification_basis, quality_state
from .remote_test import (
    RemoteTestModel,
    budget_status,
    connection_check,
    forget_provider,
    ledger_file,
    preflight,
    qualification_manifest,
)

log = logging.getLogger("ai_assistant.model_admin")

CAPABILITY = "MODEL_CONFIG_MANAGE"
# D-098 (owner: GPT-OSS only, no substitute model): what a GPT-OSS activation that can no
# longer be used reverts to. No model at all: every answer is the case-data answer. It is
# stored like an activation (audited, kept across restarts) until HR activates a model.
CASE_DATA_ONLY_ID = "case_data_only"
# The remote GPT-OSS configurations (catalogue source "code"), listed or not.
REMOTE_PROFILE_IDS = frozenset({OPENROUTER_PROFILE_ID, OPENROUTER_FAST_PROFILE_ID})
SYSTEM_ACTOR = "system"
_QUALIFICATION_ID = re.compile(r"[0-9a-f]{32}")
# The qualification runs the dev-only evaluation harness in its own process (never in this one).
QUALIFY_SCRIPT = ASSISTANT_DIR / "scripts" / "qualify_model.py"
# How often the service checks a running qualification process, and how long a cancelled
# one may take to stop by itself before it is ended.
SUPERVISE_SECONDS = 1.0
CANCEL_GRACE_SECONDS = 15.0
# Extra time a process gets beyond its own limit before the service ends it.
DEADLINE_GRACE_SECONDS = 60.0
# Key changes (D-095 addendum): at most this many attempts per administrator in the window.
CREDENTIAL_ATTEMPTS = 5
CREDENTIAL_WINDOW_SECONDS = 600.0
MAX_CREDENTIAL_BODY = 1024
# HR spending changes and provider-limit refreshes (D-096), per administrator in the window.
BUDGET_ATTEMPTS = 20
# D-098: at most one audit event a minute for sessions refused while a qualification runs.
SESSION_AUDIT_SECONDS = 60.0
# D-098: what any increase of spending authority (the daily limit or the lifetime cap) needs
# from a fresh, free preflight: a finite key limit that never resets, and a reconciled ledger.
PROVIDER_LIMIT_CHECKS = ("key.limit_set", "key.limit_never_resets")
CAP_RAISE_CHECKS = ("ledger.breaker_closed_no_open_calls", "ledger.usage_reconciled")
INCREASE_CHECKS = PROVIDER_LIMIT_CHECKS + CAP_RAISE_CHECKS

# Fixed messages only (the browser shows these and nothing else from a refusal).
MESSAGES = {
    "MODEL_CONFIG_FORBIDDEN": "You are not allowed to do this.",
    "MODEL_MANAGEMENT_OFF": "Model management is not configured on this server.",
    "PROFILE_UNKNOWN": "No such model profile.",
    "PROFILE_NOT_SELECTABLE": "This model profile is not available for use.",
    "REMOTE_NOT_AUTHORISED": "Remote models are not authorised for use in the CLM.",
    "MODEL_DISABLED_BY_ENVIRONMENT": "The AI model is switched off on this server.",
    "NOT_LOOPBACK": "Only a local loopback model can be qualified.",
    "BUILD_FAILED": "The model could not be prepared on the server.",
    "QUALIFICATION_BUSY": "Another qualification is running. Wait for it to finish.",
    "QUALIFICATION_UNKNOWN": "No such qualification run.",
    "QUALIFICATION_UNAVAILABLE": "Qualification is not available on this server.",
    "REVISION_CONFLICT": "The model settings changed since this view. Refresh and try again.",
    "NOT_QUALIFIED": "This model has no passing qualification for the current configuration.",
    "ACKNOWLEDGEMENT_REQUIRED": "Confirm that answer quality is not scored before activating.",
    "CONNECTION_FAILED": "The model did not pass the connection test.",
    "NO_ROLLBACK_TARGET": "There is no earlier model to roll back to.",
    "ALREADY_ACTIVE": "This model is already active.",
    "REMOTE_MANIFEST_MISSING": (
        "The paid qualification's question list and count are not configured on the server."
    ),
    "CREDENTIAL_INVALID": "That is not an OpenRouter API key. Nothing was saved.",
    "CREDENTIAL_ENVIRONMENT_MANAGED": (
        "The OpenRouter key is set on the server (environment or .env) and cannot be changed here."
    ),
    "CREDENTIAL_NOT_HR_MANAGED": "There is no key entered here to clear.",
    "CREDENTIAL_RATE_LIMITED": "Too many key changes. Wait a few minutes and try again.",
    "ORIGIN_REQUIRED": "This change must come from the AI Models page.",
    # D-096: HR spending controls.
    "CONTROLS_INVALID": (
        "The daily limit must be US$0.00 or more and the call limit 1 to 200. Nothing changed."
    ),
    "CONTROLS_CONFLICT": "The spending limits changed since this view. Refresh and try again.",
    "BUDGET_RATE_LIMITED": "Too many spending changes. Wait a few minutes and try again.",
    "LEDGER_UNAVAILABLE": "The spending ledger is missing or not usable. Nothing changed.",
    "CAP_OUT_OF_RANGE": "The lifetime limit cannot be below the key's opening usage.",
    "CAP_CONFIRMATION_REQUIRED": "Confirm the new lifetime limit to raise it. Nothing changed.",
    "RECONCILIATION_REQUIRED": (
        "The ledger must be reconciled with OpenRouter (no open call, no stop, usage accounted"
        " for) before a limit can be raised. Nothing changed."
    ),
    "PROVIDER_CHECK_FAILED": "The OpenRouter key could not be checked. Nothing changed.",
    # D-098: raising a limit needs a provider-side backstop.
    "DAILY_CONFIRMATION_REQUIRED": "Confirm the new daily limit to raise it. Nothing changed.",
    "PROVIDER_LIMIT_REQUIRED": (
        "A limit can only be raised while the OpenRouter key has its own limit that never"
        " resets. Nothing changed."
    ),
    # D-098: a paid qualification is confirmed, and refused before it starts if it cannot end.
    "ESCALATION_REQUIRED": (
        "This model failed a safety, answer, capacity or verification check. It can be"
        " qualified again only after IT changes its settings. Nothing started."
    ),
    "PAID_CONFIRMATION_REQUIRED": (
        "Confirm the number of paid calls this qualification makes. Nothing started."
    ),
    "QUALIFICATION_BUDGET_TOO_LOW": (
        "The spending limits do not leave room for a paid call of this qualification."
        " Nothing started."
    ),
}


# --- D-098: the Recovery Centre's diagnosis (closed codes only; the page words them) --------
#
# Every problem gets one category and one recommended action. HR may act on RECOVERABLE_BY_HR
# and QUALIFICATION_REQUIRED (and retry a TEMPORARILY_UNAVAILABLE one later); the others need an
# operator or IT, and no ordinary action can bypass them (gates, thresholds, the breaker,
# provider verification and synthetic eligibility are not settings).

HEALTHY = "HEALTHY"
QUALIFICATION_REQUIRED = "QUALIFICATION_REQUIRED"
RECOVERABLE_BY_HR = "RECOVERABLE_BY_HR"
TEMPORARILY_UNAVAILABLE = "TEMPORARILY_UNAVAILABLE"
OPERATOR_REQUIRED = "OPERATOR_REQUIRED"
POLICY_BLOCKED = "POLICY_BLOCKED"
_CATEGORY_ORDER = (
    HEALTHY,
    QUALIFICATION_REQUIRED,
    RECOVERABLE_BY_HR,
    TEMPORARILY_UNAVAILABLE,
    OPERATOR_REQUIRED,
    POLICY_BLOCKED,
)
# The settings and decisions only IT or the owner can change (remote_test.readiness codes).
_POLICY_CODES = frozenset(
    {
        "REMOTE_NOT_AUTHORISED",
        "MODEL_DISABLED_BY_ENVIRONMENT",
        "DECISION_INTERLOCK",
        "NOT_DEVELOPMENT_ENVIRONMENT",
        "OWNER_ATTESTATION_MISSING",
        "ENDPOINT_NOT_APPROVED",
        "REMOTE_SETTINGS_INVALID",
    }
)
# (category, action, retryable) for a spending-view refusal or a closed run/start-up code.
_SERVICE_CODES: dict[str, tuple[str, str, bool]] = {
    "CREDENTIAL_MISSING": (RECOVERABLE_BY_HR, "ENTER_KEY", True),
    "CREDENTIAL_INVALID": (RECOVERABLE_BY_HR, "ENTER_KEY", True),
    "DAILY_CAP_INVALID": (RECOVERABLE_BY_HR, "REVIEW_BUDGET", True),
    "DAILY_ALLOWANCE_EXHAUSTED": (RECOVERABLE_BY_HR, "REVIEW_BUDGET", True),
    "LIFETIME_CAP_EXHAUSTED": (RECOVERABLE_BY_HR, "REVIEW_BUDGET", True),
    "CALL_LIMIT_REACHED": (RECOVERABLE_BY_HR, "REVIEW_BUDGET", True),
    "PROVIDER_LIMIT_NOT_CHECKED": (RECOVERABLE_BY_HR, "REFRESH_LIMITS", True),
    "PROVIDER_CHECK_FAILED": (TEMPORARILY_UNAVAILABLE, "REFRESH_LIMITS", True),
    "PROVIDER_LIMIT_EXHAUSTED": (OPERATOR_REQUIRED, "CONTACT_OPERATOR", False),
    "QUALIFICATION_OUT_OF_DATE": (QUALIFICATION_REQUIRED, "RUN_QUALIFICATION", True),
    "NOT_QUALIFIED": (QUALIFICATION_REQUIRED, "RUN_QUALIFICATION", True),
    "CONFIG_MISMATCH": (QUALIFICATION_REQUIRED, "RUN_QUALIFICATION", True),
    "CANCELLED": (QUALIFICATION_REQUIRED, "RUN_QUALIFICATION", True),
    "DEADLINE": (TEMPORARILY_UNAVAILABLE, "RUN_QUALIFICATION", True),
    "STALE": (TEMPORARILY_UNAVAILABLE, "RUN_QUALIFICATION", True),
    "PROCESS_EXITED": (TEMPORARILY_UNAVAILABLE, "RUN_QUALIFICATION", True),
    "HARNESS_ERROR": (TEMPORARILY_UNAVAILABLE, "RUN_QUALIFICATION", True),
    "REMOTE_MANIFEST_MISSING": (OPERATOR_REQUIRED, "CONTACT_IT", False),
    "QUALIFICATION_UNAVAILABLE": (OPERATOR_REQUIRED, "CONTACT_IT", False),
    "LEDGER_UNAVAILABLE": (OPERATOR_REQUIRED, "CONTACT_OPERATOR", False),
    "PROFILE_MISSING": (OPERATOR_REQUIRED, "CONTACT_IT", False),
    "PROFILE_CHANGED": (QUALIFICATION_REQUIRED, "RUN_QUALIFICATION", True),
    "PROFILE_UNAVAILABLE": (OPERATOR_REQUIRED, "CONTACT_IT", False),
}
# Qualification gates (model_qualification.py): what a failure means for HR. G-3 (an unsafe
# line), G-6 (answer validity), G-7 (capacity) and G-8 (provider verification) are never
# retried away: they go to IT or an operator.
_GATE_CODES: dict[str, tuple[str, str, bool]] = {
    "G-1": (TEMPORARILY_UNAVAILABLE, "TEST_CONNECTION", True),
    "G-2": (TEMPORARILY_UNAVAILABLE, "RUN_QUALIFICATION", True),
    "G-3": (POLICY_BLOCKED, "CONTACT_IT", False),
    "G-4": (TEMPORARILY_UNAVAILABLE, "REVIEW_BUDGET", True),
    "G-6": (OPERATOR_REQUIRED, "CONTACT_IT", False),
    "G-7": (OPERATOR_REQUIRED, "CONTACT_IT", False),
    "G-8": (OPERATOR_REQUIRED, "CONTACT_OPERATOR", False),
}
# Gates whose failure blocks a new run of the same configuration and code (post_qualification).
_ESCALATION_GATES = frozenset({"G-3", "G-6", "G-7", "G-8"})


def escalation_gates_failed(code: str) -> bool:
    """A run's code names a gate whose failure blocks a new run of the same configuration."""

    if not code.startswith("GATES_FAILED:"):
        return False
    return any(gate in _ESCALATION_GATES for gate in code.removeprefix("GATES_FAILED:").split(","))


# Preflight checks (remote_checks.py) behind a failed connection (G-1).
_CHECK_CODES: dict[str, tuple[str, str, bool]] = {
    "key.status": (TEMPORARILY_UNAVAILABLE, "TEST_CONNECTION", True),
    "endpoint.listing": (TEMPORARILY_UNAVAILABLE, "TEST_CONNECTION", True),
    "ledger.headroom_for_one_call": (RECOVERABLE_BY_HR, "REVIEW_BUDGET", True),
    "ledger.daily_room_for_one_call": (RECOVERABLE_BY_HR, "REVIEW_BUDGET", True),
    "ledger.cap_above_opening": (RECOVERABLE_BY_HR, "REVIEW_BUDGET", True),
    "ledger.healthy": (OPERATOR_REQUIRED, "CONTACT_OPERATOR", False),
    "ledger.breaker_closed_no_open_calls": (OPERATOR_REQUIRED, "CONTACT_OPERATOR", False),
    "ledger.usage_reconciled": (OPERATOR_REQUIRED, "CONTACT_OPERATOR", False),
    "ledger.earlier_calls_verified": (OPERATOR_REQUIRED, "CONTACT_OPERATOR", False),
    "test_mode.ready": (POLICY_BLOCKED, "CONTACT_IT", False),
    "gate.account": (POLICY_BLOCKED, "CONTACT_IT", False),
}


def _classified(code: str, table: dict[str, tuple[str, str, bool]]) -> tuple[str, str, bool]:
    """(category, action, retryable) for a code: its own entry, else by kind; anything not
    known needs an operator (never a retry)."""

    if code in table:
        return table[code]
    if code in _SERVICE_CODES:
        return _SERVICE_CODES[code]
    if code in _POLICY_CODES or code.startswith("owner."):
        return POLICY_BLOCKED, "CONTACT_IT", False
    if code.startswith("endpoint."):
        # The provider's listing changed (price, quantization, ZDR, provider): IT reviews.
        return POLICY_BLOCKED, "CONTACT_IT", False
    if code.startswith("key."):
        # The key's own settings live in the OpenRouter dashboard: the owner changes them.
        return OPERATOR_REQUIRED, "CONTACT_OPERATOR", False
    return OPERATOR_REQUIRED, "CONTACT_OPERATOR", False


def _finding(code: str, table: dict[str, tuple[str, str, bool]], **extra: Any) -> dict[str, Any]:
    category, action, retryable = _classified(code, table)
    return {"code": code, "category": category, "action": action, "retryable": retryable, **extra}


def diagnose_qualification(item: dict[str, Any] | None) -> dict[str, Any] | None:
    """Why a qualification run did not pass, gate by gate, as closed codes (None: it passed,
    is running, or never ran)."""

    if item is None or item["status"] in ("passed", "running"):
        return None
    code = str(item.get("code") or "HARNESS_ERROR")
    summary = item.get("summary") or {}
    findings: list[dict[str, Any]] = []
    if code.startswith("GATES_FAILED:"):
        for gate in code.removeprefix("GATES_FAILED:").split(","):
            if gate == "G-1":
                connection = summary.get("connection") or item.get("connection") or {}
                checks = [c["check"] for c in connection.get("checks") or [] if not c.get("ok")]
                for check in checks or ["key.status"]:
                    findings.append(_finding(check, _CHECK_CODES, gate="G-1"))
                continue
            findings.append(_finding(gate, _GATE_CODES, gate=gate))
    else:
        findings.append(_finding(code, _SERVICE_CODES))
    worst = max(findings, key=lambda f: _CATEGORY_ORDER.index(f["category"]))
    return {
        "code": code,
        "category": worst["category"],
        "action": worst["action"],
        "retryable": all(f["retryable"] for f in findings),
        "findings": findings,
    }


def diagnose_service(
    *,
    active: dict[str, Any],
    profiles: list[dict[str, Any]],
    budget: dict[str, Any] | None,
) -> dict[str, Any]:
    """The recovery view: the active model's state, what stops it now, and each profile of the
    remote model, each with one category and one action to take. Closed codes and numbers
    only (no key, prompt, answer or case data)."""

    issues: list[dict[str, Any]] = []
    active_view = next((p for p in profiles if p["profile_id"] == active["profile_id"]), None)
    remote_active = bool(active_view and active_view.get("deployment") == "openrouter")
    if active.get("reverted"):
        issues.append(_finding(str(active["reverted"]), _SERVICE_CODES, scope="ACTIVE"))
    if active.get("config_changed"):
        issues.append(_finding("PROFILE_CHANGED", _SERVICE_CODES, scope="ACTIVE"))
    if budget is not None and budget.get("configured") and (remote_active or not issues):
        refusal = budget.get("refusal")
        if refusal and (remote_active or refusal not in _POLICY_CODES):
            issues.append(_finding(str(refusal), _SERVICE_CODES, scope="SPENDING"))
        controls = budget.get("controls") or {}
        if remote_active and controls.get("calls_remaining") == 0:
            issues.append(_finding("CALL_LIMIT_REACHED", _SERVICE_CODES, scope="SPENDING"))
    configurations = []
    for item in profiles:
        if item.get("source") != "code":
            continue
        diagnosis = diagnose_qualification(item.get("qualification"))
        blockers = list(item.get("activation_blockers") or [])
        reason = item.get("reason")
        if item.get("status") != "selectable" and reason:
            state = _finding(str(reason), _SERVICE_CODES)
        elif diagnosis is not None:
            state = {key: diagnosis[key] for key in ("code", "category", "action", "retryable")}
        elif blockers:
            state = _finding(str(blockers[0]), _SERVICE_CODES)
        else:
            state = {"code": None, "category": HEALTHY, "action": "NONE", "retryable": False}
        configurations.append(
            {
                "profile_id": item["profile_id"],
                "active": bool(item.get("active")),
                "qualified": not blockers and item.get("status") == "selectable",
                "previous_pass_current": item.get("previous_pass_current", False),
                # D-098: the activation in use keeps the passing run it was activated with
                # (checked when it was built); a later failed run does not end it, it only
                # stops a new activation. Not so once IT changed the profile's settings.
                "active_qualification_current": bool(item.get("active"))
                and active.get("qualification_id") is not None
                and not active.get("config_changed"),
                "state": state,
                "qualification": diagnosis,
            }
        )
    alternatives = [
        c["profile_id"]
        for c in configurations
        if remote_active and not c["active"] and c["qualified"]
    ]
    status = max((i["category"] for i in issues), key=_CATEGORY_ORDER.index) if issues else HEALTHY
    if (
        not remote_active
        and status == HEALTHY
        and configurations
        and not any(c["qualified"] for c in configurations)
    ):
        # The remote model is not in use and no configuration could be: say why.
        status = min((c["state"]["category"] for c in configurations), key=_CATEGORY_ORDER.index)
    first = issues[0] if issues else None
    return {
        "status": status,
        "remote_active": remote_active,
        "action": first["action"] if first else "NONE",
        "issues": issues,
        "remote_profiles": configurations,
        "other_qualified": alternatives,
    }


def _refusal(status: int, code: str, message_code: str | None = None) -> HTTPException:
    return HTTPException(
        status_code=status,
        # A configuration code with no message of its own (for example CREDENTIAL_MISSING)
        # shows the generic fixed message; the code itself is still returned.
        detail={
            "code": code,
            "message": MESSAGES.get(message_code or code, MESSAGES["BUILD_FAILED"]),
        },
    )


@dataclass(frozen=True)
class Active:
    """The model answers use, as one immutable snapshot."""

    revision: int
    profile_id: str
    fingerprint: str
    model: ChatModel | None
    base_url: str | None
    prompt_limit: int | None = None
    qualification_id: str | None = None
    reverted: str | None = None
    # A remote configuration's own settings (its reasoning effort), kept when HR controls apply.
    settings_update: tuple[tuple[str, object], ...] = ()


class ModelSelector:
    """Holds the active model. Without a store (no profiles file, the model switched off, or a
    model passed in by tests and the evaluation harness) it is fixed: today's behaviour."""

    def __init__(
        self,
        settings: AiAssistantSettings,
        baseline_model: ChatModel | None,
        store: ModelAdminStore | None = None,
        *,
        environ: dict[str, str] | None = None,
        transport: object = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.environ = environ
        self.transport = transport
        # The public listing reader for the D-094 preflight (tests replace it).
        self.fetch: Callable[[str], Any] | None = None
        # Starts the qualification process for a recorded run (tests run it in-process).
        self.launch: Callable[[str], Any] = self._launch_process
        self._baseline_model = baseline_model
        self.baseline = baseline_entry(settings)
        self._lock = threading.Lock()
        # Serialises administrator changes in this process (the store's CAS covers others).
        self.change_lock = threading.Lock()
        # Which HR spending controls (model object, revision) the active model runs with.
        self._controls_lock = threading.Lock()
        self._controls_applied: tuple[int, int] | None = None
        self._active = self._baseline(0)
        if store is not None:
            self._active = replace(self._active, revision=-1)
            self.current()

    @property
    def managed(self) -> bool:
        return self.store is not None

    def _launch_process(self, qualification_id: str) -> "subprocess.Popen[bytes]":
        """``scripts/qualify_model.py`` for one recorded run: fixed arguments only (the id,
        and this service's own state database and profiles file); no output is kept."""

        path = profiles_path(self.settings)
        if not QUALIFY_SCRIPT.is_file() or path is None:
            raise ProfileConfigError("QUALIFICATION_UNAVAILABLE", "the harness is not installed")
        return subprocess.Popen(
            [
                sys.executable,
                str(QUALIFY_SCRIPT),
                "--qualification-id",
                qualification_id,
                "--db",
                str(store_file(self.settings)),
                "--profiles",
                str(path),
            ],
            cwd=ASSISTANT_DIR,
            env=qualification_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def baseline_choice(self) -> Choice:
        return Choice(BASELINE_ID, self.baseline.fingerprint)

    def _baseline(self, revision: int, reverted: str | None = None) -> Active:
        return Active(
            revision=revision,
            profile_id=BASELINE_ID,
            fingerprint=self.baseline.fingerprint,
            model=self._baseline_model,
            base_url=self.settings.llm_base_url,
            reverted=reverted,
        )

    def case_data_only_choice(self) -> Choice:
        return Choice(CASE_DATA_ONLY_ID, CASE_DATA_ONLY_ID)

    def _case_data_only(self, revision: int, reverted: str | None = None) -> Active:
        return Active(
            revision=revision,
            profile_id=CASE_DATA_ONLY_ID,
            fingerprint=CASE_DATA_ONLY_ID,
            model=None,
            base_url=None,
            reverted=reverted,
        )

    def current(self) -> Active:
        """The active model for one request (read once, used for the whole answer), with the
        HR spending controls that apply now (another process may have changed them)."""

        active = self._current()
        self.sync_controls(active)
        return active

    def _current(self) -> Active:
        if self.store is None:
            return self._active
        try:
            revision = self.store.revision()
        except Exception:
            log.error("model state unavailable; keeping the current model")
            return self._active
        if revision == self._active.revision:
            return self._active
        with self._lock:
            try:
                if self.store.revision() != self._active.revision:
                    self._active = self._restore()
            except Exception:
                # Never fail an answer on model state: keep the model already in use.
                log.error("model state could not be reloaded; keeping the current model")
            return self._active

    # --- HR spending controls (D-096) -------------------------------------------------------

    def spending_controls(self) -> SpendingControls | None:
        """The stored controls (revision 0 when never set), or None when unreadable."""

        if self.store is None:
            return SpendingControls(0, None, None, None, None)
        try:
            return self.store.spending_controls()
        except Exception:
            log.error("spending controls unavailable; no daily allowance until they are")
            return None

    def controlled(self) -> AiAssistantSettings:
        """The settings the remote model runs with: HR values in place of the environment
        defaults; unreadable controls fail closed (no daily allowance)."""

        return apply_controls(self.settings, self.spending_controls())

    def sync_controls(self, active: Active | None = None) -> None:
        """Put the current HR controls into the active remote model in place, so a change
        applies without a restart or a new activation and its call count is kept.

        remote_test.py is part of the qualification basis (changing it would make every
        earlier qualification out of date), so this module sets the model's settings and its
        budget guard's daily cap; both are read under the model's own lock or per reservation.
        The daily cap is still enforced by the ledger inside its admission transaction."""

        current = active or self._active
        model = current.model
        if not isinstance(model, RemoteTestModel):
            return
        # Read inside the lock that applies them, so a late reader can never put an older
        # revision back over a newer one.
        with self._controls_lock:
            controls = self.spending_controls()
            key = (id(model), controls.revision if controls is not None else -1)
            if self._controls_applied == key and controls is not None:
                return
            settings = apply_controls(self.settings, controls)
            if current.settings_update:  # the configuration's own reasoning effort stays
                settings = settings.model_copy(update=dict(current.settings_update))
            with model._lock:  # noqa: SLF001 - see the docstring
                model._settings = settings  # noqa: SLF001
                inner = model._inner  # noqa: SLF001
                if isinstance(inner, BudgetedChatModel):
                    inner._daily_cap = settings.budget_daily_cap_micro_usd  # noqa: SLF001
            self._controls_applied = key

    def calls_used(self) -> int | None:
        """Calls the active remote model made since its activation or this service's start
        (open calls included), as its own call limit counts them; None when it is not active.
        Read-only: the ledger is checked, never recovered or changed."""

        model = self._active.model
        if not isinstance(model, RemoteTestModel):
            return None
        ledger = BudgetLedger(model._ledger_file)  # noqa: SLF001 - see sync_controls
        ledger.verify()
        start = model._start_call  # noqa: SLF001
        return len(ledger.closed_calls_after(start)) + ledger.status().open_calls

    def _restore(self) -> Active:
        assert self.store is not None
        for _ in range(3):
            stored = self.store.activation(self.baseline_choice())
            if stored.active_profile_id == BASELINE_ID:
                return self._baseline(stored.revision)
            if stored.active_profile_id == CASE_DATA_ONLY_ID:
                return self._case_data_only(stored.revision)
            active, problem = self._build_stored(stored)
            if active is not None:
                return active
            # D-098: a GPT-OSS configuration is never replaced by another model (the
            # environment baseline may be a local one): it reverts to no model.
            remote = stored.active_profile_id in REMOTE_PROFILE_IDS
            try:
                revision = self.store.activate(
                    stored.revision,
                    self.case_data_only_choice() if remote else self.baseline_choice(),
                    _last_good(stored),
                    SYSTEM_ACTOR,
                )
            except RevisionConflict:
                continue
            self.store.record(
                actor=SYSTEM_ACTOR,
                role=None,
                action="STARTUP_REVERTED",
                outcome="reverted",
                profile_id=stored.active_profile_id,
                fingerprint=stored.active_fingerprint,
                code=problem,
                revision=revision,
            )
            if remote:
                return self._case_data_only(revision, reverted=problem)
            return self._baseline(revision, reverted=problem)
        if self._active.profile_id in REMOTE_PROFILE_IDS | {CASE_DATA_ONLY_ID}:
            return self._case_data_only(self._active.revision)
        return self._baseline(self._active.revision)

    def remote_options(self) -> dict[str, Any]:
        """The D-094 remote model's test seams (tests only; None in the service)."""

        options: dict[str, Any] = {"environ": self.environ, "transport": self.transport}
        if self.fetch is not None:
            options["fetch"] = self.fetch
        return options

    def _build_stored(self, stored: Activation) -> tuple[Active | None, str]:
        assert self.store is not None
        if not self.settings.llm_enabled:
            return None, "MODEL_DISABLED_BY_ENVIRONMENT"
        entry = load_catalogue(self.settings).get(stored.active_profile_id)
        if entry is None or entry.source not in ("file", "code"):
            return None, "PROFILE_MISSING"
        if entry.status != "selectable":
            return None, "PROFILE_UNAVAILABLE"
        if entry.fingerprint != stored.active_fingerprint:
            return None, "PROFILE_CHANGED"
        qualification = (
            self.store.qualification(stored.active_qualification_id)
            if stored.active_qualification_id
            else None
        )
        if (
            qualification is None
            or qualification["status"] != "passed"
            or qualification["basis"] != qualification_basis()
            or not stored.active_prompt_limit
        ):
            return None, "QUALIFICATION_OUT_OF_DATE"
        if entry.source == "code":
            # D-094: the remote model, gated per call and per case (remote_test.py).
            try:
                remote = RemoteTestModel(
                    entry.settings_for(self.controlled()), **self.remote_options()
                )
            except ProfileConfigError as exc:
                return None, exc.code
            return (
                Active(
                    revision=stored.revision,
                    profile_id=entry.profile_id,
                    fingerprint=entry.fingerprint,
                    model=remote,
                    base_url=None,
                    prompt_limit=stored.active_prompt_limit,
                    qualification_id=stored.active_qualification_id,
                    settings_update=entry.settings_update,
                ),
                "",
            )
        try:
            adapter = build_profile_model(entry, environ=self.environ, transport=self.transport)
        except ProfileConfigError as exc:
            return None, exc.code
        return (
            Active(
                revision=stored.revision,
                profile_id=entry.profile_id,
                fingerprint=entry.fingerprint,
                model=BoundedPromptModel(adapter, stored.active_prompt_limit),
                base_url=entry.base_url,
                prompt_limit=stored.active_prompt_limit,
                qualification_id=stored.active_qualification_id,
            ),
            "",
        )

    def apply(self, expected: int, choice: Choice, previous: Choice | None, by: str) -> Active:
        """Store the change (compare-and-set) and swap the in-memory model atomically."""

        assert self.store is not None
        with self._lock:
            before = self.store.activation(self.baseline_choice())
            revision = self.store.activate(expected, choice, previous, by)
            stored = self.store.activation(self.baseline_choice())
            if choice.profile_id == BASELINE_ID:
                self._active = self._baseline(revision)
                return self._active
            active, problem = self._build_stored(stored)
            if active is not None:
                self._active = active
                return self._active
            # Changed between the checks and the store: put the previous model back (as it
            # was, last good model included), record that, and restore it as at start-up
            # (which falls back to the baseline, audited, if it is no longer usable either).
            # D-098: exactly the activation that was in place (no model included), never a
            # substitute for it.
            was = Choice(
                before.active_profile_id,
                before.active_fingerprint,
                before.active_qualification_id,
                before.active_prompt_limit,
            )
            undo = self.store.activate(revision, was, _last_good(before), by)
            self.store.record(
                actor=by,
                role=None,
                action="ACTIVATION_UNDONE",
                outcome="reverted",
                profile_id=choice.profile_id,
                fingerprint=choice.fingerprint,
                code=problem or "BUILD_FAILED",
                revision=undo,
            )
            self._active = self._restore()
            raise ProfileConfigError(problem or "BUILD_FAILED", "activation undone")


def qualification_environment() -> dict[str, str] | None:
    """The qualification process's environment: this one's, plus an HR-entered key (which only
    this process's memory holds) as OPENROUTER_API_KEY. Never on its command line; None (the
    inherited environment) when the key comes from the environment or .env, or there is none."""

    key, status = key_sources.resolve()
    if key is None or status.source != "hr_memory":
        return None
    return {**os.environ, key_sources.CREDENTIAL_VARIABLE: key.get_secret_value()}


def _last_good(stored: Activation) -> Choice | None:
    if stored.last_good_profile_id is None or stored.last_good_fingerprint is None:
        return None
    return Choice(
        stored.last_good_profile_id,
        stored.last_good_fingerprint,
        stored.last_good_qualification_id,
        stored.last_good_prompt_limit,
    )


def open_selector(
    settings: AiAssistantSettings, baseline_model: ChatModel | None, injected: bool
) -> ModelSelector:
    """Managed only when IT named a profiles file, the model is on, and the model was not
    passed in (tests and the evaluation harness keep a fixed model)."""

    if injected or not settings.llm_enabled or not settings.model_profiles_file:
        return ModelSelector(settings, baseline_model)
    return ModelSelector(settings, baseline_model, ModelAdminStore(store_file(settings)))


def store_file(settings: AiAssistantSettings) -> Path:
    path = Path(settings.model_admin_db_path)
    return path if path.is_absolute() else ASSISTANT_DIR / path


class ChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=0)
    acknowledge_quality_unscored: bool = False


class SpendingControlsRequest(BaseModel):
    """Both controls at once; bounds are checked by the route (a fixed refusal message)."""

    model_config = ConfigDict(extra="forbid")

    expected_revision: StrictInt = Field(ge=0)
    daily_cap_micro_usd: StrictInt
    max_calls: StrictInt
    # D-098: a raise of the daily limit needs the same amount again (the HR confirmation step).
    confirm_daily_cap_micro_usd: StrictInt | None = None


class QualificationRequest(BaseModel):
    """A paid (remote) qualification needs its number of paid calls repeated back (the HR
    confirmation step); a local one needs no body."""

    model_config = ConfigDict(extra="forbid")

    confirm_paid_calls: StrictInt | None = None


class LifetimeCapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cap_micro_usd: StrictInt
    # A raise needs the same amount again (the HR confirmation step).
    confirm_cap_micro_usd: StrictInt | None = None
    # D-098: the cap the page showed (the ledger's own revision for the cap). A raise needs it
    # and is refused if the cap changed since; a decrease checks it when it is sent.
    expected_cap_micro_usd: StrictInt | None = None


def model_admin_router(
    *,
    selector: ModelSelector,
    backend: ClmBackendClient,
    check_origin: Callable[[Request], None],
) -> APIRouter:
    router = APIRouter(prefix="/assistant/admin/models")
    settings = selector.settings

    def audit(profile: dict[str, Any], action: str, outcome: str, **fields: Any) -> None:
        if selector.store is None:
            return
        selector.store.record(
            actor=str(profile.get("user_id") or "unknown"),
            role=str(profile.get("role")) if profile.get("role") else None,
            action=action,
            outcome=outcome,
            **fields,
        )

    rejected_at = [0.0]  # the last refused-session audit event (at most one per window)

    def session_rejected(exc: ClmBackendError) -> None:
        """D-098 diagnostics: a refused session while a qualification runs is logged and (at
        most once a minute) audited, with codes only, so a sign-out can be found. Nothing
        about the run changes: it carries on in its own process."""

        if exc.status_code != 401 or selector.store is None:
            return
        try:
            running = selector.store.running_qualification()
        except Exception:
            return
        if running is None:
            return
        log.warning("session refused by the CLM backend while a qualification runs")
        now_at = time.monotonic()
        with attempts_lock:
            if now_at - rejected_at[0] < SESSION_AUDIT_SECONDS:
                return
            rejected_at[0] = now_at
        try:
            selector.store.record(
                actor="unknown",
                role=None,
                action="SESSION_REFUSED",
                outcome="refused",
                profile_id=running["profile_id"],
                code=exc.code,
            )
        except Exception:
            log.error("refused session could not be recorded")

    def load(request: Request) -> dict[str, Any]:
        check_origin(request)
        try:
            actor = backend.load_actor(request.cookies.get(SESSION_COOKIE_NAME))
        except ClmBackendError as exc:
            session_rejected(exc)
            raise HTTPException(
                status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}
            ) from None
        return dict(actor["profile"])

    def admin(request: Request) -> dict[str, Any]:
        profile = load(request)
        if CAPABILITY not in (profile.get("capabilities") or []):
            audit(profile, "ACCESS_REFUSED", "refused", code="MODEL_CONFIG_FORBIDDEN")
            raise _refusal(403, "MODEL_CONFIG_FORBIDDEN")
        return profile

    Admin = Annotated[dict[str, Any], Depends(admin)]

    def recheck(request: Request, profile: dict[str, Any], action: str) -> None:
        """Ask the backend again inside the change lock: same user, still allowed."""

        current = load(request)
        if current.get("user_id") != profile.get("user_id") or CAPABILITY not in (
            current.get("capabilities") or []
        ):
            audit(current, action, "refused", code="MODEL_CONFIG_FORBIDDEN")
            raise _refusal(403, "MODEL_CONFIG_FORBIDDEN")

    def managed() -> ModelAdminStore:
        if selector.store is None:
            raise _refusal(409, "MODEL_MANAGEMENT_OFF")
        return selector.store

    def entry_for(
        catalogue: Catalogue, profile_id: str, profile: dict[str, Any], action: str
    ) -> CatalogueEntry:
        entry = catalogue.get(profile_id)
        if entry is None:
            audit(profile, action, "refused", profile_id=None, code="PROFILE_UNKNOWN")
            raise _refusal(404, "PROFILE_UNKNOWN")
        refusal = None
        if entry.status == "pending_authorisation":
            refusal = "REMOTE_NOT_AUTHORISED"
        elif entry.status == "disabled" and entry.profile_id == BASELINE_ID:
            refusal = "MODEL_DISABLED_BY_ENVIRONMENT"
        elif entry.status != "selectable":
            refusal = "PROFILE_NOT_SELECTABLE"
        if refusal:
            audit(
                profile,
                action,
                "refused",
                profile_id=entry.profile_id,
                fingerprint=entry.fingerprint,
                code=refusal,
            )
            raise _refusal(409, refusal)
        return entry

    def adapter_for(
        entry: CatalogueEntry, profile: dict[str, Any], action: str, *, loopback: bool = False
    ) -> OpenAICompatibleChatModel:
        try:
            if entry.profile_id == BASELINE_ID:
                return build_baseline_adapter(
                    settings,
                    environ=selector.environ,
                    transport=selector.transport,
                    loopback=loopback,
                )
            return build_profile_model(
                entry, environ=selector.environ, transport=selector.transport
            )
        except ProfileConfigError as exc:
            code = "NOT_LOOPBACK" if exc.code == "NOT_LOOPBACK" else exc.code
            audit(
                profile,
                action,
                "refused",
                profile_id=entry.profile_id,
                fingerprint=entry.fingerprint,
                code=code,
            )
            raise HTTPException(
                status_code=409,
                detail={"code": code, "message": MESSAGES.get(code, MESSAGES["BUILD_FAILED"])},
            ) from None

    def qualification_view(
        item: dict[str, Any] | None, entry: CatalogueEntry, basis: str
    ) -> dict[str, Any] | None:
        if item is None:
            return None
        summary = item.get("summary") or {}
        return {
            "qualification_id": item["qualification_id"],
            "status": item["status"],
            "code": item["code"],
            "started_at": item["started_at"],
            "started_by": item["started_by"],
            "finished_at": item["finished_at"],
            "done_turns": item["done_turns"],
            "total_turns": item["total_turns"],
            "cancel_requested": item["cancel_requested"],
            "current": item["fingerprint"] == entry.fingerprint and item["basis"] == basis,
            "gates": summary.get("gates"),
            "metrics": summary.get("metrics"),
            "lines": summary.get("lines"),
            "capacity": summary.get("capacity"),
            "connection": summary.get("connection"),
            "quality": summary.get("quality"),
            "reproducibility": summary.get("reproducibility"),
        }

    def readiness(entry: CatalogueEntry, latest: dict[str, Any] | None, basis: str) -> list[str]:
        if entry.profile_id == BASELINE_ID:
            return (
                [] if entry.status == "selectable" else [entry.reason or "PROFILE_NOT_SELECTABLE"]
            )
        if entry.status != "selectable":
            return [entry.reason or "PROFILE_NOT_SELECTABLE"]
        if (
            latest is None
            or latest["status"] != "passed"
            or latest["fingerprint"] != entry.fingerprint
            or latest["basis"] != basis
        ):
            return ["NOT_QUALIFIED"]
        return []

    def last_failure(profiles: list[dict[str, Any]]) -> dict[str, Any] | None:
        """The newest failed qualification or connection test (codes and times only)."""

        failures = []
        for item in profiles:
            run = item.get("qualification")
            if run and run["status"] not in ("passed", "running"):
                failures.append(
                    {
                        "source": "QUALIFICATION",
                        "profile_id": item["profile_id"],
                        "code": run["code"],
                        "at": run["finished_at"] or run["started_at"],
                    }
                )
            test = item.get("connection_test")
            if test and test.get("outcome") != "passed":
                failures.append(
                    {
                        "source": "CONNECTION_TEST",
                        "profile_id": item["profile_id"],
                        "code": test.get("code"),
                        "at": test.get("at"),
                    }
                )
        return max(failures, key=lambda f: f["at"] or "", default=None)

    def qualification_cost(budget: dict[str, Any] | None) -> dict[str, Any] | None:
        """What a remote (paid) qualification needs: its calls (one after another, each
        admitted by the ledger on its own), the reservation each holds until it is charged, the
        worst case if every call cost its whole reservation, and whether the limits leave room
        for the first call and for that worst case."""

        manifest = qualification_manifest(settings)
        if manifest is None or budget is None or not budget.get("configured"):
            return None
        reservation = budget.get("reservation_micro_usd")
        needed = len(manifest) * reservation if isinstance(reservation, int) else None
        available = budget.get("effective_remaining_micro_usd")
        return {
            "paid_calls": len(manifest),
            "reservation_micro_usd": reservation,
            "needed_micro_usd": needed,
            "available_micro_usd": available,
            "budget_ok": isinstance(reservation, int)
            and isinstance(available, int)
            and available >= reservation,
            "worst_case_ok": needed is not None
            and isinstance(available, int)
            and available >= needed,
            "call_limit_ok": settings.local_api_test_max_calls >= len(manifest),
            "provider_checked": budget.get("provider") is not None,
        }

    def overview() -> dict[str, Any]:
        catalogue = load_catalogue(settings)
        active = selector.current()
        basis = qualification_basis()
        quality, reason = quality_state()
        store = selector.store
        stored = store.activation(selector.baseline_choice()) if store else None
        profiles = []
        for entry in catalogue.entries:
            latest = store.latest_qualification(entry.profile_id) if store else None
            passed = store.last_passed_qualification(entry.profile_id) if store else None
            profiles.append(
                {
                    **entry.view(),
                    "active": entry.profile_id == active.profile_id,
                    "connection_test": store.connection_test(entry.profile_id) if store else None,
                    "qualification": qualification_view(latest, entry, basis),
                    "activation_blockers": readiness(entry, latest, basis),
                    # D-098: an earlier pass matches today's configuration and code (it keeps an
                    # activation that uses it; a new activation needs the latest run to pass).
                    "previous_pass_current": passed is not None
                    and passed["fingerprint"] == entry.fingerprint
                    and passed["basis"] == basis,
                }
            )
        active_entry = catalogue.get(active.profile_id)
        last_good = _last_good(stored) if stored else None
        running = store.running_qualification() if store else None
        active_view = {
            "profile_id": active.profile_id,
            "display_name": active_entry.display_name if active_entry else active.profile_id,
            "model_id": active.model.name if active.model is not None else None,
            "prompt_limit": active.prompt_limit,
            "qualification_id": active.qualification_id,
            "changed_at": stored.changed_at if stored else None,
            "changed_by": stored.changed_by if stored else None,
            "config_changed": active_entry is not None
            and active_entry.fingerprint != active.fingerprint,
            "reverted": active.reverted,
        }
        budget = budget_view() if settings.local_api_test_decision else None
        return {
            "configured": selector.managed,
            "file_status": catalogue.file_status,
            "file_errors": list(catalogue.file_errors),
            "model_enabled": settings.llm_enabled,
            "revision": active.revision if selector.managed else 0,
            "active": active_view,
            "last_good": None
            if last_good is None
            else {
                "profile_id": last_good.profile_id,
                "display_name": (
                    catalogue.get(last_good.profile_id) or selector.baseline
                ).display_name,
            },
            "quality": {"status": quality, "reason": reason},
            "basis": basis[:12],
            "running": running
            and {
                "qualification_id": running["qualification_id"],
                "profile_id": running["profile_id"],
                "done_turns": running["done_turns"],
                "total_turns": running["total_turns"],
                "started_by": running["started_by"],
            },
            "profiles": profiles,
            # D-095: the remote profile's spending view and key status (never the key).
            "budget": budget,
            # D-098: what to do when the model cannot answer (closed codes; the page words them).
            "recovery": {
                **diagnose_service(active=active_view, profiles=profiles, budget=budget),
                "last_failure": last_failure(profiles),
                "qualification_cost": qualification_cost(budget),
            },
        }

    @router.get("")
    def get_overview(profile: Admin) -> dict[str, Any]:
        return overview()

    @router.get("/audit")
    def get_audit(
        profile: Admin, limit: Annotated[int, Query(ge=1, le=500)] = 100
    ) -> dict[str, Any]:
        return {"events": selector.store.events(limit) if selector.store else []}

    @router.post("/{profile_id}/connection-test")
    def post_connection_test(profile_id: str, profile: Admin) -> dict[str, Any]:
        store = managed()
        entry = entry_for(load_catalogue(settings), profile_id, profile, "CONNECTION_TEST")
        if entry.source == "code":
            # D-094 remote model: its preflight (no inference, no case data).
            result = connection_check(
                entry.settings_for(selector.controlled()), **selector.remote_options()
            )
        else:
            model = adapter_for(entry, profile, "CONNECTION_TEST")
            result = anyio.run(connection_test, model, model.name)
        store.save_connection_test(
            entry.profile_id,
            entry.fingerprint,
            str(profile.get("user_id")),
            result["outcome"],
            result["code"],
            result,
        )
        audit(
            profile,
            "CONNECTION_TEST",
            result["outcome"],
            profile_id=entry.profile_id,
            fingerprint=entry.fingerprint,
            code=result["code"],
        )
        return result

    def supervise(
        handle: Any, qualification_id: str, profile: dict[str, Any], entry: CatalogueEntry
    ) -> None:
        """Wait for the qualification process; end it when it overruns its limit or does not
        stop soon after a cancel; close the run if the process did not; audit the outcome."""

        store = managed()
        limit = time.monotonic() + settings.model_qualification_max_seconds + DEADLINE_GRACE_SECONDS
        cancelled_at: float | None = None
        ended = None
        try:
            while handle.poll() is None:
                now = time.monotonic()
                try:
                    store.touch(qualification_id)
                    item = store.qualification(qualification_id)
                except Exception:  # keep supervising; the limit below still applies
                    log.error("qualification state unavailable while supervising")
                    item = None
                if item is not None and item["cancel_requested"] and cancelled_at is None:
                    cancelled_at = now
                if now > limit:
                    ended = "DEADLINE"
                elif cancelled_at is not None and now - cancelled_at > CANCEL_GRACE_SECONDS:
                    ended = "CANCELLED"
                if ended:
                    break
                threading.Event().wait(SUPERVISE_SECONDS)
        except Exception:
            log.error("qualification supervisor failed; ending the process")
            ended = ended or "SUPERVISOR_FAILED"
        finally:
            if handle.poll() is None:
                handle.kill()
            handle.wait()
        try:
            # Only a run the process left open is closed here (a finished one never changes).
            if ended == "CANCELLED":
                store.finish_qualification(qualification_id, "cancelled", "CANCELLED", None)
            store.finish_qualification(qualification_id, "error", ended or "PROCESS_EXITED", None)
            final = store.qualification(qualification_id) or {}
            audit(
                profile,
                "QUALIFICATION_FINISHED",
                str(final.get("status") or "error"),
                profile_id=entry.profile_id,
                fingerprint=entry.fingerprint,
                code=final.get("code"),
            )
        except Exception:
            log.error("qualification outcome could not be recorded")

    @router.post("/{profile_id}/qualifications", status_code=202)
    def post_qualification(
        profile_id: str, profile: Admin, body: QualificationRequest | None = None
    ) -> dict[str, Any]:
        store = managed()
        entry = entry_for(load_catalogue(settings), profile_id, profile, "QUALIFICATION_STARTED")

        def refuse(code: str) -> HTTPException:
            audit(
                profile,
                "QUALIFICATION_STARTED",
                "refused",
                profile_id=entry.profile_id,
                fingerprint=entry.fingerprint,
                code=code,
            )
            return _refusal(409, code)

        # The same checks the qualification process applies, before anything starts.
        if entry.source == "code":
            # D-094: a paid run, so only the configured, counted question manifest.
            if qualification_manifest(settings) is None:
                raise refuse("REMOTE_MANIFEST_MISSING")
            # D-098: HR repeats the number of paid calls back, and a run the limits leave no
            # room to start is not started (the ledger still admits every call itself).
            cost = qualification_cost(budget_view())
            confirmed = body.confirm_paid_calls if body is not None else None
            if cost is None or confirmed != cost["paid_calls"]:
                raise refuse("PAID_CONFIRMATION_REQUIRED")
            if not (cost["budget_ok"] and cost["call_limit_ok"]):
                raise refuse("QUALIFICATION_BUDGET_TOO_LOW")
        else:
            adapter_for(entry, profile, "QUALIFICATION_STARTED", loopback=True)
        try:
            qualification_id = store.begin_qualification(
                entry.profile_id,
                entry.fingerprint,
                qualification_basis(),
                str(profile.get("user_id")),
                0,
                # D-098: a safety, answer-validity, capacity or verification gate failure is
                # not run again on the same configuration and code until IT changes one of
                # them (a new fingerprint or basis); repeating it until a run passes would
                # bypass the gate. Checked in the start's own transaction.
                blocked=escalation_gates_failed,
            )
        except QualificationBlocked:
            raise refuse("ESCALATION_REQUIRED") from None
        except QualificationBusy:
            audit(
                profile,
                "QUALIFICATION_STARTED",
                "refused",
                profile_id=entry.profile_id,
                fingerprint=entry.fingerprint,
                code="QUALIFICATION_BUSY",
            )
            raise _refusal(409, "QUALIFICATION_BUSY") from None
        try:
            handle = selector.launch(qualification_id)
        except (OSError, ProfileConfigError):
            store.finish_qualification(qualification_id, "error", "QUALIFICATION_UNAVAILABLE", None)
            audit(
                profile,
                "QUALIFICATION_STARTED",
                "refused",
                profile_id=entry.profile_id,
                fingerprint=entry.fingerprint,
                code="QUALIFICATION_UNAVAILABLE",
            )
            raise _refusal(409, "QUALIFICATION_UNAVAILABLE") from None
        audit(
            profile,
            "QUALIFICATION_STARTED",
            "started",
            profile_id=entry.profile_id,
            fingerprint=entry.fingerprint,
        )
        threading.Thread(
            target=supervise,
            args=(handle, qualification_id, profile, entry),
            name="model-qualification",
            daemon=True,
        ).start()
        return {"qualification_id": qualification_id}

    @router.get("/qualifications/{qualification_id}")
    def get_qualification(qualification_id: str, profile: Admin) -> dict[str, Any]:
        store = managed()
        item = (
            store.qualification(qualification_id)
            if _QUALIFICATION_ID.fullmatch(qualification_id)
            else None
        )
        if item is None:
            audit(profile, "QUALIFICATION_VIEW", "refused", code="QUALIFICATION_UNKNOWN")
            raise _refusal(404, "QUALIFICATION_UNKNOWN")
        entry = load_catalogue(settings).get(item["profile_id"]) or selector.baseline
        return qualification_view(item, entry, qualification_basis()) or {}

    @router.post("/qualifications/{qualification_id}/cancel")
    def cancel_qualification(qualification_id: str, profile: Admin) -> dict[str, Any]:
        store = managed()
        if not _QUALIFICATION_ID.fullmatch(qualification_id) or not store.request_cancel(
            qualification_id
        ):
            audit(
                profile,
                "QUALIFICATION_CANCEL_REQUESTED",
                "refused",
                code="QUALIFICATION_UNKNOWN",
            )
            raise _refusal(404, "QUALIFICATION_UNKNOWN")
        item = store.qualification(qualification_id) or {}
        audit(
            profile,
            "QUALIFICATION_CANCEL_REQUESTED",
            "requested",
            profile_id=item.get("profile_id"),
        )
        return {"qualification_id": qualification_id, "cancel_requested": True}

    def change(
        request: Request,
        profile: dict[str, Any],
        body: ChangeRequest,
        action: str,
        target: Callable[[Activation, Catalogue], tuple[CatalogueEntry, Choice | None]],
    ) -> dict[str, Any]:
        store = managed()
        with selector.change_lock:
            recheck(request, profile, action)
            stored = store.activation(selector.baseline_choice())
            catalogue = load_catalogue(settings)
            entry, qualified = target(stored, catalogue)

            def refuse(code: str, status: int = 409) -> HTTPException:
                audit(
                    profile,
                    action,
                    "refused",
                    profile_id=entry.profile_id,
                    fingerprint=entry.fingerprint,
                    code=code,
                    revision=stored.revision,
                )
                return _refusal(status, code)

            if stored.revision != body.expected_revision:
                raise refuse("REVISION_CONFLICT")
            if entry.profile_id == stored.active_profile_id:
                raise refuse("ALREADY_ACTIVE")
            choice = selector.baseline_choice()
            unscored = False
            if entry.profile_id != BASELINE_ID:
                if qualified is None:
                    raise refuse("NOT_QUALIFIED")
                # Only the qualification run itself verifies the owner gold lock; anything
                # short of its verified "SCORED" needs the explicit acknowledgement.
                unscored = not run_was_scored(qualified.qualification_id)
                if unscored and not body.acknowledge_quality_unscored:
                    raise refuse("ACKNOWLEDGEMENT_REQUIRED")
                probe = (
                    connection_check(
                        entry.settings_for(selector.controlled()), **selector.remote_options()
                    )
                    if entry.source == "code"
                    else anyio.run(
                        connection_test, adapter_for(entry, profile, action), entry.model_id or ""
                    )
                )
                if probe["outcome"] != "passed":
                    raise refuse("CONNECTION_FAILED")
                choice = qualified
            previous = (
                # D-098: "no model" is not a rollback target; the earlier one stays.
                _last_good(stored)
                if stored.active_profile_id == CASE_DATA_ONLY_ID
                else Choice(
                    stored.active_profile_id,
                    stored.active_fingerprint,
                    stored.active_qualification_id,
                    stored.active_prompt_limit,
                )
            )
            try:
                active = selector.apply(
                    body.expected_revision, choice, previous, str(profile.get("user_id"))
                )
            except RevisionConflict:
                raise refuse("REVISION_CONFLICT") from None
            except ProfileConfigError as exc:
                raise refuse(exc.code) from None
            audit(
                profile,
                action,
                "applied",
                profile_id=entry.profile_id,
                fingerprint=entry.fingerprint,
                revision=active.revision,
                code="QUALITY_NOT_SCORED_ACKNOWLEDGED" if unscored else None,
            )
        return overview()

    def run_was_scored(qualification_id: str | None) -> bool:
        item = (
            selector.store.qualification(qualification_id)
            if (selector.store and qualification_id)
            else None
        )
        quality = ((item or {}).get("summary") or {}).get("quality") or {}
        return quality.get("status") == "SCORED"

    def qualified_choice(entry: CatalogueEntry, qualification_id: str | None) -> Choice | None:
        store = selector.store
        assert store is not None
        item = store.qualification(qualification_id) if qualification_id else None
        if (
            item is None
            or item["status"] != "passed"
            or item["profile_id"] != entry.profile_id
            or item["fingerprint"] != entry.fingerprint
            or item["basis"] != qualification_basis()
        ):
            return None
        limit = ((item.get("summary") or {}).get("capacity") or {}).get("prompt_limit")
        if not isinstance(limit, int) or limit <= 0:
            return None
        return Choice(entry.profile_id, entry.fingerprint, item["qualification_id"], limit)

    @router.post("/{profile_id}/activate")
    def activate(
        profile_id: str, body: ChangeRequest, profile: Admin, request: Request
    ) -> dict[str, Any]:
        def target(
            stored: Activation, catalogue: Catalogue
        ) -> tuple[CatalogueEntry, Choice | None]:
            entry = entry_for(catalogue, profile_id, profile, "ACTIVATED")
            if entry.profile_id == BASELINE_ID:
                return entry, None
            latest = selector.store.latest_qualification(entry.profile_id)  # type: ignore[union-attr]
            return entry, qualified_choice(entry, latest["qualification_id"] if latest else None)

        return change(request, profile, body, "ACTIVATED", target)

    @router.post("/rollback")
    def rollback(body: ChangeRequest, profile: Admin, request: Request) -> dict[str, Any]:
        def target(
            stored: Activation, catalogue: Catalogue
        ) -> tuple[CatalogueEntry, Choice | None]:
            last = _last_good(stored)
            if last is None:
                audit(
                    profile,
                    "ROLLED_BACK",
                    "refused",
                    code="NO_ROLLBACK_TARGET",
                    revision=stored.revision,
                )
                raise _refusal(409, "NO_ROLLBACK_TARGET")
            entry = entry_for(catalogue, last.profile_id, profile, "ROLLED_BACK")
            if entry.profile_id == BASELINE_ID:
                return entry, None
            if entry.fingerprint != last.fingerprint:
                return entry, None
            return entry, qualified_choice(entry, last.qualification_id)

        return change(request, profile, body, "ROLLED_BACK", target)

    # --- D-095: the daily spending view and the OpenRouter key (never the key itself) -------

    @router.get("/budget")
    def get_budget(profile: Admin) -> dict[str, Any]:
        return budget_view()

    def credential_view() -> dict[str, Any]:
        return key_sources.resolve(selector.environ)[1].view()

    @router.get("/credential")
    def get_credential(profile: Admin) -> dict[str, Any]:
        return credential_view()

    attempts: dict[str, list[float]] = {}
    attempts_lock = threading.Lock()

    def guard_change(request: Request, profile: dict[str, Any], action: str) -> None:
        """A key change must come from an allowed page (the Origin header is required, not
        only checked when present) and stay within the per-administrator rate limit."""

        if not request.headers.get("origin"):
            audit(profile, action, "refused", code="ORIGIN_REQUIRED")
            raise _refusal(403, "ORIGIN_REQUIRED")
        now = time.monotonic()
        user = str(profile.get("user_id"))
        with attempts_lock:
            recent = [at for at in attempts.get(user, []) if now - at < CREDENTIAL_WINDOW_SECONDS]
            limited = len(recent) >= CREDENTIAL_ATTEMPTS
            if not limited:
                recent.append(now)
            attempts[user] = recent
        if limited:
            audit(profile, action, "refused", code="CREDENTIAL_RATE_LIMITED")
            raise _refusal(429, "CREDENTIAL_RATE_LIMITED")

    def environment_managed() -> bool:
        return key_sources.resolve(selector.environ)[1].source in ("environment", "env_file")

    @router.put("/credential")
    async def put_credential(request: Request, profile: Admin) -> dict[str, Any]:
        action = "CREDENTIAL_SET"
        guard_change(request, profile, action)
        # Parsed here, not by a request model, so a refusal can never echo the value back.
        raw = await request.body()
        key: object = None
        if len(raw) <= MAX_CREDENTIAL_BODY and request.headers.get("content-type", "").startswith(
            "application/json"
        ):
            try:
                body = json.loads(raw)
            except ValueError:
                body = None
            if isinstance(body, dict) and set(body) == {"api_key"}:
                key = body["api_key"]
        if not isinstance(key, str) or not key_sources.HR_KEY.fullmatch(key):
            audit(profile, action, "refused", code="CREDENTIAL_INVALID")
            raise _refusal(400, "CREDENTIAL_INVALID")
        secret = SecretStr(key)
        del key, raw
        await anyio.to_thread.run_sync(recheck, request, profile, action)
        if environment_managed():
            audit(profile, action, "refused", code="CREDENTIAL_ENVIRONMENT_MANAGED")
            raise _refusal(409, "CREDENTIAL_ENVIRONMENT_MANAGED")
        key_sources.HR_STORE.set(secret, str(profile.get("user_id")))
        forget_provider()  # the spending view's key limit was read for the previous key
        audit(profile, action, "applied")
        return credential_view()

    @router.delete("/credential")
    def delete_credential(request: Request, profile: Admin) -> dict[str, Any]:
        action = "CREDENTIAL_CLEARED"
        guard_change(request, profile, action)
        recheck(request, profile, action)
        if environment_managed():
            audit(profile, action, "refused", code="CREDENTIAL_ENVIRONMENT_MANAGED")
            raise _refusal(409, "CREDENTIAL_ENVIRONMENT_MANAGED")
        if not key_sources.HR_STORE.clear():
            audit(profile, action, "refused", code="CREDENTIAL_NOT_HR_MANAGED")
            raise _refusal(409, "CREDENTIAL_NOT_HR_MANAGED")
        forget_provider()
        audit(profile, action, "applied")
        return credential_view()

    # --- D-096: HR spending controls, the lifetime ledger cap and provider limits -----------

    def budget_view() -> dict[str, Any]:
        """The D-095 spending view with the HR controls that apply, the calls the active model
        has left, and the range the lifetime cap may be set within. Read-only."""

        controls = selector.spending_controls()
        effective = apply_controls(settings, controls)
        view = budget_status(effective, environ=selector.environ)
        try:
            used = selector.calls_used()
        except LedgerError:
            used = None
        limit = effective.local_api_test_max_calls
        lifetime = None
        try:
            ledger = BudgetLedger(ledger_file(settings))
            ledger.verify()
            status = ledger.status()
            lifetime = {
                "opening_usage_micro_usd": status.opening_usage,
                "cap_micro_usd": status.cap,
                "max_cap_micro_usd": MAX_MICRO_USD,
                "committed_micro_usd": status.committed,
            }
        except LedgerError:
            pass
        view["controls"] = {
            "revision": controls.revision if controls is not None else None,
            "readable": controls is not None,
            "daily_cap_micro_usd": effective.budget_daily_cap_micro_usd,
            "daily_cap_max_micro_usd": DAILY_CAP_MAX_MICRO_USD,
            "daily_cap_source": "hr"
            if controls is not None and controls.daily_cap_micro_usd is not None
            else "environment",
            "max_calls": limit,
            "max_calls_range": list(MAX_CALLS_RANGE),
            "max_calls_source": "hr"
            if controls is not None and controls.max_calls is not None
            else "environment",
            "calls_used": used,
            "calls_remaining": None if used is None else max(limit - used, 0),
            "changed_at": controls.changed_at if controls is not None else None,
            "changed_by": controls.changed_by if controls is not None else None,
            "lifetime": lifetime,
        }
        return view

    budget_attempts: dict[str, list[float]] = {}

    def guard_budget(request: Request, profile: dict[str, Any], action: str) -> None:
        """Like a key change: the Origin header of an allowed page is required, and each
        administrator has a bounded number of spending changes and refreshes per window."""

        if not request.headers.get("origin"):
            audit(profile, action, "refused", code="ORIGIN_REQUIRED")
            raise _refusal(403, "ORIGIN_REQUIRED")
        now = time.monotonic()
        user = str(profile.get("user_id"))
        with attempts_lock:
            recent = [
                at for at in budget_attempts.get(user, []) if now - at < CREDENTIAL_WINDOW_SECONDS
            ]
            limited = len(recent) >= BUDGET_ATTEMPTS
            if not limited:
                recent.append(now)
            budget_attempts[user] = recent
        if limited:
            audit(profile, action, "refused", code="BUDGET_RATE_LIMITED")
            raise _refusal(429, "BUDGET_RATE_LIMITED")

    @router.put("/budget/controls")
    def put_spending_controls(
        body: SpendingControlsRequest, profile: Admin, request: Request
    ) -> dict[str, Any]:
        """The daily allowance per Singapore day (US$0 up; US$1.00 is only the default) and the
        calls per activation (1 to 200). Spend and the activation's call count are never
        reset. D-098: a higher daily limit than the one that applies needs the amount confirmed
        and a fresh provider check (a finite key limit that never resets; a reconciled
        ledger); a lower one is always allowed."""

        action = "SPENDING_CONTROLS_CHANGED"
        guard_budget(request, profile, action)
        store = managed()
        if not valid_controls(body.daily_cap_micro_usd, body.max_calls):
            audit(profile, action, "refused", code="CONTROLS_INVALID")
            raise _refusal(400, "CONTROLS_INVALID")
        with selector.change_lock:
            recheck(request, profile, action)
            stored = selector.spending_controls()
            # The increase is judged against the row the change replaces: a view read under
            # another revision is refused before any check (the store's compare-and-set
            # refuses the same row changing after this read).
            if stored is not None and stored.revision != body.expected_revision:
                audit(profile, action, "refused", code="CONTROLS_CONFLICT")
                raise _refusal(409, "CONTROLS_CONFLICT")
            current = apply_controls(settings, stored)
            if body.daily_cap_micro_usd > current.budget_daily_cap_micro_usd:
                if body.confirm_daily_cap_micro_usd != body.daily_cap_micro_usd:
                    audit(profile, action, "refused", code="DAILY_CONFIRMATION_REQUIRED")
                    raise _refusal(400, "DAILY_CONFIRMATION_REQUIRED")
                verify_increase(profile, action)
            try:
                revision = store.set_spending_controls(
                    body.expected_revision,
                    body.daily_cap_micro_usd,
                    body.max_calls,
                    str(profile.get("user_id")),
                )
            except RevisionConflict:
                audit(profile, action, "refused", code="CONTROLS_CONFLICT")
                raise _refusal(409, "CONTROLS_CONFLICT") from None
            audit(
                profile,
                action,
                "applied",
                code=f"DAILY_{body.daily_cap_micro_usd}_MICRO_USD_CALLS_{body.max_calls}",
                revision=revision,
            )
        selector.sync_controls()
        return budget_view()

    def increase_failures() -> list[str] | None:
        """The checks an increase needs (INCREASE_CHECKS: the existing checks of the free
        preflight, GET /key against the ledger; no inference, nothing changed) that failed, or
        None when OpenRouter or the ledger could not be checked at all."""

        report, _, _ = preflight(selector.controlled(), **selector.remote_options())
        found = {check.name: check.ok for check in report.checks}
        if any(name not in found for name in INCREASE_CHECKS):
            return None
        return [name for name in INCREASE_CHECKS if not found[name]]

    def verify_increase(profile: dict[str, Any], action: str) -> None:
        """Refuse an increase unless OpenRouter confirms a finite key limit that never resets
        and the ledger matches the key's usage (fails closed when either is unknown)."""

        try:
            failed = increase_failures()
        except (ProfileConfigError, LedgerError):
            failed = None
        if failed is None:
            audit(profile, action, "refused", code="PROVIDER_CHECK_FAILED")
            raise _refusal(409, "PROVIDER_CHECK_FAILED")
        if any(name in PROVIDER_LIMIT_CHECKS for name in failed):
            audit(profile, action, "refused", code="PROVIDER_LIMIT_REQUIRED:" + ",".join(failed))
            raise _refusal(409, "PROVIDER_LIMIT_REQUIRED")
        if failed:
            audit(profile, action, "refused", code="RECONCILIATION_REQUIRED:" + ",".join(failed))
            raise _refusal(409, "RECONCILIATION_REQUIRED")

    @router.put("/budget/lifetime-cap")
    def put_lifetime_cap(
        body: LifetimeCapRequest, profile: Admin, request: Request
    ) -> dict[str, Any]:
        """Set the ledger's lifetime cap from its opening provider usage up (D-098: no US$1.00
        allocation bound). A raise needs the same amount confirmed and a fresh provider check
        (a finite key limit that never resets; a reconciled ledger); the ledger keeps every
        call, charge and earlier event."""

        action = "LIFETIME_CAP_CHANGED"
        guard_budget(request, profile, action)
        managed()  # a change is made only where it can be audited
        with selector.change_lock:
            recheck(request, profile, action)
            try:
                ledger = BudgetLedger.open(ledger_file(settings))
                status = ledger.status()
            except LedgerError:
                audit(profile, action, "refused", code="LEDGER_UNAVAILABLE")
                raise _refusal(409, "LEDGER_UNAVAILABLE") from None
            cap = body.cap_micro_usd
            if not status.opening_usage <= cap <= MAX_MICRO_USD:
                audit(profile, action, "refused", code="CAP_OUT_OF_RANGE")
                raise _refusal(409, "CAP_OUT_OF_RANGE")
            raising = cap > status.cap
            if raising and body.confirm_cap_micro_usd != cap:
                audit(profile, action, "refused", code="CAP_CONFIRMATION_REQUIRED")
                raise _refusal(400, "CAP_CONFIRMATION_REQUIRED")
            if (raising or body.expected_cap_micro_usd is not None) and (
                body.expected_cap_micro_usd != status.cap
            ):
                audit(profile, action, "refused", code="CONTROLS_CONFLICT")
                raise _refusal(409, "CONTROLS_CONFLICT")
            if raising:
                verify_increase(profile, action)
            if cap != status.cap:
                try:
                    # D-098: the cap this decision was made on is compared again in the
                    # ledger's own write transaction (the provider check above takes time,
                    # and the operator's script or another process may change the cap).
                    ledger.set_cap(
                        cap,
                        allow_raise=raising,
                        confirm=cap if raising else None,
                        expected=status.cap,
                    )
                except LedgerError as error:
                    if error.code in ("CAP_CHANGED", "CAP_RAISE_REFUSED"):
                        audit(profile, action, "refused", code="CONTROLS_CONFLICT")
                        raise _refusal(409, "CONTROLS_CONFLICT") from None
                    audit(profile, action, "refused", code="LEDGER_UNAVAILABLE")
                    raise _refusal(409, "LEDGER_UNAVAILABLE") from None
                audit(
                    profile,
                    action,
                    "applied",
                    code=f"{'RAISED' if raising else 'LOWERED'}_TO_{cap}_MICRO_USD",
                )
        return budget_view()

    @router.post("/budget/provider-refresh")
    def post_provider_refresh(profile: Admin, request: Request) -> dict[str, Any]:
        """Read the OpenRouter key's limit again (the free preflight: no inference, no case
        data; the key and its provider-side limit are never changed)."""

        action = "PROVIDER_LIMITS_REFRESHED"
        guard_budget(request, profile, action)
        managed()  # audited like every other spending action
        report, _, _ = preflight(selector.controlled(), **selector.remote_options())
        failed = [check.name for check in report.checks if not check.ok]
        audit(
            profile,
            action,
            "passed" if report.passed else "failed",
            code=None if report.passed else "PREFLIGHT_FAILED:" + ",".join(failed),
        )
        return budget_view()

    return router
