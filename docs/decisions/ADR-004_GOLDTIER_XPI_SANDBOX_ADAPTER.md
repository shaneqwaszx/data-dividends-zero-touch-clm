# ADR-004 — GoldTier XPI sandbox adapter under the existing target ledger

## Status

Proposed

## Date

2026-09-24

## Context

The accepted POC has one GoldTier target port, an EDS-shaped deterministic Mock
adapter, provider-neutral immutable submission input and a target ledger that owns
operation order and no-replay recovery. The sponsor-supplied XPI guide and Postman
collection now establish a materially different six-operation sandbox dialect. Its
customer Search keys, flat Shell/Policy/Amend bodies, `user_id` header and related-party
`childId` dependency cannot be represented truthfully by renaming the Mock DTOs.

The supplied sandbox request model has been observed to return HTTP 200 with an empty
JSON array for bounded no-match searches. Non-empty response shapes, production
authentication, PingFed, production interoperability and the related-party child-ID
lifecycle remain unproved.

## Decision

Add an explicit `sandbox` composition beside the default `mock` composition under the
existing `GoldTierConnector` target boundary. Keep XPI DTOs, exact serialization,
bounded HTTPS/TLS 1.3 transport and response decoding in focused XPI connector/mapper
modules. The historical EDS Mock DTOs and deterministic Mock behavior remain supported
unchanged.

The existing target execution ledger remains the only operation-order, intent,
outcome, recovery and no-replay owner. It receives immutable provider-neutral case
input, including a case-bound target-policy snapshot. The existing policy catalogue is
the only editable/versioned source for institution-specific target values. The existing
entity-resolution engine is the only candidate-resolution owner and consumes bounded
safe XPI Search projections; XPI transport does not make identity decisions.

Sandbox composition is explicit and fail closed. A sandbox configuration, validation,
transport or decoding failure never falls back to Mock. Sandbox evidence is labelled
`SANDBOX / PARTIAL`; production remains not implemented and not verified.

For an existing CLM submission, the retained submission plan—not mutable process
configuration—is the provider-identity authority. The plan freezes one valid
environment/classification pair; its mode is copied into the immutable submission
input. The configured mapper and connector are compatibility assertions only and must
both match before the target ledger or transport is touched. Provider drift raises a
typed sanitized failure and never switches dialects.

## Alternatives considered

- Rename or loosen the Mock DTOs to fit XPI: rejected because it corrupts the accepted
  Mock compatibility contract and mixes distinct provider dialects.
- Put XPI Search matching or target defaults in the connector: rejected because that
  would duplicate entity-resolution and policy authority inside an untrusted adapter.
- Add a second execution service/ledger for sandbox: rejected because it would create a
  competing replay owner and divergent ordering semantics.
- Dispatch directly from a diagnostic script: rejected for mutations because it would
  bypass the target ledger. Read-only contract/reachability diagnostics may remain
  separate and sanitized.
- Make no runtime change: rejected because documentation alone cannot satisfy the
  authorized bounded sandbox execution and no-replay acceptance evidence.

## Consequences

- Composition and target mapping gain one explicit dialect branch, while execution,
  policy, identity and persistence owners remain singular.
- Target-specific required values must be populated through authority-labelled policy
  rules and frozen into each new case. Missing or sentinel values block before network
  dispatch.
- Request preview can reuse the case-scoped CLM plan surface and the same preparation
  result used for dispatch; it makes no provider call.
- The XPI adapter must tolerate no more than the bounded response envelopes supported
  by tests and sanitized observations. Unknown/malformed results fail closed.
- Related-party DTO transformation may be implemented locally, but external RP calls
  remain blocked until the `childId` lifecycle and relationship-value authority are
  proved.

## Architecture invariants affected

- Preserved: source DTO -> canonical evidence -> target mapper; no direct ACRA-to-XPI
  mapping.
- Preserved: one Decimal ownership engine and one entity-resolution owner.
- Preserved: one policy catalogue/snapshot owner and one case-envelope persistence
  owner.
- Preserved: one target ledger and no automatic replay after an uncertain mutation.
- Added: explicit provider-mode binding and authority-labelled target preparation are
  part of the immutable submission input.
- Added: the immutable CLM plan owns provider identity across preparation, execution,
  persistence reconstruction and presentation; mapper/connector configuration cannot
  reinterpret it.
- Added: Sandbox and Production classifications remain distinct in configuration, API,
  UI and evidence.

## Security and persistence implications

XPI permits HTTPS only, verified certificates, TLS 1.3, bounded timeouts and response
bodies, no redirects, strict URL/query construction and fixed safe errors. The supplied
`user_id` is backend-only configuration and must not appear in logs, previews, reports
or browser responses. Raw provider bodies and real customer data are not retained.

The target-policy snapshot is an additive optional field within the current case policy
snapshot and submission input. Older schema-v5 cases remain readable without silent
rewrite. Memory and Mongo use the same strict model/CAS owners. Any attempted mutation
with an unknown outcome remains non-replayable in the existing ledger.
Schema-v5 reconstruction rejects contradictory plan, submission-input and matching
ledger provider modes while preserving plan-only records and the v1-v4 read path. No
schema-v6 envelope is created.

## Migration and retirement implications

Mock remains the default supported compatibility path, not a fallback. Existing cases
without target-policy data keep their prior Mock interpretation. XPI cases require an
explicit sandbox composition and complete target preparation. Removing sandbox later
requires disabling its explicit mode and retiring its focused adapter; it does not
change historical Mock DTOs or records.

## Verification

- Strict RED/GREEN tests for DTOs, Postman path/header agreement, mapping, preview,
  missing enrichment, transport security, Search outcomes, safe errors and response
  bounds.
- Orchestration tests for exact/no-match/ambiguous/conflict behavior, zero Shell calls,
  existing-party routing, ledger ordering and uncertain-write no replay.
- Policy immutability, schema-v5 backward reads, memory/Mongo parity, RBAC/cache and
  Mock regressions.
- Architecture, security, provider-readiness, project-state, contract, full backend,
  frontend, E2E/lifecycle and independent quality-gate evidence.

## Revisit conditions

Revisit when GoldTier supplies production authentication/PingFed details, corrected
response OpenAPI/examples, mandatory-field vocabularies, a related-party child creation
lifecycle, or a sponsor-approved replacement for provisional target policies.

## Related contracts and sponsor questions

- `docs/contracts/GOLDTIER_CONTRACT_BASELINE.md`
- `docs/contracts/GOLDTIER_CONTRACT_DISCREPANCIES.md`
- `docs/contracts/EXTERNAL_PROVIDER_ACTIVATION_CONTRACT.md`
- `docs/contracts/INTEGRATION_ADAPTER_CONTRACTS.md`
- `docs/integration/GOLDTIER_XPI_MAPPING_MATRIX.md`
- `docs/sponsor-questions/OPEN_QUESTIONS.md` (Q-001, Q-006, Q-007, Q-009, Q-010,
  Q-011, Q-018)
