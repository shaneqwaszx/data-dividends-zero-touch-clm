# Phase 02 Planner Handoff - ACRA Registry Integration and Ingestion Foundation

## Goal

Introduce the first production-shaped external source boundary for Singapore ACRA
registry ingestion while preserving the complete Phase 01 onboarding workflow:

`Mock or sandbox ACRA -> ACRA source DTO -> ACRA mapper -> canonical entity -> existing onboarding service -> Mock GoldTier`

Phase 02 distinguishes connector implementation readiness from live sandbox
verification. The implementation must remain useful and fully testable without
credentials, but it must never claim that an unexecuted ACRA sandbox call succeeded.
GoldTier remains fully mocked.

## Evidence and access boundary

- Sponsor decisions D-001, D-002, D-006, and D-012 confirm ACRA as the sole live
  registry source and define safe registry-reference provenance requirements.
- Official public ACRA material confirms that the Business Profile API is part of the
  Entity Information Query service and can provide UEN, entity name, business
  activities, incorporation/registration date, and position-holder/owner/partner
  information.
- The repository currently contains no approved ACRA operation schema, subscribed
  endpoint/path, error schema, authentication specification, sandbox base URL, or
  authorized sandbox credentials.
- Therefore Phase 02 may implement and test transport, authorization, parsing,
  configuration, error, DTO, and mapping boundaries with sanitized synthetic
  contract fixtures, but it must keep the exact subscribed ACRA binding isolated and
  explicitly blocked until authoritative subscriber documentation is supplied.
- Do not infer ACRA authentication from the GoldTier PingFed material, public open-data
  APIs, or undocumented examples.

## Final implementation scope

### Preserve Phase 01 architecture

- Keep `OnboardingService` dependent only on `AcraConnector`; do not add transport or
  authentication knowledge to orchestration.
- Preserve all Phase 01 scenarios, state transitions, mock GoldTier behavior, and API
  routes.
- Keep source payload -> canonical model -> GoldTier mapping as separate layers.

### ACRA source and connector boundary

- Refine the ACRA source DTO to include only Phase 02 needs: UEN, legal name, entity
  type, incorporation/registration date, registered address, entity status, and safe
  source metadata.
- Keep optional future officer/shareholder fields out unless a confirmed current
  source schema naturally supplies them and a current mapping requires them.
- Add a neutral `AcraSandboxConnector` HTTP adapter with injectable HTTP transport,
  request authorization, clock, and response decoder boundaries.
- Retrieve by normalized UEN, enforce bounded timeouts, validate the response before
  returning a source DTO, and never expose raw HTTP/client types to orchestration.
- Do not persist or log raw real responses. Tracked response fixtures must be
  synthetic, sanitized, and clearly labelled.

### Authentication and configuration

- Define an authorization/request interface that can add request metadata without
  exposing it to business logic or logs.
- Do not implement an undocumented OAuth, API-key, Singpass, Corppass, or other auth
  flow. The default application composition must fail safely when sandbox mode lacks
  an approved authorization implementation/configuration.
- Support explicit `mock` and `sandbox` connector modes; default to `mock`.
- Sandbox configuration must validate an HTTPS base URL, endpoint/path configuration,
  positive bounded timeouts, and the availability of an authorization provider.
- Keep all private ACRA configuration backend-only. No secret or private configuration
  may enter the application API, frontend, fixture files, logs, or error messages.
- Never weaken TLS verification.

### Canonical mapping and provenance

- Map source DTOs through the dedicated ACRA mapper into the existing source-neutral
  canonical entity.
- Add canonical fields only where justified by Phase 02 source information; any added
  field must remain registry-neutral, documented, and tested.
- Preserve `source_system=ACRA`; represent connector selection separately as
  `environment=MOCK` or `environment=SANDBOX`.
- Store only safe registry proof preparation metadata: an ACRA endpoint/reference and
  a timezone-aware UTC sourcing timestamp. Do not claim GoldTier proof completion.
- Reject or safely fail mapping of non-UTC/naive provenance timestamps and malformed
  required source fields rather than silently coercing uncertain data.

### Safe failures and workflow behavior

- Translate source outcomes into safe typed connector errors for not found,
  authentication/configuration failure, timeout, unavailable service, malformed
  response, mapping failure, and unexpected transport failure.
- Connector errors must contain stable safe codes/messages and must not retain raw
  payloads, credentials, authorization headers, endpoint query secrets, stack traces,
  or underlying exception text.
- Preserve the Phase 01 invariant: once a case is accepted, any unexpected connector
  or mapping failure persists terminal `FAILED`, returns only safe API detail, and
  performs no GoldTier operation.
- A not-found result remains a normal terminal failed case. Do not add retries or
  queues in this phase.

### API and frontend

- Keep `POST /api/onboarding/cases` and `GET /api/onboarding/cases/{case_id}` stable.
- Keep the frontend dependent only on backend case/configuration status; it must never
  call ACRA directly.
- Generalize the safe discovery/status response so the UI clearly shows `ACRA Mock`
  or `ACRA Sandbox` while GoldTier remains mock, without exposing configuration.
- Retain the existing UI structure and make only the minimum labeling/input changes
  needed for the configured source mode.

### Verification and documentation

- Add unit tests for success parsing, not found, timeout, unavailable service,
  malformed response, authentication/configuration failure, and unexpected failure
  sanitization.
- Add mapping tests for UEN, legal name/type/status/incorporation date, registered
  address, ACRA provenance, endpoint reference, and UTC sourcing timestamp.
- Add composition tests for default mock mode, sandbox mode with safe injected fake
  dependencies, missing/invalid sandbox configuration, and unchanged orchestration
  behavior between modes.
- Retain all Phase 01 workflow/API/resilience/contract tests and prove that an ACRA
  failure cannot produce false completion or any GoldTier activity.
- Provide an explicitly opt-in manual live smoke test only when an authoritative
  request binding and authorized local access are available. Exclude it from CI and
  prevent credential/payload output or persistence.
- Create `docs/contracts/ACRA_CANONICAL_MAPPING.md` and
  `docs/architecture/PHASE_02_ACRA_INGESTION.md`; update the README, environment
  template, decision/question logs, and CI naming where Phase 02 changes them.

## Acceptance criteria

1. `MockAcraConnector` remains deterministic and all Phase 01 scenarios retain their
   exact terminal outcomes and downstream call-stopping behavior.
2. `AcraSandboxConnector` implements the existing `AcraConnector` interface and can be
   exercised against an injectable, synthetic HTTP boundary without changing
   `OnboardingService`.
3. External JSON is validated into an ACRA source DTO before mapping; it is never
   deserialized directly into the canonical entity.
4. Successful source parsing and mapping cover UEN, name, type, status,
   incorporation/registration date, registered address, ACRA/SANDBOX provenance,
   endpoint/reference metadata, and a timezone-aware UTC sourcing timestamp.
5. Sandbox mode validates safe backend-only configuration and fails clearly when the
   base/path/auth binding is missing or invalid; local/default and CI execution require
   no credentials.
6. Not found, auth/config, timeout, unavailable, malformed response, mapping failure,
   and unexpected transport failure are covered with stable sanitized outcomes.
7. Every accepted ACRA connector/mapping failure leaves a retrievable terminal
   `FAILED` case, never `COMPLETED`, and records no GoldTier call.
8. The existing onboarding create/get API remains stable, and any environment/status
   response exposes only `ACRA` plus `MOCK`/`SANDBOX` and mock GoldTier metadata.
9. The frontend visibly renders `ACRA Mock` or `ACRA Sandbox`, relies on backend case
   state, and contains no ACRA URL, credential, authorization, or direct ACRA request.
10. All committed ACRA fixtures are synthetic/sanitized and no live response, token,
    credential, private sponsor data, or sensitive transport header is tracked or
    logged.
11. `ACRA_CANONICAL_MAPPING.md` records each field, transformation, requiredness,
    decision confidence, sponsor-confirmation need, and intentionally ignored fields.
12. The architecture document records connector/auth/config/parser boundaries,
    provenance, mode switching, errors, live-verification status, limitations, and
    Phase 03 handoff considerations without beginning Phase 03.
13. Backend tests, Ruff, strict mypy, repository/contract/Phase 01 regressions, ACRA
    tests, secret checks, GoldTier validator regression, frontend typecheck/tests/build,
    dependency integrity, `git diff --check`, and equivalent untracked whitespace
    checks pass.
14. Optional live verification is reported separately as `EXECUTED`, `NOT EXECUTED`,
    or `FAILED`; implementation readiness and live verification readiness are never
    conflated.
15. No real GoldTier/PingFed work, IDP, OCR, confidence scoring, UBO, related party,
    hierarchy, Ready-for-Approval, Camunda, Redis/queues, full database, additional
    registry, or production connectivity is introduced.

## Explicit assumptions and blockers

- The authoritative subscriber-only ACRA request/response and authentication contract
  is not currently available in the approved project material. Exact live binding and
  live sandbox verification are blocked until it is supplied with authorized access.
- Phase 02 synthetic DTO fixtures represent a narrow project adapter contract and must
  be reconciled against the authoritative ACRA schema before live verification.
- ACRA Business Profile/EIQ access may require a subscription; the project must not
  automate around or bypass that access requirement.
- Process-local persistence, synchronous orchestration, mock GoldTier, and the Phase 01
  synthetic UEN format remain accepted technical limits unless a confirmed ACRA
  contract requires a narrowly scoped change.

## Non-goals

Real GoldTier, PingFed, sponsor GoldTier credentials, IDP/PDF/OCR, document confidence,
UBO decisions/calculation, related-party orchestration, relationship graphs, hierarchy
creation/retrieval, `createRelationship`, Ready-for-Approval, Camunda, Redis/queues,
full database persistence, production ACRA connectivity, and any registry outside ACRA
are excluded. Phase 03 must not begin.
