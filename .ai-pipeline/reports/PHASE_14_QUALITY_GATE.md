# Phase 14 Case Management and Performance — Independent Quality Gate

Review date: 2026-09-09

Reviewer role: independent quality-gate reviewer; this reviewer did not implement Phase 14.

Branch: `phase/14-case-management-performance`

Baseline/HEAD: `aba264af3b4088a9a10fe682ee6fc0cb418d550d`

Fetched `origin/main`: `aba264af3b4088a9a10fe682ee6fc0cb418d550d`

## 1. Executive Result

**FAIL.** Phase 14 has one reproducible high-severity hard-delete lifecycle race and one
reproducible medium-severity stale-cache race. A case creation can write case-owned
automation or demo state after a successful deletion, and an older in-flight list query
can repopulate a deleted row after the server has returned `204`. The mandatory physical
Mongo proof is also **SKIPPED / UNVERIFIED** because `PHASE12_MONGO_URI` was not configured.

The broad backend, frontend, contract, lifecycle, dependency, and focused regression
suites otherwise pass. This report does not remediate either defect and does not authorize
commit, PR, merge, or a next phase.

## 2. Reviewer Independence and Method

The execution report was treated only as an assertion list. Evidence was rebuilt from the
planner, current source, direct diff, focused and broad tests, bounded security scans,
dependency inspection, deterministic query-count assertions, and two additional adversarial
race harnesses. The repository quality-gate, integration-security, POC-regression,
integration-safety, and sponsor-reconciliation guidance was applied.

No implementation file, test, dependency file, planner, execution report, or implementation
documentation was modified by this review. This dedicated report is the only QG-created file.

## 3. Baseline and Main-Drift Evidence

Initial post-fetch evidence:

| Check | Result |
|---|---|
| Current branch | `phase/14-case-management-performance` |
| `git rev-parse HEAD` | `aba264af3b4088a9a10fe682ee6fc0cb418d550d` |
| `git rev-parse origin/main` | `aba264af3b4088a9a10fe682ee6fc0cb418d550d` |
| `git merge-base HEAD origin/main` | `aba264af3b4088a9a10fe682ee6fc0cb418d550d` |
| `git log --oneline HEAD..origin/main` | empty |
| Tracked implementation delta | present: 48 modified tracked files |
| Tracked unrelated change | none identified |

The first sandboxed fetch could not write `.git/FETCH_HEAD`; the required read-only fetch was
rerun with approved escalation and succeeded. Main had not advanced before review.

## 4. Exact Changed-File Classification

### Intended product changes

- Backend: `apps/backend/app/api_models.py`,
  `apps/backend/app/domain/case_management.py`,
  `apps/backend/app/demo/zero_touch_control.py`, `apps/backend/app/main.py`,
  `apps/backend/app/persistence/composition.py`,
  `apps/backend/app/persistence/mongo_case_store.py`,
  `apps/backend/app/persistence/repositories.py`,
  `apps/backend/app/services/authorization.py`,
  `apps/backend/app/services/case_deletion.py`,
  `apps/backend/app/services/case_portfolio_repository.py`,
  `apps/backend/app/services/case_query.py`,
  `apps/backend/app/services/clm_repository.py`,
  `apps/backend/app/services/dashboard.py`,
  `apps/backend/app/services/document_repository.py`,
  `apps/backend/app/services/onboarding.py`,
  `apps/backend/app/services/ownership_repository.py`,
  `apps/backend/app/services/reconciliation_repository.py`,
  `apps/backend/app/services/repository.py`,
  `apps/backend/app/services/target_execution_repository.py`,
  `apps/backend/app/services/zero_touch_orchestration.py`,
  `apps/backend/app/services/zero_touch_provider_bindings.py`, and
  `apps/backend/app/services/zero_touch_repository.py`.
- Frontend/dependencies: `apps/frontend/package.json`,
  `apps/frontend/package-lock.json`, `apps/frontend/src/App.tsx`,
  `apps/frontend/src/api.ts`, `apps/frontend/src/auth.tsx`,
  `apps/frontend/src/caseQueries.ts`, `apps/frontend/src/queryClient.tsx`,
  `apps/frontend/src/design-system.css`, `apps/frontend/src/types.ts`,
  `apps/frontend/src/viewModels.ts`, `apps/frontend/src/pages/CaseDetail.tsx`,
  `apps/frontend/src/pages/CaseQueue.tsx`,
  `apps/frontend/src/pages/ClientDetail.tsx`,
  `apps/frontend/src/pages/Dashboard.tsx`,
  `apps/frontend/src/pages/DeleteCaseDialog.tsx`, and
  `apps/frontend/src/pages/OnboardedClients.tsx`.

### Supporting changes

- Tests/CI/safety: `.github/workflows/ci.yml`,
  `apps/backend/tests/test_phase14_case_management_performance.py`,
  `apps/backend/tests/test_phase14_real_mongo.py`,
  `apps/backend/tests/test_phase13_auth_rbac.py`,
  `apps/backend/tests/test_phase13_dashboard.py`,
  `apps/backend/tests/test_phase13_mongo_test_safety.py`,
  `apps/backend/tests/test_phase13_priority.py`,
  `apps/backend/tests/test_pre_phase12_workspace_multidoc.py`,
  `apps/frontend/src/Phase14CaseManagementPerformance.test.tsx`,
  `apps/frontend/src/App.test.tsx`, `apps/frontend/src/Dashboard.test.tsx`,
  `apps/frontend/src/Phase13AuthPriority.test.tsx`,
  `apps/frontend/src/UiV2Integration.test.tsx`, `scripts/mongo_test_safety.py`, and
  `tests/test_demo_lifecycle_windows.py`.
- Documentation: `docs/architecture/PHASE_14_CASE_MANAGEMENT_PERFORMANCE.md`,
  `docs/architecture/README.md`, `docs/PROJECT_CONTEXT.md`,
  `docs/decisions/DECISION_LOG.md`, `docs/integration/CONFIGURATION_REFERENCE.md`, and
  `.ai-pipeline/reports/PHASE_14_EXECUTION.md`.

### Unexpected changes

None. The supplied planner was inspected by exact path as a protected task input, not
classified as implementation output. Arbitrary untracked files were not enumerated.

The implementation surface is large but connected to the planner's portfolio, cache,
deletion, lifecycle isolation, and regression work. No unrelated feature, commented-out
security, debugging output, hidden compatibility fallback, or unauthorized direct dependency
upgrade was found. The only new direct runtime dependency is
`@tanstack/react-query@5.102.8`; the only new direct development dependency is
`jsdom@30.0.1`.

## 5. Phase Acceptance Checklist

| Planner requirement | Result | Independent evidence |
|---|---|---|
| Permanent DELETE route, empty `204` | PASS | Route/source inspection and focused HTTP test |
| Director/RM/Onboarder matrix | PASS | HTTP tests plus access-policy/service inspection |
| Safe inaccessible/absent `404` | PASS | Access is resolved before delete-role policy |
| Phase 13 session/CSRF/browser-source controls | PASS | Unsafe-route middleware coverage and 114-test regression |
| Any workflow-status deletion | PASS | Delete service contains no automation/workflow status gate; constructible pending cases delete; transition paths serialize on the case lock |
| Insert-only create/update-only save | PASS | Memory and Mongo owners reject duplicate create and missing save |
| No stale-write resurrection | **FAIL** | P14-QG-001 reproduces an uncovered creation boundary |
| Complete memory hard delete | **FAIL** | Sequential aggregate cleanup is complete, but P14-QG-001 leaves post-delete orphan automation/demo state |
| Mongo revision compare-and-delete | PARTIAL | Source and unit-double inspection pass; physical CAS unavailable |
| Confirmation dialog/accessibility | PASS | Component/source and eight focused frontend tests |
| Session-memory TanStack cache defaults | PASS | Exact QueryClient defaults and dependency tree |
| Clear on logout/401/login/identity change | PASS | Auth lifecycle/source and tests |
| No browser persistence | PASS | Task-owned frontend source scan |
| Queue and Onboarded remove HTTP 1+N | PASS | Each observed as one list request, zero detail requests |
| Mongo list/Dashboard remove 1+N | PASS | One projected `find`, zero per-case `get`/`find_one` in unit-double evidence |
| Cache/mutation coherence | **FAIL** | P14-QG-002 reproduces stale list resurrection after delete |
| Phase 13 priority/Dashboard compatibility | PASS | 114 focused tests and full backend suite |
| Windows ordinary-test isolation | PASS | Hostile ambient regression and full 18-test lifecycle suite |
| No Phase 14 formatter defect | PASS | Five new Python files clean; LF-normalized baseline attribution found zero new semantic defects |
| No live provider deletion | PASS | Delete composition invokes only local repositories/transient release functions |
| Isolated physical Mongo proof | **SKIPPED / UNVERIFIED** | `PHASE12_MONGO_URI_CONFIGURED=NO` |

## 6. Architecture Review

The portfolio read model has one clear owner and removes the previous browser list/detail and
Mongo list/get N+1 paths. Team scope is backend-authored and included in the Mongo query.
Projection decoding validates schema version, envelope/embedded case identity, discriminator,
types, enum values, and bounds. The projection excludes documents and document events,
ownership graph, reconciliation and CLM bodies, automation timeline, submission snapshot,
and target ledger. Malformed/cross-bound records fail closed.

The deletion service is appropriately separated from HTTP and persistence composition. It
holds `OnboardingService.case_lock`, re-reads authorization inside the lock, physically
deletes the aggregate, and only then releases provider/demo transients. Mongo uses one
revision-qualified `delete_one`; memory removes all composed repositories.

The central architecture defect is that the lock's ownership boundary does not cover the
whole case establishment transaction. `ZeroTouchOrchestrator.create_case` completes the
locked onboarding/CLM creation and later writes its automation record outside the lock;
the demo route then registers scenario state outside the lock as well. This contradicts the
documented lifecycle boundary and permits post-delete orphaning.

`main.py` remains an accepted composition hotspot. No duplicate portfolio/cache/deletion
owner or retained fallback N+1 path was found. The existing Audit Trail N+1 behavior remains
explicitly deferred and is outside Phase 14's list/Dashboard scope.

## 7. DELETE/RBAC Adversarial Matrix

| Actor/case | Expected | Result/evidence |
|---|---:|---|
| Director, Team A | 204 | PASS |
| Director, Team B | 204 | PASS |
| Director, legacy/null team | 204 | PASS through null-team deletion-service test |
| Director, absent | safe 404 | PASS by common missing path |
| RM, own team | 204 | PASS |
| RM, other team | safe 404 | PASS |
| RM, legacy/null | safe 404 | PASS by access-policy scope |
| RM, absent | safe 404 | PASS |
| Client Onboarder, own visible | fixed 403 `CASE_DELETE_FORBIDDEN` | PASS |
| Client Onboarder, other team | safe 404 | PASS |
| Client Onboarder, absent | safe 404 | PASS |
| Unauthenticated, existing | 401 | PASS |
| Unauthenticated, absent | 401 | PASS: authentication precedes lookup |
| Repeat after success | safe 404 | PASS |

The route accepts no request body model and derives actor/team solely from the authenticated
session. Role/team-like headers, query parameters, forwarding headers, body fields, and
request `Host` are not authorization inputs and cannot elevate authority.

## 8. Non-Disclosure Evidence

`CaseDeletionService.delete` calls the existing case-access policy before applying the
delete-role rule. Therefore an own-team Onboarder reaches the fixed `403`, while an
other-team Onboarder/RM and a nonexistent case stop at the same safe `404`. Authentication
is middleware-enforced before case lookup. The HTTP tests and Phase 13 authorization suite
confirm the outcome matrix. No timing assertion was used as proof.

## 9. CSRF, Browser-Source, and Session Evidence

DELETE is present in the exact case-scoped route inventory and traverses the accepted unsafe
mutation middleware. The test suite covers no authentication, missing/wrong/valid CSRF,
foreign and malformed Origin/Referer, Referer fragments, duplicate physical headers including
case variants, spoofed Host/forwarding headers, and session invalidation. Rejected requests
do not reach deletion. Focused Phase 14 tests independently confirmed `401` without auth,
`403` without CSRF, and rejection of foreign/duplicate Origin. No Phase 13 policy weakening
was found.

## 10. Any-Status Deletion

Observed HTTP deletion includes `PENDING_INPUTS`; the sequential real-Mongo test defines a
`COMPLETED` case but was correctly skipped locally. Source inspection is decisive for the
remaining statuses: deletion reads the onboarding envelope and access policy but never checks
automation status. Thus `RUNNING`, `WAITING_FOR_REVIEW`, `RECOVERY_PENDING`,
`TECHNICAL_FAILURE`, and `COMPLETED` cannot be rejected by status. `RESUMING` is transient;
its transition uses the canonical case lock, so deletion waits rather than inventing a held
status fixture. No terminal-only workaround exists.

This status-independent policy passes. The separate creation-boundary race in P14-QG-001
still fails resurrection safety.

## 11. Resurrection and Concurrency Review

Memory `create` is insert-only, `save` is update-only, duplicate creation conflicts, and save
after deletion conflicts. Mongo `insert_one`, revision-qualified replace, and
revision-qualified `delete_one` provide the same single-envelope contract in source and unit
doubles. Established document, ownership, reconciliation, CLM, priority, automation, target,
resume, recovery, and exception mutations inspected use the canonical case lock or fail on a
missing envelope. The focused lock test proves deletion waits for an established mutation.

Those protections do not cover initial orchestration completion. The independent deterministic
race held the automation repository's create after the onboarding case existed, deleted the
case as the own-team RM, then released the creation thread. Result:

```text
{'onboarding_absent': True, 'automation_orphan_present': True}
```

This is not a distributed-lock limitation: it reproduces in the supported single-process
memory implementation. The demo scenario registration immediately after orchestration has the
same outside-lock gap.

Concurrent DELETE is otherwise serialized: at most one call can delete; the follower re-reads
inside the lock and returns safe `404`. Physical Mongo revision-race/CAS behavior remains
unverified because the explicit URI is absent.

## 12. Memory Hard-Delete Review

Sequential source and tests show removal from onboarding, automation, CLM, documents,
ownership, reconciliation, target execution, demo scenario, provider bindings, recovery/demo
transients, list, Dashboard, and detail owners. Unrelated IDs are keyed independently. The
delete path performs no Registry, IDP, Ownership-provider, or GoldTier connector call and does
not claim external erasure.

Overall result is **FAIL**, because a successful delete is not final under P14-QG-001: the
creator can subsequently write an orphan automation record or demo registration. Sequential
cleanup completeness does not satisfy hard-delete completeness under the required race.

## 13. Physical Mongo Gate

`PHASE12_MONGO_URI_CONFIGURED=NO`. No URI/hostname/value was printed or sourced from `.env`.
The Phase 14 physical test was not run, no database was created, and no ambient configuration
was used. Consequently rich-envelope deletion, restart absence, physical count reduction,
unrelated raw-envelope preservation, physical stale-save/CAS behavior, orphan absence, and
cleanup are **SKIPPED / UNVERIFIED** and remain an integration blocker.

Static safeguards pass: only generated `^clm_p14_[0-9a-f]{24}$` names are allowed, CI includes
the Phase 14 physical test, and the test cleanup verifies deletion. `clm_poc` was neither
inspected nor mutated.

## 14. Portfolio Projection and Query-Count Proof

| Surface | Observed result |
|---|---|
| Case Queue, N rows | 1 list HTTP request; 0 detail requests |
| Onboarded, N rows | 1 list HTTP request; 0 detail requests |
| Mongo case list | 1 projected `find`; 0 per-case `get`/`find_one` |
| Mongo Dashboard input | same shared portfolio call: 1 projected `find`; 0 per-case `get`/`find_one` |

No `Promise.all(...fetchZeroTouchCase...)` or hidden detail-fetch fallback remains in either
list page. Detail is requested only after navigation. Priority invalidation targets list
families and does not reintroduce row-detail requests. These are deterministic call counts,
not a claimed millisecond SLO.

## 15. Priority, Order, Filter, and Dashboard Compatibility

The projected path retains prioritised-before-unset ordering, both selected priority
directions, `automation.updated_at DESC` then `case_id DESC` ties, and unset-last behavior.
Priority mutation does not change automation `updated_at`. Dashboard totals, completed and
non-completed counts, prioritised/unprioritised counts, completion rate, exact status and
priority distributions, team scope, recent ten, top active five, and 30-day UTC trend pass the
114-test Phase 13 auth/priority/Dashboard regression group and the full backend suite.

## 16. Frontend Cache Semantics

The actual owner is TanStack Query. Defaults are `staleTime=45_000`, `gcTime=900_000`,
`refetchOnWindowFocus=false`, `refetchOnReconnect=true`, GET retry `1`, and mutation retry
`false`. GET functions consume `AbortSignal`. Fresh navigation reuses data; stale data remains
available during one deduplicated background request; concurrent identical observers share one
request; manual refresh invalidates/refetches. Filters are part of list keys and obsolete view
requests cannot overwrite a different active key.

Overall cache result is **FAIL** due P14-QG-002. `caseDeletedEffect` filters current list caches
before cancelling any list-family request and never cancels those requests. A deterministic
TanStack Query harness started an old list request, applied the exact effect order, then allowed
the old request to settle:

```text
{"afterEffect":[],"afterOldResponse":[{"case_id":"deleted"}]}
```

The deleted row therefore can reappear after a confirmed server `204`.

## 17. Cross-User Cache Isolation

All business query keys begin with `['auth', userId]`. Successful login, logout, a foreground
or background `401`, identity replacement, and same-user re-login cancel active work and clear
the complete QueryClient before the new authenticated workspace is used. User A's Dashboard,
case list, detail, document, or ownership data is therefore neither keyed nor retained for User
B. Tests cover the lifecycle and source inspection found no parallel page-local business cache.
Result: **PASS**.

## 18. Persistent Browser Storage Scan

Task-owned production frontend source contains no `localStorage`, `sessionStorage`,
`IndexedDB`/`indexedDB`, `persistQueryClient`, service-worker cache, or cache-persistence
plugin usage. Storage references are limited to test stubs. A new QueryClient/page reload starts
empty. Result: **NONE FOUND**.

## 19. Deletion Dialog and Accessibility

Director and RM controls are rendered on authorized queue/detail surfaces; Client Onboarder has
no usable Delete control. Opening, Cancel, and Escape send zero deletes. Confirm has a
synchronous in-flight guard and sends exactly one DELETE; failure retains dialog/case and shows
a bounded error; success effects run only after `204`, then navigation returns safely from a
deleted detail. The component has `alertdialog`, `aria-modal`, labelled title, described
permanence warning, initial Cancel focus, Tab containment, Escape handling, and trigger-focus
restoration. Result: **PASS** for destructive interaction semantics.

The stale list race is assigned to cache/mutation invalidation, not to the dialog widget.

## 20. Mutation Invalidation

Create, priority, supporting evidence/document, reconciliation, resume, exception resolution,
polling, and delete use centralized cache effects. Detail/list/Dashboard invalidations are
otherwise consistent and priority never fetches N details. Delete does not optimistically hide
the case before server success.

Overall result: **FAIL** because deletion does not settle/cancel the list family before patching
it; a pre-204 request can overwrite the post-204 cache. Dashboard is removed, but deletion
should settle/cancel its request family too so no stale completion is retained or briefly
observable by an existing observer.

## 21. Lifecycle Test Isolation and Historical Incident

The current Windows lifecycle harness forcibly sets memory persistence, an ordinary-test
database namespace, and a loopback non-service Mongo poison URI after copying ambient
environment values. The hostile ambient regression proves those values win. The full escalated
Windows lifecycle suite passed **18/18** and cleaned its owned processes.

The historical ambient-database event remains only an incident receipt. This review did not
investigate its destination or outcome and makes no claim about historical `clm_poc` state.

## 22. Formatter Attribution

The bounded current formatter check reports 26 existing modified Python paths that Ruff would
reformat. All five new Phase 14 Python files are formatter-clean. An independent LF-normalized
comparison found:

- baseline semantic formatter findings: 9 files;
- current semantic formatter findings: 8 files (one baseline condition was fixed);
- Phase 14-introduced semantic formatter findings: **0**;
- current direct-only EOL-attributed paths: 17;
- broad repository formatter run: unavailable because Ruff encountered sandbox-inaccessible
  paths; no check was weakened and no formatting rewrite was performed.

`git diff --check` passed. This is a Phase 14 attribution pass, not a repository-wide formatter
pass. The count discrepancy with the execution report is P14-QG-003.

## 23. Dependency and Supply-Chain Review

`npm.cmd ls --all` passed with optional platform/peer packages reported as unmet only.
Targeted ownership is:

- `@tanstack/react-query@5.102.8`: direct runtime addition;
- `jsdom@30.0.1`: direct development-only addition;
- `vite@7.1.11` and `vitest@3.2.4`: unchanged direct development toolchain;
- `nanoid@3.3.16`: transitive under the existing PostCSS/Vite toolchain.

`npm.cmd audit` reports **0 vulnerabilities**. No audit fix or dependency upgrade was run.

## 24. Documentation and Sponsor-Authority Review

The architecture, project context, D-040, and configuration reference correctly describe the
cache as session memory, distinguish local deletion from external erasure, avoid live ACRA or
GoldTier deletion claims, and label the deletion/cache policy **PROJECT-DEFINED POC BEHAVIOR
PENDING SPONSOR CONFIRMATION**. Physical Mongo is reported as skipped, repository-wide
formatter success is not claimed, and the historical incident is not converted into a claim
that shared data was untouched.

However, the architecture/context/decision/execution claim that lifecycle serialization and
create-vs-save semantics prevent resurrection is false under P14-QG-001. The execution report
also names the new dialog at `src/components/DeleteCaseDialog.tsx` although the actual path is
`src/pages/DeleteCaseDialog.tsx`, and its formatter attribution says 10 baseline plus 16 EOL
paths rather than the independently reproduced 9 plus 17. These evidence inaccuracies are
captured in P14-QG-001 and P14-QG-003.

Sponsor artefact precedence is unaffected: no GoldTier/ACRA contract changed and no sponsor
approval is inferred. Production identity, deletion/retention, and governance remain open.

## 25. Focused and Broad Test Results

### Backend

| Command | Result |
|---|---|
| `python -m pytest tests/test_phase14_case_management_performance.py -p no:cacheprovider` | 9 passed in 1.19s |
| Phase 13 auth + priority + Dashboard focused group | 114 passed in 21.05s |
| `python -m pytest tests/test_pre_phase12_workspace_multidoc.py -p no:cacheprovider` | 32 passed in 3.10s |
| `python -m pytest` | 906 passed, 13 skipped, 3 existing adversarial Pydantic warnings in 67.79s |
| `python -m mypy app` | success; 83 source files |
| `python -m pip check` | no broken requirements |

Broad `python -m ruff check .` encountered access-denied warnings outside the task surface but
returned `All checks passed!`. The bounded task-owned check passed. A root lifecycle file has
13 Ruff lint findings; baseline stdin comparison reproduces the same 13, so Phase 14 introduced
zero lint findings. Broad `python -m ruff format --check .` could not complete because Ruff
encountered sandbox-inaccessible paths; the bounded/normalized attribution in section 22 was
used without weakening or modifying code.

### Frontend

| Command | Result |
|---|---|
| `npm.cmd ls --all` | passed; optional platform/peer unmet only |
| `npm.cmd run typecheck` | passed |
| `npm.cmd test -- --run` | 124 passed across 5 files; Phase 14 file contributed 8 passed |
| `npm.cmd run build` | passed; 94 modules transformed |
| `npm.cmd audit` | 0 vulnerabilities |

The sandbox initially denied child-process creation for Vitest/Vite; the read-only commands were
rerun with approved escalation and passed.

### Root, contracts, and POC regression

| Check | Result |
|---|---|
| Contract unittest discovery | 44 passed in 8.53s |
| Phase 07 delivery-assets discovery | 4 passed |
| Windows lifecycle discovery | 18 passed in 189.598s |
| Secret-checker unit tests | 5 passed |
| Pre-PR checker unit tests | 37 passed in 28.149s |
| GoldTier example validation | 19 valid; 19 invalid/quarantined; 48 not validated |
| Bounded task-owned `scan_file` security scan | 58 files scanned; 0 files with findings |

The accepted mock scenarios, workflow ordering, terminal/call-stopping behavior, authorization,
priority, Dashboard, multi-document, and lifecycle regressions are green in the combined focused
and broad suites. The two additional adversarial races expose coverage gaps despite those green
suites. The actual `scripts/pre_pr_check.py` and broad `scripts/check_secrets.py` were
intentionally not run, as instructed.

## 26. Integration-Security Review

Authorization, non-disclosure, CSRF/browser source, session invalidation, role/team spoofing,
Mongo scope/query construction, projection validation, direct Mongo access, sensitive logging,
browser persistence, and provider-call boundaries were inspected across the complete delta.

No credential, token, URI, cookie, session/CSRF value, KYC/PII payload, or raw sponsor artefact
was found in the bounded task-owned scan or printed by this review. Mongo query fields are
server-authored enums/scopes rather than raw client operators. Delete errors are fixed and
sanitized. No new direct integration credential or TLS boundary was introduced.

Security result: **FAIL** because hard-delete integrity is security-relevant and P14-QG-001
allows retained orphan case state after a successful deletion. P14-QG-002 is an integrity and
destructive-UX defect, not a backend authorization bypass. No Critical issue was found.

## 27. Findings Table

| ID | Severity | Affected file/contract | Concrete failure mode and reproducible evidence | Required remediation |
|---|---|---|---|---|
| P14-QG-001 | **High** | `apps/backend/app/services/zero_touch_orchestration.py:115-282`; `apps/backend/app/main.py:1172-1184`; lifecycle claims in D-040/architecture/context/execution report | Initial CLM/onboarding creation releases the canonical case lock before `_create(record)` writes automation. DELETE can then return `204`, after which the creator writes an orphan automation record. Deterministic two-thread harness result: `onboarding_absent=True`, `automation_orphan_present=True`. Demo scenario registration is also outside the lock. | Make whole case establishment—including automation create and demo registration—one canonical serialized lifecycle transaction, or add an equivalent atomic/fail-closed protocol. Roll back partial creation on failure. Add deterministic create-vs-delete and demo-registration race tests proving final absence and no case-owned orphan. Correct false resurrection-safety documentation. |
| P14-QG-002 | **Medium** | `apps/frontend/src/caseQueries.ts:172-187` | `caseDeletedEffect` patches list caches without first cancelling/settling list requests. An older request can resolve afterward and overwrite the cache. Deterministic QueryClient harness: after effect `[]`; after old response the deleted item is present again. | Cancel and await/settle all affected list and Dashboard query families before removal/filtering, then ensure stale completions cannot repopulate them. Add an adversarial test with a request already in flight at delete success. Preserve the rule that UI removal occurs only after server `204`. |
| P14-QG-003 | **Low** | `.ai-pipeline/reports/PHASE_14_EXECUTION.md` | Changed-file receipt names `src/components/DeleteCaseDialog.tsx`; actual file is `src/pages/DeleteCaseDialog.tsx`. Independent normalized formatter attribution is 9 baseline semantic + 17 EOL-only paths, not 10 + 16, while the important introduced count remains zero. | Correct the path and evidence counts after implementation remediation, without claiming repository-wide formatter success. |

Finding totals: **Critical 0; High 1; Medium 1; Low 1.**

## 28. Required Fixes and Separate Deferred Items

Current blockers:

1. Remediate P14-QG-001 and add adversarial create/delete/demo-state proof.
2. Remediate P14-QG-002 and add an actual in-flight delete-cache race test.
3. Correct the P14-QG-003 execution evidence inaccuracies.
4. Run the mandatory Phase 14 physical Mongo suite using only an explicitly configured URI
   and generated `clm_p14_<24 lowercase hex>` database; verify cleanup.
5. Rerun the independent gate after remediation and physical proof.

Separate accepted/deferred items: production retention/erasure governance, distributed
multi-instance locking, pagination, Audit Trail optimization, full production identity policy,
live ACRA verification, and real GoldTier integration. These do not excuse current defects.

## 29. Data-Safety Receipt

- `.env` accessed: **NO**
- protected unrelated artifacts accessed/enumerated/scanned: **NO**
- shared `clm_poc` inspected: **NO**
- shared `clm_poc` written: **NO**
- Mongo URI/host/credentials printed: **NO**
- physical/ambient Mongo used: **NO**
- historical incident investigated or cleaned: **NO**

Only exact task-owned untracked paths were inspected. The historical ambient-database incident
remains unresolved and unaltered.

## 30. Final Verdict, Readiness, and Git Status

**Final verdict: FAIL — Phase 14 contains a reproducible hard-delete orphan/resurrection race
and a reproducible stale-list cache resurrection race, while mandatory physical Mongo proof is
also outstanding.**

- Ready for remediation: **YES**
- Ready for commit: **NO**
- Ready for PR: **NO**
- Ready for next phase: **NO**
- Live ACRA verification readiness: unchanged and out of this phase; not performed
- Real GoldTier integration readiness: unchanged and out of this phase; not performed

Git action receipt: no implementation modified; nothing staged, committed, amended, pushed,
merged, rebased, reset, stashed, cleaned, or branch-switched. Only this dedicated report was
created. The final fetch succeeded; HEAD, `origin/main`, and merge base remained
`aba264af3b4088a9a10fe682ee6fc0cb418d550d`; `HEAD..origin/main` remained empty; the
tracked status remained the reviewed 48-file implementation delta; the staged-file list was
empty; the report appeared only as its exact untracked path; and `git diff --check` passed.
