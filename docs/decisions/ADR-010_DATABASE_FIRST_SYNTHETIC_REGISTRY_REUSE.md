# ADR-010 - Database-first synthetic registry reuse

## Status

Proposed; explicit owner-authorized POC remediation, pending independent gate and human review.

## Date

2026-10-05

## Context

The owner requires fresh complete database registry evidence before ACRA acquisition, and four controlled synthetic happy paths. ADR-002/D-064 already assign exact-key acquisition and persistence to the registry coordinator/repository. Disabled-by-default configuration prevents ordinary reuse. Marketplace sample catalogues are operation-specific, not coherent whole-company fixtures.

## Decision

Extend existing owners. Default `REGISTRY_CACHE_MODE=auto` enables the existing cache in non-production synthetic/official Mock lanes. Explicit `disabled` remains an operator override; explicit legacy `mock` retains its validation. Generic Sandbox and production auto mode perform no cache use. Baseline freshness remains 90 elapsed days, overridden at use only by frozen approved case policy.

Before configured-provider cache/acquisition, the coordinator checks exactly ACRA/MOCK/PHASE10_ACQUISITION_V1/LOCAL_SYNTHETIC_UAT_V1 (using the adapter's actual contract constant) for the exact normalized UEN. Only a fresh COMPLETE validated normalized bundle can bind. It retains synthetic local references, original seed timestamps and that distinct dataset key; CACHE_HIT never claims network acquisition. Miss, expiry or incomplete seed proceeds to the provider's own exact namespace; no seed prefix is mixed into provider results. Malformed stored evidence fails closed. No name/UEN-specific production branch is introduced.

## Alternatives considered

Retrieve-each or hidden opt-in cannot meet ordinary reuse. Putting seeds under the official namespace would misstate source. A second database/cache owner or raw fake HTTP persistence duplicates ownership. A read-only approved synthetic identity inside the existing coordinator preserves the boundary.

## Consequences

Non-production Mock runtime reads database-backed normalized evidence automatically. No new collection, dependency, HTTP endpoint, frontend cache, legal retention claim or Live classification. Manual seed refresh is bounded and CAS-controlled; expiry falls back to configured ACRA and does not extend freshness silently.

## Architecture invariants affected

One registry coordinator/repository, source-to-canonical-to-target flow, one Decimal graph engine and ledger-owned no-replay preserved. Exact provider/environment/contract/dataset/UEN isolation gains one explicitly approved synthetic lookup.

## Security and persistence implications

Shared schema1/2 and case schema9 unchanged. Insert-only create/update-only revision CAS, strict decode, defensive copies and auth gates preserved. Seed CLI rejects production and unsafe database names before connection, never reads .env or prints connection details, and touches only four fixture keys.

## Migration and retirement implications

No migration/read rewrite. Old explicit disabled/mock settings remain supported. Existing fixture namespaces stay distinct. Rollback to prior code disables ordinary auto reuse; current binary supports explicit disabled override.

## Verification

Focused absence/failure, exact-key/freshness/copy, seed conflict/idempotence, four Decimal/OCR/target journeys; guarded physical Mongo restart/CAS/cleanup; affected E2E; full backend/frontend/type/build/security/contracts/governance; fresh independent gate.

## Revisit conditions

Production/subscriber source or retention authority, new dataset, schema, distributed concurrency or altered freshness requires new review.

## Related contracts and sponsor questions

REGISTRY_CACHE_FRESHNESS_PROFILE, PERSISTENCE_RECOVERY_PROFILE, ADR-002, D-064, D-069; Q-012/Q-015/Q-016 remain open beyond this POC.

An authorized reconciliation legal-name selection that changes canonical entity clears
only its active registry equality binding. The original acquisition bundle and shared
cache entry remain unchanged; the reconciliation decision remains separately retained.
The unchanged-name path retains its binding. This preserves existing correction behavior
with the ordinary cache default without weakening the binding validator.
