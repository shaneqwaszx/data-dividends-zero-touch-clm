# Phase 02 ACRA Registry Integration and Ingestion Foundation

## Scope and outcome

Phase 02 adds the first production-shaped source integration adapter while preserving
the Phase 01 onboarding service and Mock GoldTier target:

```text
MockAcraConnector -----------+
                            |
AcraSandboxConnector -------+--> AcraConnector
        |                            |
        +--> request authorizer      v
        +--> HTTP transport     ACRA source DTO
        +--> response decoder        |
                                     v
                                  ACRA mapper
                                     |
                                     v
                              Canonical legal entity
                                     |
                                     v
                              OnboardingService
                                     |
                                     v
                              MockGoldTierConnector
```

No real GoldTier, PingFed, IDP, UBO, relationship, hierarchy, or approval capability is
introduced.

## Connector architecture

`OnboardingService` still consumes only `AcraConnector.fetch_company(uen)`. Composition
selects `MockAcraConnector` or `AcraSandboxConnector` from `ACRA_CONNECTOR_MODE`; no
service method branches on connector mode and no HTTP/client object enters orchestration.

`AcraSandboxConnector` owns status mapping and normalized UEN retrieval. Its HTTP
transport, request authorizer, response decoder, and clock are injectable. The default
transport uses HTTPX with certificate verification enabled, redirects disabled, an
explicit bounded timeout, and no response logging.

## Authentication and configuration boundary

The approved project evidence does not define the subscribed ACRA auth mechanism.
Phase 02 therefore defines `AcraRequestAuthorizer` rather than guessing OAuth, API-key,
Singpass, or Corppass behavior. A generic static-header implementation exists only as a
backend integration seam; `ACRA_AUTH_HEADER_NAME` and `ACRA_AUTH_HEADER_VALUE` must come
from authoritative authorized documentation. They are not evidence that ACRA uses a
particular header.

Sandbox mode requires:

- an HTTPS `ACRA_BASE_URL` without embedded user information, query, or fragment;
- an `ACRA_COMPANY_PATH_TEMPLATE` containing exactly one `{uen}` placeholder and no
  query/fragment;
- a timeout greater than zero and at most 60 seconds; and
- an injected or configured request authorizer.

Missing/invalid settings raise only `ACRA_CONFIGURATION_ERROR`. Secret values are held
as Pydantic `SecretStr`, are never returned by an endpoint, and are never logged. TLS
verification is not configurable and cannot be disabled.

## Source DTO and decoder

External JSON is decoded into `AcraCompanyPayload` before canonical mapping. The DTO is
strict (`extra=forbid`) and contains only UEN, name, country code, entity type,
registration date, status, registered address, and safe source metadata.

The project adapter trims its required text fields and rejects empty-after-trim values
for UEN, legal name, entity type, required company country, and the required components
of any supplied registered address. This is provisional source-integrity validation,
not a production ACRA format or value-list rule. A wholly absent address still uses the
existing Phase 01 human-review path; a supplied but semantically blank address is a
malformed source response.

`ProjectAcraResponseDecoder` validates a sanitized project envelope used by tests. The
exact subscriber JSON contract is not available, so this decoder is intentionally
replaceable and explicitly provisional. See `docs/contracts/ACRA_CANONICAL_MAPPING.md`.

## Canonical mapping and provenance

The mapper adds two source-neutral Phase 02 fields to `CanonicalLegalEntity`:
`registration_date` and `entity_status`. It maps address components without copying the
source model into the domain. GoldTier mappers remain unchanged and ignore these fields
until a later confirmed target mapping requires them.

Before GoldTier is called, source-neutral canonical checks independently reject blank
minimum business values, including the registration number, legal name, party type, and
required registered-address values. This defense in depth protects the workflow from a
future connector/mapper that bypasses source validation without duplicating the source
schema.

Provenance always records business source `ACRA`. The environment is separately `MOCK`
or `SANDBOX`. `registry_source_link` is the query-free endpoint/reference used for the
lookup, and `retrieved_at` must be timezone-aware UTC. Naive or non-UTC timestamps cause
a safe mapping failure. Raw payloads, auth headers, and credentials are not retained.

This prepares later registry-reference proof mapping under D-006/D-012; it does not
complete or submit GoldTier proof metadata.

## Error handling

The HTTP/status translations below are a **PROJECT-DEFINED PROVISIONAL ADAPTER POLICY**
for synthetic Phase 02 testing. They are not confirmed ACRA subscriber semantics and
must be reconciled with Q-012 before live verification.

| Source condition | Safe connector/application code | Behavior |
|---|---|---|
| HTTP 404 | `ACRA_ENTITY_NOT_FOUND` | Normal terminal failed case; no GoldTier call |
| Missing/invalid config or authorizer | `ACRA_CONFIGURATION_ERROR` | Safe 503 after case acceptance, or safe composition failure at startup |
| HTTP 401/403 | `ACRA_AUTHENTICATION_ERROR` | Terminal failed case; no downstream call |
| HTTP/client timeout | `ACRA_TIMEOUT` | Terminal failed case; no downstream call |
| HTTP 429/5xx or network transport failure | `ACRA_SERVICE_UNAVAILABLE` | Terminal failed case; no downstream call |
| Invalid JSON/schema/UEN mismatch/unexpected success status | `ACRA_MALFORMED_RESPONSE` | Terminal failed case; no downstream call |
| Deterministic mapper precondition failure | `ACRA_SOURCE_MAPPING_FAILED` | Terminal failed case; no downstream call |
| Other connector implementation failure | `ACRA_CONNECTOR_UNEXPECTED_FAILURE` | Sanitized terminal failure; no downstream call |

Original exception text, stack traces, response bodies, auth data, and implementation
details are discarded. The Phase 01 unexpected-failure fallback remains for untyped
failures. No retry engine is added.

Typed connector exceptions may retain private diagnostic context internally, but their
public code/message are fixed by trusted application error mappings. Adapter-provided
context and underlying causes cannot automatically become API responses, persisted
errors, or workflow events.

## Mode switching and API/UI

Mock mode is the default and requires no external configuration. Sandbox mode is
explicit and fails closed when required backend configuration is missing. Mock GoldTier
is the only target mode.

The create/get case routes remain unchanged. The existing read-only discovery endpoint
returns safe connector environment metadata: four synthetic scenarios in Mock mode and
an empty scenario list in Sandbox mode. Internal canonical/proof metadata retains the
query-free registry endpoint reference, while a dedicated browser response projection
omits it and exposes only source system, environment, and sourcing timestamp. The UI
renders `ACRA Mock` or `ACRA Sandbox` and always `GoldTier Mock`; it never receives the
configured endpoint, auth headers, or secret settings and never calls ACRA directly.

## Live verification status

As of 10 August 2026:

- Connector implementation foundation: implemented and synthetic-contract tested.
- Live ACRA sandbox smoke test: NOT EXECUTED / BLOCKED.
- Blocker: Q-012 (authoritative subscribed operation/auth schema, authorized sandbox
  URL/access, and approved credential delivery).

`scripts/acra_sandbox_smoke.py` is manual and opt-in. Normal CI never invokes it. The
script prints only `EXECUTED`, `NOT EXECUTED`, or `FAILED` with safe summaries; it does
not print the UEN, configuration, headers, credential, or response payload. Reusable
connector composition is held in a side-effect-free module, so the disabled guard runs
before settings validation or connector construction and invalid configuration is
contained by the script's sanitized failure boundary.

## Known limitations and Phase 03 handoff

- The tracked decoder schema must be reconciled with the authoritative ACRA subscriber
  contract before live verification; it is not a generated ACRA client.
- Cases remain process-local/in-memory and the workflow remains synchronous.
- The existing Phase 01 synthetic UEN input pattern remains a demo validation rule.
- Business activities, officers/shareholders, documents, confidence scoring, ownership,
  UBO, and related parties are deliberately not modeled.
- GoldTier remains fully mocked and real GoldTier/PingFed is still NOT READY.

Phase 03 may consume the canonical/provenance result only within its separately approved
scope. Phase 02 does not implement or pre-empt any Phase 03 feature.
