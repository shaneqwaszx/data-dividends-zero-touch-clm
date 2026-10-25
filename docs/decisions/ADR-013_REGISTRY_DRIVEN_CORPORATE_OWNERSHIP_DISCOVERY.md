# ADR-013 — Registry-driven corporate ownership discovery

- Status: Proposed (owner-authorized Stage 1 candidate, 2026-10-23; pending integrated
  acceptance and independent Quality Gate)
- Decision record: D-076
- Change classes: BACKEND_DOMAIN, BACKEND_API, PERSISTENCE, EXTERNAL_PROVIDER (Mock
  fixture/provider parity), FRONTEND_UI

## Context

The ownership boundary loaded one root registry acquisition. The local Mock served
Garden Business (`11111999A`) as one flattened response containing SIM LIM
(`111111111M`) and SIM LIM's own holders, and no SIM LIM issuer profile existed. A
corporate owner therefore could not be acquired from its own registry record, cached
separately, or traced recursively. The owner requested registry-driven recursive
discovery with cache-first lookup, editable case-frozen policy, and no special case in
orchestration.

## Existence check

- `OwnershipAnalysisService` and `calculate_ownership_paths()` remain the only Decimal
  calculator and classifier. Reused unchanged except one additive output: the exact
  root-equivalent share reaching each legal entity without owners.
- `RegistryProviderRouter`, `AcraRegistryProviderAdapter`, `RegistryAcquisitionCoordinator`
  and the snapshot repository remain the only registry route, adapter, cache owner and
  persistence. Reused through a new narrow read-only method
  `OnboardingService.acquire_subsidiary_registry_evidence()`.
- `RegistryAcquisitionOwnershipProvider` keeps root-case loading; its normalization is
  extracted into `acquisition_ownership_source()` so every issuer uses one mapping.
- No existing owner schedules retrieval of additional issuers, so one focused
  `OwnershipDiscoveryCoordinator` is added. It holds no cache, no persistence and no
  classification logic.

## Decision

1. Each corporate owner with a verified Singapore UEN and leaf position in the current
   graph is acquired as its own issuer through the existing coordinator (fresh cache hit:
   zero provider calls; miss/stale: one configured-provider acquisition). Its own direct
   holders attach under issuer-namespaced identifiers; issuer nodes deduplicate by UEN.
2. Retrieval is iterative and bounded: case-frozen trace threshold, corporate depth and
   optional business budget, plus fixed technical caps (32 issuer lookups, 60 s deadline,
   sequential acquisition, existing graph/evidence caps).
3. Branches below the trace threshold are deferred only when a sound global bound shows
   no threshold result can change; any unresolved branch keeps the graph partial and
   the existing REVIEW_REQUIRED/INDETERMINATE classification.
4. Person identity is never inferred across issuer records. Equal source identifiers in
   different issuers raise `PERSON_IDENTITY_UNRESOLVED`; an explicit verified binding
   seam exists but no current provider supplies one.
5. Garden and SIM LIM become separate local Mock issuers. The local synthetic dataset
   namespace becomes `MOCK_ACRA_SYNTHETIC_V2`, isolating flattened V1 cache entries.
   The official Marketplace Mock keeps its separately labelled Garden supplement.
6. Case snapshot schema 11 adds optional `ownership_discovery` policy and ownership
   `discovery` audit; v1-v10 envelopes cannot carry non-null values.

## Consequences

- New Garden cases reach the same Decimal UBO outcome from two issuer records; repeated
  cases reuse SIM LIM's snapshot. Historical cases keep their bound evidence and policy.
- Deferral trades registry calls for human review; it never clears a candidate.
- Each new durable field follows the explicit-version pattern. Rolling back to older
  code cannot read schema-11 envelopes or schema-3 policy catalogues (fail closed).

## Retirement

`derive_garden_ownership()` and `build_garden_supplement()` remain only for the official
Marketplace Mock lane, which has no relationship operation or verified SIM LIM issuer
record. Retire them when an authorized provider exposes separate issuer ownership.

## Amendment — D-077 hybrid direct overlay (candidate, 2026-10-23)

The narrow `SINGLE_SOURCE` discovery gate also admits
`OFFICIAL_MOCK_PLUS_LOCAL_DIRECT_OVERLAY` (never the flattened legacy supplement). The
coordinator gains no cache, repository or classification: for a whitelisted scenario
issuer it still performs the official cache-first lookup and only then attaches declared
direct holders through the same issuer-scoped merge, recording the official lookup
observation and identity basis. The overlay catalogue is a fixture boundary in
`connectors/`; the service validates its LOCAL provenance. `SubsidiaryRegistryEvidence`
reports a fresh definitive NOT_FOUND cache hit as zero provider calls and whether an
incomplete result reused a cached entity profile. Case envelope schema 12 records the new
optional fields; v1..v11 readers reject them. Retire with the overlay when an authorized
provider exposes issuer relationships and denominators.

## Amendment — D-079 official shareholder evidence without an entity profile (candidate, 2026-10-24)

The discovery coordinator stays the single scheduler.
- After a non-overlay issuer's definitive entity-basic NOT_FOUND, it asks the same reader
  for `acquire_subsidiary_shareholder_evidence()`.
- That method answers only in the official Marketplace composition. It goes through the
  existing adapter (`retrieve_shareholder_evidence`) and the single registry coordinator
  (schema 3 entries under contract `MARKETPLACE_SHAREHOLDERS_V1`).
- The rows are kept on the discovery record outside the graph. The engine, path arithmetic
  and threshold classification are unchanged, and the branch stays unresolved.
- Case envelope schema 13 records the new optional fields; v1..v12 readers reject them.
- D-080 (candidate): the same path keeps each row's source share class and currency
  (cache schema 4 under `MARKETPLACE_SHAREHOLDERS_V2`, case envelope schema 14). Owners,
  scheduling and arithmetic are unchanged.
- D-081 (candidate): in the opt-in hybrid lane only, the coordinator also turns an issuer's
  retained current rows into labelled POC equal-unit links
  (`official_equal_unit_component`, which reuses `quantized_unit_share`). They attach through
  the existing merge, and the existing engine computes the paths. The engine, comparator
  and the non-hybrid path are unchanged. The manual replacement path refuses to keep or
  redeclare those links unchanged (owner F1 decision).
- D-082 (candidate, opt-in, default off): an eligible Garden analysis records a separate POC
  acceptance beside its unchanged review result. The ownership service honours it at the
  readiness boundary only while its own composition enables the policy; discovery and the
  engine are unchanged.

Retire when an authorized provider supplies an issuer profile and same-entity denominators.
