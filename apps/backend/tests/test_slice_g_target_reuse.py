"""G normal target reuse reacquires required evidence without inventing target proof."""

from datetime import timedelta
from uuid import uuid4

import pytest
from scripts.slice_b_registry_fixture import CountingSyntheticRegistry
from test_phase16_registry_cache import MutableClock
from test_slice_d_mock_goldtier import NAME, UEN, prepared
from test_slice_d_real_mongo import RecordingMock

from app.connectors.mock_acra import MOCK_ACRA_DATASET_NAMESPACE, MockAcraConnector
from app.connectors.registry import AcraRegistryProviderAdapter, RegistryProviderRouter
from app.domain.models import (
    RegistryFreshnessPolicy,
    RegistryProviderIdentity,
    SourceEnvironment,
    SourceSystem,
)
from app.services.onboarding import OnboardingService
from app.services.registry_acquisition import RegistryAcquisitionCoordinator
from app.services.registry_cache_repository import InMemoryRegistrySnapshotRepository
from app.services.repository import InMemoryOnboardingCaseRepository


def build_owner(*, cache):
    clock = MutableClock()
    registry = CountingSyntheticRegistry()
    registry.delegate = MockAcraConnector(clock=clock)
    target = RecordingMock()
    identity = RegistryProviderIdentity(
        provider=SourceSystem.ACRA,
        environment=SourceEnvironment.MOCK,
        acquisition_contract_version=AcraRegistryProviderAdapter.ACQUISITION_CONTRACT_VERSION,
        dataset_namespace=MOCK_ACRA_DATASET_NAMESPACE,
    )
    adapter = AcraRegistryProviderAdapter(registry, clock=clock, cache_identity=identity)
    snapshots = InMemoryRegistrySnapshotRepository()
    coordinator = (
        RegistryAcquisitionCoordinator(snapshots, RegistryFreshnessPolicy(), clock=clock)
        if cache
        else None
    )
    owner = OnboardingService(
        acra=None,
        goldtier=target,
        repository=InMemoryOnboardingCaseRepository(),
        registry_router=RegistryProviderRouter(adapter),
        registry_acquisition_coordinator=coordinator,
        clock=clock,
    )
    submission = prepared(owner)
    owner.execute_submission_input(submission)
    return owner, registry, target, clock


@pytest.mark.parametrize(
    ("cache", "expired", "expected"), [(False, False, 8), (True, False, 4), (True, True, 8)]
)
def test_required_acquisition_obeys_current_cache_owner(cache, expired, expected):
    owner, registry, target, clock = build_owner(cache=cache)
    if expired:
        clock.value += timedelta(days=90)
    before_target = list(target.calls)
    case = owner.create_staged_case_with_identity(uuid4(), uuid4(), UEN, "SG", legal_name=NAME)
    assert case.initial_target_search.disposition == "EXACT_MATCH"
    assert case.existing_target_state is not None
    assert case.registry_acquisition.status.value == "COMPLETE"
    assert case.entity == case.registry_acquisition.entity_profile
    assert len(registry.calls) == expected
    assert target.calls == before_target + ["SEARCH"]
    if cache:
        assert case.registry_evidence_binding.disposition.value == (
            "PROVIDER_FETCH" if expired else "CACHE_HIT"
        )
    else:
        assert case.registry_evidence_binding is None


@pytest.mark.parametrize(
    ("field", "value"), [("entity_name", "DIFFERENT SYNTHETIC PTE. LTD."), ("country_code", "MY")]
)
def test_conflicting_current_registry_identity_cannot_relabel_prior_search(field, value):
    owner, registry, target, clock = build_owner(cache=False)
    original = registry.fetch_company
    registry.fetch_company = lambda identifier: original(identifier).model_copy(
        update={field: value}
    )
    before_target = list(target.calls)
    case = owner.create_staged_case_with_identity(uuid4(), uuid4(), UEN, "SG", legal_name=NAME)
    assert case.state.value == "REVIEW_REQUIRED"
    assert case.error.code == "GT_SEARCH_IDENTITY_REVIEW_REQUIRED"
    assert case.existing_target_state is None
    assert case.initial_target_search.disposition == "REVIEW_REQUIRED"
    assert case.initial_target_search.selected_party_id is None
    assert target.calls == before_target + ["SEARCH"]
    assert case.entity == case.registry_acquisition.entity_profile
    assert owner.get_case(case.case_id) == case


@pytest.mark.parametrize(
    ("failure", "expected_status", "expected_code"),
    [
        ("profile", "FAILED", "ACRA_SERVICE_UNAVAILABLE"),
        ("cache_read", "FAILED", "REGISTRY_CACHE_READ_FAILED"),
        ("cache_write", "FAILED", "REGISTRY_CACHE_WRITE_FAILED"),
        ("cache_conflict", "FAILED", "REGISTRY_CACHE_CONFLICT"),
        ("absent", "REVIEW_REQUIRED", "ACRA_ENTITY_NOT_FOUND"),
    ],
)
def test_required_registry_failure_is_not_projected_as_skipped(
    failure, expected_status, expected_code
):
    from fastapi.testclient import TestClient
    from test_phase16_registry_cache import (
        ConflictRepository,
        ReadFailureRepository,
        WriteFailureRepository,
    )

    from app.config import Settings
    from app.connectors.errors import AcraServiceUnavailableError
    from app.main import create_app

    owner, registry, target, clock = build_owner(cache=False)
    if failure in {"cache_read", "cache_write", "cache_conflict"}:
        repositories = {
            "cache_read": ReadFailureRepository,
            "cache_write": WriteFailureRepository,
            "cache_conflict": ConflictRepository,
        }
        owner._registry_acquisition_coordinator = RegistryAcquisitionCoordinator(  # noqa: SLF001
            repositories[failure](), RegistryFreshnessPolicy(), clock=clock
        )
    elif failure == "absent":
        registry.fetch_company = lambda identifier: None
    else:

        def unavailable(identifier):
            raise AcraServiceUnavailableError

        registry.fetch_company = unavailable
    before_target = list(target.calls)
    client = TestClient(
        create_app(
            Settings(_env_file=None, app_env="test"),
            onboarding_service=owner,
            acra_connector=registry,
        )
    )
    created = client.post(
        "/api/clm/zero-touch/cases",
        json={
            "uen": UEN,
            "legal_name": NAME,
            "country_of_incorporation": "SG",
        },
    )
    assert created.status_code == 201
    result = created.json()
    assert result["case"]["registry_acquisition"] is None
    assert result["case"]["error"]["code"] == expected_code
    node = next(
        item for item in result["processing_pipeline"] if item["node_id"] == "ACRA_REGISTRY"
    )
    assert node["status"] == expected_status
    assert node["blocker_code"] == expected_code
    assert "skipped" not in node["safe_result"].casefold()
    assert target.calls == before_target + ["SEARCH"]


@pytest.mark.parametrize("operation", ["fetch_officers", "fetch_ownership_parties"])
def test_identity_conflict_does_not_hide_failed_required_operation(operation):
    from uuid import UUID

    from fastapi.testclient import TestClient

    from app.config import Settings
    from app.connectors.errors import AcraServiceUnavailableError
    from app.main import create_app

    owner, registry, target, clock = build_owner(cache=False)
    original = registry.fetch_company
    registry.fetch_company = lambda identifier: original(identifier).model_copy(
        update={"entity_name": "DIFFERENT SYNTHETIC PTE. LTD."}
    )

    def unavailable(identifier):
        raise AcraServiceUnavailableError

    setattr(registry, operation, unavailable)
    before_target = list(target.calls)
    client = TestClient(
        create_app(
            Settings(_env_file=None, app_env="test"),
            onboarding_service=owner,
            acra_connector=registry,
        )
    )
    response = client.post(
        "/api/clm/zero-touch/cases",
        json={
            "uen": UEN,
            "legal_name": NAME,
            "country_of_incorporation": "SG",
        },
    )
    assert response.status_code == 201
    result = response.json()
    assert result["status"] == "TECHNICAL_FAILURE"
    assert result["current_stage"] == "REGISTRY"
    assert result["active_exceptions"] == []
    node = next(
        item for item in result["processing_pipeline"] if item["node_id"] == "ACRA_REGISTRY"
    )
    assert node["status"] == "FAILED"
    assert node["blocker_code"] == "REGISTRY_OPERATION_UNAVAILABLE"
    case = owner.get_case(UUID(result["case"]["case_id"]))
    assert case.registry_acquisition.status.value == "FAILED"
    assert case.state.value == "FAILED"
    assert case.error.code == "REGISTRY_OPERATION_UNAVAILABLE"
    assert case.existing_target_state is None
    assert case.initial_target_search.disposition == "REVIEW_REQUIRED"
    assert case.initial_target_search.selected_party_id is None
    assert target.calls == before_target + ["SEARCH"]


@pytest.mark.parametrize("cache", [False, True])
def test_same_identity_recheck_retains_current_required_acquisition(cache):
    owner, registry, target, clock = build_owner(cache=cache)
    clock.value += timedelta(days=90)
    case = owner.create_staged_case_with_identity(uuid4(), uuid4(), UEN, "SG", legal_name=NAME)
    current = case.registry_acquisition
    binding = case.registry_evidence_binding
    before_source, before_target = len(registry.calls), list(target.calls)
    repaired = owner.repair_initial_identity_and_recheck(
        case_id=case.case_id,
        actor_id="g-local-review",
        legal_name=NAME,
        registration_number=UEN,
        country_of_incorporation="SG",
        expected_case_event_count=len(case.events),
    )
    assert repaired.state.value == "VALIDATED"
    assert repaired.entity == current.entity_profile
    assert repaired.registry_acquisition == current
    assert repaired.registry_evidence_binding == binding
    assert repaired.initial_target_search_attempts[-1].status == "COMPLETED"
    assert owner.get_case(case.case_id) == repaired
    assert len(registry.calls) == before_source
    assert target.calls == before_target + ["SEARCH"]


@pytest.mark.parametrize("failure", [None, "absent", "profile", "officers"])
def test_exact_recheck_requires_missing_current_registry_evidence(failure):
    from app.connectors.errors import AcraServiceUnavailableError
    from app.services.errors import OnboardingInfrastructureError

    owner, registry, target, clock = build_owner(cache=False)
    case = owner.create_staged_case_with_identity(uuid4(), uuid4(), UEN, "SG", legal_name=NAME)
    # Valid retained source-free target provenance is readable; a new recheck needs evidence.
    case.registry_acquisition = None
    case.registry_evidence_binding = None
    owner._repository.save(case)  # noqa: SLF001
    before_source, before_target = len(registry.calls), list(target.calls)
    if failure == "absent":
        registry.fetch_company = lambda identifier: None
    elif failure in {"profile", "officers"}:

        def unavailable(identifier):
            raise AcraServiceUnavailableError

        setattr(
            registry, "fetch_company" if failure == "profile" else "fetch_officers", unavailable
        )
    arguments = dict(
        case_id=case.case_id,
        actor_id="g-local-review",
        legal_name=NAME,
        registration_number=UEN,
        country_of_incorporation="SG",
        expected_case_event_count=len(case.events),
    )
    if failure == "profile":
        with pytest.raises(OnboardingInfrastructureError):
            owner.repair_initial_identity_and_recheck(**arguments)
        repaired = owner.get_case(case.case_id)
    else:
        repaired = owner.repair_initial_identity_and_recheck(**arguments)
    assert repaired.initial_target_search_attempts[-1].status == "COMPLETED"
    assert target.calls == before_target + ["SEARCH"]
    if failure is None:
        assert len(registry.calls) == before_source + 4
        assert repaired.state.value == "VALIDATED"
        assert repaired.entity == repaired.registry_acquisition.entity_profile
    elif failure == "absent":
        assert repaired.state.value == "REVIEW_REQUIRED"
        assert repaired.error.code == "ACRA_ENTITY_NOT_FOUND"
        assert repaired.registry_acquisition is None
    else:
        assert repaired.state.value == "FAILED"
        assert repaired.error.code == (
            "ACRA_SERVICE_UNAVAILABLE" if failure == "profile" else "REGISTRY_OPERATION_UNAVAILABLE"
        )
    assert owner.get_case(case.case_id) == repaired


@pytest.mark.parametrize("failure", ["profile", "officers", "absent"])
def test_public_recheck_settles_search_and_preserves_required_source_failure(failure):
    from uuid import UUID

    from fastapi.testclient import TestClient

    from app.config import Settings
    from app.connectors.errors import AcraServiceUnavailableError
    from app.main import create_app

    owner, registry, target, clock = build_owner(cache=False)
    client = TestClient(
        create_app(
            Settings(_env_file=None, app_env="test"),
            onboarding_service=owner,
            acra_connector=registry,
        )
    )
    created = client.post(
        "/api/clm/zero-touch/cases",
        json={
            "uen": UEN,
            "legal_name": NAME,
            "country_of_incorporation": "SG",
        },
    )
    assert created.status_code == 201
    summary = created.json()
    case_id = UUID(summary["case"]["case_id"])
    case = owner.get_case(case_id)
    case.registry_acquisition = None
    case.registry_evidence_binding = None
    owner._repository.save(case)  # noqa: SLF001
    original_profile = registry.fetch_company
    if failure == "absent":
        registry.fetch_company = lambda identifier: None
    else:

        def unavailable(identifier):
            raise AcraServiceUnavailableError

        setattr(
            registry, "fetch_company" if failure == "profile" else "fetch_officers", unavailable
        )
    before_target = list(target.calls)
    result = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/identity-search-recheck",
        json={
            "legal_name": NAME,
            "registration_number": UEN,
            "country_of_incorporation": "SG",
            "expected_automation_version": summary["version"],
            "expected_clm_version": summary["clm"]["version"],
            "expected_case_event_count": len(case.events),
        },
    )
    assert result.status_code == (503 if failure == "profile" else 200), result.json().get("detail")
    current = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
    assert current["status"] == (
        "WAITING_FOR_REVIEW" if failure == "absent" else "TECHNICAL_FAILURE"
    )
    assert current["current_stage"] == "REGISTRY"
    node = next(
        item for item in current["processing_pipeline"] if item["node_id"] == "ACRA_REGISTRY"
    )
    assert node["status"] == ("REVIEW_REQUIRED" if failure == "absent" else "FAILED")
    if failure != "absent":
        assert current["active_exceptions"] == []
    retained = owner.get_case(case_id)
    assert retained.initial_target_search_attempts[-1].status == "COMPLETED"
    assert retained.existing_target_state is None
    assert target.calls == before_target + ["SEARCH"]

    if failure in {"profile", "absent"}:
        registry.fetch_company = original_profile
        if failure == "profile":
            registry.fetch_officers = unavailable
        retry = client.post(
            f"/api/clm/zero-touch/cases/{case_id}/identity-search-recheck",
            json={
                "legal_name": NAME,
                "registration_number": UEN,
                "country_of_incorporation": "SG",
                "expected_automation_version": current["version"],
                "expected_clm_version": current["clm"]["version"],
                "expected_case_event_count": len(retained.events),
            },
        )
        assert retry.status_code == 200
        now = retry.json()
        if failure == "profile":
            assert now["status"] == "TECHNICAL_FAILURE"
            assert now["technical_failure"]["code"] == "REGISTRY_OPERATION_UNAVAILABLE"
        else:
            assert now["status"] == "PENDING_INPUTS"
            assert now["current_stage"] == "DOCUMENT"
            assert not any(item["stage"] == "REGISTRY" for item in now["active_exceptions"])
        assert owner.get_case(case_id).initial_target_search_attempts[-1].status == "COMPLETED"
        assert target.calls == before_target + ["SEARCH", "SEARCH"]
