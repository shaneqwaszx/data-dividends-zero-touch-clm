# PR95-R5 independent full-PR adversarial re-review, Round 2

## Outcome and role boundary

**PASS / CLEAR FOR A NEW SEPARATE FINAL INDEPENDENT QUALITY GATE.** R5-QG-01 is
verified corrected. No further required implementation finding was established in this
comprehensive review of the entire accumulated PR95 candidate against current main.
All six R5 findings, both preserved R4 frontend corrections and earlier R2/R3 protections
remain accounted for below. This is a new exact-content adversarial assessment, not
final acceptance, a commit decision, pre-PR verification or publication authorization.

The earlier adversarial CLEAR missed an explicit mandatory preflight guarantee. The
separate final Quality Gate correctly returned FAIL for that gap. Both reports remain
immutable history; this review does not overwrite or retrospectively validate them.
The final-source complete ordinary backend run and a distinct fresh final Quality Gate
are still required. No final acceptance PASS or local implementation commit may derive
from this narrower prerequisite alone.

## Frozen identity and scope

- Branch: `codex/pr95-dashboard-remediation-20261018`.
- Worktree: `C:/Users/shane/.codex-clean2/worktrees/pr95-dashboard-remediation-20261018/data-dividends-zero-touch-clm`.
- Committed/published starting HEAD: `e970a0b31fe2cf2c1617dcc759c9d2131433ba68`.
- Committed starting tree: `8abb0de47de69a24f88550f3ddece82c03b7a626`.
  These identities exclude the intentionally uncommitted R4/R5 source and reports.
- Comparison base/local origin/main: `4a280da473dcdbeb345ffdfa79aaa4c001e75f62`.
- Complete frozen input: `.runtime/pr95-r5-scoped-frozen-r3.json`, all62 paths below.
- Compact sorted raw path/hash map SHA256:
  `8039146dbbe6c4ec5af79526a847fe49e907b503a17dfd7ede721c90a72a5972`.
- Exact default serialization `git diff --binary origin/main --`, independently reproduced:
  `35abe818e0b5a578b507b7fc112958eb4ade64c5c7e58a054d534a1e4e2cccac`.
- Explicit alternative `git -c core.autocrlf=false diff --binary origin/main`, also reproduced:
  `9a0045d592ad718426e3b29badf5e8982906d64eacebb509c5e1a90862b92972`.
  The initial apparent discrepancy is explained by these different serialization options,
  not source drift. Both reviewer and coordinator verified all62 identical actual raw
  hashes/base/HEAD; `.runtime/pr95-r5-scoped-r3-diff-reconciliation.json` records it.
  The complete raw map binds untracked inputs that Git diff alone omits.
- Since frozen V2, product changes only in MongoCaseStore's raw routing-key integrity
  check; its new eight regressions change the scoped-dashboard test file. Three new
  supporting reports preserve the earlier CLEAR, final-QG FAIL and remediation record.
  Every other source/test/contract/script/frontend byte remains the V2 reviewed byte.
- Index remains empty. Original teammate and main ancestry were verified in the preceding
  review and HEAD/base remain unchanged. Remote refresh and primary/worktree preservation
  are coordinator-owned observations; this reviewer made no fetch or Git mutation.
- Prior adversarial report remains SHA256
  `9cfd0aa2548593559722542bce5fd2a3895fa437d930fdf5125d229cfec72842`.
- Prior final-QG FAIL remains SHA256
  `0d8cd885f58056d893b147f7fc40a5534cd0a612accff7bb14f47b1803c26de2`.
- R4 FAIL remains SHA256
  `3334134fbeef63ae2a30fe934e1fee43e9168a1d17ab5e82979d786e1292d6ee`.
- Design preflight remains SHA256
  `443a25ec606b42195460d702b11c2299ac6a43c827b45869a7e9e01f4b28fa32`.

All62 raw hashes were checked at entry and after the full runtime run before writing
this report. The only reviewer tracked write is this newly assigned R2 report, whose
hash must be recorded separately rather than included in a self-referential manifest.
No reviewed source/test/configuration or previous report was changed by the reviewer.

Read-set and authority: the complete R5 owner assignment and approved interface plan;
root/backend/frontend AGENTS; canonical quality-gate, integration, persistence, architecture,
frontend cache and security procedures/checklist; current workflow/merge/coordination and
reviewer/security roles; current architecture/project-state/provider/sponsor limits; case
access/timing/activity/persistence contracts; all accumulated source/test/report categories
against main; immutable R4 assessment/handoff/design and R2/R3 gates; initial R5
preflight/implementation/adversarial report; new final-QG FAIL and conformance remediation.
Unchanged-source inspection from this auditor's preceding run is bound by identical
raw hashes and re-challenged against all criteria, not treated as a final acceptance waiver.

## R5-QG-01: corrected mandatory query-integrity guarantee

**VERIFIED FIXED.** CapturedCaseBatch now distinguishes original capture authority from
final cohort selection. It first constructs canonical string IDs from its captured
frozen UUID set. Every returned raw routing key must be a string belonging to that set;
otherwise the existing PersistenceDataInvalidError is raised. Only after that integrity
check can an authorized excluded-cohort key skip full decoding.

This rejects foreign, missing, null and integer keys even with an empty selected cohort.
It retains full decode/identity binding for selected valid keys and deliberately avoids
schema/nested validation of valid authorized excluded envelopes. It adds no new query,
clock, authorization owner, codec relaxation, fallback, schema/index or provider action.
Existing finally blocks clear raw/model/callback/authority references on failure, and
adapter/context cleanup prevents reuse or partial response publication.

The eight regression cases were observed failing first (8RED/19deselected). Current
independent focused execution passes all102 selected items, including those eight and
seven R3 fixture safeguards. Beyond those authored tests, this reviewer independently
executed eight actual authenticated HTTP probes using the real store/adapter/service/API
with a controlled impossible-result cursor: foreign/missing/null/integer key times empty
or nonempty date cohort. Each cursor receives only the authorized finite query, closes
once, and every response is exactly503/DASHBOARD_UNAVAILABLE with no underlying data.
A valid selected raw envelope precedes the unexpected row in these probes, so an error
cannot silently publish a partial successful dashboard.

These controlled cursors are explicit internal conformance probes, not evidence that
real Mongo can violate its finite `_id/$in` query. The fresh complete guarded Mongo run
separately proves real driver/server behavior and all retained persistence regressions.
The original finding was a mandatory interface-conformance gap, not an observed foreign
record leak; its correction does not invent a broader security or architecture claim.

## Every assigned finding and earlier protection

| Requirement | Independent disposition on frozen R3 input |
| --- | --- |
| P2-06 scoped automation read | VERIFIED FIXED, including R5-QG-01. Backend-authorized finite IDs precede one eagerly materialized raw capture. One final clock selects the unchanged Singapore cohort before strict selected-only decoding. Original captured authority and final selected subset are separately enforced. Excluded malformed nested/schema data does not decode; selected corruption fails safe. |
| R4-A1 negative retained stage samples | VERIFIED FIXED. Dashboard validates all selected samples before DTO construction, using canonical CaseTimingDataInvalidError and safe503. Negative relevant data is not clamped/discarded; zero/missing/exact integer values remain. Unit, HTTP and actual Mongo evidence distinguishes selected from excluded data, including a201-case adverse probe. No global validator or blanket Pydantic catch. |
| R4-A2 truthful200-case prefix | VERIFIED FIXED. All cases/Your cases/Blocked cases disclose loaded subset plus authoritative cohort count, local Person/status/age/progress and pager scope, and existing Cases navigation. Capped empty text speaks only about loaded rows; mine remains creator-only. API200cap and bounded browser requests remain. Component0/1/200/201/250 and actual205-case evidence applies to unchanged frontend bytes. |
| R4-V1 browser selector inventory | VERIFIED FIXED. Discovery110, complete disjoint shards55/55, unchanged9960-second launcher and234-minute CI outer budget. Exact supporting expectation reconciled; no safety deadline/workflow/test/skip reduction.244-test governance evidence passes; root is obtaining a final explicit-command rerun separately. |
| R4-M1 empty pager | VERIFIED FIXED. Empty local pagers say0of0, with Prev/Next disabled; nonempty ranges/page clamping retained. |
| R4-M2 date accessible name | VERIFIED FIXED. Native selector is explicitly named Dashboard date range; four labels/values,30d initial selection/query and callbacks remain. |
| R4 P2-07 server activity pagination | PRESERVED. One10-event server page, offset/has_more, Prev/refresh/retry, distinct loading/error/empty handling, live-boundary text and capped Audit navigation. No invented total or100-event client cutoff; actual browser traverses all fixture events beyond100. |
| R4 P2-08 keyboard stage disclosure | PRESERVED. Six native buttons have stable unique controls, labelled hidden regions and aria-expanded. Sorting/focus/repeated toggles and Tab/Shift+Tab/Enter/Space remain verified. |
| R2 P2-01 creator validation | PRESERVED. Authorized scope precedes projected validation; invalid authorized creator evidence cannot be hidden by created_by filtering. Schema9/10 grammar and legacy absent creator semantics remain; malformed other-team cases stay excluded. |
| R2 P2-02 resolution chronology | PRESERVED. Relevant RESOLVED chronology passes canonical timing before resolver/delay projection, including missing resolver. Reversed/future invalid evidence produces safe503; no negative DTO values. |
| R2 P2-03 validation beyond display caps | PRESERVED. Every selected authorized record is validated before aggregating/capping lists. Valid201 totals remain201; malformed timing or stage values at/beyond the200 display boundary fail closed. |
| R2 P2-04 age/duration labels | PRESERVED. Active cells identify case age; completed cells case duration. Mixed headings/filters and shared truthful zero/subsecond duration formatting remain fixed under browser clock skew. |
| R2 P2-05 accessible sorting | PRESERVED. All four tables use native sortable buttons inside th scope=col, one active aria-sort and hidden decorative carets, with real keyboard/focus proof. |
| R3 fifteen Ruff fixes | PRESERVED. Seven scripts retain exact accepted bytes: benchmark3RUF100; generator1RUF100; concurrency1RUF059; load3FURB157; optimization BLE001/RUF059/I001/FURB157; sponsor fixture2I001; classification fixture1I001. Exact unused-binding barrier, Decimal/import/fixture safeguards and narrow sampler containment annotation remain. Current canonical broad Ruff passes. |

## Complete accumulated-PR adversarial challenge

| Dimension | Assessment |
| --- | --- |
| Authorization and excluded-record isolation | Existing CaseQueryService/access policy owns RM/onboarder exact team, Director global/team/unassigned and HR denial. Creator/mine/date filters narrow existing authority. Selected inaccessible/absent case activity remains identical safe404. No frontend authorization or cross-team person/metric disclosure is introduced. Real Mongo scope/corruption/parity regressions pass. |
| Raw capture/selected decode/query shape | Existing automation port, Mongo adapter and MongoCaseStore own the opaque handle; service receives no raw documents. One finite authorized-ID find is fully materialized/closed before observation, zero for empty authority. Every raw key now binds captured authority; every selected envelope uses the unchanged strict codec. No whole-store decode, N+1, post-clock fetch, scope expansion or memory fallback. |
| Batch lifetime, ordering and missing/deleted records | Invalid/foreign selections, repeated reads, post-close use and context reuse fail. Success/failure cleanup releases owned data/callbacks; memory captures defensive models under lock and retains private binding fields. Later update/delete/caller mutation cannot rewrite the current snapshot; subsequent request sees absence, never resurrection. Shared ordering ignores driver order. Missing automation is omitted under existing rules. |
| Timing/midnight/exception failures | Exactly one final Dashboard observation follows case read and raw capture; Singapore N-date cohort, UTC legacy trend and returned durations share it. Selected stage and all-cohort timing plus successful resolution chronology validate before display caps. Unknown timings remain absent, integer means floor exactly. CASE_TIMING_PROFILE unchanged by R5; no second clock, clamp or suppression. |
| API compatibility and descriptive metrics | Omitted date_range retains all-history team totals and original30 zero-filled UTC historical_trend before new cohort filtering; v2 explicitly requests30d. Four date ranges and additive types remain. Creator cases and actual resolver fixes, once per RESOLVED blocker, stay separate; draft/open/cancelled/duplicate decisions cannot inflate counts. Mine discloses only actor workload and creator lists. Zero-touch/progress/stage/weekly formulas remain project-defined, with no sponsor SLA/compliance/productivity or Live claim. |
| All lists, filters and pagination | Established recent10/active5/scoped200/stage3 caps remain; aggregates use full selected cohort. Loaded case subset labels and empty claims are truthful, all local filters remain bounded, and Cases navigation respects its own authorized filters. Activity follows real server pages and offset cap without unlimited accumulation. |
| Accessibility, sorting and responsive scope | Four sort tables and six disclosures retain native keyboard/focus behavior. Date selector is named; empty paging is truthful. Actual relevant browser evidence covers narrow contained tables; inherited whole-document mobile overflow remains a documented limitation, not a new global-layout PASS. No R2 guard correction changes frontend bytes. |
| Cache identity/cancellation/session lifecycle | Existing AuthProvider/QueryClient/authenticated transport own identity/session/logout/401 clearing. Dashboard keys include user/team/view/range; activity adds creator/role/team/page/limit. AbortSignal, scope reset, invalidation/deletion prefixes and late old-session/team rejection remain. No persistent evidence cache or retry expansion. |
| Assistant/latest-main integration | Accepted AiAssistantPanel/context/navigation and authenticatedFetch remain. Accumulated App delta removes only the superseded unused local snapshot. Actual broader8-browser evidence includes PR89 Assistant, auth/RM/Director, portfolio/activity and logout/role navigation; current frontend is byte-identical for these paths. Original teammate/main ancestry is retained. |
| Persistence/provider boundaries | Existing strict schema1..10, identity/CAS, insert-only create, update-only mutations, restart/deletion and target no-replay owners remain. No direct route-to-Mongo, schema/index/migration, provider dispatch, connector/mapper/configuration or sponsor-rule change. Fresh complete real Mongo24-suite165 run passes on corrected product bytes. |
| Test/governance integrity | New8RED prove the explicit conformance defect before repair. Query-spy correction forwards projection arguments without removing exact one-capture/predicate assertions. No test/workflow deadline or accepted behavior was weakened. Canonical broad/configured Ruff and type/static checks pass; noncanonical invocation failures stay recorded separately. |

The request snapshot remains the approved sequential live-read POC boundary, not a new
cross-read transaction or persistent snapshot. Strict startup whole-store validation is
unchanged; excluded-record isolation on a running Dashboard is not a promise that corrupt
durable data can restart. Python private attributes are an internal abstraction, not a
sandbox against arbitrary trusted-code introspection. Driver/BSON/infrastructure failures
remain unavailable. These explicit limits do not waive selected-data integrity or RBAC.

## Runtime and other verification

Current independent executions after the integrity correction use prefix
`.runtime/pr95-r5-scoped-audit-r2-`:

| Fresh independent lane | Result | Evidence |
| --- | --- | --- |
| Focused dashboard/compatibility/scoped read/activity/portfolio plus R3 fixture guards |102 PASS,5.54s,exit0 | backend.log |
| Additional snapshot/schema/lifetime/over-cap adverse probes |7 PASS | probe.log; unchanged audited probe source audit-probe.py |
| New controlled-cursor real authenticated HTTP integrity probes |8 PASS: foreign/missing/null/integer keys times empty/nonempty cohort, each exact safe503, one closed finite capture | integrity.py; integrity.log |
| COMPLETE guarded physical Mongo on corrected product |24 suites,165 collected/165PASS,0fail/errors/skips,exit0 | physical-full.log |

Exact owned container was freshly verified as
`6dd114f17e0d0a02114a0d627e3a68be4653e1284f3a360ad70c664e31419046`,
mongo:7, running solely on loopback27029. The canonical guarded runner and existing
safety helper generate newly allowlisted test databases and verify cleanup absence.
No clm_poc connection, dotenv access, URI/credential output or actual provider request
was used. Full execution completed and the runtime slot was immediately released before
report writing; no reviewer backend/browser/Mongo runtime remains. Container ownership
and eventual service cleanup stay with the coordinator for the final gate.

Other evidence is explicitly attributed, not promoted to this reviewer's fresh executions:

- Coordinator fresh unchanged frontend:955PASS/57files/12.02s, typecheck/build PASS;
  `pr95-r5-scoped-final-frontend.log`, final-typecheck.log and final-build.log.
- Coordinator current canonical broad Ruff exact command
  `python -m ruff check apps/backend scripts tests --no-cache`:PASS;
  `pr95-r5-scoped-final-ruff-canonical.log`. Configured backend-CWD Ruff PASS and
  mypy127sources PASS; integrity-ruff2.log/integrity-mypy.log. Six static/security
  checks PASS; integrity-static.log. Dependency checks previously passed unchanged inputs.
- Previous direct independent frontend41 and actual browser2PASS25.7s remain applicable
  only to their unchanged raw frontend/test inputs, not new backend guard behavior.
  Root's previous actual broader8PASS35.0s covers Assistant/auth/navigation. No need to
  repeat unchanged browser/UI merely to relabel it current execution; actual controlled
  HTTP and complete physical runtimes above exercise the changed boundary freshly.
- Coordinator final explicit-command reruns completed: governance/performance244PASS
  in83.483s (final-governance.log) and canonical unittest-discovery contracts44PASS in
  1.401s (final-contract-canonical.log). Earlier direct pytest contract collection had
  two missing-helper import errors; final-contract.log and the older combined exit
  receipt preserve that invocation failure. Only the new canonical contract exit0 is
  passing evidence; no test/source/configuration change was used to clear it.
- Previous V2 complete backend2818PASS/171SKIP/3warnings/1073.47s is PRE-CORRECTION
  BASELINE ONLY. Corrected-source full ordinary backend is **PENDING** and assigned to
  the following fresh final Quality Gate. It is not supplied by focused102 or Mongo165.
- Final independent acceptance Quality Gate is **NOT_YET_RUN** at this verdict. Actual
  clean committed pre-PR is **NOT_RUN**, pending exact final PASS and later local commits.
  No GitHub Actions/hosted review claim follows from any local result.

## Failure history, hygiene and remaining acceptance boundary

Immutable R4 FAIL, original R5 adversarial CLEAR and final R5 FAIL are preserved with
exact hashes above. Eight integrity RED failures, first signature E501 and invalid edit/
filename invocations remain in their receipts. The correct new test signature was only
wrapped; no assertion changed. Prior full physical164PASS/1FAIL and focused12PASS/1FAIL
were test-spy signature failures; the fresh complete corrected165 run is required proof,
not a silent substitution of focused evidence. Earlier UI6RED/backend8RED and corrected
harness/fixture assumptions also remain.

Two extra noncanonical lint invocations are not the required broad check: root-dot
covered archived Python evidence and found9I001; forcing backend configuration over all
root scripts/tests produced193 diagnostics. They remain failed invocation evidence. No
historical source/configuration was changed to chase them; the exact documented broad
command and configured backend commands pass. Existing Vite680.40kB bundle warning,
SSR/React test-render warnings, inherited mobile overflow and optional native OCR limits
remain. Ordinary physical skips must be reconciled with actual physical coverage by the
final gate; unavailable native OCR never becomes PASS.

Tracked full-delta whitespace passed; new report/test Markdown/text whitespace is checked
explicitly because Git omits untracked paths. No mass line-ending cleanup, dependency,
lockfile, generated artifact, secret/confidential artifact or external configuration
change is introduced. Existing R3 script bytes, timing contract, PR89 and PR96 content
remain under exact reviewed identities. No sponsor production question is closed; no
Mock/Local/Partial mode is promoted to Live. Historical billing-refused CI remains
**NOT_EXECUTED**, and no hosted review or remote write is requested here.

Current required adversarial implementation findings: **NONE**. The corrected candidate
is **CLEAR for a separate fresh final independent Quality Gate** on unchanged frozen
content. That gate must directly establish final full-backend and other required current
acceptance evidence, inspect the corrected preflight guarantee and issue its own honest
verdict. This report provides no implementation commit, publication or merge authority.
Any reviewed content change or material latest-main drift requires affected re-review.

Sole tracked reviewer write: this assigned new R2 report. Ignored probes/logs are evidence
only. No source/test/configuration/ordinary-document fix, prior report edit, stage/commit,
fetch/push/PR/thread action, shared-history rewrite, protected-data operation, provider
call, PR96 modification or next-phase work occurred. Root remains the sole Git/source
writer and owns preserving main, teammate history and all registered worktrees.

## Complete frozen input inventory

All62 paths are intended implementation or supporting tests/contracts/planner/evidence;
none is unexpected. This report is an additional supporting path, hashed separately.

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
| `.ai-pipeline/reports/PR95_R5_FULL_PR_ADVERSARIAL_REVIEW.md` | `9cfd0aa2548593559722542bce5fd2a3895fa437d930fdf5125d229cfec72842` |
| `.ai-pipeline/reports/PR95_R5_IMPLEMENTATION.md` | `b10faa93343e76214940a77d5a4b6e497dacc6e31037f33c67b4ef552270c250` |
| `.ai-pipeline/reports/PR95_R5_INTERFACE_PREFLIGHT.md` | `443a25ec606b42195460d702b11c2299ac6a43c827b45869a7e9e01f4b28fa32` |
| `.ai-pipeline/reports/PR95_R5_PREFLIGHT_CONFORMANCE_REMEDIATION.md` | `5a499be8e9546820c20b4e3533dde7d13777adc1c9ab3a14bd38d87e172dcdb0` |
| `.ai-pipeline/reports/PR95_R5_QUALITY_GATE.md` | `0d8cd885f58056d893b147f7fc40a5534cd0a612accff7bb14f47b1803c26de2` |
| `apps/backend/app/domain/case_management.py` | `ab2ef38e60c30e45f0f425c3e20c02510ed7b30fa0c7f47a70c3e6c84e73cd70` |
| `apps/backend/app/domain/dashboard.py` | `f63a1fab027bd2efc2f8fc0281d44ad99c04f7eb1149dbffd44faab97ffdcb2a` |
| `apps/backend/app/main.py` | `0ceef47b725fd1fe736ef909a05d6dc40ef5ec3f40a305b4732d018f3ad659e6` |
| `apps/backend/app/persistence/mongo_case_store.py` | `97e92022c19cac894599cb9b9b455f63b8a7e23e478c73534cb8c6b56b6d7380` |
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
| `apps/backend/tests/test_pr95_r5_scoped_dashboard.py` | `600b328aa0b365f678128f73b4a4a1b02113051e5e4dc1e9ac078dbd77119e50` |
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
