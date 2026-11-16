# Worker memory limit on macOS - independent quality gate

Bounded governance/security fix to safety control SF-002 (security patch PR #188).

- Reviewer: independent reviewer subagent (did not author or remediate this change).
- Branch: `fix/worker-memory-limit-macos`
- Reviewed HEAD: `68eb66c` (single commit on top of `origin/main` `db669ca`; base is current, no merge needed)
- Reviewed path set (`git diff origin/main...HEAD`, 4 files, +54/-3):
  - `apps/backend/app/connectors/local_document_worker.py`
  - `apps/backend/tests/test_sf001_sf002_document_worker_hardening.py`
  - `docs/decisions/DECISION_LOG.md`
  - `apps/assistant/ai_assistant/synthetic_boundary.json`
- Working tree at review start and end: clean apart from this report. No staged or untracked task files.
- All results below are local (macOS, Darwin 24.2.0, Python 3.12 worktree venv). CI is billing-blocked; nothing here is hosted CI evidence.

## 1. Executive Result

**PASS**

The change is exactly the agreed size: `_limit_memory()` now returns early on `win32` and `darwin` only. The Linux code path is byte-identical to `origin/main` and still fails closed. The deployed backend image is Linux (`python:3.12-slim-bookworm`, `platform: linux/amd64`), so `sys.platform` cannot be `darwin` in deployment. The new regression test fails on the unfixed worker on macOS and passes on the fix. No required fixes remain. Because this amends a safety control, Shane must still accept the SF-002 amendment at PR review. This verdict does not replace that decision.

## 2. Acceptance Checklist

| # | Requirement | Result | Evidence |
|---|---|---|---|
| 1 | `_limit_memory()` skips only on `win32`/`darwin` | Met | Diff: `if sys.platform in ("win32", "darwin"): return`. No other platform added. |
| 2 | Linux path unchanged; still sets the cap | Met | Body after the guard compared with `origin/main` using `diff`: identical (`getrlimit`, `min(limit, hard)`, `setrlimit(RLIMIT_AS, (limit, hard))`). |
| 3 | Linux failure still fails closed (exit 2) | Met | No try/except added around `setrlimit`; `main()`'s catch-all still returns 2. Simulated Linux path on this Mac (forced `sys.platform='linux'` in-process, then `main()`): returned **2**, because setrlimit raised and the error was not swallowed. |
| 4 | No `RLIMIT_DATA` substitution; errors not ignored | Met | `grep RLIMIT` across `apps/` shows only `RLIMIT_AS`; no new exception handling. |
| 5 | Owner's cap test skip widened to darwin, reason updated | Met (legitimate) | See section 4. Linux coverage is unchanged. |
| 6 | New test: dev platforms leave RLIMIT_AS unchanged | Met | `test_development_platforms_skip_the_cap_and_leave_rlimit_as_unchanged` passes on macOS. |
| 7 | New test: real worker subprocess validates clean fixture, exit 0, all platforms | Met | `test_the_real_worker_validates_a_clean_fixture_pdf` passes; it runs on every platform including Linux. |
| 8 | Decision log: un-numbered SF-002 amendment | Met | One section appended; follows the existing un-numbered `## ST-7 amendment` precedent (line 2885); marked "needs owner acceptance". |
| 9 | Synthetic boundary regenerated | Met | `build_synthetic_boundary.py --check`: "synthetic boundary is current" (exit 0). The only change is adding `"darwin"`. |

## 3. Contract and Integration Findings

None. No connector contract, schema, API or persistence change. The worker's output format and exit-code contract are unchanged. The `synthetic_boundary.json` addition is the mechanical consequence of a new backend string literal; `--check` passes.

Deployment check: `deploy/backend.Dockerfile` uses `FROM python:3.12-slim-bookworm`, and `deploy/compose.yml` pins the backend to `platform: linux/amd64`. The only Dockerfiles are the backend, frontend and egress images, and none is macOS-based. `darwin` appears nowhere else in `apps/backend/app`. The skip cannot reach a deployed worker.

## 4. Tester and Adversarial Findings

Interpreter: the worktree-only venv. `python -I -c "import app; print(app.__file__)"` gives `/Users/tasha/Documents/GitHub/dd-clm-worker-memory-limit/apps/backend/app/__init__.py`, so worker children import the reviewed code, not the main checkout.

Commands run by the reviewer:

- `pytest -p no:cacheprovider tests/test_sf001_sf002_document_worker_hardening.py` (from `apps/backend`): **16 passed, 1 skipped, 1 failed**.
  - Skipped: `test_the_worker_caps_its_own_address_space` ("RLIMIT_AS is enforced on Linux only"); expected on macOS.
  - Failed: `test_a_real_child_process_sees_no_backend_secret`. The only extra variable is `__CF_USER_TEXT_ENCODING`, which macOS injects into every process. It is not a backend secret, and none of the SECRETS assertions were reached with a leak. The test runs `python -c` through `local_process.run_bounded_process` and never touches `_limit_memory` or the worker. `local_process.py` and this test body are unchanged by the diff (`git diff origin/main...HEAD -- local_process.py` is empty), so the failure is pre-existing on `origin/main` on macOS and unrelated. This is a macOS-only test portability issue; it is recorded as a non-blocking observation (O1).
- Reproduction (origin/main worker vs fixed worker, run directly with `-I -B` on `tests/fixtures/uat/zero-touch-database/demo-alpha-scanned.pdf`): origin/main `db669ca` worker **exit 2**; fixed worker **exit 0**, `{"pages": []}`. On this Mac, `setrlimit(RLIMIT_AS, (1536 MiB, RLIM_INFINITY))` raises `ValueError: current limit exceeds maximum limit`, which confirms the root cause.
- Adversarial Linux-path simulation: forced `sys.platform = "linux"` in-process and called `main()`. Result: **2** (fail closed, the error is not swallowed).
- E2E rerun by the reviewer (worktree venv on PATH): `scripts/run_e2e.py --selectors-file` with `e2e/authenticated-zero-touch.e2e.ts:765` and a reviewer-owned results JSON: **PASS** (1/1, ~10.5 s). This journey uploads a clean fixture (`setInputFiles(cleanFixture)`) and waits for "Completed POC workflow". The implementer's `e2e/responsive-layout.e2e.ts:441` PASS (results `e2e-worker-memory-r3.json`, status PASS, 2/2) was inspected and reused, not rerun.
- `ruff check` and `ruff format --check` on the two changed Python files: clean. `git diff --check origin/main...HEAD`: clean.
- `scripts/pre_pr_check.py` on the clean committed tree: **SUMMARY: PASS (0 unsafe conditions, 0 warnings)**.
- Reused, not rerun: the implementer's broader suites (`test_local_process.py`, `test_s2_local_ocr.py`, `test_document_processing.py`, `test_document_api.py`), with only the 6 known macOS `test_real_local_ocr_acceptance[*]` font failures plus O1; and the mypy result on changed files (4 errors claimed identical to main's baseline). The diff adds no new typed surface beyond the test functions, so reuse is reasonable.

Test quality:

- **Is the regression test meaningful?** Yes. `test_the_real_worker_validates_a_clean_fixture_pdf` launches the real worker module as a subprocess. `run_bounded_process` raises `FAILED` on any non-zero exit (`local_process.py:104-105`), so on the unfixed worker on macOS it fails, as the direct reproduction shows (exit 2). It also runs on Linux, where it proves a clean PDF still validates under the cap.
- **The darwin in-process test** would raise `ValueError` on the unfixed code on macOS, so it also guards the regression. Running it in-process is safe because the function returns before touching limits.
- **Is the owner's skip change a weakening?** No. On Linux the test still runs unchanged, with the same assertion (`<= MAX_WORKER_ADDRESS_SPACE`). On macOS, under `origin/main`, this test could not pass: `_limit_memory()` raises, the child exits non-zero and `run_bounded_process` raises `FAILED`. The skip removes a test that could only fail on a platform where the control is not deployed and cannot be enforced. The changed assertion in Shane's test must still be listed in the PR for his review (repository rule).

## 5. Code and Architecture Review

No defects. The change is minimal and in scope, with an accurate comment. The worker still never imports workflow, network or persistence code. No scope creep.

Accepted limitation, made explicit: on macOS and Windows development machines the worker runs without an address-space cap. That is the trade-off of the fix. It is recorded in the decision log and needs owner acceptance.

## 6. Security Review

- SF-002 (memory cap) stays enforced, and fails closed, on the only deployment platform (Linux container). The other #188 controls (SF-001 minimal environment, decoder allowlist, bounded process timeouts and output limits) are untouched and still pass, apart from O1, which is pre-existing.
- No secrets, auth, TLS, PII or logging changes. `.env` was not read.
- Residual risk: a developer Mac has no worker memory cap, so a hostile upload processed locally could use more memory. Timeouts and output limits still bound it. This only affects development machines.

## 7. Required Fixes

None.

Non-blocking observations (no fix required for this gate):

- **O1 (Low, pre-existing, out of scope):** `test_a_real_child_process_sees_no_backend_secret` fails on macOS because of the OS-injected `__CF_USER_TEXT_ENCODING`. It is unrelated to this diff. Shane may want a follow-up to tolerate that variable on darwin.
- **O2 (Process):** the PR must flag the changed skip condition in Shane's `test_the_worker_caps_its_own_address_space` and request owner acceptance of the SF-002 amendment.

## 8. Readiness

Governance/publication readiness: ready for PR, subject to Shane accepting the SF-002 amendment (a safety-control change) at review. This gate says nothing about product-phase readiness, live ACRA or real GoldTier readiness.

## 9. Git Status

- Branch `fix/worker-memory-limit-macos`, HEAD `68eb66c`, base `origin/main` `db669ca`.
- Tracked, staged and untracked: clean before this report. The reviewer's only repository write is this report file (untracked).
- The reviewer's temporary files (old worker copy, E2E selectors and results JSON, worker output directories) live in the session scratchpad, outside the repository.
- No implementation fix, commit, push, merge, stash, reset, rebase or branch checkout was performed.
