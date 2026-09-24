# Phase 05 End-to-End CLM Orchestration

## Scope and flow

Phase 05 composes the accepted Phase 01–04 process-local capabilities without changing
their domain authority:

```text
Browser
  -> POST /api/clm/cases
  -> OnboardingService.create_staged_case
       -> AcraConnector -> source DTO -> canonical mapper -> validation
       -> persist existing OnboardingCase at VALIDATED
  -> existing document API / DocumentProcessingService
  -> existing ownership API / OwnershipAnalysisService
  -> ClmOrchestrationService readiness evaluation
  -> immutable minimized submission snapshot
       -> exact frozen GoldTierSubmissionInput
  -> OnboardingService.execute_submission_input
       -> GoldTierConnector (Mock): search -> conditional shell -> policy -> amend
       -> minimal safe target outcome recorded at the terminal business boundary
       -> safe process-local execution receipt
  -> recoverable CLM terminal finalization
  -> unified CLM summary and safe timeline
```

The original `POST /api/onboarding/cases` remains
`create_staged_case + submit_staged_case(complete_legacy_flow=True)` and preserves its
accepted Phase 01 `COMPLETED` semantics. The staged path leaves the underlying case at
`VALIDATED` until explicit eligible submission. After successful Mock submission it is
`GT_ENRICHED`, while the Phase 05 aggregate reports `MOCK_GOLDTIER_SUBMITTED`.

## Components

### Reusable onboarding stages

`create_staged_case` owns case creation, ACRA retrieval, canonical mapping, shared
canonical validation, safe registry errors, and persistence. `submit_staged_case` and
Phase 05 both construct `GoldTierSubmissionInput` and use the single accepted target
sequence. The legacy `create_case` method composes both, so no complete onboarding path
is duplicated.

### Orchestration aggregate

`ClmOrchestrationRecord` is keyed by existing case ID and contains orchestration and
correlation IDs, expected-write version, integrated status, current assessment,
blockers/warnings, safe plan, optional immutable snapshot/reference preparation,
bounded Mock result, safe events, and timestamps. It references rather than copies raw
document/ownership evidence.

### Readiness engine

The engine reads the current onboarding case, every case-owned document record, and the
case-owned ownership analysis. It reuses the same canonical minimum validator as
onboarding rather than trusting historical `VALIDATED` state. Reviewed document values
are compared with current canonical values; their original extraction and Phase 03
captured canonical comparison remain unchanged. It returns typed registry/document/
ownership/GoldTier stage statuses, all blockers, and separate real-integration warnings.
React never derives eligibility.

### Snapshot and related-party preparation

The frozen snapshot contains the exact target input: target-needed canonical business
fields, source-case/submission/correlation identifiers, stable accepted time, and
per-operation idempotency IDs, plus versioned evidence references. Target mappers consume
this frozen input, not a second read of the live canonical entity. It excludes raw
external/provider/document data. Related-party preparation remains an internal summary
with no target payload or write.

## API

- `POST /api/clm/cases`
- `GET /api/clm/cases/{case_id}`
- `POST /api/clm/cases/{case_id}/readiness/evaluate`
- `GET /api/clm/cases/{case_id}/submission-plan`
- `POST /api/clm/cases/{case_id}/submit`

Phase 03/04 document and ownership APIs are reused unchanged.

## Concurrency, finality, and stale readiness

Each case has a process-local re-entrant submission lock. Submission acquires it,
re-reads authoritative evidence, validates the current canonical entity, evaluates
readiness, creates the snapshot, persists `SUBMITTING`, and only then calls Mock
GoldTier. A concurrent duplicate waits and then returns the existing snapshot/result
without executing another business operation.

The target service creates a process-local ledger entry before connector execution. The
entry is bound to the complete immutable submission input, including submission,
correlation, and per-operation idempotency identities. When the target sequence knows a
terminal SUCCESS, MATCH_FOUND, controlled failure, PARTIAL_AMEND, or unexpected-stage
failure, it records a minimal trusted outcome before rich receipt/result/error mapping
or onboarding terminal projection continues.

Every connector response is untrusted. Immediately after each search, shell, policy, or
amend call, the service reconstructs a fresh strict response model before reading a
returned value or building the next request. Retainable party/policy identifiers are
nonblank, control-free technical identifiers of at most 96 characters; statuses and
error codes are bounded to 64 characters, and messages to 200 control-free characters.
Operation/outcome/status combinations are checked against the bounded Mock contract.
These are POC safety bounds, not verified real GoldTier response claims.

If validation fails after an operation may have executed, no later target operation is
called. The owner records a fixed `GT_MALFORMED_TARGET_RESPONSE` failure with only the
submission identity and completed-operation prefix; the malformed value and connector
text are discarded. If normal target-outcome construction itself fails, a separate
constant-only failure outcome is stored without using that mapping path.

The safe outcome contains fixed classification/error facts, permitted Mock identifiers
and statuses, operation-completion markers, and submission/idempotency fingerprints. It
contains no raw request/response, endpoint, credential, provider evidence, or exception
text. Receipt construction is retryable from this outcome. If receipt/result/error
mapping, completion clock, terminal event construction, receipt/terminal save, or a
one-shot CAS update fails, a retry resumes without repeating search/shell/policy/amend
and without requiring the onboarding case to remain `VALIDATED`.

The ledger lifecycle is absence/`NOT_STARTED` -> `IN_PROGRESS` ->
`TARGET_OUTCOME_RECORDED` -> `FINALIZED` (rich receipt available). Per-case locking
permits at most one finalization owner; concurrent retries converge on the same terminal
CLM record. The CLM history retains one submission-start event, one bounded receipt
event, and one terminal event.

`IN_PROGRESS` means an active execution owner only. The owner records each operation
attempt immediately before invoking the connector and, on exit, must either have a
recorded/finalized outcome or write the constant-only sanitized failure. If it exits
before any operation was attempted, the unused ledger entry is removed so a later call
can start normally. This finally-style guarantee is process-local and cannot survive a
forced process termination.

The orchestration repository uses expected-version compare-and-set writes. Existing
document and ownership records remain unchanged on target failure. This is process-local
Mock POC recovery/idempotency only. It is not production exactly-once behavior. A
durable/multi-process service requires transactional persistence, durable outcome/
receipt evidence, and a distributed uniqueness/serialization boundary.

## Trust and data boundaries

```text
untrusted browser input
  -> typed CLM API
  -> existing validated ACRA/canonical boundary
  -> existing bounded IDP/document records
  -> existing validated ownership records
  -> server-authored readiness
  -> minimized immutable snapshot
  -> typed Mock GoldTier connector (response still untrusted)
  -> fresh bounded response validation before any downstream use
  -> safe process-local target outcome before fallible rich mapping
  -> minimized browser projection
```

No readiness status is accepted from the client. The summary excludes internal registry
links, ownership source references, PDFs/text, provider payloads, target DTOs, auth data,
private endpoints, and exception detail. Events contain fixed safe identifiers,
statuses, codes, and messages.

## Frontend

The UI creates/reopens staged CLM cases, reuses the document and ownership controls, and
shows five backend-authored stages, typed blockers, real-integration warnings, the safe
configured target plan, result, and unified timeline. Every document/ownership mutation immediately
replaces stale readiness with a refresh state and then fetches the authoritative CLM
summary. A rejected/conflicting submit also refreshes. Submit is enabled only for a
fresh backend `READY_FOR_MOCK_SUBMISSION` response.

Environment labels remain ACRA Mock/Sandbox, IDP Mock/Local as supplied, ownership
Mock/Local as supplied, and backend-authoritative GoldTier Mock or GoldTier Sandbox
(`SANDBOX_PARTIAL`). Provisional IDP/UBO and unavailable
hierarchy/related-party/real-GoldTier/approval dependencies remain visible.

## GoldTier adapter seam

The existing `GoldTierConnector` remains the replacement boundary. The pre-Phase 22
candidate adds only the sponsor-supplied XPI sandbox dialect as an explicit partial
adapter; it does not authorize production/Live GoldTier. PingFed, production secret
delivery, related-party child-ID lifecycle, hierarchy creation, and the approval
transition remain unresolved or separately gated.
