"""Plan, preflight, apply, verify and roll back one approved release on the single host.

The applier changes only the services the approval names, one at a time, with
``up -d --no-build --no-deps --wait <service>``. It never runs ``down``, ``-v``,
``--remove-orphans`` or a volume removal, and it never starts a second backend. Every step
before the first ``up`` fails back to "nothing changed". After a container has changed, a
failure is rolled back only where the manifest proves data compatibility and the owner
approved automatic rollback; otherwise the run stops and holds for an owner decision.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

from . import approval as approvals
from . import catalog, credstore, records, registry, render
from .core import (
    Clock,
    Command,
    Effect,
    Gate,
    Mode,
    ReleaseError,
    StopCondition,
    format_utc,
    parse_utc,
    utc_now,
)
from .host import ContainerState, Host, SshTarget, safe
from .manifest import (
    Manifest,
    image_reference,
    manifest_hash,
    require_deployable,
    rollback_eligibility,
    validate_manifest,
)

PASS, FAIL, SKIPPED = "PASS", "FAIL", "SKIPPED"
PUBLIC_PORTS = frozenset({22, 80, 443})
MIN_COMPOSE = (2, 30)
STATEFUL_NEIGHBOURS = ("mongo",)


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str = ""


@dataclass
class Context:
    gate: Gate
    host: Host
    manifest: Manifest
    store: records.StateStore
    root: Path
    transfer: str = "pull"
    approval: approvals.Approval | None = None
    credentials: credstore.CredentialStore | None = None
    clock: Clock = utc_now
    baseline: dict[str, Any] = field(default_factory=dict)

    @property
    def changed(self) -> list[str]:
        return [s for s in catalog.DEPLOY_ORDER if s in self.manifest["services_changed"]]

    @property
    def active(self) -> tuple[str, ...]:
        return tuple(self.manifest["overlay"]["active_host_overlays"])

    def running_services(self) -> list[str]:
        services = ["frontend", "backend", "mongo"]
        if "assistant" in self.active:
            services.append("assistant")
        if "goldtier" in self.active:
            services += ["goldtier-egress", "goldtier-dns"]
        return services

    def wrapper(self, service: str) -> str:
        return catalog.wrapper_set_for(service, self.active)


# --------------------------------------------------------------------------------------------
# Plan
# --------------------------------------------------------------------------------------------


def build_plan(
    manifest: Manifest, *, transfer: str, profile: catalog.HostProfile
) -> dict[str, Any]:
    """Exactly which services would change, which must not, and the host commands in order.

    Pure: needs no host, registry or approval. References are shown as they will be once the
    registry digest is known.
    """

    validate_manifest(manifest)
    if transfer not in {"pull", "load"}:
        raise ReleaseError("TRANSFER_UNKNOWN", "transfer must be pull or load")
    active = tuple(manifest["overlay"]["active_host_overlays"])
    changed = [s for s in catalog.DEPLOY_ORDER if s in manifest["services_changed"]]
    unsupported = [s for s in manifest["services_changed"] if s not in changed]
    if unsupported:
        raise StopCondition(
            "SERVICE_NOT_AUTOMATED", f"{unsupported[0]} is never changed by the automated applier"
        )
    running = ["frontend", "backend", "mongo"]
    running += ["assistant"] if "assistant" in active else []
    running += ["goldtier-egress", "goldtier-dns"] if "goldtier" in active else []
    must_not_change = [s for s in running if s not in changed]
    planner = Host(Gate(_NoRunner(), Mode.PLAN_ONLY, _silent_log()), SshTarget("HOST"), profile)
    steps: list[dict[str, str]] = []
    services: list[dict[str, Any]] = []
    for name in changed:
        svc = catalog.service(name)
        wrapper = catalog.wrapper_set_for(name, active)
        digest = manifest["images"][name]["registry_manifest_digest"]
        reference = (
            image_reference(manifest, name, transfer=transfer)
            if transfer == "load" or digest
            else f"{svc.repository}@<registry digest: unknown until published>"
        )
        eligible, reason = rollback_eligibility(manifest, name)
        services.append(
            {
                "service": name,
                "container": svc.container,
                "compose_env_line": svc.image_variable,
                "new_reference": reference,
                "wrapper_overlay_set": wrapper,
                "overlay_files": list(catalog.overlay_files(wrapper)),
                "rollback": manifest["rollback"][name],
                "automatic_rollback_eligible": eligible,
                "automatic_rollback_reason": reason,
            }
        )
    steps.append({"step": "preflight", "effect": "read", "command": "(read-only checks)"})
    steps.append(
        {
            "step": "transfer",
            "effect": "write",
            "command": f"{transfer} each approved image and verify its identity",
        }
    )
    steps.append(
        {
            "step": "backup",
            "effect": "write",
            "command": (
                f"sudo -n cp -p {profile.compose_env} {profile.compose_env}.pre-<release>-<utc>"
            ),
        }
    )
    for entry in services:
        steps.append(
            {
                "step": f"pin {entry['service']}",
                "effect": "write",
                "command": f"replace the single line {entry['compose_env_line']}=... with "
                f"{entry['new_reference']}",
            }
        )
    for wrapper in sorted({e["wrapper_overlay_set"] for e in services} | {"base"}):
        steps.append(
            {"step": "validate", "effect": "read", "command": planner.compose_config_quiet(wrapper)}
        )
    if "backend" in changed:
        steps.append(
            {
                "step": "stop ingress",
                "effect": "write",
                "command": planner.compose_stop("base", "frontend"),
            }
        )
        steps.append(
            {
                "step": "stop old backend",
                "effect": "write",
                "command": planner.compose_stop(
                    catalog.wrapper_set_for("backend", active), "backend"
                ),
            }
        )
    for entry in services:
        steps.append(
            {
                "step": f"apply {entry['service']}",
                "effect": "write",
                "command": planner.compose_up(entry["wrapper_overlay_set"], entry["service"]),
            }
        )
    if "backend" in changed and "frontend" not in changed:
        steps.append(
            {
                "step": "restore ingress",
                "effect": "write",
                "command": planner.compose_start("base", "frontend"),
            }
        )
    steps.append(
        {
            "step": "verify",
            "effect": "read",
            "command": "container identity, image, health, volumes, networks, public smoke",
        }
    )
    steps.append(
        {
            "step": "browser acceptance",
            "effect": "owner",
            "command": "the owner completes the runsheet; nothing else runs meanwhile",
        }
    )
    return {
        "release_id": manifest["release_id"],
        "manifest_sha256": manifest_hash(manifest),
        "risk_class": manifest["risk_class"],
        "risk_reasons": manifest["risk_reasons"],
        "transfer": transfer,
        "services_change": services,
        "services_must_not_change": must_not_change,
        "deploy_order": changed,
        "rollback_order": [s for s in catalog.ROLLBACK_ORDER if s in changed],
        "ingress_interruption": "backend" in changed,
        "host_steps": steps,
        "never": [
            "compose down",
            "-v / --volumes",
            "--remove-orphans",
            "volume removal",
            "compose rm",
            "a second backend",
            "a rebuild",
            "a floating tag",
        ],
        "stop_conditions": stop_conditions(manifest),
        "smoke": manifest["smoke"],
    }


def stop_conditions(manifest: Manifest) -> list[str]:
    conditions = [
        "approval missing, for another manifest, for other services, not yet valid or expired",
        "any preflight check fails (nothing has changed)",
        "an image on the host is not the approved digest (nothing has changed)",
        "compose.env differs from the expected single-line change (restored, nothing changed)",
        "a service that must not change would be recreated (restored, nothing changed)",
        "a container other than the approved ones changes during the run",
        "a data volume or the proxy network changes identity",
        "more than one backend container exists",
        "a health check or public smoke request fails",
    ]
    for name in manifest["services_changed"]:
        for item in manifest["rollback"][name]["stop_conditions"]:
            conditions.append(f"{name}: {item}")
    return conditions


class _NoRunner:
    def run(self, command: Command) -> Any:  # pragma: no cover - never reached in plan mode
        raise StopCondition("PLAN_ONLY", "a plan never executes a command")


def _silent_log() -> Any:
    from .core import AuditLog

    return AuditLog()


# --------------------------------------------------------------------------------------------
# Preflight (read-only)
# --------------------------------------------------------------------------------------------


def _int(text: str) -> int | None:
    found = re.search(r"-?\d+", text)
    return int(found.group()) if found else None


def preflight(ctx: Context) -> list[CheckResult]:
    """Read-only host checks. A skipped read (plan or offline dry-run) is reported as SKIPPED."""

    host, profile, results = ctx.host, ctx.host.profile, []

    def add(name: str, ok: bool | None, detail: str = "") -> None:
        results.append(CheckResult(name, SKIPPED if ok is None else PASS if ok else FAIL, detail))

    lone = host.read(
        "echo \"ssh=$(pgrep -fc '^sshd(-session)?: [^ ]+@' || true) "
        "ops=$(pgrep -fc '[d]ocker compose|[d]ocker pull|[d]ocker load|[m]ongodump' || true)\"",
        "confirm this is the only operator session",
    )
    if lone.skipped:
        add("sole-operator", None)
    else:
        found = re.search(r"ssh=(\d+) ops=(\d+)", lone.stdout)
        ok = bool(found) and found is not None and found.group(1) == "1" and found.group(2) == "0"
        add("sole-operator", ok, lone.stdout.strip())

    lock = host.read(
        f"test -e {shlex.quote(profile.lock_dir)} && echo held || echo free",
        "check the host release lock",
    )
    add(
        "no-overlapping-release",
        None if lock.skipped else lock.stdout.strip() == "free",
        lock.stdout.strip(),
    )

    clock = host.read("date -u +%s", "read the host clock")
    if clock.skipped:
        add("clock", None)
    else:
        remote = _int(clock.stdout)
        drift = None if remote is None else abs(remote - int(ctx.clock().timestamp()))
        add("clock", drift is not None and drift <= 120, f"drift {drift}s")

    capacity = host.read(
        "awk '/^MemAvailable/{print $2}' /proc/meminfo; "
        "df -Pk /var/lib/docker | awk 'NR==2{print $4}'",
        "read free memory and disk",
    )
    if capacity.skipped:
        add("capacity", None)
    else:
        numbers = [int(n) for n in re.findall(r"^\d+$", capacity.stdout, re.MULTILINE)]
        ok = (
            len(numbers) == 2
            and numbers[0] >= profile.min_mem_available_kb
            and numbers[1] >= profile.min_disk_free_kb
        )
        add("capacity", ok, f"MemAvailable_kB,disk_free_kB={numbers}")

    version = host.read(
        "sudo -n docker compose version --short; "
        "echo compose_env=$( (env; sudo -n env) 2>/dev/null | grep -c '^COMPOSE_' || true)",
        "read the Compose version and COMPOSE_ variables",
    )
    if version.skipped:
        add("compose", None)
    else:
        parts = re.match(r"v?(\d+)\.(\d+)", version.stdout.strip())
        ok = (
            parts is not None
            and (int(parts.group(1)), int(parts.group(2))) >= MIN_COMPOSE
            and "compose_env=0" in version.stdout
        )
        add("compose", ok, version.stdout.strip().replace("\n", " "))

    files = host.read(
        f"cd {shlex.quote(profile.workdir)} && sha256sum "
        + " ".join(shlex.quote(e["path"]) for e in ctx.manifest["compose_files"]),
        "hash the installed Compose files",
    )
    if files.skipped:
        add("compose-files", None)
    else:
        seen = {
            line.split()[1].lstrip("*"): line.split()[0]
            for line in files.stdout.splitlines()
            if len(line.split()) == 2
        }
        wrong = [
            e["path"] for e in ctx.manifest["compose_files"] if seen.get(e["path"]) != e["sha256"]
        ]
        add(
            "compose-files",
            not wrong,
            "installed files equal the manifest" if not wrong else f"differs: {wrong[0]}",
        )

    states = host.container_states(ctx.running_services())
    if not states:
        add("containers", None)
        add("no-drift", None)
    else:
        bad = [
            name
            for name, state in states.items()
            if not (state.present and state.running and state.health == "healthy")
        ]
        add(
            "containers",
            not bad,
            "all running and healthy" if not bad else f"not healthy: {bad[0]}",
        )
        add("no-drift", *_drift(ctx, states))
        ctx.baseline["states"] = states

    add("volumes", *_volumes(ctx))
    add("backups", *_backups(ctx))
    add("images-and-rollback", *_image_state(ctx))
    add("network-boundaries", *_boundaries(ctx))

    health = ctx.gate.run(_curl(profile.site + "/health", "GET"))
    add(
        "public-health",
        None if health.skipped else health.stdout.strip() == "200",
        f"/health={health.stdout.strip()}",
    )
    return results


def _curl(url: str, method: str) -> Command:
    return Command(
        (
            "curl",
            "-s",
            "-o",
            "NUL" if _windows() else "/dev/null",
            "-m",
            "15",
            "-w",
            "%{http_code}",
            "-X",
            method,
            url,
        ),
        Effect.PUBLIC_READ,
        f"{method} {url}",
        timeout=30,
    )


def _windows() -> bool:
    import sys

    return sys.platform == "win32"


def _hashes(ctx: Context, set_name: str) -> dict[str, str] | None:
    result = ctx.host.read(
        ctx.host.compose_hashes(set_name), f"read {set_name} service hashes", quiet=True
    )
    if result.skipped:
        return None
    if result.returncode != 0:
        raise StopCondition("HOST_CONFIG_INVALID", f"Compose refused the {set_name} configuration")
    return dict(line.split()[:2] for line in result.stdout.splitlines() if len(line.split()) >= 2)


def _drift(ctx: Context, states: dict[str, ContainerState]) -> tuple[bool | None, str]:
    """Every running service must already equal what its wrapper renders: no hidden drift."""

    cache: dict[str, dict[str, str] | None] = {}
    for name, state in states.items():
        if not state.present:
            continue
        wrapper = ctx.wrapper(name)
        if wrapper not in cache:
            cache[wrapper] = _hashes(ctx, wrapper)
        hashes = cache[wrapper]
        if hashes is None:
            return None, ""
        if hashes.get(name) != state.config_hash:
            return False, f"{name} differs from its rendered configuration before any change"
    return True, "running containers equal their rendered configuration"


def _volumes(ctx: Context) -> tuple[bool | None, str]:
    variables = ["MONGO_DATA_VOLUME"]
    if "assistant" in ctx.active:
        variables.append("ASSISTANT_DATA_VOLUME")
    names: list[str] = []
    for variable in variables:
        value = ctx.host.env_value(variable)
        if value is None:
            return (None, "") if ctx.gate.mode is not Mode.EXECUTE else (False, f"{variable} unset")
        names.append(safe(value))
    result = ctx.host.read(
        "sudo -n docker volume inspect -f '{{.Name}} {{.CreatedAt}}' "
        + " ".join(shlex.quote(n) for n in names)
        + "; sudo -n docker inspect -f '{{range .Mounts}}{{.Name}}:{{.Destination}} {{end}}' "
        + shlex.quote(ctx.host.profile.containers["mongo"]),
        "read data volume identities",
    )
    if result.skipped:
        return None, ""
    lines = result.stdout.splitlines()
    identities = [line for line in lines if line.split()[:1] and line.split()[0] in names]
    mounted = any(f"{names[0]}:/data/db" in line for line in lines)
    ok = result.returncode == 0 and len(identities) == len(names) and mounted
    ctx.baseline["volumes"] = sorted(identities)
    ctx.baseline["volume_names"] = names
    return ok, f"{len(identities)} volume(s) present; Mongo data mounted={mounted}"


def _read_volumes(ctx: Context) -> list[str] | None:
    names = ctx.baseline.get("volume_names")
    if not names:
        return None
    result = ctx.host.read(
        "sudo -n docker volume inspect -f '{{.Name}} {{.CreatedAt}}' "
        + " ".join(shlex.quote(n) for n in names),
        "re-read data volume identities",
    )
    return None if result.skipped else sorted(result.stdout.splitlines())


def _backups(ctx: Context) -> tuple[bool | None, str]:
    stateful = [s for s in ctx.changed if catalog.service(s).stateful]
    if not stateful:
        return None, "not required: no stateful service changes"
    location = ctx.host.profile.backup_glob
    if location is None:
        return False, "backup location is not configured; a stateful release is refused"
    minutes = ctx.host.profile.max_backup_age_hours * 60
    result = ctx.host.read(
        f"sudo -n find {shlex.quote(location)} -maxdepth 1 -type f -mmin -{minutes} | wc -l",
        "count recent backups",
    )
    if result.skipped:
        return None, ""
    count = _int(result.stdout) or 0
    return count >= 1, f"{count} backup file(s) newer than {ctx.host.profile.max_backup_age_hours}h"


def _image_state(ctx: Context) -> tuple[bool | None, str]:
    """The host must be where the manifest assumes, and each rollback image must be present."""

    pins: dict[str, str] = {}
    for name in ctx.changed:
        variable = catalog.service(name).image_variable
        assert variable is not None
        current = ctx.host.env_value(variable)
        if current is None:
            return (None, "") if ctx.gate.mode is not Mode.EXECUTE else (False, f"{variable} unset")
        if "@sha256:" not in current and not re.search(r":rc-[0-9a-f]{12}-[0-9a-f]{12}$", current):
            return False, f"{name}: the current pin is a floating reference"
        entry = ctx.manifest["rollback"][name]
        if entry["target_image"] is not None and entry["target_image"] != current:
            return False, f"{name}: the host is not at the rollback target the manifest names"
        if name == "backend" and not entry.get("target_confirmed_on_host", False):
            return False, "backend: the running backend's identity and schema are not confirmed"
        if ctx.host.image_id(current) is None:
            return False, f"{name}: the rollback image is not cached on the host"
        pins[name] = current
    for link in ctx.manifest["coupling"]:
        if link["satisfied_by"] != "already-deployed":
            continue
        variable = catalog.service(link["requires"]).image_variable
        assert variable is not None
        deployed = ctx.host.env_value(variable) or ""
        if not deployed.endswith(str(link["deployed_image"])):
            return False, f"{link['service']} needs a {link['requires']} that is not deployed"
    ctx.baseline["pins"] = pins
    return True, "current pins recorded; rollback images cached"


def _boundaries(ctx: Context) -> tuple[bool | None, str]:
    profile = ctx.host.profile
    result = ctx.host.read(
        f"sudo -n docker network inspect -f '{{{{.Id}}}} {{{{.Internal}}}}' "
        f"{shlex.quote(profile.proxy_network)}; sudo -n ss -Htln | awk '{{print $4}}'",
        "read the proxy network and listening sockets",
    )
    if result.skipped:
        return None, ""
    lines = result.stdout.split()
    if len(lines) < 2 or lines[1] != "true":
        return False, "the proxy network is missing or not internal"
    ctx.baseline["proxy_network"] = lines[0]
    exposed = set()
    for address in lines[2:]:
        host_part, _, port = address.rpartition(":")
        if host_part.startswith(("127.", "[::1]")) or not port.isdigit():
            continue
        exposed.add(int(port))
    if exposed - PUBLIC_PORTS:
        return False, f"unexpected listening port {sorted(exposed - PUBLIC_PORTS)[0]}"
    scripts = []
    if "goldtier" in ctx.active:
        scripts.append("deploy/egress/host/verify_host_firewall.sh")
    if "assistant-provider" in ctx.active:
        scripts.append("apps/assistant/deploy/egress/verify_assistant_egress.sh")
    for script in scripts:
        verify = ctx.host.read(
            f"cd {shlex.quote(profile.workdir)} && "
            f"sudo -n bash {shlex.quote(script)} >/dev/null 2>&1; "
            "echo verify_exit=$?",
            f"run {Path(script).name} (read-only)",
            timeout=180,
        )
        if "verify_exit=0" not in verify.stdout:
            return False, f"{Path(script).name} did not pass"
    return True, f"proxy internal; public ports {sorted(exposed)}; {len(scripts)} firewall check(s)"


# --------------------------------------------------------------------------------------------
# Apply
# --------------------------------------------------------------------------------------------


@dataclass
class RunState:
    backup: str = ""
    pins_before: dict[str, str] = field(default_factory=dict)
    references: dict[str, str] = field(default_factory=dict)
    host_image_ids: dict[str, str] = field(default_factory=dict)
    applied: list[str] = field(default_factory=list)
    env_changed: bool = False
    ingress_stopped: bool = False
    events: list[str] = field(default_factory=list)


def run(ctx: Context) -> dict[str, Any]:
    """Dry-run or execute one release. Returns the result record that was stored.

    A result is written on every exit path, including an interrupt or an unexpected error, so
    a run that touched the host never ends without a record.
    """

    manifest, mode = ctx.manifest, ctx.gate.mode
    if mode is Mode.PLAN_ONLY:
        raise ReleaseError("MODE", "use build_plan for plan-only")
    with ctx.store.lock(manifest["release_id"]):
        state = RunState()
        try:
            outcome = _run_locked(ctx, state)
        except StopCondition as stop:
            outcome = _handle_stop(ctx, state, stop)
        except BaseException as crash:
            _record(ctx, state, _interrupted(state, crash))
            raise
        return _record(ctx, state, outcome)


def _record(ctx: Context, state: RunState, outcome: dict[str, Any]) -> dict[str, Any]:
    outcome.update(
        {
            "release_id": ctx.manifest["release_id"],
            "manifest_sha256": manifest_hash(ctx.manifest),
            "mode": ctx.gate.mode.value,
            "transfer": ctx.transfer,
            "services": ctx.changed,
            "applied": list(state.applied),
            "env_backup": state.backup,
            "pins_before": state.pins_before,
            "references": state.references,
            "events": state.events,
            "approval_id": (ctx.approval or {}).get("approval_id"),
        }
    )
    ctx.store.write_result(ctx.manifest["release_id"], outcome)
    return outcome


def _interrupted(state: RunState, crash: BaseException) -> dict[str, Any]:
    """The record for a run that ended without a decision (Ctrl-C, a killed tool, a defect)."""

    touched = state.env_changed or bool(state.applied) or state.ingress_stopped
    state.events.append(f"INTERRUPTED by {type(crash).__name__}")
    outcome: dict[str, Any] = {
        "state": records.FAILED_HELD if touched else records.FAILED_NO_CHANGE,
        "stop_code": "INTERRUPTED",
        "stop_message": f"the run ended unexpectedly ({type(crash).__name__})",
    }
    if touched:
        outcome["held_reason"] = (
            "the run was interrupted after it began changing the host; the host state is not "
            "verified. Follow 'After an interrupted run' in the runbook before anything else"
        )
        outcome["ingress_stopped"] = state.ingress_stopped
    return outcome


def _handle_stop(ctx: Context, state: RunState, stop: StopCondition) -> dict[str, Any]:
    try:
        return _stopped(ctx, state, stop)
    except StopCondition as second:
        state.events.append(f"STOP WHILE HANDLING A STOP {second.code}: {second.message}")
        return {
            "state": records.FAILED_HELD,
            "stop_code": stop.code,
            "stop_message": stop.message,
            "held_reason": f"failure handling was itself stopped: {second.code}",
            "ingress_stopped": state.ingress_stopped,
        }


def _run_locked(ctx: Context, state: RunState) -> dict[str, Any]:
    manifest, gate, host = ctx.manifest, ctx.gate, ctx.host
    execute = gate.mode is Mode.EXECUTE
    validate_manifest(manifest)
    plan = build_plan(manifest, transfer=ctx.transfer, profile=host.profile)
    if execute or ctx.approval is not None:
        if ctx.approval is None:
            raise StopCondition("APPROVAL_MISSING", "no owner approval record was supplied")
        approvals.check_approval(
            ctx.approval,
            manifest,
            action="deploy",
            services=ctx.changed,
            clock=ctx.clock,
            consumed=ctx.store.consumed_approvals() if execute else frozenset(),
        )
        gate.set_deadline(approvals.deadline(ctx.approval, ctx.clock))
    if execute:
        require_deployable(manifest, transfer=ctx.transfer)
        _require_window(ctx)
    state.events.append("approval and manifest accepted")

    sets = render.validate_release_config(gate, ctx.root, manifest)
    state.events.append(f"effective configuration validated offline for {', '.join(sets)}")

    checks = preflight(ctx)
    failed = [c for c in checks if c.status == FAIL]
    if execute:
        # Only the backup check may be skipped (no stateful service); an unread check is a stop.
        failed += [c for c in checks if c.status == SKIPPED and c.name != "backups"]
    if failed:
        detail = failed[0].detail or "the check could not be read"
        raise StopCondition("PREFLIGHT_FAILED", f"{failed[0].name}: {detail}")
    state.pins_before = dict(ctx.baseline.get("pins", {}))
    state.events.append(f"preflight {sum(c.status == PASS for c in checks)} passed")

    locked = host.write(f"mkdir {shlex.quote(host.profile.lock_dir)}", "take the host release lock")
    if not locked.skipped and locked.returncode != 0:
        raise StopCondition("RELEASE_IN_PROGRESS", "another release holds the host lock")
    try:
        _transfer(ctx, state)
        if execute:
            # Single use: from the first change to the host's configuration onwards, this
            # approval cannot start another run. A stop before this point may be retried.
            ctx.store.consume_approval(ctx.approval["approval_id"], "deploy")  # type: ignore[index]
        _pin_images(ctx, state)
        _validate_on_host(ctx, state)
        for name in ctx.changed:
            _apply_service(ctx, state, name)
        if state.ingress_stopped:
            _restore_ingress(ctx, state)
        _smoke(ctx, state)
        _verify_stable(ctx, state)
    finally:
        host.write(
            f"rmdir {shlex.quote(host.profile.lock_dir)} 2>/dev/null || true",
            "release the host release lock",
            housekeeping=True,
        )
    if not execute:
        return {
            "state": records.DRY_RUN_OK,
            "preflight": [c.__dict__ for c in checks],
            "plan": plan,
            "would_issue": [{"effect": c.effect.value, "purpose": c.purpose} for c in gate.skipped],
        }
    return {
        "state": records.DEPLOYED_AWAITING_ACCEPTANCE,
        "preflight": [c.__dict__ for c in checks],
        "deployed_at": format_utc(ctx.clock()),
        "next": "owner browser acceptance; then run the accept command",
    }


def _require_window(ctx: Context) -> None:
    """Refuse to start changing the host when the window cannot cover the whole run."""

    assert ctx.approval is not None
    needed = timedelta(seconds=600 + 2 * ctx.host.profile.wait_timeout_seconds * len(ctx.changed))
    if parse_utc(ctx.approval["expires_at"]) - ctx.clock() < needed:
        raise StopCondition(
            "APPROVAL_WINDOW_TOO_SHORT",
            "not enough of the approval window is left to finish and verify the release",
        )


def _transfer(ctx: Context, state: RunState) -> None:
    for name in ctx.changed:
        if ctx.transfer == "pull":
            if ctx.gate.mode is Mode.EXECUTE:
                if ctx.credentials is None:
                    raise StopCondition("CREDENTIAL_MISSING", "no credential store is configured")
                credential = credstore.fetch(ctx.credentials, "pull", ctx.clock)
                reference = registry.host_pull(ctx.host, ctx.manifest, name, credential)
            else:
                digest = ctx.manifest["images"][name]["registry_manifest_digest"]
                reference = (
                    image_reference(ctx.manifest, name, transfer="pull")
                    if digest
                    else f"{catalog.service(name).repository}@unpublished"
                )
                ctx.gate.run(
                    Command(
                        ctx.host._argv("(pull by digest with a temporary configuration)"),
                        Effect.HOST_WRITE,
                        f"pull {name} by digest on the host",
                    )
                )
        else:
            reference = registry.host_load(ctx.gate, ctx.host, ctx.manifest, name)
        state.references[name] = reference
        if ctx.gate.mode is Mode.EXECUTE:
            identity = ctx.host.image_id(reference)
            if identity is None:
                raise StopCondition("IMAGE_PULL_FAILED", f"{name}: image missing after transfer")
            state.host_image_ids[name] = identity
        state.events.append(f"{name}: image present on the host and verified")


def _pin_images(ctx: Context, state: RunState) -> None:
    """Back up compose.env and replace exactly one line per changed service."""

    host, env_file = ctx.host, shlex.quote(ctx.host.profile.compose_env)
    stamp = ctx.clock().strftime("%Y%m%dT%H%M%SZ")
    backup = f"{ctx.host.profile.compose_env}.pre-{safe(ctx.manifest['release_id'])}-{stamp}"
    before = host.read(
        f"sudo -n stat -c '%a %U' {env_file}; sudo -n grep -c . {env_file}",
        "read compose.env mode and line count",
    )
    made = host.write(
        f"sudo -n test ! -e {shlex.quote(backup)} && "
        f"sudo -n cp -p {env_file} {shlex.quote(backup)}",
        "back up compose.env",
    )
    if not made.skipped and made.returncode != 0:
        raise StopCondition("ENV_BACKUP_FAILED", "compose.env could not be backed up")
    state.backup = backup
    for name in ctx.changed:
        variable = catalog.service(name).image_variable
        assert variable is not None
        old = state.pins_before.get(name)
        new = safe(state.references[name])
        if old is None:
            if ctx.gate.mode is Mode.EXECUTE:
                raise StopCondition("HOST_STATE_UNEXPECTED", f"{name}: current pin unknown")
            old = "<current pin>"
        elif old == new:
            raise StopCondition("NOTHING_TO_DEPLOY", f"{name} is already at the approved image")
        else:
            safe(old)
        edited = host.write(
            f"sudo -n sed -i 's#^{variable}={old}$#{variable}={new}#' {env_file}",
            f"pin {name} to the approved image",
        )
        state.env_changed = state.env_changed or not edited.skipped
        if not edited.skipped and edited.returncode != 0:
            raise StopCondition("ENV_EDIT_FAILED", f"{name}: compose.env was not updated")
    if ctx.gate.mode is not Mode.EXECUTE:
        return
    after = host.read(
        f"sudo -n stat -c '%a %U' {env_file}; sudo -n grep -c . {env_file}; "
        f"sudo -n diff {shlex.quote(backup)} {env_file} | grep -c '^[<>]' || true",
        "verify the compose.env change",
    )
    expected = before.stdout.split() + [str(2 * len(ctx.changed))]
    if after.stdout.split() != expected:
        raise StopCondition(
            "ENV_EDIT_UNEXPECTED", "compose.env does not show exactly one changed line per service"
        )
    for name in ctx.changed:
        variable = catalog.service(name).image_variable
        assert variable is not None
        if ctx.host.env_value(variable) != state.references[name]:
            raise StopCondition("ENV_EDIT_UNEXPECTED", f"{name}: the pin was not written")
    state.events.append(f"compose.env updated ({len(ctx.changed)} line(s)); backup kept")


def _validate_on_host(ctx: Context, state: RunState) -> None:
    """Before any container changes: only the approved services may differ from what runs."""

    host, execute = ctx.host, ctx.gate.mode is Mode.EXECUTE
    wrappers = sorted({ctx.wrapper(s) for s in ctx.running_services()})
    states: dict[str, ContainerState] = ctx.baseline.get("states", {})
    for wrapper in wrappers:
        quiet = host.read(host.compose_config_quiet(wrapper), f"validate {wrapper} configuration")
        if not quiet.skipped and quiet.returncode != 0:
            raise StopCondition(
                "HOST_CONFIG_INVALID", f"Compose refused the {wrapper} configuration"
            )
        hashes = _hashes(ctx, wrapper)
        if hashes is None:
            continue
        for name, current in states.items():
            if not current.present or ctx.wrapper(name) != wrapper:
                continue
            same = hashes.get(name) == current.config_hash
            if name in ctx.changed and same and execute:
                raise StopCondition("NOTHING_TO_DEPLOY", f"{name} would not be recreated")
            if name not in ctx.changed and not same:
                raise StopCondition(
                    "UNAUTHORISED_SERVICE_CHANGE",
                    f"{name} would be recreated but is not in the approved service list",
                )
    for name in ctx.changed:
        wrapper = ctx.wrapper(name)
        result = host.read(
            host.compose_summary(wrapper), f"summarise {wrapper} on the host", quiet=True
        )
        if result.skipped:
            continue
        import json

        try:
            summary = json.loads(result.stdout)
        except ValueError as exc:
            raise StopCondition("HOST_CONFIG_INVALID", "the host summary is unreadable") from exc
        problems = render.invariant_violations(wrapper, summary)
        body = summary["services"].get(name, {})
        if execute and body.get("image") != state.references[name]:
            problems.append(f"{name}: effective image is not the approved reference")
        reference = render.load_baseline()[wrapper]["services"][name]
        declared = ctx.manifest["declared_config_changes"].get(name, {})
        for kind in ("networks", "ports"):
            extra = set(body.get(kind, [])) - set(reference[kind]) - set(declared.get(kind, []))
            if extra:
                problems.append(f"{name}: undeclared {kind} entry {sorted(extra)[0]}")
        if problems:
            raise StopCondition("EFFECTIVE_CONFIG_UNDECLARED", "; ".join(problems[:4]))
    state.events.append("host configuration validated: only approved services differ")


def _others_unchanged(ctx: Context, exempt: set[str]) -> None:
    before: dict[str, ContainerState] = ctx.baseline.get("states", {})
    now = ctx.host.container_states(ctx.running_services())
    for name, old in before.items():
        if name in exempt or name not in now:
            continue
        if now[name].identity() != old.identity():
            raise StopCondition(
                "UNAUTHORISED_SERVICE_CHANGE", f"{name} changed although it must not"
            )
    volumes = _read_volumes(ctx)
    if volumes is not None and volumes != ctx.baseline.get("volumes"):
        raise StopCondition("VOLUME_IDENTITY_CHANGED", "a data volume changed identity")
    network = ctx.host.read(
        f"sudo -n docker network inspect -f '{{{{.Id}}}}' "
        f"{shlex.quote(ctx.host.profile.proxy_network)}",
        "re-read the proxy network identity",
    )
    if not network.skipped and network.stdout.strip() != ctx.baseline.get("proxy_network"):
        raise StopCondition("NETWORK_IDENTITY_CHANGED", "the proxy network was recreated")


def _apply_service(ctx: Context, state: RunState, name: str) -> None:
    host, wrapper = ctx.host, ctx.wrapper(name)
    before: dict[str, ContainerState] = ctx.baseline.get("states", {})
    if name == "backend":
        stopped = host.write(
            host.compose_stop("base", "frontend"), "stop ingress before the backend"
        )
        state.ingress_stopped = not stopped.skipped
        if not stopped.skipped and stopped.returncode != 0:
            raise StopCondition("APPLY_FAILED", "ingress could not be stopped")
        halted = host.write(host.compose_stop(wrapper, "backend"), "stop the old backend writer")
        if not halted.skipped and halted.returncode != 0:
            raise StopCondition("APPLY_FAILED", "the old backend could not be stopped")
    result = host.write(
        host.compose_up(wrapper, name),
        f"recreate {name} only",
        timeout=host.profile.wait_timeout_seconds + 120,
    )
    if result.skipped:
        state.events.append(f"{name}: would be recreated (not executed)")
        return
    state.applied.append(name)
    if result.returncode != 0:
        raise StopCondition(
            "APPLY_FAILED", f"{name}: up did not complete or did not become healthy"
        )
    now = host.container_states(ctx.running_services())
    current = now[name]
    old = before.get(name)
    if old is not None and old.present and current.container_id == old.container_id:
        raise StopCondition("APPLY_FAILED", f"{name} was not recreated")
    if not (current.running and current.health == "healthy" and current.restarts == 0):
        raise StopCondition("HEALTH_CHECK_FAILED", f"{name} is not healthy after the change")
    if current.image != state.host_image_ids[name]:
        raise StopCondition("WRONG_DIGEST", f"{name} is not running the approved image")
    if name == "backend":
        count = host.read(
            "sudo -n docker ps -a --filter label=com.docker.compose.project="
            f"{shlex.quote(host.profile.project)} "
            "--filter label=com.docker.compose.service=backend "
            "--format '{{.ID}}' | wc -l",
            "count backend containers",
        )
        if _int(count.stdout) != 1:
            raise StopCondition("SECOND_BACKEND", "there is not exactly one backend container")
    exempt = set(state.applied) | ({"frontend"} if state.ingress_stopped else set())
    _others_unchanged(ctx, exempt)
    state.events.append(f"{name}: recreated on the approved image and healthy")


def _restore_ingress(ctx: Context, state: RunState) -> None:
    if "frontend" in ctx.changed:
        state.ingress_stopped = False
        return
    started = ctx.host.write(ctx.host.compose_start("base", "frontend"), "start ingress again")
    if not started.skipped and started.returncode != 0:
        raise StopCondition("APPLY_FAILED", "ingress could not be started again")
    state.ingress_stopped = False
    state.events.append("ingress started again")


def _smoke(ctx: Context, state: RunState) -> None:
    site = ctx.host.profile.site
    for probe in ctx.manifest["smoke"]:
        result = ctx.gate.run(_curl(site + probe["path"], probe["method"]))
        if result.skipped:
            continue
        if result.stdout.strip() != str(probe["expect_status"]):
            raise StopCondition(
                "SMOKE_FAILED",
                f"{probe['method']} {probe['path']} returned {result.stdout.strip() or 'nothing'}, "
                f"expected {probe['expect_status']}",
            )
    state.events.append(f"public smoke: {len(ctx.manifest['smoke'])} request(s) as expected")


def _verify_stable(ctx: Context, state: RunState) -> None:
    if ctx.gate.mode is not Mode.EXECUTE:
        return
    now = ctx.host.container_states(ctx.running_services())
    for name, current in now.items():
        if not (current.present and current.running and current.health == "healthy"):
            raise StopCondition(
                "HEALTH_CHECK_FAILED", f"{name} is not healthy at post-verification"
            )
        if name in ctx.changed and current.restarts != 0:
            raise StopCondition("HEALTH_CHECK_FAILED", f"{name} restarted after the change")
    _others_unchanged(
        ctx, set(ctx.changed) | {"frontend"} if "backend" in ctx.changed else set(ctx.changed)
    )
    state.events.append("post-deploy verification passed")


# --------------------------------------------------------------------------------------------
# Failure handling and rollback
# --------------------------------------------------------------------------------------------


def _stopped(ctx: Context, state: RunState, stop: StopCondition) -> dict[str, Any]:
    """Decide what a stop means: nothing changed, rolled back, or held for the owner."""

    state.events.append(f"STOP {stop.code}: {stop.message}")
    base = {"stop_code": stop.code, "stop_message": stop.message}
    if ctx.gate.mode is not Mode.EXECUTE:
        return {"state": records.FAILED_NO_CHANGE, **base}
    container_changed = bool(state.applied) or state.ingress_stopped
    if not container_changed:
        if state.env_changed and state.backup:
            restored = _restore_env(ctx, state)
            state.events.append(
                "compose.env restored from the backup" if restored else "compose.env NOT restored"
            )
            if not restored:
                return {
                    "state": records.FAILED_HELD,
                    **base,
                    "held_reason": "compose.env could not be restored; no container changed",
                    "manual_next_step": (
                        f"sudo -n cp -p {state.backup} {ctx.host.profile.compose_env}"
                    ),
                }
        return {"state": records.FAILED_NO_CHANGE, **base}
    if not state.applied and stop.code != "APPROVAL_EXPIRED":  # ingress_stopped only
        # Only the old containers were stopped; no new image ever started. Put them back.
        try:
            _resume_previous(ctx, state)
        except StopCondition as failure:
            state.events.append(f"RESUME STOP {failure.code}: {failure.message}")
            return {
                "state": records.FAILED_HELD,
                **base,
                "held_reason": "the previous containers could not be started again",
                "ingress_stopped": True,
            }
        return {"state": records.FAILED_NO_CHANGE, **base}
    reasons = rollback_blockers(ctx, state, stop)
    if reasons:
        if state.ingress_stopped:
            reasons.append("INGRESS IS STOPPED: the site is down until the owner decides")
        return {
            "state": records.FAILED_HELD,
            **base,
            "held_reason": "; ".join(reasons),
            "ingress_stopped": state.ingress_stopped,
            "manual_next_step": (
                "Owner decision needed. Nothing further was changed. Review the events, then "
                "either approve a rollback or a forward fix."
            ),
        }
    try:
        rollback(ctx, state)
    except StopCondition as failure:
        state.events.append(f"ROLLBACK STOP {failure.code}: {failure.message}")
        return {
            "state": records.FAILED_HELD,
            **base,
            "held_reason": f"automatic rollback did not complete: {failure.code}",
            "ingress_stopped": state.ingress_stopped,
        }
    return {"state": records.ROLLED_BACK, **base}


def rollback_blockers(
    ctx: Context, state: RunState, stop: StopCondition | None, *, need_consent: bool = True
) -> list[str]:
    """Why a rollback must not run. An empty list means it may.

    "Compatible" here means what the manifest declares and the owner approved; the tool cannot
    inspect what an image writes.
    """

    reasons: list[str] = []
    if stop is not None and stop.code == "APPROVAL_EXPIRED":
        reasons.append("the approval window ended; expiry stops execution and is never extended")
    if need_consent and (ctx.approval is None or not ctx.approval.get("auto_rollback", False)):
        reasons.append("the owner did not approve automatic rollback")
    for name in sorted(_touched(ctx, state)):
        eligible, reason = rollback_eligibility(ctx.manifest, name)
        if not eligible:
            reasons.append(f"{name}: {reason}")
        elif name not in state.pins_before:
            reasons.append(f"{name}: the previous image pin was not recorded")
    return reasons


def _touched(ctx: Context, state: RunState) -> set[str]:
    touched = set(state.applied) | ({"backend"} if state.ingress_stopped else set())
    return touched & set(ctx.changed)


def _must(result: Any, message: str) -> None:
    if result.returncode != 0:
        raise StopCondition("ROLLBACK_FAILED", message)


def _resume_previous(ctx: Context, state: RunState) -> None:
    """Start the untouched previous backend and ingress again; no new image has run."""

    host = ctx.host
    if state.env_changed and not _restore_env(ctx, state):
        raise StopCondition("ROLLBACK_FAILED", "compose.env could not be restored")
    for wrapper, name in ((ctx.wrapper("backend"), "backend"), ("base", "frontend")):
        started = host.write(host.compose_start(wrapper, name), f"start the previous {name} again")
        _must(started, f"the previous {name} did not start")
    before: dict[str, ContainerState] = ctx.baseline.get("states", {})
    now = host.container_states(["backend", "frontend"])
    for name in ("backend", "frontend"):
        same = name in before and now[name].container_id == before[name].container_id
        if not (same and now[name].running):
            raise StopCondition("ROLLBACK_FAILED", f"the previous {name} is not running")
    state.ingress_stopped = False
    state.events.append("previous backend and ingress started again; no new image ran")


def _restore_env(ctx: Context, state: RunState) -> bool:
    """Put compose.env back as it was before this run.

    Housekeeping: it returns a file to its pre-run content and touches no container, so it is
    still allowed after the approval window has ended. Used only inside the run that made the
    backup, under the host lock.
    """

    restored = ctx.host.write(
        f"sudo -n cp -p {shlex.quote(state.backup)} {shlex.quote(ctx.host.profile.compose_env)}",
        "restore compose.env from the backup",
        housekeeping=True,
    )
    return restored.skipped or restored.returncode == 0


def _unpin(ctx: Context, state: RunState, services: list[str]) -> None:
    """Owner-requested rollback: change back only this release's lines, and only if the host
    still shows this release's pins. Later edits to compose.env are left alone."""

    env_file = shlex.quote(ctx.host.profile.compose_env)
    for name in services:
        variable = catalog.service(name).image_variable
        assert variable is not None
        new, old = safe(state.references[name]), safe(state.pins_before[name])
        if ctx.host.env_value(variable) != new:
            raise StopCondition(
                "HOST_STATE_UNEXPECTED",
                f"{name}: compose.env no longer pins this release; nothing was changed",
            )
    for name in services:
        variable = catalog.service(name).image_variable
        assert variable is not None
        new, old = safe(state.references[name]), safe(state.pins_before[name])
        edited = ctx.host.write(
            f"sudo -n sed -i 's#^{variable}={new}$#{variable}={old}#' {env_file}",
            f"pin {name} back to its previous image",
        )
        _must(edited, f"{name}: compose.env was not updated")
        if ctx.host.env_value(variable) != old:
            raise StopCondition("ROLLBACK_FAILED", f"{name}: the previous pin was not written")


def rollback(ctx: Context, state: RunState, *, manual: bool = False) -> None:
    """Return every touched service to its previous image and verify the site is serving.

    With a backend among them, ingress is stopped first and started last, so a new frontend is
    never served by an old backend and there is one backend writer throughout. Otherwise the
    frontend goes first. Every step's result is checked.
    """

    host = ctx.host
    touched = _touched(ctx, state)
    if manual:
        _unpin(ctx, state, [s for s in catalog.ROLLBACK_ORDER if s in touched])
    elif not _restore_env(ctx, state):
        raise StopCondition("ROLLBACK_FAILED", "compose.env could not be restored")
    with_backend = "backend" in touched
    if with_backend:
        stopped = host.write(
            host.compose_stop("base", "frontend"), "stop ingress for the backend rollback"
        )
        _must(stopped, "ingress could not be stopped")
        state.ingress_stopped = True
        halted = host.write(
            host.compose_stop(ctx.wrapper("backend"), "backend"), "stop the failed backend"
        )
        _must(halted, "the failed backend could not be stopped")
        order = [s for s in ("backend", "assistant", "frontend") if s in touched]
    else:
        order = [s for s in catalog.ROLLBACK_ORDER if s in touched]
    for name in order:
        wrapper = ctx.wrapper(name)
        quiet = host.read(host.compose_config_quiet(wrapper), "validate the restored configuration")
        _must(quiet, "the restored configuration is invalid")
        result = host.write(
            host.compose_up(wrapper, name),
            f"roll {name} back to its previous image",
            timeout=host.profile.wait_timeout_seconds + 120,
        )
        _must(result, f"{name} did not come back healthy")
        expected = host.image_id(state.pins_before[name])
        current = host.container_states([name])[name]
        on_previous = expected is not None and current.image == expected
        if not (current.running and current.health == "healthy" and on_previous):
            raise StopCondition("ROLLBACK_FAILED", f"{name} is not on its previous image")
        state.events.append(f"{name}: rolled back to the previous image and healthy")
    if with_backend and "frontend" not in touched:
        started = host.write(host.compose_start("base", "frontend"), "start ingress again")
        _must(started, "ingress could not be started again")
    for name, current in host.container_states(ctx.running_services()).items():
        if not (current.present and current.running and current.health == "healthy"):
            raise StopCondition("ROLLBACK_FAILED", f"{name} is not running and healthy afterwards")
    state.ingress_stopped = False
    health = ctx.gate.run(_curl(host.profile.site + "/health", "GET"))
    if health.stdout.strip() != "200":
        raise StopCondition("ROLLBACK_FAILED", "the public health check does not return 200")
    _others_unchanged(ctx, touched | ({"frontend"} if with_backend else set()))
    state.events.append("rollback verified: every service healthy and the site serving")


def manual_rollback(ctx: Context, release_id: str) -> dict[str, Any]:
    """Owner-requested rollback of a deployed release.

    Needs its own approval with the ``rollback`` action (single use). The eligibility rules
    are those of the automatic path; an ineligible service is refused, never forced.
    """

    previous = ctx.store.read_result(release_id)
    if previous is None or previous["state"] not in {
        records.DEPLOYED_AWAITING_ACCEPTANCE,
        records.ACCEPTANCE_FAILED,
        records.FAILED_HELD,
    }:
        raise StopCondition("ROLLBACK_NOT_APPLICABLE", "this release is not in a deployed state")
    if previous.get("manifest_sha256") != manifest_hash(ctx.manifest):
        raise StopCondition("APPROVAL_MANIFEST_MISMATCH", "this is not the deployed manifest")
    if ctx.approval is None:
        raise StopCondition("APPROVAL_MISSING", "a rollback needs a current owner approval")
    approvals.check_approval(
        ctx.approval,
        ctx.manifest,
        action="rollback",
        services=ctx.changed,
        clock=ctx.clock,
        consumed=ctx.store.consumed_approvals(),
    )
    ctx.gate.set_deadline(approvals.deadline(ctx.approval, ctx.clock))
    state = RunState(
        backup=previous["env_backup"],
        pins_before=dict(previous["pins_before"]),
        references=dict(previous["references"]),
        applied=list(previous.get("applied", previous["services"])),
        ingress_stopped=bool(previous.get("ingress_stopped", False)),
    )
    host = ctx.host
    with ctx.store.lock(release_id):
        reasons = rollback_blockers(ctx, state, None, need_consent=False)
        if reasons:
            raise StopCondition("ROLLBACK_REFUSED", "; ".join(reasons))
        if not _touched(ctx, state):
            raise StopCondition("ROLLBACK_NOT_APPLICABLE", "no service of this release changed")
        for name in sorted(_touched(ctx, state)):
            variable = catalog.service(name).image_variable
            assert variable is not None
            if host.env_value(variable) != state.references.get(name):
                raise StopCondition(
                    "HOST_STATE_UNEXPECTED",
                    f"{name}: compose.env no longer pins this release; nothing was changed",
                )
        ctx.baseline["states"] = host.container_states(ctx.running_services())
        for name, (ok, detail) in (("volumes", _volumes(ctx)), ("network", _boundaries(ctx))):
            if ok is not True:
                raise StopCondition("PREFLIGHT_FAILED", f"{name}: {detail or 'not readable'}")
        locked = host.write(f"mkdir {shlex.quote(host.profile.lock_dir)}", "take the host lock")
        if locked.returncode != 0:
            raise StopCondition("RELEASE_IN_PROGRESS", "another release holds the host lock")
        ctx.store.consume_approval(ctx.approval["approval_id"], "rollback")
        try:
            rollback(ctx, state, manual=True)
            outcome: dict[str, Any] = {"state": records.ROLLED_BACK}
        except StopCondition as failure:
            state.events.append(f"ROLLBACK STOP {failure.code}: {failure.message}")
            outcome = {
                "state": records.FAILED_HELD,
                "held_reason": f"rollback did not complete: {failure.code}",
                "ingress_stopped": state.ingress_stopped,
            }
        finally:
            host.write(
                f"rmdir {shlex.quote(host.profile.lock_dir)} 2>/dev/null || true",
                "release the host release lock",
                housekeeping=True,
            )
        outcome = {**previous, **outcome, "events": previous["events"] + state.events}
        outcome["rollback_approval_id"] = ctx.approval["approval_id"]
        ctx.store.write_result(release_id, outcome)
        return outcome


# --------------------------------------------------------------------------------------------
# Owner acceptance
# --------------------------------------------------------------------------------------------


def acceptance_runsheet(manifest: Manifest, profile: catalog.HostProfile) -> str:
    lines = [
        f"# Browser acceptance: {manifest['release_id']}",
        "",
        f"Site: {profile.site}",
        f"Services changed: {', '.join(manifest['services_changed'])}",
        "",
        "The pipeline has stopped and waits for the owner. Nothing else runs until the owner",
        "records a result with the `accept` command.",
        "",
        "| # | Check | Expected | Result |",
        "|---|---|---|---|",
        "| 1 | Open the site signed out | Login page over HTTPS, valid certificate | |",
        "| 2 | Sign in as a synthetic RM | Dashboard loads with no error banner | |",
        "| 3 | Open one existing synthetic case | Case detail and documents load | |",
    ]
    if "assistant" in manifest["services_changed"]:
        lines += [
            "| 4 | Ask the assistant about an approved case | An answer, with its sources | |",
            "| 5 | Ask about a case that is not approved | Refused (not eligible) | |",
        ]
    if "frontend" in manifest["services_changed"]:
        lines.append("| 6 | Hard-refresh a deep link | The page loads (no 404) | |")
    lines += [
        "",
        "Record: `release.ps1 accept --release <id> --result pass|fail`.",
        "A failed acceptance never rolls back by itself; it records the result and stops.",
    ]
    return "\n".join(lines) + "\n"


def accept(
    store: records.StateStore,
    manifest: Manifest,
    *,
    passed: bool,
    accepted_by: str,
    interactive: bool,
) -> dict[str, Any]:
    if not interactive:
        raise StopCondition("ACCEPTANCE_NEEDS_OWNER", "acceptance is recorded by the owner only")
    previous = store.read_result(manifest["release_id"])
    if previous is None or previous["state"] != records.DEPLOYED_AWAITING_ACCEPTANCE:
        raise StopCondition("ACCEPTANCE_NOT_PENDING", "this release is not awaiting acceptance")
    if previous["manifest_sha256"] != manifest_hash(manifest):
        raise StopCondition("APPROVAL_MANIFEST_MISMATCH", "this is not the deployed manifest")
    outcome = {
        **previous,
        "state": records.ACCEPTED if passed else records.ACCEPTANCE_FAILED,
        "accepted_by": accepted_by,
    }
    if passed:
        outcome["known_good"] = store.record_known_good(manifest)
    store.write_result(manifest["release_id"], outcome)
    return outcome
