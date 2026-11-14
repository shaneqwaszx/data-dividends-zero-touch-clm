"""Validate the complete effective Compose configuration for a supported overlay set.

The approach is the coordinator's ``render_combined.py`` and ``tests/deploy``: render offline
with ``docker compose config`` and placeholder values, never reading an ``.env`` file. On top of
that this module compares the result with a reviewed baseline and refuses anything a release
did not declare.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import catalog
from .core import Command, Effect, Gate, ReleaseError, StopCondition, read_json
from .effective_summary import summarise

BASELINE = Path(__file__).resolve().parent / "policy" / "effective-baseline.json"
Summary = dict[str, Any]
Declared = Mapping[str, Mapping[str, list[str]]]

# The developer's own environment must never leak into an interpolated value.
INTERPOLATED_PREFIXES = (
    "BACKEND_",
    "FRONTEND_",
    "ASSISTANT_",
    "GOLDTIER_",
    "CLM_",
    "MONGO_",
    "ACRA_",
    "AI_ASSISTANT_",
    "HTTP_BIND",
    "HTTPS_BIND",
    "COMPOSE_",
)
INTERNAL_NETWORKS = ("proxy", "database", "goldtier-control")
EXTERNAL_VOLUMES = ("mongo-data", "assistant-data")
# The most each service may ever be attached to. A release cannot declare its way past these.
NETWORK_CEILING: dict[str, frozenset[str]] = {
    "frontend": frozenset({"default", "proxy"}),
    "backend": frozenset({"proxy", "database", "goldtier-control"}),
    "mongo": frozenset({"database"}),
    "assistant": frozenset({"proxy", "assistant-uplink"}),
    "goldtier-egress": frozenset({"goldtier-control", "goldtier-uplink"}),
    "goldtier-dns": frozenset({"goldtier-control", "goldtier-uplink"}),
}
FRONTEND_PORTS = frozenset({"80:80/tcp", "443:443/tcp"})
MODEL_FREE_BASE_URL = "http://127.0.0.1:9/v1"


def placeholder_environment(scratch: Path) -> dict[str, str]:
    """Placeholder interpolation values. No real address, origin, volume or credential."""

    for name in ("empty.env", "backend.env", "mongo-ca.pem", "mongo-server.pem"):
        (scratch / name).write_text("", encoding="ascii")
    inherited = {
        k: v for k, v in os.environ.items() if not k.upper().startswith(INTERPOLATED_PREFIXES)
    }
    return inherited | {
        "BACKEND_IMAGE": "example.invalid/backend@sha256:" + "0" * 64,
        "FRONTEND_IMAGE": "example.invalid/frontend@sha256:" + "1" * 64,
        "ASSISTANT_IMAGE": "example.invalid/assistant@sha256:" + "2" * 64,
        "GOLDTIER_EGRESS_IMAGE": "example.invalid/egress@sha256:" + "3" * 64,
        "BACKEND_ENV_FILE": str(scratch / "backend.env"),
        "CLM_SITE": "clm.example.invalid",
        "MONGO_URI": "placeholder-connection-setting",
        "MONGO_CA_FILE": str(scratch / "mongo-ca.pem"),
        "MONGO_SERVER_PEM": str(scratch / "mongo-server.pem"),
        "MONGO_DATA_VOLUME": "clm-render-mongo",
        "ASSISTANT_DATA_VOLUME": "clm-render-assistant",
        "ASSISTANT_BROWSER_ORIGIN": "https://clm.example.invalid",
        "ASSISTANT_ELIGIBLE_CASE_REFS": "000000000000",
        "ASSISTANT_ELIGIBLE_CREATED_BEFORE": "2099-01-01T00:00:00Z",
        "CLM_GOLDTIER_EGRESS_FQDN": "goldtier.render.invalid",
        "CLM_GOLDTIER_EGRESS_DST_V4": "192.0.2.10",
        "ASSISTANT_CLAUDE_LIFETIME_CAP_MICRO_USD": "30000000",
        "ASSISTANT_ANTHROPIC_PINNED_V4": "192.0.2.20",
    }


def render_set(gate: Gate, root: Path, set_name: str) -> Summary:
    """Render one supported overlay set offline and return its secret-free summary."""

    files = catalog.overlay_files(set_name)
    for relative in files:
        if not (root / relative).is_file():
            raise ReleaseError("COMPOSE_FILE_MISSING", f"{relative} is not in the source tree")
    with tempfile.TemporaryDirectory(prefix="clm-render-") as scratch_name:
        scratch = Path(scratch_name)
        env = placeholder_environment(scratch)
        argv = [
            "docker",
            "compose",
            "--env-file",
            str(scratch / "empty.env"),
            "--project-name",
            "clm-staging",
        ]
        for relative in files:
            argv += ["-f", str(root / relative)]
        argv += ["config", "--format", "json", "--no-path-resolution"]
        result = gate.run(
            Command(
                tuple(argv),
                Effect.LOCAL_READ,
                f"render overlay set {set_name} offline",
                env=env,
                cwd=str(root),
                timeout=120,
                quiet=True,
            )
        )
    if result.returncode != 0:
        raise StopCondition(
            "COMPOSE_RENDER_FAILED", f"{set_name}: Compose refused the configuration"
        )
    try:
        document = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise StopCondition("COMPOSE_RENDER_FAILED", f"{set_name}: unreadable render") from exc
    return normalise(summarise(document))


def normalise(summary: Summary) -> Summary:
    """Drop the parts that legitimately differ between a placeholder render and the host."""

    for body in summary["services"].values():
        body["image"] = ""
    return summary


def load_baseline() -> dict[str, Summary]:
    return read_json(BASELINE)  # type: ignore[no-any-return]


def invariant_violations(set_name: str, summary: Summary) -> list[str]:
    """Rules no manifest can relax: the protected network and data boundaries."""

    found: list[str] = []
    provider = set_name in {"assistant-provider", "full-provider-goldtier"}
    for name, body in summary["services"].items():
        ceiling = NETWORK_CEILING.get(name)
        if ceiling is None:
            found.append(f"{name}: unknown service")
            continue
        extra = set(body["networks"]) - ceiling
        if extra:
            found.append(f"{name}: forbidden network {sorted(extra)[0]}")
        if name == "frontend":
            if set(body["ports"]) - FRONTEND_PORTS:
                found.append("frontend: publishes a port other than 80 and 443")
        elif body["ports"]:
            found.append(f"{name}: publishes a port (only the frontend may)")
        settings = body["settings"]
        if settings.get("privileged"):
            found.append(f"{name}: privileged")
        for key in ("network_mode", "pid", "ipc", "userns_mode"):
            if settings.get(key) == "host":
                found.append(f"{name}: {key} host")
        if settings.get("devices"):
            found.append(f"{name}: device mapping")
        if "replicas" in settings:
            found.append(f"{name}: more than one replica")
        if name in {"backend", "assistant", "goldtier-egress", "goldtier-dns"}:
            if settings.get("cap_drop") != ["ALL"]:
                found.append(f"{name}: capabilities are not all dropped")
            if settings.get("read_only") is not True:
                found.append(f"{name}: root filesystem is writable")
        if any(v.startswith("bind:") and v.endswith(":rw") for v in body["volumes"]):
            found.append(f"{name}: writable host bind mount")
        if any("docker.sock" in v for v in body["volumes"]):
            found.append(f"{name}: Docker socket mounted")
    services = summary["services"]
    backend = services.get("backend")
    if backend is not None:
        if backend["safe_values"].get("GOLDTIER_SANDBOX_ALLOW_WRITES") != "false":
            found.append("backend: GoldTier Sandbox writes are not refused")
        if "default" in backend["networks"]:
            found.append("backend: attached to a network with an internet route")
    assistant = services.get("assistant")
    if assistant is not None:
        if "assistant-uplink" in assistant["networks"] and not provider:
            found.append("assistant: uplink network without the provider overlay")
        if not provider:
            if assistant["safe_values"].get("AI_ASSISTANT_LLM_BASE_URL") != MODEL_FREE_BASE_URL:
                found.append("assistant: model client does not point at the closed local port")
            if "ASSISTANT_HOSTING_PROVIDER" in assistant["environment"]:
                found.append("assistant: provider configured without the provider overlay")
        keys = [e for e in assistant["environment"] if e.endswith(("API_KEY", "_TOKEN", "_SECRET"))]
        if keys:
            found.append("assistant: a credential variable is configured in Compose")
    for network in INTERNAL_NETWORKS:
        if network in summary["networks"] and not summary["networks"][network]["internal"]:
            found.append(f"network {network}: must be internal")
    for volume in EXTERNAL_VOLUMES:
        if volume in summary["volumes"] and not summary["volumes"][volume]["external"]:
            found.append(f"volume {volume}: must be external so Compose can never remove it")
    return found


def undeclared_changes(baseline: Summary, summary: Summary, declared: Declared) -> list[str]:
    """Everything the render has that the baseline lacks and the manifest did not declare."""

    found: list[str] = []
    for name, body in summary["services"].items():
        base = baseline["services"].get(name)
        if base is None:
            found.append(f"{name}: service is not in the reviewed baseline")
            continue
        allowed = declared.get(name, {})
        for kind in ("networks", "ports", "environment"):
            extra = set(body[kind]) - set(base[kind]) - set(allowed.get(kind, []))
            for item in sorted(extra):
                found.append(f"{name}: undeclared {kind} entry {item}")
        settings_allowed = set(allowed.get("settings", []))
        for key in ("volumes", "extra_hosts", "depends_on", "addresses", "safe_values"):
            if body[key] != base[key] and key not in settings_allowed:
                found.append(f"{name}: undeclared change to {key}")
        for key in sorted(set(body["settings"]) | set(base["settings"])):
            if body["settings"].get(key) != base["settings"].get(key) and (
                key not in settings_allowed
            ):
                found.append(f"{name}: undeclared change to setting {key}")
        for kind in ("networks", "ports", "environment"):
            for item in sorted(set(base[kind]) - set(body[kind])):
                if f"removed:{kind}:{item}" not in settings_allowed:
                    found.append(f"{name}: undeclared removal of {kind} entry {item}")
    for name in baseline["services"]:
        if name not in summary["services"]:
            found.append(f"{name}: service missing from the render")
    for kind in ("networks", "volumes"):
        if summary[kind] != baseline[kind]:
            names = sorted(set(summary[kind]) ^ set(baseline[kind])) or sorted(summary[kind])
            if not all(
                f"top-level:{kind}:{n}" in set(declared.get("*", {}).get("settings", []))
                for n in names
            ):
                found.append(f"top-level {kind} differ from the reviewed baseline")
    return found


def check_summary(
    set_name: str, summary: Summary, declared: Declared, baseline: dict[str, Summary] | None = None
) -> None:
    """Refuse a render that breaks an invariant or contains an undeclared change."""

    catalog.overlay_files(set_name)
    problems = invariant_violations(set_name, summary)
    if problems:
        raise StopCondition("EFFECTIVE_CONFIG_INVARIANT", "; ".join(problems[:6]))
    reference = (baseline if baseline is not None else load_baseline()).get(set_name)
    if reference is None:
        raise StopCondition("OVERLAY_SET_UNSUPPORTED", f"no reviewed baseline for {set_name}")
    problems = undeclared_changes(reference, summary, declared)
    if problems:
        raise StopCondition("EFFECTIVE_CONFIG_UNDECLARED", "; ".join(problems[:6]))


def validate_release_config(gate: Gate, root: Path, manifest: Mapping[str, Any]) -> list[str]:
    """Render and check every overlay set this release touches. Returns the sets checked."""

    active = tuple(manifest["overlay"]["active_host_overlays"])
    sets = {manifest["overlay"]["validation_set"]}
    for name in manifest["services_changed"]:
        sets.add(catalog.wrapper_set_for(name, active))
    declared: Declared = manifest["declared_config_changes"]
    for set_name in sorted(sets):
        check_summary(set_name, render_set(gate, root, set_name), declared)
    return sorted(sets)


def build_baseline(gate: Gate, root: Path) -> dict[str, Summary]:
    """Developer action: regenerate the baseline from the Compose files. Review the diff."""

    baseline: dict[str, Summary] = {}
    for set_name in catalog.OVERLAY_SETS:
        summary = render_set(gate, root, set_name)
        problems = invariant_violations(set_name, summary)
        if problems:
            raise StopCondition("EFFECTIVE_CONFIG_INVARIANT", "; ".join(problems[:6]))
        baseline[set_name] = summary
    return baseline
