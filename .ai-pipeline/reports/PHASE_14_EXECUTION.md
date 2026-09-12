# Phase 14 Case Management and Performance — Execution Report

Execution window: 2026-09-08 to 2026-09-12
Branch: `phase/14-case-management-performance`
Recorded `BASE_SHA`: `aba264af3b4088a9a10fe682ee6fc0cb418d550d`
Implementation HEAD: `aba264af3b4088a9a10fe682ee6fc0cb418d550d` (no commit was authorized)
Final fetched `origin/main`: `aba264af3b4088a9a10fe682ee6fc0cb418d550d`
Final merge base: `aba264af3b4088a9a10fe682ee6fc0cb418d550d`
Main drift: none; `HEAD..origin/main` was empty after the final fetch.

## Outcome

Slices 1–5 of the Phase 14 planner are implemented in the working tree. The change adds
one lightweight authorization-scoped portfolio read path, one projected Mongo query,
session-memory TanStack Query caching, bounded list rendering, and resurrection-safe
hard deletion for the two authorized POC roles.

The implementation is **not PR-ready**. P14-QG-001, P14-QG-002, and P14-QG-003 are closed.
P14-FRQG-001 is closed by the repaired physical verifier and its deterministic Mongo-free
structural guards. The physical Mongo suite was correctly skipped because the explicit URI
was not configured, so this run does not claim physical execution passed. The clean-tree
pre-PR check is not authorized, and the historical data-safety incident receipt below
remains open for owner review.

No stage, commit, amend, push, merge, rebase, reset, stash, clean, or branch switch was
performed.

## Implemented behavior

### Lightweight portfolio and query performance

- Added a strict `CasePortfolioRecord` and authorization-derived portfolio scope.
- Cases and Dashboard now consume one shared portfolio owner instead of list-plus-detail
  joins.
- Mongo performs one projected `find` with backend-authored team/status/priority filters,
  strict projection validation, deterministic Python ordering, and no documents,
  ownership graph, reconciliation, event history, submission snapshot, or target ledger.
- Added the bounded compound index `onboarding_team_lookup` for team-scoped portfolio
  queries. No index experiment was run against shared data.
- Added the list fields required to render Cases and Onboarded without detail requests:
  `resolved_jurisdiction`, `created_at`, `completed_at`, and
  `mock_goldtier_party_id`.

### Session-memory query cache

- Added exact-pinned `@tanstack/react-query@5.102.8` and development-only
  `jsdom@30.0.1`; npm generated the manifest/lock changes.
- One application-owned query client uses 45-second staleness and 15-minute garbage
  collection. It has no browser-persistence plugin or storage API.
- Query keys include the authenticated user ID. Logout, 401, successful login, and
  identity replacement cancel and clear all cached query/mutation state.
- GET query functions accept `AbortSignal`; mutation effects are centralized for create,
  priority, supporting evidence, workflow/resume, polling, and delete.
- After server `204`, deletion awaits cancellation of the authenticated user's list and
  Dashboard query families plus exact case resources before it mutates/removes caches.
  Cancelled stale responses cannot publish after the deletion effect completes.
- Cases and Onboarded issue one list request and zero row-detail requests. Detail
  resources load only after navigation and are cached/deduplicated.
- Queue filters live above detail navigation and survive the return path.

### Hard deletion

- Added `DELETE /api/clm/zero-touch/cases/{case_id}` with an empty `204` response.
- The existing access policy resolves visibility first. Inaccessible or absent cases are
  `404`; an accessible Onboarder case is `403 CASE_DELETE_FORBIDDEN`; Director and
  Relationship Manager may delete accessible cases in any workflow status.
- CSRF, trusted-origin, authenticated-session, duplicate-header, and fixed route-policy
  middleware remain authoritative. Request bodies, role/team headers, and query fields do
  not grant authority.
- The service holds the canonical per-case lifecycle lock, re-reads authorization inside
  the lock, then invokes one composed deletion port. No registry, IDP, ownership, or
  GoldTier connector is called.
- Zero-touch creation reserves its case identity before the first write and holds that
  same canonical reentrant lock through onboarding, initial CLM, automation, and
  applicable demo registration. Any escaped required-write failure performs bounded
  same-case aggregate rollback through repository boundaries before the lock is released.
- Memory deletion clears onboarding, automation, CLM, document, ownership,
  reconciliation, target-ledger, demo-scenario, provider-binding, and demo transient
  state.
- Mongo deletion removes the single complete envelope with a revision-aware predicate.
  Explicit insert-only `create` and update-only `save` semantics prevent stale saves from
  recreating a deleted envelope.
- Persistence conflicts map to `409 CASE_DELETE_CONFLICT`; unavailable persistence maps
  to `503 CASE_DELETE_UNAVAILABLE`. Neither error claims success.
- The accessible confirmation dialog contains retained identifiers and a permanent-action
  warning, initially focuses Cancel, traps Tab, supports Escape, restores trigger focus,
  prevents duplicate submission, and keeps bounded errors visible.

The deletion role policy and cache lifecycle are **PROJECT-DEFINED POC BEHAVIOR PENDING
SPONSOR CONFIRMATION.** External ACRA, IDP, ownership, and GoldTier systems are not
deleted or mutated by the delete operation.

## Deterministic performance evidence

| Area | Baseline | Phase 14 measured test result |
|---|---:|---:|
| Cases list HTTP | `1 + N` | `1` list, `0` details |
| Onboarded list HTTP | `1 + N` | `1` list, `0` details |
| Case list Mongo | `1 + N` full-envelope reads | `1` projection `find`, `0` per-case gets |
| Dashboard Mongo | `1 + N` full-envelope reads | `1` projection `find`, `0` per-case gets |
| Concurrent same-key frontend query | duplicate possible | `1` underlying request |
| Fresh repeated navigation | blocking refetch | cache hit, `0` additional request |
| Deleted-case cache | unavailable | detail/supporting/list/Dashboard data removed |

These are deterministic call/query assertions, not millisecond production SLOs.

## API, persistence, dependency, and security changes

- API inventory: 44 routes; `CASE_SCOPED` count is 32 after the additive DELETE route.
- API list type: four additive backend-authored fields; existing Phase 13 filter/order and
  Dashboard definitions are preserved.
- Persistence lifecycle: onboarding creation is insert-only; established mutation is
  update-only; physical deletion is revision-aware; no tombstone or dual fallback exists.
- Mongo schema: remains envelope schema v2; no migration. One additive team lookup index.
- Dependencies: exact TanStack Query runtime pin and exact jsdom development pin only.
- Security: backend role/access decisions remain authoritative; cache is session memory
  only; no credential, token, URI, provider payload, KYC/PII, or raw sponsor artefact was
  intentionally printed or added to source.
- Test isolation: the Windows lifecycle harness now forcibly selects memory mode, a
  loopback non-service Mongo URI, and `clm_ordinary_tests`, regardless of ambient config.

## Files changed

### New backend owners and tests

- `apps/backend/app/domain/case_management.py`
- `apps/backend/app/services/case_portfolio_repository.py`
- `apps/backend/app/services/case_deletion.py`
- `apps/backend/tests/test_phase14_case_management_performance.py`
- `apps/backend/tests/test_phase14_real_mongo.py`

### Modified backend and CI

- `.github/workflows/ci.yml`
- `apps/backend/app/api_models.py`
- `apps/backend/app/demo/zero_touch_control.py`
- `apps/backend/app/main.py`
- `apps/backend/app/persistence/composition.py`
- `apps/backend/app/persistence/mongo_case_store.py`
- `apps/backend/app/persistence/repositories.py`
- `apps/backend/app/services/authorization.py`
- `apps/backend/app/services/case_query.py`
- `apps/backend/app/services/clm_orchestration.py`
- `apps/backend/app/services/clm_repository.py`
- `apps/backend/app/services/dashboard.py`
- `apps/backend/app/services/document_repository.py`
- `apps/backend/app/services/onboarding.py`
- `apps/backend/app/services/ownership_repository.py`
- `apps/backend/app/services/reconciliation_repository.py`
- `apps/backend/app/services/repository.py`
- `apps/backend/app/services/target_execution_repository.py`
- `apps/backend/app/services/zero_touch_orchestration.py`
- `apps/backend/app/services/zero_touch_provider_bindings.py`
- `apps/backend/app/services/zero_touch_repository.py`
- `apps/backend/tests/test_phase13_auth_rbac.py`
- `apps/backend/tests/test_phase13_dashboard.py`
- `apps/backend/tests/test_phase13_mongo_test_safety.py`
- `apps/backend/tests/test_phase13_priority.py`
- `apps/backend/tests/test_pre_phase12_workspace_multidoc.py`
- `scripts/mongo_test_safety.py`
- `tests/test_demo_lifecycle_windows.py`

### New frontend owners and tests

- `apps/frontend/src/queryClient.tsx`
- `apps/frontend/src/caseQueries.ts`
- `apps/frontend/src/pages/DeleteCaseDialog.tsx`
- `apps/frontend/src/Phase14CaseManagementPerformance.test.tsx`

### Modified frontend

- `apps/frontend/package.json`
- `apps/frontend/package-lock.json`
- `apps/frontend/src/App.tsx`
- `apps/frontend/src/auth.tsx`
- `apps/frontend/src/api.ts`
- `apps/frontend/src/types.ts`
- `apps/frontend/src/viewModels.ts`
- `apps/frontend/src/design-system.css`
- `apps/frontend/src/pages/Dashboard.tsx`
- `apps/frontend/src/pages/CaseQueue.tsx`
- `apps/frontend/src/pages/OnboardedClients.tsx`
- `apps/frontend/src/pages/CaseDetail.tsx`
- `apps/frontend/src/pages/ClientDetail.tsx`
- `apps/frontend/src/App.test.tsx`
- `apps/frontend/src/Dashboard.test.tsx`
- `apps/frontend/src/Phase13AuthPriority.test.tsx`
- `apps/frontend/src/UiV2Integration.test.tsx`

### Documentation

- `docs/architecture/PHASE_14_CASE_MANAGEMENT_PERFORMANCE.md`
- `docs/architecture/README.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/decisions/DECISION_LOG.md` (`D-040`)
- `docs/integration/CONFIGURATION_REFERENCE.md`
- `.ai-pipeline/reports/PHASE_14_EXECUTION.md`

The supplied planner remains the protected untracked artefact
`.ai-pipeline/001_planner/PHASE_14_CASE_MANAGEMENT_PERFORMANCE.md` and was not modified.

## Verification receipt

### Backend

| Command / scope | Result |
|---|---|
| Planner focused Phase 14 + Phase 13 auth/priority/Dashboard command | `123 passed` |
| Planner focused persistence + Mongo-safety command | `26 passed` |
| `python -m pytest tests/test_phase14_case_management_performance.py -p no:cacheprovider` | `17 passed in 1.54s` after targeted rollback remediation |
| directly impacted CLM/zero-touch/provider tests | `244 passed, 3 existing adversarial Pydantic warnings in 17.18s` |
| canonical `python -m pytest` from `apps/backend` | `920 passed, 13 skipped, 3 existing adversarial Pydantic warnings in 83.44s` |
| `python -m ruff check .` | Recursive run encountered sandbox access-denied paths; task-owned Python path check subsequently passed |
| backend task-owned `python -m ruff check <explicit paths>` from `apps/backend` | passed |
| bounded `python -m ruff format --check <33 explicit task-owned Python paths>` | non-zero: 10 retained semantic baseline paths and 17 EOL-only paths; 6 paths clean |
| `python -m mypy app` | passed for 83 source files |
| `python -m pip check` | no broken requirements |
| closure `test_pre_phase12_workspace_multidoc.py` | `32 passed` |

The three full-suite warnings are existing adversarial Pydantic serializer warnings. No
formatter rewrite was applied because it would create broad unrelated formatting/EOL
churn across existing files. Bounded baseline comparison produced:

- `PHASE14_INTRODUCED_FORMATTER_DEFECTS=0`
- `FORMATTER_CURRENT_BASELINE_SEMANTIC_FINDINGS=10`
- `FORMATTER_EOL_ATTRIBUTED_PATHS=17`
- `FORMATTER_CLEAN_PATHS=6`
- `FORMATTER_BROAD_CHURN_AVOIDED=YES`

Six Phase 14-local formatting findings identified during attribution were corrected
without whole-file formatting. The final EOL-normalized comparison found no remaining
Phase 14-introduced formatting defect. This is not a repository-wide formatter PASS.

### Frontend

| Command | Result |
|---|---|
| `npm.cmd ls --all` | passed; optional platform packages reported as unmet only |
| `npm.cmd run typecheck` | passed |
| focused `Phase14CaseManagementPerformance.test.tsx` remediation run | `10 passed in 1.82s` |
| `npm.cmd test -- --run` | `126 passed` across 5 files in 1.54s |
| `npm.cmd run build` | passed after an escalated rerun of the sandbox-blocked child process; 94 modules transformed in 685ms |
| `npm.cmd ls @tanstack/react-query jsdom vite vitest nanoid` | passed; exact dependency ownership recorded |
| `npm.cmd audit --json` and `npm.cmd audit` (closure read-only rerun) | passed; `0` current vulnerabilities |

An earlier execution-pass audit reported `nanoid`, Vite, and Vitest findings. Those
findings are not reproducible against the current advisory response: both closure audit
runs returned zero vulnerabilities. The current tree places `nanoid@3.3.16` only beneath
Vite's PostCSS toolchain; TanStack Query and jsdom introduce no currently identified
advisory. No package or lockfile version changed during closure, and no audit fix or
unapproved dependency upgrade was run. Current attribution:

- `TANSTACK_NEW_ADVISORY=NO`
- `JSDOM_NEW_ADVISORY=NO`
- `PREEXISTING_TOOLCHAIN_ADVISORIES=NO` in the current audit response

### Repository root and security

| Command / check | Result |
|---|---|
| contract unittest discovery | `44 passed in 0.577s` |
| Phase 07 delivery-assets unittest discovery | `4 passed` |
| Windows demo lifecycle unittest discovery | `18 passed in 187.603s` under explicit memory isolation, including the hostile-ambient-configuration regression |
| `test_check_secrets.py` unittest discovery | `5 passed in 0.004s` |
| `test_pre_pr_check.py` unittest discovery | `37 passed in 39.122s` after an escalated sandbox-compatible rerun |
| `python scripts/validate_goldtier_examples.py --if-present` | passed: 19 canonical valid, 19 invalid/quarantined, 48 not validated |
| bounded task-owned credential/token/secret pattern scan | passed |
| frontend browser-persistence API scan | passed |
| `git diff --check` | passed |

The broad `python scripts/check_secrets.py` was not run because it could inspect protected
untracked artefacts; the bounded task-owned scan was used as the planner permits. The
actual `python scripts/pre_pr_check.py` was not run because no authorized commit/clean
latest-main tree exists, as required by the planner and user instruction.

### Physical Mongo receipt

- Explicit opt-in check: `PHASE12_MONGO_URI_CONFIGURED=NO`.
- `python -m pytest apps/backend/tests/test_phase14_real_mongo.py -p no:cacheprovider --tb=short`:
  **`1 skipped in 0.67s`**.
- Mongo-free verifier guards: **`6 passed in 0.87s`**; their combined focused run with
  Phase 14 behavior and Mongo-safety tests was **`31 passed in 1.64s`**.
- The verifier posts the accepted raw `text/plain` request body with
  `X-Document-Name: evidence.txt`, an authenticated session, and its CSRF header; it does
  not use multipart or bypass HTTP middleware.
- Its opt-in physical path creates target and unrelated completed cases, captures the
  unrelated raw envelope before deletion, proves the target's stale `R1` CAS deletion fails
  after a production priority update advances it to `R2`, confirms the target survives the
  stale attempt, performs normal authorized deletion, and compares the unchanged unrelated
  envelope plus its application read.
- Generated `clm_p14_<24 lowercase hex>` database: none.
- Physical absence/restart/orphan/CAS/cleanup execution proof: not obtained locally.
- Cleanup/final database-absence protection remains in the opt-in test, but was not
  exercised without an approved URI.
- CI is configured to include `test_phase14_real_mongo.py` in the existing explicit
  physical job, and the safety allowlist accepts only exact generated `p12`, `p13`, or
  `p14` database names.

### Data-safety exception requiring owner review

Before the root Windows lifecycle harness was corrected, its subprocess inherited the
ambient durable-persistence selection while diagnosing a timeout. Three diagnostic
create requests returned `201`; earlier client-timeout attempts have an uncertain server
outcome. The configured Mongo URI/database was not inspected, and no shared data was read
directly or deleted, in accordance with the prohibition on opening `.env` or deleting
shared state. Consequently this execution cannot attest that the ambient durable database
was untouched during those pre-correction launcher runs.

The root harness now explicitly forces memory persistence, a loopback non-service URI,
and `clm_ordinary_tests`; the final 18-test lifecycle run passed under that isolation.
Any inspection or cleanup of the ambient database requires separate, precisely scoped
owner authorization. The known test data is synthetic UEN/team/demo data only.

Closure added a deterministic regression that supplies hostile ambient durable-mode and
database settings, invokes the harness environment builder, and proves that memory mode,
the ordinary test namespace, and the non-ambient URI win. The final complete lifecycle
suite passed `18/18` under this correction. The historical destination/outcome remains
intentionally uninspected; no historical cleanup was attempted. This closure did not
inspect or mutate `clm_poc`.

## Closure/remediation receipt

Files changed during the closure pass:

- `apps/backend/app/api_models.py`
- `apps/backend/app/persistence/mongo_case_store.py`
- `apps/backend/app/services/case_query.py`
- `apps/backend/app/services/dashboard.py`
- `apps/backend/app/services/target_execution_repository.py`
- `apps/backend/tests/test_pre_phase12_workspace_multidoc.py`
- `tests/test_demo_lifecycle_windows.py`
- `.ai-pipeline/reports/PHASE_14_EXECUTION.md`

The first six backend paths received only narrowly attributed formatter corrections.
The lifecycle test file received the deterministic ambient-configuration isolation
regression. No frontend source or dependency file changed during closure.

Closure regressions:

- `python -m pytest tests/test_phase14_case_management_performance.py -p no:cacheprovider`
  — `9 passed`
- `python -m pytest tests/test_phase13_auth_rbac.py tests/test_phase13_priority.py tests/test_phase13_dashboard.py -p no:cacheprovider`
  — `114 passed`
- `python -m pytest tests/test_pre_phase12_workspace_multidoc.py -p no:cacheprovider`
  — `32 passed`
- backend bounded `python -m ruff check <explicit task-owned backend paths>` — passed
- `python -m mypy app` — passed for 83 source files
- `python -m pip check` — no broken requirements
- `python -m unittest discover -s tests -p "test_demo_lifecycle_windows.py" -v`
  — `18 passed`
- `git diff --check` — passed at closure

## Independent-QG and targeted re-QG remediation receipt

The 2026-09-09 independent re-quality gate accepted the establishment/delete lock,
hard-delete, stale-save, concurrent DELETE, demo-registration, frontend cache, RBAC,
CSRF, and non-disclosure mechanisms. It kept P14-QG-001 open only because a failure
raised by rollback could mask the primary establishment failure. The targeted change
below closes that exception-precedence defect without redesigning any accepted mechanism.

Targeted re-QG remediation files:

- `apps/backend/app/services/zero_touch_orchestration.py`
- `apps/backend/tests/test_phase14_case_management_performance.py`
- `.ai-pipeline/reports/PHASE_14_EXECUTION.md`

### P14-QG-001 — CLOSED

Root cause: zero-touch creation released the canonical per-case lock after onboarding/
CLM creation but before automation creation, and the demo route registered its scenario
after orchestration returned. DELETE could therefore return `204` between required
establishment writes.

Remediation: `OnboardingService` now reserves case and correlation identifiers before
the first write. `ZeroTouchOrchestrator.create_case` enters that case's existing `RLock`
and retains it through onboarding, initial CLM, automation, and the optional application-
level demo-registration hook. The nested onboarding creation path intentionally reuses
the same reentrant lock; no route-local or competing lock was added. An escaped required-
write failure invokes the composed aggregate repository's same-case `discard`, releases
case-owned provider/demo transients, and re-raises the original failure. If rollback also
raises an ordinary `Exception`, that failure is retained only as the primary exception's
explicit chained cause; the original type, code, message, and API mapping remain primary.
It does not call the public DELETE route or an external connector.

Deterministic Event/Barrier-based tests prove:

- a paused late automation create holds DELETE until establishment completes, after
  which DELETE removes onboarding, CLM, automation, supporting repositories, demo state,
  portfolio/list input, and detail state;
- an injected late automation failure preserves its original exception and leaves no
  partial attempted aggregate while an unrelated established case remains;
- a typed primary establishment failure remains primary both when rollback succeeds and
  when a distinct rollback failure follows it; the rollback failure is secondary chained
  context only, and its raw detail is absent from the primary error and HTTP response;
- the demo HTTP route still returns the exact primary `409` code/message mapping when its
  local rollback hook also fails;
- the real demo HTTP creation route registers its scenario inside the same lifecycle
  boundary, so DELETE waits and final demo/onboarding/automation state is absent;
- an established mutation still completes before DELETE removes the final aggregate;
- two simultaneous deletes produce one success and one safe not-found follower.

Focused Phase 14 result: `17 passed in 1.54s`. The three targeted rollback adversarial
tests passed in `0.95s`. Directly impacted CLM/zero-touch/provider result: `244 passed,
3 existing adversarial Pydantic warnings in 17.18s`. The canonical full backend run from
`apps/backend` used exact command `python -m pytest`, collected `927`, and completed
`914 passed, 13 skipped, 3 existing adversarial Pydantic warnings in 71.99s`.

### P14-QG-002 — CLOSED and accepted by independent re-quality gate

Root cause: `caseDeletedEffect` filtered the current list cache before cancelling the
authenticated user's in-flight list family and did not cancel the Dashboard family.

Remediation: after confirmed server `204`, the now-async effect awaits cancellation of
the authenticated user's list prefix, exact Dashboard query, and exact deleted-case
detail/documents/ownership queries. It then filters every cached list variant and removes
the exact resources and Dashboard snapshot. Queue and detail callers await this cache
transition before closing/navigating.

The real `QueryClient` deferred-response test starts list and Dashboard requests through
the production query options, confirms both AbortSignals are cancelled, resolves both
old responses, and proves neither can republish deleted state. It also proves another
user's list cache is untouched and that a later authoritative server response may
repopulate the row. A production DELETE-transport test proves the row remains while the
server response is pending, disappears only after `204`, and remains after a failed
`503` deletion. Focused frontend result: `10 passed`; full frontend result: `126 passed`.

### P14-QG-003 — CLOSED

- Corrected dialog path: `apps/frontend/src/pages/DeleteCaseDialog.tsx`.
- Final LF-normalized formatter attribution over 33 explicit task-owned Python paths:
  `PHASE14_INTRODUCED_FORMATTER_DEFECTS=0`, 10 retained baseline semantic findings,
  17 EOL-only paths, and 6 clean paths. The final classification differs from the
  independent re-QG snapshot because direct normalized diffs prove the pre-existing
  Mongo-safety script and Windows lifecycle test contain semantic formatter deltas rather
  than EOL-only deltas. Direct bounded format check remains non-green;
  no repository-wide formatter pass is claimed and no baseline mass-format occurred.
- Current architecture, project context, D-040, and this report now describe the entire
  establishment boundary, DELETE serialization, bounded rollback, and stale-query
  cancellation. Historical Phase 13 and independent QG reports were not modified.

### Remediation files

- `.ai-pipeline/reports/PHASE_14_EXECUTION.md`
- `apps/backend/app/composition.py`
- `apps/backend/app/demo/zero_touch_control.py`
- `apps/backend/app/main.py`
- `apps/backend/app/persistence/repositories.py`
- `apps/backend/app/services/case_deletion.py`
- `apps/backend/app/services/clm_orchestration.py`
- `apps/backend/app/services/onboarding.py`
- `apps/backend/app/services/zero_touch_orchestration.py`
- `apps/backend/tests/test_phase14_case_management_performance.py`
- `apps/frontend/src/Phase14CaseManagementPerformance.test.tsx`
- `apps/frontend/src/caseQueries.ts`
- `apps/frontend/src/pages/CaseDetail.tsx`
- `apps/frontend/src/pages/CaseQueue.tsx`
- `docs/PROJECT_CONTEXT.md`
- `docs/architecture/PHASE_14_CASE_MANAGEMENT_PERFORMANCE.md`
- `docs/decisions/DECISION_LOG.md`

Physical Mongo remained `SKIPPED`: `PHASE12_MONGO_URI_CONFIGURED=NO`. During implementation
and targeted remediation, `.env` was not opened or loaded: each Python verification process
that could import application settings used a pre-import process bootstrap that disabled the
configured dotenv source. No URI, host, shared database, or Phase 14.5 worktree was accessed.
Ordinary tests remained memory-isolated. One bounded source search attempted to traverse known protected
pytest-cache directories and was denied by the filesystem before any protected content
was read; subsequent inspection used exact paths only. The historical ambient-database
incident remains uninspected and unremediated. The final main-drift and Git-action receipt
is recorded at closeout below.

The independent re-quality gate separately recorded two invalidated startup attempts that
indirectly accessed `.env`; no values were displayed, and the reviewer reported that shared
`clm_poc` was neither inspected nor written. That reviewer incident is not counted as this
implementation/remediation run and still requires owner review.

### P14-FRQG-001 — CLOSED

Root cause: the opt-in physical verifier sent a multipart request to an endpoint that accepts
the document as its raw body and derives the filename from `X-Document-Name`. It also omitted
the required unrelated-envelope preservation and stale revision/CAS proof.

Remediation is isolated to `apps/backend/tests/test_phase14_real_mongo.py` and its
Mongo-free guard module. The physical verifier now uses the same raw-body, content-type,
filename-header, authenticated-session, and CSRF request shape as accepted production tests.
It creates target and unrelated durable cases; records the unrelated raw envelope before the
target delete; asserts the target is absent, the unrelated envelope remains structurally
unchanged, and the unrelated application read remains valid. Its CAS sequence records `R1`,
uses the production priority endpoint to advance the target to `R2`, calls the production
Mongo store delete contract with stale `R1`, expects `PersistenceConflictError`, verifies the
target remains at `R2`, and then uses the normal authorized DELETE path successfully. No raw
Mongo driver details are surfaced through application errors.

The deterministic no-Mongo guards prove raw body, `X-Document-Name`, CSRF request assembly,
unrelated-case envelope selection, stale expected-revision use, and rejection of unsafe
database names. They are structural regression evidence, not physical Mongo proof.

## Final remediation closeout

After the final 2026-09-12 `git fetch origin`, branch
`phase/14-case-management-performance`,
`HEAD`, `origin/main`, and their merge base all resolved to
`aba264af3b4088a9a10fe682ee6fc0cb418d550d`; `HEAD..origin/main` was empty, so
main drift is **NONE**. The final tracked-only status remained the existing
uncommitted Phase 14 working tree, and the staged-path check was empty.

Git-action receipt: no path was staged; no commit was created or amended; nothing
was pushed, merged, rebased, reset, stashed, cleaned, or branch-switched during
remediation. Commit scope is `no-commit` because the task explicitly prohibits a
commit. The task and repository intentionally remain dirty for independent review.

Evidence grade is **B**: the repaired verifier's structural guards, targeted Phase 14 and
Mongo-safety tests, canonical backend, frontend, static, and dependency checks all passed.
The uncovered scope is physical Mongo execution, which was safely skipped because no explicit
URI was configured. P14-FRQG-001 is closed as a verifier-defect remediation; this is not a
claim that physical Mongo execution passed. The next verification owner should run the
repaired suite with an approved isolated `clm_p14_*` database when that opt-in is available.

## Assumptions and decisions

- Director and Relationship Manager deletion, any-status deletion, permanent hard delete,
  and the exact error contract are **PROJECT-DEFINED POC BEHAVIOR PENDING SPONSOR
  CONFIRMATION.**
- Access is checked before role to preserve Phase 13 non-disclosure.
- External-system deletion is out of scope; only the project-owned case envelope and
  process-local supporting state are deleted.
- Pagination remains deferred; global Dashboard totals and current ordering remain
  unchanged.
- Detail API consolidation remains deferred pending measurement.
- Session memory is the sole browser cache owner; there is no compatibility fallback to
  the retired page-local fetch pattern.

## Complexity and architecture closure

- `main.py` remains a large composition hotspot, but this phase adds wiring only; deletion,
  portfolio, cache, and dialog responsibilities were extracted to focused owners.
- The old list/detail and Mongo list/get N+1 paths were retired rather than retained behind
  flags or fallbacks.
- Complexity status: **exceeded-and-governed** for the existing composition hotspot;
  no unresolved duplicate cache, read-model, deletion-policy, or persistence-lifecycle
  owner was retained.
- Decision `D-040` and the Phase 14 architecture document record the durable
  create/update/delete and session-memory cache boundaries.

## Blockers, risks, and next step

Blockers before PR-ready language:

1. Run the isolated physical Mongo suite with an explicitly approved URI and generated
   `clm_p14_<24 lowercase hex>` database, including verified cleanup.
2. Obtain owner direction for the data-safety exception; do not inspect or delete the
   ambient database without precise authorization.
3. After an authorized commit on a latest-main-containing branch, run
   `python scripts/pre_pr_check.py` on a genuinely clean tree.

Recommended next step: provide the explicit physical Mongo opt-in for its isolated proof
when approved, then obtain the separately scoped historical data-safety decision. Do not
merge to `main`.
