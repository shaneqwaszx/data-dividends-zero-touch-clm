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

Decision D-046 permits one bounded project fixture for `GARDEN BUSINESS` (`11111999A`)
and its corporate owner `SIM LIM PTE. LTD.` (`111111111M`). Within that fixture only,
strict positive Decimal `shareAllotted` counts are treated as equal synthetic economic
units, withdrawn holders are excluded, and relationship percentages are quantized to
six decimal places. Missing, binary-float, zero, negative, duplicate-identity, or
malformed fixture data fails closed.

Since D-076 the local Mock serves Garden and SIM LIM as two separate issuer records:
Garden's record names only SIM LIM (Corporate, 5000 units) and LIM CHOON HUAT (3000
units); SIM LIM's holders come only from SIM LIM's own record (see the recursive
discovery section below). The graph then follows the ordinary ownership contract. In
particular, the path
`11111999A -> 111111111M (62.500000%) -> S123AC1234E (81.818182%)` produces
`51.13636375%`, approximately `51.136364%` at six-decimal presentation. LIM CHOON HUAT
retains direct `37.500000%`; the two `9.090909%` SIM LIM holders each have effective
`5.681818125%`. The existing provisional inclusive 25% candidate rule remains the sole
classification rule. This fixture is not legal ownership, voting-rights, control, Live
ACRA, or production UBO authority; Q-004 and Q-012 remain open.

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
- Value and inclusivity: **SPONSOR-CONFIRMED bounded numeric POC rule, D-062**;
  broader legal/control/jurisdiction policy remains pending Q-004
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

## S2 document-assisted source decisions — merged PR #69

The existing Decimal engine remains the only calculator. Document extraction produces
PROPOSED observations with immutable document/version/page/reference, method/quality,
raw OCR and deterministic score, explicit owner/type/identifier/count/percentage/class,
owned entity and as-of date where supplied. No missing type, percentage or denominator
is invented. Counts compare with original scalar evidence; arbitrary holder sums are
never used as a denominator. Complete explicit percentages feed the existing graph.

Current discrepancies compare registry graph, original local supplement, documents and
existing manual graph. MATCH still requires a creator source decision for a proposal;
MISMATCH, NOT_COMPARABLE and AMBIGUOUS retain originals and block automatic progression.
Creator-only decisions require current access/session/team within the owning lock/CAS.
Unknown historical creators are read-only for these decisions. Optional reviewer note, actor/time,
case/document event versions, selected immutable observations, chosen source/graph and
replaced analysis/version are retained. CURRENT_EVIDENCE requires the exact current
graph, including supported partial parent totals without inventing missing percentages.
The exact-100 declaration rule applies to USER_SUPPLIED_DECLARATION and
DOCUMENT_OBSERVATIONS; it does not alter retained CURRENT_EVIDENCE.
DOCUMENT_OBSERVATIONS requires selected current rows to match every graph edge;
manual additions/corrections require USER_SUPPLIED_DECLARATION. These choices do not
establish automatic source precedence or legal verification.

ANALYZED evidence is editable before any retained target attempt/submission. Accepted
revisions preserve bounded prior analyses and receipts, recalculate paths, invalidate
readiness/confirmation and auto-resume to the next real blocker. A changed document
retires only proven obsolete dependency checkpoints. Submitted content is frozen.
The ownership tree is collapsed by default with a concise provisional-candidate summary;
keyboard expansion shows sources, direct/effective interests, each path/calculation and
unresolved branches. The frontend displays Decimal strings and cannot recalculate.

### Explicit official-Mock plus local Garden supplement

`ACRA_CONNECTOR_MODE=api_marketplace_mock` automatically composes the existing
bounded Garden supplement; no manual toggle is required. The existing coordinator
checks fresh compatible official/cache evidence or acquires it. Only successful known Garden
`11111999A` evidence permits the separately labelled LOCAL_SYNTHETIC_SUPPLEMENT/LOCAL.
Official entity/address/officers and empty/unsupported quantitative evidence remain
unchanged. Failure cannot select the fixture. Future nonempty official quantity is
retained and compared, not added to local percentages. Upload conflicts require review.

The unchanged current fixture has active Garden counts SIM LIM 5000 and LIM CHOON HUAT
3000: denominator 8000, direct 62.500000% and 37.500000%. SIM LIM active counts are
ABCD123 900, TAN WEI LING 100 and EFGH2345 100: denominator 1100, rounded edge percentages
81.818182%, 9.090909%, 9.090909%. Withdrawn FORMER OWNER 10000 is excluded only under
this explicit known synthetic fixture. ABCD123 effective interest is 51.13636375%; LIM
CHOON HUAT is 37.500000%. Both meet >=25%. TAN WEI LING and EFGH2345 each have
5.681818125%. This is local synthetic derivation, not official ACRA or legal ownership.

Reviewer notes may be omitted, null or blank (normalized to null). Supplied notes retain
the bounded safe-text/control-character/prompt-marker and length checks. Actor/time,
source selection, as-of date, document IDs/event versions, selected immutable
observations, graph and replacement bindings remain structured audit evidence.
Historical string rationale decodes without read-time rewriting or fabricated prose.
`GARDEN_SUPPLEMENT_ENABLED` is deprecated compatibility input; neither value disables
the accepted official-Mock Garden path. Its historical true/outside-official-lane
configuration rejection remains; internal isolated provider test seams remain explicit.

For that exact validated fixture graph, official OFFICERS role rows remain descriptive
registry evidence and do not create a second quantitative ownership requirement.
Other unresolved roles/interests, conflicts, unbound evidence and official quantities
retain the existing review/discrepancy checks; no general officer-to-owner rule changes.

A successful creator-owned graph replacement invalidates the earlier local target
review even when a classification revision followed that review. The existing
orchestration owner recomputes ownership/readiness before a new explicit send; it
cannot resume target dispatch while the ownership stage is incomplete.

## Separate ML-assisted advisory

### Phase 24 scalar evidence — merged PR #67

The merged Phase 24 implementation adds optional bounded scalar evidence, original
values, source operation, UEN, retrieval/as-of time, class/unit, determination basis,
confidence and evidence version. Share units are not percentages.
Unknown owned-entity bindings are retained as null; they never participate in arithmetic.
Nested percentages bind the actual owned parent entity, rather than the case root.
Repeated parties on different relationships retain distinct scalar references.
Only an explicitly authoritative positive denominator with matching
UEN/provider/environment/class/unit
and non-missing matching as-of semantics permits division in the existing Decimal
owner. Unknown activity status cannot be interpreted as active. Multiple/contradictory
interests, incompatible or incomplete denominators and non-representable six-decimal
ratios stay unquantified; shareholder rows never establish a denominator.

Explicit provider/reviewed direct percentages enter the same graph engine. Threshold
comparison remains case-frozen and inclusive; D-062 confirms only the bounded >=25%
default/comparator, superseding historical provisional descriptions of that default.
Candidate results remain provisional. Owner/partner/member/shareholder roles are
semantic evidence; officer/director labels establish neither ownership nor legal UBO.
Company, business/partnership, LLP, LP and unknown legal forms remain distinct.

`OWNERSHIP_DENOMINATOR_REQUIRED`, `OWNERSHIP_REQUIRED`, `UBO_REVIEW_REQUIRED` and
`OWNERSHIP_METHOD_UNSUPPORTED` explain current evidence deficits. Rule tags retain
evidence references, reasons, rule/case/evidence versions, confidence and provenance.
They use `DETERMINISTIC_RULES / ML_RUNTIME_NOT_AVAILABLE`; no trained-model metrics
are claimed. This tagger is separate from the existing advisory below. Schema v7
accepts these optional fields without rewriting historical records. Unknown prior
identity/correction bindings stay unknown. Registry rebind replacement retains prior
evidence/graphs/tags and validates the current parent identity/generation under Mongo
CAS; it cannot resurrect a deleted case or replay target operations.

Graph diagnostics and scalar evidence diagnostics are combined before candidate
classification. Mixed valid and unresolved evidence remains review required; affected
candidate percentages may be retained but their status is indeterminate. A later
return to the same UEN cannot resurrect independent evidence from before an intervening
different or unknown identity. A genuinely newer identity generation can replace that
retired analysis through the existing expected-version boundary.
This includes unresolved group, unknown, control, membership/economic-interest and
unmatched owner/partner/member/shareholder-role observations beside a quantified
graph. Unknown or withdrawn direct/share activity remains review required even when
a graph edge matches the retained scalar value. A director/officer role alone neither
adds ownership nor invalidates supported numeric evidence.

Service currentness and Mongo mutation guards share the ownership repository's
predicate under the existing lock/CAS boundary. Independent same-UEN evidence can
continue after a correction only without an intervening different/unknown identity;
registry-derived evidence remains generation-bound. Replacement uses the stricter
current parent generation and cannot revive a deleted case.

`ubo-advisory-linear-v1` is a separate case-bound review aid. It consumes each retained
deterministic `OwnershipCandidate`, preserves its authoritative Decimal percentage and
classification, and emits `LIKELY_UBO`, `REVIEW`, or `UNLIKELY_UBO` with the permanent
labels `ML_ASSISTED` and `NOT_LEGAL_UBO_DETERMINATION`. Indeterminate/review-required
ownership produces `REVIEW` without a guessed probability. The project-defined advisory
thresholds are editable and snapshotted for new cases, but do not change the graph,
provisional UBO rule, or Q-004 status. See `docs/models/UBO_ADVISORY_MODEL_CARD.md`.


Interrupted pre-submission registry rechecks recover before orchestration's waiting
return under the existing case lock and repository CAS. A known durable ownership
dependency `registry_evidence_generation` is compared with the authoritative case's
identity-correction count: older means obsolete even after bounded history pruning;
equal remains potentially current; future is an integrity anomaly and stays review.
No UEN-only currentness, guessed generation, larger history or second counter is used.

Legacy null generation uses only an exact retained registry analysis/prior reference
and the existing currentness predicate. Unknown or pruned legacy provenance stays
review. All newly raised registry-derived ownership/readiness dependencies bind to
proven current evidence, including current legacy analyses. Target/classification,
document and independent user decisions are outside this retirement category.
Recovery rebinds partial CLM projection from retained Search, preserves cancelled
history, and recomputes reconciliation/ownership/readiness without provider replay.
Submission freeze, authorization and stale-writer protections remain authoritative.

## Registry-driven recursive corporate discovery — D-076 candidate, 2026-10-23

`OwnershipDiscoveryCoordinator` (ADR-013) runs inside the ownership load, under the case
lock, only for registry-sourced graphs of cases whose frozen snapshot carries
`ownership_discovery`. Historical snapshots without it keep root-only semantics.

- **Trigger.** A legal-entity leaf (no disclosed owners in the current graph) with a
  verified Singapore UEN is acquired as its own issuer through
  `OnboardingService.acquire_subsidiary_registry_evidence()`: fresh compatible cache
  first (zero provider calls), configured provider on miss/stale, never a case rewrite.
  Names never link entities. Non-SG or unverified identifiers are never sent to ACRA.
- **Acceptance.** Requested/returned UEN, entity profile, MOCK environment, COMPLETE
  status and COMPANY legal form must agree; the issuer record must itself be a valid
  ownership graph. Officer roles stay descriptive; ownership-like roles keep review.
  NOT_FOUND, unsupported, partial, failed, invalid and cache failures are distinct
  unresolved outcomes, never success.
- **Identity.** Issuer nodes deduplicate by verified UEN (diamonds share one acquisition;
  a holder pointing back to an ancestor becomes the engine's `CYCLE_DETECTED`). Holders
  from an issuer record use `<issuer UEN>.<source id>` identifiers (hashed when unsafe or
  long), so source-local IDs never collide. Equal source person identifiers in different
  issuer records stay distinct and raise `PERSON_IDENTITY_UNRESOLVED`; only an explicit
  verified binding merges them, and no current provider supplies one.
- **Tracing.** A frontier issuer whose exact root-equivalent share is at least the frozen
  trace threshold is acquired first. Smaller branches are deferred only when a sound
  global bound proves no known or unknown person can cross the UBO threshold; the bound
  assumes each unresolved issuer's holders total at most 100% and is void on cycles,
  traversal limits, over-allocated resolved issuers or unresolved person identity.
  Otherwise deferred branches are expanded. A deferral is never a non-UBO finding.
- **Limits.** Corporate depth (root level 0) is case policy; deeper owners are
  `DEPTH_LIMIT`. The optional business budget counts provider-backed issuer
  acquisitions (cache hits do not count; uncertain busy/cache failures count
  conservatively). Fixed technical caps always apply: 32 issuer lookups, 60 s deadline,
  sequential acquisition, existing 100-party/200-relationship/256-evidence limits. The
  8-edge calculation depth and path limits are unchanged.
- **Status.** The audit records `graph_complete` and `classification_certainty`
  (`COMPLETE`, `BOUNDED_NO_THRESHOLD_CHANGE`, `UNCERTAIN`) with per-issuer outcome,
  depth, root-equivalent exposure and lookup counts. Any unresolved branch adds
  `CORPORATE_OWNERSHIP_UNRESOLVED` beside the engine's `INCOMPLETE_LEGAL_ENTITY`, so the
  existing rule keeps every candidate `REVIEW_REQUIRED`/`INDETERMINATE`; the graph never
  becomes ownership-ready while a branch is unresolved.
- **Currentness.** After acquisition the case is re-read; a changed identity or retained
  target result fails the load as `OWNERSHIP_SOURCE_STALE` with no derived analysis.

Garden through this path: Garden direct edges `111111111M` 62.500000% and LIM CHOON HUAT
37.500000%, then SIM LIM's own holders 81.818182/9.090909/9.090909% (withdrawn holder
excluded), giving ABCD123 `51.13636375%`, LIM CHOON HUAT `37.500000%` and two
`5.681818125%` holders — identical to the accepted D-046 result.

## Hybrid official-Mock plus local direct overlay — D-077 candidate, 2026-10-23

Opt-in only (`ACRA_MARKETPLACE_OWNERSHIP_OVERLAY=hybrid_direct_overlay`, official
Marketplace Mock lane). The default keeps the accepted flattened Garden supplement above.

- **Scope.** Only whitelisted scenarios in `connectors/hybrid_ownership_overlay.py`:
  `GARDEN_DIRECT_OVERLAY_V1` (owner-supplied Garden body, direct rows only; SIM LIM's
  own holders are never attached locally) and `FIVE_LAYER_MARKETPLACE_HYBRID_V1`. No
  calculator, service or router branches on these UENs.
- **Declared basis.** Each issuer declares active same-class units and a complete active
  denominator that must equal their sum; withdrawn rows never become edges; float,
  group/member, non-ordinary or unverified-UEN rows fail closed. The D-046 six-decimal
  rule derives each direct percentage. Original units are retained as
  `supplemental_evidence`, outside arithmetic.
- **Provenance.** Links are `LOCAL_SYNTHETIC_RELATIONSHIP` / `LOCAL`. Entity identity is
  official only when the official lookup returned the same-UEN profile.
- **Root.** Applied only to fresh, successful, same-UEN official Marketplace evidence.
  If the official root ever carries quantitative ownership, the declaration is retained
  beside it and the existing comparison requires review; it never replaces it.
- **Issuers.** The D-076 coordinator performs each corporate holder's cache-first official
  lookup. A definitive NOT_FOUND (identity `LOCAL_SYNTHETIC_IDENTITY`) or an official
  profile without shareholder rows (`OFFICIAL_MOCK_ENTITY_PROFILE`) attaches the
  scenario's declared holders as `LOCAL_SYNTHETIC_OVERLAY`. Failure, mismatch, another
  lane or official shareholder rows (`OFFICIAL_QUANTITY_PRECLUDES_OVERLAY`) leave the
  branch unresolved.
- **Review.** `SYNTHETIC_OWNERSHIP_EVIDENCE` is always raised, so analyses stay
  REVIEW_REQUIRED and candidates REVIEW_REQUIRED/INDETERMINATE. The discovery audit adds
  `topology_complete`, `official_identity_complete`, `quantitative_evidence_complete`
  (always false) and certainty `UNCERTAIN`. `synthetic_basis_threshold_result` is the
  same inclusive comparator on the declared basis: MET survives unresolved branches,
  NOT_MET needs complete topology or a sound bound; cycles, limits, person ambiguity or
  contradictions give INDETERMINATE. It is never a classification or readiness input.

Five-layer declared topology (fictional): `201511222D` -> `200811111M` 80% ->
`201688888A` 62.5% -> `200811111K` 60% / `199801111H` 40% -> `111111111K` 100% / 50%,
with persons ALEX TAN 20% (root), BEATRICE LIM 37.5% (L2), CHARLES ONG 50% (L4B),
DIANA KOH 62.5% and EDWARD NG 37.5% (L5). Exact path products: 20, 30, 10,
DIANA KOH 18.75 + 6.25 = 25 (inclusive MET on the synthetic basis), EDWARD NG
11.25 + 3.75 = 15. See `docs/demo/FIVE_LAYER_ACRA_HYBRID_DEMO.md`.
