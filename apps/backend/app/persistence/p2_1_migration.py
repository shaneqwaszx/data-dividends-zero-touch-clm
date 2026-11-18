"""ADR-017 section 1.4 / B-0 section 2: the P2-1 governance migration (roll forward only).

Per workflow definition document (payload never changed):

* every existing version gets ``VersionProvenance`` with origin
  ``PRE_GOVERNANCE_DIRECTOR_ACTIVATION``: ``activated_by`` kept, ``author_id`` and
  ``approved_by`` None, the fixed ``LEGACY_VERSION_NOTE``. Legacy versions are never
  shown or counted as approved;
* a non-empty legacy ``draft_stages`` becomes a ``WITHDRAWN`` proposal with origin
  ``PRE_GOVERNANCE_DRAFT``, ``author_id`` None and ``legacy_editor`` per ADR-017 1.4 (see
  ``legacy_draft_proposal``), kept as a decided entry with its
  full record. Its id and timestamps are derived from the stored document only, so a
  re-run produces byte-identical cold content;
* ``required_baseline`` is seeded from the **currently active** version only, by the
  injected ``seed_baseline`` (``services/workflow_ratchet.py``); no active version gives
  ``RequiredBaseline()``;
* one ``MIGRATED`` governance event, referenced by the outbox for the archiver.

Order: cold copies of every existing version and of the legacy draft proposal are
inserted durably **first** (idempotent: a re-run's duplicate gets a fresh attempt suffix,
fallback mode), then **one** compare-and-set on ``_id``, revision and nonce, filtered on the
marker being absent, writes every governance field with the marker **last**. Re-running
after the marker is a no-op; an interrupted run re-runs safely.

Planning reads only. The CLI (``scripts/p2_1_migration.py``) dry-runs by default; its
owner-approved apply mode (2026-11-18) adds a signed window approval, a verified backup,
writer quiescence (no live dispatch lease plus an exclusive migration lock that backend
startup refuses), a fresh plan whose hash must equal the dry run's, and post-apply
P2-1 verification; the helpers for those steps are at the end of this module.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pymongo.errors import DuplicateKeyError, PyMongoError

from app.domain.workflow_governance import (
    FIELD_MIGRATION_MARKER,
    GOVERNANCE_TOP_LEVEL_FIELDS,
    HARD_CEILING_BYTES,
    LEGACY_VERSION_NOTE,
    MAX_BASELINE_BYTES,
    DecidedProposalEntry,
    GovernanceEvent,
    GovernanceEventKind,
    MigrationMarker,
    OutboxCollection,
    ProposalKind,
    ProposalOrigin,
    ProposalState,
    RequiredBaseline,
    VersionOrigin,
    VersionProvenance,
    WorkflowGovernanceState,
    WorkflowProposal,
    canonical_json,
    proposal_content_hash,
    record_content_hash,
    version_logical_id,
)
from app.domain.workflows import WorkflowDefinition, WorkflowVersion
from app.persistence.adr017_backfill import DURABLE, DefinitionFinding, verify_definition_document
from app.persistence.workflow_governance_store import (
    ColdHistoryIntegrityError,
    ColdHistoryStore,
    archive_record,
    decided_entry,
    encode_governance_fields,
    encoded_size,
    governed_document,
    lookup_cold,
    outbox_for_event,
)

P2_1_MIGRATION_TOOL_VERSION = "p2-1-m1"
DRAFT_SAVED_ACTION = "DRAFT_SAVED"
# Fixed namespace: a legacy draft's proposal id depends only on its workflow and content.
LEGACY_DRAFT_NAMESPACE = uuid.UUID("6f1c2b0e-5d1a-4f7e-9a51-2b7d9c3e8a10")
MIGRATED_EVENT_SUMMARY = (
    "Migrated to approval governance; earlier versions were activated before governance."
)

SeedBaseline = Callable[[WorkflowVersion], RequiredBaseline]


class MigrationRefusedError(RuntimeError):
    """The plan has refusals, or a definition changed after it was planned."""


@dataclass(frozen=True)
class ColdInsert:
    collection: OutboxCollection
    logical_id: str
    content_hash: str
    record: Mapping[str, Any]


@dataclass(frozen=True)
class PlannedMigration:
    workflow_id: str
    revision: int
    write_nonce: str | None
    governance: WorkflowGovernanceState
    cold_inserts: tuple[ColdInsert, ...]

    def summary(self) -> dict[str, object]:
        marker = self.governance.migration_marker
        assert marker is not None
        return {
            "id": self.workflow_id,
            "legacy_versions": marker.legacy_versions,
            "legacy_draft_converted": marker.legacy_draft_converted,
            "baseline_seeded_from_version": marker.baseline_seeded_from_version,
            "baseline_stages": len(self.governance.required_baseline.stages),
            "cold_inserts": len(self.cold_inserts),
            "outbox_entries": len(self.governance.outbox),
        }


@dataclass
class P21MigrationPlan:
    migrations: list[PlannedMigration] = field(default_factory=list)
    already_migrated: list[str] = field(default_factory=list)
    refusals: list[DefinitionFinding] = field(default_factory=list)

    @property
    def refused(self) -> bool:
        return bool(self.refusals)

    def summary(self) -> dict[str, object]:
        """Safe identifiers, counts and reasons only; never document content."""

        return {
            "to_migrate": [item.summary() for item in self.migrations],
            "already_migrated": sorted(self.already_migrated),
            "refusals": [{"id": item.workflow_id, "reason": item.reason} for item in self.refusals],
        }


def legacy_draft_proposal(
    definition: WorkflowDefinition,
    *,
    base_version: int,
    active_version: WorkflowVersion | None,
) -> WorkflowProposal | None:
    """The authorless WITHDRAWN proposal for a non-empty legacy ``draft_stages``.

    ``legacy_editor`` precedence (ADR-017 1.4 outranks the programme brief):
    1. the ``activated_by`` of the version active at migration (the D-123 Director editor);
    2. with no active version, the actor of the latest ``DRAFT_SAVED`` audit event
       (project-defined fallback, not sponsor-confirmed; ADR-017 1.4 names only 1);
    3. otherwise None. Authorship is never inferred: ``author_id`` stays None.
    """

    if not definition.draft_stages:
        return None
    saved = [item for item in definition.audit if item.action == DRAFT_SAVED_ACTION]
    latest = saved[-1] if saved else None
    if active_version is not None:
        editor: str | None = active_version.activated_by
    else:
        editor = None if latest is None else latest.actor_id
    at = latest.occurred_at if latest is not None else definition.updated_at
    content = proposal_content_hash(ProposalKind.CHANGE, definition.draft_stages)
    proposal_id = uuid.uuid5(LEGACY_DRAFT_NAMESPACE, f"{definition.workflow_id}:{content}")
    return WorkflowProposal(
        proposal_id=str(proposal_id),
        workflow_id=definition.workflow_id,
        kind=ProposalKind.CHANGE,
        state=ProposalState.WITHDRAWN,
        origin=ProposalOrigin.PRE_GOVERNANCE_DRAFT,
        base_version=base_version,
        stages=definition.draft_stages,
        author_id=None,
        legacy_editor=editor,
        created_at=at,
        updated_at=at,
        last_activity_at=at,
        withdrawn_at=at,
    )


def legacy_provenance(version: WorkflowVersion) -> VersionProvenance:
    return VersionProvenance(
        version=version.version,
        origin=VersionOrigin.PRE_GOVERNANCE_DIRECTOR_ACTIVATION,
        author_id=None,
        approved_by=None,
        proposal_id=None,
        activated_by=version.activated_by,
        published_at=version.activated_at,
        note=LEGACY_VERSION_NOTE,
    )


def plan_definition_migration(
    raw: Mapping[str, Any],
    *,
    seed_baseline: SeedBaseline,
    now: datetime,
    cold: ColdHistoryStore | None = None,
) -> PlannedMigration | DefinitionFinding | None:
    """Read-only. ``None`` = already migrated (no-op); a finding = refusal."""

    workflow_id = str(raw.get("_id"))

    def refuse(reason: str) -> DefinitionFinding:
        return DefinitionFinding(workflow_id, reason)

    if FIELD_MIGRATION_MARKER in raw:
        return None
    if any(name in raw for name in GOVERNANCE_TOP_LEVEL_FIELDS):
        # One CAS writes every field, so partial governance content is never ours.
        return refuse("GOVERNANCE_FIELDS_WITHOUT_MARKER")
    structural = verify_definition_document(raw)
    if structural is not None:
        return refuse(structural)
    revision = raw.get("revision")
    if type(revision) is not int:
        return refuse("REVISION_INVALID")
    nonce = raw.get("write_nonce")
    if nonce is not None and not isinstance(nonce, str):
        return refuse("NONCE_INVALID")
    try:
        definition = WorkflowDefinition.model_validate(raw["payload"])
    except Exception:  # noqa: BLE001
        return refuse("DEFINITION_INVALID")
    if definition.workflow_id != workflow_id:
        return refuse("DEFINITION_ID_MISMATCH")
    active = raw["active_version"]
    active_version = next((item for item in definition.versions if item.version == active), None)
    if active and active_version is None:
        return refuse("ACTIVE_VERSION_NOT_HOT")
    try:
        baseline = RequiredBaseline() if active_version is None else seed_baseline(active_version)
    except Exception:  # noqa: BLE001 - a seeding failure is a refusal, never a guess
        return refuse("BASELINE_SEED_FAILED")
    if encoded_size({"v": baseline.model_dump(mode="json")}) > MAX_BASELINE_BYTES:
        return refuse("BASELINE_TOO_LARGE")
    try:
        draft = legacy_draft_proposal(
            definition, base_version=active, active_version=active_version
        )
    except Exception:  # noqa: BLE001
        return refuse("LEGACY_DRAFT_INVALID")

    inserts = [
        ColdInsert(
            collection=OutboxCollection.VERSIONS,
            logical_id=version_logical_id(workflow_id, item.version),
            content_hash=record_content_hash(item),
            record=item.model_dump(mode="json"),
        )
        for item in definition.versions
    ]
    decided: tuple[DecidedProposalEntry, ...] = ()
    if draft is not None:
        entry = decided_entry(draft, ended_at=draft.updated_at)
        # Its cold copy is durably acknowledged before the marker CAS (inserted first).
        decided = (entry.model_copy(update={"archived": True}),)
        inserts.append(
            ColdInsert(
                collection=OutboxCollection.PROPOSALS,
                logical_id=draft.proposal_id,
                content_hash=entry.record_hash,
                record=draft.model_dump(mode="json"),
            )
        )
    event = GovernanceEvent(
        sequence=1,
        occurred_at=now,
        actor_id=None,
        kind=GovernanceEventKind.MIGRATED,
        version=active or None,
        summary=MIGRATED_EVENT_SUMMARY,
    )
    try:
        governance = WorkflowGovernanceState(
            migration_marker=MigrationMarker(
                migrated_at=now,
                tool_version=P2_1_MIGRATION_TOOL_VERSION,
                legacy_versions=len(definition.versions),
                legacy_draft_converted=draft is not None,
                baseline_seeded_from_version=active or None,
            ),
            required_baseline=baseline,
            decided_proposals=decided,
            governance_events=(event,),
            outbox=(outbox_for_event(workflow_id, event),),
            version_provenance=tuple(legacy_provenance(item) for item in definition.versions),
            governance_sequence=1,
        )
    except Exception:  # noqa: BLE001
        return refuse("GOVERNANCE_STATE_INVALID")
    document = governed_document(
        definition,
        governance,
        write_nonce=nonce,
        active_version=active,
        latest_version=raw["latest_version"],
    )
    if encoded_size(document) > HARD_CEILING_BYTES:
        return refuse("DOCUMENT_TOO_LARGE")
    if cold is not None:
        try:
            for insert in inserts:
                lookup_cold(
                    cold, insert.collection, insert.logical_id, expected_hash=insert.content_hash
                )
        except ColdHistoryIntegrityError:
            return refuse("COLD_INTEGRITY_CONFLICT")
        except Exception:  # noqa: BLE001
            return refuse("COLD_STORE_UNAVAILABLE")
    return PlannedMigration(
        workflow_id=workflow_id,
        revision=revision,
        write_nonce=nonce,
        governance=governance,
        cold_inserts=tuple(inserts),
    )


def plan_p2_1_migration(
    raws: Iterable[Mapping[str, Any]],
    *,
    seed_baseline: SeedBaseline,
    now: datetime,
    cold: ColdHistoryStore | None = None,
) -> P21MigrationPlan:
    """Dry run: per-document planned changes and refusals. Writes nothing."""

    plan = P21MigrationPlan()
    for raw in raws:
        outcome = plan_definition_migration(raw, seed_baseline=seed_baseline, now=now, cold=cold)
        if outcome is None:
            plan.already_migrated.append(str(raw.get("_id")))
        elif isinstance(outcome, DefinitionFinding):
            plan.refusals.append(outcome)
        else:
            plan.migrations.append(outcome)
    return plan


def store_cold_inserts(planned: PlannedMigration, cold: ColdHistoryStore, *, now: datetime) -> None:
    """Step 1: every cold copy, each with its own durable acknowledgement (fallback mode)."""

    for insert in planned.cold_inserts:
        archive_record(
            cold,
            collection=insert.collection,
            logical_id=insert.logical_id,
            content_hash=insert.content_hash,
            workflow_id=planned.workflow_id,
            record=insert.record,
            now=now,
        )


def apply_p2_1_migration(
    plan: P21MigrationPlan,
    definitions: Any,
    cold: ColdHistoryStore,
    *,
    now: datetime,
) -> int:
    """All-or-nothing gate, then per document: cold copies, then the marker CAS.

    Reached from the CLI only through the guarded apply mode. ``definitions`` is a pymongo
    collection (or a test double with ``with_options`` and ``update_one``).
    """

    if plan.refused:
        raise MigrationRefusedError("the P2-1 migration plan has refusals")
    durable = definitions.with_options(write_concern=DURABLE)
    applied = 0
    for planned in plan.migrations:
        store_cold_inserts(planned, cold, now=now)
        fields = encode_governance_fields(planned.governance)  # marker last
        result = durable.update_one(
            {
                "_id": planned.workflow_id,
                "revision": planned.revision,
                "write_nonce": (
                    planned.write_nonce if planned.write_nonce is not None else {"$exists": False}
                ),
                FIELD_MIGRATION_MARKER: {"$exists": False},
            },
            {"$set": {"write_nonce": secrets.token_hex(16), **fields}},
        )
        if result.modified_count != 1:
            raise MigrationRefusedError("a definition changed after it was planned")
        applied += 1
    return applied


# --- Owner-approved apply mode (2026-11-18): plan hash, window approval, backup, quiescence,
# --- the migration lock. None of these connect to anything; callers pass collections.

WINDOW_APPROVAL_FORMAT = "clm-p2-1-migration-window/v1"
BACKUP_MANIFEST_FORMAT_PREFIX = "mongo-gzip-archive/"  # deploy/recovery manifest convention
PROTECTED_DATABASES = frozenset({"clm_poc", "clm_staging"})
MAX_WINDOW = timedelta(hours=12)
MIGRATION_LOCK_COLLECTION = "clm_migration_locks"
MIGRATION_LOCK_ID = "p2_1_governance_migration"
# Leases are written with the server clock ($$NOW); a client-side check treats any lease
# ending within this skew of "now" as still live (fail closed).
LEASE_CLOCK_SKEW = timedelta(minutes=5)


class ApplyPreconditionError(RuntimeError):
    """A precondition for the apply mode is not met; ``reason`` is a stable safe code."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class MigrationLockHeldError(ApplyPreconditionError):
    def __init__(self, lock: Mapping[str, Any]) -> None:
        super().__init__("MIGRATION_LOCK_HELD")
        self.lock = safe_lock_summary(lock)


def plan_hash(plan: P21MigrationPlan) -> str:
    """SHA-256 over what the apply would write, independent of the run's clock.

    Covers per document the id, revision and nonce read (so any write between the dry
    run and the apply changes the hash), the cold inserts and the governance fields with
    the run-time timestamps (marker ``migrated_at``, the MIGRATED event time and the
    event's outbox hash) blanked; plus the already-migrated ids and the refusals.
    """

    def governance(item: PlannedMigration) -> dict[str, Any]:
        dumped = item.governance.model_dump(mode="json")
        dumped["migration_marker"]["migrated_at"] = None
        for event in dumped["governance_events"]:
            event["occurred_at"] = None
        for entry in dumped["outbox"]:
            if entry["collection"] == OutboxCollection.EVENTS.value:
                entry["content_hash"] = None
        return dumped

    body = {
        "tool_version": P2_1_MIGRATION_TOOL_VERSION,
        "migrations": [
            {
                "id": item.workflow_id,
                "revision": item.revision,
                "write_nonce": item.write_nonce,
                "cold": [
                    [insert.collection.value, insert.logical_id, insert.content_hash]
                    for insert in item.cold_inserts
                ],
                "governance": governance(item),
            }
            for item in sorted(plan.migrations, key=lambda value: value.workflow_id)
        ],
        "already_migrated": sorted(plan.already_migrated),
        "refusals": sorted([item.workflow_id, item.reason] for item in plan.refusals),
    }
    return hashlib.sha256(canonical_json(body)).hexdigest()


def _utc(value: Any, reason: str) -> datetime:
    if not isinstance(value, str):
        raise ApplyPreconditionError(reason)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ApplyPreconditionError(reason) from None
    if parsed.tzinfo is None:
        raise ApplyPreconditionError(reason)
    return parsed.astimezone(UTC)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class WindowApproval:
    """The owner-signed window approval (``WINDOW_APPROVAL_FORMAT``).

    JSON fields: ``format``, ``database``, ``window_id``, ``start_utc``, ``end_utc`` (ISO-8601
    with an offset; window at most 12 h), ``approver``, and ``backup``:
    ``{"manifest_path", "manifest_sha256"[, "archive_path"]}``. Relative paths resolve
    against the approval file's directory.
    """

    database: str
    window_id: str
    start: datetime
    end: datetime
    approver: str
    manifest_path: Path
    manifest_sha256: str
    archive_path: Path | None
    approval_sha256: str

    def summary(self) -> dict[str, object]:
        return {
            "database": self.database,
            "window_id": self.window_id,
            "start_utc": self.start.isoformat(),
            "end_utc": self.end.isoformat(),
            "approver": self.approver,
            "approval_sha256": self.approval_sha256,
            "backup_manifest_sha256": self.manifest_sha256,
        }


def load_window_approval(path: Path, *, database: str, now: datetime) -> WindowApproval:
    """Validate the approval for this database and this moment; refuse otherwise."""

    if not path.is_file():
        raise ApplyPreconditionError("WINDOW_APPROVAL_MISSING")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise ApplyPreconditionError("WINDOW_APPROVAL_INVALID") from None
    if not isinstance(raw, dict) or raw.get("format") != WINDOW_APPROVAL_FORMAT:
        raise ApplyPreconditionError("WINDOW_APPROVAL_INVALID")
    named = raw.get("database")
    if not isinstance(named, str) or not named.strip():
        raise ApplyPreconditionError("WINDOW_APPROVAL_INVALID")
    if named.strip().lower() != database.strip().lower():
        raise ApplyPreconditionError("WINDOW_APPROVAL_DATABASE_MISMATCH")
    window_id, approver = raw.get("window_id"), raw.get("approver")
    if not all(
        isinstance(item, str) and 0 < len(item.strip()) <= 120 for item in (window_id, approver)
    ):
        raise ApplyPreconditionError("WINDOW_APPROVAL_INVALID")
    start = _utc(raw.get("start_utc"), "WINDOW_APPROVAL_INVALID")
    end = _utc(raw.get("end_utc"), "WINDOW_APPROVAL_INVALID")
    if not start < end or end - start > MAX_WINDOW:
        raise ApplyPreconditionError("WINDOW_APPROVAL_INVALID")
    if not start <= now.astimezone(UTC) <= end:
        raise ApplyPreconditionError("OUTSIDE_APPROVED_WINDOW")
    backup = raw.get("backup")
    if not isinstance(backup, dict):
        raise ApplyPreconditionError("BACKUP_NOT_NAMED")
    manifest, manifest_hash = backup.get("manifest_path"), backup.get("manifest_sha256")
    if not isinstance(manifest, str) or not isinstance(manifest_hash, str):
        raise ApplyPreconditionError("BACKUP_NOT_NAMED")
    if not _SHA256.fullmatch(manifest_hash):
        raise ApplyPreconditionError("BACKUP_NOT_NAMED")
    archive = backup.get("archive_path")
    if archive is not None and not isinstance(archive, str):
        raise ApplyPreconditionError("WINDOW_APPROVAL_INVALID")
    base = path.parent

    def resolve(value: str) -> Path:
        candidate = Path(value)
        return candidate if candidate.is_absolute() else base / candidate

    return WindowApproval(
        database=named.strip(),
        window_id=str(window_id).strip(),
        start=start,
        end=end,
        approver=str(approver).strip(),
        manifest_path=resolve(manifest),
        manifest_sha256=manifest_hash,
        archive_path=None if archive is None else resolve(archive),
        approval_sha256=_sha256_file(path),
    )


def protected_database_allowed(database: str, approval: WindowApproval | None) -> bool:
    """``clm_poc`` / ``clm_staging`` only when the approval names exactly that database."""

    name = database.strip().lower()
    if name not in PROTECTED_DATABASES:
        return True
    return approval is not None and approval.database.strip().lower() == name


def verify_backup(approval: WindowApproval, *, database: str, now: datetime) -> dict[str, object]:
    """The backup named by the approval exists and is the one recorded.

    The manifest follows the ``deploy/recovery`` convention (JSON with ``format`` starting
    ``mongo-gzip-archive/``, ``database``, ``boundary_utc``, ``sha256`` and ``bytes`` of the
    archive). Its SHA-256 must equal the approval's ``manifest_sha256``; its database must
    be this database; its boundary must lie inside the window and not in the future. With
    ``archive_path`` set, the archive's size and SHA-256 must equal the manifest's.
    """

    path = approval.manifest_path
    if not path.is_file():
        raise ApplyPreconditionError("BACKUP_MANIFEST_MISSING")
    if _sha256_file(path) != approval.manifest_sha256:
        raise ApplyPreconditionError("BACKUP_MANIFEST_HASH_MISMATCH")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise ApplyPreconditionError("BACKUP_MANIFEST_INVALID") from None
    if not isinstance(manifest, dict):
        raise ApplyPreconditionError("BACKUP_MANIFEST_INVALID")
    kind, archive_hash, size = manifest.get("format"), manifest.get("sha256"), manifest.get("bytes")
    if (
        not isinstance(kind, str)
        or not kind.startswith(BACKUP_MANIFEST_FORMAT_PREFIX)
        or not isinstance(archive_hash, str)
        or not _SHA256.fullmatch(archive_hash)
        or type(size) is not int
        or size <= 0
    ):
        raise ApplyPreconditionError("BACKUP_MANIFEST_INVALID")
    named = manifest.get("database")
    if not isinstance(named, str) or named.strip().lower() != database.strip().lower():
        raise ApplyPreconditionError("BACKUP_DATABASE_MISMATCH")
    boundary = _utc(manifest.get("boundary_utc"), "BACKUP_MANIFEST_INVALID")
    if not approval.start <= boundary <= now.astimezone(UTC):
        raise ApplyPreconditionError("BACKUP_NOT_IN_WINDOW")
    if approval.archive_path is not None:
        archive = approval.archive_path
        if not archive.is_file():
            raise ApplyPreconditionError("BACKUP_ARCHIVE_MISSING")
        if archive.stat().st_size != size or _sha256_file(archive) != archive_hash:
            raise ApplyPreconditionError("BACKUP_ARCHIVE_HASH_MISMATCH")
    return {
        "backup_boundary_utc": boundary.isoformat(),
        "backup_archive_sha256": archive_hash,
        "backup_archive_verified": approval.archive_path is not None,
    }


def _as_utc(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def live_dispatch_leases(cases: Any, *, now: datetime) -> int:
    """Read-only: case ledger entries whose ``workflow_dispatch`` claim may still be live.

    A claim counts as live unless its entry is FINALIZED or its ``lease_until`` ended more
    than ``LEASE_CLOCK_SKEW`` before ``now``; a claim without a readable lease is live.
    Any live claim means a P2-0 or P2-1 writer may be running (mixed-version refusal).
    """

    threshold = now.astimezone(UTC) - LEASE_CLOCK_SKEW
    live = 0
    for raw in cases.find({}, {"target_executions": 1}):
        for entry in raw.get("target_executions") or ():
            if not isinstance(entry, dict):
                continue
            claim = entry.get("workflow_dispatch")
            if not isinstance(claim, dict) or entry.get("state") == "FINALIZED":
                continue
            lease = _as_utc(claim.get("lease_until"))
            if lease is None or lease > threshold:
                live += 1
    return live


def safe_lock_summary(lock: Mapping[str, Any]) -> dict[str, object]:
    return {
        key: (value.isoformat() if isinstance(value, datetime) else value)
        for key, value in lock.items()
        if key in {"lock_id", "database", "window_id", "acquired_at", "expires_at", "state"}
    }


def read_migration_lock(locks: Any) -> dict[str, Any] | None:
    """For the backend startup hook: a present lock means a migration owns the database."""

    found = locks.find_one({"_id": MIGRATION_LOCK_ID})
    return None if found is None else dict(found)


def acquire_migration_lock(
    locks: Any, *, approval: WindowApproval, now: datetime, lock_id: str | None = None
) -> str:
    """Insert-only, durable. A present lock is never overwritten (``MigrationLockHeldError``)."""

    token = lock_id or secrets.token_hex(16)
    document = {
        "_id": MIGRATION_LOCK_ID,
        "lock_id": token,
        "state": "HELD",
        "database": approval.database,
        "window_id": approval.window_id,
        "acquired_at": now,
        "expires_at": approval.end,
        "tool_version": P2_1_MIGRATION_TOOL_VERSION,
    }
    try:
        locks.with_options(write_concern=DURABLE).insert_one(document)
    except DuplicateKeyError:
        existing = read_migration_lock(locks) or {}
        raise MigrationLockHeldError(existing) from None
    except PyMongoError:
        raise ApplyPreconditionError("MIGRATION_LOCK_OUTCOME_UNKNOWN") from None
    return token


def resume_migration_lock(
    locks: Any, *, approval: WindowApproval, expected_lock_id: str, now: datetime
) -> str:
    """Explicit stale-lock handling: take over the lock of an interrupted run **of the same
    approved window and database** only, by its exact id (durable CAS, new id)."""

    token = secrets.token_hex(16)
    try:
        result = locks.with_options(write_concern=DURABLE).update_one(
            {
                "_id": MIGRATION_LOCK_ID,
                "lock_id": expected_lock_id,
                "window_id": approval.window_id,
                "database": approval.database,
            },
            {"$set": {"lock_id": token, "acquired_at": now, "expires_at": approval.end}},
        )
    except PyMongoError:
        raise ApplyPreconditionError("MIGRATION_LOCK_OUTCOME_UNKNOWN") from None
    if result.modified_count != 1:
        raise ApplyPreconditionError("MIGRATION_LOCK_NOT_RESUMABLE")
    return token


def release_migration_lock(locks: Any, lock_id: str) -> bool:
    """Durable delete filtered on the exact lock id (never another run's lock)."""

    try:
        result = locks.with_options(write_concern=DURABLE).delete_one(
            {"_id": MIGRATION_LOCK_ID, "lock_id": lock_id}
        )
    except PyMongoError:
        return False
    return bool(result.deleted_count == 1)
