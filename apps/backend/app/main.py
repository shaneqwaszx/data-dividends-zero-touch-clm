"""FastAPI application and Phase 07 application-facing endpoints."""

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api_models import (
    BrowserTargetOperationEvidence,
    ClmCaseSummaryResponse,
    DocumentProcessingResponse,
    OnboardingCaseResponse,
    OwnershipAnalysisResponse,
    ZeroTouchCaseSummaryResponse,
)
from app.composition import (
    build_acra_connector as build_acra_connector,
)
from app.composition import (
    build_clm_orchestration_service,
    build_document_processing_service,
    build_mock_idp_demo_control,
    build_mock_ownership_demo_control,
    build_onboarding_service,
    build_ownership_analysis_service,
    build_zero_touch_demo_control,
    build_zero_touch_orchestrator,
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
    SimulationProfile,
)
from app.demo.uat_evidence import UatEvidenceExport, build_uat_evidence
from app.demo.zero_touch_control import ZeroTouchDemoControl, ZeroTouchDemoScenario
from app.domain.clm import GoldTierSubmissionPlan
from app.domain.documents import DocumentFieldKey, ReviewDecision
from app.domain.ownership import OwnershipCandidate
from app.domain.target_submission import GoldTierOperationMarker, GoldTierTargetOutcome
from app.domain.zero_touch import ExceptionResolutionAction, ZeroTouchAutomationRecord
from app.services.clm_errors import ClmInfrastructureError, ClmRequestError
from app.services.clm_orchestration import ClmOrchestrationService
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
from app.services.zero_touch_errors import (
    ZeroTouchInfrastructureError,
    ZeroTouchRequestError,
)
from app.services.zero_touch_orchestration import ZeroTouchOrchestrator


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


class ClmFailureDetail(BaseModel):
    """Stable CLM error projection without evidence or connector detail."""

    code: str
    message: str
    case_id: UUID | None = None
    orchestration_id: UUID | None = None
    correlation_id: UUID | None = None


class DocumentFieldReviewRequest(BaseModel):
    """Bounded field decision with no caller-asserted reviewer identity."""

    model_config = ConfigDict(extra="forbid")

    field_key: DocumentFieldKey
    decision: ReviewDecision
    corrected_value: str | None = Field(default=None, max_length=512)
    note: str | None = Field(default=None, max_length=240)


class ZeroTouchDemoStartRequest(StartOnboardingRequest):
    model_config = ConfigDict(extra="forbid")

    scenario: ZeroTouchDemoScenario = ZeroTouchDemoScenario.STRAIGHT_THROUGH


class ZeroTouchExceptionResolutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ExceptionResolutionAction
    expected_automation_version: int = Field(ge=1)
    evidence_version: str = Field(min_length=1, max_length=128)


class ZeroTouchFailureDetail(BaseModel):
    code: str
    message: str
    case_id: UUID | None = None
    automation_id: UUID | None = None


def create_app(
    settings: Settings | None = None,
    onboarding_service: OnboardingService | None = None,
    document_processing_service: DocumentProcessingService | None = None,
    idp_demo_control: MockIdpDemoControl | None = None,
    ownership_analysis_service: OwnershipAnalysisService | None = None,
    ownership_demo_control: MockOwnershipDemoControl | None = None,
    clm_orchestration_service: ClmOrchestrationService | None = None,
    zero_touch_orchestrator: ZeroTouchOrchestrator | None = None,
    zero_touch_demo_control: ZeroTouchDemoControl | None = None,
    scenario_catalogue: MockScenarioCatalogue | None = None,
) -> FastAPI:
    """Build the application with injectable settings for deterministic tests."""

    active_settings = settings or get_settings()
    application = FastAPI(title=active_settings.app_name, version="0.1.0")
    catalogue = scenario_catalogue or Phase01MockScenarioCatalogue()
    zero_touch_demo = zero_touch_demo_control or build_zero_touch_demo_control()
    service = onboarding_service or build_onboarding_service(
        catalogue,
        active_settings,
        target_finalization_fault=(
            zero_touch_demo.should_fail_target_finalization
            if active_settings.demo_controls_enabled
            else None
        ),
    )
    documents = document_processing_service or build_document_processing_service(
        service, active_settings
    )
    demo_idp = idp_demo_control or build_mock_idp_demo_control()
    ownership = ownership_analysis_service or build_ownership_analysis_service(
        service, active_settings
    )
    demo_ownership = ownership_demo_control or build_mock_ownership_demo_control()
    clm = clm_orchestration_service or build_clm_orchestration_service(
        service,
        documents,
        ownership,
    )
    zero_touch = zero_touch_orchestrator or build_zero_touch_orchestrator(
        service, documents, ownership, clm, active_settings
    )

    def require_demo_controls() -> None:
        if not active_settings.demo_controls_enabled:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "DEMO_CONTROLS_DISABLED",
                    "message": "Demo controls are not enabled in this environment.",
                },
            )

    def execution_profile() -> SimulationProfile:
        registry_environment: Literal["MOCK", "SANDBOX"] = (
            "MOCK" if active_settings.acra_connector_mode == "mock" else "SANDBOX"
        )
        return SimulationProfile(
            registry_environment=registry_environment,
            idp_environment=(
                "LOCAL" if active_settings.idp_connector_mode == "local_pdf_text" else "MOCK"
            ),
            idp_provider=(
                "LOCAL_PDF_TEXT"
                if active_settings.idp_connector_mode == "local_pdf_text"
                else "MOCK_IDP"
            ),
            idp_review_confidence_threshold=(active_settings.idp_review_confidence_threshold),
            ubo_ownership_threshold_percent=(active_settings.ubo_ownership_threshold_percent),
        )

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
        if "/zero-touch/" in request.url.path and request.url.path.endswith("/resolve"):
            zero_detail = ZeroTouchFailureDetail(
                code="ZERO_TOUCH_RESOLUTION_INVALID",
                message="The exception resolution request is invalid.",
            )
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content={"detail": zero_detail.model_dump(mode="json", exclude_none=True)},
            )
        return await request_validation_exception_handler(request, exc)

    def get_onboarding_service() -> OnboardingService:
        return service

    def get_document_processing_service() -> DocumentProcessingService:
        return documents

    def get_ownership_analysis_service() -> OwnershipAnalysisService:
        return ownership

    def get_clm_orchestration_service() -> ClmOrchestrationService:
        return clm

    def get_zero_touch_orchestrator() -> ZeroTouchOrchestrator:
        return zero_touch

    def clm_response(record: object) -> ClmCaseSummaryResponse:
        from app.domain.clm import ClmOrchestrationRecord

        orchestration = ClmOrchestrationRecord.model_validate(record)
        case = service.get_case(orchestration.case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="CLM case not found")
        return ClmCaseSummaryResponse.from_domain(orchestration, case)

    def target_operation_evidence(
        outcome: GoldTierTargetOutcome | None,
    ) -> tuple[BrowserTargetOperationEvidence, ...]:
        """Project only bounded operation outcomes; never target requests or receipts."""

        order = (
            GoldTierOperationMarker.SEARCH,
            GoldTierOperationMarker.SHELL,
            GoldTierOperationMarker.POLICY,
            GoldTierOperationMarker.AMEND,
        )
        attempted = outcome.completed_operations if outcome is not None else ()
        last_attempted = attempted[-1] if attempted else None
        result: list[BrowserTargetOperationEvidence] = []
        for operation in order:
            operation_status: Literal[
                "NOT_ATTEMPTED",
                "IN_PROGRESS",
                "NO_MATCH",
                "MATCH_FOUND",
                "CREATED",
                "SUCCESS",
                "FAILED",
            ] = "NOT_ATTEMPTED"
            if operation in attempted:
                if operation == GoldTierOperationMarker.SEARCH:
                    operation_status = (
                        "MATCH_FOUND"
                        if outcome is not None
                        and outcome.error_code == "GT_EXISTING_PARTY_REVIEW_REQUIRED"
                        else "FAILED"
                        if outcome is not None
                        and outcome.error_code is not None
                        and last_attempted == operation
                        else "NO_MATCH"
                    )
                elif (
                    outcome is not None
                    and outcome.error_code is not None
                    and last_attempted == operation
                ):
                    operation_status = "FAILED"
                elif operation in {
                    GoldTierOperationMarker.SHELL,
                    GoldTierOperationMarker.POLICY,
                }:
                    operation_status = "CREATED"
                else:
                    operation_status = "SUCCESS"
            result.append(
                BrowserTargetOperationEvidence(
                    operation=operation.value,
                    status=operation_status,
                )
            )
        return tuple(result)

    def zero_touch_response(record: object) -> ZeroTouchCaseSummaryResponse:
        automation = ZeroTouchAutomationRecord.model_validate(record)
        case = service.get_case(automation.case_id)
        clm_record = clm.get(case_id=automation.case_id)
        if case is None or clm_record is None:
            raise HTTPException(status_code=404, detail="Zero-touch case not found")
        target_outcome = (
            service.get_target_outcome(clm_record.submission_snapshot.submission_id)
            if clm_record.submission_snapshot is not None
            else None
        )
        return ZeroTouchCaseSummaryResponse.from_domain(
            automation,
            clm_record,
            case,
            target_operations=target_operation_evidence(target_outcome),
        )

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
        "/api/system/execution-profile",
        response_model=SimulationProfile,
        tags=["system"],
    )
    def get_execution_profile() -> SimulationProfile:
        """Expose only truthful, non-sensitive connector environment labels."""

        return execution_profile()

    @application.get(
        "/api/onboarding/mock-scenarios",
        response_model=MockScenarioDiscovery,
        tags=["onboarding"],
    )
    def mock_scenarios() -> MockScenarioDiscovery:
        require_demo_controls()
        profile = execution_profile()
        discovery = catalogue.discovery(profile.registry_environment)
        return discovery.model_copy(update={"simulation": profile})

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
        "/api/clm/cases",
        response_model=ClmCaseSummaryResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["clm"],
    )
    def create_clm_case(
        request: StartOnboardingRequest,
        active_clm: Annotated[ClmOrchestrationService, Depends(get_clm_orchestration_service)],
    ) -> ClmCaseSummaryResponse:
        try:
            return clm_response(active_clm.create_case(request.uen))
        except ClmInfrastructureError as exc:
            detail = ClmFailureDetail(
                code=exc.code,
                message=exc.public_message,
                case_id=exc.case_id,
                orchestration_id=exc.orchestration_id,
                correlation_id=exc.correlation_id,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail.model_dump(mode="json", exclude_none=True),
            ) from None
        except ClmRequestError as exc:
            raise _clm_http_error(exc) from None

    @application.get(
        "/api/clm/cases/{case_id}",
        response_model=ClmCaseSummaryResponse,
        tags=["clm"],
    )
    def get_clm_case(
        case_id: UUID,
        active_clm: Annotated[ClmOrchestrationService, Depends(get_clm_orchestration_service)],
    ) -> ClmCaseSummaryResponse:
        record = active_clm.get(case_id=case_id)
        if record is None:
            raise _clm_http_error(
                ClmRequestError(
                    code="CLM_CASE_NOT_FOUND",
                    message="The staged CLM case was not found.",
                )
            )
        return clm_response(record)

    @application.post(
        "/api/clm/cases/{case_id}/readiness/evaluate",
        response_model=ClmCaseSummaryResponse,
        tags=["clm"],
    )
    def evaluate_clm_readiness(
        case_id: UUID,
        active_clm: Annotated[ClmOrchestrationService, Depends(get_clm_orchestration_service)],
    ) -> ClmCaseSummaryResponse:
        try:
            return clm_response(active_clm.evaluate(case_id=case_id))
        except ClmRequestError as exc:
            raise _clm_http_error(exc) from None

    @application.get(
        "/api/clm/cases/{case_id}/submission-plan",
        response_model=GoldTierSubmissionPlan,
        tags=["clm"],
    )
    def get_clm_submission_plan(
        case_id: UUID,
        active_clm: Annotated[ClmOrchestrationService, Depends(get_clm_orchestration_service)],
    ) -> GoldTierSubmissionPlan:
        try:
            return active_clm.submission_plan(case_id=case_id)
        except ClmRequestError as exc:
            raise _clm_http_error(exc) from None

    @application.post(
        "/api/clm/cases/{case_id}/submit",
        response_model=ClmCaseSummaryResponse,
        tags=["clm"],
    )
    def submit_clm_case(
        case_id: UUID,
        active_clm: Annotated[ClmOrchestrationService, Depends(get_clm_orchestration_service)],
    ) -> ClmCaseSummaryResponse:
        try:
            return clm_response(active_clm.submit(case_id=case_id))
        except ClmRequestError as exc:
            raise _clm_http_error(exc) from None
        except ClmInfrastructureError as exc:
            detail = ClmFailureDetail(
                code=exc.code,
                message=exc.public_message,
                case_id=exc.case_id,
                orchestration_id=exc.orchestration_id,
                correlation_id=exc.correlation_id,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail.model_dump(mode="json", exclude_none=True),
            ) from None

    @application.post(
        "/api/clm/zero-touch/cases",
        response_model=ZeroTouchCaseSummaryResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["zero-touch"],
    )
    def create_zero_touch_case(
        request: StartOnboardingRequest,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
    ) -> ZeroTouchCaseSummaryResponse:
        try:
            return zero_touch_response(active_zero_touch.create_case(request.uen))
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None

    @application.post(
        "/api/demo/clm/zero-touch/cases",
        response_model=ZeroTouchCaseSummaryResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["demo"],
    )
    def create_demo_zero_touch_case(
        request: ZeroTouchDemoStartRequest,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
    ) -> ZeroTouchCaseSummaryResponse:
        require_demo_controls()
        uen = zero_touch_demo.uen_for(request.uen, request.scenario)
        try:
            record = active_zero_touch.create_case(uen)
            zero_touch_demo.register(record.case_id, request.scenario)
            return zero_touch_response(record)
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None

    @application.get(
        "/api/clm/zero-touch/cases/{case_id}",
        response_model=ZeroTouchCaseSummaryResponse,
        tags=["zero-touch"],
    )
    def get_zero_touch_case(
        case_id: UUID,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
    ) -> ZeroTouchCaseSummaryResponse:
        record = active_zero_touch.get(case_id=case_id)
        if record is None:
            raise _zero_touch_http_error(
                ZeroTouchRequestError(
                    code="ZERO_TOUCH_CASE_NOT_FOUND",
                    message="The zero-touch onboarding case was not found.",
                )
            )
        return zero_touch_response(record)

    @application.get(
        "/api/demo/clm/zero-touch/cases/{case_id}/uat-evidence",
        response_model=UatEvidenceExport,
        tags=["demo"],
    )
    def export_zero_touch_uat_evidence(
        case_id: UUID,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
        active_clm: Annotated[ClmOrchestrationService, Depends(get_clm_orchestration_service)],
    ) -> UatEvidenceExport:
        require_demo_controls()
        scenario = zero_touch_demo.registered_scenario_for(case_id)
        automation = active_zero_touch.get(case_id=case_id)
        clm_record = active_clm.get(case_id=case_id)
        case = service.get_case(case_id)
        if scenario is None or automation is None or clm_record is None or case is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "DEMO_UAT_CASE_NOT_FOUND",
                    "message": "The synthetic UAT case was not found.",
                },
            )
        return build_uat_evidence(
            automation=automation,
            clm=clm_record,
            scenario=scenario,
            synthetic_uen=case.requested_uen,
            simulation=execution_profile(),
            target_calls=active_clm.attempted_target_operations(case_id=case_id),
            exported_at=datetime.now(UTC),
        )

    async def attach_zero_touch_document_request(
        *,
        case_id: UUID,
        request: Request,
        active_zero_touch: ZeroTouchOrchestrator,
        display_name: str,
        use_demo_provider: bool,
    ) -> ZeroTouchCaseSummaryResponse:
        try:
            documents.validate_upload_metadata(
                case_id=case_id,
                display_name=display_name,
                content_type=request.headers.get("content-type", ""),
            )
            body = await _read_bounded_body(request, documents.max_upload_bytes)
            idp_provider = None
            ownership_provider = None
            if use_demo_provider:
                case = service.get_case(case_id)
                if case is None or case.entity is None:
                    raise ZeroTouchRequestError(
                        code="ZERO_TOUCH_CASE_NOT_FOUND",
                        message="The zero-touch onboarding case was not found.",
                    )
                idp_provider = zero_touch_demo.idp_provider_for(case_id, case.entity)
                ownership_provider = zero_touch_demo.ownership_provider_for(case_id)
            record = active_zero_touch.attach_document(
                case_id=case_id,
                display_name=display_name,
                content_type=request.headers.get("content-type", ""),
                content=body,
                idp_provider=idp_provider,
                ownership_provider=ownership_provider,
            )
            return zero_touch_response(record)
        except DocumentRequestError as exc:
            raise _document_http_error(exc) from None
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
        except ZeroTouchInfrastructureError as exc:
            detail = ZeroTouchFailureDetail(
                code=exc.code,
                message=exc.public_message,
                case_id=exc.case_id,
                automation_id=exc.automation_id,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail.model_dump(mode="json", exclude_none=True),
            ) from None

    @application.post(
        "/api/clm/zero-touch/cases/{case_id}/documents",
        response_model=ZeroTouchCaseSummaryResponse,
        tags=["zero-touch"],
    )
    async def attach_zero_touch_document(
        case_id: UUID,
        request: Request,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
        x_document_name: Annotated[str | None, Header(alias="X-Document-Name")] = None,
    ) -> ZeroTouchCaseSummaryResponse:
        return await attach_zero_touch_document_request(
            case_id=case_id,
            request=request,
            active_zero_touch=active_zero_touch,
            display_name=x_document_name or "",
            use_demo_provider=False,
        )

    @application.post(
        "/api/clm/zero-touch/cases/{case_id}/documents/{document_id}/replacement",
        response_model=ZeroTouchCaseSummaryResponse,
        tags=["zero-touch"],
    )
    async def replace_zero_touch_document(
        case_id: UUID,
        document_id: UUID,
        request: Request,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
        x_document_name: Annotated[str | None, Header(alias="X-Document-Name")] = None,
        x_document_event_count: Annotated[
            int | None, Header(alias="X-Document-Event-Count")
        ] = None,
    ) -> ZeroTouchCaseSummaryResponse:
        """Accept a current document's explicit replacement, never an implicit overwrite."""

        try:
            documents.validate_upload_metadata(
                case_id=case_id,
                display_name=x_document_name or "",
                content_type=request.headers.get("content-type", ""),
            )
            if x_document_event_count is None or x_document_event_count < 1:
                raise DocumentRequestError(
                    code="DOCUMENT_REPLACEMENT_VERSION_INVALID",
                    message="A valid current document evidence version is required.",
                )
            body = await _read_bounded_body(request, documents.max_upload_bytes)
            record = active_zero_touch.replace_document(
                case_id=case_id,
                document_id=document_id,
                expected_document_event_count=x_document_event_count,
                display_name=x_document_name or "",
                content_type=request.headers.get("content-type", ""),
                content=body,
            )
            return zero_touch_response(record)
        except DocumentRequestError as exc:
            raise _document_http_error(exc) from None
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
        except ZeroTouchInfrastructureError as exc:
            raise _zero_touch_infrastructure_http_error(exc) from None

    @application.post(
        "/api/demo/clm/zero-touch/cases/{case_id}/documents",
        response_model=ZeroTouchCaseSummaryResponse,
        tags=["demo"],
    )
    async def attach_demo_zero_touch_document(
        case_id: UUID,
        request: Request,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
        x_document_name: Annotated[str | None, Header(alias="X-Document-Name")] = None,
    ) -> ZeroTouchCaseSummaryResponse:
        require_demo_controls()
        return await attach_zero_touch_document_request(
            case_id=case_id,
            request=request,
            active_zero_touch=active_zero_touch,
            display_name=x_document_name or "",
            use_demo_provider=True,
        )

    @application.post(
        "/api/clm/zero-touch/cases/{case_id}/start",
        response_model=ZeroTouchCaseSummaryResponse,
        tags=["zero-touch"],
    )
    def start_zero_touch_case(
        case_id: UUID,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
    ) -> ZeroTouchCaseSummaryResponse:
        try:
            return zero_touch_response(active_zero_touch.start(case_id=case_id))
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
        except ZeroTouchInfrastructureError as exc:
            raise _zero_touch_infrastructure_http_error(exc) from None

    @application.post(
        "/api/clm/zero-touch/cases/{case_id}/resume",
        response_model=ZeroTouchCaseSummaryResponse,
        tags=["zero-touch"],
    )
    def resume_zero_touch_case(
        case_id: UUID,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
    ) -> ZeroTouchCaseSummaryResponse:
        """Idempotently resume only when no unresolved exception blocks progress."""

        try:
            return zero_touch_response(active_zero_touch.start(case_id=case_id))
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
        except ZeroTouchInfrastructureError as exc:
            raise _zero_touch_infrastructure_http_error(exc) from None

    @application.post(
        "/api/clm/zero-touch/cases/{case_id}/exceptions/{exception_id}/resolve",
        response_model=ZeroTouchCaseSummaryResponse,
        tags=["zero-touch"],
    )
    def resolve_zero_touch_exception(
        case_id: UUID,
        exception_id: UUID,
        request: ZeroTouchExceptionResolutionRequest,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
    ) -> ZeroTouchCaseSummaryResponse:
        try:
            return zero_touch_response(
                active_zero_touch.resolve_exception(
                    case_id=case_id,
                    exception_id=exception_id,
                    action=request.action,
                    expected_automation_version=request.expected_automation_version,
                    evidence_version=request.evidence_version,
                )
            )
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
        except ZeroTouchInfrastructureError as exc:
            raise _zero_touch_infrastructure_http_error(exc) from None

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
        require_demo_controls()
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
        require_demo_controls()
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
        "DOCUMENT_ALREADY_SUPERSEDED",
        "DOCUMENT_NOT_REPLACEABLE",
        "DOCUMENT_REVIEW_STALE",
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


def _clm_http_error(exc: ClmRequestError) -> HTTPException:
    status_code = status.HTTP_409_CONFLICT
    if exc.code == "CLM_CASE_NOT_FOUND":
        status_code = status.HTTP_404_NOT_FOUND
    detail = ClmFailureDetail(code=exc.code, message=exc.public_message)
    return HTTPException(
        status_code=status_code,
        detail=detail.model_dump(mode="json", exclude_none=True),
    )


def _zero_touch_http_error(exc: ZeroTouchRequestError) -> HTTPException:
    status_code = status.HTTP_409_CONFLICT
    if exc.code == "ZERO_TOUCH_CASE_NOT_FOUND":
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.code in {
        "ZERO_TOUCH_RESOLUTION_NOT_ALLOWED",
        "ZERO_TOUCH_REPLACEMENT_EVIDENCE_REQUIRED",
    }:
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    detail = ZeroTouchFailureDetail(code=exc.code, message=exc.public_message)
    return HTTPException(
        status_code=status_code,
        detail=detail.model_dump(mode="json", exclude_none=True),
    )


def _zero_touch_infrastructure_http_error(
    exc: ZeroTouchInfrastructureError,
) -> HTTPException:
    detail = ZeroTouchFailureDetail(
        code=exc.code,
        message=exc.public_message,
        case_id=exc.case_id,
        automation_id=exc.automation_id,
    )
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=detail.model_dump(mode="json", exclude_none=True),
    )


app = create_app()
