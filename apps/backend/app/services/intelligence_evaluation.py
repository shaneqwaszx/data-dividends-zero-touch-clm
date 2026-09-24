"""Versioned synthetic adverse-case evaluation for the advisory model bundle."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.onboarding_intelligence import (
    EntityIdentity,
    EntityResolutionOutcome,
    MockRiskBand,
    MockRiskInputs,
)
from app.domain.ownership import (
    OwnershipCandidate,
    OwnershipCandidateClassification,
    OwnershipThresholdResult,
    Party,
    PartyType,
)
from app.services.onboarding_intelligence import OnboardingIntelligenceService


def _identity(
    candidate_id: str,
    *,
    registration_number: str | None = "202400001A",
    country: str | None = "SG",
    legal_name: str | None = "Synthetic Merlion Labs Pte. Ltd.",
    legal_form: str | None = "PRIVATE_COMPANY_LIMITED_BY_SHARES",
    address: str | None = "1 Fictional Boulevard Singapore 018989",
    incorporated_on: date | None = date(2024, 1, 15),
) -> EntityIdentity:
    return EntityIdentity(
        candidate_id=candidate_id,
        registration_number=registration_number,
        country=country,
        legal_name=legal_name,
        legal_form=legal_form,
        registered_address=address,
        incorporated_on=incorporated_on,
        source_reference="SYNTHETIC_EVALUATION",
    )


def _ownership_candidate(
    party_id: str,
    percent: str,
    classification: OwnershipCandidateClassification,
    threshold_result: OwnershipThresholdResult,
) -> OwnershipCandidate:
    return OwnershipCandidate(
        party=Party(
            party_id=party_id,
            display_name="Synthetic Evaluation Owner",
            party_type=PartyType.NATURAL_PERSON,
            country="SG",
        ),
        direct_ownership_percent=Decimal(percent),
        indirect_ownership_percent=Decimal("0"),
        aggregated_ownership_percent=Decimal(percent),
        threshold_percent=Decimal("25"),
        threshold_comparator="GREATER_THAN_OR_EQUAL_TO",
        threshold_result=threshold_result,
        classification=classification,
        paths=[],
    )


def _agreement(results: list[tuple[str, str, str]]) -> dict[str, object]:
    matched = sum(actual == expected for _, expected, actual in results)
    return {
        "scenario_count": len(results),
        "expected_outcome_agreement": f"{matched}/{len(results)}",
        "scenarios": [
            {"name": name, "expected": expected, "observed": actual}
            for name, expected, actual in results
        ],
    }


def _ratio(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "NOT_APPLICABLE"
    return str((Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.000001")))


def _auto_match_metrics(results: list[tuple[str, str, str]]) -> dict[str, object]:
    automatic = {
        EntityResolutionOutcome.EXACT_MATCH.value,
        EntityResolutionOutcome.PROBABLE_MATCH.value,
    }
    true_positive = sum(
        expected in automatic and observed in automatic
        for _, expected, observed in results
    )
    false_positive = sum(
        expected not in automatic and observed in automatic for _, expected, observed in results
    )
    true_negative = sum(
        expected not in automatic and observed not in automatic for _, expected, observed in results
    )
    false_negative = sum(
        expected in automatic and observed not in automatic for _, expected, observed in results
    )
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    f1 = (
        "NOT_APPLICABLE"
        if precision == "NOT_APPLICABLE" or recall == "NOT_APPLICABLE"
        else _ratio(
            2 * true_positive,
            (2 * true_positive) + false_positive + false_negative,
        )
    )
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "true_negative": true_negative,
        "false_negative": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": _ratio(false_positive, false_positive + true_negative),
        "false_negative_rate": _ratio(false_negative, false_negative + true_positive),
    }


def evaluate_synthetic_intelligence_bundle() -> dict[str, object]:
    """Evaluate deterministic behavior; this is not production or population validation."""

    service = OnboardingIntelligenceService()
    source = _identity("SOURCE")
    descriptive_source = _identity("SOURCE", registration_number=None)
    name_only_source = _identity(
        "SOURCE",
        registration_number=None,
        legal_form=None,
        address=None,
        incorporated_on=None,
    )
    address_only_source = _identity(
        "SOURCE",
        registration_number=None,
        country="SG",
        legal_name=None,
        legal_form=None,
        incorporated_on=None,
    )
    name_legal_form_source = _identity(
        "SOURCE",
        registration_number=None,
        address=None,
        incorporated_on=None,
    )
    unicode_identifier_source = _identity(
        "SOURCE",
        registration_number="公司甲",
        legal_name=None,
        legal_form=None,
        address=None,
        incorporated_on=None,
    )
    unusable_identifier_source = _identity(
        "SOURCE",
        registration_number="---",
        legal_name=None,
        legal_form=None,
        address=None,
        incorporated_on=None,
    )
    entity_specs = (
        (
            "exact_identifier_country",
            EntityResolutionOutcome.EXACT_MATCH,
            source,
            (_identity("EXACT"),),
        ),
        (
            "punctuated_exact_identifier",
            EntityResolutionOutcome.EXACT_MATCH,
            source,
            (
                _identity(
                    "EXACT-PUNCTUATED",
                    registration_number="2024-00001a",
                    legal_name="Different synthetic name",
                    address="Different synthetic address",
                ),
            ),
        ),
        (
            "identifier_country_conflict",
            EntityResolutionOutcome.CONFLICT,
            source,
            (_identity("CONFLICT", country="AU"),),
        ),
        (
            "punctuation_suffix_abbreviation_probable",
            EntityResolutionOutcome.PROBABLE_MATCH,
            descriptive_source,
            (
                _identity(
                    "ABBREVIATED",
                    registration_number=None,
                    legal_name="SYNTHETIC MERLION LABS PRIVATE LTD",
                    address="1 Fictional Boulevard, Singapore 018989",
                ),
            ),
        ),
        (
            "reordered_address_probable",
            EntityResolutionOutcome.PROBABLE_MATCH,
            descriptive_source,
            (
                _identity(
                    "REORDERED-ADDRESS",
                    registration_number=None,
                    address="Singapore 018989, 1 Fictional Boulevard",
                ),
            ),
        ),
        (
            "same_name_different_identifier_no_match",
            EntityResolutionOutcome.NO_MATCH,
            source,
            (_identity("DIFFERENT-ID", registration_number="209999999Z"),),
        ),
        (
            "different_identifier_candidate_country_missing_no_match",
            EntityResolutionOutcome.NO_MATCH,
            source,
            (
                _identity(
                    "DIFFERENT-ID-NO-CANDIDATE-COUNTRY",
                    registration_number="209999999Z",
                    country=None,
                ),
            ),
        ),
        (
            "different_identifier_source_country_missing_no_match",
            EntityResolutionOutcome.NO_MATCH,
            _identity("SOURCE-NO-COUNTRY", country=None),
            (_identity("DIFFERENT-ID-NO-SOURCE-COUNTRY", registration_number="209999999Z"),),
        ),
        (
            "same_name_different_country_conflict",
            EntityResolutionOutcome.CONFLICT,
            descriptive_source,
            (_identity("DIFFERENT-COUNTRY", registration_number=None, country="AU"),),
        ),
        (
            "descriptive_probable",
            EntityResolutionOutcome.PROBABLE_MATCH,
            descriptive_source,
            (_identity("PROBABLE", registration_number=None),),
        ),
        (
            "address_only_review",
            EntityResolutionOutcome.REVIEW_REQUIRED,
            address_only_source,
            (
                _identity(
                    "ADDRESS-ONLY",
                    registration_number=None,
                    legal_name=None,
                    legal_form=None,
                    incorporated_on=None,
                ),
            ),
        ),
        (
            "name_plus_generic_legal_form_review",
            EntityResolutionOutcome.REVIEW_REQUIRED,
            name_legal_form_source,
            (
                _identity(
                    "NAME-LEGAL-FORM",
                    registration_number=None,
                    address=None,
                    incorporated_on=None,
                ),
            ),
        ),
        (
            "distinct_unicode_identifiers_no_match",
            EntityResolutionOutcome.NO_MATCH,
            unicode_identifier_source,
            (
                _identity(
                    "UNICODE-DIFFERENT",
                    registration_number="公司乙",
                    legal_name=None,
                    legal_form=None,
                    address=None,
                    incorporated_on=None,
                ),
            ),
        ),
        (
            "unusable_identifier_normalization_no_match",
            EntityResolutionOutcome.NO_MATCH,
            unusable_identifier_source,
            (
                _identity(
                    "UNUSABLE-ID",
                    registration_number="...",
                    legal_name=None,
                    legal_form=None,
                    address=None,
                    incorporated_on=None,
                ),
            ),
        ),
        (
            "name_only_review",
            EntityResolutionOutcome.REVIEW_REQUIRED,
            name_only_source,
            (
                _identity(
                    "NAME-ONLY",
                    registration_number=None,
                    legal_form=None,
                    address=None,
                    incorporated_on=None,
                ),
            ),
        ),
        (
            "ambiguous_tie_review",
            EntityResolutionOutcome.REVIEW_REQUIRED,
            descriptive_source,
            (
                _identity("TIE-A", registration_number=None),
                _identity("TIE-B", registration_number=None),
            ),
        ),
        ("no_candidates", EntityResolutionOutcome.NO_MATCH, source, ()),
    )
    entity_results = [
        (
            name,
            expected.value,
            service.resolve_entity(source=source_item, candidates=candidates).outcome.value,
        )
        for name, expected, source_item, candidates in entity_specs
    ]

    ubo_specs = (
        (
            "above_threshold",
            "LIKELY_UBO",
            _ownership_candidate(
                "OWNER-HIGH",
                "40",
                OwnershipCandidateClassification.PROVISIONAL_UBO_CANDIDATE,
                OwnershipThresholdResult.MET,
            ),
        ),
        (
            "below_threshold",
            "UNLIKELY_UBO",
            _ownership_candidate(
                "OWNER-LOW",
                "10",
                OwnershipCandidateClassification.BELOW_PROVISIONAL_THRESHOLD,
                OwnershipThresholdResult.NOT_MET,
            ),
        ),
        (
            "indeterminate_review",
            "REVIEW",
            _ownership_candidate(
                "OWNER-UNKNOWN",
                "0",
                OwnershipCandidateClassification.INDETERMINATE,
                OwnershipThresholdResult.INDETERMINATE,
            ),
        ),
    )
    ubo_results = [
        (name, expected, service.advise_ubo(candidate).label.value)
        for name, expected, candidate in ubo_specs
    ]

    risk_specs = (
        (
            "low_complete",
            MockRiskBand.LOW,
            MockRiskInputs(
                entity_resolution_outcome=EntityResolutionOutcome.EXACT_MATCH,
                document_exception_count=0,
                ownership_issue_count=0,
            ),
        ),
        (
            "low_below_medium",
            MockRiskBand.LOW,
            MockRiskInputs(
                entity_resolution_outcome=EntityResolutionOutcome.PROBABLE_MATCH,
                document_exception_count=1,
                ownership_issue_count=0,
            ),
        ),
        (
            "high_document_review",
            MockRiskBand.HIGH,
            MockRiskInputs(
                entity_resolution_outcome=EntityResolutionOutcome.REVIEW_REQUIRED,
                document_exception_count=2,
                ownership_issue_count=None,
            ),
        ),
        (
            "high_conflict",
            MockRiskBand.HIGH,
            MockRiskInputs(
                entity_resolution_outcome=EntityResolutionOutcome.CONFLICT,
                document_exception_count=1,
                ownership_issue_count=1,
            ),
        ),
        (
            "insufficient_not_assessed",
            MockRiskBand.NOT_ASSESSED,
            MockRiskInputs(
                entity_resolution_outcome=None,
                document_exception_count=None,
                ownership_issue_count=0,
            ),
        ),
    )
    risk_results = [
        (name, expected.value, service.assess_mock_risk(inputs).band.value)
        for name, expected, inputs in risk_specs
    ]

    entity = _agreement(entity_results)
    entity["auto_match_metrics"] = _auto_match_metrics(entity_results)
    ubo = _agreement(ubo_results)
    risk = _agreement(risk_results)
    return {
        "dataset": "synthetic-adverse-v3",
        "contains_real_customer_data": False,
        "model_bundle_version": "onboarding-intelligence-v1",
        "entity_resolution": entity,
        "ubo_advisory": ubo,
        "mock_risk": risk,
        "all_expected_outcomes_observed": all(
            expected == observed
            for results in (entity_results, ubo_results, risk_results)
            for _, expected, observed in results
        ),
        "limitations": (
            "Synthetic deterministic scenario agreement only; no population-level accuracy, "
            "fairness, calibration, live-provider, or sponsor validation claim."
        ),
    }
