# Phase 17 — Case Activity & Audit Explorer

## Assignment and owner authorization

Implement this complete bounded product increment in ONE parent Codex session.
One implementation owner handles backend, frontend, tests, and remediation.
Do not allocate routine backend/frontend milestones to separate implementation agents.
Planning is the first internal step, not the final deliverable.

By submitting this prompt, I approve Phase 17 as the project-defined POC scope below,
and authorize its specified setup, branch creation, implementation, tests, bounded
repairs, independent reviews, scoped commit/push and one PR. This is not sponsor
approval of production audit, retention, reviewer attribution, or business policy.
No PR merge or residual-risk acceptance is delegated.

MODEL / EFFORT
Lead and sole implementer: Sol High; Extra High only for a concrete difficult design
question if actually supported. Fresh independent final reviewer: Sol High.
Distinct publication invocation: Medium where available. Claim only actual tools,
models and reviewer invocations; do not fabricate independence.

WORKTREE
C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix

EXPECTED RELEASED BRANCH
feature/blocker-aware-attention-queue

EXPECTED RELEASED HEAD
2a8b9b6e3be8a67829191ad7ddcb7cfb8d260bf1

BASE_SHA
1657a88a43e2fa8606e4f3d26f3bd05d16313d9e

NEW BRANCH
phase/17-case-activity-audit-explorer

REPOSITORY
shaneqwaszx/data-dividends-zero-touch-clm

## 1. Preflight and continuity

Read AGENTS.md, current project state, architecture, development workflow, relevant
contracts/decisions/questions and repository skills, then current owners/tests.
Use current source over stale snapshot prose. Phase 16, the Evidence Workbench and
Attention Queue are accepted; do not rebuild them.

Verify exact folder, branch, HEAD, index, tracked/untracked ownership, active Git
operation, live remote state, and absence of a concurrent writer. Fetch through normal
permissions. Do not bypass a denial, alter ACLs, delete Git metadata or inspect siblings.

If still on the released branch, require a clean tree and verify PR #45 merged and
origin/main equals BASE_SHA. Verify the new branch is absent locally and remotely;
a failed lookup does not establish absence. Direct creation from that verified commit
in THIS worktree is explicitly authorized; do not switch the stale control checkout:

git switch --no-track -c phase/17-case-activity-audit-explorer 1657a88a43e2fa8606e4f3d26f3bd05d16313d9e

If already on the assigned branch, reconcile task-owned work and continue. A copy of
this prompt explicitly supplied in the worktree is an allowed task input. Do not reset,
stash, clean, duplicate a branch, create another worktree, or discard existing work.
Stop for unexpected ownership or unexplained main drift, not for normal task changes.

Verify the existing .venv interpreter/import path, pip check, pinned frontend tree,
installed Chromium, Docker, and actual PowerShell process-control permissions. Reuse
working installations. Missing worktree-local environment/dependencies may be prepared
with supported Python 3.12, repository-declared backend dev installation, npm ci, and
lockfile-matched Chromium. No upgrades or new dependencies/system software.

Reserve browser ports 8875/4285 only when free; lifecycle uses 8000/5173. Do not kill
unrelated occupants. Verify manifests and ownership before execution. Report STARTUP
READY as progress and continue; do not end the session there.

## 2. Product outcome and initial design

Replace the existing AuditTrail browser list-plus-every-case-detail fan-out with an
authorized paged read of RETAINED AUTOMATION TIMELINE EVENTS. Preserve the existing
all-cases and case-specific navigation, existing action buckets, and useful case links.
Add exact stage/outcome filters, a UTC date window, bounded paging and explicit refresh.

The user should answer: what recorded events happened, on which accessible case,
at what time, and with what reported outcome? The user must not be told who performed
an action when the source does not record an actor.

Read AuditTrail.tsx, mapCaseTimelineToAuditEntries, the existing summary timeline
projection, AutomationEvent, access-policy route classification, CaseQueryService,
portfolio repository adapters, and MongoCaseStore. Confirm that the existing timeline
maps to ZeroTouchAutomationRecord.events; do not assume other event streams are covered.

Create one compact .ai-pipeline/001_planner/PHASE_17_PLAN.md with exact files, interface,
ordering/validation strategy, permissions, checks and acceptance mapping. Prove the old
request-count behavior in a deterministic test/harness. Do not recreate a broad roadmap.

This task authorizes extending the existing case-query and portfolio-read context with
activity methods, one read-only route and one minimized DTO family. It does NOT authorize
another persisted event store or an independent business audit owner. Apply the existing
architecture-change review before implementation. If existing ownership suffices, record
that evidence in the plan. A genuinely new canonical owner/dependency direction requires
its ADR/checkpoint before dependent edits; do not hide it as a helper or build a framework.

## 3. Exact event and API contract

Add GET /api/clm/zero-touch/activity, classified under existing CASE_PORTFOLIO access.
Preserve all existing list, detail, review, dashboard and audit navigation routes.
This endpoint changes route coverage, not the existing roles or capabilities.

Query inputs:
- optional case_id: canonical UUID;
- existing Director team_filter semantics; ordinary team users cannot override scope;
- optional action: existing CREATED, DOCUMENT, RECONCILIATION, OWNERSHIP, TARGET,
  COMPLETED presentation buckets, with the exact current matching semantics;
- optional stage and outcome: exact EXISTING AutomationStage/EventOutcome enums;
- optional from/to: explicit timezone-aware timestamps normalized to UTC; interval is
  from-inclusive/to-exclusive; when both exist require from < to;
- limit: integer, default 50, minimum 1, maximum 100;
- offset: integer, default 0, maximum 10000, non-negative.

UI All omits its parameter. Reject invalid enum/UUID/date/window/paging values using
existing safe 422 conventions. No raw expression, regex, arbitrary sort, SQL/Mongo
fragment, user-supplied authority or free-text-message search. Do not add global counts.

Return items, offset, limit and has_more. Determine has_more with at most limit+1 row
lookahead. No total/total-pages estimate. Empty matches are a successful empty page;
inaccessible/nonexistent/deleted requested cases retain the same safe 404 behavior.
A visible existing case with no automation/events can return an empty history.

Each item contains only fields needed for this view: case_id, source sequence,
timestamp, event_type, status, stage, outcome, code and the existing bounded safe message.
Preserve source values. Derive the UI key from (case_id, sequence), not a new stored ID.
Retain the existing displayed priority/client-scope context only through minimized
current_priority/current_client_scope_label projection and bounded metadata resolution.
Label these as CURRENT case metadata, not the values at event time. No per-row queries.

Do not expose source payloads, document fields, exception evidence, cache keys, endpoint
references, target request/response bodies, tokens, hashes, notes or invented attribution.
The existing safe event message is not authorization to return arbitrary log text.
Render it as escaped text; do not put it in URLs, logs, HTML or analytics.

Global order is timestamp descending, canonical case UUID ascending, sequence descending.
Tie-breaking must be identical in memory and Mongo. Preserve timestamp precision and
compare instants, not inconsistent textual encodings; inspect the actual storage encoder
before choosing aggregation expressions. Do not silently round to milliseconds.
Event sequence is source-local; timestamps do not prove cross-case causal order.

Filters apply BEFORE pagination, and authorization applies BEFORE event processing.
The action buckets are presentation filters only and may overlap as they do today.
They must not change workflow classification or event production.

## 4. Live-view, scope and retention boundaries

This is a paginated view of currently retained automation events, not a new production
compliance audit ledger. Do not aggregate document/admin/auth streams to suggest complete
coverage. No actor identification, signatures, immutability certification or exactly-once
claim. Existing case deletion removes the corresponding available history; do not retain
copies, tombstones or a separate archive. Export CSV remains unavailable.

Offset paging is a bounded live POC view, NOT a transactionally frozen cross-page snapshot.
For unchanged data, traversal is deterministic with no omissions/duplicates. Concurrent
inserts/deletes can move page boundaries; disclose this, provide Refresh from page one,
and do not fabricate completeness or resurrect deleted cases to stabilize pages.
No automatic background polling or fetch-all-pages behavior.

At the offset limit, disable further Next navigation and ask the user to narrow filters;
do not falsely report the end of all retained history when has_more is true. These numeric
limits are owner-approved technical safety bounds, not sponsor SLAs or retention policy.

Use only existing current access semantics. Re-authorize every request independently;
client query state never grants permission. HR/no-case-capability access remains denied.
A single-case filter must not turn inaccessible existence into a count or different error.

## 5. Read architecture and strict persistence

Extend existing CaseQueryService, portfolio repository protocol/adapters and
MongoCaseStore with cohesive activity-read methods. Keep authorization and metadata
resolution in the existing service/policy owners, never in React or database route code.
Do not call the full zero-touch summary/orchestrator for every event or case.

Mongo requirements:
- first restrict candidate envelopes by server-authored visibility and optional case;
- project only identity/schema/revision metadata, permitted current-case context and
  required automation-event fields;
- filter/sort/page in the database using a server-owned bounded pipeline;
- one case-collection aggregation per page, excluding normal bounded authentication,
  selected-case existence/access and team-metadata checks;
- at most limit+1 event rows transferred to application code, plus bounded validation
  status where needed; no complete envelope decoding or per-case/per-event fetch loop;
- no $out/$merge, writes, repair-on-read, collection, index, migration or schema v5;
- a finite execution/resource budget, with failures sanitized and reported as errors,
  not empty success; no memory fallback after Mongo failure.

Validate relevant candidate envelope identity/schema/revision and event structure:
strict sequence/type/status/stage/outcome/time/identity, bounded code/message, and source
identity agreement. Supported v1-v4 remain readable without rewrite. A missing/wrong-type
event array is not an empty history unless that absence is actually a valid legacy shape.

Do not silently drop corrupt events using conversion defaults, unwind behavior or an
is-valid filter. Design a bounded invalid-data signal so malformed scoped query-relevant
data cannot become a clean empty/partial page. Corrupt OTHER-TEAM data must not affect a
team user's result. State the precise validation boundary; do not claim this read validates
unselected payload fields or the entire database. One aggregate may contain a bounded
validation branch; do not fetch all events into Python to perform it.

Memory uses the same contract and ordering, scopes before event inspection, and avoids
copying complete case envelopes or creating a second persistent read store. Measure and
disclose scan costs. A bounded reply/one query does not imply constant-time database work.
Do not add an index or external search system to claim scale not actually demonstrated.

## 6. Frontend and existing-cache integration

Refactor AuditTrail to the new endpoint through existing authenticated transport and
React Query ownership. Remove its list-plus-N-detail loading path; do not keep it as a
silent fallback. Retire old helpers only after checking all consumers.

Preserve /audit and existing case-specific URLs, Clear case filter and native case links.
Do not build a new navigation state system. An App.tsx change, if necessary, is thin
actor/prop wiring only. Keep authentication/session transport owners unchanged.

Use current session/user-scoped keys including case, team, action, stage, outcome, UTC
window, offset and limit. Preserve AbortSignal and compatibility of existing callers.
A new filter/actor/case key must not display previous-key results as current. Reset paging
when filters change; same-key refresh can show its own stale data with an explicit label.
Logout, 401, same-user replacement and authorization changes clear incompatible data.

Extend existing mutation cache effects so relevant case/review/priority changes invalidate
activity queries. Deletion must cancel/remove affected activity caches before a late
response can republish deleted rows, including all-cases pages. No business action is
triggered by opening, filtering, paging, refreshing or inspecting the history.

Build accessible filters with labels, previous/next controls, returned-page count,
explicit empty/loading/error states and 480px layout/internal table scrolling. Detail
expansion is local and request-free. Remove the always-unknown By/Loop display columns,
not unrelated data/models. Show “Actor attribution is not recorded” in the explanatory
copy. Keep export disabled; do not introduce export or print artifacts.

Do not call an empty page “no activity anywhere”, “approved”, or “compliant”. Show the
UTC date convention and live-pagination limitation prominently enough to be understood.

## 7. Authorized files and small context refresh

Expected existing owners:
apps/backend/app/domain/case_management.py
apps/backend/app/services/case_query.py
apps/backend/app/services/case_portfolio_repository.py
apps/backend/app/persistence/mongo_case_store.py
apps/backend/app/persistence/repositories.py
apps/backend/app/api_models.py
apps/backend/app/main.py (thin route wiring)
apps/backend/app/services/authorization.py (exact route registration only)
apps/frontend/src/api.ts, types.ts, caseQueries.ts, viewModels.ts
apps/frontend/src/pages/AuditTrail.tsx and narrowly relevant styles

Directly affected source tests, API/RBAC route inventories, physical suites and guarded
E2E may be extended. Choose a small activity-domain module only if needed for cohesive
read types; it is not another canonical repository/service. Record exact additions in
the plan before editing. No broad configuration/dependency/refactoring permission.

Authorized evidence/docs:
.ai-pipeline/001_planner/PHASE_17_PLAN.md
.ai-pipeline/reports/PHASE_17_IMPLEMENTATION.md
.ai-pipeline/reports/PHASE_17_QUALITY_GATE.md (independent reviewer only)
docs/contracts/CASE_ACTIVITY_QUERY_PROFILE.md
docs/demo/PHASE_17_ACTIVITY_DEMO.md
docs/PROJECT_STATE.md and docs/ARCHITECTURE.md (narrow relevant updates)

Fold in the outstanding PR #45 context correction: inspect its accepted main behavior
and set the documented inspected baseline to BASE_SHA. Mark Attention Queue accepted;
Phase 17 remains candidate/pending merge in its phase reports. Do not invent its future
squash SHA, close sponsor questions or start a separate docs-only PR.

## 8. Continuous verification and acceptance

Implement the entire vertical slice incrementally. Run focused tests as each owner
changes; inspect your diff and fix demonstrable in-scope defects before QG. Do not
wait for final review to discover missing types, route coverage or malformed fixtures.

Cover these acceptance criteria:
A17-01 Exact retained automation events only; event values and source identity preserved.
A17-02 Current role/team access, selected-case safe 404 and corrupt-other-team isolation.
A17-03 Strict action/stage/outcome/UTC/paging validation and filter intersection.
A17-04 Same deterministic memory/Mongo order, timestamp ties/precision, boundary pages.
A17-05 Empty/one/full/lookahead/end/offset-cap behavior; no invented total or snapshot.
A17-06 v1-v4 compatibility; malformed scoped metadata/events fail safely, no hidden skip.
A17-07 One page HTTP call and one Mongo activity aggregation, no detail fan-out/full decode.
A17-08 Zero workflow/provider/ownership/cache/target/persistence mutation from activity reads.
A17-09 Session/filter/page isolation, cancellation, invalidation and no deleted-row resurrection.
A17-10 Real browser login, filters, paging, scoped view, case links and keyboard/mobile layout.
A17-11 Honest actor, current-metadata, timeline-coverage, deletion and live-view limitations.
A17-12 Existing Attention Queue, Workbench, review/recovery, no-replay and navigation preserved.
A17-13 Physical Mongo and current relevant regression matrix pass with cleanup verified.
A17-14 Frozen-content independent PASS, truthful docs and controlled publication.

Measure old and new request counts with synthetic fixtures. For 1/25/100 accessible cases,
prove the old structural 1+N behavior versus one uncached activity-page request after
initial authentication and unrelated app bootstrap. A same-key cache hit can require zero
requests. Do not manufacture provider operations merely to create bulk load data: use
existing safe deterministic/physical fixture construction. Browser setup uses public
supported synthetic flows; direct storage injection is confined to disposable test fixtures.

Test overlapping timestamps, multiple pages, expired/revoked sessions, case deletion between
pages, filter changes mid-request, same-user session replacement, unknown/invalid stored
fields, malformed/naive dates, query injection shapes, and escaped hostile safe-message
strings. Do not log confidential test payloads.

Run full affected backend, Ruff/mypy, contracts and route/security/governance checks;
full frontend/typecheck/build; the supported guarded Chromium suite; relevant POC
regressions and the unchanged Windows lifecycle suite. Use repository commands and actual
current totals, not historical counts. Compare test inventory when counts unexpectedly fall.

Physical Mongo is required. Extend an existing owned physical suite where cohesive; if a
new module is necessary, only the explicit existing runner list and its tests may be changed
so every old suite and the new suite execute. Do not alter the CI workflow.

One disposable task-owned MongoDB 7 container is authorized when needed, using a verified
loopback-only port, no host-data mount/shared volumes/privileged mode. Standard image pull
is allowed. URI goes only into test-process environment; never print or save it, read .env,
use Atlas/ambient databases, or access clm_poc. Verify database cleanup and remove only exact
owned container/anonymous volumes. No Docker prune.

Serialize browser/lifecycle/Mongo. Verify all prerequisites BEFORE each heavy run, including
worktree .venv and approved process control. Preserve pre-execution failures separately;
a corrected prerequisite permits the same original command to execute, not weaker assertions.

## 9. Bounded self-remediation and independent QG

A failure starts diagnosis inside this session, not an automatic user handoff. Reproduce
in-scope defects, add a regression, repair the cause and rerun affected evidence. Batch
related findings, but do not hide failures or weaken assertions.

Two unsuccessful repair cycles for the same mechanism trigger one internal High/Extra High
design assessment. If still unresolved or outside authority, stop dependent acceptance with
a specific handoff. Do not poll reviewers or repeat unchanged full suites until one passes.
Environment preparation failures are different from application assertions. New unexplained
login/lifecycle/persistence failures cannot inherit old owner-risk decisions.

Keep one compact implementation record with source identity, owned paths, results, failed
history, unresolved issues and next action. After context compaction reread it and resume;
do not restart discovery. Check tracked AND task-owned new Markdown for final newline,
trailing whitespace and conflict markers before freezing. Mechanical normalization within
task docs is authorized with proportional review; do not create a permission loop over it.

Freeze complete candidate content and invoke a real fresh Sol High independent reviewer
from the parent session. Supply this contract, plan, diff, manifest and exact evidence.
The reviewer must inspect code and run proportionate adversarial verification, not merely
endorse supplied test summaries. It writes only PHASE_17_QUALITY_GATE.md, preserves previous
findings, and cannot remediate production/tests. Pause implementation during review.

The parent repairs findings, re-verifies affected behavior and obtains independent re-QG.
Exact PASS is required; PASS WITH MINOR FIXES or diagnostic-only PASS is insufficient.
If genuine independent review is unavailable, return READY FOR INDEPENDENT QG rather than
role-playing acceptance. Do not self-hash the reviewer report or rewrite old verdicts.

## 10. Publication and finish

After exact independent PASS, launch the distinct publisher invocation within this session.
It verifies reviewed identity, stages only accepted files, checks staged hygiene/secrets,
and commits implementation plus finalized evidence before running clean-tree pre-PR.

Fetch and inspect latest-main drift at a clean boundary. An understood normal integration
merge is authorized; changed semantics require affected verification and independent
recheck. Stop on unclear conflicts. No rebase, accepted-history amendment, force-push or
blind ours/theirs. Keep diagnostic output and credentials out of publication.

After pre-PR PASS and clean state, push the assigned branch and create/update ONE PR:
feat(audit): add paginated case activity explorer

Verify local/remote SHA match. Observe normal push and pull_request CI separately, including
actual checkout identity when available. New in-scope causal CI defects may be repaired
within the same remaining budget with tests/review and a real corrective commit. No empty
commits, blind reruns, check waiver or owner-risk acceptance. Live CI status belongs in PR/chat,
not new report-only commits. Do not merge or enable auto-merge.

Target one six-to-eight-hour active execution budget, finishing earlier if done. This is a
work budget, not a promise of continuous runtime. Reserve time for independent review and
publication. Actual platform approvals still apply; do not evade them. If a permission/time/
resource limit prevents completion, preserve a precise resumable handoff.

Return one final receipt: scope, base/head, changed owners, measured query/request behavior,
all tests and preserved failures, physical/process cleanup, independent verdict, commit/
pre-PR/remote/PR/CI, a five-minute synthetic demo and the exact next human action.
Do not stop at planning or between normal milestones. Stop after this increment.
