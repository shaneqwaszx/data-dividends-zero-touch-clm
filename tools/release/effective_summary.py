"""Reduce a rendered Compose configuration (JSON on stdin) to a summary with no secret.

Self-contained on purpose: the same source text runs on the host as `python3 -c` behind a pipe,
so the full rendered configuration (which contains the database connection setting) never
leaves the host and is never printed. Environment values are dropped; only names survive,
apart from a short list of non-secret safety switches.
"""

import json
import sys
from typing import Any

SAFE_VALUES = (
    "APP_ENV",
    "CLM_PERSISTENCE_MODE",
    "MONGO_DATABASE",
    "PHASE13_COOKIE_SECURE",
    "ACRA_CONNECTOR_MODE",
    "GOLDTIER_CONNECTOR_MODE",
    "GOLDTIER_SANDBOX_ALLOW_WRITES",
    "IDP_CONNECTOR_MODE",
    "DEMO_CONTROLS_ENABLED",
    "AI_ASSISTANT_LLM_BASE_URL",
    "AI_ASSISTANT_LLM_MODEL",
    "ASSISTANT_HOSTING_PROVIDER",
    "ASSISTANT_HOSTING_SEED_SYNTHETIC",
    "CLM_EGRESS_ROLE",
)
SETTINGS = (
    "cap_add",
    "cap_drop",
    "read_only",
    "privileged",
    "network_mode",
    "pid",
    "ipc",
    "userns_mode",
    "security_opt",
    "restart",
    "user",
    "dns",
    "sysctls",
    "devices",
    "container_name",
    "platform",
    "init",
    "tmpfs",
    "volumes_from",
    "group_add",
    "mem_limit",
    "pids_limit",
)
# Kept in their written order: sorting an argument list would hide a reordering.
ORDERED = ("command", "entrypoint")


def summarise(document: dict[str, Any]) -> dict[str, Any]:
    services = {}
    for name, body in sorted((document.get("services") or {}).items()):
        environment = body.get("environment") or {}
        networks = body.get("networks") or {}
        ports = []
        for port in body.get("ports") or []:
            ports.append(
                "{}:{}/{}".format(
                    port.get("published", ""), port.get("target", ""), port.get("protocol", "tcp")
                )
            )
        volumes = []
        bind_sources = []
        for volume in body.get("volumes") or []:
            kind = volume.get("type", "")
            source = volume.get("source", "") if kind == "volume" else ""
            if kind == "bind":
                bind_sources.append(str(volume.get("source", "")))
                if "docker.sock" in str(volume.get("source", "")):
                    source = "docker-socket"
            mode = "ro" if volume.get("read_only") else "rw"
            volumes.append("{}:{}:{}:{}".format(kind, source, volume.get("target", ""), mode))
        settings = {}
        for key in SETTINGS:
            if body.get(key) not in (None, [], {}, ""):
                value = body[key]
                settings[key] = sorted(value) if isinstance(value, list) else value
        for key in ORDERED:
            if body.get(key) not in (None, [], ""):
                settings[key] = body[key]
        test = (body.get("healthcheck") or {}).get("test")
        if test:
            settings["healthcheck"] = test
        deploy = body.get("deploy") or {}
        if deploy.get("replicas") not in (None, 1):
            settings["replicas"] = deploy["replicas"]
        hosts = body.get("extra_hosts") or []
        if isinstance(hosts, dict):
            hosts = sorted(hosts)
        else:
            hosts = sorted(str(item).split("=")[0].split(":")[0] for item in hosts)
        services[name] = {
            "image": body.get("image", ""),
            "networks": sorted(networks),
            "addresses": dict(
                (net, (cfg or {}).get("ipv4_address", "")) for net, cfg in sorted(networks.items())
            ),
            "ports": sorted(ports),
            "environment": sorted(environment),
            "safe_values": dict(
                (key, str(environment[key])) for key in SAFE_VALUES if key in environment
            ),
            "volumes": sorted(volumes),
            "bind_sources": sorted(bind_sources),
            "extra_hosts": hosts,
            "depends_on": sorted(body.get("depends_on") or {}),
            "settings": settings,
        }
    network_map = {}
    for name, body in sorted((document.get("networks") or {}).items()):
        body = body or {}
        network_map[name] = {
            "internal": bool(body.get("internal")),
            "external": bool(body.get("external")),
        }
    volume_map = {}
    for name, body in sorted((document.get("volumes") or {}).items()):
        volume_map[name] = {"external": bool((body or {}).get("external"))}
    return {
        "project": document.get("name", ""),
        "services": services,
        "networks": network_map,
        "volumes": volume_map,
    }


if __name__ == "__main__":
    json.dump(summarise(json.load(sys.stdin)), sys.stdout, sort_keys=True)
