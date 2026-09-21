# Phase 19 Factual Case Timing — Implementation Report

## Outcome and identity

Phase 19 is implemented in the uncommitted worktree candidate on
`phase/19-factual-case-timing`. The accepted base, current `HEAD`, and locally known
`origin/main` are all `b69fee6f475bfa32160a6d4acb9784edf3f4ff69`; the branch is
0 ahead and 0 behind that baseline. This report is implementer evidence, not an
independent quality-gate verdict. No file is staged, committed, pushed, published, or
merged.

The applicable change classes are `FRONTEND_UI`, `BACKEND_DOMAIN`, `BACKEND_API`,
`PERSISTENCE`, `CI_TOOLING`, plus the affected documentation. No external-provider,
authorization/RBAC, workflow-transition, target-ledger, durable schema-version, index,
or dependency change was made.

## Delivered contract

- One deterministic case-management helper receives validated retained timestamps and
  one backend-authored UTC `observed_at`. Integer milliseconds use exact timedelta
  components and floor sub-millisecond remainder; values are never clamped or inferred.
- Active case elapsed is `observed_at - created_at`; completed case elapsed is
  `completed_at - created_at` and remains stable.
- Time since last update is `observed_at - updated_at`.
- Automation elapsed is null without `started_at`; otherwise it is
  `(completed_at or observed_at) - started_at`.
- Recorded total duration is the existing `metrics.total_duration_ms`, not a replacement
  calculation. Existing `stage_durations_ms` remain recorded completed automated-stage
  processing durations, not full residence time, human wait, SLA, or vendor latency.
- Naive/non-UTC timestamps, future authorized timestamps, reversed supported chronology,
  negative/malformed retained totals, and any resulting negative duration fail closed.
  The portfolio uses its existing sanitized `CASE_PORTFOLIO_UNAVAILABLE` response;
  detail uses sanitized `CASE_TIMING_UNAVAILABLE`.
- The paged portfolio adds one top-level `observed_at` and nested row `timing`. The
  legacy `GET /api/clm/zero-touch/cases` array DTO remains byte-shape compatible and has
  no timing member. The existing query parameters, authorization-first filtering,
  search, ordering, offset paging, and no-total semantics are unchanged.
- Case Detail adds a backend-projected `timing` object with its single observation. The
  browser formats returned numbers only and does not calculate from `Date.now()`.
- Memory and Mongo expose the same retained `started_at` and total-duration scalar.
  Mongo keeps one bounded aggregation per page, performs no row-detail calls or writes,
  and supports v1-v4/legacy projections where the two newly selected optional scalars
  are absent. All other exact-key/type validation remains strict.
- The Cases and detail views use neutral labels: Case age/duration, Last updated,
  Automation elapsed, Recorded total automation duration, and the explicit stage metric
  qualification. They add no timer, polling interval, query key, cache owner, mutation,
  colour severity, or policy classification.

No SLA, service target, due date, overdue/breach state, escalation, notification,
ageing threshold, risk/approval effect, reviewer assignment, scheduler, TTL, workflow
timeout/action, provider call, or current-stage/status age was added.

## Owners and changed surfaces

- Domain/API: `apps/backend/app/domain/case_management.py`,
  `apps/backend/app/services/case_query.py`, `apps/backend/app/api_models.py`, and the
  thin projection/error mapping in `apps/backend/app/main.py`.
- Read models: `apps/backend/app/services/case_portfolio_repository.py` and
  `apps/backend/app/persistence/mongo_case_store.py`.
- Browser: `apps/frontend/src/types.ts`, `viewModels.ts`, `shared.ts`, the existing
  Cases/detail state-panel owners, and narrow neutral styles.
- Verification: focused backend/frontend tests, Phase 18/attention fixtures, guarded
  E2E, one Phase 19 physical suite, the p19 disposable-name allowlist, and dynamic runner
  inventory proof.
- Context/contracts: the compact planner, `CASE_TIMING_PROFILE.md`, contract index,
  architecture, project state, test-plan wording, and concise Aegis process records.

## Verification evidence

All results below apply to the current product/source candidate unless a limitation is
stated.

| Surface | Command/evidence | Result |
|---|---|---|
| Final focused backend | `.venv\Scripts\python.exe -m pytest apps/backend/tests/test_phase18_case_portfolio.py apps/backend/tests/test_phase19_case_timing.py apps/backend/tests/test_attention_queue_backend.py -q` | 40 passed |
| Final focused frontend | from `apps/frontend`: `npm.cmd test -- --run src/Phase18CasePortfolio.test.tsx src/Phase19Timing.test.tsx` | 2 files, 16 passed |
| Full backend | `.venv\Scripts\python.exe -m pytest apps/backend/tests -q` plus collection inventory | 1,134 collected: 1,106 passed, 28 explicit physical/environment skips, 0 failed/errors |
| Full frontend | from `apps/frontend`: `npm.cmd test -- --run` | 19 files, 262 passed |
| Frontend types/build | `npm.cmd run typecheck`; `npm.cmd run build` | PASS; build transformed 113 modules |
| Backend static checks | Ruff over `apps/backend`, `scripts`, and `tests`; strict mypy | PASS; mypy checked 94 source files |
| Contracts/security/tooling | contract unittest, secret unittest/direct scan, GoldTier validator, delivery assets, physical-runner units, governance units, direct project-state/architecture/tooling checks | 44, 8, 5, 4, 16, and 39 tests passed respectively; all direct checks PASS |
| Guarded browser | `.venv\Scripts\python.exe scripts/run_e2e.py --backend-port 8799 --frontend-port 4199` | 6/6 passed in 19.3s; active/completed/detail timing, truthful stage copy, search/navigation, 480px/accessibility baseline, stable no-action request count, and a strictly newer manual-reload observation proved |
| Physical MongoDB 7 | guarded `scripts/run_physical_mongo_tests.py` against the exact owned disposable Mongo 7 resource | `SUITES=8; COLLECTED=28; PASSED=28; FAILED=0; ERRORS=0; SKIPPED=0` |
| POC catalogue | full 1,134-test backend run, including every current accepted scenario test already subsumed by the Phase 18 591-test explicit selection | No catalogue change; terminal/call-stopping/replay/isolation/Mock-label invariants remain green |
| Pre-PR checker | `python scripts/pre_pr_check.py` | Expected non-publication FAIL only for the required unstaged/untracked implementation state; branch relationship and project/architecture/tooling checks PASS |

The full backend's 28 skips are the deliberately opt-in physical/environment variants;
they are not used as physical evidence. The separately guarded Mongo run executed every
physical test with zero skips. Existing FastAPI/httpx deprecation warnings and existing
React Router/layout/act warnings were observed; none is introduced by the timing path.
The Windows lifecycle harness was not required because no startup/process ownership
surface changed; the guarded browser did start and stop the exact owned application
processes on dedicated ports.

The Aegis helper generated the Phase 19 checkpoint, drift, evidence, reflection, and
proof-bundle records. Its workspace-wide `check` remains non-green only because
pre-existing Phase 13, 14.5, 16, and 18 work Markdown is absent from the generated
workspace index. Phase 19 did not rewrite those historical records or claim this
process-only validator as product evidence.

### Shared-resource cleanup

The physical run used only the exact Phase 19-owned Mongo 7 container/volume on port
27029 and generated allowlisted `clm_p19_*` databases. After execution, remaining
generated databases were 0, the owned container and volume were absent, and port 27029
was free. The unrelated `safetrace` container was present before/after and untouched.
The browser used only ports 8799/4199; both were free after the run. No `.env`,
`clm_poc`, sponsor artefact, credential, raw provider payload, or non-allowlisted
database was read or modified.

## Defects found and remediated

1. Initial focused frontend work exposed two test-only issues: policy-word scanning
   matched a negated contract sentence, and one cache notification assertion was async.
   Assertions were made semantic/deterministic; the final focused and full suites pass.
2. The first physical run was 25/28. Three Phase 18 cases showed that previously valid
   portfolio projections can omit the newly selected optional `started_at` and
   `total_duration_ms`. The decoder and Mongo candidate expression now permit absence
   only for those two optional scalars, preserve all other exact validation, and have a
   unit regression. The final physical run is 28/28.
3. The guarded-browser slice first found an ambiguous timing label and then a navigation
   cache response that was not a new network observation. The locator is scoped to the
   Operational timing region; the test explicitly reloads to acquire each response,
   proves no request growth during a bounded no-action window, accepts the harness's
   bounded 1–2 reload requests, and requires the later response's `observed_at` to be
   strictly newer. Final result is 6/6.
4. Broad suites found only stale test fixtures: one backend `SimpleNamespace` lacked the
   newly read optional metrics, and two frontend detail fixture builders lacked required
   timing. The fixtures were updated; backend 1,106/28 and frontend 262/262 then pass.
5. Sandbox-only child-process/temp-Git permission failures affected Vitest and two helper
   unit suites. Exact approved-host reruns passed (frontend results above; pre-PR helper
   42/42; governance 39/39). These were environment failures, not product failures.

## Self-review and security disposition

The diff was challenged against P19-01 through P19-21 for one-clock ownership, UTC,
future/reversed chronology, completed stability, null starts, cached observation copy,
one Mongo operation, cross-team corrupt-row containment, v1-v4 compatibility,
sanitized failures, cache/session/deletion behavior, stage wording, policy language,
polling, browser-clock ownership, and persistence writes. No unresolved product defect
was found after the remediations above.

Integration-security review found no active security defect in the changed boundary.
The projection exposes only existing safe timestamps, integer durations, status/stage,
and authorized identifiers; it adds no raw body, PII/KYC, provider/internal reference,
exception text, endpoint, credential, token, log, or browser authorization decision.
Existing safe 404/team scope and sanitized 503 behavior remain backend-owned. Provider
classifications remain ACRA Mock by default, IDP Local/Mock, ownership Local, GoldTier
Mock, and no PingFed/live target connectivity. Production authentication/integration
limitations and sponsor dependencies are unchanged.

## Handoff, limitations, and next action

- The implementation is deliberately uncommitted and unstaged, so no candidate commit
  or tree SHA exists. The exact review identity is the complete task-owned path set plus
  per-file SHA-256 and a deterministic combined diff/content SHA-256 frozen after this
  report; it is supplied in the implementer-to-reviewer handoff.
- `python scripts/pre_pr_check.py` cannot pass until publication is authorized and the
  reviewed files are committed. Its two failures are therefore expected at this stage,
  not waived publication evidence.
- No independent `PHASE_19_QUALITY_GATE.md` has been written by the implementer. The
  next authorized action is a genuinely fresh reviewer checking this exact frozen
  candidate and writing only that gate report. Publication requires exact independent
  `PASS`; repository-owner humans retain final merge authority.

Stop after Phase 19. Do not start Phase 20.
