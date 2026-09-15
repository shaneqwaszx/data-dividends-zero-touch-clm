# Development Governance and Context Setup — Implementation Report

## Result and baseline

Implementation result: **PASS pending independent quality gate**.

- Branch: `codex/dev-governance-context`
- Initial `BASE_SHA`: `62a7d80324b40308e8cb3feba806b73a24c9c6ac`
- Implementation HEAD: unchanged at the base SHA because this run intentionally creates
  no commit.
- Verified `origin/main` at start: `62a7d80324b40308e8cb3feba806b73a24c9c6ac`
- Tracked tree before work: clean.
- Change classes: `DOCS_ONLY`, `ARCHITECTURE_REFACTOR` (governance/context ownership),
  and `CI_TOOLING`. Application architecture/runtime owners are documented, not changed.
- Optional external audit: unavailable at the supplied exact path. No substitute was
  searched or inferred; current tracked source remained the highest authority.

## Files added

- `.ai-pipeline/001_planner/DEVELOPMENT_GOVERNANCE_CONTEXT_INFRASTRUCTURE.md`
- `.ai-pipeline/reports/DEVELOPMENT_GOVERNANCE_CONTEXT_SETUP.md`
- `docs/PROJECT_STATE.md`
- `docs/ARCHITECTURE.md`
- `docs/DEVELOPMENT_WORKFLOW.md`
- `docs/decisions/ADR_TEMPLATE.md`
- `docs/development/TOOLING_AND_MCP.md`
- `.agents/skills/architecture-change-review/SKILL.md`
- `.agents/skills/phase-closeout-context-refresh/SKILL.md`
- `.agents/skills/external-provider-integration/SKILL.md`
- `.agents/skills/persistence-schema-change/SKILL.md`
- `.agents/skills/frontend-state-cache-change/SKILL.md`
- `scripts/dev_context.py`
- `scripts/check_project_state.py`
- `scripts/check_architecture.py`
- `tests/test_dev_context.py`
- `tests/test_check_project_state.py`
- `tests/test_check_architecture.py`

## Files modified

- `AGENTS.md`
- `README.md`
- `.agents/skills/README.md`
- `.ai-pipeline/README.md`
- `docs/architecture/README.md`
- `docs/decisions/DECISION_LOG.md`
- `.github/pull_request_template.md`
- `.github/workflows/ci.yml`
- `scripts/pre_pr_check.py`
- `tests/test_pre_pr_check.py`

## Current-state and source-of-truth model

`PROJECT_STATE.md` is a 217-line operational snapshot, not a phase report. A fenced
structured JSON block records `verified_main_sha`, verified date, provider names/modes/
classifications, persistence/identity/workflow-engine truth and open question IDs.
`verified_main_sha` is the inspected main baseline, not an assertion that every feature
HEAD must equal it.

The current evidence ordering is now explicit: synchronized source/tests; current
contracts/decisions; configuration/composition; sponsor questions/decisions; supplied
external audits; architecture/context; recent reports; historical reports. The existing
GoldTier-specific provisional contract ordering remains directly preserved.

Observed provider truth was checked against `config.py`, `composition.py`, connector
modules, persistence composition, auth/cache source and current Phase 14/14.5 records:

| Boundary | Current truth |
|---|---|
| ACRA | Mock default; generic sandbox-shaped partial; BizFile dormant/uncomposed; no Live proof |
| IDP | local deterministic extraction default; Mock demo/fault path; no vendor OCR |
| Ownership | registry-fed local deterministic Decimal engine; no external service |
| GoldTier/PingFed | Mock target only; no active PingFed/live adapter |
| Persistence | explicit memory default or Mongo; no silent fallback |
| Identity | repository-backed synthetic profiles plus process-local sessions; no production SSO |
| Camunda | not implemented |

## Agent context-loading workflow

`AGENTS.md` now directs fresh agents through:

```text
AGENTS.md
  -> docs/PROJECT_STATE.md
  -> docs/ARCHITECTURE.md
  -> docs/DEVELOPMENT_WORKFLOW.md
  -> relevant contracts/decisions/open questions
  -> relevant repository skill
  -> current owning source/tests
```

Assigned planners and nearest accepted gates are then loaded for phase/remediation/gate
work. Historical reports are on-demand only. README, architecture and pipeline indexes
repeat the four-file Start Here route.

## Canonical architecture and workflow

`docs/ARCHITECTURE.md` maps 18 bounded contexts to canonical files, responsibilities,
allowed dependency direction and prohibited ownership. It captures canonical evidence,
registry, IDP, ownership, reconciliation, target ledger, RBAC, policy, persistence,
portfolio and React Query boundaries plus 17 explicit invariants.

`docs/DEVELOPMENT_WORKFLOW.md` defines planner, implementer, QG, remediation, integration
and owner responsibilities; ten change classes; a proportional verification matrix;
skill precedence; stop conditions; ADR rules; sponsor-authority gates; integration and
closeout behavior. Physical Mongo is required only for changes capable of affecting
Mongo behavior.

## Skills added and validation

Each skill was created sequentially using a baseline pressure scenario, post-change
application, and loophole refinement. The baseline agents already resisted major unsafe
shortcuts but lacked a repeatable evidence/handoff contract; the skills standardize it.

| Skill | Baseline gap addressed | Post-change result |
|---|---|---|
| architecture-change-review | no fixed existence/entropy/retirement/handoff matrix | PASS after planner-stage, waiver, scope and retroactive-ADR loopholes were closed |
| phase-closeout-context-refresh | pending-merge report location/provider evidence dimensions implicit | PASS after exact report location and mode/classification separation |
| external-provider-integration | discrepancy/mock parity/call-count/security handoff incomplete | PASS after `PARTIAL` was limited to authority-independent scaffolding |
| persistence-schema-change | compatibility/CAS/restart/cleanup receipt not standardized | PASS after `PARTIAL` could not defer runtime/physical evidence |
| frontend-state-cache-change | key/session/cancel/invalidation/deletion matrix not standardized | PASS after `PARTIAL` could not defer isolation/adverse tests |

Every skill contains Trigger, Purpose, Inputs, Mandatory context, Preconditions, Analysis
steps, Allowed changes, Forbidden changes, Stop conditions, Required tests, Required
evidence, Expected report and Handoff format. `.agents/skills/README.md` now states when
to use/not use every skill and their precedence/composition.

## Deterministic scripts

### `dev_context.py`

Prints repository root, branch/HEAD/origin/main/merge base/ahead-behind, tracked-only
status, project-state baseline, provider matrix, sponsor question IDs, indexed skills,
workflow and pre-PR command. It reads a fixed safe file set, uses
`git status --short --untracked-files=no`, does not import application settings, and
never reads `.env`, arbitrary untracked files, environment values, Mongo or providers.

### `check_project_state.py`

Validates required state sections, structured metadata, baseline commit ancestry,
canonical provider inventory, source-parsed Settings defaults, Mock-only GoldTier
composition and Camunda absence. It does not require feature HEAD to equal the documented
main baseline and does not police free-form English.

### `check_architecture.py`

Implements only five narrow baseline-green rule families: no concrete Mongo imports in
API route modules; no frontend persistence references; one domain ownership owner;
dormant BizFile absent from composition; and Mock-only GoldTier configuration/composition.
More semantic invariants remain review obligations rather than brittle regex gates.

## CI and pre-PR integration

The CI security job runs the 13 governance tests and both direct checks once. No new
dependency or expensive product suite was duplicated. `pre_pr_check.py` runs both
governance scripts when present and records their bounded safe output; a focused unit
test verifies argument-array invocation and `shell=False`.

The real `pre_pr_check.py` was intentionally not run on this uncommitted handoff: it is
defined for a clean committed PR state and scans untracked files, while pre-existing
unrelated protected root artefacts are present and explicitly out of scope. Its full
synthetic test suite passed. Independent QG should operate on task-owned paths without
opening those artefacts.

## ADR and tooling/MCP support

`ADR_TEMPLATE.md` supports future decisions without inventing historical rationale.
The decision log now states when to use it. No retrospective ADR was fabricated.

`TOOLING_AND_MCP.md` distinguishes repository tools, skills, connectors, accounts and
secrets. No official tracked repo-local MCP schema was found, so no guessed `.mcp.json`
was created. GitHub, sponsor documents, Mongo, ACRA/GoldTier and Camunda postures are
documented with owner/manual boundaries.

## AGENTS.md rule migration

| Old rule/category | New canonical location | Still directly in AGENTS.md? | Reason |
|---|---|---:|---|
| source-of-truth hierarchy | `AGENTS.md`, workflow | yes | constitutional conflict resolution |
| sponsor authority/GoldTier overlay | `AGENTS.md`, contracts/decisions | yes | cannot be hidden behind links |
| secrets/KYC/PII | `AGENTS.md`, tooling/security skill | yes | task-start safety |
| protected/unrelated artefacts | `AGENTS.md` | yes | prevents unsafe scans/cleanup |
| Git/main/feature safety | `AGENTS.md`, branch protocol/integration skill | yes | mandatory baseline |
| worktree safety | `AGENTS.md`, branch protocol | yes | prevents overwriting developer state |
| physical Mongo/`clm_poc` safety | `AGENTS.md`, persistence skill/workflow | yes | destructive-data boundary |
| independent QG/re-QG | `AGENTS.md`, workflow/QG skill | yes | role separation |
| external-provider truth | `PROJECT_STATE.md`, architecture | yes, concise | dated detail outside constitution |
| mock/live labeling | `AGENTS.md`, state/provider skill | yes | false-success prohibition |
| pre-PR expectations | `AGENTS.md`, workflow/integration skill | yes | required readiness boundary |
| implementation/non-goals | `PROJECT_STATE.md` | yes, scope guard | current mutable detail delegated |
| architecture flow/interfaces/Decimal/HITL | `ARCHITECTURE.md` | yes, core invariants | complete owner map delegated |
| tests/definition of done/report fields | workflow | yes, concise | matrix/detail delegated |

Migration result: **PASS**. No unique safety requirement identified in the original file
was discarded. Mutable current state moved to its dated owner; critical prohibitions
remain in the entrypoint.

## Tests and checks

| Check | Result |
|---|---|
| focused governance `unittest` suite | PASS — 13 tests |
| pre-PR checker unit suite | PASS |
| secret-scanner unit suite | PASS |
| Ruff format | PASS — 8 Python files normalized |
| Ruff changed Python | PASS |
| `check_project_state.py` | PASS on current baseline |
| `check_architecture.py` | PASS on current baseline |
| `dev_context.py` | PASS; safe concise output |
| CI YAML `yaml.safe_load` | PASS |
| `git diff --check` | PASS (line-ending notices only) |

Tests prove no `.env`/untracked-secret reads, no environment-secret output, no Git/file
mutation, tracked-only status behavior, feature-HEAD independence, deliberate state
mismatch detection, and every encoded architecture violation. Synthetic Git fixtures
run only under the repository ignored test-temp area; the sandbox requires local
permission for their `.git` writes.

Physical Mongo, application lifecycle, full frontend and full backend product suites were
not run because application runtime/business code and provider/persistence/cache behavior
were not changed. Direct secret scanning was not run because it would traverse protected
untracked artefacts; the scanner unit suite passed.

## Manual-only setup

1. Owner-approved MCP/plugin/connector installation when a future task needs it.
2. OAuth/external-account authentication for GitHub/sponsor document/external services.
3. Secret/certificate/token/URI provisioning and rotation through approved runtime means.
4. GitHub account/repository/branch-protection/CI-secret settings; unchanged here.
5. Final human review, push/PR action and PR merge.
6. Any machine-global dependency, Mongo service or external sandbox installation;
   intentionally not performed.

## Deferred recommendations, risks and readiness

- Independent QG should challenge document accuracy, checker false positives/negatives,
  skill trigger overlap and the AGENTS migration table.
- The missing optional external audit remains an advisory evidence gap; current source
  and accepted tracked records were sufficient for this implementation.
- Existing inaccessible pytest-cache directories and unrelated protected untracked root
  artefacts remain owner/workstation concerns. They were not opened, scanned or changed.
- Exact project-state baseline should advance only after an accepted merge is inspected;
  use `phase-closeout-context-refresh` to handle the squash SHA safely.
- No application API, shared product type, persistence schema, connector interface,
  configuration name, business rule, mapping, auth behavior or runtime composition changed.

The branch working tree is ready for an independent governance quality gate, not for a
completion/merge claim. No commit, push, PR or merge was performed.
