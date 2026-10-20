# PR95 Dashboard v2 acceptance Quality Gate - round 3

## Outcome

**FAIL** on frozen commit `01bf8263015e4ac53f8013fa5c1133bf09113e12`.
F1-F4 are corrected in the inspected content, but three required corrections remain:
F5, the server observation precedes its input reads; F6, resolution milliseconds lose
precision through floating-point conversion; F7, the new completed-case physical fixture
violates the retained automation contract and prevents required Mongo parity proof.
The full backend also has an unresolved HTTP seeder response-body timeout. No passing
focused receipt or prior candidate result waives these failures.

This independent reviewer made no implementation, test, configuration or ordinary
documentation fix. This report is immutable evidence for this freeze. Remediation and
a fresh independent gate belong to separate assigned runs.

## Reviewed identity and authority

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/pr95-dashboard-remediation-20261018/data-dividends-zero-touch-clm`.
- Branch: `codex/pr95-dashboard-remediation-20261018`.
- Frozen HEAD: `01bf8263015e4ac53f8013fa5c1133bf09113e12`.
- Frozen tree: `e190fcb8048161bc5c792b69bcd037d7a0d7e071`.
- BASE_SHA, merge base and inspected origin/main:
  `cc10a2b626ef92d2dd44600d488c1f15cc4f04f8`.
- Published PR95 parent: `1c1fd9fbf1a68f79137d150ac8609cf811b10938`.
- Normal integration merge: `aa8b9a4333f8858262fe5c15cdccd1e1272ace36`.
- Feature common ancestor: `12ba994b8128a4777e12fcc764bafc8f39b9292a`.
- Complete reviewed set: 36 paths differing from origin/main. Independently recomputed
  every raw-byte SHA256 and the complete changed-path set: all 36 matched, no missing,
  added or mismatched reviewed paths. Manifest `.runtime/pr95-review-manifest-r3.json`
  raw UTF8 SHA256: `412327fea78b29ec623e3a82cf299c3cdd8dc562e37b3c7de7249a7bf8bbf52a`.
  Its encoding is sorted JSON with indent=2 and a final newline; a different JSON
  serialization is not the manifest-file identity.
- Initial tracked/index state clean. The only allowed tracked write is this report.

Read authority: AGENTS.md; canonical fyp-quality-gate and report template; deterministic
context union for BACKEND_DOMAIN, BACKEND_API, FRONTEND_UI, FRONTEND_STATE_CACHE,
PERSISTENCE, AUTH_RBAC_SECURITY and CI_TOOLING; workflow, architecture, project state,
coordination/integration protocol, active planner/remediation, both immutable prior FAILs,
current access/timing/persistence contracts, relevant decisions/open questions, role
instructions, accepted PR89 gate and POC regression catalogue. Applied persistence,
frontend-cache, security and POC-regression review guidance. Current source/contracts
remain authoritative over historical receipts.

Observed reviewer capabilities: escalated shell access to this authorized isolated
checkout, Python3.12.10/pytest8.4.2, actual guarded Mongo execution against the assigned
running mongo:7 service, and access to current coordinator logs. The coordinator owned
browser ports8775/4183 and all Git mutations; the reviewer owned physical execution on
loopback27027. No external provider, retained database, PR96 or protected sponsor
artifact was used. Standalone probes used the canonical ordinary-test bootstrap before
application construction. No credential/URI/raw payload was printed or retained in this
report. Source remained frozen throughout all executions.

## Acceptance assessment

| Requirement | Assessment |
|---|---|
| Preserve Dashboard v2 and accepted main Assistant | Whole 36-path delta inspected; Assistant implementation/client/streaming owners have no delta. Current frontend and real-browser receipts preserve Assistant, navigation and session behavior. |
| Additive API and legacy compatibility | PASS focused/source: omitted date range remains all-history, original historical_trend remains 30 zero-filled UTC days before the v2 cohort, browser explicitly initializes30d. |
| Selected cohort and descriptive metrics | Singapore half-open N-calendar-date selection, creator case counts/lists, completion/zero-intervention denominator and recorded stages/6 are preserved. F5 observation ordering and F6 precision remain required corrections. |
| F1 creator versus resolver attribution | Corrected: separate authorized/date cohort resolver aggregation; mine returns only actor row, including authorized teammate-case fixes, while creator lists/counts remain unchanged. Independent adverse probe passes deduplication and draft/open/cancelled/team/date exclusion. |
| F2 truthful timing prose | Corrected: stage samples describe processing attempts, excluding blocker wait; totals describe retained workflow-start-to-completion durations. No new timing history or formula. |
| F3 provider truth | Corrected to Available; no unsupported user-visible Live availability badge. Provider classifications remain unchanged. |
| F4 browser clock authority | Corrected: manager/mine display, sort and age filters consume returned case_elapsed_ms; canonical projection and one observation are reused for workload age. Current unit/browser clock-skew receipts pass. F5 independently exposes an additional server observation-order defect. |
| RBAC/security/cache lifecycle | Independent71 auth/RBAC tests pass. HR denial, exact team scope, Director filters, safe404, user/team/view/date/creator keys, AbortSignal,401/session clearing and deletion owners remain. No new grants or browser authorization. |
| Mongo creator/legacy/read parity | Creator projection and strict schema9/10 grammar/legacy unknown handling inspected. Both full physical executions fail155/156; serial diagnostics identify F7. Required completed-case parity is unverified, never PASS. |
| Broad verification | Current full backend fails one seeder test; current physical fails one new fixture. Frontend/browser/static/contracts/governance receipts pass as separately attributed below. No overall acceptance PASS. |

## Required findings

### F5 - P2: Observation taken before reads rejects legitimate updates and predates returned facts

`apps/backend/app/services/dashboard.py:77` captures data_as_of before list_cases at:82
and before automation.list_records at:119. Canonical Phase19 portfolio behavior takes
its observation after the repository read (`case_query.py:148-149`).

Independent deterministic interleaving probe: injected current server time begins at T;
the real DashboardService captures T. Its case-query read advances current server time
by1ms and returns a row legitimately updated at T+1ms. Dashboard raises
CaseTimingDataInvalidError; the existing route maps it to sanitized503. The exact same
retained row passes canonical project_case_timing at the actual post-read time T+1ms.
This models ordinary overlapping update/read requests, not corrupt future data.

A second probe advances time only during the later explicit automation read. A fully
revalidated RESOLVED blocker at T+1ms enters the actor's mine workload (one fix), while
response data_as_of remains T. The first portfolio read was old state; the second
retained automation read was valid new state. There were two existing repository reads.
Thus simply moving the observation between the two reads does not cover both inputs.

Required correction: obtain existing authorized case/automation inputs before the single
server observation, then use that observation consistently for cohort dates, legacy
trend, all case ages and workload ages; reuse the fetched automation input. Preserve
all authorization, creator/resolver and list bounds. No new owner or snapshot-isolation
claim is required. Do not clamp timestamps, discard valid updates, add sleeps/retries,
or weaken chronology validation.

Required proof: failing-first advancement during each input read; one clock call after
both; active/completed/workload parity; date boundaries anchored to the returned
observation; genuine malformed/future chronology still sanitized503; fresh physical,
full backend and independent review on corrected content.

### F6 - P3: Floating-point resolution conversion loses retained milliseconds

`dashboard.py:295-297` converts a timedelta through total_seconds()*1000 before int.
The same conversion occurs in delay-note selection at:494; _mean_ms also uses floating
point division for an integer-floor result.

Independent actual workload probe: one retained1001ms resolution returns
mean_fix_time_ms=1000. Two retained1001ms/3003ms resolutions return2001; exact expected
mean is2002. Attribution/counts remain correct. This is bounded descriptive metric
inaccuracy, not a sponsor SLA or staff-performance finding.

Required correction: retain exact integer-millisecond floor arithmetic in this existing
owner, including consistent resolution conversion and integer-floor mean semantics.
Prove1001/3003ms and fractional-millisecond truncation without rounding up or changing
the chosen descriptive formula, authorization, attribution or persistence.

### F7 - P2 verification blocker: New completed Mongo fixture is not a valid retained automation

The serial full physical diagnostic fails
`test_phase13_real_mongo.py::test_pr95_physical_workload_and_legacy_trend_match_memory_after_restart`
at:399, after adding the completed fixture at:389-397. Stack: DashboardService:119,
Mongo automation repository:515, MongoCaseStore.list:162, strict decode:578;
PersistenceDataInvalidError.

Independent database-free reproduction: the read-model `_record(COMPLETED)` helper
produces completed_stages=(). validate_automation_record rejects it with the fixed
reason `completed automation record is inconsistent`. The COMPLETED invariant requires
the full current ordered stage prefix (`domain/zero_touch.py:575-583`). An immediate
MongoCaseStore._encode(snapshot) then _decode(encoded) reproduces
PersistenceDataInvalidError. This is the decisive cause; COMPLETED validation itself
does not require started_at, whereas RUNNING validation does.

Required correction: construct a fully valid completed retained record in this physical
fixture, with the accepted ordered completed stages and meaningful retained timing/
metrics as appropriate. Preserve production strict decode, schema, status invariants,
and all completed-duration/memory-Mongo parity assertions. Do not weaken the decoder,
mark the test skipped, or replace actual Mongo evidence with mocks. Then rerun all24
physical suites with zero failures/errors/skips and verified cleanup.

## Independent execution and adverse evidence

Ordinary commands used explicit candidate root/backend PYTHONPATH,
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, explicit AnyIO, no pytest cache and no physical URI.

- `python -m pytest apps/backend/tests/test_phase13_dashboard.py apps/backend/tests/test_pr95_dashboard_compatibility.py apps/backend/tests/test_phase17_case_activity.py apps/backend/tests/test_phase18_case_portfolio.py apps/backend/tests/test_phase19_case_timing.py -o addopts= -p anyio -p no:cacheprovider -q --tb=short`:
  **74 PASS,5.11s**.
- Same options on `test_phase13_auth_rbac.py`: **71 PASS,24.85s**.
- Independent resolver scope/dedup/draft/open/cancelled probe: PASS. Five invalid/future
  chronology variants plus three persistence error classes each returned the exact safe
 503 DASHBOARD_UNAVAILABLE object, without private sentinel projection.
- Independent F5 advancing-read probes: REPRODUCED both case-read false future rejection
  and later automation fact after data_as_of. Independent F6 exact-ms workload probe:
  REPRODUCED. Independent F7 canonical validation/encode-decode probe: REPRODUCED.
- First full guarded physical command: `python scripts/run_physical_mongo_tests.py --timeout-seconds 1800`, with URI constructed internally for the task-owned loopback
  service, never printed/persisted: **156 collected,155 passed,1 failed,0 errors,0 skipped**,
  exit1. The standard wrapper suppressed its failing node identity; it is not invented.
- Serial full physical diagnostic, after the coordinator's full backend exited, reran
  the identical24-suite inventory/environment/database guards. An in-memory wrapper
  changed only traceback presentation from no to short and emitted whitelisted node ID,
  source locations and exception class from captured output. No test/assertion/source
  change: **156 collected,155 passed,1 failed,0 errors,0 skipped**, exit1; F7 above.
  No cleanup error occurred; existing per-test finally helpers validate generated
  allowlisted database names, drop only those databases and verify absence. No retained
  database or clm_poc was connected/tested/cleaned. Container lifecycle remains with
  coordinator; the reviewer did not stop/remove it.
- Complete changed-path diff whitespace: PASS. All36 raw hashes and HEAD/tree rechecked
  unchanged. Explicit new-report Markdown whitespace is checked at closure.

Probe setup errors were corrected without product edits: the first standalone probe
omitted ordinary-test auth bootstrap and failed before exercising the target; later
full-model validation required reconstruction of model_dump-excluded internal bindings.
Only corrected executions above supply behavioral evidence.

## Current coordinator receipts independently inspected

These are coordinator executions on this exact freeze, not reviewer reruns:

| Lane / command | Actual result and limitation |
|---|---|
| Full backend from apps/backend: `python -m pytest -o addopts= -p anyio -p no:cacheprovider -q -rs --tb=short` | **1 FAILED,2781 PASS,162 SKIPPED,3 warnings,1100.12s**,2944 collected, exit1. `.runtime/pr95-r3-backend.log`. |
| Seeder isolated rerun | **1 PASS,8.35s**, `.runtime/pr95-r3-seeder-isolated.log`; does not clear failed full invocation. |
| Frontend full Vitest | **57 files,933 PASS,13.00s**, `.runtime/pr95-r3-frontend.log`; existing React act warnings remain. |
| Actual guarded browser campaign | **9 PASS,42.1s**, `.runtime/pr95-r3-browser.log`; genuine synthetic Mock completion, positive Singapore weekly segment/no invented Australia,40-day JS clock skew, Assistant resources, RBAC/navigation/session reset, portfolio/deletion/activity and responsive shell. |
| Public contracts and delivery | **48 PASS,3.90s** (44+4), `.runtime/pr95-r3-contracts.log`. Private sponsor examples absent/unvalidated, not PASS. |
| Root governance/runner unittest | **220 PASS,93.478s**, `.runtime/pr95-r3-governance.log`; expected adverse E2E failure text occurs inside overall unittest OK. |
| Static/build/dependencies | Whole-backend Ruff PASS; mypy127files PASS; six project-state/architecture/tooling/policy/provider-readiness/secret checks PASS; pipcheck PASS; frontend typecheck/build and npm ls --all PASS. `.runtime/pr95-r3-static.log` and `pr95-r3-npm-tree.log`. Existing Vite>500kB bundle warning remains. |

The full backend failure is specifically
`test_phase13_demo_scripts.py::test_http_seeder_runs_twice_against_one_live_memory_backend`:
first seed, target-confirmation response, HttpSeedApi._request response.read(1_048_577)
raises TimeoutError. The traceback names demo_scripts.py:467/:372 and
scripts/seed_phase13_demo.py:181. Resource contention is a hypothesis, not proven cause;
no product-versus-environment attribution or timeout waiver is made. Keep this failed
run and obtain a complete current successful backend run after bounded remediation.

The162 ordinary skips are156 opt-in physical cases plus6 optional unchanged local OCR
cases when Tesseract is unavailable. They are not executed/PASS; the two physical runs
above execute all156 and fail one. Three expected Pydantic warnings arise in malicious
DTO conformance cases. Prior471fd62 full2780PASS and earlier physical156PASS belong to
other trees and supply historical context only.

## Architecture, security, integration and impact

The inspected delta extends existing DashboardService, CaseQueryService, portfolio
adapters, canonical timing, auth/QueryClient and view owners. No new owner/framework,
dependency direction, route-to-Mongo bypass, persistence/auth/Decimal engine, provider
composition or target-ledger bypass appears. No new ADR is required for these bounded
corrections. F5 is an ordering bug within the existing owner, not a justification for
new timing architecture.

Strict creator projections preserve legacy unknown evidence, reject later fields in
schemas1..8 and constrain activity creator filtering within authorization before paging.
Durable schema10, identity/revision CAS, insert-only create/update-only mutation,
deletion/no resurrection and restart/no replay owners remain unchanged. F7 must be
fixed in the invalid new fixture, not by relaxing these invariants.

Security review found no additional secret, raw sponsor/provider/document body, private
error, TLS/auth grant or browser-storage expansion in the complete task delta. Existing
safe404, session cancellation/clearing and mutation/deletion effects remain. Scanner
PASS is bounded pattern coverage, not a universal security guarantee.

POC catalogue/target owners are unchanged. Current browser execution genuinely reaches
Mock COMPLETED after explicit Review & Send. No current passing whole-backend/physical
catalogue result is claimed while those lanes fail. Required-stage call stopping,
uncertain-target no replay and false-completion protections must remain covered in the
fresh full regression. The catalogue was not changed.

| Surface | Effect |
|---|---|
| API/shared types | Additive dashboard fields/query inputs, creator activity selector and case_elapsed_ms changed. |
| Durable schema/write/CAS/index | Unchanged; bounded creator read projections/validation changed. |
| Connectors/mappings/config/dependencies | Unchanged. |
| Business rules | Owner-approved descriptive dashboard formulas changed; sponsor policy/rules unchanged. F6 corrects accuracy within that formula. |
| Auth/security | Existing grants/owners unchanged; scoped filter/cache identity extended; safe timing/persistence503 added. |
| Architecture/provider status | Existing owners/direction and Mock/Local/Partial/Dormant classifications unchanged. |
| Runtime | Dashboard metrics/cohorts/activity/presentation changed; F5/F6 remain defects and F7 blocks physical proof. |

Later sponsor production authentication, legal/control UBO, mapping, source precedence,
privacy/retention, related-party child lifecycle and RFA/Live authority remain outside
PR95. Nothing here establishes real ACRA/GoldTier Live readiness.

## Readiness and next authorized action

Local acceptance is blocked by F5-F7 and failed current broad evidence. Coordinator may
perform only the bounded corrections and meaningful failing-first regressions, preserve
all three immutable FAIL reports, freeze new content and request a fresh independent
gate at a new assigned report path. Rerun current physical/full backend serially and
all affected frontend/browser/static/contracts/governance evidence after final changes.
No next phase is authorized.

Clean committed pre_pr_check remains intentionally NOT_RUN in this review; it follows
exact independent PASS and the authorized report/source commit plus latest-main
assessment. The gate grants no push, PR replacement/publication or merge authority.
Coordinator-reported original PR95 run39051770323/attempt1/head1c1fd9f jobs did not start
due billing; that is unexecuted hosted CI, not this candidate's executed evidence.
Repository-owner humans merge PRs.

## Closure and complete reviewed file inventory

At closure the original HEAD/tree and all36 raw content hashes remain unchanged; the
index is empty and this report alone is a new nonignored path. Tracked diff whitespace
and explicit report whitespace pass. The reviewer staged/committed/pushed nothing,
made no branch/merge/PR/container-lifecycle mutation, and fixed no reviewed artifact.

```text
.ai-pipeline/001_planner/PR95_DASHBOARD_INTEGRATION_REMEDIATION.md
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
