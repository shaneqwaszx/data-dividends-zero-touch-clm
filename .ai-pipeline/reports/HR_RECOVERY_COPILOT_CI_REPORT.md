# HR recovery, AI Assistant copilot and CI stabilisation (2026-11-03)

Outcome: implemented and independently reviewed on branch `feat/hr-rectification-assistant-copilot`
from `origin/main` `c233ecd` (verified current on 2026-11-03). Local commits only: nothing is
pushed, no PR is open, nothing is merged or switched on. Evidence class: Local (offline tests,
disposable ledgers, state databases and `mongo:7`; scripted models). No paid call, no live store,
no provider credential, no restart of the running assistant.

## 1. Summary

| Concern | Commit(s) | State |
| --- | --- | --- |
| CI stabilisation and PR #149 follow-ups | `e27f602` | Root causes found and fixed; hosted CI not yet run |
| HR recovery centre (D-116) | `3cf0521`, `c8ec49c`, part of `6b992d0` | Built; within existing authority |
| Copilot answers (D-115 A1-A4) | `99d37b0`, `6b992d0`, `ab20f8d`, `a5edf6c`, `082f06a` | Built behind `AI_ASSISTANT_ANSWER_MODE=copilot` (default `exact_lines`); PROPOSED |
| Case memory lifecycle (D-115 M1-M2) | `99d37b0` | Built, applies in both modes (owner-directed by this assignment) |

The commits are ordered so the CI commit and the HR commits can be published apart from the
copilot commits, which move the qualification basis.

## 2. Files

- CI: `.github/workflows/ci.yml`, `apps/{backend,assistant}/pyproject.toml` (Starlette pin),
  `scripts/run_physical_mongo_tests.py`, `tests/test_run_physical_mongo_tests.py`,
  `tests/test_check_tooling_config.py`, `tests/contract/test_phase_04_ownership_contract.py`,
  `apps/backend/tests/test_{am18_ownership_checkpoint,final_review_editing_real_mongo}.py`.
- HR: `apps/assistant/ai_assistant/{recovery.py,model_admin.py,model_admin_store.py}`,
  `apps/assistant/tests/test_recovery_centre.py`,
  `apps/frontend/src/pages/aiModels/RecoveryCentre{.tsx,.test.tsx}`,
  `apps/frontend/src/pages/AiModelManagement.tsx`, `aiModelConsole.css`, `aiAssistant.ts`.
- Assistant: `apps/assistant/ai_assistant/{copilot.py,case_contexts.py,main.py,config.py,
  telemetry.py,model_qualification.py,synthetic_boundary.json}`,
  `apps/assistant/assistant_eval/copilot_eval.py`,
  `apps/assistant/tests/{test_copilot.py,test_copilot_eval.py}`,
  `apps/frontend/src/pages/AiAssistantPanel{.tsx,.test.tsx}`, `App.tsx`, `aiAssistant.ts`.
- Decisions: `docs/decisions/DECISION_LOG.md` (D-112 clarification, D-115, D-116).

Changed: API (additive: recovery routes, context routes, general chat, `context_id`, health
fields), schema (new `recovery_requests` table in the model state database, created on start),
configuration (`answer_mode`, `context_*`), business rules (copilot checks), auth/security
(new routes under existing capabilities), runtime behaviour (panel memory cleared on leaving a
case). Not changed: CLM backend code, mappings, connectors, provider status, ledgers, limits,
credentials, reconciliation rules, RBAC.

## 3. HR rectification matrix

| Problem | UI action | Server operation | Verification | Limits |
| --- | --- | --- | --- | --- |
| Reconciliation overdue / 7-day chat window expired | Reconcile (opens Spending & Limits) | D-110 preview, confirm, apply | Recovery centre re-reads; new deadlines shown | Blocked (with reasons) while breaker, open, unverified or quarantined calls, runs, markers or P1 are outstanding |
| 24-hour paid window expired | Same reconcile flow | D-110 | Paid deadline shown separately | As above |
| Reconciliation due within 24 h | Same | D-110 | Same | First live use still gated on S1-S3 and P1 (D-110) |
| HR session key missing, ended, invalid or unverified | Enter or replace key; sign in again; Test connection | D-106 credential routes; connection test | Key status, Test connection | Key never shown |
| Server key unavailable | Owner recovery request; Test connection after restore | Recovery request (audited) | Test connection | HR cannot set a server key |
| Daily limit reached | Review daily limit, or wait for reset | D-102 / D-098 controls | Remaining amount | Within ranges |
| Lifetime cap reached | Raise cap with typed confirmation (if below ceiling) or owner request | D-102 / D-098 | Headroom | Ceiling US$30.00 / workspace limit unchanged |
| Breaker open | Owner recovery request with evidence | Recovery request | Request resolvable only when the breaker reads closed | D-110 R8: HR never resets |
| Unverified closed calls | Verify with Test connection (inline, confirmed) | Free preflight verifies in-band | Problem re-checked | A failing call is quarantined, never settled |
| Quarantined / stuck open calls | Owner recovery request | Recovery request | Count reaches zero | Owner reconciliation |
| Run pending | Resolve run (inline, confirmed, after the bound) | D-110 resolve | Run shows applied/failed/unresolved | Ledger never written |
| Run unresolved / marker / P1 missing / never reconciled | Owner recovery request | Recovery request | Server re-diagnosis (only from a full diagnosis) | Owner script |
| Qualification out of date or failed | Test connection, run qualification (paid confirm dialog) | D-098 | Qualification shows current | Paid runs need confirmation and limits |
| Model unavailable | Activate eligible model, roll back, or qualify | Activation / rollback | Active model | Nothing switches automatically |

Deadline: the Claude chat window recorded for 2026-11-07 09:42:37 SGT renews only through a
reconciliation. D-110 R12's fallback (owner CLI reconciliation if HR reconciliation is not
rolled out by 2026-11-05 18:00 SGT) still applies. No live reconciliation was run.

## 4. AI Assistant before and after

Before: the model may only repeat approved catalog lines (ADR-012 C); history comes from the
browser; a case chat is kept per case in the browser.

After (copilot mode, local model only): scope check, then backend access with the user's
session, then case facts and approved knowledge, then reasoning under `copilot.RULES` (guidelines,
not templates), then per-sentence checking. The checks cover grounding, offered actions,
authority and Live claims, document values, citations, assistant self-action claims, UBO
conclusions, ungrounded percentages and capitalised names. Last comes the read-only reply for
change requests. A general onboarding chat is available with no case. External or restricted
models keep exact lines and their D-094/D-095 gates.

## 5. Case memory

- Context opened on the first question, bound to user and case (or general).
- Turns live in process memory only: 16 turns, 8 contexts per user, 30 min idle, 8 h absolute.
- Closed when the case is left, on unmount (sign-out or user change) and on `pagehide`.
- Browser history is ignored when a context is named. Another user's or another case's context
  is refused. Late answers are never added.
- D-105 redacted answer records are not deleted, so the retention conflict is the owner's
  decision (D-115 R1).

## 6. Safeguards

- Preserved: ADR-012 exact lines (default), D-094/D-095 gates, D-104 data access, D-110 R4-R13,
  ledgers, limits, credentials, RBAC, redaction.
- Replaced only in copilot mode, and only if approved: the exact-line rule.
- Awaiting approval: D-115 A1-A4, R1, Q1 (basis: main `d5d882f12e93…`, then #153 `bcd6afc2b454…` and #154 `1cb45edc5939…`, then `f7df76e56ee2…`, a paid
  requalification) and review of the `code_vocabulary` widening (+176/-4; 57/4 of these were
  already stale on main).

## 7. Tests (head `082f06a`, content identical to `a5edf6c` plus decision text)

| Suite | Result |
| --- | --- |
| Backend full (CI-equivalent venv: backend + assistant, Starlette 1.6.0) | 3594 tests: 0 failed, 184 skipped (run at `e27f602` content); `test_ai_assistant_main_integration` 2/2 and contract suite OK at head |
| Physical Mongo (disposable `mongo:7`, CI-equivalent venv) | 177/177 (before the pin: 176/177, reproducing the hosted failure) |
| Assistant full | 3249 tests: 3235 passed, 14 failed. The 14 are the same `Errno 24` loopback tests that fail on pristine main in a long Windows run, and all pass in isolation. |
| Copilot evaluation | 15 scenarios, 14 categories, 6 dimensions: all pass |
| Frontend | 74 files, 1341 tests pass; typecheck and build pass |
| Governance | `check_project_state`, `check_architecture`, `check_policy_authority`, `check_tooling_config`, `check_secrets` all PASS; runner 20, tooling 11, run_e2e 72 unit tests OK |
| Browser E2E (focused: AI Models reconciliation, answer records, streaming, 11 responsive) | 14/14 passed, real Chromium on Windows, disposable `mongo:7`; the full 119-selector run was not repeated |
| Hosted CI | NOT EXECUTED (nothing pushed) |

Limitations:
- The evaluation scores the service's controls with scripted answers, not a real model's
  intelligence. There is no local model on this machine, and paid runs were not authorised.
  For comparison, the historical Fast scores were 2.75/3 overall and 2.24/3 completeness.
- The Ubuntu 24.04 Playwright install is not proven until hosted CI runs.

## 8. Independent review

- QG (`c8ec49c`): PASS WITH NOTES. F1-F6 were remediated in `6b992d0`.
- Re-QG (`6b992d0`): PASS WITH NOTES. N1-N4 and A1 were remediated in `ab20f8d`.
- Re-QG 2 (`ab20f8d`): PASS WITH NOTES. Remediated in `a5edf6c`.
- Re-QG 3 (`a5edf6c`): PASS WITH NOTES. All earlier items were resolved. The remaining R1
  (some genuine case questions without an onboarding word are redirected) and R2 (company
  suffix spelling) both fail closed and are recorded as known limits in D-115 A3 (`082f06a`).

Advisory items not acted on: the close endpoint has no rate limit; a context of a previous user
lingers until idle expiry when a different user signs in on the same tab; the new assistant CI
job's runtime is unmeasured on hosted runners.

## 9. Owner decisions

1. D-115 A1-A4: approve copilot mode (local model only), or keep it off.
2. D-115 R1: D-105 retention (a) keep, (b) record only rated copilot chats, or (c) shorten.
3. Basis move and paid requalification (Claude becomes AI unavailable after merge and restart
   until requalified). Schedule outside demos.
4. Review the boundary `code_vocabulary` additions.
5. Publication: push branches and open PRs (CI first, then HR, then copilot), then hosted CI.
6. Live reconciliation before 2026-11-07 09:42:37 SGT (D-110 R12 fallback date 2026-11-05 18:00 SGT).

## 10. Demo walkthrough

1. **HR recovery.** Sign in as HR, then go to AI Models → Overview → Recovery centre. Read the
   problem list, the blocked-by reasons and the separate deadlines. Run "Verify calls with Test
   connection" (with confirmation) and see "Recovery verified". Record an owner request for an
   open breaker and see that "Mark resolved" stays disabled while the breaker is reported.
2. **General chat.** With `AI_ASSISTANT_ANSWER_MODE=copilot` and a local model, an RM with no
   case open sees "General onboarding help". Ask "What is a UBO?". Then ask "Write me a poem",
   which gets the redirection.
3. **Case analysis.** Open a case and ask "Why is this case blocked?" for a free-form answer
   built from the case facts. Then ask "Approve this case for me", which gets the read-only
   reply first.
4. **Case switching.** Ask a question on case A, then open case B. The case A chat is gone and
   its context is closed (204). Case B starts empty. Return to case A and it starts afresh.
