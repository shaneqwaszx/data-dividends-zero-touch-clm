"""Workflow governance history storage (ADR-017 section 5, D-135, B-0 final).

This module owns, for both persistence modes:

* the codec of the reserved top-level governance fields of a definition document;
* the BSON byte budget check made before every governance compare-and-set;
* the three insert-only cold collections (``workflow_versions``, ``workflow_proposals``,
  ``workflow_governance_events``) behind one protocol, with an in-memory and a Mongo
  implementation. ``_id = <logical_id>#<attempt>``; lookups go by ``logical_id`` and accept
  any record whose content hash matches; differing hashes are an integrity failure;
* the archiver that drains the outbox. **Fallback mode** (the default, no confirming
  writes): a duplicate key is ambiguous, so a fresh ``<logical_id>#<attempt+1>`` is
  inserted with its own durable acknowledgement. A confirming ``$inc`` on
  ``archive_confirmations`` exists only behind an explicit flag (default off). An entry
  leaves the outbox only after the durable acknowledgement of its cold copy; a read-back
  is never sufficient;
* compaction, which moves only acknowledged items out of the hot document and never the
  pinned set (active and latest version, open proposal, notices, outbox-referenced records).

Nothing here truncates history: past ``HARD_CEILING_BYTES`` a write is refused with
``WorkflowHistoryUnavailableError`` (``503 WORKFLOW_HISTORY_UNAVAILABLE``).
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from threading import RLock
from typing import Any, Protocol

import bson
from pydantic import BaseModel, ValidationError
from pymongo import ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, PyMongoError
from pymongo.write_concern import WriteConcern

from app.domain.workflow_governance import (
    COMPACTION_START_BYTES,
    FIELD_DECIDED_PROPOSALS,
    FIELD_GOVERNANCE_EVENTS,
    FIELD_GOVERNANCE_SEQUENCE,
    FIELD_MIGRATION_MARKER,
    FIELD_NOTICES,
    FIELD_OPEN_PROPOSAL,
    FIELD_OUTBOX,
    FIELD_REQUIRED_BASELINE,
    FIELD_VERSION_PROVENANCE,
    HARD_CEILING_BYTES,
    MAX_HOT_DECIDED_PROPOSALS,
    MAX_HOT_EVENTS,
    MAX_HOT_VERSIONS,
    ColdRecord,
    DecidedProposalEntry,
    GovernanceErrorCode,
    GovernanceEvent,
    OutboxCollection,
    OutboxEntry,
    ProposalState,
    RequiredBaseline,
    WorkflowGovernanceState,
    WorkflowProposal,
    canonical_json,
    event_logical_id,
    record_content_hash,
    version_logical_id,
)
from app.domain.workflows import WorkflowDefinition, WorkflowVersion
from app.persistence.errors import (
    PersistenceConflictError,
    PersistenceDataInvalidError,
    PersistenceError,
    PersistenceOutcomeAmbiguousError,
    PersistenceUnavailableError,
)

# ADR-017 section 3.1: cold-archive inserts and outbox removal use the durable write rule.
DURABLE_WRITE_CONCERN = WriteConcern(w="majority", j=True, wtimeout=5_000)
# Fresh-suffix inserts per outbox entry per drain before the archiver stops (fail closed).
MAX_ARCHIVE_ATTEMPTS = 16


# --- Errors ---------------------------------------------------------------------------


class WorkflowHistoryUnavailableError(PersistenceError):
    """The service maps this to ``503 WORKFLOW_HISTORY_UNAVAILABLE``. Nothing is truncated."""

    code = GovernanceErrorCode.HISTORY_UNAVAILABLE.value


class ColdHistoryIntegrityError(WorkflowHistoryUnavailableError):
    """Same logical id with different content, or a hot record that does not match its
    outbox reference. Governance mutations fail closed (also ``503``)."""


class WorkflowGovernanceNotMigratedError(PersistenceError):
    """The definition has no P2-1 migration marker (``503 WORKFLOW_GOVERNANCE_NOT_MIGRATED``)."""

    code = GovernanceErrorCode.GOVERNANCE_NOT_MIGRATED.value


class ColdDuplicateKeyError(PersistenceError):
    """An insert met an existing ``_id``. Never counts as inserted by itself (R3-5)."""

    code = "COLD_DUPLICATE_KEY"


# --- The decoded document ---------------------------------------------------------------


@dataclass(frozen=True)
class GovernedDefinition:
    """One definition document: the P2-0 payload (carrying ``write_nonce``,
    ``stored_active_version`` and ``latest_version``) and its decoded governance state."""

    definition: WorkflowDefinition
    governance: WorkflowGovernanceState


# Attribute on ``WorkflowGovernanceState`` -> stored top-level field. The marker is last.
_STATE_FIELDS: tuple[tuple[str, str], ...] = (
    ("required_baseline", FIELD_REQUIRED_BASELINE),
    ("open_proposal", FIELD_OPEN_PROPOSAL),
    ("decided_proposals", FIELD_DECIDED_PROPOSALS),
    ("governance_events", FIELD_GOVERNANCE_EVENTS),
    ("notices", FIELD_NOTICES),
    ("outbox", FIELD_OUTBOX),
    ("version_provenance", FIELD_VERSION_PROVENANCE),
    ("governance_sequence", FIELD_GOVERNANCE_SEQUENCE),
    ("migration_marker", FIELD_MIGRATION_MARKER),
)
STORED_GOVERNANCE_FIELDS = tuple(stored for _, stored in _STATE_FIELDS)


def encode_governance_fields(state: WorkflowGovernanceState) -> dict[str, Any]:
    """The stored top-level fields, marker last. An unmigrated default state stores nothing."""

    if not state.migrated:
        if state != WorkflowGovernanceState():
            raise ValueError("governance state without a migration marker is never stored")
        return {}
    dumped = state.model_dump(mode="json")
    return {stored: dumped[attribute] for attribute, stored in _STATE_FIELDS}


def decode_governance_fields(raw: Mapping[str, Any]) -> WorkflowGovernanceState:
    """Absent fields take their defaults; an absent marker means not migrated."""

    data: dict[str, Any] = {}
    for attribute, stored in _STATE_FIELDS:
        if stored not in raw:
            continue
        value = raw[stored]
        if value is None and attribute == "open_proposal":
            continue
        if value is None:
            # A stored null marker (or other null field) is invalid, never "absent".
            raise PersistenceDataInvalidError
        data[attribute] = value
    try:
        return WorkflowGovernanceState.model_validate(data)
    except ValidationError:
        raise PersistenceDataInvalidError from None


def governed_document(
    definition: WorkflowDefinition,
    governance: WorkflowGovernanceState,
    *,
    write_nonce: str | None,
    active_version: int | None,
    latest_version: int | None,
    dispatch_authorisation_seq: int = 0,
) -> dict[str, Any]:
    """The stored document shape (both modes); used for the byte budget and verification."""

    document: dict[str, Any] = {"_id": definition.workflow_id, "revision": definition.revision}
    if write_nonce is not None:
        document["write_nonce"] = write_nonce
    if active_version is not None:
        document["active_version"] = active_version
    if latest_version is not None:
        document["latest_version"] = latest_version
    document["dispatch_authorisation_seq"] = dispatch_authorisation_seq
    document["payload"] = definition.model_dump(mode="json")
    document.update(encode_governance_fields(governance))
    return document


def encoded_size(document: Mapping[str, Any]) -> int:
    return len(bson.encode(dict(document)))


def check_document_size(document: Mapping[str, Any]) -> int:
    """ADR-017 N-13: computed before every governance compare-and-set; never truncated."""

    size = encoded_size(document)
    if size > HARD_CEILING_BYTES:
        raise WorkflowHistoryUnavailableError
    return size


def _item_size(value: Any) -> int:
    return len(bson.encode({"v": value}))


# --- Record content and outbox references ----------------------------------------------


def dict_hash(record: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(dict(record))).hexdigest()


def version_record(version: WorkflowVersion) -> dict[str, Any]:
    return version.model_dump(mode="json")


def event_record(event: GovernanceEvent) -> dict[str, Any]:
    """An event as archived: its ``archived`` flag is not part of its content."""

    return event.model_copy(update={"archived": False}).model_dump(mode="json")


def event_content_hash(event: GovernanceEvent) -> str:
    return dict_hash(event_record(event))


def outbox_for_version(workflow_id: str, version: WorkflowVersion) -> OutboxEntry:
    return OutboxEntry(
        collection=OutboxCollection.VERSIONS,
        logical_id=version_logical_id(workflow_id, version.version),
        content_hash=record_content_hash(version),
    )


def outbox_for_proposal(proposal: WorkflowProposal) -> OutboxEntry:
    return OutboxEntry(
        collection=OutboxCollection.PROPOSALS,
        logical_id=proposal.proposal_id,
        content_hash=record_content_hash(proposal),
    )


def outbox_for_event(workflow_id: str, event: GovernanceEvent) -> OutboxEntry:
    return OutboxEntry(
        collection=OutboxCollection.EVENTS,
        logical_id=event_logical_id(workflow_id, event.sequence),
        content_hash=event_content_hash(event),
    )


def decided_entry(proposal: WorkflowProposal, *, ended_at: datetime) -> DecidedProposalEntry:
    """The hot entry of a terminal proposal: complete record kept until archived."""

    return DecidedProposalEntry(
        proposal_id=proposal.proposal_id,
        kind=proposal.kind,
        state=proposal.state,
        origin=proposal.origin,
        author_id=proposal.author_id,
        decided_by=proposal.decided_by,
        decided_at=proposal.decided_at,
        ended_at=ended_at,
        published_version=proposal.published_version,
        content_hash=proposal.content_hash,
        record_hash=record_content_hash(proposal),
        archived=False,
        record=proposal,
    )


def outbox_record(
    definition: WorkflowDefinition, state: WorkflowGovernanceState, entry: OutboxEntry
) -> dict[str, Any]:
    """The full hot record an outbox entry references; it must still be present."""

    workflow_id = definition.workflow_id
    if entry.collection == OutboxCollection.VERSIONS:
        for version in definition.versions:
            if version_logical_id(workflow_id, version.version) == entry.logical_id:
                return version_record(version)
    elif entry.collection == OutboxCollection.PROPOSALS:
        for item in state.decided_proposals:
            if item.proposal_id == entry.logical_id and item.record is not None:
                return item.record.model_dump(mode="json")
    else:
        for event in state.governance_events:
            if event_logical_id(workflow_id, event.sequence) == entry.logical_id:
                return event_record(event)
    raise ColdHistoryIntegrityError("OUTBOX_REFERENCE_MISSING")


# --- Cold store ------------------------------------------------------------------------


class ColdHistoryStore(Protocol):
    def initialize(self) -> None:
        """Idempotently create the ``logical_id`` (and ``workflow_id``) indexes."""
        ...

    def insert(self, collection: OutboxCollection, record: ColdRecord) -> None:
        """Insert-only under the durable write rule. Returning means durably acknowledged.

        Raises ``ColdDuplicateKeyError`` on an existing ``_id`` and
        ``PersistenceOutcomeAmbiguousError`` when the outcome is unknown.
        """
        ...

    def confirm(self, collection: OutboxCollection, document_id: str, content_hash: str) -> bool:
        """The confirming ``$inc`` filtered on ``_id`` and content hash (flagged mode only)."""
        ...

    def find(self, collection: OutboxCollection, logical_id: str) -> list[ColdRecord]: ...

    def list_for_workflow(
        self, collection: OutboxCollection, workflow_id: str
    ) -> list[ColdRecord]: ...


def _check_record(record: ColdRecord) -> ColdRecord:
    if dict_hash(record.record) != record.content_hash:
        raise ColdHistoryIntegrityError("COLD_RECORD_HASH_MISMATCH")
    return record


class InMemoryColdHistoryStore:
    """Process-local cold store with the same insert-only and identity rules."""

    def __init__(self) -> None:
        self._records: dict[OutboxCollection, dict[str, ColdRecord]] = {
            collection: {} for collection in OutboxCollection
        }
        self._lock = RLock()

    def initialize(self) -> None:
        return None

    def insert(self, collection: OutboxCollection, record: ColdRecord) -> None:
        with self._lock:
            records = self._records[collection]
            if record.document_id in records:
                raise ColdDuplicateKeyError
            records[record.document_id] = record

    def confirm(self, collection: OutboxCollection, document_id: str, content_hash: str) -> bool:
        with self._lock:
            records = self._records[collection]
            current = records.get(document_id)
            if current is None or current.content_hash != content_hash:
                return False
            records[document_id] = current.model_copy(
                update={"archive_confirmations": current.archive_confirmations + 1}
            )
            return True

    def find(self, collection: OutboxCollection, logical_id: str) -> list[ColdRecord]:
        with self._lock:
            found = [
                item for item in self._records[collection].values() if item.logical_id == logical_id
            ]
        return [_check_record(item) for item in sorted(found, key=lambda item: item.attempt)]

    def list_for_workflow(self, collection: OutboxCollection, workflow_id: str) -> list[ColdRecord]:
        with self._lock:
            found = [
                item
                for item in self._records[collection].values()
                if item.workflow_id == workflow_id
            ]
        return [
            _check_record(item)
            for item in sorted(found, key=lambda item: (item.logical_id, item.attempt))
        ]

    def all_records(self, collection: OutboxCollection) -> list[ColdRecord]:
        """Test and verification helper: every stored record of one collection."""

        with self._lock:
            return sorted(self._records[collection].values(), key=lambda item: item.document_id)


def _encode_cold(record: ColdRecord) -> dict[str, Any]:
    return {
        "_id": record.document_id,
        "logical_id": record.logical_id,
        "attempt": record.attempt,
        "content_hash": record.content_hash,
        "workflow_id": record.workflow_id,
        "archived_at": record.archived_at,
        "archive_confirmations": record.archive_confirmations,
        "record": dict(record.record),
    }


def _decode_cold(raw: Mapping[str, Any]) -> ColdRecord:
    try:
        record = ColdRecord.model_validate(
            {key: raw[key] for key in ColdRecord.model_fields if key in raw}
        )
    except ValidationError:
        raise PersistenceDataInvalidError from None
    if raw.get("_id") != record.document_id:
        raise ColdHistoryIntegrityError("COLD_RECORD_ID_MISMATCH")
    return _check_record(record)


class MongoColdHistoryStore:
    """The three insert-only cold collections. The only mutable field is
    ``archive_confirmations``, changed only by :meth:`confirm` (R1-5)."""

    def __init__(self, database: Database[dict[str, Any]]) -> None:
        self._collections: dict[OutboxCollection, Collection[dict[str, Any]]] = {
            collection: database[collection.value] for collection in OutboxCollection
        }

    def initialize(self) -> None:
        try:
            for collection in self._collections.values():
                collection.create_index([("logical_id", ASCENDING)], name="cold_logical_id")
                collection.create_index([("workflow_id", ASCENDING)], name="cold_workflow_id")
        except PyMongoError:
            raise PersistenceUnavailableError from None

    def insert(self, collection: OutboxCollection, record: ColdRecord) -> None:
        durable = self._collections[collection].with_options(write_concern=DURABLE_WRITE_CONCERN)
        try:
            result = durable.insert_one(_encode_cold(record))
        except DuplicateKeyError:
            raise ColdDuplicateKeyError from None
        except PyMongoError:
            # Timeout, wtimeout, network error or unknown commit state: never "done".
            raise PersistenceOutcomeAmbiguousError from None
        if not result.acknowledged:
            raise PersistenceOutcomeAmbiguousError

    def confirm(self, collection: OutboxCollection, document_id: str, content_hash: str) -> bool:
        durable = self._collections[collection].with_options(write_concern=DURABLE_WRITE_CONCERN)
        try:
            result = durable.update_one(
                {"_id": document_id, "content_hash": content_hash},
                {"$inc": {"archive_confirmations": 1}},
            )
        except PyMongoError:
            raise PersistenceOutcomeAmbiguousError from None
        return bool(result.acknowledged and result.modified_count == 1)

    def _find(self, collection: OutboxCollection, query: dict[str, Any]) -> list[ColdRecord]:
        try:
            raws = list(self._collections[collection].find(query))
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return [_decode_cold(raw) for raw in raws]

    def find(self, collection: OutboxCollection, logical_id: str) -> list[ColdRecord]:
        found = self._find(collection, {"logical_id": logical_id})
        return sorted(found, key=lambda item: item.attempt)

    def list_for_workflow(self, collection: OutboxCollection, workflow_id: str) -> list[ColdRecord]:
        found = self._find(collection, {"workflow_id": workflow_id})
        return sorted(found, key=lambda item: (item.logical_id, item.attempt))


def lookup_cold(
    cold: ColdHistoryStore,
    collection: OutboxCollection,
    logical_id: str,
    *,
    expected_hash: str | None = None,
) -> ColdRecord | None:
    """By ``logical_id``; any record whose hash matches. Differing hashes fail closed."""

    records = cold.find(collection, logical_id)
    hashes = {item.content_hash for item in records}
    if len(hashes) > 1:
        raise ColdHistoryIntegrityError("COLD_LOGICAL_ID_CONFLICT")
    if expected_hash is not None and hashes and expected_hash not in hashes:
        raise ColdHistoryIntegrityError("COLD_HOT_CONTENT_MISMATCH")
    return records[0] if records else None


def cold_version(cold: ColdHistoryStore, workflow_id: str, version: int) -> WorkflowVersion | None:
    found = lookup_cold(cold, OutboxCollection.VERSIONS, version_logical_id(workflow_id, version))
    if found is None:
        return None
    try:
        decoded = WorkflowVersion.model_validate(found.record)
    except ValidationError:
        raise ColdHistoryIntegrityError("COLD_VERSION_INVALID") from None
    if decoded.version != version:
        raise ColdHistoryIntegrityError("COLD_VERSION_NUMBER_MISMATCH")
    return decoded


# --- Archiver ---------------------------------------------------------------------------


def archive_record(
    cold: ColdHistoryStore,
    *,
    collection: OutboxCollection,
    logical_id: str,
    content_hash: str,
    workflow_id: str,
    record: Mapping[str, Any],
    now: datetime,
    first_attempt: int = 0,
    confirming_writes: bool = False,
) -> int:
    """Store one cold copy with a durable acknowledgement; return the attempt acknowledged.

    Fallback mode inserts at the first free attempt suffix (a duplicate is ambiguous and
    never counts). Confirming mode may instead confirm an existing identical record with
    the durable ``$inc``. A differing hash for the same logical id is an integrity failure.
    Any ambiguous outcome propagates, so the entry stays in the outbox.
    """

    if dict_hash(record) != content_hash:
        raise ColdHistoryIntegrityError("HOT_RECORD_HASH_MISMATCH")
    for _ in range(MAX_ARCHIVE_ATTEMPTS):
        existing = cold.find(collection, logical_id)
        if any(item.content_hash != content_hash for item in existing):
            raise ColdHistoryIntegrityError("COLD_LOGICAL_ID_CONFLICT")
        if confirming_writes and existing:
            target = existing[0]
            if cold.confirm(collection, target.document_id, content_hash):
                return target.attempt
            raise PersistenceOutcomeAmbiguousError
        attempt = max([first_attempt, *(item.attempt + 1 for item in existing)])
        candidate = ColdRecord(
            logical_id=logical_id,
            attempt=attempt,
            content_hash=content_hash,
            workflow_id=workflow_id,
            archived_at=now,
            record=dict(record),
        )
        try:
            cold.insert(collection, candidate)
        except ColdDuplicateKeyError:
            continue  # re-read, then a fresh suffix
        return attempt
    raise WorkflowHistoryUnavailableError


@dataclass(frozen=True)
class DrainResult:
    definition: WorkflowDefinition
    governance: WorkflowGovernanceState
    archived: tuple[OutboxEntry, ...]
    error: PersistenceError | None


def mark_archived(
    workflow_id: str, state: WorkflowGovernanceState, acknowledged: Sequence[OutboxEntry]
) -> WorkflowGovernanceState:
    """Remove acknowledged entries from the outbox and flag their hot items archived."""

    if not acknowledged:
        return state
    done = {(item.collection, item.logical_id) for item in acknowledged}
    proposals = {lid for collection, lid in done if collection == OutboxCollection.PROPOSALS}
    events = {lid for collection, lid in done if collection == OutboxCollection.EVENTS}
    return state.model_copy(
        update={
            "outbox": tuple(
                item for item in state.outbox if (item.collection, item.logical_id) not in done
            ),
            "decided_proposals": tuple(
                item.model_copy(update={"archived": True})
                if item.proposal_id in proposals
                else item
                for item in state.decided_proposals
            ),
            "governance_events": tuple(
                item.model_copy(update={"archived": True})
                if event_logical_id(workflow_id, item.sequence) in events
                else item
                for item in state.governance_events
            ),
        }
    )


def drain_outbox_entries(
    definition: WorkflowDefinition,
    state: WorkflowGovernanceState,
    cold: ColdHistoryStore,
    *,
    now: datetime,
    confirming_writes: bool = False,
) -> DrainResult:
    """Archive outbox entries in order until one fails; the caller commits the acknowledged
    prefix in one compare-and-set, then raises ``error`` if set."""

    acknowledged: list[OutboxEntry] = []
    error: PersistenceError | None = None
    for entry in state.outbox:
        try:
            record = outbox_record(definition, state, entry)
            archive_record(
                cold,
                collection=entry.collection,
                logical_id=entry.logical_id,
                content_hash=entry.content_hash,
                workflow_id=definition.workflow_id,
                record=record,
                now=now,
                first_attempt=entry.attempt,
                confirming_writes=confirming_writes,
            )
        except PersistenceError as exc:
            error = exc
            break
        acknowledged.append(entry)
    return DrainResult(
        definition=definition,
        governance=mark_archived(definition.workflow_id, state, acknowledged),
        archived=tuple(acknowledged),
        error=error,
    )


# --- Compaction -------------------------------------------------------------------------


def _model_size(model: BaseModel) -> int:
    return _item_size(model.model_dump(mode="json"))


def _pinned_versions(
    state: WorkflowGovernanceState, *, active_version: int, latest_version: int, workflow_id: str
) -> set[int]:
    pinned = {active_version, latest_version}
    if state.open_proposal is not None:
        pinned.add(state.open_proposal.base_version)
    for entry in state.outbox:
        if entry.collection == OutboxCollection.VERSIONS:
            prefix = f"{workflow_id}:"
            if entry.logical_id.startswith(prefix):
                tail = entry.logical_id[len(prefix) :]
                if tail.isdigit():
                    pinned.add(int(tail))
    return pinned


def non_pinned_bytes(
    definition: WorkflowDefinition,
    state: WorkflowGovernanceState,
    *,
    active_version: int,
    latest_version: int,
) -> int:
    """Encoded size of everything compaction could ever move (ADR-017 N-13)."""

    workflow_id = definition.workflow_id
    pinned = _pinned_versions(
        state,
        active_version=active_version,
        latest_version=latest_version,
        workflow_id=workflow_id,
    )
    referenced = {(item.collection, item.logical_id) for item in state.outbox}
    total = sum(_model_size(item) for item in definition.versions if item.version not in pinned)
    total += sum(
        _model_size(item)
        for item in state.decided_proposals
        if (OutboxCollection.PROPOSALS, item.proposal_id) not in referenced
    )
    total += sum(
        _model_size(item)
        for item in state.governance_events
        if (OutboxCollection.EVENTS, event_logical_id(workflow_id, item.sequence)) not in referenced
    )
    total += sum(_model_size(item) for item in state.notices if item.acknowledged_at is not None)
    return total


def compaction_needed(
    definition: WorkflowDefinition,
    state: WorkflowGovernanceState,
    *,
    active_version: int,
    latest_version: int,
) -> bool:
    return (
        len(definition.versions) > MAX_HOT_VERSIONS
        or len(state.decided_proposals) > MAX_HOT_DECIDED_PROPOSALS
        or len(state.governance_events) > MAX_HOT_EVENTS
        or non_pinned_bytes(
            definition, state, active_version=active_version, latest_version=latest_version
        )
        > COMPACTION_START_BYTES
    )


def compact_history(
    definition: WorkflowDefinition,
    state: WorkflowGovernanceState,
    cold: ColdHistoryStore,
    *,
    active_version: int,
    latest_version: int,
) -> tuple[WorkflowDefinition, WorkflowGovernanceState]:
    """Move acknowledged, unpinned items to cold-only when the RD-5 maxima or the 4 MiB
    non-pinned budget are exceeded. Each removal re-checks that a matching cold copy
    exists; anything not provably archived stays hot. Notices are never compacted (M1)."""

    if not compaction_needed(
        definition, state, active_version=active_version, latest_version=latest_version
    ):
        return definition, state
    workflow_id = definition.workflow_id
    pinned = _pinned_versions(
        state,
        active_version=active_version,
        latest_version=latest_version,
        workflow_id=workflow_id,
    )
    referenced = {(item.collection, item.logical_id) for item in state.outbox}

    def in_cold(collection: OutboxCollection, logical_id: str, content_hash: str) -> bool:
        return lookup_cold(cold, collection, logical_id, expected_hash=content_hash) is not None

    versions = list(definition.versions)
    removable_versions = [
        item
        for item in versions
        if item.version not in pinned
        and (OutboxCollection.VERSIONS, version_logical_id(workflow_id, item.version))
        not in referenced
    ]
    decided = list(state.decided_proposals)
    events = list(state.governance_events)

    def decided_removable(item: DecidedProposalEntry) -> bool:
        return item.archived and (OutboxCollection.PROPOSALS, item.proposal_id) not in referenced

    def event_removable(item: GovernanceEvent) -> bool:
        return (
            item.archived
            and (OutboxCollection.EVENTS, event_logical_id(workflow_id, item.sequence))
            not in referenced
        )

    # 1. Archived decided proposals drop to summaries (their record is in cold).
    for index, item in enumerate(decided):
        if (
            decided_removable(item)
            and item.record is not None
            and in_cold(OutboxCollection.PROPOSALS, item.proposal_id, item.record_hash)
        ):
            decided[index] = item.model_copy(update={"record": None})

    def remove_version(item: WorkflowVersion) -> bool:
        if item not in versions:
            return False
        if not in_cold(
            OutboxCollection.VERSIONS,
            version_logical_id(workflow_id, item.version),
            record_content_hash(item),
        ):
            return False
        versions.remove(item)
        return True

    def remove_decided(item: DecidedProposalEntry) -> bool:
        if not in_cold(OutboxCollection.PROPOSALS, item.proposal_id, item.record_hash):
            return False
        decided.remove(item)
        return True

    def remove_event(item: GovernanceEvent) -> bool:
        if not in_cold(
            OutboxCollection.EVENTS,
            event_logical_id(workflow_id, item.sequence),
            event_content_hash(item),
        ):
            return False
        events.remove(item)
        return True

    # 2. The RD-5 maxima, oldest first.
    for version_item in sorted(removable_versions, key=lambda item: item.version):
        if len(versions) <= MAX_HOT_VERSIONS:
            break
        remove_version(version_item)
    for decided_item in [item for item in decided if decided_removable(item)]:
        if len(decided) <= MAX_HOT_DECIDED_PROPOSALS:
            break
        remove_decided(decided_item)
    for event_item in sorted(
        (item for item in events if event_removable(item)), key=lambda item: item.sequence
    ):
        if len(events) <= MAX_HOT_EVENTS:
            break
        remove_event(event_item)

    def current() -> tuple[WorkflowDefinition, WorkflowGovernanceState]:
        return (
            definition.model_copy(update={"versions": tuple(versions)}),
            state.model_copy(
                update={"decided_proposals": tuple(decided), "governance_events": tuple(events)}
            ),
        )

    def over_budget() -> bool:
        compact_definition, compact_state = current()
        return (
            non_pinned_bytes(
                compact_definition,
                compact_state,
                active_version=active_version,
                latest_version=latest_version,
            )
            > COMPACTION_START_BYTES
        )

    # 3. The non-pinned byte budget, oldest first: versions, then proposals, then events.
    for version_item in sorted(removable_versions, key=lambda item: item.version):
        if not over_budget():
            break
        remove_version(version_item)
    for decided_item in [item for item in decided if decided_removable(item)]:
        if not over_budget():
            break
        remove_decided(decided_item)
    for event_item in sorted(
        (item for item in events if event_removable(item)), key=lambda item: item.sequence
    ):
        if not over_budget():
            break
        remove_event(event_item)
    return current()


# --- The governance write, shared by both modes -----------------------------------------


def highest_version(definition: WorkflowDefinition) -> int:
    return max((item.version for item in definition.versions), default=0)


class GovernanceHistoryRewriteError(WorkflowHistoryUnavailableError):
    """A governance write would remove or rewrite stored history outside the archiver's
    and compaction's own verified paths (owner condition). Fails closed, nothing written."""


def check_history_preserved(
    stored: GovernedDefinition,
    definition: WorkflowDefinition,
    governance: WorkflowGovernanceState,
    *,
    publication: bool = False,
) -> None:
    """History is append-only for a caller: every stored outbox entry, decided entry,
    event, hot version, provenance entry and notice must still be present unchanged, and
    everything new must be unarchived and referenced by the outbox. Only ``mark_archived``
    (after durable acknowledgement) and ``compact_history`` (after a verified cold copy)
    remove or flag history, and they run inside the repository, never through a caller."""

    before, workflow_id = stored.governance, definition.workflow_id

    def refuse(reason: str) -> None:
        raise GovernanceHistoryRewriteError(reason)

    if definition.workflow_id != stored.definition.workflow_id:
        refuse("WORKFLOW_ID_CHANGED")
    if governance.migration_marker != before.migration_marker:
        refuse("MARKER_CHANGED")
    if governance.governance_sequence < before.governance_sequence:
        refuse("SEQUENCE_DECREASED")
    outbox = set(governance.outbox)
    if any(item not in outbox for item in before.outbox):
        refuse("OUTBOX_ENTRY_REMOVED")
    referenced = {(item.collection, item.logical_id) for item in governance.outbox}
    decided = {item.proposal_id: item for item in governance.decided_proposals}
    old_decided = {item.proposal_id for item in before.decided_proposals}
    if any(decided.get(item.proposal_id) != item for item in before.decided_proposals):
        refuse("DECIDED_ENTRY_REMOVED_OR_CHANGED")
    for item in governance.decided_proposals:
        if item.proposal_id not in old_decided and (
            item.archived
            or item.record is None
            or (OutboxCollection.PROPOSALS, item.proposal_id) not in referenced
        ):
            refuse("NEW_DECIDED_ENTRY_NOT_IN_OUTBOX")
    events = {item.sequence: item for item in governance.governance_events}
    old_events = {item.sequence for item in before.governance_events}
    if any(events.get(item.sequence) != item for item in before.governance_events):
        refuse("EVENT_REMOVED_OR_CHANGED")
    for event in governance.governance_events:
        key = (OutboxCollection.EVENTS, event_logical_id(workflow_id, event.sequence))
        if event.sequence not in old_events and (event.archived or key not in referenced):
            refuse("NEW_EVENT_NOT_IN_OUTBOX")
    versions = {item.version: item for item in definition.versions}
    old_versions = {item.version for item in stored.definition.versions}
    if any(versions.get(item.version) != item for item in stored.definition.versions):
        # Covers the pinned active and latest versions and any version not yet in cold.
        refuse("VERSION_REMOVED_OR_CHANGED")
    for version in definition.versions:
        key = (OutboxCollection.VERSIONS, version_logical_id(workflow_id, version.version))
        if version.version not in old_versions and key not in referenced:
            refuse("NEW_VERSION_NOT_IN_OUTBOX")
    count = len(before.version_provenance)
    if governance.version_provenance[:count] != before.version_provenance:
        refuse("PROVENANCE_REWRITTEN")
    notices = {item.notice_id: item for item in governance.notices}
    for notice in before.notices:
        incoming = notices.get(notice.notice_id)
        if incoming is None:
            refuse("NOTICE_REMOVED")
            return
        # Only the acknowledgement may be added (None -> value); nothing else changes.
        keep = {"acknowledged_by", "acknowledged_at"}
        if incoming.model_dump(exclude=keep) != notice.model_dump(exclude=keep):
            refuse("NOTICE_CHANGED")
        for name in keep:
            if getattr(notice, name) is not None and getattr(incoming, name) != getattr(
                notice, name
            ):
                refuse("NOTICE_ACKNOWLEDGEMENT_CHANGED")
    _check_open_proposal(before, governance, old_decided, refuse)
    _check_baseline(before.required_baseline, governance.required_baseline, publication, refuse)


def _check_open_proposal(
    before: WorkflowGovernanceState,
    governance: WorkflowGovernanceState,
    old_decided: set[str],
    refuse: Callable[[str], None],
) -> None:
    """A stored open proposal is never lost: it stays (same id, revision not lower,
    frozen content unchanged while pending) or ends as a new, unarchived decided entry
    with its full record, referenced by the outbox (checked with the other new entries)."""

    stored = before.open_proposal
    if stored is None:
        return
    incoming = governance.open_proposal
    if incoming is not None and incoming.proposal_id == stored.proposal_id:
        if incoming.revision < stored.revision:
            refuse("OPEN_PROPOSAL_REVISION_DECREASED")
        if stored.state == ProposalState.PENDING_APPROVAL and (
            incoming.state != stored.state
            or incoming.content_hash != stored.content_hash
            or incoming.stages != stored.stages
            or incoming.kind != stored.kind
            or incoming.base_version != stored.base_version
        ):
            refuse("PENDING_PROPOSAL_CONTENT_CHANGED")
        return
    entry = next(
        (item for item in governance.decided_proposals if item.proposal_id == stored.proposal_id),
        None,
    )
    if (
        entry is None
        or stored.proposal_id in old_decided
        or entry.archived
        or entry.record is None
        or entry.record.proposal_id != stored.proposal_id
        or entry.record.revision < stored.revision
    ):
        refuse("OPEN_PROPOSAL_DROPPED")


def _check_baseline(
    before: RequiredBaseline,
    incoming: RequiredBaseline,
    publication: bool,
    refuse: Callable[[str], None],
) -> None:
    """Defence in depth for the ratchet's baseline (ADR-017 2): it changes only on a
    publication, and then only becomes stricter; no stored obligation disappears."""

    if incoming == before:
        return
    if not publication:
        refuse("BASELINE_CHANGED_WITHOUT_PUBLICATION")
        return
    stages = {item.stage_id: item for item in incoming.stages}
    for stage in before.stages:
        new_stage = stages.get(stage.stage_id)
        if new_stage is None or new_stage.normalised_name != stage.normalised_name:
            refuse("BASELINE_STAGE_REMOVED_OR_RENAMED")
            return
        fields = {item.field_id: item.signature for item in new_stage.fields}
        for field in stage.fields:
            old, new = field.signature, fields.get(field.field_id)
            if new is None:
                refuse("BASELINE_FIELD_REMOVED")
                return
            if new.kind != old.kind or new.normalised_label != old.normalised_label:
                refuse("BASELINE_SIGNATURE_CHANGED")
            if old.choice_options is not None and (
                new.choice_options is None or not set(new.choice_options) <= set(old.choice_options)
            ):
                refuse("BASELINE_CHOICE_WIDENED")
            if new.has_case_data_key and not old.has_case_data_key:
                refuse("BASELINE_CASE_DATA_KEY_GAINED")
            if new.applicability != old.applicability:
                refuse("BASELINE_APPLICABILITY_CHANGED")


def check_outbox_integrity(
    definition: WorkflowDefinition, governance: WorkflowGovernanceState, cold: ColdHistoryStore
) -> None:
    """Every outbox entry resolves to its full hot record, and no cold record with the same
    logical id carries a different hash. Runs inside every governance write, so a skipped
    drain cannot hide an integrity failure (fails closed with ``503``)."""

    for entry in governance.outbox:
        if dict_hash(outbox_record(definition, governance, entry)) != entry.content_hash:
            raise ColdHistoryIntegrityError("OUTBOX_HASH_MISMATCH")
        lookup_cold(cold, entry.collection, entry.logical_id, expected_hash=entry.content_hash)


def prepare_governance_write(
    stored: GovernedDefinition,
    definition: WorkflowDefinition,
    governance: WorkflowGovernanceState,
    cold: ColdHistoryStore,
    *,
    active_version: int | None,
    latest_version: int | None,
) -> tuple[WorkflowDefinition, WorkflowGovernanceState, int, int]:
    """Validate against the **stored** document, guard history, compact, and return what
    the CAS writes (the caller-supplied version fields are never trusted).

    Without a publication, no payload version may pass the stored high-water mark and the
    stored ``active_version``/``latest_version`` are kept. A publication raises
    ``latest_version`` by exactly one (never equal, lower or skipping), the newest hot
    version is the latest, and ``active_version`` is 0 or the latest (ADR-017 3.5).
    """

    if not governance.migrated:
        raise WorkflowGovernanceNotMigratedError
    if not stored.governance.migrated:
        raise PersistenceConflictError
    current_active = stored.definition.stored_active_version
    current_latest = stored.definition.latest_version
    if current_latest is None or current_active is None:
        raise PersistenceDataInvalidError
    highest = highest_version(definition)
    if (active_version is None) != (latest_version is None):
        raise ValueError("a publication sets both active_version and latest_version")
    if latest_version is None or active_version is None:
        if highest > current_latest:
            raise PersistenceConflictError
        active, latest = current_active, current_latest
    else:
        if latest_version != current_latest + 1:
            raise ValueError("a publication raises latest_version by exactly one")
        if active_version not in {0, latest_version}:
            raise ValueError("active_version is 0 or latest_version")
        if highest != latest_version:
            raise ValueError("the newest hot version is the latest version")
        active, latest = active_version, latest_version
    check_history_preserved(stored, definition, governance, publication=latest_version is not None)
    check_outbox_integrity(definition, governance, cold)
    compact_definition, compact_state = compact_history(
        definition, governance, cold, active_version=active, latest_version=latest
    )
    return compact_definition, compact_state, active, latest
