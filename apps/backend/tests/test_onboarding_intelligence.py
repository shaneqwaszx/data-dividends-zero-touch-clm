from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from phase13_test_settings import ordinary_test_settings
from pydantic import ValidationError

from app.domain.onboarding_intelligence import (
    ClassificationConsistencyStatus,
    EntityCandidateEvidence,
    EntityIdentity,
    EntityResolutionOutcome,
    EntityResolutionResult,
    FeatureAssessment,
    MockRiskAssessment,
    MockRiskBand,
    MockRiskInputs,
    ResolutionFeatureEvidence,
    ResolutionFeatureName,
    UboAdviceLabel,
    UboAdviceResult,
    assess_classification_consistency,
)
from app.domain.ownership import (
    OwnershipCandidate,
    OwnershipCandidateClassification,
    OwnershipThresholdResult,
    Party,
    PartyType,
)
from app.domain.policy import (
    EntityResolutionWeights,
    IntelligencePolicySnapshot,
    legacy_intelligence_policy_snapshot,
)
from app.main import create_app
from app.services.onboarding_intelligence import OnboardingIntelligenceService

PDF = (Path(__file__).parent / "fixtures" / "uat" / "clean-company-profile.pdf").read_bytes()


def identity(
    *,
    candidate_id: str,
    registration_number: str | None = None,
    country: str | None = "SG",
    legal_name: str | None = "Merlion Circular Labs Pte. Ltd.",
    legal_form: str | None = "PRIVATE_COMPANY_LIMITED_BY_SHARES",
    address: str | None = "1 Marina Boulevard Singapore 018989",
    incorporated_on: date | None = date(2024, 1, 15),
    source_reference: str | None = "SYNTHETIC_EVALUATION",
) -> EntityIdentity:
    return EntityIdentity(
        candidate_id=candidate_id,
        registration_number=registration_number,
        country=country,
        legal_name=legal_name,
        legal_form=legal_form,
        registered_address=address,
        incorporated_on=incorporated_on,
        source_reference=source_reference,
    )


def test_exact_registration_number_and_country_dominate_descriptive_differences() -> None:
    service = OnboardingIntelligenceService()
    source = identity(candidate_id="source", registration_number="202400001A")
    candidate = identity(
        candidate_id="goldtier-17",
        registration_number=" 202400001a ",
        legal_name="Historical trading name",
        address="Former address",
    )

    result = service.resolve_entity(source=source, candidates=(candidate,))

    assert result.outcome == EntityResolutionOutcome.EXACT_MATCH
    assert result.selected_candidate_id == "goldtier-17"
    assert result.model_version == "entity-resolution-linear-v1"
    assert result.candidates[0].features[0].name == "REGISTRATION_NUMBER_AND_COUNTRY"
    assert result.candidates[0].features[0].agreement == Decimal("1")
    assert Decimal("0.55") <= result.candidates[0].probability <= Decimal("1")
    assert result.candidates[0].source_reference == "SYNTHETIC_EVALUATION"
    assert result.candidates[0].top_contributing_features[0] == (
        "REGISTRATION_NUMBER_AND_COUNTRY"
    )
    serialized = result.model_dump_json().casefold()
    assert "historical trading name" not in serialized
    assert "merlion circular labs" not in serialized


def test_identifier_country_conflict_is_never_hidden_by_name_similarity() -> None:
    service = OnboardingIntelligenceService()
    source = identity(candidate_id="source", registration_number="202400001A", country="SG")
    candidate = identity(
        candidate_id="candidate",
        registration_number="202400001A",
        country="AU",
    )

    result = service.resolve_entity(source=source, candidates=(candidate,))

    assert result.outcome == EntityResolutionOutcome.CONFLICT
    assert result.selected_candidate_id is None
    assert "IDENTIFIER_COUNTRY_CONFLICT" in result.reason_codes


def test_distinct_unicode_identifiers_never_collapse_to_exact_match() -> None:
    service = OnboardingIntelligenceService()
    source = identity(
        candidate_id="source",
        registration_number="公司甲",
        legal_name=None,
        legal_form=None,
        address=None,
        incorporated_on=None,
    )
    candidate = identity(
        candidate_id="candidate",
        registration_number="公司乙",
        legal_name=None,
        legal_form=None,
        address=None,
        incorporated_on=None,
    )

    result = service.resolve_entity(source=source, candidates=(candidate,))

    assert result.outcome == EntityResolutionOutcome.NO_MATCH
    assert result.selected_candidate_id is None
    assert result.reason_codes == ("WEIGHTED_EVIDENCE_BELOW_THRESHOLD",)


def test_unusable_identifier_normalization_is_not_assessed() -> None:
    source = identity(
        candidate_id="source",
        registration_number="---",
        legal_name=None,
        legal_form=None,
        address=None,
        incorporated_on=None,
    )
    candidate = identity(
        candidate_id="candidate",
        registration_number="...",
        legal_name=None,
        legal_form=None,
        address=None,
        incorporated_on=None,
    )

    result = OnboardingIntelligenceService().resolve_entity(
        source=source,
        candidates=(candidate,),
    )

    assert result.outcome == EntityResolutionOutcome.NO_MATCH
    assert result.candidates[0].features[0].assessment == FeatureAssessment.NOT_ASSESSED


@pytest.mark.parametrize(
    ("source_country", "candidate_country"),
    [("SG", None), (None, "SG")],
)
def test_distinct_usable_identifiers_never_auto_match_when_country_is_missing(
    source_country: str | None,
    candidate_country: str | None,
) -> None:
    source = identity(
        candidate_id="source",
        registration_number="202400001A",
        country=source_country,
    )
    candidate = identity(
        candidate_id="candidate",
        registration_number="209999999Z",
        country=candidate_country,
    )

    result = OnboardingIntelligenceService().resolve_entity(
        source=source,
        candidates=(candidate,),
    )

    assert result.outcome == EntityResolutionOutcome.NO_MATCH
    assert result.selected_candidate_id is None
    assert result.candidates[0].features[0].assessment == FeatureAssessment.ASSESSED
    assert result.candidates[0].features[0].agreement == Decimal("0")
    assert result.reason_codes == ("WEIGHTED_EVIDENCE_BELOW_THRESHOLD",)


def test_name_plus_generic_legal_form_never_auto_selects() -> None:
    source = identity(
        candidate_id="source",
        registration_number=None,
        address=None,
        incorporated_on=None,
    )
    candidate = identity(
        candidate_id="candidate",
        registration_number=None,
        address=None,
        incorporated_on=None,
    )

    result = OnboardingIntelligenceService().resolve_entity(
        source=source,
        candidates=(candidate,),
    )

    assert result.outcome == EntityResolutionOutcome.REVIEW_REQUIRED
    assert result.selected_candidate_id is None
    assert result.reason_codes == ("INSUFFICIENT_CORROBORATION",)


def test_same_name_different_country_never_auto_selects() -> None:
    source = identity(candidate_id="source", registration_number=None, country="SG")
    candidate = identity(
        candidate_id="candidate",
        registration_number=None,
        country="AU",
    )

    result = OnboardingIntelligenceService().resolve_entity(
        source=source,
        candidates=(candidate,),
    )

    assert result.outcome == EntityResolutionOutcome.CONFLICT
    assert result.selected_candidate_id is None
    assert result.reason_codes == ("IDENTIFIER_COUNTRY_CONFLICT",)


def test_name_only_and_address_only_never_auto_match() -> None:
    service = OnboardingIntelligenceService()
    name_only_source = identity(
        candidate_id="source",
        registration_number=None,
        address=None,
        legal_form=None,
        incorporated_on=None,
    )
    name_only_candidate = identity(
        candidate_id="candidate",
        registration_number=None,
        address=None,
        legal_form=None,
        incorporated_on=None,
    )
    address_only_source = identity(
        candidate_id="source",
        registration_number=None,
        legal_name=None,
        legal_form=None,
        incorporated_on=None,
    )
    address_only_candidate = identity(
        candidate_id="candidate",
        registration_number=None,
        legal_name=None,
        legal_form=None,
        incorporated_on=None,
    )

    name_result = service.resolve_entity(source=name_only_source, candidates=(name_only_candidate,))
    address_result = service.resolve_entity(
        source=address_only_source, candidates=(address_only_candidate,)
    )

    assert name_result.outcome == EntityResolutionOutcome.REVIEW_REQUIRED
    assert name_result.selected_candidate_id is None
    assert address_result.outcome == EntityResolutionOutcome.REVIEW_REQUIRED
    assert address_result.selected_candidate_id is None
    assert "INSUFFICIENT_CORROBORATION" in name_result.reason_codes
    assert "INSUFFICIENT_CORROBORATION" in address_result.reason_codes


def test_two_near_equal_candidates_require_review_instead_of_arbitrary_selection() -> None:
    service = OnboardingIntelligenceService()
    source = identity(candidate_id="source", registration_number=None)
    first = identity(candidate_id="candidate-a", registration_number=None)
    second = identity(
        candidate_id="candidate-b",
        registration_number=None,
        address="1 Marina Boulevard, Singapore 018989",
    )

    result = service.resolve_entity(source=source, candidates=(first, second))

    assert result.outcome == EntityResolutionOutcome.REVIEW_REQUIRED
    assert result.selected_candidate_id is None
    assert result.reason_codes == ("AMBIGUOUS_TOP_CANDIDATES",)
    assert [item.candidate_id for item in result.candidates] == [
        "candidate-a",
        "candidate-b",
    ]


def test_entity_resolution_uses_case_bound_weights_and_thresholds() -> None:
    default = legacy_intelligence_policy_snapshot()
    policy = IntelligencePolicySnapshot(
        **default.model_dump(
            exclude={"entity_resolution_auto_match_threshold", "entity_resolution_weights"}
        ),
        entity_resolution_auto_match_threshold=Decimal("0.999"),
        entity_resolution_weights=EntityResolutionWeights(
            identifier=Decimal("0.10"),
            name=Decimal("0.40"),
            address=Decimal("0.30"),
            legal_form=Decimal("0.10"),
            incorporation_date=Decimal("0.10"),
        ),
    )
    source = identity(candidate_id="source", registration_number=None)
    candidate = identity(
        candidate_id="candidate",
        registration_number=None,
        address="1 Marina Boulevard Singapore 018980",
    )

    result = OnboardingIntelligenceService().resolve_entity(
        source=source,
        candidates=(candidate,),
        policy=policy,
    )

    assert result.outcome == EntityResolutionOutcome.REVIEW_REQUIRED
    assert result.selected_candidate_id is None
    weights = {item.name: item.weight for item in result.candidates[0].features}
    assert weights["LEGAL_NAME_SIMILARITY"] == Decimal("0.40")
    assert weights["REGISTERED_ADDRESS_SIMILARITY"] == Decimal("0.30")


def ownership_candidate(
    *, classification: OwnershipCandidateClassification, aggregated: str
) -> OwnershipCandidate:
    threshold_result = (
        OwnershipThresholdResult.MET
        if classification == OwnershipCandidateClassification.PROVISIONAL_UBO_CANDIDATE
        else OwnershipThresholdResult.NOT_MET
    )
    return OwnershipCandidate(
        party=Party(
            party_id="PERSON-1",
            display_name="Synthetic Owner",
            party_type=PartyType.NATURAL_PERSON,
            country="SG",
        ),
        direct_ownership_percent=Decimal(aggregated),
        indirect_ownership_percent=Decimal("0"),
        aggregated_ownership_percent=Decimal(aggregated),
        threshold_percent=Decimal("25"),
        threshold_comparator="GREATER_THAN_OR_EQUAL_TO",
        threshold_result=threshold_result,
        classification=classification,
        paths=[],
    )


def test_ubo_advice_consumes_deterministic_result_and_carries_non_legal_label() -> None:
    result = OnboardingIntelligenceService().advise_ubo(
        ownership_candidate(
            classification=OwnershipCandidateClassification.PROVISIONAL_UBO_CANDIDATE,
            aggregated="40",
        )
    )

    assert result.label == UboAdviceLabel.LIKELY_UBO
    assert result.probability == Decimal("0.800000")
    assert result.assistance_label == "ML_ASSISTED"
    assert result.disclaimer == "NOT_LEGAL_UBO_DETERMINATION"
    assert result.authoritative_ownership_percent == Decimal("40")
    assert result.model_version == "ubo-advisory-linear-v1"


def test_ubo_advice_uses_case_bound_advisory_thresholds() -> None:
    default = legacy_intelligence_policy_snapshot()
    policy = IntelligencePolicySnapshot(
        **default.model_dump(
            exclude={"ubo_advisory_likely_threshold", "ubo_advisory_unlikely_threshold"}
        ),
        ubo_advisory_likely_threshold=Decimal("0.90"),
        ubo_advisory_unlikely_threshold=Decimal("0.10"),
    )
    result = OnboardingIntelligenceService().advise_ubo(
        ownership_candidate(
            classification=OwnershipCandidateClassification.PROVISIONAL_UBO_CANDIDATE,
            aggregated="40",
        ),
        policy=policy,
    )

    assert result.probability == Decimal("0.800000")
    assert result.label == UboAdviceLabel.REVIEW


def test_indeterminate_ownership_is_review_not_a_guessed_probability() -> None:
    candidate = ownership_candidate(
        classification=OwnershipCandidateClassification.PROVISIONAL_UBO_CANDIDATE,
        aggregated="40",
    ).model_copy(
        update={
            "classification": OwnershipCandidateClassification.INDETERMINATE,
            "threshold_result": OwnershipThresholdResult.INDETERMINATE,
        }
    )

    result = OnboardingIntelligenceService().advise_ubo(candidate)

    assert result.label == UboAdviceLabel.REVIEW
    assert result.probability is None
    assert result.reason_codes == ("DETERMINISTIC_RESULT_INDETERMINATE",)


def test_mock_risk_is_bounded_advisory_and_exposes_missing_signals() -> None:
    service = OnboardingIntelligenceService()
    result = service.assess_mock_risk(
        MockRiskInputs(
            entity_resolution_outcome=EntityResolutionOutcome.REVIEW_REQUIRED,
            document_exception_count=2,
            ownership_issue_count=None,
        )
    )

    assert result.score == 65
    assert result.band == MockRiskBand.HIGH
    assert result.label == "MOCK_ADVISORY_RISK"
    assert result.disclaimer == "NOT_COMPLIANCE_DECISION"
    assert result.blocks_readiness is False
    assert result.signal_assessments["ownership"] == "NOT_ASSESSED"
    assert {"pep", "sanctions", "adverse_media"}.issubset(result.not_assessed_signals)


def test_mock_risk_with_too_little_evidence_is_not_assessed_not_zero() -> None:
    result = OnboardingIntelligenceService().assess_mock_risk(
        MockRiskInputs(
            entity_resolution_outcome=None,
            document_exception_count=None,
            ownership_issue_count=0,
        )
    )

    assert result.score is None
    assert result.band == MockRiskBand.NOT_ASSESSED
    assert result.signal_assessments["entity_resolution"] == "NOT_ASSESSED"
    assert result.signal_assessments["document"] == "NOT_ASSESSED"


def test_mock_risk_uses_case_bound_band_thresholds() -> None:
    default = legacy_intelligence_policy_snapshot()
    policy = IntelligencePolicySnapshot(
        **default.model_dump(exclude={"mock_risk_medium_threshold", "mock_risk_high_threshold"}),
        mock_risk_medium_threshold=20,
        mock_risk_high_threshold=80,
    )
    result = OnboardingIntelligenceService().assess_mock_risk(
        MockRiskInputs(
            entity_resolution_outcome=EntityResolutionOutcome.REVIEW_REQUIRED,
            document_exception_count=2,
            ownership_issue_count=None,
        ),
        policy=policy,
    )

    assert result.score == 65
    assert result.band == MockRiskBand.MEDIUM


def test_mock_risk_reports_case_bound_readiness_review_flag_without_deciding_readiness() -> None:
    default = legacy_intelligence_policy_snapshot()
    policy = IntelligencePolicySnapshot(
        **default.model_dump(exclude={"mock_risk_blocks_readiness"}),
        mock_risk_blocks_readiness=True,
    )
    result = OnboardingIntelligenceService().assess_mock_risk(
        MockRiskInputs(
            entity_resolution_outcome=EntityResolutionOutcome.CONFLICT,
            document_exception_count=1,
            ownership_issue_count=1,
        ),
        policy=policy,
    )

    assert result.band == MockRiskBand.HIGH
    assert result.blocks_readiness is True
    assert result.disclaimer == "NOT_COMPLIANCE_DECISION"


def _entity_feature(
    name: ResolutionFeatureName,
    *,
    agreement: str | None,
) -> ResolutionFeatureEvidence:
    return ResolutionFeatureEvidence(
        name=name,
        assessment=(
            FeatureAssessment.NOT_ASSESSED
            if agreement is None
            else FeatureAssessment.ASSESSED
        ),
        agreement=Decimal(agreement) if agreement is not None else None,
        weight=Decimal("0.20"),
    )


def test_entity_result_rejects_selected_candidate_for_no_match() -> None:
    with pytest.raises(ValidationError, match="selected candidate"):
        EntityResolutionResult(
            outcome=EntityResolutionOutcome.NO_MATCH,
            selected_candidate_id="ghost",
            candidates=(),
            reason_codes=("NO_CANDIDATES",),
        )


def test_entity_result_rejects_selected_candidate_outside_candidate_set() -> None:
    features = tuple(
        _entity_feature(name, agreement="1") for name in ResolutionFeatureName
    )
    candidate = EntityCandidateEvidence(
        candidate_id="candidate",
        probability=Decimal("1"),
        assessed_weight=Decimal("1"),
        corroborating_feature_count=4,
        features=features,
        top_contributing_features=(ResolutionFeatureName.LEGAL_NAME_SIMILARITY,),
    )
    with pytest.raises(ValidationError, match="candidate set"):
        EntityResolutionResult(
            outcome=EntityResolutionOutcome.EXACT_MATCH,
            selected_candidate_id="ghost",
            candidates=(candidate,),
            reason_codes=("EXACT_IDENTIFIER_AND_COUNTRY",),
        )


def test_entity_result_rejects_no_match_with_exact_identifier_evidence() -> None:
    features = tuple(
        _entity_feature(name, agreement="1") for name in ResolutionFeatureName
    )
    candidate = EntityCandidateEvidence(
        candidate_id="candidate",
        probability=Decimal("1"),
        assessed_weight=Decimal("1"),
        corroborating_feature_count=4,
        features=features,
        top_contributing_features=(
            ResolutionFeatureName.REGISTRATION_NUMBER_AND_COUNTRY,
        ),
    )

    with pytest.raises(ValidationError, match="exact identity evidence"):
        EntityResolutionResult(
            outcome=EntityResolutionOutcome.NO_MATCH,
            selected_candidate_id=None,
            candidates=(candidate,),
            reason_codes=("WEIGHTED_EVIDENCE_BELOW_THRESHOLD",),
        )


def test_ubo_result_rejects_label_probability_and_ownership_contradiction() -> None:
    with pytest.raises(ValidationError):
        UboAdviceResult(
            party_id="",
            probability=None,
            label=UboAdviceLabel.LIKELY_UBO,
            authoritative_ownership_percent=Decimal("0"),
            reason_codes=("CONSUMES_DETERMINISTIC_OWNERSHIP_RESULT",),
        )


def test_mock_risk_rejects_score_band_and_signal_contradictions() -> None:
    with pytest.raises(ValidationError):
        MockRiskAssessment(
            score=100,
            band=MockRiskBand.LOW,
            signal_assessments={
                "entity_resolution": "NOT_ASSESSED",
                "document": "NOT_ASSESSED",
                "ownership": "NOT_ASSESSED",
            },
            reason_codes=("INSUFFICIENT_AVAILABLE_SIGNALS",),
            not_assessed_signals=frozenset(),
        )


def test_mock_risk_rejects_unknown_limitation_name() -> None:
    with pytest.raises(ValidationError):
        MockRiskAssessment(
            score=0,
            band=MockRiskBand.LOW,
            signal_assessments={
                "entity_resolution": "0",
                "document": "0",
                "ownership": "0",
            },
            reason_codes=("ENTITY_EXACT_MATCH",),
            not_assessed_signals=frozenset(
                {"pep", "sanctions", "unexpected_external_signal"}
            ),
        )


def test_completed_demo_exposes_case_scoped_safe_intelligence_projection() -> None:
    application = create_app(ordinary_test_settings(demo_controls_enabled=True))
    team_a = RawTestClient(application)
    team_b = RawTestClient(application)
    login_a = team_a.post(
        "/api/auth/login", json={"user_id": "maya-lim", "password": TEST_PASSWORD}
    )
    login_b = team_b.post(
        "/api/auth/login", json={"user_id": "sophia-ng", "password": TEST_PASSWORD}
    )
    assert login_a.status_code == login_b.status_code == 200
    created = team_a.post(
        "/api/demo/clm/zero-touch/cases",
        headers={"X-CSRF-Token": login_a.json()["csrf_token"]},
        json={"uen": "202400001A", "scenario": "SME_STRAIGHT_THROUGH"},
    )
    assert created.status_code == 201
    case_id = created.json()["case"]["case_id"]
    completed = team_a.post(
        f"/api/demo/clm/zero-touch/cases/{case_id}/documents",
        headers={
            "X-CSRF-Token": login_a.json()["csrf_token"],
            "Content-Type": "application/pdf",
            "X-Document-Name": "synthetic.pdf",
        },
        content=PDF,
    )
    assert completed.status_code == 200

    response = team_a.get(f"/api/clm/zero-touch/cases/{case_id}/intelligence")

    assert response.status_code == 200
    body = response.json()
    assert body["model_bundle_version"] == "onboarding-intelligence-v1"
    assert body["entity_resolution"]["outcome"] == "NO_MATCH"
    assert body["ubo_advice"][0]["assistance_label"] == "ML_ASSISTED"
    assert body["ubo_advice"][0]["disclaimer"] == "NOT_LEGAL_UBO_DETERMINATION"
    assert body["mock_risk"]["label"] == "MOCK_ADVISORY_RISK"
    assert body["mock_risk"]["disclaimer"] == "NOT_COMPLIANCE_DECISION"
    assert "display_name" not in response.text
    assert "registered_address" not in response.text
    activity = team_a.get(f"/api/clm/zero-touch/activity?case_id={case_id}")
    assert activity.status_code == 200
    intelligence_events = [
        item
        for item in activity.json()["items"]
        if item["event_type"] == "INTELLIGENCE_EVALUATED"
    ]
    assert len(intelligence_events) == 1
    assert intelligence_events[0]["code"] == "ONBOARDING_INTELLIGENCE_V1"
    assert "policy catalogue" in intelligence_events[0]["message"].lower()

    inaccessible = team_b.get(f"/api/clm/zero-touch/cases/{case_id}/intelligence")
    assert inaccessible.status_code == 404


def test_sme_ambiguous_entity_scenario_stops_before_target_with_explainable_review() -> None:
    application = create_app(ordinary_test_settings(demo_controls_enabled=True))
    client = RawTestClient(application)
    login = client.post(
        "/api/auth/login", json={"user_id": "maya-lim", "password": TEST_PASSWORD}
    )
    assert login.status_code == 200
    csrf = login.json()["csrf_token"]
    created = client.post(
        "/api/demo/clm/zero-touch/cases",
        headers={"X-CSRF-Token": csrf},
        json={"uen": "202400001A", "scenario": "SME_AMBIGUOUS_ENTITY"},
    )
    assert created.status_code == 201
    case_id = created.json()["case"]["case_id"]

    paused = client.post(
        f"/api/demo/clm/zero-touch/cases/{case_id}/documents",
        headers={
            "X-CSRF-Token": csrf,
            "Content-Type": "application/pdf",
            "X-Document-Name": "synthetic.pdf",
        },
        content=PDF,
    )

    assert paused.status_code == 200
    assert paused.json()["status"] == "WAITING_FOR_REVIEW"
    assert paused.json()["current_stage"] == "READINESS"
    assert paused.json()["active_exceptions"][0]["exception_type"] == (
        "ENTITY_RESOLUTION_REVIEW_REQUIRED"
    )
    assert paused.json()["active_exceptions"][0]["available_actions"] == []
    intelligence = client.get(
        f"/api/clm/zero-touch/cases/{case_id}/intelligence"
    ).json()
    assert intelligence["entity_resolution"]["outcome"] == "REVIEW_REQUIRED"
    assert intelligence["entity_resolution"]["reason_codes"] == [
        "AMBIGUOUS_TOP_CANDIDATES"
    ]
    assert intelligence["mock_risk"]["disclaimer"] == "NOT_COMPLIANCE_DECISION"
@pytest.mark.parametrize(
    ("legal_form", "kyc_customer_type", "expected"),
    [
        (
            "Private company limited by shares",
            "Company - Private",
            ClassificationConsistencyStatus.COMPATIBLE,
        ),
        (
            "Private company limited by shares",
            "Association - Incorporated",
            ClassificationConsistencyStatus.OPERATOR_REVIEW,
        ),
        (
            "UNKNOWN",
            "Association - Incorporated",
            ClassificationConsistencyStatus.UNKNOWN_LEGAL_FORM,
        ),
    ],
)
def test_classification_consistency_is_advisory_without_inventing_policy(
    legal_form: str,
    kyc_customer_type: str,
    expected: ClassificationConsistencyStatus,
) -> None:
    advisory = assess_classification_consistency(
        legal_form=legal_form,
        kyc_customer_type=kyc_customer_type,
    )

    assert advisory.status == expected
    assert advisory.blocking is False
    assert advisory.authority == "PROJECT_ADVISORY_ONLY"
