# Phase 15A — Targeted CI Remediation

## CI failure and cause

GitHub CI's security-job governance unit-test step ran 37 tests and failed five
synthetic-project-state fixture tests. The fixture created a new synthetic Git
baseline at test execution time but hard-coded `verified_date` as `2026-09-15`.
The checker correctly rejects a verification date that materially predates the
baseline commit, so the fixture became invalid as calendar time advanced.

## Correction

`ProjectStateCheckerTests._fixture()` now obtains the synthetic source commit SHA,
then derives `baseline_date` from that same commit with `git show -s --format=%cs`.
It places that date in fixture metadata as `verified_date`. This is deterministic
against the generated baseline, independent of the wall clock, and preserves all
existing ancestry and one-day timezone-tolerance assertions.

## Preserved semantics and non-goals

No checker validation, tolerance, real project-state metadata, runtime/business
behavior, API, schema, provider, configuration, dependency, or CI workflow changed.
The correction is test-fixture-only; the existing stale-date negative test remains.

## Verification

- `python -m unittest tests.test_check_project_state -v` (project virtual environment):
  PASS — 16 tests.
- `python -m unittest tests.test_dev_context tests.test_check_project_state
  tests.test_check_architecture -v` (project virtual environment): PASS — 37 tests.
- `python scripts/check_project_state.py`: PASS.
- `python scripts/check_architecture.py`: PASS.
- `python scripts/dev_context.py`: PASS; reports the expected Phase 15A branch,
  feature head, origin/main, and provider metadata.
- `git diff --check`: PASS; no whitespace errors.
- `git diff -- scripts/check_project_state.py`: no output; checker source unchanged.

The initial global-interpreter invocation could not import the repository namespace
because this Windows machine has an unrelated installed `tests` package. The project
virtual environment resolves the repository package and was used for the test evidence;
CI's clean runner does not have that local collision.

## Git and data safety

No stage, commit, push, merge, rebase, reset, stash, clean, amend, or branch switch is
part of this remediation. No `.env`, secret, Mongo URI, private key/certificate,
`clm_poc`, or protected unrelated artifact is accessed.

## Required next action

An independent targeted re-quality-gate review is required before an owner commits or
pushes this remediation.
