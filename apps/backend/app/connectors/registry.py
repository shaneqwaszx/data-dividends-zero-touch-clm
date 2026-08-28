"""Provider-neutral company registry boundary and Singapore ACRA adapter."""

from datetime import datetime
from typing import Protocol

from app.connectors.acra import AcraCompanyPayload, AcraConnector
from app.connectors.errors import (
    AcraMappingError,
    AcraResponseIdentityMismatchError,
    AcraResponseInvalidError,
    AcraUnexpectedMappingError,
)
from app.domain.jurisdiction import (
    JurisdictionCode,
    RegistryProviderCode,
    RegistryRoutingDecision,
    RegistryRoutingStatus,
    is_eligible_singapore_uen,
)
from app.domain.models import CanonicalLegalEntity
from app.mappers.acra import map_acra_company
from app.mappers.errors import MappingError


class RegistryProvider(Protocol):
    """Return canonical company data without leaking provider payloads downstream."""

    provider_code: RegistryProviderCode

    def retrieve_company(self, identifier: str) -> CanonicalLegalEntity | None:
        """Retrieve and map one company profile by registration identifier."""


class AcraIdentifierNotEligibleError(ValueError):
    """A fixed, safe domain error raised before an ineligible ACRA request."""

    def __init__(self) -> None:
        super().__init__("The identifier is not eligible for Singapore ACRA retrieval.")


class AcraRegistryProviderAdapter:
    """Preserve the existing strict ACRA DTO, identity, mapping, and provenance checks."""

    provider_code = RegistryProviderCode.ACRA

    def __init__(self, connector: AcraConnector) -> None:
        self._connector = connector

    def retrieve_company(self, identifier: str) -> CanonicalLegalEntity | None:
        normalized_identifier = identifier.strip().upper()
        if not is_eligible_singapore_uen(normalized_identifier):
            raise AcraIdentifierNotEligibleError
        source_payload = self._connector.fetch_company(normalized_identifier)
        if source_payload is None:
            return None
        try:
            untrusted_payload = (
                source_payload.model_dump(mode="json", warnings=False)
                if isinstance(source_payload, AcraCompanyPayload)
                else source_payload
            )
            validated_payload = AcraCompanyPayload.model_validate(untrusted_payload)
        except Exception as exc:
            raise AcraResponseInvalidError(exc) from None
        if validated_payload.uen.strip().upper() != normalized_identifier:
            raise AcraResponseIdentityMismatchError from None
        try:
            return map_acra_company(validated_payload)
        except MappingError as exc:
            raise AcraMappingError(exc) from None
        except Exception as exc:
            raise AcraUnexpectedMappingError(exc) from None


class RegistryProviderRouter:
    """Closed Phase 09 routing table: Singapore selects ACRA; others stop safely."""

    def __init__(self, acra: RegistryProvider) -> None:
        if acra.provider_code != RegistryProviderCode.ACRA:
            raise ValueError("Singapore registry provider must identify as ACRA")
        self._acra = acra

    def route(
        self, jurisdiction: JurisdictionCode, *, decided_at: datetime
    ) -> tuple[RegistryRoutingDecision, RegistryProvider | None]:
        if jurisdiction == JurisdictionCode.SINGAPORE:
            return (
                RegistryRoutingDecision(
                    status=RegistryRoutingStatus.SELECTED,
                    jurisdiction=jurisdiction,
                    provider=RegistryProviderCode.ACRA,
                    decided_at=decided_at,
                ),
                self._acra,
            )
        return (
            RegistryRoutingDecision(
                status=RegistryRoutingStatus.PROVIDER_NOT_IMPLEMENTED,
                jurisdiction=jurisdiction,
                decided_at=decided_at,
            ),
            None,
        )
