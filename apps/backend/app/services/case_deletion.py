"""Authorized hard deletion across one complete CLM case aggregate."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from app.demo.zero_touch_control import DemoScenarioRepository
from app.domain.access import AuthenticatedActor, Role
from app.persistence.errors import PersistenceConflictError, PersistenceUnavailableError
from app.services.authorization import CaseAccessPolicy, CaseNotAvailableError
from app.services.clm_repository import ClmOrchestrationRepository
from app.services.document_repository import DocumentProcessingRepository
from app.services.onboarding import OnboardingService
from app.services.onboarding_intelligence_repository import OnboardingIntelligenceRepository
from app.services.ownership_repository import OwnershipAnalysisRepository
from app.services.reconciliation_repository import ReconciliationRepository
from app.services.repository import OnboardingCaseRepository
from app.services.target_execution_repository import TargetExecutionRepository
from app.services.zero_touch_repository import ZeroTouchAutomationRepository


class CaseDeleteForbiddenError(Exception):
    """The caller may read this case but their role cannot delete it."""


class CaseDeleteConflictError(Exception):
    """The case changed while its durable delete was being claimed."""


class CaseDeleteUnavailableError(Exception):
    """The persistence boundary failed without exposing infrastructure detail."""


class CaseDeletionRepository(Protocol):
    def delete(self, case_id: UUID) -> str | None: ...

    def discard(self, case_id: UUID) -> str | None: ...


class InMemoryCaseDeletionRepository:
    """Remove every process-local record owned by a case."""

    def __init__(
        self,
        *,
        onboarding: OnboardingCaseRepository,
        documents: DocumentProcessingRepository,
        ownership: OwnershipAnalysisRepository,
        intelligence: OnboardingIntelligenceRepository,
        reconciliation: ReconciliationRepository,
        clm: ClmOrchestrationRepository,
        automation: ZeroTouchAutomationRepository,
        target_executions: TargetExecutionRepository,
        demo_scenarios: DemoScenarioRepository,
    ) -> None:
        self._onboarding = onboarding
        self._documents = documents
        self._ownership = ownership
        self._intelligence = intelligence
        self._reconciliation = reconciliation
        self._clm = clm
        self._automation = automation
        self._target_executions = target_executions
        self._demo_scenarios = demo_scenarios

    def delete(self, case_id: UUID) -> str | None:
        return self.discard(case_id)

    def discard(self, case_id: UUID) -> str | None:
        automation = self._automation.get_for_case(case_id)
        binding_id = automation.ownership_provider_binding_id if automation is not None else None
        self._documents.delete_for_case(case_id)
        self._ownership.delete_for_case(case_id)
        self._intelligence.delete_for_case(case_id)
        self._reconciliation.delete_for_case(case_id)
        self._clm.delete_for_case(case_id)
        self._automation.delete_for_case(case_id)
        self._target_executions.delete_for_case(case_id)
        self._demo_scenarios.delete_for_case(case_id)
        self._onboarding.delete_for_case(case_id)
        return binding_id


class CaseDeletionService:
    """Re-authorize, delete atomically where durable, then clear transient state."""

    def __init__(
        self,
        *,
        cases: OnboardingService,
        access_policy: CaseAccessPolicy,
        repository: CaseDeletionRepository,
        release_provider_binding: Callable[[str], None],
        release_demo_transients: Callable[[UUID], None],
        delete_workflow_data: Callable[[UUID], None] | None = None,
    ) -> None:
        self._cases = cases
        self._access_policy = access_policy
        self._repository = repository
        self._release_provider_binding = release_provider_binding
        self._release_demo_transients = release_demo_transients
        self._delete_workflow_data = delete_workflow_data

    def delete(self, actor: AuthenticatedActor, case_id: UUID) -> None:
        with self._cases.case_lock(case_id):
            self._access_policy.require_case_access(actor, case_id, self._cases)
            if actor.profile.role not in {Role.DIRECTOR, Role.RELATIONSHIP_MANAGER}:
                raise CaseDeleteForbiddenError
            try:
                # D-121: first, so collected answers can never outlive their case.
                if self._delete_workflow_data is not None:
                    self._delete_workflow_data(case_id)
                binding_id = self._repository.delete(case_id)
            except PersistenceConflictError:
                raise CaseDeleteConflictError from None
            except PersistenceUnavailableError:
                raise CaseDeleteUnavailableError from None
            if binding_id is not None:
                self._release_provider_binding(binding_id)
            self._release_demo_transients(case_id)


__all__ = [
    "CaseDeleteConflictError",
    "CaseDeleteForbiddenError",
    "CaseDeleteUnavailableError",
    "CaseDeletionRepository",
    "CaseDeletionService",
    "CaseNotAvailableError",
    "InMemoryCaseDeletionRepository",
]
