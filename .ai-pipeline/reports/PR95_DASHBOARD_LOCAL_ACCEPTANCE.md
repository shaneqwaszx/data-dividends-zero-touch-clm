# PR95 Dashboard v2 local acceptance Quality Gate - round 5

## Executive result

**PASS** on frozen commit `43b313d52de43c02702bf5927c659b43128db197`.
All current bounded acceptance criteria are verified and no required fix remains.
This fresh independent gate reviews the complete PR95 candidate integrated with accepted
main, including the separate F8 remediation. The completed current serial full backend,
fresh independent physical Mongo, real-render challenge and attributed affected receipts
support local implementation acceptance. Final integration/publication gates remain
separate and no publication is authorized.

## Reviewed identity and boundary

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/pr95-dashboard-remediation-20261018/data-dividends-zero-touch-clm`.
- Branch: `codex/pr95-dashboard-remediation-20261018`.
- Current source, independently reviewed content and current execution HEAD:
  `43b313d52de43c02702bf5927c659b43128db197`.
- Frozen tree: `58c851c48206969d061e7a0b3808f997167718c5`.
- BASE_SHA / merge base / inspected origin/main:
  `cc10a2b626ef92d2dd44600d488c1f15cc4f04f8`.
- Published PR95 parent: `1c1fd9fbf1a68f79137d150ac8609cf811b10938`;
  published branch `ui-enhancement-v1` is outside this local branch.
- Normal main-integration merge: `aa8b9a4333f8858262fe5c15cdccd1e1272ace36`.
- Original feature common ancestor: `12ba994b8128a4777e12fcc764bafc8f39b9292a`.
- Complete reviewed set: all 38 paths differing from origin/main, listed below.
  The reviewer recomputed the exact path set and all raw-byte SHA256 values.
- Manifest: `.runtime/pr95-review-manifest-r5.json`; sorted UTF8 JSON, indent2,
  final LF SHA256 `6c67347baa1df656660f7804181729c76b36873bdc259ed5088bc7ba2683e447`.
- Initial tracked/index state was clean. This report alone is the permitted write;
  it is outside the frozen implementation identity. The reviewer made no source,
  test, configuration, ordinary documentation, Git or container-lifecycle mutation.

Authority: AGENTS.md; canonical fyp-quality-gate and report template; dev_context union
BACKEND_DOMAIN, BACKEND_API, FRONTEND_UI, FRONTEND_STATE_CACHE, PERSISTENCE,
AUTH_RBAC_SECURITY and CI_TOOLING; emitted workflow/state/architecture, coordination
and merge protocol; current planner/remediation; four immutable FAIL reports;
access/timing/activity/portfolio/persistence contracts; relevant decisions and sponsor
questions; tester/reviewer/security/contract roles and the POC catalogue. Persistence,
frontend-cache, security and POC-regression guidance was applied. Current source and
contracts outrank historical report wording.

Capabilities actually used: approved escalated shell in the assigned checkout,
Python/pytest, Node/esbuild/React server rendering/jsdom and guarded Mongo execution
against the coordinator-owned mongo:7 loopback service on27027. The coordinator owns
Git/source writes and browser ports8775/4183. Heavy execution was serialized: the fresh
physical lane completed before the coordinator started full ordinary backend execution.
This reviewer ran no competing backend/browser lane after releasing that slot.
No dotenv, confidential sponsor archive, retained database or external provider was
accessed. The assigned Mongo service URI was constructed in memory and never emitted
or saved. Only generated allowlisted disposable test databases were used.

## Acceptance assessment

| Criterion | Result and evidence |
|---|---|
| Preserve Dashboard v2 and accepted main Assistant | PASS: complete source/test/style/doc delta inspected; Assistant package/client/resource owners have no feature delta. App removes only the unused historical dashboard helper. Current full frontend and nine actual-browser tests preserve Assistant/navigation/session behavior. |
| Additive API and original default/trend compatibility | PASS: omitted date_range remains all-history/team, browser initializes explicitly30d; historical_trend remains30 zero-filled UTC days over the authorized view before new created-date filtering. Backend/shared types agree. |
| Cohort, progress and zero-touch calculations | PASS: exactly N Singapore calendar dates with inclusive start/exclusive next day; selected cohort denominators; completed/no-exception ratio; recorded automated stages/6 capped and COMPLETED100. These are owner-approved descriptive POC metrics. |
| Creator projection, activity and legacy parity | PASS: nullable schema9/10 creator grammar, unknown historical absence, rejection of later creator fields in schemas1..8. Creator predicates intersect backend scope and existing filters before paging. Current physical HTTP/restart tests pass. |
| Creator versus actual resolver attribution (F1) | Corrected: counts/lists belong to creator; one RESOLVED blocker contributes once to its recorded resolver. Mine exposes only actor workload row, including authorized teammate-case fixes. Other-team/excluded-date, drafts/open/cancelled and duplicate decisions do not inflate successful fixes. |
| Truthful timing prose and provider availability (F2/F3) | Corrected: processing attempts exclude blocker waiting/resolution; retained run time means workflow start to completion. Available replaces the unsupported Live badge. |
| Backend timing observation, precision and physical fixture (F4-F7) | Corrected: canonical project_case_timing and one data_as_of after both reads; saved automation input reused; exact integer timedelta/mean calculations; canonical completed prefix/start/metrics validated before physical create. Current physical156PASS; unchanged owning backend bytes also match preceding independent evidence. |
| Factual duration formatting (F8) | Corrected: existing shared formatDuration is reused behind a nullable guard for case/workload/stage/fix/run displays. Independent actual-render challenge150 assertions passes, including0/12/999/1000/60999ms, larger boundaries and unknown values. No backend value, clock, layout, label or control change in this correction. |
| RBAC, privacy and authenticated cache lifecycle | PASS: HR denied; RM/onboarder exact team and Director filter semantics; inaccessible/absent404; user/team/view/date/creator query identity; AbortSignal and existing auth-generation/401/deletion clearing remain. Current physical scope matrix and frontend/browser regressions pass. |
| Required full ordinary/backend and POC regression | PASS: current complete serial run2785PASS/162SKIP/3warnings,1051.49s, exit0; fresh independent physical156PASS separately executes all opt-in Mongo cases. |
| Contract/static/governance/security evidence | PASS for the bounded public/local lanes as attributed below. Private sponsor archive validation and Live external checks are unexecuted and outside this candidate's readiness claim. |

## Independent executions and adverse review

1. Frozen identity: exact38-path set and every raw hash verified before review, after
   physical execution and at closure. HEAD/tree remained fixed. `git diff --check
   origin/main...HEAD` passed; assigned untracked Markdown is separately whitespace
   checked at closure.

2. Fresh full physical lane: existing `scripts/run_physical_mongo_tests.py`, equivalent
   runner.main invocation with the approved loopback URI constructed only in memory.
   **PASS:24 suites,156 collected,156 passed,0 failed,0 errors,0 skipped; exit0.**
   Runner collection checks suite ownership before executing its explicit inventory.
   Existing fixture safety generates new allowlisted namespaces and cleanup drops only
   the validated generated database, retries and verifies absence. No cleanup exception
   occurred. No retained database or clm_poc test/cleanup took place. Container lifecycle
   remains coordinator-owned.

3. F8 independent actual-render challenge: read the real Dashboard.tsx, bundle entirely
   in memory with esbuild `write:false`, load through CommonJS and render its exported
   DashboardView with the installed ReactDOMServer, QueryClientProvider and MemoryRouter.
   jsdom inspected actual KPI/table cells. **150 assertions PASS**, exit0, across team
   and mine for0,12,999,1000,1001,59999,60000,60999,119999,3599999,3600000,
   3601000,86401000ms and null/undefined nullable metrics.
   Observed examples:0/12/999ms -> `< 1s`;1000ms -> `1s`;59999ms -> `59s`;
   60999ms -> `1m`;119999ms -> `1m 59s`;3601000ms -> `1h`;
   86401000ms -> `1d`; nullable absent metrics -> `—`.
   Non-null case_elapsed_ms was used on case items; null/undefined were challenged only
   on nullable timing/workload surfaces. No file, backend duration,
   browser clock, HTTP response or server was changed. Expected React SSR layout-effect
   warnings were suppressed in this numerical probe; they are not test failures.
   Source inspection confirms expanded top-case duration uses the same wrapper.

4. Direct raw comparison against previous reviewed feca3d245e0f9752774fdba57a82c522e2eb0e2a:
   **34/38 paths byte-identical**. Only the planner, newly archived round4 FAIL report,
   Dashboard view and Dashboard rendering tests differ. Thus preceding independent
   backend148PASS26.40s, advancing-read/precision/safe503 probes and public/static/
   governance receipts remain applicable to unchanged files; they are explicitly prior
   executions, not claimed fresh reruns. The physical lane was rerun freshly anyway.

F8 failing-first coordinator receipt: `.runtime/pr95-f8-red.log` records7 failures and
16 passes in23 tests before the correction; `pr95-f8-green.log` records23 passes
afterward. The reviewer inspected both and independently exercised the corrected real
render; authored assertions alone did not establish acceptance.

## Coordinator execution receipts

These are coordinator executions inspected by this reviewer, not reviewer reruns.
Current receipts exercise the frozen43b313d content; prior-file applicability is
bounded by the raw comparison above.

| Lane | Actual result and receipt |
|---|---|
| Complete ordinary backend | 2785PASS,162SKIP,3warnings,1051.49s(17:31), exit0; `.runtime/pr95-r5-backend.log`. Current outcome inventory2947. The earlier failed HTTP seeder node passed within this full run in6.80s. |
| Complete frontend |57files,940PASS,12.19s; `.runtime/pr95-r5-frontend.log`. |
| Frontend typecheck/build | PASS, exit0 in the current frontend receipt. Existing Vite>500kB bundle warning remains. |
| Actual guarded local Mock browser |9PASS,38.0s; `.runtime/pr95-r5-browser.log`. |
| Current six governance scripts | All exit0/PASS; `.runtime/pr95-r5-static.log`. check_project_state, check_architecture, check_tooling_config, check_policy_authority, check_external_provider_readiness and check_secrets. |
| Public contracts/delivery |48PASS,6.32s; `.runtime/pr95-r4-static-contracts.log`, unchanged owning content. No private archive validation is claimed. |
| Ruff/mypy/dependencies | Whole backend RuffPASS, mypy127source filesPASS, pipcheckPASS in the same r4 receipt; owning backend/scripts/manifests are unchanged. npm dependency tree PASS as recorded in the preceding reviewed receipt. |
| Governance and runner unittests |220PASS,88.106s; `.runtime/pr95-r4-governance.log`, unchanged scripts/tests. Expected adverse E2E failure text occurs inside overall unittest OK. |

Current full-backend command, from apps/backend, with candidate backend/root PYTHONPATH,
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 and PHASE12_MONGO_URI removed:

```text
python -m pytest -o addopts= -p anyio -p no:cacheprovider -q -rs --tb=short --durations=10
```

Other exact command families: frontend `npm test -- --reporter=dot`,
`npm run typecheck`, `npm run build`; configured guarded `scripts/run_e2e.py`
selection for PR95 Dashboard v2, PR89 streaming resources, login, RM/Director, bounded
portfolio/deletion, activity, responsive shell and session reset. Browser evidence
includes a real normal-UI synthetic Mock completion after explicit Review & Send,
a visible positive Singapore weekly segment and no invented Australia segment,
40-day JS clock skew, scope/date requests, navigation/history/reload and logout/role
reset. No browser response mocking substitutes for that acceptance flow.

## Contract, architecture and security review

No current required defect remains established. Existing DashboardService,
CaseQueryService, portfolio adapters, canonical envelope, AuthProvider/QueryClient,
navigation and view owners remain authoritative. There is no new service/repository/
provider/framework, reversed dependency, route-to-Mongo query, second Decimal/
authorization/persistence owner, target-ledger bypass or dormant runtime composition.
No new ADR is required for these bounded existing-owner extensions.

Creator identity is a validated read projection of already retained evidence. Unknown
legacy creator is not inferred; the durable schema stays10, with strict historical
read compatibility. Insert-only create, update-only mutation, identity/revision CAS,
locked sensitive reauthorization, deletion/no resurrection and restart/no replay remain.
Activity created_by filters case creator, not event actor; JSON/CSV share the existing
authorized dependency. Browser output stays minimized and text-escaped.

No new secret, raw sponsor/provider/document body, private-error projection, TLS bypass,
auth grant or persistent sensitive browser storage was found in the inspected task
delta. Timing/persistence failures use fixed sanitized503 DASHBOARD_UNAVAILABLE. Secret
pattern checks are bounded evidence, not a proof against every possible disclosure.
No sponsor endpoint/schema/mapping/authentication/SLA/approval rule was inferred.

## POC catalogue and adverse regression assessment

**PASS for this bounded POC regression assessment.** The current full ordinary backend
completed successfully, supplemented by fresh independent24-suite physical156PASS and
current actual-browser9PASS. The reviewed Dashboard delta does not change catalogue,
orchestration or target-ledger behavior.

The accepted catalogue is unchanged. Source inspection and the complete current backend
plus physical/browser evidence assess:

| Scenario/invariant | Assessment |
|---|---|
| Canonical Mock happy/missing/unknown/policy-failure/partial-amend outcomes | Completion, review and failure remain distinct; missing/unknown source evidence cannot fabricate completion. |
| Required-stage and malformed-provider stopping | Controlled Search/Shell/Policy failures, malformed responses and loop guards stop prohibited later operations; safe terminal/uncertain states remain retrievable. |
| Document/reconciliation/ownership blockers | Unresolved conflict, missing/low-confidence evidence, cycles/incomplete ownership and stale/cross-case decisions remain blocked under current owners. |
| Target order and no replay | Existing early Search/confirmation Search, ledger-owned Shell/Policy/required Amend and identity readback order is preserved; retained uncertain attempts cannot replay and receipt-finalization recovery adds no target mutation. |
| Persistence and scope | Physical restart/read/CAS/deletion/creator parity and scope matrix pass without provider replay or retained database access. |
| Truthful labels and approval boundary | Actual local Mock completion and Available label remain factual; no Live, regulatory/GoldTier approval or Ready-for-Approval claim follows. |

Representative inspected regression owners include test_onboarding,
test_clm_orchestration, test_zero_touch_orchestration, strict target-response tests
and the runner's24 physical suites. Existing accepted D2/readback and confirmation
amendments govern current call sequences; historical four-operation examples do not
silently replace the current ledger contract.

## Impact disclosure

| Surface | Effect |
|---|---|
| API/shared types | Additive dashboard fields, scope/date inputs, activity creator selector and case_elapsed_ms changed. Legacy omitted-date/team and historical_trend behavior retained. |
| Durable schema/write/CAS/index | Unchanged; bounded creator read projections/validation changed. |
| Connectors | Unchanged. |
| Configuration/dependencies/lockfiles/CI workflows | Unchanged; browser inventory assertions updated for actual selectors. |
| Business rules | Owner-authorized descriptive dashboard cohort/metric calculations changed; sponsor policy/SLA/approval rules unchanged. |
| Mappings | Unchanged. |
| Auth/security | Grants and owners unchanged; authorized filter/cache inputs extended and fixed safe timing/persistence503 added. |
| Architecture | Existing owners/direction retained; no new owner or ADR. |
| Provider status | Mock/Local/Partial/Dormant classifications unchanged; no Live upgrade. |
| Runtime | Dashboard/cohort/activity/metrics/presentation changed; F8 only reuses the canonical duration presentation. |

## Required fixes, limitations and readiness

**Required fixes: none.** F1-F8 are corrected on the frozen reviewed content.
Local implementation acceptance is exact PASS; this is not a publication action.

The four earlier FAIL reports remain immutable evidence for their own freezes.
Prior01bf826 full backend1FAIL/2781PASS/162SKIP in1100.12s remains a failed historical
attempt: its seeder HTTP body-read timeout was not causally attributed, and the isolated
1PASS8.35s never cleared the broad failure. Prior physical155/1 failures remain
historical F7 evidence. Fresh completed current lanes supply their own bounded
acceptance evidence; no assertion, timeout, skip or criterion was weakened.

Current skip reasons were independently counted from the complete receipt:156 opt-in
physical Mongo cases were skipped only in the ordinary lane and all156 passed in the
fresh physical lane. Six unchanged optional native-Tesseract cases remain unexecuted
because local Tesseract is unavailable; no real OCR claim is made here. Three expected
Pydantic serializer warnings come from the provider-conformance trailing-LF bypass,
malformed-address and malformed-timestamp DTO challenges. No failure/error occurred.
The two slowest100-iteration orchestration regressions completed in100.44s and89.85s;
long progress pauses were active execution, not a skipped or interrupted lane.
Private sponsor archives and actual Live/external smoke are NOT_VALIDATED/NOT_RUN.
The inherited locked npm advisory inventory remains6 (1moderate,3high,2critical),
with no dependency change in PR95; this gate does not claim their remediation.
Existing bundle-size/React warning limitations remain. This review adds no production
scale, distributed atomicity, full MIS, complete audit/retention or legal UBO claim.
Later sponsor identity/auth/TLS, full mappings/contracts, source precedence,
privacy/retention, related-party/hierarchy and RFA/Live dependencies remain outside PR95.

The frozen local PR95 implementation is accepted for coordinator handoff. The next
authorized action is the coordinator's report-only handoff commit, unchanged-content
verification, latest-main/PR-head assessment and clean committed integration gate.
No next product phase is authorized or begun. Real ACRA/GoldTier Live readiness is not
established by this local Mock/Local/physical acceptance.

The final clean committed pre_pr_check and checklist are a separate integration gate,
pending the coordinator's authorized report-only handoff commit and latest-main/PR-head
assessment. They were NOT_RUN by this reviewer and are not silently reported passing.
No publication or next phase follows from this report. Push, PR creation/replacement,
shared-history rewrite, PR96 mutation and PR merge remain unauthorized. Humans merge.

Hosted CI does not certify this local candidate. Coordinator observed published PR95
head1c1fd9f still unchanged; historical push run39051770323 attempt1 did not start jobs
because of billing. No executed hosted CI PASS is inferred. Local candidate acceptance
and final integration readiness remain separate from remote mergeability/CI.

## Git closure and complete reviewed inventory

At closure the implementation HEAD/tree, exact38-path set and all raw hashes remain
unchanged. Initial and pre-report tracked/index states were clean. The index remains
empty and this assigned report is the sole new nonignored path. Explicit report
whitespace and complete changed-path whitespace pass. This reviewer fixed no reviewed
artifact, staged/committed/pushed nothing, switched no branch, made no merge/PR action
and changed no container lifecycle. The four previous FAIL reports remain unchanged.

| Reviewed path | Raw-byte SHA256 |
|---|---|
| `.ai-pipeline/001_planner/PR95_DASHBOARD_INTEGRATION_REMEDIATION.md` | `1f0de633d672b82420596b44daf15a021f07790145749731e615faa9751faa82` |
| `.ai-pipeline/reports/PR95_DASHBOARD_ACCEPTANCE_QUALITY_GATE.md` | `cdc38eb9101c6af98eb181db5b1dfb66eb7f111491f8c728749c70d1f9282586` |
| `.ai-pipeline/reports/PR95_DASHBOARD_FINAL_ACCEPTANCE.md` | `ffbe77c76e7efa2ae052d36a42e62d3bb8ca27edd7d877228e58571fcb735ad8` |
| `.ai-pipeline/reports/PR95_DASHBOARD_FINAL_QUALITY_GATE.md` | `9e51a0a43b25adef7b4ce82f7e819f408a58e0d9fd71473425bab395f3caf126` |
| `.ai-pipeline/reports/PR95_DASHBOARD_QUALITY_GATE.md` | `d0f1dd49d050b47acec242f5037f59efab50a0897e0da57e9c9247b8bed03f80` |
| `.ai-pipeline/reports/PR95_DASHBOARD_REMEDIATION.md` | `04230b1e94e699dae93cb125c01279a1a9de85ac501a832cd26a56a4f2c40c63` |
| `apps/backend/app/domain/case_management.py` | `ab2ef38e60c30e45f0f425c3e20c02510ed7b30fa0c7f47a70c3e6c84e73cd70` |
| `apps/backend/app/domain/dashboard.py` | `f63a1fab027bd2efc2f8fc0281d44ad99c04f7eb1149dbffd44faab97ffdcb2a` |
| `apps/backend/app/main.py` | `66d1690d2c0b7cedae3fa0c588ed685fd84a8638038994913c2cc5e0b3af7101` |
| `apps/backend/app/persistence/mongo_case_store.py` | `2e3c226bff1dff0ba5ca2daddc6e64b46587c753ebe90881156d2e653faf7377` |
| `apps/backend/app/services/case_portfolio_repository.py` | `63975c7e8fb482fbebafb36dc1dc26aef3a79f25a94ecfdb10785db3014c9d07` |
| `apps/backend/app/services/case_query.py` | `f9859d74d3a150aad6b9d4fff2941c237ae49b5dc9482aaa74ac3dc7054f7657` |
| `apps/backend/app/services/dashboard.py` | `4d3020e848c742daa95dcf7b54c43589508bf4a5f4cceafd29c92cede28eba5f` |
| `apps/backend/tests/s1_date_filter_fixtures.py` | `601eed0557b79fc1eb946ae5d6c366d484d867162fd405cff1d25e9040b8add4` |
| `apps/backend/tests/test_attention_queue_backend.py` | `5f22f226fde72b3edd55d5387176cb4221ede034e28948cb39b2df034ea70ecb` |
| `apps/backend/tests/test_phase13_dashboard.py` | `02cc2fe4619d9d5b55162d13cf5c42e59170a3bdc4de770ff490cf1ee4b98861` |
| `apps/backend/tests/test_phase13_real_mongo.py` | `7183b1314b758ce23bc6a63b87024b1276bcd1338d02060e4d800a48af00d2e7` |
| `apps/backend/tests/test_phase17_case_activity.py` | `b05fd3538da703105173d62f67e236d4678a71ef881cb5d92c60a4f11942680c` |
| `apps/backend/tests/test_phase18_case_portfolio.py` | `4e49a65b11249df1c84afa72ee4a8d9ed17d85fac656fe60010c0650d0ed4ca4` |
| `apps/backend/tests/test_pr95_dashboard_compatibility.py` | `ca658c796ee21012880f7e082a624f158dd95bcfbad4ff17d548418c045b6bfe` |
| `apps/frontend/e2e/pr95-dashboard.e2e.ts` | `1952926800fa993d8c9c832cc40d02ac7207de0ad6a615a75151296c4904032e` |
| `apps/frontend/src/api.ts` | `11ab366786ea50336d496d35635b92e3eb5f8f37ad3ff9ba56f4fa2f195fa346` |
| `apps/frontend/src/App.test.tsx` | `99e49be81eab702f5278437dc036dbbcd23c03ec2bc9f4f427eee895d5d557a2` |
| `apps/frontend/src/App.tsx` | `f0b7cc0687fa592a9c4dd0ec684ced2296bca4c5d415458ae4b6cadbb3f7e922` |
| `apps/frontend/src/caseQueries.ts` | `ae6f64366ef4ce93842f17d590c2367bfe4e39348039594289d5b5493e5c4053` |
| `apps/frontend/src/Dashboard.test.tsx` | `319cb6e1d3b0c3e9521e6e0802a32a21ec5200d5dced153e2acddc6f1b4b5396` |
| `apps/frontend/src/design-system.css` | `f39dfc84c32c1196bf96d95e7f7c0d3cd85ca53ffff225523a0ddcafc8306160` |
| `apps/frontend/src/pages/Dashboard.tsx` | `305b0f203d35c42ad4010d67c02a429d0f060ebd83e2ffee103908aaf0bf05a7` |
| `apps/frontend/src/pages/DirectorTeamFilter.tsx` | `2cc06b184bfe1c7ef5efc03d7a8aaf0c4d1608e3da81d4dbc29c8e97c4eba60c` |
| `apps/frontend/src/Phase14CaseManagementPerformance.test.tsx` | `1c803b6a1e3e782f52e83d7de3f4a5bf9ab7913167951407053796cc1e8cbfe8` |
| `apps/frontend/src/Pr95DashboardCache.test.ts` | `61285b344624e17c324e19f8edfdbbf495392371c22e4f6a2dba58f38ddc2c7e` |
| `apps/frontend/src/styles.css` | `fbc8f6e0c1e14f84196b126f4fb6744de14541210f1765e6010be13c2ddd596a` |
| `apps/frontend/src/types.ts` | `2ee881bbc1f3d4d36bcb8a496969ab2bc7f528967852551c084e0445a8bcfa3c` |
| `docs/ARCHITECTURE.md` | `6ca01c696fe2b92d07bcfcc1448f3e5eabdd3cb36245a600a233cce287493708` |
| `docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md` | `9534c1a003ca8f9e0a9f2d9796fb4e371b1657c13af24730fa7a8855eba4d3ef` |
| `docs/contracts/CASE_TIMING_PROFILE.md` | `e7fba60fa127924ee5982094e2942e16a4d8eb5d28973243ba7439b798ddb623` |
| `docs/PROJECT_STATE.md` | `19727f85d8245cc01838351dcdb89263e089d4623731a8a10afd066ab4048b1c` |
| `tests/test_run_e2e.py` | `8da5fc7ce5dc7715f90f4ee1af7728178402113849fda523383c95071c2016dc` |
