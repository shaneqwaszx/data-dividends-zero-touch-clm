# Garden ownership trace and demo recovery truth — independent Quality Gate

## Verdict: PASS

The bounded LOCAL continuation satisfies its current acceptance criteria. No P0, P1
or P2 finding remains. Gate remediation rounds: **0**; the invalid-declaration correction
preceded this gate and is not a gate remediation round. No implementation fix was made
by this reviewer. All previous reports and gates remain preserved.

## Reviewed identity and authority

Review date: 2026-10-01. Reviewer had no implementation role and wrote only this report.
Applied `fyp-quality-gate`, current root/backend/frontend AGENTS and the user's Garden
Ownership Trace + Demo Recovery Truth continuation. Read the accepted local handoff
sections, current compact report, all nine source/test delta files and relevant owning
connector/ownership/cache boundaries. Review is against the task-start accepted candidate,
not the accumulated uncommitted diff against HEAD.

Branch `fix/demo-happy-path-stabilization`; HEAD/base/local origin/main
`efc31f450f0103766fa812bc0aa80754f801dbe9`. Index empty. Reviewed manifest
`tmp/GARDEN_OWNERSHIP_TRACE_REVIEW_MANIFEST.json`: nine source/test paths plus the
compact implementation report, deterministic identity
`983142aaf9a4ce1d61b8379801cead5a42184a0f8a7b4c92e23cce6caac2696f`.
Raw hashes and manifest identity matched before and after review. Preserved task-start
hashes/copies and delta identify the exact continuation. No Git mutation, provider call,
.env access, Atlas access or retained Mongo mutation occurred in this review.

## Independent answers Q1–Q12

| Question | Answer and evidence |
| --- | --- |
| Q1. Absent upstream or dropped? | **Explicitly empty upstream in the accepted recorded/offline Garden path.** The strict offline shareholder response is HTTP200 with `entities: []`; decoding retains zero parties, canonical OWNERSHIP_PARTIES=EMPTY/count0, and the registry ownership provider retains root only. The engine reports REVIEW_REQUIRED/INCOMPLETE_LEGAL_ENTITY with no transport error. No boundary drops available Garden owners. |
| Q2. Does existing ownership survive? | **Yes, supported observations remain intact.** Nonempty Marketplace shareholders retain identifiers, categories/status and exact share counts; absent percentages remain absent and are not inferred. Sufficient normal Golden Mock acquisition relationships survive canonical/provider/API analysis without OWNERSHIP_REQUIRED, and the new UI renders retained relationships with exact decimal strings. Marketplace share counts alone do not establish sufficient ownership percentages. |
| Q3. Is empty UI truthful/actionable? | **Yes.** Registry separates Identity retrieved from Ownership unavailable; the active ownership explanation and structured-details/upload actions are present. FAILED, NOT_ATTEMPTED and UNSUPPORTED are distinct from EMPTY. Fresh Garden clean/conflict browser assertions verify the current gap and action focus. |
| Q4. LOCAL versus ACRA provenance? | **Clearly separated.** Manual analysis and every retained relationship have LOCAL provenance. The same screen says client-supplied, not ACRA-derived and not independently verified. Original registry EMPTY remains a neutral source fact. |
| Q5. Does valid save immediately clear blocker? | **Yes.** Normal ownership POST resolves ownership into history, removes its active intervention/banner and publishes the next genuine state without reload or Continue. Invalid inputs leave version, active/history and stage unchanged. |
| Q6. Existing Decimal engine automatic? | **Yes.** The unchanged ownership owner calculates exact 60/40 and both provisional UBO candidates at the case-frozen >=25 threshold after valid save; no Analyze action or second engine. |
| Q7. Can stale data resurrect blocker? | **No in the verified supported flows.** Existing exact cancellation and revision guards are unchanged; independently rerun held/stale publication tests retain newer summaries/documents/ownership. No page-local cache owner, optimistic blocker removal or mutation retry was introduced. |
| Q8. Golden unchanged? | **Yes.** Fresh independent normal-UI Golden run completed with zero exception interventions, one explicit Mock send confirmation and COMPLETED; provider ownership remains sufficient. No demo shortcut or forced state. |
| Q9. Active/history correct? | **Yes.** Resolved ownership disappears from active state and remains RESOLVED history; conflict decisions progress 4/3/2/1/0. Generic confirmation accounting and explicit RM final send from the accepted baseline remain intact. |
| Q10. GoldTier recovery unchanged? | **Yes, per unchanged sanitized fresh-process read proof.** Same retained case/submission and ID143880, PROVIDER_VERIFIED_RECOVERY, original Shell uncertain, replayed=false, no Policy/Amend, no terminal outcome/receipt. Raw before/after document SHA matches. Reviewer inspected proof without reconnecting or initializing the database. |
| Q11. External calls exactly zero? | **Yes for this task and review.** Memory/local Mock and injected strict offline Marketplace transport; browser network guard; no ACRA, GoldTier or PingFed dispatch. No fresh official provider observation claimed. |
| Q12. Synthetic ownership invented? | **No provider ownership was invented.** Golden is its disclosed deterministic Mock dataset; Garden recovery is explicitly user-supplied synthetic 60/40 evidence through normal validated input. Empty ACRA ownership is never replaced by fabricated ACRA parties/percentages or fallback. |

## Trace, correctness, security and architecture

Reviewed the complete transport/decoder/source DTO/canonical/provider/analysis/
orchestration/API/query/UI trace and the compact sanitized reproduction/final proofs.
The root cause is presentation of genuine missing evidence, not a broken acquisition
or ownership engine. The new explanation is gated on the existing acquisition provider
and EMPTY operation. The recovered-party table uses retained identifiers, relationships,
exact percent strings and relationship provenance; it does not calculate percentages.
No sponsor source precedence, hierarchy/related-party operation or business rule was added.

The second narrow defect was domain declaration conversion escaping as a server error.
The API boundary now converts Pydantic ValidationError to fixed sanitized 422 without
raw exception text or party names. Percentage/duplicate/required-metadata rejection
retains current workflow state. Existing authenticated actor, authorization and
lock-bound reauthorization continue to own the sensitive mutation. No route-to-database,
ledger bypass, alternate ownership mapper/engine or frontend authorization appears.

Change classes are BACKEND_API and FRONTEND_UI plus documentation. API projection/error
presentation and component prop changed; shared JSON statuses/types, connector,
configuration, target mapping, auth/RBAC, schema/repository/CAS, Decimal engine and
provider classification are unchanged. Existing session/team/case scope, revision
guards, no-replay target safety and current final confirmation remain preserved.

## Executed evidence

Fresh independent execution on the frozen candidate:

- Safe remediation plus Marketplace connector suites: **41 passed**, one existing warning.
- Safe manual ownership plus registry acquisition suites: **74 passed**, one existing warning.
- Focused ownership/provenance/cache Vitest: **21 passed** across three files, including
  exact long Decimal rendering and held/stale publication checks.
- Guarded normal Garden clean/conflict browser: **2 passed**; gap/action/focus, busy state,
  exact 60/40 LOCAL table, active disappearance/history and automatic readiness progression.
- Guarded normal Golden browser: **1 passed**, zero exception interventions, one explicit
  confirmation, COMPLETED and no `/api/demo/*` request.
- Guarded contract unittest lane: **44 passed**.
- Final frozen hashes, empty index and task Markdown whitespace: verified.

Backend commands used the existing `tmp/zero_touch_safe_pytest.py` with
`-o addopts='' -p no:cacheprovider`: dotenv reads blocked, memory/Mock and MongoClient
forbidden. Initial selection included a nonexistent ownership test filename and aborted
collection; corrected selection above executed successfully. This was a reviewer command
selection mistake, not a candidate failure. Scoped approved frontend/browser escalation
allowed existing Vite/esbuild ancestor access; no provider/database access was granted.

Fresh independent Garden screenshots: `tmp/zero-touch-browser/1790836508533`.
Viewed recovered clean ownership viewport and conflict saving viewport. The recovered
screen shows 60%/40%, LOCAL/not-ACRA declaration, candidate controls and readiness READY;
saving disables inputs. Table overflow remains in its existing horizontal scroll region.
Fresh Golden screenshots: `tmp/zero-touch-browser/1790836556950`.
No new native zoom/responsive claim is made. Test-only API verification reads are separate
from measured browser requests. Each ownership save and conflict decision used one POST
plus three supporting GETs; action focus made zero requests. Golden send used one POST
plus one intelligence GET. Garden stops at readiness for explicit send, not target approval.

Coordinator evidence inspected and separately attributed: affected backend **346 passed**;
full frontend **392 passed**; contracts44; Ruff, strict mypy112, typecheck/build,
architecture/secrets and tooling/policy/provider checks PASS. Additional full safe backend
on this unchanged frozen candidate: **1531 passed, 38 skipped, 4 warnings** in
`tmp/GARDEN_OWNERSHIP_TRACE_BACKEND_ALL.log`. This additional result was supplied after
the compact report froze; it does not imply that report was changed or skipped physical
checks passed. Earlier failing-first UI/invalid-declaration evidence remains retained.

Retained read proof `tmp/GARDEN_OWNERSHIP_TRACE_LEDGER_PROOF.json` records no database
initialization/writes/provider calls and preserved running service, with identical raw
before/after SHA-256
`fb11ed2085b234ae83eaba4d97247b994f6e48617f4ee6b2224e184883a7574f`.
The recovery chronology, uncertain original Shell and replayed=false remain unchanged.

## Limitations and next authorized action

Current Live ownership availability was not retested. The earlier named official
Garden EMPTY observation supports its historical scope only. LOCAL declarations are
not independently verified ownership or provider approval. The pre-existing project-state
unreachable verified-main SHA remains a disclosed governance failure, not a passing check.
No provenance refresh, fetch or metadata repair was authorized.

No persistence source changed, so no new physical rerun was triggered. Earlier required
physical acceptance remains pending its authorized mongo:7 CI lane; 38 skipped lanes are
not physical PASS. This limitation does not block the bounded local presentation/error
boundary acceptance and is not waived by this gate.

All requested current stop conditions are verified. The frozen LOCAL continuation is
accepted; no required local correction remains. Next authorized action is owner review
of the uncommitted candidate and this gate. No commit, push, PR, merge, new phase or
external provider operation is authorized by PASS.
