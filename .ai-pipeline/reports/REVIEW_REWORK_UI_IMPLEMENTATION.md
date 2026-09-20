# Review/Rework UI Follow-up — Implementation Report

Date: 2026-09-20<br>
Role: implementation writer and self-reviewer (not an independent quality gate)<br>
Status: implementation and bounded independent-QG remediation complete; ready for fresh independent re-review

## Independent-QG remediation

The 2026-09-20 independent gate returned `FAIL`. This follow-up changed only findings
F-01 through F-04:

- F-01: recovered-intake continuation now fails closed when **any** current document is
  `FAILED`, including a second unrelated current document. A multi-document regression
  proves that negative case.
- F-02: Priority, Delete (including an already-open confirmation), exception resolution,
  reconciliation resolution, safe recovery, and evidence actions are serialized behind
  the existing `CaseDetail` identity-token mutation owner. Cross-control tests prove both
  evidence-then-priority/delete and priority-then-evidence/delete exclusion. No second
  cache or mutation owner was introduced.
- F-04: replacement and targeted-retry uploads now use visually hidden but native,
  labelled, keyboard-focusable file inputs with a visible `:focus-within` outline.
  Component tests cover both controls and execute targeted retry through that input.
- F-03: the real guarded browser journey now completes all four supported field reviews,
  observes the current document become backend-authored `REVIEWED`, proves no browser
  `/resume`, focuses and uses the replacement input, waits for authoritative
  supersession, and reconstructs read-only history after reload. The public guarded
  runtime still cannot create a failed replacement: `e2e_backend_server.py` explicitly
  disables demo controls and the public deterministic local provider exposes no fault
  selector. No backend/setup endpoint, hidden fixture, or interception was added.
  Targeted retry/refetch and continuation positive/negative eligibility are maximized in
  deterministic UI tests.

## Final F-03 stabilization cycle

The fresh re-QG accepted F-01, F-02, and F-04 but retained F-03 because neither of its
two guarded runs completed the supported browser journey. The final authorized cycle
followed the systematic-debugging route before editing:

- An unchanged, instrumented three-run reproduction printed sanitized output from every
  owned process at teardown. Results were one 3/3 pass followed by failures at test 2
  login and test 3 login. In all runs Vite was healthy in 335–398 ms, backend output was
  empty, and owned lifecycle cleanup completed; passing and failing service output was
  otherwise identical.
- The failing test helper waited for the `Dashboard` heading after login. That heading
  depends on a separate dashboard query and is not the authenticated-session boundary.
  The clean lane likewise waited only for a transient live-view completion projection.
  The causal classification is therefore E2E synchronization at the consumer boundary,
  not a product behavior or runner lifecycle defect.
- The smallest repair changes only the existing E2E file: login waits for the
  authenticated `Main workspace` navigation; clean onboarding captures the retained case
  URL, polls the public case route for backend-authored `COMPLETED`, then opens the
  canonical Case Detail route and verifies the completed Mock projection. Review and
  supersession waits remain bound to fresh public document state. No sleep, retry,
  weakened assertion/network guard, runner change, product change, fallback, demo
  control, or fault route was added.
- The first post-repair run exposed an incorrect diagnostic reload target:
  `/new-onboarding/:caseId` intentionally owns `RetainedIntakeRecovery`, not the completed
  projection. Rebinding the assertion to canonical `/cases/:caseId` resolved that
  deterministic test error. The consecutive-pass count restarted from zero.
- Final repeatability evidence: three consecutive full guarded suite passes, each 3/3,
  in 9.5 s, 9.0 s, and 8.3 s. This is the exact final E2E content identified below.

Repair disposition: the authored test now observes the authoritative conditions it
claims. Retirement disposition: downstream `Dashboard` and live-view completion waits
were retired as readiness owners while both views remain valid product capabilities.
Confidence is B because the recurrence loop is clean and service lifecycle was directly
observed, while only a bounded three-run sample was authorized.

## Revision and scope

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-review-rework-ui`
- Branch: `followup/review-rework-ui`
- `BASE_SHA`, current `HEAD`, local `origin/main`, and merge base:
  `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
- Current source is an uncommitted working tree based on that SHA. The tested behavior is
  the exact task-owned file content identified below, not a commit SHA. No independent
  content revision has yet been reviewed.
- Change classification: `FRONTEND_UI` and `FRONTEND_STATE_CACHE`.
- Owner boundary: `CaseDetail` remains the mutation, authenticated query-cache,
  authoritative-refresh, and case/actor/generation owner. `DocumentEvidencePanel` owns
  rendering and ephemeral correction-form state only.
- No backend, public API, shared type/model, persistence schema, connector/provider,
  configuration, dependency, mapping, business rule, authorization policy, cache-key,
  or architecture-owner change was made.
- No commit, push, branch switch, PR, merge, staging, or publication action was taken.

## Preflight and authority

The implementation followed `AGENTS.md`, the current project state, architecture and
development workflow, the document-review/automation/access contracts, current source
and tests, nearest accepted gates, the frontend-state-cache and phase-execution skills,
and the supplied `REVIEW_REWORK_UI_FOLLOWUP.md` planner. `python scripts/dev_context.py`
passed at task start. The execution environment provided Python 3.12.10, Node 22.23.2,
npm 10.9.8, a task-local `.venv`, installed frontend dependencies, Playwright Chromium,
and free assigned loopback ports 8867/4275. Network access was not required.

The interrupted-review contract was checked against the backend owner and tests before
implementation. The resulting execution clarification is recorded in
`.ai-pipeline/001_planner/REVIEW_REWORK_UI_EXECUTION_ADDENDUM.md`: only a current,
fully final `REVIEWED` document on a `WAITING_FOR_REVIEW`/`DOCUMENT` case exposes a
distinct exact-repeat checkpoint repair. Its request is reconstructed from retained
typed `field_key`, final `review_status`, raw `reviewed_value`, and raw `review_note`.
It is not an edit and never causes a browser `/resume` call.

## Implemented behavior

- Current evidence is shown ahead of collapsed superseded history. Historical evidence
  includes its lineage and has no mutation or upload controls.
- Current pending fields show suggestion, canonical comparison, confidence, provenance,
  review status, and only the existing valid Accept/Reject/Correct actions. Accept is
  absent when no suggestion exists. The correction fieldset focuses on open, supports
  Escape/Cancel focus return, and applies the existing 512/240 limits.
- Final decisions are read-only. Missing or below-case-threshold original evidence with
  a retained correction is explicitly labelled replacement-required.
- Partial counts and independent-blocker wording are dynamic. Local/Mock and not-approval
  labels remain explicit.
- Current failed evidence exposes targeted retry only for
  `DOCUMENT_REUPLOAD_REQUIRED`. Continue is exposed only for authoritative
  `PENDING_INPUTS`/`DOCUMENT` state with the latest matching timeline checkpoint and
  bidirectional current-to-failed supersession lineage.
- Review, replacement, retry, and explicit recovered-intake continuation use one
  settlement path. Success, 409, 503, and ambiguous transport outcomes perform one
  bounded authoritative read of case, documents, and ownership. There is no mutation
  replay. A refresh failure preserves last-confirmed data, locks mutation controls, and
  exposes only an explicit read-only refresh; safe 404 uses the generic unavailable
  view.
- A synchronous identity-token lock rejects same-tick duplicates. Awaited results are
  contained by generation, case ID, and actor ID so stale A or old-actor completion
  cannot update B, clear B's active lock, publish errors, or navigate.
- Unsupported Assign reviewer and Return for rework affordances were removed from Case
  Detail. Their component files were retained because repository search found active
  `HomeOnboarding.tsx` consumers outside this planner's write boundary.

## Files

Created:

- `.ai-pipeline/001_planner/REVIEW_REWORK_UI_EXECUTION_ADDENDUM.md`
- `apps/frontend/src/pages/DocumentEvidencePanel.tsx`
- `apps/frontend/src/pages/DocumentEvidencePanel.test.tsx`
- `.ai-pipeline/reports/REVIEW_REWORK_UI_IMPLEMENTATION.md`

Modified:

- `apps/frontend/src/pages/CaseDetail.tsx`
- `apps/frontend/src/pages/DeleteCaseDialog.tsx`
- `apps/frontend/src/pages/PriorityControl.tsx`
- `apps/frontend/src/styles.css`
- `apps/frontend/src/UiV2Integration.test.tsx`
- `apps/frontend/src/Phase15CNavigation.test.tsx`
- `apps/frontend/e2e/authenticated-zero-touch.e2e.ts`

The supplied untracked planner was preserved unchanged. No other source file was edited.

## Verification evidence

All results below were produced in this worktree. The final source change was followed
by fresh focused tests, full tests, typecheck, build, and guarded browser verification.

| Check | Result |
|---|---|
| Focused Vitest: `DocumentEvidencePanel`, UI V2 integration, Phase 15C navigation | PASS — 3 files, 87/87 tests |
| Full frontend Vitest | PASS — 10 files, 205/205 tests, including Vite history fallback 1/1 |
| Frontend typecheck | PASS |
| Production frontend build | PASS — Vite 7.1.11, 109 modules; JS 355.07 kB (103.22 kB gzip), CSS 61.04 kB (13.02 kB gzip) |
| Guarded Playwright on backend 8867/frontend 4275 | PASS repeatability loop — three consecutive full-suite runs, each 3/3, in 9.5s, 9.0s, and 8.3s |
| Canonical contract suite | PASS — 44/44 tests |
| `check_architecture.py` | PASS |
| `check_project_state.py` | PASS |
| `check_tooling_config.py` | PASS |
| `check_secrets.py` | PASS |
| `dev_context.py` | PASS |
| `git diff --check` | PASS; only Git LF-to-CRLF working-copy notices |
| Task-owned final-newline check | PASS for every implementation/addendum/test file |
| Assigned loopback lifecycle | PASS — ports 8867 and 4275 free after guarded cleanup |

The browser journey uses the real public local Mock API. It proves authenticated access,
a same-tick partial decision with one exact POST, all four supported reviews and
backend-authored `REVIEWED` state, no `/resume`, authoritative reads between durable
checkpoints, keyboard focus on replacement, successful replacement, read-only superseded
history, reload/deep-link reconstruction, and truthful Mock/not-approval labels. Its
readiness/state polls are read-only.

The guarded runner's final prose still says `2 authenticated local Mock smoke tests`;
that is stale CI-tooling text and was intentionally not edited because CI tooling is
outside scope. The authoritative Playwright runner output directly above it reports
`3 passed`.

Focused tests additionally cover exact retained repair payloads; positive and negative
repair eligibility; missing and low-confidence replacement-required wording; current
versus historical actions; partial counts; valid decision controls; correction focus and
limits; failed-replacement continuation lineage; refresh-failure mutation lock; one
refresh after 409/503/network ambiguity; no replay/resume; same-tick duplication; safe
404; and stale case/actor success and failure containment.

Observed non-product failures were resolved and retained as diagnostic context:

- sandboxed Vite/esbuild initially returned `spawn EPERM`; the same repository commands
  passed with the approved process-spawn permission;
- early browser drafts assumed an unavailable demo-control route and then observed the
  real case URL before document creation; the journey was corrected to use the public
  mismatch fixture and a bounded read-only readiness poll;
- one intermediate rerun timed out on the pre-existing login test; subsequent fresh
  guarded runs passed all three tests, including the final tested content;
- remediation browser attempts exposed timing at initial Case Detail render and
  intermediate review-count rendering, plus isolated unchanged clean-flow/login
  timeouts. The authored lane now waits for durable public document state and reloads
  from that authoritative state. On the pre-stabilization remediation source, one run
  passed tests 1/2 but timed out at test 3 login; the immediate fresh rerun passed 3/3 in
  9.7 seconds. Both outcomes are retained as historical evidence; the final synchronization
  repair and its three-run repeatability result are recorded above;
- existing React SSR `useLayoutEffect` warnings remain in UI V2 tests and do not fail
  the suite.

The public guarded runtime cannot deterministically create a failed replacement: its
normal replacement path uses the deterministic local provider and exposes no public
replacement-fault control. No fabricated production fixture or browser interception was
added. Positive/negative recovery lineage and action ownership are therefore proven in
the deterministic component/navigation suites; the real browser covers review,
replacement, history, refresh, and deep-link behavior.

## Tested content identity

SHA-256 values for the exact implementation/addendum/test files used by final
verification:

```text
101828E18D25EEB11FC80B9CC934B7DB4DFEF9666AAF394261B50951EE26E01D  .ai-pipeline/001_planner/REVIEW_REWORK_UI_EXECUTION_ADDENDUM.md
623D040CB361D51839A51878A1402A279FBCE4FBC3A434381B793D2541521FBC  apps/frontend/e2e/authenticated-zero-touch.e2e.ts
0FAEFA580F454CBDA7664DDE98ACA27839860ACCA4E9DF030B119A2452B248C0  apps/frontend/src/Phase15CNavigation.test.tsx
74C9687E321B5C84C1A4E09FAA8AB577866BBCE43666537574119D4470000C58  apps/frontend/src/UiV2Integration.test.tsx
6C26E08E29190CF39BBB19C57E9905DFFF8BC2B3F96B221378C3FB1DB1A855CA  apps/frontend/src/pages/CaseDetail.tsx
EDFC82F145429BDDD6D94777643E019098DEC0184F475B2C64D0FCBA0FD18090  apps/frontend/src/pages/DeleteCaseDialog.tsx
F836C47FFA0628A4EA0CFD10A4013E22B38A2FDD7185E62F039531DC4EF18C8F  apps/frontend/src/pages/DocumentEvidencePanel.tsx
CFC09FE4A083EDB58013059F8B6781FEE4CA93E1BC5966F915D4A9DCEF17396B  apps/frontend/src/pages/DocumentEvidencePanel.test.tsx
6A1E9A27BB8411B69C4A9057A9DDF3C1443DFD41CB9C1336CC03D4275DB53A81  apps/frontend/src/pages/PriorityControl.tsx
FED28E1A9C58EFF1A203A23F342AD0BCC02702B67E4EB772240FF3A72535437E  apps/frontend/src/styles.css
```

`pre_pr_check.py` was not run or claimed: the governing planner assigns it to the later
clean committed PR-readiness state, while this implementer was explicitly prohibited
from committing. The next authorized action is a fresh independent quality gate over
the exact content above. Publication remains contingent on exact independent PASS and
separate Git/publication authority.
