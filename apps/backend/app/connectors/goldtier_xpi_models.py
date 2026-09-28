"""Strict request DTOs for the sponsor-supplied GoldTier XPI sandbox dialect."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Annotated

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def _safe_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    if not normalized or any(ord(character) < 32 for character in normalized):
        raise ValueError("XPI text must be non-blank control-free text")
    return normalized


def _safe_optional_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    if value == "":
        return value
    return _safe_text(value)


XpiText = Annotated[
    str,
    BeforeValidator(_safe_text),
    Field(min_length=1, max_length=240),
]
XpiOptionalText = Annotated[
    str,
    BeforeValidator(_safe_optional_text),
    Field(max_length=240),
]
XpiIdentifier = Annotated[
    str,
    BeforeValidator(_safe_text),
    Field(min_length=1, max_length=96),
]
XpiCountry = Annotated[
    str,
    BeforeValidator(_safe_text),
    Field(pattern=r"^[A-Za-z]{2}$"),
]


def _bounded_owner_percent(value: str) -> str:
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        raise ValueError("XPI owner percentage is invalid") from None
    if not parsed.is_finite() or parsed < Decimal("0") or parsed > Decimal("100"):
        raise ValueError("XPI owner percentage must be between 0 and 100")
    return value


XpiOwnerPercent = Annotated[
    str,
    BeforeValidator(_safe_text),
    Field(pattern=r"^(?:0|[1-9][0-9]?|100)(?:\.[0-9]{1,6})?$"),
    AfterValidator(_bounded_owner_percent),
]


class XpiContractModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
        frozen=True,
        revalidate_instances="always",
    )


class XpiCustomerSearchRequest(XpiContractModel):
    goldtier_id: XpiIdentifier | None = Field(
        default=None,
        validation_alias="goldTierID",
        serialization_alias="goldTierID",
    )
    legal_name: XpiText | None = Field(
        default=None,
        validation_alias="legalName",
        serialization_alias="legalName",
    )
    group_company_name: XpiText | None = Field(
        default=None,
        validation_alias="groupCompanyName",
        serialization_alias="groupCompanyName",
    )
    country_of_incorporation: XpiCountry | None = Field(
        default=None,
        validation_alias="countryOfIncorporation",
        serialization_alias="countryOfIncorporation",
    )

    @model_validator(mode="after")
    def at_least_one_criterion(self) -> XpiCustomerSearchRequest:
        if not any(
            (
                self.goldtier_id,
                self.legal_name,
                self.group_company_name,
                self.country_of_incorporation,
            )
        ):
            raise ValueError("XPI Search requires at least one criterion")
        return self

    def query_items(self) -> tuple[tuple[str, str], ...]:
        values = (
            ("goldTierID", self.goldtier_id),
            ("legalName", self.legal_name),
            ("groupCompanyName", self.group_company_name),
            ("countryOfIncorporation", self.country_of_incorporation),
        )
        return tuple((name, value) for name, value in values if value is not None)


class XpiSystemReference(XpiContractModel):
    customer_external_system: XpiText = Field(
        validation_alias="customerExternalSystem",
        serialization_alias="customerExternalSystem",
    )
    customer_external_system_key: XpiIdentifier = Field(
        validation_alias="customerExternalSystemKey",
        serialization_alias="customerExternalSystemKey",
    )


class XpiLegalRegisteredAddress(XpiContractModel):
    address_type: XpiText | None = Field(
        default=None, validation_alias="type", serialization_alias="type"
    )
    street1: XpiText
    street2: XpiText | None = None
    street3: XpiText | None = None
    city: XpiText | None = None
    country_iso2: XpiCountry = Field(
        validation_alias="countryIso2", serialization_alias="countryIso2"
    )
    state: XpiText | None = None
    zip: XpiText


class XpiRegistration(XpiContractModel):
    registration_type: XpiText = Field(
        validation_alias="registrationType", serialization_alias="registrationType"
    )
    country_iso2: XpiCountry = Field(
        validation_alias="countryIso2", serialization_alias="countryIso2"
    )
    registration_number: XpiIdentifier = Field(
        validation_alias="registrationNumber", serialization_alias="registrationNumber"
    )


class XpiContact(XpiContractModel):
    name: XpiText
    contact_type: XpiText = Field(validation_alias="type", serialization_alias="type")
    phone: XpiText | None = None
    email: Annotated[str, BeforeValidator(_safe_text), Field(max_length=254)] | None = None


class XpiCreateCustomerRequest(XpiContractModel):
    legal_name: XpiText = Field(
        validation_alias="legalName", serialization_alias="legalName"
    )
    kyc_customer_type: XpiText = Field(
        validation_alias="kycCustomerType", serialization_alias="kycCustomerType"
    )
    client_segment: XpiText = Field(
        validation_alias="clientSegment", serialization_alias="clientSegment"
    )
    global_relationship_manager_email: (
        Annotated[str, BeforeValidator(_safe_text), Field(max_length=254)] | None
    ) = Field(
        default=None,
        validation_alias="globalRelationshipManagerEmail",
        serialization_alias="globalRelationshipManagerEmail",
    )
    system_reference: XpiSystemReference = Field(
        validation_alias="systemReference", serialization_alias="systemReference"
    )
    legal_registered_address: XpiLegalRegisteredAddress = Field(
        validation_alias="legalRegisteredAddress",
        serialization_alias="legalRegisteredAddress",
    )
    registration: XpiRegistration
    contact: XpiContact | None = None
    country_of_incorporation: XpiCountry = Field(
        validation_alias="countryOfIncorporation",
        serialization_alias="countryOfIncorporation",
    )
    group_company_name: XpiText | None = Field(
        default=None,
        validation_alias="groupCompanyName",
        serialization_alias="groupCompanyName",
    )


class XpiCreateCustomerPolicyRequest(XpiContractModel):
    customer_external_system: XpiText = Field(
        validation_alias="customerExternalSystem",
        serialization_alias="customerExternalSystem",
    )
    customer_external_system_key: XpiIdentifier = Field(
        validation_alias="customerExternalSystemKey",
        serialization_alias="customerExternalSystemKey",
    )
    goldtier_id: XpiIdentifier = Field(
        validation_alias="goldTierId", serialization_alias="goldTierId"
    )
    policy: XpiText
    booking_entity: XpiText = Field(
        validation_alias="bookingEntity", serialization_alias="bookingEntity"
    )
    account_entity_type: XpiOptionalText = Field(
        default="",
        validation_alias="accountEntityType", serialization_alias="accountEntityType"
    )
    product_type: XpiOptionalText = Field(
        default="",
        validation_alias="productType", serialization_alias="productType"
    )


class XpiAmendCustomerRequest(XpiContractModel):
    goldtier_id: XpiIdentifier = Field(
        validation_alias="goldTierId", serialization_alias="goldTierId"
    )
    policy: XpiText
    anzsic: XpiText | None = None
    group_company_name: XpiText | None = Field(
        default=None,
        validation_alias="groupCompanyName",
        serialization_alias="groupCompanyName",
    )


class XpiRelationshipAttribute(XpiContractModel):
    relationship_type: XpiText = Field(
        validation_alias="relationshipType", serialization_alias="relationshipType"
    )
    relationship_titles: tuple[XpiText, ...] = Field(
        min_length=1,
        max_length=16,
        validation_alias="relationshipTitles",
        serialization_alias="relationshipTitles",
    )
    receivable_financing: bool = Field(
        validation_alias="receivableFinancing", serialization_alias="receivableFinancing"
    )
    authorized_signatory: bool = Field(
        validation_alias="authorizedSignatory", serialization_alias="authorizedSignatory"
    )
    controller: bool
    responsible_entity: bool = Field(
        validation_alias="responsibleEntity", serialization_alias="responsibleEntity"
    )
    owner_type: XpiText = Field(
        validation_alias="ownerType", serialization_alias="ownerType"
    )
    owner_percent: XpiOwnerPercent = Field(
        validation_alias="ownerPercent", serialization_alias="ownerPercent"
    )


class XpiRelationships(XpiContractModel):
    relationship_attribute: XpiRelationshipAttribute = Field(
        validation_alias="relationshipAttribute",
        serialization_alias="relationshipAttribute",
    )


class XpiCreateRelatedPartyPolicyRequest(XpiContractModel):
    customer_external_system: XpiText = Field(
        validation_alias="customerExternalSystem",
        serialization_alias="customerExternalSystem",
    )
    customer_external_system_key: XpiIdentifier = Field(
        validation_alias="customerExternalSystemKey",
        serialization_alias="customerExternalSystemKey",
    )
    goldtier_id: XpiIdentifier = Field(
        validation_alias="goldTierId", serialization_alias="goldTierId"
    )
    child_id: XpiIdentifier = Field(
        validation_alias="childId", serialization_alias="childId"
    )
    anzsic: XpiText | None = None
    country_of_incorporation: XpiCountry = Field(
        validation_alias="countryOfIncorporation",
        serialization_alias="countryOfIncorporation",
    )
    policy: XpiText
    relationships: XpiRelationships


class XpiAmendRelatedPartyRequest(XpiContractModel):
    customer_external_system: XpiText = Field(
        validation_alias="customerExternalSystem",
        serialization_alias="customerExternalSystem",
    )
    customer_external_system_key: XpiIdentifier = Field(
        validation_alias="customerExternalSystemKey",
        serialization_alias="customerExternalSystemKey",
    )
    goldtier_id: XpiIdentifier = Field(
        validation_alias="goldTierId", serialization_alias="goldTierId"
    )
    policy: XpiText
    group_company_name: XpiText | None = Field(
        default=None,
        validation_alias="groupCompanyName",
        serialization_alias="groupCompanyName",
    )
