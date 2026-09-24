from __future__ import annotations

from app.services.intelligence_evaluation import evaluate_synthetic_intelligence_bundle


def test_synthetic_intelligence_evaluation_is_complete_and_deterministic() -> None:
    first = evaluate_synthetic_intelligence_bundle()
    second = evaluate_synthetic_intelligence_bundle()

    assert first == second
    assert first["dataset"] == "synthetic-adverse-v3"
    assert first["contains_real_customer_data"] is False
    assert first["entity_resolution"]["scenario_count"] == 17
    assert first["entity_resolution"]["expected_outcome_agreement"] == "17/17"
    assert first["entity_resolution"]["auto_match_metrics"] == {
        "true_positive": 5,
        "false_positive": 0,
        "true_negative": 12,
        "false_negative": 0,
        "precision": "1.000000",
        "recall": "1.000000",
        "f1": "1.000000",
        "false_positive_rate": "0.000000",
        "false_negative_rate": "0.000000",
    }
    assert first["ubo_advisory"]["scenario_count"] == 3
    assert first["ubo_advisory"]["expected_outcome_agreement"] == "3/3"
    assert first["mock_risk"]["scenario_count"] == 5
    assert first["mock_risk"]["expected_outcome_agreement"] == "5/5"
    assert first["all_expected_outcomes_observed"] is True
