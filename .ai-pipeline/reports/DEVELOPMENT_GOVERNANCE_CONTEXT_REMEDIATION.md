# Development Governance and Context — Targeted Remediation

## Baseline and scope

- Branch: `codex/dev-governance-context`
- Accepted base, starting HEAD, fetched `origin/main`, and merge base:
  `62a7d80324b40308e8cb3feba806b73a24c9c6ac`
- Change classes: `CI_TOOLING` and `DOCS_ONLY`
- Scope: DGQG-001 through DGQG-005 only
- Runtime, business logic, API contracts, persistence implementation, provider behavior,
  frontend behavior, authentication behavior, dependencies, and CI wiring: unchanged

## Finding closure

| Finding | Status | Remediation |
|---|---|---|
| DGQG-001 | CLOSED | Structured state fields are type/value/source correlated with adverse tests. |
| DGQG-002 | CLOSED | Brittle text rules were replaced or narrowed to AST/import syntax checks. |
| DGQG-003 | CLOSED | `app/main.py` is documented and tested as an assembly-only composition-root exception. |
| DGQG-004 | CLOSED | Important Git/state/error edge cases now have direct tests. |
| DGQG-005 | CLOSED | Pre-PR governance failures report bounded stdout, stderr, and exit status. |

## Exact remediation files

- `docs/PROJECT_STATE.md`
- `docs/ARCHITECTURE.md`
- `.agents/skills/phase-closeout-context-refresh/SKILL.md`
- `scripts/check_project_state.py`
- `scripts/check_architecture.py`
- `scripts/dev_context.py`
- `scripts/pre_pr_check.py`
- `tests/test_check_project_state.py`
- `tests/test_check_architecture.py`
- `tests/test_dev_context.py`
- `tests/test_pre_pr_check.py`
- `.ai-pipeline/reports/DEVELOPMENT_GOVERNANCE_CONTEXT_REMEDIATION.md`

The independent QG report was not modified.

## DGQG-001 — structured project state

### Root cause

The original checker parsed the bounded JSON block but validated only its baseline,
provider-name inventory, three provider defaults, GoldTier Live prohibition, and
Camunda absence. Metadata schema/date, canonical case-envelope version, persistence,
identity, and most provider mode/classification values had no deterministic contract.

### Fix and structured format

`PROJECT_STATE.md` retains one human-readable fenced `json project-state` block; no
sidecar source of truth or parser dependency was added. Its validated fields are:

- metadata `schema_version = 1` and `verification_status = verified-against-main`;
- `case_envelope_schema_version`, statically compared with
  `CASE_SNAPSHOT_SCHEMA_VERSION` in persistence models;
- ISO `verified_date`, which cannot predate the baseline commit date;
- `verified_main_sha`, which must be a real commit and the current fetched
  `origin/main` baseline;
- exact current provider name/mode/classification records, with configurable defaults
  also compared with `Settings` `Literal` annotations/defaults;
- persistence default and supported modes, statically compared with
  `clm_persistence_mode`;
- bootstrap-account/process-local-session/no-production-SSO classification, with
  bootstrap and in-process session structure checked through Python AST;
- current Camunda absence.

The baseline means the synchronized main commit inspected for the snapshot. Feature
HEAD may be ahead or detached while `origin/main` remains that baseline. A missing,
unreachable, malformed, or superseded main baseline fails and requests context refresh;
feature HEAD equality is never required. The closeout skill now explicitly includes
the metadata schema, case-envelope version, persistence, and identity/session fields.

### Tests

Fifteen project-state tests cover the real baseline, wrong metadata and case schema
versions, malformed/nonexistent SHA, invalid/pre-baseline dates, main advancement,
persistence contradictions, identity contradiction, provider contradiction, feature
HEAD advancement, detached HEAD, harmless prose, commit-date timezone tolerance, and
read-only/secret-safe behavior.

## DGQG-002 — architecture checker

### Root cause and redesign

The frontend rule scanned arbitrary source substrings; Python `from package import
module` imports lost the imported symbol; and GoldTier configuration depended on one
exact source line. `main.py` was also grouped with ordinary API modules.

| Rule | Invariant protected | Detection technique | False-positive risk | Intentional limitation / false-negative risk |
|---|---|---|---|---|
| `API_PERSISTENCE_BOUNDARY` | Ordinary API modules do not import concrete persistence implementations. | Python AST expands `import x` and `from x import y`, including aliases; known concrete persistence modules are matched. | Low; persistence error types remain allowed and `main.py` is excluded. | File naming defines the mechanically checked API set; semantic route-body queries remain review-owned. |
| `FRONTEND_BACKEND_BOUNDARY` | Frontend does not depend on backend persistence. | Comment-aware static ES import-specifier extraction. | Low; strings, comments, variable names, and local presentation imports are ignored. | Dynamic imports and CommonJS calls are not broadly policed without a real parser. |
| `OWNERSHIP_CANONICAL_OWNER` | The canonical domain ownership module remains unique. | Tracked path inventory scoped to domain ownership filenames. | Low. | Semantic duplication under unrelated names requires architecture review. |
| `DORMANT_BIZFILE` | BizFile does not enter runtime composition. | Python AST import inspection only in the runtime composition owner. | Low; docs/tests/comments are ignored. | Indirect factory/reflection wiring requires independent review. |
| `MOCK_GOLDTIER_ONLY` | Settings and current composition remain Mock-only. | AST parsing of `Settings` `Literal`/default plus imported-constructor instantiation, including aliases. | Low; whitespace, wrapping, quote style, and import aliases are tolerated. | A future alternate composition design requires an intentional checker/architecture update. |

Removed or narrowed behavior:

- removed arbitrary frontend substring scanning;
- removed `main.py` from the ordinary API import rule;
- narrowed persistence imports to concrete implementation/schema/composition modules,
  retaining legitimate persistence error projection;
- replaced exact GoldTier annotation text with AST semantics;
- replaced BizFile and Mock GoldTier raw markers with composition-scoped AST evidence.

Twelve architecture tests cover current baseline, both prohibited Python import forms,
composition-root wiring, frontend false-positive cases and a real import, BizFile
composition, GoldTier formatting/alias tolerance and semantic Live addition, ownership
duplication, and read-only/secret-safe behavior.

## DGQG-003 — composition root

`docs/ARCHITECTURE.md` now separates HTTP/API transport from the application composition
root. `apps/backend/app/main.py` may import concrete implementations only for dependency
construction/application assembly. It may not perform persistence queries, place
business behavior in route handlers, or bypass service/repository boundaries. The
static dependency diagram and bounded-context table reflect this distinction. The
checker enforces only the reliable file/import subset and documents that semantic
architecture remains review-owned.

## DGQG-004 — development context

`dev_context` resolves the repository top level from either the root or a subdirectory,
renders an empty branch as `DETACHED`, and fails safely outside a Git worktree. Nine
tests cover root invocation, subdirectory resolution, detached HEAD, missing
`origin/main`, missing/malformed state, tracked dirtiness, Git lookup failure, and the
existing no-env/no-untracked/no-mutation guarantees.

## DGQG-005 — pre-PR diagnostics

Governance subprocess failure remains fail-closed. The report now includes the exit
code and separately labelled, bounded stdout and stderr (2,000 characters each), or an
explicit no-diagnostics message. It continues to use argument arrays and `shell=False`.
Four focused cases prove stderr-only, stdout-only, combined failure, and success.

## Verification

- Project-state tests: PASS — 15
- Architecture tests: PASS — 12
- Development-context tests: PASS — 9
- Complete pre-PR test suite: PASS — 41, executed in bounded batches for host timing
- Secret-scanner tests: PASS — 8
- Governance regression aggregate: PASS — 85 tests across the five suites
- `python scripts/check_project_state.py`: PASS
- `python scripts/check_architecture.py`: PASS
- `python scripts/dev_context.py`: PASS
- Ruff check and format check on all eight changed/new Python files: PASS after formatting
- CI YAML: PASS; not changed during remediation and existing wiring retained
- `git diff --check`: PASS; CRLF conversion advisories only
- Full `pre_pr_check.py`: intentionally not run on the uncommitted QG handoff tree
- Product/backend/frontend/lifecycle/physical Mongo/live-provider suites: not run; no
  application or persistence runtime surface changed

## Remaining limitations and readiness

The architecture checker intentionally proves only narrow mechanical syntax/path
invariants. It does not replace semantic architecture review and does not attempt a
full TypeScript parser, semantic duplicate-owner detection, or runtime call-graph proof.
These are documented limits, not silent guarantees. The structured project-state
checker deliberately requires refresh when fetched `origin/main` advances, while
allowing feature HEAD commits and detached feature/test checkouts.

The obsolete raw frontend substring check, exact GoldTier source-line check, and
`main.py`-as-ordinary-route path were retired in place. A scoped lingering-reference
audit found no remaining execution path for those checks. No compatibility fallback or
second checker owner was retained.

No Critical, High, or Medium remediation finding remains. Independent re-quality-gate
is still required and remains separate from this remediation run. The working tree is
intentionally uncommitted and is not ready for commit, push, or PR during this run.
