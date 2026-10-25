"""Opt-in physical Session 2 Mongo restart, creator CAS and bound-evidence proof."""

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier
from typing import Any
from uuid import UUID, uuid4

import pytest
from pymongo import MongoClient
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
    require_ephemeral_mongo_database,
)
from test_s2_ownership_intelligence import Cases
from test_s2_persistence_security import (
    legacy_document_raw,
    session2_snapshot,
    supplemental_snapshot,
)
from test_slice_a_legacy_compatibility import historical_raw

from app.config import Settings
from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider
from app.domain.ownership import OwnershipAnalysisRecord, OwnershipAnalysisState
from app.persistence.errors import PersistenceConflictError, PersistenceDataInvalidError
from app.persistence.models import DurableCaseSnapshot
from app.persistence.mongo_case_store import MongoCaseStore
from app.persistence.repositories import (
    MongoDocumentProcessingRepository,
    MongoOnboardingCaseRepository,
    MongoOwnershipAnalysisRepository,
)
from app.services.document_ownership import current_document_inputs
from app.services.document_processing import DocumentProcessingService
from app.services.ownership_analysis import _snapshot_prior_analysis
from app.services.ownership_repository import OwnershipRepositoryConflictError

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")


@pytest.fixture
def physical_database() -> Iterator[Settings]:
    assert MONGO_URI is not None
    database = require_ephemeral_mongo_database(generate_ephemeral_mongo_database("p12"))
    settings = Settings(
        _env_file=None, app_env="test", clm_persistence_mode="mongo", mongo_uri=MONGO_URI,
        mongo_database=database, mongo_case_collection="clm_case_snapshots",
    )
    cleanup_client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    try:
        yield settings
    finally:
        try:
            cleanup_ephemeral_mongo_database(cleanup_client, database)
            assert database not in cleanup_client.list_database_names()
        finally:
            cleanup_client.close()


def open_store(settings: Settings) -> MongoCaseStore:
    assert MONGO_URI is not None
    require_ephemeral_mongo_database(settings.mongo_database)
    store = MongoCaseStore(
        MongoClient(MONGO_URI), database=settings.mongo_database,
        collection=settings.mongo_case_collection,
    )
    store.initialize()
    return store


def test_duplicate_table_originals_survive_physical_restart_with_exact_bindings(
    physical_database: Settings,
) -> None:
    original = supplemental_snapshot()
    first = open_store(physical_database)
    text = (
        "Shareholder | Type | Shares | Share count\n"
        "SYNTHETIC OWNER | NATURAL_PERSON | 250 | 300"
    )
    try:
        first.create(original)
        service = DocumentProcessingService(
            cases=Cases(original.onboarding), idp=LocalPdfTextIdpProvider(),
            repository=MongoDocumentProcessingRepository(first),
            max_upload_bytes=5 * 1024 * 1024, review_confidence_threshold=0.85,
        )
        record = service.create_document(
            case_id=original.case_id, display_name="duplicate-table.txt",
            content_type="text/plain", content=text.encode(),
        )
        expected_observations, expected_bindings = current_document_inputs((record,))
        assert {str(item.share_count) for item in expected_observations} == {"250", "300"}
        assert len({item.observation_id for item in expected_observations}) == 2
    finally:
        first.close()
    second = open_store(physical_database)
    try:
        restored = second.get(original.case_id)
        assert restored is not None and restored.documents == (record,)
        observations, bindings = current_document_inputs(restored.documents)
        assert observations == expected_observations and bindings == expected_bindings
        assert all(
            item.document_id == record.document_id and item.document_version == 1
            and item.page_number == 1 and item.extraction_quality == "AMBIGUOUS"
            and item.decision_state == "PROPOSED"
            for item in observations
        )
        assert restored.onboarding.created_by_actor_id == original.onboarding.created_by_actor_id
    finally:
        second.close()


@pytest.mark.parametrize("fixture", [session2_snapshot, supplemental_snapshot])
def test_schema9_restarts_preserve_creator_pages_proposals_receipts_and_supplement(
    physical_database: Settings, fixture,
) -> None:
    original = fixture()
    first = open_store(physical_database)
    try:
        first.create(original)
        raw = first._collection.find_one({"_id": str(original.case_id)})  # noqa: SLF001
        assert raw is not None and raw["schema_version"] == 15
    finally:
        first.close()
    second = open_store(physical_database)
    try:
        restored = second.get(original.case_id)
        assert restored == original
        assert restored.onboarding.created_by_actor_id == "maya-lim"
        if restored.documents:
            document = restored.documents[0]
            assert document.document_version == 1
            assert document.pages[0].page_number == 2
            assert document.pages[0].raw_ocr_mean_confidence == 94
            assert restored.ownership.document_observations == document.ownership_observations
            assert document.ownership_observations[0].decision_state == "PROPOSED"
            assert restored.ownership.document_discrepancies[0].verification_state == "REVIEWED"
            assert restored.ownership.prior_analyses[-1].manual_review_receipt is not None
        else:
            assert restored.ownership.supplemental_parties == (
                original.ownership.supplemental_parties
            )
            assert restored.ownership.supplemental_relationships == (
                original.ownership.supplemental_relationships
            )
            assert restored.ownership.supplemental_evidence == (
                original.ownership.supplemental_evidence
            )
            assert restored.onboarding.registry_acquisition.relationships == ()
    finally:
        second.close()


@pytest.mark.parametrize("note", [None, "Historical reviewer note remains unchanged."])
def test_optional_and_historical_notes_survive_physical_restart_without_read_rewrite(
    physical_database: Settings, note,
) -> None:
    original = session2_snapshot()
    receipt = original.ownership.manual_review_receipt.model_copy(update={"rationale": note})
    original = original.model_copy(update={
        "ownership": original.ownership.model_copy(update={"manual_review_receipt": receipt})
    })
    first = open_store(physical_database)
    try:
        first.create(original)
        raw_before = first._collection.find_one({"_id": str(original.case_id)})
    finally:
        first.close()
    second = open_store(physical_database)
    try:
        restored = second.get(original.case_id)
        assert restored.ownership.manual_review_receipt.rationale == note
        assert restored == original
        raw_after = second._collection.find_one({"_id": str(original.case_id)})
        assert raw_after == raw_before
    finally:
        second.close()


@pytest.mark.parametrize("version", range(1, 9))
def test_exact_v1_to_v8_physical_reads_keep_unknown_creator_without_rewrite(
    physical_database: Settings, version: int,
) -> None:
    raw = historical_raw(version)
    document = legacy_document_raw()
    document["case_id"] = raw["case_id"]
    for event in document["events"]:
        event["case_id"] = raw["case_id"]
    raw["documents"] = [document]
    first = open_store(physical_database)
    case_id = UUID(raw["case_id"])
    try:
        first._collection.insert_one(deepcopy(raw))  # noqa: SLF001
    finally:
        first.close()
    second = open_store(physical_database)
    try:
        decoded = second.get(case_id)
        assert decoded.schema_version == 15
        assert decoded.onboarding.created_by_actor_id is None
        assert decoded.documents[0].document_version is None
        assert decoded.documents[0].fields[0].extraction_method == "UNKNOWN"
        assert decoded.documents[0].pages == ()
        assert decoded.documents[0].ownership_observations == ()
        assert second._collection.find_one({"_id": str(case_id)}) == raw  # noqa: SLF001
        corrupt = deepcopy(raw)
        corrupt["onboarding"]["created_by_actor_id"] = None
        second._collection.replace_one({"_id": str(case_id)}, corrupt)  # noqa: SLF001
        with pytest.raises(PersistenceDataInvalidError):
            second.get(case_id)
        assert second._collection.find_one({"_id": str(case_id)}) == corrupt  # noqa: SLF001
    finally:
        second.close()


@pytest.mark.parametrize("path", ["repository", "store"])
def test_physical_creator_identity_is_immutable_through_adapter_and_envelope_cas(
    physical_database: Settings, path: str,
) -> None:
    store = open_store(physical_database)
    # A receipt-free source reaches the creator CAS itself; a retained receipt
    # would independently reject a forged creator during envelope validation.
    original = supplemental_snapshot()
    try:
        store.create(original)
        changed_case = original.onboarding.model_copy(update={"created_by_actor_id": "olivia-koh"})
        with pytest.raises(PersistenceConflictError):
            if path == "repository":
                MongoOnboardingCaseRepository(store).save(changed_case)
            else:
                store.replace(original.model_copy(update={"onboarding": changed_case}),
                              expected_revision=original.revision)
        assert store.get(original.case_id) == original
    finally:
        store.close()


def document_replacement(
    store: MongoCaseStore,
) -> tuple[DurableCaseSnapshot, OwnershipAnalysisRecord]:
    original = session2_snapshot()
    store.create(original)
    document = original.documents[0]
    changed = document.model_copy(update={"events": [
        *document.events, document.events[-1].model_copy(update={"sequence": 2}),
    ]})
    MongoDocumentProcessingRepository(store).save(changed)
    observations, bindings = current_document_inputs((changed,))
    previous = original.ownership
    replacement = OwnershipAnalysisRecord(
        case_id=original.case_id, version=previous.version,
        analysis_id=uuid4(), correlation_id=uuid4(), state=OwnershipAnalysisState.LOADING,
        identity_registration_number=previous.identity_registration_number,
        identity_correction_version=previous.identity_correction_version,
        threshold_percent=previous.threshold_percent,
        document_observations=observations, document_bindings=bindings,
        prior_analyses=(*previous.prior_analyses, _snapshot_prior_analysis(previous)),
        created_at=previous.created_at, updated_at=previous.updated_at,
    )
    return original, replacement


def test_two_physical_adapters_have_one_document_bound_cas_winner(
    physical_database: Settings,
) -> None:
    first = open_store(physical_database)
    second = open_store(physical_database)
    try:
        original, replacement = document_replacement(first)
        barrier = Barrier(2)

        def replace(store: MongoCaseStore) -> str:
            barrier.wait(timeout=10)
            try:
                MongoOwnershipAnalysisRepository(store).replace_document_bound(
                    replacement, expected_version=original.ownership.version,
                )
            except OwnershipRepositoryConflictError:
                return "CONFLICT"
            return "PERSISTED"

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(replace, (first, second)))
        assert sorted(outcomes) == ["CONFLICT", "PERSISTED"]
        saved = first.get(original.case_id)
        assert saved.ownership.version == original.ownership.version + 1
        assert saved.ownership.analysis_id == replacement.analysis_id
        assert saved.ownership.document_bindings[0].event_count == 2
        assert saved.documents[0].document_version == 1
        assert saved.ownership.prior_analyses[-1].manual_review_receipt == (
            original.ownership.manual_review_receipt
        )
        with pytest.raises(OwnershipRepositoryConflictError):
            MongoOwnershipAnalysisRepository(second).replace_document_bound(
                replacement, expected_version=original.ownership.version,
            )
    finally:
        first.close()
        second.close()


@pytest.mark.parametrize("corruption", [
    "stale_document", "foreign_document", "changed_original", "wrong_identity",
])
def test_document_bound_replacement_rejects_stale_or_forged_source_evidence(
    physical_database: Settings, corruption: str,
) -> None:
    store = open_store(physical_database)
    try:
        original, replacement = document_replacement(store)
        before = store.get(original.case_id)
        if corruption == "stale_document":
            document = before.documents[0]
            document = document.model_copy(update={"events": [
                *document.events, document.events[-1].model_copy(update={"sequence": 3}),
            ]})
            MongoDocumentProcessingRepository(store).save(document)
            before = store.get(original.case_id)
        elif corruption == "foreign_document":
            replacement = replacement.model_copy(update={"document_observations": (
                replacement.document_observations[0].model_copy(update={"document_id": uuid4()}),
            )})
        elif corruption == "changed_original":
            replacement = replacement.model_copy(update={"document_observations": (
                replacement.document_observations[0].model_copy(
                    update={"explicit_percentage": "71"}
                ),
            )})
        else:
            replacement = replacement.model_copy(
                update={"identity_registration_number": "202400001A"}
            )
        with pytest.raises(OwnershipRepositoryConflictError):
            MongoOwnershipAnalysisRepository(store).replace_document_bound(
                replacement, expected_version=original.ownership.version,
            )
        assert store.get(original.case_id) == before
    finally:
        store.close()


def test_deleted_case_cannot_be_resurrected_by_new_creator_or_document_bound_adapter(
    physical_database: Settings,
) -> None:
    store = open_store(physical_database)
    other = open_store(physical_database)
    try:
        original, replacement = document_replacement(store)
        retained = store.get(original.case_id)
        store.delete(original.case_id, expected_revision=retained.revision)
        with pytest.raises(PersistenceConflictError):
            MongoOnboardingCaseRepository(other).save(original.onboarding)
        with pytest.raises(PersistenceConflictError):
            MongoDocumentProcessingRepository(other).save(original.documents[0])
        with pytest.raises(OwnershipRepositoryConflictError):
            MongoOwnershipAnalysisRepository(other).replace_document_bound(
                replacement, expected_version=original.ownership.version,
            )
        with pytest.raises(PersistenceConflictError):
            other.replace(retained, expected_revision=retained.revision)
        assert store.get(original.case_id) is None
        assert other.get(original.case_id) is None
        assert store._collection.count_documents({"_id": str(original.case_id)}) == 0  # noqa: SLF001
    finally:
        store.close()
        other.close()

def test_physical_read_adapters_transfer_fresh_independent_models(
    physical_database: Settings,
) -> None:
    from test_performance_mongo_read_ownership import (
        READ_NAMES,
        mutable_ids,
        populated_snapshot,
        read,
    )

    original = populated_snapshot()
    first = open_store(physical_database)
    second = None
    try:
        first.create(original)
        expected = first.get(original.case_id)
        assert expected is not None
        second = open_store(physical_database)
        for name in READ_NAMES:
            caller, later = read(first, original, name), read(second, original, name)
            assert caller is not None and caller == later
            assert mutable_ids(caller).isdisjoint(mutable_ids(later))
        case = MongoOnboardingCaseRepository(first).get(original.case_id)
        document = MongoDocumentProcessingRepository(first).get(
            original.documents[0].document_id
        )
        assert case is not None and document is not None
        case.events.clear()
        document.fields.clear()
        assert first.get(original.case_id) == second.get(original.case_id) == expected
    finally:
        first.close()
        if second is not None:
            second.close()


def test_deleted_case_cannot_be_recreated_from_caller_owned_read(
    physical_database: Settings,
) -> None:
    from test_performance_mongo_read_ownership import populated_snapshot

    original = populated_snapshot()
    store = open_store(physical_database)
    try:
        store.create(original)
        repository = MongoOnboardingCaseRepository(store)
        caller = repository.get(original.case_id)
        assert caller is not None
        store.delete(original.case_id, expected_revision=original.revision)
        with pytest.raises(PersistenceConflictError):
            repository.save(caller)
        assert store.get(original.case_id) is None
        assert repository.get(original.case_id) is None
    finally:
        store.close()
