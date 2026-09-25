# Frontend Guidance

These instructions extend the repository root guidance for files under `apps/frontend`.

## Boundaries and conventions

- Keep TypeScript strict and derive browser contracts from the backend API; do not
  invent fields, statuses, capabilities, or authorization rules in the UI.
- React components own presentation and interaction. Centralize navigation, API access,
  authentication/session lifecycle, and TanStack Query behavior in their existing
  owners instead of adding page-local alternatives.
- Backend RBAC is authoritative. Capability visibility is usability only. Never persist
  case/evidence data in browser storage or place sensitive/auth/evidence values in URLs.
- Query keys include every server-result input, beginning with authenticated identity
  and including Director team scope where applicable. Pass `AbortSignal`, cancel and
  clear incompatible state on logout/session or identity change/`401`, and prevent late
  responses or deletion races from republishing stale data.
- Keep mutation retry disabled unless backend idempotency and duplicate-effect behavior
  are explicitly proved. Preserve loading, empty, error, focus, keyboard, label, and
  accessible-name behavior in affected views.
- Browser location remains the page/case-navigation identity. Route entry, refresh, and
  history traversal must not trigger business mutations; SPA fallback must not absorb
  API, asset/file, or unsafe-method requests.

Use `frontend-state-cache-change` for shared server-state/cache lifecycle changes and
`architecture-change-review` before adding or replacing a state owner or framework.

## Verification

Select required checks from the root change-class matrix. From `apps/frontend`, the
standard commands are:

```powershell
npm run typecheck
npm test
npm run build
```

Run the focused Vitest file first. Use the configured Playwright/lifecycle path for
navigation or real browser/process claims when required; do not substitute component
tests for those claims.
