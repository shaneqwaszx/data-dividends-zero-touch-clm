# D-098 recovery view, qualification UX and flexible spending limits — evidence

Branch `claude/gracious-lovelace-bjvh2z-recovery`, stacked on PR #127's head `65535ce` (D-097),
whose base is main `025ebc7`. Offline only: no real or paid OpenRouter call, no key, no ledger
outside the tests' temporary directories.

## 1. Qualification sign-out: investigation

| Mechanism | Evidence | Result |
| --- | --- | --- |
| Qualification code path | `post_qualification`, the supervisor thread and `qualify_model.py` never touch the HR session; the harness talks to a mock CLM backend (`eval-session`) | no 401 source |
| Assistant auth (`model_admin.load`) | every admin request asks the backend `/api/auth/me` with the browser's cookie; a backend 401 becomes a 401 | correct; only reflects the backend |
| Frontend | `api.ts`/`aiAssistant.ts` treat any 401 (assistant included) as a session end and sign out; the page polls the overview every 3 s while a run is in progress | a single 401 during a run signs HR out (by design) |
| Backend sessions (`authentication.py`) | in memory; 8 h TTL; **one session per account** (a new login removes the earlier session); a changed security version removes it | each produces a 401 on the next poll |
| Backend restart | sessions are not persisted; `docs/UI_DEMO_QUICK_START.md` runs the backend with `--reload` (a source change restarts it) | every session ends |

Not reproduced offline: the owner's run had no captured backend log or audit trail at the
moment of sign-out. The most likely causes are the same HR account signing in elsewhere (another
browser, tab after a cleared cookie, a script) or a backend restart; both are legitimate session
ends and are not weakened here. Added instead: the run is unaffected (test
`test_a_qualification_outlives_the_session_that_started_it_and_is_never_repeated`), the page says
so, and a refused session during a run is logged and audited once a minute (`SESSION_REFUSED`,
codes only). To pin the cause next time: look for `SESSION_REFUSED` in the AI Models audit, and
check whether the backend restarted or the account signed in elsewhere at that time.

## 2. Hardcoded restrictions audited

| Place | Before | After |
| --- | --- | --- |
| `budget.py` | `DAILY_CAP_CEILING_MICRO_USD` 1,000,000; `daily_cap_for` refused more | `DEFAULT_DAILY_CAP_MICRO_USD` 1,000,000; valid 0..`MAX_MICRO_USD` (10^12) |
| `config.py` | `budget_daily_cap_micro_usd` le=1,000,000 | le=10^12 |
| `remote_checks.py` | `key.limit_within_allocation` (remaining ≤ US$1 + one reservation); `ledger.cap_within_allocation` (0 < cap − opening ≤ US$1) | removed; `ledger.cap_above_opening` (opening < cap ≤ 10^12). `key.limit_set`, `key.limit_never_resets`, `key.room_for_one_call` unchanged |
| `remote_test.py` | `daily_cap_ceiling_micro_usd` | `daily_cap_default_micro_usd`; provider view adds key limit, usage, reset; `account_credits` null |
| `model_admin_store.py` | CHECK daily ≤ 1,000,000 | CHECK ≤ 10^12; D-096 table migrated in one transaction, row kept |
| `model_admin.py` | lifetime ≤ opening + US$1; daily ≤ US$1; no daily-raise confirmation | lifetime opening..10^12; raises (both) need confirmation and a fresh preflight (`key.limit_set`, `key.limit_never_resets`, breaker closed/no open call, usage reconciled) |
| Frontend | inputs and texts capped at US$1.00 / opening + US$1.00 | no ceiling text; daily-raise confirmation; key limit/usage/reset; "Account credits: not available" |

Unchanged: micro-USD integers, the ledger's overflow checks and `BEGIN IMMEDIATE` admission
(daily, lifetime and breaker together), read-only provider refresh, reconciliation, the
non-resetting key requirement, the US$0.30 A/B authorisation (not run).

Limitation: OpenRouter's current-key reply gives the key's limit, remaining, usage and reset,
not account credits; the page says credits are not available rather than estimating them.

## 3. Qualification compatibility

- Commit 1 (recovery, confirmation, diagnostics): no basis file changed; basis
  `2bd93aeb8886…` unchanged; `synthetic_boundary.json` current.
- Commit 2 (ceilings): `budget.py`, `remote_checks.py`, `remote_test.py` are basis files;
  basis → `73fdcd75f559…`; `synthetic_boundary.json` byte-identical. BASIS_FILES unchanged (no
  file omitted). Every stored qualification is out of date: Balanced and Fast need a new paid
  qualification (2 manifest calls each); a stored GPT-OSS activation reverts to no AI model
  (case-data answers only) at the next start. No qualification was marked passed. Paid requalification needs separate
  authorisation.

## 4. Independent Quality Gate

- **R1 FAIL**, one REQUIRED finding: a G-3/G-6/G-7/G-8 failure could be re-run until a run
  passed (the docs said such results are never retried away). Advisories: "an earlier pass is
  still valid" read as activatable after a later failed run; the daily-raise check compared
  against controls read under a revision other than the one the change replaces; the remote
  "Run qualification" did nothing without a cost view; stale US$1.00 wording in messages and
  comments; the environment default is not provider-checked.
- **Remediation:** the server refuses a new run of the same configuration and code after one of
  those gates (`ESCALATION_REQUIRED`, audited) until IT changes its settings or the code changes;
  the page words the earlier pass correctly; a daily raise under another revision is refused
  (`CONTROLS_CONFLICT`) before any provider check; without a cost view the server's own refusal
  is shown; wording and docs corrected. Tests added for each.

- **R2 FAIL** (fresh reviewer), one REQUIRED finding: the block was read outside the start's
  transaction, so a run that failed G-3 while a new start was under way could still be
  followed by a new run. Advisories: the "cannot be retried away" text also showed for
  operator-side results; a stale ceiling docstring in `budget.py`; no revision protection on
  lifetime-cap raises; the block looked at the latest run only.
- **Remediation:** the block is decided inside `begin_qualification`'s `BEGIN IMMEDIATE`
  transaction over every earlier failed run of the same profile, fingerprint and basis; the
  page words operator-side results separately; the docstring is corrected; a lifetime change
  names the cap the page showed (`expected_cap_micro_usd`, required for raises) and is refused
  with `CONTROLS_CONFLICT` if it changed. Tests added (a failure recorded mid-request, switching
  back, a stale lifetime raise and decrease).

## 4a. Owner review round (2026-10-28)

- Automatic Fast → Balanced switching: not approved; nothing implemented.
- Lifetime-cap race: `BudgetLedger.set_cap(expected=...)` compares the cap inside its own
  write transaction; tests interleave the operator's change during the HR raise's provider
  check (refused, operator value kept, spend/calls/daily view unchanged).
- GPT-OSS-only fallback: an unusable GPT-OSS activation reverts to no AI model
  (`case_data_only`), never to the environment baseline; the undo of a failed activation
  restores exactly the earlier activation. One existing test
  (`test_a_daily_limit_above_one_dollar_survives_a_restart_and_keeps_todays_spend`) had passed
  only because a restarted selector without the key reverted to the baseline mock, which still
  answered as "model"; it now builds the selector as the service does and checks that GPT-OSS
  answers.
- The recovery view separates an activation that stays valid from eligibility for a new
  activation (`active_qualification_current`).
- The sign-out remains **not reproduced**; no root-cause fix is claimed.

## 5. Tests (offline)

Backend: `tests/test_recovery.py` (classification, Fast-fails-Balanced-active, confirmation,
call-limit refusal, duplicate start, session revoked mid-run with exactly the manifest's
calls, RBAC, no key in responses, a failed run after a pass); `tests/test_spending_controls.py`
D-098 section (daily above US$1 confirmed and verified, unbounded/resetting/unreadable key and
unreconciled usage refused for both raises while decreases pass, strictest limit, restart,
concurrent administrators, D-096 store migration); `tests/test_budget_daily.py` (default not
ceiling; enforcement at US$2.50 to the micro-dollar); `tests/test_phase_b_live.py` (a finite
key limit above US$1 passes; unbounded or resetting fails). Frontend: recovery panel,
retry confirmation, raise confirmation, key figures.
