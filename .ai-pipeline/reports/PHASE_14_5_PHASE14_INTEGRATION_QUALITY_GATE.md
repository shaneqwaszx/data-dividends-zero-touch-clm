# Phase 14.5 / Phase 14 Final Independent Integration Quality Gate

Date: 2026-09-13
Reviewer role: final independent integration quality-gate reviewer
Result: BLOCKED

## Executive Result

BLOCKED. The staged merge is structurally clean and the backend, frontend, contract, static, and structural-safety evidence is strong. One High integration defect remains: a Director's selected team is sent to the Dashboard API but absent from its TanStack Query cache key. Switching TEAM_A to TEAM_B can render the cached TEAM_A Dashboard snapshot for the 45-second freshness interval. This violates cache-scope and Director-filter integrity.

No implementation or test remediation was made by this review.

## Phase Acceptance Checklist

| Requirement | Result | Evidence |
|---|---|---|
| Merge integrity | PASS | Active staged merge; no unresolved paths; staged and working diff checks clean. |
| Authorized optimized portfolio reads | PASS | Typed scopes, role restriction, validation, and Mongo projection reads remain intact. |
| Case deletion/RBAC | PASS in memory | Canonical lock reauthorization, role gate, CAS deletion, and case-owned-state removal remain intact. |
| React Query cache scope | FAIL | Lists include team filter in their keys; Dashboard does not. |
| Administration, policy, persistence | PASS | Full test/static evidence; typed runtime snapshots and composition remain intact. |
| Hostile environment | PASS | Exact backend PYTHONPATH change preserves hostile-Mongo shared-DB refusal. |

## Contract and Integration Findings

Phase 14 and Phase 14.5 backend semantics coexist: non-Director filters fail safely, Director selected teams are validated server-side, unassigned handling uses global scope, and the Mongo portfolio query remains projected rather than N+1. No live ACRA, PingFed, GoldTier, or private sponsor artefact was accessed.

## Tester and Adversarial Findings

| Check | Result |
|---|---|
| Full backend | 980 passed, 14 skipped, 3 existing Phase 06 serializer warnings |
| MyPy app | Success: no issues found in 91 source files |
| Ruff | All checks passed |
| Frontend critical suites | 6 files / 152 tests passed |
| Frontend typecheck and build | PASS; 97 modules transformed |
| Established contract discovery | 44 passed |
| Mongo structural/safety | 14 passed |
| Lifecycle reviewer rerun | Owned-process termination denied by this environment; later checks failed closed. Owner evidence: 18 passed in 190.22s. |
| Physical Mongo | URI absent; not requested or printed. Owner evidence: Phase 14 1 passed, Phase 14.5 1 passed, structural/safety 14 passed. |

Ruff formatting over 33 broader Phase-14-touched backend paths reported six retained format candidates, including line-ending-only differences. Lint is clean; this is not an integration finding.

## Code and Architecture Review

High — P145-IQG-001: Dashboard cache key omits selected Director team.

- Evidence: apps/frontend/src/caseQueries.ts defines dashboard keys solely from userId. dashboardQueryOptions accepts teamFilter only for fetchDashboard. Dashboard.tsx maintains the filter locally and reuses the unchanged key.
- Impact: cache identity does not distinguish all, unassigned, TEAM_A, and TEAM_B. A snapshot from one filter can render for another before refetch/staleness.
- Required fix: include a normalized team filter in the dashboard key, update dashboard read/removal/invalidation helpers for that key family, and add a QueryClient/UI regression that switches filters and proves no old snapshot is displayed.

## Security Review

No credential exposure, authentication bypass, shared-Mongo activation, or delete-authority defect was found. The hostile-environment change preserves hostile Mongo values and shared-DB refusal without reading .env. P145-IQG-001 is still High because it mis-scopes sensitive authorized portfolio data within an authenticated Director session.

## Required Fixes

1. Fix P145-IQG-001 and rerun affected frontend tests, full frontend suite/typecheck/build, and integration-focused backend coverage.

Live ACRA and real GoldTier/PingFed remain separately blocked by existing sponsor dependencies.

## Readiness

- Ready for owner merge commit: NO.
- Ready for PR: NO.
- Ready for merge to main: NO.
- Next-phase readiness: NO until remediation and independent revalidation.
- Live ACRA / real GoldTier readiness: NO; existing sponsor blockers remain open.

## Git Status

The merge is active, staged, conflict-free, and diff-clean. This review created only this report. No implementation, test, configuration, or prior report was modified. No commit, push, merge/continue/abort, rebase, reset, stash, clean, or branch switch occurred.

## Required Receipt

RESULT:
BLOCKED

BRANCH:
phase/14-5-policy-team-admin

HEAD:
200464d55248d5e13a84f67fa887bba0f11c80c0

ORIGIN MAIN:
b8f9406b57929c7ede537b0262ea78f655b48c27

MERGE HEAD:
b8f9406b57929c7ede537b0262ea78f655b48c27

MERGE STATE:
active, staged integration; no unresolved paths

CONFLICTS REMAINING:
none

DIFF CHECK:
clean

PARENT COMPARISON:
completed against both supplied parents; P145-IQG-001 is in the combined Phase-14.5 Director-filter addition over the Phase-14 query-cache owner.

PHASE14 CASE DELETE:
PASS

PHASE14 QUERY PERFORMANCE:
PASS

N+1 SAFETY:
PASS

PHASE14 REACT QUERY:
FAIL

CACHE SCOPE / DIRECTOR FILTER:
FAIL

AUTH CACHE INVALIDATION:
PASS

PHASE14.5 AUTH/RBAC:
PASS

PHASE14.5 TEAMS:
PASS

PHASE14.5 ADMINISTRATION:
PASS

PHASE14.5 DIRECTOR FILTER:
PASS server-side / FAIL browser-cache scope

PHASE14.5 POLICY:
PASS

PERSISTENCE COMPOSITION:
PASS

P145-PHYS-001:
PRESERVED

P145-MYPY-001:
PRESERVED

HOSTILE ENVIRONMENT SAFETY:
PASS

BACKEND FOCUSED:
PASS (covered by independent full backend run)

FULL BACKEND:
980 passed, 14 skipped, 3 existing warnings

MYPY APP:
PASS

RUFF:
PASS

RUFF FORMAT:
six retained formatting candidates in broader Phase-14-touched paths; no lint failure

FRONTEND:
6 files, 152 tests passed

FRONTEND TYPECHECK:
PASS

CONTRACTS:
44 passed via CI-established unittest discovery

LIFECYCLE:
owner-evidence; reviewer environment denied child-process termination

PHASE14 PHYSICAL MONGO:
owner-evidence; URI absent

PHASE14.5 PHYSICAL MONGO:
owner-evidence; URI absent

PHYSICAL STRUCTURAL / SAFETY:
14 passed

FINDINGS:
Critical: none

High: P145-IQG-001 Dashboard cache key omits selected Director team.

Medium: none

Low: none

READY FOR OWNER MERGE COMMIT:
NO

READY FOR PR:
NO

READY FOR MERGE TO MAIN:
NO

REPORT:
.ai-pipeline/reports/PHASE_14_5_PHASE14_INTEGRATION_QUALITY_GATE.md

FILES MODIFIED:
report only

DATA SAFETY:
.env accessed = NO

Mongo URI printed = NO

password/hash material printed = NO

shared clm_poc inspected = NO

shared clm_poc written = NO

Phase14 worktree accessed = NO

protected artifacts accessed = NO

No commit, push, merge, merge --continue, merge abort, rebase, reset, stash, clean, or branch switch occurred.
