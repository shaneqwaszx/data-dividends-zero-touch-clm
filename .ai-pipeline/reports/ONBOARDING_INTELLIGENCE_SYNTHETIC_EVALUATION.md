# Onboarding Intelligence Synthetic Evaluation

Date: 2026-09-24
Dataset: `synthetic-adverse-v3`
Bundle: `onboarding-intelligence-v1`
Real customer data: no
Reproduction: `python scripts/evaluate_onboarding_intelligence.py`

| Projection | Scenarios | Expected outcomes observed |
|---|---:|---:|
| Entity resolution | 17 | 17/17 |
| UBO advisory | 3 | 3/3 |
| Mock advisory risk | 5 | 5/5 |

Entity-resolution automatic-match confusion matrix: TP 5, FP 0, TN 12, FN 0.
Precision, recall, and F1 were `1.000000`; false-positive and false-negative rates were
`0.000000` on this small synthetic set.

The entity set includes distinct Unicode and unusable normalized identifiers,
same-name/different-identifier cases with complete or one-sided missing country,
different-country cases, weak name/legal-form and single-feature evidence, and
punctuation/suffix/reordered-address variants.

This evidence proves deterministic behavior for the named adverse fixtures only. It does
not establish population accuracy, probability calibration, fairness, production
fitness, sponsor approval, or live-provider interoperability.
