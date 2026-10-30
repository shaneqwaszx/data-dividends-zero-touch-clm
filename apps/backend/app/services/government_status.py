"""D-101 Singapore Government status evidence, replacing the ownership/UBO step.

MAS Notice 626 para 6.12: for a Singapore Government entity the bank needs only
information confirming it is one. The requirement is met only by one current reviewed
document carrying every labelled field plus an explicit RM confirmation bound to that
exact document version. Nothing here sets the status automatically or from a label.
Project-defined, not sponsor-confirmed. A foreign government body is out of scope.
"""

import hashlib
import json
from dataclasses import dataclass
from uuid import UUID

from app.domain.documents import (
    DocumentProcessingRecord,
    DocumentProcessingState,
    ExtractionQuality,
)
from app.domain.models import OnboardingCase
from app.domain.registry_legal_form import RegistryLegalForm, classify_registry_legal_form
from app.domain.target_classification import TargetClassificationKey
from app.services.document_processing import document_semantic_assessment

GOVERNMENT_KYC_CUSTOMER_TYPE = "Government"
GOVERNMENT_CLIENT_SEGMENT = "DI - Government"


@dataclass(frozen=True)
class GovernmentStatusEvidence:
    document_id: UUID
    document_event_count: int
    founding_instrument: str
    evidence_fingerprint: str


def government_profile_applies(case: OnboardingCase) -> bool:
    """The KYC type is Government and the registry legal form is exactly GOVERNMENT."""
    target = case.policy_snapshot.goldtier_target
    return (
        case.entity is not None
        and classify_registry_legal_form(case.entity.party_type) == RegistryLegalForm.GOVERNMENT
        and target is not None
        and target.kyc_customer_type.value == GOVERNMENT_KYC_CUSTOMER_TYPE
    )


def government_status_evidence(
    case: OnboardingCase,
    documents: list[DocumentProcessingRecord],
    *,
    confidence_threshold: float,
) -> GovernmentStatusEvidence | None:
    """The single current reviewed document carrying every Government-status label."""

    def trusted(item: object) -> bool:
        return (
            getattr(item, "extraction_quality", None) == ExtractionQuality.HIGH
            and float(getattr(item, "evidence_score", 0.0)) >= confidence_threshold
        )

    found: list[GovernmentStatusEvidence] = []
    for document in documents:
        if (
            not document.is_current_evidence
            or document.state != DocumentProcessingState.REVIEWED
            or document_semantic_assessment(
                record=document,
                current_entity=case.entity,
                confidence_threshold=confidence_threshold,
            ).blockers
        ):
            continue
        labels = {
            (item.field_key.value, item.value)
            for item in document.classification_observations
            if trusted(item)
        }
        instruments = {
            item.value for item in document.government_status_observations if trusted(item)
        }
        if (
            len(instruments) != 1
            or (TargetClassificationKey.KYC_CUSTOMER_TYPE.value, GOVERNMENT_KYC_CUSTOMER_TYPE)
            not in labels
            or (TargetClassificationKey.CLIENT_SEGMENT.value, GOVERNMENT_CLIENT_SEGMENT)
            not in labels
            or len(labels) != 2
        ):
            continue
        instrument = next(iter(instruments))
        payload = {
            "document_id": str(document.document_id),
            "document_event_count": len(document.events),
            "founding_instrument": instrument,
            "kyc_customer_type": GOVERNMENT_KYC_CUSTOMER_TYPE,
            "client_segment": GOVERNMENT_CLIENT_SEGMENT,
            "legal_name": case.entity.legal_name if case.entity is not None else None,
            "registration_number": (
                case.entity.registration_number if case.entity is not None else None
            ),
        }
        found.append(
            GovernmentStatusEvidence(
                document_id=document.document_id,
                document_event_count=len(document.events),
                founding_instrument=instrument,
                evidence_fingerprint=hashlib.sha256(
                    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest(),
            )
        )
    return found[0] if len(found) == 1 else None


def government_status_confirmed(
    case: OnboardingCase,
    documents: list[DocumentProcessingRecord],
    *,
    confidence_threshold: float,
) -> bool:
    """An RM confirmation that is still bound to the current evidence."""
    confirmation = case.government_status_confirmation
    evidence = government_status_evidence(
        case, documents, confidence_threshold=confidence_threshold
    )
    return (
        confirmation is not None
        and evidence is not None
        and confirmation.document_id == evidence.document_id
        and confirmation.document_event_count == evidence.document_event_count
        and confirmation.evidence_fingerprint == evidence.evidence_fingerprint
    )
