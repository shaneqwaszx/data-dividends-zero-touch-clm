# D-099 Option B: independent Quality Gate, round 3

**Verdict: PASS**

- **L-4 is resolved.** Each of the three paths now reads the ledger profile without recovering
  it: `anthropic_runtime.check_ledger`, `remote_checks.run_preflight` and the HR lifetime-cap
  endpoint. A ledger is opened (and recovered) only after its profile matches.
- **Claude ledger opens.** Every one goes through `open_own`.
- **The new tests do exercise recovery.** Each one puts an expired open call on the other
  provider's ledger and asserts that the call stays open with the breaker closed. I reverted
  each guarded site on its own in a scratch copy, and the matching test failed every time.
- **GPT-OSS.** No behaviour is weakened. For a correct OpenRouter ledger, the preflight and the
  HR cap still verify, recover and run the same checks as before.
- **No new finding** at Low or above. There is one Info observation (I-1).

## Reviewed content (frozen identity)

| Item | Value |
| --- | --- |
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\assistant-claude-sonnet-console-20261029` |
| Branch | `feat/assistant-claude-sonnet-console` (draft PR #130) |
| Reviewed commit | `ecacbd60d7191d6f362d7d318e11c9e65492e4e2` (HEAD; status clean before this report) |
| Reviewed tree | `8d03dc8d31044f75fa337539a4d34e208d0570c4` |
| Delta reviewed | The whole of `git diff 6196c20 ecacbd6`: 9 files, +344/-32. `d405986` only adds the R2 report. In `ecacbd6`, the code changes are in `anthropic_runtime.py`, `remote_checks.py`, `model_admin.py` and `tests/test_claude_runtime.py`. The doc changes are in DECISION_LOG, AI_MODEL_CONFIGURATION, PROJECT_STATE and the implementation report. |
| Prior reports read | `D099_OPTION_B_QUALITY_GATE.md` (R1 FAIL, M-1) and `D099_OPTION_B_QUALITY_GATE_R2.md` (R2 PASS WITH FINDINGS, L-4) |

## L-4: resolved

**Read-only probe.** `BudgetLedger(path)` plus `verify()` plus `status()` makes no writes.

- `__init__` only stores fields.
- `verify()` and `status()` run inside a `BEGIN IMMEDIATE` transaction, but only `SELECT`
  and `PRAGMA` statements, then commit with nothing changed (`budget.py:394-408`, `:556-628`).
- Only `open()` (`:483-486`) and `recover()` call `_abandon_expired`.
- The probe therefore cannot abandon a call or open the breaker.

**Profile read before any open, at each site.**

- **`anthropic_runtime.ledger_profile` / `open_own` (`anthropic_runtime.py:252-264`).**
  - `ledger_profile` runs the probe.
  - `open_own` raises `LEDGER_PROFILE_MISMATCH` unless the profile is the Anthropic one, and
    only then calls `BudgetLedger.open`.
- **`check_ledger` (`:317-340`).**
  - The profile is read with `ledger_profile`. On a mismatch the function returns after the
    `ledger.profile` failure.
  - On a match, `open_own` opens (and recovers) the ledger, then `verify_calls` runs. This is
    the same order as `open` plus `recover()` before the change.
- **`remote_checks.run_preflight` (`remote_checks.py:492-503`).**
  - The probe runs, the profile is checked, and only then come `BudgetLedger.open` and
    `recover()`.
- **HR `PUT /budget/lifetime-cap` (`model_admin.py:2040-2053`).**
  - The probe runs and the profile is checked before `BudgetLedger.open`, all under
    `selector.change_lock`.
  - A mismatch is still audited and refused as `409 LEDGER_UNAVAILABLE`.

**Every Claude ledger open goes through `open_own`.** I checked this with a grep of
`ai_assistant/` and `scripts/`.

- `open_own` is used by:
  - the `ClaudeTestModel` constructor (`:612`);
  - the `BudgetedChatModel` ledger (`:663`);
  - the per-call limit check (`:710`);
  - `verify_now` (`:742`);
  - `calls_since_start` (`:754`).
- The only other Claude ledger accesses use read-only probes: `status_view` (`:512`),
  `calls_used` (`:758`) and `model_admin._paid_call_uncertain` (`:612`).
- `ClaudeTestModel` is also how a Claude chat activation is built (`model_admin.py:675`), so
  the chat path is covered too.
- The constructor's mismatch code changed from `INVALID_INPUT` to `LEDGER_PROFILE_MISMATCH`.
  It is still mapped to `ProfileConfigError("LEDGER_UNAVAILABLE")`, so callers see no
  difference.

**The new tests exercise recovery.** I checked this by mutation.

- `_with_an_expired_open_call` (`tests/test_claude_runtime.py:379-390`) reserves a call under
  the ledger's own profile and sets its lease to expired. The meta totals stay consistent, so
  `verify()` still passes.
- `_untouched` (`:393-398`) reads without recovering. It asserts that one call is still open,
  the breaker is closed, and the earlier unverified call is still unverified.
- I extracted `ecacbd6` into a scratch directory and, in five separate copies, reverted one
  site to "open first, then check the profile". Each reverted copy failed:

| Reverted site | Failing test (line) |
| --- | --- |
| `check_ledger` read via `BudgetLedger.open` | `test_a_claude_preflight_never_recovers_...` at `:425` (after the preflight) |
| `ClaudeTestModel` constructor only | the same test at `:428` (after the model build). The model-build assertion is independent. |
| `open_own` without the probe | the same test at `:425` |
| `run_preflight` probe replaced by `open` | `test_a_gpt_oss_preflight_never_recovers_...` (`_untouched`) |
| HR cap probe replaced by `open` | `test_hr_never_changes_the_anthropic_ledgers_cap` (`_untouched`) |

- The unmodified scratch copy passed all three tests.

## OpenRouter/GPT-OSS protections: not weakened

**`run_preflight`, for an OpenRouter-profile ledger.** The order is now:

1. probe `verify()` and `status()`;
2. profile check;
3. `BudgetLedger.open` (`verify()` and `recover()`);
4. `recover()` again;
5. `status()`.

- Before the change it was the same sequence minus the leading probe.
- Every check that follows is untouched: `verify_earlier_calls`, `check_ledger`, `check_daily`
  and the return of the opened ledger.
- A missing, corrupt or schema-mismatched ledger is still refused with the same codes,
  because the probe's `verify()` and `_connect()` raise exactly what `open()` raised.

**HR lifetime cap, for an OpenRouter ledger.** After the probe, the endpoint runs the same
`open`/`status` and the same range, `expected_cap`, confirmation, provider-limit,
reconciliation and audit path.

- The only behaviour change is the additive refusal that was already present in R2.

**What the delta does not touch.** No GPT-OSS cap, breaker, verification, key or daily rule
changed. `remote_test.py`, `model_factory.py` and `budget.py` are unchanged in this delta.

**Residual race.** A file swapped between the probe and the open is a local
time-of-check/time-of-use gap. It is negligible here, because one process owns the file and
`open()` re-verifies anyway.

## Docs accuracy

- **DECISION_LOG D-099 C8 P-3:** "neither provider's preflight recovers or verifies the
  other's ledger (its profile is read before the ledger is opened)". This is now accurate for
  both preflights. The basis is quoted as `adec795f61bd…`, which matches.
- **AI_MODEL_CONFIGURATION §13:** the Anthropic ledger path must differ from the GPT-OSS
  ledger path (`LEDGER_PATH_SHARED`). This matches `readiness()`
  (`anthropic_runtime.py:185-187`). The requalification text gives the basis as
  `b4049047884e…` → `adec795f61bd…`, which matches.
- **PROJECT_STATE:** the basis and the "path must differ" note are both accurate.
- **`D099_OPTION_B_IMPLEMENTATION.md`:**
  - The basis line is accurate.
  - The R2 summary is accurate, including which tests now cover which paths.
  - §4a ("checks the ledger profile before `recover()`/`verify_calls()`") is now true.
  - I did not reproduce the "815 passed" figure, because this gate ran only the assigned
    modules. It remains an author claim.
- **Test names and code comments:** the claim that the other ledger is never recovered is now
  backed by code and by tests.

## New findings

None at Low or above.

**I-1 (Info, outside the L-4 claim scope; GPT-OSS code unchanged from `main`).**

- **Where.**
  - The GPT-OSS runtime model build opens its ledger with recovery before it checks the
    profile: `remote_test.py:314`, and `model_factory.py:240-247` via `_build_inner`.
  - So does the operator CLI `scripts/budget_ledger.py` (`status`, `set-cap`, `reconcile`,
    `reset-breaker`; `:107`, `:146`, `:173`, `:182`).
- **Failure scenario.**
  - An operator swaps the two ledger files, so each configured path holds the other
    provider's ledger.
  - `LEDGER_PATH_SHARED` does not catch this, because the two paths differ.
  - Restoring or activating a GPT-OSS configuration then abandons an expired open Claude call
    on the Anthropic-profile file, charges it in full and opens that ledger's breaker. The
    build is then refused.
- **Why only Info.**
  - It fails closed and never writes `verified`.
  - No doc claim covers it: the claims cover the two preflights, the HR cap and Claude-side
    opens.
  - The OpenRouter path's behaviour on `main` is unchanged.
- **Optional hardening.** The `ledger_profile`-style probe could be reused in `build_chat_model`
  and the CLI. It would be purely additive.

**Earlier Info items.** Round-1 and round-2 Info items (R2 I-4, I-5 and the outstanding owner
acknowledgements) are unchanged by this delta.

## Boundary and qualification basis

| Check | Result |
| --- | --- |
| `scripts/build_synthetic_boundary.py --check` | "synthetic boundary is current", exit 0 |
| `synthetic_boundary.json` in `6196c20..ecacbd6` | unchanged (its only change on the branch is the earlier +3 since `541b10f`) |
| `qualification_basis()` on the reviewed tree | `adec795f61bdcdd03c95ea0109db28e1773d4ee038f4b7ea4b2a824c6bd25610`, which equals the expected value |

## Evidence

All runs were offline, from `apps/assistant` with `PYTHONPATH=.`, using
`C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm\.venv\Scripts\python.exe`.

| Check | Result |
| --- | --- |
| `pytest tests/test_claude_runtime.py tests/test_remote_test.py tests/test_spending_controls.py tests/test_d098_recovery.py tests/test_budget_ledger.py tests/test_synthetic_eligibility.py` | 363 collected; 363 passed, 0 failed (one dot per test, with the `-qq` that `addopts` produces) |
| Mutation runs (scratch copies only) | 5 of 5 reverted sites caught; the unmodified copy passes |
| `ruff check` (the 4 changed .py files) | All checks passed |
| `ruff format --check` (the same 4) | 4 files already formatted |
| `mypy` (the same 4; cache in the scratchpad) | Success: no issues found in 4 source files |
| `python scripts/check_secrets.py` (repo root) | Secret scan passed, exit 0 |
| `git diff --check 6196c20 ecacbd6` | clean, exit 0 |

**Not run, as assigned:**

- the full assistant suite (the author runs it separately);
- any network or paid call;
- any read of `.env`.

## Result

**PASS. L-4 is RESOLVED.**

- No new finding at Low or above. I-1 is Info only.
- Reviewed commit: `ecacbd60d7191d6f362d7d318e11c9e65492e4e2`.
- Reviewed tree: `8d03dc8d31044f75fa337539a4d34e208d0570c4`.
- This report is the only file this gate created. Nothing was edited, staged, committed or
  pushed.
