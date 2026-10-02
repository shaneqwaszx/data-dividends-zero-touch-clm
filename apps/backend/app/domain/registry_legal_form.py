"""Bounded source classification; no inference of legal ownership rights."""

from enum import StrEnum


class RegistryLegalForm(StrEnum):
    COMPANY = "COMPANY"
    BUSINESS_PARTNERSHIP = "BUSINESS_PARTNERSHIP"
    LLP = "LLP"
    LP = "LP"
    OTHER = "OTHER"


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
    return RegistryLegalForm.OTHER
