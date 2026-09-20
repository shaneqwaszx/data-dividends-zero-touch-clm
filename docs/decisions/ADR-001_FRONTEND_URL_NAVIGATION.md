# ADR-001 — Frontend URL navigation

## Status

Proposed

## Date

2026-09-19

## Context

The authenticated React workspace currently chooses its page and case with transient
`App.tsx` state (`activeTab`, selected case/client IDs, and an audit case seed). Direct
entry, refresh, browser Back/Forward, and native new-tab links therefore cannot restore
the same application identity. Phase 15C requires the URL to become canonical without
moving authentication, server-state caching, authorization, or workflow mutation into
the router.

`AuthProvider` already owns the session lifecycle, one in-memory QueryClient already
owns user/case/team-scoped server state, and the backend remains authoritative for
capabilities, access, case existence, and business transitions. The routing boundary
must reuse those owners and retire the competing transient page/case owner.

## Decision

Use exact `react-router@7.18.4` in declarative `BrowserRouter` mode. Browser location
plus `apps/frontend/src/navigation.tsx` own route patterns, safe path builders,
capability-visible navigation, route matching, root selection, and generic unavailable
presentation.

The router is mounted once outside the existing `AuthProvider`. Route elements receive
existing page components and handlers from the still-mounted `App`; no loader, action,
second QueryClient, second auth guard, persistent browser store, or route-triggered
business mutation is introduced. Only an opaque, bounded case ID is encoded in paths.

## Alternatives considered

- Keep the transient `App.tsx` owner: rejected because it cannot provide stable direct
  entry, refresh, history, copy-link, or new-tab behavior.
- Build a custom History API and `popstate` matcher: rejected because it would create a
  repository-owned routing framework and duplicate maintained matching, link,
  accessibility, and active-state behavior.
- Use hash routing: rejected because the approved identity is a real pathname and
  deployment requires an explicit safe history fallback.
- Use React Router data/framework mode: rejected because existing API handlers and
  TanStack Query already own data and mutation lifecycles; loaders/actions would overlap
  those owners.
- Adopt React Router v8: rejected because it would require unrelated React and Node
  baseline changes. Phase 15C is pinned to the compatible maintained v7 line.

## Consequences

- Every existing workspace screen and case view has one stable URL with native link and
  browser-history semantics.
- `activeTab`, selected case/client/audit identity, `initialTab`, and their setter-based
  routing are removed rather than synchronized.
- Existing intake state remains tab-memory only. A created case receives a retained
  intake URL before upload when the user is still at the originating destination; a
  late create response never steals a newer destination.
- A refresh cannot restore `File` objects or in-memory duplicate guards. The retained
  intake route therefore renders backend-authored GET state and safe recovery links
  without retrying or reconstructing the original package.
- `BrowserRouter` requires the deployment owner to serve `index.html` for eligible
  application GET/HEAD routes after API and static handling, while never rewriting
  `/api/**`, missing assets, or unsafe methods.
- The new runtime dependency and deployment fallback are ongoing compatibility surfaces.

## Architecture invariants affected

- Added: URL/router is the sole page and case navigation identity.
- Added: route mount, refresh, and history never initiate a new business mutation.
- Preserved: `AuthProvider` owns authentication/session transitions.
- Preserved: TanStack Query owns scoped server state, cancellation, and invalidation.
- Preserved: backend RBAC, case existence, workflow, providers, and persistence remain
  authoritative.
- Retired: transient page/case selection in `App.tsx`, including the test-only
  `initialTab` path. No feature flag or compatibility fallback remains.

## Security and persistence implications

Routes may contain only encoded opaque case IDs. Credentials, tokens, CSRF values,
UENs, names, filenames, evidence, document text, filters, and private error detail are
excluded from URLs and history. Capability checks are presentation only; absent,
deleted, and inaccessible cases retain the backend's identical safe 404. No case data
is added to localStorage, sessionStorage, IndexedDB, a service worker, or shared cache.

The router adds no schema, persistence, provider, transport, or logging behavior. Login
retains the current same-origin pathname without a return-target parameter or external
redirect surface. Unknown/unavailable routes are inert and generic.

## Migration and retirement implications

All approved routes move in one bounded frontend change. The former tab and selected-ID
owner is removed in the same change, and historical tests receive router context rather
than a hidden state fallback. Rollback would remove the router dependency and restore
the old owner as one coherent change; running both owners is prohibited.

Production deployment configuration is not present in this repository and is owned by
dev-tooling/deployment. Its fallback rule is an operational prerequisite, not a Phase
15C production-host verification claim.

## Verification

- Focused route, link, history, capability, malformed-parameter, intake, auth/cache,
  deletion, and delayed Case A -> Case B tests.
- Existing frontend behavior/performance tests plus the full frontend suite,
  typecheck, and production build.
- Exact manifest/lockfile audit and dependency audit.
- Backend, contract, static, security, architecture, project-state, lifecycle, and POC
  regression checks required by the phase plan.
- Local Vite application-route fallback plus API/static/unsafe-method exclusions, and
  actual-browser direct entry, refresh, Back/Forward, and new-tab verification when the
  supported local harness can be run safely.
- Independent Phase 15C quality gate before this ADR may become Accepted.

## Revisit conditions

Revisit if the application adopts SSR/framework routing, a production IdP introduces an
authorized redirect protocol, hosting cannot satisfy the safe fallback contract, React
Router v7 leaves supported maintenance, or measured scale requires route-level code
splitting. None of these conditions authorizes moving API data or mutations into the
router without a new architecture review.

## Related contracts and sponsor questions

- [Phase 15C frontend navigation plan](../../.ai-pipeline/001_planner/PHASE_15C_FRONTEND_NAVIGATION.md)
- [Case access and priority profile](../contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md)
- [Multi-document intake profile](../contracts/MULTI_DOCUMENT_INTAKE_PROFILE.md)
- [Zero-touch automation policy](../contracts/ZERO_TOUCH_AUTOMATION_POLICY.md)
- [Decision log](DECISION_LOG.md), especially D-040 and D-041
- [Open sponsor questions](../sponsor-questions/OPEN_QUESTIONS.md), especially Q-016
