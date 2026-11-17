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

Planning reads only. In M1 the CLI (``scripts/p2_1_migration.py``) is dry-run only.
"""

from __future__ import annotations

import secrets
import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

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
    2. with no active version, the actor of the latest ``DRAFT_SAVED`` audit event;
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

    Not reachable from the M1 CLI (dry run only). ``definitions`` is a pymongo
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
