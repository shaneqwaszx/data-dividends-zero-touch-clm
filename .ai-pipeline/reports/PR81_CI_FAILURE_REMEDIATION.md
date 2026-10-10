# PR #81 bounded CI remediation

Status: **STOPPED / NOT READY FOR HUMAN MERGE**. A new corrected-candidate Windows
health deadline failure triggered the owner's reassessment condition. No revised
independent PASS, commit, push or merge. Owner authority SHA256:
`94c2315b283531f51f7816fe9bdeeca636758d522e4f66f895f9ce1cde644448`.
Task base `973ce93a21ef7ca1cda1a2458f316b8030b96b12`; main / merge-base
`e799d74063678bb0eccbea445d5ab3c8628dd2c0`.

## Causal evidence and corrections

| Area | Reproduced cause | Small correction |
|---|---|---|
| Windows checkout | Git builtin checkout without long-path support cannot materialize archived evidence. A fresh deeper Windows checkout failed with filename errors; the process-scoped counterfactual succeeded. | Set command-scope `core.longpaths=true` for the Windows job before checkout. No archived path or byte change. |
| Concurrent create/delete | Deterministic chronology: deletion requested, establishment lock released, deletion completed, HTTP response 404. Projection read case-owned state after the establishment boundary. | Project the creation response through a callback while the existing case establishment lock is held, for both creation routes. Preserve registration, rollback, authorization and deletion owners. |
| Browser shard 2 | A held earlier upload response released during focus inspection emits `POST /api/clm/zero-touch/cases/<case>/intake/complete` before the navigation click (742 ms into the captured window). Initial Search ambiguity already reports WAITING_FOR_REVIEW before intake completes. | Register and await the intake-complete HTTP response before opening the full case and measuring navigation. Keep the original zero-mutation assertion and deadlines. |
| P2 grouped retry | A+B source commit, failed automation save, then A-only retry returns 200 with source RESOLVED and one unresolved automation blocker. A complete old group also replayed after a later reconciliation revision. | Existing reconciliation idempotence now requires the full retained decision-version group and its immediate committed revision. No new persisted field, receipt owner or cross-owner transaction. |

The browser corrected counterfactual retains the earlier upload barrier, observes
the initial WAITING_FOR_REVIEW pause, awaits its continuation, then passes with zero
navigation mutations (one test, 4.9 seconds). Scratch-only diagnostics are absent
from the candidate. New browser artifacts are isolated in a task-owned checkout;
its historical report copies are retained byte-exact outside the output directory.
The publication worktree's historical reports remain immutable.

## Verification checkpoint

- Fresh Windows checkout: PASS; the four originally failing JSON blobs retain exact
  SHA256 bytes when command-scoped CRLF conversion is disabled for raw comparison.
  Windows lifecycle on the initial fresh checkout: 31/31 PASS, 348.826 seconds.
  Corrected source: 30 PASS / 1 FAIL, 439.865 seconds; current lifecycle verdict FAIL.
- Frontend: 576/576 PASS in 49 files, typecheck PASS, build PASS. Existing React test
  warnings and build-size advisory do not indicate a failed check.
- Focused in-memory race/reconciliation/batch suites: 76 PASS before the additional
  later-version guard; reconciliation/batch suite after that guard: 47 PASS.
- Physical Mongo: all 145 tests in 23 canonical suites PASS, no skips/errors/failures.
- Full backend, corrected root security/governance and complete browser shards were
  cancelled at the owner stop boundary. They have no complete PASS verdict. Browser
  shard 1 had 33 completed lifecycles when its buffered output was last observed;
  shard 2 and the eight-journey complete proof are unavailable.

Exact full-group recovery retains source versions, avoids duplicate decisions and
target calls, and reaches the existing final human confirmation. Negative coverage
includes subset, changed action, duplicate, stale fingerprint/version, extra choice
and later revision. Physical restart tests cover one- and two-choice groups with
registry retention and canonical legal-name update, plus explicit Resume recovery.

## Scope and risk

API routes/models, frontend shared types, durable schema, connector interfaces,
external configuration, mappings, provider classifications and owner/dependency map
are unchanged. Runtime response atomicity and source retry currentness are corrected.
The internal establishment method gains a projection callback; Windows CI gains
job-scoped Git configuration. No frontend runtime/cache/auth behavior changes.
No business rule or sponsor-controlled integration decision is introduced.

ArchitectureReviewRequired: no new owner or dependency direction; the existing case
lock and reconciliation UoW remain authoritative. Test posture: diagnostic
reproduction followed by focused adverse regressions; formal TDD mode is off.

SDQ-01 remains historical root cause unresolved, with owner-accepted residual risk.
Revised-candidate applicability is PENDING fresh independent verification of exact
unchanged progress controls, complete green coverage and no new timeout. Earlier
FAIL reports and independent gates remain unchanged and historical.

No protected database, original checkout, unrelated worktree or real provider write
is authorized or performed. Publication requires fresh exact independent PASS,
latest-main assessment, committed-state pre-PR PASS and both actual nine-job CI runs.
The owner performs the final human merge.

## Verification invocation correction

The first local umbrella root-unittest command ran 370 tests and ended with two
discovery errors: `contract.test_phase_06_zero_touch_contract` and
`contract.test_phase_07_uat_contract` could not import `phase13_contract_credentials`.
Recursive root discovery lacked the contract helper's module path; canonical CI
discovers `tests/contract` separately. This is a local invocation defect, with no
candidate source correction. Its failed receipt remains preserved at ignored
`tmp/pr81-static-verification.json`. Corrected full discovery supplies that path,
and the canonical separate contract command remains required. No failed product
assertion or timeout is dismissed or relabeled as PASS.
