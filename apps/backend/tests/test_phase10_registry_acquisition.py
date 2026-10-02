"""Focused Phase 10 acquisition, ownership integration, and call-stopping tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.connectors.acra import (
    AcraCompanyPayload,
    AcraOfficerPayload,
    AcraOfficersPayload,
    AcraOwnershipPartiesPayload,
    AcraRelationshipsPayload,
)
from app.connectors.mock_acra import (
    EMPTY_OFFICERS_UEN,
    FAILED_RELATIONSHIPS_UEN,
    LEGAL_ENTITY_OWNER_UEN,
    MALFORMED_RELATIONSHIPS_UEN,
    MISSING_OWNERSHIP_UEN,
    MULTI_LEVEL_OWNER_UEN,
    MULTIPLE_OWNERS_UEN,
    MockAcraConnector,
)
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
from app.domain.models import (
    RegistryAcquisitionBundle,
    RegistryAcquisitionStatus,
    RegistryOperationStatus,
    WorkflowState,
)
from app.domain.ownership import OwnershipAnalysisState
from app.main import create_app
from app.services.onboarding import OnboardingService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_repository import InMemoryOwnershipAnalysisRepository
from app.services.repository import InMemoryOnboardingCaseRepository

NOW = datetime(2026, 8, 28, 2, 0, tzinfo=UTC)


class CountingAcraConnector:
    def __init__(self) -> None:
        self.delegate = MockAcraConnector(clock=lambda: NOW)
        self.calls = {
            "ENTITY_PROFILE": 0,
            "OFFICERS": 0,
            "OWNERSHIP_PARTIES": 0,
            "RELATIONSHIPS": 0,
        }

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        self.calls["ENTITY_PROFILE"] += 1
        return self.delegate.fetch_company(uen)

    def fetch_officers(self, uen: str) -> AcraOfficersPayload:
        self.calls["OFFICERS"] += 1
        return self.delegate.fetch_officers(uen)

    def fetch_ownership_parties(self, uen: str) -> AcraOwnershipPartiesPayload:
        self.calls["OWNERSHIP_PARTIES"] += 1
        return self.delegate.fetch_ownership_parties(uen)

    def fetch_relationships(self, uen: str) -> AcraRelationshipsPayload:
        self.calls["RELATIONSHIPS"] += 1
        return self.delegate.fetch_relationships(uen)


class WrongIdentityOfficersConnector(CountingAcraConnector):
    def fetch_officers(self, uen: str) -> AcraOfficersPayload:
        self.calls["OFFICERS"] += 1
        payload = self.delegate.fetch_officers(uen)
        return payload.model_copy(update={"uen": "202400002B"})


def build_service(
    connector: CountingAcraConnector | None = None,
) -> tuple[OnboardingService, CountingAcraConnector]:
    active = connector or CountingAcraConnector()
    return (
        OnboardingService(
            acra=active,
            goldtier=MockGoldTierConnector(),
            repository=InMemoryOnboardingCaseRepository(),
            clock=lambda: NOW,
        ),
        active,
    )


def direct_bundle_payload(identifier: str = "202400001A") -> dict[str, Any]:
    """Return mutable primitives for direct aggregate-construction probes."""

    service, _ = build_service()
    acquisition = service.create_staged_case(identifier).registry_acquisition
    assert acquisition is not None
    return acquisition.model_dump(mode="json")


def operation_payload(payload: dict[str, Any], operation: str) -> dict[str, Any]:
    return next(
        item for item in payload["operation_results"] if item["operation"] == operation
    )


def expected_missing_issue() -> dict[str, str]:
    return {
        "code": "REGISTRY_EXPECTED_DATA_MISSING",
        "message": "Expected registry ownership evidence was not returned.",
    }


def technical_issue() -> dict[str, str]:
    return {
        "code": "REGISTRY_OPERATION_UNAVAILABLE",
        "message": "Registry operation could not be completed.",
    }


def test_normal_singapore_acquisition_calls_each_operation_exactly_once() -> None:
    service, connector = build_service()

    case = service.create_staged_case("202400001A")

    assert case.state == WorkflowState.VALIDATED
    assert case.registry_acquisition is not None
    assert case.registry_acquisition.status == RegistryAcquisitionStatus.COMPLETE
    assert connector.calls == {
        "ENTITY_PROFILE": 1,
        "OFFICERS": 1,
        "OWNERSHIP_PARTIES": 1,
        "RELATIONSHIPS": 1,
    }
    assert [item.status for item in case.registry_acquisition.operation_results] == [
        RegistryOperationStatus.COMPLETE,
        RegistryOperationStatus.COMPLETE,
        RegistryOperationStatus.COMPLETE,
        RegistryOperationStatus.COMPLETE,
    ]
    assert service.get_case(case.case_id) == case
    assert connector.calls["ENTITY_PROFILE"] == 1


@pytest.mark.parametrize(
    ("identifier", "country", "code"),
    (
        ("UNKNOWN-123", None, "JURISDICTION_UNRESOLVED"),
        ("202400001A", "AU", "JURISDICTION_CONFLICT"),
        ("AU-REG-123", "AU", "REGISTRY_PROVIDER_NOT_IMPLEMENTED"),
        ("BAD-ID", "SG", "REGISTRY_IDENTIFIER_NOT_ELIGIBLE"),
    ),
)
def test_phase09_blockers_make_zero_acquisition_calls(
    identifier: str, country: str | None, code: str
) -> None:
    service, connector = build_service()

    case = service.create_staged_case(identifier, country)

    assert case.state == WorkflowState.REVIEW_REQUIRED
    assert case.error is not None and case.error.code == code
    assert case.registry_acquisition is None
    assert set(connector.calls.values()) == {0}


def test_legitimate_empty_officer_collection_is_truthfully_complete() -> None:
    service, connector = build_service()

    case = service.create_staged_case(EMPTY_OFFICERS_UEN)

    assert case.state == WorkflowState.VALIDATED
    assert case.registry_acquisition is not None
    assert case.registry_acquisition.status == RegistryAcquisitionStatus.COMPLETE
    assert case.registry_acquisition.officers == ()
    assert case.registry_acquisition.operation_results[1].status == RegistryOperationStatus.EMPTY
    assert connector.calls == {key: 1 for key in connector.calls}


def test_missing_ownership_retains_partial_evidence_but_validates_registry_identity() -> None:
    service, connector = build_service()

    case = service.create_staged_case(MISSING_OWNERSHIP_UEN)

    assert case.state == WorkflowState.VALIDATED
    assert case.error is None
    assert case.registry_acquisition is not None
    assert case.registry_acquisition.status == RegistryAcquisitionStatus.PARTIAL
    assert case.registry_acquisition.ownership_parties == ()
    assert case.registry_acquisition.relationships == ()
    assert connector.calls == {key: 1 for key in connector.calls}
    assert case.goldtier_result is None


@pytest.mark.parametrize(
    ("identifier", "expected_code"),
    (
        (MALFORMED_RELATIONSHIPS_UEN, "REGISTRY_OPERATION_MALFORMED_RESPONSE"),
        (FAILED_RELATIONSHIPS_UEN, "REGISTRY_OPERATION_UNAVAILABLE"),
    ),
)
def test_later_step_malformed_and_provider_failure_are_sanitized(
    identifier: str, expected_code: str
) -> None:
    service, connector = build_service()

    case = service.create_staged_case(identifier)

    assert case.state == WorkflowState.FAILED
    assert case.error is not None and case.error.code == expected_code
    assert case.registry_acquisition is not None
    assert case.registry_acquisition.status == RegistryAcquisitionStatus.FAILED
    relationship = case.registry_acquisition.operation_results[-1]
    assert relationship.status == RegistryOperationStatus.FAILED
    assert relationship.error is not None and relationship.error.code == expected_code
    assert connector.calls == {key: 1 for key in connector.calls}
    assert "unsafe-shape" not in case.model_dump_json()


def test_later_operation_identity_mismatch_stops_remaining_operations() -> None:
    connector = WrongIdentityOfficersConnector()
    service, _ = build_service(connector)

    case = service.create_staged_case("202400001A")

    assert case.state == WorkflowState.FAILED
    assert case.error is not None
    assert case.error.code == "REGISTRY_OPERATION_MALFORMED_RESPONSE"
    assert connector.calls == {
        "ENTITY_PROFILE": 1,
        "OFFICERS": 1,
        "OWNERSHIP_PARTIES": 0,
        "RELATIONSHIPS": 0,
    }
    assert case.registry_acquisition is not None
    assert [item.status for item in case.registry_acquisition.operation_results] == [
        RegistryOperationStatus.COMPLETE,
        RegistryOperationStatus.FAILED,
        RegistryOperationStatus.NOT_ATTEMPTED,
        RegistryOperationStatus.NOT_ATTEMPTED,
    ]


@pytest.mark.parametrize(
    "identifier",
    (LEGAL_ENTITY_OWNER_UEN, MULTIPLE_OWNERS_UEN, MULTI_LEVEL_OWNER_UEN),
)
def test_bounded_synthetic_ownership_scenarios_normalize(identifier: str) -> None:
    service, _ = build_service()

    case = service.create_staged_case(identifier)

    assert case.state == WorkflowState.VALIDATED
    assert case.registry_acquisition is not None
    assert case.registry_acquisition.ownership_parties
    assert case.registry_acquisition.relationships
    assert all(
        item.provenance.evidence_reference.startswith("acra:")
        for item in case.registry_acquisition.relationships
    )


@pytest.mark.parametrize("identifier", ("202400001A", MISSING_OWNERSHIP_UEN))
def test_registry_evidence_feeds_existing_decimal_ownership_analysis(identifier: str) -> None:
    service, _ = build_service()
    case = service.create_staged_case(identifier)
    ownership = OwnershipAnalysisService(
        cases=service,
        provider=RegistryAcquisitionOwnershipProvider(service),
        repository=InMemoryOwnershipAnalysisRepository(),
        threshold_percent=Decimal("25"),
        max_parties=100,
        max_relationships=200,
        max_depth=8,
        max_paths_per_candidate=64,
        max_total_paths=256,
        clock=lambda: NOW,
    )

    loaded = ownership.load(case_id=case.case_id)
    analyzed = ownership.analyze(case_id=case.case_id)

    assert loaded.provider_name == "ACRA_REGISTRY_ACQUISITION"
    if identifier == MISSING_OWNERSHIP_UEN:
        assert analyzed.state == OwnershipAnalysisState.REVIEW_REQUIRED
        assert analyzed.candidates == []
        assert [item.code.value for item in analyzed.issues] == [
            "INCOMPLETE_LEGAL_ENTITY", "OWNERSHIP_REQUIRED"
        ]
        assert case.registry_acquisition is not None
        assert case.registry_acquisition.status == RegistryAcquisitionStatus.PARTIAL
        return
    assert analyzed.state == OwnershipAnalysisState.ANALYZED
    assert [item.aggregated_ownership_percent for item in analyzed.candidates] == [
        Decimal("60"),
        Decimal("40"),
    ]
    assert all(
        item.threshold_comparator == "GREATER_THAN_OR_EQUAL_TO"
        for item in analyzed.candidates
    )


def test_registry_cycle_uses_existing_cycle_handling() -> None:
    service, _ = build_service()
    case = service.create_staged_case("202400006F")
    ownership = OwnershipAnalysisService(
        cases=service,
        provider=RegistryAcquisitionOwnershipProvider(service),
        repository=InMemoryOwnershipAnalysisRepository(),
        threshold_percent=Decimal("25"),
        max_parties=100,
        max_relationships=200,
        max_depth=8,
        max_paths_per_candidate=64,
        max_total_paths=256,
        clock=lambda: NOW,
    )

    ownership.load(case_id=case.case_id)
    analyzed = ownership.analyze(case_id=case.case_id)

    assert analyzed.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert {item.code.value for item in analyzed.issues} == {"CYCLE_DETECTED"}


def test_collection_bound_rejects_oversized_officer_response() -> None:
    officer = AcraOfficerPayload(
        officer_id="OFFICER_A",
        name="Alex Synthetic",
        role="DIRECTOR",
    )
    with pytest.raises(ValidationError):
        AcraOfficersPayload(
            uen="202400001A",
            officers=tuple(officer.model_copy() for _ in range(33)),
            source_environment="MOCK",
            source_endpoint="https://mock.acra.gov.sg/api/entities/202400001A/officers",
            retrieved_at=NOW,
        )


def test_original_false_complete_counterexample_is_rejected_directly() -> None:
    payload = direct_bundle_payload()
    payload["ownership_parties"] = []
    payload["relationships"] = []
    for operation in ("OWNERSHIP_PARTIES", "RELATIONSHIPS"):
        result = operation_payload(payload, operation)
        result.update(
            status="NOT_ATTEMPTED",
            record_count=0,
            provenance=None,
            error=None,
        )

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_complete_with_relationships_not_attempted_is_rejected_directly() -> None:
    payload = direct_bundle_payload()
    payload["relationships"] = []
    operation_payload(payload, "RELATIONSHIPS").update(
        status="NOT_ATTEMPTED",
        record_count=0,
        provenance=None,
        error=None,
    )

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_complete_with_ownership_empty_is_rejected_directly() -> None:
    payload = direct_bundle_payload()
    payload["ownership_parties"] = []
    payload["relationships"] = []
    for operation in ("OWNERSHIP_PARTIES", "RELATIONSHIPS"):
        operation_payload(payload, operation).update(status="EMPTY", record_count=0)

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_complete_with_relationships_empty_is_rejected_directly() -> None:
    payload = direct_bundle_payload()
    payload["relationships"] = []
    operation_payload(payload, "RELATIONSHIPS").update(status="EMPTY", record_count=0)

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


@pytest.mark.parametrize("failed_operation", ("OWNERSHIP_PARTIES", "RELATIONSHIPS"))
def test_complete_with_failed_ownership_operation_is_rejected_directly(
    failed_operation: str,
) -> None:
    payload = direct_bundle_payload()
    failed_index = ("ENTITY_PROFILE", "OFFICERS", "OWNERSHIP_PARTIES", "RELATIONSHIPS").index(
        failed_operation
    )
    if failed_operation == "OWNERSHIP_PARTIES":
        payload["ownership_parties"] = []
    payload["relationships"] = []
    operation_payload(payload, failed_operation).update(
        status="FAILED",
        record_count=0,
        error=technical_issue(),
    )
    for result in payload["operation_results"][failed_index + 1 :]:
        result.update(
            status="NOT_ATTEMPTED",
            record_count=0,
            provenance=None,
            error=None,
        )

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_complete_with_missing_required_operation_is_rejected_directly() -> None:
    payload = direct_bundle_payload()
    payload["operation_results"] = payload["operation_results"][:-1]

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_complete_with_duplicate_operation_is_rejected_directly() -> None:
    payload = direct_bundle_payload()
    payload["operation_results"][-1] = payload["operation_results"][-2]

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_complete_with_unknown_extra_operation_is_rejected_directly() -> None:
    payload = direct_bundle_payload()
    payload["operation_results"].append(
        {
            "operation": "UNKNOWN_OPERATION",
            "status": "NOT_ATTEMPTED",
            "record_count": 0,
            "provenance": None,
            "error": None,
        }
    )

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_complete_with_blocking_missing_data_issue_is_rejected_directly() -> None:
    payload = direct_bundle_payload()
    payload["issues"] = [expected_missing_issue()]

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


@pytest.mark.parametrize("identifier", ("202400001A", EMPTY_OFFICERS_UEN))
def test_valid_complete_bundles_are_accepted_directly(identifier: str) -> None:
    payload = direct_bundle_payload(identifier)

    acquisition = RegistryAcquisitionBundle.model_validate(payload)

    assert acquisition.status == RegistryAcquisitionStatus.COMPLETE


def test_partial_with_all_required_evidence_complete_is_rejected_directly() -> None:
    payload = direct_bundle_payload()
    payload["status"] = "PARTIAL"
    payload["issues"] = [expected_missing_issue()]

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_partial_with_technical_failure_is_rejected_directly() -> None:
    payload = direct_bundle_payload(FAILED_RELATIONSHIPS_UEN)
    payload["status"] = "PARTIAL"

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_partial_without_expected_missing_data_issue_is_rejected_directly() -> None:
    payload = direct_bundle_payload()
    payload["relationships"] = []
    operation_payload(payload, "RELATIONSHIPS").update(status="EMPTY", record_count=0)
    payload["status"] = "PARTIAL"
    payload["issues"] = []

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_partial_empty_operation_with_retained_collection_is_rejected_directly() -> None:
    payload = direct_bundle_payload()
    operation_payload(payload, "RELATIONSHIPS").update(status="EMPTY", record_count=0)
    payload["status"] = "PARTIAL"
    payload["issues"] = [expected_missing_issue()]

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_valid_partial_missing_ownership_is_accepted_directly() -> None:
    payload = direct_bundle_payload(MISSING_OWNERSHIP_UEN)

    acquisition = RegistryAcquisitionBundle.model_validate(payload)

    assert acquisition.status == RegistryAcquisitionStatus.PARTIAL


def test_valid_partial_missing_relationships_is_accepted_directly() -> None:
    payload = direct_bundle_payload()
    payload["relationships"] = []
    operation_payload(payload, "RELATIONSHIPS").update(status="EMPTY", record_count=0)
    payload["status"] = "PARTIAL"
    payload["issues"] = [expected_missing_issue()]

    acquisition = RegistryAcquisitionBundle.model_validate(payload)

    assert acquisition.status == RegistryAcquisitionStatus.PARTIAL


def test_failed_bundle_without_failed_operation_is_rejected_directly() -> None:
    payload = direct_bundle_payload()
    payload["status"] = "FAILED"
    payload["issues"] = [technical_issue()]

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_failed_bundle_rejects_completed_operation_after_first_failure() -> None:
    payload = direct_bundle_payload()
    payload["officers"] = []
    payload["relationships"] = []
    operation_payload(payload, "OFFICERS").update(
        status="FAILED",
        record_count=0,
        error=technical_issue(),
    )
    operation_payload(payload, "RELATIONSHIPS").update(
        status="NOT_ATTEMPTED",
        record_count=0,
        provenance=None,
        error=None,
    )
    payload["status"] = "FAILED"
    payload["issues"] = [technical_issue()]

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_failed_bundle_rejects_records_for_not_attempted_operation() -> None:
    payload = direct_bundle_payload()
    payload["officers"] = []
    payload["relationships"] = []
    operation_payload(payload, "OFFICERS").update(
        status="FAILED",
        record_count=0,
        error=technical_issue(),
    )
    for operation in ("OWNERSHIP_PARTIES", "RELATIONSHIPS"):
        operation_payload(payload, operation).update(
            status="NOT_ATTEMPTED",
            record_count=0,
            provenance=None,
            error=None,
        )
    payload["status"] = "FAILED"
    payload["issues"] = [technical_issue()]

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_failed_operation_without_safe_error_is_rejected_directly() -> None:
    payload = direct_bundle_payload(FAILED_RELATIONSHIPS_UEN)
    operation_payload(payload, "RELATIONSHIPS")["error"] = None

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_valid_officer_failure_prefix_is_accepted_directly() -> None:
    connector = WrongIdentityOfficersConnector()
    service, _ = build_service(connector)
    acquisition = service.create_staged_case("202400001A").registry_acquisition
    assert acquisition is not None

    reconstructed = RegistryAcquisitionBundle.model_validate(
        acquisition.model_dump(mode="json")
    )

    assert [item.status for item in reconstructed.operation_results] == [
        RegistryOperationStatus.COMPLETE,
        RegistryOperationStatus.FAILED,
        RegistryOperationStatus.NOT_ATTEMPTED,
        RegistryOperationStatus.NOT_ATTEMPTED,
    ]


def test_valid_relationship_failure_prefix_is_accepted_directly() -> None:
    payload = direct_bundle_payload(FAILED_RELATIONSHIPS_UEN)

    acquisition = RegistryAcquisitionBundle.model_validate(payload)

    assert acquisition.status == RegistryAcquisitionStatus.FAILED
    assert acquisition.operation_results[-1].status == RegistryOperationStatus.FAILED


@pytest.mark.parametrize(
    ("operation", "record_count"),
    (("OFFICERS", 2), ("RELATIONSHIPS", 1)),
)
def test_complete_record_count_mismatch_is_rejected_directly(
    operation: str, record_count: int
) -> None:
    payload = direct_bundle_payload()
    operation_payload(payload, operation)["record_count"] = record_count

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_empty_officer_result_with_nonzero_count_is_rejected_directly() -> None:
    payload = direct_bundle_payload(EMPTY_OFFICERS_UEN)
    operation_payload(payload, "OFFICERS")["record_count"] = 1

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_duplicate_officer_identity_is_rejected_directly() -> None:
    payload = direct_bundle_payload()
    payload["officers"].append(payload["officers"][0])
    operation_payload(payload, "OFFICERS")["record_count"] = 2

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_record_operation_provenance_mismatch_is_rejected_directly() -> None:
    payload = direct_bundle_payload()
    payload["officers"][0]["provenance"]["operation"] = "RELATIONSHIPS"

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_record_timestamp_provenance_mismatch_is_rejected_directly() -> None:
    payload = direct_bundle_payload()
    payload["officers"][0]["provenance"]["retrieved_at"] = (
        NOW + timedelta(seconds=1)
    ).isoformat()

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_operation_environment_mismatch_is_rejected_directly() -> None:
    payload = direct_bundle_payload()
    officer_result = operation_payload(payload, "OFFICERS")
    officer_result["provenance"]["environment"] = "SANDBOX"
    payload["officers"][0]["provenance"]["environment"] = "SANDBOX"

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_bundle_timestamp_mismatch_is_rejected_directly() -> None:
    payload = direct_bundle_payload()
    payload["retrieved_at"] = (NOW + timedelta(seconds=1)).isoformat()

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_entity_identity_mismatch_is_rejected_directly() -> None:
    payload = direct_bundle_payload()
    payload["entity_profile"]["registration_number"] = "202400002B"

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_entity_profile_noncomplete_status_is_rejected_directly() -> None:
    payload = direct_bundle_payload()
    entity_result = operation_payload(payload, "ENTITY_PROFILE")
    entity_result.update(
        status="FAILED",
        record_count=0,
        error=technical_issue(),
    )
    payload["status"] = "FAILED"
    payload["issues"] = [technical_issue()]

    with pytest.raises(ValidationError):
        RegistryAcquisitionBundle.model_validate(payload)


def test_browser_projection_is_bounded_truthful_and_endpoint_free() -> None:
    service, connector = build_service()
    client = TestClient(
        create_app(
            Settings(app_env="test", demo_controls_enabled=True),
            onboarding_service=service,
        )
    )

    response = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})

    assert response.status_code == 201
    acquisition = response.json()["case"]["registry_acquisition"]
    assert acquisition["status"] == "COMPLETE"
    actual_operations = [
        (item["operation"], item["status"], item["record_count"])
        for item in acquisition["operation_results"]
    ]
    assert actual_operations == [
        ("ENTITY_PROFILE", "COMPLETE", 1),
        ("OFFICERS", "COMPLETE", 1),
        ("OWNERSHIP_PARTIES", "COMPLETE", 2),
        ("RELATIONSHIPS", "COMPLETE", 2),
    ]
    serialized = response.text
    assert "source_endpoint" not in serialized
    assert "mock.acra.gov.sg" not in serialized
    assert "authorization" not in serialized.casefold()
    assert connector.calls == {key: 1 for key in connector.calls}


def test_partial_identity_can_continue_but_failed_acquisition_stops() -> None:
    service, _ = build_service()
    client = TestClient(
        create_app(
            Settings(app_env="test", demo_controls_enabled=True),
            onboarding_service=service,
        )
    )

    partial = client.post(
        "/api/clm/zero-touch/cases", json={"uen": MISSING_OWNERSHIP_UEN}
    ).json()
    failed = client.post(
        "/api/clm/zero-touch/cases", json={"uen": FAILED_RELATIONSHIPS_UEN}
    ).json()

    assert partial["status"] == "PENDING_INPUTS"
    assert partial["current_stage"] == "DOCUMENT"
    assert partial["case"]["error"] is None
    assert "REGISTRY_NOT_READY" not in partial["clm"]["readiness"]["blockers"]
    assert "OWNERSHIP_REQUIRED" in partial["clm"]["readiness"]["blockers"]
    assert failed["status"] == "TECHNICAL_FAILURE"
    assert failed["technical_failure"]["code"] == "REGISTRY_OPERATION_UNAVAILABLE"
    for payload in (partial, failed):
        case_id = payload["case"]["case_id"]
        documents = client.get(f"/api/onboarding/cases/{case_id}/documents")
        ownership = client.get(f"/api/onboarding/cases/{case_id}/ownership")
        assert documents.status_code == 200 and documents.json() == []
        assert ownership.status_code == 404
        assert all(
            item["status"] == "NOT_ATTEMPTED"
            for item in payload["target_operations"]
            if item["operation"] != "SEARCH"
        )
