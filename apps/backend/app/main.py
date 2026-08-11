"""FastAPI application and Phase 04 application-facing endpoints."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api_models import (
    DocumentProcessingResponse,
    OnboardingCaseResponse,
    OwnershipAnalysisResponse,
)
from app.composition import (
    build_acra_connector as build_acra_connector,
)
from app.composition import (
    build_document_processing_service,
    build_mock_idp_demo_control,
    build_mock_ownership_demo_control,
    build_onboarding_service,
    build_ownership_analysis_service,
)
from app.config import Settings, get_settings
from app.connectors.idp import IdpProvider
from app.connectors.ownership import OwnershipProvider
from app.demo.idp_control import MockIdpDemoControl
from app.demo.ownership_control import MockOwnershipDemoControl
from app.demo.scenarios import (
    MockScenarioCatalogue,
    MockScenarioDiscovery,
    Phase01MockScenarioCatalogue,
)
from app.domain.documents import DocumentFieldKey, ReviewDecision
from app.domain.ownership import OwnershipCandidate
from app.services.document_errors import (
    DocumentProcessingInfrastructureError,
    DocumentRequestError,
)
from app.services.document_processing import DocumentProcessingService
from app.services.errors import OnboardingInfrastructureError
from app.services.onboarding import OnboardingService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_errors import (
    OwnershipInfrastructureError,
    OwnershipRequestError,
)


class HealthResponse(BaseModel):
    """Public, non-sensitive service health response."""

    status: Literal["ok"]
    service: str
    environment: str


class StartOnboardingRequest(BaseModel):
    """Small application-facing input; external target DTOs stay behind connectors."""

    uen: Annotated[str, Field(min_length=10, max_length=10, pattern=r"^[0-9]{9}[A-Z]$")]

    @field_validator("uen", mode="before")
    @classmethod
    def normalize_uen(cls, value: object) -> object:
        """Apply Phase 01 demo normalization before validation and case creation."""

        if isinstance(value, str):
            normalized = value.strip().upper()
            if not normalized:
                raise ValueError("UEN must not be blank")
            return normalized
        return value


class InfrastructureFailureDetail(BaseModel):
    """Safe retrievable-case metadata returned for unexpected stage failures."""

    code: str
    message: str
    case_id: UUID
    correlation_id: UUID


class DocumentFailureDetail(BaseModel):
    """Stable safe detail for document request and processing failures."""

    code: str
    message: str
    case_id: UUID | None = None
    document_id: UUID | None = None
    correlation_id: UUID | None = None


class OwnershipFailureDetail(BaseModel):
    """Stable safe detail for ownership request and terminal failures."""

    code: str
    message: str
    case_id: UUID | None = None
    analysis_id: UUID | None = None
    correlation_id: UUID | None = None


class DocumentFieldReviewRequest(BaseModel):
    """Bounded field decision with no caller-asserted reviewer identity."""

    model_config = ConfigDict(extra="forbid")

    field_key: DocumentFieldKey
    decision: ReviewDecision
    corrected_value: str | None = Field(default=None, max_length=512)
    note: str | None = Field(default=None, max_length=240)


def create_app(
    settings: Settings | None = None,
    onboarding_service: OnboardingService | None = None,
    document_processing_service: DocumentProcessingService | None = None,
    idp_demo_control: MockIdpDemoControl | None = None,
    ownership_analysis_service: OwnershipAnalysisService | None = None,
    ownership_demo_control: MockOwnershipDemoControl | None = None,
    scenario_catalogue: MockScenarioCatalogue | None = None,
) -> FastAPI:
    """Build the application with injectable settings for deterministic tests."""

    active_settings = settings or get_settings()
    application = FastAPI(title=active_settings.app_name, version="0.1.0")
    catalogue = scenario_catalogue or Phase01MockScenarioCatalogue()
    service = onboarding_service or build_onboarding_service(catalogue, active_settings)
    documents = document_processing_service or build_document_processing_service(
        service, active_settings
    )
    demo_idp = idp_demo_control or build_mock_idp_demo_control()
    ownership = ownership_analysis_service or build_ownership_analysis_service(
        service, active_settings
    )
    demo_ownership = ownership_demo_control or build_mock_ownership_demo_control()

    @application.exception_handler(RequestValidationError)
    async def safe_request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Project invalid request data through fixed messages without echoing input."""

        if request.url.path.endswith("/reviews"):
            locations = {str(part) for error in exc.errors() for part in error.get("loc", ())}
            if "field_key" in locations:
                detail = DocumentFailureDetail(
                    code="DOCUMENT_FIELD_INVALID",
                    message="The provisional document field is not supported.",
                )
            elif "decision" in locations:
                detail = DocumentFailureDetail(
                    code="DOCUMENT_REVIEW_DECISION_INVALID",
                    message="The document field review decision is not supported.",
                )
            elif locations.intersection({"corrected_value", "note"}):
                detail = DocumentFailureDetail(
                    code="DOCUMENT_REVIEW_TEXT_INVALID",
                    message="Review text is invalid or exceeds the configured limit.",
                )
            else:
                detail = DocumentFailureDetail(
                    code="DOCUMENT_REVIEW_REQUEST_INVALID",
                    message="The document field review request is invalid.",
                )
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content={"detail": detail.model_dump(mode="json", exclude_none=True)},
            )
        return await request_validation_exception_handler(request, exc)

    def get_onboarding_service() -> OnboardingService:
        return service

    def get_document_processing_service() -> DocumentProcessingService:
        return documents

    def get_ownership_analysis_service() -> OwnershipAnalysisService:
        return ownership

    def load_ownership_request(
        *,
        case_id: UUID,
        active_ownership: OwnershipAnalysisService,
        provider: OwnershipProvider | None,
    ) -> OwnershipAnalysisResponse:
        try:
            record = active_ownership.load(case_id=case_id, provider=provider)
        except OwnershipRequestError as exc:
            raise _ownership_http_error(exc) from None
        except OwnershipInfrastructureError as exc:
            detail = OwnershipFailureDetail(
                code=exc.code,
                message=exc.public_message,
                case_id=exc.case_id,
                analysis_id=exc.analysis_id,
                correlation_id=exc.correlation_id,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail.model_dump(mode="json", exclude_none=True),
            ) from None
        return OwnershipAnalysisResponse.from_domain(record)

    async def process_document_request(
        *,
        case_id: UUID,
        request: Request,
        active_documents: DocumentProcessingService,
        display_name: str,
        provider: IdpProvider | None,
    ) -> DocumentProcessingResponse:
        try:
            active_documents.validate_upload_metadata(
                case_id=case_id,
                display_name=display_name,
                content_type=request.headers.get("content-type", ""),
            )
        except DocumentRequestError as exc:
            raise _document_http_error(exc) from None

        body = await _read_bounded_body(request, active_documents.max_upload_bytes)
        try:
            record = active_documents.create_document(
                case_id=case_id,
                display_name=display_name,
                content_type=request.headers.get("content-type", ""),
                content=body,
                provider=provider,
            )
        except DocumentRequestError as exc:
            raise _document_http_error(exc) from None
        except DocumentProcessingInfrastructureError as exc:
            detail = DocumentFailureDetail(
                code=exc.code,
                message=exc.public_message,
                case_id=exc.case_id,
                document_id=exc.document_id,
                correlation_id=exc.correlation_id,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail.model_dump(mode="json", exclude_none=True),
            ) from None
        return DocumentProcessingResponse.from_domain(record)

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=active_settings.app_name,
            environment=active_settings.app_env,
        )

    @application.get(
        "/api/onboarding/mock-scenarios",
        response_model=MockScenarioDiscovery,
        tags=["onboarding"],
    )
    def mock_scenarios() -> MockScenarioDiscovery:
        registry_environment: Literal["MOCK", "SANDBOX"] = (
            "MOCK" if active_settings.acra_connector_mode == "mock" else "SANDBOX"
        )
        discovery = catalogue.discovery(registry_environment)
        return discovery.model_copy(
            update={
                "simulation": discovery.simulation.model_copy(
                    update={
                        "idp_review_confidence_threshold": (
                            active_settings.idp_review_confidence_threshold
                        ),
                        "ubo_ownership_threshold_percent": (
                            active_settings.ubo_ownership_threshold_percent
                        ),
                    }
                )
            }
        )

    @application.post(
        "/api/onboarding/cases",
        response_model=OnboardingCaseResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["onboarding"],
    )
    def create_onboarding_case(
        request: StartOnboardingRequest,
        active_service: Annotated[OnboardingService, Depends(get_onboarding_service)],
    ) -> OnboardingCaseResponse:
        try:
            return OnboardingCaseResponse.from_domain(active_service.create_case(request.uen))
        except OnboardingInfrastructureError as exc:
            detail = InfrastructureFailureDetail(
                code=exc.code,
                message=exc.public_message,
                case_id=exc.case_id,
                correlation_id=exc.correlation_id,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail.model_dump(mode="json"),
            ) from None

    @application.get(
        "/api/onboarding/cases/{case_id}",
        response_model=OnboardingCaseResponse,
        tags=["onboarding"],
    )
    def get_onboarding_case(
        case_id: UUID,
        active_service: Annotated[OnboardingService, Depends(get_onboarding_service)],
    ) -> OnboardingCaseResponse:
        case = active_service.get_case(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="Onboarding case not found")
        return OnboardingCaseResponse.from_domain(case)

    @application.post(
        "/api/onboarding/cases/{case_id}/ownership/load",
        response_model=OwnershipAnalysisResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["ownership"],
    )
    def load_ownership(
        case_id: UUID,
        active_ownership: Annotated[
            OwnershipAnalysisService, Depends(get_ownership_analysis_service)
        ],
    ) -> OwnershipAnalysisResponse:
        """Generic provider-neutral load using the composed ownership provider."""

        return load_ownership_request(
            case_id=case_id,
            active_ownership=active_ownership,
            provider=None,
        )

    @application.post(
        "/api/demo/onboarding/cases/{case_id}/ownership/load",
        response_model=OwnershipAnalysisResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["demo"],
    )
    def load_mock_ownership(
        case_id: UUID,
        active_ownership: Annotated[
            OwnershipAnalysisService, Depends(get_ownership_analysis_service)
        ],
        x_mock_ownership_scenario: Annotated[
            str | None, Header(alias="X-Mock-Ownership-Scenario")
        ] = None,
    ) -> OwnershipAnalysisResponse:
        try:
            provider = demo_ownership.provider_for(x_mock_ownership_scenario)
        except ValueError:
            raise _ownership_http_error(
                OwnershipRequestError(
                    code="OWNERSHIP_SCENARIO_INVALID",
                    message="The Mock ownership scenario is not supported.",
                )
            ) from None
        return load_ownership_request(
            case_id=case_id,
            active_ownership=active_ownership,
            provider=provider,
        )

    @application.post(
        "/api/onboarding/cases/{case_id}/ownership/analyze",
        response_model=OwnershipAnalysisResponse,
        tags=["ownership"],
    )
    def analyze_ownership(
        case_id: UUID,
        active_ownership: Annotated[
            OwnershipAnalysisService, Depends(get_ownership_analysis_service)
        ],
    ) -> OwnershipAnalysisResponse:
        try:
            record = active_ownership.analyze(case_id=case_id)
        except OwnershipRequestError as exc:
            raise _ownership_http_error(exc) from None
        except OwnershipInfrastructureError as exc:
            detail = OwnershipFailureDetail(
                code=exc.code,
                message=exc.public_message,
                case_id=exc.case_id,
                analysis_id=exc.analysis_id,
                correlation_id=exc.correlation_id,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail.model_dump(mode="json", exclude_none=True),
            ) from None
        return OwnershipAnalysisResponse.from_domain(record)

    @application.get(
        "/api/onboarding/cases/{case_id}/ownership",
        response_model=OwnershipAnalysisResponse,
        tags=["ownership"],
    )
    def get_ownership(
        case_id: UUID,
        active_ownership: Annotated[
            OwnershipAnalysisService, Depends(get_ownership_analysis_service)
        ],
    ) -> OwnershipAnalysisResponse:
        try:
            record = active_ownership.get(case_id=case_id)
        except OwnershipRequestError as exc:
            raise _ownership_http_error(exc) from None
        if record is None:
            raise _ownership_http_error(
                OwnershipRequestError(
                    code="OWNERSHIP_NOT_LOADED",
                    message="Ownership data has not been loaded for this case.",
                )
            )
        return OwnershipAnalysisResponse.from_domain(record)

    @application.get(
        "/api/onboarding/cases/{case_id}/ubo-candidates",
        response_model=list[OwnershipCandidate],
        tags=["ownership"],
    )
    def get_ubo_candidates(
        case_id: UUID,
        active_ownership: Annotated[
            OwnershipAnalysisService, Depends(get_ownership_analysis_service)
        ],
    ) -> list[OwnershipCandidate]:
        try:
            record = active_ownership.get(case_id=case_id)
        except OwnershipRequestError as exc:
            raise _ownership_http_error(exc) from None
        if record is None:
            raise _ownership_http_error(
                OwnershipRequestError(
                    code="OWNERSHIP_NOT_LOADED",
                    message="Ownership data has not been loaded for this case.",
                )
            )
        return [candidate.model_copy(deep=True) for candidate in record.candidates]

    @application.post(
        "/api/onboarding/cases/{case_id}/documents",
        response_model=DocumentProcessingResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["documents"],
    )
    async def create_document(
        case_id: UUID,
        request: Request,
        active_documents: Annotated[
            DocumentProcessingService, Depends(get_document_processing_service)
        ],
        x_document_name: Annotated[str | None, Header(alias="X-Document-Name")] = None,
    ) -> DocumentProcessingResponse:
        """Generic provider-neutral document endpoint using the composed provider."""

        return await process_document_request(
            case_id=case_id,
            request=request,
            active_documents=active_documents,
            display_name=x_document_name or "",
            provider=None,
        )

    @application.post(
        "/api/demo/onboarding/cases/{case_id}/documents",
        response_model=DocumentProcessingResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["demo"],
    )
    async def create_mock_demo_document(
        case_id: UUID,
        request: Request,
        active_documents: Annotated[
            DocumentProcessingService, Depends(get_document_processing_service)
        ],
        x_document_name: Annotated[str | None, Header(alias="X-Document-Name")] = None,
        x_mock_idp_scenario: Annotated[str | None, Header(alias="X-Mock-IDP-Scenario")] = None,
    ) -> DocumentProcessingResponse:
        try:
            provider = demo_idp.provider_for(x_mock_idp_scenario)
        except ValueError:
            raise _document_http_error(
                DocumentRequestError(
                    code="IDP_SCENARIO_INVALID",
                    message="The Mock IDP scenario is not supported.",
                )
            ) from None

        return await process_document_request(
            case_id=case_id,
            request=request,
            active_documents=active_documents,
            display_name=x_document_name or "",
            provider=provider,
        )

    @application.get(
        "/api/onboarding/cases/{case_id}/documents",
        response_model=list[DocumentProcessingResponse],
        tags=["documents"],
    )
    def list_documents(
        case_id: UUID,
        active_documents: Annotated[
            DocumentProcessingService, Depends(get_document_processing_service)
        ],
    ) -> list[DocumentProcessingResponse]:
        try:
            records = active_documents.list_documents(case_id=case_id)
        except DocumentRequestError as exc:
            raise _document_http_error(exc) from None
        return [DocumentProcessingResponse.from_domain(record) for record in records]

    @application.get(
        "/api/onboarding/cases/{case_id}/documents/{document_id}",
        response_model=DocumentProcessingResponse,
        tags=["documents"],
    )
    def get_document(
        case_id: UUID,
        document_id: UUID,
        active_documents: Annotated[
            DocumentProcessingService, Depends(get_document_processing_service)
        ],
    ) -> DocumentProcessingResponse:
        record = active_documents.get_document(case_id=case_id, document_id=document_id)
        if record is None:
            raise _document_http_error(
                DocumentRequestError(
                    code="DOCUMENT_NOT_FOUND",
                    message="The document review record was not found.",
                )
            )
        return DocumentProcessingResponse.from_domain(record)

    @application.post(
        "/api/onboarding/cases/{case_id}/documents/{document_id}/reviews",
        response_model=DocumentProcessingResponse,
        tags=["documents"],
    )
    def review_document_field(
        case_id: UUID,
        document_id: UUID,
        review: DocumentFieldReviewRequest,
        active_documents: Annotated[
            DocumentProcessingService, Depends(get_document_processing_service)
        ],
    ) -> DocumentProcessingResponse:
        try:
            record = active_documents.review_field(
                case_id=case_id,
                document_id=document_id,
                field_key=review.field_key,
                decision=review.decision,
                corrected_value=review.corrected_value,
                note=review.note,
            )
        except DocumentRequestError as exc:
            raise _document_http_error(exc) from None
        return DocumentProcessingResponse.from_domain(record)

    return application


async def _read_bounded_body(request: Request, limit: int) -> bytes:
    """Read a request body without accepting more than the configured PDF limit."""

    declared_length = request.headers.get("content-length")
    if declared_length is not None:
        try:
            parsed_length = int(declared_length)
        except ValueError:
            raise _document_http_error(
                DocumentRequestError(
                    code="DOCUMENT_LENGTH_INVALID",
                    message="The upload length is invalid.",
                )
            ) from None
        if parsed_length < 0:
            raise _document_http_error(
                DocumentRequestError(
                    code="DOCUMENT_LENGTH_INVALID",
                    message="The upload length is invalid.",
                )
            )
        if parsed_length > limit:
            raise _document_http_error(
                DocumentRequestError(
                    code="DOCUMENT_TOO_LARGE",
                    message="The uploaded PDF exceeds the configured size limit.",
                )
            )

    body = bytearray()
    async for chunk in request.stream():
        remaining_capacity = limit - len(body)
        if len(chunk) > remaining_capacity:
            raise _document_http_error(
                DocumentRequestError(
                    code="DOCUMENT_TOO_LARGE",
                    message="The uploaded PDF exceeds the configured size limit.",
                )
            )
        body.extend(chunk)
    return bytes(body)


def _document_http_error(exc: DocumentRequestError) -> HTTPException:
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    if exc.code in {"ONBOARDING_CASE_NOT_FOUND", "DOCUMENT_NOT_FOUND"}:
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.code == "DOCUMENT_MEDIA_TYPE_UNSUPPORTED":
        status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    elif exc.code == "DOCUMENT_TOO_LARGE":
        status_code = status.HTTP_413_CONTENT_TOO_LARGE
    elif exc.code in {
        "DOCUMENT_FIELD_REVIEW_CONFLICT",
        "DOCUMENT_NOT_REVIEWABLE",
    }:
        status_code = status.HTTP_409_CONFLICT
    detail = DocumentFailureDetail(code=exc.code, message=exc.public_message)
    return HTTPException(
        status_code=status_code,
        detail=detail.model_dump(mode="json", exclude_none=True),
    )


def _ownership_http_error(exc: OwnershipRequestError) -> HTTPException:
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    if exc.code in {"ONBOARDING_CASE_NOT_FOUND", "OWNERSHIP_NOT_LOADED"}:
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.code in {
        "OWNERSHIP_ALREADY_LOADED",
        "OWNERSHIP_NOT_ANALYZABLE",
        "OWNERSHIP_ROOT_UNAVAILABLE",
        "OWNERSHIP_LOAD_CONFLICT",
        "OWNERSHIP_ANALYSIS_CONFLICT",
    }:
        status_code = status.HTTP_409_CONFLICT
    detail = OwnershipFailureDetail(code=exc.code, message=exc.public_message)
    return HTTPException(
        status_code=status_code,
        detail=detail.model_dump(mode="json", exclude_none=True),
    )


app = create_app()
