# E2E macOS TMPDIR fix — independent Quality Gate

Date: 2026-10-30. A fresh, independent reviewer ran this under `fyp-quality-gate`, change class CI_TOOLING. This file is the only one the reviewer wrote. The reviewer did not edit, stage, commit, push or merge anything, did not read `.env`, did not start Mongo or any server, and did not rerun the E2E suite.

## Executive result

**PASS: P0/P1/P2 = 0/0/0.** There is one P3 nit, and it is not blocking.

## Reviewed identity

- Worktree: `/Users/tasha/Documents/GitHub/dd-clm-e2e-tmpdir`, branch `fix/e2e-macos-tmpdir`.
- HEAD: `ac1376f60784c03e4f2913f03c11a17dc1181f4c`. This is the only commit on top of origin/main `4e738973ac892ad84d0a22d150894dd344938c6a`.
- The working tree was clean. The diff against origin/main touches 3 files (+15/-0):
  - `scripts/run_e2e.py`: `"TMPDIR"` added to `_SYSTEM_ENV_KEYS`.
  - `scripts/e2e_backend_server.py`: `"TMPDIR"` added to `_SYSTEM_ENV_KEYS`.
  - `tests/test_run_e2e.py`: the existing allowlist test now also checks TMPDIR, and there is a new test, `test_backend_keeps_the_os_temp_directory_for_local_ocr`.

## Assessment

### Safety and allowlist intent
- Both allowlists only copy listed keys from the parent environment: `run_e2e.py:355` and `e2e_backend_server.py:106`, which clears `os.environ` and then restores the listed keys. TMPDIR is the POSIX equivalent of the `TEMP`/`TMP` keys that were already allowed. It holds a path, not a credential.
- The allowlist approach is unchanged. The test still asserts that `MONGO_URI`, `GITHUB_TOKEN` and `PHASE13_*_PASSWORD_HASH` are removed. No denylist was added, and no secret-shaped or app-config key now passes through.
- No product safety control is affected: the exact-line catalog, maker-checker and permission rechecks are untouched. The change is limited to the E2E harness, and no application or runtime code changed.

### Root cause
- I reran the reproduction (`ocr_env_probe.py`, run under `env -i` from `apps/backend`):
  - Without TMPDIR: tesseract returned rc=1. Leptonica reported `fopenReadStream: failed to open locally ... /tmp/clm-document-*/page-1.png` and `image file not found`.
  - With TMPDIR: rc=0, with 3965 bytes of OCR output.
- This confirms the claimed mechanism. Without TMPDIR, Python's `tempfile` falls back to `/tmp`, and Homebrew Leptonica does not open the page image there, which causes OCR_PROCESSING_FAILED.

### Tests
- `pytest tests/test_run_e2e.py`: 71 passed, 1 failed. The failure is `test_windows_stop_targets_only_owned_process_tree` (an AttributeError on macOS). It is the same failure the caller reported on main, the test is Windows-specific, and the change does not touch it.
- `ruff check` on the 3 files passes.
- `ruff format --check` reports drift on all 3 files, but the same 3 files already fail on origin/main. The format-diff line count for `tests/test_run_e2e.py` is identical before and after the change (945 vs 945), so the change adds no new format drift.
- Adequacy: the extended `_system_environment` test shows TMPDIR passes through while secrets are still removed, which is a behavioural check for `run_e2e.py`. The new test loads `e2e_backend_server.py` and checks that both allowlists contain TMPDIR, which protects against regression. The OCR failure itself depends on the host's Homebrew setup and cannot be unit-tested portably. It is covered by the probe and the local E2E evidence.
- No existing assertion was changed, removed or weakened. The change only adds assertions.

### E2E evidence (caller-supplied, not rerun by this reviewer, as instructed)
- Before the fix (`main-90115e4-known9.json`): 9 failures.
- After the fix (`tmpdir-e2e-full.json`): 114/117. The 3 remaining failures are onboarding-recovery:6, s3-sandbox-submission:232 and slice-c-recovery:294. These are GoldTier stage-button waits that also fail on main, so they are unrelated to this change.
- The 6 tests that now pass are database-classification 191/196/201/206, responsive-layout:567 and s3-sandbox-submission:752. All of them use OCR or document processing, which fits the root cause.
- This is local evidence only. It is not hosted CI, and hosted CI remains billing-blocked.

### Effect on Windows, Linux and CI
- Windows: TMPDIR is normally not set, and the `if key in` filter skips keys that are absent. Python on Windows uses TEMP/TMP first, so nothing changes.
- Linux and Ubuntu CI: TMPDIR is usually unset, in which case nothing changes. If a runner sets it, the backend uses the runner's own temp directory, which is the correct behaviour.
- No CI workflow changed.

## Findings

- **P3-1 (nit, non-blocking):** `"TMPDIR"` sits between `"TEMP"` and `"TMP"` in both tuples, so the list is no longer in alphabetical order. This has no functional effect.

## Verdict

The change is minimal and fixes the confirmed root cause. It passes a non-secret OS path variable that matches the existing TEMP/TMP pass-through, keeps the allowlist approach intact, adds tests with no regressions, and does not change Windows, Linux or CI behaviour. The usual project rules still apply: Tasha approves the push, Shane merges and decides on the manual-CI exception.

VERDICT: PASS
