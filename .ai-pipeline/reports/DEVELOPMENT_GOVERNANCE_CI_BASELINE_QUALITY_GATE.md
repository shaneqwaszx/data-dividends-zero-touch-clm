# Development Governance CI Baseline Quality Gate

## Executive Result

**PASS.** This independent, review-only re-gate verifies the uncommitted PR #32
remediation. It corrects the `security` job's historical-Git availability and replaces
the impossible permanent-equality interpretation of `verified_main_sha` without
weakening the source-to-state checks required by DGQG-001. No remediation was made in
this gate.

## Baseline and Scope

- Branch: `codex/dev-governance-context`
- HEAD / origin feature: `1eeba1b04eca04cec50e6b1016fd057103b38636`
- origin/main: `fd760e4f74019002f5f9374467cc6a701f6cf585`
- Merge base: `fd760e4f74019002f5f9374467cc6a701f6cf585`
- Change classification: `CI_TOOLING` and governance-check regression tests.

The reviewed implementation diff is limited to:

- `.github/workflows/ci.yml`
- `scripts/check_project_state.py`
- `tests/test_check_project_state.py`

The remediation evidence report
`.ai-pipeline/reports/DEVELOPMENT_GOVERNANCE_CI_BASELINE_REMEDIATION.md` was reviewed
as evidence, not authority. No application/runtime/business, provider, persistence,
authentication, dependency, or Camunda file changed.

## CI History Verdict

**PASS.** Only the `security` job's `actions/checkout@v4` step now specifies
`fetch-depth: 0`; all other checkout steps remain unchanged. Repository permissions
remain `contents: read`, no secret/permission scope was broadened, and the existing
repository-root governance tests and scripts remain wired in the job.

The checkout action's documented full-history behavior fetches all branch history,
including the `origin/main` ref. That supplies both the historical verified baseline
for `git cat-file` and the reference required by `git merge-base --is-ancestor`, even
when a pull-request trigger checks out a detached synthetic merge commit.

## Baseline-Semantics Verdict

**PASS.** `verified_main_sha` must be lowercase 40-hex, resolve as a commit, and be an
ancestor of `origin/main`. A nonzero `git cat-file` or `git merge-base --is-ancestor`
result produces a validation failure; a missing/unavailable `origin/main` therefore
cannot silently pass. The obsolete `origin/main != verified_main_sha` equality failure
has been removed. `git show` date failures also fail through an unparsable baseline
date. The checker creates no refs and performs no Git mutation.

Direct adversarial fixture results:

| Case | Result |
| --- | --- |
| A — verified baseline equals `origin/main` | PASS |
| B — `origin/main` is a descendant | PASS |
| C — existing but unrelated verified baseline | FAIL as required |
| D — nonexistent verified baseline | FAIL as required |
| Missing `origin/main` | FAIL as required |

## DGQG-001 and Source-Drift Verdict

**PRESERVED.** The unchanged checker continues to validate metadata schema, case
envelope schema, ISO date and baseline-date relationship, provider metadata and
configured defaults, Mock GoldTier composition, persistence modes/default, bootstrap
identity composition, process-local sessions, and Camunda absence. An independent
fixture changed the current GoldTier configuration default to an unreviewed `live`
mode while retaining Mock project-state metadata; validation failed. Descendant-main
tolerance therefore does not accept a material current source/state contradiction.

## Documentation Verdict

**PASS.** `PROJECT_STATE.md`, `DEVELOPMENT_WORKFLOW.md`, and the remediation report
describe `verified_main_sha` as an inspected historical main baseline/provenance
anchor. They do not require a future squash-merge SHA to be predicted. The workflow
still requires a refresh after accepted meaningful state changes when the inspected
main commit is known.

## Regression and Static Evidence

| Check | Result |
| --- | --- |
| `test_check_project_state.py` | 16 passed |
| `test_check_architecture.py` | 12 passed |
| `test_dev_context.py` | 9 passed |
| `test_pre_pr_check.py` | 41 passed |
| `test_check_secrets.py` | 8 passed |
| `python scripts/check_project_state.py` | PASS |
| `python scripts/check_architecture.py` | PASS |
| `python scripts/dev_context.py` | PASS |
| Ruff on changed Python | PASS |
| Ruff format check on changed Python | PASS |
| CI YAML parse | PASS |
| `git diff --check` before report creation | PASS |

The fixture suites require temporary Git repositories. The default sandbox rejected
those Git initializations; the recorded passing executions used elevated permission
solely for disposable test fixtures. No production repository state or protected data
was accessed.

## Findings

- Critical: none.
- High: none.
- Medium: none.
- Low: none.

## Required Fixes

None.

## Readiness

The remediation is ready to be committed by its implementer and then pushed to update
PR #32, subject to the owner workflow. This verdict does not authorize commit, push,
PR update, merge, a new phase, live ACRA verification, or real GoldTier integration.

## Git and Safety Status

The implementation working tree remains uncommitted and unstaged. This report is the
only gate-created file. No implementation fix, commit, push, merge, branch switch,
reset, rebase, stash, clean, force operation, `.env` access, secret/hash output, Mongo
connection/URI access, certificate/private-key access, `clm_poc` access, or protected
unrelated-artifact access occurred.
