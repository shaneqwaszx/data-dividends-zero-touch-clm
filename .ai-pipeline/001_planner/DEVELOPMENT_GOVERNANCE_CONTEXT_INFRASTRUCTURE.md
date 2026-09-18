# Development Governance and Agent Context Infrastructure

## Plan header

**Goal:** Replace repeated historical reconstruction with a concise, source-backed
current-state snapshot, canonical agent architecture guide, change-class workflow,
procedural repository skills, and deterministic read-only governance checks.

**Architecture:** Markdown remains the human and agent authority surface. Small Python
tools inspect tracked source, Git metadata, and machine-readable metadata embedded in
`docs/PROJECT_STATE.md`; they do not become an application runtime dependency or a
policy engine. `AGENTS.md` remains the constitutional entrypoint and delegates detail
without hiding critical safety rules.

**Tech stack:** Markdown, Python 3.12 standard library, `unittest`, Git, and the existing
GitHub Actions/pre-PR framework. No application, database, MCP, plugin, or package
dependency is added.

**Baseline/authority refs:** `origin/main` and feature base
`62a7d80324b40308e8cb3feba806b73a24c9c6ac`; current tracked source and tests;
current contracts/decisions/configuration; `AGENTS.md`; `docs/PROJECT_CONTEXT.md`;
Phase 14/14.5 planner, architecture, execution, and final gate material. The requested
external audit path was checked and was unavailable; it is not substituted or inferred.

**Compatibility boundary:** No application API, business rule, persistence schema,
provider composition, authentication behavior, frontend state behavior, or product
runtime changes. Existing unique Git, secret, sponsor-authority, mock/live, Mongo safety,
and quality-gate rules remain discoverable and enforceable.

**TDD Route:**

- Mode: off
- Decision: skipped
- Strict authority: not applicable
- Strict signals: new deterministic checks require regression tests, but strict
  test-first implementation was not requested.
- Light eligibility: documentation is low-risk; checkers are bounded tooling with
  focused post-change tests.
- TDD-fit exception: repository skills use their separate mandatory pressure-scenario
  validation protocol.
- Test posture: post-change regression plus synthetic negative fixtures; baseline and
  post-change pressure scenarios for each skill.
- Reason: proportional verification is explicitly assigned.
- Verification: focused governance tests, tooling suite, Ruff, direct checker runs,
  `git diff --check`, and the intended dirty-tree pre-PR behavior.

## Planning controls

### Aegis visibility

Planning is required because this task changes repository-wide context authority,
development workflow, reusable skills, CI/pre-PR gates, and future architecture-change
behavior.

### BaselineUsageDraft

- Required: repository rules; project context; current architecture, contracts,
  decisions, sponsor questions, configuration, composition, auth/cache architecture,
  Phase 14/14.5 evidence, current CI/checkers, and repository skills.
- Acknowledged before planning: all required current tracked sources above.
- Missing: the advisory external audit at the supplied exact path.
- Decision: continue; current tracked source outranks the missing advisory source.

### Requirement Ready Check

- Requirement source: user-supplied governance implementation brief dated 2026-09-15.
- Acceptance: explicit phase outputs B–S, final coherence questions, and exact Git/data
  safety stop state.
- Open blocker: none; the external audit is optional and lower authority.
- Decision: ready.

### Change Necessity

- Need: fresh agents currently need many historical reports to reconstruct current
  truth and no deterministic state/architecture drift check exists.
- No-change option: linking existing phase documents would preserve duplication and
  stale provider/runtime claims.
- Minimum boundary: governance Markdown, repository-scoped skills, three standard-
  library scripts, focused tests, and narrow CI/pre-PR/index wiring.
- Decision: docs/config/tooling code change.

### Existence and architecture integrity checks

- `docs/architecture/ARCHITECTURE.md` is historical/current but not at the required
  canonical path and does not provide a complete owner/dependency map. Reference it;
  create `docs/ARCHITECTURE.md` as the current canonical agent entrypoint.
- `docs/PROJECT_CONTEXT.md` mixes durable scope with accumulated phase history. Keep it
  as context; create a shorter operational `PROJECT_STATE.md`.
- `docs/CODEX_WORKFLOW.md`, branch protocol, skills, and phase reports overlap. Create
  one change-class workflow that links rather than moves their specialized detail.
- Existing `pre_pr_check.py` is the correct aggregator; add narrow governance commands
  only if tests prove deterministic behavior.
- No application canonical owner is replaced or duplicated.

### Execution Readiness View

- Intent lock: repository governance/context infrastructure only.
- Scope fence: files listed below; no app runtime/business logic.
- Baseline lock: verified clean `origin/main` SHA `62a7d803…`.
- Owner constraints: source/tests outrank docs; AGENTS remains constitutional;
  checkers are conservative and tracked-source-only.
- Compatibility boundary: existing unique rules and runtime behavior remain.
- Retirement boundary: stale statements are referenced as history or superseded; no
  historical report is deleted or rewritten.
- Test obligations: direct positive/negative checker tests and safety properties.
- Review gate: independent QG after an unstaged, uncommitted implementation handoff.
- Drift rule: if source contradicts planned provider/owner assertions, source wins and
  documents/checks are revised before completion.
- Advisory boundary: this plan is guidance, not sponsor authority or completion proof.

## Current baseline

- Branch created from synchronized main: `codex/dev-governance-context`.
- `BASE_SHA`, `HEAD`, and `origin/main`: `62a7d80324b40308e8cb3feba806b73a24c9c6ac`.
- Tracked tree at entry: clean.
- ACRA: Mock default; generic sandbox-shaped connector optional/partial; BizFile
  implementation dormant and absent from composition; no live proof.
- IDP: local deterministic text extraction default; Mock demo/fault path; no vendor OCR.
- Ownership: registry evidence feeds the single local deterministic Decimal engine;
  Mock ownership is fault/demo support only.
- GoldTier: `Literal["mock"]` configuration and `MockGoldTierConnector` composition;
  no active PingFed/live adapter.
- Persistence: memory default; explicit Mongo mode with schema v3, CAS, strict mode
  separation, and no fallback.
- Identity: repository-backed synthetic profiles/teams plus process-local opaque
  sessions; no production SSO/IdP.
- Camunda: no runtime module, adapter, configuration, or composition.
- Frontend: one session-memory QueryClient; user-scoped keys, Director team-filter
  identity, AbortSignal cancellation, and cache clearing on auth transition/401.

## Existing governance inventory and drift

| Surface | Keep/reference | Current issue addressed |
|---|---|---|
| `AGENTS.md` | Refactor, preserve critical rules | Too much mutable state; lacks new start order/change classes |
| `docs/PROJECT_CONTEXT.md` | Reference | Valuable history but too large for every task start |
| `docs/architecture/*` | Reference/index | Phase-local detail; current owner map is fragmented |
| `docs/CODEX_WORKFLOW.md` | Reference/supersede workflow entry | Predates explicit change-class matrix |
| branch protocol and pre-PR checklist | Reference | Specialized Git detail remains canonical |
| contracts/decision/open-question docs | Reference | Remain authority for scoped questions |
| phase reports/prompts | Historical, consult on demand | Must not drive current truth by recency alone |
| repository skills | Retain and index | Missing architecture/provider/persistence/cache/closeout procedures |
| `pre_pr_check.py`, secret checker, CI | Extend narrowly | No current-state or architecture checks |

Stale/duplicated material will not be moved or deleted. New canonical entry documents
will label phase documents as historical/detail evidence, link existing specialist
owners, and state source precedence explicitly.

## AGENTS.md migration inventory

| Existing rule/category | Planned canonical location | Directly retained? |
|---|---|---|
| bounded assigned scope/no guessing | `AGENTS.md`, workflow | yes |
| latest-main branch protocol/no main development | `AGENTS.md`, workflow, integration skill | yes |
| no reset/rebase/stash/clean/force/broad staging | `AGENTS.md`, branch protocol | yes |
| source/contract/sponsor hierarchy | `AGENTS.md`, workflow | yes |
| implementation/non-goals/provider truth | `PROJECT_STATE.md` | concise prohibition retained |
| architecture dependency direction | `ARCHITECTURE.md` | core prohibitions retained |
| secret/KYC/PII/private artefact safety | `AGENTS.md`, tooling guide, security skill | yes |
| current sponsor-confirmed GoldTier facts | decisions/contracts/state | authority rule retained |
| test expectations/definition of done | workflow/change matrix | concise requirement retained |
| independent QG/pre-PR | workflow and skills | yes |
| physical Mongo allowlist/`clm_poc` protection | `AGENTS.md`, persistence skill/workflow | yes |

Before editing `AGENTS.md`, the implementation will compare every current paragraph to
this table. The implementation report will contain the required final migration proof.

## Exact file map and necessity

### Create

- `docs/PROJECT_STATE.md`: concise verified operational truth plus structured metadata.
- `docs/ARCHITECTURE.md`: current canonical bounded-context/owner/dependency map.
- `docs/DEVELOPMENT_WORKFLOW.md`: lifecycle, roles, classes, checks, stops, ADR/sponsor gates.
- Five `.agents/skills/*/SKILL.md` files: procedural high-risk change playbooks.
- `scripts/dev_context.py`: safe task-start readout.
- `scripts/check_project_state.py`: conservative metadata/source drift validator.
- `scripts/check_architecture.py`: narrow tracked-source dependency/composition guards.
- `tests/test_dev_context.py`, `tests/test_check_project_state.py`,
  `tests/test_check_architecture.py`: synthetic safety/negative/baseline tests.
- `docs/decisions/ADR_TEMPLATE.md`: honest future-decision template.
- `docs/development/TOOLING_AND_MCP.md`: tool/account/secret boundaries.
- `.ai-pipeline/reports/DEVELOPMENT_GOVERNANCE_CONTEXT_SETUP.md`: implementation evidence.

### Modify

- `AGENTS.md`: concise constitutional start point without losing safety rules.
- `.agents/skills/README.md`: non-overlapping trigger/composition matrix.
- `scripts/pre_pr_check.py` and `tests/test_pre_pr_check.py`: run both governance checks
  in a deterministic source-validation section, if isolated integration stays green.
- `.github/workflows/ci.yml`: run governance unit tests and direct checks once in security.
- `.github/pull_request_template.md`: practical change/governance evidence.
- `README.md`, `.ai-pipeline/README.md`, `docs/architecture/README.md`: start-here links.
- `docs/decisions/DECISION_LOG.md`: append ADR usage/index guidance without fabricating history.

No existing file is moved. Existing architecture, context, contracts, phase prompts,
reports, and role files remain specialist/history references.

## Deterministic script design

### Shared safety principles

- Standard library only; explicit repository root; no imports from application config.
- Never load `.env`, environment secret values, Mongo, network, provider, or untracked content.
- Git subprocesses use argument arrays, `shell=False`, UTF-8 replacement, and
  `GIT_OPTIONAL_LOCKS=0`.
- Status uses exactly `--short --untracked-files=no`.
- Exit `0` on success, `1` on detected drift, `2` on tool/input failure where useful.

### `dev_context.py`

- Read safe Git refs/relationship, tracked status, declared project-state metadata,
  provider matrix rows, sponsor question IDs, tracked repository skill names, workflow
  and pre-PR references.
- Output fixed labels and stable ordering; no arbitrary recursive traversal.

### `check_project_state.py`

- Validate required headings and a fenced TOML-like/JSON metadata block with baseline
  commit, verified date, provider names/modes, persistence/auth/Camunda declarations.
- Verify baseline is a 40-hex commit reachable from `origin/main`, not equal to feature
  HEAD.
- Compare narrow facts against parsed `Settings` literals and composition/import
  markers. Reject documented live GoldTier/Camunda and unknown provider names.
- Avoid policing free-form English.

### `check_architecture.py`

- Inspect only an explicit tracked file set/rules.
- Prohibit `app.persistence`/`app.mongo` imports in API route modules.
- Prohibit backend persistence imports in frontend sources.
- Assert one canonical Decimal ownership implementation file and prohibit a second
  domain ownership implementation by declared marker.
- Assert dormant BizFile is not imported/composed by `composition.py`.
- Assert GoldTier composition remains Mock while configuration is Mock-only.
- Rules will report names, rationale, and exact file; tests will cover every violation.
  More semantic rules remain manual architecture-review items.

## Skill validation strategy

Each skill is created sequentially. Before its file exists, run a pressure scenario
against a delegated agent that combines urgency, authority pressure, and a tempting
shortcut. Record the failure/rationalization in the implementation report. Then create
only that skill, rerun a matched application/pressure scenario with the skill supplied,
and refine before starting the next skill. No skill is treated as validated only because
its headings exist.

## Test and CI/pre-PR strategy

- Synthetic temporary repositories and temporary trees prove Git metadata handling,
  mismatch failures, architecture violation detection, no `.env` reads, no untracked
  dependency, no environment-secret output, and no mutation.
- Current repository tests prove baseline acceptance for state and architecture checks.
- Add one focused `unittest` discovery command to CI security, then direct checker runs.
- Integrate direct checks into `pre_pr_check.py` through a small subprocess helper whose
  output is summarized without secret values. Dirty-tree failure remains expected for
  this uncommitted handoff; direct governance checks still run separately.
- No physical Mongo, lifecycle, or product suite is required because app runtime is
  untouched.

## Documentation drift strategy

- `PROJECT_STATE.md` records `verified_main_sha`, not feature HEAD.
- Closeout skill updates verified facts on an accepted main/squash result; before exact
  merge SHA exists it records `pending_merge` and the source branch/base without
  inventing a commit.
- Checkers validate source-correlated structured metadata; prose is reviewed through
  architecture/phase closeout skills.
- Phase history remains immutable evidence and is not force-synchronized.

## Implementation slices

1. Author and validate `PROJECT_STATE.md`, `ARCHITECTURE.md`, and workflow.
2. Run baseline pressure test, create, and post-validate each of five skills sequentially.
3. Refactor `AGENTS.md` and update skill/index/start-here documentation.
4. Implement three scripts and focused tests.
5. Add ADR/tooling/PR surfaces and narrow CI/pre-PR wiring.
6. Run verification, inspect latest-main drift, and write the final implementation report.
7. Run final Git/data safety inventory and stop uncommitted for independent QG.

## Explicit non-goals

- No app runtime, business logic, public API, schema, dependency, provider, database,
  authentication, cache, or UI behavior change.
- No RAG/vector database, agent framework, policy engine, repo MCP server, guessed MCP
  config, sponsor-rule inference, or architecture auto-rewrite.
- No external account authentication, credential/certificate provisioning, Mongo test,
  GitHub settings change, commit, push, PR, merge, or branch cleanup.
- No historical ADR fabrication or wholesale historical documentation rewrite.

## Risks and controls

| Risk | Control |
|---|---|
| New docs become another stale layer | Structured minimal state plus source-backed checker and closeout skill |
| Checker false positives | Narrow explicit rules, synthetic negative tests, baseline-green requirement |
| Safety rule lost in AGENTS refactor | Migration inventory and final old-to-new proof |
| Mock/sandbox overstated as live | Source-derived matrix and explicit constitutional prohibition |
| CI duplication/latency | Standard-library checks run once in security and via pre-PR orchestration |
| Skill ambiguity | Trigger/non-trigger/precedence matrix and pressure validation |
| Missing external audit | Record missing advisory evidence; never lower source authority |
| Squash-merge SHA paradox | Store verified main baseline and allow pending-merge closeout state |

## Stop conditions

Stop the affected slice if current source cannot support a documented fact, an
architecture guard cannot be narrow and baseline-green, a sponsor rule would need to be
invented, a unique safety rule cannot be mapped, CI wiring requires product dependency
changes, or Git/main/protected-artifact safety changes. Completion requires fresh direct
checker/test evidence and an uncommitted feature-branch working tree ready for
independent QG.
