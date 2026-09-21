# Phase 19 — Factual Case Timing & Aging plan

## Goal

Expose factual, backend-authored case and automation timing from retained UTC timestamps
without adding an SLA, threshold, risk judgement, timer, scheduler, persistence write, or
workflow action. Preserve the Phase 18 paged query and the legacy array endpoint.

## Architecture

- Reuse `domain/case_management.py` as the deterministic timing-projection owner and
  `CaseQueryService` as the paged response observation-clock owner.
- Generate one UTC `observed_at` per paged response, then project every returned row from
  that same instant. The browser formats returned milliseconds only.
- Add the same bounded timing projection to the existing case-detail response from one
  response-time observation; do not expose raw start/completion timestamps merely so the
  browser can calculate.
- Memory reads source the retained automation record directly. Mongo extends its existing
  one-operation page projection only with `started_at` and `metrics.total_duration_ms`.
  No schema version, collection, index, migration, repair, or write changes.

## Tech stack

Python 3.12 / FastAPI / Pydantic / PyMongo 4.15; React 18 / TypeScript 5.9 /
TanStack Query 5 / Vitest / Playwright 1.56; disposable loopback MongoDB 7.

## Baseline and authority refs

- Worktree `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`;
  branch `phase/19-factual-case-timing`; `BASE_SHA` and task-start `origin/main`
  `b69fee6f475bfa32160a6d4acb9784edf3f4ff69`.
- `AGENTS.md`, `docs/PROJECT_STATE.md`, `docs/ARCHITECTURE.md`,
  `docs/DEVELOPMENT_WORKFLOW.md`, `docs/contracts/CASE_PORTFOLIO_QUERY_PROFILE.md`,
  decisions/open questions, current owners/tests, and accepted Phase 18 implementation/QG.
- Change classes: `BACKEND_DOMAIN`, `BACKEND_API`, `PERSISTENCE` (read-only projection),
  `FRONTEND_UI`, and `DOCS_ONLY`.

## Compatibility boundary

- Keep `GET /api/clm/zero-touch/cases` as the same array shape.
- Add only top-level `observed_at` and per-row `timing` to
  `GET /api/clm/zero-touch/case-portfolio`; do not change request, scope, search, filter,
  ordering, offset/lookahead, failure, cache-key, deletion, or session semantics.
- Detail adds a bounded `timing` object to its existing response. Providers, schema v4,
  RBAC, workflow, target ledger, mappings, configuration, and business policy are unchanged.

## Approved formulas and null semantics

- `case_elapsed_ms = (completed_at or observed_at) - created_at`.
- `time_since_last_update_ms = observed_at - updated_at`.
- `automation_elapsed_ms = null` when `started_at` is absent; otherwise
  `(completed_at or observed_at) - started_at`.
- `recorded_total_duration_ms` is the retained `metrics.total_duration_ms` scalar, never a
  recomputation. A completed case's computed elapsed is stable at `completed_at`.
- All inputs must be timezone-aware UTC and every emitted duration a non-negative integer
  millisecond value. Naive/non-UTC, future observation-relative input, reversed completion,
  or malformed retained scalar fails closed. Unknown `started_at` remains `null`.
- Current-stage/status age is omitted: retained events do not provide one unambiguous entry
  instant for every current state without inference.

## Stage-duration meaning

`metrics.stage_durations_ms` stores the orchestrator's recorded wall-clock delta around a
successfully completed automated processing attempt. It is not complete stage residence,
human waiting, SLA, vendor latency, compliance handling, or time across retries. UI wording:
"Recorded automated-stage processing duration".

## TDD Route

- Mode: off.
- Decision: skipped.
- Strict authority: not applicable.
- Test posture: minimum implementation plus deterministic post-change regression and
  explicit adverse-case tests; no wall-clock sleeps.
- Verification: focused backend/frontend, then all required broad, physical, browser,
  regression, governance, security, and hygiene checks.

## Requirement readiness and necessity

- Requirement source: the complete Phase 19 user brief; P19-01 through P19-22 are explicit.
- Decision: ready; no sponsor decision is needed for observational timing.
- Code necessity: existing DTOs do not expose the factual projection and the case-detail
  response omits start/completion facts, so docs-only or browser-only work cannot satisfy
  backend clock ownership. Minimum boundary is the existing domain/query/API/read-model and
  view owners.
- Existence check: reuse the existing portfolio/query and detail owners; add one small
  deterministic helper and one frontend formatting owner, with no duplicate timing engine.
- ADR: not triggered; no canonical owner, dependency direction, persistence strategy, or
  compatibility surface is replaced.

## Files and milestones

1. **A — contract/helper:** add strict source/timing projection models and the deterministic
   formula helper in `domain/case_management.py`; add focused chronology/UTC/boundary tests.
2. **B — memory/service:** source `started_at` and recorded total in the memory repository;
   have `CaseQueryService` call its clock exactly once and enrich the page.
3. **C — Mongo:** extend the existing strict projection, validation, and decoder with the two
   bounded scalars while retaining one aggregation and v1-v4 compatibility.
4. **D — API:** add the paged `observed_at`/row timing DTO and a bounded case-detail timing
   DTO using the same helper; map inconsistent portfolio timing to the existing sanitized
   `CASE_PORTFOLIO_UNAVAILABLE` path. Keep the legacy list DTO unchanged.
5. **E — Cases UI:** extend shared types/view model and render neutral Case age/Case duration,
   Last updated, and "Timing observed at" copy without polling or browser-clock authority.
6. **F — detail UI:** add Operational timing with computed case/automation facts, retained
   total duration, and truthful recorded automated-stage processing labels.
7. **G — evidence:** add focused tests, a Phase 19 physical Mongo suite/allowlist/runner entry,
   and proportional guarded browser assertions for active/completed/detail/refresh/paging/
   narrow-screen/no-egress behavior.
8. **H — self-review/docs:** inspect all P19 criteria and adverse paths; update the timing
   contract, architecture, Phase 18 accepted/Phase 19 candidate project state, demo notes if
   needed, and implementation report; remediate only reproduced in-scope defects.

Likely source/test paths are the existing owners named above plus `api_models.py`, `main.py`,
`types.ts`, `viewModels.ts`, `shared.ts`, `pages/CaseQueue.tsx`,
`pages/CaseDetail.tsx`/`CaseStatePanels.tsx`, focused Phase 19 tests, the physical runner and
safety helper, and `authenticated-zero-touch.e2e.ts`. No dependency or lockfile change.

## Verification

- Focused backend: Phase 19 timing plus Phase 18 portfolio, attention queue, Phase 17
  activity, route/security, and Mongo-structure tests.
- Backend broad: full `pytest`, Ruff, strict mypy, contracts/security/regression suites.
- Frontend: focused Phase 19/Phase 18/cache/navigation tests, full Vitest, typecheck, build.
- Guarded browser: repository runner with Phase 19 assertions; no unexpected egress.
- Physical Mongo 7: canonical guarded runner with every registered suite collected and
  `PASSED == COLLECTED`, zero failures/errors/skips, exact generated `clm_p19_*` cleanup.
- POC/lifecycle/governance: regression catalogue checks, Windows lifecycle when required,
  project-state/architecture/tooling/secret checks, pre-PR-checker tests, whitespace and
  task-owned-file hygiene. `pre_pr_check.py` itself is expected to remain blocked until a
  separately authorized publisher creates a clean committed tree.

## Risks, stop conditions, and retirement

- Stop for ambiguous retained time semantics, a required schema/version/migration, weakened
  scope-first validation, an N+1/read-write path, unsafe Mongo target, or unavailable
  mandatory physical/browser evidence.
- Reject browser `Date.now()`, background polling, negative/clamped results, inferred
  timestamps, current-state age, persisted ages, SLA/severity language, and silent fallback.
- Rollback is removal of the additive projections/UI/docs and restoration of the prior
  bounded source projection; no persisted data needs rollback.
- Freeze exact candidate paths plus content/diff hashes before the independent reviewer.

## Execution readiness

- Intent lock: factual observation only.
- Scope fence: milestones A–H; independent QG/publication are separate roles.
- Baseline lock: accepted Phase 18 main `b69fee6f...`.
- Evidence lock: current uncommitted diff/hash identity, not a future commit SHA.
- Drift rule: any owner/schema/policy/provider expansion returns to planning; two failed
  repairs of one mechanism trigger escalation.
- Execution route: inline single writer in the assigned worktree; no subagents and no Git
  mutations, staging, commit, push, PR, merge, or Phase 20 work.
