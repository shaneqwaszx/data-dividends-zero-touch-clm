"""Focused browser registry-binding projection and read-only route proofs."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Never, cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from test_phase16_registry_cache import (
    START,
    VALID_UEN,
    CountingAcraConnector,
    CountingRepository,
    MutableClock,
    build_cached_service,
)

from app.api_models import OnboardingCaseResponse
from app.composition import build_zero_touch_demo_control
from app.config import Settings
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.connectors.mock_idp import MockIdpProvider
from app.connectors.mock_ownership import MockOwnershipProvider
from app.domain.models import SourceEnvironment
from app.main import create_app
from app.services.clm_orchestration import ClmOrchestrationService
from app.services.clm_repository import InMemoryClmOrchestrationRepository
from app.services.document_processing import DocumentProcessingService
from app.services.document_repository import InMemoryDocumentProcessingRepository
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_repository import InMemoryOwnershipAnalysisRepository
from app.services.repository import InMemoryOnboardingCaseRepository
from app.services.target_execution_repository import InMemoryTargetExecutionRepository
from app.services.zero_touch_orchestration import ZeroTouchOrchestrator
from app.services.zero_touch_repository import InMemoryZeroTouchAutomationRepository

PDF = (
    Path(__file__).parent / "fixtures" / "uat" / "clean-company-profile.pdf"
).read_bytes()

EXPECTED_BINDING_KEYS = {
    "disposition",
    "bound_to_case_at",
    "expires_at",
    "freshness_policy_id",
    "freshness_policy_version",
    "freshness_duration_seconds",
    "freshness_comparator",
}
FORBIDDEN_CACHE_KEYS = {
    "acquisition_contract_version",
    "bundle_retrieved_at",
    "cache_id",
    "cache_key",
    "cache_revision",
    "cache_schema_version",
    "cache_written_at",
    "dataset_namespace",
    "digest",
    "endpoint_reference",
    "fingerprint",
    "freshness_anchor",
    "freshness_policy",
    "freshness_policy_fingerprint",
    "key",
    "normalized_identifier",
    "provider_effective_at",
    "provider_identity",
    "raw_payload",
    "revision",
    "source_reference",
    "written_at",
}


def _walk(value: Any) -> Iterator[Any]:
    yield value
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk(item)


def _assert_minimized_binding(payload: dict[str, Any], expected_disposition: str) -> None:
    binding = payload["registry_evidence_binding"]
    assert set(binding) == EXPECTED_BINDING_KEYS
    assert binding == {
        "disposition": expected_disposition,
        "bound_to_case_at": binding["bound_to_case_at"],
        "expires_at": binding["expires_at"],
        "freshness_policy_id": "MOCK_ACRA_FIXED_90D",
        "freshness_policy_version": 1,
        "freshness_duration_seconds": 7_776_000,
        "freshness_comparator": "EVALUATION_NOW_LT_EXPIRES_AT",
    }


def _build_cached_zero_touch_system() -> tuple[
    TestClient,
    Any,
    DocumentProcessingService,
    OwnershipAnalysisService,
    MockGoldTierConnector,
    CountingAcraConnector,
    Any,
    CountingRepository,
    InMemoryOnboardingCaseRepository,
    InMemoryTargetExecutionRepository,
]:
    clock = MutableClock()
    registry_connector = CountingAcraConnector(clock)
    cases, coordinator, cache_repository = build_cached_service(clock, registry_connector)
    case_repository = cast(InMemoryOnboardingCaseRepository, cases.case_repository)
    target = cast(MockGoldTierConnector, cases._goldtier)
    target_ledger = cast(InMemoryTargetExecutionRepository, cases._target_executions)
    documents = DocumentProcessingService(
        cases=cases,
        idp=MockIdpProvider(),
        repository=InMemoryDocumentProcessingRepository(),
        max_upload_bytes=1024 * 1024,
        review_confidence_threshold=0.85,
    )
    ownership = OwnershipAnalysisService(
        cases=cases,
        provider=MockOwnershipProvider(),
        repository=InMemoryOwnershipAnalysisRepository(),
        threshold_percent=Decimal("25"),
        max_parties=100,
        max_relationships=200,
        max_depth=8,
        max_paths_per_candidate=64,
        max_total_paths=256,
    )
    clm = ClmOrchestrationService(
        cases=cases,
        documents=documents,
        ownership=ownership,
        repository=InMemoryClmOrchestrationRepository(),
    )
    zero_touch = ZeroTouchOrchestrator(
        cases=cases,
        documents=documents,
        ownership=ownership,
        clm=clm,
        repository=InMemoryZeroTouchAutomationRepository(),
    )
    application = create_app(
        Settings(app_env="test", demo_controls_enabled=True),
        onboarding_service=cases,
        document_processing_service=documents,
        ownership_analysis_service=ownership,
        clm_orchestration_service=clm,
        zero_touch_orchestrator=zero_touch,
        zero_touch_demo_control=build_zero_touch_demo_control(),
    )
    return (
        TestClient(application),
        cases,
        documents,
        ownership,
        target,
        registry_connector,
        coordinator,
        cast(CountingRepository, cache_repository),
        case_repository,
        target_ledger,
    )


def _complete_demo_case(client: TestClient) -> dict[str, Any]:
    created = client.post(
        "/api/demo/clm/zero-touch/cases",
        json={"uen": VALID_UEN, "scenario": "STRAIGHT_THROUGH"},
    )
    assert created.status_code == 201
    case_id = created.json()["case"]["case_id"]
    completed = client.post(
        f"/api/demo/clm/zero-touch/cases/{case_id}/documents",
        headers={"content-type": "application/pdf", "X-Document-Name": "synthetic.pdf"},
        content=PDF,
    )
    assert completed.status_code == 200
    return completed.json()


def test_provider_fetch_and_cache_hit_project_exact_public_values() -> None:
    clock = MutableClock()
    connector = CountingAcraConnector(clock)
    service, _, _ = build_cached_service(clock, connector)

    fetched = service.create_staged_case(VALID_UEN)
    first_response = OnboardingCaseResponse.from_domain(fetched)
    first = first_response.model_dump(mode="json")
    _assert_minimized_binding(first, "PROVIDER_FETCH")
    assert first_response.registry_evidence_binding is not None
    assert first_response.registry_evidence_binding.bound_to_case_at == START
    assert first_response.registry_evidence_binding.expires_at == (
        START + timedelta(seconds=7_776_000)
    )

    clock.value += timedelta(hours=1)
    hit = service.create_staged_case(VALID_UEN)
    second_response = OnboardingCaseResponse.from_domain(hit)
    second = second_response.model_dump(mode="json")
    _assert_minimized_binding(second, "CACHE_HIT")
    assert second_response.registry_evidence_binding is not None
    assert second_response.registry_evidence_binding.bound_to_case_at == clock.value
    assert second_response.registry_evidence_binding.expires_at == (
        START + timedelta(seconds=7_776_000)
    )


def test_absent_binding_is_null_without_inference_from_complete_mock_acquisition() -> None:
    service, _, _ = build_cached_service(MutableClock(), CountingAcraConnector(MutableClock()))
    case = service.create_staged_case(VALID_UEN).model_copy(
        update={"registry_evidence_binding": None}
    )

    projected = OnboardingCaseResponse.from_domain(case).model_dump(mode="json")

    assert projected["registry_acquisition"]["status"] == "COMPLETE"
    assert projected["registry_evidence_binding"] is None


def test_non_mock_domain_binding_fails_closed_at_browser_projection() -> None:
    clock = MutableClock()
    service, _, _ = build_cached_service(clock, CountingAcraConnector(clock))
    case = service.create_staged_case(VALID_UEN)
    binding = case.registry_evidence_binding
    assert binding is not None
    bad_identity = binding.cache_key.provider_identity.model_copy(
        update={"environment": SourceEnvironment.SANDBOX}
    )
    bad_key = binding.cache_key.model_copy(update={"provider_identity": bad_identity})
    bad_binding = binding.model_copy(update={"cache_key": bad_key})
    case = case.model_copy(update={"registry_evidence_binding": bad_binding})

    with pytest.raises(ValueError, match="requires Mock provenance"):
        OnboardingCaseResponse.from_domain(case)


def test_projection_excludes_internal_cache_identity_from_direct_and_nested_responses() -> None:
    client, cases, _, _, _, _, _, _, _, _ = _build_cached_zero_touch_system()
    completed = _complete_demo_case(client)
    case_id = UUID(completed["case"]["case_id"])
    domain_case = cases.get_case(case_id)
    assert domain_case is not None and domain_case.registry_evidence_binding is not None
    internal = domain_case.registry_evidence_binding
    direct = OnboardingCaseResponse.from_domain(domain_case).model_dump(mode="json")

    for payload in (direct, completed["case"], completed["clm"]["case"]):
        _assert_minimized_binding(payload, "PROVIDER_FETCH")
        flattened = set(item for item in _walk(payload) if isinstance(item, str))
        assert not (FORBIDDEN_CACHE_KEYS & flattened)
        assert internal.cache_id not in flattened
        assert internal.freshness_policy_fingerprint not in flattened
        assert internal.cache_key.provider_identity.acquisition_contract_version not in flattened
        assert internal.cache_key.provider_identity.dataset_namespace not in flattened


def test_existing_case_projection_is_unchanged_after_shared_cache_refresh() -> None:
    clock = MutableClock()
    connector = CountingAcraConnector(clock)
    service, _, _ = build_cached_service(clock, connector)
    case_a = service.create_staged_case(VALID_UEN)
    before = OnboardingCaseResponse.from_domain(case_a).model_dump(mode="json")

    clock.value += timedelta(seconds=7_776_000)
    case_b = service.create_staged_case(VALID_UEN)
    reloaded_a = service.get_case(case_a.case_id)
    assert reloaded_a is not None

    assert case_b.registry_evidence_binding is not None
    assert case_b.registry_evidence_binding.bound_to_case_at == clock.value
    assert OnboardingCaseResponse.from_domain(reloaded_a).model_dump(mode="json") == before


def test_detailed_case_get_only_reads_retained_state_after_fixture_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        client,
        cases,
        documents,
        ownership,
        target,
        registry_connector,
        coordinator,
        cache_repository,
        case_repository,
        target_ledger,
    ) = _build_cached_zero_touch_system()
    completed = _complete_demo_case(client)
    case_id = UUID(completed["case"]["case_id"])

    def forbidden(*args: object, **kwargs: object) -> Never:
        raise AssertionError("detailed case GET invoked a forbidden execution/write path")

    monkeypatch.setattr(coordinator, "acquire", forbidden)
    for method in (
        "fetch_company",
        "fetch_officers",
        "fetch_ownership_parties",
        "fetch_relationships",
    ):
        monkeypatch.setattr(registry_connector, method, forbidden)
    for method in ("get", "create", "replace"):
        monkeypatch.setattr(cache_repository, method, forbidden)
    for method in (
        "create",
        "save",
        "delete_for_case",
        "transaction_replace",
        "transaction_restore",
    ):
        monkeypatch.setattr(case_repository, method, forbidden)
    monkeypatch.setattr(documents._idp, "process", forbidden)
    monkeypatch.setattr(ownership, "load", forbidden)
    monkeypatch.setattr(ownership, "analyze", forbidden)
    for method in ("search_party", "create_shell_customer", "create_policy", "amend_party"):
        monkeypatch.setattr(target, method, forbidden)

    ledger_reads = 0
    original_ledger_get: Callable[..., Any] = target_ledger.get

    def counted_ledger_get(*args: object, **kwargs: object) -> Any:
        nonlocal ledger_reads
        ledger_reads += 1
        return original_ledger_get(*args, **kwargs)

    monkeypatch.setattr(target_ledger, "get", counted_ledger_get)
    for method in ("create", "replace", "delete_if_unattempted", "delete_for_case"):
        monkeypatch.setattr(target_ledger, method, forbidden)

    response = client.get(f"/api/clm/zero-touch/cases/{case_id}")

    assert response.status_code == 200
    _assert_minimized_binding(response.json()["case"], "PROVIDER_FETCH")
    assert response.json()["target_operations"]
    assert ledger_reads == 1
    assert cases.get_case(case_id) is not None
