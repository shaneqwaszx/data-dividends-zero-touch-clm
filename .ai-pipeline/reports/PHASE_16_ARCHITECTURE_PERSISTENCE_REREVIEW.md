# Phase 16 — Independent Architecture and Persistence Re-review

## Verdict

**ARCHITECTURE REVIEW: PROCEED**

**PERSISTENCE CHANGE: PROCEED**

The revised design deterministically closes P16-APR-001, P16-APR-002, and
P16-APR-003. The new coordinator/repository split remains the smallest justified owner
boundary; disabled behavior, keyed locking, strict cache/case schemas, CAS, restart,
deletion independence, and physical-test requirements are now explicit enough to
implement without inventing persistence semantics.

This is a pre-implementation design verdict. It authorizes only the planner's next
domain/configuration implementation slice; it is not implementation acceptance, a
behavioral quality-gate PASS, publication authority, or evidence that physical Mongo
requirements have passed.

## Review identity and preflight

- Role: fresh independent architecture/persistence re-reviewer; no reviewed design or
  implementation artifact was edited.
- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`.
- Branch, assigned `BASE_SHA`, current `HEAD`, observed `origin/main`, and merge base:
  `phase/16-registry-cache-freshness-planning` /
  `cab05d7dc98d4c50c8fc096835fe49802d5896e2`.
- Current source revision: the SHA above. The reviewed Phase 16 design is uncommitted
  working-tree content layered on that source revision.
- Project-state behavioral baseline remains separately recorded as
  `614e9ffc36bc8f0d1a9a4674d04639ad6b2bc638`; it is not treated as this reviewed tree.
- Available and used: workspace filesystem access, PowerShell, Git 2.55.0, Python
  3.12.10, Node 22.23.2, npm 10.9.8, and `rg`.
- Docker CLI 29.8.0 is installed, but its daemon was inaccessible. `mongod` and
  `mongosh` were unavailable and `PHASE12_MONGO_URI` was absent. No database, provider,
  browser, port, `.env`, credential, private sponsor artifact, sibling worktree, or
  `clm_poc` was accessed.
- Current tracked working-tree changes and untracked Phase 16 artifacts pre-existed this
  review and were preserved. The only review-authored file is this report.

### Exact reviewed design content

| SHA-256 | Path |
|---|---|
| `966c2063181857a9598c5b3d276792cc5ba375a8fd327583bc0d4ba19d81efcd` | `.ai-pipeline/001_planner/PHASE_16_REGISTRY_CACHE_FRESHNESS.md` |
| `97b24f7677822930e26f584aea7be2fb620a9e506a38b65602179710e98aa057` | `.ai-pipeline/001_planner/PHASE_16_EXECUTION_ADDENDUM.md` |
| `502e7804b2c7e6a325104b9d06aacc9c9e60100633e179f5032cf43b96ba7499` | `docs/contracts/REGISTRY_CACHE_FRESHNESS_PROFILE.md` |
| `6aa2e2c2efb39b86ceeef485098c7654ecbdbd4dce38e5a0d5ea0019681b8695` | `docs/decisions/ADR-002_REGISTRY_SNAPSHOT_CACHE.md` |
| `ff217546273b29098b30b3b66b6adec90b1a90c09798c5777cafe2f5146d20fc` | `docs/decisions/DECISION_LOG.md` |
| `b4ea326764e01a8751366d0a3b7d13206db0abeff98c32018455fb3889d66fb9` | `docs/contracts/README.md` |

The prior review inspected older addendum/profile/ADR hashes. Those three artifacts
changed; the governing planner, decision-log entry, and contract index did not. Any
further change to the six hashes above requires a fresh review of the changed scope.

## Requirement and change classes

The bounded approved requirement remains a disabled-by-default, synthetic-Mock-only
shared registry snapshot cache with exact `7_776_000`-second elapsed freshness,
exclusive expiry, exact provider/environment/contract/data-set key isolation,
immutable per-case evidence, memory/Mongo semantics, and no public refresh surface.
O-16-01 through O-16-04 and D-044 provide provisional project-owner authority only;
they do not establish ACRA validity, licensing, live interoperability, production
sharing, or retention policy.

Applicable implementation classes remain `BACKEND_DOMAIN`, `PERSISTENCE`,
`EXTERNAL_PROVIDER`, `ARCHITECTURE_REFACTOR`, and `CI_TOOLING`. Frontend behavior,
public API fields, forced refresh, sandbox/live caching, existing-case reassessment,
scheduling, and production retention remain outside scope.

## Prior finding closure

### P16-APR-001 — CLOSED — Timestamp serialization and freshness are exact

The revised addendum, contract, and ADR now choose one representation for every cache
timestamp: canonical timezone-aware UTC ISO-8601 text with all supplied microseconds.
BSON Date, rounding, and truncation are expressly excluded. The rule covers all four
operation provenances, bundle `retrieved_at`, freshness anchor, optional
`provider_effective_at`, cache `written_at`, case `bound_to_case_at`, and computed
`expires_at` (`PHASE_16_EXECUTION_ADDENDUM.md:29-38`;
`REGISTRY_CACHE_FRESHNESS_PROFILE.md:58-85`;
`ADR-002_REGISTRY_SNAPSHOT_CACHE.md:95-99`).

Freshness is recomputed from unchanged decoded operation provenance under the per-key
lock: minimum provenance plus an exact timedelta, fresh strictly before expiry and
stale at expiry. Every operation time, the derived anchor, and write time are rejected
if future relative to the injected evaluation clock. The verification matrix requires
sub-millisecond equality and identical one-microsecond-before/exact-expiry decisions
before and after physical Mongo restart.

This is compatible with current source: the Mock connector can supply microsecond
values, and the case-store serializer already emits lossless UTC text
(`apps/backend/app/persistence/mongo_case_store.py:532-554`). A direct read-only probe
serialized `2026-09-20T12:34:56.123456+00:00` as
`2026-09-20T12:34:56.123456Z`. No normalization point or boundary arithmetic remains
for the implementer to invent.

### P16-APR-002 — CLOSED — Binding/null and failure outcomes are complete

The contract now gives an explicit acquisition/entity/binding matrix for fresh hit,
committed complete fetch, disabled/bypass, entity-not-found, partial, failed,
invalid/read failure, and post-fetch write/CAS failure
(`REGISTRY_CACHE_FRESHNESS_PROFILE.md:88-128`). The addendum states the same owner rule:

- a binding exists only after a complete snapshot was successfully read or committed;
- `CACHE_HIT` and `PROVIDER_FETCH` require all identity, revision, original time,
  policy, expiry, acquisition, and canonical-entity invariants;
- partial and failed provider bundles retain current case evidence and entity with no
  binding;
- entity-not-found, invalid/read failure, and complete-fetch write/CAS failure retain
  no acquisition, canonical entity, or binding;
- an absent binding means only that no successful enabled-cache binding was recorded;
  complete acquisition plus `None` remains legal solely for disabled/provider-identity
  bypass compatibility.

Schema-v4 validation must reject bindings on non-complete evidence, mismatched case,
provider, environment, contract, data set, digest, times, expiry, or revision, while
preserving current complete/partial/failed provider semantics. The coordinator therefore
cannot present an uncommitted fetch as case evidence or freshness metadata, and the
case writer does not have to invent optional binding fields.

### P16-APR-003 — CLOSED — Legacy read compatibility and semantic recovery are separate

The revised rule is now qualified exactly: ordinary exact v1/v2/v3 decoding produces
`None` and performs no write solely for version conversion or an absent binding.
Existing startup recovery may independently CAS-write only when
`_recover_interrupted` semantically changes an aggregate; that write uses the current
schema, retains `None`, and makes no Registry or target call
(`PHASE_16_EXECUTION_ADDENDUM.md:48-53`;
`REGISTRY_CACHE_FRESHNESS_PROFILE.md:98-103`;
`ADR-002_REGISTRY_SNAPSHOT_CACHE.md:99-110`).

This matches the current split between strict legacy `_decode` and startup
`_recover_interrupted`/`replace` in
`apps/backend/app/persistence/mongo_case_store.py:70-98,233-271,390-529`. The planned
verification now separately requires exact v1/v2/v3 zero-write reads and interrupted
legacy recovery to v4 without Registry/target replay. The current focused legacy-read
test passed during this review.

## Architecture assessment

### Existence check and canonical owners

The existence check remains satisfied:

- `RegistryProviderRouter` owns only closed jurisdiction/provider selection
  (`connectors/registry.py:381-409`).
- `AcraRegistryProviderAdapter` and `RegistryAcquisitionBundle` own strict ordered
  provider acquisition and normalized complete/partial/failed evidence
  (`connectors/registry.py:63-371`; `domain/models.py:223-408`).
- `OnboardingService` remains the post-auth/team/jurisdiction/identifier caller and
  per-case binder (`services/onboarding.py:251-436`).
- The case repository remains UUID/team-owned case evidence and cannot safely own
  backend-global cross-case reuse.
- The mutable policy catalogue is not reused, avoiding new operator mutation and
  retroactive policy behavior.

One `RegistryAcquisitionCoordinator` is therefore justified as the sole hit/miss/stale
and process-local single-flight owner, and one `RegistrySnapshotRepository` port is
justified as the sole shared snapshot owner. Existing authorization, jurisdiction,
router, provider adapter, mapper, case repository, reconciliation, ownership, workflow,
deletion, and target-ledger owners remain unchanged. No direct API-to-persistence,
provider-to-case-store, ACRA-to-target, second router, second ownership engine, second
authorization owner, or replay bypass is introduced.

### Disabled behavior, locking, and resource bounds

Disabled mode is literal: it performs no cache read/write, requires no cache collection
or index initialization, and adds no cache-specific startup dependency. It preserves
current retrieve-for-each behavior and is not a fallback after enabled Mongo failure
(`PHASE_16_EXECUTION_ADDENDUM.md:46-47`;
`REGISTRY_CACHE_FRESHNESS_PROFILE.md:21-31`). Sandbox behavior remains unchanged and
cannot use the cache.

The lock contract is deterministic enough to implement and falsify:

1. the existing case/establishment lock is acquired before the registry-key lock;
2. cache code never acquires a case lock;
3. waiters register before blocking;
4. all success/failure paths release in `finally`;
5. a key entry retires only after the holder and every registered waiter finish; and
6. waiters re-read/re-evaluate under the lock rather than relying on the first result.

Barrier/event tests are required for same-key single-flight, independent different-key
progress, failure release, and lock retirement. The lock map is bounded by active
operations, not historical identifiers. Persistent storage truthfully remains
unbounded over the provider keyspace: one current entry per exact key, with no TTL,
purge, scheduler, eviction, or globally bounded-capacity claim. Cross-process duplicate
provider calls remain possible; unique identity and CAS protect stored state without a
distributed exactly-once claim.

### Entropy and retirement

The delta is proportionate: one coordinator, one repository port, memory/Mongo
adapters, one separate collection, one disabled/Mock mode, one key descriptor, and one
case compatibility path. Retrieve-each is retained for a proven compatibility reason
as disabled mode, not as an error fallback. There is no previous cache owner to retire.
Redis, connector-side caching, raw/per-operation caches, distributed locking,
transactions, background refresh, forced refresh, live/sandbox caching, and
existing-case refresh are explicitly rejected or deferred behind new authority. ADR-002
is required and present as `Proposed`; it may advance only with the later accepted
implementation.

## Persistence assessment

### Schema, readers, writers, and compatibility

| State | Canonical owner / key | Version | Compatibility rule |
|---|---|---:|---|
| Shared complete registry snapshot | `RegistrySnapshotRepository` / deterministic exact-key digest | cache v1 | Strict decode; no repair/read fallback; provider mismatch is adjacent miss, returned key mismatch is corruption |
| Per-case evidence/workflow | Existing case repository / canonical case UUID | case v4 | New writes use v4; strict v1/v2/v3 ordinary reads supply binding `None` without version-only write |
| Interrupted legacy aggregate | Existing `MongoCaseStore` startup recovery | resulting case v4 | CAS-write only after an independently detected semantic recovery; binding stays `None`; no provider/target replay |

The cache document retains decoded key fields and revalidates them against the SHA-256
identity. Complete-bundle validation covers all four ordered operation provenances,
identity, source/environment, contract/data-set namespace, bounds, and timestamps.
Unknown versions, malformed or extra fields, wrong identity, mixed evidence, and
impossible binding combinations fail closed. Shared cache state and case state remain
independent aggregates with no cross-collection transaction claim.

### CAS, create/update, restart, deletion, and anti-resurrection

- Cache create is insert-only at revision 0; replacement is update-only against exact
  `_id` and expected revision, without upsert, overwrite, or automatic conflict retry.
- A same-key insert collision or replacement conflict returns
  `REGISTRY_CACHE_CONFLICT`; the losing fetched value cannot bind a case.
- Corrupt data is not deleted, repaired, or treated as a miss. Read/write/startup
  failure is sanitized and never falls back to memory.
- A complete shared write may remain after later case-establishment rollback because
  the snapshot is not case-owned; this is explicit, not accidental partial commit.
- Memory restart misses. Enabled Mongo restart strictly initializes/index-validates and
  may hit a valid entry without Registry or target replay.
- Case deletion remains case-only and never cascades to the shared snapshot. Cache
  replacement cannot mutate old case evidence. Existing case updates remain
  update-only/CAS, so a stale case writer cannot recreate a deleted case.
- The shared snapshot repository has no runtime delete operation in Phase 16. Expiry is
  ineligibility, not deletion.

These rules preserve current identity/CAS/create/update/delete and no-resurrection
invariants while adding no second case persistence model.

### Physical Mongo safety and testability

The design is physically testable through the existing guarded runner after its planned
bounded extension:

- add exactly `clm_p16_<24 lowercase hex>` to the allowlist and generator;
- add one explicit Phase 16 physical suite and derive suite reporting from
  `len(PHYSICAL_SUITES)` rather than the current hard-coded four;
- cover insert collision, fresh restart hit, one-microsecond timestamp boundary parity,
  stale CAS conflict, invalid schema/key identity, enabled startup failure, exact legacy
  read/recovery behavior, case-delete independence, and stale anti-resurrection;
- clean only the generated validated database and prove its absence without printing a
  URI or credential.

Current source does not yet allow `p16` (`scripts/mongo_test_safety.py:11-32`) and the
runner currently owns four suites (`scripts/run_physical_mongo_tests.py:16-23,183`).
Those are expected implementation changes, not unresolved design choices. Physical
Mongo infrastructure was unavailable in this re-review, so no physical behavior is
claimed. Its absence must block later durable implementation acceptance if it remains
unavailable; it does not block this now-deterministic pre-implementation design.

## Verification disposition

Fresh read-only checks on the reviewed tree:

- `python scripts/dev_context.py` — PASS; branch/HEAD/origin and current provider/
  persistence classifications reported.
- `python scripts/check_architecture.py` — `ARCHITECTURE CHECK: PASS`.
- `python scripts/check_project_state.py` — `PROJECT STATE CHECK: PASS`.
- `python -m pytest apps/backend/tests/test_phase12_persistence.py::test_schema_v2_read_receives_legacy_policy_snapshot_without_rewrite -q` — PASS (`1 passed`).
- Direct current-serializer microsecond probe — PASS; exact `.123456Z` retained.
- Source inspection — current owner direction, strict bundle states, legacy decode,
  semantic startup recovery, insert/update/CAS/delete boundaries, and physical harness
  safety verified against `cab05d7...`.

Covered scope: deterministic closure of the three prior design findings and re-review
of owner split, disabled behavior, lock/resource claims, schema/compatibility,
CAS/restart/deletion, and physical testability. Confidence: high for design readiness.

Uncovered scope: no Phase 16 implementation exists; no backend/full regression, Ruff,
mypy, security, physical Mongo, lifecycle, or independent implementation QG was run or
claimed. Those remain mandatory on the exact implemented revision.

## Residual risks and next authorized action

- No blocking architecture or persistence finding remains for the approved synthetic
  Mock-only scope.
- Physical Mongo availability is a mandatory later evidence dependency. The
  implementation must stop before durable acceptance if the guarded suite and cleanup
  proof cannot run.
- Any sandbox/live caching, public/forced refresh, existing-case reassessment,
  production sharing/retention/deletion, operator-editable freshness, multi-process
  single-flight, or provider-effective timestamp expands authority and requires a fresh
  design review.
- Because both required verdicts are `PROCEED`, the next authorized action is the
  planner's domain/configuration implementation slice on an authorized feature branch,
  followed by the repository, coordinator, integration, adverse, physical Mongo, and
  independent-QG sequence. This report grants no commit, push, PR, merge, or publication
  authority.
