# Development Tooling Runbook

This runbook covers repository-owned development validation only. It does not activate
Live providers, Camunda runtime orchestration, production authentication, or external
approval. Commands are written for Windows Command Prompt and run from the repository
root unless a different directory is stated.

## Responsibility map

| State | Activity | Owner/boundary |
|---|---|---|
| Automatic | Offline tooling-config validation, unit tests, E2E process lifecycle, sanitized GitHub check observation | Repository scripts; no external mutation |
| Manual | Dependency/browser installation, GitHub login, Docs MCP login, local Mongo provisioning, external credentials and accounts | Human owner |
| Blocked | Camunda cluster MCP activation, Live ACRA/GoldTier/PingFed claims, automatic PR approval/merge | Separate authority and reviewed change required |

## Local setup

Prerequisites are Python 3.12, Node.js 22, npm, and an available supported Chromium
binary installed through Playwright. The repository does not change global npm trust,
proxy, CA, browser, Docker, or Codex configuration.

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e "apps\backend[dev]"
npm.cmd --prefix apps\frontend ci
apps\frontend\node_modules\.bin\playwright.cmd install chromium
```

In managed networks, use the organization's approved CA/proxy setup. Never disable TLS
verification. CI installs its own Chromium dependency; the local runner uses only an
already available browser and never downloads one.

## Authenticated browser smoke

Listing reports the current configured test inventory and does not start servers,
generate a password, or require external credentials. Multiple parameterized tests
can share one exact selector; test and selector counts are distinct:

```bat
npm.cmd --prefix apps\frontend run e2e:list
```

Run the complete local smoke through the sole process owner:

```bat
.venv\Scripts\python.exe scripts\run_e2e.py
```

Optional distinct loopback ports can be assigned explicitly:

```bat
.venv\Scripts\python.exe scripts\run_e2e.py --backend-port 8765 --frontend-port 4173
```

Concurrent worktrees may instead set `CLM_E2E_BACKEND_PORT` and
`CLM_E2E_FRONTEND_PORT`; explicit command-line values take precedence. For a manual
visible-browser diagnostic after Chromium is installed, use:

```bat
npm.cmd --prefix apps\frontend run e2e:headed
```

The launcher rejects invalid, duplicate, occupied, or Chromium-restricted ports
(`ERR_UNSAFE_PORT`, for example 5060, 6000, 6566 or 10080; the default 8765/4173
ranges contain none). A suite derives one port pair per lifecycle from the base ports
and checks every pair before the first lifecycle starts, so an unsafe or occupied base
fails at once instead of mid-suite; each lifecycle still probes its own pair at
startup. The launcher then starts the real backend in
test/memory mode with Mock ACRA, local deterministic document extraction, registry-fed
local ownership analysis, Mock GoldTier, and demo controls disabled; starts Vite with
strict port ownership; waits for process-owned readiness; runs every discovered selector
in a fresh lifecycle; and tears down only its own process groups. Tagged Garden selectors
use strict offline synthetic protocol fixtures; Golden retains the normal Mock composition.

`--timeout-seconds` is the per-lifecycle readiness plus Playwright execution budget
(default 240 seconds, allowed 30-900), including focused `--grep` runs. A complete
isolated suite gives each selector this full budget; prior successful selectors do
not consume later selectors' execution allowances. Product assertion timeouts and
retries remain unchanged.

The separate finite suite safety budget is `60 + selector_count *
(lifecycle_timeout + 120)` seconds. Discovery is bounded at 60 seconds; each lifecycle
reserves 120 seconds for existing bounded cleanup, capture joins and dispatch. The
three owned processes can each require up to six five-second POSIX stop phases;
Windows cleanup is also bounded. Cleanup failure remains fatal, with no further
selector dispatched. A suite safety exhaustion names an undispatched selector and
returns non-zero, never suite PASS.

CI explicitly uses a 60-second per-lifecycle budget, two `--shard` jobs and the job
timeout in `.github/workflows/ci.yml`. `tests/test_run_e2e.py` derives the largest
shard's worst-case budget from current discovery and fails if it plus the setup
allowance exceeds that job timeout, so reassess the bound when that test fails rather
than recording a selector count here. The launcher logs discovered count, effective
budgets, individual lifecycle elapsed time, total elapsed and the slowest lifecycle.
GitHub's job timeout remains a final outer guard even if the launcher is forcibly
terminated.

Failure categories distinguish `INDIVIDUAL_SELECTION_TIMEOUT`, `SUITE_JOB_TIMEOUT`,
`ASSERTION_FAILURE` (non-zero Playwright result), `READINESS_FAILURE`, and
`CLEANUP_FAILURE`. No failed, undispatched or skipped selector is counted as passing.

### Isolated diagnostics

Three opt-in flags apply only to isolated lifecycles (never with `--grep`); without
them the suite, its fail-fast exit and CI behavior are unchanged.

- `--selectors-file PATH` runs only the listed discovered selectors (one per line,
  blank lines and `#` comments ignored), each in its own lifecycle with its normal
  fixture composition, in discovery order. Unknown, repeated or absent entries fail
  before any lifecycle starts. It cannot be combined with `--shard`. Use it to rerun
  failed selectors under the same isolation as the official suite; a `--grep` run
  shares one lifecycle and is not equivalent evidence.
- `--keep-going` continues after a failed lifecycle, then lists every failure and exits
  non-zero. It never prints suite PASS when any lifecycle failed. Interruption, a
  cleanup failure and the suite safety budget still stop the run. It is a diagnostic
  inventory, not acceptance evidence.
- `--results-json PATH` writes a new file (an existing path is refused, never
  overwritten) with the run identity (`HEAD`, its tree, a dirty flag, `origin/main`),
  Node/Playwright versions, and one record per selected lifecycle: selector, fixture,
  ports, result (`PASS`, `PORT_UNAVAILABLE`, `READINESS_FAILURE`, `ASSERTION_FAILURE`,
  `INDIVIDUAL_SELECTION_TIMEOUT`, `CLEANUP_FAILURE`, `INTERRUPTED` or `NOT_RUN`),
  exit code, elapsed time and phase durations (backend readiness, frontend readiness,
  Playwright, cleanup). A failure before the first lifecycle records only its stage
  as `setup_failure` (`DISCOVERY`, `SELECTION`, `PORT_ALLOCATION` or
  `PORT_PREFLIGHT`); the sanitized detail is printed to stderr only. The file holds
  no output text, credentials or URIs. With a dirty tree, the recorded tree is
  `HEAD`'s, not the tested content.

```bat
.venv\Scripts\python.exe scripts\run_e2e.py --timeout-seconds 60 --keep-going --results-json tmp\e2e-results.json
.venv\Scripts\python.exe scripts\run_e2e.py --timeout-seconds 60 --selectors-file tmp\rerun.txt
```

The browser interception layer continues only requests to the task-owned loopback
origins. It recognizes the one exact baseline `fonts.googleapis.com` stylesheet URL
used by `design-system.css` and fulfills that request locally with an empty CSS
response; no request is sent to Google. Any URL, path, family query, or resource-type
variant—including every `fonts.gstatic.com` request—is aborted and recorded as a
sanitized unexpected-egress violation, which fails the smoke after the request has
received its single route disposition.

The per-run password exists only in the backend and Playwright process environments.
It is not placed in Vite variables, command-line arguments, source, bundles, or normal
output. Trace, video, screenshots, HAR, persistent profiles, and `storageState` are
disabled by configuration. Individual synthetic browser tests may explicitly retain
sanitized screenshots in ignored task-owned output; these are not publication content.
`playwright-report/`, `test-results/`, and `.playwright-output/` are ignored defensively.
Ordinary interruption is handled; no user-space launcher can promise cleanup after an
uncatchable operating-system termination.

## GitHub PR/check evidence

Authenticate interactively; never paste a token into the helper or its output:

```bat
gh auth login -h github.com
```

Observe the current branch PR, a specific PR, or wait within a bounded deadline:

```bat
.venv\Scripts\python.exe scripts\github_pr_ci.py
.venv\Scripts\python.exe scripts\github_pr_ci.py 123
.venv\Scripts\python.exe scripts\github_pr_ci.py 123 --wait --timeout-seconds 600 --poll-seconds 15
```

The helper uses only `git remote get-url origin` and `git branch --show-current` for
fixed read-only local identity discovery, then invokes only `gh pr view` and
`gh pr checks`. Every GitHub command is explicitly bound to the expected
`OWNER/REPO`. The helper validates repository, requested target, observed PR number,
branch where applicable, head SHA, and checks as one observation identity. Explicit PR
URL query and fragment data are ignored for identity and removed from canonical output;
untrusted response fields and raw stderr are never copied through. Required-check
absence, all-skipped checks, unavailable or malformed identity/data, failures,
cancellation, timeout, or head movement are non-success. Optional failures are listed
separately. This is evidence, not approval, merge readiness, or authorization to change
GitHub.

## Physical Mongo tests

Physical execution is opt-in. An owner must provision and start a disposable local or
CI Mongo service, then set `PHASE12_MONGO_URI` through an approved local secret
mechanism. Do not echo the value. The repository runner neither starts Mongo nor reads
`.env`.

```bat
.venv\Scripts\python.exe scripts\run_physical_mongo_tests.py
```

The runner collects and executes only the Phase 12, 13, 14, and 14.5 physical modules.
Each suite creates and cleans its own fresh generated allowlisted database through
`scripts/mongo_test_safety.py`. The runner never enumerates, reads, writes, counts,
cleans, or drops `clm_poc` or another shared/arbitrary database. Missing configuration,
missing/zero collection, all-skipped execution, timeout, test failure, or cleanup
failure is not verification and requires owner investigation—not manual broad cleanup.

For a connectivity-only diagnostic using an explicitly set `MONGO_URI`:

```bat
.venv\Scripts\python.exe scripts\check_mongodb.py
```

The diagnostic issues only a ping and reports no URI or database content.

## Project-scoped Codex MCP configuration

`.codex/config.toml` is loaded only after the repository is trusted. Validate it
offline without starting or contacting a server:

```bat
.venv\Scripts\python.exe scripts\check_tooling_config.py
```

`camunda_docs` is optional, prompt-approved, and restricted in this Codex client to
`search_camunda_knowledge_sources`. First-use authentication is manual:

```bat
codex mcp login camunda_docs
```

Queries leave the machine for the Kapa-powered service. Never send sponsor-confidential
material, source payloads, KYC/PII, secrets, private code, credentials, or internal
error bodies. Camunda documents rate-limit the service and require consequential output
to be checked against official Camunda documentation. The `enabled_tools` list is a
client-side exposure restriction, not server authorization and not a guarantee about
other clients.

`camunda_cluster` remains disabled. Its allowlist contains only `getClusterStatus` and
`getTopology`, but no cluster connection is authorized by this repository.

## Future Camunda cluster gate

Do not execute this gate as part of normal setup. Before a separate reviewed change may
enable the cluster entry, the owner must confirm a supported Camunda 8.9+ cluster,
explicitly enable the cluster MCP server, create a scoped API client, and load the
required values into the local environment through the approved secret mechanism.
Then the owner may create and verify the local profile:

```bat
c8 add profile fyp-camunda --from-env
c8 get topology --profile fyp-camunda
```

Profile creation, credentials, endpoints, client identifiers, cluster identifiers,
OAuth settings, activation, and runtime use are outside this phase. A separate security
and architecture review is required. Camunda remains `Not implemented` in the product.

## Governance checks

Focused tooling checks:

```bat
.venv\Scripts\python.exe -m unittest tests.test_check_tooling_config tests.test_github_pr_ci tests.test_run_e2e tests.test_run_physical_mongo_tests -v
.venv\Scripts\python.exe scripts\check_tooling_config.py
```

The pre-PR checker also invokes the tooling-config checker, but it is designed for a
clean committed feature tree. Implementation work with expected uncommitted files must
not present its failure as a product or tooling regression.

Final squash/merge, branch protection, repository secrets, external accounts, global
Codex settings, Docker/npm trust configuration, and external service setup remain
human-owned.
