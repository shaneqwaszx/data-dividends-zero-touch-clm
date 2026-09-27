"""FastAPI application and Phase 07 application-facing endpoints."""

import json
import os
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api_admin import build_admin_router
from app.api_auth import (
    BrowserOriginPolicy,
    build_auth_router,
    build_case_reauthorizer,
    install_auth_boundary,
)
from app.api_intelligence import build_intelligence_router
from app.api_models import (
    BrowserTargetOperationEvidence,
    CaseActivityPageResponse,
    CaseDetailTimingResponse,
    CasePortfolioPageResponse,
    CasePriorityResponse,
    ClmCaseSummaryResponse,
    DocumentProcessingResponse,
    OnboardingCaseResponse,
    OwnershipAnalysisResponse,
    ZeroTouchCaseListItemResponse,
    ZeroTouchCaseSummaryResponse,
)
from app.api_policies import build_policy_router
from app.api_provider_sandbox import build_provider_sandbox_router
from app.composition import (
    build_acra_connector as build_acra_connector,
)
from app.composition import (
    build_authentication_service,
    build_clm_orchestration_service,
    build_document_processing_service,
    build_mock_idp_demo_control,
    build_mock_ownership_demo_control,
    build_onboarding_service,
    build_ownership_analysis_service,
    build_reconciliation_service,
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
from app.domain.access import AuthenticatedActor, CasePriority, TeamId
from app.domain.case_management import (
    CaseActivityAction,
    CaseActivityPage,
    CaseTimingDataInvalidError,
    project_case_timing,
)
from app.domain.clm import (
    GoldTierSearchCheckpointStatus,
    GoldTierSearchDisposition,
    GoldTierSubmissionPlan,
)
from app.domain.dashboard import DashboardSnapshot
from app.domain.documents import DocumentFieldKey, ReviewDecision
from app.domain.jurisdiction import JurisdictionCode
from app.domain.models import EventOutcome
from app.domain.ownership import OwnershipCandidate
from app.domain.reconciliation import ReconciliationDecisionAction
from app.domain.target_submission import (
    GoldTierExecutionLedgerEntry,
    GoldTierOperationMarker,
    GoldTierTargetOutcome,
)
from app.domain.zero_touch import (
    AutomationStage,
    AutomationStatus,
    BusinessExceptionType,
    ExceptionResolutionAction,
    ZeroTouchAutomationRecord,
)
from app.persistence.composition import build_persistence_bundle
from app.persistence.errors import (
    PersistenceDataInvalidError,
    PersistenceSchemaUnsupportedError,
    PersistenceUnavailableError,
)
from app.services.activity_export import render_case_activity_csv
from app.services.administration import AdministrationService, AdministrationValidationError
from app.services.authentication import AuthenticationConfigurationError, AuthenticationService
from app.services.authorization import (
    CaseAccessPolicy,
    CaseNotAvailableError,
    CreationTeamSelectionError,
)
from app.services.case_deletion import (
    CaseDeleteConflictError,
    CaseDeleteForbiddenError,
    CaseDeleteUnavailableError,
    CaseDeletionService,
)
from app.services.case_query import (
    CaseActivityQueryInvalidError,
    CasePortfolioQueryInvalidError,
    CaseQueryService,
    CaseTeamFilterForbiddenError,
    CaseTeamFilterInvalidError,
    PriorityFilter,
    PrioritySort,
)
from app.services.clm_errors import ClmInfrastructureError, ClmRequestError
from app.services.clm_orchestration import ClmOrchestrationService
from app.services.dashboard import DashboardService
from app.services.document_errors import (
    DocumentProcessingInfrastructureError,
    DocumentRequestError,
)
from app.services.document_processing import DocumentProcessingService
from app.services.errors import OnboardingInfrastructureError
from app.services.onboarding import OnboardingService
from app.services.onboarding_intelligence import OnboardingIntelligenceProjectionService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_errors import (
    OwnershipInfrastructureError,
    OwnershipRequestError,
)
from app.services.policy_management import PolicyManagementService
from app.services.reconciliation import ReconciliationService
from app.services.zero_touch_errors import (
    ZeroTouchInfrastructureError,
    ZeroTouchRequestError,
)
from app.services.zero_touch_orchestration import ZeroTouchOrchestrator

_E2E_REQUEST_ID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _e2e_upload_milestone(
    request: Request,
    *,
    milestone: str,
    case_id: UUID,
    started_at: float,
    status_code: int | None = None,
) -> None:
    """Emit a payload-free upload milestone only in the owned E2E diagnostic process."""

    if os.environ.get("CLM_E2E_DIAGNOSTICS") != "1":
        return
    request_id = request.headers.get("x-e2e-request-id", "")
    if _E2E_REQUEST_ID.fullmatch(request_id) is None:
        return
    declared_length = request.headers.get("content-length", "")
    content_length = (
        int(declared_length) if declared_length.isascii() and declared_length.isdecimal() else None
    )
    payload: dict[str, object] = {
        "milestone": milestone,
        "request_id": request_id,
        "method": request.method,
        "route_family": "/api[/demo]/clm/zero-touch/cases/{case_id}/intake/documents",
        "case_id": str(case_id),
        "monotonic_ms": round(time.monotonic() * 1000),
        "elapsed_ms": round((time.monotonic() - started_at) * 1000),
        "pid": os.getpid(),
        "backend_port": int(os.environ["CLM_E2E_BACKEND_PORT"]),
    }
    if content_length is not None:
        payload["content_length"] = content_length
    if status_code is not None:
        payload["status"] = status_code
    print(f"E2E_DIAG {json.dumps(payload, sort_keys=True)}", flush=True)


class HealthResponse(BaseModel):
    """Public, non-sensitive service health response."""

    status: Literal["ok"]
    service: str
    environment: str


class StartOnboardingRequest(BaseModel):
    """Small application-facing input; external target DTOs stay behind connectors."""

    model_config = ConfigDict(extra="forbid")

    uen: Annotated[
        str,
        Field(min_length=1, max_length=32, pattern=r"^[A-Z0-9-]+$"),
    ]
    country_of_incorporation: JurisdictionCode | None = None
    team_id: TeamId | None = None

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


class CompleteDocumentIntakeRequest(BaseModel):
    """Bind explicit intake completion to the browser's intended bounded file set."""

    model_config = ConfigDict(extra="forbid")

    expected_document_count: int = Field(ge=1, le=20)


class UpdateCasePriorityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: CasePriority | None


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


class StartZeroTouchCaseRequest(StartOnboardingRequest):
    priority: CasePriority | None = None


class ZeroTouchDemoStartRequest(StartZeroTouchCaseRequest):
    model_config = ConfigDict(extra="forbid")

    scenario: ZeroTouchDemoScenario = ZeroTouchDemoScenario.STRAIGHT_THROUGH


class ZeroTouchExceptionResolutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ExceptionResolutionAction
    expected_automation_version: int = Field(ge=1)
    evidence_version: str = Field(min_length=1, max_length=128)


class ReconciliationResolutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ReconciliationDecisionAction
    expected_automation_version: int = Field(ge=1)
    expected_reconciliation_version: int = Field(ge=1)
    evidence_fingerprint: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")


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
    reconciliation_service: ReconciliationService | None = None,
    clm_orchestration_service: ClmOrchestrationService | None = None,
    zero_touch_orchestrator: ZeroTouchOrchestrator | None = None,
    zero_touch_demo_control: ZeroTouchDemoControl | None = None,
    scenario_catalogue: MockScenarioCatalogue | None = None,
    authentication_service: AuthenticationService | None = None,
    e2e_portfolio_seed_count: int = 0,
    clock: Callable[[], datetime] | None = None,
) -> FastAPI:
    """Build the application with injectable settings for deterministic tests."""

    active_settings = settings or get_settings()
    active_clock = clock or (lambda: datetime.now(UTC))
    browser_origin_policy = BrowserOriginPolicy.from_origins(
        active_settings.phase13_trusted_browser_origins,
        require_https=active_settings.app_env == "production",
    )
    persistence = build_persistence_bundle(active_settings)
    policy_management = PolicyManagementService(persistence.policies)
    administration = AdministrationService(persistence.teams, persistence.profiles)
    application = FastAPI(title=active_settings.app_name, version="0.1.0")
    application.router.add_event_handler("shutdown", persistence.close)
    catalogue = scenario_catalogue or Phase01MockScenarioCatalogue()
    zero_touch_demo = zero_touch_demo_control or build_zero_touch_demo_control(
        persistence.demo_scenarios
    )
    service = onboarding_service or build_onboarding_service(
        catalogue,
        active_settings,
        target_finalization_fault=(
            zero_touch_demo.should_fail_target_finalization
            if active_settings.demo_controls_enabled
            else None
        ),
        repository=persistence.onboarding,
        target_execution_repository=persistence.target_executions,
        policy_snapshot_provider=policy_management.case_snapshot,
        registry_snapshot_repository=persistence.registry_snapshots,
    )
    documents = document_processing_service or build_document_processing_service(
        service, active_settings, repository=persistence.documents
    )
    demo_idp = idp_demo_control or build_mock_idp_demo_control()
    ownership = ownership_analysis_service or build_ownership_analysis_service(
        service, active_settings, repository=persistence.ownership
    )
    demo_ownership = ownership_demo_control or build_mock_ownership_demo_control()
    reconciliation = (
        reconciliation_service
        or getattr(zero_touch_orchestrator, "_reconciliation", None)
        or build_reconciliation_service(
            service,
            documents,
            repository=persistence.reconciliation,
            unit_of_work=persistence.reconciliation_unit_of_work,
        )
    )
    clm = clm_orchestration_service or build_clm_orchestration_service(
        service,
        documents,
        ownership,
        reconciliation,
        repository=persistence.clm,
    )
    intelligence_projection = OnboardingIntelligenceProjectionService(
        cases=service,
        documents=persistence.documents,
        ownership=persistence.ownership,
        repository=persistence.intelligence,
        clock=active_clock,
        candidate_resolver=(
            zero_touch_demo.entity_candidates_for if active_settings.demo_controls_enabled else None
        ),
    )
    zero_touch = zero_touch_orchestrator or build_zero_touch_orchestrator(
        service,
        documents,
        ownership,
        clm,
        reconciliation,
        active_settings,
        repository=persistence.automation,
        establishment_discard=persistence.deletion.discard,
        durable_provider_bindings=persistence.mode == "mongo",
        clock=active_clock,
        intelligence_evaluator=intelligence_projection.evaluate,
    )
    if e2e_portfolio_seed_count:
        if active_settings.app_env != "test" or not 1 <= e2e_portfolio_seed_count <= 250:
            raise ValueError("E2E portfolio seeds require test mode and a count from 1 to 250")
        for index in range(e2e_portfolio_seed_count):
            zero_touch.create_case(
                f"2099{index:05d}A",
                team_id=TeamId.TEAM_A,
            )
    cookie_secure = (
        active_settings.app_env == "production"
        if active_settings.phase13_cookie_secure is None
        else active_settings.phase13_cookie_secure
    )
    if active_settings.app_env == "production" and not cookie_secure:
        raise AuthenticationConfigurationError("PHASE13_COOKIE_SECURE")
    authentication = authentication_service or build_authentication_service(
        active_settings, persistence.profiles, persistence.teams
    )
    administration.bind_session_revoker(authentication.revoke_user_sessions)
    access_policy = CaseAccessPolicy()
    case_query = CaseQueryService(
        cases=service,
        case_repository=service.case_repository,
        automation_repository=zero_touch.automation_repository,
        access_policy=access_policy,
        teams=persistence.teams,
        portfolio_repository=(
            persistence.portfolio
            if onboarding_service is None and zero_touch_orchestrator is None
            else None
        ),
        clock=active_clock,
    )
    dashboard = DashboardService(case_query, administration.directory)
    case_deletion = CaseDeletionService(
        cases=service,
        access_policy=access_policy,
        repository=persistence.deletion,
        release_provider_binding=zero_touch.release_provider_binding,
        release_demo_transients=zero_touch_demo.release_case_transients,
    )
    application.include_router(
        build_auth_router(
            authentication,
            administration.directory,
            cookie_secure=cookie_secure,
        )
    )
    application.include_router(build_admin_router(administration))
    application.include_router(build_provider_sandbox_router(service, active_settings))
    application.include_router(build_policy_router(policy_management))
    application.include_router(
        build_intelligence_router(
            intelligence_projection,
            cases=service,
            access_policy=access_policy,
        )
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
            "SANDBOX" if active_settings.acra_connector_mode == "sandbox" else "MOCK"
        )
        registry_provider_mode: Literal[
            "LOCAL_MOCK", "API_MARKETPLACE_MOCK", "GENERIC_SANDBOX"
        ]
        if active_settings.acra_connector_mode == "mock":
            registry_provider_mode = "LOCAL_MOCK"
        elif active_settings.acra_connector_mode == "api_marketplace_mock":
            registry_provider_mode = "API_MARKETPLACE_MOCK"
        else:
            registry_provider_mode = "GENERIC_SANDBOX"
        target_environment: Literal["MOCK", "SANDBOX"] = (
            "MOCK" if active_settings.goldtier_connector_mode == "mock" else "SANDBOX"
        )
        return SimulationProfile(
            registry_environment=registry_environment,
            registry_provider_mode=registry_provider_mode,
            target_environment=target_environment,
            target_provider_classification=(
                "MOCK" if target_environment == "MOCK" else "SANDBOX_PARTIAL"
            ),
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
            persistence=persistence.public_label,
        )

    @application.exception_handler(RequestValidationError)
    async def safe_request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Project invalid request data through fixed messages without echoing input."""

        if request.url.path == "/api/auth/login":
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content={
                    "detail": {
                        "code": "AUTHENTICATION_REQUEST_INVALID",
                        "message": "The authentication request is invalid.",
                    }
                },
            )

        if request.url.path.startswith("/api/admin/") or request.url.path.startswith(
            "/api/policies"
        ):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content={
                    "detail": {
                        "code": (
                            "POLICY_REQUEST_INVALID"
                            if request.url.path.startswith("/api/policies")
                            else "ADMINISTRATION_REQUEST_INVALID"
                        ),
                        "message": "The administration request is invalid.",
                    }
                },
            )

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

    def get_reconciliation_service() -> ReconciliationService:
        return reconciliation

    def authenticated_actor(request: Request) -> AuthenticatedActor:
        actor = getattr(request.state, "actor", None)
        if not isinstance(actor, AuthenticatedActor):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "AUTHENTICATION_REQUIRED",
                    "message": "A valid authenticated session is required.",
                },
            )
        return actor

    def creation_team(request: StartOnboardingRequest, actor: AuthenticatedActor) -> TeamId:
        try:
            resolved = access_policy.resolve_creation_team(
                actor,
                request.team_id,
                field_was_supplied="team_id" in request.model_fields_set,
            )
            administration.directory.require_active(resolved)
            return resolved
        except (CreationTeamSelectionError, AdministrationValidationError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CASE_TEAM_SELECTION_INVALID",
                    "message": "The case team selection is invalid.",
                },
            ) from None

    def clm_response(record: object) -> ClmCaseSummaryResponse:
        from app.domain.clm import ClmOrchestrationRecord

        orchestration = ClmOrchestrationRecord.model_validate(record)
        case = service.get_case(orchestration.case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="CLM case not found")
        return ClmCaseSummaryResponse.from_domain(
            orchestration, case, administration.directory.get(case.team_id)
        )

    def target_operation_evidence(
        clm_record: object,
        entry: GoldTierExecutionLedgerEntry | None,
        outcome: GoldTierTargetOutcome | None,
    ) -> tuple[BrowserTargetOperationEvidence, ...]:
        """Project only bounded operation outcomes; never target requests or receipts."""

        from app.domain.clm import ClmOrchestrationRecord

        orchestration = ClmOrchestrationRecord.model_validate(clm_record)

        order = (
            GoldTierOperationMarker.SEARCH,
            GoldTierOperationMarker.SHELL,
            GoldTierOperationMarker.POLICY,
            GoldTierOperationMarker.AMEND,
        )
        checkpoint = orchestration.target_search_checkpoint
        attempted = (
            entry.attempted_operations
            if entry is not None
            else outcome.completed_operations
            if outcome is not None
            else (GoldTierOperationMarker.SEARCH,)
            if checkpoint is not None
            else ()
        )
        completed = (
            entry.definitively_completed_operations
            if entry is not None
            else outcome.completed_operations
            if outcome is not None
            else attempted
        )
        last_attempted = attempted[-1] if attempted else None
        result: list[BrowserTargetOperationEvidence] = []
        for operation in order:
            operation_status: Literal[
                "NOT_ATTEMPTED",
                "IN_PROGRESS",
                "NO_MATCH",
                "MATCH_FOUND",
                "SKIPPED",
                "REVIEW_REQUIRED",
                "CREATED",
                "SUCCESS",
                "FAILED",
            ] = "NOT_ATTEMPTED"
            if operation == GoldTierOperationMarker.SEARCH and checkpoint is not None:
                operation_status = (
                    "MATCH_FOUND"
                    if checkpoint.disposition == GoldTierSearchDisposition.EXACT_MATCH
                    else "NO_MATCH"
                    if checkpoint.disposition == GoldTierSearchDisposition.NO_MATCH
                    else "REVIEW_REQUIRED"
                    if checkpoint.status == GoldTierSearchCheckpointStatus.REVIEW_REQUIRED
                    else "FAILED"
                )
            elif (
                operation == GoldTierOperationMarker.SHELL
                and checkpoint is not None
                and checkpoint.disposition == GoldTierSearchDisposition.EXACT_MATCH
            ):
                operation_status = "SKIPPED"
            elif operation in attempted:
                if operation not in completed:
                    operation_status = "IN_PROGRESS"
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
        target_entry = (
            service.get_target_execution_entry(clm_record.submission_snapshot.submission_id)
            if clm_record.submission_snapshot is not None
            else None
        )
        target_outcome = target_entry.target_outcome if target_entry is not None else None
        observed_at = active_clock()
        try:
            timing = project_case_timing(
                created_at=automation.created_at,
                updated_at=automation.updated_at,
                started_at=automation.started_at,
                completed_at=automation.completed_at,
                recorded_total_duration_ms=automation.metrics.total_duration_ms,
                observed_at=observed_at,
            )
        except CaseTimingDataInvalidError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "CASE_TIMING_UNAVAILABLE",
                    "message": "Case timing is temporarily unavailable.",
                },
            ) from None
        return ZeroTouchCaseSummaryResponse.from_domain(
            automation,
            clm_record,
            case,
            timing=CaseDetailTimingResponse(
                **timing.model_dump(),
                observed_at=observed_at,
            ),
            reconciliation=reconciliation.get(case_id=automation.case_id),
            target_operations=target_operation_evidence(clm_record, target_entry, target_outcome),
            team=administration.directory.get(case.team_id),
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
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
    ) -> OnboardingCaseResponse:
        try:
            created_case = active_service.create_case(
                request.uen,
                request.country_of_incorporation,
                team_id=creation_team(request, actor),
            )
            return OnboardingCaseResponse.from_domain(
                created_case, administration.directory.get(created_case.team_id)
            )
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
        return OnboardingCaseResponse.from_domain(case, administration.directory.get(case.team_id))

    @application.post(
        "/api/clm/cases",
        response_model=ClmCaseSummaryResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["clm"],
    )
    def create_clm_case(
        request: StartOnboardingRequest,
        active_clm: Annotated[ClmOrchestrationService, Depends(get_clm_orchestration_service)],
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
    ) -> ClmCaseSummaryResponse:
        try:
            return clm_response(
                active_clm.create_case(
                    request.uen,
                    request.country_of_incorporation,
                    team_id=creation_team(request, actor),
                )
            )
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

    async def intake_zero_touch_document_request(
        *,
        case_id: UUID,
        request: Request,
        active_zero_touch: ZeroTouchOrchestrator,
        display_name: str,
        use_demo_provider: bool,
    ) -> DocumentProcessingResponse:
        """Accept and analyse one file while keeping later automation paused."""

        diagnostic_started_at = time.monotonic()
        _e2e_upload_milestone(
            request,
            milestone="BACKEND_REQUEST_ENTERED",
            case_id=case_id,
            started_at=diagnostic_started_at,
        )
        try:
            documents.validate_upload_metadata(
                case_id=case_id,
                display_name=display_name,
                content_type=request.headers.get("content-type", ""),
            )
            _e2e_upload_milestone(
                request,
                milestone="BACKEND_BODY_READ_STARTED",
                case_id=case_id,
                started_at=diagnostic_started_at,
            )
            body = await _read_bounded_body(request, documents.max_upload_bytes)
            _e2e_upload_milestone(
                request,
                milestone="BACKEND_BODY_READ_COMPLETE",
                case_id=case_id,
                started_at=diagnostic_started_at,
            )
            provider = None
            if use_demo_provider:
                case = service.get_case(case_id)
                if case is None or case.entity is None:
                    raise ZeroTouchRequestError(
                        code="ZERO_TOUCH_CASE_NOT_FOUND",
                        message="The zero-touch onboarding case was not found.",
                    )
                provider = zero_touch_demo.idp_provider_for(case_id, case.entity)
            _e2e_upload_milestone(
                request,
                milestone="BACKEND_DOCUMENT_SERVICE_STARTED",
                case_id=case_id,
                started_at=diagnostic_started_at,
            )
            record = active_zero_touch.intake_document(
                case_id=case_id,
                display_name=display_name,
                content_type=request.headers.get("content-type", ""),
                content=body,
                idp_provider=provider,
            )
            _e2e_upload_milestone(
                request,
                milestone="BACKEND_DOCUMENT_SERVICE_COMPLETE",
                case_id=case_id,
                started_at=diagnostic_started_at,
            )
            response = DocumentProcessingResponse.from_domain(record)
            _e2e_upload_milestone(
                request,
                milestone="BACKEND_RESPONSE_RETURNED",
                case_id=case_id,
                started_at=diagnostic_started_at,
                status_code=status.HTTP_201_CREATED,
            )
            return response
        except DocumentRequestError as exc:
            raise _document_http_error(exc) from None
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
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

    @application.post(
        "/api/clm/zero-touch/cases/{case_id}/intake/documents",
        response_model=DocumentProcessingResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["zero-touch"],
    )
    async def intake_zero_touch_document(
        case_id: UUID,
        request: Request,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
        x_document_name: Annotated[str | None, Header(alias="X-Document-Name")] = None,
    ) -> DocumentProcessingResponse:
        return await intake_zero_touch_document_request(
            case_id=case_id,
            request=request,
            active_zero_touch=active_zero_touch,
            display_name=x_document_name or "",
            use_demo_provider=False,
        )

    @application.post(
        "/api/demo/clm/zero-touch/cases/{case_id}/intake/documents",
        response_model=DocumentProcessingResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["demo"],
    )
    async def intake_demo_zero_touch_document(
        case_id: UUID,
        request: Request,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
        x_document_name: Annotated[str | None, Header(alias="X-Document-Name")] = None,
    ) -> DocumentProcessingResponse:
        require_demo_controls()
        return await intake_zero_touch_document_request(
            case_id=case_id,
            request=request,
            active_zero_touch=active_zero_touch,
            display_name=x_document_name or "",
            use_demo_provider=True,
        )

    async def retry_zero_touch_intake_document_request(
        *,
        case_id: UUID,
        failed_document_id: UUID,
        request: Request,
        active_zero_touch: ZeroTouchOrchestrator,
        display_name: str,
        use_demo_provider: bool,
    ) -> DocumentProcessingResponse:
        try:
            documents.validate_upload_metadata(
                case_id=case_id,
                display_name=display_name,
                content_type=request.headers.get("content-type", ""),
            )
            body = await _read_bounded_body(request, documents.max_upload_bytes)
            provider = None
            if use_demo_provider:
                case = service.get_case(case_id)
                if case is None or case.entity is None:
                    raise ZeroTouchRequestError(
                        code="ZERO_TOUCH_CASE_NOT_FOUND",
                        message="The zero-touch onboarding case was not found.",
                    )
                provider = zero_touch_demo.idp_provider_for(case_id, case.entity)
            record = active_zero_touch.retry_intake_document(
                case_id=case_id,
                failed_document_id=failed_document_id,
                display_name=display_name,
                content_type=request.headers.get("content-type", ""),
                content=body,
                idp_provider=provider,
                reauthorize=build_case_reauthorizer(
                    request, authentication, access_policy, service, case_id
                ),
            )
            return DocumentProcessingResponse.from_domain(record)
        except DocumentRequestError as exc:
            raise _document_http_error(exc) from None
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
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

    @application.post(
        "/api/clm/zero-touch/cases/{case_id}/intake/documents/{failed_document_id}/retry",
        response_model=DocumentProcessingResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["zero-touch"],
    )
    async def retry_zero_touch_intake_document(
        case_id: UUID,
        failed_document_id: UUID,
        request: Request,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
        x_document_name: Annotated[str | None, Header(alias="X-Document-Name")] = None,
    ) -> DocumentProcessingResponse:
        return await retry_zero_touch_intake_document_request(
            case_id=case_id,
            failed_document_id=failed_document_id,
            request=request,
            active_zero_touch=active_zero_touch,
            display_name=x_document_name or "",
            use_demo_provider=False,
        )

    @application.post(
        "/api/demo/clm/zero-touch/cases/{case_id}/intake/documents/{failed_document_id}/retry",
        response_model=DocumentProcessingResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["demo"],
    )
    async def retry_demo_zero_touch_intake_document(
        case_id: UUID,
        failed_document_id: UUID,
        request: Request,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
        x_document_name: Annotated[str | None, Header(alias="X-Document-Name")] = None,
    ) -> DocumentProcessingResponse:
        require_demo_controls()
        return await retry_zero_touch_intake_document_request(
            case_id=case_id,
            failed_document_id=failed_document_id,
            request=request,
            active_zero_touch=active_zero_touch,
            display_name=x_document_name or "",
            use_demo_provider=True,
        )

    def complete_zero_touch_intake_request(
        *,
        case_id: UUID,
        request: Request,
        intake: CompleteDocumentIntakeRequest,
        active_zero_touch: ZeroTouchOrchestrator,
        use_demo_provider: bool,
    ) -> ZeroTouchCaseSummaryResponse:
        try:
            ownership_provider = (
                zero_touch_demo.ownership_provider_for(case_id) if use_demo_provider else None
            )
            return zero_touch_response(
                active_zero_touch.start(
                    case_id=case_id,
                    ownership_provider=ownership_provider,
                    expected_document_count=intake.expected_document_count,
                    reauthorize=build_case_reauthorizer(
                        request, authentication, access_policy, service, case_id
                    ),
                )
            )
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
        except ZeroTouchInfrastructureError as exc:
            raise _zero_touch_infrastructure_http_error(exc) from None

    @application.post(
        "/api/clm/zero-touch/cases/{case_id}/intake/complete",
        response_model=ZeroTouchCaseSummaryResponse,
        tags=["zero-touch"],
    )
    def complete_zero_touch_intake(
        case_id: UUID,
        request: Request,
        intake: CompleteDocumentIntakeRequest,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
    ) -> ZeroTouchCaseSummaryResponse:
        return complete_zero_touch_intake_request(
            case_id=case_id,
            request=request,
            intake=intake,
            active_zero_touch=active_zero_touch,
            use_demo_provider=False,
        )

    @application.post(
        "/api/demo/clm/zero-touch/cases/{case_id}/intake/complete",
        response_model=ZeroTouchCaseSummaryResponse,
        tags=["demo"],
    )
    def complete_demo_zero_touch_intake(
        case_id: UUID,
        request: Request,
        intake: CompleteDocumentIntakeRequest,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
    ) -> ZeroTouchCaseSummaryResponse:
        require_demo_controls()
        return complete_zero_touch_intake_request(
            case_id=case_id,
            request=request,
            intake=intake,
            active_zero_touch=active_zero_touch,
            use_demo_provider=True,
        )

    @application.post(
        "/api/clm/zero-touch/cases",
        response_model=ZeroTouchCaseSummaryResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["zero-touch"],
    )
    def create_zero_touch_case(
        request: StartZeroTouchCaseRequest,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
    ) -> ZeroTouchCaseSummaryResponse:
        try:
            return zero_touch_response(
                active_zero_touch.create_case(
                    request.uen,
                    request.country_of_incorporation,
                    team_id=creation_team(request, actor),
                    priority=request.priority,
                )
            )
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None

    @application.get(
        "/api/clm/zero-touch/cases",
        response_model=list[ZeroTouchCaseListItemResponse],
        tags=["zero-touch"],
    )
    def list_zero_touch_cases(
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
        status_filter: Annotated[AutomationStatus | None, Query(alias="status")] = None,
        priority_filter: Annotated[
            PriorityFilter, Query(alias="priority_filter")
        ] = PriorityFilter.ALL,
        priority_sort: Annotated[
            PrioritySort, Query(alias="priority_sort")
        ] = PrioritySort.HIGHEST_FIRST,
        team_filter: Annotated[str | None, Query(alias="team_filter", max_length=64)] = None,
        attention_type: Annotated[
            BusinessExceptionType | None, Query(alias="attention_type")
        ] = None,
    ) -> list[ZeroTouchCaseListItemResponse]:
        """Project the process-local portfolio without running any workflow stage."""

        del active_zero_touch
        try:
            records = case_query.list_cases(
                actor,
                status=status_filter,
                priority_filter=priority_filter,
                priority_sort=priority_sort,
                team_filter=team_filter,
                attention_type=attention_type,
            )
        except CaseTeamFilterForbiddenError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "TEAM_FILTER_FORBIDDEN",
                    "message": "Team filtering is not permitted.",
                },
            ) from None
        except CaseTeamFilterInvalidError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "TEAM_FILTER_INVALID",
                    "message": "The selected team filter is invalid.",
                },
            ) from None
        return [
            ZeroTouchCaseListItemResponse.from_domain(
                item, administration.directory.get(item.team_id)
            )
            for item in records
        ]

    @application.get(
        "/api/clm/zero-touch/case-portfolio",
        response_model=CasePortfolioPageResponse,
        tags=["zero-touch"],
    )
    def list_case_portfolio(
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
        status_filter: Annotated[AutomationStatus | None, Query(alias="status")] = None,
        priority_filter: Annotated[
            PriorityFilter, Query(alias="priority_filter")
        ] = PriorityFilter.ALL,
        priority_sort: Annotated[
            PrioritySort, Query(alias="priority_sort")
        ] = PrioritySort.HIGHEST_FIRST,
        team_filter: Annotated[str | None, Query(alias="team_filter", max_length=64)] = None,
        attention_type: Annotated[
            BusinessExceptionType | None, Query(alias="attention_type")
        ] = None,
        jurisdiction: Annotated[JurisdictionCode | None, Query(alias="jurisdiction")] = None,
        search: Annotated[str | None, Query(alias="search")] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
    ) -> CasePortfolioPageResponse:
        try:
            page = case_query.list_portfolio(
                actor,
                status=status_filter,
                priority_filter=priority_filter,
                priority_sort=priority_sort,
                team_filter=team_filter,
                attention_type=attention_type,
                jurisdiction=jurisdiction,
                search=search,
                limit=limit,
                offset=offset,
            )
            teams = {item.team_id: item for item in administration.teams.list()}
            return CasePortfolioPageResponse.from_domain(page, teams)
        except CaseTeamFilterForbiddenError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "TEAM_FILTER_FORBIDDEN",
                    "message": "Team filtering is not permitted.",
                },
            ) from None
        except CaseTeamFilterInvalidError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "TEAM_FILTER_INVALID",
                    "message": "The selected team filter is invalid.",
                },
            ) from None
        except CasePortfolioQueryInvalidError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CASE_PORTFOLIO_QUERY_INVALID",
                    "message": "The case portfolio query is invalid.",
                },
            ) from None
        except (
            CaseTimingDataInvalidError,
            PersistenceDataInvalidError,
            PersistenceSchemaUnsupportedError,
            PersistenceUnavailableError,
        ):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "CASE_PORTFOLIO_UNAVAILABLE",
                    "message": "The case portfolio is temporarily unavailable.",
                },
            ) from None

    def _authorized_activity_page(
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
        case_id: Annotated[UUID | None, Query(alias="case_id")] = None,
        team_filter: Annotated[str | None, Query(alias="team_filter", max_length=64)] = None,
        action: Annotated[CaseActivityAction | None, Query(alias="action")] = None,
        stage: Annotated[AutomationStage | None, Query(alias="stage")] = None,
        outcome: Annotated[EventOutcome | None, Query(alias="outcome")] = None,
        from_at: Annotated[datetime | None, Query(alias="from")] = None,
        to_at: Annotated[datetime | None, Query(alias="to")] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
    ) -> CaseActivityPage:
        try:
            return case_query.list_activity(
                actor,
                case_id=case_id,
                team_filter=team_filter,
                action=action,
                stage=stage,
                outcome=outcome,
                from_at=from_at,
                to_at=to_at,
                limit=limit,
                offset=offset,
            )
        except CaseTeamFilterForbiddenError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "TEAM_FILTER_FORBIDDEN",
                    "message": "Team filtering is not permitted.",
                },
            ) from None
        except CaseTeamFilterInvalidError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "TEAM_FILTER_INVALID",
                    "message": "The selected team filter is invalid.",
                },
            ) from None
        except CaseActivityQueryInvalidError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CASE_ACTIVITY_QUERY_INVALID",
                    "message": "The case activity query is invalid.",
                },
            ) from None
        except CaseNotAvailableError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "CASE_NOT_FOUND",
                    "message": "The requested case was not found.",
                },
            ) from None
        except (
            PersistenceDataInvalidError,
            PersistenceSchemaUnsupportedError,
            PersistenceUnavailableError,
            ValueError,
        ):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "CASE_ACTIVITY_UNAVAILABLE",
                    "message": "Case activity is temporarily unavailable.",
                },
            ) from None

    @application.get(
        "/api/clm/zero-touch/activity",
        response_model=CaseActivityPageResponse,
        tags=["zero-touch"],
    )
    def list_zero_touch_activity(
        page: Annotated[CaseActivityPage, Depends(_authorized_activity_page)],
    ) -> CaseActivityPageResponse:
        return CaseActivityPageResponse.from_domain(page)

    @application.get(
        "/api/clm/zero-touch/activity.csv",
        tags=["zero-touch"],
    )
    def export_zero_touch_activity(
        page: Annotated[CaseActivityPage, Depends(_authorized_activity_page)],
    ) -> Response:
        return Response(
            content=render_case_activity_csv(page),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="case-activity.csv"',
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @application.delete(
        "/api/clm/zero-touch/cases/{case_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["zero-touch"],
    )
    def delete_zero_touch_case(
        case_id: UUID,
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
    ) -> Response:
        try:
            case_deletion.delete(actor, case_id)
        except CaseNotAvailableError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Zero-touch case not found",
            ) from None
        except CaseDeleteForbiddenError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "CASE_DELETE_FORBIDDEN",
                    "message": "This role cannot delete cases.",
                },
            ) from None
        except CaseDeleteConflictError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "CASE_DELETE_CONFLICT",
                    "message": "The case changed before deletion completed.",
                },
            ) from None
        except CaseDeleteUnavailableError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "CASE_DELETE_UNAVAILABLE",
                    "message": "Case deletion is temporarily unavailable.",
                },
            ) from None
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.get(
        "/api/clm/zero-touch/dashboard",
        response_model=DashboardSnapshot,
        tags=["zero-touch"],
    )
    def get_zero_touch_dashboard(
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
        team_filter: Annotated[str | None, Query(alias="team_filter", max_length=64)] = None,
    ) -> DashboardSnapshot:
        """Return a provider-free historical view of the caller's authorized cases."""

        try:
            return dashboard.get_dashboard(actor, team_filter=team_filter)
        except CaseTeamFilterForbiddenError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "TEAM_FILTER_FORBIDDEN",
                    "message": "Team filtering is not permitted.",
                },
            ) from None
        except CaseTeamFilterInvalidError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "TEAM_FILTER_INVALID",
                    "message": "The selected team filter is invalid.",
                },
            ) from None

    @application.patch(
        "/api/clm/zero-touch/cases/{case_id}/priority",
        response_model=CasePriorityResponse,
        tags=["zero-touch"],
    )
    def update_case_priority(
        case_id: UUID,
        request: UpdateCasePriorityRequest,
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
    ) -> CasePriorityResponse:
        return CasePriorityResponse.from_domain(
            case_query.update_priority(actor, case_id, request.priority)
        )

    @application.post(
        "/api/demo/clm/zero-touch/cases",
        response_model=ZeroTouchCaseSummaryResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["demo"],
    )
    def create_demo_zero_touch_case(
        request: ZeroTouchDemoStartRequest,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
    ) -> ZeroTouchCaseSummaryResponse:
        require_demo_controls()
        uen = zero_touch_demo.uen_for(request.uen, request.scenario)
        try:
            record = active_zero_touch.create_case(
                uen,
                request.country_of_incorporation,
                team_id=creation_team(request, actor),
                priority=request.priority,
                establishment_action=lambda case_id: zero_touch_demo.register(
                    case_id, request.scenario
                ),
                establishment_rollback=zero_touch_demo.discard_case,
            )
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
                reauthorize=build_case_reauthorizer(
                    request, authentication, access_policy, service, case_id
                ),
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
        request: Request,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
    ) -> ZeroTouchCaseSummaryResponse:
        try:
            return zero_touch_response(
                active_zero_touch.start(
                    case_id=case_id,
                    reauthorize=build_case_reauthorizer(
                        request, authentication, access_policy, service, case_id
                    ),
                )
            )
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
        request: Request,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
    ) -> ZeroTouchCaseSummaryResponse:
        """Idempotently resume only when no unresolved exception blocks progress."""

        try:
            return zero_touch_response(
                active_zero_touch.start(
                    case_id=case_id,
                    reauthorize=build_case_reauthorizer(
                        request, authentication, access_policy, service, case_id
                    ),
                    refresh_document_checkpoint=True,
                )
            )
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
        http_request: Request,
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
                    reauthorize=build_case_reauthorizer(
                        http_request, authentication, access_policy, service, case_id
                    ),
                )
            )
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
        except ZeroTouchInfrastructureError as exc:
            raise _zero_touch_infrastructure_http_error(exc) from None

    @application.post(
        (
            "/api/clm/zero-touch/cases/{case_id}/reconciliation/"
            "discrepancies/{discrepancy_id}/resolve"
        ),
        response_model=ZeroTouchCaseSummaryResponse,
        tags=["zero-touch"],
    )
    def resolve_reconciliation_discrepancy(
        case_id: UUID,
        discrepancy_id: UUID,
        http_request: Request,
        request: ReconciliationResolutionRequest,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
    ) -> ZeroTouchCaseSummaryResponse:
        try:
            return zero_touch_response(
                active_zero_touch.resolve_reconciliation_discrepancy(
                    case_id=case_id,
                    discrepancy_id=discrepancy_id,
                    action=request.action,
                    expected_automation_version=request.expected_automation_version,
                    expected_reconciliation_version=(request.expected_reconciliation_version),
                    evidence_fingerprint=request.evidence_fingerprint,
                    reauthorize=build_case_reauthorizer(
                        http_request, authentication, access_policy, service, case_id
                    ),
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
        request: Request,
        review: DocumentFieldReviewRequest,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
    ) -> DocumentProcessingResponse:
        try:
            record = active_zero_touch.review_document_field(
                case_id=case_id,
                document_id=document_id,
                field_key=review.field_key,
                decision=review.decision,
                corrected_value=review.corrected_value,
                note=review.note,
                reauthorize=build_case_reauthorizer(
                    request, authentication, access_policy, service, case_id
                ),
            )
        except DocumentRequestError as exc:
            raise _document_http_error(exc) from None
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
        except ZeroTouchInfrastructureError as exc:
            raise _zero_touch_infrastructure_http_error(exc) from None
        return DocumentProcessingResponse.from_domain(record)

    install_auth_boundary(
        application,
        authentication,
        access_policy,
        service,
        browser_origin_policy=browser_origin_policy,
    )
    return application


async def _read_bounded_body(request: Request, limit: int) -> bytes:
    """Read a request body without accepting more than the configured per-file limit."""

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
                    message="The uploaded document exceeds the configured size limit.",
                )
            )

    body = bytearray()
    async for chunk in request.stream():
        remaining_capacity = limit - len(body)
        if len(chunk) > remaining_capacity:
            raise _document_http_error(
                DocumentRequestError(
                    code="DOCUMENT_TOO_LARGE",
                    message="The uploaded document exceeds the configured size limit.",
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
    elif exc.code in {"DOCUMENT_TOO_LARGE", "DOCUMENT_TOTAL_SIZE_LIMIT_EXCEEDED"}:
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
