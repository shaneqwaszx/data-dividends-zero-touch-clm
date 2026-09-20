# Phase 16 — Registry Cache Execution Addendum

## Authority and scope lock

This addendum records the project-owner approvals supplied on 2026-09-20 for the
implementation described by
`PHASE_16_REGISTRY_CACHE_FRESHNESS.md`. The governing planner remains unchanged.

- **O-16-01:** fresh reuse is approved only for synthetic Mock ACRA snapshots. The
  cache is disabled by default; disabled mode retrieves for every eligible new case.
- **O-16-02:** enabled Mock caching uses exactly `7_776_000` seconds, meaning 90
  elapsed 24-hour periods. It is not three calendar months, an ACRA validity rule, or
  sponsor-confirmed production policy.
- **O-16-03:** one backend-global cache may reuse eligible synthetic Mock snapshots
  across cases, teams, and users. Uploaded documents, human corrections, case state,
  reconciliation, ownership, readiness, and target outcomes are excluded.
- **O-16-04:** one current complete entry exists per exact key. Only a successful
  complete refresh may replace it. Expiry makes an entry ineligible but does not delete
  it. Case deletion does not cascade. No TTL, purge API, history collection, scheduler,
  or background refresh is authorized.

Forced refresh is deferred. Phase 16 adds no Director capability, request flag, public
endpoint, or frontend control. Sandbox/live caching, production sharing/retention, and
existing-case reassessment remain outside this approval. These project-owner decisions
do not resolve sponsor or provider authority.

## Focused execution clarifications

- Freshness is evaluated after acquiring the per-key process-local lock and at the
  actual binding/use point. Every operation provenance timestamp is validated
  individually; the minimum anchor cannot conceal an invalid or future timestamp.
- Memory and Mongo representations must round-trip to identical domain timestamp
  values. The Phase 16 Mongo cache stores every timestamp as the same canonical UTC
  ISO-8601 text representation used by the current case store, including all supplied
  microseconds; it does not use BSON Date. No timestamp is rounded or truncated.
  Freshness and expiry are computed from those unchanged instants. Physical tests must
  prove sub-millisecond round-trip equality and the same one-microsecond-before/exact-
  expiry result before and after restart.
- Lock order is case/establishment lock before registry-key lock. Cache code never
  acquires a case lock. A key lock is released on every success/failure path and is
  retired only after its holder and registered waiters finish. The lock map is bounded
  by active operations, not by the unbounded history of requested identifiers.
- The current synthetic Mock data set is finite, but Phase 16 does not claim the
  provider identifier keyspace is globally bounded. Eviction, retention, or capacity
  policy requires separate authority.
- Disabled mode performs no cache lookup/write and adds no cache-specific startup
  dependency. Current supported Mock and Sandbox routing/error behavior remains.
- The case envelope becomes schema v4. Ordinary exact v1/v2/v3 decoding produces an
  absent binding in memory and never writes solely because a legacy version was read or
  because the binding is absent. Existing independently triggered startup recovery may
  still CAS-write a semantically changed interrupted aggregate in the current schema;
  that recovery must retain an absent binding and must not replay Registry or target
  work.
- In every schema version, an absent binding means only that no successful enabled-cache
  binding was recorded. It does not imply `CACHE_HIT`, `PROVIDER_FETCH`, a newly fetched
  snapshot, or a legacy record. A binding exists only for a complete snapshot that was
  successfully inserted/replaced (or successfully read as a hit) before the case copied
  it. Partial/failed bundles retain their existing case evidence with no binding;
  entity-not-found, cache invalid/read failure, and complete-fetch/cache-write failure
  retain no acquisition, canonical entity, or binding.

## Task-start preflight and evidence identity

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`
- Branch / `BASE_SHA` / current source: `phase/16-registry-cache-freshness-planning` /
  `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
- Observed `origin/main`: `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
- Initial tree: tracked-clean; the governing planner was the expected sole untracked
  file; no Git operation was active.
- Available runtimes: Python 3.12.10, Node 22.23.2, npm 10.9.8, Git, `rg`, and Docker
  CLI 29.8.0. The Docker daemon was not accessible in the initial sandboxed preflight;
  physical Mongo acceptance therefore requires a later authorized local-daemon run.
- Exposed collaboration capability supports a fresh read-only architecture reviewer
  and later independent quality-gate reviewer. No app/plugin is required for this
  source-based task.
- No browser, port, database, or provider endpoint is reserved. `.env`, credentials,
  private sponsor material, sibling worktrees, and `clm_poc` remain out of scope.

Keep current source, tested content, and independently reviewed content distinct in all
later evidence. This addendum is authority/design evidence, not behavioral evidence or
an independent gate verdict.

## Canonical owner and write boundary

The new owners are limited to `RegistryAcquisitionCoordinator` (freshness,
single-flight, hit/miss/stale orchestration) and `RegistrySnapshotRepository`
(one shared normalized snapshot per exact key, with memory and Mongo adapters). Existing
authorization, jurisdiction, routing, provider acquisition, canonical mapping, case
repository, reconciliation, ownership, workflow, deletion, and target-ledger owners are
preserved.

The approved implementation may change backend domain/configuration, provider identity
metadata, cache service/repository adapters, persistence composition/case schema,
backend tests, the guarded physical-Mongo harness, and affected contract/configuration
documentation. It must not change frontend files, public API fields, forced-refresh
surfaces, provider endpoints, dependencies, or the separate UI planner.

## Stop conditions and next authorized action

Stop the dependent slice if independent architecture review finds a substantive owner,
schema, dependency, timestamp, serialization, or lock-lifecycle decision unresolved;
if a shared integration surface changes under the parallel UI lane; or if required
physical Mongo evidence cannot be obtained. The next authorized action after an
independent `PROCEED` is the planner's domain/configuration slice.
