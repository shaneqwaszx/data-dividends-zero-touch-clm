# Phase 06 — Zero-Touch Orchestration, Exception-Only HITL and Integration Readiness

## Authority and goal

This handoff records the detailed Phase 06 assignment supplied on 12 August 2026. It
changes the primary Mock POC product behaviour from manually triggered subsystem
stages to one backend-controlled case journey:

`start -> registry -> document/IDP -> ownership/UBO -> readiness -> Mock GoldTier`

A clean case must reach `MOCK_GOLDTIER_SUBMITTED` with zero human interventions after
the initial UEN/PDF Start action. Human interaction is permitted only for a typed
business exception. Resolution of the final blocker automatically resumes deterministic
work from the next safe checkpoint.

## Required implementation

- Add a top-level, source-neutral orchestrator which coordinates the accepted Phase
  03–05 services and never reimplements comparison, ownership, readiness, target
  ordering, snapshot binding, response validation, or recovery.
- Keep automation runtime state separate from subsystem/CLM state, with equivalents of
  `PENDING_INPUTS`, `RUNNING`, `WAITING_FOR_REVIEW`, `RESUMING`, `COMPLETED`, and
  `TECHNICAL_FAILURE`.
- Define typed, case-isolated, evidence-version-bound business exceptions, conservative
  permitted actions, one-intervention resolution, stale-conflict protection, and
  automatic resume.
- Add an explicit project-defined/provisional document auto-clear decision for complete,
  valid, all-match extraction at or above the configured threshold. Preserve historical
  Phase 03 manual review and distinguish `AUTO_CONFIRMED` from human review.
- Automatically load/analyse ownership, evaluate readiness, and invoke the single
  hardened Phase 05 Mock submission path. Never replay completed target side effects.
- Separate business exceptions from sanitized technical failure. Add no general queue,
  distributed transaction, blind side-effect retry, or sponsor SLA.
- Serialize start/resume/resolution per case, advance monotonically with a fixed loop
  bound, and stop safely on no progress.
- Extend the unified browser summary with automation stage/status, completed stages,
  active exceptions, safe technical failure, metrics, timings, warnings, and timeline.
- Present one sponsor-facing Start action and automatic progress. Move scenario and
  manual Phase 03–05 controls behind an explicit Demo/Test boundary. Short polling is
  sufficient; WebSockets are excluded.
- Add reusable adapter-conformance evidence for Registry, IDP, Ownership, and GoldTier
  boundaries and keep Mock scenario knowledge outside provider-neutral orchestration.

## Accepted scenarios

Permanent Phase 06 coverage must include straight-through zero touch; document mismatch
pause and resolve/resume; low confidence; ownership cycle/incomplete; existing party;
technical provider failure; duplicate/concurrent start and resume; stale resolution;
multiple blockers; cross-case isolation; no-progress loop guard; and target-response/
recovery preservation. The clean path metric is `human_interventions = 0`.

## Policy and sponsor boundary

The Phase 06 auto-clear threshold, source-retention resolution, ownership rule, bounded
retry treatment, and exception authority are PROJECT-DEFINED / PROVISIONAL. Q-003,
Q-005, Q-013, and Q-014 remain open for document/review policy; Q-004 for UBO; Q-012
for live ACRA; Q-002 for hierarchy; Q-006/Q-007 for related-party mapping/write;
Q-008/D-018 and environment details for real GoldTier/PingFed; and Q-001 for
Ready-for-Approval. No review action is approval.

The bounded terminal remains `MOCK_GOLDTIER_SUBMITTED`. Real ACRA networking, real
GoldTier/PingFed, live hierarchy, related-party writes, Ready-for-Approval, autonomous
compliance decisions, production RBAC/retention, durable queues/databases, Camunda, and
Phase 07 are explicit non-goals.

## Documentation and supporting reviews

Create:

- `docs/architecture/PHASE_06_ZERO_TOUCH_ORCHESTRATION.md`
- `docs/contracts/ZERO_TOUCH_AUTOMATION_POLICY.md`
- `docs/contracts/INTEGRATION_ADAPTER_CONTRACTS.md`
- `.ai-pipeline/reports/PHASE_06_INTEGRATION_SECURITY_REVIEW.md`
- `.ai-pipeline/reports/PHASE_06_POC_REGRESSION.md`

Update project context, README, decisions/open questions, documentation indexes, and
the canonical regression catalogue only for implemented and verified behaviour.

## Verification and stop condition

Run the complete backend and Phase 01–06 focused suites; exception/resume/stale/
concurrency/loop/isolation/conformance/target-recovery/adversarial tests; contracts and
repository tests; Ruff; strict mypy; secret and GoldTier validators; frontend typecheck,
tests, and production build; dependency checks; and tracked/cached/untracked whitespace
checks. Apply the integration-security-review and poc-regression-check workflows after
implementation.

Do not stage, commit, push, merge, change branch, begin Phase 07, or issue the
independent Phase 06 Quality Gate.
