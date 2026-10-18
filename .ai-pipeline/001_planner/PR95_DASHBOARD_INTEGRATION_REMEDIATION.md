# PR95 Dashboard v2 integration and remediation

Owner assignment: 2026-10-18. Coordinator owns all Git/source writes. Independent
reviewer receives frozen content and may write only its assigned gate report.

- Branch: `codex/pr95-dashboard-remediation-20261018`.
- Published PR95 base: `1c1fd9fbf1a68f79137d150ac8609cf811b10938`.
- Integration baseline: `cc10a2b626ef92d2dd44600d488c1f15cc4f04f8`.
- Initial common ancestor: `12ba994b8128a4777e12fcc764bafc8f39b9292a`.
- Scope: preserve Dashboard v2 and accepted main Assistant; fix Mongo creator
  projection/activity parity, metric correctness, Ruff, integration regressions.
- Owners: DashboardService; CaseQueryService; existing memory/Mongo portfolio
  adapters; authenticated frontend transport/query/view owners. No new owner/ADR.
- Write boundary: dashboard domain/service/routes/types/view/query/tests; existing
  Mongo bounded projections/validators; affected contracts and task reports.
- Non-goals: connectors, sponsor policy, target ledger/orchestration, PR96,
  publication, teammate-branch mutation, redesign, dependencies.
- Classes: BACKEND_DOMAIN, BACKEND_API, FRONTEND_UI, FRONTEND_STATE_CACHE,
  PERSISTENCE, AUTH_RBAC_SECURITY; CI_TOOLING for browser inventory assertions.
- Required evidence: failing-first regressions; full backend/frontend, Ruff/mypy,
  typecheck/build, contracts/security, guarded physical Mongo, browser/navigation,
  tooling/state/architecture/secrets, final complete diff and independent gate.
- Adverse cases: creator type/schema corruption, unknown legacy creator, cross-team
  creator filter, RM/Director/HR scopes, inaccessible versus absent 404, session and
  team cache separation, old cases/default dates, zero-touch denominator, progress.
- Capabilities observed: Python 3.12.10; Node 22.23.3; npm 10.9.9;
  pytest 8.4.2; Ruff 0.16.2; mypy 1.20.2; pymongo 4.15.1; Docker 29.8.2.
  Managed isolated worktree; writes/network require escalation. Primary .env and
  evaluation artifacts are excluded. Physical Mongo uses owned container
  `clm-pr95-mongo-20261018`, loopback port27027 and generated allowlisted databases.
  Browser runner uses task-reserved ports8775/4183; no shared service termination.
- Owner explicitly authorized local candidate/normal main merge commits, fresh
  independent gate, and clean committed pre-PR verification; no publication authority.
- Owner authorized creator case counts and actual recorded resolver fixes, including
  resolver-only rows, deduplicated RESOLVED blockers and authorized scope parity.
- Owner requires additive v2 fields, original historical_trend calculation/schema,
  all-history API default, and explicit30d browser initialization; no endpoint versioning.
- Exact N-day Singapore boundaries correct the off-by-one selected-date defect.
  Progress/zero-touch formulas remain the explicit project-defined PR95 formulas.
- Stop on unresolved conflict intent, unsafe Mongo namespace, unavailable required
  evidence, or unresolved authorization. No test weakening or sponsor assumptions.

Implementation/tested/reviewed identities and final commands/results belong to
PR95_DASHBOARD_IMPLEMENTATION.md and PR95_DASHBOARD_QUALITY_GATE.md reports.

Round 2 independently found F4: browser-clock dashboard ages violate the accepted
case timing profile. Remediation reuses the canonical backend projection and one
observation for lists/workload, adds safe unavailable errors and clock/filter/sort/
completed-duration/physical parity regressions. Preserve both FAIL reports; fresh
acceptance writes PR95_DASHBOARD_ACCEPTANCE_QUALITY_GATE.md on the corrected freeze.

Round 3 requires F5 observation after both existing state reads, F6 exact integer
resolution/mean arithmetic, and F7 a canonically valid retained completed fixture.
No schema/decoder relaxation is permitted. Regression evidence covers read
interleavings, SG/UTC boundaries, millisecond precision and physical restart parity.
Fresh acceptance uses PR95_DASHBOARD_FINAL_ACCEPTANCE.md; earlier FAILs stay immutable.
