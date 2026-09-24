# UBO Advisory Model Card

## Identity and purpose

- Model: `ubo-advisory-linear-v1`
- Bundle: `onboarding-intelligence-v1`
- Labels: `ML_ASSISTED` and `NOT_LEGAL_UBO_DETERMINATION`
- Purpose: provide a transparent review aid over the existing deterministic ownership
  result.
- Prohibited uses: calculating ownership, replacing the Decimal graph engine, changing
  its provisional classification, making a legal UBO determination, or approving a case.

## Method and inputs

The owner consumes only a deterministic `OwnershipCandidate`. The current POC proxy is
the bounded aggregated-ownership percentage divided by 50, capped at `0.99`. The
project-defined, editable, case-bound thresholds are `0.65` for `LIKELY_UBO` and `0.35`
for `UNLIKELY_UBO`; values between them produce `REVIEW`. An indeterminate or
review-required deterministic result always produces `REVIEW` with no guessed
probability. Available output includes the authoritative Decimal percentage, proxy,
label, reasons, and version.

No title/controller, source-completeness, or relationship-evidence feature is fabricated
when the current ownership record does not provide an authoritative bounded value.

## Data and evaluation

- Training data: none; the transparent project-defined transform has no trained or
  serialized executable artifact.
- Evaluation data: `synthetic-adverse-v3`, fictional and non-confidential.
- Random seed: not applicable; the implementation is deterministic.
- Last evaluated: 2026-09-24.
- Reproduction: `python scripts/evaluate_onboarding_intelligence.py`.

Expected-outcome agreement was `3/3` across above-threshold, below-threshold, and
indeterminate cases. This is deterministic scenario coverage, not statistical accuracy,
probability calibration, fairness evidence, or a legal validation study.

## Human-review and authority boundary

The deterministic Decimal ownership graph and provisional threshold classification
remain authoritative. The advisory output is retained separately in the case envelope,
is safe-projected in the API/UI, and cannot mutate ownership. Policy changes affect only
newly bound cases. Persisted advisory thresholds must equal that immutable snapshot.
Disagreement or indeterminate evidence is a review suggestion only.
