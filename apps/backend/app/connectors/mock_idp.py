"""Deterministic Mock IDP provider; no OCR, networking, or content inference."""

from enum import StrEnum

from app.connectors.idp import (
    IdpDocumentInput,
    IdpProcessingError,
    IdpProviderMetadata,
    IdpSourceField,
    IdpSourceResult,
)
from app.domain.documents import DocumentFieldKey, IdpEnvironment


class MockIdpScenario(StrEnum):
    """Demo-only deterministic scenario selector owned by the Mock provider."""

    ALL_FIELDS_MATCH = "ALL_FIELDS_MATCH"
    FIELD_MISMATCH = "FIELD_MISMATCH"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    MISSING_FIELD = "MISSING_FIELD"
    PROCESSOR_FAILURE = "PROCESSOR_FAILURE"


class MockIdpProvider:
    """Return the explicit project-defined synthetic Phase 03 scenarios."""

    def __init__(
        self, scenario: MockIdpScenario = MockIdpScenario.ALL_FIELDS_MATCH
    ) -> None:
        self._scenario = scenario

    @property
    def metadata(self) -> object:
        return IdpProviderMetadata(
            provider_name="MOCK_IDP",
            environment=IdpEnvironment.MOCK,
        )

    def process(self, document: IdpDocumentInput) -> object:
        if self._scenario == MockIdpScenario.PROCESSOR_FAILURE:
            raise IdpProcessingError

        values: dict[DocumentFieldKey, str | None] = {
            DocumentFieldKey.REGISTRATION_NUMBER: " 202400001a ",
            DocumentFieldKey.LEGAL_NAME: "Merlion Circular Labs Pte. Ltd.",
            DocumentFieldKey.REGISTERED_ADDRESS: (
                "18 Innovation Way, #04-01, 018956, SG"
            ),
            DocumentFieldKey.COUNTRY_OF_INCORPORATION: "sg",
        }
        confidence: dict[DocumentFieldKey, float] = {
            key: 0.97 for key in DocumentFieldKey
        }

        if self._scenario == MockIdpScenario.FIELD_MISMATCH:
            values[DocumentFieldKey.LEGAL_NAME] = "Merlion Circular Labs Pte. Limited"
        elif self._scenario == MockIdpScenario.LOW_CONFIDENCE:
            confidence[DocumentFieldKey.REGISTERED_ADDRESS] = 0.54
        elif self._scenario == MockIdpScenario.MISSING_FIELD:
            values[DocumentFieldKey.REGISTERED_ADDRESS] = None
            confidence[DocumentFieldKey.REGISTERED_ADDRESS] = 0.0

        return IdpSourceResult(
            profile=document.profile,
            fields=[
                IdpSourceField(
                    field_key=key,
                    value=values[key],
                    confidence=confidence[key],
                    page_number=None if values[key] is None else 1,
                    source_reference="SYNTHETIC_PAGE_1",
                )
                for key in DocumentFieldKey
            ],
        )
