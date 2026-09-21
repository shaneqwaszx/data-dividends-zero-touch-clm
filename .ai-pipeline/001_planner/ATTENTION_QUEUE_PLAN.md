# Blocker-aware Attention Queue — implementation plan

## Scope and evidence identity

- Approved increment: add a read-only blocker-aware filter and presentation to the
  existing Cases queue. This is not Phase 17 and does not authorize assignment, risk,
  SLA, approval, retention, source-precedence, provider, or workflow policy.
- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`
- Branch: `feature/blocker-aware-attention-queue`
- `BASE_SHA` and task-start `HEAD`: `c45ff77c7ff3472eb8867798c4c73d8692ca248b`
- Verified task-start `origin/main`: `c45ff77c7ff3472eb8867798c4c73d8692ca248b`
- Documented behavioral baseline remains
  `99dd8eeea1c79bb4b9a9a592e6b47b4c038fdd4c`; it is not the candidate identity.
- Task-start tracked tree and index are clean. The execution brief and this plan are
  task-owned new files. No Git operation is active and no remote branch collision was
  found.

## Classification and architecture/privacy checkpoint

Applicable change classes are `BACKEND_DOMAIN`, `BACKEND_API`,
`AUTH_RBAC_SECURITY`, `PERSISTENCE`, `FRONTEND_UI`, `FRONTEND_STATE_CACHE`, and
supporting `DOCS_ONLY`. No external-provider, dependency, schema-version, index,
migration, canonical-owner, framework, or dependency-direction change is required.

Existing owners are sufficient:

- `CasePortfolioRecord` owns the bounded server projection.
- `InMemoryCasePortfolioRepository` and `MongoCaseStore.list_portfolio` own memory and
  Mongo projection parity.
- `CaseQueryService` remains the authorized filtering and ordering owner.
- The existing list route/API model owns the public transport shape.
- Existing authenticated React Query case-list keys and `CaseQueue` presentation state
  own browser request identity and UI state.

The new surface exposes only existing exact `BusinessExceptionType` values derived
from current `OPEN` business exceptions. It does not expose blocker codes,
explanations, evidence, notes, reviewer identity, assignment data, or arbitrary filter
expressions. Mongo may additionally project only
`automation.exceptions.exception_type` beside the already projected exception
`status`. No ADR is triggered.

## Frozen API and projection contract

1. Every list row adds `active_exception_types`, a bounded JSON array/tuple of unique
   existing `BusinessExceptionType` values in enum declaration order.
2. Only exceptions whose own status is `OPEN` contribute. `RESOLVED` and `CANCELLED`
   history does not contribute. Status and type are validated as a correlated pair.
3. `active_exception_count` remains the actual number of open exception records, not
   the number of unique types. No open business exception yields `[]` and does not
   imply health, approval, completion, or absence of a technical/recovery problem.
4. Existing `GET /api/clm/zero-touch/cases` accepts optional exact enum query parameter
   `attention_type`. Omission means no attention filter. Invalid values retain FastAPI
   422 behavior. There is no backend `ALL` value, alias, fuzzy match, expression, new
   endpoint, facet, or global count.
5. `CaseQueryService` obtains the already authorized/team-scoped projection before
   applying `attention_type`. It intersects with existing status, priority, team, and
   unassigned filters. Existing priority ordering and tie ordering do not change.
6. Mongo performs one bounded projected `find`; it performs no full-envelope decode,
   row-detail read, pushdown attention predicate, new index, write, provider/cache
   lookup, workflow progression, readiness evaluation, or target call.
7. Missing, unknown, malformed, or extra projected exception status/type data fails
   closed. Supported schema-v1 through current envelopes remain readable without
   rewriting, migration, or schema-version change.
8. The frontend adds an exact `BusinessExceptionType` union sourced from the existing
   backend vocabulary, a complete typed display-label map, and one optional attention
   argument appended after the existing positional `AbortSignal` argument so current
   callers do not shift.
9. Case-list keys retain the existing user/status/priority/sort/team prefix and include
   attention type. Requests omit `attention_type` for All. Existing mutation,
   priority, and delete effects continue targeting the case-list prefix, therefore all
   variants remain invalidated/cancelled/removed.
10. `CaseQueuePresentationState` remains the only queue presentation owner and adds a
    backward-compatible `attentionType` value/default. No URL state, second store,
    second QueryClient, App ownership change, or client-side authorization is added.
11. UI wording is `Open business exception type`, `All types (no type filter)`, and
    `Open business exceptions`. A known empty list renders
    `No open business exceptions recorded`. Existing status/count/team/client scope,
    priority, delete, and native Open navigation remain.
12. The unsupported `Assigned to` column and `CaseRowView.assigned_to` placeholder are
    removed after tracked-consumer verification. Unrelated HomeOnboarding assignment
    demo controls and real team scope are untouched.

## Disjoint implementation ownership

The coordinator is the only Git owner and owns this plan, cross-lane integration,
guarded browser work after worker freeze, documentation/reports, scheduling, final
verification, independent QG dispatch, and publication coordination.

Backend worker write ownership:

- `apps/backend/app/domain/case_management.py`
- `apps/backend/app/services/case_portfolio_repository.py`
- `apps/backend/app/services/case_query.py`
- `apps/backend/app/persistence/mongo_case_store.py`
- `apps/backend/app/api_models.py`
- `apps/backend/app/main.py`
- focused backend tests, including
  `apps/backend/tests/test_phase14_case_management_performance.py`,
  `apps/backend/tests/test_phase14_real_mongo.py`, and a narrowly named new focused
  test module if useful

Frontend worker write ownership:

- `apps/frontend/src/types.ts`
- `apps/frontend/src/api.ts`
- `apps/frontend/src/caseQueries.ts`
- `apps/frontend/src/viewModels.ts`
- `apps/frontend/src/pages/CaseQueue.tsx`
- narrow queue styling in `apps/frontend/src/styles.css` if required
- focused frontend tests/fixtures for API, query identity/cancellation, view-model
  retirement, queue rendering, truthful states, and invalidation coverage

No worker may write the other lane, this plan, shared reports, E2E, docs, Git metadata,
dependencies, lockfiles, App/navigation/auth/query-client owners, persistence envelope
models, provider/cache/workflow/target owners, CI, lifecycle tooling, or governance
files. Writers stop before integrated, browser, lifecycle, physical Mongo, or other
heavy suites.

## Acceptance and adverse-test map

- AQ-01/AQ-02: memory projection tests cover duplicate OPEN types, enum ordering,
  resolved/cancelled exclusion, actual count, and valid empty lists.
- AQ-03/AQ-04: service/API tests cover omission, exact filtering, 422 invalid input,
  composition with status/priority/team/unassigned, stable ordering, and OPEN-A plus
  closed-B not matching B.
- AQ-05: tests prove authorization/team scope is established before attention
  selection and malformed inaccessible data cannot affect the caller.
- AQ-06/AQ-07/AQ-08: strict projected decoder tests cover schema-v1 through current,
  exact minimized projection, one find, corrupt/missing/unknown/extra fields, no
  full-envelope reads or writes/calls, and memory/Mongo parity.
- AQ-09/AQ-10/AQ-11: frontend tests cover exact URL omission/inclusion, stable
  positional AbortSignal, key identity, filter switching/loading/error/cached-refresh,
  user/team isolation, and prefix-wide review/priority/delete invalidation and
  cancellation.
- AQ-12/AQ-13: rendering tests preserve status semantics, use truthful empty wording,
  render chips without conflating count, retire assignment only from the queue/view
  model, and retain team/client scope and Open links.
- AQ-14: guarded Playwright creates two feasible real synthetic cases through existing
  non-fault public operations (document review/low-confidence path and ownership-cycle
  path), selects each exact filter, clears the filter, opens a case, checks keyboard and
  narrow-screen behavior, and retains the network guard. Filter-read traffic is
  measured separately from setup.
- AQ-15: extend the already owned Phase 14 physical Mongo suite and run all suites
  through `scripts/run_physical_mongo_tests.py` against only generated allowlisted
  disposable databases, followed by exact database/container cleanup proof.
- AQ-16: focused checks precede full backend pytest, Ruff, mypy, contracts/security/
  governance, full frontend tests/typecheck/build, POC regression, lifecycle, guarded
  browser, whitespace, conflict-marker, and secret checks required by current repo
  tooling.
- AQ-17: freeze exact candidate identity, obtain a fresh independent Sol High exact
  `PASS`, then use a separate publisher for scoped staging, commit, latest-main
  assessment/integration if safe, clean-tree pre-PR, normal push, one PR, and distinct
  push/pull_request CI observation. Human merge only.

## Capability/resource preflight

- Worktree-local Python 3.12.10 resolves `app.config` to this worktree; `pip check`
  reports no broken requirements.
- Node 22.23.2, npm 10.9.8, the locked frontend dependency tree, Playwright 1.56.1,
  and its Chromium executable are present.
- PowerShell 7.6.5 and Windows CMD are available.
- Docker client/server 29.8.0 and local `mongo:7` are available through the approved
  daemon path. No ambient URI or `.env` is used.
- Ports 8873, 4283, 8000, and 5173 were free at preflight. Browser, lifecycle, and
  physical Mongo workloads remain serialized.
- PR #44 is merged at the accepted base and the last normal `main` push CI run
  completed successfully at that SHA. Current source tests prove two distinct open
  business-exception scenarios are reachable without a fault endpoint.

## Stop and review conditions

Stop dependent work if current source disproves the frozen contract, an existing owner
cannot hold the behavior, authorized filtering cannot precede attention selection,
strict legacy projection parity cannot be preserved, browser scenarios require demo
faults/fake success, or required physical/browser evidence is unavailable. Two failed
repair attempts for one underlying defect trigger design escalation. Independent review
must be read-only except for its report; any source/test/doc change after review requires
an applicable independent recheck.
