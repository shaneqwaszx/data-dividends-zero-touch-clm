# Phase 05 Target-Response Remediation

## Goal

Close the remaining Phase 05 target-response CRITICAL without redesigning readiness,
snapshot binding, pre-receipt recovery, frontend behavior, or sponsor policy.

Every Mock GoldTier response is untrusted. It must be reconstructed into one bounded
trusted operation-specific result before any returned identifier, status, code, or
message can affect downstream state or a later target request. A malformed response
must stop the sequence, retain a constant sanitized failed target outcome, and permit
CLM terminalization/retry without target replay.

## Bounded implementation

- Define one explicit trusted target-response boundary shared by search, shell, policy,
  and amend.
- Align trusted connector-response bounds with the existing retained-outcome bounds:
  identifiers at most 96 characters; statuses/codes at most 64; messages at most 200;
  nonblank, control-free, and restricted to the smallest safe identifier/status/code
  grammars needed by the current Mock contract.
- Reconstruct untrusted connector model instances from primitive field values so
  previously constructed or mutated Pydantic objects cannot bypass the boundary.
- Validate each response immediately after the connector returns and before using a
  target-returned identifier or changing downstream orchestration state.
- On invalid search/shell/policy/amend success or error response, record
  `FAILED / GT_MALFORMED_TARGET_RESPONSE` with a fixed message, completed-operation
  markers, stable submission/correlation/idempotency linkage, and only identifiers that
  passed earlier trusted boundaries. Do not copy the unsafe field.
- Make the execution owner guarantee that every exit after an operation was attempted
  leaves `TARGET_OUTCOME_RECORDED` or `FINALIZED`. `IN_PROGRESS` may exist only while
  the owner is actively executing.
- Protect normal outcome construction with a constant-only minimal fallback outcome
  that does not depend recursively on the rejected response projection.

## Required regressions

- Shell party ID: length 96 accepted; length 97, blank, whitespace, control characters,
  forbidden grammar, and token/URL-like forms rejected before policy/amend.
- Malformed policy ID/status, search status/matched ID/code/message, amend status/code/
  message, and malformed error code/message.
- Normal `GoldTierTargetOutcome` construction failure falls back to the constant safe
  failed outcome without leaving `IN_PROGRESS`.
- Every malformed case proves exact call stopping, safe retained outcome, eventual CLM
  `FAILED`, stable identity, zero replay on retry/duplicate, one logical terminal
  history, and absence of the unsafe/private value from outcome, ledger, receipt, CLM,
  API, events, and frontend contract.
- All previous receipt-construction/mapping/clock/save/CAS/concurrent recovery and
  current-canonical/snapshot/frontend regressions remain green.

## Security and claim boundary

- Store no malformed returned value, connector raw request/response, exception text,
  endpoint, credential, auth material, document/ownership/provider payload, or private
  sentinel.
- Use fixed trusted error code/message for malformed responses and fallback outcome
  construction.
- This is Mock-bound contract hardening and process-local recovery only. It is not a
  verified real GoldTier response schema, durable transaction, distributed exactly-once
  guarantee, sponsor policy decision, or Ready-for-Approval.

## Documentation and evidence

- Update Phase 05 architecture and GoldTier submission-preparation contracts with the
  untrusted-response boundary, bounds, stopping behavior, outcome fallback, and active
  `IN_PROGRESS` ownership semantics.
- Extend the authorized POC catalogue with malformed target-response scenarios.
- Regenerate the security and POC regression reports while preserving the progression:
  original post-write gap, pre-receipt fix, malformed-response gate finding, and this
  target-response remediation.

## Explicit non-goals

- Real GoldTier/PingFed/network schemas, credentials, live ACRA, live hierarchy,
  related-party writes, Ready-for-Approval, durable persistence/outbox/queue,
  distributed transaction, sponsor policy change, or Phase 06.

## Validation and stop condition

Run the full backend and Phase 01-05 suites, focused malformed-response and existing
recovery tests, contract/repository tests, Ruff, strict mypy, secret scanner/tests,
GoldTier validators, frontend typecheck/tests/build, dependency checks, and tracked/
cached/untracked whitespace checks. Then rerun the integration-security and POC
regression workflows.

Do not stage, commit, push, merge, change branch, or begin Phase 06. Hand the resulting
worktree to a new independent Phase 05 gate.
