# Mock Advisory Risk Model Card

## Identity and purpose

- Model: `mock-advisory-risk-rules-v1`
- Bundle: `onboarding-intelligence-v1`
- Permanent labels: `MOCK_ADVISORY_RISK` and `NOT_COMPLIANCE_DECISION`
- Purpose: demonstrate how available onboarding evidence could be summarized for human
  attention in a local POC.
- Prohibited uses: compliance decisions, regulatory risk rating, sanctions/PEP/adverse
  media conclusions, final approval, production customer treatment, or sponsor-policy
  claims.

## Method and inputs

The score uses only three available project signals: entity-resolution outcome,
document-exception count, and ownership-issue count. Contributions are bounded to a
0–100 integer. Missing signals are `NOT_ASSESSED`; fewer than two assessed groups produces
the `NOT_ASSESSED` band rather than zero risk. PEP, sanctions, adverse media, transaction
monitoring, and product/channel risk remain explicitly unassessed.

The editable case-bound band thresholds are project defaults: medium `30` and high `60`.
`MOCK_RISK_BLOCKS_READINESS` defaults to `false`. If a Director explicitly changes that
policy for a newly created case, a high result asks the existing readiness owner to create
a typed human-review stop before target execution. The risk model itself never owns or
mutates readiness. Q-017 remains unresolved, so this is not sponsor risk authority.

## Data and evaluation

- Training data: none; the rule table is transparent, data-only logic.
- Evaluation data: `synthetic-adverse-v3`, fictional and non-confidential.
- Random seed: not applicable; inference is deterministic.
- Last evaluated: 2026-09-24.
- Reproduction: `python scripts/evaluate_onboarding_intelligence.py`.

Expected-outcome agreement was `5/5` across complete low, below-medium low, document
review high, conflict high, and insufficient-evidence not-assessed cases. This is bounded
scenario evidence only—not calibration, production accuracy, fairness validation,
regulatory approval, or sponsor confirmation.

## Governance and security

The record contains safe contribution labels, reason codes, a closed bounded vocabulary
of unassessed-factor names, policy/model versions, and no raw provider or document
payload. Its thresholds and readiness flag must equal the immutable case policy. It is
access-controlled, case-bound, CAS-persisted, deleted with the case, and displayed with
its permanent non-compliance disclaimer.
