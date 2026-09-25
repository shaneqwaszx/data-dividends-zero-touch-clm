# ACRA API Marketplace Mock Readiness

## Current decision

The official ACRA API Marketplace Mock is a distinct provider lane with canonical
runtime-mode name `api_marketplace_mock`. It is not the local synthetic `mock` mode,
the generic `sandbox` seam, the dormant BizFile provider, or Live ACRA.

Current classification and readiness are:

- provider classification: `MOCK`;
- evidence classification: `OFFICIAL_MOCK_OBSERVED` (authentication failure only);
- authentication authority: partial (request-side Mock facts only);
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

The observation proves only that the historical no-auth hypothesis is false for this
request. It does not prove a successful entity response, schema, not-found behavior,
officer/shareholder operation, relationship operation, mapping, Sandbox
interoperability, or Live connectivity.

No exact UTC instant or safe diagnostic/correlation UUID was retained. Therefore this
summary is intentionally not represented as a schema-v2 external-provider evidence JSON
record. The strict validator contains a future auth-failure profile, but an artifact may
be created only from an actual diagnostic that retains every required safe metadata
field.

## Source-use boundary

- Current user direction is authority for the bounded POC mode name, this sanitized
  observation, and the official authentication facts recorded below.
- Official ACRA material establishes the request-side Mock token facts below. It does
  not establish the successful operation or token response/error contracts still listed
  as open.
- Historical Postman-derived comments and sample response shapes remain supporting
  evidence. The observed `401` supersedes the no-auth assumption for runtime use.
- The dormant sample decoder may inform tests, but it cannot become successful-provider
  evidence without an authenticated, bounded, schema-valid response.

## Confirmed request-side authentication facts

- grant: OAuth2 Client Credentials;
- exact Mock token endpoint:
  `https://api-sandbox.bizfile.gov.sg/authorizeServer/oauth/token?grant_type=client_credentials`;
- token-endpoint client authentication: HTTP Basic, with client ID as username and
  secret key as password;
- documented token lifetime: 60 minutes;
- downstream API header name: exactly `token`;
- Bearer is not established;
- Mock and Production token hosts are separate; no Production token URL is represented
  in configuration or source.

The code foundation stores only optional backend credentials, fixed non-secret facts,
and a pure HTTP Basic constructor. It does not construct or send a token request, assume
a method/body, parse a response, cache or refresh a token, inject a downstream token, or
activate a connector. The generic sandbox header value is not a fallback.

## Required next evidence

Before runtime activation, the API owner must answer the remaining Q-012 items: approved
secret delivery and access, token response/error schema and downstream value semantics,
successful operation base/path/schema, approved Mock identities, provider errors,
rate/timeout/retry guidance, TLS requirements, related operations, and a successful
sanitized receipt. A subsequent authorized diagnostic must use certificate verification,
disabled redirects, bounded time and response size, safe status/schema summaries, and no
raw payload logging. Any uncertain auth result must stop; it must never trigger scheme,
method/body, response-shape, operation, or fallback guessing.
