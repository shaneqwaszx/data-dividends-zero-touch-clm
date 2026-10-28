"""The OpenRouter key for the remote profile (D-095 addendum), from the first source that
holds one:

    1  environment   OPENROUTER_API_KEY in the process environment (authoritative)
    2  env_file      OPENROUTER_API_KEY in the git-ignored apps/assistant/.env (only that one
                     line is read; it is never copied into the process environment)
    3  hr_memory     a key an HR administrator entered in AI Models, held in this process's
                     memory only: it is lost on restart and must be entered again

A source that holds a value decides, even when the value is malformed (the key is then
``invalid`` and nothing falls through to a later source). An HR administrator can neither
see, replace nor clear an environment or .env key. The key is never returned, logged,
audited or written anywhere by this module; callers get a ``SecretStr``. Choosing a key
changes no spending limit: the ledger's lifetime cap, its daily allowance and the key's own
provider-side limit are checked on every call whatever the source (the preflight re-runs when
the key changes).
"""

import hashlib
import hmac
import os
import re
import secrets
import threading
import time
from collections.abc import Mapping
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

Source = Literal["environment", "env_file", "hr_memory", "none"]


@dataclass(frozen=True)
class CredentialStatus:
    """What the AI Models page may show: never the key, nor any part of it."""

    source: Source
    status: Literal["configured", "missing", "invalid"]
    hr_editable: bool
    set_at: float | None
    set_by: str | None
    generation: int

    def view(self) -> dict[str, object]:
        return {
            "source": self.source,
            "status": self.status,
            "hr_editable": self.hr_editable,
            "persistence": "memory_only" if self.source in ("hr_memory", "none") else "server",
            "set_at": self.set_at,
            "set_by": self.set_by,
        }


class HrCredential:
    """The HR-entered key, in memory only. ``generation`` changes on every set or clear, so a
    model holding an older key rebuilds and re-runs its preflight before the next call."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._key: SecretStr | None = None
        self._set_at: float | None = None
        self._set_by: str | None = None
        self._generation = 0

    def set(self, key: SecretStr, by: str) -> None:
        with self._lock:
            self._key, self._set_at, self._set_by = key, time.time(), by
            self._generation += 1

    def clear(self) -> bool:
        with self._lock:
            had = self._key is not None
            self._key, self._set_at, self._set_by = None, None, None
            self._generation += 1
            return had

    def snapshot(self) -> tuple[SecretStr | None, float | None, str | None, int]:
        with self._lock:
            return self._key, self._set_at, self._set_by, self._generation


# The service's one HR store (tests replace it).
HR_STORE = HrCredential()
# Compares keys within this process without keeping them side by side; never stored or shown.
_PROCESS_SECRET = secrets.token_bytes(32)


def identity(key: SecretStr | None) -> str | None:
    """A process-local marker of which key is in use (an HMAC under a random per-process
    secret): equal markers mean the same key. Never written, logged or returned."""

    if key is None:
        return None
    return hmac.new(_PROCESS_SECRET, key.get_secret_value().encode(), hashlib.sha256).hexdigest()


def _env_file_value(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        value = dotenv_values(path, interpolate=False).get(CREDENTIAL_VARIABLE)
    except (OSError, UnicodeDecodeError, ValueError):
        return "\x00unreadable"  # present but unusable: reported as invalid, never shown
    return value if value else None


def resolve(
    environ: Mapping[str, str] | None = None,
    *,
    env_file: Path | None = None,
    store: HrCredential | None = None,
) -> tuple[SecretStr | None, CredentialStatus]:
    """The key and its status. ``environ`` given (tests and seams): that mapping only, unless
    ``env_file`` or ``store`` are also given. Left out: the process environment, then the
    service's .env file, then the HR store."""

    if environ is None:
        environ = os.environ
        env_file = ENV_FILE if env_file is None else env_file
        store = HR_STORE if store is None else store
    key, set_at, set_by, generation = store.snapshot() if store else (None, None, None, 0)
    candidates: list[tuple[Source, str | None]] = [
        ("environment", environ.get(CREDENTIAL_VARIABLE) or None),
        ("env_file", _env_file_value(env_file) if env_file is not None else None),
        ("hr_memory", key.get_secret_value() if key is not None else None),
    ]
    for source, value in candidates:
        if value is None:
            continue
        valid = bool(_CREDENTIAL.fullmatch(value))
        hr = source == "hr_memory"
        status = CredentialStatus(
            source=source,
            status="configured" if valid else "invalid",
            hr_editable=hr,
            set_at=set_at if hr else None,
            set_by=set_by if hr else None,
            generation=generation,
        )
        return (SecretStr(value) if valid else None), status
    return None, CredentialStatus("none", "missing", store is not None, None, None, generation)
