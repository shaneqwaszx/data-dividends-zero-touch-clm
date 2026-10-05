# Post-UAT publication CI remediation R1 independent quality gate

Date: 2026-10-05. Fresh independent `fyp-quality-gate` review of publication
remediation round 1. This reviewer made no implementation fix and wrote only this
assigned report.

## Executive result

**PASS - P0/P1/P2 = 0/0/0.** The physical-Mongo test harness deadlock and two
obsolete document-event timing expectations are corrected without changing product
behavior, weakening CAS/currentness/no-replay assertions, skipping tests, adding
retries or increasing the runner deadline. All 23 tests in the owning physical suite
passed independently. The coordinator also completed the unchanged full physical
runner: 16 suites, 116 passed, zero failures/errors/skips.

No required current fix remains. This incremental final-feature verdict retains the
original independent product acceptance by verifying its complete content unchanged,
and independently reviews the additional CI remediation delta. It releases the
owner-authorized new remediation commit and publication checks. Remote CI and final
mergeability still require coordinator observation; this local gate does not itself
claim all required GitHub checks are green. Human merge only.

## Current, tested and reviewed identity

- Branch: `fix/post-uat-document-ownership-goldtier-ux`.
- Worktree: `C:/Users/shane/.codex-clean2/worktrees/post-uat-document-ownership-goldtier-ux/data-dividends-zero-touch-clm`.
- Accepted initial feature HEAD/current source commit/remediation parent:
  `7caf438e18dfa1692d2e71ddd9be022bdf921399`.
- BASE_SHA / inspected `origin/main`:
  `ae27654a075f13354364e86ec8fe5a81d24777d4`.
- Original accepted payload: 55 paths, aggregate SHA256
  `230fd5401bfa896f8a8095e949c4474f945489ba4104f8c9f874d69183c50277`.
  Its retained manifest is
  `POST_UAT_DOCUMENT_OWNERSHIP_GOLDTIER_UX_REVIEWED_CONTENT.json`.
- New CI-R1 payload: two paths, aggregate SHA256
  `ab890233f63c61f4be921a543917c950adefa4dfb55158fe7cd0ce99558b6b9e`.
  Its manifest is `POST_UAT_DOCUMENT_OWNERSHIP_GOLDTIER_UX_CI_REVIEWED_CONTENT_R1.json`.
- Executable payload:
  `apps/backend/tests/test_phase12_real_mongo.py`, SHA256
  `58697c40faa628925e6e2d83b53a033bdfbf70497cabf05a5abf1feeb012b4fc`.
- Evidence payload:
  `POST_UAT_DOCUMENT_OWNERSHIP_GOLDTIER_UX_CI_REMEDIATION_R1.md`, SHA256
  `a87d331d3f7435b7fd6de874f6b6b465e823f01ad8fea14242d1b938a2360985`.

Text hashes normalize CRLF to LF; the original PNG uses exact bytes. Aggregate
input is the lexically sorted UTF-8 concatenation of
`path + NUL + sha256 + newline`. The reviewer independently recomputed both
aggregates and every payload hash, and compared all 57 paths in the accepted
feature commit with their current worktree contents. All remain unchanged. The
owning Phase12 test file was outside those original 57 paths and is the sole new
executable delta. No unrelated modified or task-owned new path appeared.

Before this report, the complete new delta was one tracked modified test and two
untracked evidence artifacts; index empty. Final review scope adds this assigned
report, yielding exactly four delta paths. The tests below exercised the frozen
uncommitted delta on the accepted parent. The coordinator must prove the subsequent
new commit contains precisely this reviewed content and derivative outputs; a content
change requires fresh independent review.

## Acceptance and causal review

| Requirement | Result and direct evidence |
|---|---|
| Preserve accepted functional delta | PASS: original 55 payload hashes and all 57 committed paths unchanged; original independent PASS remains tied to its recorded evidence. |
| Diagnose first causal owner | PASS: coordinator reproduction/25-second thread dump identifies the test barrier intercepting the winner's second review-completion save after the CAS loser exits. Independent inspection of the service's two-write completion path agrees. |
| Preserve a real concurrent CAS race | PASS: both stores must hold the same captured initial revision; only initial writes synchronize, with a bounded 10-second barrier. One successful record and one `PersistenceConflictError` remain required. |
| Persist the winner fully | PASS: added fresh readback requires winner and durable document both REVIEWED and exactly two durable revision increments; winning legal-name status comparison remains. Physical owning suite passed. |
| Align replacement expectations with accepted attach-time confirmation | PASS: upload-time auto-confirm event, exact unchanged intake event list and only legal_name PENDING replace the obsolete greater-than event count in both tests. |
| Preserve adverse persistence behavior | PASS: failed IDP/reupload state, restart, replacement lineage/history, stale 409, source selection, provider counters and no-replay assertions remain and execute in the complete owning suite. |
| No weakened CI contract | PASS: authoritative CI command, explicit 16-suite inventory, default 900-second deadline and fail-closed collection/skip/error guards unchanged; 19 runner unit tests passed independently. |
| Contain scope and protected data | PASS: test/evidence-only delta; task-created Mongo and generated allowlisted databases only; no product/provider/transport/auth changes, owner .env/private access or external provider calls. |

The concurrency correction is precise. `DocumentProcessingService.review_field`
first persists the field decision, then persists review completion when no field is
pending. Accepted upload auto-confirmation already accepts the matching sibling
fields, leaving only the conflicting legal name. The old unconditional barrier
therefore traps the winner's completion save with no second participant. Restricting
the barrier to the captured initial revision preserves the contested CAS write and
allows the normal owner to complete. The test still fails if either contender fails
to reach the race, both succeed, the loser has the wrong exception, completion is
missing, the durable result diverges, or revision accounting differs.

The replacement corrections assert more specific accepted timing: automatic sibling
confirmation occurs at upload and intake cannot duplicate those document events.
They do not remove replacement or recovery coverage. Independent inspection covered
the full three changed tests, surrounding helpers, document review/auto-confirm
owner, physical runner, allowlisted database cleanup owner and unchanged CI command.

## Fresh independent execution

Existing primary Python venv was used with the worktree/root/backend PYTHONPATH,
plugin autoload disabled, `-o addopts=`, `-p no:cacheprovider`, and bytecode writes
disabled. Physical execution was serialized after the coordinator's broad run
finished. It used only the task-created Mongo7 loopback server and the fixture's
newly generated allowlisted databases; connection data was retained only in the
child environment and never printed or persisted. No `clm_poc` access occurred.

| Command/surface | Actual independent result |
|---|---|
| pytest apps/backend/tests/test_phase12_real_mongo.py -o addopts= -p no:cacheprovider -q --tb=short | 23 passed / 0 failed / 0 errors / 0 skipped; pytest 46.60s, wrapper 48.23s. Existing TestClient deprecation warning only. |
| unittest tests.test_run_physical_mongo_tests -v | 19 passed, 1.652s. Includes all-pass parsing, mixed/all-skipped rejection, ownership inventory, timeout/output containment and narrow child environment. |
| Ruff check --no-cache apps/backend/tests/test_phase12_real_mongo.py | PASS. |
| check_project_state / check_architecture / check_tooling_config / check_policy_authority / check_external_provider_readiness / check_secrets | All six PASS. Scanner verifies its supported patterns only. |
| git diff --check; explicit new payload whitespace; original/new hashes, aggregate, path inventory and empty index | PASS. Rechecked at report completion. |

The reviewer made no external ACRA or GoldTier call. Product/browser/contract/full
ordinary backend suites were not re-executed for this test-only delta. Their original
exact identities and limitations remain in the accepted product gate; no new
single all-green ordinary backend invocation is claimed here.

## Attributed coordinator evidence and CI incidents

The coordinator supplied actual terminal evidence after this review began:
unchanged `run_physical_mongo_tests.py` completed with exit 0,
`PHYSICAL_MONGO_RESULT=PASSED; SUITES=16; COLLECTED=116; PASSED=116;
FAILED=0; ERRORS=0; SKIPPED=0`. This is broad affected physical evidence, distinct
from the reviewer's independently executed 23-test owning suite.

The frozen remediation checkpoint truthfully records that broad run as pending at
its freeze time. This report records the later terminal result without modifying
the frozen checkpoint or borrowing a pending result as a pass. Earlier diagnostic
114-pass/2-fail and 21-pass/2-fail runs remain failures; they are not passing evidence.

Initial accepted-head push run 37308319161 / Mongo job 111757277959 and PR run
37308446822 / Mongo job 111757696872 timed out at the unchanged 900-second
deadline. The single targeted push rerun, attempt 2 / job 111764006211, also failed
with the same timeout. No further targeted rerun is authorized or claimed. The
coordinator reports all twelve other initial event jobs passed. These historical
failures are not erased by local success; new remediation-head push and PR events
must independently prove CI closure before final merge readiness.

Original remote PR ordinary-backend evidence is attributed separately: job
111757696971 tested the merge preview and reported 2367 passed / 122 skipped /
4 warnings. Its prerequisite skips include the 116 guarded physical and six local
OCR tests; the earlier local ordinary coverage of 2373 included available actual
OCR. Counts have different environments and must not be silently interchanged.

## Contract, architecture and security assessment

No current P0/P1/P2 finding. API/types, schema/version/migration, connector,
configuration, business rule, mapping, auth/security implementation, architecture,
provider classification and product runtime behavior are unchanged by this CI-R1
delta. Existing owners, real revision CAS, insert/update semantics, currentness,
restart and target ledger/no-replay guarantees remain intact. No second persistence
owner, route-to-Mongo access, provider switch or production authority is introduced.

The reviewer read the owner publication assignment, AGENTS, quality-gate
skill/template, tester/reviewer/security roles, CI_TOOLING context selector and Tier1
sections, original accepted gate/manifests, current frozen remediation handoff and
actual executable delta. Accepted Mock/Local/Partial classifications and unresolved
sponsor dependencies remain unchanged; this evidence does not prove Live ACRA,
Production/PingFed, sponsor-approved policy, legal UBO or downstream approval.

No confidential sponsor artifact, owner environment file, credential, raw provider
payload or PII was accessed or added. Existing synthetic fixture data remains within
the guarded offline tests. The task Mongo container was not removed by this reviewer.

## Required fixes, readiness and report-only boundary

Required current fixes: **none**. Final independent gate: **PASS, 0/0/0**.

The final feature content is independently accepted incrementally: unchanged
original reviewed product payload plus this exact two-path CI remediation payload
and derivative manifest/report. Next authorized action is a new remediation commit
without rewriting the accepted initial commit, exact committed hash/path readback,
clean committed pre-PR check, normal feature-branch push and observation of both
new-head CI events. All required push and PR jobs must pass and PR state must be
open/non-draft/mergeable/clean before the coordinator returns merge-ready. Owner
clicks Merge; neither merge nor auto-merge is released by this gate.

Reviewer wrote only this assigned report and performed no fix, stage, commit, push,
PR modification, main mutation, branch/worktree deletion, cleanup or new phase.
All frozen hashes and complete path sets remained unchanged through the final
report boundary. Index remained empty; HEAD and origin/main stayed at their
recorded identities. CI round 1 is the sole current publication remediation round;
the owner's maximum of two rounds remains controlling.
