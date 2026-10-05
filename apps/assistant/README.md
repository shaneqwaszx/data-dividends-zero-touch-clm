# Onboarding Copilot (Phase 1, read-only)

A separate service that explains one onboarding case to the RM: what is blocking it, why,
what to do next, and where the facts came from. It **cannot change a case**.

```
Case page chat panel ──/assistant──▶ Copilot service (this folder, port 8100)
                                        ├─ GET existing CLM APIs (port 8000), with the RM's own session
                                        └─ chat model via an OpenAI-compatible API (Ollama by default)
```

- **The backend stays the authority.** Blockers, owners, next steps and allowed actions are
  copied from what the CLM backend already computed. The model only puts them into plain
  English. Access is still decided by the backend, because the RM's own session is
  forwarded.
- **Read-only.** Only `GET` requests are made to the CLM backend.
- **No-AI fallback.** The opening summary is built straight from the case data, so it is
  instant. If the model is off, missing or slow, chat answers come from the case data and
  say so.
- **Swappable model.** Any OpenAI-compatible endpoint works: Ollama (default), LM Studio,
  or a cloud provider. Only the `COPILOT_LLM_*` settings change.
- **Document text is data.** The model is told never to follow instructions found in it.

## Run it locally (Mac)

1. Install [Ollama](https://ollama.com), open it, then pull the model once:
   `ollama pull ministral-3:8b`
2. Start the CLM backend as usual (port 8000).
3. Start the copilot (its dependencies are already in the backend's `.venv`):

   ```
   cd apps/assistant
   ../../.venv/bin/python -m uvicorn copilot.main:app --host 127.0.0.1 --port 8100
   ```
4. Restart the frontend (`npm run dev`). Vite forwards `/api/assistant` to the copilot on port 8100 (under `/api` so the browser sends the session cookie).
5. Click the round **Ask Copilot** button (bottom right) on any page.

Check it is up: `curl http://127.0.0.1:8100/assistant/health`

Settings are in `.env.example` (copy to `.env` to change them).

## API

| Method | Path | What it returns |
|---|---|---|
| GET | `/assistant/health` | Whether a model is configured |
| GET | `/assistant/cases/{case_id}/brief` | Opening summary of one case and suggested questions (no AI) |
| POST | `/assistant/cases/{case_id}/chat` | `{message, history}` → answer about that case |

The browser reaches these at `/api/assistant/...` through the Vite proxy. The copilot only
discusses a case the system has already replied on: a case's page under **Cases**, or the
case being onboarded on **New onboarding** (once it has been created). Its button is on every
page for easy access; elsewhere it asks the RM to open or start a case. It keeps a separate
conversation per case and requests nothing until it is opened.

## Tests

```
cd apps/assistant
../../.venv/bin/python -m pytest
../../.venv/bin/python -m ruff check copilot tests
../../.venv/bin/python -m mypy copilot
```

## Not in Phase 1

One-click actions, resuming the pipeline, navigation links and the audit log are Phase 2.
They will call the existing CLM endpoints only after the RM clicks.
