# Phase 16 — Independent Architecture and Persistence Review

## Verdict

**ARCHITECTURE REVIEW: REVISE**

**PERSISTENCE CHANGE: STOP**

The proposed ownership split is justified and preserves the current dependency
direction, but the persistence contract is not yet deterministic enough to implement
without guessing. Two blocking design ambiguities remain: exact timestamp preservation
versus millisecond-normalized Mongo persistence, and schema-v4 binding/null semantics
for non-complete acquisition outcomes. A third compatibility ambiguity must also be
resolved so that the new no-rewrite promise does not disable the existing authorized
startup-recovery write.

This is a pre-implementation review, not a quality gate or behavioral acceptance. No
reviewed artifact was remediated. The only review-authored file is this report.

## Review identity and preflight

- Role: fresh independent pre-implementation architecture/persistence reviewer.
- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`.
- Branch: `phase/16-registry-cache-freshness-planning`.
- Assigned `BASE_SHA`, current `HEAD`, observed `origin/main`, and merge base:
  `cab05d7dc98d4c50c8fc096835fe49802d5896e2`.
- Current source revision: the SHA above. The reviewed design is uncommitted working-tree
  content layered on that source revision.
- Behavior tested by this review: none. `python scripts/dev_context.py` passed as a
  context/baseline check; no result from an earlier revision is transferred as current
  behavior evidence.
- Tools/runtimes observed: worktree-scoped filesystem access, PowerShell, Git 2.55.0,
  Python 3.12.10, Node 22.23.2, npm 10.9.8, `rg`, and Docker CLI 29.8.0.
- Physical Mongo was unavailable in this session: `PHASE12_MONGO_URI` was absent and no
  `mongod` executable was found. No database, browser, port, lifecycle process, provider
  endpoint, `.env`, credential, private sponsor artifact, sibling worktree, or
  `clm_poc` was accessed.
- Current worktree before this report contained the six reviewed Phase 16 artifacts,
  plus two Aegis work-state files outside the reviewed design set. Existing work was not
  modified, moved, staged, committed, or cleaned.

### Exact reviewed design content

The verdict applies to these exact SHA-256 contents:

| SHA-256 | Path |
|---|---|
| `966c2063181857a9598c5b3d276792cc5ba375a8fd327583bc0d4ba19d81efcd` | `.ai-pipeline/001_planner/PHASE_16_REGISTRY_CACHE_FRESHNESS.md` |
| `30059937abb8ef484941540b5c749188a305aa2882e5e448cbf4f0f8df80fcf8` | `.ai-pipeline/001_planner/PHASE_16_EXECUTION_ADDENDUM.md` |
| `6d80a1e55394a95c5b3feaa8a1344f2bfdbf2c17d7dc0cbed8d2a5fb5581ea70` | `docs/contracts/REGISTRY_CACHE_FRESHNESS_PROFILE.md` |
| `ff881bc7037b7494cfdcf99bd61a4334626d95707f46a71abf5f9109609c039b` | `docs/decisions/ADR-002_REGISTRY_SNAPSHOT_CACHE.md` |
| `ff217546273b29098b30b3b66b6adec90b1a90c09798c5777cafe2f5146d20fc` | `docs/decisions/DECISION_LOG.md` |
| `b4ea326764e01a8751366d0a3b7d13206db0abeff98c32018455fb3889d66fb9` | `docs/contracts/README.md` |

Any change to those contents requires a fresh review of the changed scope.

## Requirement and change classes

The approved bounded requirement is a disabled-by-default, synthetic-Mock-only shared
registry snapshot cache with a fixed `7_776_000`-second exclusive freshness boundary,
exact provider/contract/dataset key isolation, immutable per-case evidence, memory/Mongo
parity, and no public refresh surface. O-16-01 through O-16-04 provide provisional
project-owner authority in
`.ai-pipeline/001_planner/PHASE_16_EXECUTION_ADDENDUM.md:5-25`; D-044 records the same
bounded non-production decision in `docs/decisions/DECISION_LOG.md:55`.

Applicable implementation classes are `BACKEND_DOMAIN`, `PERSISTENCE`,
`EXTERNAL_PROVIDER`, `ARCHITECTURE_REFACTOR`, and `CI_TOOLING`. No frontend, public API,
forced-refresh, sandbox/live, existing-case reassessment, scheduled refresh, production
retention, or distributed-execution change is authorized.

## Architecture review

### Existence check

The new focused owner is justified:

- `RegistryProviderRouter` currently owns only closed jurisdiction-to-provider routing
  (`apps/backend/app/connectors/registry.py:381-409`); adding state/freshness there would
  duplicate application coordination.
- `AcraRegistryProviderAdapter` owns strict four-operation acquisition and normalized
  bundle construction (`apps/backend/app/connectors/registry.py:79-371`); adding
  persistence/freshness there would mix provider translation with cache policy and could
  be invoked before application gates.
- `OnboardingService` owns the post-route binding checkpoint and currently calls the
  selected provider only after jurisdiction, routing, and identifier eligibility
  (`apps/backend/app/services/onboarding.py:316-365`). It is the correct caller, but
  placing repository, freshness, and keyed-lock behavior directly in this hotspot would
  create responsibility overlap.
- `OnboardingCaseRepository` is case-UUID-owned, team-bound durable evidence
  (`apps/backend/app/services/repository.py:12-30`; `apps/backend/app/persistence/models.py:161-183`),
  so it cannot safely own backend-global cross-case reuse.
- The existing mutable policy catalogue would introduce operator mutation/RBAC and
  retroactive shared-cache behavior outside Phase 16.

Conclusion: one `RegistryAcquisitionCoordinator` plus one
`RegistrySnapshotRepository` port is the smallest non-duplicative boundary. There is no
remaining ambiguity about who owns cache decisions or shared snapshot state.

### Dependency and owner map

The proposed direction is valid:

```text
authenticated case creation / existing team authority
  -> OnboardingService jurisdiction + identifier gates
  -> existing RegistryProviderRouter
  -> new RegistryAcquisitionCoordinator
       -> one RegistrySnapshotRepository port
       -> existing selected RegistryProvider on miss/stale
  -> immutable case-owned bundle + binding
  -> existing reconciliation / ownership / readiness / target owners
```

The plan and ADR expressly preserve router, adapter, mapper, case repository,
authorization, reconciliation, ownership, workflow, deletion, and target-ledger owners
(`PHASE_16_REGISTRY_CACHE_FRESHNESS.md:288-300`;
`docs/decisions/ADR-002_REGISTRY_SNAPSHOT_CACHE.md:27-42`). The cache contains only a
strict complete normalized bundle and never raw provider DTOs, URLs, credentials,
documents, case state, ownership conclusions, or target state
(`docs/contracts/REGISTRY_CACHE_FRESHNESS_PROFILE.md:10-19,45-56`). No route-to-storage,
provider-to-case-store, direct ACRA-to-target, second ownership engine, second router,
second authorization owner, or target-ledger bypass is proposed.

### Locking and resource bounds

The lock design is directionally complete: the case/establishment lock is acquired
first; cache code never acquires it; waiters register before blocking; release occurs in
`finally`; and retirement waits for the holder and registered waiters
(`PHASE_16_EXECUTION_ADDENDUM.md:29-39`;
`REGISTRY_CACHE_FRESHNESS_PROFILE.md:111-121`). A correct implementation can therefore
use a guarded per-key entry/reference count without a waiter-retirement race. Required
barrier/event tests are listed at `PHASE_16_REGISTRY_CACHE_FRESHNESS.md:655-686`.

The resource claims are also truthful rather than falsely finite:

- process-local lock state is proportional to currently active distinct keys and their
  registered users, not historical identifiers;
- the persistent snapshot collection is one current entry per exact key but the global
  provider keyspace is explicitly unbounded;
- no eviction, TTL, purge, scheduler, or bounded-capacity claim exists
  (`PHASE_16_EXECUTION_ADDENDUM.md:38-42`;
  `REGISTRY_CACHE_FRESHNESS_PROFILE.md:123-125`).

No distributed lock, transaction, lease, outbox, or exactly-once guarantee is claimed.
Across processes duplicate provider calls remain possible and only unique identity plus
CAS protect stored state (`REGISTRY_CACHE_FRESHNESS_PROFILE.md:119-121`).

### Entropy, compatibility, and retirement

The intended entropy is proportionate: one coordinator, one port, memory/Mongo
adapters, one separate collection, one disabled/Mock mode, one exact key descriptor, and
one case-schema compatibility path. Retrieve-each is intentionally retained as the
disabled behavior, not as a failure fallback; there is no legacy cache owner to retire.
Forced refresh, live/sandbox caching, per-operation caches, raw-response caches, Redis,
background work, and existing-case refresh are excluded. The ADR is required by the
workflow and is correctly present as `Proposed` pending a reviewable final decision.

The owner/dependency design would be eligible for `PROCEED` once the persistence
semantics below are reconciled. Because those semantics cross the coordinator, shared
repository, case schema, and restart boundary, the current architecture verdict is
`REVISE`, not a conditional approval to implement.

## Blocking findings

### P16-APR-001 — HIGH — Exact provenance and millisecond persistence are underspecified and internally inconsistent

**Evidence.** The contract defines `freshness_anchor` as the exact minimum of all four
operation provenance times and `expires_at = anchor + 7_776_000 seconds`
(`docs/contracts/REGISTRY_CACHE_FRESHNESS_PROFILE.md:58-77`). It simultaneously requires
memory/Mongo round trips to preserve equivalent UTC instants, Mongo values and derived
binding/expiry values to be normalized to millisecond precision, and original accepted
provider provenance not to be altered. The addendum repeats those obligations without
defining representation or rounding (`PHASE_16_EXECUTION_ADDENDUM.md:29-35`). The current
Mock connector supplies ordinary Python `datetime.now(UTC)` values, which may contain
microseconds (`apps/backend/app/connectors/mock_acra.py:48-49,109-120,137-143`), while the
current case store preserves datetimes as lossless ISO text rather than BSON Date
(`apps/backend/app/persistence/mongo_case_store.py:532-554`).

**Why this blocks.** If the new store writes the bundle/anchor as BSON Date, sub-
millisecond provenance is changed after restart. If it preserves the bundle exactly but
truncates the stored anchor, the required equality `anchor = minimum(provenance)` no
longer holds. If only expiry/binding is rounded, the exclusive fresh/stale boundary can
move by less than one millisecond and memory/Mongo behavior can diverge. The reviewed
documents do not state which timestamp fields use BSON Date versus lossless text, where
normalization occurs, whether normalization truncates or rounds, or which value is used
for model validation and freshness after restart. Normalizing test inputs does not
resolve runtime values from the current connector.

**Required revision.** Before implementation, define a field-by-field serialization
matrix for operation provenance, bundle `retrieved_at`, freshness anchor,
`provider_effective_at`, `written_at`, `bound_to_case_at`, and `expires_at`; define the
exact normalization algorithm and point; and prove the same hit/stale decision and
domain values before and after memory/Mongo round trips without mutating original
provider provenance. The contract, ADR/addendum, model invariants, and focused/physical
tests must agree on that one rule.

### P16-APR-002 — HIGH — Schema-v4 binding/null semantics are undefined for partial, failed, and post-fetch write-failure cases

**Evidence.** The contract says each new case receives a bundle copy and binding with
`PROVIDER_FETCH` or `CACHE_HIT`, original retrieval/anchor/write times, and computed
expiry (`REGISTRY_CACHE_FRESHNESS_PROFILE.md:79-90`). The planner similarly defines
non-optional anchor/expiry semantics for the binding
(`PHASE_16_REGISTRY_CACHE_FRESHNESS.md:347-365`) and says integration binds metadata
before existing complete/partial/failed handling (line 565). But only complete bundles
may be cached (`REGISTRY_CACHE_FRESHNESS_PROFILE.md:47-56`), provider partial/failure is
retained without insertion (lines 94-106), and a cache-write failure after a complete
fetch must not progress using the uncommitted value (lines 101-103).

Current failed bundles can contain `NOT_ATTEMPTED` operations without provenance
(`apps/backend/app/connectors/registry.py:334-371`), and `OnboardingService` currently
retains partial/failed bundles on the case before stopping
(`apps/backend/app/services/onboarding.py:360-409`). Such cases cannot populate the
specified four-operation freshness anchor, cache write time, or computed expiry. The
new `None` meaning is specified only for legacy v1/v2/v3 reads, not for new schema-v4
failure paths (`PHASE_16_EXECUTION_ADDENDUM.md:45-47`).

**Why this blocks.** An implementer must currently invent whether a new v4 partial/
failed case has no binding, a weakened `PROVIDER_FETCH` binding with optional fields, or
a misleading freshness binding. Cache read failures, invalid entries, entity-not-found,
and complete-fetch/cache-write-failure paths are likewise missing an exact case-evidence
matrix. That changes field requiredness/default semantics, persisted truth, failure
evidence, and compatibility assertions.

**Required revision.** Define, for hit, committed complete fetch, entity-not-found,
partial bundle, failed bundle, invalid/read-failed cache, and complete-fetch/write-
failed cache: whether `registry_acquisition`, canonical entity, and
`registry_evidence_binding` exist; which binding fields are required/absent; the exact
meaning of `None`; and whether the fetched bundle is retained as failed-case evidence.
Then make schema-v4 validation reject every impossible combination.

### P16-APR-003 — MEDIUM — The absolute legacy no-rewrite wording conflicts with existing startup recovery

**Evidence.** The addendum and ADR state that exact v1/v2/v3 reads yield an absent
binding without repair-on-read or rewrite
(`PHASE_16_EXECUTION_ADDENDUM.md:43-47`;
`docs/decisions/ADR-002_REGISTRY_SNAPSHOT_CACHE.md:94-104`). Current decode converts
schema v1/v2 to the current in-memory model without an ordinary read write
(`apps/backend/app/persistence/mongo_case_store.py:233-271`), but startup intentionally
calls `_recover_interrupted` and CAS-replaces any semantically changed snapshot
(`apps/backend/app/persistence/mongo_case_store.py:70-98,390-529`). On a legacy document
that needs authorized interruption recovery, that replacement necessarily writes the
current schema.

**Why this blocks.** Taken literally, the new wording could cause implementation to
disable accepted restart recovery for legacy cases. Preserving current behavior, on the
other hand, violates an unqualified “no rewrite” claim. This is not a reason to add a
migration; it is a reason to distinguish compatibility-only decoding from an existing
semantic recovery write.

**Required revision.** Specify whether “no rewrite” means no write solely because a
legacy version/binding was decoded, while the existing independently triggered restart
recovery may still CAS-write a changed aggregate. Add separate tests for ordinary
v1/v2/v3 reads with zero writes and for legacy interrupted-state recovery, including the
resulting schema version and retained no-provider/no-target-replay behavior.

## Persistence assessment

### Schema and owner map

The intended separation is correct:

| State | Owner/key | Version | Relationship |
|---|---|---:|---|
| Shared reusable registry snapshot | New `RegistrySnapshotRepository`, exact key digest | cache v1 | Backend-global; never case/team/user-owned |
| Per-case evidence and workflow | Existing case repository/envelope, case UUID | case v4 | Deep-copied immutable bundle plus use binding |
| Legacy case documents | Exact v1/v2/v3 readers | legacy | In-memory absent binding; no version-only rewrite |

The ADR explicitly rejects reuse of another case envelope and records no cross-
collection transaction (`docs/decisions/ADR-002_REGISTRY_SNAPSHOT_CACHE.md:39-59`). A
valid shared write may survive failed case establishment, and case deletion does not
cascade (`ADR-002:61-73,87-98`). Those are coherent independent aggregates rather than a
distributed atomicity claim.

### CAS, create, update, delete, and restart

The proposed repository operations preserve the existing persistence constitution:

- create is insert-only at revision 0;
- replacement is update-only against exact `_id` plus expected revision, without
  upsert, retry, or overwrite;
- decoded key fields are revalidated against deterministic `_id`;
- corrupt data fails closed and is not repaired/deleted as a miss;
- Mongo failure never falls back to memory;
- the cache has no runtime delete operation in this phase, while case deletion remains
  case-only and cannot recreate a missing case;
- memory restart misses; enabled Mongo restart strictly decodes entries and may hit;
- no provider or target replay is added.

These decisions are present at `REGISTRY_CACHE_FRESHNESS_PROFILE.md:33-56,92-125` and
`PHASE_16_REGISTRY_CACHE_FRESHNESS.md:462-495`. They are acceptable subject to closing
P16-APR-001 through P16-APR-003.

Disabled mode must be implemented literally: no snapshot read/write, collection/index
initialization, or cache-specific startup failure. The contract states this at
`REGISTRY_CACHE_FRESHNESS_PROFILE.md:21-31` and the addendum at lines 43-44. This is an
acceptance requirement, not permission to create a no-op fallback after an enabled
Mongo failure.

### Physical testability

The proposed physical path is testable and safely bounded once infrastructure exists.
The planner requires a generated `clm_p16_<24 hex>` database, explicit `p16` allowlist,
the Phase 16 physical suite, dynamic runner suite counts, exact cleanup, and absence
proof (`PHASE_16_REGISTRY_CACHE_FRESHNESS.md:589-603,630-632`). Current safety code only
allows p12/p13/p14/p145 (`scripts/mongo_test_safety.py:11-32`) and the current runner
owns four suites with hard-coded wording/count (`scripts/run_physical_mongo_tests.py:16-23,109-183`),
so those planned changes are necessary and correctly scoped.

Required physical evidence must cover insert collision, fresh hit after restart, stale
CAS conflict, invalid schema/key identity, enabled-mode startup failure, case-delete
independence, legacy read/recovery behavior, timestamp round-trip/boundary parity, exact
generated-database cleanup, and verified absence. Because no physical Mongo capability
was available in this review session, no runtime-persistence readiness claim is made.

## Verification disposition

Read-only/source checks performed:

- `python scripts/dev_context.py` — PASS; branch/HEAD/origin baseline and current
  provider/persistence classifications reported.
- Git branch/HEAD/origin/merge-base inspection — all observed at `cab05d7...`.
- Current worktree inventory and SHA-256 freeze of the six reviewed artifacts — PASS.
- Current source, tests, physical harness, accepted Phase 15A cache boundary, and
  accepted Phase 12 persistence evidence inspected.

Not run and not claimed: backend tests, Ruff, mypy, physical Mongo, provider access,
browser tests, lifecycle tests, pre-PR checks, or an independent implementation quality
gate. There is no implementation to test in this review.

After remediation of the three design findings, the fresh re-review should require the
planner's full matrix, including deterministic barrier-controlled lock retirement,
per-operation future-time rejection, exact sub-millisecond round-trip cases, strict
v1/v2/v3 no-version-only-write behavior, v4 impossible-state rejection, Mongo physical
restart/CAS/cleanup evidence, full backend/static/security/governance regression, and a
later independent implementation quality gate.

## Risks, authority, and next action

- No substantive canonical-owner or sponsor-authority ambiguity remains for the
  approved synthetic Mock-only core. O-16-01 through O-16-04 are sufficient provisional
  project authority and do not authorize production/live claims.
- P16-APR-001 and P16-APR-002 are substantive persistence-schema decisions; P16-APR-003
  is a current-source compatibility conflict. The addendum's own stop condition at
  `.ai-pipeline/001_planner/PHASE_16_EXECUTION_ADDENDUM.md:85-91` therefore applies.
- Do not begin the domain/configuration or persistence implementation slice on this
  verdict. Revise only the governing planner/addendum/contract/ADR as needed to make the
  three decisions exact, then obtain a fresh independent architecture/persistence
  re-review.
- Physical Mongo availability remains a later mandatory evidence prerequisite. Its
  current absence does not decide the design, but it blocks eventual durable
  implementation acceptance if not resolved.
