# Phase 01 Planner Handoff — Mocked End-to-End Vertical Slice

## Goal

Build the smallest complete, credential-free Singapore new-to-bank onboarding flow
through the established application boundaries:

`Mock ACRA -> ACRA connector -> canonical entity -> orchestration -> GoldTier connector -> Mock GoldTier`

The slice proves that a user can submit a synthetic Singapore UEN, observe safe
workflow history, and receive a deterministic mock GoldTier result. It does not claim
real ACRA or GoldTier interoperability or implement the sponsor's unresolved
Ready-for-Approval transition.

## Final implementation scope

### Canonical domain

- Define only the legal-entity, address, source metadata, case, workflow-event, and
  mock-result fields needed by this phase.
- Keep ACRA source payloads and GoldTier contract DTOs outside the canonical domain.
- Use UUID case/correlation/idempotency identifiers and UTC ISO-8601 timestamps.
- Retain safe case history containing stages, outcomes, identifiers, and sanitised
  error codes/messages only.

### Mock ACRA boundary

- Define an ACRA connector protocol and a `MockAcraConnector` implementation.
- Supply entirely synthetic Singapore scenarios for a valid SME, an incomplete
  entity, GoldTier failure/partial paths, and unknown UEN behavior.
- Map the mock source payload into the canonical entity in a dedicated mapper.
- Ensure orchestration calls the connector and never reads fixture data directly.

### Mock GoldTier boundary

- Define a GoldTier connector protocol and a credential-free
  `MockGoldTierConnector`; add no HTTP, PingFed, token, or credential code.
- Model and exercise only `searchParty`, `createShellCustomer`, `createPolicy`, and
  `amendParty` for the Phase 01 sequence.
- Keep `POST /v1/eds/parties/{partyId}/amend` as the documented connector route.
- Use only `X-Source-Case-Id` and `sourceContext.sourceCaseId`, with matching values.
- Require `countryOfIncorporation` for shell creation and require
  `customerExternalSystem` plus `customerExternalSystemKey` for policy creation under
  the Phase 00 provisional contract.
- Use standalone-operation structure/enums and the sponsor-directed mandatory-field
  overlays; do not use quarantined sponsor JSON or derive enums from it.
- Support deterministic not-found search, success, validation failure, and useful
  partial-success behavior without modelling every GoldTier response.

### Orchestration and API

- Implement the application-level state sequence `REQUESTED`, `REGISTRY_FETCHED`,
  `VALIDATED`, `GT_SEARCHED`, `GT_SHELL_CREATED`, `GT_POLICY_CREATED`, `GT_ENRICHED`,
  and `COMPLETED`, with terminal `REVIEW_REQUIRED` and `FAILED` paths.
- Stop before GoldTier when canonical required data is incomplete and route the case
  to human review.
- Never mark a case `COMPLETED` unless every required GoldTier stage succeeds.
- Store cases in an explicitly temporary in-memory repository for this phase.
- Expose `POST /api/onboarding/cases`, `GET /api/onboarding/cases/{case_id}`, and a
  small read-only mock-scenario discovery endpoint.
- Keep GoldTier EDS paths private to the connector/contract boundary.

### Frontend

- Replace the foundation page with a usable simulated onboarding page.
- Allow UEN selection or entry and start a case through the application API.
- Render canonical company information, ordered workflow history, current status,
  safe errors, and the resulting mock GoldTier identifier/result.
- Clearly and persistently label the environment as simulated/mock.
- Render `REVIEW_REQUIRED` and `FAILED` outcomes distinctly.

### Verification and documentation

- Add backend/domain tests for mapping, happy path, unknown UEN, incomplete data,
  GoldTier validation failure, partial success, workflow order, and no false
  completion.
- Add contract tests for canonical mock DTOs/fixtures, mandatory overlays, canonical
  amend/source-case names, and absence of quarantined/stale fields.
- Add frontend tests for request behavior, happy-path/stage rendering, mock labelling,
  and review/error states.
- Document the implemented architecture, boundaries, states, scenarios, limitations,
  and later-phase replacements in `docs/architecture/PHASE_01_VERTICAL_SLICE.md`.
- Update setup/run documentation and CI naming/scope where needed.

## Acceptance criteria

1. A user can submit the valid synthetic UEN and receive a completed case containing
   canonical entity details, the full ordered workflow, and a mock GoldTier party ID.
2. The orchestration service depends on connector interfaces; no application service
   reads ACRA fixtures or uses raw external HTTP payloads directly.
3. Unknown UEN returns a persisted `FAILED` case with a safe registry-not-found event.
4. Incomplete source data returns `REVIEW_REQUIRED` before any GoldTier operation.
5. A deterministic mock GoldTier validation error returns `FAILED`, records no later
   successful stages, and never reports `COMPLETED`.
6. A deterministic partial outcome returns `REVIEW_REQUIRED` and exposes a sanitised
   result without false completion.
7. Phase 01 GoldTier requests satisfy the provisional mandatory fields, canonical
   source-case equality rule, and UUID v4 idempotency/correlation rules.
8. No tracked mock fixture imports, copies, or derives values from invalid/quarantined
   sponsor JSON; stale DSD-specific source-case fields and the stale amend route are
   absent from Phase 01 implementation and fixtures.
9. The frontend visibly labels the environment as simulated, renders all workflow
   stages returned by the API, and displays completed, review, and failed outcomes.
10. Backend tests, Ruff, mypy, frontend typecheck/tests/build, contract tests, the
    secret scanner, `git diff --check`, and equivalent untracked-file whitespace
    checks all pass.
11. No real external connector, credential/authentication feature, IDP, UBO,
    relationship, hierarchy, Camunda, Ready-for-Approval transition, analytics, or
    additional jurisdiction is introduced.
12. Phase completion documentation states assumptions, limitations, remaining
    sponsor questions, and combined Quality Gate readiness without claiming real
    integration readiness.

## Explicit assumptions

- Phase 01 uses process-local in-memory cases; persistence across restarts is not an
  acceptance requirement.
- Starting a case executes the deterministic mock flow synchronously; the event model
  preserves an upgrade path to asynchronous orchestration later.
- Basic deterministic validation is limited to Phase 01 canonical presence/format
  checks and is not represented as the unresolved sponsor validation split.
- A partial result in a required onboarding stage requires human review rather than
  completion.
- Mock external-system and policy identifiers are development constants only, not
  sponsor-confirmed Singapore mapping values.

## Non-goals

Real ACRA, Singpass, real GoldTier/PingFed/credentials, IDP/PDF processing, UBO
calculation, relationship orchestration, hierarchy creation/retrieval, Ready-for-
Approval, Camunda, analytics, a full exception workbench, and AU/MY/HK connectors are
excluded. Phase 02 must not begin from this task.
