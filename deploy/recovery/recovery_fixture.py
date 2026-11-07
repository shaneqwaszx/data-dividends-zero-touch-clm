"""Synthetic fixture driven by the baseline application persistence model."""

import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.persistence.mongo_case_store import MongoCaseStore
from bson import json_util
from pymongo import MongoClient


def seed(store):
    from app.composition import (
        build_clm_orchestration_service,
        build_document_processing_service,
        build_onboarding_service,
        build_ownership_analysis_service,
    )
    from app.config import Settings
    from app.domain.clm import (
        ClmSubmissionSnapshot,
        EvidenceReference,
        GoldTierSubmissionPlan,
        ProvisionalUboSummary,
    )
    from app.domain.target_submission import (
        GoldTierExecutionLedgerEntry,
        GoldTierExecutionLedgerState,
        GoldTierProviderMode,
    )
    from app.persistence.models import DurableCaseSnapshot

    settings = Settings(_env_file=None)
    onboarding = build_onboarding_service(settings=settings)
    documents = build_document_processing_service(onboarding, settings)
    ownership = build_ownership_analysis_service(onboarding, settings)
    record = build_clm_orchestration_service(onboarding, documents, ownership).create_case(
        "202400001A"
    )
    case = onboarding.get_case(record.case_id)
    mode = GoldTierProviderMode.MOCK
    target = onboarding.build_submission_input(case, provider_mode=mode)
    now = datetime.now(UTC)
    bound = record.model_copy(update={
        "submission_plan": GoldTierSubmissionPlan(environment=mode, provider_classification="MOCK"),
        "submission_snapshot": ClmSubmissionSnapshot(
            snapshot_id=uuid4(), target_input=target, document_references=(),
            ownership_reference=EvidenceReference(
                reference_id=uuid4(), version=1, status="ANALYZED", updated_at=now,
            ),
            provisional_ubo=ProvisionalUboSummary(candidate_count=0), created_at=now,
        ),
    })
    store.initialize()
    store.create(DurableCaseSnapshot(
        case_id=case.case_id, revision=1, onboarding=case, clm=bound,
        target_executions=(GoldTierExecutionLedgerEntry(
            submission_input=target, state=GoldTierExecutionLedgerState.NOT_STARTED,
        ),),
        created_at=now, updated_at=now,
    ))


def bson_precision(snapshot):
    updated = snapshot.updated_at
    return snapshot.model_copy(update={
        "updated_at": updated.replace(microsecond=updated.microsecond // 1000 * 1000),
    })


def check_cas(collection, store, raw, snapshot, *, regression):
    store.initialize()
    if collection.find_one() != raw:
        raise RuntimeError("Backend repository startup rewrote restored data")
    candidate = snapshot.model_copy(update={"revision": 2})
    persisted = store.replace(candidate, expected_revision=1)
    readback = store.get(snapshot.case_id)
    stored = collection.find_one({"_id": raw["_id"]})
    if persisted != candidate.model_copy(update={"updated_at": persisted.updated_at}):
        raise RuntimeError("Repository changed fields beyond the intended revision and timestamp")
    if readback is None or bson_precision(readback) != bson_precision(persisted):
        raise RuntimeError("Backend CAS readback differs from the persisted result")
    if stored is None or stored != (raw | {"revision": 2, "updated_at": stored["updated_at"]}):
        raise RuntimeError("CAS changed or removed a raw schema-20 field")
    if regression and readback == candidate:
        raise RuntimeError("Regression fixture did not reproduce the pre-write false negative")
    return {"revision": readback.revision, "pre_write_comparison_rejected": readback != candidate}


def inspect(database, store, action):
    names = sorted(database.list_collection_names())
    collection = database["clm_case_snapshots"]
    if names != ["clm_case_snapshots"] or collection.count_documents({}) != 1:
        raise RuntimeError("Unexpected synthetic database inventory")
    raw = collection.find_one()
    case_id = UUID(raw["_id"])
    snapshot = store.get(case_id)
    if raw["schema_version"] != 20 or snapshot.schema_version != 20:
        raise RuntimeError("Schema 20 required")
    if snapshot.revision != 1 or not snapshot.onboarding.events:
        raise RuntimeError("Missing expected revision or workflow audit events")
    if len(snapshot.target_executions) != 1 or snapshot.target_executions[0].state != "NOT_STARTED":
        raise RuntimeError("Expected one synthetic NOT_STARTED ledger entry")
    indexes = sorted(collection.list_indexes(), key=lambda index: index["name"])
    required_indexes = {
        "_id_", "case_id_unique", "automation_status_updated_at", "target_submission_lookup",
        "document_id_lookup", "onboarding_team_lookup",
    }
    if {index["name"] for index in indexes} != required_indexes:
        raise RuntimeError("Missing expected case indexes")
    cas = None
    if action in {"qualify", "regression"}:
        cas = check_cas(collection, store, raw, snapshot, regression=action == "regression")
    canonical = json_util.dumps([raw, indexes], json_options=json_util.CANONICAL_JSON_OPTIONS)
    return {
        "summary": {
            "collections": names, "cases": 1, "indexes": len(indexes),
            "schema": 20, "revision": 1, "audit_events": len(snapshot.onboarding.events),
            "target_ledger_state": "NOT_STARTED",
        },
        "content_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "cas": cas,
    }


mongo, database, action = sys.argv[1:]
if not re.fullmatch(r"clm_recovery_[0-9a-f]{32}", database):
    raise RuntimeError("Disposable database required")
if mongo not in {f"{database}-source", f"{database}-restore"}:
    raise RuntimeError("Disposable Mongo host required")
with MongoClient(host=mongo, serverSelectionTimeoutMS=5000, tz_aware=True) as client:
    store = MongoCaseStore(client, database=database, collection="clm_case_snapshots")
    if action == "seed":
        seed(store)
    print(json.dumps(inspect(client[database], store, action)))
