# PR95 Dashboard v2 final acceptance Quality Gate - round 4

## Outcome

**FAIL** on frozen commit `feca3d245e0f9752774fdba57a82c522e2eb0e2a`.
F1-F7 are corrected in the inspected content and all 156 guarded physical tests now
pass. A further required P2 finding, F8, remains: the Dashboard displays a factual
zero-millisecond case age as `1h` and a 12-millisecond processing/fix sample as `1m`.
The local minimum/rounded formatters violate the accepted factual timing display
contract. Passing server calculations and tests do not make those rendered values true.

This fresh independent reviewer made no product, test, configuration or ordinary
documentation fix. This report is immutable evidence for this freeze. The coordinator
must remediate F8 in a separate run, then obtain a fresh independent gate. No current
full ordinary backend PASS is claimed; that expensive lane was deliberately held once
the required presentation defect was established.

## Reviewed identity, authority and write boundary

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/pr95-dashboard-remediation-20261018/data-dividends-zero-touch-clm`.
- Branch: `codex/pr95-dashboard-remediation-20261018`.
- Current source / independently reviewed HEAD: `feca3d245e0f9752774fdba57a82c522e2eb0e2a`.
- Frozen tree: `86815a65cb34f7b4a7b95cc9d6cdda47938a9ceb`.
- BASE_SHA / merge base / inspected origin/main: `cc10a2b626ef92d2dd44600d488c1f15cc4f04f8`.
- Published PR95 source parent: `1c1fd9fbf1a68f79137d150ac8609cf811b10938`.
- Normal integration merge: `aa8b9a4333f8858262fe5c15cdccd1e1272ace36`.
- Feature common ancestor: `12ba994b8128a4777e12fcc764bafc8f39b9292a`.
- Complete reviewed set: all 37 paths differing from origin/main. The independent
  initial and closure audits recomputed every raw-byte SHA256 and exact changed-path
  set: 37 matched, no missing/extra/mismatched paths.
- Manifest: `.runtime/pr95-review-manifest-r4.json`, raw UTF8 sorted indent=2 JSON
  plus final LF, SHA256 `0f4af3c64bb87095cfba2a08138afb29b4c857a686e72372c682e024712d107d`.
- Initial tracked/index state was clean. The sole allowed tracked write is this report.
  All behavioral executions and inspected coordinator receipts below exercise this
  frozen content. The report itself is outside that frozen implementation identity.

Authority reviewed: AGENTS.md; canonical fyp-quality-gate/report template; deterministic
context union BACKEND_DOMAIN, BACKEND_API, FRONTEND_UI, FRONTEND_STATE_CACHE,
PERSISTENCE, AUTH_RBAC_SECURITY and CI_TOOLING; workflow, architecture/provider state,
coordination/branch protocol, current planner/remediation, three immutable FAIL reports,
access/timing/activity/persistence contracts, relevant decisions/open questions, role
instructions, accepted PR89 baseline and POC catalogue. Applied persistence, frontend
cache, integration-security and POC-regression guidance. No sponsor authority or timing
exception was inferred from old screenshots, authored tests or feature preservation.

Observed capabilities: approved escalated shell access to the assigned managed checkout,
Python/pytest with explicit AnyIO, Node/esbuild/React server rendering, current local
receipt access and actual guarded Mongo execution against the assigned existing mongo:7
loopback service on27027. Coordinator owned browser ports8775/4183 and all Git/source
mutations. Heavy execution was serialized: the reviewer began focused/backend/physical
only after the coordinator released its four short lanes. No competing full backend ran.
No dotenv, protected sponsor/evaluation artifact, external provider or retained database
was accessed. No connection string, credential, raw payload or private error was printed
or persisted. No container was stopped/removed by this reviewer.

## Acceptance assessment

| Criterion | Independent assessment |
|---|---|
| Preserve Dashboard v2 and accepted main Assistant | Whole 37-path delta inspected; accepted Assistant implementation/client/resource owners have no feature delta. Current frontend and actual-browser receipts preserve Assistant, navigation and session behavior. |
| API/default/trend compatibility | PASS focused/source: API omission remains all-history/team; browser explicitly requests30d; original 30 zero-filled UTC-day historical_trend precedes the v2 creation cohort. Additive fields/shared types agree. |
| Selected cohort and descriptive metrics | PASS server evidence: exactly N Singapore created calendar dates; common selected denominators; completed/no-exception zero-touch; recorded stages/6 capped with COMPLETED100. No sponsor SLA/scoring/approval rule. |
| F1 creator versus resolver | Corrected: mine creator lists/counts remain creator-only; its own resolver row includes successful authorized teammate-case fixes. Other-team/excluded-date facts, drafts/open/cancelled and duplicate decisions do not inflate fixes. |
| F2 truthful timing prose | Corrected: processing attempts exclude blocker waiting/resolution; totals describe recorded workflow-start-to-completion rather than intake creation. |
| F3 provider label | Corrected to Available; no unsupported visible Live availability claim. Mock/Local/Partial/Dormant classifications unchanged. |
| F4 backend timing authority | Corrected calculation/filter/sort source: case_elapsed_ms and workload ages share server data_as_of; client clock is unused. Current clock-skew unit/browser checks pass. F8 independently exposes incorrect formatting of those correct values. |
| F5 observation ordering | Corrected and independently challenged: authorized case read then existing saved automation read then one clock. Ages/cohort/UTC trend use the final observation. Concurrent valid updates no longer look future merely because observation preceded reads. |
| F6 exact milliseconds | Corrected: timedelta integer floor division and integer mean preserve1001/3003ms and floor sub-millisecond remainders. The same conversion is used for delay selection. Physical mean2400334ms passes. |
| F7 canonical physical fixture | Corrected: full ordered completion prefix, start and retained metrics, canonical validation before create. Production decoder/schema are unchanged. Actual full physical24-suite156PASS proves the corrected retained completion/read/restart parity. |
| F8 factual duration formatting | **FAIL**: minimum/rounded Dashboard formatters turn0ms age into1h and12ms processing/fix values into1m. Required bounded correction below. |
| RBAC/privacy/cache | Independent focused/RBAC148PASS plus physical scope matrix. HR denied; exact team/Director scope and safe404 retained. Query keys include user/team/view/date/creator; existing session-generation clearing, AbortSignal,401 and deletion owners remain. |
| Required broad evidence | Current short-lane receipts pass as attributed below. Full ordinary backend intentionally NOT_RUN on this freeze after F8; earlier failed full run is retained and cannot be cleared by isolated/focused tests. |

## Required finding

### F8 - P2: Dashboard synthesizes minimum hour/minute timing values

`apps/frontend/src/pages/Dashboard.tsx:54-65` defines two local display functions.
`formatDuration` applies `Math.max(1, Math.round(ms / 60000))` for every sub-hour
value; `formatAge` applies `Math.max(1, Math.round(ms / 3600000))` for every sub-day
value. Therefore0ms,12ms,999ms and1000ms all display as `1h` in case/oldest-open age
and `1m` in processing/fix duration. This is a numerical presentation defect even
though the response, sort and filter values now remain correct.

Affected real consumers: stage clean/blocked/combined/top cases at:261-273; creator
oldest age and resolver mean at:384/:387; manager and My work case ages at:476/:584;
manager total timing at:634; My work mean fix/recorded run at:687-688.

Authority: `docs/contracts/CASE_TIMING_PROFILE.md:10` makes the backend duration the
presentation authority; :26-27 prohibits rounded-up/clamped/synthesized duration
values; :62-64 requires factual formatting such as `< 1s`, seconds, minutes/seconds,
hours/minutes and days/hours. The current Dashboard contract explicitly reuses this
canonical timing projection. No planner or owner decision permits fabricated minimum
hours/minutes. Preserving the intended v2 layout does not authorize changing0ms to1h.

Independent reproduction executed the actual frozen Dashboard.tsx entirely in memory:
read source, append temporary exports only in memory, esbuild bundle with write=false,
load that bundle and call the actual helpers. For each0/12/999/1000/59999/60000ms,
current output was caseAge=`1h`, processingDuration=`1m`. The probe then rendered the
actual exported DashboardView through ReactDOMServer/MemoryRouter using a synthetic
fixed snapshot. It asserted real table cells: zero-ms case age and workload oldest
=`1h`;12ms processing and resolver mean=`1m`. No source/test file, server/browser,
network response or backend duration was changed. This is execution proof beyond
reading an authored assertion or simulating a different formatter.

Required correction: use the existing factual shared duration formatter (currently
`apps/frontend/src/shared.ts:55`) consistently across these Dashboard timing consumers,
with the existing nullable/unknown guard and without introducing another timing owner.
Preserve backend values, fixed observations, filters/sort, active/completed semantics,
creator/resolver scope, neutral labels and the v2 layout. Add meaningful failing-first
actual-render assertions for0ms,12ms,999ms,1000ms,60999ms and larger boundaries in
manager/My work case ages, workload age, processing, fix and total-duration surfaces.
Null stays unknown rather than becoming zero. No client clock, schema, policy, provider
or arithmetic change is authorized by this finding.

No other required source defect was established in this review. That statement does
not supply the unexecuted current full-backend acceptance evidence.

## Independent execution and adverse evidence

Ordinary execution used candidate root/backend PYTHONPATH,
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, explicit AnyIO, no pytest cache, and no physical URI.

- `python -m pytest apps/backend/tests/test_phase13_dashboard.py apps/backend/tests/test_pr95_dashboard_compatibility.py apps/backend/tests/test_phase17_case_activity.py apps/backend/tests/test_phase18_case_portfolio.py apps/backend/tests/test_phase19_case_timing.py apps/backend/tests/test_phase13_auth_rbac.py -o addopts= -p anyio -p no:cacheprovider -q --tb=short`:
  **148 PASS,26.40s**, exit0. This includes the corrected chronology/interleaving,
  exact-ms, attribution/date/default, activity/portfolio and auth/RBAC regressions.
- Separate independent in-memory advancing-read challenge: real service inputs advance
  clock1ms during each read; call order exactly cases/automation/clock, final observation
  NOW+2ms, active age and resolver elapsed172800002ms. PASS.
- Separate actual HTTP error challenge with canonical ordinary-test bootstrap:
  five invalid chronology/duration variants and three persistence exception classes
  each return exact sanitized503 DASHBOARD_UNAVAILABLE; private sentinel absent. PASS.
- Actual in-memory Dashboard helper and React render probe: **F8 REPRODUCED** as above.
  This is a failed acceptance behavior, not a passing test count.
- Full guarded physical runner: `python scripts/run_physical_mongo_tests.py --timeout-seconds 1800`
  equivalent existing runner.main invocation, URI constructed internally for the assigned
  loopback service, never printed/persisted. **PASS:24 suites,156 collected,156 passed,
  0 failed,0 errors,0 skipped**, exit0. The current runner independently collects and
  validates suite ownership before execution; the inventory is revision-specific.
- Physical safety: only existing generated allowlisted disposable namespaces were used.
  Direct and imported shared fixtures use validated cleanup, drop only their generated
  database and verify absence. No cleanup exception occurred. No retained database or
  clm_poc connection/test/cleanup occurred. Existing container lifecycle stays with root.
- Full changed-path whitespace check: PASS. All37 raw hashes, HEAD/tree and exact path
  set rechecked unchanged after execution. The report receives its own explicit
  whitespace check because git diff --check does not inspect an untracked Markdown file.

## Coordinator receipts on this exact frozen content

These are coordinator executions independently inspected, not reviewer reruns:

| Lane | Actual result / receipt |
|---|---|
| Full frontend Vitest |57files,933PASS,15.00s; `.runtime/pr95-r4-frontend.log`. Existing React act/server-render warnings remain. |
| Frontend typecheck/build/dependency tree | PASS, exit0 in the same receipt. Existing Vite>500kB bundle warning and platform-optional package omissions remain. No dependency manifest/lock delta. |
| Actual guarded local Mock browser |9PASS,41.5s; `.runtime/pr95-r4-browser.log`. Genuine normal-UI Mock completion after explicit Review & Send, visible positive Singapore weekly segment/no invented Australia,40-day JS-clock skew, Dashboard filters/range/nav/history/reload, PR89 resource/cancellation, auth/team/reset, portfolio/deletion/activity/mobile. |
| Public contracts and delivery |44+4=48PASS,6.32s; `.runtime/pr95-r4-static-contracts.log`. Private sponsor archives absent/unvalidated, not PASS. |
| Static/security/dependencies | RuffPASS; mypy127source filesPASS; project-state/architecture/tooling/policy/provider-readiness/secret pattern checksPASS; pipcheckPASS; diffcheck and clean initial status, same receipt. |
| Governance/runner unittests |220PASS,88.106s; `.runtime/pr95-r4-governance.log`. Expected adverse E2E failure text occurs inside overall unittest OK, not a real failed browser lane. |

Exact coordinator commands, supplied by the coordinator and tied to the inspected
receipts (the review did not rerun them):

```text
# apps/frontend
npm test -- --reporter=dot
npm run typecheck
npm run build
npm ls --all
# root; configured local actual-browser runner, original lifecycle/assertions
python scripts/run_e2e.py --backend-port 8775 --frontend-port 4183 --grep 'PR95 Dashboard v2|PR89 streaming resources|protected workspace requires|Case activity uses one paged|Director explicitly selects|ordinary RM repairs|Cases uses one bounded|responsive shell contains|S1 logout and interactive role'
# root; explicit backend/root/test credential helper PYTHONPATH
python -m pytest -o addopts= -p no:cacheprovider -q tests/contract tests/test_phase_07_delivery_assets.py
python -m ruff check apps/backend
# apps/backend
python -m mypy app
# root
python scripts/check_project_state.py
python scripts/check_architecture.py
python scripts/check_tooling_config.py
python scripts/check_policy_authority.py
python scripts/check_external_provider_readiness.py
python scripts/check_secrets.py
python -m pip check
python -m unittest tests.test_check_project_state tests.test_check_architecture tests.test_check_tooling_config tests.test_check_policy_authority tests.test_check_external_provider_readiness tests.test_check_secrets tests.test_pre_pr_check tests.test_run_e2e tests.test_run_physical_mongo_tests
```

The published PR95 run39051770323/attempt1/head1c1fd9f was coordinator-reported as
not started because of billing. It supplies no executed hosted CI for this candidate.
No push/PR or current remote candidate run was performed by this reviewer. The inherited
locked npm install has six advisory findings (1moderate/3high/2critical), as previously
reported; dependency remediation is outside this unchanged manifest/lock scope.

Historical attempts stay explicit: prior01bf826 full ordinary backend failed
1/2781PASS/162SKIP/3warnings in1100.12s in the HTTP demo seeder target-confirmation
response.read timeout. Its isolated1PASS8.35s never cleared the full failure. Product
attribution was unproved; no timeout/assertion/criteria change or waiver was made.
Prior physical runs failed155PASS/1FAIL due to F7 and are preserved in the immutable
round3 report. Current physical156PASS supersedes only that dependent physical claim;
no historical full-backend result transfers to this tree. Current full backend was
held for F8 remediation, so its completion remains required on the next freeze.
The ordinary162skip inventory historically consists of156 opt-in physical cases and
six optional native Tesseract cases; no unavailable native OCR is claimed executed.
No OCR/connector path changes in this task.

## Architecture, contracts, security and impact

The complete inspected delta extends existing DashboardService, CaseQueryService,
portfolio adapters, auth/QueryClient and view owners. No new service/repository/provider,
framework, dependency direction, direct route-to-Mongo access, duplicate authorization/
persistence/Decimal owner, target-ledger bypass or runtime provider composition appears.
No new ADR is required. Current main Assistant source/resource behavior is preserved.

Strict creator read projections preserve unknown legacy absence, require schema9/10
identity grammar and reject later creator fields on schemas1..8. Activity created_by
intersects existing authorization/team/case/date/etc before paging and applies equally
through the shared JSON/CSV dependency. It is case creator filtering, not event-actor
attribution. Schema10, insert-only create, update-only mutation, strict identity/revision
CAS, deletion/no resurrection and restart/no replay owners remain unchanged.

No new secret/raw sponsor/provider/document body, private error projection, TLS/auth
grant or persistent browser storage was found in the inspected task delta. Scope/filter
inputs stay under backend authority; centralized GET AbortSignal,401/session clearing,
mutation effects and deletion cancellation remain. Pattern scanning is bounded evidence,
not a universal security proof. F8 affects factual presentation, not permission grants.

POC/target owners and catalogue are unchanged. Actual browser proves one genuine local
Mock COMPLETED outcome after confirmation, without Live, GoldTier-internal/regulatory
approval or RFA claims. Physical restart/no-replay coverage passes. Broad ordinary
required-stage stopping/terminal/error/catalogue regressions must still complete on the
next candidate. No catalogue expansion or later sponsor behavior was authorized.

| Surface | Effect |
|---|---|
| API/shared types | Additive dashboard fields/query inputs, creator selector and case_elapsed_ms changed. |
| Durable schema/write/CAS/index | Unchanged; bounded creator read projections/validation changed. |
| Connectors/mappings/configuration/dependencies | Unchanged. |
| Business rules | Owner-approved descriptive cohort/metrics changed; sponsor rules/policy unchanged. |
| Auth/security | Existing grants/owners unchanged; scoped filter/cache identity extended; safe timing/persistence503 added. |
| Architecture/provider status | Owners/direction and Mock/Local/Partial/Dormant classifications unchanged. |
| Runtime | Dashboard/cohort/activity/metrics/presentation changed. F8 remains a false numeric timing display. |

Later sponsor production identity/auth/TLS, complete schemas/mappings, source precedence,
legal/control UBO, privacy/retention, related-party lifecycle and RFA/Live authority remain
outside PR95. This gate establishes no real ACRA/GoldTier Live readiness.

## Readiness and next authorized action

Local acceptance is blocked by F8. Return only the bounded presentation correction and
meaningful regressions to the coordinator. Preserve all four immutable FAIL reports,
freeze the corrected source/test/docs set, rerun affected frontend/browser/static/
contracts/governance and required complete ordinary backend plus physical evidence,
then request a fresh independent gate. No next phase is authorized.

Clean committed pre_pr_check/checklist remains NOT_RUN by this reviewer. That separate
integration gate follows exact independent PASS, the authorized report/source commit and
latest-main assessment. Its pending status does not cause this factual-timing FAIL.
Publication, push, PR creation/replacement, shared-history rewrite, PR96 mutation and PR
merge remain unauthorized. Repository-owner humans merge; coordinator owns local Git.

## Closure and complete reviewed path inventory

At report closure the implementation HEAD/tree and all37 raw content hashes remained
unchanged. Initial and pre-report index/tracked status were clean; this assigned report
alone is the new nonignored path. Explicit report whitespace is verified at closure.
This reviewer staged/committed/pushed nothing, switched no branch, made no merge/PR/
container-lifecycle mutation, and fixed no reviewed artifact.

```text
.ai-pipeline/001_planner/PR95_DASHBOARD_INTEGRATION_REMEDIATION.md
.ai-pipeline/reports/PR95_DASHBOARD_ACCEPTANCE_QUALITY_GATE.md
.ai-pipeline/reports/PR95_DASHBOARD_FINAL_QUALITY_GATE.md
.ai-pipeline/reports/PR95_DASHBOARD_QUALITY_GATE.md
.ai-pipeline/reports/PR95_DASHBOARD_REMEDIATION.md
apps/backend/app/domain/case_management.py
apps/backend/app/domain/dashboard.py
apps/backend/app/main.py
apps/backend/app/persistence/mongo_case_store.py
apps/backend/app/services/case_portfolio_repository.py
apps/backend/app/services/case_query.py
apps/backend/app/services/dashboard.py
apps/backend/tests/s1_date_filter_fixtures.py
apps/backend/tests/test_attention_queue_backend.py
apps/backend/tests/test_phase13_dashboard.py
apps/backend/tests/test_phase13_real_mongo.py
apps/backend/tests/test_phase17_case_activity.py
apps/backend/tests/test_phase18_case_portfolio.py
apps/backend/tests/test_pr95_dashboard_compatibility.py
apps/frontend/e2e/pr95-dashboard.e2e.ts
apps/frontend/src/App.test.tsx
apps/frontend/src/App.tsx
apps/frontend/src/Dashboard.test.tsx
apps/frontend/src/Phase14CaseManagementPerformance.test.tsx
apps/frontend/src/Pr95DashboardCache.test.ts
apps/frontend/src/api.ts
apps/frontend/src/caseQueries.ts
apps/frontend/src/design-system.css
apps/frontend/src/pages/Dashboard.tsx
apps/frontend/src/pages/DirectorTeamFilter.tsx
apps/frontend/src/styles.css
apps/frontend/src/types.ts
docs/ARCHITECTURE.md
docs/PROJECT_STATE.md
docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md
docs/contracts/CASE_TIMING_PROFILE.md
tests/test_run_e2e.py
```
