# Phase 05 GoldTier Submission Preparation

## Bounded outcome

Phase 05 prepares and executes only credential-free Mock GoldTier base operations
through the existing `GoldTierConnector`. It adds no real HTTP client, PingFed flow,
token acquisition, credentials, endpoint configuration, relationship payload, or
Ready-for-Approval action.

## Reused base operations

| Order | Operation | Phase 05 behavior |
|---:|---|---|
| 1 | `searchParty` | Always first. `NO_MATCH` alone permits shell creation. |
| 2 | `createShellCustomer` | Executed only after explicit `NO_MATCH`. |
| 3 | `createPolicy` | Executed only after shell success. |
| 4 | `amendParty` | Uses canonical `POST /v1/eds/parties/{partyId}/amend` semantics and runs only after policy success. |

The Mock requests continue to use the accepted source-case, correlation, idempotency,
mandatory-shell-country, and external policy-reference behavior from Phase 01. Phase 05
retains the exact correlation ID, stable accepted time, and per-operation idempotency IDs
inside the frozen target input. This is not a real transport proof.

## Outcome and call-stopping rules

- `MATCH_FOUND` -> CLM `REVIEW_REQUIRED`; no shell, policy, or amend.
- Search failure -> CLM `FAILED`; no later call.
- Shell failure -> CLM `FAILED`; no policy or amend.
- Policy failure -> CLM `FAILED`; no amend.
- Partial amend -> CLM `REVIEW_REQUIRED`; never Mock-submitted success.
- Unexpected connector failure -> safe terminal `FAILED`, sanitized fixed error, and no
  stranded `SUBMITTING` state.
- Required successful amend -> `MOCK_GOLDTIER_SUBMITTED`, not approval.

## Immutable submission snapshot

Immediately before execution, the orchestration stores an immutable process-local
snapshot containing the exact `GoldTierSubmissionInput` consumed by the existing
mappers: minimized canonical business data, case/source-case/submission/correlation IDs,
stable accepted time, and per-operation idempotency IDs. It also retains reviewed
document IDs/event-count versions/statuses/timestamps, ownership analysis reference,
provisional candidate summary, readiness policy version, and creation timestamp.

It excludes PDF bytes/text, raw IDP output, raw ACRA or ownership provider responses,
private provenance, credentials, auth headers, secrets, private endpoints, and sponsor
artefact content. It never mutates the canonical entity or subsystem records.

## Target outcome, execution receipt, and recovery

Before connector execution, the process-local target service records an `IN_PROGRESS`
entry keyed by the immutable submission identity and verifies the full input—including
correlation and per-operation idempotency values—on every reuse. Absence represents
`NOT_STARTED`.

As soon as the accepted target flow knows a terminal SUCCESS, MATCH_FOUND, controlled
failure, PARTIAL_AMEND, or unexpected-stage failure, it records a minimal safe target
outcome. This happens before `GoldTierExecutionReceipt` construction and its rich
result/error projections. The outcome retains only submission/case/correlation linkage,
input and idempotency fingerprints, fixed classification/error facts, operation markers,
and already-permitted Mock IDs/statuses. It contains no request/response body, endpoint,
document/ownership/provider evidence, credential, auth material, or exception text.

Connector return objects are not trusted merely because they have a response DTO type.
After every Mock search, shell, policy, and amend call, the target service reconstructs
and validates a fresh strict response before using an ID or starting the next operation.
The retained/usable technical bounds are aligned across connector and outcome models:
party/policy identifiers are nonblank, control-free, restricted identifiers up to 96
characters; statuses and error codes are restricted to 64 characters; messages are
control-free and at most 200 characters. Operation-specific Mock status/outcome/HTTP
status combinations and returned-party consistency are also checked.

An invalid response stops the sequence at that operation. The ledger records a fixed
sanitized `FAILED / GT_MALFORMED_TARGET_RESPONSE` outcome with the completed-operation
prefix and no malformed ID, status, message, code, raw response, or exception string.
Normal target-outcome construction has a separate constant-only failure fallback so a
mapping/validation defect cannot leave the execution owner in `IN_PROGRESS`.

The ledger then transitions from `TARGET_OUTCOME_RECORDED` to `FINALIZED` when the rich
receipt is available. Receipt construction can be retried from the recorded outcome
without requiring the onboarding aggregate to remain `VALIDATED` and without another
target call.

`IN_PROGRESS` is reserved for a currently active process-local execution owner. The
owner records the operation prefix before each connector call and must leave behind a
recorded/finalized safe outcome after any attempted call. An unused entry is removed if
execution exits before the first operation. Forced process termination is outside this
in-memory guarantee.

The CLM aggregate persists the receipt before translating it into
`MOCK_GOLDTIER_SUBMITTED`, `REVIEW_REQUIRED`, or `FAILED`. A retry after result mapping,
error mapping, receipt construction, clock, terminal event, receipt-save, terminal-save,
or one-shot CAS failure resumes from the retained outcome/receipt using the same logical
identifiers and does not call the target sequence again.

This is process-local Mock POC recovery/idempotency. It is not a distributed transaction,
production exactly-once guarantee, or real GoldTier recovery proof. Durable deployment
requires a durable transactional/outbox equivalent and distributed uniqueness.

## Related-party boundary

Phase 05 produces `RelatedPartySubmissionPreparation` with candidate count, internal
party IDs, analysis reference, `mapping_status=PENDING_SPONSOR_CONFIRMATION`, and
`write_status=RELATED_PARTY_WRITE_NOT_EXECUTED`.

No `createRelatedParty` payload or call is created. Q-006 still controls atomic
direct-link semantics/minimums and Q-007 still controls Singapore mappings/value lists.
Contradictory sponsor JSON remains quarantined. No contract discrepancy is silently
resolved or reclassified by Phase 05.

## Safe exposed plan

The browser receives operation names/order and bounded outcome labels only. It does not
receive raw target DTOs, HTTP paths, endpoints, auth headers, idempotency values,
credentials, or sponsor payloads.

## Real integration blockers

- Q-008/D-018 containment, sanitized authentication reference, fresh approved secret
  delivery, PingFed details, granted scopes, and sponsor sandbox connectivity.
- GoldTier TLS 1.3 plus confirmed mTLS/private-CA/network requirements.
- Q-006/Q-007 related-party inputs and Singapore mappings.
- Q-001 exact Ready-for-Approval/four-eye transition.
- Q-002 seeded hierarchy retrieval contract.

Therefore Mock base submission is implemented; real GoldTier remains **NOT READY**.
