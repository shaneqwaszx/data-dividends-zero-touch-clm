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
allowance (at most US$1.00 per Singapore day) and the calls per activation (1 to 200), stored
in the model state database (compare-and-set, every process reads them per request, applied to
the active model without a restart or a new activation, its call count kept); the ledger's
lifetime cap, from the key's opening provider usage up to US$1.00 above it (a raise needs the
amount confirmed and the existing reconciliation checks against OpenRouter's reported usage);
and a read-only refresh of the key's OpenRouter limit. Spend, calls and ledger history are
never reset, no ledger is created, and neither the key nor its OpenRouter limit is changed.

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
from .budget import BudgetedChatModel, BudgetLedger, LedgerError
from .clm_client import SESSION_COOKIE_NAME, ClmBackendClient, ClmBackendError
from .config import AiAssistantSettings
from .llm import ChatModel, OpenAICompatibleChatModel, micro_usd
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
from .model_profiles import ProfileConfigError
from .model_qualification import connection_test, qualification_basis, quality_state
from .remote_checks import ALLOCATION_LIMIT_USD
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
# The lifetime cap may be set from the ledger's opening provider usage up to this much above
# it (the D-092 allocation the preflight's ledger.cap_within_allocation check also enforces).
LIFETIME_ALLOCATION_MICRO_USD = micro_usd(ALLOCATION_LIMIT_USD)
# Reconciliation checks a lifetime cap increase needs (remote_checks.check_ledger).
CAP_RAISE_CHECKS = ("ledger.breaker_closed_no_open_calls", "ledger.usage_reconciled")

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
        "The daily limit must be US$0.00 to US$1.00 and the call limit 1 to 200. Nothing changed."
    ),
    "CONTROLS_CONFLICT": "The spending limits changed since this view. Refresh and try again.",
    "BUDGET_RATE_LIMITED": "Too many spending changes. Wait a few minutes and try again.",
    "LEDGER_UNAVAILABLE": "The spending ledger is missing or not usable. Nothing changed.",
    "CAP_OUT_OF_RANGE": (
        "The lifetime limit must stay between the key's opening usage and US$1.00 above it."
    ),
    "CAP_CONFIRMATION_REQUIRED": "Confirm the new lifetime limit to raise it. Nothing changed.",
    "RECONCILIATION_REQUIRED": (
        "The ledger must be reconciled with OpenRouter (no open call, no stop, usage accounted"
        " for) before the lifetime limit can be raised. Nothing changed."
    ),
    "PROVIDER_CHECK_FAILED": "The OpenRouter key could not be checked. Nothing changed.",
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
            active, problem = self._build_stored(stored)
            if active is not None:
                return active
            try:
                revision = self.store.activate(
                    stored.revision,
                    self.baseline_choice(),
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
            return self._baseline(revision, reverted=problem)
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


class LifetimeCapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cap_micro_usd: StrictInt
    # A raise needs the same amount again (the HR confirmation step).
    confirm_cap_micro_usd: StrictInt | None = None


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
            profiles.append(
                {
                    **entry.view(),
                    "active": entry.profile_id == active.profile_id,
                    "connection_test": store.connection_test(entry.profile_id) if store else None,
                    "qualification": qualification_view(latest, entry, basis),
                    "activation_blockers": readiness(entry, latest, basis),
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
            "revision": active.revision if selector.managed else 0,
            "active": {
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

    @router.post("/{profile_id}/qualifications", status_code=202)
    def post_qualification(profile_id: str, profile: Admin) -> dict[str, Any]:
        store = managed()
        entry = entry_for(load_catalogue(settings), profile_id, profile, "QUALIFICATION_STARTED")
        # The same checks the qualification process applies, before anything starts.
        if entry.source == "code":
            # D-094: a paid run, so only the configured, counted question manifest.
            if qualification_manifest(settings) is None:
                audit(
                    profile,
                    "QUALIFICATION_STARTED",
                    "refused",
                    profile_id=entry.profile_id,
                    fingerprint=entry.fingerprint,
                    code="REMOTE_MANIFEST_MISSING",
                )
                raise _refusal(409, "REMOTE_MANIFEST_MISSING")
        else:
            adapter_for(entry, profile, "QUALIFICATION_STARTED", loopback=True)
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
            previous = Choice(
                stored.active_profile_id,
                stored.active_fingerprint,
                stored.active_qualification_id,
                stored.active_prompt_limit,
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
                "max_cap_micro_usd": status.opening_usage + LIFETIME_ALLOCATION_MICRO_USD,
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
        """The daily allowance (US$0 to US$1.00 per Singapore day) and the calls per
        activation (1 to 200). Spend and the activation's call count are never reset."""

        action = "SPENDING_CONTROLS_CHANGED"
        guard_budget(request, profile, action)
        store = managed()
        if not valid_controls(body.daily_cap_micro_usd, body.max_calls):
            audit(profile, action, "refused", code="CONTROLS_INVALID")
            raise _refusal(400, "CONTROLS_INVALID")
        with selector.change_lock:
            recheck(request, profile, action)
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

    def reconciliation_failures() -> list[str] | None:
        """The existing reconciliation checks (``remote_checks.check_ledger`` inside the free
        preflight: GET /key against the ledger; no inference, nothing changed). The failed
        checks, or None when OpenRouter or the ledger could not be checked at all."""

        report, _, _ = preflight(selector.controlled(), **selector.remote_options())
        found = {check.name: check.ok for check in report.checks}
        if any(name not in found for name in CAP_RAISE_CHECKS):
            return None
        return [name for name in CAP_RAISE_CHECKS if not found[name]]

    @router.put("/budget/lifetime-cap")
    def put_lifetime_cap(
        body: LifetimeCapRequest, profile: Admin, request: Request
    ) -> dict[str, Any]:
        """Set the ledger's lifetime cap between its opening provider usage and the US$1.00
        allocation above it. A raise needs the same amount confirmed and passing
        reconciliation checks; the ledger keeps every call, charge and earlier event."""

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
            if not (
                status.opening_usage <= cap <= status.opening_usage + LIFETIME_ALLOCATION_MICRO_USD
            ):
                audit(profile, action, "refused", code="CAP_OUT_OF_RANGE")
                raise _refusal(409, "CAP_OUT_OF_RANGE")
            raising = cap > status.cap
            if raising:
                if body.confirm_cap_micro_usd != cap:
                    audit(profile, action, "refused", code="CAP_CONFIRMATION_REQUIRED")
                    raise _refusal(400, "CAP_CONFIRMATION_REQUIRED")
                try:
                    failed = reconciliation_failures()
                except (ProfileConfigError, LedgerError):
                    failed = None
                if failed is None:
                    audit(profile, action, "refused", code="PROVIDER_CHECK_FAILED")
                    raise _refusal(409, "PROVIDER_CHECK_FAILED")
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
                    ledger.set_cap(cap, allow_raise=raising, confirm=cap if raising else None)
                except LedgerError:
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
