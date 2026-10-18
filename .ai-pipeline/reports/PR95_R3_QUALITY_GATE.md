# PR95-R3 independent combined Quality Gate

## Outcome

**PASS.** The frozen combined candidate independently satisfies the five hosted P2
corrections and the bounded resolution of all15 inherited Ruff diagnostics. The mandatory
repository-root Ruff command passes with zero errors. No required implementation fix
remains. The single specifically justified local BLE001 annotation is independently
**APPROVED** below; no global rule, configuration or validation relaxation was introduced.

This accepts the exact uncommitted content identified below. The historical R2 FAIL
report remains unchanged. The next authorized stage is scoped local commits followed by
latest-main assessment and the clean committed pre-PR gate. This review does not certify
that later stage in advance and authorizes no publication, hosted-review/thread action,
merge, provider execution or next phase.

## Reviewed identity and authority

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/pr95-dashboard-remediation-20261018/data-dividends-zero-touch-clm`.
- Branch: `codex/pr95-dashboard-remediation-20261018`.
- Base/current committed HEAD: `390f46ea08c877b7d86b85e9109fc8add3950d4a`.
- Committed baseline tree: `976548b693e406241d34eab043fc68b6fb03d72f`.
  This tree identifies the published baseline, not the new uncommitted fixes.
- Accepted main/merge base: `4a280da473dcdbeb345ffdfa79aaa4c001e75f62`.
- Original teammate ancestry remains `1c1fd9fbf1a68f79137d150ac8609cf811b10938`.
- Local remote-tracking published branch remains `ui-enhancement-v1` at390f46.
  Fresh fetch/remote identity verification is coordinator-attributed evidence. This
  reviewer performed no fetch or Git mutation. The coordinator must repeat drift checks
  in the subsequent local commit/pre-PR stage.
- Frozen18-path manifest: `.runtime/pr95-r3-frozen.json`.
- Canonical SHA256 of sorted compact JSON path/hash map:
  `da2b5b3d3ced05bf03bd52adc5bb410606557dd510c4a962ff6fd3d8ce047cd7`.
- Tracked `git diff --binary HEAD` SHA256:
  `d96b7d8f3f26d24e71a1d40f048c63debb5abdaf5caae68cc4f5780a1a93cc24`.
- All18 raw hashes, canonical manifest digest and binary diff were independently checked
  before/after execution. Index remained empty. All eight previously reviewed R2
  source/test hashes are exact matches; no R2 implementation was reopened.
- Preserved R2 FAIL report SHA256:
  `73029b67883331ab8b6fd5194560758f4c0a8936af1f8a7ac7cc8925e0f0b45e`.

Authority/read-set: explicit pasted PR95-R3 owner assignment; root/backend/frontend
AGENTS; canonical skill routing and fyp-quality-gate/report template; development workflow,
merge protocol, reviewer/security roles; current owner architecture/project state,
case timing, activity, access and persistence contracts; security/persistence skills;
accepted POC regression catalogue; exact changed source/tests; prior R2 gate and freeze.
`dev_context.py` was run for BACKEND_DOMAIN, BACKEND_API, FRONTEND_UI, PERSISTENCE,
AUTH_RBAC_SECURITY and CI_TOOLING. Shared cache/auth/Assistant owners remain regression
surfaces, not newly edited owners. The reviewer authored none of the implementation.

Current-session capability was established by execution: task-local repository venv,
pytest/Ruff/mypy, installed Vitest/Playwright, real guarded HTTP/browser lifecycle and
physical Mongo runner. Heavy runtime suites were serialized. The task-local venv was
provisioned by the coordinator when the pre-existing primary venv lacked the optional
psutil verification dependency; tracked requirements/locks and the primary venv were
not changed. All current broad evidence uses the task-local runtime; historical results
from other inputs are not substituted.

## Acceptance and five hosted P2 dispositions

| Criterion / finding | Independent disposition |
|---|---|
| [P2-01](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/95#discussion_r4306346317): malformed creator hidden by prefilter | VERIFIED FIXED. Existing Mongo team/case selection precedes validation; creator matching now occurs only inside validated rows. The invalid facet still inspects every relevant authorized projected envelope. Physical schema9/10 string/bool/number/array/object/empty corruption fails closed; matching/nonmatching/null/legacy rows, deterministic paging and other-team/selected-case isolation remain correct. |
| [P2-02](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/95#discussion_r4306346319): reversed resolution chronology | VERIFIED FIXED. Relevant retained RESOLVED chronology is checked with canonical project_case_timing before resolver workload or completed delay notes, including absent resolver evidence. Existing API mapping returns exactly sanitized503 DASHBOARD_UNAVAILABLE. No negative result, Pydantic500 masking, clamping or silent discard. Present/absent resolver, RUNNING/COMPLETED, team/mine and memory/Mongo paths were executed. |
| [P2-03](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/95#discussion_r4306346322): invalid timing after display cap | VERIFIED FIXED. Every selected authorized cohort case is validated before list caps and metric projection. Invalid started_at and completed_at at selected position201 fail closed; valid201 cases still produce201 totals/history and only200 selected rows. Existing authorized date/creator semantics and the two aggregate reads remain; no provider/detail fan-out or new timing owner. |
| [P2-04](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/95#discussion_r4306346327): completed durations labelled Age | VERIFIED FIXED. Both mixed-status headers and filters say Case age / duration; cells identify Case age for unfinished and Case duration for completed. Active/blocked/completed/missing legacy values, zero/subsecond rendering, filtering and sorting were checked without changing returned numbers or API types. |
| [P2-05](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/95#discussion_r4306346330): mouse-only sortable headers | VERIFIED FIXED. Native scoped th headers contain native type=button controls, active aria-sort and hidden decorative caret. Actual Tab/Shift+Tab, Enter and Space work in pipeline timing, workload, all-cases and your-cases tables. Direction changes, focus, filters, navigation and bounded table scrolling remain supported. |
| Exact R2 preservation | PASS: all eight raw-byte hashes and the prior R2 FAIL report remain unchanged. Fresh owning/physical/frontend/browser tests verify behavior, rather than assuming the previous gate supplies current PASS. |
| Exact inherited baseline | PASS: seven original script copies independently match published390f46 and main4a280da modulo checkout line endings. Independent Ruff on published baseline blobs reproduced all15 exact rule/location/message tuples; coordinator cross-baseline receipts confirm both accepted refs. |
| Full combined verification | PASS as individually attributed below; genuine skips/warnings remain explicit. |
| Independent boundary | PASS: report-only reviewer, no implementation/test/configuration/Git/GitHub/lifecycle fix. |

Hosted discussions remain unresolved on GitHub. These dispositions apply to local content;
no thread was resolved/dismissed and no new hosted review was requested.

## Fifteen inherited Ruff dispositions and script equivalence

| Authorized script | Diagnostics / reviewed correction |
|---|---|
| `scripts/benchmark_blocker_review.py` |3 RUF100: remove obsolete E402 directives; retain F401 suppression on the required conftest side-effect import. Executable AST unchanged. |
| `scripts/generate_zero_touch_happy_path_documents.py` |1 RUF100: remove obsolete E402 only; executable AST unchanged. |
| `scripts/performance_concurrency.py` |1 RUF059: rename unused context-manager tuple binding bundle to _bundle; context evaluation, lifetime, returns, workload/assertions unchanged. |
| `scripts/performance_load.py` |3 FURB157: Decimal(60), Decimal(40), Decimal(0) replace the corresponding exact integer strings; no percentage/order/calculation change. |
| `scripts/performance_optimization.py` |1 BLE001: specifically approved local annotation preserving existing catch;1 RUF059 unused-binding rename;1 I001 multiline import normalization;1 FURB157 exact Decimal(25). |
| `scripts/sponsor_demo_browser_fixture.py` |2 I001: only the flagged top-level and local import blocks normalized; guarded actual offline sponsor-garden browser execution verifies the local import branch. |
| `scripts/zero_touch_classification_browser_fixture.py` |1 I001: only the flagged top-level imports normalized. Cold import, preconnection guards and missing-native-OCR cleanup/refusal are exercised. |

**Independent BLE001 approval:** the sole new `# noqa: BLE001` is attached to the
existing Resources.poll `except Exception` and specifically explains OS-sampler
containment/no invented evidence. The catch itself is unchanged. Narrowing it would
allow unexpected sampling failures to escape the worker. Fresh injected Process
constructor RuntimeError, ValueError, TypeError and OSError produce no first observation,
zero peak RSS/empty CPU evidence, fixed startup refusal and a joined thread with no
unhandled-thread callback. Existing invalid-observation, startup/cleanup deadline and
positive real-sample tests also pass. This approval is limited to this exact local
annotation; it is not a blanket suppression or permission to hide benchmark failures.

The performance source-preservation test necessarily accommodates the authorized unused
binding rename. It requires exactly one old occurrence and one new occurrence, reverses
only that exact spelling for comparison, then compares every other source byte including
all original assertions. No workload/count/order assertion was removed or relaxed; no
broad AST normalization replaced that barrier. The new fixture tests supplement existing
safety checks and prove invalid mode/environment/port refuses before Mongo connection,
and unavailable actual OCR closes its owned fake client and reports truthful failure.

Coordinator execution reviewed: seven script ASTs are identical after only the explicitly
allowed unused-binding/Decimal/import transformations; all12 precision/value Decimal
as_tuple checks pass; all seven imports pass, including seven fresh processes with socket
connections forbidden. Actual blocker benchmark baseline/batch measures preserve expected
mutation/GET counts and unchanged target; ownership workload, one native memory intake and
one full memory-load group complete with original correctness/count/order/no-target
assertions. Outputs were redirected to task-owned ignored scratch, not historical evaluation.

Separate line-ending audit: the first six original checkout copies used CRLF, but the
candidate uses the LF already stored in HEAD for those six files. There is no committed
EOL conversion. Classification retains its existing mixed144 CRLF/7 LF-only lines.
Optimization adds only3 LF lines for the required import wrapping. No unrelated formatting,
dependency/configuration or global Ruff-rule change is present.

## Fresh execution evidence

All current results concern the frozen candidate and current runtime. Coordinator results
were inspected and are explicitly attributed. Independent subsets are reruns within the
broader lanes, not extra unique totals.

| Lane | Result / evidence |
|---|---|
| Independent mandatory repository-root Ruff |PASS, zero errors: `.\.venv\Scripts\python.exe -m ruff check apps\backend scripts tests --no-cache`; `.runtime/pr95-r3-qg-ruff.log`. Configured backend-CWD Ruff check . --no-cache independently PASS too. |
| Independent backend mypy |PASS,127 source files under backend project configuration; `.runtime/pr95-r3-qg-mypy.log`. |
| Independent owning Dashboard/activity and new fixture tests |48 passed, exit0; `.runtime/pr95-r3-qg-backend.log`. |
| Independent performance/evidence guards |17 unittest tests passed, exit0; `.runtime/pr95-r3-qg-performance-corrected.log`. |
| Independent additional adverse probes |10 passed: reversed chronology across status/resolver/view combinations plus invalid start/completion at selected201; `.runtime/pr95-r3-qg-adverse.log`. The inspected existing scratch probe was freshly executed. |
| Independent guarded physical Mongo |1 owned suite,6 collected/6 passed,0 failures/errors/skips, exit0; `.runtime/pr95-r3-qg-physical.log`. |
| Independent Dashboard frontend |27 passed, exit0; `.runtime/pr95-r3-qg-ui.log`. |
| Independent actual configured browsers |2 passed, exit0: PR95 Dashboard and PR89 Assistant through real HTTP/process lifecycle; `.runtime/pr95-r3-qg-browser.log`. |
| Independent static/security checks |All6 PASS: check_project_state, check_architecture, check_tooling_config, check_policy_authority, check_external_provider_readiness and check_secrets; direct tool execution. |
| Coordinator complete ordinary backend |2799 passed/164 skipped/3 warnings, exit0,1076.66s; **current** `.runtime/pr95-r3-lint-backend-final.log`. Full suite with explicit AnyIO/no plugin autoload and no physical URI. |
| Coordinator complete guarded physical Mongo |24 suites,158 collected/158 passed,0 failures/errors/skips, exit0; `.runtime/pr95-r3-physical-full.log`. |
| Coordinator broader focused backend |110 passed, exit0; `.runtime/pr95-r3-focused-backend.log`. |
| Coordinator full frontend |57 files/944 tests passed, exit0; `.runtime/pr95-r3-frontend-full.log`. |
| Coordinator frontend types/build/dependency integrity |Typecheck, Vite build and npm ls --all PASS; current typecheck/build/npm-ls logs. Optional platform fsevents absence is not an executed dependency. |
| Coordinator affected real browsers |9 passed; `.runtime/pr95-r3-browser.log`: Dashboard, Assistant, login/navigation, RM repair, Director scope, portfolio/activity paging, responsive shell and logout/role reset. Independent2 are contained in these9. |
| Coordinator changed fixture branch browser |1 additional sponsor-garden test passed20.4s; `.runtime/pr95-r3-fixture-browser.log`. Real guarded HTTP/browser with offline transports/generated disposable Mongo; cleanup VERIFIED. No real Sandbox/provider interoperability claim. |
| Coordinator API/contracts/assets |48 passed; `.runtime/pr95-r3-contract.log`. |
| Coordinator governance/security/tooling and performance |244 unittest tests passed, exit0; `.runtime/pr95-r3-governance.log`. Expected injected E2E-failure text belongs to passing runner-failure tests. |
| Coordinator script equivalence/runtime smoke |PASS: seven AST/imports,12 Decimal cases, benchmark2 modes, ownership and memory intake/load; `.runtime/pr95-r3-equivalence.log`; seven cold imports `.runtime/pr95-r3-cold-imports.log`. |
| Hygiene / preserved content |All18 frozen raw hashes and both deterministic digests independently PASS; index empty; git diff --check PASS; task-owned new Markdown/Python whitespace explicitly checked. |
| Clean committed pre-PR |NOT_EXECUTED at this gate: authorized next only after this exact PASS and scoped local commits. The coordinator must record its later result separately. |
| GitHub Actions |NOT_EXECUTED: historical billing-refused jobs are not CI PASS. No new push/CI/hosted-review action was requested in R3. |

Failing-first evidence is retained: exact configured-venv root Ruff15 errors before R3,
then zero errors after the minimal changes; the R2 red/green evidence remains in the
unchanged prior report and fresh P2 suites above pass. The independent initial unittest
invocation mistakenly selected nonexistent tests.test_performance_evidence_guards;
that invocation error is preserved in pr95-r3-qg-performance.log. Selecting the actual
existing modules produced17 passing tests; no implementation/test was changed for it.
An initial independent original-copy path typo likewise only affected scratch inspection.

Historical similarly named files, especially `.runtime/pr95-r3-backend.log` and
`.runtime/pr95-r3-static.log`, are **not** current final execution receipts and are not
used to claim these passes. The current unique backend receipt is named above.

## Architecture, contract, security and limitations

Mongo remains one scoped repository aggregation, with backend-authoritative team/case
visibility and safe inaccessible-case404. There is no route-to-Mongo bypass, schema
change/migration, new owner, silent persistence fallback, write/CAS/delete change or
provider fan-out. Relevant invalid retained data fails closed through existing sanitized
API errors. Timing remains canonical server-authored integer milliseconds and exact
resolver deduplication. No private timestamp/error/provider detail is projected.

API DTO/type/schema, endpoint/defaults, historical_trend/all-history compatibility,
explicit UI30d default, creator-versus-resolver definitions, Director/team/mine scope,
PR89 Assistant, authenticated transport, cancellation and session-scoped cache are
preserved. RBAC grants and authorization ownership are unchanged. Runtime changes remain
the five accepted R2 validations/presentation/interactions; the seven R3 scripts preserve
intended execution behavior. No sponsor business rule, mapping, external connector,
configuration, provider classification, dependency direction or application architecture
changes. Descriptive metrics remain project-defined, not sponsor SLA/compliance/productivity
or approval assertions.

Only generated allowlisted disposable databases were used through the existing runner.
No clm_poc connection/mutation/drop, dotenv read, confidential sponsor artefact, real
external provider request or evaluation overwrite is required or evidenced. The coordinator
verified/stopped/removed only the exact R3-owned loopback Mongo container after all physical
lanes; `.runtime/pr95-r3-mongo-cleanup.txt`. No volume/prune/shared-service action.

Genuine limits remain explicit:

- Ordinary backend164 skips comprise158 opt-in physical tests separately executed with
  zero skips, plus6 unavailable actual-native-Tesseract tests. Those6 OCR paths remain
  NOT_EXECUTED; mocked absence/cleanup is not OCR success. Classification's unchanged OCR
  path is not claimed as an actual OCR-browser acceptance.
- Three Pydantic serialization warnings originate in intentionally malformed Phase06
  provider conformance fixtures (trailing-LF/address/timestamp). They were not suppressed.
- Existing SSR useLayoutEffect and Vite chunk-over500kB warnings remain. No dependency
  advisory remediation or external security audit is claimed by npm ls.
- Prior R2 layout falsification found the same existing whole-document mobile overflow
  with old/new header markup. Current bounded table-scroll tests pass; this gate does
  not claim the entire Dashboard is free of inherited mobile overflow.
- Remote billing-refused CI remains NOT_EXECUTED. There is no fresh hosted Codex approval
  of these unpushed changes, and local PASS does not stand in for that future review.
- Real ACRA/GoldTier Live readiness, production sponsor questions and next development
  work remain outside this task; no provider classification is promoted.

## Required fixes, readiness and Git boundary

**Required fixes: none. Overall independent verdict: PASS.** All current combined R2/R3
implementation/review acceptance criteria are verified with the limits above. This clears
the prior inherited Ruff blocker; it does not rewrite the historical R2 FAIL.

Ready for the owner-authorized local commit/main-drift/clean committed pre-PR stage on
unchanged reviewed bytes. Final publication readiness must be stated by the coordinator
after that stage succeeds. Any changed implementation or invalidating main drift requires
a fresh independent assessment. Publication, hosted discussion/review changes, merge and
next-phase work remain unauthorized in R3.

At verdict: HEAD/tree remain the starting committed baseline;16 tracked source/test paths
are modified and the frozen prior report/new fixture test are untracked, plus this new
assigned report. Index is empty. The complete task inventory is18 frozen paths below
plus this assigned report,19 paths total. The reviewer wrote only this report as a tracked
candidate addition and allowed ignored scratch evidence; no implementation/test/config/
ordinary-document fix, stage, commit, fetch, push, merge, PR96/GitHub change, provider action
or lifecycle mutation was performed. Primary checkout/main, original teammate history,
registered unrelated worktrees and historical reports/evaluation remain preserved under
the coordinator's recorded checks.

## Frozen inventory

The path/hash map below binds the independently reviewed input. This newly authored
report is additional supporting content at
`.ai-pipeline/reports/PR95_R3_QUALITY_GATE.md`; its own hash is recorded by the coordinator
outside the self-referential report. R2 source/test8, authorized scripts7 and necessary
verification tests2 are intended/supporting; preserved R2 report1 and this new report1
are supporting. No unexpected path is present.

| Frozen path | Raw SHA256 |
|---|---|
| `.ai-pipeline/reports/PR95_R2_QUALITY_GATE.md` | `73029b67883331ab8b6fd5194560758f4c0a8936af1f8a7ac7cc8925e0f0b45e` |
| `apps/backend/app/persistence/mongo_case_store.py` | `1d6bfdf47bd59f13f94d2b1cd1e1457e034461b1ceec764e17820d8a95a9ea8a` |
| `apps/backend/app/services/dashboard.py` | `f90718f20c4ff95c4985b58bf1ebf486fa92c9d3c7eca8b50835f9fbb3c19ec3` |
| `apps/backend/tests/test_phase13_dashboard.py` | `cbc55bbaf2a0a72e8527162a4150f6c24e3ffb27261c2e4999f0195a304b7e77` |
| `apps/backend/tests/test_phase13_real_mongo.py` | `58f2392f589508d3f1da33b593371665eb9a6846d4120f7822b1195c9d9ffad7` |
| `apps/backend/tests/test_pr95_r3_script_fixtures.py` | `817a34f85e248a1f3e9fb0512e85ed721530cb416cfcb264e18f93bb59ea0476` |
| `apps/frontend/e2e/pr95-dashboard.e2e.ts` | `7b19b8c518a86abd66beccdca1b0962bcad4a5af5985e917383d2b1266043e9c` |
| `apps/frontend/src/Dashboard.test.tsx` | `9a62c49478b8e556c316944ed79eaa2c30ac8258fab0961e540103b0bbd1fa6e` |
| `apps/frontend/src/design-system.css` | `c778a5c5bb315fd6509622b0b4afa2f37280e1145a2b297845c17494816069cd` |
| `apps/frontend/src/pages/Dashboard.tsx` | `169fbbc1088035d4042377c3424d85c978f756e2c746b90e5a9e7c3a17d77028` |
| `scripts/benchmark_blocker_review.py` | `09262762f697c3cb2222ed6fce512f49562099fc81be17a6ec3d429ba58c0c09` |
| `scripts/generate_zero_touch_happy_path_documents.py` | `d72fc2d71a6ab363af97b4b52c7942c0a67b68572349e8d5eb376dee73d40f8c` |
| `scripts/performance_concurrency.py` | `34ed591b5a5fa3ac7e1f99b97ab14dda16e0b724beba88ecdd875952ef4060ad` |
| `scripts/performance_load.py` | `ae8837ea63dc7bd156167e79d1dbec86f9b4562e40fae28dcc2dbc2923e5aa98` |
| `scripts/performance_optimization.py` | `3f69d2d1c82ba66803d93645336fc8c021fcb5beb46f74932d36ecbd1778d909` |
| `scripts/sponsor_demo_browser_fixture.py` | `8e3cb2bdf20ca34496da2640c4cca087db578c7943bd01a840f582b7b9652a84` |
| `scripts/zero_touch_classification_browser_fixture.py` | `ba6c1e2061020f96fc32f32d4140d34f9df1049aa4584b3b89158824579d6bb7` |
| `tests/test_performance_review_remediation.py` | `0357c613f7b6ad2d2e04c9e799fb46614dca704e606a473a9061b12c9a236a85` |
