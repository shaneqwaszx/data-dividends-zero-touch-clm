# ACRA Mock API Profile — Phase 10 Expanded Registry Acquisition

## Contract status

> These are project-owned Mock contracts used to exercise the POC architecture. They
> are not asserted to be the authoritative subscribed ACRA API contract while Q-012
> remains open.

This profile belongs to the local synthetic `mock` mode. The separately named official
`api_marketplace_mock` lane is an opt-in `MOCK_INTEROPERABILITY_OBSERVED` runtime after
the authorized 2026-09-26 token/entity/shareholder observations. Its provider data does
not change this local synthetic Mock contract or its fixture-only percentage rules.

The operations, paths, field names, collection limits, empty rules, and errors below
are synthetic project behavior. They are not captured ACRA responses and do not prove
live or sandbox interoperability. ACRA remains the business source; `MOCK` identifies
the credential-free environment. The existing sandbox-shaped entity-profile seam is
retained, but expanded sandbox operations fail closed because Q-012 supplies no
authoritative paths or schemas for them.

## Acquisition sequence

```text
eligible resolved Singapore identifier
  -> GET_ENTITY_PROFILE
  -> GET_OFFICERS
  -> GET_OWNERSHIP_PARTIES
  -> GET_RELATIONSHIPS
  -> RegistryAcquisitionBundle
  -> canonical entity + existing OwnershipAnalysisService
```

The backend owns routing and call order. A request cannot select a URL, provider class,
module, operation path, or credential. Each returned envelope is freshly reconstructed
through a strict DTO, bound to the requested UEN, checked for consistent environment
and UTC provenance, and normalized before business use.

## Common request and provenance

All four Mock operations take one required `uen` string. For the implemented Singapore
path it is normalized uppercase and must satisfy one of three bounded project syntax
forms: eight digits plus a letter, nine digits plus a letter, or `T`/`S`/`R` plus two
year digits, two letters, four digits, and a final letter. This remains a routing safety
predicate, not a complete official UEN validator or evidence of Live ACRA support.

Each response envelope requires:

| Field | Type | Required | Rule |
|---|---|---:|---|
| `uen` | string | YES | 1–32 bounded alphanumeric source text; must equal requested UEN |
| `source_environment` | enum | YES | `MOCK` for expanded fixtures; `SANDBOX` only at an explicitly configured seam |
| `source_endpoint` | string | YES | Internal query-free HTTPS provenance; never projected to the browser |
| `retrieved_at` | UTC date-time | YES | Timezone-aware UTC |

Normalized records retain an opaque browser-safe evidence reference such as
`acra:officers:202400001A`. Raw endpoints, headers, authorization, response bodies,
connector configuration, and exceptions are not retained in browser models.

## Operation 1 — `GET_ENTITY_PROFILE`

Project connector method: `fetch_company(uen)`.

### Response

| Field | Type | Required | Notes |
|---|---|---:|---|
| `uen` | string | YES | Request-bound identity |
| `entity_name` | string | YES | 1–512 characters |
| `country_code` | string | YES | 2–3 letters |
| `entity_type` | string | YES | Project fixture value, not an official ACRA enum claim |
| `registration_date` | date | NO | ISO date |
| `entity_status` | string | NO | Project fixture value |
| `registered_address` | object/null | YES | May be absent to exercise canonical review |
| common provenance | fields above | YES | Internal only where stated |

Address fields are `block`, `street`, optional `unit`, optional `building_name`,
`postal_code`, and `country_code`. Unknown properties, blank required text, control
characters, unsafe provenance, non-UTC time, and identity mismatch are rejected.

### Synthetic example

```json
{
  "uen": "202400001A",
  "entity_name": "MERLION CIRCULAR LABS PTE. LTD.",
  "country_code": "SG",
  "entity_type": "PRIVATE_COMPANY_LIMITED_BY_SHARES",
  "registration_date": "2024-01-02",
  "entity_status": "LIVE",
  "registered_address": {
    "block": "18",
    "street": "INNOVATION WAY",
    "unit": "#04-01",
    "building_name": null,
    "postal_code": "018956",
    "country_code": "SG"
  },
  "source_environment": "MOCK",
  "source_endpoint": "internal query-free HTTPS provenance",
  "retrieved_at": "2026-08-28T02:00:00Z"
}
```

No entity is not a legitimate empty profile: it produces `ACRA_ENTITY_NOT_FOUND` and
stops all later operations. A malformed profile uses the existing safe ACRA response,
identity, or mapping errors and cannot create canonical data.

## Operation 2 — `GET_OFFICERS`

Project connector method: `fetch_officers(uen)`.

### Response

`officers` is a required array with at most **32** records. Each record is strict:

| Field | Type | Required | Notes |
|---|---|---:|---|
| `officer_id` | safe string | YES | 1–64, bounded opaque project ID |
| `name` | string | YES | 1–160; fixtures are fictional |
| `role` | string | YES | Project vocabulary such as `DIRECTOR`; not an official code list |
| `appointment_date` | date | NO | No inferred legal effect |
| `cessation_date` | date | NO | No inferred legal effect |
| `country` | 2–3 letter string | NO | Used only when the fixture supplies it |

### Synthetic example

```json
{
  "uen": "202400001A",
  "officers": [
    {
      "officer_id": "OFFICER_A",
      "name": "Alex Synthetic",
      "role": "DIRECTOR",
      "appointment_date": "2024-01-02",
      "cessation_date": null,
      "country": "SG"
    }
  ],
  "source_environment": "MOCK",
  "source_endpoint": "internal query-free HTTPS provenance",
  "retrieved_at": "2026-08-28T02:00:00Z"
}
```

An empty officer array is a legitimate optional result and is displayed as `EMPTY`; it
does not by itself make acquisition partial. A malformed response becomes
`REGISTRY_OPERATION_MALFORMED_RESPONSE`. A provider/transport failure becomes a safe
timeout or unavailable result, and later operations are `NOT_ATTEMPTED`.

## Operation 3 — `GET_OWNERSHIP_PARTIES`

Project connector method: `fetch_ownership_parties(uen)`.

### Response

`ownership_parties` is a required array with at most **64** records.

| Field | Type | Required | Notes |
|---|---|---:|---|
| `party_id` | safe string | YES | Unique within the acquisition |
| `party_type` | enum | YES | `NATURAL_PERSON` or `LEGAL_ENTITY` |
| `name` | string | YES | 1–160; fixtures are fictional |
| `registration_identifier` | string | NO | Used for legal entities when known |
| `country` | 2–3 letter string | NO | No nationality/legal inference |
| `ownership_percentage` | Decimal `(0,100]` | NO | Registry evidence only; never a UBO conclusion |

### Synthetic example

```json
{
  "uen": "202400001A",
  "ownership_parties": [
    {
      "party_id": "PERSON_A",
      "party_type": "NATURAL_PERSON",
      "name": "Avery Tan",
      "registration_identifier": null,
      "country": "SG",
      "ownership_percentage": "60"
    }
  ],
  "source_environment": "MOCK",
  "source_endpoint": "internal query-free HTTPS provenance",
  "retrieved_at": "2026-08-28T02:00:00Z"
}
```

For the normal ownership-bearing SME fixtures, an empty collection means expected
registry evidence is missing. Transport success is therefore displayed as `EMPTY`, but
the bundle is `PARTIAL / REGISTRY_EXPECTED_DATA_MISSING` and onboarding stops for
review. No sponsor rule is inferred to fill or waive the missing ownership evidence.

## Operation 4 — `GET_RELATIONSHIPS`

Project connector method: `fetch_relationships(uen)`.

### Response

`relationships` is a required array with at most **128** records.

| Field | Type | Required | Notes |
|---|---|---:|---|
| `relationship_id` | safe string | YES | Unique within the acquisition |
| `owned_entity_id` | safe string | YES | Root or a legal-entity ownership party |
| `owner_party_id` | safe string | YES | Must reference a returned ownership party |
| `relationship_type` | enum | YES | Project value `SHARE_OWNERSHIP` only |
| `ownership_percentage` | Decimal `(0,100]` | YES | Exact edge evidence |

### Synthetic example

```json
{
  "uen": "202400001A",
  "relationships": [
    {
      "relationship_id": "REL_DIRECT_A",
      "owned_entity_id": "ENTITY_202400001A",
      "owner_party_id": "PERSON_A",
      "relationship_type": "SHARE_OWNERSHIP",
      "ownership_percentage": "60"
    }
  ],
  "source_environment": "MOCK",
  "source_endpoint": "internal query-free HTTPS provenance",
  "retrieved_at": "2026-08-28T02:00:00Z"
}
```

References, IDs, percentages, provenance, and collection bounds are revalidated as a
whole. Missing relationships when ownership parties exist produce a partial expected-
data issue. Malformed references or shapes fail the relationship operation safely.

## Bundle and operation states

The normalized bundle contains the canonical entity profile, bounded officer/party/
relationship collections, exactly four ordered operation results, a UTC retrieval time,
and safe issues. It contains no UBO candidate or threshold result.

Operation status is one of `COMPLETE`, `EMPTY`, `FAILED`, or `NOT_ATTEMPTED`. Bundle
status is:

| Status | Meaning | Workflow result |
|---|---|---|
| `COMPLETE` | Every attempted operation validated; optional officers may be empty; required ownership evidence exists | Continue to document and ownership stages |
| `PARTIAL` | Transport succeeded but expected ownership parties or relationships are missing | `REVIEW_REQUIRED / REGISTRY_EXPECTED_DATA_MISSING` |
| `FAILED` | A later operation timed out, was unavailable, or returned malformed/inconsistent data | Sanitized technical `FAILED`; no downstream call |

### Aggregate integrity rules

`RegistryAcquisitionBundle` validates the advertised aggregate state on every normal
construction/revalidation path. It does not trust the connector or factory to make the
fields agree.

- The catalogue is exactly `ENTITY_PROFILE`, `OFFICERS`, `OWNERSHIP_PARTIES`, then
  `RELATIONSHIPS`, once each. Missing, duplicate, reordered, unknown, or extra results
  are invalid.
- `ENTITY_PROFILE` is always `COMPLETE / 1`; its canonical registration number, source,
  environment, retrieval time, requested identifier, and deterministic root party must
  agree.
- `COMPLETE` requires `OWNERSHIP_PARTIES` and `RELATIONSHIPS` both to be `COMPLETE`
  with non-empty evidence. Officers may be `COMPLETE` or `EMPTY`. No issue or
  `NOT_ATTEMPTED` result is permitted.
- `PARTIAL` is reserved for expected missing ownership evidence. It has no `FAILED` or
  `NOT_ATTEMPTED` operation, at least one ownership operation is `EMPTY`, and its sole
  issue is `REGISTRY_EXPECTED_DATA_MISSING`.
- `FAILED` has exactly one technical `FAILED` operation. Earlier operations form a
  valid complete/empty prefix; every later operation is `NOT_ATTEMPTED`; the sole
  bundle issue equals the failed operation's safe error.
- Operation counts equal the corresponding collection lengths. `EMPTY`, `FAILED`, and
  `NOT_ATTEMPTED` operations retain zero records. A record's provider, environment,
  operation, retrieval time, and evidence reference must equal its operation-result
  provenance.
- Officer, ownership-party, and relationship identifiers are unique within their
  collections, and existing relationship endpoint/reference validation remains active.

Consequently, a bundle with overall `COMPLETE` and unattempted or empty mandatory
ownership operations is a domain validation error and cannot be serialized or projected
as successful acquisition evidence.

## Ownership-engine integration

```text
RegistryAcquisitionBundle
  -> RegistryAcquisitionOwnershipProvider
  -> existing OwnershipSourceResult
  -> existing OwnershipAnalysisService
```

The adapter creates the root legal-entity party and maps returned parties and share
edges into the existing ownership vocabulary. The existing service remains solely
responsible for graph validation, Decimal path multiplication, multiple-path
aggregation, provisional threshold comparison, cycle detection, incomplete chains, and
path/depth limits. Phase 10 adds no second calculator and changes no UBO rule.

The historical Mock ownership providers remain available only for explicit developer/
test fault scenarios.

## Synthetic scenario catalogue

| UEN | Project-owned purpose | Acquisition result |
|---|---|---|
| `202400001A` | Normal SME, one officer, two direct natural-person owners | Complete |
| `202400002B` | Existing incomplete canonical-address regression | Acquisition complete, later canonical review |
| `202400003C` | Existing later Mock GoldTier policy failure | Complete |
| `202400004D` | Existing later partial amend | Complete |
| `202400005E` | Existing-party Mock GoldTier search | Complete |
| `202400006F` | Registry-fed ownership cycle | Complete acquisition; existing ownership analysis requires review |
| `202400007G` | Legal-entity shareholder | Complete |
| `202400008H` | Multiple owners | Complete |
| `202400009I` | Multi-level ownership | Complete |
| `202400010J` | Legitimately empty officer collection | Complete with Officers `EMPTY` |
| `202400011K` | Missing expected ownership evidence | Partial/review required |
| `202400012L` | Malformed later relationship response | Failed safely |
| `202400013M` | Later relationship provider failure | Failed safely |
| `11111999A` | Garden Business bounded recursive synthetic ownership demo | Complete |

All names, identifiers, dates, addresses, officers, owners, and relationships are
fictional. They are not sponsor-approved golden cases.

### Garden Business bounded synthetic profile

`11111999A` is a project-defined Mock fixture only. Its entity profile is `GARDEN
BUSINESS`, its officer operation is validly empty, and its ownership operations contain
the following exact synthetic graph:

- `SIM LIM PTE. LTD.` (`111111111M`), Corporate, 5,000 active units → `62.500000%`;
- `LIM CHOON HUAT` (`S9988776F`), Individual, 3,000 active units → `37.500000%`;
- beneath SIM LIM, active counts `900 / 100 / 100` derive `81.818182% / 9.090909% /
  9.090909%`; the explicitly withdrawn holder is excluded.

The exact `shareAllotted / active total` derivation exists only inside this fixture. It
does not define legal ownership, voting rights, controller status, or generic ACRA
mapping. The resulting relationships enter the ordinary registry acquisition and sole
Decimal ownership engine. Q-004 and Q-012 remain open.

## Safe errors and call stopping

Entity-profile errors retain the accepted ACRA safe codes. Expanded operations use:

| Code | Meaning |
|---|---|
| `REGISTRY_OPERATION_MALFORMED_RESPONSE` | Strict DTO, identity, environment, provenance, or relationship consistency validation failed |
| `REGISTRY_OPERATION_TIMEOUT` | Operation exceeded its bounded timeout |
| `REGISTRY_OPERATION_UNAVAILABLE` | Operation/provider could not be completed |
| `REGISTRY_EXPECTED_DATA_MISSING` | Valid empty result omitted ownership evidence required by the current conservative POC path |

Raw exceptions and response bodies never enter the case, event, API, or frontend. A
failed operation stops later registry operations. Any Registry-stage blocker from Phase
09 makes zero calls to all four acquisition operations and zero IDP, ownership, or
GoldTier calls.

## Source → internal → GoldTier mapping readiness

### Entity

| Mock ACRA field | Internal field | GoldTier field | Notes |
|---|---|---|---|
| `uen` | `CanonicalLegalEntity.registration_number` | `TBD_SPONSOR` | Request-bound uppercase identifier |
| `entity_name` | `CanonicalLegalEntity.legal_name` | `TBD_SPONSOR` | Trim only |
| `country_code` | `country_of_incorporation` | `TBD_SPONSOR` | Singapore value mapping unconfirmed |
| `entity_type` | `party_type` | `TBD_SPONSOR` | Value-list mapping unconfirmed |
| address fields | `RegisteredAddress` | `TBD_SPONSOR` | Bounded line assembly |

### Officer/director

| Mock ACRA field | Internal field | GoldTier field | Notes |
|---|---|---|---|
| `officer_id` | `RegistryOfficer.officer_id` | `TBD_SPONSOR` | Opaque project identifier |
| `name` | `RegistryOfficer.name` | `TBD_SPONSOR` | Synthetic POC evidence |
| `role` | `RegistryOfficer.role` | `TBD_SPONSOR` | No official/source-to-target role mapping claimed |
| appointment/cessation/country | matching normalized fields | `TBD_SPONSOR` | Optional evidence |

### Ownership party

| Mock ACRA field | Internal field | GoldTier field | Notes |
|---|---|---|---|
| `party_id` | `RegistryOwnershipParty.party_id` | `TBD_SPONSOR` | Opaque project identifier |
| `party_type` | normalized party type | `TBD_SPONSOR` | Natural/legal only |
| name/identifier/country | normalized party fields | `TBD_SPONSOR` | No related-party write in Phase 10 |
| `ownership_percentage` | registry evidence | `TBD_SPONSOR` | Not a UBO tag |

### Relationship

| Mock ACRA field | Internal field | GoldTier field | Notes |
|---|---|---|---|
| relationship/endpoints | `RegistryRelationship` then existing `OwnershipRelationship` | `TBD_SPONSOR` | No `createRelationship` call |
| `relationship_type` | `SHARE_OWNERSHIP` | `TBD_SPONSOR` | Project vocabulary only |
| `ownership_percentage` | existing Decimal edge percent | `TBD_SPONSOR` | Existing calculator consumes exact Decimal |

## Limitations and sponsor dependencies

- Q-012 remains open for authoritative provider errors, limits, complete operation and
  relationship semantics, same-entity capital/share-class denominator authority,
  subscriber Sandbox, Production, and Live verification. The official Mock token,
  entity, and shareholder subset is separately observed and implemented.
- Q-015 remains open; acquisition adds no jurisdiction source precedence or resolution.
- Officer roles and relationship semantics are project vocabulary, not legal findings.
- Collection bounds are conservative POC safety limits, not ACRA service limits or SLAs.
- No ACRA+, foreign registry, live ACRA, new provider-mode framework, durable Mongo
  repository, control-based UBO rule, related-party write, real GoldTier, final mapping,
  or Ready-for-Approval behavior is implemented.
