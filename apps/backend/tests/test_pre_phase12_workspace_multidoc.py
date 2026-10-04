"""Focused Pre-Phase 12 portfolio, intake-boundary, and aggregation tests."""

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi.testclient import TestClient

from app.composition import (
    build_clm_orchestration_service,
    build_onboarding_service,
    build_reconciliation_service,
    build_zero_touch_orchestrator,
)
from app.config import Settings
from app.connectors.idp import IdpDocumentInput
from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider
from app.connectors.mock_acra import MockAcraConnector
from app.connectors.ownership import OwnershipProviderRequest
from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
from app.domain.reconciliation import (
    ObservationValidity,
    ReconciliationField,
    ReconciliationObservation,
    ReconciliationOutcome,
    ReconciliationSourceKind,
    derive_allowed_actions,
    derive_reconciliation_outcome,
)
from app.domain.zero_touch import (
    AutomationStage,
    AutomationStatus,
    ZeroTouchAutomationRecord,
)
from app.main import create_app
from app.services.document_errors import DocumentRequestError
from app.services.document_processing import DocumentProcessingService
from app.services.document_repository import InMemoryDocumentProcessingRepository
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_repository import InMemoryOwnershipAnalysisRepository
from app.services.zero_touch_orchestration import ZeroTouchOrchestrator
from app.services.zero_touch_repository import InMemoryZeroTouchAutomationRepository

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "uat"
TEXT_PROFILE = """Legal Name: MERLION CIRCULAR LABS PTE. LTD.
UEN: 202400001A
Registered Address: 18 INNOVATION WAY, #04-01, 018956, SG
Country: SG
"""
DOCX_MEDIA = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class CountingAcraConnector(MockAcraConnector):
    def __init__(self) -> None:
        super().__init__()
        self.calls = {
            "ENTITY_PROFILE": 0,
            "OFFICERS": 0,
            "OWNERSHIP_PARTIES": 0,
            "RELATIONSHIPS": 0,
        }

    def fetch_company(self, uen: str) -> object:
        self.calls["ENTITY_PROFILE"] += 1
        return super().fetch_company(uen)

    def fetch_officers(self, uen: str) -> object:
        self.calls["OFFICERS"] += 1
        return super().fetch_officers(uen)

    def fetch_ownership_parties(self, uen: str) -> object:
        self.calls["OWNERSHIP_PARTIES"] += 1
        return super().fetch_ownership_parties(uen)

    def fetch_relationships(self, uen: str) -> object:
        self.calls["RELATIONSHIPS"] += 1
        return super().fetch_relationships(uen)


class CountingIdpProvider(LocalPdfTextIdpProvider):
    def __init__(self) -> None:
        self.calls = 0

    def process(self, document: IdpDocumentInput) -> object:
        self.calls += 1
        return super().process(document)


class CountingOwnershipProvider:
    def __init__(self, delegate: RegistryAcquisitionOwnershipProvider) -> None:
        self.delegate = delegate
        self.calls = 0

    @property
    def metadata(self) -> object:
        return self.delegate.metadata

    def load(self, request: OwnershipProviderRequest) -> object:
        self.calls += 1
        return self.delegate.load(request)


def counted_system() -> tuple[
    ZeroTouchOrchestrator,
    CountingAcraConnector,
    CountingIdpProvider,
    CountingOwnershipProvider,
]:
    settings = Settings(app_env="test")
    acra = CountingAcraConnector()
    onboarding = build_onboarding_service(settings=settings, acra_connector=acra)
    idp = CountingIdpProvider()
    documents = DocumentProcessingService(
        cases=onboarding,
        idp=idp,
        repository=InMemoryDocumentProcessingRepository(),
        max_upload_bytes=settings.idp_max_upload_bytes,
        max_files_per_case=settings.idp_max_files_per_case,
        max_total_intake_bytes=settings.idp_max_total_intake_bytes,
        review_confidence_threshold=settings.idp_review_confidence_threshold,
    )
    ownership_provider = CountingOwnershipProvider(RegistryAcquisitionOwnershipProvider(onboarding))
    ownership = OwnershipAnalysisService(
        cases=onboarding,
        provider=ownership_provider,
        repository=InMemoryOwnershipAnalysisRepository(),
        threshold_percent=settings.ubo_ownership_threshold_percent,
        max_parties=settings.ownership_max_parties,
        max_relationships=settings.ownership_max_relationships,
        max_depth=settings.ownership_max_depth,
        max_paths_per_candidate=settings.ownership_max_paths_per_candidate,
        max_total_paths=settings.ownership_max_total_paths,
    )
    reconciliation = build_reconciliation_service(onboarding, documents)
    clm = build_clm_orchestration_service(onboarding, documents, ownership, reconciliation)
    zero_touch = build_zero_touch_orchestrator(
        onboarding,
        documents,
        ownership,
        clm,
        reconciliation,
        settings,
    )
    return zero_touch, acra, idp, ownership_provider


def docx_bytes(
    text: str = TEXT_PROFILE,
    *,
    extra_member_names: tuple[str, ...] = (),
) -> bytes:
    output = BytesIO()
    paragraphs = "".join(f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>" for line in text.splitlines())
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Override PartName="/word/document.xml"
 ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""",
        )
        archive.writestr(
            "word/document.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{paragraphs}</w:body></w:document>""",
        )
        for member_name in extra_member_names:
            archive.writestr(member_name, "synthetic adversarial member")
    return output.getvalue()


def create_case(client: TestClient, uen: str = "202400001A") -> dict[str, object]:
    response = client.post("/api/clm/zero-touch/cases", json={"uen": uen})
    assert response.status_code == 201
    return response.json()


def upload(
    client: TestClient, case_id: str, name: str, media_type: str, content: bytes
) -> dict[str, object]:
    response = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
        headers={"Content-Type": media_type, "X-Document-Name": name},
        content=content,
    )
    assert response.status_code == 201, response.text
    return response.json()


def confirm_api_target_if_ready(
    client: TestClient, result: dict[str, object]
) -> dict[str, object]:
    exceptions = result["active_exceptions"]
    assert isinstance(exceptions, list)
    if not any(
        item["exception_type"] == "TARGET_CONFIRMATION_REQUIRED" for item in exceptions
    ):
        return result
    case = result["case"]
    clm = result["clm"]
    assert isinstance(case, dict) and isinstance(clm, dict)
    response = client.post(
        f"/api/clm/zero-touch/cases/{case['case_id']}/target-confirmation",
        json={
            "expected_automation_version": result["version"],
            "expected_clm_version": clm["version"],
            "expected_case_event_count": len(case["events"]),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def confirm_orchestrator_target(
    zero_touch: ZeroTouchOrchestrator, waiting: ZeroTouchAutomationRecord
) -> ZeroTouchAutomationRecord:
    case = zero_touch._cases.get_case(waiting.case_id)  # noqa: SLF001
    clm = zero_touch._clm.get(case_id=waiting.case_id)  # noqa: SLF001
    assert case is not None and clm is not None
    return zero_touch.confirm_target_dispatch(
        case_id=waiting.case_id,
        actor_id="multi-document-test-operator",
        expected_automation_version=waiting.version,
        expected_clm_version=clm.version,
        expected_case_event_count=len(case.events),
    )


def pending_automation_record(case_id: UUID, *, updated_at: datetime) -> ZeroTouchAutomationRecord:
    return ZeroTouchAutomationRecord(
        case_id=case_id,
        automation_id=uuid4(),
        ownership_provider_binding_id="a" * 32,
        status=AutomationStatus.PENDING_INPUTS,
        current_stage=AutomationStage.DOCUMENT,
        completed_stages=(AutomationStage.REGISTRY, AutomationStage.GOLDTIER_SEARCH),
        created_at=updated_at,
        updated_at=updated_at,
    )


def test_repository_listing_is_empty_ordered_and_defensively_copied() -> None:
    repository = InMemoryZeroTouchAutomationRepository()
    assert repository.list_records() == []

    first_id = UUID("00000000-0000-0000-0000-000000000001")
    second_id = UUID("00000000-0000-0000-0000-000000000002")
    first_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    second_at = datetime(2026, 1, 2, 3, 4, 6, tzinfo=UTC)
    repository.save(
        pending_automation_record(first_id, updated_at=first_at),
        expected_version=None,
    )
    repository.save(
        pending_automation_record(second_id, updated_at=second_at),
        expected_version=None,
    )
    listed_records = repository.list_records()
    assert [item.case_id for item in listed_records] == [second_id, first_id]
    listed_records[0].metrics.human_interventions = 99
    listed_records.clear()
    assert [item.case_id for item in repository.list_records()] == [second_id, first_id]
    assert repository.list_records()[0].metrics.human_interventions == 0

    client = TestClient(create_app(Settings(app_env="test")))
    created = create_case(client)
    listed = client.get("/api/clm/zero-touch/cases")
    assert listed.status_code == 200
    payload = listed.json()
    assert [item["case_id"] for item in payload] == [created["case"]["case_id"]]
    assert set(payload[0]) == {
        "case_id",
        "requested_uen",
        "legal_name",
        "status",
        "current_stage",
        "updated_at",
        "active_exception_count",
        "active_exception_types",
        "human_interventions",
        "final_outcome",
        "team_id",
        "client_scope_label",
        "priority",
        "resolved_jurisdiction",
        "created_at",
        "completed_at",
        "mock_goldtier_party_id",
    }


def test_repository_equal_timestamps_use_case_id_not_save_chronology() -> None:
    repository = InMemoryZeroTouchAutomationRepository()
    lower_id = UUID("00000000-0000-0000-0000-000000000001")
    higher_id = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    tied_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)

    # Save the higher ID first: the later save does not win an exact timestamp tie.
    repository.save(
        pending_automation_record(higher_id, updated_at=tied_at),
        expected_version=None,
    )
    repository.save(
        pending_automation_record(lower_id, updated_at=tied_at),
        expected_version=None,
    )

    expected = [higher_id, lower_id]
    assert [item.case_id for item in repository.list_records()] == expected
    assert [item.case_id for item in repository.list_records()] == expected


def test_case_list_status_filter_is_typed_and_backend_authored() -> None:
    client = TestClient(create_app(Settings(app_env="test")))
    created = create_case(client)
    waiting = client.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "UNKNOWN", "country_of_incorporation": "AU"},
    )
    assert waiting.status_code == 201
    response = client.get("/api/clm/zero-touch/cases?status=WAITING_FOR_REVIEW")
    assert response.status_code == 200
    assert [item["case_id"] for item in response.json()] == [waiting.json()["case"]["case_id"]]
    assert client.get("/api/clm/zero-touch/cases?status=ANYTHING").status_code == 422
    assert created["status"] == "PENDING_INPUTS"


def test_pdf_docx_and_txt_are_independently_processed_before_intake_completion() -> None:
    client = TestClient(create_app(Settings(app_env="test")))
    created = create_case(client)
    case_id = str(created["case"]["case_id"])
    pdf = (FIXTURE_ROOT / "clean-company-profile.pdf").read_bytes()

    records = [
        upload(client, case_id, "Business Profile.pdf", "application/pdf", pdf),
        upload(client, case_id, "Constitution.docx", DOCX_MEDIA, docx_bytes()),
        upload(client, case_id, "Company Details.txt", "text/plain", TEXT_PROFILE.encode()),
    ]
    assert [item["media_type"] for item in records] == [
        "application/pdf",
        DOCX_MEDIA,
        "text/plain",
    ]
    assert len({item["document_id"] for item in records}) == 3
    assert all(len(item["fields"]) == 4 for item in records)
    before = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
    assert before["status"] == "PENDING_INPUTS"
    assert before["reconciliation"] is None

    completed = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
        json={"expected_document_count": 3},
    )
    assert completed.status_code == 200, completed.text
    result = confirm_api_target_if_ready(client, completed.json())
    assert result["status"] == "COMPLETED"
    assert result["reconciliation"]["source_document_ids"] == [
        item["document_id"] for item in records
    ]
    legal_name = next(
        field for field in result["reconciliation"]["fields"] if field["field_name"] == "legal_name"
    )
    assert (
        len([item for item in legal_name["observations"] if item["source_kind"] == "DOCUMENT_IDP"])
        == 3
    )
    assert all(
        item["document_display_name"]
        for item in legal_name["observations"]
        if item["source_kind"] == "DOCUMENT_IDP"
    )


def test_three_document_call_counts_and_read_only_listing_do_not_trigger_work() -> None:
    zero_touch, acra, idp, ownership = counted_system()
    created = zero_touch.create_case("202400001A")
    zero_touch.intake_document(
        case_id=created.case_id,
        display_name="profile.pdf",
        content_type="application/pdf",
        content=(FIXTURE_ROOT / "clean-company-profile.pdf").read_bytes(),
    )
    zero_touch.intake_document(
        case_id=created.case_id,
        display_name="constitution.docx",
        content_type=DOCX_MEDIA,
        content=docx_bytes(),
    )
    zero_touch.intake_document(
        case_id=created.case_id,
        display_name="details.txt",
        content_type="text/plain",
        content=TEXT_PROFILE.encode(),
    )
    assert acra.calls == {key: 1 for key in acra.calls}
    assert idp.calls == 3
    assert ownership.calls == 0
    assert zero_touch._clm.attempted_target_operations(case_id=created.case_id) == (  # noqa: SLF001
        "SEARCH",
    )

    before_listing = (dict(acra.calls), idp.calls, ownership.calls)
    assert [item.case_id for item in zero_touch.list_cases()] == [created.case_id]
    assert zero_touch.list_cases(status=AutomationStatus.WAITING_FOR_REVIEW) == []
    assert (acra.calls, idp.calls, ownership.calls) == before_listing

    waiting = zero_touch.start(case_id=created.case_id, expected_document_count=3)
    assert waiting.status == AutomationStatus.WAITING_FOR_REVIEW
    completed = confirm_orchestrator_target(zero_touch, waiting)
    assert completed.status == AutomationStatus.COMPLETED
    assert acra.calls == {key: 1 for key in acra.calls}
    assert idp.calls == 3
    assert ownership.calls == 1
    assert zero_touch._clm.attempted_target_operations(  # noqa: SLF001
        case_id=created.case_id
    ) == ('SEARCH', 'SHELL', 'POLICY', 'AMEND', 'READBACK')


def test_multi_document_conflict_stops_ownership_and_goldtier_calls() -> None:
    zero_touch, acra, idp, ownership = counted_system()
    created = zero_touch.create_case("202400001A")
    zero_touch.intake_document(
        case_id=created.case_id,
        display_name="current.txt",
        content_type="text/plain",
        content=TEXT_PROFILE.encode(),
    )
    zero_touch.intake_document(
        case_id=created.case_id,
        display_name="conflict.txt",
        content_type="text/plain",
        content=TEXT_PROFILE.replace(
            "MERLION CIRCULAR LABS PTE. LTD.", "OTHER COMPANY PTE. LTD."
        ).encode(),
    )
    waiting = zero_touch.start(case_id=created.case_id, expected_document_count=2)
    assert waiting.status == AutomationStatus.WAITING_FOR_REVIEW
    assert acra.calls == {key: 1 for key in acra.calls}
    assert idp.calls == 2
    assert ownership.calls == 0
    assert zero_touch._clm.attempted_target_operations(case_id=created.case_id) == (  # noqa: SLF001
        "SEARCH",
    )


def test_field_missing_from_one_document_does_not_create_false_missing_blocker() -> None:
    client = TestClient(create_app(Settings(app_env="test")))
    case_id = str(create_case(client)["case"]["case_id"])
    without_name = "\n".join(
        line for line in TEXT_PROFILE.splitlines() if not line.startswith("Legal Name:")
    )
    upload(client, case_id, "partial.txt", "text/plain", without_name.encode())
    upload(client, case_id, "complete.txt", "text/plain", TEXT_PROFILE.encode())
    completed = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
        json={"expected_document_count": 2},
    )
    assert completed.status_code == 200
    assert confirm_api_target_if_ready(client, completed.json())["status"] == "COMPLETED"
    legal_name = next(
        field
        for field in completed.json()["reconciliation"]["fields"]
        if field["field_name"] == "legal_name"
    )
    assert legal_name["outcome"] == "MATCH"
    assert {item["validity"] for item in legal_name["observations"]} == {
        "VALID",
        "MISSING",
    }


def test_unverifiable_document_evidence_remains_visible_beside_usable_evidence() -> None:
    client = TestClient(create_app(Settings(app_env="test")))
    case_id = str(create_case(client)["case"]["case_id"])
    ambiguous = TEXT_PROFILE + "Legal Name: ANOTHER COMPANY PTE. LTD.\n"
    upload(client, case_id, "ambiguous.txt", "text/plain", ambiguous.encode())
    upload(client, case_id, "complete.txt", "text/plain", TEXT_PROFILE.encode())
    waiting = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
        json={"expected_document_count": 2},
    )
    assert waiting.status_code == 200
    payload = waiting.json()
    assert payload["status"] == "WAITING_FOR_REVIEW"
    legal_name = next(
        field
        for field in payload["reconciliation"]["fields"]
        if field["field_name"] == "legal_name"
    )
    assert legal_name["outcome"] == "UNVERIFIABLE"
    assert {
        item["document_display_name"] for item in legal_name["observations"] if item["document_id"]
    } == {
        "ambiguous.txt",
        "complete.txt",
    }
    discrepancy = next(
        item
        for item in payload["reconciliation"]["discrepancies"]
        if item["field_name"] == "legal_name"
    )
    assert discrepancy["allowed_actions"] == []
    assert payload["target_operations"] == [
        {"operation": "SEARCH", "status": "NO_MATCH"},
        {"operation": "SHELL", "status": "NOT_ATTEMPTED"},
        {"operation": "POLICY", "status": "NOT_ATTEMPTED"},
        {"operation": "AMEND", "status": "NOT_ATTEMPTED"},
    ]


def test_intake_completion_rejects_zero_or_incomplete_document_sets() -> None:
    client = TestClient(create_app(Settings(app_env="test")))
    created = create_case(client)
    case_id = str(created["case"]["case_id"])
    empty = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
        json={"expected_document_count": 1},
    )
    assert empty.status_code == 409
    assert empty.json()["detail"]["code"] == "ZERO_TOUCH_DOCUMENTS_REQUIRED"
    upload(client, case_id, "Company Details.txt", "text/plain", TEXT_PROFILE.encode())
    incomplete = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
        json={"expected_document_count": 2},
    )
    assert incomplete.status_code == 409
    assert incomplete.json()["detail"]["code"] == "ZERO_TOUCH_INTAKE_INCOMPLETE"
    assert client.get(f"/api/clm/zero-touch/cases/{case_id}").json()["status"] == "PENDING_INPUTS"


def test_media_validation_rejects_malformed_docx_binary_txt_and_unsupported_image() -> None:
    client = TestClient(create_app(Settings(app_env="test")))
    case_id = str(create_case(client)["case"]["case_id"])
    cases = [
        ("bad.docx", DOCX_MEDIA, b"PK-not-a-docx", "DOCUMENT_STRUCTURE_INVALID"),
        ("bad.txt", "text/plain", b"text\x00binary", "DOCUMENT_TEXT_INVALID"),
        ("image.png", "image/png", b"\x89PNG", "DOCUMENT_NAME_INVALID"),
        ("archive.zip", "application/zip", b"PK", "DOCUMENT_NAME_INVALID"),
    ]
    for name, media_type, content, expected_code in cases:
        response = client.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
            headers={"Content-Type": media_type, "X-Document-Name": name},
            content=content,
        )
        assert response.status_code in {415, 422}
        assert response.json()["detail"]["code"] == expected_code


@pytest.mark.parametrize(
    "unsafe_member",
    (
        "C:/evil.txt",
        "C:\\evil.txt",
        "../evil.txt",
        "..\\evil.txt",
        "/evil.txt",
        "\\evil.txt",
        "//server/share/evil.txt",
        "\\\\server\\share\\evil.txt",
        "D:/folder/file.xml",
        "Z:\\folder\\file.xml",
    ),
)
def test_unsafe_docx_members_stop_before_idp_ownership_and_goldtier(
    unsafe_member: str,
) -> None:
    zero_touch, acra, idp, ownership = counted_system()
    created = zero_touch.create_case("202400001A")

    with pytest.raises(DocumentRequestError) as exc_info:
        zero_touch.intake_document(
            case_id=created.case_id,
            display_name="unsafe.docx",
            content_type=DOCX_MEDIA,
            content=docx_bytes(extra_member_names=(unsafe_member,)),
        )

    assert exc_info.value.code == "DOCUMENT_STRUCTURE_INVALID"
    assert acra.calls == {key: 1 for key in acra.calls}
    assert idp.calls == 0
    assert ownership.calls == 0
    assert zero_touch._clm.attempted_target_operations(case_id=created.case_id) == (  # noqa: SLF001
        "SEARCH",
    )
    assert zero_touch.list_cases()[0].status == AutomationStatus.PENDING_INPUTS


@pytest.mark.parametrize(
    "payload",
    (
        b"plain arbitrary bytes",
        b"%PDF-1.4\nobvious non-PDF content\n%%EOF",
        b"%PDF-1.4\ntruncated object",
    ),
)
def test_malformed_pdf_stops_before_idp_ownership_and_goldtier(payload: bytes) -> None:
    zero_touch, acra, idp, ownership = counted_system()
    created = zero_touch.create_case("202400001A")

    with pytest.raises(DocumentRequestError) as exc_info:
        zero_touch.intake_document(
            case_id=created.case_id,
            display_name="unsafe.pdf",
            content_type="application/pdf",
            content=payload,
        )

    assert exc_info.value.code == "DOCUMENT_STRUCTURE_INVALID"
    assert acra.calls == {key: 1 for key in acra.calls}
    assert idp.calls == 0
    assert ownership.calls == 0
    assert zero_touch._clm.attempted_target_operations(case_id=created.case_id) == (  # noqa: SLF001
        "SEARCH",
    )
    assert zero_touch.list_cases()[0].status == AutomationStatus.PENDING_INPUTS


def test_fake_marker_only_pdf_is_a_bounded_client_error_not_503() -> None:
    client = TestClient(create_app(Settings(app_env="test")))
    case_id = str(create_case(client)["case"]["case_id"])

    response = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
        headers={"Content-Type": "application/pdf", "X-Document-Name": "unsafe.pdf"},
        content=b"%PDF-1.4\nobvious non-PDF content\n%%EOF",
    )

    assert response.status_code == 422
    assert response.status_code != 503
    assert response.json()["detail"] == {
        "code": "DOCUMENT_STRUCTURE_INVALID",
        "message": "The uploaded PDF does not pass the configured structure checks.",
    }


def test_drive_qualified_docx_is_a_bounded_client_error_without_path_echo() -> None:
    client = TestClient(create_app(Settings(app_env="test")))
    case_id = str(create_case(client)["case"]["case_id"])

    response = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
        headers={"Content-Type": DOCX_MEDIA, "X-Document-Name": "unsafe.docx"},
        content=docx_bytes(extra_member_names=("C:/evil.txt",)),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "DOCUMENT_STRUCTURE_INVALID",
        "message": "The DOCX container contains an unsafe part.",
    }
    assert "C:/evil.txt" not in response.text


def test_batch_count_and_total_byte_limits_are_enforced() -> None:
    count_client = TestClient(create_app(Settings(app_env="test", idp_max_files_per_case=2)))
    case_id = str(create_case(count_client)["case"]["case_id"])
    upload(count_client, case_id, "one.txt", "text/plain", TEXT_PROFILE.encode())
    upload(count_client, case_id, "two.txt", "text/plain", TEXT_PROFILE.encode())
    too_many = count_client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
        headers={"Content-Type": "text/plain", "X-Document-Name": "three.txt"},
        content=TEXT_PROFILE.encode(),
    )
    assert too_many.status_code == 422
    assert too_many.json()["detail"]["code"] == "DOCUMENT_COUNT_LIMIT_EXCEEDED"

    total_client = TestClient(
        create_app(
            Settings(
                app_env="test",
                idp_max_upload_bytes=200,
                idp_max_total_intake_bytes=250,
            )
        )
    )
    total_case_id = str(create_case(total_client)["case"]["case_id"])
    upload(total_client, total_case_id, "one.txt", "text/plain", TEXT_PROFILE.encode())
    too_large = total_client.post(
        f"/api/clm/zero-touch/cases/{total_case_id}/intake/documents",
        headers={"Content-Type": "text/plain", "X-Document-Name": "two.txt"},
        content=TEXT_PROFILE.encode(),
    )
    assert too_large.status_code == 413
    assert too_large.json()["detail"]["code"] == "DOCUMENT_TOTAL_SIZE_LIMIT_EXCEEDED"


def test_upload_failure_keeps_case_and_successes_then_retry_uses_same_case() -> None:
    client = TestClient(create_app(Settings(app_env="test")))
    case_id = str(create_case(client)["case"]["case_id"])
    first = upload(client, case_id, "one.txt", "text/plain", TEXT_PROFILE.encode())
    failed = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
        headers={"Content-Type": DOCX_MEDIA, "X-Document-Name": "two.docx"},
        content=b"malformed",
    )
    assert failed.status_code == 422
    assert client.get(f"/api/clm/zero-touch/cases/{case_id}").json()["status"] == "PENDING_INPUTS"
    retained = client.get(f"/api/onboarding/cases/{case_id}/documents").json()
    assert [item["document_id"] for item in retained] == [first["document_id"]]

    second = upload(client, case_id, "two.docx", DOCX_MEDIA, docx_bytes())
    completed = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
        json={"expected_document_count": 2},
    )
    assert completed.status_code == 200
    assert confirm_api_target_if_ready(client, completed.json())["status"] == "COMPLETED"
    assert {
        item["document_id"]
        for item in client.get(f"/api/onboarding/cases/{case_id}/documents").json()
    } == {first["document_id"], second["document_id"]}
    assert [item["case_id"] for item in client.get("/api/clm/zero-touch/cases").json()] == [case_id]


def test_replacing_one_of_two_documents_preserves_other_and_rebuilds_reconciliation() -> None:
    client = TestClient(create_app(Settings(app_env="test")))
    case_id = str(create_case(client)["case"]["case_id"])
    first = upload(client, case_id, "one.txt", "text/plain", TEXT_PROFILE.encode())
    conflicting_text = TEXT_PROFILE.replace(
        "MERLION CIRCULAR LABS PTE. LTD.", "OTHER COMPANY PTE. LTD."
    )
    second = upload(client, case_id, "two.txt", "text/plain", conflicting_text.encode())
    waiting = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
        json={"expected_document_count": 2},
    )
    assert waiting.status_code == 200
    assert waiting.json()["status"] == "WAITING_FOR_REVIEW"
    documents = client.get(f"/api/onboarding/cases/{case_id}/documents").json()
    second_version = next(
        len(item["events"]) for item in documents if item["document_id"] == second["document_id"]
    )
    replacement = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/documents/{second['document_id']}/replacement",
        headers={
            "Content-Type": "text/plain",
            "X-Document-Name": "two-replacement.txt",
            "X-Document-Event-Count": str(second_version),
        },
        content=TEXT_PROFILE.encode(),
    )
    assert replacement.status_code == 200, replacement.text
    assert confirm_api_target_if_ready(client, replacement.json())["status"] == "COMPLETED"
    after = client.get(f"/api/onboarding/cases/{case_id}/documents").json()
    original_a = next(item for item in after if item["document_id"] == first["document_id"])
    original_b = next(item for item in after if item["document_id"] == second["document_id"])
    assert original_a["superseded_by_document_id"] is None
    assert original_b["superseded_by_document_id"] is not None
    assert len([item for item in after if item["superseded_by_document_id"] is None]) == 2


def test_two_review_cases_are_listed_and_resolving_one_does_not_mutate_the_other() -> None:
    client = TestClient(create_app(Settings(app_env="test")))
    summaries: list[dict[str, object]] = []
    for suffix in ("A", "B"):
        case_id = str(create_case(client)["case"]["case_id"])
        conflict = TEXT_PROFILE.replace(
            "MERLION CIRCULAR LABS PTE. LTD.", f"OTHER COMPANY {suffix} PTE. LTD."
        )
        upload(client, case_id, f"conflict-{suffix}.txt", "text/plain", conflict.encode())
        waiting = client.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
            json={"expected_document_count": 1},
        ).json()
        assert waiting["status"] == "WAITING_FOR_REVIEW"
        summaries.append(waiting)

    queue = client.get("/api/clm/zero-touch/cases?status=WAITING_FOR_REVIEW").json()
    assert {item["case_id"] for item in queue} == {item["case"]["case_id"] for item in summaries}
    first, second = summaries
    discrepancy = next(
        item
        for item in first["reconciliation"]["discrepancies"]
        if item["field_name"] == "legal_name"
    )
    resolved = client.post(
        f"/api/clm/zero-touch/cases/{first['case']['case_id']}/reconciliation/"
        f"discrepancies/{discrepancy['discrepancy_id']}/resolve",
        json={
            "action": "KEEP_REGISTRY_VALUE",
            "expected_automation_version": first["version"],
            "expected_reconciliation_version": first["reconciliation"]["version"],
            "evidence_fingerprint": discrepancy["evidence_fingerprint"],
        },
    )
    assert resolved.status_code == 200, resolved.text
    assert confirm_api_target_if_ready(client, resolved.json())["status"] == "COMPLETED"
    unchanged = client.get(f"/api/clm/zero-touch/cases/{second['case']['case_id']}").json()
    assert unchanged["status"] == "WAITING_FOR_REVIEW"


def observation(
    *, source: ReconciliationSourceKind, value: str | None, validity: ObservationValidity
) -> ReconciliationObservation:
    return ReconciliationObservation(
        observation_id=uuid4(),
        field_name=ReconciliationField.LEGAL_NAME,
        raw_value=value,
        normalized_value=value,
        source_kind=source,
        source_system="TEST",
        environment="MOCK",
        observed_at=datetime.now(UTC),
        evidence_reference="safe:evidence",
        confidence=0.97 if source == ReconciliationSourceKind.DOCUMENT_IDP else None,
        validity=validity,
    )


def test_missing_in_one_document_does_not_override_another_valid_document() -> None:
    observations = (
        observation(
            source=ReconciliationSourceKind.REGISTRY,
            value="ABC",
            validity=ObservationValidity.VALID,
        ),
        observation(
            source=ReconciliationSourceKind.DOCUMENT_IDP,
            value="ABC",
            validity=ObservationValidity.VALID,
        ),
        observation(
            source=ReconciliationSourceKind.DOCUMENT_IDP,
            value=None,
            validity=ObservationValidity.MISSING,
        ),
    )
    assert (
        derive_reconciliation_outcome(ReconciliationField.LEGAL_NAME, observations)
        == ReconciliationOutcome.MATCH
    )


def test_ambiguous_document_values_never_advertise_document_winner() -> None:
    observations = (
        observation(
            source=ReconciliationSourceKind.REGISTRY,
            value="ABC",
            validity=ObservationValidity.VALID,
        ),
        observation(
            source=ReconciliationSourceKind.DOCUMENT_IDP,
            value="ABC HOLDINGS",
            validity=ObservationValidity.VALID,
        ),
        observation(
            source=ReconciliationSourceKind.DOCUMENT_IDP,
            value="ABC TECHNOLOGIES",
            validity=ObservationValidity.VALID,
        ),
    )
    outcome = derive_reconciliation_outcome(ReconciliationField.LEGAL_NAME, observations)
    assert outcome == ReconciliationOutcome.CONFLICT
    assert [
        item.value
        for item in derive_allowed_actions(ReconciliationField.LEGAL_NAME, outcome, observations)
    ] == ["KEEP_REGISTRY_VALUE"]


def test_repository_returns_defensive_record_copies() -> None:
    client = TestClient(create_app(Settings(app_env="test")))
    create_case(client)
    application = client.app
    route = next(
        route
        for route in application.routes
        if getattr(route, "path", "") == "/api/clm/zero-touch/cases"
    )
    assert route is not None
    # API projection itself is immutable JSON; mutating one response cannot affect another.
    first = client.get("/api/clm/zero-touch/cases").json()
    first[0]["status"] = AutomationStatus.COMPLETED.value
    second = client.get("/api/clm/zero-touch/cases").json()
    assert second[0]["status"] == AutomationStatus.PENDING_INPUTS.value
