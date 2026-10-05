# Post-UAT publication: CI remediation round 1

Owner assignment: publication and CI closure, 2026-10-05. Preserve the accepted
commit; at most two CI remediation rounds, fresh independent PASS before a new
commit/push, both push and PR CI green, then human merge only.

## Identity and scope

- Branch: `fix/post-uat-document-ownership-goldtier-ux`.
- Worktree: `C:/Users/shane/.codex-clean2/worktrees/post-uat-document-ownership-goldtier-ux/data-dividends-zero-touch-clm`.
- BASE_SHA / fetched origin/main: `ae27654a075f13354364e86ec8fe5a81d24777d4`.
- Accepted initial HEAD / remediation parent: `7caf438e18dfa1692d2e71ddd9be022bdf921399`.
- PR: [73](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/73),
  open/non-draft, base main. Remote initial feature SHA equals the accepted SHA.
- Initial clean committed-state pre-PR: PASS, 0 unsafe conditions / 3 disclosed
  deliberate hotspot/API/CI warnings. All55 original reviewed hashes and the
  complete57-path commit set were independently accepted and publication-read back.

The sole executable delta is three existing physical-Mongo regressions in
`apps/backend/tests/test_phase12_real_mongo.py`. This report, a delta hash manifest
and a separately assigned independent gate are supporting evidence. Original
implementation/review reports and payload remain unchanged. Change class CI_TOOLING;
no new owner, architecture decision, product behavior or persistence implementation.

## First causal failure and reproduction

Initial push run37308319161 / Mongo job111757277959 and PR run37308446822 /
Mongo job111757696872 both ended with:
`PHYSICAL_MONGO_RESULT=FAILED; REASON=TIMEOUT`, exit2 after the existing900s deadline.
All other six jobs in each event passed. Exactly one targeted rerun of the push
Mongo job was authorized/executed, without code/assertion/deadline changes; its
terminal result remains to be recorded in the publication handoff.

Fresh local reproduction of only
`test_real_mongo_concurrent_field_review_has_one_durable_winner` exceeded60s.
The25s thread dump placed the sole active worker inside the test's
`synchronized_replace` barrier, called by DocumentProcessingService's **review
completion** write. The other review worker had returned. This is a test-harness
deadlock, rather than evidence of a product assertion failure or slow Mongo.

Accepted upload auto-confirm leaves the conflicting legal-name field pending and
matching sibling fields accepted. Two independent adapters race the initial field
decision at the same revision. One wins and one loses CAS. The winner then persists
the normal document completion event. The old test barrier intercepted every
replacement and waited again with no remaining peer. That second, unbounded wait
generates the runner timeout. Product CAS, locking and completion ownership remain
correct; increasing the runner deadline would not resolve this deadlock.

## Correction and preserved assertions

Capture/assert the same initial revision from both stores; synchronize only the
two initial replacements at that revision, with a bounded10s barrier wait. Allow
the CAS winner's subsequent completion write normally. Retain every original
one-DocumentProcessingRecord/one-PersistenceConflictError assertion and winning
legal-name persisted-status comparison. Add assertions that the winner and fresh
readback are REVIEWED, and the durable revision advances by exactly two writes.

The repaired exact CAS test passes in1.93s. The first complete physical run after
that fix completed116 tests:114 PASS /2 FAIL /0 ERROR /0 SKIP. The23-test owning
suite independently reproduced21 PASS /2 FAIL, both stale timing assertions:
`test_real_mongo_failed_replacement_restart_requires_retry_without_replay` and
`test_real_mongo_replacement_restart_preserves_history_and_stales_old_decision`
expected intake to append document events (`7 > 7`). Accepted owner behavior now
records auto-confirmation during upload, including during GoldTier Search, so
intake must preserve those events. Replace those obsolete timing assertions with
exact retained-event equality, an upload-time DOCUMENT_AUTO_CONFIRMED event, and
only legal_name PENDING. Replacement lineage, stale409, restart, currentness,
provider counters and target no-replay assertions remain intact.

All three exact physical regressions pass together in10.74s. An initial pre-freeze test-edit UUID readback
type error was corrected; it is not passing evidence. No test was removed/skipped,
no assertion weakened, no retry/timeout increase introduced, and no product source,
API/type/schema/connector/configuration/business-rule/mapping/auth/provider status
or runtime behavior changed. Architecture continues to use existing owners.

## Verification checkpoint

- Exact physical CAS regression:1 PASS; final three repaired regressions:3 PASS.
- Diagnostic broad result after CAS repair:114 PASS /2 obsolete timing FAIL;
  diagnostic entire owning suite:21 PASS /2 FAIL. These are not passing runs.
- Ruff owning test (`--no-cache`): PASS.
- Existing physical runner unit tests:19 PASS.
- Full original16-suite guarded physical runner after all three corrections:
  running at this freeze checkpoint; final result belongs in the fresh independent
  gate/publication handoff, not inferred as passing here. Existing TestClient
  deprecation warning remains.

Task-created disposable Mongo7 container: `clm-postuat-ci-mongo-20261005-01`.
Only newly generated allowlisted fixture databases are used. No owner environment
file, private sponsor artifact or `clm_poc` access; no connection URI is printed or
persisted. External ACRA calls0 / GoldTier calls0. The accepted original runtime
and test hashes outside this delta remain unchanged. One coordinator owns all Git
mutations. No history rewrite, main push, auto-merge, merge, branch/worktree deletion
or new phase is authorized.

Next: finish original guarded physical verification, freeze the delta, fresh
independent fyp-quality-gate review with0/0/0, create a new local remediation
commit, run clean committed pre-PR, push normally and observe both new-head CI
events. The original failures remain historical evidence until corrected-content
CI proves closure; a passing event does not erase another applicable failure.
