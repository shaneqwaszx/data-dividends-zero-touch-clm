# Development Tooling Automation Implementation

## Result

**IMPLEMENTED WITH BOUNDED VERIFICATION GAPS.** The rebaselined developer-tooling
handoff is implemented on `dev-tooling`. Repository-owned Playwright smoke tooling,
read-only GitHub PR/check observation, guarded physical-Mongo execution, and exact
project-scoped Codex MCP policy are present and covered by focused tests. Existing CI
coverage is preserved and extended.

This result is not PR/merge approval. The local browser smoke is unavailable because
the required Playwright Chromium revision is not installed, and physical Mongo was not
run because the owner did not supply an authorized disposable/local service URI. Both
are reported as unavailable evidence, not passes. No independent quality gate, commit,
push, PR, merge, rebase, reset, stash, clean, branch switch, browser installation,
Mongo service start, MCP server contact, or Camunda activation was performed.

## Baseline and scope

- Branch: `dev-tooling`
- Authorized `BASE_SHA`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- HEAD at implementation closeout: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- Observed `origin/main`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- Ahead/behind: `0/0`
- Task-start tracked tree: clean; the supplied planner was the sole untracked input.
- Change classes: `CI_TOOLING`, `DOCS_ONLY`.
- TDD route: off, as recorded in the execution addendum.

The implementation stayed inside the handoff file map. All `apps/backend/app/**` and
`apps/frontend/src/**` product files remain unchanged. Phase 15B/15C worktrees and
sibling repositories were not inspected or modified.

## Implemented behavior

### Authenticated Playwright smoke

- Added exact-pinned development dependency `@playwright/test@1.56.1`, with a narrowly
  regenerated npm lockfile and no unrelated dependency update.
- Added Chromium-only `.e2e.ts` discovery, no Playwright `webServer`, one worker, no
  retry, and recording/storage artefacts disabled.
- Added exactly two tests: protected-workspace/login/navigation and Singapore
  `202400001A` with the existing clean synthetic document, `COMPLETED`, visible
  `GoldTier Mock`, and `MOCK_GOLDTIER_SUBMITTED` evidence.
- Added one parent runner that owns random per-run credentials, loopback ports,
  backend/Vite/Playwright processes, readiness deadlines, bounded/sanitized output,
  and process teardown. CLI and environment port overrides support concurrent
  worktrees. A headed diagnostic uses the same owner.
- Added a backend launcher that disables dotenv loading, uses test/memory mode, Mock
  ACRA and GoldTier, local deterministic IDP, registry-fed local ownership, disabled
  demo controls, explicit browser origin, and runtime-only hashes for all synthetic
  identities.
- Added an isolated Linux CI E2E job. Local browser installation remains manual; CI
  installs only Chromium and its required runner dependencies.

### GitHub PR/check observation

- Added an argument-array-only helper restricted to `gh pr view` and `gh pr checks`.
- Positive PR number, accepted GitHub PR URL, and bounded branch inputs are supported.
- Required-check absence/all-skip/failure/cancellation/pending/timeout, invalid JSON,
  unavailable data, draft/closed PR, and head-SHA movement cannot produce green.
- Reports contain stable selected fields and query-free HTTPS check links; raw stderr
  is not emitted. Optional failures remain distinct. Output explicitly disclaims merge
  approval.

### Mongo tooling

- Retired `scripts/run_phase13_physical_tests.py` in favor of one explicit-env runner
  covering the Phase 12, 13, 14, and 14.5 physical suites.
- The runner reads only `PHASE12_MONGO_URI`, disables ambient pytest options/plugins,
  contains raw output, enforces suite collection/execution, and treats no-passed or
  all-skipped execution as blocked.
- The existing generated-name/database-cleanup owner remains unchanged.
- `scripts/check_mongodb.py` now requires an explicit process `MONGO_URI`, disables
  dotenv loading, performs only `ping`, and prints no URI or collection content.

### Project-scoped Codex MCP policy

- Added `.codex/config.toml` using the official Codex schema declaration.
- `camunda_docs` is enabled but optional and prompt-approved, with only
  `search_camunda_knowledge_sources` exposed.
- `camunda_cluster` is disabled and optional, invokes owner-installed `c8 mcp-proxy`
  only through profile `fyp-camunda`, and exposes only `getClusterStatus` and
  `getTopology`, each prompt-approved.
- Added an offline exact-shape checker and wired it through CI and the existing
  pre-PR governance owner. No endpoint, credential, header, environment forwarding,
  cluster/profile creation, or product runtime dependency was introduced.
- Configuration semantics were checked against official Codex MCP/config references
  and official Camunda Docs/Orchestration MCP references before implementation.

### Documentation and CI

- Added the operator runbook with Windows Command Prompt-compatible setup/operation,
  privacy, manual/automatic/blocked boundaries, and future Camunda activation gate.
- Updated the README, tooling guide, and test plan without changing provider truth:
  ACRA and GoldTier remain Mock, IDP/ownership remain Local, Mongo remains optional,
  and Camunda product runtime remains not implemented.
- Added `tests/__init__.py`, repairing the exact current CI module invocation.
- Retired the unused root `tests/e2e/.gitkeep`; browser tests are frontend-owned.

## CI inventory before and after

| Area | Before | After |
|---|---|---|
| Jobs | `backend`, `frontend`, `phase12-mongo`, `demo-lifecycle-windows`, `security` | All five preserved; added isolated `e2e` |
| Frontend | install, inventory, typecheck, unit test, build | Preserved; added `e2e:list` |
| Physical Mongo | direct four-module pytest invocation | Same four modules through guarded runner |
| Security/governance | existing secret, pre-PR, context, project-state, architecture, contract/example checks | Preserved; added tooling-config checker |

## Verification evidence

| Check | Result |
|---|---|
| Exact context/module command: `python -m unittest tests.test_dev_context tests.test_check_project_state tests.test_check_architecture -v` | PASS — 37 tests |
| Tooling safety suites | PASS — 38 tests |
| Pre-PR checker suite | PASS — 42 tests; required elevation only for isolated temporary Git repositories |
| Focused Mongo diagnostic/safety | PASS — 16 tests |
| Full backend pytest | PASS — 981 passed, 14 expected physical/infrastructure skips, 3 existing Pydantic warnings |
| Contract discovery from `tests/contract` | PASS — 44 tests |
| `python -m mypy apps/backend/app` | PASS — 91 source files |
| Task-owned Ruff scope | PASS |
| Frontend dependency inventory | PASS — Playwright 1.56.1 / playwright-core 1.56.1 resolved; expected optional-platform packages remain optional |
| `npm run e2e:list` | PASS — exactly 2 tests in 1 file; no servers or credentials required |
| Frontend typecheck | PASS |
| Frontend unit suite | PASS — 155 tests in 7 files; `.e2e.ts` not collected |
| Frontend production build | PASS — 97 modules transformed |
| Tooling config, project state, architecture, secret scan | PASS |
| Secret-scanner adversarial suite | PASS — 8 tests |
| `git diff --check` | PASS; Windows line-ending notices only |
| Local authenticated browser execution | UNAVAILABLE — services reached readiness, but Playwright Chromium headless shell revision 1194 is not installed; no browser was downloaded |
| Independent browser teardown check | PASS — E2E exit 1, zero newly retained Python/Node processes, zero listeners on ports 8765/4173 |
| Physical Mongo execution | BLOCKED/NOT RUN — no owner-supplied `PHASE12_MONGO_URI` or authorized service; no service was started or contacted |

Two broad commands are non-green for bounded unchanged/environmental reasons:

1. `python -m ruff check apps/backend scripts tests` reports only two pre-existing,
   unchanged `RUF100` directives in
   `tests/contract/test_phase_06_zero_touch_contract.py` and
   `tests/contract/test_phase_07_uat_contract.py`. The task-owned Ruff scope passes.
   Those out-of-scope files were not modified.
2. `python -m unittest discover -s tests -p "test_*.py"` ran 188 tests but reports two
   existing root-discovery imports for `phase13_contract_credentials` and eight Windows
   demo lifecycle failures because the repository `.venv` is absent; occupied default
   demo ports were also left untouched. The canonical contract command passes 44/44,
   the exact repaired CI module command passes 37/37, and the lifecycle scripts/tests
   were not changed by this task.

`python scripts/pre_pr_check.py` was not run against this implementation tree because
it correctly requires a clean committed feature tree and commit authorization was
explicitly withheld. Its 42-test suite and every new governance checker pass.

## POC regression disposition

The canonical regression catalogue is unchanged. The full backend suite, contract
suite, frontend suite, project-state/architecture checks, and explicit browser test
definition preserve the existing Registry -> Document -> Reconciliation -> Ownership
-> Readiness -> Mock GoldTier order, call stopping, terminal outcomes, team/auth
boundaries, and truthful Mock/Local labels. No product behavior or catalogue scenario
was added, superseded, or reinterpreted. The only unexecuted direct browser path is the
local Chromium run noted above.

## Files

Created:

- `.ai-pipeline/001_planner/DEV_TOOLING_EXECUTION_ADDENDUM.md`
- `.ai-pipeline/reports/DEV_TOOLING_IMPLEMENTATION.md`
- `.codex/config.toml`
- `apps/frontend/playwright.config.ts`
- `apps/frontend/e2e/authenticated-zero-touch.e2e.ts`
- `docs/development/DEVELOPMENT_TOOLING_RUNBOOK.md`
- `scripts/check_tooling_config.py`
- `scripts/e2e_backend_server.py`
- `scripts/github_pr_ci.py`
- `scripts/run_e2e.py`
- `scripts/run_physical_mongo_tests.py`
- `tests/__init__.py`
- `tests/test_check_tooling_config.py`
- `tests/test_github_pr_ci.py`
- `tests/test_run_e2e.py`
- `tests/test_run_physical_mongo_tests.py`

Modified:

- `.github/workflows/ci.yml`, `.gitignore`, `README.md`
- `apps/backend/tests/test_mongo.py`
- `apps/frontend/package.json`, `apps/frontend/package-lock.json`
- `docs/development/TOOLING_AND_MCP.md`, `docs/test-plan/README.md`
- `scripts/check_mongodb.py`, `scripts/pre_pr_check.py`
- `tests/test_pre_pr_check.py`

Retired:

- `scripts/run_phase13_physical_tests.py` — replaced by the guarded all-suite owner.
- `tests/e2e/.gitkeep` — replaced by frontend-owned Playwright tests.

The supplied `.ai-pipeline/001_planner/DEV_TOOLING_AUTOMATION.md` remains preserved as
an untracked task input.

## Explicit change and non-change statement

- API/model/shared type: no change.
- Persistence schema/repository semantics: no change.
- External connector or provider composition: no change.
- Business rule/mapping: no change.
- Authentication/RBAC/team scope: no product change; E2E uses existing real login and
  backend-authored authorization.
- Architecture/runtime provider status: no change; no ADR required.
- Configuration: developer-only project Codex MCP configuration added; cluster entry is
  disabled and Docs access remains prompt-approved/optional.
- CI/tooling: changed as listed above.

## Decisions, risks, and owner actions

- No material sponsor ambiguity was encountered. The unresolved Ready-for-Approval,
  Live-provider, production SSO, Camunda runtime, and external account/secret boundaries
  remain unchanged.
- The primary residual validation gap is the unavailable local Chromium revision; CI
  is configured to install its pinned Chromium dependency and run the same wrapper.
- Physical Mongo evidence remains a separate owner-authorized run against a disposable
  service. Absence of that evidence is not a product regression claim.
- An independent `fyp-quality-gate` run is still required before PR readiness.
- After independent gate acceptance, an owner may authorize a scoped commit, install
  Chromium through approved CA/proxy controls for local execution if desired, supply an
  approved physical-Mongo environment for that separate check, and then run the clean
  tree pre-PR workflow. Human owners retain push, PR, and merge authority.

## Aegis impact and safety receipt

- Key judgment: developer tooling is isolated from product runtime and external
  mutation; unavailable infrastructure is reported, never converted into green.
- Avoided misfix: no test weakening, dotenv fallback, TLS bypass, shared-database read,
  general process killer, generic GitHub command passthrough, or Camunda activation.
- Boundary held: exact baseline, file map, Mock/Local provider truth, read-only GitHub,
  generated Mongo safety owner, and human integration authority.
- Baseline alignment: aligned; no product/architecture baseline change and no ADR.
- Complexity control: within budget; each new owner is narrow, and the unsafe
  phase-specific Mongo runner plus root E2E placeholder were retired.
- Evidence strength: direct focused and broad regression evidence with bounded external
  gaps; confidence **B**.
- Uncovered risk: local browser assertions and genuine Mongo execution await the
  documented owner-controlled prerequisites; independent quality gate remains pending.
- Next most valuable verification: install the pinned Chromium revision through the
  approved setup or let isolated CI execute it, then run the separate physical-Mongo
  and independent quality gates.
- Aegis path: execution addendum -> implementation -> regression checks -> verification
  closeout.

Goal closure: **done at the authorized implementation stop**, with browser/physical
execution explicitly unavailable and no claim of requirement acceptance, PR readiness,
or integration approval.

## 2026-09-19 — Playwright browser-smoke remediation

This append-only entry supersedes only the earlier local-browser availability and
execution statements. It does not alter the physical-Mongo status or issue an
independent quality gate.

### Previous and newly supplied evidence

- The implementation run originally recorded Chromium revision 1194 as unavailable.
- The owner subsequently installed Playwright Chromium and Chromium Headless Shell
  build 1194 and confirmed that discovery still found exactly two tests in one file.
- The first owner-run browser smoke then failed before login because the network guard
  blocked a request, threw after `route.abort()`, and prevented the Sign-in page from
  rendering. The second serial test did not run. Task-owned ports were released after
  that failure.

### Root cause and bounded remediation

- Static tracing and a sanitized reproduction identified an existing stylesheet's
  public HTTPS web-font import. The request was structurally
  `scheme=https;loopback=false;port=other`; it was not a frontend/backend origin,
  localhost/IPv4/IPv6 mismatch, Vite proxy error, or API-base error.
- `apps/frontend/playwright.config.ts` now owns a deterministic request classifier.
  It accepts HTTP only, exact task-owned ports only, and deliberate
  `localhost`/`127.0.0.1` equivalence. The backend port is denied for the current
  same-origin Vite-proxy journey and is permitted only when a caller explicitly marks
  direct backend browser access as required. External, LAN/private, wrong-port,
  non-HTTP, IPv6, and malformed requests fail closed.
- `apps/frontend/e2e/authenticated-zero-touch.e2e.ts` installs an E2E-only CSP before
  application scripts, preventing the remote stylesheet dependency from initiating a
  browser request. The route guard remains active for every request: an allowed request
  continues once; a disallowed request records only safe structural fields, aborts
  once, and is asserted through controlled `afterEach` failure. It no longer throws
  from the route callback after aborting.
- The CSP permits Vite's local inline React-refresh preamble but does not permit remote
  connections, styles, fonts, images, objects, or frames. No product source, Vite
  application configuration, backend behavior, provider status, or dependency changed.
- `tests/test_run_e2e.py` now exercises the owned frontend, conditional backend,
  normalized loopback form, wrong port, external HTTPS, LAN/private host, non-HTTP,
  malformed URL, single route action, sanitized violation, credential redaction, and
  recording/session-artifact policy.

### Failure-artifact policy

Playwright 1.56 creates `error-context.md` independently of screenshot, trace, video,
HAR, and storage-state settings. Its internal AI page snapshot can contain rendered
DOM/accessibility text, so a failure after login could retain KYC or workflow content.
This is classification **B**. `scripts/run_e2e.py` now supplies
`PLAYWRIGHT_NO_COPY_PROMPT=1` only to the Playwright child, suppressing that snapshot at
source. Existing `preserveOutput: "never"` and disabled screenshot/trace/video settings
remain. After the passing run, the task-owned output directory contained only
`.last-run.json`; no error context, trace, screenshot, video, HAR, or storage state was
retained.

### Fresh verification evidence

| Check | Fresh result |
|---|---|
| `npm.cmd --prefix apps\frontend run e2e:list` | PASS — exactly 2 tests in 1 file |
| `.venv\Scripts\python.exe scripts\run_e2e.py --backend-port 8865 --frontend-port 4273` | PASS — 2/2 ran and passed in 4.4 seconds; real login/navigation and Singapore synthetic Mock completion observed |
| Post-run `netstat` for `:8865` and `:4273` | PASS — no listeners/output for either assigned port |
| `.venv\Scripts\python.exe -m unittest tests.test_run_e2e -v` | PASS — 15 tests |
| Four focused tooling modules | PASS — 42 tests |
| `npm.cmd --prefix apps\frontend test` | PASS — 155 tests in 7 files |
| Frontend typecheck | PASS |
| Frontend production build | PASS — 97 modules transformed |
| `python scripts/check_secrets.py` | PASS |
| `python scripts/check_tooling_config.py` | PASS |
| `git diff --check` | PASS — Windows line-ending notices only |

The successful journey asserted the existing `Completed Mock workflow`, visible
`GoldTier Mock`, non-production wording, and `MOCK_GOLDTIER_SUBMITTED` outcome. No
unexpected external browser request succeeded.

Remediation files changed:

- `apps/frontend/e2e/authenticated-zero-touch.e2e.ts`
- `apps/frontend/playwright.config.ts`
- `scripts/run_e2e.py`
- `tests/test_run_e2e.py`
- `.ai-pipeline/reports/DEV_TOOLING_IMPLEMENTATION.md` (this append-only evidence)

The development runbook did not require correction. Branch `dev-tooling`, `BASE_SHA`,
current `HEAD`, and `origin/main` were all
`a81e7da1c677f063408952e2ae1a1a2478afc22b` at closeout. Existing task-owned
implementation changes remain unstaged; no commit, push, PR, merge, reset, rebase,
stash, or clean action was performed.

Physical Mongo remains **BLOCKED/NOT RUN** because no owner-supplied disposable
`PHASE12_MONGO_URI` or separate authorization was provided. Independent quality gate
review remains the next required action.

Remediation status: **BROWSER REMEDIATION VERIFIED — INDEPENDENT QG PENDING**.

## 2026-09-19 — Remediation after independent Development Tooling QG FAIL

This append-only section supersedes the preceding browser-acceptance and GitHub
observation-identity statements where they conflict. It records remediation evidence,
not an independent quality-gate verdict. The independent quality gate remains immutable
and its verdict was **FAIL**.

### DTA-QG-001 — deterministic no-egress font handling

The independent real-Chromium run proved that the earlier script-injected CSP was not
a sufficient owner of the existing `design-system.css` Google Fonts dependency: the
browser still requested the stylesheet, the fail-closed route guard aborted it, the
first test failed, and the second serial test did not execute. Chromium availability
was not the cause.

The CSP injection has been removed. The canonical request classifier now assigns every
request exactly one of `OWNED_LOOPBACK`, `KNOWN_NEUTRALIZED_FONT_STYLESHEET`,
`BLOCKED_EXTERNAL`, or `BLOCKED_INVALID`. Only the exact HTTPS
`fonts.googleapis.com/css2` stylesheet request, including the baseline family query and
stylesheet resource type, is locally fulfilled with a bounded empty `text/css`
response. It is not sent to the network and is not recorded as a violation. Owned
loopback traffic continues once; every other non-loopback or invalid request—including
path/query/resource-type variants and `fonts.gstatic.com`—is aborted once, recorded
only with safe structural fields, and asserted as a deterministic failure in teardown.
Product CSS and application source remain unchanged.

Fresh discovery reported exactly two tests in one file. With ports `8865` and `4273`
confirmed free, the real runner completed **2/2 PASSED in 3.6 seconds**. The first test
proved the protected workspace through real local login and authenticated navigation.
The second completed the Singapore synthetic-UEN journey and asserted `COMPLETED`,
truthful visible `GoldTier Mock`/non-production labeling, and
`MOCK_GOLDTIER_SUBMITTED`. No unexpected external request succeeded. Immediately after
the run, both assigned ports had no listener, no worktree-owned Python/Node/Chromium
child remained, and the configured output contained only `.last-run.json`; no trace,
video, screenshot, HAR, storage state, error context, or persistent profile was
retained.

### DTA-QG-002 — bound GitHub observation identity

The failed implementation trusted `gh` resolution and returned PR metadata too
loosely. The gate demonstrated that a request for PR 17 could receive a valid-looking
PR 18 response, accept green checks, exit zero, and preserve unsafe PR-URL query data.

The reporter now constructs one expected identity before observation. Numeric, branch,
and current-branch targets derive `OWNER/REPO` only from the fixed read-only
`git remote get-url origin` command; current-branch targeting additionally uses only
`git branch --show-current`. Explicit PR URLs strictly define repository and positive
PR number. Both local commands use argument arrays, `shell=False`, bounded timeouts,
and sanitized failures. Supported remotes are restricted to the required GitHub HTTPS
and SSH forms, with malformed hosts, credentials, query/fragment data, and unexpected
path shapes rejected.

Every `gh pr view` and `gh pr checks` command now carries explicit `--repo OWNER/REPO`.
Both PR views validate untrusted number, canonical HTTPS GitHub URL, repository,
applicable branch, SHA, state, review decision, merge state, base branch, and draft
boolean. Checks are queried for that exact validated PR and repository between the two
views; the second identity is revalidated before head comparison and result
calculation. Any repository, target, PR, branch, field, or head mismatch is
deterministic non-success even when all checks are green. Query and fragment data are
excluded from canonical output, child stderr remains suppressed, and GitHub Enterprise
host override variables are not passed to these exact `github.com` observations.

The GitHub suite now has **24/24 passing adversarial tests**, including wrong PR,
wrong repository, branch/current-branch mismatch, malformed or credential-bearing
URLs, canonical query/fragment stripping, malformed JSON fields, second-view identity
change, head change, all-green checks with mismatched identity, sanitized stderr/local
Git failure, strict command allowlisting, explicit repository binding, and supported
remote normalization.

### Physical Mongo, lifecycle, and regression evidence

`PHASE12_MONGO_URI` was absent. No `.env` was read, no Mongo/Docker service was started,
and no physical suite ran. Physical acceptance therefore remains **PENDING** and is the
remaining evidence blocker before an independent re-QG can return PASS.

Default lifecycle ports were free, no runtime manifest or other worktree-owned runtime
was present, and the one authorized complete serialized Windows lifecycle execution
finished **18/18 PASS in 274.464 seconds**. Afterward the default ports were free and
the runtime manifest was absent. The lifecycle implementation and tests were not
changed.

Fresh remediation regression results:

| Check | Result |
|---|---|
| `tests.test_run_e2e` | PASS — 16/16 |
| `tests.test_github_pr_ci` | PASS — 24/24 |
| Four focused tooling modules | PASS — 57/57 |
| Real Chromium smoke | PASS — 2/2 in 3.6 seconds |
| Frontend unit tests | PASS — 155/155 in 7 files |
| Frontend typecheck | PASS |
| Frontend production build | PASS — 97 modules transformed |
| Backend pytest | PASS — 934 passed, 14 skipped |
| Backend mypy | PASS — 91 source files |
| Canonical contract discovery | PASS — 44/44 |
| Context/project-state/architecture unit suites | PASS — 37/37 |
| Pre-PR checker unit suite | PASS — 42/42 |
| Serialized Windows lifecycle suite | PASS — 18/18 in 274.464 seconds |
| Task-owned Ruff scope | PASS |
| Tooling, project-state, architecture, and secret checkers | PASS |

The repository-wide Ruff command continues to report only the two explicitly accepted,
unchanged contract `RUF100` baseline findings in
`tests/contract/test_phase_06_zero_touch_contract.py` and
`tests/contract/test_phase_07_uat_contract.py`; neither file was edited. The governance
and pre-PR unit suites initially encountered sandbox-only Windows temporary-directory
permission errors, then passed unchanged with normal temporary-Git permissions. This
was an execution-environment retry, not a code or test weakening.

Remediation files changed:

- `apps/frontend/e2e/authenticated-zero-touch.e2e.ts`
- `apps/frontend/playwright.config.ts`
- `scripts/github_pr_ci.py`
- `tests/test_run_e2e.py`
- `tests/test_github_pr_ci.py`
- `.ai-pipeline/001_planner/DEV_TOOLING_EXECUTION_ADDENDUM.md`
- `docs/development/DEVELOPMENT_TOOLING_RUNBOOK.md`
- `.ai-pipeline/reports/DEV_TOOLING_IMPLEMENTATION.md` (this append-only section)

This remediation made no API/model/shared-type, persistence/schema,
connector/provider, product configuration, business-rule/mapping,
authentication/RBAC, runtime architecture, MCP, CI, dependency, or provider-status
change. Branch `dev-tooling`, `BASE_SHA`,
current `HEAD`, and `origin/main` remained
`a81e7da1c677f063408952e2ae1a1a2478afc22b`. All task-owned implementation changes
remain unstaged; no commit, push, PR, merge, rebase, reset, stash, clean, or branch
switch was performed. The next owner action is to supply and authorize a disposable
physical Mongo environment, run the guarded physical suite, and then commission a new
independent quality gate.

Remediation status: **REMEDIATION VERIFIED — PHYSICAL MONGO PENDING — RE-QG NOT YET READY**.

## 2026-09-19 — Physical Mongo runner remediation

The owner supplied an explicitly authorized disposable Mongo 7 service on loopback.
The original runner invocation reproduced the supplied false-negative result exactly:

```text
PHYSICAL_MONGO_RESULT=BLOCKED; REASON=NO_EXECUTED_TESTS; PASSED=0; FAILED=0; ERRORS=0; SKIPPED=0
```

### Root cause and repair

This was summary-parser input failure, not unavailable Mongo, missing URI propagation,
wrong interpreter, wrong paths, import failure, or zero collection. The backend pytest
configuration already contributes `-q`; the runner added a second `-q`. With pytest
8.4.2, the effective `-qq` returned success after executing the tests but suppressed
the terminal count summary. A sanitized command comparison confirmed that the extra
quiet flag produced no summary token while the configured single quiet level did.
The runner therefore parsed a successful execution as all-zero counts.

`scripts/run_physical_mongo_tests.py` now supplies `-o addopts=` before its own fixed
pytest options, so ambient/project `addopts` cannot duplicate or redirect the command
and exactly one quiet level is used. The count parser examines only the final timed
pytest summary line, in memory, and never renders captured child output. It reports
distinct sanitized outcomes for collection failure, execution failure, true zero
collection, all-skipped execution, and unavailable/inconsistent summaries. A proposed
JUnit-file implementation was rejected and removed because failure XML could transiently
retain traceback or connection material; the final implementation creates no result
artifact.

`tests/test_run_physical_mongo_tests.py` now exercises the actual worktree pytest 8.4.2
command/output for all-pass, mixed pass/skip, test failure, collection error, and true
zero collection. It also retains and expands mocked boundary tests for URI absence and
redaction, the exact four owned suites, fixed command options, narrow environment,
missing/unowned suites, all-skipped/no-pass behavior, child/cleanup failure containment,
and the absence of arbitrary database or cleanup-sweep ownership.

### Safe execution contract retained

- The child still runs through `sys.executable` from the repository root with explicit
  backend/repository `PYTHONPATH` and third-party plugin autoload disabled.
- The URI is read only from the current process `PHASE12_MONGO_URI`, forwarded only to
  the narrow child environment, never accepted on the CLI, printed, or copied to a
  result artifact. `.env` remains unused.
- Selection remains exactly the Phase 12, 13, 14, and 14.5 physical modules. Missing or
  uncollected ownership fails closed.
- The runner contains no database name, database enumeration, drop, or cleanup sweep.
  The unchanged `scripts/mongo_test_safety.py` owner continues to generate only
  allowlisted disposable names and performs verified cleanup. `clm_poc` remains outside
  the execution and cleanup boundary.
- Child stdout/stderr remains contained. Only bounded counts, reason, exit code, and
  suite count can cross the runner output boundary.

### Physical and regression evidence

The final owner-authorized physical rerun selected all four intended modules and
returned:

```text
PHYSICAL_MONGO_RESULT=PASSED; SUITES=4; COLLECTED=14; PASSED=14; FAILED=0; ERRORS=0; SKIPPED=0
```

All 14 tests executed against generated allowlisted databases. Their existing finalizers
completed the unchanged drop-and-verify cleanup; a cleanup failure would have surfaced
as a pytest error/non-success. The runner output and report contain no URI value or raw
driver/service failure text.

| Check | Fresh result |
|---|---|
| Focused physical-runner unit suite | PASS — 16/16 |
| Four focused tooling modules | PASS — 66/66 |
| Real physical Mongo runner | PASS — 4 suites, 14 collected, 14 passed, 0 failed/errors/skipped |
| Task-owned Ruff scope | PASS |
| Tooling-config checker | PASS |
| Project-state checker | PASS |
| Architecture checker | PASS |
| Secret scanner | PASS |
| `git diff --check` | PASS — Windows line-ending notices only |

Browser and Windows lifecycle suites were not rerun because this slice changed only the
physical runner, its focused tests, and this append-only report; their latest
remediation evidence remains 2/2 and 18/18 respectively. The independent quality-gate
report was not modified.

Branch `dev-tooling`, `BASE_SHA`, current `HEAD`, and local `origin/main` remain
`a81e7da1c677f063408952e2ae1a1a2478afc22b`. The existing Development Tooling
implementation and this remediation remain unstaged. No commit, push, PR, merge,
rebase, reset, stash, clean, or branch switch was performed.

No API/model/type, persistence schema/repository semantics, product connector,
configuration, business rule/mapping, authentication/RBAC, architecture, dependency,
CI, MCP, or provider-status change was made. The next action is a new independent
Development Tooling re-QG.

Remediation status: **REMEDIATION VERIFIED — PHYSICAL MONGO COMPLETE — READY FOR INDEPENDENT RE-QG**.

## 2026-09-19 — Minor remediation after PASS WITH MINOR FIXES

The independent Development Tooling re-quality gate returned **PASS WITH MINOR
FIXES** and identified one required low-risk retirement correction:
`bootstrap_folders.ps1` still declared `tests\e2e` in both `$dirs` and `$keepDirs`.
Running the tracked bootstrap would therefore recreate the retired root directory and
its `.gitkeep`, despite browser E2E ownership having moved to `apps/frontend/e2e`.

The finding was reproduced before editing in a unique isolated directory under the
repository-owned ignored `.runtime` area. The unmodified bootstrap produced both
`tests\e2e` and `tests\e2e\.gitkeep`. The validation target was resolved and checked to
be inside `.runtime` before its task-owned contents were removed.

The only executable change removes:

- `tests\e2e` from the `$dirs` array; and
- `tests\e2e` from the `$keepDirs` array.

No replacement or compatibility path was added. A post-change execution in a new
isolated validation directory produced all **18/18** remaining declared folders and
all **6/6** remaining `.gitkeep` files. It produced neither `tests\e2e` nor
`tests\e2e\.gitkeep`. The repository's
`apps/frontend/e2e/authenticated-zero-touch.e2e.ts` remained present as the canonical
browser E2E source. A non-document repository search found no remaining executable or
configuration reference to the retired root path. The focused diff contains only the
two stale declaration removals; no unrelated path was deleted or renamed.

Fresh verification:

| Check | Result |
|---|---|
| Isolated bootstrap before fix | Reproduced `tests\e2e` and `.gitkeep` recreation |
| Isolated bootstrap after fix | PASS — 18/18 folders, 6/6 keep files; retired path absent |
| Canonical frontend E2E path | PASS — directory and authenticated Playwright spec present |
| Four focused tooling modules | PASS — 66/66 |
| Executable/config stale-reference search | PASS — no matches |
| Tooling-config checker | PASS |
| Project-state checker | PASS |
| Architecture checker | PASS |
| Secret scanner | PASS |
| `git diff --check` | PASS — Windows line-ending notices only |

There is no separate repository bootstrap test suite; the isolated pre/post execution
is the direct behavioral check. Physical Mongo, Chromium, and the complete Windows
lifecycle were not rerun because this minor change does not touch their owners. Their
latest independent evidence remains 14/14, 2/2, and 18/18 respectively.

Files changed by this minor remediation:

- `bootstrap_folders.ps1`
- `.ai-pipeline/reports/DEV_TOOLING_IMPLEMENTATION.md` (this append-only section)

Branch `dev-tooling`, `BASE_SHA`, current `HEAD`, and local `origin/main` remain
`a81e7da1c677f063408952e2ae1a1a2478afc22b`. The implementation remains unstaged. No
commit, push, PR, merge, rebase, reset, stash, clean, or branch switch was performed.
The independent re-quality-gate report was not modified.

No product source, browser behavior, GitHub reporter, Mongo tooling, MCP configuration,
CI, dependency, API/model/type, schema/repository semantic, connector/provider,
business-rule/mapping, authentication/RBAC, architecture, or provider-status change was
made. The next action is a focused independent re-check of this two-entry retirement
fix.

Minor remediation status: **MINOR REMEDIATION VERIFIED — FOCUSED INDEPENDENT RE-CHECK REQUIRED**.
