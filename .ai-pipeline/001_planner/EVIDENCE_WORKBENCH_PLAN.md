# Evidence & Explainability Workbench — execution plan

## Goal

Add one coherent, read-only case evidence experience that lets an authorized reader
understand the retained registry binding, inspect the backend's existing Decimal
ownership paths, and explain the current automation/blocker/target state without adding
a new workflow, calculation, cache, authorization, persistence, or mutation owner.

## Architecture

Extend the existing `OnboardingCaseResponse` with one explicit minimized optional
projection of `RegistryEvidenceBinding`. Reuse the current case-detail, ownership,
readiness, exception, target-ledger, authentication, React Query, and route owners. New
frontend components are prop-only presentation units; `CaseDetail` remains their sole
integration point and the existing query owners remain unchanged.

## Tech stack

FastAPI/Pydantic/Python 3.12; React 18/TypeScript/Vite/TanStack Query; Vitest/jsdom;
Playwright Chromium; existing repository scripts and CI only. No dependency change.

## Baseline and authority refs

- `AGENTS.md`, `docs/PROJECT_STATE.md`, `docs/ARCHITECTURE.md`, and
  `docs/DEVELOPMENT_WORKFLOW.md`.
- `.ai-pipeline/001_planner/OVERNIGHT_EVIDENCE_WORKBENCH_BRIEF.md`.
- `docs/contracts/REGISTRY_CACHE_FRESHNESS_PROFILE.md`,
  `docs/contracts/OWNERSHIP_UBO_PROFILE.md`, `docs/contracts/CLM_READINESS_POLICY.md`,
  `docs/contracts/ZERO_TOUCH_AUTOMATION_POLICY.md`,
  `docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md`.
- `docs/decisions/ADR-002_REGISTRY_SNAPSHOT_CACHE.md`,
  `docs/decisions/DECISION_LOG.md`, and
  `docs/sponsor-questions/OPEN_QUESTIONS.md`.
- Current owner source/tests and accepted Phase 16 main-integration/login-diagnostic
  reports. Historical reports are supporting evidence only.

Baseline usage: all required refs above were read before this plan. No required ref is
missing. Current source and fetched `origin/main` are both
`6625835e6ca8b7e531c25b3078c3ff58ee4df843`; the Phase 16 release branch matches its
remote accepted head `4224936a9df90000a054149eccfbefe1da12d2c8`; PR #41 is merged at
the current main commit. Phase 17 is not reserved in the tracked roadmap/governance
inventory, so this task remains unnumbered as instructed.

## Compatibility boundary

- Existing response fields remain unchanged; the new case field is additive and nullable.
- `None`/absent binding means only unrecorded/unknown. It never proves disabled cache,
  miss, provider fetch, freshness, or present validity.
- Source timestamps remain exact UTC values. The retained expiry is described only as
  the fixed provisional Mock policy result at case use, never as a current ACRA or
  compliance validity decision.
- Ownership percentages, paths, calculations, threshold/comparator, classifications,
  issues, and relationship orientation remain backend-authored. No frontend arithmetic.
- Backend RBAC/team scope and safe 404 remain authoritative. No new endpoint, query,
  repository read, provider call, mutation, retry, or cache read/write is introduced.
- Existing document/reconciliation/recovery/priority/deletion controls remain the sole
  mutation owners. Target status remains ledger-authored and no replay is introduced.
- Mock/Local/Partial/Dormant truth, unresolved sponsor questions, offline Camunda, and
  historical lifecycle uncertainty remain explicit.

## TDD route

- Mode: off.
- Decision: skipped.
- Strict authority: not applicable; neither the user nor repository requested strict TDD.
- Strict signals: additive public projection and cross-stack consumer compatibility.
- Light eligibility: not used because the task is multi-owner and behavior-bearing.
- TDD-fit exception: none.
- Test posture: minimum implementation plus focused post-change contract/component
  regressions, then the required broad affected checks and guarded browser journey.
- Verification: commands are listed per batch and in the integrated gate below.

## Requirement-ready and change-necessity check

The submitted brief defines the goals, EW-01 through EW-17, explicit non-goals,
publication authority, and stop conditions. Discovery found no material source conflict.
Decision: ready.

Code change is necessary because the public case DTO does not expose the already-retained
binding and the current case UI has only a static ownership table/raw readiness sidebar.
Documentation alone cannot provide case-specific evidence. The minimum code boundary is
`api_models.py`, the shared TypeScript type, three focused prop-only panels, and
`CaseDetail` composition/tests. Decision: code-change.

## Existing-owner and architecture integrity check

- Registry projection: reuse `OnboardingCaseResponse`; do not add an endpoint or read
  service.
- Ownership: reuse `OwnershipAnalysisResponse` and retained paths; do not reuse the old
  unbounded whole-graph helper or create a calculator/layout dependency.
- State explanation: reuse typed automation/readiness/exception/target values; do not
  parse timeline prose or create another rules engine.
- Frontend state: keep existing user/case query keys and GET owners; local selection is
  keyed/remounted by actor and case.
- Retirement: the static ownership/readiness block inside `CaseDetail` is replaced by
  the focused explorer/explanation panels. No canonical owner or supported API retires.
- ADR: not required; the work stays inside existing owners and invariants.

Architecture integrity verdict: proceed inside current owners. A fresh read-only
architecture/privacy reviewer must approve this concrete plan before production edits.

## Frozen public registry-binding contract

`api_models.py` will define:

```text
BrowserRegistryEvidenceBinding
  disposition: PROVIDER_FETCH | CACHE_HIT
  bound_to_case_at: datetime
  expires_at: datetime
  freshness_policy_id: MOCK_ACRA_FIXED_90D
  freshness_policy_version: 1
  freshness_duration_seconds: 7776000
  freshness_comparator: EVALUATION_NOW_LT_EXPIRES_AT
```

`OnboardingCaseResponse.registry_evidence_binding` is nullable and is constructed
explicitly from the domain binding. The projection fails closed unless the retained
binding environment is exactly `MOCK`. Provider/environment and original operation
retrieval timestamps remain sourced from the already-authorized `registry_acquisition`
projection rather than being duplicated from cache identity. The projection excludes
cache write time, freshness anchor, bundle-time duplication, cache ID/digest/key,
normalized identifier duplication, cache revision, contract version, dataset namespace,
policy fingerprint, source/endpoints/references, repository internals, and raw payloads.
The TypeScript interface mirrors these exact fields.

## UI interaction and bounded-layout specification

- Registry provenance receives the existing acquisition plus the minimized binding. It
  renders source classification and original operation retrieval timestamps only from
  `registry_acquisition`, then case-use time, disposition, retained policy/version/
  duration and expiry from the binding. Null renders “Not recorded for this case” with
  unknown semantics. It has no link, action, query hook, or freshness recalculation;
  existing evidence references remain plain text and are never repurposed as links,
  cache identity, or internal proof.
- Ownership explorer selects one candidate and one retained path. Candidate/path controls
  are keyboard buttons with selected state. Exact Decimal strings and backend wording are
  displayed unchanged.
- The selected-path visual uses only `candidate.paths[].edges`, keyed by `path_id`, in
  retained order and labels the domain orientation as “owned entity -> owner”/“is owned
  by”; it never reconstructs paths from the whole relationship collection. It renders at
  most 12 visible nodes, 11 edges, and one selected path. A longer path shows bounded
  prefix and suffix segments with an explicit hidden-edge boundary, so it cannot appear
  root-to-candidate complete. All retained permitted rows remain available through a
  keyboard-usable table/list with 20 rows per page.
- Repeated party display never creates another path count. The UI calls these retained
  paths, never a complete hierarchy. Any cycle, incomplete-entity, maximum-depth, or
  path-limit issue adds an explicit non-definitive/partial-view warning. Empty, pending,
  failed and limited outcomes never appear definitive.
- State explanation has this frozen source map: automation state from `summary.status`;
  current stage from `summary.current_stage`; stage readiness from
  `summary.clm.readiness.{registry,document,ownership,goldtier}.status`; blockers and
  warnings rendered verbatim/safely from their server arrays with no inferred cause or
  remedy; exception context from retained stage/code/explanation only; target state from
  ordered `summary.target_operations`; technical failure from the sanitized
  `summary.technical_failure`. Wording maps apply only to closed status/stage enums;
  unknown strings get a visible generic uncertainty fallback.
- Explicit evidence-focus controls use fixed code/stage-to-existing-section mappings for
  registry, document, reconciliation, ownership, and recovery. They never join records
  by name/timestamp or parse timeline prose. Missing evidence produces a visible
  unavailable note. Render/update never steals focus.
- Narrow screens keep scrollable tables and stacked panels; no arbitrary HTML/URLs,
  `dangerouslySetInnerHTML`, persistent browser storage, or unbounded graph animation.

## Task-start snapshot and resources

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`.
- Branch: `feature/evidence-explainability-workbench`.
- `BASE_SHA` / initial HEAD / fetched `origin/main`:
  `6625835e6ca8b7e531c25b3078c3ff58ee4df843`.
- Initial changes: only the owner-supplied governing brief is untracked; index and tracked
  tree are clean; no merge/rebase operation is active; no remote target branch exists.
- Available tools: local shell/filesystem, `apply_patch`, supported approval path,
  subagents, local Playwright Chromium, authenticated read-only GitHub CLI, and later
  authorized publication. Coordinator alone owns Git and shared integration files.
- Runtime evidence: worktree Python 3.12.10, `pip check` pass and imports from this
  worktree; Node 22.23.2/npm 10.9.8; installed package tree and Playwright 1.56.1 valid;
  Chromium executable present.
- Reserved ports: 8871 backend and 4281 frontend for guarded E2E. Ports 8000/5173 remain
  lifecycle-owned and were also free at startup. An owned loopback process was started,
  reached, stopped, and verified absent. No container/database is reserved because no
  persistence change makes physical Mongo required locally; hosted CI still owns its
  standard physical lane.

## Change classes and verification obligations

Applicable: `BACKEND_API`, `FRONTEND_UI`, `FRONTEND_STATE_CACHE` (case/session/local
analysis selection and stale-result containment), and `AUTH_RBAC_SECURITY` because the
additive projection changes the public redaction/trust boundary. Not applicable: backend
domain, persistence/schema, external provider, architecture refactor, auth-policy change,
dependency, or CI tooling.

Required evidence: focused backend projection tests; full backend pytest, Ruff, mypy,
contract/delivery checks; focused and full frontend tests, typecheck, build, E2E list;
guarded real-browser journey; lifecycle regression; secret/governance/architecture
checks; Markdown hygiene including untracked task files; implementer self-review; fresh
independent QG; clean committed-tree pre-PR; hosted CI after publication. Physical Mongo
is locally not applicable because no durable schema/repository/CAS/read compatibility
changes; remote standard CI status will still be reported.

## File ownership and execution batches

### Batch 1 — coordinator freezes shared interface

Files: this plan and `apps/frontend/src/types.ts` only.

Add the exact optional TypeScript binding interface above. Do not alter API transport,
query keys, auth, persistence, domain models, or dependencies. Verify with frontend
typecheck after the independent plan review.

### Batch 2 — bounded parallel implementation

Backend worker owns only:

- `apps/backend/app/api_models.py`;
- new `apps/backend/tests/test_evidence_workbench_registry_projection.py`.

Implement the explicit projection and tests for provider-fetch/cache-hit, null/legacy
unknown semantics, exact case-use/expiry/policy values, Mock-only fail-closed projection,
immutable case A after shared refresh, recursive forbidden-field/value exclusion across
direct/CLM/zero-touch case responses, safe cross-team/HR/absent behavior, and a detailed
case-summary GET negative-call test. The latter must install spies/fakes after fixture
creation and prove the read invokes no registry coordinator/provider, cache repository,
case save/write, IDP, ownership-analysis execution, or target connector execution/replay.
Baseline and permit the existing retained target-outcome/ledger read that already feeds
the response, while proving no ledger create/replace/delete/write is attributable to this
feature. Do not edit routes, services, domains, acquisition, auth, persistence,
ownership, target, or existing tests.

Frontend worker owns only:

- new `apps/frontend/src/pages/RegistryProvenancePanel.tsx`;
- new `apps/frontend/src/pages/RegistryProvenancePanel.test.tsx`;
- new `apps/frontend/src/pages/OwnershipPathExplorer.tsx`;
- new `apps/frontend/src/pages/OwnershipPathExplorer.test.tsx`;
- new `apps/frontend/src/pages/CaseStateExplanationPanel.tsx`;
- new `apps/frontend/src/pages/CaseStateExplanationPanel.test.tsx`.

Implement pure prop-driven panels against the frozen TypeScript contract. No edits to
`CaseDetail`, shared types/styles, queries, API, auth, navigation, or existing tests.

Focused verification:

```powershell
.\.venv\Scripts\python.exe -m pytest apps/backend/tests/test_evidence_workbench_registry_projection.py -q
npm.cmd --prefix apps\frontend test -- RegistryProvenancePanel OwnershipPathExplorer CaseStateExplanationPanel
```

### Batch 3 — coordinator integration and adversarial coverage

Files:

- `apps/frontend/src/pages/CaseDetail.tsx`;
- `apps/frontend/src/styles.css`;
- `apps/frontend/src/Phase15CNavigation.test.tsx` only if the existing route harness is
  the smallest honest case/session isolation proof;
- `apps/frontend/e2e/authenticated-zero-touch.e2e.ts`.

Mount the panels from the existing queries, replace the old static ownership/readiness
block, add stable focus targets, and key the explorer by actor, case, and ownership
analysis ID. The component also resets selection when the selected candidate/path
disappears. Add only presentation styles. Extend the existing guarded clean-fixture
browser journey rather than creating a new runner. Record the initial authorized request
baseline and distinguish existing polling/manual refresh. Assert panel exploration adds
no API request, per-node/path lookup, or mutation verb; a manual refresh remains exactly
the three existing authorized GETs and is never described as zero network activity.
Operate candidate/path/explanation controls and exercise a narrow viewport. Preserve all
existing E2E assertions. After production writers stop, a separate adversarial test
author may own only new
`apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx`; shared files remain coordinator
owned.

Focused verification:

```powershell
npm.cmd --prefix apps\frontend test -- CaseDetail Phase15CNavigation
npm.cmd --prefix apps\frontend run typecheck
npm.cmd --prefix apps\frontend run e2e:list
```

### Batch 4 — documentation and evidence

Files:

- `docs/contracts/REGISTRY_CACHE_FRESHNESS_PROFILE.md`;
- `docs/PROJECT_STATE.md`;
- `docs/ARCHITECTURE.md`;
- `docs/demo/EVIDENCE_WORKBENCH_DEMO.md`;
- `.ai-pipeline/reports/EVIDENCE_WORKBENCH_IMPLEMENTATION.md`.

Update the obsolete “no browser projection” statement to the exact minimized case-bound
projection; record the feature-branch scope without changing provider status or sponsor
questions; document the five-minute synthetic demo and a revision-indexed EW evidence
matrix. Preserve `verified_main_sha` as the examined baseline, not a guessed future SHA.

### Batch 5 — integrated verification and self-review

Run focused checks first, then serialize broad/heavy work:

```powershell
.\.venv\Scripts\python.exe -m ruff check apps/backend
.\.venv\Scripts\python.exe -m mypy apps/backend/app
.\.venv\Scripts\python.exe -m pytest apps/backend/tests -q
.\.venv\Scripts\python.exe -m unittest discover -s tests\contract -p "test_*.py"
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_phase_07_delivery_assets.py"
npm.cmd --prefix apps\frontend run typecheck
npm.cmd --prefix apps\frontend test
npm.cmd --prefix apps\frontend run build
npm.cmd --prefix apps\frontend run e2e:list
.\.venv\Scripts\python.exe scripts\run_e2e.py --backend-port 8871 --frontend-port 4281
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_demo_lifecycle_windows.py" -v
.\.venv\Scripts\python.exe scripts\check_project_state.py
.\.venv\Scripts\python.exe scripts\check_architecture.py
.\.venv\Scripts\python.exe scripts\check_tooling_config.py
.\.venv\Scripts\python.exe scripts\check_secrets.py
```

Use the current runner/PYTHONPATH conventions if a command's documented working
directory requires it. Record actual counts and first failures. One diagnostic rerun is
allowed only with a new controlled purpose; no unchanged full-suite rerun-until-green.
Inspect the complete diff against EW-01 through EW-17, scope, stale case/session/focus,
privacy, no-mutation, no-replay, and Mock/provisional claims. Check every task-owned
Markdown file explicitly for trailing whitespace, final newline, and conflict markers.

### Batch 6 — independent QG, bounded remediation, publication

Stop all writers and freeze a stable manifest/blob identity. A fresh Sol High reviewer
that did not design or implement the candidate follows `fyp-quality-gate` and writes only
`.ai-pipeline/reports/EVIDENCE_WORKBENCH_QUALITY_GATE.md`. Exact `PASS` is required.
FAIL/BLOCKED returns only concrete in-scope findings to an implementer, with at most two
remediation rounds and a fresh independent recheck.

After exact PASS, a separate publisher verifies reviewed identities, stages only the
planned paths, checks staged whitespace/secrets, commits, fetches latest main, and stops
on unclear drift/conflicts. When main is unchanged or safely integrated and reviewed,
run clean-tree `scripts/pre_pr_check.py`, complete the pre-PR checklist, push the feature
branch, create/update one PR against `main`, attach it to this task, and inspect both push
and pull-request CI. Do not merge, enable auto-merge, rebase, force-push, bypass checks,
or create report-only CI-status commits.

## Acceptance map

- EW-01/13: unchanged existing unit, routing, review/history/recovery, lifecycle, and E2E
  assertions.
- EW-02/03/04/16: focused minimized-projection and cache-isolation/negative tests.
- EW-05: existing backend authorization/safe-404 suites plus unchanged route owner.
- EW-06/11: pure component/call-count tests, route/service negative-call spies, and
  guarded browser baseline/delta request recording; failed refresh keeps last-confirmed/
  unknown wording and adds no retry. Manual refresh is three existing authorized GETs.
- EW-07/08: exact Decimal/path/classification/issue fixtures, selected-path visual,
  truncation disclosure, and pagination covering all retained permitted rows.
- EW-09: actor/case/analysis remount, selected-ID disappearance, and controlled stale-
  response navigation tests.
- EW-10: typed automation/readiness/target mappings, verbatim server-authored blocker/
  warning arrays, and unknown fallback tests.
- EW-12: keyboard/focus/unit and narrow-screen browser checks.
- EW-14: real login/local APIs/created case under the existing guarded browser runner.
- EW-15: no persistence change; existing backend and hosted five-suite physical lane
  provide parity evidence. No sixth suite.
- EW-17: current docs distinguish baseline, branch scope, offline Camunda, unresolved
  policy, and Mock/Local limits.

## Complexity, risks, drift, and stop conditions

`api_models.py`, `types.ts`, `CaseDetail.tsx`, shared CSS and the E2E file are hotspots.
Pressure is kept within budget by extracting three focused components and limiting shared
files to contract/composition/styles/tests. Do not revive the unbounded graph helper.

Stop the dependent lane if it requires an internal cache identity/reference, new
endpoint/query/repository owner, schema v5/read repair, cache policy change, provider
call, ownership calculation, timeline-prose inference, route-local auth, target replay,
new sponsor policy, new dependency, broad auth/lifecycle repair, secret/protected
artifact access, or unresolved latest-main intent conflict. Preserve the first new
lifecycle/login failure; it blocks acceptance and is not waived by earlier reports.

Drift decisions after each batch: continue only if intent, owner, compatibility,
retirement, test, and review locks still hold. A new owner/schema/authority need returns
to planning or blocks; a reproducible in-scope defect receives the smallest repair.

## Execution readiness view

- Intent lock: the three read-only explainability capabilities only.
- Scope fence: no live integration, Camunda, policy, schema, cache behavior, calculation,
  auth owner, workflow action, dependency, or sibling checkout change.
- Baseline lock: current HEAD/base/origin main `6625835e…` and source-first authority.
- Owner/contract constraints: explicit response projection; existing query/RBAC/domain/
  ledger owners; exact Decimal strings and retained evidence.
- Compatibility boundary: additive nullable field; all existing consumers and mutation
  owners remain valid; case/session identity fences local UI state.
- Retirement boundary: only the static ownership/readiness presentation inside current
  `CaseDetail` is superseded by the new focused panels.
- Task batches: shared interface; parallel backend/frontend; coordinator integration;
  docs/evidence; verification; independent QG; publisher.
- Test obligations: EW-01 through EW-17 with focused, broad, guarded browser, lifecycle,
  security/governance, independent review, pre-PR, and CI evidence.
- Review gates: fresh architecture/privacy plan check, implementer self-review, fresh
  independent exact PASS, separate unchanged-content publisher.
- Drift/rewind: preserve first failures and exact tested identity; no retry-until-green;
  two repair rounds maximum per underlying issue and QG remediation budget.
- Completion evidence: current/tested/reviewed blob identities, exact commands/results,
  clean task-owned process/port state, local/remote/PR/CI identity, and five-minute demo.
- Advisory boundary: this plan guides execution; it is not sponsor approval, a policy
  snapshot, an independent gate, or completion authority.

## Execution route

Subagent-driven, using the host's actual shared-checkout agents and the brief's explicit
parallel backend/frontend exception. Workers receive narrow context packets and
non-overlapping leases; coordinator owns shared files, Git, heavy suites, integration,
and publication coordination. Fallback is serialized coordinator implementation if an
agent becomes unavailable. No further conversational approval is required for the
routine actions already authorized by the brief.
