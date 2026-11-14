"""Registry identities: where tokens live, how they are entered, and temporary Docker auth.

Two separate identities exist. ``publish`` may write packages and is used only on this
machine. ``pull`` may only read packages and is the only one ever streamed to the host, on
stdin, into a throwaway Docker configuration that is removed in the same command.

A token is held in the Windows Credential Manager (DPAPI-protected, per user). It is never
written to the repository, a Compose file, a log, an environment variable or a command line.
"""

from __future__ import annotations

import contextlib
import ctypes
import json
import shutil
import sys
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Protocol

from .core import (
    Clock,
    Command,
    Effect,
    Gate,
    ReleaseError,
    Secret,
    StopCondition,
    format_utc,
    parse_utc,
    register_basic_auth,
    utc_now,
)

IDENTITIES = {
    "publish": "write:packages (with read:packages); used on this machine only",
    "pull": "read:packages only; streamed to the host for one pull, never stored there",
}
TARGET_PREFIX = "clm-release/ghcr-"
MAX_TOKEN_LIFETIME = timedelta(days=90)
WARN_BEFORE = timedelta(days=7)


@dataclass(frozen=True)
class StoredCredential:
    username: str
    secret: Secret
    created_at: str
    expires_at: str


class CredentialStore(Protocol):
    def read(self, target: str) -> tuple[str, str] | None: ...  # (metadata JSON, value)

    def write(self, target: str, metadata: str, value: str) -> None: ...

    def delete(self, target: str) -> bool: ...


class MemoryStore:
    """For tests only."""

    def __init__(self) -> None:
        self.items: dict[str, tuple[str, str]] = {}

    def read(self, target: str) -> tuple[str, str] | None:
        return self.items.get(target)

    def write(self, target: str, metadata: str, value: str) -> None:
        self.items[target] = (metadata, value)

    def delete(self, target: str) -> bool:
        return self.items.pop(target, None) is not None


class WindowsCredentialStore:
    """Generic credentials in the Windows Credential Manager, through ``advapi32``."""

    _TYPE_GENERIC = 1
    _PERSIST_LOCAL_MACHINE = 2
    _NOT_FOUND = 1168

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise ReleaseError(
                "STORE_UNAVAILABLE", "the Windows Credential Manager is not available"
            )
        from ctypes import wintypes

        class _Credential(ctypes.Structure):
            _fields_ = (
                ("Flags", wintypes.DWORD),
                ("Type", wintypes.DWORD),
                ("TargetName", wintypes.LPWSTR),
                ("Comment", wintypes.LPWSTR),
                ("LastWritten", wintypes.FILETIME),
                ("CredentialBlobSize", wintypes.DWORD),
                ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                ("Persist", wintypes.DWORD),
                ("AttributeCount", wintypes.DWORD),
                ("Attributes", ctypes.c_void_p),
                ("TargetAlias", wintypes.LPWSTR),
                ("UserName", wintypes.LPWSTR),
            )

        self._struct = _Credential
        self._api = ctypes.WinDLL("advapi32", use_last_error=True)  # type: ignore[attr-defined, unused-ignore]
        self._api.CredReadW.argtypes = (
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.POINTER(_Credential)),
        )
        self._api.CredReadW.restype = wintypes.BOOL
        self._api.CredWriteW.argtypes = (ctypes.POINTER(_Credential), wintypes.DWORD)
        self._api.CredWriteW.restype = wintypes.BOOL
        self._api.CredDeleteW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD)
        self._api.CredDeleteW.restype = wintypes.BOOL
        self._api.CredFree.argtypes = (ctypes.c_void_p,)

    def read(self, target: str) -> tuple[str, str] | None:
        pointer = ctypes.POINTER(self._struct)()
        if not self._api.CredReadW(target, self._TYPE_GENERIC, 0, ctypes.byref(pointer)):
            if ctypes.get_last_error() == self._NOT_FOUND:  # type: ignore[attr-defined, unused-ignore]
                return None
            raise ReleaseError("STORE_READ_FAILED", "the credential store could not be read")
        try:
            entry = pointer.contents
            blob = ctypes.string_at(entry.CredentialBlob, entry.CredentialBlobSize)
            return (entry.Comment or "{}", blob.decode("utf-16-le"))
        finally:
            self._api.CredFree(pointer)

    def write(self, target: str, metadata: str, value: str) -> None:
        blob = value.encode("utf-16-le")
        buffer = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
        entry = self._struct()
        entry.Type = self._TYPE_GENERIC
        entry.TargetName = target
        entry.Comment = metadata
        entry.CredentialBlobSize = len(blob)
        entry.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
        entry.Persist = self._PERSIST_LOCAL_MACHINE
        entry.UserName = "clm-release"
        if not self._api.CredWriteW(ctypes.byref(entry), 0):
            raise ReleaseError("STORE_WRITE_FAILED", "the credential store refused the entry")

    def delete(self, target: str) -> bool:
        if self._api.CredDeleteW(target, self._TYPE_GENERIC, 0):
            return True
        if ctypes.get_last_error() == self._NOT_FOUND:  # type: ignore[attr-defined, unused-ignore]
            return False
        raise ReleaseError("STORE_WRITE_FAILED", "the credential store refused the removal")


def default_store() -> CredentialStore:
    return WindowsCredentialStore()


def _target(identity: str) -> str:
    if identity not in IDENTITIES:
        raise ReleaseError("IDENTITY_UNKNOWN", "identity must be publish or pull")
    return TARGET_PREFIX + identity


def bootstrap(
    store: CredentialStore,
    identity: str,
    *,
    username: str,
    expires_at: str,
    prompt: Callable[[str], str],
    interactive: bool,
    clock: Clock = utc_now,
    replace: bool = False,
) -> dict[str, str]:
    """One-time entry of a token at a hidden prompt. Returns non-secret metadata only."""

    target = _target(identity)
    if not interactive:
        raise StopCondition(
            "CREDENTIAL_NEEDS_OWNER", "a token is only ever typed by the owner at a hidden prompt"
        )
    if not username or not username.replace("-", "").isalnum() or len(username) > 39:
        raise ReleaseError("USERNAME_INVALID", "not a GitHub user name")
    expiry = parse_utc(expires_at)
    now = clock()
    if expiry <= now:
        raise StopCondition("CREDENTIAL_EXPIRED", "the stated expiry is already in the past")
    if expiry - now > MAX_TOKEN_LIFETIME:
        raise StopCondition("CREDENTIAL_LIFETIME", "use a token that expires within 90 days")
    if store.read(target) is not None and not replace:
        raise StopCondition("CREDENTIAL_EXISTS", f"{identity} already exists; use rotate")
    value = prompt(f"GHCR {identity} token ({IDENTITIES[identity]}), input hidden: ").strip()
    if not value or any(ch.isspace() for ch in value):
        raise StopCondition("CREDENTIAL_INVALID", "empty or malformed token; nothing was stored")
    secret = Secret(value)
    other = store.read(_target("pull" if identity == "publish" else "publish"))
    if other is not None and other[1] == value:
        raise StopCondition(
            "CREDENTIAL_NOT_SEPARATE", "publish and pull must be two different tokens"
        )
    metadata = {
        "username": username,
        "created_at": format_utc(now),
        "expires_at": format_utc(expiry),
        "identity": identity,
    }
    store.write(target, json.dumps(metadata, sort_keys=True), secret.reveal())
    return metadata


def rotate(
    store: CredentialStore,
    identity: str,
    *,
    username: str,
    expires_at: str,
    prompt: Callable[[str], str],
    interactive: bool,
    clock: Clock = utc_now,
) -> dict[str, str]:
    """Replace a stored token. The old one must then be revoked on GitHub by the owner."""

    previous = store.read(_target(identity))
    if previous is None:
        raise StopCondition("CREDENTIAL_MISSING", f"{identity} has not been bootstrapped")

    def different(text: str) -> str:
        value = prompt(text)
        if value.strip() == previous[1]:
            raise StopCondition("CREDENTIAL_NOT_ROTATED", "that is the token already stored")
        return value

    return bootstrap(
        store,
        identity,
        username=username,
        expires_at=expires_at,
        prompt=different,
        interactive=interactive,
        clock=clock,
        replace=True,
    )


def revoke_local(store: CredentialStore, identity: str) -> bool:
    """Remove the stored token. Revocation on GitHub is a separate owner step."""

    return store.delete(_target(identity))


def status(store: CredentialStore, clock: Clock = utc_now) -> list[dict[str, Any]]:
    """Non-secret state of both identities. Never returns or prints a token."""

    report: list[dict[str, Any]] = []
    for identity in IDENTITIES:
        found = store.read(_target(identity))
        if found is None:
            report.append({"identity": identity, "state": "absent"})
            continue
        metadata = _metadata(found[0])
        remaining = parse_utc(metadata["expires_at"]) - clock()
        state = "expired" if remaining <= timedelta(0) else "ok"
        if state == "ok" and remaining <= WARN_BEFORE:
            state = "expires-soon"
        report.append(
            {
                "identity": identity,
                "state": state,
                "username": metadata["username"],
                "created_at": metadata["created_at"],
                "expires_at": metadata["expires_at"],
                "days_left": max(remaining.days, 0),
            }
        )
    return report


def _metadata(text: str) -> dict[str, str]:
    try:
        data = json.loads(text)
        return {key: str(data[key]) for key in ("username", "created_at", "expires_at")}
    except (ValueError, KeyError, TypeError) as exc:
        raise ReleaseError("STORE_ENTRY_INVALID", "the stored entry has no valid metadata") from exc


def fetch(store: CredentialStore, identity: str, clock: Clock = utc_now) -> StoredCredential:
    """Read a token for immediate use. An expired or missing token stops the release."""

    found = store.read(_target(identity))
    if found is None:
        raise StopCondition("CREDENTIAL_MISSING", f"no {identity} token; run the bootstrap command")
    metadata = _metadata(found[0])
    if parse_utc(metadata["expires_at"]) <= clock():
        raise StopCondition("CREDENTIAL_EXPIRED", f"the {identity} token has expired; rotate it")
    secret = Secret(found[1])
    register_basic_auth(metadata["username"], secret)
    return StoredCredential(
        metadata["username"], secret, metadata["created_at"], metadata["expires_at"]
    )


@contextlib.contextmanager
def temporary_docker_config(gate: Gate) -> Iterator[dict[str, str]]:
    """A throwaway ``DOCKER_CONFIG`` with no credential helper, removed on every exit path.

    The user's own Docker configuration is neither read for credentials nor changed. Because a
    fresh configuration has no context, the daemon endpoint of the current context is passed
    explicitly.
    """

    endpoint = gate.run(
        Command(
            ("docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"),
            Effect.LOCAL_READ,
            "read the local Docker endpoint",
        )
    )
    directory = Path(tempfile.mkdtemp(prefix="clm-ghcr-"))
    try:
        (directory / "config.json").write_text('{"auths": {}}', encoding="ascii")
        env = {"DOCKER_CONFIG": str(directory)}
        if endpoint.ok and endpoint.stdout.strip():
            env["DOCKER_HOST"] = endpoint.stdout.strip()
        yield env
    finally:
        shutil.rmtree(directory, ignore_errors=True)
        if directory.exists():
            raise StopCondition(
                "AUTH_CONTEXT_NOT_REMOVED",
                "the temporary Docker configuration could not be removed",
            )
