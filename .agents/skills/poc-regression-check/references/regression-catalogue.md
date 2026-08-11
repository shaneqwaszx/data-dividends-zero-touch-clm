# Accepted POC regression catalogue

This catalogue records the accepted Phase 01 mock scenarios preserved by the final
Phase 01 and Phase 02 quality gates, plus the separately scoped Phase 03 document
scenarios established by its planner and implementation. All identifiers and data are
synthetic.

## Canonical mock scenarios

| Input | Accepted behavior | Terminal result | Required calls | Prohibited calls/claims |
|---|---|---|---|---|
| `202400001A` | Complete synthetic SME; required mock target stages succeed | `COMPLETED` | ACRA fetch; GoldTier search `NO_MATCH`; shell; policy; amend | No Ready-for-Approval or live-interoperability claim |
| `202400002B` | Registered address absent; human review before target processing | `REVIEW_REQUIRED` | ACRA fetch only | No GoldTier call; no completion |
| `202400003C` | Deterministic policy validation failure | `FAILED` | ACRA fetch; search `NO_MATCH`; shell; policy | No amend or completion |
| `202400004D` | Amend returns representative partial outcome | `REVIEW_REQUIRED` | ACRA fetch; search `NO_MATCH`; shell; policy; amend | No completion |
| `999999999Z` or another well-formed unknown synthetic UEN | Registry record not found | `FAILED` with safe `ACRA_ENTITY_NOT_FOUND` | ACRA fetch only | No GoldTier call; no completion |

Whitespace-only or malformed API input is rejected before case creation. Padded
lowercase `202400001a` normalizes to the canonical happy-path UEN; the
nine-digits-plus-letter rule is a synthetic demo rule, not a production ACRA contract
claim.

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
| `GOLDTIER_SEARCH_FAILURE` | `FAILED / GT_SEARCH_FAILED` | Search only | No later call |
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

## Accepted cross-scenario invariants

- GoldTier search `NO_MATCH` alone permits shell creation. `MATCH_FOUND` stops at
  `REVIEW_REQUIRED`; modeled search `FAILURE` stops at `FAILED`; neither creates a
  shell.
- Unexpected failures during ACRA fetch/mapping or GoldTier search/shell/policy/amend
  persist one sanitized terminal `FAILED` event and stop before every later operation.
- Malformed required ACRA source data ends as retrievable `FAILED` with a stable safe
  code and zero GoldTier calls. Canonically incomplete required data cannot reach
  GoldTier and routes to review under the accepted rule.
- A partial required stage cannot produce `COMPLETED`. Terminal state is the final event.
- Multiple cases retain independent identifiers, timestamps, histories, results, and
  connector behavior.
- Default Mock ACRA and Mock GoldTier remain credential-free and network-free. A
  sandbox-shaped synthetic ACRA success is labeled `ACRA/SANDBOX` with Mock GoldTier
  and is not evidence of a live call.
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

## Catalogue evolution record

| Established by | Change |
|---|---|
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
