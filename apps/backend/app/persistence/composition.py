"""Select process-local or fail-closed Mongo persistence infrastructure."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from pydantic import SecretStr

from app.config import Settings
from app.demo.zero_touch_control import (
    DemoScenarioRepository,
    InMemoryDemoScenarioRepository,
)
from app.mongo import create_mongo_client
from app.persistence.errors import PersistenceConfigurationError
from app.persistence.mongo_admin_store import (
    MongoAdminStore,
    MongoPolicyRepository,
    MongoProfileRepository,
    MongoTeamRepository,
)
from app.persistence.mongo_case_store import MongoCaseStore
from app.persistence.mongo_registry_cache_store import MongoRegistryCacheStore
from app.persistence.mongo_workflow_store import (
    MongoWorkflowDefinitionRepository,
    MongoWorkflowRunRepository,
    MongoWorkflowStore,
)
from app.persistence.repositories import (
    MongoCaseDeletionRepository,
    MongoCasePortfolioRepository,
    MongoClmOrchestrationRepository,
    MongoDemoScenarioRepository,
    MongoDocumentProcessingRepository,
    MongoOnboardingCaseRepository,
    MongoOnboardingIntelligenceRepository,
    MongoOwnershipAnalysisRepository,
    MongoReconciliationRepository,
    MongoReconciliationUnitOfWork,
    MongoTargetExecutionRepository,
    MongoZeroTouchAutomationRepository,
)
from app.services.admin_repository import (
    InMemoryPolicyRepository,
    InMemoryProfileRepository,
    InMemoryTeamRepository,
    PolicyRepository,
    ProfileRepository,
    TeamRepository,
    bootstrap_administration,
)
from app.services.case_deletion import (
    CaseDeletionRepository,
    InMemoryCaseDeletionRepository,
)
from app.services.case_portfolio_repository import (
    CasePortfolioRepository,
    InMemoryCasePortfolioRepository,
)
from app.services.clm_repository import (
    ClmOrchestrationRepository,
    InMemoryClmOrchestrationRepository,
)
from app.services.document_repository import (
    DocumentProcessingRepository,
    InMemoryDocumentProcessingRepository,
)
from app.services.onboarding_intelligence_repository import (
    InMemoryOnboardingIntelligenceRepository,
    OnboardingIntelligenceRepository,
)
from app.services.ownership_repository import (
    InMemoryOwnershipAnalysisRepository,
    OwnershipAnalysisRepository,
)
from app.services.reconciliation_repository import (
    InMemoryReconciliationRepository,
    ReconciliationRepository,
    ReconciliationUnitOfWork,
)
from app.services.registry_cache_repository import (
    InMemoryRegistrySnapshotRepository,
    RegistrySnapshotRepository,
)
from app.services.repository import (
    InMemoryOnboardingCaseRepository,
    OnboardingCaseRepository,
)
from app.services.target_execution_repository import (
    InMemoryTargetExecutionRepository,
    TargetExecutionRepository,
)
from app.services.workflow_repository import (
    InMemoryWorkflowDefinitionRepository,
    InMemoryWorkflowRunRepository,
    WorkflowDefinitionRepository,
    WorkflowRunRepository,
)
from app.services.zero_touch_repository import (
    InMemoryZeroTouchAutomationRepository,
    ZeroTouchAutomationRepository,
)


@dataclass(frozen=True)
class PersistenceBundle:
    mode: Literal["memory", "mongo"]
    onboarding: OnboardingCaseRepository
    documents: DocumentProcessingRepository
    ownership: OwnershipAnalysisRepository
    intelligence: OnboardingIntelligenceRepository
    reconciliation: ReconciliationRepository
    clm: ClmOrchestrationRepository
    automation: ZeroTouchAutomationRepository
    target_executions: TargetExecutionRepository
    demo_scenarios: DemoScenarioRepository
    teams: TeamRepository
    profiles: ProfileRepository
    policies: PolicyRepository
    portfolio: CasePortfolioRepository
    deletion: CaseDeletionRepository
    registry_snapshots: RegistrySnapshotRepository | None
    reconciliation_unit_of_work: ReconciliationUnitOfWork | None = None
    mongo_store: MongoCaseStore | None = None
    mongo_admin_store: MongoAdminStore | None = None

    @property
    def public_label(self) -> Literal["Process-local", "Mongo-backed durable POC"]:
        return "Mongo-backed durable POC" if self.mode == "mongo" else "Process-local"

    def close(self) -> None:
        if self.mongo_store is not None:
            self.mongo_store.close()


def build_persistence_bundle(settings: Settings) -> PersistenceBundle:
    if settings.clm_persistence_mode == "memory":
        teams = InMemoryTeamRepository()
        profiles = InMemoryProfileRepository()
        policies = InMemoryPolicyRepository()
        bootstrap_administration(teams, profiles, _bootstrap_hashes(settings))
        onboarding = InMemoryOnboardingCaseRepository()
        documents = InMemoryDocumentProcessingRepository()
        ownership = InMemoryOwnershipAnalysisRepository()
        intelligence = InMemoryOnboardingIntelligenceRepository()
        reconciliation = InMemoryReconciliationRepository()
        clm = InMemoryClmOrchestrationRepository()
        automation = InMemoryZeroTouchAutomationRepository()
        target_executions = InMemoryTargetExecutionRepository()
        demo_scenarios = InMemoryDemoScenarioRepository()
        return PersistenceBundle(
            mode="memory",
            onboarding=onboarding,
            documents=documents,
            ownership=ownership,
            intelligence=intelligence,
            reconciliation=reconciliation,
            clm=clm,
            automation=automation,
            target_executions=target_executions,
            demo_scenarios=demo_scenarios,
            teams=teams,
            profiles=profiles,
            policies=policies,
            portfolio=InMemoryCasePortfolioRepository(onboarding, automation),
            deletion=InMemoryCaseDeletionRepository(
                onboarding=onboarding,
                documents=documents,
                ownership=ownership,
                intelligence=intelligence,
                reconciliation=reconciliation,
                clm=clm,
                automation=automation,
                target_executions=target_executions,
                demo_scenarios=demo_scenarios,
            ),
            registry_snapshots=(
                InMemoryRegistrySnapshotRepository()
                if settings.registry_cache_enabled
                else None
            ),
        )

    if settings.mongo_uri is None:
        raise PersistenceConfigurationError
    client = create_mongo_client(settings)
    store = MongoCaseStore(
        client,
        database=settings.mongo_database,
        collection=settings.mongo_case_collection,
    )
    store.initialize()
    admin_store = MongoAdminStore(
        client,
        database=settings.mongo_database,
        teams_collection=settings.mongo_admin_teams_collection,
        profiles_collection=settings.mongo_admin_profiles_collection,
        policies_collection=settings.mongo_admin_policies_collection,
    )
    admin_store.initialize()
    registry_snapshots: RegistrySnapshotRepository | None = None
    if settings.registry_cache_enabled:
        mongo_registry_store = MongoRegistryCacheStore(
            client,
            database=settings.mongo_database,
            collection=settings.mongo_registry_cache_collection,
        )
        mongo_registry_store.initialize()
        registry_snapshots = mongo_registry_store
    mongo_teams = MongoTeamRepository(admin_store)
    mongo_profiles = MongoProfileRepository(admin_store)
    mongo_policies = MongoPolicyRepository(admin_store)
    bootstrap_administration(mongo_teams, mongo_profiles, _bootstrap_hashes(settings))
    return PersistenceBundle(
        mode="mongo",
        onboarding=MongoOnboardingCaseRepository(store),
        documents=MongoDocumentProcessingRepository(store),
        ownership=MongoOwnershipAnalysisRepository(store),
        intelligence=MongoOnboardingIntelligenceRepository(store),
        reconciliation=MongoReconciliationRepository(store),
        clm=MongoClmOrchestrationRepository(store),
        automation=MongoZeroTouchAutomationRepository(store),
        target_executions=MongoTargetExecutionRepository(store),
        demo_scenarios=MongoDemoScenarioRepository(store),
        teams=mongo_teams,
        profiles=mongo_profiles,
        policies=mongo_policies,
        portfolio=MongoCasePortfolioRepository(store),
        deletion=MongoCaseDeletionRepository(store),
        reconciliation_unit_of_work=MongoReconciliationUnitOfWork(store),
        mongo_store=store,
        mongo_admin_store=admin_store,
        registry_snapshots=registry_snapshots,
    )


@dataclass(frozen=True)
class WorkflowPersistence:
    definitions: WorkflowDefinitionRepository
    runs: WorkflowRunRepository
    close: Callable[[], None]


def build_workflow_persistence(settings: Settings) -> WorkflowPersistence:
    """Workflow storage has its own client so the case persistence bundle stays unchanged."""

    if settings.clm_persistence_mode == "memory":
        return WorkflowPersistence(
            definitions=InMemoryWorkflowDefinitionRepository(),
            runs=InMemoryWorkflowRunRepository(),
            close=lambda: None,
        )
    if settings.mongo_uri is None:
        raise PersistenceConfigurationError
    store = MongoWorkflowStore(
        create_mongo_client(settings),
        database=settings.mongo_database,
        definitions_collection=settings.mongo_workflow_definitions_collection,
        runs_collection=settings.mongo_workflow_runs_collection,
    )
    store.initialize()
    return WorkflowPersistence(
        definitions=MongoWorkflowDefinitionRepository(store),
        runs=MongoWorkflowRunRepository(store),
        close=store.close,
    )


def _bootstrap_hashes(settings: Settings) -> dict[str, SecretStr | str | None]:
    return {
        "maya-lim": settings.phase13_maya_lim_password_hash,
        "ethan-tan": settings.phase13_ethan_tan_password_hash,
        "sophia-ng": settings.phase13_sophia_ng_password_hash,
        "ryan-lee": settings.phase13_ryan_lee_password_hash,
        "olivia-koh": settings.phase13_olivia_koh_password_hash,
        "hr-admin": settings.phase14_5_hr_admin_password_hash,
        "support-user": settings.phase13_support_user_password_hash,
    }
