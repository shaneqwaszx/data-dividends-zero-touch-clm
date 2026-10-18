# PR95 Dashboard v2 final independent Quality Gate - round 2

## Executive result

**FAIL** on frozen HEAD 471fd62f1b3c1271e3be0658ba2ff096a290a581.
The first gate's F1-F3 are corrected. A further required P2 finding, F4, violates
the accepted backend-authoritative timing contract: Dashboard case ages and age
filters use the browser clock. An independent fixed-snapshot clock-skew probe
reproduced the misleading age. No implementation, test, configuration, or ordinary
documentation fix was made by this reviewer.

This report and the first FAIL are immutable evidence for their respective content.
Remediation belongs to the coordinator, followed by a fresh independent gate on a
new frozen candidate. Passing broad tests do not waive F4.

## Reviewed identity and authority

- Worktree: C:/Users/shane/.codex-clean2/worktrees/pr95-dashboard-remediation-20261018/data-dividends-zero-touch-clm.
- Branch: codex/pr95-dashboard-remediation-20261018.
- Frozen HEAD: 471fd62f1b3c1271e3be0658ba2ff096a290a581.
- Frozen tree: 90bff329dd4930b0d2b7a478200920b317ffc6ab.
- BASE_SHA / origin/main / normal integration parent:
  cc10a2b626ef92d2dd44600d488c1f15cc4f04f8.
- Published PR95 parent: 1c1fd9fbf1a68f79137d150ac8609cf811b10938.
- Feature common ancestor: 12ba994b8128a4777e12fcc764bafc8f39b9292a.
- Integrated merge: aa8b9a4333f8858262fe5c15cdccd1e1272ace36;
  subsequent remediation 6e5852918dcbd908b9a1c04b157144826a896616 and test-harness HEAD above.
- Complete reviewed scope: 34 paths differing from origin/main. Independently
  recomputed manifest sets and all raw-byte path hashes: 34 matched, zero missing,
  added, or mismatched paths. Manifest: .runtime/pr95-review-manifest-r2.json.
  SHA256 of sorted JSON: c5e02f29e72a21d3ba7da59db45680d2c9ff307fea9257b62d212a0c46ee4f50.
- Initial tracked/index state clean. The only allowed tracked write is this report.

Authority read: AGENTS.md; dev_context union for BACKEND_DOMAIN, BACKEND_API,
FRONTEND_UI, FRONTEND_STATE_CACHE, PERSISTENCE, AUTH_RBAC_SECURITY and CI_TOOLING;
emitted current workflow/state/architecture and sponsor questions; current access,
persistence and timing contracts; active planner and remediation; immutable first
gate; relevant role guidance and accepted PR89 gate for Assistant-preservation context.
Applied canonical fyp-quality-gate, persistence, frontend-cache, security and POC
regression guidance. Current source/contracts outrank historical reports.

No dotenv, private sponsor material, retained Mongo/evaluation artifact or external
provider was accessed. Worktree log execution/write required sandbox escalation;
this did not broaden the review write boundary.

## Acceptance assessment

| Requirement | Result and direct evidence |
|---|---|
| Preserve Dashboard v2 and accepted main Assistant | Whole 34-path diff reviewed. Assistant package and frontend Assistant source have no delta from main; App changes remove an unused historical snapshot helper. Current full frontend and focused browser receipts include Assistant regressions. |
| Additive API; all-history omitted-date default; original historical_trend | PASS in source/full backend. Legacy trend stays 30 zero-filled UTC days over the authorized view before the new selected-created-date cohort. Browser explicitly requests 30d. |
| Exact selected calendar cohort, descriptive progress/zero-touch metrics | PASS in source/tests. N Singapore dates with inclusive start/exclusive following-day bound; completion/no-intervention denominator; recorded stages/6 and completed=100. No approval/SLA/compliance claim. |
| Mongo creator projection/activity parity | Bounded schema9/10 creator grammar, old absence unknown, schemas1..8 reject later creator fields; creator intersects authorization before paging. Current ordinary/contract tests pass. Current physical lane deferred after F4; not claimed passing. |
| F1: creator case counts versus actual resolver work | Corrected. Authorized/date cohort is selected before separate creator lists/counts and resolver aggregation. Mine exposes only actor row, including teammate-created authorized fixes. Independent adverse probe PASS. |
| F2: truthful timing prose | Corrected. Processing-attempt samples exclude blocker wait; retained total means workflow start to completion. Numeric formulas remain retained facts. |
| F3: unsupported Live availability badge | Corrected to Available. Existing provider modes/classifications unchanged. |
| Backend RBAC and frontend cache lifecycle | No further required defect found. HR denied; RM/onboarder team scope and Director filters retained; safe absent/inaccessible404 preserved. Keys include user/team/view/date/creator; AbortSignal, session clearing, mutation effects and deletion owners retained. |
| Case age timing authority | FAIL F4. Identical backend snapshot changes displayed age under client clock skew, and age filters/sorting use that same browser-derived value. |
| Broad verification | Full backend PASS with explicit skips below; coordinator exact-tree frontend/browser/static/contracts/governance receipts PASS. Current physical run NOT_RUN. Pre-PR remains a later clean-commit gate. |

## Required finding

### F4 - P2: Dashboard ages and age predicates are recalculated from the browser clock

Evidence: apps/frontend/src/pages/Dashboard.tsx:415 and :530 take Date.now().
AllCasesTable uses it in case age and age filtering (:432); YourCasesTable uses it
in filtering (:539), sorting and display (:597). The helper at :69 subtracts
created_at from that client instant. Completed My work rows also keep using the
current instant rather than the retained completion boundary.

Current docs/contracts/CASE_TIMING_PROFILE.md:9-12 explicitly makes the backend
the sole timing authority and requires a cached response to remain a fixed
observation until refresh. The formula table defines completed/active elapsed time
from retained completion or one server observation. PR95 has no owner-approved
exception to that contract.

Independent reproduction: read-only TypeScript transpilation of the exact frozen
Dashboard.tsx and static rendering of DashboardView with one synthetic active case.
The server snapshot was unchanged: creation 2026-10-16T00:00:00Z, data_as_of
2026-10-18T00:00:00Z. With the client clock equal to that observation, the Age cell
was 2d. Advancing only Date.now by 40 days changed the same cell to 42d. The age
predicate uses the same value, so skew can also move a case between filter buckets.
The probe emitted no case/provider data and made no network call or source write.

Required correction: delegate factual case elapsed timing to the existing backend
timing owner, using one server observation, and consume returned durations consistently
for manager/My work age display, filtering and ordering. Preserve active versus
completed elapsed semantics and creator/authorization/cohort scope. Do not invent an
ageing/SLA policy, persist new timing history, or weaken chronology validation.
Keep invalid authorized chronology safely projected through the existing API error
boundary. Workload ages should share the response observation.

Required evidence: failing-first clock-skew/fixed-snapshot assertions; active and
completed manager/My work display/filter/sort behavior; one observation across rows
and workload; malformed/future chronology and safe errors; unchanged scopes and
memory/Mongo parity. Obtain fresh independent acceptance after the bounded fix.

## Independent execution and adverse evidence

- Full backend from apps/backend with explicit candidate-root/backend PYTHONPATH,
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 and PHASE12_MONGO_URI unset:
  python -m pytest -o addopts= -p anyio -p no:cacheprovider -q --tb=short
  **2780 PASS, 162 SKIPPED, 3 warnings, 1061.01s (17:41), exit0**.
  Current collection is 2942 tests. The full run includes the ordinary HTTP seeder
  tests; no test was selected out, weakened or forced to skip.
  Log: .runtime/pr95-r2-backend.log.
- Meaningful skips: independently collected current skip-marker inventory totals
  156 opt-in physical Mongo tests with no test URI. Six real local OCR cases skip
  when Tesseract is unavailable. None is counted as executed/PASS. Three expected
  Pydantic serialization warnings arise in malicious/bypass DTO conformance tests.
- Progress pauses at63% and97% were investigated without termination or test changes.
  CPU increased; read-only collection identified recovery/final orchestration regions,
  including two existing100-iteration regressions. The original run completed.
- Independent synthetic in-memory F1 probe: **PASS** for teammate-only resolver work,
  duplicate decisions counted once, draft/cancelled exclusion, date/team exclusion,
  actor-only mine row and unchanged empty creator lists/counts.
- Independent F4 exact-source rendering probe: **REPRODUCED**, identical server
  snapshot displays2d versus42d solely from client-clock skew.
- Current guarded physical Mongo: **NOT_RUN**, deliberately deferred once F4 was
  established and the coordinator reserved physical revalidation for the corrected
  candidate. The first gate's24 suites/156PASS belong to its older tree, not this one.
  No database connection, cleanup or container lifecycle action occurred in this gate.
- Complete changed-path whitespace check: PASS. All34 content hashes verified.
  No newly tracked secret, confidential sponsor artifact, raw provider/document body
  or private error projection was found in the reviewed delta. Report whitespace
  and final frozen-content identity are independently checked at closure.

Coordinator execution receipts, distinguished from this reviewer's executions,
on the same frozen471fd62 candidate:

- Full frontend: **57 files /931 tests PASS,12.61s**; frontend typecheck/build and
  npm ls --all PASS. Vite's existing >500KB bundle warning remains.
- Actual guarded browser: **9/9 PASS,39.6s** including PR95 actual synthetic Mock
  completion through normal Review & Send, visible positive Singapore weekly segment
  bounding box and no Australia segment; PR89 streaming resources, RM/Director
  auth/scope/navigation/cache/reset, portfolio/deletion/activity and responsive shell.
  Logs: .runtime/pr95-r2-frontend.log and .runtime/pr95-r2-browser.log.
- Contracts/delivery: **48 PASS,3.34s** (44 public contracts,4 delivery);
  .runtime/pr95-r2-contracts.log. The initial command's path setup was corrected;
  that invocation error is not a product failure.
- Root governance/runner unit tests: **220 PASS,86.007s**:89 checker tests,
  64 pre-PR unit tests and67 E2E/physical-runner tests.
  .runtime/pr95-r2-governance.log contains expected adverse-runner failure text
  inside an overall unittest OK; it is not a failing run.
- Whole-backend Ruff and backend mypy127files PASS. check_project_state.py,
  check_architecture.py, check_tooling_config.py, check_policy_authority.py,
  check_external_provider_readiness.py and check_secrets.py PASS.
- Assistant238PASS/12.62s receipt was executed on the pre471 candidate; source was
  unchanged through the QueryClient test-harness commit. This is explicitly attributed
  earlier execution on unchanged Assistant bytes, not a new full Assistant run here.
- Private sponsor example archives are absent/unvalidated; public contract PASS does
  not validate absent confidential artifacts or establish Live interoperability.

## Architecture, security, contract and regression assessment

DashboardService, CaseQueryService, portfolio adapters, canonical envelope, access
policy, AuthProvider/QueryClient and target ledger remain their existing owners.
No new service/repository/provider/framework, route-to-Mongo query, mapper, runtime
provider composition, ownership engine, authorization owner or ledger bypass appears.
F4 is a concrete timing-authority regression within the dashboard view and must be
corrected within existing owners; it does not justify a new timing architecture.

Creator projection changes are read-only: schema10 and strict legacy compatibility,
insert-only create/update-only mutation, CAS/revisions, deletion/no resurrection and
restart/no replay write semantics remain unchanged. No source/target contract,
sponsor policy, value mapping, authentication/TLS or external transport changed.
Creator filtering is distinct from event-actor attribution. Cache variants use the
existing user/session lifecycle, cancellation and mutation/deletion effects; no
persistent browser case storage or mutation retry was added.

The accepted POC regression catalogue was inspected and remains unchanged. The full
backend covers the existing terminal/call-stopping/confirmation/recovery protections;
current browser receipts include genuine Mock completion through the normal target
confirmation owner. No external provider execution, sponsor approval, RFA, compliance
or Live capability is claimed. Later sponsor production-auth/retention/related-party/
mapping/RFA dependencies remain outside PR95 rather than being silently resolved.

Scope effects of the reviewed candidate: API/shared types changed additively; durable
schema/version/write contract unchanged, read projections/validation changed;
connectors unchanged; configuration/dependencies unchanged; descriptive dashboard
calculations changed under owner authority, sponsor business rules unchanged;
mappings unchanged; backend filter/cache inputs extended, existing RBAC/capability
grants unchanged; canonical architecture owners/dependency direction unchanged;
provider classifications unchanged; dashboard/activity runtime/presentation changed.
F4's browser-time calculation remains a required violation of accepted timing authority.

## Readiness and next authorized action

Local product acceptance is blocked by F4. Coordinator may perform only the bounded
timing correction and meaningful failing-first regressions, then freeze the new content
for a fresh independent gate, including current guarded physical Mongo evidence.
This reviewer makes no correction and begins no next phase.

Clean committed pre_pr_check is intentionally NOT_RUN here. It follows independent
PASS and the coordinator's authorized report/source commit and latest-main assessment;
it is separate from this product FAIL. No publication readiness, push, PR creation/
replacement, PR merge, PR96 work or original-branch mutation is authorized by this gate.
Real ACRA/GoldTier Live readiness remains unestablished.

## Git status and complete reviewed path set

The complete34-path frozen manifest follows. At closure HEAD/tree and all hashes
remain unchanged; the index is empty and this assigned report is the only new
nonignored path. This reviewer staged/committed/pushed nothing and made no branch,
merge, PR, implementation or test change.

```text
.ai-pipeline/001_planner/PR95_DASHBOARD_INTEGRATION_REMEDIATION.md
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
tests/test_run_e2e.py
```
