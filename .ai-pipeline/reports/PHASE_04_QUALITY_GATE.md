# Phase 04 Quality Gate

## Executive Result

**PASS**

The final independent post-remediation gate found no remaining acceptance-blocking
defect in the bounded, credential-free Phase 04 ownership foundation. The six former
findings `P04-QG-001` through `P04-QG-006` were reproduced adversarially and are closed.
The complete local validation matrix passed, and all accepted Phase 01/02/03 behavior
remained unchanged.

This result approves only the source-neutral, provider-neutral, synthetic ownership
foundation and its project-defined provisional ownership-threshold calculation. It is
not evidence of a sponsor-approved legal UBO policy, live hierarchy interoperability,
real GoldTier readiness, compliance approval, or Ready-for-Approval.

## Phase 04 Acceptance Checklist

| Acceptance area | Result | Independent gate evidence |
|---|---|---|
| Source-neutral ownership model | PASS | Legal entities and natural persons are explicit; bounded identifiers, exact percentages, unique IDs, known endpoints, and non-self edges are enforced. |
| Provider-neutral retrieval | PASS | A non-Mock `LOCAL` provider was accepted by the unchanged generic service; Mock scenario selection remains in Mock/demo composition. |
| Deterministic graph construction | PASS | Owned-parent -> owner-child orientation is documented and enforced; adjacency and evidence ordering are deterministic. |
| Direct and indirect ownership | PASS | Independently reproduced 60%/40% direct ownership, 40% x 75% = 30%, 40% x 25% = 10%, and a three-edge 80% x 50% x 25% = 10% chain. |
| Multiple-path aggregation | PASS | Direct 20% plus indirect 20% produced 40%; an independent diamond produced two distinct 20%/10% paths and a 30% aggregate, each counted once. |
| Provisional classification | PASS | Exact Decimal comparison uses the configured threshold and inclusive `>=`; no hidden engine-level 25% rule was found. |
| Cycle/incomplete handling | PASS | Cyclic and unresolved legal-entity branches route to `REVIEW_REQUIRED`; retained valid-branch results become `INDETERMINATE / REVIEW_REQUIRED`. |
| Graph/path safety | PASS | Exact limits are accepted; limit+1 becomes safe review or failure without a definitive truncated classification. Traversal is iterative and bounded. |
| Safe terminalization | PASS | Recoverable failures persist one sanitized terminal failure; concurrent stale writes cannot replace terminal history. |
| Frontend truthfulness | PASS | Exact backend Decimal strings are displayed without `Number`, rounding, or classification recomputation; provisional/non-approval labels are visible. |
| Cross-phase regression | PASS | Phase 01: 28 passed; Phase 02: 80 passed; Phase 03: 59 passed; Phase 04: 77 passed. |
| Scope discipline | PASS | No live hierarchy, related-party write, PingFed, sanctions/AML, control-by-other-means, LLM UBO decision, autonomous approval, or Phase 05 implementation was found. |

## Ownership / UBO Contract Findings

### CRITICAL

None.

### HIGH

None.

### MEDIUM

None.

### LOW

None requiring a Phase 04 fix.

The implementation and documentation correctly separate the evidence classes:

1. **Sponsor-confirmed:** ACRA is the POC registry; `createRelatedParty` is limited to
   direct first-level behavior; multi-level hierarchy creation is unsupported; a seeded
   hierarchy is intended to be retrieved when an authoritative route exists; PingFed and
   TLS 1.3 are future GoldTier connection requirements.
2. **Project-defined / provisional:** owned-party -> owner edge orientation, Decimal
   multiplication and multiple-path aggregation, the default 25% threshold, inclusive
   `>=` comparator, six-decimal source/threshold precision, cycle/incomplete review
   treatment, graph limits, and synthetic classifications.
3. **Unresolved sponsor dependencies:** Q-002 hierarchy retrieval, Q-004 threshold and
   legal/controller policy, Q-006 related-party atomic-link semantics, and Q-007 final
   Singapore mappings/value lists.
4. **Synthetic/demo-only:** all Phase 04 graph data, names, source references, Mock
   provider behavior, and scenario selection.

No evidence conflict was silently reconciled. D-021 retains the provisional policy
boundary; D-022 records technical integrity remediation without claiming sponsor
confirmation. The code does not implement control by other means, classify a legal
entity as a natural-person UBO, invent a live hierarchy route, or invent a real
related-party write contract.

## Tester / Adversarial Findings

### Former finding closure

| Finding | Independent post-remediation result |
|---|---|
| `P04-QG-001` malformed natural-person parent | `ROOT -> PERSON_A -> PERSON_B`, a multi-level equivalent, and a mixed valid/malformed graph all ended `FAILED / OWNERSHIP_GRAPH_INVALID` with zero candidates. No reachable relationship was silently ignored. |
| `P04-QG-002` mutable provider trust bypass/private provenance | Existing validated metadata, party, and nested provenance objects were mutated with `object.__setattr__`; fresh reconstruction rejected each as `FAILED / OWNERSHIP_MALFORMED_SOURCE` and retained no provider graph. URI, query/token, fragment, userinfo, CR/LF, control, raw-JSON-like, and overlong references were all rejected. Browser records contained no `source_reference`. |
| `P04-QG-003` concurrent terminal overwrite | `FAILED -> stale ANALYZED`, `ANALYZED -> stale FAILED`, and terminal -> stale `ANALYZING` were rejected. Two barrier-synchronized analyze requests produced exactly one `ANALYZED` result and one `OWNERSHIP_ANALYSIS_CONFLICT`, with one start and one completion event. |
| `P04-QG-004` derived path-ID bound | Maximum 64-character relationship IDs at depth 8 and configured maximum depth 64 both produced deterministic 72-character `path-v1-<sha256>` identifiers while retaining all ordered edges and exact 25% evidence. Similar paths remain distinguishable. |
| `P04-QG-005` threshold precision mismatch | `25.000001` was accepted during `Settings` construction; `25.0000001` was rejected immediately. Service construction independently revalidates the same contract. |
| `P04-QG-006` misleading browser rounding | Source inspection found no binary numeric conversion in ownership display. Frontend tests preserved `24.9999995% / NOT_MET`, exactly 25%, above-threshold values, a long indirect Decimal, and a long multi-path aggregate. |

### Exact calculation evidence

- Direct graph: Person A = exactly 60% direct/aggregate; Person B = exactly 40%
  direct/aggregate; each has one direct path.
- Indirect graph: `40% x 75% = 30%` for Person C and `40% x 25% = 10%`
  for Person D, with ordered edge evidence.
- Three-edge graph: `80% x 50% x 25% = 10%`, retained as an indirect path.
- Multiple paths: Person A direct 20% plus `40% x 50% = 20%` indirect equals
  exactly 40%, with two unique paths.
- Independent diamond: two legal-entity branches converging on one natural person
  produced 20% plus 10% = exactly 30%, with two distinct paths.
- Configured threshold probe: the same 30% aggregate was `MET` at threshold 30 and
  `NOT_MET` at threshold 40, proving the engine does not hard-code 25.

### Invalidity and limit evidence

- Mixed valid plus cyclic and mixed valid plus incomplete graphs retained the valid
  person's evidence only as `REVIEW_REQUIRED / INDETERMINATE`, never as a provisional
  candidate.
- Exact depth was accepted; depth+1 produced `MAXIMUM_DEPTH_EXCEEDED` with no candidate.
- Exact total expansion and per-candidate path limits were accepted. Limit+1 produced
  `PATH_LIMIT_EXCEEDED`; every retained person result was non-definitive.
- Exact party and relationship counts were accepted. Count+1 failed closed as
  `OWNERSHIP_MALFORMED_SOURCE` with no candidate.
- Duplicate IDs, unknown endpoints, self-ownership, disconnected data, zero/negative/
  over-100/non-finite/excess-precision percentages, and unsafe provenance remain rejected
  by source/domain validation or safe graph validation.

## Code & Architecture Review

- Generic ownership request, provider metadata/result, domain, graph, service, and API
  calculation contracts do not depend on a Mock scenario. Mock selection is confined to
  `MockOwnershipProvider`, demo control, and the dedicated demo endpoint/UI.
- Provider-returned dictionaries, Pydantic instances, subclasses, nested models, and
  containers are recursively converted to primitives and freshly validated.
- Retained nested domain values are frozen and repository reads/writes use deep copies.
- Relationship direction is explicit: `parent_party_id` is the owned legal entity and
  `child_party_id` is its owner. Every edge parent must be `LEGAL_ENTITY`.
- Traversal uses an explicit stack, active-path visited sets, exact Decimal multiplication,
  ordered relationship-ID path keys, bounded digest presentation IDs, and exact Decimal
  aggregation.
- One-edge paths are direct; longer paths are indirect. Natural persons are terminal
  calculation subjects and legal entities are never emitted as final candidates.
- Repository creation is atomic and subsequent writes use expected-version compare-and-
  set. `FAILED`, `ANALYZED`, and `REVIEW_REQUIRED` are immutable terminal states.
- Ownership records remain isolated from the onboarding aggregate and Phase 03 documents.
- No accidental Phase 05 business implementation was found.

## Security Review

The requested integration-security review was applied to the ownership provider, API,
audit, browser, and future-integration boundaries.

- Provider name/reference/party/relationship values are bounded; Unicode controls,
  malformed identifiers, non-finite percentages, and mismatched provider provenance fail
  closed.
- Internal source references allow only short opaque ASCII identifiers and reject URI,
  userinfo, query, fragment, credential-like, whitespace/control, and raw-body syntax.
- The API/frontend omit `source_reference`; responses contain only the provider,
  environment, sourcing time, and synthetic evidence needed for explanation.
- Normal events contain fixed lifecycle text, safe IDs, statuses, and bounded counts,
  not graph dumps, relationship lists, names, percentages, credentials, URLs, raw
  provider payloads, or exception text.
- Failure projections use fixed safe codes/messages; private exception sentinels are not
  retained or returned. Partial candidates/issues are cleared on terminal failure.
- The Phase 04 provider is credential-free and network-free. No ACRA, GoldTier, or
  PingFed call occurs during ownership analysis.
- Secret scanner and five scanner tests passed. GoldTier validation retained the accepted
  `19 VALID / 19 INVALID-QUARANTINED / 48 NOT VALIDATED` classification without reading
  or promoting the quarantined authentication collection.

No active integration-security finding remains in the bounded Phase 04 scope. This is
not a production authorization/privacy review for real hierarchy data.

## Graph Safety / Path Explosion Review

- Configured defaults are 100 parties, 200 relationships, depth 8, 64 paths per natural
  person, and 256 traversal expansions/emitted paths.
- Party and relationship count checks occur before graph retention; traversal checks each
  expansion before adding more path evidence.
- Exact-limit graphs pass; limit+1 cannot silently truncate into `ANALYZED` with a
  definitive threshold result.
- Depth overflow, per-person path overflow, and total expansion overflow add safe issues
  and force the entire analysis to `REVIEW_REQUIRED`.
- Iterative traversal avoids recursion exhaustion. Active-path cycle detection prevents
  cyclic contributions while allowing independent valid evidence to remain reviewable.
- Fixed-size digest IDs prevent derived identifier growth at the supported depth-64
  boundary. Ordered edge evidence remains separate, preserving explainability and
  legitimate path distinction.

## Regression Results

### Independently reproduced outcomes

| Catalogue | Scenario | Actual outcome |
|---|---|---|
| Phase 01/02 | `202400001A` | `COMPLETED`; accepted ACRA -> search -> shell -> policy -> amend ordering |
| Phase 01/02 | `202400002B` | `REVIEW_REQUIRED / CANONICAL_DATA_INCOMPLETE`; no GoldTier calls |
| Phase 01/02 | `202400003C` | `FAILED / GT_POLICY_VALIDATION_FAILED`; no amend |
| Phase 01/02 | `202400004D` | `REVIEW_REQUIRED / GT_OPTIONAL_SECTION_REVIEW` |
| Phase 01/02 | `999999999Z` | `FAILED / ACRA_ENTITY_NOT_FOUND`; no GoldTier calls |
| Phase 03 | `ALL_FIELDS_MATCH`, `FIELD_MISMATCH`, `LOW_CONFIDENCE`, `MISSING_FIELD` | Each initially `REVIEW_REQUIRED` with four review fields and accepted event ordering |
| Phase 03 | `PROCESSOR_FAILURE` | Retrievable `FAILED / IDP_PROCESSING_FAILED`, zero fields, final failure event |
| Phase 04 | `DIRECT_OWNER` | `ANALYZED`; A 60%, B 40% |
| Phase 04 | `INDIRECT_OWNER` | `ANALYZED`; C 30% candidate, D 10% below |
| Phase 04 | `MULTIPLE_PATHS` | `ANALYZED`; A 20% direct + 20% indirect = 40% |
| Phase 04 | `BELOW_THRESHOLD` | `ANALYZED`; 20% and 15% both below |
| Phase 04 | `INCOMPLETE_CHAIN` | `REVIEW_REQUIRED / INCOMPLETE_LEGAL_ENTITY`; no candidate |
| Phase 04 | `CYCLE` | `REVIEW_REQUIRED / CYCLE_DETECTED`; no candidate |
| Phase 04 | `PROVIDER_FAILURE` | Retrievable `FAILED / OWNERSHIP_PROVIDER_FAILED`; no partial graph result |

Every independently probed ownership API response omitted `source_reference` and used the
deterministic four-event success/review lifecycle or two-event provider-failure lifecycle.

### Complete local checks

| Check | Result |
|---|---|
| Full backend Pytest | PASS — 244 tests collected and passed |
| Phase 01 focused regression | PASS — 28 |
| Phase 02 focused regression | PASS — 80 |
| Phase 03 focused regression | PASS — 59 |
| Phase 04 ownership/API tests | PASS — 77 |
| Ruff | PASS |
| Strict mypy | PASS — 39 source files |
| Repository unittest suite | PASS — 39 |
| Contract unittest suite | PASS — 29 |
| Secret scanner tests/script | PASS — 5 tests; scanner clean |
| GoldTier validator tests/classification | PASS — 5 tests; 19/19/48 baseline preserved |
| `pip check` | PASS — no broken requirements |
| `npm ls --all` | PASS — exit 0; platform/feature optional dependencies reported as optional only |
| Frontend typecheck | PASS |
| Frontend Vitest | PASS — 16 |
| Frontend production build | PASS — 28 modules; output written outside the repository |
| `git diff --check` | PASS |
| `git diff --cached --check` | PASS; no staged files |
| Untracked-file trailing whitespace scan | PASS |

Hosted GitHub Actions were **not invoked** during this local gate, as permitted by the
handoff. The configured local equivalents passed.

The regenerated `PHASE_04_INTEGRATION_SECURITY_REVIEW.md` and
`PHASE_04_POC_REGRESSION.md` explicitly acknowledge that the former independent gate
superseded their earlier PASS claims, enumerate all six former findings, and provide
post-remediation closure evidence. No superseded unqualified pre-remediation result
remains in either report.

## Accepted Phase 04 Technical Debt

- Storage, locking, idempotency, and audit history are process-local. A multi-process or
  durable deployment requires transactional persistence and a distributed concurrency
  boundary.
- The local POC has no user authentication/authorization, rate limiting, durable audit,
  reviewer identity, production retention policy, or real-data privacy approval.
- Source references are deliberately opaque and server-only. A real provider will need
  an approved provenance binding once Q-002 supplies the authoritative schema.
- Graph limits and the six-decimal source rule are conservative project safety defaults,
  not sponsor policy.
- The workflow display name in the hosted CI configuration still says Phase 03, although
  its full backend test command automatically collects Phase 04 and local equivalents all
  passed. This does not affect gate coverage or runtime behavior.
- The lightweight secret scanner covers supported current-worktree patterns, not history,
  archives, or entropy.

## Required Fixes Before Phase 05

None for Phase 04 implementation acceptance.

The following are not Phase 04 implementation fixes and do not block starting the next
bounded mock-first phase:

- **Live hierarchy verification:** Q-002 must supply the endpoint/schema, identifiers,
  pagination, and approved provenance behavior.
- **Sponsor-approved UBO policy:** Q-004 must confirm threshold(s), comparator,
  jurisdiction/policy variation, and the complete legal/controller test.
- **Real related-party integration:** Q-006 must confirm direct-link minimum fields and
  atomic persistence semantics; Q-007 must confirm Singapore mappings/value lists.
- **Real GoldTier integration:** Q-008 containment, fresh approved credentials, PingFed
  details, TLS/network binding, and real sandbox evidence remain required.

## Remaining Sponsor Dependencies

### Phase 04 implementation acceptance

No sponsor dependency blocks the bounded source/provider-neutral ownership foundation.
All sponsor-unknown behavior remains explicitly provisional or synthetic.

### Live hierarchy verification

**Q-002 — BLOCKED.** No authoritative GoldTier hierarchy retrieval endpoint/schema has
been supplied. No live route or response contract was invented.

### Sponsor-approved UBO policy

**Q-004 — NOT CONFIRMED.** The 25% threshold and inclusive `>=` comparator remain
project-defined/provisional. Ownership-only candidates are not complete legal UBO or
controller determinations.

### Real GoldTier integration

**Q-006/Q-007/Q-008 and environment access — NOT READY.** Direct related-party write
semantics, final Singapore mappings, sanitized authentication evidence, replacement
credentials, PingFed details, TLS/network configuration, and sandbox verification remain
outstanding. Phase 04 performs no such write or live call.

## Readiness

Phase 05 readiness:
**READY FOR PHASE 05**

Ownership foundation:
**READY**

UBO calculation foundation:
**READY**

Sponsor-approved UBO threshold:
**NOT CONFIRMED**

Live hierarchy integration:
**BLOCKED**

Real GoldTier integration:
**NOT READY**

## Git Status

- Branch: `phase/04-related-parties-ubo`
- HEAD: `60468e44fe80c78d003cf87b4adcc0fc2a51580c`
- Staged files: none
- Gate-authorized modification: this quality-gate report only
- Existing implementation worktree at final pre-report audit: 19 modified tracked files
  and 17 untracked files, including the Phase 04 implementation, tests, documentation,
  planner handoffs, and reports
- No application code or test was changed by this gate
- No files were staged, committed, pushed, or merged
- Phase 05 was not begun
