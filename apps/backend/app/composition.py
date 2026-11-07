"""Side-effect-free connector and service composition through Phase 07."""

import ssl
from collections.abc import Callable
from datetime import datetime
from urllib.parse import urlsplit
from uuid import UUID

from app.config import Settings, get_settings
from app.connectors.acra import AcraConnector
from app.connectors.acra_api_marketplace_auth import (
    AcraApiMarketplaceMockRequestAuthorizer,
    AcraApiMarketplaceMockTokenClient,
    AcraMarketplaceTokenTransport,
)
from app.connectors.acra_api_marketplace_mock import (
    ACRA_API_MARKETPLACE_MOCK_BASE_URL,
    ACRA_API_MARKETPLACE_MOCK_DATASET_NAMESPACE,
    ACRA_API_MARKETPLACE_MOCK_RESPONSE_MAX_BYTES,
    AcraApiMarketplaceMockConnection,
    AcraApiMarketplaceMockConnector,
)
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
from app.connectors.goldtier import GoldTierConnector, GoldTierRequestMapper
from app.connectors.goldtier_xpi import (
    GoldTierXpiConfigurationError,
    GoldTierXpiHttpTransport,
    GoldTierXpiSandboxConnection,
    GoldTierXpiSandboxConnector,
    HttpxGoldTierXpiTransport,
)
from app.connectors.hybrid_ownership_overlay import (
    HybridOwnershipOverlayCatalogue,
    hybrid_overlay_scenarios,
)
from app.connectors.local_ocr import TesseractOcrAdapter
from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider
from app.connectors.mock_acra import MOCK_ACRA_DATASET_NAMESPACE, MockAcraConnector
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
from app.domain.models import (
    RegistryFreshnessPolicy,
    RegistryProviderIdentity,
    SourceEnvironment,
    SourceSystem,
)
from app.domain.onboarding_intelligence import OnboardingIntelligenceRecord
from app.domain.policy import CasePolicySnapshot
from app.domain.registry_dataset import local_synthetic_registry_identity
from app.domain.target_identity_evidence import (
    AcceptedIdentitySource,
    TargetIdentityEvidencePolicy,
)
from app.mappers.goldtier import MockGoldTierRequestMapper
from app.mappers.goldtier_xpi import GoldTierXpiRequestMapper
from app.services.acra_diagnostics import (
    AcraDiagnosticConfiguration,
    AcraDiagnosticService,
)
from app.services.admin_repository import ProfileRepository, TeamRepository
from app.services.authentication import AuthenticationService
from app.services.clm_orchestration import ClmOrchestrationService
from app.services.clm_repository import (
    ClmOrchestrationRepository,
    InMemoryClmOrchestrationRepository,
)
from app.services.document_media import ExtractedDocumentContent
from app.services.document_processing import DocumentProcessingService
from app.services.document_repository import (
    DocumentProcessingRepository,
    InMemoryDocumentProcessingRepository,
)
from app.services.onboarding import EntityResolver, OnboardingService
from app.services.onboarding_intelligence import OnboardingIntelligenceService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_discovery import OwnershipDiscoveryCoordinator
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
from app.services.registry_acquisition import RegistryAcquisitionCoordinator
from app.services.registry_cache_repository import (
    InMemoryRegistrySnapshotRepository,
    RegistrySnapshotRepository,
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

# The reviewed sources GoldTier Sandbox accepts in shared staging. This is the only source
# reviewed today, not an authority for every legal-entity type: another source joins through
# its own reviewed provider contract. Government identities have none yet.
STAGING_SANDBOX_IDENTITY_POLICY = TargetIdentityEvidencePolicy(
    accepted_sources=(
        AcceptedIdentitySource(
            source_system=SourceSystem.ACRA,
            environment=SourceEnvironment.MOCK,
            reference_prefix=f"{ACRA_API_MARKETPLACE_MOCK_BASE_URL}/",
        ),
    )
)


def build_onboarding_service(
    scenario_catalogue: MockScenarioCatalogue | None = None,
    settings: Settings | None = None,
    acra_connector: AcraConnector | None = None,
    acra_transport: AcraHttpTransport | None = None,
    acra_authorizer: AcraRequestAuthorizer | None = None,
    acra_decoder: AcraResponseDecoder | None = None,
    acra_marketplace_token_transport: AcraMarketplaceTokenTransport | None = None,
    target_finalization_fault: Callable[[UUID], bool] | None = None,
    repository: OnboardingCaseRepository | None = None,
    target_execution_repository: TargetExecutionRepository | None = None,
    policy_snapshot_provider: Callable[[], CasePolicySnapshot] | None = None,
    registry_snapshot_repository: RegistrySnapshotRepository | None = None,
    goldtier_transport: GoldTierXpiHttpTransport | None = None,
) -> OnboardingService:
    """Compose the explicitly configured GoldTier dialect with no runtime fallback."""

    catalogue = scenario_catalogue or Phase01MockScenarioCatalogue()
    active_settings = settings or get_settings()
    active_acra = acra_connector or build_acra_connector(
        active_settings,
        transport=acra_transport,
        authorizer=acra_authorizer,
        decoder=acra_decoder,
        marketplace_token_transport=acra_marketplace_token_transport,
    )
    cache_identity = (
        RegistryProviderIdentity(
            provider=SourceSystem.ACRA,
            environment=SourceEnvironment.MOCK,
            acquisition_contract_version=(AcraRegistryProviderAdapter.ACQUISITION_CONTRACT_VERSION),
            dataset_namespace=(
                ACRA_API_MARKETPLACE_MOCK_DATASET_NAMESPACE
                if active_settings.acra_connector_mode == "api_marketplace_mock"
                else MOCK_ACRA_DATASET_NAMESPACE
            ),
        )
        if active_settings.registry_cache_enabled
        else None
    )
    registry_provider = AcraRegistryProviderAdapter(
        active_acra,
        cache_identity=cache_identity,
        company_shareholders_only=active_settings.acra_connector_mode == "api_marketplace_mock",
    )
    registry_coordinator = None
    if active_settings.registry_cache_enabled:
        freshness_seconds = active_settings.registry_cache_freshness_seconds or 7_776_000
        if active_settings.clm_persistence_mode == "mongo" and registry_snapshot_repository is None:
            raise ValueError("enabled Mongo registry cache requires its repository")
        registry_coordinator = RegistryAcquisitionCoordinator(
            registry_snapshot_repository or InMemoryRegistrySnapshotRepository(),
            RegistryFreshnessPolicy.model_validate({"duration_seconds": freshness_seconds}),
            local_seed_identity=(
                local_synthetic_registry_identity()
                if active_settings.app_env != "production" else None
            ),
            # Staging's official lane acquires only from the provider: a seeded corporate
            # holder would otherwise merge into official evidence unmarked. The Government
            # register keeps its own labelled route.
            read_seed_for_provider_lanes=not (
                active_settings.app_env == "staging"
                and active_settings.acra_connector_mode == "api_marketplace_mock"
            ),
        )
    goldtier: GoldTierConnector
    goldtier_mapper: GoldTierRequestMapper
    entity_resolver: EntityResolver | None
    if active_settings.goldtier_connector_mode == "sandbox":
        user_id = active_settings.goldtier_sandbox_user_id
        if user_id is None:
            raise GoldTierXpiConfigurationError
        goldtier = GoldTierXpiSandboxConnector(
            connection=GoldTierXpiSandboxConnection(
                base_url=active_settings.goldtier_sandbox_base_url,
                environment=active_settings.goldtier_sandbox_environment,
                user_id=user_id,
                timeout_seconds=active_settings.goldtier_sandbox_timeout_seconds,
                max_response_bytes=active_settings.goldtier_sandbox_max_response_bytes,
                allow_writes=active_settings.goldtier_sandbox_allow_writes,
            ),
            transport=goldtier_transport or HttpxGoldTierXpiTransport(),
        )
        goldtier_mapper = GoldTierXpiRequestMapper()
        entity_resolver = OnboardingIntelligenceService()
    else:
        goldtier = MockGoldTierConnector(
            policy_validation_failure_keys=catalogue.policy_validation_failure_uens(),
            partial_amend_external_keys=catalogue.partial_amend_uens(),
            match_found_external_keys=frozenset({"202400005E"}),
        )
        goldtier_mapper = MockGoldTierRequestMapper()
        entity_resolver = None

    return OnboardingService(
        acra=None,
        registry_router=RegistryProviderRouter(registry_provider),
        registry_acquisition_coordinator=registry_coordinator,
        goldtier=goldtier,
        goldtier_mapper=goldtier_mapper,
        entity_resolver=entity_resolver,
        target_identity_policy=(
            STAGING_SANDBOX_IDENTITY_POLICY
            if active_settings.app_env == "staging"
            and active_settings.goldtier_connector_mode == "sandbox"
            else None
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
    marketplace_token_transport: AcraMarketplaceTokenTransport | None = None,
) -> AcraConnector:
    """Select one explicit ACRA lane without runtime fallback."""

    if settings.acra_connector_mode == "mock":
        return MockAcraConnector()

    if settings.acra_connector_mode == "api_marketplace_mock":
        token_client = AcraApiMarketplaceMockTokenClient(
            client_id=settings.acra_api_marketplace_mock_client_id,
            secret_key=settings.acra_api_marketplace_mock_secret_key,
            timeout_seconds=settings.acra_timeout_seconds,
            transport=marketplace_token_transport,
        )
        return AcraApiMarketplaceMockConnector(
            connection=AcraApiMarketplaceMockConnection(
                timeout_seconds=settings.acra_timeout_seconds,
            ),
            transport=transport
            or HttpxAcraTransport(
                ssl_context=ssl.create_default_context(),
                trust_env=False,
            ),
            authorizer=AcraApiMarketplaceMockRequestAuthorizer(token_client),
        )

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


def build_acra_diagnostic_service(
    connector: AcraConnector,
    settings: Settings,
) -> AcraDiagnosticService:
    """Bind safe diagnostic metadata to the exact composed read-only connector."""

    mode = settings.acra_connector_mode
    safe_host = (
        urlsplit(ACRA_API_MARKETPLACE_MOCK_BASE_URL).hostname
        if mode == "api_marketplace_mock"
        else urlsplit(settings.acra_base_url).hostname
        if mode == "sandbox"
        else None
    )
    client_id_present = settings.acra_api_marketplace_mock_client_id is not None
    secret_key_present = settings.acra_api_marketplace_mock_secret_key is not None
    generic_auth_present = bool(
        settings.acra_auth_header_name and settings.acra_auth_header_value is not None
    )
    configuration = AcraDiagnosticConfiguration(
        provider=(
            "ACRA_API_MARKETPLACE_MOCK"
            if mode == "api_marketplace_mock"
            else "ACRA_GENERIC_SANDBOX"
            if mode == "sandbox"
            else "ACRA_MOCK"
        ),
        mode=mode,
        classification="PARTIAL" if mode == "sandbox" else "MOCK",
        configured=(
            client_id_present and secret_key_present
            if mode == "api_marketplace_mock"
            else generic_auth_present
            if mode == "sandbox"
            else True
        ),
        safe_host=safe_host,
        client_id_present=client_id_present,
        secret_key_present=secret_key_present,
        generic_auth_present=generic_auth_present,
        timeout_seconds=settings.acra_timeout_seconds,
        max_response_bytes=ACRA_API_MARKETPLACE_MOCK_RESPONSE_MAX_BYTES,
    )
    return AcraDiagnosticService(connector=connector, configuration=configuration)


def build_document_processing_service(
    onboarding_service: OnboardingService,
    settings: Settings,
    repository: DocumentProcessingRepository | None = None,
    upload_observer: Callable[[UUID, UUID, ExtractedDocumentContent], None] | None = None,
) -> DocumentProcessingService:
    """Compose the bounded local input-driven PDF text provider by default."""

    return DocumentProcessingService(
        cases=onboarding_service,
        idp=(
            MockIdpProvider()
            if settings.idp_connector_mode == "mock"
            else LocalPdfTextIdpProvider(ocr=TesseractOcrAdapter(
                executable=settings.local_ocr_executable,
                timeout_seconds=settings.local_ocr_timeout_seconds,
            ))
        ),
        repository=repository or InMemoryDocumentProcessingRepository(),
        max_upload_bytes=settings.idp_max_upload_bytes,
        max_files_per_case=settings.idp_max_files_per_case,
        max_total_intake_bytes=settings.idp_max_total_intake_bytes,
        review_confidence_threshold=settings.idp_review_confidence_threshold,
        upload_observer=upload_observer,
    )


def build_mock_idp_demo_control() -> MockIdpDemoControl:
    """Build the dedicated Mock-only UI scenario control."""

    return MockIdpDemoControl()


def build_ownership_analysis_service(
    onboarding_service: OnboardingService,
    settings: Settings,
    repository: OwnershipAnalysisRepository | None = None,
    documents: DocumentProcessingService | None = None,
) -> OwnershipAnalysisService:
    """Compose the credential-free provider-neutral ownership boundary."""

    official_lane = settings.acra_connector_mode == "api_marketplace_mock"
    # Exclusive official-lane compositions: the accepted flattened Garden fixture, or
    # the whitelisted D-077 hybrid direct-holder overlays. Never a provider fallback.
    hybrid = (
        official_lane and settings.acra_marketplace_ownership_overlay == "hybrid_direct_overlay"
    )
    # O5 (2026-11-01): one official-lane switch, re-read at every composition, never per
    # company; disabling it revokes acceptance. Sandbox/Live never qualify (O6).
    poc_acceptance = (
        official_lane
        and settings.acra_marketplace_poc_ownership_acceptance == "accept_eligible_poc"
    )
    # D-112 (owner decision, 2026-11-01): the legacy flattened Garden fixture is an explicit
    # opt-in only; Garden's happy path is the generic reviewed creator declaration.
    legacy_supplement = official_lane and not hybrid and settings.garden_supplement_enabled
    return OwnershipAnalysisService(
        cases=onboarding_service,
        provider=RegistryAcquisitionOwnershipProvider(
            onboarding_service,
            garden_supplement_enabled=legacy_supplement,
        ),
        documents=documents,
        garden_supplement_enabled=legacy_supplement,
        # D-086: the operator-selected OPQ scenario; the five-layer simulation by default.
        hybrid_overlay=(
            HybridOwnershipOverlayCatalogue(
                hybrid_overlay_scenarios(settings.acra_marketplace_opq_scenario)
            )
            if hybrid
            else None
        ),
        poc_acceptance_enabled=poc_acceptance,
        # Shared staging can retain cases from an earlier local Mock lane. The official
        # lane's review allowances need an official root; seeds are refused at acquisition.
        official_registry_source_prefix=(
            f"{ACRA_API_MARKETPLACE_MOCK_BASE_URL}/"
            if official_lane and settings.app_env == "staging"
            else None
        ),
        ubo_review_advisory=(
            official_lane
            # D-124: GoldTier Sandbox is the standing POC lane. Any other target never qualifies.
            and settings.goldtier_connector_mode in {"mock", "sandbox"}
            and settings.acra_marketplace_ubo_review_mode == "advisory"
        ),
        # Corporate owners are acquired separately through the same registry owner;
        # only cases with a frozen discovery policy use it.
        discovery=OwnershipDiscoveryCoordinator(onboarding_service),
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
    establishment_discard: Callable[[UUID], str | None] | None = None,
    durable_provider_bindings: bool = False,
    clock: Callable[[], datetime] | None = None,
    intelligence_evaluator: Callable[[UUID], OnboardingIntelligenceRecord | None] | None = None,
    workflow_send_hold: Callable[[UUID], str | None] | None = None,
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
        establishment_discard=establishment_discard,
        max_transitions_per_run=settings.zero_touch_max_transitions_per_run,
        clock=clock,
        intelligence_evaluator=intelligence_evaluator,
        workflow_send_hold=workflow_send_hold,
    )


def build_zero_touch_demo_control(
    scenario_repository: DemoScenarioRepository | None = None,
) -> ZeroTouchDemoControl:
    return ZeroTouchDemoControl(scenario_repository)
