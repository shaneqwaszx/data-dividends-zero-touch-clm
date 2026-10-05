# Phase27 implementation checkpoint

Date: 2026-10-05. Assigned scope: final delivery/UAT, then architecture/demo/closeout,
then proportional final regression and independent acceptance before local commit.
Current outcome: **27A grouped AGENT_EXECUTED_UAT recorded and product retests passed; BarrierA pending**.
27B/27C have not begun. No independent Phase27 verdict or commit exists yet.

## Task identity, capability and scope

- Worktree: C:/Users/shane/.codex-clean2/worktrees/phase27-final-delivery-closeout/data-dividends-zero-touch-clm.
- Branch: feat/phase27-final-delivery-closeout.
- BASE_SHA/current source HEAD/fetched main/origin/main:
  4ee8819d7404d6442e064fd60dcee03ccc84cf11 (PR #70).
- Behavioral source tree: febc43b740e3b37307c0b499a373f077eefa8ea9.
- Tested content: unchanged product source from that HEAD plus initial uncommitted DOCS_ONLY
  delta; later source-tested UI fixes are identified below; raw candidate identities will be frozen for each later independent gate.
- Primary runtime identifies this agent as Codex; exact model label is not exposed
  in a verifiable tool result. User ceiling/request: GPT-6.1 Sol / High; no Ultra/xhigh
  routing or subagent has been used. Fresh gate reviewers remain NOT_RUN.
- Main checkout was clean, main==origin/main==expected PR70 baseline after fetch.
  Created a new host-managed worktree/exact user-named branch; existing worktrees
  preserved. Coordinator alone owns Git mutations. Index empty; no commit/push/PR.
- Exposed tools used: PowerShell commands and managed-worktree API. Independent agent
  review is available for the assigned barriers. Effective worktree/test access
  required sandbox escalation; first non-escalated fetch failed to write FETCH_HEAD,
  unchanged approved fetch succeeded. That first attempt is not passing evidence.
- Runtime: normal checkout .venv Python3.12.10 reused against this worktree source;
  Node22.23.3/npm10.9.9; pinned frontend installed via offline npm ci (152 packages).
  No tracked dependency/lockfile change. Global Python lacked pytest; it was not used
  to claim backend execution. Local Chromium exercised through configured Playwright.
- Reserved ports8875/4273 were free at start; harness launches/stops only owned processes.
  Database resource: NONE. Dotenv disabled; no protected settings/provider credential
  read. Tesseract absent from PATH; actual host OCR NOT_RUN.

Canonical owners: existing document/reconciliation/ownership/policy/authorization/
orchestration/target-ledger/repository/query-cache owners remain intact. Initial work edited task-owned prose; subsequent bounded UAT remediation also changed
only two frontend presentation owners and a focused test. No new owner/boundary/ADR is required. The explicit assignment is scope
authority; no matching Phase27 planner file exists under .ai-pipeline/001_planner.
Product remediation budget2 rounds; documentation2 rounds at B; final1 round.
No external provider execution, original database contact or feature expansion is allowed.

## 27A delta and truth sync

Corrected active main metadata from pre-publication PR69 to merged PR70 in PROJECT_STATE,
ARCHITECTURE and PHASE_27_HANDOFF; removed active Phase26-pending descriptions.
Historical source/provider/test/gate identities remain unchanged. PR69-to-PR70 diff
contains16 docs/evidence files only. Current schema remains9/strict legacy1..8.

Created [truth inventory](../../docs/demo/PHASE_27_TRUTH_INVENTORY.md), updated the
[existing matrix](../../docs/demo/FINAL_UAT_ACCEPTANCE_MATRIX.md), and added the
[human checklist](../../docs/demo/PHASE_27_MANUAL_UAT_CHECKLIST.md) with21 rows covering
all19 requested journeys plus explicit Director/HR boundary observations. Includes safe
memory/offline startup, fixture grouping, exact expected/actual/status/defect fields.
All human outcomes NOT_RUN. Scratch manual inputs are controlled synthetic text in
ignored .runtime/phase27 only; no new tracked product/fixture file is introduced.

API/type, schema, connector, persistent configuration, business rule, mapping,
auth/security, architecture owners/dependencies, provider status and runtime behavior:
**UNCHANGED**. Architecture prose baseline/evidence attribution updated only. Broader
27B architecture/diagram/demo/question/presentation/closeout work waits for BarrierA.

## Newly executed automated pre-UAT

All tests use this worktree's unchanged PR70 source. Browser fixtures are offline
Mock/LOCAL or synthetic offline XPI protocol; none is a new Sandbox observation.
Manual statuses are independent and are not changed by this evidence.

| Check | Command / selection | Executed result |
|---|---|---|
| Focused backend | normal .venv python -B -m pytest -o addopts='' -p no:cacheprovider --basetemp .runtime/phase27/pytest, nine files listed below, -q |133 passed,0 skips,1 existing Starlette/httpx deprecation warning,28.50s;exit0 |
| Focused frontend | npm.cmd test -- --cache=false, four files listed below |70 passed/4files;exit0 |
| Guarded browser | normal .venv python -B scripts/run_e2e.py --backend-port 8875 --frontend-port 4273,15 selections below, separate fresh lifecycles |15 passed/15selectors;external provider calls0;exit0 |

Backend selections under apps/backend/tests: test_s1_pipeline_projection.py,
test_s1_date_filters.py, test_s2_ownership_intelligence.py, test_s3_submission_status.py,
test_s3_target_activity.py, test_s3_retained_recovery.py, test_phase16_registry_cache.py,
test_phase24c_policy.py, test_document_processing.py.
Frontend under src/pages: S2OwnershipReview.test.tsx, S3SubmissionStatus.test.tsx,
RegistryProvenancePanel.test.tsx, DocumentEvidencePanel.test.tsx.

| Browser grep selector | Fixture flags | Result |
|---|---|---|
| Slice B Garden partnership | --registry-demo garden-partnership |1 passed |
| Slice B second synthetic company | --registry-demo synthetic-cache |1 passed |
| Slice B Merlion fresh cache | --registry-demo synthetic-cache |1 passed;0 additional ACRA |
| S1 wrong UEN retains uploaded document | default isolated Mock |1 passed |
| Slice C legal name discrepancy | default isolated Mock |1 passed |
| S2 creator edits calculable | --garden-protocol |1 passed |
| S2 document proposals require | --garden-protocol |1 passed |
| Slice E HR and Director same impact | default isolated Mock |1 passed |
| Phase24C policy approval and accessible layout 320 | default isolated Mock |1 passed |
| S1 logout and interactive role changes | default isolated Mock |1 passed |
| S1 case creation date controls | default isolated Mock |1 passed |
| S1 executing workspace is inert | default isolated Mock |1 passed |
| S3 normal Sandbox submission | --sandbox-demo success |1 passed;offline only |
| S3 uncertain Policy checks | --sandbox-demo uncertain-policy |1 passed;identity check does not resolve/replay Policy |
| S3 definitive Policy failure | --sandbox-demo failed-policy |1 passed;no retry/false success |

All selectors use the unmodified harness/guards/deadlines. The first Garden execution
is the directly captured successful command; the remaining14 commands and sanitized
summaries/logs are retained in ignored .runtime/phase27/browser.json and named logs.
Their test-source assertions reject browser external violations and check failure/
uncertainty no-replay. Current browser proof uses actual backend/frontend/Chromium
processes and HTTP. These counts describe this run, not accumulated historical coverage.

## Additional27A verification and self-review

- Strict synthetic legacy-reader/current-schema/access/security plus explicit absent-OCR
  test: normal .venv pytest with addopts cleared/cache disabled and separate task temp,
  test_s2_persistence_security.py plus
  test_s2_local_ocr.py::test_absent_runtime_is_explicit_and_native_text_remains_usable:
  168 passed,0 skips,1 existing deprecation warning,29.70s;exit0. This is local codec/
  security evidence, not physical Mongo or actual OCR. The two backend runs total301
  executed cases; their individual133/168 inventories remain distinct.
- Contract discovery:44 unittest tests passed;exit0;1.288s.
- Governance/security:124 unittest tests passed;exit0;29.030s. Modules: test_dev_context,
  test_check_project_state, test_check_architecture, test_check_policy_authority,
  test_check_external_provider_readiness, test_check_secrets,
  test_validate_external_provider_evidence, test_validate_goldtier_examples,
  test_phase_07_delivery_assets. PYTHONPATH targets this worktree/apps/backend.
- Six configured scanners: check_project_state, check_architecture, check_policy_authority,
  check_external_provider_readiness, check_tooling_config and check_secrets: each PASS.
- Both scratch manual inputs passed the normal DocumentMediaRouter -> local provider
  path: each four populated identity fields/two ownership proposals, no network.
  First direct-provider probe omitted the TXT router/extracted_text boundary and failed
  DOCUMENT_STRUCTURE_INVALID; corrected normal-boundary probe passed unchanged inputs.
  That first harness attempt remains failed evidence, not a product defect or fix.
- Complete four-file tracked diff and three new prose files were reviewed by the
  implementer against assigned27A scope. No executable/config/contract/fixture delta.
  Preserved original mixed line endings so no unrelated formatting churn remains.
  Explicit new Markdown whitespace/local-link checks, tracked/index diff whitespace,
  and final secret/pathset checks accompany this final checkpoint.
- OS listener query after browser cleanup:0 listeners on8875/4273. No database
  process/connection was started. All15 guarded lifecycles stopped their owned processes.

Evidence strength: direct automated local pre-UAT, gradeB for that bounded lane;
whole Phase27 remains needs-verification/gradeC pending independent barriers.
The completed agent UI session is separately recorded below. Metadata aligns with PR70; no new business complexity, fallback or state owner.
No independent verdict is inferred from implementer review or passing governance.

## Current27A agent UI evidence and bounded remediation

Owner authorization replaces personal execution with AGENT_EXECUTED_UAT. Existing
RM/Director/HR credentials enabled normal sign-in; no credential values are included.
The [21-row results](../../docs/demo/PHASE_27_AGENT_UAT_RESULTS.md) record16 PASS,
0 FAIL,5 NOT_RUN and0 human-executed rows. All row prerequisites were assessed;
OCR, Garden, numerical cache counts and offline F/U transport lanes remain explicit
NOT_RUN. The cache UI flow was visibly executed through send but its required
numerical counter is unavailable in the normal launcher, so no full-row PASS.
No automated historical evidence becomes UAT evidence.

Main owned demo session5ed6f9ae used unchanged PR70 product source. Retest session
8d2bb519 used this worktree with two bounded FRONTEND_UI fixes and its regression.
Both normal controlled launcher5173/8000, explicit memory/Mock/local IDP settings;
no original database, external ACRA or external GoldTier access. Startup inherited
freshness mismatch was CONFIGURATION, corrected before UAT with explicit7776000.
Native date/locator/file-path mistakes were corrected UAT script issues, not code fixes.

Post-fix checks:44 focused frontend tests (3 files);505 full frontend tests (41 files);
npm typecheck and build PASS. Existing React SSR/act warnings and >500kB Vite advisory
are reported, not treated as a clean-warning claim. Two new configured real-HTTP
browser runs PASS: Phase24C320 policy layout and S2 document proposal/source bindings
(with --garden-protocol); isolated owned ports8875/4273, external network guards,
no provider calls. These complement actual visible product retests and do not supply
UAT PASS. The first regression-writing command had a wrong relative path; its41
existing tests passed but it did not add the regression. Corrected path added3
capability-action cases; subsequent44/505 results are the fresh post-change evidence.

API/types/schema/connectors/config files/business rules/mappings/auth/security/
architecture owners/provider classifications: unchanged. Runtime/UI behavior changed:
unsupported ownership upload affordance removed by consuming backend evidence action;
classic-scrollbar narrow page width now fits. No cache owner or mutation retry change.
Physical Mongo and actual OCR are NOT_RUN/not triggered by this UI delta. No .env
read or credential file was created. No commit/push/PR/merge has occurred.

Next: freeze current content for fresh independent GPT-6.1 Sol / High BarrierA.
P0/P1/P2 independently remain NOT_ASSESSED until review; implementer-confirmed
product failures are fixed/retested. Only exact PASS authorizes automatic27B, then
27C/final independent gate and local commit. Product remediation1/2 rounds used.

## Bounded product remediation round1

U27-05 offered upload on ANALYZED/pre-send cases while the canonical intake owner accepts only PENDING_INPUTS, retained identity/search intake or current OWNERSHIP/REVIEW_REQUIRED. This is a PRODUCT presentation defect, not stale evidence. The owner-generated intervention already declares OWNERSHIP_UPLOAD only for supported current review; CaseDetail now supplies its existing optional upload callback only when that declaration is present. Manual graph editing remains separately authorized. No backend rule, authorization, cache/mutation behavior or API changed. Supported discrepancy intake starts with the synthetic TXT to reach OWNERSHIP/REVIEW_REQUIRED; the first clean-PDF-then-upload setup was also a TEST/UAT SCRIPT precondition error, preserved in the results.

U27-18: Windows classic vertical scrollbar takes15px at320px; body min-width320 forces body beyond document clientWidth305. Canonical stylesheet removes only that floor; internal table scrolling remains. Decision: code-change at the existing presentation owners. No-change would retain false affordances/overflow; expanding intake would change unrelated lifecycle semantics. Patch-shape: existing optional callback wiring to the authoritative action projection, no new capability/owner/fallback. Ripple boundary: backend projection -> CaseDetail -> existing form, plus shared body layout across roles. Preserve manual-edit capability and fail-closed backend intake. Complexity: local-fix-without-new-responsibility, edit-in-place. TDD Mode: off (default), Route: skipped; concrete failing UI reproduction plus focused and full post-change regression and visible retest are required. No automatic strict TDD is inferred. Confidence before retest: B, proximate upload symptom explained by the unconditioned callback; authoritative intervention denies that upload. Runtime source identity must change to this worktree before retest.

## Barrier A prose remediation

Initial independent gate: PASS WITH MINOR FIXES, P0/P1/P2=0/0/0, P3-27A-01.
Twenty-four newly corrupted text lines in ARCHITECTURE, PROJECT_STATE and agent
UAT results were repaired with explicit UTF-8 byte reads/writes, preserving line
endings. Cause: earlier Windows default-codepage reads followed by UTF-8 writes.
No product/test/runtime change; product remediation budget remains1/2 rounds used.
Initial report remains historical and unchanged. Repaired candidate requires a
fresh independent exact PASS before27B.

## Phase27B documentation synchronization

BarrierA fresh recheck exact PASS, P0/P1/P2/P3=0/0/0, manifest
64a750a7291e9d29f105a43dc7f11b389a4504c461c7ab06a18ddfa61f4af96c.
Initial minor-fix report and recheck remain unchanged. User instruction explicitly
authorizes immediate27B/C following exact barriers and local commits after finalPASS.

Updated canonical existing ARCHITECTURE/PROJECT_STATE/PHASE27_HANDOFF and final
architecture, runbook, limitations/questions; created only requested FINAL_PROJECT_CLOSEOUT.
Current-main metadata remains PR70; unmerged UI fixes clearly accepted branch content.
C4L1/L2/L3 in existing final architecture, canonical end-to-end flow reused, five
additional decision/recovery views cover wrong-UEN/document/ownership/target/policy.
Application-owned orchestration explains event/owner/decision/provider/evidence/blocker/
resume and lock/currentness/no-replay/recovery, without claiming general BPM execution.
No owner/dependency/provider change or new ADR required.

Runbook now uses controlled batch launcher and truthful six-column steps for all
four journeys plus policy/roles. Garden remains conditional normal-launcherNR;
visible cache is distinguished from numerical counter proof. No code/config changes
force prerequisites. Four limitation classes separate current limits from production
dependencies/future work/out-of-scope; historical G inventories/counts/verdicts retained
with explicit old-checkpoint scope. Q001..018 current/production/optional/status flags
close no broad question. Tracked presentation/deck/BPMN/standalone diagram search
found none; FINAL_PRESENTATION_SOURCE=NOT_PRESENT_IN_REPOSITORY. Existing Markdown
diagrams inspected and presentation-ready bullets prepared, no invented deck.

Explicit UTF-8 writes and original equal-line bytes preserve punctuation/line endings.
Self-review checks claims against current owners, D062/D064, questions and exact UAT
16PASS/0FAIL/5NR/HUMAN0. Documentation-only27B; product budget1/2; documentation
BarrierB remediation0/2. No external calls/database/credential/Git publication.
Next freeze exact content and request fresh independent27B SolHigh; exactPASS releases27C.

## Final pre-gate checkpoint

27B fresh independent exact PASS,0/0/0/0, reportSHA256
d832669f973ec92d4a5f4841d9cd902cb2737bb1c57e2b3bfefe1668700443ec.
No documentation remediation required (0/2 rounds).27C fresh proportional results
and complete commands/identities/console-harness failure are recorded in
[regression](PHASE_27C_REGRESSION.md):135backend0skips,505frontend/41files,44contracts,
124governance,Ruff/strictmypy124files/typecheck/build/dependency/6scanners/two
guardedHTTPbrowserselectorsPASS. Product source hashes unchanged since acceptedA.
Fullbackend/physicalMongo/actualOCRNOTRUN/nottriggered, no expensive stale rerun claim.

All runnable actualUI rows completed;16PASS/0FAIL/5NR,agent16human0; original twoP2
productfixes remain visibly retested. OriginalclmpocNOTACCESSED/NOTMUTATED, external0.
Finalcurrentdocs incorporate actualB/C evidence without forecasting finalgate/commit.
Self-review:21requested UAT criteria,19corejourneys+2role boundaries, sixworkflow
views,C4L1/L2/L3,applicationorchestration,source/providertruth,6-columnrunbook,
4limitationclasses,18questionflags,missingdeck and18closeouttopics covered.
Knownhistoricalchecklist/results remain explicitlypre-A checkpoint, currenthandoff
resolvesfresh acceptance. No unrelatedsource/dependency/lockfile/config/fixturechurn.
Finalremediation0/1; exactfreshfinalSolHighPASS required before authorizedlocalcommits.
No push/PR/merge/newphase. Finalmanifest will bind all20candidatepaths; reportitself
is separatebookkeeping. ExplicitnewMDwhitespace/local links included, not justgitdiffcheck.
