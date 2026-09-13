# Phase 14 → Phase 14.5 controlled integration execution

## State

- Branch: `phase/14-5-policy-team-admin`
- Pre-integration HEAD: `200464d55248d5e13a84f67fa887bba0f11c80c0`
- Incoming `origin/main`: `b8f9406b57929c7ede537b0262ea78f655b48c27`
- Merge state: active, no commit created.

## Resolution

The integration preserves Phase 14's portfolio projection, session-scoped TanStack Query
cache, hard-delete route/adapter, compare-and-delete safety, and physical-test allowlist.
It also preserves Phase 14.5 dynamic administration, capability-based case access,
dynamic-team Director filtering, and dynamic team labels. The portfolio projection now
uses string-canonical `TeamId` values, accepts legacy v2 snapshots as well as v1/current
schema, and response/dashboard labels come from the dynamic team directory rather than a
static team map.

Mongo test-safety allowlisting accepts only generated `p12`, `p13`, `p14`, and `p145`
names. CI runs both Phase 14 and Phase 14.5 isolated physical modules when its explicitly
configured CI URI is present.

## Verification

- `python -m pytest tests/test_phase14_case_management_performance.py tests/test_phase13_auth_rbac.py tests/test_phase13_dashboard.py tests/test_phase13_mongo_test_safety.py -p no:cacheprovider --tb=short`: **94 passed**.
- `npm.cmd run typecheck -- --pretty false`: **passed**.
- Frontend owner evidence: `npm test -- --run` **152 passed across 6 test files**;
  `npm run typecheck` and `npm run build` both **passed**.
- Owner physical-Mongo evidence: Phase 14 verifier **1 passed in 107.98s**; Phase 14.5
  verifier **1 passed in 33.58s**; structural/Mongo safety support **14 passed in 0.54s**.
- Owner lifecycle evidence: `python -m pytest tests\test_demo_lifecycle_windows.py
  -p no:cacheprovider --tb=short` **18 passed in 190.22s**. `pwsh` and `pwsh.exe`
  were both resolved before that run.

## Safety receipt

- `.env` accessed: no.
- Mongo URI printed: no.
- Password/hash material printed: no.
- Shared `clm_poc` inspected or written: no.
- Phase 14 worktree or protected artifacts accessed: no.
- No commit, push, rebase, reset, stash, clean, branch switch, or merge abort was run.

## Remaining gate

The merge is staged but intentionally active and uncommitted. Physical-Mongo and lifecycle
owner proof is complete. An independent integration quality gate is the remaining gate
before any merge commit or PR decision.

## Follow-up remediation

- The hostile-environment child test launched from repository root and inherited no
  bounded backend import path. It could resolve a stale ambient `app` package that lacked
  Phase 14.5's `admin_repository`. The harness now sets `PYTHONPATH` solely to its exact
  current backend tree; hostile Mongo values remain present and the child test passes.
- The CI-established contract command is `python -m unittest discover -s ../../tests/contract
  -p 'test_*.py'` from `apps/backend` with repository-root `PYTHONPATH`. It passed 44 tests.
  The root `pytest tests/contract` command is not the established invocation and needs no
  source change.
- Ruff formatted only the nine integration-sensitive files named in the remediation
  handoff.
- No lifecycle code change was required. The owner subsequently confirmed `pwsh`/
  `pwsh.exe` resolution and a complete 18-passing lifecycle run.

## Final remediation checks

- Hostile-environment isolation: **2 passed**.
- Combined Phase 14/14.5/auth/dashboard/priority/persistence suite: **209 passed**.
- Full backend: **980 passed, 14 skipped, 3 existing Pydantic serializer warnings**.
- `python -m mypy app`: **Success: no issues found in 91 source files**.
- `python -m ruff check app tests`: **passed**.
- Targeted nine-file `ruff format --check`: **passed**.
- Lifecycle owner proof: **18 passed in 190.22s**; no lifecycle code change was required.

## Evidence closure

- Result: **PASS** for integration execution evidence.
- Physical Mongo rerun: **completed** by owner evidence for both Phase 14 and Phase 14.5.
- Owner physical execution: **not required further**.
- Owner lifecycle rerun: **not required further**.
- Ready for independent integration quality gate: **yes**.
- The merge remains active and uncommitted; it is not ready for a merge commit, PR, or
  merge to `main` until the independent integration quality gate passes.

## P145-IQG-001 targeted remediation

The independent integration quality gate found that `dashboardQueryOptions` passed the
Director team filter to the API but omitted it from the TanStack Query key. A TEAM_A
snapshot could therefore be reused after selecting TEAM_B during the 45-second freshness
window.

`caseQueryKeys.dashboard` now appends a canonical `teamFilter` segment, using `all` for
an omitted scope and retaining distinct `TEAM_A`, `TEAM_B`, dynamic-team, and `unassigned`
identities. `dashboardQueryOptions` uses that same canonical value for both the key and
the request. The Dashboard prefix remains user-scoped, so creation, priority mutation,
and deletion removal/cancellation continue to invalidate every cached Dashboard scope.

`Phase14CaseManagementPerformance.test.tsx` adds the TEAM_A → TEAM_B regression: it
proves separate keys, separate scoped requests/results, safe reuse only when returning to
the original scope, and delete invalidation of both cached scopes. Case Queue and
Onboarded already encode the team filter in their list keys, so no change was needed.

Verification:

- Focused regression: **11 passed**.
- Frontend full suite: **153 passed across 6 files**.
- Frontend typecheck: **passed**.
- Frontend production build: **passed (97 modules transformed)**.

P145-IQG-001 is closed and the integration is ready for independent re-quality-gate
review. The merge remains active and uncommitted; it is not approved for a merge commit,
PR, or merge to `main`.
