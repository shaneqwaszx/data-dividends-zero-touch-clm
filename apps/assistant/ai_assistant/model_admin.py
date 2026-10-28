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

import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import anyio
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StrictInt

from . import key_sources
from .budget import (
    DEFAULT_DAILY_CAP_MICRO_USD,
    MAX_MICRO_USD,
    BudgetedChatModel,
    BudgetLedger,
    LedgerError,
)
from .clm_client import SESSION_COOKIE_NAME, ClmBackendClient, ClmBackendError
from .config import AiAssistantSettings
from .llm import ChatModel, OpenAICompatibleChatModel
from .model_admin_store import (
    DAILY_CAP_MAX_MICRO_USD,
    MAX_CALLS_RANGE,
    Activation,
    Choice,
    ModelAdminStore,
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
SYSTEM_ACTOR = "system"
# D-098: the stored "no model" state after a GPT-OSS configuration stopped being usable (never
# a profile id in the catalogue, so it can never be activated or rolled back to).
UNAVAILABLE_ID = "ai_unavailable"
REMOTE_PROFILE_IDS = frozenset({OPENROUTER_PROFILE_ID, OPENROUTER_FAST_PROFILE_ID})
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
    "CREDENTIAL_INVALID": "That is not an OpenRouter API key. Nothing was saved.",
    "CREDENTIAL_ENVIRONMENT_MANAGED": (
        "The OpenRouter key is set on the server (environment or .env) and cannot be changed here."
    ),
    "CREDENTIAL_NOT_HR_MANAGED": "There is no key entered here to clear.",
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
        # D-098: how many qualification runs had finished when the active model was last
        # checked (None: never), so a newly finished run is noticed by every process.
        self._finished: int | None = None
        # D-098 (F2): stored reverts whose audit write failed, recorded once writes work.
        self._pending_audits: list[dict[str, Any]] = []
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
            if entry is not None and entry.source == "code" and self._paid_call_uncertain():
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

    def _paid_call_uncertain(self) -> bool:
        """A remote call is still open, or one was abandoned (read-only ledger check; an
        unreadable ledger is treated as uncertain)."""

        try:
            ledger = BudgetLedger(ledger_file(self.settings))
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
            undo = self.store.activate(
                revision, previous or self.baseline_choice(), _last_good(before), by
            )
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


# --- D-098: what a qualification outcome means, and which run makes a profile eligible -------

# Preflight checks whose failure means spend is not accounted for: an operator reconciles.
_BILLING_CHECKS = frozenset(
    {
        "ledger.breaker_closed_no_open_calls",
        "ledger.usage_reconciled",
        "ledger.earlier_calls_verified",
        "ledger.healthy",
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


def diagnose(item: dict[str, Any]) -> Diagnosis:
    """Classify one stored run from its status, code and content-free summary."""

    status, code = item.get("status"), str(item.get("code") or "")
    summary = item.get("summary") or {}
    if status == "running":
        return Diagnosis("running", "RUNNING", "WAIT")
    if status == "passed":
        return Diagnosis("passed", "PASSED", "NONE")
    if status == "cancelled":
        return Diagnosis("cancelled", "CANCELLED", "RUN_AGAIN", retryable=True)
    if code == "INTERRUPTED_BILLING_UNCERTAIN":
        return Diagnosis("billing_uncertain", code, "ESCALATE_OPERATOR")
    if code in _TECHNICAL_ERRORS:
        return Diagnosis("technical", code, "RUN_AGAIN", retryable=True)
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
    g7 = (gates.get("G-7") or {}).get("value") or {}
    if failed("G-7"):
        cut_short = g7.get("cut_short_rate") if isinstance(g7, dict) else None
        if isinstance(cut_short, int | float) and cut_short > 0:
            return Diagnosis("quality", "ANSWERS_CUT_SHORT", "ESCALATE_IT", supersedes_pass=True)
        return Diagnosis(
            "configuration", "CAPACITY_NOT_VERIFIED", "ESCALATE_IT", supersedes_pass=True
        )
    return Diagnosis("technical", "UNKNOWN", "RUN_AGAIN", retryable=True)


def eligible_run(
    store: ModelAdminStore, profile_id: str, fingerprint: str, basis: str
) -> tuple[dict[str, Any] | None, str | None]:
    """The run that lets this configuration be activated (D-098 decision 6a): its newest
    passing run for the current fingerprint and answer code, unless a genuine quality failure
    came after it. Technical, budget, configuration, billing and cancelled outcomes never
    take a pass away. Returns (run, None), or (None, the blocker code)."""

    for item in store.qualifications_for(profile_id):
        if item["fingerprint"] != fingerprint or item["basis"] != basis:
            continue
        if item["status"] == "passed":
            return item, None
        if item["status"] != "running" and diagnose(item).supersedes_pass:
            return None, "QUALIFICATION_SUPERSEDED"
    return None, "NOT_QUALIFIED"


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
            "diagnosis": diagnose(item).view(),
        }

    def readiness(entry: CatalogueEntry, blocker: str | None) -> list[str]:
        if entry.profile_id == BASELINE_ID:
            return (
                [] if entry.status == "selectable" else [entry.reason or "PROFILE_NOT_SELECTABLE"]
            )
        if entry.status != "selectable":
            return [entry.reason or "PROFILE_NOT_SELECTABLE"]
        return [blocker] if blocker else []

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
            profiles.append(
                {
                    **entry.view(),
                    "active": entry.profile_id == active.profile_id,
                    "connection_test": store.connection_test(entry.profile_id) if store else None,
                    "qualification": qualification_view(latest, entry, basis),
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
            "budget": budget_view() if settings.local_api_test_decision else None,
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
        selector.revalidate()

    def paid_estimate(entry: CatalogueEntry) -> dict[str, Any] | None:
        """D-098: what a paid qualification of this remote configuration may spend, against
        what the strictest applicable limit leaves (read-only; None for a local model)."""

        if entry.source != "code" or entry.status != "selectable":
            return None
        manifest = qualification_manifest(settings)
        try:
            view = budget_status(
                entry.settings_for(selector.controlled()), environ=selector.environ
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
        return _refusal(status, code)

    @router.post("/{profile_id}/qualifications", status_code=202)
    def post_qualification(
        profile_id: str, profile: Admin, body: QualificationRequest | None = None
    ) -> dict[str, Any]:
        store = managed()
        entry = entry_for(load_catalogue(settings), profile_id, profile, "QUALIFICATION_STARTED")
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
                if refusal.startswith("BREAKER_OPEN") or refusal == "LEDGER_UNAVAILABLE":
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
