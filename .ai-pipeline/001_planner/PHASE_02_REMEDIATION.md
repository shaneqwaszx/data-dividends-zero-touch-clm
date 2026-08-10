# Phase 02 Remediation Planner Handoff

## Goal

Close every implementation and documentation finding in the Phase 02 Quality Gate
without beginning Phase 03 or changing the approved architecture:

`Mock or sandbox ACRA -> ACRA source DTO -> ACRA mapper -> canonical entity -> existing OnboardingService -> Mock GoldTier`

Mock ACRA remains the credential-free default. `AcraSandboxConnector` remains behind
the existing `AcraConnector` boundary. The current project decoder remains synthetic
and non-authoritative. GoldTier remains mock-only.

## Bounded remediation scope

### Source-integrity validation

- Apply explicit trim/nonblank validation at the ACRA source DTO/project decoder
  boundary for the UEN, legal entity name, entity type, required company country code,
  and required components of any supplied registered address.
- Preserve the Phase 01 incomplete-address review scenario: an absent address may still
  reach the existing canonical review rule, but a supplied address with blank required
  components is malformed source data.
- Treat malformed required source data as `ACRA_MALFORMED_RESPONSE`; persist terminal
  `FAILED`, keep the case retrievable, stop all Mock GoldTier work, and never echo the
  rejected value.
- Add parameterized regressions for empty, whitespace-only, trimmed-valid, and
  independently malformed required fields. Do not add an undocumented production ACRA
  format or value-list rule.

### Canonical defense in depth

- Strengthen the small source-neutral canonical minimum checks so semantically blank
  registration number, legal name, party type, address line 1, postal code, or address
  country cannot proceed to GoldTier even if a future connector bypasses its own source
  validation.
- Keep source validation and canonical business invariants separate; do not duplicate
  the complete provisional decoder schema in the domain service.
- Preserve the existing human-review outcome for incomplete canonical data.

### Trusted public connector errors

- Remove arbitrary public code/message overrides from connector exception construction.
- Keep fixed public codes/messages owned by trusted typed errors; optional internal
  diagnostic context may be retained privately but must never automatically reach an
  API response, workflow event, or persisted safe error.
- Add authentication and representative connector-family sentinel regressions proving
  safe HTTP 503, terminal retrievable `FAILED`, no sentinel leakage, and no GoldTier
  activity.

### Import-safe optional smoke script

- Ensure the opt-in guard runs before settings validation or connector construction.
- Move reusable connector/service composition into a side-effect-free module if needed;
  do not import the module-level FastAPI application from the smoke script.
- For disabled, missing-config, invalid-config, and safe injected-success paths, emit
  only sanitized `NOT EXECUTED`, `FAILED`, or `EXECUTED` output with no traceback, UEN,
  credentials, headers, raw settings, or payload.

### Browser/internal provenance split

- Retain `registry_source_link` and the UTC retrieval timestamp in the internal
  canonical/proof metadata.
- Introduce an explicit browser-facing case response model that exposes only the source
  system, source environment, and sourcing timestamp needed by the UI; omit the full
  registry endpoint/reference.
- Remove `registry_source_link` from frontend types and add API regressions proving the
  internal value remains while create/get browser responses omit it.

### Provisional status policy and documentation

- Label current 404, 401/403, 408/504, 429, and 5xx translations as a
  **PROJECT-DEFINED PROVISIONAL ADAPTER POLICY** pending Q-012.
- Update only relevant Phase 02 architecture, mapping, README, comments, and tests to
  describe nonblank source validation, canonical defense, trusted public errors,
  browser/internal provenance separation, and import-safe smoke behavior.
- Preserve Q-012 unchanged. Do not infer the subscribed endpoint/path, real schema,
  authentication, errors, access, credentials, TLS/mTLS/private CA, or rate limits.

## Required regression evidence

- Every required source string: empty, whitespace-only, and trimmed-valid cases.
- Each required address component independently malformed with terminal
  `ACRA_MALFORMED_RESPONSE`, retrievable case, and zero GoldTier calls.
- A source-valid but canonically malformed future/custom connector cannot proceed to
  GoldTier.
- Private sentinels carried by typed authentication and other representative connector
  errors remain absent from HTTP and persisted events.
- Internal registry proof metadata retains its endpoint while browser create/get JSON
  and frontend types omit it.
- Smoke disabled/invalid paths produce no traceback or sensitive output.
- Original Phase 01 outcomes remain exactly:
  `COMPLETED`, `REVIEW_REQUIRED`, `FAILED`, `REVIEW_REQUIRED`, `FAILED` for the four
  known UENs plus a well-formed unknown UEN.
- Synthetic sandbox success still traverses transport, decoder, source DTO, mapper,
  existing service, and Mock GoldTier.

## Validation

Run backend tests, Ruff, strict mypy, repository and contract regressions, Phase 00/01/02
tests, new adversarial and smoke tests, secret tests/scanner, sponsor GoldTier validator,
frontend typecheck/tests/build, `pip check`, npm dependency integrity,
`git diff --check`, and equivalent untracked-file whitespace checks. Independently
reconfirm whitespace entity type, blank address fields, typed-error sentinel safety,
internal-versus-browser provenance, and invalid-config smoke output.

## Explicit non-goals and blockers

- Do not start Phase 03.
- Do not add live ACRA credentials, reverse-engineered auth/schema behavior, or execute
  a live smoke call.
- Do not implement real GoldTier, PingFed, IDP/OCR/PDF processing, confidence scoring,
  UBO, related parties, hierarchy, Ready-for-Approval, persistence, queues/workers,
  retries, Camunda, or another registry.
- Live ACRA verification remains blocked by Q-012; real GoldTier remains NOT READY.
- Do not stage, commit, push, or merge.
