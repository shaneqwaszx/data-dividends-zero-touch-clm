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

Listing proves there are exactly two test cases and does not start servers, generate a
password, or require external credentials:

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

The launcher rejects invalid, duplicate, or occupied ports; starts the real backend in
test/memory mode with Mock ACRA, local deterministic document extraction, registry-fed
local ownership analysis, Mock GoldTier, and demo controls disabled; starts Vite with
strict port ownership; waits for process-owned readiness; runs the two browser tests;
and tears down only its own process groups.

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
disabled. `playwright-report/`, `test-results/`, and `.playwright-output/` are ignored
defensively, but a successful configured run retains no browser recording artefacts.
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
