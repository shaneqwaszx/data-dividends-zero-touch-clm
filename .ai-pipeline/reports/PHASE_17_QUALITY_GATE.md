# Phase 17 — Case Activity & Audit Explorer independent re-quality gate

## 1. Executive Result

**PASS**

No current critical, high, medium, or minor finding remains on the exact frozen
34-path Phase 17 candidate. The earlier independent **FAIL** history is preserved:

1. The first gate found a High defect: a column labelled UTC rendered timestamps in
   Asia/Singapore time and discarded source microseconds. That defect was remediated and
   independently closed on this same frozen candidate.
2. The preceding re-gate retained **FAIL** solely because mandatory physical MongoDB 7
   evidence had not executed. It did not convert missing infrastructure into a pass.
3. The coordinator has now supplied a successful guarded physical run against the exact
   unchanged candidate: six owned suites, 24 collected, 24 passed, zero failures,
   errors, or skips, with generated-database and exact-container cleanup verified.

The physical evidence applies directly to the reviewed persistence implementation: the
guarded runner explicitly owns the new Phase 17 real-Mongo suite, that suite executes
`MongoCaseStore.list_activity` against MongoDB 7, and it exercises microsecond ordering,
page boundaries/lookahead, filter intersection, v1-v4 projected compatibility,
other-team corruption isolation, scoped corruption failure, and deletion behavior. The
reviewed runner, safety helper, suite, and persistence code are all part of the same
candidate digest reproduced before and after the supplied physical execution.

All A17-01 through A17-14 criteria are therefore satisfied for the frozen candidate.
Phase 17 is eligible for the separately assigned publication role, provided publication
first reproduces this exact candidate identity. This verdict does not authorize merge,
next-phase work, Live-provider claims, or sponsor-risk acceptance.

## 2. Reviewer independence, scope, and preflight

- Reviewer: one fresh independent Sol High quality-gate reviewer; no implementation,
  remediation, test, documentation, Git, Docker, or publication ownership was taken.
- Write boundary: read-only except this report at
  `.ai-pipeline/reports/PHASE_17_QUALITY_GATE.md`.
- Worktree:
  `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`.
- Branch: `phase/17-case-activity-audit-explorer`.
- `BASE_SHA`, current `HEAD`, local `origin/main`, and merge base:
  `1657a88a43e2fa8606e4f3d26f3bd05d16313d9e`.
- Change classes reviewed: `BACKEND_DOMAIN`, `BACKEND_API`,
  `AUTH_RBAC_SECURITY`, `PERSISTENCE`, `FRONTEND_UI`,
  `FRONTEND_STATE_CACHE`, `DOCS_ONLY`, and the bounded `CI_TOOLING` change to the
  existing physical-suite inventory.
- Required context was read in constitution order: project state, architecture,
  development workflow, the case-activity query profile, decision/open-question
  authority, the quality-gate report template, persistence and frontend-cache skills,
  original assignment, plan, implementation record, preserved prior gate, complete
  candidate diff, owning source, tests, physical runner, and safety helper.
- `python scripts/dev_context.py` confirmed the assigned branch/base and current
  Mock/Local/Partial/Dormant provider truth.
- Available local runtimes observed: Python 3.12.10 from `.venv`, Node 22.23.2,
  npm 10.9.8, Docker CLI 29.8.0, PowerShell/Git, and the installed pinned project tree.
- No port, browser, database, or Docker resource was reserved or mutated by this
  reviewer. The coordinator's supplied physical execution used its own exact resource
  identity and was complete before this gate.

## 3. Exact reviewed identity and drift control

- Reviewed content: 34 candidate paths, excluding this self-referential report.
- Manifest algorithm: paths from `git status --porcelain=v1`, `Substring(3)`, report
  exclusion, PowerShell ordinal `Sort-Object`; each UTF-8 record is
  `<lowercase file-byte SHA-256><two spaces><path><LF>`, followed by a final LF.
- Independently reproduced candidate SHA-256:
  `2dba03bf4ee562661da59d86654cd336e0d824a73f5765e0d72a70990e776928`.
- Coordinator digest before physical execution:
  `2dba03bf4ee562661da59d86654cd336e0d824a73f5765e0d72a70990e776928`.
- Coordinator digest after physical execution and cleanup:
  `2dba03bf4ee562661da59d86654cd336e0d824a73f5765e0d72a70990e776928`.
- Independent digest immediately before this verdict:
  `2dba03bf4ee562661da59d86654cd336e0d824a73f5765e0d72a70990e776928`.
- Index: empty. No active Git operation was observed. No implementation/content drift
  occurred during review.

Complete reviewed path set:

1. `.ai-pipeline/001_planner/PHASE_17_CASE_ACTIVITY_SINGLE_SESSION_PROMPT.md`
2. `.ai-pipeline/001_planner/PHASE_17_PLAN.md`
3. `.ai-pipeline/reports/PHASE_17_IMPLEMENTATION.md`
4. `apps/backend/app/api_models.py`
5. `apps/backend/app/domain/case_management.py`
6. `apps/backend/app/main.py`
7. `apps/backend/app/persistence/mongo_case_store.py`
8. `apps/backend/app/persistence/repositories.py`
9. `apps/backend/app/services/authorization.py`
10. `apps/backend/app/services/case_portfolio_repository.py`
11. `apps/backend/app/services/case_query.py`
12. `apps/backend/tests/test_attention_queue_backend.py`
13. `apps/backend/tests/test_phase13_auth_rbac.py`
14. `apps/backend/tests/test_phase13_mongo_test_safety.py`
15. `apps/backend/tests/test_phase17_case_activity.py`
16. `apps/backend/tests/test_phase17_case_activity_real_mongo.py`
17. `apps/frontend/e2e/authenticated-zero-touch.e2e.ts`
18. `apps/frontend/src/api.ts`
19. `apps/frontend/src/App.tsx`
20. `apps/frontend/src/caseQueries.ts`
21. `apps/frontend/src/pages/AuditTrail.tsx`
22. `apps/frontend/src/Phase15CNavigation.test.tsx`
23. `apps/frontend/src/Phase17CaseActivity.test.tsx`
24. `apps/frontend/src/styles.css`
25. `apps/frontend/src/types.ts`
26. `apps/frontend/src/UiV2Integration.test.tsx`
27. `apps/frontend/src/viewModels.ts`
28. `docs/ARCHITECTURE.md`
29. `docs/contracts/CASE_ACTIVITY_QUERY_PROFILE.md`
30. `docs/demo/PHASE_17_ACTIVITY_DEMO.md`
31. `docs/PROJECT_STATE.md`
32. `scripts/mongo_test_safety.py`
33. `scripts/run_physical_mongo_tests.py`
34. `tests/test_run_physical_mongo_tests.py`

## 4. Findings and preserved history

### Current findings

No required fix remains. No critical, high, medium, minor, security, contract,
architecture, persistence, cache-isolation, accessibility, or documentation finding was
identified on the frozen content.

### Preserved prior High — UTC label contradicted rendered time — REMEDIATED

The first independent gate found that the activity table said `Timestamp (UTC)` while
using the shared Singapore-local formatter and truncating microseconds. The current
candidate uses a Phase 17-local canonical UTC projection, retains the source value in
`<time dateTime>`, preserves one-to-six fractional digits, and normalizes only an
equivalent `+00:00` suffix to `Z`. Fresh and supplied component/browser evidence covers
`.123456Z`. This finding remains closed.

### Preserved prior blocker — physical MongoDB 7 lane absent — CLOSED BY EVIDENCE

The preceding re-gate correctly issued **FAIL** because static/mock evidence could not
prove real PyMongo/MongoDB aggregation behavior. The coordinator subsequently executed
the unchanged guarded command on the unchanged frozen candidate and supplied:

- Docker Desktop 4.91.0 / Engine 29.8.0 / official `mongo:7`;
- exact task-owned container `phase17-mongo-db02220f7d92`;
- Docker-assigned free port bound only to `127.0.0.1`;
- URI held only in process-local `PHASE12_MONGO_URI`, never printed or persisted;
- `PHYSICAL_MONGO_RESULT=PASSED`;
- `SUITES=6`; `COLLECTED=24`; `PASSED=24`; `FAILED=0`; `ERRORS=0`; `SKIPPED=0`;
- suite-owned generated allowlisted database cleanup passed;
- exact task container cleanup passed and the container was absent afterward;
- exact task anonymous volumes were absent afterward;
- unrelated `safetrace` resources were untouched; and
- post-cleanup candidate digest remained exactly
  `2dba03bf4ee562661da59d86654cd336e0d824a73f5765e0d72a70990e776928`.

The reviewer did not rerun or mutate Docker because there was no contradictory evidence
reason. Applicability was independently established by inspecting the exact runner list,
allowlist/cleanup guard, all six owned suite registrations, the Phase 17 physical test,
and the `MongoCaseStore.list_activity` pipeline under review. A fresh collect-only check
independently confirmed the same six suites currently collect exactly 24 tests.

## 5. Phase acceptance checklist

| Criterion | Result | Direct evidence and assessment |
|---|---|---|
| A17-01 exact retained events and identity | PASS | Reads only `ZeroTouchAutomationRecord.events`; strict DTOs preserve case ID, source-local sequence, timestamp, event type, status, stage, outcome, code, and bounded message. No alternate event stream or invented ID/actor exists. |
| A17-02 authorization, safe 404, and team isolation | PASS | Existing `CASE_PORTFOLIO`, `CaseAccessPolicy`, and server-authored team scopes remain authoritative. Ordinary cross-team and absent selected cases share safe 404. Memory and Mongo scope before event inspection; malformed other-team data is isolated. HR remains denied. |
| A17-03 strict intersecting filters | PASS | UUID/enums/paging are typed and bounded; timezone-aware instants normalize to UTC; `from < to`; from-inclusive/to-exclusive. Action, stage, outcome, time, case, and team filters intersect before pagination. No caller expression, regex, sort, or authority reaches Mongo. |
| A17-04 deterministic memory/Mongo order and precision | PASS | Both adapters implement timestamp descending, canonical case UUID ascending, sequence descending. Fixed six-digit Mongo normalization retains microseconds. Physical MongoDB 7 evidence covers tie/boundary precision and memory-contract parity. |
| A17-05 bounded live paging truth | PASS | `limit + 1` lookahead determines `has_more`; no total is invented. Empty/one/full/lookahead/end paths, offset cap, Previous/Next, page-one refresh, and narrowing guidance are covered. Copy discloses live, non-snapshot pages. |
| A17-06 v1-v4 and malformed scoped data | PASS | Mongo validates projected schema/revision/identity/team/priority/event array, exact event keys, sequence, enums, UTC time, strings, and source identity. Physical evidence reads v1-v4, fails scoped corruption, and ignores corrupt other-team data without repair or rewrite. |
| A17-07 one page request/aggregation and bounded transfer | PASS | Legacy harness measures `2/26/101` HTTP requests for 1/25/100 cases versus one new page request. Browser observed one initial uncached request and no detail fan-out. Mongo source performs one aggregation, one bounded invalid signal, and at most `limit + 1` rows; real Mongo execution passed. |
| A17-08 read-only/no owner bypass | PASS | Activity reads make no workflow, provider, ownership, registry-cache, target, persistence mutation, read repair, fallback, `$out`, or `$merge`. Existing canonical owners and no-replay ledger are unchanged. |
| A17-09 cache, cancellation, invalidation, deletion | PASS | Query identity starts with user and includes case/team/action/stage/outcome/window/offset/limit. `AbortSignal` is forwarded; previous-key data is not presented as current. Relevant mutations invalidate activity; deletion cancels/removes the full user activity family before late publication. Existing auth/session clearing remains authoritative. |
| A17-10 real browser and responsive interaction | PASS | Guarded Chromium 5/5 covers login, one request/no fan-out, filters, 25-row paging, scoped route, case links, keyboard focus, 480 px internal scrolling, and exact six-digit UTC display. |
| A17-11 truthful limits and metadata | PASS | UI/contract/demo distinguish current metadata from event-time facts and disclose no actor, no complete audit, deletion removal, live pages, UTC, and no cross-case causal order. Export remains unavailable. |
| A17-12 accepted regressions preserved | PASS | Full backend/frontend, targeted POC, guarded browser, Windows lifecycle, contracts, security, route inventory, governance, and physical suites are green. No provider/workflow/readiness/reconciliation/ownership/target/navigation behavior was redefined. |
| A17-13 complete required matrix including physical Mongo | PASS | All non-physical lanes remain green on the same digest and the previously missing real MongoDB 7 lane now passes 24/24 with zero skips and verified cleanup. |
| A17-14 frozen independent PASS and truthful publication boundary | PASS | The 34-path identity is stable and independently reproduced; prior failures are preserved; this fresh gate is exact PASS. Separate publication must verify the same digest and remains distinct from merge authority. |

## 6. Contract and integration findings

- **Evidence authority:** the activity profile is explicitly project-defined POC
  behavior. It does not claim sponsor-approved retention, actor attribution,
  immutability, compliance audit, causal ordering, or exactly-once delivery.
- **Canonical ownership:** the existing zero-touch aggregate remains the event owner;
  `CaseQueryService` owns authorization and metadata resolution; the existing portfolio
  repository owns memory/Mongo reads. No event store, second authorization owner, or
  direct route-to-Mongo dependency was added.
- **Compatibility:** case-envelope schema remains v4 with strict read-only v1-v4
  projected compatibility. There is no schema v5, index, migration, writer, read repair,
  fallback, or persistence-owner change.
- **Provider status:** unchanged. ACRA is Mock by default, generic sandbox-shaped ACRA
  is Partial, BizFile is Dormant, IDP is Local/Mock, ownership is Local, GoldTier is
  Mock-only, Mongo is optional, and memory remains default. No Live claim is made.
- **Later sponsor dependencies:** Q-013/Q-014/Q-015/Q-016/Q-018 and the broader open
  questions still govern production privacy/retention/reviewer/source/RBAC/deployment
  policy. They do not block this accurately bounded retained-event POC view.
- **ADR:** not required. The change extends established owners and does not replace a
  canonical service, state owner, framework, dependency direction, persistence strategy,
  or external contract interpretation.

## 7. Tester and adversarial findings

### Fresh commands run by this reviewer

| Command/check | Result |
|---|---|
| `python scripts/dev_context.py` | PASS; branch/base/HEAD/status/provider truth confirmed. |
| Declared 34-path manifest computation | PASS; digest reproduced as `2dba03bf...928` before review and immediately before verdict. |
| Focused Phase 17/runner/safety pytest command | First sandbox run: 31 passed and 5 temporary-directory permission errors; unchanged approved host rerun: **36 passed**, 2 deprecation warnings, 0 failures. The first result was infrastructure-only, not hidden. |
| Six-suite physical collect-only inventory | PASS; exactly **24 tests collected** from the same six runner-owned suites. No database was contacted. |
| Adversarial API probe combining Director `case_id` and a different `team_filter` | Existing globally authorized case returned an empty intersected page; an absent case returned safe 404. This is not an access leak because Director already has global case access; ordinary cross-team selected cases retain indistinguishable 404. |
| `check_project_state.py` | PASS. |
| `check_architecture.py` | PASS. |
| `check_tooling_config.py` | PASS. |
| `check_secrets.py` | PASS. |
| `git diff --check` | PASS; line-ending conversion notices only. |
| Full hygiene of eight task-owned new files | PASS for final newline, trailing whitespace, and conflict markers. |

### Supplied exact-candidate evidence inspected for applicability

- Full backend: 1071 passed, 24 explicit environment/physical skips, 0 failed from
  1095 collected before the separate physical run.
- Focused independent frontend/regression: 81/81 passed.
- Full frontend: 246/246 passed; typecheck, production build, and lint passed.
- Guarded Chromium: 5/5 passed.
- Contracts: 44/44; Phase 07 delivery assets: 4/4; governance: 39/39; pre-PR checker:
  42/42; secret scanner tests: 8/8.
- Project-state, architecture, tooling, and secret checks: PASS.
- Accepted POC regression subset: PASS.
- Windows lifecycle: 23/23, with owned processes stopped and required ports clear.
- Physical MongoDB 7: 24/24, zero failures/errors/skips, with database/container/volume
  cleanup and unchanged candidate digest.

The existing non-physical results were not blindly rerun because their applicability was
proved by the unchanged digest and direct source/test inspection. Fresh focused tests,
inventory, governance, hygiene, and adversarial checks supplemented that evidence.

## 8. Code and architecture review

- The backend path remains route -> `CaseQueryService` -> portfolio repository ->
  memory/Mongo adapter. Route code performs only parsing, service delegation, DTO
  projection, and safe error mapping.
- Memory validates every event in a scoped automation record before filtering and applies
  the shared deterministic ordering. Its scan cost remains linear in candidate records
  and retained events; no constant-time claim is made.
- Mongo matches server-authored visibility before candidate validation, projects only the
  query-relevant boundary, validates every projected scoped event, facets one bounded
  invalid signal and page rows, disables disk use, and applies a 5000 ms budget. Failures
  are sanitized; there is no memory fallback.
- Current priority/client scope are resolved as current context and clearly labelled;
  they are not rewritten as event-time facts.
- The frontend uses the existing authenticated transport, QueryClient, browser-location
  navigation, and case mutation effects. The old list-plus-N-detail fan-out and unused
  By/Loop placeholders are fully retired with no fallback or lingering consumer.
- Complexity is bounded to one additive query contract/read method/route/query family and
  the required UI. No new library, framework, cache owner, state owner, or compatibility
  layer was introduced.
- Accepted technical limits remain explicit: offset pages are not snapshots; scans are
  not constant-time; retained events are not a complete audit; deletion removes history;
  no actor/export/total/retention archive exists.

## 9. Security review

- Backend capability and case/team scope remain authoritative. Frontend controls do not
  grant access. HR is denied, team overrides are Director-only, and ordinary cross-team
  selected cases do not reveal existence.
- Request fields are typed/bounded. No raw sort, regular expression, SQL/Mongo fragment,
  free-text search, caller-supplied scope, or arbitrary projection enters persistence.
- Browser responses exclude source payloads, document bodies, evidence bodies, cache
  keys, endpoint references, target request/response bodies, tokens, hashes, notes, and
  invented actor identifiers.
- Bounded safe messages are rendered as React text. The hostile HTML fixture remains text
  and creates no executable element or unsafe sink.
- Session/user/team/filter cache identity, request cancellation, auth lifecycle clearing,
  mutation invalidation, and delete-before-remove ordering prevent cross-session leakage
  and stale deleted-row resurrection.
- The physical runner copies only an allowlisted system environment plus the process-local
  URI, disables ambient pytest options/plugins, prints only contained summary values, and
  never selects `clm_poc`. Generated database cleanup is allowlist-gated and absence-
  verified.
- No secret, raw KYC/provider payload, credential, Mongo URI, or confidential artefact was
  read into or written by this report.

## 10. Required Fixes

None.

The prior UTC code defect is remediated. The prior missing-infrastructure blocker is
closed by exact-candidate physical evidence; it did not require a further code change.
Open sponsor questions and production audit/retention/identity/provider work remain later
dependencies, not Phase 17 defects.

## 11. Readiness

- Phase 17 publication readiness: **READY for the separately assigned publication role
  on this exact digest**.
- Publication condition: first reproduce the 34-path digest
  `2dba03bf4ee562661da59d86654cd336e0d824a73f5765e0d72a70990e776928`;
  any implementation, test, contract, plan, demo, or ordinary documentation drift
  requires a fresh independent review.
- Next-phase readiness: Phase 17 itself has no remaining gate defect, but this verdict
  does not authorize starting another phase.
- PR/merge readiness: publication may perform only its separately authorized scoped
  staging/commit/fetch/integration/pre-PR/push/PR workflow. Human owners retain merge and
  residual-risk authority.
- Live ACRA and real GoldTier/PingFed readiness: **NOT READY and not claimed**.
- Production audit, retention, actor attribution, compliance, immutability, and
  Ready-for-Approval readiness: **NOT ESTABLISHED and outside Phase 17**.

## 12. Git Status and report-only statement

At verdict freeze:

- branch: `phase/17-case-activity-audit-explorer`;
- `HEAD`, base, merge base, and local `origin/main`:
  `1657a88a43e2fa8606e4f3d26f3bd05d16313d9e`;
- ahead/behind: `0 / 0`;
- staged files: none;
- active Git operation: none;
- candidate: 34 task paths plus this untracked report;
- reviewed candidate digest excluding this report:
  `2dba03bf4ee562661da59d86654cd336e0d824a73f5765e0d72a70990e776928`.

This report is the reviewer's only file write. No implementation, test, contract, plan,
demo, configuration, or ordinary documentation was edited. No file was staged; no
commit, push, PR, merge, branch switch, worktree, next phase, database mutation, or
Docker mutation occurred.

**Final verdict: PASS — prior UTC defect closed; mandatory physical MongoDB 7 evidence
now passes on the exact unchanged frozen candidate; no required fix remains.**
