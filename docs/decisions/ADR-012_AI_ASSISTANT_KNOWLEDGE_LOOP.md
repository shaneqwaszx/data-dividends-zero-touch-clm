# ADR-012 - AI Assistant knowledge loop: local knowledge store, assistant-ui panel, catalog plus approved knowledge lines

## Status

Proposed, with section C accepted. Sections A and B are proposed for owner acceptance with
PR #99; section A's chromadb footprint is decided by D-075: the direct pin
(`chromadb==1.5.9`) is retained and its transitive packages stay unlocked. Section C keeps
the owner's G6 direction (quoted in C), and the owner explicitly accepted its extension of
the allow-list with approved knowledge lines on 2026-10-21 (D-074). Section A's feedback
flow is amended by D-076 (proposed): drafts no longer come from "Solved it" / "Yes, helpful";
a Director writes the fix for an enhancement request ("Not helpful" with a note). **D-076 also
relaxes D-074's two-person control for the POC (single-reviewer mode, below) and needs the
owner's (Shane's) explicit acceptance before merge.**

## Date

2026-10-21

## Context

PR #99 adds a knowledge loop to the separate AI Assistant service (`apps/assistant`):
reviewed official guidance and approved past resolutions are retrieved and cited in answers,
RMs can mark an answer as solved or not helpful, and Directors review drafts (since D-076,
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
- Feedback (D-076, proposed; it replaces drafting from "Solved it"): "Yes, helpful" only
  records the rating with the case context (blocker codes, fields, stages) and counts towards
  confidence by topic in the stats; it drafts nothing and changes no retrieval or ranking.
  "Not helpful" needs a non-blank note (422 otherwise) and is an enhancement request
  ("gap" in the code). Directors (`POLICY_APPROVE`) handle an open request end to end; HR
  does not (it has no case access). A Director either writes the fix, a past resolution or a
  guidance change (new guidance, or a new version of existing guidance, whose visibility it
  keeps unless the Director sets one), linked to the request and pending review like any
  other entry (publishing it marks the request resolved, rejecting it opens it again), or
  closes the request with a required reason. Both recheck the caller inside the write
  transaction like every other review change.
- Single-reviewer mode (D-076, proposed; **relaxes D-074's two-person control for the POC and
  needs the owner's (Shane's) explicit acceptance before merge**). Why: the synthetic users
  have one Director (olivia-koh) and only `POLICY_APPROVE` approves knowledge, so with
  author ≠ approver nothing a Director writes could be published. The setting
  `AI_ASSISTANT_KNOWLEDGE_SINGLE_REVIEWER` (default true for this POC) lets a reviewer approve
  or reject an entry they wrote or edited. Approving shows them the entry's final text and
  needs an explicit confirmation (`confirm_single_reviewer`; otherwise 403
  `CONFIRM_SINGLE_REVIEWER`); every such decision is recorded as single-reviewer in the
  review history and listed in the Review window. With the setting false the two-person rule
  applies unchanged. In both modes the decision stays bound to the content hash, the sentence
  checks and redaction stay as they are, and retiring an approved entry still takes two
  reviewers.
- Team scope: a draft from an enhancement request carries the team the request came from
  (before D-076, a "Solved it" draft carried its RM author's team). Directors, whom
  the CLM backend scopes globally (a Director has no team), see, edit and decide every
  team's drafts and enhancement requests, and their stats count every team; other actors
  keep the team rule and see only their own team's drafts, requests and stats. An edit can narrow team and role
  visibility but never widen it. HR guidance keeps the visibility HR sets.
- Redaction: an enhancement request's note is redacted when it is stored, and a Director's
  fix (since D-076) is redacted against the request's own case, loaded with the Director's
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
  team-scoped except for global Directors). D-076 (proposed, needs the owner's explicit
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
stores are migrated in place on open. Schema v4 (D-076) adds `reviews.single_reviewer` (0 for
every existing decision) and rebuilds the `feedback` table, in one transaction, to add a
`resolved` status and a nullable `close_reason`; every existing row keeps its values and has
no close reason. A reviewer who edited a pending version in place under
schema v2 has only an 'edit' review row on it; that row counts as editing, so they stay barred
from deciding it after the migration, and the version is left out of the RM author's own
view of the entry. No credentials are stored. Redaction is a first pass: names that appear nowhere in
the case data are not recognised, so Director review, with the final text shown before
publishing, remains required before approval.

## Migration and retirement implications

Opening an older store migrates it (v1 -> v2 -> v3 -> v4). Code from before v4 can still
open a v4 store (it names the feedback and review columns it writes), but it rewrites the
schema version to 3, enforces two-person review again, drafts from "Yes, helpful" again and
closes requests without a reason; the v4 code then leaves the already migrated tables as
they are. Rolling back to the PR #99 author head
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
D-076: helpful-only ratings, required notes, a Director's fix (past case, new or changed
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
single-reviewer mode, D-076), any non-local embedding or model endpoint, cross-team
knowledge sharing, an `@assistant-ui/react` major upgrade, any further guardrail bypass, or a
proposal to show model text that is not an allowed line.

## Related contracts and sponsor questions

`docs/contracts/POLICY_AUTHORITY_MATRIX.md` (review authority, reviewer separation); Q-014;
D-073 and D-074 in `DECISION_LOG.md`; the 2026-10-06 read-only AI Assistant entry in `ARCHITECTURE.md`.
