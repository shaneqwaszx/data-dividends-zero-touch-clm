"""Bounded source classification; no inference of legal ownership rights."""

from enum import StrEnum


class RegistryLegalForm(StrEnum):
    COMPANY = "COMPANY"
    BUSINESS_PARTNERSHIP = "BUSINESS_PARTNERSHIP"
    LLP = "LLP"
    LP = "LP"
    # D-101: the exact source value only; no other value is mapped here.
    GOVERNMENT = "GOVERNMENT"
    OTHER = "OTHER"


class ConditionalLegalForm(StrEnum):
    """ADR-018 §2.1: the legal forms a workflow condition may name.

    Exactly ``RegistryLegalForm`` without ``OTHER`` (B5): an ``OTHER`` entity is unverified and
    already receives every conditional obligation. No new classification is introduced.
    """

    COMPANY = RegistryLegalForm.COMPANY.value
    BUSINESS_PARTNERSHIP = RegistryLegalForm.BUSINESS_PARTNERSHIP.value
    LLP = RegistryLegalForm.LLP.value
    LP = RegistryLegalForm.LP.value
    GOVERNMENT = RegistryLegalForm.GOVERNMENT.value


def classify_registry_legal_form(source_value: str | None) -> RegistryLegalForm:
    value = (source_value or "").strip().upper().replace("_", " ")
    if value in {
        "COMPANY",
        "LOCAL COMPANY",
        "PRIVATE COMPANY LIMITED BY SHARES",
        "PRIVATE LIMITED COMPANY",
        "EXEMPT PRIVATE COMPANY LIMITED BY SHARES",
        "PUBLIC COMPANY LIMITED BY SHARES",
        "PUBLIC COMPANY LIMITED BY GUARANTEE",
    }:
        return RegistryLegalForm.COMPANY
    if value in {"BUSINESS", "PARTNERSHIP", "SOLE PROPRIETORSHIP"}:
        return RegistryLegalForm.BUSINESS_PARTNERSHIP
    if value in {"LLP", "LIMITED LIABILITY PARTNERSHIP"}:
        return RegistryLegalForm.LLP
    if value in {"LP", "LIMITED PARTNERSHIP"}:
        return RegistryLegalForm.LP
    if value == "GOVERNMENT":
        return RegistryLegalForm.GOVERNMENT
    return RegistryLegalForm.OTHER
