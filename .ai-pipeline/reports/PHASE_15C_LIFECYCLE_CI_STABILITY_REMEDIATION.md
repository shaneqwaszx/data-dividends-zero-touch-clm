# Phase 15C Windows Lifecycle CI Stability Remediation

Date: 2026-09-20
Change class: `CI_TOOLING`
Branch: `phase/15c-frontend-navigation`
Starting HEAD: `3abecd673726200e8bcd8eb333c7d384d798eb57`
Baseline / current `origin/main`: `4d1f646b3445c8d88df44dbc68abd109fe4d7aa5`

## Outcome

Root-cause classification: **A — the Python test identity comparison was stricter
than the production lifecycle identity contract.** The cross-source timestamp precision
or formatting variation described by classification D is the tolerated trigger, not a
separate launcher defect.

The remediation is limited to `tests/test_demo_lifecycle_windows.py`. The production
controller `scripts/demo_lifecycle.ps1` is unchanged.

## GitHub evidence

- Push run `35479055483` failed only job `105993373958`
  (`demo-lifecycle-windows`).
- Pull-request run `35479069804` passed every job, including Windows lifecycle job
  `105993413953`.
- Both workflow records identify head SHA
  `3abecd673726200e8bcd8eb333c7d384d798eb57`. The pull-request checkout used GitHub's
  merge commit over the same already-integrated base; no source delta explains the
  lifecycle result difference.
- Both Windows jobs used runner `2.337.0`, image `windows-2025-vs2026`
  `20260907.229.1`, CPython `3.12.10`, Node.js `22.23.2`, and npm `10.9.8`.
- The failed run reported frontend launcher and listener PID `2624`. The listener
  identity matched while the launcher identity did not. The successful same-tree run
  completed `18/18` lifecycle tests.

## Causal chain

`assert_owned_endpoints_healthy_within` built separate expected launcher and listener
records, then required raw equality between each expected `creation_time_utc` string and
the current batched CIM observation. The launcher and listener can be the same PID while
their independently captured creation-time strings differ harmlessly in offset or
sub-millisecond precision. One stored representation can therefore compare unequal and
the other equal against the same current observation.

The production owner deliberately does not use raw string equality.
`Test-SameCreationTime` normalizes offset-bearing values to UTC and accepts an absolute
difference of at most one millisecond, retaining PID, executable, role, ancestry, and
PID-reuse protections. The Python post-rejection verifier duplicated that ownership
decision with a stricter contract.

No evidence showed a changed PID, changed executable, dead process, listener handoff,
or launcher replacement. A real replacement would also not explain why two checks of
the same PID and current observation disagreed only according to which stored record
was compared.

## Correction

The test now has one reusable process-identity helper that requires:

- the same PID;
- the same case-normalized executable path;
- valid offset-bearing ISO-8601 creation times;
- UTC-normalized creation instants no more than one millisecond apart.

Parsing uses integer 100-nanosecond ticks so `1.0001 ms` cannot be rounded down to the
accepted boundary. Missing, malformed, timezone-less, out-of-range-offset, or otherwise
invalid values fail closed.

The bounded health verifier retains its existing monotonic deadline, poll interval,
per-probe identity recheck, endpoint recovery requirement, and rejection of a success
completed after the deadline. No timeout, sleep, retry, or lifecycle action changed.

## Deterministic coverage

Coverage now proves:

- seven-digit UTC versus six-digit UTC for the same instant: pass;
- UTC versus an explicit offset for the same instant: pass;
- less than one millisecond: pass;
- exactly one millisecond: pass;
- more than one millisecond: fail;
- timezone-less or malformed input: fail closed;
- different executable, changed PID, or missing process: fail;
- same frontend launcher/listener PID with harmless representation differences: both
  checks pass;
- the same pair with over-tolerance creation time, executable replacement, PID change,
  or disappearance: both checks fail.

The existing deterministic bounded-polling cases continue to prove transient recovery,
permanent unavailability, dead/replaced processes, replacement during a probe, no late
success, and continued checking of both endpoints.

## Verification

- Regression-first timestamp/helper run before implementation: `3 tests`, `10` expected
  `NameError` errors because the new helper did not yet exist.
- Identity timestamp matrix after implementation: `3/3 PASS`.
- Focused bounded verifier plus hostile real-process ownership test: `1/1 PASS` in
  `43.164s`.
- Exact previously failing test: `1/1 PASS` in `60.796s`.
- Complete Windows lifecycle suite, executed once: `18/18 PASS` in `280.403s`.
- Ruff on the changed Python file: PASS.
- Governance unit bundle (`test_pre_pr_check`, `test_dev_context`,
  `test_check_project_state`, `test_check_architecture`): `79/79 PASS` in
  `61.354s` after rerunning with permission to create disposable temporary Git
  repositories.
- `check_project_state.py`: PASS.
- `check_architecture.py`: PASS.
- `check_tooling_config.py`: PASS.
- `check_secrets.py`: PASS.
- `git diff --check`: PASS (Git emitted only the existing LF-to-CRLF working-copy
  warning).

The first sandboxed real-process focused attempt was not product evidence: Windows
process termination was denied by the sandbox and the supported exact-ownership stop
path cleaned the test-owned partial startup. The test then passed once with the required
host process permissions. The first sandboxed governance unit attempt was likewise
invalidated by temporary-directory permission errors; its exact authorized rerun passed
all 79 tests.

## Scope and impact

No API/model/type, persistence schema, connector, configuration, business rule,
mapping, authentication/security, architecture, provider status, frontend navigation,
Playwright, Mongo, backend, or frontend production behavior changed. No lifecycle
timeout was broadened and no retry-until-green behavior was added.

Status: **READY FOR INDEPENDENT FOCUSED RECHECK**
