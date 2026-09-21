# Blocker-aware Attention Queue — implementation evidence

## Candidate identity and classification

- Task: the unnumbered Blocker-aware Attention Queue increment governed by
  `.ai-pipeline/001_planner/BLOCKER_AWARE_ATTENTION_QUEUE_EXECUTION.md`.
- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`.
- Branch: `feature/blocker-aware-attention-queue`.
- `BASE_SHA`, task-start HEAD, examined `origin/main`, and current source revision before
  publication: `c45ff77c7ff3472eb8867798c4c73d8692ca248b` plus the frozen working-tree
  candidate identified by the Git blob manifest below.
- Tested revision: the same frozen working-tree source, tests, and contract/demo docs;
  this report records evidence and the later quality-gate report is reviewer-owned.
- Change classes: `BACKEND_DOMAIN`, `BACKEND_API`, `FRONTEND_UI`,
  `FRONTEND_STATE_CACHE`, `AUTH_RBAC_SECURITY`, and `PERSISTENCE` for the bounded Mongo
  projected-read decoder. No stored schema, migration, index, provider, dependency,
  architecture-owner, or CI workflow change was made.

## Delivered behavior

The existing authorized case portfolio now exposes `active_exception_types`, a bounded,
unique sequence of existing `BusinessExceptionType` values derived only from retained
`OPEN` exception records in canonical enum-declaration order. The existing
`active_exception_count` still counts actual open records, including duplicates. A valid
row with no open exception returns `[]`; that statement does not imply health,
completion, approval, or lack of technical/recovery attention.

`GET /api/clm/zero-touch/cases` accepts one optional exact enum `attention_type`.
Authorization and Director/team selection precede the filter, omission preserves prior
results and ordering except for the additive field, and invalid values retain FastAPI's
422 behavior. Existing status, priority, team, jurisdiction, and browser search behavior
compose by intersection without a new endpoint, queue owner, or workflow.

The memory and Mongo portfolio implementations share the domain ordering helper. Mongo
adds only `automation.exceptions.exception_type` beside the existing status projection,
validates the status/type pair on every projected exception across supported envelope
versions, and still performs one authorized projected find with no full-envelope or
row-detail decode. The feature causes no workflow, provider, target, cache, or persistence
write.

The existing Cases view adds the typed **Open business exception type** control and
renders readable chips in **Open business exceptions**. It keeps the authenticated
case-list prefix while adding attention type to request/key identity and preserving the
existing fifth-position AbortSignal. All omits the query parameter. The known-empty copy
is **No open business exceptions recorded**. The unsupported queue-only **Assigned to**
column and its always-null view-model placeholder were removed after a tracked consumer
scan; team scope and unrelated onboarding assignment UI remain unchanged.

## Changed owners

- Backend domain/query/projection/API: `apps/backend/app/domain/case_management.py`,
  `services/case_portfolio_repository.py`, `services/case_query.py`,
  `persistence/mongo_case_store.py`, `api_models.py`, and `main.py`.
- Backend proof: new `test_attention_queue_backend.py` plus the Phase 14 performance,
  physical Mongo, and supported legacy-projection suites.
- Frontend contract/transport/cache/view: `types.ts`, `api.ts`, `caseQueries.ts`,
  `viewModels.ts`, `pages/CaseQueue.tsx`, and narrow `styles.css` additions.
- Frontend proof: new `AttentionQueue.test.tsx`, affected fixture suites, and the guarded
  authenticated browser journey.
- Documentation/evidence: the supplied brief, frozen plan, Phase 14 architecture and
  case-access contract updates, five-minute demo, this report, and the separately owned
  quality-gate report.

## Explicit non-changes and limits

- No new exception enum, blocker code, explanation, evidence, note, reviewer identity,
  assignment, arbitrary HTML, or URL surface is exposed.
- No stored envelope version, schema, migration, index, CAS, repository write, read
  repair, cache policy, local/session storage, or QueryClient is added.
- No role, capability, team scope, session, CSRF, safe-404, mutation, target ordering,
  replay, readiness, ownership, risk/SLA, escalation, notification, approval, or source
  precedence rule changes.
- No ACRA, IDP/OCR, ownership, GoldTier, PingFed, or Camunda classification changes.
  ACRA/Ownership/GoldTier remain Mock and IDP remains Local POC in the guarded journey;
  none is claimed Live.

## Review and remediation history

- Two Sol Medium implementation workers wrote disjoint backend and frontend owners after
  the coordinator froze the contract. The coordinator alone integrated E2E, docs,
  evidence, and Git responsibilities.
- The first browser run failed because a text locator matched both a filter option and a
  rendered chip. The test was narrowed to the Cases table. The second run then exposed a
  test-only assumption that the detail view repeats the queue chip; it was replaced with
  the existing evidence-workbench heading assertion. The unchanged product journey then
  passed 4/4. No timeout, network guard, production behavior, or assertion intent was
  weakened.
- The initial sandboxed frontend process attempt failed before collection with
  `spawn EPERM`; the identical focused suite passed through the supported approval path.
- The initial sandboxed pre-PR unit suite produced 42 environment errors because the
  sandbox denied temporary Git repository creation/cleanup. The identical suite passed
  42/42 through the supported approval path.
- The first GoldTier validation command could not import the pinned validator dependency.
  Installing the exact repository-pinned `scripts/requirements-contract-validation.txt`
  into the worktree venv changed no source or lockfile; its 5 tests passed and the absent
  private archive was truthfully reported as not validated.
- The physical Mongo container exited cleanly but Docker retained two task-created
  anonymous volumes. Creation-time/ownership inspection identified and removed only
  those exact volumes; no broad Docker cleanup was used.

## Verification evidence

| Layer | Result on final behavior |
|---|---|
| Context/runtime | `scripts/dev_context.py` PASS; Python 3.12.10, Node 22.23.2, npm 10.9.8; locked frontend tree present |
| Backend focused | 67 coordinator-focused tests passed; backend worker's related selection 113 passed |
| Backend static/full | Ruff PASS; mypy PASS on 94 source files; full pytest 1,060 passed, 23 explicit physical/environment skips, 5 dependency/Pydantic warnings |
| Frontend focused | 54 passed |
| Frontend full/static/build | 16 files and 239 tests passed; typecheck PASS; build PASS with 113 modules transformed; `npm ls --all` exit 0 with platform/feature optional dependencies absent |
| Contracts/delivery/POC | 44 contract tests, 4 delivery-asset tests, and 18 Phase 07/08 regression tests passed |
| Browser | 4 tests collected and 4/4 passed through the real local login/API/network guard; attention journey uses two feasible public synthetic cases and proves filter, clear, chips, native navigation, 480px scrolling, focus, and GET-only list effects |
| Physical Mongo | all 5 owned suites: 23 collected, 23 passed, 0 failed/errors/skipped; generated databases 0, task container 0, task anonymous volumes 0 remaining |
| Lifecycle | 23/23 passed in 319.797s; verified real start/stop/reset paths and left ports 8000/5173 plus runtime metadata clean |
| Governance/security | pre-PR unit tests 42/42; project-state/architecture/dev-context tests 39/39; project-state, architecture, tooling-config, and secret checks PASS; GoldTier validator tests 5/5 and absent private archive not read |

The frontend browser runner's legacy final line still says “2 authenticated local Mock
smoke tests” even though Playwright collected and passed four named tests; acceptance uses
the actual Playwright collection/result. Full backend skips are existing explicit
environment/physical opt-ins, while the required changed Mongo boundary ran separately
with zero skips. No private sponsor archive, `.env`, ambient Mongo URI, or `clm_poc`
database was read.

## AQ-01 through AQ-17 evidence map

- AQ-01/02: shared domain helper, strict model invariant, memory/Mongo fixtures for
  OPEN-only derivation, closed-history exclusion, duplicates, enum order, actual count,
  and empty list.
- AQ-03/04: service/API tests for exact enum/422/omission/order and composed filters,
  including OPEN-A with RESOLVED-B not matching B.
- AQ-05: authorization-before-filter tests, Director/team/unassigned coverage, and
  cross-team malformed-data exclusion.
- AQ-06/07: supported v1-v4 physical/fixture parity and fail-closed missing, unknown, and
  malformed status/type shapes; no v5 or read repair.
- AQ-08: one projected Mongo find, exact minimized fields, and no N+1/provider/business/
  target/persistence writes attributable to the list filter.
- AQ-09/10/11: typed request/key identity, preserved AbortSignal and list prefix,
  deferred-response actor/filter isolation, truthful cached-refresh states, and existing
  family invalidation/delete anti-resurrection coverage.
- AQ-12/13: explicit empty wording, preserved technical/recovery rows when unfiltered,
  exact public-field checks, and bounded assignment-placeholder retirement.
- AQ-14: final guarded browser 4/4 with two real synthetic exception types, filter clear,
  chips, existing detail navigation, keyboard focus, and narrow viewport proof.
- AQ-15: physical 5-suite 23/23 execution and exact disposable-resource cleanup.
- AQ-16: broad suites and governance/security checks above plus recorded failure history.
- AQ-17: pending fresh independent exact PASS and publication; those results belong to
  the reviewer report and final receipt, not this implementation self-review.

## Frozen candidate Git blob manifest

These are canonical Git blob IDs from `git hash-object --path=<path> <path>` in stable
path order. Repository attributes and clean filters are applied. This report excludes
itself to avoid a self-referential hash; the independent reviewer owns and excludes its
later report.

```text
80c3a45878249b8301f9b3037546697ae56e1801  .ai-pipeline/001_planner/ATTENTION_QUEUE_PLAN.md
a0d3674b06d4e2acc8c1da692a17ec54f4b6990d  .ai-pipeline/001_planner/BLOCKER_AWARE_ATTENTION_QUEUE_EXECUTION.md
a6c13aef0d38e6c4ad45874d40a62ad743c41a7b  apps/backend/app/api_models.py
9da78648a31dfd3db43542052578fb0d22135dbd  apps/backend/app/domain/case_management.py
e23ab30e5d8db72787c2dfb3998d3178801ec2ec  apps/backend/app/main.py
ccd4af2069a7185d72d3f8c9373f8e437b016e28  apps/backend/app/persistence/mongo_case_store.py
2802d972f929f6fb737180255519043d93c03210  apps/backend/app/services/case_portfolio_repository.py
cbd95395be469de7ed67135808e40ac5924bc9ab  apps/backend/app/services/case_query.py
b8d89e6b50ad92faa868c65172a2b813aaa9e1cf  apps/backend/tests/test_attention_queue_backend.py
6b0fd5a66037bafb0d53b9431e617def379bffd0  apps/backend/tests/test_phase14_case_management_performance.py
ad4e68d5adbd8e21dfe0ae4fefeda56bbbb98ff4  apps/backend/tests/test_phase14_real_mongo.py
eaf819687c17d3737468b69aac55f00206408b03  apps/backend/tests/test_pre_phase12_workspace_multidoc.py
60fec81c1f98bbe3692392fd13a5d892c54cbf27  apps/frontend/e2e/authenticated-zero-touch.e2e.ts
becaa617f8ab49b13b66fcc93f9be4fff1135bfc  apps/frontend/src/api.ts
43e7d02baa124e395f9d79aa90d5b74f35e596a5  apps/frontend/src/App.test.tsx
8f48d23d87c67067e3312cd237293371484ee5e9  apps/frontend/src/AttentionQueue.test.tsx
b170ca2115e28bddf7a5bec933b391aa164e9f54  apps/frontend/src/caseQueries.ts
7f9e2ee9c0784fca83231bf832c9f716f08e68e9  apps/frontend/src/pages/CaseQueue.tsx
9b040f085fbb9b6d29adc5889db9a9166939912c  apps/frontend/src/Phase13AuthPriority.test.tsx
117f401b07438cddc79dcbca7501e7fb4e70e822  apps/frontend/src/Phase14CaseManagementPerformance.test.tsx
70eaf7c393c505e815ad5f6dfce94e1b4bae83c9  apps/frontend/src/Phase15CNavigation.test.tsx
4813de3f1c2a8595a4f11ba8a176f3bcefeb47ba  apps/frontend/src/styles.css
da669dce542efc5fbfa75fba508b372e27da6a27  apps/frontend/src/types.ts
9c434de42405b71a1e60f61988002f00b74e83db  apps/frontend/src/UiV2Integration.test.tsx
b56fdb89149f5c0a7d71aa25e4a460414cad5ed1  apps/frontend/src/viewModels.ts
9bbe9724c78f7ce8260943343b7362a09de5bfe3  docs/architecture/PHASE_14_CASE_MANAGEMENT_PERFORMANCE.md
877b18e428219130fbed6cfc81cd141e374782f3  docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md
255c8733ea9ee662bf30b1bcd5f175edfd305523  docs/demo/ATTENTION_QUEUE_DEMO.md
```

## Next authorized action

Submit this frozen candidate to a fresh independent Sol High quality-gate reviewer.
Publication remains blocked until an exact independent `PASS`; human merge and any next
increment remain outside this implementation run.
