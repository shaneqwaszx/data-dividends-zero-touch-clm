# Phase 04 Planner Handoff - Related Parties, Ownership Graph and Deterministic UBO Foundation

## Goal

Build a case-linked, source-neutral ownership-analysis sub-workflow without changing
the accepted onboarding or document-review workflows and without beginning Phase 05:

`existing case -> related parties -> ownership graph -> direct and indirect paths ->
effective ownership -> provisional ownership-based UBO candidates -> deterministic
human-readable calculation evidence`

Phase 04 is an **ownership-based UBO foundation** only. It must never claim a complete
legal or regulatory UBO/controller determination, compliance approval, GoldTier
approval, or Ready-for-Approval.

## Authority and unresolved sponsor boundary

- This handoff implements the detailed Phase 04 scope supplied on 2026-08-11.
- Q-002 (authoritative seeded hierarchy retrieval), Q-004 (final UBO rule/threshold),
  Q-006 (remaining direct related-party creation semantics), and Q-007 (final Singapore
  mappings/value lists) remain unresolved.
- The configured ownership threshold, inclusive comparator, graph limits, incomplete
  graph treatment, and synthetic scenarios are **PROJECT-DEFINED / PROVISIONAL**.
- Real GoldTier, hierarchy retrieval, related-party writes, PingFed, and live ACRA
  ownership are excluded. Provider architecture must remain replaceable.
- Conflicting sponsor evidence must be reconciled under `AGENTS.md`; no unresolved
  sponsor rule may be silently selected or represented as confirmed.

## Implementation scope

### Source-neutral domain and provider boundary

- Add `Party` with bounded `party_id`, `display_name`, `party_type` (`LEGAL_ENTITY` or
  `NATURAL_PERSON`), plus optional registration number and country for legal entities.
- Add `OwnershipRelationship` with bounded identifiers/endpoints, fixed-precision
  `Decimal` ownership percentage, ownership basis/type, and safe bounded provenance.
- Accept only `0 < ownership_percent <= 100`; reject zero, negative, non-finite, and
  over-100 values without clamping.
- Define a provider-neutral `OwnershipProvider` request/result. Generic domain,
  service, calculation, and API types must contain no Mock scenario.
- Implement a deterministic, credential-free, network-free `MockOwnershipProvider`.
  Demo scenario selection may exist only behind a dedicated Mock/demo control boundary.

### Graph construction, validation, and safety

- Build an immutable/source-neutral adjacency representation rooted at the onboarding
  legal entity. Support natural-person and legal-entity owners, multiple levels, and
  multiple independent paths to one natural person while preserving edge provenance.
- Do not mutate the canonical ACRA entity or Phase 03 document state.
- Validate root presence, unique party/relationship IDs, known endpoints, party types,
  percentage bounds, self edges, disconnected relationships, and cycles.
- Do not require ownership totals to equal 100% and never infer missing ownership.
- Apply configurable conservative project limits for maximum parties, relationships,
  traversal depth, and enumerated paths. Exceeding a safe limit must not silently
  truncate a supposedly definitive result; route to safe review/failure treatment.
- Cycle detection must terminate, exclude invalid cyclic paths from candidate results,
  retain safe diagnostics, and force `REVIEW_REQUIRED`/indeterminate analysis.

### Deterministic calculations and provisional classification

- Use `Decimal` throughout. A path's effective ownership is the product of edge
  fractions, expressed as a percent; e.g. `40% x 75% = 30%`.
- Retain ordered edge evidence and path effective ownership for every natural person.
- Aggregate each unique valid path exactly once. Report direct, indirect, and total
  effective ownership separately.
- Configure `UBO_OWNERSHIP_THRESHOLD_PERCENT`, default `25`, because no existing
  repository decision supersedes it. Use the provisional inclusive comparator
  `aggregated ownership >= configured threshold` pending Q-004.
- Classify natural persons only as `PROVISIONAL_UBO_CANDIDATE`,
  `BELOW_PROVISIONAL_THRESHOLD`, `REVIEW_REQUIRED`, or `INDETERMINATE` (or equivalent
  truthful typed names). Never classify a legal entity as a final UBO candidate.
- An unresolved legal-entity terminal, cycle, incomplete/ambiguous graph, or exceeded
  calculation limit must be exposed honestly and must not create a false candidate.
- Explanation strings, if used, must be deterministic presentations of stored
  calculation evidence. No LLM decides or generates authoritative ownership results.

### Case integration, lifecycle, audit, and failure handling

- Attach ownership analysis beneath an existing onboarding case as an independent
  sub-workflow. Preserve the parent case, canonical ACRA entity, and document records.
- Use clear states equivalent to `NOT_LOADED`, `LOADED`, `ANALYZING`,
  `REVIEW_REQUIRED`, `ANALYZED`, and `FAILED`. `ANALYZED` means calculation completed,
  never customer/KYC/compliance/GoldTier approval.
- Add fixed safe events for load start/completion, analysis start/completion,
  review-required, and failure. Audit content may contain safe IDs, status codes, and
  bounded counts, but not names, graph payloads, percentages, credentials, URLs,
  provider exception text, or KYC/PII.
- Once accepted/started, protect the complete pipeline: provider -> source validation ->
  graph construction -> graph validation -> path calculation -> aggregation ->
  threshold classification -> result construction -> persistence.
- Any unexpected post-acceptance failure must persist a retrievable terminal `FAILED`
  record with a fixed safe error, no partial false result, and no stranded
  `ANALYZING`, while preserving parent case and document state.

### Backend API and frontend

- Add only typed case-scoped endpoints required to load, analyze, retrieve ownership,
  and retrieve provisional UBO candidates. Unknown cases, missing loads, invalid
  requests, and cross-case access must fail safely.
- The generic ownership API must not expose Mock scenario selection. If needed, add a
  dedicated Mock/demo endpoint or local provider configuration boundary.
- Extend the current UI with an `Ownership & UBO` section showing root entity, direct
  owners, intermediate entities, natural persons, edge percentages, direct/indirect
  paths, aggregated ownership, provisional threshold/comparator, classification, and
  incomplete/cycle/failure warnings.
- A nested tree/table is sufficient. Labels must make the synthetic source and
  ownership-only provisional result unmistakable and explain why a person was marked.

### Synthetic Phase 04 scenarios

Implement fictional deterministic scenarios with these accepted outcomes:

1. `DIRECT_OWNER`: root -> 60% Person A and 40% Person B; both candidates at the
   default threshold.
2. `INDIRECT_OWNER`: root -> 40% Holding B; Holding B -> 75% Person C and 25% Person D;
   effective totals 30% and 10%, respectively.
3. `MULTIPLE_PATHS`: one person owns the root through at least two independent paths;
   unique valid paths aggregate exactly once.
4. `BELOW_THRESHOLD`: natural-person totals remain below the configured threshold.
5. `INCOMPLETE_CHAIN`: an unresolved legal-entity terminal produces review-required /
   indeterminate output, never false completion.
6. `CYCLE`: circular legal-entity ownership is detected, terminates safely, and
   produces review-required / indeterminate output with no false candidate.
7. `PROVIDER_FAILURE`: retrievable sanitized `FAILED`, with no stranded `ANALYZING`.

## Security and performance requirements

- Treat provider parties, relationships, identifiers, text, percentages, provenance,
  and errors as untrusted. Enforce schema, type, semantic, text/count/depth/path limits
  before calculation or browser projection.
- Provider-controlled provenance must be trimmed, nonblank, bounded, control-free, and
  limited to provider, environment, safe reference, and UTC sourcing timestamp.
- Never retain or expose credentials, authorization headers, raw source responses,
  private URLs, sponsor artefact content, raw provider exception text, or unnecessary
  PII. Keep Mock/sandbox/live labels truthful.
- Use iterative or depth-bounded traversal and explicit path limits so cyclic, deep,
  broad, or combinatorial input cannot cause unbounded recursion or path explosion.

## Required tests

- Domain/source validation: invalid percentages (zero, negative, over 100, NaN,
  infinity), duplicate IDs, unknown endpoints, self edges, malformed party types,
  disconnected relationships, unsafe/bad provenance, and configured graph limits.
- Direct/indirect calculation: direct natural-person ownership, two/three levels,
  exact Decimal arithmetic, stored edge/path evidence.
- Multiple paths: correct aggregation and no duplicate path counting.
- Threshold: below, exactly at, above, configurable threshold, inclusive provisional
  comparator.
- Graph safety: cycles, incomplete terminals, malformed/disconnected input, bounded
  depth/breadth/path count, no recursion or false candidate.
- Provider boundary: deterministic Mock behavior, scenario-free generic contracts,
  working non-Mock stub, malformed output rejection, safe provenance.
- Failure injection: graph construction, validation, traversal, aggregation,
  classification/result construction, clock, and recoverable repository update;
  retrievable `FAILED`, no stranded `ANALYZING`, no partial result, parent/document
  preservation.
- API: unknown case, not loaded, invalid typed request, case isolation, truthful
  responses.
- Frontend: section/tree/results render, direct and indirect paths, threshold label,
  candidate classification, incomplete/cycle/review and failure states.
- Preserve every Phase 01, Phase 02, and Phase 03 accepted scenario and invariant.

## Documentation

- Create `docs/architecture/PHASE_04_RELATED_PARTIES_UBO.md`.
- Create `docs/contracts/OWNERSHIP_UBO_PROFILE.md` documenting ownership-only scope,
  model, Decimal rules, multiplication/aggregation, provisional threshold/comparator,
  classifications, incomplete/cycle handling, provenance, graph limits, and all
  unresolved sponsor dependencies.
- Update decision/open-question records only to distinguish provisional project
  choices from sponsor-confirmed facts. Update README with simple Phase 04 demo steps.
- Evolve the POC regression catalogue only for the explicit verified scenarios above.

## Acceptance criteria

1. Source-neutral typed parties, ownership relationships, provenance, provider request/
   result, graph, path evidence, analysis, and candidate models enforce all bounds.
2. Mock scenarios are isolated to the demo/provider boundary and all generic business
   contracts accept a non-Mock provider without scenario knowledge.
3. Direct, indirect, three-level, and multiple-path ownership use deterministic Decimal
   arithmetic and retain complete path evidence with no duplicate counting.
4. The default 25% inclusive rule is configurable, prominently provisional, and never
   represented as sponsor-confirmed or as a complete legal UBO test.
5. Cyclic, incomplete, malformed, excessive, and disconnected graphs terminate safely,
   produce no false candidate, and route to review/failure according to documented
   project-defined rules.
6. Ownership load/analysis remains isolated under an existing case and never mutates
   the canonical ACRA entity, onboarding state, or document state.
7. Every post-acceptance unexpected failure terminalizes to retrievable sanitized
   `FAILED`, with no partial result or stranded nonterminal state.
8. Audit, API, persistence, and frontend projections minimize data and expose no raw
   payload, private exception, secret, confidential artefact, or misleading live claim.
9. The UI explains root/relationships/paths/effective totals/threshold/result and
   displays cycle, incomplete, review, failure, Mock, and provisional warnings.
10. Architecture, contract profile, decisions/questions, README, security review, and
    regression catalogue accurately document implemented and unresolved boundaries.
11. All configured backend, Ruff, strict mypy, contract/regression/Phase 01-04,
    adversarial/terminalization, secret, GoldTier validator, frontend type/test/build,
    dependency-integrity, and whitespace checks pass or are reported exactly.

## Explicit non-goals

Do not implement real GoldTier related-party writes or hierarchy retrieval, PingFed,
Ready-for-Approval, live ACRA ownership, final legal UBO/controller or control-by-other-
means analysis, trusts/nominees, sanctions/AML scoring, LLM decisions, autonomous
approval, durable database, queues/workers, Camunda, new jurisdictions, or Phase 05.

Do not stage, commit, push, merge, change branches, or begin Phase 05.
