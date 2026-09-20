# Review / Rework UI Follow-up Plan

## Goal

Add the smallest coherent frontend slice that closes genuine review/recovery gaps in the
accepted application: let an authorized case user review fields on current document
evidence, understand why a partial review is still blocking, distinguish current from
superseded evidence, and finish the existing failed-replacement recovery sequence.

This is not a new Exception Workbench. It does not add assignment, return-for-rework,
reviewer identity, final approval, source precedence, or a backend contract.

## Architecture

Preserve the current owner chain:

`URL case identity -> CaseDetail -> authenticated API helper -> backend case lock / RBAC -> document or orchestration owner -> React Query refetch`

Browser location remains the sole case-navigation identity. The backend remains the
authority for access, current evidence, allowed actions, workflow progression, and
target replay. The frontend retains only ephemeral form/pending state and publishes no
mutation result after its case/actor generation becomes stale.

## Tech stack

- React 18.3.1 and TypeScript 5.9.3
- React Router 7.18.4
- TanStack React Query 5.102.8
- Vite 7.1.11 and Vitest 3.2.4
- Playwright 1.56.1 through the repository-owned guarded runner
- Existing FastAPI public routes; no backend implementation change

## Baseline and authority references

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-review-rework-ui`
- Branch: `followup/review-rework-ui`
- `BASE_SHA`: `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
- Current source revision inspected: `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
- Local `origin/main` at planning time: `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
- Tracked tree at planning start: clean
- Active Git operation: none
- Verified behavioral baseline: current source/contracts/tests were inspected; no
  runtime test was executed by this planning task
- Independently reviewed content: none; this planner is not a quality gate
- Governing sources: `AGENTS.md`, `docs/PROJECT_STATE.md`,
  `docs/ARCHITECTURE.md`, and `docs/DEVELOPMENT_WORKFLOW.md`
- Contracts/authority: `docs/contracts/IDP_REVIEW_CONTRACT.md`,
  `MULTI_DOCUMENT_INTAKE_PROFILE.md`, `RECONCILIATION_PROFILE.md`,
  `ZERO_TOUCH_AUTOMATION_POLICY.md`, `CASE_ACCESS_AND_PRIORITY_PROFILE.md`,
  `docs/decisions/DECISION_LOG.md`, and
  `docs/sponsor-questions/OPEN_QUESTIONS.md`
- Accepted evidence: Phase 15B re-quality gate, Phase 15C final re-quality gate, and UI
  V2 final consolidated quality gate
- Current owning source: `CaseDetail.tsx`, `CaseStatePanels.tsx`, `api.ts`, `types.ts`,
  `caseQueries.ts`, `auth.tsx`, `queryClient.tsx`, backend route/auth/service owners, and
  their tests

### Baseline usage draft

- Required baseline refs: all governing sources, review/reconciliation/automation/access
  contracts, current source/tests, and the nearest accepted gates listed above
- Acknowledged before planning: all required refs
- Cited in this plan: all required refs through their applicable invariants and contracts
- Missing refs: none for the supported frontend slice
- Decision: continue

## Compatibility boundary

The implementation must preserve:

- current public routes and request/response models;
- URL/React Router case identity and native `Link`/`NavLink` behavior;
- the existing `AuthProvider`, authenticated transport, and one in-memory QueryClient;
- user/actor/case-scoped query keys, logout/401 cancellation, and cache clearing;
- backend-authoritative capability and team access with identical absent/inaccessible
  `404` presentation;
- current-evidence-only review, immutable original extraction, and historical
  supersession lineage;
- partial-review and independent-blocker behavior;
- automatic backend progression after an accepted review mutation;
- explicit resume only where the backend recovery contract requires it;
- target-ledger ordering and no blind replay after an uncertain outcome;
- Mock/Local/Sandbox/Dormant truth labels and the meaning of `COMPLETED` as
  `MOCK_GOLDTIER_SUBMITTED`, not approval or Ready-for-Approval.

No API, shared model, persistence schema, provider, configuration, business rule,
mapping, authorization policy, or architecture owner changes are authorized.

## Change classification

Planning artifact: `DOCS_ONLY`.

Proposed execution slice: `FRONTEND_UI` and `FRONTEND_STATE_CACHE`. Existing
`AUTH_RBAC_SECURITY` behavior is an affected invariant and verification surface, not a
planned authorization change. No backend, persistence, provider, or architecture class
is in scope.

## TDD route

- Mode: off
- Decision: skipped
- Strict authority: not applicable
- Strict signals: the future slice changes user-visible mutation and stale-response
  behavior, but neither the user nor project requested strict/test-first TDD
- Light eligibility: not applicable
- TDD-fit exception: none
- Test posture: minimum implementation followed by deterministic component regression,
  full frontend verification, and real Playwright journey evidence
- Reason: conform to the repository's existing non-strict planning route while keeping
  mutation/adverse-path evidence mandatory
- Verification: exact focused and broad commands are specified below

## Requirement-ready and necessity checks

### Requirement Ready Check

- Requirement source: assigned UI follow-up task plus current contracts/source
- Goal and scenario: current-evidence document review and failed-replacement recovery in
  Case Detail
- Acceptance source: the assigned capability, async/failure, UX, and verification lists
- Open blocker questions: sponsor questions Q-014/Q-015/Q-016 block production reviewer,
  assignment, separation-of-duties, and source-authority claims, but do not block the
  already implemented provisional field-review API
- Decision: ready for the supported frontend slice

### Change Necessity

- User-visible need: a current `REVIEW_REQUIRED` document exposes evidence but no way to
  call the existing field-review API; a successfully retried failed replacement can
  remain at `PENDING_INPUTS` without an explicit continuation control
- No-change option: documentation cannot make those supported actions usable
- Minimum change boundary: Case Detail's document panel, its local mutation handling,
  focused styles/tests, and the existing guarded Playwright journey
- Decision: code-change

### Existence and architecture integrity

- Proposed new surface: one presentation component for document evidence/review
- Reuse candidates: current `CaseDetail` query/action generation, `reviewDocument`,
  `resumeZeroTouchCase`, `caseQueries`, and existing document/summary types
- Decision: reuse existing API/cache/auth/workflow owners; extract presentation from the
  374-line Case Detail hotspot rather than adding another state owner or hook framework
- Architecture verdict: no ADR or architecture review is required if execution stays
  within these owners

### Complexity budget

- Artifact class: frontend case-detail view
- Pressure: `CaseDetail.tsx` is 374 lines and already mixes case actions, evidence
  rendering, cache effects, and dialogs
- Recommendation: create a narrow `DocumentEvidencePanel.tsx`; keep authenticated
  mutation/case-generation coordination in `CaseDetail.tsx`
- Budget result: within budget only with the extraction; do not add the review form
  inline to the existing document table

## Current capability and gap map

| User task | Current UI behavior | Existing API and permission | Assessment | Smallest improvement |
|---|---|---|---|---|
| Understand the active blocker | Backend exception banners, reconciliation outcomes, readiness blockers, and document state are shown, but field-level pending decisions are buried in details | Read-only case/documents routes are case-scoped | Incomplete | Put the current document's pending/final count and field reasons beside its supported actions |
| Distinguish current from historical evidence | Every document is in one table; a details summary says Current or Superseded | Browser receives `supersedes_document_id`, `superseded_by_document_id`, and `superseded_at`; no `is_current_evidence` field exists | Incomplete | Group Current evidence before Evidence history and derive current only from `superseded_by_document_id === null` |
| Review/correct a field | `reviewDocument` exists and is contract-tested, but Case Detail never calls it | `POST /api/onboarding/cases/{case_id}/documents/{document_id}/reviews`; case-scoped permission and in-lock reauthorization | Unsupported in current Case Detail, supported by API | Add actions only for pending fields of a current `REVIEW_REQUIRED` record |
| Understand partial review | Field `review_status` is displayed only indirectly; no remaining-decision explanation | Backend keeps automation waiting and refreshes blockers after every accepted current-evidence decision | Incomplete | Show `n of 4 final`, list pending fields, and state that other documents/reconciliation/ownership blockers remain independent |
| Resolve a reconciliation conflict | `ConfirmDetailsPanel` renders only server `allowed_actions` and calls the exact resolution endpoint | Version/fingerprint-bound case-scoped endpoint | Present | Retain unchanged; do not merge it with document review |
| Resolve a document exception | Exception banner renders only server `available_actions` and calls the exact endpoint | Automation-version/evidence-version-bound case-scoped endpoint | Present | Retain unchanged; do not relabel it as field approval |
| Replace current evidence | Current non-failed record exposes Replace and sends event count | Replacement route requires `X-Document-Event-Count`; case-scoped/in-lock reauthorization | Present, presentation incomplete | Keep it on current records only; show pending state and authoritative refresh |
| Recover a failed replacement | Current failed record exposes targeted retry; success refreshes evidence | Targeted retry route accepts the exact failed current document; it does not advance automation | Incomplete | After authoritative refresh, show explicit continuation only for lineage-proved failed-replacement recovery |
| Resume safe target recovery | `RECOVERY_PENDING` shows Complete safe recovery | Idempotent `/resume`; target ledger owns no-replay | Present | Retain unchanged |
| Assign a reviewer | Clickable disclosure opens a fully disabled dialog | No endpoint, assignment model, role policy, or durable owner | Unsupported | Remove the clickable affordance and dialog from this view |
| Return for rework | Clickable disclosure opens a fully disabled dialog | No generic mutation or sponsor-authorized policy | Unsupported | Remove the clickable affordance and dialog from this view |
| Final approval / Ready-for-Approval | Not supported; completed view is Mock-labelled | No authorized backend transition | Unsupported | Add nothing |

## Recommended smallest coherent slice

### Slice: current-evidence field review plus bounded replacement recovery

1. Extract the document section into `DocumentEvidencePanel` and group actual current
   records separately from historical lineage. Do not add a browser-only evidence flag.
2. For a current record in `REVIEW_REQUIRED`, render each field's original suggestion,
   canonical comparison, confidence/provenance, final review state, and actions allowed
   by the existing field-review contract:
   - `Accept suggestion` only when an original suggestion exists;
   - `Reject suggestion`;
   - `Record correction` with a non-blank value up to 512 characters and an optional
     note up to 240 characters.
3. Make final decisions read-only. State explicitly that a correction to originally
   missing or below-threshold evidence is retained but remains replacement-required
   under the current provisional contract.
4. After every accepted field decision, refetch case, documents, and ownership. Do not
   call `/resume`: `review_document_field` already refreshes the backend document
   checkpoint and may continue automatically.
5. Retain replacement and targeted retry on current records. After targeted retry,
   refetch all case evidence. Show `Continue recovered intake` only when authoritative
   state is `PENDING_INPUTS`, no current record is failed, the automation timeline
   contains the backend `DOCUMENT_REUPLOAD_REQUIRED` checkpoint, and current lineage
   replaces the corresponding historical failed record. This survives refresh/deep link
   without a second source of truth.
6. `Continue recovered intake` calls the existing `/resume` route once. Its label and
   help text say it re-evaluates the recovered intake; they do not promise completion or
   target submission.
7. Remove the clickable Assign reviewer and Return for rework disclosures from Case
   Detail and remove their now-unowned component files if repository-wide search confirms
   there are no remaining consumers.

This slice deliberately leaves the existing reconciliation panel, exception-resolution
buttons, `RECOVERY_PENDING` action, readiness panel, and target presentation unchanged.

## Exact API sufficiency and control matrix

| Control | Helper / endpoint | Request binding | Response | Authorization | Errors and refresh | Backend progression |
|---|---|---|---|---|---|---|
| Accept/reject/correct field | `reviewDocument`; `POST /api/onboarding/cases/{case_id}/documents/{document_id}/reviews` | `field_key`, `decision`; correction max 512; optional note max 240. No caller version/fingerprint/event count exists. Backend requires current evidence and accepts only an identical final repeat | Complete `DocumentProcessingRecord` | `CASE_SCOPED`; session/profile/case access rechecked inside the case lock | 401 clears session; safe 404 for absent/inaccessible; 409 for superseded/non-reviewable/conflicting decision; 422 for invalid input; 503 for later checkpoint/infrastructure failure. Always recover by authoritative refetch, never mutation replay | Yes. The review owner refreshes the document checkpoint and may advance automatically after the final safe decision |
| Replace current document | `replaceZeroTouchDocument`; `POST /api/clm/zero-touch/cases/{case_id}/documents/{document_id}/replacement` | Raw file, safe name/media, and `X-Document-Event-Count = document.events.length` | `ZeroTouchCaseSummary` | Same case-scoped/in-lock reauthorization | 409 stale/non-current conflict; upload 413/415/422; safe 503 can mean a failed current replacement was retained. Refetch documents/case before offering recovery | Successful replacement re-evaluates automatically; failed accepted replacement enters targeted recovery |
| Retry failed current document | `retryZeroTouchIntakeDocument`; `POST /api/clm/zero-touch/cases/{case_id}/intake/documents/{failed_document_id}/retry` | Exact failed document ID and raw file. No caller version; backend verifies `PENDING_INPUTS`, `FAILED`, and current evidence under lock | `DocumentProcessingRecord` | Same case-scoped/in-lock reauthorization | 409 if intake/document is no longer retryable; upload errors as above; 503 uncertain outcome requires refetch, not automatic retry | No. It replaces/reprocesses evidence but intentionally leaves explicit continuation |
| Continue recovered intake | `resumeZeroTouchCase`; `POST /api/clm/zero-touch/cases/{case_id}/resume` | No body/version. UI visibility is derived from authoritative status and actual lineage; backend revalidates current state | `ZeroTouchCaseSummary` | Same case-scoped/in-lock reauthorization | 401/safe 404/409/503; refetch on uncertain or conflict outcome; never blind replay | Yes, only if blockers clear. Target calls still pass through the ledger |
| Resolve reconciliation | `resolveReconciliationDiscrepancy`; existing route | automation version, reconciliation version, discrepancy fingerprint, allowed action | `ZeroTouchCaseSummary` | Case-scoped/in-lock | Current 409/422/503 handling and evidence refresh remain | Automatically resumes only when all blockers clear |
| Resolve typed exception | `resolveZeroTouchException`; existing route | allowed action, automation version, evidence version | `ZeroTouchCaseSummary` | Case-scoped/in-lock | Current 409/422/503 handling and evidence refresh remain | Automatically resumes only when all blockers clear |
| Complete ledger-safe recovery | `resumeZeroTouchCase`; existing `RECOVERY_PENDING` control | No body/version | `ZeroTouchCaseSummary` | Case-scoped/in-lock | Current safe handling remains | Finalizes/re-enters only through existing ledger semantics |

The public API is sufficient for this slice. No contract decision is required. Assignment,
generic return-for-rework, reviewer attribution/separation of duties, final approval, and
broader missing/low-confidence override remain contract-dependent future slices.

## Information hierarchy and interaction design

1. Keep the case header, active backend exceptions, registry/reconciliation panels, and
   completed overview in their existing order.
2. Rename the document area to `Document evidence and review`.
3. Within it, show:
   - a current-evidence summary banner with the document name, state, provider
     classification, and `final decisions / total fields`;
   - current documents as expanded review cards when action is required;
   - a collapsed `Evidence history` section for superseded records with replacement
     links and no mutation controls;
   - the existing failed-reupload warning and upload control next to the exact failed
     current record;
   - the lineage-proved `Continue recovered intake` action after retry.
4. Each current field uses a semantic heading and status text. Actions have exact
   accessible names including the field, for example `Accept legal name suggestion`,
   `Reject legal name suggestion`, and `Record legal name correction`.
5. Use an inline `fieldset` for the correction value and optional note rather than a
   new modal. Opening it moves focus to the correction input; Cancel collapses it and
   restores focus to the triggering button. Escape may cancel while the inline editor
   has focus. Existing delete/recovery dialogs retain their current behavior.
6. Pending submission disables every mutation for the displayed case, ignores duplicate
   clicks, and exposes `aria-busy` plus action-specific text such as `Saving legal name
   decision…`.
7. Success is not optimistic. The UI shows the new field/workflow state only after the
   authoritative refetch. If blockers remain, the banner states what remains; it never
   removes independent blockers based on the submitted action alone.
8. Safe error copy uses only `ApiError.message` or fixed local text. For a timeout or
   transport failure: `The outcome could not be confirmed. Current case evidence was
   reloaded; check the field status before trying another action.` Do not include values,
   notes, raw responses, filenames beyond their already safe display name, or private
   exception detail.
9. A 409 says the evidence changed and presents refreshed state. A 401 yields the
   existing anonymous flow. A safe 404 uses the existing generic unavailable-case view.
10. Mock completion and target labels remain unchanged and explicit.

## Async, stale-state, and cache invariants

- Capture generation, case ID, and actor ID before every field review, replacement,
  retry, or resume.
- A completion from case A must not update state, cache, errors, dialogs, focus, or
  navigation after the route shows case B.
- A completion from an old actor/session must not publish after logout, 401, or identity
  replacement. Global auth cancellation/clearing remains the owner.
- Do not enable automatic mutation retry. A browser abort or network failure does not
  prove that the server rejected the mutation.
- For an active current identity, perform one read-only authoritative refresh after
  mutation success, 409, 503, or an ambiguous transport failure. If the refresh also
  fails, retain the last confirmed state and ask the user to refresh; do not infer the
  mutation outcome.
- On review success, do not merge only the returned document into a list and assume the
  summary is unchanged; backend review may update reconciliation, automation, ownership,
  and target status.
- On retry success, do not infer readiness from the response alone; refetch summary and
  all document lineage before showing continuation.
- Back/Forward, refresh, or deep link reconstructs the same controls only from backend
  queries and actual lineage. No case/evidence data enters localStorage, sessionStorage,
  IndexedDB, a service worker, or URL parameters.
- Existing query keys and auth/session clearing remain unchanged. Reuse
  `refreshEvidence`/current query options and existing invalidation effects; add no
  second QueryClient, state store, or cache namespace.

## Proposed files and ownership

### Create

- `apps/frontend/src/pages/DocumentEvidencePanel.tsx` — current/history grouping,
  field-review editor, replacement/retry/continuation presentation; no fetch or cache
  ownership. Its recovery predicate consumes both document lineage and the summary's
  backend-authored `DOCUMENT_REUPLOAD_REQUIRED` timeline event
- `apps/frontend/src/pages/DocumentEvidencePanel.test.tsx` — deterministic rendering,
  action eligibility, accessibility, partial-review, lineage, and duplicate-action tests

### Modify

- `apps/frontend/src/pages/CaseDetail.tsx` — retain case/actor generation and mutation
  orchestration; wire existing helpers to the new panel; perform authoritative refresh
  and uncertain-outcome handling; remove unsupported disclosure controls
- `apps/frontend/src/styles.css` — bounded document-review/current/history states and
  responsive containment
- `apps/frontend/src/UiV2Integration.test.tsx` — replace assertions that preserve the
  unsupported assignment/rework disclosures with truthfulness assertions that they are
  absent; retain API binding tests
- `apps/frontend/src/Phase15CNavigation.test.tsx` — extend stale A->B, Back/Forward,
  logout/actor-replacement, safe 404, and native navigation regression coverage for the
  new actions
- `apps/frontend/e2e/authenticated-zero-touch.e2e.ts` — add the real guarded browser
  review/recovery journey while retaining the network guard and Mock truth assertions

### Delete after repository-wide consumer check

- `apps/frontend/src/pages/AssignReviewerDialog.tsx`
- `apps/frontend/src/pages/ReturnForReworkDialog.tsx`

### Intentionally unchanged

- `apps/frontend/src/api.ts` — every required helper already exists
- `apps/frontend/src/types.ts` — the public response already contains all required
  status, provenance, review, event, and lineage fields
- `apps/frontend/src/caseQueries.ts`, `queryClient.tsx`, and `auth.tsx` — existing key,
  invalidation, cancellation, and session owners are sufficient
- `apps/frontend/src/App.tsx` — avoid the hotspot; the routed Case Detail is the owner
- all backend/API contract, persistence, provider, registry/cache/orchestration,
  architecture, project-state, and Phase 16 files

If implementation discovers that `api.ts`, shared types, backend routes, or persistence
must change, stop this slice and return to contract/planning review.

## Implementation task sequence

### Task 1 — Current and historical evidence presentation

Files: create `DocumentEvidencePanel.tsx` and its focused test; modify `CaseDetail.tsx`
and `styles.css`.

1. Add pure selectors that classify a record as current only when
   `superseded_by_document_id` is null/absent and identify recovered-retry lineage by
   combining the summary's `DOCUMENT_REUPLOAD_REQUIRED` timeline checkpoint with a
   current record whose `supersedes_document_id` points to a historical failed record.
2. Render current records first and historical records in a separate collapsed section.
3. Render field suggestion, canonical value, comparison, confidence, provenance, review
   status, reviewed value/note, and pending/final counts without adding derived authority.
4. Retain replacement/retry only on current records; expose no mutation on history.
5. Run the focused component test.

### Task 2 — Supported field decisions and authoritative recovery

Files: modify `DocumentEvidencePanel.tsx`, `CaseDetail.tsx`, and focused tests.

1. Add the inline field decision editor and validate correction/note lengths before the
   call; omit Accept when no original suggestion exists.
2. Wire `reviewDocument` through the existing case-action identity. On completion,
   refetch summary/documents/ownership; do not call resume.
3. Centralize current-identity mutation settlement in Case Detail so success, conflict,
   infrastructure error, and ambiguous network error follow the refresh rules above.
4. After retry and refetch, render `Continue recovered intake` only from the bounded
   lineage/status predicate and wire it to one `resumeZeroTouchCase` call.
5. Prove no duplicate submission, no optimistic success, partial review remains blocked,
   and stale results are discarded.

### Task 3 — Remove unsupported affordances

Files: modify `CaseDetail.tsx` and affected tests; delete the two dialog files only after
`rg` proves no other consumer.

1. Remove Assign reviewer and Return for rework buttons/imports/dialog state.
2. Delete the two components if unused.
3. Replace prior tests that required the disclosures with absence/no-forbidden-route
   assertions.
4. Run focused UI V2 and Phase 15C navigation tests.

### Task 4 — Browser journey and broad verification

Files: modify the existing Playwright journey only.

1. Extend the guarded authenticated journey with deterministic current review-required
   evidence and failed-replacement recovery data using existing supported setup paths.
2. Exercise one valid current-field action, a partial review that stays blocked, a
   superseded historical record with no action, targeted retry, explicit recovered-intake
   continuation, and authoritative post-action states.
3. Assert native navigation roles/hrefs, safe inaccessible-case behavior, the network
   guard, no duplicate POST, and explicit Mock/POC truth.
4. Run focused, full, build, browser, governance, and pre-PR checks in the order below.

## Acceptance and test matrix

| ID | User-visible behavior / contract proved | Deterministic coverage | Real browser evidence |
|---|---|---|---|
| UI-RR-01 | Current `REVIEW_REQUIRED` field exposes only valid accept/reject/correct actions and sends the exact existing request | Component plus API serialization assertion | Submit one current-field decision |
| UI-RR-02 | Partial review remains waiting, shows remaining fields, and does not remove another blocker or call resume/target | Deferred fetch fixture and exact call-count assertion | Review one of multiple pending fields; waiting state remains |
| UI-RR-03 | Final safe review refetches authoritative state and relies on backend automatic progression | Response/refetch sequencing with no `/resume` call | Complete the supported field sequence and observe backend-authored state |
| UI-RR-04 | Missing/low-confidence correction is labelled retained-but-replacement-required | Contract fixtures for missing and below-threshold originals | Verify explanatory copy/action result if included in the chosen fixture |
| UI-RR-05 | Superseded evidence is historical, linked, read-only, and never sent to review/replace helpers | Current/history selector and click absence | Inspect history and confirm no action control |
| UI-RR-06 | Failed current replacement exposes only targeted retry; a successful retry refetches before continuation | Retry response plus authoritative queries and exact calls | Retry affected evidence on the same case |
| UI-RR-07 | Continue appears only for actual failed-replacement lineage at `PENDING_INPUTS` and calls `/resume` once | Positive/negative lineage matrices and duplicate-click prevention | Continue recovered intake; observe re-evaluated state |
| UI-RR-08 | 409 refreshes evidence and reports stale conflict without optimistic success | `ApiError(409)` fixture and refetch assertions | Optional browser conflict interception if stable; component evidence remains mandatory |
| UI-RR-09 | 401 clears session; absent/inaccessible case is the same safe 404 presentation | Existing auth/navigation suite extended for new action | Guarded login/case-access journey retains generic unavailable state |
| UI-RR-10 | Network/503 uncertain mutation outcome is never replayed; one read refresh recovers truth | Deferred rejection/503 with exact mutation count one | Route interception or backend fault fixture where supported |
| UI-RR-11 | Pending A success/failure cannot publish after A->B navigation, Back/Forward, logout, or actor change | Extend Phase 15C deferred-promise cases for review/retry/resume | Navigate during an in-flight action; B remains untouched |
| UI-RR-12 | Buttons prevent double click and expose pending semantics | Component interaction and exact call count | Double-click one action; one request only |
| UI-RR-13 | Refresh/deep link reconstructs current/history/recovery controls from server state only | Remount with empty QueryClient and backend fixtures | Reload the case URL and observe the same authoritative controls |
| UI-RR-14 | Assignment, generic return-for-rework, final approval, and fake-enabled controls are absent | UI V2 truthfulness assertions and forbidden URL scan | Browser shows only supported controls |
| UI-RR-15 | Native navigation, network guard, and Mock/provider truth remain intact | Existing Phase 15C/UI suites | Existing protected-login and clean Mock workflow tests remain green |

Do not encode inherited test counts as acceptance criteria; record actual collected and
passed counts for the execution revision.

## Execution-time verification commands

Run only in a separately authorized implementation/review task after dependencies are
available:

```powershell
Set-Location apps/frontend
npm test -- src/pages/DocumentEvidencePanel.test.tsx src/UiV2Integration.test.tsx src/Phase15CNavigation.test.tsx
npm test
npm run typecheck
npm run build
npm run e2e
Set-Location ../..
python -m unittest discover -s tests/contract -p "test_*.py" -v
python scripts/check_architecture.py
python scripts/check_project_state.py
python scripts/check_secrets.py
python scripts/pre_pr_check.py
```

The implementer must inspect the final diff and run whitespace/final-newline checks over
tracked files and every new task-owned file before independent review. `pre_pr_check.py`
belongs to the later clean committed PR-readiness state and must not be misreported if
that prerequisite is absent.

## Tool and environment preflight

Planning-time observations:

- Local file/shell inspection and `apply_patch` are available with write permission only
  in the assigned workspace; no sibling worktree or protected file was inspected.
- Git 2.55.0, Python 3.12.10, Node 22.23.2, npm 10.9.8, and ripgrep 15.2.0 are available.
- `python scripts/dev_context.py` ran successfully and reported the exact clean baseline.
- `apps/frontend/package-lock.json`, Playwright configuration, and
  `scripts/run_e2e.py` are present.
- `.venv` and `apps/frontend/node_modules` are absent. No dependency was installed and
  no frontend/backend/browser/lifecycle test was run in this planner.
- No browser, database, provider, remote connector, credential, or external plugin was
  used. No port or disposable database was reserved.
- Execution requires installed locked frontend dependencies, the repository's Python
  test dependencies, Playwright Chromium, and free repository-managed backend/frontend
  ports. The guarded runner must own lifecycle and network policy.
- Mongo is not required for this frontend-only slice. Do not inspect a Mongo URI or use
  `clm_poc`.

Missing dependencies block local test/build/browser evidence only; they do not weaken
the implementation or independent-gate requirements.

## Deferred and sponsor-dependent features

- reviewer assignment, self-assignment, queues, reassignment, and actor attribution;
- generic Return for rework / Request additional information mutation;
- sponsor-approved reviewer roles, separation of duties, confidence/document policy,
  retention, and audit authority (Q-014/Q-015/Q-016);
- automatic source precedence or unrestricted document override;
- final approval, Ready-for-Approval, compliance/risk decision, or real target action;
- new API fields such as `is_current_evidence`; use actual lineage instead;
- new backend endpoints, schemas, workflow transitions, or persistence owners;
- registry cache/refresh behavior and all Phase 16 work;
- production-host fallback or any Live provider claim.

If product owners later authorize any deferred item, plan it as a separate
contract/authority slice. It must not be smuggled into this frontend execution.

## Parallel and integration boundaries

Phase 16 registry-cache planning is separate. This plan writes no Phase 16 artifact and
proposes no registry/cache/orchestration/backend change.

Potential future shared frontend conflict surfaces are:

- `apps/frontend/src/pages/CaseDetail.tsx`;
- `apps/frontend/src/styles.css`;
- `apps/frontend/src/UiV2Integration.test.tsx`;
- `apps/frontend/src/Phase15CNavigation.test.tsx`;
- `apps/frontend/e2e/authenticated-zero-touch.e2e.ts`.

One implementation writer should own this slice. Serialize edits/integration if another
branch touches those files. Do not edit `App.tsx`, `api.ts`, shared types, or query/auth
owners merely to avoid a conflict. The integration owner must reconcile current-main
intent and rerun all affected frontend/browser evidence; no blind ours/theirs choice.

## Execution readiness view

- Intent lock: expose only already supported current-evidence review and bounded recovery
- Scope fence: the proposed frontend files/tests above; no backend/API/schema/provider or
  Phase 16 change
- Baseline lock: `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
- Approved behavior: the control matrix and acceptance IDs UI-RR-01 through UI-RR-15
- Owner constraints: URL, auth, React Query, backend RBAC, document/reconciliation,
  orchestration, and target-ledger owners remain singular
- Compatibility boundary: all invariants in this plan
- Retirement boundary: remove only the unsupported assignment/rework disclosure
  components after confirming no consumers
- Task batches: evidence panel; field decisions/recovery; unsupported-control removal;
  Playwright/broad verification
- Review gates: implementer self-review, full affected verification, then fresh
  independent quality gate
- Drift rule: stop if main changes API shapes, Phase 16 overlaps the shared files, or
  implementation needs any intentionally unchanged owner
- Evidence before completion: revision-specific focused/full/type/build/Playwright,
  governance, diff/hygiene, and independent PASS
- Advisory boundary: this plan is execution guidance, not completion authority

## Recommended execution and review model

- Implementation: one Sol/Medium writer in the existing assigned branch after an owner
  explicitly authorizes implementation; no parallel implementation writers
- Specialist support: optional narrow read-only accessibility/browser falsification, not
  a second writer
- Independent quality gate: fresh Sol/Medium reviewer with no implementation role,
  focused on mutation truth, stale callbacks, RBAC/safe 404, accessibility, and browser
  evidence
- Publication/integration: separate role only after exact independent PASS and explicit
  authorization

No implementation, dependency installation, staging, commit, push, PR, merge, cleanup,
or independent quality-gate claim is authorized by this planner.

## Plan pressure test and final decision

- Owner/contract: all proposed controls map to existing public routes and existing
  canonical owners
- Architecture integrity: no duplicate state owner, route identity, authorization rule,
  or workflow progression path is introduced
- Verification: every required user-visible behavior and adverse case maps to a
  deterministic test; the affected journey also has guarded real Playwright evidence
- Task executability: file boundaries, stop conditions, request bindings, refresh rules,
  and exact commands are specified
- Pressure result: proceed with the bounded supported slice

**UI PLANNER HANDOFF COMPLETE**
