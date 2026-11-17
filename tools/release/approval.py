"""Owner approval records: bound to a manifest hash, a service list and a time window."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import Any

from .core import (
    Clock,
    ReleaseError,
    StopCondition,
    canonical_hash,
    format_utc,
    parse_utc,
    read_json,
    utc_now,
    write_json,
)
from .manifest import APPROVAL_SCHEMA, Manifest, manifest_hash, schema_errors

Approval = dict[str, Any]
# A toolchain safety cap, not an owner policy: no single window may be longer than this.
MAX_WINDOW = timedelta(hours=24)


def load_approval(path: Path | None) -> Approval:
    if path is None:
        raise StopCondition("APPROVAL_MISSING", "no owner approval record was supplied")
    try:
        approval = read_json(path)
    except ReleaseError as exc:
        if exc.code == "FILE_MISSING":
            raise StopCondition(
                "APPROVAL_MISSING", "the owner approval record does not exist"
            ) from exc
        raise
    schema = read_json(APPROVAL_SCHEMA)
    errors = schema_errors(approval, schema, schema)
    if errors:
        raise StopCondition("APPROVAL_INVALID", "; ".join(errors[:6]))
    return approval  # type: ignore[no-any-return]


def check_approval(
    approval: Approval,
    manifest: Manifest,
    *,
    action: str,
    services: list[str],
    clock: Clock = utc_now,
    consumed: frozenset[str] = frozenset(),
) -> None:
    """Every condition that must hold before an approved action starts."""

    if approval["manifest_sha256"] != manifest_hash(manifest):
        raise StopCondition(
            "APPROVAL_MANIFEST_MISMATCH", "the approval was given for a different manifest"
        )
    if approval["release_id"] != manifest["release_id"]:
        raise StopCondition("APPROVAL_MANIFEST_MISMATCH", "the approval names another release")
    if action not in approval["actions"]:
        raise StopCondition("APPROVAL_ACTION", f"the approval does not cover {action}")
    if sorted(approval["services"]) != sorted(services):
        raise StopCondition(
            "APPROVAL_SERVICE_MISMATCH",
            "the approved service list is not exactly the services this run would change",
        )
    if approval["risk_class"] != manifest["risk_class"]:
        raise StopCondition("APPROVAL_RISK_MISMATCH", "the approval names another risk class")
    start, end = parse_utc(approval["not_before"]), parse_utc(approval["expires_at"])
    if end <= start or end - start > MAX_WINDOW:
        raise StopCondition("APPROVAL_WINDOW_INVALID", "the approval window is empty or too long")
    now = clock()
    if now < start:
        raise StopCondition("APPROVAL_NOT_YET_VALID", "the approval window has not started")
    if now >= end:
        raise StopCondition(
            "APPROVAL_EXPIRED",
            "the approval window has ended; a new owner approval is needed (never extended)",
        )
    if f"{approval['approval_id']}:{action}" in consumed:
        raise StopCondition("APPROVAL_ALREADY_USED", "this approval has already been used")


def deadline(approval: Approval, clock: Clock = utc_now) -> Callable[[], None]:
    """A check the gate runs before every host or registry write."""

    end = parse_utc(approval["expires_at"])

    def check() -> None:
        if clock() >= end:
            raise StopCondition(
                "APPROVAL_EXPIRED",
                "the approval window ended during execution; stopped before the next change",
            )

    return check


def create_approval(
    manifest: Manifest,
    *,
    services: list[str],
    actions: list[str],
    auto_rollback: bool,
    not_before: str,
    expires_at: str,
    approved_by: str,
    confirm: Callable[[str], str],
    interactive: bool,
    clock: Clock = utc_now,
) -> Approval:
    """Record the owner's decision. The owner types the manifest hash prefix to confirm.

    Refused without an interactive terminal, so an automated process cannot approve its own
    release by running this command. This is a procedural control, not a signature.
    """

    if not interactive:
        raise StopCondition(
            "APPROVAL_NEEDS_OWNER", "approval must be typed by the owner at an interactive terminal"
        )
    digest = manifest_hash(manifest)
    start, end = parse_utc(not_before), parse_utc(expires_at)
    if end <= start or end - start > MAX_WINDOW:
        raise StopCondition("APPROVAL_WINDOW_INVALID", "the approval window is empty or too long")
    if sorted(services) != sorted(manifest["services_changed"]):
        raise StopCondition(
            "APPROVAL_SERVICE_MISMATCH", "approve exactly the services the manifest changes"
        )
    # T-1: a release whose source is an allow-listed release branch says so before approval.
    source_info = manifest.get("source", {})
    reason = source_info.get("base_reason", "INTEGRATION_BASELINE")
    lineage = (
        ""
        if reason == "INTEGRATION_BASELINE"
        else f"SOURCE IS NOT origin/main: release branch {source_info.get('base_ref')} ({reason}).\n"
    )
    typed = confirm(
        f"Release {manifest['release_id']} ({manifest['risk_class']}) changes "
        f"{', '.join(sorted(services))}; actions: {', '.join(sorted(actions))}; "
        f"automatic rollback: {'yes' if auto_rollback else 'no'}.\n"
        f"{lineage}"
        f"Window {format_utc(start)} to {format_utc(end)}.\n"
        f"Type the first 12 characters of the manifest hash to approve: "
    )
    if typed.strip().lower() != digest[:12]:
        raise StopCondition("APPROVAL_NOT_CONFIRMED", "the typed hash prefix does not match")
    now = clock()
    return {
        "schema_version": 1,
        "approval_id": f"apr-{digest[:12]}-{now.strftime('%Y%m%dT%H%M%SZ')}",
        "release_id": manifest["release_id"],
        "manifest_sha256": digest,
        "services": sorted(services),
        "risk_class": manifest["risk_class"],
        "actions": sorted(actions),
        "auto_rollback": auto_rollback,
        "not_before": format_utc(start),
        "expires_at": format_utc(end),
        "approved_by": approved_by,
        "approved_at": format_utc(now),
        "statement": (
            "I approve this exact manifest, these services and this window only. "
            "Expiry stops execution."
        ),
    }


def save_approval(path: Path, approval: Approval) -> str:
    if path.exists():
        raise StopCondition("APPROVAL_EXISTS", "an approval record already exists at that path")
    write_json(path, approval)
    return canonical_hash(approval)
