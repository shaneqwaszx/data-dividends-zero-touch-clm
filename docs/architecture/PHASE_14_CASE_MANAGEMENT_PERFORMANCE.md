# Phase 14 Case Management and Performance Boundary

## Implemented outcome

Phase 14 replaces historical case-list envelope loading with one authorized portfolio
projection and adds session-memory browser query reuse. Cases and Onboarded each render
N rows from one list HTTP request and no per-row detail requests. Mongo list and
Dashboard input use one projected `find`, with team scope in the database query and no
per-case `find_one`. The projection excludes documents/events, ownership graphs,
reconciliation and CLM bodies, automation timelines, and target execution ledgers.

The additive list response contains only the scalars needed by those views: case/team/
priority identifiers, UEN, legal name, resolved jurisdiction, automation state/stage,
created/updated/completed timestamps, open-exception and human-intervention counts,
deduplicated enum-ordered types from retained `OPEN` business exceptions, final outcome,
and Mock GoldTier party ID. Exception count remains the number of open records rather
than the number of unique types. The Mongo projection selects only each exception's
status and type, and the strict decoder validates every projected entry before deriving
the list. Strict envelope ID, embedded case IDs, schema discriminator, types, enums, and
bounds still fail closed. Mongo initializes the `onboarding_team_lookup` index.
Pagination and a separate Dashboard aggregation remain deferred and must be introduced
only from measured need.

## Session cache

TanStack Query owns a 45-second stale window and a 15-minute garbage-collection bound.
It remains in JavaScript memory only: no localStorage, sessionStorage, IndexedDB, service
worker, or HTTP shared cache stores case data. Query keys begin with the authenticated
user ID. Logout, a 401, successful login, and identity replacement cancel active queries
and clear the complete QueryClient. GET query functions consume AbortSignal.

Dashboard and the default queue are prefetched without delaying authenticated state.
Dashboard, Cases, Onboarded, Case Detail, Client Detail, documents, ownership, and the
execution profile share stable keys. Fresh navigation reuses data; stale data remains
visible during background refresh. Queue status, priority, sorting, jurisdiction,
business-exception type, and search presentation state is retained by the authenticated
workspace while a detail is opened. The optional exact `attention_type` is part of the
same user-scoped case-list query identity and filters the already-authorized projection;
it creates no second queue, persistence owner, or cache policy. Creation, priority,
supporting-evidence mutations, reconciliation, resume, exception resolution, polling,
and deletion use centralized cache effects across all list variants.

After a successful server deletion, the deletion cache effect first awaits cancellation
of that authenticated user's complete case-list family, Dashboard query, and exact
deleted-case resources. Only then does it filter cached lists and remove detail,
supporting-resource, and Dashboard entries. An older AbortSignal-backed request can no
longer publish a pre-deletion list or Dashboard snapshot after the effect completes.

## Permanent deletion

`DELETE /api/clm/zero-touch/cases/{case_id}` has no body and returns `204` with no
content. A Director may delete any accessible case, including a legacy null-team case.
A Relationship Manager may delete a case in their own team. A Client Onboarder who can
access their own-team case receives `403 CASE_DELETE_FORBIDDEN`. Inaccessible and absent
IDs are the same safe `404`; unauthenticated requests are rejected before lookup.
Existing session, CSRF, and exact Origin/Referer rules apply, including duplicate-header
rejection. Caller role/team headers, query parameters, and bodies grant no authority.

The deletion application service enters the canonical case lock, re-reads and checks
case visibility, then applies role policy. It physically removes the complete process-
local aggregate or performs Mongo compare-and-delete against the current envelope
revision. A race maps to `409 CASE_DELETE_CONFLICT`; persistence failure maps to a
sanitized `503 CASE_DELETE_UNAVAILABLE`. Only after physical deletion does it release
case-owned provider binding and demo fault state. It makes no Registry, IDP, Ownership,
or GoldTier call and attempts no external rollback.

Onboarding persistence now has an insert-only `create` and update-only `save`. Initial
zero-touch establishment reserves its case identity before writing, then holds that
case's canonical reentrant lifecycle lock across onboarding creation, initial CLM state,
automation creation, and demo-scenario registration when applicable. DELETE uses the
same lock, so it cannot complete between those writes. If a required establishment write
raises, bounded rollback discards only that case's local aggregate and demo/provider
transients through repository boundaries; it performs no external-system deletion. A
stale established mutation therefore cannot recreate a case after deletion in memory or
Mongo. Deletion is allowed in every workflow/automation status; there is no terminal-only
workaround.

The browser exposes deletion only to Director and Relationship Manager roles returned
by the backend. Queue and detail controls use an alert dialog with identifiers, a
permanence warning, initial Cancel focus, Tab containment, Escape cancellation, focus
restoration, and an in-flight submit guard. UI hiding is presentational only; backend
authorization remains authoritative.

## Authority and non-goals

The role matrix, hard-delete policy, 45-second cache interval, and performance thresholds
are **PROJECT-DEFINED POC BEHAVIOR PENDING SPONSOR CONFIRMATION.** This phase does not
define regulatory retention, production deletion governance, distributed locking,
multi-instance resurrection prevention, external-system erasure, recycle/undo, bulk
deletion, pagination, risk/SLA policy, Ready-for-Approval, or a production identity
model. Shared `clm_poc` data is not a test target and is never modified by the Phase 14
physical gate.
