"""Integrated synthetic scenario selection isolated from generic automation."""

from enum import StrEnum
from threading import RLock
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
    LOW_CONFIDENCE_DOCUMENT = "LOW_CONFIDENCE_DOCUMENT"
    OWNERSHIP_EXCEPTION = "OWNERSHIP_EXCEPTION"
    OWNERSHIP_INCOMPLETE = "OWNERSHIP_INCOMPLETE"
    EXISTING_PARTY = "EXISTING_PARTY"
    TARGET_FAILURE = "TARGET_FAILURE"
    TECHNICAL_FAILURE = "TECHNICAL_FAILURE"


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
        if self._scenario == ZeroTouchDemoScenario.DOCUMENT_DISCREPANCY:
            values[DocumentFieldKey.LEGAL_NAME] = "SYNTHETIC CONFLICTING NAME PTE. LTD."
        if self._scenario == ZeroTouchDemoScenario.LOW_CONFIDENCE_DOCUMENT:
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

    def __init__(self) -> None:
        self._scenarios: dict[UUID, ZeroTouchDemoScenario] = {}
        self._lock = RLock()

    def uen_for(self, supplied_uen: str, scenario: ZeroTouchDemoScenario) -> str:
        if scenario == ZeroTouchDemoScenario.EXISTING_PARTY:
            return "202400005E"
        if scenario == ZeroTouchDemoScenario.TARGET_FAILURE:
            return "202400003C"
        return supplied_uen

    def register(self, case_id: UUID, scenario: ZeroTouchDemoScenario) -> None:
        with self._lock:
            self._scenarios[case_id] = scenario

    def scenario_for(self, case_id: UUID) -> ZeroTouchDemoScenario:
        with self._lock:
            return self._scenarios.get(
                case_id, ZeroTouchDemoScenario.STRAIGHT_THROUGH
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
            ZeroTouchDemoScenario.OWNERSHIP_INCOMPLETE: MockOwnershipScenario.INCOMPLETE_CHAIN,
        }
        return MockOwnershipProvider(mapping.get(scenario, MockOwnershipScenario.DIRECT_OWNER))
