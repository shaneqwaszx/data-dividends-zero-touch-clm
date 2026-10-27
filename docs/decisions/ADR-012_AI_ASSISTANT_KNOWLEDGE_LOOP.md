# ADR-012 - AI Assistant knowledge loop: local knowledge store, assistant-ui panel, catalog plus approved knowledge lines

## Status

Proposed, with section C accepted. Sections A and B are proposed for owner acceptance with
PR #99; section A's chromadb footprint is decided by D-075: the direct pin
(`chromadb==1.5.9`) is retained and its transitive packages stay unlocked. Section C keeps
the owner's G6 direction (quoted in C), and the owner explicitly accepted its extension of
the allow-list with approved knowledge lines on 2026-10-21 (D-074). Section A's feedback
flow is amended by D-083 (proposed): drafts no longer come from "Solved it" / "Yes, helpful";
a Director writes the fix for an enhancement request ("Not helpful" with a note). **D-083 also
relaxes D-074's two-person control for the POC (single-reviewer mode, below) and needs the
owner's (Shane's) explicit acceptance before merge.**
Amendment 2 (D-090, proposed) adds explanation sentences, fixed lines and value templates to
the catalog (one of them relaxes section C), steers the model by question topic, adds each
topic's required lines and matches model lines ignoring formatting only; **it also needs
Shane's explicit acceptance before merge.**

## Date

2026-10-21

## Context

PR #99 adds a knowledge loop to the separate AI Assistant service (`apps/assistant`):
reviewed official guidance and approved past resolutions are retrieved and cited in answers,
RMs can mark an answer as solved or not helpful, and Directors review drafts (since D-083,
proposed: a helpful rating only, and a "Not helpful" note is an enhancement request that a
Director handles). The 2026-10-06
architecture entry describes the assistant as read-only with no persistence owner; that is
still true towards the CLM backend (GET only) but no longer true for the assistant's own
data. The independent quality gate on `ad4661c` (FAIL) and its architecture review (REVISE)
require this ADR before the change can be accepted. The gates on the two remediation heads
(`79621fe`, `97612a1`) failed again on replacing the exact-line catalog with sentence-level
checks of model prose, and the owner then decided G6 (section C). Review authority remains
`UNKNOWN_BLOCKED` (Q-014); nothing here is sponsor review policy.

## Decision

### A. Knowledge persistence inside the assistant service

- SQLite (`knowledge/store.py`) is the single source of truth for knowledge entries, their
  versions, review decisions, RM feedback and index tasks. ChromaDB (`knowledge/vector_index.py`)
  is a rebuildable search index of current approved versions only. Both live under
  `apps/assistant/data/` (git-ignored) and hold no CLM case data beyond redacted drafts.
- Versions are append-only. A reviewer's edit is a new version written by that reviewer
  (`revises` names the version it came from); the earlier version is kept unchanged and
  taken out of review. Nobody who wrote a version in that chain may decide it (except in the
  POC's single-reviewer mode, below), and every API decision or edit carries the content
  hash of the version the reviewer was shown.
  Every change runs in one SQLite write transaction taken before its checks (BEGIN
  IMMEDIATE) and moves a version on only while it is still pending, so concurrent decisions
  or edits have exactly one winner and the others get a clean 409. The first check in a
  review or guidance change reloads the caller from the CLM backend (same user, capability
  and scope), so a role, team or session withdrawn since the request began stops it and
  nothing is written. An entry may only
  replace an entry of the same kind. Retiring an approved entry, official guidance
  included, takes two reviewers: one asks, a different one confirms.
- Feedback (D-083, proposed; it replaces drafting from "Solved it"): "Yes, helpful" only
  records the rating with the case context (blocker codes, fields, stages) and counts towards
  confidence by topic in the stats; it drafts nothing and changes no retrieval or ranking.
  "Not helpful" needs a non-blank note (422 otherwise) and is an enhancement request
  ("gap" in the code). Directors (`POLICY_APPROVE`) handle an open request end to end; HR
  does not (it has no case access). A Director either writes the fix, a past resolution or a
  guidance change (new guidance, or a new version of existing guidance, whose visibility it
  takes from the current approved version, as it does the scope check, unless the Director
  sets one), linked to the request by that exact version (a reviewer's edit moves the link)
  and pending review like any other entry (publishing that version marks the request
  resolved, rejecting it opens it again; decisions on other versions of the same entry leave
  the request alone), or
  closes the request with a required reason. Both recheck the caller inside the write
  transaction like every other review change.
- Single-reviewer mode (D-083, proposed; **relaxes D-074's two-person control for the POC and
  needs the owner's (Shane's) explicit acceptance before merge**). Why: the synthetic users
  have one Director (olivia-koh) and only `POLICY_APPROVE` approves knowledge, so with
  author ≠ approver nothing a Director writes could be published. The setting
  `AI_ASSISTANT_KNOWLEDGE_SINGLE_REVIEWER` (default true for this POC) lets a reviewer approve
  or reject an entry they wrote or edited. Approving shows them the entry's final text and
  needs an explicit confirmation (`confirm_single_reviewer`; otherwise 403
  `CONFIRM_SINGLE_REVIEWER`); every such decision, approval or rejection, is recorded as
  single-reviewer in the review history, and the Review window lists the entries currently
  published that way (a replaced or retired one, or a rejection, is only in the entry's
  history). With the setting false the two-person rule
  applies unchanged. In both modes the decision stays bound to the content hash, the sentence
  checks and redaction stay as they are, and retiring an approved entry still takes two
  reviewers.
- Team scope: a draft from an enhancement request carries the team the request came from
  (before D-083, a "Solved it" draft carried its RM author's team). Directors, whom
  the CLM backend scopes globally (a Director has no team), see, edit and decide every
  team's drafts and enhancement requests, and their stats count every team; other actors
  keep the team rule and see only their own team's drafts, requests and stats. An edit can narrow team and role
  visibility but never widen it. HR guidance keeps the visibility HR sets.
- Redaction: an enhancement request's note is redacted when it is stored, and a Director's
  fix (since D-083) is redacted against the request's own case, loaded with the Director's
  session (a case they cannot load stops the change), before it is stored; earlier "Solved it"
  drafts used the RM's note and questions. Both remove the company, addresses and
  identifiers, and the parties the case summary names in the shapes the redactor knows: objects with a `party_type`, entries of person lists such as
  `officers` and `shareholders` (registry officers carry no `party_type`), and person-name
  fields. A known address is replaced whole and also by each of its comma-separated parts
  that has a letter and at least 6 characters (a street line; a bare country code such as
  `SG` is kept). Matching ignores letter case and whitespace between words. Names the case
  data does not contain, or spells differently, are not recognised (bank staff, such as the
  RM, are not case parties). Feedback no longer carries the conversation at all.
- ChromaDB product telemetry is disabled (`Settings(anonymized_telemetry=False)`) on every
  client. The embedding endpoint must be a literal loopback URL (the warm-up rule,
  `llm.is_local_model_url`); embedding requests ignore proxy environment variables and do
  not follow redirects.
- The assistant keeps reusing the CLM capabilities `POLICY_APPROVE` (review) and
  `POLICY_MUTATE` (propose guidance) as a POC mapping. This is `PROJECT_DEFINED_PROVISIONAL`
  and recorded for owner confirmation; it is not sponsor-approved reviewer authority.
- Existence check: the closest existing maker-checker owner is `PolicyManagementService` /
  `PolicyCatalogue` (D-064: HR proposes, a Director decides, one lock and repository CAS).
  It owns bounded runtime rule values that cases freeze, not versioned free text with
  retrieval, RM feedback and index tasks, and it lives in the CLM backend, which the
  assistant only reads. It is therefore not reused; this means a second four-eyes
  implementation exists, for a different aggregate.
- Python footprint: `chromadb==1.5.9` adds 62 transitive runtime packages (18 to 80 in the
  assistant environment), among them onnxruntime, grpcio, kubernetes, the OpenTelemetry SDK
  and exporters, huggingface-hub, tokenizers and numpy. They are not locked (no lock or
  constraints file). D-075 retains the direct pin with the transitive packages unlocked,
  without a new dependency management system or a broad dependency upgrade.

### B. `@assistant-ui/react` 0.15.23 in the frontend panel

- Used only as chat presentation primitives with `useExternalStoreRuntime`: the panel
  component stays the owner of its message state; every request goes through the existing
  `aiAssistant.ts` client and `authenticatedFetch`; the panel stays keyed by
  `actor.user_id`. No cloud runtime, `assistant-cloud` client or remote adapter may be
  imported or configured.
- Version pinned exactly; upgrades are a reviewed dependency change. It adds 93 runtime npm
  packages (MIT/BSD-3-Clause/0BSD, no install scripts, 13 of them pre-1.0). Against current
  main `36d8f0e` the production bundle grows by about 331 kB (689 to 1,020 kB; gzip 188 to
  286 kB, +98 kB).

### C. Output policy: the exact-line catalog stays mandatory; approved knowledge adds lines

Owner direction (G6, 2026-10-21), verbatim: "Preserve the deterministic safety guarantees of
the original output catalog. Treat sentence-level grounding as an additional safeguard unless
an independently supported architecture decision establishes an equivalent or stronger
replacement. Do not silently remove mandatory checks."

- Mandatory gate, as on main (PR89 `8407d9e`): model text reaches the RM only as whole lines
  that exactly equal an allowed line, in whole answers and while streaming. The catalog
  (`allowed_guidance`) is main's, unchanged: trusted templates filled only from this request's
  backend projection. Free model prose, paraphrases, history and document values never extend
  the allowed lines. If no allowed line remains, the deterministic case-data answer is shown
  with "The model response could not be verified".
- Extension, knowledge lines (**accepted by the owner on 2026-10-21**, D-074): for
  each entry that retrieval returned for this user and case and that is approved and visible
  to them (checked again before use), each sentence of the approved body becomes the line
  `<sentence> [Gn]` or `[Pn]`, exactly as approved (a leading list marker is dropped and
  runs of spaces become one), and only if the sentence passes the sentence checks against
  this case's facts. The prompt lists these lines with the catalog and tells the model to
  copy lines exactly; source chips still come from the tags.
- The other knowledge text in chat replies (`/chat` and `/chat/stream`) passes the same
  checks or is not sent: an entry title (source chips, the no-model answer, the prompt) is
  shown only if it passes, otherwise a neutral label ("Guidance G1", "Past case P1") is
  shown; a follow-up question (suggested questions) is dropped unless it passes; titles and
  follow-ups longer than 200 characters never pass. A source object carries only the tag,
  kind, version, that title, the approval time and the illustrative, fallback and cited
  flags: the entry id and the free-text source reference are not sent to the RM's browser
  or put in the prompt. Guidance ids derived from a title use ASCII letters and digits only.
- Outside chat replies, the author of a draft (an RM without review capabilities) can read
  only the versions they wrote through `GET /assistant/knowledge/entries/{id}`, without
  reviewers' edited versions or review notes. That includes a store migrated from schema
  v2, where a reviewer's edit changed the RM's pending version in place and kept the RM as
  its author, also when it was edited again after the migration. Since v3 every 'edit' row
  on a version is paired with exactly one version that revises it, so a version with
  another person's 'edit' row and more 'edit' rows than versions revising it is left out
  (a version its author edited in place that someone else then edited normally is left out
  too, the safe side). Directors (global, as in section A) and HR in the entry's team see the
  full history (including Directors' review notes on RM drafts); the review screens are for
  them only and show unfiltered entries by design.
- Controls for knowledge content: **two-person approval of every version is the primary,
  robust control** (two different identities, a decision bound to the content hash,
  team-scoped except for global Directors). D-083 (proposed, needs the owner's explicit
  acceptance) relaxes this for the POC: with `AI_ASSISTANT_KNOWLEDGE_SINGLE_REVIEWER` on (the
  default), one confirmed reviewer may publish their own entry, recorded as single-reviewer;
  the sentence checks below are unchanged and then carry more of the weight. The sentence checks are a **secondary,
  best-effort filter** with documented limits. They run on knowledge text only, never on
  model text, and fail closed: characters
  outside printable ASCII and typographic quotes, dashes, ellipsis and bullet (tabs,
  non-breaking and invisible spaces, look-alike letters from other scripts); numbers of
  three or more digits, decimals, UENs including the T/S/R format, NRIC/FIN, postal and unit
  numbers, step counts, quoted labels, listed contact phrases, e-mail addresses, web
  addresses written with `http://`, `https://` or `www.` (bare domains such as
  `portal.example.com` and other schemes such as `ftp://` are not recognised), and
  `(section: ...)` names that are not in this case's facts; citation tags inside the body;
  the listed action phrasings for actions this RM is not offered and the listed authority
  phrasings, unless a fixed negation directly governs them (the cycle-2 rule, without the
  coordination exemption the third gate bypassed); the listed Live phrasings; document values
  presented as confirmed. Text in a knowledge entry never vouches for its own values or
  labels.
- Bound per answer: at most 20 lines per entry and 48 knowledge lines of at most 8 KiB in
  all are offered; lines past the limits are not. Each streamed update re-sends the answer
  so far, so one stream sends at most one update per allowed line, each no larger than the
  allowed text. The fourth gate's pathological entries (4,788 lines) produced about 126 MB
  of updates before the bound; with it, the same 1-byte stream sends about 100 kB (the test
  allows 512 kB), and the fifth gate's adversarial worst case for one stream is about 1.1 MB.
- Streaming is main's line-based acceptance: only new text is split into lines, each
  complete line is looked up once and dropped from the buffer, an unfinished line is never
  shown, and model text is bounded at 64 KiB. After a stream failure only lines completed
  before it are kept, with the cut-short notice.
- Cost: model text is only split into lines and looked up in a set. On the third gate's 42
  probe shapes at 64 KiB the whole stream took at most 0.04 s in 1-byte feeds, and no single
  feed took 1 ms. The sentence checks run once per retrieved knowledge sentence per request;
  each match costs bounded work (a governing negation is searched within 80 characters, and
  phrase breaks and negation words are found once per clause). The slowest 64 KiB probe body
  took 0.18 s. Bodies proposed or edited through the API are limited to 4,000 characters;
  drafts from enhancement requests hold one note of at most 1,000 characters (drafts from
  "Solved it" in older stores can be longer: a 4,000-character question and a 1,000-character
  note), which the per-answer bound above covers.
- Residual risks:
  - Answer flexibility is reduced to selecting catalog and knowledge lines, so answers are
    less fluent and less specific than free prose; a question the lines do not cover gets
    the case-data answer.
  - Knowledge granularity: bodies are split at line breaks and after `.`, `!` or `?`
    followed by a space. An abbreviation such as "e.g." splits a sentence, a line can be
    shown without the sentence before it, and an entry whose sentences all fail adds nothing.
  - The sentence checks remain a deny-list over reviewed text and catch plain phrasings
    only, not deliberate evasion. Unsafe sentences they do not recognise are offered if two
    people approve them; none of them is ever shown from model output. Known misses, all
    pinned in `KNOWLEDGE_FILTER_LIMITS` in the tests (46 sentences):
    - 17 of the third gate's 81 sentences: context that reverses a negated action
      ("Previously you couldn't approve the case, but now you can.") and authority wording
      outside the patterns ("KYC is approved.");
    - 29 of the fourth gate's 44 further sentences: unlisted action wording (11, "Approve
      it now.", "Sign off the case."), unlisted authority wording (9, "KYC passed.", "The
      client is approved."), unlisted Live wording (3, "ACRA is connected live."), short
      numbers and percentages (3, "The ownership threshold is 10%."), people's names (2,
      "Ask Priya in operations.") and an unquoted stage name (1). The other 15 (look-alike
      letters, invisible characters, a T-format UEN, an NRIC, an e-mail and an `https://`
      address) are now caught.
    - Further evasions the fifth gate found outside these lists (for example "Appr0ve the
      case now.", "KYC: approved.", "ACRA wins."), bare domains, `ftp://` and spelled-out
      e-mail addresses are not caught either.
  - Some genuine text is over-dropped: negations such as the R4 disclaimer (which stays
    available as a catalog line), and the shipped title "Mock, Local, Sandbox and Live data"
    ("live data"), whose chip shows the neutral label instead.
  - The illustrative marker of an entry is carried by its source chip (and, for the seed, by
    the entry's own first sentence), not by every line.
  - Guidance sentences that quote values or labels absent from the case (for example the
    0.85 policy default) are withheld.
- The owner accepted the knowledge-line extension on 2026-10-21 (D-074); the residual risks
  above are unchanged. The independent architecture review of `8457f02` reviewed this section
  (PROCEED, conditional on that acceptance and on the chromadb footprint). D-075 decides
  section A's footprint and defers the real-embedding evaluation; the PR stays Draft until
  the remaining verification below is complete.

## Alternatives considered

- Extend an existing CLM backend owner with knowledge tables: rejected; it would make the
  CLM persistence owner hold assistant data and add assistant writes to the case backend.
- No persistence (static guidance files only): keeps the read-only assistant, but loses the
  reviewed feedback loop the PR exists to add.
- Keep the plain React panel: viable; the library was chosen for chat primitives and
  streaming rendering, at the dependency cost recorded in B.
- Reuse `PolicyManagementService` / `PolicyCatalogue` (D-064) for knowledge review: not a
  fit (see the existence check in A).
- Replace the catalog with sentence-level checks of model prose (the PR #99 author head and
  the first two remediation cycles): three independent gates found bypasses of that
  deny-list, and the owner's G6 direction keeps the catalog mandatory.
- The catalog alone, without knowledge lines: the strictest, but it cannot carry cited
  knowledge.
- Source chips only (no knowledge lines in answers): retrieved entries are listed as
  sources next to a catalog-only answer, so the catalog stays untouched while the answer
  still cites. Not chosen because the RM would only see that guidance exists, not what it
  says, which is what the knowledge loop is for; the owner chose the knowledge-line
  extension instead (D-074).

## Consequences

The assistant becomes stateful: its data directory needs backup if the knowledge is to be
kept, and the index can be rebuilt from SQLite (`reindex`). Review is stricter than the
original PR: an edited entry always needs a second reviewer. Retrieval needs a local
embedding model (Ollama); without it, index tasks wait and keyword search still works.

## Architecture invariants affected

- Preserved: CLM backend authority (assistant reads CLM data through GET only); backend-
  authoritative RBAC and team scope (the assistant asks `/api/auth/me` every time);
  the PR89 exact-line output catalog as the mandatory gate for model text; no Live claims.
- Added: append-only knowledge versions with maker-checker over the edit chain; decision
  bound to reviewed content; team-scoped review queue (global for Directors, as in the CLM
  backend); loopback-only embeddings; telemetry off.

## Security and persistence implications

SQLite schema v3 adds `entries.revises` (nullable) and a `retire_requests` table; v1 and v2
stores are migrated in place on open. Schema v4 (D-083) adds `reviews.single_reviewer` (0 for
every existing decision) and rebuilds the `feedback` table, in one transaction, to add a
`resolved` status, a nullable `close_reason` and a nullable `entry_version` (the exact version
of a request's fix); every existing row keeps its values and has neither. A reviewer who edited a pending version in place under
schema v2 has only an 'edit' review row on it; that row counts as editing, so they stay barred
from deciding it after the migration, and the version is left out of the RM author's own
view of the entry. No credentials are stored. Redaction is a first pass: names that appear nowhere in
the case data are not recognised, so Director review, with the final text shown before
publishing, remains required before approval.

## Migration and retirement implications

Opening an older store migrates it (v1 -> v2 -> v3 -> v4 -> v5, the last proposed with
D-084: answer-record tables and `entries.started_from_answer`, default 0, added to every
earlier shape and to earlier branch-only v5 shapes). Code from before v5 can still open a v5
store: it rewrites the schema version to 4, does not read the new tables and inserts
entries by naming its columns, so the new column takes its default; the v5 code then
reopens it unchanged. Code from before v4 can still
open a v4 store (it names the feedback and review columns it writes), but it rewrites the
schema version to 3, enforces two-person review again, drafts from "Yes, helpful" again and
closes requests without a reason; the v4 code then leaves the already migrated tables as
they are. A store from an earlier build of this branch (never on main) that is stamped 4
without every v4 column gains the missing ones when it is opened. Rolling back to the PR #99 author head
(`ad4661c`) after a v3 store has been written is not supported: that code rewrites the
schema version to 2 and can still read and decide, but cannot add a version (it inserts 20
values into a 21-column table), and it would ignore edit chains and retirement requests. To
roll back, restore a copy of `apps/assistant/data/` taken before the upgrade, or recreate the
(development-only) store. The exact-line catalog is not retired: it stays the mandatory
output gate.

## Verification

Assistant pytest, ruff, format and mypy. The PR89 catalog tests restored from main; knowledge
lines shown verbatim with their tag, paraphrased, partial or re-tagged lines dropped,
unretrieved, unapproved and other-team entries never allowed, and an approved sentence that
fails a check withheld; an approved title and follow-up that are advice never reaching the
RM through chips, suggestions or the no-model answer (chat and stream); all four gates'
unsafe sentences as model output (never shown, whole or streamed) and as approved knowledge
(withheld, apart from the listed limits); identifiers, addresses and characters; the
per-answer knowledge bound with the fourth gate's pathological entries; 64 KiB stream shapes
including whitespace runs and long tokens with a per-feed bound. Cross-team, global-Director,
edit-then-approve, two-person retirement, concurrent decision/edit, officer and address-part
redaction and forged-turn regressions; restart/persistence and v2-to-v3 migration tests.
D-083: helpful-only ratings, required notes, a Director's fix (past case, new or changed
guidance) for and closing of enhancement requests (scope, HR refused, redaction against the
request's case, resolve/reopen, concurrent draft and close, in-transaction recheck), single-
reviewer mode on and off (confirmation, history marks, editor, second reviewer, self-reject,
two-person retirement unchanged), the full flow with the real synthetic roles (maya-lim,
olivia-koh, hr-admin) and the v3-to-v4 migration.
Frontend Vitest, typecheck and build; real-embedding retrieval evaluation with a local model
`NOT_EXECUTED — MODEL NOT INSTALLED / OWNER-DEFERRED` (D-075);
architecture and project-state checks; a fresh independent quality gate and an independent
architecture review of section C.

## Revisit conditions

Sponsor review authority (Q-014), a second Director account or any non-POC use (turn off
single-reviewer mode, D-083), any non-local embedding or model endpoint, cross-team
knowledge sharing, an `@assistant-ui/react` major upgrade, any further guardrail bypass, or a
proposal to show model text that is not an allowed line.

## Related contracts and sponsor questions

`docs/contracts/POLICY_AUTHORITY_MATRIX.md` (review authority, reviewer separation); Q-014;
D-073 and D-074 in `DECISION_LOG.md`; the 2026-10-06 read-only AI Assistant entry in `ARCHITECTURE.md`.
Proposed Amendment 1 (D-084) follows below. It is not accepted; the Status section above is
updated when it is.

## Amendment 1 - answer records, request lifecycle and document upload (PROPOSED, D-084)

Status: PROPOSED by the project team on 2026-10-25. Not accepted; nothing in this amendment
is built. Each of decisions D1 to D6 in D-084 needs the repository owner's (Shane's)
explicit acceptance before code. The amendment builds on D-083 (still proposed; its code is on
main since PR #108: "Not helpful" with a note starts an enhancement request, and a Director writes the fix
or closes the request with a reason). If D-083 is not accepted, this amendment is revisited
with it.

Scope. All three parts stay inside the AI Assistant service and its local knowledge store
(section A). The assistant stays read-only towards the CLM backend. Existence check: the
knowledge store in `apps/assistant` already owns entries, versions, reviews and RM feedback
(and, with D-083, enhancement requests), so it is extended rather than a new owner added;
the CLM backend's document pipeline is not reused for the first upload step because
Markdown and text need no parser (D3). No new service, provider, dependency direction or
library. Document upload is a new untrusted-input surface inside the existing owner; its
checks are listed under Document upload. Schema v5 of the knowledge store adds the new
tables and request states (main is at schema v4, from D-083).

### Answer records

- The server stores one record per answer and sends the browser only an `answer_id` with
  the reply. The browser never sends answer text back.
- "Not helpful" sends the `answer_id` with the note. The server checks that the record
  belongs to the same user and the same case, and refuses an unknown, expired or foreign
  id; it then links the record to the new enhancement request.
- A record holds:
  - the question as the server used it: as typed, cut at the 600-character question limit;
  - the ids of the earlier answers in that chat (each has its own record);
  - the case snapshot: blocker codes, stage, steps done and a hash of the case facts;
  - the knowledge used: entry tags, ids, versions, search scores, retrieval confidence
    (high, low or none) and whether search was degraded;
  - the allowed lines the model could choose from;
  - the lines the model chose, and the lines it wrote that were dropped (redacted and
    size-capped before storage);
  - the result: notices, fallback reason, model name and timing.
- Only Directors (`POLICY_APPROVE`) and the RM who asked can view a record. Every view is
  logged. HR cannot view records.
- Records stay in the assistant's local store. They are never sent to the model again and
  never copied into knowledge automatically; anything a Director copies into a fix is
  redacted, as D-083 redacts a Director's fix.
- **This relaxes section A and needs Shane's acceptance (D1).** Section A says the store
  holds no CLM case data beyond redacted drafts, and D-083 redacts what an RM writes. An
  answer record keeps the RM's question unredacted and a snapshot of case state (blocker
  codes, stage, steps done, a facts hash). The relaxation is limited by the access rule
  above and the retention below.
- Proposed retention (D2): every record not linked to a request, whether unrated or rated
  "Yes, helpful", is deleted 7 days after the answer (the helpful count in the stats is
  kept without the record). A record linked to a request is deleted 30 days after the
  request ends, as Resolved or Closed. When "Not helpful" links a record, the earlier
  answers it names that the Director is shown (at most 2, the most recent, and only the same
  user's on the same case) are kept with it and follow the same 30-day rule, even when
  unrated; a record tied to two requests stays until both have ended.
- As built (proposed with D-084; schema v5): `answer_records`, `answer_record_views` and
  `answer_record_keeps` (one row per earlier answer and the request it is shown with). The
  Director's queue lists each request with the RM's question; listing the queue is not a
  logged view of the record, opening the record is.
- The Director's fix can start from the record: `GET .../feedback/{id}/fix-start` returns a
  title from the blocker type and the AI's left-out lines (and any shown model line that is
  not an allowed line), one sentence per line, redacted against the request's case loaded
  with the Director's own session. It is a logged view, calls no model and saves nothing.
  The saved version records `entries.started_from_answer`, shown in its review history; the
  flag is not part of what the entry says (its content hash).
- A fix whose title, text or follow-ups still contain a redaction placeholder (`[ADDRESS]`,
  `[COMPANY]` or any `[UPPERCASE]` token) is refused with 422 `PLACEHOLDER_NOT_REWRITTEN`,
  and an edit of a version started from the record may not add one. Placeholders that
  redaction makes on save are kept as before and stay the reviewer's to judge.

### Request lifecycle

- States: New → In progress (one owner) → Fix waiting → Resolved, or Closed with a required
  reason. New and In progress requests can be closed; a request whose fix is waiting needs
  that fix approved or rejected first.
- A rejected fix sends the request back to In progress, keeping its owner and history.
- One fix can resolve several requests: when it is approved, every request linked to it
  becomes Resolved.
- The queue is grouped by blocker type, with counts, and filtered by state, owner, team and
  age, oldest open first.
- Before publishing, the request page shows a red/green diff of what the fix changes.
- Every action (take, write the fix, close) is rechecked inside the database write, as
  today.

### Document upload

- Directors only (D4). Markdown and plain text first (D3 option a), with no new library.
- The upload is checked: allowed file types only, a size limit of 5 MB, valid text. The
  limit is the assistant's own setting, with the same default as the CLM backend's
  `IDP_MAX_UPLOAD_BYTES`; the assistant does not read the backend's configuration. Document
  text is data, never instructions, and is never rendered as HTML.
- The text is split at headings into proposed entries of at most 20 sentences each (the
  catalog's `MAX_LINES_PER_ENTRY`).
- The Director previews every proposed entry, can rename, edit, delete, merge and tag it,
  and sees each sentence marked used or not used with the reason. An upload has no case, so
  the preview runs only the sentence checks that do not depend on a case (characters,
  citation tags, authority phrasings, live claims). A sentence whose check depends on the
  case (for example a UEN, a contact, a web address or a long number) is marked "used only
  when the case facts contain it". The marks are indicative; the full checks still run
  against the case on every answer.
- Entries are saved as drafts that cite the file name and the section heading (Markdown has
  no pages), with the file's fingerprint, and follow the normal review rule (D6): two
  people, or the POC single-reviewer mode if D-083 is accepted.
- Uploading a file with the same name proposes new versions of its entries, shown as a
  diff, and retirement of entries whose sections no longer exist. Removing a file retires
  all its entries; retirement takes two reviewers (D-074), also in D-083's single-reviewer
  mode.
- Synthetic or public documents only for the POC (D5). Real sponsor documents need the
  sponsor's and the owner's agreement first; AGENTS.md forbids tracking confidential sponsor
  material.
- PDF and Word come later, through D3 option (b) or (c), by a later decision. Either one
  would be a new boundary needing its own architecture review.

### Alternatives considered

- Answer context sent back by the browser: rejected. PR #99's review showed browser-sent
  assistant text can be faked, which is why D-083 stopped sending the conversation.
- No answer records: keeps the store smaller, but the Director cannot see why the AI said
  what it said, so most requests cannot be diagnosed.
- Answer records in the CLM backend: rejected; it would add assistant writes to the case
  backend and make the CLM persistence owner hold assistant data (as in section A).
- An external tracing tool (for example Langfuse): rejected for the POC; it adds a
  dependency and moves answer data off the assistant's machine.
- Keep D-083's request states (open, drafted, resolved, closed): there is no owner and no
  In progress state, so nobody is answerable for a request and two Directors can work on
  the same one.
- Retrieval over uploaded documents without review: rejected; it would bypass the review
  step and the exact-line catalog.
- PDF and Word now: D3 option (b) creates a second document parser beside the CLM
  backend's; option (c) adds a Director-only endpoint to the backend, a teammate's area.
  Both are deferred.

### Risks

- The question is stored as typed (cut at 600 characters), so it may contain personal data; this relaxes
  section A (see Answer records). Mitigations: Director and own-RM access only, logged
  views, and the retention in D2, which covers every record.
- Retention runs inside the assistant; if deletion fails, records outlive the agreed period.
  The build needs a deletion test.
- The sentence checks are best effort (see section C), so approved document sentences rely
  mainly on the review step. The preview's used / not used marks support that review.
- A large document can produce many drafts at once, which strains review, more so in
  single-reviewer mode.
- Schema v5 must migrate older stores in place (v4 on main, and any older ones), as
  earlier versions did.

### What stays unchanged

- The exact-line catalog (section C): the model may only output allowed catalog lines and
  approved knowledge lines; anything else is dropped.
- Maker-checker: two-person approval (D-074), apart from the POC single-reviewer mode if
  D-083 is accepted; retirement always takes two reviewers.
- Rechecks of the caller inside the SQLite write lock.
- Read-only access towards the CLM backend: GET only, with the user's session.

## Amendment 2 - explanations, topic steering and required lines (PROPOSED, D-090)

Status: PROPOSED by the project team on 2026-10-26, built ahead of acceptance on branch
`feat/ai-assistant-explanations`. **It needs the repository owner's (Shane's) explicit
acceptance before merge, including the section C relaxation in change 2.** It amends
section C only. It builds on D-084 (Amendment 1, proposed); PR 2's `Validation.dropped` is
merged in when that PR lands.

Why. On a real request ("Explain the registered address difference", request 5) the RM saw
the opening summary again: the no-model answer sent every question with "differen" or "why"
to the opening message, the catalog had no line explaining a difference, and the model's
correct lines were dropped for formatting (`**"Keep registry value"**`, a knowledge sentence
copied without its `[G1]` tag, a bare `Keep registry value.`). A manual test then showed
answers that were safe but long, repetitive or off topic, and varied from run to run.

### Change 1 - reviewed explanation sentences (`guide.py`)

Sentences with no case values, which never say which source is right or that anything is
verified, approved or live, and name only sections that exist. Each stands alone and passes
`sentence_problem` on the synthetic Merlion case (test).

| Lines | Offered when | Source |
| --- | --- | --- |
| "The app compares the value read from a document with the current ACRA record." / "A difference between a document and ACRA can come from a reading error, an old document or a real change." / "Before choosing a value, compare what was read with the document itself." / "Choosing a value is not official verification of either source." | any field differs on a blocker | `services/reconciliation.py` |
| Registered address: "A different registered address can mean the document is older than the current ACRA record, or the company has moved." / "Before choosing an address, check the type of the document and which company it is for." | that field differs | as above; documents carry no issue date |
| Legal name: "A different company name can be a former name, a trading name or a reading error." | that field differs | as above |
| UEN: "A different UEN can come from a reading error or a document that belongs to another company." / "Before choosing a UEN, check that the document belongs to this company." | that field differs | as above |
| "When a person reviews a document, every field read from it needs a review decision." / "A field read with low confidence, or a required field that could not be read, keeps the document review open." | `DOCUMENT_REVIEW_INCOMPLETE` is still needed | readiness in `services/clm_orchestration.py`; the first sentence describes the human-review path only (the backend can also confirm a document automatically or clear it through a reconciliation decision, `services/document_processing.py`) |
| "The UBO check needs the company's owners and each owner's economic interest in percent." / "Ownership evidence can come from the registry, an uploaded ownership document or a manual ownership declaration." / "A manual ownership declaration needs a reviewed current document first." | `OWNERSHIP_REQUIRED` is still needed | `domain/ownership.py`, `services/manual_ownership_evidence.py` |

The "can" / "can mean" sentences give general reasons; the app does not work out why a value
differs, and they never read as a finding about this case.

### Change 2 - fixed lines and templates filled from the backend projection

| Line | Offered when |
| --- | --- |
| `<Field>: ACRA says "<registry value>", the document says "<document value>".` (one per difference; the case-data answer's wording) | a blocker shows the difference, both values are single-line, at most 120 characters, without straight or typographic double quotes (which could close the template's quotes) or unsupported characters, and the whole line passes the sentence checks (which catch only their listed phrasings; other wording stays inside the quotes as the document's value). **This relaxes section C** ("document values never extend the allowed lines"): the document value is untrusted text, shown only quoted inside this template. Otherwise the difference stays model data only. |
| "This case is not ready for GoldTier submission yet." | the readiness facts list a blocker (or a blocker is open) and the case is not completed |
| "Approving the case is not offered to you on this case." | the case is not ready (as above) and no approve-type action is offered to this viewer. A ready case reaches Review & Send, whose Send is the app's final human approval, so the line is never offered there. Worded so the sentence checks recognise the negation ("<action> is not offered"); the requested "is not an action offered" failed them. |
| `<blocker title>: this is for <who resolves it>.` | for each blocker whose owner is one the blocker policy names (`guide.OWNER`), with the title checked like a difference value (including no double quotes of either kind) |
| "The case data does not name a contact for this." | no blocker has such an owner line |
| "I can't answer that from this case's data." | always |
| `Registry data in this case comes from ACRA (<environment>), not the live ACRA service.` (added 2026-10-27, D-092 P7; owner-approved for `ACRA (MOCK)`, other environments by the owner's "source-correct wording" instruction) | the backend's company source (`case.entity.source`) starts with `ACRA (` and names a non-live environment (MOCK, LOCAL, SANDBOX, PARTIAL, DORMANT); never for a live or unnamed source. The same sentence remains the non-live registry notice, which is not repeated when the line is shown. |
| "This case cannot name any UBOs yet because the UBO check has not run." (added 2026-10-27, D-092 P8, owner-approved) | the backend readiness lists `OWNERSHIP_REQUIRED` and ownership is `MISSING` (set together only when the case has no ownership analysis); never for analysed, review, failed or in-progress ownership |
| "Marking the UBO check as complete is not offered to you on this case." (added 2026-10-27, D-092 P9, owner-approved; **topic-only**) | ownership readiness is MISSING, IN_PROGRESS, REVIEW_REQUIRED or FAILED and no action offered to this viewer would complete or accept ownership, UBOs or beneficial owners. Allowed by the guard, but listed to the model only in the QUESTION TOPIC message for a request to complete the check, never in the case facts. |

All values come from the backend projection, never from the model. A line with a changed
value, another case's values or an invented owner is not an allowed line and is dropped.

Answer records (D-084) store these lines redacted: every non-policy line in a record's allowed
lines, and a model answer's chosen lines and shown answer, go through the same Redactor as the
case-data answer. So the values reach the RM's screen but not the record, and ADR-012 section A
is unchanged by this amendment.

### Change 3 - topic steering (prompt only)

The no-model answer's topic detection (`briefing.question_topic`) names the question's topic
in a prompt message and lists that topic's allowed lines in order: why blocked / what next,
a field difference, readiness ("approved", "ready", "submit"), approving, who to contact,
the document review, ownership evidence. The rules ask for at most 6 lines, the answer first,
no repeats, at most one related disclaimer, and, when no topic is given and no line answers,
"I can't answer that from this case's data." with at most 2 relevant lines. The model's view
of the case no longer repeats facts that are already word for word an allowed line. Which
lines are allowed does not change.

Amended 2026-10-27 (Phase B, D-092 proposed): rule 17 now makes that line exclusive for every
question: it is used only on its own and only when no allowed line answers any part of the
question; otherwise the answer starts with the line that answers part of it. The "at most 2
relevant lines" companion was removed after the live evaluation showed answers that both
declined and answered.

Also added 2026-10-27 (D-092 P7 to P9, owner-approved): when no existing topic matches,
three targeted plans steer (i) registry-status questions to the registry source line and
the Mock, Local and Sandbox line; (ii) "who/which ... UBOs / beneficial owners /
shareholders" questions to the UBO line and the ownership-evidence lines when
`OWNERSHIP_REQUIRED` is listed; (iii) requests to complete the UBO check to the completion
refusal, the UBO line where allowed, the open ownership item and the "Ownership & UBO"
section. None requires a line, so a bare decline is never padded, and the no-model answer
is unchanged. Topic-only lines (`guide.TOPIC_ONLY_LINES`) are allowed lines the model sees
only in such a topic message. Rule 1 names allowed_guidance and KNOWLEDGE as the sources;
whether models also use a line listed only in the topic message is not yet verified live.

### Change 4 - required lines (server)

For a model answer with at least one allowed line, the server adds the topic's required
lines the model left out and puts the answer in the topic's order (other lines after).
Required: one line per blocker (why blocked / what next); the values, "why" and "check" lines
and the offered action or Record correction line (a difference); the not-ready or
not-offered line and every still-needed item (readiness, approving); the first document
review sentence; up to 3 "this is for" lines (contacts). Then, among lines the RM has not
been shown yet, lines that are not required are dropped from the end until the answer has 6
lines, and required ones until it has 8. A line already shown while the answer streamed is
never removed. The limits apply only when lines are added: an answer with nothing missing is
returned as the model chose it (rule 16 asks the model for at most 6 lines), so it can be
longer, but every line is still an allowed line. When lines are added, the answer is put in
the topic's order, so an added line can appear above lines the RM has already read. Only
allowed lines are added, in the catalog's words, and `left_out` still counts only model lines
that were not allowed lines. The reply's `added_lines` gives the positions of the added lines
(never their text), so the evaluation harness (#115) scores only the model's own selection;
the metrics' `kept_lines` likewise counts the model lines kept, not the added ones. They differ
in when they look: `kept_lines` counts the model's lines before unseen lines are trimmed to
the 6/8 limits, while the harness scores the final answer, so a model line removed by that
trim is counted in `kept_lines` but never scored. A topic's required lines are the service's
choice: gold labels should not list them as `must_not`, because when the service adds one the
harness skips it (a required line the model chose itself is still scored, and any line at an
added position that is not an offered line is still counted). An
answer with no allowed line still gets the case-data answer.

### Change 5 - formatting-tolerant matching

A model line is compared in a normal form that removes formatting only: ASCII-only
lower-casing (look-alike letters such as the Kelvin sign never fold into Latin ones), runs of
spaces, curly quotes, Markdown emphasis and backticks, a leading list marker and a trailing
full stop. An unpaired `*` or `_` next to a word is removed too; that is harmless because
only the catalog's text is shown. A line of several allowed sentences is split; every part must be allowed or the
whole line is dropped. A bare action label stands for the catalog's `The current case offers
"<label>".` line (only when offered to this viewer); a knowledge sentence without its tag
stands for its tagged line (first by ranking). Lookups use one dictionary per request; work
per line is bounded by its length times the largest number of sentences in one allowed line.
The sentence checks are never applied to model text in place of matching.

### Why this keeps G6

The owner's rule is that nothing the model writes is shown unless it is an allowed line. After
this amendment the RM still sees only allowed lines, in the catalog's own words:

- explanation sentences and fixed lines are reviewed catalog text, offered only under their
  condition;
- templates are catalog wording filled from the backend projection; the model cannot change a
  value, owner or title in them;
- topic steering changes only what the model is asked to choose, not what may be shown;
- required lines are added by the server from the same allowed lines, never from model text;
- matching removes formatting, not words: an added, removed or changed word (including a
  look-alike letter) drops the line, and the catalog's text is what is shown.

### Alternatives considered

- Fuzzy or semantic matching: rejected; it would show text that is not an allowed line.
- Showing the model's own formatting: rejected; the catalog's text is what was reviewed.
- Explanations only in the no-model answer: the model could not use them.
- Answering every topic question without the model: possible later; it would make the model
  optional for these questions. Required lines keep the model's choice and remove the
  run-to-run gaps.

### Risks

- A general reason may not apply to a given case; the "can" wording and the "check" lines
  keep the RM checking the document.
- The values template shows untrusted document text, quoted; the filters above limit it, and
  the case-data answer already showed the same values.
- The cap can drop a model line the RM would have found useful; required lines are kept first.

## Amendment 3 - external-model architecture revisit: dormant external inference profile and budget guard (ACCEPTED for the dormant A2 scope, D-091)

Status: ACCEPTED by the repository owner on 2026-10-26 for the offline, dormant Phase A2
implementation only (proposed the same day). The acceptance is recorded with D-091 X1 to X9
in PR #116 (owner governance acceptance and its reaffirmation for the merged head; see D-091
in `DECISION_LOG.md`). It records how the revisit condition "any non-local embedding or model
endpoint" is handled for one dormant model endpoint and does not satisfy that condition for
activation. **The acceptance does not authorise external inference activation**: the remote
profile stays dormant until the Phase B decisions below and a reviewed change open its locks.
It does not accept Amendment 1 (D-084) or Amendment 2 (D-090). Amendment 2 (D-090) is PR
#114's, merged before this one.

Context. ADR-012 assumed a local model. Phase A2 adds code for one external inference profile
(OpenRouter, `openai/gpt-oss-120b`) that is dormant, plus a lifetime budget guard.

Decision. (1) The `ChatModel` port is unchanged; providers are selected from a code-defined
registry through one factory; business logic does not branch on providers. (2) The remote
profile would receive exactly the messages the local model receives; no data minimisation,
prompt, retrieval or catalog change is part of this amendment. (3) The remote profile cannot
run until a Phase B decision and a reviewed change open its locks. (4) Embeddings stay
loopback-only; warm-up never targets a remote URL. (5) Sections A and C are unchanged,
including the exact-line catalog. (6) No user model selection and no shared deployment.

Revisit before Phase B: data classification and disclosure scope (O1, O2/Q-013), the pinned
endpoint, its uniqueness and same-day ZDR evidence, serving-provider verification, budget
semantics, whether a broker is acceptable, evaluation acceptance thresholds. Revisit before any
production or team-wide use: hosted deployment, shared budget, key distribution, retention of
remote-run records.

Consequences. A new external trust boundary exists in code; a new local persistence owner (the
budget ledger, separate from the knowledge store); a new offline operator script; stricter
secret scanning. Rollback: remove the profile entry; the default profile has no ledger and no
new file.
