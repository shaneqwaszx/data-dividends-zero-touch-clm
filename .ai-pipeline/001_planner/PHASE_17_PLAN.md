# Phase 17 — Case Activity & Audit Explorer plan

## Scope lock and source identity

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`.
- Branch: `phase/17-case-activity-audit-explorer`.
- `BASE_SHA`, current source baseline, and verified `origin/main` at task start:
  `1657a88a43e2fa8606e4f3d26f3bd05d16313d9e`.
- Assigned authority: `PHASE_17_CASE_ACTIVITY_SINGLE_SESSION_PROMPT.md`.
- Change classes: `BACKEND_DOMAIN`, `BACKEND_API`, `AUTH_RBAC_SECURITY`,
  `PERSISTENCE`, `FRONTEND_UI`, `FRONTEND_STATE_CACHE`, `DOCS_ONLY`, and bounded
  `CI_TOOLING` for the existing physical-suite inventory only.
- Current source, tested revisions, frozen reviewer content, and future main/PR identity
  will remain distinct in the implementation and quality-gate reports.

## Product boundary

Replace the Audit Trail list-plus-N-detail fan-out with one authorized, paged read of
retained `ZeroTouchAutomationRecord.events`. Preserve `/audit`, `/audit/:caseId`, native
case links, current action buckets, backend role/team authority, and existing mutation
owners. Add exact stage/outcome/UTC filters, bounded offset paging, explicit refresh,
current priority/client-scope context, and honest live-view/retention/actor wording.

This is not a production audit ledger. It does not add actor attribution, event
production, event persistence, schema v5, an index, a migration, totals, export,
background polling, provider calls, workflow advancement, target replay, retention,
immutability, compliance, approval, or a transactionally frozen cross-page snapshot.

## Architecture review

**ARCHITECTURE REVIEW: PROCEED**

- Invariant: authorized HTTP/UI reads depend on query services and repository ports;
  Mongo remains an adapter; retained automation events remain owned by the existing
  zero-touch aggregate.
- Existence check: `CaseQueryService`, `CasePortfolioRepository`,
  `InMemoryCasePortfolioRepository`, `MongoCasePortfolioRepository`, and
  `MongoCaseStore` already own authorized portfolio reads and can cohesively expose an
  activity method. No new canonical owner or dependency reversal is required.
- Dependency direction remains route -> `CaseQueryService` -> portfolio repository ->
  memory/Mongo adapter. React Query remains the browser server-state owner.
- Entropy: one additive repository/service method, one route, one minimized DTO family,
  and one frontend query family. The retired Audit Trail fan-out and obsolete actor/loop
  view placeholders are removed with no fallback.
- Persistence: read-only strict v1-v4 projection; no schema/index/write/read-repair
  change. Physical Mongo remains required because the aggregation/validation path is
  driver/server-specific.
- ADR: not required; all responsibilities fit existing owners and no durable boundary
  changes.

## Backend contract and strategy

- Domain/query types stay in `domain/case_management.py`: exact presentation action,
  server-authored scope, strict activity record/item/page, UTC and source-identity
  validation, action matching, and the canonical sort key `(timestamp desc, case UUID
  asc, sequence desc)`.
- `CaseQueryService` validates UTC/window/paging, resolves existing Director
  `team_filter` semantics, performs selected-case safe-404 authorization before the
  repository read, resolves team labels in one bounded team-list read, and returns
  current metadata explicitly labelled as current.
- Repository inputs contain only typed server-owned filters. Memory scopes cases before
  validating/inspecting events, validates every scoped event sequence/identity/time,
  filters before paging, and records scan counts in tests/reporting.
- Mongo first matches server-authored team/case scope, projects only envelope identity,
  schema/revision, current team/priority, and automation case/events, then uses one
  bounded aggregation with a fail-closed validation facet and a `limit + 1` row facet.
  Canonical stored UTC strings are normalized to fixed six-digit fractional precision
  for instant comparisons/sort without millisecond conversion or rounding. Malformed
  scoped projected data returns a sanitized failure; malformed other-team data is never
  inspected for a team-scoped request. `maxTimeMS` supplies a finite execution budget.
- `GET /api/clm/zero-touch/activity` is registered as `CASE_PORTFOLIO`. FastAPI owns
  enum/UUID/basic numeric parsing; the service owns timezone/window validation. Invalid
  queries return safe 422, inaccessible/absent/deleted selected cases return the
  existing safe 404, and persistence corruption/unavailability returns sanitized 503.
- API response contains only `items`, `offset`, `limit`, `has_more`; item fields are
  case ID, sequence, timestamp, event type, status, stage, outcome, code, bounded safe
  message, current priority, and current client-scope label.

## Frontend/cache strategy

- Add typed `fetchCaseActivity` with omission for All/absent filters and preserved
  `AbortSignal`.
- Add user-scoped activity query keys including case/team/action/stage/outcome/from/to/
  offset/limit. No previous-key placeholder bridge is used; a new key cannot display a
  prior key as current. Same-key refresh may show its own stale data and is labelled.
- Existing case summary/supporting/priority mutation effects invalidate the user's
  activity family. Deletion first cancels all of that user's activity requests and then
  removes all-cases pages plus exact selected-case pages so late responses cannot
  republish deleted rows. Logout, 401, and session replacement continue to clear the
  sole QueryClient.
- `AuditTrail.tsx` uses one activity-page request, resets offset when filters change,
  supports explicit refresh/previous/next, disables Next at the offset cap with
  narrowing guidance, and keeps detail expansion local/request-free. It removes By and
  Loop, retains disabled export, native case links, clear-case navigation, escaped React
  text, accessible labels/states, UTC/live-view notices, and 480px internal scrolling.
- Retire `AuditEntryView`/`mapCaseTimelineToAuditEntries` only after the consumer/test
  scan proves no remaining owner.

## Expected owned files

Runtime owners:

- `apps/backend/app/domain/case_management.py`
- `apps/backend/app/services/case_query.py`
- `apps/backend/app/services/case_portfolio_repository.py`
- `apps/backend/app/persistence/repositories.py`
- `apps/backend/app/persistence/mongo_case_store.py`
- `apps/backend/app/api_models.py`
- `apps/backend/app/main.py`
- `apps/backend/app/services/authorization.py`
- `apps/frontend/src/api.ts`
- `apps/frontend/src/types.ts`
- `apps/frontend/src/caseQueries.ts`
- `apps/frontend/src/viewModels.ts` only for retirement of the old mapping
- `apps/frontend/src/pages/AuditTrail.tsx`
- narrowly relevant `apps/frontend/src/styles.css`

Evidence and directly affected tests:

- new focused backend and frontend Phase 17 suites
- existing route/RBAC, performance/projection, cache/deletion, navigation, and fixture
  suites where contract additions require updates
- `apps/frontend/e2e/authenticated-zero-touch.e2e.ts`
- one new owned physical Phase 17 Mongo suite if the existing Phase 14 suite cannot
  remain cohesive, plus only `scripts/run_physical_mongo_tests.py` and its runner test
- `.ai-pipeline/reports/PHASE_17_IMPLEMENTATION.md`
- `.ai-pipeline/reports/PHASE_17_QUALITY_GATE.md` (independent reviewer only)
- `docs/contracts/CASE_ACTIVITY_QUERY_PROFILE.md`
- `docs/demo/PHASE_17_ACTIVITY_DEMO.md`
- narrow accepted-state updates to `docs/PROJECT_STATE.md` and `docs/ARCHITECTURE.md`

No dependency manifests, CI workflow, provider/configuration, envelope schema, or
unlisted broad refactor is planned.

## Acceptance and adverse evidence map

- A17-01/03/04/05: strict domain/service tests for source preservation, overlapping
  action buckets, filter intersection, UTC inclusivity/exclusivity, precision ties,
  empty/one/full/lookahead/end/offset cap, and identical memory/Mongo ordering.
- A17-02/06: API/RBAC and persistence tests for team/Director/HR, selected safe 404,
  v1-v4, malformed scoped metadata/events, corrupt-other-team isolation, naive/unknown
  data, and sanitized unavailable responses.
- A17-07: deterministic old `1 + N` versus new one-page HTTP measurement for 1/25/100
  cases; Mongo spy/physical evidence for one aggregation, bounded `limit + 1`, minimized
  projection, and no full decode/detail fan-out.
- A17-08/12: spies plus existing POC regression prove zero provider/workflow/ownership/
  cache/target/persistence mutation and preserve Attention Queue, Workbench,
  review/recovery, no-replay, and navigation.
- A17-09: frontend key, abort, filter-race, same-user replacement, 401, mutation
  invalidation, delete-between-pages, and stale-response anti-resurrection tests.
- A17-10/11: guarded Chromium login/filter/paging/scoped/native-link/keyboard/480px
  checks plus exact limitation copy and hostile-message text rendering.
- A17-13: full affected checks, guarded physical Mongo with generated allowlisted DB
  and verified cleanup, guarded browser, POC regression, and Windows lifecycle.
- A17-14: tracked and task-owned-file hygiene, frozen manifest, fresh independent exact
  PASS, separate publication, clean-tree pre-PR, scoped commit/push/PR, and observed CI.

## Verification order

1. Focused backend domain/service/API/Mongo-pipeline tests after each backend slice.
2. Focused frontend transport/key/cache/component tests and request-count harness.
3. Ruff, mypy, full backend pytest, route/security/contract/governance checks.
4. Full frontend test, typecheck, build, dependency inventory, E2E list.
5. Guarded browser, relevant POC regression, physical Mongo, and unchanged Windows
   lifecycle, serialized with port/resource checks.
6. Diff/self-review against A17-01..14, task-owned Markdown hygiene, secret/scope scan.
7. Freeze manifest, fresh independent Sol High review, bounded remediation/re-QG until
   exact PASS or a documented stop condition.
8. Separate publisher verifies reviewed identity, stages exact paths, commits, fetches/
   integrates understood drift if any, reruns affected evidence, runs clean-tree
   `pre_pr_check.py`, pushes, opens one PR, and observes push and PR CI. Human merge only.

## Capability/resource preflight

- Available now: local PowerShell/Git/Python/Node/npm, worktree `apply_patch`, web/UI
  automation tools, collaboration reviewer invocation, and remote Git with approval.
  Filesystem writes are scoped to the project workspace; Git metadata/network actions
  may require explicit elevated approval.
- Python: worktree `.venv`, 3.12.10, correct interpreter path, `pip check` clean.
- Frontend: Node 22.23.2, npm 10.9.8, pinned dependency tree present, Playwright 1.56.1,
  Chromium executable present.
- Ports 8875, 4285, 8000, and 5173 were free at task start and will be rechecked before
  heavy runs. Browser, Mongo, and lifecycle runs are serialized.
- Docker CLI 29.8.0 is present; the Docker Desktop Linux daemon was not running at task
  start. Physical acceptance remains blocked until a task-owned loopback MongoDB 7
  container can be started and safely cleaned. No ambient URI, `.env`, Atlas, shared
  database, host mount, privileged mode, `clm_poc`, or Docker prune is authorized.

## Stop conditions

Stop dependent work for an unclear owner, new durable audit/retention requirement,
schema/index/migration need, authorization ambiguity, corrupt-data path that can only be
hidden, unsafe database/process ownership, unavailable required physical/browser/
lifecycle evidence, unexplained main drift/conflict, or two unsuccessful repairs of the
same design mechanism. Never weaken validation, add a fallback, fabricate totals/actor/
snapshot completeness, or claim project-defined retained events are production audit.
