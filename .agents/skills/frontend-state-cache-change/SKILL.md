---
name: frontend-state-cache-change
description: "Use when changing React Query keys, authenticated cache scope, prefetching, stale times, cancellation, invalidation, mutation effects/retries, logout/401 cleanup, or deleted-case stale-response behavior."
---

# Frontend State and Cache Change

## Trigger

Use for shared server-state/cache lifecycle changes. A purely local visual state change
uses `FRONTEND_UI` instead, unless it affects server results or authorization scope.

## Purpose

Improve frontend state behavior without cross-user/team leakage, duplicate mutations,
stale-response publication, deletion resurrection, or browser-side authorization.

## Inputs

- changed query/mutation and user-visible goal;
- current key factories, AuthProvider/session lifecycle and API AbortSignal support;
- all consumers, filters/team scope, mutation effects and deletion behavior;
- backend contract/authorization and measurable performance baseline when optimization.

## Mandatory context

Read constitution/state/architecture/workflow, `auth.tsx`, `queryClient.tsx`,
`caseQueries.ts`, affected pages/API/types/tests, backend access/filter contract, and
`architecture-change-review` if adding/replacing a state owner/library.

## Preconditions

- Backend remains the authorization owner.
- Every input that changes server results is identified.
- Session transition, 401 and deletion flows are mapped before key/effect changes.
- Performance work has a deterministic call/request/render measurement.

## Analysis steps

1. Inventory query key -> query function -> consumers -> server scope. Keys must begin
   with authenticated user identity and include case ID, status, sort, priority and
   Director team filter wherever they affect results.
2. Trace login restoration, successful login, identity/session replacement, logout and
   401. Cancel active requests and clear all incompatible cached business data before a
   different/anonymous UI can consume it.
3. Pass AbortSignal through every affected GET and prove cancellation prevents a late
   old-session response from publishing.
4. Define invalidation/removal by mutation. Update only data supported by the response;
   refetch/remove all server-derived lists/dashboard/resources whose ordering/counts
   may change.
5. For deletion, cancel the user's list/dashboard/exact case resources, await server
   success, remove the case from cached lists, remove exact resources/dashboard, and
   prove stale responses cannot resurrect it. Failed deletion retains authoritative data.
6. Keep mutation retry disabled by default. Enable only operation-specific bounded retry
   with backend idempotency, duplicate-effect, authorization and call-count proof.
7. Review optimistic updates/rollback, stale-time/prefetch behavior, inactive queries,
   team switching and empty/error states. Frontend capability visibility never grants access.
8. Measure the intended benefit without persisting case data in localStorage,
   sessionStorage, IndexedDB, service workers or shared HTTP caches.
9. Run focused adverse tests, full frontend suite/typecheck/build, affected backend/API
   contracts, governance checks, security review where data scope changes, and QG.

`PARTIAL` permits only explicitly enumerated safe slices whose isolation, lifecycle and
performance evidence is complete. It cannot authorize weakened keys, cross-session
cache survival, unproved mutation retry, deleted-data retention, merge/readiness, or
deferral of the adverse tests that protect the shipped slice.

## Allowed changes

- Existing key factories, QueryClient options, auth lifecycle and centralized mutation effects.
- Bounded session-memory prefetch/stale-time/invalidation supported by measurement.
- Focused component/query tests and safe backend projection changes in their own class.

## Forbidden changes

- Removing user/session or Director team/filter scope from cache identity.
- Cache survival across logout, 401, identity/session replacement or successful new login.
- Frontend filtering/visibility as authorization.
- Global retry for non-idempotent mutations or silent duplicate submissions.
- Publishing an aborted/old-session response or retaining deleted case data until refresh.
- Persistent browser storage of case/evidence data without a new authorized security architecture.
- Calling security regression “rare” or trading it for demo smoothness/deadline.

## Stop conditions

Stop when scope inputs/consumers are unknown, backend authorization is being replaced,
session clearing cannot be proved, stale responses can publish, mutation idempotency is
unknown, deletion can resurrect, or performance improvement lacks measurement.

## Required tests

- exact key identity for users, cases, filters and Director team scopes;
- cross-user, team switch, logout/login, session replacement and 401 clearing;
- AbortSignal cancellation and late-response rejection;
- fresh/stale/prefetch/in-flight deduplication behavior where changed;
- mutation success/failure/conflict, invalidation/removal and exact call counts;
- deletion success/failure, all resource removal and no stale resurrection;
- focused and full frontend tests, typecheck and build;
- affected backend/API/contract/security/regression/governance checks and independent QG.

## Required evidence

- before/after key-consumer-scope matrix;
- session lifecycle and cancellation trace;
- mutation/invalidation/call-count matrix;
- deletion/no-resurrection evidence;
- performance result, full frontend commands/results and residual data risk.

## Expected report

```text
FRONTEND STATE/CACHE: PROCEED | PARTIAL | STOP
Queries / consumers:
Key and team isolation:
Session / 401 lifecycle:
Cancellation / stale responses:
Mutations / retries / invalidation:
Deletion / anti-resurrection:
Performance evidence:
Tests / risks:
```

## Handoff format

Give the implementer exact key/effect/auth/API/page files, scope matrix, mutation and
deletion ordering, explicit non-edits and tests. Give QG the session/team/stale-response/
call-count evidence and performance measurement. Provider/cache labels never substitute
for backend authorization or user-data security review.
