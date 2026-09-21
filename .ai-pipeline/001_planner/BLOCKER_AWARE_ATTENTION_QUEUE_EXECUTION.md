# Blocker-aware Attention Queue — bounded execution brief

## 0. Activation, scope decisions, and identity

This is an executable proposal, not evidence that the owner has already approved it. The owner activates the following authorization by submitting the accompanying approval/launcher prompt to Codex. No sponsor approval is implied.

Activated owner decisions:

1. Implement the unnumbered Blocker-aware Attention Queue as the next bounded product increment.
2. Expose and filter only existing exact `BusinessExceptionType` values derived from current `OPEN` exceptions. Do not add raw blocker codes, free-text explanations, evidence, notes, reviewer identities, or assignments to portfolio responses.
3. Remove the unsupported `Assigned to` Cases-queue column and its placeholder view-model field where consumer verification establishes safe removal. Do not remove working team-scope behavior or unrelated consumers.

Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`

Target branch: `feature/blocker-aware-attention-queue`

Accepted source / BASE_SHA: `c45ff77c7ff3472eb8867798c4c73d8692ca248b`

Released starting branch, before setup: `docs/evidence-workbench-closeout`

Released starting HEAD, before setup: `d9119b1e9c0615745e45d7420049420d890ce096`

Documented behavioral baseline: `99dd8eeea1c79bb4b9a9a592e6b47b4c038fdd4c`. This is distinct from BASE_SHA and is not stale merely because later documentation commits exist.

Repository: `shaneqwaszx/data-dividends-zero-touch-clm`

Expected brief path: `.ai-pipeline/001_planner/BLOCKER_AWARE_ATTENTION_QUEUE_EXECUTION.md`

This brief contains the necessary scope and execution handoff. Do not demand a separate missing chat attachment or restart general product discovery. Read current repository authority, contracts, source and tests to implement it accurately. Preserve existing roadmap numbering; do not declare Phase 17.

## 1. Goal, non-goals, and working example

An authorized operator can identify and filter cases by their retained open business-exception types before opening each case, then use the existing case-detail review/recovery and evidence workbench.

A case with three open exceptions of types `DOCUMENT_LOW_CONFIDENCE`, `DOCUMENT_LOW_CONFIDENCE`, and `OWNERSHIP_CYCLE` has an exception count of three and a deduplicated type list of two values. A resolved occurrence does not contribute to the list or count. These examples illustrate projection rules, not permission to create impossible workflow states in integration fixtures.

The view remains the existing Cases queue. Do not create a second workflow, queue service, or readiness/triage engine. Exception categories are not risk or urgency scores.

An empty type list means **no recorded open business exceptions**. It does not mean the case is healthy, complete, approved, or needs no attention. A technical failure or recovery state can require attention without an open business exception. Keep those statuses visible without inventing exception types.

No assignment, comments, return-for-rework mutation, due date, SLA, escalation, notification, export, audit redesign, risk calculation, new approval policy, source precedence, cache-policy change, provider integration, workflow mutation, URL fragment, or target replay. No new dependencies, vector/RAG/LLM service, Camunda runtime, persistence schema/migration/index, or scheduler.

## 2. Roles and orchestration

Recommended routing:

- Lead/coordinator: Sol High; Extra High is optional only if actually available and needed for a concrete contract/security ambiguity.
- Backend and frontend implementation: Sol Medium in distinct worker runs.
- Independent final cross-stack/security/persistence QG: fresh Sol High reviewer who did not implement the candidate.
- Publication: separate Medium role.

Use existing repository skills: phase execution, architecture change review where triggered, persistence schema/change procedure for the affected Mongo read boundary, frontend state-cache change, integration-security review, POC regression, independent quality gate, and integration-safe development. Do not create another process framework or edit AGENTS/skills to evade a restriction.

At most two implementation workers run concurrently after the coordinator freezes the interface. They may share this worktree; they do not have implicit filesystem isolation. Assign exact disjoint write ownership. One coordinator owns Git, reports, cross-lane integration and scheduling. Freeze writers before integrated or heavyweight tests. A reviewer never repairs its own findings or issues acceptance for its own implementation.

If subagents are unavailable, perform implementation sequentially. Independent QG remains required; stop publication rather than simulate a fresh reviewer. Report actual models/tools used, not intended ones.

Use an approximate six-to-eight-hour ceiling only as an execution budget, not a guaranteed outcome. Stop earlier when complete. Preserve a compact usable handoff if the budget ends. Do not start unrelated work to occupy the time.

## 3. Preflight and branch setup

Read AGENTS in its prescribed context order. Verify root, local branch/HEAD, tracked/untracked inventory, index, no active Git operation, and no competing writer. The supplied brief is an expected task-owned untracked file after it has been saved.

Fetch and verify origin/main, PR #44 merge, and the last normal main push CI. BASE_SHA must match accepted current main before starting. If it changed, inspect drift; do not silently use a stale base or overwrite work.

The owner explicitly authorizes creating the target branch directly from verified BASE_SHA in this same clean/released worktree, without checking out the stale control-repository main. If the user already created it, verify branch and HEAD instead of repeating creation. Check both local and remote name collisions. A failed lookup is not absence.

No new worktree, branch deletion/rename, reset, rebase, stash, git clean, force-push, broad staging, or sibling-worktree mutation. Respect actual Git/process/network approval mechanisms. Do not alter ACLs or security settings to bypass restrictions.

Verify the existing worktree-local `.venv\Scripts\python.exe`, Python version, pip check, and `app.config.__file__` resolving to this worktree. Reuse the valid environment. If genuinely absent, creation of a worktree-local venv and installation of `apps\backend[dev]` are authorized. Do not copy a sibling venv or upgrade dependencies.

Verify Node/npm, the locked frontend tree, Playwright browser executable, CMD/PowerShell and Docker availability. `npm ci` and lockfile-matched Chromium installation are authorized only when needed, without manifest/lock changes. No system-software installation or external account setup is authorized.

Proposed guarded browser ports: backend 8873 and frontend 4283. Verify actual runner arguments and port availability. Lifecycle uses 8000/5173; never overlap conflicting heavy workloads. Never kill unrelated occupants. Check runtime manifests and ownership before any cleanup.

Report `STARTUP READY` as a progress checkpoint and continue; do not end the task there. Missing optional tools do not stop unrelated implementation. Missing required evidence blocks the dependent acceptance claim.

## 4. Freeze the detailed plan and shared contract before parallel edits

Create `.ai-pipeline/001_planner/ATTENTION_QUEUE_PLAN.md` with the exact source owners, proposed paths, interface shape, test scenarios, role ownership and acceptance mapping below. This is implementation planning under the approved scope, not another general candidate-selection exercise.

Use a narrow read-only architecture/privacy checkpoint to establish that existing owners suffice. Do not introduce a canonical service/repository or ADR merely to make the work look sophisticated. If an ADR or substantive authority change is genuinely required, follow the repository rule and stop dependent implementation until separately authorized.

The current source map to inspect and reuse:

- `apps/backend/app/domain/case_management.py`: lightweight portfolio model.
- `apps/backend/app/domain/zero_touch.py`: existing exception/status enums; read-only unless an import-only adjustment is truly required elsewhere, not a new domain type.
- `apps/backend/app/services/case_portfolio_repository.py`: memory projection.
- `apps/backend/app/services/case_query.py`: authorized filter/order owner.
- `apps/backend/app/persistence/mongo_case_store.py`: bounded projected read and strict decoder.
- `apps/backend/app/api_models.py` and the list route in `main.py`: public projection and thin argument wiring.
- Frontend `types.ts`, `api.ts`, `caseQueries.ts`, `viewModels.ts`, and `pages/CaseQueue.tsx`.

Source observations at BASE_SHA: Mongo selects only exception `status` today and its decoder requires that exact projected shape. CaseQueue renders an always-empty assignment column. `caseQueries.ts` passes AbortSignal as the fifth argument to `fetchZeroTouchCases`. CaseQueryService already obtains an authorized projection before applying ordinary priority/unassigned filtering. Confirm these facts before editing.

Freeze the following contract:

- New row field `active_exception_types`: bounded sequence/JSON array of unique existing BusinessExceptionType values, canonical enum-declaration order, derived only from OPEN entries.
- A valid no-open-exception row returns `[]`; the existing active_exception_count remains the number of actual open exception records, not unique categories.
- Optional `attention_type` on existing `GET /api/clm/zero-touch/cases` accepts one exact enum. Omitted means no type filter. UI All omits the parameter. Invalid supplied values use existing 422 behavior; no fuzzy matching, aliases, or invented `ALL` backend enum.
- Filters compose as intersection with existing status, priority, team, jurisdiction/search behavior; ordering and unset-priority placement are unchanged.
- No new endpoint, count/facet response, parameter for arbitrary expressions, or global statistics.

Prefer the smallest service-layer filter on the already-authorized validated portfolio records. This is server-side filtering and preserves one projected Mongo find. Do not introduce database attention-query pushdown, a new index, or repository signatures solely for this slice. The new projected field and strict Mongo decoder remain required.

## 5. Backend implementation invariants

The backend worker owns the listed backend files and its focused tests. Domain models validate bounded types and deterministic output; memory and Mongo use the same semantics, not independently invented string sorting.

Authorization and team selection occur before exception filtering and before decoding data outside the selected scope. Preserve safe inaccessible/absent behavior and role-specific team-filter rules. Do not change capabilities or error policy.

Mongo projection adds only `automation.exceptions.exception_type` alongside `status`. Do not select entire exceptions, explanations, evidence values, actor details, notes, or full envelopes. Keep existing identity, revision, schema and timestamp validation.

Validate the new projected exception field on all projected entries, including closed history; only OPEN entries contribute to the result. Do not silently discard malformed entries, coerce unknown enums, infer a missing exception type from the stage, or use a default empty list to hide corrupt storage. Preserve existing safe persistence-error mapping.

Supported legacy case-envelope versions must remain readable through the existing read projection. Verify actual legacy shapes and fixtures. Do not add a v5 envelope, migration, repair-on-read, or rewrite old stored records to add this derived field.

Adversarial example: one OPEN exception of type A and one RESOLVED/CANCELLED exception of type B must not match filter B. The status and type belong to the same exception; independent array membership is insufficient.

One authorized projected Mongo query per list request, zero full-envelope decodes and zero row-detail queries attributable to filtering. No provider/cache lookup, document processing, ownership analysis, readiness evaluation, workflow progression, target call or persistence write caused by the new projection/filter. Existing authentication session housekeeping is not to be misrepresented as globally zero in-memory side effects.

No new assumption that status COMPLETED/TECHNICAL_FAILURE/RECOVERY_PENDING itself creates or removes an exception. Derive from valid retained state and preserve its invariants.

## 6. Frontend implementation invariants

The frontend worker owns its listed client files and focused tests after interface freeze. Append the optional attention argument without shifting existing positional AbortSignal callers; avoid a broad transport refactor. Thread the filter through the actual request and query key.

Retain the existing case-list prefix. Keys distinguish user, status, priority filter/sort, Director team filter and attention type. Do not add a second QueryClient, local data store, auth owner, persistence, or filter parameter in the URL.

Place presentation state in the existing CaseQueue presentation owner; avoid duplicate filter state. Changing it must not require changing App.tsx's ownership. An optional backward-compatible shape/default may be used if needed, with tests for existing callers. No broad navigation change.

Use a typed complete display-label mapping corresponding to the existing backend enum. Validate its coverage with focused contract tests; do not create an unreviewed parallel set of business categories. Static options enumerate supported categories, not categories/counts from inaccessible cases.

Suggested UI wording: filter `Open business exception type`, default `All types (no type filter)`, column `Open business exceptions`. Render `No open business exceptions recorded` for a known empty list, not `No attention needed` or `Approved`.

Keep the existing exception count and existing status labels. Never equate distinct type count to exception count or silently hide technical/recovery cases when the type filter is unset. Preserve readable labels, accessible native controls, narrow-screen wrapping/scrolling, and native Open links.

Remove the Assigned to column and placeholder field only after scanning tracked consumers. Do not remove actual team/client scope or unrelated HomeOnboarding dialogs. If the view-model placeholder has an unrelated consumer, retain it outside the queue and report the precise retirement limit rather than breaking that consumer.

Keep cached data explicitly labelled when a refresh for the SAME identity/key fails. Do not display a previous actor/team/filter's results under a new filter label. Auth loss and safe inaccessible-case handling retain current invalidation/clearing semantics.

Verify existing mutation invalidation reaches ALL attention-filter variants. A case can leave a filtered result after review; a deleted row cannot reappear from a late response. Do not add a blind mutation retry or a second optimistic decision owner.

## 7. Controlled file and integration ownership

Coordinator owns shared-plan/contract decisions, reports, E2E integration after worker freeze, and Git. No simultaneous writers to the same file.

Additional allowed changes after being named in the plan:

- Relevant existing backend and frontend tests/fixtures, including the Phase 14 projected-read and physical Mongo tests.
- New focused Attention Queue test modules following repository conventions.
- Existing guarded `apps/frontend/e2e/authenticated-zero-touch.e2e.ts`.
- Narrow queue styles in existing `styles.css`, assigned to the frontend worker.
- Existing relevant portfolio/list contract documentation, current architecture/project-state candidate wording, and a short `docs/demo/ATTENTION_QUEUE_DEMO.md`.
- The plan, this brief, `.ai-pipeline/reports/ATTENTION_QUEUE_IMPLEMENTATION.md`, and `.ai-pipeline/reports/ATTENTION_QUEUE_QUALITY_GATE.md`.

Prefer extending existing Phase 14 physical tests so runner suite ownership remains unchanged. If a separate module is concretely necessary, the coordinator may narrowly update `scripts/run_physical_mongo_tests.py` and its corresponding unit test to add the explicit suite; preserve all existing suites, safety, redaction and dynamic counts. Record CI_TOOLING as applicable. No arbitrary test discovery or ownership expansion.

Unchanged boundaries: App.tsx/navigation/auth/query-client lifecycle owners; case/cache envelope models; cache coordinator/configuration; workflow/domain action services; target ledger; providers; dependencies/lockfiles; CI workflow; lifecycle helper/launcher; repository-wide governance rules.

Unrelated defects are recorded, not opportunistically repaired. A genuine change outside these bounds requires owner authority, not internal agent approval.

## 8. Acceptance map

AQ-01: New types are derived only from OPEN exceptions; closed/cancelled history excluded from output.

AQ-02: Duplicate open types deduplicate in enum order; actual open count preserved; no-open valid rows yield [].

AQ-03: Exact optional attention_type filter; invalid values 422; omitted parameter preserves old results/order except additive field.

AQ-04: All existing filters compose correctly; mixed OPEN-A/RESOLVED-B fixture cannot match B.

AQ-05: Role/team authorization precedes attention selection; inaccessible data does not influence rows, counts, labels or parse failures. Director selected-team and unassigned behavior remains defined by current owners.

AQ-06: Memory/Mongo parity across supported case versions; no envelope writes, version/index change or full-envelope decoding.

AQ-07: Missing/unknown/malformed projected types/statuses fail closed with safe errors; corrupt data is never presented as an empty healthy result.

AQ-08: One authorized projected Mongo find and no N+1/full-case reads on list. New filter/projection causes zero business/provider/target writes or calls.

AQ-09: Query-key/request identity includes attention type and preserves AbortSignal, authentication, team filters and existing callers.

AQ-10: Filter switches and actor/session replacements cannot display stale foreign results; explicit loading/no-match/error/cached-refresh states remain truthful.

AQ-11: Existing review/recovery/priority/delete invalidation covers all list variants; deletion cannot resurrect a row.

AQ-12: Status and business-exception categories remain distinct. No fabricated reasons for technical/recovery/completed states; no "all clear" claim from an empty list.

AQ-13: Unsupported assignment column retired without breaking other consumers or team scope; no new confidential fields or arbitrary HTML/URL surface.

AQ-14: Real guarded browser journey proves usable filter selection and chips, two feasible distinct business types, cleared filter, existing case navigation, and narrow-screen/keyboard behavior.

AQ-15: Physical Mongo executes every currently owned test with no failures/errors/skips and verifies exact disposable database/container cleanup.

AQ-16: Required affected broad suites, contracts, static/security/governance checks pass on final content; historical failures and evidence applicability remain explicit.

AQ-17: Fresh independent exact PASS; reviewed-content identity preserved through pre-PR, one normal publication, separate push/PR CI identities; human-only merge.

## 9. Establish demo/test feasibility early

Before major UI work, confirm supported synthetic fixtures can create at least two different real OPEN exception types using existing guarded composition and public APIs. Preferred examples are document review/low confidence and ownership/jurisdiction blockers; use only scenarios actually reachable under current configuration.

Technical/recovery/completed states need backend/component/physical coverage even when not reachable through guarded browser setup. Do not enable demo fault controls, add hidden fixture endpoints, edit production data directly, or synthesize API success to claim a real browser journey.

Use real authenticated setup operations where the current test harness supports them, and exercise the actual filter through the browser. Setup may create/process synthetic cases; measure subsequent filter-read effects separately so setup calls are not confused with filter calls.

For an uncached filter interaction expect one new list GET, zero row-detail GETs, zero mutation calls. A valid same-key cache hit may cause no HTTP request; do not force needless traffic for a count assertion. Account for existing unrelated prefetch only by named bounded request roles, not by weakening the guard.

If no pair of scenarios can be produced in the authorized runtime, report the exact browser acceptance gap early. Do not quietly narrow the promise or wait until final QG to reveal it.

## 10. Verification and disposable infrastructure

Run focused backend/service/API/projection and frontend/query tests first. Include deferred-response tests, unknown enum/shape tests, exact payload minimization, legacy projections, cross-team malformed-data exclusion and mixed-status/type cases.

Run all required affected matrix checks: full backend, Ruff/mypy, contracts, full frontend/typecheck/build, guarded browser, required POC/lifecycle and secret/governance checks. Derive test inventory and fixture changes from current source. Unexpected removed/deselected tests need explanation; counts are not targets to manufacture.

A physical Mongo run is REQUIRED because the driver projection and strict decoder changed even though the stored schema did not. Do not reuse old physical evidence as proof of the new projection.

The owner authorizes one disposable task-owned MongoDB 7 Docker service if needed: unique name/container ID, verified free localhost-only port, no host bind mount/shared named volume/privileged mode, generated allowlisted databases only. Pulling the standard mongo:7 image if absent is permitted; installing Docker or using Atlas/ambient credentials is not.

Pass PHASE12_MONGO_URI only to the guarded physical child-process environment. Never print or save it, inspect .env, use clm_poc, or run broad database/container cleanup. Verify generated database deletion and clean up only the exact owned container/anonymous volumes. Existing approved isolated infrastructure can be reused only after positively verifying ownership and scope.

If Docker/permission/required browser is unavailable, continue independent in-scope work and report the blocked evidence. Do not issue an overall PASS without required physical/browser results.

Full lifecycle tests must use the verified local venv and existing memory/synthetic-auth isolation. No dependency on ambient Mongo. Keep the existing diagnostic instrumentation and deadline/identity rules unchanged. Serialize physical, lifecycle and browser suites.

## 11. Self-review, remediation, and independent acceptance

The implementers inspect their combined final diff against AQ-01 through AQ-17 before QG. Challenge decoder shape, privacy, type/status correlation, role/team filter composition, query prefix compatibility, same-user session replacement, cached errors and placeholder retirement.

New defects must have a deterministic regression or concrete falsifiable runtime evidence. Allow up to two implementation repair attempts per underlying defect, then an internal lead High design assessment within the existing scope. Do not add patches indefinitely or let a lower worker widen authority.

Distinguish pre-execution environment blocks from actual assertions. After an actual permission/setup correction, the previously unexecuted command may run through the supported approval path. Preserve both records. Do not restart an unchanged failing suite until green or secretly prewarm it.

After a final behavioral repair, rerun the failed focus and every affected required check. A new unresolved auth/lifecycle/physical failure is not waived by historical owner-risk decisions. Diagnose with existing sanitized evidence and stop dependent acceptance; unaffected lanes can still finish.

Freeze all final source/tests/docs and the implementation evidence before requesting a fresh independent High QG. That reviewer is read-only except its assigned quality-gate report, checks real evidence, runs proportionate independent tests, and writes exact PASS or a non-passing verdict. Self-review and diagnostic-only PASS are not final acceptance.

On findings, a separate implementer repairs within scope and a fresh review rechecks the changed content. Preserve prior FAIL findings, who implemented/reviewed, and content identity. No requirement to rerun every broad suite for a documentation-only correction if unchanged-code applicability is established.

All task-owned new Markdown is checked for final newline, trailing whitespace and conflict markers BEFORE freeze. Use normal paragraphs or explicit <br>. Mechanical hygiene correction is authorized; a changed reviewed document needs a focused identity/meaning recheck, not invented product tests or a new owner approval merely for formatting.

Do not require a report to hash itself. Capture its final published blob externally. Include the finalized final QG report in the first publication candidate; avoid status-only report commits after every CI observation.

## 12. Documentation and publication

Record implementation facts, not future acceptance. Preserve verified_main_sha's existing behavioral meaning; distinguish the source base, tested candidate, independently reviewed content and later actual main merge. Do not mark the new queue accepted on main before its human merge, rewrite historical reports, close sponsor questions, or relabel Mock/Local/Partial/Dormant as Live.

After exact independent PASS, a separate publisher is explicitly authorized to:

1. Verify frozen content and the exact task-owned path set, including final evidence reports.
2. Stage only reviewed paths; require staged whitespace/hygiene and secrets checks before committing. No git add -A.
3. Commit normally without amending accepted/shared history. Suggested title: `feat(cases): add blocker-aware attention queue`.
4. Fetch/inspect main drift at a clean boundary. An understood non-conflicting normal merge is authorized. Semantic conflicts or changes to reviewed behavior require affected tests and independent scoped recheck; no blind ours/theirs or rebase.
5. Pass clean committed-tree pre-PR and require a clean tree.
6. Push `feature/blocker-aware-attention-queue` to the verified repository, verify remote SHA, and create/update exactly one PR against main. Never force-push, duplicate a PR, enable auto-merge or merge it.
7. Observe normal push and pull_request workflows independently with repository/PR/branch/head/base/run/attempt and actual checkout identity when available. A helper limited to PR events cannot prove push status. Inspect actual failed job logs, not only exit metadata.

Respect actual platform/tool approval prompts. No instruction bypasses missing permission. If publication is unavailable, return the exact completed stage and required approval rather than only acknowledging an intent to act.

Allow at most two evidence-driven in-scope CI-remediation rounds, each with applicable independent recheck and a real corrective commit. No empty commits, blind workflow reruns or risk waivers. Unrelated failures require a bounded diagnostic handoff, not scope expansion.

Live CI results belong in the PR/chat receipt, not new source commits solely to change stored status prose. Pending CI is pending, not PASS. Do not promise monitoring after the active task ends.

## 13. Completion receipt

Return actual results:

- folder/branch/BASE_SHA/current main and source/review identities;
- scope delivered and any unsupported/deferred scenario;
- precise fields, filters, presentation changes and retired placeholders;
- backend/frontend/physical/security/contract/lifecycle/browser evidence;
- relevant counts, failing history, remediations and limits;
- independent verdict and reviewer independence;
- commit, pre-PR, remote match, PR, separate push/PR CI;
- exact owned-resource cleanup;
- a five-minute synthetic demo and truthful provider boundaries;
- next human action.

Use statuses that reflect reality: READY FOR INDEPENDENT QG; BLOCKED with a precise reason; CI IN PROGRESS; CI FAILED with evidence; or READY FOR HUMAN REVIEW/SQUASH MERGE.

Never describe this as reviewer assignment, generic risk triage, an SLA/approval system, a new workflow engine, live-provider integration, or Phase 17 completion. Stop after the authorized increment. Human final merge remains required.
