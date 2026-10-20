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
  An entry may only replace an entry of the same kind.
- Team scope: drafts from "Solved it" carry the author's team as visibility; Directors see,
  edit and decide only their own team's drafts and gaps; an edit can narrow team visibility
  but never widen it. HR guidance keeps the visibility HR sets.
- Drafts contain only the RM's own words (questions and note) and case context, redacted of
  the company, addresses, identifiers and every party named in the case summary. Browser-
  supplied "assistant" turns are not copied.
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
- Residual risks: a deny-list cannot enumerate every unsafe phrasing. The audit found a
  negation bypass, now corrected, which shows the class of risk; paraphrases outside the
  action and authority patterns may still pass; grounding treats values in retrieved
  knowledge as known.
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

SQLite schema v3 adds `entries.revises` (nullable); v1 and v2 stores are migrated in place
on open. No credentials are stored. Redaction is a first pass: names that appear nowhere in
the case data are not recognised, so Director review remains required before approval.

## Migration and retirement implications

Opening an older store migrates it (v1 -> v2 -> v3). Rolling back to the PR #99 head would
not read the `revises` column but would ignore it; edited versions would then look like
ordinary pending versions. The exact-line catalog is retired only if section C is accepted.

## Verification

Assistant pytest, ruff, format and mypy; the adversarial negation, cross-team,
edit-then-approve, redaction and forged-turn regressions; restart/persistence test; frontend
Vitest, typecheck and build; real-embedding retrieval evaluation with a local model (not
yet run); architecture and project-state checks; a fresh independent quality gate.

## Revisit conditions

Sponsor review authority (Q-014), any non-local embedding or model endpoint, cross-team
knowledge sharing, an `@assistant-ui/react` major upgrade, or any further guardrail bypass.

## Related contracts and sponsor questions

`docs/contracts/POLICY_AUTHORITY_MATRIX.md` (review authority, reviewer separation); Q-014;
D-073 in `DECISION_LOG.md`; the 2026-10-06 read-only AI Assistant entry in `ARCHITECTURE.md`.
