"""Side-effect-free connector and service composition through Phase 07."""

from collections.abc import Callable
from uuid import UUID

from app.config import Settings, get_settings
from app.connectors.acra import AcraConnector
from app.connectors.acra_sandbox import (
    AcraHttpTransport,
    AcraRequestAuthorizer,
    AcraResponseDecoder,
    AcraSandboxConnection,
    AcraSandboxConnector,
    HttpxAcraTransport,
    ProjectAcraResponseDecoder,
    StaticHeaderAcraRequestAuthorizer,
)
from app.connectors.errors import AcraConfigurationError
from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider
from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.connectors.mock_idp import MockIdpProvider
from app.connectors.ownership import OwnershipProvider
from app.connectors.registry import AcraRegistryProviderAdapter, RegistryProviderRouter
from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
from app.demo.idp_control import MockIdpDemoControl
from app.demo.ownership_control import MockOwnershipDemoControl
from app.demo.scenarios import (
    MockScenarioCatalogue,
    Phase01MockScenarioCatalogue,
)
from app.demo.zero_touch_control import DemoScenarioRepository, ZeroTouchDemoControl
from app.domain.policy import CasePolicySnapshot
from app.services.admin_repository import ProfileRepository, TeamRepository
from app.services.authentication import AuthenticationService
from app.services.clm_orchestration import ClmOrchestrationService
from app.services.clm_repository import (
    ClmOrchestrationRepository,
    InMemoryClmOrchestrationRepository,
)
from app.services.document_processing import DocumentProcessingService
from app.services.document_repository import (
    DocumentProcessingRepository,
    InMemoryDocumentProcessingRepository,
)
from app.services.onboarding import OnboardingService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_repository import (
    InMemoryOwnershipAnalysisRepository,
    OwnershipAnalysisRepository,
)
from app.services.reconciliation import ReconciliationService
from app.services.reconciliation_repository import (
    InMemoryReconciliationRepository,
    ReconciliationRepository,
    ReconciliationUnitOfWork,
)
from app.services.repository import InMemoryOnboardingCaseRepository, OnboardingCaseRepository
from app.services.target_execution_repository import TargetExecutionRepository
from app.services.zero_touch_orchestration import ZeroTouchOrchestrator
from app.services.zero_touch_provider_bindings import (
    DurableOwnershipProviderBindingResolver,
    InMemoryOwnershipProviderBindingResolver,
)
from app.services.zero_touch_repository import (
    InMemoryZeroTouchAutomationRepository,
    ZeroTouchAutomationRepository,
)


def build_onboarding_service(
    scenario_catalogue: MockScenarioCatalogue | None = None,
    settings: Settings | None = None,
    acra_connector: AcraConnector | None = None,
    acra_transport: AcraHttpTransport | None = None,
    acra_authorizer: AcraRequestAuthorizer | None = None,
    acra_decoder: AcraResponseDecoder | None = None,
    target_finalization_fault: Callable[[UUID], bool] | None = None,
    repository: OnboardingCaseRepository | None = None,
    target_execution_repository: TargetExecutionRepository | None = None,
    policy_snapshot_provider: Callable[[], CasePolicySnapshot] | None = None,
) -> OnboardingService:
    """Compose configured ACRA and credential-free Mock GoldTier connectors."""

    catalogue = scenario_catalogue or Phase01MockScenarioCatalogue()
    active_settings = settings or get_settings()
    active_acra = acra_connector or build_acra_connector(
        active_settings,
        transport=acra_transport,
        authorizer=acra_authorizer,
        decoder=acra_decoder,
    )
    return OnboardingService(
        acra=None,
        registry_router=RegistryProviderRouter(AcraRegistryProviderAdapter(active_acra)),
        goldtier=MockGoldTierConnector(
            policy_validation_failure_keys=catalogue.policy_validation_failure_uens(),
            partial_amend_external_keys=catalogue.partial_amend_uens(),
            match_found_external_keys=frozenset({"202400005E"}),
        ),
        repository=repository or InMemoryOnboardingCaseRepository(),
        target_finalization_fault=target_finalization_fault,
        target_execution_repository=target_execution_repository,
        policy_snapshot_provider=policy_snapshot_provider,
    )


def build_authentication_service(
    settings: Settings,
    profiles: ProfileRepository,
    teams: TeamRepository,
) -> AuthenticationService:
    return AuthenticationService(
        profiles,
        teams,
        max_active_sessions=settings.phase14_5_max_active_sessions,
    )


def build_acra_connector(
    settings: Settings,
    *,
    transport: AcraHttpTransport | None = None,
    authorizer: AcraRequestAuthorizer | None = None,
    decoder: AcraResponseDecoder | None = None,
) -> AcraConnector:
    """Select Mock or Sandbox ACRA without changing business orchestration."""

    if settings.acra_connector_mode == "mock":
        return MockAcraConnector()

    connection = AcraSandboxConnection(
        base_url=settings.acra_base_url,
        company_path_template=settings.acra_company_path_template,
        timeout_seconds=settings.acra_timeout_seconds,
    )
    active_authorizer = authorizer
    if active_authorizer is None:
        secret = settings.acra_auth_header_value
        if not settings.acra_auth_header_name or secret is None:
            raise AcraConfigurationError
        active_authorizer = StaticHeaderAcraRequestAuthorizer(
            settings.acra_auth_header_name,
            secret.get_secret_value(),
        )
    return AcraSandboxConnector(
        connection=connection,
        transport=transport or HttpxAcraTransport(),
        authorizer=active_authorizer,
        decoder=decoder or ProjectAcraResponseDecoder(),
    )


def build_document_processing_service(
    onboarding_service: OnboardingService,
    settings: Settings,
    repository: DocumentProcessingRepository | None = None,
) -> DocumentProcessingService:
    """Compose the bounded local input-driven PDF text provider by default."""

    return DocumentProcessingService(
        cases=onboarding_service,
        idp=(
            MockIdpProvider()
            if settings.idp_connector_mode == "mock"
            else LocalPdfTextIdpProvider()
        ),
        repository=repository or InMemoryDocumentProcessingRepository(),
        max_upload_bytes=settings.idp_max_upload_bytes,
        max_files_per_case=settings.idp_max_files_per_case,
        max_total_intake_bytes=settings.idp_max_total_intake_bytes,
        review_confidence_threshold=settings.idp_review_confidence_threshold,
    )


def build_mock_idp_demo_control() -> MockIdpDemoControl:
    """Build the dedicated Mock-only UI scenario control."""

    return MockIdpDemoControl()


def build_ownership_analysis_service(
    onboarding_service: OnboardingService,
    settings: Settings,
    repository: OwnershipAnalysisRepository | None = None,
) -> OwnershipAnalysisService:
    """Compose the credential-free provider-neutral ownership boundary."""

    return OwnershipAnalysisService(
        cases=onboarding_service,
        provider=RegistryAcquisitionOwnershipProvider(onboarding_service),
        repository=repository or InMemoryOwnershipAnalysisRepository(),
        threshold_percent=settings.ubo_ownership_threshold_percent,
        max_parties=settings.ownership_max_parties,
        max_relationships=settings.ownership_max_relationships,
        max_depth=settings.ownership_max_depth,
        max_paths_per_candidate=settings.ownership_max_paths_per_candidate,
        max_total_paths=settings.ownership_max_total_paths,
    )


def build_mock_ownership_demo_control() -> MockOwnershipDemoControl:
    """Build the dedicated Mock-only ownership scenario control."""

    return MockOwnershipDemoControl()


def build_reconciliation_service(
    onboarding_service: OnboardingService,
    document_service: DocumentProcessingService,
    repository: ReconciliationRepository | None = None,
    unit_of_work: ReconciliationUnitOfWork | None = None,
) -> ReconciliationService:
    """Compose the process-local source-neutral Phase 11 reconciliation owner."""

    return ReconciliationService(
        cases=onboarding_service,
        documents=document_service,
        repository=repository or InMemoryReconciliationRepository(),
        unit_of_work=unit_of_work,
    )


def build_clm_orchestration_service(
    onboarding_service: OnboardingService,
    document_service: DocumentProcessingService,
    ownership_service: OwnershipAnalysisService,
    reconciliation_service: ReconciliationService | None = None,
    repository: ClmOrchestrationRepository | None = None,
) -> ClmOrchestrationService:
    """Compose staged readiness and serialized Mock GoldTier submission."""

    return ClmOrchestrationService(
        cases=onboarding_service,
        documents=document_service,
        ownership=ownership_service,
        reconciliation=reconciliation_service,
        repository=repository or InMemoryClmOrchestrationRepository(),
    )


def build_zero_touch_orchestrator(
    onboarding_service: OnboardingService,
    document_service: DocumentProcessingService,
    ownership_service: OwnershipAnalysisService,
    clm_service: ClmOrchestrationService,
    reconciliation_service: ReconciliationService,
    settings: Settings,
    repository: ZeroTouchAutomationRepository | None = None,
    durable_provider_bindings: bool = False,
) -> ZeroTouchOrchestrator:
    """Compose the provider-neutral Phase 06 automation owner."""

    def provider_factory() -> OwnershipProvider:
        return ownership_service.configured_provider

    provider_bindings = (
        DurableOwnershipProviderBindingResolver(provider_factory)
        if durable_provider_bindings
        else InMemoryOwnershipProviderBindingResolver(provider_factory)
    )
    return ZeroTouchOrchestrator(
        cases=onboarding_service,
        documents=document_service,
        ownership=ownership_service,
        clm=clm_service,
        reconciliation=reconciliation_service,
        repository=repository or InMemoryZeroTouchAutomationRepository(),
        ownership_provider_bindings=provider_bindings,
        max_transitions_per_run=settings.zero_touch_max_transitions_per_run,
    )


def build_zero_touch_demo_control(
    scenario_repository: DemoScenarioRepository | None = None,
) -> ZeroTouchDemoControl:
    return ZeroTouchDemoControl(scenario_repository)
