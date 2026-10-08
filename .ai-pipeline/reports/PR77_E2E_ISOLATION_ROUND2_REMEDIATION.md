# PR77 E2E isolation round 2 remediation

Outcome: test-only isolation and CI containment remediation implemented; full unfiltered local E2E PASS. This is implementer evidence, not an independent quality-gate verdict. Fresh independent review required: YES.

## Identity, task start, and authority

Date: 2026-10-08, Asia/Singapore. Worktree: C:/Users/shane/.codex-clean2/worktrees/goldtier-reliability-recovery/data-dividends-zero-touch-clm. Branch: codex/goldtier-submission-reliability-recovery-ux. Published/current HEAD: 33bd4c9a113279b2c90554e8c572a9b82f35b04e. BASE_SHA, merge-base, local origin/main, observed remote main and PR base: 5c54c9af896585764d1e4ed809056d1deb576629. Entry tracked/untracked state was clean in this worktree; staging was empty. Primary checkout unrelated artifacts/evaluation/outputs and camunda worktree were preserved.

The explicit pasted round-2 task supplies acceptance and stop conditions. The original reliability UX planner supplies historical scope context and does not authorize new product work. Classes: CI_TOOLING and DOCS_ONLY. TaskStartSnapshot: expected branch/head/base, clean assigned worktree, one writer, current-session PowerShell/GitHub CLI and installed browser/lifecycle tools. ArchitectureReviewRequired: NO; no new owner, dependency, fallback, reset, fixture-state mutation or compatibility path. Change Necessity: code-change at test declarations, plus CI/config governance, because discovery's unique-selector owner requires distinct locations for stateful journeys. Verification uses the required pre-edit failing reproduction, followed by focused and full execution.

Previous accepted cumulative identity f212dcc53e02a11024d9b395015e5d022f6380020ee62e45f061454fff316b14 stays historical. The new exact identity and raw/normalized path hashes are in the companion manifest. It excludes itself to avoid circular hashing; this report is included. Current/tested content is HEAD plus the three-file uncommitted delta. No fresh independent verdict exists. No commit/push/PR update/Actions dispatch/rerun/merge or next phase.

## Fresh CI and causal evidence

[PR77](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/77). Read-only GitHub CLI refreshed both specified runs to completed failure, replacing the planner's pending snapshot. Both report head 33bd4c9a113279b2c90554e8c572a9b82f35b04e, attempt 1.

| Lane | [Push 37720063790](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/actions/runs/37720063790) | [PR 37720067375](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/actions/runs/37720067375) |
| --- | --- | --- |
| backend | success | success |
| frontend | success | success |
| local-ocr | success | success |
| phase12-mongo | success | success |
| security | success | success |
| demo-lifecycle-windows | success | failure |
| e2e | failure | failure |

Push E2E job 113125430892 checks out 33bd4c9a113279b2c90554e8c572a9b82f35b04e. PR E2E job 113125442652 checks out merge preview b881fc874db0bc8db68ecbba61a296d2d38bd7ee, merging that head into 5c54c9af896585764d1e4ed809056d1deb576629; metadata head and tested PR checkout are distinct. Environment: Ubuntu, Python 3.12, Node 22, installed Chromium/Tesseract, mongo:7. Both fail python scripts/run_e2e.py --timeout-seconds 60, exit 1.

Both logs show selector 48/68, e2e/s3-sandbox-submission.e2e.ts:333, three tests/one worker. Aborted passes. Truncated and held fail during prepareReview at line 119: before.calls.SHELL expected 0, received 1, before installing their own loss route. Push: 1 passed/2 failed (10.6s); PR: 1 passed/2 failed (12.4s). No timeout explains this E2E failure.

Actual pre-edit Playwright JSON: 77 tests/68 selectors; all three loss cases share line 333 and success fixture. Before editing, the actual local launcher with --timeout-seconds 60 --sandbox-demo success --grep "Lost confirmation response" reproduced 1 passed/2 failed (8.8s), same Shell 0/1 assertion.

Root cause: one dynamic declaration generates three tests with one source location. The launcher intentionally creates one target fixture process per unique selector. OfflineS3SandboxTransport retains created state and absolute operation counters in that process; a new case ID cannot reset that owner. The first test leaves Shell/Policy 1; later tests require zero. The repair gives each stateful journey its own location/lifecycle. Counterfactual evidence: all three pass with fresh lifecycles and the same body/product/fixture code. Distinct fixture modes already caused the earlier Shell/Policy collision; this same-mode collision instead contaminates state. No product defect is proved.

## Delta and preservation

One runLostConfirmationResponse helper retains all 49 original body lines exactly after UTF-8 CRLF normalization. Body SHA256: 91b0cb640df6a6f2067c9cf38e603b6728dd11347cefb3d333746760414f7b7d. Preserves every assertion, title, @s3-sandbox-success tag, timeout, confirmation POST 1, Shell 1/Policy 1/Amend 0/Readback 1, external_calls 0, GET-only observation, no replay, verification/focus/viewport UI and screenshots. No reset or fixture mutation. Prefix through the inherited Shell/Policy helper/declarations and Garden suffix are exactly preserved. Runner/configuration/fixtures are unchanged.

| Scenario | Before selector | After selector | Fixture |
| --- | --- | --- | --- |
| aborted | e2e/s3-sandbox-submission.e2e.ts:333 | e2e/s3-sandbox-submission.e2e.ts:387 | success |
| truncated | e2e/s3-sandbox-submission.e2e.ts:333 | e2e/s3-sandbox-submission.e2e.ts:395 | success |
| held | e2e/s3-sandbox-submission.e2e.ts:333 | e2e/s3-sandbox-submission.e2e.ts:403 | success |

## Complete actual-discovery duplicate audit

All pre-edit duplicates are below. Post-edit discovery retains only the first three. Exact titles, groups and fixture maps are in the manifest. Each group's source behavior was inspected, then verified together in the full suite.

| Selector | Tests sharing selector | Fixture mode(s) | Mutable shared fixture state? | Intentional/safe? |
| --- | --- | --- | --- | --- |
| e2e/phase24-identity.e2e.ts:157 | document UEN choice; other UEN choice (2) | default Mock/memory | Cases, ownership, sessions | Safe: each creates a distinct case and analysis; all assertions bind returned case ID. Old/new analysis comparison stays within that case. No global empty-count/first-call assumption. Both pass in one lifecycle. |
| e2e/phase24c-policy.e2e.ts:34 | policy approval/layout widths 320,360,768,1280,1440,1920 (6) | default Mock/memory | Active policy and proposal history persist | Intentional/safe: each captures current active heading/version, creates a new proposal and reviews newest proposal. Each proposes 0.90 against its captured baseline and only proposes reset to defaults. No first-version/empty-history/provider-counter assumption. All 6 pass together inside unchanged lifecycle deadline. |
| e2e/zero-touch-exception.e2e.ts:159 | Garden clean; Garden conflict (2) | garden-protocol/local ownership/Mock target | Case/provider activity persists | Safe: separate case IDs bind all document/reconciliation/ownership assertions; existing beforeEach resets browser request/violation arrays. No absolute global counter expectation; neither sends target confirmation. Both pass in one lifecycle. |
| e2e/s3-sandbox-submission.e2e.ts:333 (before only) | aborted; truncated; held (3) | success/offline Sandbox transport | created flag and absolute Shell/Policy counters | Unsafe: all require zero before sending. Fixed by three explicit declarations, each with its own fresh lifecycle. |

No other duplicate found. No safe group split. Inherited Shell/Policy remain :324/:328 and uncertain-shell/uncertain-policy; exact prefix comparison preserves prior repair, and both pass in this full run.

## Discovery and containment

Fresh npm run e2e:list: exit 0, 77 tests/14 files. Actual --list --reporter=json plus unchanged parser: 77 tests/70 ordered unique selectors, no conflict. Three locations replace one; inventory grows exactly 2, with no test removal/addition.

60 + 70*(60+120) = 12660 seconds = 211 minutes. Installation reserve 14 minutes = 840 seconds. Outer job 211+14=225 minutes =13500 seconds. CI comment/timeout and existing governance assertion use that exact count/bound. Assertion discovers real selectors, requires70, derives12660 and checks full-budget dispatch/containment. Fail-closed exhaustion regressions pass.

Unchanged: discovery 60s, execution/readiness 60s per lifecycle, overhead 120s, process ownership/stop bounds, routing, one Playwright worker, fullyParallel false, retries 0, test timeout 120000ms and expect timeout 15000ms. CI outer timeout is tooling configuration only; product configuration is unchanged.

## Three affected browser scenarios

Actual separate launcher commands: --timeout-seconds 60 --sandbox-demo success --grep "Lost confirmation response.*: scenario". One test per new backend/frontend/fixture lifecycle.

| Scenario | Exit | Launcher wall seconds |
| --- | --- | --- |
| aborted | 0 | 8.282 |
| truncated | 0 | 7.359 |
| held | 0 | 16.328 |

All passed preparation Shell 0/Policy 0/Amend 0/external_calls 0; then confirmation POST 1, Search 2/Shell 1/Policy 1/Amend 0/Readback 1, external_calls 0 and COMPLETED. Existing route/assertion coverage proves disabled controls, no alert, verification and confirmed heading focus/viewport, authoritative GET observation, removed send control and no second confirmation/retry/replay. An initial anchored grep found no tests because Playwright appends the tag; the command filter was corrected, with no source change. Those diagnostic no-test invocations are not passing evidence or retries.

## Complete unfiltered local run

Normal command: dependency-complete Python 3.12.10 executes scripts/run_e2e.py --timeout-seconds 60, no filter or composition override. Final exit 0; E2E SUITE PASS: 70 configured selectors passed in isolated lifecycles. All 77 tests passed; all 70 selectors dispatched in exact discovery order; zero failed/skipped/undispatched selectors, zero retries, no fixture conflict/state contamination/suite timeout. Wall time 664.109s (11.07 minutes). Slowest lifecycle 27/70: e2e/phase24c-policy.e2e.ts:34, 23.203s including dispatch/cleanup; execution deadline remains60s.

First full attempt remains recorded: exit 1 after 143.578s; selectors 1..13 pass, selector 14 fails backend readiness, selectors 15..70 undispatched. Docker was initially unavailable, then the task container was initially bound to the wrong port. Its correction to the launcher's fixed 27185 crossed database-fixture startup. Sanitized fixture failure occurred before browser execution; parent cleanup was verified. After the required port was ready, exact server composition succeeded with ephemeral credentials/new allowlisted database and no source change. The complete suite was restarted and passed. This is corrected local setup, not a suppressed failure or a retry setting; the failed attempt is retained.

Every dispatched selector and timing follows; the manifest carries the same inventory.

| Dispatch | Selector | Tests | Result | Lifecycle seconds |
| --- | --- | --- | --- | --- |
| 1 | e2e/authenticated-zero-touch.e2e.ts:229 | 1 | PASS | 5.469 |
| 2 | e2e/authenticated-zero-touch.e2e.ts:241 | 1 | PASS | 20.328 |
| 3 | e2e/authenticated-zero-touch.e2e.ts:643 | 1 | PASS | 8.093 |
| 4 | e2e/authenticated-zero-touch.e2e.ts:685 | 1 | PASS | 11.297 |
| 5 | e2e/authenticated-zero-touch.e2e.ts:776 | 1 | PASS | 9.297 |
| 6 | e2e/authenticated-zero-touch.e2e.ts:842 | 1 | PASS | 7.735 |
| 7 | e2e/authenticated-zero-touch.e2e.ts:931 | 1 | PASS | 6.750 |
| 8 | e2e/authenticated-zero-touch.e2e.ts:1019 | 1 | PASS | 11.484 |
| 9 | e2e/authenticated-zero-touch.e2e.ts:1191 | 1 | PASS | 7.094 |
| 10 | e2e/authenticated-zero-touch.e2e.ts:1237 | 1 | PASS | 11.718 |
| 11 | e2e/authenticated-zero-touch.e2e.ts:1369 | 1 | PASS | 9.063 |
| 12 | e2e/authenticated-zero-touch.e2e.ts:1499 | 1 | PASS | 10.719 |
| 13 | e2e/authenticated-zero-touch.e2e.ts:1611 | 1 | PASS | 7.078 |
| 14 | e2e/database-classification.e2e.ts:96 | 1 | PASS | 10.547 |
| 15 | e2e/database-classification.e2e.ts:97 | 1 | PASS | 11.625 |
| 16 | e2e/database-classification.e2e.ts:98 | 1 | PASS | 8.906 |
| 17 | e2e/database-classification.e2e.ts:101 | 1 | PASS | 11.531 |
| 18 | e2e/garden-happy-path.e2e.ts:183 | 1 | PASS | 8.235 |
| 19 | e2e/garden-happy-path.e2e.ts:243 | 1 | PASS | 13.203 |
| 20 | e2e/garden-happy-path.e2e.ts:327 | 1 | PASS | 9.781 |
| 21 | e2e/garden-happy-path.e2e.ts:349 | 1 | PASS | 8.234 |
| 22 | e2e/garden-happy-path.e2e.ts:400 | 1 | PASS | 6.969 |
| 23 | e2e/onboarding-recovery.e2e.ts:6 | 1 | PASS | 7.656 |
| 24 | e2e/phase24-identity.e2e.ts:83 | 1 | PASS | 7.485 |
| 25 | e2e/phase24-identity.e2e.ts:138 | 1 | PASS | 8.062 |
| 26 | e2e/phase24-identity.e2e.ts:157 | 2 | PASS | 20.500 |
| 27 | e2e/phase24c-policy.e2e.ts:34 | 6 | PASS | 23.203 |
| 28 | e2e/phase24c-policy.e2e.ts:79 | 1 | PASS | 6.360 |
| 29 | e2e/responsive-layout.e2e.ts:308 | 1 | PASS | 9.922 |
| 30 | e2e/responsive-layout.e2e.ts:347 | 1 | PASS | 11.953 |
| 31 | e2e/responsive-layout.e2e.ts:404 | 1 | PASS | 7.906 |
| 32 | e2e/responsive-layout.e2e.ts:440 | 1 | PASS | 8.484 |
| 33 | e2e/responsive-layout.e2e.ts:476 | 1 | PASS | 8.188 |
| 34 | e2e/responsive-layout.e2e.ts:494 | 1 | PASS | 6.234 |
| 35 | e2e/responsive-layout.e2e.ts:502 | 1 | PASS | 7.781 |
| 36 | e2e/s1-workspace-session.e2e.ts:93 | 1 | PASS | 6.875 |
| 37 | e2e/s1-workspace-session.e2e.ts:123 | 1 | PASS | 12.657 |
| 38 | e2e/s1-workspace-session.e2e.ts:186 | 1 | PASS | 7.906 |
| 39 | e2e/s1-workspace-session.e2e.ts:213 | 1 | PASS | 6.953 |
| 40 | e2e/s2-ownership.e2e.ts:55 | 1 | PASS | 8.297 |
| 41 | e2e/s2-ownership.e2e.ts:112 | 1 | PASS | 6.641 |
| 42 | e2e/s3-sandbox-submission.e2e.ts:124 | 1 | PASS | 8.421 |
| 43 | e2e/s3-sandbox-submission.e2e.ts:201 | 1 | PASS | 7.047 |
| 44 | e2e/s3-sandbox-submission.e2e.ts:204 | 1 | PASS | 6.985 |
| 45 | e2e/s3-sandbox-submission.e2e.ts:207 | 1 | PASS | 7.031 |
| 46 | e2e/s3-sandbox-submission.e2e.ts:324 | 1 | PASS | 9.875 |
| 47 | e2e/s3-sandbox-submission.e2e.ts:328 | 1 | PASS | 9.609 |
| 48 | e2e/s3-sandbox-submission.e2e.ts:387 | 1 | PASS | 6.985 |
| 49 | e2e/s3-sandbox-submission.e2e.ts:395 | 1 | PASS | 7.218 |
| 50 | e2e/s3-sandbox-submission.e2e.ts:403 | 1 | PASS | 16.032 |
| 51 | e2e/s3-sandbox-submission.e2e.ts:411 | 1 | PASS | 9.343 |
| 52 | e2e/slice-b-registry-demo.e2e.ts:91 | 1 | PASS | 8.438 |
| 53 | e2e/slice-b-registry-demo.e2e.ts:118 | 1 | PASS | 8.000 |
| 54 | e2e/slice-b-registry-demo.e2e.ts:128 | 1 | PASS | 8.812 |
| 55 | e2e/slice-b-registry-demo.e2e.ts:149 | 1 | PASS | 9.375 |
| 56 | e2e/slice-b-registry-demo.e2e.ts:172 | 1 | PASS | 6.891 |
| 57 | e2e/slice-c-recovery.e2e.ts:119 | 1 | PASS | 8.422 |
| 58 | e2e/slice-c-recovery.e2e.ts:140 | 1 | PASS | 8.578 |
| 59 | e2e/slice-c-recovery.e2e.ts:161 | 1 | PASS | 8.422 |
| 60 | e2e/slice-c-recovery.e2e.ts:194 | 1 | PASS | 8.609 |
| 61 | e2e/slice-c-recovery.e2e.ts:240 | 1 | PASS | 9.250 |
| 62 | e2e/slice-c-recovery.e2e.ts:243 | 1 | PASS | 9.453 |
| 63 | e2e/slice-c-recovery.e2e.ts:246 | 1 | PASS | 8.344 |
| 64 | e2e/slice-c-recovery.e2e.ts:276 | 1 | PASS | 10.485 |
| 65 | e2e/slice-c-recovery.e2e.ts:279 | 1 | PASS | 10.984 |
| 66 | e2e/slice-c-recovery.e2e.ts:284 | 1 | PASS | 8.531 |
| 67 | e2e/slice-e-policy.e2e.ts:64 | 1 | PASS | 14.344 |
| 68 | e2e/slice-e-policy.e2e.ts:114 | 1 | PASS | 7.172 |
| 69 | e2e/zero-touch-exception.e2e.ts:124 | 1 | PASS | 9.515 |
| 70 | e2e/zero-touch-exception.e2e.ts:159 | 2 | PASS | 12.657 |

## Windows finding

PR Windows job 113125442780: test_backend_override_only_preserves_frontend_default errors in resolve_lifecycle_ports (test173/helper143). powershell.exe -NoProfile parsing/launching Resolve-DemoPorts exceeds subprocess timeout 15s. 31 tests, one error, exit 1. Same-head push Windows job 113125430683 succeeds. Classification: CI/ENVIRONMENT - plausible transient, not yet proven. Windows timeout/lifecycle PowerShell/retry/assertions remain unchanged. Fresh publication push/PR lanes must be assessed; recurrence requires separate owner decision.

## Focused checks and session resources

| Check | Fresh result |
| --- | --- |
| pytest launcher plus Slice B/C/F fixture-routing files | 66 passed, zero skips, 9.06s, exit 0; one existing Starlette/httpx deprecation warning |
| npm run e2e:list; actual JSON/parser | 77 tests/14 files; 70 selectors, exit 0 |
| npm run typecheck | exit 0 |
| Ruff --no-cache, runner and four focused Python test files | PASS |
| check_tooling_config.py | PASS |
| check_project_state.py | PASS |
| check_architecture.py | PASS |
| check_secrets.py | PASS, tracked/explicit task-owned paths only |
| git diff --check; explicit Markdown/JSON hygiene | PASS at final readback |
| Exact body/prefix/suffix/runner comparisons | PASS |
| YAML whole-document semantic comparison | Only outer E2E timeout differs |
| Published-blob product source comparison | 229 tracked files unchanged |

Ran dev_context.py for CI_TOOLING/DOCS_ONLY and read emitted Tier 1 sections, applicable original planner, nearest accepted remediation/gate and owning source/tests. FYP implementation/CI triage plus Aegis debugging/verification guided proof, minimality and completion boundary. No subagents/independent reviewer in this run. Approved PowerShell execution handles worktree/network restrictions. Primary checkout .venv supplies dependencies read-only; imports use candidate source. Dotenv disabled before application imports; no .env access. Focused-check Python bytecode/pytest caches disabled.

Observed runtimes: Python 3.12.10, Node 22.23.3, npm 10.9.9, Playwright 1.56.1, Tesseract 5.4.0.20240606, Docker 29.8.1, existing mongo:7 image. Launcher owns ports starting 8765/4173. Task-only Mongo on loopback 27185 uses newly generated allowlisted clm_p16 databases and verified cleanup. No clm_poc access, sponsor credentials or real provider calls, new dependency installation or unrelated container modification. Task container removed after checks; Docker Desktop remains available. Test-generated tracked screenshots restored from published bytes, preserving historical evidence.

## Source proof and exact change inventory

All 229 tracked paths under apps/backend/app and apps/frontend/src equal published HEAD after CRLF normalization; product Git diff empty. Manifest binds per-path hashes and aggregate. Runner, Playwright configuration, fixture behavior, earlier reports/manifests and tracked screenshot evidence are unchanged. Complete three-file diff and new report/manifest read back; no secret/confidential artifact newly staged/tracked.

Changed from current published HEAD:

- .github/workflows/ci.yml
- apps/frontend/e2e/s3-sandbox-submission.e2e.ts
- tests/test_run_e2e.py
- .ai-pipeline/reports/PR77_E2E_ISOLATION_ROUND2_REMEDIATION.md (new)
- .ai-pipeline/reports/PR77_E2E_ISOLATION_ROUND2_REMEDIATION_MANIFEST.json (new)

API/shared types NO; schema/persistence NO; connector NO; runtime configuration NO; business rule NO; mapping NO; auth/security NO; architecture NO; provider status NO; runtime behavior NO. E2E declarations, CI outer timeout and its governance assertion YES. Cumulative freeze retains already published Shell/Policy and earlier accepted product work; this round adds no product delta.

## Limitations and stop

Synthetic Mock/Local/offline Sandbox execution is not Live interoperability, sponsor approval or production readiness. Fresh CI for uncommitted remediation has not run. Windows finding awaits publication lanes. Unrelated full backend/frontend unit suites, build and clean-committed pre_pr_check publication gate were not rerun; no stale evidence relabeled as fresh.

Fresh independent review required YES, against companion manifest identity. Staging remains empty. Stop for owner/planner review; publication separately authorized only after exact independent PASS. No commit/push/PR update/Actions rerun/merge or next phase.
