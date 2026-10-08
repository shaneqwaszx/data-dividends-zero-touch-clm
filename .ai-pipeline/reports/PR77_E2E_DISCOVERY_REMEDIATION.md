# PR77 E2E discovery remediation

Date: 2026-10-08 (Asia/Singapore). Bounded CI_TOOLING / test-only implementation verified;
fresh independent review REQUIRED. This is implementer evidence, not a Quality Gate verdict.

## Outcome and identity

The shared Director recovery journey is now one helper with two explicit test declarations
on distinct source lines. Actual unfiltered Playwright discovery and the original launcher
parser succeed. Both actual recovery browser scenarios pass. The harness conflict guard
remains unchanged and fail-closed. Product behavior is unchanged.

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/goldtier-reliability-recovery/data-dividends-zero-touch-clm`.
- Branch: `codex/goldtier-submission-reliability-recovery-ux`.
- PR: https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/77.
- PR head and current HEAD: `6fc74b99fb6d2f98caf02eb32418b2e28afe3e1c`.
- BASE_SHA, merge base, local origin/main and remotely inspected current main: `5c54c9af896585764d1e4ed809056d1deb576629`.
- Starting status: clean, staged diff empty, exactly the required published head.
- Current source/test content: published HEAD plus the single uncommitted E2E definition delta.
- New bounded remediation identity (one test path): `59fe071b689d3f44d4b65540d6ae24f70d3639874418661268dcae77b32c07c6`.
- New cumulative source identity (original 25-path scope): `39fe886a782c98504c1ab24056702e80f828ec079c6a46ef511f6d0c26aed33c`.
- Historical accepted source: `ffd55df6bacc51691dfc00b8d7d6e01860338e41863077ef61b87b28bdc2f5e7`.
- Historical accepted evidence bundle: `962d1e04b7d55d90bad50003d9b964dcb4e0214f237f655192659486eb424582`.

Identities use sorted UTF-8 repository-relative path + NUL + CRLF-normalized bytes + NUL,
cumulative SHA256. The new manifest binds the changed test and this report into a separate
frozen review bundle, records per-path raw/normalized hashes, and excludes its own bytes
from that bundle to avoid a circular hash. Previous reports/manifests remain untouched.
No fresh independent verdict has been issued for this delta.

## Authoritative CI and pre-fix reproduction

Read-only GitHub inspection confirmed push run37661429136, E2E job112929655459, and
pull_request run37661455938, E2E job112929750002, both at PR head above. Both failed
`python scripts/run_e2e.py --timeout-seconds 60`, exit1, with:

`E2E FAILED: Playwright test discovery returned conflicting fixture modes`

Their backend, frontend, security, local-ocr, phase12-mongo and demo-lifecycle-windows
jobs all completed successfully at final inspection. These are historical published-head
results, not fresh CI for the uncommitted repair.
CI uses ubuntu-latest, Python3.12 (PR log3.12.14), Node22, npm ci, pinned Playwright1.56.1,
and installed Chromium. The failure occurred in discovery before browser assertions.

Pre-fix execution used installed Playwright CLI `test --config playwright.config.ts
--list --reporter=json`, the same command/environment constructed by
`run_e2e._list_test_selectors`. It listed77 tests. Actual JSON contained:

| Scenario | Before selector | Tag / corresponding fixture |
| --- | --- | --- |
| Director recovers uncertain shell and continues the original submission | e2e/s3-sandbox-submission.e2e.ts:222 | @s3-sandbox-uncertain-shell / uncertain-shell |
| Director recovers uncertain policy and continues the original submission | e2e/s3-sandbox-submission.e2e.ts:222 | @s3-sandbox-uncertain-policy / uncertain-policy |

Feeding that unfiltered JSON through the unchanged parser reproduced the exact conflict.
Calling the original `main(['--timeout-seconds','60'])` returned1 with the same error;
an observation-only spy proved OwnedProcess constructor calls=0. No backend, frontend
or browser lifecycle was created. The common dynamic test declaration produced a shared
file:line selector with different fixture modes. This is a test-definition defect.

## Delta and preservation

Only accepted-code path changed: `apps/frontend/e2e/s3-sandbox-submission.e2e.ts`.
Task-owned additions: this report and `.ai-pipeline/reports/PR77_E2E_DISCOVERY_REMEDIATION_MANIFEST.json`.

`runDirectorRecovery(page: Page, operation: "shell" | "policy")` contains the entire
original journey. Shell and Policy call it from separate explicit declarations with
unchanged names and exact tags. All100 original body lines are preserved modulo
indentation; dedented body SHA256 is `aeb0897f7ef5358fe6c2f33ec0fdcd049431de9f228b75246546e0f71b7a0129`. The complete file prefix/suffix
outside this repair is unchanged after repository line-ending normalization.
No assertion, timeout, fixture semantic, scenario or test is removed or loosened.

The harness must reject a selector that could run with different fixture composition.
It remains the fixture-routing owner; weakening its guard would conceal the declaration
collision. scripts/run_e2e.py, tests/test_run_e2e.py, routing tests, provider fixtures,
product frontend/backend source and workflow/configuration are unchanged.

## Actual post-fix discovery

| Scenario | After selector | Exact tag / fixture |
| --- | --- | --- |
| Director uncertain Shell recovery | e2e/s3-sandbox-submission.e2e.ts:324 | @s3-sandbox-uncertain-shell / uncertain-shell |
| Director uncertain Policy recovery | e2e/s3-sandbox-submission.e2e.ts:328 | @s3-sandbox-uncertain-policy / uncertain-policy |

Complete JSON discovery lists77 tests and the unfiltered parser returns68 unique
lifecycle selectors, with garden8 / registry5 / recovery4 / Sandbox12 fixture selectors.
Each repaired selector has exactly one corresponding Sandbox mode. The original
`_list_test_selectors(4173, sandbox_selectors={})` completes successfully.

The exact CLI main entry with `--timeout-seconds 60` was also executed through discovery
and deterministic port allocation. An explicit observation-only stop at the first
lifecycle dispatch proved discovery completed; no lifecycle result was fabricated.
It printed selectors=68 / lifecycle_seconds=60 / suite_seconds=12300 / overhead=120.
OwnedProcess calls=0 in that boundary probe. This is a discovery PASS, not a full suite PASS.

A copy of the actual repaired Shell/Policy JSON with both line numbers forced equal
still throws the original conflicting-fixture error. Existing same-selector and
mixed-tag rejection tests ran unchanged.

## Verification

Local runtimes: Windows/PowerShell; Python3.12.10; Node22.23.3; Playwright1.56.1;
pytest8.4.2; Ruff0.16.2. The assigned worktree has installed frontend dependencies and
Chromium but no .venv. The existing primary repository .venv interpreter was reused
read-only for dependency-complete unit execution; PYTHONPATH explicitly targeted this
worktree's backend and root, bytecode/cache writes disabled. No dependency install,
.env read, real provider call, database work or concurrent agent was used.

| Command / check | Actual result |
| --- | --- |
| npm run e2e:list | PASS,77 tests |
| Actual JSON discovery / unfiltered selector parser / original CLI discovery boundary | PASS,68 unique selectors; correct separate Shell/Policy routing |
| Existing project .venv Python -B -m pytest tests/test_run_e2e.py tests/test_slice_b_e2e_fixture_routing.py tests/test_slice_c_e2e_fixture_routing.py tests/test_slice_f_fixture_routing.py -q -p no:cacheprovider | 66 passed,0 skipped; one inherited StarletteDeprecationWarning |
| Global Python -B -m unittest tests.test_run_e2e -q | 43 passed; intentional failure-path output is test evidence, not a failed suite |
| Focused Ruff over the harness and four routing/unit test files, --no-cache | PASS |
| Shell actual Chromium recovery, separate offline uncertain-shell composition | 1 passed (Playwright6.3s), lifecycle timeout60s unchanged |
| Policy actual Chromium recovery, separate offline uncertain-policy composition | 1 passed (Playwright7.2s), lifecycle timeout60s unchanged |
| npm run typecheck | PASS, exit0; configured app/node program |
| check_project_state.py / check_architecture.py | PASS / PASS |
| unittest tests.test_check_secrets -q | 8 passed |
| Tracked/task-owned check_secrets.py and explicit final-file scan | PASS, supported secret patterns0 |
| git diff --check; explicit untracked Markdown/JSON hygiene; final diff/scope/manifest readback | PASS |

Browser commands used the existing main entry with `--timeout-seconds 60`,
`--sandbox-demo uncertain-shell --grep "Director recovers uncertain shell and continues
the original submission"` at backend8965/frontend4373, then corresponding uncertain-policy
at backend8966/frontend4374. Fresh owned local processes/composition per scenario;
one worker, no retries, headless Chromium, existing external-network guard.
Both run exactly the preserved journey: one Send action; retained original confirmation
and submission UUID equality after recovery; Shell1/Policy1/Amend0; external_calls0;
RM read-only and Director recovery; stale result rejection; keyboard Enter/Space;
double-activation recovery-request1; responsive320/720/1280; reload and explicit continuation.
No target mutation replay or second confirmation is introduced by recovery/continuation.
The original screenshot outputs were backed up in memory, newly generated captures
saved only to task scratch, and the original accepted bytes restored in finally.
Both task-owned loopback port pairs were verified released after execution.

Initial diagnostic attempts are not counted as PASS: global-Python combined unit run
returned62 passed/4 failed because the isolated PDF worker lacked pypdfium2 and uploads
returned DOCUMENT_STRUCTURE_INVALID. Existing dependency-complete .venv rerun above
passed all66 without source, fixture or dependency changes. A browser grep anchored at
the beginning of the title selected no tests (Playwright full titles include file/tags);
correcting only the invocation ran the two required scenarios above.

Supplementary standalone strict no-emit TypeScript invocation is NOT a PASS: it is
outside the configured E2E program and reports11 existing missing Node declaration /
ImportMeta.env diagnostics. Compiler-host in-memory comparison of the published-head
file and repaired file proved identical diagnostic sets (codes/messages/paths), without
changing dependencies. Configured typecheck and real Playwright compilation/execution pass.

## Product-source unchanged proof

All229 tracked files under apps/backend/app and apps/frontend/src match PR-head Git
blob bytes after the repository's existing CRLF normalization. No product path was
edited. All15 product-source paths in the accepted frozen bundle additionally match
its recorded raw SHA256 hashes byte-for-byte, including the accepted recovery owners.
The manifest freezes every current product raw hash for independent recheck.
Current raw product aggregate: `f58b5dd21cc63bf86970a8b7a8f91fef1dfd8081bfa658710c4142bd036d033b`.
Current normalized product aggregate: `66f17be6c36855a9c10ad327b978c1056ead9368cc49ea7b9f8700cfe8fb7230`.
Thus the intended source change is limited to the accepted E2E definition. Original
accepted screenshot bytes and historical evidence remain unchanged.

Impact relative to published PR head: API/shared types NO; schema NO; connector NO;
configuration/timeout NO; business rule NO; mapping NO; auth/security NO; architecture
owner/dependency NO; provider status NO; product runtime behavior NO. Test discovery
behavior YES. Provider labels remain Mock/Local/Sandbox Partial; no Live claim.
ArchitectureReviewRequired: NO. No new owner, fallback, adapter or compatibility path.
Complexity control: one existing test journey helper and two explicit declarations;
the dynamic declarations are replaced, with no duplicated assertion body.

## Limitations, final state and next action

Full unfiltered local E2E execution was NOT run. It requires68 serial fresh lifecycles,
including separate OCR/database fixture resources; the launcher safety budget is205min.
Complete discovery plus the two affected real HTTP/process browser scenarios supply
bounded local evidence. No full backend, physical Mongo or publication pre-PR gate was
run solely for this test-definition change.
The unchanged CI timeout comment/test assumes65 selectors; current actual inventory
is68. The computed worst-case205min suite budget plus the comment's14min installation
reserve exceeds the existing210min job bound. No timeout/workflow change is authorized
in this remediation; actual CI execution remains necessary and any further scope is
an owner decision. No new CI failure is inferred from that budget discrepancy.

The previously accepted test path changed: fresh independent review is REQUIRED on this
new manifest and exact content. Historical PASS cannot approve this remediation.
Remaining requirement: after exact independent PASS and separate owner authorization,
publish the unchanged reviewed repair, then assess fresh push AND pull_request GitHub CI
for the new head, including the full unfiltered E2E lane. No GitHub Actions rerun occurred.

Final staged diff is empty. HEAD/branch/main/worktree inventory retain task-start
identities. Only the E2E file and the two named report/manifest files form the handoff;
no commit, push, PR amendment, auto-merge, merge or next phase. Existing worktree retained
for the reviewer. Stop for independent review; this report does not perform that gate.
