"""Select process-local or fail-closed Mongo persistence infrastructure."""

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
from app.persistence.repositories import (
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
from app.services.admin_repository import (
    InMemoryPolicyRepository,
    InMemoryProfileRepository,
    InMemoryTeamRepository,
    PolicyRepository,
    ProfileRepository,
    TeamRepository,
    bootstrap_administration,
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
    teams: TeamRepository
    profiles: ProfileRepository
    policies: PolicyRepository
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
        return PersistenceBundle(
            mode="memory",
            onboarding=InMemoryOnboardingCaseRepository(),
            documents=InMemoryDocumentProcessingRepository(),
            ownership=InMemoryOwnershipAnalysisRepository(),
            reconciliation=InMemoryReconciliationRepository(),
            clm=InMemoryClmOrchestrationRepository(),
            automation=InMemoryZeroTouchAutomationRepository(),
            target_executions=InMemoryTargetExecutionRepository(),
            demo_scenarios=InMemoryDemoScenarioRepository(),
            teams=teams,
            profiles=profiles,
            policies=policies,
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
    mongo_teams = MongoTeamRepository(admin_store)
    mongo_profiles = MongoProfileRepository(admin_store)
    mongo_policies = MongoPolicyRepository(admin_store)
    bootstrap_administration(mongo_teams, mongo_profiles, _bootstrap_hashes(settings))
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
        teams=mongo_teams,
        profiles=mongo_profiles,
        policies=mongo_policies,
        reconciliation_unit_of_work=MongoReconciliationUnitOfWork(store),
        mongo_store=store,
        mongo_admin_store=admin_store,
    )


def _bootstrap_hashes(settings: Settings) -> dict[str, SecretStr | str | None]:
    return {
        "maya-lim": settings.phase13_maya_lim_password_hash,
        "ethan-tan": settings.phase13_ethan_tan_password_hash,
        "sophia-ng": settings.phase13_sophia_ng_password_hash,
        "ryan-lee": settings.phase13_ryan_lee_password_hash,
        "olivia-koh": settings.phase13_olivia_koh_password_hash,
        "hr-admin": settings.phase14_5_hr_admin_password_hash,
    }
