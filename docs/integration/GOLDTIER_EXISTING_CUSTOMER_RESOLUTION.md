# GoldTier existing-customer resolution and provider-family reconciliation

Date: 2026-10-05. Bounded post-closeout branch based on
`1e0600335a0c7677b5cd5d5c9dd8401dfaf3b90f`. Unmerged POC remediation;
verification and independent verdict belong to its assigned gate.

## Authority and private sources

The owner relayed current sponsor answers and explicitly directed continued XPI
implementation with evidence-bound confirmation. Private artifacts are persistent
authority: inspect only relevant files under the primary repository's `private`
directory before declaring a provider contract unknown. Do not copy private content
into source, print credentials or customer bodies, or open quarantined PingFed material
for this task. File presence alone does not select a runtime provider family.

Inspected sources: `sponsor-artifacts-v2/GoldTier APIs_Guideline.pdf`,
`sponsor-artifacts-v2/GoldTier APIs.postman_collection.json`,
`sponsor-artifacts/GoldTier-XPI-Connection-Guide.pdf`,
`sponsor-artifacts/EDS-GoldTier_Integration_API_Specification.docx`,
the `searchParty.yaml` member of `gt_eds_openapi_yaml_final.zip`, and Search
structure in `gt_eds_api_specs_json.zip`. The XPI originals match the hashes already
recorded in [the mapping matrix](GOLDTIER_XPI_MAPPING_MATRIX.md).

Precedence: latest direct sponsor answer; exact matching provider-family contract;
companion dictionary/decision tree; accepted reconciliation/ADR; historical evidence.
A business answer does not invent transport syntax. Conflicting examples remain
INVALID / QUARANTINED and are never implementation fixtures.

## Two Search contracts

| Family | Search endpoint | Supplied supported query names | Current treatment |
|---|---|---|---|
| XPI Sandbox | `/{Env}/gt-xpi/v1/customers/search` | `goldTierID`, `legalName`, `groupCompanyName`, `countryOfIncorporation` | Existing transport/DTO retained; case Search uses legal name/country and readback uses retained GoldTier ID |
| EDS | `GET /v1/eds/parties/search` | `legalName`, `registrationNumber`, `registrationNumberType`, `externalSystem`, `externalSystemKey`, `lei`, `firstName`, `middleName`, `lastName`, `dateOfBirth`, `page`, `pageSize` | Supplied distinct contract; no runtime family switch or DTO union |

`SEARCH_BY_REGISTRATION = SUPPLIED_EDS_CONTRACT` and
`SEARCH_BY_EXTERNAL_SYSTEM_KEY = SUPPLIED_EDS_CONTRACT`. These capabilities are
not proven query aliases for the current XPI endpoint. Sponsor terminology
`customerExternalSystemKey` describes correlation; the EDS Search alias is
`externalSystemKey`. Neither is a unique GoldTier customer ID or sufficient
duplicate/recovery proof.

Decision: continue the existing XPI POC. Moving orchestration to EDS is a
`FUTURE_PROVIDER_FAMILY_DELTA` requiring explicit architecture/contract treatment
and assignment. No sponsor artifact resubmission is required. Registration-first
Search is appropriate only for a family whose matching contract supports it.

## Existing-customer decision

The existing case/CLM/zero-touch owners retain the Search request, bounded candidate
fields and canonical fingerprint. A single Sandbox candidate with matching provider
registration/UEN and country can produce provider `EXACT_MATCH` without requiring a
prior local case. Historical Mock reuse still requires its accepted finalized proof.
Initial candidate registration/country fields are now retained instead of discarded;
historical absent tuples mean unknown evidence.

A singleton incomplete XPI candidate with a matching normalized legal name, independent
current Singapore case identity and no supplied contradictory registration/country
may expose `CONFIRM_EXISTING_GOLDTIER_CUSTOMER`. Creator CASE_ACCESS is reauthorized
inside the existing case lock. The request binds Search UUID and automation/CLM/case
versions and a bounded rationale; it has no target-ID input. The server takes the ID
only from that retained candidate. The CLM checkpoint retains actor, UTC time, rationale,
request/ID and reviewed versions as `CONFIRMED_EXISTING`. This is a human evidence
decision, never a deterministic provider EXACT_MATCH, final dispatch or legal approval.

Confirmation performs zero provider calls. It leaves unrelated blockers open or returns
to document intake/explicit evidence continuation. The existing target ledger treats
CONFIRMED_EXISTING as existing-customer reuse: no Shell or new Policy. With no supported
resolved enrichment, Amend is AMEND_NOT_REQUIRED; only same-ID readback follows final
Review & Send. Multiple candidates, missing names and known identity conflicts have
no selection/confirmation action. Stale requests, arbitrary IDs and frozen target
attempts are rejected. A retained receipt can repair an interrupted local stage
projection without Search or target replay.

## Independent document evidence

Current-document field decisions and reconciliation can proceed at unresolved Search
through the existing document/reconciliation owners. Search remains the earliest open
blocker and target readiness remains blocked. Completed document review changes retained
evidence, not target identity or dispatch authority. Creator restrictions, immutable
decisions, supersession and final-target freezes remain in force.

## Current sponsor answers and boundaries

| Current answer | Bounded effect / unresolved boundary |
|---|---|
| Search is intended to supply identity evidence; registration and external-key search are supported in supplied specs | Reconciled by API family above; incomplete XPI evidence requires explicit confirmation |
| External key is correlation, not unique target identity | Never the sole exact, duplicate or recovery key |
| Existing GoldTier values take precedence or the user selects the correct value; resolved values must be persisted in GT | Bounded existing-customer authority recorded; identity confirmation does not silently overwrite canonical values or invent unsupported Amend fields |
| Shell, Policy, Amend are synchronous and ordered; GTAPICONNECTUSER is the API user | Existing ledger ordering/backend transport identity retained; no Production/PingFed authority |
| Amend needs existing GoldTier and Policy identifiers; ANZSIC/group-company fields are optional; Requested/Active Singapore Policy can be amended | Current XPI aliases stay `goldTierId` and `policy`; no invented `policyId`, enrichment, policy status or automatic industry mapping |
| Known Validation Failed Amend applies no customer-field changes; correction can support a NEW Amend; no idempotency/retry mechanism exists | A new corrected intent requires separate review/authorization. Historical failed/uncertain attempts are preserved and never replayed |
| `policy=Singapore` and `bookingEntity=ANZBGL (Singapore Branch)` are accepted POC values | Bounded Singapore POC, not universal/Production value authority |
| GoldTier owns downstream four-eye/KYC; this application automates Maker preparation | Review & Send remains final local approval; no achieved KYC/RFA/regulatory approval claim |

Garden remains an existing-customer scenario: retained candidate143878 may be confirmed,
ACRA official Marketplace Mock and actual LOCAL OCR evidence stay distinct, partnership
quantitative ownership remains partial, and reviewed LOCAL supplementary evidence is
required for deterministic >=25% candidates. No official percentage is fabricated.
This remediation performs no external Garden/ACRA/GoldTier call. Related-party child
lifecycle, original-file GoldTier upload, full legal/control UBO, Production and Live
remain unresolved/out of scope.
