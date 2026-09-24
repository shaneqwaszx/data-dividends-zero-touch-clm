# GoldTier XPI Sandbox Reconciliation

Date: 2026-09-24
Branch: `feature/pre-phase22-capability-expansion`
Baseline: `3ca232b58c3842f413c4552dbd3b85aabea4591c`

## Outcome

`SANDBOX_PARTIAL_IMPLEMENTED / CUSTOMER_WRITE_NOT_EXECUTED / RELATED_PARTY_BLOCKED`

The two sponsor artefacts named by the assignment became available and were reconciled
against the current source, historical EDS contract, decisions, and open questions:

- `GoldTier APIs_Guideline.pdf`, SHA-256
  `b4fedf629019d17a33c05d74a248fcf4973aef740c491e91dc63ce7d6c06ef55`;
- `GoldTier APIs.postman_collection.json`, SHA-256
  `e0c20335213e15cf566ea45b262e4e3f2c3cd27d326330c2e7c1b73c1a71a708`.

No sponsor credential, header value, portal password, raw provider body, or customer
record is copied into this document or the repository. The detailed field analysis is
in `GOLDTIER_XPI_MAPPING_MATRIX.md`.

## Contract result

The files define a six-operation XPI sandbox dialect under `/gt-xpi/v1`:

| Operation | Method and route | Implemented boundary |
|---|---|---|
| Customer search | `GET /customers/search` | Strict query DTO and bounded safe candidate projection |
| Customer create | `POST /customers/create` | Strict DTO, mapper, write opt-in, existing target ledger |
| Customer policy | `POST /customers/createPolicy` | Strict DTO, case-bound target policy, existing target ledger |
| Customer amend | `POST /customers/amendCustomer` | Strict DTO, case-bound target policy, existing target ledger |
| Related-party policy | `POST /relatedParties/createPolicy` | Strict local DTO only; external dispatch blocked |
| Related-party amend | `POST /relatedParties/amendRelatedParty` | Strict local DTO only; external dispatch blocked |

This dialect is not the historical EDS-shaped Mock contract. It therefore has focused
XPI DTO/mapper/connector modules and an explicit composition branch. Mock remains the
default and never acts as a sandbox failure fallback.

## Runtime ownership

- The existing `GoldTierConnector` boundary remains the only target port.
- The existing target ledger remains the only order, intent, outcome, recovery, and
  no-replay owner.
- The existing policy catalogue supplies eight explicit authority-labelled target
  values and freezes them into each new case.
- The existing entity-resolution owner evaluates bounded search candidates. Only an
  exact identifier/country match may reuse an existing party; every other candidate
  result stops at review with zero target mutations.
- The existing case-scoped CLM plan exposes a bounded preview. It contains mapped
  values, provenance, authority, missing status, validation, and policy version, but no
  transport identity or raw provider response.
- Schema v5 remains the one case-envelope owner. New target fields are additive and
  optional; earlier schema-v5 records read as Mock/no-target-enrichment without rewrite.

## Transport and security boundary

The XPI transport enforces HTTPS, TLS 1.3, certificate verification, redirects off,
bounded timeout, bounded response retention, strict URL/query construction, and fixed
safe errors. The sponsor-supplied `user_id` value is backend-only. Collection `noauth`
metadata is sandbox evidence only and does not establish production no-auth behavior or
replace PingFed.

Mutation timeout, transport ambiguity, cancellation, oversized response, or malformed
post-acceptance response is an uncertain outcome. The attempted ledger entry remains
`IN_PROGRESS`; no automatic replay or Mock fallback occurs.

## Sandbox observations

Four bounded, read-only, synthetic customer searches were executed with raw responses
discarded. Each returned HTTP 200 with an empty JSON array:

| Query class | Result |
|---|---|
| Unique synthetic legal name | No match |
| Synthetic legal name plus Singapore incorporation | No match |
| Unique synthetic group-company name | No match |
| Syntactically safe impossible GoldTier ID | No match |

An omitted/blank query and undocumented registration-number query were not sent because
either could unintentionally enumerate customer data if the server ignored the filter.
Non-empty candidate shape, 400/500 behavior, and production interoperability remain
unproved externally; their local adapters fail closed and are covered by synthetic
tests only.

## Mutation decision

No Shell, Policy, Amend, or related-party network request was executed.

The customer path now satisfies the local DTO, mapping, preview, ledger, fail-closed,
and no-replay prerequisites. The user-authorized `accountEntityType` POC placeholder is
now editable and labelled `PROJECT_DEFINED_PROVISIONAL`; the other seven institution-
specific target values remain `TBD_SPONSOR` in the authoritative policy defaults. The
mapper therefore still blocks ordinary case mutation before network or ledger creation.
Substituting Postman example values would invent business authority, so the optional
one-customer write was correctly not attempted.

Related-party execution remains additionally blocked because the supplied contract
requires `childId` but provides no conclusive child-identity creation/retrieval
lifecycle. Relationship value authority is also unresolved. Local DTO validation is not
evidence that the related-party operation is safe to dispatch.

## Classification and remaining authority

- Provider: `GOLDTIER_XPI`
- Mode: explicit `sandbox`
- Classification: `SANDBOX_PARTIAL`
- Default runtime: Mock
- PingFed/production authentication: not implemented
- Live interoperability: not proved
- Customer mutation evidence: not executed
- Related-party mutation evidence: blocked
- Q-016-dependent workflow mutations: deferred
- Phase 22: on hold

ADR-004 and decision D-048 record the architecture boundary. The remaining sponsor
questions include target vocabularies/authority, response contracts, PingFed/production
authentication, child-ID lifecycle, relationship semantics, and production handoff.
