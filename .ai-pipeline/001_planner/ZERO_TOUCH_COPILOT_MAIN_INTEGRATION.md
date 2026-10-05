# Latest-main integration — Zero-touch and read-only Copilot

Owner task:2026-10-06 integration attachment; local pending merge then fresh independent
PASS0/0/0 before merge commit. Maximum2 integration remediation rounds. No publication.
Worktree:existing zero-touch-registry-reuse-happy-path; branch
fix/zero-touch-registry-reuse-happy-path. Pre-integration HEAD859f21872121f437020f555169ff001c3825427f;
preserve parent/acceptedccff7471fd23e64e87bf94a087a5540762276900 without rewrite.
Original BASE771a9696e1e31e3865da4fbbb3f9b33b5959cb6a.
Fresh fetched origin/main1fc097f12c84af52b1e6d70a336cc22b03f3bef4 exactly matches owner expectation.
Only new main commit is read-only Copilot PR74:28 paths. Feature cumulative104 paths.
Exact-file overlap0. Pending merge is automatic/conflict-free, no conflict resolution.

## Shared surfaces and necessity

Same subsystem/different files: frontend root/App, Vite assistant proxy prefix before/api,
case routing/intake context, existing AuthProvider/session-generation/query lifecycle,
CaseDetail current schema10 projection, and test inventory. All backend feature source,
fixtures, currentness, final confirmation and ledger owners must remain unchanged.
No dependency/lockfile change or CI lifecycle addition is needed solely for the merge.

Source inspection finds two bounded integration adaptations:
- Copilot guide still directs users to Readiness check / Preparing GoldTier Submission,
  while accepted case UI uses Submission readiness / GoldTier submission package.
- Copilot's direct fetch bypasses the existing authenticated transport's current-session
  401 cleanup. Reproduce with a focused test, then reuse the existing owner; never add
  a second session/auth/cache owner or weaken stale-response generation guards.

Architecture review:PROCEED. Existing Copilot presentation/client consumes authorized
GET API summaries/documents; CLM retains case classification, business rules, target
mutation and persistence. Existing api.ts transport handles session generation/CSRF/401;
reuse via a narrow export rather than duplicate callbacks. Guide change is wording.
The actual schema10 probe also found fallback text saying nothing remains despite the
backend's final Review & Send node. Reuse existing next_pending_step presentation to
copy that node label; never derive readiness or grant target authority in Copilot.
Frontend adverse probes also reproduce retained inaccessible-case data after404 and
publication of an aborted older brief during evidence refresh. Clear only that local
conversation on backend404, and honor existing AbortController state before publishing
brief/chat callbacks. Keep per-case conversations and authenticated session ownership.
No new owner/service/repository/provider/framework/dependency direction or ADR required;
accepted main supplies the service. No case business logic goes into apps/assistant.

## Verification sequence

1. Focused RED for Copilot401; minimal reuse and guide alignment; current schema10
   integration tests using ordinary authenticated backend APIs in both modes.
2.102 zero-touch focus/actual OCR plus Copilot suite; current conflict/fresh/third evidence
   summaries consumed read-only with zero case/target mutation and no provider calls.
3. Frontend Copilot/context/auth/cache tests, full frontend, typecheck/build.
4. Guarded real HTTP Alpha and conflict browsers on owned Mongo7, generated allowlisted
   namespaces only. Shared root/proxy source review and additional scoped evidence.
5. Backend affected readiness/recovery/no-replay, Ruff/strict mypy, assistant Ruff/mypy,
   contracts/hostile isolation/governance/security. Serialize runtime-heavy suites.
6. Proportional full backend after all browser/physical processes finish when needed.
7. Freeze complete integrated tracked tree plus explicit task-owned new source/docs/tests.
   Fresh independent integration gate writes only assigned report, source immutable.
8. On exact PASS0/0/0, stage only reviewed integration paths/reports, compare staged/
   committed payload, commit pending merge with parents859f218 and1fc097f. Prove clean
   index/worktree, feature ancestry and main containment; no rebase/amend/squash/push/PR/
   PR merge/auto-merge/worktree deletion. Stop for owner review.

## Isolation / resources / limitations

Coordinator is sole source/Git writer. Primary checkout stays untouched; task writes
need escalation. Python3.12 primary venv, task-isolated frontend dependencies, local
Tesseract and guarded Playwright are available; dependency manifests unchanged.
Before all application imports use standard test/memory/Mock containment, no dotenv;
Copilot settings env_file disabled before its module-level app creation, LLM disabled
and only injected fake transports. No owner env/DB/clm_poc/external ACRA/GoldTier or model.
Browser reserves loopback18765/14173 and owned fresh Mongo27185 only; all generated DBs
must be absent before stopping the exact new container. Historical protected non-access
remains NOT_CERTIFIED, owner acceptedYES from prior disposition; do not investigate it.
Pre-PR checker is a later clean committed-state evidence step, not an uncommitted gate;
publication remains unassigned. No Live/approval/provider-status promotion.
