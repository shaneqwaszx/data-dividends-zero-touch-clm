# PR95 Dashboard v2 integration/remediation - independent Quality Gate

## Executive result

**FAIL** on the frozen candidate `aa8b9a4333f8858262fe5c15cdccd1e1272ace36`.
Three required correctness/truthfulness corrections remain: resolver work disappears in
My work, stage/total timing prose overstates retained measurements, and the selectable
category is labelled Live without supporting provider evidence. The implementation
writer must remediate these findings, then obtain a fresh independent gate. No fix was
made by this reviewer.

## Reviewed identity and boundary

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/pr95-dashboard-remediation-20261018/data-dividends-zero-touch-clm`.
- Branch: `codex/pr95-dashboard-remediation-20261018`.
- HEAD: `aa8b9a4333f8858262fe5c15cdccd1e1272ace36`.
- Tree: `8d9b87f9c713e69fdd5917eec2f7eb3874a8905e`.
- Published PR95 parent: `1c1fd9fbf1a68f79137d150ac8609cf811b10938`.
- Accepted main parent / origin/main / integration BASE_SHA:
  `cc10a2b626ef92d2dd44600d488c1f15cc4f04f8`.
- Feature/common ancestor: `12ba994b8128a4777e12fcc764bafc8f39b9292a`.
- Reviewed scope: all 32 paths differing from origin/main, including new planner,
  compatibility/cache/browser tests and contract/context updates. Complete raw-byte
  path/hash manifest: `.runtime/pr95-review-manifest.json`; sorted-JSON SHA256
  `72b9ebb109b3c75d3c6452b02079d86f07fa763d12ec1933363857065cfc1483`.
  Reviewer recomputed every path hash: 32 matched, zero missing/mismatched paths.
- Initially clean tracked/index state. The sole allowed tracked write is this report;
  no implementation, test, configuration or ordinary documentation was changed.

Authority read: AGENTS.md; mandatory dev_context union for BACKEND_DOMAIN, BACKEND_API,
FRONTEND_UI, FRONTEND_STATE_CACHE, PERSISTENCE, AUTH_RBAC_SECURITY and CI_TOOLING;
canonical workflow/architecture/state, assigned planner, access and persistence
contracts, relevant decisions/questions and accepted PR89 gate. Applied independent
fyp-quality-gate, persistence, frontend cache, security and POC-regression guidance.
No dotenv, private sponsor material, retained Mongo database or external provider was
used. Tool access and Python execution in the managed worktree required sandbox
escalation; this did not expand the review write boundary.

## Acceptance assessment

| Requirement | Assessment |
|---|---|
| Preserve Dashboard v2 and accepted main Assistant | Whole integration diff inspected. Main composition changes are bounded dashboard/activity wiring; Assistant source remains accepted main content. Coordinator frozen-tree Assistant 238 PASS and affected streaming browser PASS. |
| Additive API and legacy date/trend compatibility | Focused PASS. Omitted date_range remains all; browser explicitly requests 30d; original 30-day UTC historical_trend is computed before new created-date cohort. Shared types match backend additions. |
| Correct date cohorts, zero-touch and progress | Focused PASS. Exactly N Singapore calendar dates, inclusive start/exclusive next-day boundary; completed/no-intervention denominator; recorded stages/6 and completed=100. These are descriptive project metrics. |
| Creator projection/activity parity | Focused PASS; strict schema9/10 creator grammar, legacy absence unknown, schema1..8 reject later fields. Creator filter intersects authorization before activity paging; safe inaccessible/absent404 maintained. Physical execution recorded separately below. |
| Creator counts and actual resolver fixes | **FAIL F1** in My work despite team-view attribution/deduplication working. |
| Truthful timings and provider labels | **FAIL F2/F3**. |
| RBAC, privacy, cache lifecycle | No additional source defect found. HR denied; team scope/backend ownership preserved; user/team/view/date/creator keys and AbortSignal traced through existing session clear/remount,401 and deletion owners. |
| Broad/static/browser/regression verification | Coordinator exact-tree receipts inspected/reported below. Independent full backend deliberately stopped after required findings; complete final execution remains required after remediation. Nonzero weekly chart rendering needs a bounded actual-browser assertion before final acceptance. |

## Required findings

### F1 - P2: My work removes successful fixes on teammate-created cases

`apps/backend/app/services/dashboard.py:79` filters records to the actor's creator ID
before selecting automation IDs and calculating workload (`:144`). Therefore the
My work UI (`apps/frontend/src/pages/Dashboard.tsx:693`) cannot find the actor's fix
row when that actor resolved only a teammate's blockers.

Independent synthetic probe: one authorized TEAM_A case created by Ethan, one genuinely
RESOLVED blocker by Maya with two hours retained resolution elapsed time. Team view
returns Maya fixes=1; mine returns no Maya row, cases=0 and visible cases=0. The latter
case/list behavior is correct, but the resolver metric becomes an untrue zero.

The owner's explicit decision attributes successful resolutions to the actual resolver
even on another team member's case, limits metrics to existing authorized scope, and
separately preserves My work case-list filtering. Keep authorized/team/date-selected
resolver aggregation separate from creator-only case counts/lists. Mine must not expose
teammate case rows or other actors merely to repair the actor's own aggregate.

Required evidence: teammate-only resolver row in My work, actor-created case count/list
unchanged, date/team boundaries, RM/Director/HR, cross-team exclusion, deduplicated
resolved blockers versus drafts/open/cancelled, memory/Mongo restart parity, and UI
selection by actor ID.

### F2 - P2: Timing prose claims elapsed measurements that are not retained

`apps/frontend/src/pages/Dashboard.tsx:246` says stage averages include time to fix a
blocker. `_stage_timing` only averages `metrics.stage_durations_ms`. The owning
`zero_touch_orchestration.py:4109` records `_duration_ms(started_at, clock)` for the
successful processing attempt; DOCUMENT passes the clock immediately at completion
(`:3102`), and resumed OWNERSHIP starts a fresh processing timer (`:3113`). Those values
do not include the intervening review/fix wait. Independent synthetic probe retained a
2-hour blocker and 12ms recorded stage duration; dashboard correctly returned12ms,
contradicting its explanatory text.

The My work total timing text (`Dashboard.tsx:701`) says creation to Completed, but the
source total (`zero_touch_orchestration.py:3376`) is automation.started_at to
completed_at. Intake may precede start. The manager's mean-time label and domain
comments must not imply a stronger measurement either.

Correct labels/explanations to the existing recorded timing semantics. This task does
not authorize adding timing persistence, inventing wall-clock stage history or silently
changing formulas. Add tests using different created_at/started_at/completed_at and a
long retained blocker duration with a short processing duration; assert truthful copy
and unchanged numeric meaning.

### F3 - P2: Unsupported Live badge on the onboarding category

`apps/frontend/src/pages/Dashboard.tsx:205` unconditionally displays a green Live badge.
Current source/state classify registry/target as MOCK or PARTIAL sandbox, never Live;
there is no owner instruction approving this exact label. Although it appears to
contrast enabled and placeholder categories, users receive no qualification separating
feature availability from the project's defined Live evidence classification.

Use a neutral availability label such as Available/Enabled and assert that this picker
does not claim Live integration. Preserve actual backend provider-mode disclosures.
This is a user-visible truthfulness correction, not new provider work.

## Independent execution and adversarial evidence

- Focused backend command: explicit root/backend PYTHONPATH,
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, physical URI unset;
  `python -m pytest -o addopts= -p no:cacheprovider -q --tb=short`
  on test_phase13_dashboard.py, test_pr95_dashboard_compatibility.py,
  test_phase17_case_activity.py and test_phase18_case_portfolio.py:
  **54 PASS, 5.44s**.
- Independent synthetic attribution/timing probe: reproduced F1/F2 as above;
  no persistent fixture/source edits.
- Independent full backend began from configured apps/backend and stopped at12% once
  required remediation was established. It is **INTERRUPTED / NOT PASS**. An early
  async test failed because disabling all plugin autoload also disabled required AnyIO.
  Isolated `test_acra_modes.py::test_safe_discovery_reports_sandbox_without_scenarios_or_secrets`
  failed with the async-plugin diagnostic; rerunning with explicit `-p anyio` gives
  **1 PASS,0.86s**. This is invocation setup, not an established product regression.
  Final full run must preserve disabled unrelated plugin autoload but explicitly load
  AnyIO. Include the seeder integration test; coordinator observed a separate earlier
  timeout and an isolated current-tree PASS, not proof of a completed broad run.
- Guarded full physical runner against the assigned task-owned Mongo7 loopback service:
  **PASS:24 suites,156 collected,156 passed,0 failed,0 errors,0 skipped**.
  This independently executed the full current physical inventory, including actual
  memory/Mongo HTTP scopes, creator validation/legacy unknown and restarted workload/
  trend parity. Generated allowlisted disposable database safety and verified cleanup
  are owned by the existing harness; no connection string or raw failure log is retained
  here. The task-owned Mongo service remains under coordinator lifecycle ownership.
- Complete tracked diff whitespace check: PASS. All32 manifest hashes independently
  matched. No newly tracked secret, raw sponsor artefact or provider/document body was
  found in the inspected task delta. This report also receives an explicit Markdown
  whitespace check because it is not yet tracked.

Coordinator-supplied receipts on the same frozen tree, distinguished from independent
executions: full frontend **930 PASS /57 files** (`.runtime/pr95-final-frontend.log`),
frontend typecheck/build PASS (existing bundle warning), npm dependency tree PASS;
**9 actual browser tests PASS** (`.runtime/pr95-final-browser.log`) covering accepted
Assistant streaming, auth, RM/Director flows, cases/deletion, activity, responsive shell,
Dashboard scope/date/navigation/history/reload and logout/role reset; Assistant
**238 PASS**; contracts **44 PASS**; delivery **4 PASS**; governance test_check suites
**89 PASS**; pre-PR-check unit tests **64 PASS**; Ruff PASS, backend mypy **127 files**,
pip dependency check and project-state/architecture/tooling/policy/provider-readiness/
secret checks PASS. Private example archives are absent, so their validator lane is
**NOT VALIDATED**, never PASS; public contracts passed and connectors are unchanged.
These passing receipts do not waive the required findings or final full-backend run.

## Architecture, contract and security review

The existing DashboardService, CaseQueryService, portfolio adapters, auth/cache and
canonical envelope owners are retained. No new service/repository/provider/framework,
route-to-Mongo query, authorization owner, direct registry-to-target mapping, target
ledger bypass or runtime provider composition was introduced. Current main Assistant
behavior is preserved rather than replaced by old feature-branch content. No new ADR
is required for these bounded extensions.

New API fields/query selectors and portfolio creator projection are additive; schema10,
insert-only create/update-only mutation, CAS, deletion/no-resurrection and target
no-replay owners are unchanged. Projection validation now checks already-authorized
creator evidence; unknown legacy creator is not fabricated. Activity creator is not
event-actor attribution. The output stays within backend-authorized selected cases.
F1 requires narrower actor aggregation in mine output, without broader case visibility.
No secret/auth/TLS/provider-payload boundary was broadened, and no sponsor-controlled
mapping, endpoint, approval, SLA, compliance or productivity policy was added.

Scope effects of reviewed candidate: API/shared types **changed additively**; durable
schema/version/write contract **unchanged** (bounded read projections/validation changed);
connectors **unchanged**; configuration **unchanged**; descriptive dashboard calculation
rules **changed** under owner authority, sponsor business rules **unchanged**; mappings
**unchanged**; backend scope/cache inputs **extended**, existing RBAC/capability grants
**unchanged**; architecture owners/dependency direction **unchanged**; provider status
**unchanged**; dashboard/activity runtime behavior **changed**. F3 currently mislabels
availability despite unchanged provider classification.

## Readiness and next action

Local acceptance is blocked by F1-F3 and incomplete final broad evidence. Return to the
implementation writer for only these bounded corrections and meaningful regressions;
freeze the new content and request independent re-gate. No other source defect was
established in this first whole-diff review. Later sponsor production/auth/retention/
related-party/RFA dependencies remain outside PR95 and do not authorize new work.
Real ACRA/GoldTier Live readiness is not established. No next phase is authorized.

Final clean committed pre_pr_check is a separate integration/publication readiness gate
after accepted content and this report are committed by the coordinator. Its being
pending is not the reason for this product FAIL. Push, PR creation/replacement and PR
merge remain unauthorized; local commits/Git mutations belong solely to the coordinator.

## Git status

Review performed on the exact frozen commit/tree above, with a clean initial worktree.
Only this assigned report was written by the independent reviewer. No source fix, test
fix, staging, commit, push, branch switch, merge, PR action or next phase occurred.

Final closure: frozen32-path manifest independently rechecked unchanged after execution;
report-only untracked modification, empty index, and explicit report whitespace PASS.
Guarded physical process completed successfully before review closure.
