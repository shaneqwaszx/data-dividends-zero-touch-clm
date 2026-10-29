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
`b4049047884e9f2897a6ac3ebd232ccfe6482e6a6beb82aa50e6304ecb00fd22`. **Balanced's existing
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

## 8b. Owner Option A: canonical candidate plus two safeguards from PR #128 (2026-10-29)

The owner chose this branch as the canonical D-098, a proposed replacement for draft PR #128 (`d16dcbe`, later `4648b9c`), with two #128 safeguards ported in commit `2fae796`. Main `f88e170` (#127 squash) has the same tree as `65535ce`; it is merged in at `d3e16bf` with no content change.

### Feature checklist (source → canonical)

| Feature | Source | Status |
| --- | --- | --- |
| Session-end reasons (backend header, sign-in notice) | local | preserved |
| Interrupted-run closing (supervisor stamp) | local | preserved |
| Decision 6a across Activate, Rollback, active model, revalidation and start-up | local | preserved |
| Outcome classification (budget ≠ quality; billing ≠ quality) | local | preserved |
| Paid run: confirmed call count, every call's full reservation must fit | local | preserved |
| Recovery Centre, paid-run dialog, AI-unavailable banner | local | preserved |
| "Case-data guidance, not AI-generated" chat label | local | preserved |
| Safe error messages (plus a test that every message is listed) | local | preserved |
| Flexible daily and lifetime limits, finite key limit required | local / #128 (equivalent) | preserved |
| F1 lifetime-cap compare-and-set in the ledger write (`expected_cap_micro_usd`, `set_cap(expected=)`) | #128 Z7 | **imported**; deterministic interleaving test |
| F2 fail-closed start-up: unreadable state, failed or conflicting revert writes, no baseline stand-in | #128 R4/R5 | **imported** |
| F2 extensions: lost revert audit written later; stored revision shown so HR activation is never blocked | #128 advisories A2/A3 | **imported and fixed** |
| Key limit, usage and reset shown; account credits never read | #128 | **imported** |
| Exhausted key = owner action (`ESCALATE_KEY_OWNER`, `PROVIDER_KEY_LIMIT_EXHAUSTED`) | owner instruction | **added** |
| Latest-run-only activation; Z6 keeping a superseded model active; G-8 as quality; one-call paid pre-check | #128 | **excluded** (conflicts with 6a and the owner decisions) |
| Automatic Fast→Balanced switching | #128 (design only) | **excluded** (not approved) |
| Requalification plan document | #128 | not imported; impact recorded in §7 and D-098 R9 |

### Evidence on `2fae796` (docs-only changes since)

| Check | Result |
| --- | --- |
| Focused assistant suites (D-098, spending, budget, remote, model management, reasoning, eligibility, Phase B live, credentials) | 446 passed, 0 failed |
| F1 | HR raise during an operator lowering is refused, the operator's cap stands, spend/calls/daily/events unchanged; stale view refused; ledger `CAP_CHANGED` |
| F2 | Unreadable state → no model; revert write failure → no model at −1, retried, stored and audited once; 3 conflicts → no baseline stand-in; lost audit written later; HR activates while a revert is pending; local profile → baseline |
| Assistant full | 2,630 collected: 2,616 passed, **14 failed**, all `OSError: [Errno 24] Too many open files` raised from `ssl` while loading certificates (`test_required_p2` ×5, `test_streaming_resources` ×7, `test_model_factory` suite guard, `test_phase_b_live` marker) |
| Same 14 on the unchanged PR #127 head | identical 14 failures (2,577 collected), same error |
| Those 4 modules on their own at `2fae796` | 289 passed, 0 failed |
| Frontend full vitest / build | 66 files, 1,154 passed / built |
| Backend full | **rerun NOT_COMPLETED**: stalled at zero CPU (the known Windows pytest socketpair stall) and stopped. The last complete run (3,373 tests, 0 failed, 182 skipped) used backend code identical to the current head (no `apps/backend` change since `6d28401`). |

**The 14 failures.** File-handle exhaustion late in the single-process run: the C runtime's per-process file limit is reached by handles that earlier tests leave open, until `ssl.create_default_context()` cannot open the certificate store. This is pre-existing: the same 14 tests fail with the same error on unchanged PR #127, the failure count does not grow with D-098's 53 extra tests, and the tests pass on their own. It is not a D-098 leak, but it is a real test-hygiene defect, recorded as a separate follow-up; no test was changed or skipped to hide it.

## 8c. Final independent QG round on `3846010`: HOLD, remediated

The QG and security review of `3846010` (tree `3e08ac0`) found everything else in order. That covers the session-end header, the frontend probe, CSRF and origin checks, F1, budget authority, migration, basis, safe messages, the 14 failure modules (654 tests in one process passed) and the scope relative to main.

- **Q-1 (REQUIRED): F2 port incomplete.** `ModelSelector.apply` undid a failed activation to `previous or baseline`. From "AI unavailable", that put the baseline, or a local last-good profile, in place of GPT-OSS.
  - **Fix:** the undo restores exactly the activation stored before, "AI unavailable" included, as #128 does.
  - **Tests:** a build failure after the compare-and-set, from "AI unavailable" with the last good being the same profile and with it being a local profile. Both now stay "AI unavailable", with no model.
- **Q-2 (RECOMMENDED, fixed): decision 6a.** An earlier category (billing, budget, technical) could hide a genuine quality failure in the same run.
  - **Fix:** whether a pass is superseded is now decided from G-3, G-6 with lines written, and G-7, whatever the category. Billing and quality stay distinct categories, and billing alone never supersedes a pass.
  - **Tests:** all three combinations, plus billing alone.
- **Advisories, not changed:**
  - **A-1:** `close_interrupted` per-run store errors propagate (they fail closed).
  - **A-2:** a locked state database can hold one request for several SQLite timeouts. This is bounded, at 3 attempts.
  - **A-3:** test-only sqlite connections are closed by reference counting.

The qualification basis after this round is `b4049047884e9f2897a6ac3ebd232ccfe6482e6a6beb82aa50e6304ecb00fd22`. A fresh independent review of the remediated content follows.

## 8d. QG round on `8200700`: HOLD, remediated

The review confirmed the Q-1 fix and everything else, including the security review. It found one REQUIRED regression introduced by the Q-2 fix.

- **Q2-R1:** a provider timeout or rate limit mid-answer marks an answer cut short (`stream_partial`), which feeds G-7. Q-2 had counted every G-7 failure as a quality failure, so a temporary outage could take a pass away and block re-runs, contradicting R4 and §12.
  - **Fix:** G-7 is a quality failure only in two cases. Either the answers cut short beyond those explained by `stream_partial` exceed `G7_MAX_CUT_SHORT`, or capacity is unverified or a prompt is above the bound. A G-7 failure explained only by provider failures is technical (`MODEL_UNAVAILABLE`, retryable), and the earlier pass is kept.
  - **Tests:** the timeout and rate-limit cases, the G-7-only provider case, genuine cut-short answers beyond the provider failures (supersedes), and capacity or oversized prompts (supersedes).
- **A-1:** the `ACTIVATION_UNDONE` audit now goes through the same retry queue as the start-up revert.
- **A-2, A-4:** the R12 and §12 wording are corrected.
- **A-3:** `close_interrupted` store errors still fail closed. Unchanged.

The qualification basis is unchanged (`b4049047884e…`), because `model_admin.py` is not a basis file.

## 8e. QG round on `4e588a4`: HOLD, remediated (owner-authorised round, 2026-10-29)

The review confirmed the Q2-R1 fix, Q-1/F2, F1, the budget controls, the security review and the basis.

- **R5-1 (required):** a superseding quality failure behind a technical or budget category kept that category's retry advice. HR was told to retry, the server refused the re-run, and no escalation summary was offered.
  - **Fix:** a superseding failure now always advises its quality escalation: a developer for G-3/G-6, IT for G-7. A billing category keeps the operator, first.
  - **Tests:** the action is asserted for each combination.
- **R5-2 (recommended):** the G-7 check used the rounded rate and failed at exactly 10%.
  - **Fix:** whole answers are compared (`round(rate × answers) − stream_partial > 10% × answers`). Malformed counts fail safe.
  - **Tests:** the exact-threshold case and one above it.
- **R5-3 (owner decision):** a local profile's capacity probe that fails for transport reasons still supersedes its pass. This fail-safe behaviour is kept and documented in §12. GPT-OSS is unaffected.
- **Advisories:** the §12 table now lists "provider refused" under technical (operator), matching the code.

The basis is unchanged (`b4049047884e…`).

## 8f. Pre-merge verification on `f1f4d16` and the out-of-date advice fix (owner-authorised, 2026-10-29)

**Verification on `f1f4d16` (mocks only; nothing spent)**

| Check | Result |
|---|---|
| Backend full pytest | 3,373 collected: 3,191 passed, 0 failed, 182 skipped (21 min). The earlier stall did not recur. |
| Assistant full pytest | 2,647 collected: 2,633 passed, 14 failed. All 14 are `Errno 24`. |
| Cause of the 14 | Four modules (`test_answer_records`, `test_knowledge_review`, `test_knowledge_answers`, `test_fix_prefill`) leave each test's Chroma index open, about four HNSW files each. Open C-runtime descriptors reach about 520, past the 512 stream limit, so later certificate loads fail. Those four modules followed by the four failing modules reproduce the same 14 failures on D-098 and on main `f88e170`. The failing modules alone pass 289/289. Pre-existing, test-only and outside D-098's scope. |
| Playwright E2E (disposable `mongo:7`, Tesseract) | 115/116. `responsive-layout.e2e.ts:807` timed out waiting for the login page, then passed 3/3 in isolation. |
| Windows isolated smoke (own ports, copied state, no key) | Model-state and ledger migrations verified on copies, originals unchanged. Start-up gives "AI unavailable" with no substitution. The paid confirmation is enforced. Session-replaced message shown. Labelled case-data answers. |

**Finding (owner: fix before merge).** The Recovery Centre treated every pass as qualified. A
pass made for an earlier fingerprint or qualification basis read "Retry worthwhile: No" and
"Recommended action: Nothing to do", while the same configuration could not be activated. Every
install is in this state straight after merge, because D-098 changed the basis.

**Fix.** `diagnose(item, current=…)`: a pass that is no longer current is classified as
`configuration` with cause `OUT_OF_DATE`, action `RUN_AGAIN` and `retryable` true. It never
supersedes a pass. Only a pass is reclassified: a failure keeps its own category, escalation
and decision-6a effect, current or not. `eligible_run` keeps its behaviour. It now shares one
helper with `superseding_run`, and both still read only current runs. The page shows "Qualification out of date" and recommends a new qualification
with the current configuration and code. The paid run still goes through the confirmation
dialog and the spending checks, and activation stays blocked until a current run passes.
Nothing starts automatically.

Existing closed codes are reused, so the synthetic boundary vocabulary is unchanged. A new
`REQUALIFY` action was tried first. It added a word to the boundary file, a basis file, and
moved the basis to `ceeba48d…`, so it was withdrawn. The basis remains
`b4049047884e9f2897a6ac3ebd232ccfe6482e6a6beb82aa50e6304ecb00fd22`.

**Tests.**

- Backend:
  - a pass that is out of date by basis, and one out of date by fingerprint: the advice is to requalify, activation is refused, an unconfirmed start is refused, and a confirmed run passes and becomes current;
  - a current pass keeps its qualified state with no retry advice;
  - a current quality failure after an out-of-date pass still blocks a rerun;
  - unchecked key limits and an open breaker still refuse the run;
  - failures (quality, budget, billing) are never reclassified as out of date.
- Frontend:
  - the out-of-date card's text, the paid confirmation before any request, and Activate disabled;
  - a current pass with no retry button.

**QG of `023f0d0`: HOLD, remediated.**

- **R-1 (required):** the card used only the latest run. In one ordering, a genuine quality failure was shown as merely out of date:
  1. a current G-3 failure;
  2. the configuration or code changes, and a run passes;
  3. the configuration changes back.

  The card offered "Run new qualification…", which the server refuses with `QUALIFICATION_ESCALATION_REQUIRED`.
- **RC-1 (recommended, same cause):** a later retryable failure, current or stale, on top of a current quality failure also offered a retry the server refuses.
- **Fix:** when decision 6a blocks a configuration (`QUALIFICATION_SUPERSEDED`), the overview takes the diagnosis from the superseding failure (`superseding_run`), whatever run is latest. HR sees the quality escalation and no retry.
- **Tests:** the out-of-date pass, the stale technical failure and the current technical failure orderings, each with the server's refusal, plus the frontend card.
- **RC-2:** this section's wording is corrected.
- **Advisories, unchanged:** a local profile's "Run new qualification…" starts at once, like the existing retry, because local runs are unpaid. The baseline is never shown in the Recovery Centre.

## 9. Change classes

API/type: yes (new response fields; `confirm_paid_calls`, `confirm_daily_cap_micro_usd`;
session-end header). Schema: model-state SQLite only (column added; table rebuilt). Connector:
no new connector; preflight checks changed. Configuration: daily cap bound. Business rule:
spending authority (owner-directed). Mapping: none. Auth/security: 401 reason header (no
identity); session lifetime unchanged. Architecture: no new owner. Provider status: unchanged
(Mock/Local; nothing Live). Runtime behaviour: yes, as above.
