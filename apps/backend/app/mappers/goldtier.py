"""Map canonical entities into the provisional GoldTier Phase 01 DTO subset."""

from datetime import datetime

from app.connectors.goldtier_models import (
    AmendAddress,
    AmendPartyData,
    AmendPartyRequest,
    CreatePolicyRequest,
    CreateShellCustomerRequest,
    NonIndividualProfile,
    PartyNames,
    PolicyDetails,
    SearchPartyRequest,
    ShellParty,
    SourceContext,
)
from app.domain.models import CanonicalLegalEntity
from app.mappers.errors import MappingError

MOCK_POLICY = "SINGAPORE_NTB_MOCK"
MOCK_PARTY_ROLE = "Customer"
MOCK_PARTY_TYPE = "Organisation"


def _required(value: str | None, field_name: str) -> str:
    if value is None or not value.strip():
        raise MappingError(f"Canonical {field_name} is required for target mapping")
    return value


def build_source_context(source_case_id: str, accepted_at: datetime) -> SourceContext:
    return SourceContext(
        source_system="ZERO_TOUCH_CLM",
        source_case_id=source_case_id,
        accepted_by="PHASE_01_MOCK",
        accepted_at=accepted_at,
        source_channel="EDS_API",
    )


def build_search_request(entity: CanonicalLegalEntity) -> SearchPartyRequest:
    return SearchPartyRequest(
        registration_number=_required(entity.registration_number, "registration number")
    )


def build_shell_request(
    entity: CanonicalLegalEntity, source_case_id: str, accepted_at: datetime
) -> CreateShellCustomerRequest:
    legal_name = _required(entity.legal_name, "legal name")
    country_of_incorporation = _required(
        entity.country_of_incorporation, "country of incorporation"
    )
    return CreateShellCustomerRequest(
        party=ShellParty(
            party_role=MOCK_PARTY_ROLE,
            party_type=MOCK_PARTY_TYPE,
            names=PartyNames(legal_name=legal_name),
            non_individual_profile=NonIndividualProfile(
                country_of_incorporation=country_of_incorporation
            ),
        ),
        source_context=build_source_context(source_case_id, accepted_at),
    )


def build_policy_request(
    entity: CanonicalLegalEntity,
    party_id: str,
    source_case_id: str,
    accepted_at: datetime,
) -> CreatePolicyRequest:
    return CreatePolicyRequest(
        goldtier_id=party_id,
        customer_external_system="ACRA",
        customer_external_system_key=entity.registration_number,
        policy_details=PolicyDetails(policy=MOCK_POLICY),
        source_context=build_source_context(source_case_id, accepted_at),
    )


def build_amend_request(
    entity: CanonicalLegalEntity, source_case_id: str, accepted_at: datetime
) -> AmendPartyRequest:
    legal_name = _required(entity.legal_name, "legal name")
    if entity.registered_address is None:
        raise MappingError("Canonical registered address is required for target mapping")
    address = entity.registered_address
    return AmendPartyRequest(
        party_type=MOCK_PARTY_TYPE,
        policy=MOCK_POLICY,
        party=AmendPartyData(
            names=PartyNames(legal_name=legal_name),
            addresses=[
                AmendAddress(
                    address_line_1=address.address_line_1,
                    address_line_2=address.address_line_2,
                    postal_code=address.postal_code,
                    country=address.country_code,
                )
            ],
        ),
        source_context=build_source_context(source_case_id, accepted_at),
    )
