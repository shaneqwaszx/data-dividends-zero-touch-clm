# ADR-012 - AI Assistant knowledge loop: local knowledge store, assistant-ui panel, catalog plus approved knowledge lines

## Status

Proposed. Sections A and B are proposed for owner acceptance with PR #99. Section C
implements the owner's G6 direction (quoted in C) and is proposed pending an independent
architecture review; it must not be described as architecturally approved until then.

## Date

2026-10-21

## Context

PR #99 adds a knowledge loop to the separate AI Assistant service (`apps/assistant`):
reviewed official guidance and approved past resolutions are retrieved and cited in answers,
RMs can mark an answer as solved or not helpful, and Directors review drafts. The 2026-10-06
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
  taken out of review. Nobody who wrote a version in that chain may decide it, and every
  API decision or edit carries the content hash of the version the reviewer was shown.
  Every change runs in one SQLite write transaction taken before its checks (BEGIN
  IMMEDIATE) and moves a version on only while it is still pending, so concurrent decisions
  or edits have exactly one winner and the others get a clean 409. An entry may only
  replace an entry of the same kind. Retiring an approved entry, official guidance
  included, takes two reviewers: one asks, a different one confirms.
- Team scope: drafts from "Solved it" carry the author's team as visibility; Directors see,
  edit and decide only their own team's drafts and gaps, and their stats count only their
  team's entries and feedback; an edit can narrow team and role visibility but never widen
  it. HR guidance keeps the visibility HR sets.
- Drafts contain only the RM's own words (questions and note) and case context, redacted of
  the company, addresses and identifiers, and of the parties the case summary names in the
  shapes the redactor knows: objects with a `party_type`, entries of person lists such as
  `officers` and `shareholders` (registry officers carry no `party_type`), and person-name
  fields. Matching ignores letter case and whitespace between words. Names the case data does
  not contain, or spells differently, are not recognised. Browser-supplied "assistant" turns
  are not copied.
- ChromaDB product telemetry is disabled (`Settings(anonymized_telemetry=False)`) on every
  client. The embedding endpoint must be a literal loopback URL (the warm-up rule,
  `llm.is_local_model_url`); embedding requests ignore proxy environment variables and do
  not follow redirects.
- The assistant keeps reusing the CLM capabilities `POLICY_APPROVE` (review) and
  `POLICY_MUTATE` (propose guidance) as a POC mapping. This is `PROJECT_DEFINED_PROVISIONAL`
  and recorded for owner confirmation; it is not sponsor-approved reviewer authority.

### B. `@assistant-ui/react` 0.15.23 in the frontend panel

- Used only as chat presentation primitives with `useExternalStoreRuntime`: the panel
  component stays the owner of its message state; every request goes through the existing
  `aiAssistant.ts` client and `authenticatedFetch`; the panel stays keyed by
  `actor.user_id`. No cloud runtime, `assistant-cloud` client or remote adapter may be
  imported or configured.
- Version pinned exactly; upgrades are a reviewed dependency change. It adds 93 runtime npm
  packages (MIT/BSD-3-Clause/0BSD, no install scripts) and about 321 kB (95 kB gzip) to the
  bundle, several of them pre-1.0.

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
- Extension, knowledge lines: for each entry that retrieval returned for this user and case
  and that is approved and visible to them (checked again before use), each sentence of the
  approved body becomes the line `<sentence> [Gn]` or `[Pn]`, exactly as approved (a leading
  list marker is dropped and runs of spaces become one), and only if the sentence passes the
  sentence checks against this case's facts. The prompt lists these lines with the catalog
  and tells the model to copy lines exactly; source chips still come from the tags.
- Sentence checks, an additional safeguard on knowledge sentences only (never on model text),
  fail closed: non-printable characters (tabs, non-breaking or zero-width spaces); values,
  step counts, quoted labels, contacts and section names that are not in this case's facts;
  citation tags inside the body; actions this RM is not offered and authority claims, unless
  a fixed negation directly governs them (the cycle-2 rule, without the coordination
  exemption the third gate bypassed); Live claims; document values presented as confirmed.
  Text in a knowledge entry never vouches for its own values or labels.
- Streaming is main's line-based acceptance: only new text is split into lines, each
  complete line is looked up once and dropped from the buffer, an unfinished line is never
  shown, and model text is bounded at 64 KiB. After a stream failure only lines completed
  before it are kept, with the cut-short notice.
- Cost: model text is only split into lines and looked up in a set. On the third gate's 42
  probe shapes at 64 KiB the whole stream took at most 0.04 s in 1-byte feeds, and no single
  feed took 1 ms. The sentence checks run once per retrieved knowledge sentence per request;
  each match costs bounded work (a governing negation is searched within 80 characters, and
  phrase breaks and negation words are found once per clause). The slowest 64 KiB probe body
  took 0.18 s. Knowledge bodies from the API are limited to 4,000 characters.
- Residual risks:
  - Answer flexibility is reduced to selecting catalog and knowledge lines, so answers are
    less fluent and less specific than free prose; a question the lines do not cover gets
    the case-data answer.
  - Knowledge granularity: bodies are split at line breaks and after `.`, `!` or `?`
    followed by a space. An abbreviation such as "e.g." splits a sentence, a line can be
    shown without the sentence before it, and an entry whose sentences all fail adds nothing.
  - The sentence checks remain a deny-list over reviewed text. Phrasings they do not
    recognise would be offered if a reviewer approved them: context that reverses a negated
    action ("Previously you couldn't approve the case, but now you can.") and authority
    wording outside the patterns ("KYC is approved."). 17 of the third gate's 81 sentences
    are of this kind (`KNOWLEDGE_FILTER_LIMITS` in the tests); none of them is shown from
    model output. Maker-checker review of every knowledge version is the control.
  - Some genuine negations are over-dropped, including the R4 disclaimer, which stays
    available as a catalog line.
  - The illustrative marker of an entry is carried by its source chip (and, for the seed, by
    the entry's own first sentence), not by every line.
  - Guidance sentences that quote values or labels absent from the case (for example the
    0.85 policy default) are withheld.
- Until an independent architecture review accepts this section, the PR stays Draft.

## Alternatives considered

- Extend an existing CLM backend owner with knowledge tables: rejected; it would make the
  CLM persistence owner hold assistant data and add assistant writes to the case backend.
- No persistence (static guidance files only): keeps the read-only assistant, but loses the
  reviewed feedback loop the PR exists to add.
- Keep the plain React panel: viable; the library was chosen for chat primitives and
  streaming rendering, at the dependency cost recorded in B.
- Replace the catalog with sentence-level checks of model prose (the PR #99 author head and
  the first two remediation cycles): three independent gates found bypasses of that
  deny-list, and the owner's G6 direction keeps the catalog mandatory.
- The catalog alone, without knowledge lines: the strictest, but it cannot carry cited
  knowledge.

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
  bound to reviewed content; team-scoped review queue; loopback-only embeddings; telemetry off.

## Security and persistence implications

SQLite schema v3 adds `entries.revises` (nullable) and a `retire_requests` table; v1 and v2
stores are migrated in place on open. A reviewer who edited a pending version in place under
schema v2 has only an 'edit' review row on it; that row counts as editing, so they stay barred
from deciding it after the migration. No credentials are stored. Redaction is a first pass: names that appear nowhere in
the case data are not recognised, so Director review remains required before approval.

## Migration and retirement implications

Opening an older store migrates it (v1 -> v2 -> v3). Rolling back to the PR #99 author head
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
fails a check withheld; all three gates' negation sentences as model output (never shown,
whole or streamed) and as approved knowledge (withheld, apart from the listed limits); 64 KiB
stream shapes including whitespace runs and long tokens with a per-feed bound. Cross-team,
edit-then-approve, two-person retirement, concurrent decision/edit, officer redaction and
forged-turn regressions; restart/persistence and v2-to-v3 migration tests. Frontend Vitest,
typecheck and build; real-embedding retrieval evaluation with a local model (not yet run);
architecture and project-state checks; a fresh independent quality gate and an independent
architecture review of section C.

## Revisit conditions

Sponsor review authority (Q-014), any non-local embedding or model endpoint, cross-team
knowledge sharing, an `@assistant-ui/react` major upgrade, any further guardrail bypass, or a
proposal to show model text that is not an allowed line.

## Related contracts and sponsor questions

`docs/contracts/POLICY_AUTHORITY_MATRIX.md` (review authority, reviewer separation); Q-014;
D-073 in `DECISION_LOG.md`; the 2026-10-06 read-only AI Assistant entry in `ARCHITECTURE.md`.
