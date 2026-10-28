# D-098 — AI model qualification recovery, GPT-OSS-only fallback and flexible spending limits

Date: 2026-10-28. Branch `feat/d098-ai-model-recovery-budget-controls`, stacked on PR #127
(`claude/gracious-lovelace-bjvh2z` @ `65535ceb335dbad8cdca8dce7fd191c64286dfef`; main
`025ebc7`). Owner authority: investigation decisions 1–5 and 6a approved as recommended, then
"D-098 — Authorised Stacked Implementation on PR #127" (flexible limits supersede the US$1
ceilings). Classification: Mock / Local. **No real or paid OpenRouter call was made**; every
provider interaction in the evidence is a mock transport.

## 1. Logout root cause and correction

- The qualification process never touches the real CLM backend (`assistant_eval/runner.py` uses
  an `httpx.MockTransport` with a fake session), so it cannot sign anyone out.
- Every AI Models request (the page polls every 3 s while a run is going) asks the backend
  `/api/auth/me` with the browser's own session; a 401 there becomes a 401 to the browser and
  `api.ts` signs the page out. The backend keeps sessions only in process memory, one per
  account, for 8 hours from sign-in.
- Reproduced offline against the real `AuthenticationService`: a backend restart invalidates
  every session; a second sign-in of the same account ends the first; the 8-hour limit ends it
  even while polling; another account's sign-in does not.
- Correction (no change to lifetime, one-session-per-account or the 401 body): the 401 carries
  `X-Session-End-Reason` (closed codes; digests only, bounded); the sign-in page asks once and
  explains, adding that server-side work keeps running. A run left without its supervisor (an
  assistant restart) is closed as `INTERRUPTED[_BILLING_UNCERTAIN]` within 30 s instead of
  blocking new runs for up to 35 minutes; it is never restarted.

## 2. Changes by commit

| Commit | Scope |
| --- | --- |
| A `6b2d4d6` | Session-end reasons (backend, frontend); supervisor stamp and interrupted-run closing (assistant). |
| B `ac50151` | Outcome classification; decision 6a eligibility across Activate, Rollback, active model, revalidation and start-up; *AI unavailable* state; paid-run confirmation and budget pre-check; escalation block after a quality failure; Model health and recovery UI; two missing safe messages. |
| C `c8bce01` | Flexible daily and lifetime limits; finite key-limit requirement; confirmed raises; one-time `spending_controls` rebuild. |
| D `f435b01` | *Case-data guidance, not AI-generated* label in the chat. |
| E | Decision D-098, project state, IT guide section 12, this report. |

## 3. HR recovery journeys (as implemented)

- **Pass:** card *Qualified*; Activate (manual, quality-unscored acknowledgement as before).
- **Fail, other configuration qualified:** the failed card shows its category, cause, failed
  gates and recommended action; the other configuration stays activatable; nothing switches.
- **Both fail:** no GPT-OSS configuration is activatable; if one was active and its pass is
  superseded or out of date, the service stores *AI unavailable* (audited) and the chat gives
  labelled case-data guidance.
- **Runtime failure of the active model:** unchanged: case-data answer, no switch, no retry;
  breaker-class provider errors stop calls until an operator reconciles.
- **Retry after fixing the cause:** *Retry qualification…* (technical, budget, configuration
  mismatch, cancelled) opens the paid-run dialog with calls, estimate and available amount;
  it starts only on *Start paid qualification* and only if every call fits.
- **Signing back in during a run:** the sign-in page says why the session ended; the page shows
  the running qualification; it was never stopped or repeated.

## 4. Qualification and fallback rules

Eligibility (6a) = newest passing run for the current fingerprint and basis unless a genuine
quality failure (G-3 unsafe line; G-6 below 0.70 with lines written; G-7 cut short or
unverified capacity) came after it. Technical (interrupted, deadline, provider unavailable,
model unavailable), budget (calls refused before sending), configuration, billing-uncertain and
cancelled outcomes never supersede a pass. The same function governs readiness, Activate,
Rollback, `_build_stored` (active model and start-up) and `revalidate` after every run. A
GPT-OSS configuration that stops being usable becomes `ai_unavailable` (never the local
baseline, never a rollback target); a local D-093 profile still reverts to the baseline. No
automatic preferred/backup switching, no automatic qualification, no duplicate paid retry.

## 5. Daily and lifetime controls (C)

| Layer | Before | D-098 |
| --- | --- | --- |
| `budget.daily_cap_for` (admission) | ≤ US$1.00 ceiling | default US$1.00; 0..`MAX_MICRO_USD` (10^12, technical bound) |
| `config.budget_daily_cap_micro_usd` | ≤ 1,000,000 | ≤ 10^12 |
| `spending_controls` CHECK and `valid_controls` | ≤ 1,000,000 | ≤ 10^12 (table rebuilt once, row kept) |
| HR daily raise | no confirmation | amount confirmed + fresh preflight: key limit set, never resets, finite |
| HR lifetime cap | opening usage .. +US$1.00 | ≥ opening usage (≤ 10^12); raise: confirmation + key-limit checks + reconciliation, one preflight |
| Preflight `key.limit_within_allocation` | key remaining ≤ US$1.00 + 1 reservation | CLM use: `key.limit_finite` (finite, set, never resets); harness keeps D-092 |
| Preflight `ledger.cap_within_allocation` | cap − opening ≤ US$1.00 | CLM use: `ledger.cap_above_opening` |

Unchanged: ledger admission order (breaker, in-flight, lifetime cap, daily) in one
`BEGIN IMMEDIATE` transaction; reservations, settlement, abandonment, reconciliation,
breaker reset (operator only), per-call verification, events and spend history; the key and
its provider limit are only read. No path raises a limit without HR's confirmation and a
verified finite key limit, and no limit change resets spend or the breaker.

## 6. Provider-side enforcement

The key's own limit is required (`key.limit_set`, `key.limit_never_resets`,
`key.limit_finite`) by every preflight; a key without one fails, so `RemoteTestModel` refuses
every call before sending and no app limit can be raised. `key.room_for_one_call` still needs
room for one reservation at each preflight (cached up to 300 s), and OpenRouter itself refuses
beyond the key limit (402 → `payment` → breaker). The effective allowance shown and used for
the paid-run pre-check is min(daily remaining, lifetime headroom, key remaining).

## 7. Qualification impact

Basis files changed: `budget.py`, `remote_checks.py`, `remote_test.py`,
`synthetic_boundary.json` (regenerated from string constants). Basis `2bd93aeb8886…` →
`3eb5d0cebcd3925f55fc3ed7d5430610a4705ee7eee79472f8d3ac2b4af8d54c`. **Balanced's existing
qualification is not valid on this code**, nor is any Fast qualification. History is kept;
nothing is marked qualified; at start-up an active GPT-OSS configuration is stored as
*AI unavailable* (`QUALIFICATION_OUT_OF_DATE`, audited). Required after integration (owner
approval, not performed): Balanced paid qualification (the configured manifest, e.g. 2 calls),
and Fast if it will be used.

## 8. Evidence (this content; mocks only)

Run on the commits A–D plus the E test adjustment, Windows, Python 3.12 venv, Node 22.

| Check | Result |
| --- | --- |
| Offline logout reproduction (real `AuthenticationService`) | restart, second sign-in of the same account and the 8 h limit each end a session; another account's sign-in does not |
| Backend full pytest | 3,373 collected: 0 failed, 182 skipped (1,091 s) |
| New backend tests `test_d098_session_end_reasons.py` | 3 passed (with `test_phase13_auth_rbac.py`, `test_s2_persistence_security.py`) |
| Assistant full pytest | 2,617 collected: 2,603 passed, 14 failed. The 14 (`test_required_p2` real-HTTP SSE ×5, `test_streaming_resources` loopback ×7, `test_model_factory` suite guard, `test_phase_b_live` marker) fail identically on the unchanged PR #127 head (2,577 collected, the same 14 failed) and pass when their modules run alone (208 passed): pre-existing, order-dependent, unrelated. |
| New assistant tests `test_d098_recovery.py` | 39 passed (interrupted runs, classification table, paid start, 6a, AI unavailable, flexible limits, migration, safe messages) |
| Adjusted tests | `test_spending_controls.py`, `test_budget_daily.py`, `test_budget_ledger.py`, `test_remote_test.py`, `test_reasoning_configurations.py`, `test_synthetic_eligibility.py` (a paid run now needs room for every call's full reservation) |
| Frontend full vitest | 66 files, 1,152 passed (plus `sessionEnd.test.ts`, D-098 page and panel tests) |
| Frontend `tsc --noEmit`, `npm run typecheck`, `npm run build` | pass (the existing >500 kB chunk warning only) |
| Ruff (`apps/backend scripts tests apps/assistant`) | pass |
| mypy (`apps/assistant ai_assistant assistant_eval`) | pass (53 files) |
| mypy `apps/backend/app` | the two changed modules pass; 12 errors in 7 untouched files (`main.py`, `config.py`, ownership/document services) are pre-existing |
| Synthetic boundary `--check` | current (regenerated from the changed string constants) |
| Paid / real calls | none (mock OpenRouter, fake CLM backend, test ledgers only) |
| Physical Mongo | not applicable: no Mongo or case-data schema change (model-state SQLite only) |

## 8a. Independent Quality Gate

**QG R1 on `6d28401` (tree `51a9755`): HOLD**, with one REQUIRED finding.

- **R-1:** the active model was re-checked against decision 6a only when the activation revision changed, or when the run's own supervisor called `revalidate()`. A run that finished unsupervised (the service restarted inside the 30 s grace) could therefore leave a superseded configuration serving.
  - **Remediation:** the model state now also counts finished runs (`finished_qualifications`). Every request in every process re-checks the active configuration's eligibility when that count changes (`_superseded_check`: qualification rows only, nothing rebuilt), and `revalidate()` uses the same path.
  - **Tests:** a quality failure stops the active model in this and a second process on the very next answer with no `revalidate()` call; a technical or interrupted outcome never stops it.
- **N-1 (recommended):** a run closed as interrupted while its process is still alive can finish its current step. This is accepted and documented. The ledger admits at most `AI_ASSISTANT_BUDGET_MAX_IN_FLIGHT` calls (default 1) across processes in one transaction, so a new run's call cannot overlap one still in flight. The orphan stops at its next heartbeat because its row is closed, and its calls stay within every limit.
- **N-2 (owner to confirm):** raising calls per activation needs no confirmation. Money stays bound by the daily, lifetime and key limits.
- **A-1, A-2 (advisory):** an unrecognised G-8-only failure is classed technical; on start-up with an expired cookie the reason is probed twice. Both are noted, with no change.

A fresh independent review follows the remediation.

## 9. Change classes

API/type: yes (new response fields; `confirm_paid_calls`, `confirm_daily_cap_micro_usd`;
session-end header). Schema: model-state SQLite only (column added; table rebuilt). Connector:
no new connector; preflight checks changed. Configuration: daily cap bound. Business rule:
spending authority (owner-directed). Mapping: none. Auth/security: 401 reason header (no
identity); session lifetime unchanged. Architecture: no new owner. Provider status: unchanged
(Mock/Local; nothing Live). Runtime behaviour: yes, as above.
