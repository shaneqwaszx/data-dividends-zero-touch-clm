# PR81 final CI and document refresh recovery

Implementation acceptance is STOPPED / FAIL after a newly reproduced required browser lifecycle timeout. This implementer report is not an independent gate or publication acceptance. Existing PR81 remains at dd8c36c8a911f4b5f3b80e7441d049f1aa976599 until every required local check and a fresh independent PASS permit publication. Earlier FAIL/PASS reports are unchanged.

## Scope and causal evidence

Owner authorization: attachment86fe7cc3-d7d6-4308-8094-7b9717bdd9d4, with the matching PR81_FINAL_CI_RECOVERY_PLAN.md. Existing branch feat/blocker-resolution-idp-ux-optimization, task base/published HEAD dd8c36c8a911f4b5f3b80e7441d049f1aa976599, cached main/merge-base e799d74063678bb0eccbea445d5ab3c8628dd2c0. Current implementation is intentionally uncommitted; pre-PR is not run on dirty content.

Performance: actual push38059426119/job114234475940 captured all three groups passing59.9 seconds while the enclosing original60-second lifecycle failed. All three tests were registered at the same file:line19, which the runner deduplicates. The shared measurement body now remains unchanged, and test declarations are on three distinct lines139/143/147. No sample, assertion, metric, artifact, timeout or retry was removed or relaxed. Initial actual discovery confirms91 lifecycles/112 tests, partition46/45. Workflow comments and the owning budget/discovery assertions now reflect those counts while preserving the234-minute job deadline,60-second lifecycle,120-second cleanup allowance and zero retries. A final independent discovery reconciliation remains required.

Document refresh: focused reproduction returned503 after a successful replacement save. The original was superseded, two documents were retained, automation was RESUMING/DOCUMENT ending DOCUMENT_REPLACEMENT_ACCEPTED, no active exception or technical failure was projected, and target recording contained Search only. The new regression failed because no recovery projection existed. This confirmed the independently reported P2, rather than attributing it to a browser/environment failure.

## Owner-local correction and contract

ZeroTouchOrchestrator retains ownership of replacement checkpoints and continuation; CLM retains dependent refresh, documents retain immutable lineage, and the existing case lock/access/authentication owners retain mutation authority. The pre-edit architecture review chose these existing owners and no new state, schema, dependency, provider or repository. Target-specific RECOVERY_PENDING is not repurposed.

The derived, additive document_refresh_recovery object is present at the accepted but incomplete replacement checkpoint. can_resume combines creator authority and the existing target freeze rule. GET retains the durable checkpoint. Existing /resume requires automation identity and automation/CLM/case-event versions for this recovery. Current session, team, creator, identity, all versions and target freeze are rechecked inside the case lock before refresh or continuation. Missing/stale context409, missing/expired session401, noncreator403, inaccessible/deleted case404. Other existing resume callers retain their contract.

The frontend consumes that projection, stops progress polling and the idle inert overlay, displays retained-evidence guidance, and offers Resume document evidence refresh. The action uses the existing guarded mutation/coherent refresh/currentness owner and authenticated transport; no browser state edit or automatic mutation on reload is introduced. Current evidence is refreshed and normal orchestration continues without re-upload, insertion, Search or target replay. Fresh Final Review/confirmation remains authoritative. Frozen or uncertain target execution cannot be repaired by a document mutation.

The existing native intake failure/retry browser scenario is extended, preserving its title and all earlier assertions, so browser test inventory remains112. Its isolated test server produces one real CLM refresh503 after normal owner saves; it uses Local document evidence and Mock target, records actual target calls, and constructs no live provider. The XPI offline fixture rejects this separate mode.

## Current exact-byte verification

| Check | Observed result |
|---|---|
| Three isolated performance groups | PASS,10 observations each; guarded23.969/23.188/23.281 seconds, original60-second deadline |
| Measurement body/30 observations | Body identical after line-ending normalization, SHA2568b136f6091a0545ec1a48de573ff61c08a9404b4a0488d3f76ff01513252a3ce; numbered0..29 |
| Focused final recovery/grouped P2 | 44 PASS44.26 seconds |
| Actual browser503/reload/focus/click | PASS9.9 seconds, guarded17.609 seconds; SEARCH1, target mutations0, no duplicate insertion |
| Full backend | 2651 PASS,145 physical-only deferrals,4 warnings;1889.79 seconds |
| Separate guarded physical Mongo | 23 suites,145 collected/145 PASS,0 failures/errors/skips;334.0 seconds wall |
| Full frontend | 50 files/582 PASS; all original576 plus6 recovery checks retained |
| Frontend integrity/typecheck/build | PASS/PASS/PASS |
| Windows31 | PASS,31/31,372.012 seconds |
| Root/contracts/governance/security/static | PASS:374 root,16 fixture routing,44 contracts; governance/security; canonical Ruff/mypy127 files/pip integrity |
| Complete browser shard1/shard2 | FAIL: shard1 stopped at lifecycle18/46,17 lifecycles/28 tests passed; width360 timed out; shard2 NOT RUN |
| Final discovery/eight journeys/ledger reconciliation | Discovery91/112,46/45 PASS; fresh eight-journey/complete-ledger reconciliation NOT RUN after failure |
| Fresh independent gate/publication/pre-PR/both current CI events | NOT RUN: acceptance failure prevents publication |

The final browser assertions additionally require READINESS/WAITING_FOR_REVIEW, no technical failure, increased CLM version and a fresh confirmation identity. Shard1 executed and passed those final assertions at lifecycle11; the later cache performance failure blocks whole-suite acceptance. Backend source/test bytes are unchanged after its passing run. Subsequent deltas are outside backend: performance EOF hygiene, stronger browser assertions, root wrong-fixture rejection, preservation of existing LF endings, and correction of the new API test's transport expectations. Normalized text bridges retain identical script behavior; source/test receipts distinguish each raw revision.

## Preserved diagnostics and risk

New test diagnostics remain retained. Initial full-document equality assertions incorrectly prohibited normal dependent field auto-confirmation; safe changed-field inspection identified state/field review/events/timestamps/completion metadata, while the original history was unchanged. Corrected tests require immutable source observations/history and allow necessary dependent reviews. A deletion adverse initially used the legacy independently injected-service helper, whose deletion bundle differs from its service repositories; normal app composition now proves404 and no resurrection without a production deletion edit. A supplemental banner assertion initially ran before authentication, where no workspace banner is rendered; the authenticated assertion passed. A new API unit test initially expected a plain object, while the unchanged authenticated owner constructs Headers/includes cookies; focused2/2 and full582/582 now verify exact headers and cookies. These are preserved diagnosed test-fixture expectations, not hidden product waivers or blind CI reruns.

All866 tracked baseline report/planner entries plus the two explicitly required ignored stop records remain byte-identical, including all785 historical reports. Original authenticated progress/RM source, Playwright configuration, stage-disclosure helper and the prior grouped-retry/RM/creation-order corrections remain preserved except the explicitly assigned new owner-local deltas. No protected database, original checkout or unrelated worktree was modified.

SDQ-01 historical cause remains unresolved and is NOT fixed by this task. Prospective owner acceptance requires unchanged original progress assertions/deadlines, current full coverage, eight offline journeys, isolated Windows assessment, no active regression and fresh independent acceptance for this exact candidate. No prior PASS is inherited and no current mandatory failure is waived. SDQ-02 remains independently closed; current lifecycle cleanup must also pass. Real Sandbox UAT/interoperability remains NOT_VERIFIED. No real ACRA/GoldTier writes, merge or auto-merge are performed.

## Change disclosure and remaining boundary

API/shared types: additive derived projection and guarded recovery headers. Durable schema/repository formats: unchanged, schema10. Connector/provider interfaces and classifications: unchanged; isolated test fixture only. Configuration: test fixture allowlist/label and CI inventory comments/assertions; no runtime external setting/dependency/deadline change. Business rule/source precedence/mapping: unchanged. Auth/security: existing owners enforce creator/currentness/freeze for this newly exposed action. Architecture/persistence/cache owners: unchanged. Runtime behavior: the partial replacement checkpoint is visibly and safely recoverable through the normal UI.

The required sequential acceptance stopped at a new reproducible width360 cache lifecycle timeout. Owner review is required before expanding remediation or declaring acceptance. Only exact PASS plus every mandatory check permits latest-main assessment, exact-path staging/scoped commit, clean committed canonical pre-PR/checklist PASS, normal push to existing PR81, both actual nine-job CI results and legitimate reassessment/disposition of both P2 threads. Stop before human merge.

## Bounded acceptance stop

The complete shard1 retained output records17 passing lifecycles/28 passing tests, followed by INDIVIDUAL_SELECTION_TIMEOUT at the unchanged performance-browser.e2e.ts:98 width360 test, lifecycle18/46,66.484 seconds including owned cleanup. The runner stopped the remaining28 shard1 lifecycles; shard2 was not dispatched. One targeted diagnostic with safe per-sample timing reproduced the same60-second guard failure,66.610 seconds including cleanup. It reached index20 warm-navigation render at56.085 seconds from the test body start; both kinds require indices0..21 plus their original500ms accounting tails. This shows accumulated lifecycle work rather than a reported assertion exception. The underlying latency change remains unresolved; no host-contention or harmless-transient conclusion is established. No samples, waits, assertions, timeout, retry, exclusion or runtime source were changed. The probe changed only scratch diagnostic logging and restored its exact original bytes; root source stayed unchanged. An initial pre-execution guard and a helper syntax error were corrected before the single actual diagnostic run.

The extra root-wide Ruff invocation was noncanonical and found15 findings in unchanged scripts. Its complete diagnostic is retained. CI uses Ruff from apps/backend with the owned pyproject configuration; that exact command, mypy and pip check passed. No unrelated lint fixes or lint configuration changes were made.

Fresh independent review/PASS, clean committed pre-PR, commit, push, PR update/reassessment and thread resolution were not performed. Both remote P2 threads remain unresolved; PR81 remote head remains dd8c36c8a911f4b5f3b80e7441d049f1aa976599, MERGEABLE but BLOCKED. Historical push7/9 success with2 failures and PR9/9 success belong only to that previously published head. They provide no CI acceptance for this uncommitted candidate. SDQ-01 historical cause remains unresolved; SDQ-02 remains independently closed. See PR81_FINAL_CI_RECOVERY_STOP_REPORT.md and STOP_EVIDENCE.json.
