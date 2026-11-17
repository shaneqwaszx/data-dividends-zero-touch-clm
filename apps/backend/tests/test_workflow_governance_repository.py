"""ADR-017 P2-1 governance repository: memory and Mongo at strict parity.

The Mongo repository runs over the dict-backed pymongo double from
``test_workflow_governance_cold_store`` (no server, no mongomock).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from test_workflow_governance_cold_store import FakeClient

from app.domain.workflow_governance import (
    COLD_VERSIONS,
    GOVERNANCE_TOP_LEVEL_FIELDS,
    BaselineField,
    BaselineStage,
    ColdRecord,
    FieldSignature,
    GovernanceEvent,
    GovernanceEventKind,
    GovernanceNotice,
    MigrationMarker,
    ProposalKind,
    ProposalState,
    RequiredBaseline,
    VersionOrigin,
    VersionProvenance,
    WorkflowGovernanceState,
    WorkflowProposal,
    proposal_content_hash,
)
from app.domain.workflows import (
    ONBOARDING_WORKFLOW_ID,
    WorkflowDefinition,
    WorkflowField,
    WorkflowFieldKind,
    WorkflowStage,
    WorkflowVersion,
)
from app.persistence.errors import PersistenceConflictError
from app.persistence.mongo_workflow_store import (
    MongoWorkflowDefinitionRepository,
    MongoWorkflowStore,
)
from app.persistence.workflow_governance_store import (
    ColdHistoryIntegrityError,
    GovernanceHistoryRewriteError,
    GovernedDefinition,
    InMemoryColdHistoryStore,
    WorkflowGovernanceNotMigratedError,
    WorkflowHistoryUnavailableError,
    decided_entry,
    outbox_for_event,
    outbox_for_proposal,
    outbox_for_version,
    prepare_governance_write,
)
from app.services.workflow_repository import InMemoryWorkflowDefinitionRepository

NOW = datetime(2031, 3, 1, 9, 0, tzinfo=UTC)
WID = "refresh"


class Harness:
    def __init__(self, kind: str) -> None:
        self.kind = kind
        self.client = FakeClient()
        if kind == "memory":
            self.repository: Any = InMemoryWorkflowDefinitionRepository()
        else:
            store = MongoWorkflowStore(
                self.client,  # type: ignore[arg-type]
                database="clm_p12_000000000000000000000000",
                definitions_collection="clm_workflow_definitions",
                runs_collection="clm_workflow_runs",
            )
            store.initialize()
            self.repository = MongoWorkflowDefinitionRepository(store)

    @property
    def definitions(self) -> Any:
        return self.client["clm_p12_000000000000000000000000"]["clm_workflow_definitions"]

    @property
    def cold_versions(self) -> Any:
        return self.client["clm_p12_000000000000000000000000"][COLD_VERSIONS]


@pytest.fixture(params=["memory", "mongo"])
def harness(request: pytest.FixtureRequest) -> Harness:
    return Harness(request.param)


def payload(*versions: WorkflowVersion, revision: int = 1) -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id=WID,
        name="Refresh",
        use_case="Case refresh",
        country="Singapore",
        revision=revision,
        versions=versions,
        created_at=NOW,
        updated_at=NOW,
    )


def born() -> WorkflowGovernanceState:
    created = GovernanceEvent(
        sequence=1,
        occurred_at=NOW,
        actor_id="hr-author",
        kind=GovernanceEventKind.WORKFLOW_CREATED,
        summary="Workflow created",
    )
    return WorkflowGovernanceState(
        migration_marker=MigrationMarker(
            migrated_at=NOW, tool_version="born", legacy_versions=0, legacy_draft_converted=False
        ),
        governance_events=(created,),
        outbox=(outbox_for_event(WID, created),),
        governance_sequence=1,
    )


def stages(label: str) -> tuple[WorkflowStage, ...]:
    field = WorkflowField(field_id="reason", label=label, kind=WorkflowFieldKind.TEXT)
    return (WorkflowStage(stage_id="review", name="Review", fields=(field,)),)


def pending_proposal(current: GovernedDefinition, number: int) -> WorkflowProposal:
    at = NOW + timedelta(hours=number)
    content = stages(f"Reason {number}")
    return WorkflowProposal(
        proposal_id=str(uuid4()),
        workflow_id=WID,
        state=ProposalState.PENDING_APPROVAL,
        base_version=current.definition.stored_active_version or 0,
        stages=content,
        author_id="hr-author",
        created_at=at,
        updated_at=at,
        last_activity_at=at,
        submitted_at=at,
        content_hash=proposal_content_hash(ProposalKind.CHANGE, content),
    )


def submit(harness: Harness, current: GovernedDefinition, number: int) -> GovernedDefinition:
    """Put a PENDING_APPROVAL proposal in the open slot (what WS-B's submit stores)."""

    return harness.repository.write_governance(
        current.definition.model_copy(update={"revision": current.definition.revision + 1}),
        current.governance.model_copy(update={"open_proposal": pending_proposal(current, number)}),
        expected_revision=current.definition.revision,
    )


def approve(current: GovernedDefinition, number: int) -> tuple[WorkflowDefinition, Any]:
    """What WS-B's decision writes: one CAS that ends the stored open proposal with the
    version, provenance, record, events and outbox. Without a stored open proposal the
    result is only useful for tests that expect a refusal."""

    at = NOW + timedelta(hours=number)
    opened = current.governance.open_proposal or pending_proposal(current, number)
    proposal = opened.model_copy(
        update={
            "state": ProposalState.APPROVED,
            "revision": opened.revision + 1,
            "decided_at": at,
            "decided_by": "director-one",
            "decision_reason": "Approved for the test.",
            "published_version": number,
        }
    )
    content = proposal.stages
    published = WorkflowVersion(
        version=number, stages=content, activated_at=at, activated_by="director-one"
    )
    state = current.governance
    sequence = state.governance_sequence
    approved = GovernanceEvent(
        sequence=sequence + 1,
        occurred_at=at,
        actor_id="director-one",
        kind=GovernanceEventKind.PROPOSAL_APPROVED,
        proposal_id=proposal.proposal_id,
        version=number,
        summary="Proposal approved",
    )
    publication = approved.model_copy(
        update={
            "sequence": sequence + 2,
            "kind": GovernanceEventKind.VERSION_PUBLISHED,
            "summary": "Version published",
        }
    )
    governance = state.model_copy(
        update={
            "open_proposal": None,
            "decided_proposals": (*state.decided_proposals, decided_entry(proposal, ended_at=at)),
            "governance_events": (*state.governance_events, approved, publication),
            "outbox": (
                *state.outbox,
                outbox_for_version(WID, published),
                outbox_for_proposal(proposal),
                outbox_for_event(WID, approved),
                outbox_for_event(WID, publication),
            ),
            "version_provenance": (
                *state.version_provenance,
                VersionProvenance(
                    version=number,
                    origin=VersionOrigin.GOVERNED_APPROVAL,
                    author_id="hr-author",
                    approved_by="director-one",
                    proposal_id=proposal.proposal_id,
                    published_at=at,
                ),
            ),
            "governance_sequence": sequence + 2,
        }
    )
    definition = current.definition.model_copy(
        update={
            "versions": (*current.definition.versions, published),
            "revision": current.definition.revision + 1,
        }
    )
    return definition, governance


def publish(harness: Harness, current: GovernedDefinition, number: int) -> GovernedDefinition:
    if current.governance.open_proposal is None:
        current = submit(harness, current, number)
    definition, governance = approve(current, number)
    return harness.repository.write_governance(
        definition,
        governance,
        expected_revision=current.definition.revision,
        active_version=number,
        latest_version=number,
    )


# --- create / read --------------------------------------------------------------------


def test_create_governed_is_insert_only_and_born_with_its_marker(harness: Harness) -> None:
    created = harness.repository.create_governed(payload(), born())
    assert created.governance.migrated and created.definition.write_nonce
    assert created.definition.stored_active_version == 0 == created.definition.latest_version
    read = harness.repository.get_governed(WID)
    assert (
        read.governance == born() and read.definition.write_nonce == created.definition.write_nonce
    )
    with pytest.raises(PersistenceConflictError):
        harness.repository.create_governed(payload(), born())
    with pytest.raises(WorkflowGovernanceNotMigratedError):
        harness.repository.create_governed(
            payload().model_copy(update={"workflow_id": "other"}), WorkflowGovernanceState()
        )


def test_p2_0_definition_reads_as_not_migrated(harness: Harness) -> None:
    harness.repository.create(payload())
    read = harness.repository.get_governed(WID)
    assert read.governance == WorkflowGovernanceState() and not read.governance.migrated
    assert [item.definition.workflow_id for item in harness.repository.list_governed()] == [WID]
    if harness.kind == "mongo":
        stored = harness.definitions.documents[WID]
        assert not set(GOVERNANCE_TOP_LEVEL_FIELDS) & set(stored)


# --- the governance compare-and-set ---------------------------------------------------


def test_governance_write_is_a_cas_on_revision_and_nonce(harness: Harness) -> None:
    created = harness.repository.create_governed(payload(), born())
    first = publish(harness, created, 1)
    assert first.definition.write_nonce not in {None, created.definition.write_nonce}
    assert first.definition.stored_active_version == 1 == first.definition.latest_version
    assert first.definition.revision == 3  # submit, then decide
    # A writer holding the old snapshot never overwrites the publication.
    stale, governance = approve(created, 1)
    with pytest.raises(PersistenceConflictError):
        harness.repository.write_governance(
            stale, governance, expected_revision=1, active_version=1, latest_version=1
        )
    # Same revision, different nonce (another history): refused.
    other = first.definition.model_copy(update={"write_nonce": "0" * 32})
    with pytest.raises(PersistenceConflictError):
        harness.repository.write_governance(
            other, first.governance, expected_revision=first.definition.revision
        )
    assert harness.repository.get_governed(WID) == first


def test_mongo_governance_write_is_durable_and_filters_the_marker() -> None:
    harness = Harness("mongo")
    created = harness.repository.create_governed(payload(), born())
    insert = harness.definitions.log[-1]
    assert insert[:2] == ("insert_one", True)
    submitted = submit(harness, created, 1)
    publish(harness, submitted, 1)
    operation, durable, (query, update) = harness.definitions.log[-1]
    assert (operation, durable) == ("update_one", True)
    assert query["revision"] == 2 and query["write_nonce"] == submitted.definition.write_nonce
    assert query["p2_1_migration_marker"] == {"$exists": True}
    written = update["$set"]
    assert list(written)[-1] == "p2_1_migration_marker"
    assert written["active_version"] == written["latest_version"] == 1
    assert "dispatch_authorisation_seq" not in written
    assert "write_nonce" not in written["payload"]


def test_publication_fields_are_validated(harness: Harness) -> None:
    created = harness.repository.create_governed(payload(), born())
    first = publish(harness, created, 1)
    definition, governance = approve(first, 2)
    with pytest.raises(PersistenceConflictError):  # no publication: cannot pass latest
        harness.repository.write_governance(
            definition, governance, expected_revision=first.definition.revision
        )
    with pytest.raises(ValueError):
        harness.repository.write_governance(
            definition,
            governance,
            expected_revision=first.definition.revision,
            active_version=2,
            latest_version=0,
        )
    with pytest.raises(ValueError):
        harness.repository.write_governance(
            definition,
            governance,
            expected_revision=first.definition.revision,
            active_version=1,
            latest_version=2,
        )
    assert harness.repository.get_governed(WID) == first


def test_update_only_never_resurrects_a_missing_definition(harness: Harness) -> None:
    created = harness.repository.create_governed(payload(), born())
    definition, governance = approve(created, 1)
    ghost = definition.model_copy(update={"workflow_id": "ghost"})
    with pytest.raises(PersistenceConflictError):
        harness.repository.write_governance(
            ghost, governance, expected_revision=1, active_version=1, latest_version=1
        )
    assert harness.repository.get_governed("ghost") is None


def test_governance_write_to_an_unmigrated_document_is_refused(harness: Harness) -> None:
    created = harness.repository.create(payload())
    governed = GovernedDefinition(created, born())
    definition, governance = approve(governed, 1)
    with pytest.raises(PersistenceConflictError):
        harness.repository.write_governance(
            definition, governance, expected_revision=1, active_version=1, latest_version=1
        )
    with pytest.raises(WorkflowGovernanceNotMigratedError):
        harness.repository.write_governance(
            created.model_copy(update={"revision": 2}),
            WorkflowGovernanceState(),
            expected_revision=1,
        )


def test_p2_0_update_refuses_a_migrated_document_and_changes_nothing(harness: Harness) -> None:
    created = harness.repository.create_governed(payload(), born())
    first = publish(harness, created, 1)
    before = harness.definitions.documents[WID] if harness.kind == "mongo" else None
    # The P2-0 draft-save path: after migration every write goes through write_governance.
    draft = first.definition.model_copy(update={"revision": 3, "draft_stages": stages("Draft")})
    with pytest.raises(PersistenceConflictError):
        harness.repository.update(draft, expected_revision=2)
    assert harness.repository.get_governed(WID) == first
    if harness.kind == "mongo":
        assert harness.definitions.documents[WID] == before
        query = harness.definitions.log[-1][2][0]
        assert query["p2_1_migration_marker"] == {"$exists": False}


def test_p2_0_update_of_an_unmigrated_document_still_works(harness: Harness) -> None:
    created = harness.repository.create(payload())
    draft = created.model_copy(update={"revision": 2, "draft_stages": stages("Draft")})
    written = harness.repository.update(draft, expected_revision=1)
    assert written.draft_stages == stages("Draft")
    assert not harness.repository.get_governed(WID).governance.migrated


def test_byte_ceiling_refuses_and_never_truncates(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    created = harness.repository.create_governed(payload(), born())
    monkeypatch.setattr("app.persistence.workflow_governance_store.HARD_CEILING_BYTES", 2_000)
    with pytest.raises(WorkflowHistoryUnavailableError):
        publish(harness, created, 1)
    assert harness.repository.get_governed(WID) == created


# --- archiver, compaction and reads ---------------------------------------------------


def test_drain_archives_then_marks_and_keeps_the_revision(harness: Harness) -> None:
    created = harness.repository.create_governed(payload(), born())
    first = publish(harness, created, 1)
    assert harness.repository.drain_outbox(WID, now=NOW) == 5
    drained = harness.repository.get_governed(WID)
    assert drained.governance.outbox == ()
    assert all(item.archived for item in drained.governance.decided_proposals)
    assert all(item.record is not None for item in drained.governance.decided_proposals)
    assert all(item.archived for item in drained.governance.governance_events)
    assert drained.definition.revision == first.definition.revision
    assert drained.definition.write_nonce != first.definition.write_nonce
    assert harness.repository.drain_outbox(WID, now=NOW) == 0
    assert harness.repository.verify_governance_state() == []
    assert harness.repository.verify_dispatch_state() == []


def test_many_publications_compact_and_stay_readable(harness: Harness) -> None:
    current = harness.repository.create_governed(payload(), born())
    for number in range(1, 21):
        current = publish(harness, current, number)
        harness.repository.drain_outbox(WID, now=NOW)
        current = harness.repository.get_governed(WID)
    hot = [item.version for item in current.definition.versions]
    assert len(hot) == 16 and hot[-1] == 20
    assert current.definition.latest_version == 20 == current.definition.stored_active_version
    old = harness.repository.get_version(WID, 1)
    assert old is not None and old.stages == stages("Reason 1")
    assert harness.repository.get_version(WID, 20) == current.definition.versions[-1]
    assert harness.repository.get_version(WID, 21) is None
    assert len(current.governance.version_provenance) == 20
    assert harness.repository.verify_governance_state() == []
    assert harness.repository.verify_dispatch_state() == []


def test_drain_all_covers_every_migrated_definition(harness: Harness) -> None:
    harness.repository.create_governed(payload(), born())
    other = payload().model_copy(update={"workflow_id": "other"})
    harness.repository.create(other)
    assert harness.repository.drain_all(now=NOW) == 1


def test_memory_and_mongo_reach_the_same_governance_state() -> None:
    results = []
    for kind in ("memory", "mongo"):
        harness = Harness(kind)
        current = harness.repository.create_governed(payload(), born())
        for number in (1, 2):
            current = publish(harness, current, number)
        harness.repository.drain_outbox(WID, now=NOW)
        results.append(harness.repository.get_governed(WID))
    memory, mongo = results
    strip = {"write_nonce": None}
    assert memory.definition.model_copy(update=strip) == mongo.definition.model_copy(update=strip)

    def comparable(item: GovernedDefinition) -> dict[str, Any]:
        dumped = item.governance.model_dump(mode="json")
        for entry in dumped["decided_proposals"]:  # proposal ids are random per run
            entry.pop("proposal_id"), entry.pop("record"), entry.pop("record_hash")
        for entry in dumped["governance_events"] + dumped["version_provenance"]:
            entry.pop("proposal_id", None)
        dumped["outbox"] = [entry["collection"] for entry in dumped["outbox"]]
        return dumped

    assert comparable(memory) == comparable(mongo)


def test_housekeeping_keeps_the_client_revision_but_refuses_the_old_nonce(
    harness: Harness,
) -> None:
    created = harness.repository.create_governed(payload(), born())
    first = publish(harness, created, 1)
    held = submit(harness, first, 2)  # a writer's snapshot taken before the drain
    assert harness.repository.drain_outbox(WID, now=NOW) == 5
    # A writer still holding the pre-housekeeping nonce is refused...
    stale, governance = approve(held, 2)
    with pytest.raises(PersistenceConflictError):
        harness.repository.write_governance(
            stale,
            governance,
            expected_revision=held.definition.revision,
            active_version=2,
            latest_version=2,
        )
    # ...while a client request carrying the pre-housekeeping revision still succeeds,
    # because the service re-reads (fresh nonce) and the revision did not move.
    client_revision = held.definition.revision
    fresh = harness.repository.get_governed(WID)
    assert fresh.definition.revision == client_revision
    definition, governance = approve(fresh, 2)
    written = harness.repository.write_governance(
        definition,
        governance,
        expected_revision=client_revision,
        active_version=2,
        latest_version=2,
    )
    assert written.definition.latest_version == 2


# --- QG R1: stored-value validation, history guard, integrity without drain -----------


def _two_versions(harness: Harness) -> GovernedDefinition:
    current = harness.repository.create_governed(payload(), born())
    current = publish(harness, current, 1)
    return publish(harness, current, 2)


def version_numbered(number: int) -> WorkflowVersion:
    return WorkflowVersion(
        version=number, stages=stages("x"), activated_at=NOW, activated_by="director-one"
    )


@pytest.mark.parametrize("latest", [1, 2, 4])  # decreasing, equal, skipping
def test_publication_must_raise_latest_by_exactly_one(harness: Harness, latest: int) -> None:
    current = _two_versions(harness)
    definition, governance = approve(current, 3)
    definition = definition.model_copy(
        update={"versions": (*current.definition.versions, version_numbered(latest))}
    )
    with pytest.raises(ValueError):
        harness.repository.write_governance(
            definition,
            governance,
            expected_revision=current.definition.revision,
            active_version=latest,
            latest_version=latest,
        )
    assert harness.repository.get_governed(WID) == current


def test_caller_supplied_version_fields_are_never_trusted(harness: Harness) -> None:
    current = _two_versions(harness)
    forged = current.definition.model_copy(
        update={
            "versions": current.definition.versions[:1],
            "latest_version": 0,
            "stored_active_version": 0,
            "revision": current.definition.revision + 1,
        }
    )
    with pytest.raises((ValueError, GovernanceHistoryRewriteError)):
        harness.repository.write_governance(
            forged,
            current.governance,
            expected_revision=current.definition.revision,
            active_version=1,
            latest_version=1,
        )
    assert harness.repository.get_governed(WID).definition.latest_version == 2


def test_mongo_filters_assert_active_and_latest_as_read() -> None:
    harness = Harness("mongo")
    current = _two_versions(harness)
    query = harness.definitions.log[-1][2][0]
    assert (query["active_version"], query["latest_version"]) == (1, 1)
    harness.repository.drain_outbox(WID, now=NOW)
    query = harness.definitions.log[-1][2][0]
    assert (query["active_version"], query["latest_version"]) == (2, 2)
    assert query["revision"] == current.definition.revision


def _without(current: GovernedDefinition, kind: str) -> tuple[WorkflowDefinition, Any]:
    definition = current.definition.model_copy(update={"revision": current.definition.revision + 1})
    state = current.governance
    if kind == "outbox":
        return definition, state.model_copy(update={"outbox": state.outbox[1:]})
    if kind == "decided":
        return definition, state.model_copy(update={"decided_proposals": ()})
    if kind == "event":
        events = state.governance_events[:-1]
        return definition, state.model_copy(update={"governance_events": events})
    if kind == "latest_version":
        return definition.model_copy(update={"versions": definition.versions[:1]}), state
    if kind == "unarchived_version":
        return definition.model_copy(update={"versions": definition.versions[1:]}), state
    if kind == "provenance":
        return definition, state.model_copy(update={"version_provenance": ()})
    if kind == "archived_flag":
        events = tuple(
            item.model_copy(update={"archived": True}) for item in state.governance_events
        )
        return definition, state.model_copy(update={"governance_events": events})
    raise AssertionError(kind)


@pytest.mark.parametrize(
    "kind",
    [
        "outbox",
        "decided",
        "event",
        "latest_version",
        "unarchived_version",
        "provenance",
        "archived_flag",
    ],
)
def test_a_write_never_drops_or_rewrites_history(harness: Harness, kind: str) -> None:
    current = _two_versions(harness)
    definition, governance = _without(current, kind)
    with pytest.raises(GovernanceHistoryRewriteError):
        harness.repository.write_governance(
            definition, governance, expected_revision=current.definition.revision
        )
    assert harness.repository.get_governed(WID) == current
    assert harness.repository.authorise_dispatch(WID, 2)


def test_new_history_must_be_referenced_by_the_outbox(harness: Harness) -> None:
    current = _two_versions(harness)
    extra = GovernanceEvent(
        sequence=current.governance.governance_sequence + 1,
        occurred_at=NOW,
        actor_id="hr-author",
        kind=GovernanceEventKind.PROPOSAL_EDITED,
        summary="Edited",
    )
    governance = current.governance.model_copy(
        update={
            "governance_events": (*current.governance.governance_events, extra),
            "governance_sequence": extra.sequence,
        }
    )
    definition = current.definition.model_copy(update={"revision": current.definition.revision + 1})
    with pytest.raises(GovernanceHistoryRewriteError):
        harness.repository.write_governance(
            definition, governance, expected_revision=current.definition.revision
        )
    governance = governance.model_copy(
        update={"outbox": (*governance.outbox, outbox_for_event(WID, extra))}
    )
    written = harness.repository.write_governance(
        definition, governance, expected_revision=current.definition.revision
    )
    assert written.governance.governance_events[-1] == extra


def test_integrity_conflict_refuses_writes_even_without_a_drain(harness: Harness) -> None:
    current = harness.repository.create_governed(payload(), born())
    current = submit(harness, publish(harness, current, 1), 2)
    entry = current.governance.outbox[0]
    harness.repository._cold.insert(  # noqa: SLF001 - plant a conflicting cold copy
        entry.collection,
        ColdRecord(
            logical_id=entry.logical_id,
            attempt=0,
            content_hash="ab" * 32,
            workflow_id=WID,
            archived_at=NOW,
            record={"x": 1},
        ),
    )
    definition, governance = approve(current, 2)
    with pytest.raises(ColdHistoryIntegrityError):
        harness.repository.write_governance(
            definition,
            governance,
            expected_revision=current.definition.revision,
            active_version=2,
            latest_version=2,
        )
    assert harness.repository.get_governed(WID) == current


# --- QG R2 notes: open proposal, notices, baseline ------------------------------------


def _bump(current: GovernedDefinition) -> WorkflowDefinition:
    return current.definition.model_copy(update={"revision": current.definition.revision + 1})


def _event(current: GovernedDefinition, kind: GovernanceEventKind, pid: str) -> GovernanceEvent:
    return GovernanceEvent(
        sequence=current.governance.governance_sequence + 1,
        occurred_at=NOW,
        actor_id="hr-author",
        kind=kind,
        proposal_id=pid,
        summary=kind.value.title(),
    )


def _with_open_proposal(harness: Harness, *, pending: bool = False) -> GovernedDefinition:
    current = publish(harness, harness.repository.create_governed(payload(), born()), 1)
    content = stages("Open")
    proposal = WorkflowProposal(
        proposal_id=str(uuid4()),
        workflow_id=WID,
        state=ProposalState.PENDING_APPROVAL if pending else ProposalState.DRAFT,
        base_version=1,
        stages=content,
        author_id="hr-author",
        created_at=NOW,
        updated_at=NOW,
        last_activity_at=NOW,
        revision=2,
        submitted_at=NOW if pending else None,
        content_hash=proposal_content_hash(ProposalKind.CHANGE, content) if pending else None,
    )
    created = _event(current, GovernanceEventKind.PROPOSAL_CREATED, proposal.proposal_id)
    state = current.governance
    governance = state.model_copy(
        update={
            "open_proposal": proposal,
            "governance_events": (*state.governance_events, created),
            "outbox": (*state.outbox, outbox_for_event(WID, created)),
            "governance_sequence": created.sequence,
        }
    )
    return harness.repository.write_governance(
        _bump(current), governance, expected_revision=current.definition.revision
    )


def _refused(harness: Harness, current: GovernedDefinition, governance: Any) -> None:
    with pytest.raises(GovernanceHistoryRewriteError):
        harness.repository.write_governance(
            _bump(current), governance, expected_revision=current.definition.revision
        )
    assert harness.repository.get_governed(WID) == current


def test_an_open_proposal_is_never_silently_dropped_or_replaced(harness: Harness) -> None:
    current = _with_open_proposal(harness)
    stored = current.governance.open_proposal
    assert stored is not None
    _refused(harness, current, current.governance.model_copy(update={"open_proposal": None}))
    other = stored.model_copy(update={"proposal_id": str(uuid4())})
    _refused(harness, current, current.governance.model_copy(update={"open_proposal": other}))
    older = stored.model_copy(update={"revision": 1})
    _refused(harness, current, current.governance.model_copy(update={"open_proposal": older}))
    # Withdrawal: the record ends as a new, unarchived decided entry in the outbox.
    withdrawn = stored.model_copy(
        update={"state": ProposalState.WITHDRAWN, "withdrawn_at": NOW, "revision": 3}
    )
    event = _event(current, GovernanceEventKind.PROPOSAL_WITHDRAWN, stored.proposal_id)
    state = current.governance
    without_outbox = state.model_copy(
        update={
            "open_proposal": None,
            "decided_proposals": (
                *state.decided_proposals,
                decided_entry(withdrawn, ended_at=NOW),
            ),
            "governance_events": (*state.governance_events, event),
            "outbox": (*state.outbox, outbox_for_event(WID, event)),
            "governance_sequence": event.sequence,
        }
    )
    _refused(harness, current, without_outbox)
    complete = without_outbox.model_copy(
        update={"outbox": (*without_outbox.outbox, outbox_for_proposal(withdrawn))}
    )
    written = harness.repository.write_governance(
        _bump(current), complete, expected_revision=current.definition.revision
    )
    assert written.governance.open_proposal is None
    assert written.governance.decided_proposals[-1].record == withdrawn


def test_a_pending_proposal_keeps_its_frozen_content(harness: Harness) -> None:
    current = _with_open_proposal(harness, pending=True)
    stored = current.governance.open_proposal
    assert stored is not None
    edited = stored.model_copy(update={"stages": stages("Edited"), "revision": 3})
    _refused(harness, current, current.governance.model_copy(update={"open_proposal": edited}))
    touched = stored.model_copy(update={"revision": 3})
    written = harness.repository.write_governance(
        _bump(current),
        current.governance.model_copy(update={"open_proposal": touched}),
        expected_revision=current.definition.revision,
    )
    assert written.governance.open_proposal == touched


def test_notices_only_gain_an_acknowledgement(harness: Harness) -> None:
    current = publish(harness, harness.repository.create_governed(payload(), born()), 1)
    notice = GovernanceNotice(
        notice_id=str(uuid4()),
        raised_at=NOW,
        raised_by="director-one",
        version=1,
        reason="Emergency fallback for the test.",
    )
    current = harness.repository.write_governance(
        _bump(current),
        current.governance.model_copy(update={"notices": (notice,)}),
        expected_revision=current.definition.revision,
    )
    changed = notice.model_copy(update={"reason": "A rewritten reason text."})
    _refused(harness, current, current.governance.model_copy(update={"notices": (changed,)}))
    _refused(harness, current, current.governance.model_copy(update={"notices": ()}))
    acknowledged = notice.model_copy(
        update={"acknowledged_by": "hr-author", "acknowledged_at": NOW}
    )
    current = harness.repository.write_governance(
        _bump(current),
        current.governance.model_copy(update={"notices": (acknowledged,)}),
        expected_revision=current.definition.revision,
    )
    other = acknowledged.model_copy(update={"acknowledged_by": "someone-else"})
    _refused(harness, current, current.governance.model_copy(update={"notices": (other,)}))


def _baseline(options: tuple[str, ...], *, case_key: bool = False) -> RequiredBaseline:
    field = WorkflowField(
        field_id="choice",
        label="Choice",
        kind=WorkflowFieldKind.CHOICE,
        options=options,
    )
    return RequiredBaseline(
        seeded_from_version=1,
        updated_at_version=1,
        stages=(
            BaselineStage(
                stage_id="review",
                normalised_name="review",
                representative_name="Review",
                fields=(
                    BaselineField(
                        field_id="choice",
                        signature=FieldSignature(
                            kind=WorkflowFieldKind.CHOICE,
                            normalised_label="choice",
                            choice_options=options,
                            has_case_data_key=case_key,
                        ),
                        representative=field,
                    ),
                ),
                first_published_version=1,
                last_published_version=1,
            ),
        ),
    )


def _publish_with_baseline(
    harness: Harness, current: GovernedDefinition, number: int, baseline: RequiredBaseline
) -> GovernedDefinition:
    if current.governance.open_proposal is None:
        current = submit(harness, current, number)
    definition, governance = approve(current, number)
    return harness.repository.write_governance(
        definition,
        governance.model_copy(update={"required_baseline": baseline}),
        expected_revision=current.definition.revision,
        active_version=number,
        latest_version=number,
    )


def test_baseline_only_tightens_and_only_on_a_publication(harness: Harness) -> None:
    current = harness.repository.create_governed(payload(), born())
    current = _publish_with_baseline(harness, current, 1, _baseline(("a", "b", "c")))
    stricter = _baseline(("a", "b"))
    _refused(
        harness, current, current.governance.model_copy(update={"required_baseline": stricter})
    )
    current = submit(harness, current, 2)
    for weaker in (
        _baseline(("a", "b", "c", "d")),
        _baseline(("a",), case_key=True),
        RequiredBaseline(),
    ):
        with pytest.raises(GovernanceHistoryRewriteError):
            _publish_with_baseline(harness, current, 2, weaker)
        assert harness.repository.get_governed(WID) == current
    written = _publish_with_baseline(harness, current, 2, stricter)
    assert written.governance.required_baseline == stricter


# --- QG R3: identity and frozen content of an ending proposal -------------------------


def _end_with(harness: Harness, current: GovernedDefinition, record: WorkflowProposal) -> Any:
    entry = decided_entry(record, ended_at=NOW)
    state = current.governance
    governance = state.model_copy(
        update={
            "open_proposal": None,
            "decided_proposals": (*state.decided_proposals, entry),
            "outbox": (*state.outbox, outbox_for_proposal(record)),
        }
    )
    return harness.repository.write_governance(
        _bump(current), governance, expected_revision=current.definition.revision
    )


@pytest.mark.parametrize("pending", [False, True])
@pytest.mark.parametrize("change", ["stages", "author", "created_at", "same_id_author"])
def test_an_ending_or_kept_proposal_keeps_identity_and_content(
    harness: Harness, pending: bool, change: str
) -> None:
    current = _with_open_proposal(harness, pending=pending)
    stored = current.governance.open_proposal
    assert stored is not None
    ended = stored.model_copy(update={"state": ProposalState.WITHDRAWN, "withdrawn_at": NOW})
    with pytest.raises(GovernanceHistoryRewriteError):
        if change == "stages":
            alt = stages("Swapped")
            hashed = proposal_content_hash(ProposalKind.CHANGE, alt) if pending else None
            _end_with(
                harness, current, ended.model_copy(update={"stages": alt, "content_hash": hashed})
            )
        elif change == "author":
            _end_with(harness, current, ended.model_copy(update={"author_id": "someone-else"}))
        elif change == "created_at":
            moved = ended.model_copy(update={"created_at": NOW + timedelta(days=1)})
            _end_with(harness, current, moved)
        else:
            kept = stored.model_copy(update={"author_id": "someone-else"})
            harness.repository.write_governance(
                _bump(current),
                current.governance.model_copy(update={"open_proposal": kept}),
                expected_revision=current.definition.revision,
            )
    assert harness.repository.get_governed(WID) == current
    assert _end_with(harness, current, ended).governance.open_proposal is None


def test_a_pending_proposal_cannot_be_rebased_but_a_draft_can(harness: Harness) -> None:
    pending = _with_open_proposal(harness, pending=True)
    stored = pending.governance.open_proposal
    assert stored is not None
    rebased = stored.model_copy(update={"base_version": 0})
    _refused(harness, pending, pending.governance.model_copy(update={"open_proposal": rebased}))


def test_draft_rebase_is_allowed(harness: Harness) -> None:
    draft = _with_open_proposal(harness)
    stored = draft.governance.open_proposal
    assert stored is not None
    rebased = stored.model_copy(update={"base_version": 0, "revision": 3})
    written = harness.repository.write_governance(
        _bump(draft),
        draft.governance.model_copy(update={"open_proposal": rebased}),
        expected_revision=draft.definition.revision,
    )
    assert written.governance.open_proposal == rebased


def test_a_new_decided_summary_must_match_its_record(harness: Harness) -> None:
    current = _with_open_proposal(harness)
    stored = current.governance.open_proposal
    assert stored is not None
    ended = stored.model_copy(update={"state": ProposalState.WITHDRAWN, "withdrawn_at": NOW})
    entry = decided_entry(ended, ended_at=NOW).model_copy(update={"author_id": "someone-else"})
    state = current.governance
    governance = state.model_copy(
        update={
            "open_proposal": None,
            "decided_proposals": (*state.decided_proposals, entry),
            "outbox": (*state.outbox, outbox_for_proposal(ended)),
        }
    )
    _refused(harness, current, governance)


# --- QG R4: a governed decided entry only ever ends the stored open proposal ----------


def test_a_decided_entry_without_the_stored_open_proposal_is_refused(harness: Harness) -> None:
    current = publish(harness, harness.repository.create_governed(payload(), born()), 1)
    definition, governance = approve(current, 2)  # invents a proposal never stored
    with pytest.raises(GovernanceHistoryRewriteError):
        harness.repository.write_governance(
            definition,
            governance,
            expected_revision=current.definition.revision,
            active_version=2,
            latest_version=2,
        )
    assert harness.repository.get_governed(WID) == current


def test_a_decided_entry_for_a_proposal_that_stays_open_is_refused(harness: Harness) -> None:
    current = submit(
        harness, publish(harness, harness.repository.create_governed(payload(), born()), 1), 2
    )
    definition, governance = approve(current, 2)
    still_open = governance.model_copy(update={"open_proposal": current.governance.open_proposal})
    with pytest.raises(GovernanceHistoryRewriteError):
        harness.repository.write_governance(
            definition,
            still_open,
            expected_revision=current.definition.revision,
            active_version=2,
            latest_version=2,
        )
    assert harness.repository.get_governed(WID) == current


# --- M2: deactivation (ADR-017 4, CC-5) ------------------------------------------------


def _deactivation(current: GovernedDefinition) -> tuple[WorkflowDefinition, Any]:
    """Submit-then-approve of a DEACTIVATE proposal, written as one decision CAS."""

    opened = current.governance.open_proposal
    assert opened is not None and opened.kind == ProposalKind.DEACTIVATE
    record = opened.model_copy(
        update={
            "state": ProposalState.APPROVED,
            "revision": opened.revision + 1,
            "decided_at": NOW,
            "decided_by": "director-one",
            "decision_reason": "Deactivated for the test.",
        }
    )
    state = current.governance
    event = GovernanceEvent(
        sequence=state.governance_sequence + 1,
        occurred_at=NOW,
        actor_id="director-one",
        kind=GovernanceEventKind.DEACTIVATED,
        proposal_id=record.proposal_id,
        summary="Workflow deactivated",
    )
    governance = state.model_copy(
        update={
            "open_proposal": None,
            "decided_proposals": (*state.decided_proposals, decided_entry(record, ended_at=NOW)),
            "governance_events": (*state.governance_events, event),
            "outbox": (*state.outbox, outbox_for_proposal(record), outbox_for_event(WID, event)),
            "governance_sequence": event.sequence,
        }
    )
    definition = current.definition.model_copy(update={"revision": current.definition.revision + 1})
    return definition, governance


def _submit_deactivation(harness: Harness, current: GovernedDefinition) -> GovernedDefinition:
    proposal = WorkflowProposal(
        proposal_id=str(uuid4()),
        workflow_id=current.definition.workflow_id,
        kind=ProposalKind.DEACTIVATE,
        state=ProposalState.PENDING_APPROVAL,
        base_version=current.definition.stored_active_version or 0,
        author_id="hr-author",
        created_at=NOW,
        updated_at=NOW,
        last_activity_at=NOW,
        submitted_at=NOW,
        content_hash=proposal_content_hash(ProposalKind.DEACTIVATE, ()),
    )
    return harness.repository.write_governance(
        current.definition.model_copy(update={"revision": current.definition.revision + 1}),
        current.governance.model_copy(update={"open_proposal": proposal}),
        expected_revision=current.definition.revision,
    )


def _deactivate(harness: Harness, current: GovernedDefinition, **kwargs: Any) -> Any:
    definition, governance = _deactivation(current)
    governance = governance.model_copy(update=kwargs.pop("governance_update", {}))
    return harness.repository.write_governance(
        definition,
        governance,
        expected_revision=current.definition.revision,
        deactivate=True,
        **kwargs,
    )


def test_deactivation_sets_active_to_zero_and_keeps_everything_else(harness: Harness) -> None:
    current = publish(harness, harness.repository.create_governed(payload(), born()), 1)
    current = _submit_deactivation(harness, current)
    written = _deactivate(harness, current, active_version=0)
    logged = harness.definitions.log[-1] if harness.kind == "mongo" else None
    assert written.definition.stored_active_version == 0
    assert written.definition.latest_version == 1
    assert written.definition.versions == current.definition.versions
    assert written.governance.required_baseline == current.governance.required_baseline
    assert written.governance.decided_proposals[-1].published_version is None
    assert not harness.repository.authorise_dispatch(WID, 1)
    assert harness.repository.verify_dispatch_state() == []
    harness.repository.drain_outbox(WID, now=NOW)
    assert harness.repository.verify_governance_state() == []
    assert harness.repository.verify_dispatch_state() == []
    if logged is not None:
        query, update = logged[2]
        assert (query["active_version"], query["latest_version"]) == (1, 1)
        assert update["$set"]["active_version"] == 0
        assert update["$set"]["latest_version"] == 1


def test_reactivation_publishes_latest_plus_one_from_active_zero(harness: Harness) -> None:
    current = publish(harness, harness.repository.create_governed(payload(), born()), 1)
    current = _deactivate(harness, _submit_deactivation(harness, current))
    reactivated = publish(harness, current, 2)
    assert (
        reactivated.definition.stored_active_version == 2 == reactivated.definition.latest_version
    )
    harness.repository.drain_outbox(WID, now=NOW)
    assert harness.repository.verify_governance_state() == []
    assert harness.repository.authorise_dispatch(WID, 2)


def test_deactivation_is_refused_on_onboarding() -> None:
    """Shared rule (both modes call ``prepare_governance_write`` first, before any write)."""

    published = WorkflowVersion(
        version=1, stages=stages("Onboarding"), activated_at=NOW, activated_by="director-one"
    )
    onboarding = payload(published).model_copy(
        update={
            "workflow_id": ONBOARDING_WORKFLOW_ID,
            "stored_active_version": 1,
            "latest_version": 1,
        }
    )
    stored = GovernedDefinition(onboarding, born())
    with pytest.raises(ValueError, match="onboarding"):
        prepare_governance_write(
            stored,
            onboarding.model_copy(update={"revision": 2}),
            born(),
            InMemoryColdHistoryStore(),
            active_version=0,
            latest_version=None,
            deactivate=True,
        )


def test_deactivation_is_refused_when_nothing_is_active(harness: Harness) -> None:
    empty = _submit_deactivation(harness, harness.repository.create_governed(payload(), born()))
    with pytest.raises(ValueError):
        _deactivate(harness, empty)
    assert harness.repository.get_governed(WID) == empty


def test_deactivation_twice_and_with_a_publication_are_refused(harness: Harness) -> None:
    current = publish(harness, harness.repository.create_governed(payload(), born()), 1)
    current = _submit_deactivation(harness, current)
    with pytest.raises(ValueError):
        _deactivate(harness, current, latest_version=1)
    current = _deactivate(harness, current)
    again = _submit_deactivation(harness, current)
    with pytest.raises(ValueError):
        _deactivate(harness, again)


def test_deactivation_keeps_the_baseline_byte_identical(harness: Harness) -> None:
    current = harness.repository.create_governed(payload(), born())
    current = _publish_with_baseline(harness, current, 1, _baseline(("a", "b", "c")))
    current = _submit_deactivation(harness, current)
    with pytest.raises((ValueError, GovernanceHistoryRewriteError)):
        _deactivate(
            harness, current, governance_update={"required_baseline": _baseline(("a", "b"))}
        )
    assert harness.repository.get_governed(WID) == current
    written = _deactivate(harness, current)
    assert written.governance.required_baseline.model_dump(mode="json") == (
        current.governance.required_baseline.model_dump(mode="json")
    )
