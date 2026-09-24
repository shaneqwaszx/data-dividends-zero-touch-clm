"""Source-neutral, explainable onboarding intelligence projections.

These types carry bounded evidence and immutable advisory labels. They do not own
canonical entity data, legal UBO calculation, compliance risk, readiness, or approval.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.policy import IntelligencePolicySnapshot


class EntityResolutionOutcome(StrEnum):
    EXACT_MATCH = "EXACT_MATCH"
    PROBABLE_MATCH = "PROBABLE_MATCH"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NO_MATCH = "NO_MATCH"
    CONFLICT = "CONFLICT"


class ResolutionFeatureName(StrEnum):
    REGISTRATION_NUMBER_AND_COUNTRY = "REGISTRATION_NUMBER_AND_COUNTRY"
    LEGAL_NAME_SIMILARITY = "LEGAL_NAME_SIMILARITY"
    REGISTERED_ADDRESS_SIMILARITY = "REGISTERED_ADDRESS_SIMILARITY"
    LEGAL_FORM_AGREEMENT = "LEGAL_FORM_AGREEMENT"
    INCORPORATION_DATE_AGREEMENT = "INCORPORATION_DATE_AGREEMENT"


class FeatureAssessment(StrEnum):
    ASSESSED = "ASSESSED"
    NOT_ASSESSED = "NOT_ASSESSED"
    CONFLICT = "CONFLICT"


class EntityIdentity(BaseModel):
    """Bounded canonical identity fields used as scorer inputs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")]
    registration_number: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    country: Annotated[str, Field(pattern=r"^[A-Za-z]{2,3}$")] | None = None
    legal_name: Annotated[str, Field(min_length=1, max_length=160)] | None = None
    legal_form: Annotated[str, Field(min_length=1, max_length=80)] | None = None
    registered_address: Annotated[str, Field(min_length=1, max_length=240)] | None = None
    incorporated_on: date | None = None
    source_reference: Annotated[
        str,
        Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
    ] | None = None

    @field_validator(
        "registration_number", "country", "legal_name", "legal_form", "registered_address"
    )
    @classmethod
    def normalized_non_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized or any(ord(character) < 32 for character in normalized):
            raise ValueError("identity text must be non-blank safe text")
        return normalized


class ResolutionFeatureEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: ResolutionFeatureName
    assessment: FeatureAssessment
    agreement: Annotated[
        Decimal | None,
        Field(default=None, ge=Decimal("0"), le=Decimal("1"), decimal_places=6),
    ]
    weight: Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("1"), decimal_places=6)]

    @model_validator(mode="after")
    def assessment_matches_agreement(self) -> ResolutionFeatureEvidence:
        if self.assessment == FeatureAssessment.NOT_ASSESSED and self.agreement is not None:
            raise ValueError("unassessed feature cannot carry agreement")
        if self.assessment == FeatureAssessment.ASSESSED and self.agreement is None:
            raise ValueError("assessed feature requires agreement")
        if self.assessment == FeatureAssessment.CONFLICT and self.agreement != Decimal("0"):
            raise ValueError("conflicting feature requires zero agreement")
        return self


class EntityCandidateEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")]
    probability: Annotated[
        Decimal, Field(ge=Decimal("0"), le=Decimal("1"), decimal_places=6)
    ]
    assessed_weight: Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("1"), decimal_places=6)]
    corroborating_feature_count: Annotated[int, Field(ge=0, le=5)]
    features: tuple[ResolutionFeatureEvidence, ...] = Field(min_length=5, max_length=5)
    top_contributing_features: tuple[ResolutionFeatureName, ...] = Field(max_length=3)
    source_reference: Annotated[
        str,
        Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
    ] | None = None

    @model_validator(mode="after")
    def evidence_is_internally_consistent(self) -> EntityCandidateEvidence:
        names = [item.name for item in self.features]
        if tuple(names) != tuple(ResolutionFeatureName):
            raise ValueError("candidate evidence requires each ordered feature exactly once")
        assessed = tuple(
            item
            for item in self.features
            if item.assessment == FeatureAssessment.ASSESSED and item.agreement is not None
        )
        if self.assessed_weight != sum((item.weight for item in assessed), Decimal("0")):
            raise ValueError("assessed weight does not match feature evidence")
        weighted_agreement = sum(
            (
                item.weight * item.agreement
                for item in assessed
                if item.agreement is not None
            ),
            Decimal("0"),
        )
        expected_probability = (
            weighted_agreement / self.assessed_weight
            if self.assessed_weight
            else Decimal("0")
        ).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        if self.probability != expected_probability:
            raise ValueError("candidate probability contradicts feature evidence")
        expected_corroboration = sum(
            1
            for item in assessed
            if item.name != ResolutionFeatureName.LEGAL_FORM_AGREEMENT
            and item.agreement is not None
            and item.agreement >= Decimal("0.80")
        )
        if self.corroborating_feature_count != expected_corroboration:
            raise ValueError("corroborating feature count does not match strong evidence")
        if len(set(self.top_contributing_features)) != len(self.top_contributing_features):
            raise ValueError("top contributing features must be unique")
        if not set(self.top_contributing_features) <= set(names):
            raise ValueError("top contributing feature is absent from evidence")
        return self


class EntityResolutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome: EntityResolutionOutcome
    selected_candidate_id: Annotated[
        str,
        Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$"),
    ] | None = None
    source_reference: Annotated[
        str,
        Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
    ] | None = None
    candidates: tuple[EntityCandidateEvidence, ...] = Field(max_length=25)
    reason_codes: tuple[Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")], ...]
    model_version: Literal["entity-resolution-linear-v1"] = "entity-resolution-linear-v1"
    assistance_label: Literal["ML_ASSISTED"] = "ML_ASSISTED"
    disclaimer: Literal["NOT_IDENTITY_AUTHORITY"] = "NOT_IDENTITY_AUTHORITY"

    @model_validator(mode="after")
    def outcome_matches_candidate_evidence(self) -> EntityResolutionResult:
        candidate_ids = [item.candidate_id for item in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("duplicate entity candidate")
        if tuple(self.candidates) != tuple(
            sorted(self.candidates, key=lambda item: (-item.probability, item.candidate_id))
        ):
            raise ValueError("entity candidates must use deterministic ranking")
        selected_outcomes = {
            EntityResolutionOutcome.EXACT_MATCH,
            EntityResolutionOutcome.PROBABLE_MATCH,
        }
        identifier_features = tuple(
            next(
                feature
                for feature in candidate.features
                if feature.name == ResolutionFeatureName.REGISTRATION_NUMBER_AND_COUNTRY
            )
            for candidate in self.candidates
        )
        exact_candidates = tuple(
            candidate
            for candidate, identifier in zip(
                self.candidates, identifier_features, strict=True
            )
            if identifier.assessment == FeatureAssessment.ASSESSED
            and identifier.agreement == Decimal("1")
        )
        conflicting_candidates = tuple(
            candidate
            for candidate, identifier in zip(
                self.candidates, identifier_features, strict=True
            )
            if identifier.assessment == FeatureAssessment.CONFLICT
        )
        if conflicting_candidates and self.outcome != EntityResolutionOutcome.CONFLICT:
            raise ValueError("conflicting identity evidence requires conflict outcome")
        if len(exact_candidates) == 1 and self.outcome != EntityResolutionOutcome.EXACT_MATCH:
            raise ValueError("exact identity evidence requires exact match outcome")
        if len(exact_candidates) > 1 and self.outcome != EntityResolutionOutcome.CONFLICT:
            raise ValueError("duplicate exact identity evidence requires conflict outcome")
        if self.outcome == EntityResolutionOutcome.CONFLICT and not (
            conflicting_candidates or len(exact_candidates) > 1
        ):
            raise ValueError("conflict outcome requires conflicting identity evidence")
        if self.outcome in selected_outcomes:
            if self.selected_candidate_id is None:
                raise ValueError("selected outcome requires selected candidate")
            if self.selected_candidate_id not in candidate_ids:
                raise ValueError("selected candidate is absent from candidate set")
            selected = next(
                item
                for item in self.candidates
                if item.candidate_id == self.selected_candidate_id
            )
            if self.outcome == EntityResolutionOutcome.EXACT_MATCH:
                identifier = next(
                    item
                    for item in selected.features
                    if item.name
                    == ResolutionFeatureName.REGISTRATION_NUMBER_AND_COUNTRY
                )
                if (
                    identifier.assessment != FeatureAssessment.ASSESSED
                    or identifier.agreement != Decimal("1")
                ):
                    raise ValueError("exact match requires exact trusted identity evidence")
            else:
                identifier = next(
                    item
                    for item in selected.features
                    if item.name
                    == ResolutionFeatureName.REGISTRATION_NUMBER_AND_COUNTRY
                )
                if selected is not self.candidates[0]:
                    raise ValueError("probable match must select the top-ranked candidate")
                if selected.corroborating_feature_count < 2:
                    raise ValueError("probable match requires independently strong evidence")
                if (
                    identifier.assessment == FeatureAssessment.ASSESSED
                    and identifier.agreement == Decimal("0")
                ):
                    raise ValueError("probable match cannot override identifier disagreement")
        elif self.selected_candidate_id is not None:
            raise ValueError("non-selected outcome cannot carry selected candidate")
        return self

    def validate_policy_semantics(self, policy: IntelligencePolicySnapshot) -> None:
        expected_weights = {
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
        if self.model_version != policy.entity_resolution_model_version:
            raise ValueError("entity-resolution model version contradicts case policy")
        if any(
            feature.weight != expected_weights[feature.name]
            for candidate in self.candidates
            for feature in candidate.features
        ):
            raise ValueError("entity-resolution weights contradict case policy")

        if not self.candidates:
            expected_outcome = EntityResolutionOutcome.NO_MATCH
            expected_selected = None
        else:
            identifier_features = tuple(candidate.features[0] for candidate in self.candidates)
            conflicts = tuple(
                candidate
                for candidate, identifier in zip(
                    self.candidates, identifier_features, strict=True
                )
                if identifier.assessment == FeatureAssessment.CONFLICT
            )
            exact = tuple(
                candidate
                for candidate, identifier in zip(
                    self.candidates, identifier_features, strict=True
                )
                if identifier.assessment == FeatureAssessment.ASSESSED
                and identifier.agreement == Decimal("1")
            )
            if conflicts or len(exact) > 1:
                expected_outcome = EntityResolutionOutcome.CONFLICT
                expected_selected = None
            elif len(exact) == 1:
                expected_outcome = EntityResolutionOutcome.EXACT_MATCH
                expected_selected = exact[0].candidate_id
            else:
                top = self.candidates[0]
                ambiguous = (
                    len(self.candidates) > 1
                    and top.probability >= policy.entity_resolution_review_threshold
                    and top.probability - self.candidates[1].probability
                    <= policy.entity_resolution_ambiguity_margin
                )
                identifier_disagrees = (
                    top.features[0].assessment == FeatureAssessment.ASSESSED
                    and top.features[0].agreement == Decimal("0")
                )
                if ambiguous:
                    expected_outcome = EntityResolutionOutcome.REVIEW_REQUIRED
                    expected_selected = None
                elif (
                    top.probability >= policy.entity_resolution_auto_match_threshold
                    and top.corroborating_feature_count >= 2
                    and not identifier_disagrees
                ):
                    expected_outcome = EntityResolutionOutcome.PROBABLE_MATCH
                    expected_selected = top.candidate_id
                elif top.probability >= policy.entity_resolution_review_threshold:
                    expected_outcome = EntityResolutionOutcome.REVIEW_REQUIRED
                    expected_selected = None
                else:
                    expected_outcome = EntityResolutionOutcome.NO_MATCH
                    expected_selected = None
        if self.outcome != expected_outcome or self.selected_candidate_id != expected_selected:
            raise ValueError("entity-resolution outcome contradicts case policy and evidence")


class UboAdviceLabel(StrEnum):
    LIKELY_UBO = "LIKELY_UBO"
    REVIEW = "REVIEW"
    UNLIKELY_UBO = "UNLIKELY_UBO"


class UboAdviceResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    party_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")]
    probability: Annotated[
        Decimal | None,
        Field(default=None, ge=Decimal("0"), le=Decimal("1"), decimal_places=6),
    ]
    label: UboAdviceLabel
    authoritative_ownership_percent: Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("100"))]
    reason_codes: tuple[
        Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")], ...
    ] = Field(min_length=1, max_length=8)
    likely_threshold: Annotated[
        Decimal,
        Field(ge=Decimal("0"), le=Decimal("1"), decimal_places=6),
    ] = Decimal("0.65")
    unlikely_threshold: Annotated[
        Decimal,
        Field(ge=Decimal("0"), le=Decimal("1"), decimal_places=6),
    ] = Decimal("0.35")
    model_version: Literal["ubo-advisory-linear-v1"] = "ubo-advisory-linear-v1"
    assistance_label: Literal["ML_ASSISTED"] = "ML_ASSISTED"
    disclaimer: Literal["NOT_LEGAL_UBO_DETERMINATION"] = "NOT_LEGAL_UBO_DETERMINATION"

    @model_validator(mode="after")
    def label_matches_probability_and_ownership(self) -> UboAdviceResult:
        if self.unlikely_threshold >= self.likely_threshold:
            raise ValueError("UBO advisory thresholds overlap")
        if self.probability is None:
            if self.label != UboAdviceLabel.REVIEW:
                raise ValueError("missing UBO probability requires review")
            return self
        expected_probability = min(
            Decimal("0.990000"),
            self.authoritative_ownership_percent / Decimal("50"),
        ).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        if self.probability != expected_probability:
            raise ValueError("UBO probability contradicts authoritative ownership")
        expected_label = (
            UboAdviceLabel.LIKELY_UBO
            if self.probability >= self.likely_threshold
            else UboAdviceLabel.UNLIKELY_UBO
            if self.probability <= self.unlikely_threshold
            else UboAdviceLabel.REVIEW
        )
        if self.label != expected_label:
            raise ValueError("UBO label contradicts probability and thresholds")
        return self


class MockRiskBand(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    NOT_ASSESSED = "NOT_ASSESSED"


MockRiskSignalName = Literal["entity_resolution", "document", "ownership"]
MockRiskLimitationName = Literal[
    "entity_resolution",
    "document",
    "ownership",
    "pep",
    "sanctions",
    "adverse_media",
    "transaction_monitoring",
    "product_channel",
]


class MockRiskInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_resolution_outcome: EntityResolutionOutcome | None = None
    document_exception_count: Annotated[int | None, Field(default=None, ge=0, le=100)]
    ownership_issue_count: Annotated[int | None, Field(default=None, ge=0, le=100)]


class MockRiskAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    score: Annotated[int | None, Field(default=None, ge=0, le=100)]
    band: MockRiskBand
    signal_assessments: dict[MockRiskSignalName, str]
    reason_codes: tuple[
        Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")], ...
    ] = Field(min_length=1, max_length=12)
    not_assessed_signals: frozenset[MockRiskLimitationName]
    medium_threshold: Annotated[int, Field(ge=0, le=100)] = 30
    high_threshold: Annotated[int, Field(ge=0, le=100)] = 60
    model_version: Literal["mock-advisory-risk-rules-v1"] = "mock-advisory-risk-rules-v1"
    label: Literal["MOCK_ADVISORY_RISK"] = "MOCK_ADVISORY_RISK"
    disclaimer: Literal["NOT_COMPLIANCE_DECISION"] = "NOT_COMPLIANCE_DECISION"
    blocks_readiness: bool = False

    @model_validator(mode="after")
    def band_matches_score_thresholds_and_signals(self) -> MockRiskAssessment:
        if self.medium_threshold >= self.high_threshold:
            raise ValueError("mock-risk thresholds overlap")
        required_signals = {"entity_resolution", "document", "ownership"}
        if set(self.signal_assessments) != required_signals:
            raise ValueError("mock-risk signal set is incomplete")
        for name, value in self.signal_assessments.items():
            if value == "NOT_ASSESSED":
                if name not in self.not_assessed_signals:
                    raise ValueError("unassessed signal missing from explicit limitations")
                continue
            if not value.isascii() or not value.isdecimal() or not 0 <= int(value) <= 100:
                raise ValueError("assessed mock-risk signal must be a bounded integer")
            if name in self.not_assessed_signals:
                raise ValueError("assessed signal cannot be listed as not assessed")
        if self.score is None:
            if self.band != MockRiskBand.NOT_ASSESSED:
                raise ValueError("missing mock-risk score requires NOT_ASSESSED band")
            if sum(
                value != "NOT_ASSESSED" for value in self.signal_assessments.values()
            ) >= 2:
                raise ValueError("two assessed signals require a mock-risk score")
            return self
        expected_band = (
            MockRiskBand.HIGH
            if self.score >= self.high_threshold
            else MockRiskBand.MEDIUM
            if self.score >= self.medium_threshold
            else MockRiskBand.LOW
        )
        if self.band != expected_band:
            raise ValueError("mock-risk band contradicts score and thresholds")
        assessed_count = sum(
            value != "NOT_ASSESSED" for value in self.signal_assessments.values()
        )
        if assessed_count < 2:
            raise ValueError("scored mock risk requires at least two assessed signals")
        expected_score = min(
            100,
            sum(
                int(value)
                for value in self.signal_assessments.values()
                if value != "NOT_ASSESSED"
            ),
        )
        if self.score != expected_score:
            raise ValueError("mock-risk score contradicts signal contributions")
        return self


class OnboardingIntelligenceRecord(BaseModel):
    """Case-bound immutable advisory projection retained in the case envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: UUID
    version: Annotated[int, Field(ge=1)]
    input_fingerprint: Annotated[str, Field(pattern=r"^sha256:[a-f0-9]{64}$")]
    policy_catalogue_version: Annotated[int, Field(ge=0)]
    model_bundle_version: Literal["onboarding-intelligence-v1"] = "onboarding-intelligence-v1"
    entity_resolution: EntityResolutionResult | None = None
    ubo_advice: tuple[UboAdviceResult, ...] = Field(default=(), max_length=64)
    mock_risk: MockRiskAssessment | None = None
    evaluated_at: datetime

    @field_validator("evaluated_at")
    @classmethod
    def evaluated_at_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("intelligence evaluation timestamp must be UTC")
        return value

    @model_validator(mode="after")
    def contains_projection(self) -> OnboardingIntelligenceRecord:
        if self.entity_resolution is None and not self.ubo_advice and self.mock_risk is None:
            raise ValueError("intelligence record has no projections")
        party_ids = [item.party_id for item in self.ubo_advice]
        if len(party_ids) != len(set(party_ids)):
            raise ValueError("duplicate UBO advisory party")
        return self

    def validate_policy_binding(
        self,
        *,
        catalogue_version: int,
        policy: IntelligencePolicySnapshot,
    ) -> None:
        if self.policy_catalogue_version != catalogue_version:
            raise ValueError("intelligence catalogue version contradicts case policy")
        if self.entity_resolution is not None:
            self.entity_resolution.validate_policy_semantics(policy)
        if any(
            advice.likely_threshold != policy.ubo_advisory_likely_threshold
            or advice.unlikely_threshold != policy.ubo_advisory_unlikely_threshold
            or advice.model_version != policy.ubo_advisory_model_version
            for advice in self.ubo_advice
        ):
            raise ValueError("UBO advisory thresholds contradict case policy")
        if self.mock_risk is not None and (
            self.mock_risk.medium_threshold != policy.mock_risk_medium_threshold
            or self.mock_risk.high_threshold != policy.mock_risk_high_threshold
            or self.mock_risk.blocks_readiness != policy.mock_risk_blocks_readiness
            or self.mock_risk.model_version != policy.mock_risk_model_version
        ):
            raise ValueError("mock-risk projection contradicts case policy")
