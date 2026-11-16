"""FastAPI application and Phase 07 application-facing endpoints."""

import json
import os
import re
import time
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from app.api_acra_diagnostics import build_acra_diagnostic_router
from app.api_admin import build_admin_router
from app.api_auth import (
    BrowserOriginPolicy,
    build_auth_router,
    build_case_reauthorizer,
    install_auth_boundary,
)
from app.api_execution_plan import build_execution_plan_router
from app.api_intelligence import build_intelligence_router
from app.api_models import (
    BrowserTargetOperationEvidence,
    BrowserTargetSubmissionEvidence,
    CaseActivityPageResponse,
    CaseDetailTimingResponse,
    CasePortfolioPageResponse,
    CasePriorityResponse,
    ClmCaseSummaryResponse,
    DocumentDigestResponse,
    DocumentProcessingResponse,
    ExistingCustomerConfirmationRequest,
    OnboardingCaseResponse,
    OwnershipAnalysisResponse,
    ZeroTouchCaseListItemResponse,
    ZeroTouchCaseSummaryResponse,
    project_entity_type_basis,
    project_processing_pipeline,
)
from app.api_policies import build_policy_router
from app.api_provider_sandbox import build_provider_sandbox_router
from app.api_workflows import build_workflow_router
from app.composition import (
    build_acra_connector as build_acra_connector,
)
from app.composition import (
    build_acra_diagnostic_service,
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
from app.connectors.acra import AcraConnector
from app.connectors.errors import ConnectorError, MutationUncertaintyReason, public_connector_error
from app.connectors.goldtier_xpi import GoldTierXpiHttpTransport
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
from app.domain.access import AuthenticatedActor, Capability, CasePriority, TeamId, has_capability
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
from app.domain.documents import DocumentFieldKey, DocumentProcessingRecord, ReviewDecision
from app.domain.jurisdiction import JurisdictionCode
from app.domain.models import (
    GOVERNMENT_STATUTE_PATTERN,
    EventOutcome,
    GovernmentBodyType,
)
from app.domain.ownership import (
    OwnershipAnalysisState,
    OwnershipCandidate,
    OwnershipDocumentBinding,
    Party,
    SafePartyId,
)
from app.domain.reconciliation import ReconciliationDecisionAction
from app.domain.review_decisions import ReviewDecisionBatch
from app.domain.target_submission import (
    GoldTierExecutionClassification,
    GoldTierExecutionLedgerEntry,
    GoldTierExecutionLedgerState,
    GoldTierOperationMarker,
    GoldTierRecoveryOrigin,
    GoldTierSearchResolution,
    GoldTierTargetOutcome,
)
from app.domain.zero_touch import (
    AutomationStage,
    AutomationStatus,
    BusinessExceptionType,
    ExceptionResolutionAction,
    ZeroTouchAutomationRecord,
)
from app.persistence.composition import (
    PersistenceBundle,
    build_goldtier_read_budget,
    build_persistence_bundle,
    build_workflow_persistence,
)
from app.persistence.errors import (
    PersistenceDataInvalidError,
    PersistenceSchemaUnsupportedError,
    PersistenceUnavailableError,
)
from app.services.acra_diagnostics import AcraDiagnosticService
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
from app.services.login_admission import LoginAdmission
from app.services.manual_ownership_evidence import (
    CanonicalUen,
    ManualEconomicInterest,
    ManualOwnershipDeclaration,
    SafeReviewText,
)
from app.services.onboarding import OnboardingService
from app.services.onboarding_execution_plan import ExecutionPlanService
from app.services.onboarding_intelligence import OnboardingIntelligenceProjectionService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_errors import (
    OwnershipInfrastructureError,
    OwnershipRequestError,
)
from app.services.policy_management import PolicyManagementService
from app.services.reconciliation import ReconciliationService
from app.services.workflow_case_data import onboarded_case_values
from app.services.workflow_management import WorkflowManagementService
from app.services.zero_touch_errors import (
    ZeroTouchInfrastructureError,
    ZeroTouchRequestError,
)
from app.services.zero_touch_orchestration import ZeroTouchOrchestrator
from app.services.zero_touch_repository import ZeroTouchRepositoryReadError

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
    legal_name: str | None = Field(default=None, min_length=1, max_length=160)
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


class TargetClassificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_classification_evidence_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    kyc_customer_type: str = Field(min_length=1, max_length=80)
    client_segment: str = Field(min_length=1, max_length=80)
    expected_automation_version: int = Field(ge=1)
    expected_case_event_count: int = Field(ge=1)


class TargetStatusCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_submission_id: UUID


class TargetStatusCheckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    submission_id: UUID
    checked_at: datetime
    verified_party_id: str | None = Field(default=None, max_length=96)
    result: Literal[
        "NO_MATCH", "IDENTITY_UNVERIFIED", "CUSTOMER_IDENTITY_VERIFIED",
        "AMBIGUOUS", "CHECK_FAILED",
    ]
    message: str = (
        "Read-only customer Search cannot prove Policy, KYC or full submission completion. "
        "The retained mutation remains protected from replay."
    )


class CompletedTargetVerificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    submission_id: UUID
    goldtier_id: str = Field(max_length=96)
    checked_at: datetime
    result: Literal["VERIFIED", "REQUIRES_REVIEW", "UNAVAILABLE"]
    legal_name: str | None = Field(default=None, max_length=160)
    registration_number: str | None = Field(default=None, max_length=32)
    country: str | None = Field(default=None, max_length=2)


class TargetDispatchConfirmationRequest(BaseModel):
    """CAS-bound local-POC confirmation; destination and warnings are server-owned."""

    model_config = ConfigDict(extra="forbid")

    expected_clm_version: int = Field(ge=0)
    expected_case_event_count: int = Field(ge=1)
    expected_automation_version: int = Field(default=0, ge=0)


class IdentitySearchRecheckRequest(BaseModel):
    """CAS-bound same-case identity correction and read-only Search recheck."""

    model_config = ConfigDict(extra="forbid")

    legal_name: str = Field(min_length=1, max_length=160)
    registration_number: str = Field(min_length=1, max_length=32)
    country_of_incorporation: Literal["SG"]
    expected_automation_version: int = Field(ge=1)
    expected_clm_version: int = Field(ge=0)
    expected_case_event_count: int = Field(ge=1)


class RegistryIdentityCorrectionRequest(IdentitySearchRecheckRequest):
    choice: Literal["ENTERED", "DOCUMENT", "OTHER"] = "OTHER"
    document_id: UUID | None = None
    expected_document_event_count: int | None = Field(default=None, ge=1)


class TargetRecoveryRequest(BaseModel):
    """Untrusted browser attestation checked against case and fresh provider evidence."""

    model_config = ConfigDict(extra="forbid")

    recovered_party_id: str = Field(min_length=1, max_length=96)
    expected_submission_id: UUID | None = None
    legal_name: str | None = Field(default=None, min_length=1, max_length=160)
    registration_number: str | None = Field(default=None, min_length=1, max_length=32)
    country_of_incorporation: str | None = Field(default=None, min_length=2, max_length=3)
    origin: GoldTierRecoveryOrigin
    operation: Literal["SHELL", "POLICY"] = "SHELL"
    provider_policy: str | None = Field(default=None, min_length=1, max_length=80)
    provider_policy_status: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def require_submission_binding(self) -> "TargetRecoveryRequest":
        # Preserve the existing complete attestation API. The new minimal browser
        # contract must name the exact frozen submission, never infer it from a case.
        if self.expected_submission_id is None and any(value is None for value in (
            self.legal_name, self.registration_number, self.country_of_incorporation,
        )):
            raise ValueError("Recovery requires the expected frozen submission")
        return self


class TargetRecoveryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: UUID
    submission_id: UUID
    recovered_party_id: str
    operation: Literal["SHELL", "POLICY"]
    authority: Literal["PROVIDER_VERIFIED_RECOVERY"]
    origin: GoldTierRecoveryOrigin
    original_outcome_uncertain: Literal[True]
    replayed: Literal[False]
    provider_policy: str | None
    provider_policy_status: str | None
    attempted_operations: tuple[str, ...]
    definitively_completed_operations: tuple[str, ...]
    lifecycle_resolved_operations: tuple[str, ...]


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


class GovernmentStatusConfirmationRequest(BaseModel):
    """D-101: confirm Government status from one exact reviewed document version."""

    model_config = ConfigDict(extra="forbid")

    document_id: UUID
    document_event_count: int = Field(ge=1)
    expected_automation_version: int = Field(ge=1)
    expected_case_event_count: int = Field(ge=1)
    # D-125: the RM keys in the legal basis; checked against the document server-side.
    founding_statute: str = Field(
        min_length=3, max_length=200, pattern=GOVERNMENT_STATUTE_PATTERN
    )
    statute_section: str | None = Field(
        default=None, max_length=40, pattern=GOVERNMENT_STATUTE_PATTERN
    )
    government_body_type: GovernmentBodyType

    @field_validator("founding_statute", "statute_section", mode="before")
    @classmethod
    def strip_statute_text(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class ManualOwnershipEvidenceRequest(BaseModel):
    """Typed reviewed declaration; actor identity is always supplied by the server."""

    model_config = ConfigDict(extra="forbid")

    root_registration_number: CanonicalUen
    evidence_document_id: UUID
    evidence_document_version: int = Field(ge=1)
    source_selection: Literal[
        "USER_SUPPLIED_DECLARATION", "CURRENT_EVIDENCE", "DOCUMENT_OBSERVATIONS"
    ] = "USER_SUPPLIED_DECLARATION"
    observed_document_versions: tuple[OwnershipDocumentBinding, ...] = Field(
        default=(), max_length=32
    )
    selected_observation_ids: tuple[UUID, ...] = Field(default=(), max_length=128)
    as_of_date: date
    rationale: SafeReviewText = None
    root_party_id: SafePartyId
    parties: tuple[Party, ...] = Field(min_length=2, max_length=100)
    relationships: tuple[ManualEconomicInterest, ...] = Field(
        min_length=1, max_length=200
    )
    expected_automation_version: int = Field(ge=1)
    expected_ownership_version: int = Field(ge=1)
    expected_case_event_count: int = Field(ge=1)

    def declaration_for(self, case_id: UUID) -> ManualOwnershipDeclaration:
        return ManualOwnershipDeclaration(
            case_id=case_id,
            root_registration_number=self.root_registration_number,
            evidence_document_id=self.evidence_document_id,
            evidence_document_version=self.evidence_document_version,
            source_selection=self.source_selection,
            observed_document_versions=self.observed_document_versions,
            selected_observation_ids=self.selected_observation_ids,
            as_of_date=self.as_of_date,
            rationale=self.rationale,
            root_party_id=self.root_party_id,
            parties=self.parties,
            relationships=self.relationships,
        )


class PolicySnapshotRebindRequest(BaseModel):
    """Case-bound CAS request; actor identity is supplied by the authenticated session."""

    model_config = ConfigDict(extra="forbid")

    rationale: str = Field(min_length=10, max_length=240)
    expected_automation_version: int = Field(ge=1)
    expected_clm_version: int = Field(ge=1)
    expected_case_event_count: int = Field(ge=1)

    @field_validator("rationale")
    @classmethod
    def safe_rationale(cls, value: str) -> str:
        normalized = value.strip()
        prohibited = (
            "ignore previous",
            "ignore prior",
            "system prompt",
            "developer message",
            "<script",
            "javascript:",
        )
        if (
            not normalized
            or any(ord(character) < 32 for character in normalized)
            or any(marker in normalized.casefold() for marker in prohibited)
        ):
            raise ValueError("policy rebind rationale is invalid")
        return normalized


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


def _onboarded_values(
    persistence: PersistenceBundle, cases: OnboardingService, case_id: UUID
) -> dict[str, str]:
    case = cases.get_case(case_id)
    if case is None:
        return {}
    return onboarded_case_values(
        case,
        documents=persistence.documents.list_for_case(case_id),
        ownership=persistence.ownership.get_for_case(case_id),
        reconciliation=persistence.reconciliation.get_for_case(case_id),
        intelligence=persistence.intelligence.get_for_case(case_id),
    )


def _automation_is_complete(record: ZeroTouchAutomationRecord | None) -> bool:
    return record is not None and record.status == AutomationStatus.COMPLETED


def _automation_is_sent(record: ZeroTouchAutomationRecord | None) -> bool:
    return record is not None and record.current_stage in {
        AutomationStage.MOCK_GOLDTIER,
        AutomationStage.COMPLETE,
    }


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
    acra_diagnostic_service: AcraDiagnosticService | None = None,
    acra_connector: AcraConnector | None = None,
    goldtier_transport: GoldTierXpiHttpTransport | None = None,
    e2e_acra_protocol_fixture: bool = False,
    e2e_portfolio_seed_count: int = 0,
    clock: Callable[[], datetime] | None = None,
) -> FastAPI:
    """Build the application with injectable settings for deterministic tests."""

    active_settings = settings or get_settings()
    if e2e_acra_protocol_fixture and (
        active_settings.app_env != "test"
        or active_settings.clm_persistence_mode != "memory"
        or active_settings.acra_connector_mode != "api_marketplace_mock"
        or acra_connector is None
        or onboarding_service is not None
    ):
        raise ValueError("Offline ACRA protocol fixtures require an injected test/memory connector")
    active_clock = clock or (lambda: datetime.now(UTC))
    secure_browser = active_settings.app_env in {"staging", "production"}
    browser_origin_policy = BrowserOriginPolicy.from_origins(
        active_settings.phase13_trusted_browser_origins,
        require_https=secure_browser,
        require_origin_evidence=active_settings.app_env == "staging",
    )
    cookie_secure = active_settings.phase13_cookie_secure
    if cookie_secure is None:
        cookie_secure = secure_browser
    if secure_browser and not cookie_secure:
        raise AuthenticationConfigurationError("PHASE13_COOKIE_SECURE")
    persistence = build_persistence_bundle(active_settings)
    policy_management = PolicyManagementService(persistence.policies)
    administration = AdministrationService(persistence.teams, persistence.profiles)
    application = FastAPI(title=active_settings.app_name, version="0.1.0")
    application.router.add_event_handler("shutdown", persistence.close)
    catalogue = scenario_catalogue or Phase01MockScenarioCatalogue()
    zero_touch_demo = zero_touch_demo_control or build_zero_touch_demo_control(
        persistence.demo_scenarios
    )
    active_acra_connector: AcraConnector | None = None
    if onboarding_service is None:
        active_acra_connector = acra_connector or build_acra_connector(active_settings)
        # ST-7: the daily Sandbox read budget (None when reads are not counted).
        read_budget = build_goldtier_read_budget(active_settings)
        application.router.add_event_handler("shutdown", read_budget.close)
        service = build_onboarding_service(
            catalogue,
            active_settings,
            acra_connector=active_acra_connector,
            target_finalization_fault=(
                zero_touch_demo.should_fail_target_finalization
                if active_settings.demo_controls_enabled
                else None
            ),
            repository=persistence.onboarding,
            target_execution_repository=persistence.target_executions,
            policy_snapshot_provider=policy_management.case_snapshot,
            registry_snapshot_repository=persistence.registry_snapshots,
            goldtier_transport=goldtier_transport,
            goldtier_read_budget=read_budget.budget,
        )
    else:
        service = onboarding_service
    # C2: the stored workflows always back the send check, so switching the manager off
    # never drops a required stage an earlier activation put on open cases. The flag only
    # turns off the workflow routes, upload suggestions and workflow-data deletion.
    workflow_persistence = build_workflow_persistence(active_settings)
    application.router.add_event_handler("shutdown", workflow_persistence.close)
    workflow_enforcement = WorkflowManagementService(
        definitions=workflow_persistence.definitions,
        runs=workflow_persistence.runs,
        cases=service,
        case_is_sent=lambda case_id: _automation_is_sent(
            persistence.automation.get_for_case(case_id)
        ),
        case_is_onboarded=lambda case_id: _automation_is_complete(
            persistence.automation.get_for_case(case_id)
        ),
        case_data=lambda case_id: _onboarded_values(persistence, service, case_id),
        clock=active_clock,
    )
    workflows: WorkflowManagementService | None = (
        workflow_enforcement if active_settings.workflow_manager_enabled else None
    )
    active_acra_diagnostics = acra_diagnostic_service or (
        build_acra_diagnostic_service(active_acra_connector, active_settings)
        if active_acra_connector is not None
        else None
    )
    documents = document_processing_service or build_document_processing_service(
        service,
        active_settings,
        repository=persistence.documents,
        upload_observer=(
            None
            if workflows is None
            else lambda case_id, document_id, extracted: workflows.suggest_from_document(
                case_id=case_id,
                document_id=document_id,
                content=extracted.content,
                media_type=extracted.media_type,
                extracted_text=extracted.extracted_text,
            )
        ),
    )
    demo_idp = idp_demo_control or build_mock_idp_demo_control()
    ownership = ownership_analysis_service or build_ownership_analysis_service(
        service, active_settings, repository=persistence.ownership, documents=documents
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
        workflow_send_hold=workflow_enforcement.send_hold_code,
    )
    application.router.add_event_handler("startup", zero_touch.release_advisory_holds)
    if e2e_portfolio_seed_count:
        if active_settings.app_env != "test" or not 1 <= e2e_portfolio_seed_count <= 250:
            raise ValueError("E2E portfolio seeds require test mode and a count from 1 to 250")
        for index in range(e2e_portfolio_seed_count):
            zero_touch.create_case(
                f"2099{index:05d}A",
                team_id=TeamId.TEAM_A,
            )
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
    dashboard = DashboardService(
        case_query, administration.directory, zero_touch.automation_repository, clock=active_clock
    )
    case_deletion = CaseDeletionService(
        cases=service,
        access_policy=access_policy,
        repository=persistence.deletion,
        release_provider_binding=zero_touch.release_provider_binding,
        release_demo_transients=zero_touch_demo.release_case_transients,
        delete_workflow_data=None if workflows is None else workflows.delete_case_data,
    )
    login_admission = LoginAdmission()
    application.include_router(
        build_auth_router(
            authentication,
            administration.directory,
            cookie_secure=cookie_secure,
            login_admission=login_admission if active_settings.app_env == "staging" else None,
        )
    )
    application.include_router(build_admin_router(administration, login_admission=login_admission))
    application.include_router(build_provider_sandbox_router(service, active_settings))
    if active_acra_diagnostics is not None:
        application.include_router(build_acra_diagnostic_router(active_acra_diagnostics))
    application.include_router(build_policy_router(policy_management, authentication))
    application.include_router(
        build_workflow_router(
            workflows,
            authentication,
            access_policy,
            service,
            active_settings.idp_max_upload_bytes,
            _read_bounded_body,
        )
    )
    # P1: read-only view of what actually runs; outside the manager switch (D-136 E4).
    application.include_router(
        build_execution_plan_router(
            ExecutionPlanService(
                settings=active_settings,
                search_follows_registry=service.search_follows_registry,
                target_provider_mode=service.target_provider_mode,
                workflows=workflow_enforcement,
            ),
            authentication,
        )
    )
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
            "LOCAL_MOCK", "API_MARKETPLACE_MOCK", "GENERIC_SANDBOX",
            "API_MARKETPLACE_PROTOCOL_TEST",
        ]
        if active_settings.acra_connector_mode == "mock":
            registry_provider_mode = "LOCAL_MOCK"
        elif e2e_acra_protocol_fixture:
            registry_provider_mode = "API_MARKETPLACE_PROTOCOL_TEST"
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
        if request.url.path.endswith("/manual-ownership-evidence"):
            zero_detail = ZeroTouchFailureDetail(
                code="ZERO_TOUCH_MANUAL_OWNERSHIP_INVALID",
                message="The manual ownership evidence request is invalid.",
            )
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content={"detail": zero_detail.model_dump(mode="json", exclude_none=True)},
            )
        if request.url.path.endswith("/government-status-confirmation"):
            zero_detail = ZeroTouchFailureDetail(
                code="ZERO_TOUCH_GOVERNMENT_STATUS_INVALID",
                message="The Government status confirmation request is invalid.",
            )
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content={"detail": zero_detail.model_dump(mode="json", exclude_none=True)},
            )
        if request.url.path.endswith("/policy-rebind"):
            zero_detail = ZeroTouchFailureDetail(
                code="ZERO_TOUCH_POLICY_REBIND_INVALID",
                message="The policy rebind request is invalid.",
            )
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content={"detail": zero_detail.model_dump(mode="json", exclude_none=True)},
            )
        if "/zero-touch/" in request.url.path and request.url.path.endswith(
            "/confirm-existing-customer"
        ):
            zero_detail = ZeroTouchFailureDetail(
                code="ZERO_TOUCH_EXISTING_CUSTOMER_INVALID",
                message="The existing customer confirmation request is invalid.",
            )
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content={"detail": zero_detail.model_dump(mode="json", exclude_none=True)},
            )
        if "/zero-touch/" in request.url.path and request.url.path.endswith(
            "/verify-goldtier"
        ):
            return JSONResponse(
                status_code=422,
                content={"detail": {
                    "code": "GOLDTIER_VERIFICATION_INVALID",
                    "message": "The GoldTier verification request is invalid.",
                }},
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
        active: bool = False,
    ) -> tuple[BrowserTargetOperationEvidence, ...]:
        """Project only bounded operation outcomes; never target requests or receipts."""

        from app.domain.clm import ClmOrchestrationRecord

        orchestration = ClmOrchestrationRecord.model_validate(clm_record)

        order: tuple[GoldTierOperationMarker, ...] = (
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
            entry.lifecycle_resolved_operations
            if entry is not None
            else outcome.completed_operations
            if outcome is not None
            else attempted
        )
        if (
            orchestration.submission_plan.environment.value == "SANDBOX"
            or GoldTierOperationMarker.READBACK in attempted
        ):
            order = (*order, GoldTierOperationMarker.READBACK)
        last_attempted = attempted[-1] if attempted else None
        result: list[BrowserTargetOperationEvidence] = []
        for operation in order:
            operation_status: Literal[
                "NOT_ATTEMPTED",
                "IN_PROGRESS",
                "OUTCOME_UNCERTAIN",
                "NO_MATCH",
                "MATCH_FOUND",
                "SKIPPED",
                "RECOVERED",
                "REVIEW_REQUIRED",
                "CREATED",
                "SUCCESS",
                "FAILED",
            ] = "NOT_ATTEMPTED"
            if operation == GoldTierOperationMarker.SEARCH and checkpoint is not None:
                operation_status = (
                    "MATCH_FOUND"
                    if checkpoint.disposition in {
                        GoldTierSearchDisposition.EXACT_MATCH,
                        GoldTierSearchDisposition.CONFIRMED_EXISTING,
                    }
                    else "NO_MATCH"
                    if checkpoint.disposition == GoldTierSearchDisposition.NO_MATCH
                    else "REVIEW_REQUIRED"
                    if checkpoint.status == GoldTierSearchCheckpointStatus.REVIEW_REQUIRED
                    else "FAILED"
                )
            elif (
                operation
                in {
                    GoldTierOperationMarker.SHELL,
                    GoldTierOperationMarker.POLICY,
                }
                and checkpoint is not None
                and checkpoint.disposition in {
                    GoldTierSearchDisposition.EXACT_MATCH,
                    GoldTierSearchDisposition.CONFIRMED_EXISTING,
                }
            ):
                operation_status = "SKIPPED"
            elif operation in attempted:
                if (
                    entry is not None
                    and entry.provider_recovery_for(operation) is not None
                ):
                    operation_status = "RECOVERED"
                elif (
                    entry is not None
                    and entry.provider_verified_amend_failure is not None
                    and operation == GoldTierOperationMarker.AMEND
                ):
                    operation_status = "FAILED"
                elif operation not in completed:
                    operation_status = "IN_PROGRESS" if active else "OUTCOME_UNCERTAIN"
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
            elif (
                operation == GoldTierOperationMarker.AMEND
                and (
                    entry.amend_status if entry is not None
                    else outcome.amend_status if outcome is not None
                    else None
                ) == "AMEND_NOT_REQUIRED"
            ):
                operation_status = "SKIPPED"
            result.append(
                BrowserTargetOperationEvidence(
                    operation=operation.value,
                    status=operation_status,
                )
            )
        return tuple(result)

    def zero_touch_response(
        record: object, *, actor: AuthenticatedActor
    ) -> ZeroTouchCaseSummaryResponse:
        automation = ZeroTouchAutomationRecord.model_validate(record)
        case = service.get_case(automation.case_id)
        clm_record = clm.get(case_id=automation.case_id)
        if case is None or clm_record is None:
            raise HTTPException(status_code=404, detail="Zero-touch case not found")
        target_entry, target_active = (
            service.get_target_execution_activity_snapshot(clm_record.submission_snapshot.submission_id)
            if clm_record.submission_snapshot is not None
            else (None, False)
        )
        target_outcome = target_entry.target_outcome if target_entry is not None else None
        target_operations = target_operation_evidence(
            clm_record, target_entry, target_outcome, target_active
        )
        submission_id = (
            clm_record.submission_snapshot.submission_id
            if clm_record.submission_snapshot is not None else None
        )
        target_state: Literal[
            "NOT_SUBMITTED", "SENDING", "SUBMISSION_CONFIRMED", "SUBMISSION_FAILED",
            "SUBMISSION_OUTCOME_UNCERTAIN", "FINALIZATION_PENDING",
        ] = "NOT_SUBMITTED"
        target_uncertain = bool(
            target_entry is not None and not target_active
            and target_entry.state == GoldTierExecutionLedgerState.IN_PROGRESS
            and target_entry.attempted_operations != target_entry.lifecycle_resolved_operations
            and target_outcome is None and target_entry.receipt is None
        )
        if target_entry is not None and submission_id is not None:
            if target_active:
                target_state = "SENDING"
            elif target_uncertain:
                target_state = "SUBMISSION_OUTCOME_UNCERTAIN"
            elif target_outcome is not None:
                if target_outcome.classification != GoldTierExecutionClassification.SUCCESS:
                    target_state = "SUBMISSION_FAILED"
                elif (
                    automation.status == AutomationStatus.COMPLETED
                    and target_entry.receipt is not None
                    and (
                        target_entry.receipt.classification
                        == GoldTierExecutionClassification.SUCCESS
                    )
                    and (
                        clm_record.submission_plan.environment.value == "MOCK"
                        or (
                            GoldTierOperationMarker.READBACK in target_outcome.completed_operations
                            and target_outcome.readback_party_id == target_outcome.party_id
                            and target_outcome.readback_status == "VERIFIED"
                            and (
                                target_outcome.policy_status is not None
                                or (
                                    target_entry.search_resolution in {
                                        GoldTierSearchResolution.EXACT_MATCH,
                                        GoldTierSearchResolution.CONFIRMED_EXISTING,
                                    }
                                    and target_outcome.shell_status == "EXISTING_PARTY_REUSED"
                                )
                            )
                        )
                    )
                ):
                    target_state = "SUBMISSION_CONFIRMED"
                else:
                    target_state = "FINALIZATION_PENDING"
            elif automation.status in {
                AutomationStatus.RUNNING, AutomationStatus.RESUMING
            }:
                target_state = "SENDING"
            elif (
                automation.status == AutomationStatus.RECOVERY_PENDING
                and target_entry.attempted_operations
                and target_entry.attempted_operations == target_entry.lifecycle_resolved_operations
            ):
                # Presentation only: existing lock/ledger resume guards still own execution.
                target_state = "FINALIZATION_PENDING"
            else:
                # No unresolved operation exists: an empty intent is not an uncertain mutation.
                target_state = (
                    "FINALIZATION_PENDING" if target_entry.attempted_operations else "NOT_SUBMITTED"
                )
        reconciliation_record = reconciliation.get(case_id=automation.case_id)
        ownership_record = ownership.get(case_id=automation.case_id)
        retained_goldtier_id = (
            str(target_entry.resolved_party_id)
            if target_entry is not None and target_entry.resolved_party_id is not None
            else str(target_outcome.party_id)
            if target_outcome is not None and target_outcome.party_id is not None
            else None
        )
        observed_at = active_clock()
        recovery_operation = (
            service.target_recovery_operation(clm_record.submission_snapshot.target_input)
            if target_uncertain and clm_record.submission_snapshot is not None
            and clm.retained_submission_is_current(case_id=automation.case_id)
            and zero_touch.target_recovery_context_is_supported(automation)
            else None
        )
        uncertainty_reason = next((
            event.code.removeprefix("GT_TARGET_OUTCOME_UNCERTAIN_")
            for event in reversed(case.events)
            if event.code is not None and event.code in {
                f"GT_TARGET_OUTCOME_UNCERTAIN_{reason.value}"
                for reason in MutationUncertaintyReason
            }
        ), "UNKNOWN") if target_uncertain else None
        target_submission = BrowserTargetSubmissionEvidence(
            submission_id=submission_id, state=target_state, goldtier_id=retained_goldtier_id,
            recovery_operation=recovery_operation,
            recovery_available=(
                recovery_operation is not None
                and has_capability(actor.profile.role, Capability.TARGET_RECOVERY)
            ),
            provider_policy=(
                target_entry.submission_input.target_policy.policy.value
                if recovery_operation == "POLICY" and target_entry is not None
                and target_entry.submission_input.target_policy is not None else None
            ),
            uncertainty_reason=uncertainty_reason,
            ledger_state=target_entry.state.value if target_entry is not None else None,
            attempted_operations=tuple(
                item.value for item in target_entry.attempted_operations
            ) if target_entry is not None else (),
            definitively_completed_operations=tuple(
                item.value for item in target_entry.definitively_completed_operations
            ) if target_entry is not None else (),
            lifecycle_resolved_operations=tuple(
                item.value for item in target_entry.lifecycle_resolved_operations
            ) if target_entry is not None else (),
            status_check_available=(
                target_state == "SUBMISSION_OUTCOME_UNCERTAIN"
                and clm_record.submission_plan.environment.value == "SANDBOX"
                and submission_id is not None and target_uncertain
            ),
            verification_available=(
                target_state == "SUBMISSION_CONFIRMED"
                and clm_record.submission_plan.environment.value == "SANDBOX"
                and retained_goldtier_id is not None
            ),
            customer_handling=(
                "EXISTING_REUSED"
                if target_outcome is not None
                and target_outcome.shell_status == "EXISTING_PARTY_REUSED"
                else "NEW_CREATED"
                if target_outcome is not None
                and GoldTierOperationMarker.SHELL in target_outcome.completed_operations
                else None
            ),
        )
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
            reconciliation=reconciliation_record,
            target_operations=target_operations,
            target_submission=target_submission,
            classification_assessment=documents.assess_target_classification(case_id=case.case_id),
            processing_pipeline=project_processing_pipeline(
                automation=automation,
                clm=clm_record,
                case=case,
                reconciliation=reconciliation_record,
                target_operations=target_operations,
                retained_goldtier_id=retained_goldtier_id,
                target_submission=target_submission,
            ),
            team=administration.directory.get(case.team_id),
            ownership=ownership_record,
            entity_type_basis=project_entity_type_basis(
                case,
                ownership_record,
                [
                    item
                    for item in documents.list_documents(case_id=case.case_id)
                    if item.is_current_evidence
                ],
                government_resume_required=zero_touch.government_reconfirmation_needs_resume(
                    case_id=case.case_id
                ),
            ),
            evidence_decision_authorized=access_policy.can_decide_evidence(actor, case),
            document_replacement_authorized=(
                access_policy.can_decide_evidence(actor, case)
                and zero_touch.document_replacement_allowed(case_id=case.case_id)
            ),
            document_refresh_recovery_authorized=(
                access_policy.can_decide_evidence(actor, case)
                and not zero_touch.evidence_edit_is_frozen(case_id=case.case_id)
                if zero_touch.document_refresh_pending(automation) else None
            ),
            advisory_continuation_authorized=(
                access_policy.can_decide_evidence(actor, case)
                if zero_touch.advisory_continuation_pending(automation) else None
            ),
            ownership_edit_authorized=(
                access_policy.can_decide_evidence(actor, case)
                and not zero_touch.evidence_edit_is_frozen(case_id=case.case_id)
                and case.goldtier_result is None
                and ownership_record is not None
                and ownership_record.state in {
                    OwnershipAnalysisState.ANALYZED, OwnershipAnalysisState.REVIEW_REQUIRED
                }
                and not service.has_retained_target_execution(case.case_id)
            ),
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
                legal_name=request.legal_name,
                team_id=creation_team(request, actor),
                    created_by_actor_id=actor.profile.user_id,
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
                    legal_name=request.legal_name,
                    team_id=creation_team(request, actor),
                    created_by_actor_id=actor.profile.user_id,
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
        "/api/clm/cases/{case_id}/target-confirmation",
        response_model=ClmCaseSummaryResponse,
        tags=["clm"],
    )
    def confirm_clm_target_dispatch(
        case_id: UUID,
        confirmation: TargetDispatchConfirmationRequest,
        request: Request,
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
        active_clm: Annotated[ClmOrchestrationService, Depends(get_clm_orchestration_service)],
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
    ) -> ClmCaseSummaryResponse:
        try:
            return clm_response(
                active_clm.confirm_target_dispatch(
                    case_id=case_id,
                    actor_id=actor.profile.user_id,
                    expected_clm_version=confirmation.expected_clm_version,
                    expected_case_event_count=confirmation.expected_case_event_count,
                    reauthorize=_refusing_unsendable_case(
                        build_case_reauthorizer(
                            request, authentication, access_policy, service, case_id
                        ),
                        active_zero_touch,
                        case_id,
                    ),
                )
            )
        except ClmRequestError as exc:
            raise _clm_http_error(exc) from None

    @application.post(
        "/api/clm/cases/{case_id}/submit",
        response_model=ClmCaseSummaryResponse,
        tags=["clm"],
    )
    def submit_clm_case(
        case_id: UUID,
        request: Request,
        active_clm: Annotated[ClmOrchestrationService, Depends(get_clm_orchestration_service)],
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
    ) -> ClmCaseSummaryResponse:
        try:
            return clm_response(
                active_clm.submit(
                    case_id=case_id,
                    reauthorize=_refusing_unsendable_case(
                        build_case_reauthorizer(
                            request, authentication, access_policy, service, case_id
                        ),
                        active_zero_touch,
                        case_id,
                        target_write_started=lambda: active_clm.target_write_started(
                            case_id=case_id
                        ),
                    ),
                )
            )
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
            record = await run_in_threadpool(
                active_zero_touch.intake_document,
                case_id=case_id,
                display_name=display_name,
                content_type=request.headers.get("content-type", ""),
                content=body,
                idp_provider=provider,
                reauthorize=build_case_reauthorizer(
                    request, authentication, access_policy, service, case_id
                ),
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
        except ZeroTouchInfrastructureError as exc:
            raise _zero_touch_infrastructure_http_error(exc) from None
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
            , actor=authenticated_actor(request))
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
        response: ZeroTouchCaseSummaryResponse | None = None

        def project_established_case(record: ZeroTouchAutomationRecord) -> None:
            nonlocal response
            response = zero_touch_response(record, actor=actor)

        try:
            active_zero_touch.create_case(
                request.uen,
                request.country_of_incorporation,
                legal_name=request.legal_name,
                team_id=creation_team(request, actor),
                created_by_actor_id=actor.profile.user_id,
                priority=request.priority,
                establishment_projection=project_established_case,
            )
            assert response is not None
            return response
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
        created_from: Annotated[date | None, Query()] = None,
        created_to: Annotated[date | None, Query()] = None,
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
                created_from=created_from,
                created_to=created_to,
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
        except CasePortfolioQueryInvalidError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CASE_PORTFOLIO_QUERY_INVALID",
                    "message": "The created-date range is invalid.",
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
        progress: Annotated[Literal["in_progress", "onboarded"] | None, Query()] = None,
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
        created_from: Annotated[date | None, Query()] = None,
        created_to: Annotated[date | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
    ) -> CasePortfolioPageResponse:
        try:
            page = case_query.list_portfolio(
                actor,
                status=status_filter,
                progress=progress,
                priority_filter=priority_filter,
                priority_sort=priority_sort,
                team_filter=team_filter,
                attention_type=attention_type,
                jurisdiction=jurisdiction,
                search=search,
                created_from=created_from,
                created_to=created_to,
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
        created_by: Annotated[str | None, Query(alias="created_by", max_length=32)] = None,
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
                created_by=created_by,
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
        scope: Annotated[Literal["team", "mine"], Query(alias="scope")] = "team",
        date_range: Annotated[
            Literal["7d", "30d", "90d", "all"], Query(alias="date_range")
        ] = "all",
    ) -> DashboardSnapshot:
        """Return a provider-free historical view of the caller's authorized cases."""

        try:
            return dashboard.get_dashboard(
                actor, team_filter=team_filter, scope=scope, date_range=date_range
            )
        except (
            CaseTimingDataInvalidError,
            ZeroTouchRepositoryReadError,
            PersistenceDataInvalidError,
            PersistenceSchemaUnsupportedError,
            PersistenceUnavailableError,
        ):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "DASHBOARD_UNAVAILABLE",
                    "message": "Dashboard data is temporarily unavailable.",
                },
            ) from None
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

    @application.put(
        "/api/clm/zero-touch/cases/{case_id}/target-classification",
        response_model=ZeroTouchCaseSummaryResponse,
        tags=["zero-touch"],
    )
    def bind_target_classification(
        case_id: UUID,
        classification: TargetClassificationRequest,
        request: Request,
        active_zero_touch: Annotated[
            ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)
        ],
    ) -> ZeroTouchCaseSummaryResponse:
        try:
            record = active_zero_touch.bind_target_classification(
                case_id=case_id,
                kyc_customer_type=classification.kyc_customer_type,
                client_segment=classification.client_segment,
                expected_classification_evidence_fingerprint=classification.expected_classification_evidence_fingerprint,
                expected_automation_version=classification.expected_automation_version,
                expected_case_event_count=classification.expected_case_event_count,
                actor_id=authenticated_actor(request).profile.user_id,
                reauthorize=build_case_reauthorizer(
                    request, authentication, access_policy, service, case_id,
                    require_creator=True,
                ),
            )
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
        except ZeroTouchInfrastructureError as exc:
            raise _zero_touch_infrastructure_http_error(exc) from None
        return zero_touch_response(record, actor=authenticated_actor(request))

    @application.post(
        "/api/clm/zero-touch/cases/{case_id}/policy-rebind",
        response_model=ZeroTouchCaseSummaryResponse,
        tags=["zero-touch"],
    )
    def rebind_zero_touch_policy_snapshot(
        case_id: UUID,
        rebind: PolicySnapshotRebindRequest,
        request: Request,
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
        active_zero_touch: Annotated[
            ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)
        ],
    ) -> ZeroTouchCaseSummaryResponse:
        try:
            record = active_zero_touch.rebind_case_policy_snapshot(
                case_id=case_id,
                actor_id=actor.profile.user_id,
                rationale=rebind.rationale,
                expected_automation_version=rebind.expected_automation_version,
                expected_clm_version=rebind.expected_clm_version,
                expected_case_event_count=rebind.expected_case_event_count,
                reauthorize=build_case_reauthorizer(
                    request, authentication, access_policy, service, case_id
                ),
            )
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
        return zero_touch_response(record, actor=actor)

    @application.post(
        "/api/clm/zero-touch/cases/{case_id}/target-confirmation",
        response_model=ZeroTouchCaseSummaryResponse,
        tags=["zero-touch"],
    )
    def confirm_zero_touch_target_dispatch(
        case_id: UUID,
        confirmation: TargetDispatchConfirmationRequest,
        request: Request,
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
        active_zero_touch: Annotated[
            ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)
        ],
    ) -> ZeroTouchCaseSummaryResponse:
        try:
            record = active_zero_touch.confirm_target_dispatch(
                case_id=case_id,
                actor_id=actor.profile.user_id,
                expected_automation_version=confirmation.expected_automation_version,
                expected_clm_version=confirmation.expected_clm_version,
                expected_case_event_count=confirmation.expected_case_event_count,
                reauthorize=build_case_reauthorizer(
                    request, authentication, access_policy, service, case_id
                ),
            )
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
        return zero_touch_response(record, actor=actor)

    @application.post(
        "/api/clm/zero-touch/cases/{case_id}/confirm-existing-customer",
        response_model=ZeroTouchCaseSummaryResponse,
        tags=["zero-touch"],
    )
    def confirm_existing_goldtier_customer(
        case_id: UUID, confirmation: ExistingCustomerConfirmationRequest, request: Request,
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
    ) -> ZeroTouchCaseSummaryResponse:
        try:
            record = active_zero_touch.confirm_existing_customer(
                case_id=case_id, actor_id=actor.profile.user_id,
                search_request_id=confirmation.search_request_id,
                expected_automation_version=confirmation.expected_automation_version,
                expected_clm_version=confirmation.expected_clm_version,
                expected_case_event_count=confirmation.expected_case_event_count,
                rationale=confirmation.rationale,
                reauthorize=build_case_reauthorizer(
                    request, authentication, access_policy, service, case_id, require_creator=True,
                ),
            )
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
        return zero_touch_response(record, actor=actor)

    @application.post(
        "/api/clm/zero-touch/cases/{case_id}/identity-search-recheck",
        response_model=ZeroTouchCaseSummaryResponse,
        tags=["zero-touch"],
    )
    def repair_identity_and_recheck_search(
        case_id: UUID,
        correction: IdentitySearchRecheckRequest,
        request: Request,
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
        active_zero_touch: Annotated[
            ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)
        ],
    ) -> ZeroTouchCaseSummaryResponse:
        try:
            record = active_zero_touch.repair_initial_identity_and_recheck(
                case_id=case_id,
                actor_id=actor.profile.user_id,
                legal_name=correction.legal_name,
                registration_number=correction.registration_number,
                country_of_incorporation=correction.country_of_incorporation,
                expected_automation_version=correction.expected_automation_version,
                expected_clm_version=correction.expected_clm_version,
                expected_case_event_count=correction.expected_case_event_count,
                reauthorize=build_case_reauthorizer(
                    request, authentication, access_policy, service, case_id,
                    require_creator=True,
                ),
            )
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
        except ZeroTouchInfrastructureError as exc:
            raise _zero_touch_infrastructure_http_error(exc) from None
        return zero_touch_response(record, actor=actor)

    @application.post(
        "/api/clm/zero-touch/cases/{case_id}/registry-identity",
        response_model=ZeroTouchCaseSummaryResponse,
        tags=["zero-touch"],
    )
    def correct_registry_identity(
        case_id: UUID, correction: RegistryIdentityCorrectionRequest, request: Request,
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
    ) -> ZeroTouchCaseSummaryResponse:
        try:
            record = active_zero_touch.repair_initial_identity_and_recheck(
                case_id=case_id, actor_id=actor.profile.user_id,
                legal_name=correction.legal_name,
                registration_number=correction.registration_number,
                country_of_incorporation=correction.country_of_incorporation,
                expected_automation_version=correction.expected_automation_version,
                expected_clm_version=correction.expected_clm_version,
                expected_case_event_count=correction.expected_case_event_count,
                verify_registry=True, identity_choice=correction.choice,
                document_id=correction.document_id,
                expected_document_event_count=correction.expected_document_event_count,
                reauthorize=build_case_reauthorizer(
                    request, authentication, access_policy, service, case_id,
                    require_creator=True,
                ),
            )
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
        except ZeroTouchInfrastructureError as exc:
            raise _zero_touch_infrastructure_http_error(exc) from None
        return zero_touch_response(record, actor=actor)

    @application.post(
        "/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
        response_model=ZeroTouchCaseSummaryResponse,
        tags=["zero-touch"],
    )
    def submit_manual_ownership_evidence(
        case_id: UUID,
        evidence: ManualOwnershipEvidenceRequest,
        request: Request,
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
        active_zero_touch: Annotated[
            ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)
        ],
    ) -> ZeroTouchCaseSummaryResponse:
        try:
            declaration = evidence.declaration_for(case_id)
        except ValidationError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "ZERO_TOUCH_MANUAL_OWNERSHIP_INVALID",
                    "message": (
                        "The ownership declaration or required evidence metadata is invalid."
                    ),
                },
            ) from None
        try:
            record = active_zero_touch.submit_manual_ownership_evidence(
                case_id=case_id,
                actor_id=actor.profile.user_id,
                declaration=declaration,
                expected_automation_version=evidence.expected_automation_version,
                expected_ownership_version=evidence.expected_ownership_version,
                expected_case_event_count=evidence.expected_case_event_count,
                reauthorize=build_case_reauthorizer(
                    request, authentication, access_policy, service, case_id,
                    require_creator=True,
                ),
            )
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
        except ZeroTouchInfrastructureError as exc:
            raise _zero_touch_infrastructure_http_error(exc) from None
        return zero_touch_response(record, actor=actor)

    @application.post(
        "/api/clm/zero-touch/cases/{case_id}/government-status-confirmation",
        response_model=ZeroTouchCaseSummaryResponse,
        tags=["zero-touch"],
    )
    def confirm_government_status(
        case_id: UUID,
        confirmation: GovernmentStatusConfirmationRequest,
        request: Request,
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
        active_zero_touch: Annotated[
            ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)
        ],
    ) -> ZeroTouchCaseSummaryResponse:
        try:
            record = active_zero_touch.confirm_government_status(
                case_id=case_id,
                actor_id=actor.profile.user_id,
                document_id=confirmation.document_id,
                document_event_count=confirmation.document_event_count,
                expected_automation_version=confirmation.expected_automation_version,
                expected_case_event_count=confirmation.expected_case_event_count,
                founding_statute=confirmation.founding_statute,
                statute_section=confirmation.statute_section,
                government_body_type=confirmation.government_body_type,
                reauthorize=build_case_reauthorizer(
                    request, authentication, access_policy, service, case_id,
                    require_creator=True,
                ),
            )
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
        except ZeroTouchInfrastructureError as exc:
            raise _zero_touch_infrastructure_http_error(exc) from None
        return zero_touch_response(record, actor=actor)

    @application.post(
        "/api/clm/zero-touch/cases/{case_id}/verify-goldtier",
        response_model=CompletedTargetVerificationResponse,
        tags=["zero-touch"],
    )
    def verify_completed_target(
        case_id: UUID,
        check: TargetStatusCheckRequest,
        request: Request,
    ) -> CompletedTargetVerificationResponse:
        with service.case_lock(case_id):
            reauthorize = build_case_reauthorizer(
                request, authentication, access_policy, service, case_id
            )
            reauthorize()
            current_clm = clm.get(case_id=case_id)
            automation = zero_touch.get(case_id=case_id)
            if (
                current_clm is None or current_clm.submission_snapshot is None
                or current_clm.submission_snapshot.submission_id != check.expected_submission_id
                or automation is None or automation.status != AutomationStatus.COMPLETED
            ):
                raise HTTPException(status_code=409, detail={
                    "code": "GOLDTIER_VERIFICATION_UNAVAILABLE",
                    "message": "A current completed Sandbox submission is required.",
                })
            try:
                evidence = service.verify_completed_target(
                    case_id=case_id, submission_id=check.expected_submission_id,
                    reauthorize=reauthorize,
                )
            except ValueError:
                raise HTTPException(status_code=409, detail={
                    "code": "GOLDTIER_VERIFICATION_UNAVAILABLE",
                    "message": "A current completed Sandbox submission is required.",
                }) from None
            return CompletedTargetVerificationResponse(
                submission_id=evidence.submission_id, goldtier_id=evidence.goldtier_id,
                checked_at=evidence.checked_at, result=evidence.result,
                legal_name=evidence.legal_name, registration_number=evidence.registration_number,
                country=evidence.country,
            )

    @application.post(
        "/api/clm/zero-touch/cases/{case_id}/target-status-check",
        response_model=TargetStatusCheckResponse,
        tags=["zero-touch"],
    )
    def check_uncertain_target_status(
        case_id: UUID,
        check: TargetStatusCheckRequest,
        request: Request,
    ) -> TargetStatusCheckResponse:
        with service.case_lock(case_id):
            reauthorize = build_case_reauthorizer(
                request, authentication, access_policy, service, case_id
            )
            reauthorize()
            current_clm = clm.get(case_id=case_id)
            if (
                current_clm is None or current_clm.submission_snapshot is None
                or current_clm.submission_snapshot.submission_id != check.expected_submission_id
            ):
                raise HTTPException(status_code=409, detail={
                    "code": "TARGET_STATUS_CHECK_STALE",
                    "message": "The intended retained submission is no longer current.",
                })
            try:
                evidence = service.check_uncertain_target_status(
                    case_id=case_id, submission_id=check.expected_submission_id,
                    reauthorize=reauthorize,
                )
            except ValueError:
                raise HTTPException(status_code=409, detail={
                    "code": "TARGET_STATUS_CHECK_UNAVAILABLE",
                    "message": (
                        "Read-only status checking requires a current uncertain Sandbox submission."
                    ),
                }) from None
            return TargetStatusCheckResponse(
                submission_id=evidence.submission_id, checked_at=evidence.checked_at,
                result=evidence.result,
                verified_party_id=evidence.verified_party_id,
            )

    @application.post(
        "/api/clm/zero-touch/cases/{case_id}/target-recovery",
        response_model=TargetRecoveryResponse,
        tags=["zero-touch"],
    )
    def recover_uncertain_target_operation(
        case_id: UUID,
        recovery_request: TargetRecoveryRequest,
        request: Request,
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
    ) -> TargetRecoveryResponse:
        try:
            reauthorize = build_case_reauthorizer(
                request,
                authentication,
                access_policy,
                service,
                case_id,
                Capability.TARGET_RECOVERY,
            )
            with service.case_lock(case_id):
                reauthorize()
                record = clm.get(case_id=case_id)
                if record is None or record.submission_snapshot is None:
                    raise HTTPException(status_code=409, detail={
                        "code": "TARGET_RECOVERY_INPUT_UNAVAILABLE",
                        "message": "The durable target submission input is unavailable.",
                    })
                submission = record.submission_snapshot.target_input
                if (
                    recovery_request.expected_submission_id is not None
                    and recovery_request.expected_submission_id != submission.submission_id
                ):
                    raise HTTPException(status_code=409, detail={
                        "code": "TARGET_RECOVERY_STALE",
                        "message": "The intended retained submission is no longer current.",
                    })
                if not clm.retained_submission_is_current(case_id=case_id):
                    raise ValueError("Recovery requires current frozen submission evidence")
                current_case = service.get_case(case_id)
                if current_case is None or not service.has_valid_target_dispatch_confirmation(
                    current_case
                ):
                    raise ValueError("Recovery requires the original valid target confirmation")
                identity = submission.canonical_entity
                # Legacy supplied identity is still checked by the owning service.
                # The browser form sends only the UUID and genuinely new provider evidence.
                name = recovery_request.legal_name or identity.legal_name
                registration = recovery_request.registration_number or identity.registration_number
                country = (
                    recovery_request.country_of_incorporation or identity.country_of_incorporation
                )
                if recovery_request.operation == "POLICY":
                    if (
                        recovery_request.provider_policy is None
                        or recovery_request.provider_policy_status is None
                    ):
                        raise ValueError("Policy recovery evidence is incomplete")
                    entry = zero_touch.record_provider_policy_recovery(
                        case_id=case_id, recovered_party_id=recovery_request.recovered_party_id,
                        legal_name=name, registration_number=registration,
                        country_of_incorporation=country,
                        provider_policy=recovery_request.provider_policy,
                        provider_policy_status=recovery_request.provider_policy_status,
                        actor_id=actor.profile.user_id, origin=recovery_request.origin,
                        reauthorize=reauthorize,
                    )
                else:
                    if (
                        recovery_request.provider_policy is not None
                        or recovery_request.provider_policy_status is not None
                    ):
                        raise ValueError("Shell recovery cannot contain Policy evidence")
                    entry = zero_touch.record_provider_shell_recovery(
                        case_id=case_id, recovered_party_id=recovery_request.recovered_party_id,
                        legal_name=name, registration_number=registration,
                        country_of_incorporation=country, actor_id=actor.profile.user_id,
                        origin=recovery_request.origin, reauthorize=reauthorize,
                    )
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
        except ZeroTouchInfrastructureError as exc:
            raise _zero_touch_infrastructure_http_error(exc) from None
        except ConnectorError as exc:
            public = public_connector_error(exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"code": public.code, "message": public.message},
            ) from None
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "TARGET_RECOVERY_REJECTED",
                    "message": (
                        "The evidence does not match a recoverable retained target operation."
                    ),
                },
            ) from None
        except RuntimeError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "TARGET_RECOVERY_CONFLICT",
                    "message": "Target recovery could not retain durable ledger ownership.",
                },
            ) from None
        operation = GoldTierOperationMarker(recovery_request.operation)
        recovery = entry.provider_recovery_for(operation)
        if recovery is None:
            raise RuntimeError("Recovery endpoint did not retain recovery evidence")
        return TargetRecoveryResponse(
            case_id=case_id,
            submission_id=entry.submission_input.submission_id,
            recovered_party_id=recovery.recovered_party_id,
            operation=recovery_request.operation,
            authority=recovery.authority.value,
            origin=recovery.origin,
            original_outcome_uncertain=True,
            replayed=False,
            provider_policy=recovery.provider_policy,
            provider_policy_status=recovery.provider_policy_status,
            attempted_operations=tuple(item.value for item in entry.attempted_operations),
            definitively_completed_operations=tuple(
                item.value for item in entry.definitively_completed_operations
            ),
            lifecycle_resolved_operations=tuple(
                item.value for item in entry.lifecycle_resolved_operations
            ),
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
        response: ZeroTouchCaseSummaryResponse | None = None

        def project_established_case(record: ZeroTouchAutomationRecord) -> None:
            nonlocal response
            response = zero_touch_response(record, actor=actor)

        try:
            active_zero_touch.create_case(
                uen,
                request.country_of_incorporation,
                legal_name=request.legal_name,
                team_id=creation_team(request, actor),
                created_by_actor_id=actor.profile.user_id,
                priority=request.priority,
                establishment_action=lambda case_id: zero_touch_demo.register(
                    case_id, request.scenario
                ),
                establishment_rollback=zero_touch_demo.discard_case,
                establishment_projection=project_established_case,
            )
            assert response is not None
            return response
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
        actor: Annotated[AuthenticatedActor, Depends(authenticated_actor)],
    ) -> ZeroTouchCaseSummaryResponse:
        record = active_zero_touch.get(case_id=case_id)
        if record is None:
            raise _zero_touch_http_error(
                ZeroTouchRequestError(
                    code="ZERO_TOUCH_CASE_NOT_FOUND",
                    message="The zero-touch onboarding case was not found.",
                )
            )
        return zero_touch_response(record, actor=actor)

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
            return zero_touch_response(record, actor=authenticated_actor(request))
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
        x_automation_version: Annotated[int | None, Header(alias="X-Automation-Version")] = None,
        x_clm_version: Annotated[int | None, Header(alias="X-Clm-Version")] = None,
        x_case_event_count: Annotated[int | None, Header(alias="X-Case-Event-Count")] = None,
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
                expected_automation_version=x_automation_version,
                expected_clm_version=x_clm_version,
                expected_case_event_count=x_case_event_count,
                display_name=x_document_name or "",
                content_type=request.headers.get("content-type", ""),
                content=body,
                reauthorize=build_case_reauthorizer(
                    request, authentication, access_policy, service, case_id,
                    require_creator=True,
                ),
            )
            return zero_touch_response(record, actor=authenticated_actor(request))
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
            , actor=authenticated_actor(request))
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
        x_automation_id: Annotated[UUID | None, Header()] = None,
        x_automation_version: Annotated[int | None, Header(ge=1)] = None,
        x_clm_version: Annotated[int | None, Header(ge=1)] = None,
        x_case_event_count: Annotated[int | None, Header(ge=0)] = None,
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
                    expected_automation_id=x_automation_id,
                    expected_automation_version=x_automation_version,
                    expected_clm_version=x_clm_version,
                    expected_case_event_count=x_case_event_count,
                    reauthorize_document_recovery=build_case_reauthorizer(
                        request, authentication, access_policy, service, case_id,
                        require_creator=True,
                    ),
                )
            , actor=authenticated_actor(request))
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
                    actor_id=authenticated_actor(http_request).profile.user_id,
                    reauthorize=build_case_reauthorizer(
                        http_request, authentication, access_policy, service, case_id,
                    require_creator=True,
                    ),
                )
            , actor=authenticated_actor(http_request))
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
                    actor_id=authenticated_actor(http_request).profile.user_id,
                    reauthorize=build_case_reauthorizer(
                        http_request, authentication, access_policy, service, case_id,
                    require_creator=True,
                    ),
                )
            , actor=authenticated_actor(http_request))
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
        return OwnershipAnalysisResponse.from_domain(
            record,
            poc_basis_accepted=active_ownership.poc_basis_accepted(record),
            simulation_calculated=active_ownership.simulation_calculated(record),
            entity_effective_interests=active_ownership.entity_effective_interests(record),
        )

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
        return OwnershipAnalysisResponse.from_domain(
            record,
            poc_basis_accepted=active_ownership.poc_basis_accepted(record),
            simulation_calculated=active_ownership.simulation_calculated(record),
            entity_effective_interests=active_ownership.entity_effective_interests(record),
        )

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

    def document_response(record: DocumentProcessingRecord) -> DocumentProcessingResponse:
        response = DocumentProcessingResponse.from_domain(record)
        if record.is_current_evidence:
            current_reconciliation = reconciliation.get(case_id=record.case_id)
            if current_reconciliation is not None:
                response = response.model_copy(
                    update={"reconciliation_version": current_reconciliation.version}
                )
            checkpoint = reconciliation.resolved_document_checkpoint(
                case_id=record.case_id,
                document_id=record.document_id,
                event_count=len(record.events),
            )
            if checkpoint is not None:
                return response.model_copy(
                    update={
                        "semantic_completion": "RECONCILIATION_RESOLVED",
                        "reconciliation_version": checkpoint.version,
                    }
                )
        return response

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
        return [document_response(record) for record in records]

    @application.get(
        "/api/onboarding/cases/{case_id}/document-digests",
        response_model=list[DocumentDigestResponse],
        tags=["documents"],
    )
    def list_document_digests(
        case_id: UUID,
        active_documents: Annotated[
            DocumentProcessingService, Depends(get_document_processing_service)
        ],
    ) -> list[DocumentDigestResponse]:
        """D-095: the SHA-256 this backend computed from each document's uploaded bytes, read
        from the same stored records as the document list (same case scope). Used only by the
        AI assistant to recognise approved synthetic fixtures; no content is returned."""

        try:
            records = active_documents.list_documents(case_id=case_id)
        except DocumentRequestError as exc:
            raise _document_http_error(exc) from None
        return [
            DocumentDigestResponse(
                document_id=record.document_id,
                document_version=record.document_version,
                content_sha256=record.content_sha256,
            )
            for record in records
        ]

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
        return document_response(record)

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
                actor_id=authenticated_actor(request).profile.user_id,
                reauthorize=build_case_reauthorizer(
                    request, authentication, access_policy, service, case_id,
                    require_creator=True,
                ),
            )
        except DocumentRequestError as exc:
            raise _document_http_error(exc) from None
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
        except ZeroTouchInfrastructureError as exc:
            raise _zero_touch_infrastructure_http_error(exc) from None
        return document_response(record)

    @application.post(
        "/api/clm/zero-touch/cases/{case_id}/review-decisions",
        response_model=ZeroTouchCaseSummaryResponse,
        tags=["zero-touch"],
    )
    def confirm_review_decisions(
        case_id: UUID,
        http_request: Request,
        batch: ReviewDecisionBatch,
        active_zero_touch: Annotated[ZeroTouchOrchestrator, Depends(get_zero_touch_orchestrator)],
    ) -> ZeroTouchCaseSummaryResponse:
        try:
            record = active_zero_touch.apply_review_decisions(
                case_id=case_id,
                batch=batch,
                actor_id=authenticated_actor(http_request).profile.user_id,
                reauthorize=build_case_reauthorizer(
                    http_request,
                    authentication,
                    access_policy,
                    service,
                    case_id,
                    require_creator=True,
                ),
            )
            return zero_touch_response(record, actor=authenticated_actor(http_request))
        except DocumentRequestError as exc:
            raise _document_http_error(exc) from None
        except ZeroTouchRequestError as exc:
            raise _zero_touch_http_error(exc) from None
        except ZeroTouchInfrastructureError as exc:
            raise _zero_touch_infrastructure_http_error(exc) from None

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


def _refusing_unsendable_case(
    reauthorize: Callable[[], None],
    zero_touch: ZeroTouchOrchestrator,
    case_id: UUID,
    *,
    target_write_started: Callable[[], bool] | None = None,
) -> Callable[[], None]:
    """The direct CLM target routes never pass a hold that blocks sending.

    D-124: a hold that needs an explicit resume. D-123 (C1): a required added workflow
    stage that is not confirmed, or a send check that cannot be read. It runs inside the
    CLM case lock, after the reauthorization, before every target step. Only Submit
    passes ``target_write_started``: a send whose first GoldTier write is already in the
    persisted ledger keeps going, so recovery never replays or strands it.
    """

    def check() -> None:
        reauthorize()
        record = zero_touch.automation_repository.get_for_case(case_id)
        if record is not None and zero_touch.advisory_continuation_pending(record):
            raise ClmRequestError(
                code="CLM_NOT_READY",
                message="Continue onboarding first; no GoldTier target mutation was attempted.",
            )
        hold_code = zero_touch.workflow_send_hold(case_id)
        if hold_code is None:
            return
        if target_write_started is not None and target_write_started():
            return
        raise ClmRequestError(
            code=hold_code,
            message=(
                "Complete and confirm the added workflow stages before sending; no GoldTier "
                "target mutation was attempted."
            ),
        )

    return check


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
        "ZERO_TOUCH_TARGET_CLASSIFICATION_INVALID",
        "ZERO_TOUCH_PARTNERSHIP_AGREEMENT_MISMATCH",
        "ZERO_TOUCH_GOVERNMENT_STATUS_EVIDENCE_REQUIRED",
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
