# Provisional Ownership and UBO Calculation Profile

## Status and scope

This profile is **PROJECT-DEFINED / PROVISIONAL / PENDING Q-004**. It supports an
ownership-only POC and is not a Delta Capita-approved UBO policy, legal controller
definition, KYC/compliance decision, GoldTier result, or Ready-for-Approval.

Control by other means, voting agreements, nominee/trust arrangements, management
control, sanctions, and AML risk are outside this profile.

## Party and relationship contract

| Concept | Rule | Status |
|---|---|---|
| Party | bounded ID/name; `LEGAL_ENTITY` or `NATURAL_PERSON` | Project source-neutral model |
| Legal-entity detail | optional registration number and country | Used where source supports it |
| Ownership edge | unique ID; owned parent -> owner child; percent/type/basis/provenance | Project orientation |
| Relationship type/basis | `OWNERSHIP` / `SHARE_OWNERSHIP` | Phase 04 profile |
| Percentage | Decimal, up to six source decimal places, `0 < value <= 100` | Integrity rule |

Zero, negative, non-finite, over-100, or clamped values are prohibited. Parent ownership
sums need not equal 100%; missing ownership is not inferred.

The owned `parent_party_id` of every Phase 04 ownership edge must be a `LEGAL_ENTITY`.
A `NATURAL_PERSON` cannot be an owned parent or intermediate in this orientation. That
shape is graph-semantic invalidity rather than a source-decoding rule: analysis
terminalizes safely with no definitive candidate, including when another branch is valid.

### Garden Business synthetic recursive demo exception

For the bounded `11111999A -> 111111111M` Marketplace Mock demo chain only, D-034
permits the connector to replace Garden Business's empty shareholder collection with a
local synthetic fixture and to retrieve the supplied SIM LIM shareholder collection.
Active `shareAllotted` counts, including different share classes, are treated as equal
economic units; withdrawn holders are excluded; each owner percentage is the active
share count divided by the active-count total, rounded to six decimal places. This is a
project-defined demonstration rule only, not an ACRA, legal, voting-rights, or
production UBO policy.

## Calculation and aggregation

For edges `p1 ... pn`, effective ownership percent is
`100 x (p1 / 100) x ... x (pn / 100)`. Python `Decimal` is authoritative; binary floats
are not used. Each path retains ordered edge evidence and a deterministic presentation.

Paths are unique by ordered relationship-ID sequence. `path_id` is the bounded stable
`path-v1-` SHA-256 digest of a length-delimited encoding of that ordered sequence; it is
not a concatenation of source IDs. Human-readable ordered edges remain separate. For each
natural person, direct ownership is the sum of one-edge paths, indirect ownership is the
sum of longer paths, and aggregated ownership is direct plus indirect. A path is counted
once. Legal entities are never final candidates.

## Provisional threshold and classifications

- Configuration: `UBO_OWNERSHIP_THRESHOLD_PERCENT`
- Default: `25%`
- Comparator: `aggregated ownership >= configured threshold`
- Value and inclusivity: **PROJECT-DEFINED / PROVISIONAL / PENDING Q-004**
- Precision: the same finite, six-decimal `(0, 100]` contract as source ownership
  percentages; invalid configuration fails before service operation

| Classification | Meaning |
|---|---|
| `PROVISIONAL_UBO_CANDIDATE` | Complete-enough ownership result meets the provisional threshold |
| `BELOW_PROVISIONAL_THRESHOLD` | Complete-enough result is below it |
| `REVIEW_REQUIRED` | A graph issue makes a retained result non-definitive |
| `INDETERMINATE` | Reserved for a result with no supportable threshold outcome |

Threshold results are `MET`, `NOT_MET`, or `INDETERMINATE`. None is approval.

## Graph validation, cycles, incompleteness, and limits

Hard failure covers missing/non-legal root, any natural-person parent/owned edge, root
registration mismatch, duplicate IDs, unknown endpoints, self edges, malformed
types/percentages, disconnected data, unsafe provenance/text, and party/relationship
count excess.

A reachable legal-entity leaf produces `INCOMPLETE_LEGAL_ENTITY`. A repeated party in an
active path produces `CYCLE_DETECTED`; the cyclic path cannot create a candidate. Depth
or path excess produces `MAXIMUM_DEPTH_EXCEEDED` or `PATH_LIMIT_EXCEEDED`, routing the
analysis to review without a definitive truncated result.

Project defaults are 100 parties, 200 relationships, depth 8, 64 paths per candidate,
and 256 total traversal expansions/emitted paths. They are security/performance controls,
not sponsor constraints.

## Provenance

Every internal edge retains provider, generic environment (`MOCK`, `LOCAL`, `SANDBOX`,
`LIVE`), a safe opaque source reference, and timezone-aware UTC sourcing time. The
reference is restricted to 1-128 ASCII letters, digits, dot, underscore, or hyphen and
rejects schemes, userinfo, queries, fragments, credential/token-like segments, controls,
whitespace, and raw body syntax. Relationship provenance must match provider metadata.

Provider-owned models and containers are recursively detached to primitive input and
freshly revalidated, including nested models. Trusted nested domain objects are frozen,
and retained records are defensive copies. Browser responses omit `source_reference` and
show only provider, environment, and sourcing time.

Credentials, auth headers, raw responses, private URLs, raw sponsor content, and
exception text are prohibited. Mock provenance proves only synthetic scenario origin.

## Repository finality and browser Decimal truth

Process-local repository writes are atomic create/expected-version compare-and-set
operations. A terminal `FAILED`, `ANALYZED`, or `REVIEW_REQUIRED` version rejects stale
writes; one duplicate concurrent load/analyze owns the transition and the other receives
a conflict. Terminal history cannot be erased or re-enter `ANALYZING`.

API Decimal values are strings. The frontend formats those strings without JavaScript
binary-number conversion or threshold-relevant rounding and never recomputes the backend
classification.

## Sponsor confirmation required

1. Q-002: hierarchy endpoint, schema, identifiers, pagination, and provenance.
2. Q-004: threshold(s), comparator, jurisdiction/policy variation, and legal tests.
3. Q-006: direct related-party minimums and atomic persistence.
4. Q-007: Singapore fields/value lists.

No Phase 04 Mock field or rule may become a real GoldTier assertion without confirmation.
