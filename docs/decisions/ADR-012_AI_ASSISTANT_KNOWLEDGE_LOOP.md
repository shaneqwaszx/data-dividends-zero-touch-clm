# ADR-012 - AI Assistant knowledge loop: local knowledge store, assistant-ui panel, sentence-level answer checks

## Status

Proposed. Sections A and B are proposed for owner acceptance with PR #99. Section C (the
replacement of the exact-line output catalog) is an **owner decision pending**: it is not
accepted by this ADR and must not be described as architecturally approved until the owner
records a decision.

## Date

2026-10-21

## Context

PR #99 adds a knowledge loop to the separate AI Assistant service (`apps/assistant`):
reviewed official guidance and approved past resolutions are retrieved and cited in answers,
RMs can mark an answer as solved or not helpful, and Directors review drafts. The 2026-10-06
architecture entry describes the assistant as read-only with no persistence owner; that is
still true towards the CLM backend (GET only) but no longer true for the assistant's own
data. The independent quality gate on `ad4661c` (FAIL) and its architecture review (REVISE)
require this ADR before the change can be accepted. Review authority remains
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

### C. Sentence-level answer checks replacing the exact-line output catalog (owner decision pending)

- Existing deterministic behavior (main, PR89 `8407d9e`): only answer lines that exactly match
  a catalog generated from the case facts are shown; anything else is withheld. Safety is by
  allow-list.
- New behavior (PR #99): the model's answer is split into sentences; each sentence is checked
  for grounding (values, labels, contacts, step counts, cited sources), policy (actions this RM
  is not offered, authority claims) and disclosures (Live claims, document values as fact).
  Failing sentences are removed and the RM is told how many. Safety is by deny-list.
- Retained guarantees: a sentence that fails a check is never shown, also while streaming;
  actions come only from the backend's offered actions, never from document text; Live and
  authority claims are removed; the 64 KiB model-text limit, cancellation and required
  terminal event are kept; checking is incremental (each sentence once).
- Negation handling is fail-closed: an action the RM is not offered, or an authority claim,
  is removed unless a fixed negating construction directly governs it (a negated modal or
  "never" before the action; "no", "not", a negated "is" or a negated denial verb before
  the claim) with no other negation earlier in that phrase. Two independent gates found
  negation bypasses (6 sentences on `ad4661c`, 15 more on `79621fe`); all of them are
  regression tests now. Some genuine negations are over-dropped.
- Checking cost is linear in the answer's length, also on long whitespace runs: every
  sentence's whitespace runs are collapsed before the checks, and the streaming guard looks
  at each piece of model text once.
- Residual risks: a deny-list cannot enumerate every unsafe phrasing. Paraphrases outside
  the action and authority patterns (for example an action described without its verb) may
  still pass; grounding treats values in retrieved knowledge as known. A third negation
  repair is not planned: further bypasses are an argument for the allow-list below.
- Recommended compatibility strategy: keep sentence-level checks for free-form explanation,
  and add an allow-list for operational instructions, so that any sentence that tells the RM
  to act must name an action the backend offers (the PR89 catalog principle applied to action
  sentences only); keep the adversarial regression suite as an acceptance gate.
- Until the owner decides, the PR stays Draft and this section is not accepted.

## Alternatives considered

- Extend an existing CLM backend owner with knowledge tables: rejected; it would make the
  CLM persistence owner hold assistant data and add assistant writes to the case backend.
- No persistence (static guidance files only): keeps the read-only assistant, but loses the
  reviewed feedback loop the PR exists to add.
- Keep the plain React panel: viable; the library was chosen for chat primitives and
  streaming rendering, at the dependency cost recorded in B.
- Keep the exact-line catalog: the safest model, but it cannot carry cited knowledge or
  explanation; see the compatibility strategy in C.

## Consequences

The assistant becomes stateful: its data directory needs backup if the knowledge is to be
kept, and the index can be rebuilt from SQLite (`reindex`). Review is stricter than the
original PR: an edited entry always needs a second reviewer. Retrieval needs a local
embedding model (Ollama); without it, index tasks wait and keyword search still works.

## Architecture invariants affected

- Preserved: CLM backend authority (assistant reads CLM data through GET only); backend-
  authoritative RBAC and team scope (the assistant asks `/api/auth/me` every time);
  no Live claims.
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
(development-only) store. The exact-line catalog is retired only if section C is accepted.

## Verification

Assistant pytest, ruff, format and mypy; the adversarial negation (both gates' sentences),
whitespace-run cost, cross-team, edit-then-approve, single-person retirement, concurrent
decision/edit, officer redaction and forged-turn regressions; restart/persistence and
v2-to-v3 migration tests; frontend
Vitest, typecheck and build; real-embedding retrieval evaluation with a local model (not
yet run); architecture and project-state checks; a fresh independent quality gate.

## Revisit conditions

Sponsor review authority (Q-014), any non-local embedding or model endpoint, cross-team
knowledge sharing, an `@assistant-ui/react` major upgrade, or any further guardrail bypass.

## Related contracts and sponsor questions

`docs/contracts/POLICY_AUTHORITY_MATRIX.md` (review authority, reviewer separation); Q-014;
D-073 in `DECISION_LOG.md`; the 2026-10-06 read-only AI Assistant entry in `ARCHITECTURE.md`.
