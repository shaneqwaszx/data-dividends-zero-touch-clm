# GoldTier XPI Sandbox Diagnosis

Date: 2026-09-23
Scope: read-only preflight and evidence availability only

## Result

`NOT_EXECUTED`

No GoldTier network request, TLS handshake, DNS lookup, browser portal login, search,
create, amend, policy, or related-party write was executed.

## Reasons

1. The referenced GoldTier XPI guideline PDF and Postman collection are absent.
2. `GOLDTIER_SANDBOX_HOST` is absent from the current process environment.
3. `GOLDTIER_SANDBOX_USER_ID` is absent from the current process environment.
4. `GOLDTIER_SANDBOX_ALLOW_WRITES` is absent from the current process environment.
5. The repository currently composes Mock GoldTier only and has no reviewed XPI DTO or
   connector implementation.

Environment checks were presence-only. No value or secret was read or printed.

## Write safety

All write operations are `NOT_EXECUTED`. The required explicit write opt-in was absent,
and a missing opt-in is deny-by-default. No customer, policy, or related-party record was
created or amended.

## TLS and identity evidence

TLS version/cipher/certificate evidence is `NOT_AVAILABLE` because no host was provided
and no network connection was attempted. PingFed/API identity evidence is
`NOT_AVAILABLE`; portal credentials, even if later supplied, must not be interpreted as
API authentication material.

## Next diagnostic boundary

After the exact source artefacts and non-secret host/user configuration are supplied,
the first allowed diagnostic remains read-only customer search. Any mutation additionally
requires the exact reviewed DTO contract, explicit `GOLDTIER_SANDBOX_ALLOW_WRITES`, an
allowlisted synthetic target, and evidence capture that excludes credentials and raw
confidential payloads.

## Continuation evidence — 2026-09-24

The preceding result remains the historical 23 September preflight. On 24 September the
two sponsor files became available and were inspected read-only:

- `GoldTier APIs_Guideline.pdf`, SHA-256
  `b4fedf629019d17a33c05d74a248fcf4973aef740c491e91dc63ce7d6c06ef55`;
- `GoldTier APIs.postman_collection.json`, SHA-256
  `e0c20335213e15cf566ea45b262e4e3f2c3cd27d326330c2e7c1b73c1a71a708`.

They define six XPI sandbox operations under `/gt-xpi/v1`: customer Search, Shell,
Policy and Amend, plus related-party Policy and Amend. The collection supplies an HTTPS
host, environment segment and consistent `user_id` header value. Those values were read
only for bounded execution and were not printed, copied into the repository or treated
as production authentication material. The requests are marked `noauth`; this is
sandbox evidence only and does not establish production no-auth or PingFed behavior.

### Read-only Customer Search observations

All requests used TLS 1.3 only with certificate verification, redirects disabled, a
12-second timeout and a 128-KiB response limit. Responses were parsed only for status,
JSON top-level type and cardinality; raw bodies were not retained. No credential,
header value, sponsor example value or customer data was logged.

| Query | Result | Elapsed |
|---|---|---:|
| Unique synthetic `legalName` | HTTP 200, JSON array, 0 records | 1,589 ms |
| Same synthetic `legalName` plus `countryOfIncorporation=SG` | HTTP 200, JSON array, 0 records | 509 ms |
| Unique synthetic `groupCompanyName` | HTTP 200, JSON array, 0 records | 487 ms |
| Syntactically safe impossible `goldTierID` | HTTP 200, JSON array, 0 records | 381 ms |

The endpoint was therefore reachable and the supplied sandbox header/configuration was
accepted for these no-match searches. A no-match is observed as HTTP 200 with an empty
JSON array. Unique-match, multiple-match, malformed-input 400, service-failure 500 and
the result-object schema remain unproved.

A blank/omitted query was deliberately not sent because it could enumerate customer
records. An undocumented `registrationNumber` query was also not sent because an
ignored parameter could have the same broad-data effect. These safety skips are not
negative support claims.

### Mutation boundary

No Shell, Policy, Amend or related-party request has been executed. One synthetic
customer write remains conditionally eligible only after the reviewed XPI adapter,
strict DTOs, immutable case-bound target-policy snapshot, target ledger/no-replay path,
request preview, local tests and managed external-mutation approval are all in place.
Related-party execution remains blocked on the unproved `childId` lifecycle and
relationship-value authority.

This continuation changes the provider classification only to **Sandbox / Partial**.
It does not prove Live or production interoperability.

## Implementation closure — 2026-09-24

The explicit XPI sandbox connector, strict DTOs, mapper, immutable target-policy
snapshot, case request preview, exact-match/no-match routing, and existing-ledger
no-replay behavior are now implemented and locally verified. Mock remains the default;
there is no runtime fallback from sandbox to Mock.

No customer mutation was executed. Although the local execution prerequisites now
exist, the authoritative defaults for all eight institution-specific target values
remain `TBD_SPONSOR`. Dispatch therefore fails before ledger creation or network access.
Copying example values from the collection would invent target-policy authority and was
not permitted. The optional one-customer write was not used as acceptance evidence.

No related-party mutation was executed. The `childId` creation/retrieval lifecycle and
relationship-value authority remain unproved, so the RP boundary stays blocked even
though its strict local DTOs are testable.

Final classification: `SANDBOX_PARTIAL`. PingFed/production authentication and Live
interoperability remain not implemented/not proved. Raw provider payloads, header
values, portal credentials, and customer data were not retained or printed.
