# D-098 paid requalification of GPT-OSS 120B Balanced and Fast — Windows-local plan (NOT EXECUTED)

Status: **plan only.** No paid call is authorised by this document. The US$0.30 A/B
authorisation (PR #127) is separate and unchanged; this plan does not draw on it. Run it only
after the owner gives a T7 approval for these calls, after PR #127 and then this PR are on the
code being run.

Why: D-098 changes qualification-basis files (`budget.py`, `remote_checks.py`, `remote_test.py`),
so every stored qualification is out of date (current basis on this branch: see
`docs/PROJECT_STATE.md`). At the first start on the new code, a stored GPT-OSS activation reverts
to **no AI model** (case-data answers only; audited `STARTUP_REVERTED`,
`QUALIFICATION_OUT_OF_DATE`); no other model is substituted. Balanced and Fast each need their own
passing run under the new basis. Nothing switches between them automatically (owner decision:
not approved).

## Expected cost (to approve)

| Run | Paid calls | Measured cost | Bound shown before confirming |
| --- | --- | --- | --- |
| Balanced (medium) | the manifest count (`AI_ASSISTANT_LOCAL_API_TEST_QUALIFICATION_COUNT`, 2 in the D-094/D-095 set-up) | Phase B median about US$0.00022 a question | the retry dialog: reservation per call and the worst case |
| Fast (low) | the same count | not established (expected lower) | the same |

Every call is admitted against the lowest of today's allowance, the lifetime headroom and the
key's own limit; nothing beyond them can be charged.

## Procedure (PowerShell, on the owner's machine)

Use the existing key source (environment, `apps/assistant/.env` or HR entry), the existing ledger
(`apps/assistant/data/budget/ledger.sqlite3`), the existing model-state database
(`apps/assistant/data/models/model_admin.sqlite3`) and the configured synthetic manifest. Never
create, reset or replace the ledger or the state database; never print the key.

1. **Code.** Check out the merged main (or the PR head under review) in the usual checkout; no
   `git reset`/`clean`. Record `git rev-parse HEAD`.
2. **Read-only copies.** With the services stopped, copy (do not move) both SQLite files to a
   dated folder outside the repository, for evidence only:
   `Copy-Item apps\assistant\data\budget\ledger.sqlite3 $env:USERPROFILE\clm-evidence\<date>\`
   (same for `data\models\model_admin.sqlite3`). They are never copied back.
3. **Ledger before.** `..\..\.venv\Scripts\python.exe scripts\budget_ledger.py status` (from
   `apps\assistant`): breaker closed, no open call. Note the committed amount.
4. **Start** the backend, frontend and assistant as for the earlier D-095 runs (same environment;
   `AI_ASSISTANT_REMOTE_LOW_REASONING_PROFILE_ENABLED=true` only for step 8).
5. **Free checks only** (AI Models, HR account):
   - the active model reads *No AI model (case-data answers only)* with the start-up notice, and
     the audit history shows `STARTUP_REVERTED` / `QUALIFICATION_OUT_OF_DATE`;
   - **Refresh Limits**: the key shows a limit that never resets, remaining above the
     reservation; *Account credits: not available*;
   - **Test Connection** for Balanced: passed (no inference call).
   Stop here if any of these differs.
6. **Balanced (paid; only with approval).** AI model status and recovery → *Retry
   Qualification* on GPT-OSS 120B — Balanced. Check the dialog: number of paid calls equals the
   manifest count; reservation, worst case and available amount are as expected. Tick the
   confirmation and run it once. Wait for the result on the page (leaving or signing in again
   does not stop or repeat it).
7. **Activate Balanced** (free) only if every gate passed, including G-8 with every call
   verified: *Activate*, with the not-scored acknowledgement. Ask one synthetic Garden question
   as the RM to confirm "Answered by GPT-OSS 120B".
8. **Fast (paid; only with approval).** Stop the assistant, set
   `AI_ASSISTANT_REMOTE_LOW_REASONING_PROFILE_ENABLED=true`, start it. Balanced stays active.
   *Test Connection* then *Retry Qualification* on GPT-OSS 120B — Fast, as in step 6. Do **not**
   activate Fast unless the owner asks for it separately.
9. **After.** `budget_ledger.py status` again: the committed amount rose by at most the runs'
   settled cost; breaker closed; no open call. Export the AI Models audit history.

## Stop conditions (do not retry; report)

- any free check in step 5 fails, or the page shows an operator or policy category;
- a run fails G-3, G-6, G-7 or G-8 (the server then refuses a re-run of that configuration
  until IT changes it: `ESCALATION_REQUIRED`), or opens the ledger breaker;
- the dialog's call count or amounts differ from the approval, or the ledger's committed amount
  rises by more than the dialog's worst case;
- any refusal code you do not expect (`PAID_CONFIRMATION_REQUIRED`,
  `QUALIFICATION_BUDGET_TOO_LOW`, `QUALIFICATION_BUSY`, `PROVIDER_*`, `RECONCILIATION_REQUIRED`).

## Handoff to record (no key, prompt, answer or case data)

Commit, basis (first 12 characters), each run's qualification id, gate results, verified calls,
settled cost from the ledger, the audit events, and which configuration is active afterwards.
