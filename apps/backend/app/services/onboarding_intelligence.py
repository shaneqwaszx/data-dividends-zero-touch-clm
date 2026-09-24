"""Deterministic explainable advisory scoring over canonical onboarding evidence."""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from difflib import SequenceMatcher
from hashlib import sha256
from uuid import UUID

from app.domain.documents import DocumentProcessingState
from app.domain.onboarding_intelligence import (
    EntityCandidateEvidence,
    EntityIdentity,
    EntityResolutionOutcome,
    EntityResolutionResult,
    FeatureAssessment,
    MockRiskAssessment,
    MockRiskBand,
    MockRiskInputs,
    MockRiskLimitationName,
    MockRiskSignalName,
    OnboardingIntelligenceRecord,
    ResolutionFeatureEvidence,
    ResolutionFeatureName,
    UboAdviceLabel,
    UboAdviceResult,
)
from app.domain.ownership import (
    OwnershipCandidate,
    OwnershipCandidateClassification,
    OwnershipThresholdResult,
)
from app.domain.policy import IntelligencePolicySnapshot, legacy_intelligence_policy_snapshot
from app.services.document_repository import DocumentProcessingRepository
from app.services.onboarding import OnboardingService
from app.services.onboarding_intelligence_repository import OnboardingIntelligenceRepository
from app.services.ownership_repository import OwnershipAnalysisRepository

_SIX_PLACES = Decimal("0.000001")
_EXTERNAL_UNAVAILABLE_RISK_SIGNALS: frozenset[MockRiskLimitationName] = frozenset(
    {"pep", "sanctions", "adverse_media", "transaction_monitoring", "product_channel"}
)


def _six(value: Decimal) -> Decimal:
    return value.quantize(_SIX_PLACES, rounding=ROUND_HALF_UP)


def _normalized_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(
        "".join(character if character.isalnum() else " " for character in normalized).split()
    )


def _normalized_identifier(value: str) -> str | None:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    retained = "".join(character for character in normalized if character.isalnum())
    return retained or None


def _similarity(left: str, right: str) -> Decimal:
    normalized_left = _normalized_text(left)
    normalized_right = _normalized_text(right)
    if not normalized_left or not normalized_right:
        return Decimal("0")
    ratio = SequenceMatcher(None, normalized_left, normalized_right).ratio()
    return _six(Decimal(str(ratio)))


class OnboardingIntelligenceService:
    """Owns advisory feature extraction and scoring, never authoritative decisions."""

    def resolve_entity(
        self,
        *,
        source: EntityIdentity,
        candidates: tuple[EntityIdentity, ...],
        policy: IntelligencePolicySnapshot | None = None,
    ) -> EntityResolutionResult:
        active_policy = policy or legacy_intelligence_policy_snapshot()
        probable_threshold = active_policy.entity_resolution_auto_match_threshold
        review_threshold = active_policy.entity_resolution_review_threshold
        ambiguity_margin = active_policy.entity_resolution_ambiguity_margin
        evidence = tuple(
            self._candidate_evidence(source, candidate, active_policy) for candidate in candidates
        )
        ranked = tuple(
            sorted(evidence, key=lambda item: (-item.probability, item.candidate_id))
        )
        if not ranked:
            return EntityResolutionResult(
                outcome=EntityResolutionOutcome.NO_MATCH,
                source_reference=source.source_reference,
                candidates=(),
                reason_codes=("NO_CANDIDATES",),
            )

        conflicts = tuple(
            item for item in ranked if item.features[0].assessment == FeatureAssessment.CONFLICT
        )
        if conflicts:
            return EntityResolutionResult(
                outcome=EntityResolutionOutcome.CONFLICT,
                source_reference=source.source_reference,
                candidates=ranked,
                reason_codes=("IDENTIFIER_COUNTRY_CONFLICT",),
            )

        exact = tuple(
            item
            for item in ranked
            if item.features[0].assessment == FeatureAssessment.ASSESSED
            and item.features[0].agreement == Decimal("1")
        )
        if len(exact) == 1:
            return EntityResolutionResult(
                outcome=EntityResolutionOutcome.EXACT_MATCH,
                selected_candidate_id=exact[0].candidate_id,
                source_reference=source.source_reference,
                candidates=ranked,
                reason_codes=("EXACT_IDENTIFIER_AND_COUNTRY",),
            )
        if len(exact) > 1:
            return EntityResolutionResult(
                outcome=EntityResolutionOutcome.CONFLICT,
                source_reference=source.source_reference,
                candidates=ranked,
                reason_codes=("DUPLICATE_EXACT_IDENTITIES",),
            )

        top = ranked[0]
        if len(ranked) > 1 and top.probability >= review_threshold:
            second = ranked[1]
            if top.probability - second.probability <= ambiguity_margin:
                return EntityResolutionResult(
                    outcome=EntityResolutionOutcome.REVIEW_REQUIRED,
                    source_reference=source.source_reference,
                    candidates=ranked,
                    reason_codes=("AMBIGUOUS_TOP_CANDIDATES",),
                )

        identifier_disagrees = (
            top.features[0].assessment == FeatureAssessment.ASSESSED
            and top.features[0].agreement == Decimal("0")
        )
        if (
            top.probability >= probable_threshold
            and top.corroborating_feature_count >= 2
            and not identifier_disagrees
        ):
            return EntityResolutionResult(
                outcome=EntityResolutionOutcome.PROBABLE_MATCH,
                selected_candidate_id=top.candidate_id,
                source_reference=source.source_reference,
                candidates=ranked,
                reason_codes=("WEIGHTED_EVIDENCE_ABOVE_THRESHOLD",),
            )
        if top.probability >= review_threshold:
            code = (
                "INSUFFICIENT_CORROBORATION"
                if top.corroborating_feature_count < 2
                else "IDENTIFIER_DISAGREEMENT_REQUIRES_REVIEW"
                if identifier_disagrees
                else "WEIGHTED_EVIDENCE_REQUIRES_REVIEW"
            )
            return EntityResolutionResult(
                outcome=EntityResolutionOutcome.REVIEW_REQUIRED,
                source_reference=source.source_reference,
                candidates=ranked,
                reason_codes=(code,),
            )
        return EntityResolutionResult(
            outcome=EntityResolutionOutcome.NO_MATCH,
            source_reference=source.source_reference,
            candidates=ranked,
            reason_codes=("WEIGHTED_EVIDENCE_BELOW_THRESHOLD",),
        )

    def _candidate_evidence(
        self,
        source: EntityIdentity,
        candidate: EntityIdentity,
        policy: IntelligencePolicySnapshot,
    ) -> EntityCandidateEvidence:
        weights = {
            ResolutionFeatureName.REGISTRATION_NUMBER_AND_COUNTRY: (
                policy.entity_resolution_weights.identifier
            ),
            ResolutionFeatureName.LEGAL_NAME_SIMILARITY: policy.entity_resolution_weights.name,
            ResolutionFeatureName.REGISTERED_ADDRESS_SIMILARITY: (
                policy.entity_resolution_weights.address
            ),
            ResolutionFeatureName.LEGAL_FORM_AGREEMENT: (
                policy.entity_resolution_weights.legal_form
            ),
            ResolutionFeatureName.INCORPORATION_DATE_AGREEMENT: (
                policy.entity_resolution_weights.incorporation_date
            ),
        }
        identifier_feature = self._identifier_feature(source, candidate, weights)
        features = (
            identifier_feature,
            self._text_feature(
                ResolutionFeatureName.LEGAL_NAME_SIMILARITY,
                source.legal_name,
                candidate.legal_name,
                weights,
            ),
            self._text_feature(
                ResolutionFeatureName.REGISTERED_ADDRESS_SIMILARITY,
                source.registered_address,
                candidate.registered_address,
                weights,
            ),
            self._exact_feature(
                ResolutionFeatureName.LEGAL_FORM_AGREEMENT,
                source.legal_form,
                candidate.legal_form,
                weights,
            ),
            self._exact_feature(
                ResolutionFeatureName.INCORPORATION_DATE_AGREEMENT,
                source.incorporated_on.isoformat() if source.incorporated_on else None,
                candidate.incorporated_on.isoformat() if candidate.incorporated_on else None,
                weights,
            ),
        )
        assessed = tuple(
            item
            for item in features
            if item.assessment == FeatureAssessment.ASSESSED and item.agreement is not None
        )
        assessed_weight = sum((item.weight for item in assessed), Decimal("0"))
        weighted = sum(
            (item.weight * item.agreement for item in assessed if item.agreement is not None),
            Decimal("0"),
        )
        probability = _six(weighted / assessed_weight) if assessed_weight else Decimal("0")
        corroborating = len(
            tuple(
                item
                for item in assessed
                if item.name != ResolutionFeatureName.LEGAL_FORM_AGREEMENT
                and item.agreement is not None
                and item.agreement >= Decimal("0.80")
            )
        )
        contributions = tuple(
            item.name
            for item in sorted(
                assessed,
                key=lambda item: (
                    -(item.weight * (item.agreement or Decimal("0"))),
                    item.name.value,
                ),
            )[:3]
        )
        return EntityCandidateEvidence(
            candidate_id=candidate.candidate_id,
            probability=probability,
            assessed_weight=_six(assessed_weight),
            corroborating_feature_count=corroborating,
            features=features,
            top_contributing_features=contributions,
            source_reference=candidate.source_reference,
        )

    @staticmethod
    def _identifier_feature(
        source: EntityIdentity,
        candidate: EntityIdentity,
        weights: dict[ResolutionFeatureName, Decimal],
    ) -> ResolutionFeatureEvidence:
        name = ResolutionFeatureName.REGISTRATION_NUMBER_AND_COUNTRY
        weight = weights[name]
        source_identifier = (
            _normalized_identifier(source.registration_number)
            if source.registration_number
            else None
        )
        candidate_identifier = (
            _normalized_identifier(candidate.registration_number)
            if candidate.registration_number
            else None
        )
        if (
            source.country
            and candidate.country
            and source.country.upper() != candidate.country.upper()
        ):
            return ResolutionFeatureEvidence(
                name=name,
                assessment=FeatureAssessment.CONFLICT,
                agreement=Decimal("0"),
                weight=weight,
            )
        if (
            source_identifier is not None
            and candidate_identifier is not None
            and source_identifier != candidate_identifier
        ):
            return ResolutionFeatureEvidence(
                name=name,
                assessment=FeatureAssessment.ASSESSED,
                agreement=Decimal("0"),
                weight=weight,
            )
        if not source.country or not candidate.country:
            return ResolutionFeatureEvidence(
                name=name,
                assessment=FeatureAssessment.NOT_ASSESSED,
                agreement=None,
                weight=weight,
            )
        if source_identifier is None or candidate_identifier is None:
            return ResolutionFeatureEvidence(
                name=name,
                assessment=FeatureAssessment.NOT_ASSESSED,
                agreement=None,
                weight=weight,
            )
        same_identifier = source_identifier == candidate_identifier
        same_country = source.country.upper() == candidate.country.upper()
        if same_identifier and not same_country:
            return ResolutionFeatureEvidence(
                name=name,
                assessment=FeatureAssessment.CONFLICT,
                agreement=Decimal("0"),
                weight=weight,
            )
        return ResolutionFeatureEvidence(
            name=name,
            assessment=FeatureAssessment.ASSESSED,
            agreement=Decimal("1") if same_identifier else Decimal("0"),
            weight=weight,
        )

    @staticmethod
    def _text_feature(
        name: ResolutionFeatureName,
        left: str | None,
        right: str | None,
        weights: dict[ResolutionFeatureName, Decimal],
    ) -> ResolutionFeatureEvidence:
        weight = weights[name]
        if left is None or right is None:
            return ResolutionFeatureEvidence(
                name=name,
                assessment=FeatureAssessment.NOT_ASSESSED,
                agreement=None,
                weight=weight,
            )
        normalized_left = _normalized_text(left)
        normalized_right = _normalized_text(right)
        if not normalized_left or not normalized_right:
            return ResolutionFeatureEvidence(
                name=name,
                assessment=FeatureAssessment.NOT_ASSESSED,
                agreement=None,
                weight=weight,
            )
        return ResolutionFeatureEvidence(
            name=name,
            assessment=FeatureAssessment.ASSESSED,
            agreement=_similarity(left, right),
            weight=weight,
        )

    @staticmethod
    def _exact_feature(
        name: ResolutionFeatureName,
        left: str | None,
        right: str | None,
        weights: dict[ResolutionFeatureName, Decimal],
    ) -> ResolutionFeatureEvidence:
        weight = weights[name]
        if left is None or right is None:
            return ResolutionFeatureEvidence(
                name=name,
                assessment=FeatureAssessment.NOT_ASSESSED,
                agreement=None,
                weight=weight,
            )
        normalized_left = _normalized_text(left)
        normalized_right = _normalized_text(right)
        if not normalized_left or not normalized_right:
            return ResolutionFeatureEvidence(
                name=name,
                assessment=FeatureAssessment.NOT_ASSESSED,
                agreement=None,
                weight=weight,
            )
        return ResolutionFeatureEvidence(
            name=name,
            assessment=FeatureAssessment.ASSESSED,
            agreement=(
                Decimal("1") if normalized_left == normalized_right else Decimal("0")
            ),
            weight=weight,
        )

    def advise_ubo(
        self,
        candidate: OwnershipCandidate,
        *,
        policy: IntelligencePolicySnapshot | None = None,
    ) -> UboAdviceResult:
        active_policy = policy or legacy_intelligence_policy_snapshot()
        if (
            candidate.threshold_result == OwnershipThresholdResult.INDETERMINATE
            or candidate.classification
            in {
                OwnershipCandidateClassification.INDETERMINATE,
                OwnershipCandidateClassification.REVIEW_REQUIRED,
            }
        ):
            return UboAdviceResult(
                party_id=candidate.party.party_id,
                probability=None,
                label=UboAdviceLabel.REVIEW,
                authoritative_ownership_percent=candidate.aggregated_ownership_percent,
                reason_codes=("DETERMINISTIC_RESULT_INDETERMINATE",),
                likely_threshold=active_policy.ubo_advisory_likely_threshold,
                unlikely_threshold=active_policy.ubo_advisory_unlikely_threshold,
            )

        probability = _six(
            min(Decimal("0.990000"), candidate.aggregated_ownership_percent / Decimal("50"))
        )
        if probability >= active_policy.ubo_advisory_likely_threshold:
            label = UboAdviceLabel.LIKELY_UBO
        elif probability <= active_policy.ubo_advisory_unlikely_threshold:
            label = UboAdviceLabel.UNLIKELY_UBO
        else:
            label = UboAdviceLabel.REVIEW
        return UboAdviceResult(
            party_id=candidate.party.party_id,
            probability=probability,
            label=label,
            authoritative_ownership_percent=candidate.aggregated_ownership_percent,
            reason_codes=(
                "CONSUMES_DETERMINISTIC_OWNERSHIP_RESULT",
                f"THRESHOLD_RESULT_{candidate.threshold_result.value}",
            ),
            likely_threshold=active_policy.ubo_advisory_likely_threshold,
            unlikely_threshold=active_policy.ubo_advisory_unlikely_threshold,
        )

    def assess_mock_risk(
        self,
        inputs: MockRiskInputs,
        *,
        policy: IntelligencePolicySnapshot | None = None,
    ) -> MockRiskAssessment:
        active_policy = policy or legacy_intelligence_policy_snapshot()
        score = 0
        assessed = 0
        signal_assessments: dict[MockRiskSignalName, str] = {}
        reason_codes: list[str] = []
        not_assessed: set[MockRiskLimitationName] = set(
            _EXTERNAL_UNAVAILABLE_RISK_SIGNALS
        )

        entity_scores = {
            EntityResolutionOutcome.EXACT_MATCH: 0,
            EntityResolutionOutcome.PROBABLE_MATCH: 10,
            EntityResolutionOutcome.REVIEW_REQUIRED: 35,
            EntityResolutionOutcome.NO_MATCH: 45,
            EntityResolutionOutcome.CONFLICT: 60,
        }
        if inputs.entity_resolution_outcome is None:
            signal_assessments["entity_resolution"] = "NOT_ASSESSED"
            not_assessed.add("entity_resolution")
        else:
            assessed += 1
            contribution = entity_scores[inputs.entity_resolution_outcome]
            score += contribution
            signal_assessments["entity_resolution"] = str(contribution)
            reason_codes.append(f"ENTITY_{inputs.entity_resolution_outcome.value}")

        if inputs.document_exception_count is None:
            signal_assessments["document"] = "NOT_ASSESSED"
            not_assessed.add("document")
        else:
            assessed += 1
            contribution = min(30, inputs.document_exception_count * 15)
            score += contribution
            signal_assessments["document"] = str(contribution)
            reason_codes.append("DOCUMENT_EXCEPTION_COUNT_AVAILABLE")

        if inputs.ownership_issue_count is None:
            signal_assessments["ownership"] = "NOT_ASSESSED"
            not_assessed.add("ownership")
        else:
            assessed += 1
            contribution = min(40, inputs.ownership_issue_count * 20)
            score += contribution
            signal_assessments["ownership"] = str(contribution)
            reason_codes.append("OWNERSHIP_ISSUE_COUNT_AVAILABLE")

        if assessed < 2:
            return MockRiskAssessment(
                score=None,
                band=MockRiskBand.NOT_ASSESSED,
                signal_assessments=signal_assessments,
                reason_codes=("INSUFFICIENT_AVAILABLE_SIGNALS",),
                not_assessed_signals=frozenset(not_assessed),
                medium_threshold=active_policy.mock_risk_medium_threshold,
                high_threshold=active_policy.mock_risk_high_threshold,
                blocks_readiness=active_policy.mock_risk_blocks_readiness,
            )

        bounded_score = min(100, score)
        band = (
            MockRiskBand.HIGH
            if bounded_score >= active_policy.mock_risk_high_threshold
            else MockRiskBand.MEDIUM
            if bounded_score >= active_policy.mock_risk_medium_threshold
            else MockRiskBand.LOW
        )
        return MockRiskAssessment(
            score=bounded_score,
            band=band,
            signal_assessments=signal_assessments,
            reason_codes=tuple(reason_codes),
            not_assessed_signals=frozenset(not_assessed),
            medium_threshold=active_policy.mock_risk_medium_threshold,
            high_threshold=active_policy.mock_risk_high_threshold,
            blocks_readiness=active_policy.mock_risk_blocks_readiness,
        )


class OnboardingIntelligenceProjectionService:
    """Build and persist one versioned case projection from existing canonical owners."""

    def __init__(
        self,
        *,
        cases: OnboardingService,
        documents: DocumentProcessingRepository,
        ownership: OwnershipAnalysisRepository,
        repository: OnboardingIntelligenceRepository,
        intelligence: OnboardingIntelligenceService | None = None,
        candidate_resolver: Callable[
            [UUID, EntityIdentity], tuple[EntityIdentity, ...] | None
        ]
        | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._cases = cases
        self._documents = documents
        self._ownership = ownership
        self._repository = repository
        self._intelligence = intelligence or OnboardingIntelligenceService()
        self._candidate_resolver = candidate_resolver
        self._clock = clock or (lambda: datetime.now(UTC))

    def get(self, case_id: UUID) -> OnboardingIntelligenceRecord | None:
        record = self._repository.get_for_case(case_id)
        if record is None:
            return None
        case = self._cases.get_case(case_id)
        if case is None or case.policy_snapshot.intelligence is None:
            raise ValueError("intelligence record has no immutable case policy")
        record.validate_policy_binding(
            catalogue_version=case.policy_snapshot.catalogue_version,
            policy=case.policy_snapshot.intelligence,
        )
        return record

    def evaluate(self, case_id: UUID) -> OnboardingIntelligenceRecord | None:
        case = self._cases.get_case(case_id)
        if case is None or case.policy_snapshot.intelligence is None:
            return None
        policy = case.policy_snapshot.intelligence
        documents = tuple(self._documents.list_for_case(case_id))
        ownership = self._ownership.get_for_case(case_id)
        if ownership is None:
            return None

        entity_resolution = None
        if self._candidate_resolver is not None and case.entity is not None:
            address = case.entity.registered_address
            source = EntityIdentity(
                candidate_id="SOURCE",
                registration_number=case.entity.registration_number,
                country=case.entity.country_of_incorporation,
                legal_name=case.entity.legal_name,
                legal_form=case.entity.party_type,
                registered_address=(
                    " ".join(
                        item
                        for item in (
                            address.address_line_1,
                            address.address_line_2,
                            address.postal_code,
                            address.country_code,
                        )
                        if item
                    )
                    if address is not None
                    else None
                ),
                incorporated_on=case.entity.registration_date,
                source_reference="CASE_CANONICAL_ENTITY",
            )
            candidates = self._candidate_resolver(case_id, source)
            if candidates is not None:
                entity_resolution = self._intelligence.resolve_entity(
                    source=source,
                    candidates=candidates,
                    policy=policy,
                )

        ubo_advice = tuple(
            self._intelligence.advise_ubo(candidate, policy=policy)
            for candidate in ownership.candidates
        )
        document_exception_count = sum(
            item.is_current_evidence
            and item.state
            in {
                DocumentProcessingState.REVIEW_REQUIRED,
                DocumentProcessingState.FAILED,
            }
            for item in documents
        )
        mock_risk = self._intelligence.assess_mock_risk(
            MockRiskInputs(
                entity_resolution_outcome=(
                    entity_resolution.outcome if entity_resolution is not None else None
                ),
                document_exception_count=document_exception_count if documents else None,
                ownership_issue_count=len(ownership.issues),
            ),
            policy=policy,
        )
        fingerprint_payload = {
            "case_id": str(case_id),
            "policy_catalogue_version": case.policy_snapshot.catalogue_version,
            "entity_resolution": (
                entity_resolution.model_dump(mode="json")
                if entity_resolution is not None
                else None
            ),
            "document_versions": [
                [str(item.document_id), item.state.value, len(item.events)]
                for item in documents
                if item.is_current_evidence
            ],
            "ownership": [
                str(ownership.analysis_id),
                ownership.version,
                ownership.state.value,
                len(ownership.events),
            ],
        }
        encoded = json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        fingerprint = f"sha256:{sha256(encoded).hexdigest()}"
        current = self._repository.get_for_case(case_id)
        if current is not None:
            current.validate_policy_binding(
                catalogue_version=case.policy_snapshot.catalogue_version,
                policy=policy,
            )
            if current.input_fingerprint == fingerprint:
                return current
        version = 1 if current is None else current.version + 1
        record = OnboardingIntelligenceRecord(
            case_id=case_id,
            version=version,
            input_fingerprint=fingerprint,
            policy_catalogue_version=case.policy_snapshot.catalogue_version,
            entity_resolution=entity_resolution,
            ubo_advice=ubo_advice,
            mock_risk=mock_risk,
            evaluated_at=self._clock(),
        )
        record.validate_policy_binding(
            catalogue_version=case.policy_snapshot.catalogue_version,
            policy=policy,
        )
        return self._repository.save(
            record,
            expected_version=None if current is None else current.version,
        )
