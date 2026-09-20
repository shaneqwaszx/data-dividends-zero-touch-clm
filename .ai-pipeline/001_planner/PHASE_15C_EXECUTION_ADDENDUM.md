# Phase 15C execution addendum

This addendum preserves and narrows
`PHASE_15C_FRONTEND_NAVIGATION.md`; it does not replace or broaden that plan.

## A. Navigation identity and live-operation identity

The browser URL is the only page and case navigation identity. Existing in-memory
intake refs remain only the owner of one explicitly user-initiated live intake
operation. They may retain its immutable case ID, selected `File` objects, successful
upload keys, failed-document bindings, and progress while this tab remains mounted,
but they do not select a page and may never contradict the route.

## B. Late-response publication boundary

Every intake callback is bound to the immutable operation generation, actor identity,
and created case ID captured for that operation. A late response must not navigate away
from a newer user-selected destination, publish under another case route, repopulate a
freshly reset journey, or update another authenticated session. Case A query responses
remain confined to Case A's user/case-scoped query keys and local presentation.

The narrow exception to the ordinary create-then-replace sequence is a create response
that arrives after the user has left the originating New onboarding destination. The
returned case remains bound to its proper live operation and the already initiated
workflow may continue under existing semantics, but the callback does not steal
navigation. Returning through the New onboarding link may then select that retained
operation's case-specific URL. Already-issued backend work is not claimed to be rolled
back.

## C. Route-triggered mutation accounting

"Zero route-triggered mutation" means mounting, refreshing, direct entry, and browser
history cause zero new business mutation. Verification reports these separately from:

- explicit login/logout requests;
- user clicks that create, upload, retry, complete, resume, resolve, update, or delete;
- settlement of an operation explicitly initiated before a later navigation.

A previously initiated upload settling after navigation is not counted as a router
write, but its callback remains subject to the identity and publication guards above.

## D. Inert unknown and unavailable routes

Unknown and capability-unavailable routes perform no case/resource-specific fetch and
no business write. Existing authentication restoration and global/session profile
reads may still occur at the application boundary. They are accounted for separately,
must not be duplicated by routing, and do not authorize a protected screen.

## E. Phase 15B boundary

New review buttons and continue-after-retry controls owned by Phase 15B remain a later,
separately authorized integration task. Phase 15C neither implements nor tests those
business semantics and does not edit Phase 15B's backend, contracts, review/rework
behavior, or worktree.

## F. Evidence categories

The completion report distinguishes four evidence categories:

1. `MemoryRouter`/jsdom component and route behavior;
2. actual browser navigation behavior;
3. local Vite HTTP history-fallback and API/static exclusions;
4. production-host history fallback.

Evidence in one category is never represented as proof of another. Production-host
fallback remains unverified unless an authorized host is actually tested.

## G. Stop boundary

This implementation run ends after the implementation report. It does not self-issue
an independent quality-gate verdict and performs no staging, commit, push, PR, merge,
rebase, reset, stash, clean, branch switch, sibling-worktree change, or external
activation.

## Dependency and owner confirmation

Before installation, the official versioned React Router documentation and tagged
package manifest confirmed `react-router` `7.18.4`, declarative `BrowserRouter`, Node
`>=20.0.0`, and React/React DOM peers `>=18`. The local versions are Node `22.23.2` and
React/React DOM `18.3.1`, so the exact dependency is compatible without upgrading the
existing stack. `docs/decisions/ADR-001_FRONTEND_URL_NAVIGATION.md` was confirmed unused.

## Owner-authorized remediation refinement after independent Phase 15C QG

**Dated:** 2026-09-19

The repository owner authorizes two narrow additions to the Phase 15C remediation
boundary after the independent quality gate failed:

- `apps/frontend/src/pages/CaseDetail.tsx` is in scope only to bind local action,
  dialog, busy, error, mutation-publication, and post-mutation navigation lifetime to
  exactly one active routed case identity. This adds no backend, API, review/rework, or
  business capability.
- `apps/frontend/vite.config.ts` is in scope only to correct the local Vite development
  server's static `/assets/**` namespace so a missing asset cannot fall through to the
  SPA history fallback. Existing application fallback and API proxy behavior must be
  preserved.

Lifecycle scripts, lifecycle tests, backend lifecycle behavior, timeout and port-
ownership rules remain read-only. Production hosting remains a later deployment-owner
dependency and is not configured or verified by this remediation. The independent
`PHASE_15C_QUALITY_GATE.md` remains immutable evidence.
