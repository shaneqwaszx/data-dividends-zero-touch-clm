# Search / Registry disclosure independent Quality Gate — final corrective checkpoint

## Final executive result

**FAIL. DO NOT PUBLISH.** The two initial scoped findings are independently corrected. Mandatory complete canonical browser verification remains failed and incomplete because case-summary GETs returned HTTP500 in two subsequent journeys (SR-QG-03). The causal boundary remains unresolved. No successful complete shard2 exists on this corrected candidate. Focused successes do not supply its missing suite-pass receipt.

Independent reviewer: `/root/search_registry_quality_gate`, 15 October 2026, with no implementation/remediation involvement. The one post-gate corrective cycle is **1/1 consumed**. No further code cycle, full-suite retries, commit, push, PR, merge or next phase is authorized by this gate. Original deadline remains 16 October 2026 at 00:45:52 SGT. This is the final uncommitted checkpoint, not publication readiness.

The original initial FAIL is preserved **verbatim** below, including its original frozen 16 identities, findings and execution results. Its SHA256 remains `27573b0a7f43d14468c867a9aa12779005974eb199b3ac40891010e555e45e04` in `tmp/am-search-registry-disclosure/initial-quality-gate.md`.

## Corrected reviewed identity and scope

Worktree: `C:/Users/shane/.codex-clean2/worktrees/am-search-registry-20261015-1645/data-dividends-zero-touch-clm`.
Branch: `feat/am-search-registry-disclosure-20261015-1645`.
BASE_SHA / HEAD / merge base / final inspected origin/main: `66cd66fbc7be0b0425202cf5b4625b3120aa7308`; base/HEAD tree `01d422fe95fdf2a8e00dfc396bc286af797461fd`.
Latest-main fetch is coordinator-attributed; reviewer final readback confirmed HEAD/origin/main unchanged and no staged paths.

The current tested/reviewed source is HEAD plus all 17 frozen source/test/document paths, aggregate **`c1c025aa7642588e70a20ea3a654a9474b7630b4557eb84a65d5f3ce73f66722`**, from `tmp/am-search-registry-disclosure/frozen-candidate.json`. Algorithm and raw/LF/native binding are as specified in the initial gate. This report is excluded and separately hashed. Every17 field and the exact changed/new path set, excluding only this assigned report, was independently recomputed before and after execution. Native identities are Git-filtered working-content identities; no staged candidate/store tree is claimed.

Thirteen initial paths are byte-unchanged. The corrective delta is only CaseDetail's named Search wrapper, added actual fallback assertions within the existing responsive selector, the separately authorized UX helper/two assertion blocks, and the one integration document. UX has exactly three diff hunks; all other native content, titles, fixtures, guards, focus/endpoint/body/mobile/ownership/target assertions remain. The newly added assertion iteration that incorrectly expected Save enabled with incomplete required fields remains FAILED in `corrective-focused-browser.log`; final assertions retain the existing disabled Save guard and visible editable UEN. No production guard was weakened. `tests/test_run_e2e.py` remains exact native filtered-main raw bytes after only the three authorized numeric substitutions. Independent scope receipt: `reviewer-r1-static.json`.

## Complete corrected content binding

| Path | Raw SHA256 | LF SHA256 | Native Git blob |
|---|---|---|---|
| `apps/frontend/e2e/am-wave1.e2e.ts` | `1e1e5bd152c8cc085f201e285f8bad116e78388f9a44b5ba1335f64cc26231e9` | `1e1e5bd152c8cc085f201e285f8bad116e78388f9a44b5ba1335f64cc26231e9` | `704958e8dbb1a50aac5be00be266b3ebc20d23bd` |
| `apps/frontend/e2e/authenticated-zero-touch.e2e.ts` | `a58856c3285bba44f6e75bcb1bac8357be81484167925191a635d1529af9a9a4` | `3b32f45736c501aae9163146ac1871355ec6e7ca2161d2db90a074fc6a78a8c9` | `82905a88cb55fb40f1cb50f21b818ed4ebf2308d` |
| `apps/frontend/e2e/onboarding-recovery.e2e.ts` | `3f7ec4a8592d0350f643debb708630bba8969a82c1a960ef0e3ed63c2e30d560` | `3f7ec4a8592d0350f643debb708630bba8969a82c1a960ef0e3ed63c2e30d560` | `628ee044a66425a506089f63a815097f1ad87f2d` |
| `apps/frontend/e2e/registry-binding-timestamps.ts` | `e39b1e388cba26821e2d107e492235c7050ab960d92b0fd183d072471f3f1d1b` | `e39b1e388cba26821e2d107e492235c7050ab960d92b0fd183d072471f3f1d1b` | `884f7e60b48f8fc1230da313c6bb89ce87ef4532` |
| `apps/frontend/e2e/responsive-layout.e2e.ts` | `98a25f47e94957a093e8021f1b5b7f77c9c537e3b40533a26402879ccbf6c039` | `94cfaba051d24b9a0b22484bb122b79dfdebdede3096f352e00ffecce15038cc` | `b6fe632f1896d599d3654ca708dab7129529fcc8` |
| `apps/frontend/e2e/slice-b-registry-demo.e2e.ts` | `8e93e19636e481a219e29bb28240602132f4cd48103f3d8b7c31c89ad8b4ea68` | `8e93e19636e481a219e29bb28240602132f4cd48103f3d8b7c31c89ad8b4ea68` | `8c7c06d742dd3a88269fc9db6e03fed87ccdcbc7` |
| `apps/frontend/e2e/stage-disclosures.ts` | `630c357f84c055dbd7b3481b5759929bc82951e5f836a7b130e95e901211bf6a` | `630c357f84c055dbd7b3481b5759929bc82951e5f836a7b130e95e901211bf6a` | `fda78c4c80cd004cb7cad38219de5cd7f5d9b71b` |
| `apps/frontend/e2e/ux-refinement.e2e.ts` | `05b189a013a0908100ff5d021423f4fcb381b504685315971158be044ba58740` | `05b189a013a0908100ff5d021423f4fcb381b504685315971158be044ba58740` | `26d0bb94d2d01fa7d03207d0feeb727a4cad20e5` |
| `apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx` | `5affb15094eccb2295e6fbf3fe71385c3cff8de415170f0fa6af788124ceb989` | `5affb15094eccb2295e6fbf3fe71385c3cff8de415170f0fa6af788124ceb989` | `fb006fd87fd99110863aadd1d3fe9b729bf154c4` |
| `apps/frontend/src/pages/AM03SearchStage.test.tsx` | `e86ccfe27ac248fbf0e1b14d44b09d15e7525ab79873dab693ff278062292adc` | `e86ccfe27ac248fbf0e1b14d44b09d15e7525ab79873dab693ff278062292adc` | `fba1675191830e6b79978e95d00f3064a93eba7e` |
| `apps/frontend/src/pages/CaseDetail.tsx` | `0cb9c41ec69a7c980dc9a3a5383eff52db2912d2d694ff8af5526a39bab25bc6` | `0cb9c41ec69a7c980dc9a3a5383eff52db2912d2d694ff8af5526a39bab25bc6` | `1a7e7f004054e620e32bcbe29217b696dc45340e` |
| `apps/frontend/src/pages/CaseStatePanels.test.tsx` | `c2c4fed56e60e5abd4add845531274a27cc5649e0840bcff4dc9fc4d75d399dd` | `c2c4fed56e60e5abd4add845531274a27cc5649e0840bcff4dc9fc4d75d399dd` | `331166d2aa433b4bdaadbc10b4e202afaca01cf1` |
| `apps/frontend/src/pages/CaseStatePanels.tsx` | `ee2873dbcb0081a805665648ffc9b2b06217b199c769ea3d14702587689dfcbd` | `ee2873dbcb0081a805665648ffc9b2b06217b199c769ea3d14702587689dfcbd` | `43040fbb9d1c75fac65fb082ff9831d4acc56564` |
| `apps/frontend/src/pages/RegistryProvenancePanel.test.tsx` | `a4762311de4ec29a1c61ff87ccd9ffd2178d22837eede2e76dc29df5a048dc7b` | `c4ed71650bb26dd229dd967ba4485020285b41f0e0771de44fdd9ec90ceba72a` | `bd160d65869ec32d7153a588fa7d3f31845a3de3` |
| `apps/frontend/src/pages/RegistryProvenancePanel.tsx` | `765e844b700d1fa66d427ff1852687192d539ca3050ff978ecd126656c2622fd` | `ef551b6f33e775defc829b3d356a7639bd95a4295c9e8e0f5e31dde044ec0765` | `7381a33277a0467a60907185cf79bd1b42ca8893` |
| `docs/integration/AM_SEARCH_REGISTRY_DISCLOSURE.md` | `755bf6f38d900fce4f066138fe8d94b4abd9e1e73b8f46c47e29ff1b915ee157` | `06cb74bccaceef9f7e40d2243dc911d4c0c8980a1e720f6894503631094116a5` | `d8890ecd14addaff691217e51778b15fbdc824ff` |
| `tests/test_run_e2e.py` | `688bae0ff7476d7f1175c5da06c8bb18bb3f8cd2952f902e3df5944479d5d1e1` | `142340c8ce6c95b9cef38731f13cdb6f44ac88720ccfe58960bc41385c730404` | `8faf12df85262d422a3741a2860c037fdd818568` |

## Finding dispositions and current blocker

| Finding | Final disposition |
|---|---|
| SR-QG-01, obsolete UX whole-stage assumptions | **RESOLVED on frozen 17.** Local helper retains strict legacy collapse; persistent collapse closes only More/Technical and proves Main visible. Two obsolete Registry expanded-state checks now prove visible Main, editable UEN and visible guarded Save after exact corrective focus. Independent actual UX browser records pass, including both projection-only variants and mixed identity correction with existing endpoint/body/no-write/target assertions. |
| SR-QG-02, nameless actual Search fallback | **RESOLVED on frozen 17.** The stable outer anchor now has `role="group"` and `aria-label="Existing-customer search"`, preserving the one inner labelled Search region. The original independent probe is unchanged and now passes actual native keyboard navigation, focused anchor, computed name, closed support and zero mutations. Durable coverage was added within the existing responsive selector; inventory stays 107. |
| SR-QG-03, mandatory complete canonical evidence | **OPEN — P1 verification blocker.** Corrected shard2 and the fresh observed shard2 fail on summary GET HTTP500 in different journeys. Root cause is **UNRESOLVED**; undispatched tails remain **NOT_EXECUTED**. This is not accepted technical debt and cannot be waived by unit/focused success. |

### SR-QG-03 evidence and causal limits

1. `canonical-corrected-shard2.log`: selector 50/53, `e2e/sponsor-demo-journeys.e2e.ts:324`, multilevel sponsor journey. The first summary showed `PENDING_INPUTS / DOCUMENT`; a later summary GET returned500 in `create()` polling at line 74, before line 75 Open full case and before CaseDetail entry. Forty-nine selectors/54 records passed; one selected lifecycle failed; three selectors were undispatched. The same journey passed in an earlier frozen attempt. This identifies an observed boundary, not a cause.
2. Targeted instrumented multilevel diagnosis passed native 0 in 28.1 s. No matched backend500/type/frame was captured. This result does not exonerate the prior failure or replace complete canonical coverage.
3. `canonical-observed-shard2.log`: selector 1/53, `e2e/am-wave1.e2e.ts:124`, existing-customer reuse balanced-correction journey. Target confirmation returned200 at line 70; summary GET polling for COMPLETED at line 71 returned500. The selected lifecycle failed; zero records passed and 52 selectors were undispatched. This separate observation does **not** establish reproduction or closure of the original AM18 incident. Original attribution remains **NOT_REPRODUCED / OPEN**.

The observed run addressed an evidence-capture gap: the canonical runner normally omits backend capture on a Playwright assertion failure. An ignored observer calls the original process cleanup first, then retains only bounded source-frame locations, matched exception-type identifiers and backend HTTP500 counts. Reviewer source audit confirms unchanged canonical dispatch, fixture selection, assertions and 60-second lifecycle limit; no runner/backend/fixture edit or synthetic success was introduced. Observer SHA256 `6d7932fc43325934ba4c7fa1fe086060cedaf7908dd81e79e7c68e0f01a94084` remained exact.

Its55 backend observations contain zero matched classes/frames/backend500 lines. This is supplemental bounded capture: the regex covers Error/Exception suffixes, not every exception class, and backend status-line matching does not cover every proxy-generated500. Empty capture is not proof of absence or a cause determination. The failing canonical response/status assertions remain primary. No second corrective code cycle or further full-suite retry occurred after this result.

## Current A–V assessment

“Supported” below means direct focused/source evidence; complete release acceptance is withheld by SR-QG-03.

| Criterion | Current evidence/disposition |
|---|---|
| A Search Main / closed support | Supported by independent current owner tests and actual four-width browser. |
| B Registry Main / closed support | Supported by the same actual visibility and compact absence/source tests. |
| C Independent optional controls | Supported: actual Enter/Space/Tab and sibling visibility remain correct. |
| D Necessary correction/candidate controls | Supported by current Main composition and candidate/rationale/editor tests; no optional expansion is required. |
| E Correct intervention ownership | Supported by separate filters, coexistence tests and unchanged intervention owner. |
| F One editor / endpoint / expected bodies | Supported by exact AM03 requests and actual corrected UX request/focus/retention assertions. |
| G Failure is not customer absence | Supported by visible Main warning and failed-search tests. |
| H Empty retained checkpoint | Supported by truthful absence tests and independent no-action browser projection. |
| I Candidate/rationale/explicit confirmation | Supported by existing authority and current owner tests; no automatic confirmation added. |
| J Wrong UEN / document conflict | Supported by predicates/current owner tests and actual mixed-identity UX correction. |
| K Cache / seed / Mock / partial / unsupported | Supported by safe source partition, current provenance/state tests and executed canonical portions; no source/provider rule changes. |
| L Invalid/missing timestamps | Supported by unchanged shared validation/reuse owner and current warning/invalid-time tests. |
| M SGT and original UTC | Supported by current owner tests and preserved exact timestamp-source/consumer comparisons. |
| N Main blockers stay visible | Supported by actual persistent Main and current warnings/intervention/editor placement. |
| O Stable IDs / order / navigation | Initial defect resolved: independent actual fallback and strict UX correction/focus now pass; backend ordering unchanged. |
| P Scope / drafts / refresh / replacement | Supported by current scope keys, auth session remount owner and fresh isolation/full frontend tests. |
| Q Keyboard / names | Initial defect resolved: actual fallback computed name and native optional-summary controls pass. |
| R Four required widths | Supported at 1440/1280/900/360 in independent current canonical responsive selector. |
| S PR87 focus precedence | Supported by unchanged guarded owner, fresh frontend tests and completed current shard1's queued/nested keyboard/pointer/no-input records. |
| T Frozen / completed / denied / history | Supported by unchanged predicates/current tests and no-action denial probe; no new edit authority. |
| U No mutation/replay from inspection | Supported by both independent browser commands; zero inspection writes and existing guarded target assertions remain. |
| V No raw/private hidden DOM payload | Supported by explicit field projection, sentinel test, full diff/document/security review and current supported secret scan. |
| Required complete canonical pair | **FAIL / NOT VERIFIED.** No corrected53-selector shard2 suite PASS exists. Partial/focused executions do not complete the required pair. |

## Fresh independent corrected execution

All commands below exercise the frozen 17 aggregate above, with separate `reviewer-r1-*` evidence so the initial logs remain intact. Detailed command/cwd/exit/duration receipt: `reviewer-r1-command-receipt.json`.

| Independent lane | Result |
|---|---|
| Seven owning/navigation/disclosure/intervention Vitest files | **PASS**,180/180 tests,7 files. |
| Full frontend | **PASS**,729/729 tests,54 files; no skipped tests. |
| Frontend typecheck | **PASS**,exit0. |
| Production build to task-owned ignored output | **PASS**,exit0;140 modules;628.46kB JS. Existing >500kB advisory retained. |
| Complete `tests.test_run_e2e` unittest suite | **PASS**,48 tests. Its mocked negative-path suite-failed text remains expected test output. |
| Configured backend Ruff and affected tooling-owner Ruff | Both **PASS**,exit0. |
| project_state / architecture / tooling_config / policy_authority / external_provider_readiness / supported secrets | All six **PASS**,exit0. |
| Original independent no-action probe, unchanged | **PASS**,1 real Chromium record; keyboard reaches named actual group, optional support closed, zero unsafe-method requests. |
| Affected canonical UX/disclosure grep | **PASS**,6 real Chromium records, native exit 0; strict actual focus, UEN usability, required-field guard, endpoint/retention/mobile/no-write/target coverage retained. |
| All17 raw/LF/native identities / path inventory / exact three numeric raw substitutions | **PASS**,independent before/after checks. |
| Tracked diff and every task-owned new Markdown whitespace | **PASS**,explicit checks; no staged paths. |

Reviewer browser logs: `reviewer-r1-no-action.log` and `reviewer-r1-focused-browser.log`. Both use real local auth/HTTP with standard network/lifecycle guards and memory/offline fixtures;60-second guard, no retries, no own Mongo or external provider writes. The corrected coordinator focused6/units180/full729/type/build/tooling-governance122/Ruff/six checks were independently audited as attributed evidence in `corrective-command-receipt.json`. Existing React act warnings remain non-failing and unsuppressed. Earlier exploratory overbroad Ruff failures and runtime setup/Policy/OCR observations remain in the initial history.

## Complete current canonical execution audit

Independent discovery remains **107 unique selectors /136 listed records**, partitioned completely and disjointly 54/53 with unchanged fixture tags/routing. The current actual runs are independently reconciled against native receipts and full logs in `reviewer-r1-canonical-failure-audit.json`.

| Attempt | Passing selectors / actual records | Failure | Undispatched | Native result |
|---|---|---|---|---|
| corrected shard1 |54 /77|none|0|0 / PASS|
| corrected shard2 |49 /54|50/53 multilevel summary500|3|1 / FAIL|
| observed shard1 |54 /77|none|0|0 / PASS|
| observed shard2 |0 /0|1/53 reuse completion-poll summary500|52|1 / FAIL|

Log SHA256 respectively: `0bcf994553a0a1fb9a75bb8e8143f4be197238c399b73fe73d9c17d82c8d6849`, `3ddcbbf180dd07a1f04d16d58e5c28fc22c50ceecd6344979ab6a07c27e60890`, `20ad6cf9a51cc20288b1fd5e236af2945668874ffee6b4af73d21cefef114208`, `bea23e1420c7cc293ed7f72a903b3640d47f5f52a196f1f7e92ad1e4ce393277`. The corrected pair retains 7+6 disposable cleanup markers; observed shard1 retains 7. The failed observed first selector required no database fixture. Successful complete shard2 is still missing. No passing aggregate, covered-tail assumption, hidden skip, fixture alteration, timeout inflation or accepted exception is claimed.

## Architecture, contract, security and impact

No additional scoped code/architecture/security defect was found in the correction. One static named presentation group restores the existing focus target; existing focus algorithms, state ownership, scope keys and backend authority remain. Legacy browser compatibility is retained through the existing local helper while persistent Main remains visible. No framework, global focus owner or alternative state calculator was added.

Shared API/types, durable schema, connectors, runtime configuration/dependencies, business rules, mappings, auth/security semantics, architecture owners, provider classifications and backend behavior are unchanged by this slice. Local React presentation props, frontend rendering/disclosure scope/accessibility/focus and browser assertions changed; three revision-bound test numbers changed only as owner-authorized. StageDisclosure, HumanInterventionPanel, API/types/cache/auth, backend/provider files, CSS and snapshots remain protected/unchanged. Mock/Local/offline Sandbox evidence does not establish Live interoperability, sponsor policy, hierarchy, production compliance, Ready-for-Approval or final approval. Original AM18 remains NOT_REPRODUCED / OPEN.

The unresolved500 observations are current verification blockers with unknown cause, not a new inferred sponsor rule, a proven frontend cause, a proven backend/proxy cause, or accepted technical debt. No backend/runtime/fixture fix was attempted in this re-gate. No .env, protected database, raw provider/document body, credential material or private exception message was accessed or persisted by this reviewer. Supported secret and manual changed/new-content checks pass; no confidential artefact is introduced.

## Resource cleanup and final readiness

Coordinator receipt `final-resource-cleanup.json` (SHA256 `17569fe02b5476676c9474b796ddbc1dcf6158e437bb1a2d39a075232e69d30c`) records exact task container `7b48d2213fa15fbd419d8481eec25b95a3334a7df2b06a1b738e64cb0ff4e9a9`, name/label/loopback 27245 verification, remaining dedicated-server databases only admin/config/local, removal of that container and its two task-owned anonymous volumes, and preservation of other resources. These database/removal operations are coordinator-attributed; reviewer performed none.

Reviewer independently queried only the exact container ID and confirmed absence, then bound/closed all 128 canonical/reviewer browser ports and Mongo 27245 after independent runs: all 129 bind-free, including all 20 reserved reviewer ports. Detailed receipt: `reviewer-r1-cleanup-audit.json`. No service/container is left for this reviewer and no own Mongo access occurred. Cleanup success does not change failed behavioral evidence.

**Final readiness: checkpoint only; DO NOT PUBLISH.** SR-QG-01 and02 are closed on the corrected bytes; SR-QG-03 blocks exact PASS. Preserve this worktree, frozen manifests, source candidate, report and failure evidence. The one corrective cycle is exhausted; no further implementation or full-suite retry is authorized here. Any further causal investigation, remediation or missing canonical-evidence recovery needs a separate owner-scoped instruction. Do not start document disclosure or another phase. Full backend/physical-persistence suites are NOT_EXECUTED and not required solely for this presentation delta. Commit/clean committed pre-PR/push/PR/current-head review and hosted CI are NOT_EXECUTED for this failing candidate. Hosted billing refusal is not passing CI.

## Final Git and write boundary

Final source/HEAD/origin/main remain the recorded baseline plus unchanged frozen 17 delta. Sixteen tracked modified paths plus the untracked integration document and this assigned report; no staged content. Only the assigned report and task-owned ignored evidence/build outputs were written by the independent reviewer. No implementation/canonical-test/documentation/configuration fix, commit, push, PR, merge, branch switch, other-worktree mutation or next phase occurred during re-review. The report's current identity is separately returned to the coordinator; the original initial report bytes remain the verbatim suffix below.

---

# Preserved initial FAIL history — verbatim original content

# Search / Registry disclosure independent Quality Gate — initial frozen candidate

## Executive result

**FAIL.** Required canonical browser compatibility is incomplete (SR-QG-01), and the stable no-action Search focus destination has lost its accessible name (SR-QG-02). No publication, commit, push, PR or merge is accepted by this verdict. The implementation is substantially present, but required failing/unexecuted evidence cannot be called PASS.

Independent reviewer: `/root/search_registry_quality_gate`, 15 October 2026. This reviewer did not implement or remediate this candidate. This is the initial gate, before the coordinator's single authorized post-gate corrective cycle. Preserve this initial result when recording a later re-gate.

## Reviewed identity and authority

Worktree: `C:/Users/shane/.codex-clean2/worktrees/am-search-registry-20261015-1645/data-dividends-zero-touch-clm`.
Branch: `feat/am-search-registry-disclosure-20261015-1645`.
BASE_SHA, HEAD, merge base and inspected local origin/main: `66cd66fbc7be0b0425202cf5b4625b3120aa7308`.
HEAD/base tree: `01d422fe95fdf2a8e00dfc396bc286af797461fd`.
Coordinator reports a fresh latest-main fetch with the same SHA and no drift; the reviewer performed no Git mutation or fetch.

Reviewed content is the complete uncommitted 16-path source/test/document candidate, not HEAD alone. Frozen manifest: `tmp/am-search-registry-disclosure/frozen-candidate.json`; initial aggregate `8b7f7ed9c1f905c5d7ca2d979e20fa7474705e7086213c6768f797793c80fb46`. The SHA256 algorithm is compact sorted-key Python JSON over the path-sorted records array, including each path/raw SHA256/LF SHA256/native Git blob identity. The reviewer independently recomputed every field before and after execution, checked the exact 15 modified plus one untracked path inventory, and explicitly read the new integration document. The table below binds both raw working files and Git's filtered native content. No candidate is staged; actual index/store identity remains a later publication check.

Authority read: complete original owner attachment `08cc33a7-6988-480c-bce9-a72297785e58/Pasted text.txt`; current design handoff; root/frontend AGENTS; repository skill routing; FRONTEND_UI + CI_TOOLING dev-context selections, workflow/branch protocol, selected architecture/state sections; fyp-quality-gate/report template and POC regression catalogue; current source/tests and accepted PR85/86/87/88 integration/gate boundaries. The three added browser consumers were separately owner-authorized. The reviewer independently proved `tests/test_run_e2e.py` equals Git's native filtered main bytes after only 104→107, 9420→9780, and 52→54 substitutions; all 972 CRLF line endings are retained. The later UX helper/two-assertion authority applies to remediation, not to changed content in this initial gate. No acceptance criterion was relaxed.

## Complete frozen content binding

| Path | Raw SHA256 | LF SHA256 | Native Git blob |
|---|---|---|---|
| `apps/frontend/e2e/am-wave1.e2e.ts` | `1e1e5bd152c8cc085f201e285f8bad116e78388f9a44b5ba1335f64cc26231e9` | `1e1e5bd152c8cc085f201e285f8bad116e78388f9a44b5ba1335f64cc26231e9` | `704958e8dbb1a50aac5be00be266b3ebc20d23bd` |
| `apps/frontend/e2e/authenticated-zero-touch.e2e.ts` | `a58856c3285bba44f6e75bcb1bac8357be81484167925191a635d1529af9a9a4` | `3b32f45736c501aae9163146ac1871355ec6e7ca2161d2db90a074fc6a78a8c9` | `82905a88cb55fb40f1cb50f21b818ed4ebf2308d` |
| `apps/frontend/e2e/onboarding-recovery.e2e.ts` | `3f7ec4a8592d0350f643debb708630bba8969a82c1a960ef0e3ed63c2e30d560` | `3f7ec4a8592d0350f643debb708630bba8969a82c1a960ef0e3ed63c2e30d560` | `628ee044a66425a506089f63a815097f1ad87f2d` |
| `apps/frontend/e2e/registry-binding-timestamps.ts` | `e39b1e388cba26821e2d107e492235c7050ab960d92b0fd183d072471f3f1d1b` | `e39b1e388cba26821e2d107e492235c7050ab960d92b0fd183d072471f3f1d1b` | `884f7e60b48f8fc1230da313c6bb89ce87ef4532` |
| `apps/frontend/e2e/responsive-layout.e2e.ts` | `21faca2eb8073cebf6f633eeb4d8a5a5d16adca10f29907deb804d709b41912e` | `80a22c137d8b2db32e71e1411858530b9bc6d8d4a8ac26b4bf80932c836c5524` | `b63c7acd4084a061c32f7c72925c0994e6fde3f6` |
| `apps/frontend/e2e/slice-b-registry-demo.e2e.ts` | `8e93e19636e481a219e29bb28240602132f4cd48103f3d8b7c31c89ad8b4ea68` | `8e93e19636e481a219e29bb28240602132f4cd48103f3d8b7c31c89ad8b4ea68` | `8c7c06d742dd3a88269fc9db6e03fed87ccdcbc7` |
| `apps/frontend/e2e/stage-disclosures.ts` | `630c357f84c055dbd7b3481b5759929bc82951e5f836a7b130e95e901211bf6a` | `630c357f84c055dbd7b3481b5759929bc82951e5f836a7b130e95e901211bf6a` | `fda78c4c80cd004cb7cad38219de5cd7f5d9b71b` |
| `apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx` | `5affb15094eccb2295e6fbf3fe71385c3cff8de415170f0fa6af788124ceb989` | `5affb15094eccb2295e6fbf3fe71385c3cff8de415170f0fa6af788124ceb989` | `fb006fd87fd99110863aadd1d3fe9b729bf154c4` |
| `apps/frontend/src/pages/AM03SearchStage.test.tsx` | `e86ccfe27ac248fbf0e1b14d44b09d15e7525ab79873dab693ff278062292adc` | `e86ccfe27ac248fbf0e1b14d44b09d15e7525ab79873dab693ff278062292adc` | `fba1675191830e6b79978e95d00f3064a93eba7e` |
| `apps/frontend/src/pages/CaseDetail.tsx` | `35e9a75cb3bc6330debefc04607065d31790876a20c981b4d0f5e62c73dc4ab4` | `35e9a75cb3bc6330debefc04607065d31790876a20c981b4d0f5e62c73dc4ab4` | `48bbe9e1823262334d2f4f47e186bd006e425fa3` |
| `apps/frontend/src/pages/CaseStatePanels.test.tsx` | `c2c4fed56e60e5abd4add845531274a27cc5649e0840bcff4dc9fc4d75d399dd` | `c2c4fed56e60e5abd4add845531274a27cc5649e0840bcff4dc9fc4d75d399dd` | `331166d2aa433b4bdaadbc10b4e202afaca01cf1` |
| `apps/frontend/src/pages/CaseStatePanels.tsx` | `ee2873dbcb0081a805665648ffc9b2b06217b199c769ea3d14702587689dfcbd` | `ee2873dbcb0081a805665648ffc9b2b06217b199c769ea3d14702587689dfcbd` | `43040fbb9d1c75fac65fb082ff9831d4acc56564` |
| `apps/frontend/src/pages/RegistryProvenancePanel.test.tsx` | `a4762311de4ec29a1c61ff87ccd9ffd2178d22837eede2e76dc29df5a048dc7b` | `c4ed71650bb26dd229dd967ba4485020285b41f0e0771de44fdd9ec90ceba72a` | `bd160d65869ec32d7153a588fa7d3f31845a3de3` |
| `apps/frontend/src/pages/RegistryProvenancePanel.tsx` | `765e844b700d1fa66d427ff1852687192d539ca3050ff978ecd126656c2622fd` | `ef551b6f33e775defc829b3d356a7639bd95a4295c9e8e0f5e31dde044ec0765` | `7381a33277a0467a60907185cf79bd1b42ca8893` |
| `docs/integration/AM_SEARCH_REGISTRY_DISCLOSURE.md` | `2c5722ccc8a81509f54b4e47a82ec04d2b4811a9c5b8f8c9385796f398ec7d71` | `3d6072ddddc1e83d3354ccc62273aee174d5c2c73fa82f5bcd8e0b3448150045` | `178a0e38b7177c49b3cda84e6e97d3cbe03b0362` |
| `tests/test_run_e2e.py` | `688bae0ff7476d7f1175c5da06c8bb18bb3f8cd2952f902e3df5944479d5d1e1` | `142340c8ce6c95b9cef38731f13cdb6f44ac88720ccfe58960bc41385c730404` | `8faf12df85262d422a3741a2860c037fdd818568` |

## Owner A–V acceptance checklist

These focused results identify direct support; they do not replace the failed mandatory complete browser pair. Failing and undispatched canonical journeys remain unaccepted.

| Criterion | Initial finding and direct evidence |
|---|---|
| A Search Main / closed support | Supported: independent owner tests and actual new Chromium case; Main visible, both optional sections closed. |
| B Registry Main / closed support | Supported by the same independent executions and compact absence/source tests. |
| C Independent open/close | Supported: native Enter/Space/Tab and independent sibling visibility in Chromium. |
| D Visible correction/candidate controls | Supported: one Main identity renderer, candidate/rationale tests, executed canonical S1 and existing-customer journeys. |
| E Correct intervention ownership | Supported: separate REGISTRY/GOLDTIER_SEARCH filters and coexistence tests; shared intervention owner unchanged. |
| F One editor / endpoint / expected versions | Supported: independent AM03 exact Search-versus-Registry endpoint and version-body assertions; document/source-choice request owner unchanged. |
| G Failure is not absence | Supported: failed-search Main warning and no NO_MATCH assertion; executed failure/recovery browser coverage. |
| H Empty checkpoint | Supported: explicit no-retained-result wording, no invented result/confirmation in Main or support. |
| I Candidate identity/rationale/explicit confirm | Supported: unchanged HumanIntervention authority and current AM03 plus canonical existing-customer confirmation/count coverage. |
| J Wrong UEN / document conflict | Supported focused predicates and executed S1; full PR84 browser acceptance is blocked by SR-QG-01. |
| K Cache / seed / Mock / partial / unsupported | Supported source partition, current provenance/state tests and completed canonical cache, seed and partial-source journeys; no new provider call is inferred. |
| L Invalid/missing timestamps | Supported: shared timestamp validation/reuse helpers unchanged; current tests and visible invalid-time Main warning. |
| M SGT and original UTC | Supported: shared formatter and exact original source strings retained; revised browser consumers keep exact UTC comparisons. |
| N Current blockers visible | Supported: required Search warning, Registry limits/interventions/editor stay Main with optional content closed. |
| O IDs / processing order / focus navigation | **FAIL**: stable Search ID remains but its actual fallback focus container is nameless (SR-QG-02); obsolete canonical navigation consumers also fail (SR-QG-01). Backend ordering is unchanged. |
| P Scope/drafts/refresh/replacement | Supported: caller keys use actor/case/role/team and retained request or acquisition/binding identities; same-scope refresh/toggle and replacement tests pass; auth session-generation remount owner unchanged. |
| Q Keyboard/accessibility | **PARTIAL / FAIL**: native optional controls pass; keyboard no-action fallback reaches an empty-name container (SR-QG-02). |
| R 1440/1280/900/360 layout | Supported by independent canonical new browser case, actual visibility and document containment checks at all four widths. |
| S PR87 focus precedence | Supported: unchanged guarded focus owner and independent full frontend; six current queued/nested keyboard/pointer/no-input canonical records completed before the later UX failures. |
| T Frozen/completed/denied/history | Supported focused/full frontend and completed canonical frozen/read-only scenarios; no edit/confirmation predicate broadened. |
| U No mutation/replay from inspection | Supported: independent normal disclosure browser and no-action probe both observe zero unsafe-method requests; target ledger/API/cache owners unchanged. |
| V Browser privacy | Supported: explicit safe field projection, forbidden-property sentinel test and manual complete diff/document review; no raw provider/document body introduced. |
| Mandatory complete canonical pair | **FAIL**: final pair has 102 passing selectors / 129 passing records, two failed selected lifecycles, three undispatched selectors. Neither shard supplies a suite PASS. |

## Required findings

### SR-QG-01 — P1 required canonical compatibility / verification blocker

`apps/frontend/e2e/ux-refinement.e2e.ts:27` unconditionally queries a whole-stage button in local `collapse()`. Registry is now intentionally persistent and has no such button. Calls at lines47,145,185 wait for an impossible control; lines50 and148 also retain obsolete Registry `aria-expanded` expectations. Final shard1 times out at selector53/54, `ux-refinement.e2e.ts:166` (PR84 mixed identity blockers); final shard2 times out at selector51/53, `ux-refinement.e2e.ts:32` (attention/sticky/mobile routing). This causal mismatch is directly visible in current source, and both failures are reproduced by the fresh guarded canonical run. It is separate from the earlier OCR/Policy observations.

Required correction: narrowly adapt the local helper and its two obsolete Registry assertions under the owner's explicit amendment. Preserve legacy toggling and strict actual UEN focus/visibility, one editor, endpoint/version bodies, retained evidence, desktop/mobile, mutation/network and target boundaries. Preserve titles, fixtures, selector inventory, guards and timeouts. Rerun affected UX journeys and the complete current pair; undispatched tails cannot be waived.

### SR-QG-02 — P2 accessible name lost on stable Search fallback target

`apps/frontend/src/pages/CaseDetail.tsx:1286` changes the original labelled Search section into a focusable outer `div` with no accessible name. The inner persistent section is labelled, but `focusSearch()` still passes the outer `SEARCH_TARGET_ID` to `focusActionControl()` when no diagnostic/action is present. Its no-control branch focuses that outer element, not the labelled inner stage.

Fresh independent Chromium falsification used real login/HTTP and a bounded legacy/empty GET projection with existing recognized Search exception/code, no retained checkpoint/pipeline/intervention and denied correction. Native keyboard activation of the actual attention button focused `#case-existing-customer-search`; both support sections stayed closed; unsafe request count and network violations were zero. `toHaveAccessibleName("Existing-customer search")` then failed with received `""`. The observed target was DIV, `aria-labelledby=null`, `aria-label=null`. Evidence: `tmp/am-search-registry-disclosure/reviewer-no-action.log`; reviewer-only probe is ignored and does not modify canonical source/tests.

Required correction: preserve a meaningful accessible name on the actual stable no-action focus destination, retain one labelled Search region, and add durable actual-fallback/name/zero-write coverage. A named wrapper group is a bounded option; no new disclosure framework or focus owner is needed. Do not substitute direct programmatic anchor focus for navigation in its regression test.

## Fresh independent execution

Commands/results bind the 16 frozen paths above. Full command/cwd/exit/duration receipts and complete logs are under `tmp/am-search-registry-disclosure/reviewer-command-receipt.json` and `reviewer-*.log`.

| Reviewer-executed lane | Actual result |
|---|---|
| Seven owner/navigation/disclosure/intervention Vitest files | **PASS**,180 tests /7 files. |
| Full frontend `npm test` | **PASS**,729 tests /54 files; no skipped tests. |
| Frontend typecheck | **PASS**,exit0. |
| Production build to task-owned ignored output | **PASS**,exit0;140 modules,628.41kB JS. Existing >500kB advisory remains; no threshold change. |
| Complete `python -B -m unittest tests.test_run_e2e` | **PASS**,48 tests. Its mocked negative-path suite-failed line is expected test output, not a real browser PASS. |
| Configured backend Ruff; narrow run_e2e/test_run_e2e Ruff | Both **PASS**,exit0. |
| project_state / architecture / tooling_config / policy_authority / external_provider_readiness / supported secrets | All six **PASS**,exit0. |
| Current four-width Search/Registry canonical browser selector | **PASS**,1 actual Chromium record,60-second lifecycle; native independent support/keyboard/visibility/zero writes. |
| Independent no-action fallback accessibility probe | **FAILED**,1 actual Chromium record, solely at missing computed accessible name after focus/closed support/no-write assertions passed (SR-QG-02). |
| Frozen raw/LF/native identities, exact numeric-only amendment, tracked/new whitespace | **PASS**,independently before and after execution. `git diff --check` also passed; untracked integration Markdown was explicitly checked. |

The independent validation wrapper initially stopped after a passing focused run because Windows cp1252 stdout could not print a checkmark. It was rerun with task-process UTF-8 stdout; no candidate bytes changed. Reviewer probe discovery initially lacked a local ESM marker; adding it only in the ignored reviewer fixture made discovery pass. Neither setup failure is implementation evidence or hidden.

## Complete canonical inventory and evidence audit

Independent configured discovery found107 unique selectors; exact54/53 partitions are disjoint and cover the entire inventory. The canonical runner, CI, fixtures, lifecycle timeouts and network policy are unchanged. Counts below are revision-specific actual executions, independently parsed from complete coordinator logs. Every undispatched selector is **NOT_EXECUTED** in that attempt.

| Coordinator log | Passing selectors / actual records | Failed selected lifecycle | Undispatched selectors | Result |
|---|---|---|---|---|
| canonical-shard1.log |37 /56|38/54, scanned Garden upload503|16|FAILED|
| canonical-shard2.log |45 /50|46/53, unchanged Policy heading wait|7|FAILED|
| canonical-final-shard1.log |52 /74|53/54, UX mixed identity legacy button|1|FAILED|
| canonical-final-shard2.log |50 /55|51/53, UX attention legacy button|2|FAILED|

Final shard log SHA256: `c326d6f28d6ec557cb05eed88322a5e3edffd73adb5ad4b50b67e7aeb13e8b24` and `18a631edde25c4a4672d9b01520d7c8911cfb6c4ac9f91b6e9eefebccaafcff3`. Initial log SHA256: `cf001265d1b9b9dc8b3158f3883851a16e5d277a7e0be40f193d16a4fec0bf8c` and `282a3ae94ce32a9d4e43af583452f00c31e6d1252a37970dada29a6685bebe24`. Detailed parsed receipt: `reviewer-browser-audit.json`.

Initial OCR503 was traced to installed Tesseract missing from inherited PATH. The existing executable passed actual synthetic OCR preflight and the unchanged focused scanned Garden journey after task-process PATH prefix; no machine/source/fixture change. Earlier PDF-body runtime deficiency was resolved using the task-local pinned venv, not a fixture/backend alteration. Initial Policy timeout remains intermittent with unresolved cause: controlled main-source and restored-candidate focused executions passed; no Policy patch/timeout/assertion change. Those initial attempts remain FAILED. Their resolved/falsified hypotheses do not excuse the later deterministic UX compatibility failures.

Coordinator current-tree full frontend729/54, typecheck/build and affected governance/tooling122/122 evidence was audited as attributed execution, not claimed as reviewer reruns. Its two exploratory overbroad root/scripts Ruff invocations remain FAILED with pre-existing archive/benchmark diagnostics (24 and15); no exclusion or unrelated fix was applied. Reviewer configured backend and affected tooling-owner Ruff independently passed. Original RED component/selector failures remain causal historical RED evidence; none supplies acceptance.

## Contract, architecture and security review

No additional contract/security finding. Reuse remains with CaseDetail composition, canonical registryPresentation, RegistryProvenancePanel retained evidence subsets, existing guarded focus and unchanged StageDisclosure/HumanInterventionPanel. Exactly one identity editor and unchanged Search/Registry endpoint/request selection remain. There is no second status resolver, ownership calculator, authorization/persistence owner, mapper, provider or framework. Legacy default presentation compatibility stays in existing owners; the missed UX browser consumer is SR-QG-01.

Shared API/types, durable schema, connectors, runtime configuration/dependencies, business rules, mappings, backend authorization/security semantics, architecture ownership, provider classifications and backend runtime are unchanged. Local React presentation props, frontend rendering/disclosure scope/accessibility/focus behavior and browser assertions change. The three test expectation numbers change only as authorized. Mock, Local seed and synthetic offline Sandbox remain distinct; no new Live, sponsor-policy, hierarchy, compliance, Ready-for-Approval or final-approval claim is made. Original AM18 attribution remains **NOT_REPRODUCED / OPEN**.

Only explicit minimized existing fields are rendered. The reviewer accessed no .env, credential material, raw provider/document body or protected database. Supported secret scan and manual changed/new-file review found no newly tracked confidential artefact. Collapse is not authorization. Browser fixtures used real local auth/HTTP with contained offline providers; no real external provider/target write occurred.

## Runtime, cleanup and readiness

The coordinator serialized complete canonical runs before releasing the runtime. Independent browser runs used owned9450/4650 and9451/4651 only, unchanged60-second lifecycle guard, configured Chromium/network policy, no retries or assertion weakening. Both completed owned-process cleanup; all20 reviewer candidate ports9450–9459/4650–4659 were independently bind-free afterwards. Reviewer used no Mongo. Existing coordinator Mongo27245 remains coordinator-owned for the separate corrective verification; its final canonical logs contain7+6 verified generated fixture database-cleanup markers. This is not certification of container removal or a full physical-persistence suite. Root remains sole resource-cleanup/Git coordinator.

**Not ready for publication.** Complete the owner's one bounded corrective cycle for SR-QG-01/SR-QG-02, freeze the changed complete candidate, rerun affected and mandatory complete evidence, and obtain a fresh independent exact PASS. Initial cycle use at this verdict is0/1; this report grants no additional budget. No next stage/phase starts. Live ACRA/GoldTier readiness and sponsor dependencies remain unchanged and unproved. Full backend/physical-persistence suites are NOT_EXECUTED and not required solely for this presentation/tooling delta. Pre-PR, commit/push/PR/current-head review and hosted CI are NOT_EXECUTED for this uncommitted failing candidate; billing-refused hosted runs are never passing evidence.

## Git and reviewer write boundary

HEAD/base/origin-main remained the recorded baseline. Initially15 modified tracked files plus one untracked integration document, no staged content. The only tracked-output addition by this reviewer is this assigned report; all other reviewer writes are task-owned ignored validation/build evidence. No implementation, canonical test, ordinary documentation or configuration fix occurred during review. No stage, commit, push, PR, merge, branch switch, other-worktree mutation or next phase occurred. The frozen16-path candidate excludes this report, whose identity is recorded separately by the coordinator. All16 raw/LF/native identities remained exact after execution.
