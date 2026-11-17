"""Physical Mongo evidence for immutable GoldTier provider identity."""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from pymongo import MongoClient
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)

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
from app.domain.ownership import OwnershipAnalysisRecord, OwnershipAnalysisState
from app.domain.ownership_evidence import OwnershipEvidence
from app.domain.registry_legal_form import RegistryLegalForm
from app.domain.target_submission import (
    GoldTierExecutionLedgerEntry,
    GoldTierExecutionLedgerState,
    GoldTierProviderMode,
)
from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.models import DurableCaseSnapshot
from app.persistence.mongo_case_store import MongoCaseStore
from app.persistence.repositories import (
    MongoOnboardingCaseRepository,
    MongoOwnershipAnalysisRepository,
)
from app.services.ownership_analysis import _snapshot_prior_analysis
from app.services.ownership_evidence_tagger import OwnershipEvidenceTagger
from app.services.ownership_repository import OwnershipRepositoryConflictError

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")
COLLECTION_NAME = "clm_case_snapshots"


@pytest.fixture
def isolated_provider_database() -> Iterator[str]:
    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p12")
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    assert database not in client.list_database_names()
    try:
        yield database
    finally:
        unexpected_collections = set(client[database].list_collection_names()) - {
            COLLECTION_NAME
        }
        cleanup_ephemeral_mongo_database(client, database)
        cleanup_succeeded = database not in client.list_database_names()
        client.close()
        assert not unexpected_collections
        assert cleanup_succeeded


def _open_store(database: str, *, initialize: bool = True) -> MongoCaseStore:
    assert MONGO_URI is not None
    store = MongoCaseStore(
        MongoClient(MONGO_URI),
        database=database,
        collection=COLLECTION_NAME,
    )
    if initialize:
        store.initialize()
    return store


def _provider_bound_snapshot(mode: GoldTierProviderMode) -> DurableCaseSnapshot:
    settings = Settings(_env_file=None)
    onboarding = build_onboarding_service(settings=settings)
    documents = build_document_processing_service(onboarding, settings)
    ownership = build_ownership_analysis_service(onboarding, settings)
    clm = build_clm_orchestration_service(onboarding, documents, ownership)
    record = clm.create_case("202400001A")
    case = onboarding.get_case(record.case_id)
    assert case is not None
    target_input = onboarding.build_submission_input(case, provider_mode=mode)
    now = datetime.now(UTC)
    submission_snapshot = ClmSubmissionSnapshot(
        snapshot_id=uuid4(),
        target_input=target_input,
        document_references=(),
        ownership_reference=EvidenceReference(
            reference_id=uuid4(),
            version=1,
            status="ANALYZED",
            updated_at=now,
        ),
        provisional_ubo=ProvisionalUboSummary(candidate_count=0),
        created_at=now,
    )
    provider_classification = "MOCK" if mode == GoldTierProviderMode.MOCK else "SANDBOX_PARTIAL"
    bound_record = record.model_copy(
        update={
            "submission_plan": GoldTierSubmissionPlan(
                environment=mode,
                provider_classification=provider_classification,
            ),
            "submission_snapshot": submission_snapshot,
        },
        deep=True,
    )
    return DurableCaseSnapshot(
        case_id=case.case_id,
        revision=1,
        onboarding=case,
        clm=bound_record,
        target_executions=(
            GoldTierExecutionLedgerEntry(
                submission_input=target_input,
                state=GoldTierExecutionLedgerState.NOT_STARTED,
            ),
        ),
        created_at=now,
        updated_at=now,
    )


def _insert_raw(database: str, raw: dict[str, Any]) -> None:
    assert MONGO_URI is not None
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    try:
        client[database][COLLECTION_NAME].insert_one(raw)
    finally:
        client.close()


def test_phase24_identity_replacement_is_bound_to_current_parent_and_survives_restart(
    isolated_provider_database: str,
) -> None:
    settings = Settings(_env_file=None)
    cases = build_onboarding_service(settings=settings)
    created = cases.create_case("202400001A")
    ownership = build_ownership_analysis_service(cases, settings)
    ownership.load(case_id=created.case_id)
    old = ownership.analyze(case_id=created.case_id)
    scalar = OwnershipEvidence(
        evidence_id="phase24-units", entity_identifier=created.requested_uen,
        party_id=old.root_party_id or "ROOT", kind="SHARE_UNITS",
        raw_value="6000", numeric_value="6000", source_operation="SYNTHETIC",
        provider="SYNTHETIC", environment="MOCK", retrieved_at=datetime.now(UTC),
        evidence_version=1,
    )
    old = old.model_copy(update={
        "evidence": (scalar,), "legal_form": RegistryLegalForm.COMPANY,
        "tagging": OwnershipEvidenceTagger().tag((scalar,), case_version=len(created.events)),
    }, deep=True)
    cases.repair_initial_identity_and_recheck(
        case_id=created.case_id, actor_id="phase24-operator",
        legal_name="Synthetic", registration_number="202400009I",
        country_of_incorporation="SG", expected_case_event_count=len(created.events),
        verify_registry=True,
    )
    corrected = cases.get_case(created.case_id)
    assert corrected is not None
    now = datetime.now(UTC)
    store = _open_store(isolated_provider_database)
    try:
        store.create(DurableCaseSnapshot(
            case_id=created.case_id, revision=0, onboarding=corrected,
            ownership=old, created_at=now, updated_at=now,
        ))
        repository = MongoOwnershipAnalysisRepository(store)
        replacement = OwnershipAnalysisRecord(
            case_id=created.case_id, analysis_id=uuid4(), correlation_id=uuid4(),
            identity_registration_number="202400002B", state=OwnershipAnalysisState.LOADING,
            identity_correction_version=len(corrected.identity_corrections),
            version=old.version, prior_analyses=(_snapshot_prior_analysis(old),),
            poc_interest_ledger=old.poc_interest_ledger,
            threshold_percent=old.threshold_percent, created_at=now, updated_at=now,
        )
        with pytest.raises(OwnershipRepositoryConflictError):
            repository.replace_identity_bound(replacement, expected_version=old.version)
        replacement = replacement.model_copy(
            update={"identity_registration_number": corrected.requested_uen}, deep=True
        )
        saved = repository.replace_identity_bound(replacement, expected_version=old.version)
        with pytest.raises(OwnershipRepositoryConflictError):
            repository.replace_identity_bound(replacement, expected_version=old.version)
        # A continuation from this generation cannot overwrite a same-UEN reverify.
        cases.repair_initial_identity_and_recheck(
            case_id=created.case_id, actor_id="phase24-operator",
            legal_name="Synthetic", registration_number=corrected.requested_uen,
            country_of_incorporation="SG", expected_case_event_count=len(corrected.events),
            verify_registry=True,
        )
        rebound = cases.get_case(created.case_id)
        assert rebound is not None
        current_snapshot = store.get(created.case_id)
        assert current_snapshot is not None
        store.replace(
            current_snapshot.model_copy(update={"onboarding": rebound}, deep=True),
            expected_revision=current_snapshot.revision,
            expected_nonce=current_snapshot.write_nonce,
        )
        with pytest.raises(OwnershipRepositoryConflictError):
            repository.save(saved, expected_version=saved.version)
    finally:
        store.close()
    restarted = _open_store(isolated_provider_database)
    try:
        restored = MongoOwnershipAnalysisRepository(restarted).get_for_case(created.case_id)
        assert restored == saved
        assert restored.prior_analyses[-1].analysis_id == old.analysis_id
        assert restored.prior_analyses[-1].evidence == (scalar,)
        assert restored.prior_analyses[-1].tagging == old.tagging
        assert restored.prior_analyses[-1].legal_form == RegistryLegalForm.COMPANY
    finally:
        restarted.close()


def test_phase24_history_exhaustion_and_invalid_candidate_preserve_physical_readability(
    isolated_provider_database: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pydantic import ValidationError

    store = _open_store(isolated_provider_database)
    try:
        repository = MongoOnboardingCaseRepository(store)
        cases = build_onboarding_service(settings=Settings(_env_file=None), repository=repository)
        case = cases.create_case("202400001A")
        for _ in range(16):
            case = cases.repair_initial_identity_and_recheck(
                case_id=case.case_id, actor_id="phase24-operator", legal_name="Synthetic",
                registration_number="202400001A", country_of_incorporation="SG",
                expected_case_event_count=len(case.events), verify_registry=True,
            )
        before = store.get(case.case_id)
        assert before is not None

        def forbidden(*args: object, **kwargs: object) -> None:
            pytest.fail("history exhaustion must precede provider calls")

        monkeypatch.setattr(cases, "_verify_registry_correction", forbidden)
        monkeypatch.setattr(cases, "_run_initial_identity_search", forbidden)
        with pytest.raises(ValueError, match="history is full"):
            cases.repair_initial_identity_and_recheck(
                case_id=case.case_id, actor_id="phase24-operator", legal_name="Synthetic",
                registration_number="202400001A", country_of_incorporation="SG",
                expected_case_event_count=len(case.events), verify_registry=True,
            )
        invalid = case.model_copy(update={
            "identity_corrections": (*case.identity_corrections, case.identity_corrections[-1])
        }, deep=True)
        with pytest.raises(ValidationError):
            repository.save(invalid)
        with pytest.raises(PersistenceDataInvalidError):
            store.replace(before.model_copy(update={"onboarding": invalid}, deep=True),
                          expected_revision=before.revision, expected_nonce=before.write_nonce)
        assert store.get(case.case_id) == before
    finally:
        store.close()
    restarted = _open_store(isolated_provider_database)
    try:
        assert restarted.get(case.case_id) == before
        assert len(before.onboarding.identity_corrections) == 16
        assert len(before.onboarding.initial_target_search_attempts) == 16
    finally:
        restarted.close()


@pytest.mark.parametrize("registry_derived", [False, True])
def test_phase24_loaded_same_uen_continuation_obeys_source_currentness(
    isolated_provider_database: str, registry_derived: bool,
) -> None:
    from app.connectors.mock_ownership import MockOwnershipProvider
    from app.services.ownership_errors import OwnershipRequestError

    settings = Settings(_env_file=None)
    store = _open_store(isolated_provider_database)
    try:
        cases = build_onboarding_service(
            settings=settings, repository=MongoOnboardingCaseRepository(store)
        )
        case = cases.create_case("202400001A")
        ownership = build_ownership_analysis_service(
            cases, settings, repository=MongoOwnershipAnalysisRepository(store)
        )
        loaded = ownership.load(case_id=case.case_id,
                                provider=None if registry_derived else MockOwnershipProvider())
        assert loaded.state == "LOADED" and loaded.identity_correction_version == 0
        cases.repair_initial_identity_and_recheck(
            case_id=case.case_id, actor_id="phase24-operator", legal_name="Synthetic",
            registration_number="202400001A", country_of_incorporation="SG",
            expected_case_event_count=len(case.events), verify_registry=True,
        )
        before = store.get(case.case_id)
        if registry_derived:
            assert ownership.get(case_id=case.case_id) is None
            with pytest.raises(OwnershipRequestError) as rejected:
                ownership.analyze(case_id=case.case_id)
            assert rejected.value.code == "OWNERSHIP_IDENTITY_STALE"
            with pytest.raises(OwnershipRepositoryConflictError):
                MongoOwnershipAnalysisRepository(store).save(
                    loaded.model_copy(update={"state": OwnershipAnalysisState.ANALYZING}),
                    expected_version=loaded.version,
                )
            assert store.get(case.case_id) == before
            retained = loaded
        else:
            retained = ownership.analyze(case_id=case.case_id)
            assert retained.state == "ANALYZED"
            assert retained.analysis_id == loaded.analysis_id
            assert retained.identity_correction_version == 0
    finally:
        store.close()
    restarted = _open_store(isolated_provider_database)
    try:
        restored = restarted.get(case.case_id)
        assert restored.ownership == retained
        assert len(restored.onboarding.identity_corrections) == 1
    finally:
        restarted.close()


def test_phase24_independent_roundtrip_replacement_survives_physical_restart(
    isolated_provider_database: str,
) -> None:
    from app.connectors.mock_ownership import MockOwnershipProvider

    settings = Settings(_env_file=None)
    cases = build_onboarding_service(settings=settings)
    case = cases.create_case("202400001A")
    ownership = build_ownership_analysis_service(cases, settings)
    ownership.load(case_id=case.case_id, provider=MockOwnershipProvider())
    old = ownership.analyze(case_id=case.case_id)
    assert old.provider_name not in {None, "ACRA_REGISTRY_ACQUISITION"}
    for uen in ("202400009I", "202400001A"):
        case = cases.repair_initial_identity_and_recheck(
            case_id=case.case_id, actor_id="phase24-operator", legal_name="Synthetic",
            registration_number=uen, country_of_incorporation="SG",
            expected_case_event_count=len(case.events), verify_registry=True,
        )
        assert ownership.get(case_id=case.case_id) is None
    now = datetime.now(UTC)
    store = _open_store(isolated_provider_database)
    try:
        store.create(DurableCaseSnapshot(case_id=case.case_id, revision=0,
                                        onboarding=case, ownership=old,
                                        created_at=now, updated_at=now))
        repository = MongoOwnershipAnalysisRepository(store)
        replacement = OwnershipAnalysisRecord(
            case_id=case.case_id, analysis_id=uuid4(), correlation_id=uuid4(),
            identity_registration_number=case.requested_uen, identity_correction_version=2,
            state=OwnershipAnalysisState.LOADING, version=old.version,
            prior_analyses=(_snapshot_prior_analysis(old),),
            poc_interest_ledger=old.poc_interest_ledger,
            threshold_percent=old.threshold_percent,
            created_at=now, updated_at=now,
        )
        saved = repository.replace_identity_bound(replacement, expected_version=old.version)
    finally:
        store.close()
    restarted = _open_store(isolated_provider_database)
    try:
        restored = MongoOwnershipAnalysisRepository(restarted).get_for_case(case.case_id)
        assert restored == saved
        assert restored.prior_analyses[-1].analysis_id == old.analysis_id
        assert restored.identity_correction_version == 2
    finally:
        restarted.close()


@pytest.mark.parametrize(
    "mode",
    [GoldTierProviderMode.MOCK, GoldTierProviderMode.SANDBOX],
)
def test_physical_restart_preserves_stable_provider_identity(
    isolated_provider_database: str,
    mode: GoldTierProviderMode,
) -> None:
    database = isolated_provider_database
    original = _provider_bound_snapshot(mode)
    store = _open_store(database)
    store.create(original)
    store.close()

    restarted = _open_store(database)
    try:
        restored = restarted.get(original.case_id)
        assert restored is not None and restored.clm is not None
        assert restored.clm.submission_snapshot is not None
        assert restored.clm.submission_plan.environment == mode
        assert restored.clm.submission_snapshot.target_input.provider_mode == mode
        assert restored.target_executions[0].submission_input.provider_mode == mode
    finally:
        restarted.close()


@pytest.mark.parametrize(
    ("plan_mode", "contradictory_mode"),
    [
        (GoldTierProviderMode.MOCK, GoldTierProviderMode.SANDBOX),
        (GoldTierProviderMode.SANDBOX, GoldTierProviderMode.MOCK),
    ],
)
def test_physical_restart_rejects_plan_input_contradiction(
    isolated_provider_database: str,
    plan_mode: GoldTierProviderMode,
    contradictory_mode: GoldTierProviderMode,
) -> None:
    snapshot = _provider_bound_snapshot(plan_mode)
    raw = snapshot.model_dump(mode="json")
    raw["_id"] = str(snapshot.case_id)
    raw["clm"]["submission_snapshot"]["target_input"]["provider_mode"] = (
        contradictory_mode.value
    )
    raw["target_executions"] = []
    _insert_raw(isolated_provider_database, raw)

    restarted = _open_store(isolated_provider_database, initialize=False)
    try:
        with pytest.raises(PersistenceDataInvalidError):
            restarted.get(snapshot.case_id)
        with pytest.raises(PersistenceDataInvalidError):
            restarted.initialize()
    finally:
        restarted.close()


def test_physical_restart_rejects_matching_ledger_provider_contradiction(
    isolated_provider_database: str,
) -> None:
    snapshot = _provider_bound_snapshot(GoldTierProviderMode.MOCK)
    raw = snapshot.model_dump(mode="json")
    raw["_id"] = str(snapshot.case_id)
    raw["target_executions"][0]["submission_input"]["provider_mode"] = "SANDBOX"
    _insert_raw(isolated_provider_database, raw)

    restarted = _open_store(isolated_provider_database, initialize=False)
    try:
        with pytest.raises(PersistenceDataInvalidError):
            restarted.get(snapshot.case_id)
        with pytest.raises(PersistenceDataInvalidError):
            restarted.initialize()
    finally:
        restarted.close()


def test_physical_restart_accepts_plan_without_submission(
    isolated_provider_database: str,
) -> None:
    snapshot = _provider_bound_snapshot(GoldTierProviderMode.SANDBOX)
    assert snapshot.clm is not None
    plan_only = snapshot.model_copy(
        update={
            "clm": snapshot.clm.model_copy(
                update={"submission_snapshot": None},
                deep=True,
            ),
            "target_executions": (),
        },
        deep=True,
    )
    store = _open_store(isolated_provider_database)
    store.create(plan_only)
    store.close()

    restarted = _open_store(isolated_provider_database)
    try:
        restored = restarted.get(plan_only.case_id)
        assert restored is not None and restored.clm is not None
        assert restored.clm.submission_plan.environment == GoldTierProviderMode.SANDBOX
        assert restored.clm.submission_snapshot is None
        assert restored.target_executions == ()
    finally:
        restarted.close()


def _phase24b_restart_services(store):
    """Reconstruct normal owners over a reopened disposable case envelope."""
    from test_zero_touch_orchestration import build_system

    from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
    from app.persistence.repositories import (
        MongoClmOrchestrationRepository,
        MongoDocumentProcessingRepository,
        MongoReconciliationRepository,
        MongoReconciliationUnitOfWork,
        MongoTargetExecutionRepository,
        MongoZeroTouchAutomationRepository,
    )
    from app.services.zero_touch_provider_bindings import DurableOwnershipProviderBindingResolver

    client, zero, _, target, _ = build_system(require_confirmation=True)
    zero._cases._repository = MongoOnboardingCaseRepository(store)
    zero._cases._target_executions = MongoTargetExecutionRepository(store)
    zero._documents._repository = MongoDocumentProcessingRepository(store)
    zero._ownership._repository = MongoOwnershipAnalysisRepository(store)
    zero._ownership._provider = RegistryAcquisitionOwnershipProvider(zero._cases)
    zero._clm._repository = MongoClmOrchestrationRepository(store)
    zero._repository = MongoZeroTouchAutomationRepository(store)
    zero._reconciliation._repository = MongoReconciliationRepository(store)
    zero._reconciliation._unit_of_work = MongoReconciliationUnitOfWork(store)
    zero._ownership_provider_bindings = DurableOwnershipProviderBindingResolver(
        lambda: zero._ownership.configured_provider,
    )
    return client, zero, target


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("boundary", ["clm", "reconciliation"])
def test_phase24b_interrupted_registry_retry_survives_physical_restart(
    isolated_provider_database, monkeypatch, legacy, boundary,
):
    from test_phase24b_interrupted_retry import (
        blocked_registry_case,
        interrupt_refresh,
        snapshot_of,
    )

    client, zero, _, _, registry, blocker, case_id = blocked_registry_case(durable=True)
    store = _open_store(isolated_provider_database)
    try:
        store.create(snapshot_of(zero, case_id))
    finally:
        store.close()
    # Run the interrupted write through physical owners, then close every store.
    store = _open_store(isolated_provider_database, initialize=False)
    try:
        physical_client, physical, target = _phase24b_restart_services(store)
        physical._cases._registry_router = zero._cases._registry_router
        interrupt_refresh(physical_client, physical, registry, blocker, monkeypatch,
                          case_id=case_id, boundary=boundary, legacy=legacy)
        assert target.calls == ["search"]
        interrupted_revision = store.get(case_id).revision
    finally:
        store.close()
    store = _open_store(isolated_provider_database, initialize=False)
    try:
        restarted_client, restarted, restarted_target = _phase24b_restart_services(store)
        assert restarted._ownership.get(case_id=case_id) is None
        response = restarted_client.post(f"/api/clm/zero-touch/cases/{case_id}/resume")
        assert response.status_code == 200
        ownership = restarted._ownership.get(case_id=case_id)
        assert ownership.state == "ANALYZED" and ownership.identity_correction_version == 1
        assert next(item for item in restarted.get(case_id=case_id).exceptions
                    if item.exception_id == blocker.exception_id).status == "CANCELLED"
        assert {item.blocker_code for item in restarted.get(case_id=case_id).active_exceptions} == {
            "TARGET_CONFIRMATION_REQUIRED",
        }
        assert restarted_target.calls == []
        assert store.get(case_id).revision > interrupted_revision
        recovered_revision = store.get(case_id).revision
    finally:
        store.close()
    # A second repository reopen cannot resurrect cancelled history or replay.
    store = _open_store(isolated_provider_database, initialize=False)
    try:
        final_client, final, final_target = _phase24b_restart_services(store)
        assert final_client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
        assert store.get(case_id).revision == recovered_revision
        assert final_target.calls == []
        assert next(item for item in final.get(case_id=case_id).exceptions
                    if item.exception_id == blocker.exception_id).status == "CANCELLED"
    finally:
        store.close()


@pytest.mark.parametrize("replacements, legacy, expected", [
    (4, False, "CANCELLED"), (5, False, "CANCELLED"), (10, False, "CANCELLED"),
    (5, True, "OPEN"),
])
def test_phase24b_generation_pruning_restart_uses_durable_binding(
    isolated_provider_database, monkeypatch, replacements, legacy, expected,
):
    from test_phase24_identity import correction
    from test_phase24b_interrupted_retry import (
        blocked_registry_case,
        interrupt_refresh,
        snapshot_of,
    )

    _, initial, _, _, registry, blocker, case_id = blocked_registry_case(durable=True)
    first = initial._ownership.get(case_id=case_id)
    store = _open_store(isolated_provider_database)
    try:
        store.create(snapshot_of(initial, case_id))
        client, physical, target = _phase24b_restart_services(store)
        physical._cases._registry_router = initial._cases._registry_router
        for generation in range(1, replacements + 1):
            interrupt_refresh(client, physical, registry, blocker, monkeypatch,
                              case_id=case_id, boundary="clm", legacy=legacy,
                              generation=generation)
            assert client.post(f"/api/onboarding/cases/{case_id}/ownership/load").status_code == 201
            response = client.post(f"/api/onboarding/cases/{case_id}/ownership/analyze")
            assert response.status_code == 200
        current = physical._ownership.get(case_id=case_id)
        assert current.state == "ANALYZED" and len(current.prior_analyses) == 4
        assert (first.analysis_id in {item.analysis_id for item in current.prior_analyses}) == (
            replacements == 4
        )
        assert target.calls == ["search"] * replacements
    finally:
        store.close()
    restarted = _open_store(isolated_provider_database, initialize=False)
    try:
        client, physical, target = _phase24b_restart_services(restarted)
        physical._cases._registry_router = initial._cases._registry_router
        response = client.post(f"/api/clm/zero-touch/cases/{case_id}/resume")
        assert response.status_code == 200
        assert next(item for item in physical.get(case_id=case_id).exceptions
                    if item.exception_id == blocker.exception_id).status == expected
        assert physical._ownership.get(case_id=case_id).state == "ANALYZED"
        assert target.calls == []
        if not legacy:
            response = correction(client, physical, physical.get(case_id=case_id),
                                  choice="ENTERED", uen="202400001A")
            assert response.status_code == 200
            assert physical._ownership.get(case_id=case_id).identity_correction_version == (
                replacements + 1
            )
            assert next(item for item in physical.get(case_id=case_id).exceptions
                        if item.exception_id == blocker.exception_id).status == "CANCELLED"
            assert target.calls == ["search"]
    finally:
        restarted.close()


@pytest.mark.parametrize(
    "raise_current, legacy_order", [(False, False), (True, False), (True, True)],
)
def test_stage_recovery_mixed_chronology_survives_physical_restart(
    isolated_provider_database, monkeypatch, raise_current, legacy_order,
):
    from test_phase24b_interrupted_retry import snapshot_of
    from test_phase24b_stage_recovery import mixed_case

    from app.domain.zero_touch import AutomationStage

    _, zero, _, stale, case_id = mixed_case(monkeypatch, raise_current=raise_current)
    snapshot = snapshot_of(zero, case_id)
    if legacy_order:
        from app.persistence.mongo_case_store import _persistence_value
        raw = _persistence_value(snapshot)
        raw["automation"]["stage_order_version"] = 1
        raw["automation"]["completed_stages"] = [
            stage for stage in raw["automation"]["completed_stages"] if stage != "GOLDTIER_SEARCH"
        ]
        snapshot = DurableCaseSnapshot.model_validate(raw)
    store = _open_store(isolated_provider_database)
    try:
        store.create(snapshot)
    finally:
        store.close()
    store = _open_store(isolated_provider_database, initialize=False)
    try:
        client, restarted, target = _phase24b_restart_services(store)
        assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
        current = restarted.get(case_id=case_id)
        assert current.current_stage == AutomationStage.OWNERSHIP
        assert next(item for item in current.exceptions
                    if item.exception_id == stale.exception_id).status == "CANCELLED"
        assert any(item.blocker_code == "TARGET_CONFIRMATION_REQUIRED"
                   for item in current.active_exceptions)
        assert restarted._ownership.get(case_id=case_id).state == "REVIEW_REQUIRED"
        revision = store.get(case_id).revision
        assert target.calls == []
    finally:
        store.close()
    store = _open_store(isolated_provider_database, initialize=False)
    try:
        client, final, target = _phase24b_restart_services(store)
        assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
        assert final.get(case_id=case_id) == current
        assert store.get(case_id).revision == revision
        assert target.calls == []
    finally:
        store.close()


@pytest.mark.parametrize("loaded", [False, True])
@pytest.mark.parametrize("available", [False, True])
def test_unfinished_stage_prerequisites_survive_physical_restart(
    isolated_provider_database, monkeypatch, loaded, available,
):
    from test_phase24b_stage_recovery_round1 import unfinished_mixed_case

    from app.domain.zero_touch import AutomationStage

    _, _, _, stale, case_id, snapshot = unfinished_mixed_case(
        monkeypatch, loaded=loaded, available=available,
    )
    retained = next(item for item in snapshot.automation.active_exceptions
                    if item.blocker_code == "TARGET_CONFIRMATION_REQUIRED")
    store = _open_store(isolated_provider_database)
    try:
        store.create(snapshot)
    finally:
        store.close()
    store = _open_store(isolated_provider_database, initialize=False)
    try:
        client, restarted, target = _phase24b_restart_services(store)
        assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
        current = restarted.get(case_id=case_id)
        expected = AutomationStage.READINESS if available else AutomationStage.OWNERSHIP
        assert current.current_stage == expected
        assert AutomationStage.DOCUMENT in current.completed_stages
        assert next(item for item in current.exceptions
                    if item.exception_id == stale.exception_id).status == "CANCELLED"
        assert next(item for item in current.active_exceptions
                    if item.exception_id == retained.exception_id) == retained
        ownership = restarted._ownership.get(case_id=case_id)
        assert ownership.state == ("ANALYZED" if available else "REVIEW_REQUIRED")
        assert ownership.identity_correction_version == 6
        revision = store.get(case_id).revision
        assert target.calls == []
    finally:
        store.close()
    store = _open_store(isolated_provider_database, initialize=False)
    try:
        client, final, target = _phase24b_restart_services(store)
        assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
        assert final.get(case_id=case_id) == current
        assert final._ownership.get(case_id=case_id) == ownership
        assert store.get(case_id).revision == revision
        assert target.calls == []
    finally:
        store.close()



def test_historical_v1_stale_only_stage_recovery_survives_physical_restart(
    isolated_provider_database, monkeypatch,
):
    from test_phase24b_generation_currentness import rebuilt_registry_generations
    from test_phase24b_interrupted_retry import snapshot_of

    from app.domain.zero_touch import AutomationStage
    from app.persistence.mongo_case_store import _persistence_value

    _, zero, _, _, stale, case_id = rebuilt_registry_generations(monkeypatch)
    raw = _persistence_value(snapshot_of(zero, case_id))
    raw["automation"]["stage_order_version"] = 1
    raw["automation"]["completed_stages"] = [
        stage for stage in raw["automation"]["completed_stages"] if stage != "GOLDTIER_SEARCH"
    ]
    store = _open_store(isolated_provider_database)
    try:
        store.create(DurableCaseSnapshot.model_validate(raw))
    finally:
        store.close()
    store = _open_store(isolated_provider_database, initialize=False)
    try:
        client, restarted, target = _phase24b_restart_services(store)
        assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
        current = restarted.get(case_id=case_id)
        assert current.stage_order_version == 2
        assert current.current_stage == AutomationStage.READINESS
        assert current.completed_stages == (
            AutomationStage.REGISTRY, AutomationStage.GOLDTIER_SEARCH,
            AutomationStage.DOCUMENT, AutomationStage.OWNERSHIP,
        )
        assert next(item for item in current.exceptions
                    if item.exception_id == stale.exception_id).status == "CANCELLED"
        revision = store.get(case_id).revision
        assert target.calls == []
    finally:
        store.close()
    store = _open_store(isolated_provider_database, initialize=False)
    try:
        client, final, target = _phase24b_restart_services(store)
        assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
        assert final.get(case_id=case_id) == current
        assert store.get(case_id).revision == revision
        assert target.calls == []
    finally:
        store.close()
