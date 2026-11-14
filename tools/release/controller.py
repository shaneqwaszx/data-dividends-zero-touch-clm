"""The local release controller: turn an approved release request into a promotion-ready record.

It runs on this Windows machine and needs no GitHub Actions job. One ``tick``:

1. notes a new commit on the integration baseline (a notice only);
2. for each new request in the inbox: verifies the exact commit and a clean checkout, runs the
   selected local checks, accepts or builds the images, proves their content, validates the
   effective Compose configuration and writes the manifest;
3. stops at ``PROMOTION_READY``.

It never publishes, approves or deploys. Promotion is always a separate command that needs an
owner approval record. Nothing runs while this machine is off.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from . import catalog, images, render, source
from .core import (
    Clock,
    Command,
    Effect,
    Gate,
    ReleaseError,
    StopCondition,
    format_utc,
    read_json,
    utc_now,
    write_json,
)
from .manifest import Manifest, manifest_hash, minimum_risk, validate_manifest
from .records import StateStore

DETECTED, PROMOTION_READY, FAILED = "DETECTED", "PROMOTION_READY", "FAILED"
REQUEST_FIELDS = {
    "request_id",
    "commit",
    "tree",
    "pull_request",
    "change_classes",
    "services_changed",
    "active_host_overlays",
    "validation_set",
    "candidates",
    "build",
    "risk_class",
    "rollback",
    "coupling",
    "smoke",
    "quality_gates",
    "evidence",
    "declared_config_changes",
    "notes",
    "sequence",
    "extra_checks",
    "allow_untracked",
}


def load_request(path: Path) -> dict[str, Any]:
    request = read_json(path)
    if not isinstance(request, dict):
        raise ReleaseError("REQUEST_INVALID", "a release request is a JSON object")
    unknown = set(request) - REQUEST_FIELDS
    if unknown:
        raise ReleaseError("REQUEST_INVALID", f"unknown field {sorted(unknown)[0]}")
    for name in (
        "request_id",
        "commit",
        "change_classes",
        "services_changed",
        "risk_class",
        "rollback",
        "smoke",
    ):
        if name not in request:
            raise ReleaseError("REQUEST_INVALID", f"missing {name}")
    return request


def assemble_manifest(
    gate: Gate,
    root: Path,
    request: dict[str, Any],
    store: StateStore,
    *,
    clock: Clock = utc_now,
    run_checks: bool = True,
) -> Manifest:
    """Verify, check, prepare images and write down everything a release needs."""

    commit = request["commit"]
    state = source.verify_source(
        gate,
        root,
        commit=commit,
        tree=request.get("tree"),
        allow_untracked=tuple(request.get("allow_untracked", ())),
    )
    changed: list[str] = request["services_changed"]
    active = tuple(request.get("active_host_overlays", ()))
    validation_set = request.get("validation_set") or _default_validation_set(active)
    order = catalog.overlay_files(validation_set)
    names = source.select_checks(request["change_classes"], tuple(request.get("extra_checks", ())))
    if run_checks:
        checks = source.run_checks(gate, root, names)
    else:
        checks = [
            {"name": name, "status": "NOT_RUN", "detail": "skipped on request; not a pass"}
            for name in [*names, *(f"ci-job:{job}" for job in source.MANUAL_CI_JOBS)]
        ]
    entries: dict[str, Any] = {}
    candidates: dict[str, dict[str, str]] = request.get("candidates", {})
    for name in changed:
        key = "goldtier-egress" if name.startswith("goldtier") else name
        if key in entries:
            continue
        if key in candidates:
            reference = candidates[key]["local_ref"]
            images.accept_existing(gate, reference, candidates[key]["local_image_id"])
            mode = "accepted-existing"
        elif key in request.get("build", []):
            reference = f"clm-rc-{key}:{commit[:7]}"
            with tempfile.TemporaryDirectory(prefix="clm-context-") as scratch:
                context = images.export_context(gate, root, commit, Path(scratch) / "context")
                images.build(gate, context, key, reference)
            mode = "built"
        else:
            raise StopCondition("IMAGE_MISSING", f"no candidate and no build requested for {name}")
        entries[key] = images.describe_candidate(gate, root, commit, key, reference, mode=mode)
    previous = store.known_good()
    manifest: Manifest = {
        "schema_version": 1,
        "release_id": (
            f"rel-{commit[:7]}-{clock().strftime('%Y%m%d')}-{int(request.get('sequence', 1)):02d}"
        ),
        "created_at": format_utc(clock()),
        "source": {
            "repository": "shaneqwaszx/data-dividends-zero-touch-clm",
            "commit": state.commit,
            "tree": state.tree,
            "base_ref": state.base_ref,
            "clean": True,
            "pull_request": request.get("pull_request"),
        },
        "risk_class": request["risk_class"],
        "risk_reasons": [],
        "change_classes": request["change_classes"],
        "services_changed": changed,
        "services_unchanged": [s for s in _running(active) if s not in changed],
        "overlay": {
            "active_host_overlays": list(active),
            "validation_set": validation_set,
            "order": list(order),
        },
        "images": entries,
        "compose_files": source.compose_file_hashes(gate, root, commit, order),
        "declared_config_changes": request.get("declared_config_changes", {}),
        "checks": checks,
        "evidence": request.get("evidence", []),
        "quality_gates": request.get("quality_gates", []),
        "coupling": request.get("coupling", []),
        "rollback": request["rollback"],
        "smoke": request["smoke"],
        "previous_known_good": (
            {"release_id": previous["release_id"], "manifest_sha256": previous["manifest_sha256"]}
            if previous
            else None
        ),
        "notes": request.get("notes", []),
    }
    manifest["risk_reasons"] = minimum_risk(manifest)[1]
    validate_manifest(manifest)
    render.validate_release_config(gate, root, manifest)
    manifest["checks"].append(
        {
            "name": "effective-compose-config",
            "status": "PASS",
            "detail": "rendered offline; no undeclared network, port or variable",
        }
    )
    return manifest


def _running(active: tuple[str, ...]) -> list[str]:
    services = ["frontend", "backend", "mongo"]
    if "assistant" in active:
        services.append("assistant")
    if "goldtier" in active:
        services += ["goldtier-egress", "goldtier-dns"]
    return services


def _default_validation_set(active: tuple[str, ...]) -> str:
    if "goldtier" in active and "assistant-provider" in active:
        return "full-provider-goldtier"
    if "goldtier" in active and "assistant" in active:
        return "full-assistant-goldtier"
    if "goldtier" in active:
        return "goldtier"
    if "assistant-provider" in active:
        return "assistant-provider"
    return "assistant" if "assistant" in active else "base"


class Controller:
    def __init__(self, gate: Gate, root: Path, store: StateStore, clock: Clock = utc_now) -> None:
        self.gate, self.root, self.store, self.clock = gate, root, store, clock
        self.inbox = store.root / "inbox"
        self.requests = store.root / "requests"

    def _status_path(self, request_id: str) -> Path:
        if not request_id.replace("-", "").replace("_", "").isalnum():
            raise ReleaseError("REQUEST_INVALID", "request_id has unsafe characters")
        return self.requests / request_id / "status.json"

    def detect_new_commit(self) -> dict[str, Any] | None:
        """Record a new head of the integration baseline. A notice: it starts nothing."""

        head = self.gate.run(
            Command(
                ("git", "rev-parse", "--verify", "origin/main"),
                Effect.LOCAL_READ,
                "read the last fetched integration baseline",
                cwd=str(self.root),
            )
        )
        if head.returncode != 0:
            return None
        commit = head.stdout.strip()
        path = self.store.root / "seen-main.json"
        seen = read_json(path) if path.exists() else {"commit": None}
        if seen["commit"] == commit:
            return None
        notice = {"commit": commit, "seen_at": format_utc(self.clock()), "previous": seen["commit"]}
        write_json(path, notice)
        self.gate.log.event("new-main-commit", commit=commit)
        return notice

    def tick(self, *, run_checks: bool = True) -> list[dict[str, Any]]:
        """Process every new request once. Returns the status of each request handled."""

        handled: list[dict[str, Any]] = []
        self.detect_new_commit()
        for path in sorted(self.inbox.glob("*.json")) if self.inbox.is_dir() else []:
            try:
                request = load_request(path)
                status_path = self._status_path(request["request_id"])
            except ReleaseError as error:
                handled.append({"request": path.name, "state": FAILED, "code": error.code})
                continue
            if status_path.exists():
                continue  # done or failed: never retried silently
            status: dict[str, Any] = {
                "request_id": request["request_id"],
                "commit": request["commit"],
                "started_at": format_utc(self.clock()),
            }
            try:
                with self.store.lock(f"rel-prepare-{request['request_id']}"):
                    manifest = assemble_manifest(
                        self.gate,
                        self.root,
                        request,
                        self.store,
                        clock=self.clock,
                        run_checks=run_checks,
                    )
                    target = self.store.release_dir(manifest["release_id"]) / "manifest.json"
                    write_json(target, manifest)
                failed = [c["name"] for c in manifest["checks"] if c["status"] == "FAIL"]
                if failed:
                    raise StopCondition("CHECK_FAILED", f"check {failed[0]} failed")
                status |= {
                    "state": PROMOTION_READY,
                    "release_id": manifest["release_id"],
                    "manifest": str(target),
                    "manifest_sha256": manifest_hash(manifest),
                    "risk_class": manifest["risk_class"],
                    "services": manifest["services_changed"],
                    "not_run": [c["name"] for c in manifest["checks"] if c["status"] == "NOT_RUN"],
                    "next": (
                        "Owner: review the plan, then approve. Nothing is published or deployed "
                        "until an approval record exists and a person runs the command."
                    ),
                }
            except ReleaseError as error:
                status |= {"state": FAILED, "code": error.code, "message": error.message}
            status["finished_at"] = format_utc(self.clock())
            write_json(status_path, status)
            self.gate.log.event("request-processed", **status)
            handled.append(status)
        return handled

    def status(self) -> list[dict[str, Any]]:
        if not self.requests.is_dir():
            return []
        return [read_json(p) for p in sorted(self.requests.glob("*/status.json"))]

    def retry(self, request_id: str) -> bool:
        """Explicitly allow a failed request to be processed again on the next tick."""

        path = self._status_path(request_id)
        if not path.exists():
            return False
        current = read_json(path)
        if current.get("state") != FAILED:
            raise StopCondition("RETRY_REFUSED", "only a failed request can be retried")
        path.replace(
            path.with_name(f"status-failed-{self.clock().strftime('%Y%m%dT%H%M%SZ')}.json")
        )
        return True
