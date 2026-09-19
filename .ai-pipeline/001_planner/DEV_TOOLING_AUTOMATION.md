# Development Tooling Automation — Rebaselined Planner Handoff

## Goal

Complete the approved developer-tooling work without changing product workflow,
domain, API, persistence semantics, frontend behavior, or provider composition. The
bounded outcome is:

1. a deterministic Mock-only browser smoke path;
2. read-only GitHub PR/CI inspection and bounded waiting;
3. repaired Mongo diagnostics and physical-test orchestration that cannot target a
   shared database;
4. repository-scoped Codex/MCP configuration for Camunda documentation;
5. an inert, disabled Camunda cluster MCP definition with no credentials and no
   activation authority; and
6. a manual operator runbook plus CI/pre-PR validation of the tooling boundary.

This is a tooling phase, not a product-feature phase.

## Architecture

All new behavior remains outside application runtime composition:

```text
developer / CI
  -> repository tooling scripts
     -> existing test runners and local Mock application processes
     -> read-only GitHub CLI queries
     -> guarded physical Mongo test suite

trusted Codex project
  -> .codex/config.toml
     -> Camunda Docs MCP (enabled, optional, prompt-approved)
     -> Camunda cluster MCP proxy (disabled, optional, read-only allowlist)
```

The browser harness may start the existing backend and frontend as local child
processes, but it must not add application routes, test-only runtime switches, product
composition, a Camunda adapter, or external-provider calls. Mongo tooling may exercise
the existing persistence adapters only through the current generated-database safety
owner. GitHub tooling is observation-only and has no push, PR-create/update, merge,
rerun, cancel, approval, or repository-settings operation.

## Tech stack

- Python 3.12 repository scripts and `unittest`/`pytest` tests.
- Node.js 22, npm, Vite, and exact-pinned `@playwright/test` for Chromium E2E.
- GitHub CLI `gh`; local discovery observed version `2.101.0`.
- Existing PyMongo/Mongo 7 physical-test path.
- Codex trusted-project `.codex/config.toml` MCP configuration.
- Camunda Docs Streamable HTTP MCP and the locally installed `c8`/`c8ctl` CLI;
  local discovery observed `c8ctl v4.1.0` and verified
  `c8 mcp-proxy --profile <profile>` semantics.

## Baseline and authority references

- `AGENTS.md`
- `docs/PROJECT_STATE.md`
- `docs/ARCHITECTURE.md`
- `docs/DEVELOPMENT_WORKFLOW.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/decisions/DECISION_LOG.md`, especially D-039
- `docs/sponsor-questions/OPEN_QUESTIONS.md`
- `docs/development/BRANCH_MERGE_PROTOCOL.md`
- `docs/development/TOOLING_AND_MCP.md`
- `.agents/skills/integration-safe-development/SKILL.md`
- current CI, scripts, manifests, tests, and the historical
  `chore/dev-tooling-automation` branch as supporting evidence only
- official Codex project configuration and MCP documentation:
  `https://learn.chatgpt.com/docs/config-file/config-basic` and
  `https://learn.chatgpt.com/docs/extend/mcp?surface=cli`
- official Camunda Docs MCP documentation:
  `https://docs.camunda.io/docs/next/reference/mcp-docs/`
- official Camunda Orchestration Cluster MCP setup documentation:
  `https://docs.camunda.io/docs/next/apis-tools/orchestration-cluster-api-mcp/orchestration-cluster-api-mcp-setup/`

### Baseline record

- Branch: `dev-tooling`
- Authorized `BASE_SHA`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- HEAD at planning: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- `origin/main` at planning: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- Ahead/behind: `0/0`
- Tracked working tree at entry: clean
- `python scripts/dev_context.py`: passed and reported the same baseline
- `python scripts/pre_pr_check.py`: passed with zero unsafe conditions and zero
  warnings on the clean no-delta branch
- The CI command
  `python -m unittest tests.test_dev_context tests.test_check_project_state tests.test_check_architecture -v`
  currently fails because root `tests/__init__.py` is absent. This is an observed
  current-main CI defect, not a historical inference.

### Baseline usage draft

- Required refs: repository constitution, current state, architecture, development
  workflow, decision/open-question context, integration procedure, current owning
  source/tests, official Codex/Camunda configuration semantics.
- Acknowledged before planning: all required refs above.
- Cited in this plan: all required refs above.
- Missing refs: none for tooling implementation.
- Decision: continue.

## Compatibility boundary

- Preserve every accepted application API, model, schema, business rule, provider
  classification, authentication/RBAC rule, frontend/cache behavior, and Mock POC
  scenario.
- Preserve `memory` as the normal local/unit-test default and existing explicit Mongo
  mode. No unit test may begin requiring physical Mongo.
- Preserve current `scripts/pre_pr_check.py` read-only behavior and human final merge.
- Preserve current CI jobs; add narrowly scoped checks/jobs without replacing coverage.
- Do not modify Phase 15B/15C worktrees or product files they may touch.
- Do not add a Camunda runtime dependency, adapter, BPMN deployment, worker, cluster
  mutation, or Live-provider claim.
- Do not write to `%USERPROFILE%\.codex`, user GitHub configuration, c8 profiles,
  Docker settings, or any other machine-global configuration.

## TDD route

- Mode: off
- Decision: skipped
- Strict authority: not applicable
- Strict signals: none; this is tooling/configuration work with proportional tests.
- Light eligibility: not used as a TDD mode.
- TDD-fit exception: no strict RED/GREEN cycle was requested.
- Test posture: minimum implementation plus focused post-change regression,
  adversarial safety tests, broad affected checks, physical evidence where relevant,
  and an independent quality gate.
- Reason: the user requested a planner handoff, not strict test-first execution.
- Verification: exact commands are specified below.

## Change classification

Primary class: `CI_TOOLING`.

Supporting class: `DOCS_ONLY` for the runbook and tooling guidance edits.

`FRONTEND_UI` does not apply because no rendering or user-facing product behavior may
change. `PERSISTENCE` does not apply because the Mongo work changes only test/diagnostic
orchestration, not schema, repository semantics, CAS, indexes, startup, read/write, or
recovery behavior. `EXTERNAL_PROVIDER` does not apply to product composition; the MCP
entries are developer-tool integrations only. Because CI tooling touches external
accounts, secrets, subprocesses, and physical Mongo safety, the implementation still
requires the CI-tooling security review and physical evidence called for by the
workflow matrix.

## Requirement ready check

- Requirement source: attached Development Tooling Planner brief.
- Goals/scope: explicit and bounded to developer tooling.
- User/scenarios: local developer, CI runner, repository owner, and future authorized
  Camunda administrator.
- Acceptance criteria: supplied in the brief and made executable below.
- Open blocker questions: none for the safe implementation slices. GitHub login,
  local browser installation, physical Mongo availability, Camunda Docs sign-in, and
  Camunda cluster access remain manual/external prerequisites, not implementation
  blockers.
- Decision: ready.

## Change necessity and existence checks

### Change necessity

- User-visible need: reproducible developer/CI validation and safe external-tool
  inspection without product changes.
- No-change option: insufficient. Playwright and repository MCP config are absent;
  GitHub inspection/wait automation is absent; the current physical Mongo runner
  inspects a shared configured database; the Mongo diagnostic reads `FYP.users`; and
  one prescribed CI unittest invocation is currently broken.
- Minimum boundary: repository scripts/tests/config/docs plus frontend test dependency
  metadata and CI wiring.
- Decision: code-change, restricted to tooling and tests.

### Existence checks

- Reuse `scripts/pre_pr_check.py`; do not add a second branch-readiness owner.
- Reuse `scripts/mongo_test_safety.py` and existing physical tests; do not add a second
  database-name or cleanup owner.
- Reuse `.github/workflows/ci.yml`; do not create a parallel CI system.
- Reuse application Mock providers, existing synthetic fixture, and current auth
  bootstrap implementation through a test-only launcher; do not add a product test
  route or stable committed password/hash.
- Add one GitHub read-only reporter because no existing owner provides structured,
  bounded PR/check observation.
- Add one tooling-config checker because no current checker validates MCP safety.
- Add Playwright as the single browser E2E framework; do not add Selenium/Cypress or a
  second browser harness.
- Verdict: reuse existing owners where present; add only the proven missing surfaces.

## Rebaselined inventory and disposition

| Intended item | Classification | Current evidence | Planned disposition |
|---|---|---|---|
| Existing backend/frontend/security/Mongo/Windows CI jobs | **ALREADY PRESENT** | `.github/workflows/ci.yml` | Preserve; add only E2E and tooling-config coverage and route the Mongo job through the repaired runner. |
| Branch/pre-PR validation | **ALREADY PRESENT** | `scripts/pre_pr_check.py`, `tests/test_pre_pr_check.py`, branch protocol, PR template | Reuse as canonical owner. Extend only to invoke the new tooling-config checker. |
| CI governance unittest invocation | **NEEDS REPAIR** | Current `tests.*` module command fails on main | Add the root package marker and prove the exact current CI command. |
| Playwright dependency/config | **SAFE TO IMPLEMENT NOW** | Absent on main; only `tests/e2e/.gitkeep` exists | Add exact-pinned Playwright, config, launcher, and focused authenticated Mock smoke. |
| Browser binaries on a developer machine | **MANUAL SETUP ONLY** | Browser assets are not repository content | Document trusted-CA setup and Chromium installation; never disable TLS validation. |
| Browser E2E against Live ACRA/GoldTier | **BLOCKED** | Providers remain Mock/Partial/Dormant | Explicitly prohibited; no plan task. |
| GitHub PR/check inspection and bounded wait | **SAFE TO IMPLEMENT NOW** | `gh 2.101.0` supports JSON PR/check output and pending exit code 8 | Add read-only deterministic reporter with timeout. |
| PR creation/update, push, rerun/cancel, approval, or merge automation | **MANUAL SETUP ONLY** for push/PR create and **BLOCKED** for automated merge/bypass | Human-owner boundary in constitution/workflow | Do not expose these operations in the helper. Human final squash/merge remains mandatory. |
| GitHub authentication/account/repository settings | **MANUAL SETUP ONLY** | External account state; no credential authority | Document `gh auth login`/status checks; never accept or print a token. |
| Generated Mongo database allowlist and cleanup | **ALREADY PRESENT** | `scripts/mongo_test_safety.py` and focused tests | Reuse unchanged as the sole owner. |
| Current phase-specific physical Mongo runner | **NEEDS REPAIR** | Reads ambient `Settings`, can load local `.env`, inspects configured shared DB/count, and omits later physical suites | Replace with an explicit-env, all-suite, no-shared-read runner. |
| Current `FYP.users` Mongo diagnostic | **NEEDS REPAIR** | Reads an arbitrary collection unrelated to CLM persistence | Reduce to an explicit-env, connectivity-only ping with sanitized output. |
| Normal unit tests without Mongo | **ALREADY PRESENT** | Ordinary test environment forces memory mode | Preserve; no physical service dependency. |
| Local Mongo service installation/start | **MANUAL SETUP ONLY** | Machine-global service/Docker owner action | Document prerequisites only. |
| Repository-scoped Codex MCP config | **SAFE TO IMPLEMENT NOW** | Official Codex supports trusted-project `.codex/config.toml`; main has none | Add a tracked, secret-free config and validate it. |
| Camunda Docs MCP | **SAFE TO IMPLEMENT NOW** plus **MANUAL SETUP ONLY** first-use sign-in | Official public endpoint is documented; per-user GitHub/Google authentication and rate limits apply | Enable as optional and prompt-approved; document sign-in and confidentiality constraints. |
| Disabled `fyp-camunda` cluster bridge | **SAFE TO IMPLEMENT NOW** only as inert config | Installed `c8 v4.1.0` and official docs support `mcp-proxy --profile`; actual project cluster/auth values are absent | Track a disabled optional entry using only the profile name and a read-only tool allowlist. |
| Camunda cluster profile creation, MCP enablement, and authentication | **BLOCKED** now; later **MANUAL SETUP ONLY** after authority | Cluster URL/version/state, API-client scope, and credentials are not available/authorized | Do not create the profile or enable the server. Record the exact future owner gate. |
| Camunda runtime/application integration | **BLOCKED** | Architecture says Camunda is not implemented | No implementation task. Requires a separate phase and ADR. |
| Delivery governance and human final merge | **ALREADY PRESENT** | Constitution, workflow, integration skill, branch protocol, PR template | Do not rewrite governance. Add a concise operator runbook that points to the existing owners. |
| Global Codex/c8/npm/GitHub/Docker configuration | **MANUAL SETUP ONLY** | User/machine-owned | Never modify automatically. |

## Exact file map

### Create

- `.codex/config.toml` — trusted-project, secret-free MCP configuration.
- `apps/frontend/playwright.config.ts` — Chromium-only, `.e2e.ts`-only config with
  explicit base URL, trace-on-first-retry, screenshots/videos only on failure, and no
  server reuse.
- `apps/frontend/e2e/authenticated-zero-touch.e2e.ts` — two focused smoke tests:
  authentication/protected navigation and a Singapore Mock zero-touch completion.
- `scripts/e2e_backend_server.py` — test-only backend launcher that reads an ephemeral
  password supplied by the parent runner, derives runtime-only hashes, forces memory
  persistence and Mock/Local providers, disables `.env` loading, and starts one explicit
  loopback port.
- `scripts/run_e2e.py` — cross-platform owner of the ephemeral credential, explicit
  ports, availability checks, Playwright invocation, bounded timeout, and safe child
  teardown.
- `scripts/github_pr_ci.py` — read-only PR/check status and bounded CI-wait reporter.
- `scripts/check_tooling_config.py` — fail-closed MCP/tooling configuration checker.
- `scripts/run_physical_mongo_tests.py` — replacement physical Mongo suite runner.
- `tests/test_run_e2e.py` — launcher safety/process-boundary tests.
- `tests/test_github_pr_ci.py` — command allowlist, sorting, exit-code, timeout, and
  redaction tests.
- `tests/test_check_tooling_config.py` — TOML safety and disabled-cluster tests.
- `tests/test_run_physical_mongo_tests.py` — explicit-env, suite selection, and no
  shared-database-read tests.
- `tests/__init__.py` — package marker required by the current CI module invocation.
- `docs/development/DEVELOPMENT_TOOLING_RUNBOOK.md` — manual setup and operating
  commands.

### Modify

- `.gitignore` — ignore Playwright `test-results/`, `playwright-report/`, and blob
  output without ignoring E2E sources/config.
- `apps/frontend/package.json` — add exact-pinned `@playwright/test` and `e2e`,
  `e2e:list`, and `e2e:headed` scripts; no runtime dependency.
- `apps/frontend/package-lock.json` — regenerate only from the manifest change.
- `.github/workflows/ci.yml` — fix/prove governance test loading, call the tooling
  checker, add isolated E2E, and route physical Mongo through the safe runner.
- `scripts/pre_pr_check.py` — invoke `check_tooling_config.py` through the existing
  governance-check mechanism; do not change Git/read-only ownership.
- `tests/test_pre_pr_check.py` — prove tooling-check pass/fail propagation.
- `scripts/check_mongodb.py` — replace the arbitrary `FYP.users` read with an
  explicit-env connectivity-only ping and sanitized result.
- `apps/backend/tests/test_mongo.py` — update focused diagnostic tests; retain
  `app.mongo` unit coverage without changing application behavior.
- `docs/development/TOOLING_AND_MCP.md` — replace the stale “no project-local schema”
  claim; distinguish Docs MCP from cluster MCP and state the data-sharing boundary.
- `docs/test-plan/README.md` — record the new browser-smoke scope and non-goals.
- `README.md` — link the tooling runbook and list only safe entry commands.

### Delete/retire

- `scripts/run_phase13_physical_tests.py` — superseded by the all-phase safe runner.
  No tracked current-main consumer references this path.
- `tests/e2e/.gitkeep` — retire the unused root placeholder because the frontend-owned
  Playwright package resolves tests under `apps/frontend/e2e`.

### Explicitly unchanged

- All `apps/backend/app/**` product files.
- All `apps/frontend/src/**` product files.
- `scripts/mongo_test_safety.py` and the existing physical Mongo test modules, except
  only if implementation discovers a factual incompatibility; such a discovery is a
  stop-and-replan condition.
- `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/PROJECT_STATE.md`, and
  `docs/DEVELOPMENT_WORKFLOW.md`; current governance already covers this work.
- Phase 15B/15C files and worktrees.

## Implementation tasks

### Task 1 — Repair the current CI governance invocation

Files: create `tests/__init__.py`; modify `.github/workflows/ci.yml` only if the exact
existing command needs no further correction after the marker is added.

Steps:

1. Add the empty package marker.
2. Run the exact current CI command and confirm all three modules load.
3. Preserve the existing individual secret/pre-PR/contract commands.

Acceptance:

- The exact `python -m unittest tests.test_dev_context tests.test_check_project_state tests.test_check_architecture -v` command passes.
- No test discovery or product import semantics regress.

### Task 2 — Add a deterministic authenticated Playwright smoke foundation

Files: frontend manifest/lockfile, Playwright config, E2E spec, two launcher scripts,
launcher tests, `.gitignore`, CI, test-plan/runbook docs, and retire the root placeholder.

Steps:

1. Add exact-pinned `@playwright/test@1.56.1` as a dev dependency and regenerate the
   lockfile with npm; do not use a caret/range.
2. Scope Playwright discovery to `apps/frontend/e2e/**/*.e2e.ts` so Vitest never
   collects browser tests.
3. Make `scripts/run_e2e.py` require two explicit loopback ports (defaults may be
   repository-documented), check both are free, and fail without killing/reusing an
   occupant. Support environment overrides for concurrent worktrees.
4. Generate a random credential per run in memory. Pass it only through child-process
   environment. Never print it or persist it.
5. Make the backend launcher force `_env_file=None`, `APP_ENV=test`, memory persistence,
   Mock ACRA, local deterministic IDP, local registry-fed ownership, Mock GoldTier,
   demo controls off, and the explicit frontend origin. Derive all six runtime-only
   bootstrap hashes from the ephemeral password.
6. Start the backend and Vite on loopback with strict ports, wait for bounded readiness,
   invoke Playwright, and tear down only processes/process groups created by the runner.
   Do not call a general process killer.
7. Test unauthenticated protection plus login using `maya-lim` and the ephemeral
   password.
8. Test one Singapore case using UEN `202400001A` and the existing clean synthetic UAT
   document. Assert `COMPLETED` / `MOCK_GOLDTIER_SUBMITTED` evidence and visible Mock
   labeling; do not assert Ready-for-Approval, Live interoperability, or sponsor policy.
9. Add an isolated Linux CI job that installs the existing backend dev dependencies,
   runs `npm ci`, installs only Chromium plus required runner dependencies, then runs
   the wrapper. Keep ports explicit and do not supply external secrets.

Acceptance:

- `npm test` does not collect `.e2e.ts`.
- `npm run e2e:list` finds exactly the intended smoke tests.
- An occupied port causes a safe failure and no process termination.
- Backend/frontend child processes are absent after pass, test failure, readiness
  failure, timeout, and interruption.
- The complete smoke uses only local Mock/Local providers and memory persistence.
- No stable credential/hash or browser artifact is tracked.

### Task 3 — Add read-only GitHub PR/CI observation

Files: `scripts/github_pr_ci.py`, its tests, CI/tooling docs.

Steps:

1. Accept an optional PR number/URL/branch; default to the PR for the current branch.
2. Invoke only `gh pr view --json ...` and `gh pr checks --json ...` with argument
   arrays and `shell=False`.
3. Treat GitHub CLI check exit `8` as pending, not command failure.
4. Normalize the report to stable JSON: PR identity/state/review decision followed by
   checks sorted by workflow/name/link. Exclude PR body, comments, logs, environment,
   and raw stderr.
5. Add `--wait`, bounded `--timeout-seconds`, and bounded polling interval. Exit
   success only when every observed required check passes; use distinct nonzero exits
   for pending timeout, check failure/cancel, unavailable authentication/PR, and invalid
   CLI output.
6. Do not expose any `gh pr create/edit/merge/review`, `gh run rerun/cancel`, `git push`,
   or repository-settings path.

Acceptance:

- Tests prove the command allowlist, shell-free execution, exit-8 handling, deterministic
  order, timeout, redaction, and fail-closed malformed JSON behavior.
- The helper never changes Git, PR, check, workflow, or repository state.

### Task 4 — Repair Mongo development/test tooling

Files: replace the physical runner, repair the diagnostic, update focused tests, route
CI through the new runner, and update the runbook.

Steps:

1. Delete the phase-specific runner and create `run_physical_mongo_tests.py`.
2. Read only `PHASE12_MONGO_URI` from the current process environment. Do not construct
   application `Settings`, read `.env`, accept a URI argument, or print/copy the value.
3. Run all four current real-Mongo modules (Phase 12, 13, 14, and 14.5) with
   `--tb=no`. Let each module create and clean its own generated allowlisted database
   through `mongo_test_safety.py`.
4. Do not query, count, list contents from, write, clean, or drop `clm_poc` or any other
   shared/arbitrary database. Do not add a fallback cleanup sweep.
5. Make the physical runner report only sanitized suite/exit summaries. A cleanup
   failure is a hard failure requiring owner investigation, not authorization to drop
   anything manually.
6. Change `check_mongodb.py` to a connectivity-only ping using explicit process
   environment and `_env_file=None`; remove the `FYP.users` count and any database
   content output.
7. Route the existing CI Mongo service job through the runner so the safety wrapper is
   exercised, while ordinary backend/unit tests remain Mongo-independent.

Acceptance:

- `clm_poc`, arbitrary names, uppercase/short/traversal names, and absent explicit URI
  are rejected before any destructive operation.
- Unit tests prove no Settings `.env` load, no shared database lookup, no URI output,
  all physical suites selected, and sanitized failure output.
- A physical Mongo run proves generated database creation/use/cleanup for all current
  suites and leaves zero task-created databases.
- No connection string appears in stdout/stderr or durable evidence.

### Task 5 — Add and validate project-scoped MCP configuration

Files: `.codex/config.toml`, tooling checker/tests, pre-PR/CI integration, and MCP docs.

Steps:

1. Add the official Codex schema comment and a `camunda_docs` Streamable HTTP entry for
   `https://camunda-docs.mcp.kapa.ai`.
2. Set Docs MCP `enabled=true`, `required=false`,
   `default_tools_approval_mode="prompt"`, bounded timeouts, and
   `enabled_tools=["search_camunda_knowledge_sources"]`.
3. Add a `camunda_cluster` STDIO entry using local command `c8` with args
   `mcp-proxy --profile fyp-camunda`. Set `enabled=false`, `required=false`, prompt
   approval, bounded timeouts, and an initial read-only allowlist of
   `getClusterStatus` and `getTopology`.
4. Add no URL, cluster/region ID, OAuth endpoint, audience, client ID/secret, header,
   bearer token, environment-forwarding map, or placeholder credential.
5. Make `check_tooling_config.py` parse the tracked TOML and enforce the exact public
   docs URL, allowed keys/tool list, disabled cluster entry, exact local command/args,
   prompt approvals, optional startup, and absence of secret-bearing fields/values.
6. Invoke the checker from pre-PR and CI through the existing governance pattern.
7. Update the tooling guide: first-use Docs MCP sign-in is manual; queries leave the
   machine for the Kapa-powered service; never send sponsor-confidential material,
   source payloads, PII, secrets, or private code; validate consequential answers
   against official Camunda documentation.

Acceptance:

- Codex loads the project config only after the user trusts the repository.
- The Docs MCP is optional and prompt-approved.
- The cluster server remains disabled and cannot expose mutation tools even if someone
  accidentally starts its transport.
- Any secret field, non-approved endpoint, activation, command drift, expanded tool
  list, auto approval, or required startup makes the tooling checker and pre-PR fail.

### Task 6 — Publish the manual runbook and complete governance wiring

Files: development tooling runbook, existing tooling guide, test plan, README, CI,
pre-PR, and focused tests.

Steps:

1. Document local dependency setup, Playwright Chromium installation, safe port
   overrides, E2E listing/run commands, and artifact locations.
2. Document human GitHub login (`gh auth login -h github.com`) and the read-only helper
   commands. Do not ask for a token in a prompt or report.
3. Document physical Mongo as opt-in: an owner starts/provisions the local service and
   exports `PHASE12_MONGO_URI` through an approved local secret mechanism. Do not print
   an example URI. State that cleanup is limited to per-test generated allowlisted
   names.
4. Document Camunda Docs first-use sign-in and rate-limit/privacy caveats.
5. Document the future cluster gate without executing it: owner confirms Camunda 8.9+
   cluster support, enables cluster MCP in Camunda, creates a scoped API client, loads
   credentials into the local environment, runs
   `c8 add profile fyp-camunda --from-env`, verifies with
   `c8 get topology --profile fyp-camunda`, and requests a separate reviewed change to
   enable the repository MCP entry. Credentials/profile creation and config activation
   are not part of this phase.
6. Reiterate that final PR squash/merge, branch protection, repository secrets, global
   Codex config, Docker/npm trust settings, and external accounts remain human-owned.

Acceptance:

- A new developer can identify what is automatic, manual, or blocked without reading a
  historical report.
- No manual command embeds a credential, token, client secret, Mongo URI, cluster ID,
  OAuth endpoint, or guessed value.
- The runbook never describes Mock/Local/Partial/Dormant behavior as Live.

## Verification plan

Run focused checks first, then the complete affected `CI_TOOLING` matrix.

### Focused

```powershell
python -m unittest tests.test_dev_context tests.test_check_project_state tests.test_check_architecture -v
python -m unittest tests.test_check_tooling_config tests.test_github_pr_ci tests.test_run_e2e tests.test_run_physical_mongo_tests -v
python -m pytest apps/backend/tests/test_mongo.py apps/backend/tests/test_phase13_mongo_test_safety.py -p no:cacheprovider --tb=short
npm.cmd --prefix apps/frontend run e2e:list
npm.cmd --prefix apps/frontend test
```

Run the GitHub helper tests with subprocess/network calls mocked. Do not require GitHub
authentication for unit verification.

### Browser smoke

```powershell
python scripts/run_e2e.py
```

Before claiming pass, independently verify both ports are released and no runner-owned
backend/Vite/Playwright child remains. If Chromium is not installed or trusted CA setup
blocks installation, record the run as unavailable; do not disable certificate checks.

### Physical Mongo

After the owner supplies the environment-only URI to an authorized disposable/local
service:

```powershell
python scripts/run_physical_mongo_tests.py
```

Do not echo the environment variable. Physical evidence must show all selected suites
passed and task-created generated databases were cleaned. No claim is allowed when the
service is unavailable or any cleanup fails.

### Broad affected checks

```powershell
python -m pytest apps/backend/tests -p no:cacheprovider --tb=short
python -m ruff check apps/backend scripts tests
python -m mypy apps/backend/app
python -m unittest discover -s tests/contract -p "test_*.py"
python -m unittest discover -s tests -p "test_*.py"
python scripts/check_tooling_config.py
python scripts/check_project_state.py
python scripts/check_architecture.py
python scripts/check_secrets.py
npm.cmd --prefix apps/frontend run typecheck
npm.cmd --prefix apps/frontend test
npm.cmd --prefix apps/frontend run build
git diff --check
```

Then obtain an independent quality gate. Before PR readiness, fetch latest main under
the integration-safe workflow, integrate only if authorized, rerun affected checks,
commit only with explicit authorization, ensure a clean tree, run
`python scripts/pre_pr_check.py`, and complete the existing pre-PR checklist. Do not
commit, push, open a PR, or merge during the implementation task unless separately
authorized.

## Security and failure risks

| Risk | Control / stop condition |
|---|---|
| Browser harness inherits `.env`, Live modes, or shared Mongo | Backend launcher disables env-file loading and sets explicit memory/Mock/Local values. Checker/tests assert the exact environment. |
| Stable test credential leaks | Generate per run; pass in child environment only; never print, write, snapshot, or attach it. |
| Port collision harms another worktree | Check explicit ports; `strictPort`; no reuse; fail without killing. Allow owner-selected overrides. |
| Teardown kills unrelated process | Track only created PIDs/process groups; verify ownership/liveness; no name-based or port-owner killing. Stop and report if safe teardown cannot be proved. |
| Playwright artifacts contain case/auth data | Use synthetic data only, retain failure artifacts locally/CI with normal retention, never include secrets, and ignore generated directories in Git. |
| GitHub helper mutates external state | Hard command allowlist and mocked tests; no generic command passthrough or shell. |
| GitHub/CLI errors leak account or token detail | Suppress raw stderr and emit stable sanitized categories. |
| Mongo helper targets shared/arbitrary DB | Existing regex/generator remains sole owner; no user-supplied database argument or cleanup sweep; never inspect/drop `clm_poc`. |
| Mongo URI leaks in exception/traceback | `--tb=no`, boundary sanitization, no raw exception text, tests with credential-bearing fake errors. |
| Docs MCP receives confidential prompts | Prompt approval, manual sign-in, explicit prohibition on private/sponsor/PII/secret queries. |
| Disabled cluster MCP is accidentally activated | Checker requires `enabled=false`, prompt approval, optional startup, exact profile name, and read-only tool allowlist. Activation is a separate reviewed change. |
| `npx -y` downloads unpinned Camunda code | Do not use it. The disabled entry calls an owner-installed `c8`; installation/update is manual. |
| New dependency/lockfile collides with Phase 15 work | Touch only frontend manifest/lockfile after checking current main; never take another branch's lockfile wholesale. |
| CI coverage is accidentally replaced | Preserve all current jobs/steps and add the minimum new checks. Independent QG compares old and new job inventories. |

Stop and return to the owner if implementation requires a product-source edit, an
unknown external endpoint/auth value, a global configuration write, a database name
outside the current allowlist, a general cleanup/kill operation, test weakening, or a
change to Phase 15B/15C behavior.

## Rollback

- Playwright: remove the E2E job/config/spec/launcher/tests, remove only the exact
  Playwright manifest entry/scripts, regenerate the lockfile, and remove generated
  artifact ignores if no longer used. Product code remains untouched.
- GitHub reporter: delete its script/tests and remove only its runbook references; the
  canonical pre-PR checker remains.
- Mongo: restore the prior diagnostic/runner only if reverting the entire change, but
  do not run the restored unsafe shared-database inspection. A preferred operational
  rollback is to disable the new runner invocation while preserving the existing
  generated-name safety owner.
- MCP: set/remove the project entries by reverting `.codex/config.toml`; no global
  state or credential should require rollback. The cluster entry must remain disabled
  throughout this phase.
- CI/pre-PR: revert only the added job/steps/checker call and confirm every pre-existing
  job/step remains.
- Documentation: revert the runbook/tooling-guide delta with the implementation. Do not
  restore the stale claim that project-local Codex config is unsupported.

No rollback step may reset/rebase shared history, force-push, run `git clean`, delete a
database outside a generated allowlisted test name, or kill an unowned process.

## Parallel-worktree considerations

- The authorized branch/worktree is `dev-tooling`; do not switch branches or touch the
  Phase 15B/15C worktrees.
- Likely shared hotspots are `.github/workflows/ci.yml`, `apps/frontend/package.json`,
  `apps/frontend/package-lock.json`, `README.md`, and `scripts/pre_pr_check.py`. Inspect
  current `origin/main` before each hotspot edit and again before PR readiness.
- The E2E wrapper must allow per-worktree port overrides and fail on occupied defaults.
  It must not reuse a server from another checkout.
- Keep runtime artifacts under ignored task-owned paths; do not place them in a shared
  parent directory.
- If main advances with manifest/lockfile/CI changes, merge only when authorized and
  regenerate the lockfile from the reconciled manifest. Never choose a lockfile side
  blindly.
- CI uses one isolated runner per job, so it may use documented fixed loopback ports;
  local concurrent worktrees must supply non-colliding overrides.

## Architecture and ADR decision

No product architecture owner, dependency direction, public API, persistence strategy,
or runtime provider changes. Playwright is a developer-only test dependency, and MCP
configuration is developer-tool configuration, not application composition. No ADR is
required for this bounded tooling phase. If implementation proposes Camunda runtime,
a product-side MCP client/server, a new persistence owner, or a product test endpoint,
stop: that would require a separate architecture review and likely an ADR.

## Execution readiness view

- Intent lock: developer tooling only.
- Scope fence: exact files above; no product behavior or external activation.
- Baseline lock: `a81e7da1c677f063408952e2ae1a1a2478afc22b` at plan time; re-check
  `origin/main` before execution/PR readiness.
- Approved behavior: local Mock E2E, read-only GitHub reporting, guarded Mongo tests,
  optional Docs MCP, disabled cluster MCP.
- Compatibility: all current application behavior and CI coverage retained.
- Retirement: remove the stale physical runner, arbitrary collection diagnostic, and
  unused root E2E placeholder; do not retain parallel fallback owners.
- Task batches: CI repair; E2E; GitHub reporter; Mongo repair; MCP validation; docs and
  broad verification.
- Review gates: focused checks, affected broad checks, physical evidence when available,
  independent QG, latest-main integration, clean-tree pre-PR.
- Drift rule: if product files, credentials/endpoints, or parallel-phase conflicts enter
  the delta, stop and replan.
- Completion evidence: exact commands/results, changed-file classification, provider
  truth, security review, manual blockers, and independent gate verdict.

## Completion acceptance criteria

The implementation phase is complete only when all of the following are true:

- Only the authorized tooling/config/test/docs files changed.
- The current broken CI unittest module command passes.
- Playwright runs authenticated critical Mock smoke coverage with deterministic local
  setup/teardown, explicit collision-safe ports, and no product test hooks.
- GitHub tooling is strictly read-only, bounded, deterministic, and sanitized.
- The physical Mongo runner uses explicit environment-only configuration, all current
  real-Mongo suites, generated allowlisted databases, deterministic per-test cleanup,
  and no shared database inspection.
- The connectivity diagnostic no longer reads `FYP.users` or any other collection.
- `.codex/config.toml` contains no secret/auth/account/cluster values; Docs MCP is
  optional and prompt-approved; cluster MCP is disabled and read-only allowlisted.
- Unit, frontend, contract, security, governance, E2E, and applicable physical Mongo
  checks pass with truthful evidence; unavailable checks are not reported as passes.
- Existing CI coverage is preserved and the new CI paths pass.
- No secret/confidential artifact is newly tracked or printed.
- No Mock/Local/Partial/Dormant capability is called Live.
- An independent quality gate passes in a separate run.
- No commit, push, PR creation, merge, global configuration, external account setup,
  or cluster activation occurs without separate explicit authority.

## Final human actions

After independent acceptance, the owner may authorize commit/push/PR work under the
existing integration workflow. The owner handles GitHub authentication, trusted CA and
browser installation, local Mongo/Docker availability, Camunda Docs OAuth sign-in,
future Camunda cluster/API-client/profile setup, repository settings/secrets, and the
final squash merge.

STOP AFTER PLANNING. Do not implement tooling in the planner run.
