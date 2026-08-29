# Phase 11 Quality Gate Remediation

## 1. Executive Summary

The four findings from the independent Phase 11 Quality Gate have been remediated within the assigned process-local POC boundary. Legal-name selection and reconciliation resolution now commit through one coordinated unit of work; reconciliation field, discrepancy, and case aggregates reject contradictory semantic states; duplicate decisions are accepted only against the complete current evidence context; and low-confidence conflicting evidence produces one actionless `UNVERIFIABLE` blocker.

All required focused, regression, static, contract, frontend, security, dependency, GoldTier, delivery, and Windows lifecycle checks passed. No independent re-quality gate was performed and Phase 12 was not started.

## 2. Quality Gate Findings Addressed

| Finding | Severity | Disposition |
| --- | --- | --- |
| P11-QG-001 | High | Fixed. Canonical legal-name mutation and decision persistence are coordinated atomically under one process-local unit-of-work lock, with exact rollback on recoverable repository faults. |
| P11-QG-002 | High | Fixed. Field results, discrepancies, and case records derive and validate their semantic state from current observations and links; forged false-clear aggregates are rejected. |
| P11-QG-003 | Medium | Fixed. Idempotent duplicate return now follows all current-context freshness checks rather than bypassing them. |
| P11-QG-004 | Medium | Fixed. Low-confidence conflicting evidence yields a single `UNVERIFIABLE` discrepancy with no selection actions. |

## 3. Root Causes

- Resolution previously persisted the onboarding canonical update and reconciliation record through separate repository calls, exposing a half-committed state when the second call failed.
- Domain models checked structural shape but trusted caller-supplied outcomes and case statuses instead of deriving their meaning from observations and current discrepancy links.
- Duplicate-decision handling returned a retained decision before rechecking whether the discrepancy, versions, documents, and evidence fingerprints were still current.
- Service comparison logic separately emitted unusable-evidence and value-conflict discrepancies, so the same evidence could create two semantic blockers and incorrectly expose selection actions.

## 4. Files Changed

Remediation-specific implementation and tests:

- `apps/backend/app/domain/reconciliation.py`
- `apps/backend/app/services/reconciliation.py`
- `apps/backend/app/services/reconciliation_repository.py`
- `apps/backend/app/services/repository.py`
- `apps/backend/app/services/onboarding.py`
- `apps/backend/tests/test_phase11_remediation.py`
- `apps/backend/tests/test_zero_touch_orchestration.py`

Remediation-specific documentation:

- `docs/contracts/RECONCILIATION_PROFILE.md`
- `docs/architecture/PHASE_11_RECONCILIATION_REVIEW_RESUME.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/decisions/DECISION_LOG.md`
- `.agents/skills/poc-regression-check/references/regression-catalogue.md`
- `.ai-pipeline/reports/PHASE_11_REMEDIATION.md`

The broader unstaged Phase 11 implementation already present in the working tree was preserved. Nothing was staged, committed, pushed, merged, rebased, stashed, reset, or cleaned.

## 5. Atomic Decision/Canonical Commit Design

`OnboardingService.prepare_reconciled_value()` now creates and validates a proposed onboarding aggregate without persistence. `ReconciliationService.resolve_discrepancy()` independently prepares and validates the proposed reconciliation record, including the decision, refreshed fingerprints, discrepancy links, and derived status.

`ProcessLocalReconciliationUnitOfWork` then acquires the shared onboarding/reconciliation repository lock and rechecks the expected whole-case fingerprint, canonical-entity fingerprint, and reconciliation version. It snapshots both repository entries, applies both validated candidates while the shared lock prevents observation of an intermediate state, and restores both exact snapshots before releasing the lock if any recoverable in-process exception occurs. The visible result is therefore either both canonical selection and decision committed, or neither committed.

The unit of work is deliberately bounded to the current in-memory POC. It is not a generic transaction framework and does not claim process-crash or restart durability.

## 6. Atomicity Fault Injection

Direct service/unit-of-work tests prove the original state is preserved for:

1. canonical candidate preparation failure;
2. reconciliation candidate validation failure;
3. reconciliation version conflict before commit;
4. failure before the onboarding commit boundary;
5. failure before reconciliation persistence;
6. unexpected failure after both internal replacements but before successful return.

Every failure assertion verifies the original canonical entity, original open discrepancy, absent decision, and unchanged event/history state. The success controls verify that both aggregates commit and that Registry and Document observations remain retained.

## 7. Field Result Invariants

A shared pure outcome derivation function is used by service construction and domain validation. It applies the bounded Phase 11 priority and comparison contract:

- genuine invalid evidence derives `INVALID`;
- unusable/low-confidence evidence derives `UNVERIFIABLE`;
- absent expected Registry or Document evidence derives `MISSING_IN_SOURCE`;
- usable normalized values that all agree derive `MATCH`;
- usable distinct normalized values derive `CONFLICT`.

Direct construction now rejects declared outcomes that disagree with those observations. `MATCH` cannot reference a discrepancy.

## 8. Discrepancy Invariants

Discrepancies re-derive their outcome and allowed actions from their own field observations. Construction rejects `MATCH` discrepancies, outcome/observation contradictions, invalid resolution state, decisions outside the allowed action set, cross-field decisions, and malformed evidence fingerprints. Fingerprints are restricted to 64 lowercase hexadecimal characters.

Each current non-match field links to exactly one authoritative current discrepancy for its evidence. Unusable evidence cannot simultaneously create an actionable conflict. Historical superseded discrepancies may remain retained, but cannot masquerade as current blockers.

## 9. Case-Level Reconciliation Invariants

`ReconciliationCaseRecord` validates current source document IDs, the fixed ordered four-field result set, current field/discrepancy observation equality, unique linkage, discrepancy currency, and status semantics.

- `NOT_STARTED` is permitted only for an empty version-zero record.
- `MATCHED` requires every current field to be `MATCH` and no current blocker.
- `REVIEW_REQUIRED` requires at least one correctly linked current open blocker.
- `RESOLVED` requires every current blocker to have a retained valid decision and no current open blocker.
- `FAILED` may carry only bounded safe error state and cannot carry active evidence/results.

`is_currently_cleared()` uses the revalidated aggregate's intrinsic cleared semantics and a current whole-evidence fingerprint comparison. It no longer trusts status alone.

## 10. Original False-Cleared Counterexample

The original attack—conflicting Registry and Document legal names forged as `MATCH`, a cancelled/forged discrepancy, and a caller-supplied `MATCHED` case—now fails domain/repository validation. The repository preserves the original `REVIEW_REQUIRED` record, and `is_currently_cleared()` remains false.

Direct negative tests also cover all required false field outcomes, discrepancy contradictions, malformed fingerprints, false case statuses, unrelated open discrepancies, and duplicate current field/discrepancy linkage. Positive direct-construction controls cover every supported outcome and status.

## 11. Stale Duplicate Decision Fix

The duplicate-decision path now loads the current onboarding case and active documents before considering idempotency. It returns a retained decision only when the case and current discrepancy link, reconciliation and automation versions, whole evidence fingerprint, canonical evidence, active document IDs/event counts, discrepancy fingerprint, and requested action all still agree.

A replay of an old resolved discrepancy after document/evidence replacement is rejected as stale by the reconciliation service itself. A genuinely identical request against unchanged current evidence remains idempotent.

## 12. Low-Confidence Action Fix

Registry `ACME PTE LTD` plus a conflicting Document legal name below the confidence threshold now produces exactly one current legal-name `UNVERIFIABLE` discrepancy. Its `allowed_actions` is empty in the domain and API response, so the frontend receives no `KEEP_REGISTRY_VALUE` or `USE_DOCUMENT_VALUE` control. Replacement evidence remains the supported path.

## 13. No-Precedence Confirmation

The remediation introduces no Registry, Document, current-canonical, recency, or confidence-based source precedence. Usable conflicting evidence remains blocked for an explicit authorized POC decision; unusable, invalid, or missing evidence remains blocked for replacement evidence.

## 14. Canonical Legal-Name Boundary

`USE_DOCUMENT_VALUE` remains limited to one unambiguous usable legal-name Document observation. Direct mutation attempts for registered address, registration identifier, and country continue to be rejected. Registry and IDP observations remain immutable evidence.

## 15. Multi-Blocker / Resume Regression

The accepted resume sequence remains intact:

- with two blockers: ownership calls `0`, GoldTier calls `0`;
- after resolving one blocker: ownership calls `0`, GoldTier calls `0`;
- after resolving the final blocker: ownership runs once, then GoldTier search/shell/policy/amend each run once;
- repeated completed start/resume: no additional ownership or GoldTier calls.

The one-current-discrepancy rule is per field/current evidence and does not collapse independent blockers on different fields. Multiple same-field Document observations remain preserved inside the single authoritative discrepancy in stable order.

## 16. Replacement Regression

Replacement keeps Registry acquisition unchanged, retains the superseded Document and historical cancelled discrepancy, builds a new reconciliation record from the replacement, rejects the old discrepancy/fingerprint, and runs IDP only for the replacement document. Ownership and GoldTier remain stopped until all current evidence clears.

## 17. Phase 09 / Phase 10 Regression

- Phase 09: `39 passed`; jurisdiction blockers and zero-call downstream behavior preserved.
- Phase 10: `52 passed`; four-operation Singapore Registry acquisition preserved.
- Normal Singapore acquisition remains entity `1`, officers `1`, ownership parties `1`, relationships `1`.

Ownership/UBO calculation and GoldTier code were not changed by this remediation.

## 18. API / Frontend Impact

No remediation-specific endpoint or frontend implementation change was required. Existing response types already represent an empty `allowed_actions` list. The backend now truthfully returns no selection action for low-confidence/unverifiable evidence, and existing frontend rendering therefore shows no selection control.

## 19. Security / Persistence Boundary

The remediation adds no outbound integration, credential path, authorization bypass, raw-evidence logging, KYC/PII logging, or browser storage. The secret scanner and security unit tests passed. Evidence and canonical fingerprints are backend integrity values and contain no raw evidence.

Persistence remains process-local. The shared-lock snapshot/restore protocol protects against tested recoverable in-process repository exceptions; it does not survive interpreter termination, machine failure, or restart. MongoDB was not added or enabled. Production reviewer authorization, durable audit transactions, and restart semantics remain outside this phase.

## 20. Exact Test Results

| Check | Result |
| --- | --- |
| Phase 11 focused reconciliation + remediation | `58 passed`, 1 existing Starlette/httpx deprecation warning |
| New remediation/direct model/repository/fault/stale/low-confidence tests | `38 passed` |
| Focused zero-touch + Phase 07 UAT | `48 passed` |
| Phase 09 suite | `39 passed` |
| Phase 10 suite | `52 passed` |
| Focused POC/provider regression | `197 passed`, 4 warnings |
| Full backend | `658 passed`, 4 warnings |
| Ruff | Passed |
| strict mypy, no incremental cache | 64 source files, no issues |
| Contract tests | `44 passed`, 1 existing Starlette/httpx deprecation warning |
| Frontend typecheck | Passed |
| Frontend tests | `52 passed` |
| Frontend production build | Passed, 29 modules transformed |
| Secret unit tests | `5 passed` |
| Secret scan | Passed |
| Python dependency check | No broken requirements |
| Frontend dependency tree | Passed; only expected optional dependencies absent |
| GoldTier unit validation | `5 passed` |
| GoldTier example validation | 19 valid, 19 invalid/quarantined, 48 not validated; exit 0 |
| Delivery assets | `4 passed` |
| Windows lifecycle | `13 passed` in 148.727 seconds on the clean rerun; owned processes stopped |
| `git diff --check` | Passed; line-ending notices only |
| `git diff --cached --check` | Passed; staging area empty |

The first Windows lifecycle attempt encountered retained environmental process/port state and failed before establishing a clean runtime. Read-only inspection found no remaining runtime metadata or listeners; the complete clean rerun then passed 13/13 without manual destructive cleanup.

Live ACRA and live MongoDB were not required. The configured Mongo diagnostic failed safely without `MONGO_URI`, as expected. Installed `pymongo` version was 4.15.1.

## 21. Sponsor Dependencies

- Q-012 remains open for the authoritative subscribed ACRA endpoint/schema/authentication/error/rate-limit contract and authorized sandbox access.
- Q-015 remains open for production source/reviewer authority, conflict-resolution governance, retained audit evidence, and restart/resume policy.

The implemented decisions remain bounded project POC decisions and do not claim sponsor confirmation.

## 22. Scope / Non-Goals Confirmation

This remediation changed only the four assigned Quality Gate findings and directly related tests/documentation. It did not add Phase 12 work, MongoDB, live ACRA, foreign registries, production RBAC, structured-address editing, corrected-value entry, ownership/UBO logic, GoldTier mapping, `createRelationship`, multi-level hierarchy creation, risk assessment, autonomous approval, analytics/MIS, or a full Exception Workbench.

## 23. Remaining Risks

No known Critical or High finding remains within this bounded remediation after local verification. Independent re-quality-gate review is still required.

Known boundaries remain:

- atomicity and idempotency are process-local, not crash/restart durable;
- production reviewer authority and durable audit semantics depend on Q-015;
- live ACRA binding depends on Q-012;
- concurrent multi-process persistence is unsupported by the in-memory repositories;
- the existing Starlette/httpx compatibility warning remains non-blocking.

## 24. Readiness

All four assigned findings are fixed, their required counterexamples and fault paths are covered, required regressions pass, and documentation records the bounded guarantees and unresolved sponsor dependencies. The working tree is preserved unstaged for independent inspection.

READY FOR PHASE 11 RE-QUALITY GATE
