# Phase 01 Mocked End-to-End Vertical Slice

## Purpose and boundary

Phase 01 proves that a synthetic Singapore legal entity can travel through the complete
application architecture without credentials or real external systems. It is a mock-
development slice, not evidence of ACRA or GoldTier interoperability.

```text
React onboarding page
        |
        v
FastAPI application API
        |----------------------> Phase01MockScenarioCatalogue
        |                              |
        |                              `--> simulation profile + demo discovery
        v
OnboardingService --------------------> safe in-memory case history
        |                                      |
        |                                      v
        |                              API/UI status response
        |
        +--> AcraConnector
        |        |
        |        `--> MockAcraConnector --> synthetic source payload
        |                                      |
        |                                      v
        |                              dedicated ACRA mapper
        |                                      |
        |                                      v
        +------------------------ canonical legal entity
                                               |
                                               v
                                      dedicated GoldTier mapper
                                               |
                                               v
                                      GoldTierConnector
                                               |
                                               `--> MockGoldTierConnector
```

No service reads a mock fixture directly. The source connector owns ACRA-shaped data,
the ACRA mapper produces the canonical entity, and the GoldTier mapper produces typed
target-contract requests. The frontend sees only application-facing case resources.

## Canonical model

The Phase 01 domain deliberately contains only:

- case ID, source case ID, and correlation ID;
- requested UEN/registration number;
- legal name, country of incorporation, party type, and registered address;
- business source system (`ACRA`), separate environment (`MOCK` or `SANDBOX`),
  registry source link, and UTC retrieval time;
- current workflow state and safe ordered workflow events;
- a small mock GoldTier result summary; and
- an optional sanitised error code/message.

Raw ACRA payloads, raw GoldTier request/response bodies, credentials, documents,
related parties, ownership, UBO fields, and the full GoldTier data dictionary are not
part of the canonical model.

## Connector boundaries

### ACRA

`AcraConnector` exposes corporate-registry retrieval only. `MockAcraConnector` returns
in-process, entirely synthetic Singapore fixtures and does not perform HTTP. An unknown
UEN returns no source record. The orchestration service receives the connector payload
through this interface and immediately maps it to the canonical entity.

Demo discovery is intentionally separate. `Phase01MockScenarioCatalogue` owns scenario
labels, backend simulation metadata, and explicit cross-mock behavior configuration.
A future real ACRA connector therefore does not need to implement mock-lab discovery.

Canonical provenance always identifies the business source as `ACRA`; mockness is the
separate `environment=MOCK` value. Phase 02's connector can emit `SANDBOX` without
changing the business source or orchestration boundary.

### GoldTier

`GoldTierConnector` exposes only `searchParty`, `createShellCustomer`, `createPolicy`,
and `amendParty`. `MockGoldTierConnector` is deterministic and contains no HTTP,
PingFed, token, TLS, or credential logic. Its typed requests apply the Phase 00
provisional contract:

- canonical amend path `POST /v1/eds/parties/{partyId}/amend`;
- `X-Source-Case-Id` equal to `sourceContext.sourceCaseId`;
- UUID correlation and UUID v4 idempotency identifiers;
- required shell `countryOfIncorporation` overlay; and
- required policy `customerExternalSystem` and `customerExternalSystemKey` fields.

The external-system, party-role/type, and policy values used by this mock are explicit
development constants only. They are not represented as sponsor-confirmed Singapore
value-list mappings. Invalid/quarantined sponsor JSON is not imported or copied.

`searchParty` has a dedicated result rather than reusing generic write-operation
outcomes:

- `NO_MATCH` permits shell creation;
- `MATCH_FOUND` prevents duplicate creation and routes the case to
  `REVIEW_REQUIRED`; and
- modeled `FAILURE` routes the case to `FAILED`.

The existing-match review path is deliberately non-destructive while sponsor behavior
for an existing NTB candidate remains unresolved. It is not a claim about real
GoldTier production workflow.

Mock GoldTier behavior is configured at composition time using the demo catalogue. It
does not import Mock ACRA constants. Policy requests associate the external key with
the created mock party, so later partial-amend behavior uses prior request data rather
than parsing UENs from source-case identifiers.

## End-to-end orchestration

`POST /api/onboarding/cases` executes the bounded mock flow synchronously:

1. create and store the case with safe identifiers;
2. retrieve a source record through `AcraConnector`;
3. map the source record into the canonical entity;
4. run Phase 01 presence/format validation;
5. search through `GoldTierConnector`;
6. create a shell after the deterministic no-match outcome;
7. create the mock Singapore policy;
8. amend/enrich the mock party;
9. record each safe state transition; and
10. return the current terminal case representation.

Required-stage failures stop processing. A partial required amendment records the
partial `GT_ENRICHED` outcome and routes the case to human review. Neither path can
produce `COMPLETED`.

Every connector and mapping call is also protected by a stage-specific unexpected-
failure boundary. Once `REQUESTED` has been persisted, an exception during ACRA fetch,
ACRA mapping, search, shell, policy, or amend first appends and persists a sanitized
terminal `FAILED` event. The application then returns HTTP 503 with only safe code,
message, case ID, and correlation ID. The original exception text, traceback, payload,
credentials, and implementation details are not included, and no downstream stage is
called. The case remains retrievable through the normal GET endpoint.

This infrastructure path is distinct from modeled GoldTier business outcomes:
validation failure still returns a normal terminal failed case, while partial success
still routes to review. Phase 01 adds no retry framework.

## Workflow states

| State | Meaning |
|---|---|
| `REQUESTED` | Application accepted a synthetic UEN and created a case. |
| `REGISTRY_FETCHED` | Mock ACRA returned a source record and it was mapped. |
| `VALIDATED` | The bounded Phase 01 canonical checks passed. |
| `GT_SEARCHED` | Mock GoldTier search completed with explicit match/no-match semantics. |
| `GT_SHELL_CREATED` | Mock shell customer creation succeeded. |
| `GT_POLICY_CREATED` | Mock Singapore policy creation succeeded. |
| `GT_ENRICHED` | Mock amend succeeded or produced a recorded partial outcome. |
| `COMPLETED` | Every required Phase 01 mock stage succeeded. |
| `REVIEW_REQUIRED` | Missing canonical data or a partial target outcome requires a human. |
| `FAILED` | Registry not-found or a required mock target operation failed. |

Each event contains only its sequence, stage, outcome, UTC timestamp, case/correlation
identifiers, and a sanitised message/code. Complete corporate or target payloads are
not written to history or normal logs.

## Mock scenarios

| Synthetic UEN | Scenario | Terminal result |
|---|---|---|
| `202400001A` | Complete synthetic SME; all target operations succeed | `COMPLETED` |
| `202400002B` | Registered address absent | `REVIEW_REQUIRED` before GoldTier |
| `202400003C` | Policy operation returns representative validation failure | `FAILED` |
| `202400004D` | Amend returns representative `207`-style partial success | `REVIEW_REQUIRED` |
| Any other UEN | No Mock ACRA record | `FAILED` with safe not-found code |

Names, addresses, identifiers, and outcomes are project-created test data; they do not
copy sponsor customer/company data.

## Application API and UI

The frontend uses only:

- `GET /api/onboarding/mock-scenarios`;
- `POST /api/onboarding/cases`; and
- `GET /api/onboarding/cases/{case_id}`.

The discovery endpoint returns a backend-owned simulation profile plus the scenario
list. The React page uses that profile and canonical source metadata rather than
duplicating `MOCK_ACRA` as domain truth.

At the POST boundary, UEN input is trimmed and uppercased before validation or case
creation. Blank-after-trim input is rejected with 422. The `nine digits plus one
uppercase letter` pattern is a Phase 01 synthetic/demo check only; it is not presented
as the final production ACRA UEN rule. A well-formed unknown UEN remains a valid
onboarding request and reaches the modeled `ACRA_ENTITY_NOT_FOUND/FAILED` outcome.

GoldTier EDS paths do not become browser-facing routes. The React page supports typed
or selected UENs and renders canonical company data, safe workflow history, terminal
review/failure states, and the mock GoldTier identifier/result. Vite proxies `/api` to
local FastAPI during development.

## Assumptions, limitations, and later replacements

- Cases are process-local and in-memory. Restarting the backend clears them, and
  multiple backend processes do not share state.
- Starting a case runs the deterministic mock flow synchronously. The repository
  interface and event model preserve later persistence/asynchronous replacement paths.
- Basic validation checks only the documented Phase 01 synthetic UEN format and the presence of legal
  name, Singapore country, party type, and registered address. It is not the sponsor's
  still-unresolved final validation responsibility split.
- Phase 02 adds a selectable `AcraSandboxConnector` behind the same retrieval boundary;
  exact subscribed-contract binding and live verification remain separately blocked.
- A later GoldTier phase replaces `MockGoldTierConnector` only after the TLS 1.3,
  PingFed, environment, and credential-containment blockers are resolved.
- IDP, confidence scoring, related parties, deterministic ownership/UBO processing,
  seeded hierarchy retrieval, and richer review handling belong to later phases.
- The actual Ready-for-Approval/four-eye transition remains sponsor question Q-001;
  `COMPLETED` means only that the required Phase 01 mock stages succeeded.
- Singapore GoldTier mappings/value lists and the validation responsibility split
  remain Q-007 and Q-005. Mock constants must not become real-integration assertions
  without confirmation.
