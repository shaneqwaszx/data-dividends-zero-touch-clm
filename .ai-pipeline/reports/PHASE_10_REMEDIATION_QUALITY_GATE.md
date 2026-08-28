# Phase 10 Remediation Re-Quality Gate

Date: 2026-08-28
Branch: `phase/10-expanded-acra-registry-acquisition`
Accepted baseline / current HEAD: `2ca3ad67d16d7f6fa2e48b44bce37b909bf2b8f8`
Review type: independent, report-only remediation re-quality gate

## 1. Verdict

**PASS.** The original High aggregate-integrity defect is closed at
`RegistryAcquisitionBundle` itself. Direct model construction/revalidation now rejects
false `COMPLETE` states with missing, `EMPTY`, `FAILED`, or `NOT_ATTEMPTED` mandatory
ownership evidence. Valid `COMPLETE`, `PARTIAL`, and `FAILED` controls remain accepted.

There are no current Critical, High, Medium, or Low implementation findings in the
assigned remediation boundary. Phase 10 is ready for separately assigned
next-development planning; this review does not design or begin Phase 11.

## 2. Remediation Scope Reviewed

The planner, Phase 10 execution report, original quality-gate report, remediation
report, repository rules, project context, decisions, open questions, current working
tree, implementation, tests, API/frontend projection, architecture, and Mock contract
were reviewed independently.

The branch and HEAD remain unchanged from the original gate. Nothing is staged. The
working tree contains the full uncommitted Phase 10 implementation plus bounded
remediation. The tracked diff against the accepted baseline is 25 files, 1,995
insertions and 170 deletions, with the expected Phase 10 untracked files. The only file
created by this re-review is this report.

The remediation-owned changes were confirmed in:

- `apps/backend/app/domain/models.py`;
- `apps/backend/tests/test_phase10_registry_acquisition.py`;
- `docs/architecture/PHASE_10_EXPANDED_REGISTRY_ACQUISITION.md`;
- `docs/contracts/ACRA_MOCK_API_PROFILE.md`;
- `.ai-pipeline/reports/PHASE_10_REMEDIATION.md`.

No connector, orchestration, frontend, GoldTier, ownership-calculation, jurisdiction,
Mongo, dependency, schema, or migration change was introduced by the remediation.

## 3. Original High Finding Re-Test

**PH10-QG-001 — CLOSED.** A hand-built primitive payload was passed directly to
`RegistryAcquisitionBundle.model_validate(...)`, without invoking the acquisition
adapter/factory. This exact state raised `ValidationError`:

```text
overall              COMPLETE
ENTITY_PROFILE       COMPLETE / 1
OFFICERS             COMPLETE / 1
OWNERSHIP_PARTIES    NOT_ATTEMPTED / 0
RELATIONSHIPS        NOT_ATTEMPTED / 0
```

Direct variants with ownership `EMPTY`, relationships `EMPTY`, ownership `FAILED`, and
a blocking issue under overall `COMPLETE` also raised `ValidationError`. Because the
invalid aggregate cannot be constructed/revalidated, it cannot proceed through normal
serialization or browser projection as a successful acquisition.

## 4. COMPLETE Aggregate Invariants

**PASS.** The aggregate intrinsically requires the exact four-operation catalogue in
deterministic order. Entity profile must be `COMPLETE / 1`, its operation provenance
must match canonical source metadata, its requested/nonblank canonical identity must
agree, and its root party is deterministic.

Officers may be `COMPLETE` with matching non-empty evidence or legitimate `EMPTY / 0`.
Ownership parties and relationships must both be `COMPLETE`, non-empty, count-bound,
and internally referentially valid. `EMPTY`, `FAILED`, or `NOT_ATTEMPTED` mandatory
ownership operations are rejected. A complete bundle cannot retain any issue.

Positive direct controls passed for normal complete evidence and complete evidence with
empty officers.

## 5. PARTIAL Aggregate Invariants

**PASS.** `PARTIAL` requires a completed entity profile, no `FAILED` or
`NOT_ATTEMPTED` operation, valid complete/empty officer semantics, at least one empty
ownership-related operation, zero records behind each empty operation, and exactly one
`REGISTRY_EXPECTED_DATA_MISSING` issue.

Direct construction rejected fully complete evidence marked partial, a technical
failure marked partial, missing the expected issue, and evidence retained behind an
empty result. Legitimate missing-ownership and missing-relationship controls were
accepted.

## 6. FAILED / NOT_ATTEMPTED Invariants

**PASS.** `FAILED` requires exactly one technical failed operation with provenance and
a bounded error. Earlier operations form a valid `COMPLETE`/`EMPTY` prefix; every later
operation is `NOT_ATTEMPTED`. The sole bundle issue equals the failed operation error,
and the missing-data business code cannot masquerade as a technical failure.

`NOT_ATTEMPTED` requires count zero, no provenance, no error, and no corresponding
records. It occurs only after the failure in a failed bundle and is impossible under
overall `COMPLETE` or `PARTIAL`.

Direct construction rejected failed-without-failure, a completed operation after the
failure, retained records behind not-attempted state, and a failed result without its
safe error. Valid officer-failure and relationship-failure prefixes were accepted.

## 7. Operation Catalogue / Count Integrity

**PASS.** Missing, duplicated, incorrectly ordered, unknown, or extra operation results
are rejected. Each operation result count equals its normalized collection length.
Complete operations require evidence; empty, failed, and not-attempted operations
retain none.

Direct mismatches including one officer reported as count two, relationships count
mismatch, a nonzero empty count, and retained ownership/relationship evidence behind a
non-complete result were rejected.

## 8. Identity / Uniqueness / Provenance Assessment

**PASS.** Officer, ownership-party, and relationship IDs are unique. Relationship
endpoints must reference the deterministic root or an eligible legal-entity party and a
known owner, without self-edges. Every collection record provenance equals its
operation-result provenance. Attempted operations share the canonical provider and
environment, and bundle retrieval time equals the latest attempted-operation time.

Direct duplicate officer, record-operation mismatch, record-time mismatch,
cross-environment operation, incorrect bundle time, conflicting nonblank canonical
registration, and non-complete entity-result probes were rejected. Existing ownership
party/relationship uniqueness and reference defenses remain green. The deliberate
blank-canonical mapper-bypass case still reaches the accepted
`CANONICAL_DATA_INCOMPLETE` review defense; its focused seven-case regression passed.

**PH10-QG-002 — CLOSED.** The prior Medium identity/provenance weakness is now enforced
by the aggregate.

## 9. Direct Construction Adversarial Results

The independent, hand-built model probe produced:

```text
DIRECT_MODEL_PROBE PASS rejected=15 accepted_controls=5
```

The 15 rejected cases covered the exact original false complete, mandatory empty/failed
complete states, complete-with-issue, invalid partial/failed states, missing/order/count
integrity, duplicate officer identity, provenance/environment inconsistency, and
canonical identity conflict. The five accepted controls covered valid complete, empty
officers, missing-relationship partial, officer-failure prefix, and relationship
failure.

The authored focused file passed **52 tests**. The remediation adds **34 direct
construction cases** over the prior 18-test file; a name-based `-k directly` run
selected and passed **32**, while the two remaining direct failed-prefix tests have no
`directly` substring in their names.

**PH10-QG-003 — CLOSED.** Direct adversarial coverage and the aggregate contract are now
explicit.

## 10. Runtime Four-Operation Regression

**PASS.** A normal eligible Singapore Mock case produced exactly:

| Operation | Calls | Result |
|---|---:|---|
| `ENTITY_PROFILE` | 1 | `COMPLETE / 1` |
| `OFFICERS` | 1 | `COMPLETE / 1` |
| `OWNERSHIP_PARTIES` | 1 | `COMPLETE / 2` |
| `RELATIONSHIPS` | 1 | `COMPLETE / 2` |

Reading the retained case did not reacquire evidence. There was no retry, duplicate,
hidden call, or collapse back to one monolithic connector request.

## 11. Empty / Partial / Failure Runtime Regression

**PASS.** Empty officers remain `OFFICERS = EMPTY` with overall `COMPLETE` when required
ownership evidence is complete.

Missing ownership and missing relationships remain `PARTIAL /
REGISTRY_EXPECTED_DATA_MISSING`, stop for Registry review, and make zero IDP, ownership
analysis, and GoldTier calls. No graph or UBO result is fabricated.

Malformed/unavailable relationship paths remain technical `FAILED` outcomes with safe
fixed codes/messages and zero downstream progression. An officer identity failure
produces `COMPLETE, FAILED, NOT_ATTEMPTED, NOT_ATTEMPTED`, proving the earlier-failure
prefix. Raw malformed response content was absent from the retained case/API.

## 12. Phase 09 Call-Stopping Regression

**PASS.** The 39-test Phase 09 adversarial suite and the Phase 10 four-operation counter
confirmed these exact results:

| Blocker | Entity | Officers | Parties | Relationships | IDP | Ownership | GoldTier |
|---|---:|---:|---:|---:|---:|---:|---:|
| `JURISDICTION_UNRESOLVED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `JURISDICTION_CONFLICT` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `REGISTRY_PROVIDER_NOT_IMPLEMENTED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `REGISTRY_IDENTIFIER_NOT_ELIGIBLE` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

All four blockers retain no acquisition bundle, no document/ownership result, and only
not-attempted target operations.

## 13. Ownership Integration Assessment

**PASS.** The architecture remains:

```text
RegistryAcquisitionBundle
  -> RegistryAcquisitionOwnershipProvider
  -> Party / OwnershipRelationship
  -> OwnershipAnalysisService
```

The registry provider performs only bounded graph translation. It contains no path
traversal, direct/indirect aggregation, threshold calculation, UBO classification, or
separate cycle logic. The existing Decimal engine remains authoritative. Registry-fed
direct and synthetic multi-level/multiple-owner cases normalize successfully; existing
direct, indirect, multiple-path, cycle, and incomplete-evidence regressions passed.
The explicit registry-cycle case remains `REVIEW_REQUIRED / CYCLE_DETECTED` through the
existing ownership service.

## 14. Mock / Sandbox Truthfulness

**PASS.** Expanded operations remain project-owned synthetic Mock contracts. The UI and
documentation label them as synthetic and not verified live ACRA. The sandbox-shaped
entity operation is unchanged; officers, ownership parties, and relationships raise a
safe unavailable error immediately because Q-012 supplies no authoritative endpoint or
schema. No synthetic expanded data is returned as sandbox/live evidence, and no
operation is labelled live.

## 15. API / Frontend Regression

**PASS.** The aggregate now rejects impossible success before projection. The API
continues to expose backend-authored overall/operation states, counts, normalized
records, bounded provenance, and safe issues while excluding connector URLs,
authorization, configuration, raw bodies, provider objects, and exception text.

The frontend renders all four statuses/counts, distinguishes empty/partial/failed/not
attempted states, shows the synthetic Mock/not-verified-live label, and renders no fake
ACRA panel for Phase 09 blockers. Typecheck, 48 tests, and the 29-module production
build passed without a redesign.

## 16. Security / Trust Boundary

**PASS.** Source DTOs remain strict, bounded, identity-bound, UTC-bound, and freshly
reconstructed from primitives. Collection maxima are 32 officers, 64 ownership
parties, and 128 relationships; the existing ownership graph/path limits remain a
second boundary. Provider/environment/provenance and relationship-reference checks now
survive direct aggregate construction.

No credentials, raw payloads, raw endpoints, headers, untrusted exception text, PII
logging, dynamic provider selection, or new logging was introduced. Sandbox credentials
remain backend-only `SecretStr` configuration. Secret unit tests and the repository
scanner passed. There are no Critical, High, or Medium security findings.

## 17. Mongo / Persistence Boundary

**PASS.** MongoDB remains an optional read-only connectivity diagnostic and is not
wired into application composition. Onboarding, documents, ownership, CLM, and
zero-touch repositories remain process-local in-memory stores. No acquisition Mongo
repository, schema, migration, or durable-state claim was added. The focused Mongo
suite passed 6 tests. Lack of durable persistence is accepted future work, not a Phase
10 failure.

## 18. GoldTier Regression

**PASS.** GoldTier remains Mock-only. Existing search, conditional shell, policy, and
amend ordering/call-stopping is unchanged. Phase 10 maps registry ownership evidence
only into the existing ownership graph and does not invent GoldTier fields,
`createRelationship`, hierarchy writes, or related-party writes. Expanded mappings
remain `TBD_SPONSOR`. Mock completion remains `MOCK_GOLDTIER_SUBMITTED`, not approval or
Ready-for-Approval.

Validator regressions passed 5 tests; fixture validation remained **19 valid, 19
invalid/quarantined, and 48 not validated**.

## 19. Full Test / Quality Results

| Independent check | Exact result |
|---|---|
| Phase 10 focused/adversarial | **52 passed**, one existing deprecation warning |
| Direct-name selection | **32 passed**; 34 net new direct cases in the file |
| Hand-built direct model probe | **15 invalid rejected; 5 valid accepted** |
| Phase 09 adversarial | **39 passed**, one existing deprecation warning |
| Focused zero-touch/UAT/input/provider | **197 passed**, four existing warnings |
| Full backend | **600 passed**, four existing warnings |
| Canonical-defense selection | **7 passed** |
| Full Phase 02 remediation file | **44 passed** |
| Mongo focused | **6 passed** |
| Ruff, no cache | **PASS** |
| Strict mypy, no incremental cache | **PASS**, 60 source files |
| Contract tests | **44 passed** |
| Secret-unit tests | **5 passed** |
| Repository secret scanner | **PASS**, no supported patterns |
| GoldTier validator tests | **5 passed** |
| GoldTier fixture validation | **PASS**, 19 valid / 19 quarantined / 48 not validated |
| Python dependency consistency | **PASS**, no broken requirements |
| Frontend dependency tree | **PASS**; expected optional packages absent |
| Frontend typecheck | **PASS** |
| Frontend tests | **48 passed** on the permissioned esbuild run |
| Frontend production build | **PASS**, 29 modules; temporary output removed |
| Delivery asset tests | **4 passed** |
| Windows/demo lifecycle | **13 passed in 176.546s**; owned processes stopped |
| `git diff --check` | **PASS**, line-ending notices only |
| `git diff --cached --check` | **PASS**, nothing staged |

The first sandboxed frontend test attempt failed only at process creation with the known
Windows `esbuild spawn EPERM`; the authoritative permissioned rerun passed all 48 tests.
The pre-existing inaccessible untracked
`apps/frontend/pytest-cache-files-89airr88/` directory remains uninspected and untouched;
no result depended on it.

## 20. Findings by Severity

### Critical

None.

### High

None. **PH10-QG-001 is closed.**

### Medium

None. **PH10-QG-002 and PH10-QG-003 are closed.**

### Low

None introduced or exposed by this remediation re-review.

## 21. Remaining Sponsor Dependencies / Technical Debt

- **Q-012 — OPEN.** Authoritative expanded ACRA operations, official schemas,
  authentication/access, limits/errors, TLS/mTLS/private-CA details, and live/sandbox
  verification remain blocked.
- **Q-015 — OPEN.** Jurisdiction evidence authority, source precedence, disagreement
  resolution, reviewer authority, and resolution/resume policy remain blocked.
- Accepted unchanged debt includes process-local persistence, Mock-only expanded
  registry/GoldTier behavior, provisional UBO and GoldTier mapping policy, the narrow
  synthetic Singapore identifier predicate, and existing upstream deprecation/
  adversarial serializer warnings.

These are explicit sponsor dependencies or later technical work, not remediation
failures. No sponsor question was silently resolved.

## 22. Next-Development Readiness

The Phase 10 remediation satisfies the aggregate-integrity gate. The original High and
both related Medium findings are closed with direct construction evidence and a fully
green required verification matrix. Next-development planning may begin only as a
separately assigned task. Phase 11 has not begun in this review.

PASS — READY FOR NEXT DEVELOPMENT PLANNING
