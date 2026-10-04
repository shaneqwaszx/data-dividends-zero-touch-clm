"""Map immutable canonical/target-policy input into the GoldTier XPI sandbox dialect."""

from __future__ import annotations

from typing import Literal

from app.connectors.goldtier_xpi_models import (
    XpiAmendCustomerRequest,
    XpiCreateCustomerPolicyRequest,
    XpiCreateCustomerRequest,
    XpiCustomerSearchRequest,
    XpiLegalRegisteredAddress,
    XpiRegistration,
    XpiSystemReference,
)
from app.domain.policy import (
    AuthorityLabelledTargetValue,
    GoldTierTargetPolicySnapshot,
    PolicyAuthority,
    is_usable_policy_text,
)
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
)


class MissingTargetEnrichmentError(ValueError):
    """Block XPI mutation construction without exposing missing values."""

    def __init__(self, missing_fields: tuple[str, ...]) -> None:
        self.missing_fields = missing_fields
        super().__init__("Required GoldTier target enrichment is unavailable.")


class InvalidTargetPreparationError(ValueError):
    pass


def _authority(value: PolicyAuthority) -> TargetFieldAuthority:
    return TargetFieldAuthority(value.value)


def _canonical_field(name: str, value: str, *, required: bool = True) -> GoldTierPreviewField:
    return GoldTierPreviewField(
        target_field=name,
        value=value,
        provenance=TargetValueProvenance.CANONICAL_EVIDENCE,
        authority=TargetFieldAuthority.CANONICAL_EVIDENCE,
        required=required,
        missing=False,
        validation=TargetFieldValidation.VALID,
    )


def _derived_field(name: str, value: str | None, *, required: bool = True) -> GoldTierPreviewField:
    missing = required and value is None
    return GoldTierPreviewField(
        target_field=name,
        value=value,
        provenance=TargetValueProvenance.SYSTEM_DERIVED,
        authority=TargetFieldAuthority.PROJECT_DEFINED_PROVISIONAL,
        required=required,
        missing=missing,
        validation=(TargetFieldValidation.MISSING if missing else TargetFieldValidation.VALID),
    )


def _policy_field(
    name: str,
    item: AuthorityLabelledTargetValue,
    *,
    required: bool = True,
) -> GoldTierPreviewField:
    missing = required and (
        item.authority == PolicyAuthority.TBD_SPONSOR or item.value == "TBD_SPONSOR"
    )
    invalid = required and not missing and not is_usable_policy_text(item.value)
    return GoldTierPreviewField(
        target_field=name,
        value=None if missing or invalid else item.value,
        provenance=TargetValueProvenance.POLICY,
        authority=_authority(item.authority),
        required=required,
        missing=missing,
        validation=(
            TargetFieldValidation.MISSING
            if missing
            else TargetFieldValidation.INVALID
            if invalid
            else TargetFieldValidation.VALID
        ),
    )


def _optional_policy_field(
    name: str, item: AuthorityLabelledTargetValue
) -> GoldTierPreviewField:
    explicit = item.authority in {
        PolicyAuthority.SPONSOR_SUPPLIED,
        PolicyAuthority.SANDBOX_OBSERVED,
    }
    usable = explicit and is_usable_policy_text(item.value)
    return GoldTierPreviewField(
        target_field=name,
        value=item.value if usable else "",
        provenance=TargetValueProvenance.POLICY,
        authority=_authority(item.authority),
        required=False,
        missing=False,
        validation=TargetFieldValidation.VALID,
    )


def _optional_policy_value(item: AuthorityLabelledTargetValue) -> str:
    if item.authority in {
        PolicyAuthority.SPONSOR_SUPPLIED,
        PolicyAuthority.SANDBOX_OBSERVED,
    } and is_usable_policy_text(item.value):
        return item.value
    return ""


def _operation(
    name: Literal["SEARCH", "SHELL", "POLICY", "AMEND", "READBACK"],
    fields: tuple[GoldTierPreviewField, ...],
) -> GoldTierOperationPreview:
    missing = tuple(item.target_field for item in fields if item.missing)
    invalid = any(item.validation == TargetFieldValidation.INVALID for item in fields)
    return GoldTierOperationPreview(
        operation=name,
        fields=fields,
        missing_fields=missing,
        validation=(
            TargetFieldValidation.INVALID
            if invalid
            else TargetFieldValidation.MISSING
            if missing
            else TargetFieldValidation.VALID
        ),
    )


class GoldTierXpiRequestMapper:
    """Own XPI request preparation; it performs no transport or business resolution."""

    environment = GoldTierProviderMode.SANDBOX

    @staticmethod
    def _validate_submission(submission: GoldTierSubmissionInput) -> None:
        if submission.provider_mode != GoldTierProviderMode.SANDBOX:
            raise InvalidTargetPreparationError("XPI mapper requires a sandbox submission")

    @classmethod
    def _target_policy(
        cls, submission: GoldTierSubmissionInput
    ) -> GoldTierTargetPolicySnapshot:
        cls._validate_submission(submission)
        policy = submission.target_policy
        if policy is None:
            raise MissingTargetEnrichmentError(("targetPolicy",))
        if not policy.dispatch_ready:
            if policy.missing_fields:
                raise MissingTargetEnrichmentError(policy.missing_fields)
            raise InvalidTargetPreparationError("GoldTier target enrichment is invalid")
        if submission.target_external_key is None:
            raise MissingTargetEnrichmentError(("customerExternalSystemKey",))
        return policy

    def build_search_request(
        self, submission: GoldTierSubmissionInput
    ) -> XpiCustomerSearchRequest:
        self._validate_submission(submission)
        entity = submission.canonical_entity
        return XpiCustomerSearchRequest(
            legal_name=entity.legal_name,
            country_of_incorporation=entity.country_of_incorporation,
        )

    def build_readback_request(
        self, submission: GoldTierSubmissionInput, party_id: str
    ) -> XpiCustomerSearchRequest:
        self._validate_submission(submission)
        return XpiCustomerSearchRequest(goldtier_id=party_id)

    def build_shell_request(
        self, submission: GoldTierSubmissionInput
    ) -> XpiCreateCustomerRequest:
        policy = self._target_policy(submission)
        external_key = submission.target_external_key
        if external_key is None:
            raise MissingTargetEnrichmentError(("customerExternalSystemKey",))
        entity = submission.canonical_entity
        address = entity.registered_address
        return XpiCreateCustomerRequest(
            legal_name=entity.legal_name,
            kyc_customer_type=policy.kyc_customer_type.value,
            client_segment=policy.client_segment.value,
            system_reference=XpiSystemReference(
                customer_external_system=policy.customer_external_system.value,
                customer_external_system_key=external_key,
            ),
            legal_registered_address=XpiLegalRegisteredAddress(
                street1=address.address_line_1,
                street2=address.address_line_2,
                country_iso2=address.country_code,
                zip=address.postal_code,
            ),
            registration=XpiRegistration(
                registration_type=policy.registration_type.value,
                country_iso2=entity.country_of_incorporation,
                registration_number=entity.registration_number,
            ),
            country_of_incorporation=entity.country_of_incorporation,
        )

    def build_policy_request(
        self,
        submission: GoldTierSubmissionInput,
        party_id: str,
    ) -> XpiCreateCustomerPolicyRequest:
        policy = self._target_policy(submission)
        external_key = submission.target_external_key
        if external_key is None:
            raise MissingTargetEnrichmentError(("customerExternalSystemKey",))
        return XpiCreateCustomerPolicyRequest(
            customer_external_system=policy.customer_external_system.value,
            customer_external_system_key=external_key,
            goldtier_id=party_id,
            policy=policy.policy.value,
            booking_entity=policy.booking_entity.value,
            account_entity_type=_optional_policy_value(policy.account_entity_type),
            product_type=_optional_policy_value(policy.product_type),
        )

    def build_amend_request(
        self,
        submission: GoldTierSubmissionInput,
        party_id: str,
    ) -> XpiAmendCustomerRequest:
        policy = self._target_policy(submission)
        return XpiAmendCustomerRequest(
            goldtier_id=party_id,
            policy=policy.policy.value,
        )

    def requires_amend(self, submission: GoldTierSubmissionInput) -> bool:
        if submission.target_policy is None or not submission.target_policy.dispatch_ready:
            return False
        request = self.build_amend_request(submission, "PRE_DISPATCH_VALIDATION")
        return request.anzsic is not None or request.group_company_name is not None

    def build_preview(self, submission: GoldTierSubmissionInput) -> GoldTierRequestPreview:
        self._validate_submission(submission)
        entity = submission.canonical_entity
        address = entity.registered_address
        policy = submission.target_policy
        if policy is None:
            raise MissingTargetEnrichmentError(("targetPolicy",))

        search = _operation(
            "SEARCH",
            (
                _canonical_field("legalName", entity.legal_name),
                _canonical_field(
                    "countryOfIncorporation", entity.country_of_incorporation
                ),
            ),
        )

        shell = _operation(
            "SHELL",
            (
                _canonical_field("legalName", entity.legal_name),
                _policy_field("kycCustomerType", policy.kyc_customer_type),
                _policy_field("clientSegment", policy.client_segment),
                _policy_field(
                    "systemReference.customerExternalSystem",
                    policy.customer_external_system,
                ),
                _derived_field(
                    "systemReference.customerExternalSystemKey",
                    submission.target_external_key,
                ),
                _canonical_field("legalRegisteredAddress.street1", address.address_line_1),
                *(
                    (_canonical_field(
                        "legalRegisteredAddress.street2", address.address_line_2, required=False
                    ),)
                    if address.address_line_2 is not None else ()
                ),
                _canonical_field("legalRegisteredAddress.countryIso2", address.country_code),
                _canonical_field("legalRegisteredAddress.zip", address.postal_code),
                _policy_field("registration.registrationType", policy.registration_type),
                _canonical_field(
                    "registration.countryIso2", entity.country_of_incorporation
                ),
                _canonical_field(
                    "registration.registrationNumber", entity.registration_number
                ),
                _canonical_field(
                    "countryOfIncorporation", entity.country_of_incorporation
                ),
            ),
        )
        policy_operation = _operation(
            "POLICY",
            (
                _policy_field(
                    "customerExternalSystem", policy.customer_external_system
                ),
                _derived_field(
                    "customerExternalSystemKey", submission.target_external_key
                ),
                _derived_field("goldTierId", "BOUND_FROM_SEARCH_OR_SHELL"),
                _policy_field("policy", policy.policy),
                _policy_field("bookingEntity", policy.booking_entity),
                _optional_policy_field("accountEntityType", policy.account_entity_type),
                _optional_policy_field("productType", policy.product_type),
            ),
        )
        amend_fields: tuple[GoldTierPreviewField, ...] = (
            _derived_field("goldTierId", "BOUND_FROM_SEARCH_OR_SHELL"),
            _policy_field("policy", policy.policy),
        )
        if self.requires_amend(submission):
            enrichment = self.build_amend_request(submission, "PRE_DISPATCH_VALIDATION")
            for name, value in (
                ("ANZSIC", enrichment.anzsic),
                ("groupCompanyName", enrichment.group_company_name),
            ):
                if value is not None:
                    amend_fields += (_derived_field(name, value),)
        amend = _operation("AMEND", amend_fields)
        readback = _operation(
            "READBACK",
            (_derived_field("goldTierID", "BOUND_FROM_SEARCH_OR_SHELL"),),
        )
        operations = (
            (search, shell, policy_operation, amend, readback)
            if self.requires_amend(submission)
            else (search, shell, policy_operation, readback)
        )
        return GoldTierRequestPreview(
            environment="SANDBOX",
            policy_version=submission.policy_catalogue_version,
            operations=operations,
            dispatch_ready=all(
                item.validation == TargetFieldValidation.VALID for item in operations
            ),
        )

    def validate_pre_dispatch(self, submission: GoldTierSubmissionInput) -> None:
        """Validate every customer request shape before reserving ledger ownership."""

        validation_party_id = "PRE_DISPATCH_VALIDATION"
        self.build_search_request(submission)
        self.build_shell_request(submission)
        self.build_policy_request(submission, validation_party_id)
        self.build_amend_request(submission, validation_party_id)
        self.build_readback_request(submission, validation_party_id)
