# Phase 15B — Review / Rework Stabilization Plan

## Goal

Stabilize the existing document-review, reconciliation, replacement, and zero-touch resume workflow without creating a full Exception Workbench, inventing reviewer/assignment policy, weakening evidence checks, or overlapping Phase 15C's frontend-navigation ownership.

The bounded outcome is that review actions are tied to current evidence, every evidence-changing action refreshes or invalidates the existing reconciliation and automation guards, recoverable processing failures return the case to a usable intake state, authorization is rechecked at mutation time, and target calls still occur at most once and only after all blockers are cleared.

## Architecture

Keep the current owner chain intact:

`authenticated API mutation -> case-scoped lock -> document/reconciliation service -> zero-touch orchestrator -> target-call ledger -> GoldTier connector`

Extend the current document event counts, reconciliation evidence fingerprints, canonical fingerprints, automation versions, and persistence envelope revision/CAS. Do not add a second evidence-version mechanism, a parallel authorization owner, a reviewer-task store, a new persistence model, or direct API-to-provider orchestration.

## Tech Stack

- Python backend domain and service layer
- FastAPI request/authentication composition
- Pydantic persisted envelopes and the existing memory/Mongo repository modes
- `Decimal`-based canonical ownership engine, unchanged
- Pytest unit, API, persistence, RBAC, and regression coverage
- React/TypeScript frontend inspected for integration boundaries only; no frontend implementation in the backend slice

## Baseline and Authority References

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-15b`
- Branch: `phase/15b-review-rework`
- `BASE_SHA`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- `HEAD` at planning start: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- `origin/main` at planning start: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- Tracked worktree at planning start: clean
- Context check: `python scripts/dev_context.py` passed on this branch and baseline
- Governing sources: `AGENTS.md`, `docs/PROJECT_STATE.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT_WORKFLOW.md`
- Relevant contracts: `IDP_REVIEW_CONTRACT.md`, `MULTI_DOCUMENT_INTAKE_PROFILE.md`, `RECONCILIATION_PROFILE.md`, `ZERO_TOUCH_AUTOMATION_POLICY.md`, `CASE_ACCESS_AND_PRIORITY_PROFILE.md`, `PERSISTENCE_RECOVERY_PROFILE.md`, `CLM_READINESS_POLICY.md`, `POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md`
- Authority records: `docs/decisions/DECISION_LOG.md` and `docs/sponsor-questions/OPEN_QUESTIONS.md`
- Accepted evidence consulted: Phase 11 final quality gate, pre-Phase-12 persistence/RBAC re-quality, Phase 12 re-quality, and Phase 13 re-quality reports

Authority remains source-and-test first. No roadmap label or disabled UI control is treated as implemented capability.

## Compatibility Boundary

The implementation must preserve:

- the current public route shapes and persisted envelope schema unless a separately reviewed plan authorizes otherwise;
- memory as the default persistence mode and Mongo as an explicit mode, with equivalent behavior;
- the existing POC case-access policy: team scope, Director global visibility, HR without case access, and safe inaccessible-case `404`;
- existing reconciliation actions and legal-name canonical update semantics;
- multi-blocker behavior: clearing one blocker must not clear another;
- target-ledger ordering and no replay after completion or restart;
- `REQUEST_ADDITIONAL_INFORMATION` as reserved/unadvertised, not a newly enabled action;
- disabled assignment and return-for-rework controls until sponsor policy exists;
- original extracted evidence and historical review events as immutable lineage, apart from appended decisions on current evidence;
- mock/local/sandbox labels; this phase proves no Live provider behavior.

If the bounded fix requires a new persisted field, schema version, new service owner, reviewer identity/audit model, assignment model, generic override, or cross-provider change, stop and return to architecture/planning review.

## TDD Route

- Mode: off.
- Decision: skipped because strict/test-first TDD was not requested and no active strict-TDD route exists.
- Verification route: add focused regression tests with each repair, run them first during iteration, then run the complete affected backend, contract, security, regression, and physical-Mongo gates before readiness is claimed.

## Verification

Planning-time evidence:

- Focused current-baseline suite passed: `test_document_processing.py`, `test_phase11_reconciliation.py`, `test_zero_touch_orchestration.py`, `test_phase12_persistence.py`, and `test_phase13_auth_rbac.py`.
- Three direct reproductions confirmed the stale/manual-correction behavior, replacement-processing recovery dead end, and mutation of superseded evidence described below.

Implementation-time completion requires the exact focused tests and gates in this plan. Passing mock tests is not evidence of sponsor approval or live-provider interoperability.

## 1. Current Behavior Discovered

### 1.1 Document review

- `DocumentProcessingService.review_field` accepts `ACCEPTED`, `REJECTED`, and `CORRECTED` decisions while a record is `REVIEW_REQUIRED` or `REVIEWED`.
- Repeating the same final decision is idempotent; submitting a different final decision for the same field conflicts.
- A document becomes `REVIEWED` when every reviewable field has a final decision.
- The service preserves the original extracted value and appends review events/decisions.
- The service does not currently require the reviewed document to be `is_current_evidence=True`. A superseded historical record can therefore still be mutated.
- Missing and low-confidence fields enter review, but the current downstream reconciliation does not apply reviewed corrections as effective evidence.

### 1.2 Reconciliation

- Reconciliation builds observations from registry evidence and current document records.
- Document observations currently use `original_extracted_value`; `reviewed_value` and final review status do not alter the effective value.
- Reconciliation already owns a full evidence fingerprint over case, registry, and current-document evidence, plus discrepancy fingerprints and versioned compare-and-swap protection.
- A legal-name `USE_DOCUMENT_VALUE` decision uses a unit of work that validates canonical/onboarding fingerprints before the canonical update.
- Resolving one of several blockers leaves the automation waiting; only the final cleared blocker permits continuation.
- Successful replacement cancels open discrepancies derived from old evidence while retaining resolved historical decisions.

### 1.3 Zero-touch exceptions and resume

- The orchestration enters `WAITING_FOR_REVIEW` with typed exceptions when document or reconciliation evidence blocks progress.
- Resolution binds the submitted action to the automation version and an exact evidence version. Stale resolution is rejected.
- Calling `start` while the automation is already `WAITING_FOR_REVIEW` returns the unchanged record. It does not refresh reconciliation after an out-of-band document-field decision.
- The target-call ledger remains the owner of ordering, call-stopping, recovery, and no replay.
- `REQUEST_ADDITIONAL_INFORMATION` exists in the action vocabulary but is not advertised or implemented as a supported operator path.

### 1.4 Replacement/reupload and recovery

- Successful document replacement supersedes the old record, makes the new record current, invalidates old discrepancies, and can resume processing.
- If processing of the replacement fails, the document service persists a current failed replacement and supersedes the old document before raising `DocumentProcessingInfrastructureError`.
- The zero-touch replacement path does not currently convert that failure into a recoverable intake transition. Its old active exception still points at the superseded document.
- The API replacement handler does not currently translate that document-processing infrastructure exception into the controlled zero-touch/API failure family.
- Persistence restart recovery already has the required semantic pattern: an interrupted/failed current document returns automation to `PENDING_INPUTS` at the document stage, cancels stale open exceptions, and records `DOCUMENT_REUPLOAD_REQUIRED`.
- The existing targeted retry route can reuse the failed current document. An explicit intake completion/start step remains necessary afterward.

### 1.5 Assignment and reviewer ownership

- There is no backend assignment, self-assignment, reviewer ownership, team-queue ownership, task claiming, or reassignment model.
- `assigned_to` is not backed by durable assignment behavior. A legacy/local frontend workbench uses session-local display state only.
- `AssignReviewerDialog` and `ReturnForReworkDialog` intentionally disclose that those capabilities are unavailable.
- Phase 15B must not turn those placeholders into policy or persistence.

### 1.6 Authorization

- Authentication middleware reloads the current user profile per request and applies safe `404` semantics for inaccessible cases.
- Team members are team-scoped, Directors can access across teams, and HR has no case access under the current POC policy.
- Profile/security-version changes revoke stale sessions; current tests prove a previously valid session becomes unauthorized.
- Case priority and deletion paths already demonstrate sensitive reauthorization inside the owning lock/CAS boundary.
- Review, replacement, reconciliation resolution, and resume currently rely primarily on the pre-lock API authorization. They need an in-lock freshness check so access loss between page load/request entry and mutation cannot alter evidence.
- No sponsor-confirmed reviewer role, separation-of-duties rule, or actor/audit attribution model exists.

### 1.7 Persistence and concurrency

- A per-case re-entrant lock serializes mutations in one process.
- Mongo persists the full case envelope with revision CAS; stale whole-envelope writes fail.
- Decisions, evidence versions, document events, automation state, exceptions, and target-call ledger state are durable in Mongo.
- This is not a distributed lock across multiple service instances. Multi-instance guarantees remain bounded to repository CAS and idempotency keys/ledger behavior.

### 1.8 Frontend

- `CaseDetail.tsx` supports replacement/retry for current documents.
- It does not expose field-level `ACCEPTED`/`REJECTED`/`CORRECTED` review actions.
- After retrying a failed current document, the detail view refreshes but does not expose the intake-complete/start action needed from `PENDING_INPUTS`.
- The assignment and return-for-rework dialogs remain disabled disclosures.
- `App.tsx` is a Phase 15C hotspot and is not required for the backend repair.

## 2. Reproducible Defects

### Defect A — reviewed correction cannot refresh a waiting automation

Classification: **IMPLEMENTATION DEFECT** in an existing review/resume workflow.

Reproduction:

1. Start a case whose extracted legal name conflicts with registry evidence.
2. Reach `WAITING_FOR_REVIEW` with an active reconciliation/document blocker.
3. Correct the legal-name field to the registry value and finalize the other review fields.
4. Observe the document become `REVIEWED`.
5. Call the existing start/resume behavior.

Observed result: automation remains `WAITING_FOR_REVIEW` at the same version, reconciliation continues to use the original extracted value, and attempting to resolve the old exception produces `ZERO_TOUCH_EXCEPTION_STALE`. No target calls occur.

Required result: the review mutation must invalidate/refresh the current blocker using existing evidence guards. Once all required fields are final, safe effective evidence must be reconciled; the case resumes only if no blocker remains.

### Defect B — failed replacement strands the case behind a superseded exception

Classification: **IMPLEMENTATION DEFECT** in replacement/reupload recovery.

Reproduction:

1. Reach `WAITING_FOR_REVIEW` for a document blocker.
2. Submit a replacement whose IDP processing fails.
3. Observe the prior document is superseded and the failed replacement is current.
4. Observe automation remains waiting with the old exception referencing the superseded document.
5. Retry through the old exception or call start/resume.

Observed result: start returns unchanged and retry through the old reference fails with `DOCUMENT_ALREADY_SUPERSEDED`; the case has no coherent recovery path. No target calls occur.

Required result: atomically invalidate the old exception, keep the failed replacement as current, transition to `PENDING_INPUTS` at the document stage, record `DOCUMENT_REUPLOAD_REQUIRED`, and expose a controlled retryable API failure.

### Defect C — superseded historical evidence accepts new review mutations

Classification: **IMPLEMENTATION DEFECT** in evidence immutability.

Reproduction:

1. Create a review-required document.
2. Replace it successfully so the original becomes non-current.
3. Submit a field-review decision directly against the old document ID.

Observed result: the historical record accepts the decision and appends an event even after the automation completes.

Required result: reject review of non-current/superseded evidence before any event, record, reconciliation, automation, or ledger mutation.

## 3. Existing Canonical Owners

| Concern | Canonical owner to extend | Boundary |
|---|---|---|
| Per-field extraction/review state and original evidence | `DocumentProcessingService` and document domain records | Only current evidence is mutable; historical records remain lineage |
| Effective observations, discrepancies, evidence fingerprint, canonical-name update | `ReconciliationService` and reconciliation repository | No duplicate mapping or evidence hash in routes/orchestrator |
| Workflow state, exception lifecycle, resume, replacement coordination | `ZeroTouchOrchestrator` and zero-touch domain transition rules | All progress still passes through target-ledger ordering |
| Authentication and case-access policy | `AuthenticationService`, `CaseAccessPolicy`, API auth composition | Recheck inside the same case lock; do not create a second policy engine |
| In-process mutation serialization | Existing case-scoped `RLock` | Do not add an unrelated lock owner |
| Durable mutation conflict detection | Existing envelope revision CAS/repositories | No new review-specific persistence store |
| Target side effects and replay protection | Existing target-call ledger | Never call a connector directly from review/reconciliation code |
| Restart recovery | Existing persistence/zero-touch recovery semantics | Reuse `PENDING_INPUTS` plus `DOCUMENT_REUPLOAD_REQUIRED` |

## 4. Desired Bounded State/Action Matrix

| Starting state / evidence | Action | Required resulting state | Side-effect rule |
|---|---|---|---|
| `WAITING_FOR_REVIEW`, current field undecided | `ACCEPTED` | Stay waiting until all fields are final; refresh/bump stale exception guards | No target call |
| `WAITING_FOR_REVIEW`, current field has usable original evidence | `CORRECTED` with valid value | Preserve original, record correction; after all fields final reconcile using safe effective value | Resume only if every blocker clears |
| `WAITING_FOR_REVIEW`, current field | `REJECTED` | Remain waiting for replacement/reupload | No override and no target call |
| Missing original or below usable-confidence threshold | `CORRECTED` | Record the decision but keep replacement-required blocker under current provisional policy | No target call; no silent human override |
| All required fields final and effective evidence matches/clears reconciliation | Automatic refresh | `RESUMING`, then existing progression | At-most-once target calls through ledger |
| All required fields final but another document/reconciliation/ownership blocker remains | Automatic refresh | Current `WAITING_FOR_REVIEW` with refreshed active blocker(s) | No target call past blocked stage |
| Open reconciliation discrepancy | `KEEP_REGISTRY_VALUE` | Resolve only that discrepancy; wait if any blocker remains | Existing canonical value retained |
| Open legal-name discrepancy permitted by contract | `USE_DOCUMENT_VALUE` | Validate evidence/canonical fingerprints; update via current UoW; wait if other blockers remain | No bypass of canonical UoW |
| Current document replacement succeeds | Replace | Invalidate old document-derived exceptions/decisions; reconcile new evidence; resume only if clear | Old evidence stays historical |
| Current document replacement processing fails | Replace | `PENDING_INPUTS` at document stage with current failed record and `DOCUMENT_REUPLOAD_REQUIRED` | Controlled retryable failure; no stale active exception |
| `PENDING_INPUTS` with failed current document | Targeted retry | Reprocess same current document; explicit intake completion/start then resumes | No duplicate evidence identity or target replay |
| Superseded/non-current document | Any review/replacement decision bound to old ID | Reject as stale/non-current | Zero mutation |
| Stale automation version, reconciliation fingerprint, canonical fingerprint, or discrepancy fingerprint | Resolve/resume | Reject with existing typed stale/conflict response | Zero mutation and no target call |
| Repeated resume while unresolved | Start/resume | Return unchanged waiting state | No target call |
| Repeated resume after completion or recovered call | Start/resume | Return current completed/recovered state | Ledger prevents replay |
| Actor lost session/case access or attempts cross-team mutation | Any sensitive mutation | `401` for invalid session or safe `404` for inaccessible case | Zero mutation and no existence disclosure |

`REQUEST_ADDITIONAL_INFORMATION`, assignment, reassignment, task claiming, final approval, and general reviewer override are deliberately absent from the executable matrix.

## 5. Evidence Invalidation Rules

1. A document-field review decision is valid only for the current document record and its current event history. A non-current document ID is rejected before mutation.
2. Original extracted values remain immutable evidence. A review decision appends lineage; it does not rewrite the extraction result.
3. Effective document value for bounded reconciliation is:
   - `ACCEPTED`: original extracted value;
   - `CORRECTED`: reviewed value only when the original field was present and met the existing usable-confidence threshold;
   - `REJECTED`: unusable, replacement required;
   - missing original or low-confidence original: still replacement required, even if a correction was entered, until sponsor policy authorizes a broader override.
4. Every accepted current-evidence review mutation invalidates open document-derived exceptions and refreshes reconciliation using the existing evidence fingerprint. It also advances the automation version so a browser holding the prior exception/version cannot decide the new evidence state.
5. Partial review never resumes processing. Refresh may produce the current typed document-review blocker, but target calls remain stopped.
6. Once all required fields are final, recompute reconciliation from current effective observations. Resume exactly once only when document review, reconciliation, ownership, and every other existing blocker are clear.
7. Replacement changes document identity and event history. All open exceptions/discrepancies tied to the superseded document are cancelled or made stale; resolved historical decisions remain audit lineage and are never applied to the replacement.
8. Replacement-processing failure still changes current evidence. The old exception is cancelled, the failed replacement remains current, and automation moves to recoverable document input rather than pretending the old evidence is actionable.
9. Reconciliation resolution continues to require the exact discrepancy fingerprint and evidence version. Legal-name canonical mutation additionally requires the existing canonical/onboarding fingerprint checks.
10. Ownership decisions remain bound to the current ownership analysis ID/version. Phase 15B adds no ownership correction or replacement flow.
11. Automation resolution continues to require the exact automation version and server-generated evidence version/digest. Client-provided summaries are never authoritative.
12. Mongo revision CAS remains the final durable stale-write barrier. A CAS conflict must return a typed conflict/reload outcome; it must never retry by overwriting a newer decision.

## 6. Authorization Boundaries

- Preserve middleware authentication and current safe-`404` case lookup as the first boundary.
- For review, replacement/retry, reconciliation resolution, and start/resume mutations, reacquire current session/profile authority inside the existing case-scoped lock immediately before reading actionable evidence and writing state.
- Apply the existing `CaseAccessPolicy` inside that boundary; do not encode Director/team/HR rules directly in each route.
- If session security version changed, return the existing unauthorized response. If the current actor cannot access the case, return the existing safe `404`.
- Perform no document event append, reconciliation update, exception cancellation, automation version change, persistence save, or target call before this check succeeds.
- Do not persist a reviewer/assignee identity or claim separation-of-duties evidence in this phase. The final role and audit policy is sponsor-dependent.
- Continue sanitizing logs: safe case/document/correlation identifiers and typed codes only; no document body, raw source payload, PII, bearer material, or private exception details.

## 7. Sponsor Dependencies and Classification

| Topic | Classification | Phase 15B treatment |
|---|---|---|
| Superseded evidence remains reviewable | IMPLEMENTATION DEFECT | Fix now |
| Reviewed correction does not refresh effective evidence/workflow | IMPLEMENTATION DEFECT | Fix only for the bounded safe-value rules above |
| Failed replacement strands stale exception | IMPLEMENTATION DEFECT | Fix now by reusing recovery semantics |
| Existing team/Director/HR case access and safe `404` | PROJECT-DEFINED POC BEHAVIOR | Preserve and recheck inside mutation boundary |
| Current reconciliation `KEEP_REGISTRY_VALUE` and bounded legal-name `USE_DOCUMENT_VALUE` | PROJECT-DEFINED POC BEHAVIOR | Preserve |
| Final reviewer role and separation of duties | SPONSOR-DEPENDENT: Q-014 | Do not implement |
| Final source precedence, correction authority, missing/invalid/confidence override, and production resume policy | SPONSOR-DEPENDENT: Q-015 | Keep fail-closed bounded rule; do not generalize |
| Production assignment/reassignment/role policy | SPONSOR-DEPENDENT: Q-016 | Do not implement assignment |
| Final validation owner split | SPONSOR-DEPENDENT: Q-005 | Do not move ownership between source/target layers |
| Final Ready-for-Approval policy | SPONSOR-DEPENDENT: Q-001 and related readiness questions | Do not add final approval/decision |
| Final UBO rule | SPONSOR-DEPENDENT | Preserve current deterministic engine; no override |
| Assignment, self-assignment, team queues, task claiming, reassignment | NEW CAPABILITY | Out of scope |
| `REQUEST_ADDITIONAL_INFORMATION` operator workflow/client messaging | NEW CAPABILITY plus sponsor policy | Keep unadvertised/out of scope |
| Full Exception Workbench | NEW CAPABILITY | Out of scope |

## 8. Backend-Only Parallel Implementation Slice

### Task 1 — Make historical evidence immutable

Files:

- `apps/backend/app/services/document_processing.py`
- `apps/backend/tests/test_document_processing.py`
- `apps/backend/tests/test_document_api.py`

Implementation:

1. In `review_field`, validate `is_current_evidence` after loading under the case lock and before appending an event.
2. Return a stable typed document request conflict for superseded evidence, preferring the existing `DOCUMENT_ALREADY_SUPERSEDED` vocabulary unless the owning contract requires a more precise existing code.
3. Preserve same-decision idempotency only for current evidence; historical evidence is never newly mutable.
4. Add service and API regressions proving no event count, state, reconciliation, automation, or target-ledger change occurs.

Change necessity: this is the smallest fix for Defect C and closes the most direct stale-browser mutation path.

### Task 2 — Define one effective reviewed-observation rule

Files:

- `apps/backend/app/services/reconciliation.py`
- `apps/backend/tests/test_phase11_reconciliation.py`
- `docs/contracts/IDP_REVIEW_CONTRACT.md`
- `docs/contracts/RECONCILIATION_PROFILE.md`

Implementation:

1. Centralize the effective-value selection in reconciliation; do not pre-map reviewed values in routes or the orchestrator.
2. Implement the bounded rules from Section 5: accepted original; safely corrected reviewed value; rejected/missing/low-confidence replacement-required.
3. Include the field decision/event history through the existing document contribution to the evidence fingerprint; do not introduce another version field.
4. Retain existing discrepancy kinds/actions and legal-name canonical UoW semantics.
5. Add multi-document and multi-blocker coverage so a corrected field cannot hide a different blocker.

Change necessity: Defect A cannot be resolved merely by calling resume while reconciliation continues to ignore reviewed evidence.

### Task 3 — Coordinate review refresh and one safe resume

Files:

- `apps/backend/app/services/zero_touch_orchestration.py`
- `apps/backend/app/main.py`
- `apps/backend/tests/test_zero_touch_orchestration.py`
- `apps/backend/tests/test_document_api.py`
- `docs/contracts/ZERO_TOUCH_AUTOMATION_POLICY.md`

Implementation:

1. Route the API field-review mutation through an orchestration-owned operation under the existing case lock rather than mutating the document service out of band.
2. Apply the review decision, invalidate/cancel document-derived open exceptions made stale by the new event, refresh reconciliation, and advance the automation version atomically within the current persistence envelope.
3. If review is partial or any blocker remains, persist a coherent current waiting state and stop.
4. If all blockers clear, enter the existing `RESUMING` path and continue through the ledger exactly once.
5. Preserve idempotency for an exact repeated current decision; reject contradictory or stale decisions.

Change necessity: a refresh owner is needed because `start` intentionally treats waiting as stable, and changing that generic behavior would broaden every exception path.

Complexity guard: `zero_touch_orchestration.py` is already under strong size pressure. Reuse its existing exception/reconciliation helpers. If the cohesive delta grows beyond a small orchestration operation (approximately 80 net lines excluding tests) or introduces a new responsibility, stop for an extraction/architecture review rather than extending the monolith opportunistically.

### Task 4 — Recover atomically from replacement processing failure

Files:

- `apps/backend/app/domain/zero_touch.py`
- `apps/backend/app/services/zero_touch_orchestration.py`
- `apps/backend/app/main.py`
- `apps/backend/tests/test_zero_touch_orchestration.py`
- `apps/backend/tests/test_document_api.py`
- `apps/backend/tests/test_phase12_persistence.py`
- `apps/backend/tests/test_phase12_real_mongo.py`
- `docs/contracts/ZERO_TOUCH_AUTOMATION_POLICY.md`
- `docs/contracts/PERSISTENCE_RECOVERY_PROFILE.md`

Implementation:

1. Permit the explicit legal transition from waiting review to `PENDING_INPUTS` at the document stage for failed current replacement recovery.
2. Catch `DocumentProcessingInfrastructureError` in the orchestration replacement transaction after the document service persists the failed current record.
3. Cancel stale open document exceptions, reset completed stages to the existing safe document-retry boundary, append `DOCUMENT_REUPLOAD_REQUIRED`, advance automation version, and persist once.
4. Translate the result through the existing zero-touch infrastructure/API error contract (retryable `503` behavior), without exposing provider internals.
5. Reuse the current targeted retry path. Do not create a second upload or recovery API.
6. Prove the subsequent explicit intake completion/start resumes once and that restart preserves the same recovery state.

Change necessity: this closes Defect B by using behavior already accepted for restart recovery.

### Task 5 — Reauthorize sensitive mutations inside the case lock

Files:

- `apps/backend/app/api_auth.py`
- `apps/backend/app/main.py`
- `apps/backend/tests/test_phase13_auth_rbac.py`
- `apps/backend/tests/test_phase14_5_administration.py`
- `docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md`
- `docs/contracts/POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md`

Implementation:

1. Extract/reuse one API-auth composition helper that reloads the current session/profile and applies `CaseAccessPolicy` while the orchestration-owned case lock is held.
2. Apply it to field review, document replacement/retry, reconciliation resolution, and explicit start/resume mutations.
3. Preserve the existing public response distinction: invalid/revoked session is unauthorized; inaccessible or cross-team case is safe `404`.
4. Add deterministic hooks/tests that revoke access between initial request authentication and locked mutation.
5. Assert zero state and connector changes when reauthorization fails.

Change necessity: current request-entry checks do not close the time-of-check/time-of-use window required by this phase's adversarial cases.

### Task 6 — Run persistence, regression, and security closure

Files:

- `apps/backend/tests/test_phase12_persistence.py`
- `apps/backend/tests/test_phase12_real_mongo.py`
- `apps/backend/tests/test_phase13_auth_rbac.py`
- `apps/backend/tests/test_phase14_5_administration.py`
- Phase execution report at the repository-prescribed path for the implementation run

Implementation:

1. Exercise the same scenarios in memory and newly generated allowlisted disposable Mongo database modes.
2. Verify CAS conflicts, restart in every affected waiting/recovery state, and target-ledger no replay.
3. Run the POC regression scenario set and integration-security review.
4. Record commands, results, branch/base/current main, exact files, decisions, risks, and any skipped physical evidence in the implementation report.

No production work begins from this planner run. A separate explicitly authorized implementation run must recheck `origin/main`, branch cleanliness, and overlap before Task 1.

## 9. Deferred Phase 15C Frontend Integration

Backend implementation can proceed without editing `App.tsx`, routing, navigation, or frontend shell files.

After the backend slice is accepted, coordinate a small Phase 15C-owned integration:

- `apps/frontend/src/pages/CaseDetail.tsx`: expose current-document field decisions and the explicit continue/complete-intake action after a failed-document retry; surface stale/conflict responses as reload-required rather than silently retrying.
- `apps/frontend/src/api.ts`: call the existing/updated review and resume endpoints and preserve server versions/fingerprints exactly.
- `apps/frontend/src/UiV2Integration.test.tsx`: cover corrected review, partial review, stale submission, failed replacement retry, and no premature progress.
- `apps/frontend/src/types.ts`: change only if the accepted backend contract adds a response field; the planned backend repair should avoid requiring this.

Expected non-changes:

- `apps/frontend/src/App.tsx`: no Phase 15B edit is needed.
- `apps/frontend/src/pages/AssignReviewerDialog.tsx`: remain disabled.
- `apps/frontend/src/pages/ReturnForReworkDialog.tsx`: remain disabled.

The frontend must not calculate evidence validity, decide authorization, auto-retry stale writes, or infer that a corrected value overrides registry evidence. Those remain backend-authoritative.

## 10. Exact Files Expected to Change

### Backend/domain/API/persistence slice

- `apps/backend/app/domain/zero_touch.py`
- `apps/backend/app/services/document_processing.py`
- `apps/backend/app/services/reconciliation.py`
- `apps/backend/app/services/zero_touch_orchestration.py`
- `apps/backend/app/api_auth.py`
- `apps/backend/app/main.py`
- `docs/contracts/IDP_REVIEW_CONTRACT.md`
- `docs/contracts/RECONCILIATION_PROFILE.md`
- `docs/contracts/ZERO_TOUCH_AUTOMATION_POLICY.md`
- `docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md`
- `docs/contracts/PERSISTENCE_RECOVERY_PROFILE.md`
- `docs/contracts/POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md`
- `apps/backend/tests/test_document_processing.py`
- `apps/backend/tests/test_document_api.py`
- `apps/backend/tests/test_phase11_reconciliation.py`
- `apps/backend/tests/test_zero_touch_orchestration.py`
- `apps/backend/tests/test_phase12_persistence.py`
- `apps/backend/tests/test_phase12_real_mongo.py`
- `apps/backend/tests/test_phase13_auth_rbac.py`
- `apps/backend/tests/test_phase14_5_administration.py`
- The Phase 15B implementation report required by the phase-execution skill

No change is expected to persistence schemas/models, Mongo repository implementation, provider connectors, shared frontend types, `PROJECT_STATE.md`, or `ARCHITECTURE.md`. If implementation proves one is necessary, stop and reclassify/replan before editing it.

### Later Phase 15C-owned integration

- `apps/frontend/src/pages/CaseDetail.tsx`
- `apps/frontend/src/api.ts`
- `apps/frontend/src/UiV2Integration.test.tsx`
- `apps/frontend/src/types.ts` only if an accepted contract change requires it

## 11. Exact Tests Required

### Focused regression cases

Add named cases to the existing files for:

- `test_document_processing.py`
  - reject review against superseded evidence with no appended event;
  - exact repeat on current evidence remains idempotent;
  - conflicting second reviewer decision is rejected.
- `test_document_api.py`
  - stale document/version submission returns the typed conflict;
  - replacement processor failure returns controlled retryable response and coherent state;
  - revoked/cross-team actor cannot review, replace, retry, or resume.
- `test_phase11_reconciliation.py`
  - accepted field uses original evidence;
  - safe correction uses reviewed value while preserving original;
  - rejected/missing/low-confidence field remains replacement-required;
  - correction-to-registry clears only that discrepancy;
  - correction to a third value remains a conflict;
  - replacement invalidates old open decisions and keeps resolved history;
  - one resolved blocker while another remains does not resume.
- `test_zero_touch_orchestration.py`
  - partial review remains waiting;
  - all safe reviews trigger one refresh and one resume;
  - stale browser decision is rejected after another review/replacement;
  - failed replacement transitions to `PENDING_INPUTS` with `DOCUMENT_REUPLOAD_REQUIRED`;
  - retry plus explicit start resumes once;
  - duplicate start/resume and completed recovery do not replay target calls;
  - ownership/reconciliation blockers still stop progress.
- `test_phase12_persistence.py`
  - all new state transitions round-trip in memory-compatible repository behavior;
  - restart while partially reviewed, fully reviewed/waiting, and failed replacement retains exact state;
  - stale envelope revision cannot overwrite a newer review/replacement.
- `test_phase12_real_mongo.py`
  - physical CAS race between two reviewers permits one durable winner;
  - physical restart/reload preserves effective evidence, exception invalidation, and retry state;
  - target ledger does not replay after restart.
- `test_phase13_auth_rbac.py`
  - loss of team membership/access between request entry and mutation yields safe `404` and no mutation;
  - revoked session yields unauthorized and no mutation;
  - Director behavior remains allowed and HR remains denied.
- `test_phase14_5_administration.py`
  - profile/team/security-version changes invalidate an already-open review action before mutation.

### Required commands

Run focused tests first, then:

```powershell
Set-Location apps/backend
python -m pytest tests/test_document_processing.py tests/test_document_api.py tests/test_phase11_reconciliation.py tests/test_zero_touch_orchestration.py -q -p no:cacheprovider
python -m pytest tests/test_phase12_persistence.py tests/test_phase13_auth_rbac.py tests/test_phase14_5_administration.py -q -p no:cacheprovider
```

Run the repository-prescribed full backend/type/contract/security/regression commands from `docs/DEVELOPMENT_WORKFLOW.md` and the relevant skill checklists. Run physical Mongo evidence only with a newly generated allowlisted disposable database, never `clm_poc`, and never print the URI.

Before PR readiness in the later implementation run:

```powershell
python scripts/dev_context.py
python scripts/pre_pr_check.py
```

Complete `.agents/skills/integration-safe-development/references/PRE_PR_CHECKLIST.md`. The checker does not replace semantic, security, restart, concurrency, or physical-persistence review.

## 12. Concurrency and Adversarial Cases

| Case | Required protection and observable result |
|---|---|
| Two reviewers decide the same field concurrently | Case lock serializes in process; exact duplicate is idempotent, contradictory decision conflicts; Mongo CAS admits one durable winner across instances |
| Reviewer loses access after opening task | In-lock fresh authentication/case-access check rejects before mutation; safe `404` or unauthorized as appropriate |
| Evidence replaced after review decision | Old document becomes non-current; open old exceptions/discrepancies become stale/cancelled; no decision transfers to replacement |
| One blocker resolved while another remains | Automation remains waiting at the current earliest blocker; target ledger does not advance |
| Corrected/replacement document fails processing | Current failed evidence is retained; automation returns to recoverable `PENDING_INPUTS`; old exception is not actionable |
| Stale browser submits old decision | Document currency plus automation/evidence/discrepancy version checks reject with zero mutation |
| Duplicate resume | Waiting unresolved is unchanged; clear/completed/recovered state uses version/ledger idempotency; no duplicate connector call |
| Restart while waiting/reviewed/retrying | Persisted events, effective evidence inputs, exceptions, automation version, and ledger reconstruct the same next legal action |
| Review resolution without appropriate evidence | Missing, low-confidence, rejected, or non-current evidence remains blocked; no broad human override |
| Cross-team resolution attempt | Existing policy returns safe `404`; no existence disclosure and no state change |
| Canonical name changes between open and submit | Existing canonical/onboarding fingerprint validation rejects stale `USE_DOCUMENT_VALUE` |
| Ownership result changes while document blocker is open | Existing ownership analysis version/fingerprint makes prior resolution stale; no ownership override is added |

Multi-instance scope must be stated honestly: the case `RLock` is process-local; durable correctness relies on Mongo revision CAS and ledger/idempotency behavior. If tests show the current repository transaction shape cannot make the composed mutation atomic under CAS, stop for persistence architecture review rather than adding retries that replay business decisions.

## 13. Stop Conditions

Stop implementation and return to the planner/owner if any of the following occurs:

- The fix requires choosing final source precedence, reviewer authority, separation of duties, assignment policy, final readiness, or final UBO policy.
- A correction must override missing or low-confidence source evidence to satisfy a desired scenario.
- A generic `REQUEST_ADDITIONAL_INFORMATION`, client-messaging, assignment, self-claim, reassignment, or full workbench workflow is requested.
- A new persisted field/schema version, new repository, new evidence-version system, new authorization owner, or new target-call path appears necessary.
- Current contracts disagree materially and the source-of-truth priority does not resolve the conflict; record it in the appropriate discrepancy/decision/open-question log.
- A required change touches `App.tsx`, routing/navigation shell, Dev Tooling-owned CI/governance, ACRA live integration, Camunda runtime, or another active workstream without owner coordination.
- `origin/main` advances and its intent cannot be reconciled by an authorized normal merge.
- The implementation branch is dirty with overlapping unknown edits.
- Safe `404`, session revocation, Mongo CAS, restart recovery, multi-blocker stop behavior, or target-ledger no-replay regresses.
- Physical Mongo evidence would require a non-disposable/non-allowlisted database or access to secrets/private artifacts.
- The orchestration delta becomes a broad refactor or creates a second state owner.

## 14. Acceptance Criteria

Phase 15B implementation is acceptable only when:

1. Review mutations against superseded/non-current evidence are rejected with zero state change.
2. Accepted and safely corrected current fields produce deterministic effective observations while original extraction evidence remains intact.
3. Rejected, missing, and low-confidence evidence remains fail-closed and requires replacement under the current provisional policy.
4. Every current review decision refreshes/invalidate existing evidence guards atomically; a stale browser cannot mutate the refreshed state.
5. Partial review and multi-blocker cases remain waiting with no target call.
6. Clearing the final permitted blocker enters the existing resume path exactly once.
7. Failed replacement produces a current failed document plus coherent `PENDING_INPUTS`/`DOCUMENT_REUPLOAD_REQUIRED` recovery state, not a stale superseded exception.
8. Targeted retry plus explicit completion/start can recover after processing becomes available.
9. Duplicate resolution/resume and restart do not replay target calls.
10. Review/replacement/reconciliation/resume reauthenticate and reauthorize inside the owning case lock; revocation and cross-team attempts cause no mutation.
11. Memory and Mongo behavior match, with physical CAS/restart evidence for the affected transitions.
12. No assignment, final approval, broad override, live provider, Camunda, or full Exception Workbench capability is introduced.
13. No Phase 15C-owned frontend shell file is edited by the backend slice.
14. Contracts describe the exact provisional behavior without labeling it sponsor-confirmed.
15. Required tests/gates pass on the latest authorized main baseline and the implementation report contains fresh evidence.

## 15. Change Classifications

This planning run is `DOCS_ONLY` and creates only this planner artifact.

The later bounded backend implementation is classified as:

- `BACKEND_DOMAIN`
- `BACKEND_API`
- `AUTH_RBAC_SECURITY`
- `PERSISTENCE`

It is not expected to be `EXTERNAL_PROVIDER`, `FRONTEND_STATE_CACHE`, or `ARCHITECTURE_REFACTOR`. If a schema, ownership boundary, dependency direction, provider status, or new durable model changes, add the corresponding classification and stop for the required architecture/persistence/provider review before implementation continues.

The deferred Phase 15C integration is `FRONTEND_UI`; add `FRONTEND_STATE_CACHE` only if its accepted implementation changes query keys, scope, invalidation, cancellation, mutation effects, or retries.

## 16. Required Quality and Security Gates

- Implementation self-verification under `fyp-phase-execution` with exact commands/results.
- Independent `fyp-quality-gate` after implementation; the implementer must not self-accept the phase.
- `integration-security-review` for in-lock reauthorization, safe `404`, session revocation, sensitive logging, stale decision handling, and provider-error sanitization.
- `persistence-schema-change` gate applied to persistence semantics even though no schema change is planned; physical Mongo CAS/restart evidence is required because durable mutation behavior changes.
- `poc-regression-check` for accepted mock scenarios, workflow ordering, terminal/waiting states, connector call-stopping, no replay, and honest provider labels.
- `architecture-change-review` only if a stop condition reveals a new owner/schema/dependency; not required for the planned local fixes within existing owners.
- Pre-PR latest-main sync assessment, `scripts/pre_pr_check.py`, and the repository pre-PR checklist in the later authorized implementation run.
- Secret/confidential artifact review limited to tracked and task-owned paths; no `.env` or `private/` access.

## Plan Pressure Test and Execution Readiness

- **Visibility:** all planned code, contract, test, and deferred frontend files are listed explicitly.
- **Plan basis:** current source/tests/contracts, accepted gates, and direct reproductions—not roadmap assumptions.
- **Baseline usage:** `BASE_SHA` is the synchronized branch/main baseline; implementation must revalidate it before edits.
- **Requirement readiness:** the three defects have reproducible current/expected behavior. Sponsor-dependent extensions are excluded rather than guessed.
- **Change necessity:** each production edit maps to current-evidence immutability, effective observation ownership, workflow refresh/recovery, or in-lock authorization. No speculative feature work is included.
- **Existence check:** document review, reconciliation, zero-touch exceptions, retry/replacement, RBAC, case locks, CAS, and ledger owners already exist; assignment and full rework workflow do not.
- **Architecture integrity:** the plan extends existing owners and keeps all target calls behind the ledger.
- **Complexity budget:** local-fix plus wiring-only. Avoid broad decomposition in this phase, but stop if the orchestration change creates a new responsibility or exceeds a small cohesive delta.
- **Compatibility confidence:** public actions, safe `404`, memory/Mongo modes, historical evidence, existing reconciliation choices, and frontend shell ownership are preserved.
- **Execution route:** deferred. This planner run stops here. A separate explicitly authorized Phase 15B implementation run may execute the six backend tasks sequentially, with review after the evidence/reconciliation slice and again before persistence/security closure.

## Planner Decision

A safe backend-only implementation **can begin in a separate authorized run**, provided it follows the fail-closed correction policy, reuses existing evidence/version/CAS/ledger owners, and stops at the sponsor and architecture boundaries above. It does not require concurrent edits to Phase 15C's `App.tsx` or navigation shell.

## Owner-authorized refinement after independent Phase 15B QG

Date: 2026-09-19

The repository owner authorizes **monotonic sequential recoverability** for the existing
document-review, reconciliation, and automation sections. This refinement supersedes
only this plan's cross-section atomicity wording, including the cross-section meaning of
"atomically" in Defect B, Task 3, Task 4, the multi-instance scope statement, and
Acceptance Criterion 4. It does not weaken any evidence, authorization, CAS, blocker,
target-ledger, or no-replay requirement and does not alter the remaining plan.

The refined requirement is:

1. Each accepted section save is individually durable through its existing repository
   and case-envelope revision CAS. No new schema, repository, transaction coordinator,
   workflow owner, or target-call owner is introduced.
2. The sequence is current document evidence, then current reconciliation evidence,
   then the automation checkpoint that invalidates stale document exceptions and marks
   resumption. Earlier accepted evidence may remain durable when a later section rejects
   its save.
3. A rejected reconciliation request/CAS save, reconciliation infrastructure failure,
   authorization failure, or automation checkpoint save fails closed. It must preserve
   current blockers, perform zero ownership or target work, and must not invisibly retry
   the rejected prerequisite in the same request.
4. Progression is permitted only after both reconciliation and the automation checkpoint
   are durably accepted. Expected replacement-IDP processing failure remains the sole
   bounded route into `PENDING_INPUTS / DOCUMENT_REUPLOAD_REQUIRED`; repository, CAS,
   infrastructure, or authorization failures must not enter that path.
5. Recovery after an interrupted later checkpoint is explicit: an exact repeated review
   or `/resume` may repair from durable current evidence. Ordinary reads do not retry or
   progress the workflow, and document events or target operations must not replay.
6. Physical Mongo acceptance must cover a genuinely partial review across restart, an
   actual failed replacement across restart and targeted retry/start, and a distinct-store
   CAS race with a fresh durable reload. If the configured physical service is absent,
   the evidence remains pending rather than inferred from memory tests.

This is an owner-authorized same-owner remediation, not sponsor confirmation and not an
architecture exception for a new owner or broader orchestrator growth. The existing
`ZeroTouchOrchestrator`, section repositories, case envelope CAS, and target ledger remain
the canonical owners.
