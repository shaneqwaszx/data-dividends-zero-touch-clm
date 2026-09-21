# Phase 18 case portfolio — intent

Requested outcome: deliver the bounded backend-authoritative Cases search/filter/page
vertical slice, independently gate it, and publish one unmerged PR.

Scope and non-goals are locked by `.ai-pipeline/001_planner/PHASE_18_PLAN.md`. The work
must preserve the old list endpoint, canonical authorization/query/repository/cache
owners, provider behavior, workflow behavior, schema v4, and human-only merge.

Baseline read set: `AGENTS.md`, `docs/PROJECT_STATE.md`, `docs/ARCHITECTURE.md`,
`docs/DEVELOPMENT_WORKFLOW.md`, the case access/priority contract, relevant decisions and
Q-016, repository phase/integration/cache/persistence/regression/gate skills, current
owners/tests, and accepted Phase 17 plan/implementation/gate evidence.

Baseline usage: all required current authority was acknowledged before the Phase 18
plan. No missing sponsor authority affects this project-defined read-only POC query.
Q-016 remains open and no assignment, risk, SLA, or workflow policy is inferred.

Impact: additive paged read contract, repository query semantics, React Query identity,
and Cases presentation. No new state owner, persisted field, index, provider call, or
business mutation.

Execution readiness: intent, scope, base, owners, compatibility, query semantics, test
obligations, independent gate, publication boundary, drift rules, and evidence required
before completion are recorded in the Phase 18 plan. Stop states are done, blocked,
needs-verification, or scope-exceeded.
