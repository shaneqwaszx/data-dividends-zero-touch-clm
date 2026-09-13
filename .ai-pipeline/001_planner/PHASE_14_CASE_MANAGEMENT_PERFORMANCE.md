# Phase 14 — Case Management & Performance Optimisation

## Plan header

**Goal:** Add permanent, backend-authorized deletion of any accessible CLM case for
Director and own-team Relationship Manager actors, while removing the current frontend
and Mongo list/dashboard N+1 paths and adding session-scoped in-memory query caching.

**Architecture:** Keep FastAPI as the only application boundary. Route deletion through
one application service which re-authorizes inside the existing canonical per-case lock
and invokes a persistence deletion port. Mongo deletes the one complete case envelope by
revision-aware compare-and-delete; memory mode removes the equivalent records through a
composed in-memory deletion adapter. Split repository creation from update so a stale
writer cannot recreate a deleted case. Replace the case-list join with a strict lightweight
portfolio read model and a Mongo projection query. In React, mount one TanStack Query
client per authenticated session lifecycle, with no persistence plugin or browser storage.

**Tech stack:** Python 3.12, FastAPI 0.141.1, Pydantic 2, PyMongo 4.15.1,
MongoDB 7, React 18.3.1, TypeScript 5.9.3, Vite 7.1.11, Vitest 3.2.4, and one
new runtime dependency, `@tanstack/react-query`. A DOM-capable Vitest environment
(`jsdom` as a development dependency) is justified only for destructive-dialog focus,
keyboard, and duplicate-submission tests.

**Baseline/authority refs:** `AGENTS.md`; the Phase 14 owner brief supplied on
2026-09-08; `docs/PROJECT_CONTEXT.md`; `.agents/skills/README.md`;
`.ai-pipeline/README.md`; `docs/development/BRANCH_MERGE_PROTOCOL.md`;
`.agents/skills/integration-safe-development/SKILL.md`; the Phase 13 planner,
architecture, execution/remediation reports, Dashboard/Mongo completion report, final
quality evidence, and duplicate-browser-source final re-quality gate; current source and
tests at commit `aba264af3b4088a9a10fe682ee6fc0cb418d550d`.

**Compatibility boundary:** Preserve Phase 13 authentication, exact Origin/Referer
cardinality and trust, session-bound CSRF, safe case non-disclosure, team immutability,
priority semantics/order, Dashboard definitions, process-local versus Mongo behavior,
durable envelope schema version 2, provider call-stopping/replay protections, and all
Registry/document/reconciliation/ownership/CLM/Mock GoldTier business behavior. The
intentional additions are one DELETE route, repository create/update separation, case
deletion ports, additive list-summary fields, a projection read path, cache-driven UI
loading, and role-gated destructive controls.

**TDD Route:**

- Mode: off
- Decision: skipped
- Strict authority: not applicable
- Strict signals: deletion, RBAC, persistence, concurrency, shared API/types, and cache
  isolation are high-risk, but neither the user nor the repository requires strict
  RED/GREEN TDD.
- Light eligibility: not applicable; this is a cross-module security and persistence
  change.
- TDD-fit exception: none.
- Test posture: make each bounded change and immediately run focused post-change
  regression; then run adverse concurrency, physical Mongo, broad regression, and an
  independent quality gate.
- Reason: meaningful tests are mandatory, but strict test-first execution was not
  authorized.
- Verification: the exact focused and broad checks in sections 27 and 33.

**Verification:** Completion requires deterministic HTTP-call and Mongo-query evidence,
the complete delete/RBAC/security/cache matrix, isolated physical Mongo restart proof,
all repository CI-equivalent checks, final latest-main integration evidence, and an
independent Phase 14 quality gate. Millisecond thresholds are deliberately not used
without a measured baseline.

## Planning controls

### Aegis visibility

Planning is necessary because this phase changes a destructive authorization contract,
persistence lifecycle, stale-write behavior, shared read models, frontend dependency
surface, and authenticated data lifetime.

### BaselineUsageDraft

- Required baseline refs: repository rules, project context, integration protocol, Phase
  13 authentication/RBAC/priority/Mongo/Dashboard/test-isolation authority, current code,
  and the Phase 14 brief.
- Acknowledged before plan refs: all required refs above.
- Cited in plan refs: plan header and sections 2, 3, 8–11, 13–22, 25–35.
- Missing refs: none material to the project-defined POC plan. No sponsor production
  deletion policy exists; this is explicitly provisional rather than missing authority
  for the requested POC behavior.
- Decision: continue.

### Requirement Ready Check

- Requirement source refs: Phase 14 owner brief and `AGENTS.md`.
- Goals and scope refs: permanent case deletion, role matrix, concurrency safety,
  Mongo/memory parity, list/dashboard query reduction, and session-memory caching.
- User/scenario refs: Director, own-team RM, cross-team RM, Client Onboarder,
  unauthenticated actor, absent case, any workflow status, logout/expiry/identity change,
  fresh/stale/empty cache, and growing case volume.
- Acceptance/verification refs: the explicit Phase 14 test and deterministic performance
  criteria plus current repository CI and Phase 13 regression owners.
- Open blocker questions: none for planning. Production retention/deletion policy remains
  sponsor-unconfirmed and must not be inferred.
- Decision: ready.

### Change Necessity

- User-visible need: permanent deletion, role-specific control, immediate repeat
  navigation, and removal of loading caused by repeated list/detail/database reads.
- No-change/non-code option: documentation, frontend hiding, HTTP cache headers, or a
  browser-storage shortcut cannot hard-delete persistence, enforce RBAC, prevent stale
  writes, or safely isolate cached team data.
- Why code change is necessary: there is no delete API/repository operation; list pages
  explicitly call detail for every row; `CaseQueryService` performs a Mongo
  list plus a Mongo get per record; every tab remount starts a new request.
- Minimum change boundary: a focused deletion owner and portfolio-read owner; narrow
  persistence, auth-route, response-model, composition, frontend query, and affected page
  integrations; focused tests and required dependency manifests.
- Decision: code-change.

### Existence Check

- Proposed new surfaces: `CaseDeletionService`/deletion port, lightweight
  portfolio read repository, authenticated query-cache owner, and delete dialog.
- Existing reuse candidates: `CaseAccessPolicy`, `OnboardingService.case_lock`,
  Phase 12 envelope/store, existing memory repositories, `AuthProvider`, `api.ts`, and
  design-system dialog styles.
- Why existing surfaces are insufficient: none currently owns destructive role policy or
  cross-repository deletion; the automation repository exposes only automation records;
  local page state has no shared cache, deduplication, invalidation, or session reset.
- Creation proof: the new owners replace—not duplicate—the current list join and centralize
  deletion/cache lifecycle rather than distributing Mongo calls or page-local caches.
- Entropy/retirement impact: retire Case Queue/Onboarded per-row detail loading and retire
  Mongo list-plus-get. Do not retain fallback paths. The query-cache package is removable
  without changing backend contracts; no persistent cache schema is created.
- Decision: add-with-proof.

### Architecture Integrity Lens

- Invariant: backend-authored identity and canonical case ownership decide access before
  deletion or data projection; inaccessible and absent cases remain indistinguishable.
- Canonical owners/contracts: `CaseAccessPolicy` owns visibility;
  `CaseDeletionService` owns role/deletion policy; the case lock owns in-process case
  serialization; persistence adapters own physical removal; the portfolio repository owns
  efficient summaries; TanStack Query owns browser cache mechanics.
- Responsibility overlap: FastAPI does not call Mongo directly; React does not infer
  database authority; repositories do not derive identity from client input; Dashboard
  remains a calculation service over authorized summaries.
- Higher-level simplification: one strict summary model serves Cases, Onboarded, and
  Dashboard, eliminating both HTTP and database joins while leaving the durable write
  envelope unchanged.
- Retirement/falsifier: remove old `Promise.all(detail-per-row)` and
  `automation.list_records() -> get_case()` paths in the same slice. Discovery that a
  required table field cannot be safely projected would narrow that field, not restore
  N+1 as a fallback.
- Verdict: proceed.

### Complexity Budget and Plan-Time Complexity Check

- Artifact class: destructive security endpoint, persistence lifecycle, read projection,
  and authenticated frontend cache.
- Current pressure: `main.py` is about 1,790 lines, `App.tsx` about 2,234 lines,
  `api.ts` about 482 lines, and `MongoCaseStore` already owns envelope validation/CAS.
- Projected pressure: over-budget if deletion policy, cache keys, or query mapping is
  embedded directly in hotspot files.
- Planned governance: add focused service/read-model/cache/dialog modules; restrict
  `main.py`, `App.tsx`, `api.ts`, and shared types to wiring and additive contracts.
- Recommendation: add owner files and extract shared query/mutation effects; do not add
  another application state manager or replace the durable model.

### Plan Pressure Test

- Owner/contract/retirement: deletion, create/update, projection, cache, and old N+1
  retirement are explicit.
- Architecture integrity/higher-level path: existing access policy, case lock, envelope,
  service composition, and design-system modal styles are reused.
- Verification scope: role/non-disclosure, CSRF, physical absence, restart, resurrection,
  call counts, query counts, cache isolation, package integrity, and broad regressions are
  covered.
- Task executability: sections 25–27 name concrete files, slices, commands, and expected
  outcomes.
- Pressure result: proceed.

## 1. Executive summary

Phase 14 should implement hard deletion as a true application-database lifecycle action,
not as a workflow status. Director may delete any accessible case, including legacy
unassigned cases. Relationship Manager may delete an own-team case. Client Onboarder is
explicitly forbidden only after the existing visibility check has established that the
case is accessible; inaccessible cases remain safe 404. The DELETE is authenticated,
CSRF-protected, and returns `204 No Content`.

The performance work should replace the existing case-list join with one strict summary
query. This removes the browser `1 + N` detail pattern in Cases/Onboarded and the Mongo
`1 + N` full-envelope pattern in Cases/Dashboard. A session-memory TanStack Query client
then supplies 45-second fresh data, stale-while-revalidate behavior, in-flight request
sharing, cancellation, mutation invalidation, and complete cache destruction on logout,
401, or identity transition.

No case deletion is sent to ACRA or GoldTier. Current GoldTier behavior is Mock-only;
deleting this application's target ledger/result does not reverse even the simulated
external party/policy operation.

## 2. Verified baseline/current-state findings

**OBSERVED baseline:**

- Branch, `HEAD`, local `origin/main`, and merge base were all verified before analysis:
  `phase/14-case-management-performance` at
  `aba264af3b4088a9a10fe682ee6fc0cb418d550d`.
- The tracked working tree was clean at entry using
  `git status --short --untracked-files=no`.
- Phase 13 middleware authenticates every `/api` route except login, resolves the actor
  from an opaque server session, checks exact browser source policy, requires CSRF on
  `POST`/`PUT`/`PATCH`/`DELETE`, and performs central case access for routes classified
  `CASE_SCOPED`.
- `CaseAccessPolicy` allows Director to access all canonical and legacy-null-team cases;
  team actors may access only exact own-team cases. Missing and inaccessible cases share
  the fixed `404 CASE_NOT_FOUND` response.
- `CaseQueryService` lists automation records, then calls
  `OnboardingService.get_case()` once per record before authorization/filter/order.
- `DashboardService` calls that same `CaseQueryService.list_cases()` and derives all
  metrics in memory from the returned authorized records.
- `MongoZeroTouchAutomationRepository.list_records()` calls `MongoCaseStore.list()`,
  which fetches and strictly deserializes complete envelopes. `CaseQueryService` then
  triggers an additional full-envelope `find_one` per automation record.
- `DurableCaseSnapshot` schema v2 is one document containing onboarding/canonical Registry
  state, documents and their events/replacement links, ownership/UBO analysis,
  reconciliation and decisions, CLM state, zero-touch automation and exception/timeline
  state, target execution ledger, demo-scenario ID, and timestamps/revision.
- Process-local memory mode stores the equivalent state across separate repositories.
  `ZeroTouchDemoControl` additionally retains recovery-fault counters; the in-memory
  provider-binding resolver may retain per-case test/demo provider factories.
- `MongoOnboardingCaseRepository.save()` currently creates a new envelope when no
  snapshot exists. That behavior is a resurrection risk if a stale writer runs after
  deletion.
- Established document, ownership, reconciliation, CLM, automation, target-submission,
  and priority mutations participate in the `OnboardingService.case_lock(case_id)`
  boundary through their service owners. Initial staged onboarding writes occur outside
  that lock and must be brought inside the same lifecycle boundary.
- `App.tsx` conditionally mounts one tab at a time. Returning to Dashboard, Cases, or
  Onboarded remounts the page and repeats its effect-driven network loading.
- `CaseQueue` and `OnboardedClients` each fetch the list and then every full case detail.
  The list response lacks the jurisdiction/creation/completion/Mock-party fields those
  tables currently derive from detail.
- `CaseDetail` loads summary, documents, and ownership in three concurrent HTTP requests;
  this is legitimate detailed data and should occur only after opening a case. Repeat
  views can reuse session cache.
- `AuditTrail` has another `1 + N` full-detail pattern when showing all cases. It is
  confirmed but deliberately deferred from Phase 14 because an audit event read model
  has a separate pagination and retention contract.
- Existing frontend tests run in Node and largely use static rendering/direct function
  tests. A destructive accessible dialog needs one focused DOM-capable test file.

## 3. Current performance call/query map

### 3.1 Dashboard load

```text
Dashboard mount
  -> GET /api/clm/zero-touch/dashboard
  -> FastAPI auth middleware
  -> DashboardService.get_dashboard(actor)
  -> CaseQueryService.list_cases(actor)
  -> ZeroTouchAutomationRepository.list_records()
  -> MongoCaseStore.list(): 1 find of every complete envelope + full decode
  -> for each automation: OnboardingService.get_case(case_id)
  -> MongoCaseStore.get(): N find_one calls + N complete-envelope decodes
  -> authorize/filter/order in Python
  -> calculate Dashboard in Python
```

Current Mongo target: `1 + N` database reads and repeated full-envelope decoding.
Proposed target: one authorization-scoped projection query; Dashboard calculations remain
in the service and remain truthful over all authorized cases.

### 3.2 Case Queue load

```text
CaseQueue mount/filter change
  -> GET /api/clm/zero-touch/cases: backend 1 + N Mongo reads as above
  -> browser receives N list items
  -> Promise.all(GET /api/clm/zero-touch/cases/{id}) for every item
  -> each detail passes middleware case lookup and performs several repository reads
```

Current browser target: `1 + N` HTTP requests. Proposed normal target: one list request
whose response contains every table field. No detail request occurs until a row opens.

### 3.3 Case Detail load

```text
Open one row
  -> GET zero-touch case summary
  -> GET documents for case
  -> GET ownership for case
  -> render detailed evidence
```

The three detailed resources are valid, distinct current contracts. Cache each by case
ID and pass `AbortSignal` through the query functions. Consolidating their backend APIs
or the several Mongo reads used to assemble the summary is deferred pending measurement;
do not broaden Phase 14 into a detail-contract rewrite.

### 3.4 Priority mutation

```text
PriorityControl
  -> PATCH /cases/{id}/priority (CSRF)
  -> CaseQueryService takes canonical case lock
  -> access policy re-reads case
  -> onboarding repository saves case/envelope
  -> page currently reloads list + N details, or detail reloads 3 resources
```

Proposed: keep backend mutation unchanged except create/update-safe repository semantics;
invalidate/refetch the one active list summary, remove inactive list snapshots where
server order could be stale, remove Dashboard cache, and refresh only the affected detail.
Never refetch every case detail.

### 3.5 Logout/login/session expiry

```text
logout -> POST /api/auth/logout -> AuthProvider clears auth state
401 -> transport callback -> AuthProvider clears auth state
login/me -> server-authored profile/CSRF -> authenticated App mounts
```

There is currently no query cache to clear. Proposed: the same transition synchronously
cancels and clears the QueryClient before anonymous or different-user content can mount;
a successful login begins with an empty client and fire-and-forget prefetch.

## 4. Confirmed bottlenecks

1. **Frontend Cases N+1:** one list plus N zero-touch detail requests.
2. **Frontend Onboarded N+1:** one completed list plus N zero-touch detail requests.
3. **Backend list/dashboard N+1:** one full envelope list plus N full envelope gets.
4. **Oversized read payload:** Mongo listing decodes documents, events, ownership graphs,
   reconciliation, target ledger, and other evidence not needed by tables/Dashboard.
5. **Navigation reload:** conditional tab remount plus page-local effects discard usable
   recently fetched data.
6. **Priority refresh amplification:** one PATCH is followed by the full list/detail N+1.
7. **Additional measured candidate:** Audit all-cases is `1 + N`, but is outside the
   minimum Phase 14 contract and is explicitly deferred.

## 5. Phase 14 goals

- Permanently remove an authorized case and all application-owned case state.
- Encode the exact Director/RM/Onboarder/unauthenticated/non-disclosure matrix.
- Permit deletion in every workflow status without resurrection.
- Keep deletion behind existing authentication, browser-origin, CSRF, and case-scope
  controls.
- Achieve one bounded HTTP list request for normal Cases and Onboarded rendering.
- Achieve one bounded Mongo projection query for Cases and Dashboard list input.
- Keep Dashboard totals truthful over all authorized cases.
- Render fresh cached Dashboard/Cases immediately and stale data immediately with at
  most one background refresh.
- Clear all cached business data on logout, 401, identity change, and new login.
- Preserve every Phase 13 security, business, persistence, and test-isolation invariant.

## 6. Explicit non-goals

- Archive, soft delete, recycle bin, cancel status, restore, undo, or bulk delete.
- Deleting/reversing ACRA, GoldTier, or future external-system activity.
- Production retention policy, legal hold, supervisory approval, maker-checker, or audit
  disposition policy.
- New workflow stages, Ready-for-Approval/four-eye, UBO rules, ACRA/GoldTier live work,
  PingFed/SSO, or authentication redesign.
- Durable/browser-disk cache, offline mode, service worker, Redux/global-state rewrite,
  or persistent query-cache plugin.
- Pagination, AuditTrail event read-model redesign, case-detail endpoint consolidation,
  or arbitrary latency SLOs in this phase.
- Broad database migration, schema-version bump, unrelated indexes/refactors/UI redesign.

## 7. Deletion role/RBAC matrix

| Actor | Case | Middleware visibility | Deletion decision | HTTP |
|---|---|---:|---:|---:|
| Director | Team A | visible | allow | `204` |
| Director | Team B | visible | allow | `204` |
| Director | legacy/null team | visible | allow | `204` |
| Director | absent | not found | no route execution | `404 CASE_NOT_FOUND` |
| Relationship Manager | own canonical team | visible | allow | `204` |
| Relationship Manager | other team | hidden | no route execution | `404 CASE_NOT_FOUND` |
| Relationship Manager | legacy/null team | hidden | no route execution | `404 CASE_NOT_FOUND` |
| Client Onboarder | own canonical team | visible | explicit forbid | `403 CASE_DELETE_FORBIDDEN` |
| Client Onboarder | other team | hidden | no route execution | `404 CASE_NOT_FOUND` |
| Client Onboarder | absent | not found | no route execution | `404 CASE_NOT_FOUND` |
| Unauthenticated | any/absent | no actor | deny before lookup | `401 AUTHENTICATION_REQUIRED` |

The frontend may hide controls using the server-authored authenticated role and the
already-authorized case result, but that is only presentation. The deletion service
re-reads the canonical case and actor inside the lock; no request role/team/capability
field is accepted.

## 8. DELETE API contract

Add the exact route policy and handler:

```http
DELETE /api/clm/zero-touch/cases/{case_id}
X-CSRF-Token: <session-bound value>
Cookie: <opaque host-only session>
```

- Classify it as `CASE_SCOPED` in the existing exact route inventory.
- Accept no request body, team, role, revision, force flag, or status override.
- Return `204 No Content` with an empty body after physical deletion and local lifecycle
  cleanup. This matches HTTP semantics and avoids inventing a deleted-case DTO.
- Preserve the current fixed `401`, `403 CSRF_VALIDATION_FAILED`, and safe
  `404 CASE_NOT_FOUND` boundaries.
- Map accessible Client Onboarder denial to fixed `403 CASE_DELETE_FORBIDDEN` without
  extra case metadata.
- Map a revision race/persistence conflict for an otherwise authorized case to bounded
  `409 CASE_DELETE_CONFLICT`; the client leaves the case visible and may retry after an
  authoritative refresh.
- Map sanitized persistence unavailability through the existing safe infrastructure
  error convention (normally `503`); never emit driver/URI/internal state.
- A repeated DELETE after success reaches the middleware's normal safe `404`.
- Add no OpenAPI response body for 204. `api.ts` must not attempt JSON parsing on success.

## 9. Hard-delete persistence architecture

```text
DELETE route
  -> Phase 13 auth/origin/CSRF middleware
  -> CaseDeletionService.delete(actor, case_id)
  -> OnboardingService.case_lock(case_id)
  -> re-read canonical case + CaseAccessPolicy
  -> role policy (Director or Relationship Manager)
  -> CaseDeletionRepository.delete_case(case_id)
       Mongo: revision-aware delete of the one envelope
       Memory: composed delete across all case-owned repositories
  -> release case-associated demo/provider-binding memory
  -> 204
```

Create a narrow deletion port rather than adding Mongo methods to FastAPI or a general
administrative repository. The service owns authorization/order; adapters own physical
removal.

### Mongo contents removed by one envelope delete

- onboarding case and canonical/Registry acquisition state;
- onboarding workflow events/error/GoldTier result;
- document records, fields, document events, and replacement links;
- ownership graph, deterministic calculations, issues, candidates, and events;
- reconciliation observations, discrepancies, decisions, and events;
- CLM readiness/submission snapshot/status/events;
- zero-touch automation status, exceptions, metrics, timeline, and recovery state;
- Mock target execution intent/outcome/receipt ledger;
- persisted demo-scenario identifier;
- envelope timestamps, schema version, and revision.

The Mongo adapter obtains the current strict envelope under the store lock and deletes
with `{"_id": case_id, "revision": expected_revision}`. `deleted_count != 1` is a
conflict, never success. No child collection exists today, so this one physical removal
has no durable case-owned orphan. Tests must prove that fact directly.

### Memory contents removed

Add narrow `delete_for_case` operations to the memory onboarding, document, ownership,
reconciliation, CLM, automation, target-execution, and demo-scenario owners. The composed
memory deletion adapter invokes them while the canonical case lock is held. Target
entries are removed by `entry.submission_input.case_id`; document insertion-order state
is removed with documents. The demo control drops any per-case recovery-fault counter.
If the automation used a non-default in-memory provider binding, release that unique
binding after the automation snapshot is captured and before success is returned.

Do not reach into private repository dictionaries from the application service. Do not
call any external connector during deletion.

## 10. Concurrency/resurrection prevention design

The smallest safe design has five mandatory parts:

1. **Serialize deletion and mutations.** Acquire the existing
   `OnboardingService.case_lock(case_id)` before the deletion service re-reads the case,
   checks access/role, or removes state. Keep the lock through local cleanup.
2. **Audit every mutation owner.** Existing established-case paths already use this lock
   through onboarding/document/ownership/reconciliation/CLM/automation/priority service
   owners. Add explicit regression inventory so a future case mutation cannot bypass it.
   Bring initial staged case persistence inside the case lock once its server UUID exists,
   and register demo-scenario state under the same lock.
3. **Split create from update.** Add insert-only `create()` to
   `OnboardingCaseRepository`; make `save()` update-only and fail if the case/envelope is
   absent. Use `create()` exactly once in staged onboarding. Apply the same semantics in
   memory and Mongo. This removes the current “missing means create” resurrection path.
4. **Use storage CAS.** Mongo delete matches current revision. Concurrent external-process
   writes either win first (delete retries from current state) or make deletion fail 409;
   a stale update after successful delete fails because update is no longer insert-capable.
5. **No tombstone fallback.** A tombstone would contradict the requested physical hard
   delete and create a second lifecycle store. Explicit create/update semantics and CAS
   are sufficient and testable.

Authorized deletion is not restricted by automation status. For an in-process mutation
already holding the case lock, DELETE waits; after that mutation completes, deletion
removes the final envelope. For a cross-process revision race it fails closed with 409
and never partially reports success. The implementation must not add a “terminal cases
only” restriction.

## 11. Mongo vs memory parity

| Behavior | Memory | Mongo |
|---|---|---|
| Access/role decision | same deletion service | same deletion service |
| Serialization | canonical per-case `RLock` | canonical per-case `RLock` plus store lock |
| Create | explicit insert-only | `insert_one`, duplicate fails |
| Update after delete | fails missing/conflict | replacement/update fails missing/conflict |
| Delete | remove all case-owned repo entries | compare-and-delete one envelope |
| Repeated delete | safe 404 | safe 404 |
| Restart proof | process restart naturally empty | physical absence survives restart |
| External calls | none | none |

Parity is behavioral, not an identical storage implementation. The durable schema stays
at version 2 because no stored field changes.

## 12. Frontend confirmation-modal behavior

Add a reusable `DeleteCaseDialog` using the existing `dialog-backdrop`, `dialog`, and
button styles, with destructive-specific styling kept small.

- Show Delete only for server-authored `DIRECTOR` and `RELATIONSHIP_MANAGER` profiles on
  authorized Case Queue rows and Case Detail. Client Onboarder gets no usable control.
- The row-level Delete button stops row navigation.
- Opening the dialog performs no request. The dialog shows legal name when present,
  UEN/registration ID, and: “This removes the case and its stored onboarding information
  and cannot be undone.”
- Actions are `Cancel` and `Delete permanently`; initial focus goes to Cancel, Escape
  cancels, focus is contained while open, and focus returns to the invoking control.
- Use `role="alertdialog"`, `aria-modal="true"`, a unique labelled heading, and a
  described irreversible-warning element.
- Cancel, backdrop-safe close, and Escape perform zero mutation.
- Confirm uses both a synchronous in-flight guard and disabled controls so rapid click,
  Enter, or rerender results in exactly one DELETE.
- While pending, render `Deleting…`; do not remove the case yet.
- Failure keeps the case and dialog visible and shows a bounded `role="alert"` message.
- Success closes the dialog, removes the case from all cached lists, removes its detail
  resources and Dashboard cache, and—when invoked from detail—calls a dedicated
  `onDeleted` callback that returns to Cases without attempting to reopen it.
- A direct URL/API reopen receives the backend 404. There is no undo, archive, or bulk
  selection.

## 13. Cache architecture recommendation

**Decision: use `@tanstack/react-query`; do not build a first-party cache.**

The requested behavior is no longer a simple map: it requires stale/fresh time,
observer-driven background refresh, one in-flight promise per key, AbortSignal
cancellation, mutation cancellation/invalidation, error retention, cache removal, and
whole-session reset. Reimplementing those mechanisms beside the current page-local state
would create a second state framework with more security-sensitive lifecycle code than
the dependency integration.

Create a focused frontend query module containing keys, options, and mutation effects.
`AuthProvider` owns one `QueryClient` for the current in-memory browser process and wraps
authenticated children in `QueryClientProvider`. On logout, 401, any authenticated
identity transition, and before accepting a new login profile, synchronously clear the
client; cancel active queries best-effort. Include `profile.user_id` in every business
query key as defense in depth even though the cache is also cleared.

Do not add `persistQueryClient`, localStorage/sessionStorage/IndexedDB adapters, service
workers, or custom serialization. Page reload creates a new empty client naturally.

Package impact:

- runtime: one exact-pinned `@tanstack/react-query` dependency and lockfile update;
- development only: exact-pinned `jsdom` for one focused interaction/accessibility test
  environment; no testing framework replacement;
- tests: QueryClient unit/integration tests with retries disabled and cache timers
  controlled; existing static render tests remain valid.

The selected API supports `QueryClient.clear`, cancellation, invalidation, cached
freshness, and AbortSignal query functions in the current official documentation:
[QueryClient](https://tanstack.com/query/latest/docs/framework/react/reference/classes/QueryClient),
[important defaults](https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults),
and [query cancellation](https://tanstack.com/query/latest/docs/framework/react/guides/query-cancellation).

## 14. Concrete cache TTL/stale policy

Use one deterministic policy for Dashboard, list, case summary, documents, and ownership:

- `staleTime: 45_000` milliseconds;
- `gcTime: 15 * 60_000` milliseconds, still bounded by session clearing;
- `refetchOnWindowFocus: false` for deterministic demo behavior;
- `refetchOnReconnect: true`;
- `retry: 1` for GET queries and `retry: false` for mutations;
- query functions consume the supplied `AbortSignal`.

Semantics:

- **fresh cache:** render immediately and do not request on remount;
- **stale cache:** retain/render data immediately and issue at most one shared background
  refresh; show `Refreshing…` from `isFetching` without blanking content;
- **no cache:** show the existing bounded loading state and issue one request;
- **manual Refresh:** call `refetch()` and therefore always issue a real request;
- **background error:** retain last successful data and show a bounded non-blocking
  warning; initial-load error keeps the existing blocking retry state.

## 15. Cache key design

All keys begin with `['auth', userId]`:

```text
['auth', userId, 'dashboard']
['auth', userId, 'cases', 'list', {status, priorityFilter, prioritySort}]
['auth', userId, 'cases', 'detail', caseId]
['auth', userId, 'cases', 'documents', caseId]
['auth', userId, 'cases', 'ownership', caseId]
['auth', userId, 'system', 'execution-profile']
```

Onboarded reuses the cases-list key with `status='COMPLETED'`; do not duplicate the same
server result under an `onboarded` key. Jurisdiction/search remain client presentation
filters and are not network cache-key fields. Normalize absent values to stable explicit
sentinels rather than creating equivalent `undefined`/empty variants.

AuditTrail should reuse cached individual detail keys when available, but Phase 14 does
not introduce an all-audit endpoint or promise to eliminate its first-load N+1.

## 16. Cache invalidation matrix

| Mutation | Detail | Lists | Dashboard | Other |
|---|---|---|---|---|
| Case create | seed returned detail | remove/invalidate list family | remove | default list/dashboard may refetch when active |
| Case delete | cancel/remove summary, docs, ownership | synchronously filter ID from every cached list after 204 | remove entire snapshot | navigate away from deleted detail |
| Priority change | invalidate affected detail | refetch active list; remove inactive variants whose filter/order may be stale | remove | never fetch N details |
| Document upload/retry/replace/review | set returned summary when available; invalidate documents | invalidate active/remove inactive lists if visible summary can change | remove | invalidate reconciliation-relevant detail |
| Reconciliation resolve | set returned summary; invalidate affected supporting data | invalidate active/remove inactive lists | remove | preserve 409 authoritative refresh |
| Resume/exception/workflow mutation | set returned summary; invalidate supporting data | invalidate active/remove inactive lists | remove | polling writes latest detail cache |
| Logout | cancel/remove all | clear all | clear all | clear mutation cache |
| Any 401/session expiry | cancel/remove all | clear all | clear all | unmount authenticated shell |
| New/different authenticated profile | start from empty identity namespace | empty | empty | prefetch only after profile accepted |

Deletion may patch cached arrays by removal because removal cannot violate backend order.
Do not locally recompute Dashboard counts/trends or priority order. Removing Dashboard
data forces the next view to obtain authoritative totals and prevents a deleted case from
flashing in stale cached metrics.

## 17. Cross-user cache isolation design

1. Query keys include the stable server-authored `profile.user_id`; no team/role is read
   from browser storage or request input.
2. `clearSession()` first cancels/clears the QueryClient and transport CSRF state, then
   transitions the UI to anonymous.
3. A successful login clears any prior cache before installing the new CSRF token/profile.
4. A profile restored by `/auth/me` starts in a naturally empty page-load cache.
5. If an authenticated profile identity changes unexpectedly, clear before rendering it.
6. A 401 callback clears cache even when the failed request was a background refresh.
7. No persistent cache plugin or storage API exists.
8. Tests use distinct Team A/Team B payload markers and prove user B never renders or
   retrieves user A cached Dashboard/list/detail data.

## 18. Frontend N+1 remediation

Extend `ZeroTouchCaseListItemResponse` and its TypeScript peer with the bounded scalars
already needed by Case Queue and Onboarded:

- resolved jurisdiction;
- automation `created_at` and `completed_at`;
- Mock GoldTier party ID when present.

Existing fields already cover legal name, UEN, status, stage, update time, active
exception count, human interventions, final outcome, team/client scope, and priority.
These additions are projections of existing canonical/envelope data; they add no policy.

Change `mapZeroTouchCaseToCaseRow` and `mapCompletedCaseToOnboardedRow` to consume only the
list item. Remove optional detail parameters and both `Promise.all(fetchZeroTouchCase)`
loops. Case Queue and Onboarded each call one `useQuery` list key. Opening a row then loads
the three detail resources by case ID.

Acceptance: rendering N rows makes exactly one list HTTP request and zero detail requests.

## 19. Backend N+1 remediation

Replace `AuthorizedCaseRecord(automation, case)` with a strict immutable
`CasePortfolioRecord` containing only the summary fields required by list and Dashboard.
Define a `CasePortfolioRepository` port:

```text
list_authorized(scope, status, priority_filter) -> list[CasePortfolioRecord]
```

`CaseAccessPolicy` converts the authenticated actor into a typed repository scope:
Director/global or exact team. `CaseQueryService` supplies that server-authored scope,
applies the accepted final priority/tie ordering, and remains the priority mutation owner.
The repository never accepts arbitrary client team IDs.

- Memory adapter joins its in-memory automation/case repositories and returns defensive
  strict summary models. Memory calls are process-local and behaviorally identical.
- Mongo adapter makes one filtered projection query against the envelope collection and
  validates each projected result. It must not call `MongoCaseStore.list()` or
  `MongoCaseStore.get()` per record.
- Dashboard consumes `CasePortfolioRecord` and preserves all current counts, scope,
  limits, 30-day UTC trend, and top-active ordering.
- Delete/list races are safe: a projection either sees the pre-delete record or not; the
  frontend deletion mutation removes that ID and drops Dashboard cache after 204.

Do not keep the old list-plus-get code as a fallback.

## 20. Mongo projection/read-model design

Use a strict read projection, not the durable write DTO. Select only:

- `_id`, `schema_version`, top-level `case_id`, `revision`;
- onboarding `case_id`, `team_id`, `priority`, `requested_uen`;
- onboarding entity legal name;
- jurisdiction resolution's resolved jurisdiction;
- onboarding Mock GoldTier result party ID;
- automation `case_id`, status, current stage, created/updated/completed timestamps,
  exception statuses needed for active count, and metrics human-intervention/final-outcome
  fields.

The projection decoder must:

- require canonical `_id` and equality with top-level/onboarding/automation case IDs;
- require exact integer schema discriminator (`type(value) is int`);
- support exact v1 projection only as Director-visible null team/null priority, matching
  current migration behavior;
- reject unknown schema, malformed required values, invalid enum/priority/timestamps,
  and impossible bindings with existing sanitized persistence errors;
- never infer missing automation; cases without automation remain absent from this
  zero-touch portfolio as today.

`MongoCaseStore.initialize()` continues its strict full-envelope validation/recovery.
Detail reads and every write continue to decode the full durable schema. The projection
is a read-path optimization only; it neither replaces nor weakens the write model.

Push backend-authored team/status/priority match predicates into Mongo where supplied.
Perform the accepted final null-last priority/timestamp/case-ID ordering in
`CaseQueryService` so memory and Mongo share one exact comparator and no computed Mongo
sort contract is introduced before pagination.

## 21. Index recommendations tied to query shapes

Current indexes were verified as:

- unique `case_id`;
- `automation.status + top-level updated_at`;
- target submission ID;
- document ID.

Phase 14 recommendation:

1. Keep unique case ID: it supports point read and compare-and-delete identity.
2. Keep the existing automation-status index for status predicate support; do not claim
   its top-level timestamp is the accepted automation ordering key.
3. Add one `onboarding.team_id` ascending index because every team actor's list/dashboard
   query has an exact backend-authored team predicate. Director's unfiltered portfolio
   must scan authorized summary records by definition.
4. Permit Mongo to intersect team/status/priority predicates where useful, but do not add
   a speculative compound-index family in Phase 14.
5. Do not add an `automation.updated_at` sort or priority-order index while ordering is
   intentionally performed over the projected authorized set and pagination is deferred.

Before adding any further index, use isolated Phase 14 Mongo data and `explain` to record
the actual query shape and benefit. Never run index experiments against shared `clm_poc`.
This gives one directly justified new index and avoids index proliferation.

## 22. Pagination decision

**DEFER.**

Cursor pagination would change the list response contract, frontend controls/cache keys,
priority/null ordering token, AuditTrail discovery, Onboarded behavior, and Dashboard's
need for complete authorized totals. Introducing it before measuring the projection and
cache improvements would broaden Phase 14 and risks making Dashboard reflect only a page.

The Phase 14 read port must nevertheless remain pagination-ready: keep one stable
comparator `(priority-present, priority direction, automation.updated_at, case_id)` and
do not bake UI page state into the durable model. A later measured phase may add an opaque
cursor and a dedicated Mongo Dashboard aggregation while keeping totals global.

## 23. Additional optimisations accepted into Phase 14

- Fire-and-forget prefetch of Dashboard and the default unfiltered Case Queue after
  authenticated session establishment; it must not delay login. Dashboard's own mount
  shares the same in-flight request.
- Preserve Case Queue status, priority sort/filter, jurisdiction, and search state when
  opening detail and returning, by lifting the small presentation state to the queue
  route owner in `App.tsx`; it remains memory-only and resets on logout/app reload.
- Keep cached content visible with a subtle `Refreshing…` state rather than replacing it
  with a blank loader.
- Pass AbortSignal through Dashboard/list/detail/document/ownership GETs so obsolete
  filter/case requests can be canceled and old-key responses cannot overwrite the new
  view.
- After confirmed 204 only, remove the deleted case locally from all list caches and
  remove its detail/Dashboard caches.
- Replace priority's list-plus-N refresh with one authoritative active-list refetch.

## 24. Additional optimisations explicitly deferred

- Server-side/cursor pagination and separate Dashboard aggregation.
- AuditTrail all-cases event endpoint and its confirmed first-load `1 + N`.
- Consolidating three Case/Client Detail HTTP resources or the summary's internal Mongo
  reads; measure after list/cache work.
- Optimistic deletion before server 204, undo/recycle bin, or bulk deletion.
- Client-owned priority sorting or broad optimistic Dashboard arithmetic.
- HTTP/CDN caching of authenticated case data.
- Redux, router replacement, component-library redesign, virtualized tables, compression,
  schema rewrite, or external cache/session service.

## 25. Expected files/modules to change

Exact names may be narrowed during execution, but new ownership must follow this map and
must not move logic into unrelated hotspots.

### Backend domain/services

- Create `apps/backend/app/domain/case_management.py`: strict portfolio record/scope.
- Create `apps/backend/app/services/case_portfolio_repository.py`: read port plus memory
  adapter, or place the port in `case_query.py` if it remains compact.
- Create `apps/backend/app/services/case_deletion.py`: deletion role policy/application
  service and safe typed errors.
- Modify `apps/backend/app/services/authorization.py`: actor-to-portfolio-scope helper;
  retain the existing case-access decision.
- Modify `apps/backend/app/services/case_query.py`: consume portfolio summaries; preserve
  exact filter/order and priority mutation.
- Modify `apps/backend/app/services/dashboard.py`: consume summary fields.
- Modify `apps/backend/app/services/onboarding.py` and
  `apps/backend/app/services/repository.py`: explicit create/update semantics and creation
  lock participation.
- Modify the focused repository protocols/implementations for memory deletion:
  `document_repository.py`, `ownership_repository.py`, `reconciliation_repository.py`,
  `clm_repository.py`, `zero_touch_repository.py`, and
  `target_execution_repository.py`.
- Modify `apps/backend/app/services/zero_touch_provider_bindings.py` and
  `apps/backend/app/demo/zero_touch_control.py` only for bounded per-case release/delete.

### Backend persistence/API/composition

- Modify `apps/backend/app/persistence/mongo_case_store.py`: projected list and
  revision-aware physical delete; one team index.
- Modify `apps/backend/app/persistence/repositories.py`: Mongo portfolio/deletion adapters
  and update-only onboarding save.
- Modify `apps/backend/app/persistence/composition.py`: expose portfolio/deletion adapters
  through the bundle.
- Modify `apps/backend/app/api_models.py`: additive list-summary scalar fields only.
- Modify `apps/backend/app/api_auth.py`: exact DELETE route policy; retain all security
  behavior.
- Modify `apps/backend/app/main.py`: compose services, wire DELETE 204, use portfolio
  responses; no inline Mongo logic.
- No `apps/backend/app/persistence/models.py` schema change is expected.

### Backend tests/tooling

- Create `apps/backend/tests/test_phase14_case_management_performance.py` for API, RBAC,
  memory delete, summary projection, query counts, and concurrency doubles.
- Create `apps/backend/tests/test_phase14_real_mongo.py` for physical absence, restart,
  unrelated-case safety, CAS/resurrection, projection, and index evidence.
- Modify `apps/backend/tests/test_phase13_auth_rbac.py` for the exact route inventory and
  delete non-disclosure/CSRF adversarial coverage.
- Modify `apps/backend/tests/test_phase13_dashboard.py` and
  `apps/backend/tests/test_phase13_priority.py` only where the new summary repository or
  reduced refetch path changes fixtures.
- Modify `apps/backend/tests/test_phase13_mongo_test_safety.py` and
  `scripts/mongo_test_safety.py` to add exact `p14` generated-name support while still
  rejecting `clm_poc` and arbitrary names.
- Modify `.github/workflows/ci.yml` only if the new physical Phase 14 file is not selected
  by the current Mongo job; preserve every existing job.

### Frontend

- Create `apps/frontend/src/queryClient.tsx`: QueryClient ownership/defaults/session reset
  and provider.
- Create `apps/frontend/src/caseQueries.ts`: stable keys, query options, cache mutation
  effects, prefetch, and removal helpers.
- Create `apps/frontend/src/pages/DeleteCaseDialog.tsx`: accessible confirmation UI.
- Modify `apps/frontend/src/api.ts`: AbortSignal on GETs and no-body DELETE client.
- Modify `apps/frontend/src/auth.tsx` and `apps/frontend/src/main.tsx`: cache lifetime tied
  to auth lifecycle and non-blocking prefetch.
- Modify `apps/frontend/src/types.ts` and `apps/frontend/src/viewModels.ts`: additive list
  fields and detail-free row mapping.
- Modify `apps/frontend/src/pages/Dashboard.tsx`, `CaseQueue.tsx`,
  `OnboardedClients.tsx`, `CaseDetail.tsx`, `ClientDetail.tsx`, and
  `PriorityControl.tsx`: queries, refreshing states, deletion controls, and bounded
  invalidation.
- Modify `apps/frontend/src/App.tsx`: pass actor/deletion navigation, retain queue filter
  state, and connect existing mutations to cache effects; keep changes surgical.
- Modify `apps/frontend/src/automationPolling.ts` only to publish latest detail data into
  the query cache/consume cancellation without changing polling business rules.
- Modify `apps/frontend/src/design-system.css` only for destructive dialog details.
- Create `apps/frontend/src/Phase14CaseManagementPerformance.test.tsx`; update Phase 13
  Dashboard/priority tests only for additive list fields and reduced request counts.
- Modify `apps/frontend/package.json` and `apps/frontend/package-lock.json` via
  `npm.cmd install --save-exact`; no manual lockfile edits.

### Documentation after implementation

- Update `docs/PROJECT_CONTEXT.md`, Phase 14 architecture/API/security/performance docs,
  decision log, and configuration/dependency reference only where implementation truth
  requires it. Record the deletion policy as project-defined provisional POC behavior.
- Create one Phase 14 execution report through the assigned implementation workflow.
- Do not edit sponsor contract artefacts or claim sponsor approval.

## 26. Ordered implementation slices

### Slice 1 — Lightweight read/query foundation

**Why first:** It is read-only behavior, removes both expected N+1 paths, and provides
the enriched list contract required by later cache/deletion UI without destructive state.

1. Add the strict portfolio scope/record and repository port.
2. Add memory and Mongo projection adapters with strict identity/schema validation.
3. Rewire `CaseQueryService`, list response, and Dashboard to summaries.
4. Add jurisdiction/created/completed/Mock-party list fields.
5. Remove Case Queue/Onboarded per-row detail calls and update mappings.
6. Add deterministic frontend HTTP-count and backend Mongo-query-count tests.
7. Add only the team index after isolated query-shape evidence.
8. Run focused Phase 13 list/priority/Dashboard/Mongo regression.

Stop if projection cannot preserve v1 legacy visibility, strict malformed-data behavior,
or exact ordering without restoring a full-envelope fallback.

### Slice 2 — Session cache and navigation optimisation

1. Install exact-pinned TanStack Query and jsdom through npm.
2. Add query client/provider, keys, 45-second defaults, AbortSignal propagation, and
   fresh/stale/empty rendering.
3. Tie cancel/clear to logout, 401, successful login, and identity change.
4. Migrate Dashboard, Cases, Onboarded, Case Detail, and Client Detail reads.
5. Add fire-and-forget Dashboard/default-queue prefetch.
6. Preserve Case Queue presentation filters across detail navigation.
7. Add cache freshness, deduplication, cancellation, manual-refresh, and cross-user tests.

Stop if any query data survives an identity transition or any storage persistence API is
introduced.

### Slice 3 — Resurrection-safe hard-delete backend

1. Split onboarding repository `create` from update-only `save`; update creation flow.
2. Add deletion port/adapters and per-case cleanup methods.
3. Add deletion application service with inside-lock re-read, access, and role policy.
4. Add Mongo revision-aware physical delete and memory parity cleanup.
5. Add provider-binding/demo transient cleanup without connector rollback.
6. Add exact route inventory, DELETE 204, safe 403/404/409/503 mapping.
7. Add role, CSRF, hard-delete, any-status, and stale-write/concurrency tests.
8. Extend the Mongo safety helper to exact Phase 14 ephemeral names.

Stop rather than status-restrict if a mutation owner is found that cannot join the
canonical lock/create-update boundary within this bounded slice.

### Slice 4 — Confirmation modal and cache-consistent deletion UX

1. Add no-body DELETE transport and mutation option.
2. Add accessible dialog with explicit identifiers/warning, focus/keyboard behavior,
   in-flight guard, and bounded error state.
3. Add role-gated controls to Case Queue and Case Detail.
4. On 204, remove the ID from lists, remove detail/supporting queries and Dashboard,
   then navigate safely from detail.
5. Prove Cancel/no-open mutation, exactly-one confirm, failure retention, success removal,
   direct reopen 404, and Client Onboarder no-control behavior.

### Slice 5 — Bounded cache mutation integration and performance closure

1. Route create/priority/document/reconciliation/resume/exception/poll updates through
   the invalidation matrix.
2. Ensure priority reload is one list request with no per-row detail requests.
3. Verify stale content remains visible during one background refresh.
4. Capture deterministic current/proposed HTTP and Mongo query counts.
5. Confirm no pagination/Audit/detail-consolidation scope leaked in.

### Slice 6 — Broad regression, latest-main integration, and independent gates

1. Run focused backend/frontend/security/physical Mongo checks.
2. Run full backend, Ruff/check-format, mypy, pip check, frontend dependency/type/test/
   build, contracts, lifecycle, and security units/scanner under the repository's safe
   rules.
3. Fetch `origin/main`; if advanced, obtain authorization and merge into the feature
   branch—never rebase—then rerun affected and broad checks.
4. Commit only reviewed scoped paths when authorized; run clean-tree pre-PR check.
5. Run independent Phase 14 quality gate plus integration-security and POC regressions.

This order deliberately places destructive behavior after the read/cache foundations
are independently verifiable, but before final mutation integration, so the cache UX is
built against a stable DELETE contract.

## 27. Detailed test matrix

### 27.1 DELETE RBAC and non-disclosure

- Director deletes Team A, Team B, and legacy/null cases: `204`.
- Director absent ID: fixed `404`.
- RM own-team: `204`; other-team/legacy/absent: identical fixed `404`.
- Client Onboarder own-team: fixed `403 CASE_DELETE_FORBIDDEN`.
- Client Onboarder other-team/absent: identical fixed `404`, never the role 403.
- Unauthenticated existing and absent IDs: fixed `401` before case lookup.
- Caller-supplied role/team headers, query fields, and bodies do not affect any result.
- Delete every canonical automation status using controlled fixtures; no status is denied.
- Repeated DELETE after 204: fixed `404`.

### 27.2 DELETE security

- Missing/wrong CSRF: existing fixed 403; no deletion.
- Trusted single Origin/Referer plus valid CSRF: normal role behavior.
- Foreign, malformed, duplicate, mixed-case duplicate, or fragment-invalid browser-source
  headers preserve Phase 13 failure and perform no deletion.
- Logout/relogin/session rotation/expiry behavior is unchanged.
- Route inventory exact equality includes the DELETE and no accidental public route.
- Errors/log capture contains no case evidence, URI, credential, cookie, session, CSRF,
  or internal persistence detail.

### 27.3 Hard delete — memory

- Build a case with canonical Registry data, multiple documents/events, ownership,
  reconciliation, CLM, automation, target ledger, and demo scenario.
- After delete, onboarding/detail/list/Dashboard/document/ownership/reconciliation/CLM/
  automation/target/demo lookups are absent.
- Recovery-fault counter and unique provider binding are no longer retained.
- An unrelated complete case remains byte/model-equivalent and visible.
- No external connector method is called by delete.

### 27.4 Hard delete — isolated physical Mongo only

- Generate only `clm_p14_<24 hex>` via the strict helper; reject `clm_poc`, p12/p13
  mismatches, arbitrary names, suffixes, and traversal shapes.
- Persist a complete case envelope plus unrelated case.
- DELETE 204; direct raw lookup by deleted `_id` returns absent; collection count drops
  by exactly one; unrelated raw envelope/revision is unchanged.
- Recompose/restart application; deleted detail is 404 and list/Dashboard omit it.
- Assert the single envelope was the only case-owned durable record and no child
  collection/document keyed by the case exists.
- Cleanup retries, verifies database absence, and redacts driver details.
- Never create/update/delete shared `clm_poc`.

### 27.5 Deletion concurrency/resurrection

- Pause an established workflow mutation while it holds the canonical case lock; start
  deletion; prove delete cannot pass the mutation, then release and prove final absence.
- Pause deletion after authorized snapshot; introduce a revision change through an
  isolated second store/process; prove compare-and-delete fails 409 without partial
  deletion.
- After successful deletion, attempt a stale onboarding `save` in memory and Mongo;
  prove missing/conflict and physical absence.
- Prove explicit `create` succeeds once and duplicate create fails; update of missing case
  never inserts.
- Race two authorized DELETE calls: at most one 204, the other safe 404/409; final absence.
- Cover RUNNING, WAITING_FOR_REVIEW, COMPLETED, RECOVERY_PENDING, TECHNICAL_FAILURE, and
  pending input fixtures without status restrictions.

### 27.6 Frontend confirmation/accessibility

- Director/RM authorized list/detail renders Delete; Client Onboarder does not.
- Opening dialog, Cancel, backdrop-safe close, and Escape cause zero DELETE.
- Dialog label/description include legal name fallback and UEN plus irreversible warning.
- Initial focus, focus containment, Escape, and trigger-focus restoration pass in jsdom
  plus a manual real-browser check.
- Confirm makes exactly one DELETE under double click/Enter/rerender and disables actions.
- Failure keeps row/detail/dialog, renders bounded error, and performs no cache removal.
- Success removes row, clears case/Dashboard caches, closes dialog, and detail navigates
  back safely.

### 27.7 Cache freshness, deduplication, cancellation, isolation

- No cache: one network request and loading state.
- Fresh second mount/navigation inside 45 seconds: immediate data, zero new request.
- Stale cache at 45 seconds: immediate old data plus exactly one background request;
  content never blanks and `Refreshing…` is bounded.
- Manual Refresh inside fresh window: one real request.
- Two concurrent observers/same key: one underlying request.
- Filter/key change aborts obsolete request where practical; old-key response never
  overwrites current view.
- Logout, 401 from foreground/background request, same-user new login, and user-ID change
  cancel/clear all query and mutation state.
- Team A marker -> logout -> Team B: no Team A Dashboard/list/detail data is rendered or
  returned from cache.
- Stub localStorage/sessionStorage/IndexedDB and prove cache never reads/writes them.
- New QueryClient/page reload starts empty.
- Prefetch is fire-and-forget and does not delay login state; default Dashboard observer
  shares the in-flight prefetch.

### 27.8 Cache mutation invalidation

- Create removes/invalidate list and Dashboard; returned detail can seed exact case key.
- Delete removes ID from every filter/sort list and all case resource keys; Dashboard is
  removed.
- Priority mutation refetches one active list only, drops potentially stale inactive
  variants and Dashboard, and never loads all details.
- Document/reconciliation/resume/exception mutations refresh affected detail/supporting
  resources and list/Dashboard only when summary fields may change.
- Polling publishes the latest detail without reintroducing duplicate requests.

### 27.9 HTTP/query-count and projection

- N Case Queue rows: exactly one list HTTP call, zero detail calls.
- N Onboarded rows: exactly one completed-list HTTP call, zero detail calls.
- Opening one row: detail resources start only then.
- Mongo case list and Dashboard input: exactly one projection `find`/aggregate call and
  zero per-case `get`/`find_one` calls.
- Projection excludes documents, document events, ownership graph, reconciliation body,
  CLM body, automation timeline, and target ledger.
- All list/Dashboard required scalar fields map correctly in v2 and Director-visible v1.
- Malformed projection/schema/identity/priority/status fails closed; detail/write strict
  envelope tests remain green.
- Provider counters remain zero for list/Dashboard/detail reads as Phase 13 requires.

### 27.10 Broad regression commands

Run focused selections first from `apps/backend`:

```powershell
python -m pytest tests/test_phase14_case_management_performance.py tests/test_phase13_auth_rbac.py tests/test_phase13_priority.py tests/test_phase13_dashboard.py -p no:cacheprovider
python -m pytest tests/test_phase12_persistence.py tests/test_phase13_mongo_test_safety.py -p no:cacheprovider
```

Run physical Mongo only through explicit `PHASE12_MONGO_URI` CI/approved isolated test
configuration; the test itself generates the p14 database:

```powershell
python -m pytest tests/test_phase12_real_mongo.py tests/test_phase13_real_mongo.py tests/test_phase14_real_mongo.py -p no:cacheprovider --tb=no
```

Run broad backend checks from `apps/backend`:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy app
python -m pip check
```

Run frontend checks from `apps/frontend`:

```powershell
npm.cmd ls --all
npm.cmd run typecheck
npm.cmd test -- --run
npm.cmd run build
```

Run repository-root checks with the environment/test-isolation conventions from CI and
accepted Phase 13 reports:

```powershell
python -m unittest discover -s tests/contract -p "test_*.py"
python -m unittest discover -s tests -p "test_phase_07_delivery_assets.py"
python -m unittest discover -s tests -p "test_demo_lifecycle_windows.py" -v
python -m unittest discover -s tests -p "test_check_secrets.py"
python -m unittest discover -s tests -p "test_pre_pr_check.py"
python scripts/check_secrets.py
python scripts/validate_goldtier_examples.py --if-present
```

Do not run the broad secret scanner if doing so would inspect protected unrelated
untracked artifacts; use the repository's task-owned tracked-path safe procedure and
report the limitation. Run `python scripts/pre_pr_check.py` only after authorized commits,
latest-main integration, and a genuinely clean tree.

## 28. Deterministic performance acceptance criteria

| Area | Current verified behavior | Phase 14 target |
|---|---|---|
| Case Queue HTTP | `1 + N` list/detail | `1` bounded list request; `0` details |
| Onboarded HTTP | `1 + N` list/detail | `1` completed-list request; `0` details |
| Case Detail HTTP | 3 detailed resources on open | only on open; cached/deduped on repeat |
| Dashboard Mongo | `1 + N` complete-envelope reads | 1 authorized projection query |
| Case list Mongo | `1 + N` complete-envelope reads | 1 authorized projection query |
| Repeat fresh navigation | blocking remount request | immediate cache; no network |
| Repeat stale navigation | blocking request/blank | immediate cache + at most 1 refresh |
| Concurrent same key | duplicate possible | 1 underlying request |
| Priority mutation refresh | list + N details | 1 active list refresh; 0 row details |
| Delete cache result | not available | no deleted ID/detail/Dashboard cache |

Record call/query counts in tests. Optionally record payload byte size before/after as
diagnostic evidence, but do not set a fragile millisecond SLO or make network timing a
gate.

## 29. Security/RBAC invariants

- Authentication and identity remain server-owned; no request authority field exists.
- DELETE is unsafe and retains exact Origin/Referer plus session CSRF enforcement.
- Case existence is checked before role-specific denial, preserving cross-team 404.
- Authorization is rechecked inside the deletion lock; middleware alone is not the
  destructive authority.
- Query scopes come only from the authenticated actor/access policy and are applied
  before projection/aggregation.
- Cache contains only authenticated server responses, is keyed by user, and is cleared
  before identity/session transitions render.
- No cache, log, error, test output, or documentation exposes credentials, session/CSRF
  values, Mongo URI/host, raw provider data, or KYC/PII.
- Existing host-only HttpOnly strict-same-site cookie, production Secure behavior,
  duplicate browser-source rejection, route inventory, and fixed errors remain unchanged.
- No external connector is called on hard delete; no external rollback is claimed.

## 30. Data safety / isolated Mongo test policy

- Shared `clm_poc` is read-only and should not be connected to during implementation
  tests unless a separately authorized direct read-only count is required by a gate.
- Phase 14 physical tests require `PHASE12_MONGO_URI` as the existing explicit connection
  opt-in but generate only an internally owned `clm_p14_<24 lowercase hex>` database.
- Extend the current exact allowlist rather than create a parallel cleanup helper.
- Every physical test uses `_env_file=None`, explicit Mongo mode/database/collection, and
  `try/finally` cleanup with absence verification/redacted failure.
- Ordinary tests continue to force memory mode before app imports and reject persistence
  overrides, even when the parent environment names Mongo and `clm_poc`.
- Do not open `.env`; do not print or interpolate URI/credentials; use only settings/CI
  injection.
- Before/after physical assertions target only the generated database and exact case ID.
- If cleanup fails, report the generated database name and safe exception class only;
  stop rather than touching broader databases.

## 31. Sponsor/provisional assumptions

- The deletion role policy is **PROJECT-DEFINED POC BEHAVIOR PENDING SPONSOR
  CONFIRMATION**. No Delta Capita production deletion/retention authority was supplied.
- Hard delete applies only to this CLM application's stored case envelope/process memory.
  It does not undo or instruct ACRA, GoldTier, or a future external system.
- Current GoldTier execution is Mock-only. Removing its retained application evidence does
  not claim that a simulated or future external party/policy was removed.
- Case priority remains ordering metadata only; deletion adds no approval, SLA, risk,
  escalation, or notification meaning.
- Live ACRA, live GoldTier/PingFed, final UBO/business policy, and Ready-for-Approval/
  four-eye remain outside Phase 14.
- Memory cache TTL is a technical responsiveness choice, not sponsor retention policy.

## 32. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Stale mutation recreates deleted envelope | explicit insert-only create/update-only save + case lock + Mongo CAS |
| Partial memory cleanup | one composed adapter under canonical lock; exhaustive repository absence test |
| Cross-process delete/write race | revision compare-and-delete; update-only missing failure; bounded 409 |
| Cross-team existence leak | existing CASE_SCOPED middleware first; inside-lock policy; adverse matrix |
| Client role spoof | no request authority inputs; server actor only |
| Cached prior-user data | per-user keys plus cancel/clear before auth transition; no persistence |
| Deleted case flashes from stale Dashboard | remove Dashboard query after 204 instead of invalidating in place |
| Cache invalidation drift | one centralized key/effects module and mutation matrix tests |
| Projection accepts corrupt data | strict projection DTO/identity/schema validation; full writes/details/startup remain strict |
| Frontend dependency/lock conflict | exact npm install, reviewed manifest/lockfile, `npm ls`, no manual lock edits |
| Hotspot merge conflict | focused owner files; minimal wiring in `main.py`, `App.tsx`, `api.ts`, types |
| Unbounded growth still hurts | pagination explicitly deferred with stable comparator and measured follow-up trigger |
| Delete request waits on long mutation | current Mock/synchronous POC boundary; wait safely rather than status-restrict or race |
| Physical test harms shared data | exact p14 generated database guard, explicit opt-in, cleanup verification |

## 33. Quality-gate checklist

- [ ] Baseline and latest `origin/main` SHAs recorded; feature branch is not `main`.
- [ ] Only intended/supporting files changed; no protected artifacts or `.env` accessed.
- [ ] DELETE route inventory, 204 contract, fixed errors, CSRF, and complete role matrix pass.
- [ ] Memory and isolated Mongo hard-delete/restart/orphan proofs pass.
- [ ] Stale/in-flight persistence cannot resurrect a deleted case in deterministic tests.
- [ ] Any-status deletion is demonstrated; no quiet terminal-only restriction exists.
- [ ] Case Queue and Onboarded HTTP count is exactly one list request for N rows.
- [ ] Mongo list and Dashboard query count is exactly one projection query, zero per-case
  gets, with heavy fields excluded.
- [ ] Dashboard definitions, scope, trends, priority ordering, and provider-free reads pass.
- [ ] Fresh/stale/no-cache/manual-refresh/dedup/cancel/error behavior passes.
- [ ] Logout/401/new-login/user-A-to-user-B cache isolation passes.
- [ ] No localStorage/sessionStorage/IndexedDB cache use exists.
- [ ] Confirmation semantics, exactly-once submit, error retention, success navigation,
  keyboard/focus, and role-hidden controls pass.
- [ ] Existing Phase 13 auth/RBAC/browser-source/priority/test-isolation/Mongo safety tests
  pass.
- [ ] Full backend, Ruff, Ruff format check, mypy, pip check, frontend dependency tree,
  typecheck, tests, build, contracts, lifecycle, and security checks pass.
- [ ] Physical Mongo tests use only generated p14 database and clean it successfully.
- [ ] No secrets/confidential raw artefacts are newly tracked or printed.
- [ ] API/list type, dependency, persistence lifecycle, RBAC policy, indexes, and
  provisional business policy are explicitly documented in the execution report.
- [ ] `git diff --check` passes; no unresolved paths.
- [ ] After authorized commit/integration, `python scripts/pre_pr_check.py` passes on a
  clean latest-main-containing branch.
- [ ] Independent `fyp-quality-gate`, `integration-security-review`, and
  `poc-regression-check` evidence is complete before PR-ready language.

## 34. Integration/rollback considerations

Integration hotspots are `main.py`, `api_auth.py`, `api_models.py`, persistence
composition/store/adapters, frontend `App.tsx`/`auth.tsx`/`api.ts`/`types.ts`, CI, and
package lock. Preserve newer main's route inventory/security/test-isolation behavior and
reapply the smallest Phase 14 delta if conflicts occur. Never choose a whole-file side.

The feature is internally slice-revertible:

- Query projection/list fields can revert together to the old read path only before
  release; do not ship dual paths or runtime fallbacks.
- Query-cache/frontend dependency/provider/pages must revert as one unit; removing only
  lifecycle clearing would be unsafe.
- Delete API, deletion service/adapters, and explicit create/update semantics are one
  security/persistence unit. Do not retain the DELETE while reverting resurrection
  protection.
- The additive team index can remain harmlessly if code rollback occurs; owner-approved
  index removal is an operational action, not an automatic rollback step.
- No schema migration or browser cache migration is required. Memory cache disappears on
  reload; durable envelope stays schema v2.

Before PR readiness, fetch origin. If `origin/main` advanced from the recorded baseline,
merge it into the feature branch only when authorized, rerun focused then broad checks,
commit reviewed resolution, and run the clean-tree checker. Do not rebase, force-push,
or merge the PR.

ADR signal: explicit create/update lifecycle plus compare-and-delete and the session-only
cache boundary are durable architecture decisions. At completion, evaluate whether to
record them in the existing decision log/architecture docs; do not create a duplicate
source of truth during implementation.

## 35. Exact execution handoff for the implementation agent

1. Read `AGENTS.md`, `docs/PROJECT_CONTEXT.md`, this planner, integration-safe guidance,
   Phase 13 architecture/final reports, current CI, and the relevant source/tests before
   writing.
2. Verify branch, HEAD, `origin/main`, merge base, and tracked-only status. Record
   `BASE_SHA=aba264af3b4088a9a10fe682ee6fc0cb418d550d`. Stop on material drift or unexpected
   tracked changes; do not inspect protected untracked artifacts.
3. Record a `TaskStartSnapshot`, scope map, hotspot list, and strict non-goals. Do not
   create another planner or start unrelated refactors.
4. Execute Slices 1–5 in order. After each slice, run its focused tests and inspect the
   exact diff. Do not commit a slice unless explicitly authorized.
5. In Slice 1, delete the old HTTP and Mongo N+1 owners when the projection path passes;
   do not keep feature flags/fallbacks.
6. In Slice 2, install dependencies only with npm in `apps/frontend`; review both manifest
   and generated lockfile. Never add browser persistence.
7. In Slice 3, do not expose DELETE until explicit create/update semantics, case-lock
   serialization, memory cleanup, Mongo CAS, and adverse tests are present together.
8. If any established-case mutation bypasses the canonical lock and cannot be bounded,
   stop and request owner direction. Do not restrict deletable statuses as a workaround.
9. Run physical deletion tests only against generated p14 databases through the extended
   Phase 13 safety owner. Shared `clm_poc` remains read-only and untouched.
10. Execute the complete section 27 checks, documenting exact pass/fail/skip counts and
    any environmental limitation. Do not describe a skipped physical test as passing.
11. Update only implementation-impacted docs and record that delete policy is provisional
    POC behavior and external systems are unaffected.
12. Fetch origin for final drift. Merge latest main only with explicit authorization;
    never rebase. Rerun checks after conflict resolution.
13. Run `python scripts/pre_pr_check.py` only after authorized commits and a clean tree.
    Request independent Phase 14 quality, integration-security, and POC regression gates.
14. Final report must list files, API/type/persistence/index/dependency/security changes,
    exact tests/results, HTTP/query counts, physical Mongo data-safety receipt, assumptions,
    blockers/risks, main drift, and recommended next step. Do not merge to main.

### Execution Readiness View

- Intent Lock: permanent authorized case deletion plus bounded list/dashboard/navigation
  performance, with no Phase 15 or external-system work.
- Scope Fence: the files/slices/non-goals in sections 6, 24–26.
- Baseline Lock: Phase 13 final accepted commit
  `aba264af3b4088a9a10fe682ee6fc0cb418d550d` and latest `origin/main` at execution start.
- Approved Behavior: exact deletion matrix, 204 contract, any-status safety, one-request
  list, one-query projection, 45-second session-memory cache.
- Owner/Contract Constraints: access policy owns visibility; deletion service owns role;
  case lock/CAS owns concurrency; repository owns persistence; backend owns truth; query
  client owns browser cache mechanics.
- Compatibility Boundary: Phase 13 auth/RBAC/CSRF/order/Dashboard/schema/test safety and
  accepted POC workflow remain intact.
- Retirement Boundary: remove list/detail and Mongo list/get N+1 paths; no compatibility
  fallback, tombstone, or parallel cache owner.
- Task Batches: six slices in section 26.
- Test Obligations: section 27 plus quality checklist section 33.
- Review Gates: focused review per slice, broad CI-equivalent verification, physical
  Mongo proof, independent quality/security/POC gates.
- Drift/Rewind Rules: stop on material baseline/unexpected-file/contract conflict; revert
  coherent units only; never weaken security or status-restrict deletion to hide a race.
- Evidence Required Before Completion: exact HTTP/query counts, RBAC/security matrix,
  physical absence/restart, resurrection tests, cache isolation, broad checks, latest-main
  evidence, and data-safety receipt.
- Advisory Boundary: method-pack execution guidance only; not a GateDecision,
  PolicySnapshot, or completion authority.

### Planner readiness decision

**READY FOR PHASE 14 IMPLEMENTATION, NOT IMPLEMENTED.** The owner requirements are
sufficient for the project-defined POC. Execution should be inline on the assigned branch
using the ordered slices and should stop at any unresolved lock/resurrection, data-safety,
scope, or latest-main boundary. This planner does not authorize staging, committing,
pushing, merging, rebasing, resetting, cleaning, branch switching, or shared Mongo writes.
