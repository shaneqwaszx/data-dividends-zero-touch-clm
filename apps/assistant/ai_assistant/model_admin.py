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
                               GET|PUT|DELETE .../credential/anthropic      (D-106)
                               POST .../provider/anthropic/workspace-read   (D-107)
                               PUT  .../provider/anthropic                  (D-107)
                               PUT  /assistant/admin/models/budget/controls     (D-096)
                               PUT  /assistant/admin/models/budget/lifetime-cap
                               POST /assistant/admin/models/budget/provider-refresh
                               GET  .../budget/claude/reconciliation          (D-110)
                               POST .../budget/claude/reconciliation/preview
                               POST .../budget/claude/reconciliation/apply
                               POST .../budget/claude/reconciliation/runs/{run}/resolve

Who is asking, and whether they hold ``MODEL_CONFIG_MANAGE``, always comes from the CLM
backend with the caller's own session; activation and rollback ask again inside the lock
that applies them. Refusals of a signed-in caller are audited. Nothing here reads a case or
an answer record, and the browser can only name a profile id, except that an HR
administrator may hand the server an OpenRouter or an Anthropic key (D-106, key_sources.py):
it is kept in server memory only, bound to that administrator's own session (used before an
environment or .env key, dropped when the session ends) and never sent back, logged or
audited; changing it needs the Origin header of an allowed page and is rate limited.

D-096: an HR administrator also sets the remote model's spending controls here: the daily
allowance per Singapore day and the calls per activation (1 to 200), stored in the model state
database (compare-and-set, every process reads them per request, applied to the active model
without a restart or a new activation, its call count kept); the ledger's lifetime cap, at or
above the key's opening provider usage; and a read-only refresh of the key's OpenRouter limit.
D-098: neither limit has a US$1 ceiling (US$1.00 stays the daily default). Raising either
needs the amount confirmed again and a fresh free preflight showing the key has a finite,
never-resetting OpenRouter limit; raising the lifetime cap also needs the existing
reconciliation checks against OpenRouter's reported usage. At every call the strictest of the
daily allowance, the lifetime cap and the key's own limit applies. Spend, calls and ledger
history are never reset, no ledger is created, and neither the key nor its OpenRouter limit is
changed.

Switching is atomic: each answer takes one snapshot of the active model when it starts and
keeps it to the end, and the choice is a compare-and-set on the stored revision, which every
request checks (so a restart, or a second service process, uses the same model). At start,
a stored model that is missing, changed, no longer selectable, qualified against older code,
or cannot be built is replaced by the environment baseline, with the reason audited. A model
failing at run time is never switched automatically: the RM gets the deterministic case-data
answer and an administrator decides.
"""

import hashlib
import json
import logging
import re
import sqlite3
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

import anyio
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StrictBool, StrictInt

from . import anthropic_profiles, anthropic_runtime, data_access, key_sources, recovery
from . import claude_reconciliation as reconciliation
from .budget import (
    DEFAULT_DAILY_CAP_MICRO_USD,
    MAX_MICRO_USD,
    RECONCILE_TOLERANCE_MICRO_USD,
    SESSION_DEFAULT_MICRO_USD,
    SESSION_MAX_MICRO_USD,
    BudgetedChatModel,
    BudgetLedger,
    LedgerError,
    LedgerStatus,
)
from .clm_client import SESSION_COOKIE_NAME, ClmBackendClient, ClmBackendError
from .config import AiAssistantSettings
from .llm import ChatModel, OpenAICompatibleChatModel
from .model_admin_store import (
    CLAUDE_DAILY_CAP_RANGE,
    CLAUDE_MAX_CALLS_RANGE,
    DAILY_CAP_MAX_MICRO_USD,
    MAX_CALLS_RANGE,
    Activation,
    Choice,
    DataAccessPolicy,
    ModelAdminStore,
    QualificationBusy,
    RecoveryRequestRefused,
    RevisionConflict,
    SpendingControls,
    apply_claude_controls,
    apply_controls,
    valid_claude_controls,
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
from .model_qualification import (
    G7_MAX_CUT_SHORT,
    connection_test,
    qualification_basis,
    quality_state,
)
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
SYSTEM_ACTOR = "system"
# D-098: the stored "no model" state after a GPT-OSS configuration stopped being usable (never
# a profile id in the catalogue, so it can never be activated or rolled back to).
UNAVAILABLE_ID = "ai_unavailable"
# D-099 Option B: the Claude configurations follow the same fail-closed rules (R6 extended).
REMOTE_PROFILE_IDS = (
    frozenset({OPENROUTER_PROFILE_ID, OPENROUTER_FAST_PROFILE_ID}) | anthropic_profiles.PROFILE_IDS
)
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
# D-107: how long a free workspace read vouches for enabling Claude with the same key.
WORKSPACE_READ_SECONDS = 3600.0
CREDENTIAL_WINDOW_SECONDS = 600.0
MAX_CREDENTIAL_BODY = 1024
# B1 (QG L1): how many times the Claude spending view is read again when the ledger changed
# while it was being read, before its figures are withheld instead of mixing two states.
CLAUDE_VIEW_ATTEMPTS = 3
# HR spending changes and provider-limit refreshes (D-096), per administrator in the window.
BUDGET_ATTEMPTS = 20
# Reconciliation checks a lifetime cap increase needs (remote_checks.check_ledger).
CAP_RAISE_CHECKS = ("ledger.breaker_closed_no_open_calls", "ledger.usage_reconciled")
# D-098: what any increase of app spending authority needs from the key itself: a finite
# provider-side limit that never resets (a missing limit is never read as permission).
PROVIDER_LIMIT_CHECKS = ("key.limit_set", "key.limit_never_resets", "key.limit_finite")

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
    "CREDENTIAL_INVALID": (
        "That is not an API key for this provider (an inference key only). Nothing was saved."
    ),
    "CREDENTIAL_NOT_HR_MANAGED": "There is no key entered here to clear.",
    # D-107: Claude's provider setup.
    "ENABLEMENT_INVALID": (
        "Confirm all four statements and give the workspace's monthly limit (US$0.000001 to"
        " US$30.00). Nothing changed."
    ),
    "WORKSPACE_NOT_READ": (
        "Read the workspace with the key now in use first, then confirm it. Nothing changed."
    ),
    "WORKSPACE_CHANGE_REFUSED": (
        "Claude is already set up for another Anthropic workspace. A different workspace needs"
        " an operator and its own ledger. Nothing changed."
    ),
    "WORKSPACE_MISMATCH": (
        "The workspace set on the server differs from the one the key reports. Nothing changed."
    ),
    "ENABLEMENT_CONFLICT": "Claude's setup changed since this view. Refresh and try again.",
    "ENABLEMENT_UNAVAILABLE": "Claude's setup could not be read. Nothing changed.",
    # D-118: a fresh Claude ledger, paid sessions and the conservative-only resume.
    "OPENING_REQUIRED": (
        "This is the first set-up on this machine: say whether the workspace is new with no"
        " earlier usage, or enter its cumulative cost from the Anthropic Console. Nothing changed."
    ),
    "OPENING_INVALID": (
        "The opening usage must be a whole amount from US$0.00 up to below the ledger cap."
        " Nothing changed."
    ),
    "LEDGER_EXISTS": (
        "Claude's spending ledger already exists here, so it keeps its own figures. Leave the"
        " opening out. Nothing changed."
    ),
    "SESSION_CHANGED": "The paid session changed since this view. Refresh and try again.",
    "SESSION_BUSY": "A paid call is still in progress. Wait for it to finish, then try again.",
    "SESSION_MISSING": "No paid session is open yet. Nothing changed.",
    "BREAKER_RESUME_REFUSED": (
        "The ledger cannot prove every recent charge was a full, conservative charge, so paid"
        " calls stay stopped for the owner. Nothing changed."
    ),
    "LEDGER_MIGRATION_REQUIRED": (
        "This spending ledger is in the earlier format; the owner must migrate it first."
        " Nothing changed."
    ),
    "NOT_ENABLED": "Claude is not enabled, so there is nothing to disable.",
    "CREDENTIAL_SESSION_UNVERIFIED": (
        "The session key cannot be used now: the HR session that entered it cannot be checked."
        " Nothing started."
    ),
    "CREDENTIAL_RATE_LIMITED": "Too many key changes. Wait a few minutes and try again.",
    "ORIGIN_REQUIRED": "This change must come from the AI Models page.",
    # D-096: HR spending controls.
    "CONTROLS_INVALID": (
        "The daily limit must be a non-negative US$ amount and the call limit 1 to 200."
        " Nothing changed."
    ),
    "DAILY_CONFIRMATION_REQUIRED": "Confirm the new daily limit to raise it. Nothing changed.",
    "PROVIDER_LIMIT_REQUIRED": (
        "The OpenRouter key must have its own finite spending limit that never resets before"
        " the app's spending limits can be raised. Nothing changed."
    ),
    "CONTROLS_CONFLICT": "The spending limits changed since this view. Refresh and try again.",
    "BUDGET_RATE_LIMITED": "Too many spending changes. Wait a few minutes and try again.",
    "RECOVERY_RATE_LIMITED": "Too many recovery requests. Wait a few minutes and try again.",
    "RECOVERY_PROBLEM_NOT_PRESENT": "That problem is not reported now; check the page again.",
    "RECOVERY_PROBLEM_NOT_OWNER": "HR can fix that problem on this page; no request is needed.",
    "RECOVERY_PROBLEM_STILL_PRESENT": "The problem is still reported, so it stays open.",
    "RECOVERY_REQUEST_EXISTS": "An open request for this problem already exists.",
    "RECOVERY_REQUEST_LIMIT": "Too many open recovery requests. Close some first.",
    "RECOVERY_REQUEST_UNKNOWN": "No such recovery request.",
    "RECOVERY_REQUEST_CLOSED": "This recovery request is already closed.",
    "RECOVERY_REQUEST_STATUS_INVALID": "That is not a valid way to close a request.",
    "RECOVERY_NOTE_REFUSED": "The note must be plain text without keys or secrets.",
    "LEDGER_UNAVAILABLE": "The spending ledger is missing or not usable. Nothing changed.",
    "CAP_OUT_OF_RANGE": (
        "The lifetime limit cannot be below the key's opening usage. Nothing changed."
    ),
    "CAP_CONFIRMATION_REQUIRED": "Confirm the new lifetime limit to raise it. Nothing changed.",
    "RECONCILIATION_REQUIRED": (
        "The ledger must be reconciled with OpenRouter (no open call, no stop, usage accounted"
        " for) before the lifetime limit can be raised. Nothing changed."
    ),
    "PROVIDER_CHECK_FAILED": "The OpenRouter key could not be checked. Nothing changed.",
    # D-098: paid qualification confirmation, budget and escalation.
    "PAID_CONFIRMATION_REQUIRED": (
        "Confirm the number of paid calls this qualification may make. Nothing started."
    ),
    "QUALIFICATION_BUDGET_INSUFFICIENT": (
        "The spending limits do not leave room for every paid call this qualification may"
        " make. Nothing started."
    ),
    "QUALIFICATION_BILLING_UNRECONCILED": (
        "Paid calls are stopped until an operator reconciles the spending ledger. Nothing started."
    ),
    "PROVIDER_LIMIT_NOT_CHECKED": (
        "Run Test connection first so the OpenRouter key's own limit is checked. Nothing started."
    ),
    # D-099: the same refusal for a Claude configuration, whose free check reads the attested
    # Anthropic workspace and the model (there is no readable key limit).
    "PROVIDER_LIMIT_NOT_CHECKED_ANTHROPIC": (
        "Run Test connection first so the Anthropic workspace and model are checked (a free"
        " model read). Nothing started."
    ),
    "PROVIDER_KEY_LIMIT_EXHAUSTED": (
        "The OpenRouter key's own spending limit has no room. Only the key's owner can raise"
        " it at OpenRouter; it is not an HR setting. Nothing started."
    ),
    "QUALIFICATION_ESCALATION_REQUIRED": (
        "This configuration failed on answer quality. A developer or IT must change it before"
        " it is qualified again. Nothing started."
    ),
    "QUALIFICATION_SUPERSEDED": (
        "A later qualification of this configuration failed on answer quality."
    ),
    # D-102: Claude's own spending changes (the same codes, worded for the Anthropic ledger).
    "CONTROLS_INVALID_ANTHROPIC": (
        "Claude's daily limit must be more than US$0.00 and at most US$5.00, and its call limit"
        " 1 to 20. Nothing changed."
    ),
    "CAP_OUT_OF_RANGE_ANTHROPIC": (
        "Claude's lifetime limit must be above the workspace's opening usage and at most the"
        " lower of US$30.00 and the attested workspace limit. Nothing changed."
    ),
    "RECONCILIATION_REQUIRED_ANTHROPIC": (
        "Claude's ledger must be reconciled with the Anthropic Console's usage within the last"
        " day (no open call, no stop) before a Claude limit can be raised. Nothing changed."
    ),
    "CALLS_CONFIRMATION_REQUIRED": ("Confirm the new call limit to raise it. Nothing changed."),
    "CLAUDE_NOT_READY": (
        "Claude is not fully configured on this server, so its limits can only be lowered."
        " Nothing changed."
    ),
    # Data access policy (data_access.py).
    "EXTERNAL_DATA_POLICY_LOCKED": (
        "External models (OpenRouter and Anthropic) are restricted to verified synthetic cases"
        " on this deployment; this setting cannot change that. Nothing changed."
    ),
    "DATA_ACCESS_POLICY_UNAVAILABLE": (
        "The data access policy could not be read, so local models are restricted to verified"
        " synthetic cases until IT repairs it. Nothing changed."
    ),
    "DATA_ACCESS_POLICY_CONFLICT": (
        "The data access policy changed since this view. Refresh and try again."
    ),
    "DATA_ACCESS_RATE_LIMITED": (
        "Too many data access policy changes. Wait a few minutes and try again."
    ),
    "WIDEN_CONFIRMATION_REQUIRED": (
        "Confirm that the local model may answer every case you are authorised to see."
        " Nothing changed."
    ),
}

# D-102: which message a Claude spending refusal shows (its code is returned unchanged).
CLAUDE_MESSAGE_CODES = {
    "CONTROLS_INVALID": "CONTROLS_INVALID_ANTHROPIC",
    "CAP_OUT_OF_RANGE": "CAP_OUT_OF_RANGE_ANTHROPIC",
    "RECONCILIATION_REQUIRED": "RECONCILIATION_REQUIRED_ANTHROPIC",
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


def _claude_refusal(status: int, code: str) -> HTTPException:
    return _refusal(status, code, CLAUDE_MESSAGE_CODES.get(code))


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
        restrict_remote: bool = False,
    ) -> None:
        self.settings = settings
        self.store = store
        # D-104 (re-QG M1): a model on a non-loopback endpoint is restricted with or without a
        # state database. Only a model passed in by tests or the evaluation harness is exempt.
        self.restrict_remote = restrict_remote or store is not None
        self.environ = environ
        self.transport = transport
        # The public listing reader for the D-094 preflight (tests replace it).
        self.fetch: Callable[[str], Any] | None = None
        # Starts the qualification process for a recorded run (tests run it in-process).
        self.launch: Callable[[str], Any] = self._launch_process
        # D-106: per run started here, the provider whose HR key it may be handed (set before
        # launch), and the key it was handed (provider: generation), so its supervisor ends it
        # once that key is cleared or replaced or its HR session ends.
        self.handoff_providers: dict[str, str] = {}
        self.handoffs: dict[str, dict[str, int]] = {}
        self._baseline_model = baseline_model
        self.baseline = baseline_entry(settings)
        self._lock = threading.Lock()
        # Serialises administrator changes in this process (the store's CAS covers others).
        self.change_lock = threading.Lock()
        # Which HR spending controls (model object, revision) the active model runs with.
        self._controls_lock = threading.Lock()
        self._controls_applied: tuple[int, int] | None = None
        self._claude_controls_applied: tuple[int, int] | None = None
        self._active = self._baseline(0)
        # D-098: how many qualification runs had finished when the active model was last
        # checked (None: never), so a newly finished run is noticed by every process.
        self._finished: int | None = None
        # D-098 (F2): stored reverts whose audit write failed, recorded once writes work.
        self._pending_audits: list[dict[str, Any]] = []
        # D-110: the HR reconciliation workflow, set by the router (None without a store).
        self.reconciler: Any = None
        if store is not None:
            # D-098 (F2): until the stored activation is read and usable there is no model
            # (never the environment baseline, which may be a local LLM, in place of GPT-OSS).
            self._active = self._unavailable(-1)
            self.current()
            # D-098: a run whose supervisor stopped with the previous service is closed now.
            self.close_interrupted()

    @property
    def managed(self) -> bool:
        return self.store is not None

    def _launch_process(self, qualification_id: str) -> "subprocess.Popen[bytes]":
        """``scripts/qualify_model.py`` for one recorded run: fixed arguments only (the id,
        and this service's own state database and profiles file); no output is kept."""

        path = profiles_path(self.settings)
        if not QUALIFY_SCRIPT.is_file() or path is None:
            raise ProfileConfigError("QUALIFICATION_UNAVAILABLE", "the harness is not installed")
        payload, generations = qualification_handoff(
            self.handoff_providers.pop(qualification_id, None)
        )
        handle = subprocess.Popen(
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
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # D-106: HR keys only through this pipe (never the command line or the environment).
        pipe = handle.stdin
        try:
            if pipe is None:
                raise OSError("no standard input")
            pipe.write(payload)
            pipe.close()
        except OSError:
            handle.kill()
            handle.wait()
            raise
        finally:
            del payload
        self.handoffs[qualification_id] = generations
        return handle

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

    def current(self) -> Active:
        """The active model for one request (read once, used for the whole answer), with the
        HR spending controls that apply now (another process may have changed them)."""

        active = self._current()
        self.sync_controls(active)
        return self._with_data_access(active)

    # --- data access policy ---------------------------------------------------------------

    def data_access_policy(self) -> DataAccessPolicy | None:
        # The stored policy (revision 0 when never set), or None when unreadable. Comments,
        # not docstrings, in the D-104 additions (data_access.py says why).
        if self.store is None:
            return DataAccessPolicy(0, False, None, None)
        try:
            return self.store.data_access_policy()
        except Exception:
            log.error("data access policy unavailable; local models restricted until it is")
            return None

    def _with_data_access(self, active: Active) -> Active:
        # A local or IT-configured model under the policy's restriction (or an unreadable
        # policy) answers only cases that pass the shared synthetic gate (data_access.py).
        # External models are restricted by their own code; without a store nothing changes.
        # A model on an endpoint that is not literal loopback is restricted whatever the policy,
        # with or without a state database (restrict_remote).
        if active.model is None:
            return active
        kind = data_access.model_class(active.model, active.base_url)
        if kind == data_access.LOCAL_CLASS:
            if self.store is None or not data_access.local_restricted(self.data_access_policy()):
                return active
        elif kind != data_access.IT_CLASS or not self.restrict_remote:
            return active
        model = data_access.SyntheticOnlyModel(
            active.model, self.settings, local=kind == data_access.LOCAL_CLASS
        )
        return replace(active, model=model)

    def _current(self) -> Active:
        if self.store is None:
            return self._active
        try:
            revision = self.store.revision()
            finished = self.store.finished_qualifications()
        except Exception:
            log.error("model state unavailable; keeping the current model")
            return self._active
        if (
            revision == self._active.revision
            and finished == self._finished
            and not self._pending_audits
        ):
            return self._active
        with self._lock:
            try:
                self._flush_audits()
                if self.store.revision() != self._active.revision:
                    self._active = self._restore()
                # D-098 decision 6a: a run finished (in any process, supervised or not), so
                # the active configuration is checked again before this answer uses it.
                finished = self.store.finished_qualifications()
                if finished != self._finished:
                    self._superseded_check()
                    self._finished = finished
            except Exception:
                # Never fail an answer on model state: keep the model already in use.
                log.error("model state could not be reloaded; keeping the current model")
            return self._active

    def _superseded_check(self) -> None:
        """Under ``self._lock``: stop the active configuration (stored "AI unavailable", or
        the baseline for a local profile, audited) when a later genuine quality failure
        superseded its pass. Cheap: the qualification rows only; nothing is rebuilt."""

        assert self.store is not None
        active = self._active
        if active.profile_id in (BASELINE_ID, UNAVAILABLE_ID):
            return
        basis = qualification_basis()
        if eligible_run(self.store, active.profile_id, active.fingerprint, basis)[0] is None:
            self._active = self._restore("QUALIFICATION_SUPERSEDED")

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

    def claude_spending_controls(self) -> SpendingControls | None:
        """D-102: Claude's stored controls (revision 0 when never set), None when unreadable."""

        if self.store is None:
            return SpendingControls(0, None, None, None, None)
        try:
            return self.store.claude_spending_controls()
        except Exception:
            log.error("Claude spending controls unavailable; no Claude call until they are")
            return None

    def claude_controlled(self) -> AiAssistantSettings:
        """D-102: the settings a Claude configuration runs with (HR values in place of the
        environment defaults; unreadable controls fail closed). Never GPT-OSS's controls."""

        return apply_claude_controls(self.settings, self.claude_spending_controls())

    def sync_controls(self, active: Active | None = None) -> None:
        """Put the current HR controls into the active remote model in place, so a change
        applies without a restart or a new activation and its call count is kept.

        remote_test.py is part of the qualification basis (changing it would make every
        earlier qualification out of date), so this module sets the model's settings and its
        budget guard's daily cap; both are read under the model's own lock or per reservation.
        The daily cap is still enforced by the ledger inside its admission transaction."""

        current = active or self._active
        model = current.model
        if isinstance(model, anthropic_runtime.ClaudeTestModel):
            self._sync_claude(model)
            return
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

    def _sync_claude(self, model: anthropic_runtime.ClaudeTestModel) -> None:
        # D-102: as above for an active Claude configuration and its own controls. The daily
        # cap is still enforced by the Anthropic ledger inside its admission transaction.
        with self._controls_lock:
            controls = self.claude_spending_controls()
            key = (id(model), controls.revision if controls is not None else -1)
            if self._claude_controls_applied == key and controls is not None:
                return
            settings = apply_claude_controls(self.settings, controls)
            with model._lock:  # noqa: SLF001 - see sync_controls
                model._settings = settings  # noqa: SLF001
                inner = model._inner  # noqa: SLF001
                if isinstance(inner, BudgetedChatModel):
                    inner._daily_cap = settings.anthropic_daily_cap_micro_usd  # noqa: SLF001
            self._claude_controls_applied = key

    def claude_calls_used(self) -> int | None:
        """D-102: calls an active Claude configuration made (as its call limit counts them);
        None when no Claude configuration is active. Read-only."""

        model = self._active.model
        if isinstance(model, anthropic_runtime.ClaudeTestModel):
            return model.calls_used()
        return None

    def calls_used(self) -> int | None:
        """Calls the active remote model made since its activation or this service's start
        (open calls included), as its own call limit counts them; None when it is not active.
        Read-only: the ledger is checked, never recovered or changed."""

        model = self._active.model
        # QG L3: a Claude configuration's calls are Claude's (claude_calls_used), never GPT-OSS's.
        if not isinstance(model, RemoteTestModel):
            return None
        ledger = BudgetLedger(model._ledger_file)  # noqa: SLF001 - see sync_controls
        ledger.verify()
        # D-118: the chat calls of the open session, as the call limit counts them.
        session = ledger.session()
        return 0 if session is None else session.chat_calls

    def revalidate(self) -> None:
        """D-098 decision 6a: after a run finishes, an active configuration whose pass a
        genuine quality failure superseded stops serving at once (audited); it is never
        replaced by another model automatically. Every request makes the same check when a run
        has finished (``_current``), so this only makes it happen without waiting for one."""

        self._current()

    def _restore(self, action: str = "STARTUP_REVERTED") -> Active:
        """The stored activation as a model, or its audited revert when it cannot be used.

        D-098 (F2, fail closed, ported from PR #128 R4/R5): a GPT-OSS configuration is never
        replaced by another model, not even for a moment: if its revert cannot be stored
        (the state database is locked or failing) there is no model now, at revision -1, so
        the next request reads the state and tries again until the revert is stored; after
        repeated conflicts the decision follows the last stored activation read, never a
        model kept in memory. A local profile reverts to the baseline as in D-093."""

        assert self.store is not None
        remote = self._active.profile_id in REMOTE_PROFILE_IDS | {UNAVAILABLE_ID}
        for _ in range(3):
            stored = self.store.activation(self.baseline_choice())
            if stored.active_profile_id == BASELINE_ID:
                return self._baseline(stored.revision)
            if stored.active_profile_id == UNAVAILABLE_ID:
                return self._unavailable(stored.revision)
            active, problem = self._build_stored(stored)
            if active is not None:
                return active
            remote = self.is_remote(stored.active_profile_id)
            target = Choice(UNAVAILABLE_ID, UNAVAILABLE_ID) if remote else self.baseline_choice()
            try:
                revision = self.store.activate(
                    stored.revision,
                    target,
                    _last_good(stored),
                    SYSTEM_ACTOR,
                )
            except RevisionConflict:
                continue
            except Exception:
                if not remote:
                    raise
                log.error("model state could not be updated; no model until it is")
                return self._unavailable(-1, reverted=problem)
            self._audit_revert(
                {
                    "actor": SYSTEM_ACTOR,
                    "role": None,
                    "action": action,
                    "outcome": "reverted",
                    "profile_id": stored.active_profile_id,
                    "fingerprint": stored.active_fingerprint,
                    "code": problem,
                    "revision": revision,
                }
            )
            if remote:
                return self._unavailable(revision, reverted=problem)
            return self._baseline(revision, reverted=problem)
        if remote:
            return self._unavailable(self._active.revision)
        return self._baseline(self._active.revision)

    def _audit_revert(self, event: dict[str, Any]) -> None:
        """Record a stored revert; if the audit write fails, keep it (in this process) and
        record it once the state database accepts writes again (``_flush_audits``)."""

        self._pending_audits.append(event)
        self._flush_audits()

    def _flush_audits(self) -> None:
        assert self.store is not None
        while self._pending_audits:
            try:
                self.store.record(**self._pending_audits[0])
            except Exception:
                log.error("model change audit could not be written; retrying later")
                return
            self._pending_audits.pop(0)

    def _unavailable(self, revision: int, reverted: str | None = None) -> Active:
        """D-098: no model at all (the chat gives labelled case-data guidance)."""

        return Active(
            revision=revision,
            profile_id=UNAVAILABLE_ID,
            fingerprint=UNAVAILABLE_ID,
            model=None,
            base_url=None,
            reverted=reverted,
        )

    def is_remote(self, profile_id: str) -> bool:
        """A GPT-OSS configuration (listed now, or one of the known remote profile ids)."""

        if profile_id in REMOTE_PROFILE_IDS:
            return True
        entry = load_catalogue(self.settings).get(profile_id)
        return entry is not None and entry.source == "code"

    def close_interrupted(self) -> list[str]:
        """D-098: close every run whose supervising service has gone (a restart, a crash) as
        ``INTERRUPTED``, or ``INTERRUPTED_BILLING_UNCERTAIN`` when a paid call of the remote
        model may have been open. Never restarts a run; the ledger keeps any open call, which an
        operator reconciles. Returns the ids closed."""

        if self.store is None:
            return []
        try:
            orphans = self.store.unsupervised()
        except Exception:
            log.error("qualification state unavailable; interrupted runs not checked")
            return []
        closed = []
        for qualification_id in orphans:
            item = self.store.qualification(qualification_id) or {}
            entry = load_catalogue(self.settings).get(str(item.get("profile_id")))
            code = "INTERRUPTED"
            if (
                entry is not None
                and entry.source == "code"
                and self._paid_call_uncertain(entry.deployment == "anthropic")
            ):
                code = "INTERRUPTED_BILLING_UNCERTAIN"
            self.store.finish_qualification(qualification_id, "error", code, item.get("summary"))
            final = self.store.qualification(qualification_id) or {}
            if final.get("code") != code:
                continue  # it finished by itself meanwhile
            closed.append(qualification_id)
            self.store.record(
                actor=SYSTEM_ACTOR,
                role=None,
                action="QUALIFICATION_INTERRUPTED",
                outcome="error",
                profile_id=item.get("profile_id"),
                fingerprint=item.get("fingerprint"),
                code=code,
            )
        return closed

    def _paid_call_uncertain(self, anthropic: bool = False) -> bool:
        """A remote call is still open, or one was abandoned (read-only ledger check; an
        unreadable ledger is treated as uncertain). D-099: a Claude run's own ledger."""

        path = (
            anthropic_runtime.ledger_file(self.settings)
            if anthropic
            else ledger_file(self.settings)
        )
        try:
            ledger = BudgetLedger(path)
            ledger.verify()
            status = ledger.status()
        except LedgerError:
            return True
        return status.open_calls > 0 or status.breaker_code == "abandoned_call"

    def remote_options(self) -> dict[str, Any]:
        """The D-094 remote model's test seams (tests only; None in the service)."""

        options: dict[str, Any] = {"environ": self.environ, "transport": self.transport}
        if self.fetch is not None:
            options["fetch"] = self.fetch
        return options

    def claude_options(self) -> dict[str, Any]:
        """The Claude model's test seams (D-099; tests only, None in the service)."""

        return {"environ": self.environ, "transport": self.transport}

    def remote_check(self, entry: CatalogueEntry, within_seconds: int) -> dict[str, Any]:
        """A code entry's free preflight (no inference). D-099: a Claude configuration's own
        checks, with the reconciliation no older than ``within_seconds``."""

        if entry.deployment == "anthropic":
            return anthropic_runtime.connection_check(
                self.claude_controlled(), within_seconds=within_seconds, **self.claude_options()
            )
        return connection_check(entry.settings_for(self.controlled()), **self.remote_options())

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
        basis = qualification_basis()
        if (
            qualification is None
            or qualification["status"] != "passed"
            or qualification["basis"] != basis
            or not stored.active_prompt_limit
        ):
            return None, "QUALIFICATION_OUT_OF_DATE"
        # D-098 decision 6a: a later genuine quality failure of this configuration ends it.
        if eligible_run(self.store, entry.profile_id, entry.fingerprint, basis)[0] is None:
            return None, "QUALIFICATION_SUPERSEDED"
        if entry.source == "code":
            # D-094: the remote model, gated per call and per case (remote_test.py). D-099: a
            # Claude configuration under its own Anthropic safeguards (anthropic_runtime.py);
            # GPT-OSS's HR spending controls never apply to it, only Claude's own (D-102).
            try:
                remote: ChatModel = (
                    anthropic_runtime.ClaudeTestModel(
                        self.claude_controlled(), entry.profile_id, **self.claude_options()
                    )
                    if entry.deployment == "anthropic"
                    else RemoteTestModel(
                        entry.settings_for(self.controlled()), **self.remote_options()
                    )
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
            # Changed between the checks and the store: put back exactly what was stored
            # before (D-098 F2: "AI unavailable" included, never the baseline or the last good
            # model in its place), last good model included, record that, and restore it as at
            # start-up (which reverts, audited, if it is no longer usable either).
            was = Choice(
                before.active_profile_id,
                before.active_fingerprint,
                before.active_qualification_id,
                before.active_prompt_limit,
            )
            undo = self.store.activate(revision, was, _last_good(before), by)
            self._audit_revert(
                {
                    "actor": by,
                    "role": None,
                    "action": "ACTIVATION_UNDONE",
                    "outcome": "reverted",
                    "profile_id": choice.profile_id,
                    "fingerprint": choice.fingerprint,
                    "code": problem or "BUILD_FAILED",
                    "revision": undo,
                }
            )
            self._active = self._restore()
            raise ProfileConfigError(problem or "BUILD_FAILED", "activation undone")


HANDOFF_STORES = {"openrouter": "HR_STORE", "anthropic": "ANTHROPIC_STORE"}


def hr_store(provider: str) -> key_sources.HrCredential:
    store: key_sources.HrCredential = getattr(key_sources, HANDOFF_STORES[provider])
    return store


def handoff_provider(entry: CatalogueEntry) -> str | None:
    """Whose HR key a qualification of this configuration may use (None: a local model)."""

    if entry.deployment == "anthropic":
        return "anthropic"
    return "openrouter" if entry.source == "code" else None


def qualification_handoff(provider: str | None) -> tuple[bytes, dict[str, int]]:
    """D-106: the qualified provider's HR key (only this process's memory holds it), as one
    JSON object for the qualification process's standard input, and its generation, checked
    against the HR session first. A key whose session cannot be checked now refuses the start
    (``CREDENTIAL_SESSION_UNVERIFIED``): the run never falls back to a server key in its place.
    The process inherits this one's environment unchanged, so a server key reaches it as
    before when no HR key exists."""

    if provider is None:
        return b"{}", {}
    entry = hr_store(provider).current(max_age=0)
    if entry.held:
        raise ProfileConfigError("CREDENTIAL_SESSION_UNVERIFIED", "the HR session is unchecked")
    if entry.key is None:
        return b"{}", {}
    payload = json.dumps({provider: entry.key.get_secret_value()}).encode("utf-8")
    return payload, {provider: entry.generation}


def handoff_revoked(generations: dict[str, int]) -> bool:
    """Whether a key handed to a running qualification was cleared, replaced or dropped with
    its HR session (or its session cannot be checked now)."""

    for provider, generation in generations.items():
        entry = hr_store(provider).current()
        if entry.key is None or entry.generation != generation:
            return True
    return False


def _last_good(stored: Activation) -> Choice | None:
    if stored.last_good_profile_id is None or stored.last_good_fingerprint is None:
        return None
    return Choice(
        stored.last_good_profile_id,
        stored.last_good_fingerprint,
        stored.last_good_qualification_id,
        stored.last_good_prompt_limit,
    )


# --- D-098: what a qualification outcome means, and which run makes a profile eligible -------

# Preflight checks whose failure means spend is not accounted for: an operator reconciles.
_BILLING_CHECKS = frozenset(
    {
        "ledger.breaker_closed_no_open_calls",
        "ledger.usage_reconciled",
        "ledger.earlier_calls_verified",
        "ledger.healthy",
        # D-099: the Anthropic ledger's own checks.
        "ledger.profile",
        "ledger.reconciled_recently",
    }
)
# Checks HR can resolve with the spending controls (or by waiting for the daily reset).
_BUDGET_CHECKS = frozenset({"ledger.daily_room_for_one_call", "ledger.headroom_for_one_call"})
# D-098: the OpenRouter key's own limit has no room. Only the key's owner can raise it at
# OpenRouter; it is never an HR spending control.
_KEY_LIMIT_CHECKS = frozenset({"key.room_for_one_call"})
# Server settings, the key's own limit or owner attestations: IT or the owner.
_CONFIGURATION_CHECKS = frozenset(
    {
        "test_mode.ready",
        "gate.account",
        "endpoint.approved",
        "key.limit_set",
        "key.limit_never_resets",
        "key.limit_finite",
        "ledger.cap_within_allocation",
        "ledger.cap_above_opening",
        "owner.auto_topup_off",
        "owner.prompt_logging_off",
        # D-099: the Claude configuration's settings, key, workspace and ledger ceiling.
        "anthropic.ready",
        "anthropic.inference_key",
        "anthropic.workspace_matches",
        "anthropic.model_available",
        "ledger.cap_within_ceiling",
    }
)
# Provider answers that trip the ledger breaker (budget.TRIP_ERROR_CLASSES): not retryable.
_PROVIDER_REFUSALS = frozenset(
    {
        "bad_request",
        "auth",
        "payment",
        "payment_key_limit",
        "forbidden",
        "not_allowed",
        "no_provider",
    }
)
# Errors that end a run without saying anything about the model.
_TECHNICAL_ERRORS = frozenset(
    {
        "INTERRUPTED",
        "STALE",
        "PROCESS_EXITED",
        "SUPERVISOR_FAILED",
        "HARNESS_ERROR",
        "DEADLINE",
        "CANCELLED",
    }
)


@dataclass(frozen=True)
class Diagnosis:
    """What a run's outcome means for HR, as closed codes (the page names them).

    ``category``: passed, running, cancelled, technical, budget, configuration, quality or
    billing_uncertain. ``retryable``: a retry is worth making now without another change.
    ``supersedes_pass``: a genuine quality failure, so an earlier pass of the same
    configuration no longer counts (D-098 decision 6a); nothing else ever supersedes one."""

    category: str
    cause: str
    action: str
    retryable: bool = False
    supersedes_pass: bool = False

    def view(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "cause": self.cause,
            "action": self.action,
            "retryable": self.retryable,
            "supersedes_pass": self.supersedes_pass,
        }


def diagnose(item: dict[str, Any], *, current: bool = True) -> Diagnosis:
    """Classify one stored run from its status, code and content-free summary.

    ``current``: the run was made for the configuration's current fingerprint and answer code
    (the qualification basis). A pass that is no longer current cannot be activated, so HR is
    told to qualify the current configuration (the paid-run confirmation, budget checks and
    decision 6a still apply to that new run). Only a pass is treated this way: a failure keeps
    its own classification and escalation."""

    status, code = item.get("status"), str(item.get("code") or "")
    summary = item.get("summary") or {}
    if status == "running":
        return Diagnosis("running", "RUNNING", "WAIT")
    if status == "passed":
        if not current:
            return Diagnosis("configuration", "OUT_OF_DATE", "RUN_AGAIN", retryable=True)
        return Diagnosis("passed", "PASSED", "NONE")
    if status == "cancelled":
        return Diagnosis("cancelled", "CANCELLED", "RUN_AGAIN", retryable=True)
    if code == "INTERRUPTED_BILLING_UNCERTAIN":
        return Diagnosis("billing_uncertain", code, "ESCALATE_OPERATOR")
    if code in _TECHNICAL_ERRORS:
        return Diagnosis("technical", code, "RUN_AGAIN", retryable=True)
    if code == "CREDENTIAL_REVOKED":
        # D-106: the HR session key it was given ended (sign-out, expiry, clearing): a key is
        # needed again and Test connection must pass before a retry. Nothing about the model.
        return Diagnosis("configuration", code, "TEST_CONNECTION")
    if code == "CONFIG_MISMATCH":
        # The settings or the answer code changed while it ran: qualify the current ones.
        return Diagnosis("configuration", code, "RUN_AGAIN", retryable=True)
    if code == "CONNECTION_FAILED":
        return _connection_diagnosis(summary.get("connection") or {})
    if code.startswith("GATES_FAILED:"):
        return _gate_diagnosis(summary)
    # Settings the server refused (REMOTE_MANIFEST_MISSING, LEDGER_UNAVAILABLE, ...).
    return Diagnosis("configuration", code or "UNKNOWN", "ESCALATE_IT")


def _connection_diagnosis(connection: dict[str, Any]) -> Diagnosis:
    failed = {str(c.get("check")) for c in connection.get("checks") or [] if not c.get("ok")}
    if failed & _BILLING_CHECKS:
        return Diagnosis("billing_uncertain", "LEDGER_NOT_RECONCILED", "ESCALATE_OPERATOR")
    if failed & _CONFIGURATION_CHECKS:
        return Diagnosis("configuration", "SERVER_SETTINGS", "ESCALATE_IT")
    if failed & _KEY_LIMIT_CHECKS:
        return Diagnosis("budget", "KEY_LIMIT_EXHAUSTED", "ESCALATE_KEY_OWNER")
    if failed & _BUDGET_CHECKS:
        return Diagnosis("budget", "NO_ROOM_FOR_CALLS", "REVIEW_SPENDING", retryable=True)
    # The provider or its public listing could not be read, or a local model did not answer.
    return Diagnosis("technical", "PROVIDER_UNAVAILABLE", "TEST_CONNECTION", retryable=True)


def _gate_diagnosis(summary: dict[str, Any]) -> Diagnosis:
    """The category explains what HR sees first (billing, budget, technical, quality); a
    genuine quality failure supersedes an earlier pass whatever the category (D-098 6a),
    so billing and quality stay distinct and neither hides the other."""

    result = _gate_category(summary)
    escalation = _quality_escalation(summary)
    if not result.supersedes_pass and escalation is not None:
        # The re-run is refused (QUALIFICATION_ESCALATION_REQUIRED), so the advice is the
        # quality escalation, never a retry; an unreconciled billing run still goes to the
        # operator first (both must be resolved).
        action = result.action if result.category == "billing_uncertain" else escalation
        return replace(result, action=action, retryable=False, supersedes_pass=True)
    return result


def _quality_escalation(summary: dict[str, Any]) -> str | None:
    """Who resolves a genuine quality failure, or None: a developer for G-3 (an unsafe line
    shown) or G-6 with lines written; IT for G-7 for the configuration's own reasons
    (``_g7_cause``; never a provider failure mid-answer)."""

    gates = {g.get("gate"): g for g in summary.get("gates") or [] if isinstance(g, dict)}

    def failed(gate: str) -> bool:
        item = gates.get(gate)
        return bool(item and item.get("gating") and not item.get("passed"))

    validity = (gates.get("G-6") or {}).get("value")
    if failed("G-3") or (failed("G-6") and isinstance(validity, int | float)):
        return "ESCALATE_DEVELOPER"
    return "ESCALATE_IT" if _g7_cause(summary) is not None else None


def _g7_cause(summary: dict[str, Any]) -> str | None:
    """Why G-7 failed, when it is the configuration's own failure: answers cut short by the
    token limits beyond G7_MAX_CUT_SHORT once those cut short by a provider failure
    mid-answer (``stream_partial``: technical, see G-4) are set aside, or context capacity
    not verified for the prompts. None when G-7 passed or only provider failures explain it."""

    gates = {g.get("gate"): g for g in summary.get("gates") or [] if isinstance(g, dict)}
    item = gates.get("G-7") or {}
    if not item.get("gating") or item.get("passed"):
        return None
    raw = item.get("value")
    value: dict[str, Any] = raw if isinstance(raw, dict) else {}
    limit, largest = value.get("prompt_limit"), value.get("largest_prompt_bound")
    if value.get("capacity") != "verified" or (
        isinstance(limit, int) and isinstance(largest, int) and largest > limit
    ):
        return "CAPACITY_NOT_VERIFIED"
    metrics = summary.get("metrics") or {}
    answers = metrics.get("answers")
    rate = value.get("cut_short_rate")
    if (
        not isinstance(answers, int)
        or isinstance(answers, bool)
        or answers <= 0
        or not isinstance(rate, int | float)
    ):
        return "ANSWERS_CUT_SHORT"  # cannot be explained away: fail safe
    partial = (metrics.get("fallback_reasons") or {}).get("stream_partial", 0)
    if not isinstance(partial, int) or isinstance(partial, bool) or partial < 0:
        return "ANSWERS_CUT_SHORT"  # malformed: fail safe
    # Whole answers, not the rounded rate (the rate is stored to 4 decimals): cut short by
    # the configuration itself = all cut short - those cut short by a provider failure.
    genuine = round(rate * answers) - partial
    return "ANSWERS_CUT_SHORT" if genuine > G7_MAX_CUT_SHORT * answers else None


def _gate_category(summary: dict[str, Any]) -> Diagnosis:
    gates = {g.get("gate"): g for g in summary.get("gates") or [] if isinstance(g, dict)}
    metrics = summary.get("metrics") or {}

    def failed(gate: str) -> bool:
        item = gates.get(gate)
        return bool(item and item.get("gating") and not item.get("passed"))

    reasons = metrics.get("fallback_reasons") or {}
    errors = metrics.get("call_errors") or {}
    calls, verified = metrics.get("remote_calls"), metrics.get("remote_calls_verified")
    if failed("G-3"):  # a displayed line that is not allowed: never acceptable
        return Diagnosis("quality", "UNSAFE_LINE", "ESCALATE_DEVELOPER", supersedes_pass=True)
    if failed("G-8") and isinstance(calls, int) and calls > 0 and verified != calls:
        return Diagnosis("billing_uncertain", "CALLS_NOT_VERIFIED", "ESCALATE_OPERATOR")
    validity = (gates.get("G-6") or {}).get("value")
    if failed("G-6") and isinstance(validity, int | float):
        # Lines were written and too few passed the exact-line check.
        return Diagnosis("quality", "LOW_LINE_VALIDITY", "ESCALATE_DEVELOPER", supersedes_pass=True)
    if int(reasons.get("budget_refused", 0)) + int(reasons.get("remote_boundary", 0)) > 0:
        # Calls were refused before anything was sent (allowance, limits, preflight).
        return Diagnosis("budget", "CALLS_REFUSED", "REVIEW_SPENDING", retryable=True)
    if failed("G-4") or failed("G-2") or (failed("G-6") and validity is None):
        if set(errors) & _PROVIDER_REFUSALS:
            return Diagnosis("technical", "PROVIDER_REFUSED", "ESCALATE_OPERATOR")
        return Diagnosis("technical", "MODEL_UNAVAILABLE", "RETRY_LATER", retryable=True)
    g7 = _g7_cause(summary)
    if g7 == "ANSWERS_CUT_SHORT":
        return Diagnosis("quality", g7, "ESCALATE_IT", supersedes_pass=True)
    if g7 == "CAPACITY_NOT_VERIFIED":
        return Diagnosis("configuration", g7, "ESCALATE_IT", supersedes_pass=True)
    if failed("G-7"):  # only provider failures mid-answer cut the answers short
        return Diagnosis("technical", "MODEL_UNAVAILABLE", "RETRY_LATER", retryable=True)
    return Diagnosis("technical", "UNKNOWN", "RUN_AGAIN", retryable=True)


def eligible_run(
    store: ModelAdminStore, profile_id: str, fingerprint: str, basis: str
) -> tuple[dict[str, Any] | None, str | None]:
    """The run that lets this configuration be activated (D-098 decision 6a): its newest
    passing run for the current fingerprint and answer code, unless a genuine quality failure
    came after it. Technical, budget, configuration, billing and cancelled outcomes never
    take a pass away. Returns (run, None), or (None, the blocker code)."""

    item = _deciding_run(store, profile_id, fingerprint, basis)
    if item is None:
        return None, "NOT_QUALIFIED"
    if item["status"] == "passed":
        return item, None
    return None, "QUALIFICATION_SUPERSEDED"


def superseding_run(
    store: ModelAdminStore, profile_id: str, fingerprint: str, basis: str
) -> dict[str, Any] | None:
    """The genuine quality failure that blocks this configuration under decision 6a, if any.
    The AI Models page shows its escalation even when a later run (for example a pass made
    for another configuration or answer code) is the latest one."""

    item = _deciding_run(store, profile_id, fingerprint, basis)
    return None if item is None or item["status"] == "passed" else item


def _deciding_run(
    store: ModelAdminStore, profile_id: str, fingerprint: str, basis: str
) -> dict[str, Any] | None:
    """The newest current run that decides decision 6a: a pass, or a genuine quality failure
    that came after any pass. None when neither exists."""

    for item in store.qualifications_for(profile_id):
        if item["fingerprint"] != fingerprint or item["basis"] != basis:
            continue
        if item["status"] == "passed":
            return item
        if item["status"] != "running" and diagnose(item).supersedes_pass:
            return item
    return None


def open_selector(
    settings: AiAssistantSettings, baseline_model: ChatModel | None, injected: bool
) -> ModelSelector:
    """Managed only when IT named a profiles file, the model is on, and the model was not
    passed in (tests and the evaluation harness keep a fixed model)."""

    if injected or not settings.llm_enabled or not settings.model_profiles_file:
        return ModelSelector(settings, baseline_model, restrict_remote=not injected)
    return ModelSelector(settings, baseline_model, ModelAdminStore(store_file(settings)))


def store_file(settings: AiAssistantSettings) -> Path:
    path = Path(settings.model_admin_db_path)
    return path if path.is_absolute() else ASSISTANT_DIR / path


class AnthropicEnablementRequest(BaseModel):
    # D-107: Claude's provider setup (no key; the workspace id is not secret).
    model_config = ConfigDict(extra="forbid")

    expected_revision: StrictInt = Field(ge=0)
    enabled: StrictBool
    workspace_id: str = Field(default="", max_length=80)
    workspace_limit_micro_usd: StrictInt | None = None
    confirmations: list[str] = Field(default_factory=list, max_length=8)
    # D-118 S4: how a fresh Claude ledger opens (only when none exists yet): a new, dedicated
    # workspace with no earlier usage (owner-confirmed), or the workspace's cumulative cost
    # from the Console. Never zero by default.
    opening: Literal["new_workspace", "console_usage"] | None = None
    opening_usage_micro_usd: StrictInt | None = None


class SessionStartRequest(BaseModel):
    # D-118 S3: HR's explicit new session on one provider's ledger.
    model_config = ConfigDict(extra="forbid")

    provider: Literal["anthropic", "openrouter"]
    allowance_micro_usd: StrictInt = Field(ge=1, le=SESSION_MAX_MICRO_USD)
    expected_session_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")


class SessionAllowanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["anthropic", "openrouter"]
    allowance_micro_usd: StrictInt = Field(ge=1, le=SESSION_MAX_MICRO_USD)
    expected_revision: StrictInt = Field(ge=1)


class BreakerResumeRequest(BaseModel):
    # D-118 S6: only a conservative-only breaker, on the ledger's own proof.
    model_config = ConfigDict(extra="forbid")

    provider: Literal["anthropic", "openrouter"]
    code: Literal["abandoned_call", "usage_missing"]


class ChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=0)
    acknowledge_quality_unscored: bool = False


class QualificationRequest(BaseModel):
    """D-098: a paid (remote) run needs its number of calls confirmed; a local run needs none."""

    model_config = ConfigDict(extra="forbid")

    confirm_paid_calls: StrictInt | None = None


class SpendingControlsRequest(BaseModel):
    """Both controls at once; bounds are checked by the route (a fixed refusal message)."""

    model_config = ConfigDict(extra="forbid")

    expected_revision: StrictInt = Field(ge=0)
    daily_cap_micro_usd: StrictInt
    max_calls: StrictInt
    # D-098: a raise of the daily limit needs the same amount again (the HR confirmation).
    confirm_daily_cap_micro_usd: StrictInt | None = None


class ClaudeSpendingControlsRequest(SpendingControlsRequest):
    """D-102: Claude's controls. A raise of the call limit also needs the same number again
    (QG L1); GPT-OSS's request model is unchanged."""

    confirm_max_calls: StrictInt | None = None


class DataAccessRequest(BaseModel):
    # Restrict AI to verified synthetic cases, per provider class. restrict_external must stay
    # true (locked); letting a restricted local model answer every case needs confirm_widen.
    model_config = ConfigDict(extra="forbid")

    expected_revision: StrictInt = Field(ge=0)
    restrict_external: StrictBool = True
    restrict_local: StrictBool
    confirm_widen: StrictBool = False


class ReconciliationPreviewRequest(BaseModel):
    # D-110: HR's Anthropic Console reading. Times are ISO 8601 with their offset.
    model_config = ConfigDict(extra="forbid")

    usage_micro_usd: StrictInt = Field(ge=0, le=MAX_MICRO_USD)
    as_of: str = Field(max_length=40)
    as_of_kind: str = Field(max_length=40)
    viewed_at: str = Field(max_length=40)
    scope_workspace: StrictBool
    scope_only: StrictBool
    scope_cumulative: StrictBool


class ReconciliationApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preview_id: str = Field(min_length=32, max_length=32, pattern="^[0-9a-f]{32}$")
    # The figure typed again (the HR confirmation step).
    confirm_usage_micro_usd: StrictInt
    scope_workspace: StrictBool
    scope_only: StrictBool
    scope_cumulative: StrictBool


# A short operator note; never a key (the D-106 key forms and long token-like runs refused).
RECOVERY_NOTE_MAX = 280
_NOTE_REFUSED = re.compile(r"sk-|sk_|Bearer\s|-----BEGIN|[A-Za-z0-9_\-]{32,}")


class RecoveryRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_code: str = Field(min_length=3, max_length=64, pattern="^[A-Z0-9_]+$")
    note: str | None = Field(default=None, max_length=RECOVERY_NOTE_MAX)


class RecoveryCloseBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(pattern="^(resolved|withdrawn)$")


class LifetimeCapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cap_micro_usd: StrictInt
    # A raise needs the same amount again (the HR confirmation step).
    confirm_cap_micro_usd: StrictInt | None = None
    # D-098 (F1): the cap the page showed when HR decided (required for a raise).
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

    def load(request: Request) -> dict[str, Any]:
        check_origin(request)
        try:
            actor = backend.load_actor(request.cookies.get(SESSION_COOKIE_NAME))
        except ClmBackendError as exc:
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

    def hr_session_live(session: SecretStr, user_id: str) -> bool | None:
        # D-106: the session that entered an HR key, asked about with its own cookie (an RM's
        # session is never used for this): live only while the same user is signed in and may
        # still manage AI models. Ended, expired or revoked: False. Unreachable: None.
        try:
            actor = backend.load_actor(session.get_secret_value())
        except ClmBackendError as exc:
            return False if exc.status_code in (401, 403, 404) else None
        except Exception:  # noqa: BLE001 - an unexpected reply holds the key back
            return None
        current = actor["profile"]
        return current.get("user_id") == user_id and CAPABILITY in (
            current.get("capabilities") or []
        )

    key_sources.install_session_check(hr_session_live)

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
        item: dict[str, Any] | None,
        entry: CatalogueEntry,
        basis: str,
        superseding: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """The last argument (the overview): the genuine quality failure that blocks this
        configuration; its escalation is the advice whatever run came later (decision 6a)."""

        if item is None:
            return None
        summary = item.get("summary") or {}
        current = item["fingerprint"] == entry.fingerprint and item["basis"] == basis
        diagnosis = diagnose(superseding) if superseding else diagnose(item, current=current)
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
            "current": current,
            "gates": summary.get("gates"),
            "metrics": summary.get("metrics"),
            "lines": summary.get("lines"),
            "capacity": summary.get("capacity"),
            "connection": summary.get("connection"),
            "quality": summary.get("quality"),
            "reproducibility": summary.get("reproducibility"),
            "diagnosis": diagnosis.view(),
        }

    def readiness(entry: CatalogueEntry, blocker: str | None) -> list[str]:
        if entry.profile_id == BASELINE_ID:
            return (
                [] if entry.status == "selectable" else [entry.reason or "PROFILE_NOT_SELECTABLE"]
            )
        if entry.status != "selectable":
            return [entry.reason or "PROFILE_NOT_SELECTABLE"]
        return [blocker] if blocker else []

    def data_access_view(active: Active | None = None) -> dict[str, Any]:
        current = active or selector.current()
        return data_access.view(
            selector.data_access_policy(),
            managed=selector.managed,
            remote_restricted=selector.restrict_remote,
            settings=settings,
            model=current.model,
            base_url=current.base_url,
        )

    def overview() -> dict[str, Any]:
        selector.close_interrupted()
        catalogue = load_catalogue(settings)
        active = selector.current()
        basis = qualification_basis()
        quality, reason = quality_state()
        store = selector.store
        stored = store.activation(selector.baseline_choice()) if store else None
        profiles = []
        for entry in catalogue.entries:
            latest = store.latest_qualification(entry.profile_id) if store else None
            eligible, blocker = (
                eligible_run(store, entry.profile_id, entry.fingerprint, basis)
                if store
                else (None, "NOT_QUALIFIED")
            )
            superseding = (
                superseding_run(store, entry.profile_id, entry.fingerprint, basis)
                if store and blocker == "QUALIFICATION_SUPERSEDED"
                else None
            )
            profiles.append(
                {
                    **entry.view(),
                    "active": entry.profile_id == active.profile_id,
                    "connection_test": store.connection_test(entry.profile_id) if store else None,
                    "qualification": qualification_view(latest, entry, basis, superseding),
                    "activation_blockers": readiness(entry, blocker),
                    # D-098: the passing run activation would use (it may be older than the
                    # latest run when that one failed for a technical or budget reason).
                    "eligible_qualification": None
                    if eligible is None
                    else {
                        "qualification_id": eligible["qualification_id"],
                        "finished_at": eligible["finished_at"],
                        "is_latest": latest is not None
                        and latest["qualification_id"] == eligible["qualification_id"],
                    },
                    "paid_qualification": paid_estimate(entry),
                }
            )
        active_entry = catalogue.get(active.profile_id)
        last_good = _last_good(stored) if stored else None
        running = store.running_qualification() if store else None
        return {
            "configured": selector.managed,
            "file_status": catalogue.file_status,
            "file_errors": list(catalogue.file_errors),
            "model_enabled": settings.llm_enabled,
            # D-098 (F2): while a revert is not yet stored (in-memory revision -1) the page
            # gets the stored revision, so HR can still activate a model (compare-and-set).
            "revision": (active.revision if active.revision >= 0 else stored.revision)
            if selector.managed and stored is not None
            else 0,
            "active": {
                "profile_id": active.profile_id,
                "display_name": active_entry.display_name
                if active_entry
                else (
                    "AI unavailable" if active.profile_id == UNAVAILABLE_ID else active.profile_id
                ),
                # D-098: no model answers; the chat gives labelled case-data guidance only.
                "unavailable": active.profile_id == UNAVAILABLE_ID,
                "model_id": active.model.name if active.model is not None else None,
                "prompt_limit": active.prompt_limit,
                "qualification_id": active.qualification_id,
                "changed_at": stored.changed_at if stored else None,
                "changed_by": stored.changed_by if stored else None,
                "config_changed": active_entry is not None
                and active_entry.fingerprint != active.fingerprint,
                "reverted": active.reverted,
            },
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
            # D-107: Claude's own view no longer needs the D-094 decision name.
            "budget": budget_view()
            if settings.local_api_test_decision
            else {"configured": False, "claude": claude_budget_view()},
            "data_access": data_access_view(active),
            "anthropic_setup": anthropic_setup_view(),
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
            result = selector.remote_check(entry, anthropic_runtime.CHAT_RECONCILE_SECONDS)
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
        handed = selector.handoffs.pop(qualification_id, {})
        try:
            while handle.poll() is None:
                now = time.monotonic()
                if handed and handoff_revoked(handed):
                    ended = "CREDENTIAL_REVOKED"
                    break
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
        selector.revalidate()

    def paid_estimate(entry: CatalogueEntry) -> dict[str, Any] | None:
        """D-098: what a paid qualification of this remote configuration may spend, against
        what the strictest applicable limit leaves (read-only; None for a local model)."""

        if entry.source != "code" or entry.status != "selectable":
            return None
        manifest = qualification_manifest(settings)
        try:
            # D-099: a Claude run against the Anthropic ledger, reconciled within 24 hours.
            view = (
                anthropic_runtime.budget_status(
                    selector.claude_controlled(), environ=selector.environ
                )
                if entry.deployment == "anthropic"
                else budget_status(
                    entry.settings_for(selector.controlled()), environ=selector.environ
                )
            )
        except Exception:  # an unreadable spending view never allows a paid run
            log.error("spending view unavailable for the qualification estimate")
            view = {"refusal": "LEDGER_UNAVAILABLE", "effective_remaining_micro_usd": 0}
        calls = len(manifest) if manifest else None
        reservation = view.get("reservation_micro_usd")
        estimate = (
            calls * reservation if calls is not None and isinstance(reservation, int) else None
        )
        remaining = view.get("effective_remaining_micro_usd")
        refusal = view.get("refusal")
        return {
            "calls": calls,
            "reservation_micro_usd": reservation,
            "estimate_micro_usd": estimate,
            "effective_remaining_micro_usd": remaining,
            "refusal": refusal,
            "sufficient": refusal is None
            and estimate is not None
            and isinstance(remaining, int)
            and remaining >= estimate,
        }

    def refuse_start(
        entry: CatalogueEntry, profile: dict[str, Any], code: str, status: int = 409
    ) -> HTTPException:
        audit(
            profile,
            "QUALIFICATION_STARTED",
            "refused",
            profile_id=entry.profile_id,
            fingerprint=entry.fingerprint,
            code=code,
        )
        # D-099: only the message differs for Claude; the code, status and audit are the same.
        message = (
            "PROVIDER_LIMIT_NOT_CHECKED_ANTHROPIC"
            if code == "PROVIDER_LIMIT_NOT_CHECKED" and entry.deployment == "anthropic"
            else None
        )
        return _refusal(status, code, message)

    @router.post("/{profile_id}/qualifications", status_code=202)
    def post_qualification(
        profile_id: str, profile: Admin, body: QualificationRequest | None = None
    ) -> dict[str, Any]:
        store = managed()
        entry = entry_for(load_catalogue(settings), profile_id, profile, "QUALIFICATION_STARTED")
        # D-106: a held-back HR key refuses the start (never a server key in its place).
        provider = handoff_provider(entry)
        if provider is not None and hr_store(provider).current(max_age=0).held:
            raise refuse_start(entry, profile, "CREDENTIAL_SESSION_UNVERIFIED")
        # The same checks the qualification process applies, before anything starts.
        if entry.source == "code":
            # D-094: a paid run, so only the configured, counted question manifest.
            if qualification_manifest(settings) is None:
                raise refuse_start(entry, profile, "REMOTE_MANIFEST_MISSING")
        else:
            adapter_for(entry, profile, "QUALIFICATION_STARTED", loopback=True)
        # D-098: after a genuine quality failure the same configuration is not run again; a
        # developer or IT changes it first (which makes it a new configuration or answer code).
        if eligible_run(store, entry.profile_id, entry.fingerprint, qualification_basis())[1] == (
            "QUALIFICATION_SUPERSEDED"
        ):
            raise refuse_start(entry, profile, "QUALIFICATION_ESCALATION_REQUIRED")
        if entry.source == "code":
            # D-098: a paid run starts only when HR confirmed its number of calls and every one
            # of them fits the strictest applicable limit (daily, lifetime, the key's own).
            estimate = paid_estimate(entry) or {}
            if body is None or body.confirm_paid_calls != estimate.get("calls"):
                raise refuse_start(entry, profile, "PAID_CONFIRMATION_REQUIRED", 400)
            if not estimate.get("sufficient"):
                refusal = str(estimate.get("refusal") or "")
                if refusal.startswith("BREAKER_OPEN") or refusal in (
                    "LEDGER_UNAVAILABLE",
                    "RECONCILIATION_STALE",
                    "LEDGER_PROFILE_MISMATCH",
                ):
                    raise refuse_start(entry, profile, "QUALIFICATION_BILLING_UNRECONCILED")
                if refusal in ("PROVIDER_LIMIT_NOT_CHECKED", "PROVIDER_CHECK_FAILED"):
                    raise refuse_start(entry, profile, "PROVIDER_LIMIT_NOT_CHECKED")
                if refusal == "PROVIDER_LIMIT_EXHAUSTED":
                    raise refuse_start(entry, profile, "PROVIDER_KEY_LIMIT_EXHAUSTED")
                raise refuse_start(entry, profile, "QUALIFICATION_BUDGET_INSUFFICIENT")
        selector.close_interrupted()
        try:
            qualification_id = store.begin_qualification(
                entry.profile_id,
                entry.fingerprint,
                qualification_basis(),
                str(profile.get("user_id")),
                0,
            )
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
        if provider is not None:
            selector.handoff_providers[qualification_id] = provider
        try:
            handle = selector.launch(qualification_id)
        except (OSError, ProfileConfigError) as error:
            selector.handoff_providers.pop(qualification_id, None)
            code = (
                error.code
                if isinstance(error, ProfileConfigError)
                and error.code == "CREDENTIAL_SESSION_UNVERIFIED"
                else "QUALIFICATION_UNAVAILABLE"
            )
            store.finish_qualification(qualification_id, "error", code, None)
            audit(
                profile,
                "QUALIFICATION_STARTED",
                "refused",
                profile_id=entry.profile_id,
                fingerprint=entry.fingerprint,
                code=code,
            )
            raise _refusal(409, code) from None
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
        selector.close_interrupted()
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
        # D-098: a run with no supervisor left is closed as interrupted, not left to wait.
        if qualification_id in selector.close_interrupted():
            audit(profile, "QUALIFICATION_CANCEL_REQUESTED", "requested", code="INTERRUPTED")
            return {"qualification_id": qualification_id, "cancel_requested": False}
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
                    # D-099: a Claude configuration needs a reconciliation within 24 hours.
                    selector.remote_check(entry, anthropic_runtime.PAID_RECONCILE_SECONDS)
                    if entry.source == "code"
                    else anyio.run(
                        connection_test, adapter_for(entry, profile, action), entry.model_id or ""
                    )
                )
                if probe["outcome"] != "passed":
                    raise refuse("CONNECTION_FAILED")
                choice = qualified
            last = _last_good(stored)
            previous = (
                # D-098: "AI unavailable" is never a rollback target; the last good one stays,
                # unless it is the one now being made active.
                (last if last is not None and last.profile_id != entry.profile_id else None)
                if stored.active_profile_id == UNAVAILABLE_ID
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
        # D-098 decision 6a: Activate and Rollback both refuse a pass that a later genuine
        # quality failure of the same configuration superseded.
        if eligible_run(store, entry.profile_id, entry.fingerprint, item["basis"])[0] is None:
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
            assert selector.store is not None
            eligible, _ = eligible_run(
                selector.store, entry.profile_id, entry.fingerprint, qualification_basis()
            )
            return entry, qualified_choice(
                entry, eligible["qualification_id"] if eligible else None
            )

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

    def credential_view(provider: str = "openrouter") -> dict[str, Any]:
        if provider == "anthropic":
            return anthropic_runtime.resolve_key(selector.environ)[1].view()
        return key_sources.resolve(selector.environ)[1].view()

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

    # D-106: one HR key per provider (OpenRouter for GPT-OSS, Anthropic for both Claude
    # configurations), bound to the HR session that entered it and used before an environment
    # or .env key. /credential stays the OpenRouter key's address.
    # The key shape HR may enter, and what a key change makes stale.
    providers: dict[str, tuple[re.Pattern[str], Callable[[], None]]] = {
        "openrouter": (key_sources.HR_KEY, forget_provider),
        "anthropic": (anthropic_runtime.HR_KEY, lambda: None),
    }

    def provider_store(provider: str) -> key_sources.HrCredential:
        # Looked up per request, so a replaced store (tests) is the one used.
        return key_sources.ANTHROPIC_STORE if provider == "anthropic" else key_sources.HR_STORE

    async def set_credential(
        request: Request, profile: dict[str, Any], provider: str
    ) -> dict[str, Any]:
        action = "CREDENTIAL_SET"
        guard_change(request, profile, action)
        shape, forget = providers[provider]
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
        if not isinstance(key, str) or not shape.fullmatch(key):
            audit(profile, action, "refused", profile_id=provider, code="CREDENTIAL_INVALID")
            raise _refusal(400, "CREDENTIAL_INVALID")
        secret = SecretStr(key)
        del key, raw
        await anyio.to_thread.run_sync(recheck, request, profile, action)
        session = request.cookies.get(SESSION_COOKIE_NAME)
        if not session:
            raise _refusal(401, "AUTHENTICATION_REQUIRED")
        provider_store(provider).set(
            secret, str(profile.get("user_id")), session=SecretStr(session)
        )
        forget()  # the spending view's key limit was read for the previous key
        audit(profile, action, "applied", profile_id=provider)
        view: dict[str, Any] = await anyio.to_thread.run_sync(credential_view, provider)
        return view

    def clear_credential(
        request: Request, profile: dict[str, Any], provider: str
    ) -> dict[str, Any]:
        action = "CREDENTIAL_CLEARED"
        guard_change(request, profile, action)
        recheck(request, profile, action)
        if not provider_store(provider).clear():
            audit(profile, action, "refused", profile_id=provider, code="CREDENTIAL_NOT_HR_MANAGED")
            raise _refusal(409, "CREDENTIAL_NOT_HR_MANAGED")
        providers[provider][1]()
        audit(profile, action, "applied", profile_id=provider)
        return credential_view(provider)

    @router.get("/credential")
    def get_credential(profile: Admin) -> dict[str, Any]:
        return credential_view()

    @router.put("/credential")
    async def put_credential(request: Request, profile: Admin) -> dict[str, Any]:
        return await set_credential(request, profile, "openrouter")

    @router.delete("/credential")
    def delete_credential(request: Request, profile: Admin) -> dict[str, Any]:
        return clear_credential(request, profile, "openrouter")

    @router.get("/credential/anthropic")
    def get_anthropic_credential(profile: Admin) -> dict[str, Any]:
        return credential_view("anthropic")

    @router.put("/credential/anthropic")
    async def put_anthropic_credential(request: Request, profile: Admin) -> dict[str, Any]:
        return await set_credential(request, profile, "anthropic")

    @router.delete("/credential/anthropic")
    def delete_anthropic_credential(request: Request, profile: Admin) -> dict[str, Any]:
        return clear_credential(request, profile, "anthropic")

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
                # D-098: only the ledger's technical bound (no US$1 allocation ceiling).
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
            "daily_cap_default_micro_usd": DEFAULT_DAILY_CAP_MICRO_USD,
            # D-098: what a raise of either limit needs (shown on the page before HR asks).
            "raise_requires": ["confirmation", "finite_provider_limit"],
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
        view["claude"] = claude_budget_view()
        return view

    def claude_budget_view() -> dict[str, Any]:
        # B1 (QG L1): every Claude ledger figure in one response comes from one unchanged ledger
        # state. The reads below run in several transactions (budget_status, the call count, the
        # lifetime and reconciliation reads), so they are bracketed by SQLite's data_version on a
        # separate read-only connection (mode=ro: it can never write or recover the ledger). A
        # commit by any other connection or process in between changes it, and the whole view is
        # read again; if the ledger keeps changing, its figures are withheld (fail closed).
        path = Path(anthropic_runtime.ledger_file(settings)).resolve()
        try:
            watch = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True, timeout=2)
        except sqlite3.Error:
            # No readable ledger file: the reads report it themselves (nothing to mix).
            return claude_budget_read()
        with closing(watch):

            def version() -> int:
                return int(watch.execute("PRAGMA data_version").fetchone()[0])

            view: dict[str, Any] = {}
            for _ in range(CLAUDE_VIEW_ATTEMPTS):
                try:
                    before = version()
                    view = claude_budget_read()
                    if version() == before:
                        return view
                except sqlite3.Error:
                    # The file opened but its version could not be read (busy, or a hot journal
                    # this connection may not recover): the reads cannot be shown as one state.
                    view = view or claude_budget_read()
                    break
        # The ledger kept changing, or could not be checked, while it was read.
        view.update(ledger=None, daily=None, reconciliation=None, effective_remaining_micro_usd=0)
        view["effective_remaining_usd"] = f"{0:.6f}"
        # Any refusal the unchecked reads produced may itself come from mixed states.
        view["refusal"] = "LEDGER_BUSY"
        view["controls"].update(lifetime=None, calls_used=None, calls_remaining=None)
        return view

    def claude_budget_read() -> dict[str, Any]:
        """D-102: Claude's spending view (anthropic_runtime.budget_status, read-only) with the
        HR controls that apply, the calls an active Claude configuration has left, and the
        range its lifetime cap may be set within. Nothing is sent, recovered or changed."""

        controls = selector.claude_spending_controls()
        effective = apply_claude_controls(settings, controls)
        view = anthropic_runtime.budget_status(effective, environ=selector.environ)
        try:
            used = selector.claude_calls_used()
        except LedgerError:
            used = None
        limit = effective.anthropic_max_calls
        lifetime = None
        reconciliation = None
        try:
            ledger = BudgetLedger(anthropic_runtime.ledger_file(settings))
            ledger.verify()
            status = ledger.status()
            if status.profile_id == anthropic_profiles.LEDGER_PROFILE_ID:
                lifetime = {
                    "opening_usage_micro_usd": status.opening_usage,
                    "cap_micro_usd": status.cap,
                    "max_cap_micro_usd": claude_cap_ceiling(),
                    "committed_micro_usd": status.committed,
                }
                reconciliation = claude_reconciliation_view(ledger, status, time.time())
        except LedgerError:
            pass
        view["reconciliation"] = reconciliation
        view["controls"] = {
            "revision": controls.revision if controls is not None else None,
            "readable": controls is not None,
            "daily_cap_micro_usd": effective.anthropic_daily_cap_micro_usd,
            "daily_cap_range": list(CLAUDE_DAILY_CAP_RANGE),
            "daily_cap_default_micro_usd": settings.anthropic_daily_cap_micro_usd,
            "raise_requires": ["confirmation", "reconciled_within_one_day"],
            "daily_cap_source": "hr"
            if controls is not None and controls.daily_cap_micro_usd is not None
            else "environment",
            "max_calls": limit,
            "max_calls_range": list(CLAUDE_MAX_CALLS_RANGE),
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

    def claude_reconciliation_view(
        ledger: BudgetLedger, status: LedgerStatus, now: float
    ) -> dict[str, Any]:
        # B1 Phase A (read-only): the Claude ledger's accounting and its reconciliation windows,
        # from the ledger's own read methods (BudgetLedger(path), never BudgetLedger.open, so no
        # expired call is closed here). The GPT-OSS ledger is never opened. Content-free: counts,
        # micro-USD amounts, the key alias and times only.
        reconciled = ledger.last_reconciled_ms()
        closed = ledger.closed_calls_after(0)

        def moment(ms: float | None) -> str | None:
            if ms is None:
                return None
            return datetime.fromtimestamp(ms / 1000, UTC).isoformat(timespec="seconds")

        def within(seconds: int) -> bool:
            # The same rule the chat and paid gates apply, at this view's moment.
            return anthropic_runtime.reconciled_within(ledger, seconds, clock=lambda: now)

        chat = anthropic_runtime.CHAT_RECONCILE_SECONDS
        paid = anthropic_runtime.PAID_RECONCILE_SECONDS
        states = [call.state for call in closed]
        checks = [call.verification for call in closed]
        return {
            "key_alias": status.key_alias,
            "reconciled_at": moment(reconciled),
            # When chat (7 days) and a paid qualification or activation (1 day) stop being
            # allowed unless the ledger is reconciled again (D-099); None if never reconciled.
            "chat_deadline_at": None if reconciled is None else moment(reconciled + chat * 1000),
            "paid_deadline_at": None if reconciled is None else moment(reconciled + paid * 1000),
            "chat_fresh": within(chat),
            "paid_fresh": within(paid),
            "chat_window_seconds": chat,
            "paid_window_seconds": paid,
            # The ledger's estimate of the key's cumulative provider usage: the last reconciled
            # baseline plus what it charged since. A reconciliation compares the Console with it.
            "baseline_micro_usd": status.baseline,
            "local_charged_micro_usd": status.local_charged,
            "estimate_micro_usd": status.baseline + status.local_charged,
            "last_provider_usage_micro_usd": status.last_provider_usage,
            "open_reserved_micro_usd": status.open_reserved,
            "tolerance_micro_usd": RECONCILE_TOLERANCE_MICRO_USD,
            "calls": {
                "total": len(closed) + status.open_calls,
                "open": status.open_calls,
                "settled": states.count("settled"),
                "unsettled": states.count("unsettled"),
                "abandoned": states.count("abandoned"),
                "verified": checks.count("verified"),
                "quarantined": checks.count("quarantined"),
                "unverified": checks.count("unverified"),
                "charged_micro_usd": sum(call.charged_micro_usd or 0 for call in closed),
            },
        }

    def claude_cap_ceiling() -> int:
        # The lower of the D-102 lifetime ceiling and the owner-confirmed workspace limit
        # (D-107: HR's record when there is one, else the environment's attestation).
        return min(
            anthropic_runtime.LIFETIME_CEILING_MICRO_USD,
            anthropic_runtime.workspace_limit(settings),
        )

    budget_attempts: dict[str, list[float]] = {}
    # D-104 (QG L3): data access changes have their own count and their own message.
    policy_attempts: dict[str, list[float]] = {}

    def guard_budget(
        request: Request,
        profile: dict[str, Any],
        action: str,
        *,
        attempts: dict[str, list[float]] = budget_attempts,
        limited_code: str = "BUDGET_RATE_LIMITED",
    ) -> None:
        """Like a key change: the Origin header of an allowed page is required, and each
        administrator has a bounded number of spending changes and refreshes per window."""

        if not request.headers.get("origin"):
            audit(profile, action, "refused", code="ORIGIN_REQUIRED")
            raise _refusal(403, "ORIGIN_REQUIRED")
        now = time.monotonic()
        user = str(profile.get("user_id"))
        with attempts_lock:
            recent = [at for at in attempts.get(user, []) if now - at < CREDENTIAL_WINDOW_SECONDS]
            limited = len(recent) >= BUDGET_ATTEMPTS
            if not limited:
                recent.append(now)
            attempts[user] = recent
        if limited:
            audit(profile, action, "refused", code=limited_code)
            raise _refusal(429, limited_code)

    @router.put("/budget/controls")
    def put_spending_controls(
        body: SpendingControlsRequest, profile: Admin, request: Request
    ) -> dict[str, Any]:
        """The daily allowance per Singapore day (D-098: no US$1 ceiling) and the calls per
        activation (1 to 200). A raise of the daily allowance needs the amount confirmed and
        the key's own finite limit verified now. Spend and the call count are never reset."""

        action = "SPENDING_CONTROLS_CHANGED"
        guard_budget(request, profile, action)
        store = managed()
        if not valid_controls(body.daily_cap_micro_usd, body.max_calls):
            audit(profile, action, "refused", code="CONTROLS_INVALID")
            raise _refusal(400, "CONTROLS_INVALID")
        with selector.change_lock:
            recheck(request, profile, action)
            # The allowance in force now (unreadable controls read as none: any value raises).
            stored = selector.spending_controls()
            if stored is not None and stored.revision != body.expected_revision:
                audit(profile, action, "refused", code="CONTROLS_CONFLICT")
                raise _refusal(409, "CONTROLS_CONFLICT")
            current = apply_controls(settings, stored)
            if body.daily_cap_micro_usd > current.budget_daily_cap_micro_usd:
                if body.confirm_daily_cap_micro_usd != body.daily_cap_micro_usd:
                    audit(profile, action, "refused", code="DAILY_CONFIRMATION_REQUIRED")
                    raise _refusal(400, "DAILY_CONFIRMATION_REQUIRED")
                require_provider_limit(profile, action)
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

    def preflight_failures(names: tuple[str, ...]) -> list[str] | None:
        """Which of ``names`` fail in the free preflight (GET /key against the ledger; no
        inference, nothing changed), or None when OpenRouter or the ledger could not be
        checked at all."""

        try:
            report, _, _ = preflight(selector.controlled(), **selector.remote_options())
        except (ProfileConfigError, LedgerError):
            return None
        found = {check.name: check.ok for check in report.checks}
        if any(name not in found for name in names):
            return None
        return [name for name in names if not found[name]]

    def require_provider_limit(
        profile: dict[str, Any], action: str, also: tuple[str, ...] = ()
    ) -> list[str]:
        """D-098: more app spending authority only with a verified, finite key limit (one
        free preflight). Returns which of ``also`` failed in that same preflight."""

        failed = preflight_failures(PROVIDER_LIMIT_CHECKS + also)
        if failed is None:
            audit(profile, action, "refused", code="PROVIDER_CHECK_FAILED")
            raise _refusal(409, "PROVIDER_CHECK_FAILED")
        key = [name for name in failed if name in PROVIDER_LIMIT_CHECKS]
        if key:
            audit(profile, action, "refused", code="PROVIDER_LIMIT_REQUIRED:" + ",".join(key))
            raise _refusal(409, "PROVIDER_LIMIT_REQUIRED")
        return [name for name in failed if name in also]

    @router.put("/budget/lifetime-cap")
    def put_lifetime_cap(
        body: LifetimeCapRequest, profile: Admin, request: Request
    ) -> dict[str, Any]:
        """Set the ledger's lifetime cap at or above its opening provider usage (D-098: no
        US$1 allocation ceiling). A raise needs the same amount confirmed, the key's own
        finite limit verified and passing reconciliation checks; the ledger keeps every call,
        charge and earlier event."""

        action = "LIFETIME_CAP_CHANGED"
        guard_budget(request, profile, action)
        managed()  # a change is made only where it can be audited
        with selector.change_lock:
            recheck(request, profile, action)
            try:
                # D-099 (QG M-1/L-4): HR changes the GPT-OSS ledger only, never the Anthropic
                # one; its profile is read before the ledger is opened (and recovered).
                probe = BudgetLedger(ledger_file(settings))
                probe.verify()
                if probe.status().profile_id != OPENROUTER_PROFILE_ID:
                    raise LedgerError("LEDGER_PROFILE_MISMATCH", "not the OpenRouter ledger")
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
            # D-098 (F1): a change is decided on the cap the page showed; a raise must say
            # which, and any change is refused if the cap moved since (another HR change).
            if (raising or body.expected_cap_micro_usd is not None) and (
                body.expected_cap_micro_usd != status.cap
            ):
                audit(profile, action, "refused", code="CONTROLS_CONFLICT")
                raise _refusal(409, "CONTROLS_CONFLICT")
            if raising:
                if body.confirm_cap_micro_usd != cap:
                    audit(profile, action, "refused", code="CAP_CONFIRMATION_REQUIRED")
                    raise _refusal(400, "CAP_CONFIRMATION_REQUIRED")
                failed = require_provider_limit(profile, action, CAP_RAISE_CHECKS)
                if failed:
                    audit(
                        profile,
                        action,
                        "refused",
                        code="RECONCILIATION_REQUIRED:" + ",".join(failed),
                    )
                    raise _refusal(409, "RECONCILIATION_REQUIRED")
            if cap != status.cap:
                try:
                    # The cap this decision was made on is checked again inside the ledger's
                    # own write transaction: a change in between (the operator's script,
                    # another process) refuses this one; it is never overwritten.
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

    # --- D-102: Claude's HR spending controls and its lifetime ledger cap ---------------------

    def require_claude_raise(profile: dict[str, Any], action: str) -> None:
        """More Claude spending authority only when Claude is fully configured (D-099
        readiness) and its own ledger was reconciled with the Anthropic Console within the
        last day, with the breaker closed and no call open (read-only: never recovered here)."""

        code = anthropic_runtime.readiness(settings)
        if code is not None:
            audit(profile, action, "refused", code=code)
            raise _refusal(409, code, "CLAUDE_NOT_READY")
        try:
            ledger = BudgetLedger(anthropic_runtime.ledger_file(settings))
            ledger.verify()
            status = ledger.status()
            if status.profile_id != anthropic_profiles.LEDGER_PROFILE_ID:
                raise LedgerError("LEDGER_PROFILE_MISMATCH", "not the Anthropic ledger")
            fresh = anthropic_runtime.reconciled_within(
                ledger, anthropic_runtime.PAID_RECONCILE_SECONDS, clock=time.time
            )
        except LedgerError:
            audit(profile, action, "refused", code="LEDGER_UNAVAILABLE")
            raise _claude_refusal(409, "LEDGER_UNAVAILABLE") from None
        if not fresh or status.breaker_open or status.open_calls:
            audit(profile, action, "refused", code="RECONCILIATION_REQUIRED")
            raise _claude_refusal(409, "RECONCILIATION_REQUIRED")

    @router.put("/budget/claude/controls")
    def put_claude_spending_controls(
        body: ClaudeSpendingControlsRequest, profile: Admin, request: Request
    ) -> dict[str, Any]:
        """Claude's daily allowance per Singapore day (up to US$5.00) and calls per activation
        (1 to 20). A raise of either needs the new value confirmed and a recent
        reconciliation. Spend and the call count are never reset; GPT-OSS is never touched."""

        action = "CLAUDE_SPENDING_CONTROLS_CHANGED"
        guard_budget(request, profile, action)
        store = managed()
        if not valid_claude_controls(body.daily_cap_micro_usd, body.max_calls):
            audit(profile, action, "refused", code="CONTROLS_INVALID")
            raise _claude_refusal(400, "CONTROLS_INVALID")
        with selector.change_lock:
            recheck(request, profile, action)
            stored = selector.claude_spending_controls()
            if stored is not None and stored.revision != body.expected_revision:
                audit(profile, action, "refused", code="CONTROLS_CONFLICT")
                raise _claude_refusal(409, "CONTROLS_CONFLICT")
            # Unreadable controls read as no allowance and no calls: any value is then a raise.
            current = apply_claude_controls(settings, stored)
            current_calls = current.anthropic_max_calls if stored is not None else 0
            daily_raise = body.daily_cap_micro_usd > current.anthropic_daily_cap_micro_usd
            calls_raise = body.max_calls > current_calls
            if daily_raise and body.confirm_daily_cap_micro_usd != body.daily_cap_micro_usd:
                audit(profile, action, "refused", code="DAILY_CONFIRMATION_REQUIRED")
                raise _claude_refusal(400, "DAILY_CONFIRMATION_REQUIRED")
            # QG L1: more calls per activation is more spending authority too.
            if calls_raise and body.confirm_max_calls != body.max_calls:
                audit(profile, action, "refused", code="CALLS_CONFIRMATION_REQUIRED")
                raise _claude_refusal(400, "CALLS_CONFIRMATION_REQUIRED")
            if daily_raise or calls_raise:
                require_claude_raise(profile, action)
            try:
                revision = store.set_claude_spending_controls(
                    body.expected_revision,
                    body.daily_cap_micro_usd,
                    body.max_calls,
                    str(profile.get("user_id")),
                )
            except RevisionConflict:
                audit(profile, action, "refused", code="CONTROLS_CONFLICT")
                raise _claude_refusal(409, "CONTROLS_CONFLICT") from None
            audit(
                profile,
                action,
                "applied",
                code=f"DAILY_{body.daily_cap_micro_usd}_MICRO_USD_CALLS_{body.max_calls}",
                revision=revision,
            )
        selector.sync_controls()
        return budget_view()

    @router.put("/budget/claude/lifetime-cap")
    def put_claude_lifetime_cap(
        body: LifetimeCapRequest, profile: Admin, request: Request
    ) -> dict[str, Any]:
        """Set the Anthropic ledger's lifetime cap above its opening usage and at most the
        lower of US$30.00 and the attested workspace limit. A raise needs the amount
        confirmed, the cap the page showed, and a reconciliation within the last day; the ledger
        keeps every call and charge. The GPT-OSS ledger is never opened here."""

        action = "CLAUDE_LIFETIME_CAP_CHANGED"
        guard_budget(request, profile, action)
        managed()  # a change is made only where it can be audited
        with selector.change_lock:
            recheck(request, profile, action)
            try:
                ledger = anthropic_runtime.open_own(anthropic_runtime.ledger_file(settings))
                status = ledger.status()
            except LedgerError:
                audit(profile, action, "refused", code="LEDGER_UNAVAILABLE")
                raise _claude_refusal(409, "LEDGER_UNAVAILABLE") from None
            cap = body.cap_micro_usd
            raising = cap > status.cap
            # QG L2: a strictly lower cap only reduces authority, so it needs no attested
            # workspace limit (it never enables Claude: every call still needs readiness and
            # a cap within that limit). Any other value is checked against the ceiling too.
            lowering = status.opening_usage < cap < status.cap
            if not lowering and not status.opening_usage < cap <= claude_cap_ceiling():
                audit(profile, action, "refused", code="CAP_OUT_OF_RANGE")
                raise _claude_refusal(409, "CAP_OUT_OF_RANGE")
            if (raising or body.expected_cap_micro_usd is not None) and (
                body.expected_cap_micro_usd != status.cap
            ):
                audit(profile, action, "refused", code="CONTROLS_CONFLICT")
                raise _claude_refusal(409, "CONTROLS_CONFLICT")
            if raising:
                if body.confirm_cap_micro_usd != cap:
                    audit(profile, action, "refused", code="CAP_CONFIRMATION_REQUIRED")
                    raise _claude_refusal(400, "CAP_CONFIRMATION_REQUIRED")
                require_claude_raise(profile, action)
            if cap != status.cap:
                try:
                    # The operator's rule as well (the ceiling; a raise only after a
                    # reconciliation), then the cap this decision was made on, checked again
                    # inside the ledger's own write transaction.
                    anthropic_runtime.check_cap_change(ledger, cap, raising=raising)
                    ledger.set_cap(
                        cap,
                        allow_raise=raising,
                        confirm=cap if raising else None,
                        expected=status.cap,
                    )
                except LedgerError as error:
                    code = {
                        "CAP_CHANGED": "CONTROLS_CONFLICT",
                        "CAP_RAISE_REFUSED": "RECONCILIATION_REQUIRED",
                    }.get(error.code, "LEDGER_UNAVAILABLE")
                    audit(profile, action, "refused", code=code)
                    raise _claude_refusal(409, code) from None
                audit(
                    profile,
                    action,
                    "applied",
                    code=f"{'RAISED' if raising else 'LOWERED'}_TO_{cap}_MICRO_USD",
                )
        return budget_view()

    # --- D-110: HR reconciliation of the Claude ledger (claude_reconciliation.py) ----------

    reconciler = (
        reconciliation.Reconciler(
            lambda: Path(anthropic_runtime.ledger_file(settings)),
            reconciliation.Runs(store_file(settings)),
            lambda: float(settings.budget_settle_lag_seconds),
        )
        if selector.store is not None
        else None
    )
    # Tests replace the clocks through this handle.
    selector.reconciler = reconciler

    reconcile_status = {
        "INVALID_INPUT": 400,
        "SCOPE_UNCONFIRMED": 400,
        "USAGE_CONFIRMATION_REQUIRED": 400,
        "RUN_UNKNOWN": 404,
    }

    def reconcile_refusal(
        profile: dict[str, Any], action: str, refused: reconciliation.ReconcileRefused
    ) -> HTTPException:
        audit(profile, action, "refused", code=refused.code)
        # The page words every code itself; the facts are numbers, times and run ids only.
        return HTTPException(
            status_code=reconcile_status.get(refused.code, 409),
            detail={"code": refused.code, "message": "Nothing changed.", **refused.facts},
        )

    def session_of(request: Request) -> str:
        cookie = request.cookies.get(SESSION_COOKIE_NAME) or ""
        return hashlib.sha256(cookie.encode()).hexdigest()

    def reconciler_for() -> reconciliation.Reconciler:
        if reconciler is None:
            raise _refusal(409, "MODEL_MANAGEMENT_OFF")
        return reconciler

    @router.get("/budget/claude/reconciliation")
    def get_claude_reconciliation(profile: Admin) -> dict[str, Any]:
        """The runs, the owner's recorded prerequisite and any intent marker. Read-only: no
        ledger, run or marker is written here (D-110 F11)."""

        action = "CLAUDE_RECONCILIATION"
        try:
            return reconciler_for().listing()
        except reconciliation.ReconcileRefused as refused:
            raise reconcile_refusal(profile, action, refused) from None

    @router.post("/budget/claude/reconciliation/preview")
    def post_claude_reconciliation_preview(
        body: ReconciliationPreviewRequest, profile: Admin, request: Request
    ) -> dict[str, Any]:
        """What reconciling with this Console reading would do. Nothing is written but the
        preview itself, kept in this process for five minutes for this administrator."""

        action = "CLAUDE_RECONCILIATION"
        guard_budget(request, profile, action)
        recon = reconciler_for()
        with selector.change_lock:
            recheck(request, profile, action)
            try:
                reading = reconciliation.Reading(
                    usage_micro_usd=body.usage_micro_usd,
                    as_of_ms=reconciliation.parse_moment(body.as_of),
                    as_of_kind=body.as_of_kind,
                    viewed_at_ms=reconciliation.parse_moment(body.viewed_at),
                    scope_workspace=body.scope_workspace,
                    scope_only=body.scope_only,
                    scope_cumulative=body.scope_cumulative,
                )
                return recon.preview(
                    reading, actor=str(profile.get("user_id")), session=session_of(request)
                )
            except reconciliation.ReconcileRefused as refused:
                raise reconcile_refusal(profile, action, refused) from None

    @router.post("/budget/claude/reconciliation/apply")
    def post_claude_reconciliation_apply(
        body: ReconciliationApplyRequest, profile: Admin, request: Request
    ) -> dict[str, Any]:
        """Apply a stored preview with the existing BudgetLedger.reconcile (no release, no
        breaker reset). The lock, the intent and the ledger write all happen in this request's
        own worker thread, so a dropped connection cannot release the lock early."""

        action = "CLAUDE_RECONCILIATION"
        guard_budget(request, profile, action)
        recon = reconciler_for()
        with selector.change_lock:
            recheck(request, profile, action)
            try:
                result = recon.apply(
                    body.preview_id,
                    confirm_usage_micro_usd=body.confirm_usage_micro_usd,
                    scopes=(body.scope_workspace, body.scope_only, body.scope_cumulative),
                    actor=str(profile.get("user_id")),
                    role=str(profile.get("role")) if profile.get("role") else None,
                    session=session_of(request),
                )
            except reconciliation.ReconcileRefused as refused:
                raise reconcile_refusal(profile, action, refused) from None
        return {**result, "budget": budget_view()}

    @router.post("/budget/claude/reconciliation/runs/{run_id}/resolve")
    def post_claude_reconciliation_resolve(
        run_id: str, profile: Admin, request: Request
    ) -> dict[str, Any]:
        """Decide a run that did not finish, from the ledger's own events: applied only when
        its commit and its attribution are proven, failed only when no commit is proven,
        otherwise unresolved for the owner. The ledger is never written here."""

        action = "CLAUDE_RECONCILIATION"
        guard_budget(request, profile, action)
        if not re.fullmatch(r"[0-9a-f]{32}", run_id):
            raise reconcile_refusal(profile, action, reconciliation.ReconcileRefused("RUN_UNKNOWN"))
        recon = reconciler_for()
        with selector.change_lock:
            recheck(request, profile, action)
            try:
                result = recon.resolve(
                    run_id,
                    actor=str(profile.get("user_id")),
                    role=str(profile.get("role")) if profile.get("role") else None,
                )
            except reconciliation.ReconcileRefused as refused:
                raise reconcile_refusal(profile, action, refused) from None
        return {**result, "budget": budget_view()}

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

    # --- D-107: Claude's provider setup by HR (no decision or attestation settings) --------

    # The last free workspace read in this process, for the key it was made with (process-local
    # key marker, never shown). Enabling needs a read with the key now in use, within the hour.
    workspace_reads: dict[str, Any] = {}
    workspace_lock = threading.Lock()
    enable_attempts: dict[str, list[float]] = {}

    def current_read() -> dict[str, Any] | None:
        with workspace_lock:
            read = dict(workspace_reads)
        if not read or time.time() - float(read["at"]) > WORKSPACE_READ_SECONDS:
            return None
        key, _, _ = anthropic_runtime.resolve_key(selector.environ)
        if read["key"] != key_sources.identity(key):
            return None  # read with another key
        return read

    def anthropic_setup_view() -> dict[str, Any]:
        # What HR needs for Claude's setup (no key, no key marker). ``record`` is HR's stored
        # setup; ``source`` says what decides now; the limit is owner-confirmed, never read.
        try:
            record = selector.store.anthropic_enablement() if selector.store else None
            readable = True
        except Exception:
            record, readable = None, False
        read = current_read()
        legacy = settings.anthropic_decision == anthropic_profiles.DECISION_ID
        return {
            "managed": selector.store is not None,
            "readable": readable,
            "source": "hr" if record is not None else ("environment" if legacy else "none"),
            "enabled": anthropic_runtime.configured(settings),
            "readiness": anthropic_runtime.readiness(settings),
            "local_deployment": anthropic_runtime.local_deployment(settings),
            "record": None
            if record is None
            else {
                "revision": record.revision,
                "enabled": record.enabled,
                "workspace_id": record.workspace_id,
                "workspace_limit_micro_usd": record.workspace_limit_micro_usd,
                "workspace_limit_basis": "owner_confirmed",
                "confirmations": sorted(record.confirmations),
                "changed_at": record.changed_at,
                "changed_by": record.changed_by,
            },
            "workspace_read": None
            if read is None
            else {
                "workspace_id": read["workspace_id"],
                "at": datetime.fromtimestamp(float(read["at"]), UTC).isoformat(timespec="seconds"),
            },
            "confirmations_required": sorted(anthropic_runtime.OWNER_ATTESTATIONS),
            "workspace_limit_max_micro_usd": anthropic_runtime.LIFETIME_CEILING_MICRO_USD,
        }

    @router.post("/provider/anthropic/workspace-read")
    def read_anthropic_workspace(profile: Admin, request: Request) -> dict[str, Any]:
        # The free models read with the key in force (D-106 order): which workspace it reports.
        # No inference, no case data, no ledger. Rate limited like a key change.
        action = "ANTHROPIC_WORKSPACE_READ"
        guard_change(request, profile, action)
        result = anthropic_runtime.read_workspace(settings, **selector.claude_options())
        if result["outcome"] == "passed":
            with workspace_lock:
                workspace_reads.clear()
                workspace_reads.update(
                    key=result["key"], workspace_id=result["workspace_id"], at=time.time()
                )
        audit(profile, action, result["outcome"], profile_id="anthropic", code=result["code"])
        return {
            "outcome": result["outcome"],
            "code": result["code"],
            "workspace_id": result["workspace_id"],
            "setup": anthropic_setup_view(),
        }

    def fresh_claude_ledger(
        body: AnthropicEnablementRequest, limit: int
    ) -> tuple[str | None, tuple[int, int, str] | None]:
        # D-118 S4: how a fresh deployment's Claude ledger opens, decided before anything is
        # stored: only where none exists, and never at zero unless the owner confirmed a new
        # workspace (the free read named it: never the default workspace). Returns a refusal
        # code, or the (cap, opening, basis) to create once the setup record is stored (QG F4).
        if anthropic_runtime.ledger_file(settings).exists():
            return (None if body.opening is None else "LEDGER_EXISTS"), None
        cap = min(anthropic_runtime.LIFETIME_CEILING_MICRO_USD, limit)
        if body.opening == "new_workspace" and body.opening_usage_micro_usd is None:
            opening, basis = 0, "new_workspace_confirmed"
        elif body.opening == "console_usage" and type(body.opening_usage_micro_usd) is int:
            opening, basis = body.opening_usage_micro_usd, "console_usage_entered"
        else:
            return ("OPENING_REQUIRED" if body.opening is None else "OPENING_INVALID"), None
        if not 0 <= opening < cap:
            return "OPENING_INVALID", None
        return None, (cap, opening, basis)

    @router.put("/provider/anthropic")
    def put_anthropic_enablement(
        body: AnthropicEnablementRequest, profile: Admin, request: Request
    ) -> dict[str, Any]:
        # Enable Claude for verified synthetic cases (the workspace the key reported, the
        # owner-confirmed monthly limit, the four confirmations) or disable it. HR only,
        # compare-and-set, re-checked inside the change, stored with its audit row.
        action = "ANTHROPIC_ENABLED" if body.enabled else "ANTHROPIC_DISABLED"
        guard_budget(
            request, profile, action, attempts=enable_attempts, limited_code="BUDGET_RATE_LIMITED"
        )
        store = managed()

        def refuse(code: str, status: int = 409) -> HTTPException:
            audit(profile, action, "refused", profile_id="anthropic", code=code)
            return _refusal(status, code)

        with selector.change_lock:
            recheck(request, profile, action)
            try:
                record = store.anthropic_enablement()
            except Exception:
                raise refuse("ENABLEMENT_UNAVAILABLE") from None
            current = record.revision if record is not None else 0
            if current != body.expected_revision:
                raise refuse("ENABLEMENT_CONFLICT")
            fresh: tuple[int, int, str] | None = None
            if body.enabled:
                if not anthropic_runtime.local_deployment(settings):
                    raise refuse("NOT_DEVELOPMENT_ENVIRONMENT")
                limit = body.workspace_limit_micro_usd
                if (
                    frozenset(body.confirmations) != anthropic_runtime.OWNER_ATTESTATIONS
                    or len(body.confirmations) != len(anthropic_runtime.OWNER_ATTESTATIONS)
                    or type(limit) is not int
                    or not 1 <= limit <= anthropic_runtime.LIFETIME_CEILING_MICRO_USD
                ):
                    raise refuse("ENABLEMENT_INVALID", 400)
                read = current_read()
                if read is None or read["workspace_id"] != body.workspace_id:
                    raise refuse("WORKSPACE_NOT_READ")
                if record is not None and record.workspace_id != body.workspace_id:
                    raise refuse("WORKSPACE_CHANGE_REFUSED")
                environment = settings.anthropic_workspace_id
                if environment and environment != body.workspace_id:
                    raise refuse("WORKSPACE_MISMATCH")
                workspace, confirmations = body.workspace_id, anthropic_runtime.OWNER_ATTESTATIONS
                code, fresh = fresh_claude_ledger(body, limit)
                if code is not None:
                    raise refuse(code, 400 if code == "OPENING_INVALID" else 409)
            elif record is not None:
                if not record.enabled:
                    raise refuse("NOT_ENABLED")
                workspace, limit = record.workspace_id, record.workspace_limit_micro_usd
                confirmations = record.confirmations
            else:
                # Claude configured on the server (D-099): disabling stores HR's record, switched
                # off, with the server's workspace and limit, so it decides from now on.
                workspace = settings.anthropic_workspace_id
                limit = settings.anthropic_workspace_limit_micro_usd
                if (
                    settings.anthropic_decision != anthropic_profiles.DECISION_ID
                    or not anthropic_runtime.valid_workspace(workspace)
                    or not 1 <= limit <= anthropic_runtime.LIFETIME_CEILING_MICRO_USD
                ):
                    raise refuse("NOT_ENABLED")
                confirmations = anthropic_runtime.attestations(settings)
            try:
                store.set_anthropic_enablement(
                    body.expected_revision,
                    enabled=body.enabled,
                    workspace_id=workspace,
                    workspace_limit_micro_usd=limit,
                    confirmations=confirmations,
                    by=str(profile.get("user_id")),
                    role=str(profile.get("role")) if profile.get("role") else None,
                )
            except RevisionConflict:
                raise refuse("ENABLEMENT_CONFLICT") from None
            if body.enabled and fresh is not None:
                # After the record is stored, so a refused change never leaves a ledger behind.
                # If this fails the record stays enabled with no ledger: enabling again with the
                # opening creates it (nothing paid can run without a ledger).
                cap, opening, basis = fresh
                try:
                    BudgetLedger.initialise(
                        anthropic_runtime.ledger_file(settings),
                        cap_micro_usd=cap,
                        opening_usage_micro_usd=opening,
                        key_alias="key-01",
                        profile_id=anthropic_profiles.LEDGER_PROFILE_ID,
                        opening_basis=basis,
                    )
                except LedgerError as error:
                    raise refuse(error.code) from None
        return anthropic_setup_view()

    @router.get("/data-access")
    def get_data_access(profile: Admin) -> dict[str, Any]:
        return data_access_view()

    @router.put("/data-access")
    def put_data_access(
        body: DataAccessRequest, profile: Admin, request: Request
    ) -> dict[str, Any]:
        # Restrict AI to verified synthetic cases. External models stay restricted (locked);
        # a local or IT-configured model may answer every authorised case only with the change
        # confirmed. Compare-and-set on the policy's revision, the capability re-checked inside
        # the change, every change and refusal audited with the old and new setting as a code.
        action = "DATA_ACCESS_POLICY_CHANGED"
        guard_budget(
            request,
            profile,
            action,
            attempts=policy_attempts,
            limited_code="DATA_ACCESS_RATE_LIMITED",
        )
        store = managed()
        if not body.restrict_external:
            audit(profile, action, "refused", code="EXTERNAL_DATA_POLICY_LOCKED")
            raise _refusal(409, "EXTERNAL_DATA_POLICY_LOCKED")
        with selector.change_lock:
            recheck(request, profile, action)
            stored = selector.data_access_policy()
            if stored is None:
                audit(profile, action, "refused", code="DATA_ACCESS_POLICY_UNAVAILABLE")
                raise _refusal(409, "DATA_ACCESS_POLICY_UNAVAILABLE")
            if stored.revision != body.expected_revision:
                audit(profile, action, "refused", code="DATA_ACCESS_POLICY_CONFLICT")
                raise _refusal(409, "DATA_ACCESS_POLICY_CONFLICT")
            widening = stored.local_restricted and not body.restrict_local
            if widening and not body.confirm_widen:
                audit(profile, action, "refused", code="WIDEN_CONFIRMATION_REQUIRED")
                raise _refusal(400, "WIDEN_CONFIRMATION_REQUIRED")
            # QG L4: the policy and its audit row are written in one transaction.
            try:
                store.set_data_access_policy(
                    body.expected_revision,
                    body.restrict_local,
                    str(profile.get("user_id")),
                    role=str(profile.get("role")) if profile.get("role") else None,
                    action=action,
                )
            except RevisionConflict:
                audit(profile, action, "refused", code="DATA_ACCESS_POLICY_CONFLICT")
                raise _refusal(409, "DATA_ACCESS_POLICY_CONFLICT") from None
        return data_access_view()

    # --- recovery centre ------------------------------------------------------------------

    recovery_attempts: dict[str, list[float]] = {}

    def recovery_view(profile: dict[str, Any]) -> dict[str, Any]:
        """Every current problem, from the same views this page already shows. Read-only."""

        listing: dict[str, Any] | None = None
        listing_error: str | None = None
        if reconciler is not None:
            try:
                listing = reconciler.listing()
            except reconciliation.ReconcileRefused as refused:
                listing_error = refused.code
        view = recovery.diagnose(
            overview(),
            listing=listing,
            listing_error=listing_error,
            now=datetime.now(UTC),
            hr_allowed=CAPABILITY in (profile.get("capabilities") or []),
        )
        requests = selector.store.recovery_requests() if selector.store else []
        present = recovery.present_codes(view)
        view["requests"] = [
            {**item, "problem_present": item["problem_code"] in present} for item in requests
        ]
        return view

    def recovery_refused(
        profile: dict[str, Any], action: str, code: str, status: int = 409
    ) -> HTTPException:
        audit(profile, action, "refused", code=code)
        return _refusal(status, code)

    @router.get("/recovery")
    def get_recovery(profile: Admin) -> dict[str, Any]:
        return recovery_view(profile)

    @router.post("/recovery/requests")
    def post_recovery_request(
        body: RecoveryRequestBody, profile: Admin, request: Request
    ) -> dict[str, Any]:
        """Ask the owner to act on a problem only the owner may fix. The request carries the
        server's own evidence for it, never figures from the browser. Nothing else changes."""

        action = "RECOVERY_REQUESTED"
        guard_budget(
            request, profile, action, attempts=recovery_attempts,
            limited_code="RECOVERY_RATE_LIMITED",
        )
        store = managed()
        note = (body.note or "").strip() or None
        if note is not None and (_NOTE_REFUSED.search(note) or not note.isprintable()):
            raise recovery_refused(profile, action, "RECOVERY_NOTE_REFUSED", 422)
        with selector.change_lock:
            recheck(request, profile, action)
            view = recovery_view(profile)
            if body.problem_code not in recovery.present_codes(view):
                raise recovery_refused(profile, action, "RECOVERY_PROBLEM_NOT_PRESENT")
            if body.problem_code not in recovery.OWNER_PROBLEMS:
                raise recovery_refused(profile, action, "RECOVERY_PROBLEM_NOT_OWNER")
            try:
                store.open_recovery_request(
                    body.problem_code,
                    recovery.evidence_snapshot(view, body.problem_code),
                    note,
                    str(profile.get("user_id")),
                    role=str(profile.get("role")) if profile.get("role") else None,
                )
            except RecoveryRequestRefused as refused:
                raise recovery_refused(profile, action, refused.code) from None
            return recovery_view(profile)

    @router.post("/recovery/requests/{request_id}/close")
    def post_recovery_close(
        request_id: str, body: RecoveryCloseBody, profile: Admin, request: Request
    ) -> dict[str, Any]:
        """Withdraw a request, or mark it resolved: only once the server no longer reports
        its problem (the recovery is verified here, not taken from the browser)."""

        action = "RECOVERY_RESOLVED" if body.status == "resolved" else "RECOVERY_WITHDRAWN"
        guard_budget(
            request, profile, action, attempts=recovery_attempts,
            limited_code="RECOVERY_RATE_LIMITED",
        )
        store = managed()
        if not re.fullmatch(r"[0-9a-f]{32}", request_id):
            raise recovery_refused(profile, action, "RECOVERY_REQUEST_UNKNOWN", 404)
        with selector.change_lock:
            recheck(request, profile, action)
            existing = store.recovery_request(request_id)
            if existing is None:
                raise recovery_refused(profile, action, "RECOVERY_REQUEST_UNKNOWN", 404)
            if body.status == "resolved":
                view = recovery_view(profile)
                code = existing["problem_code"]
                # Resolved only when a full diagnosis no longer reports it: a part that could
                # not be read (an unreadable ledger or run store) proves nothing (QG F4).
                if code in recovery.present_codes(view) or not recovery.problem_covered(
                    view, code
                ):
                    raise recovery_refused(profile, action, "RECOVERY_PROBLEM_STILL_PRESENT")
            try:
                store.close_recovery_request(
                    request_id,
                    body.status,
                    str(profile.get("user_id")),
                    role=str(profile.get("role")) if profile.get("role") else None,
                )
            except RecoveryRequestRefused as refused:
                raise recovery_refused(profile, action, refused.code) from None
            return recovery_view(profile)

    # --- D-118: paid-model sessions, the conservative-only resume and the setup view --------

    def provider_ledger(provider: str) -> Path:
        if provider == "anthropic":
            return anthropic_runtime.ledger_file(settings)
        return ledger_file(settings)

    def ledger_profile_of(path: Path) -> str:
        probe = BudgetLedger(path)
        probe.verify()
        return probe.status().profile_id

    def session_view(provider: str) -> dict[str, Any]:
        """One provider's ledger state, open session and breaker, read-only (never recovered,
        never changed). Amounts are micro-USD integers."""

        expected = (
            anthropic_profiles.LEDGER_PROFILE_ID
            if provider == "anthropic"
            else OPENROUTER_PROFILE_ID
        )
        view: dict[str, Any] = {
            "provider": provider,
            "ledger": "missing",
            "code": None,
            "accounting_mode": None,
            "origin": None,
            "opening_basis": None,
            "allowance_default_micro_usd": SESSION_DEFAULT_MICRO_USD,
            "allowance_max_micro_usd": SESSION_MAX_MICRO_USD,
            "session": None,
            "breaker_open": False,
            "breaker_code": None,
            "resumable": False,
            "resume_blocker": None,
        }
        path = provider_ledger(provider)
        if not path.exists():
            return view
        try:
            ledger = BudgetLedger(path)
            ledger.verify()
            status = ledger.status()
            if status.profile_id != expected:
                raise LedgerError("LEDGER_PROFILE_MISMATCH", "not this provider's ledger")
            profile = ledger.profile()
            session = ledger.session()
            blocker = (
                ledger.resume_blocker(status.breaker_code)
                if status.breaker_open and status.breaker_code
                else None
            )
        except LedgerError as error:
            view["ledger"] = (
                "migration_required" if error.code == "LEDGER_MIGRATION_REQUIRED" else "unavailable"
            )
            view["code"] = error.code
            return view
        view.update(
            ledger="ready",
            accounting_mode=profile.accounting_mode,
            origin=profile.origin,
            opening_basis=profile.opening_basis,
            breaker_open=status.breaker_open,
            breaker_code=status.breaker_code,
            resumable=status.breaker_open and blocker is None,
            resume_blocker=blocker,
        )
        if session is not None:
            started = datetime.fromtimestamp(session.created_at / 1000, UTC)
            view["session"] = {
                "session_id": session.session_id,
                "revision": session.revision,
                "allowance_micro_usd": session.allowance,
                "settled_micro_usd": session.settled,
                "held_micro_usd": session.open_reserved,
                "committed_micro_usd": session.committed,
                "remaining_micro_usd": session.remaining,
                "calls": session.calls,
                "chat_calls": session.chat_calls,
                "started_at": started.isoformat().replace("+00:00", "Z"),
            }
        return view

    def setup_blockers(view: dict[str, Any]) -> list[dict[str, str]]:
        """The exceptions a guided setup shows: one closed code and who acts. Routine use has
        none; reconciliation and the P1 record are never among them (D-118)."""

        found: list[dict[str, str]] = []
        anthropic = view["provider"] == "anthropic"
        if view["ledger"] == "missing":
            action = "ENABLE_CLAUDE" if anthropic else "TEST_CONNECTION"
            found.append({"code": "LEDGER_CREATED_AT_SETUP", "who": "hr", "action": action})
        elif view["ledger"] == "migration_required":
            found.append({"code": "LEDGER_MIGRATION_REQUIRED", "who": "owner", "action": "OWNER"})
        elif view["ledger"] == "unavailable":
            code = view["code"] or "LEDGER_UNAVAILABLE"
            found.append({"code": code, "who": "owner", "action": "OWNER"})
        if view["breaker_open"]:
            found.append(
                {
                    "code": f"BREAKER_OPEN:{view['breaker_code']}",
                    "who": "hr" if view["resumable"] else "owner",
                    "action": "RESUME" if view["resumable"] else "OWNER",
                }
            )
        session = view["session"]
        if session is not None and session["remaining_micro_usd"] <= 0:
            found.append({"code": "SESSION_ALLOWANCE_USED", "who": "hr", "action": "NEW_SESSION"})
        return found

    def provider_setup(provider: str) -> dict[str, Any]:
        view = session_view(provider)
        view["blockers"] = setup_blockers(view)
        return view

    @router.get("/setup")
    def get_setup(profile: Admin) -> dict[str, Any]:
        return {"providers": {p: provider_setup(p) for p in ("anthropic", "openrouter")}}

    def session_change(
        provider: str,
        profile: dict[str, Any],
        request: Request,
        action: str,
        change: Callable[[BudgetLedger], Any],
    ) -> dict[str, Any]:
        guard_budget(request, profile, action)
        with selector.change_lock:
            recheck(request, profile, action)
            path = provider_ledger(provider)
            try:
                if provider == "anthropic":
                    ledger = anthropic_runtime.open_own(path)
                else:
                    if ledger_profile_of(path) != OPENROUTER_PROFILE_ID:
                        raise LedgerError("LEDGER_PROFILE_MISMATCH", "not the OpenRouter ledger")
                    ledger = BudgetLedger.open(path)
                change(ledger)
            except LedgerError as error:
                audit(profile, action, "refused", profile_id=provider, code=error.code)
                raise _refusal(409, error.code) from None
        audit(profile, action, "succeeded", profile_id=provider)
        return provider_setup(provider)

    @router.post("/session/start")
    def start_session(
        body: SessionStartRequest, profile: Admin, request: Request
    ) -> dict[str, Any]:
        def start(ledger: BudgetLedger) -> None:
            ledger.start_session(
                body.allowance_micro_usd, expected_session_id=body.expected_session_id
            )

        return session_change(body.provider, profile, request, "PAID_SESSION_STARTED", start)

    @router.put("/session/allowance")
    def put_session_allowance(
        body: SessionAllowanceRequest, profile: Admin, request: Request
    ) -> dict[str, Any]:
        def change(ledger: BudgetLedger) -> None:
            ledger.set_session_allowance(
                body.allowance_micro_usd, expected_revision=body.expected_revision
            )

        action = "PAID_SESSION_ALLOWANCE_CHANGED"
        return session_change(body.provider, profile, request, action, change)

    @router.post("/budget/resume")
    def resume_breaker(
        body: BreakerResumeRequest, profile: Admin, request: Request
    ) -> dict[str, Any]:
        def resume(ledger: BudgetLedger) -> None:
            if body.provider == "anthropic":
                # In-band verification first (free, no request), so every closed call is
                # either verified or judged by the proof.
                anthropic_runtime.verify_calls(ledger)
            ledger.resume_breaker(body.code)

        return session_change(body.provider, profile, request, "BREAKER_RESUMED", resume)

    return router
