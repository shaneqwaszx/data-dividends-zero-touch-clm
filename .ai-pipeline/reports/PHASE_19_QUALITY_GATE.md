# Phase 19 — Factual Case Timing final independent quality gate

## 1. Executive Result

**PASS**

The exact frozen 52-path Phase 19 candidate satisfies P19-01 through P19-22 with
zero Critical, Important, or Minor findings. Fresh independent source/contract review,
deterministic timing falsification, full backend/frontend regression, MongoDB 7,
guarded authenticated Chromium, static analysis, governance, security, and candidate
hygiene all pass on the same unchanged reviewed content.

Phase 19 is ready for the separately authorized publication role on this exact frozen
identity. This verdict does not itself authorize a commit, push, pull request, merge,
or Phase 20 work.

## 2. Independence, scope, preflight, and reviewed identity

- Reviewer role: genuinely fresh independent whole-phase reviewer. This reviewer did
  not implement or remediate Phase 19.
- Sole repository write:
  `.ai-pipeline/reports/PHASE_19_QUALITY_GATE.md`.
- Worktree:
  `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`.
- Branch: `phase/19-factual-case-timing`.
- `BASE_SHA`, committed `HEAD`, local `origin/main`, and merge base:
  `b69fee6f475bfa32160a6d4acb9784edf3f4ff69`.
- Reviewed/tested source revision: that commit plus the frozen uncommitted 52-path
  candidate below. This report is excluded from the candidate identity.
- Candidate composition: 27 tracked modifications plus 25 task-owned untracked files;
  staged paths 0; unmerged paths 0.
- Applicable classes: `DOCS_ONLY`, `FRONTEND_UI`, `BACKEND_DOMAIN`, `BACKEND_API`,
  `PERSISTENCE` (read-only projection), and `CI_TOOLING`. The existing frontend
  state/cache, authorization, workflow, and provider surfaces were regression-checked
  but not changed.
- Available local capability: PowerShell/Git; Python 3.12.10 in the repository virtual
  environment; Node 22.23.2; npm 10.9.8; Playwright 1.56.1 with installed Chromium;
  Docker client/server 29.8.0; writable task worktree; and reviewer-owned loopback
  ports/resources. No external provider or app connector was used.
- Physical evidence used only the exact loopback-only `mongo:7` container
  `codex-p19-qg` on port 27029. The unrelated `safetrace` container was observed and
  not touched. Browser evidence used only ports 8799/4199.
- No `.env`, `clm_poc`, private/sponsor artefact, credential, raw provider payload,
  KYC/document body, or unrelated repository/container was read or modified.

Required context was read in authority order, including the complete user brief,
project state, architecture, workflow, relevant portfolio/timing contracts, decisions
and open questions, the complete quality-gate skill/template, Phase 19 plan and
implementation report, accepted Phase 18 evidence, all Phase 19 Aegis records, and the
current owning source/tests. `python scripts/dev_context.py` confirmed the assigned
branch/base and current Mock/Local/Partial/Dormant provider truth.

### Frozen identity

The independent manifest algorithm is: tracked modified paths plus expanded untracked
file paths, report exclusion, ordinal sort, then one UTF-8 record per path as
`<lowercase file-byte SHA-256><two spaces><path><LF>`. The SHA-256 of those records is:

`b777cb9d7d6e387f5d52aa33897784018c919bba3d2da63af7acc4e20aaf5a96`

The PowerShell-normalized UTF-8 `git diff --binary` identity for the 27 tracked paths is:

`00684657c2728f805321aef6c39ab44bf54dd5cc4615e70f80562523113d201d`

Both identities independently matched the implementer handoff before review and again
after all verification/cleanup immediately before this report. Complete reviewed paths:

```text
.ai-pipeline/001_planner/PHASE_19_PLAN.md
.ai-pipeline/reports/PHASE_19_IMPLEMENTATION.md
apps/backend/app/api_models.py
apps/backend/app/domain/case_management.py
apps/backend/app/main.py
apps/backend/app/persistence/mongo_case_store.py
apps/backend/app/services/case_portfolio_repository.py
apps/backend/app/services/case_query.py
apps/backend/tests/test_attention_queue_backend.py
apps/backend/tests/test_phase13_mongo_test_safety.py
apps/backend/tests/test_phase18_case_portfolio.py
apps/backend/tests/test_phase19_case_timing.py
apps/backend/tests/test_phase19_case_timing_real_mongo.py
apps/frontend/e2e/authenticated-zero-touch.e2e.ts
apps/frontend/src/App.test.tsx
apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx
apps/frontend/src/Phase15CNavigation.test.tsx
apps/frontend/src/Phase19Timing.test.tsx
apps/frontend/src/pages/CaseDetail.tsx
apps/frontend/src/pages/CaseQueue.tsx
apps/frontend/src/pages/CaseStatePanels.tsx
apps/frontend/src/shared.ts
apps/frontend/src/styles.css
apps/frontend/src/types.ts
apps/frontend/src/viewModels.ts
docs/ARCHITECTURE.md
docs/PROJECT_STATE.md
docs/aegis/BASELINE-GOVERNANCE.md
docs/aegis/INDEX.md
docs/aegis/README.md
docs/aegis/work/2026-09-21-phase-19-factual-case-timing/10-intent.md
docs/aegis/work/2026-09-21-phase-19-factual-case-timing/20-checkpoint.md
docs/aegis/work/2026-09-21-phase-19-factual-case-timing/90-evidence.md
docs/aegis/work/2026-09-21-phase-19-factual-case-timing/99-reflection.md
docs/aegis/work/2026-09-21-phase-19-factual-case-timing/baseline-read-set-hint.json
docs/aegis/work/2026-09-21-phase-19-factual-case-timing/baseline-usage-draft.json
docs/aegis/work/2026-09-21-phase-19-factual-case-timing/drift-check-draft.json
docs/aegis/work/2026-09-21-phase-19-factual-case-timing/evidence-bundle-draft-browser.json
docs/aegis/work/2026-09-21-phase-19-factual-case-timing/evidence-bundle-draft-physical.json
docs/aegis/work/2026-09-21-phase-19-factual-case-timing/evidence-bundle-draft-verification.json
docs/aegis/work/2026-09-21-phase-19-factual-case-timing/gate-input-pack.json
docs/aegis/work/2026-09-21-phase-19-factual-case-timing/impact-statement-draft.json
docs/aegis/work/2026-09-21-phase-19-factual-case-timing/proof-bundle.md
docs/aegis/work/2026-09-21-phase-19-factual-case-timing/resume-state-hint.json
docs/aegis/work/2026-09-21-phase-19-factual-case-timing/task-intent-draft.json
docs/aegis/work/2026-09-21-phase-19-factual-case-timing/todo-checkpoint-draft.json
docs/contracts/CASE_TIMING_PROFILE.md
docs/contracts/README.md
docs/test-plan/README.md
scripts/mongo_test_safety.py
scripts/run_physical_mongo_tests.py
tests/test_run_physical_mongo_tests.py
```

## 3. Phase Acceptance Checklist

| Criterion | Result | Independent evidence |
|---|---|---|
| P19-01 no SLA/risk/escalation judgement | PASS | Diff/source/UI inspection found only neutral factual labels and explicit non-goals. No threshold, severity colour, due date, overdue/breach state, risk effect, escalation, or policy decision was added. |
| P19-02 one UTC `observed_at` per portfolio response | PASS | `CaseQueryService` reads its injected/default UTC clock exactly once after the repository page read, projects every row from it, and emits it once at page level. Focused tests assert one clock call. |
| P19-03 active case elapsed | PASS | The helper uses `observed_at - created_at`; deterministic multi-day, near-zero, and active cases pass. |
| P19-04 completed stability | PASS | The helper uses `completed_at - created_at`, independent of later observations. Unit, API, physical, and browser evidence cover completed duration. |
| P19-05 time since last update | PASS | The helper uses `observed_at - updated_at`; exact-observation and positive examples pass. |
| P19-06 automation elapsed/null start | PASS | Absent `started_at` returns null; otherwise the end is exactly `completed_at` or `observed_at`. Reversed completion/start fails. |
| P19-07 no negative/misleading duration | PASS | UTC awareness, observation-relative future values, update/start before create, completion before create/start, boolean/negative retained totals, and every resulting negative delta fail closed rather than clamp. Portfolio projection maps invalid timing to fixed sanitized 503. |
| P19-08 memory/Mongo parity | PASS | Both repositories expose the same retained start/total scalars into the single helper. Fresh MongoDB 7 and memory tests reproduce the same active/completed facts. |
| P19-09 one bounded Mongo operation/no N+1 | PASS | The established page path still performs one scoped read-only aggregation. Only two bounded scalars were added to projection/validation; there is no row-detail/automation fan-out. |
| P19-10 no time-driven persistence write | PASS | The projection is calculated after a read. No update, repair, background writer, TTL, scheduler, or time-advance mutation was added; Mongo remains aggregation-only. |
| P19-11 legacy array compatibility | PASS | `GET /api/clm/zero-touch/cases` retains `ZeroTouchCaseListItemResponse` and its array shape with no `timing`; focused API and full backend suites pass. |
| P19-12 Phase 18 semantics unchanged | PASS | Current Phase 18/Attention tests pass; scope-first authorization, filters, literal search, priority/tie ordering, offset/lookahead, no-total response, and sanitized availability behavior remain. |
| P19-13 neutral factual frontend | PASS | Cases/detail display Case age/duration, Last updated, Automation elapsed, and recorded durations with neutral styling/copy; the focused frontend suite rejects policy-language additions. |
| P19-14 no browser-clock authority | PASS | Product source contains no `Date.now()` timing calculation. The browser formats server-authored integer milliseconds and displays returned `observed_at`; `Date.parse` appears only in guarded test comparison. |
| P19-15 no new polling/scheduler | PASS | No timer, interval, query polling option, background refresh, or scheduler was added. Guarded browser observed no portfolio request growth during a no-action window and a new observation only after explicit reload. |
| P19-16 truthful stage-duration wording | PASS | Contract and UI say “Recorded automated-stage processing duration” and explicitly exclude human wait and complete stage residence. Existing metrics are not recomputed or relabelled as SLA/vendor latency. |
| P19-17 session/filter/page/deletion safety | PASS | Query-key/cache owners are unchanged. Full frontend, Phase 18, navigation, auth ordering, deletion, and guarded browser regressions pass with AbortSignal/session/page semantics intact. |
| P19-18 guarded authenticated browser | PASS | Fresh Chromium 6/6 proves active and completed timing, detail and stage copy, explicit refresh/new observation, no automatic request storm, search/filter/page/Open/deletion regressions, keyboard/narrow-screen behavior, and guarded loopback networking. |
| P19-19 physical MongoDB 7 | PASS | Fresh exact guarded runner: 8 suites, 28 collected, 28 passed, 0 failed/errors/skipped. Real timing projection, scoped corruption isolation, malformed retained timing failure, legacy projection, one-operation paging, and cleanup pass. |
| P19-20 Phase 18 context closeout | PASS | `PROJECT_STATE.md` now records accepted Phase 18 at `b69fee6f...`, preserves live-offset/no-total/no-snapshot/no-SLA limitations, and marks Phase 19 candidate/pending. |
| P19-21 provider/schema/RBAC/workflow/policy unchanged | PASS | No provider/connector/configuration, schema version/migration/index, capability/role, workflow transition, target ledger, mapping, dependency, or sponsor-policy change exists. Provider classifications remain truthful. |
| P19-22 fresh whole-phase exact PASS | PASS | This independent whole-phase review returns exact `PASS` on the unchanged frozen identity with zero findings. |

## 4. Contract and Integration Findings

No Critical, Important, or Minor finding.

The candidate implements one cohesive timing projection under the existing
case-management/query owner. Its formulas and failure rules agree across the brief,
plan, `CASE_TIMING_PROFILE.md`, architecture, source, API DTOs, and UI. The paged
portfolio extension is additive; the old array DTO is unchanged. Case detail uses the
same helper and one independent response observation, avoiding raw-timestamp arithmetic
in the browser.

Memory and Mongo retain equivalent source semantics. Mongo's projection and strict
candidate/decoder validation allow `started_at` and `total_duration_ms` to be absent or
null for compatible legacy reads while rejecting wrong/negative types. All other exact
container/key/type checks remain strict. Phase 18's physical schema-v1 row and current
schema-v4 rows pass; unit/complete persistence regression covers supported v1-v4 reads.
No schema bump, migration, read repair, collection, index, or persistence write is
introduced.

Provider truth remains unchanged: ACRA Mock by default, generic ACRA sandbox Partial,
BizFile Dormant, IDP Local/Mock, ownership Local, GoldTier Mock only, Mongo optional and
memory default. No open sponsor question is resolved. Q-016/Q-017/Q-018 and existing
provider/policy questions remain later production dependencies, not Phase 19 defects.

## 5. Tester and Adversarial Findings

No product defect was reproduced.

### Fresh commands and exact results

| Command/evidence | Result |
|---|---|
| `python scripts/dev_context.py` plus Git/status inventory | Correct branch/base/HEAD/origin-main; 27 tracked + 25 untracked candidate; staged 0. |
| Independent manifest and tracked binary-diff computation, before and after evidence | Exact `b777cb9d...aaf5a96` and `00684657...3d201d`; zero drift. |
| `.venv\Scripts\python.exe -m pytest apps/backend/tests/test_phase18_case_portfolio.py apps/backend/tests/test_phase19_case_timing.py apps/backend/tests/test_attention_queue_backend.py -q -p no:cacheprovider` | 40 passed. |
| From `apps/frontend`: `npm.cmd test -- --run src/Phase18CasePortfolio.test.tsx src/Phase19Timing.test.tsx` | 2 files, 16 passed. |
| `.venv\Scripts\python.exe -m pytest apps/backend/tests -q -o addopts= -p no:cacheprovider` | 1,134 collected: 1,106 passed, 28 explicit physical/environment skips, 0 failed/errors; 5 existing warnings. |
| From `apps/frontend`: `npm.cmd test -- --run` | 19 files, 262 passed; existing React test-environment warnings only. |
| `npm.cmd run typecheck`; `npm.cmd run build` | PASS; Vite transformed 113 modules. |
| `.venv\Scripts\python.exe -m ruff check apps/backend scripts tests` | PASS. |
| `.venv\Scripts\python.exe -m mypy apps/backend/app` | PASS; 94 source files. |
| `.venv\Scripts\python.exe -m unittest discover -s tests\contract -p "test_*.py"` | 44 passed. |
| Secret unit/direct scanner | 8 passed; direct `check_secrets.py` PASS. |
| Project-state/architecture/tooling direct checks | PASS / PASS / PASS. |
| Dev-context, project-state, architecture, tooling, pre-PR-checker, and physical-runner units on host | 107 passed. |
| Exact MongoDB 7 guarded runner | `SUITES=8; COLLECTED=28; PASSED=28; FAILED=0; ERRORS=0; SKIPPED=0`. |
| `.venv\Scripts\python.exe scripts\run_e2e.py --backend-port 8799 --frontend-port 4199 --timeout-seconds 300` | Guarded authenticated Chromium 6/6 passed in 18.8 s; harness PASS. |
| `git diff --check`; UTF-8/final-LF/conflict scan of all 52 paths; full trailing-whitespace scan of all 25 new files | PASS. Five whitespace-only CSS lines are unchanged in `HEAD`, not candidate additions. |

The 28 skips in the ordinary backend run are the deliberately opt-in physical variants;
they are not used as physical success. The separate guarded run executed all 28 physical
tests with zero skips.

Three non-successful setup attempts were classified separately from product evidence:

1. Sandboxed Vitest could not spawn installed `esbuild` (`EPERM`); unchanged host runs
   passed 16/16 focused and 262/262 full.
2. An exploratory root `pytest tests` invocation lacked the contract helper import path
   and stopped on two collection imports; the repository's canonical contract command
   passed 44/44.
3. Sandboxed governance units could not create/delete disposable Git/temp fixtures.
   Their exact workspace-local temporary directory was removed, and the unchanged host
   run passed 107/107. No temporary candidate path remained.

Physical cleanup was independently verified: generated allowlisted databases 0,
`codex-p19-qg` absent, and port 27029 free. Browser ports 8799/4199 were free after the
harness. `scripts/pre_pr_check.py` itself was not run because this required review
candidate is intentionally uncommitted/dirty; its checker unit suite passed, and the
publisher must run the direct checker on the clean committed tree.

## 6. Code and Architecture Review

No Critical, Important, or Minor finding.

- HTTP remains a thin projection over `CaseQueryService`; ordinary routes do not query
  Mongo or own timing business rules.
- `project_case_timing` is the single deterministic timing owner. It uses exact
  `timedelta` components and floors only sub-millisecond remainder; it does not clamp,
  synthesize, or infer timestamps.
- One page-level observation follows the repository read, so every row is comparable at
  the same instant and the query itself is not prolonged by per-row clock reads.
- Mongo remains one scope-first bounded read-only aggregation. No full-envelope decode,
  N+1 detail call, memory fallback, or writer exists in the timing path.
- Frontend formatting is one dependency-free owner over returned integers. Cache/query
  identity, mutation effects, auth lifecycle, and route identity remain established
  owners.
- Existing schema v4 and supported legacy reads remain; no ADR trigger or new canonical
  owner/dependency direction exists.
- Accepted limitations are explicit: observation-at-fetch, no live ticking, no
  current-stage/status age, no total/snapshot isolation, no analytics/history, and no
  SLA/risk/deadline interpretation.
- **PERSISTENCE CHANGE:** PROCEED on the exact reviewed candidate.

## 7. Security Review

No Critical, Important, or Minor finding.

- Backend authorization/team scope remains authoritative and precedes timing projection.
  Other-team corrupt rows remain isolated by the established scope-first Mongo pipeline.
- Additive browser data is limited to one observation timestamp and non-negative timing
  scalars already derivable from authorized retained case state. No raw provider/body,
  KYC/document content, credential, endpoint, cache key, or private exception detail is
  exposed.
- Invalid authorized portfolio timing uses fixed sanitized
  `CASE_PORTFOLIO_UNAVAILABLE`; invalid detail chronology uses fixed sanitized
  `CASE_TIMING_UNAVAILABLE`. No raw retained/persistence detail crosses the boundary.
- No browser authorization owner, persistent browser storage, unexpected network
  destination, external provider call, or secret/configuration surface was added.
- Secret scanning and guarded browser network policy pass.
- **INTEGRATION SECURITY:** PROCEED. **FRONTEND STATE/CACHE:** PROCEED.
  **POC REGRESSION:** PASS.

## 8. Required Fixes

None.

There is no current bug/blocker, stale required evidence, unresolved authority required
for the bounded factual read, or accepted minor correction. Production identity,
provider, retention, audit, SLA, risk, and workflow-policy questions remain explicitly
later dependencies rather than Phase 19 acceptance gaps.

## 9. Readiness

- Phase 19 acceptance: **PASS on the exact frozen 52-path candidate**.
- Publication readiness: **READY for the separately authorized publication role**, on
  condition that it first reproduces the candidate identity and changes no reviewed
  content.
- Commit/push/PR authorization: not granted by this gate.
- Pre-PR readiness: publisher must stage/commit only accepted paths, confirm a clean
  tree, fetch/assess current `origin/main`, and run `python scripts/pre_pr_check.py`.
  Semantic integration or reviewed-content drift requires affected reruns and fresh
  independent review.
- Merge readiness: human-only regardless of this verdict.
- Phase 20: not started and not authorized.
- Live ACRA readiness: **NOT READY and not claimed**.
- Real GoldTier/PingFed readiness: **NOT READY and not claimed**.
- Production SLA/risk/monitoring readiness: **NOT IMPLEMENTED and not claimed**.

## 10. Git Status and report-only statement

At the pre-report verdict freeze:

- branch: `phase/19-factual-case-timing`;
- `HEAD`, `BASE_SHA`, `origin/main`, and merge base:
  `b69fee6f475bfa32160a6d4acb9784edf3f4ff69`;
- reviewed candidate: 52 paths, exact manifest
  `b777cb9d7d6e387f5d52aa33897784018c919bba3d2da63af7acc4e20aaf5a96`;
- tracked binary diff:
  `00684657c2728f805321aef6c39ab44bf54dd5cc4615e70f80562523113d201d`;
- staged paths 0; unmerged paths 0; active merge none;
- exact physical/browser resources absent and their assigned ports free.

This report is the reviewer's only repository file write. No implementation, test,
configuration, contract, plan, Aegis record, tooling, dependency, or ordinary
documentation file was edited. No file was staged; no commit, push, pull request,
merge, branch switch, worktree change, external/Live provider call, unsafe database
action, publication, or next-phase work occurred.

**Final verdict: PASS — P19-01 through P19-22 are independently verified on the exact
unchanged frozen candidate with zero findings.**
