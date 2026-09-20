# ADR-002 — Mock registry snapshot cache ownership

## Status

Proposed

## Date

2026-09-20

## Context

Each eligible new case currently invokes the existing four-operation ACRA acquisition
adapter and retains its own normalized `RegistryAcquisitionBundle`. Phase 16 has explicit
project-owner approval to reuse fresh synthetic Mock snapshots under a fixed provisional
policy, while preserving retrieve-each behavior by default. Case evidence cannot safely
own cross-case reuse, and routing/provider adapters must not acquire storage or policy
responsibilities.

The approved scope requires memory/Mongo parity, exact provider/data-set isolation,
immutable per-case evidence, strict legacy reads, safe concurrency, and unchanged
downstream owners. It does not authorize sandbox/live caching, production retention,
forced refresh, existing-case reassessment, or distributed exactly-once claims.

## Decision

Add one `RegistryAcquisitionCoordinator` as the sole owner of post-route cache
hit/miss/stale decisions and process-local per-key single-flight. Add one
`RegistrySnapshotRepository` port with defensive memory and strict Mongo adapters as the
sole shared snapshot state owner.

The coordinator is called only after existing authorization/team, jurisdiction, router,
and identifier gates. It delegates misses/stale refreshes to the existing
`RegistryProvider.retrieve_acquisition`, accepts only complete normalized bundles, and
returns a defensive bundle plus immutable case-use binding. Existing router, adapter,
mapper, case repository, reconciliation, ownership, workflow, deletion, and target
ledger owners remain unchanged.

Shared cache schema v1 is separate from case-envelope schema v4. A complete shared
snapshot is written first and then copied into a case; no cross-collection transaction
or distributed exactly-once guarantee is made. Insert and replacement remain distinct;
replacement uses revision CAS without upsert or automatic conflict retry.

## Alternatives considered

- Keep retrieve-each only: retained as the disabled default, but it does not provide
  the explicitly approved Mock reuse mode.
- Reuse another case envelope: rejected because it would couple shared evidence to case
  identity, team access, deletion, and mutable workflow history.
- Put caching in `RegistryProviderRouter`: rejected because routing does not own storage
  or freshness.
- Decorate `AcraRegistryProviderAdapter`: rejected because it would mix provider
  acquisition with policy/persistence and could be invoked before application gates.
- Extend the mutable policy catalogue: rejected because it would create new operator
  mutation/RBAC behavior and retroactive policy changes outside this phase.
- Cache per operation or raw responses: rejected because it permits mixed/partial
  evidence and violates normalized-data and minimization boundaries.
- Add Redis, distributed locks, leases, transactions, or background refresh: rejected
  because the single-process POC does not justify those owners or dependencies.

## Consequences

- Enabled Mock mode can suppress repeated provider calls for fresh exact-key snapshots.
- Disabled mode keeps current retrieve-for-each behavior with no cache lookup/write or
  cache-specific startup dependency.
- Each case preserves immutable original evidence. A binding records a cache hit or a
  successfully committed complete provider fetch without claiming re-verification;
  disabled/bypass or incomplete/failure paths retain no binding.
- Memory cache is process-local; Mongo cache survives restart. Multi-process duplicate
  provider calls remain possible, with CAS protecting the stored winner.
- A valid cache write may survive a later case-establishment failure because shared
  snapshot state is not case-owned.
- Expired entries remain stored and ineligible; capacity, retention, and purge remain
  unresolved future policy.

## Architecture invariants affected

- Added: exactly one cache/acquisition coordinator and one snapshot repository port.
- Added: shared snapshot and case evidence are separate schemas and owners.
- Added: case/establishment lock precedes registry-key lock; cache code never acquires a
  case lock.
- Preserved: source payload -> strict DTO -> normalized bundle/canonical evidence.
- Preserved: router/provider/case/authorization/reconciliation/ownership/target owners.
- Preserved: explicit memory/Mongo modes with no fallback, strict identity and CAS,
  insert-only create, update-only replace, and no stale resurrection.
- Retired: none. Retrieve-each remains the disabled compatibility behavior.

## Security and persistence implications

The cache contains only normalized synthetic Mock bundles. It has no API, listing,
browser field, team/user selector, raw provider payload, endpoint, credential, document,
human correction, ownership result, or target state. Existing team-owned case access is
still the only disclosure surface.

Mongo uses a distinct collection, deterministic exact-key identity, strict schema-v1
decoding, unique identity/index validation, and revision CAS. All cache timestamps use
canonical UTC ISO-8601 text with full microseconds, matching the current lossless case
serializer; BSON Date, rounding, and truncation are excluded. Case schema v4 adds the
binding while ordinary exact v1/v2/v3 decoding yields `None` with no version-only write.
Existing semantic startup recovery may still CAS-write a changed interrupted aggregate
to the current schema, retains `None`, and makes no Registry or target call. Mongo
failure never falls back to memory. Case deletion does not cascade to shared snapshots,
and a stale case write cannot recreate a deleted case.

## Migration and retirement implications

No bulk migration or binding/version repair-on-read is used. Existing case documents
remain readable through exact versioned readers and are not rewritten merely because
they are legacy or lack a binding. The existing separately triggered interrupted-state
recovery write remains intact. Cache mode can be disabled to restore retrieve-each
behavior without changing historical case evidence; disabling is not a persistence
fallback and does not delete shared entries.

The cache owner is revisited, not automatically retired, if production provider,
retention, licensing, scale, or multi-process requirements are authorized. No legacy
cache path exists.

## Verification

- Focused key/model/configuration, freshness-boundary, invalid/future timestamp,
  complete-only, failure, call-stopping, defensive-copy, concurrency, and lock-retirement
  tests with injected clocks and controlled barriers/events.
- Exact v1/v2/v3 ordinary-read compatibility with zero writes, legacy interrupted-state
  recovery to v4 without provider/target replay, v4 outcome/binding matrix and impossible-
  combination rejection, CAS, restart, and delete-independence tests.
- Lossless sub-millisecond ISO timestamp round trip and identical one-microsecond-before/
  exact-expiry decisions in memory and physical Mongo.
- Physical Mongo insert/hit/restart/CAS/conflict/invalid-schema/cleanup evidence using a
  generated allowlisted `clm_p16_<24 hex>` database and never `clm_poc`.
- Full affected backend, Ruff, mypy, contract/security/governance, POC regression, and
  independent quality-gate evidence on frozen content.

## Revisit conditions

Revisit for any sandbox/live caching, authoritative provider-effective timestamp,
production sharing/retention/deletion rule, existing-case reassessment, forced refresh,
operator-editable policy, globally bounded capacity/eviction requirement, or deployment
where multi-process single-flight is required.

## Related contracts and sponsor questions

- [Phase 16 planner](../../.ai-pipeline/001_planner/PHASE_16_REGISTRY_CACHE_FRESHNESS.md)
- [Phase 16 execution addendum](../../.ai-pipeline/001_planner/PHASE_16_EXECUTION_ADDENDUM.md)
- [Registry cache freshness profile](../contracts/REGISTRY_CACHE_FRESHNESS_PROFILE.md)
- [Persistence recovery profile](../contracts/PERSISTENCE_RECOVERY_PROFILE.md)
- [ACRA Mock API profile](../contracts/ACRA_MOCK_API_PROFILE.md)
- [Decision log](DECISION_LOG.md), especially D-029, D-033, D-040, D-042, and D-044
- [Open sponsor questions](../sponsor-questions/OPEN_QUESTIONS.md), especially Q-012,
  Q-013, Q-015, and Q-016
