# Phase 04 Integration Security Review - Post-Remediation

## Result

**PASS for the bounded credential-free synthetic Phase 04 scope.**

The independent Phase 04 gate superseded the earlier PASS and identified three HIGH and
three MEDIUM findings. `P04-QG-001` through `P04-QG-006` now have direct adversarial
coverage and are closed in the implementation. No active CRITICAL, HIGH, MEDIUM, or LOW
finding remains within this process-local scope.

This is not production or live-integration approval. Q-002/Q-004/Q-006/Q-007 and real
ACRA/GoldTier/PingFed connectivity remain external dependencies.

## Trust and data flow reviewed

1. Backend settings validate the provisional threshold with the same finite six-decimal
   `(0, 100]` contract as ownership edges and cap nodes, relationships, depth, paths per
   candidate, and all traversal expansions.
2. The generic API supplies only an existing case ID. Scenario selection remains on the
   dedicated Mock demo route.
3. Provider metadata/results are untrusted whether returned as dictionaries, model
   instances, subclasses, or previously validated nested objects. The service recursively
   dumps them to primitive data and reconstructs fresh strict trusted models.
4. Frozen nested domain values and defensive repository copies prevent later provider
   mutation from changing retained data.
5. Graph business validation separately enforces the owned legal-entity parent -> owner
   child orientation before traversal. A natural-person parent edge fails the complete
   graph and clears definitive candidates.
6. Iterative traversal applies depth, per-candidate path, and total expansion/path caps.
   Ordered edge evidence remains readable while path IDs are fixed-size SHA-256 digests.
7. Repository creation and updates are protected by a process-local lock plus expected-
   version compare-and-set. Terminal records reject stale success, failure, intermediate,
   and event-history writes.
8. API relationship provenance contains provider, environment, and sourcing time only.
   The internal opaque source reference is absent from browser DTOs and frontend types.
9. The frontend presents authoritative Decimal strings lexically. It does not use binary
   `Number`, round across a threshold, or recompute classification.

## Gate finding closure

| Finding | Remediation | Direct verification |
|---|---|---|
| P04-QG-001 HIGH | Every relationship parent must resolve to `LEGAL_ENTITY`; malformed/mixed graphs terminalize with no candidates | Root, nested, mixed-validity, and multi-level natural-person-parent tests |
| P04-QG-002 HIGH | Fresh recursive primitive reconstruction; frozen nested models; opaque reference/provider grammars; browser reference removed | Mutated metadata, nested provenance, party, ID, percentage, subclass, URL/userinfo/query/fragment/token/body/length tests plus API minimization assertion |
| P04-QG-003 HIGH | Atomic create and expected-version compare-and-set; terminal versions immutable | Deterministic failed-then-stale-success, analyzed-then-stale-failure, two-analyze, duplicate-load, reentry, and final-event tests |
| P04-QG-004 MEDIUM | `path-v1-` SHA-256 digest over length-delimited ordered edge IDs | Maximum 64-character IDs at depth 8 and 64, stable same path, near-identical distinct paths, multi-path aggregation |
| P04-QG-005 MEDIUM | One six-decimal threshold/edge contract at settings and service construction | `0.000001`, `25.000001`, `100.000000` accepted; zero, seven decimals, and over-100 rejected before load |
| P04-QG-006 MEDIUM | Exact string-only ownership percentage formatting | Below/equal/above threshold, long indirect, and multi-path aggregate frontend tests |

## Provider/source and provenance controls

- IDs/provider names use bounded opaque ASCII grammars; names/text are trimmed, bounded,
  nonblank, and reject Unicode control categories.
- Internal `source_reference` permits only 1-128 ASCII letters, digits, dot, underscore,
  or hyphen. URI schemes, slash/userinfo/query/fragment syntax, raw JSON-like text,
  whitespace, controls, and compact/camel credential-like terms are rejected.
- Percentages are exact finite Decimal values above zero and at most 100, with no more
  than six source decimal places.
- UTC-aware sourcing time and metadata/provenance provider/environment agreement remain
  mandatory.
- Duplicate IDs, unknown/self endpoints, missing/non-legal root, root mismatch,
  disconnected data, natural-person parents, and configured source-count excess fail
  closed without retaining provider content.

## Denial-of-service and integrity controls

- Traversal is iterative rather than recursive.
- Active-path visited sets detect cycles and exclude circular paths.
- Defaults cap 100 parties, 200 relationships, depth 8, 64 paths per candidate, and 256
  traversal expansions/emitted paths.
- Limit excess routes to non-definitive review and never silently truncates into a
  provisional candidate.
- Digest path IDs remain bounded even at the configured maximum depth of 64 and maximum
  source relationship-ID length.
- Process-local compare-and-set prevents duplicate request work from corrupting terminal
  state or history. It is an integrity boundary, not a substitute for production
  database transactions, rate limiting, or worker isolation.

## Error, audit, API, and browser safety

- Stable public errors contain only fixed code/message and safe case/analysis/correlation
  IDs; raw provider/stage/repository text is not retained or projected.
- Audit events contain fixed messages, IDs, status, and bounded counts rather than names,
  percentages, graphs, payloads, source references, or exception text.
- Ownership responses expose fictional names and exact edge/path evidence required for
  human explanation, but omit internal source routing/reference data.
- Parent onboarding and Phase 03 document state remain isolated from ownership failures.
- Mock ownership remains explicit `MOCK`, credential-free, network-free, and is not live
  interoperability evidence.

## Severity findings

| Severity | Active finding |
|---|---|
| CRITICAL | None |
| HIGH | None |
| MEDIUM | None |
| LOW | None |

## Accepted Phase 04 limitations

- Local unauthenticated POC: no user authorization, rate limiting, durable database/audit,
  distributed lock, queue, reviewer identity, or production retention policy.
- Only fictional ownership data is authorized. Real hierarchy data requires privacy,
  access, retention, encryption, and frontend-minimization decisions.
- Process-local locking/versioning is correct for this API instance only; multi-process
  deployment would require a durable transactional version boundary.
- The secret scanner checks supported current-worktree patterns, not history, archives,
  or entropy.
- A future live provider requires HTTPS/certificate/auth/redirect/timeout/body-size/
  pagination/rate-limit and data-classification review. Real GoldTier additionally
  requires approved replacement authentication material, PingFed, TLS 1.3, and network
  binding.

## Verification evidence

- Full backend: 244 passed.
- Focused Phase 04 ownership/API: 77 passed.
- Repository unittest: 39 passed; contract: 29 passed.
- Ruff and strict mypy (39 source files): PASS.
- Frontend typecheck, 16 tests, and 28-module production build: PASS.
- Secret scanner/tests, dependency integrity, GoldTier validator regressions, and final
  whitespace/diff checks: PASS.

## Sponsor dependencies

- Q-002 blocks authoritative live hierarchy transport/schema/provenance binding.
- Q-004 blocks a sponsor-approved threshold/comparator/controller claim.
- Q-006 blocks real direct related-party write semantics.
- Q-007 blocks final Singapore GoldTier mappings/value lists.
- No sponsor evidence was changed or reinterpreted by this technical remediation.
