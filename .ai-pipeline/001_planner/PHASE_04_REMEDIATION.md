# Phase 04 Remediation Handoff

## Goal and authority

Close `P04-QG-001` through `P04-QG-006` from
`.ai-pipeline/reports/PHASE_04_QUALITY_GATE.md` without redesigning the accepted
source-neutral Phase 04 ownership architecture or beginning Phase 05.

This remediation preserves D-021 and the unresolved sponsor boundaries Q-002,
Q-004, Q-006, and Q-007. It does not change the project-defined provisional 25%
inclusive ownership threshold, introduce a sponsor-approved UBO rule, or implement
real ACRA/GoldTier hierarchy access, related-party writes, PingFed, legal controller
tests, Ready-for-Approval, durable infrastructure, or AI decisioning.

## Required remediations

### P04-QG-001: ownership-edge semantics

- Preserve the Phase 04 orientation `parent_party_id = owned party` and
  `child_party_id = owner`.
- Require every ownership relationship parent to resolve to `LEGAL_ENTITY` before
  definitive calculation.
- Reject malformed natural-person-parent graphs or route the complete result to an
  explicitly non-definitive review/indeterminate state.
- Never silently ignore a reachable relationship or retain definitive candidate
  classifications from an insufficiently valid mixed graph.
- Cover root/nested/mixed/multi-level natural-person-parent adversarial graphs.

### P04-QG-002: untrusted provider boundary and provenance

- Treat dictionaries, existing models, subclasses, and previously validated provider
  objects as untrusted.
- Reconstruct metadata and results through primitive data into fresh trusted models,
  deeply revalidating every nested party, relationship, and provenance value without
  retaining provider-owned mutable objects.
- Protect trusted retained models against later provider mutation.
- Redefine `source_reference` as a bounded opaque identifier. Reject URI schemes,
  userinfo, query strings, fragments, credential/token-like forms, controls, blank or
  overlong values, and JSON/body-like text.
- Remove source references from browser DTOs unless required for human explanation;
  retain only provider, environment, and sourcing time in the browser projection.
- Test mutated provider name, party text, relationship identifiers/percentages, nested
  provenance, unsafe private/query/token-like references, and API/UI non-projection.

### P04-QG-003: process-local concurrency and terminal finality

- Replace unconditional last-write-wins state changes with deterministic expected
  state/version semantics, using repository compare-and-set and/or case serialization.
- Terminal `FAILED`, `ANALYZED`, and `REVIEW_REQUIRED` records must be immutable to
  stale intermediate writes.
- Duplicate simultaneous load/analyze requests must have a documented deterministic
  result; exactly one invocation owns the accepted transition.
- Stale writes must not erase terminal events, restore `ANALYZING`, or swap one terminal
  result for another.
- Use deterministic barriers/events or repository seams for failed-then-success,
  success-then-failed, two-success, duplicate-load, terminal-reentry, and event-history
  tests.

### P04-QG-004: bounded path identifiers

- Preserve ordered relationship IDs as human-readable calculation evidence.
- Derive `path_id` as a deterministic bounded opaque digest of the ordered edge path.
- Identical paths must have identical IDs; different paths must have negligible
  collision risk and remain independently aggregatable.
- Verify maximum-length relationship IDs at default and configured maximum depth, near-
  identical paths, and multiple-path deduplication.

### P04-QG-005: threshold precision

- Use the existing ownership percentage contract end to end: finite Decimal,
  `0 < value <= 100`, at most six decimal places.
- Reject unsupported threshold precision in settings/composition before the first load.
- Align service construction, retained models, calculation, API, documentation, and
  exact configured-threshold tests.
- Preserve the provisional default `25` and inclusive `>=` comparator pending Q-004.

### P04-QG-006: exact browser Decimal presentation

- Keep authoritative ownership values as strings in frontend contracts.
- Format Decimal strings without conversion to JavaScript `Number` or classification-
  relevant rounding.
- Render exact below/equal/above threshold results, long indirect values, and multiple-
  path aggregates without recomputing classifications.

## Preserved behavior

- Provider-neutral contracts and Mock scenario isolation.
- Decimal direct/indirect path multiplication, ordered evidence, and unique-path
  aggregation.
- `DIRECT_OWNER`, `INDIRECT_OWNER`, `MULTIPLE_PATHS`, `BELOW_THRESHOLD`,
  `INCOMPLETE_CHAIN`, `CYCLE`, and `PROVIDER_FAILURE` outcomes.
- Configurable provisional threshold, cycle/incomplete review behavior, bounded
  traversal, safe terminal errors, browser explainability, no legal-entity final UBO,
  and no LLM decisioning.
- Phase 01/02/03 scenarios, case/document/ownership isolation, connector stopping,
  Mock/live labeling, and false Ready-for-Approval protections.

## Documentation and review evidence

Update only affected Phase 04 architecture, ownership profile, README, and decision
record sections. Document edge orientation, malformed-parent treatment, explicit
provider-to-trusted-model reconstruction, opaque provenance, browser minimization,
terminal concurrency semantics, digest path IDs, threshold precision, and exact Decimal
rendering. These are technical controls, not new sponsor policy.

After implementation stabilizes, rerun the integration security review and POC
regression check. Replace the superseded PASS claims in:

- `.ai-pipeline/reports/PHASE_04_INTEGRATION_SECURITY_REVIEW.md`
- `.ai-pipeline/reports/PHASE_04_POC_REGRESSION.md`

Direct coverage must include all six gate findings and the expanded adversarial cases.

## Required verification

Run the full backend suite, Ruff, strict mypy, contract tests, repository regressions,
focused Phase 01/02/03/04 suites, malformed-graph/provider-mutation/provenance/
deterministic-concurrency/path-bound/threshold-precision/frontend-exact-decimal tests,
graph and terminalization adversarial tests, secret scanner and tests, GoldTier
validators, frontend typecheck/tests/production build, `pip check`, `npm ls --all`,
tracked/cached diff checks, and untracked whitespace checks.

## Completion boundary

Stop after the bounded remediation and final evidence. Do not stage, commit, push,
merge, change branches, implement live integrations, or begin Phase 05. The next human
action is the final independent Phase 04 Quality Gate.
