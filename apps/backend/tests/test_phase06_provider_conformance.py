"""Reusable Phase 06 adapter expectations proven against current Mock providers."""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.connectors.acra import AcraAddressPayload, AcraCompanyPayload
from app.connectors.goldtier_models import (
    GoldTierOperationResult,
    GoldTierOutcome,
    GoldTierRequestMetadata,
    GoldTierSearchOutcome,
    GoldTierSearchResult,
    SearchPartyRequest,
)
from app.connectors.idp import (
    IdpDocumentInput,
    IdpProcessingError,
    IdpProviderMetadata,
    IdpSourceField,
    IdpSourceResult,
)
from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.connectors.mock_idp import MockIdpProvider, MockIdpScenario
from app.connectors.mock_ownership import MockOwnershipProvider, MockOwnershipScenario
from app.connectors.ownership import (
    OwnershipProviderError,
    OwnershipProviderMetadata,
    OwnershipProviderRequest,
    OwnershipSourceResult,
)
from app.domain.documents import DocumentFieldKey, DocumentProfile, IdpEnvironment
from app.domain.ownership import (
    OwnershipEnvironment,
    OwnershipProvenance,
    OwnershipRelationship,
    Party,
    PartyType,
)
from app.services.clm_orchestration import ClmOrchestrationService
from app.services.clm_repository import InMemoryClmOrchestrationRepository
from app.services.document_processing import DocumentProcessingService
from app.services.document_repository import InMemoryDocumentProcessingRepository
from app.services.onboarding import OnboardingService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_repository import InMemoryOwnershipAnalysisRepository
from app.services.repository import InMemoryOnboardingCaseRepository
from app.services.zero_touch_orchestration import ZeroTouchOrchestrator
from app.services.zero_touch_repository import InMemoryZeroTouchAutomationRepository


def assert_registry_adapter_conformance(adapter: object) -> None:
    company = adapter.fetch_company("202400001A")  # type: ignore[attr-defined]
    assert company is not None
    assert company.uen == "202400001A"
    assert company.source_environment == "MOCK"
    assert company.source_endpoint.startswith("https://")
    assert company.retrieved_at.tzinfo is not None
    assert adapter.fetch_company("999999999Z") is None  # type: ignore[attr-defined]


def assert_idp_adapter_conformance(adapter: MockIdpProvider) -> IdpSourceResult:
    result = IdpSourceResult.model_validate(
        adapter.process(
            IdpDocumentInput(
                profile=DocumentProfile.PROVISIONAL_CORPORATE,
                content=b"%PDF-1.4\nSYNTHETIC\n%%EOF",
            )
        )
    )
    assert {field.field_key for field in result.fields} == set(DocumentFieldKey)
    assert adapter.metadata.environment == "MOCK"  # type: ignore[union-attr]
    return result


def assert_ownership_adapter_conformance(
    adapter: MockOwnershipProvider,
) -> object:
    result = adapter.load(
        OwnershipProviderRequest(
            case_id=uuid4(),
            registration_number="202400001A",
            display_name="SYNTHETIC COMPANY PTE. LTD.",
        )
    )
    assert result.root_party_id == "ROOT_ENTITY"  # type: ignore[union-attr]
    assert adapter.metadata.environment == OwnershipEnvironment.MOCK  # type: ignore[union-attr]
    return result


def test_mock_registry_proves_valid_not_found_and_provenance_contract() -> None:
    assert_registry_adapter_conformance(
        MockAcraConnector(clock=lambda: datetime(2026, 8, 12, tzinfo=UTC))
    )


@pytest.mark.parametrize(
    "scenario",
    [
        MockIdpScenario.ALL_FIELDS_MATCH,
        MockIdpScenario.LOW_CONFIDENCE,
        MockIdpScenario.MISSING_FIELD,
    ],
)
def test_mock_idp_proves_clean_low_confidence_and_missing_contract(
    scenario: MockIdpScenario,
) -> None:
    result = assert_idp_adapter_conformance(MockIdpProvider(scenario))
    if scenario == MockIdpScenario.LOW_CONFIDENCE:
        assert min(field.confidence for field in result.fields) < 0.85
    if scenario == MockIdpScenario.MISSING_FIELD:
        assert any(field.value is None for field in result.fields)


def test_mock_idp_proves_controlled_processing_failure_contract() -> None:
    with pytest.raises(IdpProcessingError):
        assert_idp_adapter_conformance(MockIdpProvider(MockIdpScenario.PROCESSOR_FAILURE))


@pytest.mark.parametrize(
    "scenario",
    [
        MockOwnershipScenario.DIRECT_OWNER,
        MockOwnershipScenario.INCOMPLETE_CHAIN,
        MockOwnershipScenario.CYCLE,
    ],
)
def test_mock_ownership_proves_definitive_and_indeterminate_graph_contract(
    scenario: MockOwnershipScenario,
) -> None:
    result = assert_ownership_adapter_conformance(MockOwnershipProvider(scenario))
    assert len(result.parties) > 0  # type: ignore[union-attr]


def test_mock_ownership_proves_controlled_provider_failure_contract() -> None:
    with pytest.raises(OwnershipProviderError):
        assert_ownership_adapter_conformance(
            MockOwnershipProvider(MockOwnershipScenario.PROVIDER_FAILURE)
        )


def test_mock_goldtier_exposes_explicit_no_match_and_existing_party_outcomes() -> None:
    connector = MockGoldTierConnector(match_found_external_keys=frozenset({"202400005E"}))
    metadata = GoldTierRequestMetadata(
        correlation_id=uuid4(), source_case_id="synthetic-case", idempotency_key=uuid4()
    )
    no_match = connector.search_party(
        SearchPartyRequest(registration_number="202400001A"), metadata
    )
    existing = connector.search_party(
        SearchPartyRequest(registration_number="202400005E"), metadata
    )
    assert no_match.outcome == GoldTierSearchOutcome.NO_MATCH
    assert no_match.matched_party_id is None
    assert existing.outcome == GoldTierSearchOutcome.MATCH_FOUND
    assert existing.matched_party_id == "GT-MOCK-EXISTING-202400005E"


class LocalRegistryAdapter:
    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        if uen != "202400001A":
            return None
        return AcraCompanyPayload(
            uen=uen,
            entity_name="MERLION CIRCULAR LABS PTE. LTD.",
            country_code="SG",
            entity_type="PRIVATE_COMPANY_LIMITED_BY_SHARES",
            registration_date=date(2024, 1, 2),
            entity_status="LIVE",
            registered_address=AcraAddressPayload(
                block="18",
                street="INNOVATION WAY",
                unit="#04-01",
                postal_code="018956",
                country_code="SG",
            ),
            source_environment="SANDBOX",
            source_endpoint="https://local.invalid/business-profile/202400001A",
            retrieved_at=datetime(2026, 8, 12, tzinfo=UTC),
        )


def _local_registry_payload(*, uen: str = "202400001A") -> AcraCompanyPayload:
    return AcraCompanyPayload(
        uen=uen,
        entity_name="MERLION CIRCULAR LABS PTE. LTD.",
        country_code="SG",
        entity_type="PRIVATE_COMPANY_LIMITED_BY_SHARES",
        registration_date=date(2024, 1, 2),
        entity_status="LIVE",
        registered_address=AcraAddressPayload(
            block="18",
            street="INNOVATION WAY",
            unit="#04-01",
            postal_code="018956",
            country_code="SG",
        ),
        source_environment="SANDBOX",
        source_endpoint=f"https://local.invalid/business-profile/{uen}",
        retrieved_at=datetime(2026, 8, 12, tzinfo=UTC),
    )


class StaticRegistryAdapter:
    def __init__(self, payload: object | None) -> None:
        self.payload = payload

    def fetch_company(self, uen: str) -> object | None:
        return self.payload


class LocalIdpAdapter:
    metadata = IdpProviderMetadata(provider_name="LOCAL_IDP", environment=IdpEnvironment.SANDBOX)

    def process(self, document: IdpDocumentInput) -> IdpSourceResult:
        values = {
            DocumentFieldKey.LEGAL_NAME: "MERLION CIRCULAR LABS PTE. LTD.",
            DocumentFieldKey.REGISTRATION_NUMBER: "202400001A",
            DocumentFieldKey.COUNTRY_OF_INCORPORATION: "SG",
            DocumentFieldKey.REGISTERED_ADDRESS: "18 INNOVATION WAY, #04-01, 018956, SG",
        }
        return IdpSourceResult(
            profile=document.profile,
            fields=[
                IdpSourceField(
                    field_key=key,
                    value=value,
                    confidence=Decimal("0.99"),
                    page_number=1,
                    source_reference=f"local:{key.value}:1",
                )
                for key, value in values.items()
            ],
        )


class LocalOwnershipAdapter:
    metadata = OwnershipProviderMetadata(
        provider_name="LOCAL_OWNERSHIP", environment=OwnershipEnvironment.SANDBOX
    )

    def load(self, request: OwnershipProviderRequest) -> OwnershipSourceResult:
        provenance = OwnershipProvenance(
            provider="LOCAL_OWNERSHIP",
            environment=OwnershipEnvironment.SANDBOX,
            source_reference="local-ownership-v1",
            sourced_at=datetime(2026, 8, 12, tzinfo=UTC),
        )
        return OwnershipSourceResult(
            root_party_id="LOCAL_ROOT",
            parties=[
                Party(
                    party_id="LOCAL_ROOT",
                    display_name=request.display_name,
                    party_type=PartyType.LEGAL_ENTITY,
                    registration_number=request.registration_number,
                    country="SG",
                ),
                Party(
                    party_id="LOCAL_OWNER",
                    display_name="Synthetic Local Owner",
                    party_type=PartyType.NATURAL_PERSON,
                    country="SG",
                ),
            ],
            relationships=[
                OwnershipRelationship(
                    relationship_id="LOCAL_REL_1",
                    parent_party_id="LOCAL_ROOT",
                    child_party_id="LOCAL_OWNER",
                    ownership_percent=Decimal("30"),
                    provenance=provenance,
                )
            ],
        )


class LocalTargetAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def search_party(self, request: Any, metadata: Any) -> GoldTierSearchResult:
        self.calls.append("search")
        return GoldTierSearchResult(
            outcome=GoldTierSearchOutcome.NO_MATCH,
            status_code=200,
            message="Local contract stub found no existing party.",
        )

    def create_shell_customer(self, request: Any, metadata: Any) -> GoldTierOperationResult:
        self.calls.append("shell")
        return GoldTierOperationResult(
            outcome=GoldTierOutcome.SUCCESS,
            status_code=201,
            party_id="LOCAL-PARTY-1",
            status="SHELL_CREATED",
            message="Local contract stub created a shell.",
        )

    def create_policy(self, request: Any, metadata: Any) -> GoldTierOperationResult:
        self.calls.append("policy")
        return GoldTierOperationResult(
            outcome=GoldTierOutcome.SUCCESS,
            status_code=201,
            party_id="LOCAL-PARTY-1",
            policy_id="LOCAL-POLICY-1",
            status="POLICY_CREATED",
            message="Local contract stub created a policy.",
        )

    def amend_party(self, party_id: str, request: Any, metadata: Any) -> GoldTierOperationResult:
        self.calls.append("amend")
        return GoldTierOperationResult(
            outcome=GoldTierOutcome.SUCCESS,
            status_code=200,
            party_id=party_id,
            status="ENRICHED",
            message="Local contract stub amended the party.",
        )


def _build_local_zero(registry: object) -> tuple[ZeroTouchOrchestrator, LocalTargetAdapter]:
    target = LocalTargetAdapter()
    cases = OnboardingService(
        acra=registry,  # type: ignore[arg-type]
        goldtier=target,
        repository=InMemoryOnboardingCaseRepository(),
    )
    documents = DocumentProcessingService(
        cases=cases,
        idp=LocalIdpAdapter(),
        repository=InMemoryDocumentProcessingRepository(),
        max_upload_bytes=1024,
        review_confidence_threshold=0.85,
    )
    ownership = OwnershipAnalysisService(
        cases=cases,
        provider=LocalOwnershipAdapter(),
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
    return (
        ZeroTouchOrchestrator(
            cases=cases,
            documents=documents,
            ownership=ownership,
            clm=clm,
            repository=InMemoryZeroTouchAutomationRepository(),
        ),
        target,
    )


def _assert_registry_contract_failure(payload: object, expected_code: str) -> None:
    zero, target = _build_local_zero(StaticRegistryAdapter(payload))
    failed = zero.create_case("202400001A")
    assert failed.status == "TECHNICAL_FAILURE"
    assert failed.current_stage == "REGISTRY"
    assert failed.completed_stages == ()
    assert failed.technical_failure is not None
    assert failed.technical_failure.code == expected_code
    assert failed.metrics.human_interventions == 0
    case = zero._cases.get_case(failed.case_id)  # noqa: SLF001
    assert case is not None and case.entity is None
    assert zero._documents.list_documents(case_id=failed.case_id) == []  # noqa: SLF001
    assert zero._ownership.get(case_id=failed.case_id) is None  # noqa: SLF001
    clm = zero._clm.get(case_id=failed.case_id)  # noqa: SLF001
    assert clm is not None
    assert all(event.event_type != "READINESS_EVALUATED" for event in clm.events)
    source_endpoint = getattr(payload, "source_endpoint", None)
    if isinstance(source_endpoint, str):
        assert source_endpoint not in failed.model_dump_json()
    assert target.calls == []


ACRA_TEXT_FIELD_PATHS = (
    ("uen",),
    ("entity_name",),
    ("entity_status",),
    ("entity_type",),
    ("country_code",),
    ("source_environment",),
    ("source_endpoint",),
    ("registered_address", "block"),
    ("registered_address", "street"),
    ("registered_address", "unit"),
    ("registered_address", "building_name"),
    ("registered_address", "postal_code"),
    ("registered_address", "country_code"),
)


def _raw_registry_payload_with_control(
    field_path: tuple[str, ...], control: str, position: str
) -> dict[str, object]:
    payload = _local_registry_payload().model_dump(mode="json")
    target: dict[str, object] = payload
    for segment in field_path[:-1]:
        nested = target[segment]
        assert isinstance(nested, dict)
        target = nested
    field_name = field_path[-1]
    original = target[field_name]
    if original is None:
        original = "SYNTHETIC CENTRE"
    assert isinstance(original, str)
    if position == "leading":
        target[field_name] = f"{control}{original}"
    elif position == "trailing":
        target[field_name] = f"{original}{control}"
    else:
        midpoint = max(1, len(original) // 2)
        target[field_name] = f"{original[:midpoint]}{control}{original[midpoint:]}"
    return payload


@pytest.mark.parametrize(
    "field_path", ACRA_TEXT_FIELD_PATHS, ids=lambda path: ".".join(path)
)
@pytest.mark.parametrize("control", ["\n", "\r", "\t"], ids=["lf", "cr", "tab"])
@pytest.mark.parametrize("position", ["leading", "trailing", "embedded"])
def test_P06_QG_009_R2_ALL_ACRA_TEXT_CONTROLS_FAIL_CLOSED(
    field_path: tuple[str, ...], control: str, position: str
) -> None:
    _assert_registry_contract_failure(
        _raw_registry_payload_with_control(field_path, control, position),
        "ACRA_RESPONSE_INVALID",
    )


def test_P06_QG_009_R2_EXACT_TRAILING_LF_FULL_FLOW_BYPASS() -> None:
    payload = AcraCompanyPayload.model_construct(
        **_raw_registry_payload_with_control(("entity_name",), "\n", "trailing")
    )
    _assert_registry_contract_failure(payload, "ACRA_RESPONSE_INVALID")


def test_P06_QG_009_R2_RAW_PROVIDER_RESULT_REJECTED() -> None:
    payload = _raw_registry_payload_with_control(("entity_name",), "\n", "trailing")
    _assert_registry_contract_failure(payload, "ACRA_RESPONSE_INVALID")


def test_P06_QG_009_R2_MUTATED_TYPED_DTO_REJECTED() -> None:
    payload = _local_registry_payload()
    object.__setattr__(
        payload, "entity_name", "MERLION CIRCULAR LABS PTE. LTD.\n"
    )
    _assert_registry_contract_failure(payload, "ACRA_RESPONSE_INVALID")


def test_P06_QG_009_R2_ORDINARY_TYPED_CONSTRUCTION_REJECTED() -> None:
    payload = _local_registry_payload().model_dump(mode="json")
    payload["entity_name"] = "MERLION CIRCULAR LABS PTE. LTD.\n"
    with pytest.raises(ValidationError, match="control characters"):
        AcraCompanyPayload.model_validate(payload)


def test_P06_QG_009_R2_ORDINARY_SPACES_NORMALIZE_AND_COMPLETE() -> None:
    payload = _local_registry_payload().model_dump(mode="json")
    payload["uen"] = "  202400001A  "
    payload["entity_name"] = "  MERLION CIRCULAR LABS PTE. LTD.  "
    payload["entity_status"] = "  LIVE  "
    payload["entity_type"] = "  PRIVATE_COMPANY_LIMITED_BY_SHARES  "
    payload["country_code"] = "  SG  "
    payload["source_environment"] = "  SANDBOX  "
    payload["source_endpoint"] = (
        "  https://local.invalid/business-profile/202400001A  "
    )
    address = payload["registered_address"]
    assert isinstance(address, dict)
    for key in ("block", "street", "unit", "postal_code", "country_code"):
        value = address[key]
        assert isinstance(value, str)
        address[key] = f"  {value}  "
    address["building_name"] = "   "
    typed = AcraCompanyPayload.model_validate(payload)
    zero, target = _build_local_zero(StaticRegistryAdapter(typed))

    created = zero.create_case("202400001A")
    completed = zero.attach_document(
        case_id=created.case_id,
        display_name="spaces.pdf",
        content_type="application/pdf",
        content=b"%PDF-1.4\nSYNTHETIC NORMALIZATION TEST\n%%EOF",
    )

    assert created.status == "PENDING_INPUTS"
    assert completed.status == "COMPLETED"
    assert completed.metrics.human_interventions == 0
    assert target.calls == ["search", "shell", "policy", "amend"]


def test_P06_QG_009_WRONG_RETURNED_UEN() -> None:
    _assert_registry_contract_failure(
        _local_registry_payload(uen="209999999Z"),
        "ACRA_RESPONSE_IDENTITY_MISMATCH",
    )


def test_P06_QG_009_MUTATED_TYPED_DTO() -> None:
    payload = _local_registry_payload()
    object.__setattr__(payload, "uen", "209999999Z")
    _assert_registry_contract_failure(payload, "ACRA_RESPONSE_IDENTITY_MISMATCH")


def test_P06_QG_009_BLANK_NAME_BYPASS() -> None:
    payload = _local_registry_payload().model_copy()
    object.__setattr__(payload, "entity_name", "   ")
    _assert_registry_contract_failure(payload, "ACRA_RESPONSE_INVALID")


def test_P06_QG_009_MALFORMED_ADDRESS() -> None:
    payload = _local_registry_payload().model_copy()
    object.__setattr__(
        payload,
        "registered_address",
        {"block": "18", "street": "", "postal_code": "018956", "country_code": "SG"},
    )
    _assert_registry_contract_failure(payload, "ACRA_RESPONSE_INVALID")


def test_P06_QG_009_MALFORMED_TIMESTAMP() -> None:
    payload = _local_registry_payload().model_copy()
    object.__setattr__(payload, "retrieved_at", "not-a-timestamp")
    _assert_registry_contract_failure(payload, "ACRA_RESPONSE_INVALID")


def test_P06_QG_009_UNSAFE_PROVENANCE_QUERY() -> None:
    payload = _local_registry_payload().model_copy()
    object.__setattr__(
        payload,
        "source_endpoint",
        "https://local.invalid/business-profile/202400001A?filter=synthetic",
    )
    _assert_registry_contract_failure(payload, "ACRA_RESPONSE_INVALID")


def test_P06_QG_009_HTTP_PROVENANCE() -> None:
    payload = _local_registry_payload().model_copy()
    object.__setattr__(
        payload,
        "source_endpoint",
        "http://local.invalid/business-profile/202400001A",
    )
    _assert_registry_contract_failure(payload, "ACRA_RESPONSE_INVALID")


def test_alternate_local_adapters_complete_the_full_zero_touch_path() -> None:
    target = LocalTargetAdapter()
    cases = OnboardingService(
        acra=LocalRegistryAdapter(),
        goldtier=target,
        repository=InMemoryOnboardingCaseRepository(),
    )
    documents = DocumentProcessingService(
        cases=cases,
        idp=LocalIdpAdapter(),
        repository=InMemoryDocumentProcessingRepository(),
        max_upload_bytes=1024,
        review_confidence_threshold=0.85,
    )
    ownership = OwnershipAnalysisService(
        cases=cases,
        provider=LocalOwnershipAdapter(),
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
    zero = ZeroTouchOrchestrator(
        cases=cases,
        documents=documents,
        ownership=ownership,
        clm=clm,
        repository=InMemoryZeroTouchAutomationRepository(),
    )
    created = zero.create_case("202400001A")
    completed = zero.attach_document(
        case_id=created.case_id,
        display_name="local.pdf",
        content_type="application/pdf",
        content=b"%PDF-1.4\nSYNTHETIC LOCAL ADAPTER TEST\n%%EOF",
    )
    assert completed.status == "COMPLETED"
    assert completed.metrics.human_interventions == 0
    assert target.calls == ["search", "shell", "policy", "amend"]
    assert documents.list_documents(case_id=created.case_id)[0].provider_environment == "SANDBOX"
    analyzed = ownership.get(case_id=created.case_id)
    assert analyzed is not None and analyzed.provider_environment == "SANDBOX"
    assert analyzed.candidates[0].aggregated_ownership_percent == Decimal("30.0000")
