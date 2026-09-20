# Overnight execution brief — Case Evidence & Explainability Workbench

Prepared for Shane / Data Dividends / Delta Capita FYP.
Pinned starting main: `6625835e6ca8b7e531c25b3078c3ff58ee4df843`.
This document proposes and, when submitted by the owner, authorizes the bounded work below. It is not sponsor approval or a production-policy decision.

## 1. Mission and completion boundary

Build a coherent read-only evidence experience on the accepted CLM prototype, not a new workflow engine or another review/rework implementation. A case reader should be able to answer:

1. Where did this case's registry evidence come from, and was it acquired or reused when bound to the case?
2. Which retained ownership paths explain the existing provisional UBO result?
3. Which existing blockers or target-operation states explain why the case is waiting, stopped, recovering, or Mock-complete?

Deliver three integrated capabilities: registry provenance, ownership-path exploration, and blocker/target explanation. Add the contract/regression/browser evidence and a short reproducible synthetic demo guide needed to accept them. This is one product increment and one PR, with separate implementation workers, not several independently published branches.

Use the task name **Evidence & Explainability Workbench**. Do not overwrite an existing Phase 17 roadmap assignment. During discovery, check the relevant roadmap once. If Phase 17 is reserved, keep this task unnumbered and record that fact; do not stop unrelated approved work or renumber other phases.

Target an approximately six-to-eight-hour work budget, including testing and remediation. This is a planning budget, not a promised duration or a requirement to keep working after completion. Stop earlier when the scope is complete. Reserve the final part of the budget for acceptance and handoff rather than more features. Do not begin a new phase or stretch feature automatically.

Desired result: exact independent PASS, clean-tree pre-PR PASS, one published feature PR with honest current CI status, and no merge. If blocked, leave a useful, reproducible handoff and preserve completed work without a false PASS.

## 2. Models, roles, independence, and permissions

Lead orchestrator: **Sol Extra High** if actually available; otherwise **Sol High**. Use Extra High for plan/architecture synthesis and difficult integration decisions, not every shell command.

Suggested routing when the host supports per-worker choices:
- bounded source discovery: Terra Medium or another available inexpensive capable model;
- backend projection implementation: Sol Medium;
- frontend evidence implementation: Sol Medium;
- adversarial test author: Sol High where asynchronous/security semantics require it;
- final independent QG: a fresh Sol High reviewer that did not implement or design the correction;
- publisher: Luna Medium or Sol Medium.

Use only actual models/tools supported by this session. Do not claim configured models, subagent independence, or isolated files that the host did not provide. If subagents cannot be spawned, implementation may proceed serially, but independent acceptance remains blocked until a real independent review is available. Renaming the implementer as reviewer is not independence.

Spawn at most three active implementation/discovery workers at a time. Stop implementation writers before final review. All workers share this one checkout only under explicit file ownership. One coordinator owns Git, shared integration files, dependency installation, final test scheduling, and publication. Workers never stage, commit, fetch, switch branches, or push.

By submitting this brief, the owner authorizes planning, the read-only product features below, needed additive safe response projection, scoped tests/docs, bounded in-scope remediation, necessary existing pinned dependency setup, local synthetic execution, disposable Mongo validation when relevant, independent reviews, scoped commit/push, and creation/update of one PR after acceptance. These are separately assigned stages in this run; do not stop after the planner merely because implementation is another role.

Platform permission prompts still apply. Do not disable the sandbox, change global approval policy, enable unrestricted computer use, obtain new account access, or approve your own tool actions. If a tool approval is unavailable, complete unrelated authorized work and report the exact blocked action. Do not promise the run can bypass an approval while the owner sleeps.

Human-only: sponsor-policy decisions, accepting unresolved new risks, changes to external account/secrets/security settings, and final PR merge. No automatic risk acceptance inherited from PR #41 or #42.

## 3. Workspace, branch, and source identity

Repository: `shaneqwaszx/data-dividends-zero-touch-clm`.
Reusable worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`.
Expected released branch before setup: `phase/16-registry-cache-freshness-planning`.
Last accepted released feature head: `4224936a9df90000a054149eccfbefe1da12d2c8`.
Merged starting main: `6625835e6ca8b7e531c25b3078c3ff58ee4df843`.
New branch: `feature/evidence-explainability-workbench`.

Prefer the owner to perform branch setup before starting this run. If setup is still needed, creation from the verified fetched main directly in this clean linked worktree is explicitly authorized. Do NOT try to switch to main in the stale control checkout. Read AGENTS.md first and surface a genuine non-resolvable authority conflict rather than guessing.

Preflight:
- verify exact root, current branch, HEAD, Git operation state, and current worker activity;
- fetch once before workers start and verify the expected main and merged PR #41;
- verify the released branch has no new local-only work beyond its accepted PR;
- require both local/remote target branch names and target task artifacts to be absent unless this is a verified continuation;
- preserve ignored environments and local data; do not inspect .env or protected parent artefacts;
- the owner-supplied brief at `.ai-pipeline/001_planner/OVERNIGHT_EVIDENCE_WORKBENCH_BRIEF.md` is an expected initial new file;
- stop on unrelated working-tree changes; never reset/stash/clean to obtain a preferred state.

If still on the released branch and safe, create:
`git switch --no-track -c feature/evidence-explainability-workbench 6625835e6ca8b7e531c25b3078c3ff58ee4df843`

If already on the intended branch at the intended baseline, do not recreate it. If main has advanced, inspect before any implementation and stop for a material authority/scope conflict. Do not silently replace the pinned starting design with unknown changes.

No additional worktrees, no cleanup/renaming of old folders, no local/remote branch deletion, and no change to the control, Camunda-sync, UI, observer, or visualization checkouts. They are not scratch space.

## 4. Current implementation facts to verify locally

Load authority in the repository-prescribed order: AGENTS.md; PROJECT_STATE; ARCHITECTURE; DEVELOPMENT_WORKFLOW; relevant contracts/decisions/open questions; appropriate skills; actual owners/tests. Then run `scripts/dev_context.py` with the valid worktree interpreter.

At the supplied baseline:
- CaseDetail already renders document-review/retry/replacement actions, reconciliation, ownership candidate percentages/calculation strings, registry operation details, readiness, target operations, and a timeline. Do not duplicate these as newly invented capabilities.
- Backend registry-cache acquisition/binding is implemented. Its coordinator is not a read-model service to invoke on page opening.
- `api_models.py` owns minimized browser projections and explicitly excludes internal registry references. Extend that owner, not raw domain serialization.
- Authentication uses current backend access controls and frontend session-generation containment. Preserve them.
- The Decimal ownership engine and retained paths are calculation authority. The browser must not calculate UBO outcomes.
- Cache is opt-in Mock only, default off, with case-bound evidence; a shared cache refresh does not reassess existing cases.
- Offline Camunda tests exist, but runtime Camunda, production SSO, and live-provider integrations remain absent.
- Historical lifecycle/login timeouts were not causally fixed by the merged diagnostic changes. Owner risk decisions were scoped to their exact earlier revisions; new failures are not waived.

A code-search index or historical prose can lag main. Resolve current facts using pinned files, not search-result recency. Never access a private sponsor artefact to fill an authority gap.

## 5. Startup gate — finish before leaving the machine unattended

Within the first stage, validate actual capabilities and prerequisites, then return a brief progress message `STARTUP READY` or the precise blocked prerequisite. `STARTUP READY` is a progress checkpoint, not the end of the task; continue automatically when safe.

Verify:
- `.venv\Scripts\python.exe`, supported Python, pip check, and imports resolve to THIS worktree;
- Node/npm and the existing frontend lockfile installation;
- local pinned Playwright executable and Chromium availability;
- PowerShell/CMD process-control support;
- ability to spawn and clean up owned loopback processes through supported approval;
- authenticated read-only GitHub access; publication permissions are separately enforced;
- required task ports and safe runtime metadata state;
- availability of independent subagents;
- Docker readiness only if physical verification is planned.

Necessary setup, if genuinely missing, is authorized:
`python -m venv .venv`
`".venv\Scripts\python.exe" -m pip install -e "apps\backend[dev]"`
`npm.cmd --prefix apps\frontend ci`
`apps\frontend\node_modules\.bin\playwright.cmd install chromium`

Inspect and repair an incomplete task-owned environment non-destructively; do not delete/copy another environment or change the launcher to use global Python. Use no dependency upgrades, audit fix, lockfile churn, or new graph/UI libraries. Do not perform setup repeatedly if already verified.

Use the repository's supported preflight/runner mechanisms. Do not perform a secret login or synthetic business mutation merely to test tool permissions. No warm-up before a cold-start acceptance journey unless explicitly identified as a separate experiment.

## 6. Plan and freeze the interface before parallel writes

Create one compact governing plan:
`.ai-pipeline/001_planner/EVIDENCE_WORKBENCH_PLAN.md`.

Perform parallel read-only discovery first: one source/API analyst and one UI/acceptance analyst. Each returns exact owner paths, observed gaps, pitfalls, and suggested tests. Do not load every historical report.

The lead then specifies:
- goals, non-goals, change classes, actual write set and component ownership;
- which existing components/helpers are reused or retired, with consumer search;
- the small safe registry-binding response contract, its unknown/legacy semantics, and frontend fixtures;
- explanation source map: every display claim points to an existing typed field/enum/result;
- layout/accessibility interaction specification;
- security, concurrency, data-minimization, and test requirements;
- proportional architecture/privacy review before new API exposure;
- merge and publication boundaries.

Obtain a fresh read-only architecture/privacy check of the concrete plan and additive public projection. A supported minimal response projection within the existing owner is authorized; a new workflow/data owner, domain policy, or persistence schema is not. The lead may accept ordinary engineering choices within these bounds and continue without asking for each component label or file name.

Do not turn the plan checkpoint into a separate planning PR. Plan, implement, review, remediate, and publish within this task when all gates allow it.

## 7. Capability A — case-bound registry provenance

Expose the existing immutable case binding through a deliberately minimized optional browser projection if the current public DTO does not already contain it. Prefer the established case response; no new endpoint or repository is needed merely for this panel.

The interface should communicate only retained, justified facts such as:
- acquisition disposition: original provider fetch versus cache hit;
- original provider/source classification and source retrieval timestamps;
- time the evidence was bound/used for THIS case;
- the retained freshness interval/version used for that binding, if present in source;
- a clear distinction between original retrieval and case use.

Proposed field names are not authority. Derive their actual names and types from RegistryEvidenceBinding and the existing browser model. An optional `registry_evidence_binding` projection is a reasonable default when no public equivalent exists. Backend and frontend workers share one frozen contract.

Required semantics:
- null/absent historical metadata means unrecorded/unknown; it does not prove a miss, disabled cache, a fresh fetch, or current validity;
- show original operation timestamps without rewriting or rounding away provenance;
- describe validity at use, not an invented live freshness evaluation;
- do not fetch shared cache contents to decorate a historical case;
- do not infer expiry from the current global policy or clock and invalidate an existing case;
- label 90 elapsed days as provisional Mock POC policy when sourced from the binding, not an ACRA validity or compliance guarantee;
- cache-disabled cases still display their existing source evidence and a truthful missing-binding explanation.

Do NOT expose cache-key digests, dataset internals, opaque server proof references, endpoints, credentials, arbitrary provenance URLs, repository internals, or other cases/teams. Do not serialize the entire domain object with model_dump into a public field.

Use explicit projection and strict bounded types. Preserve existing response fields. Additive contract changes must pass all existing consumers and tests. No persisted-field addition, schema v5, migration, read-repair, or cache-policy modification.

Opening/refreshing this panel must cause zero registry/IDP/ownership-analysis/target calls and zero business/cache writes attributable to the new feature. Normal existing authentication/session housekeeping is not falsely described as absolutely zero state activity.

## 8. Capability B — ownership/path explorer

Replace or enhance the existing static ownership presentation with a focused accessible explorer of ALREADY COMPUTED evidence.

Required experience:
- select a candidate/party;
- show direct, indirect and aggregated percentages exactly as the API's Decimal strings;
- inspect that candidate's retained calculation paths one at a time;
- highlight the corresponding nodes/relationships in a bounded diagram or path view;
- expose the backend's threshold/comparator, classification, uncertainty and issue messages;
- retain a keyboard-usable table/list alternative.

Read actual relationship semantics and do not reverse owner/owned arrows because of a generic graph layout. Party nodes repeated for display must not be counted as separate ownership paths. Use existing stable party/relationship/path IDs.

Do not multiply percentages, reaggregate paths, compute threshold decisions, choose UBO candidates, resolve cycles, invent missing edges, infer share classes, or compare floats as business authority. Layout arithmetic is fine; ownership arithmetic belongs to the existing Decimal engine.

Use existing components if present. No new external graph/layout dependency. A selected-path SVG/HTML layout is preferable to attempting a new unrestricted whole-graph engine.

Bound presentation: use a clear chosen limit for visible nodes/edges/paths, record it as a UI engineering constraint, disclose truncation, and keep access to the complete permitted table through bounded pagination. Never label a partial visualisation as a complete hierarchy. Avoid force-directed animation, exponential traversal, recursion over cycles, or huge DOM rendering.

Handle empty, pending, failed, cyclic, incomplete, and backend-limit results honestly. Do not hide uncertainty because the visible subgraph appears simple. Mock/local provisional ownership is not legal UBO identification or GoldTier hierarchy support.

## 9. Capability C — why-this-state explanation

Create a compact read-only explanation of the case's existing blocker/readiness/target evidence, with links/focus to the owning existing evidence section.

Required experience:
- explain the current typed automation state and stage;
- list the actual active blockers with their existing evidence/status;
- distinguish warnings from blockers;
- show retained target-operation statuses/order without replay;
- link the reader to the existing current-document review, reconciliation, ownership, or recovery section where supported.

This is deterministic display, not an LLM, rules engine, readiness calculator, or action recommender. A wording map may translate a known typed status, but unknown values need a safe generic fallback and visible uncertainty. Do not parse narrative timeline prose to invent eligibility.

Do not introduce another copy of review/resume/assignment controls. Existing mutation handlers remain the only owners. Clicking explanation navigation, expanding a panel, changing a selected path, or mounting the page must not issue any POST/PATCH/DELETE or secretly evaluate readiness.

An absent target operation is not automatically success, skipped, or safe-to-retry. Show exactly the retained result and current limitation. Mock submission is not approval. Do not add risk, SLA, staff performance, Ready-for-Approval, final reviewer policy, forced refresh, or production claims.

Where the response lacks a reliable evidence link, say so rather than join records by ambiguous names or timestamps. This view is a projection of observed records, not a newly certified atomic multi-record snapshot.

## 10. Runtime state and security invariants

Preserve existing authenticated transport, AuthProvider, React Query owner, URL identity, actor/session scoping, and case-action generation guards. No new QueryClient, persistent browser cache, localStorage/IndexedDB, service worker, auth provider, or mutable server-state mirror.

Fetch through existing case/document/ownership query owners. Opening these panels should normally add no network calls beyond the existing queries and the additive response field. No per-node or per-path network lookup. Manual read refresh must use supported owners and not become mutation replay.

On case A-to-B navigation, logout, same-user new session, actor/team change, deletion, 401/403/404, or an out-of-order response, no stale content/selection/error/focus may appear under another case or identity. Test using controlled promises and the actual accepted auth/cache machinery where applicable.

Use framework text escaping. No dangerouslySetInnerHTML, HTML injection, arbitrary source links, or raw payload display. Keep names/identifiers within existing authorized case views; do not turn those values into logs, test artifacts, exports, URLs or telemetry. No new data export feature in this core slice.

GET projection must use already authorized case/service state. Do not add direct Mongo/registry reads in an API handler or fall back to another team when a lookup fails. Cross-team absent/inaccessible semantics remain indistinguishable. A failed refresh must not be described as successfully reloaded evidence.

## 11. Parallel write ownership and integration

Freeze the actual paths after discovery. Default partition:

**Backend worker**
- `apps/backend/app/api_models.py`: additive minimized projection only;
- new focused backend API/projection tests under `apps/backend/tests/`;
- directly corresponding contract tests/docs;
- no acquisition/ownership/reconciliation/target/auth/persistence runtime edits.

**Frontend worker**
- new focused read-only components and their unit tests under `apps/frontend/src/pages/`;
- a task-local presentation helper/CSS module only when useful;
- no CaseDetail integration until coordinator assigns that exclusive stage;
- no mutation/auth/navigation-owner rewriting.

**Adversarial/QA worker**
- disjoint new test/fixture paths specified in the plan;
- existing physical test extension only under exclusive assignment;
- scenario map and demo guide;
- no production edits; not the final independent QG reviewer.

**Coordinator / integration writer**
- shared TypeScript types and frozen interface fixtures BEFORE parallel writing;
- CaseDetail mounting/section refs and styles AFTER workers stop touching dependencies;
- any minimum existing query-helper integration;
- E2E file integration after feature components are stable;
- canonical documentation refresh;
- all Git operations and dependency/environment changes.

No two writers edit a shared file simultaneously. If an owner needs a shared file, transfer the lease explicitly and pause its other writer. Worker tests must not race compilation of incomplete shared files. Heavy suites run only on a frozen integrated candidate.

No API transport/auth implementation edit is authorized merely because api.ts is nearby. If the existing helper already fetches the required case response, leave it unchanged. Narrow display integration is not authorization for an unrelated cache/session bug fix.

## 12. Synthetic scenarios and acceptance IDs

Bind actual fixtures to these criteria during planning; never invent a public setup capability.

| ID | Required proof |
|---|---|
| EW-01 | Existing baseline UI behavior remains available; no duplicate mutation owner. |
| EW-02 | Provider-fetch and cache-hit projections show actual retained disposition/timestamps. |
| EW-03 | Missing/legacy binding stays unknown and causes no persistence rewrite or cache lookup. |
| EW-04 | Refreshing shared registry evidence cannot mutate an older case's view/binding. |
| EW-05 | Authorized case access only; cross-team/HR/inaccessible behavior remains safe. |
| EW-06 | Panel reads and exploration cause zero domain/provider/target mutation/calls. |
| EW-07 | Decimal strings and backend classifications/calculations are displayed unchanged. |
| EW-08 | Multiple paths, cycles, incomplete/limited analysis are visualized without false completeness. |
| EW-09 | Candidate selection, focus and asynchronous results cannot cross case/session identity. |
| EW-10 | Blocker explanations use typed current evidence; warnings/unknowns never become approval. |
| EW-11 | Refresh errors retain truthful uncertainty; no automatic mutation retries. |
| EW-12 | Keyboard focus, table alternative, narrow-screen layout and truncation are usable. |
| EW-13 | Existing login, clean Mock onboarding, review/history/recovery and routing regressions remain. |
| EW-14 | Supported real-browser evidence journey executes through real login/local APIs under the network guard. |
| EW-15 | Existing five-suite Mongo parity passes when required; newly added projection checks execute without skips. |
| EW-16 | Public payload and diagnostic artifact negative tests exclude forbidden internal/private fields. |
| EW-17 | Current docs distinguish merged baseline, new branch scope, offline Camunda and unresolved policy. |

At least one real guarded browser journey must open the enhanced view on an actually created case and operate candidate/path/explanation controls. API interception may test errors/order but cannot substitute for the successful real journey. Preserve all existing E2E tests and original assertions; current inventory grows naturally.

Cache-hit/browser setup must be assessed early. Prefer supported unit/API/Mongo fixtures for proving cache-hit projection and a safe frontend contract test if the existing guarded browser runner cannot enable caching. Do not secretly enable cache/demo fault controls, alter runtime defaults, add fault endpoints or modify the runner to get a screenshot. Report exactly which layer proved each case. The required generic real-browser feature journey still must execute.

Add synthetic fixture files only inside the approved test directories, with no real sponsor/customer content. Do not generate long-lived credentials or write synthetic password values into reports. Use existing test-auth fixtures.

## 13. Testing, resources and physical evidence

Use the change-class matrix, not a blanket all-suites-on-every-worker policy. This likely includes FRONTEND_UI, FRONTEND_STATE_CACHE, BACKEND_API and privacy/security effects of the new projection. Classify actual changes explicitly. A read-only projection does not by itself authorize a persistence schema change.

Run focused tests after each coherent batch. Before QG, run the required integrated backend/frontend/type/build/contract/security/governance suites once on frozen implementation content. Let the final reviewer rerun targeted hostile tests and necessary real evidence, not create redundant unbounded full-suite loops.

Resources:
- proposed guarded E2E ports: backend 8871, frontend 4281, after actual runner-interface and free-port checks;
- Windows lifecycle uses its unchanged 8000/5173 ports;
- no concurrent full backend, browser, lifecycle, or physical Mongo workloads;
- use the existing worktree interpreter explicitly, not PATH-dependent global Python.

Typical commands (verify actual current package/scripts first):
`".venv\Scripts\python.exe" scripts\dev_context.py`
`npm.cmd --prefix apps\frontend run typecheck`
`npm.cmd --prefix apps\frontend test`
`npm.cmd --prefix apps\frontend run build`
`npm.cmd --prefix apps\frontend run e2e:list`
`".venv\Scripts\python.exe" scripts\run_e2e.py --backend-port 8871 --frontend-port 4281`
`".venv\Scripts\python.exe" -m unittest discover -s tests -p "test_demo_lifecycle_windows.py" -v`

Use current repository wrappers/PYTHONPATH conventions for backend/contract/static tests. Do not improvise commands that collect unrelated protected directories. Confirm test discovery and actual executed counts.

If security/read-path/legacy projection warrants physical verification, use the existing five-suite runner and add focused checks to the owning Phase 16 physical module under the plan. Do not create a sixth permanent suite solely for an ephemeral presentation task.

A single task-owned disposable local MongoDB 7 container is authorized if needed: unique name, loopback-only verified free port, no host data mount/shared volume/privileged mode, no shared database, and only generated names accepted by the existing safety owner. Use/pull the approved mongo:7 image through standard Docker permissions. No Docker installation, Atlas fallback, or ambient unverified URI. Keep PHASE12_MONGO_URI in the child environment only. Never print/persist it or touch clm_poc. Remove only the exact task-owned container/volumes after verified database cleanup; no prune.

All required physical tests must collect, execute and pass with zero failures/errors/skips. Read the runner summary, not only its exit status. Dynamic totals, not historical 22/23/etc., are authoritative. Memory-only ordinary tests must not inherit durable runtime settings.

## 14. Failure handling without overnight approval loops

Classify each failure as environment precondition, application/test defect, unavailable authority, stale evidence, or unexplained runtime failure. Preserve the first actual failure and exact tested identity.

Pre-execution sandbox/dependency failures may be corrected within authorized setup and the identical command retried after the concrete prerequisite changes. Do not count that as product evidence. Never bypass the actual permission system.

For an observed test failure, allow one focused diagnostic rerun ONLY with a stated new diagnostic purpose and controlled condition; it is not proof that the original failure disappeared. Do not rerun full suites on unchanged content until green.

For in-scope reproducible defects, implementer has up to two repair cycles per underlying issue. After two unsuccessful cycles, ask a fresh High architecture/contract analyst once for a materially different within-scope plan. If the necessary solution needs new sponsor authority or crosses a prohibited owner, stop the dependent task; do not expand it unattended.

Allow at most two remediation rounds after the first independent QG, followed by independent re-review of changed semantics and affected checks. No infinite critic loop. Unknown historical/new timing failures, secrets, policy ambiguity, destructive cleanup, broad auth/persistence refactoring, and missing required infrastructure are not solvable by a self-issued risk waiver.

A new lifecycle/login error blocks the dependent acceptance/publication. Do not increase timeouts, weaken hashing/security, disable StrictMode, skip failing tests, prewarm covertly, inject login state, or reuse earlier owner acceptance. Capture existing sanitized diagnostics. Other disjoint work may finish, but the overall core increment does not get PASS if a required criterion remains blocked.

Do not undertake a new auth/lifecycle reliability phase tonight. If that becomes necessary, preserve the feature result with a precise blocker instead of spending the entire night on out-of-scope remediation.

## 15. Documentation and evidence hygiene

Use these bounded artifacts, plus the supplied brief:
- `.ai-pipeline/001_planner/EVIDENCE_WORKBENCH_PLAN.md`;
- `.ai-pipeline/reports/EVIDENCE_WORKBENCH_IMPLEMENTATION.md`;
- `.ai-pipeline/reports/EVIDENCE_WORKBENCH_QUALITY_GATE.md`;
- `docs/demo/EVIDENCE_WORKBENCH_DEMO.md`.

Keep worker scratch summaries in conversation or an existing ignored task-state location without secrets. Do not create a new report for every command, status read or minor repair. The implementation report can maintain a revision-indexed evidence matrix and progress/next-action handoff across compaction.

Canonical docs may be minimally refreshed once, by the coordinator: PROJECT_STATE, ARCHITECTURE, and relevant API/contract handoff. At baseline they still describe Phase 16 as a feature-branch implementation and a historical verified SHA. Correct actual merged-capability wording from source, and distinguish the newly implemented branch scope from accepted main. Any verified_main_sha must describe the baseline genuinely examined, not a guessed future commit. Do not create a separate state-closeout PR or keep chasing a self-changing SHA.

Do not close Q-001 through Q-018 or change provider classifications. Retain the offline Camunda and historical timing limitations.

Before independent QG, check ALL task-owned new and changed Markdown for trailing whitespace, final newline and conflict markers. Reports must use ordinary paragraphs or explicit <br>, never trailing-space hard breaks. A formatting-only normalization within current task-owned docs is authorized; preserve wording and historical verdicts and have a fresh low/medium reviewer verify exact transformation when it changes frozen evidence. Do not halt overnight for permission to remove two trailing spaces, and do not silently rewrite a historic review.

Record canonical Git blob identities for the reviewed source set, with line-ending handling explicit. Do not hash a final reviewer report into itself or demand a commit hash before that commit can exist. The report writer owns its report; the code-review freeze excludes that authorized report addition. Use one stable ordering for manifests.

## 16. Independent quality gate

Stop all writers and freeze the candidate after integrated verification and implementer self-review.

Assign a fresh Sol High final reviewer following fyp-quality-gate, supplemented by an independent security reader if the public projection warrants it. No reviewer may have implemented the candidate or its remediation. Architecture-plan advice is not a substitute for final independent review.

Reviewer may write only the final QG report. It must:
- inspect the complete candidate against EW-01–17 and actual APIs;
- verify no second business/calculation/action owner;
- challenge internal-reference leakage, cross-case/session state and false freshness/approval claims;
- execute selected adversarial tests rather than accept the implementer's prose;
- verify real browser results and fixture honesty;
- verify physical/read-parity evidence if applicable;
- verify preserved review/recovery/no-replay behavior and source classification;
- identify runtime/deployment limitations accurately.

Verdicts: exact PASS; FAIL with concrete findings; or BLOCKED with missing required evidence/authority. PASS WITH MINOR FIXES is not publication-eligible. A note saying an environment is imperfect cannot override a real failed criterion.

If remediation is needed, assign it back to the implementer, retain the prior findings and identity, rerun affected checks, and use a fresh independent recheck. Resume automatically within the authorization and budget; do not return to the owner for routine in-scope corrections.

If partial low-priority polish is incomplete, report it only if the predeclared core criteria still all pass. Do not silently drop a core capability to claim completion. A genuinely standalone smaller PR requires independent coherent acceptance and truthful narrower scope; never publish a half-wired backend/UI contract.

## 17. Publication — one reviewed PR, no automatic merge

After exact independent PASS, separate publisher is authorized to:
1. verify accepted source identities and scoped report additions;
2. stage only the planned task paths, never broad git add -A;
3. run staged whitespace/secret checks before commit;
4. create a descriptive feature commit containing implementation, tests and finalized evidence;
5. fetch latest main and inspect drift;
6. if unchanged, avoid needless integration; if advanced and safely non-conflicting, a normal integration merge is authorized, with affected tests and independent recheck for changed semantics;
7. stop on unclear conflict intent; no ours/theirs wholesale, no rebase/reset/force-push;
8. run clean committed-tree pre-PR and complete its checklist;
9. push `feature/evidence-explainability-workbench` and verify remote SHA;
10. create/update exactly one PR targeting main.

Suggested title: `feat(evidence): add registry and ownership explainability`.

The body must state actual scope, baseline/head, source/projection differences, reviews/evidence, implementation versus pre-existing capability, and unchanged sponsor/provider boundaries. It must not erase old PR evidence or claim compliance certification. Restore/retain a complete PR body when adding CI status, rather than replacing it with a diagnostic sentence.

Do not end after acknowledgement if operations succeeded: return actual commit, remote, PR and CI identities. If publication approval is unavailable, leave the accepted clean commit safely local and return the exact blocked operation; do not pretend it was pushed.

Observe applicable normal push and pull_request runs separately, with run/attempt and actual checked-out SHA/tree from logs when available. Do not infer push status from a PR-only wrapper. Do not manually rerun failed jobs or make empty commits. Poll only read-only status within the active task and remaining budget; no unattended promise after returning.

For a concrete in-scope CI defect, one bounded causal remediation/publication cycle may proceed under the remaining overall repair budget, requiring independent recheck. Unknown failures or broadened scope block; report detailed safe logs. No risk acceptance, checks bypass, branch-protection change or merge.

Include the final QG report in the feature publication before final-head CI. Live run statuses belong in the PR/chat, not a new documentation commit after every run. Do not create a needless final-head report/CI/report loop.

## 18. Morning handoff and stop

Return one concise receipt plus the implementation/demo report paths:
- branch, BASE_SHA, final local/remote head, current main;
- completed capabilities versus existing reused behavior;
- exact changed/retired owners and files;
- API/schema/provider/auth/runtime changes stated explicitly;
- tests and coverage map, including failures, skipped prerequisites and actual counts;
- independent QG and remediation history;
- commit/pre-PR/PR/push and PR CI status;
- task-owned process/port/container cleanup;
- limits, unresolved risk, and the next human action.

Allowed final states:
- READY FOR HUMAN REVIEW — CI GREEN;
- ACCEPTED AND PUBLISHED — CI IN PROGRESS;
- ACCEPTED LOCALLY — PUBLICATION APPROVAL BLOCKED;
- IMPLEMENTED — INDEPENDENT REVIEW/EVIDENCE BLOCKED;
- BLOCKED — precise cause and safe retained state.

Finish with a five-minute demo path based on actual supported synthetic fixtures. Do not call a mocked client test a real journey. Do not leave servers running by default, consume the rest of the night with extra work, clean old worktrees, or start another phase.

No automatic main merge. No new sponsor-policy decision. No external runtime activation.

## Source anchors for the orchestrator

Read these in the local pinned repository; no separate attachment handoff is required beyond this brief:
- `AGENTS.md`;
- `docs/PROJECT_STATE.md`;
- `docs/ARCHITECTURE.md`;
- `docs/DEVELOPMENT_WORKFLOW.md`;
- `docs/sponsor-questions/OPEN_QUESTIONS.md`;
- `apps/backend/app/api_models.py`;
- `apps/backend/app/domain/models.py` and `domain/ownership.py`;
- `apps/backend/app/services/registry_acquisition.py`;
- `apps/frontend/src/pages/CaseDetail.tsx` and `CaseStatePanels.tsx`;
- `apps/frontend/src/pages/DocumentEvidencePanel.tsx`;
- existing ownership components, `types.ts`, `caseQueries.ts`, and auth ordering tests;
- `docs/demo/DEMO_RUNBOOK.md`, guarded E2E and physical-test runbooks;
- accepted Phase 16 main-integration and diagnostic reports only where they answer the current question.

Official tooling references, if version/permissions questions arise:
- https://developers.openai.com/codex/subagents/
- https://learn.chatgpt.com/docs/agent-approvals-security

Primary source code and current installed-version documentation take precedence over an outdated search index or unverified historical claim.
