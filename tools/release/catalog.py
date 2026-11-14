"""What the toolchain knows about the stack: services, overlay sets, order and risk.

These facts restate ``deploy/LIGHTSAIL_RUNTIME.md`` (the ``dc`` / ``dca`` / ``dcg`` wrappers and
overlay order) and ``deploy/README.md``. Nothing here invents a new rule; a combination that the
runbooks do not describe is unsupported and refused.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .core import ReleaseError, StopCondition

REGISTRY_HOST = "ghcr.io"
REGISTRY_NAMESPACE = "ghcr.io/shaneqwaszx"
PLATFORM = "linux/amd64"

# Overlay files in their only supported order.
COMPOSE_BASE = "deploy/compose.yml"
COMPOSE_MONGO = "deploy/compose.mongo.yml"
COMPOSE_ASSISTANT = "apps/assistant/deploy/compose.assistant.yml"
COMPOSE_PROVIDER = "apps/assistant/deploy/compose.assistant-provider.yml"
COMPOSE_GOLDTIER = "deploy/compose.goldtier-egress.yml"
OVERLAY_ORDER = (COMPOSE_BASE, COMPOSE_MONGO, COMPOSE_ASSISTANT, COMPOSE_PROVIDER, COMPOSE_GOLDTIER)

# name -> ordered files. ``dc`` = base, ``dca`` = assistant, ``dcg`` = goldtier.
OVERLAY_SETS: dict[str, tuple[str, ...]] = {
    "base": (COMPOSE_BASE, COMPOSE_MONGO),
    "assistant": (COMPOSE_BASE, COMPOSE_MONGO, COMPOSE_ASSISTANT),
    "assistant-provider": (COMPOSE_BASE, COMPOSE_MONGO, COMPOSE_ASSISTANT, COMPOSE_PROVIDER),
    "goldtier": (COMPOSE_BASE, COMPOSE_MONGO, COMPOSE_GOLDTIER),
    # Whole-stack renders, used only for validation; no wrapper applies them on the host.
    "full-assistant-goldtier": (COMPOSE_BASE, COMPOSE_MONGO, COMPOSE_ASSISTANT, COMPOSE_GOLDTIER),
    "full-provider-goldtier": OVERLAY_ORDER,
}
VALIDATION_ONLY_SETS = frozenset({"full-assistant-goldtier", "full-provider-goldtier"})
# Optional overlays that may be active on the host, and the state name used in a manifest.
HOST_OVERLAYS = ("assistant", "assistant-provider", "goldtier")

LOW, MEDIUM, HIGH = "LOW", "MEDIUM", "HIGH"
RISK_ORDER = {LOW: 0, MEDIUM: 1, HIGH: 2}


@dataclass(frozen=True)
class Service:
    name: str
    image_variable: str | None  # the compose.env line that pins the image
    repository: str | None
    container: str
    base_risk: str
    stateful: bool
    # The automated applier may recreate this service. False = plan and document only.
    automated_apply: bool
    data_volume_variable: str | None = None
    in_image_paths: tuple[tuple[str, str], ...] = ()  # (repository path, path in the image)
    notes: str = ""


SERVICES: dict[str, Service] = {
    "frontend": Service(
        name="frontend",
        image_variable="FRONTEND_IMAGE",
        repository=f"{REGISTRY_NAMESPACE}/clm-aws-demo-frontend",
        container="clm-staging-frontend-1",
        base_risk=LOW,
        stateful=False,
        automated_apply=True,
        in_image_paths=(("deploy/Caddyfile", "/etc/caddy/Caddyfile"),),
    ),
    "assistant": Service(
        name="assistant",
        image_variable="ASSISTANT_IMAGE",
        repository=f"{REGISTRY_NAMESPACE}/clm-aws-demo-assistant",
        container="clm-staging-assistant",
        base_risk=MEDIUM,
        stateful=True,  # its stores live on an external volume a newer image may upgrade
        automated_apply=True,
        data_volume_variable="ASSISTANT_DATA_VOLUME",
        in_image_paths=(
            ("apps/assistant/ai_assistant", "/opt/assistant/ai_assistant"),
            ("apps/assistant/assistant_hosting", "/opt/assistant/assistant_hosting"),
            ("apps/assistant/assistant_eval", "/opt/assistant/assistant_eval"),
            (
                "apps/assistant/deploy/model_profiles.hosted.json",
                "/opt/assistant/deploy/model_profiles.hosted.json",
            ),
            (
                "apps/assistant/deploy/requirements.lock",
                "/opt/assistant/deploy/requirements.lock",
            ),
        ),
    ),
    "backend": Service(
        name="backend",
        image_variable="BACKEND_IMAGE",
        repository=f"{REGISTRY_NAMESPACE}/clm-aws-demo-backend",
        container="clm-staging-backend",
        base_risk=HIGH,
        stateful=True,  # the single Mongo writer
        automated_apply=True,
        in_image_paths=(("apps/backend/app", "/opt/clm/apps/backend/app"),),
    ),
    "mongo": Service(
        name="mongo",
        image_variable=None,  # pinned by digest inside compose.mongo.yml
        repository=None,
        container="clm-staging-mongo-1",
        base_risk=HIGH,
        stateful=True,
        automated_apply=False,
        data_volume_variable="MONGO_DATA_VOLUME",
        notes="Never recreated by the toolchain; follow the manual recovery runbook.",
    ),
    "goldtier-egress": Service(
        name="goldtier-egress",
        image_variable="GOLDTIER_EGRESS_IMAGE",
        repository=f"{REGISTRY_NAMESPACE}/clm-aws-demo-goldtier-egress",
        container="clm-staging-goldtier-egress",
        base_risk=HIGH,
        stateful=False,
        automated_apply=False,
        notes="Needs host firewall files and units (G3); manual, separately gated.",
    ),
    "goldtier-dns": Service(
        name="goldtier-dns",
        image_variable="GOLDTIER_EGRESS_IMAGE",
        repository=f"{REGISTRY_NAMESPACE}/clm-aws-demo-goldtier-egress",
        container="clm-staging-goldtier-dns",
        base_risk=HIGH,
        stateful=False,
        automated_apply=False,
        notes="Needs host firewall files and units (G3); manual, separately gated.",
    ),
}

# Deploy order when several services change in one release; rollback uses the reverse, so the
# frontend always rolls back first or together with the backend.
DEPLOY_ORDER = ("backend", "assistant", "frontend")
ROLLBACK_ORDER = tuple(reversed(DEPLOY_ORDER))

# The only backend line known to write case-snapshot schema 19. It can never be a rollback
# target once a schema-20 backend has run (image QG F-1, 2026-11-14).
SCHEMA_19_BACKEND_COMMITS = ("4c1db49",)
CURRENT_SNAPSHOT_SCHEMA = 20


@dataclass(frozen=True)
class HostProfile:
    """Non-secret facts about the single Lightsail host. No address or key lives here."""

    project: str = "clm-staging"
    workdir: str = "/opt/clm"
    compose_env: str = "/etc/clm/compose.env"
    mongo_uri_file: str = "/etc/clm/mongo.uri"
    site: str = "https://delta-clm.duckdns.org"
    proxy_network: str = "clm-staging_proxy"
    min_mem_available_kb: int = 1_500_000
    min_disk_free_kb: int = 3_000_000
    # Where the host lane keeps its quiesced Mongo archives. Not known to this repository: the
    # operator configuration supplies it, and a stateful release is refused without it.
    backup_glob: str | None = None
    max_backup_age_hours: int = 72
    wait_timeout_seconds: int = 180
    lock_dir: str = "/run/lock/clm-release.lock"
    state_dir: str = "~/clm-release"
    containers: dict[str, str] = field(
        default_factory=lambda: {name: svc.container for name, svc in SERVICES.items()}
    )


def overlay_files(set_name: str) -> tuple[str, ...]:
    try:
        return OVERLAY_SETS[set_name]
    except KeyError as exc:
        raise StopCondition(
            "OVERLAY_SET_UNSUPPORTED", f"overlay set {set_name!r} is not supported"
        ) from exc


def resolve_overlay_files(files: tuple[str, ...]) -> str:
    """Name the supported set for an ordered file list, or refuse."""

    normalised = tuple(f.replace("\\", "/") for f in files)
    if len(set(normalised)) != len(normalised):
        raise StopCondition("OVERLAY_DUPLICATE", "an overlay file is listed twice")
    unknown = [f for f in normalised if f not in OVERLAY_ORDER]
    if unknown:
        raise StopCondition("OVERLAY_UNKNOWN_FILE", f"unknown Compose file: {unknown[0]}")
    for name, expected in OVERLAY_SETS.items():
        if expected == normalised:
            return name
    if set(normalised) in [set(v) for v in OVERLAY_SETS.values()]:
        raise StopCondition("OVERLAY_ORDER", "Compose files are not in the supported order")
    raise StopCondition("OVERLAY_SET_UNSUPPORTED", "this overlay combination is not supported")


def wrapper_set_for(service: str, active_overlays: tuple[str, ...]) -> str:
    """The overlay set the runbook's wrapper uses for one service (``dc``/``dca``/``dcg``)."""

    for overlay in active_overlays:
        if overlay not in HOST_OVERLAYS:
            raise StopCondition("OVERLAY_SET_UNSUPPORTED", f"unknown host overlay {overlay!r}")
    if "assistant-provider" in active_overlays and "assistant" not in active_overlays:
        raise StopCondition(
            "OVERLAY_SET_UNSUPPORTED", "the provider overlay needs the assistant overlay"
        )
    if service == "frontend":
        return "base"
    if service == "assistant":
        if "assistant" not in active_overlays:
            raise StopCondition(
                "OVERLAY_SET_UNSUPPORTED", "the assistant overlay is not active on the host"
            )
        return "assistant-provider" if "assistant-provider" in active_overlays else "assistant"
    if service in {"backend", "mongo"}:
        return "goldtier" if "goldtier" in active_overlays else "base"
    if service in {"goldtier-egress", "goldtier-dns"}:
        if "goldtier" not in active_overlays:
            raise StopCondition(
                "OVERLAY_SET_UNSUPPORTED", "the GoldTier egress overlay is not active on the host"
            )
        return "goldtier"
    raise ReleaseError("SERVICE_UNKNOWN", f"unknown service {service!r}")


def service(name: str) -> Service:
    try:
        return SERVICES[name]
    except KeyError as exc:
        raise ReleaseError("SERVICE_UNKNOWN", f"unknown service {name!r}") from exc


def highest_risk(*classes: str) -> str:
    return max(classes, key=lambda c: RISK_ORDER[c])
