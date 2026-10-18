# PR95-R2 independent Quality Gate

## Outcome

**FAIL — BLOCKED.** All five assigned hosted P2 defects are independently
**VERIFIED FIXED** on the frozen uncommitted content. The mandatory repository-root
Ruff command fails with 15 diagnostics in seven unchanged scripts. This is an
inherited verification failure, not an R2 regression, but it cannot be reported PASS
or silently excluded from the documented required check. No implementation fix
remains identified within the five-finding delta.

The owner limited this round to those five findings and prohibited broad cleanup.
An owner decision on the separate lint blocker is required before exact independent
PASS, local commits, clean committed pre-PR verification or publication readiness.
The reviewer made no implementation, test, configuration, ordinary documentation,
Git, container-lifecycle or GitHub mutation.

## Reviewed identity and boundary

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/pr95-dashboard-remediation-20261018/data-dividends-zero-touch-clm`.
- Branch: `codex/pr95-dashboard-remediation-20261018`.
- Starting/current HEAD: `390f46ea08c877b7d86b85e9109fc8add3950d4a`.
- Committed HEAD tree: `976548b693e406241d34eab043fc68b6fb03d72f`.
  That tree is the published baseline, not a committed representation of the new fixes.
- Inspected accepted main/merge base: `4a280da473dcdbeb345ffdfa79aaa4c001e75f62`.
- Coordinator final fetch/remote observation: accepted main and published branch remain
  exactly the identities above; HEAD..origin/main is empty and both accepted main and
  original teammate ancestry checks succeed. This is coordinator-attributed Git evidence;
  the reviewer did not fetch or mutate refs.
- Original teammate commit: `1c1fd9fbf1a68f79137d150ac8609cf811b10938`.
- Published branch remains `ui-enhancement-v1` at the starting HEAD; no R2 push occurred.
- Reviewed implementation/test inventory: exactly the eight paths listed below,
  with raw-byte SHA256 values independently checked before and after execution.
- Frozen binary diff SHA256:
  `b71309295fa9fac69ab39777f9dff1220e482dbca46bc5275b3af2d1f2cd4dae`.
- Manifest: `.runtime/pr95-r2-frozen.json`. Index remained empty. This report is the
  sole permitted tracked-path write, additional to that frozen eight-path inventory.

Authority: the explicit PR95-R2 pasted owner request, root/backend/frontend AGENTS,
canonical development workflow and merge protocol, fyp-quality-gate/report template,
security and persistence skills, current architecture/provider state, owning source
and tests, case timing/activity/access/persistence contracts and the preceding
accepted PR95 integration gate. The previous local PASS is historical evidence and
was not substituted for this fresh review. Change classes are BACKEND_DOMAIN,
BACKEND_API, FRONTEND_UI, PERSISTENCE and AUTH_RBAC_SECURITY. The coordinator owns
all Git/source writes; this reviewer independently inspected and executed checks.

Capabilities used: escalated shell in the assigned worktree, Python3.12.10,
pytest8.4.2, Ruff0.16.2, Node22.23.3/npm10.9.9, installed Vitest/Playwright and the
existing guarded browser/physical runners. Heavy suites were serialized with the
coordinator. Only the coordinator-owned mongo:7 loopback service on27028 and newly
generated allowlisted disposable databases were used. No dotenv, protected Mongo
database, confidential sponsor artefact or external provider was accessed. No URI,
password or credential hash is reproduced in this report. After all physical runs,
the coordinator verified the exact task-owned container ID/name/image/loopback binding
and stopped/removed only that container, with no volume/prune/shared-service operation;
receipt `.runtime/pr95-r2-mongo-cleanup.txt`.

## Five-finding disposition

| Hosted finding | Independent disposition and evidence |
|---|---|
| [P2-01](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/95#discussion_r4306346317): creator filtering hid malformed authorized schema9/10 identity | VERIFIED FIXED. Mongo retains server-authored team/case selection before the facet; creator filtering now applies only to validated rows inside the rows facet. The invalid facet inspects the relevant authorized envelopes. Physical regressions reject malformed strings, booleans, numbers, arrays, objects and empty identity, retain valid nonmatching/null/legacy behavior, page deterministically, and exclude malformed other-team or unselected-case data. Existing strict creator grammar and schema versions are unchanged. |
| [P2-02](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/95#discussion_r4306346319): reversed resolved timestamps produced500 or negative delay | VERIFIED FIXED. Before either workload or delay-note projection, every relevant RESOLVED exception with a retained resolved_at passes the existing canonical timing validator. Reversed chronology raises CaseTimingDataInvalidError and the unchanged API boundary returns exactly sanitized503 DASHBOARD_UNAVAILABLE. No clamping, skipped-invalid evidence, new schema owner or Pydantic500 masking was introduced. Both resolver-present/absent and RUNNING/COMPLETED paths were executed. |
| [P2-03](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/95#discussion_r4306346322): invalid timing after200 rows entered aggregates | VERIFIED FIXED. Every selected authorized cohort record is validated before creator-view selection, aggregation and bounded response lists. Independent probes placed both invalid started_at and completed_at at position201; each failed closed. Valid201-case totals/history remain201 while scoped_cases remains capped200. Existing automation reads are reused; no provider or per-case persistence fan-out was added. |
| [P2-04](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/95#discussion_r4306346327): completed durations labelled Age | VERIFIED FIXED. Both mixed-status table headings and filters read Case age / duration. Accessible cells identify Case age for unfinished cases and Case duration for completed cases. Active, blocked, completed and missing legacy display states were rendered in team and mine views; exact returned values, zero/subsecond formatting, ordering and filtering remain intact. No API type or browser-clock calculation changed. |
| [P2-05](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/95#discussion_r4306346330): mouse-only sortable headers | VERIFIED FIXED. Shared SortableTh retains native th scope=col and contains a native type=button; aria-sort is present on exactly the active header and caret text is aria-hidden. Native Tab/Shift+Tab, Enter and Space were executed for every sortable header in pipeline timing, workload, all-cases and your-cases tables. Ascending/descending state toggles, visible focus, filters, navigation and existing presentation remain supported. |

All five exact hosted comment bodies and commit identities were independently read
through read-only GitHub API calls. The hosted threads were not resolved or dismissed;
fix verification here concerns the local frozen content only.

## Executed verification and red/green evidence

All results below were newly executed against the frozen R2 input unless explicitly
identified as the earlier failing-first baseline. Successful coordinator logs were
inspected and attributed; independent executions are labelled separately.

| Lane | Current evidence |
|---|---|
| Independent Dashboard/activity owning tests |41 passed, exit0; pytest test_phase13_dashboard.py plus test_phase17_case_activity.py; `.runtime/pr95-r2-qg-backend.log`. |
| Independent additional adverse probes |10 passed: reversed resolution across two statuses, present/absent resolver and team/mine; invalid started_at/completed_at at selected position201; `.runtime/pr95-r2-qg-adverse.log`. |
| Independent guarded physical Mongo |1 selected owned suite,6 collected/6 passed,0 failures/errors/skips, exit0; `.runtime/pr95_r2_physical.py --focused`; `.runtime/pr95-r2-qg-physical.log`. |
| Independent configured actual browsers |2 passed, exit0: PR95 Dashboard and PR89 Assistant, real HTTP/process lifecycle; `.runtime/pr95-r2-qg-browser.log`. PR95 executes native keyboard controls in all four tables, duration labels, date/view/age filtering and contained table scrolling. |
| Independent Dashboard frontend |27 passed in1 file, exit0; `npm test -- --run src/Dashboard.test.tsx`; `.runtime/pr95-r2-qg-ui.log`. |
| Coordinator broader focused backend |58 passed; `.runtime/pr95-r2-focused-backend.log`. |
| Coordinator complete ordinary backend |2792 passed/164 skipped/3 warnings, exit0,1076.49s; full backend pytest with explicit AnyIO, plugin autoload disabled, no physical URI and backend/root PYTHONPATH; `.runtime/pr95-r2-backend-full.log`.158 physical skips are executed separately below;6 native Tesseract skips remain unexecuted. Three inherited Pydantic serialization warnings arise from intentionally malformed Phase06 conformance fixtures. |
| Coordinator complete guarded physical Mongo |24 suites,158 collected/158 passed,0 failures/errors/skips, exit0; `.runtime/pr95-r2-physical-full.log`. |
| Coordinator full frontend |57 files/944 tests passed; `.runtime/pr95-r2-frontend-full.log`. |
| Frontend typecheck/build/dependency integrity |PASS: tsc, Vite build and npm ls --all. Playwright discovery138 selectors in25 files is inventory only, not138 executed browser tests. |
| Coordinator affected actual browsers |9 passed; Dashboard, Assistant, login/protected navigation, RM review, Director scope, portfolio/activity paging, responsive shell and logout/role resets; `.runtime/pr95-r2-browser.log`. The independent2 are reruns within this scope, not11 unique tests. |
| Backend configured Ruff/mypy |PASS: backend-CWD `python -m ruff check .`; strict mypy app,127 files. These passes do not clear the separate root-command failure. |
| Required root Ruff |FAIL: `python -m ruff check apps/backend scripts tests --no-cache`,15 diagnostics; `.runtime/pr95-r2-qg-ruff.log`. |
| Public API/contracts/assets |48 passed; `.runtime/pr95-r2-contract.log`. |
| Governance/security/runner unit tests |227 passed, exit0; `.runtime/pr95-r2-governance.log`. Expected injected runner-failure text occurs inside passing harness tests. |
| Independently repeated static/security checks |PASS: check_project_state, check_architecture, check_tooling_config, check_policy_authority, check_external_provider_readiness and check_secrets. |
| Diff/identity hygiene |PASS: exact eight-path raw hashes and frozen binary diff verified before/after independent execution; empty index; git diff --check. Final report whitespace is checked separately because it is untracked. |
| Clean committed pre-PR |NOT_EXECUTED: exact independent PASS prerequisite for local commits is not met. An intentionally dirty tree is not certified with the clean committed publication gate. |

Failing-first baseline was preserved and inspected: backend5 FAIL/2 PASS directly
reproduced four reversed-chronology permutations and the invalid201st case; physical
schema9/10 tests both failed with DID NOT RAISE before the Mongo correction; new
frontend4 FAIL established wrong labels/missing native buttons; actual browser failed
because the first sortable header exposed no button. Corrected owning and physical,
frontend and real-browser executions pass as attributed above. No failing assertion was
removed or weakened to obtain those passes.

The independent scratch adverse probe initially omitted the ordinary test bootstrap
and could not import the app without synthetic credential-hash setup. Adding the
existing conftest bootstrap to that scratch probe produced the10 passing executions;
no product/test/config content or real credentials were changed. An initial coordinator
contract invocation likewise needed the existing test-helper PYTHONPATH; its corrected
48-test execution is the current result.

## Required blocker and other observations

### R2-QG-01 — mandatory root Ruff check fails

Backend AGENTS Verification documents the repository-root command spanning
apps/backend, scripts and tests; the workflow matrix requires Ruff for the affected
backend/API/security/persistence classes. Independent execution yields these15 errors:

| Unchanged script | Diagnostics |
|---|---|
| scripts/benchmark_blocker_review.py |RUF100 at14:18,15:54,16:62 |
| scripts/generate_zero_touch_happy_path_documents.py |RUF100 at12:55 |
| scripts/performance_concurrency.py |RUF059 at45:54 |
| scripts/performance_load.py |FURB157 at302:29,303:29,306:83 |
| scripts/performance_optimization.py |BLE001 at132:16; RUF059 at308:48; I001 at417:9; FURB157 at446:65 |
| scripts/sponsor_demo_browser_fixture.py |I001 at3:1,101:21 |
| scripts/zero_touch_classification_browser_fixture.py |I001 at3:1 |

The reviewer independently compared identical rule/row/column/message tuples obtained
from current files with exact git-show blobs from both published390f46 and main4a280da.
All15 are inherited. Backend files use their tracked pyproject Ruff configuration;
the unchanged root scripts use Ruff defaults. The host-config explanation was
falsified and is not the cause. No checker, rule selection, CI setting or unrelated
script was changed. Narrow backend Ruff PASS is correctly retained as evidence but
cannot be substituted for this documented broader failed command. Required next step
is an owner decision authorizing a bounded separate resolution, followed by required
reruns and independent re-gate; this reviewer does not grant that scope.

Other limitations do not excuse this blocker:

- A coordinator layout challenge found whole-document scroll width686px at a390px
  viewport. In-page restoration of the original pre-R2 labels/header markup measured
  the identical686px. Thus no R2 overflow regression was established; affected table
  scroll boxes are contained and the actual keyboard/layout regression passes. This
  report does not claim the complete Dashboard is free of existing mobile overflow.
- Existing frontend SSR useLayoutEffect warnings and the Vite chunk-over500kB warning
  remain visible. Dependencies/locks were not changed; no dependency remediation is
  implied by this bounded five-finding review.
- Ordinary backend158 opt-in physical and6 unavailable-native-OCR skips are not PASS for
  those paths. Physical behavior is separately exercised by158 passing guarded tests.
- GitHub Actions is billing-blocked. No new R2 CI run or hosted review was requested,
  and no refused historical job is reported PASS; remote jobs remain NOT_EXECUTED.
- No external ACRA/GoldTier Live or sponsor-compliance/approval assertion is made.

## Architecture, contract and security assessment

The Mongo read remains one bounded aggregation through its existing repository owner.
Team/case selection still precedes validation and creator filtering; no out-of-scope
identity/event details enter the reply or error. Strict schema/version/identity rules,
legacy nullability, CAS/write/delete behavior and no-fallback configuration are intact.
The timing guard reuses canonical project_case_timing, with one server observation;
valid exact integer-duration arithmetic and successful resolver deduplication remain.

API shape, frontend shared types, endpoints, defaults, legacy historical_trend,
creator-versus-resolver semantics, authorized team/Director/mine filtering, inaccessible
case404, user/session-scoped transport/cache, backend capability ownership and PR89
Assistant behavior are preserved. Runtime changes are limited to fail-closed invalid
retained evidence and truthful accessible presentation/interactions. No business rule,
DTO/schema/version, connector, configuration, mapping, provider classification,
external trust boundary, target mutation rule or architecture owner was added/changed.
The source and tests remain tightly scoped; no broad formatting or dependency churn
was found. No secret/confidential artifact is added by the reviewed inventory.

## Readiness and Git status

Local R2 acceptance and separate-publication readiness are **BLOCKED** by R2-QG-01.
All five hosted P2 corrections are independently verified, but this overall gate is
FAIL, not PASS WITH MINOR FIXES and not publication-eligible. Local source changes
remain uncommitted because the owner explicitly conditioned commits on exact PASS.
The clean committed pre-PR/checklist and any publication are pending a future owner
decision and successful independent acceptance; none is claimed complete here.

The starting committed branch/main identities and original teammate ancestry remain
preserved. The primary main checkout and other registered worktrees are untouched.
Only the eight frozen source/test paths plus this assigned new report are task changes.
This reviewer performed no implementation fix, stage, commit, fetch, push, branch change,
merge, PR update, hosted thread resolution, CI/settings change or next-phase work.

## Frozen implementation/test inventory

| Frozen path | Raw SHA256 |
|---|---|
| `apps/backend/app/persistence/mongo_case_store.py` | `1d6bfdf47bd59f13f94d2b1cd1e1457e034461b1ceec764e17820d8a95a9ea8a` |
| `apps/backend/app/services/dashboard.py` | `f90718f20c4ff95c4985b58bf1ebf486fa92c9d3c7eca8b50835f9fbb3c19ec3` |
| `apps/backend/tests/test_phase13_dashboard.py` | `cbc55bbaf2a0a72e8527162a4150f6c24e3ffb27261c2e4999f0195a304b7e77` |
| `apps/backend/tests/test_phase13_real_mongo.py` | `58f2392f589508d3f1da33b593371665eb9a6846d4120f7822b1195c9d9ffad7` |
| `apps/frontend/e2e/pr95-dashboard.e2e.ts` | `7b19b8c518a86abd66beccdca1b0962bcad4a5af5985e917383d2b1266043e9c` |
| `apps/frontend/src/Dashboard.test.tsx` | `9a62c49478b8e556c316944ed79eaa2c30ac8258fab0961e540103b0bbd1fa6e` |
| `apps/frontend/src/design-system.css` | `c778a5c5bb315fd6509622b0b4afa2f37280e1145a2b297845c17494816069cd` |
| `apps/frontend/src/pages/Dashboard.tsx` | `169fbbc1088035d4042377c3424d85c978f756e2c746b90e5a9e7c3a17d77028` |

Supporting ninth changed path: `.ai-pipeline/reports/PR95_R2_QUALITY_GATE.md`
(this independently authored report; outside the implementation freeze).
