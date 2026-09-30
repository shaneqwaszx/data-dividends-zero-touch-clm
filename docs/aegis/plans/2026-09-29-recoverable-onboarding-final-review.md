# Recoverable Onboarding and Final Review Implementation Plan

## Goal

Deliver a recoverable Singapore onboarding path that retains a draft, permits audited
same-case correction and bounded read-only provider recovery, stops every normal route
at an editable final review, and requires the authenticated user's durable confirmation
before the first GoldTier business mutation. Add an HR-only read-only ACRA diagnostic
console, truthful documented sample handling, and accessible operator tiles.

## Architecture

Extend the existing canonical owners. `OnboardingService` owns initial identity,
GoldTier Search, and registry continuation; `ZeroTouchOrchestrator` owns recoverable
stage transitions and blocker actions; reconciliation/document/ownership services keep
their current evidence responsibilities; `ClmOrchestrationService` owns readiness and
the frozen submission plan; the target ledger remains the only mutation/no-replay
owner; the schema-versioned case envelope remains the persistence/CAS owner;
authorization remains backend-owned; React Query remains the browser cache owner.
There is no second resolver, approval engine, persistence owner, provider router, or
target execution path.

## Tech Stack

Python 3.12, FastAPI, Pydantic, MongoDB, pytest, Ruff, strict mypy; React 18,
TypeScript, TanStack Query, Vitest, Playwright, Vite; browser print/PDF generated from
the server-frozen review projection.

## Baseline / Authority Refs

- User request attached 2026-09-29, including explicit supersession of earlier local
  non-goals for identity repair, Search recheck, editable classification, and final
  confirmation.
- `AGENTS.md`, `docs/DEVELOPMENT_WORKFLOW.md`, `docs/ARCHITECTURE.md`,
  `docs/PROJECT_STATE.md`, and current source/tests.
- D-056 and D-057 for bounded Singapore XPI values and current KYC/segment vocabularies.
- D-058 through D-060 and ADR-006 for initial identity, provider recovery, evidence
  continuation, ledger/no-replay, and the behavior now narrowly superseded.
- Current ACRA/GoldTier contracts, Q-006/Q-007/Q-012/Q-015, and the accepted operator
  blocker-resolution gate at main baseline `3d6e7b560b8062daeb93c31cf91b0df957797e9c`.

## Compatibility Boundary

- Singapore ACRA only; provider modes and evidence classifications remain truthful.
- Search failure never becomes no-match; ambiguity never becomes an automatic match.
- Independent evidence may continue without a selected GoldTier customer.
- No Shell, Policy, Amend, related-party, or other target business mutation occurs
  before a current durable confirmation; Search/read-back diagnostics remain read-only.
- The existing target ledger owns persisted intent, ordering, call stopping, uncertain
  outcome, finalization, and no-replay.
- Historical Garden target records, ID `143878`, uncertain Amend, and related-party
  child-ID blocker are never retried, erased, rebound, or generalized.
- Existing durable cases decode without read-time rewrite. Completed or historically
  mutated identities remain immutable; pre-submission cases may be corrected through
  version/CAS-bound actions.
- HR provider diagnostics grant no case access or submission authority. No secrets,
  raw provider payloads, document bodies, or private exception details enter browser,
  logs, tracked fixtures, or reports.

## TDD Route

- Mode: off
- Decision: skipped
- Strict authority: not applicable
- Strict signals: state-machine, API, authorization, persistence, provider, and
  concurrency behavior are affected.
- Light eligibility: not applicable.
- TDD-fit exception: none.
- Test posture: diagnostic reproduction followed by focused adverse regression and
  broad affected verification.
- Reason: the user requires comprehensive evidence but did not require strict RED/GREEN.
- Verification: focused backend/frontend tests after each slice, then the complete
  affected matrix and independent Quality Gate.

## Requirement Ready Check

- Requirement source: the current user request is explicit and supersedes the named
  earlier local omissions without changing unresolved external contract limits.
- Scenarios: missing identity, evidence continuation, Search exact/no-match/ambiguous/
  technical recovery, classification/rebind, document replacement/manual evidence,
  final review/confirmation, HR diagnostics, samples, and responsive operator UX.
- Acceptance: S1-S10 and the twelve numbered test groups in the current request.
- Open external limits: related-party child ID, arbitrary Amend fields, provider
  approval, and Live/Production claims remain blocked but do not block local work.
- Missing supplied inputs: the referenced screenshots and Garden demo pack are not in
  the attachment folder or repository; actual-pack parser/PDF verification is blocked
  until supplied. Source-backed reproduction and independent local work continue.
- Decision: ready for local implementation; external-read and missing-fixture evidence
  remain separately bounded.

## Change Necessity and Existence Check

- Code change is necessary because current executable behavior has no retained identity
  editor, no late Search action, no final confirmation state, direct submit paths, no
  ACRA console, and inaccessible tile hover/reflow behavior.
- Reuse candidates are sufficient: existing services, exception/action model, case
  lock/CAS envelope, target ledger, provider capability, GoldTier console pattern,
  navigation, and React Query effects.
- Add only durable facts and API/view surfaces inside those owners. Add one shared
  read-only ACRA diagnostic service because calling onboarding would create a case and
  mutate state; inject the already composed connector rather than constructing another.
- Architecture review: PROCEED by reuse. A superseding ADR is required for the durable
  confirmation boundary and recoverable late-Search transition.

## Execution Readiness View

- Intent Lock: implement S1-S10 without external writes.
- Scope Fence: no foreign registry, final/provider approval, arbitrary Amend mapping,
  related-party activation, historical replay, database reset, push, PR, or merge.
- Baseline Lock: branch `feat/recoverable-onboarding-final-review`, base/HEAD/origin-main
  `3d6e7b560b8062daeb93c31cf91b0df957797e9c`, initially clean.
- Owner Constraints: existing canonical owners only; root is Git/integration owner;
  writers receive disjoint sequential file ownership.
- Compatibility: preserve safe 404, in-lock reauthorization, session/team cache scope,
  strict provider DTO boundaries, Decimal ownership, ledger no-replay, and old-schema
  strict reads.
- Task Batches: backend state/persistence/API; frontend recovery/final review/console;
  operator tile accessibility; fixtures/provider reads; browser/PDF/physical evidence;
  independent QG, remediation, and re-QG.
- Drift Rules: stop only the dependent slice for an unresolved external contract,
  missing protected input, unsafe persistence transition, or target replay risk.
- Evidence Before Completion: exact tests, safe external read/write counts, physical
  restart proof, inspected screenshots/PDF, final diff/hygiene, and exact independent
  PASS on unchanged bytes.
- Advisory Boundary: this plan is execution guidance, not completion authority.

## Task 1 - Reproduce and freeze current dead ends

Inspect and extend existing backend/frontend tests for incomplete identity, retained
case editing absence, policy `TBD_SPONSOR` provenance, Search failure evidence
continuation, duplicate registry focus controls, tile hover/reflow, and direct target
submission paths. Start an isolated local runtime only after deterministic tests are
mapped; capture current/default/hover/focus evidence without external writes.

Verification: focused current tests in `test_onboarding_resilience.py`,
`test_zero_touch_orchestration.py`, `CaseStateExplanationPanel.test.tsx`,
`CaseStatePanels.test.tsx`, and guarded Playwright.

## Task 2 - Add durable recoverable actions and invalidation

Modify the existing domain/service/API/persistence owners to support version-bound
identity correction, accepted SG policy rebind, pre-confirmation classification edits,
and bounded same-case Search recheck. Reauthorize inside the case lock/CAS boundary.
Retain before/after/rationale and evidence references; invalidate dependent Search,
registry/document bindings, readiness, frozen review, and confirmation only when their
inputs change. Completed/attempted/uncertain target cases reject in-place identity
replacement and return a linked-new-case or existing provider-recovery action.

Primary files: `domain/models.py`, `domain/zero_touch.py`, `domain/clm.py`,
`services/onboarding.py`, `services/zero_touch_orchestration.py`,
`services/clm_orchestration.py`, repository protocols/implementations,
`persistence/models.py`, `persistence/mongo_case_store.py`, `main.py`, `api_models.py`.

Verification: missing-input/save/resume, stale revision, reauthorization, double click,
independent blocker retention, late Search outcomes, identity-change invalidation,
old/current/new schema decode, CAS, restart, delete/anti-resurrection, and physical
Mongo against one generated allowlisted disposable database.

## Task 3 - Make documents, decisions, and manual evidence independently usable

Reuse document replacement/field-review and reconciliation owners so uploads persist
and recompute even while GoldTier identity is unresolved. Add only typed manual
ownership evidence permitted by the current POC direction, bound to case/entity/source/
date/basis and validated by the existing Decimal engine. Add a versioned blocker
decision classification (`AUTO_RESOLVED_WITH_NOTE`, `CONTINUE_WITH_WARNING`,
`USER_ACTION_REQUIRED`, `EXTERNAL_DEPENDENCY`, `HARD_STOP`) as retained decision
metadata, not an AI override or second workflow engine.

Verification: missing/no-text/corrupt/encrypted/replacement/conflict, manual evidence
totals/cycles/wrong identity/cross-UEN rejection, prompt-injection-as-data, and clearing
one blocker without clearing another.

## Task 4 - Add frozen final review and universal confirm-and-send gate

Create a canonical review projection from the exact mapped submission input and target
operation plan. Persist actor, timestamp, case/evidence/policy versions, destination,
acknowledged warnings, and canonical digest. Every normal API/worker path must stop at
`READY_FOR_CONFIRMATION`; `execute_submission_input` and incremental ledger dispatch
must reject absent/stale confirmation before creating target intent or calling the
connector. Recheck duplicate/target state immediately before dispatch; invalidate and
return a revised review when material state changes. Preserve idempotent double-confirm,
refresh, two-tab, restart, accepted/processing/completed/uncertain distinctions, and
deletion protections.

Verification: new/existing customer paths, all direct APIs/workers, digest/version
staleness, role/team change, double confirm, restart, duplicate reservation, no pre-
confirmation Shell/Policy/Amend, and unsupported editable fields labelled as local-only.

## Task 5 - Build recovery, review, print, and cache-safe frontend flows

Add retained-case identity/policy/classification forms and a case-scoped Review and Send
route. Render exact mapped fields/operations, evidence sources/limitations, corrections,
warnings, local-only fields, edit links, Save draft, Review outstanding items, and the
explicit sandbox confirmation label. Generate screen and A4 print/download output from
the same frozen server projection. Extend the centralized React Query key/effect owners
for edits, recheck, review, confirmation, invalidation, cancellation, session change,
and 401 clearing.

Verification: role/capability presentation, stale response rejection, mutation retry
disabled, keyboard/mobile/print behavior, digest invalidation, and PDF visual inspection.

## Task 6 - Add HR-only read-only ACRA console

Inject the already composed ACRA connector into a focused diagnostic service. Reuse
`PROVIDER_SANDBOX_TEST`; retain HR's lack of `CASE_ACCESS`. Expose fixed safe host,
mode/classification, credential-presence booleans, bounds, actual supported-operation
coverage, last check, typed empty/not-found/partial/error results, and a sanitized
receipt. Add bounded concurrency/rate/cancellation safeguards as project safety, not
provider claims. Never create a case or ledger entry.

Verification: 401/403/RBAC, bounded UEN, arbitrary-host rejection, exact call counts,
redaction, timeout/429/malformed/oversize/not-found/empty/partial outcomes, cancellation,
and zero repository/ledger/provider mutation.

## Task 7 - Correct tile layout and operator usability

Deduplicate registry focus actions; render responsive title/status/action rows with
normal wrapping, sensible minimum width, 44px targets, visible focus, AA text contrast,
forced-colors and reduced-motion support. Problem tiles open/focus the real corrective
surface or a compact owner/missing-items/next-action explanation. Keep stage navigation
separate from mutations.

Verification: component tests plus inspected 360, 768, 1280, 1440, 1920, 320-reflow,
200%-zoom, hover, focus, long-label, keyboard, mobile, live-progress, and print captures.

## Task 8 - Validate official samples and upload fixtures honestly

Use the app's composed connector with writes disabled and the authorized budget of at
most 12 ACRA operation requests and 6 GoldTier Searches. Stop on auth/rate limiting.
Evaluate Garden, OPQ, and RRR separately; do not combine SIM LIM shareholder/capital
samples. Add profile-matching upload fixtures only after observed values are known and
label synthesized supplementary evidence. The absent Garden pack remains a named
blocker to verifying its original bytes; do not fabricate it.

Verification: sanitized receipt, exact read/write counts, fixture parser/address checks,
one normal/correctable/no-text expected-outcome set, and zero external writes.

## Task 9 - Durable docs, verification, and independent gate

Add the superseding ADR/decision, update active architecture/contracts/state only to the
proved candidate truth, and run the complete affected backend/frontend/type/build/
contract/security/governance/Playwright/physical-Mongo matrix. Inspect the complete diff
and all task-owned untracked Markdown. Freeze exact content for a fresh independent
`fyp-quality-gate`; remediate findings and obtain a fresh re-gate on changed bytes.

No commit, push, PR, merge, provider write, or database reset is authorized.

## Risks and Retirement

- Large existing service/UI hotspots increase ripple risk; prefer focused helpers inside
  existing boundaries and inspect all consumers.
- Late exact-match reconciliation must not silently attach prior evidence to another
  target identity; changed identity invalidates dependent bindings.
- Retire direct normal auto-submit behavior, terminal missing-input dead ends, write-once
  pre-confirm classification, duplicate focus controls, squeezed tile layout, and any
  UI-only confirmation illusion.
- Retain historical ledger truth, source evidence immutability, unresolved external
  contract labels, unsupported-field transparency, and no-replay semantics.

## Execution Route

- Decision: subagent-driven with one root integration owner.
- Evidence: the user explicitly requests delegation and a fresh independent reviewer;
  backend, tile-only UI, and provider/sample investigation have disjoint boundaries.
- Fallback: serialize writers whenever owner files overlap; root resolves integration
  only after each slice is verified.
- User confirmation required: no for local implementation and authorized read-only
  diagnostics; yes later for any case-specific external write, which is outside this task.

