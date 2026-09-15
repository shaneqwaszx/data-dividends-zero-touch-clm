# Development Governance and Context — Independent Quality Gate

## Executive Result

**BLOCKED.** The governance documentation is broadly useful, the constitutional
`AGENTS.md` migration preserves the important safety boundaries, and all focused tests
pass when run with permission to create isolated Git fixtures. However, three Medium
findings remain: the project-state checker accepts materially contradictory structured
metadata; the architecture checker combines brittle false positives with real import
bypasses; and the canonical architecture map does not accurately distinguish the
top-level composition-root dependency in `app/main.py` from ordinary API-route
dependencies. These defects undermine the claimed deterministic drift/architecture
guard and require remediation plus an independent re-quality gate before commit.

## Baseline and Scope

- Review role: independent quality gate; this reviewer did not implement the change.
- Branch: `codex/dev-governance-context`.
- Accepted base, HEAD, fetched `origin/main`, and merge base:
  `62a7d80324b40308e8cb3feba806b73a24c9c6ac`.
- Main drift after fetch: none.
- Change classes reviewed: `DOCS_ONLY`, governance-level
  `ARCHITECTURE_REFACTOR`, and `CI_TOOLING`.
- Application runtime changed: no.
- Application business logic changed: no.
- No application API/model/shared type, persistence schema, connector interface,
  runtime configuration, mapping, authorization behavior, or frontend cache behavior
  is in the implementation manifest or tracked diff.
- The only reviewer-created file is this report. No remediation was performed.

## Files Reviewed

All 28 implementation-manifest files were reviewed:

- constitutional/index surfaces: `AGENTS.md`, `README.md`,
  `.agents/skills/README.md`, `.ai-pipeline/README.md`,
  `docs/architecture/README.md`, and `docs/decisions/DECISION_LOG.md`;
- canonical governance: `docs/PROJECT_STATE.md`, `docs/ARCHITECTURE.md`,
  `docs/DEVELOPMENT_WORKFLOW.md`, `docs/decisions/ADR_TEMPLATE.md`, and
  `docs/development/TOOLING_AND_MCP.md`;
- new skills: `architecture-change-review`, `phase-closeout-context-refresh`,
  `external-provider-integration`, `persistence-schema-change`, and
  `frontend-state-cache-change`;
- tooling/tests: `scripts/dev_context.py`, `scripts/check_project_state.py`,
  `scripts/check_architecture.py`, `scripts/pre_pr_check.py`, and their four focused
  test modules;
- delivery surfaces: `.github/pull_request_template.md`,
  `.github/workflows/ci.yml`, the governance planner, and the implementation report.

The baseline authority read-set included the prior `AGENTS.md`, `README.md`,
`docs/PROJECT_CONTEXT.md`, current contracts, decision log, open sponsor questions,
configuration reference, demo runbook, current application configuration/composition,
frontend auth/query owners, secret scanner, CI/pre-PR owners, and relevant Phase 14/
14.5 accepted evidence. Historical reports were used only as supporting evidence.

## Source-of-Truth Review

**PASS.** The new hierarchy puts current synchronized source/tests first, followed by
current contracts/decisions and composition/configuration. It preserves the special
provisional GoldTier conflict ordering, quarantines contradictory examples, and makes
clear that project-defined behavior is not sponsor-confirmed. Historical reports do
not outrank current source. No circular authority dependency was found: current source
remains ultimate implementation evidence while `PROJECT_STATE` and `ARCHITECTURE` are
explicit current summaries.

## AGENTS.md Migration Verdict

**PASS.** The entrypoint remains sufficiently self-contained. It directly retains the
assigned-scope rule, material-ambiguity stop, source hierarchy, sponsor authority,
task-start order, feature-branch/no-main rule, Git/worktree/protected-artifact safety,
secret/PII safety, physical-Mongo/`clm_poc` prohibition, independent-QG expectation,
Mock/Sandbox/Live truthfulness, pre-PR requirement, and final human merge boundary.
Mutable implementation status was moved into a dated state document without hiding
critical safety rules. No material weakening of the prior constitution was found.

## PROJECT_STATE Verdict

**PASS for the document; checker FAIL is separate.** The document is a concise current
snapshot rather than a phase narrative. Direct source/configuration checks support the
provider classifications, memory/Mongo composition, schema v3, process-local identity,
Mock GoldTier, dormant BizFile, local ownership engine, cache ownership, and lack of
Camunda/production SSO. It clearly limits `COMPLETED / MOCK_GOLDTIER_SUBMITTED`, UBO,
reconciliation, and policy claims; it does not claim Ready-for-Approval or Live
interoperability. `verified_main_sha` is explicitly an inspected main baseline rather
than a feature-HEAD equality requirement, and the closeout instructions handle squash
merge SHAs without invention.

## ARCHITECTURE Verdict

**FAIL.** Most bounded-context owners, provider classifications, evidence flow,
RBAC/persistence/ledger/cache invariants, and prohibited duplicate-owner rules agree
with current source. Finding DGQG-003 remains: the canonical dependency map groups
`app/main.py` with ordinary HTTP/API modules and lists only service/domain dependencies,
while current `app/main.py` imports `app.persistence.composition` and constructs the
persistence bundle. The text also labels a diagram as dependency direction while
showing adapters in a bidirectional-looking control/dependency relationship. The map
must explicitly distinguish the top-level composition-root exception from route-module
rules so future agents do not either remove legitimate wiring or normalize persistence
dependencies inside routes.

## Development Workflow / Change-Class Verdict

**PASS.** The ten classes, role separation, latest-main integration, sponsor stop
conditions, ADR criteria, independent QG/re-QG, and physical-Mongo boundary are clear.
Pressure-checking the matrix produced proportionate outcomes:

- CSS-only UI: focused/full frontend, typecheck/build, affected checks, pre-PR;
- ownership rule: backend/domain/static/regression/contract/QG evidence;
- React Query key: cache skill plus focused/adverse/full frontend evidence;
- Mongo schema: persistence skill, CAS/restart/security and physical Mongo;
- ACRA sandbox: provider/contract/security/call-stopping evidence, sandbox only when authorized;
- CI-only: focused tooling, Ruff, secret/governance, QG and pre-PR;
- architecture refactor: broad affected evidence, ADR decision and architecture review;
- sponsor clarification docs: authority reconciliation plus affected docs/checks without
  automatically claiming runtime acceptance.

No matrix row was found to require a materially irrelevant destructive or live check.

## Skills Verdict

**PASS.** All five skills have usable triggers/non-triggers, mandatory context,
preconditions, deterministic stop conditions, proportional test/evidence contracts,
and actionable handoffs. Provider work composes contract reconciliation and security
review; persistence composes architecture/integration safety where applicable; cache
work remains under backend authorization and phase/QG ownership. None grants sponsor
authority, destructive Git/data behavior, commit/push/merge, or Live classification.
The index makes overlap and precedence discoverable.

## dev_context Verdict

**PASS with a Low test-depth note.** The script is fixed-root by default, uses explicit
files, tracked-only Git status, argument-array subprocesses with `shell=False`, and no
application settings/environment-value/Mongo/provider loading. It does not search for
parent repositories or print remotes. Missing/malformed state fails with a sanitized
error; missing refs return `UNAVAILABLE`. A detached branch currently renders an empty
branch value, and the focused suite does not directly cover missing origin, detached
HEAD, malformed state, or a subdirectory-supplied `--root`; this is DGQG-004, not an
unsafe behavior.

## Project-State Checker Verdict

**FAIL.** Baseline and feature-HEAD independence pass, but DGQG-001 shows that the
checker does not implement several validations claimed by the plan/report. An
in-memory adversarial run changed `schema_version` to `999`, `verified_date` to an
invalid string, persistence default to `mongo`, and identity mode to
`production_sso` while current source remained schema 3 / memory / local POC; `validate`
returned `[]`. The checker also does not validate `verification_status` or most provider
mode/classification pairs. Its narrow prose policy is reasonable, but structured
metadata and explicitly claimed source correlations must not silently drift.

Baseline-SHA semantics themselves are sound: the checker proves commit existence and
ancestry and does not require feature HEAD equality. After an ordinary feature commit
or squash merge, the baseline may remain an ancestor; a closeout refresh updates it
after accepted main behavior is inspected. The defect is the insufficient correlated
metadata coverage, not the absence of arbitrary HEAD equality.

## Architecture Checker Verdict

**FAIL.** The rules are read-only and baseline-green, but DGQG-002 violates the
requirement that encoded rules be narrow mechanical invariants:

- `FRONTEND_BACKEND_BOUNDARY` scans raw source substrings, so a comment or harmless
  display string triggers; its negative test uses exactly a harmless string literal,
  not a prohibited import/dependency.
- `API_PERSISTENCE_BOUNDARY` misses the real concrete-import form
  `from app.persistence import mongo_case_store` because AST extraction returns only
  `app.persistence` and the predicate does not flag it.
- `MOCK_GOLDTIER_ONLY` requires one exact formatted annotation string, creating avoidable
  format/refactor coupling rather than parsing the `Settings` literal structurally.

The canonical-owner and BizFile checks have low maintenance cost but intentionally
limited detection; semantic duplicate owners and composition changes still require
review. The current implementation mixes those acceptable limits with the material
false-positive/false-negative behavior above.

## Pre-PR Integration Verdict

**PASS with a Low diagnostic finding.** Both governance scripts are invoked with the
current interpreter, explicit root, `shell=False`, copied environment, and optional Git
locks disabled. Nonzero results make pre-PR fail and there is no recursive invocation.
Missing scripts are intentionally skipped for compatibility, while CI invokes the new
scripts directly. DGQG-005: a failing subprocess report includes only stdout and has no
test for nonzero/stderr-only failure, so an exception written only to stderr produces an
opaque failure. This does not make the gate bypassable, but should be corrected.

The actual full pre-PR command was not run: this intentionally uncommitted tree and
protected unrelated untracked artifacts make its untracked inventory/scan unsafe and
misleading. Its 38-test synthetic suite is the appropriate evidence for this gate.

## CI Verdict

**PASS for wiring.** Valid YAML adds the 13 focused governance tests and both direct
checks to the root-working-directory security job after checkout/Python 3.12 setup.
No secret, Mongo, network provider, product-suite duplication, dependency, or working-
directory mistake was introduced. Direct-check nonzero exits fail the step. The
semantic weakness of those checks is covered by DGQG-001/002 rather than a CI wiring
finding.

## MCP / Tooling Verdict

**PASS.** The guide separates repository tools, skills, MCP/connectors, accounts, and
secrets. It grants no sponsor authority from tool installation, recommends no broad
Mongo access, describes Camunda as absent, creates no invented MCP schema, and keeps
OAuth/accounts/secrets/certificates/manual setup outside tracked repository config.

## ADR and PR Template Verdict

- ADR template: **PASS.** It captures genuine future context, alternatives,
  consequences, invariants, security/persistence, migration/retirement, verification,
  revisit conditions and authority without fabricating history.
- PR template: **PASS.** It surfaces class, base/main, architecture/ADR, sponsor and
  provider authority, security/persistence impact, exact verification, QG, integration,
  context refresh, and human merge ownership without excessive repetition.

## Discoverability Verdict

**PASS.** README, pipeline, skill, architecture, and decision indexes expose the four
canonical start documents quickly. A scoped relative-link validation over the changed/
new Markdown surfaces passed. No dead link or conflicting startup sequence was found.

## External Audit Absence

**NO IMPACT.** The materials available to this gate do not expose another exact audit
path to inspect, and no arbitrary directory search was performed. The implementation
did not need that advisory audit to establish the current provider/runtime/owner facts:
current source, tests, configuration, contracts, decisions, and accepted integration
evidence were sufficient. No statement reviewed appears dependent on unverifiable stale
memory from the absent audit.

## Verification Evidence

| Check | Result |
|---|---|
| Governance tests | PASS — 13 tests in 9.523s after permissioned rerun |
| Initial sandbox governance attempt | INVALIDATED — isolated `git init` denied; baseline-only tests passed |
| Pre-PR tests | PASS — 38 tests in 52.690s |
| Secret-scanner tests | PASS — 8 tests |
| `python scripts/check_project_state.py` | PASS on current baseline |
| `python scripts/check_architecture.py` | PASS on current baseline |
| `python scripts/dev_context.py` | PASS; safe tracked-only context output |
| Ruff on all 8 changed/new Python files | PASS |
| CI YAML `yaml.safe_load` | PASS |
| Scoped Markdown relative-link check | PASS |
| `git diff --check` | PASS; CRLF advisory warnings only |
| Full pre-PR command | NOT RUN — unsafe/misleading on intentional dirty tree with protected unrelated untracked artifacts |
| Physical Mongo/live providers/full product suites | NOT RUN — out of scope; no product runtime change |

## Findings

### Critical

None.

### High

None.

### Medium

#### DGQG-001 — Structured project-state drift silently passes

`scripts/check_project_state.py` does not validate or source-correlate several structured
fields its design/report claims to protect: metadata schema/date/status, persistence,
identity, and most provider classifications. A materially contradictory in-memory state
mutation returned no failures. Add narrow type/value/source validations and realistic
negative tests without introducing feature-HEAD equality or free-form prose policing.

#### DGQG-002 — Architecture checker is brittle and bypassable

The frontend rule flags harmless text/comments, the API rule misses a concrete
`from app.persistence import mongo_case_store` import, and Mock GoldTier configuration
uses exact text matching. Replace these with syntax/import-aware mechanical checks and
make every negative fixture an actual prohibited dependency/composition violation.

#### DGQG-003 — Canonical architecture obscures the composition-root exception

`docs/ARCHITECTURE.md` describes `app/main.py` under an API dependency row that excludes
persistence composition, while source legitimately imports `app.persistence.composition`
to construct the runtime bundle. Split or explicitly document composition-root wiring,
ordinary route restrictions, static dependency direction, and runtime port dispatch.

### Low

#### DGQG-004 — dev_context edge cases lack direct tests

Add focused assertions for detached HEAD, missing origin/main, missing/malformed state,
Git warning/error behavior, and subdirectory/invalid-root invocation. Render detached
branch explicitly rather than as a blank label.

#### DGQG-005 — Pre-PR governance failure diagnostics omit stderr

Capture a bounded sanitized stderr fallback for nonzero governance subprocesses and
test nonzero, stderr-only, and intentionally missing-script behavior. Failure already
propagates, so this is diagnostic/test debt rather than a bypass.

## Required Fixes and Readiness

Required remediation is limited to DGQG-001 through DGQG-003. DGQG-004/005 are bounded
low-risk corrections that should be included if convenient but do not independently
justify architectural expansion. Rerun the focused governance, pre-PR, secret-scanner,
direct checker, Ruff, YAML, link and diff checks, then obtain an independent re-QG.

- Ready for remediation: yes.
- Ready for commit: no.
- Ready for push: no.
- Ready for PR: no.
- Ready for merge: no.
- Live ACRA readiness: no.
- Real GoldTier/PingFed readiness: no.

## Git and Data Safety Receipt

- `.env` accessed: no.
- Secret/hash material printed: no.
- Mongo URI accessed or printed: no.
- Private key/certificate accessed: no.
- `clm_poc` accessed: no.
- Protected unrelated artifacts accessed/enumerated/scanned: no.
- Files modified by reviewer other than this report: no.
- Staged/committed/pushed/reset/rebased/stashed/cleaned/force-pushed: no.
- Branch switch/main development: no.
