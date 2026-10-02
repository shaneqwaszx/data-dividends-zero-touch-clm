# ADR-008: bounded ownership evidence tagging

Status: proposed Phase 24 POC, pending independent review.

The explicit Phase 24 assignment needs semantic evidence tags while preserving the
existing Decimal ownership owner. No approved ML runtime, trained artifact or external
AI provider exists. Existing onboarding intelligence is advisory and deterministic;
it does not normalize original ownership-unit evidence.

Extend the registry normalizer to retain bounded original scalars and source-neutral
ownership evidence. OwnershipAnalysisService alone derives percentages, validates
graphs and applies the frozen case threshold. Add OwnershipEvidenceTagger only for
versioned semantic labels and reason codes. Deterministic rules are the baseline,
with ML_RUNTIME_NOT_AVAILABLE. An experimental model protocol remains unwired until
approved runtime/evaluation authority exists. Core onboarding never depends on it.

Do not interpret officers/directors as owners, roles as percentages or control UBOs,
capital currency as share units, row sums as denominators, or one UEN's capital as
another UEN's denominator. Missing class/unit/as-of authority leaves evidence
unquantified. No new dependency, cache, persistence, graph or authorization owner.

Additive optional scalar/evidence fields retain unknown defaults for historical schema
v7 records. Reads do not infer tags or rewrite historical records. Changed identity
must invalidate derived state through existing owners and preserve bounded history.
Verification requires focused adverse/compatibility/restart tests, affected broad
checks and independent review. No final legal UBO or Live/provider status changes.
