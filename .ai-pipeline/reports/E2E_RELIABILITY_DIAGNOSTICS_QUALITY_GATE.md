# E2E Reliability and Diagnostics (Assignment B) - Independent Quality Gate

Stage 3 independent Quality Gate for change class `CI_TOOLING`. The reviewer did not
author, test or remediate the reviewed content. This is a governance/tooling gate: it
states publication readiness only and makes no product-phase claim.

## 1. Executive Result

**PASS WITH MINOR FIXES**

All intended behavior is implemented and verified independently, and default
fail-fast acceptance, lifecycle isolation, shard coverage, budgets, cleanup-is-fatal
and the CI workflow are unchanged. Two bounded, low-risk defects remain:

- F1: the results JSON can contain Playwright discovery output text.
- F2: one new unit test binds the real default ports 8765/4173.

Neither defect is a false success, a security exposure or a contract change. Both must
be remediated and rechecked before Stage 4 publication.

## 2. Reviewed identity

| Item | Value |
|---|---|
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\e2e-reliability-diagnostics-20261022` |
| Branch | `feat/e2e-reliability-diagnostics-20261022` |
| HEAD = origin/main = merge base | `9e47b4fc000426d2609ba5310e0e9bb0b66fb5e4` (ahead/behind 0/0) |
| Reviewed path set (uncommitted, tracked) | exactly 3 modified files, nothing staged, no untracked files before this report |
| `scripts/run_e2e.py` | `git hash-object` `d91c0828fe1b3d1f6817042290827405ee91154d` |
| `tests/test_run_e2e.py` | `d76a0b66450a84d4d8637b5429abdc1ef2e1f36d` |
| `docs/development/DEVELOPMENT_TOOLING_RUNBOOK.md` | `9586ae21156eedd0ea258adb275fac6a61342604` |
| Diff size | 811 insertions, 23 deletions; `git diff --stat` equals `git diff --ignore-cr-at-eol --stat` (no line-ending churn) |
| `.github/` | no diff |

The hashes matched the frozen values at gate start and again at gate end. The reviewed
files were last modified at 2026-10-22 12:48-12:49 UTC, before Stage 2 run S2-1 started
at 15:03:54 UTC. Stage 2 evidence therefore binds to the frozen content.

Context: `AGENTS.md`, `docs/DEVELOPMENT_WORKFLOW.md`, the `fyp-quality-gate` skill and
template, and `python scripts/dev_context.py --change-class CI_TOOLING` Tier 1 sections
(Architecture section 19 hotspots, PROJECT_STATE tooling). The shared side-session notes
folder was empty.

Session capability: Windows 11; repository `.venv` Python 3.12.10; Node v22.23.3;
installed Playwright 1.56.1 with Chromium 141.0.7390.37; local Docker image
`clm-ci64-linux-ready:20260930` (Linux, Python 3.12.3) run with `--network none`. No
Mongo container was needed or started. Hosted CI was unavailable.

## 3. Acceptance checklist

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Pinned `CHROMIUM_RESTRICTED_PORTS` rejected for every derived backend/frontend port | PASS | `_allocate_lifecycle_ports` calls `_reject_restricted_ports` per pair. Real CLI probe P6 (`--frontend-port 6565`, 2 selectors): exit 1 in 1.5 s, "frontend port 6566 for lifecycle 2 is restricted". Mutation M18 killed. |
| 1a | ...and in single `--grep` runs | PASS | `run()` checks before the port probe; `test_single_run_rejects_a_restricted_port_before_startup`; mutation M10 killed. |
| 1b | Set matches pinned Chromium | PASS | Reviewer probe in Chromium 141.0.7390.37: all 80 non-zero set members return `ERR_UNSAFE_PORT`; 4190, 6679, 4173, 8765, 28765 and 24173 are not blocked (`ERR_CONNECTION_REFUSED`). Port 0 is in the set but harmless (below 1024). |
| 2 | `_preflight_lifecycle_ports` probes every pair before lifecycle 1 | PASS | Called after allocation inside the setup `try`. Real probe P4 (listener on 28766, lifecycle 2): exit 1 in 1.4 s, no lifecycle started; S2-3 is the same on lifecycle 3. Mutation M9 killed. |
| 2a | `SO_REUSEADDR` only on POSIX with TIME_WAIT tolerance; never on Windows | PASS | `elif` after `SO_EXCLUSIVEADDRUSE`. Real Linux kernel probe: wildcard and loopback live listeners are still rejected with tolerance; a real TIME_WAIT (`/proc/net/tcp` state 06) is accepted by preflight only; the per-lifecycle probe still rejects it. Mutations M2 and M15 killed. |
| 2b | Each lifecycle still probes its own pair | PASS | `run()` still calls `_assert_ports_available(backend, frontend)` without tolerance. |
| 3 | `--keep-going`: continues after ordinary failure; stops on 130 / `CLEANUP_FAILURE`; never prints suite PASS on failure; exits non-zero | PASS | Code path verified. S2-2b: PASS / INDIVIDUAL_SELECTION_TIMEOUT / PASS, "1/3 isolated selections failed", no suite PASS. S2-2a: stopped on CLEANUP_FAILURE, lifecycle 3 `NOT_RUN`. Mutations M3, M4, M8 and M12 killed. |
| 4 | `--selectors-file`: exact subset in discovery order, fixture dispatch preserved; unknown/duplicate/empty fail closed; not with `--shard` | PASS | Real run P8 (file order 147, 84): executed 84 then 147, both PASS. P5 unknown entry: exit 1 before any lifecycle. P7 with `--shard`: argparse exit 2. Mutations M5, M6, M16 and M19 killed. |
| 5 | `--results-json`: exclusive creation, never overwritten | PASS | Early `exists()` refusal plus `open("x")`. Real P2 against an existing file: exit 1, content intact. Mutation M7 killed. |
| 5a | Holds identity, versions, per-lifecycle kind, ports, fixture, phase timings, `NOT_RUN` records | PASS | P8 and S2-1/2a/2b/3 JSON inspected: schema keys, `NOT_RUN` records, phase timings and identity (`HEAD`, tree, dirty, origin/main) are all present. Mutations M14 and M17 killed. |
| 5b | No output text, credentials or URIs | **FAIL (F1)** | No credentials or URIs appear in any inspected JSON (a grep for password/mongodb:///token/authorization/secret returned 0). However, `setup_failure` stores `str(exc)`. For a discovery failure that is `"Playwright test discovery failed: " + _sanitize(stdout + stderr)`, up to 12,000 characters. Reviewer probe: 42 lines / 1,416 characters of discovery stdout and stderr were persisted. |
| 6 | `run()` optional `outcome` record | PASS | All 7 kinds reachable. `test_run_records_result_kind_and_phase_durations` covers 6 kinds; `PORT_UNAVAILABLE` is covered by the restricted-port test. Mutation M13 killed. |
| 7 | Dead code removed from `_base_environment` | PASS | The removed `if result == 0` compared a dict with 0 and was unreachable. |
| 8 | Hard-coded `112` / `10140` replaced by discovery-derived checks; job-deadline bound retained | PASS | `launcher_seconds + 14 min <= 234 min` retained, with `max(map(len, shards))` derived from live discovery (112 on this revision). |
| 9 | Existing suite tests patch `_preflight_lifecycle_ports` so unit tests never bind real ports | **PARTIAL (F2)** | `RunE2ETests.setUp` patches it. But the new `test_preflight_probes_every_pair_and_tolerates_only_time_wait` calls the real preflight on `(8765, 4173)` unpatched in its last block. The reviewer's bind monitor saw real binds to 127.0.0.1:8765/4173, and with 8765 held the test errors with "lifecycle 1 (8765/4173) are already occupied". |
| 10 | Runbook documents flags; stale "90-minute / 26-selector" text dropped | PASS (see F1) | Accurate except "It holds no output text" and the undocumented `setup_failure` field (F1). Older counts remain only in historical reports, which is acceptable. |
| 11 | Unchanged without new flags: fail-fast exit/output, isolated lifecycles, shard partition/coverage, budgets, cleanup-is-fatal, CI workflow | PASS | Without `results_path`, `finish()` returns the code unchanged with no extra output. Suite/lifecycle budget formulas and constants are unchanged. Shard slicing is unchanged. Cleanup failure still returns 1 and stops dispatch. `.github/` has no diff. The one intended default change is the upfront preflight (D8). |

## 4. Tester and adversarial findings

Commands were run by the reviewer on the frozen content with `PYTHONPATH` pinned to
`<worktree>\apps\backend` and bytecode writing disabled:

- `python -m unittest tests.test_run_e2e`: **69 tests OK**, 3.4 s (up from 49 on
  `origin/main`).
- Consumer tests `test_slice_b/c/f_*_fixture_routing` and `test_check_tooling_config`:
  11 OK.
- `ruff check --no-cache` on both Python files: pass. `ruff format --check` reports
  both files, but the `origin/main` blobs report identically and CI runs `ruff check`
  only, so this is not a regression.
- `git diff --check`: pass.
- `check_secrets`, `check_project_state`, `check_architecture`, `check_tooling_config`,
  `check_policy_authority` and `check_external_provider_readiness`: all exit 0.
- Reviewer mutation set (20, applied in memory, worktree untouched): **19 killed**.
  - Killed: M1-M19, covering TIME_WAIT tolerance, Windows `SO_REUSEADDR`,
    keep-going stop conditions, selector order, duplicate and unknown entries,
    exclusive write, exit code, preflight call, the restricted check in `run()` and
    allocation, the restricted set, default fail-fast, the cleanup kind, status,
    garden dispatch and `NOT_RUN`.
  - Survived: M20 (a results-write failure after a passing suite returns 0 instead
    of 1). The code is correct; this path has no test.
  - The clean baseline rerun after mutation was 69 OK.
- Real CLI probes on disjoint ports 28765/24173:
  - P1: `--grep` with `--keep-going` exits 2.
  - P2: an existing results file exits 1 and is not overwritten.
  - P4: occupied lifecycle-2 port exits 1 in 1.4 s.
  - P5: an unknown selector exits 1 in 1.4 s.
  - P6: a restricted derived port exits 1 in 1.5 s.
  - P7: `--selectors-file` with `--shard` exits 2.
  - P8: a real 2-lifecycle browser run with `--keep-going --selectors-file
    --results-json` exits 0 in 18.8 s. Both lifecycles passed in discovery order,
    and the JSON was correct and secret-free.
- Real discovery on this revision: 112 selectors.
- Stage 2 evidence inspected, not trusted:
  - S2-1: 112/112 PASS, `complete=true`, `counts={PASS:112}`, ports 8765/4173 to
    8876/4284, 112 unique selectors, 1,416.0 s, slowest 57.016 s.
  - S2-2a: PASS, then CLEANUP_FAILURE, then NOT_RUN; stopped.
  - S2-2b: PASS / TIMEOUT / PASS, exit 1.
  - S2-3: preflight failure on lifecycle 3 in 1.141 s.
  - All carry identity `9e47b4f`, dirty, Playwright 1.56.1, and are bound to the
    frozen content by the file timeline above. The full suite was **not** rerun:
    S2-1 is valid, complete and bound.
- **Hosted CI: `HOSTED_CI_NOT_EXECUTED - BILLING/INFRASTRUCTURE BLOCKED`** (Stage 2
  report; not independently re-observed, because the GitHub connector failed in this
  session). It is not counted as passing. `tests/test_run_e2e.py` is not run by
  `.github/workflows/ci.yml` (pre-existing).
- Not run: `pre_pr_check.py` (Stage 4, requires a clean committed tree), the full
  backend/frontend suites (not affected), mypy (CI scope is `apps/backend/app`, which
  is unaffected), and macOS/BSD socket semantics (no host).

**Known finding adjudicated (S2-2a primary cause).** `run()` records `READINESS_FAILURE`
and then overwrites it with `CLEANUP_FAILURE` when cleanup fails. The JSON therefore
keeps only the terminal kind, while stderr keeps both. The recorded kind is truthful:
it is the controlling, fatal outcome that stops the suite. The null readiness phases
(`backend_ready_seconds: null`) show readiness never completed, and nothing is reported
as passing. Classified as **accepted technical debt D1**, not a bug. Adding a
`primary_result` field is an optional improvement.

## 5. Code and architecture review

The change is confined to the existing runner owner and its tests, with no new owner,
dependency or CI change, so no ADR is needed. Fixture dispatch was refactored into
`fixture()` with identical semantics, and M16 confirms garden routing. Exit codes stay
fail-closed in every new path.

**F1 - bug, low.** Results JSON `setup_failure` persists Playwright discovery output.
- Location: `scripts/run_e2e.py`, the setup `except` in `run_isolated_suite`, which
  stores `_sanitize(str(exc))`. For the discovery failure raised in
  `_list_test_selectors`, that text embeds sanitized process stdout and stderr.
- This violates the criterion "no output text" and the runbook sentence "It holds no
  output text".
- The content is sanitized and identical to what stderr already prints, so it is not a
  security exposure. But the results JSON is designed as durable evidence and
  contradicts its own contract.

**F2 - test bug, low.** `test_preflight_probes_every_pair_and_tolerates_only_time_wait`
really binds 127.0.0.1:8765 and 127.0.0.1:4173 in its final `REAL_PREFLIGHT([(8765,
4173), (8766, 6566)])` block. It errors whenever 8765 is in use, which happens during
any concurrent default-port E2E or local backend. It also contradicts the stated "unit
tests never bind real ports" property.

**Accepted technical debt and observations (non-blocking):**

- D1: The results JSON keeps the terminal kind only (see above).
- D2: The restricted set is pinned to Chromium 141 / Playwright 1.56.1. 4190 (WHATWG
  Fetch bad port) is in the default frontend range at lifecycle 18. If a future
  Chromium blocks it, the check will not catch it. Re-pin and re-probe on any
  Playwright upgrade; the code comment already records this.
- D3: BSD/macOS `SO_REUSEADDR` may let preflight miss a wildcard listener. The
  unchanged per-lifecycle probe remains the backstop. Not verified (no host).
- D4: The results JSON is not written when an exception escapes `run()` before its
  `try` (missing dependency, invalid Mongo port env) or when an interrupt arrives
  outside a lifecycle. These are pre-existing paths that exit non-zero; there is no
  false success.
- D5: The identity is `HEAD`'s tree plus a dirty flag, not per-file content hashes.
  The runbook states this truthfully.
- D6: `finish()` git and node probes (bounded by 10 s timeouts each) run after the
  suite budget, and only with `--results-json`, which CI does not use.
- D7: The slowest lifecycle used 57.0 s of a 60 s budget (`performance-browser:98`).
  This risk existed before the change.
- D8: The upfront preflight now applies to default runs (intended). A later port that
  is transiently occupied fails at once instead of possibly freeing up. Default ranges
  lie below OS ephemeral ranges.
- D9: When writing the results file fails after a passing suite, "E2E SUITE PASS" is
  printed before the write error, but the exit code is 1 (fail-closed). Mutation M20
  shows that this exit path is untested.

## 6. Security review

- The ephemeral credential stays out of the JSON (test with sentinel plus inspection
  of all real JSON files).
- URIs and secret assignments are redacted by `_sanitize`.
- `_git_identity` is read-only (`GIT_OPTIONAL_LOCKS=0`, allowlisted environment).
- The selector file is parsed as data only. Unknown entries fail closed; the first
  unknown entry is echoed, which is user-supplied text.
- No new network, authentication or KYC surface. Windows keeps `SO_EXCLUSIVEADDRUSE`
  (no port theft).
- F1 has no credential or KYC impact, because discovery is unauthenticated and the
  output is sanitized. Its fix is required as a contract correction, not as a security
  fix.
- No secret or confidential artefact is newly tracked.

## 7. Required fixes

1. **F1:** Stop persisting process output in the results JSON. For example, record a
   fixed failure category or message for setup failures (such as "discovery failed")
   and keep the sanitized detail on stderr only. Alternatively, store a strictly
   bounded first line with no subprocess output. Add a test proving that discovery
   stdout and stderr never reach the file. Keep the runbook statement true.
2. **F2:** Make the final block of
   `test_preflight_probes_every_pair_and_tolerates_only_time_wait` non-binding, for
   example by patching `_assert_ports_available` there. Keep the assertion that a
   restricted lifecycle-2 port raises `ValueError`.

Optional in the same remediation (not required): a test for the results-write-failure
exit path (M20), and a `primary_result` field (D1).

Recheck scope: the corrected delta, `tests.test_run_e2e`, Ruff, `git diff --check`,
`check_secrets`, and a focused real probe of the setup-failure JSON. S2-1 full-suite
evidence stays valid if the fix touches only the setup-failure recording and tests; a
broader runner change invalidates it.

## 8. Readiness

**Not ready for Stage 4 publication.** Bounded remediation (F1, F2) and a fresh
independent recheck of the changed delta are required first. After an exact `PASS`,
publication still needs separate owner authorization and a clean-tree
`python scripts/pre_pr_check.py`. Hosted CI remains `HOSTED_CI_NOT_EXECUTED` until
GitHub runs it. This gate makes no product-phase, ACRA or GoldTier readiness claim.

## 9. Git status

- Branch `feat/e2e-reliability-diagnostics-20261022` at HEAD
  `9e47b4fc000426d2609ba5310e0e9bb0b66fb5e4`.
- The three reviewed files are modified, unstaged and unchanged by the reviewer.
- The only reviewer write in the worktree is this untracked report.
- Probe scripts and outputs were written only to the reviewer's session scratchpad.
- The reviewer made no implementation, test, documentation or config fix, and no
  commit, push, PR or merge, and did not touch `main` or `ui-enhancement-v1`.
- No container, browser or server process was left running. The Linux probe container
  was started with `--rm`.
