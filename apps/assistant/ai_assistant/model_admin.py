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

Who is asking, and whether they hold ``MODEL_CONFIG_MANAGE``, always comes from the CLM
backend with the caller's own session; activation and rollback ask again inside the lock
that applies them. Refusals of a signed-in caller are audited. Nothing here reads a case or
an answer record, and the browser can only name a profile id, except that an HR
administrator may hand the server an OpenRouter key when no environment or .env key exists
(key_sources.py): it is kept in server memory only and never sent back, logged or audited;
changing it needs the Origin header of an allowed page and is rate limited.

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
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from . import key_sources
from .clm_client import SESSION_COOKIE_NAME, ClmBackendClient, ClmBackendError
from .config import AiAssistantSettings
from .llm import ChatModel, OpenAICompatibleChatModel
from .model_admin_store import (
    Activation,
    Choice,
    ModelAdminStore,
    QualificationBusy,
    RevisionConflict,
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
from .remote_test import (
    RemoteTestModel,
    budget_status,
    connection_check,
    forget_provider,
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
        """The active model for one request (read once, used for the whole answer)."""

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
                remote = RemoteTestModel(self.settings, **self.remote_options())
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
            "budget": budget_status(settings, environ=selector.environ)
            if settings.local_api_test_decision
            else None,
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
            result = connection_check(settings, **selector.remote_options())
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
                    connection_check(settings, **selector.remote_options())
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
        return budget_status(settings, environ=selector.environ)

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

    return router
