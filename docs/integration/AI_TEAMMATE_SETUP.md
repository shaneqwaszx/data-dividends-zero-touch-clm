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

Never share one Anthropic workspace between machines. Each machine's ledger counts only its own
calls, so a shared workspace hides the other machines' spend from every ledger. An Admin key is
always refused.

## Steps

1. Start the stack with your own data root. Copy
   `apps/assistant/scripts/storage/start_assistant.example.ps1` and set the data root under
   `%LOCALAPPDATA%\DataDividendsCLM\assistant`. You do **not** run `budget_ledger.py`: the
   spending ledger is created from the AI Models page.
2. Sign in as HR and open **AI Models**. It opens on **Set up AI**.
3. **Select a model.**
4. **Enter the API key, then choose Save & test.** The key stays in the server's memory for your
   sign-in session only. It is never shown again or kept in the browser.
   - **GPT-OSS:** the free key check reads the key's own limit and usage, then creates the
     ledger. Its opening usage is what OpenRouter reports for the key, so nothing it spent before
     is forgotten.
   - **Claude:** the page reads the workspace the key belongs to (free). Then fill in the
     one-time setup record:
     - the workspace's monthly limit;
     - that the workspace is used only for the FYP;
     - that the key will be revoked when the FYP ends;
     - whether the workspace is **new with no earlier usage** or, if not, its cumulative cost from
       the Anthropic Console.

     A ledger never starts at zero by default.
5. **Test & qualify.** One confirmation names the paid test calls and the most they can cost out
   of your US$5.00 session.
6. **Activate.** One confirmation repeats that this is an external, paid API. Case users then use
   the AI Assistant on an open, verified synthetic case.

You never need a CLI command, the P1 record or a manual reconciliation for this.

## The US$5.00 session

- **Starts:** the first paid action (a confirmed qualification or a chat answer) opens it.
  Qualification and chat share it.
- **Never starts or resets it:** a restart, a reconnect, a new key or a re-activation.
- **Lowering it:** choose *Use a smaller amount* to set anything above US$0.00 and up to US$5.00.
  You never have to confirm the default.
- **When it runs out:** paid calls stop and RMs get the labelled case-data guidance. Nothing
  renews the session by itself. **Start a new session** is a deliberate HR action that shows what
  the old session used.
- **Other limits still apply:** the daily limit (US$5.00 by default, per Singapore day), the
  lifetime cap and the chat-call limit per session (both providers).

**What the app does and does not guarantee.** It never admits a call whose worst case would go
past what is left in the session. Real charges can still go slightly over in three ways:

- one call costing more than its worst-case estimate (the breaker then stops further calls);
- someone using the same key or workspace outside this app;
- a wrong figure from the provider.

The provider's own limit is the hard ceiling:

- **OpenRouter:** the key's never-resetting limit.
- **Anthropic:** the workspace's monthly limit, which resets each month, so it bounds a month,
  not a session.

## When something stops

The status strip on **Set up AI** names the problem in one sentence and offers the next action.

| You see | What to do |
| --- | --- |
| Allowance used up | **Start a new session** (HR). |
| Paid calls paused after an interrupted call | **Resume, keeping the charge** (HR). This works only when the ledger proves every recent call was charged its full worst case, with no anomaly. |
| Paid calls stopped for the owner (a routing, model or cost anomaly, a provider refusal, a quarantined OpenRouter call) | Ask the owner. They review it with the recovery centre and the operator script; HR cannot clear it. |
| Ledger in the earlier format | The owner migrates it once (below). |

## Owner only: migrating an existing ledger

Existing stores are never migrated by the service. With separate approval, stop the assistant
service, then run (from `apps/assistant`) with the store settings your launcher sets:

```bash
python scripts/budget_ledger.py --anthropic migrate-v2 --backup <new backup file> --confirm-service-stopped
```

- **It refuses unless the ledger is quiet:** no call, close or operator event in the last
  300 seconds, no open call, no reconciliation lock or intent marker, and the breaker closed or
  resumable.
- **On success:** it writes a verified backup, migrates in one exclusive transaction, and proves
  every earlier row and event is unchanged.
- **The fence:** after migration, an older copy of the code or scripts can no longer write to the
  ledger.
- **The GPT-OSS ledger:** drop `--anthropic` to migrate it. The accounting mode follows the
  provider: Claude provider-capped, GPT-OSS provider-anchored.
