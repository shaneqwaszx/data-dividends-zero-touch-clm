# D-102 Independent Delta Re-Quality Gate (amended candidate)

Reviewer: independent re-QG. I did not author or remediate this content. Date: 2026-10-30.
Verdict: **PASS** for the frozen content `e4f58e36…0d75`, as a technical gate. Owner acceptance of
D-102 (still PROPOSED) and owner authorisation of commit and publication are separate
preconditions (see section 6). They are not defects.

## 1. Candidate identity

- Worktree: `C:\Users\shane\Desktop\claude-worktrees\claude-hr-spending-d102-20261029`, on branch
  `feat/claude-hr-spending-d102`.
- HEAD = base = origin/main = `d90ab6a735e3b181f4cfca8f78e090c9539e1a2b`.
- Everything is uncommitted and the index is untouched: 13 modified files plus the untracked
  `apps/assistant/tests/test_claude_hr_spending.py`. The file set is the same as for `f1d32387`.
  `git diff HEAD --stat` gives 916 insertions and 75 deletions.
- Fingerprint: sha256 of `git diff HEAD --binary` followed by the untracked test file.
  - At start: `e4f58e36e17c5cba6e6d2e71aafcece73fc3636be27c5c6e961ae5565ad90d75`.
  - At end: the same value.
  - It matches the expected amended fingerprint, so all of the evidence below applies to it.
- `git status` was unchanged after all runs. The build went to the scratchpad, and no caches were
  written into the repo.

## 2. Disposition of the prior Low findings

| ID | Disposition | Evidence |
| --- | --- | --- |
| L1 calls raise ungated | **Resolved** | See L1 below. |
| L2 lowering refused without attestation | **Resolved** | See L2 below. |
| L3 GPT-OSS view counted Claude calls | **Resolved** | See L3 below. |
| L4 raise checks outside the ledger transaction | **Accepted residual, recorded** | D-102 decision text records it. There is no code change. My assessment is unchanged: the impact is negligible. |

**L1 (calls raise ungated): resolved.**
- **Code.** `model_admin.py` adds `ClaudeSpendingControlsRequest(SpendingControlsRequest)` with
  `confirm_max_calls: StrictInt | None`. It inherits `extra="forbid"` and is used only by
  `PUT /budget/claude/controls`.
- **Raise rules.** A raise is `body.max_calls > current_calls`. When the controls are unreadable,
  `current_calls` is 0, so any value counts as a raise. A raise needs
  `confirm_max_calls == max_calls` and then `require_claude_raise`. That check covers:
  - D-099 readiness;
  - a reconciliation within 24 hours;
  - a closed breaker;
  - no open call.
- **Order of checks.** Revision compare-and-set (CAS), then the daily confirmation, then the calls
  confirmation, then the raise gate, then the store write.
- **Probes passed.** All of these refused and left the stored controls unchanged:
  - a missing confirmation, 11, 9, -10 or None: 400 `CALLS_CONFIRMATION_REQUIRED`;
  - a bool, float, string, list or object confirmation: 422;
  - a stale reconciliation: 409 `RECONCILIATION_REQUIRED`;
  - an open call or an open breaker: 409 `RECONCILIATION_REQUIRED`;
  - not ready (workspace limit 0): 409 `WORKSPACE_LIMIT_NOT_ATTESTED`, with the `CLAUDE_NOT_READY` message;
  - unreadable controls with calls=1: `CALLS_CONFIRMATION_REQUIRED`, and with confirmations but a
    stale reconciliation, `RECONCILIATION_REQUIRED`.
- **Combined daily and calls raise.**
  - Confirming only one value refuses with the other value's code.
  - Both confirmations with a stale reconciliation give 409.
  - Lowering the daily limit while raising calls is still gated by the calls rule.
  - Lowering both succeeds with a stale reconciliation.
  - Both confirmations with a fresh reconciliation give 200.
- **Lowering is still ungated.** It succeeds with an open call, an open breaker or a stale
  reconciliation. Saving an unchanged value needs no confirmation (a stray confirmation is ignored).
- **GPT-OSS is unchanged.**
  - The `SpendingControlsRequest` fields are exactly
    `{expected_revision, daily_cap_micro_usd, max_calls, confirm_daily_cap_micro_usd}`.
  - `confirm_max_calls` on `/budget/controls` gives 422.
  - A GPT-OSS calls raise is still ungated per D-098 (200 in the probe).
  - `MESSAGES` changes are additions only.
  - The new `CALLS_CONFIRMATION_REQUIRED` message is in the frontend `SAFE_ERROR_MESSAGES`, and
    `test_every_model_management_message_is_in_the_browser_safe_list` passes.
- **UI.**
  - The `claude-calls-raise-confirm` checkbox appears only on a raise.
  - Save is disabled until it is ticked, and the save sends `confirm_max_calls`.
  - The confirmation resets when the input, the revision or the save outcome changes.
  - The Troubleshooting sentence ("Raising one ... needs ... reconciled within 24 hours") is now accurate.

**L2 (lowering refused without attestation): resolved.**
- **Code.** In `put_claude_lifetime_cap`, `lowering = opening_usage < cap < status.cap` bypasses
  only the ceiling check. Any other value must still satisfy
  `opening_usage < cap <= min(US$30, workspace limit)`.
- **CAS.** It applies to every request that sends `expected_cap_micro_usd`. `ledger.set_cap(expected=status.cap)` also
  checks it again inside the ledger's write transaction.
- **Ledger rules still apply.** A lowering calls `check_cap_change(raising=False)` (profile, at most
  US$30) and `set_cap` without `allow_raise`.
- **Probes passed** with workspace limit 0, an open breaker and a 40-day-old reconciliation:
  - the equal value (5.00), a higher value (5.000001, confirmed, with expected) and 0 (the opening
    usage) all give 409 `CAP_OUT_OF_RANGE`;
  - an expected cap of 4.00 against the actual 5.00 gives 409 `CONTROLS_CONFLICT`;
  - lowering to 1 micro-USD gives 200.
- **What the lowering did not change:**
  - the breaker is still open;
  - readiness is still `WORKSPACE_LIMIT_NOT_ATTESTED`;
  - the settings dump, including the attestation, is byte-identical;
  - no Anthropic request or POST was made;
  - the GPT-OSS ledger's cap, committed and opening usage are unchanged;
  - the view still reports a refusal, and `max_cap_micro_usd` is 0.
- **No raise after a lowering.** With ceiling 0, a raise (2 to 3, confirmed) gives `CAP_OUT_OF_RANGE`.
- **Cap above a reduced workspace limit.** Workspace limit 3.00, cap 5.00: lowering to 4.00 (still
  above the limit) is now accepted. The new behaviour is still safe because calls stay refused:
  - the budget view gives `LIFETIME_CEILING_EXCEEDED`;
  - the per-call `check_ledger` reports `ledger.cap_within_ceiling ok=False`;
  - a later raise to 3.50 gives `CAP_OUT_OF_RANGE` (candidate test).
- **Lowering below what is already committed.** This is accepted (the ledger has no lower bound
  except `opening_usage`). Calls then stop: the next chat gets the case-data answer and no POST is
  sent. This only reduces authority.
- **UI.** `capValid` allows `cap < current` when `max_cap` is 0, and the raise confirmation is not
  shown on a lowering. The new vitest checks that the body sends `confirm_cap_micro_usd: null` and
  the cap that was shown.

**L3 (GPT-OSS view counted Claude calls): resolved.**
- **Code.** `ModelSelector.calls_used()` no longer has the Claude branch, so it returns None for
  anything that is not a `RemoteTestModel`. `claude_calls_used()` serves only Claude. The
  only callers are `budget_view` (GPT-OSS) and `claude_budget_view` (Claude), which I checked by grep.
- **Claude active, 2 Claude calls.**
  - The GPT-OSS view shows `calls_used` = None and `calls_remaining` = None.
  - Claude's view shows `calls_used` = 2, and `selector.calls_used()` is None.
- **GPT-OSS active, 1 GPT-OSS call.**
  - The GPT-OSS view shows `calls_used` = 1.
  - Claude's view shows `calls_used` and `calls_remaining` as None, and `claude_calls_used()` is None.
- **Existing tests.** `test_spending_controls.py` (GPT-OSS counts 2/18, 2/0, 3/0) passes.

## 3. New findings

No Critical, High or Medium findings.

**Low**

**N1. The lifetime help text says "lowering it is always allowed".**
`apps/frontend/src/pages/AiModelManagement.tsx:345` (ClaudeLimits lifetime help text).
- The sentence overstates the rule. A lower value must still be above the opening usage, the
  shown cap must still match (CAS), and the Anthropic ledger must exist and be healthy.
- The same sentence states "may be set above the opening usage", and the inline validation message
  is accurate, so a user cannot actually be misled into a bad save. This is wording only.
- Optional fix: "lowering it (above the opening usage) needs no confirmation or reconciliation".
- It does not block the gate.

**Informational**

**I1 (pre-existing pattern).**
- **Scenario.** Claude's controls table is unreadable, and a client bypasses the UI, which disables
  Save when `readable` is false. It then passes both confirmations and a fresh reconciliation.
- **Result.** `put_claude_spending_controls` reaches the store write. The store raises, and the
  route returns an unhandled HTTP 500 with no refusal audit row. Probe
  `test_l1_unreadable_controls_fresh_write_outcome` showed status 500.
- **Assessment.** It fails closed: nothing is written, and Claude stays at a daily allowance of 0.
  The GPT-OSS route has the same shape (only `RevisionConflict` is caught), and this path is
  unchanged from `f1d32387`. No action is required.

**I2.** Claude's controls form disables Save when `controls.readable` is false, but the lifetime
form does not depend on it. This is correct: the cap lives in the ledger, not in the controls table.

## 4. Test evidence (on `e4f58e36…`; `ai_assistant.__file__` and `assistant_eval.__file__` are under the worktree)

| Check | Command (cwd) | Result |
| --- | --- | --- |
| Independent re-QG probes | `PYTHONPATH=<wt>/apps/assistant python -m pytest -p no:cacheprovider -o faulthandler_timeout=600 --rootdir=. <scratch>/qg-d102-r2/probes/test_reqg_probes.py` (wt apps/assistant) | **24 passed** |
| Focused assistant suites | `pytest -q -p no:cacheprovider -o faulthandler_timeout=600 tests/test_claude_hr_spending.py tests/test_claude_runtime.py tests/test_claude_console.py tests/test_d098_recovery.py tests/test_model_management.py tests/test_remote_test.py tests/test_budget_cli.py tests/test_spending_controls.py` | exit 0. **378 collected and 378 passed**: 15 + 72 + 50 + 79 + 52 + 67 + 17 + 26 by `--co`, with no F or E in the output |
| ruff check / format | `ruff check --no-cache .`; `ruff format --check --no-cache .` | All checks passed / 130 files formatted |
| mypy | `mypy ai_assistant assistant_eval --cache-dir=<scratch>` | Success, 56 files |
| Frontend full | `npx vitest run` (wt apps/frontend) | **66 files, 1,210 passed** (1,208 before, plus the 2 new tests) |
| Typecheck / build | `npm run -s typecheck`; `npx vite build --outDir <scratch>/qg-d102-r2/fe-dist` | pass / built |
| Governance | `scripts/check_secrets.py`, `check_project_state.py`, `check_architecture.py`, `check_policy_authority.py` | all exit 0 |
| Synthetic boundary | `scripts/build_synthetic_boundary.py --check` | "synthetic boundary is current" |
| Qualification basis | `qualification_basis()` | `4c54e4dd9dbd7fbec743371722eacf1d07fd0b8645983ac9035a97422110e358` (identical to `f1d32387`) |
| Hygiene | `git diff HEAD --check`; trailing-whitespace grep on the untracked test | clean |

**Basis.**
- `BASIS_FILES` (`model_qualification.py:57`) contains `anthropic_runtime.py`, `budget.py`,
  `anthropic_chat.py`, `anthropic_profiles.py`, the remote/synthetic files and the core runtime.
- It does not contain `model_admin.py`, `model_admin_store.py`, `qualification.py`, the frontend or
  the docs.
- The remediation touched only files outside the basis, and the computed basis is unchanged.

**Gaps (stated honestly).**
- **No full assistant-suite rerun by me.** It was optional, and only `model_admin.py`, tests,
  frontend and docs changed.
  - The implementer reports 2,860 collected, 2,846 passed and 14 failed, all `OSError: [Errno 24]`.
  - The prior QG independently showed that the same 14 ids fail identically on unmodified main and
    pass in isolation.
  - This is an environmental Windows limitation, **not a clean full-suite PASS**.
- No hosted or Linux CI (billing-blocked; not executed).
- No browser or Playwright check: vitest/jsdom only.
- No live Anthropic call (prohibited, and not needed).

## 5. Provider isolation and D-099 safeguards

- **Isolation in both directions holds.**
  - Claude routes write only `claude_spending_controls` and the Anthropic ledger. The GPT-OSS store
    row was equal before and after a Claude lower and a Claude raise (probe).
  - The GPT-OSS ledger was unchanged by a Claude lifetime reduction (probe).
  - The GPT-OSS request schema and route are unchanged.
  - L3 removes the last display leak.
  - The prior QG's isolation probes cover code paths that did not change in this delta.
- **Authorization is unchanged.** Both Claude routes still use:
  - `Admin` (MODEL_CONFIG_MANAGE);
  - `guard_budget` (Origin required, the shared per-admin rate limit);
  - `managed()`;
  - `recheck()` inside `change_lock`;
  - content-free closed audit codes, including the new `CALLS_CONFIRMATION_REQUIRED`.
- **The D-099 safeguards are intact.** The delta does not touch any of them:
  - ceilings (US$30 / US$5 / 20 calls);
  - readiness and the four attestations;
  - the inference-only key and no HR key entry;
  - the separate ledger and the `open_own` profile check;
  - non-resetting accounting;
  - the 7-day and 24-hour reconciliation windows;
  - in-band verification;
  - no automatic fallback;
  - the synthetic-only boundary (current);
  - paid-qualification confirmation.
  - The probes and the focused suites confirm that L2 reductions cannot enable Claude or reach Anthropic.

## 6. Remaining risks and owner decisions

1. **Accept D-102** (PROPOSED). This includes the L1 tightening, which the owner approved, and the
   L2 semantics: a strictly lower cap is allowed even without attestation, or when the cap is above
   a reduced workspace limit.
2. **Authorise commit and publication** of the reviewed content `e4f58e36…`, unchanged.
3. **Residual risks, unchanged from the prior QG:**
   - L4 (raise checks outside the ledger transaction);
   - the workspace limit is attested, not read;
   - the chat reconciliation window stays at 7 days while the daily allowance can be up to US$5;
   - up to six times the previous lifetime exposure.
4. **Re-qualification after merge.** The basis is `4c54e4dd…`, so every earlier qualification
   becomes stale. GPT-OSS and both Claude configurations then each need a separately approved paid
   qualification.
5. **Optional:** the N1 wording fix. Any change needs a delta re-review of `AiModelManagement.tsx`
   and a vitest rerun.

## 7. Verdict

**PASS** for the frozen content `e4f58e36e17c5cba6e6d2e71aafcece73fc3636be27c5c6e961ae5565ad90d75`.
- L1, L2 and L3 are resolved, and L4 is recorded as an accepted residual.
- There are no new defects above Low, and N1 is optional wording.
- Readiness for publication still depends on the owner's acceptance of D-102 and explicit
  commit and publication authorisation. The Errno 24 full-suite limitation stays disclosed as
  environmental.
