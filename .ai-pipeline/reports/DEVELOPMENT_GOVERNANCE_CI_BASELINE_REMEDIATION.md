# Development Governance CI Baseline Remediation

## Scope

This targeted remediation addresses the `security` job failure on PR #32 only. It is
not a feature, application, provider, persistence, authentication, dependency, or
Camunda change. The working tree remains intentionally uncommitted for targeted
independent quality review.

## Failure evidence and root cause

- PR: #32 (`codex/dev-governance-context` -> `main`)
- Failing workflow run/job: `34937804764` / `security`
- First causal test: `ProjectStateCheckerTests.test_accepts_current_repository_baseline`
- Observed error: `verified_main_sha must exist and be reachable from origin/main`

The security job used the default `actions/checkout@v4` shallow checkout
(`fetch-depth: 1`) of the synthetic pull-request merge ref. The historical
`verified_main_sha` anchor was therefore absent from the runner Git object graph.

The checker also treated any descendant `origin/main` commit as a failure. That was a
self-referential freshness rule: a tracked `PROJECT_STATE.md` cannot name the future
squash-merge commit that will contain it.

## Corrected semantics

`verified_main_sha` is a historical verified-main anchor. It must be a lowercase
40-hex commit, exist locally, and be an ancestor of `origin/main` when that ref is
available. A descendant `origin/main` is valid; an unrelated baseline remains a
failure. Commit-date validation and all current source-to-structured-state checks
remain unchanged.

The security checkout alone now uses `fetch-depth: 0`, providing the history required
for `git cat-file` and `git merge-base --is-ancestor`. Other CI jobs remain shallow.

## Files changed

- `.github/workflows/ci.yml`
- `scripts/check_project_state.py`
- `tests/test_check_project_state.py`
- this report

## Verification

- Project-state tests: 16 passed, including descendant-main acceptance and unrelated
  baseline rejection.
- Architecture tests: 12 passed.
- Development-context tests: 9 passed.
- Pre-PR tests: 41 passed.
- Secret-scanner tests: 8 passed.
- Direct project-state, architecture, and development-context checks: passed.
- Ruff and Ruff format on changed Python: passed.
- CI YAML parse: passed.
- `git diff --check`: passed.

The adversarial coverage proves: equal baseline/main passes; descendant main with an
unchanged current state passes; unrelated baseline fails; and provider/state metadata
drift fails.

## Non-goals and next step

No application runtime/business logic, provider, Mongo schema, authentication,
dependency, or Camunda content changed. The remediation is ready for targeted
independent quality gating; it is not authorized for commit, push, CI rerun, or merge.
