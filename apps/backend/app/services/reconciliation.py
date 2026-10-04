"""Deterministic Phase 11 reconciliation and backend-authorized decisions."""

import hmac
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from app.domain.documents import (
    DocumentFieldKey,
    DocumentProcessingRecord,
    FieldReviewStatus,
)
from app.domain.models import CanonicalLegalEntity, OnboardingCase
from app.domain.reconciliation import (
    NON_BLOCKING_RECONCILIATION_OUTCOMES,
    DiscrepancyStatus,
    FieldReconciliationResult,
    ObservationValidity,
    ReconciliationCaseRecord,
    ReconciliationDecision,
    ReconciliationDecisionAction,
    ReconciliationDiscrepancy,
    ReconciliationField,
    ReconciliationObservation,
    ReconciliationSourceKind,
    ReconciliationStatus,
    derive_allowed_actions,
    derive_reconciliation_outcome,
)
from app.services.document_processing import (
    DocumentProcessingService,
    canonical_value_for_field,
    normalize_document_value,
    required_document_fields,
)
from app.services.onboarding import OnboardingService
from app.services.reconciliation_errors import (
    ReconciliationInfrastructureError,
    ReconciliationRequestError,
)
from app.services.reconciliation_repository import (
    ProcessLocalReconciliationUnitOfWork,
    ReconciliationRepository,
    ReconciliationRepositoryConflictError,
    ReconciliationUnitOfWork,
    ReconciliationUnitOfWorkError,
)

COUNTRY_CODE = re.compile(r"^[A-Z]{2,3}$")
REGISTRATION_IDENTIFIER = re.compile(r"^[A-Z0-9-]{1,32}$")

FIELD_TO_DOCUMENT = {
    ReconciliationField.LEGAL_NAME: DocumentFieldKey.LEGAL_NAME,
    ReconciliationField.REGISTRATION_IDENTIFIER: DocumentFieldKey.REGISTRATION_NUMBER,
    ReconciliationField.REGISTERED_ADDRESS: DocumentFieldKey.REGISTERED_ADDRESS,
    ReconciliationField.COUNTRY_OF_INCORPORATION: (DocumentFieldKey.COUNTRY_OF_INCORPORATION),
}


class ReconciliationService:
    """Own one source-neutral current reconciliation aggregate per case."""

    def __init__(
        self,
        *,
        cases: OnboardingService,
        documents: DocumentProcessingService,
        repository: ReconciliationRepository,
        unit_of_work: ReconciliationUnitOfWork | None = None,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self._cases = cases
        self._documents = documents
        self._repository = repository
        self._unit_of_work = unit_of_work or ProcessLocalReconciliationUnitOfWork(
            onboarding_repository=cases.repository,
            reconciliation_repository=repository,
        )
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4

    def get(self, *, case_id: UUID) -> ReconciliationCaseRecord | None:
        return self._repository.get_for_case(case_id)

    def reconcile_current(self, *, case_id: UUID) -> ReconciliationCaseRecord:
        """Evaluate current retained evidence once; unchanged reads never invoke providers."""

        with self._cases.case_lock(case_id):
            case, documents = self._current_evidence(case_id)
            fingerprint = self._evidence_fingerprint(case, documents)
            current = self._repository.get_for_case(case_id)
            if current is not None and hmac.compare_digest(
                current.evidence_fingerprint, fingerprint
            ):
                return current
            try:
                fields, discrepancies = self._compare(case, documents)
                now = self._clock()
                retained = []
                created_at = now
                reconciliation_id = self._uuid_factory()
                if current is not None:
                    created_at = current.created_at
                    reconciliation_id = current.reconciliation_id
                    retained = [item.model_copy(deep=True) for item in current.discrepancies]
                    for item in retained:
                        if item.status == DiscrepancyStatus.OPEN:
                            item.status = DiscrepancyStatus.CANCELLED
                    retained.extend(discrepancies)
                else:
                    retained = list(discrepancies)
                status = (
                    ReconciliationStatus.MATCHED
                    if all(
                        item.outcome in NON_BLOCKING_RECONCILIATION_OUTCOMES
                        for item in fields
                    )
                    else ReconciliationStatus.REVIEW_REQUIRED
                )
                candidate = ReconciliationCaseRecord(
                    case_id=case_id,
                    reconciliation_id=reconciliation_id,
                    status=status,
                    source_document_ids=tuple(item.document_id for item in documents),
                    source_document_event_counts=tuple(len(item.events) for item in documents),
                    evidence_fingerprint=fingerprint,
                    fields=fields,
                    discrepancies=retained,
                    created_at=created_at,
                    updated_at=now,
                )
                return self._repository.save(
                    candidate,
                    expected_version=current.version if current is not None else None,
                )
            except ReconciliationRepositoryConflictError:
                raise ReconciliationRequestError(
                    code="RECONCILIATION_CONFLICT",
                    message="Reconciliation evidence changed during this operation.",
                ) from None
            except ReconciliationRequestError:
                raise
            except Exception:
                raise ReconciliationInfrastructureError(
                    code="RECONCILIATION_PROCESSING_FAILED",
                    message="Current evidence could not be reconciled safely.",
                ) from None

    def resolve_discrepancy(
        self,
        *,
        case_id: UUID,
        discrepancy_id: UUID,
        action: ReconciliationDecisionAction,
        expected_version: int,
        evidence_fingerprint: str,
    ) -> ReconciliationCaseRecord:
        """Resolve exactly one discrepancy, preserving every source observation."""

        with self._cases.case_lock(case_id):
            record = self._repository.get_for_case(case_id)
            if record is None:
                raise ReconciliationRequestError(
                    code="RECONCILIATION_NOT_FOUND",
                    message="Reconciliation evidence was not found for this case.",
                )
            case, documents = self._current_evidence(case_id)
            current_fingerprint = self._evidence_fingerprint(case, documents)
            current_document_ids = tuple(item.document_id for item in documents)
            current_document_versions = tuple(len(item.events) for item in documents)
            existing = next(
                (item for item in record.discrepancies if item.discrepancy_id == discrepancy_id),
                None,
            )
            current_discrepancy_ids = {
                item.discrepancy_id for item in record.fields if item.discrepancy_id is not None
            }
            if (
                existing is not None
                and existing.status == DiscrepancyStatus.RESOLVED
                and existing.decision is not None
            ):
                if (
                    existing.discrepancy_id in current_discrepancy_ids
                    and existing.decision.reconciliation_version == expected_version
                    and existing.decision.action == action
                    and hmac.compare_digest(existing.evidence_fingerprint, evidence_fingerprint)
                    and hmac.compare_digest(record.evidence_fingerprint, current_fingerprint)
                    and record.source_document_ids == current_document_ids
                    and record.source_document_event_counts == current_document_versions
                ):
                    return record
                raise ReconciliationRequestError(
                    code="RECONCILIATION_STALE",
                    message="The previous decision no longer matches current evidence.",
                )
            if record.version != expected_version:
                raise ReconciliationRequestError(
                    code="RECONCILIATION_STALE",
                    message="Reconciliation changed before this decision.",
                )
            if (
                existing is None
                or existing.status != DiscrepancyStatus.OPEN
                or existing.discrepancy_id not in current_discrepancy_ids
            ):
                raise ReconciliationRequestError(
                    code="RECONCILIATION_DISCREPANCY_NOT_FOUND",
                    message="The active reconciliation discrepancy was not found.",
                )
            if not hmac.compare_digest(existing.evidence_fingerprint, evidence_fingerprint):
                raise ReconciliationRequestError(
                    code="RECONCILIATION_STALE",
                    message="Reconciliation evidence changed before this decision.",
                )
            if (
                not hmac.compare_digest(record.evidence_fingerprint, current_fingerprint)
                or record.source_document_ids != current_document_ids
                or record.source_document_event_counts != current_document_versions
            ):
                raise ReconciliationRequestError(
                    code="RECONCILIATION_STALE",
                    message="Authoritative case or source evidence changed before this decision.",
                )
            if action not in existing.allowed_actions:
                raise ReconciliationRequestError(
                    code="RECONCILIATION_ACTION_NOT_ALLOWED",
                    message="This action is not authorized for the active discrepancy.",
                )
            selected_source = (
                ReconciliationSourceKind.REGISTRY
                if action == ReconciliationDecisionAction.KEEP_REGISTRY_VALUE
                else ReconciliationSourceKind.DOCUMENT_IDP
            )
            selected = self._select_observation(existing, selected_source)
            if selected is None or selected.normalized_value is None:
                raise ReconciliationRequestError(
                    code="RECONCILIATION_ACTION_NOT_ALLOWED",
                    message="The selected source has no usable value for this discrepancy.",
                )
            now = self._clock()
            candidate = record.model_copy(deep=True)
            target = next(
                item for item in candidate.discrepancies if item.discrepancy_id == discrepancy_id
            )
            target.status = DiscrepancyStatus.RESOLVED
            target.decision = ReconciliationDecision(
                action=action,
                selected_observation_id=selected.observation_id,
                selected_value=selected.normalized_value,
                decided_at=now,
                reconciliation_version=record.version,
                evidence_fingerprint=target.evidence_fingerprint,
            )
            expected_entity_fingerprint = self._cases.canonical_entity_fingerprint(case_id)
            expected_onboarding_fingerprint = sha256(
                case.model_dump_json().encode("utf-8")
            ).hexdigest()
            onboarding_candidate = None
            if action == ReconciliationDecisionAction.USE_DOCUMENT_VALUE:
                try:
                    onboarding_candidate = self._cases.prepare_reconciled_value(
                        case_id=case_id,
                        field_name=existing.field_name,
                        selected_value=selected.raw_value or selected.normalized_value,
                        expected_entity_fingerprint=expected_entity_fingerprint,
                    )
                except ValueError:
                    raise ReconciliationRequestError(
                        code="RECONCILIATION_CANONICAL_UPDATE_REJECTED",
                        message="The selected document value cannot safely update canonical data.",
                    ) from None
                candidate.evidence_fingerprint = self._evidence_fingerprint(
                    onboarding_candidate, documents
                )
                for item in candidate.open_discrepancies:
                    item.evidence_fingerprint = self._discrepancy_fingerprint(
                        candidate.evidence_fingerprint, item.field_name, item.observations
                    )
            candidate.status = (
                ReconciliationStatus.REVIEW_REQUIRED
                if candidate.open_discrepancies
                else ReconciliationStatus.RESOLVED
            )
            candidate.updated_at = now
            try:
                validated_candidate = self._validate_resolution_candidate(candidate)
            except Exception:
                raise ReconciliationInfrastructureError(
                    code="RECONCILIATION_DECISION_INVALID",
                    message="The proposed decision could not be validated safely.",
                ) from None
            try:
                return self._unit_of_work.commit_resolution(
                    onboarding_candidate=onboarding_candidate,
                    reconciliation_candidate=validated_candidate,
                    expected_reconciliation_version=record.version,
                    expected_onboarding_fingerprint=expected_onboarding_fingerprint,
                    expected_entity_fingerprint=expected_entity_fingerprint,
                )
            except ReconciliationRepositoryConflictError:
                raise ReconciliationRequestError(
                    code="RECONCILIATION_CONFLICT",
                    message="Reconciliation changed during this decision.",
                ) from None
            except ReconciliationUnitOfWorkError:
                raise ReconciliationInfrastructureError(
                    code="RECONCILIATION_COMMIT_FAILED",
                    message="The decision and canonical value were not committed.",
                ) from None

    @staticmethod
    def _validate_resolution_candidate(
        candidate: ReconciliationCaseRecord,
    ) -> ReconciliationCaseRecord:
        return ReconciliationCaseRecord.model_validate(candidate)

    def is_currently_cleared(self, *, case_id: UUID) -> bool:
        """Return true only for fresh MATCHED/RESOLVED current evidence."""

        record = self._repository.get_for_case(case_id)
        if record is None or not record.semantically_cleared:
            return False
        try:
            case, documents = self._current_evidence(case_id)
        except ReconciliationRequestError:
            return False
        return hmac.compare_digest(
            record.evidence_fingerprint, self._evidence_fingerprint(case, documents)
        ) and all(
            item.document_required
            == self._document_field_required(documents, item.field_name)
            for item in record.fields
        )

    def resolved_document_checkpoint(
        self, *, case_id: UUID, document_id: UUID, event_count: int
    ) -> ReconciliationCaseRecord | None:
        """Read an exact resolved checkpoint without changing source review evidence."""
        record = self.get(case_id=case_id)
        if (
            record is None
            or record.case_id != case_id
            or record.status != ReconciliationStatus.RESOLVED
            or (document_id, event_count)
            not in tuple(
                zip(record.source_document_ids, record.source_document_event_counts, strict=True)
            )
            or not self.is_currently_cleared(case_id=case_id)
        ):
            return None
        return record

    def _current_evidence(
        self, case_id: UUID
    ) -> tuple[OnboardingCase, list[DocumentProcessingRecord]]:
        case = self._cases.get_case(case_id)
        if (
            case is None
            or case.entity is None
            or (case.registry_acquisition is None and case.existing_target_state is None)
        ):
            raise ReconciliationRequestError(
                code="RECONCILIATION_CASE_NOT_READY",
                message="Registry evidence is not ready for reconciliation.",
            )
        documents = [
            item
            for item in self._documents.list_documents(case_id=case_id)
            if item.is_current_evidence
        ]
        if not documents:
            raise ReconciliationRequestError(
                code="RECONCILIATION_DOCUMENT_REQUIRED",
                message="Current document evidence is required for reconciliation.",
            )
        return case, documents

    def _compare(
        self, case: OnboardingCase, documents: list[DocumentProcessingRecord]
    ) -> tuple[tuple[FieldReconciliationResult, ...], tuple[ReconciliationDiscrepancy, ...]]:
        results: list[FieldReconciliationResult] = []
        discrepancies: list[ReconciliationDiscrepancy] = []
        base_fingerprint = self._evidence_fingerprint(case, documents)
        baseline_entity = (
            case.registry_acquisition.entity_profile
            if case.registry_acquisition is not None
            else case.entity
        )
        if baseline_entity is None:
            raise ValueError("canonical reconciliation baseline is unavailable")
        for field_name in ReconciliationField:
            document_required = self._document_field_required(documents, field_name)
            observations = self._observations_for_field(
                case=case,
                baseline_entity=baseline_entity,
                documents=documents,
                field_name=field_name,
            )
            outcome = derive_reconciliation_outcome(
                field_name,
                observations,
                document_required=document_required,
            )
            discrepancy_id = None
            if outcome not in NON_BLOCKING_RECONCILIATION_OUTCOMES:
                discrepancy_id = self._uuid_factory()
                discrepancies.append(
                    ReconciliationDiscrepancy(
                        discrepancy_id=discrepancy_id,
                        field_name=field_name,
                        outcome=outcome,
                        observations=observations,
                        created_at=self._clock(),
                        allowed_actions=derive_allowed_actions(field_name, outcome, observations),
                        evidence_fingerprint=self._discrepancy_fingerprint(
                            base_fingerprint, field_name, observations
                        ),
                    )
                )
            results.append(
                FieldReconciliationResult(
                    field_name=field_name,
                    observations=observations,
                    outcome=outcome,
                    document_required=document_required,
                    discrepancy_id=discrepancy_id,
                )
            )
        return tuple(results), tuple(discrepancies)

    @staticmethod
    def _document_field_required(
        documents: list[DocumentProcessingRecord], field_name: ReconciliationField
    ) -> bool:
        document_key = FIELD_TO_DOCUMENT[field_name]
        return any(
            document_key in required_document_fields(document.profile)
            for document in documents
        )

    def _observations_for_field(
        self,
        *,
        case: OnboardingCase,
        baseline_entity: CanonicalLegalEntity,
        documents: list[DocumentProcessingRecord],
        field_name: ReconciliationField,
    ) -> tuple[ReconciliationObservation, ...]:
        document_key = FIELD_TO_DOCUMENT[field_name]
        confidence_threshold = float(case.policy_snapshot.idp_review_confidence_threshold)
        if case.registry_acquisition is not None:
            operation = case.registry_acquisition.operation_results[0]
            provenance = operation.provenance
            if provenance is None:
                raise ValueError("registry entity provenance is unavailable")
            baseline_source_kind = ReconciliationSourceKind.REGISTRY
            baseline_source_system = provenance.provider.value
            baseline_environment: str | None = provenance.environment.value
            baseline_observed_at = provenance.retrieved_at
            baseline_evidence_reference = provenance.evidence_reference
        elif case.existing_target_state is not None:
            baseline_source_kind = ReconciliationSourceKind.EXISTING_CASE
            baseline_source_system = "EXISTING_VERIFIED_TARGET_CASE"
            baseline_environment = None
            baseline_observed_at = case.existing_target_state.verified_at
            baseline_evidence_reference = (
                f"case:{case.existing_target_state.source_case_id}:"
                f"target:{case.existing_target_state.target_party_id}"
            )
        else:
            raise ValueError("canonical reconciliation baseline is unavailable")
        baseline_value = canonical_value_for_field(baseline_entity, document_key)
        registry_normalized, registry_validity = self._normalize(
            field_name,
            baseline_value,
            confidence=None,
            unavailable=False,
            confidence_threshold=confidence_threshold,
        )
        observations: list[ReconciliationObservation] = []
        if field_name == ReconciliationField.REGISTRATION_IDENTIFIER:
            user_normalized, user_validity = self._normalize(
                field_name,
                case.requested_uen,
                confidence=None,
                unavailable=False,
                confidence_threshold=confidence_threshold,
            )
            observations.append(
                ReconciliationObservation(
                    observation_id=self._uuid_factory(),
                    field_name=field_name,
                    raw_value=case.requested_uen,
                    normalized_value=user_normalized,
                    source_kind=ReconciliationSourceKind.USER_INPUT,
                    source_system="ONBOARDING_REQUEST",
                    observed_at=case.created_at,
                    evidence_reference="request.registration_identifier",
                    validity=user_validity,
                )
            )
        observations.append(
            ReconciliationObservation(
                observation_id=self._uuid_factory(),
                field_name=field_name,
                raw_value=baseline_value,
                normalized_value=registry_normalized,
                source_kind=baseline_source_kind,
                source_system=baseline_source_system,
                environment=baseline_environment,
                observed_at=baseline_observed_at,
                evidence_reference=baseline_evidence_reference,
                validity=registry_validity,
            )
        )
        for document in documents:
            field = next(item for item in document.fields if item.field_key == document_key)
            unavailable = field.provenance.source_reference == "DOCUMENT_TEXT_UNAVAILABLE"
            original_normalized, original_validity = self._normalize(
                field_name,
                field.original_extracted_value,
                confidence=field.confidence,
                unavailable=unavailable,
                confidence_threshold=confidence_threshold,
            )
            raw_value = field.original_extracted_value
            normalized = original_normalized
            validity = original_validity
            source_system = field.provenance.provider
            environment: str | None = field.provenance.environment.value
            observed_at = document.processed_at or document.updated_at
            evidence_reference = field.provenance.source_reference
            if field.extraction_quality == "AMBIGUOUS":
                validity = ObservationValidity.AMBIGUOUS
                evidence_reference = "DOCUMENT_AMBIGUOUS_EXTRACTION"
            confidence: float | None = field.confidence
            if field.review_status == FieldReviewStatus.REJECTED:
                raw_value = normalized = None
                validity = ObservationValidity.MISSING
                source_system = "HUMAN_REVIEW"
                environment = None
                observed_at = field.reviewed_at or document.updated_at
                evidence_reference = "DOCUMENT_REVIEW_REJECTED"
                confidence = None
            elif field.review_status == FieldReviewStatus.CORRECTED:
                if original_validity == ObservationValidity.VALID:
                    raw_value = field.reviewed_value
                    normalized, validity = self._normalize(
                        field_name,
                        raw_value,
                        confidence=None,
                        unavailable=False,
                        confidence_threshold=confidence_threshold,
                    )
                    source_system = "HUMAN_REVIEW"
                    environment = None
                    observed_at = field.reviewed_at or document.updated_at
                    evidence_reference = "DOCUMENT_REVIEW_CORRECTION"
                    confidence = None
            observations.append(
                ReconciliationObservation(
                    observation_id=self._uuid_factory(),
                    field_name=field_name,
                    raw_value=raw_value,
                    normalized_value=normalized,
                    source_kind=ReconciliationSourceKind.DOCUMENT_IDP,
                    source_system=source_system,
                    environment=environment,
                    observed_at=observed_at,
                    evidence_reference=evidence_reference,
                    source_record_id=document.document_id,
                    source_display_name=document.display_name,
                    confidence=confidence,
                    validity=validity,
                )
            )
        return tuple(observations)

    def _normalize(
        self,
        field_name: ReconciliationField,
        value: str | None,
        *,
        confidence: float | None,
        unavailable: bool,
        confidence_threshold: float,
    ) -> tuple[str | None, ObservationValidity]:
        if value is None:
            return None, ObservationValidity.MISSING
        normalized = normalize_document_value(FIELD_TO_DOCUMENT[field_name], value)
        if normalized is None:
            return None, ObservationValidity.INVALID
        if field_name == ReconciliationField.REGISTRATION_IDENTIFIER and not (
            REGISTRATION_IDENTIFIER.fullmatch(normalized)
        ):
            return normalized, ObservationValidity.INVALID
        if field_name == ReconciliationField.COUNTRY_OF_INCORPORATION and not (
            COUNTRY_CODE.fullmatch(normalized)
        ):
            return normalized, ObservationValidity.INVALID
        if unavailable or (confidence is not None and confidence < confidence_threshold):
            return normalized, ObservationValidity.UNVERIFIABLE
        return normalized, ObservationValidity.VALID

    @staticmethod
    def _select_observation(
        discrepancy: ReconciliationDiscrepancy,
        source: ReconciliationSourceKind,
    ) -> ReconciliationObservation | None:
        candidates = [
            item
            for item in discrepancy.observations
            if item.source_kind == source and item.validity == ObservationValidity.VALID
        ]
        values = {item.normalized_value for item in candidates}
        return candidates[0] if candidates and len(values) == 1 else None

    @staticmethod
    def _evidence_fingerprint(
        case: OnboardingCase, documents: list[DocumentProcessingRecord]
    ) -> str:
        payload = {
            "domain": "phase-15b-reconciliation-evidence-v4",
            "case_id": str(case.case_id),
            "requested_identifier": case.requested_uen,
            "current_canonical": (
                case.entity.model_dump(mode="json") if case.entity is not None else None
            ),
            "registry": (
                case.registry_acquisition.model_dump(mode="json")
                if case.registry_acquisition is not None
                else None
            ),
            "existing_target_state": (
                case.existing_target_state.model_dump(mode="json")
                if case.existing_target_state is not None
                else None
            ),
            "documents": [item.model_dump(mode="json") for item in documents],
        }
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        return sha256(encoded).hexdigest()

    @staticmethod
    def _discrepancy_fingerprint(
        case_fingerprint: str,
        field_name: ReconciliationField,
        observations: tuple[ReconciliationObservation, ...],
    ) -> str:
        payload = {
            "case_fingerprint": case_fingerprint,
            "field": field_name.value,
            "observations": [item.model_dump(mode="json") for item in observations],
        }
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
                "utf-8"
            )
        ).hexdigest()
