# Phase 13 Auth/RBAC Execution Intent

## Requested outcome

Execute the approved Phase 13 planner for five synthetic profiles, process-local opaque
authentication, server-owned Team A/Team B/Director access, strict optional priority,
schema-v2 persistence compatibility, and UI V2 integration.

## Scope and non-goals

The scope is exactly the eight batches in
`.ai-pipeline/001_planner/PHASE_13_CASE_PRIORITY_AUTH_RBAC.md`. Production IAM, PingFed,
OAuth/JWT, MFA, reassignment, sharing, differentiated role permissions, priority SLA,
live connector work, dependency changes, commits, pushes, merges, rebases, resets,
cleans, and branch switches are excluded.

## Baseline read set and usage

- Required and acknowledged: `AGENTS.md`, `docs/PROJECT_CONTEXT.md`,
  `docs/CODEX_WORKFLOW.md`, the Phase 13 planner, decision/open-question/protocol docs,
  mandated execution/integration/security/regression skills and their checklists,
  Phase 12 persistence architecture/recovery/execution/re-quality-gate evidence, UI V2
  consolidated gate, and the accepted ordering parity gate.
- Current implementation owners inspected: canonical onboarding case/repository/service,
  Phase 12 persistence DTO/store/adapters/composition, API model/route composition,
  zero-touch ordering/orchestration, and current UI V2 API/shell/page surfaces.
- Missing baseline refs: none.
- Decision: continue.

## Impact statement

This phase deliberately changes the public API security boundary, canonical case
metadata, persistence schema, list ordering, and frontend session shell. It must retain
all accepted Phase 01-12 workflow, recovery, call-stopping, and UI V2 behavior.

## Execution readiness view

- Intent lock: Phase 13 only.
- Scope fence: no production identity or new business-policy claims.
- Baseline lock: `36d0247befce04bbed85e3dced9f9c1c2b617855`.
- Canonical owners: one auth service, one access policy, one case query owner, existing
  canonical case and Phase 12 envelope.
- Compatibility: schema-v1 reads are strict and non-writing; new writes are schema-v2;
  legacy cases remain unassigned and Director-only.
- Batches: execute 1 through 8 in order with focused checks per batch.
- Evidence gate: focused auth/RBAC/priority, persistence parity/restart, full backend,
  frontend, contract, security, lifecycle, diff, and drift evidence.
- Stop: done, blocked by a stated planner stop condition, needs verification, or scope
  exceeded.
