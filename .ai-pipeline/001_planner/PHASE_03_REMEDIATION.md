# Phase 03 Remediation Handoff

## Goal

Close every active finding in `.ai-pipeline/reports/PHASE_03_QUALITY_GATE.md`
without changing the accepted Phase 03 product scope or beginning Phase 04. Preserve
the existing document-review UI, immutable original extraction, accept/reject/correct
semantics, provisional four-field profile, all Phase 01/02 scenarios, all five Phase
03 Mock IDP scenarios, and credential-free/network-free Mock IDP operation.

## Authority and boundary

- This handoff records the bounded remediation assigned on 2026-08-10.
- The Phase 03 planner, AGENTS.md, D-020, and the independent Phase 03 quality gate
  remain controlling evidence.
- The four fields, `0.85` threshold, normalization/comparison rules, upload limit, and
  local review completion rule remain **PROJECT-DEFINED / PROVISIONAL**.
- Q-003, Q-005, Q-013, and Q-014 remain unresolved. Q-012 still blocks live ACRA;
  Q-008/D-018 and sponsor sandbox dependencies still block real GoldTier.

## Required remediation

### 1. Terminalize all post-acceptance processing failures (P03-QG-001)

After the initial document record is persisted, the trusted processing boundary must
cover provider metadata/invocation, result validation, field construction,
normalization/comparison, retained-model construction, clock/timestamps, and repository
updates through `REVIEW_REQUIRED`. Controlled errors keep their fixed projections;
unexpected errors use a fixed sanitized code/message. Every recoverably persistable
failure must end in exactly one terminal failure event, remain retrievable as `FAILED`,
leave the parent case unchanged, expose no exception text, produce no review result,
and call no downstream business connector.

Validate canonical comparison inputs before bounded retained models. Add adversarial
regressions for the gate's 513-character legal name, comparison/model exceptions,
post-validation clock failure, and one-shot update failure with recovery persistence.
Prove that no accepted document remains `PROCESSING`.

### 2. Make the generic IDP boundary provider-neutral (P03-QG-002)

Remove `MockIdpScenario` from `IdpDocumentInput`, `IdpProvider`,
`DocumentProcessingService`, source-neutral domain models, and generic request/response
metadata. Provider-neutral input is document bytes plus the provisional profile;
provider-neutral validated metadata/result crosses the connector boundary. Environment
metadata must support generic modes such as Mock, Local, Sandbox, and Live and must
come from provider/composition output rather than service constants.

Keep deterministic scenario selection only in the Mock provider and a dedicated
demo/mock control used by composition/UI tests. A future provider must not implement a
demo selector. Prove a non-Mock stub can use the unchanged service and preserve the
same comparison/review behavior.

### 3. Strict provenance validation (P03-QG-003)

Create reusable provider-neutral provenance types that trim, reject blank-after-trim,
reject control characters/newlines, and enforce conservative bounds for provider name
and source reference. Malformed metadata/output must terminalize safely without raw
provider output, credentials, headers, tokens, or exception detail. Cover newline,
CRLF, whitespace-only, embedded-control, and overlong cases.

### 4. Pre-append streaming bound (P03-QG-004)

Before each `body.extend(chunk)`, require the chunk to fit the remaining configured
capacity. Preserve declared-length validation and actual streaming validation. Cover a
single oversized chunk, multiple chunks crossing the limit, and an exactly-at-limit
valid PDF; reject safely before provider invocation.

### 5. Typed review request contract (P03-QG-005)

Use `DocumentFieldKey` and `ReviewDecision` directly in the request model, bound
correction to 512 characters and note to 240, and forbid extra properties. Invalid
enums, extras, and overlong values must fail at the API validation boundary through
stable sanitized errors. OpenAPI must expose the enum schemas. Runtime review rules,
idempotency, conflicts, and original-value preservation remain unchanged.

### 6. UEN normalization alignment (P03-QG-006)

For registration-number comparison only, trim, remove all internal whitespace, and
uppercase. `2024 00001a` must normalize to `202400001A`. Legal names, countries, and
addresses retain conservative whitespace collapse. Keep the rule explicitly
provisional and update tests/documentation consistently.

## Integrity and scenario invariants

- Original extraction remains immutable and distinct from accepted/corrected values.
- Rejection never erases extraction; confidence never approves a field or customer.
- Every provisional field needs an explicit final decision before local `REVIEWED`.
- `REVIEWED` is not Ready-for-Approval, compliance, customer, or GoldTier approval.
- Preserve onboarding outcomes: `202400001A -> COMPLETED`, `202400002B ->
  REVIEW_REQUIRED`, `202400003C -> FAILED`, `202400004D -> REVIEW_REQUIRED`, and
  `999999999Z -> FAILED`.
- Preserve document outcomes: all-match review then reviewed after four decisions;
  mismatch/low-confidence/missing remain review-required; processor failure is failed.

## Security and explicit non-goals

Use synthetic PDF bytes only. Do not add real documents/customer/KYC data,
authentication/RBAC, malware/CDR services, real OCR/cloud IDP/VLM, real ACRA, real
GoldTier/PingFed, UBO, hierarchy, related parties, workers/queues, a database, or any
Phase 04 capability. Keep Q-013/Q-014 production limitations explicit.

## Documentation and supporting reviews

Update only affected Phase 03 architecture/contract/demo/test documentation. After the
implementation is stable, rerun the integration-security and POC-regression workflows
and replace their Phase 03 reports. The regression report must include the expanded
post-acceptance adversarial failures and must not retain superseded PASS claims without
execution proof. Update the canonical regression catalogue only for scenarios and
invariants explicitly established and verified by this handoff.

## Required validation

Run backend tests, Ruff, strict mypy, contract and repository tests, Phase 01/02/03
regressions, new terminalization/provider/provenance/upload/review/OpenAPI/UEN tests,
secret scanner/tests, GoldTier validator regressions, frontend typecheck/tests/build,
`pip check`, npm dependency integrity, diff checks, and tracked/untracked whitespace
checks. Report all exact results; do not stage, commit, push, merge, or begin Phase 04.

## Completion readiness statements

Report Phase 03 quality-gate readiness separately from IDP foundation readiness,
sponsor approval of the IDP profile, live ACRA verification, and real GoldTier
readiness. Only a later independent quality gate may issue final Phase 03 acceptance.
