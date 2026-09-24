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
from app.domain.target_preparation import (
    GoldTierOperationPreview,
    GoldTierPreviewField,
    GoldTierRequestPreview,
    TargetFieldAuthority,
    TargetFieldValidation,
    TargetValueProvenance,
)
from app.domain.target_submission import (
    GoldTierProviderMode,
    GoldTierSubmissionInput,
    SubmissionCanonicalEntity,
)
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


TargetEntity = CanonicalLegalEntity | SubmissionCanonicalEntity


def build_search_request(entity: TargetEntity) -> SearchPartyRequest:
    return SearchPartyRequest(
        registration_number=_required(entity.registration_number, "registration number")
    )


def build_shell_request(
    entity: TargetEntity, source_case_id: str, accepted_at: datetime
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
    entity: TargetEntity,
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
    entity: TargetEntity, source_case_id: str, accepted_at: datetime
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


def _mock_preview_field(name: str, value: str) -> GoldTierPreviewField:
    return GoldTierPreviewField(
        target_field=name,
        value=value,
        provenance=TargetValueProvenance.REGISTRY,
        authority=TargetFieldAuthority.PROJECT_DEFINED_PROVISIONAL,
        required=True,
        missing=False,
        validation=TargetFieldValidation.VALID,
    )


class MockGoldTierRequestMapper:
    """Retain the accepted mock DTO mapping behind the shared mapper seam."""

    environment = GoldTierProviderMode.MOCK

    def build_search_request(self, submission: GoldTierSubmissionInput) -> SearchPartyRequest:
        return build_search_request(submission.canonical_entity)

    def build_shell_request(
        self, submission: GoldTierSubmissionInput
    ) -> CreateShellCustomerRequest:
        return build_shell_request(
            submission.canonical_entity,
            submission.source_case_id,
            submission.accepted_at,
        )

    def build_policy_request(
        self, submission: GoldTierSubmissionInput, party_id: str
    ) -> CreatePolicyRequest:
        return build_policy_request(
            submission.canonical_entity,
            party_id,
            submission.source_case_id,
            submission.accepted_at,
        )

    def build_amend_request(
        self, submission: GoldTierSubmissionInput, party_id: str
    ) -> AmendPartyRequest:
        del party_id
        return build_amend_request(
            submission.canonical_entity,
            submission.source_case_id,
            submission.accepted_at,
        )

    def build_preview(self, submission: GoldTierSubmissionInput) -> GoldTierRequestPreview:
        entity = submission.canonical_entity
        operations = (
            GoldTierOperationPreview(
                operation="SEARCH",
                fields=(
                    _mock_preview_field("registrationNumber", entity.registration_number),
                ),
                missing_fields=(),
                validation=TargetFieldValidation.VALID,
            ),
        )
        return GoldTierRequestPreview(
            environment="MOCK",
            policy_version=submission.policy_catalogue_version,
            operations=operations,
            dispatch_ready=True,
        )

    def validate_pre_dispatch(self, submission: GoldTierSubmissionInput) -> None:
        """Construct every operation locally before the ledger or connector is touched."""

        validation_party_id = "PRE_DISPATCH_VALIDATION"
        self.build_search_request(submission)
        self.build_shell_request(submission)
        self.build_policy_request(submission, validation_party_id)
        self.build_amend_request(submission, validation_party_id)
