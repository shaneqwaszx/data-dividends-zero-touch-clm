# Pre-Phase 22 Manual-UAT Stabilization Plan

## Goal

Stabilize the accepted Phase 21 main baseline for manual UAT by repairing application-wide responsive layout and the account-hover contrast defect, removing misleading unsupported assignment/rework controls, investigating the apparent Mongo history loss without mutation, reconciling teammate ACRA history without changing provider code, and leaving one independently accepted local candidate running for human UAT.

## Architecture

Frontend presentation remains the only product-change boundary. `design-system.css` owns shared authenticated-shell, responsive-layout, table, dialog, and account-control styling. `HomeOnboarding.tsx` owns the remaining misleading controls and will retain only backend-authorized operational actions. Existing API, React Query, authentication, workflow, persistence, provider, and target-ledger owners remain unchanged. Mongo and Git history lanes are read-only evidence work.

## Tech Stack

React 18, React Router 7, TypeScript 5.9, Vite 7, Vitest 3, Playwright 1.56 guarded Chromium, Python 3.12 governance tooling, Git/GitHub CLI, and PyMongo for a bounded read-only diagnostic.

## Baseline and Authority References

- `AGENTS.md`, `docs/PROJECT_STATE.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT_WORKFLOW.md`, and `docs/demo/DEMO_RUNBOOK.md`
- `docs/sponsor-questions/OPEN_QUESTIONS.md`, especially Q-014 and Q-016
- `docs/contracts/POLICY_AUTHORITY_MATRIX.md` and Phase 20 implementation/QG
- Phase 15B implementation/re-QG and review/rework UI implementation/re-QG
- Phase 21 implementation/QG and provider activation packet
- User-supplied `PRE-PHASE 22 MANUAL-UAT STABILIZATION` brief
- Accepted base `ef338c9b7926a298e8987acb975fd93c96ed2bfb`, tree `003c7b56685da22071fd31ec5a28b8bbf6f06e5b`, successful push CI `35671556733`

## Compatibility Boundary

- Preserve existing visual language, navigation semantics, keyboard focus, route/deep-link behavior, authenticated session ownership, supported field review/reconciliation/replacement/resume behavior, table-local scrolling, and Mock/Local/Dormant provider truth.
- Add no backend/API/model/type, React Query/cache, persistence/schema, provider/connector, mapping, auth/RBAC, business-policy, assignment, rework, approval, or Phase 22 behavior.
- Mongo access is read-only and may emit only safe labels, counts, and schema/count metadata; no URI, credential, raw document, or raw case data may be printed.
- ACRA history reconciliation may describe diffs but may not restore or modify provider code without separate authorization.

## Classification

`FRONTEND_UI`, `DOCS_ONLY`, and a narrow `CI_TOOLING` repair discovered during
verification. The Mongo and ACRA lanes are read-only investigations, not `PERSISTENCE`
or `EXTERNAL_PROVIDER` changes. No ADR or architecture-owner review is required because
no owner, dependency direction, compatibility surface, or runtime boundary changes.
The tooling repairs preserve the parent environment for `git ls-files` on Windows,
inspect the actual candidate after tracked deletions, and give each dynamically
discovered Playwright test a fresh owned backend/frontend/browser lifecycle when the
unfiltered CI command runs. They do not alter application behavior or skip/retry a test.

## Requirement Ready Check

- Requirement source: supplied stabilization brief plus current source/contracts/decisions.
- User scenarios: 360/390/480/768/1024/1280/1440 authenticated and login layouts; readable account hover/focus; truthful operational controls; historical Mongo visibility; teammate ACRA history.
- Acceptance: mechanical overflow/bounding checks, scoped hover computation, unsupported-control absence, supported-review regression, read-only Mongo evidence, all-ref ACRA reconciliation, governance checks, exact independent QG PASS, stable local commit, healthy running demo.
- Open authority: Q-014/Q-016 remain open and require omission of assignment/generic rework, not invention.
- Decision: ready.

## Baseline Usage Draft

- Required refs: all authority references above, current frontend source/tests, persistence settings/composition, dormant BizFile connector/tests/history.
- Acknowledged before plan: complete mandatory context chain, current frontend owners, accepted Phase 15B/20/21 evidence.
- Missing refs: none for implementation; Mongo reachability and the alleged Garden Business file are investigation outcomes.
- Decision: continue.

## Change Necessity and Owner Fit

- User-visible need: current layout can overflow or compress before existing breakpoints; the account pill inherits a dark global hover; `HomeOnboarding` presents unsupported operations as clickable.
- Non-code option: documentation cannot repair layout, contrast, or executable affordances.
- Minimum code boundary: shared design-system CSS, `HomeOnboarding`, focused unit/browser coverage, and removal of now-unowned dialog components/styles.
- Decision: code-change.
- Existing owner reuse: edit the presentation owners; add no runtime owner, fallback, adapter, or parallel state.
- Complexity: `design-system.css` is the correct shared style owner; the large existing E2E file is avoided by a focused responsive E2E file; removing dialog state/imports decreases `HomeOnboarding` complexity.

## TDD Route

- Mode: auto.
- Decision: strict.
- Strict authority: recorded auto decision from systematic debugging for shared responsive/interaction regressions.
- Test posture: strict RED tests in a focused browser file plus a focused `HomeOnboarding` unit assertion.
- RED proves the current 768/1024/1280 shell/column defects, inherited green hover, and remaining executable unsupported controls.
- GREEN proves only the repaired frontend slices; full frontend, governance, browser, self-review, and independent QG remain required.

## Execution Readiness View

- Intent lock: stabilization only; do not start Phase 22.
- Scope fence: frontend product delta plus bounded reports/state closeout and read-only diagnostics.
- Baseline lock: exact accepted SHA/tree/CI above on `fix/pre-phase22-manual-uat-stabilization`.
- Owner constraints: design system and `HomeOnboarding` only for product changes.
- Retirement boundary: remove remaining unsupported dialog consumers and component files only after repository-wide reference proof.
- Test obligations: RED/GREEN focused tests, full frontend, guarded multi-viewport Chromium, supported review regression, governance/security/hygiene, and pre-PR inventory.
- Review gate: fresh independent Sol High reviewer owns only the assigned QG report; exact PASS required.
- Drift rule: stop the dependent lane for provider/persistence mutation, unresolved authority, changed baseline intent, unsafe data access, or repeated design failure.

## Task 1 — RED: responsive, hover, and unsupported-action regressions

Files:

- Create `apps/frontend/e2e/responsive-layout.e2e.ts`.
- Modify the narrow existing `HomeOnboarding` test coverage in `apps/frontend/src/Phase13AuthPriority.test.tsx`.

Steps:

1. Add guarded-browser helpers that assert document width containment and bounding boxes for nav, brand, tabs, provider banner, account control, principal form/actions, local table scrollers, and a dialog.
2. Cover viewport widths 360, 390, 480, 768, 1024, 1280, and 1440; exercise login, Dashboard, New onboarding, Cases, Case Detail/review state, Onboarded, Onboarded Detail, Audit, Policy, and applicable admin routes at representative desktop/tablet/mobile widths.
3. Hover the account button and assert a light neutral background, readable text, and scoped focus-visible behavior.
4. Render an active-exception `HomeOnboarding` state and assert assignment/rework do not appear as executable buttons while backend-authorized actions remain.
5. Run the focused Vitest and guarded E2E grep and record the expected failures before production edits.

Verification:

```powershell
npm.cmd --prefix apps\frontend test -- --run src\Phase13AuthPriority.test.tsx
python scripts\run_e2e.py --grep "responsive shell"
```

## Task 2 — GREEN: owner-level frontend repair and retirement

Files:

- Modify `apps/frontend/src/design-system.css`.
- Modify `apps/frontend/src/pages/HomeOnboarding.tsx`.
- Delete `apps/frontend/src/pages/AssignReviewerDialog.tsx` and `apps/frontend/src/pages/ReturnForReworkDialog.tsx` only after confirming zero remaining consumers.

Steps:

1. Move authenticated-nav reflow to the content-pressure range and use grid/flex/minmax/wrapping so tabs, banner, and account control remain contained and keyboard reachable.
2. Keep the environment label visible and meaningfully truncated; reduce account metadata at narrow widths without hiding the operable identity control.
3. Collapse fixed two-column/side-rail layouts before 768px pressure and make header/actions wrap without page expansion.
4. Add a scoped `.operator-account__button:hover:not(:disabled)` light-neutral rule and retain the shared focus-visible rule; do not alter other button hovers.
5. Remove unsupported disclosure buttons, dialog state/imports/rendering, and the obsolete disclosure style/component files. Preserve every backend-authorized action and supported review/reconciliation/replacement/resume path.
6. Rerun the focused tests until GREEN, then refactor only duplication introduced by this slice.

Verification: the Task 1 commands must pass.

## Task 3 — Read-only Mongo diagnosis

Files:

- Create `.ai-pipeline/reports/PRE_PHASE22_MONGO_DATA_DIAGNOSIS.md`.

Steps:

1. Use validated application settings only to obtain safe database/collection labels and internally consume the secret URI without printing it.
2. Ping Mongo, list database and collection labels, and count the configured case collection plus expected CLM collections. Emit only labels/counts/schema-version counts.
3. Compare alternate database labels and inspect tracked Git/scripts/history for deletion owners only if the configured collection is empty/missing.
4. Classify the observed result A-E and explain that `memory` mode hides Mongo-backed history but does not delete it.

Stop: no insert, update, delete, drop, migration, repair, cleanup, raw document readback, or URI/credential output.

## Task 4 — ACRA teammate-history reconciliation

Files:

- Create `.ai-pipeline/reports/PRE_PHASE22_ACRA_TEAMMATE_RECONCILIATION.md`.

Steps:

1. Search all reachable refs and history case-insensitively for Garden/shareholder/BizFile terms and likely fixture keys.
2. Inspect teammate-authored commits, branch ancestry, deleting diffs, `branch --contains`, and comparisons among main, `acra-integration`, `CRUDoperations`, and every relevant ref.
3. Classify any content as source, fixture, sample, test, documentation, or untracked/confidential and list exact commit/path facts.
4. Stop the lane if restoration would alter provider behavior, API/schema/auth/network/mapping/composition; report the exact diff for human authorization.

## Task 5 — State closeout and implementation report

Files:

- Modify `docs/PROJECT_STATE.md` narrowly for `verified_main_sha=ef338c9...` and Phase 21 accepted status.
- Create `.ai-pipeline/reports/PRE_PHASE22_MANUAL_UAT_STABILIZATION.md`.
- Maintain `docs/aegis/work/2026-09-22-pre-phase22-manual-uat-stabilization/*` checkpoints/evidence/reflection.

Steps:

1. Preserve provider classifications and every open sponsor question.
2. Record root causes, viewport matrix, hover fix, unsupported-action authority, Mongo classification, ACRA history result, exact file/change boundaries, and no backend/provider/Mongo-data change.
3. Include the requested Phase 15A-to-21 concise delivered/runtime/unsupported table.

## Task 6 — Broad verification and self-review

Run:

```powershell
npm.cmd --prefix apps\frontend run typecheck
npm.cmd --prefix apps\frontend test -- --run
npm.cmd --prefix apps\frontend run build
python scripts\run_e2e.py --grep "responsive shell|current document review"
python scripts\check_project_state.py
python scripts\check_architecture.py
python scripts\check_tooling_config.py
python scripts\check_policy_authority.py
python scripts\check_external_provider_readiness.py
python scripts\check_secrets.py
git diff --check
```

Inspect the complete tracked and task-owned-new-file diff, run the current pre-PR checker inventory appropriate to the dirty candidate, and challenge every self-review question in the user brief. Record failures as defects, missing infrastructure, stale evidence, or unresolved authority; repair only in scope and rerun affected checks.

## Task 7 — Independent quality gate

1. Freeze the reviewed path set and content identity.
2. Dispatch one fresh independent `gpt-5.6-sol` reviewer at High reasoning using `fyp-quality-gate`; it may write only `.ai-pipeline/reports/PRE_PHASE22_MANUAL_UAT_STABILIZATION_QUALITY_GATE.md`.
3. Require exact `PASS`. On findings, the parent remediates, reruns affected checks, and dispatches a fresh independent re-QG.

## Task 8 — Freeze local candidate and leave demo running

1. After exact PASS, stage only reviewed task-owned files, inspect the staged diff, and create the authorized local commit `fix(ui): stabilize pre-phase22 manual uat`.
2. Record commit/tree and clean status. Do not push, create a PR, or merge.
3. Start `scripts\start_demo_windows.bat`, verify launcher ownership plus frontend/backend health, and leave the demo running at the documented URLs.

## Risks and Retirement

- Browser data/setup may expose a pre-existing responsive issue outside the shared owner; diagnose before widening scope.
- The unfiltered browser suite may accumulate process-local test data/work across tests; isolate configured tests at the runner owner rather than weakening assertions or product behavior.
- Mongo may be unreachable; classify C rather than claiming deletion.
- Git history cannot establish untracked/confidential teammate material; request exact filename/branch/SHA if absent.
- Retire only the two unsupported dialog components and disclosure style once all consumers are removed. No supported capability or carrier is retired.
- Rollback surface is limited to the frontend CSS/component/test delta and documentation; no data or provider rollback exists because those lanes are read-only.

## Execution Route

- Decision: inline.
- Evidence: one implementation writer is required; product edits overlap shared frontend styles and browser verification, while the only delegated role is the explicitly required independent reviewer.
- Fallback: pause a dependent lane on an authority/safety blocker and continue unrelated verified lanes.
- User confirmation required: no.
