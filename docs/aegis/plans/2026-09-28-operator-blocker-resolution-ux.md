# Operator Blocker Resolution UX Implementation Plan

## Goal

Deliver the bounded local behavior requested on `feat/operator-blocker-resolution-ux`:
consistent Director case deletion, explicit blank-by-default Director team ownership,
safe case-evidence continuation after a failed read-only GoldTier Search, truthful
backend pipeline status, and accessible stage-to-resolution navigation.

## Architecture

Reuse the existing owners. `OnboardingService` owns initial Search and registry
acquisition, `ClmOrchestrationService` owns target-identity readiness,
`ZeroTouchOrchestrator` owns stage progression, `project_processing_pipeline` owns
browser-visible pipeline truth, backend authorization remains authoritative, the target
ledger remains the only mutation/replay owner, React Query remains the deletion/cache
owner, and `HumanInterventionPanel` remains the mutation/action owner. No second action
engine, provider router, authorization model, cache owner, or target ledger is added.

## Tech Stack

Python 3.12 / FastAPI / Pydantic / pytest / Ruff / strict mypy; React 18 / TypeScript /
React Query / Vitest / Playwright / Vite.

## Baseline / Authority Refs

- User-supplied bounded task dated 2026-09-28.
- `AGENTS.md`, `docs/DEVELOPMENT_WORKFLOW.md`, `docs/PROJECT_STATE.md`, and
  `docs/ARCHITECTURE.md`.
- `docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md`,
  `docs/contracts/ZERO_TOUCH_AUTOMATION_POLICY.md`, and the current GoldTier contract
  baseline.
- `docs/decisions/ADR-005_INCREMENTAL_GOLDTIER_ORCHESTRATION.md` and
  `docs/decisions/ADR-006_GOLDTIER_FIRST_PROVIDER_VERIFIED_RECOVERY.md`.
- PR #61 accepted behavior at `3e517d3660de2fd64b1d491a59954cc24321144f` and its
  exact independent re-quality gate.

## Compatibility Boundary

- Preserve `200 + [] = NO_MATCH`; only NO_MATCH permits the new-customer target path.
- A technical Search failure never becomes NO_MATCH and never permits Shell, Policy,
  Amend, target binding, or manual target-ID entry.
- No external provider request is made by implementation or verification.
- Do not retry the historical Amend and do not invent related-party `childId` behavior.
- Keep the existing DELETE endpoint, `DeleteCaseDialog`, safe inaccessible-case `404`,
  in-lock authorization, and local-aggregate-only deletion semantics.
- Keep non-Director creation team ownership backend-derived and non-overridable.
- Keep pipeline tiles navigation-only; backend-authorized panels own actions.

## TDD Route

- Mode: off
- Decision: skipped
- Strict authority: not applicable
- Strict signals: behavior, authorization, cache, provider semantics, and cross-module
  regression risk are present, but configured Aegis TDD mode is explicitly off.
- Light eligibility: not applicable.
- TDD-fit exception: none.
- Test posture: diagnostic reproduction plus focused post-change regression.
- Reason: repository and user require comprehensive tests, but do not require strict
  RED/GREEN sequencing.
- Verification: focused backend/frontend tests first, then every affected broad suite
  and checker from the assigned task.

## Aegis Visibility

Planning is required because one product clarification changes an accepted workflow
decision (Search failure no longer invalidates independent case evidence) while target
identity and replay safety must remain fail-closed.

## Baseline Usage Draft

- Required baseline refs: the refs listed above plus current owning source/tests.
- Delivered context refs: the user task attachment.
- Acknowledged before plan refs: all required Tier 0/Tier 1 refs and the PR #61 re-gate.
- Cited in plan refs: all sources listed under Baseline / Authority Refs.
- Missing refs: none for the local behavior; production/live and related-party authority
  remain explicitly out of scope.
- Decision: continue.

## Requirement Ready Check

- Requirement source refs: user-supplied workstreams A-L and test/verification matrix.
- Goals and scope refs: same task plus current project architecture/contracts.
- User/scenario refs: Director/RM/Client Onboarder/HR, Search exact/no-match/failure,
  and operator pipeline interaction scenarios are explicit.
- Requirement item refs: delete, team selection, evidence continuation, status truth,
  diagnosis, clickable blocks, unified resolution, current-stage ownership, and retained
  case actions are enumerated.
- Acceptance/verification criteria refs: the supplied test matrix and command list.
- Open blocker questions: no local blocker; read-only Search retry is excluded unless a
  safe late exact-match transition can be proved without weakening prior-verified target
  identity or contradicting already-retained ACRA evidence.
- Decision: ready.

## Change Necessity

- User-visible need: the current UI can retain a Director team across actor/new-case
  transitions, retained onboarding lacks delete control, Search failure terminalizes
  the whole case, downstream status can be misleading, and live pipeline tiles are
  passive.
- No-change / non-code option: documentation cannot reset React state, invalidate a
  deleted retained case, continue evidence execution, correct projection truth, or add
  accessible navigation.
- Why code change is necessary: each symptom is generated by current executable owner
  behavior.
- Minimum change boundary: existing onboarding/CLM/zero-touch/projection owners and the
  existing App/page/cache/panel owners with focused tests.
- Decision: code-change.

## Root-Cause and Patch-Shape Readback

- Topology: independent compound. The Director-state defect, Search terminalization,
  projection/current-node selection, and passive tile rendering are separate active
  mechanisms with distinct owners and manifestations.
- Director selector recurrence generator: `directorTeamId` is initialized blank but is
  omitted from actor-change and start-new-case resets; submit-time validation does not
  disable the create affordance.
- GoldTier recurrence generator: initial Search failure calls the terminal case path;
  CLM maps the blocker to whole-record failure; zero-touch maps it to terminal technical
  failure and later treats unresolved identity as readiness inconsistency.
- Current-stage recurrence generator: the frontend searches status classes globally
  before respecting backend workflow order.
- Interaction recurrence generator: pipeline nodes are rendered as passive list items
  with no typed node-to-panel navigation contract.
- PatchShape: fix canonical owners and typed consumers; do not add label parsing,
  caller-side target fallback, or duplicate action handlers.
- CanonicalOwner: onboarding/CLM/zero-touch/API projection for workflow truth; App and
  React Query effects for client lifecycle; CaseStatePanels for presentation/navigation.
- UpwardDrillSignal: closed at the explicit user clarification, which supersedes only
  the failed-Search stop in ADR-006 while retaining all target-identity/no-replay rules.
- Decision: fix owner.
- Falsifier: if the selected owners were not causal, resetting the state owners and
  changing backend progression/projection would not eliminate the reproduced stale
  selection, terminal case, false stage, and passive tile behavior. Source traces show
  no alternate team default or frontend stage reconstruction owner.
- Layer ceiling: the user clarification is the L7 behavior authority for this bounded
  change; sponsor-controlled mutation, production, related-party, and approval behavior
  remains outside it.

## Existence Check and Architecture Integrity Lens

- Proposed new surface: typed stage-to-focus mapping and a read-only blocker explanation
  where no authorized action exists.
- Existing owner / reuse candidate: `OnboardingProgressPanel`, existing evidence panel
  IDs/focus helper, `HumanInterventionPanel`, `DeleteCaseDialog`, and React Query effects.
- Why existing surface is sufficient: these owners already render backend nodes, own
  evidence navigation/actions, deletion, and cache lifecycle.
- Creation proof: only a small typed mapping/helper or focused presentational component
  may be extracted if it reduces hotspot growth; no new business owner is needed.
- Entropy / retirement impact: no fallback or compatibility branch is introduced;
  passive list-item-only rendering is retired for actionable nodes.
- Decision: reuse-existing.
- Architecture verdict: PROCEED within existing owners. An ADR amendment/superseding
  decision is required because the failed-Search workflow consequence changes; no
  provider contract, target mutation order, persistence owner, or dependency direction
  changes.

## Complexity Budget

- Artifact class: source and maintained tests.
- Target files/artifacts: `onboarding.py` (~146 KB), `zero_touch_orchestration.py`
  (~107 KB), `api_models.py` (~69 KB), `App.tsx`, and large integration tests.
- Current pressure: strong hotspot/size pressure in the core services and App.
- Projected post-change pressure: at risk.
- Budget result: at-risk.
- Planned governance: keep owner edits narrow; extract only cohesive typed UI mapping or
  case-action helpers where that makes the hotspot smaller; avoid unrelated refactors.

## Plan-Time Complexity Check

- Target files: existing service/projection owners and frontend page/cache owners.
- Existing size/shape signals: several files exceed 800/1200-line pressure thresholds.
- Owner fit: the changed rules already belong to these owners.
- Add-in-place risk: mixed concerns and regression ripple.
- Better file boundary: a focused frontend stage-navigation mapping/component is allowed;
  backend business decisions stay in their canonical services.
- Recommendation: local-fix-without-new-responsibility plus focused UI extraction only
  if needed.

## Plan Pressure Test

- Owner / contract / retirement: owners are known; ADR-006 failed-Search stopping is
  superseded narrowly; old terminalization is retired.
- Architecture integrity / higher-level path: backend projection remains the source of
  stage truth and the target ledger remains the only target mutation owner.
- Verification scope: specified backend/frontend/E2E/contracts/security/governance
  checks cover the ripple.
- Task executability: all required local runtimes and frontend dependencies are present;
  no external provider or protected credential is required.
- Pressure result: proceed.

## Execution Readiness View

- Intent Lock: implement only workstreams A-L and the supplied test matrix.
- Scope Fence: no external calls, Amend retry, childId/hierarchy, manual GoldTier ID,
  approval policy, Live claim, commit, push, PR, or merge.
- Baseline Lock: branch/base/HEAD/origin-main are `3e517d3`; working tree was clean before
  Aegis plan/work records.
- Approved Behavior: Director explicit team and delete; failure != no-match; independent
  evidence may continue; target mutation stays blocked; pipeline state and navigation are
  backend-typed and accessible.
- Owner / Contract Constraints: existing service/port/ledger/cache/action owners only.
- Compatibility Boundary: preserve exact-match/no-match behavior, safe 404, no replay,
  session/team cache scope, and PR #61 intervention ownership.
- Retirement Boundary: retire stale Director selection, whole-case Search-failure
  terminalization, false downstream failure projection, global status-priority current
  selection, and passive actionable tiles.
- Task Batches: backend semantics/projection; Director/cache/delete UI; typed accessible
  stage navigation; docs; full verification; independent QG/remediation/re-QG.
- Test Obligations: every user-specified focused and broad check; physical Mongo only if
  durable schema/repository/CAS/index/driver bytes change.
- Review Gates: implementation self-review, integration-security review, POC regression,
  fresh independent QG; exact PASS required before stopping for publication authority.
- Drift / Rewind Rules: stop dependent work for contract ambiguity, new persistence
  schema, unsafe late exact-match retry, target replay risk, or new owner need.
- Evidence Required Before Completion: exact commands/results, final diff/path set,
  no-secret receipt, provider-call receipt, and independent exact PASS.
- Advisory Boundary: method-pack execution guidance only; not GateDecision,
  PolicySnapshot, or completion authority.

## Task 1 — Correct GoldTier Search failure semantics and evidence continuation

Files:

- Modify `apps/backend/app/services/onboarding.py`.
- Modify `apps/backend/app/services/clm_orchestration.py`.
- Modify `apps/backend/app/services/zero_touch_orchestration.py`.
- Modify `apps/backend/app/api_models.py` only for truthful safe projection.
- Modify focused tests in `apps/backend/tests/test_onboarding_resilience.py`,
  `test_clm_orchestration.py`, and `test_zero_touch_orchestration.py`.

Why: a failed read-only target identity check currently terminalizes independent case
evidence and later risks false stage ownership.

Change Necessity: code must distinguish target-identity readiness from case-evidence
validity inside the current owners; documentation or frontend-only changes cannot make
ACRA/documents/reconciliation/ownership execute safely.

Impact / Compatibility: preserve exact/no-match/ambiguous branches and all target call
stopping. Normalize only safe failure categories; expose no raw response or exception.
Do not implement Search retry unless late exact-match provenance and already-retained
registry evidence can be reconciled without a new unresolved contract.

Steps:

1. Add focused diagnostic assertions for 400, 5xx/timeout/malformed, no-match, exact,
   ambiguous, ACRA attempted/not-attempted truth, evidence continuation, and zero target
   mutation after unresolved Search.
2. Replace the initial Search-failure terminal path with safe failed Search evidence plus
   continued eligible ACRA acquisition.
3. Keep CLM target identity failed/blocked while allowing document and ownership
   readiness to be evaluated independently.
4. Let zero-touch route through document/reconciliation/ownership after the failed
   Search, then stop at the Search-owned target-identity blocker before readiness/target
   mutation.
5. Project only attempted stages as FAILED; leave unattempted downstream stages
   NOT_REACHED/BLOCKED and render NO_MATCH as successful new-customer continuation.

Verification:

`python -m pytest apps/backend/tests/test_onboarding_resilience.py apps/backend/tests/test_clm_orchestration.py apps/backend/tests/test_zero_touch_orchestration.py -q -o "addopts=-p no:cacheprovider"`

Repair Track: fix the terminalization/projection recurrence at the service owners.
Retirement Track: remove the old failed-Search whole-case terminal behavior; retain no
fallback and no retry path whose late exact-match semantics are unproved.

## Task 2 — Correct Director team selection and current-case deletion lifecycle

Files:

- Modify `apps/frontend/src/App.tsx` and
  `apps/frontend/src/pages/HomeOnboarding.tsx`.
- Modify `apps/frontend/src/pages/ClientDetail.tsx` only if the existing onboarded detail
  is a case-owning surface with the same safe deletion lifecycle.
- Reuse `apps/frontend/src/pages/DeleteCaseDialog.tsx` and
  `apps/frontend/src/caseQueries.ts`; modify them only if a proven lifecycle gap exists.
- Modify focused frontend/backend RBAC tests and E2E coverage.

Why: Director creation must be visibly explicit, while every sensible case-owning
surface must expose the already-authorized local case deletion flow without stale state.

Change Necessity: local state reset/button availability/current-route cleanup are
executable UI/cache behavior.

Impact / Compatibility: frontend rendering reflects roles/capabilities but never grants
authority. Non-Director requests omit team selection. Delete cancels/removes exact and
derived queries before the deleted case can reappear, clears retained local identity,
and navigates to a safe route.

Steps:

1. Reset `directorTeamId` on actor identity change and Start-new-case.
2. Present `Owning team *` with blank `Select team`, prominently echo the selected team,
   and disable create/demo creation until a Director explicitly selects an option.
3. Assert the create request contains exactly the selected team and no default/first
   option behavior; preserve backend-derived team for non-Directors.
4. Add retained-current-case actions for Start new, Delete case when rendered for the
   existing authorized roles, and Open full case detail/review.
5. Reuse `DeleteCaseDialog`, DELETE API, and `caseDeletedEffect`; invalidate the active
   operation generation, clear retained/live local state and selected case identity, and
   navigate to `/onboarding/new` after success.
6. Add/reuse the same deletion lifecycle on onboarded detail only if that page owns the
   case aggregate rather than a detached client projection.

Verification:

`npm test -- --run apps/frontend/src/Phase13AuthPriority.test.tsx apps/frontend/src/Phase15CNavigation.test.tsx apps/frontend/src/UiV2Integration.test.tsx`

and focused backend RBAC tests proving explicit Alpha/Beta persistence and no override.

Repair Track: reset the actual state owner and reuse the cache deletion owner.
Retirement Track: remove implicit retained selection across actor/new-case boundaries;
retain no duplicated delete authorization model.

## Task 3 — Add typed, accessible stage-to-resolution navigation

Files:

- Modify or extract a focused helper/component from
  `apps/frontend/src/pages/CaseStatePanels.tsx`.
- Modify `apps/frontend/src/pages/CaseDetail.tsx`,
  `HomeOnboarding.tsx`, `HumanInterventionPanel.tsx`, and
  `TargetClassificationPanel.tsx` only to expose stable focus targets and authoritative
  owner panels.
- Modify `apps/frontend/src/styles.css` and focused component/E2E tests.

Why: actionable backend stages are currently passive and the displayed current stage
can be owned by a later status instead of the earliest workflow blocker.

Change Necessity: semantic button behavior, keyboard/focus movement, reduced motion,
and typed node mapping require code and styles.

Impact / Compatibility: tiles navigate/focus only. Backend-authored actions remain in
their current panel. Unknown/non-actionable nodes remain non-interactive. Missing
resolution surfaces receive a read-only explanation, never an invented bypass.

Steps:

1. Change current-node selection to the earliest actionable/in-progress node in backend
   order.
2. Define an exhaustive stable `node_id` to focus-target mapping for Search, ACRA,
   documents, reconciliation, ownership, classification, target, and approval.
3. Render actionable nodes as full-tile buttons with >=44px target, visible hover/focus,
   descriptive aria labels, native Enter/Space behavior, and no nested controls.
4. Focus then scroll the target; use instant scrolling when reduced motion is preferred.
5. Focus `HumanInterventionPanel` or its stage-owned card where backend actions exist;
   otherwise focus the specific evidence/owner panel or a read-only blocker explanation
   that states why blocked, what can be done, and what cannot be bypassed.
6. Cover exact node mapping, keyboard use, focus transfer, reduced-motion behavior,
   non-actionable tiles, and absence of duplicated intervention actions.

Verification:

`npm test -- --run apps/frontend/src/pages/CaseStatePanels.test.tsx apps/frontend/src/Phase15CNavigation.test.tsx`

plus the relevant guarded Playwright selection.

Repair Track: fix ordered selection and passive rendering at the shared panel owner.
Retirement Track: retire status-priority selection and passive actionable list items;
retain complete/skipped stages as non-actionable unless useful read-only navigation is
explicitly mapped.

## Task 4 — Record the changed workflow decision and verify the complete candidate

Files:

- Add a focused ADR that supersedes only ADR-006's failed-Search-before-ACRA stop.
- Update `docs/decisions/DECISION_LOG.md` and `docs/ARCHITECTURE.md` for candidate truth.
- Update current contract prose only where it directly states the superseded stop.
- Maintain the current Aegis work evidence/checkpoint; do not change PROJECT_STATE as
  accepted-main truth before acceptance/merge unless the repository checker requires a
  clearly labelled candidate statement.

Why: the task changes a durable workflow consequence and must not leave architecture
documents contradicting source/tests.

Change Necessity: durable decision/projection documentation must match the reviewed
candidate, while accepted-main state remains truthful.

Verification:

1. Focused backend and frontend tests from Tasks 1-3.
2. `python -m pytest apps/backend/tests -q -o "addopts=-p no:cacheprovider"`.
3. `python -m ruff check apps/backend/app apps/backend/tests`.
4. `python -m mypy apps/backend/app` from `apps/backend` configuration context.
5. `npm test`, `npm run typecheck`, and `npm run build` in `apps/frontend`.
6. Relevant `python scripts/run_e2e.py` selection, or the full guarded suite when the
   harness lacks a reliable focused selector.
7. Contract tests, POC regression catalogue, `check_architecture.py`,
   `check_project_state.py`, `check_external_provider_readiness.py`,
   `check_policy_authority.py`, `check_secrets.py`, and `git diff --check` plus explicit
   whitespace checks for task-owned untracked Markdown.
8. Physical Mongo only if implementation changes durable schema/repository/CAS/index/
   driver behavior.
9. Fresh independent `fyp-quality-gate` against the exact frozen content. Remediate
   every task-scoped finding and request a fresh re-gate until exact PASS.

## Risks

- Treating a routed/settled Search stage as internally complete could inflate metrics or
  hide its failed outcome; projection and metric tests must distinguish routing progress
  from provider success.
- A late Search retry can create an unproved transition between retained ACRA evidence
  and exact-existing target state; omit retry unless that transition is fully proved.
- Large hotspot edits can create unrelated regressions; keep deltas narrow and inspect
  the complete diff.
- Home onboarding has fewer evidence panels than Case Detail; its tile navigation must
  focus a truthful local explanation/owner or route to full detail without fabricating
  an action.

## Retirement

- Retire stale Director team selection across actor/new-case transitions.
- Retire whole-case terminalization for a non-mutation Search failure.
- Retire false downstream FAILED propagation and global status-priority current-node
  selection.
- Retire passive actionable pipeline tiles.
- Retain the target ledger, historical mutation records, Amend no-replay, safe 404,
  backend authorization, and PR #61's single intervention action owner unchanged.

## Execution Route

- Decision: inline.
- Evidence: one implementation writer is required, core files overlap, and shared
  checkout/cache/provider owners make parallel writers unsafe. The user requested an
  independent agent only for the final Quality Gate.
- Fallback: pause at the current checkpoint if a new persistence/contract boundary is
  discovered, then revise this plan before editing.
- User confirmation required: no.
