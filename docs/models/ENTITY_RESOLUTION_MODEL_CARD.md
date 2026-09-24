# Entity Resolution Model Card

## Identity and purpose

- Model: `entity-resolution-linear-v1`
- Bundle: `onboarding-intelligence-v1`
- Status: local deterministic POC advisory; not a production or identity-authority model
- Purpose: rank a bounded provider-supplied candidate set and route ambiguity to human review.
- Prohibited uses: legal identity determination, all-to-all discovery, autonomous approval,
  production duplicate merging, or treating a name match as identity proof.

## Method and inputs

The implementation is an explainable weighted linear probability proxy inspired by
Fellegi-Sunter linkage practice. It has no executable serialized model and no external
runtime dependency. Exact normalized registration identifier plus country is evaluated
first and dominates descriptive similarity. Normalization retains Unicode alphanumeric
characters and treats values that lose all identifier content as unassessed. A same
identifier with a different country is a conflict; distinct usable identifiers cannot
auto-match. Descriptive features are legal-name similarity, registered-address
similarity, legal-form agreement, and incorporation-date agreement. Missing features
are `NOT_ASSESSED`, not disagreements.

The default project-defined weights are identifier/country `0.55`, legal name `0.25`,
address `0.10`, legal form `0.05`, and incorporation date `0.05`. They must total one.
The editable case-bound policies are `ENTITY_RESOLUTION_AUTO_MATCH_THRESHOLD` (`0.85`),
`ENTITY_RESOLUTION_REVIEW_THRESHOLD` (`0.60`), the ambiguity margin (`0.03`), and the
five weights. These values are not industry constants or sponsor-confirmed thresholds.

Output is one of `EXACT_MATCH`, `PROBABLE_MATCH`, `REVIEW_REQUIRED`, `NO_MATCH`, or
`CONFLICT`, with candidate ID, a bounded probability proxy, assessed weight, safe source
reference, feature evidence, top contributions, model version, and reason codes. Name,
address, or name plus generic legal-form agreement cannot automatically select a
candidate; near-equal top candidates require review.

## Data and evaluation

- Training data: none. Parameters are transparent project-defined POC defaults.
- Evaluation data: `synthetic-adverse-v3`; fictional, non-confidential, deterministic.
- Random seed: not applicable because neither fitting nor inference uses randomness.
- Reproduction: `python scripts/evaluate_onboarding_intelligence.py`.
- Last evaluated: 2026-09-24.

The 17-case synthetic set covers exact and punctuated identifiers, identifier-country
conflict, descriptive/punctuation/suffix/address variants, same-name different-ID with
complete or one-sided missing country, different-country cases, name-only, address-only,
name-plus-generic-legal-form, distinct Unicode identifiers, unusable identifier
normalization, tied candidates, and no candidates. Observed expected-outcome agreement
was `17/17`. For the automatic-match band
(`EXACT_MATCH` or `PROBABLE_MATCH`): precision `1.000000`, recall `1.000000`, F1
`1.000000`, false-positive rate `0.000000`, and false-negative rate `0.000000` (TP 5,
FP 0, TN 12, FN 0).

These are tiny synthetic scenario metrics, not population accuracy, fairness,
calibration, sponsor validation, or interoperability evidence. The key adverse boundary
is false-positive matching; any ambiguous, weak, duplicate-exact, or conflicting case is
routed to review.

## Governance and security

Only bounded canonical fields and safe references enter the projection. Persisted
outcome/evidence is revalidated against the immutable case thresholds and weights; an
exact, conflicting, or probable outcome cannot contradict its candidate evidence. The API omits
raw identity values, provider payloads, document bodies, and credentials. The result is
case-bound with the policy catalogue version and input fingerprint. Inaccessible cases
return the same 404 as absent cases. Human review remains the authority for ambiguity.
