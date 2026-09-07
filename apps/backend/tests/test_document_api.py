from pathlib import Path

import httpx
import pytest

from app.composition import build_onboarding_service
from app.config import Settings
from app.connectors.idp import IdpDocumentInput, IdpProvider
from app.connectors.mock_idp import MockIdpProvider
from app.demo.scenarios import VALID_SME_UEN
from app.domain.documents import DocumentFieldKey
from app.main import create_app
from app.services.document_processing import DocumentProcessingService
from app.services.document_repository import InMemoryDocumentProcessingRepository
from app.services.onboarding import OnboardingService

PDF = (Path(__file__).parent / "fixtures" / "uat" / "clean-company-profile.pdf").read_bytes()


class RecordingProvider:
    def __init__(self) -> None:
        self.call_count = 0
        self._delegate = MockIdpProvider()

    @property
    def metadata(self) -> object:
        return self._delegate.metadata

    def process(self, document: IdpDocumentInput) -> object:
        self.call_count += 1
        return self._delegate.process(document)


class FixedProviderDemoControl:
    def __init__(self, provider: IdpProvider) -> None:
        self._provider = provider

    def provider_for(self, raw_scenario: str | None) -> IdpProvider:
        del raw_scenario
        return self._provider


def app_with_recording_provider(
    *,
    max_upload_bytes: int,
) -> tuple[object, RecordingProvider]:
    settings = Settings(
        app_env="test", demo_controls_enabled=True, idp_max_upload_bytes=max_upload_bytes
    )
    onboarding: OnboardingService = build_onboarding_service(settings=settings)
    provider = RecordingProvider()
    documents = DocumentProcessingService(
        cases=onboarding,
        idp=provider,
        repository=InMemoryDocumentProcessingRepository(),
        max_upload_bytes=max_upload_bytes,
        review_confidence_threshold=0.85,
    )
    application = create_app(
        settings,
        onboarding_service=onboarding,
        document_processing_service=documents,
        idp_demo_control=FixedProviderDemoControl(provider),  # type: ignore[arg-type]
    )
    return application, provider


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def create_case(client: httpx.AsyncClient) -> dict[str, object]:
    response = await client.post("/api/onboarding/cases", json={"uen": VALID_SME_UEN})
    assert response.status_code == 201
    return response.json()


async def upload(
    client: httpx.AsyncClient,
    case_id: object,
    scenario: str = "ALL_FIELDS_MATCH",
    *,
    content: bytes = PDF,
    name: str = "synthetic-corporate-profile.pdf",
    content_type: str = "application/pdf",
) -> httpx.Response:
    return await client.post(
        f"/api/demo/onboarding/cases/{case_id}/documents",
        content=content,
        headers={
            "Content-Type": content_type,
            "X-Document-Name": name,
            "X-Mock-IDP-Scenario": scenario,
        },
    )


async def review(
    client: httpx.AsyncClient,
    case_id: object,
    document_id: object,
    field_key: str,
    decision: str,
    *,
    corrected_value: str | None = None,
    note: str | None = None,
) -> httpx.Response:
    body: dict[str, object] = {"field_key": field_key, "decision": decision}
    if corrected_value is not None:
        body["corrected_value"] = corrected_value
    if note is not None:
        body["note"] = note
    return await client.post(
        f"/api/onboarding/cases/{case_id}/documents/{document_id}/reviews",
        json=body,
    )


@pytest.mark.anyio
async def test_upload_lists_four_compared_fields_and_preserves_parent_case() -> None:
    application = create_app(Settings(app_env="test", demo_controls_enabled=True))
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        original_case = await create_case(client)
        response = await upload(client, original_case["case_id"])
        listed = await client.get(f"/api/onboarding/cases/{original_case['case_id']}/documents")
        current_case = await client.get(f"/api/onboarding/cases/{original_case['case_id']}")

    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "REVIEW_REQUIRED"
    assert body["display_name"] == "synthetic-corporate-profile.pdf"
    assert body["media_type"] == "application/pdf"
    assert body["profile"] == "PROVISIONAL_CORPORATE"
    assert body["provider_environment"] == "MOCK"
    assert len(body["fields"]) == 4
    assert {item["comparison_status"] for item in body["fields"]} == {"MATCH"}
    assert {item["review_status"] for item in body["fields"]} == {"PENDING"}
    assert all(item["provenance"]["page_number"] == 1 for item in body["fields"])
    assert listed.status_code == 200 and listed.json() == [body]
    assert current_case.json() == original_case
    assert "SYNTHETIC API PDF" not in response.text


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("scenario", "field_key", "comparison", "confidence"),
    [
        ("FIELD_MISMATCH", "legal_name", "MISMATCH", 0.97),
        ("LOW_CONFIDENCE", "registered_address", "MATCH", 0.54),
        ("MISSING_FIELD", "registered_address", "MISSING_FROM_DOCUMENT", 0.0),
    ],
)
async def test_synthetic_processing_scenarios(
    scenario: str, field_key: str, comparison: str, confidence: float
) -> None:
    application = create_app(Settings(app_env="test", demo_controls_enabled=True))
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        case = await create_case(client)
        response = await upload(client, case["case_id"], scenario)

    target = next(item for item in response.json()["fields"] if item["field_key"] == field_key)
    assert response.status_code == 201
    assert target["comparison_status"] == comparison
    assert target["confidence"] == confidence


@pytest.mark.anyio
async def test_accept_reject_correct_and_review_completion_preserve_originals() -> None:
    application = create_app(Settings(app_env="test", demo_controls_enabled=True))
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        case = await create_case(client)
        uploaded = await upload(client, case["case_id"], "FIELD_MISMATCH")
        document_id = uploaded.json()["document_id"]
        original_name = next(
            item for item in uploaded.json()["fields"] if item["field_key"] == "legal_name"
        )["original_extracted_value"]

        accepted = await review(
            client, case["case_id"], document_id, "registration_number", "ACCEPTED"
        )
        rejected = await review(
            client,
            case["case_id"],
            document_id,
            "legal_name",
            "REJECTED",
            note="Synthetic mismatch",
        )
        corrected = await review(
            client,
            case["case_id"],
            document_id,
            "registered_address",
            "CORRECTED",
            corrected_value="18 Innovation Way, #04-02, 018956, SG",
        )
        completed = await review(
            client, case["case_id"], document_id, "country_of_incorporation", "ACCEPTED"
        )
        fetched = await client.get(
            f"/api/onboarding/cases/{case['case_id']}/documents/{document_id}"
        )

    assert accepted.json()["state"] == "REVIEW_REQUIRED"
    assert rejected.json()["state"] == "REVIEW_REQUIRED"
    assert corrected.json()["state"] == "REVIEW_REQUIRED"
    assert completed.status_code == 200
    assert completed.json()["state"] == "REVIEWED"
    assert fetched.json() == completed.json()
    name_field = next(
        item for item in completed.json()["fields"] if item["field_key"] == "legal_name"
    )
    assert name_field["original_extracted_value"] == original_name
    assert name_field["review_status"] == "REJECTED"
    assert name_field["reviewed_value"] is None
    address = next(
        item for item in completed.json()["fields"] if item["field_key"] == "registered_address"
    )
    assert address["original_extracted_value"] != address["reviewed_value"]
    assert address["review_status"] == "CORRECTED"
    assert completed.json()["events"][-1]["event_type"] == "DOCUMENT_REVIEW_COMPLETED"


@pytest.mark.anyio
async def test_review_retry_invalid_input_and_conflict_use_safe_results() -> None:
    application = create_app(Settings(app_env="test", demo_controls_enabled=True))
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        case = await create_case(client)
        uploaded = await upload(client, case["case_id"])
        document_id = uploaded.json()["document_id"]
        first = await review(client, case["case_id"], document_id, "legal_name", "ACCEPTED")
        retried = await review(client, case["case_id"], document_id, "legal_name", "ACCEPTED")
        conflict = await review(client, case["case_id"], document_id, "legal_name", "REJECTED")
        bad_correction = await review(
            client, case["case_id"], document_id, "registered_address", "CORRECTED"
        )
        unknown_field = await review(
            client, case["case_id"], document_id, "private_unknown_field", "ACCEPTED"
        )
        unknown_decision = await review(
            client, case["case_id"], document_id, "registered_address", "PRIVATE_DECISION"
        )

    assert retried.json() == first.json()
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "DOCUMENT_FIELD_REVIEW_CONFLICT"
    assert bad_correction.status_code == 422
    assert bad_correction.json()["detail"]["code"] == "DOCUMENT_CORRECTION_REQUIRED"
    assert unknown_field.status_code == 422
    assert "private_unknown_field" not in unknown_field.text
    assert unknown_decision.status_code == 422
    assert unknown_decision.json()["detail"]["code"] == "DOCUMENT_REVIEW_DECISION_INVALID"
    assert "PRIVATE_DECISION" not in unknown_decision.text


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("extra_body", "expected_code", "private_value"),
    [
        (
            {"private_extra": "PRIVATE_EXTRA_SENTINEL"},
            "DOCUMENT_REVIEW_REQUEST_INVALID",
            "PRIVATE_EXTRA_SENTINEL",
        ),
        ({"corrected_value": "C" * 513}, "DOCUMENT_REVIEW_TEXT_INVALID", "C" * 513),
        ({"note": "N" * 241}, "DOCUMENT_REVIEW_TEXT_INVALID", "N" * 241),
    ],
)
async def test_review_request_schema_rejects_extra_and_overlong_text_safely(
    extra_body: dict[str, str], expected_code: str, private_value: str
) -> None:
    application = create_app(Settings(app_env="test", demo_controls_enabled=True))
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        case = await create_case(client)
        uploaded = await upload(client, case["case_id"])
        response = await client.post(
            f"/api/onboarding/cases/{case['case_id']}/documents/"
            f"{uploaded.json()['document_id']}/reviews",
            json={
                "field_key": "registered_address",
                "decision": "CORRECTED",
                "corrected_value": "Safe correction",
                **extra_body,
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == expected_code
    assert private_value not in response.text


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("kwargs", "status_code", "code"),
    [
        ({"content_type": "text/plain"}, 415, "DOCUMENT_MEDIA_TYPE_UNSUPPORTED"),
        ({"name": "../../unsafe.pdf"}, 422, "DOCUMENT_NAME_INVALID"),
        ({"content": b""}, 422, "DOCUMENT_EMPTY"),
        ({"content": b"not-pdf"}, 422, "DOCUMENT_STRUCTURE_INVALID"),
        ({"scenario": "UNKNOWN"}, 422, "IDP_SCENARIO_INVALID"),
    ],
)
async def test_invalid_uploads_return_safe_detail(
    kwargs: dict[str, object], status_code: int, code: str
) -> None:
    application = create_app(Settings(app_env="test", demo_controls_enabled=True))
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        case = await create_case(client)
        response = await upload(client, case["case_id"], **kwargs)  # type: ignore[arg-type]
    assert response.status_code == status_code
    assert response.json()["detail"]["code"] == code
    assert "unsafe.pdf" not in response.text
    assert "not-pdf" not in response.text


@pytest.mark.anyio
async def test_oversize_missing_headers_unknown_case_and_unknown_document() -> None:
    application = create_app(
        Settings(app_env="test", demo_controls_enabled=True, idp_max_upload_bytes=16)
    )
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        case = await create_case(client)
        too_large = await upload(client, case["case_id"])
        missing_scenario = await client.post(
            f"/api/demo/onboarding/cases/{case['case_id']}/documents",
            content=b"%PDF-1.4\n%%EOF",
            headers={"Content-Type": "application/pdf", "X-Document-Name": "safe.pdf"},
        )
        missing_name = await client.post(
            f"/api/demo/onboarding/cases/{case['case_id']}/documents",
            content=b"%PDF-1.4\n%%EOF",
            headers={
                "Content-Type": "application/pdf",
                "X-Mock-IDP-Scenario": "ALL_FIELDS_MATCH",
            },
        )
        unknown_case = await client.get(
            "/api/onboarding/cases/00000000-0000-4000-8000-000000000999/documents"
        )
        unknown_document = await client.get(
            f"/api/onboarding/cases/{case['case_id']}/documents/"
            "00000000-0000-4000-8000-000000000998"
        )
    assert too_large.status_code == 413
    assert too_large.json()["detail"]["code"] == "DOCUMENT_TOO_LARGE"
    assert missing_scenario.json()["detail"]["code"] == "IDP_SCENARIO_INVALID"
    assert missing_name.json()["detail"]["code"] == "DOCUMENT_NAME_INVALID"
    assert unknown_case.status_code == 404
    assert unknown_case.json()["detail"]["code"] == "CASE_NOT_FOUND"
    assert unknown_document.status_code == 404
    assert unknown_document.json()["detail"]["code"] == "DOCUMENT_NOT_FOUND"


@pytest.mark.anyio
async def test_processor_failure_is_terminal_retrievable_and_parent_is_unchanged() -> None:
    application = create_app(Settings(app_env="test", demo_controls_enabled=True))
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        case = await create_case(client)
        failed = await upload(client, case["case_id"], "PROCESSOR_FAILURE")
        detail = failed.json()["detail"]
        fetched = await client.get(
            f"/api/onboarding/cases/{case['case_id']}/documents/{detail['document_id']}"
        )
        parent = await client.get(f"/api/onboarding/cases/{case['case_id']}")
    assert failed.status_code == 503
    assert detail["code"] == "IDP_PROCESSING_FAILED"
    assert fetched.status_code == 200
    assert fetched.json()["state"] == "FAILED"
    assert fetched.json()["fields"] == []
    assert fetched.json()["events"][-1]["event_type"] == "DOCUMENT_PROCESSING_FAILED"
    assert parent.json() == case
    assert "SYNTHETIC API PDF" not in failed.text + fetched.text


@pytest.mark.anyio
async def test_streaming_single_chunk_overflow_rejects_before_provider() -> None:
    application, provider = app_with_recording_provider(max_upload_bytes=len(PDF))
    transport = httpx.ASGITransport(app=application)

    async def oversized_chunk():
        yield b"X" * (len(PDF) + 1)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        case = await create_case(client)
        response = await client.post(
            f"/api/onboarding/cases/{case['case_id']}/documents",
            content=oversized_chunk(),
            headers={
                "Content-Type": "application/pdf",
                "X-Document-Name": "synthetic.pdf",
            },
        )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "DOCUMENT_TOO_LARGE"
    assert provider.call_count == 0


@pytest.mark.anyio
async def test_streaming_multiple_chunks_crossing_limit_rejects_before_provider() -> None:
    application, provider = app_with_recording_provider(max_upload_bytes=len(PDF))
    transport = httpx.ASGITransport(app=application)

    async def crossing_chunks():
        yield PDF[:10]
        yield PDF[10:]
        yield b"X"

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        case = await create_case(client)
        response = await client.post(
            f"/api/onboarding/cases/{case['case_id']}/documents",
            content=crossing_chunks(),
            headers={
                "Content-Type": "application/pdf",
                "X-Document-Name": "synthetic.pdf",
            },
        )

    assert response.status_code == 413
    assert provider.call_count == 0


@pytest.mark.anyio
async def test_streaming_exact_limit_structurally_valid_pdf_reaches_provider() -> None:
    application, provider = app_with_recording_provider(max_upload_bytes=len(PDF))
    transport = httpx.ASGITransport(app=application)

    async def exact_chunks():
        yield PDF[:10]
        yield PDF[10:]

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        case = await create_case(client)
        response = await client.post(
            f"/api/onboarding/cases/{case['case_id']}/documents",
            content=exact_chunks(),
            headers={
                "Content-Type": "application/pdf",
                "X-Document-Name": "synthetic.pdf",
            },
        )

    assert response.status_code == 201
    assert response.json()["state"] == "REVIEW_REQUIRED"
    assert provider.call_count == 1


def test_review_openapi_contract_exposes_enums_bounds_and_forbids_extras() -> None:
    openapi = create_app(Settings(app_env="test", demo_controls_enabled=True)).openapi()
    schema = openapi["components"]["schemas"]
    request_schema = schema["DocumentFieldReviewRequest"]

    assert request_schema["additionalProperties"] is False
    assert request_schema["properties"]["field_key"]["$ref"].endswith("DocumentFieldKey")
    assert request_schema["properties"]["decision"]["$ref"].endswith("ReviewDecision")
    assert schema["DocumentFieldKey"]["enum"] == [key.value for key in DocumentFieldKey]
    assert schema["ReviewDecision"]["enum"] == ["ACCEPTED", "REJECTED", "CORRECTED"]
    assert request_schema["properties"]["corrected_value"]["anyOf"][0]["maxLength"] == 512
    assert request_schema["properties"]["note"]["anyOf"][0]["maxLength"] == 240
    generic_upload_parameters = openapi["paths"]["/api/onboarding/cases/{case_id}/documents"][
        "post"
    ]["parameters"]
    assert "X-Mock-IDP-Scenario" not in {
        parameter["name"] for parameter in generic_upload_parameters
    }
    demo_upload_parameters = openapi["paths"]["/api/demo/onboarding/cases/{case_id}/documents"][
        "post"
    ]["parameters"]
    assert "X-Mock-IDP-Scenario" in {parameter["name"] for parameter in demo_upload_parameters}
