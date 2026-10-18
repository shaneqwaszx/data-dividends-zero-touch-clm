# PR95-R5 independent full-PR adversarial re-review

## Outcome and role boundary

**PASS -- CLEAR FOR THE SEPARATE FINAL INDEPENDENT QUALITY GATE.** No required
implementation finding remains in this comprehensive adversarial assessment of the
complete accumulated PR95 candidate against current main. All six authorized R5
corrections and both preserved R4 frontend corrections are independently verified.
No new required defect outside the owner's bounded authorization was established.

This report is the prerequisite full-PR adversarial assessment, not the subsequent
final acceptance Quality Gate. The complete ordinary backend run is still pending at
this verdict and belongs to the following acceptance stage. No exact final-QG PASS,
local commit permission being exercised, clean committed pre-PR result, publication
readiness or hosted Codex approval is supplied by this report. The coordinator must
obtain that separate fresh final gate and complete the authorized later local stages.
No push, hosted-review request, GitHub thread change, PR96 modification or merge occurs.

## Exact reviewed identity

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/pr95-dashboard-remediation-20261018/data-dividends-zero-touch-clm`.
- Branch: `codex/pr95-dashboard-remediation-20261018`.
- Committed/published baseline HEAD: `e970a0b31fe2cf2c1617dcc759c9d2131433ba68`.
- Committed baseline tree: `8abb0de47de69a24f88550f3ddece82c03b7a626`.
  These committed identities exclude the intentionally uncommitted R4/R5 corrections.
- Comparison base/local origin/main: `4a280da473dcdbeb345ffdfa79aaa4c001e75f62`.
- Original teammate `1c1fd9fbf1a68f79137d150ac8609cf811b10938` and accepted main
  independently remain ancestors of HEAD. Index is empty. Root owns remote-ref and
  primary/worktree-preservation checks; this reviewer made no fetch or Git mutation.
- Complete frozen input: all59 paths below, including new task-owned tests/reports,
  not merely the latest R5 diff. Freeze: `.runtime/pr95-r5-scoped-frozen-r2.json`.
- SHA256 of the compact sorted path/hash map:
  `114f4306016116c12dc43076ba17da3f07757fdbb158d229b101181f7ab75d22`.
- Independently reproduced tracked binary diff SHA256 against origin/main:
  `d0a582c04360a97ad90e66525c558b26a212ca9445dce393c30e80db4dd30162`.
  All59 raw path hashes are authoritative, including paths Git diff omits as untracked.
- V1 map `bf92c2a0efcfdda97e2441245033ea1db80d0d4f77529a94bd5c3c9fb330a8a3`
  is superseded only for the new physical query spy and implementation evidence record.
  No product byte changed between those freezes. V2 was reverified before independent
  runtime execution and after all runtimes before this report; no reviewed implementation changed.
- Immutable R4 FAIL report remains SHA256
  `3334134fbeef63ae2a30fe934e1fee43e9168a1d17ab5e82979d786e1292d6ee`.
- Independent design preflight PASS remains SHA256
  `443a25ec606b42195460d702b11c2299ac6a43c827b45869a7e9e01f4b28fa32`.
  Its exact approved plan SHA256 is
  `337ca8bc724ebb76d1905434ce81da6030a1a8466c364a77fe7c1869db12f43f`.
- This sole reviewer-authored report is additional supporting content, outside its own
  self-referential hash map. Its hash must be recorded by the coordinator/final reviewer.

Authority/read-set: complete R5 owner attachment; root/backend/frontend AGENTS;
canonical skill routing, quality-gate role boundary, integration-safe-development,
persistence-schema-change, architecture-change-review, frontend-state-cache-change,
integration-security-review/checklist; reviewer/security roles; current workflow/merge
protocol and coordination instructions; emitted dev_context union for BACKEND_DOMAIN,
BACKEND_API, AUTH_RBAC_SECURITY, PERSISTENCE, FRONTEND_UI, FRONTEND_STATE_CACHE and
CI_TOOLING; architecture/project-state/provider and sponsor-authority context; case
access/timing/activity and persistence contracts; approved plan/preflight, immutable R4
assessment/handoff/design, current implementation and historical attributed gates;
all59 changed-path categories, owning implementations/tests and current runtime receipts.
Historical verdicts are not acceptance evidence for this changed candidate.

## Authorized finding dispositions

| Finding | Independent disposition |
| --- | --- |
| P2-06, excluded Mongo automation decoding | VERIFIED FIXED. Dashboard resolves backend-authorized case IDs, eagerly captures one finite raw batch, takes exactly one final Dashboard clock, derives the existing Singapore cohort, then strictly reads only selected IDs. The real guarded Mongo run covers other-team/excluded-date malformed evidence, selected failure, role/team/unassigned/mine parity, zero and201+ cohorts, query shape, midnight and deletion/lifetime behavior. |
| R4-A1, negative retained stage duration HTTP500 | VERIFIED FIXED. Every selected automation's retained stage samples are checked before DTO construction through CaseTimingDataInvalidError. Negative selected samples return precisely sanitized503/DASHBOARD_UNAVAILABLE; excluded samples do not decode, zero/missing/exact positive samples remain truthful. No clamp, invalid-record skip, global validator change or blanket Pydantic catch. Independent extra probe also rejects a negative sample in a201-record selected cohort. |
| R4-A2, misleading200-case prefix | VERIFIED FIXED. All cases, Your cases and Blocked cases receive authoritative cohort totals, disclose the loaded subset and local-filter/pager limits, link the existing Cases route and avoid complete-cohort empty claims. Mine says creator-only. Component scenarios cover0/1/200/201/250; actual browser creates205 cases and verifies both views/subset navigation without removing the cap or loading all cases into the product UI. |
| R4-V1, browser inventory mismatch | VERIFIED FIXED. Current discovery110 reconciles the exact supporting expectation; complete disjoint shards are55/55. Existing9960-second launcher bound and234-minute CI outer budget, safety deadlines and cleanup assertions remain. The focused tests and complete244-test governance lane pass. No workflow or skip changes. |
| R4-M1, invalid empty pagination | VERIFIED FIXED. Empty local pagers display0of0, with Prev/Next disabled; nonempty ranges and clamped paging remain. Tested across both views and all empty local list sections. |
| R4-M2, unnamed date selector | VERIFIED FIXED. Native selector has the explicit accessible name Dashboard date range. Its four options,30d default, callbacks, query identity and date semantics remain. Browser locates it by that name. |
| P2-07, Recent Activity100-event truncation | PRESERVED AND VERIFIED. UI holds one bounded10-event server page, advances by offset/has_more, supports Prev/refresh/retry and distinguishes loading/errors/empty data. It invents no total; offset cap directs to Audit. Current actual browser traverses the larger205-case fixture's complete retained event oracle, including beyond100 events. |
| P2-08, mouse-only stage disclosure | PRESERVED AND VERIFIED. All six native buttons have stable unique controls/regions and aria-expanded, preserve sort/expanded state and focus. Actual Tab/Shift+Tab/Enter/Space and repeated toggles execute in the browser. |

## Scoped-read architecture and adverse challenge

The existing DashboardService depends only on the existing automation repository port.
The service receives an AutomationReadBatch protocol, not raw documents or a Mongo
store. The existing Mongo automation adapter translates store-decoded snapshots. The
store owns private raw envelopes and the unchanged strict codec. No route-to-Mongo,
second authorization/persistence owner, new schema/index/migration or provider dispatch
was introduced. The preflight's no-ADR conclusion remains applicable to this bounded
existing-owner extension; architecture/persistence documentation records the lifecycle.

The store executes one `_id/$in` predicate over the finite already-authorized UUID set,
fully materializes the driver cursor and closes it before yielding. Empty authorized
input makes no query. The selected argument must be an actual frozen UUID set and a
subset of capture authority. Only canonical selected Mongo keys route full decoding;
selected duplicate/identity/schema errors fail closed. Excluded nested data is never
validated through the complete-envelope codec. There is no selected-ID fetch after the
clock, per-case fan-out, whole-store fallback or silent memory fallback.

The adapter/store and memory batch consume selection on success or failure, reject
foreign/invalid/double/post-close use and clear retained raw/model/callback references.
The generator context cannot be re-entered. Independent probes directly inspected cleanup
after a selected-schema failure and foreign subset rejection. Defensive model copying
preserves the private ownership binding; later repository update/deletion and returned
model mutation cannot change captured data. Shared ordering is stable regardless of driver
order. No serialization, cache, logging or API exposure of the opaque handle is added.

Missing/deleted-before-capture automation is omitted, never fabricated or recreated.
A later deletion does not retroactively change the owned request snapshot; the next
request sees absence. This is an existing sequential live-read POC consistency limit,
not cross-read transactional isolation or a persistent snapshot. Startup still performs
its existing strict whole-store validation; this change does not promise that an app
with corrupt durable data can restart. Driver/transport corruption remains unavailable.

The date cohort still uses the sole post-capture final observation, including the
Singapore-midnight interleaving. Legacy UTC trend and returned ages/durations use that
same observation. CASE_TIMING_PROFILE was not edited by R5. The owner-authorized raw
date-superset capture changes no timing rule: authorized IDs precede capture; final
cohort IDs precede full decode. Creator-only mine filtering follows cohort validation,
so authorized teammate cases still supply the requesting resolver's retained fix evidence.

## Comprehensive accumulated-PR challenges

| Dimension | Result and practical boundary |
| --- | --- |
| Authorization/privacy | Backend case-query/access owners remain authoritative. RM/onboarder exact team, Director all/team/unassigned and HR denial remain; selected inaccessible/absent case activity retains safe404. Creator predicates intersect authorized scope, never grant access. No other-team metric/person evidence is projected. |
| Creator/resolver semantics | Case counts/oldest-open use creator; one RESOLVED blocker contributes once to its recorded resolver, including resolver-only people and teammate-created cases. Draft/open/cancelled/duplicate decision history cannot add extra fixes. Mine preserves creator-only lists and only the actor's own workload row. Integer resolution/mean arithmetic remains exact. |
| Chronology/error containment | Relevant resolved timestamps pass canonical timing even with unknown resolver. All cohort case timing and stage samples validate before200-row display caps. Invalid selected data returns safe503; excluded unprojected corruption cannot poison another cohort. No blanket exception masking. |
| API/backward compatibility | Omitted date_range remains all-history team scope; historical_trend retains original30 zero-filled UTC days before new cohort filtering. Four explicit date ranges, exact Singapore inclusive-day bounds and additive v2 fields/types remain. Browser explicitly requests30d. |
| Metric truth | Zero-touch means completed cases with no recorded exception interventions/completed cases; final Review & Send still applies. Progress is the approved recorded-stages/6 display formula. Stage samples exclude waiting/resolution; weekly chart uses retained completions in selected cases and eight UTC Monday weeks. No sponsor SLA, productivity/compliance score or Live approval is claimed. |
| Lists/filters/paging | API caps10 recent/5 active/200 selected/3 stage samples remain. Full-cohort totals are separate from truthful local loaded-subset counts. Person/status/age/progress filters search only loaded data, with explanatory text and Cases navigation. Recent activity is genuine bounded server pagination with live-boundary disclosure, not a100-row client slice. |
| Sorting/disclosure/accessibility | All four sortable tables use native buttons/th scope/one active aria-sort; null values stay last, current filters and duration labels remain. Six stage disclosures have stable IDs and labelled hidden regions. Date selector is named; empty pagers are truthful. Component and real keyboard/browser checks pass. |
| Responsive containment | Actual narrow-browser checks preserve contained table scrolling. No R5 CSS/layout redesign occurs. The inherited whole-document mobile overflow limitation documented in R2/R3/R4 remains; this report does not claim global overflow freedom. |
| Cache/session transport | Existing AuthProvider/QueryClient/transport own user/session replacement, logout/401 clearing and cancellation. Dashboard identity contains user/team/view/range; activity adds creator/role/team/offset/limit. Scope changes reset activity; late old-team/session responses cannot publish. Mutation/deletion prefix invalidation covers all variants. No persistent browser evidence storage or retry expansion. |
| Assistant/main integration | Current App contains accepted AiAssistantPanel/context/navigation and exported authenticatedFetch; accumulated App delta removes only the superseded unused local snapshot. Root's actual broader browser lane covers PR89 Assistant and session navigation. Main/teammate ancestry is valid; no shared-history rewrite. |
| Persistence/provider safety | Existing strict schema1..10/identity/CAS/create/update/delete/restart/no-replay owners remain. Full real Mongo24-suite165-item rerun independently passes, including original behavior and new read-path proof. No connector/mapper/provider configuration, target ledger, secret or database namespace change. New tests use synthetic evidence and zero actual provider requests. |
| Runner/governance/hygiene | Browser inventory, shard coverage and measured local journeys fit unchanged safety budgets. No tests/assertions/workflows are removed or weakened. Full-delta Git whitespace and all task-owned new-file whitespace pass. Seven R3 scripts, narrow BLE001 containment rationale and accepted PR96 governance remain preserved. |

## Earlier R2/R3 preservation

All five R2 findings remain corrected: creator validity precedes activity creator
filtering; reversed successful-resolution chronology is contained; selected timing
validation precedes display caps; mixed status tables/cells distinguish case age from
case duration; every sortable header is keyboard operable. Current tests/source and
independent execution cover those behaviors, rather than borrowing the old gate verdict.

All15 R3 Ruff diagnostics remain resolved in the same seven unchanged script byte
identities: benchmark3 RUF100; happy-path generator1 RUF100; concurrency1 RUF059;
load3 FURB157; optimization BLE001/RUF059/I001/FURB157; sponsor fixture2 I001;
classification fixture1 I001. The approved sole BLE001 annotation still contains
unexpected resource-sampler errors without inventing evidence. The exact unused-binding
source barrier, Decimal values, import/fixture guards and missing-OCR cleanup tests are
retained. Current broad Ruff and fixture/performance tests pass. R2 FAIL and R3 PASS
remain immutable attributed history, not rewritten by this assessment.

## Fresh execution evidence

All reviewer runtimes below exercised frozen V2 input. Logs use the unique current
`.runtime/pr95-r5-scoped-` prefix; similarly named older-round files are not substituted.

| Lane | Observed current result | Evidence |
| --- | --- | --- |
| Independent backend dashboard/compatibility/scoped-read/activity/portfolio/R3 fixtures |94 passing test items, exit0;94 passing dots, no skip/failure markers | audit-backend.log |
| Independent Dashboard/cache component tests |41 PASS across2 files,3.21s | audit-ui.log |
| Independent additional adverse probes |7 PASS: post-capture update immutability in both modes; failure reference cleanup in both modes; excluded unknown schema; selected schema failure/raw cleanup; negative stage in201 selected records | audit-probe.py; audit-probe.log |
| Independent actual configured PR95 browser |2 PASS,25.7s; real guarded local HTTP/process/Mock behavior, native keyboard,30d/default/range/navigation,205-case subset and bounded activity traversal | audit-browser.log |
| Independent COMPLETE guarded physical Mongo |24 suites,165 collected/165 PASS,0 failures/errors/skips,exit0 | audit-physical-full.log |
| Coordinator complete frontend |955 PASS/57files,12.45s | frontend-full.log |
| Coordinator typecheck/build/npm dependency tree |PASS; existing680.40kB Vite chunk warning retained | typecheck.log; build.log; npm-ls.log |
| Coordinator API/contracts |44 PASS,3.16s | contract.log |
| Coordinator governance/performance |244 PASS,88.041s; expected injected runner-failure output belongs to passing harness tests | governance.log |
| Coordinator broad/backend Ruff and configured mypy |PASS,0 Ruff errors; mypy127 sources | ruff-broad2.log; ruff-backend2.log; mypy-configured.log |
| Coordinator static/security and dependency integrity |All six checkers PASS; pipcheck PASS | static.log; pip-check.log |
| Coordinator broader actual browser |8 PASS,35.0s: Assistant, auth, RM/Director, portfolio/activity paging, responsive containment and logout/role reset | browser-broad.log |
| Coordinator corrected physical focused run |13 PASS,0 skips; supplements, does not replace, the independent complete165 rerun | physical-focused-final.log |
| Complete ordinary backend for R5 |PENDING at this report; required before final acceptance. Earlier R3 numbers are historical only. | Separate following acceptance stage |
| Final independent Quality Gate |NOT_YET_RUN at this report; this clear assessment permits that distinct review to begin | Separate reviewer/report required |
| Actual clean committed pre-PR checker |NOT_RUN at this report; candidate remains uncommitted pending exact final independent PASS | Coordinator's later authorized stage |

The physical service was independently verified as exact owned container
`6dd114f17e0d0a02114a0d627e3a68be4653e1284f3a360ad70c664e31419046`,
`mongo:7`, loopback27029. The canonical guarded runner creates newly generated
allowlisted databases; existing safety helpers reject protected names and verify cleanup
absence. The complete passing suites exercise that cleanup. No connection to clm_poc,
dotenv read, actual external provider call or URI/credential disclosure occurred.
The service remains coordinator-owned for the following final gate. Browser and Mongo
runs are complete; this reviewer released the exclusive runtime slot with none active.

## Preserved failures and limitations

- R4's independent FAIL/BLOCKED remains unchanged. Its six remaining findings are
  disposed explicitly above; the verdict is historical, never silently changed to PASS.
- Initial complete R5 physical run was164PASS/1FAIL; focused diagnosis was12PASS/1FAIL.
  Safe node/location evidence identifies a new test spy TypeError: find(query) did not
  forward the portfolio's find(query, projection). V2 forwards all arguments and counts
  only raw authorized-ID automation captures, retaining exactly-one-capture and exact
  predicate assertions. No product change or weakened assertion was needed. The full
  independent165PASS rerun, not just focused13PASS, clears the broader evidence gap.
- Initial UI6RED/backend8RED and corrected reruns remain. Early Mongo-double and
  expanded-browser fixture assumptions are identified as harness errors; no unexecuted
  physical/provider behavior is inferred from doubles or synthetic success.
- Noncanonical root type/lint invocations lacked backend-CWD configuration; those
  failures remain recorded. Configured backend mypy127 and Ruff are current passing
  evidence. No configuration or error suppression was changed to obtain a pass.
- Prior full backend2799PASS/164SKIP and physical158PASS are R3 history only. Optional
  actual native OCR availability is not proved here. The following final gate must
  classify current ordinary/physical skips truthfully and retain native OCR limits.
- Existing Vite bundle and SSR test-render warnings and inherited mobile overflow are
  not waived or converted to broader passing claims. Focused browser2 plus broader8
  are relevant journeys, not execution of all110 discovered browser selectors.
- Historical GitHub billing-refused jobs remain NOT_EXECUTED. No new hosted review or
  Actions result is asserted. Mock/Local/Partial classifications and open production
  sponsor questions remain separate from bounded local application acceptance.

## Final boundary and next action

Required adversarial implementation fixes: **NONE**. Overall assessment: **PASS / CLEAR
FOR A SEPARATE FRESH FINAL INDEPENDENT QUALITY GATE**, on unchanged frozen V2 content.
The final gate must incorporate the pending complete backend and all applicable current
acceptance lanes. It must not copy this narrower verdict into final acceptance without
its own exact-content review. Any implementation change or material main drift requires
re-review of the affected frozen content.

The sole tracked reviewer write is this assigned report. Ignored scratch probes/logs
support evidence only. No implementation/test/configuration/ordinary-document fix,
stage/commit/fetch/push/PR action, reset/stash/clean/shared rebase, protected-database
operation, provider call or next-phase work was performed by the reviewer. Preserve
main, teammate history, all registered unrelated worktrees, historical evaluation and
PR96. Publication and final squash merge remain separately unauthorized.

## Complete frozen input inventory

All paths are INTENDED implementation or SUPPORTING tests/contracts/planner/evidence;
none is unexpected. Hashes below bind the reviewed bytes, not merely Git's tracked diff.
This report is the sole additional supporting path.

| Frozen path | Raw SHA256 |
| --- | --- |
| `.ai-pipeline/001_planner/PR95_DASHBOARD_INTEGRATION_REMEDIATION.md` | `66631f8050dcc49bc77c75b0d89fbd8b8f5db69085e53d211fac95dcd9510c16` |
| `.ai-pipeline/reports/PR95_DASHBOARD_ACCEPTANCE_QUALITY_GATE.md` | `cdc38eb9101c6af98eb181db5b1dfb66eb7f111491f8c728749c70d1f9282586` |
| `.ai-pipeline/reports/PR95_DASHBOARD_FINAL_ACCEPTANCE.md` | `ffbe77c76e7efa2ae052d36a42e62d3bb8ca27edd7d877228e58571fcb735ad8` |
| `.ai-pipeline/reports/PR95_DASHBOARD_FINAL_QUALITY_GATE.md` | `9e51a0a43b25adef7b4ce82f7e819f408a58e0d9fd71473425bab395f3caf126` |
| `.ai-pipeline/reports/PR95_DASHBOARD_IMPLEMENTATION.md` | `6deb3a1835c342d6b213f2b39c5ff3c03dc003f23fe5798327ae61b30ef2df0b` |
| `.ai-pipeline/reports/PR95_DASHBOARD_LOCAL_ACCEPTANCE.md` | `d96c0540f58128559a97498118b12561f6dddcb23a420b6f7d72ffdfb72b353e` |
| `.ai-pipeline/reports/PR95_DASHBOARD_MAIN_INTEGRATION_GATE.md` | `8c909a5af89d8853b1ffaec0e897d434c52d57a2f7ff4cb634c46f3a2128e749` |
| `.ai-pipeline/reports/PR95_DASHBOARD_QUALITY_GATE.md` | `d0f1dd49d050b47acec242f5037f59efab50a0897e0da57e9c9247b8bed03f80` |
| `.ai-pipeline/reports/PR95_DASHBOARD_REMEDIATION.md` | `04230b1e94e699dae93cb125c01279a1a9de85ac501a832cd26a56a4f2c40c63` |
| `.ai-pipeline/reports/PR95_R2_QUALITY_GATE.md` | `73029b67883331ab8b6fd5194560758f4c0a8936af1f8a7ac7cc8925e0f0b45e` |
| `.ai-pipeline/reports/PR95_R3_QUALITY_GATE.md` | `5cb6619e70a524c706ba3d1e7dbd472c1ac778694fa8677ce032148fe1d88ad6` |
| `.ai-pipeline/reports/PR95_R4_FULL_PR_ADVERSARIAL_REVIEW.md` | `3334134fbeef63ae2a30fe934e1fee43e9168a1d17ab5e82979d786e1292d6ee` |
| `.ai-pipeline/reports/PR95_R5_IMPLEMENTATION.md` | `b10faa93343e76214940a77d5a4b6e497dacc6e31037f33c67b4ef552270c250` |
| `.ai-pipeline/reports/PR95_R5_INTERFACE_PREFLIGHT.md` | `443a25ec606b42195460d702b11c2299ac6a43c827b45869a7e9e01f4b28fa32` |
| `apps/backend/app/domain/case_management.py` | `ab2ef38e60c30e45f0f425c3e20c02510ed7b30fa0c7f47a70c3e6c84e73cd70` |
| `apps/backend/app/domain/dashboard.py` | `f63a1fab027bd2efc2f8fc0281d44ad99c04f7eb1149dbffd44faab97ffdcb2a` |
| `apps/backend/app/main.py` | `0ceef47b725fd1fe736ef909a05d6dc40ef5ec3f40a305b4732d018f3ad659e6` |
| `apps/backend/app/persistence/mongo_case_store.py` | `14f131929e91450896d8ab395a25fccb8cc14daa040153c35ebc7c4ae7923d61` |
| `apps/backend/app/persistence/repositories.py` | `4b82f6e114e8997718ebb66e8ac07a6ef2fc0d663f002c168fefa11f787c97cc` |
| `apps/backend/app/services/case_portfolio_repository.py` | `63975c7e8fb482fbebafb36dc1dc26aef3a79f25a94ecfdb10785db3014c9d07` |
| `apps/backend/app/services/case_query.py` | `f9859d74d3a150aad6b9d4fff2941c237ae49b5dc9482aaa74ac3dc7054f7657` |
| `apps/backend/app/services/dashboard.py` | `c04d745c81718e6af4ed9740e1b72b9d25b93da60753e14feff20c57c07e6301` |
| `apps/backend/app/services/zero_touch_repository.py` | `96e8e9827f0947412e66f333751859e3f2071b26d4b592fc347dbb8b91ea8455` |
| `apps/backend/tests/s1_date_filter_fixtures.py` | `601eed0557b79fc1eb946ae5d6c366d484d867162fd405cff1d25e9040b8add4` |
| `apps/backend/tests/test_attention_queue_backend.py` | `5f22f226fde72b3edd55d5387176cb4221ede034e28948cb39b2df034ea70ecb` |
| `apps/backend/tests/test_phase13_dashboard.py` | `a9c3ed129d86694e3d4b12ec4ef2523bf58c5e9c2a464a49af0006d2ac0bea11` |
| `apps/backend/tests/test_phase13_real_mongo.py` | `4bcf6acb7e740a7e9ca7c8681a6ae51c152a41c16b51dfa0df9da7605e777a77` |
| `apps/backend/tests/test_phase17_case_activity.py` | `b05fd3538da703105173d62f67e236d4678a71ef881cb5d92c60a4f11942680c` |
| `apps/backend/tests/test_phase18_case_portfolio.py` | `4e49a65b11249df1c84afa72ee4a8d9ed17d85fac656fe60010c0650d0ed4ca4` |
| `apps/backend/tests/test_pr95_dashboard_compatibility.py` | `ca658c796ee21012880f7e082a624f158dd95bcfbad4ff17d548418c045b6bfe` |
| `apps/backend/tests/test_pr95_r3_script_fixtures.py` | `817a34f85e248a1f3e9fb0512e85ed721530cb416cfcb264e18f93bb59ea0476` |
| `apps/backend/tests/test_pr95_r5_scoped_dashboard.py` | `c47a91da7922cf428c5de44047995fe8d22821cd965a32ecc4f64793cf24d0b0` |
| `apps/frontend/e2e/pr95-dashboard.e2e.ts` | `f39926186e9f854801b7334d500586a9fd42a2ddc8d83a83dbdaf894f8141f07` |
| `apps/frontend/src/App.test.tsx` | `99e49be81eab702f5278437dc036dbbcd23c03ec2bc9f4f427eee895d5d557a2` |
| `apps/frontend/src/App.tsx` | `f0b7cc0687fa592a9c4dd0ec684ced2296bca4c5d415458ae4b6cadbb3f7e922` |
| `apps/frontend/src/Dashboard.test.tsx` | `5c30bbedae9654e69c159e30bead8a7b3d6bfe670fbf28210e1e76180e8c1243` |
| `apps/frontend/src/Phase14CaseManagementPerformance.test.tsx` | `1c803b6a1e3e782f52e83d7de3f4a5bf9ab7913167951407053796cc1e8cbfe8` |
| `apps/frontend/src/Pr95DashboardCache.test.ts` | `e176ce8f430dbe776e6cf7e8e9e65cbdcb8bfbb3dcd43365376779af9466ad5d` |
| `apps/frontend/src/api.ts` | `11ab366786ea50336d496d35635b92e3eb5f8f37ad3ff9ba56f4fa2f195fa346` |
| `apps/frontend/src/caseQueries.ts` | `84e4d7de220e3b4bb7b2a6a3a7f629975b13cc7fae1576f7599eb1ef08aff9c7` |
| `apps/frontend/src/design-system.css` | `c778a5c5bb315fd6509622b0b4afa2f37280e1145a2b297845c17494816069cd` |
| `apps/frontend/src/pages/Dashboard.tsx` | `bb5dba6d46653535d046ea43518edfbb38d8c3eae50658f360f83d4201d66d1d` |
| `apps/frontend/src/pages/DirectorTeamFilter.tsx` | `2cc06b184bfe1c7ef5efc03d7a8aaf0c4d1608e3da81d4dbc29c8e97c4eba60c` |
| `apps/frontend/src/styles.css` | `fbc8f6e0c1e14f84196b126f4fb6744de14541210f1765e6010be13c2ddd596a` |
| `apps/frontend/src/types.ts` | `2ee881bbc1f3d4d36bcb8a496969ab2bc7f528967852551c084e0445a8bcfa3c` |
| `docs/ARCHITECTURE.md` | `49a04c0b187b74abce437c24c122d776421c1dafe0e590fa050d4a4d7f610d06` |
| `docs/PROJECT_STATE.md` | `19727f85d8245cc01838351dcdb89263e089d4623731a8a10afd066ab4048b1c` |
| `docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md` | `9534c1a003ca8f9e0a9f2d9796fb4e371b1657c13af24730fa7a8855eba4d3ef` |
| `docs/contracts/CASE_TIMING_PROFILE.md` | `e7fba60fa127924ee5982094e2942e16a4d8eb5d28973243ba7439b798ddb623` |
| `docs/contracts/PERSISTENCE_RECOVERY_PROFILE.md` | `8561be4b0868ec86414ff115137b3d600ff4e7c437af53bb5abb2a2e48e42f60` |
| `scripts/benchmark_blocker_review.py` | `09262762f697c3cb2222ed6fce512f49562099fc81be17a6ec3d429ba58c0c09` |
| `scripts/generate_zero_touch_happy_path_documents.py` | `d72fc2d71a6ab363af97b4b52c7942c0a67b68572349e8d5eb376dee73d40f8c` |
| `scripts/performance_concurrency.py` | `34ed591b5a5fa3ac7e1f99b97ab14dda16e0b724beba88ecdd875952ef4060ad` |
| `scripts/performance_load.py` | `ae8837ea63dc7bd156167e79d1dbec86f9b4562e40fae28dcc2dbc2923e5aa98` |
| `scripts/performance_optimization.py` | `3f69d2d1c82ba66803d93645336fc8c021fcb5beb46f74932d36ecbd1778d909` |
| `scripts/sponsor_demo_browser_fixture.py` | `8e3cb2bdf20ca34496da2640c4cca087db578c7943bd01a840f582b7b9652a84` |
| `scripts/zero_touch_classification_browser_fixture.py` | `ba6c1e2061020f96fc32f32d4140d34f9df1049aa4584b3b89158824579d6bb7` |
| `tests/test_performance_review_remediation.py` | `0357c613f7b6ad2d2e04c9e799fb46614dca704e606a473a9061b12c9a236a85` |
| `tests/test_run_e2e.py` | `561314f3a3c9e4eeddb547d0689247ca4117261f1b4a42868c03a1181b0823cf` |
