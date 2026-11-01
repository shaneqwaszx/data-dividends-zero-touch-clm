"""D-101 fail-closed cross-checks: registry partners against the partnership agreement.

The registry lists a partnership's partners by name and role only. Their shares come
from a reviewed partnership agreement, proposed per row and confirmed by the RM through
the existing manual ownership declaration. These checks never accept or correct a share;
any mismatch keeps the case blocked for review.
"""

from collections import Counter
from collections.abc import Iterable, Sequence
from decimal import Decimal

from app.domain.documents import DocumentOwnershipObservation, DocumentProcessingRecord
from app.domain.models import (
    RegistryAcquisitionBundle,
    RegistryOperation,
    RegistryOperationStatus,
    SourceEnvironment,
)
from app.domain.registry_legal_form import RegistryLegalForm, classify_registry_legal_form
from app.services.document_ownership import normalized_party_name

PARTNERSHIP_REGISTRY_ROLE = "PARTNER"
PARTNER_SHARE_ROW_MARKER = "_PARTNER_SHARE_ROW_"  # as set by the local PDF IDP reader


def registry_partner_names(acquisition: RegistryAcquisitionBundle | None) -> tuple[str, ...]:
    """Partner names for the D-101 partnership shape: partners listed, no registry shares."""
    if (
        acquisition is None
        or classify_registry_legal_form(acquisition.entity_profile.party_type)
        != RegistryLegalForm.BUSINESS_PARTNERSHIP
        or acquisition.relationships
    ):
        return ()
    listed = tuple(
        party.name
        for party in acquisition.ownership_parties
        if party.source_category == PARTNERSHIP_REGISTRY_ROLE
    )
    if listed or not _shareholder_method_unsupported(acquisition):
        return listed
    # D-113: the Marketplace Mock lists a partnership's partners only as officers.
    # A current partner is a PARTNER role with no withdrawal (cessation) date.
    return tuple(
        officer.name
        for officer in acquisition.officers
        if officer.role.strip().upper() == PARTNERSHIP_REGISTRY_ROLE
        and officer.cessation_date is None
        and officer.provenance.environment == SourceEnvironment.MOCK
    )


def _shareholder_method_unsupported(acquisition: RegistryAcquisitionBundle) -> bool:
    """Only the Marketplace Mock lane marks the shareholder lookup unsupported for a non-company."""
    return any(
        result.operation == RegistryOperation.OWNERSHIP_PARTIES
        and result.status == RegistryOperationStatus.UNSUPPORTED
        for result in acquisition.operation_results
    )


def agreement_rows(document: DocumentProcessingRecord) -> tuple[DocumentOwnershipObservation, ...]:
    return tuple(
        item
        for item in document.ownership_observations
        if PARTNER_SHARE_ROW_MARKER in item.source_reference
    )


def partnership_agreement_issues(
    *,
    registry_partners: Sequence[str],
    rows: Sequence[DocumentOwnershipObservation],
    root_uen: str,
    confidence_threshold: float,
    declared: Iterable[tuple[str, Decimal]] | None = None,
) -> tuple[str, ...]:
    """Every failed check, in a stable order; empty only when all of them pass."""
    if not rows:
        return ("PARTNERSHIP_AGREEMENT_MISSING",)
    issues: list[str] = []
    if any(
        item.extraction_quality != "HIGH" or item.evidence_score < confidence_threshold
        for item in rows
    ):
        issues.append("PARTNERSHIP_AGREEMENT_LOW_CONFIDENCE")
    if any(item.owned_entity_registration_identifier != root_uen for item in rows):
        issues.append("PARTNERSHIP_AGREEMENT_WRONG_ENTITY")
    names = [normalized_party_name(item.owner_name) for item in rows]
    if len(set(names)) != len(names):
        issues.append("PARTNERSHIP_DUPLICATE_PARTNER")
    shares = [item.explicit_percentage for item in rows]
    if any(share is None or share <= 0 for share in shares):
        issues.append("PARTNERSHIP_SHARE_NOT_POSITIVE")
    if sum((share or Decimal("0") for share in shares), Decimal("0")) != Decimal("100"):
        issues.append("PARTNERSHIP_SHARES_NOT_100")
    registry = {normalized_party_name(name) for name in registry_partners}
    if registry - set(names):
        issues.append("PARTNERSHIP_PARTNER_MISSING_FROM_AGREEMENT")
    if set(names) - registry:
        issues.append("PARTNERSHIP_EXTRA_PARTNER_IN_AGREEMENT")
    if declared is not None and Counter(
        (normalized_party_name(name), percent) for name, percent in declared
    ) != Counter(zip(names, shares, strict=True)):
        issues.append("PARTNERSHIP_DECLARATION_MISMATCH")
    return tuple(issues)
