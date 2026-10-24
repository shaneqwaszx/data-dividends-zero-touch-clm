# E2E Reliability and Diagnostics (Assignment B) - Independent Re-Quality Gate

Stage 3 independent re-Quality Gate for change class `CI_TOOLING`, after the bounded
remediation of the first gate's F1 and F2. The reviewer did not author, test, remediate
or previously review this work. This is a tooling/governance gate. It states
publication readiness only and makes no product-phase, ACRA or GoldTier claim.

## 1. Executive Result

**PASS**

F1 and F2 are fixed and independently verified. The optional M20 test was added and
kills its mutant. The remediation delta is confined to setup-failure recording, three
tests, one test-block patch and one runbook paragraph. It introduces no new defect, no
false-success path, no security exposure and no change to default fail-fast acceptance,
lifecycle isolation, shard coverage, budgets, cleanup-is-fatal or CI. No required fix
remains.

## 2. Identities

| Item | Prior reviewed content (first QG) | Re-reviewed content (this gate) |
|---|---|---|
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\e2e-reliability-diagnostics-20261022` | same |
| Branch | `feat/e2e-reliability-diagnostics-20261022` | same |
| HEAD = origin/main | `9e47b4fc000426d2609ba5310e0e9bb0b66fb5e4` | same (uncommitted, nothing staged) |
| `scripts/run_e2e.py` | `d91c0828fe1b3d1f6817042290827405ee91154d` | `b3d9550c3c950b1a7052ec0c7de5fc3939792282` |
| `tests/test_run_e2e.py` | `d76a0b66450a84d4d8637b5429abdc1ef2e1f36d` | `475931ce089c1ac8d179628265d48bd31b4cb2fa` |
| `docs/development/DEVELOPMENT_TOOLING_RUNBOOK.md` | `9586ae21156eedd0ea258adb275fac6a61342604` | `b0bbf871288bab242b8adbcc08a04dce47de6fc7` |
| Diff vs `origin/main` | 811 insertions, 23 deletions | 883 insertions, 24 deletions |

Verification performed by this reviewer:

- `git status --short`: exactly the 3 modified files plus the untracked first-gate
  report. `git rev-parse HEAD origin/main`: both `9e47b4f`. `git hash-object` of each
  file matched the frozen values above at gate start and gate end.
- The prior reviewed copies in the remediator's scratchpad `reviewed\` folder hash to
  the first gate's values with `git hash-object --path=<repo path>`, so they are the
  exact reviewed content.
- `git diff --stat` equals `git diff --ignore-cr-at-eol --stat`, so there is no
  line-ending churn against the mixed-EOL committed blobs. The prior-to-current delta
  has the same stat with and without `--ignore-cr-at-eol`.
- `.github/`: no diff.
- The remediation delta was regenerated with `git diff --no-index --ignore-cr-at-eol`
  per file rather than taken from `remediation-delta.patch`. It contains:
  - runner: +7/-1;
  - tests: +69/-7;
  - runbook: +5/-2.

Context read: `AGENTS.md`, `docs/DEVELOPMENT_WORKFLOW.md` (change-class matrix and
"Evidence reuse and invalidation"), `.agents/skills/fyp-quality-gate/SKILL.md`, the
first gate report `E2E_RELIABILITY_DIAGNOSTICS_QUALITY_GATE.md` and the sibling
side-session note (data only).

Session capability: Windows 11, repository `.venv` Python 3.12.10, Node v22.23.3,
Playwright 1.56.1. No Mongo container was needed or started. The GitHub connector failed
to connect in this session, so hosted CI was not observed.

## 3. Remediation delta review

### Runner (`scripts/run_e2e.py`)

- New constant `SETUP_FAILURE_STAGES = ("DISCOVERY", "SELECTION", "PORT_ALLOCATION",
  "PORT_PREFLIGHT")`.
- In `run_isolated_suite`, a local `setup_stage` starts as `DISCOVERY` and advances:
  - to `SELECTION` after `discovered_count` is recorded;
  - to `PORT_ALLOCATION` after `selected_count` is recorded;
  - to `PORT_PREFLIGHT` before `_preflight_lifecycle_ports`.
- The `except` block still prints `E2E FAILED: <sanitized detail>` to stderr and returns
  `finish(1, complete=False)`. It now stores only `setup_stage` in
  `document["setup_failure"]`.

Every exception raised inside the `try` maps to the stage that raised it:

- `DISCOVERY`: `_find_node`, a missing Playwright CLI, non-zero discovery, or invalid
  JSON.
- `SELECTION`: shard slicing and selector-file reading or validation.
- `PORT_ALLOCATION`: restricted-port rejection.
- `PORT_PREFLIGHT`: restricted or occupied pairs.

The recorded value is always one of four fixed literals, so no exception text or
subprocess output can reach the file through this field. Outside the `except` body, the
only change is the addition of side-effect-free local string assignments. The success
path, lifecycle dispatch, `run()`, budgets, shard logic, fixture dispatch and `finish()`
are byte-identical to the reviewed content (ignoring CR).

### Tests (`tests/test_run_e2e.py`)

- `test_discovery_failure_output_reaches_stderr_but_never_the_results_file` replaces
  `test_setup_failure_is_recorded_without_lifecycles`. It runs the real
  `_list_test_selectors` with `subprocess.run` returning a non-zero listing whose
  stdout and stderr carry sentinels. It asserts:
  - exit 1 and no lifecycle;
  - the stdout sentinel reaches stderr;
  - no `SENTINEL` appears in the raw file;
  - the key set is exactly `RESULT_KEYS | {"setup_failure"}`;
  - `setup_failure == "DISCOVERY"`.
- `test_setup_failure_records_only_a_fixed_stage` covers `SELECTION` (a real unknown
  selector-file entry), `PORT_ALLOCATION` and `PORT_PREFLIGHT`. Each case has a
  sentinel that must appear on stderr and never in the file, and the recorded value
  must be in `SETUP_FAILURE_STAGES`.
- `test_results_write_failure_fails_closed_after_a_passing_suite` (optional M20): two
  passing lifecycles, then `_write_results` raises `OSError`. It asserts exit 1, two
  dispatches, and the write-error message.
- In the F2 block, `_assert_ports_available` is now patched. The block asserts the
  `ValueError` for restricted lifecycle 2 and that only pair 1 was probed
  (`[call(8765, 4173, tolerate_time_wait=True)]`).

### Runbook

The new sentence documents `setup_failure` and its four values, and states that detail
goes to stderr only. "The file holds no output text, credentials or URIs" is now true
for every observed path (see section 4).

## 4. Finding dispositions

| Finding | Disposition | Evidence |
|---|---|---|
| **F1** (results JSON persisted discovery output) | **FIXED - verified** | Code inspection above. Reviewer mutants A (`str(exc)` restored) and B (stage plus message) are killed by both new F1 tests. Reviewer real CLI probes Q1-Q3 (real discovery, 112 selectors) record only `SELECTION` / `PORT_ALLOCATION` / `PORT_PREFLIGHT` with no message text, while stderr keeps the detail. Q1's user-supplied sentinel selector appears on stderr and not in the JSON. |
| **F2** (unit test bound real default ports) | **FIXED - verified** | Reproduced before and after with a bind monitor that recorded every `socket.bind` while real listeners held 127.0.0.1:8765 and 4173. Prior reviewed files: the F2 test errors with "lifecycle 1 (8765/4173) are already occupied", and tests bound 8765. Current files: 71 run, 0 failures, 0 errors, and no default port bound by any test (one OS-assigned ephemeral port only). |
| M20 (optional; untested write-failure exit) | **ADDED - verified** | Reviewer mutant H (`return code or 1` changed to `return code`) is killed by the new test. |
| D1 (no `primary_result`) | Accepted debt, unchanged | Not in the remediation scope. The first gate's rationale still holds. |
| D9 (PASS line printed before a write error) | Accepted debt, unchanged | The M20 test asserts exit 1 and the error message, and does not assert the PASS line is absent. This matches the accepted debt. Exit stays fail-closed. |
| D2-D8 | Unchanged | The delta does not reach them. |

New findings from the delta: **none requiring a fix.** Non-blocking observations:

- **O1 (test design).** The discovery test patches `pathlib.Path.is_file` and
  `subprocess.run` process-wide for its duration. `finish()`'s git and Node probes
  therefore also receive the fake non-zero result and record `None` identity fields.
  This is harmless and test-local. It incidentally shows that identity probes discard
  output from a non-zero exit, so the sentinel assertion is not weakened.
- **O2 (stage granularity).** `SELECTION` covers both shard slicing and selector-file
  errors, and `DISCOVERY` covers a missing Node or Playwright dependency as well as
  discovery itself. The labels are accurate stage names. Finer categories are optional.

## 5. Evidence

### Run by this reviewer on the re-reviewed hashes

All commands pinned `PYTHONPATH` to `<worktree>\apps\backend` and set
`PYTHONDONTWRITEBYTECODE=1`.

| Check | Result |
|---|---|
| `python -m unittest tests.test_run_e2e` | **71 OK**, 3.45 s |
| Same 71, in-process, with real listeners on 127.0.0.1:8765/4173 and a bind monitor | 71 run, 0 failures, 0 errors; no test bound 8765 or 4173 |
| Consumer tests: `test_slice_b_e2e_fixture_routing`, `test_slice_c_e2e_fixture_routing`, `test_slice_f_fixture_routing`, `test_check_tooling_config` | 11 OK |
| `ruff check --no-cache` on both Python files | pass |
| `git diff --check` | pass |
| `check_secrets`, `check_project_state`, `check_architecture`, `check_tooling_config`, `check_policy_authority`, `check_external_provider_readiness` | all exit 0 |
| Reviewer mutation set: 11 mutants, full module, run on copies outside the worktree, diffed against an unmutated-copy baseline | **11/11 killed** (details below) |
| Real CLI probes on disjoint ports 28765/24173 with real discovery (112) | Q1-Q4 (details below) |

Mutation baseline: the unmutated copy fails the same 6 browser-config and CI-bound tests
in every run. Those tests need the full `apps/frontend` tree, which the copy omits; this
is environmental and unrelated to the delta. A mutant counts as killed only when it fails
a test the baseline passes.

Killed mutants:

- A: F1 full message restored.
- B: stage plus message.
- C: wrong initial stage.
- D, E, F: each stage advance removed.
- G: stderr detail dropped.
- H: write failure exits 0.
- I: setup failure exits 0.
- J: `setup_failure` not recorded.
- K: `SELECTION` dropped from `SETUP_FAILURE_STAGES`.

Real CLI probes (`--keep-going --results-json`, with a selector file of
`e2e/responsive-layout.e2e.ts:544` and `e2e/authenticated-zero-touch.e2e.ts:233`
unless noted):

- Q1, unknown sentinel selector: exit 1 in 1.5 s; `SELECTION`; no lifecycles.
- Q2, `--frontend-port 6565`: exit 1 in 1.5 s; `PORT_ALLOCATION` (6566 restricted for
  lifecycle 2).
- Q3, listener held on 28766: exit 1 in 1.4 s; `PORT_PREFLIGHT` ("lifecycle 2
  (28766/24174) are already occupied").
- Q4, real 2-lifecycle browser run: exit 0 in 13.9 s; `status=PASS`,
  `complete=true`, both lifecycles PASS in discovery order, no `setup_failure` key.

Every Q1-Q4 JSON carries identity `9e47b4f`, tree `50ffcbab`, `dirty=true` and
Playwright 1.56.1, and none contains a sentinel or message text. No listener remained on
the probe or default ports afterwards.

Probe scripts and outputs are in this reviewer's session scratchpad only.

### Remediator evidence

The remediator's claims are consistent with the results above: 71 OK, 71 OK with default
ports held, Ruff, `git diff --check`, the six checks, 10/10 mutants, and `r1-*.json`.
This gate does not rely on them. The reviewer re-read `r1-allocation.json`,
`r1-selection.json` and `r1-preflight.json`; each holds only its stage value.

### Reused earlier evidence and why it remains valid

`docs/DEVELOPMENT_WORKFLOW.md` requires the complete applicable set to be rerun when a
change reaches a shared owner, hotspot or CI orchestration, *or its impact cannot be
safely bounded*. `scripts/run_e2e.py` is such an owner, so the reviewer bounded the
impact explicitly instead of assuming it.

The regenerated delta proves that, outside the setup `except` body, the only runner
change is the addition of four side-effect-free assignments to a local string. The
success path and every post-setup path execute the same statements as the reviewed
content. The reviewer judges the impact safely bounded. On that basis:

- **S2-1** (112/112 PASS, `complete=true`, 1,416.0 s, Playwright 1.56.1, prior hashes):
  **remains valid** for full-suite success-path behavior. The one key whose content
  changed (`setup_failure`) is absent on a successful run. Q4 independently re-confirms
  real lifecycle dispatch, isolation and JSON on the new hashes.
- **S2-2a** (CLEANUP_FAILURE stops, `NOT_RUN` recorded) and **S2-2b** (keep-going
  across a timeout, exit 1): **remain valid**. These paths are after setup and are
  unchanged.
- **S2-3** (preflight failure on lifecycle 3 before any lifecycle, in 1.141 s):
  **behavior remains valid** (exit 1, no lifecycle started, timing). Its JSON
  `setup_failure` value is the old free-text form and is **superseded** by Q3 and
  `r1-preflight.json` on the new hashes.
- First-gate probes P1-P8 and mutants M1-M19 target unchanged code and **remain valid**.
  M20's survivor is now killed (mutant H).
- **Hosted CI: `HOSTED_CI_NOT_EXECUTED - BILLING/INFRASTRUCTURE BLOCKED`** (carried
  forward, not re-observed, not counted as passing).

No full 112-lifecycle suite was run in this gate. None is required, because S2-1 remains
valid.

Not run:

- `pre_pr_check.py` (Stage 4; it needs a clean committed tree).
- The full backend and frontend suites and mypy (the affected surface is the runner
  script and its tests only).
- macOS/BSD socket semantics (no host; D3 unchanged).

## 6. Security review

- The delta strictly reduces what the results JSON can hold: four fixed literals replace
  free exception text.
- No new subprocess, network, file-write or credential surface. Stderr output is
  unchanged and still passes through `_sanitize`.
- No secret or confidential artefact is newly tracked (`check_secrets` exit 0).
- The new tests use local temporary paths only.

## 7. Change statement

- Runtime behavior: the results JSON `setup_failure` value is now a fixed stage instead
  of sanitized message text (opt-in `--results-json` only).
- Tooling/script: yes.
- Unchanged: API/type, schema of product data, connector, configuration, business rule,
  mapping, auth/security posture, architecture and provider status.
- CI workflow: unchanged.

## 8. Verdict and readiness

**PASS** for the frozen re-reviewed content (`b3d9550c` / `475931ce` / `b0bbf871` on
`9e47b4f`).

Publication readiness: **ready for Stage 4 consideration only.** Publication still needs:

- separate explicit owner authorization;
- a commit of exactly this reviewed content, with no further change;
- a clean-tree `python scripts/pre_pr_check.py` and its checklist.

Any change to the reviewed files invalidates this verdict for the changed scope. Hosted
CI remains `HOSTED_CI_NOT_EXECUTED` until GitHub runs it.

## 9. Git status

- Branch `feat/e2e-reliability-diagnostics-20261022` at HEAD
  `9e47b4fc000426d2609ba5310e0e9bb0b66fb5e4`.
- The three reviewed files are modified, unstaged and unchanged by this reviewer.
- The first-gate report is untouched. This report is the reviewer's only write in the
  worktree.
- No commit, push, PR or merge was made. `main` and `ui-enhancement-v1` were not
  touched. No container, browser or server process was left running.
