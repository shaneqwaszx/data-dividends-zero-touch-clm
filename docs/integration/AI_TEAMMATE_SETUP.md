# AI Assistant: teammate setup with paid-model sessions (D-118)

This guide is for a teammate running their own local copy of the CLM proof of concept. External
models (Claude Sonnet 5.5 and GPT-OSS 120B) answer **verified synthetic cases only**. This is
local development, not Live. Never use real customer data.

## What you need

| Model | You need | Session allowance |
| --- | --- | --- |
| Local Ollama | Ollama running on `127.0.0.1:11434` | None (free) |
| GPT-OSS 120B (OpenRouter) | Your own OpenRouter key with a **credit limit that never resets** (US$5.00 recommended) and auto top-up off | US$5.00 by default |
| Claude Sonnet 5.5 (Anthropic) | An **inference** key in **your own dedicated, non-default Anthropic workspace** with a monthly spend limit (US$5.00 recommended) | US$5.00 by default |

**The provider's limit is your real spending ceiling.** The app's US$5.00 session allowance
stops it from starting calls, but it does not read the provider's bill.

**Never share one workspace or key between machines.** Each machine counts only its own calls.

**An Admin key is always refused.**

## Steps

1. Start the stack with the launcher template,
   `apps/assistant/scripts/storage/start_assistant.example.ps1`. It sets your data root and the
   OpenRouter owner statements. You run no ledger command: AI Models creates the spending store
   for you.
2. Sign in as HR and open **AI Models**. It opens on **Set up AI**.
3. **Select a model.**
4. **Enter the API key, then choose Save & test.**
   - The key is held in the server's memory for your sign-in session only. It is never shown
     again or kept in the browser.
   - **Claude:** the first time, the page reads the workspace the key belongs to (free). Confirm
     the one-time setup record: the workspace is used only for the FYP, its monthly limit, and
     that the key will be revoked when the FYP ends. Then choose **Enable Claude**.
5. **Run qualification.** The free connection check runs first. Then one confirmation names the
   paid test calls and the most they can cost from your US$5.00 session. Confirming it is your
   consent to those calls.
6. **Activate.** One confirmation repeats that this is an external, paid API. Case users then use
   the AI Assistant on an open, verified synthetic case.

None of this needs a CLI command, a P1 record, a ledger migration or a reconciliation.

**After a restart:** your session, its spend and the activation are kept. Enter the key again
(keys live in memory only), and carry on.

## The US$5.00 session

- **Starts:** the first paid action (a confirmed qualification or a chat answer) opens it.
  Qualification and chat share it.
- **Never starts or resets it:** a restart, a reconnect, a new key or a re-activation.
- **Changing it:** choose *Use a smaller amount* to set anything above US$0.00 and up to US$5.00,
  including raising it back to US$5.00. You never have to change or confirm it to activate.
- **When it runs out:** paid calls stop and RMs get the labelled case-data guidance. Nothing
  renews it by itself. **Start a new session** is a deliberate HR action that shows what the old
  session used.
- **Other limits still apply:** the daily limit (US$5.00 by default), the lifetime cap and the
  chat-call limit per session.

**What the app does and does not guarantee.** It never admits a call whose worst case would go
past what is left in the session. Real charges can still go slightly over in three ways:

- one call costing more than its estimate (paid calls then pause);
- someone using the same key or workspace outside this app;
- a wrong figure from the provider.

The provider's own limit is the hard ceiling:

- **OpenRouter:** the key's never-resetting limit.
- **Anthropic:** the workspace's monthly limit, which resets each month.

## When something stops

Nothing is ever retried automatically. The status strip on **Set up AI** names the problem and
offers the next action.

| You see | What to do |
| --- | --- |
| Allowance used up | **Start a new session** (HR). |
| Paid calls are paused: an interrupted call, a provider refusal (key, payment or limit) or a cost above its estimate | Fix the cause if there is one, then **Resume, keeping the charge** (HR). |
| Paid calls are stopped for the owner: a model, provider or workspace mismatch, or a ledger problem | Ask the owner. They review it and clear it with `budget_ledger.py resume-after-review --code CODE --confirm-reviewed`. |
| The launcher names a store from the earlier design | Ask the owner (below). |

## Owner only: retiring the earlier accounting stores

The simplified runtime never uses the earlier design's ledgers (`budget/ledger.sqlite3`,
`budget/anthropic_fyp_ledger.sqlite3`). To keep them and start clean, under separate approval:

1. Stop the assistant service.
2. From `apps/assistant`, run:

   ```bash
   python -I scripts/storage/archive_accounting_stores.py <data-root> <new archive folder>
   ```

   - It copies each ledger and any reconciliation intent marker with the reviewed
     `backup_stores.py`, writes a manifest and checks every row.
   - It never moves, changes or deletes a source, and it refuses an existing archive folder.
3. In the launcher, set `AI_ASSISTANT_ANTHROPIC_LEDGER_PATH` and
   `AI_ASSISTANT_BUDGET_LEDGER_PATH` to `data/budget/sessions/...` (the template shows this),
   then restart.

The old files stay where they were, as history. Audit events and qualification history in the
model state database are kept.
