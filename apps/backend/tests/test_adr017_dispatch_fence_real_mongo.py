"""ADR-017 P2-0 writer release against a physical, disposable MongoDB (CT-4, CT-5, CT-16,
CT-17, CT-18, CT-20 where they apply).

Opt-in: runs only when ``PHASE12_MONGO_URI`` is set. Each test uses a newly generated
allowlisted database that is dropped afterwards; never ``clm_poc``, ``clm_staging`` or a
staging host. The pinned server is the staging image digest (7.0.40 standalone).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pymongo import MongoClient
from pymongo.write_concern import WriteConcern
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)
from test_adr017_reader_release import _snapshot

from app.domain.target_submission import (
    GoldTierExecutionLedgerState,
    GoldTierOperationMarker,
    WorkflowDispatchState,
)
from app.domain.workflows import ONBOARDING_WORKFLOW_ID, WorkflowDefinition, WorkflowVersion
from app.persistence.adr017_backfill import (
    BackfillRefusedError,
    apply_backfill,
    plan_backfill,
    verify_definitions,
)
from app.persistence.errors import PersistenceOutcomeAmbiguousError
from app.persistence.fence_store import MongoFenceLedger
from app.persistence.mongo_case_store import MongoCaseStore
from app.persistence.mongo_workflow_store import (
    MongoWorkflowDefinitionRepository,
    MongoWorkflowStore,
)
from app.persistence.repositories import MongoTargetExecutionRepository
from app.services.dispatch_fence import CHECK_UNAVAILABLE, DispatchFence, FenceHealth
from app.services.errors import DispatchFenceRefusedError
from app.services.target_execution_repository import TargetExecutionRepositoryConflictError

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")
CASES, DEFINITIONS = "clm_case_snapshots", "clm_workflow_definitions"
SHELL = GoldTierOperationMarker.SHELL
NOW = datetime(2031, 3, 1, 9, 0, tzinfo=UTC)
BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture
def lane() -> Iterator[dict[str, Any]]:
    database = generate_ephemeral_mongo_database("p12")
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    try:
        store = MongoCaseStore(client, database=database, collection=CASES)
        store.initialize()
        workflows = MongoWorkflowStore(
            client, database=database, definitions_collection=DEFINITIONS,
            runs_collection="clm_workflow_runs",
        )
        workflows.initialize()
        definitions = MongoWorkflowDefinitionRepository(workflows)
        definitions.create(
            WorkflowDefinition(
                workflow_id=ONBOARDING_WORKFLOW_ID, name="Corporate onboarding",
                use_case="Corporate onboarding", country="Singapore", created_at=NOW,
                updated_at=NOW,
            )
        )
        snapshot = _snapshot()
        search = (GoldTierOperationMarker.SEARCH,)
        entry = snapshot.target_executions[0].model_copy(
            update={
                "attempted_operations": search, "completed_operations": search,
                "resolved_operations": search,
            }
        )
        store.create(snapshot.model_copy(update={"target_executions": (entry,)}, deep=True))
        yield {
            "client": client, "database": database, "store": store,
            "ledger": MongoTargetExecutionRepository(store), "definitions": definitions,
            "entry": entry, "cases": client[database][CASES],
            "definitions_raw": client[database][DEFINITIONS],
        }
    finally:
        cleanup_ephemeral_mongo_database(client, database)
        client.close()


def _fence(lane: dict[str, Any], *, available: bool = True) -> DispatchFence:
    return DispatchFence(
        ledger=lane["ledger"], definitions=lane["definitions"],
        workflow_id=ONBOARDING_WORKFLOW_ID, hold=lambda _case_id: None,
        health=lambda: FenceHealth(available=available),
    )


def _authorise(lane: dict[str, Any]) -> Any:
    entry = lane["entry"]
    return _fence(lane).authorise_first_write(
        case_id=entry.submission_input.case_id,
        submission_id=entry.submission_input.submission_id, operation=SHELL,
    )


def _raw(lane: dict[str, Any]) -> dict[str, Any]:
    raw = lane["cases"].find_one({"_id": str(lane["entry"].submission_input.case_id)})
    assert raw is not None
    return raw


def _element(raw: dict[str, Any]) -> dict[str, Any]:
    return raw["target_executions"][0]


def test_the_fence_writes_the_marker_with_server_leases_and_a_post_image(lane) -> None:
    before = _raw(lane)
    written = _authorise(lane)
    after = _raw(lane)
    claim = _element(after)["workflow_dispatch"]
    assert claim["state"] == "AUTHORISED" and claim["first_write"]["operation"] == "SHELL"
    assert claim["first_write"]["receipt"] == claim["receipt"]
    assert isinstance(claim["lease_until"], datetime) and isinstance(claim["d3_at"], datetime)
    assert _element(after)["attempted_operations"] == ["SEARCH", "SHELL"]
    assert after["revision"] == before["revision"] + 3  # D2, D4, D5
    assert after["write_nonce"] != before["write_nonce"]
    assert written.workflow_dispatch.first_write.receipt == claim["receipt"]
    raw_definition = lane["definitions_raw"].find_one({"_id": ONBOARDING_WORKFLOW_ID})
    assert raw_definition["dispatch_authorisation_seq"] == 1


def test_d3_against_a_publication_matches_nothing(lane) -> None:
    """CT-4: a publication changes active/latest; D3 for the old version modifies nothing."""

    lane["definitions_raw"].update_one(
        {"_id": ONBOARDING_WORKFLOW_ID}, {"$set": {"active_version": 1, "latest_version": 1}}
    )
    assert lane["definitions"].authorise_dispatch(ONBOARDING_WORKFLOW_ID, 0) is False
    raw = lane["definitions_raw"].find_one({"_id": ONBOARDING_WORKFLOW_ID})
    assert raw["dispatch_authorisation_seq"] == 0


def test_a_slipped_legacy_append_fails_d3_and_startup_verification(lane) -> None:
    raw = lane["definitions_raw"].find_one({"_id": ONBOARDING_WORKFLOW_ID})
    payload = dict(raw["payload"])
    payload["versions"] = [
        WorkflowVersion(version=1, stages=(), activated_at=NOW, activated_by="legacy")
        .model_dump(mode="json")
    ]
    lane["definitions_raw"].update_one(
        {"_id": ONBOARDING_WORKFLOW_ID}, {"$set": {"payload": payload}}
    )
    assert lane["definitions"].authorise_dispatch(ONBOARDING_WORKFLOW_ID, 0) is False
    assert lane["definitions"].verify_dispatch_state() == [
        (ONBOARDING_WORKFLOW_ID, "LAST_VERSION_NOT_LATEST")
    ]


def test_an_expired_lease_changes_nothing_no_nonce_revision_or_receipt(lane) -> None:
    """CT-20: the server-time lease condition fails the whole update atomically."""

    ledger: MongoFenceLedger = lane["store"].fence_ledger()
    entry = lane["entry"]
    sid = entry.submission_input.submission_id
    snapshot = lane["store"].get(entry.submission_input.case_id)
    assert ledger.claim(
        case_id=snapshot.case_id, revision=snapshot.revision, nonce=snapshot.write_nonce,
        submission_id=sid, token="1" * 32, version=0,
    ) is not None
    # Move the lease into the past directly (a stalled worker).
    lane["cases"].update_one(
        {"_id": str(snapshot.case_id)},
        {"$set": {"target_executions.0.workflow_dispatch.lease_until":
                  datetime.now(UTC) - timedelta(seconds=1)}},
    )
    before = _raw(lane)
    current = lane["store"].get(snapshot.case_id)
    for step in (
        lambda: ledger.authorise(
            case_id=current.case_id, revision=current.revision, nonce=current.write_nonce,
            submission_id=sid, token="1" * 32, version=0,
        ),
        lambda: ledger.first_write(
            case_id=current.case_id, revision=current.revision, nonce=current.write_nonce,
            submission_id=sid, token="1" * 32, operation=SHELL,
        ),
    ):
        assert step() is None
        assert _raw(lane) == before


def test_a_revision_reused_in_another_history_cannot_claim(lane) -> None:
    """CT-17: a matching revision with another nonce fails on the nonce."""

    ledger: MongoFenceLedger = lane["store"].fence_ledger()
    entry = lane["entry"]
    snapshot = lane["store"].get(entry.submission_input.case_id)
    lane["cases"].update_one({"_id": str(snapshot.case_id)}, {"$set": {"write_nonce": "9" * 32}})
    before = _raw(lane)
    assert ledger.claim(
        case_id=snapshot.case_id, revision=snapshot.revision, nonce=snapshot.write_nonce,
        submission_id=entry.submission_input.submission_id, token="1" * 32, version=0,
    ) is None
    assert _raw(lane) == before


def test_an_ambiguous_durable_write_stops_before_d6(lane) -> None:
    """CT-16/CT-20: an unsatisfiable write concern (w:2 on a standalone) is ambiguous."""

    entry = lane["entry"]
    ledger = lane["store"].fence_ledger()
    ledger._collection = lane["cases"].with_options(  # noqa: SLF001
        write_concern=WriteConcern(w=2, j=True, wtimeout=300)
    )
    snapshot = lane["store"].get(entry.submission_input.case_id)
    with pytest.raises(PersistenceOutcomeAmbiguousError):
        ledger.claim(
            case_id=snapshot.case_id, revision=snapshot.revision, nonce=snapshot.write_nonce,
            submission_id=entry.submission_input.submission_id, token="1" * 32, version=0,
        )
    lane["store"].fence_ledger = lambda: ledger  # type: ignore[method-assign]
    with pytest.raises(DispatchFenceRefusedError) as refused:
        _authorise(lane)
    assert refused.value.code == CHECK_UNAVAILABLE
    assert "SHELL" not in _element(_raw(lane))["attempted_operations"]


def test_ledger_replace_asserts_the_read_predicate_in_its_filter(lane) -> None:
    """Same-snapshot correction: a stale caller predicate never overwrites."""

    entry = lane["entry"]
    with pytest.raises(TargetExecutionRepositoryConflictError):
        lane["ledger"].replace(
            entry.model_copy(update={"shell_status": "X"}),
            expected_state=GoldTierExecutionLedgerState.IN_PROGRESS.value,
            expected_attempted=(),
        )
    lane["ledger"].replace(
        entry.model_copy(update={"shell_status": "PENDING"}),
        expected_state=GoldTierExecutionLedgerState.IN_PROGRESS.value,
        expected_attempted=entry.attempted_operations,
    )
    assert _element(_raw(lane))["shell_status"] == "PENDING"


def test_startup_clears_unattempted_claims_and_keeps_marked_ones(lane) -> None:
    """CT-5: a crash between D2 and D5 leaves a claim; the next start clears it."""

    entry = lane["entry"]
    sid = entry.submission_input.submission_id
    assert lane["ledger"].fence_claim(sid, token="1" * 32, version=0) is not None
    restarted = MongoCaseStore(lane["client"], database=lane["database"], collection=CASES)
    restarted.initialize()
    assert "workflow_dispatch" not in _element(_raw(lane))
    written = _authorise(lane)
    assert written.workflow_dispatch is not None
    restarted.initialize()
    assert _element(_raw(lane))["workflow_dispatch"]["first_write"]["operation"] == "SHELL"


def test_the_probe_accepts_the_pinned_standalone(lane) -> None:
    assert lane["store"].probe_durability() == (True, None)


def test_two_processes_record_exactly_one_first_write(lane) -> None:
    """CT-17 multi-process: competing workers, one durable first write."""

    entry = lane["entry"]
    env = dict(os.environ)
    root = BACKEND.parents[1]
    env["PYTHONPATH"] = os.pathsep.join([str(BACKEND), str(root)])
    env["ADR017_WORKER_URI"] = MONGO_URI or ""
    go_at = time.time() + 3.0
    workers = [
        subprocess.Popen(
            [sys.executable, str(BACKEND / "tests" / "adr017_fence_worker.py"),
             "ADR017_WORKER_URI", lane["database"], str(entry.submission_input.case_id),
             str(entry.submission_input.submission_id), str(go_at)],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        for _ in range(4)
    ]
    results = []
    for worker in workers:
        out, _err = worker.communicate(timeout=120)
        results.append(json.loads(out.strip().splitlines()[-1]))
    assert sorted(item["result"] for item in results).count("WRITTEN") == 1, results
    element = _element(_raw(lane))
    assert element["attempted_operations"].count("SHELL") == 1
    assert element["workflow_dispatch"]["state"] == WorkflowDispatchState.AUTHORISED.value


def test_the_backfill_is_dry_run_first_idempotent_and_verified(lane) -> None:
    raw = lane["definitions_raw"]
    raw.delete_many({})
    legacy = WorkflowDefinition(
        workflow_id="refresh", name="Refresh", use_case="Refresh", country="Singapore",
        versions=tuple(
            WorkflowVersion(version=n, stages=(), activated_at=NOW, activated_by="d")
            for n in (1, 2)
        ),
        created_at=NOW, updated_at=NOW,
    )
    raw.insert_one({"_id": "refresh", "revision": 1, "payload": legacy.model_dump(mode="json")})
    plan = plan_backfill(raw)
    assert [(c[0], c[3]) for c in plan.changes] == [("refresh", 2)]
    assert raw.find_one({"_id": "refresh"}).get("latest_version") is None  # dry run wrote nothing
    assert apply_backfill(plan, raw) == 1
    stored = raw.find_one({"_id": "refresh"})
    assert (stored["active_version"], stored["latest_version"], stored["revision"]) == (2, 2, 1)
    assert verify_definitions(raw.find({})) == []
    again = plan_backfill(raw)
    assert again.changes == [] and again.already_backfilled == 1
    raw.update_one({"_id": "refresh"}, {"$set": {"latest_version": 5}})
    refused = plan_backfill(raw)
    assert [item.reason for item in refused.refusals] == ["LAST_VERSION_NOT_LATEST"]
    with pytest.raises(BackfillRefusedError):
        apply_backfill(refused, raw)


def test_an_ambiguous_startup_clearing_never_stops_the_backend(lane, monkeypatch) -> None:
    """QG R0 P3-3: the store still starts; the fence reports itself unavailable."""

    entry = lane["entry"]
    assert lane["ledger"].fence_claim(
        entry.submission_input.submission_id, token="1" * 32, version=0
    ) is not None

    def ambiguous(self, **_kwargs):
        raise PersistenceOutcomeAmbiguousError

    monkeypatch.setattr(MongoFenceLedger, "clear_unattempted_claim", ambiguous)
    restarted = MongoCaseStore(lane["client"], database=lane["database"], collection=CASES)
    restarted.initialize()  # does not raise
    assert restarted.probe_durability() == (False, "STARTUP_CLAIM_CLEARING_INCOMPLETE")
    assert "workflow_dispatch" in _element(_raw(lane))  # nothing was guessed away
