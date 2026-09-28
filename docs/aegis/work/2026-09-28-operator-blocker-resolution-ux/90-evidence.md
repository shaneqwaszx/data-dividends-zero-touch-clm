# Operator blocker resolution UX - Evidence

- Baseline: branch `feat/operator-blocker-resolution-ux`; base/HEAD/origin-main
  `3e517d3660de2fd64b1d491a59954cc24321144f` before task edits.
- Focused backend: Search failure/no-match/ambiguous, six bounded safe failure
  categories, Alpha/Beta ownership persistence, and sandbox terminal-state checks
  passed.
- Canonical backend: full `pytest -q` reached 100% (`1,433 passed, 36 skipped`)
  after the Search technical-failure remediation.
- Static backend: `ruff check app tests` passed; strict `mypy app` passed for 108
  source files. The exploratory non-gate `mypy app tests` exposed pre-existing test
  typing debt and is not represented as a passing check.
- Frontend: 25 Vitest files / 318 tests passed; typecheck and production build passed.
  An intermediate full-suite run exposed router coupling in isolated Case Detail tests;
  focus intent was moved to an optional prop from the existing route owner and the full
  suite then passed.
- Browser: 18 guarded isolated Playwright scenarios passed, including blank Director
  team, Alpha/Beta request persistence, start-new/delete/actor reset, retained focus
  intent, problem-only controls, Search/classification/target/approval panel focus,
  keyboard activation, and reduced-motion behavior.
- Governance/security: architecture, project-state, provider-readiness, policy-authority,
  tooling, secret scan and GoldTier example validation passed.
- Physical Mongo: not triggered; no schema/repository/CAS/index/driver bytes changed.
- Provider receipt: local Mock composition only; no external ACRA or GoldTier call and
  no target-mutation retry was performed.
- Initial independent Quality Gate: `FAIL`; its technical/business-state,
  dead-destination, Onboarded-detail route, and focused-regression findings were all
  remediated before the first re-gate.
- First independent re-gate: `FAIL`; it identified a truthful-projection gap where an
  evaluated blocked Readiness node appeared `NOT_REACHED`, plus one stale architecture
  diagram edge. Both are remediated. The failed-Search regression now asserts the exact
  full top-level pipeline vector and safe blocker code; focused and full backend,
  Ruff, strict mypy, architecture, project-state, provider-readiness, policy-authority,
  secret, and diff checks pass after this final business-code change. A second fresh
  independent re-gate remains required.
