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
    GovernanceEvent,
    GovernanceEventKind,
    MigrationMarker,
    ProposalKind,
    ProposalState,
    VersionOrigin,
    VersionProvenance,
    WorkflowGovernanceState,
    WorkflowProposal,
    proposal_content_hash,
)
from app.domain.workflows import (
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
    GovernedDefinition,
    WorkflowGovernanceNotMigratedError,
    WorkflowHistoryUnavailableError,
    decided_entry,
    outbox_for_event,
    outbox_for_proposal,
    outbox_for_version,
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


def approve(current: GovernedDefinition, number: int) -> tuple[WorkflowDefinition, Any]:
    """What WS-B's decision writes: one CAS with version, provenance, record, events, outbox."""

    at = NOW + timedelta(hours=number)
    content = stages(f"Reason {number}")
    proposal = WorkflowProposal(
        proposal_id=str(uuid4()),
        workflow_id=WID,
        state=ProposalState.APPROVED,
        base_version=current.definition.stored_active_version or 0,
        stages=content,
        author_id="hr-author",
        created_at=at,
        updated_at=at,
        last_activity_at=at,
        submitted_at=at,
        content_hash=proposal_content_hash(ProposalKind.CHANGE, content),
        decided_at=at,
        decided_by="director-one",
        decision_reason="Approved for the test.",
        published_version=number,
    )
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
    assert first.definition.revision == 2
    # A writer holding the old snapshot never overwrites the publication.
    stale, governance = approve(created, 1)
    with pytest.raises(PersistenceConflictError):
        harness.repository.write_governance(
            stale, governance, expected_revision=1, active_version=1, latest_version=1
        )
    # Same revision, different nonce (another history): refused.
    other = first.definition.model_copy(update={"write_nonce": "0" * 32})
    with pytest.raises(PersistenceConflictError):
        harness.repository.write_governance(other, first.governance, expected_revision=2)
    assert harness.repository.get_governed(WID) == first


def test_mongo_governance_write_is_durable_and_filters_the_marker() -> None:
    harness = Harness("mongo")
    created = harness.repository.create_governed(payload(), born())
    insert = harness.definitions.log[-1]
    assert insert[:2] == ("insert_one", True)
    publish(harness, created, 1)
    operation, durable, (query, update) = harness.definitions.log[-1]
    assert (operation, durable) == ("update_one", True)
    assert query["revision"] == 1 and query["write_nonce"] == created.definition.write_nonce
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
        harness.repository.write_governance(definition, governance, expected_revision=2)
    with pytest.raises(ValueError):
        harness.repository.write_governance(
            definition, governance, expected_revision=2, active_version=2, latest_version=0
        )
    with pytest.raises(ValueError):
        harness.repository.write_governance(
            definition, governance, expected_revision=2, active_version=1, latest_version=2
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


def test_p2_0_write_preserves_every_governance_field(harness: Harness) -> None:
    created = harness.repository.create_governed(payload(), born())
    first = publish(harness, created, 1)
    before = (
        {key: harness.definitions.documents[WID][key] for key in GOVERNANCE_TOP_LEVEL_FIELDS}
        if harness.kind == "mongo"
        else None
    )
    # The P2-0 draft-save path: only payload, revision and nonce change.
    draft = first.definition.model_copy(update={"revision": 3, "draft_stages": stages("Draft")})
    harness.repository.update(draft, expected_revision=2)
    after = harness.repository.get_governed(WID)
    assert after.governance == first.governance
    assert after.definition.draft_stages == stages("Draft")
    if harness.kind == "mongo":
        stored = harness.definitions.documents[WID]
        assert {key: stored[key] for key in GOVERNANCE_TOP_LEVEL_FIELDS} == before
        assert stored["active_version"] == stored["latest_version"] == 1


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
