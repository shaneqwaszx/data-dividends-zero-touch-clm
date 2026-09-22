# PR #52 E2E Port-Release Remediation

Date: 2026-09-22

Branch: `integration/acra-teammate-reconciliation`

Base and current `origin/main`: `ef338c9b7926a298e8987acb975fd93c96ed2bfb`

Original PR head: `cff6e2f49d9b84e5ac5d66b3e7424bebf0e21ace`

Change class: `CI_TOOLING` with supporting tests and this report.

## Historical CI Evidence

- Push run `35720468238`, event `push`, head `cff6e2f49d9b84e5ac5d66b3e7424bebf0e21ace`: `e2e` failed; `backend`, `frontend`, `security`, `phase12-mongo`, and `demo-lifecycle-windows` passed.
- PR run `35725121231`, event `pull_request`, head `cff6e2f49d9b84e5ac5d66b3e7424bebf0e21ace`: the same job state and failure recurred independently.
- In both E2E jobs, isolated lifecycle 1/7 passed. Lifecycle 2/7 then failed in the unchanged strict `_assert_ports_available()` bind proof with `OSError: [Errno 98] Address already in use`, surfaced as `RuntimeError: An assigned E2E loopback port is already occupied`.

These historical runs remain failures; this remediation does not relabel them.

## Root Cause

The proven mechanism is a lifecycle-owner release-proof gap. On POSIX, `OwnedProcess.stop()` signals the task-owned process group and waits for its process-group leader. `run()` then returned immediately after stopping the Playwright, frontend, and backend owners. It did not positively prove that both exact listener ports had become bindable before the next isolated lifecycle began.

The two CI runs show the resulting recurrence generator: lifecycle 1 completed, cleanup returned, and lifecycle 2's strict pre-start probe immediately observed an assigned port still non-bindable. The historical logs do not identify which of the two ports was occupied and cannot distinguish a briefly surviving signalled group member from kernel socket teardown after process exit. The correction therefore addresses the established owner-level defect without claiming an unevidenced lower-level mechanism.

The workflow invocation itself is not the defect. `.github/workflows/ci.yml` continues to run the repository-owned `python scripts/run_e2e.py` command unchanged.

## Source Changes

### `scripts/run_e2e.py`

- Added `_wait_for_ports_available()` at the existing lifecycle owner.
- The helper repeatedly invokes the unchanged `_assert_ports_available()` proof for both exact assigned loopback ports.
- Polling is condition-based at 50 ms and bounded by both the lifecycle deadline and a 10-second cleanup cap.
- `run()` now records its result, stops all task-owned processes in the existing reverse order, then requires the port-release proof before returning.
- A release timeout returns E2E failure with only the safe backend/frontend port numbers; it never proceeds as a successful lifecycle.
- The next lifecycle retains its independent final `_assert_ports_available()` pre-start proof.

### `tests/test_run_e2e.py`

The existing runner test owner now covers:

- immediately available ports;
- a genuinely occupied port still failing strict preflight;
- event-synchronised delayed release followed by success;
- deterministic bounded timeout for a never-released port;
- distinct backend/frontend port enforcement;
- closure of every temporary probe socket;
- reverse process cleanup completing before the release proof;
- release-proof failure overriding apparent Playwright success; and
- unchanged isolated-selection sequencing and fail-fast behavior.

## Why This Is Not a Sleep or Bypass

- There is no unconditional delay. The first strict bind proof succeeds immediately when both ports are available.
- A short sleep occurs only between failed condition probes and never establishes success.
- Success requires both exact assigned ports to pass the original strict bind operation.
- `_assert_ports_available()` is unchanged and remains the pre-start gate.
- No `SO_REUSEADDR`, occupied-port suppression, random-port workaround, test retry, or workflow retry was introduced.
- No unrelated process is discovered or killed. Windows and POSIX task-owned process-group stop behavior is unchanged.

## Verification

All evidence below was produced locally on the current candidate source unless noted.

| Check | Result |
|---|---|
| RED: `python -m unittest tests.test_run_e2e -v` before implementation | Expected failure: 4 new tests failed/errored because `_wait_for_ports_available` did not exist |
| Final `python -m unittest tests.test_run_e2e -v` | PASS — 23/23 |
| `python -m ruff check scripts/run_e2e.py tests/test_run_e2e.py` | PASS |
| `python scripts/check_secrets.py` | PASS |
| `python scripts/check_tooling_config.py` | PASS |
| `git diff --check` | PASS |
| `python -m unittest tests.test_demo_lifecycle_windows -v` | PASS — 23/23 in 369.116 seconds |
| `python scripts/run_e2e.py` outside the restricted process sandbox, consecutive run 1 | PASS — 7/7 dynamically discovered isolated lifecycles |
| Same exact command, consecutive run 2 | PASS — 7/7 |
| Same exact command, consecutive run 3 | PASS — 7/7 |

The first sandboxed full-E2E attempt was blocked before browser startup by local `esbuild` `spawn EPERM`. The identical permitted rerun and two consecutive repeats passed. This was recorded as a capability restriction, not as candidate success.

## Safety and Scope Invariants

- Task-owned process groups remain the only processes stopped.
- Windows cleanup semantics, POSIX process-group signalling, timeout bounds, output sanitisation, generated credentials, loopback-only routing, and browser-network restrictions remain intact.
- Failed or uncertain cleanup remains failure; a cleanup timeout cannot become success.
- Every configured Playwright selection still receives an independent backend/frontend/test lifecycle, with no test reduction or retry.
- No API/model/type, schema, connector, configuration, business rule, mapping, auth/security, persistence, architecture, provider-status, CI workflow, or dependency behavior changed.
- ACRA routing, BizFile decoding, Garden Business fixture/behavior, ownership/UBO, provider readiness, priority, Mongo, policy, responsive UI, and Cases table behavior are unchanged.
- No Phase 22 work was performed.

## Self-Review

The final diff was challenged against the original dual-CI failure and all requested adverse cases. The release proof is positive, exact-port, bounded, fail-closed, and socket-closing. The strict preflight remains. No fixed-sleep-only repair, reuse-option bypass, broad process kill, or product-facing delta is present. The original failure class is prevented at its canonical lifecycle owner.
