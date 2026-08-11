# Phase 05 Integration Security Review — Target-Response Remediation

Date: 2026-08-11

Branch: `phase/05-clm-orchestration`

Reviewed HEAD: `0ef1ea4077fc201114c84bc406e4337e00d36afa` plus the unstaged Phase 05 worktree

## Result

**PASS for the bounded process-local Mock Phase 05 scope.** No active CRITICAL,
HIGH, MEDIUM, or LOW integration-security finding remains in this supporting review.
The worktree is ready for a new independent Phase 05 Quality Gate; this report is not
that gate.

This conclusion does not erase the two independent failures that led here:

1. The original post-write design retained a rich receipt too late, so receipt
   construction could strand `SUBMITTING`.
2. The pre-receipt outcome remediation closed that gap for well-formed target results.
3. The next gate found an earlier trust-boundary gap: a 97-character shell `party_id`
   reached policy/amend and then failed outcome construction, leaving `IN_PROGRESS`.
4. This target-response remediation validates each response immediately and guarantees
   a sanitized target outcome after any attempted Mock operation.

This result is not authorization for production KYC/PII, live ACRA, live hierarchy,
PingFed, real GoldTier, related-party write, Ready-for-Approval, or Phase 06.

## Reviewed trust path

`browser -> CLM API -> current case-owned evidence -> server readiness -> immutable
snapshot/GoldTierSubmissionInput -> process-local ledger IN_PROGRESS -> Mock connector
call -> untrusted response -> fresh strict response validation -> safe target outcome ->
rich receipt -> recoverable CLM terminal result -> minimized browser summary`

Primary evidence:

- `apps/backend/app/domain/target_safety.py`
- `apps/backend/app/connectors/goldtier_models.py`
- `apps/backend/app/services/target_response_validation.py`
- `apps/backend/app/domain/target_submission.py`
- `apps/backend/app/services/onboarding.py`
- `apps/backend/app/services/clm_orchestration.py`
- `apps/backend/tests/test_clm_orchestration.py`
- `tests/contract/test_phase_05_clm_contract.py`

## Closure of the malformed-response CRITICAL

| Boundary | Previous failing behavior | Remediated behavior |
|---|---|---|
| Connector return | Response DTO accepted unbounded target text. | Connector DTO and retained models share bounded safe text types. |
| Shell identifier | A 97-character `party_id` was used by policy/amend. | A fresh strict model rejects it immediately after shell; policy/amend are not called. |
| Response trust | A typed connector object was implicitly trusted. | Every return is dumped to primitives and reconstructed with `model_validate` before business use. |
| Malformed response after side effect | Normal outcome construction copied the unsafe field and failed. | A fixed `FAILED / GT_MALFORMED_TARGET_RESPONSE` outcome records only identity and operation markers. |
| Owner exit | The ledger could remain `IN_PROGRESS` after the execution owner returned. | Attempted operations are marked before invocation; the owner finally converges to an outcome/final state or removes an unused entry. |
| Outcome constructor fault | Normal outcome construction was itself a loss point. | A separate constant-only failure constructor records `GT_TARGET_OUTCOME_RECORDING_FAILED`. |
| Retry | Retry saw permanent in-progress state. | Retry uses the retained outcome/receipt and performs zero additional target calls. |

## Trusted response contract

- Party and policy identifiers: 1–96 characters, restricted ASCII identifier grammar,
  no blank/whitespace/control/URL-like forms.
- Statuses and error codes: 1–64 characters, restricted uppercase technical grammar.
- Messages: 1–200 characters and control-free.
- Search, shell, policy, and amend each enforce the accepted Mock outcome/HTTP-status/
  operation-status shape before a returned field is used.
- Policy/amend returned party IDs, when present, must match the previously validated
  shell ID.
- Only locally recognized Mock business error codes are retained; other bounded codes
  are projected to a fixed local fallback rather than copied into CLM.

These are local Mock POC safety bounds. They do not assert verified real GoldTier
response schemas or sponsor-approved production grammar.

## Malformed and adversarial outcomes

| Probe | Calls | Safe retained/final behavior |
|---|---|---|
| Shell ID length 96 | search, shell, policy, amend | Accepted; normal Mock success. |
| Shell ID length 97 | search, shell | Fixed malformed-response failure; no policy/amend. |
| Blank/whitespace/control/URL-like/invalid shell ID | search, shell | Same fixed failure; unsafe ID absent. |
| Oversized policy ID | search, shell, policy | Fixed failure; no amend. |
| Invalid search status/outcome | search | Fixed failure; no later call. |
| Invalid amend status/result | search, shell, policy, amend | Fixed failure retained; no replay. |
| Malformed error code/message | through affected operation only | Original code/message discarded. |
| Normal outcome construction failure | accepted sequence once | Constant-only outcome; retry finalizes `FAILED`. |
| Unexpected response validator exception | search, shell | Owner-exit fallback records the two-operation prefix. |

All malformed-response outcomes preserve submission/case/correlation and immutable
idempotency linkage. They do not contain the malformed value, raw request/response,
endpoint, auth material, document/ownership payload, or exception text.

## Ledger, receipt recovery, and concurrency

- Absence is `NOT_STARTED`; stored lifecycle is `IN_PROGRESS` ->
  `TARGET_OUTCOME_RECORDED` -> `FINALIZED`.
- `IN_PROGRESS` means a currently active process-local owner. Operation markers are
  written before calls because a malformed response can follow a completed side effect.
- The owner does not overwrite an already recorded valid outcome in its exit guard.
- SUCCESS, MATCH_FOUND, POLICY_FAILURE, and PARTIAL_AMEND receipt-construction and rich
  result/error mapping fault tests remain green with exactly one target execution.
- Completion clock, terminal event, receipt/terminal repository save, CAS conflict, and
  concurrent recovery tests remain green.
- One logical submission retains one start event, one receipt-recorded event where
  applicable, and one terminal event. Recovery does not append repeated starts.

## Sanitization and isolation

- Private sentinels in party ID, policy ID, status, error code, message, validators,
  receipt construction, mapping, clock, events, and repositories are absent from the
  outcome, ledger receipt, onboarding/CLM record, API error/response, event history,
  and browser contract.
- API models and frontend types expose neither ledger state, target outcome, receipt,
  input/idempotency fingerprints, nor per-operation idempotency values.
- No target-boundary application logging was introduced. The secret scanner remains
  green.
- Current canonical validation, document/current-canonical comparison, immutable
  snapshot mapping, case isolation, server-authored readiness, and frontend summary
  invalidation remain green.
- No real HTTP, PingFed/OAuth, credentials, live endpoint, or new sponsor rule was added.

## Verification evidence

- Full backend: **305/305 PASS**.
- Phase 01: 28/28; Phase 02: 80/80; Phase 03: 59/59; Phase 04: 77/77;
  Phase 05: **61/61 PASS**.
- Contract suite: **38/38**; repository unittest discovery: **48/48 PASS**.
- Ruff: PASS. Strict mypy: PASS over **47 source files**.
- Secret tests: 5/5; secret scan: PASS.
- GoldTier validator tests: 5/5; classification remains **19 VALID / 19
  INVALID-QUARANTINED / 48 NOT VALIDATED**; strict invalid mode returned expected 1.
- Frontend typecheck, **22/22** Vitest tests, and production build: PASS.
- `pip check`, `npm ls --all`, tracked/cached/untracked whitespace checks: PASS.
- Branch remained `phase/05-clm-orchestration`; staged diff remained empty.

## Findings and limitations

- CRITICAL: none active in this bounded supporting review.
- HIGH: none active.
- MEDIUM: none active.
- LOW: none active.

The ledger, locks, and repositories are process-local. Forced process termination or a
restart can lose in-memory evidence. Production would require durable transactional
outcome evidence and distributed uniqueness/idempotency. This POC does not claim a
distributed transaction, production exactly-once, or real GoldTier recovery guarantee.

Sponsor/live dependencies remain unchanged: Q-012 live ACRA; Q-002 live hierarchy;
Q-003/Q-005/Q-013/Q-014 IDP/readiness/document authority; Q-004 UBO policy;
Q-006/Q-007 related-party mapping/write; Q-008/D-018 and approved environment/auth
details for real GoldTier/PingFed; Q-001 Ready-for-Approval.
