# Registry Cache Freshness Profile

## Status and authority

Current behavior includes the owner-authorized 2026-10-05 database-first amendment
below (D-069 / ADR-010). The preceding Phase24C amendment covers schema2 operation-prefix and
definitive-negative reuse, frozen ACTIVE per-case freshness/negative-TTL policy,
and separate synthetic-Mock/official-Marketplace-Mock dataset namespaces. Earlier
Phase16 schema1/complete-only/fixed-policy paragraphs record compatibility history;
they do not override that amendment. Sandbox/Live cache remains prohibited.

This is a project-owner-approved, provisional POC profile for synthetic Mock ACRA data.
It is not an ACRA contract, a sponsor-confirmed validity or retention policy, production
licensing authority, or evidence of live interoperability. Sandbox and live registry
caching are prohibited.

## Scope

Phase 16 may reuse only a complete normalized `RegistryAcquisitionBundle` created by the
existing four-operation Mock ACRA adapter. The cache is backend-global and has no public
cache route or administration surface. The existing authorized case response may expose
only a minimized case-bound use projection: disposition, binding time, computed expiry,
and the fixed policy ID/version/duration/comparator. That projection is available only
for a retained Mock binding and excludes cache identity, key, revision, write/anchor
times, fingerprints, repository details, endpoints, source references, and raw payloads.
Cache use occurs only after authorization/team creation, jurisdiction resolution,
provider routing, and identifier eligibility succeed.

The cache never stores raw provider responses, URLs, credentials, documents, human
corrections, case state, reconciliation, ownership, readiness, target payloads, or target
outcomes.

## Configuration

- `registry_cache_mode` is `disabled` by default and may be `mock` only.
- Enabled Mock mode requires exactly `7_776_000` seconds: 90 elapsed 24-hour periods.
- The fixed duration is not three calendar months and has no provider or production
  policy meaning.
- Disabled mode performs no cache read/write and requires no cache-specific startup
  dependency.
- The Mongo cache collection is distinct from all case and administration collections.
  A collision or invalid enabled configuration fails startup; Mongo never falls back to
  memory.

## Exact key and provider identity

Each key contains the normalized eligible identifier plus exact provider code, source
environment, acquisition-contract version, and synthetic data-set namespace. Initial
values are ACRA, MOCK, the Phase 10 acquisition contract, and the versioned Mock fixture
namespace. A deterministic SHA-256 digest of canonical serialized key fields is the
Mongo identity; decoded fields are retained and revalidated against that digest.

Case, team, user, URL, credentials, and freshness duration are not key fields. A
provider/environment/contract/data-set mismatch is an adjacent miss. A repository value
returned for the requested digest but inconsistent with that key is corruption.

## Entry and completeness

Cache schema v1 contains one frozen complete bundle, its exact key and digest, a CAS
revision, the earliest of the four operation retrieval times as freshness anchor, an
optional authoritative provider-effective time (absent for current Mock), and the
coordinator write time. All four operation provenances are required and individually
validated as timezone-aware UTC.

Only a complete bundle may be inserted or replace an entry. Partial, failed, malformed,
wrong-identity, mixed-provider/environment, reordered, or incomplete evidence is never
cached. One current entry exists per exact key. Replacement is update-only and requires
the expected revision; insert is create-only. Neither path uses upsert.

## Freshness and timestamp semantics

Freshness is evaluated under the per-key lock at the actual binding/use point:

```text
freshness_anchor = minimum(all four operation provenance retrieval times)
expires_at       = freshness_anchor + 7_776_000 seconds
eligible         = evaluation_now < expires_at
stale            = evaluation_now >= expires_at
```

Every operation timestamp, the anchor, and the cache write time must not be in the
future relative to the injected evaluation clock. No clock-skew tolerance is implied.
The bundle `retrieved_at` remains the latest operation retrieval time; it is never
rewritten to the cache write or use time.

Memory and Mongo round trips preserve identical UTC instants. The cache document encodes
each datetime as canonical UTC ISO-8601 text with its full supplied microseconds, using
the same lossless datetime representation as the current case-envelope store. BSON Date
is deliberately not used for operation provenance, bundle `retrieved_at`, freshness
anchor, optional `provider_effective_at`, cache `written_at`, case
`bound_to_case_at`, or computed `expires_at`. No field is rounded or truncated.

On decode, each text value is strictly parsed as timezone-aware UTC and its domain value
must equal the pre-write value. Freshness uses the unchanged decoded operation
provenance, derives the minimum anchor again, and derives expiry by exact timedelta
addition. Physical tests use sub-millisecond values and prove identical domain values
and the same fresh result one microsecond before expiry and stale result exactly at
expiry before and after restart.

## Case binding and compatibility

Each successful enabled-cache use receives a defensive deep copy of the complete bundle
and an immutable use binding that records `PROVIDER_FETCH` or `CACHE_HIT`, exact
provider/key/policy identity, committed entry revision, the original retrieval/anchor/
write times, binding time, and computed expiry. `PROVIDER_FETCH` means the complete
provider result was successfully inserted or CAS-replaced before binding; an
uncommitted fetched value cannot produce a binding. A binding never claims re-retrieval
or re-verification at cache-use time.

Case schema v4 stores the binding. Ordinary exact v1/v2/v3 decoding sets it to `None` in
memory and performs no write solely because of the version or absent field. Existing
startup recovery remains authorized to CAS-write a legacy aggregate only when it also
performs its already-owned semantic interruption recovery; the resulting current-schema
record retains `None` and recovery makes no Registry or target call.

`None` means only that no successful enabled-cache binding was recorded. It can describe
a legacy case, disabled mode, an explicit provider-identity bypass, a partial/failed
bundle, or an early/cache failure; callers must not infer which. A later shared refresh
cannot mutate an existing case or any of its evidence, decisions, ownership, readiness,
or target state.

The browser renders `None` as unrecorded/unknown and does not infer a miss, disabled
cache, provider fetch, freshness, or current validity. Original provider/environment and
operation retrieval times remain sourced from the separately minimized registry
acquisition projection. The binding projection never turns the provisional fixed Mock
expiry into an ACRA validity, compliance, retention, or present-freshness claim.

Schema-v4 validation enforces this matrix:

| Outcome | Acquisition | Canonical entity | Binding |
|---|---|---|---|
| Fresh cache hit | complete defensive copy | matching entity | required `CACHE_HIT` with committed cache identity/revision |
| Complete provider fetch and successful cache insert/replace | complete defensive copy | matching entity | required `PROVIDER_FETCH` with committed cache identity/revision |
| Disabled mode or provider without explicit cache identity | current provider result | current behavior | `None` |
| Entity not found | `None` | `None` | `None` |
| Partial provider bundle | retained partial bundle | retained entity under current behavior | `None` |
| Failed provider bundle | retained failed bundle | retained entity under current behavior | `None` |
| Invalid entry or cache read failure | `None` | `None` | `None` |
| Complete fetch followed by cache write/CAS failure | `None` | `None` | `None` |

Whenever a binding exists, schema validation requires a complete acquisition, matching
case/acquisition identifier and entity, exact provider/environment/contract/data-set and
cache digest identity, matching original retrieval/anchor/write/expiry values, and a
valid committed revision. A non-complete acquisition forbids a binding. A complete
acquisition with no binding is permitted only because disabled/bypass behavior must
remain compatible; it carries no cache-use implication.

## Failure and replacement behavior

- Miss: fetch through the existing ordered provider adapter, insert only on complete
  success, then bind the new case.
- Fresh hit: make zero provider calls and bind an independent bundle copy.
- Stale: fetch while retaining but never serving the old entry; replace by CAS only
  after complete success.
- Corrupt/invalid entry: `REGISTRY_CACHE_INVALID`; do not delete, repair, treat as miss,
  or call the provider.
- Read failure: `REGISTRY_CACHE_READ_FAILED`; make zero provider/downstream calls.
- Write failure: `REGISTRY_CACHE_WRITE_FAILED`; do not return or persist the fetched
  uncommitted acquisition/entity/binding on the case and do not progress downstream.
- CAS conflict: `REGISTRY_CACHE_CONFLICT`; no retry loop or overwrite.
- Provider partial/failure: preserve current sanitized outcome and ordered call stopping;
  do not insert/replace and never serve stale.

Messages and logs contain only stable safe codes/context, never raw provider data,
endpoints, authorization, Mongo URI, or private exception detail.

## Concurrency and retention

The coordinator uses one process-local lock per exact key. The caller's case or
establishment lock is acquired first; cache code never acquires it. Waiters register
before blocking, all paths release in `finally`, and a lock entry is retired only after
the holder and registered waiters finish. The lock map is bounded by active operations,
not identifier history. Different keys do not block each other.

This provides single-process single-flight only. Across processes duplicate provider
calls remain possible; a unique key and CAS protect stored state but do not establish
distributed exactly-once behavior. There is no cross-collection transaction.

Expiry is ineligibility, not deletion. Case deletion never deletes a shared snapshot.
There is no TTL index, purge endpoint, history collection, scheduler, eviction rule, or
claim that the overall provider keyspace is bounded.

## Deferred or prohibited extensions

Forced refresh, existing-case reassessment, scheduled/OCDD/perpetual-KYC refresh,
sandbox/live storage, production cross-team sharing, retention/deletion policy, and
provider-effective timestamps require separate authority and design review.

## Phase24C normalized operation/negative cache amendment — 2026-10-02

D-064 supersedes the complete-only write and fixed-runtime-duration limitations for the
explicitly enabled Mock cache. Configuration remains disabled by default, with explicit
mock mode and the unchanged 90-day baseline configuration. Approved case-bound business
parameters control use: freshness days 1..365 (default90); definitive NOT_FOUND TTL
seconds 1..3600 (default600). Historical case parameters absent retain fixed90days/600s;
new cases freeze ACTIVE parameters and version. Sandbox/Live remain prohibited.
The existing official API Marketplace Mock may opt in with a distinct
ACRA_API_MARKETPLACE_MOCK_V1 namespace; synthetic Mock remains MOCK_ACRA_SYNTHETIC_V1.
Neither lane falls back or shares evidence across namespaces.

Schema1 remains complete-only. Explicit schema2 retains normalized successful operation
prefixes (including FAILED/PARTIAL bundles with failed operations never reusable), or
only definitive NOT_FOUND (no acquisition, anchor equals write time). Required empty
ownership/relationship operations are reacquired; optional empty officers may be reused.
Only COMPLETE evidence gets a case binding. ENTITY_PROFILE expiry invalidates the
operation reuse set; unavailable ownership invalidates relationship reuse. Freshness is
exclusive at exact expiry and rechecked at actual binding after acquisition. Expiry
crossing during acquisition fails safely without committing/binding stale evidence.
Only definitive absence is negative; timeout/TLS/malformed/uncertain failures are not.

Schema3 (D-079 candidate) holds only shareholder evidence read without an entity profile.
- **Key:** the same provider identity, with acquisition contract
  `MARKETPLACE_SHAREHOLDERS_V1`.
- **Contents:** no acquisition and no negative result. The anchor equals the operation
  retrieval time.
- **Freshness:** COMPLETE evidence follows the case freshness policy and EMPTY evidence the
  definitive negative TTL. A FAILED operation is never written.
- **Unchanged:** the same exact-key locks, CAS revisions and strict decoding apply, and
  schema1/schema2 keys and meanings are unchanged.
- **Rollback:** schema1/schema2 documents written by this version serialize
  `shareholder_evidence` as null, so an earlier version reading them fails closed.

One process-local exact-key owner suppresses active same-key calls, with max256 keys,
max64 registered users per key and max45s waiter deadline (bounded test seams). Cancellation
before/post acquisition commits no result; locks retire after the last user. Error or
incomplete results shared within a registered cohort never become negative cache hits;
partial results are rechecked under each caller's frozen freshness policy. There is no
distributed lock/exactly-once claim, provider retry loop, TTL deletion or retention policy.
CAS validates the entire returned entry; insert-only/update-only/no-upsert and UTC
microsecond-preserving storage remain. Normal tests use fake transports only.

## Database-first manual-UAT amendment - 2026-10-05

D-069 supersedes the disabled default for ordinary non-production Mock lanes. `auto`
enables the same coordinator/repository and configured Mongo collection. Explicit
`disabled` remains a deliberate override; legacy `mock` retains exact baseline validation.
Auto does not enable generic Sandbox or production caching. Historical schema and
case bindings retain their original identities and frozen policy.

After authorization, jurisdiction, route and UEN checks, the coordinator can read one
explicit approved seed identity: ACRA/MOCK/PHASE10_ACQUISITION_V1/LOCAL_SYNTHETIC_UAT_V1.
This lookup is admitted only for the two existing Mock provider namespaces under the
same acquisition contract. It is separate from the provider key, not an alias or
network-produced evidence. COMPLETE validated exact-UEN evidence plus exclusive bounded
freshness yields CACHE_HIT and a defensive case copy, with original seed times and
local-synthetic references. Failed, incomplete, expired or missing seed evidence is
never bound or partially mixed into the provider namespace. Normal provider acquisition
and its existing partial/negative cache semantics then apply. Unknown/malformed stored
evidence still fails closed; no corrupt entry is overwritten or interpreted.

The eight fixture definitions live in scripts/zero_touch_happy_path_fixtures.py.
Seed creates only these eight keys through the existing repository, checks deterministic
content before writes, leaves fresh matching entries untouched and CAS-refreshes only
expired matching entries. Production and unallowlisted databases are refused before
connection. `--check` performs no writes or index initialization. No raw HTTP payload,
SSIC field invention, personal identifier, GoldTier seed, legal UBO or retention claim.

An authorized reconciliation legal-name selection that changes canonical entity clears
only its active registry equality binding. The original acquisition bundle and shared
cache entry remain unchanged; the reconciliation decision remains separately retained.
The unchanged-name path retains its binding. This preserves existing correction behavior
with the ordinary cache default without weakening the binding validator.


## Synthetic company pack correction - 2026-10-09

Orion, Pacific, Straits and Meridian extend the existing LOCAL_SYNTHETIC_UAT_V1
seed owner. The configured normal provider remains api_marketplace_mock. A fresh
COMPLETE exact-UEN seed is a CACHE_HIT with zero Marketplace token/HTTP operations;
missing or stale seeds proceed to the configured provider through the same coordinator.
The browser binding adds nullable synthetic_seed_namespace, allowlisted only to
LOCAL_SYNTHETIC_UAT_V1 when the full retained identity equals the approved local seed
identity. Private keys, arbitrary namespaces, endpoints and contract identifiers remain
private. Original evidence references and provider configuration are not relabelled.

## Corporate-owner issuer reuse - D-076 candidate, 2026-10-23

Recursive ownership discovery reads each corporate owner's own registry evidence through
the same coordinator, exact key and case-frozen freshness/negative policy, via the
read-only `OnboardingService.acquire_subsidiary_registry_evidence()`. A fresh COMPLETE
snapshot (including the approved local seed) is a CACHE_HIT with zero provider calls; a
miss or stale entry uses the configured provider once and is saved under the existing
insert/CAS rules. The result is never bound to, or written onto, any case; only the
derived ownership graph records it. Read/write/CAS/invalid cache failures leave that
corporate branch unresolved for review rather than serving or overwriting evidence.

The local synthetic namespace advances to `MOCK_ACRA_SYNTHETIC_V2` because Garden's
record changed shape (direct owners only). Existing V1 entries are not deleted,
reinterpreted or reused; historical cases keep their bound V1 evidence. The seed lookup
is admitted for `MOCK_ACRA_SYNTHETIC_V2` and `ACRA_API_MARKETPLACE_MOCK_V1` only.
