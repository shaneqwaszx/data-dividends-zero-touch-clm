# D-102 Independent Quality Gate: Claude US$30 ceiling and HR-editable Claude limits

Reviewer: independent QG (did not author or remediate the candidate). Date: 2026-10-29.
Verdict: **CONDITIONAL PASS** (equivalent to PASS WITH MINOR FIXES). No Critical, High or
Medium defects. Four Low findings. The condition is the owner's acceptance of D-102, which is
PROPOSED. One Low text fix is recommended before publication.

## 1. Candidate identity

- Worktree: `C:\Users\shane\Desktop\claude-worktrees\claude-hr-spending-d102-20261029`,
  branch `feat/claude-hr-spending-d102`.
- HEAD = base = origin/main = `d90ab6a735e3b181f4cfca8f78e090c9539e1a2b` (ahead/behind 0/0).
  All changes are uncommitted. The index was not touched (no `git add`, not even `-N`).
- Fingerprints (sha256):
  - `git diff HEAD --binary`: `8986033da35df8689d33bbfa6a874d1ea8ed2f019df09f01265a5aebdf818409`
  - untracked `apps/assistant/tests/test_claude_hr_spending.py`: `b88a4a56ad7e17a92b1127f9e6bb5fa19f94da801f5fa3acab3afcb92ec1d40f`
  - combined (diff followed by the untracked file): **`f1d3238785a618abea21a66c4292da3ebde131ed309ff546e543179f7b05c600`**
  - I fingerprinted again after all evidence was collected and got the same values, so all the evidence below applies to this content.
- Files (13 modified, 1 untracked; 827 insertions, 73 deletions; same `--stat` with
  `--ignore-cr-at-eol`, so no EOL churn):
  `apps/assistant/ai_assistant/{anthropic_runtime,config,model_admin,model_admin_store}.py`,
  `apps/assistant/assistant_eval/qualification.py`, `apps/assistant/scripts/budget_ledger.py`,
  `apps/assistant/tests/test_claude_runtime.py`, `apps/assistant/tests/test_claude_hr_spending.py` (new),
  `apps/frontend/src/{aiAssistant.ts,pages/AiModelManagement.tsx,pages/AiModelManagement.test.tsx}`,
  `docs/{PROJECT_STATE.md,decisions/DECISION_LOG.md,integration/AI_MODEL_CONFIGURATION.md}`.
  I read the whole diff and the new test file.

## 2. Findings

### Critical / High / Medium
None.

### Low

**L1. The UI says a calls raise is reconciliation-gated, but it is not.**
`apps/frontend/src/pages/AiModelManagement.tsx:240` (Troubleshooting) says HR sets the daily
allowance, calls and lifetime limit, and that "Raising one, or a paid qualification, needs the
Claude ledger reconciled ... within 24 hours".
The backend gates only daily-allowance and lifetime-cap raises
(`model_admin.py:2302`). A raise of `max_calls` (for example 1 to 20) is accepted with no
confirmation and with a reconciliation 30 days old. Probe
`test_calls_raise_is_ungated` reproduced this (HTTP 200).
This matches D-102 E3 and the GPT-OSS D-098 behaviour, so the code is correct by the stated policy. The page text, however, overstates a safeguard.
Fix: change the sentence to "Raising the daily or lifetime limit ..." (or gate the calls raise if the owner prefers; see section 6).

**L2. Lowering the lifetime cap is refused while no workspace limit is attested.**
`model_admin.py:2348` with `claude_cap_ceiling()` (`model_admin.py:2070`) uses
`min(30_000_000, workspace_limit)`. When `AI_ASSISTANT_ANTHROPIC_WORKSPACE_LIMIT_MICRO_USD=0` (not attested), every cap, including a lower one, is
`CAP_OUT_OF_RANGE` (probe `test_lowering_refused_when_workspace_limit_not_attested`).
D-102 E3 says "Lowering never needs a confirmation or reconciliation", and the
`CLAUDE_NOT_READY` text says limits "can only be lowered". This is fail-closed: no Claude call is possible in that state because readiness refuses it. The documented behaviour is still not quite what happens.
Fix: either document it ("needs an attested workspace limit"), or allow a lowering whenever `opening_usage < cap < current cap`.

**L3. The GPT-OSS controls view counts Claude's calls while Claude is active (pre-existing, made more visible).**
`ModelSelector.calls_used()` (`model_admin.py:530`) returns the active Claude model's
calls. `budget_view()["controls"]` (`model_admin.py:1980`) then shows GPT-OSS's
"calls used / remaining" against the GPT-OSS limit. The probe showed GPT-OSS
`calls_used: 1, max_calls: 20` after a single Claude call.
Main `d90ab6a` has the same behaviour, so D-102 did not introduce it. Now that Claude has its own
`claude.controls.calls_used`, the GPT-OSS panel is misleading. This affects display only; no enforcement is affected.
Fix: return `None` from `calls_used()` for a `ClaudeTestModel` (tests and the UI may need a small update).

**L4. The raise preconditions are read outside the ledger's write transaction (informational).**
`require_claude_raise` (`model_admin.py:2255-2278`) checks freshness, the breaker and open calls on a
separate read. A chat call (which does not take `change_lock`) could open between that check
and the store/ledger write. The impact is negligible: each call is still admitted by the
ledger's own transaction, under the new daily cap and lifetime headroom. The lifetime cap itself is compare-and-set in the
ledger (`expected=`), and `check_cap_change` re-checks reconciliation.
Readiness also does not require the key to be present, which is harmless (more authority with no key cannot spend). No fix required. Record it as accepted residual.

## 3. Security and spending-policy assessment

- **Ceilings** are verified in code and by probes.
  - `LIFETIME_CEILING_MICRO_USD=30_000_000`, `DAILY_CEILING_MICRO_USD=5_000_000`, `MAX_CALLS_CEILING=20`, prompt 32 KiB unchanged.
  - Config bounds: workspace limit `le=30_000_000`, daily `le=5_000_000` with default 1,000,000 (unchanged), calls `1..20` with default 20.
  - `readiness()` re-checks the bounds, which also covers `model_construct`.
  - The SQLite CHECKs on `claude_spending_controls` repeat 1..5,000,000 and 1..20.
  - The store validates with `type(x) is int` (bool refused).
  - The ledger cap is at most min(US$30, attested workspace limit). The route, the per-call preflight (`check_ledger` cap_within_ceiling) and the budget view (`LIFETIME_CEILING_EXCEEDED`) all enforce this. `check_cap_change` and the operator script refuse more than US$30.
- **D-099 safeguards retained** (diff inspection plus the existing suite):
  - dedicated workspace id and the exact four owner attestations, both still server-only;
  - inference-only key regex with the Admin key refused, and no HR key entry;
  - separate Anthropic ledger with a profile check before open (`open_own`) and `LEDGER_PATH_SHARED`;
  - non-resetting lifetime accounting (`set_cap` never resets committed);
  - 7-day/24-hour reconciliation windows unchanged;
  - in-band verification;
  - synthetic-only boundary unchanged (`build_synthetic_boundary.py --check`: current);
  - no automatic fallback (existing tests pass);
  - paid-qualification confirmation unchanged.
- **Authorization.** Both routes take `Admin` (MODEL_CONFIG_MANAGE via the backend actor), `guard_budget` (Origin required, the shared per-admin rate limit of 20 per window), `managed()`, and `recheck()` inside `change_lock`.
  Probes confirmed:
  - no Origin gives 403 `ORIGIN_REQUIRED`;
  - an RM session gives 403 `MODEL_CONFIG_FORBIDDEN`;
  - the 21st request gives 429;
  - bool, float, string, negative, 10^30, extra fields, a missing `expected_revision`, `expected_revision=-1`, a bool confirm, a wrong `expected_cap`, a raise without `expected_cap`, and a confirm mismatch all give 400, 409 or 422, with nothing changed.
- **Audit.** Content-free closed codes are recorded (`CLAUDE_SPENDING_CONTROLS_CHANGED`, `CLAUDE_LIFETIME_CAP_CHANGED`, with applied/refused codes). No key appears in the budget or audit text (candidate test).
- **Fail-closed.**
  - Unreadable controls (table dropped) give `readable:false` and daily 0, so the active ClaudeTestModel refuses and the chat gets the case-data answer with no POST. The GPT-OSS view stays readable (probe).
  - A missing Claude ledger: GET still returns 200, both Claude PUTs give `LEDGER_UNAVAILABLE`, and no file is created by a read (probe).
- **Secrets.** `check_secrets.py` passed. The new test uses the existing split sentinel key. No `.env` was read by me.
- **Policy note.** Moving from US$5/US$1 to US$30/US$5 increases maximum Claude exposure sixfold lifetime and fivefold daily. This is bounded by the ledger cap and the owner-attested workspace limit; the attestation is not machine-verified, and Anthropic's own workspace limit is the outer bound.

## 4. Test evidence (all on the fingerprinted content unless stated)

| Check | Command (cwd) | Result |
| --- | --- | --- |
| Full assistant suite, candidate | `PYTHONPATH=<wt>/apps/assistant python -m pytest -q -p no:cacheprovider -o faulthandler_timeout=600 --junitxml=...` (wt apps/assistant) | 2,855 collected, **2,841 passed, 14 failed, 0 errors**, 589 s. All 14 failures are `OSError: [Errno 24] Too many open files` (junit parsed) |
| Full assistant suite, main d90ab6a | same (main apps/assistant; main has no assistant changes) | 2,844 collected, 16 failed: **the same 14 Errno 24 tests** + 2 `test_synthetic_eligibility` failures caused by the main checkout's untracked UAT PDF (`apps/backend/tests/fixtures/uat/OPQ ... .pdf`). Both pass in the candidate worktree |
| The 14 Errno 24 tests in isolation, candidate | `pytest tests/test_model_factory.py::test_the_suite_guard_blocks_remote_connections tests/test_phase_b_live.py::test_marker_is_not_an_offline_transport tests/test_required_p2.py::test_real_http_sse_framing tests/test_streaming_resources.py::test_loopback_total_deadline tests/test_streaming_resources.py::test_real_chunked_http_enforces_budgets` | **14 passed** |
| Import identity | `ai_assistant.__file__`/`assistant_eval.__file__` under the worktree; `CLAUDE_DAILY_CAP_RANGE` (worktree-only) imports | confirmed |
| Independent probes (outside the worktree) | `scratchpad/qg-d102/probes/test_qg_probes.py` (33 tests, the suite's conftest imported) | **33 passed** |
| ruff check / ruff format --check | `--no-cache` (wt apps/assistant) | pass / 130 files formatted |
| mypy (strict config) | `python -m mypy ai_assistant assistant_eval --cache-dir=<scratch>` | Success, 56 files |
| Frontend full | `npx vitest run` (wt apps/frontend) | **66 files, 1,208 passed** |
| Frontend focused | `npx vitest run src/pages/AiModelManagement.test.tsx src/aiAssistant` | 141 passed |
| Typecheck / build | `npm run -s typecheck`; `npx vite build --outDir <scratch>` (not into the repo) | pass / built |
| Governance | `scripts/check_secrets.py`, `check_project_state.py`, `check_architecture.py`, `check_policy_authority.py` | all PASS |
| Synthetic boundary | `scripts/build_synthetic_boundary.py --check` (wt apps/assistant) | current |
| Hygiene | `git diff HEAD --check`; trailing-whitespace grep on the untracked file | clean |
| Persistence compatibility | DB created by main code, then opened and written by candidate, then reopened by main | OK, no loss; GPT-OSS row untouched |
| Qualification basis | `qualification_basis()` on worktree vs main | `4c54e4dd9dbd7fbec743…e358` vs `33f602653de73f37…7513` (confirmed) |

**Errno 24 classification: confirmed environmental, not a D-102 regression.** The identical 14
tests fail identically in a full run on unmodified main, and all 14 pass in isolation on the candidate. The cause is resource/order dependence of the Windows full run: the SSL context fails `load_verify_locations` after file handles are exhausted.
The implementer's functional failure (`test_every_model_management_message_is_in_the_browser_safe_list`) passes in my full run on the final content.

**Gaps.**
- There is no clean full-suite run (Windows Errno 24 limit).
- No Linux or hosted CI was run (billing-blocked per project memory; not executed here).
- No browser/Playwright check of the new panel: it was covered only by vitest/jsdom.
- No live Anthropic call (prohibited, and not needed).

## 5. Provider isolation

Confirmed both directions:
- **Claude routes leave GPT-OSS alone.** Claude PUTs change neither the GPT-OSS ledger's cap or committed amount nor the GPT-OSS controls (probe `test_isolation_both_ways`).
- **GPT-OSS routes leave Claude alone.** GPT-OSS `/budget/controls` and `/budget/lifetime-cap` leave Claude's row (revision, daily, calls) and the Anthropic ledger cap unchanged (same probe). The existing `test_hr_spending_controls_never_apply_to_claude` passes.
- **Claude route on the GPT-OSS ledger.** With Claude's ledger path pointed at the GPT-OSS ledger, the Claude lifetime route refuses with `LEDGER_UNAVAILABLE` and leaves the GPT-OSS cap unchanged (`open_own` profile check).
- **Separate storage.** Separate table/row/revision (`claude_spending_controls`); `_set_controls` table names are constants.
- **Qualification.** It applies `apply_claude_controls` only to the Anthropic entry, and `apply_controls` only to GPT-OSS.
- **Sync.** `sync_controls` dispatches Claude models to `_sync_claude`, which never reads GPT-OSS controls.
- The only cross-provider leak is the display issue L3, which predates D-102.

Other behaviour verified:
- **Persistence and sync across processes.** A restart (new `ModelSelector` over the same store and ledger) restores the active Claude model with HR values. A second-process store write is picked up by `current()`.
- **Concurrency.** Four concurrent raises at one revision give exactly one 200 and three 409.
- **Open calls and the breaker.** A non-expired open call, or an open breaker, blocks raises with `RECONCILIATION_REQUIRED`. A lowering still succeeds, and the open call is not abandoned.
- **Workspace limit below the ledger cap.** Reducing the workspace limit below the ledger cap makes the view refuse. HR can then lower to the limit with a stale reconciliation, and a cap above the limit gives `CAP_OUT_OF_RANGE`.

## 6. Owner policy decisions still needed

1. **Accept D-102 itself** (PROPOSED). The code enforces the higher ceilings now, so publication and merge should wait for explicit owner acceptance.
2. **Calls raise.** Should a `max_calls` raise (at most 20) need confirmation and a reconciliation? It is currently ungated, consistent with D-098 and E3; see L1.
3. **Lifetime ceiling.** Confirm that HR may raise the lifetime cap all the way to min(US$30, attested workspace limit) with no second approver. This is the current design.
4. **Residual risks.**
   - The workspace limit is attested, not read.
   - The chat reconciliation window stays at 7 days while the daily allowance is now up to US$5 (bounded by the lifetime cap).
   - The raise checks are outside the ledger transaction (L4).
5. **Re-qualification.** The basis change invalidates every earlier GPT-OSS and Claude qualification once merged, so each needs a new, separately approved paid qualification and spend.
6. **Lowering when no workspace limit is attested.** Decide whether this must be possible (L2).

## 7. Verdict

**CONDITIONAL PASS** for the frozen content `f1d32387…c600`.
- The technical acceptance is met: ceilings, HR controls, gates, isolation, fail-closed paths, frontend, docs and the basis disclosure.
- Conditions: owner acceptance of D-102 (section 6) before commit or publication, and the L1 copy fix recommended.
- Any change to the reviewed content needs a delta re-review of the changed files. Valid evidence can be reused, but rerun the frontend tests if `AiModelManagement.tsx` changes, and rerun the assistant tests if `model_admin.py` changes.

## 8. Bounded remediation (optional; each requires delta re-review)

- L1: in `AiModelManagement.tsx:240`, say that only daily and lifetime raises need the 24-hour reconciliation. Adjust any vitest assertion on that text.
- L2: document that lowering the lifetime cap needs an attested workspace limit, or permit `opening_usage < cap < status.cap` when the limit is 0. Add one test.
- L3 (optional, pre-existing): in `ModelSelector.calls_used()`, return `None` for `ClaudeTestModel`. Update the GPT-OSS view tests.
- No change is required for L4.
