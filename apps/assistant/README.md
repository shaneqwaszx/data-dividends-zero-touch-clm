# AI Assistant (Phase 1, read-only)

A separate service that explains one onboarding case to the RM: what is blocking it, why,
what to do next, and where the facts came from. It **cannot change a case**.

```
Case page chat panel ──/assistant──▶ AI Assistant service (this folder, port 8100)
                                        ├─ GET existing CLM APIs (port 8000), with the RM's own session
                                        └─ chat model via an OpenAI-compatible API (Ollama by default)
```

- **The backend stays the authority.** Blockers, owners, next steps and allowed actions are
  copied from what the CLM backend already computed. The model selects exact reviewed guidance statements grounded in the current actions.
  Arbitrary generated prose is replaced with a deterministic case-data answer. Access is still decided by the backend, because the RM's own session is
  forwarded.
- **Read-only.** Only `GET` requests are made to the CLM backend.
- **No-AI fallback.** The opening summary is built straight from the case data, so it is
  instant. If the model is off, missing or slow, chat answers come from the case data and
  say so.
- **Swappable model.** Explicit questions use an OpenAI-compatible endpoint, such as
  Ollama (default) or LM Studio. Configuring an endpoint does not establish approved
  data handling. Remote/cloud deployment authorization remains a separate policy boundary.
- **Document text is data.** Document values never extend the allowed output catalog.
  Streaming validates complete catalog lines before displaying them. Unknown lines are
  dropped; if no verified line remains, the service uses the case-data answer.
- **Truthful completion.** The model adapter requires `[DONE]` or a supported terminal
  `finish_reason` (`stop` or `length`). EOF without a terminal marker is a failure.
  Already verified partial text is retained with a cut-short notice; malformed provider
  objects are contained by the same owned failure boundary.

## Run it locally (Mac)

1. Install [Ollama](https://ollama.com), open it, then pull the model once:
   `ollama pull ministral-3:8b`
2. Start the CLM backend as usual (port 8000).
3. Start the AI Assistant (its dependencies are already in the backend's `.venv`):

   ```
   cd apps/assistant
   ../../.venv/bin/python -m uvicorn ai_assistant.main:app --host 127.0.0.1 --port 8100
   ```
4. Restart the frontend (`npm run dev`). Vite forwards `/api/assistant` to the AI Assistant on port 8100 (under `/api` so the browser sends the session cookie).
5. Click the round **Ask AI Assistant** button (bottom right) on any page.

Check it is up: `curl http://127.0.0.1:8100/assistant/health`

Settings are in `.env.example` (copy to `.env` to change them).

## Changing how the AI Assistant behaves

The model instructions live in `ai_assistant/instructions/`. The code-owned output policy in
`guardrails.py` remains authoritative: editing prose cannot extend the allowed guidance catalog.

| File | What it controls |
|---|---|
| `persona_and_rules.md` | Who the AI Assistant is and the rules it must follow. Sent to the model as its first message. |
| `case_page_terms.md` | What labels on the case page mean (one `- **term**: meaning` per line). Used with or without the model. |

The model cannot open files: the AI Assistant reads these files at start-up and puts their text in the
model's context. Notes inside `<!-- ... -->` are for editors and are not sent to the model.
Restart the AI Assistant after an edit, and run `pytest` to check the files are still valid.

## API

| Method | Path | What it returns |
|---|---|---|
| GET | `/assistant/health` | Whether a model is configured |
| GET | `/assistant/cases/{case_id}/brief` | Opening summary of one case and suggested questions (no AI) |
| POST | `/assistant/cases/{case_id}/chat` | `{message, history}` → answer about that case |
| POST | `/assistant/cases/{case_id}/chat/stream` | Same, but the answer arrives while it is written (one JSON object per line: `text` updates, then `done`). Used by the chat panel. |

The browser reaches these at `/api/assistant/...` through the Vite proxy. The AI Assistant only
discusses a case the system has already replied on: a case's page under **Cases**, or the
case being onboarded on **New onboarding** (once it has been created). Its button is on every
page for easy access; elsewhere it asks the RM to open or start a case. It keeps a separate
conversation per case and requests nothing until it is opened.

## Speed

A small model on a laptop is slow, so the AI Assistant keeps the model's work small:

| What | Why it helps |
|---|---|
| **Short case view for the model** (`prompts.py`) | Selected facts plus the current allowed guidance catalog. The full facts support deterministic no-AI answers. |
| **Glossary only when asked** | A page label's meaning is added only if the question mentions it (a small keyword retrieval step). |
| **Cache-friendly order** | Rules, then case facts, then history, then the question. The start stays the same, so Ollama reuses what it already read. |
| **History budget** | The opening summary is not sent back (it repeats the facts), and only recent turns that fit about 2,400 characters are sent. The RM still sees the whole chat. |
| **Pre-warming** | Optional background reading of rules and case facts is restricted to literal loopback model URLs. Remote and ambiguous destinations are skipped even when enabled. |
| **Streaming** | The answer appears one complete catalog line at a time. Exact validation happens before display. |
| **Length safety limit** | `AI_ASSISTANT_LLM_MAX_ANSWER_TOKENS` (600) only stops a runaway answer; if reached, the RM is told it was cut short. Answers are asked to be concise but complete. |

`AI_ASSISTANT_LLM_WARM_UP=true` retains local warm-up for literal loopback IPv4
(`127.0.0.0/8`) or IPv6 (`::1`) HTTP(S) URLs. The model adapter checks the actual
call destination, ignores environment proxies and refuses redirects for warm-up.
DNS names (including `localhost`), wildcard/private/remote IPs, credentials in URLs,
query/fragment routing and malformed or ambiguous URLs fail closed. Use a numeric
loopback URL for a controlled local inference server. A loopback forwarding gateway
is not verification of local inference; deployment must ensure the model runs locally.
Set the flag false to disable local warm-up too. There is no remote warm-up override
or cloud approval mechanism. Explicit user questions and their deployment data-handling
authorization remain separate and unchanged. A brief still comes from backend case data.

Recommended Ollama settings on a Mac (quit Ollama, run these, then open Ollama again):

```
launchctl setenv OLLAMA_CONTEXT_LENGTH 8192     # room for rules, facts and history
launchctl setenv OLLAMA_KEEP_ALIVE 1h           # keep the model loaded between questions
launchctl setenv OLLAMA_FLASH_ATTENTION 1       # faster, less memory
launchctl setenv OLLAMA_KV_CACHE_TYPE q8_0      # smaller cache (needs flash attention)
```

Measure it (before vs after, against a saved sample case; no backend or login needed):

```
cd apps/assistant
../../.venv/bin/python scripts/speed_test.py
```

## Tests

```
cd apps/assistant
../../.venv/bin/python -m pytest
../../.venv/bin/python -m ruff check ai_assistant tests
../../.venv/bin/python -m mypy ai_assistant
```

## Not in Phase 1

One-click actions, resuming the pipeline, navigation links and the audit log are Phase 2.
They will call the existing CLM endpoints only after the RM clicks.
