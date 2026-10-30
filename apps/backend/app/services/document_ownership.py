"""Normalize proposed document observations against retained sources; no arithmetic."""

import re
from collections.abc import Sequence
from typing import Literal

from app.domain.documents import DocumentOwnershipObservation, DocumentProcessingRecord
from app.domain.ownership import (
    OwnershipDocumentBinding,
    OwnershipDocumentDiscrepancy,
    OwnershipRelationship,
    Party,
)
from app.domain.ownership_evidence import OwnershipEvidence


def current_document_inputs(
    documents: Sequence[DocumentProcessingRecord],
) -> tuple[tuple[DocumentOwnershipObservation, ...], tuple[OwnershipDocumentBinding, ...]]:
    current = sorted(
        (item for item in documents if item.is_current_evidence),
        key=lambda item: str(item.document_id),
    )
    if any(
        observation.document_id != item.document_id
        or observation.document_version != item.document_version
        for item in current
        for observation in item.ownership_observations
    ):
        raise ValueError(
            "ownership document observations must match their retained document version"
        )
    observations = tuple(
        observation for item in current for observation in item.ownership_observations
    )
    if len(observations) > 128 or len(current) > 32:
        raise ValueError("ownership document evidence exceeds safe limits")
    bindings = tuple(
        OwnershipDocumentBinding(document_id=item.document_id, event_count=len(item.events))
        for item in current
        if item.ownership_observations
    )
    return observations, bindings


_PARTNER_SHARE_ROW = "_PARTNER_SHARE_ROW_"


def _name(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", value.upper()).strip()


def normalized_party_name(value: str) -> str:
    """The existing document/registry name comparison, shared with D-101 checks."""
    return _name(value)


def compare_document_ownership(
    observations: tuple[DocumentOwnershipObservation, ...],
    parties: list[Party],
    relationships: list[OwnershipRelationship],
    evidence: tuple[OwnershipEvidence, ...],
) -> tuple[OwnershipDocumentDiscrepancy, ...]:
    """All proposals need creator verification, even when independently in agreement."""
    results: list[OwnershipDocumentDiscrepancy] = []
    for item in observations:
        owners = [
            party
            for party in parties
            if (
                party.registration_number == item.owner_registration_identifier
                if item.owner_registration_identifier
                else _name(party.display_name) == _name(item.owner_name)
            )
            and (item.owner_type is None or party.party_type.value == item.owner_type)
        ]
        parents = [
            party
            for party in parties
            if (
                party.registration_number == item.owned_entity_registration_identifier
                if item.owned_entity_registration_identifier
                else item.owned_entity_name is not None
                and _name(party.display_name) == _name(item.owned_entity_name)
            )
        ]
        edges = [
            edge
            for edge in relationships
            if len(owners) == 1
            and len(parents) == 1
            and edge.child_party_id == owners[0].party_id
            and edge.parent_party_id == parents[0].party_id
        ]
        agreement = "NOT_COMPARABLE"
        reason: Literal[
            "OWNERSHIP_PROPOSAL_REVIEW_REQUIRED",
            "OWNERSHIP_DOCUMENT_CONFLICT",
            "OWNERSHIP_DOCUMENT_INCOMPLETE",
            "OWNERSHIP_DOCUMENT_AMBIGUOUS",
            "PARTNERSHIP_AGREEMENT_SHARE",
        ] = "OWNERSHIP_DOCUMENT_INCOMPLETE"
        if (
            # D-101: a partnership registry lists partners without shares, so an agreement
            # share has no registry value to disagree with. It still needs RM confirmation.
            not relationships
            and _PARTNER_SHARE_ROW in item.source_reference
            and item.extraction_quality != "AMBIGUOUS"
        ):
            agreement, reason = "NOT_COMPARABLE", "PARTNERSHIP_AGREEMENT_SHARE"
        elif (
            item.extraction_quality == "AMBIGUOUS"
            or len(owners) > 1
            or len(parents) > 1
            or len(edges) > 1
        ):
            agreement, reason = "AMBIGUOUS", "OWNERSHIP_DOCUMENT_AMBIGUOUS"
        elif len(edges) == 1 and item.owner_type is not None:
            edge = edges[0]
            if item.explicit_percentage is not None:
                agreement = (
                    "MATCH" if edge.ownership_percent == item.explicit_percentage else "MISMATCH"
                )
            elif item.share_count is not None:
                # A row count is only compared to its original scalar. Never sum rows/divide here.
                units = [
                    scalar
                    for scalar in evidence
                    if scalar.kind == "SHARE_UNITS"
                    and scalar.party_id == edge.child_party_id
                    and scalar.entity_identifier == parents[0].registration_number
                    and scalar.share_class == item.share_class
                ]
                if len(units) == 1 and units[0].numeric_value is not None:
                    agreement = (
                        "MATCH" if units[0].numeric_value == item.share_count else "MISMATCH"
                    )
            if agreement == "MATCH":
                reason = "OWNERSHIP_PROPOSAL_REVIEW_REQUIRED"
            elif agreement == "MISMATCH":
                reason = "OWNERSHIP_DOCUMENT_CONFLICT"
        elif (
            not edges
            and item.owner_type is not None
            and item.explicit_percentage is not None
            and len(owners) == 1
            and len(parents) == 1
        ):
            agreement, reason = "MISMATCH", "OWNERSHIP_DOCUMENT_CONFLICT"
        results.append(
            OwnershipDocumentDiscrepancy(
                observation_id=item.observation_id,
                document_id=item.document_id,
                document_version=item.document_version,
                agreement=agreement,
                reason_code=reason,
                compared_relationship_ids=tuple(edge.relationship_id for edge in edges),
                current_percentage=edges[0].ownership_percent if len(edges) == 1 else None,
                proposed_percentage=item.explicit_percentage,
            )
        )
    return tuple(results)
