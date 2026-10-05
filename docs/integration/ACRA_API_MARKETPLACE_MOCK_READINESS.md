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
