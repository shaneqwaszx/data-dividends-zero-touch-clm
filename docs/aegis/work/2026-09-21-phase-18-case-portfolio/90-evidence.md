# Phase 18 case portfolio — evidence

## Behavioral proof

- API compatibility and additive route: focused Phase 18 API tests plus full backend.
- Exact filter/order/scope/search semantics: domain, memory, structural Mongo, physical
  Mongo, API, frontend transport/key, and guarded browser assertions.
- Bounded inventories: API 1/25/105; browser 105; physical Mongo 105 with 100/5 pages.
- Cache/session/deletion safety: exact actor/all-dimension keys, bounded prefetch,
  300 ms no-stale-label debounce, mutation family invalidation, cancel-before-delete,
  cross-user isolation, logout/login browser transition, and no resurrection.
- Read-only boundaries: one Mongo aggregate, no full-envelope/detail fan-out, no legacy
  list prefetch for Cases, no provider/workflow/target/cache/write call from portfolio.

## Final owned results before independent review

- Backend: focused 61/61; full 1088 passed, 27 expected physical/environment skips.
- Frontend: focused 22/22; full 252/252; typecheck/build PASS.
- Static: Ruff PASS; strict mypy 94 files PASS.
- Governance/contracts/runners/scanner/lifecycle: complete root run 231/231 with the
  required contract-support path before the bounded route-only repair; all four direct
  checks were rerun after that repair and PASS. A first final invocation without the
  support path failed collection and supplied no behavioral evidence.
- POC catalogue: the full 1088-test backend run subsumes the previously explicit
  591/591 catalogue selection; no catalogue change.
- Windows lifecycle: 23/23; owned ports/processes clear.
- Guarded Chromium: 6/6.
- Physical MongoDB 7: 7 suites, 27/27, zero skips/errors/failures; cleanup confirmed.
- Hygiene: final tracked diff check and conflict scan PASS; new-file hygiene is part of
  the frozen manifest step.

Evidence is revision/content-specific. It is implementer evidence and not an independent
quality-gate verdict.
