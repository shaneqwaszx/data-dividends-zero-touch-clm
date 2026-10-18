# PR95-R4 comprehensive independent full-PR adversarial assessment

## Outcome and role boundary

**FAIL / BLOCKED.** This is the owner-authorized independent read-only adversarial
assessment of the entire accumulated PR95 delta against current main, including the
partial R4 frontend corrections. It is not the subsequent final acceptance Quality Gate.
P2-06 remains deliberately unimplemented under the owner's explicit timing decision.
This assessment additionally confirms two required P2 defects outside the three authorized
R4 corrections. A mandatory governance inventory assertion also fails. No implementation, test, configuration, ordinary documentation, Git,
GitHub or database fix was made by this reviewer.

The prerequisite clear full-PR assessment is unmet. The later final Quality Gate is
**NOT_RUN**, local commits are not permitted, and clean committed pre-PR verification
is **NOT_RUN**. Passing affected suites below do not override these findings or provide
publication authority. Recommendation: **BLOCKED; return the design and new findings
for a separate owner decision.**

## Reviewed identity and freeze

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/pr95-dashboard-remediation-20261018/data-dividends-zero-touch-clm`.
- Branch: `codex/pr95-dashboard-remediation-20261018`.
- Committed/published starting HEAD: `e970a0b31fe2cf2c1617dcc759c9d2131433ba68`.
- Committed tree: `8abb0de47de69a24f88550f3ddece82c03b7a626`.
  This is the published baseline tree, not a tree identity for the five uncommitted R4 files.
- Comparison base/current local `origin/main`: `4a280da473dcdbeb345ffdfa79aaa4c001e75f62`.
- Local `origin/ui-enhancement-v1`: the same published e970a0b. Fresh fetch/direct remote
  observations belong to the coordinator; this reviewer made no remote/Git mutation.
- Entire reviewed accumulated delta: 52 paths, enumerated below, including eleven
  historical reports and the original planner. Raw hashes are frozen in
  `.runtime/pr95-r4-hosted-frozen.json`.
- SHA256 of compact sorted JSON path/hash map:
  `0948cefe8dc99ace74d048fcba65922924a902e6aaec83e3e206b6be754ed410`.
- Current independently reproduced binary diff SHA256 using
  `git -c core.autocrlf=false diff --binary origin/main`:
  `05c528a2f905e01be13e7013bc06070b9e5c4ac63a658bf59426dc6a59862cbe`.
- The initial recorded diff serialization `8de3a281...` is not reproducible. All 52 raw
  hashes, base and HEAD remain identical. The coordinator independently confirms this
  in `.runtime/pr95-r4-hosted-diff-reconciliation.json`. The initial digest is retired
  as standalone identity evidence; an EOL/index explanation is only a hypothesis.
  The exact base/HEAD plus complete raw path/hash map bind this review.
- Both frozen scratch design/plan hashes also match. Backend, seven R3 scripts, root
  performance tests and historical R2/R3 reports match published HEAD raw blobs.
  R2 FAIL report remains SHA256
  `73029b67883331ab8b6fd5194560758f4c0a8936af1f8a7ac7cc8925e0f0b45e`.
- The only five implementation/test modifications after published HEAD are
  Dashboard.tsx, caseQueries.ts, Dashboard.test.tsx, Pr95DashboardCache.test.ts and
  pr95-dashboard.e2e.ts. Index remained empty. This report is a separate reviewer output.

Read-set: root/backend/frontend AGENTS; development workflow and merge protocol;
canonical skill routing, fyp-quality-gate, frontend-state-cache-change,
persistence-schema-change and integration-security-review/checklist; reviewer/security
roles; emitted dev_context union for BACKEND_DOMAIN, BACKEND_API, FRONTEND_UI,
FRONTEND_STATE_CACHE, AUTH_RBAC_SECURITY, PERSISTENCE and CI_TOOLING; current architecture,
project state, CODEX_WORKFLOW, pipeline README and open sponsor questions; case-access,
timing, activity and persistence contracts; original/current task planners and exact
owner timing decision; all changed-path categories and owning source/tests; existing
published/R2/R3 reports and receipts only as attributed historical evidence. Shared
read-path inspection additionally includes Mongo adapters/strict codec, automation
validation/decision retention, authorization/query, AuthProvider, QueryClient,
authenticated transport and mutation/deletion invalidation. Historical verdicts are not
silently transferred to this candidate.

## Required findings

### P2-06: excluded Mongo evidence still controls dashboard availability -- OPEN

Owner: DashboardService / existing automation repository / MongoCaseStore read boundary.
Anchor: `apps/backend/app/services/dashboard.py:78` and `:79`,
`apps/backend/app/persistence/repositories.py` MongoZeroTouchAutomationRepository.list_records,
and MongoCaseStore.list. The service performs an unscoped automation read before its
final clock and date selection; the adapter executes find({}) and decodes every envelope.
A malformed unprojected field in another team's record or an authorized case outside
7d can therefore fail an otherwise valid request before its clock/cohort is calculated.

Independent deterministic probe uses the real store codec and Mongo automation adapter
with an in-memory collection double, not a real Mongo server: OTHER_TEAM,
EXCLUDED_DATE and IN_COHORT malformed envelopes all raise PersistenceDataInvalidError;
all three record an empty query and zero clock reads. Existing API mapping safely returns
503 for that error, but excluded data must not determine another scope's availability.
Evidence: `.runtime/pr95-r4-hosted-audit-adverse.py` / `-adverse-final.log`.
Physical-server proof is not claimed in this assessment.

Attribution: existing published PR95 behavior; unchanged by this partial R4 candidate.
The owner explicitly stopped the backend correction to preserve the single post-read
final-clock Singapore cohort. This requirement is unresolved, not waived or passed.

### R4-A1 [P2]: malformed retained stage durations escape as HTTP 500 -- NEW REQUIRED

Owner: DashboardService._stage_timing, with the existing API safe-error boundary.
Anchor: `apps/backend/app/services/dashboard.py:416` through the
DashboardStageCaseTiming construction at `:421`; API catches at `apps/backend/app/main.py:2215`.

AutomationMetrics.stage_durations_ms accepts integer values without a non-negative
value constraint. validate_automation_record does not check those values. Independent
proof constructs an otherwise valid RUNNING automation (including a valid started_at)
with REGISTRY=-1, passes validate_automation_record, and round-trips it through the
actual MongoCaseStore._encode/_decode. The dashboard then raises Pydantic ValidationError
while building its ge=0 stage DTO. The authenticated real FastAPI route, executed with
raise_server_exceptions=False, returns **500 Internal Server Error**, rather than the
contract's sanitized **503 DASHBOARD_UNAVAILABLE**. No private exception detail leaked
in this response; the problem is incorrect availability/error containment.

Evidence: `.runtime/pr95-r4-hosted-audit-adverse-final.log` records canonical codec
acceptance, ValidationError and HTTP500. No model_construct, invalid model_copy of the
negative metric, database connection, provider request or weakened validator was needed.
The copy only supplies the missing valid start timestamp to the ordinary test helper.

Attribution: the underlying duration-validation gap is inherited; PR95 newly consumes
these retained stage samples, exposing a dashboard regression versus main's old read
model. This is distinct from P2-06: the malformed value belongs to the selected authorized
cohort and survives the current canonical decoder. It would remain after merely scoping
reads. A separate owner decision should authorize bounded retained-stage validation
before projection with the established safe failure, plus memory/guarded-Mongo and
included/excluded-scope regression proof. Do not mask all ValidationErrors or loosen the
codec to fix it. No remediation was performed.

### R4-A2 [P2]: capped case prefixes are presented as complete case history -- NEW REQUIRED

Owner: Dashboard presentation, preserving the accepted API display cap.
Anchors: `apps/frontend/src/pages/Dashboard.tsx:432`, `:640`, `:711` and the shared
pagination total at `:147`.

The accepted API intentionally returns only the first200 scoped_cases while retaining
full cohort totals. AllCasesTable receives only that prefix, labels it **All cases**,
and presents its length as the local exact total. Its Person/status/age filters and
My work's Your cases/Blocked cases also operate only on the prefix. There is no capped
subset disclosure or link from these sections to the complete existing portfolio.
A user whose matching person/blocked case occurs after200 can receive a false empty
filtered result while complete KPI counts include that case.

Independent evidence first obtains an actual backend-produced snapshot for201 selected
completed cases: total_cases=201, completed_cases=201, len(scoped_cases)=200. Rendering
that unchanged response produces **1-5 of 200** under **All cases**, shows201 in the KPI,
and contains no subset/truncation warning. Source tracing proves all local filters
operate solely on that array. Evidence: `pr95-r4-hosted-audit-large-snapshot.json`,
`pr95-r4-hosted-audit-render.mjs` and `-render-final.log` under `.runtime/`.

Attribution: PR95 Dashboard v2 presentation, inherited by current R4; not introduced by
the two R4 frontend fixes. The cap itself is expressly accepted and is not this finding.
The required correction is truthful subset/filter labeling and access to the existing
full portfolio, or another separately owner-approved bounded approach. Do not remove
caps, download all cases or redesign the API. No remediation was performed.

## Additional required integration-check failure

**R4-V1: current browser discovery and inventory assertion disagree.** The mandatory
coordinator governance/performance run executes244 tests and fails one: tests.test_run_e2e
RunE2ETests.test_ci_outer_bound_covers_current_discovery_and_bounded_cleanup,
`tests/test_run_e2e.py:1013`, expects109 but current discovery contains110. R4 added one
real recent-activity browser test. This is an R4 integration regression in supporting
inventory evidence, separate from the product P2 findings. The largest shard stays55
for109 or110 selectors, so this evidence does not demonstrate a time-budget overflow;
9960 seconds/234-minute outer bound need not change merely because of the extra selector.
The assertion must be reconciled truthfully and the affected governance lane rerun on a
freshly frozen candidate before acceptance. No source/test/configuration fix was made.
Evidence: `.runtime/pr95-r4-hosted-governance.log`.

## Minor findings, separate from required P2s

- **R4-M1 [P3], empty local pagination:** Dashboard.tsx:147 computes a first row of1
  even when total=0, so empty workload/exception/case/list sections show `1-0 of 0`.
  The actual independent empty snapshot render confirms it. This is presentation
  polish; it does not authorize broad cleanup or account for the required stop.
- **R4-M2 [P3], unnamed date filter:** Dashboard.tsx:759 has no label, aria-label or
  aria-labelledby. Native options expose values but not an explicit programmatic
  control name. Independent render/source inspection confirms it. Add a descriptive
  name if separately authorized; this assessment did not edit it.

## Authorized R4 corrections and prior acceptance preservation

| Finding / invariant | Current disposition |
|---|---|
| P2-07, recent activity first100 ceiling | Corrected in the frozen frontend. Bounded10-event API pages track offset, include creator/team/actor role/team/page/limit in authenticated keys, use has_more, carry AbortSignal and do not fabricate a total. Actual browser traverses more100 real authorized events, compares deterministic ordering, reaches final disabled Next, goes backward and refreshes to page one. |
| Activity loading/error/refresh/isolation | Current page loading and refreshing states are explicit; failed/empty results differ; retry does not falsely show empty success. Component/key tests exercise105 events, final/previous/refresh, creator/role/team switches, deferred old-team replies and cancelled old-session responses. Existing auth/session-generation clearing remains authoritative. Activity is explicitly all dates, independent of dashboard created-date range, and live page-boundary movement is disclosed. Existing offset10000 cap has an Audit narrowing message. |
| P2-08, stage disclosure | Corrected: native type=button in its data cell, stable unique useId/stage IDs, aria-expanded/controls, labelled hidden detail region, escaped unchanged content and separate native sort controls. All six stages, zero-detail states, repeated toggle and sort-while-open are exercised. Actual browser proves Tab/Shift+Tab, Enter/Space, focus and narrow table containment. |
| R2 P2-01, creator validation | Source and exact published bytes preserved: authorized Mongo candidate invalid facet runs before creator rows filter; schema9/10 valid nullable creator and legacy absence remain strict. Fresh deterministic creator compatibility/activity tests pass. Previous physical proof is historical, not newly executed. |
| R2 P2-02, reversed resolver chronology | Canonical timing guard still runs for every selected resolved exception, including missing resolver; sanitized503 regressions freshly pass. |
| R2 P2-03, validation beyond200 | Every selected case timing is validated before display cap. Fresh valid201/invalid201 tests pass; full counts/trend survive. This does not cure the separate capped-table disclosure finding. |
| R2 P2-04, age versus completed duration | Both mixed-status tables use Case age / duration, status-specific cell labels and shared exact formatter; browser clock does not recompute or change filters. Fresh component/browser regressions pass. |
| R2 P2-05, sortable headers | All four tables retain native scoped header buttons, aria-sort and keyboard activation; fresh actual browser covers them. |
| R3 fifteen Ruff corrections | All seven script bytes match published HEAD. Obsolete noqas, two unused bindings, exact Decimal integers, import ordering and the one explicitly approved local BLE001 annotation remain unchanged. No configuration/rule weakening or removed workload assertion. Current broad/backend Ruff pass. The sampler/performance evidence guards retain their narrow byte barrier and adverse error checks. |
| External and durable boundaries | No connector, target ledger, provider mode, schema/version/index/migration, write/CAS/delete, authentication grant or configuration path changed in R4. Strict earlier compatibility and provider truth remain; no Live/compliance/SLA/productivity authority is invented. |

## Full accumulated data, metric and integration challenge

Authorization remains backend-owned: query scope resolves actor role/team, Director
filter intersects existing teams/unassigned, HR remains denied and inaccessible case
lookups retain the same safe404. Creator counts/lists and actual recorded resolver fixes
are distinct; once per RESOLVED exception, open/cancelled/draft/missing attribution does
not become a successful fix. Resolver-only rows have zero creator counts. Mine returns
only the actor's row without widening case lists. Cross-team/date exclusions, exact
integer resolution means and repeated decisions are covered in current source and fresh
owning tests. Read-error isolation is still defective as specifically identified above.

Metrics inspected: completed-only zero-touch denominator with zero-empty behavior;
recorded non-null start-to-completion means and separate clean/blocked counts; recorded
processing-attempt stage times and top3; retained exception history; UTC Monday eight-week
completion buckets inside the selected created cohort; progress stages/6 with completion100;
full-cohort counts before10/5/200 display limits. Legacy historical_trend remains the
original30 zero-filled UTC dates before v2 cohort filtering. Omitted API date_range remains
all history; the UI explicitly requests30d. Singapore N-calendar-day boundaries and one
post-read observation/midnight tests remain unchanged. Missing historical creators and
unknown timings stay unknown. No unsupported sponsor approval rule was added.

UI inspection covered every local pager (exception, workload, All cases, Your cases,
Blocked cases) and server activity pager; all sortable headers and stage detail regions;
filters/local state; loading/error/cached refresh and session clearing; links and
responsive scroll containers. The two additional presentation findings above are not
hidden by passing happy-path tests. Sorting remains local to each returned bounded array.

Integration diff preserves the current authenticated transport and PR89 Assistant;
App removes only the obsolete local DashboardSnapshot component/styles. Shared APIs/types
add v2 fields atomically while preserving the legacy trend/default response. Portfolio
and activity keep their established read owners and bounded API; creator filtering adds
an intersection, not authority. PR96 governance paths are inherited unchanged from main;
no workflow/dependency/lock/configuration change is in the accumulated delta. Browser
inventory assertions still encode109 from the published baseline, whereas the new R4
activity browser increases actual discovery to110. The required inventory check fails
as recorded below; this is not a demonstrated CI time-budget overflow. R3 script normalization has no
workload/target/provider semantic change. New failures cannot trigger Mock substitution,
provider fallback or a target mutation; the Dashboard read owner has no connector call.

## Execution evidence and limits

All fresh executions below concern the frozen current files. Reviewer subsets overlap
coordinator lanes; counts must not be added as unique tests.

| Lane | Actual result and attribution |
|---|---|
| Independent focused backend |75 passed4.81s; Dashboard, compatibility, activity, portfolio and R3 fixture guards. `.runtime/pr95-r4-hosted-audit-backend.log`. |
| Independent Dashboard/cache |35 passed; two Vitest files, including105-event traversal and adverse keys/session/team cases. `-audit-ui.log`. |
| Independent actual configured browser |2 passed14.7s through run_e2e, owned local processes and real HTTP; complete PR95 Dashboard sorting/disclosure/navigation/clock test plus real >100-event activity. `-audit-browser.log`. No API route mocking. |
| Independent adverse codec/API |Canonical negative stage sample survives actual codec; projector ValidationError/HTTP500 reproduced. Real adapter with collection double confirms P2-06 included/excluded decode ordering. `-audit-adverse-final.log`. Not physical Mongo. |
| Independent adverse presentation |Actual backend201-case response rendered through current React components; capped pager/no warning, empty range and unnamed date filter confirmed. `-audit-render-final.log`. SSR rendering is not substituted for the separate actual browser evidence. |
| Coordinator focused backend |68 passed8.74s; `pr95-r4-hosted-backend-focused.log`. |
| Coordinator full frontend |57 files /949 passed12.33s; `pr95-r4-hosted-frontend-full.log`. |
| Coordinator frontend tooling |Typecheck, build and npm ls --all PASS; final typecheck/build/npm-ls logs. |
| Coordinator applicable broad actual browser |10 passed47.5s; PR95, PR89 Assistant, auth/navigation, Director/RM, portfolio/activity paging, responsive shell and logout/role reset. `pr95-r4-hosted-browser-broad.log`. Independent2 are a subset. |
| Coordinator lint/types/static |Broad Ruff and backend configured Ruff PASS; mypy127 source files PASS; all six repository/state/architecture/tooling/policy/provider-readiness/secret checks PASS; logs individually inspected. |
| Coordinator contracts |44 passed3.18s; `pr95-r4-hosted-contract.log`. Actual count is used, not prior historical48. |
| Coordinator governance/performance |FAIL:244 executed,243 passed/1 failed82.567s; stale109-versus110 selector assertion in tests/test_run_e2e.py:1013. pr95-r4-hosted-governance.log. No fix or test weakening. |
| Fresh full backend / physical Mongo |NOT_EXECUTED in R4. Backend/R3 inputs match the published/R3-tested bytes, but this does not create fresh R4 full/physical evidence or accept P2-06. No Mongo service was made available/used by this reviewer. |
| Carried R3 broader evidence |Attributed historical only: full backend2799 passed/164 skipped/3 warnings; guarded physical158 passed/zero skips; performance/governance244, contracts48 and script behavior proof belong to the exact R3 input. They are not fresh R4 passes and do not cover the newly found defects. |
| Final acceptance QG / local commits / clean committed pre-PR |NOT_RUN; clear-audit prerequisite unmet. Intentionally uncommitted handoff is not certified by running the clean-tree publication gate. |
| Hosted CI/review |No new remote action. Historical billing-refused jobs remain NOT_EXECUTED; no fresh hosted approval is claimed. |

The coordinator preserved failing-first UI/repository observations and browser harness
errors in unique hosted-R4 logs. Initial UI mocks assumed wrong team directory and
explicit offset0; the initial browser used a positional locator after sorting and
assumed a fixed two-page fixture. Corrected tests retain the intended invariants and
exercise real pages; this review found no corresponding product weakening. The independent
SSR scratch bootstrap initially lacked Vite env/automatic JSX and later used a mismatched
Unicode search literal; these were scratch invocation/probe errors, not product fixes.
Final render results above use the actual backend output and corrected probe.

Existing SSR useLayoutEffect warnings and the679.35kB Vite JS chunk warning remain.
Whole-document inherited mobile overflow is not certified absent; actual Dashboard table
scroll containers are bounded at390px. Historical six unavailable native Tesseract tests
remain unexecuted, not OCR success. No real ACRA/GoldTier Sandbox/Live request, confidential
artifact access, .env read, protected clm_poc operation, database/container mutation or
persistent browser evidence cache is required or evidenced by this reviewer. Secret
scanner PASS covers configured patterns, not a universal external security audit.

## P2-06 design assessment and smallest further authority

The frozen ignored design assessment correctly identifies a causal cycle: the existing
clock/cohort must follow both reads, while literal date-selected IDs-before-fetch would
require that cohort before the automation read. A second timestamp, earlier data_as_of,
changed midnight behavior, catch-and-skip, weakened decoder, memory fallback, whole-store
repair or N+1 access is not authorized. The owner explicitly rejected the pre-fetch clock.

Recommended owner decision: authorize a narrow opaque request-local captured raw batch
inside the existing automation repository/store. Read one finite server-authorized ID
superset without full-envelope decoding; fully capture it, observe the single final
clock, compute the unchanged final cohort, and decode only selected IDs inside that same
repository-owned batch through the unchanged strict codec. The raw payload must never
leave the adapter boundary, become log/API content, survive the request, accept foreign
subset IDs or create a cache/second owner. Memory must provide equivalent defensive
snapshot and ordering behavior. No schema/index/write/CAS/provider change is needed.

This needs explicit authority to replace the literal date-selected-before-fetch condition
with date-selected-before-full-decoding, plus preimplementation review of the narrow
read/decode interface. Authorized dates may be captured as a raw superset; that trade-off
must be explicit. This is the smallest plausible route preserving the final-clock
contract, not an implemented or independently accepted architecture. A specialized projected
read model has greater validation/mapping drift; a transaction/snapshot redesign is much
larger and would redefine logical/physical reads. Both need broader authority.

If authorized, require actual guarded Mongo included/excluded team/date corruption,
RM/Director/unassigned/mine and creator/resolver cases,0/201+ cases, strict identity/schema
and relevant failures, one batch/no N+1, unchanged clock count/order/midnight tests,
ordering/memory parity, handle lifetime/subset guards and no provider calls. The two new
required findings also need explicit bounded remediation authorization; their fixes must
return to a fresh full-PR assessment and then a separate final acceptance QG.

## Complete reviewed changed-file inventory

Each of the52 paths below is part of the accumulated diff against main, regardless of
whether R4 edited it. INTENDED means product/script behavior within original PR95/R2/R3;
SUPPORTING means focused verification, contracts/context or historical review evidence.
No unexpected implementation path was found. This newly authored report is additional
review evidence outside the frozen52; its own final hash is returned separately.

| Path | Classification |
|---|---|
| `.ai-pipeline/001_planner/PR95_DASHBOARD_INTEGRATION_REMEDIATION.md` | SUPPORTING |
| `.ai-pipeline/reports/PR95_DASHBOARD_ACCEPTANCE_QUALITY_GATE.md` | SUPPORTING |
| `.ai-pipeline/reports/PR95_DASHBOARD_FINAL_ACCEPTANCE.md` | SUPPORTING |
| `.ai-pipeline/reports/PR95_DASHBOARD_FINAL_QUALITY_GATE.md` | SUPPORTING |
| `.ai-pipeline/reports/PR95_DASHBOARD_IMPLEMENTATION.md` | SUPPORTING |
| `.ai-pipeline/reports/PR95_DASHBOARD_LOCAL_ACCEPTANCE.md` | SUPPORTING |
| `.ai-pipeline/reports/PR95_DASHBOARD_MAIN_INTEGRATION_GATE.md` | SUPPORTING |
| `.ai-pipeline/reports/PR95_DASHBOARD_QUALITY_GATE.md` | SUPPORTING |
| `.ai-pipeline/reports/PR95_DASHBOARD_REMEDIATION.md` | SUPPORTING |
| `.ai-pipeline/reports/PR95_R2_QUALITY_GATE.md` | SUPPORTING |
| `.ai-pipeline/reports/PR95_R3_QUALITY_GATE.md` | SUPPORTING |
| `apps/backend/app/domain/case_management.py` | INTENDED |
| `apps/backend/app/domain/dashboard.py` | INTENDED |
| `apps/backend/app/main.py` | INTENDED |
| `apps/backend/app/persistence/mongo_case_store.py` | INTENDED |
| `apps/backend/app/services/case_portfolio_repository.py` | INTENDED |
| `apps/backend/app/services/case_query.py` | INTENDED |
| `apps/backend/app/services/dashboard.py` | INTENDED |
| `apps/backend/tests/s1_date_filter_fixtures.py` | SUPPORTING |
| `apps/backend/tests/test_attention_queue_backend.py` | SUPPORTING |
| `apps/backend/tests/test_phase13_dashboard.py` | SUPPORTING |
| `apps/backend/tests/test_phase13_real_mongo.py` | SUPPORTING |
| `apps/backend/tests/test_phase17_case_activity.py` | SUPPORTING |
| `apps/backend/tests/test_phase18_case_portfolio.py` | SUPPORTING |
| `apps/backend/tests/test_pr95_dashboard_compatibility.py` | SUPPORTING |
| `apps/backend/tests/test_pr95_r3_script_fixtures.py` | SUPPORTING |
| `apps/frontend/e2e/pr95-dashboard.e2e.ts` | SUPPORTING |
| `apps/frontend/src/App.test.tsx` | SUPPORTING |
| `apps/frontend/src/App.tsx` | INTENDED |
| `apps/frontend/src/Dashboard.test.tsx` | SUPPORTING |
| `apps/frontend/src/Phase14CaseManagementPerformance.test.tsx` | SUPPORTING |
| `apps/frontend/src/Pr95DashboardCache.test.ts` | SUPPORTING |
| `apps/frontend/src/api.ts` | INTENDED |
| `apps/frontend/src/caseQueries.ts` | INTENDED |
| `apps/frontend/src/design-system.css` | INTENDED |
| `apps/frontend/src/pages/Dashboard.tsx` | INTENDED |
| `apps/frontend/src/pages/DirectorTeamFilter.tsx` | INTENDED |
| `apps/frontend/src/styles.css` | INTENDED |
| `apps/frontend/src/types.ts` | INTENDED |
| `docs/ARCHITECTURE.md` | SUPPORTING |
| `docs/PROJECT_STATE.md` | SUPPORTING |
| `docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md` | SUPPORTING |
| `docs/contracts/CASE_TIMING_PROFILE.md` | SUPPORTING |
| `scripts/benchmark_blocker_review.py` | INTENDED |
| `scripts/generate_zero_touch_happy_path_documents.py` | INTENDED |
| `scripts/performance_concurrency.py` | INTENDED |
| `scripts/performance_load.py` | INTENDED |
| `scripts/performance_optimization.py` | INTENDED |
| `scripts/sponsor_demo_browser_fixture.py` | INTENDED |
| `scripts/zero_touch_classification_browser_fixture.py` | INTENDED |
| `tests/test_performance_review_remediation.py` | SUPPORTING |
| `tests/test_run_e2e.py` | SUPPORTING |

## Final stop boundary

All frozen source/report/design hashes were rechecked before report delivery; no reviewed
implementation changed during this assessment. The only reviewer tracked write is this
assigned report. The five R4 frontend files remain intentionally uncommitted and the
index is empty. The coordinator alone owns Git/primary-worktree preservation checks.
No push, PR description/review/thread action, merge, PR96 modification or next phase
is authorized or performed. Overall full-PR adversarial verdict: **FAIL / BLOCKED**.
Final Quality Gate: **NOT_RUN**. Return the precise P2-06 design authorization and two
new required P2s and the inventory-check failure to the owner; do not claim R4 accepted or publication-ready.
