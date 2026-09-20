# Development Tooling Automation — Independent Re-Quality and Security Gate

Date: 2026-09-19
Role: Independent reviewer
Change classes: `CI_TOOLING`, `DOCS_ONLY`, with security-sensitive browser,
GitHub-observation, subprocess, MCP-configuration, and physical-Mongo boundaries.

## 1. Executive Result

**PASS WITH MINOR FIXES.** The two prior High findings are closed, physical Mongo
execution is complete, the Windows lifecycle is green, and no remaining material
security, contract, architecture, false-success, or functional tooling defect was
found. One bounded low-risk retirement inconsistency remains: the unchanged root
`bootstrap_folders.ps1` still recreates the deleted `tests/e2e/.gitkeep` placeholder.

- **DTA-QG-001 closed:** the exact baseline Google Fonts stylesheet is fulfilled by
  Playwright with empty local CSS and is not sent to Google. All variants and every
  other non-owned request remain fail-closed. The independent real Chromium run passed
  **2/2 in 3.3 seconds** and proved real login, authenticated navigation, the synthetic
  Singapore journey, `COMPLETED`, truthful `GoldTier Mock` / non-production wording,
  and `MOCK_GOLDTIER_SUBMITTED`.
- **DTA-QG-002 closed:** repository, target, PR, applicable branch, head SHA, and checks
  form one validated observation identity. The focused adversarial GitHub suite passed
  **24/24**; wrong-identity green evidence and unsafe URL/stderr propagation are now
  rejected.
- **DTA-QG-003 closed:** the guarded physical runner independently selected all four
  intended modules and returned **14 collected, 14 passed, 0 failed, 0 errors, 0
  skipped** against the already-authorized disposable Mongo 7 service. Generated
  allowlisted cleanup completed through the existing safety owner.
- **Lifecycle sufficient:** the recorded remediation result was 18/18 in 274.464
  seconds. This gate independently reran the unchanged lifecycle suite and obtained
  **18/18 in 262.092 seconds**, followed by zero listeners on ports 8000/5173 and no
  runtime manifest.
- **Minor retirement fix required:** `bootstrap_folders.ps1:22` still creates the
  obsolete root `tests\e2e` directory, and line 37 recreates its `.gitkeep`. Running
  this tracked bootstrap after accepting the deletion would restore the retired path
  and dirty the tree. The frontend Playwright owner itself is unaffected.

Tooling acceptance is therefore **PASS WITH MINOR FIXES**. This verdict does not itself
authorize remediation, commit, push, pull request, CI workflow, merge, external login,
or Camunda activation.

### Review identity and content freeze

- Repository root:
  `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-dev-tooling`
- Branch: `dev-tooling`
- `BASE_SHA`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- `HEAD`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- Local `origin/main`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- Merge base: `a81e7da1c677f063408952e2ae1a1a2478afc22b`
- Ahead/behind: `0/0`
- Staged paths: none.
- Product source delta under `apps/backend/app/**` and `apps/frontend/src/**`: none.

The reviewed tooling/config/test identity is a deterministic SHA-256 over 23 sorted
records of `repository-relative path<TAB>file SHA-256`, with `DELETED` for
`scripts/run_phase13_physical_tests.py` and `tests/e2e/.gitkeep`:

`01be021c136fdc7dd1b144d7135fc70e9dd3719a06bd521202eb5c954ac4d806`

The set covers `.codex/config.toml`, CI and ignore configuration, the frontend package
manifests, Playwright config/spec, the changed Mongo diagnostic test, all changed/new
tooling scripts and focused tooling tests, and the two intentional deletions. Plans,
reports, ordinary documentation, and ignored runtime/build output are outside this
source/config/test digest.

## 2. Acceptance Checklist

| Requirement | Result | Direct evidence |
|---|---|---|
| Exact current CI governance module command | **PASS** | 37/37 tests under the worktree interpreter. |
| Deterministic authenticated Chromium smoke | **PASS** | Exactly two tests listed; real execution 2/2 in 3.3 s. |
| Exact known font stylesheet locally neutralized with no network egress | **PASS** | `route.fulfill` returns bounded empty CSS; focused route test and real browser run passed. |
| All other browser traffic fails closed with sanitized evidence | **PASS** | Wrong font path/query/resource type, `fonts.gstatic.com`, public, LAN/private, wrong-port, non-HTTP, and malformed cases pass adversarial coverage. |
| One route action per request | **PASS** | Exact font route produced one `fulfill`; blocked route produced one `abort`; owned route uses one `continue`. |
| Real login and truthful synthetic Singapore completion | **PASS** | Browser asserted Dashboard login, `COMPLETED`, `GoldTier Mock`, non-production wording, and `MOCK_GOLDTIER_SUBMITTED`. |
| Successful E2E cleanup and no sensitive Playwright artefact | **PASS** | Assigned ports had zero listeners. Only `test-results/.last-run.json` remained, containing `status: passed` and an empty failed-test list. No trace, video, screenshot, HAR, storage state, error context, or persistent profile existed. |
| GitHub observation identity and output safety | **PASS** | 24/24 adversarial tests plus direct source inspection. |
| Only fixed read-only Git/GitHub families | **PASS** | `git remote get-url origin`, `git branch --show-current`, `gh pr view`, and `gh pr checks`; no CLI passthrough or mutation family. |
| Safe diagnostic and four-suite physical runner | **PASS** | Diagnostic tests 8/8; runner-focused tests 16/16; real physical run 14/14. |
| Honest pytest 8.4.2 collection/execution parsing | **PASS** | Project `addopts` contains `-q`; runner resets `addopts` before applying one fixed `-q`; real all-pass, pass/skip, failure, collection-error, and zero-collection parser tests passed. |
| Generated allowlisted cleanup and no shared target | **PASS** | Existing `clm_p12_*`, `clm_p13_*`, `clm_p14_*`, `clm_p145_*` generator/guard unchanged; every physical module uses `finally` cleanup. Runner contains no database name, enumeration, drop, or cleanup sweep and cannot accept a database argument. No `clm_poc` read/write/drop path was exercised. |
| URI and raw failure containment | **PASS** | Runner output contained only bounded counts/status; no URI or raw driver text. The authorized endpoint marker was absent from all task-owned source/report inputs after execution. |
| Lifecycle | **PASS** | Owner record 18/18 in 274.464 s; independent rerun 18/18 in 262.092 s; lifecycle sources unchanged. |
| Optional Docs MCP and disabled cluster MCP | **PASS** | Exact-shape offline checker passed; cluster entry remains `enabled=false`; no MCP was contacted or authenticated. |
| Broad affected regression | **PASS, with verified baseline Ruff exceptions** | Backend, frontend, contracts, typing, governance, security, browser, lifecycle, physical Mongo, and diff checks completed as recorded below. |
| Retirement of the old root E2E placeholder | **MINOR FIX** | `tests/e2e/.gitkeep` is deleted, but unchanged `bootstrap_folders.ps1:22,37` recreates the directory and placeholder. |

## 3. Contract and Integration Findings

### DTA-QG-001 — closed

`apps/frontend/playwright.config.ts` classifies each request into exactly one of
`OWNED_LOOPBACK`, `KNOWN_NEUTRALIZED_FONT_STYLESHEET`, `BLOCKED_EXTERNAL`, or
`BLOCKED_INVALID`. The neutralized case requires all of:

- HTTPS;
- exact host `fonts.googleapis.com`;
- exact path `/css2`;
- the baseline Cormorant Garamond/Lora family query;
- no credentials, explicit port, or fragment; and
- Playwright resource type `stylesheet`.

It is fulfilled locally with status 200, `text/css; charset=utf-8`, and an empty body.
No browser network request is continued for that URL. Every variant, including a wrong
path/query/family/resource type and `fonts.gstatic.com`, is aborted and recorded only
as safe structural fields. Arbitrary public, LAN/private, wrong-port, non-HTTP, IPv6,
and malformed inputs remain blocked. The exact allowed/fulfilled/blocked action counts
and sanitized violation text are covered by `tests/test_run_e2e.py`.

The real smoke ran the existing application composition rather than a fake route. It
proved the authenticated protected workspace and the synthetic Singapore clean-fixture
journey to the accepted Mock terminal result. No product file or provider composition
changed.

### DTA-QG-002 — closed

`scripts/github_pr_ci.py` constructs the expected repository and target identity before
any GitHub observation:

- numeric, branch, and current-branch targets derive `OWNER/REPO` from only
  `git remote get-url origin`;
- current-branch targeting additionally uses only `git branch --show-current`;
- an explicit canonical GitHub PR URL supplies the repository and positive PR number;
- every `gh pr view` and `gh pr checks` call receives explicit `--repo OWNER/REPO`;
- both PR views validate PR number, canonical repository URL, applicable branch, head
  SHA, state, draft flag, review decision, merge state, and base branch; and
- checks are accepted only while the two validated views retain the same head SHA.

The 24-test adversarial suite independently covered wrong PR, wrong repository, wrong
branch/current branch, second-view identity mismatch, head movement, all-green checks
against the wrong identity, malformed/credential-bearing PR URLs, query/fragment
canonicalization, invalid view fields, raw stderr containment, local Git failure,
required-check absence/all-skip, pending exit 8, and explicit repository binding.
Child stderr is never copied through. Check and PR links are canonicalized without
query/fragment data.

No live GitHub command was required for this local source/behavior gate, and no GitHub
state was mutated. GitHub Actions execution remains external evidence, not implied by
workflow configuration.

### Physical Mongo — complete

The original `NO_EXECUTED_TESTS` was a verbosity/parser defect, not a hidden skip or
missing execution. `apps/backend/pyproject.toml` contributes `-q`; the former runner
also added `-q`, producing effective `-qq` under pytest 8.4.2 and suppressing the timed
count summary that the runner expected. The corrected runner supplies
`-o addopts=` before its own deterministic options and parses only the final timed
pytest summary line in memory.

Direct inspection and execution confirmed that the runner:

- uses `sys.executable` and was launched through this worktree's Python 3.12.10
  interpreter;
- selects only the Phase 12, 13, 14, and 14.5 physical modules;
- reads only `PHASE12_MONGO_URI` and forwards it through a narrow child environment;
- has no URI/database CLI option, `Settings` construction, `.env` loader, shared
  database read, database enumeration, database drop, or cleanup sweep;
- disables ambient pytest options and third-party plugin autoload;
- treats missing suites, collection failure, zero collection, unavailable summary,
  execution failure, inconsistent counts, and all-skipped/no-pass execution as
  non-success; and
- never renders captured child stdout/stderr or the URI.

The independent authorized rerun returned exactly:

`PHYSICAL_MONGO_RESULT=PASSED; SUITES=4; COLLECTED=14; PASSED=14; FAILED=0; ERRORS=0; SKIPPED=0`

All selected modules create generated allowlisted database names and invoke the
unchanged drop-and-verify cleanup owner from `finally`. A cleanup failure would surface
as a test error and make the runner non-success. No `clm_poc` content or other shared
database was read, written, tested, cleaned, or dropped.

### Product contract and provider truth

No API/model/shared type, persistence schema/repository semantic, external connector,
business rule, mapping, authentication/RBAC/team policy, product architecture owner,
or provider composition changed. The accepted terminal result remains
`COMPLETED / MOCK_GOLDTIER_SUBMITTED`, not approval or Live interoperability.

## 4. Tester and Adversarial Findings

### Fresh execution matrix

| Command/scope | Result |
|---|---|
| Exact context/project-state/architecture unit command | **PASS — 37/37 in 23.755 s** |
| Four focused tooling modules | **PASS — 66/66 in 7.187 s** |
| `tests.test_github_pr_ci` within focused suite | **PASS — 24/24** |
| `tests.test_run_e2e` within focused suite | **PASS — 16/16** |
| `tests.test_run_physical_mongo_tests` within focused suite | **PASS — 16/16** |
| Pre-PR checker unit suite | **PASS — 42/42 in 36.671 s** |
| Focused Mongo diagnostic | **PASS — 8/8** |
| Browser listing | **PASS — exactly 2 tests in 1 file** |
| Real authenticated Chromium smoke | **PASS — 2/2 in 3.3 s** |
| Guarded physical Mongo runner | **PASS — 4 suites, 14/14, zero failed/errors/skipped** |
| Complete Windows lifecycle suite | **PASS — 18/18 in 262.092 s** |
| Full backend pytest | **PASS — 934 passed, 14 expected physical/infrastructure skips, 5 warnings in 81.78 s** |
| Canonical contract discovery from `apps/backend` | **PASS — 44/44** |
| Backend mypy | **PASS — 91 source files** |
| Task-owned Ruff | **PASS** |
| Repository-wide Ruff | **NON-GREEN BASELINE ONLY — two unchanged `RUF100` directives** |
| Frontend unit suite | **PASS — 155/155 in 7 files** |
| Frontend typecheck | **PASS** |
| Frontend production build | **PASS — 97 modules transformed** |
| Playwright package graph | **PASS — `@playwright/test`, `playwright`, and `playwright-core` all 1.56.1** |
| Tooling config / project state / architecture | **PASS** |
| Secret checker and adversarial suite | **PASS — direct scan plus 8/8 tests** |
| `git diff --check` | **PASS — Windows line-ending notices only** |

The broad Ruff findings are limited to
`tests/contract/test_phase_06_zero_touch_contract.py:9` and
`tests/contract/test_phase_07_uat_contract.py:12`. Both files have an empty diff from
`HEAD`; these are verified baseline findings and are not classified as task defects.

Sandboxed attempts at the focused tooling suite, the browser runner, and frontend
Vitest initially encountered Windows temporary-directory or subprocess `EPERM`
restrictions. Each was rerun unchanged with normal Windows permissions and passed as
reported above. These invalid sandbox attempts did not justify or produce any source,
test, timeout, or assertion change.

The production `scripts/pre_pr_check.py` entry point was not run because this gate
reviews an intentionally uncommitted/dirty implementation tree and has no commit
authority. Its complete 42-test suite passed. GitHub Actions were not executed and are
not claimed.

## 5. Code and Architecture Review

No blocking code/architecture finding remains. One low-risk internal-retirement finding
requires a bounded fix.

### Low — DTA-RQG-001: stale bootstrap consumer recreates the retired E2E placeholder

The implementation deletes `tests/e2e/.gitkeep` because Playwright tests are now owned
under `apps/frontend/e2e`. However, unchanged `bootstrap_folders.ps1:22` still includes
`tests\e2e` in `$dirs`, and line 37 includes it in `$keepDirs`. Running that bootstrap
will recreate the directory and `.gitkeep`, undoing the retirement and creating
avoidable working-tree noise.

This is a stale internal consumer, not an external compatibility boundary. Under the
delete-first retirement rule, both root `tests\e2e` entries should be removed from the
bootstrap arrays. The main browser owner, product runtime, security boundaries, and all
executed evidence remain valid; the issue is low-risk, deterministic, and isolated to
repository scaffolding. The reviewed unchanged bootstrap file has SHA-256
`f46b5a995a291ce67725d1c362ad1fc447e46e675097dca23930d35deab964bd`.

- The browser harness stays outside product composition and uses one task-owned process
  owner, explicit distinct loopback ports, strict Vite port binding, bounded readiness
  and test deadlines, an allowlisted environment, and PID/process-group-scoped cleanup.
- The GitHub reporter is observation-only, deterministic, shell-free, deadline-bound,
  and contains no generic Git/GitHub command passthrough.
- The Mongo runner reuses the existing generated-name/cleanup owner and does not create
  a second persistence or cleanup model.
- The stale phase-specific physical runner is fully retired with no lingering
  reference. The root E2E placeholder deletion is incomplete only because of
  DTA-RQG-001; the frontend Playwright path is already the sole functional E2E owner.
- The exact-pinned Playwright graph is developer-only. No application dependency or
  product runtime import points at the new tooling.
- `.codex/config.toml` is project-scoped tooling configuration. `camunda_docs` is
  optional and prompt-approved. `camunda_cluster` is disabled, optional,
  prompt-approved, and client-allowlisted only to `getClusterStatus` and `getTopology`.
  Client allowlisting is not misrepresented as server authorization.
- Existing CI jobs remain present; the physical job uses the guarded runner, the E2E
  job uses the repository runner, and the security job invokes the exact tooling
  configuration checker.

The current official Codex configuration reference recognizes the used project MCP
keys. Current official Camunda documentation identifies the configured Docs MCP URL and
single search tool, and lists `getClusterStatus` and `getTopology` for the cluster MCP.
This validates static configuration intent only; no runtime connection or authorization
is claimed.

## 6. Security Review

No material security finding remains.

The repository integration-security checklist was applied to the changed browser,
GitHub, Mongo, subprocess, MCP, logging/redaction, and Mock/Local truth boundaries; it
identified no active defect or newly exposed sponsor/private artefact.

- Browser egress is fail-closed; the exact known stylesheet is locally fulfilled, not
  externally fetched.
- Per-run login material stays in child environments and is redacted from captured
  output. The browser receives no Mongo, GitHub, Camunda, provider, or ambient password
  configuration.
- Browser recording/session artefacts are disabled. The only retained success marker
  contains no case, credential, session, request, or response data.
- GitHub response fields are treated as untrusted, identity-bound, type/shape checked,
  and sanitized. Raw CLI/local-Git stderr is suppressed.
- Physical Mongo output contains no URI, raw exception, provider body, or database
  content. Cleanup remains restricted to generated allowlisted names.
- The secret scanner covers tracked and non-ignored untracked files and passed.
- The Camunda cluster MCP remains disabled and contains no endpoint, client/cluster ID,
  OAuth material, bearer/header value, environment-forwarding map, or placeholder
  credential.

No live provider, GitHub account mutation, MCP login/contact, global Codex/c8/npm/Docker
configuration change, or confidential sponsor artefact access occurred. The only
external-state use was the explicitly authorized, already-running disposable Mongo
service for the guarded physical verifier.

## 7. Required Fixes

1. **DTA-RQG-001:** in a separately authorized remediation, remove `tests\e2e` from
   both `$dirs` and `$keepDirs` in `bootstrap_folders.ps1`. Verify that running or
   statically evaluating the bootstrap no longer recreates `tests/e2e/.gitkeep`, that
   no lingering reference to the retired path remains, and that the existing focused
   tooling/config checks still pass. Do not reintroduce a compatibility placeholder.

The two repository-wide Ruff findings are unchanged baseline issues, not required
Development Tooling fixes. No remediation was performed during this review.

## 8. Readiness and Remaining Prerequisites

- **Development Tooling Automation acceptance:** **PASS WITH MINOR FIXES**.
- **Ready for owner-controlled scoped commit/integration:** **not yet**. Complete and
  independently verify DTA-RQG-001 first; then proceed only under an explicit owner
  instruction and the repository integration workflow.
- **Ready to claim PR/CI/merge completion now:** **no**. Before PR readiness, an
  authorized integration run must fetch current `origin/main`, reconcile any drift,
  commit only task-owned paths, obtain a clean tree, run the production
  `scripts/pre_pr_check.py`, push/open a PR only with owner authority, and obtain actual
  GitHub Actions plus human review. Repository-owner humans merge.
- **GitHub external prerequisite:** interactive owner authentication/account and actual
  PR/check execution remain manual; this gate used local adversarial tests and did not
  contact GitHub.
- **Browser external prerequisite:** new machines/CI must install the exact pinned
  Chromium revision through approved CA/proxy controls; no TLS bypass is authorized.
- **Mongo external prerequisite:** future physical reruns require an owner-provisioned,
  already-running disposable service and environment-only URI. This gate's required
  physical evidence is complete.
- **Camunda Docs prerequisite:** first-use sign-in is manual and queries leave the
  machine. Confidential sponsor material, private code, PII, secrets, and raw provider
  content must not be submitted.
- **Camunda cluster:** remains **disabled**. Profile creation, credentials, endpoint
  configuration, enablement, and product/runtime use require a separate authorized
  architecture and security change.
- **Product provider truth:** ACRA remains **Mock** by default with only a partial
  generic sandbox-shaped seam and dormant BizFile module; IDP and ownership remain
  **Local** deterministic POC behavior with Mock fault support; GoldTier remains
  **Mock**; PingFed, Live ACRA/GoldTier, production SSO, and Camunda runtime remain not
  implemented.

This gate does not authorize the next product phase or change any sponsor decision.

## 9. Git Status and Review Boundary

At report creation, branch `dev-tooling`, `HEAD`, `BASE_SHA`, merge base, and local
`origin/main` all resolve to
`a81e7da1c677f063408952e2ae1a1a2478afc22b`. The implementation remains uncommitted and
the index is empty. Expected tracked modifications/deletions and task-owned untracked
files remain present. This report is the reviewer's only repository modification.

No source, test, configuration, ordinary documentation, dependency, timeout, assertion,
or product behavior was changed. No file was staged. No commit, push, pull request,
workflow mutation, merge, branch switch, rebase, reset, stash, clean, package/browser
install, MCP activation/login, or GitHub mutation occurred.

### Verification confidence receipt

- Evidence action: full static review of the changed tooling/config/test tree; focused
  adversarial browser/GitHub/physical-runner tests; real Chromium; real physical Mongo;
  complete lifecycle; broad backend/frontend/contract/type/governance/security checks.
- Result: **PASS WITH MINOR FIXES**; all three prior blockers closed, with one bounded
  stale internal bootstrap consumer remaining.
- Covered scope: exact uncommitted Development Tooling delta, its configured local/CI
  consumers, security boundaries, Mock journey, physical persistence execution, and
  cleanup behavior.
- Uncovered scope: actual GitHub Actions/PR execution, live GitHub/MCP connectivity,
  Camunda cluster authorization, and every future machine's local dependency setup.
- Residual risk: the tracked bootstrap can recreate the intentionally deleted root E2E
  placeholder and dirty the tree; external/manual environments and later integration
  drift remain separately bounded.
- Confidence grade: **A** — direct target execution plus relevant broad regression and
  fresh independent physical/lifecycle evidence.
