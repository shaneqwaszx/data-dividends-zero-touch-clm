# PR77 E2E discovery remediation - independent Quality Gate

Date: 2026-10-08 (Asia/Singapore). Final verdict: **FAIL**.
The bounded test-definition repair is correct and independently verified. One P2
CI-budget containment defect remains and blocks publication readiness.

## 1. Reviewer independence and boundary

This is a fresh independent review-only run. This reviewer did not implement the
remediation or author its evidence. No subagents were used. Applied
`fyp-quality-gate` and `ci-failure-triage`; classified the assigned delta as
CI_TOOLING with DOCS_ONLY supporting evidence and loaded their task-scoped context.

The sole durable authored repository file is this report. No product, test, harness,
workflow, configuration, prior report, manifest or frozen screenshot was edited.
Execution used temporary scratch and process-local observation hooks; browser screenshots
were captured to buffers without overwriting accepted images. No dotenv access,
external provider request, physical database operation, staging, commit, push,
PR amendment, Actions rerun, merge or next phase occurred.

## 2. Current PR/main/head state

- Candidate worktree: `C:/Users/shane/.codex-clean2/worktrees/goldtier-reliability-recovery/data-dividends-zero-touch-clm`.
- Branch: `codex/goldtier-submission-reliability-recovery-ux`.
- HEAD and current published PR head: `6fc74b99fb6d2f98caf02eb32418b2e28afe3e1c`.
- BASE_SHA, merge-base, local origin/main, PR base and remotely inspected current main:
  `5c54c9af896585764d1e4ed809056d1deb576629`.
- [PR #77](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/77)
  remains open, non-draft and unmerged. Head/base/main were refreshed at approximately
  07:23 SGT on 2026-10-08 through read-only GitHub CLI queries.
- Remediation remains uncommitted. Staged diff is empty at entry and final inspection.
- Initial/final pre-report status is precisely the three candidate paths in section 6.
  The final status additionally includes only this untracked report.

Worktree inventory: the primary checkout on `codex/measured-master-evidence` at
5c54c9a; the assigned candidate at 6fc74b9; and the separate
`camunda-sync-maintenance` checkout at 55ddde5. No worktree/branch mutation was made.

Current inspected, independently tested and reviewed content is published HEAD plus
the exact single-test-path delta, bound by the identities below. Historical independent
acceptance is context, not approval for changed content.

## 3. One-path remediation identity

Independently recomputed:

`59fe071b689d3f44d4b65540d6ae24f70d3639874418661268dcae77b32c07c6`.

The changed path is `apps/frontend/e2e/s3-sandbox-submission.e2e.ts`.
Its raw SHA256 is
`e67e5de5daeaf5d35329a7770ff1259f228a3a53d5cb4c8b020a2a8dcf5556db`;
normalized SHA256 is
`dcaad5b9739e3cd22093a3d45e8cb731ed45a464c860e6ff5f7ffa3d90e8a554`.
Raw byte length: 29032.

## 4. Cumulative source/test identity

All 25 current source/test/planner/product-document paths and every normalized
per-path hash match the remediation manifest. Independently recomputed identity:

`39fe886a782c98504c1ab24056702e80f828ec079c6a46ef511f6d0c26aed33c`.

Historical accepted source identity:
`ffd55df6bacc51691dfc00b8d7d6e01860338e41863077ef61b87b28bdc2f5e7`.
The prior final independent GoldTier/onboarding gate was read for accepted behavior
and limitations; its PASS does not approve this new test content.

## 5. Frozen remediation bundle identity

Independently recomputed and rechecked after execution:

`2588cafa6f1b168d8440ba66f81382d759e88c3cb8981066abcf9676c53ed00a`.

Algorithm: sorted UTF-8 repository-relative path + NUL + bytes normalized from
CRLF to LF + NUL, accumulated in SHA256. The bounded bundle contains the repaired
test and implementer report. Every raw hash, normalized hash and byte length matches.
The manifest excludes itself to avoid circular hashing; its separately observed raw
SHA256 is `af2bbd622673bf88763e76abdfb56341f4545d35b2935f0eadd56b6f5eacc9d1`
and remained unchanged. This independent report is outside that frozen bundle.

Historical accepted evidence identity:
`962d1e04b7d55d90bad50003d9b964dcb4e0214f237f655192659486eb424582`.

## 6. Exact changed paths

Candidate delta relative to published HEAD:

1. `apps/frontend/e2e/s3-sandbox-submission.e2e.ts` - modified;
2. `.ai-pipeline/reports/PR77_E2E_DISCOVERY_REMEDIATION.md` - untracked;
3. `.ai-pipeline/reports/PR77_E2E_DISCOVERY_REMEDIATION_MANIFEST.json` - untracked.

Complete tracked diff: one file, 108 added and 102 removed lines, reflecting helper
extraction and two explicit declarations. Complete diff and task-owned new evidence
were inspected. No additional candidate path or staged content was found.
The review adds only `.ai-pipeline/reports/PR77_E2E_DISCOVERY_REMEDIATION_QUALITY_GATE.md`.

## 7. Original CI failure reproduction

Read the authoritative logs for push run 37661429136/job 112929655459 and PR run
37661455938/job 112929750002. Both failed the exact command
`python scripts/run_e2e.py --timeout-seconds 60`, exit 1, with:

`E2E FAILED: Playwright test discovery returned conflicting fixture modes`.

Independently executed actual installed Playwright JSON discovery on the published
test structure without replacing the file on disk: a process-local ESM loader supplied
the byte-equivalent published recovery block, preserving the remaining file.
The original `_list_test_selectors` and CLI main entry remained the owners.

Actual listing: 77 tests and 67 distinct raw file/line locations; both recovery tests
reported line 222 with different Shell/Policy fixture tags. Original CLI main returned
1 with the exact conflict; observation spies proved OwnedProcess constructors = 0
and lifecycle dispatches = 0. Backend, frontend and browser lifecycle startup did
not occur. Diagnostic hook setup failures were corrected before this successful
reproduction and are not counted as evidence of the original failure.

## 8. Root-cause assessment

The dynamic loop generated two logical tests from one `test(...)` declaration.
Their shared file:line selector required both `uncertain-shell` and
`uncertain-policy` compositions. A lifecycle selector cannot safely own two
incompatible fixture modes. The harness correctly rejected the ambiguity during
discovery. This is a test-definition/discovery defect, not evidence of a product failure.

The configured frontend listing step can enumerate both tests successfully without
applying the Python harness's fixture-ownership conflict check; its success does not
contradict the E2E lane failure.

## 9. Helper/body equivalence

Compared UTF-8 published Git blob bytes with the current file after CRLF normalization.
All 100 original journey lines are identical after structural dedentation, including
every assertion, route interception, conditional, call, keyboard action, viewport
loop, screenshot capture, reload, timeout option and continuation.

Dedented body with its final newline SHA256:
`aeb0897f7ef5358fe6c2f33ec0fdcd049431de9f228b75246546e0f71b7a0129`.

File prefix and suffix outside the replaced block are identical. The helper signature
is `runDirectorRecovery(page: Page, operation: "shell" | "policy")`; explicit tests
call it with the corresponding literal operation. Exact titles/tags are preserved.
No assertion was removed or weakened; no timeout, fixture semantics, production code,
backend code, workflow or configuration changed. An initial comparison using the
Windows default text decoding was rerun with explicit UTF-8 and passed.

## 10. Selectors before/after

| Exact existing title | Before | After | Exact source tag / fixture |
| --- | --- | --- | --- |
| Director recovers uncertain shell and continues the original submission | e2e/s3-sandbox-submission.e2e.ts:222 | e2e/s3-sandbox-submission.e2e.ts:324 | @s3-sandbox-uncertain-shell / uncertain-shell |
| Director recovers uncertain policy and continues the original submission | e2e/s3-sandbox-submission.e2e.ts:222 | e2e/s3-sandbox-submission.e2e.ts:328 | @s3-sandbox-uncertain-policy / uncertain-policy |

The logical test inventory remains 77. Splitting the collision increases distinct raw
locations from the invalid published 67 to 68 safe selectors; it adds no logical journey.
Playwright's JSON tags omit the leading at-sign; source declarations and browser
output retain the exact existing at-sign tags.

## 11. Harness fail-closed assessment

`scripts/run_e2e.py` is unchanged from published HEAD. The parser records complete
fixture-mode identity per exact selector and throws when a second occurrence differs.
It also rejects unknown and mixed Sandbox, recovery and target fixture tags.

Independently copied the actual repaired discovery payload and forced both recovery
lines to the same selector. The unchanged parser raised RuntimeError with
`Playwright test discovery returned conflicting fixture modes`.
Unknown/mixed-fixture and isolated-composition protections passed the unchanged
routing/unit tests. The repair does not bypass or loosen the guard.

## 12. Actual discovery result

Executed the actual repository-configured Playwright JSON command through
`_list_test_selectors(4173, ...)`, not merely a handcrafted payload:

- 77 actual tests; 68 unique lifecycle selectors;
- each repaired selector occurs once and owns exactly its corresponding Sandbox mode;
- fixture-selector counts: Garden 8, registry 5, recovery 4, Sandbox 12;
- parser completes successfully with no fixture-mode conflict.

Executed the original unfiltered CLI main entry through discovery and deterministic
port allocation. An observation-only sentinel stopped at its first real lifecycle
dispatch, `e2e/authenticated-zero-touch.e2e.ts:229`, with timeout 60 seconds.
It reported selectors 68, suite_seconds 12300 and overhead 120. No lifecycle result was
fabricated. This proves discovery/dispatch readiness, not full-suite execution.

## 13. Harness/routing tests

Independent dependency-complete execution:

```text
python -B -m pytest tests/test_run_e2e.py
  tests/test_slice_b_e2e_fixture_routing.py
  tests/test_slice_c_e2e_fixture_routing.py
  tests/test_slice_f_fixture_routing.py -q -p no:cacheprovider
```

Result: **66 passed, zero skipped**, in 8.57 seconds. One existing
Starlette/httpx TestClient deprecation warning. Tests and expectations were unchanged.
The existing primary repository's .venv Python was reused read-only; PYTHONPATH targeted
the assigned worktree, Settings dotenv loading was disabled before application imports,
and bytecode/pytest cache writes were disabled.

The CI containment unit passes its literal 65-count arithmetic; this does not establish
containment for actual discovery of 68. That defect is assessed separately in section 18.

## 14. Shell browser result

Exact existing launcher entry with `--timeout-seconds 60`,
`--sandbox-demo uncertain-shell`, the exact title grep, backend 8967/frontend 4375:
**1 passed**, Playwright 5.8 seconds, complete lifecycle 9.719 seconds.
Ports were available before execution and released afterward.

Real backend, Vite, HTTP requests and headless Chromium executed the unchanged journey.
One worker, zero retries, existing external-network guard, explicit offline Sandbox
composition, no external provider calls. Output was directed to disposable scratch.

## 15. Policy browser result and preserved assertions

Corresponding `--sandbox-demo uncertain-policy`, exact title grep,
backend 8968/frontend 4376: **1 passed**, Playwright 6.3 seconds, complete lifecycle
10.000 seconds. Ports released afterward.

Both scenarios execute and preserve: one confirmation/send action; equality of the
retained submission UUID and original confirmation after continuation; Shell 1,
Policy 1, Amend 0 and external_calls 0; RM diagnosis with no Resolve action; Director
recovery; rejection of a stale status result and suppression of its stale values;
one recovery request after double activation; keyboard Enter/Space; 320/720/1280
reflow checks; recovery and continuation reloads; explicit Complete safe recovery;
and focused/in-viewport completion.

The process-local Page.screenshot wrapper removed only the file destination and
performed the normal screenshot capture into a buffer. It changed no browser action,
response, assertion or timing. Both accepted retained-Shell/Policy screenshot files
remained byte-identical. No target mutation replay or second confirmation was introduced.

## 16. Product-source identity proof and impact

All 229 tracked paths under `apps/backend/app` and `apps/frontend/src` match
published HEAD Git blob bytes after repository CRLF normalization. Every current
manifest product raw/normalized hash and byte length matches. All 15 accepted raw
product-source/test hashes also match the original historical accepted manifest.

Raw product aggregate:
`f58b5dd21cc63bf86970a8b7a8f91fef1dfd8081bfa658710c4142bd036d033b`.

Normalized product aggregate:
`66f17be6c36855a9c10ad327b978c1056ead9368cc49ea7b9f8700cfe8fb7230`.

| Surface changed by this remediation | Result |
| --- | --- |
| API/shared types | NO |
| Schema/index/CAS/persistence | NO |
| Connector | NO |
| Configuration/provider timeout | NO |
| Business rule | NO |
| Mapping | NO |
| Auth/security | NO |
| Architecture owner/dependency | NO |
| Provider classification | NO |
| Product runtime behavior | NO |
| Test discovery behavior | YES |

Mock/Local/Sandbox Partial labels and sponsor limitations remain unchanged. No Live,
KYC approval, final approval or production-readiness claim follows.

## 17. Typecheck/static/hygiene

| Independent check | Result |
| --- | --- |
| Configured `npm.cmd run typecheck` (`tsc -b --pretty false`) | Exit 0 |
| Ruff `--no-cache`, harness and four assigned test files | All checks passed |
| `python -B scripts/check_architecture.py` | PASS |
| `python -B scripts/check_project_state.py` | PASS |
| Secret-scanner regression tests | 8 passed |
| Existing secret patterns over three explicit candidate paths | Zero supported findings |
| `git diff --check` using repository line-ending settings | Exit 0 |
| Explicit implementer Markdown/manifest JSON whitespace, final newline, BOM and JSON readback | PASS |
| Final manifest/source/product hash and Git scope recheck | Exact matches |

Scanner regressions used disposable scratch with fixture directory and scanner root
relocated together in memory; no test source or expectation changed. Initial sandbox
permission failures and an incomplete scratch-root relocation were corrected and are
not represented as passing runs. Sandbox-restricted Git/network operations were
repeated through approved read-only execution.

Supplementary standalone strict E2E TypeScript program: published and current files
each produce **11 identical diagnostics**, compared by code/message/file rather than
moved source line. Codes: 2307 once, 2339 twice, 2580 eight times; missing Node
declarations and ImportMeta.env context remain pre-existing. This command is outside
the configured app/node program and is not a PASS or the repository-authoritative
typecheck. Configured typecheck and actual Playwright compilation/execution pass.

Session runtimes: Windows/PowerShell, Python 3.12.10, Node 22.23.3, pinned installed
Playwright 1.56.1, pytest 8.4.2, Ruff 0.16.2. No dependencies were installed.

## 18. CI 65-vs-68 budget assessment

**Classification: P2 BLOCKER - current CI outer timeout does not contain the stated
worst-case lifecycle and setup contract.** This conclusion is based on executable
governance, current workflow and documented contract intent, not arithmetic alone.

A. The expectation is executable. In
`tests/test_run_e2e.py:906`,
`test_ci_outer_bound_covers_current_discovery_and_bounded_cleanup` asserts the
210-minute workflow timeout and computes containment with hard-coded 65. It does
not obtain current discovery count. The workflow comment at lines 97-98 also uses 65.

B. `.github/workflows/ci.yml:99` enforces `timeout-minutes: 210` on the whole E2E
job, including setup before the launcher. GitHub documents this as automatic job
cancellation at the outer limit. Its cancellation escalation can kill the process
tree before the launcher's complete reserved cleanup has finished; Python's own
cleanup handling is not a guarantee against forced termination.
See [workflow timeout syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idtimeout-minutes)
and [cancellation reference](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-cancellation).

C. Containment is intended. The current unit explicitly tests the outer bound against
discovery, execution, bounded cleanup and setup reserve. The owning deadline/runbook
documents define a bound derived from maximum allowed execution plus bounded cleanup,
rather than observed average speed, and require outer-budget reassessment as discovery
grows. Their old inventory numbers are historical; their owner/boundary principle is
corroborated by the current executable test and workflow.

D. Actual historical runtime is fast, but does not waive the worst-case contract.
Authoritative successful main push run 37489367441/job 112357724063 executed 65
selectors in 813.753 seconds; slowest lifecycle 37.228 seconds. That is historical
65-selector evidence, not a fresh 68-selector PASS or a bound on setup/cleanup.

Current declared calculation:

```text
68-selector launcher allowance = 60 + 68 * (60 + 120) = 12300 seconds = 205 minutes
stated setup reserve          = 14 * 60             =   840 seconds
required combined allowance   =                       13140 seconds = 219 minutes
GitHub job allowance          =                       12600 seconds = 210 minutes
containment shortfall         =                         540 seconds = 9 minutes
```

Independently used actual discovered selectors in a no-sleep clock simulation of the
unchanged runner: all 68 successful declared-bound lifecycles return suite success at
12300 seconds. With the stated setup reserve, GitHub's outer allowance leaves only
11760 seconds for that launcher, the declared end of lifecycle 65, leaving three
lifecycles/540 seconds uncontained. This is a deterministic contract reproduction,
not an actual nine-minute CI failure or a full local-suite PASS. No current budget
timeout has been observed on PR #77, which failed earlier during discovery.

E. The repair adds no logical tests. Published structure had 77 tests/67 raw locations
and an invalid conflict; splitting its two existing logical recovery cases produces
68 valid selectors, an increase of one distinct lifecycle location. Main's last
successful 65-selector inventory already predates additional PR #77 tests. The repair
exposes correct isolation rather than introducing new product behavior.

F. Correction requires a separately authorized CI_TOOLING remediation outside this
one-test repair: reconcile the outer job budget with the actual discovered count,
retained execution/cleanup bounds and setup allowance; make the executable containment
check validate the actual inventory rather than a stale literal; refresh directly
related budget documentation. With the existing 14-minute reserve, the current formula
requires at least 219 minutes before any additional margin. Do not simply weaken the
conflict guard, shorten recovery assertions or suppress tests. No workflow/harness/test
fix was made by this reviewer. Changed reviewed content requires fresh independent review.

## 19. Current GitHub CI state

Authoritative read-only GitHub job/log inspection; all listed jobs have completed:

| Event / run | E2E | Backend | Frontend | Security | Local OCR | Phase12 Mongo | Windows lifecycle |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [push / 37661429136](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/actions/runs/37661429136) | failure, discovery | success | success | success | success | success | success |
| [pull_request / 37661455938](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/actions/runs/37661455938) | failure, discovery | success | success | success | success | success | success |

Both runs identify PR head 6fc74b99fb6d2f98caf02eb32418b2e28afe3e1c.
Push checkout is that branch head; PR checkout is merge-preview
`d7f91a4766aab1fc6e34a9d8f71f47cf2315b8cc`, whose logged parents are head 6fc74b9
and base 5c54c9a. CI uses Ubuntu, Python 3.12, Node 22, npm ci and installed Chromium.
The first causal failures are the section 7 discovery errors, before product/browser
assertions. These completed runs test published content, not the uncommitted repair.
No job remains reported as still running and no Actions run was rerun.

## 20. Unexecuted evidence

Full unfiltered local 68-selector E2E execution: **NOT RUN**.
Fresh GitHub CI for this remediation: **NOT RUN**; the repair is uncommitted.

Complete actual discovery, both affected real browser lifecycles, unchanged
fixture-routing safety tests and mechanical product-source identity supply the required
bounded test-repair evidence. They do not fabricate full-suite acceptance.
Full unfiltered execution must occur in fresh CI after independently accepted,
separately authorized publication; the P2 must be resolved before that readiness claim.

No fresh full backend/frontend suite, frontend build, physical Mongo or pre-PR
publication gate was run solely for this test-definition delta. These are not reported
as passing. Integration/pre-PR is intentionally deferred for this uncommitted review-only
handoff. Earlier broad acceptance retains its own source/evidence identity.

## 21. Findings by severity

**P2 - Reconcile outer E2E budget with actual discovery before publication.**
Locations: `.github/workflows/ci.yml:97` and `:99`;
`tests/test_run_e2e.py:906` through its containment assertion;
`scripts/run_e2e.py:730` through its derived budget.

The executable safety check still certifies 65 lifecycles while actual discovery
requires 68. The enforced job limit can terminate a run permitted by the declared
execution/cleanup/setup budget before its own required completion/cleanup allowance.
Fast historical runtimes do not fulfill that explicit containment requirement.
A separate CI-budget remediation and independent recheck are required.

No P0/P1, product-source, recovery-assertion, identity, fixture-guard or security defect
was found in this repair. The standalone 11 diagnostics and corrected reviewer
environment/setup failures are not newly introduced product findings. Budget comments
belong to this same P2 and are not counted as a separate P3.

## 22. Final verdict and next authorized action

**FAIL** for publication readiness of the exact frozen remediation candidate:
one P2 CI-budget containment defect remains. The discovery repair itself meets its
identity, scope, equivalence, fail-closed, actual discovery, focused-unit, browser,
configured-typecheck and hygiene requirements.

The candidate is not ready for a publication update to PR #77 until the owner/planner
assigns the separate CI-budget remediation, the changed candidate receives fresh
independent review, and any publication is separately authorized. No source changed
during this review. Only this report was added; staging remains empty.
Stop for owner/planner review. No remediation, commit, push, PR update, Actions rerun,
merge or next phase is authorized or performed by this gate.
