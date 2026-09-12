# Phase 14.5 Policy, Team, and Identity Administration

## Task intent

- Requested outcome: implement the accepted Phase 14.5 planner in seven ordered slices.
- Scope: dynamic teams, Alpha/Beta presentation, persistent profile/team administration,
  HR, repository-backed authentication and session revocation, Director team filters,
  typed policy administration, and immutable per-case runtime policy snapshots.
- Non-goals: Phase 14 work, case deletion/reassignment, user/team deletion or
  deactivation, password reset, production IAM, new dependencies, live integrations,
  or sponsor-policy claims.
- Change kind: high-risk cross-module application, persistence, authentication, and
  schema evolution.

## TaskStartSnapshot

- Branch: `phase/14-5-policy-team-admin`
- HEAD / BASE_SHA: `aba264af3b4088a9a10fe682ee6fc0cb418d550d`
- origin/main: `aba264af3b4088a9a10fe682ee6fc0cb418d550d`
- merge-base: `aba264af3b4088a9a10fe682ee6fc0cb418d550d`
- `HEAD..origin/main`: empty
- tracked tree: clean
- task-owned initial untracked file:
  `.ai-pipeline/001_planner/PHASE_14_5_POLICY_TEAM_IDENTITY_ADMIN.md`
- concurrent Phase 14 worktree: prohibited and not accessed

## BaselineReadSetHint / BaselineUsageDraft

Required and acknowledged before implementation: `AGENTS.md`, repository skill
catalogue and required skills, `docs/PROJECT_CONTEXT.md`, `docs/CODEX_WORKFLOW.md`,
the complete Phase 14.5 planner, Phase 13 auth/RBAC architecture and access contract,
the accepted Phase 13 final security/re-quality evidence, relevant decision/open
question entries, the regression catalogue, and current auth/team/policy/case-query/
Dashboard/persistence/frontend owners.

Missing by design: the concurrent Phase 14 worktree. Decision: continue from the exact
accepted baseline and report later `origin/main` drift without merging.

## ImpactStatementDraft

Backend API, authorization, identity, session, global administration persistence,
Mongo collections/indexes, case schema, runtime policy consumers, shared frontend
types/transport/navigation, and current project documentation are affected. Existing
case ownership IDs, five Phase 13 user IDs, security middleware behavior, v1/v2 reads,
provider boundaries, dependencies, and historical reports must be preserved.

## Execution Readiness View

- Intent lock: the four product features plus their necessary persistence/auth/schema
  foundation.
- Scope fence: planner section 4 and the execution prompt stop conditions.
- Baseline lock: exact SHA above; no main integration during implementation.
- Canonical owners: administration repositories, authentication service,
  `CaseAccessPolicy`/`CaseQueryService`, policy catalogue, and case policy snapshot.
- Compatibility boundary: `TEAM_A`/`TEAM_B`, legacy schema readers, historical reports,
  and Phase 13 browser/session protections.
- Retirement boundary: fixed maps/profiles and browser-derived policy cease runtime
  authority; seed definitions may remain only as bootstrap input.
- Task batches: planner slices 1 through 7 in order.
- Test obligations: focused slice checks followed by the full planner matrix.
- Review gates: implementation verification only; independent quality review is out of
  scope.
- Drift rules: stop on baseline/security/schema contradiction; never inspect the other
  worktree or merge/rebase/reset.

## Anti-entropy decision

- Deletion class: internal code retirement and contract-carrying schema evolution.
- Old authority: fixed team/profile runtime maps, fixed-capacity auth, browser-derived
  policy catalogue, and global mutable threshold consumers.
- New authority: repository-backed administration, policy catalogue, and immutable
  per-case snapshot.
- Preserved behavior: persisted team IDs, bootstrap identities, v1/v2 reads, existing
  security and workflow behavior.
- Retired behavior: fixed runtime catalogue/profile ownership and retroactive global
  threshold lookup.
- Source-of-truth data risk: none; no data deletion or bulk migration is authorized.
- Path: delete-first for internal responsibilities; compatibility exception only for
  the explicit planner boundaries above.
