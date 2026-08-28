# Phase 10 Quality Gate Remediation — Registry Aggregate Integrity

Date: 2026-08-28  
Branch: `phase/10-expanded-acra-registry-acquisition`  
Baseline / HEAD: `2ca3ad67d16d7f6fa2e48b44bce37b909bf2b8f8`  
Scope: bounded Phase 10 remediation only; no independent re-quality gate performed

## 1. Executive Summary

The High false-success finding is remediated. `RegistryAcquisitionBundle` now validates
its complete/partial/failed state matrix, operation execution prefix, evidence counts,
canonical identity, record uniqueness, and provenance consistency intrinsically. A
caller can no longer construct an overall `COMPLETE` bundle while mandatory ownership
parties or relationships are empty, failed, or not attempted.

The exact quality-gate counterexample now raises a Pydantic domain validation error.
Legitimate empty officers remain complete; expected missing ownership remains partial
and review-required; technical operation failures remain failed with later operations
not attempted. The normal Singapore Mock flow still calls each of the four operations
once, and all Phase 09 blockers still call every registry/downstream boundary zero
times.

Final verification passed 52 focused Phase 10 tests, 39 Phase 09 adversarial tests, 197
focused POC/provider regressions, and 600 full backend tests, plus all required static,
contract, frontend, security, dependency, GoldTier, delivery, lifecycle, and whitespace
checks.

## 2. Quality Gate Finding Addressed

**PH10-QG-001 — High — false `COMPLETE` acquisition:** closed by intrinsic aggregate
validation. `COMPLETE` now requires usable complete ownership-party and relationship
evidence and rejects `EMPTY`, `FAILED`, and `NOT_ATTEMPTED` mandatory operations.

The directly related Medium findings are also closed:

- **PH10-QG-002:** officer IDs are unique and each record's provenance must equal its
  operation result; all attempted results share the canonical source/environment.
- **PH10-QG-003:** 34 new direct aggregate construction cases exercise the state matrix,
  operation catalogue, counts, failure prefix, identity, and provenance. Architecture
  and Mock-contract documentation now state the enforced rules explicitly.

## 3. Root Cause

The ACRA adapter/factory calculated truthful runtime states, but the normalized domain
aggregate validated only the fixed operation order, selected count cases, relationship
references, broad failed-status presence, and minimal issue presence. It did not encode
the semantic matrix advertised by `status` or the operation prefix. Consequently, a
direct/internal/reconstructed caller could combine a `COMPLETE` aggregate status with
missing or unattempted ownership acquisition.

The correction is at the owning domain boundary rather than in connector sequencing,
orchestration, API projection, frontend logic, or ownership calculation.

## 4. Files Changed

Remediation changes are limited to:

- `apps/backend/app/domain/models.py` — aggregate invariants.
- `apps/backend/tests/test_phase10_registry_acquisition.py` — direct adversarial and
  valid-construction coverage.
- `docs/architecture/PHASE_10_EXPANDED_REGISTRY_ACQUISITION.md` — intrinsic state and
  trust-boundary rules.
- `docs/contracts/ACRA_MOCK_API_PROFILE.md` — exact aggregate contract.
- `.ai-pipeline/reports/PHASE_10_REMEDIATION.md` — this report.

The pre-existing uncommitted Phase 10 working tree was preserved. Nothing was staged,
committed, pushed, merged, rebased, stashed, reset, or cleaned. No connector, service,
API, frontend, GoldTier, UBO, jurisdiction, persistence, or configuration implementation
was changed by the remediation.

## 5. RegistryAcquisitionBundle Invariants

### COMPLETE

- Exactly one ordered result exists for entity profile, officers, ownership parties,
  and relationships.
- Entity profile is `COMPLETE / 1`, retains a usable canonical entity, and binds the
  source/result identity, environment, and retrieval time. A nonblank conflicting
  canonical registration number is rejected; an invalid blank canonical field still
  reaches the established canonical-review defense.
- Officers are `COMPLETE` with matching non-empty records or legitimate `EMPTY / 0`.
- Ownership parties and relationships are both `COMPLETE`, non-empty, and count-bound.
- No operation is failed/not-attempted and no issue is retained.

### PARTIAL

- Entity profile completed successfully.
- No operation is `FAILED` or `NOT_ATTEMPTED`.
- Officers retain the same complete/legitimate-empty rule.
- At least one ownership-related operation is `EMPTY`, so a fully usable ownership
  acquisition cannot claim partial missing data.
- Exactly one `REGISTRY_EXPECTED_DATA_MISSING` issue is retained.

### FAILED

- Exactly one operation is `FAILED` with provenance and a bounded safe technical error.
- Earlier operations form a truthful `COMPLETE`/`EMPTY` prefix.
- Every later operation is `NOT_ATTEMPTED`, carries zero records, and has no provenance
  or error.
- The sole bundle issue equals the failed operation's safe error; the missing-data
  business issue cannot masquerade as a technical failure.

### NOT_ATTEMPTED and shared consistency

- A not-attempted operation is allowed only after the one failed operation in an overall
  failed bundle and retains no source records.
- Every operation count equals the corresponding normalized collection length.
- Empty, failed, and not-attempted operations retain zero records.
- Officer, ownership-party, and relationship IDs are unique where applicable.
- Record provenance equals its operation-result provenance; attempted results agree
  with canonical provider/environment, and the bundle time equals the latest attempted
  operation time.
- Existing ownership-party and relationship endpoint/reference validation remains
  active.

## 6. Original Counterexample Re-Test

Direct construction was repeated with:

```text
overall              COMPLETE
ENTITY_PROFILE       COMPLETE / 1
OFFICERS             COMPLETE
OWNERSHIP_PARTIES    NOT_ATTEMPTED / 0
RELATIONSHIPS        NOT_ATTEMPTED / 0
```

`RegistryAcquisitionBundle.model_validate(...)` now raises `ValidationError`. Because
the aggregate cannot be normally constructed/revalidated, it cannot be serialized or
projected through the API as a successful acquisition. The focused test is
`test_original_false_complete_counterexample_is_rejected_directly`.

## 7. Direct Adversarial Construction Coverage

The direct model tests reject:

- complete with ownership/relationships not attempted, empty, or failed;
- missing, duplicate, unknown/extra, or inconsistent operation results;
- complete with a blocking missing-data issue;
- partial with complete evidence, technical failure, absent expected issue, or retained
  evidence behind an empty operation;
- failed with no failed operation, a complete later operation, records behind a
  not-attempted operation, or missing safe failure information;
- officers/relationships count mismatches and nonzero empty counts;
- duplicate officer IDs;
- record operation/time provenance mismatch, cross-environment operation provenance,
  incorrect bundle time, conflicting entity identity, and non-complete entity result.

The 34 new cases include every mandatory counterexample and positive control from the
remediation brief.

## 8. Valid Aggregate Construction Coverage

Direct reconstruction accepts:

- normal complete acquisition with complete officers and ownership evidence;
- complete acquisition with legitimate empty officers;
- partial acquisition with missing ownership parties/relationships;
- partial acquisition with present parties but missing relationships;
- officer failure followed by ownership/relationships not attempted;
- relationship failure after successful prior operations.

The accepted mapper-bypass regression also confirms malformed blank canonical fields
still route to `REVIEW_REQUIRED / CANONICAL_DATA_INCOMPLETE` instead of becoming a
technical aggregate failure.

## 9. Runtime Operation Regression

Normal eligible Singapore Mock acquisition remains:

| Operation | Calls | Result |
|---|---:|---|
| Entity profile | 1 | `COMPLETE / 1` |
| Officers | 1 | `COMPLETE / 1` |
| Ownership parties | 1 | `COMPLETE / 2` |
| Relationships | 1 | `COMPLETE / 2` |

No retry, duplicate call, operation collapse, or sequencing change was introduced.

## 10. Phase 09 Call-Stopping Regression

| Blocker | Registry operations | IDP | Ownership | GoldTier |
|---|---:|---:|---:|---:|
| `JURISDICTION_UNRESOLVED` | 0 | 0 | 0 | 0 |
| `JURISDICTION_CONFLICT` | 0 | 0 | 0 | 0 |
| `REGISTRY_PROVIDER_NOT_IMPLEMENTED` | 0 | 0 | 0 | 0 |
| `REGISTRY_IDENTIFIER_NOT_ELIGIBLE` | 0 | 0 | 0 | 0 |

The Phase 09 focused suite passed all 39 tests. Jurisdiction policy and routing were not
changed.

## 11. Ownership Integration Confirmation

The accepted architecture remains unchanged:

```text
RegistryAcquisitionBundle
  -> RegistryAcquisitionOwnershipProvider
  -> Party / OwnershipRelationship
  -> existing OwnershipAnalysisService
```

The 197-test focused POC/provider suite and 600-test backend suite confirm registry-fed
direct, indirect, multiple-path, and cycle behavior remains under the existing Decimal
service. No threshold, aggregation, traversal, cycle detection, indirect engine, UBO
classification, or GoldTier hierarchy behavior changed.

## 12. Empty / Partial / Failure Confirmation

- Empty officers remain `OFFICERS = EMPTY`, overall `COMPLETE`, and may continue.
- Missing ownership evidence remains `PARTIAL / REGISTRY_EXPECTED_DATA_MISSING`, routes
  to controlled review, and makes zero IDP/ownership/GoldTier calls.
- Malformed relationship data remains `FAILED /
  REGISTRY_OPERATION_MALFORMED_RESPONSE` and stops downstream.
- Timeout/unavailable operation failures retain safe technical codes, one failed
  operation, and a not-attempted suffix.
- Entity not found remains outside the bundle as `ACRA_ENTITY_NOT_FOUND`; later
  operations are not called.

## 13. API / Frontend Impact

There is no valid-runtime schema or frontend behavior change. The existing API and UI
continue to render backend-authored complete/empty/partial/failed/not-attempted states
and the project-owned synthetic Mock label. The domain now prevents impossible states
before API projection. No frontend source or test change was required by remediation;
typecheck, 48 tests, and the production build pass.

## 14. Security / Trust Boundary Confirmation

The normalized acquisition aggregate is now a defensive trust boundary:

- external record counts, identities, references, state, provenance, and timing must
  agree before persistence or browser projection;
- failed/not-attempted operations cannot retain evidence;
- raw payloads, URLs, headers, credentials, exception text, or new logging are not
  introduced;
- Mock/Sandbox labels remain explicit and Q-012 still prevents fabricated expanded
  sandbox/live success.

Secret unit tests pass. The first repository scan detected only the newly generated
temporary frontend JavaScript build bundle; that verified temporary output was removed,
and the final source-tree scan passed with no supported secret patterns. No confidential
sponsor artefact or credential was inspected or changed.

Security findings after remediation: Critical none; High none; Medium none within the
assigned aggregate boundary.

## 15. Exact Test Results

| Check | Exact result |
|---|---|
| Phase 10 focused/direct aggregate | **52 passed**, 1 existing deprecation warning |
| New direct aggregate cases | **34 passed** within the focused suite |
| Phase 09 adversarial | **39 passed**, 1 existing deprecation warning |
| Focused zero-touch/UAT/input/provider regression | **197 passed**, 4 existing warnings |
| Full backend | **600 passed**, 4 existing warnings |
| Owning Phase 02 canonical-defense regression | **7 passed** |
| Ruff — `apps/backend scripts tests` | **PASS** |
| Strict mypy, no incremental cache | **PASS**, 60 source files |
| Contract tests | **44 passed** |
| Secret-unit tests | **5 passed** |
| Final repository secret scan | **PASS**, no supported secret patterns |
| GoldTier validator unit tests | **5 passed** |
| GoldTier fixture validation | **PASS** — 19 valid, 19 invalid/quarantined, 48 not validated |
| Python dependency consistency | **PASS**, no broken requirements |
| Frontend dependency tree | **PASS**; expected optional packages absent |
| Frontend typecheck | **PASS** |
| Frontend tests | **48 passed** on permissioned esbuild rerun |
| Frontend production build | **PASS**, 29 modules; temporary output removed after verification |
| Delivery assets | **4 passed** |
| Windows/demo lifecycle | **13 passed in 183.368s**; final launcher-owned processes stopped |
| `git diff --check` | **PASS**, line-ending notices only |
| `git diff --cached --check` | **PASS**, nothing staged |

One intermediate full-backend run reported 599 passed and one failure because the first
identity invariant rejected a deliberately blank canonical registration number before
the accepted canonical-review boundary. CI triage classified this as a remediation
product regression. The validator was narrowed to reject only a nonblank conflicting
identifier; the owning seven-case regression, focused suite, and final 600-test backend
run then passed. Frontend test/build initially encountered the known sandbox-only
`esbuild spawn EPERM`; permissioned authoritative reruns passed.

## 16. Sponsor Dependencies

- **Q-012 remains OPEN.** Authoritative ACRA expanded operations, schemas, auth, errors,
  role/relationship vocabularies, limits, TLS/mTLS/private CA, access, and live
  verification remain unknown.
- **Q-015 remains OPEN.** Jurisdiction evidence precedence, disagreement authority,
  authenticated review, correction evidence, and resume/restart policy remain unknown.

No sponsor question was resolved or narrowed by this technical remediation.

## 17. Scope / Non-Goals Confirmation

Not implemented or changed: Phase 11, reconciliation, source precedence, human-review
redesign, foreign registry, live ACRA, ACRA+, provider-mode redesign, Mongo persistence,
UBO policy/calculation, GoldTier integration/mapping, Ready-for-Approval, related-party
or relationship writes, frontend workflow/actions, production RBAC, or durable workflow.

## 18. Remaining Risks

- Critical implementation findings: none.
- High implementation findings: none.
- Q-012 and Q-015 remain open sponsor dependencies, not remediation defects.
- Existing process-local persistence, Mock-only expanded operations, provisional UBO
  policy/mappings, narrow synthetic UEN predicate, frontend PDF-selection debt, and
  upstream deprecation/adversarial serializer warnings remain accepted and unchanged.
- The pre-existing inaccessible untracked
  `apps/frontend/pytest-cache-files-89airr88/` directory remains uninspected and
  untouched; no verification depended on it.

## 19. Readiness

PH10-QG-001 through PH10-QG-003 are remediated with direct construction evidence and a
fully green required verification matrix. The branch is ready for a separately assigned
independent Phase 10 re-quality gate. Phase 11 has not begun.

READY FOR PHASE 10 RE-QUALITY GATE
