# AI Assistant (Phase 1, read-only)

A separate service that explains one onboarding case to the RM: what is blocking it, why,
what to do next, and where the facts came from. It **cannot change a case**.

```
Case page chat panel ──/assistant──▶ AI Assistant service (this folder, port 8100)
                                        ├─ GET existing CLM APIs (port 8000), with the RM's own session
                                        └─ chat model via an OpenAI-compatible API (Ollama by default)
```

- **The backend stays the authority.** Blockers, owners, next steps and allowed actions are
  copied from what the CLM backend already computed. The model only selects exact allowed
  lines: reviewed statements grounded in the current actions, and approved knowledge
  sentences that pass the checks (see Output policy). Anything else is withheld; if nothing
  is left, a deterministic case-data answer is shown. Access is still decided by the backend,
  because the RM's own session is forwarded.
- **Read-only.** Only `GET` requests are made to the CLM backend.
- **No-AI fallback.** The opening summary is built straight from the case data, so it is
  instant. If the model is off, missing or slow, chat answers come from the case data and
  say so.
- **Swappable model.** Explicit questions use an OpenAI-compatible endpoint, such as
  Ollama (default) or LM Studio. Configuring an endpoint does not establish approved
  data handling. Remote/cloud deployment authorization remains a separate policy boundary.
- **Document text is data.** Document values never extend the allowed lines. Streaming
  checks each complete line before displaying it. Unknown lines are dropped; if no allowed
  line remains, the service uses the case-data answer.
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
`guardrails.py` remains authoritative: editing the rules cannot add an allowed line, so it
cannot allow an action, value or claim.

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
  each citing its source). HR (`POLICY_MUTATE`) can propose new guidance through
  `POST /api/assistant/knowledge/guidance`; there is no in-app UI for it.
- **Approved past resolutions**: worked examples a manager (Director, `POLICY_APPROVE`) writes
  as the fix for an RM's enhancement request ("Not helpful" with a note) and that is then
  approved (D-076, proposed; see single-reviewer mode below). The demo seed
  (`seed/synthetic_resolutions.json`) is made up and labelled illustrative.

```
RM asks ─► case context (blocker codes, fields, stage)
        ─► search: approved, current versions the RM may see ─► top guidance [G1..] + resolutions [P1..]
        ─► prompt (rules → facts → history → KNOWLEDGE → question) ─► guardrails ─► answer + source chips
RM clicks "Yes, helpful" ─► rating stored with the case context (confidence by topic in the stats)
RM clicks "Not helpful" + note ─► redacted enhancement request
        ─► Director writes the fix (past case or guidance change) ─► final text shown, confirmed,
            approved ─► request resolved, searchable for the next RM (rejected: request open again)
        ─► or Director closes it with a reason
```

**Single-reviewer mode** (`AI_ASSISTANT_KNOWLEDGE_SINGLE_REVIEWER`, default `true` for this POC;
D-076, proposed, needs the owner's acceptance before merge). The synthetic users have one
Director, so with two-person review nothing a Director writes could be published. In this
mode a reviewer may approve or reject an entry they wrote or edited; approving needs
`"confirm_single_reviewer": true` (the Review window asks after showing the final text) and is
recorded as single-reviewer in the history and listed in the Review window. Set it to `false`
to keep the two-person rule. Retiring an entry always takes two reviewers.

| Part (`ai_assistant/knowledge/`) | What it does |
|---|---|
| `models.py` | An entry: kind, version, status, blocker codes, fields, stages, who may see it, follow-up questions |
| `store.py` | SQLite: every version, every review and edit, feedback, keyword index (FTS5), index to-do list |
| `vector_index.py` + `embeddings.py` | ChromaDB vectors of approved current versions only; local embeddings through Ollama (`nomic-embed-text`) |
| `service.py` | Propose, decide, retire; keeps SQLite and ChromaDB in step; retries; rebuild |
| `retrieval.py` | Hybrid search with permission filters (below) |
| `redaction.py` + `drafting.py` | Removes client values (case facts plus UEN, NRIC, email, phone, postal, unit patterns) and drafts a resolution from an enhancement request |
| `ingest.py` | Loads the guidance files (an app-approved edit is not overwritten by its file) |
| `evaluation.py` | Recall and "correctly found nothing" on a labelled question set |
| `../knowledge_answers.py` | Tags hits, keeps only approved entries the user may see, checks every knowledge text the RM can see (lines, titles, follow-up questions), lists the allowed lines in the KNOWLEDGE prompt part, works out cited sources |
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
| POST | `/assistant/cases/{case_id}/feedback` | RM on the case | "Yes, helpful" (records the rating) or "Not helpful" with a required note (an enhancement request; an empty note is a 422) |
| GET | `/assistant/knowledge/me` | anyone signed in | Whether the user can review or propose guidance, and whether single-reviewer mode is on |
| GET | `/assistant/knowledge/reviews` | Director | Drafts waiting for review and open enhancement requests (`gaps`) |
| GET | `/assistant/knowledge/entries?kind=` | Director, HR | Approved entries |
| GET | `/assistant/knowledge/entries/{id}` | Director (every team), HR (their team); the author | All versions and reviews of one entry; the author sees only the versions they wrote (not one a reviewer edited in place in an older store), without review notes |
| POST | `/assistant/knowledge/entries/{id}/versions/{v}/edit` | Director | Edit a pending draft (recorded); `"replaces": null` clears what it replaces, leaving it out keeps it |
| POST | `/assistant/knowledge/entries/{id}/versions/{v}/decision` | Director, not the author (or the author after confirming, in single-reviewer mode) | Approve or reject; `confirm_single_reviewer` confirms publishing your own entry |
| POST | `/assistant/knowledge/entries/{id}/retire` | Two Directors | Stop using an entry: the first asks, a different one confirms |
| POST | `/assistant/knowledge/feedback/{id}/draft` | Director | Write the fix for an open enhancement request: `kind` `resolution` (title, body, follow-ups) or `guidance` (title, body, `source_ref`, optional `entry_id` of guidance to change); redacted against the request's case and pending review; approving it resolves the request |
| POST | `/assistant/knowledge/feedback/{id}/close` | Director | Close an open enhancement request; `reason` is required |
| POST | `/assistant/knowledge/guidance` | HR | Propose new or changed guidance |
| POST | `/assistant/knowledge/reindex` | Director | Rebuild the vector index: re-embed every current approved entry (e.g. after changing `AI_ASSISTANT_EMBED_MODEL`) |
| GET | `/assistant/knowledge/stats` | Director | Entry counts, how helpful answers were, and confidence by topic (helpful / not helpful per blocker code) |

### In the app

The panel is built on `@assistant-ui/react`. Each answer shows the guidance and past cases it
cited as chips (G1, P1 …) and has **Yes, helpful** (one click, no note) and **Not helpful**
(asks "What was missing?"; Send stays disabled until a note is typed) buttons. Users who can review
see a **Review** button that opens the Knowledge review window.

### Demo script

1. Sign in as an RM, open a case blocked by a document/ACRA address conflict, open the AI Assistant.
2. Ask "Can I use the document address?" The answer cites guidance [G1] and an illustrative past
   case [P1], shown as chips.
3. Click **Not helpful** and say what was missing, naming the client.
4. Sign in as the Director (olivia-koh), open **Review**: under **Enhancement requests** the
   note has the client's name replaced with `[COMPANY]`. Under **Write the fix**, write what
   resolves it as a past case and **Save the fix for review**.
5. Under **Waiting for review**, click **Approve**, check the final text and **Confirm and
   publish** (single-reviewer mode; it is listed under **Published by a single reviewer**).
6. Back as an RM on a similar case, ask again: the new resolution is now cited.

## Output policy

The model's answer is never shown as written. Code (`ai_assistant/guardrails.py`) shows only
whole lines that exactly equal an allowed line, also while streaming; every other line is
left out, the answer's notice says how many, and the reply's `checks.removed` is
`["not_an_allowed_line"]`. The allowed lines are:

1. **The catalog** (`allowed_guidance`): fixed statements filled only from the backend's case
   facts (offered actions, readiness items with their section, rule explanations, the
   standing disclaimers).
2. **Knowledge lines** (ADR-012 section C, accepted by the owner on 2026-10-21, D-074): each
   sentence of a retrieved, approved entry the user may see, exactly as approved and
   followed by its tag (`... [G1]`), but only if it passes these checks against this case's
   facts. At most 20 lines per entry and 48 lines (8 KiB) per answer are offered.

The same checks apply to the other knowledge text in chat replies: an entry title on a
source chip or in the no-model answer is replaced by a neutral label ("Guidance G1", "Past
case P1") if it fails, and a follow-up question that fails is not suggested. Source objects
carry the tag, kind, version, that title, the approval time and the illustrative, fallback
and cited flags, not the entry id or the free-text source reference.

For knowledge, two-person approval is the real control. The checks are a best-effort filter:
they catch the listed phrasings and shapes only, not deliberate evasion (ADR-012 lists what
they miss).

| Check | The text is not offered when |
|---|---|
| Factual claims | a UEN (including the T/S/R format), NRIC/FIN, postal code, unit number, decimal or number of three or more digits is not in the case facts; "N of M steps" does not match the case. Short numbers and percentages are not checked |
| Labels and places | a quoted button or label, a listed contact phrase ("support team", "your manager" …), an e-mail address, a web address starting with `http://`, `https://` or `www.`, or a "(section: ...)" is not in the case facts; the text carries a citation tag of its own. People's names, bare domains and other schemes are not recognised |
| Action permissions | it uses one of the listed phrasings for an action this case does not offer the RM (keep/use a value, accept/reject a document suggestion, record a correction, request information, approve/authorize the case, submit or resend to GoldTier). Saying an action is not available is fine |
| Authority | it uses one of the listed phrasings for something only people or other systems can decide: legal UBO verification, KYC/regulatory approval, official verification, or one source always overriding the other |
| Disclosures | it calls a mock/sandbox system live or production in one of the listed ways, or presents a document value that differs from ACRA as confirmed |
| Characters | it contains anything other than printable ASCII and typographic quotes, dashes, ellipsis or bullet (a tab, a non-breaking or invisible space, a look-alike letter from another script) |

Free model prose, paraphrases and earlier chat turns never become allowed lines. When an
answer uses registry data from a registry that is not live, a notice says so (for example
"Registry data in this case comes from ACRA (MOCK) …"). If no allowed line is left, the
answer comes from the case data instead, with the notice "The model response could not be
verified".

## Speed

A small model on a laptop is slow, so the AI Assistant keeps the model's work small:

| What | Why it helps |
|---|---|
| **Short case view for the model** (`prompts.py`) | About 35% fewer characters than the full fact sheet. The full facts are still used for the guardrails and the no-AI answers. |
| **Glossary only when asked** | A page label's meaning is added only if the question mentions it (a small keyword retrieval step). |
| **Cache-friendly order** | Rules, then case facts, then history, then the question. The start stays the same, so Ollama reuses what it already read. |
| **History budget** | The opening summary is not sent back (it repeats the facts), and only recent turns that fit about 2,400 characters are sent. The RM still sees the whole chat. |
| **Pre-warming** | Optional background reading of rules and case facts is restricted to literal loopback model URLs. Remote and ambiguous destinations are skipped even when enabled. |
| **Streaming** | The answer appears line by line. Each complete line is looked up in the allowed lines before it is shown. |
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

Streaming resource limits are enforced independently of the model's requested token
budget (600 by default, at most 4,000 in settings). The adapter accepts at most 64 KiB
per SSE frame/line and 1 MiB of raw response bytes, including comments and empty-delta
frames. The server guard accepts at most 64 KiB of UTF-8 model text; if the stream fails,
only allowed lines completed before the failure are kept. These fixed safety ceilings leave
generous room for concise answers;
provider compliance with `max_tokens` is never assumed.

The configured model timeout bounds the complete network request, from connection and
headers through the final event. Each pending async read is cancellable at the remaining
deadline; HTTPX also keeps the configured connect/read/write/pool timeouts. UTF-8,
LF/CRLF/CR boundaries and multiline SSE data are handled incrementally. A terminal
`[DONE]`, `stop` or `length` must arrive in a complete SSE frame. Malformed, oversized,
uncompleted and timed-out streams close their HTTP resources. Already guarded text
keeps the cut-short notice; otherwise the deterministic case-data answer is returned.
The adapter requests identity encoding and rejects compressed SSE, so decompression
cannot expand input outside the byte limits. Cancellation closes the model stream.

The browser adds 128 KiB per NDJSON line and 2 MiB per response, scans only new bytes,
validates incremental UTF-8, and cancels/releases its reader on completion, failure or
abort. The same limits cover the buffered-response compatibility path. These browser
limits supplement the independent server limits and do not authorize model output.

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

### Browser HTTP error and finite JSON containment

All Assistant non-2xx bodies are limited to 16 KiB before strict UTF-8 decoding and
JSON parsing, regardless of Content-Length. Brief and explicit nonstream chat JSON
are independently limited to 128 KiB. Each finite JSON body has an absolute five-second
deadline after response headers, including stalled and continuous trickle bodies.
Overflow, malformed data, missing bodies and deadlines fail safely; cancellation is
initiated and readers, timers and abort listeners are released. Cleanup never waits
for an uncooperative source's cancellation promise.

Only the seven fixed safe messages currently emitted by the Assistant's origin/backend
error projection may be displayed from an error body (at most 256 characters). Other
bodies use fixed local HTTP-status messages; raw diagnostics are never displayed.
HTTP status is preserved, including 401, 403, 404, 502 and 503. The existing authenticated
transport still owns session-generation and 401 invalidation. These are local resource
controls, without a sponsor, provider or Live interoperability claim.
