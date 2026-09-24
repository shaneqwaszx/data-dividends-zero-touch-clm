# PRE-PHASE 22 Provider Orchestration — Published-Candidate CI Remediation Quality Gate

Date: 2026-09-25
Reviewer role: fresh independent final quality-gate reviewer
Candidate branch: `feature/pre-phase22-provider-orchestration`

## 1. Executive Result

**FAIL**

The published-candidate CI remediation is incomplete. Push run `36032038372` tested
published commit `9c17fc0634ca23b019cb3aba2ff339519288c530`; frontend, backend,
security, E2E, and Windows lifecycle passed, while the physical-Mongo runner reported
`35 collected / 31 passed / 4 failed / 0 errors`.

The current test-only patch corrects three failed pytest items: two physical test
functions with stale pre-restart GoldTier call totals, and one current-v2 uncertain-
target fixture missing `GOLDTIER_SEARCH`. The three edited zero-call assertions do not
represent three failed pytest items because two occur sequentially in the same test
function, whose first failing assertion stops that item.

A fourth stale physical assertion remains in
`test_real_mongo_restart_preserves_three_cases_and_replays_no_provider`: it creates one
completed Singapore case and then a second pending Singapore case, so early Search makes
the aggregate GoldTier call count `5`, but the test still expects `4`. A passing
deterministic memory-mode parity test independently proves the same two-Search pattern.
The remediation therefore does not account for and close all four CI failures.

The underlying runtime behavior, prior finding closures, and the no-replay assertions
inspected in this gate remain sound. The blocker is a current required physical-test/CI
expectation, not a request to weaken early Search or replay protection. Exact `PASS` and
publication readiness are withheld until the stale assertion and false four-failure
evidence wording are remediated, affected checks pass, and a fresh exact-content gate is
performed.

## 2. Candidate Identity and Review Boundary

| Identity item | Independently observed value |
|---|---|
| Branch | `feature/pre-phase22-provider-orchestration` |
| `BASE_SHA` | `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3` |
| Published/current `HEAD` | `9c17fc0634ca23b019cb3aba2ff339519288c530` |
| Published `HEAD` tree | `e4c84cc880c861849ee4cbe6c0c8db24bd595c51` |
| `origin/main` / merge-base | `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3` |
| Staged paths | `0` |
| Prior published candidate | `96` paths / `dfa7689710dc36c1db2e92a92e0896a9846e20b6af92a8c31260edfc3ff2b963` |
| Current reviewed candidate | `97` paths / `985e1c63ec6fb8e3d079952c0893a31f4f19169a32453b55a6eb34fccf8f1ec9` |

The current candidate is the ordinal, case-sensitive sorted union of paths changed from
`BASE_SHA` through `HEAD` plus current working-tree, staged, and untracked paths,
excluding only this canonical report. Each row is `path<TAB>git hash-object`; rows are
LF joined with no terminal LF, UTF-8 encoded, and SHA-256 hashed. The exact count and
digest matched before testing, after testing, immediately before report replacement,
and after report replacement.

Current source revision is published `HEAD` plus the uncommitted remediation delta in:

- `.ai-pipeline/reports/PRE_PHASE22_PROVIDER_ORCHESTRATION_IMPLEMENTATION.md`;
- `apps/backend/tests/test_phase12_real_mongo.py`;
- `docs/aegis/work/2026-09-24-pre-phase22-provider-orchestration/90-evidence.md`.

No product source, runtime configuration, schema, provider implementation, or frontend
file differs from the prior independently passed published candidate. Fresh local
behavioral checks exercised the current digest. Remote CI evidence belongs to published
commit `9c17fc...c530`; no physical pass is claimed for the uncommitted remediation.

## 3. Phase Acceptance Checklist

| Requirement | Result | Direct evidence |
|---|---|---|
| Early GoldTier Search after canonical Singapore Registry identity | PASS | Runtime source is unchanged; focused current orchestration/persistence tests pass and the stale physical counts themselves confirm Search occurs. |
| Existing exact customer reuses ID and skips Shell | PASS | Prior accepted source is unchanged; current focused target/orchestration coverage passes. |
| No-match waits for readiness; ambiguity/failure blocks mutation | PASS | Current focused adverse-path coverage passes; no product delta exists. |
| Incremental Shell, Policy, and Amend use one durable ledger | PASS | Existing ledger owners are unchanged; focused persistence/CLM/zero-touch tests pass. |
| Restart and uncertain target activity do not replay | PASS | Edited physical tests retain their before/after counter equality and repeated-resume assertions; deterministic current/legacy uncertainty coverage passes. |
| Schema-v5 v1/v2 automation invariants fail closed | PASS | The v2 fixture repair adds the required completed Search prefix; strict decode/adverse coverage passes. |
| Physical-Mongo CI remediation accounts for all four failures | **FAIL** | Only three failed pytest items are repaired; one unchanged aggregate call-count assertion still expects `4` instead of `5`. |
| COI optional address and legacy/mismatch behavior | PASS | Behavior-bearing source is unchanged and focused document/reconciliation coverage passes. |
| HR-only console, backend denial, safe projection, and cache scope | PASS | Behavior-bearing source is unchanged; published frontend/backend/security CI passed and focused current backend coverage passes. |
| ACRA/GoldTier provider truth and fail-closed authority | PASS | Governance/provider-readiness checks pass; no provider code or claim changed. |
| Q-016 remains deferred | PASS | No assignment, note, SLA, routing, escalation, or production identity policy was added. |
| Phase 22 remains held | PASS | No Phase 22 implementation or authorization claim exists. |

## 4. Contract and Integration Findings

No new contract, provider, mapping, or sponsor-authority defect was found. ACRA local
Mock remains default; API Marketplace Mock remains `BLOCKED_AUTHORITY`; generic ACRA
Sandbox remains Partial; BizFile remains Dormant. GoldTier remains Mock by default and
XPI remains `SANDBOX_PARTIAL`. Seven target-policy fields remain `TBD_SPONSOR`, and
related-party dispatch remains blocked on the authoritative child-ID lifecycle.

All six prior independent findings remain closed in unchanged product source:

| Prior finding | Current disposition |
|---|---|
| `PP22-QG-001` — generic restart skipped Search | CLOSED; canonical stage order and restart tests pass. |
| `PP22-QG-002` — local Mock mislabeled Sandbox Partial | CLOSED; provider truth remains unchanged and checked. |
| `PP22-QG-003` — HR Search hard-coded `NOT_ASSESSED` | CLOSED; the existing resolver remains the owner. |
| `PP22-RQG-001` — optional COI address falsely blocked | CLOSED; current focused document/reconciliation coverage passes. |
| `PP22-FQG-001` — base schema-v5 continuation gap | CLOSED; v1/v2 continuation coverage passes. |
| `PP22-4QG-001` — durable decode admitted invalid automation invariants | CLOSED; strict decode validation and adversarial persistence coverage pass. |

No external provider call, provider mutation, or database mutation was performed by this
reviewer.

## 5. Tester and Adversarial Findings

### `PP22-CI-RQG-001` — High — fourth physical-Mongo failure remains unremediated

The remote job deliberately suppresses test names and exposes only aggregate counts, so
the exact names cannot be read from the CI log. The current source nevertheless disproves
the implementation report's one-to-one accounting:

1. The three `goldtier: 0 -> 1` edits occur in only two test functions. The two edits in
   `test_real_mongo_failed_replacement_restart_requires_retry_without_replay` are
   sequential ordinary assertions; the first failing assertion terminates that pytest
   item. Those three edits therefore repair two, not three, failed items.
2. Adding `GOLDTIER_SEARCH` to the current-v2 uncertain-target fixture repairs one more
   failed item. The patch thus directly accounts for at most three failed items.
3. `test_real_mongo_restart_preserves_three_cases_and_replays_no_provider` remains
   unchanged. Its first case reaches the normal four calls
   `Search -> Shell -> Policy -> Amend`; its second valid Singapore case is created and
   remains pending documents, which now performs one additional early read-only Search.
   The correct aggregate is therefore `5`, but line 705 still expects `goldtier: 4`.
4. Fresh `test_memory_mode_preserves_safe_pending_and_completed_resume_behavior` passes
   and asserts exactly `search: 2, shell: 1, policy: 1, amend: 1` for the same pending-
   plus-completed shape. This directly falsifies the remaining physical assertion
   without requiring or mutating Mongo.

This finding is a test/CI regression, not a runtime request. Updating the stale total to
`5` preserves the subsequent `counters == before_restart` assertion, which continues to
prove that restart and resume perform no provider replay.

### Fresh independent evidence on `985e1c...f8f1ec9`

| Check | Exact result |
|---|---|
| Persistence + zero-touch deterministic suite | `111 passed` |
| Broader focused persistence/zero-touch/CLM/provider/document/ACRA/XPI/reconciliation suite | `345 passed` |
| Direct uncertainty + failed-replacement adverse tests | `3 passed` |
| Exact pending-plus-completed memory parity test | `1 passed` |
| Physical Phase 12 collection | `15 tests collected` |
| Ruff on changed physical test | PASS |
| Project-state / architecture / tooling / policy-authority / provider-readiness checks | PASS |
| Secret scanner | PASS; no supported secret pattern found |
| `git diff --check` | PASS; line-ending notices only |
| Candidate identity | `97` paths, `0` staged, exact assigned digest |

Published push run `36032038372` is authoritative remote evidence for commit
`9c17fc...c530`: frontend, backend, security, E2E, and Windows lifecycle jobs passed;
only `phase12-mongo` failed at `scripts/run_physical_mongo_tests.py` with the aggregate
`31 passed / 4 failed` result.

Physical Mongo was not available locally. A read-only Docker capability probe found the
Docker Desktop Linux daemon pipe absent. No Mongo connection, database, cleanup, or
physical execution occurred, and this report makes no physical-pass claim.

## 6. Code and Architecture Review

No product code or architecture owner changed in the remediation. The three edited test
expectations correctly acknowledge the mandatory read-only Search while retaining
restart counter equality. The v2 fixture edit restores the exact stage prefix required
by the existing strict durable invariant and retains three repeated resume attempts with
unchanged provider counters. These edits do not relax early ordering, target-ledger
ownership, strict decode, CAS, or no-replay behavior.

The missing fourth expectation is equally narrow, but it is still required. Leaving it
at `4` contradicts sponsor-confirmed early Search and the current canonical runtime. The
implementation and Aegis evidence reports also incorrectly state that the existing four
edits map one-for-one to the four failed CI items.

Canonical owners remain singular: CLM owns early Search, the entity resolver owns
candidate disposition, the target ledger owns mutation order/no-replay, persistence
owns durable reconstruction, backend capability checks own authorization, and React
Query owns browser cache lifecycle. No duplicate owner, fallback, direct
ACRA-to-GoldTier mapping, or Phase 22 scope expansion was introduced.

## 7. Security Review

No new security defect was found. The remediation changes only synthetic physical-test
expectations/fixture data and bounded evidence prose. It adds no secret, external body,
KYC/document content, endpoint, credential, retry, provider fallback, browser field, or
authorization behavior. The configured secret scan and provider/governance checks pass.

## 8. Required Fixes

1. In `test_real_mongo_restart_preserves_three_cases_and_replays_no_provider`, change
   the pre-restart aggregate GoldTier expectation from `4` to `5`; retain the subsequent
   exact no-replay comparison after restart.
2. Correct the implementation and Aegis evidence reports so they distinguish failed
   pytest items from assertion sites and accurately name the fourth stale total.
3. Rerun focused persistence/zero-touch coverage and the full guarded physical-Mongo
   suite in available infrastructure. Do not claim a local physical pass.
4. Freeze the changed candidate and obtain a fresh independent exact-content gate.

## 9. Readiness

The current candidate is **not ready for publication or human squash-merge review**.
The failing push CI has not been fully remediated, and no physical pass exists for this
candidate. This gate does not authorize a commit, push, PR update, retry, merge, provider
action, database action, or Phase 22 work.

Phase 22 remains held. Q-016 remains deferred. Live ACRA is not ready or proved. Real
GoldTier/PingFed integration is not ready or proved. GoldTier XPI remains
`SANDBOX_PARTIAL`; no external write/interoperability evidence is supplied here.

## 10. Git Status and Review Separation

- Branch: `feature/pre-phase22-provider-orchestration`.
- Published/current `HEAD`: `9c17fc0634ca23b019cb3aba2ff339519288c530`.
- `BASE_SHA`, `origin/main`, and merge-base:
  `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3`.
- Candidate: `97` paths, `0` staged paths, fingerprint
  `985e1c63ec6fb8e3d079952c0893a31f4f19169a32453b55a6eb34fccf8f1ec9`.
- This canonical report is the reviewer's only write and is excluded from the candidate
  fingerprint.
- No implementation/test/configuration fix, branch switch, stage, commit, push, CI
  rerun, provider mutation, database mutation, or merge was performed.

## Final Verdict

**FAIL — one stale physical-Mongo call-count assertion remains, so the current
remediation does not close the four-failure CI result.**
