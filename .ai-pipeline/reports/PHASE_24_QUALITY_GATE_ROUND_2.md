# Phase 24 fresh independent quality gate — after remediation round 1

## Executive Result

**FAIL.** Five current findings remain: one P1 identity-bound browser cache defect and four P2 ownership/persistence/accessibility defects. The user requires FAIL for any P0/P1/P2. Passing existing suites does not cover the independently reproduced counterexamples below. No implementation, test, configuration or ordinary documentation was repaired during this gate.

Frozen reviewed content: `a93d78a876f49b6b18cdc119b940f72c1e16c6c88a1be44a247b854781f90945`, all 60 paths in `PHASE_24_CANDIDATE_MANIFEST.json`. Branch `feat/phase24-registry-identity-ownership-ubo`; base, HEAD and inspected origin/main all `039101b69772c4c9ae4ca7b4a7ca3e4c19b03f4c`. This is a fresh review of revised content, not a revision of the preserved failed round-1 verdict. The prior report and manifest remain included, byte-frozen history.

The independent coordinator reviewed and authored this report, with two narrow read-only specialists for ownership and frontend falsification. No worker changed source. User-requested reviewer route: GPT-6.1 Sol / High; inherited specialist configuration, no fallback asserted. Current tools included shell, existing Python 3.12.10, Node 22.23.3/npm 10.9.9, pinned Playwright Chromium, and the task-owned disposable Mongo container. Narrow execution/report escalations were granted for worktree and dependency/process access; no rejected approval was bypassed.

## Phase Acceptance Checklist

The original 20 reviewer questions are assessed against the full assigned request, current planner/contracts and the user's October 2 discovery clarification.

| # | Question / result | Direct evidence and qualification |
|---|---|---|
| 1 | Canonical UEN correction — PASS | ENTERED/DOCUMENT/OTHER route through existing ZeroTouch/Onboarding verification and registry acquisition. Focused identity tests and real configured browser scenarios pass. |
| 2 | Safe document/UEN conflict — PASS at backend | Current document ID/event count, confidence, eligible UEN and actor/version are checked before mutation; explicit entered choice resolves only the identity discrepancy. Browser publication has R2-F1. |
| 3 | Dependency-aware invalidation — FAIL | Backend retires identity-derived analysis and retains history; R2-F1 leaves its old browser projection under the corrected identity. R2-F3 also breaks retained independent continuation in Mongo. |
| 4 | Completed identity immutable — PASS | Service/lock/confirmation and completed guards reject rebind before provider side effects; focused and browser completion evidence. |
| 5 | Garden truth — PASS, bounded | Sanitized current receipt: partnership, four ROLE observations/four OWNER_ROLE tags, REVIEW_REQUIRED, zero candidates, no numeric numerator/denominator/percentage. Local synthetic Garden remains explicitly offline. |
| 6 | Actual suitable official sample if available — satisfied truthful insufficiency | Available seven-page catalogue was inspected locally for candidate discovery by implementation; documented supported reads were performed. No coherent same-entity quantitative/control fallback was found. October 2 expressly permits this result; no numerical/Live demo is invented. This gate inspected receipt/source/authority and made no external call. |
| 7 | Cross-UEN mixing — PASS in inspected/executed binding paths | Same-UEN denominator compatibility and adverse tests; nested/repeated scalar parent bindings repaired. Unbound shareholder examples never joined to capital from another UEN. |
| 8 | Authoritative compatible percentages — FAIL for mixed existing-graph path | Evidence-only compatible division is bounded, but R2-F2 allows unresolved/unknown-status scalars to accompany definitive graph candidates without review. |
| 9 | Decimal authority — PASS | Sole existing graph/analysis owner; strict scalar float rejection, exact compatible-unit division, direct/indirect aggregation and inclusive threshold tests. |
| 10 | ML semantic boundary — PASS | New tagger has deterministic semantic rules only and explicit ML_RUNTIME_NOT_AVAILABLE; experimental protocol unwired, no arithmetic/external model/legal determination. Existing separate ubo-advisory-linear-v1 is unchanged. |
| 11 | Explainable tags — PASS | Bounded evidence IDs, reason/rule/case/evidence versions, confidence and provenance; semantic fixture execution, no fabricated trained-model metrics. |
| 12 | Specific UBO blockers — FAIL in uncovered mixed path | Blanket NOT_IMPLEMENTED removed and tested specific deficits retained, but R2-F2 emits no deficit/review blocker for unresolved group evidence beside a valid graph. |
| 13 | Review & Send final — PASS | Seven disclosure DOM order places Review & Send last. Unavailable explanation remains visible/compact; explicit confirm required; configured browser verifies finality. |
| 14 | Simpler collapsible blockers — PASS structurally | Stage-local interventions, optional technical details, one primary ownership intervention, history collapsed; hover legibility defect is R2-F4. |
| 15 | Active/history/completed semantics — FAIL in accessible projection | Backend history and zero-active completed result preserved; visual completion100% disagrees with accessible progress11/12 in R2-F5. R2-F1 retains obsolete current ownership. |
| 16 | Accessibility/responsive — FAIL | Keyboard/320px/200% zoom/no-overflow suites pass; actual Chromium hover contrast1.264:1 fails and ARIA progress disagrees with visible result. |
| 17 | Golden unchanged — PASS in configured regression | Golden zero exception interventions, one explicit final confirmation, COMPLETED; local Mock only. All configured browser selectors pass. |
| 18 | Authorized external boundary — PASS in bounded inspection | Added discovery only fixed official Mock OAuth/read operations, no new runtime route/endpoint; sanitized receipt24 attempts / 22 responses, two TLS failures preserved. Gate provider calls0. |
| 19 | GoldTier chronology — PASS within change scope | Existing ledger/search ordering/call-stopping/no-replay owners retained; no target mapper/connector/ledger implementation changes. Retained recovery state was never accessed or modified. |
| 20 | Secrets/tokens absent — PASS for bounded checks | Secret checker and explicit task-owned artifact/source review; no raw private document/payload/credential, token/header or private source path copied here. This is bounded evidence, not universal proof. |

## Contract and Integration Findings

Current source and tests, ownership/ACRA/persistence/automation/target contracts, ADR-008, D-018/D-054/D-061/D-062 and Q-004/Q-012 establish the review boundaries. The private catalogue availability is resolved. It is candidate-discovery input only, not authority for a new partner/member/group/capital operation, denominator, control rule or legal UBO. Current sanitized discovery documents all supported attempts; it is not deferred because an exact duplicate-download suffix was absent.

Official Mock implementation evidence totals 24 attempts (6 OAuth / 18 GET), 22 HTTP responses and two pre-HTTP read TLS failures. Five additional basic identities had no currently supported applicable quantitative method; the capital example's basic identity was empty. Fresh Garden passed through existing canonical acquisition/normalizer/tagger/sole analysis in memory with role evidence only. The shareholder example had units but no canonical basic identity or compatible authoritative denominator; unsupported member/group shapes were rejected. No capital endpoint was guessed, no cross-UEN synthesis made, and no legal/ML/Production/Live success claimed. These are inspected implementation receipts, not newly executed external evidence from this gate.

Later dependencies remain Q-012 complete operation/status/denominator/control authority, Q-004 complete legal/controller/production policy and real GoldTier/PingFed contract/security authority. They do not justify current false-success or cache defects. No suitable numerical sample is demanded contrary to the user's clarification.

### R2-F2 — P2: mixed scalar evidence can still bypass review

Owner: `apps/backend/app/services/ownership_analysis.py:813–825` (classification at 856 onward). The added diagnostic precondition recognizes unmatched SHARE_UNITS/DIRECT_PERCENTAGE, CONFLICT, unbound identifiers and OTHER legal form. It omits bound GROUP_SHAREHOLDER, UNKNOWN, unresolved membership/economic/control evidence when graph relationships already exist. A matching percentage edge also masks UNKNOWN/WITHDRAWN scalar activity status.

The coordinator independently ran Python -B stdin using the existing synthetic `evidence`, `source` and `build_system` helpers: construct valid authoritative direct60% source/graph; append bound PERSON_B GROUP_SHAREHOLDER with raw UNKNOWN/no numeric amount; load through a source provider and analyze. Observed `ANALYZED`, issues `[]`, candidate `PROVISIONAL_UBO_CANDIDATE / MET / 60.0`. The narrow independent specialist also reproduced membership/economic/control/unknown and matching direct-percentage unknown/withdrawn-status variants. No source edit or provider call was used.

`OWNERSHIP_UBO_PROFILE.md:165–166` requires mixed valid/unresolved evidence to remain review required with indeterminate candidate status. The newly retained source evidence must not disappear semantically merely because a valid graph exists. This is residual incompleteness in round-1 F3's owning boundary, not a request for new sponsor policy. No target dispatch bypass was executed or claimed.

Required fix: apply one complete evidence eligibility/review assessment before final graph candidate classification, preserve graph/scalar diagnostics, and treat unresolved supported forms/groups/status contradictions truthfully. Add adverse mixed cases and retain direct/exact-threshold behavior. Officer/director-only labels must remain bounded and must not become owners merely to resolve this issue.

## Tester and Adversarial Findings

All executions below used the frozen candidate identity. Coordinator evidence is independent from the implementation handoff.

| Independently executed lane | Command / result |
|---|---|
| Focused backend | `python -B -m pytest apps/backend/tests/test_phase24_identity.py apps/backend/tests/test_phase24_ownership_evidence.py -o addopts= -q -p no:cacheprovider --tb=short`:71 passed,1 deprecation warning,8.33s. |
| Full backend | Same pytest options on `apps/backend/tests`:1606 passed,41 guarded physical skips,4 warnings,227.76s. Physical skips are not physical PASS. |
| Physical Mongo | `python -B scripts/run_physical_mongo_tests.py --timeout-seconds 900`:9 suites,41 collected / 41 passed,0 skips/errors. Only generated allowlisted disposable databases; separate targeted R2-F3 probe below also cleaned. |
| Frontend | `npm test -- --run`:34 files / 396 passed,8.14s; existing act/layout-effect warnings. Initial sandbox Vite ancestor/config access denial executed no tests; narrowly approved rerun supplied PASS. |
| Type/build | `npm run typecheck`, `npm run build`:PASS, Vite126 modules. Existing dependencies/lockfile unchanged; ignored outputs only. |
| Ruff | `python -B -m ruff check apps/backend scripts tests --no-cache`:PASS. |
| Strict mypy | `python -B -m mypy app --no-incremental --cache-dir .mypy_cache` from backend:115 files PASS. Initial Windows NUL cache command produced mypy internal error; valid ignored-cache rerun supplied PASS. |
| Configured real browser | `python -B ../../scripts/run_e2e.py --timeout-seconds 60` from frontend:29 configured selectors / 31 instances PASS,308.000s, isolated owned local Mock HTTP/process lifecycles and guarded network. Golden/Garden/identity/roles/routes/keyboard/viewport/zoom regression. |
| Contracts | `python -B -m unittest discover -s tests/contract -p test_*.py`:44 passed. |
| Root regressions | Per-file CI-style `python -B -m unittest discover -s tests -p test_FILENAME.py`:243 non-lifecycle tests PASS. Corrected selection resumed remaining modules after lifecycle prerequisite failure; never one uninterrupted aggregate PASS. |
| Governance/security | Six scripts:check_project_state,check_architecture,check_tooling_config,check_policy_authority,check_external_provider_readiness,check_secrets — allPASS. |
| Hygiene/identity | `git diff --check`:PASS; explicit UTF-8 whitespace inspection of all manifest Markdown:PASS; all 60 byte hashes/status-path-set/contentidentity match at entry and final verification. Initial implicit Windows text decoding failed; UTF-8 rerun supplied whitespace evidence. |
| Additional falsification | Coordinator direct mixed-source probe and real physical R2-F3 probe; independent frontend specialist real frozen component/cache rendering; coordinator and specialist isolated Chromium computed hover contrast. These found defects despite suite PASS. |

Missing/unexecuted lanes are explicit. The unchanged Windows lifecycle harness was accidentally included by an incorrect exclusion filename:23 tests attempted,20 setup failures from unrelated port8000listener (3 did not fail). No unrelated process was stopped. This is infrastructure-blocked lifecycle evidence, not a product PASS or a Phase24 startup-change defect; startup composition source did not change. Pytest-only root preflight 3 and root physical-parser 17 were not rerun by this reviewer; implementation's 3/17 PASS remains separately attributed. No ten-minute imported-module aggregate was attempted. Dependency checks and private GoldTier example validation were not newly executed; private archives remain NOT VALIDATED. No network smoke was rerun, as gate authority forbids external calls. Publication `pre_pr_check.py` was not run on the intentionally uncommitted handoff; its unit tests are not that publication gate.

Round-1 F1 capacity/full-value validation is repaired on inspected/executed paths:16 accepted corrections,17th rejected under lock before registry/Search/state change; invalid constructed writes rejected and stored case remains readable after physical restart. Round-1 F2 A→B→A evidence does not reactivate and a newer generation replacement preserves history/CAS. Round-1 F4 nested/repeated-party scalars retain immediate owned-parent binding and distinct edge references. F3 combines graph/scalar issues before candidate classification for the added covered forms, but R2-F2 remains.

Adverse fixture edits preserve original assertions: constructed malformed policy now rejects at create, then separately corrupted-read injection still proves fail-closed preview/dispatch; empty ownership retains both graph and scalar issues; UTC manual fixture dates address demonstrated test-time midnight disagreement without changing runtime date policy.

## Code and Architecture Review

### R2-F1 — P1: corrected UEN publishes with obsolete ownership in the browser

New caller: `apps/frontend/src/pages/CaseDetail.tsx:707–714`; mutation dispatch at307–308; existing effect `apps/frontend/src/caseQueries.ts:306–312`. The new registry-identity correction uses legacy `identity-recheck`, which publishes the updated summary and invalidates intelligence but neither cancels nor invalidates/refetches identity-bound ownership/documents. The same case query key persists. Ownership/documents are refreshed by polling only for RUNNING/RESUMING (`CaseDetail.tsx:256–275`), so a successful correction returning WAITING_FOR_REVIEW/PENDING_INPUTS/TECHNICAL_FAILURE can retain old data.

The independent frontend specialist loaded actual frozen CaseDetail/api/caseQueries through in-memory TypeScript transpilation in jsdom/React, seeded actor/case ownership old-analysis and OLD_UEN candidates, used the real Edit UEN form, and returned a successful version 2 WAITING_FOR_REVIEW correction with UEN202400009I. After mutation and opening Ownership, actual DOM still showed OLD_UEN/Candidate One; NEW_UEN absent; cache old-analysis remained not-invalidated. Requests were correction POST and intelligence GET only, with zero ownership/document reads. This is component/cache execution, not an external or full HTTP browser reproduction. Source trace corroborates it. Existing E2E correction tests API-read the new owner but assert only a generic path-explorer heading in the UI, so their PASS misses the stale rendering.

Reproduction refinement: the specialist reran the same actual component/form path using `createSessionQueryClient()` production settings: staleTime 45,000ms, refetchOnWindowFocus false, refetchOnReconnect true, query retry 1, mutation retry false. The seeded case had one event and the correction response two; submitted expected_case_event_count was 1, so the probe does not depend on an invalid zero event count. Existing isolation fixture actor CLIENT_ONBOARDER had CASE_ACCESS/POLICY_VIEW; registryProviderMode was unspecified, old cached ownership was LOCAL/DECIMAL_GRAPH_ENGINE, version 4, and a new version 6 ownership response was available in the fetch mock. Actual React Edit UEN submission published UEN 202400009I but retained/rendered old-analysis and OLD_UEN candidates, no NEW_UEN candidate, ownership isInvalidated false; two total requests, zero ownership/document requests. No focus/reconnect/remount occurred. Earlier Infinity-stale fixture probe is superseded by this production-settings execution. In-memory transpilation emitted no files; fetch mocked all known local routes and rejected every other route, so no real network call occurred.

A further source-proved limitation matters to remediation: `caseQueries.ts:239–243` retains previous versioned evidence when incoming is null. The ownership query structural-sharing function and CaseDetail refresh/poll setters use this helper. A legitimate no-current-ownership GET after rebind therefore cannot retire old analysis through ordinary invalidation/refetch alone; explicit identity-bound retirement is necessary. This null-response branch and delayed-old-response consequence were inspected, not separately runtime-reproduced by this gate. Preserve monotonic same-identity publication while making cross-identity evidence ineligible.

Current correct identity beside a previous company's ownership can mislead the RM's review. Backend target confirmation remains authoritative; no target security bypass is claimed. Required fix: use the existing central query owner to cancel/retire and refresh identity-dependent supporting data before presenting it as current under the new identity. Prove post-correction rendered new identity/root/candidates, terminal/waiting outcomes and delayed old GET protection without reload.

### R2-F3 — P2: same-UEN independent loaded evidence cannot continue in Mongo

Owner: `apps/backend/app/persistence/repositories.py:248–257` versus service currentness `apps/backend/app/services/ownership_analysis.py:1098–1114`. Independent non-registry evidence intentionally remains current when a correction verifies the same UEN without an intervening identity change. Mongo save nevertheless demands exact correction-generation equality for every record.

Coordinator independently executed a targeted physical probe using task-owned loopback Mongo and a newly generated allowlisted p12 database. Created synthetic case/independent MOCK_OWNERSHIP LOADED generation 0; successful ENTERED same-UEN verification produced parent generation 1. Service currentness was True. Stored that real parent/ownership envelope, then actual MongoOwnershipAnalysisRepository rejected ANALYZING save with OwnershipRepositoryConflictError before replace. Snapshot stayed unchanged. Equivalent memory service analyze returned ANALYZED. Disposable database cleanup absence was True. No retained/provider state was accessed; URI never printed/persisted. Specialist's earlier fake-store guard probe agrees, but the physical result is the stronger evidence.

Required fix: reconcile persistence guard/currentness semantics under existing lock/CAS. Preserve safe independent same-UEN continuation while still rejecting registry-derived stale generations, real identity changes, A→B→A reuse, deletion/stale writers. Cover LOADED → analysis continuation in memory and physical Mongo, not only terminal-result retrieval.

### R2-F4 — P2: disclosure headings become unreadable on hover

Owner: `apps/frontend/src/styles.css:3964–3977`, interacting with existing `button:hover:not(:disabled)` at1004. New heading button inherits dark foreground and transparent base background; generic hover's higher specificity supplies dark green without a compatible foreground.

Coordinator independently ran isolated pinned Chromium with frozen stylesheet import order (styles.css then design-system.css), actual disclosure button markup, and all network routes aborted. Computed normal foreground rgb(18,41,31), transparent background; hover foreground `#12291f`, background `#0e3d2c`,26px/600; calculated contrast **1.264081629:1**, below even 3:1 for large text. Specialist independently reproduced the same values. All seven disclosure heading buttons use this selector. The dark screenshots reflect hover, not inherently open-state styling.

Required fix: make disclosure normal/hover/focus foreground/background deliberate at the existing presentation owner and verify computed contrast in each state. Keep semantic button/keyboard/focus behavior and responsive layout.

### R2-F5 — P2: completed visible progress disagrees with accessible progress

Owner: `apps/frontend/src/pages/CaseStatePanels.tsx:354` and386–388. New code forces visible percentage/bar to100% for COMPLETED, while unchanged ARIA numerator/denominator/text still count all pipeline stages including the unresolved outside-POC human approval.

Specialist rendered actual frozen OnboardingProgressPanel in memory with completed summary/11 COMPLETE+HUMAN_APPROVAL REVIEW_REQUIRED. DOM visible text:Progress 100%,Active issues 0. ARIA:now 11, max 12,11 of 12 complete/currentHumanapprovalReviewrequired (~92%). Before the new forced percentage, visible92% agreed with those attributes. Required fix: use one explicit POC-completion progress basis for visual and accessible values/text, while preserving truthful outside-POC legal/human-approval distinction. Add completed accessible assertions.

The existing unresolved human-approval explanatory label alone is **not** a finding: accepted CompletedOverview/POC boundary copy distinguishes successful POC submission from regulatory approval/Ready-for-Approval. Do not mark legal approval complete to repair the progress mismatch.

### Owner and scope assessment

One bounded semantic tagger is proposed by ADR-008; existing registry/canonical/services/persistence/query/ledger owners remain. No second arithmetic, authorization, persistence, cache, provider router or target replay owner; no package/lockfile churn, direct ACRA-to-GoldTier mapping, dormant-provider composition, hierarchy/related-party activation or autonomous approval. Specific defects above belong at those existing boundaries.

Changes are explicit: API/types YES; optional durable fields within existing v7 envelope YES; source connector/normalization YES; configuration/dependencies NO; identity/evidence business behavior YES (inclusive threshold unchanged); source mapping YES/GoldTier target mapping NO; auth-sensitive mutation YES through existing RBAC/team/lock owner; architecture YES (semantic tagger owner); provider status/classification NO; runtime behavior YES. Tagger runtime-unavailability wording is scoped to source-semantic classification; the separate existing ubo-advisory-linear-v1 remains unchanged and is not an approved source-semantic runtime.

## Security Review

R2-F1 is a current data-integrity exposure to an authorized RM, not demonstrated cross-team disclosure; R2-F2 is non-definitive evidence presented definitively; R2-F3 blocks legitimate continuation without corrupting storage. Existing CSRF/auth/team capability, inaccessible404 and locked reauthorization are preserved and tested. New safe browser identity-correction receipts exclude old private bundles. No route-to-Mongo bypass, new external model, sensitive browser storage, raw exception/payload/token projection, TLS bypass or fallback was found in the changed boundaries.

Gate external provider calls0; .env accesses0; private catalogue contents copied0; retained GoldTier recovery-state access0. Supported-pattern secret scan and explicit new artifact/source review pass. Existing Mock ledger safety tests and full regression pass; those are not evidence of production interoperability, legal/control approval or sponsor endpoint authorization.

## Required Fixes

1. R2-F1: central identity-mutation supporting-query cancellation/retirement/refetch and rendered same-current-identity proof, including late old responses.
2. R2-F2: complete mixed scalar review/eligibility before final candidate classification, with groups/unknown/interests/control/status adverse cases.
3. R2-F3: align safe independent same-UEN continuation with Mongo identity/CAS guards and execute memory/physical parity.
4. R2-F4: disclosure hover/focus contrast at the owning CSS boundary with rendered-state evidence.
5. R2-F5: consistent completed POC progress basis for visual and ARIA values/text.

No fix was made by this reviewer. The root coordinator owns the remaining permitted remediation round, affected evidence, new freeze and fresh independent gate. Preserve this FAIL and manifest before changing reviewed content; do not weaken existing assertions. Discovery insufficiency, Live/legal contracts and unavailable unchanged Windows lifecycle infrastructure are separately classified limitations, not invitations to fabricate data or broaden scope.

## Readiness

Phase24 is not accepted and is not ready for the next phase, PR or publication. Any reviewed-content change requires fresh independent review of its exact bytes. The current FAIL applies only to the identity above.

Live ACRA readiness: not verified/not claimed. Official Marketplace Mock observations remain Mock. Real GoldTier/PingFed integration and legal/final approval readiness: not verified/not claimed. No commit, push, PR, merge, publication or next phase is authorized by this report.

## Git Status and Reviewed Paths

At entry and final pre-report:44 tracked status modifications (43 effective diffs plus the exact-byte-frozen Decision Log line-ending status),18 untracked status paths including excluded manifest/report; nothing staged. Branch/HEAD/origin-main unchanged. Status path set exactly equals60 reviewed paths plus2 explicit exclusions. SHA256 of every exact candidate file matched before and after review. The report and its current manifest are self-excluded; prior ROUND_1 report/manifest are included historical evidence.

Only this assigned report was authored. No source/test/config/ordinary-doc write, Git mutation, dependency installation, external provider call or protected retained-state access occurred. Tests/builds used permitted ignored generated outputs/caches where unavoidable; no new reviewed file was introduced. Task-owned Mongo container remains running for coordinator cleanup.

The complete 60 path set follows; per-path exact byte digests and deterministic compact-JSON algorithm are recorded in the candidate manifest.

- `.ai-pipeline/001_planner/PHASE_24_PLAN.md`
- `.ai-pipeline/reports/PHASE_24_CANDIDATE_MANIFEST_ROUND_1.json`
- `.ai-pipeline/reports/PHASE_24_IMPLEMENTATION_HANDOFF.md`
- `.ai-pipeline/reports/PHASE_24_QUALITY_GATE_ROUND_1.md`
- `apps/backend/app/api_models.py`
- `apps/backend/app/composition.py`
- `apps/backend/app/connectors/acra_bizfile_sandbox.py`
- `apps/backend/app/connectors/ownership.py`
- `apps/backend/app/connectors/registry.py`
- `apps/backend/app/connectors/registry_ownership.py`
- `apps/backend/app/domain/models.py`
- `apps/backend/app/domain/ownership.py`
- `apps/backend/app/domain/ownership_evidence.py`
- `apps/backend/app/domain/registry_legal_form.py`
- `apps/backend/app/main.py`
- `apps/backend/app/persistence/mongo_case_store.py`
- `apps/backend/app/persistence/repositories.py`
- `apps/backend/app/services/authorization.py`
- `apps/backend/app/services/blocker_decision_policy.py`
- `apps/backend/app/services/onboarding.py`
- `apps/backend/app/services/ownership_analysis.py`
- `apps/backend/app/services/ownership_evidence_tagger.py`
- `apps/backend/app/services/ownership_repository.py`
- `apps/backend/app/services/repository.py`
- `apps/backend/app/services/zero_touch_orchestration.py`
- `apps/backend/tests/test_acra_api_marketplace_mock_connector.py`
- `apps/backend/tests/test_blocker_decision_policy.py`
- `apps/backend/tests/test_goldtier_xpi_sandbox.py`
- `apps/backend/tests/test_phase10_registry_acquisition.py`
- `apps/backend/tests/test_phase13_auth_rbac.py`
- `apps/backend/tests/test_phase24_identity.py`
- `apps/backend/tests/test_phase24_ownership_evidence.py`
- `apps/backend/tests/test_provider_identity_real_mongo.py`
- `apps/backend/tests/test_zero_touch_exception_remediation.py`
- `apps/frontend/e2e/authenticated-zero-touch.e2e.ts`
- `apps/frontend/e2e/garden-happy-path.e2e.ts`
- `apps/frontend/e2e/phase24-identity.e2e.ts`
- `apps/frontend/e2e/responsive-layout.e2e.ts`
- `apps/frontend/e2e/stage-disclosures.ts`
- `apps/frontend/e2e/zero-touch-exception.e2e.ts`
- `apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx`
- `apps/frontend/src/api.ts`
- `apps/frontend/src/pages/CaseDetail.tsx`
- `apps/frontend/src/pages/CaseStatePanels.tsx`
- `apps/frontend/src/pages/HumanInterventionPanel.tsx`
- `apps/frontend/src/pages/IdentityCorrectionForm.test.tsx`
- `apps/frontend/src/pages/IdentityCorrectionForm.tsx`
- `apps/frontend/src/pages/OwnershipPathExplorer.tsx`
- `apps/frontend/src/pages/StageDisclosure.test.tsx`
- `apps/frontend/src/pages/StageDisclosure.tsx`
- `apps/frontend/src/styles.css`
- `apps/frontend/src/types.ts`
- `docs/ARCHITECTURE.md`
- `docs/PROJECT_STATE.md`
- `docs/contracts/ACRA_MOCK_API_PROFILE.md`
- `docs/contracts/OWNERSHIP_UBO_PROFILE.md`
- `docs/decisions/ADR-008_OWNERSHIP_EVIDENCE_TAGGING.md`
- `docs/decisions/DECISION_LOG.md`
- `docs/development/PHASE_24_ACRA_DISCOVERY.md`
- `scripts/phase24_acra_mock_discovery.py`
