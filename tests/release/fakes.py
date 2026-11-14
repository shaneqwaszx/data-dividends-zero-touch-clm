"""A mock Lightsail host, a mock registry and manifest builders for the release tests.

No test in this package opens a network connection. ``FakeWorld`` is the ``Runner`` behind the
gate: it receives every command the toolchain would issue, simulates the host and registry in
memory, and records what reached it so tests can prove that a mode issued no write.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from tools.release import catalog, render
from tools.release.core import AuditLog, Command, Effect, Gate, Mode, Result, Secret
from tools.release.host import Host, SshTarget
from tools.release.manifest import manifest_hash

REPO = Path(__file__).resolve().parents[2]
SAMPLE = REPO / "docs" / "release" / "samples" / "release-manifest.d0142d8.sample.json"
NOW = datetime(2026, 11, 14, 10, 0, 0, tzinfo=UTC)
NS = catalog.REGISTRY_NAMESPACE


def digest(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def new_reference(manifest: dict[str, Any], name: str) -> str:
    """The digest reference a published manifest pins ``name`` to."""

    image = manifest["images"][name]
    return f"{image['repository']}@{image['registry_manifest_digest']}"


def sentinel_token(label: str = "pull") -> str:
    """A fake credential built by concatenation so the repository scanner never sees a literal."""

    return "gh" + "p_" + ("SENTINEL" + label.upper()) * 4


OLD = {
    "frontend": f"{NS}/clm-aws-demo-frontend@{digest('old-frontend')}",
    "backend": f"{NS}/clm-aws-demo-backend@{digest('old-backend')}",
    "assistant": f"{NS}/clm-aws-demo-assistant@{digest('old-assistant')}",
}


class Clock:
    def __init__(self, now: datetime = NOW) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **delta: float) -> None:
        self.now += timedelta(**delta)


def make_manifest(
    services: list[str],
    *,
    risk: str | None = None,
    active: tuple[str, ...] = ("assistant",),
    published: bool = True,
    automatic: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """A valid manifest for ``services`` derived from the tracked sample."""

    manifest: dict[str, Any] = json.loads(SAMPLE.read_text(encoding="utf-8"))
    manifest["services_changed"] = list(services)
    running = ["frontend", "backend", "mongo"] + (["assistant"] if "assistant" in active else [])
    if "goldtier" in active:
        running += ["goldtier-egress", "goldtier-dns"]
    manifest["services_unchanged"] = [s for s in running if s not in services]
    manifest["overlay"]["active_host_overlays"] = list(active)
    manifest["images"] = {k: v for k, v in manifest["images"].items() if k in services}
    manifest["rollback"] = {k: v for k, v in manifest["rollback"].items() if k in services}
    manifest["coupling"] = [
        c for c in manifest["coupling"] if c["requires"] in services and c["service"] in services
    ]
    for name in services:
        entry = manifest["rollback"][name]
        entry["target_image"] = OLD[name]
        if name == "backend":
            entry.update(
                target_source_commit="68e621dba0a845e8dcff19a9d3bd4eb2ce43a050",
                target_snapshot_schema_writes=20,
                target_confirmed_on_host=True,
                data_compatible=True,
            )
        if name == "assistant":
            entry["data_compatible"] = "unproven"
        wanted = (automatic or {}).get(name)
        if wanted is not None:
            entry["automatic"] = wanted
            if wanted:
                entry["data_compatible"] = True
        if published:
            manifest["images"][name]["registry_manifest_digest"] = digest(f"registry-{name}")
            manifest["images"][name]["registry_tag"] = "rc-d0142d8e8d74-000000000000"
    floor = max(
        (catalog.service(s).base_risk for s in services), key=lambda r: catalog.RISK_ORDER[r]
    )
    manifest["risk_class"] = risk or floor
    manifest["change_classes"] = ["CI_TOOLING"]
    return manifest


def make_approval(
    manifest: dict[str, Any],
    *,
    services: list[str] | None = None,
    actions: tuple[str, ...] = ("deploy",),
    auto_rollback: bool = True,
    start: datetime = NOW - timedelta(minutes=5),
    end: datetime = NOW + timedelta(hours=2),
) -> dict[str, Any]:
    stamp = "%Y-%m-%dT%H:%M:%SZ"
    hashed = manifest_hash(manifest)
    return {
        "schema_version": 1,
        "approval_id": f"apr-{hashed[:12]}-20261114T095500Z",
        "release_id": manifest["release_id"],
        "manifest_sha256": hashed,
        "services": sorted(services if services is not None else manifest["services_changed"]),
        "risk_class": manifest["risk_class"],
        "actions": sorted(actions),
        "auto_rollback": auto_rollback,
        "not_before": start.strftime(stamp),
        "expires_at": end.strftime(stamp),
        "approved_by": "owner (test)",
        "approved_at": start.strftime(stamp),
        "statement": "test approval",
    }


@dataclass
class Container:
    container_id: str
    image: str
    label_hash: str
    started: str = "2026-11-01T00:00:00Z"
    restarts: int = 0
    health: str = "healthy"
    running: bool = True


@dataclass
class FakeWorld:
    """Simulated host + registry + local Docker. Knobs are plain attributes tests set."""

    manifest: dict[str, Any]
    clock: Clock = field(default_factory=Clock)
    active: tuple[str, ...] = ("assistant",)
    received: list[Command] = field(default_factory=list)
    stdin_seen: list[str] = field(default_factory=list)
    ssh_sessions: int = 1
    mem_available: int = 2_500_000
    disk_free: int = 9_000_000
    host_lock: bool = False
    backups: int = 1
    listening: tuple[str, ...] = ("0.0.0.0:22", "0.0.0.0:80", "[::]:443", "127.0.0.53%lo:53")
    pull_ok: bool = True
    pull_delivers: dict[str, str] = field(default_factory=dict)  # reference -> wrong identity
    unhealthy_after_up: set[str] = field(default_factory=set)
    up_fails: set[str] = field(default_factory=set)
    stop_fails: set[str] = field(default_factory=set)
    drifted: set[str] = field(default_factory=set)
    extra_backend: bool = False
    volume_changes_after_up: bool = False
    smoke: dict[str, str] = field(default_factory=dict)
    compose_file_override: dict[str, str] = field(default_factory=dict)
    host_summary_extra_network: str | None = None
    on_command: Any = None

    def __post_init__(self) -> None:
        self.env = {
            "FRONTEND_IMAGE": OLD["frontend"],
            "BACKEND_IMAGE": OLD["backend"],
            "ASSISTANT_IMAGE": OLD["assistant"],
            "MONGO_DATA_VOLUME": "clm-mongo-data",
            "ASSISTANT_DATA_VOLUME": "clm-assistant-data",
        }
        self.backups_store: dict[str, dict[str, str]] = {}
        self.images = {ref: digest("id-" + ref) for ref in OLD.values()}
        self.volume_created = "2026-11-01T00:00:00Z"
        self.counter = 0
        self.containers: dict[str, Container] = {}
        for name in self._services():
            variable = catalog.service(name).image_variable
            pin = self.env.get(variable or "", "mongo-pinned")
            self.containers[name] = Container(
                container_id=f"{name}-c0",
                image=self.images.get(pin, digest("mongo")),
                label_hash=self._hash(name),
            )
        self.registry: dict[str, dict[str, Any]] = {}

    # -- helpers -------------------------------------------------------------------------

    def _services(self) -> list[str]:
        names = ["frontend", "backend", "mongo"]
        if "assistant" in self.active:
            names.append("assistant")
        if "goldtier" in self.active:
            names += ["goldtier-egress", "goldtier-dns"]
        return names

    def _hash(self, name: str) -> str:
        variable = catalog.service(name).image_variable or ""
        return hashlib.sha256(f"{name}|{self.env.get(variable, '')}".encode()).hexdigest()[:16]

    def effects(self, *wanted: Effect) -> list[Command]:
        return [c for c in self.received if c.effect in wanted]

    def remote_text(self) -> str:
        return "\n".join(c.argv[-1] for c in self.received if c.argv[0] == "ssh")

    def recreated(self) -> list[str]:
        return [n for n, c in self.containers.items() if not c.container_id.endswith("-c0")]

    # -- runner --------------------------------------------------------------------------

    def run(self, command: Command) -> Result:
        self.received.append(command)
        if isinstance(command.stdin, Secret):
            self.stdin_seen.append(command.stdin.reveal())
        if self.on_command is not None:
            self.on_command(command)
        if command.argv[0] == "ssh":
            return self._remote(command.argv[-1])
        if command.argv[0] == "curl":
            path = (
                "/" + command.argv[-1].split("/", 3)[-1] if command.argv[-1].count("/") > 2 else "/"
            )
            expected = {p["path"]: str(p["expect_status"]) for p in self.manifest["smoke"]}
            expected.setdefault("/health", "200")
            return Result(0, self.smoke.get(path, expected.get(path, "404")))
        return self._local(command)

    def _local(self, command: Command) -> Result:
        argv = command.argv
        if argv[:3] == ("docker", "context", "inspect"):
            return Result(0, "npipe:////./pipe/fake\n")
        if argv[:3] == ("docker", "image", "inspect"):
            for image in self.manifest["images"].values():
                if argv[-1] in {image["local_ref"], image["local_image_id"]}:
                    info = {"Id": image["local_image_id"], "Os": "linux", "Architecture": "amd64"}
                    return Result(0, json.dumps(info))
            return Result(1, "", "No such image")
        if argv[:2] == ("docker", "login"):
            return Result(0, "Login Succeeded")
        if argv[:2] == ("docker", "logout"):
            return Result(0, "")
        if argv[:2] == ("docker", "tag"):
            return Result(0, "")
        if argv[:4] == ("docker", "buildx", "imagetools", "inspect"):
            entry = self.registry.get(argv[-1])
            if entry is None:
                return Result(1, "", "not found")
            return Result(0, "", raw=entry["raw"])
        if argv[:2] == ("docker", "push"):
            return self._push(argv[-1])
        return Result(1, "", f"unexpected local command: {argv[:3]}")

    push_ok: bool = True
    push_wrong_config: bool = False

    def _push(self, reference: str) -> Result:
        if not self.push_ok:
            return Result(1, "", "denied: permission_denied")
        repository = reference.rsplit(":", 1)[0]
        image = next(i for i in self.manifest["images"].values() if i["repository"] == repository)
        config = digest("other-config") if self.push_wrong_config else image["config_digest"]
        raw = json.dumps(
            {
                "schemaVersion": 2,
                "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
                "config": {"digest": config},
            }
        ).encode()
        pushed = "sha256:" + hashlib.sha256(raw).hexdigest()
        self.registry[reference] = {"raw": raw}
        self.registry[f"{repository}@{pushed}"] = {"raw": raw}
        return Result(0, f"rc: digest: {pushed} size: 1234\n")

    # -- remote --------------------------------------------------------------------------

    def _remote(self, text: str) -> Result:
        if "pgrep -fc" in text:
            return Result(0, f"ssh={self.ssh_sessions} ops=0\n")
        if text.startswith("test -e "):
            return Result(0, "held\n" if self.host_lock else "free\n")
        if text == "date -u +%s":
            return Result(0, f"{int(self.clock().timestamp())}\n")
        if "MemAvailable" in text:
            return Result(0, f"{self.mem_available}\n{self.disk_free}\n")
        if "compose version --short" in text:
            return Result(0, "5.7.0\ncompose_env=0\n")
        if "sha256sum deploy/compose.yml" in text or " && sha256sum " in text:
            lines = [
                f"{self.compose_file_override.get(e['path'], e['sha256'])}  {e['path']}"
                for e in self.manifest["compose_files"]
            ]
            return Result(0, "\n".join(lines) + "\n")
        if text.startswith("mkdir /run/lock"):
            if self.host_lock:
                return Result(1, "", "File exists")
            self.host_lock = True
            return Result(0)
        if text.startswith("rmdir /run/lock"):
            self.host_lock = False
            return Result(0)
        if "clm-ghcr.XXXXXXXX" in text:
            return self._pull(text)
        if "docker ps -a" in text:
            return Result(0, "2\n" if self.extra_backend else "1\n")
        if "docker image inspect -f" in text:
            reference = self._quoted_last(text)
            identity = self.images.get(reference)
            return Result(0, f"{identity} linux/amd64\n" if identity else "ABSENT\n")
        if "docker volume inspect" in text:
            names = [self.env["MONGO_DATA_VOLUME"]]
            if "assistant" in self.active:
                names.append(self.env["ASSISTANT_DATA_VOLUME"])
            lines = [f"{n} {self.volume_created}" for n in names if n in text]
            if "range .Mounts" in text:
                lines.append(f"{names[0]}:/data/db ")
            return Result(0, "\n".join(lines) + "\n")
        if "docker network inspect" in text:
            if "{{.Internal}}" in text:
                return Result(0, "proxy-net-1 true\n" + "\n".join(self.listening) + "\n")
            return Result(0, "proxy-net-1\n")
        if "-mmin" in text:
            return Result(0, f"{self.backups}\n")
        if "docker inspect -f" in text:
            return self._inspect(text)
        if "grep -E '^" in text:
            variable = re.search(r"grep -E '\^([A-Z_]+)='", text)
            assert variable is not None
            value = self.env.get(variable.group(1))
            return Result(0, f"{variable.group(1)}={value}\n" if value else "")
        if "stat -c" in text:
            out = f"600 root\n{len(self.env)}\n"
            if " diff " in text:
                backup = self.backups_store[sorted(self.backups_store)[-1]]
                changed = sum(1 for k in self.env if self.env[k] != backup[k])
                out += f"{2 * changed}\n"
            return Result(0, out)
        if " cp -p /etc/clm/compose.env /etc/clm/compose.env.pre-" in text:
            name = text.split()[-1]
            self.backups_store[name] = dict(self.env)
            return Result(0)
        if re.search(r"cp -p /etc/clm/compose\.env\.pre-\S+ /etc/clm/compose\.env$", text):
            self.env = dict(self.backups_store[text.split()[-2]])
            return Result(0)
        if " sed -i " in text:
            found = re.search(r"s#\^([A-Z_]+)=(\S+)\$#([A-Z_]+)=(\S+)#", text)
            assert found is not None
            if self.env.get(found.group(1)) == found.group(2):
                self.env[found.group(1)] = found.group(4)
            return Result(0)
        if "docker compose" in text:
            return self._compose(text)
        if "verify_host_firewall.sh" in text or "verify_assistant_egress.sh" in text:
            return Result(0, "verify_exit=0\n")
        return Result(1, "", f"unexpected remote command: {text[:80]}")

    @staticmethod
    def _quoted_last(text: str) -> str:
        found = re.search(r"(ghcr\.io/\S+?)(?:'|\s)", text)
        return found.group(1) if found else ""

    def _pull(self, text: str) -> Result:
        found = re.search(r"--platform linux/amd64 (\S+)", text)
        assert found is not None
        reference = found.group(1).strip("'")
        if not self.pull_ok:
            return Result(1, "login=0 pull=1 auth_dirs_left=0\n")
        registry_digest = reference.split("@", 1)[1]
        self.images[reference] = self.pull_delivers.get(reference, registry_digest)
        return Result(0, "login=0 pull=0 auth_dirs_left=0\n")

    def _inspect(self, text: str) -> Result:
        lines = []
        for name in self._services():
            container = catalog.SERVICES[name].container
            if container not in text:
                continue
            state = self.containers[name]
            label = "drifted" if name in self.drifted else state.label_hash
            lines.append(
                f"/{container} {state.container_id} {state.image} {state.started} "
                f"{state.restarts} {state.health} {label} {'true' if state.running else 'false'}"
            )
        return Result(0, "\n".join(lines) + "\n")

    def _compose(self, text: str) -> Result:
        tail = text.split(" -f ")[-1].removesuffix(" </dev/null")
        words = tail.split()[1:]
        if "| python3" in text:
            return Result(0, json.dumps(self._summary(text)))
        if words[:2] == ["config", "--quiet"]:
            return Result(0)
        if words[:2] == ["config", "--hash"]:
            names = [n for n in self._services() if n != "assistant" or "compose.assistant" in text]
            return Result(0, "\n".join(f"{n} {self._hash(n)}" for n in names) + "\n")
        service = words[-1]
        if words[0] == "stop":
            if service in self.stop_fails:
                return Result(1, "", "cannot stop")
            self.containers[service].running = False
            return Result(0)
        if words[0] == "start":
            self.containers[service].running = True
            self.containers[service].started = "2026-11-14T10:01:00Z"
            return Result(0)
        if words[0] == "up":
            return self._up(service)
        return Result(1, "", f"unexpected compose command: {words}")

    def _up(self, service: str) -> Result:
        if service in self.up_fails:
            return Result(1, "", "container is unhealthy")
        variable = catalog.service(service).image_variable
        assert variable is not None
        self.counter += 1
        self.containers[service] = Container(
            container_id=f"{service}-c{self.counter}",
            image=self.images.get(self.env[variable], digest("missing")),
            label_hash=self._hash(service),
            started="2026-11-14T10:00:30Z",
            health="unhealthy" if service in self.unhealthy_after_up else "healthy",
        )
        if self.volume_changes_after_up:
            self.volume_created = "2026-11-14T10:00:31Z"
        return Result(0)

    def _summary(self, text: str) -> dict[str, Any]:
        set_name = catalog.resolve_overlay_files(tuple(re.findall(r"-f (\S+\.yml)", text)))
        summary: dict[str, Any] = copy.deepcopy(render.load_baseline()[set_name])
        for name, body in summary["services"].items():
            variable = catalog.service(name).image_variable
            body["image"] = self.env.get(variable or "", "")
            if self.host_summary_extra_network and name in self.manifest["services_changed"]:
                body["networks"].append(self.host_summary_extra_network)
        return summary


def make_context(
    manifest: dict[str, Any],
    tmp_path: Path,
    *,
    mode: Mode = Mode.EXECUTE,
    approval: dict[str, Any] | None | bool = True,
    world: FakeWorld | None = None,
    host_reads: bool = True,
    transfer: str = "pull",
) -> Any:
    """A deploy ``Context`` wired to a ``FakeWorld``. Returns ``(ctx, world)``."""

    from tools.release import credstore, deploy, records

    world = world or FakeWorld(manifest, active=tuple(manifest["overlay"]["active_host_overlays"]))
    clock = world.clock
    log = AuditLog(path=tmp_path / "audit.jsonl", clock=clock)
    gate = Gate(world, mode, log, host_reads=host_reads)
    profile = catalog.HostProfile(backup_glob="/var/backups/clm-test")
    host = Host(gate, SshTarget("operator@host.test.invalid"), profile)
    store = credstore.MemoryStore()
    stamp = "%Y-%m-%dT%H:%M:%SZ"
    for identity in ("pull", "publish"):
        meta = {
            "username": "release-bot",
            "created_at": (NOW - timedelta(days=1)).strftime(stamp),
            "expires_at": (NOW + timedelta(days=20)).strftime(stamp),
        }
        store.write(credstore.TARGET_PREFIX + identity, json.dumps(meta), sentinel_token(identity))
    record = make_approval(manifest) if approval is True else (approval or None)
    ctx = deploy.Context(
        gate=gate,
        host=host,
        manifest=manifest,
        store=records.StateStore(tmp_path / "state", clock),
        root=REPO,
        transfer=transfer,
        approval=record,
        credentials=store,
        clock=clock,
    )
    return ctx, world
