# Phase 10 Expanded Registry Acquisition

## Boundary

Phase 10 expands only the project-owned ACRA Mock path:

```text
jurisdiction resolution / closed router
  -> AcraRegistryProviderAdapter
     -> entity profile
     -> officers
     -> ownership parties
     -> relationships
  -> normalized RegistryAcquisitionBundle
     -> canonical entity
     -> RegistryAcquisitionOwnershipProvider
        -> existing OwnershipAnalysisService
```

The generic onboarding service depends on `RegistryProvider.retrieve_acquisition` and
never imports ACRA source DTOs. The ACRA adapter owns operation order, strict DTO
reconstruction, requested/returned identity binding, normalized provenance, safe
failure translation, and internal consistency. No caller controls a provider, URL,
module, class, or operation.

## Data flow and authority

```text
project-owned untrusted ACRA Mock DTOs
  -> strict reconstruction and bounds
  -> provider-neutral normalized evidence
  -> existing canonical/ownership domains
  -> existing document/readiness/Mock GoldTier flow
```

The acquisition bundle contains operation observations and source evidence, not UBO
conclusions. `RegistryAcquisitionOwnershipProvider` implements the existing
`OwnershipProvider` contract. It maps the bundle into the established `Party` and
`OwnershipRelationship` graph; all Decimal path arithmetic, aggregation, provisional
threshold behavior, cycle/incomplete handling, and graph/path limits remain in
`OwnershipAnalysisService`.

Explicit developer/test ownership providers remain available for fault injection. They
do not replace registry evidence in the normal Mock Singapore path.

## Operation state

Every successful entity acquisition produces exactly four ordered results:

1. `ENTITY_PROFILE`
2. `OFFICERS`
3. `OWNERSHIP_PARTIES`
4. `RELATIONSHIPS`

An operation is `COMPLETE`, `EMPTY`, `FAILED`, or `NOT_ATTEMPTED`. The bundle is
`COMPLETE`, `PARTIAL`, or `FAILED`.

- Empty officers are legitimate and do not block.
- Missing ownership parties or relationships are valid transport results but incomplete
  evidence, so the case stops in Registry review.
- Malformed, identity-inconsistent, or provider-failed later operations fail safely and
  stop every subsequent operation/downstream stage.
- Phase 09 jurisdiction/provider/identifier blockers create no acquisition bundle and
  call none of the four operations.

The normalized bundle is self-validating rather than relying on the ACRA adapter to
construct it correctly. Direct construction must satisfy all of these rules:

- exactly one result for each operation in the order above;
- entity profile is complete, count one, and bound to the requested identifier and
  deterministic root party;
- every operation count agrees with its collection, while `FAILED` and
  `NOT_ATTEMPTED` retain no records;
- `COMPLETE` requires complete non-empty ownership-party and relationship evidence,
  permits officers only as `COMPLETE` or legitimate `EMPTY`, and carries no issue;
- `PARTIAL` contains no technical failure or not-attempted step, has at least one empty
  ownership operation, and carries exactly the expected-data-missing issue;
- `FAILED` contains exactly one failed technical operation, every prior step is
  complete/empty, every later step is not attempted, and its bundle issue matches the
  failed operation;
- officer, ownership-party, and relationship IDs are unique where applicable, and
  record provenance agrees exactly with its operation result and canonical source
  environment.

These invariants make absent or unattempted ownership evidence impossible to advertise
or project as a complete acquisition.

## Trust and projection

Source DTO limits are 32 officers, 64 ownership parties, and 128 relationships. Text,
IDs, percentages, UTC timestamps, HTTPS internal provenance, environment consistency,
unique IDs, and graph references are checked before persistence. Existing ownership
service limits remain a second boundary.

The browser receives only normalized POC fields, safe opaque evidence references,
provider/environment, UTC time, operation status/count, and stable error codes/messages.
Raw endpoints, headers, credentials, configuration, response bodies, provider objects,
and exception text remain server-internal. The UI labels the surface as a project-owned
synthetic Mock contract and never as verified live ACRA.

## Environment truth

Expanded operations are implemented only in `MockAcraConnector`. The existing
sandbox-shaped entity-profile operation remains available, but expanded sandbox
operations fail closed because Q-012 does not define their authoritative paths or
schemas. This prevents synthetic expanded data from being represented as sandbox or
live interoperability evidence.

## Persistence and non-goals

Acquisition evidence is retained in the existing process-local onboarding aggregate.
MongoDB remains diagnostic-only. Phase 10 adds no ACRA+, foreign registry, source
precedence, reconciliation engine, workflow replacement, new UBO rule, GoldTier mapping
or write, real integration, production RBAC, or Ready-for-Approval transition.
