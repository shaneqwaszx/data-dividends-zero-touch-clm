# Phase 13 Demo Completeness Remediation — Independent Final Quality Gate

## 1. Executive summary

**Result: FAIL.** Two High-severity defects remain open. First, the production browser-origin policy derives an accepted origin from the request-controlled `Host` value, and it also accepts an `Origin` header containing a path. Independent production-mode probes returned HTTP 200 for both cases, contrary to the explicit fail-closed origin requirements. Second, ordinary Phase 13 tests construct `Settings(app_env="test")` without disabling the root `.env`; with this repository's configured Mongo mode, the nominal unit/focused command connected to and wrote 30 incomplete cases into the shared `clm_poc` database. The latter is both a test-isolation defect and a material quality-gate data-safety incident.

The qualifying memory-mode focused and full backend suites, isolated physical Mongo rerun, frontend, contracts, Windows lifecycle, mypy, dependency, diff, and secret/pre-PR unit checks otherwise passed. Task-owned Ruff remains non-green. Phase 13 is not ready for owner-controlled integration, and this gate does not authorize remediation or shared-database cleanup.

Evidence classification: command and database counts are **MEASURED**; code, diff, and documentation inspections are **OBSERVED**; readiness and severity conclusions are **INFERRED** against the supplied final-gate contract; production IAM and live ACRA/GoldTier behavior remain **UNKNOWN** and out of scope.

## 2. Baseline / branch / drift

| Evidence | Result |
|---|---|
| Branch | **MEASURED:** `fix/phase13-demo-login-identities` |
| Declared base | **MEASURED:** `dcb52937d46882a5b1b6ba7f2d545829e6fda662` |
| `HEAD` | **MEASURED:** `dcb52937d46882a5b1b6ba7f2d545829e6fda662` |
| Fetched `origin/main` | **MEASURED:** `dcb52937d46882a5b1b6ba7f2d545829e6fda662` |
| Merge base | **MEASURED:** `dcb52937d46882a5b1b6ba7f2d545829e6fda662` |
| `HEAD..origin/main` | **MEASURED:** empty; no main drift |
| Index | **MEASURED:** empty |
| `git diff --check` | **MEASURED:** PASS; line-ending notices only |

`git fetch origin` completed. No branch switch, merge, rebase, reset, clean, stash, stage, commit, or push occurred. The tracked and task-owned untracked scope matched the supplied inventory. The two explicitly protected unrelated untracked artifacts and the inaccessible pre-existing `pytest-cache-files-*` directories were not opened or modified.

## 3. Review scope

**OBSERVED:** The review covered the complete uncommitted authentication/identity, RBAC, priority-at-create, deterministic seeder, Mongo/restart, provider-free history, and Dashboard V1 delta against the declared baseline. AGENTS.md, project context, the Phase 13 planner, prior Phase 13 gates, role instructions, repository-scoped quality/integration/security/regression/CI skills, branch protocol, checklists, current implementation reports, changed code/tests/docs, and relevant persistence/auth/query owners were inspected.

The review remained implementation-read-only. The only repository file created is this report.

## 4. Authentication origin-policy verification

**OBSERVED:** `Settings.phase13_trusted_browser_origins` adds exactly `http://127.0.0.1:5173` in development/test and adds nothing in production. No wildcard, arbitrary port, localhost alias, or request override setting was introduced. Existing tests and the real Vite-proxy lifecycle check prove the documented Vite origin reaches normal credential validation, while ordinary foreign Origin/Referer values are rejected.

**MEASURED — FAIL:** `BrowserOriginPolicy.request_is_trusted` unions `request_origin`, derived from `request.url`, into `accepted_origins` at `apps/backend/app/api_auth.py:110-119`. Because the request URL is influenced by `Host`, a production request supplying a foreign Host and the same foreign Origin returned HTTP 200 with valid runtime credentials. This violates the explicit requirement that request-controlled Host/Origin/Referer values cannot alter trust and the requirement that production remain fail-closed.

**MEASURED — FAIL:** `_origin_from_url` at `apps/backend/app/api_auth.py:260` discards the path rather than rejecting it. A production login request with an `Origin` containing a path returned HTTP 200 instead of `CSRF_VALIDATION_FAILED`.

Normal evidence remained green: documented Vite Origin plus a wrong password reached credential validation and returned the generic 401; unknown user and wrong password remained non-enumerating.

## 5. Session / cookie / CSRF verification

**OBSERVED / MEASURED:** Opaque server-side sessions, SHA-256 token-digest lookup, eight-hour absolute expiry, one active session per synthetic profile, re-login rotation, host-only HttpOnly `SameSite=Strict` `/api` cookie, Secure production cookie, fail-closed unsafe production cookie configuration, session-bound CSRF, CSRF-protected logout, and no Mongo session persistence remain implemented and covered by the 86-test focused pass.

Missing/wrong CSRF and ordinary foreign Origin/Referer tests pass. No frontend localStorage/sessionStorage authority exists. However, the Host-derived trust defect in section 4 prevents the overall CSRF/origin boundary from passing.

## 6. Synthetic identity matrix

| User ID | Display | Role | Team | Result |
|---|---|---|---|---|
| `maya-lim` | Maya Lim | `CLIENT_ONBOARDER` | `TEAM_A` | **MEASURED: PASS** |
| `ethan-tan` | Ethan Tan | `RELATIONSHIP_MANAGER` | `TEAM_A` | **MEASURED: PASS** |
| `sophia-ng` | Sophia Ng | `CLIENT_ONBOARDER` | `TEAM_B` | **MEASURED: PASS** |
| `ryan-lee` | Ryan Lee | `RELATIONSHIP_MANAGER` | `TEAM_B` | **MEASURED: PASS** |
| `olivia-koh` | Olivia Koh | `DIRECTOR` | global/null | **MEASURED: PASS** |

**OBSERVED:** Active credential keys are the five required person-name settings. Bounded searches found no active use of the retired technical IDs; ordinary uses of the word “director” are role/variable/domain language, not the retired user ID. Missing and malformed hashes fail closed. The generator uses hidden prompts and emits generated scrypt hashes only. No usable demo plaintext password or reusable hash was found in the bounded task-owned scan.

## 7. Team metadata / persisted team IDs

**OBSERVED / MEASURED: PASS.** The backend domain owns the required DBS/OCBC display name, common team type, and client-scope label. API profile responses expose backend-authored metadata and available teams. The frontend renders it without using display names for authorization. Persisted IDs remain exactly `TEAM_A` and `TEAM_B`; Olivia remains global. No display-label migration was introduced.

## 8. Shared-store RBAC

**MEASURED: PASS in isolated memory and physical Mongo tests.** Maya/Ethan share Team A; Sophia/Ryan share Team B; Olivia sees both. Cases remain team-owned, not user-assigned. Header, query, JSON, and frontend state spoofing does not author role/team scope. Dashboard calculation begins with `CaseQueryService.list_cases(actor)` before aggregation (`apps/backend/app/services/dashboard.py:40`).

The shared database is no longer in its pre-gate state because of P13-DC-FQG-002; that operational incident does not change the observed authorization implementation but blocks safe completion.

## 9. Direct-ID non-enumeration

**MEASURED: PASS.** Team A and Team B inverse detail and representative priority-mutation probes return the same fixed 404 status/body as absent IDs; Director access succeeds. No 403/existence distinction was introduced.

## 10. Seeder implementation / idempotence

**OBSERVED / MEASURED: PASS in memory mode.** The seeder prompts through `getpass`, authenticates as `olivia-koh`, uses only HTTP application APIs, creates with initial priority, attaches a bounded fictional PDF through the normal demo workflow, and verifies final qualification. It contains no repository/Mongo write path and no direct terminal-state mutation. The memory integration test proves first run `10 created / 0 reused`, second run `0 created / 10 reused`.

Candidate selection prefers an exact priority/success match (`scripts/seed_phase13_demo.py:241-249`), uses the canonical priority PATCH only for a selected mismatch, drives non-completed candidates through the existing workflow, and performs a final portfolio verification (`scripts/seed_phase13_demo.py:258-274`). The seeder was not run against shared `clm_poc` during this gate.

## 11. Successful showcase-state verification

**MEASURED:** Projection-limited shared reads found exactly five qualifying records for Team A and five for Team B, each requiring schema v2, the expected team/UEN/priority pair, `automation.status=COMPLETED`, and `automation.metrics.final_outcome=MOCK_GOLDTIER_SUBMITTED`. Memory seeder tests independently exercise Registry → Document → Reconciliation → Ownership → Readiness → Mock GoldTier. No fake completion endpoint or raw status patch was found.

## 12. Shared historical collision handling

**MEASURED:** Before the unsafe focused run, the accepted Part 2 evidence reported 16 shared records. After the unsafe run, projection-limited read-only inspection measured 46 total: 37 Team A and 9 Team B. Exactly 30 records timestamped within the unsafe run were added, split 27 Team A / 3 Team B; none was completed. The originally qualified five-per-team showcase still exists and all shared records are schema v2.

**FAIL:** The QG therefore cannot confirm that unrelated/shared history remained untouched. No attempt was made to delete, patch, normalize, or hide the 30 added records. Owner-controlled incident assessment and cleanup authorization are required separately.

## 13. Priority create contract

**MEASURED: PASS in forced memory mode.** Omitted and explicit null become null; exact integers 1–10 succeed; 0, 11, negative values, floats, booleans, numeric strings, and arbitrary strings are rejected before creation. The Pydantic type is strict and constrained.

## 14. Atomic priority-at-create

**OBSERVED / MEASURED: PASS.** `StartZeroTouchCaseRequest` owns optional priority; both normal and demo create routes pass it through the zero-touch/CLM/onboarding chain (`apps/backend/app/main.py:1053,1123`) into the initial `OnboardingCase`. Create responses and isolated physical snapshots immediately contain the value. No initial `CASE_PRIORITY_UPDATED` event or create-then-PATCH browser sequence is required. Later PATCH remains supported and does not change automation `updated_at`.

## 15. Canonical ordering

**OBSERVED / MEASURED: PASS.** `CaseQueryService` orders non-null first, descending priority, automation `updated_at`, then case ID (`apps/backend/app/services/case_query.py:90-96`). Unset follows prioritised cases. Dashboard top-active filters the already canonical authorized order. The frontend does not establish a competing priority order.

## 16. Memory-mode evidence

**MEASURED: PASS.** With process environment `CLM_PERSISTENCE_MODE=memory`, the focused backend suite passed 86/86, the full backend passed 848 with the 12 expected physical markers skipped, the deterministic seeder passed, Dashboard/RBAC/priority passed, and the Windows lifecycle restart/reset suite passed 17/17. The runbook truthfully says memory mode is process-local and must be reseeded after restart.

## 17. Mongo configuration/connectivity

**MEASURED:** URI configured YES; scheme `mongodb+srv`; target REMOTE; configured mode `mongo`; database `clm_poc`; collection `clm_case_snapshots`. `python -m app.mongo` returned `MongoDB connection successful.` No URI, username, password, URI query parameter, authentication hash, cookie, CSRF value, or session token was reported.

A transient physical-test teardown traceback did print the remote cluster hostname. The hostname is intentionally omitted here. See P13-DC-FQG-004.

## 18. Mongo persistence composition

**OBSERVED / MEASURED: PASS.** Mongo mode selects the existing `MongoCaseStore`, calls `initialize`, and composes the existing Mongo repositories (`apps/backend/app/persistence/composition.py:84-108`). Missing URI and persistence failures fail closed; there is no memory fallback or second Mongo owner. The public label remains `Mongo-backed durable POC`.

## 19. Shared physical Mongo read-only evidence

**MEASURED with the exception disclosed below:** Projection-limited reads verified one canonical collection, schema v2 throughout, five qualified Team A showcase records, and five qualified Team B showcase records with priorities `10,8,5,1,null` and successful terminal state/outcome.

The intended read-only guarantee is **FAILED** for the gate as a whole: the first focused test command wrote 30 incomplete records before the configuration leak was identified. All subsequent shared checks were read-only, and the shared database was not seeded, cleaned, or normalized.

## 20. Isolated physical Mongo tests

**MEASURED: PASS on qualifying rerun.** The Phase 12 and Phase 13 suites used internally supplied `PHASE12_MONGO_URI` and guarded unique `clm_p12_*` / `clm_p13_*` databases. Qualifying rerun: 12 passed, 0 failed, 0 skipped.

The first run completed all 12 test bodies but ended with one teardown error after a transient connection close. One uniquely attributable `clm_p12_*` database remained. A read-only attribution check found exactly one guarded database, one document, and an in-run timestamp; it was then removed under the existing prefix/length/timestamp guard. Final guarded temporary database count is zero.

## 21. Restart durability

**MEASURED: PASS in isolated Mongo.** Recomposition preserved case IDs, Team A/Team B, priority, list/detail access, dashboard scope and counts, and schema v2. Phase 12 physical coverage preserved successful target checkpoint/outcome behavior. Identity authorization remained server-profile based after recreation.

The shared before/after dashboard total was not re-run because doing so through normal application initialization could recover/mutate interrupted shared records. Current shared raw total is **MEASURED** at 46; a current application-level shared dashboard total is **UNKNOWN** and is not used as PASS evidence.

## 22. Provider-free historical reads

**MEASURED: PASS.** Counting connector doubles recorded zero new Registry/ACRA, IDP, ownership, or GoldTier calls across list/detail/Dashboard reads after restart. Dashboard itself depends only on `CaseQueryService`; shared projection checks invoked no providers.

## 23. Dashboard architecture / authentication

**OBSERVED / MEASURED: PASS.** `GET /api/clm/zero-touch/dashboard` is actor-only and unauthenticated access returns 401. The route has no body or scope parameter. The path is authenticated actor → `CaseQueryService` → `DashboardService` → typed domain response → frontend. Dashboard does not query Mongo directly, know persistence mode, call providers, or mutate state.

## 24. Dashboard RBAC / non-leakage

**MEASURED: PASS in memory and isolated Mongo.** Team A and Team B tests prove scope is applied before every aggregate/list/trend. Director sees both authorized teams. Query/header spoofing does not change scope. Team responses contain no other-team placeholder, count, case ID, UEN, legal name, or trend contribution.

## 25. Dashboard KPI definitions

**OBSERVED / MEASURED: PASS.** Totals are authorized record counts; completed means exact `AutomationStatus.COMPLETED`; completion rate is completed/total or 0 for empty; prioritised means non-null priority (`apps/backend/app/services/dashboard.py:40-43`). No SLA, approval rate, risk score, productivity, regulatory KPI, or forecast was added.

## 26. Dashboard status distribution

**MEASURED: PASS.** Every canonical `AutomationStatus` is deterministically zero-filled and counted exactly; no invented or merged status band exists.

## 27. Dashboard priority distribution

**MEASURED: PASS.** Output is exactly priorities 10 through 1 plus unset, with factual counts and no high/medium/low business bands.

## 28. Dashboard team distribution

**MEASURED: PASS.** Team actors receive only their own backend-authored team entry. Director receives Team A/DBS Corporate Onboarding and Team B/OCBC Corporate Onboarding.

## 29. Dashboard recent cases

**OBSERVED / MEASURED: PASS.** Recent cases are capped at 10 and ordered deterministically by automation update time/case ID. Only already persisted canonical legal names are projected, no enrichment occurs, and Open reuses the existing detail flow.

## 30. Dashboard top-active cases

**OBSERVED / MEASURED: PASS.** Top-active is capped at 5, excludes exact COMPLETED cases, and preserves authorized canonical priority/query order. Unset handling is consistent and no priority-to-risk interpretation exists.

## 31. Dashboard historical trend semantics

**OBSERVED / MEASURED: PASS.** The service returns exactly 30 UTC calendar dates, oldest to newest and zero-filled. “Created” uses persisted `ZeroTouchAutomationRecord.created_at`; that record is created immediately with the accepted zero-touch case and is a stable reasonable case-creation timestamp. “Completed” uses persisted `completed_at`, set when status becomes exact COMPLETED. Implementation lines are `apps/backend/app/services/dashboard.py:137-145`; no fabricated dates or provider calls were found.

## 32. Dashboard frontend

**MEASURED: PASS.** Dashboard is the default authenticated tab; New Onboarding, Cases, Onboarded, and Audit remain accessible. Signed-in name/role/team/scope, backend KPI/status/priority/team/recent/top-active/trend data, empty/loading/sanitized-error states, refresh, and Open are covered. No chart dependency or browser auth authority was added. Vitest passed 114/114 and build transformed 46 modules.

## 33. Route inventory

**MEASURED: PASS.** The exact recursive inventory contains 43/43 classified operations: 2 public, with all remaining `/api` operations protected. Public endpoints remain only `GET /health` and `POST /api/auth/login`; Dashboard is actor-only. The adverse included-router test rejects an unclassified route.

## 34. Focused backend tests

**Qualifying MEASURED result:** 86 passed, 0 failed, 0 skipped in forced memory mode.

**Incident MEASURED result:** the initial configured-mode run produced 74 passed and 12 failed because tests expecting an empty memory store loaded the root Mongo configuration. That run inserted 30 shared cases and is the evidence for P13-DC-FQG-002. The qualifying rerun does not erase the incident.

## 35. Full backend tests

**MEASURED:** 848 passed, 0 failed, 12 skipped, 3 known malformed-provider serializer warnings in 55.52 seconds with memory mode forced. The 12 skips are the separately executed physical Mongo tests and are not counted as Mongo PASS evidence.

## 36. Physical Mongo test results

**MEASURED:** qualifying rerun 12 passed, 0 failed, 0 skipped. Initial run: 12 test bodies passed but pytest had 1 teardown error; the guarded leftover was attributed and removed. Final guarded temporary database count: 0.

## 37. Frontend regression

| Check | Result |
|---|---|
| Typecheck | **MEASURED: PASS** |
| Vitest | **MEASURED: 114 passed, 0 failed** |
| Production build | **MEASURED: PASS**, 46 modules; output written to and removed from a verified temporary directory |

The first Vitest attempt hit sandbox `spawn EPERM`; the approved local-process rerun passed and is the qualifying result.

## 38. Contract regression

**MEASURED:** 44 passed, 0 failed with `PYTHONPATH=apps/backend;tests/contract` and memory mode forced. No product code was changed for the helper-path requirement.

## 39. Windows lifecycle

**MEASURED:** qualifying approved rerun 17 passed, 0 failed in 197.34 seconds, with persistence forced to memory. It includes real backend/frontend startup and Vite-proxy login. The initial sandboxed run passed 3 and failed 14 because it lacked permission to terminate launcher-owned processes; this was an environment restriction, not the qualifying result. Final launcher cleanup succeeded.

## 40. Mypy / dependency / diff checks

| Check | Result |
|---|---|
| `python -m mypy apps/backend/app` | **MEASURED: PASS**, 80 source files |
| `python -m pip check` | **MEASURED: PASS**, no broken requirements |
| `git diff --check` | **MEASURED: PASS**, line-ending notices only |

## 41. Ruff / legacy style-debt assessment

**MEASURED: FAIL.** Exact task-owned Ruff check reported two `RUF100` errors at `scripts/generate_phase13_demo_password_hashes.py:13-14` for unused `# noqa: E402` directives. An exact task-owned `ruff format --check` reported 15 files would be reformatted and 7 already formatted, including mixed line-ending/style changes. No fix or reformat was applied. This is bounded task-owned debt, not the unrelated baseline-wide 93-finding debt reported by implementation.

## 42. Secret / `.env` security audit

**MEASURED:** secret/pre-PR unit suite qualifying rerun passed 42/42 (5 secret tests, 37 pre-PR tests). The first sandboxed pre-PR attempt could not initialize temporary Git repositories; the approved rerun passed. The prohibited broad scanner entry point was never invoked.

**MEASURED / OBSERVED:** A bounded 42-file task-owned pattern scan found no actual Mongo URI, usable scrypt hash, bearer token, private key, or real plaintext demo credential. Its two benign candidates were a loopback Mongo example and a marked frontend test-only credential literal not shared with backend test credentials. `.env` is ignored by `.gitignore`, untracked, unstaged, absent from the diff, and was not modified or printed. Settings were used only to obtain structural classifications and to pass the URI internally.

**FAILURE OF THE REQUESTED CONFIRMATION:** a PyMongo teardown traceback printed the remote hostname. No URI, username, password, query parameter, token, hash, cookie, or CSRF/session value was printed. The report does not reproduce the hostname.

## 43. Persistence schema audit

**OBSERVED / MEASURED: PASS.** `CASE_SNAPSHOT_SCHEMA_VERSION` remains exact integer 2 (`apps/backend/app/persistence/models.py:26`). No identity/team-display/priority-at-create/Dashboard migration exists. Exact schema-v1 reads convert only in memory to null team/priority without rewrite; non-integer and unknown schema discriminators fail closed. Isolated physical tests verified raw schema v2 and team immutability.

## 44. Diff / scope audit

**OBSERVED:** The tracked delta is limited to the declared 33 modified files plus the declared task-owned untracked dashboard/report/validator files. No package manifest/lockfile, connector interface, ACRA/GoldTier behavior, TLS setting, UBO comparator/engine, Policy & Rules feature, PingFed/SSO, production IAM, individual assignment, role divergence, persisted team rename, new schema migration, data warehouse, BI service, dashboard builder, SLA/risk metric, or unrelated dependency change was found.

No implementation file was modified by this QG. The external shared-data incident is separately disclosed and must not be confused with a repository diff.

## 45. Documentation / claim audit

**OBSERVED: substantially accurate.** Current docs distinguish synthetic POC identities/teams/data, Mock ACRA/GoldTier, POC auth versus PingFed/SSO, Mongo-backed durable POC versus process-local memory, Dashboard historical read model versus BI/MIS/KPI policy, provider-free backend RBAC, and open sponsor policy/UBO questions. They do not hardcode a ten-case Director total.

The docs' pre-gate statement that shared history was not rewritten was true of the implementation handoff but is no longer true of the environment after this QG's 30-record incident. This report is the authoritative incident addendum; implementation documentation was not changed during review.

## 46. Findings

### P13-DC-FQG-001 — HIGH — request-controlled Host expands production origin trust

- **Evidence:** `apps/backend/app/api_auth.py:110-119,260`; production adversarial probes returned 200 for matching foreign Host/Origin and for an Origin containing a path.
- **Impact:** production origin trust is broader than the fixed backend-owned policy, violating an explicit security acceptance criterion. Proxy/host-header behavior can influence the CSRF origin decision.
- **Required remediation:** establish the canonical same-origin authority from validated deployment configuration or an explicitly trusted proxy/host boundary; do not add raw request Host to the trusted set; strictly reject malformed Origin syntax; retain normal Referer path support while comparing its extracted origin; add direct Host-spoof and Origin-path regressions for login and authenticated unsafe mutation.

### P13-DC-FQG-002 — HIGH — ordinary Phase 13 tests can write the configured shared database

- **Evidence:** multiple ordinary tests construct `Settings(app_env="test")` without `_env_file=None` or an explicit memory mode, including `apps/backend/tests/test_phase13_priority.py:69,85,285,302,316,350,378` and `apps/backend/tests/test_phase13_auth_rbac.py:249,386,435,463,490,572`.
- **Measured consequence:** the initial focused command increased shared `clm_poc` from the reported 16 records to 46 by inserting 30 incomplete cases (27 Team A, 3 Team B). Twelve assertions then failed because the tests observed shared history.
- **Impact:** the documented ordinary test command is not isolated in a repository whose root `.env` selects Mongo; it can pollute shared demo history and produce environment-dependent failures.
- **Required remediation:** make every ordinary test use an explicit `_env_file=None` memory Settings/fixture, or enforce a test bootstrap that cannot select the shared database; add a guard that refuses non-ephemeral Mongo database names in tests. The owner must separately assess and authorize cleanup of the 30 QG-created records. This QG did not clean them.

### P13-DC-FQG-003 — LOW — task-owned Ruff and format checks are non-green

- **Evidence:** two `RUF100` errors at `scripts/generate_phase13_demo_password_hashes.py:13-14`; task-owned format check says 15 files would be reformatted.
- **Required remediation:** remove or correctly configure the stale directives and normalize only the task-owned files without broad repository formatting.

### P13-DC-FQG-004 — LOW — physical-test teardown is transiently fragile and traceback output is not minimized

- **Evidence:** the first 12-test physical run ended with one teardown connection error, left one guarded temporary database, and printed the remote hostname in the third-party traceback. The uniquely attributable database was safely removed; a suppressed-output rerun passed 12/12 and final guarded database count is zero.
- **Required remediation:** add bounded cleanup retry/final verification for self-created ephemeral databases, and run remote physical checks through traceback suppression/redaction so infrastructure hostnames are not emitted.

Finding totals: Critical **0**, High **2**, Medium **0**, Low **2**.

## 47. Remaining limitations

- POC authentication is not production PingFed/SSO, distributed sessions, MFA, account governance, or production RBAC.
- Dashboard V1 is not BI/MIS, forecasting, regulatory KPI, analytics warehouse, pagination, or export.
- Memory mode remains process-local; Mongo is a single-instance durable POC, not production retention/backup/governance.
- Live ACRA, real GoldTier/PingFed, and Ready-for-Approval/four-eye readiness remain unknown/not established.
- Production `scripts/pre_pr_check.py` was not run against the intentionally dirty uncommitted tree; it remains an owner-integration step after remediation, commit, and latest-main verification.
- Shared `clm_poc` contains 30 incomplete records created by the unsafe QG command and must be handled only through a separately authorized owner incident-response action.

## 48. Final metrics

| Metric | Exact result |
|---|---|
| Focused backend | 86 passed / 0 failed / 0 skipped (qualifying memory run); initial unsafe run 74 passed / 12 failed |
| Full backend | 848 passed / 0 failed / 12 skipped / 3 warnings |
| Physical Mongo | 12 passed / 0 failed / 0 skipped (qualifying rerun); initial run had 1 teardown error |
| Frontend typecheck | PASS |
| Frontend Vitest | 114 passed / 0 failed |
| Frontend build | PASS |
| Contracts | 44 passed / 0 failed |
| Windows lifecycle | 17 passed / 0 failed (qualifying rerun) |
| Mypy | PASS |
| `pip check` | PASS |
| `git diff --check` | PASS |
| Task-owned Ruff | FAIL — 2 RUF100; task-owned format check also non-green |
| Secret/pre-PR unit tests | 42 passed / 0 failed (qualifying rerun) |
| Memory mode | PASS |
| Remote Mongo connectivity | PASS |
| Mongo persistence | PASS in isolated physical suite; shared-data safety FAIL |
| Restart durability | PASS in isolated physical suite |
| Provider calls during historical reads | 0 |
| Dashboard TEAM_A RBAC | PASS |
| Dashboard TEAM_B RBAC | PASS |
| Dashboard Director scope | PASS |
| Dashboard historical trend | PASS |
| Critical findings | 0 |
| High findings | 2 |
| Medium findings | 0 |
| Low findings | 2 |

## 49. Final verdict

Phase 13 is not ready for owner-controlled integration. P13-DC-FQG-001 and P13-DC-FQG-002 require remediation and independent re-gating. The owner must also decide how to contain and, if explicitly authorized, remove only the 30 QG-created shared records. No next phase may begin on the basis of this gate.

FAIL — PHASE 13 DEMO COMPLETENESS REMEDIATION REQUIRES REMEDIATION
