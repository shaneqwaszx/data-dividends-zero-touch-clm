"""ADR-017 section 3.5 one-time P2-0 backfill and the startup re-verification.

Backfill (P2-0 only; never after P2-1): for every workflow definition document without
``latest_version``, set ``latest_version`` to the highest version number present and
``active_version`` to that same number (0 if none), ``dispatch_authorisation_seq`` to 0,
under the durable write rule, compare-and-set on the revision and nonce read. Apply
refuses while the plan has any refusal, then writes per document: a document that
changed after planning stops it, and a re-run resumes (QG R0 P3-6). Its rule is
valid only while every version is hot, nothing is archived or deactivated and every version
is a migrated pre-governance activation. Dry-run by default; idempotent.

Startup re-verification (every start): each definition document must have strictly
increasing hot version numbers whose last equals ``latest_version``; ``active_version`` is 0
or ``latest_version`` (onboarding: equal once anything is published); no version number
exceeds ``latest_version``. Any failure makes the fence refuse every dispatch. The P2-1
provenance rule applies only after the P2-1 migration marker, which P2-0 never writes.
"""

from __future__ import annotations

import secrets
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from pymongo.collection import Collection
from pymongo.write_concern import WriteConcern

from app.domain.workflow_governance import (
    DecidedProposalEntry,
    GovernanceEventKind,
    OutboxCollection,
    ProposalState,
    VersionOrigin,
    WorkflowGovernanceState,
    WorkflowProposal,
    event_logical_id,
    record_content_hash,
    version_logical_id,
)
from app.domain.workflows import ONBOARDING_WORKFLOW_ID, WorkflowDefinition
from app.persistence.errors import PersistenceError
from app.persistence.workflow_governance_store import (
    ColdHistoryIntegrityError,
    ColdHistoryStore,
    decode_governance_fields,
    dict_hash,
    lookup_cold,
    outbox_record,
)

DURABLE = WriteConcern(w="majority", j=True, wtimeout=5_000)
P2_1_MIGRATION_MARKER = "p2_1_migration_marker"


@dataclass(frozen=True)
class DefinitionFinding:
    workflow_id: str
    reason: str


@dataclass
class BackfillPlan:
    changes: list[tuple[str, int, str | None, int]] = field(default_factory=list)
    already_backfilled: int = 0
    refusals: list[DefinitionFinding] = field(default_factory=list)

    def summary(self) -> dict[str, object]:
        return {
            "to_backfill": [
                {"id": wid, "latest_version": version} for wid, _, _, version in self.changes
            ],
            "already_backfilled": self.already_backfilled,
            "refusals": [{"id": item.workflow_id, "reason": item.reason} for item in self.refusals],
        }


class BackfillRefusedError(RuntimeError):
    pass


def _versions(raw: Mapping[str, Any]) -> list[int]:
    definition = WorkflowDefinition.model_validate(raw["payload"])
    return [item.version for item in definition.versions]


def verify_definition_document(raw: Mapping[str, Any]) -> str | None:
    """The startup checks; return a refusal reason, or None when the document is sound."""

    workflow_id = str(raw.get("_id"))
    if P2_1_MIGRATION_MARKER in raw:
        return "P2_1_CONTENT_NOT_SUPPORTED_BY_P2_0"
    latest, active = raw.get("latest_version"), raw.get("active_version")
    if type(latest) is not int or type(active) is not int:
        return "NOT_BACKFILLED"
    try:
        versions = _versions(raw)
    except Exception:  # noqa: BLE001
        return "DEFINITION_INVALID"
    if any(later <= earlier for earlier, later in zip(versions, versions[1:], strict=False)):
        return "VERSIONS_NOT_STRICTLY_INCREASING"
    if (versions[-1] if versions else 0) != latest:
        return "LAST_VERSION_NOT_LATEST"
    if any(version > latest for version in versions):
        return "VERSION_ABOVE_LATEST"
    if active not in {0, latest}:
        return "ACTIVE_NOT_ZERO_OR_LATEST"
    if workflow_id == ONBOARDING_WORKFLOW_ID and latest > 0 and active != latest:
        return "ONBOARDING_NOT_ACTIVE"
    return None


def verify_definitions(raws: Iterable[Mapping[str, Any]]) -> list[DefinitionFinding]:
    findings = []
    for raw in raws:
        reason = verify_definition_document(raw)
        if reason is not None:
            findings.append(DefinitionFinding(str(raw.get("_id")), reason))
    return findings


def plan_backfill(definitions: Collection[dict[str, Any]]) -> BackfillPlan:
    plan = BackfillPlan()
    for raw in definitions.find({}):
        workflow_id = str(raw.get("_id"))
        if P2_1_MIGRATION_MARKER in raw:
            plan.refusals.append(DefinitionFinding(workflow_id, "P2_1_MIGRATED"))
            continue
        if "latest_version" in raw or "active_version" in raw:
            reason = verify_definition_document(raw)
            if reason is None:
                plan.already_backfilled += 1
            else:
                plan.refusals.append(DefinitionFinding(workflow_id, reason))
            continue
        try:
            versions = _versions(raw)
        except Exception:  # noqa: BLE001
            plan.refusals.append(DefinitionFinding(workflow_id, "DEFINITION_INVALID"))
            continue
        if any(later <= earlier for earlier, later in zip(versions, versions[1:], strict=False)):
            plan.refusals.append(DefinitionFinding(workflow_id, "VERSIONS_NOT_STRICTLY_INCREASING"))
            continue
        revision = raw.get("revision")
        if type(revision) is not int:
            plan.refusals.append(DefinitionFinding(workflow_id, "REVISION_INVALID"))
            continue
        nonce = raw.get("write_nonce")
        known_nonce = nonce if isinstance(nonce, str) else None
        plan.changes.append((workflow_id, revision, known_nonce, max(versions, default=0)))
    return plan


def apply_backfill(plan: BackfillPlan, definitions: Collection[dict[str, Any]]) -> int:
    if plan.refusals:
        raise BackfillRefusedError("the backfill plan has refusals")
    durable = definitions.with_options(write_concern=DURABLE)
    applied = 0
    for workflow_id, revision, nonce, latest in plan.changes:
        result = durable.update_one(
            {
                "_id": workflow_id,
                "revision": revision,
                "write_nonce": nonce if nonce is not None else {"$exists": False},
                "latest_version": {"$exists": False},
                "active_version": {"$exists": False},
            },
            {
                "$set": {
                    "latest_version": latest,
                    "active_version": latest,
                    "dispatch_authorisation_seq": 0,
                    # The backfill is a definition writer: it rotates the nonce. ``revision``
                    # stays equal to the payload revision that legacy code compares.
                    "write_nonce": secrets.token_hex(16),
                }
            },
        )
        if result.modified_count != 1:
            raise BackfillRefusedError("a definition changed after it was planned")
        applied += 1
    return applied


# --- P2-1 startup verification (P2-1 release; ADR-017 3.5 R3-3, section 5) ----------------


def verify_p2_1_definition_document(
    raw: Mapping[str, Any], *, cold: ColdHistoryStore | None = None
) -> str | None:
    """The P2-1 startup checks on one definition document; a refusal reason, or None.

    Fails closed. The P2-1 migration marker is required; the P2-0 structural checks above
    still apply; every version carries provenance, legacy provenance exists only for the
    migrated versions and precedes every governed version, and governed provenance
    (``GOVERNED_APPROVAL`` with its approved proposal record, ``EMERGENCY_FALLBACK`` with
    its event or notice) covers everything published after the marker; no version above
    ``latest_version`` exists hot or cold; every outbox reference resolves to a hot record
    that is still present in full with a matching hash; cold history is consistent.
    ``verify_definition_document`` (the P2-0 check) keeps refusing marked documents.
    """

    if P2_1_MIGRATION_MARKER not in raw:
        return "P2_1_NOT_MIGRATED"
    structural = verify_definition_document(
        {key: value for key, value in raw.items() if key != P2_1_MIGRATION_MARKER}
    )
    if structural is not None:
        return structural
    try:
        definition = WorkflowDefinition.model_validate(raw["payload"])
        state = decode_governance_fields(raw)
    except Exception:  # noqa: BLE001 - any decode failure is a refusal
        return "GOVERNANCE_STATE_INVALID"
    if state.migration_marker is None:
        return "GOVERNANCE_STATE_INVALID"
    latest = int(raw["latest_version"])
    try:
        return (
            _verify_provenance(definition, state, latest, cold)
            or _verify_hot_history(definition, state)
            or (None if cold is None else _verify_cold(definition, state, latest, cold))
        )
    except ColdHistoryIntegrityError:
        return "COLD_INTEGRITY_FAILURE"
    except PersistenceError:
        return "COLD_STORE_UNAVAILABLE"
    except Exception:  # noqa: BLE001 - an undecodable cold record is a refusal
        return "COLD_INTEGRITY_FAILURE"


def verify_p2_1_definitions(
    raws: Iterable[Mapping[str, Any]], *, cold: ColdHistoryStore | None = None
) -> list[DefinitionFinding]:
    findings = []
    for raw in raws:
        reason = verify_p2_1_definition_document(raw, cold=cold)
        if reason is not None:
            findings.append(DefinitionFinding(str(raw.get("_id")), reason))
    return findings


def _approved_record(
    version: int,
    proposal_id: str | None,
    decided: Mapping[str, DecidedProposalEntry],
    workflow_id: str,
    cold: ColdHistoryStore | None,
) -> bool:
    if proposal_id is None:
        return False
    entry = decided.get(proposal_id)
    if entry is not None:
        return entry.state == ProposalState.APPROVED and entry.published_version == version
    if cold is None:
        return False
    found = lookup_cold(cold, OutboxCollection.PROPOSALS, proposal_id)
    if found is None:
        return False
    proposal = WorkflowProposal.model_validate(found.record)
    return (
        proposal.workflow_id == workflow_id
        and proposal.state == ProposalState.APPROVED
        and proposal.published_version == version
    )


def _verify_provenance(
    definition: WorkflowDefinition,
    state: WorkflowGovernanceState,
    latest: int,
    cold: ColdHistoryStore | None,
) -> str | None:
    marker = state.migration_marker
    if marker is None:
        return "P2_1_NOT_MIGRATED"
    provenance = state.version_provenance
    numbers = [item.version for item in provenance]
    if any(later <= earlier for earlier, later in zip(numbers, numbers[1:], strict=False)):
        return "PROVENANCE_NOT_STRICTLY_INCREASING"
    if numbers and numbers[-1] > latest:
        return "PROVENANCE_ABOVE_LATEST"
    if latest > 0 and latest not in numbers:
        return "LATEST_WITHOUT_PROVENANCE"
    recorded = set(numbers)
    if any(item.version not in recorded for item in definition.versions):
        # A version written by a P2-0 (legacy) writer after the marker has no provenance.
        return "VERSION_WITHOUT_PROVENANCE"
    legacy = [
        item.version
        for item in provenance
        if item.origin == VersionOrigin.PRE_GOVERNANCE_DIRECTOR_ACTIVATION
    ]
    governed = [
        item
        for item in provenance
        if item.origin != VersionOrigin.PRE_GOVERNANCE_DIRECTOR_ACTIVATION
    ]
    if len(legacy) != marker.legacy_versions:
        return "LEGACY_PROVENANCE_MISMATCH"
    if legacy and governed and max(legacy) >= min(item.version for item in governed):
        return "LEGACY_VERSION_AFTER_MARKER"
    decided = {item.proposal_id: item for item in state.decided_proposals}
    for item in governed:
        if item.origin == VersionOrigin.GOVERNED_APPROVAL:
            if not _approved_record(
                item.version, item.proposal_id, decided, definition.workflow_id, cold
            ):
                return "GOVERNED_VERSION_WITHOUT_PROPOSAL"
        elif not any(
            event.kind == GovernanceEventKind.EMERGENCY_FALLBACK and event.version == item.version
            for event in state.governance_events
        ) and not any(notice.version == item.version for notice in state.notices):
            return "FALLBACK_VERSION_WITHOUT_RECORD"
    return None


def _verify_hot_history(
    definition: WorkflowDefinition, state: WorkflowGovernanceState
) -> str | None:
    workflow_id = definition.workflow_id
    referenced: set[tuple[OutboxCollection, str]] = set()
    for entry in state.outbox:
        key = (entry.collection, entry.logical_id)
        if key in referenced:
            return "OUTBOX_DUPLICATE"
        referenced.add(key)
        try:
            record = outbox_record(definition, state, entry)
        except ColdHistoryIntegrityError:
            return "OUTBOX_REFERENCE_MISSING"
        if dict_hash(record) != entry.content_hash:
            return "OUTBOX_HASH_MISMATCH"
    for item in state.decided_proposals:
        if item.record is not None and (
            record_content_hash(item.record) != item.record_hash
            or item.record.proposal_id != item.proposal_id
            or item.record.workflow_id != workflow_id
        ):
            return "DECIDED_RECORD_MISMATCH"
        if not item.archived and (OutboxCollection.PROPOSALS, item.proposal_id) not in referenced:
            return "UNARCHIVED_RECORD_NOT_IN_OUTBOX"
    sequences = [item.sequence for item in state.governance_events]
    if any(later <= earlier for earlier, later in zip(sequences, sequences[1:], strict=False)):
        return "EVENT_SEQUENCE_INVALID"
    if sequences and sequences[-1] > state.governance_sequence:
        return "EVENT_SEQUENCE_INVALID"
    for event in state.governance_events:
        key = (OutboxCollection.EVENTS, event_logical_id(workflow_id, event.sequence))
        if not event.archived and key not in referenced:
            return "UNARCHIVED_RECORD_NOT_IN_OUTBOX"
    if state.open_proposal is not None and state.open_proposal.workflow_id != workflow_id:
        return "OPEN_PROPOSAL_MISMATCH"
    return None


def _verify_cold(
    definition: WorkflowDefinition,
    state: WorkflowGovernanceState,
    latest: int,
    cold: ColdHistoryStore,
) -> str | None:
    workflow_id = definition.workflow_id
    cold_hashes: dict[OutboxCollection, dict[str, str]] = {}
    for collection in OutboxCollection:
        hashes: dict[str, str] = {}
        for record in cold.list_for_workflow(collection, workflow_id):
            if hashes.setdefault(record.logical_id, record.content_hash) != record.content_hash:
                return "COLD_INTEGRITY_FAILURE"
            if collection == OutboxCollection.VERSIONS:
                number = record.record.get("version")
                if type(number) is not int or number > latest:
                    return "COLD_VERSION_ABOVE_LATEST"
        cold_hashes[collection] = hashes
    cold_versions = cold_hashes[OutboxCollection.VERSIONS]
    in_outbox = {item.logical_id for item in state.outbox}
    hot: set[int] = set()
    for version in definition.versions:
        logical_id = version_logical_id(workflow_id, version.version)
        hot.add(version.version)
        stored = cold_versions.get(logical_id)
        if stored is not None and stored != record_content_hash(version):
            # e.g. a legacy writer reusing a compacted number for different content.
            return "HOT_COLD_VERSION_MISMATCH"
        if stored is None and logical_id not in in_outbox:
            return "VERSION_NOT_ARCHIVED"
    for item in state.version_provenance:
        logical_id = version_logical_id(workflow_id, item.version)
        if item.version not in hot and logical_id not in cold_versions:
            return "VERSION_HISTORY_MISSING"
    return None
