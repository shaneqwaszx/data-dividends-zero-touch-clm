"""Shared building blocks: errors, secret handling, the command model and the execution gate.

Every action the toolchain takes outside this process is a ``Command`` with a declared
``Effect``. All commands go through one ``Gate``, which is the only place that decides whether
a command may run in the current mode. Plan-only and dry-run therefore cannot write to the host
or the registry by construction, whatever the calling code does.
"""

from __future__ import annotations

import base64
import enum
import hashlib
import json
import os
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_utc(value: str) -> datetime:
    """Parse an ISO-8601 instant that must carry an explicit UTC designator."""

    if not isinstance(value, str) or not (value.endswith("Z") or value.endswith("+00:00")):
        raise ReleaseError("TIME_NOT_UTC", "timestamp must end in Z or +00:00")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReleaseError("TIME_INVALID", "timestamp is not ISO-8601") from exc
    return parsed.astimezone(UTC)


def format_utc(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class ReleaseError(Exception):
    """A refusal with a stable code. The message never contains a secret."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class StopCondition(ReleaseError):
    """An explicit stop: execution must not continue and nothing is retried silently."""


# --------------------------------------------------------------------------------------------
# Secrets and redaction
# --------------------------------------------------------------------------------------------

_SECRET_VALUES: set[str] = set()
_PATTERNS = (
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?i)\b(?:mongodb(?:\+srv)?|postgres(?:ql)?|redis)://\S+"),
    re.compile(r"(?i)\b(authorization\s*[:=]\s*)(?:bearer|basic)\s+\S+"),
    re.compile(r"\bsk-(?:ant|or)-[A-Za-z0-9_-]{12,}"),
    re.compile(r'(?i)("auth"\s*:\s*")[A-Za-z0-9+/=]{8,}(")'),
)
REDACTED = "[REDACTED]"


class Secret:
    """A credential held in memory. It cannot be printed, formatted or serialised by accident."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        if not value:
            raise ReleaseError("SECRET_EMPTY", "an empty credential was supplied")
        self._value = value
        register_secret(value)

    def reveal(self) -> str:
        """The raw value. Call only at the point where it is written to a child's stdin."""

        return self._value

    def __repr__(self) -> str:
        return "<Secret>"

    __str__ = __repr__

    def __format__(self, spec: str) -> str:
        return "<Secret>"

    def __reduce__(self) -> Any:
        raise TypeError("a Secret cannot be pickled")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Secret) and other._value == self._value

    def __hash__(self) -> int:
        return hash(("Secret", self._value))


def register_secret(value: str) -> None:
    """Make ``redact`` remove this value and its usual encodings from any text."""

    if len(value) < 4:
        return
    _SECRET_VALUES.add(value)
    _SECRET_VALUES.add(base64.b64encode(value.encode()).decode())


def register_basic_auth(username: str, secret: Secret) -> None:
    """Docker stores ``base64(user:token)``; register that form as well."""

    pair = f"{username}:{secret.reveal()}".encode()
    _SECRET_VALUES.add(base64.b64encode(pair).decode())


def redact(text: str) -> str:
    for value in sorted(_SECRET_VALUES, key=len, reverse=True):
        if value in text:
            text = text.replace(value, REDACTED)
    for pattern in _PATTERNS:
        if pattern.groups == 2:
            text = pattern.sub(lambda m: f"{m.group(1)}{REDACTED}{m.group(2)}", text)
        elif pattern.groups == 1:
            text = pattern.sub(lambda m: f"{m.group(1)}{REDACTED}", text)
        else:
            text = pattern.sub(REDACTED, text)
    return text


def contains_secret(text: str) -> bool:
    return any(value in text for value in _SECRET_VALUES)


# --------------------------------------------------------------------------------------------
# Hashing and canonical JSON
# --------------------------------------------------------------------------------------------


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(document: Any) -> bytes:
    """The single byte form a manifest or approval is hashed in."""

    return json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def canonical_hash(document: Any) -> str:
    return sha256_bytes(canonical_json(document))


# --------------------------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------------------------


class Effect(enum.Enum):
    LOCAL_READ = "local-read"
    LOCAL_WRITE = "local-write"  # local Docker build, tag or temporary container
    HOST_READ = "host-read"
    HOST_WRITE = "host-write"
    REGISTRY_READ = "registry-read"
    REGISTRY_WRITE = "registry-write"
    PUBLIC_READ = "public-read"  # unauthenticated GET against the public site
    PROVIDER_CALL = "provider-call"  # never issued by this toolchain; refused by the gate


class Mode(enum.Enum):
    PLAN_ONLY = "plan-only"
    DRY_RUN = "dry-run"
    LOCAL = "local"  # preparation on this machine: builds and checks, never host or registry
    EXECUTE = "execute"


@dataclass(frozen=True)
class Command:
    argv: tuple[str, ...]
    effect: Effect
    purpose: str
    stdin: Secret | bytes | None = None
    env: Mapping[str, str] | None = None
    cwd: str | None = None
    timeout: float = 300.0
    # Output is never copied into the audit log when True (it is still returned to the caller).
    quiet: bool = False
    # Keep stdout as bytes in ``Result.raw`` (git blobs, image archives).
    binary: bool = False
    # Stream this file to the child's stdin (an image archive); excludes ``stdin``.
    stdin_file: str | None = None
    # Write stdout straight to this file instead of capturing it (``docker save``).
    stdout_file: str | None = None
    # Releasing a lock or removing a temporary file: still allowed after an approval expires,
    # so an expired window never leaves the host locked.
    housekeeping: bool = False


@dataclass(frozen=True)
class Result:
    returncode: int
    stdout: str = ""
    stderr: str = ""
    skipped: bool = False
    raw: bytes = b""

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.skipped


class Runner(Protocol):
    def run(self, command: Command) -> Result: ...


class SubprocessRunner:
    """Runs a command without a shell. A secret reaches the child only through stdin."""

    def run(self, command: Command) -> Result:
        data: bytes | None
        if isinstance(command.stdin, Secret):
            data = (command.stdin.reveal() + "\n").encode()
        else:
            data = command.stdin
        env = dict(os.environ)
        if command.env:
            env.update(command.env)
        source = open(command.stdin_file, "rb") if command.stdin_file else None  # noqa: SIM115
        sink = open(command.stdout_file, "wb") if command.stdout_file else None  # noqa: SIM115
        try:
            done = subprocess.run(  # noqa: S603 - argv list, shell=False
                list(command.argv),
                input=None if source else data,
                stdin=source if source else None,
                stdout=sink if sink else subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=command.cwd,
                timeout=command.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return Result(124, "", "command timed out")
        except OSError as exc:
            return Result(127, "", f"could not start {command.argv[0]}: {exc.strerror}")
        finally:
            if source:
                source.close()
            if sink:
                sink.close()
        if sink:
            return Result(done.returncode, "", done.stderr.decode("utf-8", "replace"))
        if command.binary:
            return Result(
                done.returncode, "", done.stderr.decode("utf-8", "replace"), raw=done.stdout
            )
        return Result(
            done.returncode,
            done.stdout.decode("utf-8", "replace"),
            done.stderr.decode("utf-8", "replace"),
        )


# Words that must never reach the host, whoever builds the command. Defence in depth: the
# Compose builder in host.py cannot produce them, and the gate refuses them again here.
FORBIDDEN_REMOTE = (
    (re.compile(r"\bcompose\b[^|;&]*\sdown\b"), "compose down"),
    (re.compile(r"--remove-orphans\b"), "--remove-orphans"),
    (re.compile(r"\bcompose\b[^|;&]*\s(?:-v|--volumes)\b"), "compose -v/--volumes"),
    (re.compile(r"\bvolume\s+(?:rm|remove|prune)\b"), "volume removal"),
    (re.compile(r"\b(?:system|container|image|network|builder)\s+prune\b"), "prune"),
    (re.compile(r"--scale\b"), "--scale (a second backend)"),
    (
        re.compile(r"\bcompose\b[^|;&]*\s(?:run|build|create|kill|restart|exec|cp|pause)\b"),
        "unsupported verb",
    ),
    (re.compile(r"\bcompose\b[^|;&]*\srm\b"), "compose rm"),
    (re.compile(r"\bcompose\b[^|;&]*\sup\b(?![^|;&]*--no-deps)"), "up without --no-deps"),
    (re.compile(r"\bcompose\b[^|;&]*\sup\b(?![^|;&]*--no-build)"), "up without --no-build"),
    (
        re.compile(r"--renew-anon-volumes\b|--force-recreate\b|\bcompose\b[^|;&]*\s-\w*V\w*\b"),
        "recreate flag",
    ),
    (
        re.compile(r"\bcompose\b[^|;&]*\s(?:up|stop|start)\b[^|;&]*\smongo\b"),
        "Mongo is never touched",
    ),
    (
        re.compile(
            r"\bdocker\s+(?:rm|rmi|kill|build|run|stop|start|restart|exec|cp|commit|update)\b"
        ),
        "direct docker mutation",
    ),
    (
        re.compile(r"\bdocker\s+(?:container|image|network|volume)\s+(?:rm|remove|create|prune)\b"),
        "direct docker mutation",
    ),
    (re.compile(r"\b(?:mongodump|mongorestore|mongosh)\b"), "database tooling"),
    (re.compile(r"\b(?:nft|iptables|iptables-legacy|ufw)\b"), "firewall change"),
    (re.compile(r"\bsystemctl\s+(?!show\b|is-active\b|is-enabled\b|status\b)\w+"), "systemctl"),
    (re.compile(r"\b(?:reboot|shutdown|poweroff)\b"), "host power"),
)


def assert_remote_allowed(remote: str) -> None:
    """Defence in depth only: the command builders are the real control.

    Quotes and backslashes are removed first so ``"down"`` or ``do''wn`` cannot slip past.
    """

    plain = re.sub(r"[\\'\"]", "", remote)
    for pattern, label in FORBIDDEN_REMOTE:
        if pattern.search(plain):
            raise StopCondition("FORBIDDEN_HOST_COMMAND", f"refused: {label}")


@dataclass
class AuditLog:
    """Append-only JSON-lines record. Every field is redacted before it is written."""

    path: Path | None = None
    clock: Clock = utc_now
    echo: Callable[[str], None] | None = None
    events: list[dict[str, Any]] = field(default_factory=list)

    def event(self, kind: str, **fields: Any) -> None:
        entry: dict[str, Any] = {"at": format_utc(self.clock()), "kind": kind}
        for key, value in fields.items():
            entry[key] = _redact_any(value)
        self.events.append(entry)
        line = json.dumps(entry, sort_keys=True)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line + "\n")
        if self.echo is not None:
            detail = " ".join(f"{k}={entry[k]}" for k in sorted(entry) if k not in {"at", "kind"})
            self.echo(f"[{entry['at']}] {kind} {detail}".rstrip())


def _redact_any(value: Any) -> Any:
    if isinstance(value, Secret):
        return REDACTED
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, Mapping):
        return {str(k): _redact_any(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_redact_any(v) for v in value]
    if isinstance(value, bool | int | float) or value is None:
        return value
    return redact(str(value))


_ALLOWED: dict[Mode, frozenset[Effect]] = {
    Mode.PLAN_ONLY: frozenset({Effect.LOCAL_READ}),
    Mode.DRY_RUN: frozenset(
        {Effect.LOCAL_READ, Effect.HOST_READ, Effect.REGISTRY_READ, Effect.PUBLIC_READ}
    ),
    Mode.LOCAL: frozenset({Effect.LOCAL_READ, Effect.LOCAL_WRITE}),
    Mode.EXECUTE: frozenset(set(Effect) - {Effect.PROVIDER_CALL}),
}


class Gate:
    """The only path from the toolchain to a process, the host or the registry."""

    def __init__(
        self,
        runner: Runner,
        mode: Mode,
        log: AuditLog,
        *,
        host_reads: bool = True,
        deadline: Callable[[], None] | None = None,
    ) -> None:
        self._runner = runner
        self.mode = mode
        self.log = log
        self._host_reads = host_reads
        # Called before every write; raises StopCondition once an approval has expired.
        self._deadline = deadline
        self.issued: list[Command] = []
        self.skipped: list[Command] = []

    def set_deadline(self, deadline: Callable[[], None] | None) -> None:
        self._deadline = deadline

    def run(self, command: Command) -> Result:
        self._check(command)
        allowed = command.effect in _ALLOWED[self.mode]
        if command.effect in {Effect.HOST_READ, Effect.PUBLIC_READ} and not self._host_reads:
            allowed = False
        shown = redact(" ".join(command.argv))
        if not allowed:
            self.skipped.append(command)
            self.log.event(
                "command-skipped",
                effect=command.effect.value,
                mode=self.mode.value,
                purpose=command.purpose,
                command=shown,
            )
            return Result(0, "", "", skipped=True)
        writes = command.effect in {Effect.HOST_WRITE, Effect.REGISTRY_WRITE}
        if writes and self._deadline and not command.housekeeping:
            self._deadline()
        self.issued.append(command)
        result = self._runner.run(command)
        fields: dict[str, Any] = {
            "effect": command.effect.value,
            "purpose": command.purpose,
            "command": shown,
            "exit": result.returncode,
        }
        if not command.quiet and not command.binary:
            fields["stdout"] = _tail(result.stdout)
        if result.returncode != 0:
            fields["stderr"] = _tail(result.stderr)
        self.log.event("command", **fields)
        return Result(
            result.returncode,
            redact(result.stdout),
            redact(result.stderr),
            result.skipped,
            result.raw,
        )

    def _check(self, command: Command) -> None:
        if command.effect is Effect.PROVIDER_CALL:
            raise StopCondition("PROVIDER_CALL_REFUSED", "the release toolchain calls no provider")
        for part in command.argv:
            if contains_secret(part):
                raise StopCondition(
                    "SECRET_IN_ARGUMENT", "a credential was about to be passed as an argument"
                )
        for value in (command.env or {}).values():
            if contains_secret(value):
                raise StopCondition(
                    "SECRET_IN_ENVIRONMENT", "a credential was about to be placed in an environment"
                )
        if command.effect in {Effect.HOST_READ, Effect.HOST_WRITE}:
            assert_remote_allowed(command.argv[-1])


def _tail(text: str, limit: int = 2000) -> str:
    text = text.strip()
    return text if len(text) <= limit else "..." + text[-limit:]


def require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise StopCondition(code, message)


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReleaseError("FILE_MISSING", f"{path.name} not found") from exc
    except json.JSONDecodeError as exc:
        raise ReleaseError("JSON_INVALID", f"{path.name} is not valid JSON") from exc


def write_json(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())  # on disk before the caller takes its next step
    temporary.replace(path)


def short(digest: str, length: int = 12) -> str:
    return digest.removeprefix("sha256:")[:length]


def as_list(value: Sequence[str] | None) -> list[str]:
    return list(value or [])
