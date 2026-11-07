# ACRA API Marketplace Mock Readiness

## Current decision

The official ACRA API Marketplace Mock is a distinct provider lane with canonical
runtime-mode name `api_marketplace_mock`. It is not the local synthetic `mock` mode,
the generic `sandbox` seam, the dormant BizFile provider, or Live ACRA.

Current classification and readiness are:

- provider classification: `MOCK`;
- evidence classification: `OBSERVED_MOCK_INTEROPERABILITY`;
- activation state: `MOCK_INTEROPERABILITY_OBSERVED`;
- runtime activation: explicit opt-in only;
- governing open question: Q-012 remains open.

The local synthetic ACRA Mock remains the default. The generic sandbox remains
`PARTIAL / PARTIAL_SCAFFOLD_ONLY`. `ACRA_BIZFILE` remains `DORMANT / BLOCKED`.

## CONFIRMED_PROVIDER_CONTRACT

The supplied official Mock Postman exports establish the following bounded contract:

- API base: `https://api-sandbox.bizfile.gov.sg/api/acra`;
- token request: `POST` to
  `https://api-sandbox.bizfile.gov.sg/authorizeServer/oauth/token` with
  `grant_type=client_credentials` in the query;
- token authentication: HTTP Basic using the Mock client ID and secret key;
- token content type/body: `application/json` with an empty body;
- downstream authentication: raw access token in the header named exactly `token`;
- entity operation: `GET /entityQuery/entityBasicInformation?uen=<UEN>`;
- shareholder operation: `GET /entityQuery/coShareholdersDetails?uen=<UEN>`;
- capital evidence operation: `GET /entityQuery/coCapitalDetails?uen=<UEN>`;
- related supplied collections include business profile, officer record, registered
  address, and constitution operations.

Bearer downstream authentication is not established and is not used. Production host,
Production token behavior, mutation operations, subscription management, and Live ACRA
are outside this contract.

## OBSERVED_MOCK_INTEROPERABILITY

On 2026-09-26, an explicitly authorized bounded run used the supplied Mock credentials.
TLS certificate verification remained enabled, environment proxy settings were not
trusted, redirects were disabled, time and response size were bounded, and the process
contacted only `api-sandbox.bizfile.gov.sg`.

The token response was HTTP `200`, JSON, and had exactly these observed field names and
types: `access_token` string, `expires_in` integer, `scope` string, and `token_type`
string. The observed expiry value was 1,799 seconds; the token value and all credential
values were retained only in process memory and were not recorded.

Strict operation observations were:

- entity basic information for the approved Garden Mock identity returned HTTP `200`,
  matched the requested UEN, decoded strictly, and returned `GARDEN BUSINESS`;
- shareholder details for the approved SIM LIM Mock identity returned HTTP `200`,
  matched the requested UEN, decoded strictly, and exposed shareholder identity,
  category, status, and share-count evidence but no provider percentage;
- shareholder details for the Garden Mock identity returned HTTP `200` with an explicit
  empty `entities` collection, so the synthetic Garden shareholder chain is not present
  in the observed official Mock response;
- the supplied capital sample identity returned HTTP `200` and exposed share-detail
  fields including currency, issued and paid-up share capital, allotted shares, and
  share type. It is not the Garden or SIM LIM identity and therefore does not establish
  a denominator for either observed shareholder response.

Use the official Mock sample identities only for the operation each one actually
proves:

- `11111999A` (Garden) proves the entity/basic-information success path. Its observed
  shareholder collection is empty.
- `111111111M` is the supplied shareholder-operation sample only. It does not prove a
  usable basic-information entity or same-entity capital denominator.
- `111111111K` is the supplied capital-operation sample only. It does not establish
  Garden or SIM LIM ownership percentages.
- `202400001A` and the other `20240000x` values are local synthetic fixtures. They are
  not official ACRA API Marketplace Mock sample identities.

The minimized operation receipt is
`docs/evidence/acra_api_marketplace_mock_2026-09-26.json`, governed by
`docs/contracts/acra_api_marketplace_mock_evidence.schema.json`. It contains no query
values, credentials, token/header values, raw payload, provider error text, or personal
data.

## PROJECT_DERIVED_TRANSFORMATION

The runtime reuses only the sample decoder fields proven compatible by the observations.
It binds returned UEN to requested UEN, rejects ambiguous identities, keeps query-free
provenance, and carries shareholder category/status/share counts as untrusted source
evidence. Current Singapore/default entity and officer vocabulary normalization remains
project-defined unless separately evidenced by the supplied operation contract.

No ownership percentage is derived. `shareAllotted` is evidence of a count only. The
official Mock lane returns no synthetic relationship fallback and therefore reaches the
existing truthful Registry expected-data stop when a relationship graph is required.

## STILL_OPEN

Q-012 remains open for authoritative not-found and provider-error schemas, rate limits,
retry guidance, service-level timeout guidance, mTLS/private-CA requirements if any,
pagination/collection limits, complete officer/address/constitution semantics, complete
same-entity capital/share-class denominator semantics, relationship/control semantics,
and any subscriber Sandbox, Production, or Live contract. The token failure schema was
not exercised during the authorized successful run.

No uncertain result permits scheme, endpoint, mapping, percentage, or provider fallback
guessing. Any missing company identity or required relationship data continues to fail
closed.

## Post-UAT sample catalogue correction - 2026-10-05

The Marketplace Mock sample catalogue is operation-specific. An Entity Basic Information
UEN does not establish valid Officers, Ownership or Relationships records for that UEN.
Do not combine identifiers across operations or promote XYZ ACCOUNTING/another profile
sample to a whole-pipeline happy path without independently proving every required
operation coherent. Garden remains the separately bounded known special case.
The recommended fully controlled demonstrations are the four fictional database-backed
fixtures in [the database UAT guide](../demo/ZERO_TOUCH_DATABASE_HAPPY_PATH_UAT.md).
They are local synthetic normalized evidence, never real ACRA catalogue entities.

## Bounded Garden/SIM LIM verification - 2026-10-24

The owner authorized this bounded, read-only run. It used the in-process application
against the official Mock host, with verified TLS, no proxy inheritance and redirects
disabled. Credentials were read only in memory and never recorded. The reads were
allowlisted to `11111999A` and `111111111M`. There were 9 genuine requests in total: 2
token requests and 7 GETs. 8 recorded HTTP 200; the first capital read's status was not
captured.

- **Fresh Garden onboarding** (memory persistence, Mock GoldTier, hybrid direct-only
  overlay, running the D-079 code before share-class retention existed):
  - Garden `entityBasicInformation` ×2;
  - SIM LIM `entityBasicInformation` ×1, an explicit empty collection;
  - SIM LIM `coShareholdersDetails` ×1: one entity, UEN bound, 4 rows.
  The rows were retained as D-079 official shareholder evidence. A second fresh case
  made 0 GETs (cache reuse).
- **Share classes.** The 4 rows are: 1 Corporate Withdrawn (Ordinary); Active Individual
  holdings of 900 Ordinary, 100 Preference and 100 Others; all in SINGAPORE DOLLAR. The
  corporate row's identifier has a UEN-like shape, but the contract does not define it as
  a registration number, so it is not used. A foreign-registration field is present.
- **Capital.** `coCapitalDetails` for `111111111M` was read twice. The fully recorded read
  returned HTTP 200 with an explicit empty collection (0 entities). The first read returned
  no capital fields. No same-entity capital or denominator record exists in the Mock.
- **Repeat read.** One `coShareholdersDetails` repeat recorded the per-row class.

This is `MOCK_INTEROPERABILITY_OBSERVED` only, not a Live or production observation. It
supplies no share-class economic or control rule, and no denominator authority. Q-012
remains open.

## AWS staging readiness

Offline preparation only: no genuine call was made, and this adds no interoperability
evidence. The lane stays `MOCK`, not Sandbox or Live. No decision number is allocated
here; the owner assigns one when this content is accepted.

The three lanes stay distinct:

| Lane | Mode | Evidence reference | Staging |
|---|---|---|---|
| Local synthetic Mock | `mock` | `https://mock.acra.gov.sg/...` or `local-synthetic:...` | Default |
| Official Marketplace Mock | `api_marketplace_mock` | `https://api-sandbox.bizfile.gov.sg/api/acra/...` | Opt-in, after the release change to `deploy/compose.yml`, which pins `mock` today |
| Generic Sandbox or Live | `sandbox`, none | None observed | Refused or unavailable |

The Mock host name contains `sandbox`. It is the official Mock, not an ACRA Sandbox.

Staging behaviour on the official lane:

- Both credentials are required at startup. They are backend-only secrets, and a rejected
  start reports only `Invalid staging configuration`.
- POC acceptance and the advisory UBO review (D-121) apply only to cases whose identity is
  official Mock evidence. A case retained from the local Mock lane gets neither, so its
  review keeps blocking. A retained case with no review open is not affected, and the
  runtime label describes the running lane, not each retained case.
- Provider acquisition reads no local seeds, for root or corporate holders. Elsewhere this
  lane reads the seed namespace first, so a seeded holder would merge unmarked. The
  Government register keeps its own labelled route and is not promoted to official
  provenance. The seeder refuses `clm_staging`, so nothing populates that register there
  today, and a Government UEN stops at `GOVERNMENT_IDENTITY_NOT_FOUND` on both staging
  lanes. Government in staging needs an approved way to populate it.
- Registry cache keys stay isolated by dataset namespace.
- `GARDEN_SUPPLEMENT_ENABLED` and the hybrid overlay stay off by default. Both add labelled
  local synthetic evidence, so leave them unset unless the owner decides otherwise.

Known limits are unchanged. Sample UEN coverage is small and Garden shareholders are
empty. The Mock supplies no same-entity denominator, no percentage and no relationship or
control data. Missing ownership stays missing and goes to review. Q-012 remains open for
error schemas, rate and retry guidance, any network allowlist, and all Sandbox and
Production contracts.
