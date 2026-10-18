# PR95 Dashboard v2 latest-main integration Quality Gate

## Executive result

**PASS** on frozen HEAD `cd9da20052ccffaf0c2c25755a5d4ab49fe6efb8`,
tree `1d45dab633c968bd0a40123c8dd8bce8215e529c`, integrated with inspected
`origin/main` `4a280da473dcdbeb345ffdfa79aaa4c001e75f62`.
No required implementation or integration correction remains in the assigned scope.
This is a fresh independent combined gate, including the full PR95 delta and the
new-main governance seams. It does not rely on the implementer's self-review as an
independent verdict. This reviewer implemented none of the candidate.

Local integration acceptance only. The coordinator must still commit this report,
fetch and reassess main drift, and run the clean committed pre-PR checker and canonical
checklist. Those final steps are NOT_RUN by this reviewer and are not reported PASS.
No push, PR creation/replacement, PR96 mutation, PR merge or next phase is authorized.

## Scope, authority and identities

- Checkout: `C:/Users/shane/.codex-clean2/worktrees/pr95-dashboard-remediation-20261018/data-dividends-zero-touch-clm`.
- Branch: `codex/pr95-dashboard-remediation-20261018`; initially clean working tree/index.
- Initial assigned main/BASE_SHA: `cc10a2b626ef92d2dd44600d488c1f15cc4f04f8`.
- New inspected main and current merge base: `4a280da473dcdbeb345ffdfa79aaa4c001e75f62`.
- Current independently reviewed source: `cd9da20052ccffaf0c2c25755a5d4ab49fe6efb8`.
- Previously executed and independently accepted runtime revision:
  `43b313d52de43c02702bf5927c659b43128db197`, tree
  `58c851c48206969d061e7a0b3808f997167718c5`.
- Report-only checkpoint: `7f84aa6f8046ee701f0a55fd83b5c5ff7084419d`.
- Latest-main normal merge: `8041e3db602efb4ed22d99c142da0d72ae80f01f`, parents
  `7f84aa6f8046ee701f0a55fd83b5c5ff7084419d` and
  `4a280da473dcdbeb345ffdfa79aaa4c001e75f62`; tree
  `9fa31387193fd6426b54a9b14a501d13e0e08620`. No merge conflict occurred.
- Current HEAD's sole parent is that merge; subsequent changes are the PR95 planner
  and implementation handoff reconciliation supplements.
- Earlier PR95/main merge: `aa8b9a4333f8858262fe5c15cdccd1e1272ace36`.
- Original published PR95 source: `1c1fd9fbf1a68f79137d150ac8609cf811b10938`;
  original common ancestor `12ba994b8128a4777e12fcc764bafc8f39b9292a`.
- Reviewed frozen inventory: exactly40 paths relative to new main, listed below.
  `.runtime/pr95-review-manifest-main.json` is sorted UTF8 JSON, indent2, final LF;
  independently recomputed SHA256
  `5293f242d4b6e930fc110ba2d6767d2b7ee52642009ec07010aa6769d3170eb5`.
- This assigned report is outside the freeze and is the sole permitted write.
  Coordinator owns Git. Reviewer made no Git, implementation, test, configuration,
  ordinary documentation, container or remote mutation.

Applied canonical `fyp-quality-gate` and `integration-safe-development`, report template
and pre-PR checklist; read AGENTS, deterministic context union BACKEND_DOMAIN,
BACKEND_API, FRONTEND_UI, FRONTEND_STATE_CACHE, PERSISTENCE, AUTH_RBAC_SECURITY,
CI_TOOLING, workflow/coordination/merge protocol, architecture/provider state, assigned
planner/handoff, immutable prior acceptance and F1-F8 history, current access/timing/
activity/portfolio/persistence contracts, relevant decisions/questions, role guidance,
and security/persistence/cache/POC-regression skills. Sponsor-controlled external
contracts and approval authority are unchanged. The accepted PR96 minor recheck was
consulted only to reconcile already-merged governance content, not to change/review
remote PR96 or reopen its scope.

Capabilities actually used: approved escalated read-only shell in this assigned
checkout; Python/pytest/unittest, Git read commands, task-owned local receipts, and one
assigned report write. Reviewer executed no browser/physical/container lane in this
run. No dotenv, protected sponsor archive, retained database, external provider or
secret-bearing connection configuration was accessed. Browser ports8775/4183 and
Mongo lifecycle remained coordinator-owned; no shared resource was stopped.

## Integration and evidence applicability

OBSERVED through `git ls-tree -r` comparisons of the complete tracked trees, not only
selected diff paths:

| Input/surface | Comparison with accepted43b313d | Consequence |
|---|---|---|
| Complete `apps/backend/` |304 mode/type/blob entries identical | Application, all backend tests/fixtures and backend package/config inputs unchanged |
| Complete `apps/frontend/` |190 mode/type/blob entries identical | UI, tests, browser selectors/fixtures, manifests/locks/config unchanged |
| Complete `scripts/` |60 mode/type/blob entries identical | Browser/physical/governance runner implementations unchanged |
| Entire tracked-tree difference |Exactly18 paths:15 new-main paths plus PR95 planner, implementation handoff and archived PASS report | No hidden runtime, dependency, lockfile, provider or fixture change elsewhere |
| Root tests |Only added `tests/test_claude_skill_pointers.py` differs | New affected governance lane executed; previous runner tests preserved |
| Canonical authority |AGENTS, workflow, merge protocol and all canonical skills identical; only skill-index pointer explanation added | No new Codex authorization rule or acceptance owner |
| Previous38-path raw inventory |37 identical; only planner reconciliation supplement differs | F1-F8 fixes and all original product/contracts/tests retained |
| Previous independent PASS |Raw SHA256 `d96c0540f58128559a97498118b12561f6dddcb23a420b6f7d72ffdfb72b353e` unchanged | Prior acceptance remains immutable and correctly attributed |
| All15 new-main paths |Disjoint from40 PR95 paths; mode/type/blob exactly equal new main | No PR95 delta to already-merged PR96 content |
| Current40-path raw manifest |Every raw hash and exact path set match; HEAD/tree and index rechecked | Verdict applies to this complete frozen candidate |

INFERRED, supported by these exhaustive observations: prior runtime executions remain
applicable to the exact unchanged runtime inputs. They are not postmerge reruns.
The full backend, frontend, actual-browser and independent physical/SSR results remain
bound to43b313d and the earlier attributed static evidence. Current affected governance
execution and this fresh independent semantic review cover the18-path integration
difference. No existing runtime receipt is silently relabelled with the new commit.

The15 already-accepted main paths preserved exactly are:

- `.agents/skills/README.md`
- `.ai-pipeline/reports/CLAUDE_DESKTOP_COMPAT_MINOR_RECHECK.md`
- `.ai-pipeline/reports/CLAUDE_DESKTOP_COMPAT_PR96_P2_MINOR_RECHECK.md`
- `.ai-pipeline/reports/CLAUDE_DESKTOP_COMPAT_PR96_P2_REGATE.md`
- `.ai-pipeline/reports/CLAUDE_DESKTOP_COMPAT_QUALITY_GATE.md`
- `.ai-pipeline/reports/CLAUDE_DESKTOP_COMPAT_RE_QUALITY_GATE.md`
- `.claude/settings.json`
- `.claude/skills/fyp-phase-execution/SKILL.md`
- `.claude/skills/fyp-quality-gate/SKILL.md`
- `.claude/skills/integration-safe-development/SKILL.md`
- `.claude/skills/worktree-task/SKILL.md`
- `.github/workflows/ci.yml`
- `.gitignore`
- `docs/development/TOOLING_AND_MCP.md`
- `tests/test_claude_skill_pointers.py`

The CI delta contains exactly one added pointer unittest step and zero removed lines.
All prior jobs, shard/aggregate gates, commands and deadlines are preserved. The four
Claude pointers resolve canonical skills from the current checkout and add no authority.
The manual invocation flags concern Claude discovery only. Shared Claude settings
remain inherited baseline, do not govern this Codex session, and do not override the
owner's already-authorized local merge/commit instructions. Their documented
best-effort limitations remain explicit. No new product/auth/security boundary arises.

## Acceptance and combined review

| Assigned criterion | Assessment and evidence |
|---|---|
| Preserve Dashboard v2 and accepted Assistant |PASS: complete product delta inspected against main; category/team/mine controls, tables, weekly response chart, navigation and intended styling preserved. Assistant package/client/resource owners have no PR95 implementation delta. Unchanged current runtime receipts include full frontend and actual Assistant/browser navigation coverage. |
| Latest-main reconciliation |PASS: exact15-path main preservation, disjoint PR95 scope, valid merge parents/ancestry, no unresolved paths or lost CI checks;227 postmerge governance tests and six configured checks pass. |
| Additive API/default/trend compatibility |PASS: backend/shared DTOs agree; omitted date_range retains all-history/team. Original historical_trend remains30 zero-filled UTC dates before v2 cohort filtering. Browser explicitly requests30d; fresh49-test focused run includes compatibility. |
| Cohort/metrics |PASS: exactly N Singapore created dates, inclusive start/exclusive following midnight; common selected denominator; zero-touch means completed/no recorded exception interventions; recorded automated stages/6 capped and COMPLETED100. Project-defined descriptive metrics remain distinct from sponsor SLA/approval. |
| Creator/resolver attribution F1 |PASS: creator owns case counts/lists; each RESOLVED exception contributes once to recorded resolver at/after resolution. Mine exposes only actor row, including authorized teammate-case fixes; other-team/excluded dates, draft/open/cancelled and duplicate decisions excluded. Fresh focused and preserved physical regressions support this. |
| Truthful timing/provider text F2/F3 |PASS: processing attempts exclude waits/fixes; total means recorded workflow start to completion. Available badge does not claim Live integration. Provider matrix unchanged. |
| Timing authority/precision F4-F6 |PASS: canonical backend case_elapsed_ms and one observation after both retained reads, reused for cohorts/trend/lists/workload. Exact integer timedelta and means floor only submillisecond remainders. Browser display/sort/filter use returned durations; safe503 hides invalid facts/errors. Fresh focused49PASS plus unchanged clock-skew browser/SSR evidence. |
| Strict physical fixture F7 |PASS: completed fixture retains canonical stage prefix/start/metrics and validates before durable create. Codec/schema not weakened. Prior independent fresh24-suite156PASS remains applicable to identical runner/fixture/application bytes. |
| Actual rendering F8 |PASS: nullable guard reuses existing shared formatter for age/workload/stage/fix/run values; zero/12/999ms render below1s, absent nullable values remain unknown. Independent prior actual DashboardView SSR150 assertions and full940 frontend tests exercise unchanged bytes. |
| Backend RBAC/privacy |PASS: authorization precedes creator/team/date aggregation; HR denied; exact RM/onboarder team scope and Director filters; inaccessible/absent404 parity. Creator selector is a strict bounded identity, not caller authority; no provider/database bypass. |
| Frontend cache lifecycle |PASS: user/team/view/range and activity creator in keys, AbortSignal propagated, existing auth-generation/401/logout/session cancellation/clearing and deletion invalidation retained. No persistent sensitive browser store or new authorization owner. |
| Persistence |PASS: nullable creator projection/strict schema9/10 grammar, old absence unknown and schemas1..8 reject later fields; memory/Mongo creator filter intersects scope before paging. No migration/index/CAS/create/update/delete change, fallback or retained-data repair. |
| Documentation and scope |PASS: access/timing contracts and unmerged architecture/state disclosure match current behavior. Initial assigned main is explicitly distinguished from latest main in planner/handoff and this report. Immutable historical gates preserved; no unrelated change. |

Code/architecture review: existing DashboardService, CaseQueryService, portfolio
adapters, authenticated transport/query and view owners remain canonical. Source DTO/
canonical/target direction, one Decimal engine, target ledger ordering/call stopping,
no-replay recovery, backend authority and persistence ownership remain unchanged.
The POC's retained automation aggregation remains linear and read-only; no scale or
atomic cross-read snapshot guarantee is added. No new owner/dependency/ADR is required.

Security/adversarial review: strict creator schema/type/grammar validation and bounded
query inputs, exact authorized scope before projection, legacy unknown handling,
inaccessible404 parity, HR denial, late-session/cancellation tests, safe timing/storage
503 projection, boundary/midnight/precision interleavings and factual duration renders
were inspected. No raw exception/provider/document body, credential, URI, secret or
private evidence is newly tracked/projected. No new TLS/credential/provider activation
or sponsor policy is inferred. Configured secret scan passes with its existing supported
pattern coverage; it is not a claim of arbitrary secret detection.

POC regression: unchanged orchestration/target owners and accepted runtime evidence
preserve Mock completion/review/failure distinctions, missing/conflicting/unsupported
source stops, document/reconciliation/ownership blockers, required-stage downstream
call stopping, ledger-owned Shell/Policy/Amend/readback order, uncertain-attempt no
replay, terminal finality, restart/CAS/deletion and case/team isolation. Actual prior
normal UI synthetic Mock completion still requires final Review & Send. The catalogue
is unchanged; no Live interoperability or Ready-for-Approval outcome follows.

## Execution evidence

### Current postmerge independent executions

- `python -B -m unittest tests.test_claude_skill_pointers -v`: **7PASS**,0.003s.
- Focused `python -B -m pytest -o addopts= -p anyio -p no:cacheprovider -q --tb=short`
  on backend test_phase13_dashboard, test_pr95_dashboard_compatibility and
  test_phase19_case_timing: **49PASS**,1.69s. Bytecode disabled, backend/root/test
  PYTHONPATH set, unrelated plugin autoload disabled, physical URI absent. No Mongo
  connection, cache or implementation write.
- Exact40-path manifest/raw hashes and deterministic serialization hash; exhaustive
  complete-tree blob comparisons; prior38-path raw inventory and immutable PASS hash;
  merge parent/main ancestry and CI one-step-only comparison: **PASS**.
- Fresh reviewer `python -B scripts/check_*.py` executions of the six explicitly named
  project-state, architecture, tooling-config, policy-authority, external-provider-
  readiness and secrets scripts: **all6PASS/exit0** after report creation. No caches
  or other report/source writes; coordinator receipts below are separately attributed.
- `git diff --check origin/main...HEAD`: **PASS**; no unresolved files or staged paths.
  Assigned new Markdown separately checked, since diff checks omit untracked files.

### Current postmerge coordinator receipts inspected

| Receipt | Actual result |
|---|---|
| `.runtime/pr95-main-governance.log` |227 tests,81.485s,OK, coordinator exit0. Includes prior220 plus7 new pointer tests. Expected internal adverse E2E failure text appears inside overallOK, not a product failure. |
| `.runtime/pr95-main-static.log` |Six configured scripts each exit0/PASS: project state, architecture, tooling config, policy authority, external-provider readiness and secrets. |

### Applicable prior runtime receipts, not postmerge reruns

| Lane / evidence owner | Result and exact boundary |
|---|---|
| Complete ordinary backend, coordinator `.runtime/pr95-r5-backend.log` |2785PASS/162SKIP/3expected malicious-DTO serializer warnings,1051.49s, exit0 on43b313d. Earlier failed HTTP seeder node now passes6.80s within this complete run; timeout/assertion/seeder bytes unchanged. |
| Complete frontend, coordinator `.runtime/pr95-r5-frontend.log` |57files940PASS12.19s; typecheck and production buildPASS on43b313d. Existing Vite>500kB warning remains. |
| Actual guarded local Mock browser, coordinator `.runtime/pr95-r5-browser.log` |9PASS38.0s on43b313d: genuine UI Mock completion, visible positive SG/no fabricated AU segment, explicit30d/ranges/scope/back/reload,40-day JS skew, Assistant cancellation, RM/Director/session/mobile/bounded reads. |
| Physical Mongo, previous independent immutable PASS report |Fresh prior24 suites156 collected/passed,0fail/error/skip, exit0 on43b313d; guarded allowlisted generated databases and verified cleanup. Not rerun here; no physical/runtime inputs changed. |
| Actual DashboardView SSR, previous independent immutable PASS report |150 assertionsPASS, actual in-memory bundle/render using ReactDOMServer/jsdom, team/mine and duration boundaries/nullable absence on43b313d. Not a helper-only test and not rerun here. |
| Public contracts/delivery, `.runtime/pr95-r4-static-contracts.log` |48PASS6.32s; prior static backend RuffPASS, mypy127filesPASS, pipcheckPASS. Exact owning inputs unchanged through43b313d and current candidate. Private archives not validated. |
| Previous governance, `.runtime/pr95-r4-governance.log` |220PASS88.106s on prior unchanged scripts/tests; superseded for combined governance by current227PASS, not used to omit new-main testing. |
| Dependencies |Prior locked npm install/tree checksPASS; manifests/locks unchanged. Six inherited npm advisories remain1moderate/3high/2critical. No advisory remediation claimed. |

Earlier full-backend seeder timeout and F7 physical155/1 failures remain historical
failed attempts. Isolated reruns never cleared those broad failures. The completed
43b313d full backend and fresh independent156-test physical acceptance supply their
own evidence; no skip/assertion/deadline weakening occurred. Four immutable FAIL reports
and the immutable43b313d PASS remain unchanged.

The162 ordinary skips comprise156 opt-in physical cases executed separately and6
unchanged optional native-Tesseract cases unavailable. Optional real OCR is unexecuted,
not PASS. No production OCR or Live/provider claim depends on that absent lane.
The coordinator's exact-owned-container cleanup receipt remains historical; this
reviewer did not recreate/start/stop/remove a container or connect to clm_poc.

## Impact disclosure and limitations

| Surface | PR95 delta versus new main | Effect of latest-main integration |
|---|---|---|
| API/shared types |Additive dashboard metrics/scope/date and activity creator filter/case_elapsed_ms; legacy default/trend retained |No further API/type change |
| Durable schema/index/CAS/write/delete |Unchanged; strict creator read projection/validation/filter parity corrected |Unchanged |
| Connector/mapping/runtime configuration |Unchanged |Unchanged; inherited Claude developer-tool settings are baseline, not application config |
| Business rule |Owner-authorized descriptive cohort/metric/attribution corrections |No sponsor/workflow/policy change |
| Auth/security |Existing grants/owners retained; scoped read/cache variants and fixed safe503 |No new grant/Codex approval rule or runtime security boundary |
| Architecture/provider status |Existing owners/direction; Mock/Local/Partial/Dormant classifications retained |No owner/provider/Live upgrade |
| Runtime |Dashboard/activity read model, aggregation/query/presentation corrected |Product runtime unchanged from accepted43b313d |
| CI/tooling |Browser selector inventory assertions updated; no PR95 CI-workflow change |Main adds one pointer-test CI step; all previous jobs/checks retained |

Private sponsor archives and actual external/Live smoke are NOT_VALIDATED/NOT_RUN.
Later sponsor identity/auth/TLS/mapping/source-precedence/privacy/retention/related-party/
hierarchy/RFA questions remain outside PR95. Existing npm advisories, bundle warning,
POC read-model scaling limits and optional OCR infrastructure remain disclosed; none
is represented as repaired or as new acceptance evidence.

Remote state is coordinator-attributed evidence, not a fresh remote observation by
this reviewer: PR95 remains the original published head1c1fd9f, branch
ui-enhancement-v1; historical push run39051770323 attempt1 had no executed jobs due to
billing/spending refusal and is NOT_PASS. The unpublished local candidate has no remote
CI execution. No claim about current hosted mergeability or completed CI follows from
this local gate; future authorized publication must assess both push and pull_request
runs for the exact published content. No remote PR96 action was taken.

## Required fixes, readiness and Git closure

**Required fixes: none.** Fresh independent latest-main integration verdict: **PASS**.
This accepts the frozen candidate and applicable evidence for local coordinator handoff.
Final clean committed pre-PR and checklist are pending separate coordinator actions;
they are not an implementation defect and are not silently certified here. A subsequent
main advance or changed reviewed content requires reassessment/fresh review as applicable.
No next product phase, real ACRA/GoldTier readiness or production readiness is granted.

At closure: frozen HEAD/tree, all40 raw hashes/exact paths and main baseline remain
unchanged; index and unresolved set empty. Working tree contains only this assigned
new gate report, outside the freeze. Complete tracked diff whitespace and explicit
new-report whitespace pass. No implementation fix, stage, commit, fetch, branch switch,
merge, push, PR action, container lifecycle change or next phase was performed by this
reviewer. Root remains the sole Git coordinator.

## Complete frozen reviewed inventory

INTENDED means product behavior; SUPPORTING means required tests/contracts/context or
immutable task evidence. No UNEXPECTED path remains. The new assigned gate report is
SUPPORTING, outside this40-path freeze, and must be added only by the coordinator.

| Reviewed path | Class | Raw-byte SHA256 |
|---|---|---|
| `.ai-pipeline/001_planner/PR95_DASHBOARD_INTEGRATION_REMEDIATION.md` | SUPPORTING | `66631f8050dcc49bc77c75b0d89fbd8b8f5db69085e53d211fac95dcd9510c16` |
| `.ai-pipeline/reports/PR95_DASHBOARD_ACCEPTANCE_QUALITY_GATE.md` | SUPPORTING | `cdc38eb9101c6af98eb181db5b1dfb66eb7f111491f8c728749c70d1f9282586` |
| `.ai-pipeline/reports/PR95_DASHBOARD_FINAL_ACCEPTANCE.md` | SUPPORTING | `ffbe77c76e7efa2ae052d36a42e62d3bb8ca27edd7d877228e58571fcb735ad8` |
| `.ai-pipeline/reports/PR95_DASHBOARD_FINAL_QUALITY_GATE.md` | SUPPORTING | `9e51a0a43b25adef7b4ce82f7e819f408a58e0d9fd71473425bab395f3caf126` |
| `.ai-pipeline/reports/PR95_DASHBOARD_IMPLEMENTATION.md` | SUPPORTING | `6deb3a1835c342d6b213f2b39c5ff3c03dc003f23fe5798327ae61b30ef2df0b` |
| `.ai-pipeline/reports/PR95_DASHBOARD_LOCAL_ACCEPTANCE.md` | SUPPORTING | `d96c0540f58128559a97498118b12561f6dddcb23a420b6f7d72ffdfb72b353e` |
| `.ai-pipeline/reports/PR95_DASHBOARD_QUALITY_GATE.md` | SUPPORTING | `d0f1dd49d050b47acec242f5037f59efab50a0897e0da57e9c9247b8bed03f80` |
| `.ai-pipeline/reports/PR95_DASHBOARD_REMEDIATION.md` | SUPPORTING | `04230b1e94e699dae93cb125c01279a1a9de85ac501a832cd26a56a4f2c40c63` |
| `apps/backend/app/domain/case_management.py` | INTENDED | `ab2ef38e60c30e45f0f425c3e20c02510ed7b30fa0c7f47a70c3e6c84e73cd70` |
| `apps/backend/app/domain/dashboard.py` | INTENDED | `f63a1fab027bd2efc2f8fc0281d44ad99c04f7eb1149dbffd44faab97ffdcb2a` |
| `apps/backend/app/main.py` | INTENDED | `66d1690d2c0b7cedae3fa0c588ed685fd84a8638038994913c2cc5e0b3af7101` |
| `apps/backend/app/persistence/mongo_case_store.py` | INTENDED | `2e3c226bff1dff0ba5ca2daddc6e64b46587c753ebe90881156d2e653faf7377` |
| `apps/backend/app/services/case_portfolio_repository.py` | INTENDED | `63975c7e8fb482fbebafb36dc1dc26aef3a79f25a94ecfdb10785db3014c9d07` |
| `apps/backend/app/services/case_query.py` | INTENDED | `f9859d74d3a150aad6b9d4fff2941c237ae49b5dc9482aaa74ac3dc7054f7657` |
| `apps/backend/app/services/dashboard.py` | INTENDED | `4d3020e848c742daa95dcf7b54c43589508bf4a5f4cceafd29c92cede28eba5f` |
| `apps/backend/tests/s1_date_filter_fixtures.py` | SUPPORTING | `601eed0557b79fc1eb946ae5d6c366d484d867162fd405cff1d25e9040b8add4` |
| `apps/backend/tests/test_attention_queue_backend.py` | SUPPORTING | `5f22f226fde72b3edd55d5387176cb4221ede034e28948cb39b2df034ea70ecb` |
| `apps/backend/tests/test_phase13_dashboard.py` | SUPPORTING | `02cc2fe4619d9d5b55162d13cf5c42e59170a3bdc4de770ff490cf1ee4b98861` |
| `apps/backend/tests/test_phase13_real_mongo.py` | SUPPORTING | `7183b1314b758ce23bc6a63b87024b1276bcd1338d02060e4d800a48af00d2e7` |
| `apps/backend/tests/test_phase17_case_activity.py` | SUPPORTING | `b05fd3538da703105173d62f67e236d4678a71ef881cb5d92c60a4f11942680c` |
| `apps/backend/tests/test_phase18_case_portfolio.py` | SUPPORTING | `4e49a65b11249df1c84afa72ee4a8d9ed17d85fac656fe60010c0650d0ed4ca4` |
| `apps/backend/tests/test_pr95_dashboard_compatibility.py` | SUPPORTING | `ca658c796ee21012880f7e082a624f158dd95bcfbad4ff17d548418c045b6bfe` |
| `apps/frontend/e2e/pr95-dashboard.e2e.ts` | SUPPORTING | `1952926800fa993d8c9c832cc40d02ac7207de0ad6a615a75151296c4904032e` |
| `apps/frontend/src/App.test.tsx` | SUPPORTING | `99e49be81eab702f5278437dc036dbbcd23c03ec2bc9f4f427eee895d5d557a2` |
| `apps/frontend/src/App.tsx` | INTENDED | `f0b7cc0687fa592a9c4dd0ec684ced2296bca4c5d415458ae4b6cadbb3f7e922` |
| `apps/frontend/src/Dashboard.test.tsx` | SUPPORTING | `319cb6e1d3b0c3e9521e6e0802a32a21ec5200d5dced153e2acddc6f1b4b5396` |
| `apps/frontend/src/Phase14CaseManagementPerformance.test.tsx` | SUPPORTING | `1c803b6a1e3e782f52e83d7de3f4a5bf9ab7913167951407053796cc1e8cbfe8` |
| `apps/frontend/src/Pr95DashboardCache.test.ts` | SUPPORTING | `61285b344624e17c324e19f8edfdbbf495392371c22e4f6a2dba58f38ddc2c7e` |
| `apps/frontend/src/api.ts` | INTENDED | `11ab366786ea50336d496d35635b92e3eb5f8f37ad3ff9ba56f4fa2f195fa346` |
| `apps/frontend/src/caseQueries.ts` | INTENDED | `ae6f64366ef4ce93842f17d590c2367bfe4e39348039594289d5b5493e5c4053` |
| `apps/frontend/src/design-system.css` | INTENDED | `f39dfc84c32c1196bf96d95e7f7c0d3cd85ca53ffff225523a0ddcafc8306160` |
| `apps/frontend/src/pages/Dashboard.tsx` | INTENDED | `305b0f203d35c42ad4010d67c02a429d0f060ebd83e2ffee103908aaf0bf05a7` |
| `apps/frontend/src/pages/DirectorTeamFilter.tsx` | INTENDED | `2cc06b184bfe1c7ef5efc03d7a8aaf0c4d1608e3da81d4dbc29c8e97c4eba60c` |
| `apps/frontend/src/styles.css` | INTENDED | `fbc8f6e0c1e14f84196b126f4fb6744de14541210f1765e6010be13c2ddd596a` |
| `apps/frontend/src/types.ts` | INTENDED | `2ee881bbc1f3d4d36bcb8a496969ab2bc7f528967852551c084e0445a8bcfa3c` |
| `docs/ARCHITECTURE.md` | SUPPORTING | `6ca01c696fe2b92d07bcfcc1448f3e5eabdd3cb36245a600a233cce287493708` |
| `docs/PROJECT_STATE.md` | SUPPORTING | `19727f85d8245cc01838351dcdb89263e089d4623731a8a10afd066ab4048b1c` |
| `docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md` | SUPPORTING | `9534c1a003ca8f9e0a9f2d9796fb4e371b1657c13af24730fa7a8855eba4d3ef` |
| `docs/contracts/CASE_TIMING_PROFILE.md` | SUPPORTING | `e7fba60fa127924ee5982094e2942e16a4d8eb5d28973243ba7439b798ddb623` |
| `tests/test_run_e2e.py` | SUPPORTING | `8da5fc7ce5dc7715f90f4ee1af7728178402113849fda523383c95071c2016dc` |
