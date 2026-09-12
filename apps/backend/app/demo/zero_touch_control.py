"""Integrated synthetic scenario selection isolated from generic automation."""

from enum import StrEnum
from threading import RLock
from typing import Protocol
from uuid import UUID

from app.connectors.idp import (
    IdpDocumentInput,
    IdpProcessingError,
    IdpProvider,
    IdpProviderMetadata,
    IdpSourceField,
    IdpSourceResult,
)
from app.connectors.mock_ownership import MockOwnershipProvider, MockOwnershipScenario
from app.connectors.ownership import OwnershipProvider
from app.domain.documents import DocumentFieldKey, IdpEnvironment
from app.domain.models import CanonicalLegalEntity
from app.services.document_processing import canonical_value_for_field


class ZeroTouchDemoScenario(StrEnum):
    STRAIGHT_THROUGH = "STRAIGHT_THROUGH"
    DOCUMENT_DISCREPANCY = "DOCUMENT_DISCREPANCY"
    MULTIPLE_DOCUMENT_BLOCKERS = "MULTIPLE_DOCUMENT_BLOCKERS"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    LOW_CONFIDENCE_DOCUMENT = "LOW_CONFIDENCE_DOCUMENT"
    OWNERSHIP_CYCLE = "OWNERSHIP_CYCLE"
    OWNERSHIP_EXCEPTION = "OWNERSHIP_EXCEPTION"
    OWNERSHIP_INCOMPLETE = "OWNERSHIP_INCOMPLETE"
    MULTIPLE_OWNERSHIP_PATHS = "MULTIPLE_OWNERSHIP_PATHS"
    EXISTING_PARTY = "EXISTING_PARTY"
    TARGET_FAILURE = "TARGET_FAILURE"
    PARTIAL_AMEND = "PARTIAL_AMEND"
    RECOVERY = "RECOVERY"
    TECHNICAL_FAILURE = "TECHNICAL_FAILURE"


class DemoScenarioRepository(Protocol):
    def set(self, case_id: UUID, scenario: str) -> None: ...

    def get(self, case_id: UUID) -> str | None: ...

    def delete_for_case(self, case_id: UUID) -> None: ...


class InMemoryDemoScenarioRepository:
    def __init__(self) -> None:
        self._scenarios: dict[UUID, str] = {}
        self._lock = RLock()

    def set(self, case_id: UUID, scenario: str) -> None:
        with self._lock:
            self._scenarios[case_id] = scenario

    def get(self, case_id: UUID) -> str | None:
        with self._lock:
            return self._scenarios.get(case_id)

    def delete_for_case(self, case_id: UUID) -> None:
        with self._lock:
            self._scenarios.pop(case_id, None)


class _CaseMatchingMockIdpProvider:
    """Synthetic provider configured at the demo boundary from canonical test data."""

    def __init__(
        self, *, scenario: ZeroTouchDemoScenario, entity: CanonicalLegalEntity
    ) -> None:
        self._scenario = scenario
        self._entity = entity.model_copy(deep=True)

    @property
    def metadata(self) -> object:
        return IdpProviderMetadata(
            provider_name="MOCK_IDP",
            environment=IdpEnvironment.MOCK,
        )

    def process(self, document: IdpDocumentInput) -> object:
        if self._scenario == ZeroTouchDemoScenario.TECHNICAL_FAILURE:
            raise IdpProcessingError
        values = {
            key: canonical_value_for_field(self._entity, key) for key in DocumentFieldKey
        }
        confidence = {key: 0.97 for key in DocumentFieldKey}
        if self._scenario in {
            ZeroTouchDemoScenario.DOCUMENT_DISCREPANCY,
            ZeroTouchDemoScenario.MULTIPLE_DOCUMENT_BLOCKERS,
        }:
            values[DocumentFieldKey.LEGAL_NAME] = "SYNTHETIC CONFLICTING NAME PTE. LTD."
        if self._scenario in {
            ZeroTouchDemoScenario.LOW_CONFIDENCE,
            ZeroTouchDemoScenario.LOW_CONFIDENCE_DOCUMENT,
            ZeroTouchDemoScenario.MULTIPLE_DOCUMENT_BLOCKERS,
        }:
            confidence[DocumentFieldKey.REGISTERED_ADDRESS] = 0.54
        return IdpSourceResult(
            profile=document.profile,
            fields=[
                IdpSourceField(
                    field_key=key,
                    value=values[key],
                    confidence=confidence[key],
                    page_number=1,
                    source_reference="SYNTHETIC_PAGE_1",
                )
                for key in DocumentFieldKey
            ],
        )


class ZeroTouchDemoControl:
    """Retain per-case demo selection without exposing it to domain services."""

    def __init__(self, scenario_repository: DemoScenarioRepository | None = None) -> None:
        self._scenario_repository = (
            scenario_repository or InMemoryDemoScenarioRepository()
        )
        self._finalization_failures_remaining: dict[UUID, int] = {}
        self._lock = RLock()

    def uen_for(self, supplied_uen: str, scenario: ZeroTouchDemoScenario) -> str:
        if scenario == ZeroTouchDemoScenario.EXISTING_PARTY:
            return "202400005E"
        if scenario == ZeroTouchDemoScenario.TARGET_FAILURE:
            return "202400003C"
        if scenario == ZeroTouchDemoScenario.PARTIAL_AMEND:
            return "202400004D"
        return supplied_uen

    def register(self, case_id: UUID, scenario: ZeroTouchDemoScenario) -> None:
        with self._lock:
            self._scenario_repository.set(case_id, scenario.value)
            if scenario == ZeroTouchDemoScenario.RECOVERY:
                # Phase 06 retries finalization twice in one invocation. Failing both
                # attempts yields RECOVERY_PENDING; the next explicit resume succeeds.
                self._finalization_failures_remaining[case_id] = 2

    def registered_scenario_for(self, case_id: UUID) -> ZeroTouchDemoScenario | None:
        with self._lock:
            raw = self._scenario_repository.get(case_id)
            return ZeroTouchDemoScenario(raw) if raw is not None else None

    def scenario_for(self, case_id: UUID) -> ZeroTouchDemoScenario:
        with self._lock:
            raw = self._scenario_repository.get(case_id)
            return (
                ZeroTouchDemoScenario(raw)
                if raw is not None
                else ZeroTouchDemoScenario.STRAIGHT_THROUGH
            )

    def idp_provider_for(
        self, case_id: UUID, entity: CanonicalLegalEntity
    ) -> IdpProvider:
        return _CaseMatchingMockIdpProvider(
            scenario=self.scenario_for(case_id), entity=entity
        )

    def ownership_provider_for(self, case_id: UUID) -> OwnershipProvider:
        scenario = self.scenario_for(case_id)
        mapping = {
            ZeroTouchDemoScenario.OWNERSHIP_EXCEPTION: MockOwnershipScenario.CYCLE,
            ZeroTouchDemoScenario.OWNERSHIP_CYCLE: MockOwnershipScenario.CYCLE,
            ZeroTouchDemoScenario.OWNERSHIP_INCOMPLETE: MockOwnershipScenario.INCOMPLETE_CHAIN,
            ZeroTouchDemoScenario.MULTIPLE_OWNERSHIP_PATHS: MockOwnershipScenario.MULTIPLE_PATHS,
        }
        return MockOwnershipProvider(mapping.get(scenario, MockOwnershipScenario.DIRECT_OWNER))

    def should_fail_target_finalization(self, case_id: UUID) -> bool:
        """Inject only the bounded synthetic recovery fault selected at the demo edge."""

        with self._lock:
            remaining = self._finalization_failures_remaining.get(case_id, 0)
            if remaining <= 0:
                return False
            if remaining == 1:
                self._finalization_failures_remaining.pop(case_id, None)
            else:
                self._finalization_failures_remaining[case_id] = remaining - 1
            return True

    def release_case_transients(self, case_id: UUID) -> None:
        """Forget process-local fault counters after a durable case deletion."""

        with self._lock:
            self._finalization_failures_remaining.pop(case_id, None)

    def discard_case(self, case_id: UUID) -> None:
        """Roll back demo-owned state created during a failed establishment."""

        with self._lock:
            self._scenario_repository.delete_for_case(case_id)
            self._finalization_failures_remaining.pop(case_id, None)
