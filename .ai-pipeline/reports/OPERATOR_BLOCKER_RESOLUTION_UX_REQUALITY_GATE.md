# Operator Blocker Resolution UX Re-Quality Gate

## 1. Executive Result

**FAIL**

The remediation closes the findings from the historical quality gate, and all fresh
automated checks pass, but this independently reviewed candidate still has two material
truth defects:

1. after a failed GoldTier Search and successful independent evidence processing, the
   backend projects the evaluated Readiness stage as `NOT_REACHED` rather than
   `BLOCKED`; and
2. the canonical architecture diagram still routes a failed Search both onward to ACRA
   and directly to Review, contradicting the candidate decision and executable flow.

The candidate is not accepted and is not ready for publication. The two findings below
must be remediated and the changed content must receive another fresh independent gate.

Reviewed identity:

- Branch: `feat/operator-blocker-resolution-ux`
- Base SHA: `3e517d3660de2fd64b1d491a59954cc24321144f`
- HEAD: `3e517d3660de2fd64b1d491a59954cc24321144f`
- `origin/main`: `3e517d3660de2fd64b1d491a59954cc24321144f`
- Frozen tracked binary-diff SHA-256:
  `dc4110fede10f2c37ed93a6ecb44dbd9ba6b97a4`
- Combined reviewed-content SHA-256:
  `d5b658a80bc7fc8cfc6ca83f176571a2f4b9ea9a6c4ce804a6f54be794f174c1`
- Combined-hash method: UTF-8 SHA-256 of a newline-delimited manifest beginning with
  `tracked-diff<TAB><frozen hash>`, followed by sorted
  `<repository path><TAB><file SHA-256>` entries for the 23 tracked diff paths and the
  11 task-owned untracked plan/work paths listed in section 9.

The previous
`.ai-pipeline/reports/OPERATOR_BLOCKER_RESOLUTION_UX_QUALITY_GATE.md` was used only as
historical evidence and was excluded from candidate identity.

## 2. Phase Acceptance Checklist

| Requirement | Result | Direct evidence |
|---|---|---|
| A. Director case deletion is consistent across case-owning surfaces | PASS | Retained onboarding exposes Start new, Delete case, and Open full case; onboarded client detail routes to authoritative Case Detail controls; the existing delete dialog, endpoint, and cache lifecycle remain the owners. Focused frontend and E2E deletion coverage passed. |
| B. Director team ownership is explicit and safely reset | PASS | Team selection starts blank, requires explicit Alpha/Beta choice, sends the selected team exactly, and resets on actor change, start-new, deletion, and successful completion. Backend remains authoritative. Focused component, E2E, and RBAC tests passed. |
| C. Search failure remains technical and distinct from no-match | PASS | The failed provider result retains a safe Search failure; it does not become `NO_MATCH`, does not enter the new-customer target route, and does not become business Review. Exact match, no-match, ambiguous, and failure branches remain distinct in source and tests. |
| D. Independent case evidence continues after Search failure | PASS | ACRA, document, reconciliation, and ownership stages execute after the read-only Search failure. Fresh adverse-path reproduction and backend tests confirm the progression. |
| E. Pipeline status truth is preserved | **FAIL** | After evidence completes and readiness is evaluated with the retained Search blocker, `project_processing_pipeline` reports Readiness as `NOT_REACHED` while also reporting `1 blocker(s) retained`. The stage was evaluated and is blocked, not unattempted. See `RQG-OBR-01`. |
| F. No-match remains a distinct successful continuation | PASS | `200 + []` continues as `NO_MATCH`; the new-customer route remains available only for that outcome, and the UI displays separate safe no-match wording. |
| G. Safe diagnosis is available without leaking provider detail | PASS | Search failure categories normalize to safe allowlisted codes/messages, including invalid request, timeout, unavailable/configuration, malformed response, and fallback. Raw exception/provider response details are not projected. |
| H. Problem-only pipeline controls target actual owner panels | PASS | Actionable problem nodes use typed `node_id` mappings and focus actual diagnostic/resolution panels; tiles do not duplicate mutations. Unknown and non-actionable nodes remain non-interactive. |
| I. Navigation is keyboard accessible and respects reduced motion | PASS | Native buttons supply Enter/Space behavior, focus moves to the target, targets meet the 44px minimum, focus styling is visible, and reduced-motion uses instant scrolling. Focused component tests cover these paths. |
| J. Resolution actions remain unified under existing owners | PASS | `HumanInterventionPanel`, evidence panels, target classification, and Case Detail remain the action/diagnostic owners. Pipeline controls only navigate and focus. |
| K. Current-stage selection preserves backend node order and intent | PASS | The UI chooses the earliest actionable/in-progress node in backend order and preserves the intended node through Case Detail navigation. Focused unit and E2E coverage passed. |
| L. Target writes remain blocked and no replay path is introduced | PASS | The failed-Search adverse path makes only the Search target call. Shell, Policy, Amend, target binding, manual target-ID entry, and Search retry remain absent. The ledger remains the mutation/replay owner. |
| Durable decision and architecture documentation match executable truth | **FAIL** | Decision and policy prose record continuation after technical Search failure, but the canonical architecture diagram also routes `Ambiguous or failed` Search directly to Review. See `RQG-OBR-02`. |

## 3. Contract and Integration Findings

### RQG-OBR-02 — High — Canonical Search-routing diagram contradicts the active decision

`docs/ARCHITECTURE.md` shows both `GS -->|Technical failure| E` and
`GS -->|Ambiguous or failed| R`. A technical failure therefore has two incompatible
outgoing consequences in the canonical diagram: continue to Registry and stop at
Review. The candidate decision, policy prose, implementation, and tests instead define
one bounded rule: ambiguity stops for business review; technical Search failure remains
technical, permits independent evidence to continue, and later blocks target-identity
readiness and target writes.

This is a material current-contract error, not historical debt. It violates Task 4's
requirement that architecture documentation not contradict source/tests and can mislead
future maintainers into restoring the retired whole-case stop.

Required correction: make the direct Review edge ambiguity-only (and retain the
separate technical-failure continuation edge), then re-run documentation/governance
checks and a fresh independent gate.

No other contract or integration defect was found. In particular:

- untrusted provider DTO -> canonical evidence -> target mapping remains intact;
- Search, Shell, Policy, and Amend continue through controlled ports;
- the target ledger remains the sole mutation/replay owner;
- no external provider call, endpoint, authentication method, TLS behavior, mapping,
  related-party hierarchy, or `childId` behavior was added;
- unsupported/live modes remain fail-closed and no non-Live mode is presented as Live;
- contradictory GoldTier examples remain quarantined; fresh example validation reported
  `VALID=19`, `INVALID_QUARANTINED=19`, and `NOT_VALIDATED=48`.

Current local behavior is reviewable without resolving later sponsor dependencies.
Production GoldTier interoperability, safe late exact-match Search retry, related-party
hierarchy, autonomous approval, and Live provider claims remain explicitly later or
unresolved work and were not implemented.

## 4. Tester and Adversarial Findings

### RQG-OBR-01 — High — Evaluated Readiness is falsely projected as `NOT_REACHED`

A fresh in-process adverse-path reproduction used the existing test provider helper and
`project_processing_pipeline` after an initial Search technical failure followed by
successful ACRA, document, reconciliation, and ownership evidence. The projection was:

- GoldTier Search: `FAILED`, safe code `SEARCH_SERVICE_UNAVAILABLE`;
- ACRA: `COMPLETE`;
- Document: `COMPLETE`;
- Reconciliation: `COMPLETE`;
- Ownership: `COMPLETE`;
- Readiness: `NOT_REACHED`, with safe result `1 blocker(s) retained` and retained code
  `GOLDTIER_SEARCH_FAILED`;
- GoldTier target: `BLOCKED`.

The Readiness result is internally contradictory: its blocker evaluation and summary
exist, but its status says it was never reached. The cause is
`apps/backend/app/api_models.py` deriving the Readiness node solely from
`stage_status(READINESS)`, while the technical-failure helper restores the aggregate
current stage to `GOLDTIER_SEARCH` and does not add Readiness to completed stages. The
focused failed-Search regression currently asserts progression and target call stopping
but does not assert the complete projected pipeline status vector.

Required correction: project evaluated readiness with a retained blocker as `BLOCKED`
(not `FAILED` or `NOT_REACHED`) while preserving the Search node as `FAILED`, evidence
nodes as `COMPLETE`, and target as `BLOCKED`. Add a regression asserting the exact full
pipeline status vector for this adverse path.

### Fresh command evidence

| Check | Result |
|---|---|
| `python -m pytest -q -p no:cacheprovider tests/test_zero_touch_orchestration.py tests/test_clm_orchestration.py tests/test_goldtier_xpi_sandbox.py tests/test_phase13_auth_rbac.py tests/test_phase14_case_management_performance.py` from `apps/backend` | PASS — 312/312 tests passed. |
| `python -m pytest -q -p no:cacheprovider` from `apps/backend` | PASS — 1,433 passed, 36 skipped (1,469 collected). Existing Pydantic serializer warnings occurred only in adversarial malformed/trailing-LF/timestamp cases. |
| `python -m ruff check app tests` from `apps/backend` | PASS. |
| `python -m mypy app` from `apps/backend` | PASS — 108 source files. |
| Focused Vitest run for `Phase13AuthPriority.test.tsx`, `UiV2Integration.test.tsx`, and `CaseStatePanels.test.tsx` plus their selected dependencies | PASS — 5 files, 130 tests. The first sandbox launch failed with Windows `spawn EPERM`; the same command was rerun with the required execution permission and passed. Existing SSR `useLayoutEffect` warnings remain non-failing. |
| `npm test -- --run` from `apps/frontend` | PASS — 25 files, 318 tests. Existing SSR and React `act` warnings remain non-failing. |
| `npm exec -- tsc -p tsconfig.app.json --pretty false` and `npm exec -- tsc -p tsconfig.node.json --pretty false` | PASS. |
| Vite production build with output redirected to an isolated temporary directory | PASS — 118 modules transformed. No candidate or tracked build artefact was written. |
| Guarded Playwright selection for Director team/reset/delete and problem-pipeline focus | PASS — 2/2 tests. |
| Full guarded isolated Playwright suite on owned local Mock ports | PASS — 18/18 tests. |
| `python scripts/check_architecture.py` | PASS. The checker does not detect the semantic contradiction in the diagram described above. |
| `python scripts/check_project_state.py` | PASS. |
| `python scripts/check_external_provider_readiness.py` | PASS. |
| `python scripts/check_policy_authority.py` | PASS. |
| `python scripts/check_secrets.py` | PASS. |
| GoldTier example validation | PASS — expected classification totals `19 / 19 / 48`. |
| `git diff --check` plus explicit whitespace checks for all task-owned untracked Markdown | PASS. |

Failure injection and terminal-state review covered exact, no-match, ambiguous, Search
400, timeout/5xx/unavailable, malformed response, evidence continuation, target call
stopping, Director Alpha/Beta ownership, reset boundaries, deletion, focus transfer,
keyboard activation, reduced motion, and non-actionable nodes. No false target success,
target replay, duplicate intervention action, raw provider detail, or manual bypass was
observed.

Physical Mongo was not run because no durable schema, repository, CAS, index, driver, or
persistence-mode bytes changed. No external provider smoke test was run: this gate was
explicitly local/Mock, credentials were out of scope, and the candidate does not claim
Live verification. `.env` was not accessed.

## 5. Code and Architecture Review

The candidate stays within existing owners: onboarding owns initial Search and registry
acquisition; CLM owns target-identity readiness; zero-touch owns stage progression; the
API projection owns browser-visible pipeline truth; backend authorization remains
authoritative; the target ledger remains the sole mutation/replay owner; React Query
owns cache invalidation; and existing intervention/evidence panels own actions. No
second authorization, provider-routing, persistence, cache, action, or target-mutation
owner was introduced.

The Director lifecycle, safe error normalization, typed node-to-focus mapping, and
query-param intent preservation are narrow changes with focused regression coverage.
Unknown/non-actionable pipeline nodes fail closed. Onboarded detail links to the
authoritative Case Detail surface instead of duplicating controls.

The two material architecture/code findings are `RQG-OBR-01` and `RQG-OBR-02`. Apart
from those, no current blocker was found in scope, coupling, maintainability, or
dependency direction. Existing large service/App hotspots and existing non-failing test
warnings are accepted technical debt, not release blockers for this bounded task.

## 6. Security Review

No new security finding was identified.

- Backend role/capability/team scope remains authoritative; frontend affordances do not
  grant authority.
- Director Alpha/Beta selection is enforced by backend create semantics; non-Director
  ownership remains backend-derived and non-overridable.
- Deletion reuses the existing authorized DELETE route, safe inaccessible-case `404`,
  in-lock authorization, local-aggregate-only semantics, and scoped cache cleanup.
- Target writes remain blocked when Search identity is unresolved, and the adverse path
  performs no Shell, Policy, Amend, binding, or retry call.
- Provider exceptions and raw payload details are normalized to safe categories before
  projection.
- No credential, token, authorization header, private key, confidential provider
  artefact, KYC/PII body, raw provider payload, or private exception detail was accessed
  or added by this review.
- No external provider or physical Mongo connection was made.

Production hardening and Live interoperability evidence remain deferred and are not
claimed by this local proof-of-concept candidate.

## 7. Required Fixes

1. **Fix Readiness projection truth.** When readiness has actually been evaluated and
   retains the Search blocker, project Readiness as `BLOCKED`, not `NOT_REACHED`. Add a
   focused regression that asserts Search `FAILED`, independent evidence `COMPLETE`,
   Readiness `BLOCKED`, target `BLOCKED`, no business Review transition, and Search-only
   target calls.
2. **Fix the canonical architecture diagram.** Change the Search-to-Review edge from
   `Ambiguous or failed` to ambiguity-only wording so technical failure has exactly the
   D-060 continuation path. Re-run governance checks and inspect the rendered routing
   semantics.

The existing hotspot sizes, SSR/`act` warnings, and unexecuted Live provider smoke tests
are not fixes required for this bounded candidate. Safe Search retry, related-party
hierarchy, and production provider readiness remain later sponsor/integration work and
must not be folded into this remediation.

## 8. Readiness

- Bounded local task acceptance: **NOT ACCEPTED — FAIL**.
- Publication/PR readiness: **NOT READY**. This intentionally uncommitted candidate was
  not eligible for `pre_pr_check.py`, which requires the clean committed publication
  state; publication also requires a fresh exact independent `PASS` over unchanged
  remediated content.
- Next-phase readiness: **NOT AUTHORIZED** by this report.
- Live ACRA verification: **NOT PERFORMED and NOT CLAIMED**.
- Real GoldTier integration readiness: **NOT READY and NOT CLAIMED**. Local Mock and
  quarantined example evidence do not establish sponsor approval or interoperability.

## 9. Git Status

At review freeze:

- Branch: `feat/operator-blocker-resolution-ux`.
- HEAD/base/`origin/main`:
  `3e517d3660de2fd64b1d491a59954cc24321144f`.
- Staged paths: none.
- Tracked candidate diff: 23 paths, with binary-diff SHA-256
  `dc4110fede10f2c37ed93a6ecb44dbd9ba6b97a4`:
  - `.agents/skills/poc-regression-check/references/regression-catalogue.md`
  - `apps/backend/app/api_models.py`
  - `apps/backend/app/services/clm_orchestration.py`
  - `apps/backend/app/services/onboarding.py`
  - `apps/backend/app/services/zero_touch_orchestration.py`
  - `apps/backend/tests/test_clm_orchestration.py`
  - `apps/backend/tests/test_phase13_auth_rbac.py`
  - `apps/backend/tests/test_zero_touch_orchestration.py`
  - `apps/frontend/e2e/authenticated-zero-touch.e2e.ts`
  - `apps/frontend/src/App.tsx`
  - `apps/frontend/src/Phase13AuthPriority.test.tsx`
  - `apps/frontend/src/UiV2Integration.test.tsx`
  - `apps/frontend/src/pages/CaseDetail.tsx`
  - `apps/frontend/src/pages/CaseStatePanels.test.tsx`
  - `apps/frontend/src/pages/CaseStatePanels.tsx`
  - `apps/frontend/src/pages/ClientDetail.tsx`
  - `apps/frontend/src/pages/HomeOnboarding.tsx`
  - `apps/frontend/src/styles.css`
  - `docs/ARCHITECTURE.md`
  - `docs/aegis/INDEX.md`
  - `docs/contracts/ZERO_TOUCH_AUTOMATION_POLICY.md`
  - `docs/decisions/ADR-006_GOLDTIER_FIRST_PROVIDER_VERIFIED_RECOVERY.md`
  - `docs/decisions/DECISION_LOG.md`
- Task-owned untracked candidate records: 11 paths:
  - `docs/aegis/plans/2026-09-28-operator-blocker-resolution-ux.md`
  - `docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/10-intent.md`
  - `docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/20-checkpoint.md`
  - `docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/90-evidence.md`
  - `docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/99-reflection.md`
  - `docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/baseline-read-set-hint.json`
  - `docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/baseline-usage-draft.json`
  - `docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/drift-check-draft.json`
  - `docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/impact-statement-draft.json`
  - `docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/task-intent-draft.json`
  - `docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/todo-checkpoint-draft.json`
- `apps/backend/tests/test_goldtier_xpi_sandbox.py` appears modified in porcelain status
  because of the checkout's line-ending/stat state, but `git diff --quiet --` for that
  path succeeds and it is not part of the content diff or reviewed-content manifest.
- Historical report excluded from candidate:
  `.ai-pipeline/reports/OPERATOR_BLOCKER_RESOLUTION_UX_QUALITY_GATE.md`.
- This re-quality-gate report is the only file created by the reviewer:
  `.ai-pipeline/reports/OPERATOR_BLOCKER_RESOLUTION_UX_REQUALITY_GATE.md`.

The reviewer made no implementation, test, documentation, plan/work-record, or prior
report change; performed no commit, push, PR creation, merge, rebase, stash, reset, or
next-phase work; and made no external provider or physical Mongo call.
