# Phase 04 Related Parties, Ownership Graph and Deterministic UBO Foundation

## Status and truthful scope

Phase 04 adds an ownership-analysis sub-workflow beneath an existing onboarding case:

`case legal entity -> OwnershipProvider -> validated parties/relationships -> bounded
graph -> unique natural-person paths -> Decimal aggregation -> provisional ownership
threshold results -> deterministic evidence`

This is an **ownership-only foundation**. It does not implement the complete legal or
regulatory definition of a UBO/controller, control by other means, voting arrangements,
nominees, trusts, management control, compliance approval, GoldTier approval, or
Ready-for-Approval. Q-004 remains unresolved, so every threshold result is explicitly
project-defined and provisional.

## Components and trust boundaries

- `OwnershipProvider` accepts a provider-neutral case/root registration identity and
  returns parties and ownership relationships. Generic request, source, graph, service,
  domain, and API contracts contain no Mock scenario. Provider dictionaries, model
  instances, subclasses, and previously validated objects are all untrusted: the service
  recursively serializes them to primitive input and constructs fresh trusted models,
  revalidating every nested party, relationship, percentage, and provenance value.
- `MockOwnershipProvider` is credential-free, network-free, and deterministic. Scenario
  selection is confined to `MockOwnershipDemoControl` and the demo endpoint.
- `OwnershipAnalysisService` owns validation, limits, graph construction, traversal,
  aggregation, classification, events, and terminal failure handling.
- `InMemoryOwnershipAnalysisRepository` stores defensive copies keyed by case and uses
  atomic expected-version compare-and-set writes. It does not alter onboarding or
  document repositories.
- Browser models expose only parties, relationships, safe provenance, and calculation
  evidence needed by the UI. Audit events retain IDs, fixed codes/messages, and bounded
  counts—not graph names, percentages, payloads, or provider errors.

No Phase 04 component imports or calls GoldTier, PingFed, ACRA transport, document
processing, an LLM, or a third-party graph library.

Browser relationship provenance is deliberately minimized to provider, environment,
and sourcing time. The internal opaque source reference is not a browser field. Audit
events retain IDs, fixed codes/messages, and bounded counts rather than graph names,
percentages, payloads, or provider errors.

## Domain and graph design

`Party` supports `LEGAL_ENTITY` and `NATURAL_PERSON`, with bounded IDs/names and optional
registration/country details for legal entities. `OwnershipRelationship` is directed
from the owned party (`parent_party_id`) to its owner (`child_party_id`). Each edge has a
unique ID, Decimal percentage, `OWNERSHIP` type, `SHARE_OWNERSHIP` basis, and provenance.
Percentages permit at most six source decimal places and require
`0 < ownership_percent <= 100`; invalid values are rejected without clamping.

Every relationship's parent/owned party must be a `LEGAL_ENTITY`. A `NATURAL_PERSON`
cannot be an owned parent or intermediate node in this Phase 04 orientation. This is
validated at the graph/business boundary after source reconstruction and before path
calculation. Any such reachable edge makes the graph invalid, terminalizes the analysis
to safe `FAILED`, clears candidates, and prevents a mixed valid branch from retaining a
definitive classification. No reachable relationship is silently ignored.

The graph is a defensively copied adjacency mapping rooted at the onboarding legal
entity. Validation covers unique IDs, known endpoints, a legal-entity root, root
registration match, non-self edges, connectedness, provider/provenance consistency,
safe text, and configured counts. Ownership totals need not equal 100%, and missing
ownership is never inferred. The canonical ACRA entity is never mutated.

## Deterministic calculation

Traversal uses an explicit iterative stack with a per-path visited set. Each path's
effective percentage is `100 x product(edge_percent / 100)`. Thus
`40% x 75% = 30%`. Evidence retains ordered edge/party IDs and names, percentages,
direct/indirect status, effective ownership, and a deterministic calculation string.

Path uniqueness uses the ordered relationship-ID sequence, so each valid path aggregates
once. The retained `path_id` is a bounded deterministic SHA-256 identifier over a
length-delimited encoding of that sequence (`path-v1-...`); ordered relationship IDs
remain separately available in edge evidence. One-edge paths sum to direct ownership;
longer paths sum to indirect ownership; their sum is aggregated ownership. Legal entities
can only be intermediates, never final natural-person candidates.

Cycles are detected against the active path and excluded. A reachable legal-entity leaf
is incomplete. Depth/path-limit issues cannot silently truncate a definitive result:
the analysis becomes `REVIEW_REQUIRED`, and any retained person result is classified
`REVIEW_REQUIRED` with `INDETERMINATE` threshold status.

## Provisional threshold and graph limits

`UBO_OWNERSHIP_THRESHOLD_PERCENT` defaults to `25`. The comparator is
`aggregated ownership >= threshold`. Both the value and inclusive comparator are
**PROJECT-DEFINED / PROVISIONAL / PENDING Q-004**.

The setting uses the same finite Decimal contract as an ownership percentage: above zero,
at most 100, and at most six decimal places. Unsupported precision fails settings/service
composition before an ownership load rather than failing later in the workflow.

| Setting | Default | Treatment |
|---|---:|---|
| `OWNERSHIP_MAX_PARTIES` | 100 | Excess provider data fails safely |
| `OWNERSHIP_MAX_RELATIONSHIPS` | 200 | Excess provider data fails safely |
| `OWNERSHIP_MAX_DEPTH` | 8 | Review-required if exceeded |
| `OWNERSHIP_MAX_PATHS_PER_CANDIDATE` | 64 | Review-required; no definitive truncation |
| `OWNERSHIP_MAX_TOTAL_PATHS` | 256 | Bounds traversal expansions and emitted paths; review-required if exceeded |

These are conservative POC security/performance controls, not sponsor policy.

## Lifecycle, isolation, and terminalization

The lifecycle is `LOADING -> LOADED -> ANALYZING -> ANALYZED`, with
`REVIEW_REQUIRED` for reachable incomplete/cyclic/limit-affected data and `FAILED` for
malformed graphs or unexpected failures. `ANALYZED` means only that ownership
calculation completed.

After the initial record is stored, provider, source validation, graph construction,
graph validation, path calculation, aggregation, result construction, clock, and
recoverable repository-update failures are contained. Recovery starts from the last
defensive copy, clears partial results, records one fixed safe failure, and returns only
safe IDs/codes/messages. No tested failure remains stranded in `ANALYZING`.

Every repository write supplies the version read by the caller. Creation is atomic and
subsequent writes are compare-and-set transitions. `FAILED`, `ANALYZED`, and
`REVIEW_REQUIRED` are terminal and cannot be replaced by a stale success, failure, or
intermediate record. For duplicate concurrent load/analyze calls, exactly one request
owns the transition; the other receives a stable conflict and cannot erase the owner's
events or result.

The ownership record never changes the onboarding case/entity/history or Phase 03
document state. The sub-workflows fail independently.

## API and UI

- `POST /api/onboarding/cases/{case_id}/ownership/load`
- `POST /api/demo/onboarding/cases/{case_id}/ownership/load` (Mock control only)
- `POST /api/onboarding/cases/{case_id}/ownership/analyze`
- `GET /api/onboarding/cases/{case_id}/ownership`
- `GET /api/onboarding/cases/{case_id}/ubo-candidates`

The UI shows the root, direct/intermediate/natural-person owners, edge percentages,
minimized provenance, path factors, direct/indirect/aggregated totals, threshold,
classification, and review/failure warnings. JavaScript normalizes authoritative Decimal
strings lexically without conversion to binary `Number`, rounding, or classification
recomputation, so values such as `24.9999995%` remain exact beside a 25% threshold.

## Sponsor dependencies

- Q-002: authoritative seeded hierarchy retrieval endpoint/schema.
- Q-004: sponsor-approved UBO threshold/comparator and legal/controller rules.
- Q-006: direct related-party minimum/atomic-link semantics.
- Q-007: final Singapore mappings/value lists.

The provider boundary is replaceable later, but no live hierarchy, GoldTier write,
PingFed, real GoldTier, or Phase 05 work is implemented or verified.
