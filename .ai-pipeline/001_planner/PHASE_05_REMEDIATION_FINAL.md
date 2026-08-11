# Phase 05 Final Recovery Remediation

## Goal

Close the remaining `P05-QG-003` pre-ledger recovery gap without redesigning the
accepted Phase 05 workflow or changing sponsor/business policy.

After Mock GoldTier reaches a logical terminal outcome, that outcome must be bound to
the immutable submission identity in a safe process-local ledger before any fallible
rich receipt, result, error, or CLM terminal mapping. Retry must recover the actual
outcome without repeating target operations or depending on the onboarding case still
being `VALIDATED`.

## Bounded implementation

- Add a minimal frozen safe target-outcome model containing only stable submission,
  correlation, idempotency/fingerprint linkage; terminal classification/code; safe
  permitted Mock identifiers/statuses; operation completion markers; and fixed safe
  failure facts.
- Evolve the process-local execution ledger to distinguish not started, in progress,
  target outcome recorded, and rich receipt/finalization availability, or an equivalent
  minimal lifecycle.
- Capture SUCCESS, MATCH_FOUND, controlled search/shell/policy failures, PARTIAL_AMEND,
  and unexpected target failure directly where the accepted target flow knows the
  outcome, before rich receipt/result/error projection.
- Rebuild a `GoldTierExecutionReceipt` from the recorded outcome on retry. Never rerun
  search/shell/policy/amend when an outcome exists.
- Preserve existing CLM retry support for result translation, completion clock, event
  construction, receipt/terminal save, and one-shot CAS failure.
- Preserve one start event, one logical terminal event, stable identifiers, per-case
  locking, repository CAS, snapshot-as-mapper-input, current canonical/document
  revalidation, frontend invalidation, and all Phase 01–05 normal scenarios.

## Required permanent regressions

- Receipt-construction failure and rich mapping/projection failure for success,
  match-found, policy failure, and partial amend.
- Each retry reaches its exact terminal CLM outcome with the required target call count
  unchanged and no private sentinel in outcome, receipt, record, API/error projection,
  event history, or frontend contract.
- Two concurrent retries after a pre-receipt fault produce no target replay, no stale
  overwrite, one logical terminal history, and the same terminal result or a fixed
  deterministic current/conflict response.
- Existing post-receipt clock/event/save/CAS recovery, duplicate/concurrent submit,
  stale readiness, current-canonical validation, document/current-canonical conflict,
  snapshot binding, frontend invalidation, and cross-case isolation remain green.

## Documentation and evidence

- Correct the architecture and submission-preparation documents to describe the actual
  pre-receipt target-outcome boundary and its process-local limitation.
- Extend the authorized Phase 05 regression catalogue with the final recovery cases.
- Regenerate the integration-security and POC-regression reports. They must preserve
  the historical independent CRITICAL and explain why the earlier receipt-only coverage
  was incomplete.

## Security and claim boundary

- The safe outcome must exclude raw connector requests/responses, raw source/document/
  ownership data, credentials, auth material, private endpoints, exception objects or
  text, and private sentinels.
- Errors and events use fixed trusted codes/messages. Browser projection remains
  minimized and does not expose the ledger, outcome, receipt, or idempotency values.
- This is process-local Mock recovery/idempotency only. It is not a durable transaction,
  distributed exactly-once guarantee, live GoldTier recovery proof, sponsor approval,
  or Ready-for-Approval.

## Explicit non-goals

- Durable database, outbox, queue, worker, distributed transaction, or distributed
  uniqueness.
- Real GoldTier/PingFed/OAuth, credentials, live ACRA, live hierarchy, related-party
  writes, Ready-for-Approval, RBAC, or Phase 06.

## Validation and stop condition

Run the full backend and Phase 01–05 regression matrix, all new receipt/mapping/
concurrency tests, Ruff, strict mypy, contract and repository suites, secret scanner and
tests, GoldTier validators, frontend typecheck/tests/build, dependency checks, and all
tracked/cached/untracked whitespace checks. Then rerun the integration-security and
POC-regression workflows.

Do not stage, commit, push, merge, change branch, or begin Phase 06. Hand the completed
worktree to the independent final Phase 05 quality gate.
