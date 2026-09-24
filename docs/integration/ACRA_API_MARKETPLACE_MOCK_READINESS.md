# ACRA API Marketplace Mock Readiness

## Current decision

The official ACRA API Marketplace Mock is a distinct provider lane with canonical
runtime-mode name `api_marketplace_mock`. It is not the local synthetic `mock` mode,
the generic `sandbox` seam, the dormant BizFile provider, or Live ACRA.

Current classification and readiness are:

- provider classification: `MOCK`;
- evidence classification: `OFFICIAL_MOCK_OBSERVED` (authentication failure only);
- activation state: `BLOCKED_AUTHORITY`;
- runtime activation: disabled;
- governing open question: Q-012.

The local synthetic ACRA Mock remains the default. The generic sandbox remains
`PARTIAL / PARTIAL_SCAFFOLD_ONLY`. `ACRA_BIZFILE` remains `DORMANT / BLOCKED`.

## Sanitized diagnostic evidence

On 2026-09-24, a bounded read-only `GET` was made to the official Mock entity-query
endpoint without an Authorization header:

`https://api-sandbox.bizfile.gov.sg/api/acra/entityQuery/entityBasicInformation`

The result was HTTP `401`. No credential was supplied, no mutation was attempted, and
no request query, test identity, response body, response header, provider error text, or
customer data is retained here.

The only supported conclusion is that the historical no-auth hypothesis is false for
this observed request. The observation does not identify OAuth, a static header, API
key, mTLS, subscription-token, or any other authentication mechanism. It does not prove
a successful entity response, schema, not-found behavior, officer/shareholder operation,
relationship operation, mapping, Sandbox interoperability, or Live connectivity.

No exact UTC instant or safe diagnostic/correlation UUID was retained. Therefore this
summary is intentionally not represented as a schema-v2 external-provider evidence JSON
record. The strict validator contains a future auth-failure profile, but an artifact may
be created only from an actual diagnostic that retains every required safe metadata
field.

## Source-use boundary

- Current user direction is authority for the bounded POC mode name and for recording
  this sanitized observation.
- Public ACRA material supports only the existence of API Marketplace Mock APIs; it does
  not establish this operation's exact authentication or response contract.
- Historical Postman-derived comments and sample response shapes remain supporting
  evidence. The observed `401` supersedes the no-auth assumption for runtime use.
- The dormant sample decoder may inform tests, but it cannot become successful-provider
  evidence without an authenticated, bounded, schema-valid response.

## Required next evidence

Before runtime activation, the API owner must answer Q-012 with the exact authentication
mechanism, approved secret-delivery boundary, operation/schema/error contract, approved
Mock identities, rate/timeout guidance, and TLS requirements. A subsequent diagnostic
must use certificate verification, disabled redirects, bounded time and response size,
safe status/schema summaries, and no raw payload logging. A `401` or uncertain auth result
must stop; it must never trigger speculative OAuth, header guessing, or fallback to the
local Mock.
