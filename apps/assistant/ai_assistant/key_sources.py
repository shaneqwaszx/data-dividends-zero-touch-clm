"""The OpenRouter key for the remote profile (D-095 addendum, amended by D-106), from the first
source that holds one:

    1  hr_session    a key an HR administrator entered in AI Models, held in this process's
                     memory only and bound to that administrator's signed-in CLM session: it is
                     dropped when the session ends (sign-out, expiry, revocation), when HR clears
                     it, and on restart
    2  environment   OPENROUTER_API_KEY in the process environment
    3  env_file      OPENROUTER_API_KEY in the git-ignored apps/assistant/.env (only that one
                     line is read; it is never copied into the process environment)

A source that holds a value decides, even when the value is malformed (the key is then
``invalid`` and nothing falls through to a later source). An HR key whose session cannot be
checked right now is ``unverified``: it is not used and nothing falls through either. Only a
session that has ended releases the next source, and a model then rebuilds with that key and
re-runs its full preflight before the next call (the provider's own identity checks: the
Anthropic workspace, the OpenRouter usage reconciliation). The key is never returned, logged,
audited or written anywhere by this module; callers get a ``SecretStr``. Choosing a key changes
no spending limit: the ledger's lifetime cap, its daily allowance and the key's own
provider-side limit are checked on every call whatever the source.
"""

import hashlib
import hmac
import os
import re
import secrets
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import SecretStr

CREDENTIAL_VARIABLE = "OPENROUTER_API_KEY"
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
# Shape only (no network): what any source may hold. An HR-entered key must also look like an
# OpenRouter key.
_CREDENTIAL = re.compile(r"[\x21-\x7e]{1,256}")
HR_KEY = re.compile(r"sk-or-[A-Za-z0-9_-]{16,200}")

Source = Literal["hr_session", "environment", "env_file", "none"]
# Mirrors the CLM backend's fixed session lifetime (SESSION_TTL in the backend's
# services/authentication.py; using a session never extends it): an HR key never outlives it.
SESSION_LIMIT_SECONDS = 8 * 3600
# How long one successful check of the HR session is reused by read-only views. A model call, a
# connection test and a qualification start always check again (max_age 0).
REVALIDATE_SECONDS = 10.0

# The service installs the HR session check (model_admin.py: the CLM backend's /api/auth/me
# with that HR session's own cookie, never an RM's). True while the same user is signed in and
# may still manage AI models; False once the session ended or lost that right (the key is
# dropped); None when it cannot be told now (the key is held back, not dropped).
SessionCheck = Callable[[SecretStr, str], bool | None]


@dataclass(frozen=True)
class CredentialStatus:
    """What the AI Models page may show: never the key, nor any part of it."""

    source: Source
    status: Literal["configured", "missing", "invalid", "unverified"]
    hr_editable: bool
    set_at: float | None
    set_by: str | None
    generation: int
    expires_at: float | None = None
    verified_at: float | None = None
    fallback: Source = "none"

    def view(self) -> dict[str, object]:
        return {
            "source": self.source,
            "status": self.status,
            "hr_editable": self.hr_editable,
            "persistence": "memory_only" if self.source in ("hr_session", "none") else "server",
            "set_at": self.set_at,
            "set_by": self.set_by,
            "expires_at": self.expires_at,
            "verified_at": self.verified_at,
            "fallback": self.fallback,
        }


@dataclass(frozen=True)
class HrEntry:
    # The HR key once its session is known to be live (None otherwise), with what the page
    # may show; ``held`` when a key exists but its session cannot be checked now.
    key: SecretStr | None
    set_at: float | None
    set_by: str | None
    generation: int
    verified_at: float | None
    held: bool


class HrCredential:
    """One provider's HR-entered key, in memory only, bound to the HR session that entered it.
    ``generation`` changes on every set or clear, so a model holding an older key rebuilds and
    re-runs its preflight before the next call."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._key: SecretStr | None = None
        self._session: SecretStr | None = None
        self._set_at: float | None = None
        self._set_by: str | None = None
        self._verified_at: float | None = None
        self._generation = 0

    def set(self, key: SecretStr, by: str, *, session: SecretStr | None) -> None:
        # ``session`` None only inside a qualification process, for the key its supervising
        # service handed over on standard input (qualify_model.py): that service keeps checking
        # the HR session and ends the run when it ends.
        with self._lock:
            self._key, self._session, self._set_by = key, session, by
            self._set_at = self._verified_at = time.time()
            self._generation += 1

    def clear(self) -> bool:
        with self._lock:
            return self._clear()

    def _clear(self) -> bool:
        had = self._key is not None
        self._key = self._session = None
        self._set_at = self._set_by = self._verified_at = None
        self._generation += 1
        return had

    def snapshot(self) -> tuple[SecretStr | None, float | None, str | None, int]:
        with self._lock:
            return self._key, self._set_at, self._set_by, self._generation

    def current(self, max_age: float = REVALIDATE_SECONDS) -> HrEntry:
        # Past the session limit, or once the session check says the session ended, the key is
        # dropped; when the check cannot answer, the key is held back. The check runs outside
        # the lock and its answer applies only to the entry it checked.
        while True:
            now = time.time()
            with self._lock:
                if self._set_at is not None and now >= self._set_at + SESSION_LIMIT_SECONDS:
                    self._clear()
                key, session, by = self._key, self._session, self._set_by
                set_at, verified_at, generation = self._set_at, self._verified_at, self._generation
            if key is None:
                return HrEntry(None, None, None, generation, None, False)
            if session is None or (verified_at is not None and now - verified_at < max_age):
                return HrEntry(key, set_at, by, generation, verified_at, False)
            check = _SESSION_CHECK
            live = check(session, by or "") if check is not None else None
            with self._lock:
                if self._generation != generation:
                    continue  # set or cleared meanwhile: decide on the newer entry
                if live is False:
                    self._clear()
                    return HrEntry(None, None, None, self._generation, None, False)
                if live is None:
                    self._verified_at = None  # no earlier check vouches for it any more
                    return HrEntry(None, set_at, by, generation, None, True)
                self._verified_at = time.time()
                return HrEntry(key, set_at, by, generation, self._verified_at, False)


# The service's HR stores, one per provider (tests replace them).
HR_STORE = HrCredential()
ANTHROPIC_STORE = HrCredential()
_SESSION_CHECK: SessionCheck | None = None


def install_session_check(check: SessionCheck | None) -> None:
    """The service's HR session check (model_admin.py); None holds every HR key back."""

    global _SESSION_CHECK
    _SESSION_CHECK = check


# Compares keys within this process without keeping them side by side; never stored or shown.
_PROCESS_SECRET = secrets.token_bytes(32)


def identity(key: SecretStr | None) -> str | None:
    """A process-local marker of which key is in use (an HMAC under a random per-process
    secret): equal markers mean the same key. Never written, logged or returned."""

    if key is None:
        return None
    return hmac.new(_PROCESS_SECRET, key.get_secret_value().encode(), hashlib.sha256).hexdigest()


def env_file_value(path: Path, variable: str = CREDENTIAL_VARIABLE) -> str | None:
    if not path.is_file():
        return None
    try:
        value = dotenv_values(path, interpolate=False).get(variable)
    except (OSError, UnicodeDecodeError, ValueError):
        return "\x00unreadable"  # present but unusable: reported as invalid, never shown
    return value if value else None


def resolve_from(
    variable: str,
    shape: re.Pattern[str],
    environ: Mapping[str, str],
    env_file: Path | None,
    store: HrCredential | None,
    max_age: float,
) -> tuple[SecretStr | None, CredentialStatus]:
    # One provider's key and status in the D-106 order: the live HR session's key, then the
    # process environment, then the .env file. A held-back HR key decides (nothing falls
    # through); ``fallback`` names the source that applies once the HR key is gone.
    entry = store.current(max_age) if store is not None else None
    later: list[tuple[Source, str | None]] = [
        ("environment", environ.get(variable) or None),
        ("env_file", env_file_value(env_file, variable) if env_file is not None else None),
    ]
    fallback: Source = next((source for source, value in later if value is not None), "none")
    editable = store is not None
    generation = entry.generation if entry is not None else 0
    if entry is not None and (entry.key is not None or entry.held):
        status = CredentialStatus(
            source="hr_session",
            status="configured" if entry.key is not None else "unverified",
            hr_editable=True,
            set_at=entry.set_at,
            set_by=entry.set_by,
            generation=generation,
            expires_at=None if entry.set_at is None else entry.set_at + SESSION_LIMIT_SECONDS,
            verified_at=entry.verified_at,
            fallback=fallback,
        )
        return entry.key, status
    for source, value in later:
        if value is None:
            continue
        valid = bool(shape.fullmatch(value))
        state: Literal["configured", "invalid"] = "configured" if valid else "invalid"
        status = CredentialStatus(source, state, editable, None, None, generation)
        return (SecretStr(value) if valid else None), status
    return None, CredentialStatus("none", "missing", editable, None, None, generation)


def resolve(
    environ: Mapping[str, str] | None = None,
    *,
    env_file: Path | None = None,
    store: HrCredential | None = None,
    max_age: float = REVALIDATE_SECONDS,
) -> tuple[SecretStr | None, CredentialStatus]:
    """The OpenRouter key and its status. ``environ`` given (tests and seams): that mapping
    only, unless ``env_file`` or ``store`` are also given. Left out: the HR session's key, then
    the process environment, then the service's .env file."""

    if environ is None:
        environ = os.environ
        env_file = ENV_FILE if env_file is None else env_file
        store = HR_STORE if store is None else store
    return resolve_from(CREDENTIAL_VARIABLE, _CREDENTIAL, environ, env_file, store, max_age)
