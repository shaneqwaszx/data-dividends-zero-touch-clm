"""The host interface: every command that could reach the Lightsail instance is built here.

Nothing in this module opens a connection by itself. Each method returns or issues a
``Command`` through the gate, so tests replace the runner with a mock host and plan-only or
dry-run modes cannot change anything. The Compose builder can only produce the verbs the
runbook uses; ``down``, ``-v``, ``--remove-orphans``, ``rm`` and scaling are not expressible.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path

from . import catalog
from .core import Command, Effect, Gate, ReleaseError, Result, Secret, StopCondition, read_json

SAFE_VALUE = re.compile(r"^[A-Za-z0-9._/:@-]+$")
SUMMARY_SOURCE = Path(__file__).with_name("effective_summary.py")
INSPECT_FORMAT = (
    "{{.Name}} {{.Id}} {{.Image}} {{.State.StartedAt}} {{.RestartCount}} "
    "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} "
    '{{index .Config.Labels "com.docker.compose.config-hash"}} {{.State.Running}}'
)


@dataclass(frozen=True)
class SshTarget:
    """Where the operator's SSH client connects. Read from a file outside the repository."""

    destination: str
    identity_file: str | None = None
    port: int = 22

    @staticmethod
    def load(path: Path) -> SshTarget:
        data = read_json(path)
        destination = str(data.get("ssh_destination", ""))
        if not re.fullmatch(r"[A-Za-z0-9._@-]+", destination):
            raise ReleaseError("OPERATOR_CONFIG_INVALID", "ssh_destination is missing or unsafe")
        return SshTarget(destination, data.get("identity_file"), int(data.get("port", 22)))


@dataclass(frozen=True)
class ContainerState:
    name: str
    present: bool
    container_id: str = ""
    image: str = ""
    started_at: str = ""
    restarts: int = 0
    health: str = ""
    config_hash: str = ""
    running: bool = False

    def identity(self) -> tuple[str, str, int]:
        return (self.container_id, self.started_at, self.restarts)


def safe(value: str) -> str:
    """Refuse any value that is not plainly inert before it is placed in a remote command."""

    if not SAFE_VALUE.fullmatch(value):
        raise StopCondition("UNSAFE_VALUE", "a value contains characters not allowed in a command")
    return value


class Host:
    def __init__(self, gate: Gate, target: SshTarget, profile: catalog.HostProfile) -> None:
        self.gate = gate
        self.target = target
        self.profile = profile

    # -- transport -----------------------------------------------------------------------

    def _argv(self, remote: str) -> tuple[str, ...]:
        argv = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            "ConnectTimeout=15",
            "-p",
            str(self.target.port),
        ]
        if self.target.identity_file:
            argv += ["-i", self.target.identity_file]
        return (*argv, self.target.destination, "--", remote)

    def read(
        self, remote: str, purpose: str, *, quiet: bool = False, timeout: float = 60
    ) -> Result:
        return self.gate.run(
            Command(self._argv(remote), Effect.HOST_READ, purpose, quiet=quiet, timeout=timeout)
        )

    def write(
        self,
        remote: str,
        purpose: str,
        *,
        stdin: Secret | None = None,
        stdin_file: str | None = None,
        timeout: float = 600,
        housekeeping: bool = False,
    ) -> Result:
        return self.gate.run(
            Command(
                self._argv(remote),
                Effect.HOST_WRITE,
                purpose,
                stdin=stdin,
                stdin_file=stdin_file,
                timeout=timeout,
                housekeeping=housekeeping,
            )
        )

    # -- Compose -------------------------------------------------------------------------

    def compose(self, set_name: str, *arguments: str) -> str:
        """The runbook wrapper (``dc`` / ``dca`` / ``dcg``) for one supported overlay set.

        The database connection setting is read on the host into the Compose process only; it
        never crosses the SSH channel and is never an argument.
        """

        if set_name in catalog.VALIDATION_ONLY_SETS:
            raise StopCondition(
                "OVERLAY_SET_UNSUPPORTED", f"{set_name} is never applied on the host"
            )
        files = catalog.overlay_files(set_name)
        p = self.profile
        parts = [
            "sudo",
            "-n",
            "--preserve-env=MONGO_URI",
            "docker",
            "compose",
            "--env-file",
            p.compose_env,
        ]
        for name in files:
            parts += ["-f", name]
        parts += list(arguments)
        return (
            f"cd {shlex.quote(p.workdir)} && "
            f'MONGO_URI="$(sudo -n cat {shlex.quote(p.mongo_uri_file)})" && export MONGO_URI && '
            f"{shlex.join(parts)} </dev/null"
        )

    def compose_config_quiet(self, set_name: str) -> str:
        return self.compose(set_name, "config", "--quiet")

    def compose_hashes(self, set_name: str) -> str:
        return self.compose(set_name, "config", "--hash", "*")

    def compose_summary(self, set_name: str) -> str:
        """Render on the host and reduce it there; only the secret-free summary comes back."""

        # read_text uses universal newlines, so a CRLF checkout still sends LF to the host.
        source = SUMMARY_SOURCE.read_text(encoding="utf-8")
        rendered = self.compose(set_name, "config", "--format", "json").removesuffix(" </dev/null")
        return f"{rendered} </dev/null | python3 -I -c {shlex.quote(source)}"

    def compose_up(self, set_name: str, service: str) -> str:
        svc = catalog.service(service)
        if not svc.automated_apply:
            raise StopCondition(
                "SERVICE_NOT_AUTOMATED", f"{service} is never recreated automatically"
            )
        return self.compose(
            set_name,
            "up",
            "-d",
            "--no-build",
            "--no-deps",
            "--wait",
            "--wait-timeout",
            str(self.profile.wait_timeout_seconds),
            service,
        )

    def compose_stop(self, set_name: str, service: str) -> str:
        return self.compose(set_name, "stop", catalog.service(service).name)

    def compose_start(self, set_name: str, service: str) -> str:
        return self.compose(set_name, "start", catalog.service(service).name)

    # -- read-only facts ------------------------------------------------------------------

    def container_states(self, services: list[str]) -> dict[str, ContainerState]:
        names = [self.profile.containers[s] for s in services]
        fmt = shlex.quote(INSPECT_FORMAT)
        script = "; ".join(
            f"sudo -n docker inspect -f {fmt} {shlex.quote(n)} 2>/dev/null || echo /{n} ABSENT"
            for n in names
        )
        result = self.read(script, "read container identities", quiet=True)
        states: dict[str, ContainerState] = {}
        if result.skipped:
            return states
        by_container = {self.profile.containers[s]: s for s in services}
        for line in result.stdout.splitlines():
            fields = line.split()
            if not fields:
                continue
            service = by_container.get(fields[0].lstrip("/"))
            if service is None:
                continue
            if len(fields) < 8 or fields[1] == "ABSENT":
                states[service] = ContainerState(service, present=False)
                continue
            states[service] = ContainerState(
                name=service,
                present=True,
                container_id=fields[1],
                image=fields[2],
                started_at=fields[3],
                restarts=int(fields[4]),
                health=fields[5],
                config_hash=fields[6],
                running=fields[7] == "true",
            )
        for service in services:
            states.setdefault(service, ContainerState(service, present=False))
        return states

    def env_value(self, variable: str) -> str | None:
        """One non-secret line of compose.env (an image pin or a volume name)."""

        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", variable) or not variable.endswith(
            ("_IMAGE", "_VOLUME")
        ):
            raise StopCondition("UNSAFE_VALUE", "only image and volume lines may be read")
        result = self.read(
            f"sudo -n grep -E '^{variable}=' {shlex.quote(self.profile.compose_env)} || true",
            f"read the {variable} line",
        )
        if result.skipped:
            return None
        lines = [line for line in result.stdout.splitlines() if line.startswith(f"{variable}=")]
        if len(lines) != 1:
            return None
        return lines[0].split("=", 1)[1].strip()

    def image_id(self, reference: str) -> str | None:
        result = self.read(
            f"sudo -n docker image inspect -f '{{{{.Id}}}} {{{{.Os}}}}/{{{{.Architecture}}}}' "
            f"{shlex.quote(safe(reference))} 2>/dev/null || echo ABSENT",
            "read an image identity on the host",
        )
        if result.skipped:
            return None
        fields = result.stdout.split()
        if len(fields) != 2 or fields[0] == "ABSENT":
            return None
        if fields[1] != catalog.PLATFORM:
            raise StopCondition("WRONG_PLATFORM", f"host image is {fields[1]}")
        return fields[0]
