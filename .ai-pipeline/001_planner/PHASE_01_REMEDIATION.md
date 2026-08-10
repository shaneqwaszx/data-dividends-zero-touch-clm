# Phase 01 Remediation Planner Handoff

## Goal

Close only the Phase 01 Quality Gate findings that could strand accepted cases, create
duplicate target customers, or force connector-boundary redesign. Preserve all five
existing deterministic scenarios and remain entirely credential-free and mock-only.

## Bounded implementation scope

### Terminal unexpected failures

- Add an application infrastructure-error boundary carrying only case/correlation IDs
  and a stage-specific sanitized code/message.
- Guard ACRA retrieval, ACRA-to-canonical mapping, GoldTier search, shell creation,
  policy creation, and amend/enrichment.
- On any unexpected exception after case acceptance, append and persist one terminal
  `FAILED` event before raising the sanitized application error.
- Return a safe HTTP 5xx response containing the retrievable case ID while suppressing
  exception text, traceback, payload, credential, and implementation details.
- Stop downstream operations immediately.
- Keep modeled GoldTier validation, partial-success, and explicit search outcomes on
  their existing controlled workflow paths rather than treating them as exceptions.
- Add a connector error type for implementation boundaries and retain a final
  orchestration catch for nonconforming/unexpected connector exceptions.

### GoldTier search semantics

- Replace generic search results with an explicit typed result containing
  `NO_MATCH`, `MATCH_FOUND`, or `FAILURE`.
- Permit shell creation only after `NO_MATCH`.
- Route `MATCH_FOUND` to a documented, non-destructive `REVIEW_REQUIRED` terminal
  state because sponsor behavior for an existing NTB candidate is unresolved.
- Route a modeled search failure to `FAILED`; unexpected thrown search failures use
  the infrastructure-error boundary.
- Move search-request construction into the GoldTier mapper with the other target
  request builders.

### Input normalization

- Trim and uppercase UEN input in the FastAPI request model before service invocation.
- Reject blank-after-trim input with 4xx.
- Apply the existing `nine digits plus one uppercase letter` check at the API boundary
  as an explicitly Phase 01 synthetic/demo rule, not a production ACRA validation
  claim.
- Continue accepting a well-formed unknown synthetic UEN and terminalizing it as
  `FAILED/ACRA_ENTITY_NOT_FOUND` after Mock ACRA lookup.

### ACRA provenance and demo separation

- Represent canonical source provenance as business source `ACRA` plus a separate
  `MOCK`, `SANDBOX`, or `LIVE` environment value.
- Keep the connector payload's source environment explicit and map it into the
  canonical provenance model.
- Update frontend types/rendering so source and simulation mode come from backend
  response data.
- Remove mock-scenario discovery from `AcraConnector` and `OnboardingService`.
- Add a dedicated Phase 01 mock scenario catalogue providing discovery metadata,
  simulation profile, and explicit GoldTier mock-behavior configuration.
- Keep `GET /api/onboarding/mock-scenarios`, returning catalogue-owned discovery data.

### Mock isolation and mapper safety

- Remove imports from Mock GoldTier to Mock ACRA.
- Configure deterministic policy-failure and partial-amend keys explicitly at
  composition time.
- Track the external key associated with a created policy by mock party ID so amend
  behavior depends on relevant prior request data, not parsing `source_case_id`.
- Replace runtime mapper `assert` preconditions with explicit mapping errors; the
  orchestration boundary terminalizes any resulting unexpected failure safely.

### Regression coverage

- Add recording/raising protocol fakes covering ACRA fetch and every GoldTier stage.
- For each injected exception, verify safe 5xx, retrievable terminal `FAILED` case,
  sanitized event, and absence of later calls.
- Add explicit search `NO_MATCH`, `MATCH_FOUND`, and `FAILURE` tests.
- Add whitespace-only and well-formed-unknown UEN API tests.
- Add multiple-case isolation and workflow ordering/terminal invariants.
- Preserve and procedurally re-verify the original five deterministic outcomes.
- Update frontend and contract tests for source-neutral provenance and backend-provided
  simulation metadata.

## Acceptance criteria

1. Every accepted case whose required connector/mapping stage throws ends in persisted
   `FAILED` with a stage-specific sanitized event before a safe HTTP 5xx is returned.
2. The 5xx response contains a retrievable case ID and no original exception text,
   traceback, payload, credential, or internal implementation detail.
3. No connector operation after the failing stage is called.
4. Returned modeled business outcomes remain distinct: validation failure is
   `FAILED`, partial amend is `REVIEW_REQUIRED`, and neither raises infrastructure 5xx.
5. Only explicit search `NO_MATCH` permits shell creation.
6. `MATCH_FOUND` creates no shell and ends in `REVIEW_REQUIRED` with a safe existing-
   candidate event; modeled search `FAILURE` ends in `FAILED`.
7. Whitespace-only UEN returns 4xx without creating a case; normalized lowercase or
   padded valid input is accepted; well-formed unknown UEN creates a normal failed
   onboarding case.
8. Canonical provenance is `ACRA` plus environment, with no `MOCK_ACRA` business-source
   literal in backend/frontend domain models.
9. A future ACRA connector implements retrieval only; demo discovery is owned by the
   separate catalogue.
10. Mock GoldTier imports no Mock ACRA implementation/constants and does not parse UEN
    from source-case formatting.
11. Runtime mapper invariants use explicit exceptions rather than `assert`.
12. Original outcomes remain: `202400001A -> COMPLETED`, `202400002B ->
    REVIEW_REQUIRED`, `202400003C -> FAILED`, `202400004D -> REVIEW_REQUIRED`, and a
    well-formed unknown UEN `-> FAILED`.
13. Backend, Ruff, strict mypy, repository, contract, validator, scanner, frontend,
    dependency-integrity, build, diff, and untracked-whitespace checks pass.

## Explicit non-goals

No real ACRA/GoldTier HTTP, Singpass, PingFed, credentials, database, PostgreSQL,
Redis, queue/worker, retry engine, Camunda, IDP/PDF, UBO, hierarchy, related parties,
Ready-for-Approval integration, or Phase 02 functionality. In-memory synchronous
execution remains accepted Phase 01 scope.
