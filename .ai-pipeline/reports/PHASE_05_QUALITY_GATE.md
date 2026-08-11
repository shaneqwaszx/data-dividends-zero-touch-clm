# Phase 05 Final Independent Quality Gate - Target-Response Remediation

Date: 2026-08-11

Branch: `phase/05-clm-orchestration`

Reviewed HEAD: `0ef1ea4077fc201114c84bc406e4337e00d36afa` plus the unstaged Phase 05 worktree

## 1. Executive Result

**PASS**

The final target-response remediation closes the remaining Phase 05 CRITICAL for the
bounded process-local Mock POC. The exact former 97-character shell `party_id` failure
was independently reproduced again. Validation now stops after `search -> shell`, the
unsafe identifier is not used in policy or amend, a fixed sanitized target outcome is
retained, and retry finalizes the same submission as
`FAILED / GT_MALFORMED_TARGET_RESPONSE` without any target replay.

The exact test was also paused at the previous receipt boundary. At that point CLM was
temporarily `SUBMITTING`, but the ledger was already `TARGET_OUTCOME_RECORDED`, the
recoverable outcome contained the completed `SEARCH, SHELL` prefix, and neither the
97-character identifier nor a private exception sentinel was retained. Recovery used
the same submission/correlation/idempotency linkage, reached `FINALIZED`, produced one
coherent terminal history, and left no permanent `IN_PROGRESS` or `SUBMITTING` state.

The complete Phase 05 workflow, the earlier receipt-recovery remediation, frontend
truthfulness, security boundaries, and accepted Phase 01-04 scenarios also pass. No
active CRITICAL, HIGH, MEDIUM, or LOW finding remains in this gate's bounded scope.

| Decision | Status |
|---|---|
| Phase 06 readiness | **READY FOR PHASE 06** |
| Integrated CLM orchestration | **READY** |
| End-to-end Mock POC | **READY** |
| Sponsor-approved IDP/readiness policy | **NOT CONFIRMED** |
| Sponsor-approved UBO policy | **NOT CONFIRMED** |
| Live ACRA | **BLOCKED** |
| Live hierarchy | **BLOCKED** |
| Real GoldTier | **NOT READY** |

The external sponsor and live-integration dependencies are reported separately and did
not cause or weaken this result.

## 2. Primary Critical Reproduction

### Exact 97-character shell identifier

An independently instrumented Mock connector returned a successful shell response with
a 97-character `party_id`.

| Required observation | Independent result |
|---|---|
| Search | Once |
| Shell | Once |
| Policy | Zero |
| Amend | Zero |
| Later use of unsafe ID | None |
| Ledger at forced receipt fault | `TARGET_OUTCOME_RECORDED` |
| Retained operation prefix | `SEARCH, SHELL` |
| Retained party ID | `null` |
| Retained failure | `GT_MALFORMED_TARGET_RESPONSE` |
| CLM at forced receipt fault | Recoverable `SUBMITTING` with `CLM_FINALIZATION_RETRY_REQUIRED` |
| Eventual CLM status | `FAILED` |
| Eventual ledger status | `FINALIZED` |
| Calls after all retries | Still `search, shell` |
| Identity | Same submission and correlation; original per-operation idempotency bindings retained |
| History | One start, one target-receipt event, one failure terminal event |
| Unsafe/private projection | Absent from outcome, receipt, onboarding/CLM models, API responses, events, and frontend contract |

Without the additional receipt fault, the first call safely terminalized immediately as
`FAILED / GT_MALFORMED_TARGET_RESPONSE`; duplicate API and service submissions returned
that same terminal result and made no additional target calls.

## 3. Target-Response Bounds and Call Stopping

An independent 21-case matrix challenged response data constructed outside normal
Pydantic validation. All 21 cases passed.

| Boundary | Result |
|---|---|
| `party_id` length 96 | Accepted; normal four-operation Mock success |
| `party_id` length 97 | Rejected after shell; policy/amend absent |
| Blank, whitespace, or control-bearing `party_id` | Rejected after shell; unsafe value absent |
| `policy_id` length 96 | Accepted; amend executed normally |
| `policy_id` length 97 or control-bearing | Rejected after policy; amend absent |
| Valid known operation status | Accepted |
| Malformed, 65-character, or control-bearing status | Fixed malformed-response failure at the affected operation |
| Valid known error code | Retained through the controlled local projection |
| Malformed, 65-character, or control-bearing error code | Original value discarded; fixed malformed-response failure |
| Message length 200 | Accepted |
| Message length 201 or control-bearing | Original value discarded; fixed malformed-response failure |
| Malformed search result/status | Search only |
| Malformed shell result | Search and shell only |
| Malformed policy result | Search, shell, and policy only |
| Malformed amend result | Full attempted prefix retained; no replay |

Fresh strict reconstruction occurs immediately after each connector operation. Shell
and policy identifiers use a 1-96 character restricted ASCII identifier grammar;
status/error code values use bounded technical grammars; messages are 1-200 characters
and control-free. Policy and amend response party identifiers, when returned, must
match the previously validated shell identifier.

## 4. Ledger Exit and Fallback Review

The inspected execution sequence is:

`NOT_STARTED -> IN_PROGRESS -> TARGET_OUTCOME_RECORDED -> FINALIZED`

- The immutable `GoldTierSubmissionInput` is stored when execution starts.
- Each operation marker is stored before invoking the connector, so an attempted or
  side-effecting call remains represented even if its response is malformed.
- Each response is freshly validated before a returned value can enter a later request.
- A handled malformed response records only the fixed local code/message and the safe
  attempted-operation prefix.
- The execution-owner `finally` guard removes an unused entry if no call was attempted,
  or stores a fixed constant-only failed outcome if any attempted path exits without an
  outcome.
- Recovery from a retained target outcome does not require the onboarding aggregate to
  remain `VALIDATED`; it rebuilds/finalizes the rich receipt from the original input.
- Receipt binding checks submission, case, correlation, input fingerprint, and
  idempotency fingerprint before finalization.

The actual `GoldTierTargetOutcome` constructor was faulted once during a normal
four-operation success path, rather than only faulting an authored helper. The second,
constant-only fallback construction retained
`FAILED / GT_TARGET_OUTCOME_RECORDING_FAILED` with all four operation markers. Retry
made zero target calls, finalized the original identity, and excluded the private
constructor sentinel.

An unexpected validator exception after shell was also covered by the owner-exit path:
the ledger retained a safe two-operation prefix and recovery did not replay either
operation.

## 5. Previous Receipt-Recovery Remediation

The exact `OnboardingService._build_execution_receipt` post-target/pre-receipt boundary
was independently injected for all four required outcomes.

| Target outcome | Calls across failure and retries | Eventual terminal result |
|---|---|---|
| SUCCESS | search, shell, policy, amend once | `MOCK_GOLDTIER_SUBMITTED` |
| MATCH_FOUND | search once | `REVIEW_REQUIRED / GT_EXISTING_PARTY_REVIEW_REQUIRED` |
| POLICY_FAILURE | search, shell, policy once | `FAILED / GT_POLICY_VALIDATION_FAILED` |
| PARTIAL_AMEND | search, shell, policy, amend once | `REVIEW_REQUIRED / GT_OPTIONAL_SECTION_REVIEW` |

At the injected boundary each outcome existed in `TARGET_OUTCOME_RECORDED` while the
rich receipt was absent. Retry finalized from that outcome with the same submission and
no target replay. Rich success/review/failure mappers, safe identifier projection,
post-outcome clock, terminal event, receipt/terminal repository save and CAS recovery
tests all remain green.

Two synchronized retries after receipt-construction failure both observed the same
eventual Mock success. The final record contained one submission-start event, one
target-execution-recorded event, and one terminal completion event; target business
calls occurred once.

## 6. Readiness, Snapshot, Frontend, and Isolation

Independent prior-fix probes confirmed:

- Blank/invalid legal name, registration number, required address, and country each
  changed registry readiness to `BLOCKED`, returned `CANONICAL_DATA_INVALID`, caused
  submit to return `CLM_NOT_READY`, and produced zero target calls.
- The readiness service and onboarding submission eligibility both call the shared
  canonical validation policy rather than maintaining divergent required-field rules.
- After a reviewed document captured canonical legal name A, changing the current
  canonical legal name to B produced `SOURCE_CONFLICT_REQUIRES_POLICY`. The historical
  Phase 03 A remained unchanged and target calls stayed at zero.
- After snapshot A was frozen, registration number, legal name, country, address, postal
  code, and address country were mutated in the live repository to B. Search, shell,
  policy, and amend requests still contained A, and correlation/idempotency metadata
  matched the snapshot input.
- A new unresolved document after visible READY caused final server-side re-evaluation
  to return `CLM_NOT_READY / DOCUMENT_REVIEW_INCOMPLETE` with zero target calls.
- Sequential duplicate, simultaneous duplicate, recovery, stale-failure/success, and
  case-isolation tests retain one logical target execution and immutable terminal state.

Frontend document upload/review and ownership load/analyze operations clear the CLM
summary before the mutation starts, show a disabled `Refreshing authoritative CLM
readiness` state, and refetch the backend summary in a `finally` path. Submit errors,
including `CLM_NOT_READY`, trigger a backend summary refresh. The React client contains
no readiness business-rule implementation; submit is enabled only from the returned
backend status. The 22 frontend tests and production build confirm the truthful Mock
labels and disabled stale-READY behavior.

## 7. Normal POC and Cross-Phase Regression

All intended Phase 05 scenarios pass with their accepted stopping and terminal rules:

- `HAPPY_END_TO_END`
- `DOCUMENT_BLOCKED`
- `DOCUMENT_SOURCE_CONFLICT`
- `OWNERSHIP_BLOCKED`
- `MULTIPLE_BLOCKERS`
- `MATCH_FOUND`
- `SEARCH_FAILURE`
- `SHELL_FAILURE`
- `POLICY_FAILURE`
- `PARTIAL_AMEND`
- `DUPLICATE_SUBMIT`
- `CONCURRENT_SUBMIT`
- `STALE_READINESS`
- malformed search/shell/policy/amend responses
- normal-outcome fallback and pre-receipt recovery

The `poc-regression-check` catalogue preserves the accepted Phase 01-04 outcomes,
ordering, call stopping, Decimal ownership behavior, evidence isolation, and false-
completion protections. The full backend suite passed 305 tests, including 61 focused
Phase 05 tests; no earlier accepted phase regressed.

## 8. Integration Security Review

The target connector response is treated as untrusted even when it is already a typed
object: the service dumps it to primitive data and reconstructs the exact response DTO
under strict validation. Unsafe identifiers, statuses, codes, and messages therefore
cannot enter later target requests or the normal outcome projection.

The malformed-response path stores fixed local constants only. Direct service and API
probes found the unsafe 97-character identifier and private sentinels absent from the
ledger outcome, rich receipt, onboarding case, CLM record, API error/summary, events,
frontend-facing contract, and retried result. No target-boundary application logging
was introduced, and the secret scan passed.

The browser/API contract does not expose ledger state, target outcome, rich receipt,
input fingerprint, idempotency fingerprint, or per-operation idempotency values. Mock
remains the default and all completion labels remain explicitly Mock. No response can
produce a real GoldTier or Ready-for-Approval claim.

The regenerated integration-security and POC-regression reports are consistent with
this gate. Both explicitly retain the historical sequence of the original receipt gap,
the pre-receipt recovery fix, the later malformed-response CRITICAL, and the final
target-response remediation. Both contain direct 97-character/malformed-response
evidence and do not claim those earlier defects never existed.

## 9. Contract and Sponsor Scope

- The canonical amend endpoint remains `POST /v1/eds/parties/{partyId}/amend`.
- Only a validated `NO_MATCH` permits shell creation.
- Related-party preparation remains internal; no `createRelatedParty` or hierarchy
  creation write is performed.
- Mock success is `MOCK_GOLDTIER_SUBMITTED`, never GoldTier approval or
  Ready-for-Approval.
- Sponsor examples remain **19 VALID / 19 INVALID-QUARANTINED / 48 NOT VALIDATED**.
- D-023/D-024 are project technical/readiness decisions, not sponsor policy approval.
- Q-003/Q-005/Q-013/Q-014 leave the IDP/document/readiness policy unconfirmed.
- Q-004 leaves the sponsor UBO policy unconfirmed.
- Q-012 blocks live ACRA verification; Q-002 blocks live hierarchy retrieval.
- Q-008/D-018 plus missing approved environment/authentication details block real
  GoldTier/PingFed; Q-001 leaves Ready-for-Approval undefined.

These unresolved external items are truthfully separated from the passing process-local
Mock gate.

## 10. Configured Check Evidence

| Check | Result |
|---|---|
| Full backend pytest | **305 passed** |
| Focused Phase 05 pytest | **61 passed** |
| Contract unittest suite | **38 passed** |
| Repository unittest discovery | **48 passed** |
| Ruff | PASS |
| Strict mypy | PASS over **47 source files** |
| Python dependency check | PASS |
| Frontend typecheck | PASS |
| Frontend Vitest | **22 passed** |
| Frontend production build | PASS, 28 modules transformed |
| npm dependency tree | PASS; platform-inapplicable optional dependencies only |
| Secret scanner tests and scan | PASS |
| GoldTier validator tests | **5 passed** |
| GoldTier example classification | **19 / 19 / 48** as expected |
| `--fail-on-invalid` behavior | Expected exit 1 confirmed |
| Tracked, cached, and untracked whitespace checks | PASS; line-ending notices only |

Vitest and Vite required permission to spawn the local esbuild worker and then passed.
The initial backend command without the CI `PYTHONPATH` could not import the root
`scripts` package; rerunning with the same repository-root `PYTHONPATH` used by CI
passed all 305 tests. This was an invocation-environment issue, not a product failure.

## 11. Findings and Limitations

- CRITICAL: none active.
- HIGH: none active.
- MEDIUM: none active.
- LOW: none active.

The ledger, repository, locks, and recovery evidence are process-local and in memory.
Process termination can lose them. A production design needs durable transactional
outcome evidence and distributed uniqueness/idempotency. This limitation is explicit
and accepted only for the current Mock POC; this gate does not claim production
exactly-once execution or real GoldTier recovery.

## 12. Final Readiness

- **Overall result: PASS**
- **Phase 06 readiness: READY FOR PHASE 06**
- **Integrated CLM orchestration: READY**
- **End-to-end Mock POC: READY**
- **Sponsor-approved IDP/readiness policy: NOT CONFIRMED**
- **Sponsor-approved UBO policy: NOT CONFIRMED**
- **Live ACRA: BLOCKED**
- **Live hierarchy: BLOCKED**
- **Real GoldTier: NOT READY**

## 13. Git and Scope Verification

- Branch: `phase/05-clm-orchestration`.
- HEAD: `0ef1ea4077fc201114c84bc406e4337e00d36afa`.
- Staged files: none.
- The reviewed Phase 05 implementation, remediation, reports, and documentation were
  already present as tracked/untracked worktree changes.
- This gate overwrote only
  `.ai-pipeline/reports/PHASE_05_QUALITY_GATE.md`.
- No application code, test, supporting report, catalogue, configuration, or other
  documentation was modified by this gate.
- No file was staged, committed, pushed, or merged. Phase 06 was not begun.
