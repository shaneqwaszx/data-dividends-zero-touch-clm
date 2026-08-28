from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.connectors.acra import AcraCompanyPayload
from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.connectors.registry import (
    AcraIdentifierNotEligibleError,
    AcraRegistryProviderAdapter,
    RegistryProvider,
    RegistryProviderRouter,
)
from app.domain.jurisdiction import (
    JurisdictionCode,
    JurisdictionObservation,
    JurisdictionObservationSource,
    JurisdictionResolution,
    JurisdictionResolutionStatus,
    JurisdictionResolver,
    RegistryProviderCode,
    RegistryRoutingDecision,
    RegistryRoutingStatus,
    is_eligible_singapore_uen,
)
from app.domain.models import CanonicalLegalEntity
from app.main import create_app
from app.services.onboarding import OnboardingService
from app.services.repository import InMemoryOnboardingCaseRepository

NOW = datetime(2026, 8, 28, 1, 0, tzinfo=UTC)
PDF = b"%PDF-1.4\nSYNTHETIC PHASE 09\n%%EOF"


def observation(
    jurisdiction: JurisdictionCode,
    source: JurisdictionObservationSource,
) -> JurisdictionObservation:
    return JurisdictionObservation(
        jurisdiction=jurisdiction,
        source=source,
        observed_at=NOW,
        source_reference=f"test:{source.value.lower()}",
    )


def test_resolver_returns_unresolved_without_observations() -> None:
    result = JurisdictionResolver().resolve((), resolved_at=NOW)

    assert result.status == JurisdictionResolutionStatus.UNRESOLVED
    assert result.resolved_jurisdiction is None
    assert result.observations == ()


def test_resolver_retains_one_observation_and_resolves_it() -> None:
    item = observation(
        JurisdictionCode.SINGAPORE, JurisdictionObservationSource.USER_INPUT
    )

    result = JurisdictionResolver().resolve((item,), resolved_at=NOW)

    assert result.status == JurisdictionResolutionStatus.RESOLVED
    assert result.resolved_jurisdiction == JurisdictionCode.SINGAPORE
    assert result.observations == (item,)


def test_resolver_retains_agreeing_observations_without_source_precedence() -> None:
    items = (
        observation(
            JurisdictionCode.SINGAPORE,
            JurisdictionObservationSource.USER_INPUT,
        ),
        observation(
            JurisdictionCode.SINGAPORE,
            JurisdictionObservationSource.IDENTIFIER_FORMAT,
        ),
    )

    result = JurisdictionResolver().resolve(items, resolved_at=NOW)

    assert result.status == JurisdictionResolutionStatus.RESOLVED
    assert result.resolved_jurisdiction == JurisdictionCode.SINGAPORE
    assert result.observations == items


def test_resolver_returns_conflict_and_does_not_select_a_winner() -> None:
    items = (
        observation(
            JurisdictionCode.AUSTRALIA,
            JurisdictionObservationSource.USER_INPUT,
        ),
        observation(
            JurisdictionCode.SINGAPORE,
            JurisdictionObservationSource.IDENTIFIER_FORMAT,
        ),
    )

    result = JurisdictionResolver().resolve(items, resolved_at=NOW)

    assert result.status == JurisdictionResolutionStatus.CONFLICT
    assert result.resolved_jurisdiction is None
    assert result.observations == items


@pytest.mark.parametrize(
    ("status", "resolved_jurisdiction", "observations"),
    (
        (
            JurisdictionResolutionStatus.RESOLVED,
            JurisdictionCode.SINGAPORE,
            (observation(JurisdictionCode.AUSTRALIA, JurisdictionObservationSource.USER_INPUT),),
        ),
        (
            JurisdictionResolutionStatus.RESOLVED,
            JurisdictionCode.SINGAPORE,
            (
                observation(JurisdictionCode.SINGAPORE, JurisdictionObservationSource.USER_INPUT),
                observation(
                    JurisdictionCode.AUSTRALIA,
                    JurisdictionObservationSource.IDENTIFIER_FORMAT,
                ),
            ),
        ),
        (JurisdictionResolutionStatus.RESOLVED, JurisdictionCode.SINGAPORE, ()),
        (
            JurisdictionResolutionStatus.UNRESOLVED,
            None,
            (observation(JurisdictionCode.SINGAPORE, JurisdictionObservationSource.USER_INPUT),),
        ),
        (
            JurisdictionResolutionStatus.CONFLICT,
            None,
            (observation(JurisdictionCode.SINGAPORE, JurisdictionObservationSource.USER_INPUT),),
        ),
        (
            JurisdictionResolutionStatus.CONFLICT,
            None,
            (
                observation(JurisdictionCode.SINGAPORE, JurisdictionObservationSource.USER_INPUT),
                observation(
                    JurisdictionCode.SINGAPORE,
                    JurisdictionObservationSource.IDENTIFIER_FORMAT,
                ),
            ),
        ),
    ),
)
def test_jurisdiction_resolution_rejects_contradictory_direct_construction(
    status: JurisdictionResolutionStatus,
    resolved_jurisdiction: JurisdictionCode | None,
    observations: tuple[JurisdictionObservation, ...],
) -> None:
    with pytest.raises(ValidationError):
        JurisdictionResolution(
            status=status,
            resolved_jurisdiction=resolved_jurisdiction,
            observations=observations,
            resolved_at=NOW,
        )


def test_jurisdiction_resolution_accepts_each_valid_state_directly() -> None:
    sg = observation(JurisdictionCode.SINGAPORE, JurisdictionObservationSource.USER_INPUT)
    au = observation(JurisdictionCode.AUSTRALIA, JurisdictionObservationSource.IDENTIFIER_FORMAT)

    resolved = JurisdictionResolution(
        status=JurisdictionResolutionStatus.RESOLVED,
        resolved_jurisdiction=JurisdictionCode.SINGAPORE,
        observations=(sg,),
        resolved_at=NOW,
    )
    unresolved = JurisdictionResolution(
        status=JurisdictionResolutionStatus.UNRESOLVED,
        observations=(),
        resolved_at=NOW,
    )
    conflict = JurisdictionResolution(
        status=JurisdictionResolutionStatus.CONFLICT,
        observations=(sg, au),
        resolved_at=NOW,
    )

    assert resolved.status == JurisdictionResolutionStatus.RESOLVED
    assert unresolved.status == JurisdictionResolutionStatus.UNRESOLVED
    assert conflict.status == JurisdictionResolutionStatus.CONFLICT


class _StubRegistryProvider:
    provider_code = RegistryProviderCode.ACRA

    def retrieve_company(self, identifier: str) -> CanonicalLegalEntity | None:
        del identifier
        return None


def test_router_selects_acra_only_for_singapore() -> None:
    provider: RegistryProvider = _StubRegistryProvider()
    router = RegistryProviderRouter(provider)

    decision, selected = router.route(JurisdictionCode.SINGAPORE, decided_at=NOW)

    assert decision.status == RegistryRoutingStatus.SELECTED
    assert decision.provider == RegistryProviderCode.ACRA
    assert selected is provider


def test_router_recognises_foreign_jurisdictions_without_a_provider() -> None:
    router = RegistryProviderRouter(_StubRegistryProvider())

    for jurisdiction in (
        JurisdictionCode.AUSTRALIA,
        JurisdictionCode.MALAYSIA,
        JurisdictionCode.HONG_KONG,
    ):
        decision, selected = router.route(jurisdiction, decided_at=NOW)
        assert decision.status == RegistryRoutingStatus.PROVIDER_NOT_IMPLEMENTED
        assert decision.provider is None
        assert selected is None


@pytest.mark.parametrize(
    ("status", "jurisdiction", "provider"),
    (
        (
            RegistryRoutingStatus.SELECTED,
            JurisdictionCode.AUSTRALIA,
            RegistryProviderCode.ACRA,
        ),
        (RegistryRoutingStatus.SELECTED, JurisdictionCode.SINGAPORE, None),
        (
            RegistryRoutingStatus.PROVIDER_NOT_IMPLEMENTED,
            JurisdictionCode.SINGAPORE,
            None,
        ),
        (
            RegistryRoutingStatus.PROVIDER_NOT_IMPLEMENTED,
            JurisdictionCode.AUSTRALIA,
            RegistryProviderCode.ACRA,
        ),
    ),
)
def test_registry_route_rejects_contradictory_direct_construction(
    status: RegistryRoutingStatus,
    jurisdiction: JurisdictionCode,
    provider: RegistryProviderCode | None,
) -> None:
    with pytest.raises(ValidationError):
        RegistryRoutingDecision(
            status=status,
            jurisdiction=jurisdiction,
            provider=provider,
            decided_at=NOW,
        )


def test_registry_route_accepts_current_bounded_contract_directly() -> None:
    selected = RegistryRoutingDecision(
        status=RegistryRoutingStatus.SELECTED,
        jurisdiction=JurisdictionCode.SINGAPORE,
        provider=RegistryProviderCode.ACRA,
        decided_at=NOW,
    )
    unsupported = tuple(
        RegistryRoutingDecision(
            status=RegistryRoutingStatus.PROVIDER_NOT_IMPLEMENTED,
            jurisdiction=jurisdiction,
            decided_at=NOW,
        )
        for jurisdiction in (
            JurisdictionCode.AUSTRALIA,
            JurisdictionCode.MALAYSIA,
            JurisdictionCode.HONG_KONG,
        )
    )

    assert selected.provider == RegistryProviderCode.ACRA
    assert all(decision.provider is None for decision in unsupported)


class _CountingAcra:
    calls: list[str]

    def __init__(self) -> None:
        self.calls = []
        self._delegate = MockAcraConnector(clock=lambda: NOW)

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        self.calls.append(uen)
        return self._delegate.fetch_company(uen)


def build_service() -> tuple[OnboardingService, _CountingAcra]:
    acra = _CountingAcra()
    onboarding = OnboardingService(
        acra=acra,
        goldtier=MockGoldTierConnector(),
        repository=InMemoryOnboardingCaseRepository(),
        clock=lambda: NOW,
    )
    return onboarding, acra


def build_client() -> tuple[TestClient, _CountingAcra]:
    onboarding, acra = build_service()
    application = create_app(
        Settings(app_env="test", demo_controls_enabled=True),
        onboarding_service=onboarding,
    )
    return TestClient(application), acra


@pytest.mark.parametrize(
    ("identifier", "eligible"),
    (
        ("000000000A", True),
        ("202400001A", True),
        ("20240001A", False),
        ("2024000001A", False),
        ("202400001", False),
        ("202400001AA", False),
        ("202400001a", False),
        ("AU-REG-123", False),
    ),
)
def test_singapore_uen_eligibility_boundaries(identifier: str, eligible: bool) -> None:
    assert is_eligible_singapore_uen(identifier) is eligible


def test_omitted_country_preserves_singapore_uen_compatibility_with_provenance() -> None:
    client, acra = build_client()

    response = client.post(
        "/api/clm/zero-touch/cases", json={"uen": "202400001A"}
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "PENDING_INPUTS"
    assert payload["case"]["jurisdiction_resolution"]["status"] == "RESOLVED"
    assert payload["case"]["jurisdiction_resolution"]["resolved_jurisdiction"] == "SG"
    assert payload["case"]["jurisdiction_resolution"]["observations"] == [
        {
            "jurisdiction": "SG",
            "source": "IDENTIFIER_FORMAT",
            "observed_at": "2026-08-28T01:00:00Z",
            "evidence_reference": "request.uen:accepted_sg_format",
            "confidence": None,
        }
    ]
    assert payload["case"]["registry_route"]["provider"] == "ACRA"
    assert acra.calls == ["202400001A"]


def test_explicit_singapore_and_identifier_inference_agree() -> None:
    client, acra = build_client()

    response = client.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "202400001A", "country_of_incorporation": "SG"},
    )

    observations = response.json()["case"]["jurisdiction_resolution"]["observations"]
    assert response.status_code == 201
    assert [item["source"] for item in observations] == [
        "USER_INPUT",
        "IDENTIFIER_FORMAT",
    ]
    assert {item["jurisdiction"] for item in observations} == {"SG"}
    assert acra.calls == ["202400001A"]


@pytest.mark.parametrize("identifier", ("AU-REG-123", "BAD-ID", "123"))
def test_explicit_singapore_ineligible_identifier_stops_all_calls(
    identifier: str,
) -> None:
    client, acra = build_client()

    response = client.post(
        "/api/clm/zero-touch/cases",
        json={"uen": identifier, "country_of_incorporation": "SG"},
    )

    assert response.status_code == 201
    payload = response.json()
    case_id = payload["case"]["case_id"]
    attached = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/documents",
        content=PDF,
        headers={
            "Content-Type": "application/pdf",
            "X-Document-Name": "synthetic.pdf",
        },
    )
    documents = client.get(f"/api/onboarding/cases/{case_id}/documents")
    ownership = client.get(f"/api/onboarding/cases/{case_id}/ownership")

    assert payload["status"] == "WAITING_FOR_REVIEW"
    assert payload["current_stage"] == "REGISTRY"
    assert payload["case"]["error"]["code"] == "REGISTRY_IDENTIFIER_NOT_ELIGIBLE"
    assert payload["case"]["registry_route"]["status"] == "SELECTED"
    assert payload["case"]["registry_route"]["provider"] == "ACRA"
    assert (
        payload["active_exceptions"][0]["exception_type"]
        == "REGISTRY_IDENTIFIER_NOT_ELIGIBLE"
    )
    assert payload["active_exceptions"][0]["available_actions"] == []
    assert attached.status_code == 200
    assert attached.json()["case"] == payload["case"]
    assert documents.status_code == 200 and documents.json() == []
    assert ownership.status_code == 404
    assert {item["status"] for item in payload["target_operations"]} == {
        "NOT_ATTEMPTED"
    }
    assert acra.calls == []


def test_direct_service_rejects_ineligible_singapore_identifier_before_acra() -> None:
    onboarding, acra = build_service()

    case = onboarding.create_staged_case("BAD-ID", JurisdictionCode.SINGAPORE)

    assert case.state.value == "REVIEW_REQUIRED"
    assert case.error is not None
    assert case.error.code == "REGISTRY_IDENTIFIER_NOT_ELIGIBLE"
    assert acra.calls == []


def test_acra_adapter_rejects_ineligible_identifier_before_connector() -> None:
    acra = _CountingAcra()
    adapter = AcraRegistryProviderAdapter(acra)

    with pytest.raises(AcraIdentifierNotEligibleError):
        adapter.retrieve_company("BAD-ID")

    assert acra.calls == []


def test_explicit_foreign_country_conflicts_with_singapore_identifier_and_stops() -> None:
    client, acra = build_client()

    response = client.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "202400001A", "country_of_incorporation": "AU"},
    )

    payload = response.json()
    assert response.status_code == 201
    assert payload["status"] == "WAITING_FOR_REVIEW"
    assert payload["current_stage"] == "REGISTRY"
    assert payload["case"]["error"]["code"] == "JURISDICTION_CONFLICT"
    assert payload["case"]["registry_route"] is None
    assert payload["active_exceptions"][0]["blocker_code"] == "JURISDICTION_CONFLICT"
    assert payload["active_exceptions"][0]["available_actions"] == []
    assert acra.calls == []
    assert {item["status"] for item in payload["target_operations"]} == {
        "NOT_ATTEMPTED"
    }


def test_recognised_non_singapore_country_stops_as_provider_not_implemented() -> None:
    client, acra = build_client()

    response = client.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "AU-REG-123", "country_of_incorporation": "AU"},
    )

    payload = response.json()
    assert response.status_code == 201
    assert payload["status"] == "WAITING_FOR_REVIEW"
    assert payload["case"]["error"]["code"] == "REGISTRY_PROVIDER_NOT_IMPLEMENTED"
    assert payload["case"]["registry_route"] == {
        "status": "PROVIDER_NOT_IMPLEMENTED",
        "jurisdiction": "AU",
        "provider": None,
        "decided_at": "2026-08-28T01:00:00Z",
    }
    assert acra.calls == []
    assert {item["status"] for item in payload["target_operations"]} == {
        "NOT_ATTEMPTED"
    }


def test_unknown_jurisdiction_stops_before_provider_and_remains_retrievable() -> None:
    client, acra = build_client()

    created = client.post(
        "/api/clm/zero-touch/cases", json={"uen": "UNKNOWN-123"}
    )
    payload = created.json()
    case_id = payload["case"]["case_id"]
    fetched = client.get(f"/api/clm/zero-touch/cases/{case_id}")

    assert created.status_code == 201
    assert fetched.status_code == 200
    assert fetched.json()["case"] == payload["case"]
    assert fetched.json()["status"] == payload["status"]
    assert fetched.json()["active_exceptions"] == payload["active_exceptions"]
    assert payload["case"]["error"]["code"] == "JURISDICTION_UNRESOLVED"
    assert payload["case"]["jurisdiction_resolution"]["observations"] == []
    assert payload["case"]["registry_route"] is None
    assert acra.calls == []


def test_registry_blocker_refuses_document_processing_and_downstream_calls() -> None:
    client, acra = build_client()
    created = client.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "MY-REG-123", "country_of_incorporation": "MY"},
    ).json()
    case_id = created["case"]["case_id"]

    attached = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/documents",
        content=PDF,
        headers={
            "Content-Type": "application/pdf",
            "X-Document-Name": "synthetic.pdf",
        },
    )
    documents = client.get(f"/api/onboarding/cases/{case_id}/documents")
    ownership = client.get(f"/api/onboarding/cases/{case_id}/ownership")

    assert attached.status_code == 200
    assert attached.json()["case"] == created["case"]
    assert attached.json()["status"] == created["status"]
    assert attached.json()["active_exceptions"] == created["active_exceptions"]
    assert documents.status_code == 200 and documents.json() == []
    assert ownership.status_code == 404
    assert {item["status"] for item in attached.json()["target_operations"]} == {
        "NOT_ATTEMPTED"
    }
    assert acra.calls == []


def test_unknown_country_code_is_rejected_at_the_api_boundary() -> None:
    client, acra = build_client()

    response = client.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "NZ-REG-123", "country_of_incorporation": "NZ"},
    )

    assert response.status_code == 422
    assert acra.calls == []


def test_acra_adapter_preserves_current_canonical_profile_mapping() -> None:
    adapter = AcraRegistryProviderAdapter(MockAcraConnector(clock=lambda: NOW))

    entity = adapter.retrieve_company("202400001A")

    assert entity is not None
    assert entity.registration_number == "202400001A"
    assert entity.legal_name == "MERLION CIRCULAR LABS PTE. LTD."
    assert entity.country_of_incorporation == "SG"
    assert entity.entity_status == "LIVE"
    assert entity.registered_address is not None
    assert entity.registered_address.postal_code == "018956"
    assert entity.source.source_system.value == "ACRA"
    assert entity.source.environment.value == "MOCK"
