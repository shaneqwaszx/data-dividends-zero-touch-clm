# Development Tooling Automation — Execution Addendum

Date: 2026-09-19  
Role: IMPLEMENTER  
Branch: `dev-tooling`  
BASE_SHA / initial HEAD / initial `origin/main`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`  
Parent plan: `.ai-pipeline/001_planner/DEV_TOOLING_AUTOMATION.md`

## Intent and scope lock

Implement only the rebaselined development-tooling handoff: deterministic local/CI
orchestration, truthful check reporting, safe physical-Mongo routing, project-scoped
Codex MCP configuration, and the corresponding tests and documentation. The change
classes are `CI_TOOLING` and `DOCS_ONLY`.

The implementation does not change product behavior, backend APIs or domain models,
frontend application source, persistence schemas, provider contracts, sponsor rules,
or provider classifications. It does not activate Camunda, start MongoDB, contact a
real provider, or claim Live interoperability.

## Execution refinements

### A. Browser artefact containment

- Playwright traces, videos, screenshots, HAR files, persistent profiles, and
  `storageState` are disabled.
- The task must not retain raw browser network artefacts or request/response bodies.
- Browser traffic is restricted to the explicitly configured loopback frontend and
  backend origins.
- Task-owned output is captured, bounded, and sanitized before any failure summary is
  printed.

### B. GitHub check truthfulness

- Every reported check observation is bound to the pull request's observed
  `headRefOid`.
- An empty required-check set, unavailable check data, or an all-skipped required set
  is never reported as green.
- The helper re-reads the pull request head after observing checks. A changed head
  restarts polling within the original monotonic deadline or returns `HEAD_CHANGED`.
- Required checks determine the required-check result. Optional failures are reported
  separately and are never hidden.
- The helper is an evidence reporter only. It does not approve, merge, or establish
  merge readiness.

### C. Physical Mongo output and evidence

- The physical runner reads the URI only from `PHASE12_MONGO_URI`; it never loads
  `.env`, accepts a URI argument, or prints the URI.
- Collection and execution output are contained, bounded, and sanitized beyond
  `--tb=no`; ambient pytest options and third-party plugin autoload are disabled.
- Only the four explicitly assigned physical modules are collected and executed.
- Missing modules, zero collected tests, unexpected ownership, unavailable MongoDB,
  failures, or an all-skipped run are not physical verification success.
- Physical execution requires explicit owner authorization and an externally available
  MongoDB. This task does not start Docker or a database service.

### D. MCP configuration boundary

- `.codex/config.toml` is project-scoped client configuration only.
- `enabled_tools` narrows what this Codex client exposes; it is not server-side
  authorization and does not constrain other clients.
- Per-tool approval prompts remain explicit. The configuration contains no endpoint,
  token, credential, or automatic workflow activation.
- The Camunda cluster entry remains disabled and its presence does not change the
  project's `Not implemented` runtime classification.

### E. Integration-sensitive files

- `apps/frontend/package.json`, `apps/frontend/package-lock.json`, and
  `.github/workflows/ci.yml` are integration hotspots.
- This implementation edits them only for the exact pinned Playwright dependency and
  assigned CI wiring. A later authorized integration run must reconcile current-main
  intent semantically; files must not be copied wholesale from another worktree or
  accepted by choosing an entire side of a conflict.

### F. Stop boundary

- The run ends after implementation, proportional local verification, and
  `.ai-pipeline/reports/DEV_TOOLING_IMPLEMENTATION.md`.
- It does not perform the independent quality gate, stage files, commit, push, publish,
  create a pull request, merge, rebase, reset, stash, clean, switch branch, or begin a
  later phase.
- Physical Mongo verification is recorded as blocked/partial unless the owner has
  explicitly authorized it and supplied an already-running disposable test service.

## Execution readiness

- TDD route: `Mode: off`; `Decision: skipped`. The planner requires focused regression
  tests but does not authorize strict test-first sequencing.
- Canonical owners: the new task-specific scripts own orchestration/reporting; existing
  product services, `scripts/mongo_test_safety.py`, and product runtime composition stay
  unchanged.
- Compatibility boundary: current backend/frontend/contract test discovery and all
  existing CI coverage must remain present.
- Retirement boundary: `scripts/run_phase13_physical_tests.py` and
  `tests/e2e/.gitkeep` are replaced only after their assigned successors exist and are
  verified.
- Evidence boundary: focused unit tests first, then configured backend/frontend,
  contract, lifecycle, secret, governance, and tooling checks. Independent QG remains
  outstanding after this run.

## Initial checkpoint

1. Add the Python discovery marker and prove the named `unittest` command plus existing
   backend/contract discovery.
2. Add pinned Playwright configuration, safe E2E orchestration, two real-browser tests,
   and focused orchestration tests.
3. Add the bounded GitHub PR check reporter and mocked regression tests.
4. Replace the legacy physical-Mongo runner and diagnostic with explicit, sanitized
   execution plus mocked tests; route CI through it.
5. Add the project-scoped MCP configuration and offline validator after local/official
   schema verification.
6. Update the pre-PR checker, documentation, indexes, and run the required verification
   matrix.
7. Write the implementation report and stop before independent QG or Git publication.

Drift decision at start: `continue`. The observed baseline matches the planner, the
pre-existing untracked planner is preserved, and no sponsor or product decision is
required for this tooling-only scope.

## Owner-authorized remediation refinement after independent Dev Tooling QG

Date: 2026-09-19

The independent Development Tooling quality gate returned `FAIL`. This refinement
authorizes only the following remediation within the existing tooling owners:

- The Playwright interception layer may recognize the exact pre-existing Google Fonts
  stylesheet request used by `apps/frontend/src/design-system.css` and fulfill it
  locally with bounded empty CSS. No request may leave the browser. The match must bind
  HTTPS, exact `fonts.googleapis.com` host, the documented `/css2` family query, and
  stylesheet resource type. Every variant, `fonts.gstatic.com` request, or other
  non-loopback request remains an aborting, sanitized test violation. The earlier
  script-injected CSP is not accepted as the deterministic owner of this behavior.
- The GitHub evidence reporter may discover local identity using only fixed,
  read-only `git remote get-url origin` and `git branch --show-current` commands with
  argument arrays, `shell=False`, bounded timeouts, and sanitized failures. Every
  `gh pr view` and `gh pr checks` call must include explicit `--repo OWNER/REPO`
  binding. Repository, requested target, observed PR number, branch, head SHA, and
  checks form one validated observation identity; mismatches cannot return green.
- Explicit GitHub PR URLs define repository and PR identity. Query and fragment data
  are ignored for identity and excluded from canonical output. Numeric, branch, and
  current-branch observations derive the expected repository from the strict GitHub
  `origin` remote. No other Git or GitHub command is authorized.

The immutable quality-gate report remains unchanged. Product source, dependencies,
Mongo owners, MCP configuration, CI wiring, and lifecycle code/tests remain outside
this remediation. Physical Mongo execution still requires a separately authorized
disposable service. One complete serialized Windows lifecycle suite is evidence-only;
any recurring failure is a blocker for separately authorized work, not permission to
edit that harness.
