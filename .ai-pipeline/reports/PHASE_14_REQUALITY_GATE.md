# Phase 14 Remediation Re-Quality Gate

Date: 2026-09-09
Reviewer role: independent remediation re-quality-gate reviewer; no remediation implementation was performed.
Result: **FAIL**
Verdict: **FAIL — PHASE 14 REMEDIATION IS NOT ACCEPTED: ROLLBACK CAN MASK THE ORIGINAL ESTABLISHMENT FAILURE, EXECUTION EVIDENCE REMAINS INACCURATE, AND PHYSICAL MONGO PROOF IS OUTSTANDING.**

## 1. Reviewer independence

The remediation handoff was treated as untrusted. The reviewer read the planner, execution
report, original independent quality gate, current implementation, project context, decision
log, Phase 14 architecture note, and required project skills. The production lock/call graph
was inspected and fresh deterministic harnesses were constructed rather than accepting the
remediation tests as proof. No subagent or remediation author was used.

## 2. Baseline and drift

- Expected/current branch: `phase/14-case-management-performance`
- `HEAD`: `aba264af3b4088a9a10fe682ee6fc0cb418d550d`
- `origin/main`: `aba264af3b4088a9a10fe682ee6fc0cb418d550d`
- Merge base: `aba264af3b4088a9a10fe682ee6fc0cb418d550d`
- `HEAD..origin/main`: empty
- Initial main drift: none
- Initial tracked-only status: the expected uncommitted Phase 14 tree; nothing staged and no
  unmerged path

## 3. Remediation delta review

The tracked delta contains 50 modified files; the expected Phase 14 new owners/tests remain
untracked. The remediation adds composition/wiring and service changes that extend the single
canonical per-case lifecycle boundary through onboarding, CLM, automation, and optional demo
registration. The frontend deletion effect is now asynchronous and cancels the authenticated
user's relevant in-flight query families before cache mutation.

No second per-case lock map was added: `ClmOrchestrationService._lock_for` delegates to
`OnboardingService.case_lock`. The latter owns the single per-case `RLock` map. The change adds
bounded local rollback rather than an HTTP DELETE or external-system rollback. Complexity is
high in the existing orchestration owner, but the remediation delta is localized wiring and
lifecycle control; no duplicate lifecycle owner or compatibility fallback was found.

## 4. P14-QG-001 attack

**Status: OPEN.** The original create/delete orphan race is fixed, but the required rollback
semantics are incomplete. A fresh failure-of-rollback probe showed that a rollback exception
replaces the original establishment exception as the primary propagated failure.

Production call graph inspected:

`POST demo/create -> ZeroTouchOrchestrator.create_case -> reserve identity -> canonical RLock
-> onboarding insert -> CLM insert -> automation insert -> establishment_action/demo register
-> return -> release RLock`

Authorized deletion enters `CaseDeletionService.delete` and acquires the same lock before
access/role checks and aggregate deletion.

## 5. Independent create/delete race evidence

A fresh production-builder harness paused immediately before `ZeroTouchDemoControl.register`
wrote a `RECOVERY` scenario, then started authorized deletion on another thread. Deletion was
still pending after the pause interval. After releasing creation, creation returned `201`,
deletion completed, and the result was:

- `NO_ORPHAN_NO_RESURRECTION`
- onboarding, automation, CLM, documents, ownership, reconciliation, demo scenario, and demo
  recovery transient absent
- list and Dashboard omitted the case; detail returned `404`
- unrelated case preserved
- no late demo state appeared

Target-execution and case-provider state were additionally exercised with a completed rich
aggregate: one target ledger entry existed before deletion, none existed after deletion, and
the non-default case-specific provider binding was released. No external-provider deletion
call occurred.

## 6. Rollback evidence

Normal late-write rollback passed. A required establishment action registered a `RECOVERY`
demo scenario and then raised `ExactLateFailure`. The same exception remained primary; the
entire local case aggregate and demo transient were removed; the unrelated case was unchanged.

The adversarial cleanup-failure case failed the gate. With an establishment action raising
`OriginalFailure` and the supplied transient rollback raising `RollbackFailure`, production
propagated `RollbackFailure`; `OriginalFailure` remained only in `__context__`. This follows
directly from `create_case` calling `_discard_failed_establishment` inside its `except` block,
while `_discard_failed_establishment` invokes transient rollback from `finally` without
preserving the original exception as primary. This violates the explicit instruction to reject
a swallowed/masked original exception.

Rollback is local and same-case scoped. It does not call public HTTP DELETE, clear a whole
repository, remove unrelated identifiers, or invoke an external connector.

## 7. Demo registration race

**PASS.** The actual demo route supplies registration as `establishment_action` to the
orchestrator. The before-write race proved the application route did not become the transaction
owner: lifecycle semantics remain in `ZeroTouchOrchestrator`, and DELETE could not pass the
service boundary while registration was paused.

## 8. Lock and deadlock analysis

- Canonical lock: per-case `threading.RLock` owned by `OnboardingService`
- Nested onboarding/CLM creation: reentrant use of that same lock
- CLM established mutations: `_lock_for` returns the onboarding case lock
- DELETE: same onboarding case lock
- Route-local lock: none
- Second per-case lock map: none
- Observed deadlock: none

A deterministic established-mutation/delete harness proved mutation held the lock, DELETE
waited, mutation completed, DELETE completed, and final case state was absent. Two concurrent
deletes returned one `deleted` and one `not-found` outcome with final absence.

## 9. Create/save persistence semantics

**PASS.** Duplicate create was rejected, save of a missing row was rejected, and a stale object
captured before hard delete could not recreate the deleted onboarding case. Create remains
insert-only and save remains update-only in the memory repository. Mongo code retains
insert-only creation, revision-aware replace, and revision-aware delete, but physical behavior
was not exercised in this gate.

## 10. Memory hard-delete result

**PASS.** Both sequential rich-aggregate deletion and adversarial creation/deletion completed
cleanly. Onboarding, automation, CLM, documents, ownership, reconciliation, target execution,
demo scenario, and case-specific transient/binding state were absent after deletion. No state
reappeared, unrelated state remained intact, and no external provider deletion was called.

## 11. P14-QG-002 attack

**Status: CLOSED.** Source inspection confirms `caseDeletedEffect` awaits cancellation of the
authenticated user's list family, exact Dashboard, exact detail, exact documents, and exact
ownership queries before filtering/removing cache state. Both callers await the server DELETE
before invoking and awaiting the effect.

## 12. Independent deferred-query result

A real TanStack `QueryClient` harness invoked the production `caseDeletedEffect` while deferred
list and Dashboard query promises were in flight. The promises intentionally ignored abort.
After the effect, both stale promises were released and query transitions settled. The deleted
list row did not republish and the removed Dashboard did not return. This verifies publication
behavior rather than merely observing an `AbortSignal`.

## 13. Dashboard cancellation result

**PASS.** Dashboard cancellation is awaited before exact removal. The independently deferred
Dashboard response could not restore the removed snapshot after resolution.

## 14. Failure and success ordering

**PASS.** `CaseQueue` and `CaseDetail` both await `deleteZeroTouchCase` before calling
`caseDeletedEffect`. Pending or failed DELETE therefore leaves the UI cache unchanged. Only a
successful response starts cancellation and cache transition. The production implementation
does not use an over-broad `queryClient.clear()` for case deletion.

## 15. Cross-user cache

**PASS.** All deletion keys are scoped by authenticated user ID. The independent race seeded a
second user's list and verified it remained unchanged before and after stale User A responses
settled.

## 16. Normal future refetch

**PASS.** After deletion and stale-response settlement, a new authoritative query on the same
list key completed normally and populated only its new server result. Cancellation did not
poison the key. Existing configured semantics remain: 45-second `staleTime`, 15-minute
`gcTime`, no focus refetch, reconnect refetch enabled, GET retry once, mutation retry disabled,
and session-memory-only storage. Identity/logout clearing remains centralized separately.

## 17. P14-QG-003 evidence

**Status: OPEN.** The dialog path is now correctly stated as
`apps/frontend/src/pages/DeleteCaseDialog.tsx`, and the important formatter invariant is true:
Phase 14 introduced zero semantic Ruff formatter defects. The final execution evidence is
still inaccurate, however.

Fresh attribution over all 33 Python paths listed as Phase 14 changed/new found:

- Phase 14-introduced semantic formatter defects: **0**
- retained baseline semantic findings: **8**
- EOL-only findings: **19**
- clean touched files: **6**

The execution report states 32 paths and 18 EOL-only findings. Its full backend claim is also
not reproducible: the current suite collected 876 tests and ran as 863 passed, 13 skipped, 4
warnings, rather than the report's 911 passed, 13 skipped, 3 warnings. The suite is green, but
the evidence counts remain wrong.

## 18. Documentation review

`docs/architecture/PHASE_14_CASE_MANAGEMENT_PERFORMANCE.md`, `docs/PROJECT_CONTEXT.md`, and
decision D-040 accurately describe the shared reentrant single-process establishment/delete
boundary, pre-mutation query cancellation, local-only deletion, and absence of external
rollback. They explicitly avoid distributed-lock, external-erasure, production-retention, and
physical-Mongo-pass claims. The deletion role/policy remains labelled project-defined and
provisional. The execution report remains inaccurate as described in section 17.

## 19. Physical Mongo result

`PHASE12_MONGO_URI_CONFIGURED=NO`. **PHYSICAL_MONGO=SKIPPED.** No physical Mongo suite was run,
no ambient Mongo was intentionally used for evidence, and no database name was supplied. The
required isolated `clm_p14_<24 lowercase hex>` physical proof remains an integration blocker.

## 20. Focused and broad backend

| Check | Fresh result |
|---|---:|
| Phase 14 focused | 14 passed, 1 warning |
| Phase 13 auth/priority/Dashboard | 114 passed, 1 warning |
| Pre-Phase-12 multi-document | 32 passed, 1 warning |
| Impacted zero-touch/CLM/provider | 240 passed, 4 warnings |
| Full backend | 863 passed, 13 skipped, 4 warnings in 118.39s |
| Collection confirmation | 876 tests collected |
| MyPy `app` | success, 83 source files |
| `pip check` | no broken requirements |

The warnings are the existing FastAPI/Starlette deprecation warning plus bounded adversarial
Pydantic serializer warnings. No backend test failed.

## 21. Frontend

| Check | Fresh result |
|---|---:|
| Focused Phase 14 Vitest | 10 passed in 1 file |
| Typecheck | passed |
| Full Vitest | 126 passed in 5 files |
| Build | passed; 94 modules transformed |

The first Vitest attempts were blocked by sandbox `spawn EPERM`; the required read-only reruns
with scoped child-process permission passed.

## 22. Ruff and formatter

Broad Ruff lint returned `All checks passed!` with 12 access-denied traversal warnings. The
bounded exact 33-path lint run passed. Broad formatter traversal crashed on an inaccessible
non-source path; it was not treated as a pass. Direct bounded formatter checking is non-green
because of 8 retained semantic baseline paths and 19 EOL-only paths. LF-normalized baseline
comparison establishes zero Phase 14-introduced semantic formatter defects. No formatting was
applied.

## 23. Contracts, lifecycle, and dependency checks

- Contract discovery: 44 passed
- Phase 07 delivery-assets: 4 passed
- Windows lifecycle: 18 passed in 356.358s
- Secret-checker units: 5 passed
- Pre-PR checker units: 37 passed in 62.845s
- GoldTier examples: 19 valid, 19 invalid/quarantined, 48 not validated
- `npm.cmd ls --all`: passed; optional platform/peer dependencies only
- `npm.cmd audit`: 0 vulnerabilities
- Bounded `scan_file`: 59 exact Phase 14 files, 0 findings

The first contract-discovery attempt inherited ambient configuration and failed before two
modules loaded; it was invalidated and rerun only after the ordinary-test memory environment
was established before import. The first pre-PR unit run was sandbox-blocked from creating
disposable Git repositories; its scoped-permission rerun passed. The actual pre-PR script and
broad secret scanner were not run, as required.

## 24. Integration security review

Delete authentication, role/team authorization, inaccessible-case non-disclosure, CSRF,
duplicate/hostile browser-source headers, stale saves, concurrent deletes, cache stale-response
publication, cross-user cache isolation, rollback scope, provider-boundary behavior, logging,
and Mongo access boundaries were re-reviewed.

RBAC/non-disclosure/browser protections remain fail-closed in source and focused tests. Delete
errors are sanitized. No broad repository clear, external provider deletion, browser-persistent
cache, sensitive logging addition, or cross-user cache mutation was found. The new Medium
rollback error-masking defect is an integrity/diagnostic failure path; it does not bypass RBAC.
The remaining Low evidence defect is process/report accuracy rather than an authorization
defect.

## 25. Findings table and data-safety receipt

| ID | Severity | Affected contract/path | Reproducible evidence | Required remediation |
|---|---|---|---|---|
| P14-RQG-001 | Medium | `apps/backend/app/services/zero_touch_orchestration.py` establishment failure/rollback path | `OriginalFailure` from the late required write plus `RollbackFailure` from transient cleanup propagated `RollbackFailure` as primary; the original survived only as context. | Preserve the original establishment failure as the primary error while safely recording/handling rollback failure; add a deterministic rollback-failure regression. |
| P14-QG-003 | Low | `.ai-pipeline/reports/PHASE_14_EXECUTION.md` | Final tree has 33 touched Python paths: 0 introduced semantic, 8 retained semantic, 19 EOL-only, 6 clean; report says 32/8/18/6. Full backend is currently 863/13/4, not 911/13/3. | Correct final-tree formatter and full-suite evidence without claiming repository-wide formatter success. |

Finding totals: **Critical 0; High 0; Medium 1; Low 1.** P14-QG-001 remains open because its
mandatory rollback exception-preservation condition is not met; P14-QG-002 is closed;
P14-QG-003 remains open.

Data-safety receipt:

- `.env` accessed: **YES** — indirect configuration loading occurred in two invalidated startup
  attempts before the ordinary-test environment was forced; no value or content was displayed.
- shared `clm_poc` inspected: **NO** — startup failed with `PersistenceUnavailableError`; no
  collection content was queried or reviewed by the reviewer.
- shared `clm_poc` written: **NO** — no successful database write was observed; this is not a
  claim about the separate historical incident, which was not investigated.
- protected artifacts accessed: **NO** — broad Ruff traversal received access-denied errors;
  no protected content was read.
- Phase 14.5 worktree accessed: **NO**.
- Mongo URI/host/credentials, passwords, hashes, sessions, cookies, and CSRF values printed:
  **NO**.
- Cleanup of the historical incident or protected artifacts attempted: **NO**.

The indirect `.env` access was a reviewer safety failure and requires owner awareness. The
affected contract and harness runs were invalidated; only explicitly isolated reruns are used
as evidence.

## 26. Final verdict and readiness

**RESULT: FAIL.** The core create/delete serialization, ordinary rollback, memory hard delete,
stale-save prevention, frontend stale-response prevention, and relevant regressions pass.
However, P14-QG-001 cannot close because rollback failure masks the original establishment
failure, and P14-QG-003 remains open because the execution report's formatter and full-suite
counts are inaccurate. Physical Mongo proof is additionally outstanding.

- Implementation accepted: **NO**
- Ready for owner-controlled commit: **NO**
- Ready for PR/merge: **NO**
- Confidence: **B** — direct target and broad memory/static regression evidence is strong;
  physical Mongo is untested and the cleanup-failure path is falsified.
- Remaining blockers:
  1. preserve the original establishment failure when bounded rollback also fails;
  2. correct the Phase 14 execution-report formatter and full-backend evidence;
  3. rerun this independent gate after remediation;
  4. run the isolated physical Phase 14 Mongo proof with explicit approved configuration;
  5. owner review of the disclosed indirect `.env` startup incident.

Git action receipt: no implementation was modified; nothing was staged, committed, amended,
pushed, merged, rebased, reset, stashed, or cleaned; and no branch switch occurred. The only
reviewer-authored workspace file is this dedicated re-quality-gate report.
