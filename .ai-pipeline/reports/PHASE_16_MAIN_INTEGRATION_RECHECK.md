# Phase 16 Main Integration — Fresh Independent Recheck

Date: 2026-09-21

Reviewer role: fresh independent integration reviewer; report-only writer

## Executive result

**READY FOR OWNER RISK DECISION**

The final integrated PR #41 tree has no current technical, content, contract, policy, or required-CI blocker. Both specified hosted runs completed successfully against the same final tree. Their logs prove execution of every required job, including the intended 23-test Windows lifecycle module and the guarded five-suite physical Mongo runner.

This result does not erase or causally resolve the earlier Phase 13 loopback timeout or the integrated Phase 16 post-reset login response-acquisition timeout. It does not reuse PR #42's owner decision as a waiver for PR #41. A repository owner must decide whether to accept the precisely bounded residual uncertainty for this exact POC revision before merge consideration.

## Reviewed identities and preflight

| Identity | Observed value |
|---|---|
| Worktree | `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix` |
| Branch | `phase/16-registry-cache-freshness-planning` |
| Final PR head | `c9d5ced876e4b5bf50dc5cb56f3da39311458376` |
| Final tree | `98021f092b9348abd1c99e7901bb1c4da0c45e76` |
| PR base / current remote `main` | `bc21070fc1f45729e374a5cbe6425d89b8956ab9` |
| Original Phase 16 head | `92cc8fa9f971a937b7f6696eb06f8675da7e9b05` |
| Latest-main integration commit | `d8fc4ecd04459cfa4b39c920e9e67fab707eb039` |
| Diagnostic commit | `c9d5ced876e4b5bf50dc5cb56f3da39311458376` |
| PR test merge commit | `9abc2072adbedea5934d8b22ae65b2df19508806` |
| PR test merge tree | `98021f092b9348abd1c99e7901bb1c4da0c45e76` |

GitHub reports PR #41 as open, non-draft, mergeable, and `CLEAN`, with head `c9d5ced...` and base `bc21070...`. Read-only remote-ref inspection independently returned the same feature and `main` SHAs. The synthetic pull-request merge commit has parents `bc21070...` and `c9d5ced...` and the same tree as the feature head, so the push and pull-request runs exercised identical content even though their checkout commits differ.

At review start the worktree and index were clean. No unresolved path, merge, rebase, cherry-pick, revert, bisect state, or Git lock was present. No active repository writer was observed. `git diff --check` passed and the tracked-tree conflict-marker scan found none. The reviewer used local read-only Git/source inspection and authenticated read-only GitHub CLI access. No browser, local service, lifecycle process, database, provider, credential, `.env`, protected sponsor artifact, or reserved port was used. No CI or local behavioral suite was rerun.

## Authoritative hosted CI

Both specified Project CI runs are completed with conclusion `success`, attempt 1, for final head `c9d5ced...`.

| Run | Event and checkout | Required execution evidence |
|---|---|---|
| `35523101457` | `push`; checkout `c9d5ced...`; tree `98021f0...` | backend, frontend, E2E, phase12-mongo, security, and demo-lifecycle-windows all completed successfully |
| `35523103474` | `pull_request`; actual checkout `9abc207...`; tree `98021f0...` | backend, frontend, E2E, phase12-mongo, security, and demo-lifecycle-windows all completed successfully |

Detailed log evidence is identical in substance across the two runs:

- Backend: Ruff passed; mypy passed for 94 source files; pytest passed `1036` with `22` skips; the separately invoked contract suite ran `44/44`; delivery-assets ran `4/4`. The complete CI-owned backend/contract/delivery inventory is therefore `1084` passing plus `22` intentional physical-only skips.
- Frontend: typecheck passed; Vitest ran `212/212` across 11 files; production build passed.
- E2E: the repository runner executed the listed three Playwright tests using one worker and passed `3/3` in each run.
- Physical Mongo: the guarded runner emitted `PHYSICAL_MONGO_RESULT=PASSED; SUITES=5; COLLECTED=22; PASSED=22; FAILED=0; ERRORS=0; SKIPPED=0` in each run. This is execution evidence, not a skipped or shell-only success.
- Windows lifecycle: the job invoked `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_demo_lifecycle_windows.py" -v`; the post-reset selector `test_reset_restarts_and_clears_process_local_case` passed; the module ran `23/23` in 175.545 seconds for push and 192.174 seconds for pull request. The three diagnostic helper tests were therefore included with the 20 existing lifecycle tests.
- Security: the secret units, pre-PR units, project-state/architecture units, project-state checker, architecture checker, tooling checker, secret scanner, and GoldTier example validation all ran successfully. The scanner reported no supported secret pattern.

No current lifecycle, backend, Mongo, frontend, E2E, or security failure exists in either required run.

## Integrated-tree content preservation

### Phase 16 registry cache and persistence

The 44-path Phase 16 delta from `cab05d7...` to `92cc8fa...` has zero path overlap with the later `92cc8fa...` to `c9d5ced...` delta. Current backend production content under `apps/backend/app` is byte-unchanged from the original accepted Phase 16 head. Source inspection and current CI therefore preserve the accepted behavior:

- registry caching is `disabled` by default;
- enabling is restricted to synthetic Mock ACRA and rejects non-Mock composition;
- freshness is exactly `7_776_000` elapsed seconds with fresh strictly before expiry and stale at expiry;
- exact keys bind provider, environment, acquisition-contract version, data-set namespace, and normalized identifier;
- only complete four-operation normalized acquisitions are published to shared cache state;
- each enabled successful use receives an immutable defensive case binding labelled `PROVIDER_FETCH` or `CACHE_HIT` only after a committed read/write;
- case schema v4 retains strict v1/v2/v3 compatibility with an absent historical binding and no version-only rewrite;
- registry-cache schema v1 remains separate from the case envelope and uses insert-only create plus expected-revision replacement without upsert;
- memory and Mongo retain explicit, fail-closed ownership with no silent fallback;
- target execution and no-replay recovery remain ledger-owned; no Phase 16 or later production backend change bypasses that owner;
- no forced refresh, scheduler, existing-case reassessment, sandbox/live cache, production retention rule, distributed exactly-once claim, or Live-provider claim was introduced.

The original Phase 16 quality-gate `PASS`, whitespace recheck `PASS`, and architecture/persistence `PROCEED` re-review remain historical acceptance evidence for the exact Phase 16 content. The hosted backend and physical Mongo runs now provide current final-tree behavioral evidence after main integration and diagnostics.

### PR #40 Camunda boundary

PR #40 is integrated as main commit `5f31aced13bd99df78329c5a9055cffaeb168ddd`. Its observer support and contract remain under `apps/backend/tests` only. Current bounded search found zero references to the observer support module, test module, or `clm.observe-case.v1` in backend production code, frontend production code, or GitHub workflow composition. `scripts/check_project_state.py` exempts only the exact backend test tree while continuing to reject Camunda-named runtime paths, and current security CI passed that governance boundary.

The only justified statement remains **OFFLINE CONTRACT VERIFIED**. No Camunda worker, SDK, cluster, authentication, deployment, production runtime, or Live capability is claimed.

### PR #42 UI and session generation

PR #42 is integrated as main commit `bc21070fc1f45729e374a5cbe6425d89b8956ab9`. Current source preserves request-bound authenticated-transport generations: a stale `401` can publish logout only when its captured generation is still current. Session acceptance and clearing still clear incompatible query state and rotate the transport generation. Case-detail mutations, polling, deletion, priority, replacement, and field review remain bound to current actor/case/action generations, preventing stale completion from publishing into a replacement session or route identity.

Current frontend `212/212`, typecheck/build, and Playwright `3/3` results in both runs exercise the integrated session-generation and UI behavior. The earlier PR #42 lifecycle/browser incidents remain governed by the repository owner's explicit PR #42 decision for head `75d61cb...` only. That decision expressly did not prove a fix, production availability, or a future waiver, and it does not waive PR #41's later post-reset failure.

### Latest-main merge and diagnostic delta

The latest-main merge had no overlapping Phase 16-owned path and no unresolved conflict. The diagnostic commit changes only `tests/test_demo_lifecycle_windows.py` plus its two reports; it changes zero production paths under `apps`, `scripts`, or `.github`. The final diagnostic implementation retains the existing three-second request timeout, fresh cookie jar, authentication payload, CSRF/origin behavior, target request, and expected post-reset `404`. It adds bounded sanitized stage classification, no retry or synthetic success.

No merge resolution or later diagnostic work unexpectedly changes production semantics.

## Local evidence reconciliation

The assigned local evidence is consistent with the final hosted inventory and must be interpreted lane by lane:

| Evidence | What it proves | What it does not prove |
|---|---|---|
| Focused integration checks passed | Direct integration slices remained green after latest-main merge | They are narrower than full final-tree acceptance |
| First complete local backend/contract/delivery run: `1083` passed, `22` skipped, one timeout failure | A real failure occurred in the complete local run and must remain in history | It is not a passing run and supplies no cause |
| Isolated failing selector passed | The earlier failure was not deterministic in isolation | It does not erase the failure or establish infrastructure, scheduling, or any other cause |
| Confirmatory complete local run: `1084` passed, `22` skipped | The complete local inventory later passed without a code claim that fixed the event | It does not retroactively convert the earlier run to PASS |
| Frontend `212/212`, typecheck, and build | Integrated frontend deterministic behavior and compilation passed | It is not browser/process evidence by itself |
| Guarded Playwright `3/3` | Real HTTP/browser paths passed in the guarded local run | It does not prove production availability or explain older browser incidents |
| Physical Mongo: five suites, `22/22`, zero skips/errors/failures | Current owned durable-schema/restart/CAS behavior passed against a physical server with guarded ownership | It does not waive a lifecycle/authentication failure or prove distributed guarantees |
| Diagnostic helper `3/3` and independent exact `PASS` | Sanitized failure-stage classification preserves exception behavior, no retry, and no target dispatch after login failure | It does not identify the historical cause or prove the timeout fixed |
| Clean-tree pre-PR `PASS` | The committed feature tree satisfied the deterministic repository publication gate at that evidence point | It does not replace semantic review, CI, owner risk acceptance, or human merge authority |

The apparent local/CI count difference is only command partitioning: hosted CI reports `1036` backend pytest passes, then `44` contract and `4` delivery passes in separate steps, totalling the same `1084`, with `22` skips. The current hosted results are final-tree evidence; the earlier local failure remains historical evidence rather than being rewritten.

## Distinct unresolved historical events

### A. Earlier Phase 13 backend loopback timeout

One full backend run failed at the separate live-loopback `HttpSeedApi`/in-process service boundary. The isolated diagnosis passed and one confirmatory full run passed. No causal correction was established, and retained evidence does not place this event at the same response stage as the later login timeout. It remains separately disclosed pre-existing harness uncertainty.

### B. Integrated Phase 16 post-reset login timeout

The integrated local lifecycle failure occurred while `opener.open(login_request, timeout=3)` waited in `HTTPConnection.getresponse()` / `HTTPResponse._read_status()` for the login response status line. No response status, headers, body, or parsed login result was obtained, and the post-reset target GET was never dispatched. One differentiated physical selector later passed without reproducing the event. The root cause remains unknown; no authentication, launcher, lifecycle, persistence, timeout, or infrastructure fix was established.

### C. PR #42 lifecycle/browser incidents

PR #42's historical frontend-health and browser incidents remain distinct. The repository owner's recorded decision accepted that bounded residual risk only for PR #42's exact POC revision after its required current CI passed. That decision neither explains nor waives PR #41's later failure.

## Policy assessment and current blockers

Repository policy requires current required checks to execute and pass, distinguishes reproducible defects, missing infrastructure, stale evidence, and unresolved authority, and forbids calling skipped, failed, or stale evidence successful. It does not state that every non-reproduced historical transient must receive a speculative causal change before an owner may make a bounded risk decision.

The earlier diagnostic report's `DIAGNOSIS INCOMPLETE — INTEGRATION BLOCKED` conclusion remains truthful for its then-current evidence boundary: the historical event had no cause and final hosted CI had not yet supplied current acceptance evidence. This recheck does not rewrite that history. Both final-tree hosted runs now pass every required job, including lifecycle and physical Mongo, so no current technical/content/policy blocker remains.

Current blockers: **none before the owner-risk boundary**.

Human review/protection requirements and repository-owner merge authority remain mandatory after any owner decision. This report does not declare the PR ready for merge.

## Owner-risk boundary

The owner may decide only whether to accept, for PR #41 at head `c9d5ced...` and tree `98021f0...`, the residual uncertainty that the integrated Phase 16 post-reset login response-acquisition timeout has no established cause or correction, while retaining the separately disclosed Phase 13 uncertainty.

Any acceptance must not claim that:

- the login timeout was fixed;
- CI or infrastructure was proved to be the cause;
- production availability or reliability was proved;
- any future lifecycle failure is waived;
- any timeout, authentication, security, lifecycle, or physical-persistence check may be weakened, skipped, or disabled.

The diagnostic instrumentation must remain so that any recurrence is classified at the observed boundary before remediation is selected. The owner retains final review, risk acceptance, and merge authority.

## Findings and independent verdict

Current critical, high, medium, or low integration blockers: **none**.

Residual risk requiring owner disposition: **the unresolved, non-reproduced post-reset login response-acquisition timeout for this exact POC revision, with the earlier Phase 13 event retained separately**.

**INDEPENDENT INTEGRATION PASS — READY FOR OWNER RISK DECISION**

## Final Git and write state

Before this report, the branch, remote feature ref, and PR head all matched `c9d5ced...`; current remote `main` and PR base matched `bc21070...`; the worktree and index were clean. This report is the reviewer's only filesystem write. No implementation, test, configuration, ordinary documentation, PR metadata, stage, commit, push, fetch, branch switch, reset, rebase, stash, clean, CI rerun, or merge was performed.
