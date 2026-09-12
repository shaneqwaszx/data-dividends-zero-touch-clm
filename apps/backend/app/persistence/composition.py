"""Select process-local or fail-closed Mongo persistence infrastructure."""

from dataclasses import dataclass
from typing import Literal

from app.config import Settings
from app.demo.zero_touch_control import (
    DemoScenarioRepository,
    InMemoryDemoScenarioRepository,
)
from app.mongo import create_mongo_client
from app.persistence.errors import PersistenceConfigurationError
from app.persistence.mongo_case_store import MongoCaseStore
from app.persistence.repositories import (
    MongoCaseDeletionRepository,
    MongoCasePortfolioRepository,
    MongoClmOrchestrationRepository,
    MongoDemoScenarioRepository,
    MongoDocumentProcessingRepository,
    MongoOnboardingCaseRepository,
    MongoOwnershipAnalysisRepository,
    MongoReconciliationRepository,
    MongoReconciliationUnitOfWork,
    MongoTargetExecutionRepository,
    MongoZeroTouchAutomationRepository,
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
from app.services.ownership_repository import (
    InMemoryOwnershipAnalysisRepository,
    OwnershipAnalysisRepository,
)
from app.services.reconciliation_repository import (
    InMemoryReconciliationRepository,
    ReconciliationRepository,
    ReconciliationUnitOfWork,
)
from app.services.repository import (
    InMemoryOnboardingCaseRepository,
    OnboardingCaseRepository,
)
from app.services.target_execution_repository import (
    InMemoryTargetExecutionRepository,
    TargetExecutionRepository,
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
    reconciliation: ReconciliationRepository
    clm: ClmOrchestrationRepository
    automation: ZeroTouchAutomationRepository
    target_executions: TargetExecutionRepository
    demo_scenarios: DemoScenarioRepository
    portfolio: CasePortfolioRepository
    deletion: CaseDeletionRepository
    reconciliation_unit_of_work: ReconciliationUnitOfWork | None = None
    mongo_store: MongoCaseStore | None = None

    @property
    def public_label(self) -> Literal["Process-local", "Mongo-backed durable POC"]:
        return (
            "Mongo-backed durable POC"
            if self.mode == "mongo"
            else "Process-local"
        )

    def close(self) -> None:
        if self.mongo_store is not None:
            self.mongo_store.close()


def build_persistence_bundle(settings: Settings) -> PersistenceBundle:
    if settings.clm_persistence_mode == "memory":
        onboarding = InMemoryOnboardingCaseRepository()
        automation = InMemoryZeroTouchAutomationRepository()
        documents = InMemoryDocumentProcessingRepository()
        ownership = InMemoryOwnershipAnalysisRepository()
        reconciliation = InMemoryReconciliationRepository()
        clm = InMemoryClmOrchestrationRepository()
        target_executions = InMemoryTargetExecutionRepository()
        demo_scenarios = InMemoryDemoScenarioRepository()
        return PersistenceBundle(
            mode="memory",
            onboarding=onboarding,
            documents=documents,
            ownership=ownership,
            reconciliation=reconciliation,
            clm=clm,
            automation=automation,
            target_executions=target_executions,
            demo_scenarios=demo_scenarios,
            portfolio=InMemoryCasePortfolioRepository(onboarding, automation),
            deletion=InMemoryCaseDeletionRepository(
                onboarding=onboarding,
                documents=documents,
                ownership=ownership,
                reconciliation=reconciliation,
                clm=clm,
                automation=automation,
                target_executions=target_executions,
                demo_scenarios=demo_scenarios,
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
    return PersistenceBundle(
        mode="mongo",
        onboarding=MongoOnboardingCaseRepository(store),
        documents=MongoDocumentProcessingRepository(store),
        ownership=MongoOwnershipAnalysisRepository(store),
        reconciliation=MongoReconciliationRepository(store),
        clm=MongoClmOrchestrationRepository(store),
        automation=MongoZeroTouchAutomationRepository(store),
        target_executions=MongoTargetExecutionRepository(store),
        demo_scenarios=MongoDemoScenarioRepository(store),
        portfolio=MongoCasePortfolioRepository(store),
        deletion=MongoCaseDeletionRepository(store),
        reconciliation_unit_of_work=MongoReconciliationUnitOfWork(store),
        mongo_store=store,
    )
