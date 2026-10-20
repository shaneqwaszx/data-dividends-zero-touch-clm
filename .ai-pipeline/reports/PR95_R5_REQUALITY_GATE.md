# PR95-R5 final independent combined re-Quality Gate

## Outcome

**PASS.** The complete frozen accumulated PR95 candidate satisfies the six owner-authorized
R5 corrections, including corrected R5-QG-01, while preserving the three original R4
findings' intended corrections, all five R2 fixes and all fifteen R3 Ruff corrections.
No required implementation finding remains. This fresh reviewer authored none of the
implementation, preflight or comprehensive adversarial assessments.

This verdict accepts the exact uncommitted content below. It permits the coordinator's
already owner-authorized next stage: scoped local commits, unchanged-content verification,
fresh main assessment and the actual clean committed pre-PR gate/checklist. Those later
operations are **NOT_RUN at this verdict** and are not certified prospectively. No push,
hosted-review request, PR/thread/description action, PR96 modification, merge or next
phase is authorized. Recommendation at the gate boundary: **LOCAL IMPLEMENTATION ACCEPTED;
complete local commit/pre-PR verification before READY FOR PUBLICATION AUTHORIZATION**.

## Exact reviewed identity, authority and independence

- Worktree: C:/Users/shane/.codex-clean2/worktrees/pr95-dashboard-remediation-20261018/data-dividends-zero-touch-clm.
- Branch: codex/pr95-dashboard-remediation-20261018.
- Committed/published starting HEAD: e970a0b31fe2cf2c1617dcc759c9d2131433ba68.
- Committed starting tree: 8abb0de47de69a24f88550f3ddece82c03b7a626.
  These committed identities exclude the uncommitted R4/R5 changes accepted here.
- Comparison base/current origin/main: 4a280da473dcdbeb345ffdfa79aaa4c001e75f62.
- Frozen complete input: .runtime/pr95-r5-scoped-regate-frozen.json, all63 raw paths.
- Compact sorted JSON path/hash map SHA256:
  14103c987dd170f9dab01231dc622e9288ab37f640f61a8b6b0bd9c85392c79e.
- Independently reproduced default git diff --binary origin/main -- SHA256:
  35abe818e0b5a578b507b7fc112958eb4ade64c5c7e58a054d534a1e4e2cccac.
- Independently reproduced explicit core.autocrlf=false serialization SHA256:
  9a0045d592ad718426e3b29badf5e8982906d64eacebb509c5e1a90862b92972.
  The different options explain the two diff identities; the complete raw-file map is
  authoritative and includes new files omitted by ordinary Git diff.
- Main and original teammate1c1fd9fbf1a68f79137d150ac8609cf811b10938 ancestry directly PASS.
- Interface preflight PASS SHA256:
  443a25ec606b42195460d702b11c2299ac6a43c827b45869a7e9e01f4b28fa32.
- Completed new full-PR R2 adversarial prerequisite PASS/CLEAR SHA256:
  ccaf5adf579ea1872c64cc1d28011fc1a57203396891089edaaad3206bf86672.
  This prerequisite was read and independently challenged; it does not supply this verdict.
- Immutable R4 FAIL remains3334134fbeef63ae2a30fe934e1fee43e9168a1d17ab5e82979d786e1292d6ee;
  original R5 adversarial CLEAR remains9cfd0aa2548593559722542bce5fd2a3895fa437d930fdf5125d229cfec72842;
  initial R5 final-gate FAIL remains0d8cd885f58056d893b147f7fc40a5534cd0a612accff7bb14f47b1803c26de2.
  The latter correctly found a mandatory preflight gap missed by the earlier assessment;
  neither historical verdict is overwritten or retrospectively relabelled PASS.

All63 raw input hashes, base, HEAD/tree, ancestry, both diff serializations and empty index
were checked at entry; raw hashes/base/HEAD/tree/index and whitespace were rechecked after
runtime completion. The sole tracked reviewer write is this new report, separately hashed
outside its self-referential input manifest. No source/test/contract/configuration or
previous report changed during this gate. The coordinator's fresh fetch/direct remote
observations and primary-preservation receipt are explicitly attributed, not remote
commands performed by this reviewer.

Authority/read-set: complete latest R5 owner attachment; root/backend/frontend AGENTS;
canonical fyp-quality-gate/report template, integration/pre-PR checklist, architecture,
persistence, cache and security skills/checklist; dev_context union for BACKEND_DOMAIN,
BACKEND_API, PERSISTENCE, AUTH_RBAC_SECURITY, FRONTEND_UI, FRONTEND_STATE_CACHE and CI_TOOLING;
workflow/merge/coordination/current architecture/project state and sponsor boundaries;
case access, timing and persistence contracts; accepted POC regression catalogue;
original planner, approved interface/plan, R4 handoff/design/FAIL, relevant R2/R3 records,
R5 initial FAIL and remediation, both adversarial reports; actual accumulated diff,
owning source, tests and current execution receipts. No implementation authority was used.

Capabilities directly established: Python3.12.10 task venv, Node22.23.3, configured
pytest/Vitest/Ruff/mypy, actual guarded HTTP/Playwright and physical Mongo. Heavy runtimes
were serialized in an exclusively released slot. All reviewer processes/sessions ended
before runtime release. No dotenv, protected database, credential or real provider access
was needed. The primary main checkout/original seven untracked directories and all33
registered worktree paths are preserved per coordinator receipt
.runtime/pr95-r5-scoped-preservation-check.json; this reviewer performed no Git mutation.

## Acceptance and every finding disposition

| Finding / requirement | Independent disposition |
| --- | --- |
| P2-06 authorized scoped raw capture | VERIFIED FIXED. CaseQueryService resolves backend scope before one finite authorized-ID capture. Mongo fully materializes and closes that query before the one final observation. Final Singapore cohort IDs precede full decoding through the unchanged strict codec. Service receives only the existing automation port's opaque handle. No N+1, whole-store decode, after-clock fetch, fallback or new authorization owner. |
| R5-QG-01 preflight conformance | VERIFIED FIXED. Every raw routing key is first required to be a canonical string in the captured authorized set; only then may an authorized excluded-cohort key skip full decoding. Foreign/missing/null/integer keys fail even for an empty cohort. The unchanged finally cleanup consumes/releases authority, documents and callbacks on every result. Eight failing-first cases and fresh full-suite/direct actual HTTP probes prove the correction, including failure after a preceding valid decode with no partial response. |
| R4-A1 negative stage durations | VERIFIED FIXED. Every selected retained stage sample is checked before DTO/cap projection using canonical CaseTimingDataInvalidError and safe503/DASHBOARD_UNAVAILABLE. No clamp, silent discard, broad domain-validator change or blanket Pydantic catch. Selected/excluded data, negative/zero/missing/exact integer values and201st selected sample are covered by current unit, HTTP and genuine Mongo evidence. |
| R4-A2 truthful200-case lists | VERIFIED FIXED. All cases/Your cases/Blocked cases disclose loaded subset and authoritative cohort count, local filter/pager scope and existing authorized Cases navigation. Mine explicitly identifies creator-only cases; capped filtered-empty statements refer only to loaded rows. Established API cap200, aggregate totals and bounded browser requests remain.0/1/200/201/250 component cases and actual205-case journey pass. |
| R4-V1 browser inventory | VERIFIED FIXED. Canonical current discovery110 with complete disjoint55/55 shards, unchanged9960-second launcher and234-minute CI budget. The exact expectation is reconciled; no workflow, safety deadline, test removal or skip weakening. Current244-test governance/performance lane passes.110 is discovery, not a claim that all110 browser selectors executed here. |
| R4-M1 empty pagination | VERIFIED FIXED. Empty local pagers say0of0 with Prev/Next disabled, preserving nonempty ranges and clamping. |
| R4-M2 date selector accessibility | VERIFIED FIXED. Native control is explicitly named Dashboard date range; existing four options, selected30d UI default, callbacks/backend semantics/cache identity remain. |
| R4 P2-07 server activity pagination | PRESERVED AND VERIFIED. One10-event API page follows offset/has_more, permits Prev/refresh/retry and handles loading/error/empty separately. Actor/role/team/creator/page/limit participate in key identity; scope/session resets and cancellation reject late old data. Live boundaries and offset cap/Audit narrowing are disclosed. Real journey traverses all fixture activity beyond100 without unbounded accumulation. |
| R4 P2-08 keyboard stage disclosure | PRESERVED AND VERIFIED. All six native buttons retain unique stable controls, labelled hidden regions and aria-expanded; Tab/Shift+Tab/Enter/Space, focus, repeated toggles and sort-while-expanded pass in the actual browser. |
| R2 P2-01 creator validation | PRESERVED. Mongo schema9/10 nullable creator grammar and strict earlier-field absence remain. Authorized invalid facet precedes creator matching; other-team corruption cannot leak, and malformed authorized nonmatching creators cannot hide. Full/physical/compatibility tests pass. |
| R2 P2-02 resolution chronology | PRESERVED. Canonical relevant resolved chronology validation precedes resolver workload and delay notes even without actor evidence. Reversed/future facts return sanitized503 instead of negative projection/500. |
| R2 P2-03 validation beyond display cap | PRESERVED. Every selected authorized record validates before all display caps; valid201 remains201 in aggregates/200 in lists, invalid selected201 fails closed. |
| R2 P2-04 age/duration labels | PRESERVED. Active cells say Case age, completed cells Case duration; shared exact zero/subsecond formatting and backend values drive rendering/filter/sort despite browser clock skew. |
| R2 P2-05 accessible sorting | PRESERVED. All four tables use native scoped header buttons, one active aria-sort and hidden decoration; actual keyboard/focus and sorting journeys pass. |
| R3 fifteen inherited Ruff corrections | PRESERVED. Seven script raw blobs exactly match accepted HEAD. benchmark3RUF100; generator1RUF100; concurrency1RUF059; load3FURB157; optimization BLE001/RUF059/I001/FURB157; sponsor fixture2I001; classification fixture1I001. Broad and configured Ruff directly PASS. Narrow approved sampler containment annotation and exact byte/fixture/error safeguards remain, with no global rule weakening. |

## Contract, architecture, security and adverse review

**Architecture: PROCEED within the approved existing-owner design; no new ADR required.**
The existing automation repository/store/adapter owns request-local capture and strict
translation. Dashboard owns final time/cohort/calculation; CaseQueryService/access policy
owns authority; frontend auth/query/navigation owners retain session/cache lifecycle.
There is no raw service DTO, second repository/authorization/calculation owner, persistent
batch/cache, schema/index/migration or new dependency direction. Dashboard's unscoped
list_records call is retired; the port remains for proven other consumers. Current
architecture/persistence docs describe the actual bounded lifecycle. Timing contract
raw bytes and all seven R3 script blobs independently equal HEAD.

Memory captures defensive model snapshots under its existing lock, preserves private
binding fields and validates only selected records; Mongo reads fresh private raw driver
documents for the finite authority set, using existing strict historical/current codec.
Selection cannot widen capture; duplicates and key/nested mismatches fail closed. Missing
or pre-capture deleted records stay absent. Later update/delete/caller mutation cannot
rewrite that captured request; subsequent requests observe current absence. Success,
invalid/mutable/foreign selection, decode failure, caller abort, no-read exit, retry and
re-entry do not leave a reusable batch. Shared ordering ignores raw cursor order.

RM/onboarder exact-team, Director global/team/unassigned, HR denial and safe identical
inaccessible/absent404 remain. My work case lists/counts stay creator-only; resolver work
may include authorized teammate cases. Genuine RESOLVED blockers count once per blocker,
last recorded eligible resolver, excluding drafts/open/cancelled/unattributed evidence;
resolver-only people have zero creator counts. Selected cohort limits both metrics.
Means and sub-millisecond floors remain exact integer arithmetic. No out-of-scope person,
case or total is projected; no authorization or current mutation lock/CAS was bypassed.

The API keeps omitted date_range=all and original30 zero-filled UTC historical_trend
before the new created-date cohort. UI explicitly requests30d;7d/30d/90d/all use unchanged
Singapore calendar dates from the same final post-capture observation. All returned
case/oldest-open durations and legacy trend use that instant. Midnights/concurrent
resolution are executed regressions. Zero-touch, progress, stages and weekly formulas
remain the authorized descriptive project-defined values, not sponsor SLA/compliance,
staff-performance, legal approval or Live-integration calculations.

PR89 Assistant/context and authenticated transport remain; main ancestry is preserved.
User/session/team/view/range/activity paging inputs remain scoped; AbortSignal, session
rotation/logout/401 clearing and deletion invalidation protect late replies. No evidence
is persisted to browser storage, sensitive URLs or a new query owner. Existing scoped
Cases/Audit navigation retains its own authorized filters. No unsupported source winner,
connector/mapper/configuration/provider status or target-ledger/no-replay behavior changes.
External ACRA/GoldTier connectors were neither edited nor called by this reviewer.

**Security: PASS for affected boundaries.** Raw evidence remains internal, selected
corruption is unavailable and projected errors are fixed safe503. Direct fresh controlled
HTTP probes return exactly DASHBOARD_UNAVAILABLE with no retained/private data. The finite
Mongo predicate excludes real foreign rows; impossible foreign-result probes test the
mandatory defensive contract, not an observed real-Mongo scope bypass. Six static/security
checks pass. The scanner covers configured patterns and tracked/nonignored new paths;
it is not a universal privacy or external-security certification.

The ordinary sequential live-read POC limitation remains: this is not a cross-read
transaction, production snapshot-isolation or distributed exactly-once claim. Driver/BSON
or infrastructure failures remain unavailable. Startup still validates the whole durable
store strictly; excluded full-envelope isolation on a running Dashboard does not permit
corrupt durable data to restart. Python private attributes are an internal abstraction,
not a sandbox against arbitrary trusted-code introspection. These explicit boundaries
do not defer an unmet current criterion.

## Fresh direct independent execution evidence

Unique new final-gate evidence prefix is .runtime/pr95-r5-scoped-regate-.
All commands use this gate's exact63-path freeze. Counts overlap broader lanes and must
not be added as extra distinct tests.

| Direct reviewer execution | Observed result / receipt |
| --- | --- |
| COMPLETE final-source ordinary backend |2826 PASS,171 SKIP,3 warnings,exit0,1075.62s. backend-full.log plus backend-start/end/exit receipts. Started22:35:47SGT, ended22:53:46SGT. Explicit no-plugin-autoload/AnyIO/no cache runner; no physical URI. |
| Guarded real Mongo PR95 suite |1suite,13collected/13PASS,0fail/errors/skips,exit0; physical.log and physical-exit.txt. Same existing safety runner, freshly generated allowlisted disposable databases, cleanup absence verified. |
| Additional gate lifecycle/adverse probes |8PASS; adverse.py/adverse.log. Both modes: caller abort closes, mutable selection consumes, returned model cannot mutate later snapshot. Mixed valid then foreign/noncanonical raw key never returns partial success and clears refs. |
| Actual authenticated HTTP query-integrity probes |8PASS; http-integrity.log. Fresh execution of independently inspected audit-r2-integrity.py: foreign/missing/null/integer times empty/selected cohort, exact safe503 and one closed finite query. |
| Focused frontend UI/cache |41PASS across2files,3.25s; ui.log. Covers loaded subsets, labels, empty paging, retained R2/R4 interaction and cancellation/isolation. |
| Actual configured PR95 browser |2PASS,25.6s,exit0; browser.log/browser-exit.txt. Canonical run_e2e on task ports8775/4183, guarded local Mock HTTP/real Chromium, native keyboard/sorting,205-case cap/navigation and real activity beyond100. Owned processes cleanly closed. |
| Canonical broad Ruff |PASS,zero errors; python -m ruff check apps/backend scripts tests --no-cache, ruff.log. |
| Configured backend Ruff |PASS; backend CWD python -m ruff check . --no-cache, ruff-backend.log. |
| Configured cold backend mypy |PASS,127sourcefiles; backend CWD python -m mypy app --no-incremental, mypy.log. |
| Canonical public contract suite |44PASS,1.389s,exit0; python -m unittest discover -s tests/contract -p test_*.py, contract.log. |
| All six static/security checks |PASS/exit0 each; check_project_state, check_architecture, check_tooling_config, check_policy_authority, check_external_provider_readiness, check_secrets; static.log. |
| Python dependency integrity |PASS, no broken requirements; pip.log. |
| Identity/hygiene |All63raw hashes/map and both diff serializations PASS; empty index; tracked full-delta git diff --check PASS and all task-owned new-file whitespace explicitly PASS. Final checks repeated after execution. |

Full backend command, from worktree root: task venv python -m pytest apps/backend/tests
-o addopts= -p no:cacheprovider -p anyio.pytest_plugin -q -ra, with PYTEST_DISABLE_PLUGIN_AUTOLOAD=1,
PYTHONPATH containing worktree backend/root and intentionally empty PHASE12_MONGO_URI.
All171 ordinary skips are reconciled:165 real-Mongo tests deliberately run separately,
plus6 Local Tesseract unavailable tests. Native OCR remains **NOT_EXECUTED / UNAVAILABLE**,
not PASS. Three warnings come from existing deliberately malformed synthetic Pydantic
provider-conformance fixtures, not a new Dashboard warning or suppressed check.

The exact owned container was directly verified by safe-format inspection as ID
6dd114f17e0d0a02114a0d627e3a68be4653e1284f3a360ad70c664e31419046,
name clm-pr95-r5-mongo-20261018, image mongo:7, running only on127.0.0.1:27029.
The wrapper builds its connection value only in memory and uses the canonical guarded
runner/safety helper; no URI is printed or retained. No clm_poc connection/test/cleanup,
dotenv access, external provider request or shared-container operation occurred.
After all reviewer physical/API/browser checks closed, runtime ownership was released.
The coordinator subsequently reports exact-ID stop/removal of only that owned container,
without volumes/prune; its sanitized container-cleanup.log is attributed operational
closeout, not a reviewer database action or a prerequisite substituted for test evidence.

## Other current exact-content evidence, explicitly attributed

The following receipts were inspected, not relabelled as this reviewer's executions.
All13 frontend/browser input hashes match the actually executed V2 input exactly; the
sole later product change was the backend raw-key guard, freshly covered above.

| Lane / owner | Current applicable result |
| --- | --- |
| Preceding independent full-PR R2 audit, corrected product |102focused backend PASS5.54s,7additional snapshot/schema/lifetime/201st probes PASS,8actualHTTP integrity probes PASS and COMPLETE24-suite physical Mongo165/165PASS,0fail/errors/skips; audit-r2-backend/probe/integrity/physical-full logs. This whole165 physical lane, not only the gate's13 subset, covers the165 ordinary physical skips. |
| Coordinator full frontend |955PASS/57files/12.02s; final-frontend.log. Gate41 are a subset, not additional unique tests. |
| Coordinator frontend typecheck/build |PASS; final-typecheck.log/final-build.log; npm tree dependency check PASS on unchanged manifests. Existing680.40kB bundle warning remains. |
| Coordinator governance/performance |244PASS83.483s,exit0; final-governance.log. Includes110-selector discovery, complete55/55shards, unchanged deadlines/cleanup guards and inherited sampler protections. Expected injected E2E SUITE FAILED text is inside a passing runner-failure test. |
| Coordinator broader actual browser |8PASS35.0s; browser-broad.log, current scoped prefix. PR89 Assistant, auth/navigation, RM, Director, portfolio/activity, responsive shell and logout/role reset. The gate freshly reruns the2PR95 journeys; neither count implies all110selectors executed. |
| Coordinator current lint/type/static/contracts |Canonical broad Ruff, configured backend Ruff/mypy127, sixstatic and canonical44contracts PASS, corroborated by direct final-gate reruns above. |
| Primary/worktree preservation |Coordinator direct receipt confirms primary remains main atcc10a2b626ef92d2dd44600d488c1f15cc4f04f8 with original7untrackeddirs, all33registeredworktreepaths preserved. Remote main4a/publishede970 were freshly observed before this gate; coordinator repeats drift after local commits. |

Earlier V2 full backend2818PASS/171SKIP/3warnings/1073.47s is PRE-CORRECTION BASELINE ONLY;
it is superseded for final-source acceptance by this reviewer's direct2826PASS result.
Historical R3 backend/physical and similarly named earlier R5 files are not substituted.
POC call-stopping/terminal-state/no-replay/provider-label regression scenarios remain
covered by fresh complete backend plus complete physical suites; the actual browser
also reaches a genuine local Mock completion with final human confirmation. Catalogue,
external transport and sponsor authority are unchanged; no new catalogue scenario or
Live/Sandbox interoperability is inferred.

## Preserved failures, limitations and readiness boundary

The immutable R4/R5 FAIL reports remain. Failing-first evidence includes original
UI6RED/backend8RED,109-versus110 inventory failure, and eight raw-integrity RED cases.
Earlier snapshot-binding/counter and browser fixture assumptions, physical164PASS/1FAIL
and focused12PASS/1FAIL test-spy signature errors remain recorded. The spy now forwards
projection arguments while retaining exact authorized-query/count assertions; a fresh
COMPLETE165 physical PASS clears that lane. No test, validation, configuration or safety
deadline was weakened to obtain PASS.

Noncanonical invocation failures remain failures: root-dot Ruff inspected archives and
reported9I001; forcing backend config over all root scripts/tests reported193; root
mypy lacked canonical configuration; direct pytest contract collection lacked two
helpers. Canonical documented/configured commands pass, including direct gate reruns.
The first new test signature E501 was wrapped before freeze without assertion changes.
This reviewer's first unquoted PowerShell HEAD-tree read was an argument-parsing error;
the subsequent quoted/Python Git command directly verified the exact expected tree.
No product change was used to clear any invocation error.

Native OCR6 remain unavailable. Existing SSR/React test-render and Vite bundle warnings
remain. Inherited whole-document mobile overflow is not certified absent; actual Dashboard
table containers are bounded at390px. Browser evidence covers relevant configured
journeys, not all110discovered selectors. Static/secret scanners have their documented
coverage limits. Production-scale snapshots/indexing, sponsor policy and actual provider
interoperability remain separate future boundaries, not findings silently waived here.
Historical GitHub billing-refused jobs remain **NOT_EXECUTED**, never CI PASS. No new
hosted review or push/pull-request CI was requested or implied by this local verdict.

Current required fixes/blockers: **NONE for this frozen local implementation**.
Clean committed pre-PR remains **NOT_RUN at gate closure**, pending authorized local
commits and fresh main assessment. Main/teammate ancestry is valid; the coordinator must
preserve every reviewed raw byte through explicit staging and verify later committed
identities. Any changed reviewed content or material main drift requires affected fresh
review. This report predicts no final commit SHA/tree or hosted-review verdict.

Sole reviewer tracked write: this report. No source/test/configuration/docs fix, historical
report edit, stage/commit/fetch/push, branch/worktree change, PR/thread action, PR96 edit,
protected-data operation, provider call, merge or next phase occurred. The owner alone
retains publication/merge authority. Final independent acceptance verdict: **PASS**.

## Complete frozen reviewed input inventory

The63 paths below bind the entire accumulated candidate against main, including
historical supporting reports. Every path is intended product/script work or supporting
test/contract/planner/review evidence; no unexpected path was found. This report is the
64th supporting path, separately hashed after writing.

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
| `.ai-pipeline/reports/PR95_R5_FULL_PR_ADVERSARIAL_REVIEW_R2.md` | `ccaf5adf579ea1872c64cc1d28011fc1a57203396891089edaaad3206bf86672` |
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
