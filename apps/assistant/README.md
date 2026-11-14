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
- **Approved past resolutions**: worked examples a Support reviewer (`KNOWLEDGE_REVIEW`, D-103) writes
  as the fix for an RM's enhancement request ("Not helpful" with a note) and that is then
  approved (D-083, proposed; see single-reviewer mode below). The demo seed
  (`seed/synthetic_resolutions.json`) is made up and labelled illustrative.

```
RM asks ─► case context (blocker codes, fields, stage)
        ─► search: approved, current versions the RM may see ─► top guidance [G1..] + resolutions [P1..]
        ─► prompt (rules → facts → history → KNOWLEDGE → question) ─► guardrails ─► answer + source chips
RM clicks "Yes, helpful" ─► rating stored with the case context (confidence by topic in the stats)
RM clicks "Not helpful" + note ─► redacted enhancement request
        ─► Support writes the fix (past case or guidance change) ─► final text shown, confirmed,
            approved ─► request resolved, searchable for the next RM (rejected: request open again)
        ─► or Support closes it with a reason
```

**Single-reviewer mode** (`AI_ASSISTANT_KNOWLEDGE_SINGLE_REVIEWER`, default `true` for this POC;
D-083, proposed, needs the owner's acceptance before merge). The synthetic users have one
Support reviewer, so with two-person review nothing they write could be published. In this
mode a reviewer may approve or reject an entry they wrote or edited; approving needs
`"confirm_single_reviewer": true` (the Review window asks after showing the final text) and is
recorded as single-reviewer in the review history (as is a rejection of your own entry); the
Review window lists the entries currently published that way. Set it to `false`
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
| POST | `/assistant/conversations/{id}/end` | The user who asked | End conversation (D-105): `resolved`, `satisfaction` (Yes: `very_satisfied`, `satisfied`, `neutral`; No: `neutral`, `unsatisfied`, `very_unsatisfied`) and `comment` (required when not resolved), redacted; once per conversation. Neutral or worse becomes an enhancement request with a priority (low, medium, high) |
| GET | `/assistant/conversations?page=` | anyone signed in | Their own conversations, newest first, 10 a page (history) |
| GET | `/assistant/conversations/{id}` | The user who asked | One of their conversations: questions and answers as shown, redacted (views logged) |
| GET | `/assistant/knowledge/conversations?page=&resolved=&satisfaction=&status=` | Support | Rated conversations, 10 a page, high, medium, low, then no priority |
| GET | `/assistant/knowledge/conversations/{id}` | Support | Rating, comment, the whole chat (views logged), its request and the saved draft |
| PUT / DELETE | `/assistant/knowledge/conversations/{id}/draft` | Support | Save (redacted) or discard the draft fix of an open request |
| POST | `/assistant/knowledge/conversations/{id}/try` | Support | Preview: the user's question answered with an unsaved rule change offered as if approved (local model only, or hosted Claude on the registered hosted deployment under D-130; nothing saved, published or recorded) |
| POST | `/assistant/support/chat` | Support | A question about the approved rules and the active policy, no case (local model only, or hosted Claude under D-130) |
| POST | `/assistant/cases/{case_id}/feedback` | RM on the case | (Kept for compatibility; the panel no longer sends it, D-105.) "Yes, helpful" (records the rating) or "Not helpful" with a required note (an enhancement request; an empty note is a 422). `answer_id` names the answer rated when it has a record; when sent it must be the caller's own unrated, unexpired answer on this case, otherwise 404 "No such answer." "Not helpful" without one is still accepted: the reviewer then sees only the note |
| GET | `/assistant/answers/{answer_id}` | the RM who asked | Their own answer record (view logged); HR gets 403, anyone else 404 |
| GET | `/assistant/knowledge/me` | anyone signed in | Whether the user can review or propose guidance, and whether single-reviewer mode is on |
| GET | `/assistant/knowledge/reviews` | Support | Drafts waiting for review and open enhancement requests (`gaps`, each with its `answer_id` and question; listing them is not a logged record view, opening the record is) |
| GET | `/assistant/knowledge/entries?kind=` | Support, HR | Approved entries |
| GET | `/assistant/knowledge/entries/{id}` | Support (every team), HR (their team); the author | All versions and reviews of one entry; the author sees only the versions they wrote (not one a reviewer edited in place in an older store), without review notes |
| POST | `/assistant/knowledge/entries/{id}/versions/{v}/edit` | Support | Edit a pending draft (recorded); `"replaces": null` clears what it replaces, leaving it out keeps it |
| POST | `/assistant/knowledge/entries/{id}/versions/{v}/decision` | Support, not the author (or the author after confirming, in single-reviewer mode) | Approve or reject; `confirm_single_reviewer` confirms publishing your own entry |
| POST | `/assistant/knowledge/entries/{id}/retire` | Two Support reviewers | Stop using an entry: the first asks, a different one confirms |
| POST | `/assistant/knowledge/feedback/{id}/draft` | Support | Write the fix for an open enhancement request: `kind` `resolution` (title, body, follow-ups) or `guidance` (title, body, `source_ref`, optional `entry_id` of guidance to change); redacted against the request's case and pending review; approving it resolves the request. Text that still contains a redaction placeholder (`[ADDRESS]`, `[COMPANY]` or any `[UPPERCASE]` token) is a 422 `PLACEHOLDER_NOT_REWRITTEN` ("Rewrite [ADDRESS], [COMPANY] in general terms before saving."); `started_from_answer` marks a fix started from the record |
| POST | `/assistant/knowledge/feedback/{id}/close` | Support | Close an open enhancement request; `reason` is required |
| GET | `/assistant/knowledge/feedback/{id}/answer` | Support | "What happened": the answer record linked to the request (view logged) |
| GET | `/assistant/knowledge/feedback/{id}/fix-start` | Support | Where the fix can start: a title from the blocker type and the AI's left-out lines (and any shown model line that is not an allowed line), one sentence per line, redacted against the request's case; no notices or fixed disclaimers, no model call, nothing saved. A logged view of the record; 404 without one (the form starts empty) |
| GET | `/assistant/knowledge/feedback/{id}/answers/{answer_id}` | Support | One of the (at most 2, most recent) earlier answers that record names (view logged); any other id is 404 |
| POST | `/assistant/knowledge/guidance` | HR | Propose new or changed guidance |
| POST | `/assistant/knowledge/reindex` | Support | Rebuild the vector index: re-embed every current approved entry (e.g. after changing `AI_ASSISTANT_EMBED_MODEL`) |
| GET | `/assistant/knowledge/stats` | Support | Entry counts, how helpful answers were, and confidence by topic (helpful / not helpful per blocker code) |

### Answer records

Every answer except small talk is saved as an answer record (`answer_records.py`, store
schema v5; D-084, proposed) and the reply carries its `answer_id` (in the final `done` event
for /chat/stream). A record holds only what the server produced or received in that request:
the question as the model got it (after the 600-character cut), the ids of earlier answers
in the chat that the server found to be this user's on this case (at most
`max_history_messages`), the case's blocker codes, stage, steps and a facts hash, the
knowledge retrieved (tag, kind, entry, version, scores, the score thresholds, confidence,
degraded), the allowed lines each tagged policy (a fixed catalog line), case (a catalog line
filled from this case) or knowledge, the lines shown and the answer as the RM saw it (all
redacted with the case Redactor except the fixed policy lines, D-090), the lines left out (redacted, at most
8 KiB) and how the answer was made (answered by, notices, fallback reason `model_unavailable`,
`nothing_allowed` or `cut_short`, model, time). Browser history text is never stored, and a
record never goes into a prompt or into knowledge. Each record can be rated once; "Not
helpful" links it to the new enhancement request. If a record could not be saved, the answer
has no `answer_id`; "Not helpful" is still offered, the RM is told the reviewer will only
see the note, and the request page says there is no answer record (a small-talk reply,
marked `small_talk`, never has one, so the panel says nothing about it). The Knowledge
Review tab lists each request as one row (question, note, blocker types, age); the row
opens the request as a full-width page: **What the RM saw** (question, answer and notices,
then "Earlier in this chat (N)", up to 2 earlier exchanges, folded and fetched only when
opened, and the RM's note), **Why the AI answered this way** (a rule-based hint, not a
verdict: "Catalog gap: no allowed line matched", "No knowledge found" or "Missing
knowledge"; shown lines tagged Policy/Case/Knowledge, left-out lines crossed out, knowledge
with scores and thresholds, all allowed lines, the case at the time) and, below them, the
fix. When the request has a record, the fix starts from the AI's left-out lines (a guidance
change from its current title and approved text with those lines below), with the
Redactor's placeholders marked and a **Clear** button. Save stays disabled, and the service
refuses the fix, until every placeholder is rewritten in general terms; nothing is saved
until Save, and the other save rules are unchanged. A version saved from it records `started_from_answer`, shown in its review
history and on its review card. Records tied to no request are deleted after `AI_ASSISTANT_ANSWER_RECORD_UNRATED_DAYS`
(7). A record linked to a request, and the up to 2 earlier answers kept with it
(`answer_record_keeps`, same user and case; one row per request that shows it), are deleted
`AI_ASSISTANT_ANSWER_RECORD_CLOSED_DAYS` (30) after the request was resolved or closed (a
record tied to two requests waits for both): on start-up and at most hourly with a new
record.

### In the app

The panel is built on `@assistant-ui/react`. Each answer shows the guidance and past cases it
cited as chips (G1, P1 …). Feedback is given once per conversation (D-105): **End conversation**
asks "Was this issue resolved?", then how satisfied the user is (Yes: very satisfied, satisfied
or neutral, with optional comments; No: neutral, unsatisfied or very unsatisfied, with a required
"How should it be improved?"), and the chat starts again. **History** lists the user's past
chats; one opens back in the chat to continue it (a rated chat continues as a new conversation;
client details in past answers show as placeholders). Knowledge review is not
in the panel: Support users (`KNOWLEDGE_REVIEW`) review on the **Knowledge Review** tab (D-103);
Directors no longer review knowledge. With no case open, Support gets a chat about the approved
rules and the active policy (`POST /assistant/support/chat`, local model only, exact-line rule).
On the registered hosted deployment (D-130) the activated Claude configuration also answers
the general chat, Support's chat and "Try with this change", with boundary-approved repository
knowledge only and every case-chat control; anywhere else they stay local-only (D-115, D-105).

### Demo script

1. Sign in as an RM, open a case blocked by a document/ACRA address conflict, open the AI Assistant.
2. Ask "Can I use the document address?" The answer cites guidance [G1] and an illustrative past
   case [P1], shown as chips.
3. Click **End conversation**: **No**, **Very unsatisfied**, and say how it should be improved,
   naming the client.
4. Sign in as Support (support-user), open the **Knowledge Review** tab: the conversation is at the
   top with **High** priority and the comment's client name replaced with `[COMPANY]`. Click
   **Review**; under **Write the fix**, write what resolves it as a past case. **Save as draft**
   keeps it for later (the row then shows **Edit draft**).
5. **Save and publish**, check the final text and **Confirm and publish** (Support is the single
   reviewer). The row now shows **Fixed**.
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

## Observability (off by default)

`AI_ASSISTANT_TELEMETRY` (`off` by default) controls content-free metrics for each explicit
question (`ai_assistant/telemetry.py`). With `log`, every `/chat` or `/chat/stream` answer,
small talk and fallbacks included, writes one JSON line on the `ai_assistant.metrics` logger
(standard error unless that logger is configured).

A record holds only counts, sizes, timings, closed-vocabulary codes and opaque references:
route, `answered_by`, fallback reason (`small_talk`, `model_disabled`, `model_unavailable`,
`policy_no_allowed_line`, `stream_partial`), model name, prompt version (a hash of the prompt
builder, rules and page terms), characters per prompt part, history turns, retrieval
confidence with each retrieved entry's kind, version, score and an opaque reference (a hash
of its id), allowed catalog and knowledge lines, kept and left-out lines, cited sources,
cut short, cancelled, and timings (retrieval, first model piece, first answer text shown,
total). It never holds the question, history, answer, an allowed line, a title, a name, a
case or document value, a user id or the case id. Every field is checked when the record is
built: a value that is not content-free is refused, the record is dropped and counted, and
the refusal never quotes the value. A failing sink never changes the answer, and with
telemetry off no record is built. Tests and the offline harness pass their own sink to
`create_app(metrics=...)`.

Limits: `cancelled` means the stream ended without its final event reaching the client,
which covers a client that disconnected and an unexpected server error mid-stream alike.
A request whose case cannot be loaded, or whose question preparation fails, has no record,
and neither has a `/chat` request that ends in an unexpected server error.

## Offline evaluation (no model spend)

`assistant_eval/` measures which allowed lines answers select, offline and deterministically.
It runs the real service over synthetic scenarios (`tests/fixtures/eval/scenarios.json`: 16
single-question scenarios and 5 four-turn conversations, built from the saved Garden fixtures
with the synthetic variants in `assistant_eval/variants.py`), with a fake CLM backend, a
temporary knowledge base (repository guidance and the illustrative seed) and the
code-default settings (environment and `.env` ignored for the measured app; importing
`ai_assistant.main` still builds that module's own app from them, as it always has). The
knowledge store's clock and retrieval's "now" (`create_app(retrieval_clock=...)`) are both
fixed, so the frozen snapshots do not change with the date. Embeddings are off, so
retrieval runs in its keyword-and-context mode; the snapshots say so.

```
cd apps/assistant
../../.venv/bin/python scripts/evaluate_answers.py check        # frozen snapshots still current?
../../.venv/bin/python scripts/evaluate_answers.py worksheet    # allowed lines per question, for labelling
../../.venv/bin/python scripts/evaluate_answers.py run --model self-test-perfect
```

| File | What it is |
|---|---|
| `tests/fixtures/eval/snapshots.json` | What each of the 84 questions offers the model: allowed lines with stable ids (`C-` catalog, `K-` knowledge by entry, version and sentence, independent of its `[Gn]` tag), retrieval, part sizes and a prompt fingerprint without history. `check` reports drift after a prompt, catalog or retrieval change; drifted questions are left out of gold scores |
| `tests/fixtures/eval/gold.json` | **Stubs only.** Gold labels (`relevant`, `primary`, `must_not`, `expect_fallback`) are written by the owner/team, never by the harness; `lock` then freezes them in `gold.lock.json` |

Scores need no model as judge: fallback rate and reasons, line validity, unsafe display
(shown lines that are not allowed lines; must be 0), cut-short rate, latency, prompt size,
stability across repetitions and conversation-versus-single consistency, and, with gold,
precision/recall/F1, primary hits, must-not violations, expected case-data answers and
citations. Every report starts with its kind:

- `EVALUATOR_SELF_TEST`: a fixed-rule selector (`self-test-perfect`, `-random`, `-prose`,
  `-injection`) with synthetic self-test gold. It checks the harness and says nothing about
  any model.
- `MODEL_RUN_UNLABELLED`: a local model without locked owner gold; label-free measures only.
- `MODEL_EVALUATION`: a local model against locked owner/team gold (synthetic data, LOCAL
  evidence).

`run --model local` uses the service's own adapter and is refused unless the URL is a
literal loopback address and no proxy is configured (environment variables or the system
proxy settings the HTTP client reads). There is no remote or paid model path. The runtime
package never imports `assistant_eval`; `create_app(on_prepared=..., retrieval_clock=...)`
are the in-process seams the harness uses, and neither is ever set from settings. Reports go
to `data/eval/` (not in Git).

## Model profiles and budget guard (remote profile dormant)

Phase A2 (D-091, accepted for the dormant scope only; activation is not authorised) adds a
code-defined model registry (`ai_assistant/model_profiles.py`) and one composition point
(`ai_assistant/model_factory.py`).
The default profile, `local_openai_compatible`, builds exactly the adapter described above with
the same arguments, so the default model request is byte-identical
(`tests/test_default_request_golden.py`). Prompts, retrieval, the exact-line guard, fallbacks,
notices and routes are unchanged.

The `openrouter_gpt_oss_120b` profile is **dormant** in the service: a running service
cannot reach a network through it. It composes only if all four locks hold, and a running
service cannot open the first two:

| Lock | Condition |
|---|---|
| L1 | the injected transport object is exactly `httpx.MockTransport`; a real, async or subclassed transport, or any other transport object, is refused. The check is on the transport's type: a mock's handler is test code and is not inspected, and the test suite's network guard fails any connection it would make |
| L2 | the registry holds an approved record for the full endpoint slug (`provider[/variant][/region][/tier]`; a base provider slug matches every endpoint of that provider), shown to identify one endpoint |
| L3 | `AI_ASSISTANT_REMOTE_INFERENCE_DECISION` names the decision id |
| L4 | an initialised, healthy budget ledger exists (the service never creates one) |

The `OPENROUTER_API_KEY` variable is read only from the process environment, only for this
profile and only after every other check. It is never read from `.env`, never sent to the
local model and never logged. The service never sends a request to OpenRouter.

### Phase B live experiment (D-092, proposed; synthetic cases only)

Phase B approves one endpoint, `deepinfra/bf16` (DeepInfra, bf16, US$0.037/M input and
US$0.17/M output, maximum completion 117,964 tokens, in the public ZDR list; read
2026-10-26T17:05Z), and adds a live gate that only the evaluation harness can open. L1 then
also accepts the `LIVE_NETWORK` marker (httpx's own HTTPS transport, certificates verified,
no retries, no proxies or redirects) when **both** the caller passes `allow_live_network`
and `AI_ASSISTANT_REMOTE_LIVE_DECISION=D-092`; L2 to L4 and the request policy are unchanged.
Only `scripts/evaluate_answers.py` passes that argument, and it serves only the saved
synthetic fixture cases through its mock CLM backend (a test checks that `main.py` never
does), so no CLM case data can reach OpenRouter. The one other opener is the D-094 local
synthetic test mode (below), which is off by default and is used only inside the synthetic
boundary.

```bash
cd apps/assistant
# Owner, in the shell used for the run only: set OPENROUTER_API_KEY, and
#   AI_ASSISTANT_REMOTE_INFERENCE_DECISION=D-091, AI_ASSISTANT_REMOTE_LIVE_DECISION=D-092.
../../.venv/bin/python scripts/budget_ledger.py init --cap <U0 + 1.00> \
    --opening-provider-usage <U0> --key-alias key-01
../../.venv/bin/python scripts/evaluate_answers.py preflight \
    --owner-attests-auto-topup-off --owner-attests-prompt-logging-off
../../.venv/bin/python scripts/evaluate_answers.py run --model openrouter \
    --scenarios tests/fixtures/eval/phase_b_questions.json \
    --questions P01#1,P02#0 --expect-count 2 --label rerun \
    --owner-attests-auto-topup-off --owner-attests-prompt-logging-off
```

`preflight` (also run at the start of every live run, which refuses unless it passes)
re-reads the public endpoint listing and ZDR list (prices, maximum completion, provider,
quantization, slug uniqueness, ZDR membership), reads the key's own limit and usage
(`GET /api/v1/key`: a limit must be set, never reset, and leave at most US$1.00 plus one
reservation, so set it to the key's current usage + US$1.00; the key's usage must equal the
ledger's opening usage before the first call or be within the ledger afterwards), verifies any
call an earlier, interrupted run left unverified, checks the ledger (healthy, breaker closed,
cap at most US$1.00 above the opening usage) and needs the owner's attestation that auto
top-up and prompt logging are off (neither is readable through the API). A live run asks only
`phase_b_questions.json`, and only the question ids listed with `--questions`, whose number
must equal `--expect-count` (checked before the preflight; `--only` is refused for a live run,
and the run reports a mismatch if the questions asked differ from the list). After each turn the
harness reads generation metadata (`GET /api/v1/generation`, metadata only), waiting at most
two minutes while it is not yet published, and marks each call `verified` (provider DeepInfra,
model `openai/gpt-oss-120b`, total cost equal to the settled cost) or `quarantined` (any
mismatch, metadata still missing after the wait, or no generation reference at all), which
opens the ledger breaker so every later call is refused. A stream that fails after its
generation id arrived keeps that reference for verification. Answers go to `answers.jsonl` and
content-free telemetry, ledger and verification rows to `calls.json` under
`data/eval/phase_b/`. `evaluate_answers.py recheck` (same gate and decisions, no inference)
fetches the metadata of quarantined calls again and passes only if each now matches, the
breaker is open for `routing_anomaly` alone and the key's usage is within the ledger; it
changes nothing; continuing is still `budget_ledger.py reconcile` then `reset-breaker`.

Budget guard (`ai_assistant/budget.py`, `scripts/budget_ledger.py`): a git-ignored SQLite
ledger counts one key's cumulative usage in micro-USD, the usage before the ledger existed
included. Each call reserves a labelled worst case first (content tokens bounded by UTF-8
bytes, template tokens by an engineering allowance, prices and output by the endpoint record;
not a proven maximum), is settled from the provider's `usage.cost`, and anything uncertain is
charged at its full reservation. Missing usage, a cost or token count above the bound, a
routing anomaly, a refusing provider error or an abandoned call opens a breaker that an
operator closes only after reconciling against the provider's usage. A missing, corrupt,
newer or inconsistent ledger is refused, never recreated or repaired. Plan:
`.ai-pipeline/001_planner/AI_ASSISTANT_PHASE_A2_GOVERNANCE_AND_IMPLEMENTATION_PLAN.md`,
sections 5 to 8.

```
cd apps/assistant
../../.venv/bin/python scripts/budget_ledger.py --ledger PATH status   # amounts and codes only
```

Metrics version 2 adds content-free profile, requested endpoint, usage, budget and error-class
fields; telemetry stays off by default. The test suite fails on any connection to a host that
is not this machine (`tests/conftest.py`).

### Claude API model benchmark (evaluation only; synthetic Phase B questions)

`scripts/benchmark_claude.py` asks the 17 Phase B questions through the real service with
`assistant_eval/claude_bench.py`, a harness-only chat model over the native Anthropic Messages
API (official SDK, installed git-ignored in `data/anthropic-sdk`). It is not a runtime profile:
no Claude model is selectable in AI Models and the service never imports it. Every prompt must
pass the D-094 synthetic text check and an offline SHA-256 approval (`prompts`); the free
`preflight` checks the Models API, counts every prompt's tokens and prices the worst case; the
paid `run` makes one request per model and question, pinned to `https://api.anthropic.com`,
with no retries and no server-side model fallback, against its own SQLite ledger (run cap at
most US$6, at most US$0.10 reserved per call, at most 51 calls, breaker on any model, tier,
geography or cost discrepancy; any refusal before sending also stops the run).
`--ledger NAME` gives each experiment its own ledger and preflight file. The SDK client always
gets an explicit direct transport (its default would mount system or environment proxies).
The key is read only from `AI_ASSISTANT_ANTHROPIC_API_KEY` in the process environment. Results, ledger and a blinded owner-scoring set stay under
`data/eval/claude/`. Report: `.ai-pipeline/reports/CLAUDE_API_MODEL_BENCHMARK.md`.

## Model management (D-093; local loopback models only)

An HR administrator (`MODEL_CONFIG_MANAGE`) can switch the application-wide model among the
local models IT configured, from **AI Models** in the CLM. IT setup, rules and failure
behaviour: [`docs/integration/AI_MODEL_CONFIGURATION.md`](../../docs/integration/AI_MODEL_CONFIGURATION.md).

### D-094 local synthetic test mode (GPT-OSS 120B in the CLM chat; off by default)

On a development machine the owner may enable GPT-OSS 120B through OpenRouter as a model on
the same **AI Models** page. Setup and conditions are in section 9 of the guide linked above.
The existing chat then sends a question to it only when the whole prompt is inside the
synthetic boundary; otherwise nothing is sent and the RM gets the case-data answer:

- the case is GARDEN BUSINESS (UEN 11111999A) from ACRA MOCK;
- the document list was read and every document (also those the case summary names) is a
  fictional fixture file;
- the values come from the fixtures;
- the viewer is a seeded POC user;
- only repository guidance and the synthetic seed are used;
- the question and history pass a word screen:
  - printable ASCII and a few named typographic marks only;
  - words from the synthetic sources;
  - at most three number groups across the user turns, never two side by side.

  The screen guards against accidental entry, not deliberate encoding. It cannot recognise
  a real name made of ordinary words or numbers spelled out as words, and its number cap is
  per request. So real customer details must never be typed.

The modules are `ai_assistant/remote_test.py` (gate and per-call checks),
`ai_assistant/synthetic_boundary.py` (boundary check) and `ai_assistant/remote_checks.py`
(the Phase B preflight and verification, shared with the harness). After a change to prompts,
fixtures or the application's wording, regenerate the boundary and review its diff:

```
cd apps/assistant
../../.venv/Scripts/python scripts/build_synthetic_boundary.py
```

- Off unless `AI_ASSISTANT_MODEL_PROFILES_FILE` names a profiles file (example:
  `model_profiles.example.json`); the `AI_ASSISTANT_LLM_*` model stays the baseline.
- `model_catalog.py` (profiles, loopback rule, prompt bound), `model_admin.py` (active model,
  API under `/assistant/admin/models`), `model_admin_store.py` (state and audit, SQLite under
  `data/models/`), `model_qualification.py` (connection test, capacity check, gates).
- Qualification runs `scripts/qualify_model.py` in its own process (the harness never loads
  into the service); technical gates only, answer quality `NOT_SCORED` until owner gold is
  locked.
- Remote profiles are never usable here (D-091 dormant; D-092 proposed, synthetic only).

## Hosted deployment (Stage A: private, no model)

`assistant_hosting/` wraps the service for a private container beside the AWS demo stack. It
needs no model and no provider key, and it refuses to start with any remote setting. It lives
outside `ai_assistant` so the qualification basis and the synthetic boundary do not move.

- Release steps, Caddy change, recovery and measurements: [deploy/RELEASE_HANDOFF.md](deploy/RELEASE_HANDOFF.md)
- Remote models in the cloud (Stage B) are a separate proposal, not approved and not part of this
  service.
- Docker smoke with real Caddy, backend and MongoDB: `deploy/smoke_hosted.py`

## Tests

```
cd apps/assistant
../../.venv/bin/python -m pytest
../../.venv/bin/python -m ruff check ai_assistant assistant_eval tests scripts
../../.venv/bin/python -m mypy ai_assistant assistant_eval
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
