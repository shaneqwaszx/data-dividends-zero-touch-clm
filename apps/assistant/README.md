# AI Assistant (Phase 1, read-only)

A separate service that explains one onboarding case to the RM: what is blocking it, why,
what to do next, and where the facts came from. It **cannot change a case**.

```
Case page chat panel ──/assistant──▶ AI Assistant service (this folder, port 8100)
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
  or a cloud provider. Only the `AI_ASSISTANT_LLM_*` settings change.
- **Document text is data.** The model is told never to follow instructions found in it.

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

The bot's behaviour is written in plain English in `ai_assistant/instructions/`, not in code:

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

## Knowledge loop (reviewed guidance and past resolutions)

The AI Assistant learns from reviewed knowledge by **retrieving** it at question time, never by
retraining the model. There are two kinds of entry:

- **Official guidance**: the rulebook, written from recorded decisions (`knowledge/guidance/*.md`,
  each citing its source). HR (`POLICY_MUTATE`) can propose new guidance in the app.
- **Approved past resolutions**: worked examples drafted from an RM's "Solved it" feedback and
  approved by a manager (Director, `POLICY_APPROVE`). The demo seed
  (`seed/synthetic_resolutions.json`) is made up and labelled illustrative.

```
RM asks ─► case context (blocker codes, fields, stage)
        ─► search: approved, current versions the RM may see ─► top guidance [G1..] + resolutions [P1..]
        ─► prompt (rules → facts → history → KNOWLEDGE → question) ─► guardrails ─► answer + source chips
RM clicks "Solved it" ─► redacted draft ─► Director edits / approves ─► searchable for the next RM
RM clicks "Not helpful" ─► gap for the Director to handle
```

| Part (`ai_assistant/knowledge/`) | What it does |
|---|---|
| `models.py` | An entry: kind, version, status, blocker codes, fields, stages, who may see it, follow-up questions |
| `store.py` | SQLite: every version, every review and edit, feedback, keyword index (FTS5), index to-do list |
| `vector_index.py` + `embeddings.py` | ChromaDB vectors of approved current versions only; local embeddings through Ollama (`nomic-embed-text`) |
| `service.py` | Propose, decide, retire; keeps SQLite and ChromaDB in step; retries; rebuild |
| `retrieval.py` | Hybrid search with permission filters (below) |
| `redaction.py` + `drafting.py` | Removes client values (case facts plus UEN, NRIC, email, phone, postal, unit patterns) and drafts a resolution from feedback |
| `ingest.py` | Loads the guidance files (an app-approved edit is not overwritten by its file) |
| `evaluation.py` | Recall and "correctly found nothing" on a labelled question set |
| `../knowledge_answers.py` | Tags hits, builds the KNOWLEDGE prompt part, works out cited sources and follow-up suggestions |
| `../knowledge_api.py` | Feedback and review endpoints |

**Rules.** Versions are never overwritten. The author of an entry can never approve it. Approving a
version retires the previous one (and any entry it replaces), so only one version is searched.
Rejected and retired versions are never searched. Official guidance outranks past cases, and the
case facts outrank both.

**How search ranks entries.** Only approved, current entries the RM may see (by role and team, from
`/api/auth/me`) are considered. A past resolution must share a blocker code or field with the case.
Each entry then gets a score:

| Signal | Weight | Meaning |
|---|---|---|
| Meaning (semantic) | 0.45 | Vector similarity between question and entry |
| Keywords | 0.2 | FTS5 match, squashed so one long entry does not dominate |
| Case context | 0.3 | Same blocker code (0.6), field (0.3), stage (0.1) |
| Recency | ×0.05 | Tie-breaker: newer approvals rank slightly higher (half-life 180 days) |

Guidance needs 0.3 and resolutions 0.4 to be used; at most 3 of each. If Ollama embeddings are down,
search falls back to keywords and context only. All weights are `AI_ASSISTANT_RETRIEVAL_*` settings.

**Follow-up questions.** An approved resolution can carry follow-up questions; when it is used,
they are offered as suggestions after the top three.

Set it up (needs `ollama pull nomic-embed-text`):

```
cd apps/assistant
../../.venv/bin/python -m pip install -e ".[dev]"
../../.venv/bin/python scripts/ingest_knowledge.py --with-synthetic-resolutions
../../.venv/bin/python scripts/evaluate_retrieval.py --show-misses
```

Run the ingest again any time: unchanged guidance is skipped, edited files become new versions,
removed files are retired. If Ollama is not running, entries are saved and indexed later. Data
lives in `apps/assistant/data/knowledge/` (not in Git).

### Knowledge API

| Method | Path | Who | What it does |
|---|---|---|---|
| POST | `/assistant/cases/{case_id}/feedback` | RM on the case | "Solved it" (drafts a resolution) or "Not helpful" (records a gap) |
| GET | `/assistant/knowledge/me` | anyone signed in | Whether the user can review or propose guidance |
| GET | `/assistant/knowledge/reviews` | Director | Drafts waiting for review and open gaps |
| GET | `/assistant/knowledge/entries?kind=` | Director, HR | Approved entries |
| GET | `/assistant/knowledge/entries/{id}` | author, Director, HR | All versions and reviews of one entry |
| POST | `/assistant/knowledge/entries/{id}/versions/{v}/edit` | Director | Edit a pending draft (recorded) |
| POST | `/assistant/knowledge/entries/{id}/versions/{v}/decision` | Director, not the author | Approve or reject |
| POST | `/assistant/knowledge/entries/{id}/retire` | Director | Stop using an entry |
| POST | `/assistant/knowledge/feedback/{id}/close` | Director | Mark a gap as handled |
| POST | `/assistant/knowledge/guidance` | HR | Propose new or changed guidance |
| POST | `/assistant/knowledge/reindex` | Director | Rebuild the vector index |
| GET | `/assistant/knowledge/stats` | Director | Entry counts and how helpful answers were |

### In the app

The panel is built on `@assistant-ui/react`. Each answer shows the guidance and past cases it
cited as chips (G1, P1 …) and has **Solved it** / **Not helpful** buttons. Users who can review
see a **Review** button that opens the Knowledge review window.

### Demo script

1. Sign in as an RM, open a case blocked by a document/ACRA address conflict, open the AI Assistant.
2. Ask "Can I use the document address?" The answer cites guidance [G1] and an illustrative past
   case [P1], shown as chips.
3. Click **Solved it** and add a note ("ACRA was current; kept registry value").
4. Sign in as a Director (not the same user), open **Review**: the draft has the client's name
   replaced with `[COMPANY]`. Edit if needed, then **Approve**.
5. Back as an RM on a similar case, ask again: the new resolution is now cited.

## Grounding and policy validation

Every model answer is checked by code (`ai_assistant/guardrails.py`) before the RM sees it,
one sentence at a time (also while streaming). A sentence that fails is left out, and the
answer's notice says how many were left out; the reply's `checks` lists the reasons.

| Check | Left out when | Reason code |
|---|---|---|
| Factual claims | a UEN, postal code, unit number, score or long number is not in the case facts | `unsupported_value` |
| | "N of M steps" does not match the case | `wrong_step_count` |
| | a quoted button or label, or a contact, is not in the facts | `invented_label`, `invented_contact` |
| Action permissions | it tells the RM to take an action this case does not offer them (keep/use a value, accept/reject a document suggestion, record a correction, request information, approve, submit to GoldTier). Saying an action is not available is fine | `action_not_allowed` |
| Disclosures | it calls a mock/sandbox system live or production | `live_claim` |
| | it presents a document value that differs from ACRA as confirmed | `document_value_as_fact` |

When an answer uses registry data from a registry that is not live, a notice says so
(for example "Registry data in this case comes from ACRA (MOCK) …"). If nothing is left
after the checks, the answer comes from the case data instead.

## Speed

A small model on a laptop is slow, so the AI Assistant keeps the model's work small:

| What | Why it helps |
|---|---|
| **Short case view for the model** (`prompts.py`) | About 35% fewer characters than the full fact sheet. The full facts are still used for the guardrails and the no-AI answers. |
| **Glossary only when asked** | A page label's meaning is added only if the question mentions it (a small keyword retrieval step). |
| **Cache-friendly order** | Rules, then case facts, then history, then the question. The start stays the same, so Ollama reuses what it already read. |
| **History budget** | The opening summary is not sent back (it repeats the facts), and only recent turns that fit about 2,400 characters are sent. The RM still sees the whole chat. |
| **Pre-warming** | Opening the panel has the model read the rules and case facts in the background, so the first question only needs the question read. |
| **Streaming** | The answer appears sentence by sentence. Each sentence is checked by the guardrails before it is shown. |
| **Length safety limit** | `AI_ASSISTANT_LLM_MAX_ANSWER_TOKENS` (600) only stops a runaway answer; if reached, the RM is told it was cut short. Answers are asked to be concise but complete. |

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
