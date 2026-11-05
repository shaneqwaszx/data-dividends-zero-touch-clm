"""Read-only values an onboarded case offers to existing-case workflows (D-123)."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.documents import DocumentProcessingRecord, DocumentProcessingState
from app.domain.models import OnboardingCase
from app.domain.onboarding_intelligence import MockRiskBand, OnboardingIntelligenceRecord
from app.domain.ownership import OwnershipAnalysisRecord
from app.domain.reconciliation import ReconciliationCaseRecord
from app.domain.target_classification import TargetClassificationKey

_RISK_LABELS = {
    MockRiskBand.LOW: "Low",
    MockRiskBand.MEDIUM: "Medium",
    MockRiskBand.HIGH: "High",
}
_OWNER_TYPE_LABELS = {"NATURAL_PERSON": "Natural person", "LEGAL_ENTITY": "Legal entity"}


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def _identity_values(case: OnboardingCase) -> dict[str, str | None]:
    entity = case.entity
    identity = case.initial_identity
    address = entity.registered_address if entity else None
    jurisdiction = case.jurisdiction_resolution
    return {
        "CASE_REFERENCE": case.source_case_id,
        "PRIORITY": None if case.priority is None else str(case.priority),
        "LEGAL_NAME": (entity.legal_name if entity else None)
        or (identity.legal_name if identity else None),
        "REGISTRATION_ID": case.requested_uen,
        "COUNTRY": (entity.country_of_incorporation if entity else None)
        or (identity.country_of_incorporation if identity else None),
        "REGISTERED_ADDRESS": (
            None
            if address is None
            else " ".join(
                part
                for part in (address.address_line_1, address.address_line_2, address.postal_code)
                if part
            )
        ),
        "JURISDICTION": (
            None
            if jurisdiction is None or jurisdiction.resolved_jurisdiction is None
            else str(jurisdiction.resolved_jurisdiction)
        ),
    }


def _target_values(case: OnboardingCase) -> dict[str, str | None]:
    search = case.initial_target_search
    result = case.goldtier_result
    selections = {item.field_key: item.value for item in case.target_classification_selections}
    policy = case.policy_snapshot.goldtier_target
    confirmation = case.target_dispatch_confirmation
    return {
        "EXISTING_CUSTOMER": (
            None if search is None else _yes_no(search.disposition == "EXACT_MATCH")
        ),
        "GOLDTIER_ID": result.party_id if result else None,
        "KYC_CUSTOMER_TYPE": selections.get(TargetClassificationKey.KYC_CUSTOMER_TYPE)
        or (policy.kyc_customer_type.value if policy else None),
        "CLIENT_SEGMENT": selections.get(TargetClassificationKey.CLIENT_SEGMENT)
        or (policy.client_segment.value if policy else None),
        "BOOKING_ENTITY": policy.booking_entity.value if policy else None,
        "REVIEWED_BY": confirmation.actor_id if confirmation else None,
        "REVIEW_DATE": confirmation.confirmed_at.date().isoformat() if confirmation else None,
        "READY_TO_SEND": None if confirmation is None else "Yes",
    }


def _document_values(documents: Sequence[DocumentProcessingRecord]) -> dict[str, str | None]:
    if not documents:
        return {}
    return {
        "DOCUMENT_NAME": ", ".join(item.display_name for item in documents),
        "DOCUMENT_REVIEWED": _yes_no(
            all(item.state == DocumentProcessingState.REVIEWED for item in documents)
        ),
    }


def _ownership_values(ownership: OwnershipAnalysisRecord | None) -> dict[str, str | None]:
    candidates = ownership.candidates if ownership else ()
    if not candidates:
        return {}
    parties = [item.party for item in candidates]
    types = {str(party.party_type) for party in parties}
    return {
        "OWNER_NAME": ", ".join(party.display_name for party in parties),
        "OWNER_TYPE": _OWNER_TYPE_LABELS.get(next(iter(types))) if len(types) == 1 else None,
        # One number cannot describe several owners, so that stays for a person to enter.
        "OWNERSHIP_PERCENT": (
            str(candidates[0].aggregated_ownership_percent) if len(candidates) == 1 else None
        ),
    }


def onboarded_case_values(
    case: OnboardingCase,
    *,
    documents: Sequence[DocumentProcessingRecord],
    ownership: OwnershipAnalysisRecord | None,
    reconciliation: ReconciliationCaseRecord | None,
    intelligence: OnboardingIntelligenceRecord | None,
) -> dict[str, str]:
    """Only values the case really holds: an unknown value is simply left out."""

    risk = intelligence.mock_risk if intelligence else None
    values: dict[str, str | None] = {
        **_identity_values(case),
        **_target_values(case),
        **_document_values(documents),
        **_ownership_values(ownership),
        "DISCREPANCIES_FOUND": (
            None if reconciliation is None else _yes_no(bool(reconciliation.discrepancies))
        ),
        "RISK_LEVEL": _RISK_LABELS.get(risk.band) if risk else None,
    }
    return {key: value for key, value in values.items() if value}
