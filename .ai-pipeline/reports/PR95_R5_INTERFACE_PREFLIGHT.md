# PR95-R5 independent scoped-read interface preflight

## Verdict and authority

**PASS -- DESIGN PREFLIGHT ONLY.** Architecture review: **PROCEED** within the exact
existing-owner interface below. This is an independent read-only architecture/security
assessment required by the owner's PR95-R5 attachment. It permits the coordinator to
implement P2-06 within that approved design. It is not implementation acceptance, a
full-PR adversarial assessment, a Quality Gate, a physical-Mongo result, commit authority
or publication authority. No backend implementation existed in this review.

The reviewed proposal is `.runtime/PR95_R5_PLAN_AND_INTERFACE.md`, SHA256
`337ca8bc724ebb76d1905434ce81da6030a1a8466c364a77fe7c1869db12f43f`.
Its six-defect remediation plan is not accepted by this narrow preflight; only its
P2-06 interface and necessary timing/security integration are assessed here.

Observed local identities: branch `codex/pr95-dashboard-remediation-20261018`, HEAD
`e970a0b31fe2cf2c1617dcc759c9d2131433ba68`, committed tree
`8abb0de47de69a24f88550f3ddece82c03b7a626`, origin/main
`4a280da473dcdbeb345ffdfa79aaa4c001e75f62`. Read-only status shows the five preserved
R4 frontend modifications plus the untracked historical R4 adversarial report, with
an empty index. These committed identities do not describe the uncommitted R4 files.
Remote fetch and primary/worktree preservation are coordinator-owned checks, not
independently executed remote verification by this reviewer.

## Evidence and existing owner check

Authority read: the complete PR95-R5 attachment; proposed interface; root/backend
AGENTS; skill routing, architecture-change-review, persistence-schema-change,
integration-security-review/checklist, integration-safe-development and quality-gate
role boundary; development workflow/ADR criteria, merge protocol and Codex coordination
workflow; architecture owner map/dashboard/persistence sections; current project-state
provider/POC/production-debt context; case-access, timing and persistence contracts;
R4 handoff, frozen manifest, bounded design assessment and immutable adversarial FAIL
report. The current sponsor questions provide no new provider, production identity or
SLA authority, and none is needed for this read-only POC correction.

Executed read-only `dev_context.py` for BACKEND_DOMAIN, BACKEND_API, PERSISTENCE and
AUTH_RBAC_SECURITY. An initial sandboxed Git status could not identify the worktree;
an authorized escalated read reproduced the actual status and clean index. No Git
mutation, database operation, dotenv read or provider request occurred.

Owning source inspected:

- `services/dashboard.py`: authorized portfolio read, unscoped automation read, final
  clock, Singapore cohort, creator-only mine lists and authorized resolver workload.
- `services/case_query.py`: `_resolve_scope`/authorized portfolio before filtering.
- `services/zero_touch_repository.py`: existing port, locked defensive memory reads,
  canonical automation validation and shared descending updated-at/case-ID ordering.
- `persistence/repositories.py`: existing Mongo automation adapter and its strict-store
  read boundary; no second automation/persistence owner is needed.
- `persistence/mongo_case_store.py`: canonical UUID `_id`, envelope/nested identity,
  strict version/unknown-field decode, unavailable errors, current list/get and startup.
- `persistence/composition.py`: explicit mode assembly through existing port/adapter.
- Existing dashboard/compatibility and Mongo regression owners, including the final
  observation/midnight assertions; API safe DASHBOARD_UNAVAILABLE error catches.
- Browser/physical runner boundaries are relevant later evidence obligations, not
  runtime or acceptance evidence provided by this design review.

Existence check: the current automation repository port, memory owner, Mongo automation
adapter and MongoCaseStore already own every required responsibility. A separate
Dashboard read store, DTO, authorization engine or cache would duplicate an owner.
Extending these current owners is sufficient.

## Approved dependency and execution map

`DashboardService -> ZeroTouchAutomationRepository.capture_for_cases -> opaque batch`
remains a service-to-port dependency. In Mongo mode the existing automation adapter
uses a store-owned opaque captured snapshot batch. Only that adapter receives decoded
DurableCaseSnapshot values and returns canonical automation records. The service never
imports MongoCaseStore, persistence codecs, Mongo documents or driver types.

The port accepts a frozen finite UUID set and returns a context-managed batch exposing
only `read_selected(frozenset[UUID]) -> list[ZeroTouchAutomationRecord]`. Capturing does
not yield its handle until the authorized raw cursor is fully materialized. Read-selected
is one-shot; it can only narrow the original authorized set. All raw data, captured
model references and decoder callbacks are released on success, failure and context exit.
The context manager itself must not remain usable across requests or re-entry.

Required service sequence is:

1. Resolve authorized case projections under current actor/team/Director rules.
2. Enter capture using every authorized case ID, not the 200 display prefix and not
   prematurely narrowed to creator-only My work cases.
3. After capture completes, call the one existing final server clock exactly once.
4. Derive the unchanged Singapore cohort and legacy UTC trend from that observation.
5. Strictly read only final-cohort IDs from the captured batch. Creator counts/lists
   can narrow afterward; resolver evidence still includes authorized teammate cases.
6. Construct metrics from those records and that observation, closing the batch even
   if timing validation or DTO construction fails.

No DB fetch may occur in read-selected or after the clock. The interface carries no
new timestamp, date rule, actor grant or provider capability.

## Owner-required guarantee decisions

Each PASS below is an approved design property with mandatory implementation constraints;
execution proof remains a later acceptance requirement.

| Required guarantee | Design decision and implementation obligation | Verdict |
| --- | --- | --- |
| Existing boundary/raw encapsulation | Raw dictionaries stay private to the existing store batch. The adapter translates decoded snapshots. The service sees only the automation port and batch methods. No raw field/property, iterator, serializer, callback exposure or document-bearing repr. Python privacy is an internal discipline, not a sandbox against arbitrary trusted-code introspection. | PASS |
| Finite authorized input | Accept only an actual frozen set of UUID values. Build it from CaseQueryService's already authorized records. Copy/retain that immutable set; reject invalid argument shapes with fixed safe errors. The repository does not invent or re-evaluate roles. | PASS |
| No scope expansion | Selected IDs must be a subset of the original captured authorized IDs. Validate the entire argument before any selected decode. Foreign IDs fail closed; no supplemental fetch or union. | PASS |
| Final cohort before decode | Dashboard computes the final cohort after the final clock and passes exactly those IDs. The repository performs subset enforcement, not date business logic. Empty selection decodes nothing. | PASS |
| Excluded malformed isolation | One `_id: {$in: ...}` query excludes foreign teams through pre-authorized IDs. Captured authorized excluded-date envelopes must not undergo full schema, nested identity, automation or timing validation. Dispatch uses canonical Mongo `_id` routing only, not untrusted nested case IDs. Invalid excluded nested data cannot poison selected decode. Driver transport/BSON failures remain unavailable errors; this is not a promise to survive storage/driver corruption. | PASS |
| Strict selected evidence | Each selected present envelope passes the unchanged store `_decode`, including all historical versions, unknown fields, outer/nested identity and automation invariants. Bind the decoded case ID back to the selected canonical Mongo key. Do not skip, repair or clamp an invalid selected envelope. | PASS |
| Eager pre-clock materialization | Fully exhaust the one find cursor inside capture before yielding the handle. Close cursor/resources on exhaustion or error. No generator-backed raw collection, delayed find, per-ID get or lazy decoder-driven database work. | PASS |
| Request lifetime | Context closes on every exit; successful or failed one-shot selection cannot be retried or widened. Calls after close/consumption fail with fixed safe errors. Close clears store/adapter raw/model/callback references even if decode raises midway. No global registration, retained context, session cache or persistent handle. | PASS |
| Memory snapshot parity | Under the current memory RLock capture defensive deep copies for authorized IDs only. Release lock before clock/metric calculation. Validate selected canonical records only, bind dictionary key to record.case_id, return defensive copies, use common ordering, and clear captured references on exit. Later save/delete/caller mutation cannot alter the captured request snapshot. | PASS |
| Missing or deleted before capture | A missing envelope or absent automation is omitted as existing get/list behavior; no fabricated automation, reread, recovery, insert or resurrection. An authorized case projection can therefore outlive its absent automation in the same ordinary live read. | PASS |
| Delete/update after capture | Use the owned captured snapshot for this request. This does not strengthen current sequential reads to a transaction, authorize a write, or preserve the case in any future request/cache. Test a fresh subsequent request separately. | PASS |
| Duplicates and inconsistent identities | Frozen input removes requested duplicates. Mongo enforces unique `_id`; nevertheless reject duplicate selected returned keys rather than last-wins dictionary overwriting. Full selected decode rejects `_id`/case_id/nested mismatches. Excluded nested corruption is not eagerly validated. An unexpected foreign query result is an internal query-integrity failure, never data to publish. | PASS |
| Stable ordering | Ignore driver result order; selected adapter results use current order_zero_touch_automation_records updated_at/canonical case-ID descending. Do not change portfolio/creator/resolver or stable tie semantics. | PASS |
| Query/resource shape | One finite authorized-ID find, zero finds for empty authorized input, no per-case detail fetch and no whole-store decode. Over 200 is not truncated. The authorized set remains proportional to existing POC inventory; no invented production-scale bound or unbounded browser request. A driver size/resource failure must not trigger a global scan or memory fallback. | PASS |
| Privacy/errors | No raw/model payload, private validation detail or callback in API, logs, exception text, evidence, serialization, cache or durable storage. Selected strict failures use existing persistence errors; driver failures use existing unavailable error; HTTP preserves sanitized 503. Port misuse remains a fixed internal error, not an excuse for blanket exception masking. | PASS |
| No new durable/provider authority | No version, schema, index, migration, CAS, insert/update/delete, recovery, startup validation, config, auth grant, target ledger or external connector change. Do not weaken startup's existing whole-store validation as a workaround. | PASS |
| Timing and My work | Exactly one post-capture observation; unchanged Singapore midnight and UTC historical trend; cohort decode precedes creator-only narrowing, preserving actual resolver fixes on authorized teammate cases. All response durations use the same observation. | PASS |

## Architecture, entropy and ADR decision

**ADR required: NO for this exact bounded extension.** This adds an internal read
lifecycle to an existing repository owner under an explicit owner-selected design and
preserves its strict selected-envelope compatibility strategy. It creates no canonical
owner, module/trust boundary, persistent cache, durable schema strategy, framework,
transaction promise or changed timing invariant. The alternatives in the immutable R4
assessment are not being adopted. The approved request-local behavior should be recorded
in the affected current architecture/persistence description and implementation report;
CASE_TIMING_PROFILE.md does not need modification.

The new state is only captured/consumed/closed within one request. No registration,
expiry policy, configuration switch, alternate runtime mode or long-lived cleanup owner
is appropriate. Retire Dashboard's unscoped list_records call immediately when replacing
it. Keep the existing list_records port for proven other consumers: memory portfolio
list/activity and automation orchestration recovery still call it. Removing it broadly
would be unrelated cleanup and could remove accepted behavior.

Stop and obtain a new preflight/owner scope decision if implementation needs a new
repository/read model, raw service exposure, global or persistent caching, a transaction,
new timing observation, scope-changing fallback, weakened codec/startup validation,
new schema/index or changed create/update/delete semantics. Those would change this
ADR conclusion and are not covered by this PASS.

## Required implementation and acceptance evidence

Before a full-PR acceptance claim, obtain failing-first and final tests for all these
properties, plus the owner's broader six-defect matrix. Unit tests alone do not prove
driver query shape or physical behavior.

- Actual guarded physical Mongo with new allowlisted disposable databases: other-team
  and excluded-date malformed full envelopes succeed when irrelevant; selected malformed
  envelopes fail with safe503. Use runtime corruption after ordinary valid initialization
  where needed; do not weaken strict startup. Never connect to clm_poc.
- RM/onboarder, Director global/team/unassigned and My work; cross-person resolver-only
  rows and creator-only case lists. All cohort rows beyond200 must still validate.
- Empty and 201+ cohorts; one authorized-ID find/no N+1; no find for empty scope; exclude
  other teams in the actual predicate. Compare memory/Mongo result and stable ordering.
- Exactly one clock after eager materialization; Singapore midnight crossing before that
  observation; existing concurrent-resolution and legacy UTC trend regressions retained.
- Selected unknown schema, invalid identity/unknown fields and automation errors stay
  strict. Excluded malformed schema/nested values are not decoded. No fallback.
- Missing/deleted before capture, delete/update after capture, selected duplicates and
  mismatches; selected missing automation omitted without writes; subsequent request
  observes deletion. No stale resurrection/CAS/recovery/provider changes.
- Immutable ID arguments, foreign subset, malformed arguments, double-read, post-close,
  failed-decode cleanup, re-entry and caller mutation. Memory captures under lock and
  returns independent snapshots; raw resources and closures release on every exit.
- Relevant stage-duration validation is still independently necessary: canonical codec
  currently accepts negatives. P2-06 alone does not correct R4-A1 or justify suppressing
  all Pydantic exceptions. Apply only the separately authorized Dashboard timing guard.
- Fresh full affected backend and guarded physical suites, contract/security/static checks,
  comprehensive full-PR adversarial re-review, then a separate fresh exact-content Quality
  Gate. Preserve R4 FAIL; no final PASS, commits or clean-tree pre-PR claim derives here.

## Limitations and handoff

This preflight inspects a concrete interface proposal and existing source. It does not
claim that a not-yet-written handle enforces these properties, nor that infrastructure,
physical Mongo or browser execution succeeded here. No tests of a future implementation
were run. The sole reviewer tracked write is this report; no reviewed source, test,
configuration, historical report or instruction was modified. No Git/GitHub/database or
provider mutation occurred.

No further owner authorization gap was identified for implementing this precise design.
The owner explicitly superseded date-selected-before-raw-fetch with authorized-ID-before-
capture and final-cohort-before-full-decode. Proceed only within that boundary and the
mandatory constraints above. Final disposition: **PASS, independent interface preflight;
implementation and later independent acceptance remain outstanding.**
