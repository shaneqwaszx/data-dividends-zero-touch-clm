"""ADR-017 1.4 / B-0 2: the P2-1 migration library, its dry-run CLI, the P2-1 startup
verification and the mixed-version owner conditions.

Dict-backed doubles only (no Mongo server, no mongomock).
"""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from scripts import p2_1_migration as cli
from test_workflow_governance_cold_store import FakeClient, FakeCollection

from app.domain.workflow_governance import (
    GOVERNANCE_TOP_LEVEL_FIELDS,
    LEGACY_VERSION_NOTE,
    BaselineField,
    BaselineStage,
    ColdRecord,
    FieldSignature,
    GovernanceEventKind,
    OutboxCollection,
    ProposalOrigin,
    ProposalState,
    RequiredBaseline,
    VersionOrigin,
    VersionProvenance,
)
from app.domain.workflows import (
    WorkflowAuditEvent,
    WorkflowDefinition,
    WorkflowField,
    WorkflowFieldKind,
    WorkflowStage,
    WorkflowVersion,
)
from app.persistence.adr017_backfill import (
    BackfillRefusedError,
    apply_backfill,
    plan_backfill,
    verify_definition_document,
    verify_definitions,
    verify_p2_1_definition_document,
    verify_p2_1_definitions,
)
from app.persistence.adr017_migrations import (
    ReverseMigrationRefusedError,
    apply_reverse_migration,
    plan_reverse_migration,
)
from app.persistence.errors import PersistenceOutcomeAmbiguousError
from app.persistence.p2_1_migration import (
    MigrationRefusedError,
    PlannedMigration,
    apply_p2_1_migration,
    plan_p2_1_migration,
    store_cold_inserts,
)
from app.persistence.workflow_governance_store import (
    InMemoryColdHistoryStore,
    decode_governance_fields,
    dict_hash,
)
from app.services.workflow_repository import InMemoryWorkflowDefinitionRepository

NOW = datetime(2031, 3, 1, 9, 0, tzinfo=UTC)
LATER = NOW + timedelta(days=1)
DATABASE = "clm_p12_000000000000000000000000"


def stages(label: str) -> tuple[WorkflowStage, ...]:
    field = WorkflowField(field_id="reason", label=label, kind=WorkflowFieldKind.TEXT)
    return (WorkflowStage(stage_id="review", name="Review", fields=(field,)),)


def version(number: int) -> WorkflowVersion:
    return WorkflowVersion(
        version=number,
        stages=stages(f"Reason {number}"),
        activated_at=NOW + timedelta(hours=number),
        activated_by=f"director-{number}",
    )


def audit(actor: str, action: str, minutes: int) -> WorkflowAuditEvent:
    return WorkflowAuditEvent(
        occurred_at=NOW + timedelta(minutes=minutes), actor_id=actor, action=action, summary="x"
    )


def p2_0_raw(
    workflow_id: str = "refresh",
    *,
    versions: tuple[WorkflowVersion, ...] = (version(1), version(2)),
    draft: bool = True,
    audit_events: tuple[WorkflowAuditEvent, ...] | None = None,
    nonce: str | None = "1" * 32,
) -> dict[str, Any]:
    events = (
        (
            audit("hr-early", "DRAFT_SAVED", 1),
            audit("director-2", "ACTIVATED", 2),
            audit("hr-latest", "DRAFT_SAVED", 3),
        )
        if audit_events is None
        else audit_events
    )
    definition = WorkflowDefinition(
        workflow_id=workflow_id,
        name="Refresh",
        use_case="Case refresh",
        country="Singapore",
        revision=4,
        draft_stages=stages("Draft") if draft else (),
        versions=versions,
        audit=events,
        created_at=NOW,
        updated_at=NOW + timedelta(minutes=5),
    )
    latest = max((item.version for item in versions), default=0)
    raw: dict[str, Any] = {
        "_id": workflow_id,
        "revision": 4,
        "active_version": latest,
        "latest_version": latest,
        "dispatch_authorisation_seq": 3,
        "payload": definition.model_dump(mode="json"),
    }
    if nonce is not None:
        raw["write_nonce"] = nonce
    return raw


class Seeder:
    def __init__(self) -> None:
        self.calls: list[int] = []

    def __call__(self, active: WorkflowVersion) -> RequiredBaseline:
        self.calls.append(active.version)
        stage = active.stages[0]
        field = stage.fields[0]
        return RequiredBaseline(
            seeded_from_version=active.version,
            updated_at_version=active.version,
            stages=(
                BaselineStage(
                    stage_id=stage.stage_id,
                    normalised_name="review",
                    representative_name=stage.name,
                    fields=(
                        BaselineField(
                            field_id=field.field_id,
                            signature=FieldSignature(
                                kind=field.kind,
                                normalised_label=field.label.lower(),
                                has_case_data_key=False,
                            ),
                            representative=field,
                        ),
                    ),
                    first_published_version=active.version,
                    last_published_version=active.version,
                ),
            ),
        )


def collection(*raws: dict[str, Any]) -> FakeCollection:
    return FakeCollection({raw["_id"]: copy.deepcopy(raw) for raw in raws})


def plan(definitions: FakeCollection, **kwargs: Any) -> Any:
    kwargs.setdefault("seed_baseline", Seeder())
    kwargs.setdefault("now", LATER)
    return plan_p2_1_migration(definitions.find({}), **kwargs)


def migrate(*raws: dict[str, Any]) -> tuple[FakeCollection, InMemoryColdHistoryStore]:
    definitions, cold = collection(*raws), InMemoryColdHistoryStore()
    apply_p2_1_migration(plan(definitions, cold=cold), definitions, cold, now=LATER)
    return definitions, cold


def logical_cold(cold: InMemoryColdHistoryStore) -> set[tuple[str, str, str]]:
    return {
        (collection_.value, item.logical_id, item.content_hash)
        for collection_ in OutboxCollection
        for item in cold.all_records(collection_)
    }


# --- planning (dry run) ---------------------------------------------------------------


def test_dry_run_reports_planned_changes_and_writes_nothing() -> None:
    definitions, cold = (
        collection(p2_0_raw(), p2_0_raw("empty", versions=(), draft=False)),
        (InMemoryColdHistoryStore()),
    )
    before = copy.deepcopy(definitions.documents)
    result = plan(definitions, cold=cold)
    assert definitions.log == [] and definitions.documents == before
    assert logical_cold(cold) == set()
    summary = result.summary()
    assert summary["refusals"] == [] and summary["already_migrated"] == []
    assert summary["to_migrate"] == [
        {
            "id": "refresh",
            "legacy_versions": 2,
            "legacy_draft_converted": True,
            "baseline_seeded_from_version": 2,
            "baseline_stages": 1,
            "cold_inserts": 3,
            "outbox_entries": 1,
        },
        {
            "id": "empty",
            "legacy_versions": 0,
            "legacy_draft_converted": False,
            "baseline_seeded_from_version": None,
            "baseline_stages": 0,
            "cold_inserts": 0,
            "outbox_entries": 1,
        },
    ]
    assert "payload" not in json.dumps(summary)


def test_plan_builds_honest_legacy_provenance_draft_and_baseline() -> None:
    seeder = Seeder()
    (planned,) = plan(collection(p2_0_raw()), seed_baseline=seeder).migrations
    state = planned.governance
    assert [item.version for item in state.version_provenance] == [1, 2]
    for item, number in zip(state.version_provenance, (1, 2), strict=True):
        assert item.origin == VersionOrigin.PRE_GOVERNANCE_DIRECTOR_ACTIVATION
        assert (item.author_id, item.approved_by, item.proposal_id) == (None, None, None)
        assert item.activated_by == f"director-{number}" and item.note == LEGACY_VERSION_NOTE
    # The baseline comes from the currently active version only (ADR-017 1.4).
    assert seeder.calls == [2] and state.required_baseline.seeded_from_version == 2
    (entry,) = state.decided_proposals
    assert entry.archived and entry.record is not None
    record = entry.record
    assert record.state == ProposalState.WITHDRAWN
    assert record.origin == ProposalOrigin.PRE_GOVERNANCE_DRAFT
    # ADR-017 1.4: the active version's D-123 activator, not the latest draft saver.
    assert record.author_id is None and record.legacy_editor == "director-2"
    assert record.stages == stages("Draft") and record.base_version == 2
    (event,) = state.governance_events
    assert event.kind == GovernanceEventKind.MIGRATED and event.actor_id is None
    assert [item.logical_id for item in state.outbox] == ["refresh:1"]
    marker = state.migration_marker
    assert marker is not None and marker.legacy_versions == 2 and marker.legacy_draft_converted
    assert state.governance_sequence == 1 and state.open_proposal is None


def _legacy_editor(raw: dict[str, Any]) -> str | None:
    (planned,) = plan(collection(raw)).migrations
    record = planned.governance.decided_proposals[0].record
    assert record is not None and record.author_id is None
    return record.legacy_editor


def test_legacy_editor_falls_back_to_the_latest_draft_saver_without_a_version() -> None:
    assert _legacy_editor(p2_0_raw(versions=())) == "hr-latest"


def test_legacy_editor_is_none_without_a_version_or_a_draft_saved_event() -> None:
    raw = p2_0_raw(versions=(), audit_events=(audit("director-2", "ACTIVATED", 2),))
    assert _legacy_editor(raw) is None


def test_legacy_editor_prefers_the_activator_even_without_a_draft_saved_event() -> None:
    raw = p2_0_raw(audit_events=(audit("someone", "ACTIVATED", 2),))
    assert _legacy_editor(raw) == "director-2"


def test_no_active_version_seeds_an_empty_baseline() -> None:
    seeder = Seeder()
    (planned,) = plan(
        collection(p2_0_raw(versions=(), draft=False)), seed_baseline=seeder
    ).migrations
    assert seeder.calls == [] and planned.governance.required_baseline == RequiredBaseline()
    assert planned.governance.decided_proposals == ()


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        (lambda raw: raw.pop("latest_version"), "NOT_BACKFILLED"),
        (lambda raw: raw.__setitem__("outbox", []), "GOVERNANCE_FIELDS_WITHOUT_MARKER"),
        (lambda raw: raw.__setitem__("revision", "4"), "REVISION_INVALID"),
        (lambda raw: raw.__setitem__("payload", {"bad": 1}), "DEFINITION_INVALID"),
    ],
)
def test_plan_refuses_unsafe_documents(change: Any, reason: str) -> None:
    raw = p2_0_raw()
    change(raw)
    definitions = collection(raw)
    result = plan(definitions)
    assert [item.reason for item in result.refusals] == [reason]
    with pytest.raises(MigrationRefusedError):
        apply_p2_1_migration(result, definitions, InMemoryColdHistoryStore(), now=LATER)
    assert definitions.log == []


def test_seeding_failure_is_a_refusal_never_a_guess() -> None:
    def broken(_version: WorkflowVersion) -> RequiredBaseline:
        raise RuntimeError("seeder unavailable")

    result = plan(collection(p2_0_raw()), seed_baseline=broken)
    assert [item.reason for item in result.refusals] == ["BASELINE_SEED_FAILED"]


def test_conflicting_cold_record_is_refused_at_plan_time() -> None:
    cold = InMemoryColdHistoryStore()
    other = version(1).model_copy(update={"activated_by": "someone-else"}).model_dump(mode="json")
    cold.insert(
        OutboxCollection.VERSIONS,
        ColdRecord(
            logical_id="refresh:1",
            attempt=0,
            content_hash=dict_hash(other),
            workflow_id="refresh",
            archived_at=NOW,
            record=other,
        ),
    )
    result = plan(collection(p2_0_raw()), cold=cold)
    assert [item.reason for item in result.refusals] == ["COLD_INTEGRITY_CONFLICT"]


# --- applying (library only; the M1 CLI never applies) --------------------------------


class OrderedCold(InMemoryColdHistoryStore):
    def __init__(self, order: list[str]) -> None:
        super().__init__()
        self.order = order

    def insert(self, collection_: OutboxCollection, record: ColdRecord) -> None:
        super().insert(collection_, record)
        self.order.append(f"cold:{record.logical_id}")


class OrderedCollection(FakeCollection):
    order: list[str]

    def with_options(self, **kwargs: Any) -> FakeCollection:
        view = OrderedCollection(self.documents, self.log, True, self.faults)
        view.order = self.order
        return view

    def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> Any:
        self.order.append("cas")
        return super().update_one(query, update)


def test_apply_inserts_cold_copies_first_then_one_marker_cas() -> None:
    order: list[str] = []
    raw = p2_0_raw()
    definitions = OrderedCollection({"refresh": copy.deepcopy(raw)})
    definitions.order = order
    cold = OrderedCold(order)
    assert apply_p2_1_migration(plan(definitions), definitions, cold, now=LATER) == 1
    assert order[-1] == "cas" and order.count("cas") == 1
    assert len(order) == 4 and all(item.startswith("cold:") for item in order[:-1])
    assert {"cold:refresh:1", "cold:refresh:2"} <= set(order[:-1])
    operation, durable, (query, update) = definitions.log[-1]
    assert (operation, durable) == ("update_one", True)
    assert query["p2_1_migration_marker"] == {"$exists": False}
    assert query["revision"] == 4 and query["write_nonce"] == "1" * 32
    assert list(update["$set"])[-1] == "p2_1_migration_marker"
    stored = definitions.documents["refresh"]
    # Payload, revision, versions fields and the D3 counter are unchanged.
    for key in ("payload", "revision", "active_version", "latest_version"):
        assert stored[key] == raw[key]
    assert stored["dispatch_authorisation_seq"] == 3
    assert stored["write_nonce"] != raw["write_nonce"]
    assert verify_p2_1_definition_document(stored, cold=cold) is None


def test_re_running_after_the_marker_is_a_no_op() -> None:
    definitions, cold = migrate(p2_0_raw())
    snapshot = copy.deepcopy(definitions.documents)
    writes = len(definitions.log)
    again = plan(definitions, cold=cold)
    assert again.migrations == [] and again.already_migrated == ["refresh"]
    assert apply_p2_1_migration(again, definitions, cold, now=LATER) == 0
    assert definitions.documents == snapshot and len(definitions.log) == writes


def _hot(definitions: FakeCollection) -> dict[str, Any]:
    stored = copy.deepcopy(definitions.documents["refresh"])
    stored.pop("write_nonce")
    return stored


def test_interrupted_after_cold_inserts_converges_to_the_same_end_state() -> None:
    clean, clean_cold = migrate(p2_0_raw())
    definitions, cold = collection(p2_0_raw()), InMemoryColdHistoryStore()
    (planned,) = plan(definitions, cold=cold).migrations
    store_cold_inserts(planned, cold, now=LATER)  # then the process dies before the CAS
    assert "p2_1_migration_marker" not in definitions.documents["refresh"]
    apply_p2_1_migration(plan(definitions, cold=cold), definitions, cold, now=LATER)
    assert _hot(definitions) == _hot(clean)
    assert logical_cold(cold) == logical_cold(clean_cold)
    # The re-run's duplicates got fresh attempt suffixes; nothing was overwritten.
    assert [item.attempt for item in cold.find(OutboxCollection.VERSIONS, "refresh:1")] == [0, 1]
    assert verify_p2_1_definition_document(definitions.documents["refresh"], cold=cold) is None


class FlakyCold(InMemoryColdHistoryStore):
    def __init__(self, fail_at: int) -> None:
        super().__init__()
        self.calls, self.fail_at = 0, fail_at

    def insert(self, collection_: OutboxCollection, record: ColdRecord) -> None:
        self.calls += 1
        super().insert(collection_, record)
        if self.calls == self.fail_at:
            raise PersistenceOutcomeAmbiguousError  # applied, acknowledgement lost


def test_interrupted_mid_cold_inserts_writes_no_marker_and_re_runs_safely() -> None:
    clean, clean_cold = migrate(p2_0_raw())
    definitions, cold = collection(p2_0_raw()), FlakyCold(fail_at=2)
    with pytest.raises(PersistenceOutcomeAmbiguousError):
        apply_p2_1_migration(plan(definitions, cold=cold), definitions, cold, now=LATER)
    assert not set(GOVERNANCE_TOP_LEVEL_FIELDS) & set(definitions.documents["refresh"])
    apply_p2_1_migration(plan(definitions, cold=cold), definitions, cold, now=LATER)
    assert _hot(definitions) == _hot(clean)
    assert logical_cold(cold) == logical_cold(clean_cold)


def test_a_definition_changed_after_planning_stops_the_apply() -> None:
    definitions, cold = collection(p2_0_raw()), InMemoryColdHistoryStore()
    planned = plan(definitions)
    definitions.documents["refresh"]["write_nonce"] = "2" * 32  # a concurrent writer
    with pytest.raises(MigrationRefusedError):
        apply_p2_1_migration(planned, definitions, cold, now=LATER)
    assert "p2_1_migration_marker" not in definitions.documents["refresh"]


def test_memory_mode_migration_matches_the_mongo_tool() -> None:
    definitions, _ = migrate(p2_0_raw())
    repository = InMemoryWorkflowDefinitionRepository()
    payload = WorkflowDefinition.model_validate(p2_0_raw()["payload"])
    repository.create(payload)
    assert repository.migrate_to_governance(Seeder(), now=LATER) == []
    governed = repository.get_governed("refresh")
    expected = decode_governance_fields(definitions.documents["refresh"])
    assert governed.governance.model_dump(mode="json") == expected.model_dump(mode="json")
    assert governed.definition.versions == payload.versions
    assert repository.verify_governance_state() == []
    assert repository.migrate_to_governance(Seeder(), now=LATER) == []  # idempotent


# --- P2-1 startup verification --------------------------------------------------------


def test_p2_1_verification_requires_the_marker() -> None:
    assert verify_p2_1_definition_document(p2_0_raw()) == "P2_1_NOT_MIGRATED"


def test_p2_1_verification_refuses_a_legacy_activation_after_the_marker() -> None:
    definitions, cold = migrate(p2_0_raw())
    stored = definitions.documents["refresh"]
    payload = WorkflowDefinition.model_validate(stored["payload"])
    # What a P2-0 (legacy) activation would write: a version with no provenance.
    appended = payload.model_copy(update={"versions": (*payload.versions, version(3))})
    stored.update(payload=appended.model_dump(mode="json"), active_version=3, latest_version=3)
    assert verify_p2_1_definition_document(stored, cold=cold) == "LATEST_WITHOUT_PROVENANCE"
    # Without the fields a P2-0 activation never wrote (activation is frozen at P2-0).
    stored.update(active_version=2, latest_version=2)
    assert verify_p2_1_definition_document(stored, cold=cold) == "LAST_VERSION_NOT_LATEST"


def test_p2_1_verification_refuses_ungoverned_provenance_and_cold_above_latest() -> None:
    definitions, cold = migrate(p2_0_raw())
    stored = copy.deepcopy(definitions.documents["refresh"])
    provenance = stored["version_provenance"]
    forged = VersionProvenance(
        version=2,
        origin=VersionOrigin.GOVERNED_APPROVAL,
        author_id="hr-author",
        approved_by="director-one",
        proposal_id="00000000-0000-0000-0000-000000000000",
        published_at=NOW,
    ).model_dump(mode="json")
    stored["version_provenance"] = [provenance[0], forged]
    marker = dict(stored["p2_1_migration_marker"], legacy_versions=1)
    stored["p2_1_migration_marker"] = marker
    assert verify_p2_1_definition_document(stored, cold=cold) == (
        "GOVERNED_VERSION_WITHOUT_PROPOSAL"
    )
    record = version(9).model_dump(mode="json")
    cold.insert(
        OutboxCollection.VERSIONS,
        ColdRecord(
            logical_id="refresh:9",
            attempt=0,
            content_hash=dict_hash(record),
            workflow_id="refresh",
            archived_at=NOW,
            record=record,
        ),
    )
    assert verify_p2_1_definition_document(definitions.documents["refresh"], cold=cold) == (
        "COLD_VERSION_ABOVE_LATEST"
    )


def test_p2_1_verification_refuses_an_outbox_without_its_full_record() -> None:
    definitions, cold = migrate(p2_0_raw())
    stored = copy.deepcopy(definitions.documents["refresh"])
    stored["outbox"][0]["content_hash"] = "0" * 64
    assert verify_p2_1_definition_document(stored, cold=cold) == "OUTBOX_HASH_MISMATCH"
    stored = copy.deepcopy(definitions.documents["refresh"])
    stored["governance_events"] = []
    assert verify_p2_1_definition_document(stored, cold=cold) == "OUTBOX_REFERENCE_MISSING"
    stored = copy.deepcopy(definitions.documents["refresh"])
    stored["p2_1_migration_marker"]["legacy_versions"] = 5
    assert verify_p2_1_definition_document(stored, cold=cold) == "LEGACY_PROVENANCE_MISMATCH"


def test_p2_1_verification_refuses_missing_cold_history() -> None:
    definitions, _ = migrate(p2_0_raw())
    stored = definitions.documents["refresh"]
    assert verify_p2_1_definition_document(stored) is None  # hot-only checks pass
    assert verify_p2_1_definition_document(stored, cold=InMemoryColdHistoryStore()) == (
        "VERSION_NOT_ARCHIVED"
    )


# --- mixed-version owner conditions ---------------------------------------------------


def test_p2_0_release_refuses_a_migrated_document() -> None:
    """(a) The P2-0 check and the P2-0 reverse migration both refuse migrated content."""

    definitions, _ = migrate(p2_0_raw())
    stored = definitions.documents["refresh"]
    assert verify_definition_document(stored) == "P2_1_CONTENT_NOT_SUPPORTED_BY_P2_0"
    writes = len(definitions.log)
    reverse = plan_reverse_migration(
        FakeCollection(), definitions, decode_legacy_case=lambda raw: raw
    )
    assert [item.reason for item in reverse.refusals] == ["P2_1_CONTENT_PRESENT"]
    with pytest.raises(ReverseMigrationRefusedError):
        apply_reverse_migration(reverse, FakeCollection(), definitions)
    assert len(definitions.log) == writes


def test_accidental_old_writer_startup_fails_closed_without_writes() -> None:
    """(c) A P2-0 process started over a migrated store: its startup verification refuses
    every migrated document (so its fence stays unavailable: no dispatch, no provider
    call) and its backfill refuses to touch them. Nothing is written."""

    definitions, cold = migrate(p2_0_raw(), p2_0_raw("other", draft=False))
    writes = len(definitions.log)
    findings = verify_definitions(definitions.find({}))
    assert {(item.workflow_id, item.reason) for item in findings} == {
        ("refresh", "P2_1_CONTENT_NOT_SUPPORTED_BY_P2_0"),
        ("other", "P2_1_CONTENT_NOT_SUPPORTED_BY_P2_0"),
    }
    backfill = plan_backfill(definitions)  # type: ignore[arg-type]
    assert {item.reason for item in backfill.refusals} == {"P2_1_MIGRATED"}
    with pytest.raises(BackfillRefusedError):
        apply_backfill(backfill, definitions)  # type: ignore[arg-type]
    assert len(definitions.log) == writes
    # The P2-1 release accepts the same store.
    assert verify_p2_1_definitions(definitions.find({}), cold=cold) == []


# --- the dry-run CLI ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("argv", "reason"),
    [
        (["--database", DATABASE, "--apply"], "APPLY_NOT_AVAILABLE"),
        (["--database", DATABASE, "--dry-run", "--apply"], "APPLY_NOT_AVAILABLE"),
        (["--database", DATABASE, "--execute"], "APPLY_NOT_AVAILABLE"),
        (["--database", DATABASE], "DRY_RUN_REQUIRED"),
        (["--database", DATABASE, "--dry-run", "--yes"], "UNKNOWN_ARGUMENT"),
        (["--database", "clm_poc", "--dry-run"], "FORBIDDEN_DATABASE"),
        (["--database", "CLM_POC", "--dry-run"], "FORBIDDEN_DATABASE"),
    ],
)
def test_cli_refuses_anything_but_a_dry_run(
    argv: list[str], reason: str, capsys: pytest.CaptureFixture[str]
) -> None:
    def no_client(_uri: str) -> Any:
        raise AssertionError("a refused run never connects")

    assert cli.main(argv, client_factory=no_client, seed_baseline=Seeder()) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "REFUSED" and report["reason"] == reason


def test_cli_refuses_without_the_baseline_seeder(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "_default_seeder", lambda: None)
    assert cli.main(["--database", DATABASE, "--dry-run"]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "BASELINE_SEEDER_UNAVAILABLE"


def test_cli_dry_run_reads_only_and_never_prints_the_uri(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    uri = "mongodb://synthetic-user:synthetic-secret@localhost:1/x"
    monkeypatch.setenv(cli.URI_ENVIRONMENT_KEY, uri)
    client = FakeClient()
    client[DATABASE].collections["clm_workflow_definitions"] = collection(p2_0_raw())
    assert (
        cli.main(
            ["--database", DATABASE, "--dry-run"],
            client_factory=lambda _uri: client,
            seed_baseline=Seeder(),
            now=LATER,
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "synthetic-secret" not in out and uri not in out
    report = json.loads(out)
    assert report["status"] == "READY" and report["mode"] == "DRY_RUN"
    assert [item["id"] for item in report["to_migrate"]] == ["refresh"]
    database = client[DATABASE]
    assert all(not item.log and not item.indexes for item in database.collections.values())
    assert client.closed


def test_cli_failure_reports_only_the_error_type(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    uri = "mongodb://synthetic-user:synthetic-secret@localhost:1/x"
    monkeypatch.setenv(cli.URI_ENVIRONMENT_KEY, uri)
    client = FakeClient()
    client[DATABASE].collections["clm_workflow_definitions"] = FakeCollection(
        faults={"find": [RuntimeError(uri)]}
    )
    assert (
        cli.main(
            ["--database", DATABASE, "--dry-run"],
            client_factory=lambda _uri: client,
            seed_baseline=Seeder(),
        )
        == 3
    )
    out = capsys.readouterr().out
    assert json.loads(out) == {"status": "FAILED", "error_type": "RuntimeError"}
    assert "synthetic-secret" not in out


def test_planned_migration_is_frozen() -> None:
    (planned,) = plan(collection(p2_0_raw())).migrations
    assert isinstance(planned, PlannedMigration)
    with pytest.raises(AttributeError):
        planned.revision = 5  # type: ignore[misc]
