# Phase 17 — Case Activity & Audit Explorer implementation record

## Identity and status

- Task: complete the bounded Phase 17 retained automation-event explorer.
- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`.
- Branch: `phase/17-case-activity-audit-explorer`.
- `BASE_SHA`, task-start HEAD, and verified task-start `origin/main`:
  `1657a88a43e2fa8606e4f3d26f3bd05d16313d9e`.
- Current source revision: the same committed base plus the task-owned working-tree
  candidate listed below. No implementation commit exists yet.
- Tested content: current working-tree candidate after the initial-query StrictMode fix,
  selected-case authorization tests, UTC/microsecond display remediation, docs,
  physical-suite registration, and E2E updates.
- Independent review identity: fresh `gpt-5.6-sol` High reviewer. Its first frozen-candidate
  review found one High UTC-display defect and the already-recorded physical Mongo
  blocker; the display defect is remediated and re-review is pending.
- Publication: not started. No commit, push, PR, merge, or auto-merge has occurred.
- Current status: **implementation candidate; physical Mongo acceptance blocked by local
  Docker Desktop startup failure; not ready for independent PASS/publication**.

Phase 17 is project-defined POC scope. It remains pending merge and is not sponsor
approval of production audit, retention, actor attribution, compliance, immutability,
exactly-once behavior, or Ready-for-Approval.

## Implemented behavior

### Backend and persistence

- Added typed activity query/action/record/item/page contracts to the existing case
  management domain. UTC windows are explicit, normalized to UTC, from-inclusive and
  to-exclusive. Paging is limited to `1..100` rows and offset `0..10000`.
- Added one `GET /api/clm/zero-touch/activity` route under existing `CASE_PORTFOLIO`
  authorization. It supports selected-case, Director team, action, stage, outcome, UTC
  window, limit, and offset filters. Invalid inputs return safe 422; inaccessible,
  absent, or deleted selected cases return the same safe 404; persistence failures are
  sanitized 503.
- Preserved existing action-bucket overlap and source event values. Global ordering is
  timestamp descending, canonical case UUID ascending, source-local sequence descending.
- Extended the existing query service/portfolio port and memory/Mongo adapters. No new
  event store, canonical owner, persisted ID, schema v5, index, migration, read repair,
  fallback, provider call, workflow action, or target operation was added.
- Memory performs one automation-record listing and one case lookup per candidate record,
  applies visibility before event inspection, validates every scoped sequence/identity,
  then filters/orders/pages. Its cost is linear in candidate records plus scoped retained
  events; a bounded response does not make the scan constant-time.
- Mongo performs one case-collection aggregation per activity page. It first matches the
  server-authored visibility/selected-case scope, projects only required identity/schema/
  revision/current metadata/event fields, validates scoped v1–v4 candidate/event shapes,
  filters/sorts/pages in the database, transfers at most `limit + 1` rows plus one bounded
  invalid signal, disables disk use, and applies a 5000 ms execution budget. Canonical UTC
  strings are normalized to six fractional digits for microsecond-preserving comparison;
  no millisecond conversion is used.
- Current team labels are resolved by one bounded team-list read. Priority and client
  scope are labelled as current metadata, not event-time facts.

### Frontend and cache

- Replaced the Audit Trail case-list plus every-case-detail fan-out with one React Query
  activity-page request. Deterministic harness measurements are `2/26/101` legacy HTTP
  requests for `1/25/100` cases versus one new page request in every case.
- Query identity includes user, case, team, action, stage, outcome, UTC window, offset,
  and limit. Requests preserve `AbortSignal` and do not bridge previous-key data.
- Relevant case/supporting/priority mutations invalidate activity. Deletion cancels and
  removes the entire user's activity family before a late response can republish a row.
  Existing logout, 401, and session-replacement ownership continues to clear the single
  session QueryClient.
- Initial activity enablement occurs after the mount lifecycle so React development
  StrictMode does not turn one normal in-app navigation into two aborted/restarted HTTP
  requests. Guarded Chromium observed exactly one initial uncached activity request and
  no case-detail fan-out after authenticated app bootstrap.
- `/audit` and `/audit/:caseId`, Clear case filter, and native case-detail links remain.
  Added exact filters, returned-page count, previous/next, offset-cap guidance, explicit
  page-one refresh, local request-free detail expansion, loading/empty/error/refresh
  states, disabled export, keyboard focus, and 480 px internal table scrolling.
- Activity timestamps use a Phase 17-specific canonical UTC ISO projection. The UI does
  not apply the shared Singapore-local formatter and preserves the source fractional
  precision, including all six microsecond digits.
- Removed obsolete By/Loop display and its unused mapping types. Copy states that actor
  attribution is not recorded, current metadata is not event-time state, only retained
  automation events are covered, deletion removes available history, and paging is live.

## Owned candidate paths

Runtime owners:

- `apps/backend/app/api_models.py`
- `apps/backend/app/domain/case_management.py`
- `apps/backend/app/main.py`
- `apps/backend/app/persistence/mongo_case_store.py`
- `apps/backend/app/persistence/repositories.py`
- `apps/backend/app/services/authorization.py`
- `apps/backend/app/services/case_portfolio_repository.py`
- `apps/backend/app/services/case_query.py`
- `apps/frontend/src/App.tsx`
- `apps/frontend/src/api.ts`
- `apps/frontend/src/caseQueries.ts`
- `apps/frontend/src/pages/AuditTrail.tsx`
- `apps/frontend/src/styles.css`
- `apps/frontend/src/types.ts`
- `apps/frontend/src/viewModels.ts`

Tests/tooling:

- `apps/backend/tests/test_phase17_case_activity.py`
- `apps/backend/tests/test_phase17_case_activity_real_mongo.py`
- `apps/backend/tests/test_attention_queue_backend.py`
- `apps/backend/tests/test_phase13_auth_rbac.py`
- `apps/backend/tests/test_phase13_mongo_test_safety.py`
- `apps/frontend/src/Phase17CaseActivity.test.tsx`
- `apps/frontend/src/Phase15CNavigation.test.tsx`
- `apps/frontend/src/UiV2Integration.test.tsx`
- `apps/frontend/e2e/authenticated-zero-touch.e2e.ts`
- `scripts/mongo_test_safety.py`
- `scripts/run_physical_mongo_tests.py`
- `tests/test_run_physical_mongo_tests.py`

Authorized plan/report/docs:

- `.ai-pipeline/001_planner/PHASE_17_CASE_ACTIVITY_SINGLE_SESSION_PROMPT.md`
- `.ai-pipeline/001_planner/PHASE_17_PLAN.md`
- `.ai-pipeline/reports/PHASE_17_IMPLEMENTATION.md`
- `docs/contracts/CASE_ACTIVITY_QUERY_PROFILE.md`
- `docs/demo/PHASE_17_ACTIVITY_DEMO.md`
- `docs/PROJECT_STATE.md`
- `docs/ARCHITECTURE.md`

## Acceptance evidence to date

Passed on the current candidate unless noted:

- Focused backend Phase 17/RBAC/Mongo-pipeline/runner checks: 10 direct Phase 17 tests;
  combined focused run passed 35 and skipped only the intentionally unconfigured real
  Mongo module.
- Full backend final rerun: 1071 passed, 24 expected environment-gated skips, 0 failed
  from 1095 collected tests in 78.93 seconds.
- Ruff: all backend, scripts, and tests passed.
- Mypy: 94 backend source files passed; focused eight changed owners also passed.
- Frontend focused before independent review: 43/43 passed. Post-remediation Phase 17
  focused rerun: 8/8 passed.
- Frontend full after UTC remediation: 246/246 passed.
- Frontend typecheck and production build passed; build transformed 113 modules.
- Playwright inventory: 5 tests. Guarded Chromium: 5/5 passed, including real login,
  single request/no fan-out, filters, 25-row paging, scoped route, case link, keyboard,
  480 px layout, and exact UTC microsecond rendering from the activity response.
- Contract tests: 44/44 passed. Phase 07 delivery assets: 4/4 passed.
- Governance owner tests: 39/39 passed. Pre-PR checker tests: 42/42 passed. Secret
  scanner tests: 8/8 passed.
- `check_project_state.py`, `check_architecture.py`, `check_tooling_config.py`, and
  `check_secrets.py`: PASS.
- Explicit accepted POC regression subset covering onboarding, document, ownership,
  CLM/zero-touch, provider conformance, reconciliation, and registry cache: passed.
  Catalogue expectations remained unchanged: straight-through Mock completion; review/
  technical failure separation; exact GoldTier prefixes and downstream stopping;
  jurisdiction/registry gating; current-evidence reconciliation; recovery/no replay;
  case isolation; truthful Mock/Local/Partial labels. No catalogue change was made.
- Windows lifecycle: 23/23 passed in 215.376 seconds; all owned processes stopped and
  ports 8000/5173/8875/4285 were clear afterward.
- Diff whitespace check passed for tracked changes. Every non-ignored task-owned new file
  passed final-newline, trailing-whitespace, and conflict-marker checks.

## Preserved failure history and remediation

1. Focused frontend initially found one stale Phase 15C expectation for the retired
   `/cases` request. It was corrected to the activity endpoint; the same test then passed.
2. The guarded browser first counted two development StrictMode activity requests. A
   normal in-app navigation still reproduced it because consuming the AbortSignal caused
   the development mount cycle to abort/restart the request. Initial query enablement was
   moved after the mount cycle; focused tests and guarded Chromium then passed with one
   uncached activity request.
3. Two pre-existing guarded-browser operations exceeded isolated 15-second navigation/
   reload assertions on separate runs after having passed earlier. Their assertions were
   aligned to the suite's existing 30-second browser bound without changing expected
   state. The complete suite then passed 5/5.
4. Sandbox-only `spawn EPERM` affected initial Vitest/Vite execution. The exact original
   checks passed outside the sandbox with bundled workers; assertions were not weakened.
5. Sandbox temporary-Git restrictions caused governance/pre-PR unit setup errors. The
   exact suites passed outside the sandbox (39/39 and 42/42); application behavior was
   unchanged.
6. Physical Mongo could not start. Docker Desktop 4.91.0 repeatedly crashed before
   exposing its engine because its own backend could not rename/access the exact
   `C:\Users\shane\AppData\Local\Docker\run\sailor-ingest.sock` reparse point. Bounded
   recovery stopped only task-started Docker processes, terminated only Docker's WSL
   distribution, attempted a recoverable move, then an exact socket removal, and finally
   shut down an already-idle WSL runtime. The socket remained inaccessible and the engine
   pipe remained absent. No Mongo image/container/database/volume was created; no URI was
   read or printed; `clm_poc` was never accessed; no prune/reset/reboot was performed.
   Task-started failed Docker processes and its WSL distribution were stopped after the
   attempts.
7. The first independent quality gate found that the activity column labelled UTC used
   the shared Singapore-local formatter and discarded microseconds. The activity view
   now renders canonical UTC ISO text without `Date` conversion; focused coverage fixes
   the source at `.123456Z`, and guarded Chromium compares a real six-digit response
   timestamp to the displayed text. Typecheck, 8 focused tests, 246 full frontend tests,
   production build, and guarded Chromium 5/5 passed after the repair.
8. The first post-repair guarded-browser run measured the activity scroller immediately
   after returning from a scoped route and observed a zero-layout transient. The existing
   assertion now waits for visible layout before measuring; the complete suite then
   passed 5/5 without weakening the width or overflow expectations.

## Schema, provider, security, and architecture declaration

- API/model/type: one additive activity GET contract and minimized DTO family; no existing
  response field was reinterpreted.
- Durable schema/index/migration: unchanged; case envelope remains v4, readable v1–v4.
- Repository semantics: one additive read-only activity method; no write/CAS/delete/startup
  behavior change.
- Connector/configuration/provider status: unchanged. ACRA remains Mock by default,
  generic sandbox-shaped support Partial, BizFile dormant, IDP Local/Mock, ownership
  Local, GoldTier Mock, Mongo optional and memory default.
- Business rules/mappings: no workflow, readiness, reconciliation, UBO, target, approval,
  retention, or source-precedence rule changed. Action buckets are presentation filters.
- Authorization/security: existing `CASE_PORTFOLIO` capability and team/safe-404 semantics
  apply on every request. No browser authority, raw payload, secret, arbitrary query,
  unsafe message sink, or actor attribution was added.
- Architecture: existing query-service/portfolio-repository/Mongo-store owners suffice;
  dependency direction is unchanged and no ADR is required.

## Blocker and next authorized action

Required physical Mongo evidence A17-04/A17-06/A17-07/A17-13 is not available on this
host. The new real-Mongo suite and explicit six-suite runner entry are implemented but
have not executed against MongoDB 7. Therefore the candidate must not be independently
accepted, committed, pushed, or published yet.

Next authorized action after the host's Docker socket is repaired (normally by the owner
or a machine restart) is: start one loopback-only `mongo:7` container with no host mount,
run `python scripts/run_physical_mongo_tests.py` with the URI only in that test process,
verify generated `clm_p17_<24 hex>` cleanup, remove the exact owned container/anonymous
volumes, rerun the final full backend/hygiene set, freeze the manifest, and invoke the
fresh independent Sol High quality gate. Publication remains conditional on exact PASS.
