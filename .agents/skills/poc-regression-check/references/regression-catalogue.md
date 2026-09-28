# Accepted POC regression catalogue

This catalogue records the accepted Phase 01 mock scenarios preserved by the final
Phase 01 and Phase 02 quality gates, plus the separately scoped Phase 03 document
scenarios established by its planner and implementation. All identifiers and data are
synthetic.

## Phase 12 durability scenarios

| Durable scenario | Expected restored state | Required calls before restart | Additional calls from list/open after restart |
|---|---|---|---|
| Three current PDF/DOCX/TXT-equivalent structured documents, straight-through case | same `COMPLETED` case/evidence/target ledger | Registry `1/1/1/1`, IDP `3`, Ownership `1`, GoldTier `SEARCH/SHELL/POLICY/AMEND` once | Registry `0`, IDP `0`, Ownership `0`, GoldTier `0` |
| Intake not completed | same `PENDING_INPUTS` case and completed structured evidence | Registry once; IDP only for uploaded documents | all providers `0` |
| Current conflict | same `WAITING_FOR_REVIEW` case, discrepancy IDs/actions/decisions | Registry and accepted documents only | all providers `0` |
| Finalisation outcome retained | same `RECOVERY_PENDING`; explicit finalisation may continue | target operations represented by retained outcome | GoldTier `0` |
| Attempted target operation without retained outcome | controlled `RECOVERY_PENDING` | durable ordered intent/attempt marker | automatic GoldTier replay prohibited |
| Corrupt Mongo key/envelope identity | startup/read fails with controlled invalid-persistence error | none | no cross-case API projection, repair, deletion, or provider call |
| One or more interrupted current documents | each affected record is `FAILED / DOCUMENT_REUPLOAD_REQUIRED`; automation is `PENDING_INPUTS / DOCUMENT` | completed structured evidence and Registry acquisition retained | restart adds no provider calls; each targeted retry adds IDP `1` only and preserves same case/history |

Memory mode retains the historical process-local reset behavior. Mongo mode is a
single-instance durable POC, not a distributed exactly-once or Ready-for-Approval claim.

## Canonical mock scenarios

| Input | Accepted behavior | Terminal result | Required calls | Prohibited calls/claims |
|---|---|---|---|---|
| `202400001A` | Complete synthetic SME; required mock target stages succeed | `COMPLETED` | ACRA fetch; GoldTier search `NO_MATCH`; shell; policy; amend | No Ready-for-Approval or live-interoperability claim |
| `202400002B` | Registered address absent; human review before target processing | `REVIEW_REQUIRED` | ACRA fetch only | No GoldTier call; no completion |
| `202400003C` | Deterministic policy validation failure | `FAILED` | ACRA fetch; search `NO_MATCH`; shell; policy | No amend or completion |
| `202400004D` | Amend returns representative partial outcome | `REVIEW_REQUIRED` | ACRA fetch; search `NO_MATCH`; shell; policy; amend | No completion |
| `999999999Z` or another well-formed unknown synthetic UEN | Registry record not found | `FAILED` with safe `ACRA_ENTITY_NOT_FOUND` | ACRA fetch only | No GoldTier call; no completion |

Whitespace-only, over-length, or characters outside the bounded alphanumeric/hyphen
registration-identifier grammar are rejected before case creation. Padded lowercase
`202400001a` normalizes to the canonical happy-path UEN. Phase 09 supersedes the former
API-wide nine-digits-plus-letter restriction so recognised foreign identifiers can
reach the jurisdiction router without being treated as ACRA UENs. The old pattern now
serves only as explicit Singapore identifier-format evidence and remains a synthetic
demo rule, not a production ACRA contract claim.

## Phase 03 supplementary document scenarios

Each scenario starts beneath an existing onboarding case and uses a structurally valid
synthetic PDF request. It does not change the parent case or call ACRA/GoldTier.

| Mock IDP scenario | Document terminal result | Required document calls/events | Prohibited calls/claims |
|---|---|---|---|
| `ALL_FIELDS_MATCH` | `REVIEW_REQUIRED`, then `REVIEWED` only after four field decisions | Mock IDP once; four `MATCH` candidates; upload/start/process/review-required; field events; review-completed | No automatic approval, canonical overwrite, Ready-for-Approval, or GoldTier call |
| `FIELD_MISMATCH` | `REVIEW_REQUIRED`; legal name is `MISMATCH` | Mock IDP once; all original/canonical values retained for field review | High confidence cannot suppress explicit review |
| `LOW_CONFIDENCE` | `REVIEW_REQUIRED`; registered address confidence `0.54` | Mock IDP once; low-confidence field visibly reviewable | Confidence cannot approve a field/customer |
| `MISSING_FIELD` | `REVIEW_REQUIRED`; address is `MISSING_FROM_DOCUMENT` | Mock IDP once; nullable original retained; field must be rejected or corrected | Missing suggestion cannot be accepted or silently filled |
| `PROCESSOR_FAILURE` | `FAILED` with safe `IDP_PROCESSING_FAILED` | Mock IDP once; retrievable upload/start/processing-failed history | No field result/review/later event; no bytes/name/private exception in event/error |

## Phase 04 supplementary ownership scenarios

Each scenario starts beneath an existing onboarding case, loads once through the
dedicated Mock demo boundary, and then uses the generic analyze/read contract. Ownership
operations do not call ACRA, GoldTier, or IDP and do not change the parent case/document
state.

| Mock ownership scenario | Ownership terminal result | Required calculation/events | Prohibited calls/claims |
|---|---|---|---|
| `DIRECT_OWNER` | `ANALYZED`; Person A 60%, Person B 40%; both provisional candidates at default threshold | Load start/loaded; analysis start/completed; two direct paths | No legal/compliance/GoldTier approval claim |
| `INDIRECT_OWNER` | `ANALYZED`; Person C 30%, Person D 10% | `40% x 75% = 30%`; `40% x 25% = 10%`; exact evidence | No binary-float or AI calculation |
| `MULTIPLE_PATHS` | `ANALYZED`; Person A direct 20% + indirect 20% = 40% | Two unique paths aggregated once | No duplicate path counting |
| `BELOW_THRESHOLD` | `ANALYZED`; natural persons below 25% | Inclusive configurable provisional comparison | No false candidate |
| `INCOMPLETE_CHAIN` | `REVIEW_REQUIRED`; `INCOMPLETE_LEGAL_ENTITY` | Incomplete reachable legal-entity diagnostic | No inferred missing ownership or definitive result |
| `CYCLE` | `REVIEW_REQUIRED`; `CYCLE_DETECTED` | Bounded cycle detection; invalid path excluded | No recursion, infinite processing, or false candidate |
| `PROVIDER_FAILURE` | retrievable `FAILED / OWNERSHIP_PROVIDER_FAILED` | Load start/failure with safe IDs/code | No stranded `LOADING`/`ANALYZING`, raw provider error, or partial result |

## Phase 05 integrated CLM scenarios

Each scenario begins through the staged CLM path. GoldTier calls occur only after the
server revalidates current case-owned evidence and persists one minimized snapshot.

| Scenario | Terminal result | Required calls/evidence | Prohibited calls/claims |
|---|---|---|---|
| `HAPPY_END_TO_END` | `MOCK_GOLDTIER_SUBMITTED` | Valid registry; matching reviewed document; `ANALYZED` ownership; search `NO_MATCH`; shell; policy; amend | No real interoperability, related-party write, or approval claim |
| `DOCUMENT_BLOCKED` | `REVIEW_REQUIRED` | Registry and ownership ready; unresolved document blocker | Zero GoldTier calls |
| `DOCUMENT_SOURCE_CONFLICT` | `REVIEW_REQUIRED / SOURCE_CONFLICT_REQUIRES_POLICY` | Reviewed mismatch/rejection/correction conflict retained separately from canonical | Zero GoldTier calls; no canonical overwrite |
| `OWNERSHIP_BLOCKED` | `REVIEW_REQUIRED` | Reviewed document; cycle/incomplete ownership result | Zero GoldTier calls; no definitive UBO promotion |
| `MULTIPLE_BLOCKERS` | collecting/review with every applicable typed blocker | Incomplete document and ownership evidence | Zero GoldTier calls; no first-blocker-only response |
| `GOLDTIER_MATCH_FOUND` | `REVIEW_REQUIRED / GT_EXISTING_PARTY_REVIEW_REQUIRED` | Search only | No shell, policy, amend, or success |
| `GOLDTIER_SEARCH_FAILURE` | Collect independent evidence, then `TECHNICAL_FAILURE / safe Search category` | Search once; ACRA/document/reconciliation/ownership may continue | No no-match claim, reviewer substitution, retry, shell, policy, or amend |
| `GOLDTIER_SHELL_FAILURE` | `FAILED / GT_SHELL_FAILED` | Search, shell | No policy or amend |
| `GOLDTIER_POLICY_FAILURE` | `FAILED / GT_POLICY_VALIDATION_FAILED` | Search, shell, policy | No amend |
| `GOLDTIER_PARTIAL_AMEND` | `REVIEW_REQUIRED / GT_OPTIONAL_SECTION_REVIEW` | Search, shell, policy, amend | No Mock-submitted success |
| `DUPLICATE_SUBMIT` / `CONCURRENT_SUBMIT` | Existing terminal result returned | One accepted search/shell/policy/amend execution and one start event | No duplicate business write or erased terminal event |
| `STALE_READINESS` | Submission blocked by newly current evidence | Re-read case/document/ownership after an earlier ready evaluation | No submission from client/stale readiness |
| `CURRENT_CANONICAL_INVALID` | `REVIEW_REQUIRED / CANONICAL_DATA_INVALID` | Re-run shared minimum validation over the current entity | Zero GoldTier calls; historical `VALIDATED` state cannot authorize submission |
| `HISTORICAL_DOCUMENT_VS_CURRENT_CANONICAL` | `REVIEW_REQUIRED / SOURCE_CONFLICT_REQUIRES_POLICY` | Compare reviewed value with current canonical B while retaining Phase 03 captured canonical A | Zero GoldTier calls; no evidence rewrite |
| `SNAPSHOT_PAYLOAD_BINDING` | Actual target requests describe immutable snapshot A | Stable snapshot correlation/idempotency metadata and mapper input | Later live entity B cannot enter the requests |
| `POST_TARGET_FINALIZATION_RECOVERY` | Correct retained success/review/failure terminal result after retry | Safe execution receipt; same submission/correlation/idempotency identity; one business execution | No permanent `SUBMITTING`, duplicate target call, or private exception |
| `PRE_RECEIPT_OUTCOME_RECOVERY` | SUCCESS -> `MOCK_GOLDTIER_SUBMITTED`; MATCH_FOUND/PARTIAL_AMEND -> exact `REVIEW_REQUIRED`; POLICY_FAILURE -> exact `FAILED` after retry | Minimal safe target outcome recorded before injected receipt construction and result/error mapping failures; same submission/correlation/idempotency identity | No target replay, onboarding-`VALIDATED` dependency, permanent `SUBMITTING`, private sentinel, or outcome substitution |
| `CONCURRENT_FINALIZATION_RECOVERY` | Two retries after a pre-receipt fault converge on the same terminal result | One finalization owner under the case lock; one start, one receipt-recorded event, one terminal event | No repeated search/shell/policy/amend, stale overwrite, or repeated start event |
| `MALFORMED_TARGET_RESPONSE` | `FAILED / GT_MALFORMED_TARGET_RESPONSE` and retry returns that terminal result | Fresh validation immediately after the affected call; safe operation-prefix outcome retained; stable submission/correlation/idempotency identity | No later target call, unsafe returned value, permanent `IN_PROGRESS`/`SUBMITTING`, or replay |
| `SHELL_OVERSIZED_OR_CONTROL_ID` | Safe terminal failure after search/shell | 96-character safe ID accepted; 97-character, blank, whitespace, control, URL-like, or invalid-grammar ID rejected before policy | No unsafe party ID in policy/amend, ledger, receipt, record, API, event, or browser model |
| `POLICY_MALFORMED_RESPONSE` | Safe terminal failure after search/shell/policy | Invalid policy ID/status/error data discarded before amend | No amend or retry replay |
| `SEARCH_MALFORMED_RESPONSE` | Safe terminal failure after search | Invalid outcome/status/code/message discarded | No shell/policy/amend |
| `AMEND_MALFORMED_RESPONSE` | Safe terminal failure after the one amend attempt | Four-operation prefix retained without malformed amend data | No replay of any target operation |
| `TARGET_OUTCOME_CONSTRUCTION_FALLBACK` | Safe failed outcome finalizes on retry | Constant-only failure recorded when normal outcome construction or unexpected response validation raises | No private sentinel or permanent `IN_PROGRESS` |

An unexpected required-stage exception produces retrievable CLM `FAILED` with a fixed
safe code/message, preserves document/ownership records, stops later operations, and
cannot leave `SUBMITTING` stranded.

## Phase 06 zero-touch orchestration scenarios

These scenarios use the integrated zero-touch entry point. Phase 03's historical
`ALL_FIELDS_MATCH` scenario remains manual; `AUTO_CONFIRMED` applies only to this new
integrated policy path.

| Scenario | Terminal result | Required calls/evidence | Prohibited calls/claims |
|---|---|---|---|
| `STRAIGHT_THROUGH` | `COMPLETED / MOCK_GOLDTIER_SUBMITTED` | Registry, document `AUTO_CONFIRMED`, ownership, readiness, search/shell/policy/amend; zero human interventions | No manual stage clicks, live-system, approval, or exactly-once claim |
| `DOCUMENT_DISCREPANCY` | `WAITING_FOR_REVIEW / DOCUMENT_SOURCE_CONFLICT`; allowed registry retention auto-resumes to completion | Safe field evidence, version-bound `KEEP_REGISTRY_VALUE`, original extraction preserved, one intervention | No document-as-master overwrite or target call before resolution |
| `LOW_CONFIDENCE_DOCUMENT` | `WAITING_FOR_REVIEW / DOCUMENT_LOW_CONFIDENCE`; no action advertised | Configured threshold evidence | No registry-retention shortcut, target call, or invented reviewer policy |
| `MULTIPLE_DOCUMENT_BLOCKERS` | Source conflict resolves narrowly, then `DOCUMENT_LOW_CONFIDENCE` remains blocked | Both blocker codes retained; one conflict intervention | No single action clears unrelated blockers or permits a target call |
| `OWNERSHIP_EXCEPTION` | `WAITING_FOR_REVIEW / OWNERSHIP_CYCLE` | Bounded ownership diagnostic | No definitive UBO, resolution click, or target call |
| `OWNERSHIP_INCOMPLETE` | `WAITING_FOR_REVIEW / OWNERSHIP_INCOMPLETE` | Incomplete-chain diagnostic | No inferred evidence, resolution click, or target call |
| `EXISTING_PARTY` | `WAITING_FOR_REVIEW / EXISTING_PARTY_REVIEW_REQUIRED` | GoldTier search only | No shell/policy/amend or click-through |
| `TARGET_FAILURE` | `TECHNICAL_FAILURE / GT_POLICY_VALIDATION_FAILED` | Search/shell/policy and safe error | No amend, business-review substitution, or success |
| `TECHNICAL_FAILURE` | `TECHNICAL_FAILURE / IDP_PROCESSING_FAILED` | Safe provider failure retained and retrievable | No raw exception, business review, ownership, or target call |
| `DUPLICATE_OR_CONCURRENT_START_RESUME` | Same accepted checkpoint/terminal record | One logical stage/target execution | No repeated target operations or duplicated completion |
| `STALE_OR_CROSS_CASE_RESOLUTION` | `409`; case remains blocked | Versions plus server-recomputed authoritative fingerprint verified | No canonical-mutation, forged, cross-case, or stale advancement |
| `INVALID_INPUT_TRANSITION` | Invalid PDF retains `PENDING_INPUTS`; registry-review attach retains registry wait | No premature started event or progressing status | No externally visible false-running state |
| `UNEXPECTED_PROGRESS_FAULT` | `TECHNICAL_FAILURE / ZERO_TOUCH_UNEXPECTED_FAILURE` at the active stage | One fixed terminal event; private sentinel absent | No stranded running state, later call, raw exception, or replay |
| `FINALIZATION_RECOVERY` | Typed Phase 05 finalization re-entry reaches the correct Phase 06 outcome | Retained outcome/submission; target calls exactly once | No generic retry or target replay |
| `OWNERSHIP_BINDING_RESUME` | Resolution resumes with the original opaque ownership binding | Alternate cycle still raises its typed ownership exception | No provider object/scenario persistence or fallback adapter |
| `ALTERNATE_ADAPTER_FULL_PATH` | Local non-Mock-inheriting adapters reach `COMPLETED` | Strict SANDBOX DTOs, Decimal `30.0000`, exact target sequence | No interface-only conformance claim |
| `POLLING_TRANSIENT_RECOVERY` | Transient refresh error retries to terminal state | Bounded backoff, last confirmed state, retry warning | No silent polling death or false terminal UI |
| `NAVIGATION_GENERATION_GUARD` | Late previous-case response is discarded | Generation/case binding and resolution guard | No stale action or prior-case overwrite |
| `LOOP_GUARD` | `TECHNICAL_FAILURE / AUTOMATION_LOOP_GUARD` | Bounded transitions and safe terminal event | No infinite loop or downstream call after the limit |
| `MALFORMED_TARGET_RESPONSE` | `TECHNICAL_FAILURE / GT_MALFORMED_TARGET_RESPONSE` | Immediate strict response validation; accepted call prefix retained | No unsafe projection, later call, review substitution, or replay |
| `REVIEWED_DOCUMENT_SEMANTIC_CONFLICT` | `WAITING_FOR_REVIEW / DOCUMENT_SOURCE_CONFLICT` for an earlier, later, or multiple reviewed mismatch documents | Every case document re-evaluated against current canonical authority; all blocked documents retained in stable order | No `REVIEWED` shortcut, readiness inconsistency, evidence rewrite, or target call |
| `REVIEWED_CONFLICT_KEEP_REGISTRY` | Re-evaluation resumes only after explicit `KEEP_REGISTRY_VALUE` | Separate field-bound resolution; original extraction/review/captured canonical unchanged; one intervention | No document-master override or unrelated blocker clearance |
| `REVIEWED_LOW_CONFIDENCE` | `WAITING_FOR_REVIEW / DOCUMENT_LOW_CONFIDENCE` | Reviewed lifecycle retained but provisional confidence blocker remains | No advertised action, target call, or assumed sponsor policy |
| `REPEATED_FINALIZATION_RECOVERY` | `RECOVERY_PENDING`, then actual success/match/failure/partial outcome after fault removal | Stable Phase 05 submission/correlation/idempotency binding and exact target call prefix once | No loop-guard terminal, second submission, target replay, or outcome substitution |
| `REGISTRY_IDENTITY_AND_TRUST_BOUNDARY` | Wrong UEN -> `ACRA_RESPONSE_IDENTITY_MISMATCH`; malformed nested/blank/timestamp/provenance -> `ACRA_RESPONSE_INVALID` | Fresh primitive reconstruction, requested-UEN equality, query-free HTTPS provenance; safe SANDBOX and not-found preserved | No typed-instance trust, wrong-entity canonical mapping, token/query retention, business-review substitution, or target call |
| `REGISTRY_ORIGINAL_CONTROL_REJECTION` | Leading, trailing, or embedded Unicode-control source text -> `TECHNICAL_FAILURE / ACRA_RESPONSE_INVALID` | Original value inspected before trim across root/nested text and raw/typed-mutated/bypass paths; ordinary spaces still normalize | No canonical entity, document/ownership/readiness work, target call, or silent control stripping |
| `DOCUMENT_BLOCKER_INSERTION_ORDER` | Equivalent blockers remain in document journey insertion order | Repository-owned monotonic first-save sequence; 100 equal-timestamp journeys and 100 repeats of the former flaky case | No UUID/timestamp tie-break instability or changed blocker semantics |

Provider conformance additionally proves registry success/not-found/provenance; IDP
clean/low/missing/failure; ownership definitive/incomplete/cycle/failure; GoldTier
explicit no-match/existing-party outcomes; and one full alternate local adapter journey.

## Phase 09 jurisdiction gateway scenarios

These cases run before registry acquisition. Only a resolved Singapore decision may
invoke the existing ACRA adapter.

| Scenario | Terminal/checkpoint result | Required calls/evidence | Prohibited calls/claims |
|---|---|---|---|
| `COUNTRY_OMITTED_SG_UEN` | `RESOLVED / SG`, then existing `PENDING_INPUTS` Document checkpoint | One `IDENTIFIER_FORMAT -> SG` observation; ACRA once | No hidden default or loss of provenance |
| `EXPLICIT_SG_AGREES` | `RESOLVED / SG`, then existing Singapore flow | Ordered `USER_INPUT -> SG` and `IDENTIFIER_FORMAT -> SG`; ACRA once | No source suppression or precedence claim |
| `EXPLICIT_SG_INELIGIBLE_IDENTIFIER` | `WAITING_FOR_REVIEW / REGISTRY_IDENTIFIER_NOT_ELIGIBLE` at Registry | Resolved SG and selected ACRA route retained; no advertised action | Zero ACRA, IDP, ownership, or GoldTier calls; no false ACRA not-found claim |
| `EXPLICIT_FOREIGN_CONFLICTS_WITH_SG_UEN` | `WAITING_FOR_REVIEW / JURISDICTION_CONFLICT` at Registry | Both conflicting observations retained; no advertised action | Zero ACRA, IDP, ownership, or GoldTier calls; no selected provider |
| `RECOGNISED_FOREIGN_IDENTIFIER` | `WAITING_FOR_REVIEW / REGISTRY_PROVIDER_NOT_IMPLEMENTED` at Registry | Resolved AU/MY/HK observation and explicit unimplemented route | Zero ACRA, IDP, ownership, or GoldTier calls; no foreign integration claim |
| `UNKNOWN_JURISDICTION` | `WAITING_FOR_REVIEW / JURISDICTION_UNRESOLVED` at Registry | Empty observation set retained; case remains retrievable | Zero provider/downstream calls; no country guess |
| `REGISTRY_BLOCKER_DOCUMENT_ATTEMPT` | Existing registry-blocked record returned unchanged | No document record created | No IDP, ownership, readiness, or target progress |
| `ACRA_ADAPTER_COMPATIBILITY` | Existing canonical ACRA profile and safe errors unchanged | Strict DTO reconstruction, requested-UEN equality, canonical mapping/provenance | No raw/source DTO leak or weakened sandbox/mock behavior |

The optional frontend selector is bounded to Not specified, Singapore, Australia,
Malaysia, and Hong Kong. Foreign options explicitly say that their providers are not
implemented, and the backend remains authoritative.

## Phase 10 expanded registry-acquisition scenarios

These project-owned Mock operations supersede the Phase 09 monolithic ACRA call for an
eligible resolved Singapore case. They do not assert official ACRA endpoint behavior.

| Scenario | Terminal/checkpoint result | Required calls/evidence | Prohibited calls/claims |
|---|---|---|---|
| `REGISTRY_NORMAL_SME` (`202400001A`) | Complete acquisition then existing Document checkpoint | Entity profile/officers/ownership parties/relationships exactly once; two direct owners | No duplicate acquisition, live claim, or UBO calculation in the bundle |
| `REGISTRY_LEGAL_ENTITY_OWNER` (`202400007G`) | Complete acquisition | Legal shareholder and downstream persons normalize into existing graph | No new ownership engine or GoldTier hierarchy write |
| `REGISTRY_MULTIPLE_OWNERS` (`202400008H`) | Complete acquisition | Three exact Decimal share edges | No binary-float or inferred controller rule |
| `REGISTRY_MULTI_LEVEL` (`202400009I`) | Complete acquisition | Root-to-holding and holding-to-person edges | Existing path engine remains authoritative |
| `REGISTRY_EMPTY_OFFICERS` (`202400010J`) | Complete acquisition; Officers `EMPTY` | All four operations once; ownership evidence present | No false failure or fabricated officer |
| `REGISTRY_MISSING_OWNERSHIP` (`202400011K`) | `REVIEW_REQUIRED / REGISTRY_EXPECTED_DATA_MISSING` | Ownership/relationship operations validly empty; partial bundle retained | No ownership/IDP/GoldTier continuation or transport-success-as-complete claim |
| `REGISTRY_MALFORMED_LATER_STEP` (`202400012L`) | `FAILED / REGISTRY_OPERATION_MALFORMED_RESPONSE` | Valid first three operations; failed relationship status and safe provenance | No raw payload/validation detail, downstream call, or completion |
| `REGISTRY_LATER_PROVIDER_FAILURE` (`202400013M`) | `FAILED / REGISTRY_OPERATION_UNAVAILABLE` | Valid first three operations; safe relationship failure | No raw exception, downstream call, or review substitution |
| `REGISTRY_OWNERSHIP_ANALYSIS` | Existing `ANALYZED`; 60%/40% direct candidates | Registry bundle adapted through `OwnershipProvider` into existing Decimal service | No second threshold, aggregation, cycle, or UBO implementation |
| `REGISTRY_OWNERSHIP_CYCLE` (`202400006F`) | Existing ownership `REVIEW_REQUIRED / CYCLE_DETECTED` | Registry-fed cycle reaches existing graph detector | No definitive candidate or target call |
| `REGISTRY_GARDEN_SYNTHETIC` (`11111999A`) | Complete acquisition and ordinary Mock path; matching synthetic document reaches `COMPLETED / MOCK_GOLDTIER_SUBMITTED` | Empty officers; Garden direct `62.500000% / 37.500000%`; SIM LIM recursive `81.818182% / 9.090909% / 9.090909%`; existing Decimal engine derives the effective paths; target order remains search/shell/policy/amend | No network ACRA call, generic `shareAllotted` inference, legal/controller/Live claim, or target call before readiness |

For every Phase 09 Registry blocker, all four acquisition-operation counts remain zero,
as do IDP, ownership, and GoldTier counts. Browser summaries expose only normalized
records, opaque evidence references, provider/environment, UTC times, statuses, counts,
and fixed safe issues. They label the surface as a project-owned synthetic Mock contract.

## Official API Marketplace Mock runtime scenario

This separately authorized provider-Mock scenario does not replace any synthetic Mock
scenario and supplies no subscriber Sandbox, Production, or Live claim.

| Scenario | Terminal/checkpoint result | Required calls/evidence | Prohibited calls/claims |
|---|---|---|---|
| `REGISTRY_GARDEN_OFFICIAL_MARKETPLACE_MOCK` (`11111999A`) | `REVIEW_REQUIRED / REGISTRY_EXPECTED_DATA_MISSING`; partial acquisition retained | One cached Mock token per process run; strict entity basic and embedded-officer retrieval; Garden shareholder request returns explicit empty entities; relationships are explicit empty without a provider call; source environment `MOCK` | No synthetic ACRA fallback, generic sandbox call, Bearer header, ownership percentage/relationship fabrication, ownership analysis, GoldTier call, Sandbox/Production/Live claim, or false completion |

## Phase 16 synthetic Mock registry snapshot scenarios

These scenarios apply only when the backend explicitly enables the synthetic Mock cache
with the exact project-defined `7_776_000`-second duration. Disabled mode preserves the
Phase 09/10 retrieve-for-each-case behavior and adds no cache startup dependency.

| Scenario | Expected result | Required evidence/calls | Prohibited behavior/claims |
|---|---|---|---|
| Exact-key miss then fresh hit | Both cases retain the same complete original acquisition; first binding is `PROVIDER_FETCH`, second is `CACHE_HIT` | First case makes the four ordered Registry calls once; hit makes zero Registry calls; each case owns a defensive copy | No re-retrieval/re-verification claim, raw payload cache, or changed target order/count |
| One microsecond before/exact expiry | Before expiry is a hit; exact expiry is stale and refreshes | Lossless UTC microseconds in memory/Mongo; fixed elapsed-second arithmetic under the per-key lock | No calendar-month arithmetic, tolerance, rounding, or stale serving |
| Partial/failed refresh | Current case retains the existing sanitized partial/failed behavior with no binding; prior complete entry and old cases remain unchanged | Provider prefix stops at the failing operation; zero cache replacement and no downstream progression | No stale fallback, failed overwrite, or mutation/reassessment of an existing case |
| Invalid/corrupt cache or read/write/CAS failure | Safe cache-specific technical failure | Invalid/read stops before provider; failed write retains no acquisition/entity/binding on the new case; CAS has no retry loop | No corrupt-as-miss behavior, uncommitted binding, raw storage error, or silent memory fallback |
| Concurrent same/different keys | Same-key requests single-flight within one process; different keys proceed independently | Exact-key holder/waiter accounting and lock retirement after success/failure | No distributed exactly-once claim or permanent identifier lock growth |
| Memory/Mongo restart and deletion | Memory restarts miss; Mongo restarts hit; case deletion leaves the shared complete snapshot | Separate schema-v1 cache owner, strict CAS/key/schema validation, generated disposable physical database | No case-delete cascade, TTL, purge/history API, or production retention claim |

Exact cache identity includes provider, environment, acquisition-contract version,
synthetic dataset namespace, and normalized identifier. Adjacent identity is a miss;
a value returned for the requested digest with different decoded identity is corruption.
The cache remains backend-only and does not add a public API, frontend control, forced
refresh, sandbox/live caching, or production cross-team sharing authority.

## Phase 11 reconciliation/review/resume scenarios

| Scenario | Expected state | Required evidence/calls | Prohibited behavior/claims |
|---|---|---|---|
| Four fields match, including legal-name formatting only | `COMPLETED / MOCK_GOLDTIER_SUBMITTED` | Four `MATCH` results; Ownership once; search/shell/policy/amend once | No human decision, source-authority claim, or provider replay |
| One usable field disagreement | `WAITING_FOR_REVIEW / DOCUMENT_SOURCE_CONFLICT` | Registry and Document observations retained; Ownership/GoldTier zero | No automatic Registry/Document/confidence/newest winner |
| Missing, invalid, or low-confidence field | `WAITING_FOR_REVIEW` with distinct outcome | Exact `MISSING_IN_SOURCE`, `INVALID`, or `UNVERIFIABLE`; replacement remains available | No conflict collapse or unauthorized value-selection action |
| Multiple field discrepancies | `WAITING_FOR_REVIEW` until every current blocker resolves | Resolve one: Ownership/GoldTier zero; resolve final: resume once | No partial-resolution continuation or duplicate operation |
| Keep Registry | Existing canonical retained; then resume when all blockers clear | Both observations, discrepancy, decision, selected value/time retained | No Document/Registry evidence mutation |
| Use Document legal name | Canonical legal name updated; then resume when all blockers clear | Typed backend validation; Registry acquisition profile remains original | No arbitrary patch, structured-address parsing, route/identity replacement, or hidden Document precedence |
| Stale/unadvertised/cross-case decision | Safe 409/422-style rejection; still blocked | Case/discrepancy/automation-version/reconciliation-version/fingerprint binding | No canonical mutation, Ownership, or GoldTier call |
| Replacement document | Old discrepancy `CANCELLED`; matching current evidence resumes | IDP runs only for the explicit replacement; later stages once | No deletion of superseded evidence or replay of original Registry/IDP |

## Pre-Phase 12 workspace and multi-document scenarios

| Scenario | Expected state | Required evidence/calls | Prohibited behavior/claims |
|---|---|---|---|
| Process-local portfolio | Every created case remains listable newest-update first until backend restart | Lightweight safe projection; optional typed status filter; defensive repository copies | No provider call, workflow resume, raw evidence, Mongo/durability claim |
| Multiple review cases | Every authoritative `WAITING_FOR_REVIEW` case appears; resolving A leaves B unchanged | Backend status/exception count/stage/update time; exact selected-case load | No frontend-inferred authority, cross-case mutation, durable assignment claim |
| Three-document clear intake | `COMPLETED / MOCK_GOLDTIER_SUBMITTED` | Registry four operations once; PDF/DOCX/TXT each analysed once; Ownership once; search/shell/policy/amend once after intake completion | No Registry-per-document call, skipped file, early Ownership/target call, or live/approval claim |
| Missing in one, usable in another | Field remains usable and may `MATCH` Registry | Both document observations and provenance retained | No false `MISSING_IN_SOURCE` from the partial document |
| Conflicting documents | `WAITING_FOR_REVIEW` at Document | Every distinct current value visible; Ownership/GoldTier zero | No first/last/confidence/recency/source winner |
| Ambiguous legal-name documents | Conflict with Registry; only Registry-retention may be offered | Multiple Document candidates retained | No arbitrary `USE_DOCUMENT_VALUE` |
| Duplicate legal-name candidate | One unique normalized Document candidate may be explicitly selected | All source documents retained as provenance | No duplicated action or hidden document precedence |
| Incomplete upload set | Case remains `PENDING_INPUTS`; successful documents remain attached | Explicit expected-count mismatch or failed upload; same-case retry | No automatic start, replacement case, or silent partial-set processing |
| Replace B in A+B | A current, B superseded, B2 current; reconciliation rebuilt | B2 IDP once; Registry count unchanged; stale decision context rejected | No deletion of B history, A replacement, or Registry reacquisition |
| Hostile media masquerade/path | Case remains `PENDING_INPUTS`; controlled `DOCUMENT_STRUCTURE_INVALID` | Strict PDF parse; DOCX rooted/UNC/drive/traversal/backslash member rejection; IDP/Ownership/GoldTier zero | No marker-only PDF delegation, archive-path echo, provider `503`, or downstream call |

## Accepted cross-scenario invariants

- GoldTier search `NO_MATCH` alone permits shell creation. `MATCH_FOUND` stops at
  `REVIEW_REQUIRED`; modeled search `FAILURE` retains its safe category, permits only
  independent case-evidence collection, and then stops at `TECHNICAL_FAILURE` at
  `GOLDTIER_SEARCH`. Neither match nor failure creates a shell.
- Unexpected failures during ACRA fetch/mapping or GoldTier search/shell/policy/amend
  persist one sanitized terminal `FAILED` event and stop before every later operation.
- Malformed required ACRA source data ends as retrievable `FAILED` with a stable safe
  code and zero GoldTier calls. Canonically incomplete required data cannot reach
  GoldTier and routes to review under the accepted rule.
- A partial required stage cannot produce `COMPLETED`. Terminal state is the final event.
- Multiple cases retain independent identifiers, timestamps, histories, results, and
  connector behavior.
- Default Mock ACRA and Mock GoldTier remain credential-free and network-free. The
  sandbox-shaped entity-profile seam remains labeled `ACRA/SANDBOX`, but undocumented
  Phase 10 expanded sandbox operations fail closed pending Q-012; neither outcome is
  evidence of a live call.
- Browser responses minimize internal provenance; UI/API labeling remains simulated
  where any connector is mocked.
- `COMPLETED` means only completion of the currently accepted required mock stages. The
  sponsor-defined Ready-for-Approval transition remains unresolved.
- Current canonical minimum validity is recalculated during every Phase 05 readiness
  evaluation and immediately before snapshot creation. Document review is compared with
  current canonical values without changing original/captured Phase 03 evidence.
- The frozen Phase 05 target input is the only canonical business source used by target
  mappers. A minimal safe target outcome is retained at the terminal target boundary
  before rich receipt/result/error mapping. That outcome and its later receipt permit
  construction/mapping/clock/event/save/CAS recovery without repeating search, shell,
  policy, or amend. This is process-local Mock idempotency, not production exactly-once.
- Every target response crosses fresh primitive-to-strict-model validation immediately
  after its connector call. Unsafe identifiers/statuses/codes/messages stop all later
  calls and converge on a constant sanitized target outcome. The execution owner cannot
  leave `IN_PROGRESS` after an attempted operation unless the process is forcibly
  terminated.
- Document input rejected for type, name, size, or narrow structure stops before Mock
  IDP; connector/output failures terminalize a retrievable document without changing
  the parent onboarding case.
- Every recoverable failure after upload acceptance, including invalid canonical
  comparison input, comparison/model construction, clock usage, and document update,
  produces exactly one sanitized terminal failure event and no stranded `PROCESSING`
  document.
- Provider name and source reference are trimmed, bounded, nonempty, control-free, and
  provider-neutral. Malformed provenance terminalizes safely without retaining the
  unsafe value.
- The generic IDP input/provider/service/domain/API contracts contain no Mock scenario.
  A non-Mock provider can produce identical comparison and review behavior.
- Streaming size enforcement checks a chunk against remaining capacity before append;
  single-chunk and cumulative overflow stop before provider invocation.
- Review API field and decision values use the domain enums, reject unknown properties,
  and bound correction/note text. UEN comparison alone removes internal whitespace and
  normalizes case.
- Uploaded bytes are transient and absent from repositories, events, API responses,
  and browser models. A validated display name may be retained and returned, but is
  never used as a path or copied into events/errors.
- Document ownership is enforced by parent case ID; IDs, UTC timestamps, event order,
  and final review decisions remain isolated and coherent.
- Mock IDP output is explicitly synthetic and never represented as OCR derived from the
  uploaded file. Every provisional field requires an explicit local decision;
  `REVIEWED` is not customer/compliance approval.
- Ownership provider input/result, graph, service, domain, and generic API contain no
  Mock scenario. Mock selection exists only at the dedicated demo/provider boundary.
- Ownership percentages and direct/indirect/aggregate/path calculations use Decimal;
  the server-authored evidence is authoritative and each relationship path is counted
  once.
- Every ownership edge follows owned legal-entity parent -> owner child orientation.
  A reachable natural-person parent edge, including a mixed valid/malformed graph,
  terminalizes without a definitive candidate and is never silently ignored.
- Provider dictionaries, model instances, subclasses, and nested previously validated
  values cross a fresh primitive-to-trusted-model reconstruction boundary. Internal
  source references use an opaque grammar and never reach the ownership browser DTO.
- Repository writes use atomic expected versions. Exactly one simultaneous load/analyze
  owns its transition; stale success/failure/intermediate writes cannot replace terminal
  `FAILED`, `ANALYZED`, or `REVIEW_REQUIRED` or erase its final event.
- Path uniqueness remains the ordered relationship-ID sequence while the retained path
  ID is a bounded deterministic digest. Maximum valid ID/depth compositions do not fail
  result construction.
- Threshold configuration uses the same finite six-decimal `(0, 100]` contract as edge
  percentages and fails before service use if invalid. The browser renders authoritative
  Decimal strings exactly without JavaScript numeric rounding or reclassification.
- The 25% inclusive threshold and graph limits are configurable project defaults pending
  Q-004; `ANALYZED` and `PROVISIONAL_UBO_CANDIDATE` make no legal/controller, compliance,
  GoldTier, or Ready-for-Approval claim.
- Cycles, incomplete legal-entity terminals, and depth/path limits cannot create a false
  definitive candidate. Malformed or over-size provider graphs fail safely.
- Every recoverable post-acceptance ownership failure through graph construction,
  validation, traversal, aggregation, result construction, clock, and repository update
  terminalizes as retrievable sanitized `FAILED` with no partial candidates or stranded
  `ANALYZING` state.
- Ownership analysis remains isolated per case and cannot mutate the onboarding entity,
  case history/state, document records, or call ACRA/GoldTier/IDP.
- Phase 06 stage order and status are server-authored. The browser polls only `RUNNING`
  or `RESUMING`, renders only server-advertised exception actions, and keeps all manual
  scenario actions beneath disabled-by-default Demo/Test Controls.
- Zero-touch resolution is case-, exception-, automation-version-, and evidence-version-
  bound plus a server-recomputed current-authority fingerprint. Accepted resolution
  auto-resumes; duplicate start/resume and terminal reads do
  not replay Phase 05 target operations.
- Business exceptions never become technical failures, and technical/provider/target
  failures never become reviewer work or `COMPLETED`. All automation persistence and
  replay protection remain process-local POC guarantees.
- Every ACRA result, including a previously typed or bypass-mutated instance, crosses a
  fresh strict primitive reconstruction boundary. Returned and requested normalized UENs
  must match; retained endpoint provenance is query-free HTTPS. Invalid provider data is
  technical and cannot be converted to canonical-review work.
- Original ACRA text is checked for prohibited Unicode control categories before any
  whitespace normalization. Document enumeration is stable first-save insertion order;
  random UUIDs never determine same-stage blocker presentation.
- Phase 07 presenter presets remain confined to the demo provider/control boundary.
  The generic registry, document, ownership, orchestration, and target contracts stay
  scenario-free, and every sponsor-facing view remains explicitly labelled with the
  active connector profile.
- `MULTIPLE_DOCUMENT_BLOCKERS` stops before ownership and GoldTier, while
  `OWNERSHIP_CYCLE` stops before GoldTier. `MULTIPLE_OWNERSHIP_PATHS` produces one
  aggregate candidate with distinct deterministic path evidence, and `PARTIAL_AMEND`
  preserves the accepted search/shell/policy/amend call order.
- `RECOVERY` injects a demo-only receipt-finalization interruption after the retained
  target outcome. The case reaches `RECOVERY_PENDING`; one explicit resume completes
  it without replaying any target operation.
- UAT evidence export is demo-gated and case-bound. Its strict whitelist contains only
  sanitized identifiers, statuses, blockers, timings, operation names, outcome markers,
  profile labels, and safe timeline entries; it never exports document bytes, source or
  target payloads, credentials, endpoint provenance, or internal authority fingerprints.
- Process restart is the documented POC reset. It clears process-local cases, bindings,
  target ledgers, and injected recovery counters without presenting a production reset,
  persistence, or exactly-once guarantee.
- Phase 07 demo lifecycle success is server/process observable: start returns success
  only after owned backend/frontend listeners and health are verified; stop validates
  a structurally complete `RUNNING` role set (exactly one backend and one frontend), then
  validates PID, creation time, executable, fixed project command markers, and descendant
  listener before terminating the exact tree. Missing, duplicate, or unknown running
  roles fail nonzero before termination, retain metadata, and abort reset without a new
  session. Reset starts only after verified stop and makes a prior process-local case
  unavailable. Unrelated processes and occupied-port owners are never selected; fully
  nonexistent complete metadata may clear only when both required ports are free, while
  incomplete or PID-mismatched metadata fails safe.
- Sponsor blocker presentation follows the complete ordered server-provided
  `blocker_codes`. UAT-04 explicitly shows source conflict plus low confidence before
  narrow resolution and only low confidence afterward, with no target call or
  unsupported action.
- Reconciliation retains Registry, Document/IDP, and genuinely available request
  observations separately. A disagreement cannot become `MATCH`, select a winner, or
  reach Ownership/GoldTier until a backend-authorized explicit decision is recorded.
- Phase 11 remediation derives field/discrepancy outcomes and actions intrinsically,
  permits at most one current discrepancy per field/evidence set, and rejects forged
  `MATCH`/`MATCHED` aggregates at construction, repository save/retrieval, and current-
  clearance checks. A low-confidence conflicting value is one actionless
  `UNVERIFIABLE` blocker; independent blockers in different fields remain separate.
- Legal-name canonical selection and its reconciliation decision use one shared-lock
  process-local commit with snapshot restoration before lock release on first-write,
  second-write, or post-write failure. Same-context duplicates remain idempotent;
  historical decisions become stale after current evidence changes.
- `USE_DOCUMENT_VALUE` is advertised only for one unambiguous legal-name observation;
  registration identity, country routing, and structured address remain protected from
  unsafe flat-value replacement. Missing, invalid, and unverifiable evidence requires
  replacement.
- One resolved discrepancy among several leaves `WAITING_FOR_REVIEW`. The final valid
  resolution passes through `RESUMING`; unchanged reads do not rerun Registry/IDP, and
  repeated resolution/resume does not duplicate Ownership or Mock GoldTier operations.
- Reconciliation browser output contains normalized bounded values and safe provenance,
  never raw PDF text, raw ACRA payload, provider URL, internal exception, credential,
  private authority digest, or invented reviewer identity. All decisions and replay
  guarantees remain process-local.
- Jurisdiction observations are retained independently of their source. Agreement may
  resolve, but disagreement never chooses a winner without sponsor-confirmed authority.
  Omitted input infers Singapore only when the identifier matches the accepted synthetic
  SG UEN format, and the inference remains visible.
- Unresolved jurisdiction, jurisdiction conflict, and recognised-but-unimplemented
  registry routes stop at Registry with no ACRA, document/IDP, ownership, readiness, or
  GoldTier activity. Their cases and safe evidence remain retrievable and cannot falsely
  complete.
- Once Singapore/ACRA is selected, the registration identifier must satisfy the shared
  accepted Singapore UEN predicate before the connector is invoked. Ineligible
  identifiers stop as `REGISTRY_IDENTIFIER_NOT_ELIGIBLE` with zero ACRA/downstream
  calls and never become a false `ACRA_ENTITY_NOT_FOUND` outcome.
- Registry routing is a backend-owned closed table. User input cannot select an
  endpoint, module, class, credential, or foreign connector. AU/MY/HK recognition is not
  an implementation claim.
- Every `/api` operation except login is authenticated from a process-local opaque
  server session. Unsafe methods additionally require the session-bound CSRF value;
  invalid, expired, revoked, missing, or rotated sessions cannot retain browser access.
- Team A/DBS and Team B/OCBC cases are authorized only from immutable canonical
  `team_id`. Every case-scoped route family returns the same fixed 404 for a cross-team
  ID and an absent ID. Director sees both teams and legacy unassigned cases; team users
  do not enumerate legacy records.
- Team-scoped creation is server-assigned and rejects supplied team claims. Director
  creation requires an explicit fixed team. Headers, query values, and browser state
  cannot spoof user, role, or team authority.
- Priority is null or a strict integer 1–10, changes only case/audit metadata, and leaves
  automation workflow state/timestamp and all provider call sequences unchanged. Lists
  are access-filtered first, then order non-null priority descending before the accepted
  automation timestamp and case-ID tie-break.
- Mongo schema-v2 preserves team/priority through restart without provider replay. Exact
  schema-v1 reads become null/null only in memory and are not rewritten; invalid or
  unknown persistence and team changes fail closed.

## Catalogue evolution record

| Established by | Change |
|---|---|
| Official ACRA API Marketplace Mock runtime integration | Preserved every synthetic Mock scenario and added an explicit opt-in official Mock retrieval scenario whose empty Garden shareholder evidence stops at `REVIEW_REQUIRED / REGISTRY_EXPECTED_DATA_MISSING` without fallback, derived percentage, ownership analysis, target call, or Live claim |
| Pre-Phase 22 ACRA teammate reconciliation | Preserved Phase 09/10 routing, acquisition, ownership, and target call stopping; added the bounded `11111999A` Garden synthetic fixture at the Mock provider boundary, expanded the project UEN syntax predicate to the three assigned ACRA-style forms, and kept BizFile Dormant with OAuth/raw-debug/runtime activation absent |
| Phase 13 implementation | Preserved all Registry→Document→Reconciliation→Ownership→Readiness→Mock GoldTier scenarios and call stopping; added authenticated session/CSRF enforcement, exhaustive non-enumerating team access, immutable team creation, strict nullable priority/backend ordering, schema-v1 compatibility, schema-v2 adapter parity, and a genuine-Mongo restart scenario in CI |
| Phase 12 quality-gate remediation | Preserved the accepted architecture and prior phases; added canonical Mongo key/envelope identity validation, coordinated interrupted-document input recovery, bounded targeted same-case retry, and genuine-Mongo adverse restart/CAS/atomicity coverage |
| Phase 12 implementation | Preserved Phase 09–11 and Pre-Phase 12 behavior; added explicit memory/Mongo durability, schema/CAS validation, restart reconstruction, read-only no-provider-replay, and uncertain-target recovery scenarios |
| Pre-Phase 12 quality-gate remediation | Preserved all workspace/multi-document behavior; strengthened pre-IDP PDF structural recognition and DOCX archive-member namespace validation, and added accepted selected-byte visibility without moving authority to the browser |
| Pre-Phase 12 workspace/multi-document refinement | Preserved Phase 09–11 rules; added backend-authored process-local history/review queue, read-only listing, explicit bounded PDF/DOCX/TXT intake completion, per-document provenance, full-current-document aggregation, missing-with-usable semantics, ambiguous-document no-winner behavior, same-case retry, and isolated replacement |
| Phase 11 quality-gate remediation | Preserved Phase 11 source-neutral behavior and Phase 09/10 call stopping; added coordinated canonical/decision atomicity, intrinsic outcome/action/status invariants, one current discrepancy per field/evidence, current-context duplicate checks, and actionless low-confidence disagreement |
| Phase 11 implementation | Preserved Phase 09/10 and all earlier POC invariants; added four-field source-neutral observations, five deterministic outcomes, first-class discrepancies, bounded explicit decisions, evidence-preserving canonical legal-name application, multi-discrepancy call stopping, replacement re-evaluation, and idempotent process-local resume |
| Phase 10 implementation | Preserved Phase 09 routing/identifier blockers and all prior POC invariants; decomposed the eligible Singapore Mock acquisition into four bounded operations, added truthful empty/partial/failure states and browser summaries, and fed registry ownership evidence through the existing deterministic Decimal ownership service |
| Phase 09 remediation | Added the shared provider-specific Singapore UEN eligibility guard, explicit invalid-SG call-stopping scenario, and self-validating resolution/routing state invariants while preserving generic foreign intake and no-precedence behavior |
| Phase 09 implementation | Preserved every accepted Singapore/ACRA and Phase 01–08 invariant; added source-aware agreement/conflict/unresolved decisions, explicit omitted-country SG compatibility, closed Singapore-only routing, recognised foreign unsupported states, pre-IDP call stopping, and sponsor-readable ACRA profile coverage |
| Phase 07 final lifecycle remediation | Preserved every functional/UAT invariant; made complete two-role `RUNNING` metadata a pre-termination invariant and added executed missing-backend/frontend stop/reset plus duplicate/unknown-role regressions |
| Phase 07 remediation | Preserved every UAT and Phase 01–06 invariant; added executed exact-process lifecycle/start-stop-reset ownership, unrelated-process/PID-reuse/occupied-port safety, real process-local case reset, repeated lifecycle, and complete ordered sponsor blocker-presentation regressions |
| Phase 07 implementation | Preserved every Phase 01–06 invariant; added verified presenter-only multi-blocker, ownership-cycle, multiple-path, partial-amend, and no-replay recovery presets, safe case-bound UAT evidence export, always-visible execution-profile labelling, and explicit process-restart reset semantics |
| Phase 06 closure remediation | Preserved the eleven closed findings; moved generic ACRA Unicode-control validation ahead of normalization across every root/nested source text field and replaced equal-timestamp UUID ordering with repository-owned monotonic insertion order, proven by complete control-path and repeated ordering regressions |
| Phase 06 final remediation | Preserved the twelve prior finding regressions; added reviewed/all-document semantic re-evaluation with non-mutating registry-retention resolution, repeatable nonterminal Phase 05 finalization recovery, and fresh ACRA DTO/request-identity/provenance enforcement |
| Phase 06 remediation | Preserved all historical rules; added canonical-mutation stale rejection, legal-transition and terminal-fault enforcement, blocker-specific resolution, all-document aggregation, Phase 05 finalization recovery without replay, opaque ownership bindings, alternate-adapter full-path evidence, fail-closed demo routes, resilient polling, navigation guards, and truthful stage labels |
| Phase 01 final gate | Accepted the five canonical outcomes and call-stopping, search, and terminal invariants |
| Phase 02 final gate | Preserved all five outcomes; added ACRA source-validation, safe-error, provenance-minimization, and sandbox-shaped synthetic-mode regressions |
| Phase 03 implementation | Preserved all onboarding outcomes; added the verified all-match, mismatch, low-confidence, missing-field, and processor-failure scenarios, four-field comparisons, field decisions/original preservation, transient upload, and parent-case isolation invariants |
| Phase 03 remediation | Preserved the five document scenarios and added adversarial post-acceptance terminalization, provider replacement, provenance validation, pre-append stream-bound, typed review-contract, and UEN-normalization invariants |
| Phase 04 implementation | Preserved all onboarding/document scenarios; added the seven verified ownership scenarios, Decimal path/aggregation evidence, provisional inclusive threshold, cycle/incomplete/limit safety, provider replacement/provenance, terminalization, and parent/document isolation invariants |
| Phase 04 remediation | Preserved all accepted scenarios; added natural-person-parent semantic rejection, fresh provider-model reconstruction, opaque server-only provenance, terminal compare-and-set concurrency, digest path-ID bounds, threshold precision, and exact browser Decimal invariants |
| Phase 05 implementation | Preserved every onboarding/document/ownership scenario; added staged intake, deterministic integrated readiness, source-conflict containment, minimized snapshots, Mock base submission, call stopping, stale-readiness protection, idempotent concurrency, and case isolation |
| Phase 05 remediation | Preserved the normal Phase 01–05 catalogue; added current-canonical invalidation, current-canonical document conflict, exact snapshot/payload binding, safe post-target receipt recovery, stable identifier reuse, and frontend readiness invalidation invariants |
| Phase 05 final remediation | Preserved all prior scenarios; moved recovery evidence before rich receipt mapping and added four-outcome receipt/mapping fault recovery plus deterministic concurrent finalization with one logical Mock execution |
| Phase 05 target-response remediation | Preserved the receipt-recovery design; added immediate strict Mock response validation, aligned retained bounds, sanitized malformed-response stopping, operation-owner exit convergence, constant-only outcome fallback, and no-replay recovery regressions |
| Phase 06 implementation | Preserved every Phase 01–05 scenario and historical manual document rule; added verified zero-intervention orchestration, narrow integrated auto-confirmation, typed multi-blocker exceptions, version-bound resolution and auto-resume, duplicate/concurrent start/resume, provider conformance, loop/malformed-response stopping, sponsor-facing read-only progress, and Demo/Test Controls separation |
