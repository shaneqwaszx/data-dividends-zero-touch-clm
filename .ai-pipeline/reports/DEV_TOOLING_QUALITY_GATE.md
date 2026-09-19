# Development Tooling Automation — Independent Quality and Security Gate

## 1. Executive Result

**FAIL.** The implementation is not acceptable for publication in its present state.
The independent gate found two task-owned defects that can create false or unusable
evidence, and one mandatory evidence gap:

1. The real authenticated Playwright run starts Chromium and the owned local services,
   but the first test fails because the fail-closed browser policy observes and blocks
   the application's Google Fonts request. The second serial test does not run, so no
   executed browser evidence proves the synthetic Singapore onboarding journey or
   `MOCK_GOLDTIER_SUBMITTED`.
2. The GitHub reporter can return success for a different PR than the requested numeric
   target and copies unvalidated PR-view fields, including the PR URL query, into its
   supposedly safe report. A mocked adversarial observation reproduced both conditions.
3. No owner-approved disposable Mongo service or `PHASE12_MONGO_URI` was available.
   Physical verification was therefore not run: **acceptance blocked by missing
   evidence**.

The static design, offline safety suites, canonical governance tests, backend regression,
frontend unit/build checks, contract checks, and cleanup after the failing browser run are
otherwise strong. They do not override the failed acceptance evidence above. This gate is
review-only and contains no remediation.

### Review identity and scope

- Repository root: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-dev-tooling`
- Branch: `dev-tooling`
- `HEAD`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- Implementation `BASE_SHA`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- `origin/main`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- Change classes: `CI_TOOLING`, `DOCS_ONLY`, with security-sensitive process,
  credential-containment, Mongo, GitHub-observation, and MCP configuration boundaries.
- Product source delta under `apps/backend/app/**` and `apps/frontend/src/**`: none.
- Staged paths: none.

The reviewed code/config/test identity is a deterministic SHA-256 over 23 sorted records
of `repository-relative path<TAB>file SHA-256`, using `DELETED` for the two intentional
deletions:

`29160bd3272160328d3b5f8712d73a4797eab8564944959115015e14e47ebbcf`

The set comprises `.codex/config.toml`, `.github/workflows/ci.yml`, `.gitignore`, the two
frontend package manifests, Playwright config and E2E test, the Mongo diagnostic test,
the eight changed/new tooling scripts, `tests/__init__.py`, the five affected tooling
test modules, and the deleted `scripts/run_phase13_physical_tests.py` and
`tests/e2e/.gitkeep`. The same digest was obtained before report creation and after all
executed checks. Plans, reports, runbook and ordinary ignored runtime/build outputs are
outside this source-freeze digest. No source/config/test change was observed during the
gate.

## 2. Phase Acceptance Checklist

| Planner requirement | Result | Direct code and executed evidence |
|---|---|---|
| Repair exact CI governance module loading | **PASS** | `tests/__init__.py`; exact `.venv` module command passed 37/37. |
| Safe authenticated two-test Playwright smoke | **FAIL** | Exactly two tests list, Chromium launches, but the real run fails on blocked Google Fonts traffic; second serial test does not execute. |
| One owned process tree, distinct strict loopback ports, bounded timeouts, deterministic cleanup | **PASS for design and failed-run cleanup; success cleanup not executed** | Static review of `scripts/run_e2e.py`; 15 E2E unit tests inside the tooling suite; actual failed run left zero listeners on `127.0.0.1:18765` and `127.0.0.1:14173`. |
| Credential/config containment for E2E | **PASS** | Allowlisted child environment, `sys.executable`, disabled dotenv before backend import, memory/Mock/Local modes, demo controls off, ephemeral password only in child environment, and disabled traces/video/screenshots/HAR/storage state. |
| Deterministic read-only GitHub PR/CI reporter | **FAIL** | Mocked target `17` accepted a PR-view response for `18`, returned `0`, and retained a synthetic URL query marker. |
| Required/optional CI outcome handling and head-movement detection | **PASS within the observed PR** | Tooling tests cover empty, skipped, pending, failed, optional failure, unavailable data and head movement; reporter uses `gh pr view` and `gh pr checks` only. Cross-target/repository identity remains defective. |
| Safe Mongo diagnostic and consolidated four-suite physical runner | **PASS offline; physical acceptance unavailable** | Diagnostic/runner focused checks passed 15/15; static inspection confirms explicit environment-only URI, ping-only diagnostic and four intended physical modules. No database was contacted. |
| Optional prompt-approved Docs MCP and disabled read-only cluster MCP | **PASS as static client configuration only** | Offline checker passes; exact allowlists and types inspected. No MCP was invoked, authenticated or activated. |
| CI and pre-PR propagation | **PASS for configuration, not runtime CI evidence** | Workflow replaces the old physical command, adds E2E and checker steps, preserves existing jobs; pre-PR unit suite passed 42/42. No GitHub workflow was run. |
| Operator runbook and truthful Mock/Local status | **PASS** | Runbook distinguishes local tooling, disabled cluster access and external owner actions; no Live ACRA, GoldTier, OCR, SSO or Camunda runtime claim was introduced. |
| Independent browser, physical Mongo and lifecycle evidence sufficient for acceptance | **FAIL** | Browser acceptance failed; physical Mongo was not authorized/run; the 18-test lifecycle suite had one non-reproducible failure, although its exact test passed on isolated rerun. |

## 3. Contract and Integration Findings

### High — DTA-QG-001: the real browser smoke is incompatible with existing frontend traffic

`apps/frontend/src/design-system.css:4` imports fonts from
`https://fonts.googleapis.com`. The new route guard in
`apps/frontend/playwright.config.ts:65-113` allows only the owned HTTP loopback origins,
records every other request as a violation, and aborts it. The E2E suite installs that
guard at `apps/frontend/e2e/authenticated-zero-touch.e2e.ts:62-77` and asserts no
violations after every test at lines 104-106.

On explicit free ports, the real runner reached both service readiness checks and started
the pinned Chromium browser. The first test then failed with sanitized blocked external
request evidence; its sign-in assertion did not complete, and the second serial test did
not run. This is an introduced task-harness compatibility defect, not missing browser
infrastructure. The existing external font import is unchanged baseline code, but the new
acceptance harness must be compatible with the application while still rejecting
unexpected egress.

Consequence: the test definition cannot be accepted as proof of real login, the SG clean
fixture journey, truthful Mock labels, or `MOCK_GOLDTIER_SUBMITTED`.

### High — DTA-QG-002: GitHub observation is not bound to the requested PR/repository

`scripts/github_pr_ci.py:131-145` checks only that the response contains a positive PR
number and a syntactically valid head SHA. It does not verify that a numeric target's
returned number matches the requested number, and the report contains no independently
validated repository identity. `scripts/github_pr_ci.py:213-224` copies PR-view strings
and the URL directly into the output; unlike check links, the PR URL is not parsed,
restricted to HTTPS, or stripped of query and fragment data.

A mocked `gh` sequence requested PR `17`, returned a valid-looking PR `18` with passing
required checks, and supplied a URL containing a synthetic query marker. The reporter
returned exit `0`, reported PR `18`, and preserved the query marker. No real GitHub
account or network mutation was used.

Consequence: a caller can receive a green report for an observation different from its
requested target, and deterministic sanitized output is not guaranteed. This is a
false-success/evidence-integrity defect. The reporter still correctly avoids claiming
human approval and treats its output as advisory.

### Missing mandatory evidence — DTA-QG-003: physical Mongo execution unavailable

`PHASE12_MONGO_URI` and `MONGO_URI` were absent, and no explicit owner authorization for
a disposable service was supplied. In accordance with the project constitution, the
review did not connect to, inspect, provision, enumerate, or clean any database.

Static and unit evidence is positive: `mongo_test_safety.py` is unchanged; the runner
reads only `PHASE12_MONGO_URI`, launches all four intended physical modules through the
worktree interpreter, passes a narrow child environment, rejects no-pass/all-skipped
outcomes, and contains child output. The diagnostic uses `_env_file=None` and performs
only `ping_mongodb`. This does not substitute for an executed physical run.

### Compatibility and baseline classification

- The canonical contract command from `apps/backend` passed 44/44. A root-CWD `pytest
  tests/contract` attempt produced the two known `phase13_contract_credentials` import
  errors; this is an invocation/path problem, not an introduced contract regression.
- Broad Ruff reports only two unchanged `RUF100` findings in
  `tests/contract/test_phase_06_zero_touch_contract.py:9` and
  `tests/contract/test_phase_07_uat_contract.py:12`. `git diff BASE_SHA --` for both is
  empty; task-owned Ruff is green.
- Root unittest discovery was non-green with the two same import errors and lifecycle
  failures while the default demo ports were occupied. A later serialized `.venv`
  lifecycle run on free ports executed 18 tests with one failure at
  `tests/test_demo_lifecycle_windows.py:686`; the exact failed test then passed in
  isolation in 37.363 seconds. The lifecycle test and `scripts/demo.ps1` are unchanged
  from `BASE_SHA`. This is non-reproducible baseline/environment evidence, not a task
  source regression, but the full lifecycle suite must not be called green.

No sponsor contract, API/model/type, durable schema, connector behavior, business rule,
mapping, product authorization, architecture owner, or provider status changed.

## 4. Tester and Adversarial Findings

### Environment

| Component | Observed version |
|---|---|
| Python, repository `.venv` | 3.12.10 |
| Node.js | 22.23.2 |
| npm | 10.9.8 |
| Camunda `c8` CLI | 4.1.0 |
| `@playwright/test`, `playwright`, `playwright-core` | exactly 1.56.1 |

All Python acceptance reruns below used
`C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-dev-tooling\.venv\Scripts\python.exe`.
Frontend commands used this worktree's existing `apps/frontend/node_modules`. No package
or browser installation occurred.

### Executed matrix

| Working directory / command | Result |
|---|---|
| root: `.venv\Scripts\python.exe -m unittest tests.test_dev_context tests.test_check_project_state tests.test_check_architecture -v` | **PASS — 37/37** after rerun with normal Windows temporary-Git permissions; the sandbox-only attempt was invalidated. |
| root: `.venv\Scripts\python.exe -m unittest tests.test_check_tooling_config tests.test_github_pr_ci tests.test_run_e2e tests.test_run_physical_mongo_tests -v` | **PASS — 42/42**. |
| root: `.venv\Scripts\python.exe -m unittest tests.test_pre_pr_check -v` | **PASS — 42/42**. |
| root: `.venv\Scripts\python.exe -m pytest apps\backend\tests\test_mongo.py tests\test_run_physical_mongo_tests.py -q -p no:cacheprovider` | **PASS — 15/15**, two dependency deprecation warnings. |
| root: `.venv\Scripts\python.exe -m pytest apps\backend\tests -p no:cacheprovider` | **PASS — 934 passed, 14 expected physical/infrastructure skips, 5 warnings, 86.98 s**. |
| `apps/backend`: `..\..\.venv\Scripts\python.exe -m unittest discover -s ..\..\tests\contract -p "test_*.py"` | **PASS — 44/44**. |
| root: `.venv\Scripts\python.exe -m mypy apps\backend\app` | **PASS — 91 source files**. |
| root: task-owned `.venv\Scripts\python.exe -m ruff check ...` scope | **PASS**. |
| root: broad `.venv\Scripts\python.exe -m ruff check apps\backend scripts tests` | **NON-GREEN BASELINE — two unchanged `RUF100` findings**. |
| `apps/frontend`: `npm run typecheck` | **PASS**. |
| `apps/frontend`: `npm test` | **PASS — 155 tests in 7 files**; `.e2e.ts` was not collected by Vitest. |
| `apps/frontend`: `npm run build` | **PASS — 97 modules transformed**. |
| `apps/frontend`: `npm run e2e:list` | **PASS — exactly 2 tests in 1 file**. |
| root: `.venv\Scripts\python.exe scripts\run_e2e.py --backend-port 18765 --frontend-port 14173` | **FAIL — Chromium executed; first test failed on blocked external browser traffic; second serial test did not run**. |
| root: port/process check after the failed E2E run | **PASS — zero listeners on 18765/14173 and no retained task-owned Python/Node process found**. |
| root: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_demo_lifecycle_windows.py" -v` | **NON-GREEN — 17 passed, 1 failed** at final endpoint-stop assertion; ports were free afterward. |
| root: exact failed lifecycle test by full unittest identifier | **PASS — 1/1 in 37.363 s**. |
| root: direct project-state, architecture, tooling-config and tracked secret checks | **PASS**. |
| root: secret-scanner adversarial unit suite | **PASS — 8/8**. |
| root: `git diff --check` | **PASS**, with Windows line-ending notices only. |
| root: physical runner | **NOT RUN — no owner-approved disposable Mongo service**. |
| GitHub Actions | **NOT RUN — configured workflow evidence only**. |
| root: `scripts/pre_pr_check.py` production entry point | **NOT RUN by design — current tree is intentionally uncommitted/dirty**. |

The implementation report's earlier browser-unavailable result is superseded: Chromium
is now installed and launched successfully. Its failure is functional evidence, not an
installation gap.

### Process and output safety disposition

- Static inspection confirms one Python launcher owns both process trees; Vite uses
  `--strictPort`; occupied/duplicate/non-loopback ports fail closed; server reuse is
  absent; readiness and test deadlines are bounded and monotonic.
- The launcher does not enumerate or kill arbitrary port owners and does not use
  name-based process killing. Windows and POSIX termination paths are explicit.
- The child environment excludes Mongo, GitHub and Camunda variables; backend setup
  clears inherited configuration, disables dotenv before importing the app, forces
  memory persistence, Mock ACRA/GoldTier, Local IDP/ownership, disabled demos, and the
  exact trusted frontend origin.
- The per-run password is not placed in CLI arguments or Vite variables. Browser
  traces, video, screenshots, HAR and storage state are disabled. The observed failure
  output contained only sanitized request structure; no credential/session material was
  emitted.
- Actual cleanup evidence exists for browser/test failure. Successful-browser cleanup is
  not available because no browser test succeeded. Readiness failure,
  interruption and timeout cleanup are covered by mocked unit tests, not independent
  live process executions in this gate.

## 5. Code and Architecture Review

### Strengths

- The E2E and physical runners use `sys.executable`, keeping subprocesses on the
  worktree-local interpreter.
- `tests/__init__.py` repairs the exact CI module import without product behavior change.
- The physical CI step is replaced by the consolidated runner; it is not bypassed or
  duplicated. The Linux E2E job installs only its pinned browser dependency before
  calling the same repository launcher.
- The Playwright dependency and lockfile delta is limited to the planner-authorized,
  exact `@playwright/test==1.56.1` graph. `npm ls` resolves Playwright and
  `playwright-core` to the same version. No other application dependency update was
  introduced.
- The GitHub subprocess layer uses argument arrays, `shell=False`, a narrow environment,
  validated target syntax, bounded per-process/total monotonic deadlines, two head reads,
  and explicit required-versus-optional outcomes.
- The MCP checker enforces the exact intended TOML shape, value types, prompt approval,
  tool allowlists, disabled cluster state, and absence of environment/header/secret
  forwarding fields.
- No parallel persistence, authorization, ownership, mapping, provider or state owner was
  introduced. No product runtime component depends on the new developer tooling.

### Maintainability and accepted debt

- The new scripts are narrow and testable, and retirement of the stale physical runner
  is explicit. There is no retained compatibility fallback requiring a second owner.
- Current official Codex configuration documentation recognizes project
  `.codex/config.toml`, MCP enablement, tool allowlists and tool approval-mode keys:
  <https://learn.chatgpt.com/docs/config-file/config-reference>.
- Camunda's official Docs MCP page documents the configured public endpoint and single
  `search_camunda_knowledge_sources` tool, including its authentication/rate-limit
  boundary: <https://docs.camunda.io/docs/8.8/reference/mcp-docs/>. Current cluster MCP
  documentation lists `getClusterStatus` and `getTopology` but notes that discoverable
  signatures may evolve: <https://docs.camunda.io/docs/apis-tools/orchestration-cluster-api-mcp/orchestration-cluster-api-mcp-tools/>.
- These references validate only configuration intent. `enabled_tools` is client-side
  exposure control; it does not prove server authorization, client loading, runtime
  connectivity or universal server-side protection.

Complexity closure is acceptable for the intended tooling architecture, but acceptance
is blocked by DTA-QG-001 and DTA-QG-002 rather than by structural complexity.

## 6. Security Review

### High

- **DTA-QG-002 — target/evidence binding and output sanitization:** a false-green report
  for a different PR is possible, and a PR URL query can cross the sanitized output
  boundary. Repository, target PR and observed head must be treated as one validated
  identity before an outcome can be green.

### Acceptance/security blocker

- **DTA-QG-001 — fail-closed browser policy currently makes the required smoke
  unusable:** the policy correctly denies unowned egress, but the served application
  attempts such egress. Weakening the policy silently would not meet the requirement;
  the harness/application asset behavior must be reconciled while preserving fail-closed
  rejection and deterministic evidence.

### Positive containment evidence

- No `.env`, protected private artefact, browser profile, credential, sibling worktree,
  database contents or live GitHub/MCP account was accessed.
- No raw URI, password/hash, bearer material, browser session material or private
  provider payload appeared in captured output or this report.
- Mongo names remain governed by the unchanged allowlist in
  `scripts/mongo_test_safety.py`; the new runner cannot take an arbitrary URI/database on
  its CLI and has no enumeration/drop sweep.
- MCP cluster access is disabled and prompt-approved configuration does not contain an
  endpoint credential, header, environment forwarding or hidden approval override.
- The browser runner's isolated process cleanup was observed after a real failed run.

Production IAM, browser credential management, external MCP authentication, GitHub
branch protection, repository secrets, live provider access and Mongo operational
governance remain explicitly deferred owner capabilities. None is claimed by this phase.

## 7. Required Fixes

1. **DTA-QG-001:** make the real authenticated smoke pass without permitting unexpected
   external browser traffic. Preserve the fail-closed route policy and demonstrate both
   tests: real local login, one clean Singapore onboarding, truthful Mock labels and
   terminal `MOCK_GOLDTIER_SUBMITTED`. Then capture actual success-path cleanup.
2. **DTA-QG-002:** bind every GitHub observation to the requested repository, PR and
   head SHA; reject mismatches before checking/reporting success. Validate and sanitize
   all PR-view output fields, including removing URL query/fragment data. Add adversarial
   tests for wrong PR/repository identity and unsafe PR-view fields.
3. Obtain explicit owner authorization and an allowlisted disposable Mongo service, then
   run `scripts/run_physical_mongo_tests.py` from this worktree and record selected tests,
   pass/skip counts and cleanup without exposing the URI or raw service errors.
4. Rerun the serialized Windows lifecycle suite on free ports and obtain one full green
   run. If the final endpoint-stop failure recurs, diagnose it in a separately authorized
   remediation rather than treating the isolated pass as suite-wide proof.

The two unchanged Ruff findings and the root-CWD contract import behavior are baseline or
invocation issues, not fixes assigned to this tooling implementation. The formal
clean-tree `scripts/pre_pr_check.py` run remains a publication-time prerequisite after an
owner-authorized commit; it is not a reason to commit during remediation or review.

## 8. Readiness

- Development Tooling Automation acceptance: **not ready**.
- Ready for remediation: **yes**, limited to the findings above in a separate authorized
  run.
- Ready for commit/push/PR/merge: **no**.
- Configured GitHub CI status: **unknown; not executed**.
- Actual browser status: **failed**, not missing infrastructure.
- Physical Mongo status: **acceptance blocked by missing evidence**.
- Live ACRA verification: **not performed and not enabled; Mock remains default**.
- Real GoldTier/PingFed integration: **not ready; GoldTier remains Mock only**.
- Camunda product integration: **not implemented**; optional developer MCP configuration
  does not change product status.

This verdict does not authorize remediation, another phase, external account setup,
database access, commit, push, PR creation, workflow execution, or merge.

## 9. Git Status

At report time, branch `dev-tooling` remains at
`a81e7da1c677f063408952e2ae1a1a2478afc22b`, matching both `BASE_SHA` and
`origin/main`. The implementation remains uncommitted. The index is empty. Expected
tracked modifications/deletions and task-owned untracked files remain present; this file
is the only reviewer-created path.

No implementation, test, config or ordinary documentation fix was made. No dependency
or browser was installed. No file was staged. No commit, push, PR, merge, branch switch,
reset, rebase, stash, clean, workflow rerun/cancel, Mongo connection, or MCP
activation/login occurred.

### Verification confidence receipt

- Evidence action: direct static review, adversarial mocked GitHub observation, real
  Chromium execution, focused and broad local regression checks, and post-run cleanup
  inspection.
- Result: `FAIL` with two High task findings and one mandatory physical-evidence gap.
- Covered scope: task-owned code/config/tests, affected CI/pre-PR consumers, existing
  application/browser interaction, offline Mongo safety, static MCP configuration and
  relevant POC regression.
- Uncovered scope: physical Mongo behavior, successful browser cleanup, actual Linux
  GitHub Actions execution, live GitHub/MCP connectivity, and a repeat full-green Windows
  lifecycle suite.
- Residual risk: false-green GitHub evidence, no end-to-end browser proof, no physical
  persistence proof, and one non-reproducible lifecycle failure.
- Confidence grade: **B** — direct target and broad regression evidence are strong, but
  acceptance-critical physical/success-path evidence is absent by design or failure.
