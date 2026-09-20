# Phase 16 Mock Registry Snapshot Cache

## Task intent

- Requested outcome: implement the approved Phase 16 Mock registry snapshot cache and
  obtain required architecture, persistence, physical, regression, and independent-QG
  evidence before authorized publication.
- Scope: backend-only Mock cache, exact fixed freshness, separate memory/Mongo snapshot
  repository, case schema v4 binding, guarded physical suite, and affected documents.
- Non-goals: forced refresh, public API/frontend changes, sandbox/live caching,
  existing-case reassessment, new dependencies, or production policy claims.
- Change kind: high-risk backend domain, persistence, external-provider,
  architecture-owner, and CI-tooling change.

## TaskStartSnapshot

- Branch / HEAD / BASE_SHA / origin/main:
  `phase/16-registry-cache-freshness-planning` /
  `cab05d7dc98d4c50c8fc096835fe49802d5896e2`.
- Initial tracked tree: clean; governing planner was the expected untracked file.
- Active Git operation: none.

## BaselineReadSetHint / BaselineUsageDraft

Required and acknowledged: constitution, current project state, architecture, workflow,
relevant ACRA/persistence contracts, decisions/open questions, phase/persistence/
provider/architecture skills, governing planner, current owners, and current tests.
Missing: physical Mongo runtime evidence; initial Docker-daemon access was unavailable.
Decision: proceed through design and deterministic implementation while preserving the
physical-evidence stop condition.

## ImpactStatementDraft

The change affects domain/configuration, provider identity metadata, a new acquisition
coordinator/repository port, memory/Mongo composition, case schema compatibility,
physical-test tooling, and provisional governance documents. Public API/frontend,
provider endpoints/mappings, authorization, ownership, target ordering, and dependencies
must remain unchanged.

## Execution Readiness View

- Intent lock: O-16-01 through O-16-04 exactly as recorded in the execution addendum.
- Scope fence: governing planner core only; forced refresh matrix row excluded.
- Baseline lock: supplied branch and BASE_SHA; no branch switch or sibling modification.
- Owners: one coordinator and one snapshot repository; all current upstream/downstream
  owners preserved.
- Compatibility: disabled mode plus exact case v1/v2/v3 non-rewriting reads.
- Retirement: per-key locks retire after holder/waiters; no cache-retention retirement
  policy is invented.
- Batches: authority docs -> independent architecture review -> domain/config ->
  repository -> coordinator/workflow -> deterministic/broad tests -> physical Mongo ->
  independent QG -> publication only after exact PASS.
- Drift/rewind: stop on owner/schema/authority conflict, shared-surface drift, or missing
  required physical evidence.
