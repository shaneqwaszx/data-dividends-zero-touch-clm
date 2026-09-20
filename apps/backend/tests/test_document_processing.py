from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.connectors.idp import IdpProcessingError
from app.connectors.mock_idp import MockIdpProvider, MockIdpScenario
from app.domain.documents import (
    ComparisonStatus,
    DocumentEventType,
    DocumentFieldKey,
    DocumentProcessingState,
    FieldReviewStatus,
    ReviewDecision,
)
from app.domain.models import (
    CanonicalLegalEntity,
    OnboardingCase,
    RegisteredAddress,
    SourceEnvironment,
    SourceMetadata,
    SourceSystem,
    WorkflowState,
)
from app.services.document_errors import (
    DocumentProcessingInfrastructureError,
    DocumentRequestError,
)
from app.services.document_processing import (
    DocumentProcessingService,
    compare_values,
    normalize_document_value,
)
from app.services.document_repository import InMemoryDocumentProcessingRepository

CASE_ID = UUID("00000000-0000-4000-8000-000000000101")
OTHER_CASE_ID = UUID("00000000-0000-4000-8000-000000000102")
PDF = (Path(__file__).parent / "fixtures" / "uat" / "clean-company-profile.pdf").read_bytes()


def canonical_entity(*, address: RegisteredAddress | None = None) -> CanonicalLegalEntity:
    return CanonicalLegalEntity(
        registration_number="202400001A",
        legal_name="MERLION CIRCULAR LABS PTE. LTD.",
        country_of_incorporation="SG",
        party_type="PRIVATE_COMPANY_LIMITED_BY_SHARES",
        registration_date=date(2024, 1, 2),
        entity_status="LIVE",
        registered_address=address
        if address is not None
        else RegisteredAddress(
            address_line_1="18 INNOVATION WAY",
            address_line_2="#04-01",
            postal_code="018956",
            country_code="SG",
        ),
        source=SourceMetadata(
            source_system=SourceSystem.ACRA,
            environment=SourceEnvironment.MOCK,
            registry_source_link="https://mock.acra.gov.sg/api/entities/202400001A",
            retrieved_at=datetime(2026, 8, 10, tzinfo=UTC),
        ),
    )


class StubCases:
    def __init__(self, entity: CanonicalLegalEntity | None = None) -> None:
        self.entity = entity if entity is not None else canonical_entity()

    def get_case(self, case_id: UUID) -> OnboardingCase | None:
        if case_id not in {CASE_ID, OTHER_CASE_ID}:
            return None
        now = datetime(2026, 8, 10, tzinfo=UTC)
        return OnboardingCase(
            case_id=case_id,
            source_case_id="CASE-SYNTHETIC",
            correlation_id=UUID("00000000-0000-4000-8000-000000000103"),
            requested_uen="202400001A",
            state=WorkflowState.COMPLETED,
            entity=self.entity,
            created_at=now,
            updated_at=now,
        )


class IncrementingClock:
    def __init__(self) -> None:
        self._current = datetime(2026, 8, 10, tzinfo=UTC)

    def __call__(self) -> datetime:
        value = self._current
        self._current += timedelta(microseconds=1)
        return value


class FailOnceClock(IncrementingClock):
    def __init__(self, fail_at_call: int) -> None:
        super().__init__()
        self._calls = 0
        self._fail_at_call = fail_at_call

    def __call__(self) -> datetime:
        self._calls += 1
        if self._calls == self._fail_at_call:
            raise RuntimeError("PRIVATE_CLOCK_SENTINEL")
        return super().__call__()


class StubProvider:
    def __init__(
        self,
        result: object = None,
        error: Exception | None = None,
        metadata: object = None,
    ) -> None:
        self.result = result
        self.error = error
        self._metadata = metadata or {
            "provider_name": "STUB_IDP",
            "environment": "LOCAL",
        }
        self.call_count = 0

    @property
    def metadata(self) -> object:
        return self._metadata

    def process(self, document: object) -> object:
        self.call_count += 1
        if self.error is not None:
            raise self.error
        return self.result


class FailOnceRepository(InMemoryDocumentProcessingRepository):
    def __init__(self, fail_at_save: int) -> None:
        super().__init__()
        self._save_calls = 0
        self._fail_at_save = fail_at_save

    def save(self, record):  # type: ignore[no-untyped-def]
        self._save_calls += 1
        if self._save_calls == self._fail_at_save:
            raise RuntimeError("PRIVATE_REPOSITORY_SENTINEL")
        super().save(record)


def valid_provider_result(*, source_reference: str = "LOCAL_PAGE_1") -> dict[str, object]:
    values: dict[DocumentFieldKey, str] = {
        DocumentFieldKey.REGISTRATION_NUMBER: "202400001A",
        DocumentFieldKey.LEGAL_NAME: "MERLION CIRCULAR LABS PTE. LTD.",
        DocumentFieldKey.REGISTERED_ADDRESS: "18 INNOVATION WAY, #04-01, 018956, SG",
        DocumentFieldKey.COUNTRY_OF_INCORPORATION: "SG",
    }
    return {
        "profile": "PROVISIONAL_CORPORATE",
        "fields": [
            {
                "field_key": key.value,
                "value": values[key],
                "confidence": 0.91,
                "page_number": 1,
                "source_reference": source_reference,
            }
            for key in DocumentFieldKey
        ],
    }


def make_service(
    *,
    provider: Any | None = None,
    cases: StubCases | None = None,
    max_bytes: int = 1024,
    threshold: float = 0.85,
) -> tuple[DocumentProcessingService, InMemoryDocumentProcessingRepository]:
    repository = InMemoryDocumentProcessingRepository()
    service = DocumentProcessingService(
        cases=cases or StubCases(),
        idp=provider or MockIdpProvider(),
        repository=repository,
        max_upload_bytes=max_bytes,
        review_confidence_threshold=threshold,
        clock=IncrementingClock(),
        uuid_factory=uuid4,
    )
    return service, repository


def create(
    service: DocumentProcessingService,
    scenario: MockIdpScenario | None = None,
    case_id: UUID = CASE_ID,
):
    return service.create_document(
        case_id=case_id,
        display_name="synthetic.pdf",
        content_type="application/pdf",
        content=PDF,
        provider=MockIdpProvider(scenario) if scenario is not None else None,
    )


def field(record: object, key: DocumentFieldKey):
    return next(item for item in record.fields if item.field_key == key)  # type: ignore[attr-defined]


def test_all_fields_match_with_provenance_and_pending_human_review() -> None:
    service, _ = make_service()

    record = create(service)

    assert record.state == DocumentProcessingState.REVIEW_REQUIRED
    assert record.display_name == "synthetic.pdf"
    assert record.media_type == "application/pdf"
    assert record.processed_at is not None
    assert record.reviewed_at is None
    assert len(record.fields) == 4
    assert {item.comparison_status for item in record.fields} == {ComparisonStatus.MATCH}
    assert {item.review_status for item in record.fields} == {FieldReviewStatus.PENDING}
    assert all(item.provenance.provider == "MOCK_IDP" for item in record.fields)
    assert all(item.provenance.page_number == 1 for item in record.fields)
    assert [event.event_type for event in record.events] == [
        DocumentEventType.DOCUMENT_UPLOADED,
        DocumentEventType.DOCUMENT_PROCESSING_STARTED,
        DocumentEventType.DOCUMENT_PROCESSED,
        DocumentEventType.DOCUMENT_REVIEW_REQUIRED,
    ]
    assert [event.sequence for event in record.events] == [1, 2, 3, 4]
    assert [event.timestamp for event in record.events] == sorted(
        event.timestamp for event in record.events
    )


def test_mismatch_low_confidence_and_missing_scenarios_are_independent() -> None:
    service, _ = make_service()

    mismatch = create(service, MockIdpScenario.FIELD_MISMATCH)
    low = create(service, MockIdpScenario.LOW_CONFIDENCE)
    missing = create(service, MockIdpScenario.MISSING_FIELD)

    assert (
        field(mismatch, DocumentFieldKey.LEGAL_NAME).comparison_status == ComparisonStatus.MISMATCH
    )
    low_address = field(low, DocumentFieldKey.REGISTERED_ADDRESS)
    assert low_address.comparison_status == ComparisonStatus.MATCH
    assert low_address.confidence == 0.54
    missing_address = field(missing, DocumentFieldKey.REGISTERED_ADDRESS)
    assert missing_address.original_extracted_value is None
    assert missing_address.normalized_value is None
    assert missing_address.comparison_status == ComparisonStatus.MISSING_FROM_DOCUMENT
    assert missing_address.provenance.page_number is None


@pytest.mark.parametrize(
    ("key", "document", "canonical", "expected"),
    [
        (
            DocumentFieldKey.REGISTRATION_NUMBER,
            " 202400001a ",
            "202400001A",
            ComparisonStatus.MATCH,
        ),
        (
            DocumentFieldKey.LEGAL_NAME,
            " Example   Pte Ltd ",
            "EXAMPLE PTE LTD",
            ComparisonStatus.MATCH,
        ),
        (DocumentFieldKey.REGISTERED_ADDRESS, "1 Main St", "2 Main St", ComparisonStatus.MISMATCH),
        (DocumentFieldKey.LEGAL_NAME, None, "EXAMPLE", ComparisonStatus.MISSING_FROM_DOCUMENT),
        (DocumentFieldKey.LEGAL_NAME, "EXAMPLE", None, ComparisonStatus.MISSING_FROM_REGISTRY),
        (DocumentFieldKey.LEGAL_NAME, None, None, ComparisonStatus.NOT_COMPARABLE),
    ],
)
def test_deterministic_comparison_statuses(
    key: DocumentFieldKey,
    document: str | None,
    canonical: str | None,
    expected: ComparisonStatus,
) -> None:
    assert compare_values(key, document, canonical) == expected


def test_normalization_is_conservative_and_deterministic() -> None:
    assert (
        normalize_document_value(DocumentFieldKey.REGISTERED_ADDRESS, " 18  Main St, #01 ")
        == "18 MAIN ST, #01"
    )
    assert normalize_document_value(DocumentFieldKey.COUNTRY_OF_INCORPORATION, " sg ") == "SG"
    assert (
        normalize_document_value(DocumentFieldKey.REGISTRATION_NUMBER, " 2024 00001a ")
        == "202400001A"
    )
    assert (
        compare_values(
            DocumentFieldKey.REGISTRATION_NUMBER,
            "2024 00001a",
            "202400001A",
        )
        == ComparisonStatus.MATCH
    )
    assert (
        compare_values(
            DocumentFieldKey.REGISTRATION_NUMBER,
            "2024 00002a",
            "202400001A",
        )
        == ComparisonStatus.MISMATCH
    )


def test_accept_reject_and_correct_preserve_original_and_complete_review() -> None:
    service, _ = make_service()
    record = create(service, MockIdpScenario.FIELD_MISMATCH)
    original_address = field(record, DocumentFieldKey.REGISTERED_ADDRESS).original_extracted_value
    original_name = field(record, DocumentFieldKey.LEGAL_NAME).original_extracted_value

    record = service.review_field(
        case_id=CASE_ID,
        document_id=record.document_id,
        field_key=DocumentFieldKey.REGISTRATION_NUMBER,
        decision=ReviewDecision.ACCEPTED,
    )
    assert record.state == DocumentProcessingState.REVIEW_REQUIRED
    record = service.review_field(
        case_id=CASE_ID,
        document_id=record.document_id,
        field_key=DocumentFieldKey.LEGAL_NAME,
        decision=ReviewDecision.REJECTED,
        note="Synthetic mismatch rejected",
    )
    record = service.review_field(
        case_id=CASE_ID,
        document_id=record.document_id,
        field_key=DocumentFieldKey.REGISTERED_ADDRESS,
        decision=ReviewDecision.CORRECTED,
        corrected_value="18 Innovation Way, #04-02, 018956, SG",
    )
    record = service.review_field(
        case_id=CASE_ID,
        document_id=record.document_id,
        field_key=DocumentFieldKey.COUNTRY_OF_INCORPORATION,
        decision=ReviewDecision.ACCEPTED,
    )

    assert record.state == DocumentProcessingState.REVIEWED
    assert record.reviewed_at is not None
    rejected = field(record, DocumentFieldKey.LEGAL_NAME)
    assert rejected.original_extracted_value == original_name
    assert rejected.review_status == FieldReviewStatus.REJECTED
    assert rejected.reviewed_value is None
    assert rejected.review_note == "Synthetic mismatch rejected"
    corrected = field(record, DocumentFieldKey.REGISTERED_ADDRESS)
    assert corrected.original_extracted_value == original_address
    assert corrected.review_status == FieldReviewStatus.CORRECTED
    assert corrected.reviewed_value == "18 Innovation Way, #04-02, 018956, SG"
    assert record.events[-1].event_type == DocumentEventType.DOCUMENT_REVIEW_COMPLETED

    serialized_events = " ".join(event.model_dump_json() for event in record.events)
    assert "Synthetic mismatch rejected" not in serialized_events
    assert "18 Innovation Way" not in serialized_events
    assert "synthetic.pdf" not in serialized_events


def test_identical_review_retry_is_idempotent_and_conflict_is_rejected() -> None:
    service, _ = make_service()
    record = create(service)
    reviewed = service.review_field(
        case_id=CASE_ID,
        document_id=record.document_id,
        field_key=DocumentFieldKey.LEGAL_NAME,
        decision=ReviewDecision.CORRECTED,
        corrected_value="Corrected Synthetic Name",
        note="Safe note",
    )
    retried = service.review_field(
        case_id=CASE_ID,
        document_id=record.document_id,
        field_key=DocumentFieldKey.LEGAL_NAME,
        decision=ReviewDecision.CORRECTED,
        corrected_value="Corrected Synthetic Name",
        note="Safe note",
    )
    assert retried == reviewed

    with pytest.raises(DocumentRequestError) as exc_info:
        service.review_field(
            case_id=CASE_ID,
            document_id=record.document_id,
            field_key=DocumentFieldKey.LEGAL_NAME,
            decision=ReviewDecision.ACCEPTED,
        )
    assert exc_info.value.code == "DOCUMENT_FIELD_REVIEW_CONFLICT"


def test_superseded_document_rejects_review_without_appending_event() -> None:
    service, _ = make_service()
    prior = create(service)
    service.replace_document(
        case_id=CASE_ID,
        document_id=prior.document_id,
        expected_event_count=len(prior.events),
        display_name="replacement.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    superseded = service.get_document(case_id=CASE_ID, document_id=prior.document_id)
    assert superseded is not None
    event_count = len(superseded.events)

    with pytest.raises(DocumentRequestError) as exc_info:
        service.review_field(
            case_id=CASE_ID,
            document_id=prior.document_id,
            field_key=DocumentFieldKey.LEGAL_NAME,
            decision=ReviewDecision.ACCEPTED,
        )

    assert exc_info.value.code == "DOCUMENT_ALREADY_SUPERSEDED"
    unchanged = service.get_document(case_id=CASE_ID, document_id=prior.document_id)
    assert unchanged is not None
    assert len(unchanged.events) == event_count


@pytest.mark.parametrize(
    ("scenario", "decision", "correction", "code"),
    [
        (
            MockIdpScenario.ALL_FIELDS_MATCH,
            ReviewDecision.CORRECTED,
            None,
            "DOCUMENT_CORRECTION_REQUIRED",
        ),
        (
            MockIdpScenario.ALL_FIELDS_MATCH,
            ReviewDecision.ACCEPTED,
            "extra",
            "DOCUMENT_CORRECTION_NOT_ALLOWED",
        ),
        (
            MockIdpScenario.MISSING_FIELD,
            ReviewDecision.ACCEPTED,
            None,
            "DOCUMENT_MISSING_VALUE_CANNOT_BE_ACCEPTED",
        ),
    ],
)
def test_invalid_review_inputs_do_not_mutate_field(
    scenario: MockIdpScenario,
    decision: ReviewDecision,
    correction: str | None,
    code: str,
) -> None:
    service, _ = make_service()
    record = create(service, scenario)
    target = (
        DocumentFieldKey.REGISTERED_ADDRESS
        if scenario == MockIdpScenario.MISSING_FIELD
        else DocumentFieldKey.LEGAL_NAME
    )

    with pytest.raises(DocumentRequestError) as exc_info:
        service.review_field(
            case_id=CASE_ID,
            document_id=record.document_id,
            field_key=target,
            decision=decision,
            corrected_value=correction,
        )
    assert exc_info.value.code == code
    stored = service.get_document(case_id=CASE_ID, document_id=record.document_id)
    assert stored is not None
    assert field(stored, target).review_status == FieldReviewStatus.PENDING


@pytest.mark.parametrize(
    ("display_name", "content_type", "content", "code"),
    [
        ("unsafe.txt", "application/pdf", PDF, "DOCUMENT_MEDIA_TYPE_UNSUPPORTED"),
        ("../unsafe.pdf", "application/pdf", PDF, "DOCUMENT_NAME_INVALID"),
        ("unsafe.pdf", "text/plain", PDF, "DOCUMENT_MEDIA_TYPE_UNSUPPORTED"),
        ("unsafe.pdf", "application/pdf", b"", "DOCUMENT_EMPTY"),
        ("unsafe.pdf", "application/pdf", b"not a pdf", "DOCUMENT_STRUCTURE_INVALID"),
        ("unsafe.pdf", "application/pdf", b"%PDF-1.4\nno eof", "DOCUMENT_STRUCTURE_INVALID"),
    ],
)
def test_invalid_upload_stops_before_provider(
    display_name: str, content_type: str, content: bytes, code: str
) -> None:
    provider = StubProvider()
    service, _ = make_service(provider=provider)
    with pytest.raises(DocumentRequestError) as exc_info:
        service.create_document(
            case_id=CASE_ID,
            display_name=display_name,
            content_type=content_type,
            content=content,
        )
    assert exc_info.value.code == code
    assert provider.call_count == 0


def test_oversize_missing_parent_and_case_document_isolation() -> None:
    provider = StubProvider()
    service, _ = make_service(provider=provider, max_bytes=len(PDF) - 1)
    with pytest.raises(DocumentRequestError) as too_large:
        create(service)
    assert too_large.value.code == "DOCUMENT_TOO_LARGE"
    with pytest.raises(DocumentRequestError) as missing:
        create(service, case_id=UUID(int=999))
    assert missing.value.code == "ONBOARDING_CASE_NOT_FOUND"
    assert provider.call_count == 0

    normal_service, _ = make_service()
    first = create(normal_service, case_id=CASE_ID)
    second = create(normal_service, case_id=OTHER_CASE_ID)
    assert normal_service.list_documents(case_id=CASE_ID) == [first]
    assert normal_service.list_documents(case_id=OTHER_CASE_ID) == [second]
    assert normal_service.get_document(case_id=OTHER_CASE_ID, document_id=first.document_id) is None


@pytest.mark.parametrize(
    ("provider", "expected_code"),
    [
        (StubProvider(error=IdpProcessingError()), "IDP_PROCESSING_FAILED"),
        (StubProvider(result={"unexpected": "PRIVATE_OUTPUT_SENTINEL"}), "IDP_MALFORMED_OUTPUT"),
        (StubProvider(error=RuntimeError("PRIVATE_EXCEPTION_SENTINEL")), "IDP_UNEXPECTED_FAILURE"),
    ],
)
def test_provider_failures_are_terminal_retrievable_and_sanitized(
    provider: StubProvider, expected_code: str
) -> None:
    service, repository = make_service(provider=provider)
    with pytest.raises(DocumentProcessingInfrastructureError) as exc_info:
        create(service)

    failure = exc_info.value
    stored = repository.get(failure.document_id)
    assert stored is not None
    assert stored.state == DocumentProcessingState.FAILED
    assert stored.error is not None and stored.error.code == expected_code
    assert stored.fields == []
    assert stored.events[-1].event_type == DocumentEventType.DOCUMENT_PROCESSING_FAILED
    serialized = stored.model_dump_json()
    assert "PRIVATE_OUTPUT_SENTINEL" not in serialized
    assert "PRIVATE_EXCEPTION_SENTINEL" not in serialized
    assert "SYNTHETIC PHASE 03 TEST ONLY" not in serialized


def test_failed_replacement_keeps_one_current_retry_chain() -> None:
    service, repository = make_service()
    prior = create(service)

    with pytest.raises(DocumentProcessingInfrastructureError) as exc_info:
        service.replace_document(
            case_id=CASE_ID,
            document_id=prior.document_id,
            expected_event_count=len(prior.events),
            display_name="replacement.pdf",
            content_type="application/pdf",
            content=PDF,
            provider=StubProvider(error=IdpProcessingError()),
        )

    failed = repository.get(exc_info.value.document_id)
    superseded = repository.get(prior.document_id)
    assert failed is not None
    assert superseded is not None
    assert failed.state == DocumentProcessingState.FAILED
    assert failed.supersedes_document_id == prior.document_id
    assert superseded.superseded_by_document_id == failed.document_id
    assert [
        item.document_id
        for item in service.list_documents(case_id=CASE_ID)
        if item.superseded_by_document_id is None
    ] == [failed.document_id]


def assert_terminal_document_failure(
    repository: InMemoryDocumentProcessingRepository,
    failure: DocumentProcessingInfrastructureError,
    expected_code: str,
):
    stored = repository.get(failure.document_id)
    assert stored is not None
    assert stored.state == DocumentProcessingState.FAILED
    assert stored.error is not None and stored.error.code == expected_code
    assert stored.fields == []
    assert stored.reviewed_at is None
    assert stored.events[-1].event_type == DocumentEventType.DOCUMENT_PROCESSING_FAILED
    assert stored.events[-1].state == DocumentProcessingState.FAILED
    assert (
        sum(
            event.event_type == DocumentEventType.DOCUMENT_PROCESSING_FAILED
            for event in stored.events
        )
        == 1
    )
    assert all(event.state != DocumentProcessingState.REVIEWED for event in stored.events)
    return stored


def test_overlong_canonical_value_terminalizes_instead_of_stranding_processing() -> None:
    entity = canonical_entity().model_copy(update={"legal_name": "A" * 513})
    cases = StubCases(entity=entity)
    service, repository = make_service(cases=cases)
    parent_before = cases.get_case(CASE_ID)
    assert parent_before is not None

    with pytest.raises(DocumentProcessingInfrastructureError) as exc_info:
        create(service)

    failure = exc_info.value
    assert failure.code == "DOCUMENT_COMPARISON_INPUT_INVALID"
    stored = assert_terminal_document_failure(
        repository, failure, "DOCUMENT_COMPARISON_INPUT_INVALID"
    )
    assert [event.event_type for event in stored.events] == [
        DocumentEventType.DOCUMENT_UPLOADED,
        DocumentEventType.DOCUMENT_PROCESSING_STARTED,
        DocumentEventType.DOCUMENT_PROCESSING_FAILED,
    ]
    assert all(
        record.state != DocumentProcessingState.PROCESSING
        for record in repository.list_for_case(CASE_ID)
    )
    assert cases.get_case(CASE_ID) == parent_before


def test_post_validation_comparison_exception_terminalizes_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, repository = make_service()

    def raise_comparison(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError("PRIVATE_COMPARISON_SENTINEL")

    monkeypatch.setattr("app.services.document_processing.compare_values", raise_comparison)
    with pytest.raises(DocumentProcessingInfrastructureError) as exc_info:
        create(service)

    stored = assert_terminal_document_failure(repository, exc_info.value, "IDP_UNEXPECTED_FAILURE")
    assert "PRIVATE_COMPARISON_SENTINEL" not in stored.model_dump_json()


def test_post_validation_clock_failure_terminalizes_safely() -> None:
    repository = InMemoryDocumentProcessingRepository()
    service = DocumentProcessingService(
        cases=StubCases(),
        idp=MockIdpProvider(),
        repository=repository,
        max_upload_bytes=1024,
        review_confidence_threshold=0.85,
        clock=FailOnceClock(fail_at_call=4),
        uuid_factory=uuid4,
    )

    with pytest.raises(DocumentProcessingInfrastructureError) as exc_info:
        create(service)

    stored = assert_terminal_document_failure(repository, exc_info.value, "IDP_UNEXPECTED_FAILURE")
    assert "PRIVATE_CLOCK_SENTINEL" not in stored.model_dump_json()


def test_recoverable_repository_update_failure_terminalizes_from_last_saved_state() -> None:
    repository = FailOnceRepository(fail_at_save=3)
    service = DocumentProcessingService(
        cases=StubCases(),
        idp=MockIdpProvider(),
        repository=repository,
        max_upload_bytes=1024,
        review_confidence_threshold=0.85,
        clock=IncrementingClock(),
        uuid_factory=uuid4,
    )

    with pytest.raises(DocumentProcessingInfrastructureError) as exc_info:
        create(service)

    stored = assert_terminal_document_failure(repository, exc_info.value, "IDP_UNEXPECTED_FAILURE")
    assert [event.event_type for event in stored.events] == [
        DocumentEventType.DOCUMENT_UPLOADED,
        DocumentEventType.DOCUMENT_PROCESSING_STARTED,
        DocumentEventType.DOCUMENT_PROCESSING_FAILED,
    ]
    assert "PRIVATE_REPOSITORY_SENTINEL" not in stored.model_dump_json()


@pytest.mark.parametrize(
    "unsafe_provenance",
    ["\n", "\r\n", "   ", "SAFE\nUNSAFE", "X" * 129],
)
@pytest.mark.parametrize("location", ["provider_name", "source_reference"])
def test_malformed_provider_provenance_terminalizes_safely(
    unsafe_provenance: str,
    location: str,
) -> None:
    metadata: dict[str, object] = {
        "provider_name": "LOCAL_STUB",
        "environment": "LOCAL",
    }
    source_reference = "LOCAL_PAGE_1"
    if location == "provider_name":
        metadata["provider_name"] = unsafe_provenance
    else:
        source_reference = unsafe_provenance
    provider = StubProvider(
        result=valid_provider_result(source_reference=source_reference),
        metadata=metadata,
    )
    service, repository = make_service(provider=provider)

    with pytest.raises(DocumentProcessingInfrastructureError) as exc_info:
        create(service)

    stored = assert_terminal_document_failure(repository, exc_info.value, "IDP_MALFORMED_OUTPUT")
    assert unsafe_provenance not in stored.model_dump_json()


def test_non_mock_provider_uses_unchanged_service_and_review_flow() -> None:
    provider = StubProvider(result=valid_provider_result())
    service, _ = make_service(provider=provider)

    record = create(service)

    assert provider.call_count == 1
    assert record.state == DocumentProcessingState.REVIEW_REQUIRED
    assert record.provider_environment.value == "LOCAL"
    assert {item.provenance.provider for item in record.fields} == {"STUB_IDP"}
    assert {item.provenance.environment.value for item in record.fields} == {"LOCAL"}
    assert {item.comparison_status for item in record.fields} == {ComparisonStatus.MATCH}
    for key in DocumentFieldKey:
        record = service.review_field(
            case_id=CASE_ID,
            document_id=record.document_id,
            field_key=key,
            decision=ReviewDecision.ACCEPTED,
        )
    assert record.state == DocumentProcessingState.REVIEWED
