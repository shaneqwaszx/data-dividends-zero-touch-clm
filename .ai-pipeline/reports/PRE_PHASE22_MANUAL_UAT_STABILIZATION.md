# Pre-Phase 22 Manual-UAT Stabilization

## Outcome and revision boundary

This is a stabilization candidate on branch
`fix/pre-phase22-manual-uat-stabilization`, based exactly on accepted main
`ef338c9b7926a298e8987acb975fd93c96ed2bfb` (tree
`003c7b56685da22071fd31ec5a28b8bbf6f06e5b`, successful push CI
`35671556733`). It does not start Phase 22.

Product behavior changed only in the frontend presentation layer. No backend runtime,
API/model/type, persistence schema/data, connector/provider, configuration behavior,
mapping, auth/RBAC, business rule, target-ledger, React Query/cache, or architecture
owner changed. One narrow Windows CI/tooling verifier correction was required so the
mandated architecture check can resolve Git and inspect a dirty candidate containing
tracked deletions.

## Responsive root cause and correction

The authenticated navigation stayed on a single flex row until 1100px even though its
brand, tabs, provider banner, and account control exceeded the available intrinsic
width earlier. Fixed-width two-column content waited until 760px to stack, making 768px
particularly vulnerable. Several wide tables and the 30-column dashboard trend also
needed explicit local scroll/paint containment so their contents could not enlarge the
root scroll area.

The shared design-system owner now:

- reflows the nav at 1360px and uses a contained two-row grid at 900px;
- keeps tabs horizontally operable and the environment label visible/understandable;
- constrains account identity text and removes only secondary metadata on narrow mobile;
- stacks fixed two-column and detail side-rail layouts at 900px;
- wraps page-header and client actions;
- gives wide tables, tabs, and the trend local inline-size/paint containment while
  preserving operable horizontal scrolling; and
- makes the mobile trend fit its owner rather than adding document overflow.

The guarded browser test asserts actual root scrolling cannot move, body/main/nav and
essential control bounding boxes remain within the viewport, and known table scroll
containers retain `overflow-x: auto` plus a working local `scrollLeft` range.

The first independent gate found that the original test implementation repeatedly used
full document reloads for ordinary in-app navigation. With the 105-case E2E seed, those
rapid reloads repeatedly recreated authentication and abandoned background route/query
work; the focused lane then stalled at shifting later routes, sometimes on the session-
restoration screen. The product is a React Router SPA and normal UAT navigation uses its
links. The test now follows those real workspace links for ordinary route changes and
retains full reloads only for the explicit login/deep-link checks. This is a test-
lifecycle correction, not an authentication, routing, query, or backend runtime change.
The exact focused command then passed four fresh owned-process repetitions in 12.9,
13.1, 12.9, and 12.9 seconds.

The same recurrence also appeared in the existing supported document-review browser
test, which previously reloaded the entire application before each field decision.
That test now keeps its initial authenticated deep link and final persistence reload,
but verifies intermediate decisions through the live authoritative mutation/refetch
path. It passed two fresh isolated lifecycles in 5.7 and 5.0 seconds. The suite-wide
shared-backend lifecycle can still stall before that test's initial deep link after
earlier tests. The second independent gate therefore correctly returned `FAIL` on the
exact configured unfiltered command rather than accepting isolated substitutes.

The canonical CI runner now discovers every configured Playwright test from Playwright's
own JSON listing and runs each exact file/line selector in a fresh owned backend,
frontend, credential, browser, and memory-store lifecycle under one unchanged overall
deadline. Focused `--grep` runs retain their single lifecycle. The runner stops on the
first failed selector; it does not skip, retry, quarantine, hard-code, or weaken any
test. Remaining ordinary full reloads in authenticated browser tests were replaced by
real workspace links, while deliberate login, deep-link, and persistence reloads remain.
The final candidate passed the exact unfiltered CI command twice consecutively, 7/7 each.

Tested widths: **360, 390, 480, 768, 1024, 1280, and 1440px**. Covered login,
Dashboard, New onboarding, Cases, Case Detail/current field review, Onboarded,
Onboarded Detail, Audit, Policy, delete confirmation, and HR administration routes.

## Account hover/focus

Root cause: `styles.css` owns a broad dark-green
`button:hover:not(:disabled)` rule, while the design-system account pill did not own a
more specific hover state. The account button now has a scoped light-neutral hover,
slightly stronger neutral border, and unchanged high-contrast text. The existing
design-system `:focus-visible` outline remains. Browser coverage verifies the computed
background is not green, text remains `rgb(32, 31, 29)`, and keyboard focus has a
visible outline. Other button states were not changed.

## Assignment and generic rework truthfulness

Q-016 and Phase 20 continue to withhold reviewer assignment/reassignment and generic
return-for-rework authority. `HomeOnboarding` was the last consumer of the two
disclosure dialogs. Its active-looking **Assign reviewer** and **Return for rework**
buttons, local-only dialog state, obsolete disclosure suffix, and now-unowned dialog
components were removed.

Backend-authorized `exception.available_actions` remain rendered. Current-evidence
field review, reviewed-value reconciliation, replacement/re-upload, partial-review
blocking, recovery/resume, and no-replay behavior are unchanged. Focused unit and
guarded browser assertions prove the supported action remains and the two unsupported
actions are absent from operational screens.

## Mongo diagnosis

Result: **A — data still exists; memory mode merely hides it.** Mongo was reached by a
read-only probe. `clm_poc.clm_case_snapshots` exists with 14 case envelopes, all safe
schema-version count v2. Expected administration collections contain 2 teams, 6
profiles, and 1 policy. The older diagnostic `FYP.users` namespace also exists with 2
documents but is not the durable case store. No raw document or case payload was read
or printed, and no URI/host/credential was emitted.

The ephemeral probe performed only ping, labels, counts, and a schema-version
aggregation, then was removed. No Mongo write, delete, drop, cleanup, migration,
repair, or physical mutation test ran. See
`PRE_PHASE22_MONGO_DATA_DIAGNOSIS.md` for the safe evidence and deletion-owner review.

## ACRA teammate-history reconciliation

The reported file existed at
`apps/backend/app/connectors/garden_business_shareholders.py`. Rika Miyachi introduced
it in unmerged commit `79e808f24a46b099ee111a0fa57492fa01a10a49` on the
`acra-integration` line. Commit `6bcea75efd660e6dbaaa5dc2079b62749fc0abf1`
then deleted it and its project-defined Garden special-case behavior while retiring
speculative BizFile activation. No current head of `main`, `origin/acra-integration`,
or `origin/CRUDoperations` contains the file.

Current main does contain Rika's accepted initial connector commit `4ae4ed19...` and
the accepted `74a5fd2f...` OAuth/security remediation. Her later `897a4c4...` provider-
composition attempt and `79e808f...` Garden special case remain outside main. This task
made no ACRA source change. Restoring either would alter provider behavior/mapping and
requires separate explicit authorization. See
`PRE_PHASE22_ACRA_TEAMMATE_RECONCILIATION.md`.

## Phase 15 to current summary

| State | Delivered / runtime-visible behavior | Deliberately unsupported or unchanged |
|---|---|---|
| 15A | Authority-labelled evidence terminology and future-policy boundaries. | No ageing/OCDD/perpetual-KYC, supplied-risk reaction, or production handoff. |
| 15B | Current-evidence review, reviewed-value reconciliation, replacement/re-upload, partial-review blocking, and bounded resume/recovery. | No assignment, generic rework, final approval, or generic additional-information workflow. |
| Review/rework UI follow-up | Exposed supported field review with stale identity/case/session containment; removed unsupported actions from Case Detail. | `HomeOnboarding` disclosure consumers remained until this stabilization. |
| 15C | Router-owned URLs, deep links/history, case identity, stale-callback isolation, truthful Vite fallback. | No new backend route or browser authorization owner. |
| 16 | Optional exact-key, elapsed-time synthetic Mock ACRA snapshot reuse with memory/Mongo cache stores and case evidence binding. | Disabled by default; no sandbox/Live cache reuse. |
| Evidence Workbench | Read-only minimized registry binding, Decimal ownership paths, workflow/blocker/readiness/ledger explanation. | No provider rerun, approval, compliance/risk or legal-UBO claim. |
| Attention Queue | Backend-authoritative current blocker portfolio projection. | No risk score, SLA, assignment engine, escalation, or workflow owner. |
| 17 | Bounded retained-event activity explorer with filters/paging. | No actor attribution, export, retention/archive, snapshot isolation, or production audit claim. |
| 18 | Authorized bounded case search/pagination while preserving the legacy array endpoint. | No production-scale indexing or snapshot traversal. |
| 19 | Backend-authored factual age and automated-stage durations with chronology guards. | No SLA, timing policy, escalation, approval, or risk inference. |
| 19 post-merge clock fix | Propagated the deterministic injected clock through the canonical orchestrator seam. | True chronology violations still fail closed. |
| 20 | Machine-checked sponsor-policy authority registry and traceability. | No unresolved business policy activated; Q-001–Q-018 remain open. |
| 21 | Provider-readiness registry, positive sanitized-evidence profiles, activation packet/runbook, CI/tooling governance. | No provider activation, credential consumption, sandbox/Live proof, or Phase 22 authority. |

## Files changed

Product/tests:

- `apps/frontend/src/design-system.css`
- `apps/frontend/src/pages/HomeOnboarding.tsx`
- `apps/frontend/src/App.tsx`
- `apps/frontend/src/Phase13AuthPriority.test.tsx`
- `apps/frontend/src/Phase15ASponsorRebaseline.test.tsx`
- `apps/frontend/e2e/authenticated-zero-touch.e2e.ts` (test-lifecycle only)
- `apps/frontend/e2e/responsive-layout.e2e.ts`
- deleted `apps/frontend/src/pages/AssignReviewerDialog.tsx`
- deleted `apps/frontend/src/pages/ReturnForReworkDialog.tsx`

Tooling regression:

- `scripts/check_architecture.py`
- `tests/test_check_architecture.py`
- `scripts/run_e2e.py`
- `tests/test_run_e2e.py`

Governance/evidence:

- `docs/PROJECT_STATE.md`
- `.ai-pipeline/001_planner/PRE_PHASE22_MANUAL_UAT_STABILIZATION.md`
- this report, the Mongo diagnosis, the ACRA reconciliation, the eventual independent
  quality-gate report, and the task's `docs/aegis` checkpoint/evidence/reflection files.

## Verification

Current successful evidence:

- Focused frontend: 17/17 tests.
- Full frontend Vitest: 19 files, 263/263 tests.
- TypeScript typecheck: PASS.
- Vite production build: PASS, 111 modules transformed.
- Focused responsive guarded Chromium: PASS, seven-width matrix and representative
  authenticated/admin routes; four fresh post-remediation repetitions passed.
- Supported current-document review guarded Chromium: PASS in two fresh isolated
  lifecycles after the bounded same-pattern test repair.
- Case portfolio mutation/deletion guarded Chromium: PASS in isolation.
- Case activity guarded Chromium: PASS in isolation.
- Architecture checker unit suite: 14/14; direct architecture check: PASS.
- E2E runner unit suite: 18/18.
- Project state, tooling configuration, policy authority, external-provider readiness,
  and secret checks: PASS.

Four original shared-lifecycle invocations stalled cumulatively (document review three
times, Cases once). Each affected test passed promptly in a fresh lifecycle. After the
runner isolation repair, one exact run passed 7/7; a repeat exposed one remaining
ordinary reload before a second case creation. That same-pattern site was repaired and
the final candidate then passed two consecutive exact unfiltered 7/7 commands. No
failed run was reclassified as success; the history explains why the runner owner had
to change.

The first independent Sol/High gate correctly returned `FAIL` with PRE22-QG-001 because
the then-frozen responsive lane failed five fresh focused runs. Parent remediation is
limited to the browser test lifecycle and keyboard/retained-route assertions above.
The second independent Sol/High gate correctly returned `FAIL` with PRE22-RQG-001
because the exact configured unfiltered command was still red. Parent remediation then
moved lifecycle isolation to the canonical runner and closed the remaining same-pattern
navigation sites. A third different fresh reviewer must assess the new frozen identity;
only an exact re-QG `PASS` permits the local candidate commit.

Final hygiene, dirty-candidate inventory, independent QG, clean committed-tree pre-PR,
commit/tree identity, and running-demo evidence are appended only after those steps
complete.

## Explicit non-changes

- Backend runtime/provider code changed: **No**.
- API/model/type or persistence schema changed: **No**.
- Mongo data/configuration changed: **No**.
- ACRA/GoldTier/PingFed/IDP/ownership implementation or status changed: **No**.
- Assignment, reassignment, generic return-for-rework, or approval implemented: **No**.
- Phase 22 started: **No**.
